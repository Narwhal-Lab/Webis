"""
Webis Visualizer - NotebookLM-style interface for Webis pipeline
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import json
import html as html_lib
import base64
import textwrap
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import logging

# Add parent directory to path so we can import Webis modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from webis.core.schema import WebisDocument
from webis.core.llm.base import get_default_router

try:
    import markdown as md
except Exception:
    md = None

BASE_DIR = Path(__file__).parent
QUERY_HISTORY_FILE = BASE_DIR / "query_output_history.jsonl"
logger = logging.getLogger("webis.visualizer")

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
    if "last_output_dir" not in st.session_state:
        st.session_state.last_output_dir = None
    if "selected_output_dir" not in st.session_state:
        st.session_state.selected_output_dir = None
    if "output_folder_select" not in st.session_state:
        st.session_state.output_folder_select = None
    if "html_report_status" not in st.session_state:
        st.session_state.html_report_status = "idle"
    if "html_report_pending" not in st.session_state:
        st.session_state.html_report_pending = False
    if "html_report_html" not in st.session_state:
        st.session_state.html_report_html = None
    if "html_report_target_dir" not in st.session_state:
        st.session_state.html_report_target_dir = None
    if "html_report_last_dir" not in st.session_state:
        st.session_state.html_report_last_dir = None
    if "pending_select_dir" not in st.session_state:
        st.session_state.pending_select_dir = None
    if "html_report_link" not in st.session_state:
        st.session_state.html_report_link = None
    if "markdown_report_status" not in st.session_state:
        st.session_state.markdown_report_status = "idle"
    if "markdown_report_pending" not in st.session_state:
        st.session_state.markdown_report_pending = False
    if "markdown_report_last_dir" not in st.session_state:
        st.session_state.markdown_report_last_dir = None
    if "crawl_proc" not in st.session_state:
        st.session_state.crawl_proc = None
    if "crawl_query" not in st.session_state:
        st.session_state.crawl_query = None
    if "crawl_limit" not in st.session_state:
        st.session_state.crawl_limit = None
    if "crawl_before_dirs" not in st.session_state:
        st.session_state.crawl_before_dirs = None
    if "history_compacted" not in st.session_state:
        st.session_state.history_compacted = False

    # Auto-discover latest output dir with result.json if not set
    if st.session_state.last_output_dir is None:
        repo_root = Path(__file__).parent.parent.parent
        output_root = repo_root / "output"
        if output_root.exists():
            candidates = [
                p for p in output_root.iterdir()
                if p.is_dir() and (p / "result.json").exists()
            ]
            if candidates:
                latest = max(candidates, key=lambda p: p.stat().st_mtime)
                st.session_state.last_output_dir = str(latest)

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

def _find_latest_output_dir(output_root: Path) -> Path | None:
    if not output_root.exists():
        return None
    dirs = [p for p in output_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)

def _append_query_history_record(
    query: str,
    limit: int,
    output_dir: Path | None,
    status: str,
    error: str | None = None,
) -> None:
    """Append one query-output mapping record for visualizer crawl/run actions."""
    try:
        QUERY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "query": query,
            "limit": limit,
            "status": status,
            "output_dir": str(output_dir.resolve()) if output_dir else None,
        }
        if error:
            record["error"] = error
        with QUERY_HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # History logging should never break the UI flow, but keep an explicit trace in terminal.
        logger.exception("Failed to append query history record to %s", QUERY_HISTORY_FILE)


def _compact_query_history_file() -> None:
    """Keep only final records in history file (completed/failed), dropping legacy started rows."""
    try:
        if not QUERY_HISTORY_FILE.exists():
            return
        kept_lines = []
        with QUERY_HISTORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                if record.get("status") in {"completed", "failed"}:
                    kept_lines.append(json.dumps(record, ensure_ascii=False))
        with QUERY_HISTORY_FILE.open("w", encoding="utf-8") as f:
            for line in kept_lines:
                f.write(line + "\n")
    except Exception:
        logger.exception("Failed to compact query history file: %s", QUERY_HISTORY_FILE)


def _load_output_query_mapping() -> dict[str, str]:
    """Load mapping from output folder name to query text from history file."""
    mapping: dict[str, str] = {}
    try:
        if not QUERY_HISTORY_FILE.exists():
            return mapping
        with QUERY_HISTORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                if record.get("status") != "completed":
                    continue
                output_dir = record.get("output_dir")
                query = (record.get("query") or "").strip()
                if not output_dir or not query:
                    continue
                folder_name = Path(output_dir).name
                if folder_name:
                    # Keep the latest seen mapping if duplicates exist.
                    mapping[folder_name] = query
    except Exception:
        logger.exception("Failed to load output-query mapping from %s", QUERY_HISTORY_FILE)
    return mapping


def _query_for_output_folder(folder_name: str | None) -> str | None:
    if not folder_name:
        return None
    mapping = _load_output_query_mapping()
    query = (mapping.get(folder_name) or "").strip()
    return query or None


def _is_crawl_running() -> bool:
    proc = st.session_state.get("crawl_proc")
    return bool(proc and proc.poll() is None)


def _request_rerun_for_session(session_id: str) -> bool:
    """Request one rerun for a specific Streamlit session (internal API, best effort)."""
    try:
        from streamlit.runtime.runtime import Runtime

        runtime = Runtime.instance()
        session_info = runtime._session_mgr.get_session_info(session_id)
        if not session_info:
            return False
        session_info.session.request_rerun(None)
        return True
    except Exception:
        logger.exception("Failed to request rerun for session: %s", session_id)
        return False


def _attach_background_completion_rerun(proc: subprocess.Popen) -> None:
    """When background process exits, trigger exactly one UI rerun."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        session_id = ctx.session_id if ctx else None
    except Exception:
        session_id = None

    if not session_id:
        logger.warning("No Streamlit session id found; cannot auto-rerun on background completion.")
        return

    def _wait_and_rerun() -> None:
        try:
            proc.wait()
            _request_rerun_for_session(session_id)
        except Exception:
            logger.exception("Background completion watcher failed.")

    threading.Thread(target=_wait_and_rerun, daemon=True).start()


