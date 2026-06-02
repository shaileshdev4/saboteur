"""Tests for the verifier. Run before trusting anything else."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp
from sympy import Eq, symbols, sqrt, Rational

from engine.verifier import (
    expressions_equivalent,
    equations_equivalent,
    states_equivalent,
    is_well_formed,
)

x, y = symbols("x y")


def test_basic_expression_equivalence():
    assert expressions_equivalent(x + x, 2 * x)
    assert expressions_equivalent((x + 1) ** 2, x ** 2 + 2 * x + 1)
    assert not expressions_equivalent(x + 1, x - 1)
    assert not expressions_equivalent(2 * x, 2 * x + 1)


def test_fractional_equivalence():
    assert expressions_equivalent(Rational(1, 2) + Rational(1, 3), Rational(5, 6))
    assert expressions_equivalent((x + 1) / 2, x / 2 + Rational(1, 2))


def test_equation_equivalence_same_solutions():
    eq1 = Eq(2 * x + 4, 10)              # x = 3
    eq2 = Eq(2 * x, 6)                    # x = 3
    eq3 = Eq(x, 3)                        # x = 3
    assert equations_equivalent(eq1, eq2)
    assert equations_equivalent(eq2, eq3)
    assert equations_equivalent(eq1, eq3)


def test_equation_inequivalence():
    eq1 = Eq(2 * x + 4, 10)              # x = 3
    eq_wrong = Eq(2 * x, 14)              # x = 7 (sign flip would produce this kind of thing)
    assert not equations_equivalent(eq1, eq_wrong)


def test_quadratic_equivalence():
    # x^2 - 5x + 6 = 0 has solutions {2, 3}.
    eq1 = Eq(x ** 2 - 5 * x + 6, 0)
    eq2 = Eq((x - 2) * (x - 3), 0)       # factored - same solutions
    assert equations_equivalent(eq1, eq2)
    # vs wrong factoring
    eq_wrong = Eq((x - 2) * (x + 3), 0)  # solutions {2, -3}
    assert not equations_equivalent(eq1, eq_wrong)


def test_states_equivalent_dispatch():
    assert states_equivalent(2 * x, x + x)
    assert states_equivalent(Eq(2 * x, 6), Eq(x, 3))
    # mixing types must return False, not throw
    assert not states_equivalent(2 * x, Eq(x, 3))


def test_well_formed():
    assert is_well_formed(x + 1)
    assert is_well_formed(Eq(x, 3))
    assert not is_well_formed(sp.nan)
    assert not is_well_formed(sp.oo)


def test_garbage_input_does_not_throw():
    # The verifier promises to return False on bad input, not raise.
    assert not expressions_equivalent("???", x)
    assert not equations_equivalent("not an equation", Eq(x, 3))


if __name__ == "__main__":
    test_basic_expression_equivalence()
    test_fractional_equivalence()
    test_equation_equivalence_same_solutions()
    test_equation_inequivalence()
    test_quadratic_equivalence()
    test_states_equivalent_dispatch()
    test_well_formed()
    test_garbage_input_does_not_throw()
    from tests._console import say
    say("[OK] All verifier tests passed.")
