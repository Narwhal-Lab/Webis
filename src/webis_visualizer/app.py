"""
Webis Visualizer - NotebookLM-style interface for Webis pipeline
"""

import streamlit as st
import os
import sys
import json
import html as html_lib
import base64
import textwrap
from pathlib import Path

# Add parent directory to path so we can import Webis modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from webis.core.agent.crawler_agent import CrawlerAgent
from webis.core.intelligent_pipeline import IntelligentPipeline
from webis.core.schema import WebisDocument, PipelineContext
from webis.core.llm.base import get_default_router

try:
    import markdown as md
except Exception:
    md = None

BASE_DIR = Path(__file__).parent

# ------------------------------
# Configuration
# ------------------------------
st.set_page_config(
    page_title="Webis",
    page_icon=str(BASE_DIR / "assets" / "webis.svg"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# Session State Initialization
# ------------------------------
def init_session_state():
    """Initialize session state variables"""
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "structured_result" not in st.session_state:
        st.session_state.structured_result = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "pipeline_status" not in st.session_state:
        st.session_state.pipeline_status = {
            "fetch": "idle",
            "clean": "idle",
            "extract": "idle",
            "progress": 0
        }
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "data_source"
    if "queued_prompt" not in st.session_state:
        st.session_state.queued_prompt = None

# ------------------------------
# Helper Functions
# ------------------------------
def process_local_file(file):
    """Process uploaded local files"""
    from webis.core.schema import DocumentType
    
    file_type = file.type.split('/')[-1]
    
    # Simple file type detection and processing
    if file_type in ['pdf', 'application/pdf']:
        return WebisDocument(
            id=f"local-pdf-{int(os.urandom(16).hex(), 16)}",
            content=file.read(),
            doc_type=DocumentType.PDF,
            meta={
                "title": file.name,
                "source": "local_upload",
                "size": file.size
            }
        )
    elif file_type in ['text/html', 'application/xhtml+xml']:
        return WebisDocument(
            id=f"local-html-{int(os.urandom(16).hex(), 16)}",
            content=file.read(),
            doc_type=DocumentType.HTML,
            meta={
                "title": file.name,
                "source": "local_upload",
                "size": file.size
            }
        )
    elif file_type in ['text/plain', 'text/csv']:
        return WebisDocument(
            id=f"local-txt-{int(os.urandom(16).hex(), 16)}",
            content=file.read(),
            doc_type=DocumentType.TEXT,
            meta={
                "title": file.name,
                "source": "local_upload",
                "size": file.size
            }
        )
    else:
        return WebisDocument(
            id=f"local-{file_type}-{int(os.urandom(16).hex(), 16)}",
            content=file.read(),
            doc_type=DocumentType.UNKNOWN,
            meta={
                "title": file.name,
                "source": "local_upload",
                "size": file.size
            }
        )

def run_pipeline():
    """Run the full Webis pipeline"""
    if not st.session_state.documents:
        st.error("❌ No documents found. Please upload or crawl some data first.")
        return
    
    # Update pipeline status
    st.session_state.pipeline_status.update({
        "fetch": "completed",
        "clean": "in_progress",
        "extract": "idle",
        "progress": 30
    })
    
    try:
        # Initialize pipeline
        pipeline = IntelligentPipeline()
        context = PipelineContext(task="Process documents")
        
        # Run pipeline
        result = pipeline.run(
            query="Process uploaded documents",
            requirements={
                "min_count": len(st.session_state.documents),
                "relevance_threshold": 0.7
            },
            context=context
        )
        
        # Update session state
        if result.get("documents"):
            st.session_state.structured_result = result
            st.session_state.pipeline_status.update({
                "clean": "completed",
                "extract": "completed",
                "progress": 100
            })
            st.success("✅ Pipeline completed successfully!")
            
    except Exception as e:
        st.error(f"❌ Pipeline failed: {str(e)}")
        st.session_state.pipeline_status.update({
            "clean": "failed",
            "extract": "failed",
            "progress": 0
        })

# ------------------------------
# Branding Helpers
# ------------------------------
def get_logo_data_uri() -> str:
    """Return the SVG logo as a data URI for inline rendering."""
    logo_path = BASE_DIR / "assets" / "webis.svg"
    try:
        svg = logo_path.read_text(encoding="utf-8")
        svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{svg_b64}"
    except Exception:
        return ""

# ------------------------------
# AI Assistant Helpers
# ------------------------------
def format_message_html(content: str) -> str:
    """Render markdown to HTML with a safe fallback."""
    if md:
        return md.markdown(content, extensions=["extra"])
    escaped = html_lib.escape(content).replace("\n", "<br>")
    return f"<p>{escaped}</p>"


def render_chat_history(messages):
    """Render chat messages as a NotebookLM-style panel."""
    if not messages:
        st.markdown(
            "<div class=\"chat-empty\">Ask a question to get started.</div>",
            unsafe_allow_html=True
        )
        return

    rows = []
    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        body_html = format_message_html(content)
        rows.append(
            f"<div class=\"chat-bubble {role}\">"
            f"<div class=\"chat-role\">{role.title()}</div>"
            f"<div class=\"chat-content\">{body_html}</div>"
            "</div>"
        )

    history_html = "<div class=\"chat-surface\">" + "".join(rows) + "</div>"
    st.markdown(history_html, unsafe_allow_html=True)


def run_assistant(prompt: str):
    """Run assistant response and update chat history."""
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.spinner("Thinking..."):
        try:
            context = f"""
Structured data for analysis:
{json.dumps(st.session_state.structured_result, indent=2)}

User question: {prompt}
"""
            router = get_default_router()
            response = router.chat([
                {"role": "system", "content": "You are an AI analyst specializing in structured data from the Webis pipeline."},
                {"role": "user", "content": context}
            ])
            st.session_state.chat_history.append({"role": "assistant", "content": response.content})
        except Exception as e:
            st.error(f"❌ Failed to generate response: {str(e)}")

# ------------------------------
# Main App
# ------------------------------
init_session_state()

# Custom CSS
st.markdown(textwrap.dedent("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;700&display=swap');

        :root {
            --bg-1: #f2fbfb;
            --bg-2: #f3fbf1;
            --ink: #173838;
            --muted: #4a6b66;
            --accent: #31adad;
            --accent-2: #9cce7b;
            --card: #ffffff;
            --border: #d6ebe5;
            --shadow: 0 18px 40px rgba(23, 56, 56, 0.12);
        }

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--ink);
        }

        div[data-testid="stAppViewContainer"] {
            background: linear-gradient(140deg, var(--bg-1), var(--bg-2));
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(160deg, #d6efea, #d9f1d2);
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] .stButton > button {
            background: var(--accent);
            color: #ffffff;
            border: none;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: #279b9b;
            color: #ffffff;
        }

        [data-testid="stDeployButton"] {
            display: none;
        }
        [data-testid="stMainMenu"] {
            display: none;
        }
        [data-testid="stDeployButton"] {
            display: none;
        }
        a[aria-label="Deploy"] {
            display: none;
        }
        button[aria-label="Deploy"] {
            display: none;
        }
        button[title="Deploy"] {
            display: none;
        }
        button[title="Settings"] {
            display: none;
        }
        #MainMenu {
            visibility: hidden;
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"],
        header[data-testid="stHeader"] [data-testid="stToolbarActions"],
        header[data-testid="stHeader"] .stAppToolbar,
        header[data-testid="stHeader"] .stAppToolbarContainer,
        div[data-testid="stToolbar"] {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent;
            box-shadow: none;
        }
        header[data-testid="stHeader"]::after {
            background: transparent;
        }
        div[data-testid="stAppViewContainer"] .block-container {
            padding-top: 1.2rem;
        }

        h1, h2, h3, h4 {
            font-family: 'Fraunces', serif;
            letter-spacing: 0.2px;
        }

        .brand-bar {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 14px;
            border-radius: 18px;
            background: linear-gradient(120deg, rgba(49, 173, 173, 0.12), rgba(156, 206, 123, 0.12));
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            margin-bottom: 18px;
            animation: rise 0.35s ease;
        }
        .brand-mark img {
            width: 64px;
            height: 64px;
            object-fit: contain;
        }
        .brand-title {
            font-size: 1.6rem;
            font-weight: 700;
            margin: 0;
        }
        .brand-subtitle {
            font-size: 0.95rem;
            color: var(--muted);
        }

        .sidebar-title {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 14px;
            background: linear-gradient(120deg, rgba(49, 173, 173, 0.18), rgba(156, 206, 123, 0.18));
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            font-weight: 700;
            font-size: 1.1rem;
        }
        .sidebar-title span {
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.9px;
        }

        .section-title {
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 0.6rem;
        }
        .section-gap {
            height: 18px;
        }

        .status-dot {
            height: 8px;
            width: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .status-idle { background-color: #b9b4ac; }
        .status-in-progress { background-color: var(--accent); }
        .status-completed { background-color: #2f855a; }
        .status-failed { background-color: #c53030; }

        .stat-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin: 10px 0 20px;
        }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: var(--shadow);
            animation: rise 0.35s ease;
        }
        .stat-label {
            color: var(--muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stat-value {
            font-size: 1.6rem;
            font-weight: 700;
            margin-top: 6px;
        }

        .pipeline-board {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: var(--shadow);
            animation: rise 0.4s ease;
        }
        .pipeline-title {
            font-weight: 700;
            font-size: 1.05rem;
        }
        .progress-shell {
            height: 10px;
            border-radius: 999px;
            background: #e5f4f1;
            overflow: hidden;
            margin-top: 12px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
            border-radius: 999px;
            transition: width 0.3s ease;
        }
        .pipeline-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-top: 18px;
        }
        .pipeline-step {
            border-radius: 16px;
            padding: 14px 16px;
            border: 1px solid var(--border);
            background: #f8fffc;
            animation: rise 0.35s ease;
        }
        .pipeline-step.completed { border-left: 4px solid #2f855a; }
        .pipeline-step.in-progress { border-left: 4px solid var(--accent); }
        .pipeline-step.failed { border-left: 4px solid #c53030; }
        .pipeline-step.idle { border-left: 4px solid #b9b4ac; }
        .step-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .step-title {
            font-weight: 600;
            flex: 1;
        }
        .step-status {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--muted);
        }
        .step-desc {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 6px;
        }

        .chat-surface {
            background: #f8fffc;
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 16px;
            max-height: 58vh;
            overflow-y: auto;
            box-shadow: var(--shadow);
        }
        .chat-bubble {
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
            background: #ffffff;
            animation: rise 0.3s ease;
        }
        .chat-bubble.user {
            margin-left: 18%;
            background: #e4f7f4;
            border-color: #b7e6dd;
        }
        .chat-bubble.assistant {
            margin-right: 18%;
        }
        .chat-role {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--muted);
            margin-bottom: 6px;
        }
        .chat-content {
            line-height: 1.5;
        }
        .chat-empty {
            color: var(--muted);
            background: #f8fffc;
            border: 1px dashed var(--border);
            border-radius: 14px;
            padding: 16px;
        }
        .side-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: var(--shadow);
            margin-bottom: 14px;
        }
        .side-card h4 {
            margin: 0 0 10px;
            font-size: 1rem;
        }
        .source-row {
            padding: 8px 0;
            border-bottom: 1px dashed #e6e0d7;
        }
        .source-row:last-child {
            border-bottom: none;
        }
        .source-title {
            font-weight: 600;
            font-size: 0.9rem;
        }
        .source-meta {
            color: var(--muted);
            font-size: 0.8rem;
        }

        @keyframes rise {
            from { transform: translateY(6px); opacity: 0.0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
"""), unsafe_allow_html=True)

logo_uri = get_logo_data_uri()
st.markdown(
    textwrap.dedent(f"""
        <div class="brand-bar">
            <div class="brand-mark">
                <img src="{logo_uri}" alt="Webis logo"/>
            </div>
            <div>
                <div class="brand-title">Webis</div>
            </div>
        </div>
    """),
    unsafe_allow_html=True
)

# ------------------------------
# Sidebar - Data Source Management
# ------------------------------
st.sidebar.markdown(
    "<div class=\"sidebar-title\">📁 Data Sources</div>",
    unsafe_allow_html=True
)

# Single page for data sources
st.sidebar.subheader("🔍 Web Crawling")

query = st.sidebar.text_input("Search Query", placeholder="Enter your search query...")
limit = st.sidebar.slider("Number of Results", min_value=1, max_value=10, value=3)

if st.sidebar.button("🚀 Start Crawling"):
    if query:
        with st.spinner(f"Crawling for: {query}..."):
            agent = CrawlerAgent()
            docs = agent.run(query, limit=limit)
            
            # Update session state
            st.session_state.documents = docs
            st.session_state.pipeline_status["fetch"] = "completed"
            st.session_state.pipeline_status["progress"] = 30
            st.success(f"✅ Crawled {len(docs)} documents")
    else:
        st.error("❌ Please enter a search query")

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Local Upload")

uploaded_files = st.sidebar.file_uploader(
    "Upload Files",
    accept_multiple_files=True,
    type=["pdf", "html", "txt", "csv", "md"]
)

if st.sidebar.button("📋 Process Uploaded Files"):
    if uploaded_files:
        with st.spinner("Processing uploaded files..."):
            local_docs = []
            for file in uploaded_files:
                doc = process_local_file(file)
                local_docs.append(doc)
            
            # Update session state
            st.session_state.documents.extend(local_docs)
            st.session_state.pipeline_status["fetch"] = "completed"
            st.session_state.pipeline_status["progress"] = 30
            st.success(f"✅ Processed {len(local_docs)} local files")
    else:
        st.error("❌ Please upload some files first")

# ------------------------------
# Main Content Area
# ------------------------------
tab1, tab3 = st.tabs([
    "📊 Pipeline Dashboard", 
    "💬 AI Assistant"
])

with tab1:
    st.header("Pipeline Dashboard")

    progress = st.session_state.pipeline_status["progress"]
    doc_count = len(st.session_state.documents)
    structured_count = 0
    if st.session_state.structured_result:
        structured_count = len(st.session_state.structured_result.get("documents", []))

    st.markdown(
        textwrap.dedent(f"""
            <div class="stat-row">
                <div class="stat-card">
                    <div class="stat-label">Raw Documents</div>
                    <div class="stat-value">{doc_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Structured Records</div>
                    <div class="stat-value">{structured_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Pipeline Progress</div>
                    <div class="stat-value">{progress}%</div>
                </div>
            </div>
        """),
        unsafe_allow_html=True
    )

    step_defs = [
        ("fetch", "Data Acquisition", "Crawl or upload sources into the workspace."),
        ("clean", "Cleaning and Normalization", "Remove noise, parse content, and unify formats."),
        ("extract", "Structured Knowledge Base", "Extract entities, relations, and summaries.")
    ]

    def status_label(status):
        labels = {
            "idle": "Idle",
            "in_progress": "In progress",
            "completed": "Completed",
            "failed": "Failed"
        }
        return labels.get(status, status)

    step_blocks = []
    for key, title, desc in step_defs:
        status = st.session_state.pipeline_status.get(key, "idle")
        status_css = status.replace("_", "-")
        step_blocks.append(textwrap.dedent(f"""
            <div class="pipeline-step {status_css}">
                <div class="step-header">
                    <span class="status-dot status-{status_css}"></span>
                    <span class="step-title">{title}</span>
                    <span class="step-status">{status_label(status)}</span>
                </div>
                <div class="step-desc">{desc}</div>
            </div>
        """).strip())
    steps_html = "\n".join(step_blocks)

    st.markdown(
        textwrap.dedent(f"""
            <div class="pipeline-board">
                <div class="pipeline-title">Pipeline Flow</div>
                <div class="progress-shell">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
                <div class="pipeline-grid">
                    {steps_html}
                </div>
            </div>
        """).strip(),
        unsafe_allow_html=True
    )

    st.markdown("<div class=\"section-gap\"></div>", unsafe_allow_html=True)

    if st.session_state.documents:
        st.caption(f"Found {len(st.session_state.documents)} documents ready for processing.")

        st.subheader("Document Preview")
        for i, doc in enumerate(st.session_state.documents[:3]):
            with st.expander(f"Document {i+1}: {doc.meta.title or doc.id[:20]}..."):
                st.write(f"**Type:** {doc.doc_type.value}")
                st.write(f"**Source:** {doc.meta.source_plugin or 'Local Upload'}")
                if doc.clean_content:
                    st.text_area("Preview", doc.clean_content[:500] + "...", height=150)
                else:
                    st.text_area("Preview", doc.content[:500] + "...", height=150)

    if st.button("▶️ Run Full Pipeline", disabled=st.session_state.pipeline_status["progress"] == 100):
        run_pipeline()

with tab3:
    st.header("AI Assistant")
    
    if not st.session_state.structured_result:
        st.info("ℹ️ No data available for AI analysis. Run the pipeline first.")
    else:
        left, right = st.columns([2.2, 1], gap="large")

        with right:
            stats = st.session_state.structured_result.get("stats", {})
            doc_count = len(st.session_state.documents)
            structured_count = len(st.session_state.structured_result.get("documents", []))

            st.markdown(
                textwrap.dedent(f"""
                    <div class="side-card">
                        <h4>Notebook Context</h4>
                        <div class="source-meta">Raw documents: {doc_count}</div>
                        <div class="source-meta">Structured records: {structured_count}</div>
                        <div class="source-meta">Accepted / Rejected: {stats.get("accepted_count", 0)} / {stats.get("rejected_count", 0)}</div>
                        <div class="source-meta">Iterations: {stats.get("iterations", 0)}</div>
                    </div>
                """),
                unsafe_allow_html=True
            )

            sources = st.session_state.documents[:6]
            source_rows = ""
            if sources:
                for doc in sources:
                    title = doc.meta.title or doc.id[:16]
                    source = doc.meta.source_plugin or "Local Upload"
                    source_rows += f"""
                    <div class="source-row">
                        <div class="source-title">{title}</div>
                        <div class="source-meta">{source}</div>
                    </div>
                    """
            else:
                source_rows = "<div class=\"source-meta\">No sources yet.</div>"

            st.markdown(
                textwrap.dedent(f"""
                    <div class="side-card">
                        <h4>Sources</h4>
                        {source_rows}
                    </div>
                """),
                unsafe_allow_html=True
            )

            st.markdown(
                textwrap.dedent("<div class=\"side-card\"><h4>Suggested prompts</h4></div>"),
                unsafe_allow_html=True
            )
            suggestions = [
                "Summarize the key themes from the knowledge base.",
                "List the most important entities and relationships.",
                "Create a concise brief I can share with my team.",
                "Highlight gaps or missing information."
            ]
            for suggestion in suggestions:
                if st.button(suggestion, key=f"suggest-{suggestion}"):
                    st.session_state.queued_prompt = suggestion

        with left:
            st.markdown(
                textwrap.dedent("<div class=\"section-title\">Notebook Assistant</div>"),
                unsafe_allow_html=True
            )
            st.caption("Ask questions, request summaries, or build a knowledge map from your structured data.")

            chat_container = st.container()
            prompt = st.chat_input("Ask about your data, request summaries, or explore patterns...")
            prompt_to_run = st.session_state.pop("queued_prompt", None)

            if prompt:
                prompt_to_run = prompt

            if prompt_to_run:
                run_assistant(prompt_to_run)

            with chat_container:
                render_chat_history(st.session_state.chat_history)

# ------------------------------
# Footer
# ------------------------------
st.markdown("---")
st.caption("🚀 Webis Visualizer - powered by Webis AI Pipeline")
