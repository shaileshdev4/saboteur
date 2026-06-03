"""Core domain types for The Saboteur engine.

These types are deliberately simple dataclasses with no SymPy logic -the
engine code operates on these, and SymPy lives in `verifier.py` and the
generators / misconception transforms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class OperationType(str, Enum):
    """Tags what kind of algebraic operation a step performed.

    Used by misconception transforms to decide which steps they can attack.
    For example, the "sign flip on transpose" misconception only applies
    to TRANSPOSE steps.
    """
    INITIAL = "initial"               # The original problem statement
    SIMPLIFY = "simplify"              # Combined like terms / arithmetic
    TRANSPOSE = "transpose"            # Moved a term across the = sign
    MULTIPLY_BOTH_SIDES = "multiply_both_sides"
    DIVIDE_BOTH_SIDES = "divide_both_sides"
    EXPAND = "expand"                  # Distributed multiplication
    FACTOR = "factor"                  # Factored an expression
    SQUARE_ROOT = "square_root"        # Took sqrt of both sides
    SUBSTITUTE = "substitute"          # Plugged a value in
    FINAL = "final"                    # Final answer line


class ProblemType(str, Enum):
    LINEAR_ONE_VAR = "linear_one_var"          # e.g. 3x + 5 = 14
    LINEAR_TWO_STEP = "linear_two_step"        # e.g. 2(x+3) = 4x - 1
    LINEAR_FRACTION = "linear_fraction"        # e.g. (3x + 6)/3 = 4
    QUADRATIC_FACTOR = "quadratic_factor"       # factorable: x^2 - 5x + 6 = 0
    QUADRATIC_FORMULA = "quadratic_formula"     # needs the formula
    QUADRATIC_PERFECT_SQUARE = "quadratic_perfect_square"  # (x+a)^2 = b


@dataclass
class Step:
    """One state in a worked solution.

    `expression` is a SymPy object (Expr or Equality). We keep it as Any to
    avoid leaking SymPy types into pure-Python code that uses these.
    """
    index: int
    expression: Any                    # sympy.Expr or sympy.Equality
    operation: OperationType
    note: str = ""                     # Internal note, NOT player-facing
    # The narrated form is populated by the LLM layer, not here.

    def latex(self) -> str:
        from sympy import latex
        return latex(self.expression)

    def __repr__(self) -> str:
        return f"Step({self.index}, {self.operation.value}, {self.expression})"


@dataclass
class Solution:
    """A complete worked solution: ordered list of steps from problem to answer."""
    problem_type: ProblemType
    variables: list[Any]               # SymPy symbols
    steps: list[Step]
    final_answer: Any                  # The canonical answer (Expr, set, or tuple)

    @property
    def problem(self) -> Any:
        return self.steps[0].expression

    @property
    def num_steps(self) -> int:
        return len(self.steps)


@dataclass
class SabotageRecord:
    """Records what the sabotage engine did to a solution.

    If `is_clean` is True, the solution was not modified. Otherwise,
    `corrupted_step_index` is the FIRST step that was changed, and
    every step from there onward in the displayed solution may differ
    from the canonical one (because the error propagates).
    """
    is_clean: bool
    corrupted_step_index: Optional[int] = None
    misconception_id: Optional[str] = None
    # The canonical (truth) and displayed (possibly-corrupted) solutions.
    truth: Solution = field(default=None)        # type: ignore[assignment]
    displayed: Solution = field(default=None)    # type: ignore[assignment]


class PlayerDecision(str, Enum):
    TRUST = "trust"
    FLAG = "flag"


@dataclass
class PlayerAction:
    decision: PlayerDecision
    flagged_step_index: Optional[int] = None   # required if decision == FLAG
    flagged_misconception_id: Optional[str] = None  # optional bonus identification


class GradeOutcome(str, Enum):
    CORRECT_TRUST = "correct_trust"           # solution was clean, player trusted
    CORRECT_CATCH = "correct_catch"           # solution was wrong, player flagged the right step
    OVER_TRUST = "over_trust"                 # solution was wrong, player trusted   (dangerous!)
    OVER_SUSPICION = "over_suspicion"         # solution was clean, player flagged
    WRONG_STEP_CATCH = "wrong_step_catch"     # solution was wrong, player flagged the WRONG step


@dataclass
class Grade:
    outcome: GradeOutcome
    points: int
    explanation_seed: dict             # Info for the LLM explainer; never used for grading
    # The seed contains things like the misconception name + correct vs shown step,
    # so the LLM can phrase the explanation without ever judging correctness itself.
