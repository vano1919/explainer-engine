"""Layout-To-Render worker (S3): the job rules, the CLI arguments, the launch file's arithmetic, the container body rehearsed on the CPU
(real body, real wrapper, real ffmpeg/imageio, a fake ``ltx_pipelines.ic_lora`` and a fake HF client). Nothing here ran on a GPU: every
number of the A100 stays unmeasured until the L3 rung (docs/LTX_LAYOUT_JOBS.md)."""
from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from explainer_engine.training.pods.ltx import layout_job as J
from explainer_engine.training.pods.ltx import modal_layout_jobs as M
from explainer_engine.training.pods.ltx import modal_ltx_jobs as LTX
from explainer_engine.training.pods.ltx import rehearse_layout_cpu as R

LAUNCH = M.LAUNCH
PROTECTED = Path(M.LTX_DIR) / "launch.json"


def _probe_ok(path):
    return {"width": 1280, "height": 704, "fps": 24.0, "frames": 241, "audio": False}


# --- the launch file ----------------------------------------------------------------------------------------------------------

def test_launch_file_is_consistent_with_the_price_table_and_the_80_percent_rule():
    assert M.launch_problems(LAUNCH) == []
    c = LAUNCH["caps"]
    assert all(c[k] <= 0.8 * c["ledger_line_usd"] + 1e-9 for k in ("smoke_usd", "run_usd", "chain_usd"))   # one ledger file per rung
    assert c["ledger_line_usd"] <= 3.5                                    # the creator's modal per-run line
    assert c["smoke_usd"] + c["run_usd"] + c["chain_usd"] + c["item_spent_before_usd"] <= c["item_ceiling_usd"] == 4.8   # owner: $6.00, 80 % stop
    t_smoke, t_run, t_chain = M.timeouts(LAUNCH)
    assert (t_smoke + c["cold_start_s"]) * M.stated_rate(LAUNCH) / 3600 <= c["smoke_usd"]
    assert (t_run + c["cold_start_s"]) * M.stated_rate(LAUNCH) / 3600 <= c["run_usd"]
    assert (t_chain + c["cold_start_s"]) * M.stated_rate(LAUNCH) / 3600 <= c["chain_usd"]
    assert t_smoke > c["margin_s"] and t_run > c["margin_s"] and t_chain > c["margin_s"]
    assert LAUNCH["gpu"] == "A100-80GB" and LAUNCH["scaledown_window_s"] <= 5
    assert M.stage_timeout(LAUNCH) * LAUNCH["stage"]["usd_per_h"] / 3600 <= LAUNCH["stage"]["cap_usd"] == 0.1


def test_the_hard_bill_of_each_function_stays_inside_its_cap_and_the_ledger_line():
    h = M.stated_rate(LAUNCH)
    c = LAUNCH["caps"]
    worst = sum((t + c["cold_start_s"]) * h / 3600 for t in M.timeouts(LAUNCH))
    assert worst <= c["smoke_usd"] + c["run_usd"] + c["chain_usd"] + 1e-9


@pytest.mark.parametrize("change,needle", [
    (lambda L: L["caps"].update(run_usd=3.0), "80 %"),
    (lambda L: L["caps"].update(chain_usd=2.8), "item's ceiling"),
    (lambda L: L["caps"].pop("item_ceiling_usd"), "item_ceiling_usd is not set"),
    (lambda L: L["caps"].pop("chain_usd"), "chain_usd is not set"),
    (lambda L: L.update(scaledown_window_s=30), "CH-04"),
    (lambda L: L["native"].update(use=[1280, 720]), "CH-02"),
    (lambda L: L["settings"].update(first_frame_index=-1), "first_frame_index"),
    (lambda L: L["smoke"].update(frames=10), "8k+1"),
    (lambda L: L.update(module="ltx_pipelines.distilled"), "ic_lora"),
    (lambda L: L["ltx_code"].update(commit="main"), "40-hex"),
    (lambda L: L["usd_per_h"].update({"A100-80GB": 1.0}), "price table"),
    (lambda L: L["lora"].update(sha256="x"), "lora needs"),
])
def test_launch_problems_catch_each_broken_pin(change, needle):
    L = json.loads(json.dumps(LAUNCH))
    change(L)
    assert any(needle in p for p in M.launch_problems(L)), M.launch_problems(L)


def test_the_ltx_pins_are_the_protected_launches_pins_and_that_file_is_untouched():
    P = json.loads(PROTECTED.read_text(encoding="utf-8"))
    for k in ("model_repo", "model_revision", "model_files", "ltx_code", "base_image", "hf_hub_pin", "uses"):
        assert LAUNCH[k] == P[k], k
    assert LAUNCH["lora"]["revision"] == "bd765d5592f0ae78457162852a353b6a375cb00f"
    pins = json.loads((Path(M.LTX_DIR).parents[3] / "config" / "cloud_pins.json").read_text(encoding="utf-8"))
    pin = pins["models"]["video_ltx_layout_lora"]
    assert pin["revision"] == LAUNCH["lora"]["revision"] and LAUNCH["lora"]["sha256"] in json.dumps(pin)


def test_the_retired_era_list_does_not_name_the_new_worker():
    retired = (Path(M.LTX_DIR).parents[3] / "config" / "retired_era.json").read_text(encoding="utf-8")
    assert "modal_layout_jobs" not in retired and "launch_layout" not in retired


