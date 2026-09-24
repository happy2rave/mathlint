"""Which of a photo's readings the notebook can read."""

import json

import pytest

from mathlint.readable import readable
from mathlint.web_api import handle


@pytest.mark.parametrize(
    "latex",
    [
        r"\frac{x+1}{2}=3",
        r"x=2\text{ or }x=-3",
        r"2x+3y=7",
        r"\lim_{x\to 0}\frac{\sin x}{x}",
        r"y''+4y=0",
        r"\begin{pmatrix}1&2\\3&4\end{pmatrix}",
        r"=x^{2}+1",
        r"\int x^{2}\,dx",
    ],
)
def test_the_notebook_reads_what_students_write(latex):
    assert readable(latex)


@pytest.mark.parametrize("latex", ["", "=", r"\frac{1}{", "x+=", "()"])
def test_a_slip_that_makes_nonsense_is_not_read(latex):
    assert not readable(latex)


def test_the_page_gets_the_first_readable_reading():
    reply = json.loads(handle("readable", json.dumps({"latex": ["x+=", "x+1=2", "x=1"]})))
    assert reply == {"ok": True, "result": {"index": 1}}
    reply = json.loads(handle("readable", json.dumps({"latex": ["x+="]})))
    assert reply["result"] == {"index": None}
