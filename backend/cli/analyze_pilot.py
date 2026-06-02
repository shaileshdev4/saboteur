#!/usr/bin/env python3
"""Analyze Pilot Test #1 logs and optionally write calibrated difficulties.

Usage (from backend/):
    python -m cli.analyze_pilot
    python -m cli.analyze_pilot --logs cli/logs --apply
    python -m cli.analyze_pilot --sqlite data/saboteur.db
    python -m cli.analyze_pilot --min-seen 1

Human pilots: have 5+ people play via CLI or web, then run this on logs / DB.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.misconceptions import all_misconceptions
from engine.pilot_calibration import (
    aggregate_per_misconception_from_sessions,
    aggregate_session_logs,
    difficulty_overrides,
    format_report_table,
    load_overrides,
    save_overrides,
)


def _current_difficulties() -> dict[str, int]:
    return {m.id: m.difficulty for m in all_misconceptions()}


def _load_sqlite_sessions(db_path: Path) -> list[dict]:
    if not db_path.is_file():
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT state_json FROM sessions").fetchall()
    finally:
        conn.close()
    out = []
    for (raw,) in rows:
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Pilot Test #1 analysis")
    p.add_argument("--logs", type=Path, default=Path("cli/logs"),
                   help="Directory of CLI session JSON files")
    p.add_argument("--sqlite", type=Path, default=None,
                   help="Also aggregate per_misconception from web sessions DB")
    p.add_argument("--out", type=Path,
                   default=Path("data/pilot_difficulty.json"),
                   help="Where to write calibrated overrides")
    p.add_argument("--apply", action="store_true",
                   help="Write --out (does not edit Python source; engine loads JSON at startup)")
    p.add_argument("--min-seen", type=int, default=3,
                   help="Minimum sabotaged rounds per misconception to emit override")
    args = p.parse_args()

    paths = sorted(args.logs.glob("*.json")) if args.logs.is_dir() else []
    report_cli = aggregate_session_logs(paths)

    report_web = None
    if args.sqlite:
        sessions = _load_sqlite_sessions(args.sqlite)
        if sessions:
            report_web = aggregate_per_misconception_from_sessions(sessions)
            for mid, st in report_web.by_misconception.items():
                dst = report_cli.stats_for(mid)
                dst.seen += st.seen
                dst.caught += st.caught

    current = _current_difficulties()
    print(format_report_table(report_cli, current))
    print()

    if report_cli.sessions == 0 and not (report_web and report_web.sessions):
        print("No pilot data yet.")
        print("  CLI: python -m cli.play --rounds 20 --log-dir cli/logs")
        print("  Web: play on deployed app, then: --sqlite data/saboteur.db")
        return 1

    overrides = difficulty_overrides(report_cli, min_seen=args.min_seen)
    if not overrides:
        print(f"No overrides (need >={args.min_seen} samples per misconception).")
        return 0

    print(f"Proposed overrides ({len(overrides)}):")
    for mid, d in sorted(overrides.items()):
        print(f"  {mid}: {current.get(mid, '?')} -> {d}")

    if args.apply:
        save_overrides(args.out, overrides)
        print(f"\nWrote {args.out.resolve()}")
        print("Restart backend to load overrides (or set PILOT_DIFFICULTY_PATH).")
    else:
        print(f"\nDry run. To apply: python -m cli.analyze_pilot --apply")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
