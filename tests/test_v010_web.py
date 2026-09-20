from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (ROOT / "web" / "style.css").read_text(encoding="utf-8")


def test_learning_controls_are_present():
    assert "Reveal next step" in APP
    assert "Try the next step" in APP
    assert "Show all steps" in APP
    assert "Step ${Math.min(shown, steps.length)} of ${steps.length}" in APP
    assert "function tutorText(value)" in APP
    assert "\\lor" in APP
    assert 'engine.call("tutor"' in APP


def test_every_step_can_show_why():
    assert 'summary.textContent = "Why?"' in APP
    assert '["Common mistake", why.mistake]' in APP


def test_step_animation_respects_reduced_motion():
    assert "@media (prefers-reduced-motion: no-preference)" in STYLE
    assert ".worked-step.step-enter" in STYLE
