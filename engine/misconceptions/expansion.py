"""Additional misconceptions added in Phase 2 expansion.

These three target gaps in the library:
  - `combining_unlike_terms`: mixing terms of different degrees during simplify
  - `squaring_binomial_as_difference_of_squares`: confusing (a-b)^2 with (a-b)(a+b)
  - `negative_factor_distribution_sign`: sign error when expanding -(...)

All three are unit-tested via tests/test_misconceptions.py: each must (a) have
at least one applicable problem in our generators, (b) produce well-formed
output, (c) produce an expression that is NOT equivalent to the canonical step.
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


class CombiningUnlikeTerms(Misconception):
    """Combine a linear and a quadratic term as if they were like terms.

    E.g. from `x^2 + 2x + 1 = b`, the student writes `x^2 + 3 = b`
    (treated `2x + 1` as a sum of constants) -or `3x^2 + 1 = b`
    (treated `2x` as `2x^2`).

    Implementation: find a step with both x and x^2 terms. Replace the
    linear coefficient with 0 and bump the quadratic coefficient by it.
    The result has the *right* "total" if you naively added coefficients,
    but is structurally wrong.
    """
    id = "combining_unlike_terms"
    name = "Combining unlike terms"
    description = (
        "Different-degree terms are added as if they were like terms. "
        "E.g., 2x and 3x^2 are combined into 5x^2 (or 5x). This shows up "
        "during simplification when the student stops tracking exponents."
    )
    category = "coefficient"
    difficulty = 3
    applicable_ops = (OperationType.EXPAND, OperationType.SIMPLIFY,
                      OperationType.TRANSPOSE)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        return _has_linear_and_quadratic_term(step.expression,
                                               solution.variables[0])

    def apply(self, step, solution, step_index):
        sym = solution.variables[0]
        new_expr = _merge_linear_into_quadratic(step.expression, sym)
        if new_expr == step.expression:
            return step
        return Step(step.index, new_expr, step.operation,
                    note=f"sabotage:{self.id}")


class SquaringBinomialAsDifferenceOfSquares(Misconception):
    """Confuses (x - a)^2 with (x - a)(x + a). I.e., (x - 3)^2 -> x^2 - 9.

    This is structurally different from `exponent_over_sum` (which drops the
    cross term but keeps a^2 with the right sign). Here the student treats
    the SQUARED binomial as if it were a DIFFERENCE OF SQUARES factoring.
    """
    id = "squaring_as_diff_of_squares"
    name = "Squaring a binomial as a difference of squares"
    description = (
        "A squared binomial (x - a)^2 is incorrectly expanded as x^2 - a^2 "
        "(the difference-of-squares pattern), instead of x^2 - 2ax + a^2. "
        "Mixes up two distinct identities."
    )
    category = "distribution"
    difficulty = 4
    applicable_ops = (OperationType.EXPAND,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.EXPAND or step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        return _has_squared_binomial(prev) or _has_squared_binomial(step.expression)

    def apply(self, step, solution, step_index):
        if step_index == 0:
            return step
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return step
        new_lhs = _replace_squared_binomial_with_diff_of_squares(prev.lhs)
        new_rhs = _replace_squared_binomial_with_diff_of_squares(prev.rhs)
        if new_lhs == prev.lhs and new_rhs == prev.rhs:
            return step
        return Step(step.index, Eq(new_lhs, new_rhs), step.operation,
                    note=f"sabotage:{self.id}")


class NegativeFactorDistributionSign(Misconception):
    """When the previous step contains a literal negative coefficient on a
    parenthesized term (e.g., -3*(x + 2)), the expanded form gets the sign
    wrong on a subset of terms.

    This is distinct from `distribute_neg_misses_second_term`: that one
    only handles the `-(a+b)` case (unit negative). This one handles
    `-k(a+b)` for any negative k.
    """
    id = "negative_factor_distribution_sign"
    name = "Sign error when distributing a negative coefficient"
    description = (
        "When distributing a negative coefficient across a sum, one or more "
        "terms keep the wrong sign. E.g., -3(x - 2) becomes -3x - 6 instead "
        "of -3x + 6."
    )
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.EXPAND,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.EXPAND or step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        return _has_negative_coefficient_times_sum(prev)

    def apply(self, step, solution, step_index):
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return step
        new_lhs = _buggy_distribute_neg_k(prev.lhs)
        new_rhs = _buggy_distribute_neg_k(prev.rhs)
        if new_lhs == prev.lhs and new_rhs == prev.rhs:
            return step
        return Step(step.index, Eq(new_lhs, new_rhs), step.operation,
                    note=f"sabotage:{self.id}")


# ----- helpers -----

def _has_linear_and_quadratic_term(expr, sym) -> bool:
    """True if expr contains both `c1*sym` and `c2*sym**2` somewhere."""
    if isinstance(expr, sp.Equality):
        return (_has_linear_and_quadratic_term(expr.lhs, sym)
                or _has_linear_and_quadratic_term(expr.rhs, sym))
    try:
        poly = sp.Poly(expr, sym)
    except sp.PolynomialError:
        return False
    if poly.degree() < 2:
        return False
    coeffs = poly.all_coeffs()
    # coeffs is [c_deg, ..., c_0]. We need both c_1 != 0 and c_2 != 0.
    deg = poly.degree()
    if deg < 2:
        return False
    # Index from the END for the constant; linear is coeffs[-2], quadratic coeffs[-3].
    if len(coeffs) < 3:
        return False
    return coeffs[-2] != 0 and coeffs[-3] != 0


def _merge_linear_into_quadratic(expr, sym):
    """Set linear coefficient to 0, add it to the quadratic coefficient."""
    if isinstance(expr, sp.Equality):
        new_lhs = _merge_linear_into_quadratic(expr.lhs, sym)
        new_rhs = _merge_linear_into_quadratic(expr.rhs, sym)
        if new_lhs == expr.lhs and new_rhs == expr.rhs:
            return expr
        return Eq(new_lhs, new_rhs)
    try:
        poly = sp.Poly(expr, sym)
    except sp.PolynomialError:
        return expr
    if poly.degree() < 2:
        return expr
    coeffs = list(poly.all_coeffs())
    if len(coeffs) < 3:
        return expr
    linear = coeffs[-2]
    if linear == 0:
        return expr
    coeffs[-3] = coeffs[-3] + linear   # add to quadratic coefficient
    coeffs[-2] = 0                      # zero out the linear coefficient
    return sp.Poly(coeffs, sym).as_expr()


def _has_squared_binomial(expr) -> bool:
    if isinstance(expr, sp.Equality):
        return _has_squared_binomial(expr.lhs) or _has_squared_binomial(expr.rhs)
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Pow):
            base, exp = sub.args
            if (isinstance(base, sp.Add) and len(base.args) == 2
                    and exp.is_integer and exp == 2):
                return True
    return False


def _replace_squared_binomial_with_diff_of_squares(expr):
    """Replace (a+b)**2 with a**2 - b**2 (the WRONG identity for squared)."""
    if not isinstance(expr, sp.Basic):
        return expr
    def matcher(n):
        if isinstance(n, sp.Pow):
            base, exp = n.args
            return (isinstance(base, sp.Add) and len(base.args) == 2
                    and exp.is_integer and exp == 2)
        return False
    def replacer(n):
        base = n.args[0]
        a, b = base.args
        # The "diff of squares" pattern: a^2 - b^2. Pick whichever term has
        # a negative sign and use its absolute value squared with a minus.
        # If neither is "negative", subtract the second from the first.
        a_neg = _is_negative_like(a)
        b_neg = _is_negative_like(b)
        if a_neg and not b_neg:
            return b ** 2 - (-a) ** 2
        if b_neg and not a_neg:
            return a ** 2 - (-b) ** 2
        return a ** 2 - b ** 2
    return expr.replace(matcher, replacer)


def _is_negative_like(x) -> bool:
    """Heuristic: is x a negative number or a Mul with negative leading coeff."""
    if x.is_number:
        return bool(x.is_negative)
    if isinstance(x, sp.Mul):
        for a in x.args:
            if a.is_number and a.is_negative:
                return True
    return False


def _has_negative_coefficient_times_sum(expr) -> bool:
    if isinstance(expr, sp.Equality):
        return (_has_negative_coefficient_times_sum(expr.lhs)
                or _has_negative_coefficient_times_sum(expr.rhs))
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Mul):
            coeff = sp.S.One
            sum_factor = None
            for a in sub.args:
                if a.is_number:
                    coeff *= a
                elif isinstance(a, sp.Add) and len(a.args) >= 2:
                    sum_factor = a
            if coeff.is_negative and coeff != -1 and sum_factor is not None:
                return True
    return False


def _buggy_distribute_neg_k(expr):
    """Find (-k)*(a+b) where k > 1 and produce -k*a - k*b (sign wrong on b)."""
    if not isinstance(expr, sp.Basic):
        return expr
    def matcher(n):
        if not isinstance(n, sp.Mul):
            return False
        coeff = sp.S.One
        sum_factor = None
        for a in n.args:
            if a.is_number:
                coeff *= a
            elif isinstance(a, sp.Add) and len(a.args) >= 2:
                sum_factor = a
        return coeff.is_negative and coeff != -1 and sum_factor is not None
    def replacer(n):
        coeff = sp.S.One
        sum_factor = None
        for a in n.args:
            if a.is_number:
                coeff *= a
            elif isinstance(a, sp.Add) and len(a.args) >= 2:
                sum_factor = a
        # Buggy: all inner terms multiplied by |coeff| with the SAME sign on
        # the outside negative. i.e., -k*(a-b) -> -k*a - k*b (-k*b instead
        # of +k*b).
        terms = list(sum_factor.args)
        new_terms = [coeff * t if i == 0 else (-abs(coeff)) * abs(t) * sp.sign(t) * (-1) ** 0
                     for i, t in enumerate(terms)]
        # Simpler: first term correct, others negated wrongly.
        new_terms = [coeff * terms[0]]
        for t in terms[1:]:
            new_terms.append(coeff * (-t))   # WRONG: extra sign flip
        return sp.Add(*new_terms)
    return expr.replace(matcher, replacer)


register(CombiningUnlikeTerms())
register(SquaringBinomialAsDifferenceOfSquares())
register(NegativeFactorDistributionSign())
