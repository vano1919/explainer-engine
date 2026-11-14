"""Focused unit tests for Plan Steps 1 & 2 (T1-T5):
- T1: stage_sound raises ContractError when an LTX dialogue insert clip record is missing in a real run, and in a
  rehearsal builds the voice track with exact-length silence plus a REVIEW row naming the missing shot ids.
- T2: directed25d._rest_background removes the morphological bite and REST_ALPHA_GAIN dilation; objects with
  thin_share >= THIN_SHARE_MAX (0.35) stay on the background, while a person mask with a thin rifle stays whole with a
  soft inward feather and frame 0 equals the source picture inside the outline (rest_seam <= 0.04).
- T3: directed25d flattens bg_depth to the box median (with a soft edge) inside unlayered person/face/crowd boxes on the
  background sheet so bg_maps moves them rigidly without stretching.
- T4: living_director.choose_camera uses max(RATE_MIN, PRE_ACCENT_RATE) >= 0.018 (BP-21 pre_accent_rate_min_per_s) for
  the pre-word base move when a shot has a trigger word.
- T5: motion_intent.sliding_liveliness flags a 2 s clip frozen for 1.2 s in the middle as REVIEW (< 1.5 % changed pixels
  at 480x270 over a 1.0 s window), and blown_out_row FAILs above 0.015 (e.g. a 3 % burned sky).
"""
from __future__ import annotations

import importlib
import json
import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN
from explainer_engine.production import directed25d as R
from explainer_engine.production import living_director as LD
from explainer_engine.qa import gates as G
from explainer_engine.qa import motion_intent as MI
from explainer_engine.standards import sourced_rules as SR

cv2 = pytest.importorskip("cv2")


# ---------------------------------------------------------------------------
# T1: stage_sound missing LTX dialogue insert clip records
# ---------------------------------------------------------------------------

