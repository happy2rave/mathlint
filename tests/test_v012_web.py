"""The v0.12 web app: reading math from a photo or from the pad, offline.

The recognizer (``web/recognizer/``) is a model of about 4 MB and the code that
runs it. It is downloaded the first time the camera or the pad opens, never at
install, and kept offline from then on.
"""

import gzip
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
RECOGNIZER = WEB / "recognizer"


def _scripts_module(name: str):
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module  # dataclasses look their module up
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))


def test_the_recognizer_is_not_downloaded_at_install(tmp_path):
    build = _scripts_module("build_web")
    (tmp_path / "sw.js").write_text((WEB / "sw.js").read_text(encoding="utf-8"), encoding="utf-8")
    for name in ("index.html", "app.js", "recognizer/recognizer.bin", "recognizer/model.js"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert build.write_service_worker(tmp_path, "abc") == ["./", "app.js", "index.html"]


def test_the_recognizer_is_kept_offline_once_it_is_used():
    worker = (WEB / "sw.js").read_text(encoding="utf-8")
    assert '"/recognizer/"' in worker
    assert "cache.put(request, response.clone())" in worker
    # a new build fetches its own model, not the last one from the HTTP cache
    assert 'cache: "no-cache"' in worker


def test_the_recognizer_fits_its_budgets(tmp_path):
    budget = _scripts_module("budget")
    code = sum(len(gzip.compress(path.read_bytes(), 9)) for path in RECOGNIZER.glob("*.js"))
    assert code / 1024 <= budget.RECOGNIZER_KB
    model = RECOGNIZER / "recognizer.bin"
    if model.exists():
        assert model.stat().st_size / 1e6 <= budget.MODEL_MB
    (tmp_path / "recognizer").mkdir()
    (tmp_path / "recognizer" / "a.js").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "recognizer" / "recognizer.bin").write_bytes(b"\0" * 1_500_000)
    assert 0 < budget.recognizer_kb(tmp_path) < 1
    assert budget.model_mb(tmp_path) == 1.5


def test_the_recognizer_runs_in_its_own_thread():
    index = (RECOGNIZER / "index.js").read_text(encoding="utf-8")
    assert 'new Worker(new URL("./worker.js", import.meta.url), { type: "module" })' in index
