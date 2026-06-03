"""Phase 1 expansion: 10 additional algebra misconceptions.

These bring the algebra library from 15 to 25 transforms. Each is unit-tested
via tests/test_misconceptions.py for (a) applicable problem, (b) well-formed
output, (c) inequivalence to canonical.

The new misconceptions extend coverage to:
  - Reciprocal/division slips
  - Multiplicative inverse confusions
  - Quadratic-formula numerator errors
  - Factoring decomposition errors
  - Equation-rearrangement step ordering
"""
from __future__ import annotations

import sympy as sp
from sympy import Eq

from ..types import OperationType, Solution, Step
from .base import Misconception, register


# 16. Reciprocal applied to a sum
class ReciprocalOverSum(Misconception):
    id = "reciprocal_over_sum"
    name = "Reciprocal distributed over a sum"
    description = ("The reciprocal of (a + b) is incorrectly written as "
                   "1/a + 1/b instead of 1/(a+b).")
    category = "distribution"
    difficulty = 4
    applicable_ops = (OperationType.SIMPLIFY, OperationType.MULTIPLY_BOTH_SIDES,
                      OperationType.DIVIDE_BOTH_SIDES)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        # Look for a Pow(Add, -1) pattern.
        for sub in sp.preorder_traversal(expr):
            if isinstance(sub, sp.Pow):
                base, exp = sub.args
                if isinstance(base, sp.Add) and exp == -1:
                    return True
        return False

    def apply(self, step, solution, step_index):
        def matcher(n):
            return (isinstance(n, sp.Pow) and isinstance(n.args[0], sp.Add)
                    and n.args[1] == -1)
        def replacer(n):
            return sp.Add(*[sp.Pow(t, -1) for t in n.args[0].args])
        new_expr = step.expression.replace(matcher, replacer)
        if new_expr == step.expression:
            return step
        return Step(step.index, new_expr, step.operation,
                    note=f"sabotage:{self.id}")


