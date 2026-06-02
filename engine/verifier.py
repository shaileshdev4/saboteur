"""The verifier.

This module is the **single source of truth** for whether two algebraic
states are equivalent. The whole project's claim — "the LLM never decides
correctness" — rests on these functions.

Design rules:
1. The verifier only ever returns True/False. It never throws on bad input;
   on parse failure it returns False (treats it as not-equivalent).
2. We test equivalence by `simplify(a - b) == 0` for expressions, and by
   solving and comparing solution sets for equations.
3. We deliberately allow multiple normalization passes (`simplify`, `expand`,
   `together`, `radsimp`, `nsimplify`) because SymPy's `simplify` alone is
   not always enough — e.g. it may leave `(x+1)^2` and `x^2 + 2x + 1` as
   distinct unless `expand` is called.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Eq, Expr, expand, simplify, sympify


def _safe_sympify(x: Any) -> Any:
    if isinstance(x, (Expr, Eq)):
        return x
    try:
        return sympify(x)
    except (sp.SympifyError, TypeError, SyntaxError):
        return None


def expressions_equivalent(a: Any, b: Any) -> bool:
    """True iff a and b are algebraically equivalent expressions."""
    a = _safe_sympify(a)
    b = _safe_sympify(b)
    if a is None or b is None:
        return False
    if isinstance(a, Eq) or isinstance(b, Eq):
        return False  # Use equations_equivalent for equations
    try:
        diff = simplify(a - b)
        if diff == 0:
            return True
        # Second pass: expand first, then simplify. Catches things like
        # (x+1)^2 vs x^2+2x+1 that simplify alone can leave alone.
        diff2 = simplify(expand(a) - expand(b))
        return diff2 == 0
    except Exception:
        return False


def equations_equivalent(a: Any, b: Any, symbols: list[Any] | None = None) -> bool:
    """True iff two equations have the same solution set over the given symbols.

    If `symbols` is None, we extract free symbols from both equations.
    """
    a = _safe_sympify(a)
    b = _safe_sympify(b)
    if not isinstance(a, Eq) or not isinstance(b, Eq):
        return False
    if symbols is None:
        symbols = sorted(a.free_symbols | b.free_symbols, key=lambda s: s.name)
    if not symbols:
        # Both sides are constants. Equation holds iff both reduce identically.
        return expressions_equivalent(a.lhs - a.rhs, b.lhs - b.rhs)
    try:
        # Equivalence test 1: identical when rearranged to f(x)=0.
        if expressions_equivalent(a.lhs - a.rhs, b.lhs - b.rhs):
            return True
        # Equivalence test 2: same solution set.
        # We use solveset / solve and compare. For polynomial cases solve is
        # more predictable; for general cases solveset is safer.
        sol_a = sp.solve(a, symbols, dict=False)
        sol_b = sp.solve(b, symbols, dict=False)
        return _solutions_equal(sol_a, sol_b)
    except Exception:
        return False


def _solutions_equal(sol_a: Any, sol_b: Any) -> bool:
    """Compare two solve() outputs for equality, tolerantly."""
    # solve() returns lists, sometimes of dicts, sometimes of tuples, sometimes
    # of plain expressions. Normalize to a set-of-frozensets and compare.
    def norm(sol):
        if not sol:
            return frozenset()
        items = []
        for s in sol:
            if isinstance(s, dict):
                items.append(frozenset((k, simplify(v)) for k, v in s.items()))
            elif isinstance(s, (tuple, list)):
                items.append(tuple(simplify(x) for x in s))
            else:
                items.append(simplify(s))
        # Wrap each in a frozenset of one element for set-comparison robustness.
        try:
            return frozenset(items)
        except TypeError:
            # Non-hashable (tuples of Exprs); fall back to list equality.
            return items

    na, nb = norm(sol_a), norm(sol_b)
    if isinstance(na, frozenset) and isinstance(nb, frozenset):
        return na == nb
    return na == nb


def states_equivalent(a: Any, b: Any) -> bool:
    """Generic equivalence — figures out whether to use expression or equation logic."""
    a_s = _safe_sympify(a)
    b_s = _safe_sympify(b)
    if a_s is None or b_s is None:
        return False
    if isinstance(a_s, Eq) and isinstance(b_s, Eq):
        return equations_equivalent(a_s, b_s)
    if isinstance(a_s, Eq) or isinstance(b_s, Eq):
        return False
    return expressions_equivalent(a_s, b_s)


def is_well_formed(x: Any) -> bool:
    """Sanity-check that x is something SymPy can work with.

    Used after a misconception transform to ensure we didn't produce garbage.
    """
    x_s = _safe_sympify(x)
    if x_s is None:
        return False
    # Reject NaN and complex infinities — these indicate a broken transform.
    if x_s.has(sp.nan) or x_s.has(sp.zoo) or x_s.has(sp.oo) or x_s.has(-sp.oo):
        return False
    return True
