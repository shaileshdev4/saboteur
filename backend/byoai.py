"""Bring Your Own AI Answer mode (Phase 3 differentiator).

The user pastes a real LLM-generated algebra solution. We:
  1. Parse the input. We expect either:
     - Structured: problem string + list of step strings (each SymPy-parseable)
     - Best-effort: free text that we clean and split on newlines
  2. For each consecutive pair (step_i, step_i+1), check if they are
     SymPy-equivalent as equations (or expressions).
  3. Find the FIRST step that is not equivalent to its predecessor -this
     is where the AI broke. We also tell the user what the correct next step
     would have been (by solving the equation from the previous step).
  4. Verify the final answer against the original problem.

What we do NOT do:
  - Try to identify *which* of our 12 misconceptions the AI made. That's a
    hard classification problem out of scope for v1.
  - Re-narrate the steps. We just verify.

Crucial design rule: this remains "verifier decides, LLM explains." We use
SymPy for the verdict. (An LLM may help us *clean* the input -strip markdown,
unify variables -but never decides correctness.)
"""
from __future__ import annotations

import re
from typing import Optional

import sympy as sp

from engine.verifier import (
    expressions_equivalent,
    equations_equivalent,
    is_well_formed,
    states_equivalent,
)


# ---------- Input cleaning ----------

_LATEX_REPLACEMENTS = [
    (r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)"),
    (r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)"),
    (r"\\cdot", "*"),
    (r"\\times", "*"),
    (r"\\div", "/"),
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\,", " "),
    (r"\\;", " "),
    (r"\\!", ""),
    (r"\^\{([^{}]+)\}", r"**(\1)"),
    (r"\^([0-9a-zA-Z])", r"**\1"),
    (r"\\\(", ""), (r"\\\)", ""),
    (r"\\\[", ""), (r"\\\]", ""),
    (r"\$+", ""),
]


def clean_latex(s: str) -> str:
    """Convert a LaTeX-ish input to a SymPy-parseable string (best effort)."""
    s = s.strip()
    s = s.replace("·", "*").replace("×", "*")
    for pattern, replacement in _LATEX_REPLACEMENTS:
        s = re.sub(pattern, replacement, s)
    # f'(x) = ...  ->  y = ...  (SymPy-friendly for pasted AI calculus)
    s = re.sub(r"f\s*'\s*\([^)]*\)\s*=", "y =", s, flags=re.IGNORECASE)
    s = re.sub(r"df/dx\s*=", "y =", s, flags=re.IGNORECASE)
    # Implicit multiplication: "2x" -> "2*x", "3(x+1)" -> "3*(x+1)"
    s = re.sub(r"(\d)([a-zA-Z(])", r"\1*\2", s)
    s = re.sub(r"\)([a-zA-Z(\d])", r")*\1", s)
    return s.strip()


def _trim_equation_prose(s: str) -> str:
    """Drop prose glued to an equation, e.g. '2x+6=10 step by step'."""
    s = s.strip()
    m = re.match(
        r"^([-+\d\w*/().^ ]+\s*=\s*[-+\d\w*/().^ ]+)",
        s,
        flags=re.IGNORECASE,
    )
    return m.group(1).strip() if m else s


def parse_step(text: str) -> Optional[sp.Basic]:
    """Parse one step text into a SymPy expression or equation."""
    cleaned = _trim_equation_prose(clean_latex(text))
    # If it has "=", it's an equation.
    if "=" in cleaned:
        sides = cleaned.split("=", 1)
        try:
            lhs = sp.sympify(sides[0])
            rhs = sp.sympify(sides[1])
            return sp.Eq(lhs, rhs)
        except (sp.SympifyError, SyntaxError, TypeError):
            return None
    try:
        expr = sp.sympify(cleaned)
        # Single expression line (common in calculus chains): treat as y = expr
        return sp.Eq(sp.Symbol("y"), expr)
    except (sp.SympifyError, SyntaxError, TypeError):
        return None


def split_free_text_into_steps(blob: str) -> list[str]:
    """Best-effort splitter: try to peel out one equation per line."""
    lines = [line.strip() for line in blob.splitlines() if line.strip()]
    steps: list[str] = []
    for line in lines:
        # Strip leading enumerators like "1.", "Step 1:", "→", etc.
        line = re.sub(r"^(step\s*\d+[:.)]?|\d+[.)]|\u2192|->)\s*", "", line,
                      flags=re.IGNORECASE).strip()
        # Strip surrounding commentary if a line contains an "=" -keep the
        # equation portion only. A line like "So x = 7" should become "x = 7".
        m = re.search(r"([-+\d\w()*/^.\\{} ]+=[-+\d\w()*/^.\\{} ]+)", line)
        if m:
            line = m.group(1).strip()
        if line:
            steps.append(line)
    return steps


# ---------- Verification ----------

