"""F5 (docs/COMPENSATOR.md CMP-16, BP-120, BP-81, VB-08): the sound director cues the story events of the visual compensator quietly, and
nothing else. Free: a synthetic job in a tmp folder, a tmp sound library."""
from __future__ import annotations

import json

import pytest

from test_sound_director import lib_with, make_job, put

from explainer_engine.audio import sound_director as D
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

PAD = {"width": 1920, "height": 1088, "payload": {}}


def comp_job(tmp_path, specs):
    """A one-segment 60 s job whose visual/visual_comp_manifest.json holds one item per ``(archetype, [(op, word_index), ...])``."""
    job, spine = make_job(tmp_path, nseg=1, seg_s=60.0, speech=(0.5, 59.0), film=False)
    items = []
    for n, (arch, events) in enumerate(specs, start=1):
        iid = f"c{n}"
        put(job / "visual" / f"{iid}.spec.json", {"schema": "comp_spec/1", "item_id": iid, "archetype_id": arch, **PAD,
                                                  "events": [{"id": f"e{k}", "word_index": w, "op": op, "target": None}
                                                             for k, (op, w) in enumerate(events)]})
        items.append({"item_id": iid, "shot_id": f"s{n}", "archetype_id": arch, "trigger_word_index": 0, "duration_frames": 100,
                      "layers": [{"kind": "spec", "ref": f"visual/{iid}.spec.json", "reveal_word_index": None}], "on_screen_text": None})
    put(job / "visual" / "visual_comp_manifest.json", {"schema": "visual_comp_manifest/1", "items": items,
                                                       "audio_spine": {"path": "audio/audio_spine.json",
                                                                     "sha256": contracts.sha256_file(job / "audio" / "audio_spine.json")}})
    return job, spine


def cues_of(tmp_path, specs):
    job, spine = comp_job(tmp_path, specs)
    manifest, report = D.plan_with_report(job, library=lib_with(tmp_path))
    return manifest, report, spine, job


def test_thirty_story_events_in_a_minute_get_at_most_bp81_per_minute_all_at_the_bp120_level_none_inside_a_word(tmp_path):
    story = [("stamp", 2 * k) for k in range(30)]                       # 30 story events, one every 2 s
    m, rep, spine, _ = cues_of(tmp_path, [("BALLISTIC_RANGE_AND_ENERGY_HUD", story)])
    cues = m["cues"]
    assert 0 < len(cues) <= SR.T("BP-81", "per_min_review")
    assert {c["gain_db"] for c in cues} == {SR.T("BP-120", "micro_cue_dbfs")}
    for c in cues:
        assert not any(w["start_frame"] <= c["frame"] < w["end_frame"] for w in spine["words"]), c   # spine check: never inside a word
    frames = sorted(c["frame"] for c in cues)
    burst = SR.T("BP-81", "burst_max")
    window = SR.T("BP-81", "burst_window_s")
    assert all(sum(1 for g in frames if f <= g < f + window * spine["fps"]) <= burst for f in frames)
    assert len(rep["dropped_cues"]) == 30 - len(cues) and all("BP-81" in d["why"] for d in rep["dropped_cues"])
    assert [f for f in rep["findings"] if f["severity"] == "FAIL"] == []            # the AUDIO_TIMED gate: 0 FAIL


def test_only_story_ops_are_cued_camera_moves_labels_and_rings_stay_silent(tmp_path):
    silent = [("show_label", 4), ("show_ring", 8), ("set_focus", 12), ("march", 16), ("date", 20), ("hide", 24)]
    m, rep, _, _ = cues_of(tmp_path, [("TACTICAL_UNIT_MANEUVER", silent), ("PARALLAX_25D_TABLEAU", [("dolly", 2), ("peel", 6)])])
    assert m["cues"] == [] and rep["dropped_cues"] == []                  # "peel" is a story op of the cutaway, not of the parallax tableau
    m, _, spine, _ = cues_of(tmp_path / "b", [("TACTICAL_UNIT_MANEUVER", silent + [("show_route", 30), ("show_route", 60)])])
    assert [c["frame"] + 2 for c in m["cues"]] == [spine["words"][30]["start_frame"], spine["words"][60]["start_frame"]]   # 2 frames lead, 40 ms at 50 fps
    assert all(c["max_ms"] > 0 and c["name"].startswith("pop_in") for c in m["cues"])