def _finalize_background_crawl_if_finished() -> None:
    """Poll background crawl process and finalize state/history when it exits."""
    proc = st.session_state.get("crawl_proc")
    if not proc:
        return
    try:
        return_code = proc.poll()
    except Exception:
        # Stale process handle; treat as failed and clear state.
        return_code = -1
    if return_code is None:
        return

    query = st.session_state.get("crawl_query") or ""
    limit = st.session_state.get("crawl_limit") or 0
    output_root = Path(__file__).parent.parent.parent / "output"
    before_names = set(st.session_state.get("crawl_before_dirs") or [])
    after_dirs = [p for p in output_root.iterdir() if p.is_dir()] if output_root.exists() else []
    new_dirs = [p for p in after_dirs if p.name not in before_names]
    output_dir = max(new_dirs, key=lambda p: p.stat().st_mtime) if new_dirs else _find_latest_output_dir(output_root)

    if return_code == 0:
        if output_dir:
            st.session_state.last_output_dir = str(output_dir)
            st.session_state.selected_output_dir = output_dir.name
            st.session_state.pending_select_dir = output_dir.name
            _append_query_history_record(
                query=query,
                limit=limit,
                output_dir=output_dir,
                status="completed",
            )
        else:
            _append_query_history_record(
                query=query,
                limit=limit,
                output_dir=None,
                status="failed",
                error="no_output_directory_generated",
            )
        st.session_state.pipeline_status.update({
            "fetch": "completed",
            "clean": "completed",
            "extract": "completed",
            "progress": 100
        })
    else:
        _append_query_history_record(
            query=query,
            limit=limit,
            output_dir=None,
            status="failed",
            error=f"exit_code_{return_code}",
        )
        st.session_state.pipeline_status.update({
            "fetch": "failed",
            "clean": "failed",
            "extract": "failed",
            "progress": 0
        })

    st.session_state.crawl_proc = None
    st.session_state.crawl_query = None
    st.session_state.crawl_limit = None
    st.session_state.crawl_before_dirs = None


def run_crawl_cli(query: str, limit: int) -> bool:
    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"

    # Keep the UI label "Start Crawling", but execute the end-to-end run command in background.
    cmd = [sys.executable, "-m", "webis.cli", "run", query, "--limit", str(limit)]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    env["PYTHONUNBUFFERED"] = "1"
    env["HF_ENDPOINT"] = "https://hf-mirror.com"
    env["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

    if st.session_state.get("crawl_proc") and st.session_state["crawl_proc"].poll() is None:
        return False

    st.session_state.pipeline_status.update({
        "fetch": "in_progress",
        "clean": "idle",
        "extract": "idle",
        "progress": 10
    })
    st.session_state.crawl_before_dirs = [p.name for p in output_root.iterdir() if p.is_dir()] if output_root.exists() else []
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=repo_root,
            env=env,
            start_new_session=True,
        )
    except Exception as e:
        _append_query_history_record(
            query=query,
            limit=limit,
            output_dir=None,
            status="failed",
            error=str(e),
        )
        st.session_state.pipeline_status.update({
            "fetch": "failed",
            "clean": "failed",
            "extract": "failed",
            "progress": 0
        })
        st.session_state.crawl_before_dirs = None
        return False

    st.session_state.crawl_proc = proc
    st.session_state.crawl_query = query
    st.session_state.crawl_limit = limit
    print(f"[webis_visualizer] Started background crawl pid={proc.pid}: {' '.join(cmd)}", flush=True)
    _attach_background_completion_rerun(proc)
    return True

