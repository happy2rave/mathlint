import json
from pathlib import Path

from mathlint import solve

PROBLEMS = json.loads(
    (Path(__file__).resolve().parent.parent / "web" / "textbook-problems.json").read_text(
        encoding="utf-8"
    )
)


def test_every_openstax_problem_has_attribution_metadata_and_a_worked_solution():
    assert len(PROBLEMS) >= 10
    for problem in PROBLEMS:
        assert problem["book"].startswith("OpenStax ")
        assert problem["section"]
        assert problem["exercise"]
        assert problem["source"].startswith("https://openstax.org/books/")
        solution = solve(problem["text"], method=problem["method"] or None)
        assert solution.steps
        assert solution.summary
