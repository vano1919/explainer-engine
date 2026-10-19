"""Expression sheets (VB-09, PV-44; the creator 2026-10-19): about ten close-ups per speaking hero on chroma green, painted
once from the hero's reference and reused; in dialogue the keyed close-up stands over the scene, zoomed in and blurred."""
import copy
import json

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.imagegen import plan as P
from explainer_engine.production import compile as C
from explainer_engine.production import faces as FACES
from explainer_engine.production import paint
from explainer_engine.production import script as S

from test_visual_beats import _check, _vb, beats_doc


def _sheet(d):
    return d["cast"]["einstein"]["face_sheet"]


def _close_up(path, bg=None, size=(60, 80)):
    im = Image.new("RGB", size, bg or FACES.key_rgb())
    ImageDraw.Draw(im).ellipse([12, 10, 48, 70], fill=(210, 150, 110))
    im.save(path)
    return path


def test_valid_sheet_has_no_vb09_finding_and_the_schema_takes_it():
    d = beats_doc()
    assert not S.schema_errors(d)
    assert not _vb(_check(d), "VB-09")
    assert set(FACES.BASE) <= set(FACES.DEFAULT_SET) and len(FACES.DEFAULT_SET) == FACES.SET_TARGET


def test_a_speaking_hero_without_a_sheet_fails_on_v2():
    d = beats_doc()
    del d["cast"]["einstein"]["face_sheet"]
    assert _vb(_check(d), "VB-09", "FAIL")


def test_sheet_size_base_expressions_and_beats_inside_the_set():
    d = beats_doc()
    _sheet(d)["set"] = ["neutral", "joyful", "sad", "scared", "angry"]  # 5, and surprised (a base one, and used) missing
    found = _vb(_check(d), "VB-09", "FAIL")
    details = " ".join(f["detail"] for f in found)
    assert "5 expressions" in details and "surprised" in details and "not in the face sheet" in details
    d = beats_doc()
    _sheet(d)["set"] = list(FACES.DEFAULT_SET) + ["amused", "smug"]  # smug twice
    assert S.schema_errors(d)  # uniqueItems
    d = beats_doc()
    d["segments"][1]["lines"][1]["visual_beats"][1]["expression"] = "deadpan"  # used, not in the sheet
    assert any("'deadpan' is not in the face sheet" in f["detail"] for f in _vb(_check(d), "VB-09", "FAIL"))


def test_the_sheet_needs_the_heroes_reference():
    d = beats_doc()
    _sheet(d)["ref"] = ""
    assert S.schema_errors(d)
    assert any("reference picture" in f["detail"] for f in _vb(FACES.lint(d), "VB-09", "FAIL"))


def test_to_paint_asks_for_one_close_up_per_expression_on_key_green_and_reuses_painted_ones(tmp_path):
    d = beats_doc()
    items = FACES.to_paint(d)
    assert [i["id"] for i in items] == [f"einstein_faces_v1_{e}" for e in FACES.DEFAULT_SET]
    it = items[0]
    assert FACES.key_hex() in it["prompt"] and FACES.DESCRIBE["neutral"] in it["prompt"]
    assert d["cast"]["einstein"]["card"].strip(" .") in it["prompt"] and it["refs"][0] == "duo.png"
    _close_up(tmp_path / "einstein_faces_v1_neutral.png")
    assert len(FACES.to_paint(d, [tmp_path])) == len(items) - 1  # painted once for the channel, never again


def test_chroma_key_removes_the_green_and_keeps_the_face(tmp_path):
    k = FACES.keyed(Image.open(_close_up(tmp_path / "f.png")))
    a = np.asarray(k)
    assert a[0, 0, 3] == 0 and a[40, 30, 3] == 255
    assert tuple(a[40, 30, :3]) == (210, 150, 110)
    assert FACES.border_keyed(Image.open(tmp_path / "f.png")) == 1.0
    assert FACES.border_keyed(Image.open(_close_up(tmp_path / "grey.png", bg=(120, 120, 120)))) == 0.0


def test_lint_with_files_flags_unpainted_and_badly_keyed_close_ups(tmp_path):
    d = beats_doc()
    for e in FACES.DEFAULT_SET:
        _close_up(tmp_path / f"einstein_faces_v1_{e}.png")
    assert not _vb(FACES.lint(d, [tmp_path]), "VB-09")
    _close_up(tmp_path / "einstein_faces_v1_sad.png", bg=(120, 120, 120))
    (tmp_path / "einstein_faces_v1_smug.png").unlink()
    found = " ".join(f["detail"] for f in _vb(FACES.lint(d, [tmp_path]), "VB-09", "REVIEW"))
    assert "smug is not painted yet" in found and "einstein_faces_v1_sad.png: the background" in found