def test_cost_timeout_and_worker_sha_change_with_every_worker_file():
    assert M.cost_timeout(0.2, 2.9428, 60) == int(0.9 * (0.2 - 60 * 2.9428 / 3600) / 2.9428 * 3600)
    names = M.FILES
    assert set(names) == {"modal_layout_jobs.py", "layout_job.py", "ic_lora_run.py"}
    assert all((M.LTX_DIR / n).is_file() for n in names) and len(M.worker_sha()) == 64


# --- guards -------------------------------------------------------------------------------------------------------------------

def test_go_gate_needs_the_message_id_and_this_plans_hash():
    plan = "a" * 64
    assert M.go_gate({"EE_MODAL_GO": f"cmsg_01Abc:{plan[:12]}"}, plan) == f"cmsg_01Abc:{plan[:12]}"
    for env in ({}, {"EE_MODAL_GO": "yes"}, {"EE_MODAL_GO": f"cmsg_01Abc:{'b' * 12}"}):
        with pytest.raises(SystemExit):
            M.go_gate(env, plan)


def test_token_pair_must_be_the_modal1_pair():
    ok = {"MODAL1_TOKEN_ID": "i", "MODAL1_TOKEN_SECRET": "s", "MODAL1_PROFILE": "p", "MODAL_TOKEN_ID": "i", "MODAL_TOKEN_SECRET": "s",
          "MODAL_PROFILE": "p"}
    assert M.token_problems(ok) == []
    assert M.token_problems(dict(ok, MODAL_TOKEN_ID="other"))
    assert M.token_problems({})


def test_second_attempt_of_a_run_key_is_refused(tmp_path):
    commits = []
    assert M.claim_attempt(tmp_path, "run1_main", commit=lambda: commits.append(1)) is None
    err = M.claim_attempt(tmp_path, "run1_main")
    assert err and "second attempt" in err and commits == [1]
    assert M.claim_attempt(tmp_path, "run1_smoke") is None


def test_reserve_launch_refuses_a_repeat_and_settles_from_measured_seconds(tmp_path):
    led = str(tmp_path / "ledger.json")
    run = M.reserve_launch(led, "layout_smoke_x", 0.2, 2.0)
    with pytest.raises(SystemExit):
        M.reserve_launch(led, "layout_smoke_x", 0.2, 2.0)
    assert M.settle_launch(run, "layout_smoke_x", 100.0, 3.6) == pytest.approx(0.1)


def test_ledger_refuses_a_reservation_over_80_percent(tmp_path):
    led = str(tmp_path / "ledger.json")
    M.reserve_launch(led, "a", 1.4, 2.0)
    with pytest.raises(Exception):
        M.reserve_launch(led, "b", 0.4, 2.0)


# --- the copied helpers are the LTX worker's, byte for byte -------------------------------------------------------------------

@pytest.mark.parametrize("name", ["ltx_frames", "_grey_frames", "_lap_var_2d", "_crop_norm", "handover_scores", "speech_floor",
                                  "crop_filter", "frame_png", "handover_frame"])
