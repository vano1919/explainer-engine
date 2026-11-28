"""Boxless Filmic Editorial Graphics & Rough.js Hand-Drawn Overlays (Lossless PNG-RGBA MOV).

Retires monotonous dark frosted-glass PowerPoint/SaaS boxes in favor of prestige Vox / Johnny Harris /
Lemmino documentary motion design:
1. ``editorial_chapter_slate``: Boxless Cinzel + italic Cormorant Garamond typography with Rough.js ochre
   underline and soft feathered radial vignette scrim (zero card border or rectangle).
2. ``chalk_circle_callout``: Hand-drawn Rough.js double-pass chalk/ochre circle highlighting an on-screen
   subject + curved Rough.js arrow + boxless floating film typography.
3. ``handdrawn_stat_underline``: Massive tabular JetBrains Mono counter with live GSAP count-up, animated
   Rough.js hand-drawn brush underline, and italic documentary subtitle — zero box.
4. ``archival_margin_note``: Tactile vertical ochre ink hairline rule + monospace archival stamp + clean
   floating sans editorial note with subtle SVG ink-roughening turbulence filter.
5. ``rough_arrow_pointer``: Hand-drawn curved Rough.js chalk/ochre pointer arrow with floating 2-line caption.
6. ``kinetic_whisper_title``: SplitText cinematic mask reveal for punchy 2-4 word documentary beats.

Renders frame-accurately at 24fps to lossless PNG-RGBA MOV via Playwright Chromium + GSAP 3.13 + Rough.js.
"""
from __future__ import annotations

import base64
import html
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from explainer_engine.design_system.tokens import (
    PALEO_ICE_AGE_THEME,
    build_font_face_css,
    resolve_vendor_js,
)

VALID_EDITORIAL_TEMPLATES = frozenset(
    {
        "editorial_chapter_slate",
        "chalk_circle_callout",
        "handdrawn_stat_underline",
        "archival_margin_note",
        "rough_arrow_pointer",
        "kinetic_whisper_title",
    }
)


@dataclass(slots=True)
class EditorialGraphicSpec:
    graphic_id: str
    template: str
    title: str
    subtitle: str = ""
    start_s: float = 0.0
    duration_s: float = 3.8
    position: str = "bottom_left"  # bottom_left, top_left, bottom_center, center, bottom_right
    accent_color: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.template not in VALID_EDITORIAL_TEMPLATES:
            raise ValueError(
                f"Unsupported editorial graphic template {self.template!r}; "
                f"expected one of {sorted(VALID_EDITORIAL_TEMPLATES)}"
            )
        if self.duration_s < 1.0:
            raise ValueError(f"Editorial graphic duration_s must be >= 1.0s, got {self.duration_s}")
        if self.template == "handdrawn_stat_underline" and "end_val" in self.meta:
            end_v = float(self.meta["end_val"])
            prefix = str(self.meta.get("prefix", ""))
            suffix = str(self.meta.get("suffix", ""))
            rendered_stat = f"{prefix}{int(round(end_v)):,}{suffix}".strip().lower()
            compact_stat = rendered_stat.replace(" ", "").replace(",", "")
            compact_title = self.title.strip().lower().replace(" ", "").replace(",", "")
            if compact_title == compact_stat or (compact_stat and compact_title.startswith(compact_stat)):
                raise ValueError(
                    f"handdrawn_stat_underline title {self.title!r} duplicates counter value "
                    f"{rendered_stat!r}; use a descriptive label instead of repeating the number"
                )


def _yunet_detect_boxes(
    frame: Any,
    *,
    score_threshold: float = 0.55,
    yunet_model_path: Path | None = None,
) -> list[tuple[int, int, int, int]]:
    import cv2

    src_h, src_w = frame.shape[:2]
    raw_boxes: list[tuple[int, int, int, int]] = []
    repo_root = Path(__file__).resolve().parents[2]
    candidate_models = [
        yunet_model_path,
        repo_root / "assets" / "models" / "face_detection_yunet_2023mar.onnx",
        Path("assets/models/face_detection_yunet_2023mar.onnx"),
    ]
    model_file = next((m for m in candidate_models if m is not None and Path(m).is_file()), None)
    if model_file is not None and hasattr(cv2, "FaceDetectorYN"):
        det = cv2.FaceDetectorYN.create(
            str(model_file),
            "",
            (src_w, src_h),
            score_threshold=float(score_threshold),
            nms_threshold=0.3,
            top_k=50,
        )
        _, faces = det.detect(frame)
        if faces is not None:
            for row in faces:
                x, y, w, h = (
                    int(round(float(row[0]))),
                    int(round(float(row[1]))),
                    int(round(float(row[2]))),
                    int(round(float(row[3]))),
                )
                if w >= 24 and h >= 24:
                    raw_boxes.append((max(0, x), max(0, y), min(src_w, x + w), min(src_h, y + h)))

    if not raw_boxes and hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        min_dim = max(36, int(min(src_w, src_h) * 0.08))
        haar_dir = Path(cv2.data.haarcascades)  # type: ignore[attr-defined]
        for cname in ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml"):
            cpath = haar_dir / cname
            if not cpath.is_file():
                continue
            clf = cv2.CascadeClassifier(str(cpath))
            if clf.empty():
                continue
            for x, y, w, h in clf.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(min_dim, min_dim)):
                raw_boxes.append((int(x), int(y), int(x + w), int(y + h)))
    return raw_boxes