def test_composite_blurs_the_scene_behind_the_close_up_and_rests_outside_dialogue(tmp_path):
    rng = np.random.default_rng(3)
    frame = Image.fromarray((rng.random((180, 320, 3)) * 255).astype(np.uint8))
    b = {"start_frame": 30, "end_frame": 90, "who": "einstein", "close_up": _close_up(tmp_path / "f.png"), "face": None}
    assert FACES.composite(frame, [b], 0, 30, ["einstein"]) is frame
    one = np.asarray(FACES.composite(frame, [b], 60, 30, ["einstein"])).astype(int)
    two = np.asarray(FACES.composite(frame, [b], 60, 30, ["einstein"])).astype(int)
    assert np.array_equal(one, two)
    assert np.abs(one[100, 115] - np.array([210, 150, 110])).max() < 4  # the close-up's face (first hero: the left side)
    assert one[:, 250:].std() < np.asarray(frame)[:, 250:].std() / 3  # the environment is blurred
    assert (one[:, 250:, 1] <= one[:, 250:].max(axis=2)).all() and one[5, 300, 1] < 200  # no key green on screen


def test_paint_plan_faces_is_a_reusable_plan_with_its_saving(tmp_path):
    d = C.compile_doc(beats_doc())
    (tmp_path / "script.json").write_text(json.dumps(d))
    out = tmp_path / "pictures"
    assert paint.main(["plan", str(tmp_path / "script.json"), "--out", str(out), "--id", "F1", "--provider", "pod",
                       "--faces"]) == 0
    plan = json.loads((out / "plans" / "F1.json").read_text())
    assert plan["reusable"] and "expression sheets of einstein" in plan["purpose"] and len(plan["items"]) == 10
    fs = plan["faces_saving"]
    assert fs["close_ups"] == 10 and fs["expression_changes"] == 2 and fs["usd_sheet"] > 0
    assert not [f for f in P.check(plan, d) if f["severity"] == "FAIL"]
    changed = copy.deepcopy(d)
    changed["cast"]["einstein"]["card"] += " Now with a hat."
    assert any(f["rule"] == "PP-06" for f in P.check(plan, changed))


def test_end_to_end_dialogue_renders_the_keyed_close_up(tmp_path, monkeypatch):
    import test_visual_beats as TVB
    calls = []
    real = FACES.composite

    def spy(frame, faces, f, fps, order):
        if faces:
            calls.append(f)
        return real(frame, faces, f, fps, order)

    monkeypatch.setattr(FACES, "composite", spy)
    pics = tmp_path / "pictures"
    pics.mkdir()
    for e in FACES.DEFAULT_SET:
        _close_up(pics / f"einstein_faces_v1_{e}.png")
    TVB.test_end_to_end_beats_render(tmp_path)
    assert calls  # the dialogue line's frames went through the composite


def test_one_framing_per_sheet_scales_a_wide_close_up_to_the_tightest(tmp_path):
    key = FACES.key_rgb()

    def hero(path, s, top):  # a head (ellipse) on shoulders (wide trapezoid) at scale s
        im = Image.new("RGB", (688, 384), key)
        d = ImageDraw.Draw(im)
        cx = 344
        d.ellipse([cx - 40 * s, top, cx + 40 * s, top + 100 * s], fill=(200, 160, 140))
        d.polygon([(cx - 30 * s, top + 90 * s), (cx + 30 * s, top + 90 * s), (cx + 160 * s, 384), (cx - 160 * s, 384)],
                  fill=(40, 40, 50))
        im.save(path)
        return path

    wide, tight = hero(tmp_path / "w.png", 1.0, 60), hero(tmp_path / "t.png", 1.6, 20)
    s, err = FACES.relative_scale(Image.open(wide), Image.open(tight))
    assert abs(s - 1 / 1.6) < 0.05 and err < 0.1
    out = FACES.same_framing([wide, tight], wide)
    a, b = (FACES._profile(out[p]) for p in (wide, tight))
    assert abs(a[1] - b[1]) <= 3 and abs(a[0][40] - b[0][40]) <= 6  # same head top, same width a little below it
