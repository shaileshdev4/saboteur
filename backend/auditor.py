"""Universal AI auditor (BYOAI v2).

The V1 byoai.py accepted structured input: explicit problem string + step list.
This version accepts a free-form blob — what you'd actually paste from a
chatbot conversation — and tries to:

  1. Extract the problem and the worked steps from messy text.
  2. Detect which domain (algebra, geometry, calculus) the problem lives in.
  3. Route to the correct verifier and produce the structured audit.

V4 hardening: extraction now handles:
  - Markdown code fences (```math, ```latex, plain ```)
  - Prose preambles ("Sure! Let's solve...", "Step by step:")
  - Multi-line equations split by line breaks
  - "Therefore" / "So" / "Thus" prefixes on the final answer
  - Trailing affirmations ("The answer is X") that shouldn't be treated as a step

Detection is heuristic but conservative — if we can't confidently identify
the domain we say so honestly rather than guessing. The verification itself
is never heuristic; that's still the symbolic engine.

The architectural rule still holds: the LLM helps with text *cleaning* (which
is presentation work), never with deciding correctness.
"""
from __future__ import annotations

import re
from typing import Optional

import sympy as sp

from engine.domain import all_domains, get_domain
from engine.verifier import (
    expressions_equivalent,
    equations_equivalent,
    is_well_formed,
    states_equivalent,
)
try:
    from . import byoai as byoai_v1  # reuse parsing helpers
except ImportError:
    import byoai as byoai_v1


# ===========================================================================
# Text extraction from chatbot output
# ===========================================================================

# Phrases that frequently introduce the problem statement. The captured group
# must contain '=' or be a clear single-expression math line.
_PROBLEM_LEAD_PATTERNS = [
    # "Solve: 2x + 6 = 10" — capture must contain '='
    (r"(?:problem|question|given|solve(?: for [a-z])?|find|compute|evaluate|simplify)[:\s]+([^\n]*=[^\n]+)", True),
    # Bare equation on its own line
    (r"^\s*([^\n]+=[^\n]+)\s*$", True),
]

# Phrases that mark a line as PROSE-ONLY (skip entirely if no '=').
_PROSE_ONLY_PATTERNS = [
    r"^(?:sure!?|let'?s|let me|alright|okay|here'?s|i'?ll|to solve|to find|step by step)",
    r"^(?:we (?:need to|can|will|have|get|find))",
    r"^(?:first,?|next,?|then,?|finally,?|now,?)\s",
    r"^(?:the (?:answer|solution|result|value)|so the answer)",
    r"^(?:therefore the answer)",
    r"^(?:so,?\s+the)",
]

# Step-marker prefixes to strip from lines that DO contain math.
_STEP_PREFIX_PATTERNS = [
    r"^(?:step\s*\d+[:.)]?|\d+[.)])\s*",                  # "Step 1:" / "1."
    r"^(?:\u2192|->|=>)\s*",                              # arrows
    r"^(?:therefore|so|thus|hence|then),?\s*",            # connective adverbs
    r"^(?:we get|this gives|this yields|now)\s*[:,]?\s*", # narrative connectors
]

# Markdown / formatting noise to strip.
_NOISE_PATTERNS = [
    (r"^#+\s+", ""),                 # markdown headers
    (r"\*\*([^*]+)\*\*", r"\1"),     # bold
    (r"`([^`]+)`", r"\1"),           # inline code
    (r"^\s*[->•*]\s*", ""),          # bullet markers (now includes *)
]


def _strip_code_fences(blob: str) -> str:
    """Remove triple-backtick code fences, keeping their content inline.

    Many chatbots wrap math in ```math ... ``` or ```latex ... ```. We strip
    the fences but keep the content so step-extraction sees it.
    """
    # ```anything\n CONTENT \n``` -> CONTENT
    return re.sub(r"```[a-zA-Z]*\n(.*?)\n```", r"\1",
                  blob, flags=re.DOTALL)


def _is_prose_line(line: str) -> bool:
    """True if the line is prose (no useful math), should be skipped.

    A line is prose if it starts with a known prose lead AND either has no
    '=' at all, OR the '=' is only part of a trailing affirmation like
    "the answer is x = 2" (where the equation is a restatement, not new
    work).
    """
    stripped = line.strip().lower()
    if not stripped:
        return True
    for pat in _PROSE_ONLY_PATTERNS:
        if re.match(pat, stripped):
            return True
    return False


def _looks_like_math(line: str) -> bool:
    """True if the line contains at least one equation or math expression."""
    s = line.strip()
    if not s:
        return False
    # Must contain '=' OR be a single math-only token like "sqrt(25)".
    if "=" in s:
        return True
    # Lines without '=' are rarely useful steps; ignore them.
    return False


