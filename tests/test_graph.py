import json

import pytest

import mathlint
from mathlint.graph import graph_for, sample
from mathlint.web_api import handle


def graph(text, **options):
    return graph_for(text, mathlint.solve(text, **options))


def test_an_equation_draws_its_left_side_and_marks_the_answers():
    spec = graph("x^2 - 5x + 6 = 0")
    assert [curve["expr"] for curve in spec["curves"]] == ["x^2 - 5*x + 6"]
    assert spec["curves"][0]["latex"] == "y = x^{2} - 5 x + 6"
    assert [mark["label"] for mark in spec["marks"]] == ["(2, 0)", "(3, 0)"]
    assert spec["view"]["x_min"] < 2 < 3 < spec["view"]["x_max"]
    assert len(spec["samples"]["xs"]) == 400


def test_both_sides_meet_at_the_answer():
    spec = graph("sqrt(x) = x - 2")
    assert [curve["expr"] for curve in spec["curves"]] == ["sqrt(x)", "x - 2"]
    assert spec["marks"] == [{"x": 4.0, "y": 2.0, "label": "(4, 2)", "closed": True}]
    # the square root is not defined left of 0
    first = spec["samples"]["curves"][0]
    xs = spec["samples"]["xs"]
    assert all(y is None for x, y in zip(xs, first, strict=True) if x < 0)


def test_an_inequality_shades_its_answer():
    spec = graph("1/x < 2")
    assert spec["shade"] == [{"from": None, "to": 0.0}, {"from": 0.5, "to": None}]
    assert spec["marks"] == [{"x": 0.5, "y": 2.0, "label": "(0.5, 2)", "closed": False}]


def test_a_system_draws_each_equation():
    spec = graph("x + y = 5; x^2 + y^2 = 13")
    assert [curve["expr"] for curve in spec["curves"]] == [
        "5 - x",
        "-sqrt(13 - x^2)",
        "sqrt(13 - x^2)",
    ]
    assert [mark["label"] for mark in spec["marks"]] == ["(2, 3)", "(3, 2)"]
    vertical = graph("x = 2; x + y = 5")
    assert vertical["vertical"] == [{"x": 2.0, "latex": "x = 2"}]


def test_an_expression_is_a_function():
    spec = graph("(x + 2)^2")
    assert spec["curves"][0]["latex"] == "y = x^{2} + 4 x + 4"
    assert spec["marks"][0]["label"] == "(-2, 0)"


def test_a_definite_integral_shades_its_area():
    reply = json.loads(handle("solve", json.dumps({"text": r"\int_{-1}^{2} x^2 - 1\,dx"})))
    spec = reply["result"]["graph"]
    assert [curve["expr"] for curve in spec["curves"]] == ["x^2 - 1"]
    assert spec["area"] == {"from": -1.0, "to": 2.0}
    assert [mark["label"] for mark in spec["marks"]] == ["(-1, 0)", "(2, 0)"]
    # an indefinite integral has no area to shade
    reply = json.loads(handle("solve", json.dumps({"text": "int x^2 dx"})))
    assert reply["result"]["graph"] is None


@pytest.mark.parametrize("text", ["2 + 3", "v = u + a t", "x + 1 = x + 1"])
def test_no_graph_when_there_is_nothing_to_draw(text):
    result = mathlint.solve(text, variable="t") if "u" in text else mathlint.solve(text)
    assert graph_for(text, result) is None


def test_sampling_leaves_gaps_where_a_curve_is_not_defined():
    assert sample(["1/x"], "x", -1, 1, count=5) == {
        "xs": [-1.0, -0.5, 0.0, 0.5, 1.0],
        "curves": [[-1.0, -2.0, None, 2.0, 1.0]],
    }
    assert sample(["ln(x)"], "x", -1, 1, count=3)["curves"] == [[None, None, 0.0]]


def test_the_page_gets_a_graph_and_more_points():
    reply = json.loads(handle("solve", json.dumps({"text": "x^2 - 4 = 0"})))
    assert reply["result"]["graph"]["marks"][0]["label"] == "(-2, 0)"
    reply = json.loads(
        handle(
            "plot",
            json.dumps({"curves": ["x^2"], "variable": "x", "x_min": 0, "x_max": 2, "count": 3}),
        )
    )
    assert reply["result"]["curves"] == [[0.0, 1.0, 4.0]]
    bad = json.loads(
        handle("plot", json.dumps({"curves": ["x"], "variable": "x", "x_min": 2, "x_max": 1}))
    )
    assert bad["ok"] is False
