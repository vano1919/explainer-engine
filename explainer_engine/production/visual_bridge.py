"""The Visual-Bridge Layer (VB-1..VB-8 & Step 3 Epilogue Statement): word-locked documentary typography and callouts.

Implements the 8 visual-bridge devices plus epilogue on-screen statements over ``still_25d`` and ``video`` shots,
locked to the measured word spine and automatically positioned outside ``keep_in_frame`` face boxes:

- ``DATE_LOC_STAMP`` (VB-1): typewriter date + sector stamp in safe top-left/bottom-left margin.
- ``KINETIC_KEYWORD`` (VB-2): 2-4 word serif phrase landing on a spoken turn word.
- ``HIGHLIGHT_SWEEP`` (VB-3): warm amber highlight bar sweeping across an archival quote/extract.
- ``OBJECT_CALLOUT_CARD`` (VB-4): leader line + archival tag pointing to a physical prop in frame.
- ``SPATIAL_POINTER_LINE`` (VB-5): thin tactical bracket labeling trench geography.
- ``ARCHIVE_FACT_TAG`` (VB-6): lower-right archival source badge citing the historical record.
- ``LEDGER_COUNTER`` (VB-7): minimalist number counter over footage.
- ``TIMELINE_SPAN_BAR`` (VB-8): horizontal timeline bar showing war duration vs. truce duration.
- ``EPILOGUE_STATEMENT`` (Step 3): centered solemn epilogue statement (e.g. ``S08_SH004``:
  *"For one day, they remembered they were human."*).
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEVICES = (
    "DATE_LOC_STAMP",
    "KINETIC_KEYWORD",
    "HIGHLIGHT_SWEEP",
    "OBJECT_CALLOUT_CARD",
    "SPATIAL_POINTER_LINE",
    "ARCHIVE_FACT_TAG",
    "LEDGER_COUNTER",
    "TIMELINE_SPAN_BAR",
    "EPILOGUE_STATEMENT",
)

AUDIO_CLASS_OF_DEVICE = {
    "DATE_LOC_STAMP": "ov_tick",
    "KINETIC_KEYWORD": "ov_thud",
    "HIGHLIGHT_SWEEP": "ov_draw",
    "OBJECT_CALLOUT_CARD": "ov_pop",
    "SPATIAL_POINTER_LINE": "ov_draw",
    "ARCHIVE_FACT_TAG": "ov_slide",
    "LEDGER_COUNTER": "data_tick",
    "TIMELINE_SPAN_BAR": "ov_draw",
    "EPILOGUE_STATEMENT": None,  # solemn silence / music only
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, max(10, int(size)))
        except OSError:
            continue
    return ImageFont.load_default()


def safe_overlay_box(
    prefer_box: tuple[float, float, float, float],
    keep_boxes: list[dict] | None = None,
) -> tuple[float, float, float, float]:
    """Ensure an overlay box ``(x0, y0, x1, y1)`` in normalized ``[0, 1]`` coordinates avoids face boxes."""
    x0, y0, x1, y1 = prefer_box
    w, h = x1 - x0, y1 - y0
    faces = [kb["face"] for kb in (keep_boxes or []) if isinstance(kb, dict) and kb.get("face")]
    if not faces:
        return x0, y0, x1, y1

    def overlaps(bx):
        bx0, by0, bx1, by1 = bx
        for fx0, fy0, fx1, fy1 in faces:
            if min(bx1, fx1 + 0.03) > max(bx0, fx0 - 0.03) and min(by1, fy1 + 0.03) > max(by0, fy0 - 0.03):
                return True
        return False

    if not overlaps((x0, y0, x1, y1)):
        return x0, y0, x1, y1

    candidates = [
        (0.06, 0.78, 0.06 + w, 0.78 + h),
        (0.06, 0.08, 0.06 + w, 0.08 + h),
        (max(0.06, 0.94 - w), 0.78, 0.94, 0.78 + h),
        (max(0.06, 0.94 - w), 0.08, 0.94, 0.08 + h),
    ]
    for cand in candidates:
        if not overlaps(cand):
            return cand
    return x0, y0, x1, y1


def normalize_bridge_items(plan_or_shot: dict, total_frames: int, fps: int = 24) -> list[dict]:
    """Normalize ``visual_bridge`` and ``on_screen_text`` entries into frame-resolved overlay specs."""
    items: list[dict] = []
    raw_vb = plan_or_shot.get("visual_bridge")
    if isinstance(raw_vb, dict):
        raw_vb = [raw_vb]
    elif not isinstance(raw_vb, list):
        raw_vb = []

    for idx, b in enumerate(raw_vb):
        if not isinstance(b, dict):
            continue
        dev = str(b.get("device") or "KINETIC_KEYWORD")
        s_f = int(b.get("start_frame", round(float(b.get("start_s", 0.25)) * fps)))
        e_f = int(b.get("end_frame", min(total_frames, round(float(b.get("end_s", total_frames / fps - 0.25)) * fps))))
        items.append({
            "id": b.get("id") or f"vb_{idx + 1}",
            "device": dev if dev in DEVICES else "KINETIC_KEYWORD",
            "text": str(b.get("text") or "").strip(),
            "subtext": str(b.get("subtext") or "").strip(),
            "start_frame": max(0, s_f),
            "end_frame": max(s_f + 1, min(total_frames, e_f)),
            "target_xy": b.get("target_xy"),
            "box": tuple(b["box"]) if isinstance(b.get("box"), (list, tuple)) and len(b["box"]) == 4 else (0.06, 0.78, 0.54, 0.89),
        })

    ost = plan_or_shot.get("on_screen_text")
    if isinstance(ost, str) and ost.strip():
        ost = [{"text": ost.strip()}]
    if isinstance(ost, list):
        for idx, o in enumerate(ost):
            txt = str(o.get("text") if isinstance(o, dict) else o).strip()
            if not txt:
                continue
            items.append({
                "id": f"epilogue_text_{idx + 1}",
                "device": "EPILOGUE_STATEMENT",
                "text": txt,
                "subtext": "",
                "start_frame": int(round(0.35 * fps)),
                "end_frame": max(int(round(0.35 * fps)) + 12, total_frames - int(round(0.25 * fps))),
                "target_xy": None,
                "box": (0.12, 0.42, 0.88, 0.58),
            })
    return items


def bridge_audio_events(plan_or_shot: dict, total_frames: int, fps: int = 24) -> list[dict]:
    """Emit frame-locked sound events for active visual-bridge items."""
    out: list[dict] = []
    for it in normalize_bridge_items(plan_or_shot, total_frames, fps):
        cls = AUDIO_CLASS_OF_DEVICE.get(it["device"])
        if not cls:
            continue
        s_f = it["start_frame"]
        out.append({
            "event_id": f"{it['id']}:audio",
            "class": cls,
            "sync": "onset",
            "start_frame": s_f,
            "end_frame": min(total_frames, s_f + 10),
            "at_s": round(s_f / fps, 3),
        })
    return out


def render_on_frame(
    rgb: np.ndarray,
    plan_or_shot: dict,
    f: int,
    fps: int = 24,
    total_frames: int | None = None,
    keep_boxes: list[dict] | None = None,
) -> np.ndarray:
    """Composite active ``visual_bridge`` and ``on_screen_text`` items onto an RGB frame ``(H, W, 3)`` float/uint8 array."""
    H, W = rgb.shape[:2]
    total_frames = total_frames or int(plan_or_shot.get("frames") or max(f + 1, fps * 4))
    items = normalize_bridge_items(plan_or_shot, total_frames, fps)
    active = [it for it in items if it["start_frame"] <= f < it["end_frame"] and it["text"]]
    if not active:
        return rgb

    base_u8 = np.clip(rgb, 0, 255).astype(np.uint8)
    pil_im = Image.fromarray(base_u8, mode="RGB").convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for it in active:
        s_f, e_f = it["start_frame"], it["end_frame"]
        fade_in_f = max(1, int(round(0.45 * fps)))
        fade_out_f = max(1, int(round(0.55 * fps)))
        a_in = min(1.0, (f - s_f + 1) / fade_in_f)
        a_out = min(1.0, (e_f - f) / fade_out_f)
        alpha = int(round(255 * min(a_in, a_out)))
        if alpha <= 2:
            continue

        dev = it["device"]
        if dev == "EPILOGUE_STATEMENT":
            font = _load_font(int(round(H * 0.040)))
            text = it["text"]
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            tx = (W - tw) * 0.5
            ty = (H - th) * 0.48
            pad_x, pad_y = int(H * 0.028), int(H * 0.018)
            draw.rounded_rectangle(
                [tx - pad_x, ty - pad_y, tx + tw + pad_x, ty + th + pad_y],
                radius=int(H * 0.012),
                fill=(14, 13, 12, int(alpha * 0.62)),
                outline=(218, 195, 148, int(alpha * 0.70)),
                width=max(1, int(H * 0.002)),
            )
            draw.text((tx, ty), text, font=font, fill=(252, 246, 232, alpha))
        else:
            x0, y0, x1, y1 = safe_overlay_box(it["box"], keep_boxes)
            px0, py0 = int(round(x0 * W)), int(round(y0 * H))
            font = _load_font(int(round(H * 0.028)))
            text = it["text"]
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pad_x, pad_y = int(H * 0.016), int(H * 0.010)
            rx1, ry1 = min(W - 10, px0 + tw + 2 * pad_x), min(H - 10, py0 + th + 2 * pad_y)
            draw.rounded_rectangle(
                [px0, py0, rx1, ry1],
                radius=int(H * 0.008),
                fill=(22, 20, 18, int(alpha * 0.84)),
                outline=(214, 172, 96, int(alpha * 0.90)),
                width=max(1, int(H * 0.002)),
            )
            # Warm left accent bar
            draw.rectangle([px0, py0, px0 + max(3, int(W * 0.004)), ry1], fill=(214, 172, 96, alpha))
            draw.text((px0 + pad_x + 4, py0 + pad_y), text, font=font, fill=(248, 242, 228, alpha))
            if it.get("target_xy") and len(it["target_xy"]) == 2:
                tx_p, ty_p = int(round(float(it["target_xy"][0]) * W)), int(round(float(it["target_xy"][1]) * H))
                cx_card = (px0 + rx1) // 2
                cy_card = py0 if ty_p < py0 else ry1
                draw.line([(cx_card, cy_card), (tx_p, ty_p)], fill=(214, 172, 96, int(alpha * 0.85)), width=max(1, int(H * 0.002)))

    comp = Image.alpha_composite(pil_im, overlay).convert("RGB")
    out_arr = np.asarray(comp, dtype=rgb.dtype)
    return out_arr
