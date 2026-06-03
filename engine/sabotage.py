"""The sabotage engine.

Takes a canonical Solution and either:
  - Returns it unchanged (clean), OR
  - Picks a misconception whose predicate matches some step, applies it at
    that step, and returns the corrupted Solution alongside a SabotageRecord
    that records the truth.

Design rules:
- Exactly one step is corrupted.
- The corruption is at a *known* step index; the player has to find it.
- We propagate the corrupted state forward by replacing only that one step
  in the displayed solution; subsequent steps are STILL the canonical ones.
  This matches how a real solution would look if someone made one mistake
  at step k and then continued doing the *correct* operation from a wrong
  starting point -the propagated error would appear as a chain. But for
  v1 we keep it simple: only one displayed step differs from canonical.
  (Phase 2 can add full propagation.)
"""
from __future__ import annotations

import random
from typing import Optional

from .misconceptions import all_misconceptions
from .types import SabotageRecord, Solution, Step


def sabotage(solution: Solution,
             corrupt_probability: float = 0.5,
             seed: Optional[int] = None,
             difficulty_range: tuple[int, int] = (1, 5),
             ) -> SabotageRecord:
    """Possibly inject one misconception. Returns a full record."""
    rng = random.Random(seed)
    do_corrupt = rng.random() < corrupt_probability

    if not do_corrupt:
        return SabotageRecord(
            is_clean=True,
            truth=solution,
            displayed=solution,
        )

    # Gather (misconception, step_index) pairs that are applicable.
    candidates = []
    for mis in all_misconceptions():
        if not (difficulty_range[0] <= mis.difficulty <= difficulty_range[1]):
            continue
        for i, step in enumerate(solution.steps):
            if i == 0:
                continue   # never corrupt the problem statement itself
            try:
                if mis.applies_to(step, solution, i):
                    candidates.append((mis, i))
            except Exception:
                continue

    if not candidates:
        # No misconception applies -fall back to clean.
        return SabotageRecord(
            is_clean=True,
            truth=solution,
            displayed=solution,
        )

    # Shuffle and try candidates until one actually produces an inequivalent
    # step. This is the safety net -if a misconception silently no-ops we
    # don't want to return it as a "corrupted" round, because the player would
    # be looking for a non-existent error.
    from .verifier import states_equivalent
    rng.shuffle(candidates)
    for mis, idx in candidates:
        target_step = solution.steps[idx]
        try:
            corrupted_step = mis.apply(target_step, solution, idx)
        except Exception:
            continue
        if states_equivalent(corrupted_step.expression, target_step.expression):
            continue  # no-op; try another candidate
        new_steps = list(solution.steps)
        new_steps[idx] = corrupted_step
        displayed = Solution(
            problem_type=solution.problem_type,
            variables=solution.variables,
            steps=new_steps,
            final_answer=solution.final_answer,
        )
        return SabotageRecord(
            is_clean=False,
            corrupted_step_index=idx,
            misconception_id=mis.id,
            truth=solution,
            displayed=displayed,
        )

    # Every candidate no-opped. Fall back to clean.
    return SabotageRecord(
        is_clean=True,
        truth=solution,
        displayed=solution,
    )
