"""
RAG Tasks Module - Task Framework for Downstream Processing

Defines task interface and concrete task implementations that operate on RAG retrieval results.
Tasks are plugins that can be chained together to process retrieved documents.
"""

from typing import Any, Dict, List, Optional
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RAGTask(ABC):
    """
    Base class for RAG downstream tasks.
    
    A task receives retrieval context from RAG pipeline and produces outputs
    that can be consumed by the next task or the end user.
    """
    
    def __init__(self, task_name: str):
        """
        Initialize task.
        
        Args:
            task_name: Unique task identifier
        """
        self.task_name = task_name
    
    @abstractmethod
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task on RAG retrieval context.
        
        Args:
            rag_context: Context dict from RAG pipeline containing:
                - query: str
                - retrieved_documents: [...]
                - context_text: str
                - structured_data: {...}
                - scores: [float]
                - metadata: {...}
                
        Returns:
            Task-specific output dict
        """
        raise NotImplementedError
    
    def get_name(self) -> str:
        """Get task name"""
        return self.task_name


class PromptEnhancementTask(RAGTask):
    """
    Task: Enhance prompt with RAG context for LLM/Agent.
    
    Takes retrieval results and formats them into an enhanced prompt
    that can be passed to downstream agents for structured extraction
    or answer generation.
    """
    
    def __init__(self, llm_agent=None):
        """
        Initialize prompt enhancement task.
        
        Args:
            llm_agent: Optional LLM/extraction agent for executing enhanced prompt
        """
        super().__init__("prompt_enhancement")
        self.llm_agent = llm_agent
    
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute prompt enhancement task.
        
        Args:
            rag_context: RAG retrieval context
            
        Returns:
            {
                "task_name": "prompt_enhancement",
                "success": bool,
                "enhanced_prompt": str,
                "reference_count": int,
                "agent_result": {...} (optional if agent provided)
            }
        """
        query = rag_context.get("query", "")
        context_text = rag_context.get("context_text", "")
        structured_data = rag_context.get("structured_data", {})
        
        # Format structured data
        structured_text = ""
        if structured_data:
            structured_parts = []
            for key, data in structured_data.items():
                if isinstance(data, dict):
                    formatted_data = "\n".join(f"  - {k}: {v}" for k, v in data.items())
                    structured_parts.append(f"**{key}**:\n{formatted_data}")
                else:
                    structured_parts.append(f"**{key}**: {data}")
            structured_text = "\n\n".join(structured_parts)
        
        # Build enhanced prompt
        if context_text or structured_text:
            enhanced_prompt = f"""## Reference Information (Prior Knowledge from Data Pipeline)

You have access to the following retrieved documents and structured insights from our knowledge base. Use this information to provide accurate, well-informed responses.

### Retrieved Documents:
{context_text or "No relevant documents found."}

### Structured Data Insights:
{structured_text or "No structured data available."}

---

## User Query

{query}

### Instructions for Response:
- Reference the provided documents and structured data when relevant.
- Provide detailed, evidence-based answers using the prior knowledge above.
- Maintain consistency with the retrieved information."""
        else:
            enhanced_prompt = query
        
        result = {
            "task_name": self.get_name(),
            "success": True,
            "enhanced_prompt": enhanced_prompt,
            "reference_count": len(rag_context.get("retrieved_documents", [])),
            "query": query,
        }
        
        # Execute agent if provided
        if self.llm_agent:
            try:
                logger.info("Executing LLM agent with enhanced prompt...")
                agent_result = self.llm_agent.extract(
                    prompt=enhanced_prompt,
                    text="",
                    output_format="markdown"
                )
                
                result["agent_result"] = {
                    "success": agent_result.success,
                    "output_format": agent_result.output_format,
                    "parsed": agent_result.parsed,
                    "raw": agent_result.raw,
                    "error": agent_result.error,
                }
            except Exception as e:
                logger.warning(f"Failed to execute agent: {e}")
                result["agent_result"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result


class DocumentExtractionTask(RAGTask):
    """
    Task: Extract specific information from retrieved documents.
    
    Focuses on extracting structured information from the retrieved
    document context without LLM processing.
    """
    
    def __init__(self, extraction_schema: Optional[Dict[str, Any]] = None):
        """
        Initialize document extraction task.
        
        Args:
            extraction_schema: Schema for extraction (optional)
        """
        super().__init__("document_extraction")
        self.extraction_schema = extraction_schema or {
            "documents": ["title", "content", "source"],
            "structured_data": "all"
        }
    
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured information from documents.
        
        Args:
            rag_context: RAG retrieval context
            
        Returns:
            {
                "task_name": "document_extraction",
                "success": bool,
                "extracted_documents": [...],
                "extracted_data": {...},
                "query": str
            }
        """
        documents = rag_context.get("retrieved_documents", [])
        structured_data = rag_context.get("structured_data", {})
        
        extracted_docs = []
        for doc in documents:
            extracted_doc = {
                "source": doc.get("source"),
                "content": doc.get("content", "")[:500],  # Truncate long content
                "structured_data": doc.get("structured_data"),
            }
            extracted_docs.append(extracted_doc)
        
        return {
            "task_name": self.get_name(),
            "success": True,
            "extracted_documents": extracted_docs,
            "extracted_data": structured_data,
            "query": rag_context.get("query", ""),
            "document_count": len(extracted_docs),
        }


class SummaryTask(RAGTask):
    """
    Task: Generate summary of retrieved documents.
    
    Creates a concise summary of the retrieved context for quick overview.
    """
    
    def __init__(self, max_summary_length: int = 500):
        """
        Initialize summary task.
        
        Args:
            max_summary_length: Maximum length of summary text
        """
        super().__init__("summarization")
        self.max_summary_length = max_summary_length
    
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary of retrieved documents.
        
        Args:
            rag_context: RAG retrieval context
            
        Returns:
            {
                "task_name": "summarization",
                "success": bool,
                "summary": str,
                "source_count": int,
                "key_points": [str]
            }
        """
        documents = rag_context.get("retrieved_documents", [])
        context_text = rag_context.get("context_text", "")
        
        # Extract first part as summary
        if context_text:
            summary = context_text[:self.max_summary_length]
            if len(context_text) > self.max_summary_length:
                summary += "..."
        else:
            summary = "No documents retrieved."
        
        # Extract key points from structured data
        key_points = []
        structured_data = rag_context.get("structured_data", {})
        for key, data in structured_data.items():
            if isinstance(data, dict) and "summary" in data:
                key_points.append(data["summary"])
            elif isinstance(data, dict) and "key_points" in data:
                key_points.extend(data.get("key_points", []))
        
        return {
            "task_name": self.get_name(),
            "success": True,
            "summary": summary,
            "source_count": len(documents),
            "key_points": key_points[:5],  # Top 5 key points
        }


class ReportGenerationTask(RAGTask):
    """
    Task: Generate Markdown/PDF reports from RAG context.
    
    Creates comprehensive reports combining retrieved documents,
    structured data, and optional LLM-generated analysis.
    """
    
    def __init__(self, llm=None, include_raw_data: bool = False, output_format: str = "markdown"):
        """
        Initialize report generation task.
        
        Args:
            llm: Optional LLM for content generation
            include_raw_data: Include raw retrieval data in report
            output_format: 'markdown' or 'pdf'
        """
        super().__init__("report_generation")
        self.llm = llm
        self.include_raw_data = include_raw_data
        self.output_format = output_format
    
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate report from RAG context.
        
        Args:
            rag_context: RAG retrieval context
            
        Returns:
            {
                "task_name": "report_generation",
                "success": bool,
                "report_content": str,
                "report_format": str,
                "output_path": str (if saved),
                "stats": {...}
            }
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            query = rag_context.get("query", "")
            retrieved_docs = rag_context.get("retrieved_documents", [])
            context_text = rag_context.get("context_text", "")
            metadata = rag_context.get("metadata", {})
            scores = rag_context.get("scores", [])
            
            # Build markdown content
            markdown_lines = []
            
            # Header
            markdown_lines.append("# Research Report")
            markdown_lines.append("")
            markdown_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_lines.append("")
            
            # Query
            markdown_lines.append("## Query")
            markdown_lines.append(f"> {query}")
            markdown_lines.append("")
            
            # Metadata
            markdown_lines.append("## Overview")
            markdown_lines.append(
                f"- **Documents Retrieved:** {metadata.get('retrieval_count', 0)}\n"
                f"- **Webis Fetched:** {'Yes' if metadata.get('webis_fetched') else 'No'}\n"
                f"- **Top Relevance Score:** {max(scores) if scores else 'N/A':.3f}"
            )
            markdown_lines.append("")
            
            # Executive Summary
            markdown_lines.append("## Executive Summary")
            if self.llm and retrieved_docs:
                try:
                    summary = self._generate_summary(query, retrieved_docs)
                    markdown_lines.append(summary)
                except Exception as e:
                    logger.warning(f"LLM summary generation failed: {e}")
                    markdown_lines.append(self._extract_summary_from_docs(retrieved_docs))
            else:
                markdown_lines.append(self._extract_summary_from_docs(retrieved_docs))
            markdown_lines.append("")
            
            # Detailed Findings
            markdown_lines.append("## Detailed Findings")
            if self.llm and retrieved_docs:
                try:
                    detailed = self._generate_detailed_content(query, retrieved_docs)
                    markdown_lines.append(detailed)
                except Exception as e:
                    logger.warning(f"LLM content generation failed: {e}")
                    markdown_lines.append(self._format_documents_concise(retrieved_docs))
            else:
                markdown_lines.append(self._format_documents_concise(retrieved_docs))
            markdown_lines.append("")
            
            # Key Findings
            markdown_lines.append("## Key Findings")
            if self.llm and retrieved_docs:
                try:
                    findings = self._extract_key_findings(query, retrieved_docs)
                    for finding in findings:
                        markdown_lines.append(f"- {finding}")
                except Exception as e:
                    logger.warning(f"Failed to extract findings: {e}")
                    findings = self._extract_key_findings_simple(retrieved_docs)
                    for finding in findings:
                        markdown_lines.append(f"- {finding}")
            else:
                findings = self._extract_key_findings_simple(retrieved_docs)
                for finding in findings:
                    markdown_lines.append(f"- {finding}")
            markdown_lines.append("")
            
            # Source References
            markdown_lines.append("## Source References")
            markdown_lines.append("")
            for i, (doc, score) in enumerate(zip(retrieved_docs, scores), 1):
                source = doc.get("source", "Unknown")
                content_preview = doc.get("content", "")[:80]  # Shorter preview
                markdown_lines.append(f"[{i}] **{source}** (Relevance: {score:.3f})")
                markdown_lines.append(f"    {content_preview}...")
                markdown_lines.append("")
            
            # Raw Data (optional)
            if self.include_raw_data:
                markdown_lines.append("## Raw Data")
                markdown_lines.append("")
                markdown_lines.append("### Retrieved Context")
                markdown_lines.append("```")
                markdown_lines.append(context_text[:500])
                markdown_lines.append("```")
                markdown_lines.append("")
            
            # Metadata
            markdown_lines.append("## Metadata")
            markdown_lines.append("")
            markdown_lines.append(f"- **Query:** {query}")
            markdown_lines.append(f"- **Documents Retrieved:** {metadata.get('retrieval_count', 0)}")
            markdown_lines.append(f"- **Top-K Setting:** {metadata.get('top_k', 'N/A')}")
            markdown_lines.append(f"- **Webis Fetched:** {'Yes' if metadata.get('webis_fetched') else 'No'}")
            markdown_lines.append("")
            
            markdown_content = "\n".join(markdown_lines)
            
            # Try to save file
            output_path = None
            try:
                output_dir = Path(".") / "data"
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if self.output_format == "pdf":
                    output_path = output_dir / f"report_{timestamp}.pdf"
                    self._generate_pdf(markdown_content, output_path)
                else:
                    output_path = output_dir / f"report_{timestamp}.md"
                    output_path.write_text(markdown_content, encoding="utf-8")
                
                logger.info(f"✓ Report saved to {output_path}")
            except Exception as e:
                logger.warning(f"Failed to save report: {e}")
            
            return {
                "task_name": self.get_name(),
                "success": True,
                "report_content": markdown_content,
                "report_format": self.output_format,
                "output_path": str(output_path) if output_path else None,
                "stats": {
                    "documents_count": len(retrieved_docs),
                    "content_length": len(markdown_content),
                    "has_llm": self.llm is not None,
                }
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "task_name": self.get_name(),
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """Generate concise summary using LLM with source attribution."""
        if not self.llm:
            return self._extract_summary_from_docs(documents)
        
        try:
            # Prepare document chunks with source info
            doc_chunks = []
            for doc in documents[:5]:  # Top 5 docs only
                source = doc.get("source", "Unknown")
                content = doc.get("content", "")[:300]  # Limit to 300 chars per doc
                doc_chunks.append(f"[Source: {source}]\n{content}")
            
            docs_text = "\n\n".join(doc_chunks)
            
            prompt = f"""You are a professional information analyst. Your task is to synthesize the retrieved documents to produce a concise yet insightful analytical report in response to the user's query.

**User Query:** {query}

**Retrieved Context:**
{docs_text}

**Instructions for Analysis & Synthesis:**
1. **Deep Analysis:** Cross-reference information across documents. Identify the core arguments, supporting evidence, key data points, and any notable contradictions or gaps.
2. **Value-Driven Synthesis:** Do not simply list or rephrase points. Synthesize information to extract high-value insights, conclusions, or implications that are directly relevant to the query.
3. **Prioritize & Condense:** Focus on the most significant and relevant information. The output must be information-dense and avoid any filler language.

**Report Format Requirements:**
- **Overall Analysis Tone:** Authoritative, clear, and concise.
- **Structure:**
  1. **Executive Summary:** Start with 1-2 sentences that directly answer the query at a high level.
  2. **Key Findings:** Present 2-4 synthesized insights. Each finding must:
     - Be a standalone, valuable takeaway.
     - Be supported by specific details (e.g., data, reasoning) from the documents.
     - **Explicitly cite the source document(s) in brackets [Source: Document Name]** after the relevant detail.
  3. **Conclusion:** Provide a final, summative remark on the implications or state of knowledge regarding the query based on the synthesis.

**Output Only** the final analytical report according to the specified format."""
            
            if hasattr(self.llm, 'chat'):
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=300,
                )
                return response.get("content", "") if isinstance(response, dict) else str(response)
            elif hasattr(self.llm, 'invoke'):  # LangChain compatibility
                from langchain_core.messages import HumanMessage
                response = self.llm.invoke([HumanMessage(content=prompt)])
                return response.content if hasattr(response, 'content') else str(response)
            elif hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt, max_length=300)
            else:
                return self._extract_summary_from_docs(documents)
        except Exception as e:
            logger.warning(f"LLM summary failed: {e}")
            return self._extract_summary_from_docs(documents)
    
    def _generate_detailed_content(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """Generate detailed analysis using LLM with source attribution."""
        if not self.llm:
            return self._format_documents_concise(documents)
        
        try:
            # Prepare high-quality document chunks
            doc_chunks = []
            for doc in documents[:3]:  # Top 3 docs for detailed analysis
                source = doc.get("source", "Unknown")
                content = doc.get("content", "")[:400]
                doc_chunks.append(f"[Source: {source}]\n{content}")
            
            docs_text = "\n\n".join(doc_chunks)
            
            prompt = f"""Based on the following retrieved documents, provide a structured analysis of the query. Please:
1. Extract key information points (concise, remove redundancy)
2. Identify viewpoint differences across documents (if any)
3. Summarize main trends or conclusions
Every piece of information must cite its source.

Query: {query}

Document Content:
{docs_text}

Analysis Format:
[Source: Document Name] Information content
[Source: Document Name] Information content

Detailed Analysis:"""
            
            if hasattr(self.llm, 'chat'):
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500,
                )
                return response.get("content", "") if isinstance(response, dict) else str(response)
            elif hasattr(self.llm, 'invoke'):  # LangChain compatibility
                from langchain_core.messages import HumanMessage
                response = self.llm.invoke([HumanMessage(content=prompt)])
                return response.content if hasattr(response, 'content') else str(response)
            else:
                return self._format_documents_concise(documents)
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return self._format_documents_concise(documents)
    
    def _extract_key_findings(self, query: str, documents: List[Dict[str, Any]]) -> List[str]:
        """Extract key findings with source attribution."""
        if not self.llm:
            return self._extract_key_findings_simple(documents)
        
        try:
            doc_chunks = []
            for doc in documents[:4]:
                source = doc.get("source", "Unknown")
                content = doc.get("content", "")[:300]
                doc_chunks.append(f"[Source: {source}]\n{content}")
            
            docs_text = "\n\n".join(doc_chunks)
            
            prompt = f"""Extract the 5 most critical findings or key points about "{query}" from the following documents.

Requirements:
1. Each finding must be concise and clear (one sentence)
2. Each finding must cite its source document
3. Avoid repetition or generic statements
4. Sort by importance

Documents:
{docs_text}

Key Findings List Format:
[Source: Document Name] Finding content

Key Findings:"""
            
            if hasattr(self.llm, 'chat'):
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=400,
                )
                content = response.get("content", "") if isinstance(response, dict) else str(response)
            elif hasattr(self.llm, 'invoke'):  # LangChain compatibility
                from langchain_core.messages import HumanMessage
                response = self.llm.invoke([HumanMessage(content=prompt)])
                content = response.content if hasattr(response, 'content') else str(response)
            else:
                return self._extract_key_findings_simple(documents)
            
            # Parse findings from response
            findings = []
            for line in content.split('\n'):
                line = line.strip()
                if line and ('[Source' in line or line[0].isdigit()):
                    findings.append(line)
            
            return findings[:5]
        except Exception as e:
            logger.warning(f"LLM findings extraction failed: {e}")
            return self._extract_key_findings_simple(documents)
    
    def _extract_key_findings_simple(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Simple fallback for key findings extraction."""
        findings = []
        for i, doc in enumerate(documents[:5], 1):
            source = doc.get("source", "Unknown")
            content = doc.get("content", "")
            
            # Extract first meaningful sentence
            sentences = content.split('.')
            for sentence in sentences:
                clean = sentence.strip()
                if len(clean) > 20 and len(clean) < 150:
                    findings.append(f"[Source: {source}] {clean}")
                    break
        
        return findings[:5]
    
    def _extract_summary(self, context: str, length: int = 300) -> str:
        """Extract summary from context."""
        if len(context) > length:
            return context[:length] + "..."
        return context
    
    def _extract_summary_from_docs(self, documents: List[Dict[str, Any]]) -> str:
        """Extract summary from documents without LLM."""
        summaries = []
        for doc in documents[:3]:
            source = doc.get("source", "Unknown")
            content = doc.get("content", "")
            
            # Get first 150 chars as summary
            preview = content[:150] if len(content) > 150 else content
            summaries.append(f"[Source: {source}] {preview}")
        
        return "\n\n".join(summaries)
    
    def _format_documents_concise(self, documents: List[Dict[str, Any]]) -> str:
        """Format documents into concise readable text with source attribution."""
        lines = []
        
        for i, doc in enumerate(documents[:5], 1):  # Limit to top 5
            source = doc.get("source", "Unknown")
            content = doc.get("content", "")
            
            # Extract key sentences (first 2-3 sentences max)
            sentences = content.split('.')
            key_content = ""
            for sentence in sentences[:2]:
                if sentence.strip():
                    key_content += sentence.strip() + "."
            
            if not key_content:
                key_content = content[:200]
            
            lines.append(f"### [Source: {source}]")
            lines.append(key_content if len(key_content) <= 300 else key_content[:300] + "...")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_pdf(self, markdown_content: str, output_path) -> bool:
        """Try to generate PDF from markdown."""
        try:
            import markdown2
            import pdfkit
            
            html_content = markdown2.markdown(markdown_content)
            pdfkit.from_string(html_content, str(output_path))
            return True
        except ImportError:
            logger.warning("markdown2 or pdfkit not installed, saving as markdown only")
            return False
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")
            return False


class TaskPipeline:
    """
    Task Pipeline - Orchestrates execution of multiple RAG tasks.
    
    Allows chaining tasks together where each task receives the output
    of the previous task (plus the original RAG context).
    """
    
    def __init__(self):
        """Initialize task pipeline"""
        self.tasks: List[RAGTask] = []
    
    def add_task(self, task: RAGTask) -> "TaskPipeline":
        """
        Add task to pipeline.
        
        Args:
            task: RAGTask instance
            
        Returns:
            Self for chaining
        """
        self.tasks.append(task)
        logger.info(f"Added task: {task.get_name()}")
        return self
    
    def execute(self, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all tasks in pipeline.
        
        Args:
            rag_context: Initial RAG retrieval context
            
        Returns:
            {
                "query": str,
                "rag_context": {...},
                "task_results": [...],
                "success": bool
            }
        """
        if not self.tasks:
            logger.warning("No tasks in pipeline")
            return {
                "query": rag_context.get("query", ""),
                "rag_context": rag_context,
                "task_results": [],
                "success": False
            }
        
        task_results = []
        for task in self.tasks:
            try:
                logger.info(f"Executing task: {task.get_name()}")
                result = task.execute(rag_context)
                task_results.append(result)
            except Exception as e:
                logger.error(f"Task {task.get_name()} failed: {e}")
                task_results.append({
                    "task_name": task.get_name(),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "query": rag_context.get("query", ""),
            "rag_context": rag_context,
            "task_results": task_results,
            "success": all(r.get("success", False) for r in task_results if "success" in r)
        }
