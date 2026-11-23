"""v3 of the 60-second test film 'The commander\'s last night' (BP-182, BP-183, BP-184; D-116).

Proves realistic LTX minimisation on the 5-scene, 3-hero one-minute film (`j5_minute.py`):
- M1_column_wide (5.0s): 3-plane depth-sliced billboard crowd + phase-staggered stride bob + rain (0s LTX).
- M2_drummer (4.0s): hinged drumstick/arm cycle (18 deg) + Lanczos+CAS punch-in (0s LTX).
- M3_commander_leads (7.5s): hinged cloak/banner rig + 3-plane marching background on A3_field (0s LTX).
- T2, T3, T4, T5 (13.5s): J5_DIALOGUE_CARD + D-119 4x2 mouth-variant swap + 2-layer robe relief on T5 (0s LTX).
- B1_ford (5.0s): 4-plane opposing billboard army wedges + animated ford water splash mask (0s LTX).
- B2_duel (5.0s): hybrid 1.96s J5 hinged blade-lock + sparks -> 3.04s (73 frames, BP-184 cap) LTX impact clip.
- Total LTX drops from 21.0s (v1/v2 VIDEO_3D lane) down to 3.04s (73 frames = $0.049 plain / $0.074 retry-buffered).
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.blender import j5_action_rig, j5_limits, j5_minute
from explainer_engine.standards import sourced_rules as SR

TARGET_S = 60.0
ACTION_CAP_S = float(SR.T("BP-184", "action_ltx_clip_max_s"))
EPISODE_SHARE_MAX = float(SR.T("BP-184", "episode_ltx_share_max"))


def build_v3_plan() -> list[dict]:
    """Build the one-minute, 60.0-second v3 plan with explicit method and LTX seconds per shot."""
    base = [dict(s) for s in j5_minute.PLAN]
    v3: list[dict] = []
    for s in base:
        shot = dict(s)
        name = shot["name"]
        if name == "M1_column_wide":
            shot.update({
                "crowd_planes": 3,
                "bob_freq_hz": 1.6,
                "bob_amp_px": 4.5,
                "plane_speed_ratio": 1.45,
                "parallax_factor": 0.06,
            })
        elif name == "M2_drummer":
            shot.update({
                "action_kind": "drummer",
                "hinged_prop": "drumsticks",
                "hinge_angle_deg": 18.0,
                "punch_scale": 1.45,
                "axial_punch_in": True,
            })
        elif name == "M3_commander_leads":
            shot.update({
                "action_kind": "commander_leads",
                "hinged_prop": "cloak_and_banner",
                "hinge_angle_deg": 15.0,
                "crowd_planes": 3,
                "parallax_factor": 0.07,
            })
        elif name in ("T2_two_shot", "T3_commander", "T4_scout"):
            shot.update({"dialogue": True, "parallax_factor": 0.05})
        elif name == "T5_elder":
            shot.update({
                "dialogue": True,
                "hinged_prop": "staff_and_robe_relief",
                "hinge_angle_deg": 8.0,
                "parallax_factor": 0.05,
            })
        elif name == "B1_ford":
            shot.update({
                "crowd_planes": 4,
                "bob_freq_hz": 1.9,
                "bob_amp_px": 5.0,
                "plane_speed_ratio": 1.5,
                "parallax_factor": 0.07,
            })
        elif name == "B2_duel":
            shot.update({
                "action_kind": "duel",
                "requires_contact": True,
                "hinge_angle_deg": 20.0,
                "impact_flash_frames": 2,
                "camera_shake_amp_px": 7.0,
            })
        routed = j5_limits.route_action_shot(shot)
        shot["method"] = routed["method"]
        shot["ltx_seconds"] = routed["ltx_seconds"]
        shot["ltx_frames"] = routed["ltx_frames"]
        shot["route_reason"] = routed["reason"]
        v3.append(shot)
    return v3


def compare_v2_v3() -> dict:
    """Return a shot-by-shot and summary comparison between v2 (`j5_minute.PLAN`) and `v3`."""
    v2 = [dict(s) for s in j5_minute.PLAN]
    v3 = build_v3_plan()
    rows = []
    v2_video_s = 0.0
    v3_ltx_s = 0.0
    for s2, s3 in zip(v2, v3):
        sec = float(s2["seconds"])
        s2_ltx = sec if s2["lane"] == "VIDEO_3D" else 0.0
        v2_video_s += s2_ltx
        v3_ltx_s += float(s3["ltx_seconds"])
        rows.append({
            "name": s2["name"],
            "scene": s2["scene"],
            "seconds": sec,
            "v2_lane": s2["lane"],
            "v2_video_seconds": s2_ltx,
            "v3_method": s3["method"],
            "v3_ltx_seconds": s3["ltx_seconds"],
            "v3_ltx_frames": s3["ltx_frames"],
            "reason": s3["route_reason"],
        })
    return {
        "total_seconds": sum(r["seconds"] for r in rows),
        "v2_video_3d_seconds": round(v2_video_s, 2),
        "v3_ltx_seconds": round(v3_ltx_s, 2),
        "v3_ltx_share": round(v3_ltx_s / TARGET_S, 4),
        "episode_ltx_share_max": EPISODE_SHARE_MAX,
        "action_clip_cap_s": ACTION_CAP_S,
        "ltx_seconds_saved_vs_v2_video_lane": round(v2_video_s - v3_ltx_s, 2),
        "rows": rows,
    }


def _draw_ink_plate(shot: dict) -> np.ndarray:
    """Synthesize a clean 480x270 Ink Chronicle base plate for `shot` before passing to j5_action_rig."""
    sc = shot["scene"]
    palettes = {
        "title": ((234, 222, 196), (186, 168, 136)),
        "march": ((74, 88, 98), (52, 62, 54)),
        "tent": ((58, 46, 64), (118, 74, 48)),
        "ford": ((84, 98, 108), (64, 86, 72)),
        "campfire": ((36, 34, 48), (92, 54, 38)),
    }
    sky_col, ground_col = palettes.get(sc, ((80, 80, 90), (60, 60, 55)))
    canvas = np.zeros((270, 480, 3), dtype=np.uint8)
    for y in range(150):
        t = y / 150.0
        canvas[y, :] = [int(sky_col[k] * (1.0 - 0.25 * t)) for k in range(3)]
    for y in range(150, 270):
        t = (y - 150) / 120.0
        canvas[y, :] = [int(ground_col[k] * (0.85 + 0.15 * t)) for k in range(3)]

    pil = Image.fromarray(canvas)
    dr = ImageDraw.Draw(pil)
    name = shot["name"]
    if name == "M0_map":
        dr.rectangle([(25, 38), (455, 232)], outline=(45, 35, 25), width=3)
        dr.line([(55, 195), (155, 145), (275, 160), (415, 78)], fill=(175, 38, 28), width=5)
        for pt, lbl in [((55, 195), "CAMP A1"), ((275, 160), "ROAD"), ((415, 78), "FORD A3")]:
            dr.ellipse((pt[0] - 8, pt[1] - 8, pt[0] + 8, pt[1] + 8), fill=(185, 45, 30), outline=(20, 20, 20))
            dr.text((pt[0] - 22, pt[1] + 12), lbl, fill=(30, 25, 20))
    elif sc == "march":
        # Draw 3 depth tiers of marching ink silhouettes + banners
        tiers = [(135, 0.55, (42, 48, 54)), (162, 0.78, (32, 38, 44)), (195, 1.05, (22, 26, 30))]
        for tier, (y_base, scale, col) in enumerate(tiers):
            for x in range(35 + tier * 18, 445, int(44 * scale)):
                h_fig = int(42 * scale)
                w_fig = int(16 * scale)
                dr.rectangle([(x, y_base - h_fig), (x + w_fig, y_base)], fill=col, outline=(12, 12, 12))
                head_box = (x + 2, y_base - h_fig - int(11 * scale), x + w_fig - 2, y_base - h_fig)
                dr.ellipse(head_box, fill=col, outline=(12, 12, 12))
                dr.line([(x + w_fig, y_base - h_fig - 18), (x + w_fig + 6, y_base)], fill=(20, 20, 20), width=2)
        if name == "M3_commander_leads":
            dr.polygon([(195, 95), (285, 95), (305, 235), (175, 235)], fill=(165, 36, 32), outline=(15, 15, 15))
            dr.ellipse((220, 58, 260, 98), fill=(95, 98, 105), outline=(15, 15, 15))
    elif sc == "tent":
        dr.polygon([(40, 155), (145, 65), (250, 155)], fill=(215, 205, 185), outline=(25, 25, 25))
        dr.polygon([(270, 155), (375, 72), (460, 155)], fill=(195, 185, 168), outline=(25, 25, 25))
        dr.polygon([(215, 195), (240, 145), (265, 195)], fill=(245, 155, 45), outline=(185, 65, 20))
        if "H1" in shot["subject"] or name == "T2_two_shot":
            dr.rectangle([(95, 92), (175, 232)], fill=(155, 38, 34), outline=(15, 15, 15))
            dr.ellipse((112, 54, 158, 96), fill=(215, 185, 155), outline=(15, 15, 15))
        if "H2" in shot["subject"] or name == "T2_two_shot":
            dr.rectangle([(305, 102), (375, 232)], fill=(48, 105, 58), outline=(15, 15, 15))
            dr.ellipse((318, 66, 360, 104), fill=(222, 192, 162), outline=(15, 15, 15))
        if name == "T5_elder":
            dr.polygon([(195, 95), (285, 95), (298, 235), (182, 235)], fill=(48, 76, 132), outline=(15, 15, 15))
            dr.ellipse((218, 56, 262, 98), fill=(225, 205, 185), outline=(15, 15, 15))
            dr.line([(295, 48), (282, 235)], fill=(115, 78, 42), width=5)
    elif sc == "ford":
        dr.rectangle([(0, 175), (480, 228)], fill=(68, 108, 132), outline=(35, 55, 70))
        if name == "B1_ford":
            for x in range(25, 210, 24):
                dr.rectangle([(x, 125), (x + 14, 195)], fill=(155, 42, 36), outline=(15, 15, 15))
            for x in range(270, 455, 24):
                dr.rectangle([(x, 125), (x + 14, 195)], fill=(45, 75, 135), outline=(15, 15, 15))
        else:
            dr.polygon([(125, 95), (205, 95), (218, 232), (112, 232)], fill=(165, 38, 34), outline=(15, 15, 15))
            dr.polygon([(275, 102), (345, 102), (355, 232), (265, 232)], fill=(48, 105, 58), outline=(15, 15, 15))
            dr.line([(185, 135), (295, 85)], fill=(235, 238, 245), width=4)
            dr.line([(295, 138), (195, 82)], fill=(235, 238, 245), width=4)
    elif sc == "campfire":
        if name != "F3_title_card":
            dr.polygon([(210, 215), (240, 138), (270, 215)], fill=(248, 162, 42), outline=(195, 68, 22))
            dr.rectangle([(125, 105), (195, 232)], fill=(145, 36, 32), outline=(15, 15, 15))
        else:
            dr.rectangle([(60, 65), (420, 205)], outline=(215, 195, 145), width=2)
            dr.text((135, 122), "INK CHRONICLE - END OF PART 1", fill=(238, 228, 205))
    return np.array(pil)


def build_v3_contact_sheet(images_dir: Path | None, out_path: Path) -> Path:
    """Render a 15-panel (5x3, 1440x1350) annotated contact sheet (`contact_v3.png`) for v3 of the 1-minute film."""
    plan = build_v3_plan()
    panels: list[np.ndarray] = []
    for s in plan:
        base = _draw_ink_plate(s)
        m = s["method"]
        if m == "J5_BILLBOARD_CROWD":
            base = j5_action_rig.render_billboard_crowd_frame(
                base,
                t_sec=1.2,
                n_planes=int(s.get("crowd_planes", 3)),
                rain=(s["scene"] == "march"),
                water_splash=(s["scene"] == "ford"),
            )
        elif m == "J5_HINGED_RIG":
            base = j5_action_rig.render_hinged_action_frame(
                base, angle_deg=float(s.get("hinge_angle_deg", 14.0)), slash_smear=False
            )
        elif m == "HYBRID_J5_HINGE_PLUS_LTX_IMPACT":
            base = j5_action_rig.render_hinged_action_frame(
                base, angle_deg=18.0, slash_smear=True, shake_px=4.0
            )
        elif m in ("J5_RELIEF_CAM", "J5_DIALOGUE_CARD"):
            base = j5_action_rig.render_depth_relief_frame(base, yaw_deg=4.0, push_zoom=1.06)

        pil_tile = Image.fromarray(base)
        dr = ImageDraw.Draw(pil_tile)
        dr.rectangle([(0, 0), (480, 30)], fill=(18, 18, 22))
        dr.rectangle([(0, 240), (480, 270)], fill=(18, 18, 22))
        dr.rectangle([(0, 0), (479, 269)], outline=(75, 75, 82), width=1)
        badge_col = (205, 48, 38) if s["ltx_seconds"] > 0 else (36, 138, 78)
        dr.rectangle([(352, 4), (474, 25)], fill=badge_col)
        dr.text((8, 8), f"{s['name']} ({s['seconds']}s | {s['scene']})", fill=(245, 245, 245))
        dr.text((360, 8), f"LTX: {s['ltx_seconds']}s", fill=(255, 255, 255))
        dr.text((8, 247), f"v3: {s['method']} (v2: {s['lane']})", fill=(225, 212, 178))
        panels.append(np.array(pil_tile))

    grid_rows = [np.concatenate(panels[r * 3:(r + 1) * 3], axis=1) for r in range(5)]
    full_sheet = np.concatenate(grid_rows, axis=0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(full_sheet).save(out_path, format="PNG")
    return out_path
