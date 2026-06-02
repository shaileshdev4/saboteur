"""Hint system.

Players can request graduated hints during a round, at a points cost. The
hints reveal progressively more about where the error is without giving away
the answer.

Hint tiers (each successive hint costs more, and is only available after the
previous):
  1. "Something's off"           — confirms the solution contains an error.
                                     Cost: 1 point.
                                     Free info: NONE (just confirms is_clean=False).
  2. "Narrow it to a region"     — reveals which third of the steps the error is in.
                                     Cost: 2 points.
  3. "Check the technique used"  — reveals the misconception's category.
                                     Cost: 3 points.

If is_clean (no error exists), tier-1 honestly says "no error" and tier 2/3
are unavailable.

A hint is recorded on the round; the player can request up to 3 (one per
tier, ascending). The grader subtracts the cumulative hint cost from points
when the round is graded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


HINT_COSTS = {1: 1, 2: 2, 3: 3}
MAX_HINT_TIER = 3


@dataclass
class HintRequest:
    round_id: str
    tier: int


@dataclass
class HintResponse:
    tier: int
    message: str
    cost: int                  # this tier's cost
    cumulative_cost: int       # total cost of all hints used this round
    is_terminal: bool = False  # true if no more hints available


def build_hint(tier: int, record, prior_tier: int = 0) -> HintResponse:
    """Produce the hint text for a tier given the SabotageRecord.

    `record` has fields is_clean, corrupted_step_index, misconception_id,
    displayed.steps (list).
    """
    if tier not in HINT_COSTS:
        raise ValueError(f"Invalid hint tier: {tier}")
    if tier <= prior_tier:
        raise ValueError(f"Already used hint tier {prior_tier}; cannot reuse")

    cost = HINT_COSTS[tier]
    cumulative_cost = sum(HINT_COSTS[t] for t in range(1, tier + 1))

    if tier == 1:
        if record.is_clean:
            msg = ("No error to find — this solution is clean. "
                   "(Hint locked further; trust the work.)")
            return HintResponse(tier=1, message=msg, cost=cost,
                                cumulative_cost=cumulative_cost,
                                is_terminal=True)
        msg = ("There IS an error here. Look carefully at each step's "
               "arithmetic and signs.")
        return HintResponse(tier=1, message=msg, cost=cost,
                            cumulative_cost=cumulative_cost)

    if record.is_clean:
        # Shouldn't reach here if tier-1 was terminal, but be safe.
        return HintResponse(tier=tier, message="No further hint available.",
                            cost=0, cumulative_cost=cumulative_cost,
                            is_terminal=True)

    if tier == 2:
        # Reveal which third of the steps contains the error.
        n = len(record.displayed.steps)
        idx = record.corrupted_step_index
        third = (idx - 1) // max(1, (n - 1) // 3)  # 0, 1, or 2
        region_labels = ["the first third", "the middle third", "the last third"]
        region = region_labels[min(third, 2)]
        msg = f"The error is somewhere in {region} of the steps."
        return HintResponse(tier=2, message=msg, cost=cost,
                            cumulative_cost=cumulative_cost)

    # tier == 3: reveal misconception category
    from .misconceptions import get_misconception
    try:
        mis = get_misconception(record.misconception_id)
        cat = mis.category.replace("_", " ")
        msg = f"The error involves: {cat}. Look for that pattern."
    except KeyError:
        # Calculus/geometry misconceptions aren't in the global registry; use
        # the record's stored misconception_id and trust the category prefix.
        mid = record.misconception_id or ""
        if mid.startswith("calc_") or "_calc_" in mid:
            msg = "The error is a calculus rule application slip."
        elif mid.startswith("geom_") or "_geom_" in mid:
            msg = "The error involves a geometry formula or substitution."
        else:
            msg = "The error involves an arithmetic or distribution slip."
    return HintResponse(tier=3, message=msg, cost=cost,
                        cumulative_cost=cumulative_cost, is_terminal=True)
