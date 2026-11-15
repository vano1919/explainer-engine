"""Regression guards for gaps in docs/wip/argon_2026-11-14/INCIDENT_AUDIT_2026-11-15.md (rows 51, 42, 60, 61, 65, 23).
Every test is synthetic and offline: no model weights, no network."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.maps import actions as MA
from explainer_engine.maps import data as MD
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.production import directed25d as R
from explainer_engine.production import living_director as LD
from explainer_engine.qa import motion_intent as MI

REPO = Path(__file__).resolve().parents[2]


def _misty_scene(dx: int, mist_seed: int, h: int = 360, w: int = 640) -> np.ndarray:
    cv2 = pytest.importorskip("cv2")
    r = np.random.default_rng(mist_seed)
    bg = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 9) * 60 + 205
    img = np.repeat(bg[..., None], 3, 2) + r.normal(0, 2, (h, w, 3))
    fx, fy = 300 + dx, 150                                           # a ~22 px face (about 66 px at 1080p)
    cv2.ellipse(img, (fx, fy), (11, 14), 0, 0, 360, (150, 115, 95), -1)
    cv2.circle(img, (fx - 4, fy - 3), 2, (40, 30, 30), -1)
    cv2.circle(img, (fx + 4, fy - 3), 2, (40, 30, 30), -1)
    cv2.line(img, (fx - 4, fy + 6), (fx + 4, fy + 6), (90, 40, 40), 1)
    return np.clip(img, 0, 255).astype(np.uint8)


# 51 -------------------------------------------------------------------------------------------------------------------
def test_small_face_with_background_warp_passes_face_intact(tmp_path):
    """#51: a small face shifted 3 px in moving mist (new mist each frame) must not trip the face_intact FAIL."""
    cv2 = pytest.importorskip("cv2")
    h, w = 360, 640
    first = _misty_scene(0, 1)
    Image.fromarray(first).save(tmp_path / "p.png")
    lay = {"manifest": {}, "depth": np.full((h, w), 0.3, np.float32), "plate": first,
           "hole": np.zeros((h, w), np.float32), "masks": {}, "lights": {}}
    plan = {"shot_id": "T", "frames": 24, "cameras": [], "handheld": None, "rack": None, "effects": [], "far_share": 0.2,
            "keep_in_frame": [{"face": [289 / w, 134 / h, 311 / w, 166 / h]}]}
    out = (480, 270)
    st = R.Stage(tmp_path / "p.png", lay, plan, out)
    kb = st.keep[0]
    template = st.face_crop(st.render(0), 0, kb)
    assert template is not None, "the face is large enough to be judged"
    for seed in (2, 3):                                              # a different mist each time
        later = cv2.resize(_misty_scene(3, seed), out, interpolation=cv2.INTER_AREA)
        ncc = st.face_likeness(template, later, 1, kb)
        assert ncc is not None and ncc >= MI.FACE_NCC_FAIL, ncc
        assert MI.face_intact_row({"ncc": ncc, "frame": 1, "faces": 1})["status"] == "PASS"


# 42 -------------------------------------------------------------------------------------------------------------------
def test_modern_bed_loses_to_period_bed(monkeypatch):
    """#42: a take tagged with a modern word ('garage') ranks below a fire take for 'brazier', even when it names the word."""
    from explainer_engine.episode import sound_plan as SP
    assert "garage" in LD.MODERN_WORDS
    garage = {"id": "burnt_garage_brazier", "tags": ["fire", "brazier", "garage"], "source": {"kind": "generated"}}
    fire = {"id": "campfire_crackle", "tags": ["fire", "campfire"], "source": {"kind": "generated"}}
    monkeypatch.setattr(SP, "_candidates", lambda cls, root: ([garage, fire], "legacy_tags"))
    ids, status, _ = LD._pick_take("fire", "unused", {"brazier"})
    assert status == "library" and ids[0] == "campfire_crackle" and ids.index("burnt_garage_brazier") > 0


