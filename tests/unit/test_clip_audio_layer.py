"""FA-13 (Fable audit 2026-11-13, P6): the narrated LTX clips' own sound is a ``clip_audio`` layer of the effects stem, off
until the creator's switch Q2 says on; the voice track stays voice only, and every read piece split for a clip and every clip
edge gets BP-188's de-click fade."""
from __future__ import annotations

import numpy as np

from explainer_engine.audio import stems as STEMS
from explainer_engine.core import open_questions as OQ
from explainer_engine.videolane import voice as VV

RATE = 48000


def _wav(path, seconds, level=0.5):
    x = np.full(int(RATE * seconds), level, np.float32)
    return VV.write_mono(path, x)


def _plan():
    return {"shots": [{"shot_id": "V1", "start_s": 1.0, "dur_s": 2.0}]}


def test_the_layer_is_on_since_the_creators_ab_and_off_when_switched_off(tmp_path, monkeypatch):
    """Q2: the creator chose version b of the A/B on 2026-11-13 13:55 UTC (D-138), so the switch is on; switched off, the
    layer lays nothing."""
    assert OQ.value("Q2") == "on"
    monkeypatch.setattr(OQ, "value", lambda qid, path=OQ.PATH: "off" if qid == "Q2" else "x")
    layer, laid, state = STEMS.clip_audio_layer(_plan(), {"V1": str(_wav(tmp_path / "c.wav", 2.0))}, RATE * 4)
    assert not laid and state.startswith("off") and float(np.abs(layer).max()) == 0.0


def test_switched_on_it_lays_the_clip_down_with_seam_fades(tmp_path, monkeypatch):
    monkeypatch.setattr(OQ, "value", lambda qid, path=OQ.PATH: "on" if qid == "Q2" else "x")
    layer, laid, state = STEMS.clip_audio_layer(_plan(), {"V1": str(_wav(tmp_path / "c.wav", 3.0))}, RATE * 4)
    assert state.startswith("on") and laid == [{"shot_id": "V1", "at_s": 1.0, "seconds": 2.0, "gain_db": STEMS.CLIP_AUDIO_DB}]
    mono = layer.mean(axis=1)
    assert float(np.abs(mono[: RATE - 1]).max()) == 0.0                     # nothing before the shot
    assert abs(mono[RATE]) < 1e-3 and abs(mono[RATE + int(RATE * 2.0) - 1]) < 1e-2   # faded in and out (BP-188)
    mid = float(np.abs(mono[RATE + RATE // 2]))
    assert 0.0 < mid < 0.5 * 10 ** (STEMS.CLIP_AUDIO_DB / 20) * 1.01        # CLIP_AUDIO_DB down from the clip


def test_the_read_pieces_split_for_a_clip_fade_at_the_split(tmp_path):
    read = _wav(tmp_path / "read.wav", 4.0, level=0.4)
    clip = _wav(tmp_path / "clip.wav", 1.0, level=0.0)
    timing = {"fps": 24, "total_frames": 24 * 5, "inserts": [{"shot_id": "C1", "at_read_frame": 48, "frames": 24}],
              "shots": {"C1": {"start_frame": 48}}}
    rep = VV.compose(timing, read, {"C1": {"path": str(clip), "speech": []}}, tmp_path / "v.wav")
    y = VV.read_mono(tmp_path / "v.wav")
    split = 2 * RATE                       # the read stops at 2.0 s and resumes after the 1 s clip, at 3.0 s
    assert abs(y[split - 1]) < 0.02 and abs(y[3 * RATE]) < 0.02            # both sides of the split fade (BP-188)
    assert abs(y[RATE]) > 0.3 and abs(y[int(3.5 * RATE)]) > 0.3            # the read itself is untouched
    assert [p["what"] for p in rep["laid"]] == ["read", "read", "clip"]


def test_the_q2_ab_renders_both_versions_by_the_one_renderer(tmp_path):
    """Q2 (the creator 2026-11-13, answer c; D-138): the free A/B makes one narrated clip twice through ``stems.render``:
    a) the clip's sound dropped (the effects stem silent), b) the clip's sound as the quiet ducked layer; the same cue rows;
    the switch itself is restored afterwards (on since his choice, D-138)."""
    import json
    import subprocess
    from explainer_engine.audio import clip_audio_ab as AB
    from explainer_engine.episode import sound_plan as SP
    from tests.unit.test_sound_design_system import _lib
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=24:duration=3", "-f",
                    "lavfi", "-i", "sine=frequency=300:duration=3", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(clip)], check=True)
    read = _wav(tmp_path / "read.wav", 2.0, level=0.3)
    plan = SP.build(AB.one_shot_script(3.0, ["battle_din"], "plain", "bronze_age", "x"), fps=24, era="bronze_age")
    lib = _lib(tmp_path / "lib", {c: [("loop", 4.0, None)] for c in plan["classes"]})
    rep = AB.build(clip, read, tmp_path / "ab", lib, bed=["battle_din"], seconds=3.0)
    a, b = rep["versions"]["a_stripped"], rep["versions"]["b_clip_layer"]
    assert a["clip_audio"]["laid"] == [] and b["clip_audio"]["laid"][0]["gain_db"] == STEMS.CLIP_AUDIO_DB
    sa = VV.read_mono(tmp_path / "ab" / "a_stripped" / "stems" / "sfx.wav")
    sb = VV.read_mono(tmp_path / "ab" / "b_clip_layer" / "stems" / "sfx.wav")
    assert float(np.abs(sa).max()) == 0.0 and float(np.abs(sb).max()) > 0.0
    rows = lambda v: [(r["layer"], r.get("asset_id")) for r in json.loads(
        (tmp_path / "ab" / v / "stems" / "cue_sheet.json").read_text())["rows"]]
    assert rows("a_stripped") == rows("b_clip_layer")
    assert OQ.value("Q2") == "on" and (tmp_path / "ab" / "b_clip_layer.mp4").is_file()   # the switch is restored