def test_handover_helpers_equal_the_ltx_workers(name):
    a, b = inspect.getsource(getattr(J, name)), inspect.getsource(getattr(LTX, name))
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", re.sub(r'""".*?"""', "", s, flags=re.S))).strip()   # noqa: E731 - docstrings may differ
    assert norm(a) == norm(b), name


@pytest.mark.parametrize("name", ["tmp_name", "_files", "git_blob_id", "verify_uploads"])
def test_upload_helpers_equal_the_ltx_workers(name):
    a, b = inspect.getsource(getattr(M, name)), inspect.getsource(getattr(LTX, name))
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", re.sub(r'""".*?"""', "", s, flags=re.S))).strip()   # noqa: E731
    assert norm(a) == norm(b), name


def test_upload_round_differs_only_in_its_commit_message():
    a = inspect.getsource(M.upload_round).replace('f"layout: {len(new)} files"', "MSG")
    b = inspect.getsource(LTX.upload_round)
    msg = re.search(r"commit_message=(f?\"[^\"]*\"|f?'[^']*')", b).group(1)
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", re.sub(r'""".*?"""', "", s, flags=re.S))).strip()   # noqa: E731
    assert norm(a) == norm(b.replace(msg, "MSG")), msg


# --- the job rules (LR-1 .. LR-5) -------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jobdir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("job")
    R.make_job(folder, seconds=10.0, chain=1)         # real 241-frame grey layouts: the rules run on what ffprobe counts
    return folder


def _job(jobdir, **ch):
    job = json.loads((jobdir / "job.json").read_text())
    for k, v in ch.items():
        if v is None:
            job.pop(k, None)
        else:
            job[k] = v
    return job


def test_a_good_job_has_no_problems(jobdir):
    bad, warn = J.job_problems(_job(jobdir), jobdir, LAUNCH)
    assert bad == [] and warn == []


def test_size_and_frames_rules(jobdir):
    bad, _ = J.job_problems(_job(jobdir, width=1920, height=1088), jobdir, LAUNCH)
    assert any("CH-02" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir, seconds=11.0), jobdir, LAUNCH)
    assert any("longer than the model's" in p for p in bad) and any("the layout has 241 frames" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir, seed="7"), jobdir, LAUNCH)
    assert any("seed" in p for p in bad)


def test_layout_hash_and_probe_rules(jobdir):
    bad, _ = J.job_problems(_job(jobdir, layout_sha256="0" * 64), jobdir, LAUNCH)
    assert any("sha256 is not the one in the job" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir), jobdir, LAUNCH, probe=lambda p: dict(_probe_ok(p), frames=200))
    assert any("the layout has 200 frames" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir), jobdir, LAUNCH, probe=lambda p: dict(_probe_ok(p), width=640))
    assert any("CH-02" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir, layout_mp4="nope.mp4"), jobdir, LAUNCH)
    assert any("does not exist" in p for p in bad)


def test_first_picture_rules(jobdir, tmp_path):
    bad, _ = J.job_problems(_job(jobdir, first_picture="missing.png"), jobdir, LAUNCH)
    assert any("does not exist" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir, first_picture_sha256="0" * 64), jobdir, LAUNCH)
    assert any("first picture's sha256" in p for p in bad)
    (tmp_path / "junk.png").write_bytes(b"not an image")
    R.make_job(tmp_path / "j", seconds=9 / 24, chain=0)
    (tmp_path / "j" / "first.png").write_bytes(b"not an image")
    job = json.loads((tmp_path / "j" / "job.json").read_text())
    job["first_picture_sha256"] = R.sha(tmp_path / "j" / "first.png")
    bad, _ = J.job_problems(job, tmp_path / "j", LAUNCH, probe=lambda p: dict(_probe_ok(p), frames=9))
    assert any("not a readable image" in p for p in bad)


def test_grey_first_picture_is_a_warning_not_a_refusal(tmp_path):
    R.make_job(tmp_path, seconds=9 / 24, chain=0)
    R._png(tmp_path / "first.png", color=(128, 128, 128))
    job = json.loads((tmp_path / "job.json").read_text())
    job["first_picture_sha256"] = R.sha(tmp_path / "first.png")
    bad, warn = J.job_problems(job, tmp_path, LAUNCH)
    assert bad == [] and any("almost grey" in w for w in warn)


@pytest.mark.parametrize("prompt", ["A clay knight walks.", "A 3D knight walks.", "A knight in Unreal Engine walks.", "A 3-D knight walks."])
def test_forbidden_words_refuse_the_job(jobdir, prompt):
    bad, _ = J.job_problems(_job(jobdir, motion_prompt=prompt), jobdir, LAUNCH)
    assert any("forbids" in p for p in bad)


def test_prompt_is_one_or_two_sentences(jobdir):
    bad, _ = J.job_problems(_job(jobdir, motion_prompt="One. Two. Three."), jobdir, LAUNCH)
    assert any("3 sentences" in p for p in bad)
    bad, _ = J.job_problems(_job(jobdir, motion_prompt=""), jobdir, LAUNCH)
    assert any("motion_prompt is not set" in p for p in bad)
    # the film line (variant B) may push it over: a recorded warning, never a refusal
    bad, warn = J.job_problems(_job(jobdir, film_line="Shot on 35 mm film. Warm grain."), jobdir, LAUNCH)
    assert bad == [] and any("Q-L4" in w for w in warn)


def test_chain_rules_hops_and_no_own_picture(jobdir):
    job = _job(jobdir)
    job["chain"][0]["first_picture"] = "first.png"
    bad, _ = J.job_problems(job, jobdir, LAUNCH)
    assert any("brings no picture of its own" in p for p in bad)
    job = _job(jobdir)
    job["chain"][0]["hop"] = 2
    bad, _ = J.job_problems(job, jobdir, LAUNCH)
    assert any("is not its place 1" in p for p in bad)
    job = _job(jobdir)
    job["chain"] = job["chain"] * 3
    for i, c in enumerate(job["chain"]):
        job["chain"][i] = dict(c, shot_id=f"c{i}", hop=i + 1)
    bad, _ = J.job_problems(job, jobdir, LAUNCH)
    assert any("hop 3 needs the owner's word" in p for p in bad)
    job["hop3_word"] = "cmsg_01Yes"
    bad, _ = J.job_problems(job, jobdir, LAUNCH)
    assert not any("owner's word" in p for p in bad)


def test_duplicate_shot_ids_are_refused(jobdir):
    job = _job(jobdir)
    job["chain"][0]["shot_id"] = job["shot_id"]
    bad, _ = J.job_problems(job, jobdir, LAUNCH)
    assert any("unique plain names" in p for p in bad)


def test_pack_is_reproducible_sha_named_and_refuses_a_bad_job(tmp_path):
    folder = tmp_path / "f"
    R.make_job(folder, seconds=9 / 24, chain=1)
    a, sha_a = J.pack(folder, tmp_path / "o1", LAUNCH, smoke=True)
    b, sha_b = J.pack(folder, tmp_path / "o2", LAUNCH, smoke=True)
    assert sha_a == sha_b and a.name == f"batch-{sha_a}.tar.gz" and R.sha(a) == sha_a
    job = json.loads((folder / "job.json").read_text())
    job["motion_prompt"] = "A clay knight."
    (folder / "job.json").write_text(json.dumps(job))
    with pytest.raises(SystemExit):
        J.pack(folder, tmp_path / "o3", LAUNCH, smoke=True)
    assert not list((tmp_path / "o3").glob("batch-*")) if (tmp_path / "o3").exists() else True


# --- the command --------------------------------------------------------------------------------------------------------------

ROW = {"shot_id": "t1_a", "seed": 42, "seconds": 10.0, "fps": 24, "width": 1280, "height": 704}


def test_layout_cmd_has_every_argument_of_the_card_and_the_pinned_cli():
    cmd = J.layout_cmd(LAUNCH, ROW, "/p/first.png", "/p/layout.mp4", "/o/.t1_a.mp4", "A knight walks.", python="py")
    assert cmd[:3] == ["py", "-m", "ltx_pipelines.ic_lora"]

    def after(flag, n=1):
        i = cmd.index(flag)
        return cmd[i + 1:i + 1 + n]
    assert after("--lora", 2) == ["/w/model/Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render/"
                                  "ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors", "1.0"]
    assert after("--video-conditioning", 2) == ["/p/layout.mp4", "1.0"]
    assert after("--image", 3) == ["/p/first.png", "0", "1.0"]              # frame 0: the pinned CLI refuses a negative index
    assert "--stage-2-ic-lora" in cmd
    assert after("--num-frames") == ["241"] and after("--frame-rate") == ["24"] and after("--seed") == ["42"]
    assert after("--width") == ["1280"] and after("--height") == ["704"] and after("--output-path") == ["/o/.t1_a.mp4"]
    assert after("--prompt") == ["A knight walks."]
    assert "--negative-prompt" not in cmd and not any(a.startswith("--cfg") for a in cmd)     # not arguments of the distilled CLI
    assert cmd[cmd.index("--transformer-path") + 1].endswith("ltx-2.5-22b-distilled-transformer-bf16.safetensors")


def test_layout_cmd_through_the_wrapper_names_the_module_and_the_facts_file():
    cmd = J.layout_cmd(LAUNCH, ROW, "p", "l", "m", "x", python="py", wrapper="/r/ic_lora_run.py", vram_json="/o/v.json")
    assert cmd[:4] == ["py", "/r/ic_lora_run.py", "ltx_pipelines.ic_lora", "/o/v.json"] and "-m" not in cmd[:4]


def test_run_settings_record_every_setting_and_a_hash_of_the_argv():
    cmd = J.layout_cmd(LAUNCH, ROW, "p", "l", "m", "x", python="py")
    rs = J.run_settings(LAUNCH, ROW, "x", cmd)
    assert rs["settings"]["stage_2_ic_lora"] is True and rs["lora"]["sha256"] == LAUNCH["lora"]["sha256"] and rs["frames"] == 241
    assert len(rs["argv_sha256"]) == 64 and rs["ltx_commit"] == LAUNCH["ltx_code"]["commit"]


class _Stop(Exception):
    pass


def test_layout_cmd_is_accepted_by_the_real_ic_lora_main_when_installed(tmp_path, monkeypatch):
    """Runs the pinned ``ltx_pipelines.ic_lora.main`` up to the pipeline call (a stub records its arguments): proves every flag of
    ``layout_cmd`` exists, parses and lands where the docs say. Needs the pinned LTX-2 packages (torch), so it skips on a plain box."""
    pytest.importorskip("torch")
    ic = pytest.importorskip("ltx_pipelines.ic_lora")
    got = {}

    class Stub:
        def __init__(self, **kw):
            got["init"] = kw

        def stream_chunks(self, **kw):
            got["call"] = kw
            raise _Stop

    monkeypatch.setattr(ic, "ICLoraPipeline", Stub)
    files = {}
    for n in ("tr", "te", "vv", "av", "up", "lora"):
        files[n] = tmp_path / f"{n}.safetensors"
        files[n].write_bytes(b"x")
    launch = json.loads(json.dumps(LAUNCH))
    root = tmp_path / "w" / "model" / launch["model_repo"]
    for f in launch["uses"].values():
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"x")
    lp = M.lora_path(launch, tmp_path / "w")
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_bytes(b"x")
    R._png(tmp_path / "f.png", size=(1280, 704))
    R._layout(tmp_path / "l.mp4", 9)
    row = dict(ROW, seconds=9 / 24)
    cmd = J.layout_cmd(launch, row, tmp_path / "f.png", tmp_path / "l.mp4", tmp_path / "o.mp4", "A knight walks.", vol_root=tmp_path / "w",
                       python="py")
    monkeypatch.setattr(sys, "argv", ["ic_lora", *cmd[3:]])
    with pytest.raises(_Stop):
        ic.main()
    call = got["call"]
    assert (call["num_frames"], call["height"], call["width"], call["seed"], call["prompt"]) == (9, 704, 1280, 42, "A knight walks.")
    assert call["frame_rate"] == 24 and call["video_conditioning"][0][1] == 1.0 and len(call["images"]) == 1
    img = call["images"][0]
    assert img.binding.frame_idx == 0 and type(img.binding).__name__ == "ImageReplace" and img.strength == 1.0
    assert len(got["init"]["loras"]) == 1 and got["init"]["loras"][0].strength == 1.0
    # --stage-2-ic-lora reached the stage plan: the IC-LoRA stays on stage 2
    assert got["init"]["stages"] is not None


# --- helpers on the container side --------------------------------------------------------------------------------------------

def test_wrapper_writes_facts_on_every_exit_path(tmp_path):
    mod = tmp_path / "pk"
    mod.mkdir()
    (mod / "okmod.py").write_text("print('hi')\n")
    (mod / "exitmod.py").write_text("import sys\nsys.exit(3)\n")
    (mod / "boom.py").write_text("raise MemoryError('CUDA out of memory')\n")
    wrapper = M.LTX_DIR / "ic_lora_run.py"
    env = {"PYTHONPATH": str(mod), "PATH": "/usr/bin:/bin"}
    for name, code, status in (("okmod", 0, "ok"), ("exitmod", 3, "exit"), ("boom", 1, "raised")):
        out = tmp_path / f"{name}.json"
        r = subprocess.run([sys.executable, str(wrapper), name, str(out)], env=env, capture_output=True, text=True)
        assert r.returncode == code, (name, r.stderr[-200:])
        facts = json.loads(out.read_text())
        assert facts["status"] == status and facts["host_rss_peak_gib"] > 0
    assert "out of memory" in json.loads((tmp_path / "boom.json").read_text())["error"]


def test_gpu_poller_keeps_the_peak_of_nvidia_smi():
    seq = iter(["1024\n", "40960\n", "2048\n"])

    def sh(cmd, **kw):
        try:
            return type("R", (), {"stdout": next(seq)})()
        except StopIteration:
            return type("R", (), {"stdout": ""})()
    p = M.GpuPoller(sh=sh, every_s=0.01)
    with p:
        import time
        time.sleep(0.2)
    assert p.facts()["gpu_used_peak_gib"] == 40.0 and p.facts()["samples"] == 3


def test_check_weights_reports_each_kind_of_missing_file(tmp_path):
    w = R.make_world(tmp_path)
    assert M.check_weights(w.launch, w.vol, hash_lora=True, hash_base=True) == ["sha256 mismatch " + f for f in w.launch["uses"].values()] \
        or M.check_weights(w.launch, w.vol, hash_lora=True) == []
    assert M.check_weights(w.launch, w.vol, hash_lora=True) == []
    M.lora_path(w.launch, w.vol).write_bytes(b"x")
    assert any("IC-LoRA size" in p for p in M.check_weights(w.launch, w.vol, hash_lora=True))
    M.lora_path(w.launch, w.vol).unlink()
    assert any("missing IC-LoRA" in p for p in M.check_weights(w.launch, w.vol, hash_lora=False))


def test_stage_weights_downloads_only_what_the_volume_lacks(tmp_path):
    w = R.make_world(tmp_path)
    M.lora_path(w.launch, w.vol).unlink()
    got = []

    def dl(repo, rev, files, root):
        got.append((repo, rev, files))
        (Path(root) / files[0]).write_bytes(b"fake IC-LoRA")
    assert M.stage_weights(w.launch, w.vol, download=dl) == []
    assert got == [(w.launch["lora"]["repo"], w.launch["lora"]["revision"], [w.launch["lora"]["file"]])]
    assert M.stage_weights(w.launch, w.vol, download=dl) == [] and len(got) == 1      # present: nothing downloaded again


def test_fetch_batch_refuses_a_name_that_is_not_sha_named_and_a_wrong_hash(tmp_path):
    with pytest.raises(SystemExit):
        M.fetch_batch({"batch_path": "code/layout/batch-main.tar.gz", "batch_sha": "0" * 64}, tmp_path)
    f = tmp_path / "x.tar.gz"
    f.write_bytes(b"abc")
    with pytest.raises(SystemExit):
        M.fetch_batch({"batch_path": f"code/layout/batch-{'a' * 64}.tar.gz", "batch_sha": "a" * 64}, tmp_path, download=lambda n, d: f)


def test_tmp_name_keeps_the_mp4_suffix():
    assert M.tmp_name(Path("/o/t1_a.mp4")).name == ".t1_a.mp4"


# --- the container body, rehearsed on the CPU ---------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("FAKE_MODE", "FAKE_CLOCK_JUMP"):
        monkeypatch.delenv(k, raising=False)


def test_body_normal_run_two_clips_chained_saved_and_read_back(tmp_path):
    w = R.make_world(tmp_path, chain=1)
    res = R.run_body(w)
    assert res["state"] == "DONE" and res["error"] is None
    a, b = res["clips"]
    assert (a["shot_id"], a["state"], a["frames_out"], a["size_out"], a["sound"]) == ("t1_a", "DONE", 9, [1280, 704], False)
    assert b["state"] == "DONE" and b["first_picture"]["source"] == "previous clip's frame" and b["first_picture"]["handover"]["frame"] in range(9)
    assert a["first_picture"]["source"] == "job"
    # what the CLI got: the temp name keeps .mp4, the clip's own first picture, the composed prompt
    lines = w.log.read_text().splitlines()
    assert len(lines) == 2 and lines[0].split("|")[0].endswith("/.t1_a.mp4") and "t1_b1.first" not in lines[0]
    assert "t1_b1" in lines[1].split("|")[1] and lines[1].endswith("The knight turns and looks at the sea.")
    # saved to the Volume and to HF after each clip, then read back
    prefix = f"{w.launch['hf_out']}/{w.spec['run_id']}/main/"
    assert prefix + "t1_a.mp4" in w.api.files and prefix + "t1_b1.mp4" in w.api.files and prefix + "layout_record.json" in w.api.files
    assert len(w.api.commits) >= 3 and any(x.endswith("/t1_a.mp4") for x in w.api.commits[0])                     # the first clip left the container before the second began
    assert set(res["verified"].values()) == {"ok"}
    assert (w.vol / M.VOL_OUT / w.spec["run_id"] / "main" / "t1_a.mp4").is_file()
    assert (w.vol / "attempts_layout" / "main".join(["abc123_def456_", ".json"])).is_file()
    # nothing half-written is left under the output tree
    out = w.work / "out" / w.spec["run_id"] / "main"
    assert not [p for p in out.iterdir() if p.name.startswith(".") and p.suffix == ".mp4"]
    # the record carries every setting and measured fact the plan asks for
    assert a["run"]["settings"]["stage_2_ic_lora"] is True and a["run"]["frames"] == 9 and a["vram"]["host_rss_peak_gib"] > 0
    assert json.loads(json.dumps(res)) == res                                                # plain JSON only


def test_body_records_sound_when_the_clip_has_it(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "sound")
    w = R.make_world(tmp_path, chain=0)
    res = R.run_body(w)
    assert res["state"] == "DONE" and res["clips"][0]["sound"] is True


def test_body_smoke_is_one_clip_of_the_launch_smoke_frames(tmp_path):
    w = R.make_world(tmp_path, chain=0, kind="smoke")
    res = R.run_body(w)
    assert res["state"] == "DONE" and len(res["clips"]) == 1 and res["clips"][0]["frames_out"] == LAUNCH["smoke"]["frames"]
    prefix = f"{w.launch['hf_out']}/{w.spec['run_id']}/smoke/"
    assert prefix + "t1_a.mp4" in w.api.files


def test_body_smoke_refuses_a_chain_or_a_longer_clip(tmp_path):
    w = R.make_world(tmp_path, chain=1, kind="main")
    spec = dict(w.spec, kind="smoke", run_id="other_run")
    w.spec = spec
    res = R.run_body(w)
    assert res["state"] == "FAILED" and any("smoke job is one clip" in p for p in res["problems"])
    assert w.log.exists() is False


def test_body_second_attempt_is_refused_and_pays_nothing(tmp_path):
    w = R.make_world(tmp_path, chain=0)
    assert R.run_body(w)["state"] == "DONE"
    n = len(w.log.read_text().splitlines())
    again = R.run_body(w)
    assert again["state"] == "FAILED" and "second attempt" in again["error"] and len(w.log.read_text().splitlines()) == n


def test_body_deadline_in_the_middle_of_a_clip_ends_the_cli_and_keeps_what_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "sleep")
    w = R.make_world(tmp_path, chain=1)
    res = R.run_body(w, timeout_s=M.LAUNCH["caps"]["margin_s"] + 2)             # 2 s of work time: the CLI never finishes
    first = res["clips"][0]
    assert first["state"] == "PARTIAL" and first["rc"] is None and "deadline" in first["why"] and len(res["clips"]) == 1
    assert res["state"] == "FAILED"
    prefix = f"{w.launch['hf_out']}/{w.spec['run_id']}/main/"
    assert prefix + "layout_record.json" in w.api.files and not any(k.endswith(".mp4") for k in w.api.files)   # no half clip anywhere
    assert not list((w.work / "out").rglob(".*.mp4"))


def test_body_not_enough_time_left_for_the_next_clip_stops_without_starting_it(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_CLOCK_JUMP", "1000")                                 # the first clip "took" 1000 s on the body's clock
    w = R.make_world(tmp_path, chain=1)
    res = R.run_body(w, timeout_s=1500)
    assert [c["state"] for c in res["clips"]] == ["DONE", "PARTIAL"] and "not started" in res["clips"][1]["why"]
    assert res["state"] == "PARTIAL" and len(w.log.read_text().splitlines()) == 1
    assert f"{w.launch['hf_out']}/{w.spec['run_id']}/main/t1_a.mp4" in w.api.files


def test_body_a_failing_cli_is_a_failed_clip_and_the_chain_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "fail")
    w = R.make_world(tmp_path, chain=1)
    res = R.run_body(w)
    assert res["state"] == "FAILED" and res["clips"][0]["state"] == "FAILED" and res["clips"][0]["rc"] == 3 and len(res["clips"]) == 1
    assert json.loads((w.work / "out" / w.spec["run_id"] / "main" / "t1_a.vram.json").read_text())["status"] == "exit"


def test_body_storage_down_is_unverified_with_the_files_on_disk_and_on_the_volume(tmp_path):
    w = R.make_world(tmp_path, chain=0)
    res = R.run_body(w, api=R.FakeApi(down=True))
    assert res["state"] == "UPLOAD_UNVERIFIED" and set(res["verified"].values()) == {"missing on HF"}
    assert (w.work / "out" / w.spec["run_id"] / "main" / "t1_a.mp4").is_file()
    assert (w.vol / M.VOL_OUT / w.spec["run_id"] / "main" / "t1_a.mp4").is_file()


def test_body_refuses_unstaged_weights_and_a_wrong_batch_hash(tmp_path):
    w = R.make_world(tmp_path, chain=0)
    lp = M.lora_path(w.launch, w.vol)
    saved = lp.read_bytes()
    lp.unlink()
    assert "not staged" in R.run_body(w)["error"]
    lp.write_bytes(saved)
    w.spec = dict(w.spec, batch_sha="0" * 64, run_id="r2")
    res = R.run_body(w)
    assert res["state"] == "FAILED" and "nothing was run" in res["error"] and not w.log.exists()


def test_body_refuses_a_job_whose_prompt_has_a_forbidden_word_in_the_container(tmp_path):
    folder = tmp_path / "w"
    folder.mkdir()
    w = R.make_world(folder, chain=0)
    # the same job.json with a forbidden word, packed without the creator-side check
    import tarfile
    job = json.loads((w.work.parent / "job" / "job.json").read_text())
    job["motion_prompt"] = "A 3D knight walks."
    src = w.work.parent / "job"
    (src / "job.json").write_text(json.dumps(job))
    out = w.work.parent / "forced.tar.gz"
    with tarfile.open(out, "w:gz") as tf:
        for p in sorted(src.rglob("*")):
            tf.add(p, p.relative_to(src))
    w.tar, w.spec = out, dict(w.spec, batch_sha=R.sha(out), run_id="forced")
    res = R.run_body(w)
    assert res["state"] == "FAILED" and any("forbids" in p for p in res["problems"]) and not w.log.exists()


def test_body_refuses_a_launch_that_is_not_the_one_baked_into_the_image(tmp_path):
    w = R.make_world(tmp_path, chain=0)
    baked = tmp_path / "baked.json"
    baked.write_text(json.dumps(M.LAUNCH))
    res = M.body(w.spec, w.launch, timeout_s=3600, vol_root=w.vol, work=w.work, api=w.api, download=lambda n, d: w.tar, sh=w.sh,
                 poller_factory=R.NoPoller, sleep=lambda s: None, op_cls=R.FakeOp, baked=baked)
    assert res["state"] == "FAILED" and "baked into the image" in res["error"] and not w.log.exists()


def test_the_rehearsal_cli_runs_end_to_end(tmp_path):
    r = subprocess.run([sys.executable, "-m", "explainer_engine.training.pods.ltx.rehearse_layout_cpu", str(tmp_path)], capture_output=True,
                       text=True, cwd=str(Path(M.LTX_DIR).parents[3]))
    assert r.returncode == 0, r.stderr[-400:]
    assert '"state": "DONE"' in r.stdout


def test_chain_from_means_the_same_as_the_ltx_workers_with_the_launch_keys_of_each():
    ltx_launch = {"chain_overlap_frames": 0}
    for frames in (9, 97, 241):
        assert J.chain_from(LAUNCH, frames) == LTX.chain_from(ltx_launch, frames) == frames - 1
    with pytest.raises(ValueError):
        J.chain_from(dict(LAUNCH, chain=dict(LAUNCH["chain"], overlap_frames=300)), 241)


def test_a_paid_rung_without_a_paid_offer_is_refused_by_ch07_and_the_cpu_rungs_need_none():
    for entry in ("smoke", "main"):
        problems = M.offer_problems(LAUNCH, entry, {})
        assert len(problems) == 1 and problems[0].startswith("CH-07")
    assert M.WORKER_REL == "explainer_engine/training/pods/ltx/modal_layout_jobs.py" and (Path(M.LTX_DIR).parents[3] / M.WORKER_REL).is_file()
    with pytest.raises(SystemExit) as e:
        M.preflight(LAUNCH, entry="smoke", paid=True, env={})
    assert "paid preflight FAILED" in str(e.value)


def test_body_runs_without_imageio_and_without_the_hub_package(tmp_path, monkeypatch):
    """The CI box has ffmpeg, pillow and numpy but neither imageio nor huggingface_hub: the fake CLI falls back to ffmpeg and the body takes
    its commit-operation class from the caller."""
    monkeypatch.setenv("FAKE_NO_IMAGEIO", "1")
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)
    w = R.make_world(tmp_path, chain=0)
    res = R.run_body(w)
    assert res["state"] == "DONE" and res["clips"][0]["frames_out"] == 9 and set(res["verified"].values()) == {"ok"}


def test_an_unreadable_baked_folder_is_not_baked_not_a_crash(monkeypatch):
    """On a CI box /root is closed to the runner: stat() raises PermissionError there (found by the first CI run of this worker)."""
    real = Path.exists

    def exists(self, *a, **k):
        if str(self).startswith(str(M.BAKED)):
            raise PermissionError(13, "Permission denied", str(self))
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "exists", exists)
    assert M._wrapper_path() == M.LTX_DIR / "ic_lora_run.py"
    assert M.container_gate(M.LAUNCH) == []


# --- siblings: the T1 pair (the same first picture, another prompt) ----------------------------------------------------------------

def _sibling_job(folder):
    job = R.make_job(folder, seconds=9 / 24, chain=0)
    job["chain"] = [{"shot_id": "t1_b", "seed": 42, "seconds": 9 / 24, "start": "first_picture", "layout_mp4": job["layout_mp4"],
                     "layout_sha256": job["layout_sha256"], "motion_prompt": job["motion_prompt"],
                     "film_line": "In the style of the film 1917 (2019), the camera follows steadily behind him."}]
    (folder / "job.json").write_text(json.dumps(job))
    return job


def test_a_sibling_row_has_hop_0_its_own_film_line_and_no_picture_of_its_own(tmp_path):
    job = _sibling_job(tmp_path)
    assert J.job_problems(job, tmp_path, LAUNCH) == ([], [])
    rs = J.rows(job)
    assert [r["hop"] for r in rs] == [0, 0] and J.is_sibling(rs[1]) and not J.is_sibling(rs[0])
    assert J.compose_prompt(rs[1], rs[1]["film_line"]).endswith("behind him.") and "1917" not in J.compose_prompt(rs[0], None)
    bad = dict(job, chain=[dict(job["chain"][0], first_picture="first.png")])
    assert any("brings no picture" in p for p in J.job_problems(bad, tmp_path, LAUNCH)[0])
    bad = dict(job, chain=[dict(job["chain"][0], hop=1)])
    assert any("hop 0" in p for p in J.job_problems(bad, tmp_path, LAUNCH)[0])
    bad = dict(job, chain=[dict(job["chain"][0], start="elsewhere")])
    assert any("start must be" in p for p in J.job_problems(bad, tmp_path, LAUNCH)[0])
    bad = dict(job, chain=[dict(job["chain"][0], film_line="A clay film.")])
    assert any("forbids" in p for p in J.job_problems(bad, tmp_path, LAUNCH)[0])


def test_a_sibling_after_a_continuation_restarts_the_depth(tmp_path):
    job = _sibling_job(tmp_path)
    cont = {"shot_id": "t1_c", "seed": 9, "seconds": 9 / 24, "layout_mp4": job["layout_mp4"], "layout_sha256": job["layout_sha256"],
            "motion_prompt": "He stops."}
    job["chain"] = [cont, dict(job["chain"][0]), dict(cont, shot_id="t1_d")]
    assert [r["depth"] for r in J.rows(job)[1:]] == [1, 0, 1]
    assert J.job_problems(job, tmp_path, LAUNCH)[0] == []


def test_body_runs_the_pair_from_the_same_picture_with_two_prompts(tmp_path):
    w = R.make_world(tmp_path, chain=0)
    folder = tmp_path / "job"
    job = _sibling_job(folder)
    path, bsha = J.pack(folder, tmp_path / "pack2", w.launch, smoke=True)
    w.tar, w.spec = path, dict(w.spec, batch_sha=bsha, batch_path=f"code/layout/batch-{bsha}.tar.gz", run_id="pair")
    res = R.run_body(w)
    assert res["state"] == "DONE" and [c["shot_id"] for c in res["clips"]] == ["t1_a", "t1_b"]
    assert [c["first_picture"]["source"] for c in res["clips"]] == ["job", "job"]
    assert res["clips"][0]["first_picture"]["sha256"] == res["clips"][1]["first_picture"]["sha256"]      # the very same picture
    a, b = res["clips"]
    assert "1917" not in a["prompt"] and "1917 (2019)" in b["prompt"] and a["run"]["seed"] == b["run"]["seed"] == 42
    lines = w.log.read_text().splitlines()
    assert len(lines) == 2 and "1917" not in lines[0] and "1917 (2019)" in lines[1]


def test_the_module_imports_where_it_sits_at_the_container_root(tmp_path):
    """The first L1 run died in the container on ``LTX_DIR.parents[3]`` (the module is /root/modal_layout_jobs.py there) and the
    function hung until the 30-minute limit: the import must work from a shallow path with no shared gates folder."""
    import shutil
    import subprocess
    import sys
    import tempfile
    shallow = Path(tempfile.mkdtemp(dir="/tmp"))               # /tmp/xyz/file: only three parents, like /root/file in the image
    (shallow / "layout").mkdir()                              # the image: the worker at /root, the rest at /root/layout (BAKED)
    shutil.copy(Path(M.LTX_DIR) / "modal_layout_jobs.py", shallow / "modal_layout_jobs.py")
    for f in ("layout_job.py", "ic_lora_run.py", "launch_layout_a100.json"):
        shutil.copy(Path(M.LTX_DIR) / f, shallow / "layout" / f)
    src = (shallow / "modal_layout_jobs.py").read_text()      # the container has no /mnt/project-files and its BAKED is /root/layout
    assert 'SHARED_GATES = Path("/mnt/project-files' in src and 'BAKED = Path("/root/layout")' in src
    src = src.replace('SHARED_GATES = Path("/mnt/project-files', 'SHARED_GATES = Path("/nonexistent')
    (shallow / "modal_layout_jobs.py").write_text(src.replace('BAKED = Path("/root/layout")', f'BAKED = Path("{shallow}/layout")'))
    code = ("import importlib.util, sys\n"
            "s = importlib.util.spec_from_file_location('m', sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
            "print(m.LADDER_PATH, m.LAUNCH[\"gpu\"])")
    r = subprocess.run([sys.executable, "-c", code, str(shallow / "modal_layout_jobs.py")], capture_output=True, text=True,
                       cwd=str(Path(M.LTX_DIR).parents[3]))
    assert r.returncode == 0, r.stderr[-400:]
