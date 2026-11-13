"""v4.3 P9 (Q10 answer A, D-131): the old era's tools stay as code but refuse inside a v4.3 episode; outside one they still run
for the episodes made before 2026-11-12."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from explainer_engine.core.errors import ConfigError
from explainer_engine.episode import retired

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def episode(tmp_path):
    ep = tmp_path / "ep_x"
    (ep / "production").mkdir(parents=True)
    (ep / "episode.json").write_text(json.dumps({"schema": "episode_manifest/1", "episode_id": "ep_x"}))
    return ep


def test_every_retired_tool_names_existing_entry_points_and_a_replacement():
    data = retired.load()
    assert set(data["tools"]) == {"qwen_image", "xworld_lora", "ltx", "blender_scene", "runpod", "legacy_paint",
                                  "cinematic_image_animator"}
    for name, t in data["tools"].items():
        assert t["replacement"] and t["entry"], name
        for e in t["entry"]:
            assert (ROOT / e).exists(), (name, e)


@pytest.mark.parametrize("tool", ["qwen_image", "xworld_lora"])
def test_qwen_and_its_lora_are_retired_everywhere(tool, episode, tmp_path):
    """The creator, 2026-11-12 14:01 UTC (final audit section 7, answer 4; C3): no Qwen exception, the style rounds too."""
    with pytest.raises(ConfigError, match="retired everywhere"):
        retired.refuse(tool, tmp_path / "style_round", env={}, cwd=tmp_path)
    with pytest.raises(ConfigError, match="retired everywhere"):
        retired.refuse(tool, episode / "production" / "out", env={}, cwd=tmp_path)


def test_the_hook_refuses_a_qwen_worker_launch_everywhere():
    from explainer_engine.cloud import hooks as H
    for f in ("modal_qwen_jobs_v15.py", "modal_qwen_jobs_v3.py", "modal_sa_test.py"):
        cmd = f"EE_MODAL_GO=cmsg_1 modal run explainer_engine/training/pods/p15/{f}::main"
        assert "retired everywhere" in (H.modal_refusal(cmd, env={}) or ""), f
    for g in retired.load()["tools"]["qwen_image"]["workers_glob"]:
        assert list(ROOT.glob(g)), g


@pytest.mark.parametrize("tool", ["ltx", "blender_scene", "runpod", "legacy_paint", "cinematic_image_animator"])
def test_a_retired_tool_refuses_inside_a_v43_episode_and_runs_outside(tool, episode, tmp_path):
    with pytest.raises(ConfigError, match="retired for a v4.3 episode"):
        retired.refuse(tool, episode / "production" / "out", env={}, cwd=tmp_path)
    with pytest.raises(ConfigError, match="Nothing was started"):
        retired.refuse(tool, env={"EXPLAINER_EPISODE": str(episode)}, cwd=tmp_path)
    with pytest.raises(ConfigError):
        retired.refuse(tool, env={}, cwd=episode / "production")
    retired.refuse(tool, tmp_path / "old_job", env={}, cwd=tmp_path)   # an older episode's folder: allowed


def test_a_folder_with_an_older_manifest_is_not_v43(tmp_path):
    (tmp_path / "episode.json").write_text(json.dumps({"schema": "something_else/1"}))
    assert retired.v43_episode_of(tmp_path) is None
    with pytest.raises(ValueError, match="unknown retired tool"):
        retired.refuse("comfyui", env={}, cwd=tmp_path)


def test_the_runners_g1_names_a_retired_route():
    doc = {"shots": [{"shot_id": "S1", "route": "video"}, {"shot_id": "S2", "route": "J5"},
                     {"shot_id": "S3", "generation_mode": "ltx"}]}
    assert retired.retired_routes_in(doc) == ["S2: route J5", "S3: generation_mode ltx"]
    assert "no_retired_route" in (ROOT / "explainer_engine/episode/run.py").read_text()


def test_the_paint_run_and_the_blender_render_refuse_inside_an_episode(episode, monkeypatch, tmp_path):
    from explainer_engine.production import paint
    monkeypatch.setattr(paint, "_load", lambda a: ({}, {}, episode / "production" / "paint", []))
    with pytest.raises(ConfigError, match="legacy_paint"):
        paint.cmd_run(types.SimpleNamespace(script=None, run=str(tmp_path / "run.json")))
    from explainer_engine.training.pods import blender_render
    with pytest.raises(ConfigError, match="blender_scene"):
        blender_render.render("job.json", None, episode / "production" / "j5", tmp_path)


def test_the_runpod_create_refuses_inside_an_episode(episode, monkeypatch):
    from explainer_engine.cloud import runpod
    monkeypatch.setattr(runpod, "create_flag_problems", lambda rest: [])
    monkeypatch.chdir(episode)
    with pytest.raises(SystemExit, match="retired for a v4.3 episode"):
        runpod.main(["create", "--script", "x.sh", "--yes"])


def test_the_qwen_and_ltx_launchers_check_the_era_in_their_preflight():
    for name, tool in (("modal_ltx_jobs_v1.py", "ltx"), ("modal_qwen_jobs_v15.py", "qwen_image")):
        src = (ROOT / "explainer_engine/training/pods/p15" / name).read_text()
        pre = src[src.index("def preflight():"):]
        pre = pre[:pre.index("\n\n")]
        assert f'retired.refuse("{tool}")' in pre, name


def test_claude_md_states_the_v43_method_first():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    head = text[:text.index("## Commands")]
    assert head.startswith("# v4.3 episode-first (D-131)")
    for want in ("Retired, not deleted (Q10, D-131)", "config/retired_era.json", "zero approved budget", "10 % `map_action`",
                 "30 % `still_25d`", "60 % `wan`", "python -m explainer_engine.episode run"):
        assert want in head, want


def test_the_archive_animator_refuses_inside_an_episode(episode, tmp_path):
    from explainer_engine.production import cinematic_image_animator as CIA
    with pytest.raises(ConfigError, match="cinematic_image_animator"):
        CIA.render_cinematic_25d_clip_from_image({"shot_id": "S1"}, tmp_path / "p.png", episode / "production" / "c.mp4")


def test_no_retired_tool_is_on_the_v43_active_path():
    """P10's free first check of the OR-34 audit: the runner, the Wan adapter and the Wan worker import no retired entry module
    (statically, lazy imports of the v4.3 packages included); read-only data is listed with its reason, apart."""
    ap = retired.active_path()
    assert "explainer_engine.episode.run" in ap and "explainer_engine.production.layers25d" in ap and len(ap) > 50
    assert retired.retired_on_active_path() == []
    assert set(retired.load()["loaded_not_used"]) <= set(ap)


def test_the_scan_finds_a_retired_import():
    hits = retired.retired_on_active_path(roots=("explainer_engine.production.paint",))
    assert any(h.startswith("explainer_engine.production.paint <- root") for h in hits)
