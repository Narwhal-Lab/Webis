import argparse
import sys
import os
import shutil
import json
import logging
import subprocess
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from webis.core.pipeline import Pipeline
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext, StructuredResult
from webis.core.plugin import get_default_registry

# Import plugins to register them
import webis.plugins.sources
import webis.plugins.processors
import webis.plugins.extractors
import webis.plugins.outputs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("webis.cli")


def _prepare_rag_documents_from_json(documents_path: str) -> List[Dict[str, Any]]:
    """
    Load crawl output documents.json and convert entries into RAG manager input format.
    """
    with open(documents_path, "r", encoding="utf-8") as f:
        docs_data = json.load(f)

    rag_documents: List[Dict[str, Any]] = []
    for idx, doc in enumerate(docs_data):
        if not isinstance(doc, dict):
            continue

        content = (doc.get("clean_content") or doc.get("content") or "").strip()
        if not content:
            continue

        meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
        custom = meta.get("custom") if isinstance(meta.get("custom"), dict) else {}

        source = (
            meta.get("url")
            or meta.get("title")
            or custom.get("file_path")
            or doc.get("id")
            or f"document_{idx + 1}"
        )

        rag_documents.append(
            {
                "content": content,
                "source": str(source),
                "metadata": {
                    "doc_id": doc.get("id"),
                    "doc_type": doc.get("doc_type"),
                    "title": meta.get("title"),
                    "source_plugin": meta.get("source_plugin"),
                    "documents_json": os.path.abspath(documents_path),
                },
            }
        )

    return rag_documents


def _build_rag_knowledge_base_from_documents(documents_path: str) -> Optional[str]:
    """
    Build RAG knowledge base from documents.json using strict HuggingFace embeddings.
    """
    from webis.core.rag.manager import RAGManager
    from webis.plugins.processors.embedding_plugin import EmbeddingGemmaPlugin

    # Force HuggingFace mirror settings before loading embedding model.
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
    logger.info(
        "Using HuggingFace mirror for RAG embedding build: HF_ENDPOINT=%s, HF_HUB_DOWNLOAD_TIMEOUT=%s",
        os.environ["HF_ENDPOINT"],
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"],
    )

    rag_documents = _prepare_rag_documents_from_json(documents_path)
    if not rag_documents:
        logger.warning("No valid documents available for RAG build.")
        return None

    # Strict HuggingFace embedding mode: fail fast if model init or embedding generation fails.
    embedding_processor = EmbeddingGemmaPlugin(model_type="gemma", device="cpu")
    for idx, doc in enumerate(rag_documents):
        embedding = embedding_processor.embed_text(doc.get("content", ""))
        if embedding is None:
            source = doc.get("source", f"document_{idx + 1}")
            raise RuntimeError(f"Failed to generate HuggingFace embedding for source: {source}")
        doc["embeddings"] = [embedding]

    rag_store_path = os.path.join(os.path.dirname(os.path.abspath(documents_path)), "rag_store.json")
    rag_manager = RAGManager(
        rag_store_path=rag_store_path,
        auto_load=False,
        use_external_embeddings=True,
        embedding_processor=embedding_processor,
    )
    rag_manager.add_crawled_documents(rag_documents)
    rag_manager.build_and_save()

    logger.info(f"Built RAG knowledge base with {len(rag_documents)} docs: {rag_store_path}")
    print(f"🧠 RAG store saved to: {rag_store_path}")
    return rag_store_path


def _first_sentence(text: str, max_chars: int = 260) -> str:
    normalized = " ".join((text or "").split())
    if not normalized:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", normalized, maxsplit=1)
    sentence = parts[0] if parts else normalized
    if len(sentence) > max_chars:
        return sentence[:max_chars].rstrip() + "..."
    return sentence


