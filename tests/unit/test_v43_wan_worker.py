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
          "memory_gib": 64, "usd_per_h": 3.3872, "prices_date": "2026-11-07", "scaledown_window_s": 2,
          "pip_pins": {"transformers": "4.0.0", "accelerate": "1.0.0"},
          "caps": {"smoke_usd": 0.25, "run_usd": 1.0, "cold_start_s": 120},
          "native": {"fps": 16, "max_frames": 81, "sizes": [[1280, 720], [832, 480]], "use": [1280, 720]},
          "offload": "model_cpu_offload"}
PROOF = WJ.proof(PINNED)


@pytest.fixture()
def line(tmp_path, monkeypatch):
    """A spend-caps file with the creator's test-only Modal line ($1 a run, no episode line yet: final audit section 7.3)."""
    def write(per_run=1.0):
        f = tmp_path / "caps.json"
        f.write_text(json.dumps({"per_episode": {}, "modal": {"per_run_usd": per_run} if per_run else {}}))
        monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(f))
    write()
    return write


def test_the_committed_launch_file_pins_only_the_creators_pick_so_nothing_runs():
    """The model is his pick (card of 2026-11-12 14:26 UTC); the GPU price, caps, image pins and output wait for his test line
    (OR-22), so the worker still refuses everything."""
    lf = json.loads((SRC.parent / "launch.json").read_text())
    assert lf["decided"]["by"] == "creator" and lf["decided"]["message_id"].startswith("cmsg_")
    assert lf["model_repo"] == "Wan-AI/Wan2.2-I2V-A14B-Diffusers" and len(lf["model_revision"]) == 40
    assert lf["pipeline"] == "WanImageToVideoPipeline" and lf["native"]["use"] == [1280, 720] and not WJ.native_problems(lf)
    weights = {f for f in lf["model_files"] if f.endswith(".safetensors")}
    for part, n in (("transformer", 12), ("transformer_2", 12), ("text_encoder", 3), ("vae", 1)):
        assert sum(f.startswith(part + "/") for f in weights) == n, part
    assert all(len(h) == 64 for h in lf["model_files"].values())
    for still_open in ("usd_per_h", "hf_out", "scaledown_window_s"):
        assert lf[still_open] is None, still_open
    assert WJ.TIMEOUTS is None and WJ.launch_problems(lf)
    with pytest.raises(SystemExit, match="nothing was started"):
        WJ.preflight(lf)


def test_a_clip_is_made_at_the_models_own_rate_and_size_and_never_past_its_longest_clip():
    """Final audit A2: 16 fps, 4k+1 frames up to 81, the launch's size; a longer shot is refused with its remedies."""
    assert WJ.native_spec(PINNED, 5.0) == {"fps": 16, "width": 1280, "height": 720, "frames": 81}
    assert WJ.native_spec(PINNED, 1.0)["frames"] == 17 and WJ.max_seconds(PINNED) == pytest.approx(5.093, abs=1e-3)
    with pytest.raises(ValueError, match="split the shot"):
        WJ.native_spec(PINNED, 5.2)
    for bad, want in (({"fps": 24.5}, "native.fps"), ({"max_frames": 80}, "4k\\+1"), ({"sizes": [[1280, 721]]}, "multiples of 16"),
                      ({"use": [640, 360]}, "one of native.sizes")):
        assert any(__import__("re").search(want, p) for p in WJ.native_problems(dict(PINNED, native=dict(PINNED["native"], **bad))))
    assert "launch offload must be one of" in " ".join(WJ.launch_problems(dict(PINNED, offload="sequential")))


def test_entrypoints_run_the_preflight_before_the_go_gate_and_the_ladder_gate():
    tree = ast.parse(SRC.read_text())
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for name, rung in (("smoke", "L3"), ("main", "L4"), ("stage", "L2")):
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


def test_the_launch_price_is_held_to_the_dated_price_table(line):
    WJ.preflight(PINNED)
    with pytest.raises(SystemExit, match="price table"):
        WJ.preflight(dict(PINNED, usd_per_h=2.5))     # the v15 flat number would under-price CPU and memory


def test_the_shot_preflight(tmp_path, line):
    WJ.preflight(PINNED, {"shot_id": "S1", "motion_prompt": "she runs", "seconds": 2.0, "seed": 7})
    for bad, want in (({"motion_prompt": ""}, "no motion prompt"), ({"seed": None}, "seed missing"),
                      ({"end_picture": "e.png"}, "end_image_arg")):
        with pytest.raises(SystemExit, match=want):
            WJ.preflight(PINNED, dict({"shot_id": "S1", "motion_prompt": "x", "seconds": 2.0, "seed": 7}, **bad))


