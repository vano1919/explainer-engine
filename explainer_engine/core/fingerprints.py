"""Deterministic dependency fingerprints for perception, direction, and sound artefacts (Task 2 R2 Step 1, Requirement C).

Extends ``production/understand.py``'s caching discipline across the crew pipeline so a cached ``perception.json``,
``direction/<shot_id>.json``, or ``sound_plan.json`` is reused if and only if every upstream input (picture SHA-256,
relevant script fields, spoken narration + word spine, director brief, perception output + model version, knowledge-base
hashes, and module code digests) matches bit-for-bit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def canonical_json(obj: Any) -> str:
    """Return a deterministic, sorted-key JSON string suitable for SHA-256 hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_obj(obj: Any) -> str:
    """Return the hex SHA-256 of ``obj`` serialized via ``canonical_json``."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path | str | None) -> str | None:
    """Return the hex SHA-256 of a file on disk, or None when the path does not exist."""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_digest(
    rel_paths: tuple[str, ...] | list[str],
    *,
    optional_paths: tuple[str, ...] | list[str] = (),
) -> str:
    """Return a 16-char normalized SHA-256 over the given repository-relative source files.

    Raises ``FileNotFoundError`` if any required path in ``rel_paths`` is missing so cache
    fingerprints never silently ignore renamed or deleted source files.
    """
    h = hashlib.sha256()
    missing = [rel for rel in sorted(rel_paths) if not (REPO_ROOT / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"Required code_digest source file(s) missing: {missing}")
    for rel in sorted(rel_paths):
        p = REPO_ROOT / rel
        h.update(rel.encode("utf-8") + b"\0")
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    for rel in sorted(optional_paths):
        p = REPO_ROOT / rel
        if p.is_file():
            h.update(b"opt:" + rel.encode("utf-8") + b"\0")
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


PERCEPTION_CODE_FILES = (
    "explainer_engine/production/understand.py",
    "explainer_engine/production/perceive_picture.py",
)

DIRECTOR_CODE_FILES = (
    "explainer_engine/production/living_director.py",
    "explainer_engine/fx25d/living.py",
    "explainer_engine/production/motion_isolation.py",
    "explainer_engine/production/perceive_picture.py",
)

SOUND_CODE_FILES = (
    "explainer_engine/episode/sound_plan.py",
    "explainer_engine/episode/events.py",
    "explainer_engine/production/living_director.py",
)


def shot_script_slice(shot: dict, script: dict | None = None) -> dict:
    """Extract the canonical script fields of ``shot`` and its spoken ``audio_lines`` that affect perception and direction."""
    keep_keys = (
        "shot_id", "segment_id", "target_duration_seconds", "narrative_purpose", "visual_type",
        "generation_mode", "location_id", "character_ids", "prop_ids", "audio_line_ids",
        "action_start_state", "action_end_state", "camera_spec", "screen_composition",
        "lighting_and_time", "image_prompt", "video_prompt", "route", "shot_role",
        "motion_imitation", "actions", "sound_events", "intentional_silence", "sound_design",
        "director_brief", "authored_intent_archive", "map_view", "scene", "seen",
    )
    sl = {k: shot.get(k) for k in keep_keys if shot.get(k) is not None}
    if isinstance(script, dict):
        lids = set(shot.get("audio_line_ids") or [])
        lines = [
            {k: ln.get(k) for k in ("line_id", "text", "delivery_direction", "speaker_id")}
            for ln in (script.get("audio_lines") or [])
            if isinstance(ln, dict) and ln.get("line_id") in lids
        ]
        sl["_resolved_audio_lines"] = lines
        if script.get("rhythm_profile"):
            sl["_rhythm_profile"] = script.get("rhythm_profile")
    return sl


def perception_fingerprint(
    picture_sha256: str | None,
    manifest: dict | None,
    shot: dict | None = None,
    detector_model: str = "deterministic_mask_hsv/1.0",
    inference_settings: dict | None = None,
) -> str:
    """Return the deterministic dependency fingerprint for a ``PerceptionResult``."""
    man_meta = {}
    if isinstance(manifest, dict):
        man_meta = {
            "key": manifest.get("key"),
            "picture_sha256": manifest.get("picture_sha256"),
            "objects": manifest.get("masks", {}).get("objects") if isinstance(manifest.get("masks"), dict) else None,
            "lights": manifest.get("lights"),
            "sky": manifest.get("sky"),
        }
    payload = {
        "schema": "perception_fp/1.0",
        "picture_sha256": picture_sha256 or man_meta.get("picture_sha256") or "",
        "manifest": man_meta,
        "shot_queries": {
            "shot_id": (shot or {}).get("shot_id"),
            "action_start_state": (shot or {}).get("action_start_state"),
            "screen_composition": (shot or {}).get("screen_composition"),
            "lighting_and_time": (shot or {}).get("lighting_and_time"),
            "director_brief": (shot or {}).get("director_brief"),
            "seen": (shot or {}).get("seen"),
        },
        "detector_model": detector_model,
        "inference_settings": inference_settings or {},
        "code_digest": code_digest(PERCEPTION_CODE_FILES),
    }
    return sha256_obj(payload)


def direction_fingerprint(
    shot: dict,
    script: dict | None = None,
    *,
    picture_sha256: str | None = None,
    manifest: dict | None = None,
    perception: dict | None = None,
    spine: list[dict] | None = None,
    fps: float = 24.0,
) -> str:
    """Return the deterministic dependency fingerprint for a ``shot_direction/1-draft`` document."""
    man_d = manifest if isinstance(manifest, dict) else {}
    pic_sha = (
        picture_sha256
        or (perception or {}).get("provenance", {}).get("picture_sha256")
        or man_d.get("picture_sha256")
        or shot.get("picture_sha256")
        or ""
    )
    perc_fp = (perception or {}).get("dependency_fingerprint") or perception_fingerprint(pic_sha, man_d, shot)
    kb_hashes = {
        "director_kb": sha256_file(REPO_ROOT / "explainer_engine" / "standards" / "director_knowledge_base.json"),
        "motion_isolation": sha256_file(REPO_ROOT / "explainer_engine" / "standards" / "motion_isolation.json"),
        "screenwriter_guide": sha256_file(REPO_ROOT / "explainer_engine" / "standards" / "screenwriter_guide.json"),
    }
    spine_clean = [
        {k: w.get(k) for k in ("word", "frame", "start_frame", "end_frame") if k in w}
        for w in (spine or [])
        if isinstance(w, dict)
    ]
    payload = {
        "schema": "direction_fp/1.0",
        "picture_sha256": pic_sha,
        "shot_slice": shot_script_slice(shot, script),
        "spine": spine_clean,
        "fps": round(float(fps), 4),
        "perception_fingerprint": perc_fp,
        "manifest_key": man_d.get("key"),
        "knowledge_bases": kb_hashes,
        "director_code_digest": code_digest(DIRECTOR_CODE_FILES),
    }
    return sha256_obj(payload)


def sound_plan_fingerprint(
    script: dict,
    *,
    fps: int = 24,
    spines: dict | None = None,
    routes: dict | None = None,
    era: str | None = None,
    directions: dict[str, dict] | None = None,
) -> str:
    """Return the deterministic dependency fingerprint for a provisional or authoritative ``sound_plan.json``."""
    dir_fps = {}
    for sid, ddoc in sorted((directions or {}).items()):
        if isinstance(ddoc, dict):
            dir_fps[sid] = ddoc.get("dependency_fingerprint") or sha256_obj(
                {"tracks": ddoc.get("tracks"), "sound": ddoc.get("sound"), "picture_sha256": ddoc.get("picture_sha256")}
            )
    payload = {
        "schema": "sound_plan_fp/1.0",
        "episode_id": script.get("episode_id"),
        "era": era or script.get("historical_period"),
        "fps": int(fps),
        "shots": [shot_script_slice(s, script) for s in (script.get("shots") or [])],
        "spines": spines or {},
        "routes": routes or {},
        "direction_fingerprints": dir_fps,
        "sound_code_digest": code_digest(SOUND_CODE_FILES),
    }
    return sha256_obj(payload)


def is_direction_fresh(
    doc: dict | None,
    *,
    shot: dict,
    script: dict | None = None,
    picture_sha256: str | None = None,
    manifest: dict | None = None,
    perception: dict | None = None,
    spine: list[dict] | None = None,
    fps: float = 24.0,
) -> bool:
    """Return True if ``doc`` carries a ``dependency_fingerprint`` matching the current upstream inputs."""
    if not isinstance(doc, dict) or not doc.get("dependency_fingerprint"):
        return False
    expected = direction_fingerprint(
        shot,
        script,
        picture_sha256=picture_sha256,
        manifest=manifest,
        perception=perception,
        spine=spine,
        fps=fps,
    )
    return doc.get("dependency_fingerprint") == expected