def _load_rag_documents(rag_store_path: str) -> List[Dict[str, Any]]:
    rag_path = Path(rag_store_path).expanduser().resolve()
    if not rag_path.exists():
        raise FileNotFoundError(f"rag_store.json not found: {rag_path}")

    with open(rag_path, "r", encoding="utf-8") as f:
        rag_data = json.load(f)

    docs_map = rag_data.get("documents", {}) if isinstance(rag_data, dict) else {}
    if not isinstance(docs_map, dict) or not docs_map:
        raise ValueError(f"No documents found in RAG store: {rag_path}")

    dedup_seen = set()
    docs: List[Dict[str, Any]] = []
    for raw_doc in docs_map.values():
        if not isinstance(raw_doc, dict):
            continue
        content = (raw_doc.get("content") or "").strip()
        if not content:
            continue
        source = raw_doc.get("source") or "Unknown"
        dedup_key = (str(source), content)
        if dedup_key in dedup_seen:
            continue
        dedup_seen.add(dedup_key)
        docs.append(
            {
                "source": str(source),
                "content": content,
                "structured_data": raw_doc.get("structured_data"),
                "metadata": raw_doc.get("metadata") if isinstance(raw_doc.get("metadata"), dict) else {},
            }
        )

    if not docs:
        raise ValueError(f"No valid document entries found in RAG store: {rag_path}")
    return docs


