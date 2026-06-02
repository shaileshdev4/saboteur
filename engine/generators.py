"""Problem generators.

Each generator produces a `Solution` containing the problem and the canonical
step-by-step solution as an ordered list of `Step`s.

Design rules:
- Every Step's expression must be SymPy-verifiable against the previous step
  using `verifier.states_equivalent` (with the exception of FACTOR/EXPAND
  which preserve solution-set but transform the form).
- We tag each step with an OperationType so misconception transforms can
  decide whether they apply.
- Problems are parameterized by difficulty (an int 1-5) which controls
  coefficient magnitude and whether negatives / fractions appear.
"""
from __future__ import annotations

import random
from typing import Optional

import sympy as sp
from sympy import Eq, Rational, sqrt, symbols

from .types import OperationType, ProblemType, Solution, Step
from .verifier import equations_equivalent, expressions_equivalent

x = symbols("x")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nonzero_int(low: int, high: int, rng: random.Random) -> int:
    """Random integer in [low, high] excluding zero."""
    while True:
        v = rng.randint(low, high)
        if v != 0:
            return v


def _coef_range(difficulty: int) -> tuple[int, int]:
    """Maps difficulty 1-5 to a coefficient range."""
    return {
        1: (1, 9),
        2: (-9, 9),
        3: (-12, 12),
        4: (-15, 15),
        5: (-20, 20),
    }.get(difficulty, (1, 9))


# ---------------------------------------------------------------------------
# Linear one-variable: ax + b = c
# ---------------------------------------------------------------------------

def gen_linear_one_var(difficulty: int = 1, seed: Optional[int] = None) -> Solution:
    """Generate problems of form ax + b = c, with integer solution.

    Steps produced:
      0. INITIAL:   ax + b = c
      1. TRANSPOSE: ax = c - b
      2. SIMPLIFY:  ax = (c-b)
      3. DIVIDE:    x = (c-b)/a
      4. FINAL:     x = answer
    If a == 1 we skip the divide step. If b == 0 we skip transpose.
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    # Generate so the answer is a nice integer.
    answer = _nonzero_int(lo, hi, rng)
    a = _nonzero_int(max(1, lo), hi, rng) if difficulty == 1 else _nonzero_int(lo, hi, rng)
    if a == 0:
        a = 1
    b = rng.randint(lo, hi)
    c = a * answer + b

    steps: list[Step] = []
    idx = 0
    steps.append(Step(idx, Eq(a * x + b, c), OperationType.INITIAL,
                      note="initial equation"))
    idx += 1

    if b != 0:
        steps.append(Step(idx, Eq(a * x, c - b), OperationType.TRANSPOSE,
                          note=f"subtract {b} from both sides"))
        idx += 1

    if a != 1:
        # Use Rational to keep symbolic precision if division isn't exact.
        rhs = Rational(c - b, a)
        steps.append(Step(idx, Eq(x, rhs), OperationType.DIVIDE_BOTH_SIDES,
                          note=f"divide both sides by {a}"))
        idx += 1

    # Final answer step (often a duplicate of the divide step's result).
    if steps[-1].operation != OperationType.DIVIDE_BOTH_SIDES or a == 1:
        steps.append(Step(idx, Eq(x, sp.Integer(answer)), OperationType.FINAL,
                          note="solution"))

    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[x],
        steps=steps,
        final_answer=sp.Integer(answer) if a == 1 else Rational(c - b, a),
    )


# ---------------------------------------------------------------------------
# Linear two-step: a(x + p) = bx + q  --> requires distribution + collection
# ---------------------------------------------------------------------------

def gen_linear_two_step(difficulty: int = 2, seed: Optional[int] = None) -> Solution:
    """Generate problems of form a(x + p) = bx + q, with integer solution.

    Steps:
      0. INITIAL:   a(x+p) = bx + q
      1. EXPAND:    ax + ap = bx + q
      2. TRANSPOSE: ax - bx = q - ap     (move bx to left, ap to right)
      3. SIMPLIFY:  (a-b)x = q - ap
      4. DIVIDE:    x = (q - ap)/(a - b)
      5. FINAL:     x = answer
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)

    # Choose answer and coefficients so a != b (otherwise no solution / infinite).
    answer = _nonzero_int(lo, hi, rng)
    for _ in range(30):
        a = _nonzero_int(lo, hi, rng)
        b = rng.randint(lo, hi)
        if a != b:
            break
    else:
        a, b = 2, 1  # fallback

    p = rng.randint(lo, hi)
    # We want answer to satisfy a(answer + p) = b*answer + q  =>  q = a(answer+p) - b*answer
    q = a * (answer + p) - b * answer

    steps: list[Step] = []
    idx = 0
    # Keep the initial in unevaluated form so it actually contains a*(x+p)
    # rather than being auto-distributed by SymPy.
    initial_lhs = sp.Mul(sp.Integer(a), sp.Add(x, sp.Integer(p), evaluate=False),
                         evaluate=False)
    steps.append(Step(idx, Eq(initial_lhs, b * x + q, evaluate=False),
                      OperationType.INITIAL, note="initial equation"))
    idx += 1
    steps.append(Step(idx, Eq(a * x + a * p, b * x + q), OperationType.EXPAND,
                      note=f"distribute {a}"))
    idx += 1

    # Collect x terms on left, constants on right.
    coef = a - b
    const_rhs = q - a * p
    steps.append(Step(idx, Eq(a * x - b * x, q - a * p), OperationType.TRANSPOSE,
                      note=f"subtract {b}x from both sides and subtract {a*p} from both sides"))
    idx += 1
    steps.append(Step(idx, Eq(coef * x, const_rhs), OperationType.SIMPLIFY,
                      note="combine like terms"))
    idx += 1

    if coef != 1:
        rhs = Rational(const_rhs, coef)
        steps.append(Step(idx, Eq(x, rhs), OperationType.DIVIDE_BOTH_SIDES,
                          note=f"divide both sides by {coef}"))
        idx += 1

    steps.append(Step(idx, Eq(x, sp.Integer(answer)), OperationType.FINAL,
                      note="solution"))

    return Solution(
        problem_type=ProblemType.LINEAR_TWO_STEP,
        variables=[x],
        steps=steps,
        final_answer=sp.Integer(answer),
    )


