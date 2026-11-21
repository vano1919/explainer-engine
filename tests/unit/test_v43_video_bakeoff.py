"""The v4.3 video bake-off (the creator, 2026-11-12 15:01 UTC; variants 1, 4, 5 at 15:12 UTC) after the Fable OR-34 audit
(A1-A5, B1-B7): the plan holds every pin, size, length and cap; timeouts come from the caps; the GO binds the plan's and the
worker's bytes; the work ends on time by itself and a rescheduled input is refused; every clip is written as it is made and its
HF copy is checked; the ledger reserves before and settles after, and a repeat is refused; the stage stamps what it checked so
the GPU never re-hashes; the local report upscales, conforms to 24 fps, measures and prices every clip, failed ones too.
No Modal, GPU or HF call: every container step is faked."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from explainer_engine.cloud import modal_schedule as MS
from explainer_engine.training.pods.bakeoff import modal_bakeoff as B
from explainer_engine.training.pods.bakeoff import report as R

PLAN = B.load_plan()
LINE = {"per_run_usd": 2.5, "tests_total_usd": 6.5}


def test_the_committed_plan_holds_and_keeps_only_the_creators_three_variants():
    assert B.plan_problems(PLAN) == []
    assert [v["id"] for v in PLAN["variants"]] == ["ltx_distilled", "wan_a14b_lightning", "wan_ti2v_5b"]
    assert PLAN["run_order"] == ["ltx_distilled", "wan_a14b_lightning", "wan_ti2v_5b"]
    assert PLAN["variants_chosen"]["message_id"].startswith("cmsg_")
    caps = sum(v["cap_usd"] for v in PLAN["variants"]) + PLAN["stage"]["cap_usd"]
    assert caps <= PLAN["total_cap_usd"] + 1e-9
    for v in PLAN["variants"]:
        assert 9.5 <= B.shot_seconds(v) <= 10.5
    light = B.variant(PLAN, "wan_a14b_lightning")
    assert light["scheduler"] == {**light["scheduler"], "class": "FlowMatchEulerDiscreteScheduler", "shift": 5.0}   # B1
    assert all(s.get("prompt_2") for s in PLAN["shots"])                                                              # B2


def test_prices_equal_the_modal_schedule_table():
    for g, usd in B.USD_S.items():
        assert MS.GPUS[g]["usd_s"] == usd
    assert (B.CPU_CORE_S, B.MEM_GIB_S) == (MS.CPU_CORE_S, MS.MEM_GIB_S)
    assert B.usd_per_h("H100!", 8, 96) == B.usd_per_h("H100", 8, 96)


def test_every_timeout_comes_from_its_cap():
    for v in PLAN["variants"]:
        t = B.timeout_of(PLAN, v)
        assert (PLAN["cold_start_s"] + t) * B.rate_of(v) / 3600 <= v["cap_usd"]
    bad = copy.deepcopy(PLAN)
    bad["variants"][0]["cap_usd"] = 0.01
    with pytest.raises(SystemExit, match="cold start"):
        B.timeout_of(bad, bad["variants"][0])
    assert B.stage_timeout(PLAN) * B.usd_per_h(None, PLAN["stage"]["cpu"], PLAN["stage"]["memory_gib"]) / 3600 \
        <= PLAN["stage"]["cap_usd"]


@pytest.mark.parametrize("break_it, why", [
    (lambda p: p["weights"]["ltx25"].__setitem__("revision", "main"), "no pinned revision"),
    (lambda p: p["shots"][0].__setitem__("sha256", None), "no sha256"),
    (lambda p: p["variants"][1].__setitem__("frames", 80), "grid"),
    (lambda p: p["variants"][2].__setitem__("clips", 1), "not 10 s"),
    (lambda p: p["variants"][0].__setitem__("gpu", "B300"), "unknown GPU"),
    (lambda p: p["variants"][0]["uses"].__setitem__("transformer", "x.safetensors"), "not a pinned file"),
    (lambda p: p.__setitem__("total_cap_usd", 1.0), "past the plan's total"),
    (lambda p: p["shots"][1].pop("prompt_2"), "prompt_2"),
    (lambda p: p.__setitem__("run_order", ["ltx_distilled"]), "run_order"),
    (lambda p: p.pop("ledger"), "no modal ledger"),
])
def test_a_broken_plan_is_refused(break_it, why):
    p = copy.deepcopy(PLAN)
    break_it(p)
    assert any(why in b for b in B.plan_problems(p))


def test_preflight_needs_the_creators_modal_line_over_every_cap_and_the_total():
    B.preflight(PLAN, line=LINE)
    with pytest.raises(SystemExit, match="above the creator"):
        B.preflight(PLAN, line={"per_run_usd": 1.0, "tests_total_usd": 6.5})
    with pytest.raises(SystemExit, match="tests_total_usd"):
        B.preflight(PLAN, line={"per_run_usd": 2.5})


def test_the_go_binds_the_plans_and_the_workers_bytes():
    sha = B.go_sha()
    assert sha == hashlib.sha256((B.plan_sha() + B.worker_sha()).encode()).hexdigest()
    assert B.go_sha(B.plan_sha(), "0" * 64) != sha
    assert B.go_gate({"EE_MODAL_GO": f"cmsg_1A:{sha[:12]}"}, sha) == "cmsg_1A"
    with pytest.raises(SystemExit, match="another plan"):
        B.go_gate({"EE_MODAL_GO": "cmsg_1A:000000000000"}, sha)
    with pytest.raises(SystemExit):
        B.go_gate({}, sha)
    assert B.token_ok(B.token_for("cmsg_1A", sha), sha) and not B.token_ok("", sha) and not B.token_ok("cmsg_1A:0" * 1, sha)


def test_join_shows_the_anchor_frame_once_like_the_splice_spec():
    from explainer_engine.aivideo import wan_optimizer as WO
    a, b = list(range(81)), list(range(100, 181))     # b[0] is made from a[76] = frame[-5]
    j = B.join_clips([a, b], 5)
    spec = WO.compute_continuation_splice_spec(81, 81, offset_from_end=5, fps=16)
    assert len(j) == spec["prev_clip_play_frames_before_splice"] + 81 and j[75] == 75 and j[76] == 100
    assert B.chained_frames(B.variant(PLAN, "wan_a14b_lightning")) == len(j)
    s = PLAN["shots"][1]
    assert B.clip_prompt(s, 0) == s["prompt"] and B.clip_prompt(s, 1) == s["prompt_2"]


def test_fit_picture_centre_crops_to_the_clip():
    from PIL import Image
    assert B.fit_picture(Image.new("RGB", (2752, 1536)), 1280, 704).size == (1280, 704)


def test_the_deadline_raises_inside_the_work_and_refuses_a_clip_that_cannot_finish():
    clock = [1000.0]
    d = B.Deadline(600, margin_s=100, now=lambda: clock[0])
    assert d.left() == 500 and d.fits(None) and d.fits(400) and not d.fits(460)
    clock[0] += 501
    with pytest.raises(B.DeadlineHit):
        d.check()


def test_a_rescheduled_input_is_refused_by_its_attempt_marker(tmp_path):
    assert B.attempt_guard(tmp_path, "rid", "v", "n1") is None
    assert B.attempt_guard(tmp_path, "rid", "v", "n1") == "REFUSED_SECOND_ATTEMPT"
    assert B.attempt_guard(tmp_path, "rid", "v", "n2") is None          # a deliberate new launch has a new nonce


def test_no_code_path_kills_its_own_process():
    src = Path(B.__file__).read_text()
    assert "os._exit" not in src and "threading.Timer" not in src


def test_stage_downloads_only_what_is_missing_checks_every_sha_and_stamps_the_set(tmp_path):
    w = {"repo": "o/r", "revision": "a" * 40, "files": {"have.bin": hashlib.sha256(b"have").hexdigest(),
                                                         "new.bin": hashlib.sha256(b"new").hexdigest()}}
    plan = {"weights": {"w": w}}
    root = tmp_path / "model" / "o/r"
    root.mkdir(parents=True)
    (root / "have.bin").write_bytes(b"have")
    asked = []

    def dl(repo, rev, files, r):
        asked.append((repo, rev, list(files)))
        (Path(r) / "new.bin").write_bytes(b"new")
    assert B.stamp_ok(w, str(tmp_path))[0].endswith("run ::stage first")
    assert B.stage_weights(plan, str(tmp_path), dl) == []
    assert asked == [("o/r", "a" * 40, ["new.bin"])]
    assert B.stamp_ok(w, str(tmp_path)) == []                           # the GPU checks the stamp and sizes, no hashing
    (root / "new.bin").write_bytes(b"longer!")
    assert any("size differs" in b for b in B.stamp_ok(w, str(tmp_path)))
    assert any("delete it" in b for b in B.stage_weights(plan, str(tmp_path), dl))
    w2 = dict(w, files={**w["files"], "more.bin": "c" * 64})
    assert any("another file set" in b for b in B.stamp_ok(w2, str(tmp_path)))


def test_the_ltx_command_names_the_pinned_files_and_the_start_picture():
    import sys
    v = B.variant(PLAN, "ltx_distilled")
    cmd = B.ltx_cmd(PLAN, v, PLAN["shots"][0], "/tmp/in/p.png", "/o/dialogue.mp4")
    s = " ".join(cmd)
    assert cmd[:3] == [sys.executable, "-m", "ltx_pipelines.distilled"]
    for f in PLAN["weights"]["ltx25"]["files"]:
        assert f in s
    assert "--image /tmp/in/p.png 0 1.0" in s and "--num-frames 241" in s and "--frame-rate 24" in s
    assert "--distilled-lora" not in s


def _pics(tmp_path):
    from PIL import Image
    pics = {}
    for s in PLAN["shots"]:
        p = tmp_path / f"{s['id']}.png"
        Image.new("RGB", (640, 360)).save(p)
        pics[s["id"]] = p
    return pics


def test_make_ltx_bounds_each_shot_by_the_time_left_and_stops_after_a_failure(tmp_path):
    v = B.variant(PLAN, "ltx_distilled")
    seen = []

    def fake_sh(cmd, **kw):
        seen.append(kw["timeout"])
        mp4 = Path(cmd[cmd.index("--output-path") + 1])
        mp4.write_bytes(b"video")
        return subprocess.CompletedProcess(cmd, 0)
    rows = B.make_ltx(PLAN, v, str(tmp_path), _pics(tmp_path), B.Deadline(900, margin_s=100), {}, beat_fn=lambda *a, **k: None,
                      sh=fake_sh, tmp=str(tmp_path / "in"))
    assert [r["state"] for r in rows] == ["DONE", "DONE"] and all(0 < t <= 800 for t in seen)

    def timeout_sh(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])
    rows = B.make_ltx(PLAN, v, str(tmp_path), _pics(tmp_path), B.Deadline(900, margin_s=100), {}, beat_fn=lambda *a, **k: None,
                      sh=timeout_sh, tmp=str(tmp_path / "in"))
    assert [r["state"] for r in rows] == ["PARTIAL"] and "deadline" in rows[0]["why"]


def test_run_state_says_done_only_when_every_shot_is_made_and_on_hf():
    done = [{"state": "DONE"}, {"state": "DONE"}]
    assert B.run_state(done, 2, {"a": "ok"}) == "DONE"
    assert B.run_state(done, 2, {"a": "missing on HF"}) == "UPLOAD_UNVERIFIED"
    assert B.run_state([{"state": "DONE"}, {"state": "PARTIAL"}], 2, {}) == "PARTIAL"
    assert B.run_state([{"state": "FAILED"}], 2, {}) == "FAILED"
    assert B.run_state([], 2, {}, error="SystemExit: x") == "FAILED"
    assert B.run_state(done, 2, {}, error="DeadlineHit: x") == "PARTIAL"


def OP(path_in_repo, path_or_fileobj):
    return SimpleNamespace(path_in_repo=path_in_repo, path_or_fileobj=path_or_fileobj)


class FakeApi:
    def __init__(self, fail=0):
        self.commits, self.fail, self.store = [], fail, {}

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        if self.fail:
            self.fail -= 1
            raise RuntimeError("429")
        self.commits.append([o.path_in_repo for o in operations])
        for o in operations:
            self.store[o.path_in_repo] = Path(o.path_or_fileobj).read_bytes()

    def get_paths_info(self, repo, paths, repo_type, expand):
        out = []
        for p in paths:
            if p in self.store:
                data = self.store[p]
                if p.endswith(".mp4"):
                    out.append(SimpleNamespace(path=p, lfs=SimpleNamespace(sha256=hashlib.sha256(data).hexdigest()), blob_id=None))
                else:
                    out.append(SimpleNamespace(path=p, lfs=None,
                                               blob_id=hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()))
        return out


def test_uploads_are_batched_retried_and_checked_back_on_hf(tmp_path):
    root = tmp_path / "rid"
    (root / "v").mkdir(parents=True)
    (root / "v" / "a.clip1.mp4").write_bytes(b"clip")
    (root / "v" / "measured.json").write_text("{}")
    (root / "v" / "x.mp4.tmp").write_bytes(b"half")                      # an encoder's temp file is never sent
    api, seen = FakeApi(fail=1), {}
    assert B.upload_round(api, root, "pre/rid", "o/r", seen, final=True, sleep=lambda s: None, op=OP) == 2
    assert len(api.commits) == 1 and sorted(api.commits[0]) == ["pre/rid/v/a.clip1.mp4", "pre/rid/v/measured.json"]
    assert B.upload_round(api, root, "pre/rid", "o/r", seen, sleep=lambda s: None, op=OP) == 0  # nothing new, no commit
    assert B.verify_uploads(api, root / "v", "pre/rid/v", "o/r") == {"a.clip1.mp4": "ok", "measured.json": "ok"}
    (root / "v" / "b.mp4").write_bytes(b"never sent")
    api.store["pre/rid/v/a.clip1.mp4"] = b"other"
    v = B.verify_uploads(api, root / "v", "pre/rid/v", "o/r")
    assert v["b.mp4"] == "missing on HF" and v["a.clip1.mp4"] == "hash differs on HF"
    assert B.upload_round(FakeApi(fail=9), root, "pre/rid", "o/r", {}, sleep=lambda s: None, op=OP) == 0


def test_the_ledger_reserves_the_cap_before_settles_after_and_refuses_a_repeat(tmp_path):
    led = B.open_ledger(PLAN, tmp_path / "led" / "bakeoff.json")
    assert led.data["caps"]["modal"] == PLAN["total_cap_usd"]
    v = B.variant(PLAN, "ltx_distilled")
    assert B.repeat_reason(PLAN, "rid", v["id"], led, lambda p: False) is None
    item = B.reserve(PLAN, v, "rid", led, "n1")
    assert led.spent("modal") == v["cap_usd"]
    assert "ledger already holds" in B.repeat_reason(PLAN, "rid", v["id"], led, lambda p: False)
    usd = B.settle(PLAN, v, item, led, 600)
    assert abs(usd - 600 * B.rate_of(v) / 3600) < 1e-3 and abs(led.spent("modal") - usd) < 1e-9
    assert "HF already has" in B.repeat_reason(PLAN, "rid2", v["id"], led, lambda p: p.endswith("measured.json"))
    big = B.variant(PLAN, "wan_ti2v_5b")
    B.reserve(PLAN, B.variant(PLAN, "wan_a14b_lightning"), "rid", led, "n2")
    from explainer_engine.core.ledger import CapReached
    led.data["spent"]["modal"] = 4.0
    with pytest.raises(CapReached):                                       # the 80 % stop of the plan's total holds
        B.reserve(PLAN, big, "rid", led, "n3")


def test_metrics_find_motion_frozen_runs_and_start_faithfulness():
    start = np.full((18, 32, 3), 100.0, dtype=np.float32)
    frames = [start + i * 2 for i in range(10)] + [start + 18] * 6
    m = R.metrics(frames, start)
    assert m["frames"] == 16 and m["start_diff"] == 0.0
    assert m["longest_still"] == 7 and m["motion"] > 0 and m["drift"] > 0
    assert R.metrics([]) == {"frames": 0}


def test_costs_use_the_ledger_and_charge_a_run_without_a_record_at_its_cap():
    measured = {"wan_ti2v_5b": {"state": "DONE", "body_s": 600.0,
                                "shots": [{"shot": "dialogue", "gen_s": 200}, {"shot": "action", "gen_s": 200}]}}
    c = R.costs(PLAN, measured)["wan_ti2v_5b"]
    v = B.variant(PLAN, "wan_ti2v_5b")
    want = (600 + PLAN["cold_start_s"]) * B.rate_of(v) / 3600
    assert abs(c["usd"] - want) < 1e-3 and abs(c["per_shot_usd"]["dialogue"] - want / 2) < 1e-3
    led = {"reserved": {"bakeoff/rid/wan_ti2v_5b/n1": {"service": "modal", "amount": 1.234, "settled": True},
                        "bakeoff/rid/ltx_distilled/n2": {"service": "modal", "amount": 1.5}}}
    assert R.ledger_usd(led, "rid") == {"wan_ti2v_5b": 1.234}
    money = R.costs(PLAN, measured, R.ledger_usd(led, "rid"), no_record=["ltx_distilled"])
    assert money["wan_ti2v_5b"]["usd"] == 1.234 and money["wan_ti2v_5b"]["source"] == "ledger"
    assert money["ltx_distilled"]["usd"] == B.variant(PLAN, "ltx_distilled")["cap_usd"] and "NO_RECORD" in money["ltx_distilled"]["state"]


def _clip(path, frames=24, size=(320, 176), fps=16, audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size[0]}x{size[1]}:rate={fps}:duration={frames / fps}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={frames / fps}", "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_report_upscales_conforms_measures_and_prices_every_clip(tmp_path):
    from PIL import Image
    src = tmp_path / "src"
    src.mkdir()
    Image.new("RGB", (640, 352), (90, 90, 90)).save(src / "pic.jpg")
    rid = "abc_def"
    files = {}
    for v in PLAN["variants"][:2]:
        base = f"{PLAN['hf_out']}/{rid}/{v['id']}"
        m = {"state": "DONE", "body_s": 300.0, "shots": [{"shot": s["id"], "gen_s": 100} for s in PLAN["shots"]]}
        (src / f"{v['id']}.json").write_text(json.dumps(m))
        files[f"{base}/measured.json"] = src / f"{v['id']}.json"
        for s in PLAN["shots"]:
            fam = v["family"] == "ltx"
            files[f"{base}/{s['id']}.mp4"] = _clip(src / f"{v['id']}_{s['id']}.mp4", fps=24 if fam else 16, audio=fam)
    (src / "beat.json").write_text("{}")
    files[f"{PLAN['hf_out']}/{rid}/wan_ti2v_5b/beat.json"] = src / "beat.json"    # it started and left no record
    for s in PLAN["shots"]:
        files[s["picture"]] = src / "pic.jpg"

    def fetch(path, local):
        if path not in files:
            raise FileNotFoundError(path)
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        Path(local).write_bytes(files[path].read_bytes())
        return local
    up = []
    rep = R.build(PLAN, rid, tmp_path / "out", fetch, lambda local, path: up.append(path) or f"https://hf/{path}")
    made = [r for r in rep["rows"] if r["state"] == "made"]
    assert len(made) == 4 and all(r["hf_2k"].startswith("https://hf/") for r in made)
    for r in made:
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate",
                            "-of", "csv=p=0", r["file_2k"]], capture_output=True, text=True).stdout.strip()
        assert p == "2560,1440,24/1"                                       # B6: the delivery rate, Wan's 16 fps too
        assert r["usd"] > 0 and r["motion"] > 0
    assert any(r["sound"] for r in made) and not all(r["sound"] for r in made)
    assert R.has_audio(Path([r for r in made if r["sound"]][0]["file_2k"]))
    assert "NO_RECORD" in rep["money"]["wan_ti2v_5b"]["state"]              # A3: a died run is still in the money
    assert rep["total_usd"] >= B.variant(PLAN, "wan_ti2v_5b")["cap_usd"]
    assert "contact_sheet.png" in " ".join(up)


# --- the container path with a fake pipeline (delta audit N1, N2, N3: write_clip, make_wan and body had no test) ----------------

class FakeEuler:
    """Stands in for diffusers' FlowMatchEulerDiscreteScheduler: records the sigmas it is given."""

    def __init__(self, **cfg):
        self.config, self.sigmas_seen = cfg, None

    @classmethod
    def from_config(cls, config, **kw):
        return cls(**{**config, **kw})

    def set_timesteps(self, num_inference_steps=None, device=None, sigmas=None, **kw):
        self.sigmas_seen = sigmas
        sh = self.config["shift"]
        self.timesteps = [1000.0 * sh * s / (1 + (sh - 1) * s) for s in sigmas]


