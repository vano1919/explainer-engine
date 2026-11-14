"""The vendored HyperFrames skills and their entry skill (2026-11-14): licence and source kept, the pin the entry skill names is the
pin the overlay driver uses, and the vendored text is not auto-loaded as Claude skills."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "hyperframes-skills"
ENTRY = ROOT / ".claude" / "skills" / "hyperframes-lanes" / "SKILL.md"


def test_vendored_skills_keep_licence_source_and_no_media():
    assert "Apache License" in (VENDOR / "LICENSE").read_text(encoding="utf-8")
    readme = (VENDOR / "README.md").read_text(encoding="utf-8")
    assert re.search(r"commit `[0-9a-f]{40}`", readme)
    for name in ("hyperframes", "hyperframes-cli", "hyperframes-registry"):
        assert (VENDOR / name / "SKILL.md").exists(), name
    assert not (VENDOR / "media-use").exists()  # HeyGen paid media stays out
    allowed = {".md", ".txt", ".mjs", ""}
    assert not [p for p in VENDOR.rglob("*") if p.is_file() and p.suffix not in allowed]


def test_vendored_skills_are_not_claude_skills():
    skills = ROOT / ".claude" / "skills"
    for name in ("hyperframes", "hyperframes-cli", "hyperframes-registry"):
        assert not (skills / name).exists(), name


def test_entry_skill_names_the_driver_pin_and_the_privacy_rules():
    pin = json.loads((ROOT / "explainer_engine/overlay/hyperframes/package.json").read_text(encoding="utf-8"))["dependencies"]["hyperframes"]
    text = ENTRY.read_text(encoding="utf-8")
    assert f"hyperframes@{pin}" in text
    for must in ("HYPERFRAMES_NO_TELEMETRY=1", "DO_NOT_TRACK=1", "audio --quality best", "snapshot --describe", "60 %"):
        assert must in text, must
    from explainer_engine.overlay import hyperframes as hf
    assert hf.HF_VERSION == pin