def detect_face_track(
    media_path: Path,
    *,
    max_duration_s: float | None = None,
    num_samples: int = 8,
    target_w: int = 1920,
    target_h: int = 1080,
    score_threshold: float = 0.50,
    yunet_model_path: Path | None = None,
) -> list[dict[str, float]]:
    """Track the primary subject's head silhouette across a video clip in 1920x1080 coordinates.

    Returns smooth per-timestamp ellipse keyframes ``[{"t_s", "cx", "cy", "rx", "ry"}, ...]``
    generously padded outside the detected face so highlight circles never cross eyes, nose, or mouth.
    """
    import cv2

    p = Path(media_path)
    if not p.is_file() or p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return []
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        return []
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur_s = total / max(1.0, fps)
    if max_duration_s is not None:
        dur_s = min(dur_s, float(max_duration_s))
    n = max(2, int(num_samples))
    sample_times = [dur_s * (i / float(n - 1)) for i in range(n)]
    track: list[dict[str, float]] = []
    try:
        for ts in sample_times:
            idx = max(0, min(max(0, total - 1), int(round(ts * fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, bgr = cap.read()
            if not ok or bgr is None or bgr.size == 0:
                continue
            src_h, src_w = bgr.shape[:2]
            boxes = _yunet_detect_boxes(bgr, score_threshold=score_threshold, yunet_model_path=yunet_model_path)
            if not boxes:
                continue
            # Track largest primary subject face
            bx0, by0, bx1, by1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            sx = target_w / float(src_w)
            sy = target_h / float(src_h)
            cx = ((bx0 + bx1) * 0.5) * sx
            cy = ((by0 + by1) * 0.485) * sy
            # Generous outer halo (0.86x width, 0.78x height radius) keeps stroke strictly outside hair, ears & chin
            rx = max(165.0, ((bx1 - bx0) * sx) * 0.86)
            ry = max(205.0, ((by1 - by0) * sy) * 0.78)
            track.append(
                {
                    "t_s": round(ts, 3),
                    "cx": round(cx, 1),
                    "cy": round(cy, 1),
                    "rx": round(rx, 1),
                    "ry": round(ry, 1),
                }
            )
    finally:
        cap.release()
    return track


def detect_face_avoid_zones(
    media_path: Path,
    *,
    sample_time_s: float = 0.5,
    pad_x_ratio: float = 0.40,
    pad_y_ratio: float = 0.48,
    target_w: int = 1920,
    target_h: int = 1080,
    score_threshold: float = 0.55,
    yunet_model_path: Path | None = None,
    multi_frame_union: bool = True,
) -> list[tuple[int, int, int, int]]:
    """Detect human faces on CPU (OpenCV YuNet ``FaceDetectorYN`` primary, legacy Haar fallback) in 1920x1080 space.

    For videos with ``multi_frame_union=True`` (default), samples across the full clip duration and returns
    the padded union bounding box covering the subject's entire head trajectory so moving actors are never occluded.
    """
    import cv2

    p = Path(media_path)
    if not p.is_file():
        return []

    frames: list[Any] = []
    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        im = cv2.imread(str(p))
        if im is not None and im.size > 0:
            frames.append(im)
    else:
        cap = cv2.VideoCapture(str(p))
        if cap.isOpened():
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if multi_frame_union and total >= 8:
                indices = sorted({int(round(i * (total - 1) / 6.0)) for i in range(7)})
            else:
                indices = [max(0, min(max(0, total - 1), int(round(sample_time_s * fps))))]
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, bgr = cap.read()
                if ok and bgr is not None and bgr.size > 0:
                    frames.append(bgr)
            cap.release()
    if not frames:
        return []

    src_h, src_w = frames[0].shape[:2]
    raw_boxes: list[tuple[int, int, int, int]] = []
    for fr in frames:
        raw_boxes.extend(_yunet_detect_boxes(fr, score_threshold=score_threshold, yunet_model_path=yunet_model_path))

    if not raw_boxes:
        return []

    # Merge overlapping raw detections (across frames or detectors) into clean union avoid boxes
    merged: list[list[int]] = []
    for bx0, by0, bx1, by1 in sorted(raw_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True):
        placed = False
        for m in merged:
            ix0, iy0 = max(m[0], bx0), max(m[1], by0)
            ix1, iy1 = min(m[2], bx1), min(m[3], by1)
            if ix1 > ix0 and iy1 > iy0:
                inter = (ix1 - ix0) * (iy1 - iy0)
                area_b = max(1, (bx1 - bx0) * (by1 - by0))
                if inter / float(area_b) >= 0.15:
                    m[0] = min(m[0], bx0)
                    m[1] = min(m[1], by0)
                    m[2] = max(m[2], bx1)
                    m[3] = max(m[3], by1)
                    placed = True
                    break
        if not placed:
            merged.append([bx0, by0, bx1, by1])

    sx = target_w / float(src_w)
    sy = target_h / float(src_h)
    zones: list[tuple[int, int, int, int]] = []
    for bx0, by0, bx1, by1 in merged:
        bw = bx1 - bx0
        bh = by1 - by0
        px = int(round(bw * pad_x_ratio))
        py = int(round(bh * pad_y_ratio))
        zx0 = max(0, int(round((bx0 - px) * sx)))
        zy0 = max(0, int(round((by0 - py) * sy)))
        zx1 = min(target_w, int(round((bx1 + px) * sx)))
        zy1 = min(target_h, int(round((by1 + py) * sy)))
        zones.append((zx0, zy0, zx1, zy1))
    return zones


def _resolve_safe_floating_origin(
    lx: int,
    ly: int,
    avoid_zones: list[Any] | None,
    *,
    note_w: int = 520,
    note_h: int = 165,
) -> tuple[int, int]:
    """Shift a floating callout origin away from protected face/subject bounding boxes (1920x1080 space)."""
    zones: list[tuple[int, int, int, int]] = []
    for z in avoid_zones or []:
        if isinstance(z, (list, tuple)) and len(z) == 4:
            zones.append((int(z[0]), int(z[1]), int(z[2]), int(z[3])))
    if not zones:
        return max(60, min(1920 - note_w - 40, lx)), max(70, min(1080 - note_h - 40, ly))

    def _overlaps(x0: int, y0: int) -> bool:
        x1, y1 = x0 + note_w, y0 + note_h
        return any(not (x1 <= zx0 or x0 >= zx1 or y1 <= zy0 or y0 >= zy1) for zx0, zy0, zx1, zy1 in zones)

    raw_candidates = [
        (lx, ly),
        (1260, 340),
        (96, 340),
        (1260, 680),
        (96, 680),
        (lx, 760),
        (96, 760),
        (1320, 760),
        (96, 110),
        (1320, 110),
    ]
    # Prefer requested origin if clear; otherwise pick the closest non-overlapping safe anchor
    c0x = max(60, min(1920 - note_w - 40, lx))
    c0y = max(70, min(1080 - note_h - 40, ly))
    if not _overlaps(c0x, c0y):
        return c0x, c0y

    valid: list[tuple[float, int, int]] = []
    for idx_c, (cx, cy) in enumerate(raw_candidates[1:]):
        cx_c = max(60, min(1920 - note_w - 40, cx))
        cy_c = max(70, min(1080 - note_h - 40, cy))
        if not _overlaps(cx_c, cy_c):
            dist = ((cx_c - c0x) ** 2 + (cy_c - c0y) ** 2) ** 0.5
            # Slight preference for clean horizontal eye-level side callouts (indices 0, 1)
            bonus = -260.0 if idx_c in (0, 1) else 0.0
            valid.append((dist + bonus, cx_c, cy_c))
    if valid:
        valid.sort(key=lambda t: t[0])
        return valid[0][1], valid[0][2]
    return c0x, c0y


def _build_editorial_html(spec: EditorialGraphicSpec, *, width: int, height: int) -> str:
    theme = dict(PALEO_ICE_AGE_THEME)
    accent = spec.accent_color or theme["accent_amber"]
    accent_cool = str(spec.meta.get("accent_secondary") or theme["accent_glacial"])
    font_css = build_font_face_css(
        ["Cinzel", "Cormorant Garamond", "Plus Jakarta Sans", "IBM Plex Mono", "JetBrains Mono"]
    )
    gsap_uri = resolve_vendor_js("gsap.min.js").as_uri()
    split_uri = resolve_vendor_js("SplitText.min.js").as_uri()
    draw_uri = resolve_vendor_js("DrawSVGPlugin.min.js").as_uri()
    ease_uri = resolve_vendor_js("CustomEase.min.js").as_uri()
    rough_uri = resolve_vendor_js("rough.js").as_uri()

    scale = height / 1080.0
    safe_title = html.escape(spec.title)
    safe_sub = html.escape(spec.subtitle)
    eyebrow = html.escape(str(spec.meta.get("eyebrow") or "PLEISTOCENE FIELD ARCHIVE"))
    dur = float(spec.duration_s)
    out_start = max(0.75, dur - 0.50)

    pos_map = {
        "bottom_left": "stage-bottom-left",
        "bottom_right": "stage-bottom-right",
        "bottom_center": "stage-bottom-center",
        "top_left": "stage-top-left",
        "center": "stage-center",
    }
    stage_cls = pos_map.get(spec.position, "stage-bottom-left")
    scrim_anchor_map = {
        "bottom_left": "18% 88%",
        "bottom_right": "82% 88%",
        "bottom_center": "50% 88%",
        "top_left": "18% 14%",
        "center": "50% 50%",
    }
    corner_scrim_anchor = scrim_anchor_map.get(spec.position, "18% 88%")
    resolved_meta = dict(spec.meta)

    if spec.template == "editorial_chapter_slate":
        body_html = f"""
        <div id="stage" class="{stage_cls if spec.position != 'bottom_left' else 'stage-center'}">
          <div class="soft-scrim"></div>
          <div class="slate-wrap" id="bbox-root">
            <div class="eyebrow mono">{eyebrow}</div>
            <h1 class="slate-title" id="split-target">{safe_title}</h1>
            <svg id="rough-svg" class="rough-rule" viewBox="0 0 640 28" width="640" height="28"></svg>
            {f'<div class="slate-sub">{safe_sub}</div>' if safe_sub else ''}
          </div>
        </div>"""
    elif spec.template == "chalk_circle_callout":
        cx = int(spec.meta.get("cx", 960))
        cy = int(spec.meta.get("cy", 540))
        rx = int(spec.meta.get("rx", 180))
        ry = int(spec.meta.get("ry", 120))
        raw_lx = int(spec.meta.get("label_x", min(1320, cx + rx + 85)))
        raw_ly = int(spec.meta.get("label_y", max(150, cy - ry - 20)))
        lx, ly = _resolve_safe_floating_origin(raw_lx, raw_ly, spec.meta.get("avoid_zones"))
        resolved_meta["label_x"] = lx
        resolved_meta["label_y"] = ly
        scrim_x = round((lx + 240) / 19.2, 1)
        scrim_y = round((ly + 75) / 10.8, 1)
        body_html = f"""
        <div id="stage" class="stage-full">
          <div class="floating-scrim" style="background: radial-gradient(ellipse 46% 32% at {scrim_x}% {scrim_y}%, rgba(4,7,12,0.88) 0%, rgba(4,7,12,0.54) 56%, rgba(4,7,12,0) 100%);"></div>
          <svg id="rough-svg" class="full-svg" viewBox="0 0 1920 1080" width="1920" height="1080"></svg>
          <div class="floating-note" id="bbox-root" style="left:{lx}px; top:{ly}px;">
            <div class="eyebrow mono">{eyebrow}</div>
            <div class="float-title" id="split-target">{safe_title}</div>
            {f'<div class="float-sub">{safe_sub}</div>' if safe_sub else ''}
          </div>
        </div>"""
    elif spec.template == "handdrawn_stat_underline":
        start_val = float(spec.meta.get("start_val", 0))
        end_val = float(spec.meta.get("end_val", 10000))
        prefix = html.escape(str(spec.meta.get("prefix", "")))
        suffix = html.escape(str(spec.meta.get("suffix", "")))
        body_html = f"""
        <div id="stage" class="{stage_cls}">
          <div class="corner-scrim"></div>
          <div class="stat-editorial" id="bbox-root"
               data-start="{start_val}" data-end="{end_val}" data-prefix="{prefix}" data-suffix="{suffix}">
            <div class="eyebrow mono">{eyebrow}</div>
            <div class="big-num mono" id="stat-num">{prefix}{int(start_val):,}{suffix}</div>
            <svg id="rough-svg" class="stat-underline-svg" viewBox="0 0 460 26" width="460" height="26"></svg>
            <div class="float-title">{safe_title}</div>
            {f'<div class="float-sub">{safe_sub}</div>' if safe_sub else ''}
          </div>
        </div>"""
    elif spec.template == "archival_margin_note":
        body_html = f"""
        <div id="stage" class="{stage_cls}">
          <div class="corner-scrim"></div>
          <div class="margin-note" id="bbox-root">
            <svg id="rough-svg" class="margin-rule-svg" viewBox="0 0 24 140" width="24" height="140"></svg>
            <div class="margin-copy">
              <div class="eyebrow mono">{eyebrow}</div>
              <div class="float-title" id="split-target">{safe_title}</div>
              {f'<div class="float-sub">{safe_sub}</div>' if safe_sub else ''}
            </div>
          </div>
        </div>"""
    elif spec.template == "rough_arrow_pointer":
        raw_lx = int(spec.meta.get("label_x", 1180))
        raw_ly = int(spec.meta.get("label_y", 340))
        lx, ly = _resolve_safe_floating_origin(raw_lx, raw_ly, spec.meta.get("avoid_zones"))
        resolved_meta["label_x"] = lx
        resolved_meta["label_y"] = ly
        scrim_x = round((lx + 240) / 19.2, 1)
        scrim_y = round((ly + 75) / 10.8, 1)
        body_html = f"""
        <div id="stage" class="stage-full">
          <div class="floating-scrim" style="background: radial-gradient(ellipse 50% 34% at {scrim_x}% {scrim_y}%, rgba(4,7,12,0.92) 0%, rgba(4,7,12,0.62) 55%, rgba(4,7,12,0) 100%);"></div>
          <svg id="rough-svg" class="full-svg" viewBox="0 0 1920 1080" width="1920" height="1080"></svg>
          <div class="floating-note" id="bbox-root" style="left:{lx}px; top:{ly}px;">
            <div class="eyebrow mono">{eyebrow}</div>
            <div class="float-title" id="split-target">{safe_title}</div>
            {f'<div class="float-sub">{safe_sub}</div>' if safe_sub else ''}
          </div>
        </div>"""
    else:  # kinetic_whisper_title
        body_html = f"""
        <div id="stage" class="{stage_cls if spec.position != 'bottom_left' else 'stage-bottom-center'}">
          <div class="whisper-scrim"></div>
          <div class="whisper-wrap" id="bbox-root">
            <div class="eyebrow mono">{eyebrow}</div>
            <div class="whisper-title" id="split-target">{safe_title}</div>
            <svg id="rough-svg" class="rough-rule" viewBox="0 0 520 22" width="520" height="22"></svg>
            {f'<div class="float-sub">{safe_sub}</div>' if safe_sub else ''}
          </div>
        </div>"""

    meta_js = json.dumps(resolved_meta)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: {width}px; height: {height}px; overflow: hidden; background: transparent;
  font-family: {theme["font_sans"]}; color: {theme["text_primary"]};
  -webkit-font-smoothing: antialiased;
}}
#viewport-scale {{
  width: 1920px; height: 1080px;
  transform: scale({scale:.6f}); transform-origin: top left; position: relative;
}}
.mono {{ font-family: {theme["font_mono"]}; font-variant-numeric: tabular-nums; }}
.stage-center {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
.stage-bottom-left {{ position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: flex-start; padding: 0 0 76px 88px; }}
.stage-bottom-right {{ position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: flex-end; padding: 0 88px 76px 0; }}
.stage-bottom-center {{ position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 72px; }}
.stage-top-left {{ position: absolute; inset: 0; display: flex; align-items: flex-start; justify-content: flex-start; padding: 72px 0 0 88px; }}
.stage-full {{ position: absolute; inset: 0; }}

/* Organic feathered editorial scrims — ZERO solid SaaS boxes! */
.soft-scrim {{
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 72% 42% at 50% 50%, rgba(4,7,12,0.72) 0%, rgba(4,7,12,0.34) 55%, rgba(4,7,12,0) 100%);
  opacity: 0;
}}
.corner-scrim {{
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 56% 38% at {corner_scrim_anchor}, rgba(4,7,12,0.72) 0%, rgba(4,7,12,0.28) 54%, rgba(4,7,12,0) 100%);
  opacity: 0;
}}
.floating-scrim {{
  position: absolute; inset: 0; z-index: 1; pointer-events: none;
  opacity: 0;
}}
.whisper-scrim {{
  position: absolute; inset: 0;
  background: linear-gradient(0deg, rgba(4,7,12,0.78) 0%, rgba(4,7,12,0.22) 32%, rgba(4,7,12,0) 58%);
  opacity: 0;
}}

