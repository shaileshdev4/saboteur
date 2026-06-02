"""Tests for the problem generators.

For each generator we run many seeds, and for each generated solution we:
  1. Verify every consecutive pair of steps using validate_solution
  2. Verify the final_answer actually solves the original problem
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp

from engine.generators import (
    gen_linear_one_var,
    gen_linear_two_step,
    gen_linear_fraction,
    gen_quadratic_factor,
    gen_quadratic_formula,
    gen_quadratic_perfect_square,
    validate_solution,
)
from engine.types import ProblemType


def _check_solution_solves_problem(sol):
    """The final_answer field should actually solve the initial equation."""
    initial = sol.steps[0].expression
    sym = sol.variables[0]
    real_solutions = sp.solve(initial, sym, dict=False)
    if isinstance(sol.final_answer, sp.FiniteSet):
        candidates = list(sol.final_answer)
    else:
        candidates = [sol.final_answer]
    for cand in candidates:
        assert any(sp.simplify(rs - cand) == 0 for rs in real_solutions), \
            f"final_answer {cand} does not solve {initial} (real: {real_solutions})"


def test_linear_one_var_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_linear_one_var(difficulty=2, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 linear_one_var solutions failed validation"


def test_linear_two_step_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_linear_two_step(difficulty=2, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 linear_two_step solutions failed validation"


def test_quadratic_factor_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_quadratic_factor(difficulty=2, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 quadratic_factor solutions failed validation"


def test_quadratic_formula_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_quadratic_formula(difficulty=3, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 quadratic_formula solutions failed validation"


def test_linear_fraction_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_linear_fraction(difficulty=2, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 linear_fraction solutions failed validation"


def test_quadratic_perfect_square_many_seeds():
    failures = 0
    for seed in range(50):
        sol = gen_quadratic_perfect_square(difficulty=2, seed=seed)
        ok, reason = validate_solution(sol)
        if not ok:
            failures += 1
            print(f"  seed={seed}: {reason}")
            continue
        _check_solution_solves_problem(sol)
    assert failures == 0, f"{failures}/50 quadratic_perfect_square solutions failed validation"


if __name__ == "__main__":
    from tests._console import say

    test_linear_one_var_many_seeds()
    say("[OK] linear_one_var: 50 seeds passed")
    test_linear_two_step_many_seeds()
    say("[OK] linear_two_step: 50 seeds passed")
    test_linear_fraction_many_seeds()
    say("[OK] linear_fraction: 50 seeds passed")
    test_quadratic_factor_many_seeds()
    say("[OK] quadratic_factor: 50 seeds passed")
    test_quadratic_formula_many_seeds()
    say("[OK] quadratic_formula: 50 seeds passed")
    test_quadratic_perfect_square_many_seeds()
    say("[OK] quadratic_perfect_square: 50 seeds passed")
    say("\n[OK] All generator tests passed across 300 problem instances.")
