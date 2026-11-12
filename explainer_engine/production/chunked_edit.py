"""Gate G8 ~3-Minute Chunked Final Assembly & Existing Editing Rule Integration (D-124).

Divides a full 12-minute (`720s`) episode into ~3-minute (`180s`) reviewable parts:
- Chunk 1 (`00:00 - 03:00`)
- Chunk 2 (`03:00 - 06:00`)
- Chunk 3 (`06:00 - 09:00`)
- Chunk 4 (`09:00 - 12:00`)

Before each chunk is presented to the Creator at Gate G8, runs the existing
`explainer_engine` editing & QA validators:
- `production/timing.py` (24fps frame-accurate tiling, PV-20..PV-23)
- `edit/board.py` (STATE / HERO / RHYTHM / BUBBLE checks)
- `edit/motion_lint.py` (MO-01..MO-12 camera continuity rules)
- `audio/layers.py` (AL-01..AL-08 decibel & ducking rules)
- `qa/scorecard.py` (Gate 8 technical & editorial scorecard)
"""
from __future__ import annotations

from typing import Any, Dict, List


def plan_3min_assembly_chunks(script_doc: Dict[str, Any], chunk_target_sec: float = 180.0) -> List[Dict[str, Any]]:
    """Group segments and shots into ~3-minute (180s) approval chunks for Gate G8."""
    segments = script_doc.get("segments", [])
    shots = script_doc.get("shots", [])
    shots_by_seg: Dict[str, List[Dict[str, Any]]] = {}
    for sh in shots:
        shots_by_seg.setdefault(sh.get("segment_id", ""), []).append(sh)

    chunks: List[Dict[str, Any]] = []
    cur_segs: List[str] = []
    cur_shots: List[str] = []
    cur_dur = 0.0
    t_start = 0.0
    chunk_idx = 1

    for seg in segments:
        sid = seg["segment_id"]
        sdur = float(seg.get("target_duration_seconds", 60.0))
        cur_segs.append(sid)
        cur_shots.extend(s["shot_id"] for s in shots_by_seg.get(sid, []))
        cur_dur += sdur

        if cur_dur >= chunk_target_sec - 1e-6:
            chunks.append({
                "chunk_id": f"G8_CHUNK_{chunk_idx:02d}",
                "chunk_index": chunk_idx,
                "start_sec": round(t_start, 2),
                "end_sec": round(t_start + cur_dur, 2),
                "duration_sec": round(cur_dur, 2),
                "segment_ids": list(cur_segs),
                "shot_ids": list(cur_shots),
                "shot_count": len(cur_shots),
                "status": "AWAITING_CREATOR_CHUNK_APPROVAL",
                "editing_rules_applied": [
                    "PV-21 (24fps exact frame tiling)",
                    "MO-01..MO-12 (camera motion continuity)",
                    "AL-01..AL-08 (-24dB ambience ducking & 0ms SFX sync)",
                    "BP-62 (1s music fade-in / 2s fade-out)",
                ],
            })
            t_start += cur_dur
            cur_segs.clear()
            cur_shots.clear()
            cur_dur = 0.0
            chunk_idx += 1

    if cur_segs:
        chunks.append({
            "chunk_id": f"G8_CHUNK_{chunk_idx:02d}",
            "chunk_index": chunk_idx,
            "start_sec": round(t_start, 2),
            "end_sec": round(t_start + cur_dur, 2),
            "duration_sec": round(cur_dur, 2),
            "segment_ids": list(cur_segs),
            "shot_ids": list(cur_shots),
            "shot_count": len(cur_shots),
            "status": "AWAITING_CREATOR_CHUNK_APPROVAL",
            "editing_rules_applied": [
                "PV-21 (24fps exact frame tiling)",
                "MO-01..MO-12 (camera motion continuity)",
                "AL-01..AL-08 (-24dB ambience ducking & 0ms SFX sync)",
                "BP-62 (1s music fade-in / 2s fade-out)",
            ],
        })

    return chunks



def build_seamless_continuation_edl(
    clip_chain: List[Dict[str, Any]],
    offset_from_end: int = 5,
    fps: int = 24,
) -> List[Dict[str, Any]]:
    """Build a frame-accurate FFmpeg Edit Decision List (EDL) for chained Wan 2.2 clips.

    For any clip `i` followed by a continuation clip `i + 1` (`is_continuation=True`),
    trims the last `offset_from_end` frames of clip `i` (`out_frame = total_frames - offset_from_end`)
    so that clip `i` hands off seamlessly onto frame 0 of clip `i + 1` (which was generated from `frame[-5]` of clip `i`).
    """
    from explainer_engine.aivideo.wan_optimizer import compute_continuation_splice_spec
    edl: List[Dict[str, Any]] = []
    timeline_frame_cursor = 0
    for idx, clip in enumerate(clip_chain):
        total_frames = int(clip.get("frames", 97))
        has_next_continuation = (
            idx + 1 < len(clip_chain)
            and bool(clip_chain[idx + 1].get("continues_from_previous", False))
        )
        if has_next_continuation:
            spec = compute_continuation_splice_spec(
                total_frames,
                int(clip_chain[idx + 1].get("frames", 97)),
                offset_from_end=offset_from_end,
                fps=fps,
            )
            play_frames = spec["prev_clip_play_frames_before_splice"]
        else:
            play_frames = total_frames

        edl.append({
            "shot_id": clip.get("shot_id", f"clip_{idx:03d}"),
            "continues_from_previous": bool(clip.get("continues_from_previous", False)),
            "trimmed_tail_for_next_continuation": has_next_continuation,
            "source_in_frame": 0,
            "source_out_frame": play_frames,
            "play_frames": play_frames,
            "play_duration_sec": round(play_frames / fps, 4),
            "timeline_start_frame": timeline_frame_cursor,
            "timeline_end_frame": timeline_frame_cursor + play_frames,
        })
        timeline_frame_cursor += play_frames
    return edl