class FakePipe:
    calls = []

    def __init__(self):
        self.scheduler = SimpleNamespace(config={"flow_shift": 3.0}, set_timesteps=lambda n, **k: None)   # the repo's own

    @classmethod
    def from_pretrained(cls, path, **kw):
        return cls()

    def load_lora_weights(self, *a, **k):
        pass

    def set_adapters(self, *a, **k):
        pass

    def enable_model_cpu_offload(self):
        pass

    def to(self, d):
        return self

    def __call__(self, image, prompt, height, width, num_frames, generator, callback_on_step_end, output_type,
                 num_inference_steps, **kw):
        self.scheduler.set_timesteps(num_inference_steps)
        FakePipe.calls.append({"prompt": prompt, "timesteps": list(getattr(self.scheduler, "timesteps", []))})
        for i in range(num_inference_steps):
            callback_on_step_end(self, i, 0, {})
        return SimpleNamespace(frames=[np.random.rand(num_frames, height, width, 3).astype(np.float32)])


def _export_to_video(frames, path, fps=10, quality=5):
    """imageio's rule: the writer is picked by the file's suffix (a '.tmp' name has none, delta audit N1)."""
    if Path(path).suffix not in (".mp4", ".mov", ".mkv"):
        raise ValueError(f"Could not find a backend to open '{path}' with iomode 'w?'")
    Path(path).write_bytes(b"MP4" + np.asarray(frames[:1]).tobytes()[:64] + bytes([len(frames) % 256]))


