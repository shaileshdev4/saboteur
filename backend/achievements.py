"""Achievements -predicates over session CalibrationState dicts.

Unlocked set is derived on each /grade; newly unlocked IDs are returned in
GradeOut. The frontend tracks which toasts were already shown via localStorage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str
    predicate: Callable[[dict], bool]
    tier: str = "bronze"


def _counts(state: dict) -> dict:
    return state.get("counts", {})


def _domains_played(state: dict, min_rounds: int = 1) -> int:
    return len([
        d for d in state.get("per_domain", {}).values()
        if d.get("counts", {}).get("total", 0) >= min_rounds
    ])


ACHIEVEMENTS: list[Achievement] = [
    Achievement(
        id="first_catch",
        name="First Catch",
        description="Caught your first sabotaged step.",
        icon="target",
        tier="bronze",
        predicate=lambda s: _counts(s).get("correct_catch", 0) >= 1,
    ),
    Achievement(
        id="ten_rounds",
        name="Warmed Up",
        description="Played 10 rounds.",
        icon="activity",
        tier="bronze",
        predicate=lambda s: _counts(s).get("total", 0) >= 10,
    ),
    Achievement(
        id="fifty_rounds",
        name="Persistent",
        description="Played 50 rounds.",
        icon="zap",
        tier="silver",
        predicate=lambda s: _counts(s).get("total", 0) >= 50,
    ),
    Achievement(
        id="no_over_trust_streak_10",
        name="Vigilant",
        description="10 rounds without a single over-trust.",
        icon="shield",
        tier="silver",
        predicate=lambda s: (
            _counts(s).get("total", 0) >= 10
            and _counts(s).get("over_trust", 0) == 0
        ),
    ),
    Achievement(
        id="score_80",
        name="Well-Calibrated",
        description="Reached calibration score 80.",
        icon="chart",
        tier="silver",
        predicate=lambda s: s.get("score", 0) >= 80,
    ),
    Achievement(
        id="score_95",
        name="Sharp",
        description="Reached calibration score 95.",
        icon="award",
        tier="gold",
        predicate=lambda s: s.get("score", 0) >= 95,
    ),
    Achievement(
        id="four_domains",
        name="Polymath",
        description="Played rounds in all four domains.",
        icon="brain",
        tier="silver",
        predicate=lambda s: _domains_played(s) >= 4,
    ),
    Achievement(
        id="rating_1300",
        name="Rated 1300",
        description="Elo rating crossed 1300.",
        icon="star",
        tier="gold",
        predicate=lambda s: s.get("rating", 1000) >= 1300,
    ),
    Achievement(
        id="all_domains_score_70",
        name="Four-Way Calibrated",
        description="Hit score 70+ in every domain (3+ rounds each).",
        icon="trophy",
        tier="gold",
        predicate=lambda s: (
            len(s.get("per_domain", {})) >= 4
            and all(
                d.get("score", 0) >= 70
                for d in s.get("per_domain", {}).values()
                if d.get("counts", {}).get("total", 0) >= 3
            )
            and sum(
                1 for d in s.get("per_domain", {}).values()
                if d.get("counts", {}).get("total", 0) >= 3
            ) >= 4
        ),
    ),
    Achievement(
        id="catch_all_misconceptions_once",
        name="Encyclopedist",
        description="Caught at least one of 20+ algebra misconceptions.",
        icon="book",
        tier="gold",
        predicate=lambda s: sum(
            1 for v in s.get("per_misconception", {}).values()
            if v.get("caught", 0) >= 1
        ) >= 20,
    ),
]


def evaluate(state: dict) -> list[dict]:
    """Return achievement dicts currently unlocked for this state."""
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "tier": a.tier,
        }
        for a in ACHIEVEMENTS
        if a.predicate(state)
    ]
