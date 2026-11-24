"""Compile validated docudrama visual bridges into HyperFrames overlay_spec/2 and local FFmpeg overlays."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from explainer_engine.core.errors import ContractError
from explainer_engine.scripting.docudrama_structure import VALID_VISUAL_BRIDGE_KINDS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERIF_FONT_CANDIDATES = (
    ROOT / "assets" / "fonts" / "LiberationSerif-Regular.ttf",
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
    ROOT / "assets" / "fonts" / "Inter.ttf",
)


def _find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in DEFAULT_SERIF_FONT_CANDIDATES:
        if p.is_file():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def _hex_to_rgba(hex_str: str, alpha: int = 230) -> tuple[int, int, int, int]:
    cleaned = hex_str.lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6:
        return (20, 26, 36, alpha)
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16), alpha)


def compile_bridges_to_overlay_spec(
    bridges: list[dict[str, Any]],
    *,
    style_bible: dict[str, Any] | None = None,
    fps: int = 24,
    size: tuple[int, int] = (1920, 1080),
) -> dict[str, Any]:
    """Compile docudrama visual bridges into an ``overlay_spec/2`` manifest for HyperFrames or FFmpeg."""
    vis = (style_bible or {}).get("visual_identity") or {}
    vb = (style_bible or {}).get("visual_bridges") or {}
    palette = vis.get("palette_hex") or ["#1B2228", "#6B5A45", "#C8A97E"]
    accent = vb.get("accent_hex") or palette[-1]
    typography = vb.get("typography") or "Liberation Serif"

    items: list[dict[str, Any]] = []
    for idx, b in enumerate(bridges):
        kind = str(b.get("kind", ""))
        if kind not in VALID_VISUAL_BRIDGE_KINDS:
            raise ContractError(f"Unsupported visual bridge kind: {kind!r}")
        start_s = float(b.get("timestamp_s", idx * 5.0))
        dur_s = float(b.get("duration_s", 3.0))
        items.append(
            {
                "id": str(b.get("id") or f"bridge_{idx + 1:02d}"),
                "kind": kind,
                "text": str(b.get("text") or kind.replace("_", " ").title()),
                "subtext": str(b.get("subtext") or ""),
                "start_s": round(start_s, 3),
                "end_s": round(start_s + dur_s, 3),
                "start_frame": int(round(start_s * fps)),
                "end_frame": int(round((start_s + dur_s) * fps)),
                "accent_hex": accent,
                "bg_hex": palette[0],
                "typography": typography,
            }
        )

    return {
        "schema": "overlay_spec/2",
        "fps": fps,
        "width": size[0],
        "height": size[1],
        "typography": typography,
        "palette_hex": list(palette),
        "items": items,
    }


def render_bridge_overlay_png(
    item: dict[str, Any],
    out_png: Path,
    *,
    size: tuple[int, int] = (1280, 720),
) -> Path:
    """Render a transparent RGBA PNG card for one visual bridge using Liberation Serif and film palette."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_rgba = _hex_to_rgba(str(item.get("bg_hex", "#1B2228")), alpha=220)
    acc_rgba = _hex_to_rgba(str(item.get("accent_hex", "#C8A97E")), alpha=255)

    margin_x = int(w * 0.05)
    box_h = int(h * 0.14)
    y0 = h - box_h - int(h * 0.07)
    x0 = margin_x
    x1 = min(w - margin_x, int(w * 0.56))
    y1 = y0 + box_h

    draw.rectangle([x0, y0, x1, y1], fill=bg_rgba)
    draw.rectangle([x0, y0, x0 + max(6, int(w * 0.005)), y1], fill=acc_rgba)

    title_font = _find_font(max(22, int(h * 0.038)))
    sub_font = _find_font(max(16, int(h * 0.024)))
    draw.text((x0 + 22, y0 + 16), str(item.get("text", "")), font=title_font, fill=(248, 250, 252, 255))
    sub = str(item.get("subtext", "")).strip()
    if sub:
        draw.text((x0 + 22, y0 + int(box_h * 0.55)), sub, font=sub_font, fill=acc_rgba)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, format="PNG")
    return out_png


def composite_bridges_onto_video(
    base_video: Path,
    overlay_spec: dict[str, Any],
    out_video: Path,
    *,
    work_dir: Path,
) -> dict[str, Any]:
    """Composite compiled visual bridges onto ``base_video`` via FFmpeg at exact measured timestamps."""
    if not base_video.is_file():
        raise ContractError(f"Base video not found: {base_video}")
    items = list(overlay_spec.get("items") or [])
    if not items:
        raise ContractError("overlay_spec contains zero bridge items to composite")

    size = (int(overlay_spec.get("width", 1280)), int(overlay_spec.get("height", 720)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(base_video)]
    pngs: list[Path] = []
    for idx, item in enumerate(items):
        p = render_bridge_overlay_png(item, work_dir / f"bridge_{idx:02d}.png", size=size)
        pngs.append(p)
        cmd += ["-i", str(p)]

    filters: list[str] = []
    prev_label = "[0:v]"
    for idx, item in enumerate(items):
        in_lbl = f"[{idx + 1}:v]"
        out_lbl = f"[v{idx + 1}]"
        s = float(item["start_s"])
        e = float(item["end_s"])
        filters.append(f"{prev_label}{in_lbl}overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'{out_lbl}")
        prev_label = out_lbl

    out_video.parent.mkdir(parents=True, exist_ok=True)
    cmd += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        prev_label,
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(out_video),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
    digest = hashlib.sha256(out_video.read_bytes()).hexdigest()
    return {"output_video": str(out_video), "sha256": digest, "bridges_composited": len(items), "pngs": [str(p) for p in pngs]}
