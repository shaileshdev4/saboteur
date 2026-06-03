"""Sign-related misconceptions.

These attack steps where signs matter most: transposition across the equals
sign, distributing a negative, dropping a minus when squaring.
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


class SignFlipOnTranspose(Misconception):
    id = "sign_flip_transpose"
    name = "Sign flip on transposition"
    description = (
        "When moving a term across the equals sign, the sign is kept the same "
        "instead of being flipped. E.g., from x + 5 = 12 the student writes "
        "x = 12 + 5 instead of x = 12 - 5."
    )
    category = "sign"
    difficulty = 2
    applicable_ops = (OperationType.TRANSPOSE,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.TRANSPOSE:
            return False
        prev = solution.steps[step_index - 1].expression
        return isinstance(prev, sp.Equality) and isinstance(step.expression, sp.Equality)

    def apply(self, step, solution, step_index):
        # Correct transpose: LHS_prev = LHS_curr + delta, RHS_curr = RHS_prev - delta
        # (the moved term `delta` flips sign as it crosses).
        # Buggy version: student keeps the sign the same, so
        #   RHS_bug = RHS_prev + delta  (instead of RHS_prev - delta)
        # which equals  RHS_curr + 2*delta  =  RHS_prev + (LHS_prev - LHS_curr).
        prev = solution.steps[step_index - 1].expression
        curr = step.expression
        delta = sp.simplify(prev.lhs - curr.lhs)
        if delta == 0:
            # Nothing transposed on the LHS -try the RHS side.
            delta = sp.simplify(prev.rhs - curr.rhs)
            if delta == 0:
                return step  # no actual transpose to corrupt
            # symmetric: bug on the LHS
            buggy_lhs = sp.simplify(prev.lhs + delta)
            return Step(step.index, Eq(buggy_lhs, curr.rhs), step.operation,
                        note=f"sabotage:{self.id}")
        buggy_rhs = sp.simplify(prev.rhs + delta)
        if buggy_rhs == curr.rhs:
            # Sign change made no difference (delta was symmetric somehow).
            # Fall back to a different perturbation.
            buggy_rhs = curr.rhs + 2 * delta
        return Step(step.index, Eq(curr.lhs, buggy_rhs), step.operation,
                    note=f"sabotage:{self.id}")


class DistributedNegativeMissesTerm(Misconception):
    """When distributing a negative across (a + b), the student writes -a + b
    instead of -a - b. E.g., -(x + 3) = -x + 3."""
    id = "distribute_neg_misses_second_term"
    name = "Distributing a negative only to the first term"
    description = (
        "When distributing a negative sign across a sum, only the first term "
        "gets negated. E.g., -(x + 3) becomes -x + 3 instead of -x - 3."
    )
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.EXPAND,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.EXPAND:
            return False
        if step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        # We need the previous step to contain a negated sum: -(a + b) or
        # -k * (a + b) where k > 0. Detect by walking the prev expression.
        return _has_negative_distribution(prev)

    def apply(self, step, solution, step_index):
        prev = solution.steps[step_index - 1].expression
        # Build the "wrong" distributed form ourselves.
        wrong = _apply_negative_only_first_term(prev)
        if wrong is None:
            # Fall back: negate the second additive term in the current rhs/lhs.
            curr = step.expression
            new_lhs = _flip_sign_of_second_term(curr.lhs)
            return Step(step.index, Eq(new_lhs, curr.rhs), step.operation,
                        note=f"sabotage:{self.id}")
        return Step(step.index, wrong, step.operation, note=f"sabotage:{self.id}")


# --- helpers ---

def _has_negative_distribution(expr) -> bool:
    """True if expr contains a pattern like -(a+b) or k*(a+b) with negative k."""
    if not isinstance(expr, (sp.Equality, sp.Expr)):
        return False
    if isinstance(expr, sp.Equality):
        return _has_negative_distribution(expr.lhs) or _has_negative_distribution(expr.rhs)
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Mul):
            args = sub.args
            coeff = sp.S.One
            rest = []
            for a in args:
                if a.is_number:
                    coeff *= a
                else:
                    rest.append(a)
            if coeff.is_negative:
                for r in rest:
                    if isinstance(r, sp.Add) and len(r.args) >= 2:
                        return True
    return False


def _apply_negative_only_first_term(expr):
    """Manually produce a 'wrong' expansion where negative only hits 1st term."""
    if not isinstance(expr, sp.Equality):
        return None
    # Try to rewrite each side with the buggy distribution.
    new_lhs = _buggy_distribute_negative(expr.lhs)
    new_rhs = _buggy_distribute_negative(expr.rhs)
    if new_lhs == expr.lhs and new_rhs == expr.rhs:
        return None
    return Eq(new_lhs, new_rhs)


def _buggy_distribute_negative(expr):
    """Find a Mul like (-k)*(a+b+...) and turn it into -k*a + k*b + k*c..."""
    if isinstance(expr, sp.Add):
        return sp.Add(*[_buggy_distribute_negative(a) for a in expr.args])
    if isinstance(expr, sp.Mul):
        args = list(expr.args)
        # Find numeric coeff and sum factor.
        coeff = sp.S.One
        rest = []
        for a in args:
            if a.is_number:
                coeff *= a
            else:
                rest.append(a)
        if coeff.is_negative and len(rest) == 1 and isinstance(rest[0], sp.Add):
            terms = rest[0].args
            # Only buggy-distribute when distributing produces a different result.
            first = coeff * terms[0]
            others = [(-coeff) * t for t in terms[1:]]   # WRONG: sign not flipped
            return sp.Add(first, *others)
    return expr


def _flip_sign_of_second_term(expr):
    """Flip the sign of the second additive term, leaving others alone."""
    if isinstance(expr, sp.Add) and len(expr.args) >= 2:
        terms = list(expr.args)
        terms[1] = -terms[1]
        return sp.Add(*terms)
    return expr


# Register
register(SignFlipOnTranspose())
register(DistributedNegativeMissesTerm())
