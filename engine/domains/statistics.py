"""Statistics domain -mean, median, variance, basic probability, expected value."""
from __future__ import annotations

import random
from typing import Any, Optional

import sympy as sp

from ..domain import Domain, ProblemKind, register_domain
from ..misconceptions.base import Misconception
from ..types import OperationType, ProblemType, Solution, Step

EPS = sp.Rational(1, 10000)


def _data_marker(values: list[int]) -> sp.Symbol:
    return sp.Symbol(f"data({','.join(map(str, values))})")


def gen_mean(difficulty: int = 1, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    n = 4 + min(difficulty, 3)
    data = [rng.randint(2, 12) for _ in range(n)]
    total = sum(data)
    mean_val = sp.Rational(total, n)
    x_bar = sp.Symbol("x_bar", positive=True)
    S = sp.Symbol("S", positive=True)

    steps = [
        Step(0, sp.Eq(_data_marker(data), sp.Symbol("list")),
             OperationType.INITIAL,
             note=f"find the mean of {data}"),
        Step(1, sp.Eq(S, sp.Integer(total)),
             OperationType.SIMPLIFY, note="add the values"),
        Step(2, sp.Eq(x_bar, sp.Rational(total, n, evaluate=False)),
             OperationType.DIVIDE_BOTH_SIDES, note="divide by n"),
        Step(3, sp.Eq(x_bar, mean_val),
             OperationType.FINAL, note=f"mean = {float(mean_val):.2f}"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[x_bar],
        steps=steps,
        final_answer=mean_val,
    )


def gen_median(difficulty: int = 1, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    n = 5 + (difficulty % 2) * 2  # odd count
    data = sorted(rng.randint(1, 20) for _ in range(n))
    mid_idx = n // 2
    median_val = sp.Integer(data[mid_idx])
    med = sp.Symbol("median", positive=True)
    sorted_sym = sp.Symbol(f"sorted({','.join(map(str, data))})")

    steps = [
        Step(0, sp.Eq(_data_marker(data), sp.Symbol("list")),
             OperationType.INITIAL, note=f"find the median of {data}"),
        Step(1, sp.Eq(sorted_sym, sp.Symbol("sorted")),
             OperationType.SIMPLIFY, note="sort the data"),
        Step(2, sp.Eq(med, sp.Integer(data[mid_idx]),
                      evaluate=False),
             OperationType.SIMPLIFY,
             note=f"middle value (position {mid_idx + 1} of {n})"),
        Step(3, sp.Eq(med, median_val),
             OperationType.FINAL, note=f"median = {data[mid_idx]}"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[med],
        steps=steps,
        final_answer=median_val,
    )


def gen_variance(difficulty: int = 2, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    data = [rng.randint(2, 10) for _ in range(4)]
    n = len(data)
    mean_r = sp.Rational(sum(data), n)
    sq_sum = sum((sp.Integer(x) - mean_r) ** 2 for x in data)
    var_exact = sp.simplify(sq_sum / n)

    var_sym = sp.Symbol("s2", positive=True)
    mean_sym = sp.Symbol("x_bar", positive=True)
    ssq = sp.Symbol("SS", positive=True)
    sq_int = int(sum((x - float(mean_r)) ** 2 for x in data))

    steps = [
        Step(0, sp.Eq(_data_marker(data), sp.Symbol("list")),
             OperationType.INITIAL,
             note=f"sample variance of {data}"),
        Step(1, sp.Eq(mean_sym, mean_r),
             OperationType.SIMPLIFY, note="compute mean"),
        Step(2, sp.Eq(ssq, sp.Integer(sq_int)),
             OperationType.SIMPLIFY,
             note="sum of squared deviations"),
        Step(3, sp.Eq(var_sym, sp.Rational(sq_int, n, evaluate=False)),
             OperationType.DIVIDE_BOTH_SIDES, note="divide by n"),
        Step(4, sp.Eq(var_sym, var_exact),
             OperationType.FINAL, note="sample variance"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[var_sym],
        steps=steps,
        final_answer=var_exact,
    )


def gen_probability_basic(difficulty: int = 1, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    p_a = rng.choice([sp.Rational(1, 4), sp.Rational(1, 3), sp.Rational(2, 5)])
    p_b = rng.choice([sp.Rational(1, 5), sp.Rational(1, 4), sp.Rational(3, 10)])
    p_and = sp.simplify(p_a * p_b)
    P = sp.Symbol("P", positive=True)
    Pa = sp.Symbol("P_A", positive=True)
    Pb = sp.Symbol("P_B", positive=True)

    steps = [
        Step(0, sp.Eq(sp.Symbol("events"), sp.Symbol("A_and_B_independent")),
             OperationType.INITIAL,
             note="A and B are independent"),
        Step(1, sp.Eq(Pa, p_a), OperationType.SIMPLIFY, note="P(A)"),
        Step(2, sp.Eq(Pb, p_b), OperationType.SIMPLIFY, note="P(B)"),
        Step(3, sp.Eq(P, sp.Mul(Pa, Pb, evaluate=False)),
             OperationType.MULTIPLY_BOTH_SIDES,
             note="P(A and B) = P(A) * P(B)"),
        Step(4, sp.Eq(P, p_and),
             OperationType.FINAL, note="multiply probabilities"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[P],
        steps=steps,
        final_answer=p_and,
    )


def gen_expected_value(difficulty: int = 2, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    xs = [rng.randint(1, 6) for _ in range(3)]
    ps = [sp.Rational(rng.randint(1, 4), 10) for _ in range(3)]
    # Normalize probabilities to sum to 1
    total_p = sum(float(p) for p in ps)
    ps = [sp.Rational(int(round(float(p) / total_p * 100)), 100) for p in ps]
    ev_terms = [sp.Mul(sp.Integer(x), p, evaluate=False) for x, p in zip(xs, ps)]
    ev = sp.simplify(sum(x * p for x, p in zip(xs, ps)))
    EX = sp.Symbol("E_X", positive=True)

    steps = [
        Step(0, sp.Eq(sp.Symbol("X_dist"),
                      sp.Symbol(f"X in {xs}, p in {[float(p) for p in ps]}")),
             OperationType.INITIAL,
             note="discrete random variable X"),
        Step(1, sp.Eq(EX, sp.Add(*ev_terms, evaluate=False)),
             OperationType.SIMPLIFY,
             note="E[X] = sum x * P(x)"),
        Step(2, sp.Eq(EX, ev),
             OperationType.FINAL, note="expected value"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[EX],
        steps=steps,
        final_answer=ev,
    )


_GENERATORS = {
    "stat_mean": gen_mean,
    "stat_median": gen_median,
    "stat_variance": gen_variance,
    "stat_probability_basic": gen_probability_basic,
    "stat_expected_value": gen_expected_value,
}

_KINDS = [
    ProblemKind("stat_mean", "Arithmetic mean", (1, 4)),
    ProblemKind("stat_median", "Median", (1, 4)),
    ProblemKind("stat_variance", "Sample variance", (2, 5)),
    ProblemKind("stat_probability_basic", "Independent events P(A∩B)", (1, 4)),
    ProblemKind("stat_expected_value", "Expected value E[X]", (2, 5)),
]


class MeanDividesByNMinus1(Misconception):
    id = "mean_divides_by_n_minus_1"
    name = "Mean uses n−1 denominator"
    description = "Uses the sample standard-deviation divisor (n−1) when computing the mean."
    category = "statistics_mean"
    difficulty = 2
    applicable_ops = (OperationType.DIVIDE_BOTH_SIDES, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        return expr.lhs.name == "x_bar" and isinstance(expr.rhs, sp.Rational)

    def apply(self, step, solution, step_index):
        expr = step.expression
        r = expr.rhs
        if isinstance(r, sp.Rational) and r.q > 1:
            buggy = sp.Rational(r.p, max(1, r.q - 1))
            return Step(step.index, sp.Eq(expr.lhs, buggy),
                        step.operation, note=f"sabotage:{self.id}")
        return step


class MedianPositionOffByOne(Misconception):
    id = "median_position_off_by_one"
    name = "Median index off by one"
    description = "Picks the wrong sorted position (1-indexed vs 0-indexed confusion)."
    category = "statistics_median"
    difficulty = 2
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        return isinstance(expr, sp.Equality) and expr.lhs.name == "median"

    def apply(self, step, solution, step_index):
        initial = solution.steps[0].expression
        rhs_str = str(initial.lhs)
        if not rhs_str.startswith("data("):
            return step
        inner = rhs_str[5:-1]
        if not inner:
            return step
        data = [int(x) for x in inner.split(",")]
        data_sorted = sorted(data)
        n = len(data_sorted)
        wrong_idx = max(0, (n // 2) - 1) if n > 1 else 0
        buggy = sp.Integer(data_sorted[wrong_idx])
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


class VarianceNoSquaring(Misconception):
    id = "variance_no_squaring"
    name = "Variance without squaring deviations"
    description = "Sums raw deviations instead of squared deviations."
    category = "statistics_variance"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY,)

    def applies_to(self, step, solution, step_index):
        if step.operation != OperationType.SIMPLIFY:
            return False
        expr = step.expression
        return isinstance(expr, sp.Equality) and expr.lhs.name == "SS"

    def apply(self, step, solution, step_index):
        initial = solution.steps[0].expression
        rhs_str = str(initial.lhs)
        if not rhs_str.startswith("data("):
            return step
        data = [int(x) for x in rhs_str[5:-1].split(",")]
        mean_f = sum(data) / len(data)
        unsquared = int(sum(abs(x - mean_f) for x in data))
        return Step(step.index, sp.Eq(step.expression.lhs, sp.Integer(unsquared)),
                    step.operation, note=f"sabotage:{self.id}")


class ProbabilityAddedNotMultiplied(Misconception):
    id = "probability_added_not_multiplied"
    name = "P(A∩B) = P(A) + P(B)"
    description = "Adds independent probabilities instead of multiplying."
    category = "statistics_probability"
    difficulty = 2
    applicable_ops = (OperationType.MULTIPLY_BOTH_SIDES, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        return isinstance(expr, sp.Equality) and expr.lhs.name == "P"

    def apply(self, step, solution, step_index):
        pa = solution.steps[1].expression.rhs
        pb = solution.steps[2].expression.rhs
        try:
            buggy = sp.simplify(pa + pb)
        except Exception:
            return step
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


class ProbabilityComplementWrong(Misconception):
    """P(not A) = 1 + P(A) on a single-event complement step."""
    id = "probability_complement_wrong"
    name = "Complement as 1 + P(A)"
    description = "Computes P(not A) as 1 + P(A) instead of 1 − P(A)."
    category = "statistics_probability"
    difficulty = 3
    applicable_ops = (OperationType.SIMPLIFY, OperationType.FINAL)

    def applies_to(self, step, solution, step_index):
        if step.operation not in self.applicable_ops:
            return False
        expr = step.expression
        if not isinstance(expr, sp.Equality):
            return False
        return expr.lhs.name in ("P_not_A", "P_compl")

    def apply(self, step, solution, step_index):
        pa = solution.steps[1].expression.rhs
        try:
            buggy = sp.simplify(1 + pa)
        except Exception:
            buggy = sp.Integer(1) + pa
        return Step(step.index, sp.Eq(step.expression.lhs, buggy),
                    step.operation, note=f"sabotage:{self.id}")


# Replace unused stub with complement generator hook
def gen_complement(difficulty: int = 1, seed: Optional[int] = None) -> Solution:
    rng = random.Random(seed)
    p_a = rng.choice([sp.Rational(1, 4), sp.Rational(2, 5), sp.Rational(3, 10)])
    p_not = sp.simplify(1 - p_a)
    Pa = sp.Symbol("P_A", positive=True)
    Pn = sp.Symbol("P_not_A", positive=True)

    steps = [
        Step(0, sp.Eq(sp.Symbol("event"), sp.Symbol("complement")),
             OperationType.INITIAL, note="A and not-A partition the sample space"),
        Step(1, sp.Eq(Pa, p_a), OperationType.SIMPLIFY, note="P(A)"),
        Step(2, sp.Eq(Pn, sp.Add(1, Pa, evaluate=False)),
             OperationType.SIMPLIFY, note="P(not A) = 1 - P(A)"),
        Step(3, sp.Eq(Pn, p_not),
             OperationType.FINAL, note="complement probability"),
    ]
    return Solution(
        problem_type=ProblemType.LINEAR_ONE_VAR,
        variables=[Pn],
        steps=steps,
        final_answer=p_not,
    )


_GENERATORS["stat_complement"] = gen_complement
_KINDS.append(ProblemKind("stat_complement", "Complement P(not A)", (1, 4)))

_STATS_MISCONCEPTIONS = [
    MeanDividesByNMinus1(),
    MedianPositionOffByOne(),
    VarianceNoSquaring(),
    ProbabilityAddedNotMultiplied(),
    ProbabilityComplementWrong(),
]


class StatisticsDomain(Domain):
    id = "statistics"
    label = "Statistics"
    description = "Mean, median, variance, probability, and expected value."

    def problem_kinds(self) -> list[ProblemKind]:
        return _KINDS

    def generate(self, kind_id: str, difficulty: int = 1,
                 seed: Optional[int] = None) -> Solution:
        if kind_id not in _GENERATORS:
            raise KeyError(f"Unknown statistics kind: {kind_id}")
        return _GENERATORS[kind_id](difficulty=difficulty, seed=seed)

    def misconceptions(self):
        return _STATS_MISCONCEPTIONS

    def states_equivalent(self, a: Any, b: Any) -> bool:
        if not (isinstance(a, sp.Equality) and isinstance(b, sp.Equality)):
            return False
        if str(a.lhs) != str(b.lhs):
            return False
        try:
            diff_expr = sp.simplify(a.rhs - b.rhs)
            if diff_expr == 0:
                return True
            return abs(float(diff_expr)) < float(EPS)
        except (TypeError, ValueError):
            return False


register_domain(StatisticsDomain())