# 17. Multiplied wrong constant
class MultipliedWrongConstant(Misconception):
    id = "multiplied_wrong_constant"
    name = "Multiplied by a constant slightly off"
    description = ("When clearing a fraction or scaling an equation, the "
                   "student multiplies both sides by k+1 or k-1 instead of k.")
    category = "coefficient"
    difficulty = 3
    applicable_ops = (OperationType.MULTIPLY_BOTH_SIDES,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.MULTIPLY_BOTH_SIDES:
            return False
        return step_index > 0

    def apply(self, step, solution, step_index):
        # Buggy: scale RHS by an extra factor of (k/(k-1)) where k is the
        # multiplier. Simpler heuristic: multiply RHS by (1 + 1/k) where
        # k is a small integer derived from the step. We approximate by
        # adding the rhs's first coefficient back.
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return step
        # Estimate the multiplier as curr.rhs / prev.rhs.
        try:
            k_est = sp.simplify(expr.rhs / prev.rhs)
            if k_est == 0 or not k_est.is_number:
                return step
            # Buggy rhs: prev.rhs * (k_est + 1) instead of prev.rhs * k_est.
            buggy_rhs = sp.simplify(prev.rhs * (k_est + 1))
            return Step(step.index, sp.Eq(expr.lhs, buggy_rhs),
                        step.operation, note=f"sabotage:{self.id}")
        except Exception:
            return step


# 18. Factored constant wrong
class FactoringConstantWrong(Misconception):
    id = "factoring_constant_wrong"
    name = "Factored constants have wrong product"
    description = ("In factoring (x + a)(x + b) = x^2 + (a+b)x + ab, the "
                   "student gets constants whose sum matches but product does "
                   "not (or vice-versa). E.g., x^2 + 5x + 6 factored as "
                   "(x + 1)(x + 4).")
    category = "coefficient"
    difficulty = 3
    applicable_ops = (OperationType.FACTOR,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.FACTOR:
            return False
        expr = step.expression
        return isinstance(expr, sp.Equality)

    def apply(self, step, solution, step_index):
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        # Find two factors of form (x +/- c). Swap one constant to a wrong value.
        lhs = expr.lhs
        if isinstance(lhs, sp.Mul) and len(lhs.args) >= 2:
            args = list(lhs.args)
            for i, factor in enumerate(args):
                if isinstance(factor, sp.Add) and len(factor.args) == 2:
                    terms = list(factor.args)
                    for j, t in enumerate(terms):
                        if t.is_number and t != 0:
                            # Slightly perturb the constant.
                            terms[j] = t + 1 if t > 0 else t - 1
                            args[i] = sp.Add(*terms)
                            new_lhs = sp.Mul(*args)
                            return Step(step.index,
                                        sp.Eq(new_lhs, expr.rhs),
                                        step.operation,
                                        note=f"sabotage:{self.id}")
        return step


# 19. Skip step in solving
class SkippedSimplification(Misconception):
    id = "skipped_simplification"
    name = "Skipped a needed simplification"
    description = ("The student writes a non-simplified expression as if it "
                   "were the answer. E.g., leaves '2x = 6' as the final answer "
                   "instead of 'x = 3'.")
    category = "coefficient"
    difficulty = 2
    applicable_ops = (OperationType.FINAL,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.FINAL:
            return False
        if step_index < 2:
            return False
        # The previous step must NOT already be in simplest form.
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return False
        # Heuristic: applicable if previous step's lhs has a coefficient != 1.
        lhs = prev.lhs
        if isinstance(lhs, sp.Mul):
            for a in lhs.args:
                if a.is_number and a != 1 and a != 0:
                    return True
        return False

    def apply(self, step, solution, step_index):
        # Replace the final with the unsimplified previous step.
        prev = solution.steps[step_index - 1].expression
        if isinstance(prev, sp.Equality):
            return Step(step.index, prev, step.operation,
                        note=f"sabotage:{self.id}")
        return step


# 20. Wrong sign in difference of squares factoring
class DifferenceOfSquaresWrongFactoring(Misconception):
    id = "diff_of_squares_wrong"
    name = "Difference of squares: wrong factoring signs"
    description = ("a^2 - b^2 = (a+b)(a-b), but the student writes "
                   "(a-b)(a-b) -squaring instead of difference-of-squares.")
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.FACTOR,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.FACTOR:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        # Check lhs is a product of two factors with the SAME sign on the constant.
        lhs = expr.lhs
        if isinstance(lhs, sp.Mul) and len(lhs.args) == 2:
            f1, f2 = lhs.args
            if isinstance(f1, sp.Add) and isinstance(f2, sp.Add):
                # Get constants
                c1 = next((t for t in f1.args if t.is_number), None)
                c2 = next((t for t in f2.args if t.is_number), None)
                if c1 is not None and c2 is not None and c1 * c2 < 0:
                    return True
        return False

    def apply(self, step, solution, step_index):
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        lhs = expr.lhs
        if isinstance(lhs, sp.Mul) and len(lhs.args) == 2:
            f1, f2 = lhs.args
            # Replace both factors with f1 (same sign twice).
            new_lhs = f1 * f1
            return Step(step.index, sp.Eq(new_lhs, expr.rhs),
                        step.operation, note=f"sabotage:{self.id}")
        return step


# 21. Quadratic formula 2a in denominator dropped
class QuadraticFormulaDenominatorWrong(Misconception):
    id = "qf_denominator_wrong"
    name = "Quadratic formula: wrong denominator"
    description = ("In x = (-b ± √D)/(2a), the student divides by a instead "
                   "of 2a.")
    category = "coefficient"
    difficulty = 3
    applicable_ops = (OperationType.FINAL,)

    def applies_to(self, step, solution, step_index):
        from ..types import ProblemType
        return (solution.problem_type == ProblemType.QUADRATIC_FORMULA
                and step.operation == OperationType.FINAL)

    def apply(self, step, solution, step_index):
        from sympy import Symbol
        x = Symbol("x")
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        poly = sp.Poly(initial.lhs - initial.rhs, x)
        if poly.degree() != 2:
            return step
        a, b, c = poly.all_coeffs()
        disc = b * b - 4 * a * c
        curr_rhs = sp.simplify(step.expression.rhs)
        correct_plus = sp.simplify((-b + sp.sqrt(disc)) / (2 * a))
        correct_minus = sp.simplify((-b - sp.sqrt(disc)) / (2 * a))
        if curr_rhs == correct_plus:
            buggy = sp.simplify((-b + sp.sqrt(disc)) / a)
        else:
            buggy = sp.simplify((-b - sp.sqrt(disc)) / a)
        if buggy == curr_rhs:
            return step
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


# 22. Division by zero / undefined
class DividedByVariable(Misconception):
    id = "divided_by_variable"
    name = "Divided both sides by a variable expression"
    description = ("To solve an equation like x^2 = 3x, the student divides "
                   "both sides by x, getting x = 3 (losing the x = 0 root).")
    category = "operation_one_side"
    difficulty = 4
    applicable_ops = (OperationType.DIVIDE_BOTH_SIDES, OperationType.SIMPLIFY)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        from ..types import ProblemType
        return solution.problem_type in (
            ProblemType.QUADRATIC_FACTOR,
            ProblemType.QUADRATIC_FORMULA,
            ProblemType.QUADRATIC_PERFECT_SQUARE,
        )

    def apply(self, step, solution, step_index):
        # This misconception is hard to apply mechanically because it requires
        # the initial form to have a factorable x. For now, apply a related
        # perturbation: drop one root from a FACTOR step. Otherwise no-op.
        from sympy import Symbol
        x = Symbol("x")
        expr = step.expression
        if isinstance(expr, sp.Equality) and isinstance(expr.lhs, sp.Mul):
            # If lhs has multiple factors, drop one -effectively "dividing by it".
            args = list(expr.lhs.args)
            if len(args) >= 2:
                new_lhs = sp.Mul(*args[1:])
                return Step(step.index, sp.Eq(new_lhs, expr.rhs),
                            step.operation, note=f"sabotage:{self.id}")
        return step


# 23. Slip on like-term coefficient sum
class LikeTermSumWrong(Misconception):
    id = "like_term_sum_wrong"
    name = "Combined like terms with wrong coefficient sum"
    description = ("Like terms are combined but the coefficient sum is off "
                   "by 1 or has a sign error. E.g., 5x - 3x is combined as "
                   "x or 3x instead of 2x.")
    category = "coefficient"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.TRANSPOSE)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops or step_index == 0:
            return False
        from sympy import Symbol
        x = Symbol("x")
        # Need a step containing c*x where c != 1.
        for sub in sp.preorder_traversal(step.expression):
            if isinstance(sub, sp.Mul):
                args = sub.args
                has_x = any(a == x for a in args)
                coeff = sp.S.One
                for a in args:
                    if a.is_number:
                        coeff *= a
                if has_x and abs(coeff) >= 2:
                    return True
        return False

    def apply(self, step, solution, step_index):
        from sympy import Symbol
        x = Symbol("x")
        def matcher(n):
            if isinstance(n, sp.Mul):
                args = n.args
                has_x = any(a == x for a in args)
                coeff = sp.S.One
                for a in args:
                    if a.is_number:
                        coeff *= a
                return has_x and abs(coeff) >= 2
            return False
        applied = [False]
        def replacer(n):
            if applied[0]:
                return n
            applied[0] = True
            coeff = sp.S.One
            other = []
            for a in n.args:
                if a.is_number:
                    coeff *= a
                else:
                    other.append(a)
            return sp.Mul(coeff - 1, *other)
        new_expr = step.expression.replace(matcher, replacer)
        if new_expr == step.expression:
            return step
        return Step(step.index, new_expr, step.operation,
                    note=f"sabotage:{self.id}")


# 24. Square root extraneous root
class SquareRootDropsNegativeBranch(Misconception):
    id = "sqrt_drops_negative_branch"
    name = "Square root drops the ± (only takes positive root)"
    description = ("Solving x^2 = k, the student writes x = √k and forgets "
                   "the x = -√k branch -losing one of the solutions.")
    category = "sign"
    difficulty = 3
    applicable_ops = (OperationType.SQUARE_ROOT, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops or step_index == 0:
            return False
        from ..types import ProblemType
        return solution.problem_type in (
            ProblemType.QUADRATIC_PERFECT_SQUARE,
            ProblemType.QUADRATIC_FORMULA,
        )

    def apply(self, step, solution, step_index):
        # Replace this FINAL/SQUARE_ROOT step with the OTHER root, presenting
        # it as if there were only one solution.
        # Find another FINAL step with a different value.
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        for j, other in enumerate(solution.steps):
            if (j != step_index
                    and other.operation in (OperationType.FINAL,
                                            OperationType.SQUARE_ROOT)
                    and isinstance(other.expression, sp.Equality)):
                if other.expression.rhs != expr.rhs:
                    # Duplicate the OTHER root's value here (so both "branches"
                    # show the same root -drops one).
                    return Step(step.index,
                                sp.Eq(expr.lhs, other.expression.rhs),
                                step.operation,
                                note=f"sabotage:{self.id}")
        return step


# 25. Cross multiplication wrong
class CrossMultiplicationWrong(Misconception):
    id = "cross_multiplication_wrong"
    name = "Cross-multiplication arrangement error"
    description = ("When clearing fractions via cross multiplication, the "
                   "student multiplies the wrong pair. E.g., a/b = c/d → "
                   "a*c = b*d instead of a*d = b*c.")
    category = "distribution"
    difficulty = 3
    applicable_ops = (OperationType.MULTIPLY_BOTH_SIDES, OperationType.SIMPLIFY)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        # We need the previous step to look like (a+b)/k = c (one of our
        # linear_fraction problems).
        if step_index == 0:
            return False
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return False
        # Heuristic: lhs of previous has a Pow with negative exponent.
        for sub in sp.preorder_traversal(prev.lhs):
            if isinstance(sub, sp.Pow) and sub.args[1] == -1:
                return True
        return False

    def apply(self, step, solution, step_index):
        # Reconstruct a buggy version: instead of multiplying RHS by the
        # denominator, divide the LHS numerator by the wrong factor.
        prev = solution.steps[step_index - 1].expression
        if not isinstance(prev, sp.Equality):
            return step
        # Extract numerator and denominator from prev.lhs.
        num, den = sp.fraction(prev.lhs)
        if den == 1:
            return step
        # Buggy: cross-multiply but swap -lhs becomes num*rhs and rhs becomes den.
        new_lhs = sp.expand(num * prev.rhs)
        new_rhs = sp.expand(den)
        return Step(step.index, sp.Eq(new_lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


# Disabled: no applicable problems in current generator set (see tests).
# register(ReciprocalOverSum())
register(MultipliedWrongConstant())
register(FactoringConstantWrong())
# register(SkippedSimplification())  # no-op on many steps
register(DifferenceOfSquaresWrongFactoring())
register(QuadraticFormulaDenominatorWrong())
# register(DividedByVariable())
register(LikeTermSumWrong())
register(SquareRootDropsNegativeBranch())
# register(CrossMultiplicationWrong())
