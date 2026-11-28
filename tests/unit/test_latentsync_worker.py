"""The LatentSync worker's free contract (training/pods/latentsync/modal_latentsync_jobs.py): pins, job checks, the CLI it
builds, the money gates and the step-by-step output. Fakes only: no network, no modal package, no GPU."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.core import approvals
from explainer_engine.core.ledger import Run
from explainer_engine.training.pods.latentsync import modal_latentsync_jobs as M

REPO = Path(__file__).resolve().parents[2]
PLAN = hashlib.sha256(b"the approved lipsync plan").hexdigest()
CARD = "cmsg_test_latentsync_0001"
VIDEO, AUDIO = b"fake rendered clip bytes", b"fake 16 kHz wav bytes"


def full_launch() -> dict:
    """The real launch with its two open pins filled by fakes (the shape a fully pinned launch will have)."""
    lf = copy.deepcopy(M.LAUNCH)
    lf["base_image"] = "registry.example/latentsync@sha256:" + "0" * 64
    lf["face_detector"]["sha256"] = "1" * 64
    return lf


def payload(backend="latentsync_1_5", steps=25, guidance=1.5, seed=1247) -> dict:
    """What videolane/lipsync_pipeline.build_lipsync_refinement_command writes for a LatentSync backend."""
    cfg = "configs/unet/stage2_512.yaml" if backend == "latentsync_1_6" else "configs/unet/stage2.yaml"
    return {"schema": "lipsync_refinement_job/1", "backend": backend, "repo": "https://github.com/bytedance/LatentSync",
            "license": "Apache-2.0", "min_vram_gb": 18 if backend == "latentsync_1_6" else 8,
            "video_path": "/local/clip.mp4", "audio_wav_path": "/local/line_16k.wav", "out_mp4": "/local/clip_ls.mp4",
            "cmd": ["python", "-m", "scripts.inference", "--unet_config_path", cfg, "--inference_ckpt_path",
                    "checkpoints/latentsync_unet.pt", "--inference_steps", str(steps), "--guidance_scale", f"{guidance:.2f}",
                    "--video_path", "/local/clip.mp4", "--audio_path", "/local/line_16k.wav", "--video_out_path",
                    "/local/clip_ls.mp4", "--seed", str(seed)]}


def make(launch, ledger_path="/tmp/never_written.json", **kw) -> dict:
    p = payload(**kw)
    return M.make_job(launch, p, shot_id="s07_closeup",
                      inputs={"video": {"hf_path": "explainer-engine/ltx_route/out/r1/s07/s07.mp4",
                                        "sha256": hashlib.sha256(VIDEO).hexdigest()},
                              "audio": {"hf_path": "explainer-engine/voice/r1/s07_16k.wav",
                                        "sha256": hashlib.sha256(AUDIO).hexdigest()}},
                      settings={"inference_steps": int(p["cmd"][p["cmd"].index("--inference_steps") + 1]),
                                "guidance_scale": float(p["cmd"][p["cmd"].index("--guidance_scale") + 1]),
                                "seed": int(p["cmd"][p["cmd"].index("--seed") + 1])},
                      plan_sha256=PLAN, ledger_path=ledger_path)


# --- pins -------------------------------------------------------------------------------------------------------------------

def test_launch_pins_are_full_hashes_and_agree_with_cloud_pins():
    lf = M.LAUNCH
    assert re.fullmatch(r"[0-9a-f]{40}", lf["model_revision"])
    assert re.fullmatch(r"[0-9a-f]{40}", lf["latentsync_code"]["commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", lf["vae"]["revision"])
    for f, h in {**lf["model_files"], **lf["vae"]["files"]}.items():
        assert re.fullmatch(r"[0-9a-f]{64}", h), f
    assert set(lf["uses"].values()) <= set(lf["model_files"])
    pins = json.loads((REPO / "config" / "cloud_pins.json").read_text(encoding="utf-8"))["models"]["lipsync_latentsync"]
    assert pins["id"] == lf["model_repo"] and pins["revision"] == lf["model_revision"]
    assert pins["sha256_files"] == lf["model_files"] and pins["sha256"] == lf["model_files"][lf["uses"]["unet"]]
    assert pins["code"]["commit"] == lf["latentsync_code"]["commit"]
    assert pins["licence"] == "SPDX:Apache-2.0"
    assert M.pins_problems(lf) == []


def test_pins_drift_is_caught():
    pins = copy.deepcopy(M.load_pins())
    pins["sha256_files"]["whisper/tiny.pt"] = "f" * 64
    pins["code"]["commit"] = "e" * 40
    bad = M.pins_problems(M.LAUNCH, pins)
    assert any("sha256_files" in b for b in bad) and any("code commit" in b for b in bad)


def test_the_real_launch_is_refused_for_exactly_its_two_open_pins_and_defines_no_modal_function():
    assert sorted(M.launch_problems(M.LAUNCH)) == sorted([
        "launch base_image is not pinned",
        "launch face_detector buffalo_l has no sha256: insightface would fetch an unpinned zip at run time"])
    assert M.TIMEOUT is None and not hasattr(M, "app")
    with pytest.raises(SystemExit):
        M.hard_bill_usd(M.LAUNCH)


def test_a_fully_pinned_launch_passes_and_its_bill_stays_under_the_cap():
    lf = full_launch()
    assert M.launch_problems(lf) == []
    assert lf["usd_per_h"] == M.schedule_rate(lf)
    assert M.hard_bill_usd(lf) <= lf["caps"]["run_usd"]
    assert lf["startup_timeout_s"] <= lf["caps"]["cold_start_s"]


def test_the_verified_flags_are_the_launch_flags_and_a_changed_list_is_refused():
    assert tuple(M.LAUNCH["cli_flags"]) == M.VERIFIED_FLAGS
    lf = full_launch()
    lf["cli_flags"] = [*lf["cli_flags"], "--made_up_flag"]
    assert any("cli_flags" in b for b in M.launch_problems(lf))


def test_importing_the_worker_needs_no_modal_package():
    src = Path(M.__file__).read_text(encoding="utf-8")
    assert "try:\n    import modal\nexcept ImportError:\n    modal = None" in src
    assert "\nimport modal" not in src.replace("try:\n    import modal", "")


# --- the job ----------------------------------------------------------------------------------------------------------------

def test_a_job_from_the_pipeline_payload_passes():
    assert M.job_problems(full_launch(), make(full_launch())) == []


def test_the_real_pipeline_builder_output_passes_when_it_is_merged():
    lp = pytest.importorskip("explainer_engine.videolane.lipsync_pipeline")
    lf = full_launch()
    p = lp.build_lipsync_refinement_command(backend="latentsync_1_5", video_path=Path("/l/c.mp4"),
                                            audio_wav_path=Path("/l/a.wav"), out_mp4=Path("/l/o.mp4"))
    job = M.make_job(lf, p, shot_id="s1", inputs=make(lf)["inputs"],
                     settings={"inference_steps": 25, "guidance_scale": 1.5, "seed": 1247}, plan_sha256=PLAN,
                     ledger_path="/tmp/x.json")
    assert M.job_problems(lf, job) == []


@pytest.mark.parametrize("which", ["video", "audio"])
def test_unpinned_inputs_are_caught(which):
    lf = full_launch()
    job = make(lf)
    job["inputs"][which].pop("sha256")
    assert any(f"input {which} is not pinned" in b for b in M.job_problems(lf, job))
    job = make(lf)
    job["inputs"][which] = {"hf_path": "/local/disk/file", "sha256": "a" * 64}
    assert any(f"input {which} has no HF path" in b for b in M.job_problems(lf, job))
    job = make(lf)
    job["inputs"][which]["sha256"] = "not-a-hash"
    assert any(f"input {which} is not pinned" in b for b in M.job_problems(lf, job))


@pytest.mark.parametrize("key", list(M.SETTINGS))
def test_a_setting_not_written_out_is_caught(key):
    lf = full_launch()
    job = make(lf)
    job["settings"].pop(key)
    assert any(f"setting {key} is not written out" in b for b in M.job_problems(lf, job))


def test_settings_outside_the_readme_ranges_a_random_seed_and_a_drifted_command_are_caught():
    lf = full_launch()
    job = make(lf)
    job["settings"].update(inference_steps=5, guidance_scale=9.0, seed=-1)
    bad = M.job_problems(lf, job)
    assert any("inference_steps 5" in b for b in bad) and any("guidance_scale 9.0" in b for b in bad)
    assert any("seed -1" in b for b in bad)
    job = make(lf)
    job["settings"]["seed"] = 7                      # the payload's command still says 1247
    assert any("--seed 1247" in b for b in M.job_problems(lf, job))


def test_the_wrong_backend_is_caught():
    lf = full_launch()
    bad = M.job_problems(lf, make(lf, backend="latentsync_1_6"))
    assert any("backend 'latentsync_1_6' is not the one this launch pins" in b for b in bad)
    assert any("configs/unet/stage2_512.yaml" in b for b in bad)
    job = make(lf)
    job["backend"] = "musetalk_1_5"
    assert any("not a LatentSync backend" in b for b in M.job_problems(lf, job))


def test_a_flag_the_cli_does_not_have_and_a_foreign_launch_are_caught():
    lf = full_launch()
    job = make(lf)
    job["cmd"] += ["--fps", "24"]
    assert any("--fps" in b for b in M.job_problems(lf, job))
    other = copy.deepcopy(lf)
    other["caps"]["run_usd"] = 0.3
    assert any("another launch file" in b for b in M.job_problems(other, make(lf)))


# --- the command ------------------------------------------------------------------------------------------------------------

def test_build_cmd_uses_only_pinned_paths_and_verified_flags(tmp_path):
    lf = full_launch()
    job = make(lf)
    code, vol = tmp_path / "code", tmp_path / "vol"
    cmd = M.build_cmd(lf, job, tmp_path / "in.mp4", tmp_path / "in.wav", tmp_path / "out.mp4", vol_root=vol,
                      code_dir=code, temp_dir=tmp_path / "t", python="py")
    assert cmd[:3] == ["py", "-m", "scripts.inference"]
    flags = [c for c in cmd if c.startswith("--")]
    assert set(flags) <= set(M.VERIFIED_FLAGS) and len(flags) == len(set(flags))
    f = M.cmd_flags(cmd)
    assert f["--inference_ckpt_path"] == str(vol / "model" / "ByteDance/LatentSync-1.5" / "latentsync_unet.pt")
    assert f["--unet_config_path"] == str(code / "configs/unet/stage2.yaml")
    assert "checkpoints/latentsync_unet.pt" not in cmd              # the payload's relative path is never used
    assert (f["--inference_steps"], f["--guidance_scale"], f["--seed"]) == ("25", "1.5", "1247")
    assert "--enable_deepcache" not in f
    job["settings"]["enable_deepcache"] = True
    assert M.build_cmd(lf, job, "v", "a", "o.mp4")[-1] == "--enable_deepcache"


def test_the_cli_runs_offline_against_the_volume_cache():
    env = M.run_env(full_launch(), "/w")
    assert env["HF_HUB_OFFLINE"] == "1" and env["HF_HUB_CACHE"] == "/w/hf_cache"


def test_stage_input_refuses_a_file_that_is_not_the_pinned_one(tmp_path):
    spec = {"hf_path": "x/clip.mp4", "sha256": hashlib.sha256(VIDEO).hexdigest()}
    with pytest.raises(RuntimeError, match="sha256 is not the pinned one"):
        M.stage_input(spec, tmp_path / "a" / "clip.mp4", download=lambda r, p, d: d.write_bytes(b"other bytes"))
    assert M.stage_input(spec, tmp_path / "b" / "clip.mp4", download=lambda r, p, d: d.write_bytes(VIDEO)).is_file()


def test_staging_is_refused_while_a_pin_is_open(tmp_path):
    called = []
    bad = M.stage_weights(M.LAUNCH, tmp_path, download=lambda *a, **k: called.append(a), fetch=lambda *a: called.append(a))
    assert bad and not called


# --- money ------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def money(tmp_path, monkeypatch):
    """A spend-caps file with the creator's line, an owner registry with this job's approval, and a ledger path."""
    caps = json.loads((REPO / "config" / "spend_caps.json").read_text(encoding="utf-8"))
    caps["modal_latentsync"] = {"per_run_usd": 0.6}
    (tmp_path / "caps.json").write_text(json.dumps(caps))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(tmp_path / "caps.json"))
    monkeypatch.delenv("OWNER_APPROVAL_SIGNING_KEY", raising=False)
    monkeypatch.delenv("EE_APPROVAL_HMAC_KEY", raising=False)
    lf = full_launch()
    ledger = tmp_path / "ledger.json"
    job = make(lf, ledger_path=str(ledger))
    exp = (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat()
    reg = tmp_path / "owner_approvals.json"
    reg.write_text(json.dumps({"schema_version": "owner_approvals/1", "approvals": {CARD: {
        "provider": "modal_modal1", "operation_mode": "modal-latentsync-main", "manifest_sha256": M.manifest_sha(lf, job),
        "max_usd": 0.4, "expires_at": exp, "owner_evidence": "test fixture"}}}))
    return SimpleNamespace(launch=lf, job=job, ledger=ledger, registry=reg, env={"EE_MODAL_GO": f"{CARD}:{PLAN[:12]}"})


def reserve(m, amount=None):
    run = Run.open(m.ledger, caps={"modal_latentsync": 0.6})
    run.reserve("modal_latentsync", M.hard_bill_usd(m.launch) if amount is None else amount, m.job["ledger"]["item"])


def test_the_real_spend_caps_have_no_line_so_nothing_is_called(monkeypatch):
    monkeypatch.delenv("EXPLAINER_SPEND_CAPS", raising=False)
    lf = full_launch()
    calls = []
    with pytest.raises(SystemExit, match="no modal_latentsync per_run_usd"):
        M.paid_run(lf, make(lf), remote=lambda *a: calls.append(a), env={"EE_MODAL_GO": f"{CARD}:{PLAN[:12]}"})
    assert calls == []


def test_the_real_launch_is_refused_before_any_approval_or_ledger(money):
    calls = []
    with pytest.raises(SystemExit, match="base_image is not pinned"):
        M.paid_run(M.LAUNCH, make(M.LAUNCH, ledger_path=str(money.ledger)), remote=lambda *a: calls.append(a),
                   env=money.env, registry_path=money.registry)
    assert calls == [] and not money.ledger.exists()


def test_no_owner_approval_means_no_run(money):
    reserve(money)
    calls = []
    with pytest.raises(SystemExit, match="EE_MODAL_GO"):
        M.paid_run(money.launch, money.job, remote=lambda *a: calls.append(a), env={}, registry_path=money.registry)
    other = dict(money.job, settings=dict(money.job["settings"], seed=1248))
    other["cmd"] = [*other["cmd"][:-1], "1248"]
    with pytest.raises(SystemExit, match="manifest_sha256 does not match"):
        M.paid_run(money.launch, other, remote=lambda *a: calls.append(a), env=money.env, registry_path=money.registry)
    assert calls == []
    assert "launch" not in Run.open(money.ledger).data["items"]


def test_no_reservation_means_no_run(money):
    calls = []
    with pytest.raises(SystemExit, match="no open modal_latentsync reservation"):
        M.paid_run(money.launch, money.job, remote=lambda *a: calls.append(a), env=money.env, registry_path=money.registry)
    reserve(money, amount=0.01)                      # below the worst-case bill
    with pytest.raises(SystemExit, match="below the worst-case bill"):
        M.paid_run(money.launch, money.job, remote=lambda *a: calls.append(a), env=money.env, registry_path=money.registry)
    assert calls == []


def test_a_reserved_approved_run_is_called_once_settled_and_never_repeated(money):
    reserve(money)
    calls = []
    clock = iter([1000.0, 1000.0, 1100.0])

    def remote(job, launch):
        calls.append(job)
        return {"state": "DONE"}

    res = M.paid_run(money.launch, money.job, remote=remote, env=money.env, registry_path=money.registry,
                     now=lambda: next(clock))
    assert res == {"state": "DONE"} and len(calls) == 1
    sent = calls[0]
    assert sent["approval_proof"]["manifest_sha256"] == M.manifest_sha(money.launch, money.job)
    assert sent["approval_proof"]["approval_id"] == CARD and sent["nonce"]
    row = Run.open(money.ledger).data["reserved"][money.job["ledger"]["item"]]
    assert row["settled"] and row["amount"] == round(100.0 * money.launch["usd_per_h"] / 3600.0, 4)
    with pytest.raises(SystemExit):                  # settled: no open reservation; and the launch mark stays
        M.paid_run(money.launch, money.job, remote=remote, env=money.env, registry_path=money.registry)
    assert len(calls) == 1


def test_a_cap_above_80_percent_of_the_line_is_refused(money):
    lf = copy.deepcopy(money.launch)
    lf["caps"]["run_usd"] = 0.55                     # line 0.6 -> stop at 0.48
    assert any("above 80 %" in b for b in M.spend_line_problems(lf))


def test_the_container_refuses_an_unsigned_or_foreign_proof(money, tmp_path):
    key = "k" * 32
    proof = approvals.sign_approval_proof(dict(json.loads(money.registry.read_text())["approvals"][CARD], approval_id=CARD),
                                          signing_key=key, operation_id="op_test_0001")
    job = dict(money.job, approval_proof=proof)
    baked = tmp_path / "none.json"
    assert M.container_gate(job, money.launch, env={"OWNER_APPROVAL_SIGNING_KEY": key}, baked=baked) == []
    assert any("not signed" in b for b in M.container_gate(job, money.launch, env={}, baked=baked))
    assert M.container_gate(dict(money.job), money.launch, env={"OWNER_APPROVAL_SIGNING_KEY": key}, baked=baked) == [
        "no approval proof in the job"]
    moved = dict(job, settings=dict(job["settings"], guidance_scale=2.0))
    assert any("another manifest" in b for b in M.container_gate(moved, money.launch,
                                                                 env={"OWNER_APPROVAL_SIGNING_KEY": key}, baked=baked))


# --- the body: outputs written and recorded step by step ----------------------------------------------------------------------

class FakeOp:
    def __init__(self, path_in_repo, path_or_fileobj):
        self.path_in_repo, self.path = path_in_repo, path_or_fileobj


class FakeApi:
    """Keeps what each commit carried: the record's steps at that moment and the output's sha256."""

    def __init__(self):
        self.commits, self.store = [], {}

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        snap = {}
        for op in operations:
            data = Path(op.path).read_bytes()
            self.store[op.path_in_repo] = data
            snap[op.path_in_repo.rsplit("/", 1)[-1]] = data
        self.commits.append(snap)

    def get_paths_info(self, repo, paths, repo_type, expand):
        out = []
        for p in paths:
            if p in self.store:
                d = self.store[p]
                out.append(SimpleNamespace(path=p, lfs={"sha256": hashlib.sha256(d).hexdigest()}, blob_id=None))
        return out


def staged_volume(lf, vol: Path, code: Path):
    """The Volume as the stage step leaves it (files present; their sha256 was proved there) and the code checkout."""
    for p in M.needed_files(lf, vol):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"w")
    (M.face_root(vol) / "models" / "buffalo_l").mkdir(parents=True)
    code.mkdir()


def run_body(tmp_path, sh):
    lf = full_launch()
    vol, code, out = tmp_path / "vol", tmp_path / "code", tmp_path / "out"
    staged_volume(lf, vol, code)
    blobs = {"video": VIDEO, "audio": AUDIO}
    job = dict(make(lf), nonce="n1", worker_sha="w" * 64)
    names = {job["inputs"][k]["hf_path"]: blobs[k] for k in blobs}
    api = FakeApi()
    res = M.body(job, lf, 600, vol_root=vol, code_dir=code, api=api, sh=sh, out_root=out,
                 download=lambda repo, hp, dest: dest.write_bytes(names[hp]), python="py", op=FakeOp,
                 now=iter(float(t) for t in range(10_000)).__next__)
    return lf, job, api, res, vol, code


def records(api, job):
    name = f"{job['shot_id']}.run_record.json"
    return [json.loads(c[name]) for c in api.commits if name in c]


def test_a_stub_run_writes_and_uploads_each_step_with_its_sha256(tmp_path):
    seen = {}

    def sh(cmd, cwd, env, **kw):
        seen.update(cmd=cmd, cwd=cwd, env=env)
        Path(M.cmd_flags(cmd)["--video_out_path"]).write_bytes(b"lip-synced clip")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    lf, job, api, res, vol, code = run_body(tmp_path, sh)
    assert res["state"] == "DONE" and set(res["verified"].values()) == {"ok"}
    steps = [[s["step"] for s in r["steps"]] for r in records(api, job)]
    assert steps == [["inputs"], ["inputs", "weights"], ["inputs", "weights", "lipsync"],
                     ["inputs", "weights", "lipsync", "output"], ["inputs", "weights", "lipsync", "output", "end"]]
    first = records(api, job)[0]
    assert first["settings"] == job["settings"] and first["steps"][0]["sha256"] == {
        "video": hashlib.sha256(VIDEO).hexdigest(), "audio": hashlib.sha256(AUDIO).hexdigest()}
    out_sha = hashlib.sha256(b"lip-synced clip").hexdigest()
    assert res["outputs"]["clip_ls.mp4"]["sha256"] == out_sha
    mp4_commit = next(k for k, c in enumerate(api.commits) if "clip_ls.mp4" in c)
    assert hashlib.sha256(api.commits[mp4_commit]["clip_ls.mp4"]).hexdigest() == out_sha
    assert mp4_commit < len(api.commits) - 1                      # the clip left before the final flush
    assert res["argv_sha256"] == hashlib.sha256("\0".join(seen["cmd"]).encode()).hexdigest()
    assert seen["cwd"] == str(code) and seen["env"]["HF_HUB_OFFLINE"] == "1"
    assert (code / "checkpoints" / "whisper" / "tiny.pt").resolve() == (vol / "model/ByteDance/LatentSync-1.5/whisper/tiny.pt").resolve()
    ref = M.vae_snapshot(lf, vol).parents[1] / "refs" / "main"
    assert ref.read_text() == lf["vae"]["revision"]
    assert (vol / M.VOL_OUT / job["run_id"] / job["shot_id"] / "clip_ls.mp4").is_file()   # the Volume copy too


def test_a_failed_cli_is_recorded_and_uploaded_and_a_rescheduled_input_returns(tmp_path):
    def sh(cmd, cwd, env, **kw):
        return SimpleNamespace(returncode=1, stdout="", stderr="CUDA out of memory")

    lf, job, api, res, vol, code = run_body(tmp_path, sh)
    assert res["state"] == "FAILED" and "CUDA out of memory" in res["error"]
    last = records(api, job)[-1]
    assert [(s["step"], s["ok"]) for s in last["steps"]] == [("inputs", True), ("weights", True), ("lipsync", False),
                                                             ("end", False)]
    assert last["outputs"] == {}
    again = M.body(job, lf, 600, vol_root=vol, code_dir=code, out_root=tmp_path / "out")
    assert again["state"] == "REFUSED_SECOND_ATTEMPT"


def test_a_tampered_input_stops_before_the_model(tmp_path):
    lf = full_launch()
    vol, code = tmp_path / "vol", tmp_path / "code"
    staged_volume(lf, vol, code)
    job = dict(make(lf), nonce="n2")
    calls = []
    res = M.body(job, lf, 600, vol_root=vol, code_dir=code, out_root=tmp_path / "out", sh=lambda *a, **k: calls.append(a),
                 download=lambda repo, hp, dest: dest.write_bytes(b"swapped"))
    assert res["state"] == "FAILED" and "sha256 is not the pinned one" in res["error"] and calls == []
