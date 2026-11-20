"""``qa/send_validators.living_motion`` on the analyst's REAL clips (BP-215 calibration, lead's order 2026-11-20 13:13): run1 (X1 = the first 2.5D
pass, X4 = camera-only controls and their production twins) and run2 (4 photos x still, nop, drift). The clips live in the project files, not in the repo:
the tests skip where the folder is absent (CI). Calibrated on S07_SH006, S07_SH008 and S04_SH008; S04_SH014 is the held-out check (never tuned on).
A validator that fails every real clip proves nothing, and one that passes the controls proves nothing either: both sides are asserted."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.qa import send_validators as V

ROOT = Path("/mnt/project-files/explainer-engine/skills_team_2026-11-20_g1/L14_2p5d")
RUN1, RUN2 = ROOT / "run1" / "clips", ROOT / "run2" / "clips"
pytestmark = [pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg"),
              pytest.mark.skipif(not RUN1.is_dir() or not RUN2.is_dir(), reason="the analyst's real clips are not on this machine")]

RUN2_CLIPS = [f"R2_{photo}_{kind}" for photo in ("S07_SH006", "S07_SH008", "S04_SH008", "S04_SH014") for kind in ("still", "nop", "drift")]


@pytest.mark.parametrize("name", RUN2_CLIPS)
def test_every_run2_clip_passes_in_its_declared_zones(name):
    """Alive by eye (the lead and the owner saw them): still, without particles (nop) and drifting; S04_SH014 is the held-out photo."""
    r = V.living_motion(RUN2 / f"{name}.mp4")
    assert r["status"] == "PASS", r
    assert r["value"] >= V.ZONE_COVER_MIN, r


@pytest.mark.parametrize("name,zone", [("X1_S07_SH006", "fire"), ("X1_S07_SH008", "fire"), ("X1_S07_SH006", "smoke"), ("X1_S07_SH008", "smoke"),
                                       ("X1_S04_SH008", "smoke")])
def test_x1_fire_and_smoke_zones_move_once_the_sidecar_in_zones_is_found(name, zone):
    """Run1 X1 has its sidecars in run1/zones/ (not beside the clip): the search finds them; flames flicker in place and smoke drifts slowly."""
    p = RUN1 / f"{name}.mp4"
    series = V._motion_series(p, V.decode_grey(p), V._cv2())
    assert float(np.median(series.cover[zone])) >= V.ZONE_COVER_MIN, {k: float(np.median(v)) for k, v in series.cover.items()}


@pytest.mark.parametrize("name", ["X1_S04_SH008", "X1_S07_SH006", "X1_S07_SH008"])
def test_x1_never_fails_because_of_its_fire_and_never_for_a_camera_move(name):
    """X1 still FAILs (run1 declares no particle layer although snow falls over it, and the S07_SH008 sky barely moves: client items 1, 2, 8), but never
    for the old reasons: not the fire's 5 px/s, not 'a camera move or a few particles', and the zone sidecar is found."""
    r = V.living_motion(RUN1 / f"{name}.mp4")
    assert r["status"] == "FAIL", r
    assert "fire zone" not in r["detail"] and "camera move or a few particles" not in r["detail"], r
    assert "no zone sidecar found" not in r["detail"], r


@pytest.mark.parametrize("name", ["X4_S04_SH008_camera_only", "X4_S04_SH008_production", "X4_S07_SH006_camera_only", "X4_S07_SH006_production",
                                  "X4_S07_SH008_camera_only", "X4_S07_SH008_production"])
def test_the_camera_only_controls_and_their_twins_still_fail(name):
    """A layered camera push over a dead picture (Z17: 17.4 % and 15.6 % before the fix on S04) is the camera, not life."""
    r = V.living_motion(RUN1 / f"{name}.mp4")
    assert r["status"] == "FAIL", r


def test_a_clip_with_no_sidecar_says_so():
    r = V.living_motion(RUN1 / "X4_S04_SH008_camera_only.mp4")
    assert r["status"] == "FAIL" and "no zone sidecar found" in r["detail"] and "whole frame judged" in r["detail"], r
