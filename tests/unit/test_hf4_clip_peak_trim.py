"""HF-4 (Truce 1914 assembly, FL-401, FL-111, TD-304): a clip over BP-50's true-peak ceiling is trimmed in its cut and
recorded, never dropped; the raw file is not touched and CLIP-06 is judged on the trimmed cut."""
from __future__ import annotations

import hashlib

import numpy as np

from explainer_engine.qa import gates as G
from explainer_engine.qa import targets as T
from tests.unit import test_videolane_media as M

FPS = M.FPS


def _hot(seconds: float, peak: float) -> np.ndarray:
    x = M.speechy(seconds, [(1.0, 3.0)], level=0.25)
    return (x / np.abs(x).max() * peak).astype(np.float32)


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _one(tmp_path, peak):
    from explainer_engine.videolane import ingest as IN
    raw = M.write_clip(tmp_path / "A.mp4", M.moving(120, 1.0), audio=_hot(5.0, peak))
    sha = _sha(raw)
    rec = IN.ingest_scene(tmp_path / "ep", M.scene_script(), [{"shot_id": "A", "path": str(raw)}], FPS)[0]
    return rec, raw, sha


def test_a_clip_at_minus_0_3_dbtp_is_trimmed_two_db_and_is_not_a_fail(tmp_path):
    rec, raw, sha = _one(tmp_path, 0.966)                                   # -0.3 dBFS
    ceiling = T.PROFILES["long"]["true_peak_max"]
    assert rec["true_peak_before"] > ceiling and rec["level_trim_db"] >= 2.0
    assert rec["status"] != G.FAIL and not [f for f in rec["findings"] if f["rule"] == "CLIP-06"]
    assert _sha(tmp_path / "ep" / rec["raw_path"]) == sha == rec["raw_sha256"]      # the raw evidence is the model's file
    assert _sha(raw) == sha
    after = T.measure_file(tmp_path / "ep" / rec["clip_path"])["true_peak"]
    assert after <= ceiling and abs((rec["true_peak_before"] - after) - rec["level_trim_db"]) < 1.0


def test_a_clip_under_the_ceiling_gets_no_trim(tmp_path):
    rec, _raw, _sha0 = _one(tmp_path, 0.5)                                  # about -6 dBFS
    assert "level_trim_db" not in rec and "true_peak_before" not in rec


def test_a_recut_keeps_the_trim(tmp_path):
    from explainer_engine.videolane import ingest as IN
    rec, _raw, _s = _one(tmp_path, 0.966)
    longer = IN.recut(tmp_path / "ep", rec, rec["frames"] + 12, FPS)
    assert longer["level_trim_db"] == rec["level_trim_db"]
    assert T.measure_file(tmp_path / "ep" / longer["clip_path"])["true_peak"] <= T.PROFILES["long"]["true_peak_max"]
