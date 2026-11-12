"""v4.3 plan P3 (GC-01..GC-17): turn packs out, intake gates in, free masters, the paid 2K re-make only as a priced request,
model names as dated data, the paid API off by default. Nothing here calls a network."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core import model_lifecycle_guard as MLG
from explainer_engine.core.errors import ContractError
from explainer_engine.imagegen import gemini as G
from explainer_engine.imagegen import turn_pack as T

LOOK = {"style_sentence": "A warm live-action adventure film frame, 35mm, natural skin, real cloth and stone.",
        "face_sentence": "Faces of adult actors with real skin texture and lived-in features."}


def _shot(sid, seg, people, place, size="medium_shot", end=False, route="still_25d", start="Kael lifts a torch."):
    return {"shot_id": sid, "segment_id": seg, "route": route, "character_ids": people, "location_id": place,
            "camera_spec": {"shot_size": size}, "action_start_state": start, "action_end_state": "Kael lowers the torch.",
            "lighting_and_time": "dusk, firelight", "screen_composition": {"background": "a ridge of ash"},
            "keyframe_plan": {"needs_start_frame": True, "needs_end_frame": end}}


def _episode(tmp_path, look=LOOK, shots=None, eid="ep_t"):
    root = tmp_path / eid
    (root / "story").mkdir(parents=True)
    (root / "episode.json").write_text(json.dumps({"episode_id": eid, "look": look, "image_native_min_long_side": 1376,
                                                   "image_min_long_side": 2752}), encoding="utf-8")
    script = {"schema_version": "4.0.0", "episode_id": eid,
              "world_bible": {"characters": [{"character_id": "kael", "name": "Kael",
                                              "fixed_appearance_prompt": "a lean man of thirty, sun-dark skin, black braid"},
                                             {"character_id": "sena", "name": "Sena",
                                              "fixed_appearance_prompt": "a woman of twenty-five, freckled, red ochre wrap"}],
                              "locations": [{"location_id": "camp", "name": "The ridge camp",
                                             "fixed_environment_prompt": "hide tents on a basalt ridge"}],
                              "props": []},
              "shots": shots if shots is not None else [
                  _shot("S1_SH1", "S1", ["kael", "sena"], "camp", end=True),
                  _shot("S1_SH2", "S1", ["kael"], "camp", size="close_up"),
                  _shot("S1_SH3", "S1", [], None, route="map_action", start="The ash cloud spreads west.")]}
    (root / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
    return root


def _pic(path: Path, size=(1376, 768), seed=0, bars=False):
    rng = np.random.default_rng(seed)
    a = rng.integers(30, 220, (size[1], size[0], 3), dtype=np.uint8)
    if bars:
        a[: size[1] // 10] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a).save(path)


def _items(root):
    return [it for p in sorted((root / "planning" / "turn_packs").glob("pack_*.json"))
            for it in json.loads(p.read_text())["items"]]


def test_export_waits_for_the_look_and_refuses_cartoon_faces(tmp_path):
    with pytest.raises(ContractError, match="look.style_sentence"):
        T.export(_episode(tmp_path, look={}))
    with pytest.raises(ContractError, match="GC-11"):
        T.export(_episode(tmp_path / "b", look=dict(LOOK, face_sentence="cute round faces, Pixar style")))


def test_export_writes_packs_anchors_first_refs_in_order_and_no_map_pictures(tmp_path):
    root = _episode(tmp_path)
    res = T.export(root, size=6)
    items = _items(root)
    ids = [i["id"] for i in items]
    assert ids[:3] == ["kael", "sena", "camp"] and all(not i["references"] for i in items[:3])          # GC-01
    sh1 = next(i for i in items if i["id"] == "S1_SH1_start")
    assert sh1["references"] == ["assets/reference/characters/kael.png", "assets/reference/characters/sena.png",
                                 "assets/reference/locations/camp.png"]                                   # GC-02 order
    end = next(i for i in items if i["id"] == "S1_SH1_end")
    assert end["references"][0] == "assets/generated/images/S1_SH1_start.png"                             # GC-09
    assert not any(i.get("shot_id") == "S1_SH3" for i in items)                                           # maps: Python
    assert all(i["prompt"].startswith(LOOK["style_sentence"]) for i in items)                            # GC-03
    assert res["packs"] and all(len(json.loads((root / "planning" / "turn_packs" / f"{p}.json").read_text())["items"]) <= 6
                                for p in res["packs"])
    md = (root / "planning" / "turn_packs" / f"{res['packs'][0]}.md").read_text()
    assert "Flash" in md and "never Argon" in md and "OWN message" in md                                 # GC-16, GC-17


def test_a_shot_whose_hero_has_no_registry_entry_stops_the_queue(tmp_path):
    root = _episode(tmp_path, shots=[_shot("S1_SH1", "S1", ["thar"], "camp")])
    with pytest.raises(ContractError, match="thar"):
        T.export(root)


def test_a_prompt_that_asks_for_lettering_fails(tmp_path):
    root = _episode(tmp_path, shots=[_shot("S1_SH1", "S1", ["kael"], "camp", start="Kael points at a carved sign.")])
    with pytest.raises(ContractError, match="GC-07"):
        T.export(root)


def test_intake_accepts_a_native_picture_as_a_draft_and_rejects_bad_ones(tmp_path):
    root = _episode(tmp_path)
    T.export(root)
    drop = tmp_path / "drop"
    _pic(drop / "kael.png", seed=1)
    _pic(drop / "sena.png", size=(1024, 576), seed=2)          # under the chat tool's native size
    _pic(drop / "camp.png", size=(1376, 1032), seed=3)         # 4:3
    _pic(drop / "S1_SH1_start.png", seed=4, bars=True)         # letterbox
    _pic(drop / "S1_SH2_start.png", seed=1)                    # the same picture as kael
    res = T.intake(root, drop)
    assert res["accepted"] == ["kael"]
    assert set(res["rejected"]) == {"sena", "camp", "S1_SH1_start", "S1_SH2_start"}
    rows = {r["id"]: r for r in T.ledger_rows(root)}
    assert rows["kael"]["grade"] == "draft" and len(rows["kael"]["sha256"]) == 64
    fails = {k: [g["gate"] for g in v["gates"] if g["status"] == "FAIL"] for k, v in rows.items()}
    assert fails["sena"] == ["native_size"] and fails["camp"] == ["aspect_16_9"]
    assert "no_letterbox" in fails["S1_SH1_start"] and "not_duplicate" in fails["S1_SH2_start"]
    assert res["sheet"] and (root / res["sheet"]).is_file()


def test_intake_refuses_a_pack_of_another_episode(tmp_path):
    root = _episode(tmp_path)
    T.export(root)
    p = root / "planning" / "turn_packs" / "pack_01.json"
    doc = json.loads(p.read_text())
    doc["episode_id"] = "ep_waterloo"
    p.write_text(json.dumps(doc))
    with pytest.raises(ContractError, match="GC-10"):
        T.intake(root)


def test_promote_is_not_run_without_an_upscaler_and_gates_the_master(tmp_path, monkeypatch):
    root = _episode(tmp_path)
    T.export(root)
    _pic(tmp_path / "drop" / "kael.png", seed=1)
    _pic(tmp_path / "drop" / "sena.png", seed=2)
    T.intake(root, tmp_path / "drop")
    monkeypatch.delenv(T.UPSCALER_ENV, raising=False)
    assert set(T.promote(root)["not_run"]) == {"kael", "sena"}

    def double(src, dst):
        with Image.open(src) as im:
            im.resize((im.size[0] * 2, im.size[1] * 2)).save(dst)

    res = T.promote(root, upscaler=double)
    assert set(res["promoted"]) == {"kael", "sena"}
    masters = [r for r in T.ledger_rows(root) if r.get("grade") == "master"]
    assert {r["id"] for r in masters} == {"kael", "sena"} and all(Path(root / r["file"]).is_file() for r in masters)
    assert T.promote(root, upscaler=double)["promoted"] == []          # a master is made once


def test_a_master_under_the_long_side_stays_a_draft(tmp_path):
    root = _episode(tmp_path)
    T.export(root)
    _pic(tmp_path / "drop" / "kael.png", seed=1)
    T.intake(root, tmp_path / "drop")

    def same(src, dst):
        Image.open(src).save(dst)

    res = T.promote(root, upscaler=same)
    assert res["promoted"] == [] and res["failed"][0]["id"] == "kael"


def test_remake_list_lists_only_failing_close_up_hero_shots_with_the_batch_price(tmp_path):
    root = _episode(tmp_path)
    assert T.remake_list(root, None)["status"] == "NOT_RUN"
    rows = {"S1_SH1": {"status": "FAIL", "detail": "soft face"}, "S1_SH2": {"status": "FAIL", "detail": "soft face"}}
    doc = T.remake_list(root, rows)
    assert [i["shot_id"] for i in doc["items"]] == ["S1_SH2"]          # S1_SH1 is a medium shot
    unit = G.BATCH_PRICES[T.REMAKE_MODEL][T.REMAKE_SIZE] + G.REFERENCE_USD
    assert doc["usd_total"] == pytest.approx(unit) and doc["status"] == "needs_creator_ok"
    assert (root / "planning" / "remake_2k.json").is_file()
    assert T.remake_list(root, {"S1_SH2": {"status": "PASS"}})["status"] == "nothing_to_remake"


def test_scene_picture_ids_skip_maps_and_count_end_frames(tmp_path):
    root = _episode(tmp_path)
    _, script = T.load(root)
    assert T.scene_picture_ids(script) == ["S1_SH1_start", "S1_SH1_end", "S1_SH2_start"]


def test_paid_calls_need_a_freshly_checked_vendor_entry():
    data = {"max_check_age_days": 30, "retired": {"old-model": {"replacement": "new"}},
            "active": {"fresh": {"source": "https://vendor/page", "checked": "2026-11-01"},
                       "archive": {"source": "the v4.3 archive", "checked": None}}}
    assert MLG.assert_fresh_for_paid_run("fresh", today=date(2026, 11, 12), data=data) == "fresh"
    with pytest.raises(MLG.ModelCheckStale):
        MLG.assert_fresh_for_paid_run("fresh", today=date(2026, 12, 15), data=data)
    with pytest.raises(MLG.ModelCheckStale):
        MLG.assert_fresh_for_paid_run("archive", today=date(2026, 11, 12), data=data)
    with pytest.raises(MLG.ModelCheckStale):
        MLG.assert_fresh_for_paid_run("unknown", today=date(2026, 11, 12), data=data)
    with pytest.raises(MLG.RetiredModelBlockedError):
        MLG.assert_fresh_for_paid_run("old-model", today=date(2026, 11, 12), data=data)


def test_no_archive_model_name_allows_a_paid_call():
    data = MLG.load()
    unchecked = [m for m, e in data["active"].items() if not e.get("checked")]
    assert "gemini-4-argon" in unchecked                                # GC-16: Argon is never a picture model anyway
    for m in unchecked:
        with pytest.raises(MLG.ModelCheckStale):
            MLG.assert_fresh_for_paid_run(m, today=date(2026, 11, 12))


def test_the_paid_api_route_is_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv(G.API_SWITCH, raising=False)
    c = G.GeminiClient(tmp_path, key="k", cap_usd=1.0)
    with pytest.raises(G.GeminiError, match="off"):
        c._http("gemini-nano-banana-2.1", {})
    with pytest.raises(G.GeminiError, match="off"):
        c._batch_http("GET", "https://x/y")


def test_export_after_intake_resumes_with_what_is_still_open(tmp_path):
    root = _episode(tmp_path)
    T.export(root)
    _pic(tmp_path / "drop" / "kael.png", seed=1)
    T.intake(root, tmp_path / "drop")
    res = T.export(root)
    new = [it["id"] for p in res["packs"] for it in json.loads((root / "planning" / "turn_packs" / f"{p}.json").read_text())["items"]]
    assert "kael" not in new and "sena" in new
    assert T.status(root)["accepted"] == 1


def test_an_identity_miss_is_review_and_listed(tmp_path):
    root = _episode(tmp_path)
    T.export(root)
    _pic(tmp_path / "drop" / "S1_SH2_start.png", seed=7)
    res = T.intake(root, tmp_path / "drop",
                   identity=lambda path, item: {"gate": "identity", "status": "REVIEW", "detail": "kael not matched"})
    assert res["accepted"] == ["S1_SH2_start"] and res["review"] == ["S1_SH2_start"]
