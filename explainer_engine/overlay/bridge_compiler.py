"""Compile validated docudrama visual bridges into ``overlay_spec/2`` and composite via PIL + FFmpeg.

Note on rendering engine:
- Active local renderer is deterministic PIL RGBA card rendering + FFmpeg ``overlay`` filter compositing.
- Approved TrueType typography (``assets/fonts/LiberationSerif-Regular.ttf`` or explicit ``font_path``)
  is strictly verified on disk with SHA-256 tracking; silent fallback to PIL's bitmap default font is
  prohibited.
"""
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
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_approved_font_path(font_path: Path | str | None = None) -> tuple[Path, str]:
    """Resolve and verify an approved TrueType font on disk; never silently fall back to PIL default."""
    if font_path is not None:
        p = Path(font_path)
        if not p.is_file():
            raise ContractError(f"Configured bridge font not found on disk: {p}")
        return p, _sha256(p)
    for cand in DEFAULT_SERIF_FONT_CANDIDATES:
        if cand.is_file():
            return cand, _sha256(cand)
    raise ContractError(
        "No approved Liberation Serif TrueType font found on disk; silent fallback to PIL default font is prohibited"
    )


def _load_verified_font(size: int, font_path: Path | str | None = None) -> tuple[ImageFont.FreeTypeFont, Path, str]:
    resolved, digest = resolve_approved_font_path(font_path)
    try:
        font = ImageFont.truetype(str(resolved), size=size)
    except OSError as exc:
        raise ContractError(f"Failed to load approved font {resolved}: {exc}") from exc
    return font, resolved, digest


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
    font_path: Path | str | None = None,
    episode_duration_s: float | None = None,
) -> dict[str, Any]:
    """Compile docudrama visual bridges into a deterministic ``overlay_spec/2`` manifest for PIL + FFmpeg."""
    if fps <= 0:
        raise ContractError(f"fps must be positive, got {fps!r}")
    if size[0] <= 0 or size[1] <= 0:
        raise ContractError(f"size dimensions must be positive, got {size!r}")

    resolved_font, font_sha = resolve_approved_font_path(font_path)

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
        if start_s < 0 or dur_s <= 0:
            raise ContractError(f"Bridge {idx} has invalid timing: start_s={start_s}, duration_s={dur_s}")
        end_s = round(start_s + dur_s, 3)
        if episode_duration_s is not None and start_s >= episode_duration_s:
            raise ContractError(
                f"Bridge {idx} starts at {start_s}s beyond episode_duration_s={episode_duration_s}s"
            )
        items.append(
            {
                "id": str(b.get("id") or f"bridge_{idx + 1:02d}"),
                "kind": kind,
                "text": str(b.get("text") or kind.replace("_", " ").title()),
                "subtext": str(b.get("subtext") or ""),
                "start_s": round(start_s, 3),
                "end_s": end_s,
                "start_frame": int(round(start_s * fps)),
                "end_frame": int(round(end_s * fps)),
                "accent_hex": accent,
                "bg_hex": palette[0],
                "typography": typography,
            }
        )

    return {
        "schema": "overlay_spec/2",
        "renderer": "pil_ffmpeg_overlay",
        "fps": fps,
        "width": size[0],
        "height": size[1],
        "typography": typography,
        "font_path": str(resolved_font),
        "font_sha256": font_sha,
        "palette_hex": list(palette),
        "items": items,
    }


def render_bridge_overlay_png(
    item: dict[str, Any],
    out_png: Path,
    *,
    size: tuple[int, int] = (1280, 720),
    font_path: Path | str | None = None,
) -> Path:
    """Render a transparent RGBA PNG card for one visual bridge using verified TrueType typography."""
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

    title_font, _, _ = _load_verified_font(max(22, int(h * 0.038)), font_path=font_path)
    sub_font, _, _ = _load_verified_font(max(16, int(h * 0.024)), font_path=font_path)
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

    font_path, font_sha = resolve_approved_font_path(overlay_spec.get("font_path"))
    size = (int(overlay_spec.get("width", 1280)), int(overlay_spec.get("height", 720)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(base_video)]
    pngs: list[Path] = []
    png_hashes: dict[str, str] = {}
    for idx, item in enumerate(items):
        p = render_bridge_overlay_png(item, work_dir / f"bridge_{idx:02d}.png", size=size, font_path=font_path)
        pngs.append(p)
        png_hashes[str(p)] = _sha256(p)
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
    digest = _sha256(out_video)
    return {
        "renderer": "pil_ffmpeg_overlay",
        "output_video": str(out_video),
        "sha256": digest,
        "font_path": str(font_path),
        "font_sha256": font_sha,
        "bridges_composited": len(items),
        "pngs": [str(p) for p in pngs],
        "png_hashes": png_hashes,
    }
