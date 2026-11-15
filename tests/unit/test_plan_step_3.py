"""Unit tests for Plan Step 3 (T6 scene director wiring in episode/run.py and T7 long still splitting in episode/shot_split.py).

Synthetic numpy only, no model weights, no direct sys.modules mutation.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.episode import run as RUN
from explainer_engine.production import directed25d as D25
from explainer_engine.production import direction as DIR
from explainer_engine.production import layers25d as L25
from explainer_engine.production import understand as U
from explainer_engine.qa import gates as G
from explainer_engine.qa import motion_intent as MI

FPS = 24
SIZE = (192, 108)


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_episode(tmp_path: Path, shots: list[dict], audio_lines: list[dict] | None = None,
                  spines: dict[str, list[dict]] | None = None) -> Path:
    root = tmp_path / "ep_step3"
    (root / "story").mkdir(parents=True, exist_ok=True)
    (root / "production").mkdir(parents=True, exist_ok=True)
    (root / "audio").mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "episode_manifest/1",
        "episode_id": "ep_step3",
        "title": "Step 3 Test Episode",
        "fps": FPS,
        "render_size": list(SIZE),
        "run_scope": "sample",
        "historical_period": {"era_id": "ww1_1914", "label": "December 1914"},
    }
    (root / "episode.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if audio_lines is None:
        audio_lines = [
            {
                "line_id": f"L_{s['shot_id']}",
                "segment_id": s.get("segment_id", "S01"),
                "speaker_type": "narrator",
                "speaker_id": "narrator",
                "text": s.get("narration_excerpt", "Quiet snow falls over the trench."),
            }
            for s in shots
        ]
    script = {
        "episode_id": "ep_step3",
        "title": "Step 3 Test Episode",
        "fps": FPS,
        "historical_period": {"era_id": "ww1_1914"},
        "segments": [{"segment_id": "S01", "title": "One"}],
        "audio_lines": audio_lines,
        "shots": shots,
    }
    (root / "story" / "production_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    # Write synthetic start pictures and production/pictures.json.
    img_dir = root / "assets" / "generated" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    pics = {}
    for s in shots:
        sid = s["shot_id"]
        arr = rng.integers(30, 220, (SIZE[1], SIZE[0], 3), dtype=np.uint8)
        pic_path = img_dir / f"{sid}_start.png"
        Image.fromarray(arr).save(pic_path)
        pics[f"{sid}_start"] = {
            "file": str(pic_path.relative_to(root)),
            "grade": "master",
            "sha256": _sha256_bytes(pic_path),
        }
    (root / "production" / "pictures.json").write_text(
        json.dumps({"episode_id": "ep_step3", "pictures": pics}, indent=2), encoding="utf-8"
    )

    if spines is not None:
        timing_shots = {}
        t_frame = 0
        for s in shots:
            sid = s["shot_id"]
            n_frames = max(1, int(round(float(s["target_duration_seconds"]) * FPS)))
            timing_shots[sid] = {
                "start_frame": t_frame,
                "frames": n_frames,
                "duration_s": round(n_frames / FPS, 4),
            }
            t_frame += n_frames
        timing_doc = {
            "schema": "episode_timing/1",
            "fps": FPS,
            "total_frames": t_frame,
            "shots": timing_shots,
            "spines": spines,
        }
        (root / "audio" / "timing.json").write_text(json.dumps(timing_doc, indent=2), encoding="utf-8")
    return root


def _write_fake_layers(pic_path: Path, sha256: str | None = None) -> Path:
    ldir = U.layers_dir(pic_path)
    (ldir / "masks").mkdir(parents=True, exist_ok=True)
    (ldir / "lights").mkdir(parents=True, exist_ok=True)
    img = np.asarray(Image.open(pic_path).convert("RGB"))
    h, w = img.shape[:2]
    depth = np.repeat(np.linspace(20, 230, h, dtype=np.uint8)[:, None], w, axis=1)
    Image.fromarray(depth, mode="L").save(ldir / "depth.png")
    Image.fromarray(img).save(ldir / "plate.png")
    hole = np.zeros((h, w), dtype=np.uint8)
    hole[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3] = 255
    Image.fromarray(hole, mode="L").save(ldir / "hole.png")
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[h // 3 + 2 : 2 * h // 3 - 2, w // 3 + 2 : 2 * w // 3 - 2] = 255
    Image.fromarray(mask, mode="L").save(ldir / "masks" / "soldier.png")
    manifest = {
        "schema": U.SCHEMA,
        "picture": pic_path.name,
        "picture_sha256": sha256 if sha256 is not None else _sha256_bytes(pic_path),
        "size": [w, h],
        "depth": {"file": "depth.png", "far_is_zero": True},
        "plate": {"file": "plate.png", "hole": "hole.png"},
        "masks": {"objects": [{"id": "soldier", "prompt": "soldier", "file": "masks/soldier.png", "layer": True}]},
        "lights": [],
    }
    (ldir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ldir


def _direction_doc(shot_id: str, op: str = "push", strength: float = 1.08) -> dict:
    return {
        "schema": DIR.SCHEMA,
        "shot_id": shot_id,
        "kind": "photo",
        "intent": "intended",
        "far_share": 0.2,
        "seen": {
            "what": "soldier in winter trench under falling snow",
            "objects": [{"id": "soldier", "names": ["soldier"], "box": [0.33, 0.33, 0.66, 0.66]}],
            "lights": [],
            "living": [{"kind": "snow", "where": "full frame", "decision": "animate", "effects": ["snow"]}],
        },
        "tracks": [
            {
                "track": "camera",
                "op": op,
                "renderer": "directed25d",
                "params": {"strength": strength, "ease": "ease_in_out"},
                "timing": {"start": {"frac": 0.0}, "end": {"frac": 1.0}},
                "target": {"point": [0.5, 0.45]},
                "validate": {"gate": "motion_matches_intent"},
            },
            {
                "track": "atmosphere",
                "op": "snow",
                "renderer": "directed25d",
                "params": {"strength": 1.0},
                "timing": {"start": {"frac": 0.0}, "end": {"frac": 1.0}},
                "target": {},
            },
        ],
        "keep_in_frame": [],
    }


def _shot(shot_id: str = "S01_SH001", duration_s: float = 2.0, text: str = "Quiet snow falls over the trench.") -> dict:
    return {
        "shot_id": shot_id,
        "segment_id": "S01",
        "route": "still_25d",
        "route_reason": "narrated still",
        "visual_type": "cinematic_scene",
        "target_duration_seconds": duration_s,
        "audio_line_ids": [f"L_{shot_id}"],
        "narration_excerpt": text,
        "keyframe_plan": {"needs_start_frame": True, "needs_end_frame": False},
        "motion_imitation": [{"effect": "push", "strength": 1.06}, {"effect": "mist"}, {"effect": "dust"}],
    }


# --- T6 tests -------------------------------------------------------------------------------------------------------------

def test_t6_direction_and_valid_layers_calls_directed25d_and_records_qa_rows(tmp_path, monkeypatch):
    shot = _shot("S01_SH001", duration_s=1.0)
    root = _make_episode(tmp_path, [shot])
    pic_path = root / "assets" / "generated" / "images" / "S01_SH001_start.png"
    _write_fake_layers(pic_path)
    dir_dir = root / "production" / "direction"
    dir_dir.mkdir(parents=True, exist_ok=True)
    (dir_dir / "S01_SH001.json").write_text(json.dumps(_direction_doc("S01_SH001"), indent=2), encoding="utf-8")

    called = {"directed": 0, "layers25d": 0, "watch": None, "plan": None}
    real_directed = D25.render_clip
    real_layers25d = L25.render_clip

    def spy_directed(picture, layers, plan, out_mp4, size=(1920, 1080), fps=24, watch=None, **kw):
        called["directed"] += 1
        called["watch"] = watch
        called["plan"] = plan
        return real_directed(picture, layers, plan, out_mp4, size=size, fps=fps, watch=watch, **kw)

    def spy_layers25d(*args, **kwargs):
        called["layers25d"] += 1
        return real_layers25d(*args, **kwargs)

    monkeypatch.setattr(D25, "render_clip", spy_directed)
    monkeypatch.setattr(L25, "render_clip", spy_layers25d)

    ep = RUN.Episode(root, size=SIZE, fps=FPS, rehearsal=True)
    rows, _ = RUN.stage_clips(ep, rehearsal=True)
    gates = [r["gate"] for r in rows]

    assert called["directed"] == 1
    assert called["layers25d"] == 0
    assert isinstance(called["watch"], MI.Watch)
    assert called["plan"]["shot_id"] == "S01_SH001" and called["plan"]["frames"] == FPS
    assert "fill_reveal" in gates and "double_edge" in gates and "effect_seen_3s" in gates
    assert "director_not_used" not in gates


def test_t6_missing_or_stale_direction_and_layers_falls_back_to_layers25d_with_review_row(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    s1 = _shot("S01_SH001", duration_s=1.0)
    s2 = _shot("S01_SH002", duration_s=1.0)
    s3 = _shot("S01_SH003", duration_s=1.0)
    root = _make_episode(tmp_path, [s1, s2, s3])

    dir_dir = root / "production" / "direction"
    dir_dir.mkdir(parents=True, exist_ok=True)
    # S01_SH001 has no direction file ("no direction").
    # S01_SH002 has a direction file but no .layers/ cache ("no layers").
    (dir_dir / "S01_SH002.json").write_text(json.dumps(_direction_doc("S01_SH002"), indent=2), encoding="utf-8")
    # S01_SH003 has a direction file and a .layers/ cache with a stale sha256 ("stale layers").
    (dir_dir / "S01_SH003.json").write_text(json.dumps(_direction_doc("S01_SH003"), indent=2), encoding="utf-8")
    pic3 = root / "assets" / "generated" / "images" / "S01_SH003_start.png"
    _write_fake_layers(pic3, sha256="0" * 64)

    called = {"directed": 0, "layers25d": 0}
    real_layers25d = L25.render_clip

    def spy_directed(*args, **kwargs):
        called["directed"] += 1
        raise AssertionError("directed25d should not be called when direction/layers are missing or stale")

    def spy_layers25d(*args, **kwargs):
        called["layers25d"] += 1
        return real_layers25d(*args, **kwargs)

    monkeypatch.setattr(D25, "render_clip", spy_directed)
    monkeypatch.setattr(L25, "render_clip", spy_layers25d)

    ep = RUN.Episode(root, size=SIZE, fps=FPS, rehearsal=True)
    rows, _ = RUN.stage_clips(ep, rehearsal=True)

    assert called["directed"] == 0
    assert called["layers25d"] == 3
    not_used = [r for r in rows if r["gate"] == "director_not_used"]
    assert len(not_used) == 3
    assert all(r["status"] == G.FAIL for r in not_used)  # A2.1/A2.2: director_not_used is a hard technical veto (FAIL)
    details = " | ".join(r["detail"] for r in not_used)
    assert "no direction" in details
    assert "no layers" in details
    assert "stale layers" in details


def test_t6_changing_direction_file_or_renderer_changes_clip_key(tmp_path):
    shot = _shot("S01_SH001", duration_s=1.0)
    root = _make_episode(tmp_path, [shot])
    ep = RUN.Episode(root, size=SIZE, fps=FPS, rehearsal=True)
    files = [{"file": "assets/generated/images/S01_SH001_start.png", "sha256": "abc"}, None]
    spine = [{"word": "quiet", "index": 0, "start_frame": 0, "end_frame": 12}]

    k_no_dir = RUN._clip_key(shot, files, ep, spine, renderer=L25.RENDERER_VERSION)
    dir_dir = root / "production" / "direction"
    dir_dir.mkdir(parents=True, exist_ok=True)
    dir_file = dir_dir / "S01_SH001.json"
    dir_file.write_text(json.dumps(_direction_doc("S01_SH001", op="push", strength=1.06)), encoding="utf-8")
    k_dir_1 = RUN._clip_key(shot, files, ep, spine, renderer=D25.VERSION)

    dir_file.write_text(json.dumps(_direction_doc("S01_SH001", op="pull", strength=1.12)), encoding="utf-8")
    k_dir_2 = RUN._clip_key(shot, files, ep, spine, renderer=D25.VERSION)
    k_renderer_switch = RUN._clip_key(shot, files, ep, spine, renderer=L25.RENDERER_VERSION)

    assert k_no_dir != k_dir_1
    assert k_dir_1 != k_dir_2
    assert k_dir_2 != k_renderer_switch


# --- T7 tests -------------------------------------------------------------------------------------------------------------

def _s02_sh008_spine() -> list[dict]:
    """Synthetic spine for a 10.96 s (263-frame) shot with clause/sentence ends at 4.6 s ('truce.'), 5.2 s ('failed.'),
    and 8.8 s ('agreed.')."""
    spec = [
        ("In", 0.0, 0.35),
        ("early", 0.35, 0.80),
        ("December", 0.80, 1.50),
        ("the", 1.55, 1.80),
        ("Pope", 1.80, 2.30),
        ("asked", 2.30, 2.85),
        ("for", 2.85, 3.15),
        ("a", 3.15, 3.35),
        ("Christmas", 3.35, 4.00),
        ("truce.", 4.00, 4.60),       # sentence end at 4.6 s (frame 110)
        ("The", 4.62, 4.78),
        ("appeal", 4.78, 5.00),
        ("failed.", 5.00, 5.20),      # sentence end at 5.2 s (frame 125)
        ("No", 5.30, 5.75),
        ("official", 5.75, 6.55),
        ("truce", 6.55, 7.25),
        ("was", 7.25, 7.90),
        ("agreed.", 7.90, 8.80),      # sentence end at 8.8 s (frame 211)
        ("Nobody", 8.85, 9.35),
        ("asked", 9.35, 9.75),
        ("the", 9.75, 10.00),
        ("men", 10.00, 10.30),
        ("in", 10.30, 10.50),
        ("the", 10.50, 10.68),
        ("trenches.", 10.68, 10.96),
    ]
    out = []
    for idx, (w, s0, s1) in enumerate(spec):
        out.append({
            "word": w,
            "index": idx,
            "start_s": s0,
            "end_s": s1,
            "start_frame": int(round(s0 * FPS)),
            "end_frame": 263 if idx == len(spec) - 1 else int(round(s1 * FPS)),
        })
    return out


def test_t7_split_long_still_10_96s_splits_at_nearest_legal_boundary_into_parts_le_5s(tmp_path, monkeypatch):
    from explainer_engine.episode.shot_split import split_long_still

    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    spine = _s02_sh008_spine()
    text = " ".join(w["word"] for w in spine)
    shot = _shot("S02_SH008", duration_s=10.96, text=text)
    shot["total_frames"] = 263
    shot["people_centre"] = [0.58, 0.42]

    parts = split_long_still(shot, spine, max_s=5.0)
    assert [p["shot_id"] for p in parts] == ["S02_SH008a", "S02_SH008b", "S02_SH008c"]
    assert all(p["target_duration_seconds"] <= 5.0 for p in parts)
    assert [p["target_duration_seconds"] for p in parts] == [4.6, 4.2, 2.16]
    # Nearest legal first boundary is 4.6 s ("truce."), not 5.2 s ("failed." > 5.0 s).
    assert parts[0]["spine"][-1]["word"] == "truce."
    assert parts[1]["spine"][-1]["word"] == "agreed."
    assert parts[1]["framing"] == {"crop": 1.0, "focus": [0.58, 0.42]}
    assert parts[2]["framing"] == {"crop": 1.0, "focus": [0.58, 0.42]}

    # IDs, frames, durations, and word ranges add up exactly to the original shot.
    assert sum(p["frames"] for p in parts) == 263
    assert sum(p["total_frames"] for p in parts) == 263
    assert round(sum(p["target_duration_seconds"] for p in parts), 4) == 10.96
    ranges = [p["word_range"] for p in parts]
    assert ranges[0][0] == 0 and ranges[-1][1] == len(spine)
    assert all(a[1] == b[0] for a, b in zip(ranges, ranges[1:]))
    assert [w["word"] for p in parts for w in p["spine"]] == [w["word"] for w in spine]

    # Running stage_clips records split_long_still REVIEW row and never edits production_script.json.
    root = _make_episode(tmp_path, [shot], spines={"S02_SH008": spine})
    script_path = root / "story" / "production_script.json"
    script_before = script_path.read_text(encoding="utf-8")
    ep = RUN.Episode(root, size=SIZE, fps=FPS, rehearsal=True)
    rows, _ = RUN.stage_clips(ep, rehearsal=True)
    assert script_path.read_text(encoding="utf-8") == script_before

    split_rows = [r for r in rows if r["gate"] == "split_long_still"]
    assert len(split_rows) == 1 and split_rows[0]["status"] == G.REVIEW
    detail = split_rows[0]["detail"]
    assert "S02_SH008" in detail
    assert "S02_SH008a" in detail and "S02_SH008b" in detail and "S02_SH008c" in detail
    assert "truce." in detail and "agreed." in detail
    recs = json.loads((root / "production" / "shot_records.json").read_text(encoding="utf-8"))["shots"]
    assert [r["shot_id"] for r in recs] == ["S02_SH008a", "S02_SH008b", "S02_SH008c"]
    assert sum(r["total_frames"] for r in recs) == 263


def test_t7_7s_shot_without_punctuation_stays_whole_with_review_row(tmp_path, monkeypatch):
    """A2.4 & A2.2: a 7s unpunctuated multi-word still splits on a safe word boundary (before 'inside') into parts <= 5.0 s;
    an unsplittable 1-word >5s still emits long_still_unsplit with status G.FAIL (never REVIEW)."""
    from explainer_engine.episode.shot_split import split_long_still

    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    words = ["nobody", "asked", "the", "men", "waiting", "inside", "the", "frozen", "trenches", "that", "night"]
    spine = []
    for i, w in enumerate(words):
        s0 = round(i * (7.0 / len(words)), 4)
        s1 = round((i + 1) * (7.0 / len(words)), 4)
        spine.append({
            "word": w,
            "index": i,
            "start_s": s0,
            "end_s": s1,
            "start_frame": int(round(s0 * FPS)),
            "end_frame": int(round(s1 * FPS)),
        })
    shot = _shot("S01_SH009", duration_s=7.0, text=" ".join(words))
    parts = split_long_still(copy.deepcopy(shot), spine, max_s=5.0)
    assert [p["shot_id"] for p in parts] == ["S01_SH009a", "S01_SH009b"]
    assert all(p["target_duration_seconds"] <= 5.0 for p in parts)
    assert parts[0]["cut_word"] == "waiting"

    # A 1-word 7.0s shot cannot be split on any word boundary -> emits long_still_unsplit as G.FAIL (A2.2).
    one_word_spine = [{"word": "silence", "index": 0, "start_s": 0.0, "end_s": 7.0, "start_frame": 0, "end_frame": 7 * FPS}]
    shot_1w = _shot("S01_SH010", duration_s=7.0, text="silence")
    root = _make_episode(tmp_path, [shot_1w], spines={"S01_SH010": one_word_spine})
    ep = RUN.Episode(root, size=SIZE, fps=FPS, rehearsal=True)
    rows, _ = RUN.stage_clips(ep, rehearsal=True)
    unsplit = [r for r in rows if r["gate"] == "long_still_unsplit"]
    assert len(unsplit) == 1 and unsplit[0]["status"] == G.FAIL
    assert "S01_SH010" in unsplit[0]["detail"]