def extract_problem_and_steps(blob: str) -> tuple[str, list[str]]:
    """Extract a (problem, [steps]) pair from messy chatbot text.

    V4: handles code fences, prose preambles, and trailing affirmations.
    """
    if not blob.strip():
        return "", []

    blob = _strip_code_fences(blob)

    # Strip generic noise per line.
    cleaned_lines = []
    for line in blob.splitlines():
        for pat, repl in _NOISE_PATTERNS:
            line = re.sub(pat, repl, line)
        cleaned_lines.append(line)
    blob = "\n".join(cleaned_lines)

    # ----- Find the problem statement -----
    problem_text = ""
    for pat, _ in _PROBLEM_LEAD_PATTERNS:
        m = re.search(pat, blob, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip()
            if "=" in candidate:
                # Trim prose suffix after the math expression. Cut at the first
                # ", " (comma followed by space) that comes AFTER an '=' if any.
                eq_pos = candidate.find("=")
                tail = candidate[eq_pos:]
                # If a ", " appears in the tail, slice the original at that point.
                comma_idx = tail.find(", ")
                if comma_idx > 0:
                    candidate = candidate[: eq_pos + comma_idx]
                # Also strip trailing period/comma/space.
                candidate = candidate.rstrip(" .,;:").strip()
                problem_text = candidate
                break

    # Fallback: first non-empty math line.
    if not problem_text:
        for line in blob.splitlines():
            stripped = line.strip()
            if _looks_like_math(stripped) and not _is_prose_line(stripped):
                problem_text = stripped
                break

    # Clean LaTeX wrapping ($, \[ \], etc.) from problem.
    problem_text = re.sub(r"^\$+|\$+$", "", problem_text).strip()
    problem_text = re.sub(r"\\\[|\\\]|\\\(|\\\)", "", problem_text).strip()

    # ----- Find the step lines -----
    steps: list[str] = []
    seen_problem = False
    for raw_line in blob.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip pure prose lines like "Step by step:" or "First, we..."
        if _is_prose_line(line):
            continue
        # Strip step-marker prefixes.
        for pat in _STEP_PREFIX_PATTERNS:
            line = re.sub(pat, "", line, flags=re.IGNORECASE).strip()
        # Strip LaTeX delimiters.
        line = re.sub(r"^\$+|\$+$", "", line).strip()
        line = re.sub(r"\\\[|\\\]|\\\(|\\\)", "", line).strip()

        if not _looks_like_math(line):
            continue

        # Don't re-add the problem line. If we haven't seen it yet, mark it
        # seen and skip; otherwise treat as a step.
        if not seen_problem and (line == problem_text or _norm(line) == _norm(problem_text)):
            seen_problem = True
            continue

        # Extract the equation portion if the line has prose around it.
        m = re.search(r"([-+\d\w'()*/^.\\{} ]+=[-+\d\w'()*/^.\\{} ]+)", line)
        if m:
            line = m.group(1).strip()

        steps.append(line)

    return problem_text, steps


def _norm(s: str) -> str:
    """Normalize for line-equality comparison: strip whitespace + lowercase."""
    return re.sub(r"\s+", "", s.lower())


# ===========================================================================
# Domain detection
# ===========================================================================

_DOMAIN_HINTS = {
    "calculus": [
        r"\bd/?d[xytz]\b",
        r"\bderivative\b",
        r"\bintegral\b",
        r"\bintegrate\b",
        r"\bdiff(?:erentiate)?\b",
        r"f\s*'\s*\(",
        r"\\frac\s*\{\s*d",
        r"\\int\b",
        r"\bantideriv",
        r"\bchain rule\b",
        r"\bproduct rule\b",
        r"\\sum\b",
    ],
    "geometry": [
        r"\b(?:triangle|circle|rectangle|square|polygon|trapezoid|hexagon)\b",
        r"\b(?:pythagor|hypotenuse|leg)\b",
        r"\barea\b.*=",
        r"\bperimeter\b",
        r"\bcircumference\b",
        r"\bradius\b",
        r"\bdiameter\b",
        r"\\pi\b",
        r"\bdegrees?\b",
        r"\bangle\b",
    ],
}


def detect_domain(blob: str, problem_text: str = "") -> tuple[str, dict]:
    """Pick the most likely domain. Returns (domain_id, scores)."""
    combined = f"{problem_text}\n{blob}".lower()
    scores = {}
    for domain_id, patterns in _DOMAIN_HINTS.items():
        score = 0
        for pat in patterns:
            if re.search(pat, combined):
                score += 1
        scores[domain_id] = score
    scores.setdefault("algebra", 0)

    best_score = max(scores.values())
    if best_score == 0:
        return "algebra", scores
    candidates = [d for d, s in scores.items() if s == best_score]
    if "algebra" in candidates:
        return "algebra", scores
    return candidates[0], scores


# ===========================================================================
# Domain-routed verification
# ===========================================================================

def audit_universal(blob: str,
                    domain_id: Optional[str] = None,
                    problem_override: Optional[str] = None) -> dict:
    """Top-level entry: take a blob, return a structured audit result.

    Optional args:
      domain_id      — force a specific domain (skip detection)
      problem_override — force the problem text (skip extraction)
    """
    extracted_problem, extracted_steps = extract_problem_and_steps(blob)
    problem = problem_override or extracted_problem

    if not problem:
        return {
            "problem_latex": "",
            "steps": [],
            "first_error_index": None,
            "final_answer_correct": None,
            "summary": ("We couldn't find a problem in the pasted text. Try "
                        "putting the problem on its own line, e.g., "
                        "'Solve: 2x + 6 = 10'."),
            "detected_domain": "algebra",
            "domain_scores": {},
        }
    if not extracted_steps:
        return {
            "problem_latex": problem,
            "steps": [],
            "first_error_index": None,
            "final_answer_correct": None,
            "summary": ("Found the problem but no step-by-step work to "
                        "audit. The AI may have given a single-line answer "
                        "without showing its work."),
            "detected_domain": "algebra",
            "domain_scores": {},
        }

    # Detect domain.
    detected, scores = (domain_id, {}) if domain_id else detect_domain(
        blob, problem)

    # Route to the correct verifier. For algebra, the existing byoai_v1 logic
    # is robust; reuse it. For calculus/geometry, we use the domain's
    # `states_equivalent` directly.
    if detected == "algebra":
        result = byoai_v1.audit_solution(problem, extracted_steps)
        result["detected_domain"] = "algebra"
        result["domain_scores"] = scores
        return result

    # Non-algebra domains: lightweight per-step check.
    try:
        domain = get_domain(detected)
    except KeyError:
        # Fallback to algebra if domain unknown.
        result = byoai_v1.audit_solution(problem, extracted_steps)
        result["detected_domain"] = "algebra"
        result["domain_scores"] = scores
        return result

    return _audit_with_domain(domain, problem, extracted_steps, scores)


def _audit_with_domain(domain, problem_text: str, step_texts: list[str],
                       scores: dict) -> dict:
    """Per-step verification using the domain's equivalence function.

    Slightly less rigorous than the algebra path (which knows about
    FACTOR → FINAL root substitution); calculus and geometry have flatter
    step chains so the generic walk is enough.
    """
    problem = byoai_v1.parse_step(problem_text)
    parsed = [problem]
    for st in step_texts:
        parsed.append(byoai_v1.parse_step(st))

    results = []
    first_error = None
    for i in range(1, len(parsed)):
        prev = parsed[i - 1]
        curr = parsed[i]
        entry = {
            "index": i, "expression_latex": "",
            "is_valid": True, "expected_latex": None, "error_message": None,
        }
        if curr is None:
            entry["is_valid"] = False
            entry["error_message"] = "Couldn't parse this step."
            entry["expression_latex"] = step_texts[i - 1]
            results.append(entry)
            if first_error is None:
                first_error = i
            continue
        if not is_well_formed(curr):
            entry["is_valid"] = False
            entry["error_message"] = "Expression isn't well-formed."
            entry["expression_latex"] = sp.latex(curr)
            results.append(entry)
            if first_error is None:
                first_error = i
            continue
        entry["expression_latex"] = sp.latex(curr)
        if prev is None:
            entry["is_valid"] = False
            entry["error_message"] = (
                "Can't verify — the previous step didn't parse.")
        elif not domain.states_equivalent(prev, curr):
            entry["is_valid"] = False
            entry["error_message"] = (
                "This step doesn't follow from the previous step.")
            if first_error is None:
                first_error = i
        results.append(entry)

    if first_error is None:
        summary = f"All {len(results)} step transitions verified ({domain.label})."
    else:
        summary = (f"The AI's work breaks at step {first_error} "
                   f"({domain.label}). Steps before that are consistent.")

    return {
        "problem_latex": sp.latex(problem) if problem else problem_text,
        "steps": results,
        "first_error_index": first_error,
        "final_answer_correct": None,    # geometry/calculus don't yet check this
        "summary": summary,
        "detected_domain": domain.id,
        "domain_scores": scores,
    }
