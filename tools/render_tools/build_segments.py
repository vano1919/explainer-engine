"""Assembler Step 1 (Upgraded for P0-1, P1-3, P1-5, P1-9):
- Consumes ONE persisted authoritative film clock (timing.json with timing_id & render_epoch) and ONE trim contract (videolane/ingest.py clip_path).
- Input-hash segment cache key (<sid>.seg.json) invalidating stale <sid>.mp4 whenever script, timing, source media, edit points, or render_epoch change.
- Split-clip fallback continuity guard before concatenating legacy [a-z].mp4 sub-clips.
- Single overlay authority (never draws epilogue/on_screen_text a second time when already composited in 2.5D plate).
- Single final resize guard (never upscales/resizes a clip twice).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.episode import timing as ET
from explainer_engine.production import continuity as CONT

DIPS = {
    "S01_SH005", "S02_SH009", "S03_SH010", "S04_SH015",
    "S05_SH021", "S06_SH012", "S07_SH008", "S08_SH003", "S08_SH004",
}
FPS = 24
TARGET_SIZE = (2560, 1440)


def _default_paths() -> tuple[Path, Path, Path]:
    r = Path(os.environ.get("TRUCE_EPISODE_DIR", "/Users/vano_tatulashvili/Documents/explainer-engine-truce/episodes/ep_truce_1914"))
    w = Path(os.environ.get("TRUCE_WORK_DIR", "/Users/vano_tatulashvili/Documents/hf_truce/work"))
    t_path = Path(os.environ.get("TRUCE_TIMING_JSON", "/Users/vano_tatulashvili/Documents/hf_truce/dl/explainer-engine/demo_truce_1914/full_film_2026-11-15/inputs/clock/timing.json"))
    return r, w, t_path


def run(*a):
    subprocess.run(a, check=True, capture_output=True)


def dur(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out or 0.0)


def probe_dimensions(p: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(p)],
        capture_output=True, text=True,
    ).stdout.strip()
    if "x" in out:
        parts = out.splitlines()[0].split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    return 0, 0


def _file_sha256(p: Path | None) -> str:
    if p is None or not Path(p).is_file():
        return "missing"
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def compute_segment_cache_key(
    sid: str,
    shot_spec: dict,
    timing_shot: dict,
    *,
    timing_id: str,
    render_epoch: str,
    edit_entry: dict | None = None,
    source_sha256: str = "",
    overlay_authority: str = "plate",
) -> str:
    """Compute a deterministic cache key from all inputs that govern <sid>.mp4."""
    payload = {
        "shot_id": sid,
        "route": shot_spec.get("route"),
        "on_screen_text": shot_spec.get("on_screen_text"),
        "visual_bridge": shot_spec.get("visual_bridge"),
        "frames": int(timing_shot.get("frames", 0)),
        "start_frame": int(timing_shot.get("start_frame", 0)),
        "end_frame": int(timing_shot.get("end_frame", 0)),
        "timing_id": str(timing_id or ""),
        "render_epoch": str(render_epoch or ""),
        "edit_entry": edit_entry or {},
        "source_sha256": str(source_sha256 or ""),
        "overlay_authority": str(overlay_authority or "plate"),
        "dip_to_black": sid in DIPS,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_segment_cache_valid(out_mp4: Path, expected_key: str) -> bool:
    """Return True only when <sid>.mp4 AND <sid>.seg.json exist and match expected_key and output_sha256."""
    out_mp4 = Path(out_mp4)
    meta_path = out_mp4.with_suffix(".seg.json")
    if not out_mp4.is_file() or not meta_path.is_file():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if meta.get("cache_key") != expected_key:
        return False
    if meta.get("output_sha256") != _file_sha256(out_mp4):
        return False
    return True


def should_apply_segment_overlay(
    shot_spec: dict,
    route: str,
    *,
    overlay_authority: str = "plate",
) -> bool:
    """P1-5 Single Overlay Authority: still_25d/directed25d renders overlays inside the plate via visual_bridge;
    build_segments must NEVER draw on_screen_text a second time unless overlay_authority=='segment' and plate did not render it."""
    ost = shot_spec.get("on_screen_text")
    has_text = (isinstance(ost, str) and bool(ost.strip())) or (isinstance(ost, list) and len(ost) > 0)
    if not has_text:
        return False
    if shot_spec.get("overlay_rendered_in_plate", route in ("still_25d", "still", "directed25d")):
        return False
    return overlay_authority == "segment"


def synchronize_episode_clock(
    episode_dir: Path,
    timing_path: Path,
    *,
    edit_points_path: Path | None = None,
    script_path: Path | None = None,
    out_timing_path: Path | None = None,
) -> dict:
    """Retime and persist the single authoritative film clock before building segments or mixing audio."""
    episode_dir = Path(episode_dir)
    timing_doc = json.loads(Path(timing_path).read_text(encoding="utf-8"))
    script_p = Path(script_path) if script_path else (episode_dir / "story" / "production_script.json")
    script_doc = json.loads(script_p.read_text(encoding="utf-8")) if script_p.is_file() else {}
    ep_p = Path(edit_points_path) if edit_points_path else (episode_dir / "planning" / "full_film_2026-11-15" / "edit_points.json")
    ep_doc = json.loads(ep_p.read_text(encoding="utf-8")) if ep_p.is_file() else {}
    retimed = ET.retime_with_edit_points(timing_doc, script_doc, ep_doc)
    dest = Path(out_timing_path) if out_timing_path else Path(timing_path)
    return ET.persist_authoritative_clock(retimed, dest)


def resolve_video_source(episode_dir: Path, rec: dict, *, allow_raw_fallback: bool = False) -> tuple[Path, float, bool]:
    """P0-1 Single Trim Contract: consume the already-trimmed clip from videolane/ingest.py (clip_path, ss=0.0)
    instead of re-trimming raw_path a second time."""
    episode_dir = Path(episode_dir)
    clip_rel = rec.get("clip_path") or (rec.get("trim_contract") or {}).get("clip_path")
    if clip_rel:
        clip_p = episode_dir / clip_rel
        if clip_p.is_file():
            return clip_p, 0.0, True
    if allow_raw_fallback and rec.get("raw_path"):
        raw_p = episode_dir / rec["raw_path"]
        return raw_p, float(rec.get("in_s", 0.0)), False
    raise ContractError(
        f"{rec.get('shot_id', 'unknown')}: single trim contract requires ingested clip_path ({clip_rel!r}) to exist; "
        "refusing to re-trim raw_path a second time"
    )


def build(
    sid: str,
    *,
    episode_dir: Path | None = None,
    work_dir: Path | None = None,
    timing_doc: dict | None = None,
    timing_path: Path | None = None,
    edit_points: dict | None = None,
    script_shots: dict | None = None,
    overlay_authority: str = "plate",
) -> tuple[str, str]:
    r_dir, w_dir, t_path = _default_paths()
    R = Path(episode_dir) if episode_dir is not None else r_dir
    W = Path(work_dir) if work_dir is not None else w_dir
    (W / "seg").mkdir(parents=True, exist_ok=True)
    T_PATH = Path(timing_path) if timing_path is not None else t_path

    if timing_doc is None:
        timing_doc = synchronize_episode_clock(R, T_PATH)
    elif "timing_id" not in timing_doc:
        timing_doc = ET.retime_with_edit_points(timing_doc, {"shots": list((script_shots or {}).values())}, edit_points or {})

    if script_shots is None:
        sc_doc = json.loads((R / "story" / "production_script.json").read_text(encoding="utf-8"))
        script_shots = {s["shot_id"]: s for s in sc_doc.get("shots", [])}
    if edit_points is None:
        ep_file = R / "planning" / "full_film_2026-11-15" / "edit_points.json"
        edit_points = json.loads(ep_file.read_text(encoding="utf-8")).get("clips", {}) if ep_file.is_file() else {}

    sh = script_shots[sid]
    route = sh["route"]
    t_shot = timing_doc["shots"][sid]
    n = int(t_shot["frames"])
    timing_id = timing_doc.get("timing_id") or ET.compute_timing_id(timing_doc)
    render_epoch = timing_doc.get("render_epoch") or f"epoch_{timing_id}"
    e = edit_points.get(sid, {}) if isinstance(edit_points.get(sid), dict) else {}

    src: Path | None = None
    ss = 0.0
    already_upscaled = False
    if route == "video":
        rec = json.loads((R / "production" / "video" / f"{sid}.json").read_text(encoding="utf-8"))
        src, ss, _is_trimmed = resolve_video_source(R, rec, allow_raw_fallback=False)
        already_upscaled = bool(rec.get("upscaled_to_target") or rec.get("upscaled_once"))
        src_sha = rec.get("clip_sha256") or _file_sha256(src)
    else:
        full_clip = R / f"production/shot_clips/{sid}.mp4"
        if full_clip.is_file():
            src = full_clip
            src_sha = _file_sha256(src)
        else:
            parts = sorted(Path(p) for p in glob.glob(str(R / f"production/shot_clips/{sid}[a-z].mp4")))
            if not parts:
                raise ContractError(f"{sid}: neither continuous {full_clip} nor split sub-clips exist")
            check = CONT.verify_split_clip_continuity(parts, shot_spec=sh)
            if check["status"] == "FAIL":
                raise ContractError(f"{sid}: split sub-clip fallback failed continuity verification: {check['findings']}")
            lst = W / f"{sid}.concat.txt"
            lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
            cat = W / f"{sid}.cat.mp4"
            run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(cat))
            src = cat
            src_sha = _file_sha256(src)

    out = W / "seg" / f"{sid}.mp4"
    cache_key = compute_segment_cache_key(
        sid, sh, t_shot,
        timing_id=timing_id,
        render_epoch=render_epoch,
        edit_entry=e,
        source_sha256=src_sha,
        overlay_authority=overlay_authority,
    )
    if is_segment_cache_valid(out, cache_key):
        return sid, "cached"

    raw_d = dur(src)
    avail_frames = max(1, int(round((raw_d - ss) * FPS)))
    pad = max(0, n - avail_frames)
    if route == "video":
        vf = f"fps={FPS}" + (f",tpad=stop_mode=clone:stop={pad},tmix=frames=3:weights='1 2 1'" if pad > 0 else "")
    else:
        vf = f"fps={FPS}" + (f",tpad=stop_mode=clone:stop={pad}" if pad > 0 else "")

    w0, h0 = probe_dimensions(src)
    resize_applied = False
    if (w0, h0) != TARGET_SIZE:
        if already_upscaled:
            raise ContractError(f"{sid}: source clip was already upscaled once ({w0}x{h0}); refusing double resize+encode (P1-9)")
        vf += f",scale={TARGET_SIZE[0]}:{TARGET_SIZE[1]}:flags=lanczos"
        resize_applied = True
    vf += ",setsar=1,format=yuv420p"

    overlay_drawn = False
    if should_apply_segment_overlay(sh, route, overlay_authority=overlay_authority):
        ost = sh.get("on_screen_text")
        txt = ost if isinstance(ost, str) else (ost[0].get("text", "") if isinstance(ost, list) and ost else "")
        if txt.strip():
            safe_txt = txt.strip().replace(":", "\\:").replace("'", "\\'")
            vf += (
                f",drawtext=text='{safe_txt}':fontsize=58:fontcolor=0xFCF6E8:"
                "box=1:boxcolor=0x0E0D0C@0.62:boxborderw=24:x=(w-text_w)/2:y=(h-text_h)/2"
            )
            overlay_drawn = True

    if sid in DIPS:
        vf += f",fade=t=out:st={max(0.0, (n - 10) / FPS):.3f}:d={10 / FPS:.3f}"

    run(
        "ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.4f}", "-i", str(src),
        "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(out),
    )
    seg_meta = {
        "schema": "segment_build_record/1",
        "shot_id": sid,
        "route": route,
        "cache_key": cache_key,
        "timing_id": timing_id,
        "render_epoch": render_epoch,
        "frames": n,
        "start_frame": int(t_shot.get("start_frame", 0)),
        "end_frame": int(t_shot.get("end_frame", n)),
        "source_path": str(src),
        "source_sha256": src_sha,
        "output_sha256": _file_sha256(out),
        "single_trimmed_source": route == "video",
        "resize_applied": resize_applied,
        "overlay_drawn_in_segment": overlay_drawn,
    }
    write_json_atomic(out.with_suffix(".seg.json"), seg_meta)
    return sid, "ok"


if __name__ == "__main__":
    r_dir, _w_dir, t_path = _default_paths()
    sync_doc = synchronize_episode_clock(r_dir, t_path)
    for sid_arg in sys.argv[1:]:
        print(*build(sid_arg, timing_doc=sync_doc), flush=True)
