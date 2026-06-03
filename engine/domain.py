"""The Domain interface.

A `Domain` is a self-contained STEM subject (algebra, geometry, calculus, ...)
that plugs into the same sabotage / grading / calibration engine.

Each domain provides:
  - A set of `ProblemKind`s it can generate
  - A `generate(kind, difficulty, seed) -> Solution` function
  - A misconception library (list of Misconceptions applicable to this domain)
  - A `verify_step_equivalence(a, b)` function -the source of truth for
    "does step b follow from step a?" Different domains need different
    equivalence checks (algebra equations vs. geometric figures vs. calculus
    derivatives).

The Domain registers itself with the global registry; the engine and API
look up domains by id ("algebra", "geometry", "calculus").

Why an abstraction layer instead of just adding code to existing files?
Because the project's core claim -"verifier decides, LLM explains" -needs
to hold across every domain. Pulling the verifier interface out means we
can prove (via tests) that every domain implements it. New domains can't
sneak in by skipping verification.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .types import Solution, Step


@dataclass
class ProblemKind:
    """One kind of problem within a domain.

    For algebra: "linear_one_var", "quadratic_factor", etc.
    For geometry: "triangle_pythag", "circle_area", etc.
    For calculus: "polynomial_derivative", "u_sub_integral", etc.

    `id` is the wire identifier; `label` is human-readable; `difficulty_range`
    bounds the difficulty levels this kind supports.
    """
    id: str
    label: str
    difficulty_range: tuple[int, int] = (1, 5)


class Domain(ABC):
    """Subject-area plugin."""
    id: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def problem_kinds(self) -> list[ProblemKind]:
        ...

    @abstractmethod
    def generate(self, kind_id: str, difficulty: int = 1,
                 seed: Optional[int] = None) -> Solution:
        """Generate a canonical Solution for this kind."""
        ...

    @abstractmethod
    def misconceptions(self) -> list:
        """Misconceptions applicable to this domain."""
        ...

    @abstractmethod
    def states_equivalent(self, a: Any, b: Any) -> bool:
        """Domain-specific equivalence check.

        For algebra: equation/expression equivalence via SymPy.
        For geometry: numerical-with-tolerance equivalence on lengths/areas.
        For calculus: symbolic differentiation / integration check.
        """
        ...

    def validate_solution(self, solution: Solution) -> tuple[bool, str]:
        """Default validator: every consecutive step pair is equivalent.

        Domains can override for more nuance (e.g., FINAL roots, scratch
        steps), as algebra does.
        """
        for i in range(1, len(solution.steps)):
            prev = solution.steps[i - 1].expression
            curr = solution.steps[i].expression
            if not self.states_equivalent(prev, curr):
                return False, f"Step {i} doesn't follow from step {i-1}"
        return True, "ok"


# ---------- Registry ----------

_DOMAINS: dict[str, Domain] = {}


def register_domain(domain: Domain) -> Domain:
    if not domain.id:
        raise ValueError(f"Domain {domain.__class__.__name__} missing id")
    if domain.id in _DOMAINS:
        raise ValueError(f"Domain id collision: {domain.id}")
    _DOMAINS[domain.id] = domain
    return domain


def get_domain(domain_id: str) -> Domain:
    if domain_id not in _DOMAINS:
        raise KeyError(f"Unknown domain: {domain_id}. "
                       f"Registered: {list(_DOMAINS.keys())}")
    return _DOMAINS[domain_id]


def all_domains() -> list[Domain]:
    return list(_DOMAINS.values())


def find_misconception_across_domains(mid: str):
    """Search every registered domain for a misconception with this id.

    Returns the misconception object or raises KeyError if not found.
    Useful for grader/hint code that has a record's misconception_id but
    doesn't know which domain it came from.
    """
    for domain in _DOMAINS.values():
        for mis in domain.misconceptions():
            if mis.id == mid:
                return mis
    raise KeyError(f"No misconception '{mid}' in any registered domain")