def _tokenize_for_ranking(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", (text or "").lower())


def _select_report_documents(docs: List[Dict[str, Any]], query: Optional[str], top_k: int = 5) -> tuple[List[Dict[str, Any]], List[float]]:
    query_tokens = set(_tokenize_for_ranking(query or ""))

    ranked: List[tuple[float, Dict[str, Any]]] = []
    for doc in docs:
        content = doc.get("content", "")
        source = doc.get("source", "")
        if not query_tokens:
            score = min(len(content) / 4000.0, 1.0)
        else:
            doc_tokens = set(_tokenize_for_ranking(f"{source}\n{content}"))
            overlap = len(query_tokens & doc_tokens)
            score = overlap / max(len(query_tokens), 1)
            score += min(len(content) / 8000.0, 0.1)  # Slightly favor richer context
        ranked.append((float(score), doc))

    ranked.sort(key=lambda x: x[0], reverse=True)
    selected = ranked[: min(max(top_k, 1), len(ranked))]
    selected_docs = [doc for _, doc in selected]
    selected_scores = [max(score, 0.001) for score, _ in selected]
    return selected_docs, selected_scores


def _generate_markdown_report_from_rag_store_fallback(rag_store_path: str, query: Optional[str] = None) -> str:
    rag_path = Path(rag_store_path).expanduser().resolve()
    docs = _load_rag_documents(str(rag_path))

    from collections import Counter
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_docs = len(docs)
    lengths = [len((d.get("content") or "").strip()) for d in docs]
    non_empty = sum(1 for x in lengths if x > 0)
    avg_len = (sum(lengths) / total_docs) if total_docs else 0.0

    source_counter = Counter((d.get("source") or "Unknown") for d in docs)
    top_sources = source_counter.most_common(8)
    top_docs = sorted(docs, key=lambda d: len((d.get("content") or "")), reverse=True)[:5]

    lines: List[str] = []
    lines.append("# Research Report")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append("")

    if query:
        lines.append("## Query")
        lines.append(f"> {query}")
        lines.append("")

    lines.append("## Overview")
    lines.append(f"- **RAG Store:** `{rag_path}`")
    lines.append(f"- **Documents in Knowledge Base:** {total_docs}")
    lines.append(f"- **Non-empty Documents:** {non_empty}")
    lines.append(f"- **Average Content Length:** {avg_len:.1f} characters")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append(
        "This report is generated directly from the existing RAG knowledge base. "
        "It summarizes document coverage and highlights the most information-dense sources."
    )
    lines.append("")

    lines.append("## Key Findings")
    if top_docs:
        for i, doc in enumerate(top_docs, 1):
            source = doc.get("source", "Unknown")
            snippet = _first_sentence(doc.get("content", ""))
            lines.append(f"{i}. **{source}**")
            if snippet:
                lines.append(f"   {snippet}")
            else:
                lines.append("   (No readable content)")
    else:
        lines.append("No key findings available.")
    lines.append("")

    lines.append("## Source Distribution")
    if top_sources:
        for source, cnt in top_sources:
            lines.append(f"- **{source}**: {cnt} document(s)")
    else:
        lines.append("- No sources available.")
    lines.append("")

    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Total Sources:** {len(source_counter)}")
    lines.append(f"- **Report Type:** Markdown")
    lines.append("")

    markdown_content = "\n".join(lines)
    output_path = rag_path.parent / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path.write_text(markdown_content, encoding="utf-8")
    return str(output_path)


def _generate_markdown_report_from_rag_store(rag_store_path: str, query: Optional[str] = None) -> str:
    """
    Generate markdown report using the historical high-quality RAG report chain:
    ReportGenerationTask (two-stage LLM report synthesis) + RAG context.
    """
    from datetime import datetime
    from webis.apps.rag.tasks import ReportGenerationTask

    rag_path = Path(rag_store_path).expanduser().resolve()
    docs = _load_rag_documents(str(rag_path))

    report_query = (query or "").strip() or "Summarize key findings from this RAG knowledge base."
    selected_docs, scores = _select_report_documents(docs, report_query, top_k=5)

    context_blocks = []
    for doc, score in zip(selected_docs, scores):
        context_blocks.append(
            f"[Source: {doc.get('source', 'Unknown')}] (Relevance: {score:.2f})\n{doc.get('content', '')}"
        )
    context_text = "\n\n".join(context_blocks)

    rag_context = {
        "query": report_query,
        "retrieved_documents": selected_docs,
        "context_text": context_text,
        "structured_data": {},
        "scores": scores,
        "metadata": {
            "retrieval_count": len(selected_docs),
            "top_k": len(selected_docs),
            "webis_fetched": False,
        },
    }

    report_task = ReportGenerationTask(include_raw_data=True, output_format="markdown")
    task_result = report_task.execute(rag_context)
    if not task_result.get("success") or not task_result.get("report_content"):
        error_msg = task_result.get("error") or "unknown report generation error"
        raise RuntimeError(
            "ReportGenerationTask failed. "
            "Please check LLM API configuration/connectivity and retry. "
            f"Details: {error_msg}"
        )

    markdown_content = task_result["report_content"]
    output_path = rag_path.parent / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path.write_text(markdown_content, encoding="utf-8")
    return str(output_path)

def main():
    # 0. Auto-Init Configuration (Onboarding)
    # If .env is missing but .env.example exists, copy it and warn user.
    env_path = ".env"
    example_path = ".env.example"
    
    if not os.path.exists(env_path):
        if os.path.exists(example_path):
            print("🚀 Welcome to Webis! Initializing configuration...")
            try:
                shutil.copy(example_path, env_path)
                print(f"✅ Created {env_path} from template.")
                print("⚠️  IMPORTANT: Please edit .env and add your API keys (WENDALOG_API_KEY recommended) to proceed.")
                print("   Opening .env for you..." if sys.platform == "darwin" else "")
                
                # Optional: Open file automatically on Mac
                # if sys.platform == "darwin":
                #     os.system(f"open {env_path}")
                    
            except Exception as e:
                logger.warning(f"Failed to auto-create .env: {e}")
        else:
            logger.warning("No .env found and no .env.example template available.")

    # Load environment variables from .env
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Webis CLI v2")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run command (End-to-End)
    run_parser = subparsers.add_parser("run", help="Run end-to-end pipeline")
    run_parser.add_argument("task", help="Natural language task description")
    run_parser.add_argument("--limit", type=int, default=5, help="Max results")
    run_parser.add_argument("--output", "-o", help="Output directory")

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract structure from files")
    extract_parser.add_argument("files", nargs="+", help="Files to extract from")
    extract_parser.add_argument("--task", help="Extraction goal/task", default="Extract main information")
    extract_parser.add_argument("--schema", help="Path to JSON schema")
    extract_parser.add_argument("--output", "-o", help="Output file")

    # html-report command (from result.json + documents.json)
    html_report_parser = subparsers.add_parser("html-report", help="Generate HTML report from result.json")
    html_report_parser.add_argument("result", help="Path to result.json")
    html_report_parser.add_argument("--documents", help="Path to documents.json")
    html_report_parser.add_argument("--output", "-o", help="Output directory")

    # markdown-report command (from rag_store.json)
    markdown_report_parser = subparsers.add_parser(
        "markdown-report",
        help="Generate markdown report from rag_store.json",
    )
    markdown_report_parser.add_argument("rag_store", help="Path to rag_store.json")
    markdown_report_parser.add_argument("--query", help="Optional report focus query")

    # visualizer command
    visualizer_parser = subparsers.add_parser("visualizer", help="Launch Webis Visualizer UI (Streamlit)")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.task, args.limit, args.output)
    elif args.command == "extract":
        cmd_extract(args.files, args.task, args.schema, args.output)
    elif args.command == "html-report":
        cmd_html_report(args.result, args.documents, args.output)
    elif args.command == "markdown-report":
        cmd_markdown_report(args.rag_store, args.query)
    elif args.command == "visualizer":
        cmd_visualizer()
    else:
        parser.print_help()

