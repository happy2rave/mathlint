"""The recognizer's vocabulary: the LaTeX it may write, one token at a time.

The recognizer's output goes straight into the notebook's editor (MathLive), so
it writes the compact LaTeX MathLive itself writes. Every visual form has one
spelling: a power always has braces (``x^{2}``), brackets are ``\\left(`` and
``\\right)``, "or" between answers is ``\\text{ or }``. One spelling per picture
is what lets a small model learn it.
"""

from __future__ import annotations

import re

SPECIAL = ["<pad>", "<s>", "</s>"]
PAD, START, END = 0, 1, 2

DIGITS = list("0123456789")
LOWER = list("abcdefghijklmnopqrstuvwxyz")
UPPER = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
PUNCTUATION = list("+-=<>()[],;.!|'") + ["^", "_", "{", "}", "&"]
COMMANDS = [
    r"\frac",
    r"\sqrt",
    r"\left(",
    r"\right)",
    r"\left|",
    r"\right|",
    r"\left[",
    r"\right]",
    r"\cdot",
    r"\times",
    r"\div",
    r"\pm",
    r"\le",
    r"\ge",
    r"\ne",
    r"\to",
    r"\infty",
    r"\pi",
    r"\theta",
    r"\alpha",
    r"\beta",
    r"\lambda",
    r"\mu",
    r"\varphi",
    r"\Delta",
    r"\int",
    r"\lim",
    r"\sin",
    r"\cos",
    r"\tan",
    r"\cot",
    r"\sec",
    r"\csc",
    r"\ln",
    r"\log",
    r"\exp",
    r"\arcsin",
    r"\arccos",
    r"\arctan",
    r"\sinh",
    r"\cosh",
    r"\tanh",
    r"\prime",
    r"\sim",
    r"\Rightarrow",
    r"\text{ or }",
    r"\,",
    r"\begin{pmatrix}",
    r"\end{pmatrix}",
    r"\\",
]

TOKENS: list[str] = SPECIAL + DIGITS + LOWER + UPPER + PUNCTUATION + COMMANDS
INDEX = {token: index for index, token in enumerate(TOKENS)}

# the longest command first, so \left( wins over \left and \sinh over \sin
_COMMAND = re.compile(
    "|".join(re.escape(command) for command in sorted(COMMANDS, key=len, reverse=True))
)


def normalize(latex: str) -> str:
    """The one spelling of ``latex`` the recognizer learns."""
    text = latex.strip()
    text = text.replace(r"\leq", r"\le").replace(r"\geq", r"\ge").replace(r"\neq", r"\ne")
    text = re.sub(r"\\text\{\s*or\s*\}", r"\\text{ or }", text)
    text = re.sub(r"\\dfrac|\\tfrac", r"\\frac", text)
    # x^2 -> x^{2}, x_1 -> x_{1}: a script is always braced
    text = re.sub(r"([\^_])([0-9A-Za-z])", r"\1{\2}", text)
    return text


def tokenize(latex: str) -> list[str]:
    """``latex`` as vocabulary tokens; a ValueError names anything outside it."""
    text = normalize(latex)
    tokens: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "\\":
            match = _COMMAND.match(text, index)
            if not match:
                raise ValueError(f"not in the vocabulary: {text[index : index + 12]!r}")
            tokens.append(match.group(0))
            index = match.end()
            continue
        if char not in INDEX:
            raise ValueError(f"not in the vocabulary: {char!r}")
        tokens.append(char)
        index += 1
    return tokens


def encode(tokens: list[str]) -> list[int]:
    return [START, *(INDEX[token] for token in tokens), END]


def decode(ids) -> str:
    """Token ids back to LaTeX; stops at the end token."""
    out: list[str] = []
    for identifier in ids:
        identifier = int(identifier)
        if identifier == END:
            break
        if identifier in (PAD, START):
            continue
        out.append(TOKENS[identifier])
    return join(out)


def join(tokens: list[str]) -> str:
    """Tokens as LaTeX: a space only where a command would swallow a letter."""
    text = ""
    for token in tokens:
        if text and re.search(r"\\[A-Za-z]+$", text) and re.match(r"[A-Za-z]", token):
            text += " "
        text += token
    return text