def test_a_cue_that_would_start_inside_a_narration_word_is_dropped_not_moved(tmp_path):
    job, spine = comp_job(tmp_path, [("BALLISTIC_RANGE_AND_ENERGY_HUD", [("stamp", 5)])])
    tight = json.loads((job / "audio" / "audio_spine.json").read_text())
    w = tight["words"][4]
    tight["words"][5]["start_frame"] = w["end_frame"]                      # no gap at all before word 5
    cues, dropped = D.compensator_cues(job, tight, tmp_path / "lib", [])
    assert cues == [] and dropped[0]["why"].startswith("no gap before the word")


def test_cues_already_planned_count_toward_the_density(tmp_path):
    job, spine = comp_job(tmp_path, [("BALLISTIC_RANGE_AND_ENERGY_HUD", [("stamp", 2 * k) for k in range(8)])])
    per_min = int(SR.T("BP-81", "per_min_review"))
    already = [{"name": "x", "frame": f, "gain_db": -26.0, "max_ms": None} for f in range(0, 8 * 10, 10)]   # eight cues in the first 1.6 s
    cues, dropped = D.compensator_cues(job, spine, tmp_path / "lib", already)
    assert len(already) >= per_min and cues == [] and len(dropped) == 8


def test_a_later_existing_cue_counts_toward_the_burst(tmp_path):
    job, spine = comp_job(tmp_path, [("BALLISTIC_RANGE_AND_ENERGY_HUD", [("stamp", 6)])])
    burst = int(SR.T("BP-81", "burst_max"))
    lead = max(1, int(SR.T("BP-54", "early_max_ms") / 1000 * spine["fps"]))
    at = spine["words"][6]["start_frame"] - lead
    later = [{"name": "x", "frame": at + 1 + k, "gain_db": -26.0, "max_ms": None} for k in range(burst)]   # all AFTER the candidate
    cues, dropped = D.compensator_cues(job, spine, tmp_path / "lib", later)
    assert cues == [] and "BP-81" in dropped[0]["why"]
    cues, dropped = D.compensator_cues(job, spine, tmp_path / "lib", later[:-1])    # one fewer later cue: room for exactly one more
    assert len(cues) == 1 and dropped == []


def test_no_visual_manifest_changes_nothing_and_the_catalogue_marks_the_story_ops(tmp_path):
    job, _ = make_job(tmp_path, nseg=1, seg_s=20.0, speech=(0.5, 19.0), film=False)
    m, rep = D.plan_with_report(job, library=lib_with(tmp_path))
    assert m["cues"] == [] and rep["dropped_cues"] == []
    doc = json.loads(D.ARCHETYPES.read_text(encoding="utf-8"))
    assert all("story_ops" in a for a in doc["archetypes"])
    from explainer_engine.edit import hud, tableau
    from explainer_engine.maps import render
    ops = {**{k: set(v) for k, v in hud.OPS.items()}, **{k: set(v) for k, v in tableau.OPS.items()},
           **{a: set(render.OPS) for a in render.ARCHETYPES}}
    for a in doc["archetypes"]:
        assert set(a["story_ops"]) <= ops[a["id"]], a["id"]                                   # a marked op exists in its archetype
    camera = {"set_focus", "dolly", "focus"}
    assert not any(set(a["story_ops"]) & camera for a in doc["archetypes"])                   # VB-08: continuous camera moves stay silent


def test_a_manifest_built_on_another_spine_is_refused_cn_02(tmp_path):
    job, spine = comp_job(tmp_path, [("BALLISTIC_RANGE_AND_ENERGY_HUD", [("stamp", 5)])])
    path = job / "visual" / "visual_comp_manifest.json"
    stale = json.loads(path.read_text())
    stale["audio_spine"]["sha256"] = "0" * 64
    path.write_text(json.dumps(stale))
    with pytest.raises(ContractError, match="CN-02"):
        D.compensator_cues(job, spine, tmp_path / "lib", [])