def _write_pcm_wav(path: Path, seconds: float, rate: int = 48000, amp: float = 0.15) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(seconds * rate))
    t = np.arange(n, dtype=np.float32) / rate
    samples = (amp * np.sin(2.0 * np.pi * 220.0 * t) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return path


def _setup_t1_episode(tmp_path: Path, monkeypatch) -> tuple[Path, dict]:
    root = tmp_path / "ep_t1"
    (root / "story").mkdir(parents=True)
    (root / "audio" / "stems").mkdir(parents=True)
    (root / "production").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    lib = tmp_path / "sound_lib"
    lib.mkdir(parents=True)
    (lib / "manifest.json").write_text("{}", encoding="utf-8")

    (root / "episode.json").write_text(json.dumps({
        "episode_id": "ep_t1",
        "fps": 24,
        "render_size": [320, 180],
        "historical_period": {"era_id": "ww1_1914"},
    }), encoding="utf-8")

    script = {
        "episode_id": "ep_t1",
        "fps": 24,
        "segments": [{"segment_id": "S05"}],
        "audio_lines": [
            {"line_id": "S05_L001", "speaker_type": "narrator", "text": "Wait here."},
            {"line_id": "S05_L002", "speaker_type": "character", "speaker_id": "thomas", "text": "Where did you learn English?"},
        ],
        "shots": [
            {"shot_id": "S05_SH003", "segment_id": "S05", "route": "still_25d", "target_duration_seconds": 1.0,
             "audio_line_ids": ["S05_L001"]},
            {"shot_id": "S05_SH004", "segment_id": "S05", "route": "video", "target_duration_seconds": 1.5,
             "audio_line_ids": ["S05_L002"]},
        ],
    }
    (root / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
    (root / "production" / "shot_records.json").write_text(json.dumps({
        "episode_id": "ep_t1", "fps": 24, "size": [320, 180],
        "shots": [
            {"shot_id": "S05_SH003", "route": "still_25d", "total_frames": 24},
            {"shot_id": "S05_SH004", "route": "video", "total_frames": 36, "fallback_for_wan": True},
        ],
    }), encoding="utf-8")

    timing = {
        "fps": 24,
        "total_frames": 60,
        "clip_timed": ["S05_SH004"],
        "shots": {
            "S05_SH003": {"start_frame": 0, "frames": 24},
            "S05_SH004": {"start_frame": 24, "frames": 36},
        },
        "spines": {"S05_SH003": [{"word": "wait", "start_frame": 0}], "S05_SH004": []},
        "inserts": [{"shot_id": "S05_SH004", "start_frame": 24, "frames": 36, "duration_s": 1.5}],
    }
    (root / "audio" / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
    _write_pcm_wav(root / "audio" / "narration.wav", 1.0, rate=48000)
    polished_wav = _write_pcm_wav(root / "audio" / "narration_polished.wav", 1.0, rate=48000)

    monkeypatch.setattr(RUN.TM, "load", lambda r: timing, raising=False)
    monkeypatch.setattr(RUN.TM, "timed_script", lambda sc, tm: sc, raising=False)
    monkeypatch.setattr(RUN.TM, "spines_of", lambda tm: tm["spines"], raising=False)
    monkeypatch.setattr(RUN, "_polish_read", lambda ep: (polished_wav, {"chain": "test", "seconds_before": 1.0, "seconds_after": 1.0}))
    monkeypatch.setattr(RUN, "_deliver_mix", lambda raw, deliv, rehearsal=False: (
        [G.row("delivered_mix_loudness", True, "ok", -14.0), G.row("delivered_mix_true_peak", True, "ok", -1.5)],
        {"lufs": -14.0, "true_peak": -1.5}, {"lufs": -14.0, "true_peak": -1.5}
    ))

    captured: dict = {}

    sp_mod = types.ModuleType("explainer_engine.episode.sound_plan")
    sp_mod.build = lambda *a, **k: {"shots": [], "classes": [], "beds": [], "blocked_era_events": [], "av": {"decisions": {}, "review_required": [], "candidates": 0}}
    sp_mod.resolve = lambda *a, **k: {}
    sp_mod.write = lambda *a, **k: root / "audio" / "sound_plan.json"

    stems_mod = types.ModuleType("explainer_engine.audio.stems")
    def _fake_render(plan, sources, stems_dir, library_root=None, narration=None, shippable=True, clip_audio=None):
        captured["narration"] = Path(narration) if narration else None
        stems_dir.mkdir(parents=True, exist_ok=True)
        (stems_dir / "cue_sheet.json").write_text(json.dumps({"cues": []}), encoding="utf-8")
        _write_pcm_wav(stems_dir / "mix.wav", 2.5, rate=48000)
        _write_pcm_wav(root / RUN.DELIVERED_MIX_REL, 2.5, rate=48000)
        return {"shippable": shippable, "placeholders": [], "not_shippable_because": [], "levels": {"rows": []},
                "cue_rows": [], "narration_source": str(narration)}
    stems_mod.render = _fake_render

    pr_mod = types.ModuleType("explainer_engine.episode.production_runner")
    pr_mod.audit_rendered_audio_stems = lambda **k: {"mid_line_narration_dropouts": 0}

    vi_mod = types.ModuleType("explainer_engine.videolane.ingest")
    vi_mod.speech = lambda p: []

    vv_mod = types.ModuleType("explainer_engine.videolane.voice")
    def _fake_compose(tm, narr, clip_aud, out_wav, read_speech=None, pitch_shifts=None):
        captured["clip_audio"] = dict(clip_aud)
        with wave.open(str(narr), "rb") as w:
            sr = w.getframerate()
            pcm = w.readframes(w.getnframes())
        for ins in tm["inserts"]:
            cp = Path(clip_aud[ins["shot_id"]]["path"])
            with wave.open(str(cp), "rb") as w:
                assert w.getframerate() == sr
                pcm += w.readframes(w.getnframes())
        with wave.open(str(out_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm)
        return {"voice_track": str(out_wav), "inserts": list(clip_aud)}
    vv_mod.compose = _fake_compose

    vp_mod = types.ModuleType("explainer_engine.videolane.plan")
    vp_mod.clip_spoken = lambda sc: {"S05_SH004"}
    vp_mod.is_video = lambda s: s.get("route") == "video"

    mc_mod = types.ModuleType("explainer_engine.audio.mix_check")
    mc_mod.check = lambda *a, **k: {"rows": []}

    avr_mod = types.ModuleType("explainer_engine.episode.av_report")
    avr_mod.event_report = lambda *a, **k: {}

    ev_mod = types.ModuleType("explainer_engine.episode.events")
    ev_mod.events_report = lambda *a, **k: {"shots": {}}

    for name, mod in (
        ("explainer_engine.episode.sound_plan", sp_mod),
        ("explainer_engine.audio.stems", stems_mod),
        ("explainer_engine.episode.production_runner", pr_mod),
        ("explainer_engine.videolane.ingest", vi_mod),
        ("explainer_engine.videolane.voice", vv_mod),
        ("explainer_engine.videolane.plan", vp_mod),
        ("explainer_engine.audio.mix_check", mc_mod),
        ("explainer_engine.episode.av_report", avr_mod),
        ("explainer_engine.episode.events", ev_mod),
    ):
        pkg_name, attr = name.rsplit(".", 1)
        if pkg_name not in sys.modules:
            try:
                importlib.import_module(pkg_name)
            except ImportError:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = []
                sys.modules[pkg_name] = pkg
                parent_name, pkg_attr = pkg_name.rsplit(".", 1)
                setattr(importlib.import_module(parent_name), pkg_attr, pkg)
        pkg = sys.modules[pkg_name]
        monkeypatch.setattr(pkg, attr, mod, raising=False)
        old_sys = sys.modules.get(name)
        sys.modules[name] = mod
        if hasattr(monkeypatch, "_undo"):
            monkeypatch._undo.append(
                lambda n=name, o=old_sys: sys.modules.__setitem__(n, o) if o is not None else sys.modules.pop(n, None)
            )

    return root, captured


def test_t1_stage_sound_missing_insert_raises_contract_error(tmp_path, monkeypatch):
    root, _ = _setup_t1_episode(tmp_path, monkeypatch)
    ep_real = RUN.Episode(root, sound_library=tmp_path / "sound_lib", rehearsal=False)
    with pytest.raises(ContractError, match="S05_SH004"):
        RUN.stage_sound(ep_real, rehearsal=False)


def test_t1_stage_sound_rehearsal_missing_insert_builds_exact_silence_and_review_row(tmp_path, monkeypatch):
    root, captured = _setup_t1_episode(tmp_path, monkeypatch)
    ep_reh = RUN.Episode(root, sound_library=tmp_path / "sound_lib", rehearsal=True)
    rows, outputs = RUN.stage_sound(ep_reh, rehearsal=True)

    # Never fell back to the unsplit 1.0 s narration_polished.wav
    assert captured["narration"] == root / "audio" / "voice_track.wav"
    assert outputs["voice_track"] == "audio/voice_track.json"

    # Missing insert S05_SH004 was replaced by exact-length silence (1.5 s = 72,000 samples at 48 kHz)
    sil_info = captured["clip_audio"]["S05_SH004"]
    sil_path = Path(sil_info["path"])
    assert sil_path.is_file()
    with wave.open(str(sil_path), "rb") as w:
        assert w.getnframes() == int(round(1.5 * 48000))
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        assert np.all(samples == 0)

    # Combined voice track is 1.0 s read + 1.5 s silence = 2.5 s
    with wave.open(str(root / "audio" / "voice_track.wav"), "rb") as w:
        assert w.getnframes() == int(round(2.5 * 48000))

    # REVIEW row names the missing insert shot id
    review_rows = [r for r in rows if r["status"] == G.REVIEW and "S05_SH004" in (r.get("detail") or "")]
    assert len(review_rows) == 1
    assert "S05_SH004" in (review_rows[0].get("measured") or [])


# ---------------------------------------------------------------------------
# T2: _rest_background — no morphological bite, thin_share >= 0.35 on BG,
#     person with thin rifle has frame 0 identical to source inside outline
# ---------------------------------------------------------------------------

def test_t2_person_with_thin_rifle_has_frame0_identical_to_source_and_wire_not_layered(tmp_path):
    h, w = 270, 480
    rng = np.random.default_rng(11)
    src = rng.integers(30, 90, (h, w, 3), dtype=np.uint8)
    depth = np.repeat(np.linspace(0.1, 0.85, h, dtype=np.float32)[:, None], w, axis=1)

    # Person mask with a thin 2 px rifle protruding from the shoulder (thin_share < 0.35)
    person = np.zeros((h, w), np.uint8)
    cv2.ellipse(person, (150, 170), (45, 75), 0, 0, 360, 1, -1)
    cv2.line(person, (185, 130), (310, 75), 1, 2)               # thin rifle barrel
    src[person > 0] = (40, 55, 70)
    depth[person > 0] = 0.88

    # Mostly-wire object (thin_share ~ 0.42 >= 0.35, but < old FLAT_SHARE 0.50 -> stays on background)
    wire = np.zeros((h, w), np.uint8)
    cv2.circle(wire, (70, 50), 12, 1, -1)                        # small post knot
    cv2.line(wire, (20, 40), (220, 55), 1, 2)
    cv2.line(wire, (20, 55), (220, 40), 1, 2)
    depth[wire > 0] = 0.65

    p = tmp_path / "pic.png"
    Image.fromarray(src).save(p)

    # High-contrast LaMa plate so any bleed-through inside the outline would show immediately
    hole = cv2.dilate(person, np.ones((15, 15), np.uint8)).astype(np.float32)
    plate = src.copy()
    plate[hole > 0] = (230, 235, 240)

    lay = {
        "manifest": {"lights": [], "masks": {"objects": [{"id": "person", "layer": True}, {"id": "wire", "layer": True}]}},
        "depth": depth,
        "plate": plate,
        "hole": hole,
        "masks": {"person": person.astype(np.float32), "wire": wire.astype(np.float32)},
        "lights": {},
    }
    plan = {"shot_id": "T2", "frames": 24, "cameras": [], "handheld": None, "rack": None, "effects": [], "far_share": 0.2}
    st = R.Stage(p, lay, plan, size=(w, h))

    # Frame 0 equals the source picture inside the person+rifle outline, and wire is not layered
    f0 = st.render(0)
    outline_mask = person > 0
    assert np.array_equal(f0[outline_mask], src[outline_mask])
    assert "wire" in st.flat and [o["id"] for o in st.objects] == ["person"]
    assert R.THIN_SHARE_MAX == pytest.approx(0.35)

    obj = st.objects[0]
    assert 0.0 < obj["thin_share"] < R.THIN_SHARE_MAX
    assert obj["alpha"][102, 248] > 0.8                          # rifle barrel kept whole (not bitten out)
    edge = (person > 0) & (cv2.erode(person, np.ones((3, 3), np.uint8)) == 0)
    assert float(obj["alpha"][edge].mean()) < 0.95               # soft inward feather on the body outline
    assert float(obj["alpha"][170, 150]) == pytest.approx(1.0)

    seam = st.rest_seam()
    assert seam["per_outline_px"] <= 0.04 and MI.rest_seam_row(seam)["status"] == G.PASS


# ---------------------------------------------------------------------------
# T3: Crowd / unlayered person box on a depth ramp moves rigidly in bg_maps
# ---------------------------------------------------------------------------

def test_t3_crowd_box_on_depth_ramp_moves_rigidly_without_stretch(tmp_path):
    h, w = 270, 480
    rng = np.random.default_rng(19)
    img = rng.integers(50, 200, (h, w, 3), dtype=np.uint8)
    p = tmp_path / "crowd.png"
    Image.fromarray(img).save(p)

    # Steep 2D depth ramp across the whole image (both x and y vary)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    depth = np.clip(0.05 + 0.55 * (yy / h) + 0.35 * (xx / w), 0.0, 1.0)

    crowd_mask = np.zeros((h, w), np.float32)
    crowd_mask[80:190, 140:340] = 1.0
    lay = {
        "manifest": {"lights": [], "masks": {"objects": [{"id": "crowd", "layer": False}]}},
        "depth": depth,
        "plate": img.copy(),
        "hole": None,
        "masks": {"crowd": crowd_mask},
        "lights": {},
    }
    cams = [{"op": "truck", "direction": "right", "strength": 2.0, "from": 0, "to": 24, "easing": "linear"}]
    plan = {"shot_id": "T3", "frames": 24, "cameras": cams, "handheld": None, "rack": None, "effects": [], "far_share": 0.2}
    st = R.Stage(p, lay, plan, size=(w, h))

    # Inside the crowd box [140:340, 80:190], bg_depth is flattened to the median
    iy0, iy1 = int(80 * st.sh / h), int(190 * st.sh / h)
    ix0, ix1 = int(140 * st.sw / w), int(340 * st.sw / w)
    box_depth = st.bg_depth[iy0:iy1, ix0:ix1]
    assert float(np.ptp(box_depth)) < 1e-5

    # Every pixel in the crowd box translates by the exact same (dx, dy) with zero stretch or shear
    mx0, my0, _ = st.bg_maps(st.view(0))
    mx1, my1, _ = st.bg_maps(st.view(23))
    dx = (mx1 - mx0)[85:185, 145:335]
    dy = (my1 - my0)[85:185, 145:335]
    assert float(np.abs(dx).mean()) > 1.0
    assert float(np.ptp(dx)) < 1e-3 and float(np.ptp(dy)) < 1e-3


# ---------------------------------------------------------------------------
# T4: choose_camera pre-accent rate floor >= 0.018 from BP-21
# ---------------------------------------------------------------------------

def test_t4_shot_with_trigger_word_gets_pre_accent_rate_at_least_0018():
    d = {
        "intent": "intended",
        "people_mid_or_close": True,
        "seen": {
            "objects": [{"id": "thomas", "points": [[0.35, 0.5]], "names": ["thomas"]}],
            "living": [],
        },
    }
    spine = [{"word": "wait", "start_frame": 4}, {"word": "thomas", "start_frame": 48}]
    tracks, why = LD.choose_camera(d, spine, frames=96, fps=24.0, faces=[], chosen_effects=set())

    base_move = tracks[0]
    base_s = 48 / 24.0
    measured_rate = float(base_move["params"]["strength"]) * LD.PUSH_SCALE / base_s
    assert measured_rate >= 0.018 - 1e-6
    assert "1.8 %/s" in why[0]
    assert float(SR.T("BP-21", "pre_accent_rate_min_per_s")) == pytest.approx(0.018)
    assert LD.PRE_ACCENT_RATE >= 0.018


# ---------------------------------------------------------------------------
# T5: sliding_liveliness (1.0 s window, REVIEW < 1.5 %) & blown_out FAIL > 1.5 %
# ---------------------------------------------------------------------------

def test_t5_sliding_liveliness_reviews_2s_clip_frozen_12s_in_middle():
    rng = np.random.default_rng(42)
    base = rng.integers(40, 180, (270, 480, 3), dtype=np.uint8)

    # 2.0 s clip at 24 fps (48 frames) frozen for 1.2 s in the middle (frames 9..38 identical)
    frozen_clip = []
    cur = base.copy().astype(np.int16)
    for f in range(48):
        if f < 9 or f > 38:
            cur = np.clip(cur + 6, 0, 255)
        frozen_clip.append(cur.astype(np.uint8).copy())

    res = MI.sliding_liveliness(frozen_clip, fps=24.0)
    assert res["gate"] == "sliding_liveliness"
    assert res["status"] == G.REVIEW
    assert res["worst_share"] < 0.015
    assert MI.sliding_liveliness_row(res)["status"] == G.REVIEW

    # Continuously moving 2.0 s clip passes sliding_liveliness
    live_clip = [np.clip(base.astype(np.int16) + ((f * 3) % 60), 0, 255).astype(np.uint8) for f in range(48)]
    res_ok = MI.sliding_liveliness(live_clip, fps=24.0)
    assert res_ok["status"] == G.PASS and res_ok["worst_share"] >= 0.015


def test_t5_blown_out_fails_at_3_pct_burned_sky():
    # Burned sky of 3 % newly blown -> FAIL (threshold 0.015)
    burned_3pct = MI.blown_out_row({"source": 0.002, "worst": 0.032, "frame": 15})
    assert burned_3pct["gate"] == "blown_out" and burned_3pct["status"] == G.FAIL

    # Untouched / 0.4 % newly blown -> PASS
    clean_sky = MI.blown_out_row({"source": 0.002, "worst": 0.006, "frame": 15})
    assert clean_sky["status"] == G.PASS
