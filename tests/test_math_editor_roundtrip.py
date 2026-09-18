"""Text typed in "Type as text" mode is moved into the math editor as LaTeX.

The page converts it with MathLive's AsciiMath reader (plus a little help), so
the LaTeX below is exactly what the browser produced. Each pair must mean the
same thing to mathlint, or switching modes would change a student's working.
"""

import pytest
import sympy as sp

from mathlint.document import parse_document
from mathlint.parse.plain import parse_expression

EXPRESSIONS = [
    ("d/dx [x^2 sin x]", r"\frac{d}{\differentialD x }\left(x^{2}\sin x\right)"),
    ("2x sin x + x^2 cos x", r"2x\sin x+x^{2}\cos x"),
    ("int x e^x dx", r"\int xe^{x}\differentialD x "),
    ("x e^x - int e^x dx", r"xe^{x}-\int e^{x}\differentialD x "),
    ("ln|x| + e^(2x)", r"\ln |x|+e^{2x}"),
    ("sin^2(x) + cos^2 x", r"\sin ^{2}\left(x\right)+\cos ^{2}x"),
    ("int_0^1 x^2 dx", r"\int _{0}^{1}x^{2}\differentialD x "),
    ("1/(x^2+1)", r"\frac{1}{x^{2}+1}"),
]


@pytest.mark.parametrize(("text", "latex"), EXPRESSIONS)
def test_expression_means_the_same(text, latex):
    assert parse_expression(latex).expr == parse_expression(text).expr


def test_solution_list_means_the_same():
    typed = parse_document("x^2 - 5x + 6 = 0\nx = 2 or x = 3")
    edited = parse_document("x^{2}-5x+6=0\n" r"x=2\lor x=3")
    assert typed.lines[1].solutions == edited.lines[1].solutions


def test_matrix_means_the_same():
    typed = parse_document(
        "[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]\n~ [[1, 1/2, -1/2], [-3, -1, 2], [-2, 1, 2]]"
    )
    edited = parse_document(
        r"\begin{pmatrix}2&1&-1\\-3&-1&2\\-2&1&2\end{pmatrix}"
        "\n"
        r"\sim \begin{pmatrix}1&\frac{1}{2}&-\frac{1}{2}\\-3&-1&2\\-2&1&2\end{pmatrix}"
    )
    assert [line.matrix for line in typed.lines] == [line.matrix for line in edited.lines]
    assert edited.lines[1].arrow == "~"
    assert edited.lines[1].matrix[0, 1] == sp.Rational(1, 2)
