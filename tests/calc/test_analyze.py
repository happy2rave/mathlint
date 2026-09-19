import mathlint


def findings(text):
    """Step text -> what it shows."""
    result = mathlint.analyze(text)
    return {step.text: step.rendered() for step in result.steps}


def test_a_cubic():
    found = findings("x^3 - 3x")
    assert found["The zeros (x-intercepts): solve f(x) = 0"] == "x = -sqrt(3), x = 0, x = sqrt(3)"
    assert found["Increasing where f'(x) > 0"] == "(-inf, -1) U (1, inf)"
    assert found["Decreasing where f'(x) < 0"] == "(-1, 1)"
    assert found["Local maximum: f(x) rises then falls at x = -1"] == "(-1, 2)"
    assert found["Local minimum: f(x) falls then rises at x = 1"] == "(1, -2)"
    assert found["Inflection point: the bending changes direction at x = 0"] == "(0, 0)"
    assert "No asymptotes" in found


def test_asymptotes_of_a_rational_function():
    found = findings("(x^2 - 1)/(x - 2)")
    assert found["Domain: the denominator x - 2 must not be 0"] == "(-inf, 2) U (2, inf)"
    vertical = next(text for text in found if text.startswith("Vertical asymptote"))
    assert "-infinity from the left and +infinity from the right" in vertical
    assert (
        found[
            "Oblique asymptote: f(x) gets closer and closer to it as x goes to infinity in either "
            "direction"
        ]
        == "y = x + 2"
    )


def test_a_hole_is_not_an_asymptote():
    found = findings("(x^2 - 4)/(x - 2)")
    hole = next(text for text in found if text.startswith("A hole"))
    assert found[hole] == "(2, 4)"
    assert not any(text.startswith("Vertical asymptote") for text in found)


def test_one_sided_domain():
    found = findings("ln(x)/x")
    vertical = next(text for text in found if text.startswith("Vertical asymptote"))
    assert vertical.endswith("goes to -infinity from the right")
    assert found["Local maximum: f(x) rises then falls at x = e"] == "(e, e^(-1))"


def test_the_end_of_a_domain_is_not_a_hole():
    found = findings("sqrt(x - 1)")
    assert not any(text.startswith("A hole") for text in found)
    assert found["Increasing where f'(x) > 0"] == "(1, inf)"
    assert "f'(x) is never 0, so there are no critical points" in found


def test_a_periodic_function():
    found = findings("sin(x)")
    zeros = "The zeros: f(x) = 0 has infinitely many solutions, repeating along the axis"
    assert found[zeros] == "x = 2*pi*n or x = 2*pi*n + pi, for any whole number n"
    assert "No asymptotes" in found


def test_analysis_is_offered_last_and_marks_the_graph():
    import json

    from mathlint.web_api import handle

    assert mathlint.compute("x^2 - 4").methods == ["factor", "simplify", "analyze"]
    reply = json.loads(handle("solve", json.dumps({"text": "x^3 - 3x", "method": "analyze"})))
    result = reply["result"]
    assert result["kind_label"] == "Function analysis"
    labels = [mark["label"] for mark in result["graph"]["marks"]]
    assert "local maximum (-1, 2)" in labels
    # three findings at the origin share one label
    assert "y-intercept, zero, inflection point (0, 0)" in labels
