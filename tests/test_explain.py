from mathlint import solve
from mathlint.explain import why_for


def test_a_known_step_has_its_specific_explanation():
    why = why_for("Product rule: (uv)' = u'v + uv'")

    assert why.rule == "(uv)' = u'v + uv'."
    assert "not u'v'" in why.mistake


def test_an_unmatched_step_has_a_safe_explanation():
    why = why_for("Rewrite this in a convenient form")

    assert "checked symbolically" in why.rule
    assert why.example
    assert why.mistake


def test_every_serialized_solution_step_has_a_complete_why():
    solution = solve("x^2 - 5x + 6 = 0").to_dict()

    assert solution["steps"]
    for step in solution["steps"]:
        assert set(step["why"]) == {"rule", "example", "mistake"}
        assert all(step["why"].values())
