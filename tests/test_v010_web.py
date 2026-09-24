import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
# since v0.11 the page's words live in a dictionary, named by key
WORDS = json.loads((ROOT / "web" / "locales" / "en.json").read_text(encoding="utf-8"))
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")


def test_learning_controls_are_present():
    assert WORDS["steps.reveal"] == "Reveal next step" and 't("steps.reveal")' in APP
    assert WORDS["steps.try"] == "Try the next step" and 't("steps.try")' in APP
    assert WORDS["steps.showAll"] == "Show all steps" and 't("steps.showAll")' in APP
    assert WORDS["steps.progress"] == "Step {shown} of {total}" and 't("steps.progress"' in APP
    assert "function tutorText(value)" in APP
    assert "\\lor" in APP
    assert 'engine.call("tutor"' in APP


def test_every_step_can_show_why():
    assert 'summary.textContent = t("steps.why")' in APP
    assert '["mistake", why.mistake]' in APP
    assert WORDS["steps.mistake"] == "Common mistake"


def test_step_animation_respects_reduced_motion():
    assert "@media (prefers-reduced-motion: no-preference)" in STYLE
    assert ".worked-step.step-enter" in STYLE


def test_practice_problems_can_be_loaded_into_the_solver():
    assert WORDS["practice.title"] == "Practice this skill" and 't("practice.title")' in APP
    assert "solveSheet.setLines(lines)" in APP
    assert "solve(problem.method || null)" in APP


def test_open_textbook_exercises_are_loaded_with_visible_attribution():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert "Open textbook problems" in html
    assert "CC BY 4.0" in html
    assert 'fetch("textbook-problems.json")' in APP


def test_support_link_is_visible_and_keyboard_accessible():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert "https://buymeacoffee.com/happy2rave" in html
    assert "Buy me a coffee" in html
    assert 'aria-label="Buy me a coffee (opens in a new tab)"' in html
    assert ".support-link:focus-visible" in STYLE
