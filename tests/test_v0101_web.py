"""The v0.10.1 web app: a mobile-first shell around the notebook.

These pin down the promises of the redesign that a quiet edit could undo: the
notebook stays, the app fits a phone, and every page file ships.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "style.css").read_text(encoding="utf-8")
EDITOR = (WEB / "editor.js").read_text(encoding="utf-8")
KEYPAD = (WEB / "keypad.js").read_text(encoding="utf-8")


def test_the_notebook_stays_ruled_with_a_red_margin_and_numbered_lines():
    assert 'class="notebook"' in HTML
    assert "--margin-rule" in STYLE
    assert "content: counter(line);" in STYLE
    # the Solve, Check and Work out notebooks
    assert HTML.count('<article class="notebook">') == 3


def test_the_page_is_ready_for_a_phone():
    assert "viewport-fit=cover" in HTML
    assert "env(safe-area-inset-bottom" in STYLE
    assert '<meta name="theme-color"' in HTML
    # tabs at the bottom of a phone, down the side of a wide screen
    assert 'class="navbar"' in HTML
    assert 'role="tablist"' in HTML
    assert "@media (min-width: 900px)" in STYLE


def test_the_keypad_docks_on_a_phone_and_hides_again():
    assert "body.keypad-open .keypad-slot" in STYLE
    assert "function openKeypad(field)" in APP
    assert "function closeKeypad()" in APP
    assert 'setAttribute("aria-label", t("keypad.hide"))' in KEYPAD


def test_the_enter_key_says_what_it_does():
    assert 'if (solveSheet.contains(field)) return t("keypad.enterSolve");' in APP
    assert "refresh()" in KEYPAD


def test_checked_lines_are_marked_in_the_notebook_margin():
    assert "setMarks(verdicts)" in EDITOR
    assert "sheet.setMarks(verdicts)" in APP
    for verdict in ("ok", "wrong", "warning", "unsure"):
        assert f'.math-line[data-mark="{verdict}"]::after' in STYLE


def test_light_and_dark_themes_can_be_chosen():
    assert "@media (prefers-color-scheme: dark)" in STYLE
    assert ':root:not([data-theme="light"])' in STYLE
    assert ':root[data-theme="dark"]' in STYLE
    for value in ("system", "light", "dark"):
        assert f'name="theme" value="{value}"' in HTML
    assert '"mathlint:theme"' in HTML and '"mathlint:theme"' in APP


def test_formulas_cannot_widen_the_page_on_a_phone():
    # KaTeX's hidden MathML is absolutely positioned; inside a sideways
    # scroller it once escaped and zoomed the whole page out on phones
    assert ".katex { position: relative; }" in STYLE


def test_every_solve_example_belongs_to_a_group():
    examples = json.loads((WEB / "solve-examples.json").read_text(encoding="utf-8"))
    groups = {example["group"] for example in examples}
    assert groups == {"Equations", "Systems and formulas", "Calculator", "Inequalities", "Calculus"}


def test_every_icon_the_page_uses_is_drawn():
    defined = set(re.findall(r'<symbol id="i-([a-z-]+)"', HTML))
    used = set(re.findall(r'href="#i-([a-z-]+)"', HTML + EDITOR + KEYPAD))
    used |= set(re.findall(r'icon\("([a-z-]+)"\)', APP))
    assert used <= defined, used - defined


def test_every_page_file_is_stamped_by_the_build():
    build = (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
    for page_file in WEB.iterdir():
        if page_file.suffix in {".js", ".json", ".css"}:
            assert f'"{page_file.name}"' in build, page_file.name