def cmd_run(task: str, limit: int, output_dir: str = None):
    logger.info(f"🚀 Starting Intelligent Pipeline for: {task}")
    
    # Phase 1: Intelligent Crawling with validation
    logger.info("Phase 1: Intelligent Sourcing with Agent Validation...")
    
    from webis.core.intelligent_pipeline import IntelligentPipeline
    
    pipeline = IntelligentPipeline()
    validation_result = pipeline.run(
        query=task,
        requirements={
            'min_count': limit,
            'relevance_threshold': 0.7,
            'max_iterations': 3
        }
    )
    
    # Get validated documents
    docs = validation_result['documents']
    
    if not docs:
        logger.error("No documents found after Agent validation.")
        logger.info("Try: 1) Checking API keys, 2) Adjusting relevance threshold, 3) Increasing iterations")
        return
    
    stats = validation_result['stats']
    logger.info(f"✓ Got {stats['accepted_count']} validated documents")
    logger.info(f"  Rejected {stats['rejected_count']} irrelevant documents")
    logger.info(f"  Completed in {stats['iterations']} iteration(s)")

    # Phase 2: Processing (Additional)
    # Note: IntelligentPipeline already runs HTMLCleanerPlugin.
    # We only need to run parsers for specific file types if they weren't fully processed.
    logger.info("Phase 2: Additional Processing...")
    
    registry = get_default_registry()
    context = PipelineContext(task=task, output_dir=output_dir)
    
    processed_docs = []
    
    # Helper to run processors
    pdf_parser = registry.get_processor("pdf_extractor")
    doc_parser = registry.get_processor("document_parser")

    for doc in docs:
        # If PDF and raw content needs parsing
        if doc.doc_type == DocumentType.PDF and pdf_parser and not doc.clean_content:
             doc = pdf_parser.process(doc, context) or doc
        # If generic doc parser needed and still raw
        elif doc_parser and not doc.clean_content:
             doc = doc_parser.process(doc, context) or doc
              
        processed_docs.append(doc)

    logger.info(f"✓ Processed {len(processed_docs)} documents")

    # Phase 3: Extraction
    logger.info("Phase 3: LLM Structural Extraction...")
    extractor = registry.get_extractor("llm_extractor")
    
    extraction_result = None
    if extractor:
        extraction_result = extractor.extract(processed_docs, context)
        
        print("\n" + "="*70)
        print("EXTRACTION RESULT")
        print("="*70)
        print(json.dumps(extraction_result.data, indent=2, ensure_ascii=False))
        
    else:
        logger.warning("LLM Extractor not found. Skipping extraction.")
        
    # Phase 4: Build RAG knowledge base
    logger.info("Phase 4: Building RAG Knowledge Base...")
    
    # Determine output directory (Auto-save)
    if not output_dir:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("output", timestamp)
        
    os.makedirs(output_dir, exist_ok=True)

    # Save Full Documents (Raw & Cleaned)
    docs_path = os.path.join(output_dir, "documents.json")
    docs_data = [doc.model_dump(mode="json") for doc in processed_docs]
    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(docs_data, f, indent=2, ensure_ascii=False)
    logger.info(f"📁 Raw/Cleaned data saved to: {docs_path}")

    if extraction_result:
        # Save JSON
        json_path = os.path.join(output_dir, "result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(extraction_result.model_dump(mode="json"), indent=2, ensure_ascii=False))
        print(f"\n📁 JSON saved to:   {json_path}")
    else:
        logger.warning("No extraction result to save.")

    try:
        _build_rag_knowledge_base_from_documents(docs_path)
    except Exception as e:
        logger.error(f"Failed to build RAG knowledge base from documents.json: {e}")
        raise

def cmd_visualizer():
    project_root = Path(__file__).resolve().parents[2]
    app_path = project_root / "src" / "webis_visualizer" / "app.py"
    if not app_path.exists():
        logger.error(f"Visualizer app not found: {app_path}")
        return

    if not shutil.which("streamlit"):
        logger.error("Streamlit is not installed. Please install dependencies first.")
        return

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    logger.info("Launching Webis Visualizer...")
    subprocess.run(cmd, check=False, cwd=str(project_root))

def cmd_extract(files: List[str], task: str, schema_path: str = None, output_file: str = None):
    registry = get_default_registry()
    extractor = registry.get_extractor("llm_extractor")
    
    config = {}
    if schema_path:
        with open(schema_path) as f:
            config["schema"] = json.load(f)
            
    if schema_path:
         # Create a temporary instance with config
         from webis.plugins.extractors.llm_extractor_plugin import LLMExtractorPlugin
         extractor = LLMExtractorPlugin(config={"schema": config["schema"]})

    if not extractor:
        logger.error("LLM Extractor not found.")
        return

    docs = []
    # Load files as docs
    doc_parser = registry.get_processor("document_parser")
    pdf_parser = registry.get_processor("pdf_extractor")
    context = PipelineContext(task=task)
    
    for fp in files:
        doc = WebisDocument(content=fp, doc_type=DocumentType.UNKNOWN, meta=DocumentMetadata(title=os.path.basename(fp), custom={"file_path": fp}))
        
        # Parse
        if fp.lower().endswith(".pdf") and pdf_parser:
             doc.doc_type = DocumentType.PDF
             doc = pdf_parser.process(doc, context)
        elif doc_parser:
             doc = doc_parser.process(doc, context)
             
        if doc:
            docs.append(doc)
            
    result = extractor.extract(docs, context=context)
    print(json.dumps(result.data, indent=2, ensure_ascii=False))
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))

