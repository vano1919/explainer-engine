"""The variant planner (Blueprint P3, VP-01..VP-18): dynamics is the one place that counts lane shares; every check fires on a
built counter-example; cost is UNKNOWN until measured and never guessed; the Napoleon example scores as designed (V1 70, V2 70: P5 landed, KEYFRAME_LTX waits for P6)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.core import contracts, store
from explainer_engine.core.errors import ContractError
from explainer_engine.scripting import variant_plan as VP
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
NAP = ROOT / "examples" / "napoleon_vs_genghis"
CAPS = {"per_episode": {"runpod_usd": 31.0, "gemini_usd": 10.0}, "runpod": {"per_pod_usd": 6.9}}


def blk(cat, secs, **kw):
    return {"category": cat, "seconds": secs, **kw}


def seg(sid, *blocks, function=None):
    return {"id": sid, "function": function, "window_s": sum(b["seconds"] for b in blocks), "blocks": list(blocks)}


def rules(found):
    return sorted(f["rule"] for f in found)


def sev(found, rule):
    return [f["severity"] for f in found if f["rule"] == rule]


def run(segs, pid="A", template="D"):
    prof = VP.profile(pid)
    return VP.checks(VP.dynamics(segs, prof, template=template), prof)


def test_dynamics_on_a_toy_plan_gives_exact_shares_and_runs():
    segs = [seg("S01", blk("scene", 10, who="a"), blk("compensator", 20, archetype=9)),
            seg("S02", blk("map_pure", 30, archetype=1), blk("hold", 40))]
    d = VP.dynamics(segs, VP.profile("A"))
    assert d["total_s"] == 100
    assert d["share"] == {"scene": 0.1, "map_pure": 0.3, "compensator": 0.2, "host": 0.0, "hold": 0.4}
    assert sum(d["share"].values()) == pytest.approx(1.0) and d["non_character"] == pytest.approx(0.9)
    assert d["map_run_max_s"] == 30 and d["non_scene_run_max_s"] == 90
    assert d["narrator_basis"] == "seconds" and d["narrator_share"] == pytest.approx(0.9)


def test_the_category_of_a_block_follows_its_lane_and_the_film_shots_1_inference():
    assert VP.category({"lane": "MAP", "seconds": 1}) == "map_pure"
    assert VP.category({"lane": "KEYFRAME_LTX", "who": "napoleon", "seconds": 1}, cast={"napoleon"}) == "scene"
    assert VP.category({"lane": "KEYFRAME_LTX", "who": "crowd", "seconds": 1}, cast={"napoleon"}) == "compensator"
    assert VP.category({"mode": "narrated", "who": "napoleon"}, cast={"napoleon"}) == "scene"
    assert VP.category({"mode": "narrated", "who": "fog"}, cast={"napoleon"}) == "compensator"
    assert VP.category({"mode": "insert", "tier": "hold"}) == "hold"
    assert VP.category({"mode": "establish"}) == "compensator"


def test_vp02_a_map_share_over_the_limit_is_review_never_fail():
    segs = [seg("S01", blk("map_pure", 50, archetype=1), blk("scene", 50, who="a"))]
    found = run(segs)
    assert sev(found, "VP-02") == ["REVIEW"] and "FAIL" not in {f["severity"] for f in found if f["rule"] != "VP-08"}
    assert SR.severity("BP-141") == "REVIEW"


def test_vp03_vp04_vp05_runs_and_the_non_character_total():
    segs = [seg("S01", blk("scene", 10, who="a"), blk("map_pure", 100, archetype=2), blk("compensator", 20, archetype=7))]
    found = run(segs)
    assert sev(found, "VP-03") == ["REVIEW"] and sev(found, "VP-04") == ["REVIEW"] and sev(found, "VP-05") == ["REVIEW"]
    ok = run([seg("S01", blk("scene", 60, who="a"), blk("map_pure", 20, archetype=2), blk("scene", 20, who="a"))])
    assert not {"VP-03", "VP-04", "VP-05"} & set(rules(ok))


def test_vp06_the_same_archetype_twice_in_a_row_and_vp07_a_family_over_its_share():
    adjacent = [seg("S01", blk("scene", 30, who="a"), blk("compensator", 10, archetype=6), blk("compensator", 10, archetype=6))]
    assert "VP-06" in rules(run(adjacent))
    between = [seg("S01", blk("compensator", 10, archetype=6), blk("scene", 10, who="a"), blk("compensator", 10, archetype=6))]
    assert "VP-06" not in rules(run(between))
    family = [seg("S01", blk("scene", 40, who="a"), blk("compensator", 10, archetype=5), blk("compensator", 10, archetype=7),
                  blk("compensator", 10, archetype=11))]
    assert sev(run(family), "VP-07") == ["REVIEW"]


def test_vp08_a_turn_with_no_played_block_fails_by_the_creators_rule_and_vp09_a_low_share_reviews():
    assert SR.severity("BP-142") == "FAIL" and SR.rule("BP-142")["status"] == "house"
    segs = [seg("S01", blk("scene", 30, who="a")), seg("S10", blk("map_pure", 20, archetype=1), blk("compensator", 20, archetype=5))]
    d = VP.dynamics(segs, VP.profile("A"))
    assert "S10" in d["turns"] and "S01" not in d["turns"]
    found = VP.checks(d, VP.profile("A"))
    assert [f["where"] for f in found if f["rule"] == "VP-08"] == ["S10"] and sev(found, "VP-08") == ["FAIL"]
    low = [seg("S04", blk("scene", 10, who="a"), blk("compensator", 40, archetype=9))]
    found = run(low)
    assert sev(found, "VP-09") == ["REVIEW"] and "VP-08" not in rules(found)


def test_a_segment_whose_function_is_a_turn_counts_outside_template_d():
    segs = [seg("A1", blk("compensator", 30, archetype=9), function="reversal")]
    assert VP.dynamics(segs, VP.profile("B"), template="A")["turns"] == ["A1"]
    assert VP.dynamics([seg("S04", blk("compensator", 30))], VP.profile("B"), template="A")["turns"] == []


def test_vp10_one_compensator_picture_over_seven_seconds_reviews():
    long_hold = [seg("S01", blk("scene", 40, who="a"), blk("compensator", 20, archetype=9, shots=1))]
    assert sev(run(long_hold), "VP-10") == ["REVIEW"]
    split = [seg("S01", blk("scene", 40, who="a"), blk("compensator", 20, archetype=9, shots=4))]
    assert "VP-10" not in rules(run(split))


def test_vp16_the_narrator_share_uses_words_when_the_blocks_carry_them():
    segs = [seg("S01", blk("scene", 10, who="a", words={"character": 60}), blk("compensator", 10, words={"narrator": 40}))]
    d = VP.dynamics(segs, VP.profile("A"))
    assert d["narrator_basis"] == "words" and d["narrator_share"] == pytest.approx(0.4)
    assert "VP-16" not in rules(VP.checks(d, VP.profile("A")))
    heavy = [seg("S01", blk("scene", 10, who="a", words={"character": 10}), blk("compensator", 10, words={"narrator": 90}))]
    assert sev(VP.checks(VP.dynamics(heavy, VP.profile("A")), VP.profile("A")), "VP-16") == ["REVIEW"]


def test_vp17_the_central_scene_has_the_most_played_seconds():
    scenes = [seg("S04", blk("scene", 60, who="a")), seg("S06", blk("scene", 60, who="a")), seg("S08", blk("scene", 60, who="a")),
              seg("S10", blk("scene", 30, who="a")), seg("S11", blk("scene", 30, who="a")), seg("S13", blk("scene", 30, who="a"))]
    assert sev(run(scenes), "VP-17") == ["REVIEW"]
    scenes[3] = seg("S10", blk("scene", 90, who="a"))
    assert "VP-17" not in rules(run(scenes))


def test_vp18_hold_share_over_the_limit_reviews():
    segs = [seg("S01", blk("scene", 50, who="a"), blk("hold", 50))]
    assert sev(run(segs), "VP-18") == ["REVIEW"]


def test_vp11_each_missing_lane_is_one_finding_naming_its_phase_and_the_table_is_honest():
    segs = [seg("S01", blk("map_pure", 10, archetype=1), blk("map_pure", 10, archetype=2), blk("compensator", 10, archetype=8),
                blk("compensator", 10, archetype=9), blk("host", 10), blk("scene", 10, who="a"))]
    found = VP.lane_findings(segs)
    assert sorted(f["where"] for f in found) == ["HOST_COMMENTARY", "KEYFRAME_LTX:full"]   # the scene block needs a keyframe clip
    assert all(f["severity"] == "REVIEW" for f in found)
    assert "P5b" in next(f["detail"] for f in found if f["where"] == "HOST_COMMENTARY")
    assert "P6" in next(f["detail"] for f in found if f["where"] == "KEYFRAME_LTX:full")
    phases = {p["id"] for p in json.loads((ROOT / "docs" / "blueprint" / "phases.json").read_text(encoding="utf-8"))["phases"]}
    for key, info in VP.LANES.items():
        if info["available"]:
            assert (ROOT / info["evidence"]).is_file(), key   # a file that implements the lane, never a folder
        else:
            assert info["phase"] in phases, key
    # until a pod script under explainer_engine/training/pods/ names LTX-2.5 or Wan 2.2 and passes runpod dryrun (OR-21)
    for tier in ("light", "full"):
        assert not VP.LANES[f"KEYFRAME_LTX:{tier}"]["available"] and VP.LANES[f"KEYFRAME_LTX:{tier}"]["phase"] == "P6", tier
    assert VP.LANES["MAP"]["available"] and VP.LANES["COMPENSATOR"]["available"]   # P5 landed: maps/render.py, edit/visual_compensator.py
    assert VP.lane_findings([seg("S01", blk("hold", 5), blk("compensator", 5, archetype=8))]) == []   # lanes that exist in code
    assert [f["where"] for f in VP.lane_findings([seg("S01", blk("scene", 10, who="a"), blk("hold", 5))])] == ["KEYFRAME_LTX:full"]


def test_row_usd_reads_the_job_speeds_schema_written_by_runpod_cost():
    row = {"kind": "pod", "job": "ltx_clip", "units": 100, "card": "NVIDIA A40"}
    speeds = {"version": 1, "jobs": {"ltx_clip": {"unit": "clip", "rows": {"NVIDIA A40": {"s_per_unit": 10.0, "usd_per_unit": 0.0011111}}}}}
    usd, basis = VP._row_usd(row, speeds)
    assert usd == pytest.approx(100 * 0.0011111, abs=1e-6) and basis == "measured"
    assert VP._row_usd({"kind": "pod", "job": "ltx_clip", "units": 100}, {"jobs": {}}) == (None, "unknown")
    assert VP._row_usd(dict(row, card="NVIDIA L40S"), speeds) == (None, "unknown")           # a card that was never measured
    one = {"jobs": {"ltx_clip": {"rows": {"NVIDIA A40": {"s_per_unit": 10.0, "usd_per_unit": 0.002}}}}}
    assert VP._row_usd({"kind": "pod", "job": "ltx_clip", "units": 10}, one)[0] == pytest.approx(0.02)   # one measured card: no name needed
    two = {"jobs": {"ltx_clip": {"rows": {"A": {"s_per_unit": 1.0, "usd_per_unit": 0.1}, "B": {"s_per_unit": 2.0, "usd_per_unit": 0.2}}}}}
    assert VP._row_usd({"kind": "pod", "job": "ltx_clip", "units": 10}, two) == (None, "unknown")
    no_usd = {"jobs": {"ltx_clip": {"rows": {"NVIDIA A40": {"s_per_unit": 10.0}}}}}                 # seconds alone price nothing
    assert VP._row_usd(row, no_usd) == (None, "unknown")


def test_vp12_names_why_a_pod_row_is_unpriced():
    v = {"cost_rows": [{"label": "clips", "kind": "pod", "job": "ltx_clip", "units": 10, "service": "runpod_usd"}]}
    two = {"jobs": {"ltx_clip": {"rows": {"A": {"s_per_unit": 1.0, "usd_per_unit": 0.1}, "B": {"s_per_unit": 2.0, "usd_per_unit": 0.2}}}}}
    assert "2 cards measured for ltx_clip" in VP.cost_checks(VP.cost(v, speeds=two, caps=CAPS))[0]["detail"]
    assert "no measured row for job ltx_clip" in VP.cost_checks(VP.cost(v, speeds={"jobs": {}}, caps=CAPS))[0]["detail"]


def test_cost_with_no_job_speeds_is_unknown_and_never_a_guess():
    v = {"cost_rows": [{"label": "keyframes", "kind": "pod", "job": "keyframe", "units": 100, "service": "runpod_usd"},
                       {"label": "maps", "kind": "cpu", "units": 1}]}
    c = VP.cost(v, speeds=None, caps=CAPS)
    assert c["usd_planned"] == "unknown" and c["usd_worst"] == "unknown" and c["unknown_rows"] == ["keyframes"]
    assert c["known_usd_worst"] == 0.0
    found = VP.cost_checks(c)
    assert rules(found) == ["VP-12"] and found[0]["severity"] == "REVIEW"


def test_cost_from_measured_speeds_is_planned_1_5_and_worst_3_times_the_base():
    speeds = {"keyframe": {"seconds_per_unit": 3.6, "gpu": "NVIDIA RTX A5000", "measured": True}}
    from explainer_engine.cloud import runpod
    base = 100 * 3.6 / runpod.SPEED["NVIDIA RTX A5000"] / 3600 * runpod.MAX_PRICE["default"]
    v = {"cost_rows": [{"label": "keyframes", "kind": "pod", "job": "keyframe", "units": 100, "service": "runpod_usd", "pod": "p1"}]}
    c = VP.cost(v, speeds=speeds, caps=CAPS)
    assert c["usd_planned"] == pytest.approx(base * 1.5) and c["usd_worst"] == pytest.approx(base * 3) and c["unknown_rows"] == []
    assert c["rows"][0]["basis"] == "measured" and VP.cost_checks(c) == []


def test_vp13_known_worst_over_80_percent_of_a_cap_fails_and_a_small_cap_is_read_not_written():
    speeds = {"keyframe": {"seconds_per_unit": 3600.0, "gpu": "NVIDIA A100-SXM4-80GB"}}
    v = {"cost_rows": [{"label": "keyframes", "kind": "pod", "job": "keyframe", "units": 10, "service": "runpod_usd", "pod": "p1"}]}
    found = VP.cost_checks(VP.cost(v, speeds=speeds, caps=CAPS))
    assert [f["severity"] for f in found] == ["FAIL", "FAIL"] and rules(found) == ["VP-13", "VP-13"]
    assert {"per_episode.runpod_usd", "runpod.per_pod_usd (p1)"} == {f["where"] for f in found}
    tiny = VP.cost({"cost_rows": [{"label": "k", "kind": "pod", "job": "keyframe", "units": 1, "service": "runpod_usd"}]},
                   speeds=speeds, caps={"per_episode": {"runpod_usd": 31.0}})
    assert VP.cost_checks(tiny) == []


def test_vp13_still_fails_on_the_known_part_when_other_rows_are_unknown():
    speeds = {"keyframe": {"seconds_per_unit": 3600.0, "gpu": "NVIDIA A100-SXM4-80GB"}}
    rows = [{"label": "k", "kind": "pod", "job": "keyframe", "units": 10, "service": "runpod_usd"},
            {"label": "video", "kind": "pod", "job": "ltx_full", "units": 5, "service": "runpod_usd"}]
    found = VP.cost_checks(VP.cost({"cost_rows": rows}, speeds=speeds, caps=CAPS))
    assert {"VP-12", "VP-13"} <= set(rules(found))


def test_api_rows_come_from_the_price_tables_and_a_missing_price_is_unknown():
    from explainer_engine.imagegen import plan as imgplan
    from explainer_engine.imagegen import gemini
    model = next(iter(gemini.PRICES))
    size = next(iter(gemini.PRICES[model]))
    row = {"label": "pictures", "kind": "api", "provider": "gemini", "model": model, "size": size, "units": 4, "service": "gemini_usd"}
    c = VP.cost({"cost_rows": [row]}, speeds=None, caps=CAPS)
    assert c["known_usd_planned"] == pytest.approx(imgplan.price("gemini", model, size, 0) * 4 * 1.5)
    bad = VP.cost({"cost_rows": [dict(row, model="no-such-model")]}, speeds=None, caps=CAPS)
    assert bad["unknown_rows"] == ["pictures"]


def test_score_arithmetic_and_floor():
    r, f = {"severity": "REVIEW"}, {"severity": "FAIL"}
    assert VP.score([]) == 100 and VP.score([r, r]) == 80 and VP.score([f]) == 75 and VP.score([f, r]) == 65
    assert VP.score([{"severity": "INFO"}]) == 100 and VP.score([f] * 5) == 0


def test_vp15_drift_splits_review_from_the_creators_money_fail():
    chosen = {"segments": [seg("S01", blk("scene", 100, who="a")), seg("S02", blk("scene", 100, who="a"))],
              "cost": {"usd_planned": 10.0, "usd_worst": 20.0}}
    now = {"segments": [seg("S01", blk("scene", 100, who="a")), seg("S02", blk("scene", 120, who="a"))], "usd": 10.5}
    assert [(f["severity"], f["where"]) for f in VP.drift(chosen, now)] == [("REVIEW", "S02")]
    now["usd"] = 13.0
    assert ("REVIEW", "cost") in [(f["severity"], f["where"]) for f in VP.drift(chosen, now)]
    now["usd"] = 20.5
    assert ("FAIL", "cost") in [(f["severity"], f["where"]) for f in VP.drift(chosen, now)]
    assert SR.severity("BP-146") == "REVIEW"
    gone = {"segments": [seg("S01", blk("scene", 100, who="a"))], "usd": 1.0}
    assert any("added or dropped" in f["detail"] for f in VP.drift(chosen, gone))


def test_vp01_blocks_that_do_not_add_up_are_a_contract_fault():
    v = {"id": "v", "profile_id": "A", "segments": [{"id": "S01", "window_s": 50, "blocks": [blk("scene", 40, who="a")]}], "cost_rows": []}
    found = VP.variant_findings(v)
    assert rules(found) == ["VP-01"] and found[0]["severity"] == "FAIL"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_napoleon_v1_is_rebuilt_from_the_shot_cards_and_scores_70():
    fs = load(NAP / "film_shots.json")
    segs = VP.segments_from_film_shots(fs)
    d = VP.dynamics(segs, VP.profile("D"))
    assert d["total_s"] == 900 and len(fs["shots"]) == 214
    assert d["share"]["scene"] == pytest.approx(0.801, abs=0.001) and d["share"]["compensator"] == pytest.approx(0.153, abs=0.001)
    assert d["share"]["hold"] == pytest.approx(0.046, abs=0.001) and d["share"]["map_pure"] == 0 and d["share"]["host"] == 0
    assert d["narrator_share"] == pytest.approx(0.449, abs=0.001) and d["narrator_basis"] == "words"
    assert d["non_scene_run_max_s"] == 8 and d["map_run_max_s"] == 0
    assert {t: round(s, 2) for t, s in d["turn_played_share"].items()} == {"S04": 0.89, "S06": 0.70, "S08": 0.83, "S10": 0.68,
                                                                           "S11": 0.74, "S13": 0.88}
    assert d["turn_played_s"]["S10"] == pytest.approx(101, abs=1) and d["turn_played_s"]["S13"] == pytest.approx(89, abs=1)


def test_the_napoleon_fixture_is_current_valid_and_scored_as_designed():
    path = NAP / "script_variants.json"
    doc = load(path)
    contracts.validate(doc, NAP)
    assert doc == VP.napoleon_variants(speeds={}), "script_variants.json is stale: run `variant_plan napoleon --write`"
    v1, v2 = doc["variants"]
    assert (v1["profile_id"], v1["scores"]["code"], v1["risks"]) == ("D", 70, ["REVIEW VP-11 KEYFRAME_LTX:full", "REVIEW VP-11 KEYFRAME_LTX:light", "REVIEW VP-12 cost"])
    assert (v2["profile_id"], v2["scores"]["code"]) == ("B", 70)   # was 60 while MAP and COMPENSATOR were listed as missing (P5 landed)
    assert sorted(v2["risks"]) == ["REVIEW VP-11 KEYFRAME_LTX:full", "REVIEW VP-12 cost", "REVIEW VP-16 narrator"]
    assert not [f for f in VP.check_file(path, speeds={}) if f["severity"] == "FAIL"]
    assert VP.check_file(path, speeds={}) and all(f["rule"] != "VP-14" for f in VP.check_file(path, speeds={}))
    assert v1["cost"]["usd_planned"] == "unknown" and v2["cost"]["usd_worst"] == "unknown"
    assert v2["dynamics"]["share_scene"] == pytest.approx(0.362, abs=0.001) and v2["dynamics"]["share_map_pure"] == pytest.approx(0.158, abs=0.001)


def test_two_variants_of_one_profile_are_vp14_and_a_stale_score_is_cn02(tmp_path):
    doc = load(NAP / "script_variants.json")
    doc["variants"][1]["profile_id"] = "D"
    p = tmp_path / "script_variants.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    found = VP.check_file(p, speeds={})
    assert "VP-14" in rules(found) and sev(found, "VP-14") == ["REVIEW"]
    doc = load(NAP / "script_variants.json")
    doc["variants"][0]["scores"]["code"] = 100
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert [f["severity"] for f in VP.check_file(p, speeds={}) if f["rule"] == "CN-02"] == ["FAIL"]


def test_the_choice_binds_the_variants_it_was_picked_from(tmp_path):
    doc = load(NAP / "script_variants.json")
    doc["chosen"] = {"variant_id": "v1", "by": "creator", "ref": "cmsg_1", "at": "2026-10-30T00:00:00Z",
                     "variants_sha256": contracts.variants_sha256(doc)}
    p = tmp_path / "script_variants.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert not [f for f in VP.check_file(p, speeds={}) if f["severity"] == "FAIL"]
    doc["variants"][0]["title"] = "edited after the pick"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert [f["rule"] for f in VP.check_file(p, speeds={}) if f["severity"] == "FAIL"] == ["CN-04"]


def test_variant_chosen_refuses_an_approval_that_is_not_the_variants_sha256(tmp_path):
    from test_lifecycle import CREATOR, step
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    job = store.EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    step(job, "RESEARCHED")
    doc = load(NAP / "script_variants.json")
    doc["chosen"] = {"variant_id": "v1", "by": "creator", "ref": "cmsg_1", "at": "2026-10-30T00:00:00Z",
                     "variants_sha256": contracts.variants_sha256(doc)}
    f = tmp_path / "script_variants.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ContractError, match="CN-04"):
        job.move("VARIANT_CHOSEN", reason="x", approval=CREATOR, variants=f)  # CREATOR binds another sha256
    assert job.state == "RESEARCHED"
    job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": doc["chosen"]["variants_sha256"]}, variants=f)
    assert job.state == "VARIANT_CHOSEN"


def test_the_brief_holds_facts_only(tmp_path):
    (tmp_path / "dossier.md").write_text("facts", encoding="utf-8")
    b = VP.brief(tmp_path, traits={"war": True})
    assert b["dossier"]["files"][0]["path"] == "dossier.md" and len(b["dossier"]["files"][0]["sha256"]) == 64
    assert set(b["profiles"]) == {"A", "B", "C", "D"} and b["turn_slots_D"] == SR.T("BP-142", "turn_slots_D")
    assert b["lanes"]["MAP"] == {"available": True} and b["lanes"]["DIALOGUE_CU"] == {"available": False, "phase": "P6"} and b["traits"] == {"war": True}
    assert not {"recommended", "why", "score"} & set(b)


def test_a_production_script_becomes_segments_with_estimated_seconds():
    doc = {"segments": [{"id": "S04", "drama": {"function": "inciting"}, "lines": [
        {"text": "The fog lay over the field."}, {"speaker": "murat", "text": "Sire, let me charge."}]}]}
    segs = VP.segments_from_script(doc)
    d = VP.dynamics(segs, VP.profile("D"))
    assert segs[0]["function"] == "inciting" and d["turns"] == ["S04"] and d["turn_has_played"]["S04"]
    assert segs[0]["window_s"] == pytest.approx(sum(b["seconds"] for b in segs[0]["blocks"])) and segs[0]["window_s"] > 0


def test_score_write_recomputes_derived_numbers_and_keeps_the_critic_and_the_choice(tmp_path):
    doc = load(NAP / "script_variants.json")
    doc["variants"][0]["scores"] = {"code": 1, "critic": 77}
    doc["variants"][0]["dynamics"]["share_scene"] = 0.2
    fixed = VP.rescore(doc, speeds={})
    assert fixed["variants"][0]["scores"] == {"code": 70, "critic": 77}
    assert fixed["variants"][0]["dynamics"]["share_scene"] == pytest.approx(0.801, abs=0.001)
    doc["chosen"] = {"variant_id": "v1", "by": "creator", "ref": "r", "at": "2026-10-30T00:00:00Z", "variants_sha256": "0" * 64}
    assert VP.rescore(doc, speeds={})["chosen"]["variants_sha256"] == contracts.variants_sha256(VP.rescore(doc, speeds={}))


def test_the_pick_must_name_an_existing_eligible_variant(tmp_path):
    doc = load(NAP / "script_variants.json")
    doc["chosen"] = {"variant_id": "v9", "by": "creator", "ref": "r", "at": "2026-10-30T00:00:00Z", "variants_sha256": "0" * 64}
    doc["chosen"]["variants_sha256"] = contracts.variants_sha256(doc)
    p = tmp_path / "script_variants.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert any(f["rule"] == "CN-04" and f["where"] == "chosen.variant_id" for f in VP.check_file(p, speeds={}))
    doc["chosen"]["variant_id"] = "v2"
    # an eligible variant is fine; one with a FAIL (a turn told over a map) is refused
    doc["variants"][1]["segments"][3]["blocks"] = [b for b in doc["variants"][1]["segments"][3]["blocks"] if b["category"] != "scene"]
    doc["variants"][1]["segments"][3]["window_s"] = sum(b["seconds"] for b in doc["variants"][1]["segments"][3]["blocks"])
    doc = VP.rescore(doc, speeds={})
    p.write_text(json.dumps(doc), encoding="utf-8")
    found = VP.check_file(p, speeds={})
    assert any(f["rule"] == "VP-08" and f["severity"] == "FAIL" for f in found)
    assert any(f["rule"] == "CN-04" and "cannot be picked" in f["detail"] for f in found)


def test_variant_chosen_refuses_a_pick_that_names_no_variant(tmp_path):
    from test_lifecycle import CREATOR, step
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    job = store.EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    step(job, "RESEARCHED")
    doc = load(NAP / "script_variants.json")
    doc["chosen"] = {"variant_id": "nope", "by": "creator", "ref": "r", "at": "2026-10-30T00:00:00Z",
                     "variants_sha256": contracts.variants_sha256(doc)}
    f = tmp_path / "script_variants.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ContractError, match="not one of the variants"):
        job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": doc["chosen"]["variants_sha256"]}, variants=f)