@pytest.fixture
def container(tmp_path, monkeypatch):
    import sys
    import types
    from PIL import Image
    d = types.ModuleType("diffusers")
    d.WanImageToVideoPipeline, d.FlowMatchEulerDiscreteScheduler = FakePipe, FakeEuler
    d.AutoencoderKLWan = SimpleNamespace(from_pretrained=lambda *a, **k: object())
    du = types.ModuleType("diffusers.utils")
    du.export_to_video = _export_to_video
    d.utils = du
    t = types.ModuleType("torch")
    t.Generator = lambda dev=None: SimpleNamespace(manual_seed=lambda s: None)
    t.float32 = t.bfloat16 = None
    hh = types.ModuleType("huggingface_hub")
    api = FakeApi()
    hh.HfApi = lambda token=None: api
    hh.CommitOperationAdd = OP
    for name, mod in (("diffusers", d), ("diffusers.utils", du), ("torch", t), ("huggingface_hub", hh)):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(B, "OUT_ROOT", tmp_path / "out")
    monkeypatch.setattr(B, "VOL_OUT", tmp_path / "vol")
    pic = tmp_path / "pic.png"
    Image.new("RGB", (640, 360), (90, 80, 70)).save(pic)
    monkeypatch.setattr(B, "_picture", lambda plan, shot, root=None: str(pic))
    monkeypatch.setattr(B, "stamp_ok", lambda w, vol_root="/w": [])
    monkeypatch.setattr(B, "_tok", lambda: "x")
    monkeypatch.setattr(B, "libs", lambda: {})
    FakePipe.calls = []
    plan = copy.deepcopy(PLAN)
    for v in plan["variants"]:
        v["width"], v["height"] = 320, 192
    return SimpleNamespace(plan=plan, api=api, tmp=tmp_path)


