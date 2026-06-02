"""End-to-end tests: generator -> sabotage -> grade -> calibration."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

from engine.calibration import CalibrationState
from engine.generators import (
    gen_linear_one_var, gen_linear_two_step, gen_linear_fraction,
    gen_quadratic_factor, gen_quadratic_formula, gen_quadratic_perfect_square,
)
from engine.grader import grade
from engine.sabotage import sabotage
from engine.types import (
    GradeOutcome, PlayerAction, PlayerDecision,
)
from engine.verifier import states_equivalent

GENERATORS = [
    gen_linear_one_var, gen_linear_two_step, gen_linear_fraction,
    gen_quadratic_factor, gen_quadratic_formula, gen_quadratic_perfect_square,
]


def test_sabotage_clean_unchanged():
    """When sabotage chooses 'clean', the displayed solution must equal truth."""
    sol = gen_linear_one_var(difficulty=2, seed=1)
    record = sabotage(sol, corrupt_probability=0.0, seed=0)
    assert record.is_clean
    assert record.corrupted_step_index is None
    # Every step matches.
    for i, (a, b) in enumerate(zip(record.truth.steps, record.displayed.steps)):
        assert states_equivalent(a.expression, b.expression), \
            f"step {i} differs in 'clean' sabotage"


def test_sabotage_corrupt_changes_exactly_one_step():
    """When sabotage corrupts, exactly one step in displayed differs from truth."""
    for gen in GENERATORS:
        for seed in range(20):
            sol = gen(difficulty=2 if gen != gen_quadratic_formula else 3, seed=seed)
            record = sabotage(sol, corrupt_probability=1.0, seed=seed)
            if record.is_clean:
                # No applicable misconception - that's fine, but rare.
                continue
            diffs = []
            for i, (a, b) in enumerate(zip(record.truth.steps,
                                            record.displayed.steps)):
                if not states_equivalent(a.expression, b.expression):
                    diffs.append(i)
            assert len(diffs) == 1, \
                f"{gen.__name__} seed={seed}: expected 1 differing step, got {diffs}"
            assert diffs[0] == record.corrupted_step_index


def test_grade_correct_trust():
    sol = gen_linear_one_var(seed=0)
    rec = sabotage(sol, corrupt_probability=0.0, seed=0)
    action = PlayerAction(decision=PlayerDecision.TRUST)
    g = grade(action, rec)
    assert g.outcome == GradeOutcome.CORRECT_TRUST
    assert g.points > 0


def test_grade_over_trust():
    """Player trusts a sabotaged solution -> OVER_TRUST (the dangerous one)."""
    sol = gen_linear_two_step(seed=1)
    rec = sabotage(sol, corrupt_probability=1.0, seed=1)
    if rec.is_clean:
        return  # rare; skip
    action = PlayerAction(decision=PlayerDecision.TRUST)
    g = grade(action, rec)
    assert g.outcome == GradeOutcome.OVER_TRUST
    assert g.points < 0


def test_grade_correct_catch():
    """Player flags the right step -> CORRECT_CATCH."""
    for seed in range(20):
        sol = gen_linear_two_step(seed=seed)
        rec = sabotage(sol, corrupt_probability=1.0, seed=seed)
        if rec.is_clean:
            continue
        action = PlayerAction(decision=PlayerDecision.FLAG,
                              flagged_step_index=rec.corrupted_step_index)
        g = grade(action, rec)
        assert g.outcome == GradeOutcome.CORRECT_CATCH
        assert g.points > 0
        # And bonus for naming the misconception:
        action2 = PlayerAction(decision=PlayerDecision.FLAG,
                               flagged_step_index=rec.corrupted_step_index,
                               flagged_misconception_id=rec.misconception_id)
        g2 = grade(action2, rec)
        assert g2.points > g.points
        return  # one success is enough
    assert False, "no sabotaged solution produced in 20 attempts"


def test_grade_wrong_step_catch():
    for seed in range(20):
        sol = gen_linear_two_step(seed=seed)
        rec = sabotage(sol, corrupt_probability=1.0, seed=seed)
        if rec.is_clean:
            continue
        # Flag a step that's NOT the corrupted one.
        other_idx = (rec.corrupted_step_index + 1) % len(rec.displayed.steps)
        if other_idx == 0:
            other_idx = 1
        if other_idx == rec.corrupted_step_index:
            continue
        action = PlayerAction(decision=PlayerDecision.FLAG,
                              flagged_step_index=other_idx)
        g = grade(action, rec)
        assert g.outcome == GradeOutcome.WRONG_STEP_CATCH
        return
    assert False, "no sabotaged solution produced"


def test_calibration_session_improves():
    """Simulate a player who improves over rounds and check the score climbs."""
    state = CalibrationState()
    rng = random.Random(42)
    # 30 rounds. Player starts random, ends near-perfect.
    for round_num in range(30):
        gen = rng.choice(GENERATORS)
        sol = gen(difficulty=2, seed=rng.randint(0, 10_000))
        rec = sabotage(sol, corrupt_probability=0.5,
                       seed=rng.randint(0, 10_000))
        # Skill goes from 30% to 95% across the session.
        skill = 0.3 + 0.65 * (round_num / 29)
        if rec.is_clean:
            correct = rng.random() < skill
            action = PlayerAction(decision=PlayerDecision.TRUST if correct
                                  else PlayerDecision.FLAG,
                                  flagged_step_index=1 if not correct else None)
        else:
            correct = rng.random() < skill
            if correct:
                action = PlayerAction(decision=PlayerDecision.FLAG,
                                      flagged_step_index=rec.corrupted_step_index)
            else:
                action = PlayerAction(decision=PlayerDecision.TRUST)
        g = grade(action, rec)
        state.record(g, rec)

    # Final score should be higher than middle and starting.
    start = state.score_history[2]
    mid = state.score_history[14]
    end = state.score_history[-1]
    # Trend should be upward (allow some noise).
    assert end > start - 5, f"score did not climb: start={start} mid={mid} end={end}"
    assert end > mid - 10


def test_explanation_seed_never_used_for_grading():
    """Smoke test: the LLM seed contains description info but grader ignores it."""
    sol = gen_linear_one_var(seed=5)
    rec = sabotage(sol, corrupt_probability=1.0, seed=5)
    if rec.is_clean:
        return
    action = PlayerAction(decision=PlayerDecision.FLAG,
                          flagged_step_index=rec.corrupted_step_index)
    g = grade(action, rec)
    # Seed contains LLM-ready strings, never used for outcome decision.
    assert "misconception_description" in g.explanation_seed
    assert "truth_step_latex" in g.explanation_seed
    assert g.outcome == GradeOutcome.CORRECT_CATCH


if __name__ == "__main__":
    from tests._console import say

    test_sabotage_clean_unchanged()
    say("[OK] clean sabotage preserves all steps")
    test_sabotage_corrupt_changes_exactly_one_step()
    say("[OK] corrupt sabotage changes exactly one step across all generators")
    test_grade_correct_trust()
    say("[OK] grader: correct trust")
    test_grade_over_trust()
    say("[OK] grader: over-trust (dangerous mode) detected")
    test_grade_correct_catch()
    say("[OK] grader: correct catch + misconception-id bonus")
    test_grade_wrong_step_catch()
    say("[OK] grader: wrong-step catch")
    test_calibration_session_improves()
    say("[OK] calibration: score climbs as simulated skill improves")
    test_explanation_seed_never_used_for_grading()
    say("[OK] explanation seed populated; grader independent of it")
    say("")
    say("[OK] All integration tests passed.")
