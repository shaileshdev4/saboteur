"""Coefficient and arithmetic-slip misconceptions."""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


class DroppedCoefficient(Misconception):
    id = "dropped_coefficient"
    name = "Coefficient dropped"
    description = (
        "A coefficient is silently dropped from a term. E.g., 3x becomes x, "
        "or 5x + 2 becomes x + 2."
    )
    category = "coefficient"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY, OperationType.TRANSPOSE,
                      OperationType.EXPAND)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        # Need a coefficient > 1 (in abs value) on a variable somewhere.
        return _has_non_unit_coefficient(step.expression)

    def apply(self, step, solution, step_index):
        expr = step.expression
        new_expr = _drop_first_non_unit_coefficient(expr)
        if new_expr == expr:
            return step
        return Step(step.index, new_expr, step.operation, note=f"sabotage:{self.id}")


class OffByOneConstant(Misconception):
    id = "off_by_one_constant"
    name = "Off-by-one constant slip"
    description = (
        "An arithmetic slip changes a constant by ±1 during simplification. "
        "Common pattern in solving by inspection."
    )
    category = "coefficient"
    difficulty = 4    # subtle — only off by 1
    applicable_ops = (OperationType.SIMPLIFY, OperationType.TRANSPOSE,
                      OperationType.DIVIDE_BOTH_SIDES)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        return _has_nonzero_constant(step.expression)

    def apply(self, step, solution, step_index):
        expr = step.expression
        new_expr = _adjust_first_constant(expr, delta=1)
        if new_expr == expr:
            new_expr = _adjust_first_constant(expr, delta=-1)
        if new_expr == expr:
            return step
        return Step(step.index, new_expr, step.operation, note=f"sabotage:{self.id}")


# --- helpers ---

def _has_non_unit_coefficient(expr) -> bool:
    if isinstance(expr, sp.Equality):
        return (_has_non_unit_coefficient(expr.lhs)
                or _has_non_unit_coefficient(expr.rhs))
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Mul):
            coeff = sp.S.One
            has_var = False
            for a in sub.args:
                if a.is_number:
                    coeff *= a
                elif a.free_symbols:
                    has_var = True
            if has_var and abs(coeff) != 1 and coeff != 0:
                return True
    return False


def _drop_first_non_unit_coefficient(expr):
    """Find the first Mul(coeff, var...) with |coeff|>1 and replace with var..."""
    if isinstance(expr, sp.Equality):
        # Try lhs first.
        new_lhs = _drop_first_non_unit_coefficient(expr.lhs)
        if new_lhs != expr.lhs:
            return Eq(new_lhs, expr.rhs)
        new_rhs = _drop_first_non_unit_coefficient(expr.rhs)
        return Eq(expr.lhs, new_rhs)
    if not isinstance(expr, sp.Basic):
        return expr
    # Walk via replace.
    def matcher(node):
        if isinstance(node, sp.Mul):
            coeff = sp.S.One
            rest = []
            for a in node.args:
                if a.is_number:
                    coeff *= a
                else:
                    rest.append(a)
            if rest and abs(coeff) != 1 and coeff != 0:
                return True
        return False
    def replacer(node):
        rest = [a for a in node.args if not a.is_number]
        return sp.Mul(*rest) if rest else node
    # Use xreplace to do single replacement via traversal.
    # We'll iterate over args and replace only the first match.
    result, changed = _replace_first(expr, matcher, replacer)
    return result if changed else expr


def _has_nonzero_constant(expr):
    if isinstance(expr, sp.Equality):
        return _has_nonzero_constant(expr.lhs) or _has_nonzero_constant(expr.rhs)
    for sub in sp.preorder_traversal(expr):
        if sub.is_number and sub != 0 and not sub.is_Float:
            return True
    return False


def _adjust_first_constant(expr, delta=1):
    """Add `delta` to the first integer-valued constant subterm we find."""
    def matcher(node):
        # Must be a number, integer, nonzero, and not part of a Pow exponent.
        return (getattr(node, "is_number", False) and node != 0
                and node.is_integer)
    def replacer(node):
        return node + delta
    result, changed = _replace_first(expr, matcher, replacer,
                                     skip_pow_exponent=True)
    return result if changed else expr


def _replace_first(expr, matcher, replacer, skip_pow_exponent=False):
    """Replace the first node (preorder) satisfying matcher; return (new, True/False)."""
    # We implement our own walk because sympy.replace doesn't naturally do
    # "first only."
    state = {"done": False}

    def walk(node, in_exponent=False):
        if state["done"]:
            return node, False
        if skip_pow_exponent and in_exponent:
            # Don't match exponents — substituting 2 with 3 in x**2 would
            # produce x**3 which is structurally different in a way that
            # masks subtlety.
            return node, False
        if matcher(node):
            state["done"] = True
            return replacer(node), True
        if isinstance(node, sp.Equality):
            new_lhs, c1 = walk(node.lhs)
            new_rhs, c2 = walk(node.rhs)
            return Eq(new_lhs, new_rhs), c1 or c2
        if not isinstance(node, sp.Basic) or not node.args:
            return node, False
        new_args = []
        changed = False
        if isinstance(node, sp.Pow) and skip_pow_exponent:
            base, exp = node.args
            new_base, c_b = walk(base)
            # do not walk into exp
            new_args = [new_base, exp]
            changed = c_b
        else:
            for a in node.args:
                new_a, c = walk(a)
                new_args.append(new_a)
                changed = changed or c
        if changed:
            try:
                return node.func(*new_args), True
            except Exception:
                return node, False
        return node, False

    new_expr, changed = walk(expr)
    return new_expr, changed


register(DroppedCoefficient())
register(OffByOneConstant())
