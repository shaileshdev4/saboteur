"""Quadratic-specific misconceptions.

These attack factoring and the quadratic formula. The hardest student errors
live here — the formula has 4 sub-pieces and any of them can be miscopied.
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq, sqrt, symbols

from ..types import OperationType, Solution, Step
from .base import Misconception, register

x = symbols("x")


class WrongRootInFactoring(Misconception):
    id = "wrong_root_in_factoring"
    name = "Wrong root from factoring"
    description = (
        "The student factors correctly but reads one root with the wrong sign. "
        "E.g., from (x - 3)(x + 5) = 0 they conclude x = 3 and x = 5 (instead "
        "of x = -5)."
    )
    category = "sign"
    difficulty = 2
    applicable_ops = (OperationType.FINAL,)

    def applies_to(self, step, solution, step_index):
        # We attack a FINAL root step that came from a FACTOR.
        if step.operation != OperationType.FINAL:
            return False
        if step_index == 0:
            return False
        # Look back for a FACTOR step.
        for j in range(step_index - 1, -1, -1):
            if solution.steps[j].operation == OperationType.FACTOR:
                return True
            if solution.steps[j].operation == OperationType.INITIAL:
                return False
        return False

    def apply(self, step, solution, step_index):
        # Flip the sign of the root.
        if not isinstance(step.expression, sp.Equality):
            return step
        return Step(step.index, Eq(step.expression.lhs, -step.expression.rhs),
                    step.operation, note=f"sabotage:{self.id}")


class QuadraticFormulaSignError(Misconception):
    id = "qf_sign_error"
    name = "Sign error applying the quadratic formula"
    description = (
        "When applying x = (-b ± √D)/(2a), the student forgets to negate b. "
        "E.g., for b = -5 they write +(-5) = -5 instead of -(-5) = +5."
    )
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.FINAL,)

    def applies_to(self, step, solution, step_index):
        # Only applies when the originating problem is QUADRATIC_FORMULA.
        from ..types import ProblemType
        if solution.problem_type != ProblemType.QUADRATIC_FORMULA:
            return False
        if step.operation != OperationType.FINAL:
            return False
        if not isinstance(step.expression, sp.Equality):
            return False
        # Reconstruct what -(-b ± √D)/(2a) would give if we flip the sign on b.
        return True

    def apply(self, step, solution, step_index):
        # We need a + b from the initial quadratic ax^2 + bx + c = 0.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        poly = sp.Poly(initial.lhs - initial.rhs, x)
        if poly.degree() != 2:
            return step
        a, b, c = poly.all_coeffs()
        disc = b * b - 4 * a * c
        # Buggy formula: use +b instead of -b.
        # Determine which branch this step is by looking at its current rhs:
        curr_rhs = sp.simplify(step.expression.rhs)
        correct_plus = sp.simplify((-b + sp.sqrt(disc)) / (2 * a))
        # If this step is the + branch, produce buggy + branch.
        if curr_rhs == correct_plus:
            buggy = sp.simplify((b + sp.sqrt(disc)) / (2 * a))
        else:
            buggy = sp.simplify((b - sp.sqrt(disc)) / (2 * a))
        if buggy == curr_rhs:
            # The sign change made no difference (b == 0). Fall back to negating rhs.
            buggy = -curr_rhs
        return Step(step.index, Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


class QuadraticFormulaDiscriminantError(Misconception):
    id = "qf_discriminant_error"
    name = "Wrong discriminant calculation"
    description = (
        "The student computes b^2 - 4ac with an arithmetic slip, most often "
        "+4ac instead of -4ac. This propagates a wrong discriminant into the "
        "formula."
    )
    category = "sign"
    difficulty = 4
    applicable_ops = (OperationType.SIMPLIFY,)

    def applies_to(self, step, solution, step_index):
        # Attack the scratch-symbol discriminant step.
        from ..types import ProblemType
        if solution.problem_type != ProblemType.QUADRATIC_FORMULA:
            return False
        if step.operation != OperationType.SIMPLIFY:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        # rhs is a number, lhs is the scratch symbol D.
        return expr.rhs.is_number

    def apply(self, step, solution, step_index):
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        poly = sp.Poly(initial.lhs - initial.rhs, x)
        if poly.degree() != 2:
            return step
        a, b, c = poly.all_coeffs()
        # Buggy discriminant: b^2 + 4ac.
        buggy = b * b + 4 * a * c
        if buggy == b * b - 4 * a * c:
            buggy = b * b - 4 * a * c + 1
        return Step(step.index, Eq(step.expression.lhs, sp.Integer(buggy)),
                    step.operation, note=f"sabotage:{self.id}")


class IncorrectFactoring(Misconception):
    id = "incorrect_factoring"
    name = "Incorrect factoring"
    description = (
        "The quadratic is factored into a product that doesn't equal the "
        "original. Common form: getting the constants right but signs wrong "
        "(e.g., x^2 - 5x + 6 → (x + 2)(x + 3))."
    )
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.FACTOR,)

    def applies_to(self, step, solution, step_index):
        return step.operation == OperationType.FACTOR

    def apply(self, step, solution, step_index):
        # Strategy: flip the sign on one root in the factored form.
        if not isinstance(step.expression, sp.Equality):
            return step
        lhs = step.expression.lhs
        if isinstance(lhs, sp.Mul) and len(lhs.args) >= 2:
            args = list(lhs.args)
            # Find the first (x - r) or (x + r) factor and flip the constant.
            for i, a in enumerate(args):
                if isinstance(a, sp.Add):
                    terms = list(a.args)
                    # find numeric term
                    for j, t in enumerate(terms):
                        if t.is_number and t != 0:
                            terms[j] = -t
                            args[i] = sp.Add(*terms)
                            new_lhs = sp.Mul(*args)
                            return Step(step.index,
                                        Eq(new_lhs, step.expression.rhs),
                                        step.operation,
                                        note=f"sabotage:{self.id}")
        return step


register(WrongRootInFactoring())
register(QuadraticFormulaSignError())
register(QuadraticFormulaDiscriminantError())
register(IncorrectFactoring())
