import pytest
import sympy as sp

import mathlint
from mathlint.errors import UnsupportedError
from mathlint.steps.series import parse_series

x = sp.Symbol("x")

BANK = [
    ("maclaurin e^x", sp.exp(x), 0, 5),
    ("taylor sin(x) at 0 order 5", sp.sin(x), 0, 5),
    ("series of cos(x) order 6", sp.cos(x), 0, 6),
    ("taylor ln(x) at x = 1 up to 4", sp.log(x), 1, 4),
    ("taylor sqrt(x) at 4 order 3", sp.sqrt(x), 4, 3),
    ("maclaurin 1/(1 - x) order 4", 1 / (1 - x), 0, 4),
]


@pytest.mark.parametrize(("text", "function", "point", "order"), BANK, ids=[b[0] for b in BANK])
def test_matches_sympy(text, function, point, order):
    result = mathlint.solve(text)
    assert result.kind == "series"
    expected = sp.series(function, x, point, order + 1).removeO()
    assert sp.expand(result.answer - expected) == 0, result.to_text()


def test_steps():
    result = mathlint.compute("taylor sin(x) at 0 order 5")
    shown = [step.rendered() for step in result.steps]
    assert "1/1!*x - 1/3!*x^3 + 1/5!*x^5" in shown
    assert shown[-1] == "sum over k = 0, 1, 2, ... of (-1)^k*x^(2*k + 1)/(2*k + 1)!"
    table = result.steps[1].rendered().splitlines()
    assert table[2].split("|")[1].strip() == "sin(x)"


def test_powers_of_x_minus_a_are_kept():
    result = mathlint.compute("taylor ln(x) at x = 1 up to 3")
    assert result.summary.startswith("Answer: ")
    assert "(x - 1)^2" in result.steps[-1].rendered()
    assert "O((x - 1)^4)" in result.steps[-1].rendered()


def test_not_defined_at_the_point():
    with pytest.raises(UnsupportedError, match="not defined at x = 0"):
        mathlint.compute("taylor 1/x at 0")


def test_parsing_defaults():
    problem = parse_series("taylor e^x")
    assert (problem.point, problem.order) == (0, 5)
    assert parse_series("maclaurin sin(x) at 3").point == 0


def test_graph_draws_both():
    import json

    from mathlint.web_api import handle

    reply = json.loads(handle("solve", json.dumps({"text": "maclaurin e^x order 3"})))
    graph = reply["result"]["graph"]
    assert [curve["expr"] for curve in graph["curves"]] == ["e^x", "x^3/6 + x^2/2 + x + 1"]
