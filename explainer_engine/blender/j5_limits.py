"""Tool boundaries, data handoff contracts, and shot routing for LTX minimisation (BP-182, BP-183, BP-184; D-116).

Defines the hard capability limits of Python, Blender, FFmpeg, Qwen, and LTX, enforces them via sourced_rules.T,
and provides the deterministic shot decision rule ``route_action_shot(shot)``.
"""

from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

PARALLAX_FACTOR_MAX = float(SR.T("BP-182", "parallax_factor_max"))
RELIEF_YAW_MAX_DEG = float(SR.T("BP-182", "relief_yaw_max_deg"))
INPAINT_RADIUS_PX = int(SR.T("BP-182", "inpaint_radius_px"))
ARAP_DISP_FRAC_MAX = float(SR.T("BP-182", "arap_disp_frac_max"))
CPU_SEC_PER_FRAME_MAX = float(SR.T("BP-182", "cpu_sec_per_frame_max"))
PC_RX5700_SEC_PER_FRAME_MAX = float(SR.T("BP-182", "pc_rx5700_sec_per_frame_max"))

MIN_CROWD_PLANES = int(SR.T("BP-183", "min_crowd_planes"))
BOB_FREQ_BAND = list(SR.T("BP-183", "bob_freq_hz_band"))
BOB_AMP_PX_MAX = float(SR.T("BP-183", "bob_amp_px_max"))
PLANE_SPEED_RATIO_MIN = float(SR.T("BP-183", "plane_speed_ratio_min"))
HINGE_ANGLE_MAX_DEG = float(SR.T("BP-183", "hinge_angle_max_deg"))
IMPACT_FLASH_FRAMES_MAX = int(SR.T("BP-183", "impact_flash_frames_max"))
CAMERA_SHAKE_AMP_PX_MAX = float(SR.T("BP-183", "camera_shake_amp_px_max"))

ACTION_LTX_CLIP_MAX_S = float(SR.T("BP-184", "action_ltx_clip_max_s"))
CROWD_LTX_CLIP_MAX_S = float(SR.T("BP-184", "crowd_ltx_clip_max_s"))
EPISODE_LTX_SHARE_MAX = float(SR.T("BP-184", "episode_ltx_share_max"))
MOVING_LANE_MIN_SHARE = float(SR.T("BP-184", "moving_lane_min_share"))

