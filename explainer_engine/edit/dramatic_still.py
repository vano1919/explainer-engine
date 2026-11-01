"""A held still must change dramatically (BP-170, the creator 2026-11-01: a still may stay up to 5 s only if something dramatic
changes in it, a person cut out and placed elsewhere; a small dot or a small hammer is not enough).

The simple version, on purpose: a validator for the spec of the change, a pixel measure of two frames, and a renderer that cuts a
subject out of a clean plate and puts it elsewhere (or swaps the plate). No other module is touched: slow zooms (parallax),
text pops and accents are minor events and never count (C8.2), so they do not appear here at all.

    validate_dramatic_change(spec, shot_seconds=4.0, zone_id="middle_calm_90_480s") -> findings (empty = fine)
    check_script_stills(shots)                                                    -> findings for every still shot of a script
    measure_frame_change(before, after)                                           -> {"changed_frac", "is_dramatic", ...}
    render_dramatic_still(bg_before, subject_rgba, spec, t_s=..., bg_after=None) -> the frame at second t_s

A spec is the object of ``schemas/dramatic_still.schema.json``. The declared numbers are not trusted: the relocation and the
subject area are computed from the boxes.
"""

from __future__ import annotations

import math

from explainer_engine.edit import rhythm_profile
from explainer_engine.standards import sourced_rules as SR


def _finding(severity: str, where: str, detail: str) -> dict:
    return {"rule": "BP-170", "severity": SR.level("BP-170", severity), "where": where, "detail": detail}


def _center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def box_area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def relocation(from_box, to_box) -> float:
    """Distance between the box centres in frame fractions (x and y both 0..1, so the diagonal is ~1.41)."""
    (ax, ay), (bx, by) = _center(from_box), _center(to_box)
    return math.hypot(bx - ax, by - ay)


def validate_dramatic_change(spec: dict | None, *, shot_seconds: float, zone_id: str = "middle_calm_90_480s",
                             where: str = "still") -> list[dict]:
    """Findings for one held still. A still shorter than its zone's static hold needs no change; longer than BP-109's cap it
    fails whatever it does; in between it needs a change that is large, in the middle of the hold."""
    cap = SR.T("BP-109", "still_shot_max_s")
    static = SR.T("BP-170", "static_still_max_s_by_zone")
    if zone_id not in static:
        raise KeyError(f"unknown zone {zone_id!r}")
    if shot_seconds > cap:
        return [_finding("FAIL", where, f"{shot_seconds:g} s is over the {cap:g} s cap of a still (BP-109): cut or make it video")]
    if shot_seconds <= static[zone_id]:
        return []
    if not spec:
        return [_finding("FAIL", where, f"held {shot_seconds:g} s in {zone_id} (static limit {static[zone_id]:g} s) with no "
                                        "dramatic change: add a relocation or a plate swap, or cut it shorter")]
    out: list[dict] = []
    kind = spec.get("kind")
    if kind in ("cutout_relocation", "composite_cutout_and_plate"):
        if not (spec.get("from_box") and spec.get("to_box")):
            out.append(_finding("FAIL", where, "a cutout relocation names its from_box and to_box"))
        else:
            dist = relocation(spec["from_box"], spec["to_box"])
            area = box_area(spec["from_box"])
            need_d, need_a = SR.T("BP-170", "min_relocation_distance_frac"), SR.T("BP-170", "min_subject_area_frac")
            if dist < need_d:
                out.append(_finding("FAIL", where, f"the subject moves {dist:.2f} of the frame (< {need_d}): a nudge is not a change"))
            if area < need_a:
                out.append(_finding("FAIL", where, f"the subject covers {area:.2f} of the frame (< {need_a}): a small thing is not a change"))
    if kind in ("plate_swap", "composite_cutout_and_plate"):
        need_p = SR.T("BP-170", "min_plate_swap_pixel_frac")
        if float(spec.get("plate_swap_pixel_frac", 0.0)) < need_p:
            out.append(_finding("FAIL", where, f"the plate changes {spec.get('plate_swap_pixel_frac', 0.0)} of the pixels (< {need_p})"))
    if kind not in ("cutout_relocation", "plate_swap", "composite_cutout_and_plate"):
        out.append(_finding("FAIL", where, f"unknown change kind {kind!r}"))
    lo, hi = SR.T("BP-170", "change_window_frac")
    at = float(spec.get("at_s", -1))
    if not lo * shot_seconds <= at <= hi * shot_seconds:
        out.append(_finding("FAIL", where, f"the change at {at:g} s is outside the middle of the hold "
                                           f"({lo * shot_seconds:.2f}-{hi * shot_seconds:.2f} s): it must be seen, not at the edge"))
    return out


def check_script_stills(shots: list[dict], *, profile_name: str = "mrbeast_animated") -> list[dict]:
    """Every still shot of a script (BP-109 lane ``still``): its hold against its zone. A shot's time is its ``start_s`` or the
    running sum of ``seconds``; its change, if any, is ``dramatic_change``."""
    from explainer_engine.scripting.film_shots import visual_lane
    total = sum(float(s["seconds"]) for s in shots)
    t, out = 0.0, []
    for s in shots:
        start = float(s.get("start_s", t))
        t = start + float(s["seconds"])
        if visual_lane(s) != "still":
            continue
        zone = rhythm_profile.zone_at_time(start, total_s=max(total, 1.0), profile_name=profile_name)["id"]
        out += validate_dramatic_change(s.get("dramatic_change"), shot_seconds=float(s["seconds"]), zone_id=zone,
                                        where=str(s.get("id", "?")))
    return out


def measure_frame_change(before, after, *, pixel_delta: int = 24) -> dict:
    """How much of the picture differs between two frames (PIL images of one size). A relocation changes the old and the new
    place of the subject, a plate swap most of the frame; a small dot or a 4 % shift changes little."""
    import numpy as np
    a = np.asarray(before.convert("RGB"), dtype=np.int16)
    b = np.asarray(after.convert("RGB"), dtype=np.int16)
    if a.shape != b.shape:
        raise ValueError("frames of different sizes")
    mask = np.abs(a - b).max(axis=2) > pixel_delta
    frac = float(mask.mean())
    swap = frac >= SR.T("BP-170", "min_plate_swap_pixel_frac")
    moved = frac >= SR.T("BP-170", "min_subject_area_frac")
    return {"changed_frac": round(frac, 4), "plate_swap": swap, "is_dramatic": bool(swap or moved)}


def render_dramatic_still(bg_before, subject_rgba, spec: dict, *, t_s: float, bg_after=None):
    """The frame at second ``t_s``: before ``spec['at_s']`` the subject stands in ``from_box`` on ``bg_before``; from then on in
    ``to_box`` on ``bg_after`` (or the same plate). The plate must be clean, without the subject baked in, or the cut leaves a hole."""
    from PIL import Image
    after = t_s >= float(spec["at_s"])
    plate = (bg_after if (after and bg_after is not None) else bg_before).convert("RGBA")
    frame = plate.copy()
    box = spec["to_box"] if after else spec["from_box"]
    if spec.get("kind") != "plate_swap" and box:
        w, h = frame.size
        x0, y0, x1, y1 = round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)
        sub = subject_rgba.convert("RGBA").resize((max(1, x1 - x0), max(1, y1 - y0)), Image.LANCZOS)
        frame.alpha_composite(sub, (x0, y0))
    return frame.convert("RGB")
