import pytest
import sympy as sp

import mathlint

a, u, v, t, r, f, x, y, A = sp.symbols("a u v t r f x y A")


def same(found, expected):
    return len(found) == len(expected) and all(
        any(sp.simplify(value - other) == 0 for other in expected) for value in found
    )


def test_linear_formula():
    solution = mathlint.solve("v = u + a t", variable="t")
    assert same(solution.answers, [(v - u) / a])


def test_for_suffix_names_the_letter():
    solution = mathlint.solve("v = u + a t for t")
    assert solution.variable == t
    assert same(solution.answers, [(v - u) / a])


def test_dividing_by_a_letter_says_it_must_not_be_zero():
    solution = mathlint.solve("v = u + a t", variable="t")
    assert any("must not be 0" in step.text for step in solution.steps)


def test_quadratic_formula_for_a_radius():
    solution = mathlint.solve("A = pi r^2", variable="r")
    assert same(solution.answers, [-sp.sqrt(A / sp.pi), sp.sqrt(A / sp.pi)])


def test_lens_formula():
    solution = mathlint.solve("1/f = 1/u + 1/v", variable="v")
    assert same(solution.answers, [f * u / (u - f)])


def test_x_is_the_default_when_there_are_other_letters():
    solution = mathlint.solve("x + y = 1")
    assert solution.variable == x
    assert same(solution.answers, [1 - y])


def test_several_letters_without_x_ask_which_one():
    with pytest.raises(mathlint.UnsupportedError) as excinfo:
        mathlint.solve("a + b = c")
    assert "for" in str(excinfo.value)


def test_a_letter_that_is_not_there():
    with pytest.raises(mathlint.ParseError):
        mathlint.solve("v = u + a t", variable="z")


def test_to_dict_lists_the_letters():
    data = mathlint.solve("v = u + a t", variable="t").to_dict()
    assert data["letters"] == ["a", "t", "u", "v"]
    assert data["variable"] == "t"
    assert data["kind_label"] == "Formula, solved for t"
