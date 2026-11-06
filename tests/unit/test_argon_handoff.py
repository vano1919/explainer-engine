"""The Argon handoff branch (docs/handoff/argon_2026-11-06): every material row has its picture on the branch, within the size
budget, with a verdict and a reason; the documents the prompt names exist; no secret-looking text is in the handoff tree."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "docs" / "handoff" / "argon_2026-11-06"
MAX_IMAGE_BYTES = 600_000
MAX_TOTAL_BYTES = 15_000_000
VERDICTS = {"good", "bad", "mixed"}
NAMED_BY_PROMPT = ["README.md", "PRS.md", "PLANS.md", "MATERIAL.md", "LTX_HELPERS.md", "REUSE.md", "OPEN_QUESTIONS.md",
                   "ARGON_PROMPT.md", "README_ka.md"]


def _rows() -> list[dict]:
    doc = json.loads((HANDOFF / "MATERIAL.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "argon_material/1"
    return doc["rows"]


def test_every_material_row_has_a_verdict_a_reason_and_its_picture():
    rows = _rows()
    assert len(rows) >= 15
    seen = set()
    for r in rows:
        assert r["set"] not in seen, r["set"]
        seen.add(r["set"])
        assert r["verdict"] in VERDICTS, r["set"]
        for key in ("route", "cost", "hf_path", "made_for", "reason", "source", "not_verified"):
            assert str(r.get(key) or "").strip(), f"{r['set']}: {key} is empty"
        if r["path"]:
            f = HANDOFF / r["path"]
            assert f.is_file(), f"{r['set']}: {f} is missing"
            assert f.suffix in (".jpg", ".png")
            assert f.stat().st_size <= MAX_IMAGE_BYTES, f"{f.name} is {f.stat().st_size} bytes"
        else:
            assert str(r.get("no_image_reason") or "").strip(), f"{r['set']}: no picture and no reason"


def test_images_fit_the_budget_and_none_is_orphaned():
    images = sorted((HANDOFF / "images").glob("*"))
    assert sum(p.stat().st_size for p in images) <= MAX_TOTAL_BYTES
    used = {Path(r["path"]).name for r in _rows() if r["path"]}
    assert {p.name for p in images} == used


def test_material_page_lists_every_set_and_picture():
    md = (HANDOFF / "MATERIAL.md").read_text(encoding="utf-8")
    for r in _rows():
        assert f"## {r['set']} " in md, r["set"]
        if r["path"]:
            assert r["path"] in md


def test_documents_named_by_the_prompt_exist_and_the_prompt_names_them():
    prompt = (HANDOFF / "ARGON_PROMPT.md").read_text(encoding="utf-8")
    for name in NAMED_BY_PROMPT:
        assert (HANDOFF / name).is_file(), name
    for name in ("README.md", "PRS.md", "PLANS.md", "MATERIAL.md", "LTX_HELPERS.md", "REUSE.md", "OPEN_QUESTIONS.md"):
        assert name in prompt, name
    assert "<branch url>" not in prompt


def test_plans_named_in_plans_md_are_copied():
    text = (HANDOFF / "PLANS.md").read_text(encoding="utf-8")
    for name in re.findall(r"`((?:[A-Z0-9_]+(?:_v\d)?(?:_ka)?)\.md)`", text):
        if (HANDOFF / "plans" / name).exists() or (HANDOFF / name).exists():
            continue
        assert name in ("HANDOFF_STEP1/3/4.md",), f"PLANS.md names {name}, which is not on the branch"


def test_no_secret_looking_text_in_the_handoff_tree():
    pattern = re.compile(r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|rpa_[A-Za-z0-9]{10,}|api[_-]?key\s*[:=]\s*[A-Za-z0-9]{12,}|bearer\s+[A-Za-z0-9]{20,})", re.I)
    for p in HANDOFF.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".json", ".txt"):
            assert not pattern.search(p.read_text(encoding="utf-8")), p
