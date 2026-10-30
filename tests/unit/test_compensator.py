"""The visual compensator (explainer_engine/edit/visual_compensator.py, docs/COMPENSATOR.md): the catalogue, the twelve archetypes
rendered free from a demo job, the planner's checks across items and the CN-15 contract side."""

from __future__ import annotations

import ast
import copy
import io
import json
import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core import contracts as C
from explainer_engine.edit import hud, tableau
from explainer_engine.edit import visual_compensator as VC
from explainer_engine.maps import draw as D
from explainer_engine.standards import sourced_rules as SR
from tests.unit import _comp

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def job(tmp_path_factory):
    base = tmp_path_factory.mktemp("comp_job")
    return base, _comp.build(base)


def rules(findings, severity=None):
    return {f["rule"] for f in findings if severity is None or f["severity"] == severity}


def blocks(*rows):
    return [{"archetype_id": a, "start_s": s, "end_s": e} for a, s, e in rows]


# --- the catalogue ------------------------------------------------------------------------------------------------------------------

def test_the_catalogue_is_the_twelve_of_the_doc_table():
    doc = (ROOT / "docs" / "COMPENSATOR.md").read_text(encoding="utf-8")
    table = re.findall(r"^\| (\d+) \| `([A-Z0-9_]+)` \| (MAP|COMPENSATOR) \| (\w+) \|", doc, re.M)
    assert [(int(n), a, lane, fam) for n, a, lane, fam in table] == [
        (a["number"], a["id"], a["lane"], a["family"]) for a in VC.catalogue()["archetypes"]]
    assert len(VC.ids()) == 12 and len(set(VC.ids())) == 12
    assert [a["id"] for a in VC.catalogue()["archetypes"] if a["pure_map"]] == VC.ids()[:4]
    assert {VC.lane_of(i) for i in VC.ids()[:4]} == {"MAP"} and {VC.lane_of(i) for i in VC.ids()[4:]} == {"COMPENSATOR"}
    assert {a["family"] for a in VC.catalogue()["archetypes"]} == set(VC.FAMILIES)
    assert all(a["free"] for a in VC.availability())


def test_every_archetype_has_a_module_and_the_demo_a_spec_for_each():
    for a in VC.ids():
        assert VC._module(a) in ("map", "hud", "tableau")
    assert sorted(_comp.ORDER) == sorted(VC.ids())
    with pytest.raises(KeyError):
        VC.archetype("NOT_AN_ARCHETYPE")


# --- the demo job: everything renders, free --------------------------------------------------------------------------------------------

def test_the_demo_job_has_no_finding_above_info(job):
    base, manifest = job
    found = VC.check(manifest, base)
    assert [f for f in found if f["severity"] != "INFO"] == [], found


def test_all_twelve_archetypes_render_a_frame_of_their_own(job):
    base, manifest = job
    seen = {}
    for r in VC.items_of(manifest, base):
        it, spec = r["item"], r["spec"]
        n = it["duration_frames"]
        im = VC.render_item_frame(spec, r["spine"], it["trigger_word_index"], n, n - 2, 1, base)
        assert im.size == (spec["width"], spec["height"])
        assert im.mode == ("RGBA" if spec["archetype_id"] == "ORDER_OF_BATTLE_TELEMETRY_HUD" else "RGB")
        seen[spec["archetype_id"]] = D.png_bytes(im)
    assert len(seen) == 12 and len(set(seen.values())) == 12


