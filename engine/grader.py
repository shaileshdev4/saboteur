"""Grader.

Deterministic. Given a SabotageRecord (truth) and a PlayerAction, returns
the Grade. Encodes the 2x2 outcome matrix from the project doc.

Scoring weights:
  CORRECT_CATCH  = +10  (+5 bonus if misconception id is also identified)
  CORRECT_TRUST  = +5
  OVER_TRUST     = -10  (the dangerous failure mode -weighted heaviest)
  OVER_SUSPICION = -5
  WRONG_STEP_CATCH = -2  (player suspected something, but wrong step)

Phase 1 extension: if the player used hints, the cumulative hint cost is
subtracted from the final points (but never makes a correct outcome go
NEGATIVE -a correct catch with hints is still worth a positive number,
just less).
"""
from __future__ import annotations

from .types import (
    Grade,
    GradeOutcome,
    PlayerAction,
    PlayerDecision,
    SabotageRecord,
)

POINTS = {
    GradeOutcome.CORRECT_CATCH: 10,
    GradeOutcome.CORRECT_TRUST: 5,
    GradeOutcome.OVER_TRUST: -10,
    GradeOutcome.OVER_SUSPICION: -5,
    GradeOutcome.WRONG_STEP_CATCH: -2,
}

BONUS_ID_CORRECT = 5


def grade(action: PlayerAction, record: SabotageRecord,
          hint_cost: int = 0) -> Grade:
    """Grade a round. `hint_cost` is subtracted from the final points."""
    if action.decision == PlayerDecision.TRUST:
        if record.is_clean:
            outcome = GradeOutcome.CORRECT_TRUST
            seed = {"is_clean": True}
        else:
            outcome = GradeOutcome.OVER_TRUST
            seed = _explanation_seed(record)
        points = _apply_hint_cost(POINTS[outcome], hint_cost, outcome)
        return Grade(outcome=outcome, points=points, explanation_seed=seed)

    # FLAG
    if action.flagged_step_index is None:
        outcome = GradeOutcome.OVER_SUSPICION if record.is_clean else GradeOutcome.WRONG_STEP_CATCH
        return Grade(outcome=outcome,
                     points=_apply_hint_cost(POINTS[outcome], hint_cost, outcome),
                     explanation_seed=_explanation_seed(record))

    if record.is_clean:
        outcome = GradeOutcome.OVER_SUSPICION
        return Grade(outcome=outcome,
                     points=_apply_hint_cost(POINTS[outcome], hint_cost, outcome),
                     explanation_seed={"is_clean": True,
                                       "flagged_step": action.flagged_step_index})

    if action.flagged_step_index == record.corrupted_step_index:
        outcome = GradeOutcome.CORRECT_CATCH
        points = POINTS[outcome]
        if (action.flagged_misconception_id
                and action.flagged_misconception_id == record.misconception_id):
            points += BONUS_ID_CORRECT
        points = _apply_hint_cost(points, hint_cost, outcome)
        return Grade(outcome=outcome, points=points,
                     explanation_seed=_explanation_seed(record))

    outcome = GradeOutcome.WRONG_STEP_CATCH
    return Grade(outcome=outcome,
                 points=_apply_hint_cost(POINTS[outcome], hint_cost, outcome),
                 explanation_seed=_explanation_seed(record))


def _apply_hint_cost(base_points: int, hint_cost: int,
                     outcome: GradeOutcome) -> int:
    """Subtract hint cost. Clamp so a correct outcome stays >= 1 point.

    Wrong outcomes can drop below their base -hints don't save you from a
    bad guess, but a correct catch with all hints used is still worth something.
    """
    raw = base_points - hint_cost
    if outcome in (GradeOutcome.CORRECT_CATCH, GradeOutcome.CORRECT_TRUST):
        return max(1, raw)
    return raw


def _explanation_seed(record: SabotageRecord) -> dict:
    """Info for the LLM explainer. NEVER used by the grader itself."""
    if record.is_clean:
        return {"is_clean": True}
    # Cross-domain lookup so calculus/geometry misconceptions resolve.
    try:
        from .domain import find_misconception_across_domains
        mis = find_misconception_across_domains(record.misconception_id)
    except (KeyError, ImportError):
        # Fallback: try the legacy algebra-only registry.
        from .misconceptions import get_misconception
        try:
            mis = get_misconception(record.misconception_id)
        except KeyError:
            return {
                "is_clean": False,
                "corrupted_step_index": record.corrupted_step_index,
                "misconception_id": record.misconception_id,
                "misconception_name": record.misconception_id or "Unknown",
                "misconception_description": "",
                "misconception_category": "",
                "misconception_difficulty": 3,
                "truth_step_latex": record.truth.steps[record.corrupted_step_index].latex() if record.corrupted_step_index is not None else "",
                "shown_step_latex": record.displayed.steps[record.corrupted_step_index].latex() if record.corrupted_step_index is not None else "",
            }
    truth_step = record.truth.steps[record.corrupted_step_index]
    shown_step = record.displayed.steps[record.corrupted_step_index]
    return {
        "is_clean": False,
        "corrupted_step_index": record.corrupted_step_index,
        "misconception_id": mis.id,
        "misconception_name": mis.name,
        "misconception_description": mis.description,
        "misconception_category": mis.category,
        "misconception_difficulty": mis.difficulty,
        "truth_step_latex": truth_step.latex(),
        "shown_step_latex": shown_step.latex(),
    }
