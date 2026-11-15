"""Comprehensive regression guards for Task 1 logic fixes (including Round 1 C1-C6 verification fixes):
- Part A: 24 OPEN code items + 2 FIXED-NO-GUARD + 3 PARTIAL-GUARD from INCIDENT_AUDIT_2026-11-15.md
- Part A2: 5 must-fix logic gaps from outside review (chatgpt_review.md)
- Part B: 8 additional pipeline logic defects discovered across script -> director -> LTX -> 2.5D -> maps -> audio -> assemble -> QA
- Round 1 (C1-C4): Evidence-only Scene Director (no invented mist/dust/sky on interior brazier shots), wired stage_direction,
  general physical-noun preflight check with entering prop_change support, and behavioural assertions via existing entry points.

Every test here is CPU-only ($0, synthetic numpy/PIL/JSON), fails on 4d209a8 (and on pre-Round-1 for C1-C4), and passes now.
"""
from __future__ import annotations

import ast
import copy
import json
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine import docs_lint
from explainer_engine.audio import scribe_words as SW, sound_director as SD, stems as STEMS
from explainer_engine.episode import (
    acceptance as ACC,
    context as CTX,
    events as EV,
    production_runner as PR,
    router as ROUTER,
    run as RUN,
    shot_split as SS,
    sound_plan as SP,
    timing as TM,
)
from explainer_engine.finish import frame_pick as FP, superres as SR_MOD
from explainer_engine.maps import actions as MA
from explainer_engine.production import (
    continuity as CONT,
    directed25d as D25,
    direction as DIR,
    layers25d as L25,
    living_director as LD,
    map_clip as MC,
    paid_preflight as PF,
    understand as U,
)
from explainer_engine.qa import gates as G, sound_realism as RL
from explainer_engine.standards import sourced_rules as SR
from explainer_engine.training.pods.ltx import modal_ltx_jobs as LJ
from explainer_engine.videolane import plan as VP

ROOT = Path(__file__).resolve().parents[2]
FPS = 24


def _write_minimal_episode(tmp_path: Path, script_overrides: dict, manifest_overrides: dict | None = None) -> Path:
    """Create a minimal episode folder in tmp_path so RUN.stage_script can be exercised as a public entry point."""
    ep_root = tmp_path / "ep_check"
    (ep_root / "story").mkdir(parents=True, exist_ok=True)
    (ep_root / "production").mkdir(parents=True, exist_ok=True)
    base_script = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    base_script = copy.deepcopy(base_script)
    base_script["episode_id"] = "ep_check"
    base_script.update(script_overrides)
    (ep_root / "story" / "production_script.json").write_text(json.dumps(base_script), encoding="utf-8")
    man = {
        "schema": "episode_manifest/1",
        "episode_id": "ep_check",
        "title": "Check Episode",
        "fps": 24,
        "render_size": [192, 108],
        "run_scope": "full",
        "historical_period": {"era_id": "ww1_1914", "label": "December 1914"},
    }
    if manifest_overrides:
        man.update(manifest_overrides)
    (ep_root / "episode.json").write_text(json.dumps(man), encoding="utf-8")
    return ep_root


# --- Audit #1: VL-15 prop-state continuity across shot pairs ---------------------------------------------------------------

def test_pair_gate_flags_held_to_released_prop():
    """Audit #1: shot A ends with a prop held in hand while shot B starts with the same prop leaning/on ground/attached."""
    shots = [
        {
            "shot_id": "S07_SH007",
            "segment_id": "S07",
            "location_id": "loc_no_mans_land",
            "character_ids": ["char_thomas"],
            "action_end_state": "Thomas holds his rifle in his right hand at his side.",
        },
        {
            "shot_id": "S07_SH008",
            "segment_id": "S07",
            "location_id": "loc_no_mans_land",
            "character_ids": ["char_thomas"],
            "action_start_state": "Thomas stands unarmed while his rifle leans against the parapet wall.",
        },
    ]
    res = CONT.findings(shots)
    prop_fails = [f for f in res if f.get("rule") == "VL-15 PROP-STATE" and f.get("severity") == "FAIL"]
    assert len(prop_fails) == 1
    assert prop_fails[0]["prop"] == "rifle"
    assert prop_fails[0]["where"] == "S07_SH007->S07_SH008"

    shots[1]["action_start_state"] = "Thomas still holds his rifle in his right hand."
    assert [f for f in CONT.findings(shots) if f.get("rule") == "VL-15 PROP-STATE"] == []


# --- Audit #2 & C3: VL-17 LTX preflight refuses unlisted physical nouns & negations, allows entering prop_change ----------

def test_preflight_refuses_prompt_object_absent_from_start_picture():
    """Audit #2 & C3: paid_preflight.ltx refuses a prompt naming a physical object (both known like 'flag' and unlisted like
    'kettle', 'sandbag', 'periscope') absent from seen, allows props declared in prop_change / held_props, and refuses
    negative phrasing ('does not ...') in a positive motion prompt."""
    doc = {
        "names": ["Thomas", "Kurt"],
        "jobs": [
            {
                "id": "S07_SH005",
                "prompt": "A bearded soldier in a grey coat raises a white flag above the trench.",
                "frames": 97,
                "fps": 24,
                "seen": {"what": "bearded soldier in grey coat standing in muddy trench", "objects": [{"id": "soldier", "names": ["soldier"]}]},
            },
            {
                "id": "S07_SH006",
                "prompt": "The soldier lifts a copper kettle beside the sandbag and looks through a periscope.",
                "frames": 97,
                "fps": 24,
                "seen": {"what": "soldier standing in muddy trench", "objects": [{"id": "soldier", "names": ["soldier"]}]},
            },
            {
                "id": "S07_SH007",
                "prompt": "The soldier takes a copper kettle and a brass tin handed to him.",
                "frames": 97,
                "fps": 24,
                "seen": {"what": "soldier standing in muddy trench", "objects": [{"id": "soldier", "names": ["soldier"]}]},
                "prop_change": "a comrade hands a copper kettle into the frame",
                "held_props": ["tin"],
            },
            {
                "id": "S07_SH008",
                "prompt": "A young soldier in a wool coat does not fire his rifle and stands still.",
                "frames": 97,
                "fps": 24,
                "seen": {"what": "young soldier holding rifle in wool coat", "objects": [{"id": "rifle", "names": ["rifle"]}]},
            },
        ],
    }
    bad = PF.ltx(doc)
    assert any("VL-17" in b and "S07_SH005" in b and "flag" in b for b in bad)
    assert any("VL-17" in b and "S07_SH006" in b and "kettle" in b and "sandbag" in b and "periscope" in b for b in bad)
    assert not any("VL-17" in b and "S07_SH007" in b for b in bad), f"Declared entering prop_change/held_props should pass VL-17, got: {bad}"
    assert any("VL-17" in b and "S07_SH008" in b and "does not" in b.lower() for b in bad)