def test_the_start_picture_is_pinned_by_sha_and_the_spec_by_plan_and_launch(tmp_path):
    import hashlib
    pic = tmp_path / "p.png"
    pic.write_bytes(b"picture")
    sha, plan = hashlib.sha256(b"picture").hexdigest(), "c" * 64
    good = {"shot_id": "S1", "start_picture": str(pic), "extra": {"start_sha256": sha}, "plan_sha256": plan,
            "run_id": WJ.run_id(plan, PINNED), "launch_sha": WJ.launch_sha(PINNED), "seconds": 3.0, "fps": 16, "width": 1280,
            "height": 720}
    spec = tmp_path / "s.json"
    for bad, want in (({"extra": {"start_sha256": "0" * 64}}, "sha256 is not the one"),
                      ({"extra": {}}, "no start_sha256"),                      # B9: no longer optional
                      ({"plan_sha256": None}, "no plan_sha256"),
                      ({"launch_sha": "d" * 64}, "another launch file"),
                      ({"run_id": "x_y"}, "another launch file"),
                      ({"seconds": 6.0}, "past its longest clip"),          # A2: never past the model's longest clip
                      ({"fps": 24}, "not the model's 1280x720 at 16 fps"),
                      ({"width": 1920, "height": 1080}, "not the model's")):
        spec.write_text(json.dumps(dict(good, **bad)))
        with pytest.raises(SystemExit, match=want):
            WJ.read_job(str(spec), PINNED)
    spec.write_text(json.dumps(good))
    job = WJ.read_job(str(spec), PINNED)
    assert job["start_bytes"] == b"picture" and job["start_sha256"] == sha


def test_the_go_binds_the_plans_hash():
    plan = "e" * 64
    assert WJ.go_gate({"EE_MODAL_GO": "cmsg_A1:" + plan[:12]}, plan)
    for bad in ("cmsg_A1", "cmsg_A1:" + "f" * 12, "card:" + plan[:12], ""):
        with pytest.raises(SystemExit, match="nothing was started"):
            WJ.go_gate({"EE_MODAL_GO": bad}, plan)


def test_run_ids_and_hf_paths_carry_the_plan_and_the_launch():
    a, b = WJ.run_id("1" * 64, PINNED), WJ.run_id("2" * 64, PINNED)
    assert a != b and a != WJ.run_id("1" * 64, dict(PINNED, settings={"steps": 31}))
    assert WJ.hf_path(PINNED, {"run_id": a, "shot_id": "S1"}, "S1_seed7.mp4") == f"route_test/wan_out/{a}/S1/S1_seed7.mp4"
    with pytest.raises(ValueError):
        WJ.run_id("short", PINNED)


def test_the_image_pins_and_the_scaledown_window_are_pins():
    assert "launch pip_pins.accelerate is not pinned" in WJ.launch_problems(dict(PINNED, pip_pins={"transformers": "4"}))
    assert any("scaledown_window_s" in x for x in WJ.launch_problems(dict(PINNED, scaledown_window_s=600)))
    assert any("scaledown_window_s is not pinned" in x for x in WJ.launch_problems(dict(PINNED, scaledown_window_s=None)))
    src = SRC.read_text()
    assert "scaledown_window=LAUNCH[\"scaledown_window_s\"]" in src and "t.cancel()" in src   # C4