TOOL_LIMITS = {
    "python": {
        "may_animate": [
            "2D vector maps, HUDs, charts, and title cards (route H)",
            "D-119 4x2 variant-sheet cell cutting, rigid upper-face alignment, and 55ms Rhubarb viseme cross-blending",
            "Colour/depth-masked local sinusoidal/procedural warps (water ripple, banner wave, flame flicker, rain)",
            "Hinged rigid-plus-feathered-joint rotation (<= 22 deg) and bounded ARAP handle warps (<= 6% card height)",
            "Telea/Navier-Stokes disocclusion edge inpainting (radius <= 4 px) on depth-sliced RGBA layers",
        ],
        "must_stop_at": [
            "Full-body skeletal retargeting of robed figures without visible leg separation (collapses mesh)",
            "Optical-flow / RIFE interpolation between dissimilar poses (melts bold black ink outlines)",
            "ARAP handle displacements > 6% of card height (rubber-sheet stretching of ink strokes)",
            "Camera yaw synthesis > 8.0 deg without multi-layer RGBA separation",
        ],
        "handoff_formats": ["layer_rgba.png (8-bit RGBA)", "depth_16bit.png", "arap_rig.json", "cues.json"],
        "enforced_by_rule": "BP-182",
    },
    "blender": {
        "may_animate": [
            "Workbench / EEVEE 2.5D depth-relief displacement from Depth-Anything-V2-Small maps (parallax <= 0.08)",
            "Multi-plane 2.5D emission card staging (equirectangular/plate backdrop + >= 3 depth-sliced crowd planes)",
            "3D perspective camera push-in, pan, truck, and subtle Dutch/impact shake",
            "3D clay/colour/depth/line control passes for J2/J4 LTX shots when LTX is strictly required",
        ],
        "must_stop_at": [
            "Final NPR / Freestyle toon rendering of 3D mannequins as the viewer-facing picture (abandoned per D-96)",
            "Cycles path tracing or heavy shaders exceeding 1.5 s/frame on 4-core CPU CI (0.4 s/frame on RX 5700)",
            "Unmasked background furniture not listed in the shot's in_shot manifest (Standing Order 14)",
        ],
        "handoff_formats": ["frames/%06d.png (16-bit/8-bit PNG)", "shot_manifest.json (j5_shot_plan/1)"],
        "enforced_by_rule": "BP-182, BP-183",
    },
    "ffmpeg": {
        "may_animate": [
            "Segment concatenation (hard cuts by default, D-116 / step 4c)",
            "Motivated scene-boundary dissolves (0.5-1.5 s, BP-179) and J/L audio-lead overlaps",
            "Lanczos upscale to 2560x1440 + Contrast Adaptive Sharpening (cas=0.4) + temporal grain",
            "EBU R128 loudness normalization to -14.0 LUFS (BP-50) with 6 dB dialogue ducking and 20ms fades",
        ],
        "must_stop_at": [
            "Dip-to-black transitions between dialogue or intra-scene shots (banned per creator order 19:14 UTC)",
            "Motion-interpolated slow-motion (`minterpolate`) on hand-inked animation (creates ghosted double lines)",
            "Flat 2D `zoompan` where a 3D depth-relief or multi-plane parallax camera is required",
        ],
        "handoff_formats": ["minute_j5_v3.mp4 (H.264/AAC, 24 fps, -14.0 LUFS)", "compare_contact.png"],
        "enforced_by_rule": "BP-50, BP-179, BP-181",
    },
    "qwen": {
        "may_animate": [
            "Viewer-facing artwork via Qwen-Image-2.1 + xworld_v2 LoRA (ck3000 @ 0.7): backdrops, hero sheets, props",
            "One 4x2 mouth/blink variant sheet per hero (D-119) for deterministic Python viseme swapping",
            "First-frame restyles of frustum-cleaned Blender stills (`in_shot` enforced) for J2/J4 clips",
        ],
        "must_stop_at": [
            "Frame-by-frame img2img video generation (causes severe flicker and identity drift, D-78)",
            "Prompts > 90 words on crowd/action keyframes or prompts containing camera/layout directives",
            "Redrawing hero identity from text without pinning the approved hero turnaround sheet (D-101)",
        ],
        "handoff_formats": ["hero_sheet.png", "variant_sheet_4x2.png", "first_frame_restyle.png"],
        "enforced_by_rule": "BP-165, D-119",
    },
    "ltx": {
        "may_animate": [
            "Short impact clips (2.0-3.04 s, 49-73 frames, BP-184) of close-range multi-limb weapon contact (duels)",
            "Short locomotion/clash clips (3.04-5.04 s, 73-121 frames) where visible legs cross uneven 3D terrain",
            "Continuous > 30-degree 3D body/head rotation that crosses between turnaround sheet angles",
        ],
        "must_stop_at": [
            "Any dialogue shot (100% handled by J5 2.5D cards + D-119 Rhubarb mouth swap at $0 LTX)",
            "Establishing shots, atmospheric holds, and single-hero reaction/pondering shots ($0 J5 relief cam)",
            "Wide marching columns where legs are small/occluded by dust/grass ($0 J5 3-plane billboard crowd)",
            "Unclipped 8-15 s single takes when a 1.96 s J5 setup + 3.04 s LTX impact cut achieves the beat",
        ],
        "handoff_formats": ["clip_ltx_1088p.mp4 (8k+1 frames, 24 fps -> FFmpeg Lanczos+CAS 1440p)"],
        "enforced_by_rule": "BP-139, BP-172, BP-184",
    },
}


