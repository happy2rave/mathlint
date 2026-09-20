import json

import pytest

import mathlint
from mathlint.web_api import handle


def call(kind, **payload):
    return json.loads(handle(kind, json.dumps(payload)))


def test_version():
    assert call("version") == {"ok": True, "result": mathlint.__version__}


def test_check():
    reply = call("check", text="(x+1)^2\n= x^2 + 2x + 2")
    assert reply["ok"] is True
    assert reply["result"]["first_error"] == 2


def test_check_reports_unreadable_input_as_an_error():
    reply = call("check", text="x ≤ 1")
    assert reply["ok"] is False
    assert "cannot read" in reply["error"]


def test_tutor_accepts_a_valid_alternative_next_step():
    reply = call("tutor", previous="2*x + 3 = 7", expected="2*x = 4", attempt="x = 2")

    assert reply["ok"] is True
    assert reply["result"]["accepted"] is True


def test_tutor_accepts_the_expected_intermediate_or_form():
    reply = call(
        "tutor",
        previous="(x - 3)*(x - 2) = 0",
        expected="x - 3 = 0 or x - 2 = 0",
        attempt=r"x - 3 = 0\lor x - 2 = 0",
    )

    assert reply["result"] == {
        "accepted": True,
        "verdict": "OK",
        "message": "matches the next worked step",
        "hints": [],
    }


def test_tutor_returns_the_checker_hint_for_a_wrong_step():
    reply = call("tutor", previous="2*x + 3 = 7", expected="2*x = 4", attempt="2*x = 5")

    assert reply["result"]["accepted"] is False
    assert reply["result"]["message"]


def test_steps_for_a_matrix():
    reply = call("steps", operation="det", target="[[3, 8], [4, 6]]", lower="", upper="")
    assert reply["ok"] is True
    assert reply["result"]["result"] == "-14"


def test_steps_for_a_definite_integral():
    reply = call("steps", operation="integrate", target="x^2", lower="0", upper="1")
    assert reply["result"]["result"] == "1/3"


def test_solve():
    reply = call("solve", text="x^2 - 5x + 6 = 0")
    assert reply["ok"] is True
    assert reply["result"]["answers"] == ["2", "3"]
    assert reply["result"]["kind_label"] == "Quadratic equation"
    assert [method["id"] for method in reply["result"]["methods"]][0] == "factoring"
    assert reply["result"]["steps"][0]["why"]["rule"].startswith("This is the problem")


def test_solve_with_a_chosen_method():
    reply = call("solve", text="x^2 - 5x + 6 = 0", method="formula")
    assert reply["result"]["method"] == "formula"


def test_a_formula_without_x_asks_for_the_letter():
    reply = call("solve", text="v = u + a t")
    assert reply["result"] == {"needs_letter": True, "letters": ["a", "t", "u", "v"]}


def test_a_formula_solved_for_the_chosen_letter():
    reply = call("solve", text="v = u + a t", variable="t")
    assert reply["result"]["variable"] == "t"
    assert reply["result"]["kind_label"] == "Formula, solved for t"


def test_solve_without_an_equals_sign_works_it_out():
    reply = call("solve", text="x^2 - 5x + 6")
    assert reply["ok"] is True
    assert reply["result"]["kind_label"] == "Expression"
    assert reply["result"]["method"] == "factor"
    assert reply["result"]["variable"] is None


def test_arithmetic_on_the_solve_tab():
    reply = call("solve", text=r"\frac{1}{2}+\frac{1}{3}")
    assert reply["result"]["answer_latex"] == r"\frac{5}{6}"
    assert reply["result"]["decimal"] == "0.8333333333"


def test_an_expression_with_several_letters_does_not_ask_for_one():
    reply = call("solve", text="a^2 - b^2")
    assert "needs_letter" not in reply["result"]
    assert reply["result"]["answer_text"] == "Answer: (a - b)*(a + b)"


def test_choosing_what_to_do_with_an_expression():
    reply = call("solve", text="(x + 2)^2", method="factor")
    assert reply["ok"] is False
    assert "does not apply" in reply["error"]
    reply = call("solve", text="x^2 - 9", method="simplify")
    assert reply["result"]["method"] == "simplify"


def test_a_derivative_on_the_solve_tab():
    reply = call("solve", text=r"\frac{d}{dx}\left(x^2\sin x\right)")
    assert reply["result"]["kind_label"] == "Derivative"
    assert reply["result"]["answers"] == ["x*(x*cos(x) + 2*sin(x))"]


def test_an_integral_on_the_solve_tab():
    reply = call("solve", text=r"\int x e^{x}\,dx")
    assert reply["result"]["kind_label"] == "Integral"
    assert reply["result"]["answer_latex"].endswith("+ C")
    reply = call("solve", text=r"\int_0^1 x^2\,dx")
    assert reply["result"]["answers"] == ["1/3"]
    assert reply["result"]["decimal"] == "0.3333333333"


def test_the_live_answer_for_a_calculation():
    reply = call("preview", text=r"\frac{1}{2}+\frac{1}{3}")
    assert reply["result"] == {
        "latex": r"= \frac{5}{6}",
        "decimal_latex": r"\approx 0.8333333333",
    }


def test_the_live_answer_for_an_equation():
    reply = call("preview", text="x^2-5x+6=0")
    assert reply["result"]["latex"] == r"x = 2 \quad\text{or}\quad x = 3"
    assert reply["result"]["decimal_latex"] is None


def test_the_live_answer_for_an_expression():
    assert call("preview", text="(x+2)^2")["result"]["latex"] == "= x^{2} + 4 x + 4"


@pytest.mark.parametrize(
    "text",
    [
        "",  # nothing typed yet
        "2+",  # half typed
        r"\frac{\placeholder{}}{2}",  # an empty box in the editor
        "x^2 + 1",  # nothing to do
        "7",  # already an answer
        r"\int x^2\,dx",  # integrals wait for the Solve button
        "v = u + a t",  # needs a letter to be chosen
    ],
)
def test_no_live_answer_and_no_error(text):
    reply = call("preview", text=text)
    assert reply == {"ok": True, "result": {"latex": None}}


def test_unknown_request():
    reply = call("nonsense")
    assert reply["ok"] is False
    assert "nonsense" in reply["error"]