# 60 -------------------------------------------------------------------------------------------------------------------
def test_map_events_use_the_timed_script():
    """#60: the counter's knock follows the measured word times, not the estimated ones (it was 0.4 s early)."""
    from explainer_engine.episode import events as EV
    lib = REPO / "assets" / "audio" / "library"
    text = "The killer lay four thousand miles away in the ash."
    shot = {"shot_id": "M1", "route": "map_action", "target_duration_seconds": 6.0, "audio_line_ids": ["L1"],
            "actions": [{"kind": "counter", "at_word": "four", "until_word": "ash", "value": 4000, "unit": "miles"}]}
    script = {"audio_lines": [{"line_id": "L1", "text": text}], "shots": [shot]}
    words = MA.shot_words(shot, script)
    spine = [{"word": w, "start_frame": 40 + 8 * i} for i, w in enumerate(words)]

    def knock(sp):
        out = LD.sound_of_map(shot, script, sp, fps=24, library_root=lib)
        return next(e["at_s"] for e in out["events"] if e["class"] == "ov_thud")

    timed, estimated = knock(spine), knock(None)
    assert timed != estimated
    ev = next(e for e in EV.visual_events(shot, script, spine, 24) if e["op"] == "counter")
    assert timed == round(ev["end_frame"] / 24 - LD.COUNTER_KNOCK_LEAD_S, 3)


def test_run_builds_anchor_rows_from_the_timed_script():
    """#60: the runner's anchor rows read ``TM.timed_script`` (the untimed script is the old bug)."""
    import inspect

    from explainer_engine.episode import run as RUN
    src = inspect.getsource(RUN._anchor_rows)
    assert "timed_script(" in src and "spines_of(" in src


# 61 -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("span_km", [1000.0, 100.0])
def test_marker_size_scales_with_view(span_km):
    """#61: a sector marker is a screen share (6-14 % of the frame height), never a constant km size that is a speck at
    1000 km and a blanket at 100 km."""
    w, h = 1920, 1080
    view = geo.View(2.0, 50.0, span_km, w, h)
    for km in (20.0, 60.0):
        d = MA._sector_diameter_px(km, view, float(h))
        assert MD.SECTOR_WIDTH_MIN_FRAC * h - 1e-6 <= d <= MD.SECTOR_WIDTH_MAX_FRAC * h + 1e-6
        assert d >= 0.03 * h


# 65 -------------------------------------------------------------------------------------------------------------------
def test_front_line_draws_two_colours():
    """#65: the Western Front line is blue on its west side and red on its east side."""
    w, h = 400, 400
    col = MA.colours()
    c = D.Canvas(w, h, background=(255, 255, 255), ss=1)
    unit = float(h)
    width = max(3.0, unit * 0.016)
    part = [(200.0, 20.0 + i * 12.0) for i in range(31)]            # north to south, straight down the middle
    MA._draw_dual_front_line(c, part, col, col["ink"], width, unit)
    px = np.asarray(c.im.convert("RGB"), dtype=np.float32)
    offset = max(1.8, width * 0.42)

    def near(x, target):
        patch = px[150:250, int(round(x)) - 1:int(round(x)) + 2].reshape(-1, 3)
        return float(np.linalg.norm(patch - np.array(target, np.float32), axis=1).min())

    allied, german = col["allied"], col["german"]
    assert np.linalg.norm(np.array(allied, np.float32) - np.array(german, np.float32)) > 120   # two different hues
    assert near(200 - offset, allied) < 40 and near(200 + offset, german) < 40
    assert near(200 - offset, german) > near(200 - offset, allied)
    assert near(200 + offset, allied) > near(200 + offset, german)


# 23 -------------------------------------------------------------------------------------------------------------------
def _documented_route_names(text: str) -> list[str]:
    names: list[str] = []
    for group in re.findall(r"\broutes?\s*\(((?:\s*`[a-z_0-9]+`\s*,?)+)\)", text):
        names += re.findall(r"`([a-z_0-9]+)`", group)
    return names


def test_documented_route_names_exist_in_the_router():
    """#23: a route named in PRODUCTION_RULES.md is a router route or a documented legacy alias (wan -> video)."""
    from explainer_engine.episode import router
    text = (REPO / "docs" / "PRODUCTION_RULES.md").read_text(encoding="utf-8")
    names = _documented_route_names(text)
    assert {"map_action", "still_25d"} <= set(names), names          # the parser still finds the G7 route list
    known = set(router.ROUTES) | set(router.LEGACY_ROUTES)
    assert all(v in router.ROUTES for v in router.LEGACY_ROUTES.values())
    unknown = [n for n in names if n not in known]
    assert not unknown, f"docs name routes the router does not know: {unknown}"
    assert _documented_route_names("G7 clips by route (`map_action`, `teleport`)")[1] not in known   # the check bites