def route_action_shot(shot: dict) -> dict:
    """Apply the Argon J5/LTX boundary decision rule to a single shot specification."""
    lane = str(shot.get("lane") or "").upper()
    kind = str(shot.get("action_kind") or shot.get("subject") or "").lower()
    sec = float(shot.get("seconds", 4.0))

    if lane == "HELPER" or kind in ("map", "end", "title"):
        return {
            "method": "HELPER",
            "ltx_seconds": 0.0,
            "ltx_frames": 0,
            "reason": "Pure Python 2D vector graphic / title card (0 LTX s)",
        }

    if shot.get("dialogue") or shot.get("motivation") in ("the elder speaks", "dialogue") or (
        lane == "VIDEO_3D" and str(shot.get("scene")) == "tent"
    ):
        return {
            "method": "J5_DIALOGUE_CARD",
            "ltx_seconds": 0.0,
            "ltx_frames": 0,
            "reason": (
                "Blender 2.5D hero cards + D-119 variant-sheet Rhubarb mouth swap + depth-relief robe/staff "
                "(0 LTX s)"
            ),
        }

    if "duel" in kind or shot.get("requires_contact"):
        ltx_s = min(sec, ACTION_LTX_CLIP_MAX_S)
        j5_s = round(max(0.0, sec - ltx_s), 2)
        return {
            "method": "HYBRID_J5_HINGE_PLUS_LTX_IMPACT",
            "ltx_seconds": ltx_s,
            "ltx_frames": 73,
            "j5_seconds": j5_s,
            "reason": (
                f"Multi-limb sword contact requires a {ltx_s}s (73f, BP-184 cap) LTX impact clip, "
                f"paired with a {j5_s}s J5 hinged blade-lock hold + sparks"
            ),
        }

    if kind in ("column", "armies", "crowd"):
        return {
            "method": "J5_BILLBOARD_CROWD",
            "ltx_seconds": 0.0,
            "ltx_frames": 0,
            "reason": (
                f"Multi-plane (>= {MIN_CROWD_PLANES} tiers) depth-sliced billboard crowd with phase-staggered "
                "marching bob, lateral parallax, and animated water/rain/banners (0 LTX s)"
            ),
        }

    if shot.get("hinged_prop") or kind in ("drummer", "commander_leads") or (
        lane == "VIDEO_3D" and str(shot.get("scene")) == "march"
    ):
        return {
            "method": "J5_HINGED_RIG",
            "ltx_seconds": 0.0,
            "ltx_frames": 0,
            "reason": (
                f"Hinged 2D cut-out articulation (<= {HINGE_ANGLE_MAX_DEG} deg arm/cloak/banner wave) + "
                "depth-relief camera push-in (0 LTX s)"
            ),
        }

    return {
        "method": "J5_RELIEF_CAM",
        "ltx_seconds": 0.0,
        "ltx_frames": 0,
        "reason": (
            f"Depth-Anything-V2 relief mesh camera (parallax <= {PARALLAX_FACTOR_MAX}) + "
            "procedural flame/smoke/rain ambience (0 LTX s)"
        ),
    }


