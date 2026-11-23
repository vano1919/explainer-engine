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


def test_a_scene_spec_in_one_container_passes_the_hook(tmp_path, paid_offer):
    p = _write(tmp_path, _spec())
    offer = paid_offer("main")                                   # CH-07: the priced offer he was shown
    assert H.modal_refusal(f"EE_MODAL_GO={GO} EE_PAID_OFFER={offer} modal run {LTX}::main --job {p}", env={}) is None


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


def test_the_creators_message_waives_only_the_rule_it_names(tmp_path, word, paid_offer):
    one = _write(tmp_path, _spec(chain=[]))
    ok = f"EE_MODAL_GO={GO} EE_PAID_OFFER={paid_offer('main')} EE_CHEAPEST_WAIVE=cmsg_01X:CH-03 modal run {LTX}::main --job {one}"
    word("CH-03", "cmsg_01X")
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


# ---- weak points closed after the creator's check (2026-11-13 07:25 UTC, msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWDSaxGVbkbSGcfef2Lga1kM)

def test_a_waiver_without_his_recorded_word_waives_nothing(tmp_path, word):
    """An invented message id, a record for another message or rule, or a record older than an hour (a waiver left in the
    environment from an earlier run) waives nothing."""
    one = _write(tmp_path, _spec(chain=[]))
    cmd = f"EE_MODAL_GO={GO} EE_CHEAPEST_WAIVE=cmsg_01X:CH-03 modal run {LTX}::main --job {one}"
    assert "CH-03" in H.modal_refusal(cmd, env={})
    word("CH-03", "cmsg_01Y")                       # another message
    word("CH-02", "cmsg_01X")                       # another rule
    word("CH-03", "cmsg_01X", ago_s=(C.WAIVE_MINUTES + 1) * 60)   # stale
    assert "CH-03" in H.modal_refusal(cmd, env={})
    assert C.waived("", env={"EE_CHEAPEST_WAIVE": "cmsg_01X:CH-03"}) == ("cmsg_01X", set())
    word("CH-03", "cmsg_01X")
    assert C.waived("", env={"EE_CHEAPEST_WAIVE": "cmsg_01X:CH-03,CH-01"}) == ("cmsg_01X", {"CH-03"})


def test_a_waiver_record_names_one_rule():
    from explainer_engine.governance import records
    for target in ("*", "CH-*", "all"):
        with pytest.raises(ValueError, match="one rule"):
            records.add("cheapest_waive", target, "cmsg_1", "his words", root=Path("/nonexistent"))


def test_a_spec_the_check_cannot_read_is_refused(tmp_path):
    for bad in ([], "x", {"chain": ["s2"]}):
        p = _write(tmp_path, bad)
        assert "CH-03" in H.modal_refusal(f"EE_MODAL_GO={GO} modal run {LTX}::main --job {p}", env={})


def test_a_broken_money_check_refuses_a_paid_command_but_not_other_work(monkeypatch):
    def boom(*a, **k):
        raise KeyError("shots")
    monkeypatch.setattr(H, "modal_refusal", boom)
    assert H.pre_bash({"tool_input": {"command": f"EE_MODAL_GO={GO} modal run {LTX}::main --job s.json"}}) == 2
    assert H.pre_bash({"tool_input": {"command": "python -m explainer_engine.training.pods.ltx.scene_pictures submit s h"}}) == 2
    assert H.pre_bash({"tool_input": {"command": "ls -la"}}) == 0


@pytest.mark.parametrize("cmd", [
    'python -c "from explainer_engine.training.pods.ltx import modal_ltx_jobs as L\nwith L.app.run(): L.ltx_main.remote({}, L.LAUNCH)"',
    "python3 - <<'EOF'\nfrom explainer_engine.training.pods.ltx.modal_ltx_jobs import app, ltx_smoke\nwith app.run():\n    ltx_smoke.remote(j, l)\nEOF",
    f"python3 -c \"import subprocess; subprocess.run(['modal', 'run', '{LTX}::main', '--job', 's.json'])\"",
    f'"modal" run {LTX}::main --job s.json',
    f"python3 -c \"import os; os.system('modal run {LTX}::smoke')\"",
])
def test_a_worker_driven_from_python_or_a_quoted_modal_is_refused(cmd):
    assert H.worker_api_refusal(cmd)
    assert H.pre_bash({"tool_input": {"command": cmd}}) == 2


