"""Geometry domain.

Generates triangle, circle, and rectangle problems where the student computes
a length, area, or perimeter step by step.

Equivalence here is NUMERICAL with tolerance -geometry computations end at
a number. We use exact arithmetic where possible (SymPy) and fall back to
floating-point with a small epsilon.

Misconceptions include:
  - Pythagorean: swapping legs vs. hypotenuse (the most common student error)
  - Area: dropping factor of 1/2 in triangle area
  - Wrong perimeter formula (multiplying instead of summing)
  - Confusing radius and diameter
  - π vs 2π confusion in circumference vs. area
"""
from __future__ import annotations

import random
from typing import Any, Optional

import sympy as sp

from ..domain import Domain, ProblemKind, register_domain
from ..misconceptions.base import Misconception
from ..types import OperationType, ProblemType, Solution, Step


# Variables used in geometry problems
a, b, c = sp.symbols("a b c", positive=True)
r = sp.symbols("r", positive=True)
side = sp.symbols("s", positive=True)
result = sp.symbols("R", positive=True)

EPS = sp.Rational(1, 10000)   # tolerance for numerical equivalence


# ===========================================================================
# Generators
# ===========================================================================

# Pythagorean triples for clean integer answers
_PYTHAG_TRIPLES = [
    (3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25),
    (20, 21, 29), (9, 40, 41), (12, 35, 37), (11, 60, 61),
    (6, 8, 10), (9, 12, 15), (10, 24, 26),
]