def lint_limits(plan: list[dict]) -> list[dict]:
    """Check a shot plan against BP-182, BP-183, and BP-184 limits (returns REVIEW findings for hypotheses)."""
    findings: list[dict] = []
    total_s = sum(float(s.get("seconds", 0.0)) for s in plan) or 1.0
    total_ltx_s = 0.0
    moving_s = 0.0

    for s in plan:
        name = str(s.get("name", "<shot>"))
        parallax = float(s.get("parallax_factor", 0.06))
        if parallax > PARALLAX_FACTOR_MAX:
            findings.append({
                "rule": "BP-182",
                "severity": SR.level("BP-182"),
                "where": name,
                "detail": f"parallax_factor {parallax} > {PARALLAX_FACTOR_MAX} causes depth edge tearing",
            })
        yaw = abs(float(s.get("relief_yaw_deg", 0.0)))
        if yaw > RELIEF_YAW_MAX_DEG:
            findings.append({
                "rule": "BP-182",
                "severity": SR.level("BP-182"),
                "where": name,
                "detail": f"relief_yaw_deg {yaw} > {RELIEF_YAW_MAX_DEG} exceeds disocclusion inpaint limit",
            })
        arap = float(s.get("arap_disp_frac", 0.0))
        if arap > ARAP_DISP_FRAC_MAX:
            findings.append({
                "rule": "BP-182",
                "severity": SR.level("BP-182"),
                "where": name,
                "detail": f"arap_disp_frac {arap} > {ARAP_DISP_FRAC_MAX} stretches ink outlines",
            })
        cpu_spf = float(s.get("cpu_sec_per_frame", 1.0))
        if cpu_spf > CPU_SEC_PER_FRAME_MAX and float(s.get("pc_sec_per_frame", 0.2)) > PC_RX5700_SEC_PER_FRAME_MAX:
            findings.append({
                "rule": "BP-182",
                "severity": SR.level("BP-182"),
                "where": name,
                "detail": f"cpu_sec_per_frame {cpu_spf}s exceeds {CPU_SEC_PER_FRAME_MAX}s Workbench budget",
            })

        if s.get("method") == "J5_BILLBOARD_CROWD":
            planes = int(s.get("crowd_planes", MIN_CROWD_PLANES))
            if planes < MIN_CROWD_PLANES:
                findings.append({
                    "rule": "BP-183",
                    "severity": SR.level("BP-183"),
                    "where": name,
                    "detail": f"crowd_planes {planes} < {MIN_CROWD_PLANES} looks like a flat cardboard sheet",
                })
            bob_hz = float(s.get("bob_freq_hz", 1.6))
            if not (BOB_FREQ_BAND[0] <= bob_hz <= BOB_FREQ_BAND[1]):
                findings.append({
                    "rule": "BP-183",
                    "severity": SR.level("BP-183"),
                    "where": name,
                    "detail": f"bob_freq_hz {bob_hz} outside {BOB_FREQ_BAND}",
                })
            bob_px = float(s.get("bob_amp_px", 4.0))
            if bob_px > BOB_AMP_PX_MAX:
                findings.append({
                    "rule": "BP-183",
                    "severity": SR.level("BP-183"),
                    "where": name,
                    "detail": f"bob_amp_px {bob_px} > {BOB_AMP_PX_MAX}",
                })
            spd_ratio = float(s.get("plane_speed_ratio", 1.5))
            if spd_ratio < PLANE_SPEED_RATIO_MIN:
                findings.append({
                    "rule": "BP-183",
                    "severity": SR.level("BP-183"),
                    "where": name,
                    "detail": f"plane_speed_ratio {spd_ratio} < {PLANE_SPEED_RATIO_MIN}",
                })

        hinge_deg = abs(float(s.get("hinge_angle_deg", 0.0)))
        if hinge_deg > HINGE_ANGLE_MAX_DEG:
            findings.append({
                "rule": "BP-183",
                "severity": SR.level("BP-183"),
                "where": name,
                "detail": f"hinge_angle_deg {hinge_deg} > {HINGE_ANGLE_MAX_DEG} breaks joint seam",
            })
        flash_f = int(s.get("impact_flash_frames", 0))
        if flash_f > IMPACT_FLASH_FRAMES_MAX:
            findings.append({
                "rule": "BP-183",
                "severity": SR.level("BP-183"),
                "where": name,
                "detail": f"impact_flash_frames {flash_f} > {IMPACT_FLASH_FRAMES_MAX} (BP-23 flash safety)",
            })
        shake_px = float(s.get("camera_shake_amp_px", 0.0))
        if shake_px > CAMERA_SHAKE_AMP_PX_MAX:
            findings.append({
                "rule": "BP-183",
                "severity": SR.level("BP-183"),
                "where": name,
                "detail": f"camera_shake_amp_px {shake_px} > {CAMERA_SHAKE_AMP_PX_MAX}",
            })

        ltx_s = float(s.get("ltx_seconds", 0.0))
        total_ltx_s += ltx_s
        max_clip = CROWD_LTX_CLIP_MAX_S if s.get("subject") in ("armies", "crowd") else ACTION_LTX_CLIP_MAX_S
        if ltx_s > max_clip + 1e-6:
            findings.append({
                "rule": "BP-184",
                "severity": SR.level("BP-184"),
                "where": name,
                "detail": f"ltx_seconds {ltx_s}s exceeds cap {max_clip}s",
            })

        if s.get("method") not in ("HELPER", None):
            moving_s += float(s.get("seconds", 0.0))

    ltx_share = total_ltx_s / total_s
    if ltx_share > EPISODE_LTX_SHARE_MAX:
        findings.append({
            "rule": "BP-184",
            "severity": SR.level("BP-184"),
            "where": "episode",
            "detail": f"LTX share {ltx_share:.3f} exceeds BP-184 ceiling {EPISODE_LTX_SHARE_MAX}",
        })
    if (moving_s / total_s) < MOVING_LANE_MIN_SHARE:
        findings.append({
            "rule": "BP-184",
            "severity": SR.level("BP-184"),
            "where": "episode",
            "detail": f"moving share {moving_s / total_s:.3f} below {MOVING_LANE_MIN_SHARE}",
        })
    return findings
