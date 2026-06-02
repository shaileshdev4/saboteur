"""Pilot Test #1 - aggregate play logs and compute empirical misconception difficulty.

Formula (from docs/misconceptions.md):
    calibrated_difficulty = round(1 + 4 * (1 - catch_rate))
    catch_rate = caught / seen  (only sabotaged rounds with a known misconception)

Target band for a healthy misconception: catch_rate in [0.40, 0.70].
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

TARGET_LOW = 0.40
TARGET_HIGH = 0.70


@dataclass
class MisconceptionPilotStats:
    misconception_id: str
    seen: int = 0
    caught: int = 0
    wrong_step: int = 0
    over_trust: int = 0

    @property
    def catch_rate(self) -> float | None:
        if self.seen == 0:
            return None
        return self.caught / self.seen

    def calibrated_difficulty(self) -> int | None:
        rate = self.catch_rate
        if rate is None:
            return None
        return max(1, min(5, round(1 + 4 * (1 - rate))))


@dataclass
class PilotReport:
    sessions: int = 0
    rounds: int = 0
    by_misconception: dict[str, MisconceptionPilotStats] = field(default_factory=dict)
    overall_over_trust: int = 0
    overall_correct_catch: int = 0
    sabotaged_rounds: int = 0

    def stats_for(self, mid: str) -> MisconceptionPilotStats:
        if mid not in self.by_misconception:
            self.by_misconception[mid] = MisconceptionPilotStats(misconception_id=mid)
        return self.by_misconception[mid]


def _ingest_round(report: PilotReport, row: dict) -> None:
    report.rounds += 1
    if row.get("is_clean"):
        return
    report.sabotaged_rounds += 1
    mid = row.get("misconception_id")
    if not mid:
        return
    st = report.stats_for(mid)
    st.seen += 1
    outcome = row.get("outcome", "")
    if outcome == "correct_catch":
        st.caught += 1
        report.overall_correct_catch += 1
    elif outcome == "wrong_step_catch":
        st.wrong_step += 1
    elif outcome == "over_trust":
        st.over_trust += 1
        report.overall_over_trust += 1


def aggregate_session_logs(paths: Iterable[Path]) -> PilotReport:
    report = PilotReport()
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        report.sessions += 1
        for row in data.get("rounds", []):
            _ingest_round(report, row)
    return report


def aggregate_per_misconception_from_sessions(session_dicts: Iterable[dict]) -> PilotReport:
    """From CalibrationState.to_dict() blobs (web SQLite sessions)."""
    report = PilotReport()
    for state in session_dicts:
        report.sessions += 1
        pm = state.get("per_misconception") or {}
        for mid, entry in pm.items():
            st = report.stats_for(mid)
            seen = int(entry.get("seen", 0))
            caught = int(entry.get("caught", 0))
            st.seen += seen
            st.caught += caught
    return report


def difficulty_overrides(report: PilotReport, min_seen: int = 3) -> dict[str, int]:
    """Only emit overrides when we have enough samples."""
    out: dict[str, int] = {}
    for mid, st in report.by_misconception.items():
        if st.seen < min_seen:
            continue
        d = st.calibrated_difficulty()
        if d is not None:
            out[mid] = d
    return out


def format_report_table(report: PilotReport, current: dict[str, int] | None = None) -> str:
    current = current or {}
    lines = [
        f"Sessions: {report.sessions}  Rounds: {report.rounds}  "
        f"Sabotaged: {report.sabotaged_rounds}",
        "",
        f"{'misconception_id':<32} {'seen':>5} {'caught':>6} {'rate':>6} "
        f"{'old':>4} {'new':>4} {'flag':<10}",
        "-" * 78,
    ]
    for mid in sorted(report.by_misconception.keys()):
        st = report.by_misconception[mid]
        rate = st.catch_rate
        rate_s = f"{rate:.0%}" if rate is not None else "  n/a"
        old = current.get(mid, "?")
        new = st.calibrated_difficulty()
        new_s = str(new) if new is not None else "?"
        flag = ""
        if rate is not None:
            if rate < TARGET_LOW:
                flag = "too hard"
            elif rate > TARGET_HIGH:
                flag = "too easy"
            else:
                flag = "ok"
        lines.append(
            f"{mid:<32} {st.seen:>5} {st.caught:>6} {rate_s:>6} "
            f"{str(old):>4} {new_s:>4} {flag:<10}"
        )
    return "\n".join(lines)


def save_overrides(path: Path, overrides: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_overrides(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in data.items()}


def apply_overrides_to_registry(overrides: dict[str, int]) -> list[str]:
    from engine.misconceptions import all_misconceptions, get_misconception

    applied = []
    for mid, diff in overrides.items():
        try:
            get_misconception(mid).difficulty = max(1, min(5, int(diff)))
            applied.append(mid)
        except KeyError:
            continue
    return applied
