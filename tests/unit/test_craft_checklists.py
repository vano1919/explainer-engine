"""The craft checklists (P3b, docs/CRAFT_CURRICULUM.md): shape, sources, enforcement, and the rendered copies agree."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from explainer_engine.standards import craft
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
VIDEO_CRITERIA = ROOT / "explainer_engine/training/video_criteria.json"


def _rows():
    return [(d, c) for d in craft.departments() for c in craft.load(d)["criteria"]]


def test_the_checklists_are_consistent():
    assert craft.check() == []


def test_one_checklist_per_department_in_the_shape_of_video_criteria():
    assert set(craft.departments()) == set(craft.PREFIX)
    vc = json.loads(VIDEO_CRITERIA.read_text(encoding="utf-8"))
    base = {"id", "group", "name", "check"}
    assert base <= set(vc["criteria"][0])
    for dept in craft.departments():
        data = craft.load(dept)
        assert {"about", "criteria"} <= set(data) and data["criteria"], dept
        for c in data["criteria"]:
            assert base | {"rules", "artefact", "source", "enforced_by"} <= set(c), c.get("id")
            assert isinstance(c["rules"], list)
            assert c["check"] in {"code", "critic", "eye", "manual"}


def test_ids_are_unique_and_named_by_department():
    ids = [c["id"] for _, c in _rows()]
    assert len(ids) == len(set(ids))
    for dept, c in _rows():
        assert re.fullmatch(rf"CRAFT-{craft.PREFIX[dept]}-\d{{2}}", c["id"]), c["id"]


def test_every_row_has_a_source_and_an_enforcement():
    for _, c in _rows():
        assert craft.SOURCE.match(c["source"]), c["id"]
        assert c["enforced_by"], c["id"]
        if c["enforced_by"] != "manual" and not (ROOT / c["enforced_by"].split(":")[0]).exists():
            assert craft.PLANNED.match(c.get("planned", "")), f"{c['id']}: a future validator needs its plan phase"
        if c["check"] == "code":
            assert c["enforced_by"] != "manual", c["id"]


def test_every_cited_bp_rule_exists():
    ids = {r["id"] for r in SR.rules()}
    cited = {r for _, c in _rows() for r in c["rules"] if r.startswith("BP-")}
    assert cited and cited <= ids, sorted(cited - ids)


def test_the_skill_tables_are_rendered_copies():
    for dept in craft.departments():
        skill = ROOT / craft.load(dept)["skill"]
        text = skill.read_text(encoding="utf-8")
        got = craft.block(text, *craft.markers(dept))
        assert got is not None, f"{skill} lost its CHECKLIST markers"
        assert got.strip() == craft.render(dept).strip(), "run: python -m explainer_engine.standards.craft write"
        assert "## Sourced rules" in text.split(craft.markers(dept)[1], 1)[1], f"{skill}: a Sourced rules pointer follows"


def test_the_curriculum_lists_every_checklist_file_and_the_index_is_rendered():
    text = craft.CURRICULUM.read_text(encoding="utf-8")
    for dept in craft.departments():
        assert f"standards/craft_checklists/{dept}.json" in text, dept
    assert craft.block(text, *craft.INDEX).strip() == craft.render_index().strip()
    assert "CRAFT_CURRICULUM.md" in (ROOT / "docs/INDEX.md").read_text(encoding="utf-8")
    # the 13 conflict records and the 17 areas
    conflicts = text.split("## Conflicts with rules in force", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"^\| \d{1,2} \|", conflicts, flags=re.M)) == 13
    areas = text.split("## The 17 areas", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"^\| \d{1,2} \|", areas, flags=re.M)) == 17


def test_a_craft_id_has_one_home_its_json():
    for folder in (ROOT / "docs", ROOT / ".claude"):
        for p in folder.rglob("*.md"):
            text = p.read_text(encoding="utf-8")
            for dept in craft.departments():
                begin, end = craft.markers(dept)
                if begin in text:
                    head, rest = text.split(begin, 1)
                    text = head + rest.split(end, 1)[1]
            assert not re.search(r"^\|\s*CRAFT-", text, flags=re.M), f"{p} defines a CRAFT id outside the rendered copy"


def test_the_new_craft_rules_are_hypotheses_named_by_their_checklist_row():
    new = [r for r in SR.rules() if r.get("craft")]
    assert len(new) == 25 and {r["id"] for r in new} == {f"BP-{n}" for n in range(114, 139)}
    rows = {c["id"]: c for _, c in _rows()}
    for r in new:
        assert r["status"] == "hypothesis" and r["severity"] == "REVIEW", r["id"]
        # a rule names its checklist row; until its validator exists it says so in `planned`; the modules that already read it are in
        # `enforced_by` too (P3: BP-114, BP-115, BP-135 once register_lint, syllables and variant_plan landed)
        refs = [e for e in r["enforced_by"] if re.fullmatch(r"[\w/]+\.json:CRAFT-[A-Z]+-\d+", e)]
        assert len(refs) == 1, r["id"]
        assert all((ROOT / e.split(":")[0]).exists() for e in r["enforced_by"]), r["id"]  # a module that reads the rule exists
        cid = refs[0].split(":", 1)[1]
        assert r["id"] in rows[cid]["rules"], f"{r['id']} is not cited by its checklist row {cid}"
    # dramatisability caps are the Blueprint's house numbers, never attributed to McKee or Katz
    lanes = SR.rule("BP-127")
    assert "NOT taken from McKee or Katz" in lanes["statement"]
    assert all(s["type"] == "A" and not s["title"].startswith(("McKee", "Katz", "Story")) for s in lanes["sources"])


def test_the_conflicting_rules_stay_in_force():
    assert SR.T("BP-50", "lufs") == -14.0
    assert SR.T("BP-01", "wpm_target") == 170
    assert SR.T("BP-53", "depth_db") == [6.0, 12.0]
    assert SR.T("BP-30", "focal_shift_max") == 0.1
    assert SR.T("BP-36", "gap_fail_s") == 15.0
    assert SR.T("BP-29", "safe_y_px") == [288, 1248]


def test_the_check_catches_a_broken_row(monkeypatch):
    real = craft.load

    def broken(dept):
        data = json.loads(json.dumps(real(dept)))
        if dept == "sound":
            data["criteria"][0]["source"] = "a blog I remember"
            data["criteria"][0]["rules"] = ["BP-999"]
            data["criteria"][1]["enforced_by"] = "explainer_engine/nope.py"
            data["criteria"][1].pop("planned", None)
            data["criteria"][2]["id"] = data["criteria"][3]["id"]
        return data

    monkeypatch.setattr(craft, "load", broken)
    details = " ".join(f["detail"] for f in craft.check())
    assert "source is not" in details and "BP-999" in details and "does not exist" in details
    assert "duplicate id" in details and "differs from the JSON" in details


def test_the_cli_check():
    out = subprocess.run([sys.executable, "-m", "explainer_engine.standards.craft", "check"], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
