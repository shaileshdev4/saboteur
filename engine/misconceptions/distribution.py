"""Distribution-related misconceptions.

These attack steps where the student fails to apply a multiplicative or
exponential operation correctly across a sum.
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


class ExponentDistributedOverSum(Misconception):
    """(a + b)^2 → a^2 + b^2 (forgets the cross term)."""
    id = "exponent_over_sum"
    name = "Distributing exponent over a sum"
    description = (
        "An exponent is incorrectly distributed across a sum, dropping the "
        "cross terms. E.g., (a + b)^2 is written as a^2 + b^2 instead of "
        "a^2 + 2ab + b^2."
    )
    category = "distribution"
    difficulty = 3
    applicable_ops = (OperationType.EXPAND, OperationType.INITIAL, OperationType.SIMPLIFY)

    def applies_to(self, step, solution, step_index):
        # We can attack any step that contains a (sum)^n pattern that hasn't
        # already been expanded.
        return _has_powered_sum(step.expression)

    def apply(self, step, solution, step_index):
        expr = step.expression
        wrong = _buggy_expand_power_over_sum(expr)
        if isinstance(expr, sp.Equality):
            wrong_eq = Eq(_buggy_expand_power_over_sum(expr.lhs),
                          _buggy_expand_power_over_sum(expr.rhs))
            return Step(step.index, wrong_eq, step.operation, note=f"sabotage:{self.id}")
        return Step(step.index, wrong, step.operation, note=f"sabotage:{self.id}")


class DistributionDropsTerm(Misconception):
    """a(x + y + z) → ax + y + az  (drops distribution on a middle term)."""
    id = "distribution_drops_term"
    name = "Distribution misses a term"
    description = (
        "When distributing a factor over a sum, one of the inner terms is not "
        "multiplied. E.g., 3(x + 2y + 1) becomes 3x + 2y + 3."
    )
    category = "distribution"
    difficulty = 2
    applicable_ops = (OperationType.EXPAND,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.EXPAND or step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        return _has_distributable_product(prev, min_terms=2)

    def apply(self, step, solution, step_index):
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return step  # no-op
        new_lhs = _distribute_skipping_one_term(prev.lhs)
        new_rhs = _distribute_skipping_one_term(prev.rhs)
        return Step(step.index, Eq(new_lhs, new_rhs), step.operation,
                    note=f"sabotage:{self.id}")


# --- helpers ---

def _has_powered_sum(expr) -> bool:
    if isinstance(expr, sp.Equality):
        return _has_powered_sum(expr.lhs) or _has_powered_sum(expr.rhs)
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Pow):
            base, exp = sub.args
            if isinstance(base, sp.Add) and exp.is_integer and exp >= 2:
                return True
    return False


def _buggy_expand_power_over_sum(expr):
    """Replace each (a+b+...)**n with a**n + b**n + ... (wrong but plausible)."""
    if isinstance(expr, sp.Equality):
        return Eq(_buggy_expand_power_over_sum(expr.lhs),
                  _buggy_expand_power_over_sum(expr.rhs))
    if not isinstance(expr, sp.Basic):
        return expr
    # Use replace on Pow nodes whose base is Add.
    def _replace(node):
        if isinstance(node, sp.Pow):
            base, exp = node.args
            if isinstance(base, sp.Add) and exp.is_integer and exp >= 2:
                return sp.Add(*[t ** exp for t in base.args])
        return node
    # Walk bottom-up.
    return expr.replace(
        lambda n: isinstance(n, sp.Pow) and isinstance(n.args[0], sp.Add)
                  and n.args[1].is_integer and n.args[1] >= 2,
        lambda n: sp.Add(*[t ** n.args[1] for t in n.args[0].args])
    )


def _has_distributable_product(expr, min_terms=2):
    if isinstance(expr, sp.Equality):
        return (_has_distributable_product(expr.lhs, min_terms)
                or _has_distributable_product(expr.rhs, min_terms))
    for sub in sp.preorder_traversal(expr):
        if isinstance(sub, sp.Mul):
            for a in sub.args:
                if isinstance(a, sp.Add) and len(a.args) >= min_terms:
                    return True
    return False


def _distribute_skipping_one_term(expr):
    """Apply a 'buggy' distribution: distribute k*(a+b+c) as k*a + b + k*c
    (skipping multiplication on one inner term)."""
    if not isinstance(expr, sp.Basic):
        return expr
    if isinstance(expr, sp.Add):
        return sp.Add(*[_distribute_skipping_one_term(a) for a in expr.args])
    if isinstance(expr, sp.Mul):
        args = list(expr.args)
        # Find a sum factor.
        for i, a in enumerate(args):
            if isinstance(a, sp.Add) and len(a.args) >= 2:
                other = sp.Mul(*[args[j] for j in range(len(args)) if j != i])
                terms = list(a.args)
                # Skip multiplication on the second term.
                new_terms = []
                for k, t in enumerate(terms):
                    if k == 1:
                        new_terms.append(t)              # WRONG: not multiplied
                    else:
                        new_terms.append(other * t)
                return sp.Add(*new_terms)
    return expr


register(ExponentDistributedOverSum())
register(DistributionDropsTerm())