def test_the_clip_writer_keeps_the_suffix_and_the_uploader_skips_its_temp_name(tmp_path, container):
    tmp_path = tmp_path / "w"
    tmp_path.mkdir()
    p = B.write_clip(np.zeros((5, 8, 8, 3), np.float32), tmp_path / "dialogue.clip1.mp4", 16)
    assert p.is_file() and not B.tmp_name(p).exists() and B.tmp_name(p).name == ".dialogue.clip1.mp4"
    B.tmp_name(p).write_bytes(b"half")
    assert [q.name for q, _ in B._files(tmp_path)] == ["dialogue.clip1.mp4"]


def test_a_wan_run_writes_every_clip_verifies_it_on_hf_and_keeps_a_volume_copy(container):
    m = B.body(container.plan, "wan_a14b_lightning", "rid", "n1", 1110)
    assert m["state"] == "DONE", m
    out = container.tmp / "out" / "rid" / "wan_a14b_lightning"
    for s in ("dialogue", "action"):
        assert (out / f"{s}.clip1.mp4").is_file() and (out / f"{s}.clip2.mp4").is_file() and (out / f"{s}.mp4").is_file()
    assert set(m["verified"].values()) == {"ok"}
    assert (container.tmp / "vol" / "rid" / "wan_a14b_lightning" / "verified.json").is_file()
    prompts = [c["prompt"] for c in FakePipe.calls]
    assert prompts[1] == PLAN["shots"][0]["prompt_2"] and prompts[2] == PLAN["shots"][1]["prompt"]
    assert [round(x, 1) for x in FakePipe.calls[0]["timesteps"]] == [1000.0, 937.5, 833.3, 625.0]      # N3: the authors' steps
    assert B.body(container.plan, "wan_a14b_lightning", "rid", "n1", 1110)["state"] == "REFUSED_SECOND_ATTEMPT"


