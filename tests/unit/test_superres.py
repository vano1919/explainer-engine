"""Upscale direction II (2026-11-14): the U-1..U-8 decision from the script, the Q1..Q7 QC on synthetic pictures, the cache
key, NOT_RUN without the model, the fallback chain with an injected model, and GC-14's promote using it. No media, no weights."""
from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from explainer_engine.core.errors import ConfigError  # noqa: E402
from explainer_engine.finish import superres as S  # noqa: E402


def _pic(w=160, h=96, seed=3, sigma=1.2):
    rng = np.random.default_rng(seed)
    t = cv2.GaussianBlur(rng.uniform(0, 255, (h, w, 3)).astype(np.float32), (0, 0), sigma)
    return np.clip(t, 0, 255).astype(np.uint8)


def _shot(route, **ep):
    return {"shot_id": "S1", "route": route, "edit_plan": ep}


@pytest.mark.parametrize("shot,ctx,rule,action", [
    (_shot("video", continuity_mode="coverage"), None, "U-1", "none"),
    (_shot("video", continuity_mode="continuation", continue_frame={"pick": "best_tail"}), None, "U-2", "as_is"),
    (_shot("video", continuity_mode="continuation", continue_frame={"crop": [0.1, 0, 0.77, 0.67]},
           state_changed_since_anchor=False), None, "U-3", "anchor_photo_crop"),
    (_shot("video", continuity_mode="continuation", continue_frame={"crop": [0.1, 0, 0.77, 0.67]},
           state_changed_since_anchor=True), None, "U-3", "model_x4_crop"),
    (_shot("still_25d", next_use="still", state_changed_since_anchor=False), None, "U-4", "anchor_photo"),
    ({**_shot("still_25d", state_changed_since_anchor=True), "start_from": "video_frame"}, None, "U-4", "model_x2"),
    ({**_shot("still_25d"), "max_zoom": 1.25}, {"picture_width": 2752}, "U-5", "model_x2"),
    ({**_shot("still_25d"), "max_zoom": 1.05}, {"picture_width": 2752}, "U-5", "none"),
    (_shot("still_25d"), {"purpose": "promote"}, "U-6", "model_x2"),
    (_shot("map_action"), None, "U-7", "none"),
])
def test_decide_every_rule(shot, ctx, rule, action):
    d = S.decide(shot, ctx)
    assert (d["rule"], d["action"]) == (rule, action) and d["why"]


def test_video_delivery_is_lanczos_u8_and_a_missing_state_is_flagged():
    d = S.decide(_shot("video", continuity_mode="continuation", continue_frame={"crop": [0, 0, 0.67, 0.67]}))
    assert d["delivery"] == "lanczos" and d["action"] == "model_x4_crop" and d["review"] and "assumed changed" in d["why"]
    assert S.decide(_shot("map_action"))["delivery"] == "none"
    assert [x["rule"] for x in S.plan({"shots": [_shot("map_action"), _shot("video", continuity_mode="insert")]})] == ["U-7", "U-1"]


def test_qc_good_colour_shift_oversharp_and_structure_change():
    small = _pic()
    big = _pic(320, 192, sigma=0.8)                        # a "true" 2x picture: fine detail, same layout
    good = big                                             # what a good model gives back: fine detail a resize cannot
    src = cv2.resize(good, (160, 96), interpolation=cv2.INTER_AREA)
    rows = {r["gate"]: r for r in S.qc(src, good)}
    assert rows["Q1_structure"]["status"] == "PASS" and rows["Q2_colour"]["status"] == "PASS"
    assert rows["Q3_detail_added"]["status"] == "PASS" and rows["Q5_nothing_invented"]["status"] == "NOT_RUN"
    assert rows["Q7_better"]["status"] == "REVIEW" and S.accepted(list(rows.values())) is False   # Q5 not measured
    lp = lambda a, b: 0.05                                 # noqa: E731
    assert S.accepted(S.qc(src, good, lp=lp))
    shifted = np.clip(good.astype(np.int16) + np.array([0, 0, 12]), 0, 255).astype(np.uint8)
    assert {r["gate"]: r["status"] for r in S.qc(src, shifted, lp=lp)}["Q2_colour"] == "REVIEW"
    anchor = cv2.GaussianBlur(good, (0, 0), 2.0)
    assert {r["gate"]: r["status"] for r in S.qc(src, good, anchor=anchor, lp=lp)}["Q4_not_oversharp"] == "REVIEW"
    other = _pic(320, 192, seed=9)                         # a different picture: the structure changed
    rows = {r["gate"]: r["status"] for r in S.qc(src, other, lp=lp)}
    assert rows["Q1_structure"] == "REVIEW" and rows["Q7_better"] == "REVIEW"
    assert small.shape == (96, 160, 3)


