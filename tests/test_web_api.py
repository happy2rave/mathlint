import json

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


def test_solve_with_a_chosen_method():
    reply = call("solve", text="x^2 - 5x + 6 = 0", method="formula")
    assert reply["result"]["method"] == "formula"


def test_solve_without_an_equals_sign_explains_itself():
    reply = call("solve", text="x^2 - 5x + 6")
    assert reply["ok"] is False
    assert "'=' sign" in reply["error"]


def test_unknown_request():
    reply = call("nonsense")
    assert reply["ok"] is False
    assert "nonsense" in reply["error"]
