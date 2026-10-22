"""D-70 stage F: 2.5D parallax from a depth map, per-segment hashes (only what changed is made again), PV-53/PV-54."""
import copy
import json
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image

from explainer_engine.production import depth as D, parallax as PAR, segment_hash as SH

ROOT = Path(__file__).resolve().parents[2]
DOC = {"segments": [
    {"id": "S01", "lines": [{"text": "The wire hums.", "visual_beats": []}],
     "shots": [{"at": "The", "type": "A", "picture": {"id": "p1", "subject": "telegraph office"}, "motion": {"kind": "push", "z0": 1.0, "z1": 1.05}}]},
    {"id": "S02", "lines": [{"text": "Mira reads it twice."}],
     "shots": [{"at": "Mira", "type": "B", "picture": "p2", "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}}]},
]}


def stripes(w=64, h=36):
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[:, ::4] = 255
    return Image.fromarray(a)


def test_parallax_moves_near_parts_only_and_is_still_at_the_middle():
    frame = stripes()
    depth = np.zeros((36, 64), dtype=np.float32)
    depth[18:] = 1.0  # the lower half is near
    box, size = (0, 0, 64, 36), (64, 36)
    mid = PAR.shift(frame, depth, box, size, 0.5, 0.02)
    assert np.array_equal(np.asarray(mid), np.asarray(frame))  # u = 0.5: the picture as painted
    end = np.asarray(PAR.shift(frame, depth, box, size, 1.0, 0.02))
    src = np.asarray(frame)
    assert not np.array_equal(end[30], src[30])  # near rows moved
    assert not np.array_equal(end[2], src[2])  # far rows move the other way (relative to the mean depth)
    assert np.array_equal(np.asarray(PAR.shift(frame, depth, box, size, 1.0, 0.0)), src)  # no amount: flat
    flat = np.full((36, 64), 0.4, dtype=np.float32)
    assert np.array_equal(np.asarray(PAR.shift(frame, flat, box, size, 1.0, 0.02)), src)  # a flat map never moves


def test_parallax_amount_is_capped_and_follows_the_side_move():
    assert PAR.amount({"parallax": 0.5}) == PAR.MAX_AMP and PAR.amount({}) == 0.0
    assert PAR.direction({"dx": -0.05}) == -1.0 and PAR.direction({"x0": 0.0, "x1": 0.1}) == 1.0


def test_depth_map_lives_next_to_the_picture(tmp_path, monkeypatch):
    pic = tmp_path / "w_0001.png"
    stripes().save(pic)
    assert PAR.load(pic) is None
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "none"))
    assert D.ensure(pic) is None and D.main([str(pic)]) == 1  # no model: flat pictures, a clear exit

    class Fake:
        def get_inputs(self):
            return [type("I", (), {"name": "x"})()]

        def run(self, _out, feed):
            h, w = feed["x"].shape[2:]
            return [np.tile(np.linspace(0, 1, h, dtype=np.float32)[:, None], (1, w))[None]]

    made = D.ensure(pic, session=Fake())
    assert made == D.map_path(pic) and made.name == "w_0001.depth.png"
    dm = PAR.load(pic)
    assert dm.shape == (D.MAP_SIZE[1], D.MAP_SIZE[0]) and dm[-5].mean() > dm[5].mean()  # bottom nearer


def test_segment_hashes_name_only_what_changed():
    new = copy.deepcopy(DOC)
    assert SH.stale(DOC, new) == {}
    new["segments"][1]["lines"][0]["text"] = "Mira reads it three times."
    assert SH.stale(DOC, new) == {"S02": {"voice": True, "pictures": [], "edit": True}}
    new = copy.deepcopy(DOC)
    new["segments"][0]["shots"][0]["picture"]["subject"] = "a telegraph office at night"
    assert SH.stale(DOC, new) == {"S01": {"voice": False, "pictures": ["p1"], "edit": True}}
    new = copy.deepcopy(DOC)
    new["segments"][0]["shots"][0]["motion"]["z1"] = 1.08
    assert SH.stale(DOC, new) == {"S01": {"voice": False, "pictures": [], "edit": True}}
    new["segments"].append({"id": "S03", "lines": [{"text": "x"}], "shots": [{"picture": "p3"}]})
    del new["segments"][1]
    out = SH.stale(DOC, new)
    assert out["S02"]["removed"] and out["S03"] == {"voice": True, "pictures": ["p3"], "edit": True}
    assert SH.stale(SH.hashes(DOC), SH.hashes(DOC)) == {}


def test_pv53_asset_ids_and_bible_version():
    doc = copy.deepcopy(DOC)
    doc["segments"][0]["asset_ids"] = ["sheet.mira", "sprite.sci_newton"]
    found = SH.check(doc, library={"items": [{"id": "sprite.sci_newton"}]})
    assert [(f["rule"], f["where"]) for f in found] == [("PV-53", "S01")] and "sheet.mira" in found[0]["detail"]
    doc["bible"] = {"version": "9.9"}
    assert any(f["where"] == "bible" for f in SH.check(doc, library={"items": [{"id": "sheet.mira"}, {"id": "sprite.sci_newton"}]}))


def test_pv54_review_is_given_on_the_current_segment():
    doc = copy.deepcopy(DOC)
    h = SH.hashes(doc)["S01"]["edit"]
    doc["segments"][0]["review"] = {"status": "approved", "by": "ვანო", "hash": h}
    assert SH.check(doc) == []
    doc["segments"][0]["lines"][0]["text"] = "The wire sings."
    assert [(f["rule"], f["severity"]) for f in SH.check(doc)] == [("PV-54", "REVIEW")]
    doc["segments"][0]["review"] = {"status": "approved", "hash": SH.hashes(doc)["S01"]["edit"]}
    assert [f["severity"] for f in SH.check(doc)] == ["FAIL"]


def test_schema_takes_the_scene_package_fields():
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator({**schema["properties"]["segments"]["items"], "$defs": schema["$defs"]})
    good = {"id": "S01", "beat": "b", "light_beat": 1, "lines": [{"text": "x"}],
            "shots": [{"at": "x", "type": "A", "picture": "p1", "motion": {"kind": "push", "z0": 1.0, "z1": 1.05, "parallax": 0.012}}],
            "asset_ids": ["sheet.mira"], "new_assets": ["p1"], "review": {"status": "pending"}}
    assert not list(v.iter_errors(good))
    bad = copy.deepcopy(good)
    bad["shots"][0]["motion"]["parallax"] = 0.2
    bad["review"] = {"status": "ok"}
    assert len(list(v.iter_errors(bad))) == 2


def test_cli_prints_hashes_and_stale(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(DOC), encoding="utf-8")
    new = copy.deepcopy(DOC)
    new["segments"][1]["lines"][0]["text"] = "changed"
    b.write_text(json.dumps(new), encoding="utf-8")
    assert SH.main([str(a)]) == 0 and "S01" in capsys.readouterr().out
    assert SH.main([str(b), "--against", str(a)]) == 0
    assert json.loads(capsys.readouterr().out) == {"S02": {"voice": True, "pictures": [], "edit": True}}


def test_assemble_frame_draws_the_parallax_and_the_stamp_sees_a_new_depth_map(tmp_path):
    from explainer_engine.production import assemble as A

    im = stripes(128, 72)
    depth = np.zeros((72, 128), dtype=np.float32)
    depth[36:] = 1.0
    shot = {"id": "s1", "picture": "p1", "start_frame": 0, "end_frame": 10, "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0, "parallax": 0.02}}
    box = (0, 0, 128, 72)
    flat = A.finish_frame(im, box, {**shot, "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}}, 9, 30, (64, 36), [], {}, [], [], None, None, depth)
    moved = A.finish_frame(im, box, shot, 9, 30, (64, 36), [], {}, [], [], None, None, depth)
    assert not np.array_equal(np.asarray(flat), np.asarray(moved))
    pic = tmp_path / "p1.png"
    im.save(pic)
    timed = {"shots": [shot]}
    before = A.plan_stamp(timed, (64, 36), 20, None, [[0, 1]], {}, [tmp_path])
    Image.fromarray((depth * 255).astype(np.uint8)).save(tmp_path / "p1.depth.png")
    assert A.plan_stamp(timed, (64, 36), 20, None, [[0, 1]], {}, [tmp_path]) != before
