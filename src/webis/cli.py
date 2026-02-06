import argparse
import sys
import os
import shutil
import json
import logging
import subprocess
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from webis.core.pipeline import Pipeline
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext, StructuredResult
from webis.core.plugin import get_default_registry
from webis.core.agent.crawler_agent import CrawlerAgent

# Import plugins to register them
import webis.plugins.sources
import webis.plugins.processors
import webis.plugins.extractors
import webis.plugins.outputs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("webis.cli")

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

    # crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl data for a task")
    crawl_parser.add_argument("task", help="Task or Query")
    crawl_parser.add_argument("--limit", type=int, default=5)
    crawl_parser.add_argument("--output", "-o", help="Output file (JSON)")

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

    # visualizer command
    visualizer_parser = subparsers.add_parser("visualizer", help="Launch Webis Visualizer UI (Streamlit)")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.task, args.limit, args.output)
    elif args.command == "crawl":
        cmd_crawl(args.task, args.limit, args.output)
    elif args.command == "extract":
        cmd_extract(args.files, args.task, args.schema, args.output)
    elif args.command == "html-report":
        cmd_html_report(args.result, args.documents, args.output)
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
        
    # Phase 4: Reporting
    logger.info("Phase 4: Generating Report...")
    
    # Determine output directory (Auto-save)
    if not output_dir:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("output", timestamp)
        
    os.makedirs(output_dir, exist_ok=True)

    # Save Full Documents (Raw & Cleaned)
    if processed_docs:
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
        
        # Generate HTML Report
        html_plugin = registry.get_output("html_report")
        if html_plugin:
            html_plugin.save(extraction_result, context=context, output_dir=output_dir, documents=processed_docs)
            print(f"\n✨ Report generated: {os.path.join(output_dir, 'report.html')}")
            print(f"📁 JSON saved to:   {json_path}")
        else:
             logger.warning("HtmlReportPlugin not found.")
    else:
        logger.error("No result to save.")

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

def cmd_crawl(task: str, limit: int, output_file: str = None):
    # Align crawl outputs with run outputs under output/{timestamp}/
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", timestamp)
    default_output_file = os.path.join(output_dir, "documents.json")

    extra_output_file = None
    if output_file:
        # If a directory is provided, store documents.json inside it
        if os.path.isdir(output_file) or output_file.endswith(os.sep):
            extra_output_file = os.path.join(output_file.rstrip(os.sep), "documents.json")
        else:
            extra_output_file = output_file

    os.makedirs(output_dir, exist_ok=True)

    context = PipelineContext(task=task, output_dir=output_dir)
    agent = CrawlerAgent()
    docs = agent.run(task, limit=limit, context=context)
    
    data = [doc.model_dump(mode="json") for doc in docs]
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Always write default output to match `webis run`
    with open(default_output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(docs)} docs to {default_output_file}")

    # Extract structured result from crawled documents
    registry = get_default_registry()
    extractor = registry.get_extractor("llm_extractor")
    if extractor:
        result = extractor.extract(docs, context=context)
        json_path = os.path.join(output_dir, "result.json")
        with open(json_path, "w") as f:
            f.write(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
        print(f"\n📁 JSON saved to:   {json_path}")
    else:
        logger.warning("LLM Extractor not found. Skipping extraction.")

    # Optionally write to user-specified path for backward compatibility
    if extra_output_file:
        os.makedirs(os.path.dirname(extra_output_file) or ".", exist_ok=True)
        with open(extra_output_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(docs)} docs to {extra_output_file}")

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

if __name__ == "__main__":
    main()