def test_a_deadline_in_clip_two_keeps_clip_one_on_hf_and_on_the_volume(container, monkeypatch):
    n, steps = [0], B.variant(PLAN, "wan_ti2v_5b")["settings"]["num_inference_steps"]
    real = B.Deadline.check

    def check(self):
        n[0] += 1
        if n[0] == steps + 2:                                           # the 2nd step of clip 2 of the first shot
            raise B.DeadlineHit("the in-container deadline came")
        return real(self)
    monkeypatch.setattr(B.Deadline, "check", check)
    m = B.body(container.plan, "wan_ti2v_5b", "rid", "n1", 1512)
    assert m["state"] == "PARTIAL" and "DeadlineHit" in m["error"]
    assert m["verified"]["dialogue.clip1.mp4"] == "ok"
    assert (container.tmp / "vol" / "rid" / "wan_ti2v_5b" / "dialogue.clip1.mp4").is_file()


def test_with_hf_down_the_volume_copy_comes_first_and_the_end_path_stays_inside_the_timeout(container, monkeypatch):
    container.api.fail = 10 ** 6
    slept = []
    real = B.upload_round
    monkeypatch.setattr(B, "upload_round", lambda *a, **k: real(*a, **{**k, "sleep": slept.append}))
    m = B.body(container.plan, "wan_a14b_lightning", "rid", "n1", 1110)
    assert m["state"] == "UPLOAD_UNVERIFIED"
    assert (container.tmp / "vol" / "rid" / "wan_a14b_lightning" / "action.mp4").is_file()
    assert sum(slept) <= B.MARGIN_S + 1110                           # the backoff is bounded by the time left


