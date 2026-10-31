"""The shot router (P6, edit/router.py): film_shots/2 -> shot_spec/1 files + shots/route.json, all derived (CN-02); the lanes the
creator refused never reach it (D-89, A2); a derived continuity_card/2 takes its camera side from the scene_set/1 (CT-06)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.core import contracts as C
from explainer_engine.core import shot_cache
from explainer_engine.core.errors import ContractError
from explainer_engine.edit import router as R
from explainer_engine.scripting import continuity as CT

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "contracts"
H = [c * 64 for c in "0123456789abcdef"]
PINS = {"models": {
    "keyframe": {"id": "Qwen/Qwen-Image-2.1", "revision": "r-keyframe", "sha256": None},
    "video_ltx": {"id": "Lightricks/LTX-Video-0.9.8-13B-distilled", "revision": "r-ltx", "sha256": None, "params": {"steps": 8}},
    "loras": {"xworld_v2": {"id": "xworld_v2", "sha256": H[6], "weight": 0.7}},
}}


def load(*parts) -> dict:
    return json.loads(FIX.joinpath(*parts).read_text(encoding="utf-8"))


def put(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def sha(path: Path) -> str:
    return C.sha256_file(path)


def make_job(tmp_path: Path, *, lanes=("KEYFRAME_LTX", "DIALOGUE_CU", "MAP"), window="clip", comp=True) -> dict:
    """A job folder: three shots (one per lane in ``lanes``), an audio_spine/2 with a window for s2, a comp manifest for s3."""
    fs = load("film_shots_2", "valid.json")
    third = copy.deepcopy(fs["shots"][0])
    third["id"] = "s3"
    fs["shots"].append(third)
    for shot, lane in zip(fs["shots"], lanes):
        shot["lane"] = lane
    for shot in fs["shots"]:
        if shot["lane"] == "MAP":
            shot["archetype"] = "TACTICAL_UNIT_MANEUVER"
    fs_path = put(tmp_path / "film_shots.json", fs)
    bin_path = tmp_path / "x" / "file.bin"
    bin_path.parent.mkdir(parents=True)
    bin_path.write_bytes(b"x")
    spine = load("audio_spine", "valid_v2_clip.json")
    spine["derived_from"] = {k: {"path": "x/file.bin", "sha256": sha(bin_path)} for k in spine["derived_from"]}
    spine["derived_from"]["film_shots"] = {"path": "film_shots.json", "sha256": sha(fs_path)}
    spine["post_hoc_shots"][0]["shot_id"] = "s2"
    if window == "planned":
        spine["post_hoc_shots"][0].update(source="planned", clip_sha256=None)
    if window == "none":
        spine["post_hoc_shots"] = []
    spine_path = put(tmp_path / "audio" / "audio_spine.json", spine)
    out = {"fs": fs_path, "spine": spine_path, "fs_doc": fs, "comp": None}
    if comp:
        manifest = load("visual_comp_manifest", "valid.json")
        manifest["audio_spine"] = {"path": "audio/audio_spine.json", "sha256": sha(spine_path)}
        manifest["items"][0]["shot_id"] = "s3"
        out["comp"] = put(tmp_path / "visual" / "visual_comp_manifest.json", manifest)
    return out


def refresh(tmp_path: Path, job: dict) -> None:
    """After the hand-written cards change, the derived spine (and the manifest on it) name the new hashes, as a compiler would."""
    spine = json.loads(job["spine"].read_text(encoding="utf-8"))
    spine["derived_from"]["film_shots"]["sha256"] = sha(job["fs"])
    put(job["spine"], spine)
    manifest = json.loads(job["comp"].read_text(encoding="utf-8"))
    manifest["audio_spine"]["sha256"] = sha(job["spine"])
    put(job["comp"], manifest)


def run(tmp_path, job, **kw):
    return R.route(job["fs"], tmp_path, job_id="job-001", pins=PINS, comp_manifest=job["comp"], audio_spine=job["spine"], **kw)


def spec_files(tmp_path):
    return sorted((tmp_path / "shots").glob("*.spec.json"))


def keys(tmp_path):
    return {p.name: shot_cache.key(json.loads(p.read_text(encoding="utf-8"))) for p in spec_files(tmp_path)}


def test_a_every_spec_and_the_route_pass_the_contracts(tmp_path):
    job = make_job(tmp_path)
    out = run(tmp_path, job)
    assert [r["shot_id"] for r in out["routes"]] == ["s1", "s2", "s3"]
    assert [p.name for p in spec_files(tmp_path)] == ["s1.still.spec.json", "s1.video.spec.json", "s2.still.spec.json", "s2.video.spec.json"]
    for p in spec_files(tmp_path):
        C.validate(json.loads(p.read_text(encoding="utf-8")))
    C.validate(json.loads((tmp_path / "shots" / "route.json").read_text(encoding="utf-8")), tmp_path)  # fresh inputs
    assert C.main(["check", *map(str, spec_files(tmp_path)), str(tmp_path / "shots" / "route.json"), "--base", str(tmp_path)]) == 0
    still = json.loads((tmp_path / "shots" / "s1.still.spec.json").read_text(encoding="utf-8"))
    video = json.loads((tmp_path / "shots" / "s1.video.spec.json").read_text(encoding="utf-8"))
    assert still["frames"] is None and video["frames"] == 241 and still["loras"][0]["weight"] == 0.7
    assert video["refs"][0]["sha256"] == out["routes"][0]["specs"][0]["cache_key"]  # the clip depends on its keyframe's spec
    assert video["audio_slice_sha256"] is None and video["params"] == {"steps": 8}


def test_b_routing_twice_gives_identical_files(tmp_path):
    job = make_job(tmp_path)
    run(tmp_path, job)
    first = {p.name: p.read_bytes() for p in [*spec_files(tmp_path), tmp_path / "shots" / "route.json"]}
    run(tmp_path, job)
    assert first == {p.name: p.read_bytes() for p in [*spec_files(tmp_path), tmp_path / "shots" / "route.json"]}


def test_c_one_changed_word_changes_exactly_one_cache_key(tmp_path):
    job = make_job(tmp_path)
    run(tmp_path, job)
    before = keys(tmp_path)
    job["fs_doc"]["shots"][0]["sound"] = {"ambience": "wind"}   # a word in s1's video prompt only
    put(job["fs"], job["fs_doc"])
    refresh(tmp_path, job)
    run(tmp_path, job)
    after = keys(tmp_path)
    assert [n for n in after if after[n] != before[n]] == ["s1.video.spec.json"]


def test_d_a_map_shot_has_no_spec_and_points_at_its_comp_item(tmp_path):
    job = make_job(tmp_path)
    out = run(tmp_path, job)
    s3 = out["routes"][2]
    assert s3["specs"] == [] and s3["comp_items"] == ["m1"] and not list((tmp_path / "shots").glob("s3.*"))
    with pytest.raises(ContractError, match="visual_comp_manifest"):
        R.route(job["fs"], tmp_path, job_id="job-001", pins=PINS, audio_spine=job["spine"])   # no manifest at all
    manifest = json.loads(job["comp"].read_text(encoding="utf-8"))
    manifest["items"][0]["shot_id"] = "s1"
    put(job["comp"], manifest)
    with pytest.raises(ContractError, match="s3"):
        run(tmp_path, job)   # a manifest with no item for s3


def test_e_a_dialogue_shot_needs_a_recorded_spine_window(tmp_path):
    job = make_job(tmp_path, window="none")
    with pytest.raises(ContractError, match="DIALOGUE_CU has no window"):
        run(tmp_path, job)
    with pytest.raises(ContractError, match="audio_spine/2"):
        R.route(job["fs"], tmp_path, job_id="job-001", pins=PINS, comp_manifest=job["comp"])
    job = make_job(tmp_path / "planned", window="planned")
    with pytest.raises(ContractError, match="still planned"):
        run(tmp_path / "planned", job)
    job = make_job(tmp_path / "ok")
    run(tmp_path / "ok", job)
    video = json.loads((tmp_path / "ok" / "shots" / "s2.video.spec.json").read_text(encoding="utf-8"))
    assert video["audio_slice_sha256"] == "b" * 64


def test_f_every_spec_runs_at_the_cards_fps(tmp_path):
    job = make_job(tmp_path)
    out = run(tmp_path, job)
    assert out["fps"] == job["fs_doc"]["fps"]
    assert {json.loads(p.read_text(encoding="utf-8"))["fps"] for p in spec_files(tmp_path)} == {job["fs_doc"]["fps"]}
    manifest = load("job_manifest", "valid.json")
    manifest["fps"] = 30
    put(tmp_path / "job_manifest.json", manifest)
    with pytest.raises(ContractError, match="CN-09"):
        run(tmp_path, job)


def scene_set_and_card(z_second: float):
    sset = load("scene_set", "valid.json")
    sset["axis"] = {"deg": 0, "origin": [0, 0]}
    sset["cameras"] = [{**sset["cameras"][0], "shot_id": "S04-01", "pos": [0, 1.6, -3]},
                       {**sset["cameras"][0], "shot_id": "S04-02", "pos": [0, 1.6, z_second]},
                       {**sset["cameras"][0], "shot_id": "S04-03", "pos": [0, 1.6, z_second]}]
    card = json.loads((ROOT / "examples" / "continuity" / "napoleon_tent.json").read_text(encoding="utf-8"))
    return sset, card


def test_g_camera_on_the_far_side_of_the_axis_flips_the_side_and_ct06_reports_it():
    sset, card = scene_set_and_card(+3)
    assert CT.check(card) == []
    v2 = CT.derive_card_v2(card, sset)
    assert v2["schema"] == "continuity_card/2" and v2["derived_from"]["scene_set"]["path"] == "sets/tent.json"
    assert [s["camera_side"] for s in v2["shots"][:2]] == ["B", "A"] and v2["shots"][0]["camera"]["axis_cross"] == -3
    found = CT.check(v2)
    assert [(f["rule"], f["shot"]) for f in found if f["rule"] == "CT-06"] == [("CT-06", "S04-02")]
    sset, card = scene_set_and_card(-3)   # same side: nothing to report
    assert not [f for f in CT.check(CT.derive_card_v2(card, sset)) if f["rule"] == "CT-06"]
    assert card["schema"] == "continuity_card/1"   # the input is not touched
    assert {lm["id"] for lm in v2["location"]["landmarks"]} >= {"map_table", "table"}   # the set's landmark object joins the card's


def test_g3_the_scene_set_ref_hashes_the_file_not_a_reserialised_dict(tmp_path):
    sset, card = scene_set_and_card(+3)
    path = tmp_path / "tent.json"
    path.write_text(json.dumps(sset), encoding="utf-8")   # compact bytes: not what json.dumps(indent=2) would give
    ref = CT.derive_card_v2(card, path)["derived_from"]["scene_set"]
    assert ref == {"path": "sets/tent.json", "sha256": sha(path)}
    assert ref["sha256"] != CT.derive_card_v2(card, sset)["derived_from"]["scene_set"]["sha256"]


def test_g2_a_camera_on_the_axis_has_no_side_and_a_v1_card_may_not_name_a_set():
    sset, card = scene_set_and_card(0)
    with pytest.raises(ContractError, match="no side"):
        CT.derive_card_v2(card, sset)
    card["derived_from"] = {"scene_set": {"path": "sets/tent.json", "sha256": H[1]}}
    assert any(f["rule"] == "CT-01" for f in CT.check(card))


@pytest.mark.parametrize("name,cite", [("host_lane", "D-89"), ("3d_lane", "A2")])
def test_h_the_refused_lanes_never_reach_the_router(tmp_path, name, cite):
    fs = load("film_shots_2", f"invalid__{name}.json")
    path = put(tmp_path / "film_shots.json", fs)
    with pytest.raises(ContractError, match=cite):
        R.route(path, tmp_path, job_id="job-001", pins=PINS)
    assert not (tmp_path / "shots").exists()


def test_an_undecided_model_or_a_fourth_try_is_refused(tmp_path):
    job = make_job(tmp_path)
    pins = copy.deepcopy(PINS)
    pins["models"]["video_ltx"]["revision"] = None
    with pytest.raises(ContractError, match="not decided"):   # a null revision/sha256 refuses the video lane (injected pin)
        R.route(job["fs"], tmp_path, job_id="job-001", pins=pins, comp_manifest=job["comp"], audio_spine=job["spine"])
    with pytest.raises(ContractError, match="tries per shot"):
        run(tmp_path, job, attempt=4)
    run(tmp_path, job, attempt=2)
    assert json.loads((tmp_path / "shots" / "s1.still.spec.json").read_text(encoding="utf-8"))["seed"] == 1337


def test_the_real_pins_file_lists_the_lora_and_the_keyframe_model():
    from explainer_engine.cloud import pins
    models = pins.load()["models"]
    assert models["loras"]["xworld_v2"]["weight"] == 0.7 and models["keyframe"]["revision"]


def test_a_shot_route_must_name_fresh_inputs(tmp_path):
    job = make_job(tmp_path)
    run(tmp_path, job)
    route = json.loads((tmp_path / "shots" / "route.json").read_text(encoding="utf-8"))
    job["fs_doc"]["shots"][0]["seconds"] = 11
    put(job["fs"], job["fs_doc"])
    assert any(f["rule"] == "CN-02" for f in C.errors(route, tmp_path))


def test_the_real_pins_route_a_valid_keyframe_ltx_shot_to_a_still_and_a_video_spec(tmp_path):
    """config/cloud_pins.json (not an injected pin): the video model has its HF revision, the LoRA is xworld_v2 at 0.7 (creator
    2026-10-31), so a valid KEYFRAME_LTX shot produces a still spec and a video spec."""
    job = make_job(tmp_path)
    out = R.route(job["fs"], tmp_path, job_id="job-001", comp_manifest=job["comp"], audio_spine=job["spine"])   # pins=None: the real file
    assert [s["role"] for s in out["routes"][0]["specs"]] == ["still", "video"]
    still = json.loads((tmp_path / "shots" / "s1.still.spec.json").read_text(encoding="utf-8"))
    video = json.loads((tmp_path / "shots" / "s1.video.spec.json").read_text(encoding="utf-8"))
    assert video["model"] == {"id": "Lightricks/LTX-Video-0.9.8-13B-distilled", "sha256": None,
                              "revision": "7c64400e1861cc0d7b98d570a1926d5408ec60cd"}
    assert video["frames"] == 241 and video["refs"][0]["role"] == "keyframe"
    assert still["loras"] == [{"id": "xworld_v2", "sha256": "f5c420a1597a1fa585fc560f5eaaafef292006e6e6d93b65e4e645facb560b02", "weight": 0.7}]
    assert C.main(["check", *map(str, spec_files(tmp_path)), str(tmp_path / "shots" / "route.json"), "--base", str(tmp_path)]) == 0


def test_a_per_shot_attempt_map_reseeds_only_the_named_shot_and_keeps_the_others_specs(tmp_path):
    job = make_job(tmp_path)
    run(tmp_path, job)
    first = keys(tmp_path)
    run(tmp_path, job, attempt={"s1": 2})
    second = keys(tmp_path)
    seed = lambda n: json.loads((tmp_path / "shots" / n).read_text(encoding="utf-8"))["seed"]   # noqa: E731
    assert seed("s1.still.spec.json") == 1337 and seed("s2.still.spec.json") == 42
    changed = {n for n in first if first[n] != second.get(n)}
    assert changed and all(n.startswith("s1.") for n in changed)                    # no other shot's spec or cache key moved
    with pytest.raises(ContractError, match="tries per shot"):
        run(tmp_path, job, attempt={"s1": 4})
    assert "Retry k" in (R.route.__doc__ or "") and "REWEIGHT_REFERENCES" in R.route.__doc__
