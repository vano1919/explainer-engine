"""Archival helper lane (B-P1c): document, letter, newspaper, telegram renderer with validated source-asset contract.

Plugs into G7 with the same clip-record / gate contract as ``map_clip.render_action_map_clip`` so G9 assembles it identically.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import ContractError

ARCHIVAL_SUBTYPES = ("document", "letter", "newspaper", "telegram")


def validate_archival_asset(shot: dict[str, Any]) -> dict[str, Any]:
    """Validate an archival helper shot's source-asset contract and provenance."""
    asset = dict(shot.get("archival_asset") or {})
    subtype = str(asset.get("subtype") or shot.get("helper_subtype") or "").strip().lower()
    if subtype not in ARCHIVAL_SUBTYPES:
        raise ContractError(f"{shot.get('shot_id', '?')}: archival helper subtype {subtype!r} not in {ARCHIVAL_SUBTYPES}")

    text = str(asset.get("text") or asset.get("body") or shot.get("narrative_purpose") or "").strip()
    if not text:
        raise ContractError(f"{shot.get('shot_id', '?')}: archival helper requires non-empty text/body")

    provenance = str(asset.get("provenance") or asset.get("source") or "").strip()
    authentic = bool(asset.get("authentic", True))
    if authentic and not provenance:
        raise ContractError(
            f"{shot.get('shot_id', '?')}: archival helper marked authentic requires explicit historical provenance/source "
            "(no fabricated historical text presented as authentic)"
        )

    date_str = str(asset.get("date") or "").strip()
    title = str(asset.get("title") or asset.get("headline") or "").strip()
    return {
        "schema": "archival_asset/1",
        "subtype": subtype,
        "title": title,
        "text": text,
        "date": date_str,
        "provenance": provenance,
        "authentic": authentic,
    }


def render_archival_helper_clip(
    shot: dict[str, Any],
    script: dict[str, Any],
    manifest: dict[str, Any],
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    keyframes_out_dir: Path | None = None,
) -> dict[str, Any]:
    """Render an archival document/letter/newspaper/telegram clip with the same contract as ``render_action_map_clip``."""
    from PIL import Image, ImageDraw, ImageFont

    asset = validate_archival_asset(shot)
    sid = str(shot.get("shot_id") or "archival")
    dur = max(0.5, float(shot.get("target_duration_seconds") or 4.0))
    frames = max(1, int(round(dur * fps)))

    # Paper palette by subtype
    palettes = {
        "document": ((236, 228, 208), (34, 30, 26)),
        "letter": ((242, 234, 214), (42, 32, 24)),
        "newspaper": ((225, 222, 212), (25, 25, 25)),
        "telegram": ((234, 224, 185), (30, 34, 42)),
    }
    bg, fg = palettes[asset["subtype"]]
    im = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(im)
    margin_x = int(width * 0.12)
    margin_y = int(height * 0.12)
    draw.rectangle((margin_x - 24, margin_y - 24, width - margin_x + 24, height - margin_y + 24), outline=fg, width=3)

    font = ImageFont.load_default()
    y = margin_y + 20
    header = f"[{asset['subtype'].upper()}] {asset['title']}  {asset['date']}".strip()
    draw.text((margin_x, y), header, fill=fg, font=font)
    y += 40
    for line in asset["text"].splitlines()[:18]:
        draw.text((margin_x, y), line[:110], fill=fg, font=font)
        y += 28
    if asset["provenance"]:
        draw.text((margin_x, height - margin_y - 24), f"Source: {asset['provenance']}", fill=fg, font=font)

    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    kf_dir = Path(keyframes_out_dir) if keyframes_out_dir else out_mp4.parent
    kf_dir.mkdir(parents=True, exist_ok=True)
    kf_start = kf_dir / f"{sid}_start.png"
    im.save(kf_start)

    raw_bytes = im.tobytes()
    tmp = out_mp4.with_name(out_mp4.stem + ".part.mp4")
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
         "-r", str(fps), "-i", "-", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium",
         "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)],
        stdin=subprocess.PIPE,
    )
    try:
        for _ in range(frames):
            proc.stdin.write(raw_bytes)
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on archival helper {sid}")
    tmp.replace(out_mp4)

    return {
        "provider": f"archival_helper:{asset['subtype']}",
        "shot_id": sid,
        "path": str(out_mp4),
        "frames": frames,
        "fps": fps,
        "resolution": [width, height],
        "start_keyframe_path": str(kf_start),
        "end_keyframe_path": str(kf_start),
        "output_sha256": hashlib.sha256(out_mp4.read_bytes()).hexdigest(),
        "gates": {
            "status": "PASS",
            "rows": [{"gate": "archival_provenance", "status": "PASS", "detail": f"{asset['subtype']}: {asset['provenance']}"}],
        },
        "asset": asset,
    }