def gen_pythagorean(difficulty: int = 1,
                    seed: Optional[int] = None) -> Solution:
    """Find the hypotenuse (or a leg) given the other two sides.

    Steps:
      0. INITIAL:    legs a, b; find hypotenuse c
      1. SIMPLIFY:   c^2 = a^2 + b^2
      2. SIMPLIFY:   c^2 = sum
      3. SQUARE_ROOT: c = sqrt(sum)
      4. FINAL:      c = number
    """
    rng = random.Random(seed)
    # Use a smaller triple at low difficulty.
    if difficulty <= 2:
        triple_pool = _PYTHAG_TRIPLES[:5]
    else:
        triple_pool = _PYTHAG_TRIPLES
    leg_a, leg_b, hyp = rng.choice(triple_pool)

    leg_a_s = sp.Integer(leg_a)
    leg_b_s = sp.Integer(leg_b)
    hyp_s = sp.Integer(hyp)
    sum_sq = sp.Integer(leg_a ** 2 + leg_b ** 2)
    c_sym = sp.Symbol("c", positive=True)

    steps = [
        Step(0, sp.Eq(c_sym,
                      sp.Symbol(f"hyp(a={leg_a},b={leg_b})")),
             OperationType.INITIAL,
             note=f"right triangle with legs {leg_a} and {leg_b}; find c"),
        Step(1, sp.Eq(c_sym ** 2,
                      sp.Add(sp.Pow(leg_a_s, 2, evaluate=False),
                             sp.Pow(leg_b_s, 2, evaluate=False),
                             evaluate=False)),
             OperationType.SIMPLIFY, note="Pythagorean theorem: c^2 = a^2 + b^2"),
        Step(2, sp.Eq(c_sym ** 2, sum_sq),
             OperationType.SIMPLIFY, note="compute the sum"),
        Step(3, sp.Eq(c_sym, sp.sqrt(sum_sq)),
             OperationType.SQUARE_ROOT, note="square root both sides"),
        Step(4, sp.Eq(c_sym, hyp_s),
             OperationType.FINAL, note=f"c = {hyp}"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[c_sym],
        steps=steps,
        final_answer=hyp_s,
    )


def gen_triangle_area(difficulty: int = 1,
                      seed: Optional[int] = None) -> Solution:
    """Area of a triangle given base and height.

    Steps:
      0. INITIAL:    base = b, height = h
      1. SIMPLIFY:   A = (1/2) * b * h
      2. SIMPLIFY:   A = (1/2) * (b * h)
      3. FINAL:      A = number
    """
    rng = random.Random(seed)
    base = rng.randint(2, 10 + difficulty * 2) * 2  # even → integer area
    height = rng.randint(2, 10 + difficulty * 2)
    A_val = sp.Rational(base * height, 2)
    A = sp.Symbol("A", positive=True)
    half = sp.Rational(1, 2)

    steps = [
        Step(0, sp.Eq(A, sp.Symbol(f"area(base={base},height={height})")),
             OperationType.INITIAL,
             note=f"triangle with base {base} and height {height}; find area"),
        Step(1, sp.Eq(A,
                      sp.Mul(half, sp.Integer(base), sp.Integer(height),
                             evaluate=False)),
             OperationType.SIMPLIFY, note="area formula: (1/2) * base * height"),
        Step(2, sp.Eq(A,
                      sp.Mul(half, sp.Integer(base * height),
                             evaluate=False)),
             OperationType.SIMPLIFY, note="multiply base * height"),
        Step(3, sp.Eq(A, A_val),
             OperationType.FINAL, note="multiply by 1/2"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[A],
        steps=steps,
        final_answer=A_val,
    )


def gen_rectangle(difficulty: int = 1,
                  seed: Optional[int] = None) -> Solution:
    """Area and perimeter of a rectangle (combined into one Solution).

    For sabotage targeting, this gives both an Area step and a Perimeter step
    that can each be corrupted.

    Steps:
      0. INITIAL:    length L, width W
      1. SIMPLIFY:   A = L * W (area)
      2. SIMPLIFY:   P = 2L + 2W (perimeter)
      3. FINAL:      A = number, P = number  (encoded as two final steps)
    """
    rng = random.Random(seed)
    L = rng.randint(3, 8 + difficulty * 2)
    W = rng.randint(2, 8 + difficulty * 2)
    A_val = sp.Integer(L * W)
    P_val = sp.Integer(2 * L + 2 * W)
    A = sp.Symbol("A", positive=True)
    P = sp.Symbol("P", positive=True)

    steps = [
        Step(0, sp.Eq(sp.Symbol("rect"),
                      sp.Symbol(f"rectangle(L={L},W={W})")),
             OperationType.INITIAL,
             note=f"rectangle with length {L} and width {W}"),
        Step(1, sp.Eq(A, sp.Mul(sp.Integer(L), sp.Integer(W), evaluate=False)),
             OperationType.SIMPLIFY, note="area: A = L * W"),
        Step(2, sp.Eq(A, A_val),
             OperationType.SIMPLIFY, note=f"compute area"),
        Step(3, sp.Eq(P,
                      sp.Add(sp.Mul(2, sp.Integer(L), evaluate=False),
                             sp.Mul(2, sp.Integer(W), evaluate=False),
                             evaluate=False)),
             OperationType.SIMPLIFY, note="perimeter: P = 2L + 2W"),
        Step(4, sp.Eq(P, P_val),
             OperationType.FINAL, note="compute perimeter"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[A, P],
        steps=steps,
        final_answer=(A_val, P_val),
    )


def gen_circle(difficulty: int = 1,
               seed: Optional[int] = None) -> Solution:
    """Area and circumference of a circle.

    Steps:
      0. INITIAL:    radius r
      1. SIMPLIFY:   A = π r^2
      2. SIMPLIFY:   A = π * number
      3. SIMPLIFY:   C = 2 π r
      4. FINAL:      C = 2π * number
    """
    rng = random.Random(seed)
    r_val = rng.randint(2, 6 + difficulty * 2)
    pi = sp.pi
    A_val = pi * r_val ** 2
    C_val = 2 * pi * r_val
    A = sp.Symbol("A", positive=True)
    C = sp.Symbol("C", positive=True)
    r_sym = sp.Symbol("r", positive=True)

    steps = [
        Step(0, sp.Eq(r_sym, sp.Integer(r_val)),
             OperationType.INITIAL, note=f"circle with radius {r_val}"),
        Step(1, sp.Eq(A, sp.Mul(pi, sp.Pow(r_sym, 2, evaluate=False),
                                evaluate=False)),
             OperationType.SIMPLIFY, note="area: A = π r²"),
        Step(2, sp.Eq(A, A_val),
             OperationType.SIMPLIFY, note="substitute r"),
        Step(3, sp.Eq(C, sp.Mul(2, pi, r_sym, evaluate=False)),
             OperationType.SIMPLIFY, note="circumference: C = 2 π r"),
        Step(4, sp.Eq(C, C_val),
             OperationType.FINAL, note="substitute r"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[A, C],
        steps=steps,
        final_answer=(A_val, C_val),
    )


_GENERATORS = {
    "geom_pythagorean":    gen_pythagorean,
    "geom_triangle_area":  gen_triangle_area,
    "geom_rectangle":      gen_rectangle,
    "geom_circle":         gen_circle,
}

_KINDS = [
    ProblemKind("geom_pythagorean",   "Pythagorean theorem", (1, 4)),
    ProblemKind("geom_triangle_area", "Triangle area",       (1, 4)),
    ProblemKind("geom_rectangle",     "Rectangle (area + perimeter)", (1, 4)),
    ProblemKind("geom_circle",        "Circle (area + circumference)", (2, 5)),
]


# ===========================================================================
# Misconceptions
# ===========================================================================

class PythagSwapLegsAndHypotenuse(Misconception):
    id = "pythag_swap_legs_hyp"
    name = "Swapping legs and hypotenuse in Pythagoras"
    description = ("The student treats one of the legs as the hypotenuse. "
                   "Instead of a² + b² = c², they write a² + c² = b² (or "
                   "subtract instead of add).")
    category = "geometry_pythagoras"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.SIMPLIFY:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        # Must contain c^2 on lhs.
        return expr.lhs.has(sp.Pow)

    def apply(self, step, solution, step_index):
        # Replace c^2 = a^2 + b^2 with c^2 = b^2 - a^2 (sign-flipped) -a
        # classic student error.
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        rhs = expr.rhs
        if isinstance(rhs, sp.Add) and len(rhs.args) == 2:
            new_rhs = rhs.args[1] - rhs.args[0]
            return Step(step.index, sp.Eq(expr.lhs, new_rhs),
                        step.operation, note=f"sabotage:{self.id}")
        return step


class DroppedHalfInTriangleArea(Misconception):
    id = "dropped_half_triangle_area"
    name = "Dropped the 1/2 in triangle area"
    description = ("The student writes A = b * h instead of (1/2) * b * h.")
    category = "geometry_area"
    difficulty = 1
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        # Find Rational(1, 2) in the expression.
        return sp.Rational(1, 2) in [arg for arg in sp.preorder_traversal(expr)]

    def apply(self, step, solution, step_index):
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return step
        # Strip the 1/2 factor.
        def strip_half(node):
            if isinstance(node, sp.Mul):
                args = [a for a in node.args if a != sp.Rational(1, 2)]
                if len(args) < len(node.args):
                    return sp.Mul(*args)
            return node
        new_rhs = expr.rhs.replace(
            lambda n: isinstance(n, sp.Mul) and sp.Rational(1, 2) in n.args,
            strip_half)
        if new_rhs == expr.rhs:
            new_rhs = expr.rhs * 2  # fallback: literally doubled
        return Step(step.index, sp.Eq(expr.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class PerimeterUsesAreaFormula(Misconception):
    id = "perimeter_uses_area_formula"
    name = "Confusing perimeter and area formulas"
    description = ("The student computes the perimeter as L * W (the area "
                   "formula) instead of 2L + 2W.")
    category = "geometry_formulas"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        # Heuristic: lhs is the perimeter symbol P.
        return isinstance(expr.lhs, sp.Symbol) and expr.lhs.name == "P"

    def apply(self, step, solution, step_index):
        # Reconstruct from the rectangle's initial step.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        # Parse "rectangle(L=...,W=...)" from the initial.
        rhs_str = str(initial.rhs)
        import re
        m = re.match(r"rectangle\(L=(\d+),W=(\d+)\)", rhs_str)
        if not m:
            return step
        L = int(m.group(1))
        W = int(m.group(2))
        buggy = sp.Integer(L * W)   # area instead of perimeter
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


class RadiusVsDiameterConfusion(Misconception):
    id = "radius_vs_diameter"
    name = "Using diameter where radius is required"
    description = ("In circle formulas, the student substitutes the diameter "
                   "(2r) instead of the radius r -doubling the radius "
                   "everywhere.")
    category = "geometry_formulas"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops or step_index == 0:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        return expr.rhs.has(sp.pi)

    def apply(self, step, solution, step_index):
        # Get the original radius from the INITIAL step.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        # initial: Eq(r, value)
        r_val = initial.rhs
        # Substitute r -> 2r in the current rhs by replacing r_val with 2*r_val.
        if not r_val.is_number:
            return step
        new_rhs = step.expression.rhs.subs(r_val, 2 * r_val)
        if sp.simplify(new_rhs - step.expression.rhs) == 0:
            # Substitution didn't take effect (r_val isn't literally present).
            # Multiply numeric powers in the current rhs by 2 for area-like
            # terms, by 2 for circumference (linear in r).
            new_rhs = step.expression.rhs * 2
        return Step(step.index, sp.Eq(step.expression.lhs, new_rhs),
                    step.operation, note=f"sabotage:{self.id}")


class CircumferenceVsAreaSwap(Misconception):
    id = "circumference_vs_area_swap"
    name = "Confusing circumference and area formulas"
    description = ("The student uses 2πr where πr² is needed (or vice versa) "
                   "-mixing up linear and squared dependencies on r.")
    category = "geometry_formulas"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.SIMPLIFY or step_index == 0:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        return expr.rhs.has(sp.pi) and isinstance(expr.lhs, sp.Symbol)

    def apply(self, step, solution, step_index):
        # If lhs is A (area), swap to circumference form: 2πr instead of πr².
        # Find r_val from the initial step.
        initial = solution.steps[0].expression
        if not isinstance(initial, sp.Equality):
            return step
        r_val = initial.rhs
        if not r_val.is_number:
            return step
        name = step.expression.lhs.name
        if name == "A":
            buggy = 2 * sp.pi * r_val
        elif name == "C":
            buggy = sp.pi * r_val ** 2
        else:
            return step
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


_GEOMETRY_MISCONCEPTIONS = [
    PythagSwapLegsAndHypotenuse(),
    DroppedHalfInTriangleArea(),
    PerimeterUsesAreaFormula(),
    RadiusVsDiameterConfusion(),
    CircumferenceVsAreaSwap(),
]


# ===========================================================================
# Domain
# ===========================================================================

class GeometryDomain(Domain):
    id = "geometry"
    label = "Geometry"
    description = "Triangles, rectangles, circles: areas, perimeters, Pythagoras."

    def problem_kinds(self) -> list[ProblemKind]:
        return _KINDS

    def generate(self, kind_id: str, difficulty: int = 1,
                 seed: Optional[int] = None) -> Solution:
        if kind_id not in _GENERATORS:
            raise KeyError(f"Unknown geometry kind: {kind_id}")
        return _GENERATORS[kind_id](difficulty=difficulty, seed=seed)

    def misconceptions(self):
        return _GEOMETRY_MISCONCEPTIONS

    def states_equivalent(self, a: Any, b: Any) -> bool:
        """Geometry equivalence: numerical with small tolerance.

        Geometry computations end in concrete numbers (lengths, areas).
        We treat Eq(sym, val_a) and Eq(sym, val_b) as equivalent iff
        sym matches and |val_a - val_b| < tolerance.
        """
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        if a.lhs != b.lhs:
            # Different variables can still be equivalent if both reduce.
            # For now, require matching lhs.
            if str(a.lhs) != str(b.lhs):
                return False
        try:
            diff_expr = sp.simplify(a.rhs - b.rhs)
            if diff_expr == 0:
                return True
            # Float comparison fallback.
            return abs(float(diff_expr)) < float(EPS)
        except (TypeError, ValueError):
            return False


register_domain(GeometryDomain())
