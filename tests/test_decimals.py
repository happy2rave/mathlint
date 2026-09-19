"""Exact answers first, with the decimal a calculator would give alongside."""

import mathlint


def test_irrational_equation_answers_get_decimals():
    data = mathlint.solve("x^2 - x - 1 = 0").to_dict()
    assert data["answers_decimal"] == ["-0.6180339887", "1.618033989"]
    assert data["decimal"] == "x = -0.6180339887 or x = 1.618033989"
    assert data["decimal_latex"] == (
        r"x \approx -0.6180339887 \quad\text{or}\quad x \approx 1.618033989"
    )


def test_a_fraction_answer_gets_a_decimal():
    solution = mathlint.solve("3x = 1")
    assert solution.summary == "x = 1/3 (about x = 0.3333333333)"


def test_whole_number_answers_need_no_decimal():
    data = mathlint.solve("x^2 = 4").to_dict()
    assert data["decimal"] is None
    assert data["answers_decimal"] == [None, None]


def test_mixed_answers_keep_the_exact_ones_exact():
    data = mathlint.solve("3x^2 = x").to_dict()
    assert data["decimal"] == "x = 0 or x = 0.3333333333"
    assert data["decimal_latex"] == r"x = 0 \quad\text{or}\quad x \approx 0.3333333333"


def test_calculations_and_huge_numbers():
    assert mathlint.compute("1/3").to_dict()["decimal_latex"] == r"\approx 0.3333333333"
    result = mathlint.compute("2^100")
    assert result.decimal == "1.2676506 * 10^30"
    assert result.decimal_latex == r"\approx 1.2676506 \times 10^{30}"


def test_no_decimal_for_letters_or_every_number():
    assert mathlint.compute("(x+1)^2").decimal is None
    assert mathlint.solve("x + 1 = x + 1").to_dict()["decimal"] is None
