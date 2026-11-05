"""ICW-01 RW-18 (D-96, D-111, BP-175): the Blender job types exist empty (measured by ICW-09, never typed) and the Blender binary
is pinned by version and archive sha256; the LTX/Qwen pins are marked legacy (D-105)."""
import json
import re
from pathlib import Path

from explainer_engine.cloud import pins as P
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_blender_frame_job_types_exist_and_are_empty():
    jobs = json.loads((ROOT / "config" / "job_speeds.json").read_text(encoding="utf-8"))["jobs"]
    blender = {k: v for k, v in jobs.items() if k.startswith("blender_frame_")}
    assert set(blender) == {"blender_frame_eevee_fast_1440", "blender_frame_eevee_full_1440", "blender_frame_cycles_hero_1440"}
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


def test_ltx_and_qwen_pins_are_marked_legacy():
    models = P.load()["models"]
    for key in ("keyframe", "keyframe_angles", "video_ltx", "video_wan", "video_ltx_layout_lora"):
        assert models[key].get("legacy") is True, key
