"""ICW-01 RW-18 (D-96, D-111, BP-175): the Blender job types exist empty (measured by ICW-09, never typed) and the Blender binary
is pinned by version and archive sha256; the route pins (D-116) are active, the
retired ones stay legacy (D-105)."""
import json
import re
from pathlib import Path

from explainer_engine.cloud import pins as P
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_blender_frame_job_types_exist_and_are_empty():
    jobs = json.loads((ROOT / "config" / "job_speeds.json").read_text(encoding="utf-8"))["jobs"]
    blender = {k: v for k, v in jobs.items() if k.startswith("blender_frame_")}
    assert set(blender) == {"blender_frame_eevee_fast_1440", "blender_frame_eevee_full_1440",
                           "blender_frame_eevee_painterly_1440", "blender_frame_cycles_hero_1440"}
    assert all(v["unit"] == "frame" and v["rows"] == {} for v in blender.values())


def test_the_blender_pin_matches_bp175_and_names_both_archives_by_sha256():
    pins = P.load()
    b = pins["blender"]
    assert b["version"] == SR.T("BP-175", "blender_version") and b["series"] == SR.T("BP-175", "series")
    assert set(b["archives"]) == {"linux-x64", "macos-arm64"}
    for a in b["archives"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", a["sha256"]) and a["url"].startswith("https://download.blender.org/release/")
        assert f"blender-{b['version']}-" in a["url"]
    assert b["image"] is None and b["smoke_verified"] is False  # no pod image decided yet (ICW-04)


def test_the_route_pins_are_active_and_the_retired_ones_stay_legacy():
    """D-116 (2026-11-06): Qwen-Image-2.1 + xworld_v2 draw the look, LTX-2.5 + Layout-To-Render make J2, the Union-Control LoRA J4;
    the Edit-2511 angles LoRA and Wan stay legacy (D-105). Every active video pin is named by revision and file sha256."""
    models = P.load()["models"]
    for key in ("keyframe_angles", "video_wan"):
        assert models[key].get("legacy") is True, key
    for key in ("keyframe", "video_ltx", "video_ltx_layout_lora", "video_ltx_control"):
        assert models[key].get("legacy") is False, key
    assert models["loras"]["xworld_v2"].get("legacy") is False
    for key in ("video_ltx", "video_ltx_layout_lora", "video_ltx_control"):
        assert re.fullmatch(r"[0-9a-f]{40}", models[key]["revision"]) and re.fullmatch(r"[0-9a-f]{64}", models[key]["sha256"]), key
    # the control LoRA's base is recorded, not assumed: it is LTX-2.3, not the LTX-2.5 of video_ltx (an open step-3 item)
    assert models["video_ltx_control"]["base"] == "Lightricks/LTX-2.3" != models["video_ltx"]["id"]


def test_the_route_job_types_exist_unmeasured():
    jobs = json.loads((ROOT / "config" / "job_speeds.json").read_text(encoding="utf-8"))["jobs"]
    for key in ("ltx_clip_s_per_clip", "qwen_asset_s_per_image", "blender_25d_s_per_frame_pc"):
        assert jobs[key]["rows"] == {} and jobs[key]["measured"] is None, key
