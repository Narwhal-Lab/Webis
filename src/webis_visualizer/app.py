"""
Webis Visualizer - NotebookLM-style interface for Webis pipeline
"""

import streamlit as st
import os
import sys
import json
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
from webis.core.llm import list_registered_models, _has_real_env_value
from webis_visualizer.styles import get_global_css

logger = logging.getLogger(__name__)
QUERY_HISTORY_FILE = Path(__file__).parent.parent.parent / "output" / "query_history.jsonl"

_FAVICON = Path(__file__).parent / "assets" / "webis.svg"

st.set_page_config(
    page_title="Webis Visualizer",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _append_query_history_record(
    query: str,
    limit: int,
    output_dir: Path | None,
    status: str,
    error: str | None = None,
) -> None:
    try:
        QUERY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "query": query,
            "limit": limit,
            "output_dir": str(output_dir) if output_dir else None,
            "status": status,
            "error": error,
        }
        with QUERY_HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Failed to append query history record")


def _compact_query_history_file(max_records: int = 3000) -> None:
    if not QUERY_HISTORY_FILE.exists():
        return
    try:
        lines = QUERY_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) <= max_records:
            return
        QUERY_HISTORY_FILE.write_text("\n".join(lines[-max_records:]) + "\n", encoding="utf-8")
    except Exception:
        logger.exception("Failed to compact query history file")


def _find_latest_output_dir(output_root: Path) -> Path | None:
    if not output_root.exists():
        return None
    dirs = [p for p in output_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def _load_output_query_mapping() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not QUERY_HISTORY_FILE.exists():
        return mapping
    try:
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
                    mapping[folder_name] = query
    except Exception:
        logger.exception("Failed to load output-query mapping from %s", QUERY_HISTORY_FILE)
    return mapping


# ------------------------------
# Helper Functions


def _query_for_output_folder(folder_name: str | None) -> str | None:
    if not folder_name:
        return None
    mapping = _load_output_query_mapping()
    query = (mapping.get(folder_name) or "").strip()
    return query or None


def get_logo_data_uri() -> str:
    logo_path = Path(__file__).parent / "assets" / "webis.svg"
    if logo_path.exists():
        try:
            svg_content = logo_path.read_text(encoding="utf-8")
            encoded = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
            return f"data:image/svg+xml;base64,{encoded}"
        except Exception:
            logger.exception("Failed to load logo from %s", logo_path)

    fallback_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#22c55e"/><stop offset="100%" stop-color="#059669"/>'
        '</linearGradient></defs>'
        '<rect width="64" height="64" rx="16" fill="url(#g)"/>'
        '<text x="32" y="42" text-anchor="middle" font-size="28" '
        'font-family="Inter,Arial,sans-serif" font-weight="900" fill="white">W</text>'
        '</svg>'
    )
    encoded_fallback = base64.b64encode(fallback_svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded_fallback}"


def _get_env_paths() -> tuple[Path, Path]:
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / ".env", repo_root / ".env.example"


def _strip_wrapping_quotes(value: str) -> str:
    s = (value or "").strip()
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        return s[1:-1]
    return s


def _load_key_catalog(paths: list[Path]) -> dict[str, list[str]]:
    """
    Load key catalog from the first valid source file provided.
    Tries paths in order (e.g., [.env, .env.example]).
    """
    for path in paths:
        if not path.exists():
            continue

        llm_keys: list[str] = []
        data_source_keys: list[str] = []
        current_section = None
        has_valid_sections = False

        try:
            content = path.read_text(encoding="utf-8")

            # Flexible check for section headers
            has_llm_header = "LLM Provider" in content or "LLM Providers" in content
            has_data_header = "Search/Scraping" in content or "Search API" in content or "Data Source" in content

            if not has_llm_header and not has_data_header:
                continue

            lines = content.splitlines()

            def _is_section_banner(index: int) -> bool:
                if index <= 0 or index >= len(lines) - 1:
                    return False
                prev_line = lines[index - 1].strip()
                next_line = lines[index + 1].strip()
                return "===" in prev_line and "===" in next_line

            for idx, raw_line in enumerate(lines):
                line = raw_line.strip()

                # Treat banner title comments as section boundaries.
                if line.startswith("#") and _is_section_banner(idx):
                    lowered = line.lower()
                    if "llm provider" in lowered or "llm providers" in lowered:
                        current_section = "llm"
                        has_valid_sections = True
                    elif "search/scraping" in lowered or "search api" in lowered or "data source" in lowered:
                        current_section = "data_source"
                        has_valid_sections = True
                    else:
                        # Entering other top-level section; stop collecting keys.
                        current_section = None
                    continue

                if not line or line.startswith("#") or "=" not in raw_line:
                    continue

                key = raw_line.split("=", 1)[0].strip()
                if not key:
                    continue

                if current_section == "llm":
                    llm_keys.append(key)
                elif current_section == "data_source":
                    data_source_keys.append(key)
            
            if has_valid_sections:
                return {"llm": llm_keys, "data_source": data_source_keys}
                
        except Exception:
            logger.exception(f"Failed to parse key catalog from {path}")
            continue

    return {"llm": [], "data_source": []}