# --- Audit #3 & C4: script_deviation record checked via RUN.stage_script and videolane.plan -------------------------------

def test_deviation_recorded_for_accepted_clip(tmp_path):
    """Audit #3 & C4: when an accepted clip record in production/video/<shot_id>.json diverges from the frozen script's
    motion prompt, RUN.stage_script emits a FAIL gate row unless script_deviation is recorded."""
    ep_root = _write_minimal_episode(tmp_path, {})
    vid_dir = ep_root / "production" / "video"
    vid_dir.mkdir(parents=True, exist_ok=True)
    (vid_dir / "S01_SH002.json").write_text(
        json.dumps({"status": "PASS", "route": "video", "prompt": "Soldier waves both empty hands above the parapet."}),
        encoding="utf-8",
    )
    ep = RUN.Episode(ep_root, rehearsal=True)
    rows_bad, _ = RUN.stage_script(ep, rehearsal=True)
    dev_row = next((r for r in rows_bad if r["gate"] == "script_deviation_recorded"), None)
    assert dev_row is not None and dev_row["status"] == G.FAIL and "S01_SH002" in dev_row["measured"]

    (vid_dir / "S01_SH002.json").write_text(
        json.dumps({
            "status": "PASS",
            "route": "video",
            "prompt": "Soldier waves both empty hands above the parapet.",
            "script_deviation": {
                "script_says": "original script motion",
                "clip_does": "waves both empty hands",
                "reason": "start photo has no cloth in frame (VL-17)",
            },
        }),
        encoding="utf-8",
    )
    rows_ok, _ = RUN.stage_script(ep, rehearsal=True)
    dev_row_ok = next((r for r in rows_ok if r["gate"] == "script_deviation_recorded"), None)
    assert dev_row_ok is not None and dev_row_ok["status"] == G.PASS


# --- Audit #4 & A2.3 & C4: S07_SH005 route conflict & BP-109 60/30/10 mix gate via RUN.stage_script -----------------------

def test_shot_with_ltx_clip_record_is_video_route(tmp_path):
    """Audit #4, A2.3 & C4: Truce 1914 production_script.json has S07_SH005 on 'video' and passes RUN.stage_script's
    accepted_ltx_route_match and route_mix_60_30_10 gates; reverting S07_SH005 to still_25d causes RUN.stage_script to FAIL both."""
    truce_script = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    s07_sh005 = next(s for s in truce_script["shots"] if s["shot_id"] == "S07_SH005")
    assert s07_sh005["route"] == "video"

    ep_root = _write_minimal_episode(tmp_path, {})
    vid_dir = ep_root / "production" / "video"
    vid_dir.mkdir(parents=True, exist_ok=True)
    (vid_dir / "S07_SH005.json").write_text(
        json.dumps({"status": "PASS", "route": "video", "clip_path": "production/video/S07_SH005.mp4"}),
        encoding="utf-8",
    )
    ep_ok = RUN.Episode(ep_root, rehearsal=True)
    rows_ok, out_ok = RUN.stage_script(ep_ok, rehearsal=True)
    mix_row_ok = next((r for r in rows_ok if r["gate"] == "route_mix_60_30_10"), None)
    ltx_row_ok = next((r for r in rows_ok if r["gate"] == "accepted_ltx_route_match"), None)
    assert mix_row_ok is not None and mix_row_ok["status"] == G.PASS
    assert ltx_row_ok is not None and ltx_row_ok["status"] == G.PASS
    shares = out_ok["mix"]["shares"]
    assert 0.55 <= shares["video"] <= 0.65 and 0.25 <= shares["still_25d"] <= 0.35 and 0.05 <= shares["map_action"] <= 0.15

    # Reverting S07_SH005 to still_25d pushes still_25d to 35.29% (> 35% ceiling) and triggers accepted_ltx_route_match FAIL
    bad_shots = copy.deepcopy(truce_script["shots"])
    for s in bad_shots:
        if s["shot_id"] == "S07_SH005":
            s["route"] = "still_25d"
    ep_bad_root = _write_minimal_episode(tmp_path / "bad", {"shots": bad_shots})
    (ep_bad_root / "production" / "video").mkdir(parents=True, exist_ok=True)
    (ep_bad_root / "production" / "video" / "S07_SH005.json").write_text(
        json.dumps({"status": "PASS", "route": "video", "clip_path": "production/video/S07_SH005.mp4"}),
        encoding="utf-8",
    )
    rows_bad, _ = RUN.stage_script(RUN.Episode(ep_bad_root, rehearsal=True), rehearsal=True)
    mix_row_bad = next((r for r in rows_bad if r["gate"] == "route_mix_60_30_10"), None)
    ltx_row_bad = next((r for r in rows_bad if r["gate"] == "accepted_ltx_route_match"), None)
    assert mix_row_bad is not None and mix_row_bad["status"] == G.FAIL
    assert ltx_row_bad is not None and ltx_row_bad["status"] == G.FAIL


def test_mix_gate_rows_fails_when_outside_bp109_tolerance():
    """A2.3: router.mix_gate_rows emits a hard FAIL on a full episode when any lane drifts > 5 percentage points from 60/30/10."""
    skewed = {
        "shots": [
            {"shot_id": "S1", "route": "video", "target_duration_seconds": 45.0},
            {"shot_id": "S2", "route": "still_25d", "target_duration_seconds": 45.0},
            {"shot_id": "S3", "route": "map_action", "target_duration_seconds": 10.0},
        ]
    }
    rows = ROUTER.mix_gate_rows(skewed, scope="full")
    assert rows[0]["status"] == G.FAIL and rows[0]["gate"] == "route_mix_60_30_10"


# --- Audit #6 & C4: FL-112 silent-tail clip audio muting tested through STEMS.clip_audio_layer ----------------------------

