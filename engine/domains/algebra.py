"""Algebra domain — wraps existing engine code into the Domain interface.

This is a binding shim. All existing logic in engine/generators.py and
engine/misconceptions/* is preserved; we just expose it through the Domain
interface so the system can treat algebra interchangeably with future
domains.
"""
from __future__ import annotations

from typing import Any, Optional

from ..domain import Domain, ProblemKind, register_domain
from ..generators import GENERATORS, generate as _legacy_generate
from ..generators import validate_solution as _legacy_validate
from ..misconceptions import all_misconceptions
from ..types import ProblemType, Solution
from ..verifier import states_equivalent as _algebra_states_equivalent


_PROBLEM_KIND_LABELS = {
    ProblemType.LINEAR_ONE_VAR.value:           ("Linear (1-step)", (1, 4)),
    ProblemType.LINEAR_TWO_STEP.value:          ("Linear (distribution)", (2, 5)),
    ProblemType.LINEAR_FRACTION.value:          ("Linear (fraction)", (2, 5)),
    ProblemType.QUADRATIC_FACTOR.value:         ("Quadratic (factoring)", (2, 5)),
    ProblemType.QUADRATIC_FORMULA.value:        ("Quadratic (formula)", (3, 5)),
    ProblemType.QUADRATIC_PERFECT_SQUARE.value: ("Quadratic (perfect sq.)", (2, 5)),
}


class AlgebraDomain(Domain):
    id = "algebra"
    label = "Algebra"
    description = "Linear and quadratic equations: solve, factor, and verify."

    def problem_kinds(self) -> list[ProblemKind]:
        return [
            ProblemKind(id=pt.value,
                        label=_PROBLEM_KIND_LABELS[pt.value][0],
                        difficulty_range=_PROBLEM_KIND_LABELS[pt.value][1])
            for pt in GENERATORS.keys()
        ]

    def generate(self, kind_id: str, difficulty: int = 1,
                 seed: Optional[int] = None) -> Solution:
        try:
            ptype = ProblemType(kind_id)
        except ValueError as e:
            raise KeyError(f"Unknown algebra kind: {kind_id}") from e
        return _legacy_generate(ptype, difficulty=difficulty, seed=seed)

    def misconceptions(self):
        # All misconceptions in our existing library are algebra-specific.
        return all_misconceptions()

    def states_equivalent(self, a: Any, b: Any) -> bool:
        return _algebra_states_equivalent(a, b)

    def validate_solution(self, solution: Solution) -> tuple[bool, str]:
        # Use the algebra-specific validator with its FACTOR -> FINAL,
        # SQUARE_ROOT branching, and scratch-symbol logic.
        return _legacy_validate(solution)


register_domain(AlgebraDomain())
