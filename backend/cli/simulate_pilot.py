#!/usr/bin/env python3
"""Synthetic pilot sessions - tests logging + analyze pipeline, NOT human subtlety.

Runs N sessions with an 'oracle' player (always flags the true break).
Catch rates will be ~100%% - use only to verify tooling before real humans play.

Usage:
    python -m cli.simulate_pilot --sessions 5 --rounds 20
    python -m cli.analyze_pilot --apply
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.calibration import CalibrationState
from engine.generators import GENERATORS, generate
from engine.grader import grade
from engine.sabotage import sabotage
from engine.types import GradeOutcome, PlayerAction, PlayerDecision, ProblemType


def run_oracle_session(rounds: int, seed: int, corrupt_prob: float) -> dict:
    rng = random.Random(seed)
    state = CalibrationState()
    log = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pilot_mode": "oracle_simulation",
        "rounds": [],
    }
    for n in range(1, rounds + 1):
        ptype = rng.choice(list(GENERATORS))
        diff = state.suggested_difficulty()
        sol = generate(ptype, difficulty=diff, seed=rng.randint(0, 10_000))
        record = sabotage(sol, corrupt_probability=corrupt_prob, seed=rng.randint(0, 10_000))

        if record.is_clean:
            action = PlayerAction(decision=PlayerDecision.TRUST)
        else:
            action = PlayerAction(
                decision=PlayerDecision.FLAG,
                flagged_step_index=record.corrupted_step_index,
            )
        g = grade(action, record)
        state.update_rating(
            diff,
            g.outcome in (GradeOutcome.CORRECT_TRUST, GradeOutcome.CORRECT_CATCH),
        )
        state.record(g, record)
        log["rounds"].append({
            "round": n,
            "problem_type": ptype.value,
            "difficulty": diff,
            "is_clean": record.is_clean,
            "misconception_id": record.misconception_id,
            "corrupted_step_index": record.corrupted_step_index,
            "player_decision": action.decision.value,
            "flagged_step_index": action.flagged_step_index,
            "outcome": g.outcome.value,
            "points": g.points,
            "caught": g.outcome == GradeOutcome.CORRECT_CATCH,
        })
    log["final"] = state.to_dict()
    return log


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sessions", type=int, default=3)
    p.add_argument("--rounds", type=int, default=20)
    p.add_argument("--corrupt-prob", type=float, default=0.7)
    p.add_argument("--log-dir", type=Path, default=Path("cli/logs"))
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    args.log_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.sessions):
        log = run_oracle_session(args.rounds, args.seed + i, args.corrupt_prob)
        path = args.log_dir / f"sim_oracle_{int(time.time())}_{i}.json"
        path.write_text(json.dumps(log, indent=2), encoding="utf-8")
        print(f"Wrote {path}")

    print("\nOracle simulation done. Run: python -m cli.analyze_pilot")
    print("(Expect ~100% catch rates - real humans are required for true calibration.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
