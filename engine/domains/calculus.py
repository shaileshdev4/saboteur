"""Calculus domain.

Generates derivative and integral problems and provides a misconception
library specific to calculus (chain rule miss, product rule confused with
sum rule, dropped constant of integration, sign flip in integration by parts).

Architectural rule: SymPy `diff` and `integrate` are the verifier. No LLM
ever judges correctness here either.
"""
from __future__ import annotations

import random
from typing import Any, Optional

import sympy as sp
from sympy import Eq, Function, Symbol, diff, integrate, simplify, sympify

from ..domain import Domain, ProblemKind, register_domain
from ..misconceptions.base import Misconception
from ..types import OperationType, ProblemType, Solution, Step
from ..verifier import expressions_equivalent

x = sp.Symbol("x")
DERIVATIVE_OP_TAG = sp.Symbol("__deriv__")     # used to mark derivative steps
INTEGRAL_OP_TAG = sp.Symbol("__integ__")


# ===========================================================================
# Generators
# ===========================================================================

def _coef_range(difficulty: int) -> tuple[int, int]:
    return {1: (1, 5), 2: (1, 8), 3: (-8, 8), 4: (-12, 12), 5: (-15, 15)}.get(
        difficulty, (1, 5))


def gen_polynomial_derivative(difficulty: int = 1,
                              seed: Optional[int] = None) -> Solution:
    """d/dx of a polynomial.

    Steps:
      0. INITIAL:  f(x) = a_n x^n + ... + a_0
      1. SIMPLIFY: term-by-term application of the power rule
      2. FINAL:    f'(x) = simplified result
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    degree = rng.randint(2, min(4, 2 + difficulty))
    coeffs = [rng.randint(lo, hi) for _ in range(degree + 1)]
    while coeffs[0] == 0:
        coeffs[0] = rng.randint(max(1, lo), hi)

    poly = sum(c * x ** (degree - i) for i, c in enumerate(coeffs))
    derivative = sp.expand(diff(poly, x))

    # Build a middle step that shows term-by-term derivatives (unsimplified).
    middle_terms = []
    for i, c in enumerate(coeffs):
        power = degree - i
        if power == 0:
            middle_terms.append(sp.Integer(0))
        else:
            middle_terms.append(sp.Mul(c * power, x ** (power - 1),
                                       evaluate=False))
    middle = sp.Add(*middle_terms, evaluate=False)

    steps = [
        Step(0, sp.Eq(sp.Function("f")(x), poly), OperationType.INITIAL,
             note="f(x) = polynomial"),
        Step(1, sp.Eq(sp.Function("f_prime")(x), middle),
             OperationType.SIMPLIFY,
             note="apply the power rule term-by-term"),
        Step(2, sp.Eq(sp.Function("f_prime")(x), derivative),
             OperationType.FINAL,
             note="simplify"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,   # placeholder; see kind dispatch
        variables=[x],
        steps=steps,
        final_answer=derivative,
    )


def gen_product_rule(difficulty: int = 2,
                     seed: Optional[int] = None) -> Solution:
    """d/dx of f(x) * g(x) where f and g are simple polynomials.

    Steps:
      0. INITIAL:    h(x) = f(x) * g(x)
      1. EXPAND:     h'(x) = f'g + fg'   (product rule structure)
      2. SIMPLIFY:   substitute the actual derivatives
      3. FINAL:      simplified result
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    a = rng.randint(max(1, lo), hi)
    b = rng.randint(lo, hi)
    c = rng.randint(max(1, lo), hi)
    d = rng.randint(lo, hi)
    while a == 0:
        a = rng.randint(1, hi)
    while c == 0:
        c = rng.randint(1, hi)

    f_expr = a * x + b
    g_expr = c * x + d
    h_expr = f_expr * g_expr
    fp = sp.diff(f_expr, x)
    gp = sp.diff(g_expr, x)
    structured = fp * g_expr + f_expr * gp
    simplified = sp.expand(structured)

    steps = [
        Step(0, sp.Eq(sp.Function("h")(x),
                      sp.Mul(f_expr, g_expr, evaluate=False)),
             OperationType.INITIAL, note=f"h(x) = ({f_expr})({g_expr})"),
        Step(1, sp.Eq(sp.Function("h_prime")(x),
                      sp.Add(sp.Mul(fp, g_expr, evaluate=False),
                             sp.Mul(f_expr, gp, evaluate=False),
                             evaluate=False)),
             OperationType.EXPAND, note="product rule: f'g + fg'"),
        Step(2, sp.Eq(sp.Function("h_prime")(x), simplified),
             OperationType.SIMPLIFY, note="substitute and combine"),
        Step(3, sp.Eq(sp.Function("h_prime")(x), simplified),
             OperationType.FINAL, note="result"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_TWO_STEP,  # placeholder
        variables=[x],
        steps=steps,
        final_answer=simplified,
    )


def gen_chain_rule(difficulty: int = 3,
                   seed: Optional[int] = None) -> Solution:
    """d/dx of (ax + b)^n.

    Steps:
      0. INITIAL:    f(x) = (ax + b)^n
      1. EXPAND:     f'(x) = n*(ax+b)^(n-1) * d/dx(ax + b)   (chain rule)
      2. SIMPLIFY:   f'(x) = n*a*(ax+b)^(n-1)
      3. FINAL
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    a = rng.randint(max(1, lo), hi) or 1
    b = rng.randint(lo, hi)
    n = rng.randint(2, 4)

    inner = sp.Add(a * x, sp.Integer(b), evaluate=False)
    outer = sp.Pow(inner, n, evaluate=False)
    inner_derivative = sp.Integer(a)
    chain_form = sp.Mul(n, sp.Pow(inner, n - 1, evaluate=False),
                        inner_derivative, evaluate=False)
    final = n * a * (a * x + b) ** (n - 1)

    steps = [
        Step(0, sp.Eq(sp.Function("f")(x), outer),
             OperationType.INITIAL, note=f"f(x) = (ax + b)^{n}"),
        Step(1, sp.Eq(sp.Function("f_prime")(x), chain_form),
             OperationType.EXPAND, note="chain rule: outer' * inner'"),
        Step(2, sp.Eq(sp.Function("f_prime")(x), final),
             OperationType.SIMPLIFY, note="d/dx(ax + b) = a"),
        Step(3, sp.Eq(sp.Function("f_prime")(x), final),
             OperationType.FINAL, note="result"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[x],
        steps=steps,
        final_answer=final,
    )


def gen_polynomial_integral(difficulty: int = 2,
                            seed: Optional[int] = None) -> Solution:
    """Indefinite integral of a polynomial.

    Steps:
      0. INITIAL:    ∫ p(x) dx
      1. SIMPLIFY:   term-by-term anti-derivative
      2. FINAL:      result + C
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    degree = rng.randint(1, min(3, difficulty + 1))
    coeffs = [rng.randint(lo, hi) for _ in range(degree + 1)]
    while coeffs[0] == 0:
        coeffs[0] = rng.randint(max(1, lo), hi)

    poly = sum(c * x ** (degree - i) for i, c in enumerate(coeffs))
    antideriv_no_const = sp.integrate(poly, x)
    C = sp.Symbol("C")
    antideriv = antideriv_no_const + C

    # Middle step: term-by-term using power rule for integration.
    middle_terms = []
    for i, c in enumerate(coeffs):
        power = degree - i
        new_power = power + 1
        middle_terms.append(sp.Mul(sp.Rational(c, new_power),
                                   x ** new_power, evaluate=False))
    middle = sp.Add(*middle_terms, C, evaluate=False)

    F = sp.Function("F")
    steps = [
        Step(0, sp.Eq(F(x), sp.Integral(poly, x)),
             OperationType.INITIAL, note="indefinite integral"),
        Step(1, sp.Eq(F(x), middle),
             OperationType.SIMPLIFY,
             note="power rule for integration term-by-term"),
        Step(2, sp.Eq(F(x), antideriv),
             OperationType.FINAL, note="simplified, + C"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[x],
        steps=steps,
        final_answer=antideriv,
    )


_GENERATORS = {
    "calc_polynomial_derivative": gen_polynomial_derivative,
    "calc_product_rule":          gen_product_rule,
    "calc_chain_rule":            gen_chain_rule,
    "calc_polynomial_integral":   gen_polynomial_integral,
}

_KINDS = [
    ProblemKind("calc_polynomial_derivative", "Polynomial derivative", (1, 4)),
    ProblemKind("calc_product_rule",          "Product rule",          (2, 5)),
    ProblemKind("calc_chain_rule",            "Chain rule",            (3, 5)),
    ProblemKind("calc_polynomial_integral",   "Polynomial integral",   (2, 5)),
]


# ===========================================================================
# Misconceptions
# ===========================================================================

def _extract_rhs(expr):
    """If expr is Eq(f(x), rhs), return rhs; else expr itself."""
    if isinstance(expr, sp.Equality):
        return expr.rhs
    return expr


class DerivativeOfConstantIsX(Misconception):
    id = "derivative_constant_as_x"
    name = "Treating a constant as having derivative 1"
    description = ("Constant terms have derivative 0, but the student treats "
                   "them like x (derivative 1) and carries them forward.")
    category = "calculus_basic"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        if step_index == 0:
            return False
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return False
        poly = _extract_rhs(initial)
        # Must contain a literal nonzero constant term.
        if not isinstance(poly, sp.Add):
            return False
        return any(t.is_number and t != 0 for t in poly.args)

    def apply(self, step, solution, step_index):
        # Add a stray constant back into the derivative.
        if not isinstance(step.expression, sp.Equality):
            return step
        initial = solution.steps[0].expression
        poly = _extract_rhs(initial)
        const_term = next((t for t in poly.args
                           if t.is_number and t != 0), sp.Integer(0))
        # Pretend its derivative was the constant itself (treated as `c*x`
        # and then evaluated `c*1 = c`).
        new_rhs = step.expression.rhs + const_term
        return Step(step.index,
                    sp.Eq(step.expression.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class PowerRuleDropsExponent(Misconception):
    id = "power_rule_drops_exponent"
    name = "Power rule drops the original exponent"
    description = ("The student decrements the exponent but forgets to "
                   "multiply by the original exponent. d/dx(x^3) is written "
                   "as x^2 instead of 3x^2.")
    category = "calculus_power_rule"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        # Need the result to contain at least one Pow with exponent >= 1.
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        for sub in sp.preorder_traversal(expr.rhs):
            if isinstance(sub, sp.Pow) and sub.args[1].is_integer and sub.args[1] >= 1:
                return True
        return False

    def apply(self, step, solution, step_index):
        # Strip the multiplicative coefficient on Pow terms.
        if not isinstance(step.expression, sp.Equality):
            return step
        new_rhs = _strip_pow_coefficient(step.expression.rhs)
        if new_rhs == step.expression.rhs:
            return step
        return Step(step.index, sp.Eq(step.expression.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class ChainRuleDropsInnerDerivative(Misconception):
    id = "chain_rule_drops_inner"
    name = "Chain rule drops the inner derivative"
    description = ("In d/dx[(ax+b)^n], the student writes n*(ax+b)^(n-1) "
                   "but forgets to multiply by a (the derivative of the "
                   "inner expression).")
    category = "calculus_chain_rule"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL,
                      OperationType.EXPAND)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        # Heuristic: the initial step must be Eq(f(x), Pow(Add, n)) with n >= 2.
        if step_index == 0:
            return False
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return False
        for sub in sp.preorder_traversal(initial.rhs):
            if (isinstance(sub, sp.Pow) and isinstance(sub.args[0], sp.Add)
                    and sub.args[1].is_integer and sub.args[1] >= 2):
                return True
        return False

    def apply(self, step, solution, step_index):
        if not isinstance(step.expression, sp.Equality):
            return step
        # Get the inner derivative `a` from the initial Pow base.
        initial = solution.steps[0].expression
        a_coeff = None
        for sub in sp.preorder_traversal(initial.rhs):
            if (isinstance(sub, sp.Pow) and isinstance(sub.args[0], sp.Add)
                    and sub.args[1].is_integer and sub.args[1] >= 2):
                # Find the coefficient on x in the base.
                base = sub.args[0]
                for term in base.args:
                    if term.has(x):
                        if isinstance(term, sp.Mul):
                            for f in term.args:
                                if f.is_number:
                                    a_coeff = f
                                    break
                        else:
                            a_coeff = sp.Integer(1)
                        break
                break
        if a_coeff is None or a_coeff == 1:
            # Inner derivative is 1; dropping it is a no-op. Use a different
            # perturbation: drop the n*(ax+b)^(n-1) coefficient n.
            return step
        # Buggy version: divide by a (forgot to multiply by it).
        new_rhs = sp.expand(step.expression.rhs / a_coeff)
        return Step(step.index, sp.Eq(step.expression.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class ProductRuleAsSumRule(Misconception):
    id = "product_rule_as_sum"
    name = "Differentiating a product term-by-term"
    description = ("The student treats d/dx[f * g] as f' * g' (the 'sum rule' "
                   "form), instead of using the product rule f'g + fg'.")
    category = "calculus_product_rule"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL,
                      OperationType.EXPAND)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        if step_index == 0:
            return False
        # The initial step's rhs must be a Mul of two non-constant factors.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return False
        rhs = initial.rhs
        if not isinstance(rhs, sp.Mul):
            return False
        non_const = [a for a in rhs.args if a.has(x)]
        return len(non_const) >= 2

    def apply(self, step, solution, step_index):
        if not isinstance(step.expression, sp.Equality):
            return step
        initial = solution.steps[0].expression
        rhs = initial.rhs
        non_const = [a for a in rhs.args if a.has(x)]
        if len(non_const) < 2:
            return step
        f, g = non_const[0], non_const[1]
        buggy = sp.diff(f, x) * sp.diff(g, x)
        return Step(step.index, sp.Eq(step.expression.lhs, sp.expand(buggy)),
                    step.operation, note=f"sabotage:{self.id}")


class MissingConstantOfIntegration(Misconception):
    id = "missing_constant_of_integration"
    name = "Forgot the constant of integration"
    description = ("Indefinite integrals require + C; the student drops it "
                   "from the final answer.")
    category = "calculus_integration"
    difficulty = 1
    applicable_ops = (OperationType.FINAL,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.FINAL:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        return sp.Symbol("C") in expr.rhs.free_symbols

    def apply(self, step, solution, step_index):
        C = sp.Symbol("C")
        new_rhs = step.expression.rhs.subs(C, 0)
        return Step(step.index, sp.Eq(step.expression.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class IntegralPowerRuleDividesByOriginal(Misconception):
    id = "integral_divides_by_original_power"
    name = "Integration divides by the original exponent (not new one)"
    description = ("The power rule for integration is ∫x^n dx = x^(n+1)/(n+1), "
                   "but the student divides by n instead of n+1.")
    category = "calculus_integration"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops or step_index == 0:
            return False
        # Initial step must contain an integral.
        initial = solution.steps[0].expression
        return initial.has(sp.Integral)

    def apply(self, step, solution, step_index):
        # Reconstruct the buggy antiderivative.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        integrand = None
        for sub in sp.preorder_traversal(initial.rhs):
            if isinstance(sub, sp.Integral):
                integrand = sub.args[0]
                break
        if integrand is None:
            return step
        # Build the wrong antiderivative: for each term c*x^n, produce c*x^(n+1)/n
        # (dividing by n instead of n+1).
        buggy_terms = []
        terms = sp.Add.make_args(sp.expand(integrand))
        for term in terms:
            poly = sp.Poly(term, x)
            for (power_tuple, coeff) in poly.terms():
                n = power_tuple[0]
                if n == 0:
                    # Constant term: correct integral is c*x; buggy version
                    # could be c*x/0 (undefined). Skip the constant.
                    buggy_terms.append(coeff * x)
                else:
                    buggy_terms.append(sp.Rational(coeff, n) * x ** (n + 1))
        C = sp.Symbol("C")
        buggy = sp.Add(*buggy_terms) + C
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


# ---------- Helpers ----------

def _strip_pow_coefficient(expr):
    """Replace c*x^n with x^n inside an additive expression."""
    if isinstance(expr, sp.Add):
        return sp.Add(*[_strip_pow_coefficient(a) for a in expr.args])
    if isinstance(expr, sp.Mul):
        non_num = [a for a in expr.args if not a.is_number]
        # Keep only the Pow factors (drop numeric coeff).
        if any(isinstance(a, sp.Pow) for a in non_num):
            return sp.Mul(*non_num)
    return expr


# Register misconceptions
_CALCULUS_MISCONCEPTIONS = [
    DerivativeOfConstantIsX(),
    PowerRuleDropsExponent(),
    ChainRuleDropsInnerDerivative(),
    ProductRuleAsSumRule(),
    MissingConstantOfIntegration(),
    IntegralPowerRuleDividesByOriginal(),
]
# (We don't call register() on these; the Domain owns them. This avoids
#  polluting the global algebra-misconception registry with calculus entries.)


# ===========================================================================
# Domain
# ===========================================================================

class CalculusDomain(Domain):
    id = "calculus"
    label = "Calculus"
    description = ("Derivatives and indefinite integrals: power rule, chain rule, "
                   "product rule, integration by power rule.")

    def problem_kinds(self) -> list[ProblemKind]:
        return _KINDS

    def generate(self, kind_id: str, difficulty: int = 1,
                 seed: Optional[int] = None) -> Solution:
        if kind_id not in _GENERATORS:
            raise KeyError(f"Unknown calculus kind: {kind_id}")
        return _GENERATORS[kind_id](difficulty=difficulty, seed=seed)

    def misconceptions(self):
        return _CALCULUS_MISCONCEPTIONS

    def states_equivalent(self, a: Any, b: Any) -> bool:
        """For calculus: compare RHSes via SymPy expression equivalence.

        Both sides are of the form Eq(f(x), expr); we check the expressions
        are equal (modulo +C for integrals).
        """
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        # Pull RHS; allow either Integral form or expression.
        a_rhs = a.rhs
        b_rhs = b.rhs
        # If one side has an Integral, evaluate it before comparing.
        a_eval = a_rhs.doit() if a_rhs.has(sp.Integral) else a_rhs
        b_eval = b_rhs.doit() if b_rhs.has(sp.Integral) else b_rhs
        # Treat +C symbolically as a free parameter: if (a - b) is a constant
        # in x, they're equivalent.
        diff_expr = sp.simplify(a_eval - b_eval)
        if diff_expr == 0:
            return True
        try:
            # If the difference is constant (no x), accept.
            return x not in diff_expr.free_symbols
        except AttributeError:
            return False


register_domain(CalculusDomain())