def test_the_final_flush_never_sleeps_after_its_last_try_nor_past_its_budget(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    slept = []
    assert B.upload_round(FakeApi(fail=99), tmp_path, "p", "r", {}, final=True, sleep=slept.append, op=OP) == 0
    assert slept == [15.0, 30.0, 60.0, 120.0, 240.0]
    slept.clear()
    B.upload_round(FakeApi(fail=99), tmp_path, "p", "r", {}, final=True, sleep=slept.append, op=OP, budget_s=100)
    assert sum(slept) <= 100


def test_lightning_timesteps_are_the_authors():
    assert B.shifted_timesteps(4, 5.0) == [1000.0, 937.5, 833.3, 625.0]
    assert B.variant(PLAN, "wan_a14b_lightning")["scheduler"]["timesteps"] == B.shifted_timesteps(4, 5.0)
    assert B.linear_sigmas(4) == [1.0, 0.75, 0.5, 0.25]


def test_the_creators_bakeoff_line_is_its_own_and_leaves_the_wan_route_at_zero():
    from explainer_engine.core import spend_caps
    line = spend_caps.modal_bakeoff()
    assert line["per_run_usd"] == 2.5 and line["tests_total_usd"] == 6.5 and "cmsg_" in line["decided"]
    assert max(v["cap_usd"] for v in PLAN["variants"]) <= line["per_run_usd"] and PLAN["total_cap_usd"] <= line["tests_total_usd"]
    with pytest.raises(spend_caps.OverCeiling, match="zero approved budget"):
        spend_caps.modal()
    B.preflight(PLAN)
