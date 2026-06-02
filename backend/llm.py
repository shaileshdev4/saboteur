"""LLM presentation layer.

The LLM does TWO things and NOTHING ELSE:
  1. `phrase_step()`: turn a SymPy expression into one natural sentence
     describing what was done. NEVER says "correctly" or "this gives us"
     or evaluates the work.
  2. `explain_misconception()`: given a misconception name + description +
     the truth/shown LaTeX, write a short 2-sentence explanation suitable
     for showing AFTER the reveal.

These are explicit guardrails:
  - Prompts forbid evaluative adjectives (correct, right, wrong, etc.)
  - A post-filter strips banned phrases as a belt-and-suspenders backup.
  - Responses are cached per content hash; demo replays don't burn tokens.

If no API key is configured, both functions return graceful fallbacks
based on the operation tag / misconception description directly. This means
the whole system works fine without LLM — it's narration polish, not the
foundation.

Provider: LLM.API (https://llmapi.ai/) — sponsor of the hackathon.
Configured via env var LLM_API_KEY. Their API is OpenAI-compatible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Optional

import httpx


# Cache file lives next to the DB.
CACHE_PATH = os.environ.get("LLM_CACHE_PATH", "llm_cache.json")
_cache: dict[str, str] | None = None


def _load_cache() -> dict[str, str]:
    global _cache
    if _cache is None:
        try:
            with open(CACHE_PATH) as f:
                _cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(_cache, f)
    except OSError:
        pass


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


# ---------- Provider call ----------

LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.llmapi.ai/v1")
LLM_API_MODEL = os.environ.get("LLM_API_MODEL", "gpt-4o-mini")

_BANNED_PHRASES = [
    r"\bcorrectly\b",
    r"\bcorrect step\b",
    r"\bthis is correct\b",
    r"\bthis is right\b",
    r"\bthis is wrong\b",
    r"\bvalid step\b",
    r"\binvalid step\b",
    r"\bthe right answer\b",
    r"\bthe wrong answer\b",
]
_BANNED_RE = re.compile("|".join(_BANNED_PHRASES), re.IGNORECASE)


def _strip_evaluative_language(text: str) -> str:
    """Belt-and-suspenders: strip phrases that judge correctness."""
    return _BANNED_RE.sub("", text).strip()


def _call_llm(prompt: str, system: str, max_tokens: int = 220) -> str:
    """Single-shot completion. Returns text or empty string on failure."""
    cache = _load_cache()
    ck = _cache_key(f"{system}||{prompt}")
    if ck in cache:
        return cache[ck]

    if not LLM_API_KEY:
        return ""

    payload = {
        "model": LLM_API_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(f"{LLM_API_BASE}/chat/completions",
                            json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""

    text = _strip_evaluative_language(text)
    cache[ck] = text
    _save_cache()
    return text


# ---------- Public API ----------

STEP_PHRASING_SYSTEM = """You narrate algebra steps in plain English for a STEM auditing game.
You receive: a SymPy LaTeX expression, an operation tag (e.g., transpose, expand), and a brief operation note.

ABSOLUTE RULES:
- Output ONE short sentence (max 18 words), describing what was DONE.
- NEVER say "correctly", "this gives us the answer", "this step is right", "valid", or any word that judges whether the step is right or wrong. You are a narrator, not a verifier.
- Use present-tense, action-focused phrasing: "We subtract 5 from both sides" not "We subtracted 5 and got the right answer."
- Write for a high school student. No hedging, no padding.

You do NOT know whether the step is correct. Do not speculate.
"""

REVEAL_SYSTEM = """You are explaining an algebra misconception to a student AFTER they finished a round.
You receive: the misconception's name, its plain-language description, and two LaTeX expressions: what the truth should have been versus what the AI showed.

ABSOLUTE RULES:
- Output exactly 2 sentences.
- The first sentence names the misconception in plain English and points out exactly what was changed (e.g., "The sign on the moved 5 was kept positive instead of becoming negative.").
- The second sentence explains the underlying confusion (why students/AIs do this).
- DO NOT lecture. DO NOT add an extra "remember to..." sentence.
- DO NOT use the words "correctly", "validly", "right answer", "wrong answer". You are explaining a mechanism, not grading.
"""


def phrase_step(latex: str, operation: str, note: str) -> str:
    if not LLM_API_KEY:
        return _fallback_step_phrasing(operation, note)
    prompt = (
        f"Expression (LaTeX): {latex}\n"
        f"Operation: {operation}\n"
        f"Note: {note}\n\n"
        "Narrate this step in one sentence."
    )
    result = _call_llm(prompt, STEP_PHRASING_SYSTEM, max_tokens=60)
    return result or _fallback_step_phrasing(operation, note)


def _fallback_step_phrasing(operation: str, note: str) -> str:
    """Tiny rule-based narrator used when no LLM is configured."""
    mapping = {
        "initial": "Starting from the original equation",
        "simplify": "Combining like terms",
        "transpose": "Moving terms across the equals sign",
        "multiply_both_sides": "Multiplying both sides",
        "divide_both_sides": "Dividing both sides",
        "expand": "Distributing the product",
        "factor": "Factoring",
        "square_root": "Taking the square root of both sides",
        "substitute": "Substituting a value",
        "final": "Reading off the result",
    }
    base = mapping.get(operation, "Performing an operation")
    if note and not note.startswith("sabotage:"):
        return f"{base} — {note}"
    return base


def explain_misconception(misconception_name: str,
                          misconception_description: str,
                          truth_latex: str,
                          shown_latex: str) -> str:
    """Explain what went wrong, AFTER the reveal."""
    if not LLM_API_KEY:
        return _fallback_explanation(misconception_name, misconception_description)
    prompt = (
        f"Misconception: {misconception_name}\n"
        f"Description: {misconception_description}\n\n"
        f"What the truth should have been (LaTeX): {truth_latex}\n"
        f"What the AI showed (LaTeX): {shown_latex}\n\n"
        "Explain in 2 sentences exactly what was changed and the underlying confusion."
    )
    result = _call_llm(prompt, REVEAL_SYSTEM, max_tokens=160)
    return result or _fallback_explanation(misconception_name, misconception_description)


def _fallback_explanation(name: str, description: str) -> str:
    return f"{name}. {description}"