def audit_solution(problem_text: str, step_texts: list[str]) -> dict:
    """Run the audit. Returns a structured result.

    Returns:
      {
        "problem_latex": ...,
        "steps": [
          {"index": i, "expression_latex": ..., "is_valid": bool,
           "expected_latex": ..., "error_message": ...},
          ...
        ],
        "first_error_index": Optional[int],
        "final_answer_correct": Optional[bool],
        "summary": str,
      }
    """
    problem = parse_step(problem_text)
    if problem is None:
        return {
            "problem_latex": problem_text,
            "steps": [],
            "first_error_index": None,
            "final_answer_correct": None,
            "summary": ("We couldn't parse the problem. Try pasting it as a "
                        "simple equation like '2x + 5 = 11'."),
        }

    parsed_steps: list[sp.Basic | None] = [problem]
    for st in step_texts:
        parsed_steps.append(parse_step(st))

    # Build per-step result.
    results = []
    first_error = None

    # The "problem" is index 0; we report on subsequent steps.
    for i in range(1, len(parsed_steps)):
        prev = parsed_steps[i - 1]
        curr = parsed_steps[i]
        entry = {"index": i, "expression_latex": "", "is_valid": True,
                 "expected_latex": None, "error_message": None}
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
            entry["error_message"] = ("Can't verify -the previous step "
                                       "didn't parse.")
        elif states_equivalent(prev, curr):
            pass  # explicit OK
        elif _is_valid_root_step(prev, curr):
            pass  # Eq(x, r) is a root of prev -also OK
        else:
            entry["is_valid"] = False
            entry["error_message"] = ("This step doesn't follow from the "
                                       "previous step.")
            # Best-effort: tell user the actual final answer.
            entry["expected_latex"] = _try_canonical_next(prev)
            if first_error is None:
                first_error = i
        results.append(entry)

    # Final answer check: take the last well-formed step. If it's Eq(x, value)
    # and that value solves the original problem, mark correct.
    final_correct: Optional[bool] = None
    if results:
        # Find the last parsed step.
        last_parsed = None
        for step in reversed(parsed_steps[1:]):
            if step is not None:
                last_parsed = step
                break
        if last_parsed is not None and isinstance(last_parsed, sp.Equality):
            try:
                free = list(problem.free_symbols if isinstance(problem, sp.Equality)
                            else problem.free_symbols)
                if free:
                    sym = free[0]
                    if isinstance(last_parsed.lhs, sp.Symbol) and last_parsed.lhs == sym:
                        candidate = last_parsed.rhs
                        lhs_sub = problem.lhs.subs(sym, candidate) if isinstance(problem, sp.Equality) else problem.subs(sym, candidate)
                        rhs_sub = problem.rhs.subs(sym, candidate) if isinstance(problem, sp.Equality) else 0
                        final_correct = sp.simplify(lhs_sub - rhs_sub) == 0
            except Exception:
                final_correct = None

    summary = _build_summary(first_error, final_correct, len(results))

    return {
        "problem_latex": sp.latex(problem),
        "steps": results,
        "first_error_index": first_error,
        "final_answer_correct": final_correct,
        "summary": summary,
    }


def _try_canonical_next(prev_expr) -> Optional[str]:
    """Try to give a hint about what the right next step might look like:
    just solve from `prev` directly and report the solution."""
    try:
        if isinstance(prev_expr, sp.Equality):
            free = list(prev_expr.free_symbols)
            if free:
                sym = free[0]
                sols = sp.solve(prev_expr, sym)
                if sols:
                    if len(sols) == 1:
                        return sp.latex(sp.Eq(sym, sols[0]))
                    return ", ".join(sp.latex(sp.Eq(sym, s)) for s in sols)
    except Exception:
        pass
    return None


def _build_summary(first_error: Optional[int],
                   final_correct: Optional[bool],
                   step_count: int) -> str:
    if step_count == 0:
        return "No steps were provided to audit."
    if first_error is None and final_correct is True:
        return f"All {step_count} step{'s' if step_count != 1 else ''} verified."
    if first_error is None and final_correct is None:
        return f"All {step_count} step transitions verified -couldn't confirm the final answer automatically."
    if first_error is None and final_correct is False:
        return ("Every step transition checks out, but the final answer "
                "doesn't satisfy the original problem. Suspect an earlier "
                "interpretation error.")
    return (f"The AI's work breaks at step {first_error}. Steps before that "
            "are consistent with the previous line.")


def _is_valid_root_step(prev, curr) -> bool:
    """True if curr is Eq(x, r) where r satisfies prev (as an equation)."""
    if not (isinstance(prev, sp.Equality) and isinstance(curr, sp.Equality)):
        return False
    if not isinstance(curr.lhs, sp.Symbol):
        return False
    sym = curr.lhs
    r = curr.rhs
    try:
        lhs_sub = prev.lhs.subs(sym, r)
        rhs_sub = prev.rhs.subs(sym, r)
        return sp.simplify(lhs_sub - rhs_sub) == 0
    except Exception:
        return False