# ---------------------------------------------------------------------------
# Quadratic by factoring: x^2 + bx + c = 0 with integer roots
# ---------------------------------------------------------------------------

def gen_quadratic_factor(difficulty: int = 2, seed: Optional[int] = None) -> Solution:
    """Generate a factorable quadratic with two distinct integer roots.

    Steps:
      0. INITIAL:   x^2 + bx + c = 0
      1. FACTOR:    (x - r1)(x - r2) = 0
      2. SIMPLIFY (zero product): two linear equations effectively, but we
         collapse to the FINAL step listing both roots.
      3. FINAL:     x = r1, r2
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    for _ in range(30):
        r1 = _nonzero_int(lo, hi, rng)
        r2 = _nonzero_int(lo, hi, rng)
        if r1 != r2:
            break
    else:
        r1, r2 = 2, 3

    b = -(r1 + r2)
    c = r1 * r2

    steps: list[Step] = []
    idx = 0
    steps.append(Step(idx, Eq(x ** 2 + b * x + c, 0), OperationType.INITIAL,
                      note="initial quadratic"))
    idx += 1
    steps.append(Step(idx, Eq((x - r1) * (x - r2), 0), OperationType.FACTOR,
                      note=f"factor into roots {r1} and {r2}"))
    idx += 1
    # FINAL: present as a set
    roots = sp.FiniteSet(sp.Integer(r1), sp.Integer(r2))
    # We can't easily put a set in Eq; encode as a tuple-equation: x ∈ {r1, r2}.
    # For verification purposes we still store the Eq form of the factored line
    # and rely on the final_answer field for the canonical answer set.
    steps.append(Step(idx, sp.Eq(x, sp.Integer(r1)), OperationType.FINAL,
                      note=f"one root is {r1}"))
    idx += 1
    steps.append(Step(idx, sp.Eq(x, sp.Integer(r2)), OperationType.FINAL,
                      note=f"other root is {r2}"))

    return Solution(
        problem_type=ProblemType.QUADRATIC_FACTOR,
        variables=[x],
        steps=steps,
        final_answer=roots,
    )


# ---------------------------------------------------------------------------
# Quadratic via the formula: ax^2 + bx + c = 0 with nice discriminant
# ---------------------------------------------------------------------------

def gen_quadratic_formula(difficulty: int = 3, seed: Optional[int] = None) -> Solution:
    """Generate ax^2 + bx + c = 0 where the discriminant is a perfect square.

    Steps:
      0. INITIAL:   ax^2 + bx + c = 0
      1. SIMPLIFY:  discriminant = b^2 - 4ac    (we record the discriminant value)
      2. SQUARE_ROOT: x = (-b ± sqrt(D))/(2a)
      3. FINAL:     x = r1, r2
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    # Generate roots, derive coefficients, ensure discriminant is a perfect square.
    for _ in range(30):
        r1 = _nonzero_int(lo, hi, rng)
        r2 = _nonzero_int(lo, hi, rng)
        a = _nonzero_int(1, max(2, hi // 4), rng)  # keep `a` modest
        if r1 != r2:
            break
    else:
        r1, r2, a = 2, 3, 1

    # ax^2 + bx + c = a(x - r1)(x - r2)
    b = -a * (r1 + r2)
    c = a * r1 * r2
    discriminant = b * b - 4 * a * c
    sqrt_d = sp.sqrt(discriminant)

    steps: list[Step] = []
    idx = 0
    steps.append(Step(idx, Eq(a * x ** 2 + b * x + c, 0), OperationType.INITIAL,
                      note="initial quadratic"))
    idx += 1
    # We represent the discriminant calculation as an Eq for a "scratch" symbol.
    D = sp.Symbol("D")
    steps.append(Step(idx, Eq(D, sp.Integer(discriminant)), OperationType.SIMPLIFY,
                      note=f"compute discriminant b^2 - 4ac = {discriminant}"))
    idx += 1
    # The general formula application: x = (-b ± sqrt(D)) / (2a). We present
    # both branches in their simplified form as FINAL steps. We don't insert
    # an intermediate "unsimplified" step because (a) it's redundant when D
    # is a perfect square, and (b) the validator would have to skip it anyway.
    r1_expr = sp.simplify((-b + sqrt_d) / (2 * a))
    r2_expr = sp.simplify((-b - sqrt_d) / (2 * a))
    steps.append(Step(idx, Eq(x, r1_expr), OperationType.FINAL,
                      note="apply quadratic formula (+ branch)"))
    idx += 1
    steps.append(Step(idx, Eq(x, r2_expr), OperationType.FINAL,
                      note="apply quadratic formula (- branch)"))
    idx += 1

    return Solution(
        problem_type=ProblemType.QUADRATIC_FORMULA,
        variables=[x],
        steps=steps,
        final_answer=sp.FiniteSet(r1_expr, r2_expr),
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

GENERATORS = {
    ProblemType.LINEAR_ONE_VAR: gen_linear_one_var,
    ProblemType.LINEAR_TWO_STEP: gen_linear_two_step,
    ProblemType.LINEAR_FRACTION: None,  # populated below
    ProblemType.QUADRATIC_FACTOR: gen_quadratic_factor,
    ProblemType.QUADRATIC_FORMULA: gen_quadratic_formula,
    ProblemType.QUADRATIC_PERFECT_SQUARE: None,  # populated below
}


def generate(problem_type: ProblemType, difficulty: int = 1,
             seed: Optional[int] = None) -> Solution:
    return GENERATORS[problem_type](difficulty=difficulty, seed=seed)


def validate_solution(solution: Solution) -> tuple[bool, str]:
    """Sanity-check that every consecutive pair of steps preserves correctness.

    Equation-equivalence is the main check, with these exceptions:
      - Two consecutive FINAL steps (alternative roots of a quadratic): each
        FINAL must satisfy the *original* problem (steps[0]).
      - FACTOR -> FINAL: each FINAL root must satisfy the factored equation.
      - SIMPLIFY producing a scratch symbol (e.g., "D = ...") is a side
        calculation; the next step is verified against the previous non-scratch
        equation instead.
    """
    initial = solution.steps[0].expression
    sym = solution.variables[0]

    def is_scratch(step: Step) -> bool:
        if step.operation != OperationType.SIMPLIFY:
            return False
        expr = step.expression
        syms = expr.free_symbols if hasattr(expr, "free_symbols") else set()
        return sym not in syms

    for i in range(1, len(solution.steps)):
        prev_step = solution.steps[i - 1]
        curr_step = solution.steps[i]
        prev = prev_step.expression
        curr = curr_step.expression
        op = curr_step.operation

        # Skip if the current step is a scratch calculation.
        if is_scratch(curr_step):
            continue
        # If the previous step was scratch, verify against the nearest earlier
        # non-scratch step instead.
        if is_scratch(prev_step):
            j = i - 1
            while j >= 0 and is_scratch(solution.steps[j]):
                j -= 1
            if j >= 0:
                prev = solution.steps[j].expression
                prev_step = solution.steps[j]

        # Two FINAL steps in a row: alternative roots; each must satisfy
        # the original problem.
        if op == OperationType.FINAL and prev_step.operation == OperationType.FINAL:
            if not _root_satisfies(curr, initial, sym):
                return False, f"FINAL step {i} root does not satisfy initial: {curr}"
            continue

        # FACTOR -> FINAL: the root must satisfy the factored form.
        if prev_step.operation == OperationType.FACTOR and op == OperationType.FINAL:
            if _root_satisfies(curr, prev, sym):
                continue
            return False, f"FACTOR -> FINAL: root {curr} doesn't satisfy {prev}"

        # Generic FINAL: root must satisfy the previous (non-scratch) equation.
        if op == OperationType.FINAL:
            if _root_satisfies(curr, prev, sym):
                continue
            # fall through to equation-equivalence as a backup

        # Default: equation equivalence.
        if isinstance(prev, sp.Equality) and isinstance(curr, sp.Equality):
            if equations_equivalent(prev, curr):
                continue
            return False, f"Step {i} ({op.value}) not equivalent to step {i-1}: {prev} -> {curr}"
        return False, f"Step {i} ({op.value}) has unexpected non-equation form."

    return True, "ok"


def _root_satisfies(root_eq, problem_eq, sym) -> bool:
    """Check that Eq(x, r) is a root of problem_eq."""
    if not (isinstance(root_eq, sp.Equality) and isinstance(problem_eq, sp.Equality)):
        return False
    r = root_eq.rhs
    lhs_sub = problem_eq.lhs.subs(sym, r)
    rhs_sub = problem_eq.rhs.subs(sym, r)
    return sp.simplify(lhs_sub - rhs_sub) == 0


# ---------------------------------------------------------------------------
# Linear fraction: (ax + b)/k = c — rational equation
# ---------------------------------------------------------------------------

def gen_linear_fraction(difficulty: int = 2, seed: Optional[int] = None) -> Solution:
    """Generate problems of form (ax + b)/k = c, with integer solution.

    Steps:
      0. INITIAL:    (a x + b)/k = c
      1. SIMPLIFY:   distribute the division: (a/k)x + b/k = c     -- or --
                     equivalently multiply both sides by k: ax + b = kc
      2. TRANSPOSE:  ax = kc - b
      3. DIVIDE:     x = (kc - b)/a
      4. FINAL
    We use the multiply-both-sides path because it preserves a nice sum
    numerator that the cancellation-across-sum misconception can attack
    on the INITIAL step.
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    # Pick k first (always > 1), then construct numerator divisible by k.
    k = rng.randint(2, max(3, abs(hi) // 2))
    answer = _nonzero_int(lo, hi, rng)
    a = _nonzero_int(max(1, lo), hi, rng)
    # We want (a*answer + b) divisible by k. Pick b accordingly.
    target_mod = (-a * answer) % k
    # Choose a b in [lo, hi] with b % k == target_mod.
    candidates = [v for v in range(lo, hi + 1) if v % k == target_mod]
    if candidates:
        b = rng.choice(candidates)
    else:
        b = target_mod  # fallback
    numerator_value = a * answer + b
    c_val = numerator_value // k

    steps: list[Step] = []
    idx = 0
    # Keep the initial in unevaluated form so the fraction is visible.
    num = sp.Add(a * x, sp.Integer(b), evaluate=False)
    initial_lhs = sp.Mul(num, sp.Pow(sp.Integer(k), -1, evaluate=False),
                         evaluate=False)
    steps.append(Step(idx, Eq(initial_lhs, sp.Integer(c_val), evaluate=False),
                      OperationType.INITIAL, note="initial fractional equation"))
    idx += 1
    # Multiply both sides by k.
    steps.append(Step(idx, Eq(a * x + b, k * c_val),
                      OperationType.MULTIPLY_BOTH_SIDES,
                      note=f"multiply both sides by {k}"))
    idx += 1
    if b != 0:
        steps.append(Step(idx, Eq(a * x, k * c_val - b),
                          OperationType.TRANSPOSE,
                          note=f"subtract {b} from both sides"))
        idx += 1
    if a != 1:
        rhs = sp.Rational(k * c_val - b, a)
        steps.append(Step(idx, Eq(x, rhs), OperationType.DIVIDE_BOTH_SIDES,
                          note=f"divide both sides by {a}"))
        idx += 1
    steps.append(Step(idx, Eq(x, sp.Integer(answer)), OperationType.FINAL,
                      note="solution"))

    return Solution(
        problem_type=ProblemType.LINEAR_FRACTION,
        variables=[x],
        steps=steps,
        final_answer=sp.Integer(answer),
    )


# ---------------------------------------------------------------------------
# Perfect-square quadratic: (x + a)^2 = b
# ---------------------------------------------------------------------------

def gen_quadratic_perfect_square(difficulty: int = 2,
                                 seed: Optional[int] = None) -> Solution:
    """Generate (x + a)^2 = b with b a perfect square so roots are integer.

    Steps:
      0. INITIAL:     (x + a)^2 = b
      1. EXPAND:      x^2 + 2ax + a^2 = b
      2. TRANSPOSE:   x^2 + 2ax + (a^2 - b) = 0
      3. FACTOR:      (x - r1)(x - r2) = 0
      4-5. FINAL:     x = r1, r2
    """
    rng = random.Random(seed)
    lo, hi = _coef_range(difficulty)
    a_val = rng.randint(lo, hi)
    sqrt_b = _nonzero_int(1, max(2, hi // 2), rng)
    b_val = sqrt_b * sqrt_b

    steps: list[Step] = []
    idx = 0
    initial_lhs = sp.Pow(sp.Add(x, sp.Integer(a_val), evaluate=False),
                         2, evaluate=False)
    steps.append(Step(idx, Eq(initial_lhs, sp.Integer(b_val), evaluate=False),
                      OperationType.INITIAL, note="initial (x+a)^2 = b"))
    idx += 1
    # Expanded form
    steps.append(Step(idx,
                      Eq(x ** 2 + 2 * a_val * x + a_val ** 2, b_val),
                      OperationType.EXPAND,
                      note=f"expand (x + {a_val})^2"))
    idx += 1
    # Transposed to = 0
    steps.append(Step(idx,
                      Eq(x ** 2 + 2 * a_val * x + (a_val ** 2 - b_val), 0),
                      OperationType.TRANSPOSE,
                      note=f"subtract {b_val} from both sides"))
    idx += 1
    # Factor (x - r1)(x - r2) where r1, r2 = -a ± sqrt(b)
    r1 = -a_val + sqrt_b
    r2 = -a_val - sqrt_b
    steps.append(Step(idx, Eq((x - r1) * (x - r2), 0),
                      OperationType.FACTOR,
                      note=f"factor"))
    idx += 1
    steps.append(Step(idx, Eq(x, sp.Integer(r1)), OperationType.FINAL,
                      note="one root"))
    idx += 1
    steps.append(Step(idx, Eq(x, sp.Integer(r2)), OperationType.FINAL,
                      note="other root"))

    return Solution(
        problem_type=ProblemType.QUADRATIC_PERFECT_SQUARE,
        variables=[x],
        steps=steps,
        final_answer=sp.FiniteSet(sp.Integer(r1), sp.Integer(r2)),
    )


GENERATORS[ProblemType.LINEAR_FRACTION] = gen_linear_fraction
GENERATORS[ProblemType.QUADRATIC_PERFECT_SQUARE] = gen_quadratic_perfect_square
