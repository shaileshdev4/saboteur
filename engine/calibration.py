"""Calibration model.

Tracks the 2×2 outcome counts (correct trust, over-trust, correct catch,
over-suspicion, wrong-step catch) across a session and produces:
  - per-round score (the immediate grade)
  - running calibration score in [0, 100]
  - per-misconception strength (Elo-style rating)

Calibration score formula:
  score = 100 * (correct_decisions / total) - over_trust_penalty
where over-trust is weighted more heavily (research finding: it's the
dangerous failure mode).

The Elo update lets us auto-tune difficulty in Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .types import Grade, GradeOutcome, SabotageRecord


@dataclass
class OutcomeCounts:
    correct_trust: int = 0
    correct_catch: int = 0
    over_trust: int = 0
    over_suspicion: int = 0
    wrong_step_catch: int = 0

    @property
    def total(self) -> int:
        return (self.correct_trust + self.correct_catch + self.over_trust
                + self.over_suspicion + self.wrong_step_catch)

    @property
    def correct(self) -> int:
        return self.correct_trust + self.correct_catch

    def add(self, outcome: GradeOutcome) -> None:
        setattr(self, outcome.value, getattr(self, outcome.value) + 1)


@dataclass
class CalibrationState:
    counts: OutcomeCounts = field(default_factory=OutcomeCounts)
    score_history: list[float] = field(default_factory=list)
    point_history: list[int] = field(default_factory=list)
    # Per-misconception strength: how often the player catches each misconception.
    per_misconception: dict[str, dict] = field(default_factory=dict)
    # Player Elo-style rating for difficulty tuning. Starts at 1000.
    rating: float = 1000.0
    # Per-domain ratings + counts. Algebra calibration doesn't transfer to
    # geometry, so each domain has its own Elo/score curve.
    per_domain: dict[str, dict] = field(default_factory=dict)

    def record(self, grade: Grade, record: SabotageRecord,
               domain_id: str = "algebra") -> None:
        self.counts.add(grade.outcome)
        self.point_history.append(grade.points)
        self.score_history.append(self.calibration_score)
        if not record.is_clean:
            mid = record.misconception_id
            entry = self.per_misconception.setdefault(mid, {"seen": 0, "caught": 0})
            entry["seen"] += 1
            if grade.outcome == GradeOutcome.CORRECT_CATCH:
                entry["caught"] += 1

        # Per-domain tracking.
        dstate = self.per_domain.setdefault(domain_id, {
            "counts": {"correct_trust": 0, "correct_catch": 0,
                       "over_trust": 0, "over_suspicion": 0,
                       "wrong_step_catch": 0, "total": 0},
            "rating": 1000.0,
            "score_history": [],
            "point_history": [],
        })
        dstate["counts"][grade.outcome.value] = dstate["counts"].get(
            grade.outcome.value, 0) + 1
        dstate["counts"]["total"] = dstate["counts"].get("total", 0) + 1
        dstate["point_history"].append(grade.points)
        dstate["score_history"].append(
            _compute_score_from_counts(dstate["counts"]))

    @property
    def calibration_score(self) -> float:
        """Running calibration score in [0, 100].

        Formula:
          base = 100 * correct / total
          penalty = 30 * (over_trust / total)    # over-trust hits harder
          minor   = 10 * (over_suspicion / total)
          score = clamp(base - penalty - minor, 0, 100)
        """
        c = self.counts
        if c.total == 0:
            return 50.0  # neutral starting score
        base = 100.0 * c.correct / c.total
        penalty_over_trust = 30.0 * c.over_trust / c.total
        penalty_over_susp = 10.0 * c.over_suspicion / c.total
        s = base - penalty_over_trust - penalty_over_susp
        return max(0.0, min(100.0, s))

    @property
    def total_points(self) -> int:
        return sum(self.point_history)

    def update_rating(self, difficulty: int, won: bool, k: float = 32.0,
                      domain_id: str = "algebra") -> None:
        """Elo update against a difficulty-derived 'opponent' rating.

        Updates BOTH the global rating and the per-domain rating.
        """
        opp_rating = 800 + 200 * (difficulty - 1)
        # Global
        expected = 1 / (1 + 10 ** ((opp_rating - self.rating) / 400))
        actual = 1.0 if won else 0.0
        self.rating += k * (actual - expected)
        # Per-domain
        dstate = self.per_domain.setdefault(domain_id, {
            "counts": {}, "rating": 1000.0,
            "score_history": [], "point_history": [],
        })
        d_expected = 1 / (1 + 10 ** ((opp_rating - dstate["rating"]) / 400))
        dstate["rating"] += k * (actual - d_expected)

    def suggested_difficulty(self, domain_id: Optional[str] = None) -> int:
        """Map rating to a difficulty bracket 1..5. Defaults to global rating."""
        if domain_id and domain_id in self.per_domain:
            rating = self.per_domain[domain_id]["rating"]
        else:
            rating = self.rating
        if rating < 900: return 1
        if rating < 1050: return 2
        if rating < 1200: return 3
        if rating < 1400: return 4
        return 5

    def to_dict(self) -> dict:
        return {
            "counts": {
                "correct_trust": self.counts.correct_trust,
                "correct_catch": self.counts.correct_catch,
                "over_trust": self.counts.over_trust,
                "over_suspicion": self.counts.over_suspicion,
                "wrong_step_catch": self.counts.wrong_step_catch,
                "total": self.counts.total,
            },
            "score": self.calibration_score,
            "total_points": self.total_points,
            "rating": self.rating,
            "suggested_difficulty": self.suggested_difficulty(),
            "score_history": list(self.score_history),
            "point_history": list(self.point_history),
            "per_misconception": dict(self.per_misconception),
            "per_domain": {
                did: {
                    **info,
                    "score": _compute_score_from_counts(info.get("counts", {})),
                    "suggested_difficulty": self.suggested_difficulty(did),
                }
                for did, info in self.per_domain.items()
            },
        }


def _compute_score_from_counts(c: dict) -> float:
    total = c.get("total", 0)
    if total == 0:
        return 50.0
    correct = c.get("correct_trust", 0) + c.get("correct_catch", 0)
    over_trust = c.get("over_trust", 0)
    over_susp = c.get("over_suspicion", 0)
    base = 100.0 * correct / total
    penalty_ot = 30.0 * over_trust / total
    penalty_os = 10.0 * over_susp / total
    return max(0.0, min(100.0, base - penalty_ot - penalty_os))