@pytest.mark.parametrize("cmd", [
    "python -m pytest -q tests/unit/test_cheapest.py",
    f"grep -n remote {LTX}",
    f"git add {LTX} && git commit -m 'D-133: container gate'",
    "python3 - <<'EOF'\ns = '``modal serve``'\nEOF",
])
def test_ordinary_work_on_the_workers_passes(cmd):
    assert H.worker_api_refusal(cmd) is None
    assert H.pre_bash({"tool_input": {"command": cmd}}) == 0


def test_the_wan_worker_refuses_its_paid_rungs_itself(word):
    from explainer_engine.training.pods.wan import modal_wan_jobs as W
    for entry in ("stage", "smoke", "main"):
        with pytest.raises(SystemExit, match="CH-06"):
            W.cheapest_gate(entry, env={})
    W.cheapest_gate("check", env={})
    word("CH-06", "cmsg_7")
    W.cheapest_gate("main", env={"EE_CHEAPEST_WAIVE": "cmsg_7:CH-06"})


def test_the_paid_container_checks_the_rules_before_any_model_loads(tmp_path):
    nat = L.native_spec(LAUNCH, L.SMOKE_JOB["seconds"])
    job = dict(L.SMOKE_JOB, fps=nat["fps"], width=nat["width"], height=nat["height"])
    baked = tmp_path / "launch.json"
    baked.write_text(json.dumps(LAUNCH))
    assert L.container_gate(job, LAUNCH, baked) == []
    cli = dict(LAUNCH, runner="cli")
    assert any("baked" in b for b in L.container_gate(job, cli, baked))
    assert any(b.startswith("CH-01") for b in L.container_gate(job, cli, tmp_path / "none.json"))
    assert L.container_gate(dict(job, cheapest_waive=["CH-01"]), cli, tmp_path / "none.json") == []
    big = dict(job, chain=[{"shot_id": "s2", "width": 2560, "height": 1408}])
    assert any(b.startswith("CH-02") and "s2" in b for b in L.container_gate(big, LAUNCH, baked))
    assert any(b.startswith("CH-04") for b in L.container_gate(job, dict(LAUNCH, scaledown_window_s=60), tmp_path / "none.json"))


def test_the_rule_files_change_only_on_the_creators_recorded_word(tmp_path):
    """The creator chose "კი, დაიცავი" (2026-11-13 07:49 UTC, card cmsg_01Hnu5zB86sjUj5GtTgaUkPWKgzrfKpKoKqsAC7dV9CAbW): the
    rules and their basis are protected files, like config/spend_caps.json."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from _gov import make_repo
    from explainer_engine.governance import hooks as G
    root = Path(__file__).parents[2]
    rels = ("explainer_engine/cloud/cheapest.py", "explainer_engine/cloud/cheapest.json",
            "explainer_engine/training/pods/ltx/launch.json")
    assert {C.BASIS_PATH.resolve(), Path(C.__file__).resolve(), L.LAUNCH_PATH.resolve()} == {(root / r).resolve() for r in rels}
    repo = make_repo(tmp_path / "r", git=True)
    for rel in rels:
        assert G.load(root)["protected_files"][rel] == 60
        assert G.load(repo)["protected_files"][rel] == 60
        assert G.pre_write({"tool_name": "Edit", "tool_input": {"file_path": str(repo / rel)}}, repo) == 2
        assert G.pre_bash({"tool_input": {"command": f"sed -i 's/5/60/' {rel}"}}, repo) == 2
        assert G.pre_bash({"tool_input": {"command": f"cat {rel}"}}, repo) == 0
