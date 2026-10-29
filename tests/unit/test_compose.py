"""AC-01..AC-14 (docs/ASSET_COMPOSE.md): shots composed from library assets, crowds, frame reuse and the style score, on
drawn test assets (no model, no money)."""

import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.compose import crowd as CR
from explainer_engine.compose import frame as FR
from explainer_engine.compose import reuse as RU
from explainer_engine.compose import style_score as SS
from explainer_engine.compose.library import Library, check_record

SRC = {"model": "Qwen/Qwen-Image-2512", "lora": "wldnk_style_v1.0", "prompt": "wldnk style, test", "seed": 7}


def _cut(path, colour, w=120, h=360, pad=40):
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([pad, pad, pad + w - 1, pad + int(h * 0.6)], fill=colour + (255,))                  # head and body
    for x in (pad + int(w * 0.15), pad + int(w * 0.6)):                                              # two legs
        d.rectangle([x, pad + int(h * 0.6), x + int(w * 0.25), pad + h - 1], fill=colour + (255,))
    im.save(path)


@pytest.fixture
def lib(tmp_path):
    bg = Image.new("RGB", (1600, 1200), (120, 160, 220))
    ImageDraw.Draw(bg).rectangle([0, 600, 1600, 1200], fill=(235, 235, 240))      # horizon at 0.5 of the plate
    bg.save(tmp_path / "plain.png")
    recs = [{"id": "background.plain", "kind": "background", "name": "plain", "path": "plain.png", "light": "low sun left",
             "horizon": 0.5, "source": SRC, "approved": True}]
    for name, col in (("old_man", (200, 40, 40)), ("nurse", (40, 40, 200))):
        for ang, face in (("front", None), ("three_quarter", "left")):
            p = f"{name}_{ang}.png"
            _cut(tmp_path / p, col)
            recs.append({"id": f"hero.{name}.{ang}", "kind": "hero", "name": name, "path": p, "angle": ang, "facing": face,
                         "expression": "neutral", "size_kind": "adult", "source": SRC, "approved": True})
    for i, col in enumerate(((90, 90, 90), (110, 70, 50), (60, 100, 60))):
        p = f"soldier_{i}.png"
        _cut(tmp_path / p, col)
        recs.append({"id": f"crowd.soldier_{i}", "kind": "crowd", "name": f"soldier_{i}", "path": p, "angle": "three_quarter",
                     "facing": "right", "size_kind": "adult", "source": SRC, "approved": True})
    return Library(tmp_path / "library.json", recs), tmp_path


def _two_shot(size="WS", **kw):
    return {"id": kw.get("id", "S1"), "size": size, "background": "plain", "items": [
        {"tag": "old man", "kind": "adult", "where": "left", "lead": True,
         "asset": {"name": "old_man", "angle": "three_quarter", "facing": "right", "expression": "neutral"}},
        {"tag": "nurse", "kind": "adult", "where": "right", "depth": 6,
         "asset": {"name": "nurse", "angle": "front", "expression": "neutral"}}], **{k: v for k, v in kw.items() if k != "id"}}


def test_records_and_mirroring(lib):
    L, _ = lib
    assert any(f["rule"] == "AC-01" for f in check_record({"id": "Hero One", "kind": "hero"}))
    assert check_record(L.get("hero.nurse.front")) == []
    # a three-quarter view facing the other way is the same drawing mirrored; a front view is never mirrored
    assert L.find("hero", "old_man", "three_quarter", "right") == {"id": "hero.old_man.three_quarter", "flip": True}
    assert L.find("hero", "old_man", "three_quarter", "left")["flip"] is False
    assert L.find("hero", "old_man", "side", "left") is None
    assert L.find("hero", "nurse", "front", expression="angry") is None
    assert L.find("hero", "nurse", "front", expression="any")["id"] == "hero.nurse.front"


def test_a_cut_out_with_a_snow_block_is_refused(tmp_path):
    from explainer_engine.compose.library import check_cutout
    _cut(tmp_path / "ok.png", (200, 40, 40))
    assert check_cutout(Image.open(tmp_path / "ok.png")) == []
    im = Image.open(tmp_path / "ok.png")
    ImageDraw.Draw(im).rectangle([0, 400, 199, 439], fill=(250, 250, 250, 255))   # a block of snow under the feet, cut
    rules = " ".join(f["detail"] for f in check_cutout(im))
    assert "ground patch" in rules and "edge" in rules


def test_needs_lists_only_what_is_missing(lib):
    L, _ = lib
    shot = _two_shot()
    shot["items"][1]["asset"]["expression"] = "shouting"
    need = L.needs([shot, dict(_two_shot(id="S2")), {"id": "S3", "reuse": "S1"}])
    assert need["wanted"] == 4 and need["reused"] == 3
    assert need["missing"] == [{"kind": "hero", "name": "nurse", "angle": "front", "expression": "shouting"}]