def cmd_html_report(result_path: str, documents_path: str = None, output_dir: str = None):
    registry = get_default_registry()
    html_plugin = registry.get_output("html_report")

    if not html_plugin:
        logger.error("HtmlReportPlugin not found.")
        return

    if not os.path.exists(result_path):
        logger.error(f"result.json not found: {result_path}")
        return

    if not output_dir:
        output_dir = os.path.dirname(result_path) or "."

    os.makedirs(output_dir, exist_ok=True)

    with open(result_path, "r") as f:
        result_data = json.load(f)
    result = StructuredResult.model_validate(result_data)

    documents = []
    if documents_path:
        if not os.path.exists(documents_path):
            logger.error(f"documents.json not found: {documents_path}")
            return
        with open(documents_path, "r") as f:
            docs_data = json.load(f)
        documents = [WebisDocument.model_validate(d) for d in docs_data]

    context = PipelineContext(task="Generate HTML report", output_dir=output_dir)
    html_plugin.save(result, context=context, output_dir=output_dir, documents=documents)
    print(f"\n✨ Report generated: {os.path.join(output_dir, 'report.html')}")


def cmd_markdown_report(rag_store_path: str, query: str = None):
    try:
        output_path = _generate_markdown_report_from_rag_store(rag_store_path, query=query)
        print(f"\n📝 Markdown report generated: {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate markdown report from RAG store: {e}")
        raise

if __name__ == "__main__":
    main()
