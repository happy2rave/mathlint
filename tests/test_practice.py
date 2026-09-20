import pytest

from mathlint.practice import practice_for
from mathlint.solve import solve


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ("2x + 3 = 9", "linear"),
        ("x^2 - 5x + 6 = 0", "quadratic"),
        ("x + y = 5; x - y = 1", "linear-system"),
        ("x^2 - x - 6 >= 0", "polynomial-inequality"),
        ("d/dx (x^2 sin x)", "derivative"),
        ("x^2 + 5x + 6", "expression"),
    ],
)
def test_practice_matches_the_solved_skill_and_every_problem_runs(source, kind):
    result = solve(source).to_dict()

    assert result["kind"] == kind
    practice = practice_for(source, result)

    assert [problem["label"] for problem in practice] == ["Warm-up", "Another one", "Challenge"]
    assert len({problem["text"] for problem in practice}) == 3
    for problem in practice:
        solved = solve(problem["text"], method=problem["method"] or None)
        assert solved.steps


def test_practice_is_reproducible_but_changes_with_the_source():
    first = solve("2x + 3 = 9").to_dict()
    second = solve("4x - 7 = 5").to_dict()

    assert practice_for("2x + 3 = 9", first) == practice_for("2x + 3 = 9", first)
    assert practice_for("2x + 3 = 9", first) != practice_for("4x - 7 = 5", second)