.eyebrow {{
  font-size: 19px; font-weight: 600; letter-spacing: 0.24em; text-transform: uppercase;
  color: {accent}; margin-bottom: 8px;
  text-shadow: 0 3px 16px rgba(0,0,0,0.96), 0 1px 4px rgba(0,0,0,0.95);
}}
.slate-wrap {{ position: relative; text-align: center; max-width: 1460px; z-index: 2; }}
.slate-title {{
  font-family: {theme["font_display"]}; font-size: 82px; font-weight: 700;
  letter-spacing: 0.10em; line-height: 1.08; color: #F9FBFE;
  text-shadow: 0 10px 34px rgba(0,0,0,0.96), 0 3px 8px rgba(0,0,0,0.95);
  filter: url(#ink-roughen);
}}
.slate-sub {{
  font-family: {theme["font_editorial"]}; font-style: italic; font-size: 40px; font-weight: 600;
  color: #E8EFF7; margin-top: 10px;
  text-shadow: 0 5px 22px rgba(0,0,0,0.96), 0 2px 5px rgba(0,0,0,0.95);
}}
.rough-rule {{ display: block; margin: 14px auto 6px; overflow: visible; filter: drop-shadow(0 3px 10px rgba(0,0,0,0.85)); }}

.full-svg {{ position: absolute; inset: 0; width: 1920px; height: 1080px; z-index: 2; overflow: visible; filter: drop-shadow(0 4px 14px rgba(0,0,0,0.88)); }}
.floating-note {{ position: absolute; max-width: 560px; z-index: 3; }}
.float-title {{
  font-family: {theme["font_sans"]}; font-size: 38px; font-weight: 700; line-height: 1.15;
  color: #FFFFFF; letter-spacing: -0.01em;
  text-shadow: 0 6px 24px rgba(0,0,0,0.98), 0 2px 6px rgba(0,0,0,0.96);
}}
.float-sub {{
  font-family: {theme["font_editorial"]}; font-style: italic; font-size: 29px; font-weight: 600;
  color: #DCE7F2; margin-top: 6px; line-height: 1.25;
  text-shadow: 0 4px 18px rgba(0,0,0,0.98), 0 1px 4px rgba(0,0,0,0.96);
}}

.stat-editorial {{ position: relative; z-index: 2; max-width: 780px; }}
.big-num {{
  font-family: 'JetBrains Mono', monospace; font-size: 92px; font-weight: 700; line-height: 0.98;
  color: #FFFFFF; letter-spacing: -0.03em;
  text-shadow: 0 10px 32px rgba(0,0,0,0.98), 0 3px 8px rgba(0,0,0,0.96);
}}
.stat-underline-svg {{ display: block; margin: 4px 0 10px -6px; overflow: visible; }}

.margin-note {{ position: relative; z-index: 2; display: flex; align-items: stretch; gap: 22px; max-width: 760px; }}
.margin-rule-svg {{ flex-shrink: 0; overflow: visible; }}
.margin-copy {{ display: flex; flex-direction: column; justify-content: center; }}

.whisper-wrap {{ position: relative; z-index: 2; text-align: center; max-width: 1420px; }}
.whisper-title {{
  font-family: {theme["font_display"]}; font-size: 62px; font-weight: 700; letter-spacing: 0.08em;
  color: #FFFFFF; text-shadow: 0 8px 30px rgba(0,0,0,0.98), 0 2px 6px rgba(0,0,0,0.96);
}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute">
  <defs>
    <filter id="ink-roughen" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.2" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
</svg>
<div id="viewport-scale">{body_html}</div>
<script src="{gsap_uri}"></script>
<script src="{split_uri}"></script>
<script src="{draw_uri}"></script>
<script src="{ease_uri}"></script>
<script src="{rough_uri}"></script>
<script>
gsap.registerPlugin(SplitText, DrawSVGPlugin, CustomEase);
const easeOut = CustomEase.create("edOut", "M0,0 C0.16,1 0.3,1 1,1");
const template = {json.dumps(spec.template)};
const accent = {json.dumps(accent)};
const accentCool = {json.dumps(accent_cool)};
const meta = {meta_js};
const outStart = {out_start:.3f};
const svg = document.getElementById("rough-svg");
const rc = rough.svg(svg);
const roughPaths = [];

function addRoughNode(node) {{
  svg.appendChild(node);
  node.querySelectorAll("path").forEach((p) => {{
    p.setAttribute("stroke-linecap", "round");
    p.setAttribute("stroke-linejoin", "round");
    roughPaths.push(p);
  }});
}}

let chalkEllipseGroup = null;
let chalkLeaderPath = null;
let chalkBase = null;
const faceTrack = Array.isArray(meta.face_track) ? meta.face_track : [];

function sampleTrackAt(t) {{
  if (!faceTrack.length) return null;
  if (t <= faceTrack[0].t_s) return faceTrack[0];
  const last = faceTrack[faceTrack.length - 1];
  if (t >= last.t_s) return last;
  for (let i = 0; i < faceTrack.length - 1; i++) {{
    const a = faceTrack[i], b = faceTrack[i + 1];
    if (t >= a.t_s && t <= b.t_s) {{
      const u = (t - a.t_s) / Math.max(0.001, b.t_s - a.t_s);
      return {{
        cx: a.cx + (b.cx - a.cx) * u,
        cy: a.cy + (b.cy - a.cy) * u,
        rx: a.rx + (b.rx - a.rx) * u,
        ry: a.ry + (b.ry - a.ry) * u,
      }};
    }}
  }}
  return last;
}}

function computeLeaderD(cx, cy, rx, ry, lx, ly) {{
  let sx, sy, ex, ey, mx, my;
  if (lx > cx + rx * 0.50) {{
    sx = cx + rx * 1.02;
    sy = cy - ry * 0.10;
    ex = lx - 24;
    ey = ly + 42;
    mx = (sx + ex) * 0.5;
    my = Math.min(sy, ey) - 24;
  }} else if (lx + 420 < cx - rx * 0.50) {{
    sx = cx - rx * 1.02;
    sy = cy - ry * 0.10;
    ex = lx + 440;
    ey = ly + 42;
    mx = (sx + ex) * 0.5;
    my = Math.min(sy, ey) - 24;
  }} else {{
    const isBelow = ly >= cy;
    sx = cx;
    sy = isBelow ? (cy + ry * 1.02) : (cy - ry * 1.02);
    ex = Math.max(lx + 40, Math.min(lx + 380, cx));
    ey = isBelow ? (ly - 16) : (ly + 145);
    mx = (sx + ex) * 0.5 + 18;
    my = (sy + ey) * 0.5;
  }}
  return `M ${{sx.toFixed(1)}} ${{sy.toFixed(1)}} Q ${{mx.toFixed(1)}} ${{my.toFixed(1)}} ${{ex.toFixed(1)}} ${{ey.toFixed(1)}}`;
}}

// Build deterministic hand-drawn Rough.js chalk/ochre vector artwork
if (template === "editorial_chapter_slate") {{
  addRoughNode(rc.line(30, 14, 610, 14, {{ stroke: accent, strokeWidth: 3.2, roughness: 1.7, bowing: 1.8, seed: 11 }}));
  addRoughNode(rc.line(110, 21, 530, 20, {{ stroke: accentCool, strokeWidth: 1.4, roughness: 1.4, bowing: 1.2, seed: 23 }}));
}} else if (template === "chalk_circle_callout") {{
  const t0 = sampleTrackAt(0.0);
  const cx = t0 ? t0.cx : (meta.cx || 960);
  const cy = t0 ? t0.cy : (meta.cy || 540);
  const rx = t0 ? t0.rx : (meta.rx || 180);
  const ry = t0 ? t0.ry : (meta.ry || 120);
  const lx = meta.label_x || Math.min(1320, cx + rx + 85), ly = meta.label_y || Math.max(150, cy - ry - 20);
  chalkBase = {{ cx, cy, rx, ry, lx, ly }};
  chalkEllipseGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  chalkEllipseGroup.setAttribute("id", "chalk-ellipse-g");
  const ellNode = rc.ellipse(cx, cy, rx * 2, ry * 2, {{ stroke: accent, strokeWidth: 3.8, roughness: 2.0, bowing: 1.5, seed: 31 }});
  chalkEllipseGroup.appendChild(ellNode);
  svg.appendChild(chalkEllipseGroup);
  chalkEllipseGroup.querySelectorAll("path").forEach((p) => {{
    p.setAttribute("stroke-linecap", "round");
    p.setAttribute("stroke-linejoin", "round");
    roughPaths.push(p);
  }});
  if (faceTrack.length >= 2) {{
    chalkLeaderPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    chalkLeaderPath.setAttribute("d", computeLeaderD(cx, cy, rx, ry, lx, ly));
    chalkLeaderPath.setAttribute("fill", "none");
    chalkLeaderPath.setAttribute("stroke", "#F5E9D3");
    chalkLeaderPath.setAttribute("stroke-width", "3.0");
    chalkLeaderPath.setAttribute("stroke-linecap", "round");
    svg.appendChild(chalkLeaderPath);
    roughPaths.push(chalkLeaderPath);
  }} else {{
    const sx = lx > cx + rx * 0.50 ? cx + rx * 0.98 : (lx + 420 < cx - rx * 0.50 ? cx - rx * 0.98 : cx);
    const sy = (lx > cx + rx * 0.50 || lx + 420 < cx - rx * 0.50) ? cy - ry * 0.12 : (ly >= cy ? cy + ry * 0.98 : cy - ry * 0.98);
    const ex = lx > cx + rx * 0.50 ? lx - 24 : (lx + 420 < cx - rx * 0.50 ? lx + 440 : Math.max(lx + 40, Math.min(lx + 380, cx)));
    const ey = (lx > cx + rx * 0.50 || lx + 420 < cx - rx * 0.50) ? ly + 42 : (ly >= cy ? ly - 16 : ly + 145);
    const mx = (sx + ex) * 0.5;
    const my = Math.min(sy, ey) - 24;
    addRoughNode(rc.curve([[sx, sy], [mx, my], [ex, ey]], {{ stroke: "#F5E9D3", strokeWidth: 2.8, roughness: 1.6, seed: 37 }}));
  }}
}} else if (template === "handdrawn_stat_underline") {{
  addRoughNode(rc.line(8, 12, 430, 9, {{ stroke: accent, strokeWidth: 4.5, roughness: 2.0, bowing: 1.8, seed: 41 }}));
  addRoughNode(rc.line(18, 19, 360, 18, {{ stroke: accent, strokeWidth: 2.0, roughness: 1.8, bowing: 1.4, seed: 43 }}));
}} else if (template === "archival_margin_note") {{
  addRoughNode(rc.line(10, 4, 11, 134, {{ stroke: accent, strokeWidth: 4.2, roughness: 1.5, bowing: 1.2, seed: 53 }}));
}} else if (template === "rough_arrow_pointer") {{
  const x1 = meta.x1 || 620, y1 = meta.y1 || 680, cx = meta.cx || 890, cy = meta.cy || 420, x2 = meta.x2 || 1145, y2 = meta.y2 || 395;
  addRoughNode(rc.curve([[x1, y1], [cx, cy], [x2, y2]], {{ stroke: accent, strokeWidth: 4.2, roughness: 1.8, seed: 61 }}));
  const ang = Math.atan2(y2 - cy, x2 - cx);
  const a1x = x2 - 26 * Math.cos(ang - 0.45), a1y = y2 - 26 * Math.sin(ang - 0.45);
  const a2x = x2 - 26 * Math.cos(ang + 0.45), a2y = y2 - 26 * Math.sin(ang + 0.45);
  addRoughNode(rc.linearPath([[a1x, a1y], [x2, y2], [a2x, a2y]], {{ stroke: accent, strokeWidth: 4.0, roughness: 1.4, seed: 67 }}));
}} else {{
  addRoughNode(rc.line(40, 11, 480, 11, {{ stroke: accent, strokeWidth: 3.2, roughness: 1.8, bowing: 1.5, seed: 71 }}));
}}

const tl = gsap.timeline({{ paused: true }});
const scrimEl = document.querySelector(".soft-scrim, .corner-scrim, .whisper-scrim, .floating-scrim");
if (scrimEl) tl.to(scrimEl, {{ opacity: 1, duration: 0.45, ease: "power2.out" }}, 0);

if (template === "handdrawn_stat_underline") {{
  const box = document.querySelector(".stat-editorial");
  const sVal = parseFloat(box.dataset.start);
  const eVal = parseFloat(box.dataset.end);
  const pref = box.dataset.prefix || "";
  const suff = box.dataset.suffix || "";
  const obj = {{ v: sVal }};
  tl.from(".eyebrow", {{ opacity: 0, y: 12, duration: 0.35, ease: easeOut }}, 0.05)
    .from("#stat-num", {{ opacity: 0, y: 22, duration: 0.45, ease: easeOut }}, 0.08)
    .to(obj, {{
      v: eVal, duration: 1.15, ease: easeOut,
      onUpdate: () => {{
        const val = Math.round(obj.v).toLocaleString("en-US");
        document.getElementById("stat-num").textContent = pref + val + suff;
      }}
    }}, 0.10)
    .from(roughPaths, {{ drawSVG: "0%", stagger: 0.10, duration: 0.65, ease: easeOut }}, 0.25)
    .from(".float-title, .float-sub", {{ opacity: 0, y: 14, stagger: 0.08, duration: 0.45, ease: easeOut }}, 0.35)
    .to("#stage", {{ opacity: 0, y: 10, duration: 0.42, ease: "power2.in" }}, outStart);
}} else {{
  const splitTarget = document.getElementById("split-target");
  const sp = splitTarget ? new SplitText(splitTarget, {{ type: "words" }}) : null;
  tl.from(".eyebrow", {{ opacity: 0, y: 12, duration: 0.35, ease: easeOut }}, 0.05);
  if (roughPaths.length) {{
    tl.from(roughPaths, {{ drawSVG: "0%", stagger: 0.09, duration: 0.72, ease: easeOut }}, 0.08);
  }}
  if (sp) {{
    tl.from(sp.words, {{ opacity: 0, y: 24, stagger: 0.05, duration: 0.48, ease: easeOut }}, 0.16);
  }}
  tl.from(".slate-sub, .float-sub", {{ opacity: 0, y: 14, duration: 0.45, ease: easeOut }}, 0.38)
    .to("#stage", {{ opacity: 0, y: -8, duration: 0.45, ease: "power2.in" }}, outStart);
}}

window.__setTime = function(t) {{
  if (chalkEllipseGroup && chalkBase && faceTrack.length >= 2) {{
    const cur = sampleTrackAt(t);
    if (cur) {{
      const sx = cur.rx / Math.max(1, chalkBase.rx);
      const sy = cur.ry / Math.max(1, chalkBase.ry);
      chalkEllipseGroup.setAttribute(
        "transform",
        `translate(${{cur.cx.toFixed(2)}} ${{cur.cy.toFixed(2)}}) scale(${{sx.toFixed(4)}} ${{sy.toFixed(4)}}) translate(${{(-chalkBase.cx).toFixed(2)}} ${{(-chalkBase.cy).toFixed(2)}})`
      );
      if (chalkLeaderPath) {{
        chalkLeaderPath.setAttribute("d", computeLeaderD(cur.cx, cur.cy, cur.rx, cur.ry, chalkBase.lx, chalkBase.ly));
      }}
    }}
  }}
  tl.time(t, false);
}};
window.__getBBox = function() {{
  const el = document.getElementById("bbox-root");
  if (!el) return [0, 0, 0, 0];
  const r = el.getBoundingClientRect();
  return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
}};
</script>
</body>
</html>"""


def render_editorial_graphic_rgba(
    spec: EditorialGraphicSpec,
    out_mov: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    render_width: int = 1920,
    render_height: int = 1080,
    auto_face_safe_source: Path | None = None,
    face_sample_time_s: float = 0.5,
) -> dict[str, Any]:
    """Render a boxless Rough.js + GSAP 3.13 editorial graphic overlay to lossless PNG-RGBA MOV."""
    spec.validate()
    detected_zones: list[tuple[int, int, int, int]] = []
    if auto_face_safe_source is not None:
        detected_zones = detect_face_avoid_zones(auto_face_safe_source, sample_time_s=face_sample_time_s, multi_frame_union=True)
        if detected_zones:
            existing = list(spec.meta.get("avoid_zones") or [])
            spec.meta["avoid_zones"] = existing + [list(z) for z in detected_zones]
        if spec.template == "chalk_circle_callout" and not spec.meta.get("face_track"):
            track = detect_face_track(auto_face_safe_source, max_duration_s=spec.duration_s, num_samples=10)
            if track:
                spec.meta["face_track"] = track
                spec.meta["cx"] = int(round(track[0]["cx"]))
                spec.meta["cy"] = int(round(track[0]["cy"]))
                spec.meta["rx"] = int(round(track[0]["rx"]))
                spec.meta["ry"] = int(round(track[0]["ry"]))
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_mov.with_suffix(".html")
    html_path.write_text(_build_editorial_html(spec, width=render_width, height=render_height), encoding="utf-8")

    total_frames = max(2, int(round(spec.duration_s * fps)))
    sx = width / float(render_width)
    sy = height / float(render_height)
    vf = f"scale={width}:{height}:flags=lanczos" if (render_width, render_height) != (width, height) else "null"

    ff_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-vf",
        vf,
        "-c:v",
        "png",
        "-pix_fmt",
        "rgba",
        str(out_mov),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    bbox = [0, 0, 0, 0]

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": render_width, "height": render_height}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.evaluate(f"() => window.__setTime({spec.duration_s * 0.5:.3f})")
        raw_bb = list(page.evaluate("() => window.__getBBox()"))
        bbox = [
            int(round(raw_bb[0] * sx)),
            int(round(raw_bb[1] * sy)),
            int(round(raw_bb[2] * sx)),
            int(round(raw_bb[3] * sy)),
        ]
        cdp = page.context.new_cdp_session(page)
        cdp.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})

        for f_idx in range(total_frames):
            t_s = f_idx / float(fps)
            page.evaluate(f"() => window.__setTime({t_s:.4f})")
            res = cdp.send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            proc.stdin.write(base64.b64decode(res["data"]))

        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg RGBA editorial graphic encode failed with exit code {ret}")

    return {
        "bridge_id": spec.graphic_id,
        "graphic_id": spec.graphic_id,
        "template": spec.template,
        "path": str(out_mov),
        "width": width,
        "height": height,
        "fps": fps,
        "start_s": spec.start_s,
        "end_s": round(spec.start_s + spec.duration_s, 3),
        "duration_s": spec.duration_s,
        "bbox": bbox,
        "avoid_zones": list(spec.meta.get("avoid_zones") or []),
    }
