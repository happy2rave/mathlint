"""The formulas the recognizer learns from, and the vocabulary it writes them in."""

import random
import re

import pytest

from mathrec import formulas, vocab


def _reads(latex: str) -> bool:
    """Whether mathlint's own readers understand the line, as the notebook would:
    a matrix, a limit, a differential equation, or relations between expressions."""
    from mathlint.parse.latex import latex_to_plain
    from mathlint.parse.plain import parse_expression
    from mathlint.steps import parse_matrix
    from mathlint.steps.limits import looks_like_limit, parse_limit
    from mathlint.steps.odes import looks_like_ode, parse_ode

    try:
        if latex.startswith(r"\sim"):  # a row-reduction step: the matrix after it
            latex = latex[len(r"\sim") :]
        if latex.startswith(r"\begin{pmatrix}"):
            parse_matrix(latex)
            return True
        if looks_like_limit(latex):
            return parse_limit(latex) is not None
        if looks_like_ode(latex):
            parse_ode(latex)
            return True
        plain = latex_to_plain(latex)
        for side in re.split(r"=>|<=>|=|<|>|≤|≥|≠|\bor\b|;", plain.lstrip("=")):
            if side.strip():
                parse_expression(side)
        return True
    except Exception:
        return False


def test_tokens_are_unique_and_specials_come_first():
    assert len(vocab.TOKENS) == len(set(vocab.TOKENS))
    assert vocab.TOKENS[:3] == ["<pad>", "<s>", "</s>"]
    assert len(vocab.TOKENS) < 160


def test_one_spelling_for_one_picture():
    assert vocab.normalize("x^2+y_1") == "x^{2}+y_{1}"
    assert vocab.normalize(r"x\leq 3") == r"x\le 3"
    assert vocab.normalize(r"x=1\text{or}x=2") == r"x=1\text{ or }x=2"


def test_tokenize_takes_the_longest_command():
    assert vocab.tokenize(r"\sinh x") == [r"\sinh", "x"]
    assert vocab.tokenize(r"\left(x\right)^{2}") == [r"\left(", "x", r"\right)", "^", "{", "2", "}"]
    with pytest.raises(ValueError):
        vocab.tokenize(r"\sum x")


def test_decode_undoes_encode():
    for latex in [r"\sin x+\frac{1}{2}", r"\lim_{x\to 0}\frac{\sin x}{x}", r"\int x^{2}\,dx"]:
        tokens = vocab.tokenize(latex)
        again = vocab.decode(vocab.encode(tokens))
        assert vocab.tokenize(again) == tokens


def test_every_kind_is_sampled_and_tokenizes():
    rng = random.Random(1)
    for kind in formulas.KINDS:
        for _ in range(50):
            vocab.tokenize(formulas.sample(rng, kind))


def test_the_corpus_is_deterministic():
    assert formulas.corpus(20, seed=7) == formulas.corpus(20, seed=7)
    assert formulas.corpus(20, seed=7) != formulas.corpus(20, seed=8)


def test_mathlint_reads_what_the_recognizer_learns():
    lines = formulas.corpus(800, seed=3)
    unread = [line for line in lines if not _reads(line)]
    assert len(unread) / len(lines) < 0.01, unread[:10]
