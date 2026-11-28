"""3x3 Cinematic Contact Sheet Slicer (16-bit PNG / High-Bit-Depth Panel Extractor).

Implements the standard indie AI filmmaking workflow from the November 2026 research:
- Takes ONE approved 3x3 Cinematic Contact Sheet (generated in a single latent pass via
  Nano Banana Pro / GPT Image 2 / FLUX.2 / Qwen-Image-Edit so lighting, wardrobe, and color
  palette stay unified across all 9 angles).
- Slices it cleanly into 9 individual border-trimmed panels mapped to canonical cinema roles:
  Row 1: ``01_wide_establish``, ``02_full_body``, ``03_three_quarter``
  Row 2: ``04_medium_waist``, ``05_medium_chest``, ``06_closeup_frontal``
  Row 3: ``07_profile``, ``08_over_the_shoulder``, ``09_detail_insert``
- Writes a SHA-256 verified ``contact_sheet_3x3_manifest.json`` and saves clean 16-bit PNGs
  (using OpenCV ``uint16`` scaling) ready for I2V / First-Last-Frame video generation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CANONICAL_3X3_ROLES: tuple[str, ...] = (
    "01_wide_establish",
    "02_full_body",
    "03_three_quarter",
    "04_medium_waist",
    "05_medium_chest",
    "06_closeup_frontal",
    "07_profile",
    "08_over_the_shoulder",
    "09_detail_insert",
)


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _trim_gutter(panel: np.ndarray, *, max_trim_px: int = 12) -> np.ndarray:
    """Trim uniform black/white divider gutters from the edges of a sliced 3x3 panel."""
    h, w = panel.shape[:2]
    gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY) if panel.ndim == 3 else panel

    def _is_gutter(line: np.ndarray) -> bool:
        return bool(float(np.std(line)) < 3.5 and (float(np.mean(line)) < 18.0 or float(np.mean(line)) > 238.0))

    top, bot, left, right = 0, h, 0, w
    while top < min(max_trim_px, h // 8) and _is_gutter(gray[top, :]):
        top += 1
    while (h - bot) < min(max_trim_px, h // 8) and bot > top + 16 and _is_gutter(gray[bot - 1, :]):
        bot -= 1
    while left < min(max_trim_px, w // 8) and _is_gutter(gray[:, left]):
        left += 1
    while (w - right) < min(max_trim_px, w // 8) and right > left + 16 and _is_gutter(gray[:, right - 1]):
        right -= 1
    return panel[top:bot, left:right]


def slice_contact_sheet_3x3(
    sheet_path: Path,
    out_dir: Path,
    *,
    prefix: str = "scene",
    target_width: int = 1280,
    target_height: int = 720,
    save_16bit_png: bool = True,
    min_panel_width: int = 384,
) -> dict[str, Any]:
    """Slice a 3x3 cinematic contact sheet into 9 named, border-trimmed, SHA-256 verified PNG panels."""
    sheet_path = Path(sheet_path)
    if not sheet_path.is_file():
        raise FileNotFoundError(f"3x3 contact sheet not found: {sheet_path}")

    img = cv2.imread(str(sheet_path), cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        raise RuntimeError(f"Could not decode contact sheet image: {sheet_path}")

    sh, sw = img.shape[:2]
    cell_w = sw // 3
    cell_h = sh // 3
    if cell_w < min_panel_width:
        raise ValueError(
            f"3x3 contact sheet cell width {cell_w}px < minimum {min_panel_width}px "
            f"(sheet is {sw}x{sh}; generate at >= {min_panel_width * 3}px wide so panels stay crisp)"
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []

    idx = 0
    for r in range(3):
        for c in range(3):
            role = CANONICAL_3X3_ROLES[idx]
            idx += 1
            y0 = r * cell_h
            y1 = (r + 1) * cell_h if r < 2 else sh
            x0 = c * cell_w
            x1 = (c + 1) * cell_w if c < 2 else sw
            raw_cell = img[y0:y1, x0:x1]
            clean = _trim_gutter(raw_cell)
            resized = cv2.resize(clean, (int(target_width), int(target_height)), interpolation=cv2.INTER_LANCZOS4)

            out_png = out_dir / f"{prefix}_{role}.png"
            if save_16bit_png:
                # Promote cleanly to 16-bit PNG for downstream ComfyUI SaveImageAdvanced / EXR grading
                img16 = (resized.astype(np.uint16) * 257)
                cv2.imwrite(str(out_png), img16)
            else:
                cv2.imwrite(str(out_png), resized)

            panels.append(
                {
                    "panel_index": idx,
                    "role": role,
                    "grid_rc": [r, c],
                    "path": str(out_png),
                    "width": int(target_width),
                    "height": int(target_height),
                    "bit_depth": 16 if save_16bit_png else 8,
                    "sha256": _sha256_path(out_png),
                }
            )

    manifest = {
        "schema": "contact_sheet_3x3_slice/1",
        "source_sheet": str(sheet_path),
        "source_sha256": _sha256_path(sheet_path),
        "source_size": [sw, sh],
        "panel_count": len(panels),
        "panels": panels,
    }
    manifest_path = out_dir / f"{prefix}_contact_sheet_3x3_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


__all__ = ["CANONICAL_3X3_ROLES", "slice_contact_sheet_3x3"]
