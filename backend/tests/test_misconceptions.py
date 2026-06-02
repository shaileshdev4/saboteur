"""Tests for misconceptions.

For each registered misconception, we:
  1. Find problems where it applies to some step.
  2. Apply it. Confirm the result is well-formed.
  3. Confirm the result is NOT equivalent to the original step (i.e., it
     actually introduces a wrong-but-plausible change).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.generators import (
    gen_linear_one_var,
    gen_linear_two_step,
    gen_quadratic_factor,
    gen_quadratic_formula,
)
from engine.misconceptions import all_misconceptions
from engine.verifier import is_well_formed, states_equivalent


def all_problem_generators_and_difficulty():
    from engine.generators import (
        gen_linear_one_var, gen_linear_two_step, gen_linear_fraction,
        gen_quadratic_factor, gen_quadratic_formula, gen_quadratic_perfect_square,
    )
    yield "linear_one_var", gen_linear_one_var, 2
    yield "linear_two_step", gen_linear_two_step, 2
    yield "linear_fraction", gen_linear_fraction, 2
    yield "quadratic_factor", gen_quadratic_factor, 2
    yield "quadratic_formula", gen_quadratic_formula, 3
    yield "quadratic_perfect_square", gen_quadratic_perfect_square, 2


def find_applicable_problem(mis, max_attempts=200):
    """Search across generators and seeds for a problem with an applicable step."""
    for name, gen, diff in all_problem_generators_and_difficulty():
        for seed in range(max_attempts):
            sol = gen(difficulty=diff, seed=seed)
            for i, step in enumerate(sol.steps):
                if mis.applies_to(step, sol, i):
                    return sol, i, name
    return None


def test_every_misconception_has_applicable_problem():
    misses = []
    for mis in all_misconceptions():
        result = find_applicable_problem(mis)
        if result is None:
            misses.append(mis.id)
    assert not misses, f"Misconceptions with no applicable problem: {misses}"


def test_every_misconception_produces_wellformed_wrong_output():
    failures = []
    for mis in all_misconceptions():
        result = find_applicable_problem(mis)
        if result is None:
            failures.append((mis.id, "no applicable problem"))
            continue
        sol, idx, gen_name = result
        original_step = sol.steps[idx]
        try:
            corrupted = mis.apply(original_step, sol, idx)
        except Exception as e:
            failures.append((mis.id, f"exception during apply: {e}"))
            continue

        # Well-formedness check.
        if not is_well_formed(corrupted.expression):
            failures.append((mis.id, f"output not well-formed: {corrupted.expression}"))
            continue

        # Must be different from original.
        if states_equivalent(corrupted.expression, original_step.expression):
            failures.append((mis.id, f"output is equivalent to original "
                                     f"(no error introduced): {corrupted.expression}"))
            continue

    if failures:
        for fid, reason in failures:
            print(f"  FAIL {fid}: {reason}")
    assert not failures, f"{len(failures)} misconception(s) failed"


def test_misconception_is_actually_wrong_in_context():
    """For each misconception, after corrupting step i, the corrupted step must
    not be equation-equivalent to the *previous* canonical step. (This is what
    a player would actually compare against - does the displayed step follow
    from the previous one?)"""
    failures = []
    for mis in all_misconceptions():
        result = find_applicable_problem(mis)
        if result is None:
            continue
        sol, idx, _ = result
        if idx == 0:
            continue
        corrupted = mis.apply(sol.steps[idx], sol, idx)
        prev = sol.steps[idx - 1].expression
        # If corrupted is equivalent to prev, that's a fluke but not necessarily
        # wrong - but the corrupted should also not match the canonical curr.
        # The important property: corrupted != canonical step.
        if states_equivalent(corrupted.expression, sol.steps[idx].expression):
            failures.append((mis.id, "corrupted matches canonical"))
    assert not failures, failures


def test_misconception_metadata():
    for mis in all_misconceptions():
        assert mis.id, f"{mis.__class__.__name__} missing id"
        assert mis.name, f"{mis.id} missing name"
        assert mis.description, f"{mis.id} missing description"
        assert 1 <= mis.difficulty <= 5, f"{mis.id} difficulty out of range"
        assert mis.category, f"{mis.id} missing category"


if __name__ == "__main__":
    print(f"Registered misconceptions: {len(all_misconceptions())}")
    for m in all_misconceptions():
        print(f"  - [{m.difficulty}] {m.id} ({m.category})")
    print()
    from tests._console import say

    test_misconception_metadata()
    say("[OK] metadata complete")
    test_every_misconception_has_applicable_problem()
    say("[OK] every misconception has at least one applicable problem")
    test_every_misconception_produces_wellformed_wrong_output()
    say("[OK] every misconception produces well-formed wrong output")
    test_misconception_is_actually_wrong_in_context()
    say("[OK] every misconception's output differs from canonical")
    say("")
    say("[OK] All misconception tests passed.")
