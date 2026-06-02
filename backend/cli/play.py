"""Terminal harness for pilot testing. Run: cd backend && python -m cli.play"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from engine.calibration import CalibrationState
from engine.generators import GENERATORS, generate
from engine.grader import grade
from engine.sabotage import sabotage
from engine.types import GradeOutcome, PlayerAction, PlayerDecision, ProblemType


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"

    @classmethod
    def disable(cls):
        for name in list(vars(cls)):
            if name.isupper():
                setattr(cls, name, "")


def render_step(i: int, step) -> str:
    return f"  {C.DIM}Step {i}{C.RESET}  {C.CYAN}{step.latex()}{C.RESET}"


def render_solution(record):
    print(f"\n{C.BOLD}AI's worked solution:{C.RESET}")
    for step in record.displayed.steps:
        print(render_step(step.index, step))
        print()


def prompt_decision(num_steps: int, auto: str | None = None):
    if auto == "trust":
        return PlayerAction(decision=PlayerDecision.TRUST)
    if auto == "flag-0" and num_steps > 0:
        return PlayerAction(decision=PlayerDecision.FLAG, flagged_step_index=0)

    print(f"{C.BOLD}Your audit:{C.RESET}  [T] Trust  [F n] Flag step n  [Q] Quit")
    while True:
        raw = input("  > ").strip().lower()
        if raw == "q":
            return None
        if raw == "t":
            return PlayerAction(decision=PlayerDecision.TRUST)
        if raw.startswith("f"):
            parts = raw.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1])
                if 0 <= idx < num_steps:
                    return PlayerAction(decision=PlayerDecision.FLAG, flagged_step_index=idx)
        print(f"  {C.YELLOW}Try T, F <0-{num_steps - 1}>, or Q{C.RESET}")


def reveal(record, g):
    colors = {
        GradeOutcome.CORRECT_TRUST: (C.GREEN, "Correct trust"),
        GradeOutcome.CORRECT_CATCH: (C.GREEN, "Caught it"),
        GradeOutcome.OVER_TRUST: (C.RED, "Over-trust - there WAS an error"),
        GradeOutcome.OVER_SUSPICION: (C.YELLOW, "Over-suspicion - solution was clean"),
        GradeOutcome.WRONG_STEP_CATCH: (C.YELLOW, "Wrong step flagged"),
    }
    color, label = colors.get(g.outcome, (C.YELLOW, g.outcome.value))
    print(f"\n{color}{C.BOLD}{label}{C.RESET}  ({g.points:+d} pts)")
    if not record.is_clean:
        print(f"  Error at step {record.corrupted_step_index}")
        seed = g.explanation_seed
        if seed.get("truth_step_latex"):
            print(f"  Truth: {seed['truth_step_latex']}")
            print(f"  Shown: {seed['shown_step_latex']}")


def render_dashboard(state: CalibrationState):
    c = state.counts
    print(f"\n{C.BOLD}Calibration:{C.RESET} {state.calibration_score:.1f}/100  "
          f"points {state.total_points}  rating {state.rating:.0f}")
    print(f"  trust OK {c.correct_trust} | flag OK {c.correct_catch} | "
          f"over-trust {c.over_trust} | over-suspicion {c.over_suspicion}")


def run_session(args):
    rng = random.Random(args.seed)
    state = CalibrationState()
    log = {"started_at": datetime.now(timezone.utc).isoformat(), "rounds": []}

    print(f"{C.BOLD}The Saboteur - CLI pilot{C.RESET} ({args.rounds} rounds)\n")

    for n in range(1, args.rounds + 1):
        ptype = ProblemType(args.problem_type) if args.problem_type else rng.choice(list(GENERATORS))
        diff = args.difficulty if args.difficulty is not None else state.suggested_difficulty()
        sol = generate(ptype, difficulty=diff, seed=rng.randint(0, 10_000))
        record = sabotage(sol, corrupt_probability=args.corrupt_prob, seed=rng.randint(0, 10_000))

        print(f"{C.BOLD}{'=' * 50}\nRound {n}/{args.rounds}  {ptype.value}  diff {diff}{C.RESET}")
        render_solution(record)
        action = prompt_decision(len(record.displayed.steps), auto=args.auto)
        if action is None:
            break
        g = grade(action, record)
        reveal(record, g)
        state.update_rating(diff, g.outcome in (GradeOutcome.CORRECT_TRUST, GradeOutcome.CORRECT_CATCH))
        state.record(g, record)
        render_dashboard(state)
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
            "caught": g.outcome.value == "correct_catch",
        })

    if args.log_dir:
        Path(args.log_dir).mkdir(parents=True, exist_ok=True)
        path = Path(args.log_dir) / f"session_{int(time.time())}.json"
        log["final"] = state.to_dict()
        path.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")
        print(f"\n{C.DIM}Log: {path}{C.RESET}")

    print(f"\n{C.BOLD}Final score: {state.calibration_score:.1f}/100{C.RESET}")


def main():
    p = argparse.ArgumentParser(description="Saboteur CLI pilot")
    p.add_argument("--rounds", type=int, default=10)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--difficulty", type=int, choices=range(1, 6))
    p.add_argument("--corrupt-prob", type=float, default=0.5)
    p.add_argument("--problem-type", choices=[x.value for x in ProblemType])
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--log-dir", default="cli/logs")
    p.add_argument("--no-log", action="store_true")
    p.add_argument("--auto", choices=["trust", "flag-0"])
    args = p.parse_args()
    if args.no_color or not sys.stdout.isatty():
        C.disable()
    if args.no_log:
        args.log_dir = None
    if args.seed is not None:
        random.seed(args.seed)
    run_session(args)


if __name__ == "__main__":
    main()