def test_silent_tail_clip_is_muted(tmp_path):
    """Audit #6 & C4 (FL-112): STEMS.clip_audio_layer zeroes trailing windows with RMS < 0.02 in rendered clip audio, and
    scribe_words drops hallucinated words ('You', 'Thanks') in quiet tails."""
    sr = STEMS.SR  # 48000 Hz
    active = (0.18 * np.sin(np.linspace(0, 80 * np.pi, sr))).astype(np.float32)       # 1.0 s active sound (RMS ~ 0.127)
    tail_noise = (0.006 * np.sin(np.linspace(0, 40 * np.pi, sr))).astype(np.float32)  # 1.0 s quiet tail (RMS ~ 0.0042 < 0.02)
    wav_data = np.concatenate([active, tail_noise])
    pcm = np.clip(wav_data * 32767.0, -32768, 32767).astype("<i2")

    ep_root = tmp_path / "ep_audio"
    (ep_root / "production" / "video").mkdir(parents=True, exist_ok=True)
    clip_wav = ep_root / "production" / "video" / "S01_SH001.wav"
    with wave.open(str(clip_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    plan = {"shots": [{"shot_id": "S01_SH001", "start_s": 0.0, "dur_s": 2.0}]}
    layer, used, _ = STEMS.clip_audio_layer(plan, {"S01_SH001": clip_wav}, 2 * sr)
    assert len(used) == 1
    assert float(np.sqrt(np.mean(layer[: int(0.7 * sr)] ** 2))) > 0.005
    # The trailing second (where raw clip had RMS 0.0042 < 0.02) must be completely muted by clip_audio_layer
    assert float(np.max(np.abs(layer[int(1.25 * sr):]))) == 0.0

    words = [
        {"text": "halt", "start": 0.1, "end": 0.7},
        {"text": "You", "start": 1.2, "end": 1.5},
        {"text": "Thanks", "start": 1.6, "end": 1.9},
    ]
    kept = SW.filter_silent_tail_words(words, wav_data, sr=sr, rms_floor=0.02)
    assert [w["text"] for w in kept] == ["halt"]


# --- Audit #7b & C4: LTX worker handover_scores and frame_pick.pick default 1.5s window -----------------------------------

def test_worker_handover_uses_person_score(tmp_path):
    """Audit #7b & C4 (BP-199, VL-16): handover_scores weights face (0.6) and body (0.3) above whole-frame (0.1), and
    frame_pick.pick searches the last 1.5 s by default (catching a still frame at -1.4 s that a 1.0 s window misses)."""
    import cv2
    h, w = 120, 160
    rng = np.random.default_rng(11)
    base_bg = rng.uniform(40, 180, (h, w)).astype(np.float32)
    person_patch = rng.uniform(60, 220, (h, w)).astype(np.float32)

    f0 = base_bg.copy()
    f0[15:110, 35:125] = person_patch[15:110, 35:125]
    f1 = f0.copy()
    f2 = base_bg.copy()
    checker = ((np.indices((h, w)).sum(axis=0) % 2) * 250.0).astype(np.float32)
    f2[:15, :] = checker[:15, :]
    f2[15:110, 35:125] = 255.0 - person_patch[15:110, 35:125]

    scores = LJ.handover_scores([f0, f1, f2])
    best = max(scores, key=lambda s: s["score"])
    assert best["i"] in (0, 1) and scores[0]["score"] > scores[2]["score"]

    # Build a 60-frame (2.5 s at 24 fps) clip where frames 24..30 (-1.5s to -1.25s) are sharp and still, while frames 36..59
    # (the last 1.0s) are blurred and jittering. Calling FP.pick(clip) with default window_s must include frame 24..59 (1.5s).
    clip_path = tmp_path / "handover_test.mp4"
    sharp_bgr = np.dstack([f0, f0, f0]).astype(np.uint8)
    blur_bgr = cv2.GaussianBlur(sharp_bgr, (15, 15), 5.0)
    writer = cv2.VideoWriter(str(clip_path), cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (w, h))
    for idx in range(60):
        if 24 <= idx <= 30:
            writer.write(sharp_bgr)
        else:
            jitter = np.roll(blur_bgr, idx * 5, axis=1)
            writer.write(jitter)
    writer.release()

    rep = FP.pick(clip_path, model=None)
    assert rep["window"] == [24, 59], f"Expected 1.5s window [24, 59], got {rep['window']}"
    assert 24 <= rep["frame"] <= 30, f"Expected stillest sharp frame in 24..30, got {rep['frame']}"


# --- Audit #8 & C4: Face/headroom-aware crop in superres.crop_box and modal_ltx_jobs.fit_picture --------------------------

def test_crop_box_keeps_face_box_with_margin():
    """Audit #8 & C4: superres.crop_box preserves top face/hat pixels when a centred crop would slice them off, and
    modal_ltx_jobs.fit_picture preserves top headroom."""
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    arr[12:24, 80:120, :] = 250  # bright hat/head top at y=0.06..0.12 (outside centred [0.13, 0.13, 0.87, 0.87] crop)
    centred = [0.13, 0.13, 0.87, 0.87]
    face_near_top = [0.40, 0.10, 0.60, 0.22]
    cropped_blind = SR_MOD.crop_box(arr, centred)
    cropped_aware = SR_MOD.crop_box(arr, centred, face_box=face_near_top)
    assert cropped_blind[:15, :, :].mean() == 0.0
    assert cropped_aware[:15, :, :].mean() > 20.0

    arr_wide = np.zeros((800, 1280, 3), dtype=np.uint8)
    arr_wide[10:30, :, :] = 250
    pil_img = Image.fromarray(arr_wide)
    fitted_blind = np.asarray(LJ.fit_picture(pil_img, 1280, 704))
    fitted_aware = np.asarray(LJ.fit_picture(pil_img, 1280, 704, face_box=[0.4, 0.04, 0.6, 0.18]))
    assert fitted_aware[:25, :, :].mean() > fitted_blind[:25, :, :].mean() + 50.0


# --- Audit #9: superres.qc does not fail Q3 against 2x upscale DETAIL_MIN when output size equals input size ---------------

def test_q3_not_judged_when_sizes_equal():
    """Audit #9: when result.shape == original.shape (same-size restoration, e.g. x1.72 gain < 2.0), Q3_detail_added passes."""
    import cv2
    rng = np.random.default_rng(19)
    orig = rng.integers(40, 200, (128, 128, 3), dtype=np.uint8)
    blur = cv2.GaussianBlur(orig.astype(np.float32), (0, 0), 1.2)
    restored = np.clip(orig.astype(np.float32) + 0.15 * (orig.astype(np.float32) - blur), 0, 255).astype(np.uint8)
    rows = {r["gate"]: r for r in SR_MOD.qc(orig, restored)}
    assert 1.0 < rows["Q3_detail_added"]["measured"] < SR_MOD.DETAIL_MIN
    assert rows["Q3_detail_added"]["status"] == G.PASS


# --- Audit #15: sound_plan gunshot event class resolves to gunshot take, never thunder/drums/twang -------------------------

def test_plan_impact_class_gunshot_resolves_to_gunshot_take(tmp_path):
    """Audit #15: 'gunshot' is a first-class event in EVENT_CLASSES and resolves to a gunshot/rifle take rather than thunder/drums."""
    assert "gunshot" in SP.EVENT_CLASSES
    lib = tmp_path / "lib"
    (lib / "sfx").mkdir(parents=True)
    for name in ("thunder_01.wav", "war_drums_01.wav", "rifle_gunshot_1914.wav"):
        (lib / "sfx" / name).write_bytes(b"RIFF" + b"\x00" * 40)
    manifest = {
        "items": [
            {"id": "thunder_01", "file": "sfx/thunder_01.wav", "tags": ["thunder", "impact"], "source": {"kind": "cc0", "url": "https://freesound.org/1", "license": "CC0-1.0"}, "license": "CC0-1.0", "qc": {"status": "PASS"}, "review": {"human": "approved"}},
            {"id": "war_drums_01", "file": "sfx/war_drums_01.wav", "tags": ["drum", "war", "impact"], "source": {"kind": "cc0", "url": "https://freesound.org/1", "license": "CC0-1.0"}, "license": "CC0-1.0", "qc": {"status": "PASS"}, "review": {"human": "approved"}},
            {"id": "rifle_gunshot_1914", "file": "sfx/rifle_gunshot_1914.wav", "tags": ["gunshot", "rifle"], "source": {"kind": "cc0", "url": "https://freesound.org/1", "license": "CC0-1.0"}, "license": "CC0-1.0", "qc": {"status": "PASS"}, "review": {"human": "approved"}},
        ]
    }
    (lib / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    plan = {"era": "ww1_1914", "classes": ["gunshot"]}
    resolved = SP.resolve(plan, lib)
    assert resolved["gunshot"]["status"] == "library"
    assert resolved["gunshot"]["ids"] == ["rifle_gunshot_1914"]


# --- Audit #21 (TD-336 & TD-337): negative_prompt not a forbidden use; silent_beat / stage direction not a word ------------

def test_negative_prompt_not_a_use(tmp_path):
    """Audit #21 (TD-336): forbidden era words listed inside negative_prompt (to keep them out of the picture) are not
    flagged as prompt violations by acceptance.gates or context.validate_asset_against_context."""
    script = {
        "episode_id": "ep_test",
        "shots": [
            {
                "shot_id": "S01_SH001",
                "route": "still_25d",
                "target_duration_seconds": 3.0,
                "narrative_purpose": "Soldiers in winter trench",
                "image_prompt": {
                    "start_frame_prompt": "1914 British soldiers in muddy trench under snow",
                    "negative_prompt": "modern smartphone, neon sign, wristwatch, skyscraper",
                },
            }
        ],
    }
    ep_root = tmp_path / "ep_test"
    ep_root.mkdir(parents=True, exist_ok=True)
    (ep_root / "episode.json").write_text(json.dumps({"episode_id": "ep_test"}))
    rep = ACC.gates(
        root=ep_root, script=script, shot_records=[], transition_plans=None,
        audio=None, stem_audit=None, video=None, fps=24,
        forbidden_tokens=["smartphone", "skyscraper"],
    )
    row_p = next(r for r in rep["gates"] if r["gate"] == "no_foreign_era_words_in_prompts")
    assert row_p["status"] == G.PASS and row_p["measured"] == []


def test_stage_direction_not_a_word():
    """Audit #21 (TD-337): silent_beat lines and parenthesized stage directions '(Thomas does not answer...)' are excluded
    from timing.read_order and maps.actions.shot_words."""
    script = {
        "audio_lines": [
            {"line_id": "L1", "speaker_type": "narrator", "text": "The guns fell silent."},
            {"line_id": "L2", "speaker_type": "silent_beat", "text": "(Thomas does not answer. He looks down at the mud.)"},
            {"line_id": "L3", "speaker_type": "narrator", "text": "(softly) Nobody moved."},
        ],
        "shots": [
            {"shot_id": "S01_SH001", "route": "still_25d", "audio_line_ids": ["L1", "L2", "L3"], "target_duration_seconds": 4.0},
        ],
    }
    assert TM.read_order(script) == ["L1", "L3"]
    assert MA.shot_words(script["shots"][0], script) == ["the", "guns", "fell", "silent", "nobody", "moved"]


# --- Audit #23 & #40: PRODUCTION_RULES.md canonical routes & BP-200 exterior weather wording -------------------------------

def test_bp200_statement_does_not_say_every_shot_of_the_scene():
    """Audit #40 & #23: BP-200 scopes scene weather to exterior/open-air shots, and PRODUCTION_RULES.md names canonical routes."""
    bp200 = SR.rule("BP-200")
    assert "every shot of the scene" not in bp200["statement"]
    assert "exterior" in bp200["statement"] or "open-air" in bp200["statement"]
    pr_text = (ROOT / "docs" / "PRODUCTION_RULES.md").read_text(encoding="utf-8")
    assert "(`map_action`, `still_25d`, `video`)" in pr_text
    assert "(`map_action`, `still_25d`, `wan`)" not in pr_text
    lint_checks = {f["check"] for f in docs_lint.check()}
    assert "stale_route_name" not in lint_checks
    assert "bp200_interior_weather" not in lint_checks


# --- Audit #29 & Part B6: All 3 renderers include code digest in version string --------------------------------------------

def test_all_renderers_version_track_code_hash():
    """Audit #29 & Part B6: directed25d.VERSION, layers25d.RENDERER_VERSION, and maps.actions.RENDERER_VERSION all embed a
    12-hex SHA-256 code digest so renderer fixes automatically invalidate cached clips."""
    import re
    assert re.fullmatch(r"directed25d/0\.2-[0-9a-f]{12}", D25.VERSION)
    assert re.fullmatch(r"layers25d/2\.1-[0-9a-f]{12}", L25.RENDERER_VERSION)
    assert re.fullmatch(r"map_action/2\.3-[0-9a-f]{12}", MA.RENDERER_VERSION)


# --- Audit #33: stage_clips preserves per-gate gate_rows in shot_records.json ----------------------------------------------

def test_clip_record_keeps_gate_rows(tmp_path, monkeypatch):
    """Audit #33 (FL-216): shot_records.json keeps the per-gate gate_rows list alongside the summary status."""
    from tests.unit.test_plan_step_3 import _make_episode, _shot, _write_fake_layers, _direction_doc
    shot = _shot("S01_SH001", duration_s=1.0)
    root = _make_episode(tmp_path, [shot])
    pic_path = root / "assets" / "generated" / "images" / "S01_SH001_start.png"
    _write_fake_layers(pic_path)
    dir_dir = root / "production" / "direction"
    dir_dir.mkdir(parents=True, exist_ok=True)
    (dir_dir / "S01_SH001.json").write_text(json.dumps(_direction_doc("S01_SH001"), indent=2), encoding="utf-8")

    ep = RUN.Episode(root, size=(192, 108), fps=FPS, rehearsal=True)
    RUN.stage_clips(ep, rehearsal=True)
    recs = json.loads((root / "production" / "shot_records.json").read_text(encoding="utf-8"))["shots"]
    assert len(recs) == 1
    assert isinstance(recs[0].get("gate_rows"), list) and len(recs[0]["gate_rows"]) >= 1
    assert all("gate" in r and "status" in r for r in recs[0]["gate_rows"])


# --- Audit #42: sound_plan.resolve filters and ranks modern tags out in ww1_1914 -------------------------------------------

def test_sound_plan_resolve_filters_modern_tags_in_ww1_1914(tmp_path):
    """Audit #42: sound_plan.resolve filters out garage/traffic/concrete/motel takes in ww1_1914 and ranks period takes first."""
    lib = tmp_path / "lib"
    (lib / "sfx").mkdir(parents=True)
    for name in ("fire_garage_burn.wav", "fire_campfire_crackle.wav"):
        (lib / "sfx" / name).write_bytes(b"RIFF" + b"\x00" * 40)
    manifest = {
        "items": [
            {"id": "fire_garage_burn", "file": "sfx/fire_garage_burn.wav", "tags": ["fire", "garage"], "source": {"kind": "cc0", "url": "https://freesound.org/1", "license": "CC0-1.0"}, "license": "CC0-1.0", "qc": {"status": "PASS"}, "review": {"human": "approved"}},
            {"id": "fire_campfire_crackle", "file": "sfx/fire_campfire_crackle.wav", "tags": ["fire", "campfire"], "source": {"kind": "cc0", "url": "https://freesound.org/1", "license": "CC0-1.0"}, "license": "CC0-1.0", "qc": {"status": "PASS"}, "review": {"human": "approved"}},
        ]
    }
    (lib / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    res = SP.resolve({"era": "ww1_1914", "classes": ["fire"]}, lib)
    assert res["fire"]["ids"] == ["fire_campfire_crackle"]


# --- Audit #44 & C4: sound_events schema allows why & RUN.stage_script checks inline or sidecar ----------------------------

def test_every_sound_event_has_reason_in_sidecar(tmp_path):
    """Audit #44 & C4: RUN.stage_script checks that every sound_event has either an inline 'why' or a reason in
    production/director_sound_reasons.json, and production_script.schema.json allows 'why' on sound_events."""
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    se_props = schema["$defs"]["ShotSpec"]["properties"]["sound_events"]["items"]["properties"]
    assert "why" in se_props

    truce_script = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    shots_mod = copy.deepcopy(truce_script["shots"])
    shots_mod[0]["sound_events"] = [{"event_id": "S01_SH001.S99", "class": "church_bell", "at_s": 0.5}]
    ep_root = _write_minimal_episode(tmp_path, {"shots": shots_mod})
    sidecar = ep_root / "production" / "director_sound_reasons.json"
    sidecar.write_text(json.dumps({"reasons": {}}), encoding="utf-8")

    rows_bad, _ = RUN.stage_script(RUN.Episode(ep_root, rehearsal=True), rehearsal=True)
    se_row_bad = next((r for r in rows_bad if r["gate"] == "sound_events_have_reasons"), None)
    assert se_row_bad is not None and se_row_bad["status"] == G.FAIL and "S01_SH001.S99" in se_row_bad["measured"]

    base_reasons = {}
    orig_sc = ROOT / "episodes" / "ep_truce_1914" / "production" / "director_sound_reasons.json"
    if orig_sc.is_file():
        base_reasons.update(json.loads(orig_sc.read_text(encoding="utf-8")).get("reasons", {}))
    for sh in shots_mod:
        for idx_e, ev in enumerate(sh.get("sound_events") or [], 1):
            eid = ev.get("event_id") or f"{sh['shot_id']}.S{idx_e}"
            base_reasons.setdefault(eid, "authored sound event reason")
    base_reasons["S01_SH001.S99"] = "midnight church bell across the frozen marsh"
    sidecar.write_text(json.dumps({"reasons": base_reasons}), encoding="utf-8")
    rows_ok, _ = RUN.stage_script(RUN.Episode(ep_root, rehearsal=True), rehearsal=True)
    se_row_ok = next((r for r in rows_ok if r["gate"] == "sound_events_have_reasons"), None)
    assert se_row_ok is not None and se_row_ok["status"] == G.PASS


# --- Audit #64 & C4: map_clip.render_action_map_clip emits map_not_standing_still citing CMP-08 / BP-147 ------------------

def test_map_gate_cites_map_rule(tmp_path, monkeypatch):
    """Audit #64 & C4: render_action_map_clip actually emits a map_not_standing_still gate row whose detail cites CMP-08 and
    BP-147 (not BP-164), and BP-55 mentions BP-192."""
    from explainer_engine.maps import relief
    rows_g, cols_g = np.mgrid[0:180, 0:360]
    arr = (128 + 80 * np.sin(cols_g / 9.0) * np.cos(rows_g / 7.0)).astype(np.uint8)
    Image.fromarray(arr, "L").save(tmp_path / relief.RASTER_NAME)
    (tmp_path / "SR_HR.tfw").write_text("1.0\n0.0\n0.0\n-1.0\n-179.5\n89.5\n", encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path))
    relief._load.cache_clear()

    shot = {
        "shot_id": "S01_SH008",
        "route": "map_action",
        "visual_type": "map_visualization",
        "target_duration_seconds": 1.0,
        "audio_line_ids": ["L1"],
        "actions": [{"kind": "route_arrow", "from": "paris", "to": "ypres", "at_word": "hundred"}],
    }
    script = {
        "episode_id": "ep_map",
        "fps": 12,
        "audio_lines": [{"line_id": "L1", "speaker_type": "narrator", "text": "One hundred men waited."}],
        "shots": [shot],
    }
    episode = {
        "episode_id": "ep_map",
        "places": {
            "paris": {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
            "ypres": {"name": "Ypres", "lat": 50.8511, "lon": 2.8857},
        },
        "historical_period": {"era_id": "ww1_1914"},
    }
    out_mp4 = tmp_path / "S01_SH008.mp4"
    res = MC.render_action_map_clip(shot, script, episode, out_mp4, width=192, height=108, fps=12, cache_dir=tmp_path)
    row_still = next(r for r in res["gates"]["gates"] if r["gate"] == "map_not_standing_still")
    assert "CMP-08" in row_still["detail"] and "BP-147" in row_still["detail"]
    assert "BP-164" not in row_still["detail"]
    assert "BP-192" in SR.rule("BP-55")["statement"]


# --- Audit #66 & C4: helper_lane_form_fit checked through RUN.stage_script -------------------------------------------------

def test_helper_fit_flags_time_promise_drawn_as_pure_map_and_passes_counter(tmp_path):
    """Audit #66 & C4 (MA-09): RUN.stage_script emits REVIEW on helper_lane_form_fit when a 10% helper shot whose narration
    is 'Home before the leaves fall' has only geographic route_arrow/label actions, and PASS when a progress_bar is added."""
    truce_script = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    shots_mod = copy.deepcopy(truce_script["shots"])
    lines_mod = copy.deepcopy(truce_script["audio_lines"])
    map_shot = next(s for s in shots_mod if s.get("route") == "map_action")
    lid = map_shot["audio_line_ids"][0]
    for ln in lines_mod:
        if ln["line_id"] == lid:
            ln["text"] = "They were promised they would be home before the leaves fall."
    map_shot["actions"] = [{"kind": "route_arrow", "from": "paris", "to": "ypres", "at_word": "home"}]

    ep_root = _write_minimal_episode(tmp_path, {"shots": shots_mod, "audio_lines": lines_mod})
    rows_bad, _ = RUN.stage_script(RUN.Episode(ep_root, rehearsal=True), rehearsal=True)
    hf_bad = next((r for r in rows_bad if r["gate"] == "helper_lane_form_fit"), None)
    assert hf_bad is not None and hf_bad["status"] == G.REVIEW and len(hf_bad["measured"]) >= 1

    map_shot["actions"].append({"kind": "progress_bar", "value": 4, "max": 4, "at_word": "leaves", "claim": "C1"})
    ep_root_ok = _write_minimal_episode(tmp_path / "ok", {"shots": shots_mod, "audio_lines": lines_mod})
    rows_ok, _ = RUN.stage_script(RUN.Episode(ep_root_ok, rehearsal=True), rehearsal=True)
    hf_ok = next((r for r in rows_ok if r["gate"] == "helper_lane_form_fit"), None)
    assert hf_ok is not None and hf_ok["status"] == G.PASS


# --- Audit #67 & C4: VL-14 checked through VP.findings(script) and RUN.stage_script ----------------------------------------

def test_video_edit_plan_flags_zero_continuations_across_same_scene_video_shots():
    """Audit #67 & C4 (VL-14): VP.findings(script) emits a VL-14 REVIEW finding when consecutive same-scene video shots have
    0 continuations across the episode, and clears it when a continuation is present."""
    script = {
        "shots": [
            {"shot_id": "S01_SH001", "segment_id": "S01", "location_id": "loc_1", "route": "video",
             "edit_plan": {"continuity_mode": "coverage", "scene_master": "M1", "cut_in_reason": "establish"}},
            {"shot_id": "S01_SH002", "segment_id": "S01", "location_id": "loc_1", "route": "video",
             "edit_plan": {"continuity_mode": "coverage", "scene_master": "M1", "cut_in_reason": "action"}},
            {"shot_id": "S01_SH003", "segment_id": "S01", "location_id": "loc_1", "route": "video",
             "edit_plan": {"continuity_mode": "coverage", "scene_master": "M1", "cut_in_reason": "action"}},
        ]
    }
    fs_bad = VP.findings(script)
    assert any(f["rule"] == "VL-14" and f["severity"] == G.REVIEW for f in fs_bad)
    assert VP.anchor_chain_rows(script)[0]["status"] == G.REVIEW

    script["shots"][1]["edit_plan"] = {"continuity_mode": "continuation", "continuity_from": "S01_SH001", "cut_in_reason": "action"}
    fs_ok = VP.findings(script)
    assert not any(f["rule"] == "VL-14" for f in fs_ok)
    assert VP.anchor_chain_rows(script)[0]["status"] == G.PASS


# --- C1 (Blocker): Evidence-only Scene Director (interior brazier vs exterior sky mask, no fabricated mist/dust/sky) -------

def test_c1_auto_director_uses_only_evidence_interior_brazier_vs_exterior_sky_mask():
    """C1: build_shot_direction_from_script never invents mist_bank, dust_motes, sky_canopy, or sky_open=True:
    1. On real script shot S02_SH009 (dusk, warm brazier light): sky_open is False, seen.lights has brazier, fx_brazier
       animates on the brazier light, and seen.living has NO sky, mist, or dust.
    2. On a synthetic interior dugout shot with brazier light and no sky mask: sky_open is False, NO sky element is produced,
       and the brazier light is animated.
    3. On an exterior shot with a sky mask in layers: sky_open is True and sky is kept and animated.
    4. On a bare shot with no visual evidence: returns needs_eye=True and status='REVIEW' instead of fabricating elements."""
    truce_script = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    s02_sh009 = next(s for s in truce_script["shots"] if s["shot_id"] == "S02_SH009")
    doc9 = LD.build_shot_direction_from_script(s02_sh009, truce_script)
    assert doc9["seen"]["sky_open"] is False
    assert any(li["id"] == "brazier" and li["kind"] == "fire" for li in doc9["seen"]["lights"])
    living_kinds_9 = {e["kind"] for e in doc9["seen"]["living"]}
    assert "sky" not in living_kinds_9 and "mist" not in living_kinds_9 and "dust" not in living_kinds_9
    assert "fire" in living_kinds_9
    assert any(t.get("op") == "fire" and "brazier" in (t.get("target") or {}).get("lights", []) for t in doc9["tracks"])

    # Synthetic interior dugout shot with brazier light in manifest and no sky mask
    dugout_shot = {
        "shot_id": "S03_DUGOUT",
        "segment_id": "S03",
        "route": "still_25d",
        "location_id": "loc_dugout_interior",
        "target_duration_seconds": 3.0,
        "lighting_and_time": "inside timber dugout, warm brazier light",
        "action_start_state": "Two soldiers sit beside a glowing brazier in the dugout",
    }
    dugout_layers = {
        "manifest": {
            "picture_sha256": "dugout123",
            "masks": {"objects": [{"id": "soldier", "prompt": "soldier", "where": [0.4, 0.55]}]},
            "lights": [{"id": "brazier", "kind": "fire", "point": [0.62, 0.72], "radius": 0.04}],
            "geometry": {"sky_area_pct": 0.0},
        }
    }
    doc_dugout = LD.build_shot_direction_from_script(dugout_shot, {"audio_lines": [], "shots": [dugout_shot]}, layers=dugout_layers)
    assert doc_dugout["seen"]["sky_open"] is False
    assert not any(e["kind"] == "sky" for e in doc_dugout["seen"]["living"])
    assert any(li["id"] == "brazier" for li in doc_dugout["seen"]["lights"])
    assert any(t.get("op") == "fire" and "brazier" in (t.get("target") or {}).get("lights", []) for t in doc_dugout["tracks"])

    # Synthetic exterior shot with a sky mask in layers keeps sky_open=True and sky element
    ext_shot = {
        "shot_id": "S01_EXT",
        "segment_id": "S01",
        "route": "still_25d",
        "location_id": "loc_no_mans_land",
        "target_duration_seconds": 3.0,
        "lighting_and_time": "dawn over open field, ground mist",
        "action_start_state": "Mist drifts under the dawn sky",
    }
    ext_layers = {
        "manifest": {
            "picture_sha256": "ext123",
            "masks": {
                "objects": [
                    {"id": "sky_canopy", "prompt": "sky", "where": [0.5, 0.18], "area_pct": 30.0},
                ]
            },
            "lights": [{"id": "sun", "kind": "sun", "point": [0.5, 0.22], "radius": 0.05}],
            "geometry": {"sky_area_pct": 30.0},
        }
    }
    doc_ext = LD.build_shot_direction_from_script(ext_shot, {"audio_lines": [], "shots": [ext_shot]}, layers=ext_layers)
    assert doc_ext["seen"]["sky_open"] is True
    assert any(e["kind"] == "sky" and e["decision"] != "skip" for e in doc_ext["seen"]["living"])

    # Bare shot with zero visual evidence sets needs_eye=True and status='REVIEW' without fabricating mist/dust/sky
    bare_shot = {"shot_id": "S99_BARE", "route": "still_25d", "target_duration_seconds": 2.5}
    doc_bare = LD.build_shot_direction_from_script(bare_shot, {"audio_lines": [], "shots": [bare_shot]}, layers={"manifest": {"picture_sha256": "b1"}})
    assert doc_bare["seen"]["living"] == []
    assert doc_bare.get("needs_eye") is True and doc_bare.get("status") == "REVIEW"


# --- A2.1, A2.2 & C2: Mandatory Scene Director in run.py + stage_direction single code path --------------------------------

def test_run_generates_and_validates_direction_and_fails_on_director_not_used(tmp_path, monkeypatch):
    """A2.1, A2.2 & C2: stage_clips (and stage_direction) automatically runs living_director, validates with direction.check,
    persists production/direction/<shot_id>.json, and renders with directed25d."""
    from tests.unit.test_plan_step_3 import _make_episode, _shot, _write_fake_layers
    shot = _shot("S01_SH001", duration_s=1.5, text="Quiet snow falls over the trench.")
    root = _make_episode(tmp_path, [shot])
    pic_path = root / "assets" / "generated" / "images" / "S01_SH001_start.png"
    _write_fake_layers(pic_path)

    dir_file = root / "production" / "direction" / "S01_SH001.json"
    assert not dir_file.exists()

    ep = RUN.Episode(root, size=(192, 108), fps=FPS, rehearsal=True)
    dir_rows, dir_meta = RUN.stage_direction(ep, rehearsal=True)
    assert dir_meta["directed"] == 1 and dir_file.is_file()
    dir_file.unlink()  # unlink to verify stage_clips calls stage_direction and re-persists it

    rows, _ = RUN.stage_clips(ep, rehearsal=True)
    assert dir_file.is_file(), "stage_clips must call stage_direction and persist production/direction/S01_SH001.json"
    gen_doc = json.loads(dir_file.read_text(encoding="utf-8"))
    assert gen_doc["schema"] == DIR.SCHEMA and gen_doc["shot_id"] == "S01_SH001"
    assert not [r for r in rows if r["gate"] == "director_not_used"]
    recs = json.loads((root / "production" / "shot_records.json").read_text(encoding="utf-8"))["shots"]
    assert recs[0]["provider"].startswith("directed25d/")


# --- A2.4: >5s still with no clause punctuation splits on safe word boundary -----------------------------------------------

def test_unpunctuated_long_still_splits_on_safe_word_boundary():
    """A2.4: a >5.0 s still_25d shot whose spine has no punctuation splits on a safe conjunction/preposition word boundary
    so every resulting sub-shot is <= 5.0 s and internal cuts use hard_cut (Part B7)."""
    words = ["soldiers", "waited", "silently", "inside", "the", "frozen", "muddy", "trenches", "while", "snow", "drifted", "across", "flanders"]
    spine = [
        {"word": w, "index": i, "start_s": round(i * 0.6, 3), "end_s": round((i + 1) * 0.6, 3),
         "start_frame": int(round(i * 0.6 * FPS)), "end_frame": int(round((i + 1) * 0.6 * FPS))}
        for i, w in enumerate(words)
    ]
    shot = {"shot_id": "S03_SH004", "route": "still_25d", "target_duration_seconds": 7.8, "total_frames": int(round(7.8 * FPS)),
            "transition_out": "fade_to_black"}
    parts = SS.split_long_still(shot, spine, max_s=5.0, fps=FPS)
    assert len(parts) == 2
    assert all(p["target_duration_seconds"] <= 5.0 for p in parts)
    assert parts[0]["transition_out"] == "hard_cut"
    assert parts[1]["transition_out"] == "fade_to_black"


# --- A2.5: Variety constraints are scoring + REVIEW, while banned lateral moves on people are FAIL -------------------------

def test_variety_constraints_are_review_and_scored_while_banned_moves_fail():
    """A2.5: sequence_variety_rows emits REVIEW (never FAIL) and computes a variety score, and score_camera_candidates lets a
    story_locked shot repeat a move when required by storytelling while ranking varied moves first by default."""
    ranked_default = LD.score_camera_candidates(["push", "pan_crop_2d", "pull"], prev_op="push", recent_non_map=["push", "push"])
    assert ranked_default[0]["op"] == "pan_crop_2d"

    ranked_locked = LD.score_camera_candidates(["push", "pan_crop_2d", "pull"], prev_op="push", recent_non_map=["push"], story_locked=True)
    assert ranked_locked[0]["op"] == "push"

    dirs = [
        {"shot_id": f"S01_SH00{i}", "kind": "photo", "route": "still_25d",
         "choice": {"audit": {"chosen": {"primary_op": "push"}}}}
        for i in range(1, 6)
    ]
    v_rows = DIR.sequence_variety_rows(dirs)
    assert all(r["status"] == G.REVIEW for r in v_rows)
    assert all(r["status"] != G.FAIL for r in v_rows)


# --- Part B1 (Audit #22): qa/sound_realism.py bed_across_cuts masks SFX events and bounds fallback window ------------------

def test_bed_across_cuts_ignores_sfx_bursts_and_distant_windows(tmp_path):
    """Part B1: a loud gunshot/SFX event or a loud swell 6 seconds away from a cut is not mistaken for a 15 dB bed jump at the cut."""
    sr = 48000
    dur = 10.0
    n = int(dur * sr)
    rng = np.random.default_rng(7)
    bed = (rng.standard_normal(n) * 0.0316).astype(np.float64)
    bed[int(0.5 * sr):int(1.5 * sr)] *= 6.0
    bed[int(4.6 * sr):int(4.9 * sr)] *= 6.0
    pcm = np.clip(bed * 32767, -32768, 32767).astype("<i2")
    wav_path = tmp_path / "test_mix.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

    tl = {
        "duration_s": dur,
        "cuts": [5.0],
        "lines": [{"id": "L1", "start_s": 4.55, "end_s": 4.65}],
        "dialogue": [],
        "pauses": [],
        "events": [{"event_id": "E1", "kind": "spot", "class": "gunshot", "at_s": 4.6, "dur_s": 0.3}],
        "beds": [],
    }
    res = RL.measure(wav_path, tl)
    row_bed = next(r for r in res["rows"] if r["gate"] == "bed_across_cuts")
    assert row_bed["status"] == G.PASS
    assert res["measured"]["cuts"][0]["jump_db"] < 1.5


# --- Part B2 & B3: stage_assemble transition alignment and acceptance.py camera_motion_measured on split stills ------------

def test_stage_assemble_and_acceptance_handle_split_still_shots(tmp_path):
    """Part B2 & B3: _expand_script_for_records aligns transition plans with split still_25d shot records, and
    acceptance.gates recognises split sub-records (S02_SH008a, S02_SH008b) for parent shot S02_SH008."""
    from explainer_engine.edit.cinematic_transitions import plan_episode_cinematic_transitions
    script = {
        "episode_id": "ep_split",
        "shots": [
            {"shot_id": "S02_SH008", "segment_id": "S02", "location_id": "loc_trench", "route": "still_25d",
             "target_duration_seconds": 8.0, "transition_out": "cross_dissolve_8f"},
            {"shot_id": "S02_SH009", "segment_id": "S03", "location_id": "loc_field", "route": "video",
             "target_duration_seconds": 4.0, "transition_out": "hard_cut"},
        ],
    }
    records = [
        {"shot_id": "S02_SH008a", "parent_shot_id": "S02_SH008", "route": "still_25d", "duration_sec": 4.0, "total_frames": 96, "gates_25d": "PASS"},
        {"shot_id": "S02_SH008b", "parent_shot_id": "S02_SH008", "route": "still_25d", "duration_sec": 4.0, "total_frames": 96, "gates_25d": "PASS"},
        {"shot_id": "S02_SH009", "route": "video", "duration_sec": 4.0, "total_frames": 96, "status": "PASS"},
    ]
    expanded = RUN._expand_script_for_records(script, records, FPS)
    plans = plan_episode_cinematic_transitions(expanded, fps=FPS, honour_authored=True)
    assert len(plans) == len(records) - 1 == 2
    assert plans[0]["from_shot_id"] == "S02_SH008a" and plans[0]["to_shot_id"] == "S02_SH008b"
    assert plans[0]["transition_frames"] == 0
    assert plans[1]["from_shot_id"] == "S02_SH008b" and plans[1]["to_shot_id"] == "S02_SH009"
    assert plans[1]["transition_type"] == "cross_dissolve_8f"

    ep_root = tmp_path / "ep_split"
    ep_root.mkdir(parents=True, exist_ok=True)
    (ep_root / "episode.json").write_text(json.dumps({"episode_id": "ep_split"}))
    acc = ACC.gates(root=ep_root, script=script, shot_records=records, transition_plans=plans,
                    audio=None, stem_audit=None, video=None, fps=FPS)
    cam_row = next(r for r in acc["gates"] if r["gate"] == "camera_motion_measured")
    assert cam_row["status"] == G.PASS


# --- Part B4: _with_line_times partitions multi-line shots and skips silent_beat lines ------------------------------------

def test_with_line_times_partitions_multi_line_and_split_shots():
    """Part B4: _with_line_times gives distinct non-overlapping windows to multiple spoken lines in one shot and skips silent_beat."""
    script = {
        "fps": 24,
        "audio_lines": [
            {"line_id": "L1", "speaker_type": "narrator", "text": "One two"},
            {"line_id": "L_SIL", "speaker_type": "silent_beat", "text": "(silence)"},
            {"line_id": "L2", "speaker_type": "narrator", "text": "Three four"},
        ],
        "shots": [
            {"shot_id": "S01_SH001", "target_duration_seconds": 4.0, "audio_line_ids": ["L1", "L_SIL", "L2"]},
        ],
    }
    timed = {
        "fps": 24,
        "spines": {
            "S01_SH001": [
                {"word": "one", "start_frame": 0},
                {"word": "two", "start_frame": 12},
                {"word": "three", "start_frame": 48},
                {"word": "four", "start_frame": 72},
            ]
        },
    }
    out = RUN._with_line_times(script, timed)
    by_lid = {ln["line_id"]: ln for ln in out["audio_lines"]}
    assert "start_sec" not in by_lid["L_SIL"]
    assert by_lid["L1"]["start_sec"] == 0.0 and by_lid["L1"]["end_sec"] == 2.0
    assert by_lid["L2"]["start_sec"] == 2.0 and by_lid["L2"]["end_sec"] == 4.0


# --- Part B5 & B8: layers25d.SEGMENTS_MAX == 3 and every repo .py file parses on Python 3.11 AST --------------------------

def test_layers25d_accepts_three_camera_segments_and_all_py_files_parse():
    """Part B5 & B8: layers25d.SEGMENTS_MAX matches direction.SEGMENTS_MAX == 3 (R-19), and all .py files parse cleanly."""
    assert L25.SEGMENTS_MAX == DIR.SEGMENTS_MAX == 3
    for p in (ROOT / "explainer_engine").rglob("*.py"):
        ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