def _load_env_values(env_path: Path, managed_keys: list[str]) -> dict[str, str]:
    values = {key: "" for key in managed_keys}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if key in values:
            values[key] = _strip_wrapping_quotes(value)

    return values


def _save_env_values(env_path: Path, managed_keys: list[str], values: dict[str, str]) -> None:
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# Auto-generated by Webis Visualizer", ""]

    key_to_index: dict[str, int] = {}
    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key = raw_line.split("=", 1)[0].strip()
        if key in managed_keys and key not in key_to_index:
            key_to_index[key] = idx

    for key in managed_keys:
        new_line = f"{key}={values.get(key, '').strip()}"
        if key in key_to_index:
            lines[key_to_index[key]] = new_line
        else:
            lines.append(new_line)

    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _load_effective_env_values(env_path: Path, template_path: Path, managed_keys: list[str]) -> dict[str, str]:
    """
    Load values for the key panel.
    Priority: .env (runtime) > .env.example (template defaults).
    """
    template_values = _load_env_values(template_path, managed_keys)
    env_values = _load_env_values(env_path, managed_keys)
    merged = dict(template_values)
    for key in managed_keys:
        val = (env_values.get(key) or "").strip()
        if val:
            merged[key] = val
    return merged


@st.dialog("Configure API Keys")
def _show_key_config_dialog() -> None:
    env_path, template_path = _get_env_paths()
    # Prioritize loading catalog from .env itself if structured, fallback to example
    catalog = _load_key_catalog([env_path, template_path])
    llm_keys = catalog.get("llm", [])
    data_source_keys = catalog.get("data_source", [])
    managed_keys = llm_keys + data_source_keys

    if not managed_keys:
        st.error("Unable to load key catalog from .env or .env.example")
        return

    current_values = _load_effective_env_values(env_path, template_path, managed_keys)
    llm_ready = sum(1 for key in llm_keys if (current_values.get(key) or "").strip())
    data_ready = sum(1 for key in data_source_keys if (current_values.get(key) or "").strip())

    st.markdown(
        f"""
        <div class="key-config-note">
          <strong>LLM Provider keys:</strong> {llm_ready}/{len(llm_keys)} configured (at least 1 required)<br/>
          <strong>Search/Scraping keys:</strong> {data_ready}/{len(data_source_keys)} configured (3+ recommended)
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("key_config_form", clear_on_submit=False):
        submitted_values: dict[str, str] = {}
        try:
            key_scroll_container = st.container(height=340, border=False)
        except TypeError:
            key_scroll_container = st.container()

        with key_scroll_container:
            st.markdown("#### LLM Provider Keys")
            for key in llm_keys:
                submitted_values[key] = st.text_input(
                    key,
                    value=current_values.get(key, ""),
                    type="password",
                    placeholder=f"Set {key}",
                )

            st.markdown("#### Search/Scraping API Keys")
            for key in data_source_keys:
                submitted_values[key] = st.text_input(
                    key,
                    value=current_values.get(key, ""),
                    type="password",
                    placeholder=f"Set {key}",
                )

        submitted = st.form_submit_button("Save to .env", type="primary", use_container_width=True)

        if submitted:
            llm_count = sum(1 for key in llm_keys if (submitted_values.get(key) or "").strip())
            data_count = sum(1 for key in data_source_keys if (submitted_values.get(key) or "").strip())

            if llm_count < 1:
                st.error("At least one LLM Provider key is required.")
                return

            _save_env_values(env_path, managed_keys, submitted_values)
            _save_env_values(template_path, managed_keys, submitted_values)

            # Sync into current process env for immediate usage in the same UI session.
            for key, value in submitted_values.items():
                v = (value or "").strip()
                if v:
                    os.environ[key] = v
                elif key in os.environ:
                    os.environ.pop(key, None)

            st.success(f"Saved key configuration to {env_path} and {template_path}")
            if data_count < 3:
                st.warning("Search/Scraping keys configured fewer than 3. 3 or more is recommended.")
            else:
                st.info("Search/Scraping key coverage looks good.")


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


def _webis_cli_env() -> dict:
    """Return a copy of the current environment for CLI subprocess calls."""
    env = os.environ.copy()
    repo_root = str(Path(__file__).parent.parent.parent)
    src_dir = str(Path(__file__).parent.parent)
    # Ensure the repo src directory is on PYTHONPATH so webis package is importable
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{repo_root}" + (f"{os.pathsep}{existing}" if existing else "")

    # Respect model selection from the sidebar for all CLI subprocess calls.
    selected_model = st.session_state.get("webis_selected_model", "auto")
    if selected_model and selected_model != "auto":
        env["WEBIS_LLM_MODEL"] = selected_model
    else:
        env.pop("WEBIS_LLM_MODEL", None)

    return env


def run_crawl_cli(query: str, limit: int) -> bool:
    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"

    # Keep the UI label "Start Crawling", but execute the end-to-end run command in background.
    cmd = [sys.executable, "-m", "webis.cli", "run", query, "--limit", str(limit)]
    env = _webis_cli_env()
    env["PYTHONUNBUFFERED"] = "1"

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

def run_html_report_cli(target_dir: str | None) -> tuple[str | None, str | None]:
    """Run the three-agent HTML report pipeline via CLI.

    Uses rag_store.json as the primary knowledge base. The LLM model is
    automatically selected by the router fallback chain — no manual model
    selection is needed.
    """
    if _is_crawl_running():
        print("[webis_visualizer] Skip html-report: crawl task is still running.", flush=True)
        return None, "Crawl task is still running"

    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"
    if not output_root.exists():
        return None, "Output directory not found"

    if not target_dir:
        return None, "No output folder selected"

    output_dir = output_root / target_dir
    rag_store_path = output_dir / "rag_store.json"

    if not rag_store_path.exists():
        return None, "rag_store.json not found — RAG knowledge base is required"

    query = _query_for_output_folder(target_dir) or ""

    cmd = [
        sys.executable, "-m", "webis.cli", "html-report",
        str(rag_store_path),
    ]
    if query:
        cmd += ["--query", query]

    env = _webis_cli_env()
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[webis_visualizer] Running: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        output_lines.append(line)
        print(line, end="", flush=True)

    proc.wait()
    output_text = "".join(output_lines)
    if proc.returncode != 0:
        print(f"[webis_visualizer] html-report failed with exit code {proc.returncode}", flush=True)
        output_text_lower = output_text.lower()
        if "api key" in output_text_lower or "missing" in output_text_lower or "invalid" in output_text_lower:
            return None, "HTML report generation failed: API key is invalid or missing"
        return None, "HTML report generation failed"

    report_html_path = output_dir / "report.html"
    if report_html_path.exists():
        return report_html_path.read_text(encoding="utf-8"), None

    return None, "report.html was not generated"


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

    env = _webis_cli_env()
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


def run_image_report_cli(target_dir: str | None) -> tuple[str | None, str | None]:
    """Run the image report pipeline (Gemini) via CLI.

    Returns (image_path_str | None, error_msg | None).
    """
    if _is_crawl_running():
        print("[webis_visualizer] Skip image-report: crawl task is still running.", flush=True)
        return None, "Crawl task is still running"

    repo_root = Path(__file__).parent.parent.parent
    output_root = repo_root / "output"
    if not output_root.exists():
        return None, "Output directory not found"

    if not target_dir:
        return None, "No output folder selected"

    output_dir = output_root / target_dir
    rag_store_path = output_dir / "rag_store.json"

    if not rag_store_path.exists():
        return None, "rag_store.json not found — RAG knowledge base is required"

    query = _query_for_output_folder(target_dir) or ""

    cmd = [
        sys.executable, "-m", "webis.cli", "image-report",
        str(rag_store_path),
    ]
    if query:
        cmd += ["--query", query]

    env = _webis_cli_env()
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[webis_visualizer] Running: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        output_lines.append(line)
        print(line, end="", flush=True)

    proc.wait()
    output_text = "".join(output_lines)
    if proc.returncode != 0:
        print(f"[webis_visualizer] image-report failed with exit code {proc.returncode}", flush=True)
        output_text_lower = output_text.lower()
        if "api key" in output_text_lower or "zhouliu" in output_text_lower:
            return None, "Image report failed: ZHOULIU_API_KEY is invalid or missing"
        return None, "Image report generation failed"

    # Find the latest generated image
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images = sorted(output_dir.glob(ext), key=lambda p: p.stat().st_mtime, reverse=True)
        if images:
            return str(images[0]), None

    return None, "No image was generated"

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


def init_session_state() -> None:
    defaults = {
        "documents": [],
        "structured_result": None,
        "pipeline_status": {
            "fetch": "idle",
            "clean": "idle",
            "extract": "idle",
            "progress": 0,
        },
        "crawl_proc": None,
        "crawl_query": None,
        "crawl_limit": None,
        "crawl_before_dirs": None,
        "last_output_dir": None,
        "selected_output_dir": None,
        "pending_select_dir": None,
        "output_folder_select": None,
        "history_compacted": False,
        "webis_selected_model": "auto",
        "html_report_status": "idle",
        "html_report_last_dir": None,
        "html_report_html": None,
        "html_report_pending": False,
        "html_report_error": None,
        "markdown_report_status": "idle",
        "markdown_report_last_dir": None,
        "markdown_report_pending": False,
        "image_report_status": "idle",
        "image_report_last_dir": None,
        "image_report_pending": False,
        "image_report_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    pipeline_defaults = defaults["pipeline_status"]
    if not isinstance(st.session_state.pipeline_status, dict):
        st.session_state.pipeline_status = dict(pipeline_defaults)
    else:
        for status_key, status_value in pipeline_defaults.items():
            st.session_state.pipeline_status.setdefault(status_key, status_value)

# ------------------------------
# Main App
# ------------------------------
init_session_state()
if not st.session_state.history_compacted:
    _compact_query_history_file()
    st.session_state.history_compacted = True
_finalize_background_crawl_if_finished()


# Custom CSS
st.markdown(get_global_css(), unsafe_allow_html=True)

# Floating sidebar toggle button – injected into parent document via JS
st.markdown(
    """
    <script>
    (function() {
        function initToggle() {
            var pdoc = window.parent.document;

            // Avoid double-init on Streamlit reruns
            if (pdoc.getElementById('_wbs_sb_btn')) return;

            var btn = pdoc.createElement('button');
            btn.id = '_wbs_sb_btn';
            btn.title = 'Toggle sidebar';
            btn.setAttribute('aria-label', 'Toggle sidebar');
            btn.innerHTML = '<svg id="_wbs_sb_ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>';

            // Inline styles so no dependency on host CSS loading order
            Object.assign(btn.style, {
                position:     'fixed',
                top:          '50%',
                left:         '0',
                transform:    'translateY(-50%)',
                zIndex:       '999999',
                width:        '28px',
                height:       '52px',
                background:   '#ffffff',
                border:       '1px solid #e5e7eb',
                borderLeft:   'none',
                borderRadius: '0 8px 8px 0',
                boxShadow:    '2px 0 8px rgba(0,0,0,0.08)',
                cursor:       'pointer',
                display:      'flex',
                alignItems:   'center',
                justifyContent: 'center',
                padding:      '0',
                color:        '#6b7280',
                transition:   'all 0.15s ease',
            });

            btn.addEventListener('mouseenter', function() {
                btn.style.background = '#f0fdf4';
                btn.style.borderColor = '#bbf7d0';
                btn.style.color = '#15803d';
                btn.style.width = '32px';
            });
            btn.addEventListener('mouseleave', function() {
                btn.style.background = '#ffffff';
                btn.style.borderColor = '#e5e7eb';
                btn.style.color = '#6b7280';
                btn.style.width = '28px';
            });

            var _hidden = false;
            btn.addEventListener('click', function() {
                var sidebar = pdoc.querySelector('section[data-testid="stSidebar"]');
                if (!sidebar) return;
                _hidden = !_hidden;
                if (_hidden) {
                    // Hide: collapse width to 0, keep element in DOM
                    sidebar.style.cssText += ';width:0!important;min-width:0!important;overflow:hidden!important;padding:0!important;border:none!important;';
                    // Flip icon
                    btn.querySelector('svg').innerHTML = '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/><polyline points="12 8 9 13 12 18"/>';
                    btn.style.left = '0';
                } else {
                    // Restore
                    sidebar.style.cssText = sidebar.style.cssText
                        .replace(/;?width:0!important/g, '')
                        .replace(/;?min-width:0!important/g, '')
                        .replace(/;?overflow:hidden!important/g, '')
                        .replace(/;?padding:0!important/g, '')
                        .replace(/;?border:none!important/g, '');
                    btn.querySelector('svg').innerHTML = '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/>';
                }
            });

            pdoc.body.appendChild(btn);
        }

        // Run immediately and also after a short delay (for Streamlit rerenders)
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() { setTimeout(initToggle, 300); });
        } else {
            setTimeout(initToggle, 300);
        }
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

logo_uri = get_logo_data_uri()
st.markdown(
    textwrap.dedent(f"""
        <div class="brand-bar">
            <div class="brand-mark">
                <img src="{logo_uri}" alt="Webis logo"/>
            </div>
            <div>
                <div class="brand-title">Webis</div>
                <div class="brand-subtitle">Intelligent Knowledge Pipeline</div>
            </div>
            <span class="brand-badge">
                <svg width="6" height="6" viewBox="0 0 6 6" style="flex-shrink:0;"><circle cx="3" cy="3" r="3" fill="#4ade80"/></svg>
                v2.0
            </span>
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



# Main content tabs (place directly after output selector to keep spacing tight)
tab1, tab2 = st.tabs([
    "📊 Pipeline Dashboard",
    "🔄 Data Transformation",
])

selected_dir = st.session_state.selected_output_dir
_, env_example_path = _get_env_paths()
key_config_action_enabled = env_example_path.exists()

# ------------------------------
# Sidebar - Data Source Management
# ------------------------------
# Single page for data sources
st.sidebar.markdown(
    """
    <div class="sidebar-mini-title">
        <span class="smt-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="11" cy="11" r="7"/>
                <line x1="16.5" y1="16.5" x2="22" y2="22"/>
                <path d="M11 4a7 7 0 0 1 4 1.5"/>
                <path d="M8 5.5C6.5 7 6 9 6 11"/>
            </svg>
        </span>
        <span>Web Crawling</span>
    </div>
    """,
    unsafe_allow_html=True,
)

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

# --- Model Selector ---
_all_models = list_registered_models()
_model_keys = list(_all_models.keys())

def _model_display_name(key: str) -> str:
    """Create a human-friendly label for the dropdown."""
    if key == "auto":
        return "🤖 Auto"
    cfg = _all_models.get(key)
    if not cfg:
        return key
    has_key = _has_real_env_value(cfg.api_key_env) if cfg.api_key_env else False
    status = "✅" if has_key else "⚠️"
    return f"{status} {key}  —  {cfg.name}"

_selector_options = ["auto"] + _model_keys
_current_idx = 0
if st.session_state.webis_selected_model in _selector_options:
    _current_idx = _selector_options.index(st.session_state.webis_selected_model)

st.sidebar.markdown(
    """
    <div class="sidebar-mini-title">
        <span class="smt-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="4" y="4" width="16" height="16" rx="2"/>
                <rect x="9" y="9" width="6" height="6" rx="1"/>
                <line x1="9" y1="1" x2="9" y2="4"/>
                <line x1="15" y1="1" x2="15" y2="4"/>
                <line x1="9" y1="20" x2="9" y2="23"/>
                <line x1="15" y1="20" x2="15" y2="23"/>
                <line x1="20" y1="9" x2="23" y2="9"/>
                <line x1="20" y1="14" x2="23" y2="14"/>
                <line x1="1" y1="9" x2="4" y2="9"/>
                <line x1="1" y1="14" x2="4" y2="14"/>
            </svg>
        </span>
        <span>Model</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.session_state.webis_selected_model = st.sidebar.selectbox(
    "LLM Model",
    options=_selector_options,
    index=_current_idx,
    format_func=_model_display_name,
    key="_model_selector_widget",
    label_visibility="collapsed",
)

# Show a short hint about what the current selection means.
if st.session_state.webis_selected_model == "auto":
    st.sidebar.markdown(
        '<span style="font-size:0.78rem;color:var(--muted);line-height:1.4">'
        'Automatically picks the best available model</span>',
        unsafe_allow_html=True,
    )
else:
    _sel_cfg = _all_models.get(st.session_state.webis_selected_model)
    if _sel_cfg:
        _has = _has_real_env_value(_sel_cfg.api_key_env) if _sel_cfg.api_key_env else False
        if _has:
            st.sidebar.markdown(
                f'<span style="font-size:0.78rem;color:var(--green-400);line-height:1.4">'
                f'<b>{_sel_cfg.name}</b> · {_sel_cfg.provider}</span>',
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                f'<span style="font-size:0.78rem;color:#facc15;line-height:1.4">'
                f'⚠️ <code style="color:#facc15;background:rgba(250,204,21,0.1);padding:1px 4px;border-radius:4px;">{_sel_cfg.api_key_env}</code> 未配置，将使用免费模型</span>',
                unsafe_allow_html=True,
            )

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div class="sidebar-mini-title">
        <span class="smt-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="7.5" cy="15.5" r="5.5"/>
                <path d="M21 2l-9.6 9.6"/>
                <path d="M15.5 7.5l3 3"/>
                <path d="M18 5l2 2"/>
            </svg>
        </span>
        <span>Key Configuration</span>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.sidebar.button("Configure Keys", disabled=not key_config_action_enabled):
    _show_key_config_dialog()
# st.sidebar.subheader("Local Upload")
# st.sidebar.caption("Supported: PDF, Word, PPT, HTML, TXT, CSV, MD")

# uploaded_files = st.sidebar.file_uploader(
#     "Upload Files",
#     accept_multiple_files=True,
#     type=["pdf", "doc", "docx", "ppt", "pptx", "html", "txt", "csv", "md"],
#     label_visibility="collapsed"
# )

# if st.sidebar.button("Process Uploaded Files"):
#     if uploaded_files:
#         with st.spinner("Processing uploaded files..."):
#             local_docs = []
#             for file in uploaded_files:
#                 doc = process_local_file(file)
#                 local_docs.append(doc)
            
#             # Update session state
#             st.session_state.documents.extend(local_docs)
#             st.session_state.pipeline_status["fetch"] = "completed"
#             st.session_state.pipeline_status["progress"] = 30
#             st.success(f"✅ Processed {len(local_docs)} local files")
#     else:
#         st.error("❌ Please upload some files first")

# ------------------------------
# Main Content Area
# ------------------------------
with tab1:
    st.header("Pipeline Dashboard")

    progress = st.session_state.pipeline_status["progress"]
    doc_count = len(st.session_state.documents)
    st.markdown(
        textwrap.dedent(f"""
            <div class="stat-row">
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                        </svg>
                    </div>
                    <div class="stat-label">Raw Documents</div>
                    <div class="stat-value">{doc_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                        </svg>
                    </div>
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
    for idx, (key, title, desc) in enumerate(step_defs, 1):
        status = st.session_state.pipeline_status.get(key, "idle")
        status_css = status.replace("_", "-")
        step_blocks.append(textwrap.dedent(f"""
            <div class="pipeline-step {status_css}">
                <div class="step-number">{idx}</div>
                <div class="step-header">
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
                <div class="pipeline-title"><span class="pipeline-title-dot"></span>Pipeline Flow</div>
                <div class="pipeline-subtitle">Track your data processing stages from acquisition through knowledge extraction.</div>
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
        import html as _html_esc
        source_items = []
        for doc in st.session_state.documents:
            label = "Unknown source"
            if doc.meta:
                if doc.meta.url:
                    label = doc.meta.url
                elif doc.meta.title:
                    label = doc.meta.title
                elif doc.meta.custom and doc.meta.custom.get("file_path"):
                    label = doc.meta.custom.get("file_path")
            source_items.append(f'<div class="source-item">{_html_esc.escape(label)}</div>')
        st.markdown(
            '<div class="source-list">' + '\n'.join(source_items) + '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No data sources yet. Start crawling or upload local files to populate this list.")

    # Removed "Run Full Pipeline" button per request

with tab2:
    st.header("Data Transformation")
    st.caption("Select a target format and run the transformation from the selected output directory.")

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

    html_report_enabled = bool(rag_store_path and rag_store_path.exists())
    markdown_report_enabled = bool(rag_store_path and rag_store_path.exists())

    html_report_action_enabled = (
        html_report_enabled
        and st.session_state.html_report_status != "processing"
        and not _is_crawl_running()
    )
    markdown_report_action_enabled = (
        markdown_report_enabled
        and st.session_state.markdown_report_status != "processing"
        and not _is_crawl_running()
    )

    if not selected_dir:
        st.info("Select an output directory first.")
    elif not rag_store_path or not rag_store_path.exists():
        st.warning("`rag_store.json` is required before generating reports.")

    # --- Determine processing state ---
    is_any_processing = (
        st.session_state.html_report_status == "processing"
        or st.session_state.markdown_report_status == "processing"
        or st.session_state.image_report_status == "processing"
    )

    # --- Four-item navigation ---
    transform_options = ["📝 markdown", "🌐 HTML", "🖼️ image", "📊 ppt"]
    selected_transform = st.radio(
        "Transformation target",
        options=transform_options,
        horizontal=True,
        key="transform_nav_tab2",
        label_visibility="collapsed",
    )
    # Normalize: strip emoji prefix so downstream comparisons stay unchanged
    selected_transform = selected_transform.split(" ", 1)[-1]

    # ---- Preview box ----
    _is_current_processing = (
        (selected_transform == "markdown" and st.session_state.markdown_report_status == "processing")
        or (selected_transform == "HTML" and st.session_state.html_report_status == "processing")
        or (selected_transform == "image" and st.session_state.image_report_status == "processing")
    )

    _has_preview = False
    _preview_html = ""

    if selected_transform == "markdown" and markdown_report_path and markdown_report_path.exists():
        _md_raw = markdown_report_path.read_text(encoding="utf-8")
        # Render markdown to HTML for preview
        import html as _html_mod
        _escaped = _html_mod.escape(_md_raw)
        _preview_html = (
            '<div class="preview-box"><div class="preview-box-content">'
            f'<pre style="white-space:pre-wrap;word-break:break-word;font-family:inherit;margin:0;font-size:0.92rem;line-height:1.6;">{_escaped}</pre>'
            '</div></div>'
        )
        _has_preview = True
    elif selected_transform == "HTML" and report_path and report_path.exists():
        _html_raw = report_path.read_text(encoding="utf-8")
        import base64 as _b64_mod
        _b64_html = _b64_mod.b64encode(_html_raw.encode("utf-8")).decode("utf-8")
        _preview_html = (
            '<div class="preview-box">'
            f'<iframe src="data:text/html;base64,{_b64_html}" style="width:100%;min-height:418px;border:none;border-radius:12px;"></iframe>'
            '</div>'
        )
        _has_preview = True
    elif selected_transform == "image":
        # Check for any generated images in the output dir
        _img_found = False
        if selected_dir:
            _img_dir = output_root / selected_dir
            for _ext in ("*.png", "*.jpg", "*.jpeg", "*.svg"):
                _images = sorted(_img_dir.glob(_ext))
                if _images:
                    _img_path = _images[-1]
                    import base64 as _b64_mod
                    _img_bytes = _img_path.read_bytes()
                    _img_b64 = _b64_mod.b64encode(_img_bytes).decode("utf-8")
                    _suffix = _img_path.suffix.lstrip(".")
                    _mime = f"image/{'svg+xml' if _suffix == 'svg' else _suffix}"
                    _preview_html = (
                        '<div class="preview-box"><div class="preview-box-content" style="text-align:center;">'
                        f'<img src="data:{_mime};base64,{_img_b64}" alt="Generated image" />'
                        '</div></div>'
                    )
                    _has_preview = True
                    _img_found = True
                    break
    elif selected_transform == "ppt":
        # Check for pptx file in output dir
        if selected_dir:
            _ppt_dir = output_root / selected_dir
            _ppts = sorted(_ppt_dir.glob("*.pptx"))
            if _ppts:
                _preview_html = (
                    '<div class="preview-box"><div class="preview-box-empty">'
                    '<svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">'
                    '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>'
                    '</svg>'
                    '<span style="font-size:1.05rem;">PPT file generated — download to view</span>'
                    '</div></div>'
                )
                _has_preview = True

    if _is_current_processing:
        # Show loading spinner
        st.markdown(
            '<div class="preview-box">'
            '<div class="preview-loading">'
            '<div class="spinner"></div>'
            '<span class="spinner-text">Generating report…</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )
    elif _has_preview:
        st.markdown(_preview_html, unsafe_allow_html=True)
    else:
        # Show empty placeholder
        _placeholder_icon = {
            "markdown": '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
            "HTML": '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
            "image": '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
            "ppt": '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>',
        }.get(selected_transform, '')
        st.markdown(
            '<div class="preview-box">'
            '<div class="preview-box-empty">'
            f'{_placeholder_icon}'
            f'<span>Select <b>{selected_transform}</b> and click Start Generate to preview</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # --- Unified "Start Generate" button (below navigation) ---
    _gen_disabled = True
    _gen_help = ""
    if selected_transform == "markdown":
        _gen_disabled = not markdown_report_action_enabled
        if not _gen_disabled:
            _gen_help = "Generate Markdown report from rag_store.json"
    elif selected_transform == "HTML":
        _gen_disabled = not html_report_action_enabled
        if not _gen_disabled:
            _gen_help = "Generate HTML report from rag_store.json"
    elif selected_transform == "image":
        _gen_disabled = not (
            bool(rag_store_path and rag_store_path.exists())
            and st.session_state.image_report_status != "processing"
            and not _is_crawl_running()
        )
        if not _gen_disabled:
            _gen_help = "Generate image poster via Gemini from rag_store.json"
        else:
            _gen_help = "Requires rag_store.json"
    else:
        _gen_disabled = True
        _gen_help = "PPT export is coming soon"

    generate_clicked = st.button(
        "🚀 Start Generate",
        key="unified_generate_btn_tab2",
        use_container_width=True,
        disabled=_gen_disabled,
        help=_gen_help,
    )

    # Show download button inline when report is already available
    if selected_transform == "markdown" and markdown_report_path and markdown_report_path.exists():
        _md_content = markdown_report_path.read_text(encoding="utf-8")
        st.download_button(
            "⬇ Download Markdown",
            data=_md_content,
            file_name=markdown_report_path.name,
            mime="text/markdown",
            key="download_markdown_tab2",
            use_container_width=True,
        )
    elif selected_transform == "HTML" and report_path and report_path.exists():
        _html_content = report_path.read_text(encoding="utf-8")
        st.download_button(
            "⬇ Download HTML",
            data=_html_content,
            file_name="report.html",
            mime="text/html",
            key="download_html_tab2",
            use_container_width=True,
        )
    elif selected_transform == "image" and selected_dir:
        _img_dir = output_root / selected_dir
        for _ext in ("*.png", "*.jpg", "*.jpeg", "*.svg"):
            _images = sorted(_img_dir.glob(_ext))
            if _images:
                _img_path = _images[-1]
                st.download_button(
                    "⬇ Download Image",
                    data=_img_path.read_bytes(),
                    file_name=_img_path.name,
                    mime=f"image/{_img_path.suffix.lstrip('.')}",
                    key="download_image_tab2",
                    use_container_width=True,
                )
                break
    elif selected_transform == "ppt" and selected_dir:
        _ppt_dir = output_root / selected_dir
        _ppts = sorted(_ppt_dir.glob("*.pptx"))
        if _ppts:
            st.download_button(
                "⬇ Download PPT",
                data=_ppts[-1].read_bytes(),
                file_name=_ppts[-1].name,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="download_ppt_tab2",
                use_container_width=True,
            )

    # --- Handle generate click ---
    if generate_clicked:
        if selected_transform == "markdown":
            st.session_state.markdown_report_status = "processing"
            st.session_state.markdown_report_last_dir = st.session_state.selected_output_dir
            st.session_state.markdown_report_pending = True
            st.rerun()
        elif selected_transform == "HTML":
            st.session_state.html_report_status = "processing"
            st.session_state.html_report_last_dir = st.session_state.selected_output_dir
            st.session_state.html_report_html = None
            st.session_state.html_report_pending = True
            st.session_state.html_report_error = None
            st.rerun()
        elif selected_transform == "image":
            st.session_state.image_report_status = "processing"
            st.session_state.image_report_last_dir = st.session_state.selected_output_dir
            st.session_state.image_report_pending = True
            st.session_state.image_report_error = None
            st.rerun()

    # --- Pending state processing ---
    if (
        st.session_state.html_report_pending
        and st.session_state.html_report_status == "processing"
        and st.session_state.selected_output_dir
    ):
        st.session_state.html_report_pending = False
        html_output, html_error = run_html_report_cli(
            st.session_state.selected_output_dir,
        )
        if html_output:
            st.session_state.html_report_status = "ready"
            st.session_state.html_report_error = None
        else:
            st.session_state.html_report_status = "failed"
            st.session_state.html_report_error = html_error or "Failed to generate HTML report"
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

    if (
        st.session_state.image_report_pending
        and st.session_state.image_report_status == "processing"
        and st.session_state.selected_output_dir
    ):
        st.session_state.image_report_pending = False
        image_output, image_error = run_image_report_cli(
            st.session_state.selected_output_dir,
        )
        if image_output:
            st.session_state.image_report_status = "ready"
            st.session_state.image_report_error = None
        else:
            st.session_state.image_report_status = "failed"
            st.session_state.image_report_error = image_error or "Failed to generate image report"
        st.rerun()

    # Show error/status feedback
    if st.session_state.markdown_report_status == "failed" and selected_transform == "markdown":
        st.error("Failed to generate Markdown report")
    if st.session_state.html_report_status == "failed" and selected_transform == "HTML":
        st.error(st.session_state.html_report_error or "Failed to generate HTML report")
    if st.session_state.image_report_status == "failed" and selected_transform == "image":
        st.error(st.session_state.image_report_error or "Failed to generate image report")

# ------------------------------
# Footer
# ------------------------------
st.markdown(
    '<div class="webis-footer">'
    'Built with <a href="#">Webis</a> · Intelligent Knowledge Pipeline'
    '</div>',
    unsafe_allow_html=True
)