def test_main_exits_non_zero_on_a_failed_clip_and_the_rungs_record_themselves():
    tree = ast.parse(SRC.read_text())
    fns = {n.name: ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "WAN_FAILED" in fns["main"] and "SystemExit(4)" in fns["main"]          # A4
    for name, rung in (("check", "L1"), ("weights", "L2"), ("smoke", "L3")):
        assert f"record('{rung}'" in fns[name], name                              # A5
    assert "beat(out, job" in fns["generate"] and "callback_on_step_end" in fns["generate"]   # A7: the step beat


def test_a_red_record_exits_non_zero(tmp_path):
    lad = tmp_path / "ladder.json"
    MR.record_rung(lad, "L0", True, commit="abc")
    with pytest.raises(SystemExit, match="L1 is red"):
        WJ.record("L1", False, path=lad, launch=PINNED, note="env_check rc 1")
    assert MR.load_ladder(lad)["red"] == "L1"


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
        MR.record_rung(lad, "L2", True, **PROOF)
    with pytest.raises(ValueError, match="commit"):
        MR.record_rung(lad, "L0", True)                       # A5: a green L0 names its commit
    MR.record_rung(lad, "L0", True, commit="abc")
    with pytest.raises(ValueError, match="sha256"):
        MR.record_rung(lad, "L1", True)                       # A5: a green L1.. names the launch file and the worker
    MR.record_rung(lad, "L1", True, **PROOF)
    MR.record_rung(lad, "L2", False, note="a weight file is missing")
    with pytest.raises(SystemExit, match="red"):
        WJ.ladder_gate("L3", lad, PINNED)
    MR.record_rung(lad, "L2", True, **PROOF)
    d = MR.record_rung(lad, "L3", True, measured={"gpu": "A100-80GB", "s_per_clip_s": 55.0, "setup_s": 90.0}, **PROOF)
    assert d["done"] == ["L0", "L1", "L2", "L3"] and d["red"] is None and d["measured"]["s_per_clip_s"] == 55.0
    WJ.ladder_gate("L4", lad, PINNED)
    with pytest.raises(SystemExit, match="another launch file"):   # A5: a changed launch file makes L1..L3 stale
        WJ.ladder_gate("L4", lad, dict(PINNED, settings={"steps": 40}))
    be = WA.ModalWanBackend(PINNED, MR.load_ladder(lad), runner=lambda a: (0, ""), fetch=lambda j, o: None,
                            env={"EE_MODAL_GO": "cmsg_1:" + "0" * 12})
    assert be.measured_s_per_clip_s == 55.0 and be.usd_per_hour == pytest.approx(WJ.schedule_rate(PINNED))


def test_l0_runs_the_tests_and_records_their_summary_and_commit(tmp_path):
    lad, seen = tmp_path / "ladder.json", []

    def runner(argv, rc=0, dirty=""):
        seen.append(argv)
        if "pytest" in argv:
            return rc, "....\n42 passed in 3.1s\n"
        if argv[:2] == ["git", "rev-parse"]:
            return 0, "f" * 40 + "\n"
        return 0, dirty
    d = MR.l0(lad, runner=runner)
    assert d["done"] == ["L0"] and d["rungs"]["L0"]["pytest"] == "42 passed in 3.1s" and d["rungs"]["L0"]["commit"] == "f" * 40
    assert set(MR.L0_TESTS) <= set(seen[0])
    d = MR.l0(tmp_path / "b.json", runner=lambda a: runner(a, rc=1))
    assert d["red"] == "L0"
    d = MR.l0(tmp_path / "c.json", runner=lambda a: runner(a, dirty=" M explainer_engine/x.py"))
    assert d["red"] == "L0" and "uncommitted" in d["rungs"]["L0"]["note"]


def test_the_ladder_cli_marks_red_by_hand_and_never_green(tmp_path, capsys):
    lad = tmp_path / "ladder.json"
    with pytest.raises(SystemExit):
        MR.main(["record", str(lad), "L0", "ok"])     # A5: no self-reported green rung
    capsys.readouterr()
    assert MR.main(["red", str(lad), "L0", "--note", "a test failed"]) == 0
    assert json.loads(capsys.readouterr().out)["red"] == "L0"
    for f in MR.L0_TESTS:
        assert Path(f).is_file(), f


def test_the_launch_caps_stay_under_the_creators_per_run_line(line):
    WJ.preflight(PINNED)                                   # $0.25 smoke and $1.00 run under the $1 line
    line(0.5)
    with pytest.raises(SystemExit, match=r"caps.run_usd \$1 is above the creator's \$0.5"):
        WJ.preflight(PINNED)
    line(None)
    with pytest.raises(SystemExit, match="zero approved budget"):
        WJ.preflight(PINNED)


def test_the_stage_in_puts_only_the_missing_pinned_files_on_the_volume_then_checks_every_sha(tmp_path):
    """Final audit A6: the pinned revision's own files, only those still missing, then the sha256 of every file."""
    import hashlib
    launch = dict(PINNED, model_files={"a.bin": hashlib.sha256(b"A").hexdigest(), "sub/b.bin": hashlib.sha256(b"B").hexdigest()})
    root = WJ.weights_root(launch, tmp_path)
    (root / "sub").mkdir(parents=True)
    (root / "a.bin").write_bytes(b"A")
    calls = []

    def download(repo, rev, files, into, body=b"B"):
        calls.append((repo, rev, list(files)))
        (into / "sub" / "b.bin").write_bytes(body)
    assert WJ.stage_weights(launch, tmp_path, download) == []
    assert calls == [("org/wan", "a" * 40, ["sub/b.bin"])]
    assert WJ.stage_weights(launch, tmp_path, download) == [] and len(calls) == 1       # nothing missing: nothing fetched
    (root / "sub" / "b.bin").unlink()
    assert WJ.stage_weights(launch, tmp_path, lambda *a: download(*a, body=b"X")) == ["sha256 mismatch sub/b.bin"]


def test_the_stage_in_price_is_the_tables():
    from explainer_engine.cloud import modal_schedule as MS
    per_h = (WJ.STAGE_CPU * MS.CPU_CORE_S + WJ.STAGE_MEM_GIB * MS.MEM_GIB_S) * 3600
    assert WJ.STAGE_USD_PER_H == pytest.approx(per_h, abs=5e-4)
    assert WJ.STAGE_TIMEOUT_S * WJ.STAGE_USD_PER_H / 3600 < 0.5
