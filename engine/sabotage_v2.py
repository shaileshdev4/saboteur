"""Domain-aware sabotage engine.

This is the multi-domain replacement for engine/sabotage.py. The original
`sabotage()` function still works (it uses the algebra-specific global
misconception registry); this new one routes through a Domain.

Phase 1 also adds two features:
  1. **Step propagation** -optionally propagate the corruption forward so
     subsequent steps reflect the error. (Real student errors propagate.)
  2. **Hint metadata** -record which step was corrupted and the category of
     the misconception, so the hint system can give graduated help without
     revealing the answer.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .domain import Domain
from .types import SabotageRecord, Solution, Step


@dataclass
class SabotageOptions:
    corrupt_probability: float = 0.5
    difficulty_range: tuple[int, int] = (1, 5)
    propagate: bool = False           # propagate the error forward
    max_propagate_steps: int = 3      # cap propagation depth


def sabotage_domain(domain: Domain,
                    solution: Solution,
                    options: Optional[SabotageOptions] = None,
                    seed: Optional[int] = None) -> SabotageRecord:
    """Run sabotage against a Solution from a specific Domain."""
    options = options or SabotageOptions()
    rng = random.Random(seed)

    if rng.random() >= options.corrupt_probability:
        return SabotageRecord(is_clean=True, truth=solution, displayed=solution)

    # Gather (misconception, step_index) candidates from THIS domain's library.
    candidates = []
    for mis in domain.misconceptions():
        if not (options.difficulty_range[0] <= mis.difficulty
                <= options.difficulty_range[1]):
            continue
        for i, step in enumerate(solution.steps):
            if i == 0:
                continue
            try:
                if mis.applies_to(step, solution, i):
                    candidates.append((mis, i))
            except Exception:
                continue

    if not candidates:
        return SabotageRecord(is_clean=True, truth=solution, displayed=solution)

    rng.shuffle(candidates)
    for mis, idx in candidates:
        target_step = solution.steps[idx]
        try:
            corrupted = mis.apply(target_step, solution, idx)
        except Exception:
            continue
        if domain.states_equivalent(corrupted.expression, target_step.expression):
            continue   # silent no-op; try another

        new_steps = list(solution.steps)
        new_steps[idx] = corrupted

        # Optional propagation: re-derive subsequent steps from the corrupted
        # state. For Phase 1 we use a SIMPLE propagation rule: any later step
        # that is a TRANSPOSE/DIVIDE/SIMPLIFY of an equation gets the same
        # operation applied to the corrupted state. This is heuristic -not
        # all misconceptions propagate the same way -but it's better than
        # the V1 behavior (subsequent steps revert to canonical, which is
        # itself a tell).
        if options.propagate:
            new_steps = _propagate_corruption(
                domain, new_steps, idx, options.max_propagate_steps
            )

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

    return SabotageRecord(is_clean=True, truth=solution, displayed=solution)


def _propagate_corruption(domain: Domain,
                          steps: list,
                          corrupted_idx: int,
                          max_steps: int) -> list:
    """Propagate the corruption forward by re-applying each subsequent step's
    operation against the corrupted state.

    This is a HEURISTIC. We don't actually re-run the generator; we look at
    each subsequent canonical step and try to derive an analogous step from
    the corrupted state by computing the "delta" between consecutive canonical
    steps and applying it to the corrupted line.

    Bail out as soon as we can't sensibly propagate (e.g., a step uses
    Pow/Factor that we can't trivially mirror). This means the displayed
    solution will be: clean up to step k-1, corrupted at step k, propagated
    through step k+max_steps, then back to canonical. Imperfect but better
    than "step k breaks, everyone else perfect."
    """
    import sympy as sp

    propagated_steps = list(steps)
    last_state = propagated_steps[corrupted_idx].expression

    propagated_count = 0
    for j in range(corrupted_idx + 1, len(steps)):
        if propagated_count >= max_steps:
            break
        canon_prev = steps[j - 1].expression if j - 1 != corrupted_idx else None
        canon_curr = steps[j].expression

        # Compute the "delta" only when both are simple equations.
        if not (isinstance(canon_curr, sp.Equality)
                and isinstance(last_state, sp.Equality)):
            break

        # If the canonical previous step is None (because we're at corrupted+1),
        # use the original canonical step at corrupted_idx for delta calculation.
        canon_prev = steps[j - 1].expression
        if not isinstance(canon_prev, sp.Equality):
            break

        # Heuristic delta: lhs_delta = canon_curr.lhs - canon_prev.lhs;
        # rhs_delta = canon_curr.rhs - canon_prev.rhs. Apply same delta to
        # last_state.
        try:
            lhs_delta = sp.simplify(canon_curr.lhs - canon_prev.lhs)
            rhs_delta = sp.simplify(canon_curr.rhs - canon_prev.rhs)
            new_lhs = sp.simplify(last_state.lhs + lhs_delta)
            new_rhs = sp.simplify(last_state.rhs + rhs_delta)
            new_expr = sp.Eq(new_lhs, new_rhs)
        except Exception:
            break

        # If the propagated state equals the canonical state (delta happens to
        # absorb the error), stop -we'd be showing a clean step which would
        # be confusing.
        if domain.states_equivalent(new_expr, canon_curr):
            break

        # Build a propagated Step.
        propagated_steps[j] = Step(
            j, new_expr, steps[j].operation,
            note=f"propagated:{steps[j].note}",
        )
        last_state = new_expr
        propagated_count += 1

    return propagated_steps
