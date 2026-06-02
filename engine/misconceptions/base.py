"""Misconception base class and registry.

Each misconception is a structured way that students (and AIs) make algebra
errors. A misconception:
  - declares which OperationType(s) it can attack
  - has a predicate `applies_to(step, solution, step_index)` that decides
    whether it can be applied to a given step in context
  - has a transform `apply(step, solution, step_index)` that produces a NEW
    Step with a *wrong-but-plausible* expression
  - has metadata: name, plain description, difficulty (1=easy to catch,
    5=hard to catch), category

Every misconception is unit-tested to ensure:
  (a) The produced step is well-formed (no NaN, no infinity, parses cleanly)
  (b) The produced step is NOT equivalent to the truth at that step
  (c) When applicable, the predicate matches at least one step of some
      generated problem.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..types import OperationType, Solution, Step


class Misconception(ABC):
    """Abstract base for a misconception transform."""

    id: str = ""                      # short identifier, e.g. "sign_flip_transpose"
    name: str = ""                    # human name, e.g. "Sign flip on transposition"
    description: str = ""             # 1-sentence plain-language description
    category: str = ""                # "sign", "distribution", "fraction", "cancellation", "coefficient", "operation_one_side"
    difficulty: int = 3               # 1..5
    applicable_ops: tuple[OperationType, ...] = ()

    @abstractmethod
    def applies_to(self, step: Step, solution: Solution, step_index: int) -> bool:
        """Whether this misconception can attack `step`."""
        ...

    @abstractmethod
    def apply(self, step: Step, solution: Solution, step_index: int) -> Step:
        """Return a NEW Step with the corrupted expression."""
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Misconception] = {}


def register(m: Misconception) -> Misconception:
    if not m.id:
        raise ValueError(f"Misconception {m.__class__.__name__} has no id")
    if m.id in _REGISTRY:
        raise ValueError(f"Misconception id collision: {m.id}")
    _REGISTRY[m.id] = m
    return m


def all_misconceptions() -> list[Misconception]:
    return list(_REGISTRY.values())


def get_misconception(mid: str) -> Misconception:
    return _REGISTRY[mid]
