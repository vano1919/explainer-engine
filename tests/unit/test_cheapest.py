"""D-133 (the creator 2026-11-13 07:00 UTC): every paid run takes the cheapest known combination, checked by the PreToolUse
Bash hook and again by the worker's own entrypoints. Rules CH-01..CH-06 in docs/CLOUD_RUNBOOK.md."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from explainer_engine.cloud import cheapest as C
from explainer_engine.cloud import hooks as H
from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

LTX = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"
GO = "cmsg_01AbC:a1b2c3d4e5f6"
SCENE = C.SCENES_DIR / "battle_2026-11-12.json"
LAUNCH = L.load_launch()


def _spec(**kw):
    scene = json.loads(SCENE.read_text())
    sha = hashlib.sha256(SCENE.read_bytes()).hexdigest()
    shots = [s["shot_id"] for s in scene["shots"]]
    spec = {"shot_id": shots[0], "plan_sha256": sha, "width": 1280, "height": 704, "fps": 24,
            "chain": [{"shot_id": s} for s in shots[1:]]}
    spec.update(kw)
    return spec


def _write(tmp_path, spec):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    return p


def test_the_basis_is_the_creators_word_and_the_measured_rows():
    b = C.basis()
    assert b["decided"]["message_id"] == "cmsg_01Hnu5zB86sjUj5GtTgaUkPWK39gkFmq9K2RUuKFaBEx9g"
    rows = {(r["model"], r["size"]): r["gen_usd_per_s"] for r in b["video_measured"]["rows"]}
    ltx = rows[("LTX-2.5 distilled", "1280x704@24")]
    assert all(v > ltx for (m, _), v in rows.items() if not m.startswith("LTX"))   # every other open model costs more


def test_the_committed_launch_passes_and_each_launch_rule_has_its_refusal():
    assert C.launch_problems(LAUNCH) == []
    assert [r for r, _ in C.launch_problems(dict(LAUNCH, runner="cli"))] == ["CH-01"]
    bad = copy.deepcopy(LAUNCH)
    bad["native"]["use"] = [768, 448]
    assert [r for r, _ in C.launch_problems(bad)] == ["CH-02"]
    assert [r for r, _ in C.launch_problems(dict(LAUNCH, scaledown_window_s=30))] == ["CH-04"]


def test_the_worker_preflight_refuses_the_cli_runner():
    with pytest.raises(SystemExit, match="CH-01"):
        L.preflight(dict(LAUNCH, runner="cli"))


def test_a_scene_spec_in_one_container_passes_the_hook(tmp_path):
    p = _write(tmp_path, _spec())
    assert H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job {p}", env={}) is None


def test_a_launch_per_clip_or_a_spec_from_no_scene_is_refused(tmp_path):
    one = _write(tmp_path, _spec(chain=[]))
    why = H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job {one}", env={})
    assert "CH-03" in why and "one" in why
    none = _write(tmp_path, _spec(plan_sha256="0" * 64))
    assert "CH-03" in H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job {none}", env={})
    assert "CH-03" in H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job missing.json", env={})


def test_a_clip_above_or_below_the_native_size_is_refused(tmp_path):
    for w, h in ((2560, 1408), (768, 448)):
        p = _write(tmp_path, _spec(width=w, height=h))
        assert "CH-02" in H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job {p}", env={})


def test_the_creators_message_waives_only_the_rule_it_names(tmp_path):
    one = _write(tmp_path, _spec(chain=[]))
    ok = f"EE_MODAL_GO={GO} EE_CHEAPEST_WAIVE=cmsg_01X:CH-03 modal run {LTX}::main --job {one}"
    assert H.modal_refusal(ok, env={}) is None
    big = _write(tmp_path, _spec(chain=[], width=2560))
    still = f"EE_MODAL_GO={GO} EE_CHEAPEST_WAIVE=cmsg_01X:CH-03 modal run {LTX}::main --job {big}"
    assert "CH-02" in H.modal_refusal(still, env={})
    assert C.waived("", env={"EE_CHEAPEST_WAIVE": "someone:CH-03"}) == (None, set())


def test_paid_pictures_only_on_the_batch_tier(tmp_path):
    ok = f"EE_PICTURES_GO=x python -m explainer_engine.training.pods.ltx.scene_pictures submit {SCENE} heroes"
    assert C.picture_refusal(ok, env={}) is None
    scene = json.loads(SCENE.read_text())
    scene["pictures"]["tier"] = "standard"
    p = tmp_path / "scene.json"
    p.write_text(json.dumps(scene))
    cmd = f"python -m explainer_engine.training.pods.ltx.scene_pictures submit {p} heroes"
    assert "CH-05" in C.picture_refusal(cmd, env={})
    assert H.pre_bash({"tool_input": {"command": cmd}}) == 2
    assert C.picture_refusal("python -m explainer_engine.training.pods.ltx.scene_pictures estimate x.json", env={}) is None


def test_the_rules_have_one_home_in_the_cloud_runbook():
    text = (Path(__file__).parents[2] / "docs" / "CLOUD_RUNBOOK.md").read_text()
    for r in ("CH-01", "CH-02", "CH-03", "CH-04", "CH-05", "CH-06"):
        assert f"| {r} |" in text