def test_figures_stand_in_their_boxes_far_to_near(lib):
    L, root = lib
    img, rec = FR.compose(_two_shot(), L, root)
    assert not [f for f in rec["findings"] if f["severity"] == "FAIL"]
    lay = FR.camera(_two_shot())["layout"]["items"]
    for item, p in zip(lay, sorted(rec["placed"], key=lambda p: p["tag"] != "old man")):
        x0, y0, x1, y1 = p["px"]                                              # the drawn body, padding cut away
        assert abs((y1 - y0) - item["height"] * 720) < 2 and abs(y1 - item["box"][3] * 720) < 2
    assert [p["tag"] for p in rec["placed"]] == ["nurse", "old man"]        # the farther figure is painted first
    a = np.asarray(img).astype(int)
    man = next(p for p in rec["placed"] if p["tag"] == "old man")
    fx = (man["px"][0] + man["px"][2]) // 2
    ground = round(FR.camera(_two_shot())["layout"]["items"][0]["box"][3] * 720)
    assert a[ground + 2, fx].sum() < a[ground + 2, 5].sum() - 30            # AC-07: a contact shadow under the feet


def test_a_short_plate_cannot_hold_a_low_horizon(lib):
    L, root = lib
    L.get("background.plain")["horizon"] = 0.05
    _, rec = FR.compose(_two_shot(angle="low"), L, root)
    assert any(f["rule"] == "AC-05" and f["severity"] == "FAIL" for f in rec["findings"])


def test_a_battle_band(lib):
    L, root = lib
    shot = _two_shot(crowd=[{"units": ["soldier_0", "soldier_1", "soldier_2"], "count": 60, "z": [20, 80], "seed": 3}])
    img, rec = FR.compose(shot, L, root)
    crowd = [p for p in rec["placed"] if p.get("crowd")]
    assert len(crowd) == 60 and not [f for f in rec["findings"] if f["severity"] == "FAIL"]
    zs = sorted(p["z"] for p in crowd)
    assert zs[30] > 50                     # more people far away, where the ground is wider
    again = CR.scatter(shot["crowd"][0], FR.camera(shot), L)
    assert CR.scatter(shot["crowd"][0], FR.camera(shot), L) == again and len(again) == 60      # the seed fixes the crowd
    one = {"units": ["soldier_0"], "count": 40, "z": [20, 60], "seed": 1, "facing": "right"}
    found = CR.check([one], CR.scatter(one, FR.camera(shot), L))
    assert {f["rule"] for f in found if f["severity"] == "FAIL"} == {"AC-10", "AC-11"}


def test_reuse_a_b_a_and_the_zoom_limit():
    a = _two_shot("MS", id="S1")
    b = {"id": "S2", "size": "MS", "background": "plain", "items": [
        {"tag": "girl", "kind": "adult", "where": "center", "lead": True, "asset": {"name": "girl", "angle": "front"}}]}
    a2 = _two_shot("MS", id="S3", push=1.2)
    tight = _two_shot("CU", id="S4")
    teaser = _two_shot("MS", id="S0", teaser_of="S3")
    plan = {p["id"]: p for p in RU.plan([teaser, a, b, a2, tight])}
    assert plan["S1"]["action"] == "compose" and plan["S2"]["action"] == "compose"
    assert plan["S3"] == {"id": "S3", "action": "reuse", "from": "S1", "crop": plan["S3"]["crop"], "zoom": 1.2, "ok": True}
    assert plan["S4"]["action"] == "compose"                     # MS -> CU would enlarge 2.2x
    assert plan["S0"]["action"] == "reuse" and plan["S0"]["from"] == "S3"
    assert RU.check(list(plan.values())) == []
    assert RU.check([{"id": "X", "action": "reuse", "from": "S1", "zoom": 2.2, "ok": False}])[0]["rule"] == "AC-13"


def test_style_score_is_relative_to_a_control():
    rng = np.random.default_rng(0)
    refs = [rng.normal(size=8) + 3 for _ in range(6)]
    good, off = refs[0] + rng.normal(size=8) * 0.1, -refs[0]
    assert SS.score(good, refs) > 0.9 > SS.score(off, refs)
    assert SS.verdict(0.40, 0.62)["severity"] == "REVIEW"
    assert SS.verdict(0.58, 0.62)["severity"] == "PASS"
    assert SS.verdict(0.58, None)["severity"] == "INFO"
    assert "FAIL" not in {SS.verdict(s, 0.9)["severity"] for s in (0.0, 0.5)}     # a hypothesis never fails a picture
    assert len(SS.crops(Image.new("RGB", (1280, 720)))) == SS.CROPS
