from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_public_license_and_required_notice_are_present():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "PolyForm Noncommercial License 1.0.0" in license_text
    assert "Required Notice: mathlint Copyright (c) 2026 happy2rave." in license_text
    assert "https://buymeacoffee.com/happy2rave" in license_text


def test_package_metadata_does_not_claim_osi_approval():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'license = "PolyForm-Noncommercial-1.0.0"' in metadata
    assert "License :: OSI Approved" not in metadata
    assert "License :: Other/Proprietary License" in metadata


def test_third_party_content_keeps_its_separate_license():
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "CC BY 4.0" in notices
    assert "does not replace or restrict" in notices
