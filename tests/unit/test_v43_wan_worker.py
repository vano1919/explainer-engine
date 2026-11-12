"""The Wan Modal worker (v4.3 plan P6.3, D-131, Fable audit 2026-11-12 fix 1): the v15 template's money rules on a pinned
launch file, the OR-37 ladder L0..L4 in order, the free preflight before the GO gate. Nothing here imports modal or sends a
call; the committed launch file has null pins (OR-22: the creator picks the model), so the worker cannot run as committed."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from explainer_engine.aivideo import wan_adapter as WA
from explainer_engine.cloud import modal_run as MR
from explainer_engine.training.pods.wan import modal_wan_jobs as WJ

SRC = Path(WJ.__file__)
PINNED = {"app_name": "ee-wan", "model_repo": "org/wan", "model_revision": "a" * 40, "model_files": {"m.safetensors": "b" * 64},
          "pipeline": "SomePipeline", "hf_out": "route_test/wan_out", "settings": {"steps": 30}, "gpu": "A100-80GB", "cpu": 8,
          "memory_gib": 64, "usd_per_h": 3.3872, "prices_date": "2026-11-07",
          "caps": {"smoke_usd": 0.25, "run_usd": 1.0, "cold_start_s": 120}}


def test_the_committed_launch_file_pins_nothing_so_nothing_runs():
    lf = json.loads((SRC.parent / "launch.json").read_text())
    assert lf["model_repo"] is None and lf["model_revision"] is None and lf["pipeline"] is None   # OR-22
    assert WJ.TIMEOUTS is None and WJ.launch_problems(lf)
    with pytest.raises(SystemExit, match="nothing was started"):
        WJ.preflight(lf)


def test_entrypoints_run_the_preflight_before_the_go_gate_and_the_ladder_gate():
    tree = ast.parse(SRC.read_text())
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for name, rung in (("smoke", "L3"), ("main", "L4")):
        found = [c for c in ast.walk(fns[name]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        calls = [c.func.id for c in sorted(found, key=lambda c: (c.lineno, c.col_offset))]   # source order
        assert calls.index("preflight") < calls.index("go_gate") < calls.index("ladder_gate"), name
        gate = next(c for c in ast.walk(fns[name]) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "ladder_gate")
        assert gate.args[0].value == rung
    for name, rung in (("check", "L1"), ("weights", "L2")):
        first = fns[name].body[0].value
        assert first.func.id == "ladder_gate" and first.args[0].value == rung
    assert "retries=0" in SRC.read_text() and "go_gate" not in ast.unparse(fns["check"])


def test_timeouts_come_from_the_caps_and_never_cost_more():
    smoke, run = WJ.timeouts(PINNED)
    h = WJ.usd_per_h(PINNED)
    for t, cap in ((smoke, 0.25), (run, 1.0)):
        assert t > 0 and t * h / 3600 + 120 * h / 3600 <= cap
    with pytest.raises(ValueError, match="costs more"):
        WJ.check_timeout(run + 600, 1.0, h, 120)
    with pytest.raises(ValueError):
        WJ.timeouts(dict(PINNED, caps={"smoke_usd": 0.05, "run_usd": 1.0, "cold_start_s": 120}))   # cold start eats the cap


def test_the_launch_price_is_held_to_the_dated_price_table():
    WJ.preflight(PINNED)
    with pytest.raises(SystemExit, match="price table"):
        WJ.preflight(dict(PINNED, usd_per_h=2.5))     # the v15 flat number would under-price CPU and memory


def test_the_shot_preflight(tmp_path):
    WJ.preflight(PINNED, {"shot_id": "S1", "motion_prompt": "she runs", "seconds": 2.0, "seed": 7})
    for bad, want in (({"motion_prompt": ""}, "no motion prompt"), ({"seed": None}, "seed missing"),
                      ({"end_picture": "e.png"}, "end_image_arg")):
        with pytest.raises(SystemExit, match=want):
            WJ.preflight(PINNED, dict({"shot_id": "S1", "motion_prompt": "x", "seconds": 2.0, "seed": 7}, **bad))


def test_the_start_picture_is_pinned_by_sha(tmp_path):
    pic = tmp_path / "p.png"
    pic.write_bytes(b"picture")
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({"shot_id": "S1", "start_picture": str(pic), "extra": {"start_sha256": "0" * 64}}))
    with pytest.raises(SystemExit, match="sha256"):
        WJ.read_job(str(spec))
    spec.write_text(json.dumps({"shot_id": "S1", "start_picture": str(pic), "extra": {}}))
    job = WJ.read_job(str(spec))
    assert job["start_bytes"] == b"picture" and len(job["start_sha256"]) == 64


def test_frames_and_names_agree_with_the_adapter():
    assert WJ.clip_name("S01_SH001", 7) == WA.clip_name("S01_SH001", 7)
    for sec, fps in ((1.0, 24), (2.5, 24), (5.0, 16)):
        n = WJ.wan_frames(sec, fps)
        assert (n - 1) % 4 == 0 and n >= round(sec * fps)


def test_the_ladder_runs_in_order_and_a_red_rung_stops_it(tmp_path):
    lad = tmp_path / "ladder.json"
    with pytest.raises(SystemExit, match="L0"):
        WJ.ladder_gate("L3", lad)
    with pytest.raises(SystemExit, match="L1"):
        MR.record_rung(lad, "L2", True)
    for r in ("L0", "L1"):
        MR.record_rung(lad, r, True)
    MR.record_rung(lad, "L2", False, note="a weight file is missing")
    with pytest.raises(SystemExit, match="red"):
        WJ.ladder_gate("L3", lad)
    MR.record_rung(lad, "L2", True)
    d = MR.record_rung(lad, "L3", True, measured={"gpu": "A100-80GB", "s_per_clip_s": 55.0, "setup_s": 90.0})
    assert d["done"] == ["L0", "L1", "L2", "L3"] and d["red"] is None and d["measured"]["s_per_clip_s"] == 55.0
    WJ.ladder_gate("L4", lad)
    be = WA.ModalWanBackend(PINNED, MR.load_ladder(lad), runner=lambda a: (0, ""), fetch=lambda j, o: None,
                            env={"EE_MODAL_GO": "cmsg_1"})
    assert be.measured_s_per_clip_s == 55.0 and be.usd_per_hour == pytest.approx(WJ.schedule_rate(PINNED))


def test_the_ladder_cli(tmp_path, capsys):
    lad = tmp_path / "ladder.json"
    assert MR.main(["record", str(lad), "L0", "ok", "--note", "pytest green"]) == 0
    assert json.loads(capsys.readouterr().out)["next"] == "L1"
