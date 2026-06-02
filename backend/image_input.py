"""Image input: transcribe a photo of a worked solution to text.

We do NOT do OCR ourselves. Two real-world options:

1. **Multimodal LLM** (default if MULTIMODAL_API_KEY is set). We send the
   image base64 to a model that can see images (Claude, GPT-4o, etc.)
   and ask it to transcribe the math as plain text. Accuracy is good on
   handwritten algebra; less reliable on cluttered photos.

2. **Mathpix** (fallback if MATHPIX_APP_ID + MATHPIX_APP_KEY are set).
   Specialist math OCR. More accurate but paid.

If neither is configured, the endpoint returns a clear error saying so —
we don't ship a tesseract fallback because Tesseract butchers equations
and we'd be lying about quality.

After transcription, the result is fed directly to the universal auditor,
so image -> audit is a single user-visible flow.

PRIVACY: the image is sent to whichever provider is configured. We do NOT
store images on disk; they're held in memory for the transcribe call and
discarded.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

import httpx


# ---------- Provider selection ----------

MULTIMODAL_API_KEY = os.environ.get("MULTIMODAL_API_KEY", "").strip()
MULTIMODAL_API_BASE = os.environ.get(
    "MULTIMODAL_API_BASE", "https://api.anthropic.com/v1")
MULTIMODAL_MODEL = os.environ.get("MULTIMODAL_MODEL", "claude-sonnet-4-5")

MATHPIX_APP_ID = os.environ.get("MATHPIX_APP_ID", "").strip()
MATHPIX_APP_KEY = os.environ.get("MATHPIX_APP_KEY", "").strip()


def is_configured() -> bool:
    return bool(MULTIMODAL_API_KEY) or bool(MATHPIX_APP_KEY)


def transcribe_image(image_bytes: bytes, content_type: str = "image/jpeg",
                     hint: Optional[str] = None) -> dict:
    """Transcribe an image of math work to text.

    Returns:
      { ok: bool, text: str, provider: str, error: str }
    """
    if MULTIMODAL_API_KEY:
        return _via_multimodal_llm(image_bytes, content_type, hint)
    if MATHPIX_APP_KEY:
        return _via_mathpix(image_bytes, content_type)
    return {
        "ok": False,
        "text": "",
        "provider": "none",
        "error": ("Image transcription is not configured. Set "
                  "MULTIMODAL_API_KEY (for Claude/GPT-4o vision) or "
                  "MATHPIX_APP_ID + MATHPIX_APP_KEY (for Mathpix)."),
    }


# ---------- Provider implementations ----------

# Strict prompt that asks for transcription only — no judging, no solving,
# no commentary. We want exactly the text that's in the image.
_TRANSCRIBE_SYSTEM = """You are an OCR transcription tool for math.

Your one job: read the math equations and step-by-step work in this image and output it as PLAIN TEXT — one line per step.

Rules:
- Output equations using simple text math, NOT LaTeX:
    2x + 6 = 10        (good)
    \\frac{1}{2}x      (bad — use (1/2)*x)
    \\sqrt{x}          (bad — use sqrt(x))
- Each step on its own line.
- The original problem (if visible) on the FIRST line.
- Do NOT solve, judge, or annotate. Do NOT add commentary like "Step 1:". Just the math.
- If the image is unclear or contains no math, output exactly: UNCLEAR.
- If parts of the image are unreadable, transcribe what you can and omit the rest. Never make up steps that aren't visible.

Do NOT output anything other than the transcribed math lines (or UNCLEAR)."""


def _via_multimodal_llm(image_bytes: bytes, content_type: str,
                        hint: Optional[str]) -> dict:
    """Send the image to an Anthropic-compatible multimodal endpoint."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    # Anthropic Messages API format.
    payload = {
        "model": MULTIMODAL_MODEL,
        "max_tokens": 800,
        "system": _TRANSCRIBE_SYSTEM,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (f"Transcribe this. {hint or ''}".strip()),
                    },
                ],
            }
        ],
    }
    headers = {
        "x-api-key": MULTIMODAL_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{MULTIMODAL_API_BASE}/messages",
                            json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Anthropic format: { "content": [{ "type": "text", "text": "..." }] }
            blocks = data.get("content", [])
            text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            text = "\n".join(text_parts).strip()
    except Exception as e:
        return {
            "ok": False, "text": "", "provider": "multimodal_llm",
            "error": f"Multimodal call failed: {e}",
        }
    if text == "UNCLEAR" or not text:
        return {
            "ok": False, "text": "", "provider": "multimodal_llm",
            "error": ("The image was too unclear to transcribe reliably. "
                      "Try better lighting or a flatter photo."),
        }
    return {
        "ok": True, "text": text, "provider": "multimodal_llm", "error": "",
    }


def _via_mathpix(image_bytes: bytes, content_type: str) -> dict:
    """Send the image to Mathpix v3 endpoint."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "src": f"data:{content_type};base64,{b64}",
        "formats": ["text"],
        "data_options": {"include_asciimath": True},
        "line_data": True,
    }
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post("https://api.mathpix.com/v3/text",
                            json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            text = data.get("text", "").strip()
    except Exception as e:
        return {
            "ok": False, "text": "", "provider": "mathpix",
            "error": f"Mathpix call failed: {e}",
        }
    if not text:
        return {
            "ok": False, "text": "", "provider": "mathpix",
            "error": "Mathpix returned no text — image likely unclear.",
        }
    return {"ok": True, "text": text, "provider": "mathpix", "error": ""}
