"""Every equation in the bank must be classified, solved with steps, and verified."""

import pytest
import sympy as sp

import mathlint

from .bank import BANK


def same_values(found, expected):
    if len(found) != len(expected):
        return False
    remaining = [sp.nsimplify(value) if isinstance(value, float) else value for value in expected]
    for value in found:
        match = next(
            (other for other in remaining if abs(sp.N(value - other, 30)) < 1e-12),
            None,
        )
        if match is None:
            return False
        remaining.remove(match)
    return True


@pytest.mark.parametrize(("text", "kind", "expected"), BANK, ids=[entry[0] for entry in BANK])
def test_bank(text, kind, expected):
    solution = mathlint.solve(text)
    assert solution.kind == kind
    assert len(solution.steps) >= 2
    if expected == "all":
        assert solution.everything
    elif expected == "none":
        assert solution.answers == []
        assert not solution.everything
    else:
        assert same_values(solution.answers, expected), solution.to_text()
