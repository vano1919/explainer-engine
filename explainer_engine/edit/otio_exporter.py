"""OpenTimelineIO (.otio) Free NLE Exporter with 4 Separate Audio Stems & J/L-Cut Support.

Generates standards-compliant OpenTimelineIO ``Timeline.1`` JSON files directly from Python with
ZERO paid NLE dependencies — opens cleanly in **free DaVinci Resolve** and **Kdenlive** so the
creator can inspect or tweak cuts, dialogue J/L-cuts, Foley, and music stems anytime.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _rational_time(value_frames: int, rate: float) -> dict[str, Any]:
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": float(value_frames)}


def _time_range(start_frames: int, duration_frames: int, rate: float) -> dict[str, Any]:
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": _rational_time(start_frames, rate),
        "duration": _rational_time(duration_frames, rate),
    }


def _external_ref(media_path: str | Path, duration_frames: int, rate: float) -> dict[str, Any]:
    p = Path(media_path)
    return {
        "OTIO_SCHEMA": "ExternalReference.1",
        "available_range": _time_range(0, max(1, duration_frames), rate),
        "metadata": {},
        "name": p.name,
        "target_url": p.resolve().as_uri() if p.exists() else str(media_path),
    }


def _clip_item(
    *,
    name: str,
    media_path: str | Path,
    source_start_s: float,
    duration_s: float,
    fps: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    st_f = max(0, int(round(source_start_s * fps)))
    dur_f = max(1, int(round(duration_s * fps)))
    return {
        "OTIO_SCHEMA": "Clip.2",
        "effects": [],
        "enabled": True,
        "markers": [],
        "media_references": {
            "DEFAULT_MEDIA": _external_ref(media_path, st_f + dur_f, fps),
        },
        "active_media_reference_key": "DEFAULT_MEDIA",
        "metadata": dict(metadata or {}),
        "name": name,
        "source_range": _time_range(st_f, dur_f, fps),
    }


def _gap_item(duration_s: float, fps: float) -> dict[str, Any]:
    dur_f = max(1, int(round(duration_s * fps)))
    return {
        "OTIO_SCHEMA": "Gap.1",
        "effects": [],
        "enabled": True,
        "markers": [],
        "metadata": {},
        "name": "",
        "source_range": _time_range(0, dur_f, fps),
    }


def _build_audio_track(
    name: str,
    events: list[dict[str, Any]],
    *,
    fps: float,
) -> dict[str, Any]:
    children: list[dict[str, Any]] = []
    cursor_s = 0.0
    for ev in sorted(events, key=lambda e: float(e.get("start_s", 0.0))):
        st = max(0.0, float(ev.get("start_s", cursor_s)))
        dur = max(0.05, float(ev.get("duration_s", 1.0)))
        j_pre = max(0.0, float(ev.get("j_cut_prelap_s", 0.0)))
        l_post = max(0.0, float(ev.get("l_cut_postlap_s", 0.0)))
        eff_start = max(0.0, st - j_pre)
        eff_dur = dur + j_pre + l_post
        if eff_start > cursor_s + (0.5 / fps):
            children.append(_gap_item(eff_start - cursor_s, fps))
        children.append(
            _clip_item(
                name=str(ev.get("name") or ev.get("shot_id") or name),
                media_path=ev.get("audio_path") or ev.get("path") or "",
                source_start_s=float(ev.get("source_start_s", 0.0)),
                duration_s=eff_dur,
                fps=fps,
                metadata={
                    "j_cut_prelap_s": j_pre,
                    "l_cut_postlap_s": l_post,
                    "gain_db": float(ev.get("gain_db", 0.0)),
                },
            )
        )
        cursor_s = max(cursor_s, eff_start + eff_dur)
    return {
        "OTIO_SCHEMA": "Track.1",
        "children": children,
        "effects": [],
        "enabled": True,
        "kind": "Audio",
        "markers": [],
        "metadata": {},
        "name": name,
        "source_range": None,
    }


def export_episode_otio(
    *,
    episode_name: str,
    video_shots: list[dict[str, Any]],
    out_otio: Path,
    dialogue_stems: list[dict[str, Any]] | None = None,
    narrator_stems: list[dict[str, Any]] | None = None,
    foley_stems: list[dict[str, Any]] | None = None,
    music_stems: list[dict[str, Any]] | None = None,
    fps: float = 24.0,
    aspect_ratio: str = "16:9",
) -> Path:
    """Write a complete ``.otio`` timeline with V1 video + 4 isolated audio tracks (free Resolve/Kdenlive ready)."""
    v_children = [
        _clip_item(
            name=str(sh.get("shot_id") or f"shot_{i + 1:02d}"),
            media_path=sh.get("video_path") or sh.get("clip_path") or "",
            source_start_s=float(sh.get("trim_start_s", 0.0)),
            duration_s=max(0.1, float(sh.get("duration_s", 5.0))),
            fps=fps,
            metadata={
                "route": str(sh.get("video_engine") or sh.get("route") or "ltx_2_5"),
                "lipsync_engine": sh.get("lipsync_engine"),
                "scene_id": str(sh.get("scene_id") or "S01"),
            },
        )
        for i, sh in enumerate(video_shots)
    ]

    timeline = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": episode_name,
        "global_start_time": _rational_time(0, fps),
        "metadata": {
            "aspect_ratio": aspect_ratio,
            "fps": fps,
            "c2pa_ai_disclosure": True,
            "nvenc_av1_safe_export": {
                "preset": "High Quality",
                "keyframe_interval_frames": 1,
                "look_ahead": False,
                "aq_strength": 0,
            },
        },
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "enabled": True,
            "effects": [],
            "markers": [],
            "metadata": {},
            "source_range": None,
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "V1_Master",
                    "kind": "Video",
                    "enabled": True,
                    "effects": [],
                    "markers": [],
                    "metadata": {},
                    "source_range": None,
                    "children": v_children,
                },
                _build_audio_track("A1_Dialogue", dialogue_stems or [], fps=fps),
                _build_audio_track("A2_Narrator", narrator_stems or [], fps=fps),
                _build_audio_track("A3_Foley_SFX", foley_stems or [], fps=fps),
                _build_audio_track("A4_Music_Score", music_stems or [], fps=fps),
            ],
        },
    }

    out_otio = Path(out_otio)
    out_otio.parent.mkdir(parents=True, exist_ok=True)
    out_otio.write_text(json.dumps(timeline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_otio


__all__ = ["export_episode_otio"]