def run_html_report_cli(target_dir: str | None) -> str | None:
    if _is_crawl_running():
        print("[webis_visualizer] Skip html-report: crawl task is still running.", flush=True)
        return None

    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"
    if not output_root.exists():
        return None

    if not target_dir:
        return None

    output_dir = output_root / target_dir
    result_path = output_dir / "result.json"
    documents_path = output_dir / "documents.json"

    if not result_path.exists():
        return None

    cmd = [
        sys.executable, "-m", "webis.cli", "html-report",
        str(result_path),
    ]
    if documents_path.exists():
        cmd += ["--documents", str(documents_path)]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    env["HF_ENDPOINT"] = "https://hf-mirror.com"
    env["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
    print(f"[webis_visualizer] Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=repo_root, env=env)
    if result.returncode != 0:
        print(f"[webis_visualizer] html-report failed with exit code {result.returncode}", flush=True)
        return None

    report_path = output_dir / "report.html"
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")

    return None


def _find_latest_markdown_report(output_dir: Path) -> Path | None:
    reports = sorted(output_dir.glob("report_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def run_markdown_report_cli(target_dir: str | None) -> tuple[str | None, Path | None]:
    if _is_crawl_running():
        print("[webis_visualizer] Skip markdown-report: crawl task is still running.", flush=True)
        return None, None

    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"
    if not output_root.exists() or not target_dir:
        return None, None

    output_dir = output_root / target_dir
    rag_store_path = output_dir / "rag_store.json"
    if not rag_store_path.exists():
        return None, None

    before_latest = _find_latest_markdown_report(output_dir)
    query = _query_for_output_folder(target_dir)

    cmd = [
        sys.executable, "-m", "webis.cli", "markdown-report",
        str(rag_store_path),
    ]
    if query:
        cmd += ["--query", query]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    env["HF_ENDPOINT"] = "https://hf-mirror.com"
    env["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
    print(f"[webis_visualizer] Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=repo_root, env=env)
    if result.returncode != 0:
        print(f"[webis_visualizer] markdown-report failed with exit code {result.returncode}", flush=True)
        return None, None

    after_latest = _find_latest_markdown_report(output_dir)
    if not after_latest:
        return None, None

    if before_latest and after_latest.resolve() == before_latest.resolve():
        # No new report generated.
        return None, None

    return after_latest.read_text(encoding="utf-8"), after_latest

def load_output_dir_state(selected_dir: str | None) -> None:
    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"
    if not selected_dir:
        st.session_state.documents = []
        st.session_state.structured_result = None
        if not _is_crawl_running():
            st.session_state.pipeline_status.update({
                "fetch": "idle",
                "clean": "idle",
                "extract": "idle",
                "progress": 0
            })
        return

    target_dir = output_root / selected_dir
    docs_path = target_dir / "documents.json"
    result_path = target_dir / "result.json"

    if docs_path.exists():
        with docs_path.open("r", encoding="utf-8") as f:
            docs_data = json.load(f)
        st.session_state.documents = [WebisDocument.model_validate(d) for d in docs_data]
    else:
        st.session_state.documents = []

    if result_path.exists():
        with result_path.open("r", encoding="utf-8") as f:
            st.session_state.structured_result = json.load(f)
        if not _is_crawl_running():
            st.session_state.pipeline_status.update({
                "fetch": "completed",
                "clean": "completed",
                "extract": "completed",
                "progress": 100
            })
    else:
        st.session_state.structured_result = None
        if not _is_crawl_running():
            st.session_state.pipeline_status.update({
                "fetch": "completed" if docs_path.exists() else "idle",
                "clean": "idle",
                "extract": "idle",
                "progress": 30 if docs_path.exists() else 0
            })

# ------------------------------
# Main App
# ------------------------------
init_session_state()
if not st.session_state.history_compacted:
    _compact_query_history_file()
    st.session_state.history_compacted = True
_finalize_background_crawl_if_finished()


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
            display: block !important;
            visibility: visible !important;
            transform: none !important;
            margin-left: 0 !important;
            width: 20rem !important;
            min-width: 20rem !important;
        }
        /* Hide Streamlit's "Press Enter to apply" hint under text inputs */
        div[data-testid="stTextInput"] small {
            display: none !important;
        }
        .right-rail {
            position: fixed;
            top: 0;
            right: 0;
            height: 100vh;
            width: 20rem;
            background: linear-gradient(160deg, #d6efea, #d9f1d2);
            border-left: 1px solid var(--border);
            z-index: 0;
            pointer-events: auto;
            display: flex;
            flex-direction: column;
            padding: 18px 16px;
            gap: 14px;
        }
        .right-rail-title {
            font-weight: 700;
            font-size: 1.05rem;
            color: var(--ink);
        }
        .output-select-wrapper {
            margin: 10px auto 6px;
            width: 260px;
        }
        div[data-testid="stTabs"] {
            margin-top: 6px;
        }
        div[data-testid="stTabs"] [role="tablist"] {
            margin-bottom: 8px;
        }
        div[data-testid="stTabs"] [role="tabpanel"] {
            padding-top: 0;
        }
        .output-select-wrapper div[data-testid="stSelectbox"] > div {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 2px 10px;
            box-shadow: 0 8px 18px rgba(23, 56, 56, 0.08);
        }
        .output-select-wrapper div[data-testid="stSelectbox"] span {
            font-weight: 600;
            color: var(--ink);
        }
        .right-rail-list {
            display: grid;
            gap: 12px;
        }
        .right-rail-item {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: var(--shadow);
            color: var(--ink);
            font-weight: 600;
            font-size: 0.95rem;
            text-decoration: none;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .right-rail-item,
        .right-rail-item *,
        .right-rail-item:visited,
        .right-rail-item:hover,
        .right-rail-item:active,
        .right-rail-item:focus {
            text-decoration: none !important;
            text-decoration-line: none !important;
            color: var(--ink) !important;
        }
        .right-rail-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(23, 56, 56, 0.12);
        }
        .right-rail-item.disabled {
            pointer-events: none;
            opacity: 0.5;
        }
        .right-rail-button {
            width: 100%;
            text-align: left;
            cursor: pointer;
            appearance: none;
            border: 1px solid var(--border);
            background: var(--card);
        }
        .right-rail-button:disabled {
            cursor: not-allowed;
        }
        .right-rail-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 16px;
            padding: 10px 12px;
            border-radius: 12px;
            border: 1px dashed var(--border);
            color: var(--ink);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            background: rgba(255, 255, 255, 0.7);
        }
        .right-rail-link.muted {
            color: var(--muted);
            border-style: solid;
        }
        .right-rail-preview {
            border: 1px dashed var(--border);
            border-radius: 12px;
            padding: 10px 12px;
            color: var(--ink);
            background: rgba(255, 255, 255, 0.7);
            font-weight: 600;
            font-size: 0.9rem;
        }
        .right-rail-preview-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .right-rail-preview.muted {
            color: var(--muted);
            border-style: solid;
        }
        .right-rail-preview iframe {
            display: none;
        }
        .right-rail-download {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 8px;
            border: 1px solid transparent;
            background: var(--accent);
            color: #ffffff;
            font-weight: 600;
            font-size: 0.8rem;
            text-decoration: none;
            box-shadow: 0 10px 20px rgba(49, 173, 173, 0.28);
            transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
        }
        .right-rail-download,
        .right-rail-download:visited,
        .right-rail-download:hover,
        .right-rail-download:active,
        .right-rail-download:focus {
            text-decoration: none !important;
            color: #ffffff !important;
        }
        .right-rail-download:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 22px rgba(49, 173, 173, 0.35);
            background: #2a9c9c;
        }
        .right-rail-download svg {
            width: 14px;
            height: 14px;
            fill: currentColor;
        }
        .right-rail-item.download-btn {
            cursor: pointer;
        }
        .right-rail-icon {
            width: 28px;
            height: 28px;
            border-radius: 10px;
            background: #e4f7f4;
            display: grid;
            place-items: center;
            flex: 0 0 auto;
        }
        .right-rail-icon.icon-json {
            background: #e6f0ff;
            color: #2b6cb0;
        }
        .right-rail-icon.icon-html {
            background: #ffe9e3;
            color: #c05621;
        }
        .right-rail-icon.icon-md {
            background: #ecf8ef;
            color: #2f855a;
        }
        .right-rail-icon svg {
            width: 16px;
            height: 16px;
            fill: currentColor;
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
            padding-right: 22rem;
        }

        h1, h2, h3, h4 {
            font-family: 'Fraunces', serif;
            letter-spacing: 0.2px;
        }
        h1 {
            margin-top: 0 !important;
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
        .progress-shell.loading .progress-fill {
            background-size: 200% 100%;
            animation: progress-flow 1.2s ease-in-out infinite;
        }
        @keyframes progress-flow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
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
            background: #f3fbf6;
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
            border: 1px solid #d9efe8;
            background: #ffffff;
            animation: rise 0.3s ease;
        }
        .chat-bubble.user {
            margin-left: 18%;
            background: #dff5f0;
            border-color: #bfe8dd;
        }
        .chat-bubble.assistant {
            margin-right: 18%;
            background: #f7fffb;
            border-color: #d6ebe5;
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
        .assistant-shell {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .assistant-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(160deg, #d6efea, #d9f1d2);
        }
        .assistant-title {
            font-weight: 700;
            font-size: 1rem;
        }
        .assistant-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .assistant-body {
            min-height: 52vh;
            display: grid;
            place-items: center;
            padding: 32px 18px 24px;
            background: #fbfffd;
        }
        .assistant-empty {
            display: grid;
            place-items: center;
            gap: 12px;
            text-align: center;
            color: var(--muted);
        }
        .assistant-empty-title {
            font-weight: 700;
            color: var(--ink);
            font-size: 1.05rem;
        }
        .assistant-footer {
            border-top: 1px solid var(--border);
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--muted);
            font-size: 0.85rem;
            background: #f2fbf1;
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
        div[data-testid="stFileUploader"] {
            position: relative;
            border: 1px dashed var(--border);
            border-radius: 16px;
            background: #f8fffc;
            padding: 28px 12px;
            min-height: 120px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        div[data-testid="stFileUploader"]::before {
            content: "+";
            position: absolute;
            inset: 0;
            display: grid;
            place-items: center;
            font-size: 2.4rem;
            color: var(--muted);
            pointer-events: none;
        }
        div[data-testid="stFileUploader"] > label,
        div[data-testid="stFileUploader"] section {
            display: none !important;
        }
        div[data-testid="stFileUploader"] button {
            position: absolute !important;
            inset: 0 !important;
            opacity: 0 !important;
        }
        div[data-testid="stChatInput"] {
            background: #f2fbf1;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 6px 10px;
            box-shadow: var(--shadow);
        }
        div[data-testid="stChatInput"] textarea {
            background: transparent !important;
            border: none !important;
            color: var(--ink);
            font-family: 'Space Grotesk', sans-serif;
        }
        div[data-testid="stChatInput"] textarea::placeholder {
            color: var(--muted);
        }
        div[data-testid="stChatInput"] button {
            background: var(--accent) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 999px !important;
            box-shadow: none !important;
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

# Output folder selector (below header)
repo_root = Path(__file__).parent.parent.parent
output_root = repo_root / "output"
output_folders = []
if output_root.exists():
    output_folders = sorted([p.name for p in output_root.iterdir() if p.is_dir()], reverse=True)
output_query_map = _load_output_query_mapping()

if output_folders:
    if st.session_state.selected_output_dir not in output_folders:
        st.session_state.selected_output_dir = output_folders[0]
    if st.session_state.pending_select_dir in output_folders:
        st.session_state.selected_output_dir = st.session_state.pending_select_dir
        st.session_state.output_folder_select = st.session_state.pending_select_dir
        st.session_state.pending_select_dir = None
    if st.session_state.output_folder_select not in output_folders:
        st.session_state.output_folder_select = st.session_state.selected_output_dir
else:
    st.session_state.selected_output_dir = None
    st.session_state.output_folder_select = None

st.markdown("<div class=\"output-select-wrapper\">", unsafe_allow_html=True)
selected = st.selectbox(
    "Output Folder",
    options=output_folders,
    format_func=lambda folder: output_query_map.get(folder, folder),
    index=output_folders.index(st.session_state.output_folder_select) if st.session_state.output_folder_select else 0,
    key="output_folder_select",
    label_visibility="collapsed"
)
st.session_state.selected_output_dir = selected if output_folders else None
load_output_dir_state(st.session_state.selected_output_dir)
st.markdown("</div>", unsafe_allow_html=True)

# Right rail (uses selected output folder)
structured_json_link = ""
structured_json_class = "right-rail-item disabled"
selected_dir = st.session_state.selected_output_dir
result_path = None
report_path = None
rag_store_path = None
markdown_report_path = None

if selected_dir:
    result_path = output_root / selected_dir / "result.json"
    report_path = output_root / selected_dir / "report.html"
    rag_store_path = output_root / selected_dir / "rag_store.json"
    markdown_report_path = _find_latest_markdown_report(output_root / selected_dir)

if result_path and result_path.exists():
    structured_json = result_path.read_text(encoding="utf-8")
    structured_json_b64 = base64.b64encode(structured_json.encode("utf-8")).decode("utf-8")
    structured_json_link = f"data:application/json;charset=utf-8;base64,{structured_json_b64}"
    structured_json_class = "right-rail-item"
    html_report_enabled = True
else:
    html_report_enabled = False

html_report_download_link = ""
if report_path and report_path.exists():
    html_report_content = report_path.read_text(encoding="utf-8")
    html_report_b64 = base64.b64encode(html_report_content.encode("utf-8")).decode("utf-8")
    html_report_download_link = f"data:text/html;charset=utf-8;base64,{html_report_b64}"

markdown_report_download_link = ""
if markdown_report_path and markdown_report_path.exists():
    markdown_report_content = markdown_report_path.read_text(encoding="utf-8")
    markdown_report_b64 = base64.b64encode(markdown_report_content.encode("utf-8")).decode("utf-8")
    markdown_report_download_link = f"data:text/markdown;charset=utf-8;base64,{markdown_report_b64}"

markdown_report_block = '<div class="right-rail-preview muted">No Markdown report yet</div>'
is_active_markdown_dir = bool(selected_dir) and selected_dir == st.session_state.markdown_report_last_dir
if st.session_state.markdown_report_status == "processing" and is_active_markdown_dir:
    markdown_report_block = '<div class="right-rail-preview">Processing...</div>'
elif markdown_report_path and markdown_report_path.exists():
    markdown_report_block = textwrap.dedent(f"""
        <div class="right-rail-preview-row">
            <div class="right-rail-preview">Markdown Report Ready</div>
            <a class="right-rail-download" href="{markdown_report_download_link}" download="{markdown_report_path.name}">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 3a1 1 0 0 1 1 1v8.59l2.3-2.3a1 1 0 1 1 1.4 1.42l-4.01 4a1 1 0 0 1-1.38 0l-4.01-4a1 1 0 1 1 1.4-1.42L11 12.59V4a1 1 0 0 1 1-1zm-7 14a1 1 0 0 1 1 1v1h12v-1a1 1 0 1 1 2 0v2a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1z"/>
                </svg>
                <span>Download</span>
            </a>
        </div>
    """).strip()
elif st.session_state.markdown_report_status == "failed" and is_active_markdown_dir:
    markdown_report_block = '<div class="right-rail-preview muted">Failed to generate Markdown report</div>'

html_report_block = '<div class="right-rail-preview muted">No HTML report yet</div>'
is_active_html_dir = bool(selected_dir) and selected_dir == st.session_state.html_report_last_dir
if st.session_state.html_report_status == "processing" and is_active_html_dir:
    html_report_block = '<div class="right-rail-preview">Processing...</div>'
elif report_path and report_path.exists():
    html_report_block = textwrap.dedent(f"""
        <div class="right-rail-preview-row">
            <div class="right-rail-preview">HTML Report Ready</div>
            <a class="right-rail-download" href="{html_report_download_link}" download="report.html">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 3a1 1 0 0 1 1 1v8.59l2.3-2.3a1 1 0 1 1 1.4 1.42l-4.01 4a1 1 0 0 1-1.38 0l-4.01-4a1 1 0 1 1 1.4-1.42L11 12.59V4a1 1 0 0 1 1-1zm-7 14a1 1 0 0 1 1 1v1h12v-1a1 1 0 1 1 2 0v2a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1z"/>
                </svg>
                <span>Download</span>
            </a>
        </div>
    """).strip()
elif st.session_state.html_report_status == "failed" and is_active_html_dir:
    html_report_block = '<div class="right-rail-preview muted">Failed to generate HTML report</div>'

html_report_action_enabled = (
    html_report_enabled
    and st.session_state.html_report_status != "processing"
    and not _is_crawl_running()
)
html_report_button_class = "right-rail-item right-rail-button"
if not html_report_action_enabled:
    html_report_button_class += " disabled"
html_report_button_disabled_attr = "disabled" if not html_report_action_enabled else ""

markdown_report_enabled = bool(rag_store_path and rag_store_path.exists())
markdown_report_action_enabled = (
    markdown_report_enabled
    and st.session_state.markdown_report_status != "processing"
    and not _is_crawl_running()
)
markdown_report_button_class = "right-rail-item right-rail-button"
if not markdown_report_action_enabled:
    markdown_report_button_class += " disabled"
markdown_report_button_disabled_attr = "disabled" if not markdown_report_action_enabled else ""

st.markdown(
    textwrap.dedent(f"""
        <aside class="right-rail">
            <div class="right-rail-title">Value Data Generation</div>
            <div class="right-rail-list">
                <a class="{structured_json_class}" href="{structured_json_link or '#'}" download="result.json">
                    <div class="right-rail-icon icon-json">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M7 4h7l4 4v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm7 1.5V9h3.5L14 5.5zM8 12h2v2H8v-2zm0 4h2v2H8v-2zm4-4h4v2h-4v-2zm0 4h4v2h-4v-2z"/>
                        </svg>
                    </div>
                    <div>Structured JSON file</div>
                </a>
                <button class="{markdown_report_button_class}" id="markdown-report-trigger" type="button" {markdown_report_button_disabled_attr}>
                    <div class="right-rail-icon icon-md">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M5 4h8l6 6v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm8 1.5V10h4.5L13 5.5zM7 12h6v2H7v-2zm0 4h8v2H7v-2z"/>
                            <path d="M15.5 14.5h2v2h-2v-2z"/>
                        </svg>
                    </div>
                    <div>Markdown report</div>
                </button>
                <button class="{html_report_button_class}" id="html-report-trigger" type="button" {html_report_button_disabled_attr}>
                    <div class="right-rail-icon icon-html">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M4 5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5zm9-1.5V9h4.5L13 3.5zM7 12h4v2H7v-2zm0 4h6v2H7v-2z"/>
                            <path d="M14 12l2-2 2 2-2 2-2-2z"/>
                        </svg>
                    </div>
                    <div>HTML report</div>
                </button>
            </div>
            {markdown_report_block}
            {html_report_block}
        </aside>
    """),
    unsafe_allow_html=True
)

markdown_report_clicked = st.button(
    "Markdown report action",
    key="markdown_report_action_hidden",
    help="Markdown report action",
    disabled=not markdown_report_action_enabled
)

html_report_clicked = st.button(
    "HTML report action",
    key="html_report_action_hidden",
    help="HTML report action",
    disabled=not html_report_action_enabled
)

components.html(
    """
    <script>
    (function() {
      const findHiddenButton = (label) => {
        const buttons = Array.from(window.parent.document.querySelectorAll('button'));
        return buttons.find((btn) => (btn.textContent || '').trim() === label);
      };
      const bind = () => {
        const pairs = [
          ['markdown-report-trigger', 'Markdown report action'],
          ['html-report-trigger', 'HTML report action'],
        ];
        pairs.forEach(([triggerId, hiddenLabel]) => {
          const trigger = window.parent.document.getElementById(triggerId);
          const hidden = findHiddenButton(hiddenLabel);
          if (hidden) {
            const wrap = hidden.closest('[data-testid=\"stButton\"]') || hidden.parentElement;
            if (wrap) wrap.style.display = 'none';
          }
          if (trigger && hidden && !trigger.dataset.bound) {
            trigger.addEventListener('click', (event) => {
              event.preventDefault();
              event.stopPropagation();
              if (trigger.hasAttribute('disabled')) return;
              hidden.click();
            });
            trigger.dataset.bound = '1';
          }
        });
      };
      const observer = new MutationObserver(bind);
      observer.observe(window.parent.document.body, { childList: true, subtree: true });
      bind();
    })();
    </script>
    """,
    height=0,
    width=0
)

if html_report_clicked:
    st.session_state.html_report_status = "processing"
    st.session_state.html_report_last_dir = st.session_state.selected_output_dir
    st.session_state.html_report_html = None
    st.session_state.html_report_pending = True
    st.rerun()

if markdown_report_clicked:
    st.session_state.markdown_report_status = "processing"
    st.session_state.markdown_report_last_dir = st.session_state.selected_output_dir
    st.session_state.markdown_report_pending = True
    st.rerun()

if (
    st.session_state.html_report_pending
    and st.session_state.html_report_status == "processing"
    and st.session_state.selected_output_dir
):
    st.session_state.html_report_pending = False
    html_output = run_html_report_cli(st.session_state.selected_output_dir)
    if html_output:
        st.session_state.html_report_status = "ready"
    else:
        st.session_state.html_report_status = "failed"
    st.rerun()

if (
    st.session_state.markdown_report_pending
    and st.session_state.markdown_report_status == "processing"
    and st.session_state.selected_output_dir
):
    st.session_state.markdown_report_pending = False
    markdown_output, _ = run_markdown_report_cli(st.session_state.selected_output_dir)
    if markdown_output:
        st.session_state.markdown_report_status = "ready"
    else:
        st.session_state.markdown_report_status = "failed"
    st.rerun()

# ------------------------------
# Sidebar - Data Source Management
# ------------------------------
# Single page for data sources
st.sidebar.subheader("Web Crawling")

query = st.sidebar.text_input("Search Query", placeholder="Enter your search query...")
limit = st.sidebar.slider("Number of Results", min_value=1, max_value=10, value=3)

if st.sidebar.button("Start Crawling"):
    if query:
        started = run_crawl_cli(query, limit)
        if started:
            st.sidebar.success("✅ Started in background: webis run")
            st.rerun()
        else:
            st.sidebar.warning("⚠️ A crawling task is already running. Please wait for it to finish.")
    else:
        st.error("❌ Please enter a search query")

if _is_crawl_running():
    st.sidebar.info(f"⏳ Running in background: {st.session_state.get('crawl_query')}")

st.sidebar.markdown("---")
st.sidebar.subheader("Local Upload")
st.sidebar.caption("Supported: PDF, Word, PPT, HTML, TXT, CSV, MD")

uploaded_files = st.sidebar.file_uploader(
    "Upload Files",
    accept_multiple_files=True,
    type=["pdf", "doc", "docx", "ppt", "pptx", "html", "txt", "csv", "md"],
    label_visibility="collapsed"
)

if st.sidebar.button("Process Uploaded Files"):
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
    st.markdown(
        textwrap.dedent(f"""
            <div class="stat-row">
                <div class="stat-card">
                    <div class="stat-label">Raw Documents</div>
                    <div class="stat-value">{doc_count}</div>
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

    loading = any(
        status == "in_progress"
        for key, status in st.session_state.pipeline_status.items()
        if key != "progress"
    )
    loading_class = "loading" if loading else ""

    st.markdown(
        textwrap.dedent(f"""
            <div class="pipeline-board">
                <div class="pipeline-title">Pipeline Flow</div>
                <div class="progress-shell {loading_class}">
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

    st.subheader("Data Sources")
    if st.session_state.documents:
        for doc in st.session_state.documents:
            label = "Unknown source"
            if doc.meta:
                if doc.meta.url:
                    label = doc.meta.url
                elif doc.meta.title:
                    label = doc.meta.title
                elif doc.meta.custom and doc.meta.custom.get("file_path"):
                    label = doc.meta.custom.get("file_path")
            st.write(f"- {label}")
    else:
        st.caption("No data sources yet. Start crawling or upload local files to populate this list.")

    # Removed "Run Full Pipeline" button per request

with tab3:
    st.header("AI Assistant")

    pending_prompt = st.session_state.pop("queued_prompt", None)
    if st.session_state.get("pending_prompt"):
        pending_prompt = st.session_state.pop("pending_prompt")
    if pending_prompt:
        run_assistant(pending_prompt)

    st.markdown(
        textwrap.dedent("""
            <div class="assistant-shell">
                <div class="assistant-header">
                    <div class="assistant-title">Chat</div>
                </div>
            </div>
        """),
        unsafe_allow_html=True
    )

    if not st.session_state.chat_history:
        st.markdown(
            textwrap.dedent("""
                <div class="assistant-shell">
                    <div class="assistant-body">
                        <div class="assistant-empty">
                            <div class="assistant-empty-title">Add data to get started</div>
                        </div>
                    </div>
                    <div class="assistant-footer">
                        <div>Add data to get started</div>
                        <div>0 data sources</div>
                    </div>
                </div>
            """),
            unsafe_allow_html=True
        )
    else:
        with st.container():
            render_chat_history(st.session_state.chat_history)

    st.markdown("<div style=\"height: 16px;\"></div>", unsafe_allow_html=True)
    prompt = st.chat_input("Ask about your data, request summaries, or explore patterns...")
    if prompt:
        st.session_state.pending_prompt = prompt
        st.experimental_rerun()

# ------------------------------
# Footer
# ------------------------------
st.markdown("---")
st.caption("🚀 Webis Visualizer - powered by Webis AI Pipeline")
