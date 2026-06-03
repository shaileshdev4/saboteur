"""Operation-asymmetry and cancellation misconceptions.

These are the deeply-confused-student errors: applying an operation to only
one side of an equation, or cancelling across a sum.
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


class OperationOnOneSideOnly(Misconception):
    id = "operation_one_side_only"
    name = "Operation applied to only one side"
    description = (
        "An arithmetic operation (subtraction, division) is applied to one "
        "side of the equation but forgotten on the other. E.g., from "
        "2x + 6 = 10 the student writes 2x = 10 (only subtracting 6 from the "
        "left) instead of 2x = 4."
    )
    category = "operation_one_side"
    difficulty = 3
    applicable_ops = (OperationType.TRANSPOSE, OperationType.DIVIDE_BOTH_SIDES,
                      OperationType.MULTIPLY_BOTH_SIDES)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        if step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        return isinstance(prev, sp.Equality) and isinstance(step.expression, sp.Equality)

    def apply(self, step, solution, step_index):
        prev = solution.steps[step_index - 1].expression
        curr = step.expression
        # Keep prev.rhs (= forget the operation on rhs); use curr.lhs.
        return Step(step.index, Eq(curr.lhs, prev.rhs), step.operation,
                    note=f"sabotage:{self.id}")


class CancellationAcrossSum(Misconception):
    id = "cancellation_across_sum"
    name = "Illegal cancellation across a sum"
    description = (
        "A common factor is 'cancelled' across a sum, dropping the additive "
        "structure. E.g., (3x + 6)/3 = x + 6, ignoring that 6 must also be "
        "divided. Or x/(x+1) = 1/(1+1)."
    )
    category = "cancellation"
    difficulty = 4
    applicable_ops = (OperationType.SIMPLIFY, OperationType.DIVIDE_BOTH_SIDES,
                      OperationType.MULTIPLY_BOTH_SIDES)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        # We need a quotient where the numerator is a sum and the denominator
        # shares a factor with at least one term but not all.
        return _has_cancelable_sum_fraction(step.expression) or _has_cancelable_sum_fraction(
            solution.steps[step_index - 1].expression if step_index > 0 else step.expression
        )

    def apply(self, step, solution, step_index):
        # Find a Div pattern in the current expression and "cancel" only the
        # first term.
        expr = step.expression
        new_expr = _buggy_cancel_first_term(expr)
        if new_expr == expr and step_index > 0:
            prev = solution.steps[step_index - 1].expression
            new_expr = _buggy_cancel_first_term(prev)
        if new_expr == expr:
            return step
        return Step(step.index, new_expr, step.operation, note=f"sabotage:{self.id}")


# --- helpers ---

def _has_cancelable_sum_fraction(expr):
    if isinstance(expr, sp.Equality):
        return (_has_cancelable_sum_fraction(expr.lhs)
                or _has_cancelable_sum_fraction(expr.rhs))
    for sub in sp.preorder_traversal(expr):
        # A "fraction" in SymPy is typically Mul with a Pow(-1) factor.
        if isinstance(sub, sp.Mul):
            num, den = sp.fraction(sub)
            if den != 1 and isinstance(num, sp.Add) and len(num.args) >= 2:
                return True
    return False


def _buggy_cancel_first_term(expr):
    """Find num/den where num is Add; divide only the first term by den."""
    if isinstance(expr, sp.Equality):
        return Eq(_buggy_cancel_first_term(expr.lhs),
                  _buggy_cancel_first_term(expr.rhs))
    if not isinstance(expr, sp.Basic):
        return expr
    # We look for a Mul subnode that is num*den**-1 with num being Add.
    def is_target(node):
        if not isinstance(node, sp.Mul):
            return False
        num, den = sp.fraction(node)
        return den != 1 and isinstance(num, sp.Add) and len(num.args) >= 2
    def transform(node):
        num, den = sp.fraction(node)
        terms = list(num.args)
        first = terms[0] / den
        rest = sp.Add(*terms[1:])
        return first + rest    # the rest is NOT divided -the buggy "cancellation"
    return expr.replace(is_target, transform)


register(OperationOnOneSideOnly())
register(CancellationAcrossSum())
