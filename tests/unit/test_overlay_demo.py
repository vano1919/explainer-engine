"""Pure parts of the overlay demo: the photo camera and the calm-zone choice (OV-34), spec/2 determinism, the procedural sound classes."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.overlay import camera as CAM
from explainer_engine.overlay import demo_script as D
from explainer_engine.overlay import demo_sound as S
from explainer_engine.overlay import place as PL
from explainer_engine.overlay import spec2

HERE = Path(spec2.__file__).parent
STYLE = json.loads((HERE / "demo_style.json").read_text())
WORDS = {l["no"]: l for l in json.loads((HERE / "demo_words.json").read_text())}


def info(faces=(), subject=((0.3, 0.3, 0.6, 0.9),), calm=None):
    return {"id": "T", "faces": [list(f) for f in faces], "subject": [list(s) for s in subject], "size": [2752, 1548],
            "calm": np.zeros((54, 96), np.float32) if calm is None else calm}


def test_camera_is_linear_and_clamped():
    s, cx, cy = CAM.cam((1.0, 1.1, 0.9, 0.1), 0, 100)
    assert s == 1.0 and (cx, cy) == (0.5, 0.5)                 # at scale 1 the crop is the whole picture
    s, cx, cy = CAM.cam((1.0, 1.1, 0.9, 0.1), 100, 100)
    assert abs(s - 1.1) < 1e-9 and cx <= 1 - 0.5 / 1.1 + 1e-9 and cy >= 0.5 / 1.1 - 1e-9
    mid = CAM.cam((1.0, 1.2, 0.5, 0.5), 50, 100)[0]
    assert abs(mid - 1.1) < 1e-9


def test_to_frame_matches_the_affine_that_draws_the_picture():
    c = CAM.cam((1.0, 1.08, 0.6, 0.45), 70, 120)
    a = CAM.affine(c, 2752, 1548)
    x0, y0, x1, y1 = CAM.to_frame((0.4, 0.3, 0.5, 0.5), c)
    # a frame pixel (x, y) reads the source pixel (a0 x + a2, a4 y + a5): the box corners must map back to the normalised corners
    assert abs((a[0] * x0 + a[2]) / 2752 - 0.4) < 1e-6 and abs((a[4] * y1 + a[5]) / 1548 - 0.5) < 1e-6
    assert abs((a[0] * x1 + a[2]) / 2752 - 0.5) < 1e-6


def test_place_avoids_faces_and_subject_on_every_frame():
    face = (0.10, 0.10, 0.20, 0.25)
    inf = info(faces=[face], subject=[(0.45, 0.3, 0.7, 0.95)])
    push, n = (1.0, 1.06, 0.5, 0.5), 240
    box = PL.choose(inf, (864, 486), push, n, "top_left", start=10, end=230)
    x, y, w, h = box
    prot = PL.protected(inf)
    for f in range(10, 231):
        cam = CAM.cam(push, f, n)
        assert not PL.hits((x, y, x + w, y + h), [CAM.to_frame(b, cam) for b in prot]), f
    assert PL.inside_margin((x, y, x + w, y + h))


def test_place_refuses_when_no_zone_is_free():
    inf = info(subject=[(0.0, 0.0, 1.0, 1.0)])
    with pytest.raises(ValueError):
        PL.choose(inf, (864, 486), (1.0, 1.0, 0.5, 0.5), 100, "top_left")


def test_spec2_is_deterministic_and_on_the_words():
    a, b = ({sh["no"]: spec2.build(sh, WORDS[sh["no"]], STYLE, {"M1": info(), "M3": info(), "C1": info()}) for sh in D.SHOTS} for _ in range(2))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    for no, sp in a.items():
        for it in sp["items"]:
            if it.get("word") and it["kind"] not in ("scale_bar",):
                w = it["word"].split()[0]
                assert any(x["word"] == w and abs(x["start_frame"] - it["start"]) <= 3 for x in sp["words"]), (no, it["id"])
        assert all(p["end"] <= sp["frames"] - 8 for p in sp["panels"])


def test_spec2_refuses_a_word_the_line_does_not_say():
    shot = {**D.SHOTS[2], "items": [{"kind": "label", "at": "zebra", "text": "x"}]}
    with pytest.raises(ContractError):
        spec2.build(shot, WORDS[3], STYLE, {"M1": info()})


def _library(tmp_path, origin="third_party"):
    """A small library with two real takes for every overlay gesture's class (W1: library only, no numpy sounds)."""
    from explainer_engine.audio import sfx_library as L
    from explainer_engine.episode import sound_plan as SP
    rng = np.random.default_rng(0)
    for k, cls in enumerate(sorted(set(S.LIBRARY_CLASS.values()))):
        for take in (1, 2):
            x = (rng.standard_normal(int(0.3 * S.SR)) * np.exp(-np.arange(int(0.3 * S.SR)) / 2000)).astype(np.float32)
            L.add(tmp_path, name=cls, take=take, category="foley", tags=SP.EVENT_CLASSES[cls]["tags"], samples=x, rate=S.SR,
                  source={"kind": origin, "prompt": "test"}, licence={"status": "cc0", "note": "test"})
    return tmp_path


def test_sound_classes_come_from_the_library_and_are_seeded(tmp_path):
    root = _library(tmp_path)
    for cls in S.CLASSES:
        a = S.render_class(cls, 18, np.random.default_rng(3), root)
        b = S.render_class(cls, 18, np.random.default_rng(3), root)
        assert np.array_equal(a, b) and abs(float(np.max(np.abs(a))) - 1.0) < 1e-5
    for cls in ("pencil_scribble", "air_swell", "slide_grow"):          # the long classes are as long as their motion
        assert abs(len(S.render_class(cls, 36, np.random.default_rng(1), root)) / S.SR - 1.5) < 0.01
    with pytest.raises(KeyError):
        S.render_class("beep", 10, np.random.default_rng(1), root)


def test_a_procedural_take_never_plays(tmp_path):
    from explainer_engine.core.errors import ContractError
    root = _library(tmp_path, origin="procedural")
    with pytest.raises(ContractError):
        S.render_class("tick", 10, np.random.default_rng(1), root)
    assert "tick" in S.needs(["tick"], root)
    assert not hasattr(S, "sine") and not hasattr(S, "ambience")      # the numpy generators are gone (OV-56 as changed)
