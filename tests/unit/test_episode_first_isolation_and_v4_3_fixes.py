"""Unit & Integration Test Suite for Explainer Engine V4.3 Episode-First Rebuild (Sections 13.1 - 13.6)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from explainer_engine.assets import library as asset_lib
from explainer_engine.audio import acoustics, dropouts, sound_director
from explainer_engine.audio.environmental_sound_design import (
    render_continuous_environmental_soundscape,
    validate_narration_source_file,
)
from explainer_engine.audio.sfx_planner import (
    build_shot_sound_design_metadata,
    filter_sound_events_for_era,
)
from explainer_engine.edit.cinematic_transitions import (
    plan_episode_cinematic_transitions,
)
from explainer_engine.episode.context import (
    EpisodeIsolationError,
    EpisodeResolver,
    load_episode_context,
    validate_asset_compatibility,
)
from explainer_engine.maps import geo, plate, render as map_render, timeline as map_tl
from explainer_engine.production import cinematic_image_animator as CIA, parallax as PAR

REPO_ROOT = Path(__file__).resolve().parents[2]
EP_TOBA_DIR = REPO_ROOT / "episodes" / "ep_toba"
EP_WATERLOO_DIR = REPO_ROOT / "episodes" / "ep_waterloo"


# ==============================================================================
# 13.1 EPISODE ISOLATION TESTS
# ==============================================================================

def test_episode_context_loads_and_locks_to_ep_toba():
    ctx = load_episode_context(EP_TOBA_DIR)
    resolver = EpisodeResolver(ctx)
    assert ctx.episode_id == "ep_toba"
    assert ctx.era_id == "prehistoric_pleistocene"
    assert "1815_waterloo" in ctx.forbidden_era_tags
    assert "waterloo" in ctx.forbidden_semantic_tokens

    script_path = resolver.resolve_path("planning/production_script_2min.json")
    assert script_path.is_file()


def test_cross_episode_path_escape_is_rejected():
    ctx = load_episode_context(EP_TOBA_DIR)
    resolver = EpisodeResolver(ctx)
    with pytest.raises(EpisodeIsolationError):
        resolver.resolve_path("../ep_waterloo/episode.json")
    with pytest.raises(EpisodeIsolationError):
        resolver.resolve_path(EP_WATERLOO_DIR / "episode.json")


def test_incompatible_era_and_waterloo_assets_rejected_for_toba():
    ctx = load_episode_context(EP_TOBA_DIR)
    waterloo_asset = {
        "asset_id": "REF_01_Battlefield_Chiaroscuro_Anchor",
        "episode_scope": "ep_waterloo",
        "historical_period": "1815_waterloo",
        "era_tags": ["1815_waterloo", "napoleonic_19th_century"],
        "subject": "Waterloo battlefield cavalry charge",
        "shared_ok": False,
    }
    ok, reason = validate_asset_compatibility(ctx, waterloo_asset)
    assert ok is False
    assert "Cross-episode contamination blocked" in reason or "Anachronistic" in reason


def test_asset_library_find_for_episode_prevents_cross_contamination():
    ctx = load_episode_context(EP_TOBA_DIR)
    mock_lib = {
        "schema": "asset_library/2",
        "items": [
            {
                "id": "toba_forager_01",
                "kind": "image",
                "tags": ["prehistoric", "toba"],
                "usable": True, "approval": {"status": "approved"}, "licence": {"commercial_ok": True},
                "episode_scope": "ep_toba",
                "historical_period": "prehistoric_pleistocene",
                "era_tags": ["prehistoric_pleistocene", "74000_bce"],
                "subject": "74,000 BCE Pleistocene survivor in volcanic ash",
                "shared_ok": False,
            },
            {
                "id": "waterloo_wellingtons_ridge",
                "kind": "image",
                "tags": ["waterloo", "battlefield"],
                "usable": True, "approval": {"status": "approved"}, "licence": {"commercial_ok": True},
                "episode_scope": "ep_waterloo",
                "historical_period": "1815_waterloo",
                "era_tags": ["1815_waterloo", "napoleonic_19th_century"],
                "subject": "1815 Waterloo infantry square and French cavalry",
                "shared_ok": False,
            },
        ],
    }
    toba_results = asset_lib.find_for_episode(ctx, lib=mock_lib)
    assert len(toba_results) == 1
    assert toba_results[0]["id"] == "toba_forager_01"


def test_ep_toba_workspace_has_zero_contaminated_assets():
    lock_doc = json.loads((EP_TOBA_DIR / "episode_lock.json").read_text(encoding="utf-8"))
    assert lock_doc["episode_id"] == "ep_toba"
    assert lock_doc["verified_assets_count"] >= 130
    assert lock_doc["cross_episode_bleed_possible"] is False
    reg_doc = json.loads((EP_TOBA_DIR / "planning" / "episode_asset_registry.json").read_text(encoding="utf-8"))
    for item in reg_doc.get("assets", []):
        p = str(item.get("file_path") or "").lower()
        assert "waterloo" not in p
        assert "napoleon" not in p
        assert "rothschild" not in p
        assert "ref_01_battlefield" not in p


# ==============================================================================
# 13.2 AUDIO TESTS
# ==============================================================================

def test_mount_toba_and_spear_never_trigger_cavalry_or_sword_clash():
    shot = {
        "shot_id": "S01_SH003",
        "segment_id": "S01",
        "episode_id": "ep_toba",
        "historical_period": "prehistoric_pleistocene",
        "location_id": "loc_mount_toba_caldera",
        "narrative_purpose": "Mount Toba erupts above the mountain ridge while a scout grips an obsidian spear and stone blade.",
        "action_start_state": "Scout climbs the mountain slope with a hafted flint spear.",
        "action_end_state": "Pyroclastic cloud rises over Mount Toba.",
        "target_duration_seconds": 5.0,
    }
    sd = build_shot_sound_design_metadata(shot, historical_period="prehistoric_pleistocene")
    assert "horse_hooves_gallop" not in sd["sound_events"]
    assert "cavalry_movement" not in sd["physical_actions"]
    assert "sword_metal_clash" not in sd["sound_events"]
    assert "stone_lithic_strike" in sd["sound_events"]
    assert "volcanic_explosion_debris" in sd["sound_events"]


def test_era_compatibility_table_blocks_anachronistic_sounds():
    events, blocked = filter_sound_events_for_era(
        ["horse_hooves_gallop", "sword_metal_clash", "page_flip", "wind_howl"],
        historical_period="prehistoric_pleistocene",
    )
    assert "horse_hooves_gallop" not in events
    assert "sword_metal_clash" not in events
    assert "page_flip" not in events
    assert "stone_lithic_strike" in events
    assert "stone_tablet_slide" in events
    assert len(blocked) == 3


def test_sfx_pack_forbidden_as_narration():
    with pytest.raises(ValueError, match="SFX_PACK_FORBIDDEN_AS_NARRATION"):
        validate_narration_source_file("G4_SFX_Footsteps_Ambience_Music_Pack.mp3")


def test_sound_director_detects_narration_stem_dropout_even_with_continuous_ambience():
    sr = acoustics.SR
    fps = 24
    total_frames = 72  # 3.0s
    total_samples = 3 * sr
    spine = {
        "fps": fps,
        "total_frames": total_frames,
        "words": [
            {"word": "supervolcano", "start_frame": 12, "end_frame": 36},  # 0.5s .. 1.5s
            {"word": "erupted", "start_frame": 40, "end_frame": 60},       # 1.67s .. 2.5s
        ],
    }
    manifest = {
        "fps": fps,
        "total_frames": total_frames,
        "scenes": [{"scene": "S01", "start_frame": 0, "end_frame": total_frames, "acoustic": "outdoor", "entry": "butt", "ir_seed": acoustics.seed_of("S01")}],
        "beds": [{"id": "rt01", "scene": "S01", "kind": "room_tone", "ref": "rt", "gain_db": -38.0, "start_frame": 0, "end_frame": total_frames}],
        "music": [],
        "spots": [],
        "vacuums": [],
        "dialogue": [],
    }
    t = np.arange(total_samples, dtype=np.float32) / sr
    amb = (0.05 * np.sin(2 * np.pi * 180.0 * t)).astype(np.float32)
    nar = np.zeros(total_samples, dtype=np.float32)
    nar[int(1.67 * sr):int(2.5 * sr)] = 0.25 * np.sin(2 * np.pi * 120.0 * t[int(1.67 * sr):int(2.5 * sr)])
    stems = {
        "narration": np.stack([nar, nar], axis=1),
        "ambience": np.stack([amb, amb], axis=1),
        "mix": np.stack([amb + nar, amb + nar], axis=1),
    }
    findings = sound_director._check_stems(manifest, spine, stems, {}, (0.5, 0.5))
    nar_findings = [f for f in findings if f["rule"] == "SD-02" and f["where"] == "narration"]
    assert len(nar_findings) == 1
    assert "supervolcano" in nar_findings[0]["detail"]


# ==============================================================================
# 13.3 GIS & SHADED-RELIEF MAP TESTS
# ==============================================================================

def test_dem_shaded_relief_generation_and_letterless_plate(tmp_path, monkeypatch):
    # v4.3 P4 (F6): the synthetic DEM with its hand-placed Toba terrain is gone; the relief is Natural Earth's raster.
    # A small fixture raster stands in for the 233 MB file (tests/unit/test_v43_map_actions.py covers the sampling).
    from explainer_engine.maps import relief
    rows, cols = np.mgrid[0:180, 0:360]
    Image.fromarray((128 + 100 * np.sin(cols / 9.0) * np.cos(rows / 7.0)).astype(np.uint8), "L").save(tmp_path / relief.RASTER_NAME)
    (tmp_path / "SR_HR.tfw").write_text("1.0\n0.0\n0.0\n-1.0\n-179.5\n89.5\n")
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path))
    relief._load.cache_clear()
    view = geo.View(98.88, 2.68, 1200.0, 320, 180)
    hs = relief.sample(view)
    assert hs.shape == (180, 320)
    assert 0.0 <= float(hs.min()) < float(hs.max()) <= 1.0

    saved = plate.save_plate(view, tmp_path, shaded_relief=True)
    assert saved.is_file()
    assert plate.spec_hash(view, shaded_relief=True)[:16] in saved.name
    relief._load.cache_clear()


def test_toba_gis_map_specs_validate_and_render(tmp_path, monkeypatch):
    # v4.3 P4 (F6): the plate needs Natural Earth's raster; CI has no download, so a 1-degree fixture raster stands in
    from explainer_engine.maps import relief
    rows, cols = np.mgrid[0:180, 0:360]
    Image.fromarray((128 + 100 * np.sin(cols / 9.0) * np.cos(rows / 7.0)).astype(np.uint8), "L").save(tmp_path / relief.RASTER_NAME)
    (tmp_path / "SR_HR.tfw").write_text("1.0\n0.0\n0.0\n-1.0\n-179.5\n89.5\n")
    monkeypatch.setenv("EXPLAINER_RELIEF_DIR", str(tmp_path))
    relief._load.cache_clear()
    for sid in ("S01_SH008", "S02_SH001", "S02_SH010"):
        spec, spine = map_render.build_toba_gis_map_spec(sid, width=320, height=180, total_frames=48)
        assert map_render.validate_payload(spec) == []
        assert map_render.route_findings(spec) == []
        tl, clock = map_tl.build(spec, spine, trigger_word_index=0, duration_frames=48)
        f0 = map_render.render_frame(spec, tl, clock, 0, ss=1, base_dir=tmp_path)
        f40 = map_render.render_frame(spec, tl, clock, 40, ss=1, base_dir=tmp_path)
        assert f0.size == (320, 180)
        assert f40.size == (320, 180)
        assert not np.array_equal(np.asarray(f0), np.asarray(f40))


# ==============================================================================
# 13.4 CAMERA & MOTION TESTS
# ==============================================================================

def test_multi_axis_parallax_and_smoothstep_camera_bounds():
    img = Image.fromarray(np.random.default_rng(7).integers(20, 220, (180, 320, 3), dtype=np.uint8), mode="RGB")
    depth, face_mask = PAR.estimate_synthetic_depth_and_face_safe_mask(img, protect_center_character=True)
    assert depth.shape == (180, 320)
    assert face_mask.shape == (180, 320)

    for preset in CIA.CAMERA_PRESETS:
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            box, sx, sy, ax, ay = CIA.compute_camera_trajectory_box(preset, u, width=320, height=180, focal_xy=(0.55, 0.45))
            x0, y0, x1, y1 = box
            assert 0.0 <= x0 < x1 <= 320.0
            assert 0.0 <= y0 < y1 <= 180.0
            shifted = PAR.shift(img, depth, box, (320, 180), u, amp=ax, sign=sx, dy_amp=ay, sign_y=sy)
            assert shifted.size == (320, 180)


def test_blender_render_shot_has_non_rig_dof_keyframing():
    src = (REPO_ROOT / "explainer_engine" / "blender" / "bpy" / "render_shot.py").read_text(encoding="utf-8")
    assert 'data.dof.keyframe_insert("focus_distance"' in src
    assert 'data.dof.keyframe_insert("aperture_fstop"' in src
    assert 'ee_dof_focus_keyed' in src
    assert 'ee_dof_fstop_keyed' in src


# ==============================================================================
# 13.5 TRANSITION TESTS
# ==============================================================================

def test_transitions_follow_ed04_and_eliminate_smoke_wipe_spam():
    script_doc = json.loads((EP_TOBA_DIR / "planning" / "production_script_2min.json").read_text(encoding="utf-8"))
    plans = plan_episode_cinematic_transitions(script_doc, fps=24, allow_decorative_wipes=False)
    assert len(plans) == len(script_doc["shots"]) - 1
    for p in plans:
        assert p["ed04_compliant"] is True
        assert p["transition_type"] != "atmospheric_smoke_ash_wipe"
        assert p["transition_type"] != "foreground_object_wipe"

    map_handoffs = [p for p in plans if p["from_shot_id"] in ("S01_SH008", "S02_SH001", "S02_SH010")]
    assert len(map_handoffs) == 3
    assert all(p["transition_type"] == "map_to_location_zoom_through" for p in map_handoffs)