def test_cache_key_and_to_size():
    a, b = b"one", b"two"
    assert S.cache_key(a, "span2x") != S.cache_key(b, "span2x") != S.cache_key(a, "realplksr4x")
    assert S.cache_key(a, "span2x", [0, 0, 0.5, 0.5]) != S.cache_key(a, "span2x")
    img = _pic(64, 32)
    assert S.to_size(img, 32, 16).shape == (16, 32, 3)
    with pytest.raises(ConfigError):
        S.to_size(img, 128, 64)


def test_not_run_without_the_model(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_MODELS_DIR", str(tmp_path / "none"))
    S._LOADED.clear()
    assert not S.available()
    r = S.upscale(_pic(), tmp_path, "p", lp=None)
    assert r["status"] in ("NOT_RUN", "REVIEW") and r["model"] is None
    assert all(t["status"] == "NOT_RUN" for t in r["tries"])


def _fake(mode):
    def loader(model_id):
        s = S.MODELS[model_id]["scale"]

        def fn(rgb):
            up = cv2.resize(rgb, (rgb.shape[1] * s, rgb.shape[0] * s), interpolation=cv2.INTER_CUBIC)
            if mode(model_id) == "sharp":
                up = np.clip(up * 3.0 - cv2.GaussianBlur(up, (0, 0), 1.0 * s / 2) * 2.0, 0, 1)
            elif mode(model_id) == "colour":
                up = np.clip(up + np.array([0.2, 0, 0], np.float32), 0, 1)
            return up.astype(np.float32)
        fn.scale = s
        return fn
    return loader


def test_the_fallback_chain_with_an_injected_model(tmp_path):
    img = _pic(96, 64)
    lp = lambda a, b: 0.05                                 # noqa: E731
    first = S.upscale(img, tmp_path, "a", loader=_fake(lambda m: "sharp"), lp=lp)
    assert first["status"] == "PASS" and first["model"] == "realplksr4x" and first["size"] == [192, 128]
    again = S.upscale(img, tmp_path, "a", loader=_fake(lambda m: "sharp"), lp=lp)
    assert again["tries"][0]["cached"] is True
    fb = S.upscale(img, tmp_path, "b", loader=_fake(lambda m: "colour" if m == "realplksr4x" else "sharp"), lp=lp)
    assert fb["model"] == "span2x" and not fb["tries"][0]["accepted"]
    none = S.upscale(img, tmp_path, "c", loader=_fake(lambda m: "colour"), lp=lp)
    assert none["status"] == "REVIEW" and none["model"] is None and none["result"].endswith("c.as_is.png")


def test_promote_uses_superres_when_it_is_available(tmp_path, monkeypatch):
    from explainer_engine.imagegen import turn_pack as T
    monkeypatch.delenv(T.UPSCALER_ENV, raising=False)
    monkeypatch.setattr(S, "available", lambda *a: True)
    calls = []
    monkeypatch.setattr(S, "upscale_file", lambda src, dst, factor=2: calls.append((src, dst, factor)))
    up = T.find_upscaler()
    up(tmp_path / "a.png", tmp_path / "b.png")
    assert calls == [(tmp_path / "a.png", tmp_path / "b.png", 2)]
    monkeypatch.setattr(S, "available", lambda *a: False)
    assert T.find_upscaler() is None


def test_colour_fix_keeps_detail_and_restores_the_colour():
    src = _pic(96, 64)
    big = cv2.resize(src, (384, 256), interpolation=cv2.INTER_CUBIC)
    sat = np.clip(big.astype(np.int16) * np.array([1.0, 1.0, 1.25]) - np.array([0, 0, 10]), 0, 255).astype(np.uint8)
    fixed = S.colour_fix(sat, src)
    shift = lambda x: float(np.abs(cv2.resize(x, (96, 64), interpolation=cv2.INTER_AREA).reshape(-1, 3).mean(0)  # noqa: E731
                                   - src.reshape(-1, 3).mean(0)).max())
    assert shift(sat) > 5 and shift(fixed) < 1.5
    assert S.MODELS["realplksr4x"]["colour_fix"] and S.MODELS["span2x"]["colour_fix"]
