"""
Gemini Unified Text Client
===========================

Shared helper for calling ``gemini-3-pro-image-preview`` in **text-only
mode** (``responseModalities: ["text"]``).  Used by both the RAG analysis
stage and the Content Planner stage of the image-report pipeline.

Endpoint & key are identical to the ones used by ``ImageRenderAgent``,
keeping everything on a single model.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — same endpoint / key as ImageRenderAgent
# ---------------------------------------------------------------------------
_GEMINI_URL = (
    "https://zhouliuai.online/v1beta/models/"
    "gemini-3-pro-image-preview:generateContent"
)
_ENV_KEY = "ZHOULIU_API_KEY"

_MAX_RETRIES = 2
_RETRY_DELAY = 5  # seconds
_TIMEOUT = 180     # seconds per request


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_gemini_text(
    user_prompt: str,
    system_prompt: str | None = None,
    *,
    json_mode: bool = False,
    api_key: str | None = None,
) -> str:
    """Call Gemini in text-only mode and return the text response.

    Parameters
    ----------
    user_prompt:
        The user message / question.
    system_prompt:
        Optional system message prepended as context.
    json_mode:
        If *True*, append a JSON-schema instruction so the model returns
        valid JSON.  (``responseMimeType`` is NOT supported by the image-
        preview model, so we only hint via prompt.)
    api_key:
        Explicit key override; falls back to ``ZHOULIU_API_KEY`` env var.

    Returns
    -------
    str
        Raw text from the model.

    Raises
    ------
    RuntimeError
        If all retry attempts fail.
    """
    key = api_key or os.environ.get(_ENV_KEY, "")
    if not key:
        raise RuntimeError(
            f"Gemini text call requires the {_ENV_KEY} env var to be set."
        )

    # Build contents list
    contents: List[Dict[str, Any]] = []

    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": f"[System Instructions]\n{system_prompt}"}],
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood. I will follow those instructions."}],
        })

    contents.append({
        "role": "user",
        "parts": [{"text": user_prompt}],
    })

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "responseModalities": ["text"],
        },
    }

    url = f"{_GEMINI_URL}?key={key}"
    headers = {"Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 2):
        try:
            logger.info(
                "Gemini text request attempt %d/%d …",
                attempt,
                _MAX_RETRIES + 1,
            )
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=_TIMEOUT,
            )

            if resp.status_code == 429:
                wait = _RETRY_DELAY * attempt
                logger.warning("Rate limited (429). Retrying in %ds…", wait)
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                error_text = resp.text[:500]
                raise RuntimeError(
                    f"Gemini API returned {resp.status_code}: {error_text}"
                )

            data = resp.json()
            return _extract_text(data)

        except RuntimeError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini text call failed: %s", exc)
            if attempt <= _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    raise RuntimeError(
        f"Gemini text generation failed after {_MAX_RETRIES + 1} attempts: "
        f"{last_error}"
    )


# ---------------------------------------------------------------------------
# JSON parsing helper (shared with agents)
# ---------------------------------------------------------------------------

def parse_json_response(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction from model output."""
    raw = text.strip()

    # Strip markdown code fences
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        if first_nl != -1:
            raw = raw[first_nl + 1:]
    if raw.endswith("```"):
        raw = raw[:-3].rstrip()

    # Direct parse
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Find outermost braces
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start: end + 1]
        # Fix trailing commas
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise ValueError("Unable to parse valid JSON from Gemini response")


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _extract_text(response_json: Dict[str, Any]) -> str:
    """Walk Gemini response and return concatenated text parts."""
    candidates = response_json.get("candidates", [])
    if not candidates:
        feedback = response_json.get("promptFeedback", {})
        block_reason = feedback.get("blockReason", "")
        if block_reason:
            raise RuntimeError(
                f"Gemini blocked the request: {block_reason}. "
                f"Feedback: {json.dumps(feedback, ensure_ascii=False)}"
            )
        raise RuntimeError(
            "Gemini returned no candidates. Full response: "
            + json.dumps(response_json, ensure_ascii=False)[:1000]
        )

    texts: list[str] = []
    for candidate in candidates:
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                texts.append(part["text"])

    if not texts:
        raise RuntimeError(
            "Gemini response contained no text parts. "
            f"Raw: {json.dumps(response_json, ensure_ascii=False)[:1000]}"
        )

    return "\n".join(texts)