def test_a_frame_is_the_same_bytes_in_a_chunked_render(job):
    base, manifest = job
    for r in VC.items_of(manifest, base):
        it, spec = r["item"], r["spec"]
        args = (spec, r["spine"], it["trigger_word_index"], it["duration_frames"])
        n = it["duration_frames"]
        first = [D.png_bytes(VC.render_item_frame(*args, f, 1, base)) for f in (n // 3, n - 1)]
        again = [D.png_bytes(VC.render_item_frame(*args, f, 1, base)) for f in (n - 1, n // 3)]
        assert first == again[::-1], spec["archetype_id"]


def test_a_changing_frame_changes_and_the_telemetry_overlay_is_transparent(job):
    base, manifest = job
    for r in VC.items_of(manifest, base):
        it, spec = r["item"], r["spec"]
        n = it["duration_frames"]
        a = np.asarray(VC.render_item_frame(spec, r["spine"], it["trigger_word_index"], n, 4, 1, base))
        b = np.asarray(VC.render_item_frame(spec, r["spine"], it["trigger_word_index"], n, n - 2, 1, base))
        assert (a != b).any(), f"{spec['archetype_id']} does not move"
        if spec["archetype_id"] == "ORDER_OF_BATTLE_TELEMETRY_HUD":
            assert b[..., 3].min() == 0 and b[..., 3].max() > 0


def test_the_cli_checks_renders_and_measures(job, tmp_path, capsys):
    base, manifest = job
    path = base / "visual" / "visual_comp_manifest.json"
    assert VC.main(["check", str(path), "--base", str(base)]) == 0
    assert VC.main(["render", str(path), "it05", str(tmp_path), "--base", str(base), "--frames", "0:2", "--ss", "1"]) == 0
    assert len(list(tmp_path.glob("*.png"))) == 2
    m = VC.measure(manifest, base, size=(160, 90), frames=1)
    assert set(m["s_per_frame"]) == set(VC.ids()) and all(v >= 0 for v in m["s_per_frame"].values())
    assert VC.main([]) == 2


# --- the payloads ------------------------------------------------------------------------------------------------------------------------

def test_a_dossier_card_has_no_stamp(job):
    base, manifest = job
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "PRIMARY_SOURCE_DOSSIER_CARD")
    spec = copy.deepcopy(row["spec"])
    assert VC.payload_findings(spec, base) == []
    spec["payload"]["stamp"] = "HISTORICAL FACT"
    found = VC.payload_findings(spec, base)
    assert rules(found) == {"CMP-15"} and rules(found, "FAIL") == {"CMP-15"}
    spec["payload"].pop("stamp")
    spec["payload"]["stamps"] = ["COUNTERFACTUAL"]
    assert rules(VC.payload_findings(spec, base)) == {"CMP-15"}


def test_a_broken_payload_is_a_fail_not_a_crash(job):
    base, manifest = job
    for r in VC.items_of(manifest, base):
        spec = copy.deepcopy(r["spec"])
        spec["payload"] = {"nonsense": 1}
        found = VC.check_item(spec, r["spine"], r["item"]["trigger_word_index"], r["item"]["duration_frames"], base)
        assert "FAIL" in {f["severity"] for f in found}, spec["archetype_id"]


def _drops(node, path=()):
    """Every way to remove one key of a nested payload, as (path) tuples: dict keys, and the keys of the first item of a list."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + (k,)
            yield from _drops(v, path + (k,))
    elif isinstance(node, list) and node:
        yield from _drops(node[0], path + (0,))


def _without(payload, path):
    out = copy.deepcopy(payload)
    node = out
    for step in path[:-1]:
        node = node[step]
    del node[path[-1]]
    return out


def test_a_payload_missing_any_key_is_a_fail_or_a_clean_pass_never_an_exception(job):
    base, manifest = job
    tried = 0
    for r in VC.items_of(manifest, base):
        for path in _drops(r["spec"]["payload"]):
            spec = copy.deepcopy(r["spec"])
            spec["payload"] = _without(spec["payload"], path)
            args = (spec, r["spine"], r["item"]["trigger_word_index"], r["item"]["duration_frames"], base)
            found = VC.check_item(*args)                                  # must not raise
            assert all("rule" in f and "severity" in f for f in found)
            C.errors(spec, base)                                         # the contract check must not raise either
            tried += 1
    assert tried > 150


def test_the_malformed_payloads_a_review_found_are_fails(job):
    base, manifest = job
    rows = {r["spec"]["archetype_id"]: r for r in VC.items_of(manifest, base)}

    def fails(kind, edit):
        r = rows[kind]
        spec = copy.deepcopy(r["spec"])
        edit(spec["payload"])
        found = VC.check_item(spec, r["spine"], r["item"]["trigger_word_index"], r["item"]["duration_frames"], base)
        assert rules(found, "FAIL"), (kind, found)
        assert rules(C.errors(spec, base), "FAIL"), kind
    fails("MULTI_SCENARIO_VERDICT_MATRIX", lambda p: p.update(scenarios=[{"id": "s1", "label": "x"}]))
    fails("TECH_TREE_DEPENDENCY_GRAPH", lambda p: p.update(edges=[{"to": "n2"}]))
    fails("TACTICAL_UNIT_MANEUVER", lambda p: p["routes"][0].pop("id"))
    fails("TACTICAL_UNIT_MANEUVER", lambda p: p.update(base={"kind": "plate"}))
    fails("TACTICAL_UNIT_MANEUVER", lambda p: p.update(base={"kind": "plate", "ref": "p.png"}))


def test_a_parallax_spec_checked_without_a_folder_is_not_failed_for_its_files(job):
    base, manifest = job
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "PARALLAX_25D_TABLEAU")
    assert VC.payload_findings(row["spec"], None) == []
    assert C.errors(row["spec"]) == []


def test_an_element_without_an_event_is_flagged_for_every_archetype_that_has_elements(job):
    base, manifest = job
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "TECH_TREE_DEPENDENCY_GRAPH")
    spec = copy.deepcopy(row["spec"])
    spec["events"] = []
    found = VC.check_item(spec, row["spine"], row["item"]["trigger_word_index"], row["item"]["duration_frames"], base)
    assert "CMP-04" in rules(found)


def test_a_word_before_the_trigger_word_is_a_fail_not_frame_zero(job):
    base, manifest = job
    for kind in ("TACTICAL_UNIT_MANEUVER", "SPLIT_SCREEN_SPEED_RACE"):
        row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == kind)
        spec = copy.deepcopy(row["spec"])
        spec["events"][0]["word_index"] = row["item"]["trigger_word_index"] - 3
        found = VC.check_item(spec, row["spine"], row["item"]["trigger_word_index"], row["item"]["duration_frames"], base)
        assert any(f["rule"] == "CN-01" and f["severity"] == "FAIL" and "before the item's trigger" in f["detail"] for f in found), kind
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "MAP_3D_TERRAIN_FLYOVER")
    spec = copy.deepcopy(row["spec"])
    spec["payload"]["camera"]["moves"][0]["from_word"] = row["item"]["trigger_word_index"] - 1
    found = VC.check_item(spec, row["spine"], row["item"]["trigger_word_index"], row["item"]["duration_frames"], base)
    assert any(f["rule"] == "CN-01" and f["severity"] == "FAIL" for f in found)


def test_a_literal_colour_is_refused_in_a_hud_too(job):
    base, manifest = job
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "SPLIT_SCREEN_SPEED_RACE")
    spec = copy.deepcopy(row["spec"])
    spec["payload"]["note"] = "#D93025"
    found = VC.check_item(spec, row["spine"], row["item"]["trigger_word_index"], row["item"]["duration_frames"], base)
    assert "CMP-06" in rules(found)


def test_the_parallax_tableau_needs_its_assets(job, tmp_path):
    base, manifest = job
    row = next(r for r in VC.items_of(manifest, base) if r["spec"]["archetype_id"] == "PARALLAX_25D_TABLEAU")
    assert tableau.asset_findings(row["spec"], base) == []
    missing = tableau.asset_findings(row["spec"], tmp_path)
    assert missing and rules(missing, "FAIL")


# --- across items: the planner's checks --------------------------------------------------------------------------------------------------

def test_cmp10_rotation():
    ok = blocks(("MAP_3D_TERRAIN_FLYOVER", 0, 20), ("BALLISTIC_RANGE_AND_ENERGY_HUD", 30, 40), ("TACTICAL_UNIT_MANEUVER", 50, 70))
    assert VC.rotation(ok) == []
    twice = blocks(("SPLIT_SCREEN_SPEED_RACE", 0, 10), ("SPLIT_SCREEN_SPEED_RACE", 12, 20))
    assert "adjacent" in VC.rotation(twice)[0]["detail"] and VC.rotation(twice)[0]["severity"] == SR.level("BP-149")
    window, fam_max = SR.T("BP-149", "window_s"), SR.T("BP-149", "family_max")
    fam = [a for a in VC.ids() if VC.archetype(a)["family"] == "hud"]
    crowd = blocks(*[(fam[k % len(fam)], k * 5, k * 5 + 4) for k in range(int(fam_max) + 1)])
    assert any("hud items" in f["detail"] for f in VC.rotation(crowd))
    maps = [a for a in VC.ids() if VC.archetype(a)["pure_map"]]
    run = blocks((maps[0], 0, 40), (maps[1], 40.2, 80), (maps[2], 80.4, 120))
    assert any("map run" in f["detail"] for f in VC.rotation(run))
    broken = blocks((maps[0], 0, 40), (maps[1], 40.2, 60), ("BALLISTIC_RANGE_AND_ENERGY_HUD", 61, 70), (maps[2], 71, 111))
    assert not any("map run" in f["detail"] for f in VC.rotation(broken))
    assert window > 0


def test_cmp11_map_share():
    maps = [a for a in VC.ids() if VC.archetype(a)["pure_map"]]
    small = blocks((maps[0], 0, 20), ("SPLIT_SCREEN_SPEED_RACE", 20, 100))
    assert VC.map_share(small, 100) == []
    big = blocks((maps[0], 0, 30), ("SPLIT_SCREEN_SPEED_RACE", 30, 100))
    found = VC.map_share(big, 100)
    assert rules(found) == {"CMP-11"} and "high mark" not in found[0]["detail"]
    huge = blocks((maps[0], 0, 80), ("SPLIT_SCREEN_SPEED_RACE", 80, 100))
    assert "high mark" in VC.map_share(huge, 100)[0]["detail"]


def test_cmp12_lane_balance():
    run_max = SR.T("BP-127", "non_character_run_max_s")
    scene_max = SR.T("BP-127", "character_scene_max_s")
    fine = [{"kind": "map", "start_s": 0, "end_s": 20}, {"kind": "character", "start_s": 20, "end_s": 50}, {"kind": "hud", "start_s": 50, "end_s": 70}]
    assert VC.lane_balance(fine) == []
    long_run = [{"kind": "map", "start_s": 0, "end_s": run_max}, {"kind": "hud", "start_s": run_max, "end_s": run_max + 10}]
    assert "non-character" in VC.lane_balance(long_run)[0]["detail"]
    host = [{"kind": "map", "start_s": 0, "end_s": run_max - 5}, {"kind": "host", "start_s": run_max - 5, "end_s": run_max}, {"kind": "hud", "start_s": run_max, "end_s": 2 * run_max - 5}]
    assert VC.lane_balance(host) == []
    long_scene = [{"kind": "character", "start_s": 0, "end_s": 50}, {"kind": "character", "start_s": 50, "end_s": scene_max + 5}]
    assert "payoff" in VC.lane_balance(long_scene)[0]["detail"]
    payoff = [{"kind": "character", "start_s": 0, "end_s": 50}, {"kind": "hud", "start_s": 50, "end_s": 60}, {"kind": "character", "start_s": 60, "end_s": scene_max + 5}]
    assert VC.lane_balance(payoff) == []


def _variant_job(base, mutate):
    """The demo job, copied, with ``mutate(manifest, specs)`` applied (specs: item_id -> spec) and every file written back."""
    import shutil
    dest = base / "variant"
    shutil.copytree(job_dir(base), dest)
    manifest = json.loads((dest / "visual" / "visual_comp_manifest.json").read_text(encoding="utf-8"))
    specs = {it["item_id"]: json.loads((dest / "visual" / "specs" / f"{it['item_id']}.json").read_text(encoding="utf-8")) for it in manifest["items"]}
    mutate(manifest, specs)
    for iid, sp in specs.items():
        (dest / "visual" / "specs" / f"{iid}.json").write_text(json.dumps(sp), encoding="utf-8")
    (dest / "visual" / "visual_comp_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return dest, manifest


def job_dir(tmp_path):
    src = tmp_path / "src"
    _comp.build(src)
    return src


def test_the_rotation_is_checked_over_a_whole_manifest(tmp_path):
    def same_twice(manifest, specs):
        a, b = manifest["items"][4], manifest["items"][5]
        b["archetype_id"] = a["archetype_id"]
        moved = _comp.shift(copy.deepcopy(specs[a["item_id"]]), b["trigger_word_index"] - a["trigger_word_index"])
        specs[b["item_id"]] = {**moved, "item_id": b["item_id"]}
        b["duration_frames"] = a["duration_frames"]
    base, manifest = _variant_job(tmp_path, same_twice)
    found = VC.check(manifest, base)
    assert rules(found, "FAIL") == set(), found
    assert any(f["rule"] == "CMP-10" and "adjacent" in f["detail"] for f in found)


def test_check_runs_the_map_share_over_the_runtime_of_the_spine(tmp_path):
    base, manifest = job_dir(tmp_path), None
    manifest = json.loads((base / "visual" / "visual_comp_manifest.json").read_text(encoding="utf-8"))
    assert "CMP-11" not in rules(VC.check(manifest, base))          # the demo's four maps are a small share of its 7.5 minutes
    spine = json.loads((base / "audio" / "audio_spine.json").read_text(encoding="utf-8"))
    short = {**spine, "duration_s": 120.0}
    (base / "audio" / "audio_spine.json").write_text(json.dumps(short), encoding="utf-8")
    manifest["audio_spine"]["sha256"] = C.sha256_file(base / "audio" / "audio_spine.json")
    found = VC.check(manifest, base)
    assert any(f["rule"] == "CMP-11" for f in found), "the maps of the demo are over a quarter of a 2-minute spine"


def test_check_runs_the_lane_balance_when_the_planner_passes_its_beats(tmp_path):
    base = job_dir(tmp_path)
    manifest = json.loads((base / "visual" / "visual_comp_manifest.json").read_text(encoding="utf-8"))
    assert "CMP-12" not in rules(VC.check(manifest, base))                # no beats given: the check is not run
    assert "CMP-12" in rules(VC.check(manifest, base, beats=[]))          # no character beat at all over a long run of compensators
    rows = VC.items_of(manifest, base)
    beats = [{"kind": "host", "start_s": r["start_s"] + 1.0, "end_s": r["start_s"] + 1.5} for r in rows]
    assert "CMP-12" not in rules(VC.check(manifest, base, beats=beats))


# --- CN-15: the contract side ------------------------------------------------------------------------------------------------------------

def fixture(name):
    return json.loads((ROOT / "tests" / "fixtures" / "contracts" / name).read_text(encoding="utf-8"))


def test_cn15_a_manifest_item_names_a_catalogue_archetype():
    doc = fixture("visual_comp_manifest/valid.json")
    assert "CN-15" not in rules(C.errors(doc))
    doc["items"][0]["archetype_id"] = "MAP_OF_EVERYTHING"
    assert "CN-15" in rules(C.errors(doc), "FAIL")


def test_cn15_a_comp_spec_names_a_catalogue_archetype():
    assert "CN-15" not in rules(C.validate(fixture("comp_spec/valid.json")))
    assert C.errors(fixture("comp_spec/invalid__unknown_archetype.json"))
    for name in ("invalid__event_without_a_word.json", "invalid__racer_without_time.json"):
        assert C.errors(fixture(f"comp_spec/{name}")), name


def test_cn15_a_map_or_compensator_shot_sits_on_its_lane():
    shots = {"schema": "film_shots/2", "fps": 24, "shots": []}
    ok = {"id": "s1", "lane": "MAP", "archetype": "TACTICAL_UNIT_MANEUVER", "seconds": 5, "duration_frames": 120, "width": 1280, "height": 720}
    assert C._film_shots({**shots, "shots": [ok]}, None) == []
    wrong = {**ok, "lane": "COMPENSATOR"}
    found = C._film_shots({**shots, "shots": [wrong]}, None)
    assert rules(found) == {"CN-15"} and "belongs on the MAP lane" in found[0]["detail"]
    unknown = {**ok, "archetype": "NOPE"}
    assert rules(C._film_shots({**shots, "shots": [unknown]}, None)) == {"CN-15"}


# --- CMP-14: free by construction --------------------------------------------------------------------------------------------------------

FORBIDDEN = {"requests", "urllib", "http", "socket", "httpx", "aiohttp", "google", "openai", "anthropic", "runpod", "elevenlabs", "torch",
             "diffusers", "transformers", "onnxruntime", "boto3", "subprocess"}


def imports_of(path: Path) -> set[str]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_cmp14_the_compensator_imports_no_client_and_no_model():
    files = [*(ROOT / "explainer_engine" / "maps").glob("*.py"), ROOT / "explainer_engine" / "edit" / "hud.py",
             ROOT / "explainer_engine" / "edit" / "tableau.py", ROOT / "explainer_engine" / "edit" / "visual_compensator.py"]
    assert len(files) >= 10
    for f in files:
        bad = {m for m in imports_of(f) if m.split(".")[0] in FORBIDDEN}
        assert not bad, f"{f.name} imports {sorted(bad)} (CMP-14)"
    for f in (ROOT / "explainer_engine" / "maps" / "data" / "build.py",):
        assert f.exists()      # the one network-capable file is the offline build script, run by a person, never by a render


def test_cmp14_the_catalogue_is_free_and_shots_cost_nothing():
    assert all(a["free"] for a in VC.catalogue()["archetypes"])
    assert not any(k in json.dumps(VC.catalogue()) for k in ("usd", "price", "cost_per"))
