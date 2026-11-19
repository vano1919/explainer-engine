"""W5 (final plan 2026-11-19, P-6, CT-2): the LTX worker's job kinds keyframes / upscale_x2 / retake / a2v. A fake pipeline stands
in for the official CLI (no Modal, GPU or HF call): the job spec, the written-out run record, the refusal of an unpinned or
mismatched file, the conditioning stills (start replace, end guide), the sha-checked staging of a retake source, and that a kind
job runs through the same body (attempt marker, deadline, per-clip save, upload check) as a clip."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

LAUNCH = L.load_launch()
PINS = json.loads((Path(L.__file__).resolve().parents[4] / "config" / "cloud_pins.json").read_text())["models"]["video_ltx"]
SETTINGS = dict(LAUNCH["kind_defaults"])
SETTINGS = {k: SETTINGS[k] for k in L.KIND_SETTINGS} | {"image_strength": 1.0}
SHA = "ab" * 32


def _job(kind="keyframes", **kw):
    j = {"kind": kind, "shot_id": "S07_SH008", "seconds": 8.25, "fps": 24, "width": 1280, "height": 704, "seed": 7112,
         "motion_prompt": "Thomas climbs down, picks up his rifle and steps onto the fire step.", "settings": dict(SETTINGS),
         "start_sha256": SHA}
    if kind == "keyframes":
        j.update(end_picture="end.png", end_frame=200, extra={"end_sha256": SHA})
    if kind == "retake":
        j.update(source={"hf_path": "x/clip.mp4", "sha256": SHA}, start_time=2.0, end_time=4.0)
        j["settings"] = {"num_inference_steps": 8}
    if kind == "a2v":
        j.update(audio={"hf_path": "x/line.wav", "sha256": SHA})
    return dict(j, **kw)


def test_the_kind_files_are_pinned_and_equal_the_cloud_pins():
    assert L.launch_problems(LAUNCH) == []
    for role, f in LAUNCH["kind_uses"].items():
        assert LAUNCH["kind_model_files"][f] == PINS["sha256_files"][f], role
    up = LAUNCH["uses"]["spatial_upsampler"]
    assert LAUNCH["model_files"][up] == PINS["sha256_files"][up] and PINS["revision"] == LAUNCH["model_revision"]
    assert L.kind_launch_problems(dict(LAUNCH, kind_model_files={"f": "short"})) != []


@pytest.mark.parametrize("kind", ["keyframes", "upscale_x2", "retake", "a2v"])
def test_a_complete_job_of_every_kind_has_no_problem(kind):
    assert L.kind_problems(LAUNCH, _job(kind), PINS) == []


def test_the_default_kind_is_the_untouched_distilled_clip():
    assert L.kind_of({}) == "clip" and L.kind_problems(LAUNCH, {}) == []
    assert L.kind_problems(LAUNCH, {"kind": "extend"})[0].startswith("job kind 'extend' is not built")


def test_an_unpinned_or_mismatched_file_is_refused():
    no_dev = copy.deepcopy(LAUNCH)
    no_dev["kind_uses"].pop("dev_transformer")
    assert any("dev_transformer" in p for p in L.kind_problems(no_dev, _job(), PINS))
    wrong = copy.deepcopy(LAUNCH)
    f = wrong["kind_uses"]["distilled_lora"]
    wrong["kind_model_files"][f] = "00" * 32
    assert any("config/cloud_pins.json" in p for p in L.kind_problems(wrong, _job("a2v"), PINS))
    nosha = copy.deepcopy(LAUNCH)
    nosha["kind_model_files"][f] = "nothex"
    assert L.kind_problems(nosha, _job("upscale_x2"), PINS)
    other_rev = dict(LAUNCH, model_revision="0" * 40)
    assert any("model_revision" in p for p in L.kind_problems(other_rev, _job(), PINS))
    for own in ("transformer_path", "distilled_lora", "spatial_upsampler_path", "loras"):
        assert any(own in p for p in L.kind_problems(LAUNCH, _job(**{own: "/tmp/x.safetensors"}), PINS))
    # retake needs no extra files, but still never an own checkpoint
    assert any("checkpoint_path" in p for p in L.kind_problems(LAUNCH, _job("retake", checkpoint_path="/x"), PINS))
    assert any("transformer_path" in p for p in L.kind_problems(LAUNCH, _job("retake", transformer_path="/x"), PINS))


def test_every_setting_must_be_written_out_and_native():
    j = _job()
    j["settings"].pop("video_cfg_guidance_scale")
    assert any("video_cfg_guidance_scale" in p for p in L.kind_problems(LAUNCH, j, PINS))
    assert any("not native" in p for p in L.kind_problems(LAUNCH, _job(width=1920, height=1088), PINS))
    assert any("longer than" in p for p in L.kind_problems(LAUNCH, _job(seconds=11.0), PINS))
    assert any("end_frame" in p for p in L.kind_problems(LAUNCH, _job(end_frame=0), PINS))
    assert any("end_picture" in p for p in L.kind_problems(LAUNCH, _job(end_picture=None, extra={}), PINS))
    assert any("takes no end picture" in p for p in L.kind_problems(LAUNCH, _job("upscale_x2", end_picture="e.png"), PINS))
    assert any("start_time" in p for p in L.kind_problems(LAUNCH, _job("retake", start_time=4.0, end_time=2.0), PINS))
    assert any("source" in p for p in L.kind_problems(LAUNCH, _job("retake", source={"hf_path": "x"}), PINS))
    assert any("audio" in p for p in L.kind_problems(LAUNCH, _job("a2v", audio={}), PINS))


def test_preflight_lets_only_the_keyframes_kind_carry_an_end_picture(monkeypatch):
    from explainer_engine.core import spend_caps
    monkeypatch.setattr(spend_caps, "modal_ltx", lambda episode=False: {"per_run_usd": 2.0})
    L.preflight(LAUNCH, _job("keyframes"))
    with pytest.raises(SystemExit, match="only the keyframes kind"):
        L.preflight(LAUNCH, dict(_job("clip"), end_picture="e.png"))
    with pytest.raises(SystemExit, match="takes no end picture|only the keyframes kind"):
        L.preflight(LAUNCH, dict(_job("a2v"), end_picture="e.png"))
    with pytest.raises(SystemExit, match="kind 'extend'"):
        L.preflight(LAUNCH, _job("extend"))


def test_the_keyframes_command_binds_start_replace_and_end_guide_with_every_setting():
    cmd = L.kind_cmd(LAUNCH, _job(), "/t/s.png", "/o/c.mp4", end_png="/t/e.png")
    s = " ".join(cmd)
    assert cmd[1:3] == ["-m", "ltx_pipelines.ti2vid_two_stages"]
    assert "--image /t/s.png 0 1.0 replace" in s and "--image /t/e.png 200 1.0 guide" in s and "--refine-audio" in s
    for f in (LAUNCH["kind_uses"]["dev_transformer"], LAUNCH["kind_uses"]["distilled_lora"],
              LAUNCH["uses"]["spatial_upsampler"]):
        assert f in s
    for flag, v in (("--num-inference-steps", "40"), ("--video-cfg-guidance-scale", "3.0"), ("--seed", "7112"),
                    ("--distilled-lora-strength-stage-2", "0.5"), ("--num-frames", "201")):
        assert f"{flag} {v}" in s
    one = " ".join(L.kind_cmd(LAUNCH, _job("upscale_x2"), "/t/s.png", "/o/c.mp4"))
    assert one.count("--image") == 1 and "--refine-audio" not in one


def test_retake_and_a2v_commands_use_their_own_modules_and_inputs():
    r = L.kind_cmd(LAUNCH, _job("retake"), "/t/s.png", "/o/c.mp4", source="/t/src.mp4")
    assert r[2] == "ltx_pipelines.retake" and "--start-time 2.0" in " ".join(r) and "--video-path /t/src.mp4" in " ".join(r)
    assert LAUNCH["uses"]["transformer"] in " ".join(r) and "dev-transformer" not in " ".join(r)   # distilled: no new weights
    a = L.kind_cmd(LAUNCH, _job("a2v"), "/t/s.png", "/o/c.mp4", audio="/t/line.wav")
    assert a[2] == "ltx_pipelines.a2vid_two_stage" and "--audio-path /t/line.wav" in " ".join(a)


def test_the_run_record_holds_every_setting_and_the_upscalers_sha256():
    job = _job()
    cmd = L.kind_cmd(LAUNCH, job, "/t/s.png", "/o/c.mp4", end_png="/t/e.png")
    rec = L.kind_record(LAUNCH, job, cmd)
    up = LAUNCH["uses"]["spatial_upsampler"]
    assert rec["spatial_upsampler"] == {"file": up, "sha256": LAUNCH["model_files"][up]}
    assert rec["seed"] == 7112 and rec["settings"]["num_inference_steps"] == 40 and rec["frames"] == 201
    assert [(c["role"], c["frame"], c["strength"], c["binding"]) for c in rec["conditioning"]] == [
        ("start", 0, 1.0, "replace"), ("end", 200, 1.0, "guide")]
    assert rec["dev_transformer"]["sha256"] == PINS["sha256_files"][LAUNCH["kind_uses"]["dev_transformer"]]
    assert rec["ltx_commit"] == LAUNCH["ltx_code"]["commit"] and len(rec["argv_sha256"]) == 64
    assert json.loads(json.dumps(rec)) == rec
    assert L.kind_record(LAUNCH, _job("retake"), L.kind_cmd(LAUNCH, _job("retake"), "p", "m", source="s"))["start_time"] == 2.0


def test_a_retake_source_with_another_sha256_is_never_run(tmp_path):
    data = b"clip bytes"
    spec = {"hf_path": "x/clip.mp4", "sha256": hashlib.sha256(data).hexdigest()}
    got = L.stage_input(spec, tmp_path / "src.mp4", download=lambda repo, p, dest: dest.write_bytes(data))
    assert got.read_bytes() == data
    with pytest.raises(RuntimeError, match="not the pinned one"):
        L.stage_input(dict(spec, sha256="00" * 32), tmp_path / "other.mp4", download=lambda r, p, d: d.write_bytes(data))


# ---- a kind job through the same body as a clip (fake CLI) --------------------------------------------------------------
class FakeApi:
    def __init__(self):
        self.store = {}

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        for o in operations:
            self.store[o.path_in_repo] = Path(o.path_or_fileobj).read_bytes()

    def get_paths_info(self, repo, paths, repo_type, expand):
        out = []
        for p in paths:
            if p in self.store:
                d = self.store[p]
                lfs = SimpleNamespace(sha256=hashlib.sha256(d).hexdigest()) if p.endswith(".mp4") else None
                out.append(SimpleNamespace(path=p, lfs=lfs, blob_id=None if lfs else hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()))
        return out


def _png(color) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1280, 704), color).save(b, "PNG")
    return b.getvalue()


def test_a_keyframes_job_runs_the_official_cli_records_its_settings_and_is_saved_per_clip(tmp_path, monkeypatch):
    hub = types.ModuleType("huggingface_hub")
    hub.CommitOperationAdd = lambda path_in_repo, path_or_fileobj: SimpleNamespace(path_in_repo=path_in_repo,
                                                                                   path_or_fileobj=path_or_fileobj)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    launch = copy.deepcopy(LAUNCH)
    root = tmp_path / "w" / "model" / launch["model_repo"]
    for f in {**launch["model_files"], **launch["kind_model_files"]}:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"w")
    monkeypatch.setattr(L, "weights_root", lambda la, vol_root="/w": root)
    calls, clock = [], [0.0]

    def sh(cmd, **kw):
        calls.append(cmd)
        clock[0] += 120.0
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"mp4:keyframes")
        return SimpleNamespace(returncode=0)
    start, end = _png((10, 20, 30)), _png((30, 20, 10))
    job = dict(_job(), run_id="rid", launch_sha=L.launch_sha(launch), nonce="n1", start_bytes=start,
               start_sha256=hashlib.sha256(start).hexdigest(), end_bytes=end,
               extra={"end_sha256": hashlib.sha256(end).hexdigest()})
    res = L.body(job, launch, 582, vol_root=tmp_path / "w", api=FakeApi(), sh=sh, now=lambda: clock[0],
                 out_root=tmp_path / "out")
    assert res["state"] == "DONE" and "runner" not in res          # no in-process session for a kind
    cmd = calls[0]
    assert cmd[2] == "ltx_pipelines.ti2vid_two_stages" and cmd.count("--image") == 2
    assert res["record"]["conditioning"][1]["binding"] == "guide" and res["record"]["settings"]["num_inference_steps"] == 40
    assert set(res["verified"].values()) == {"ok"}
    assert (tmp_path / "w" / L.VOL_OUT / "rid" / "S07_SH008" / "S07_SH008_seed7112.mp4").is_file()
    again = L.body(job, launch, 582, vol_root=tmp_path / "w", api=FakeApi(), sh=sh, now=lambda: clock[0],
                   out_root=tmp_path / "out")
    assert again["state"] == "REFUSED_SECOND_ATTEMPT" and len(calls) == 1


def test_read_job_refuses_an_end_picture_that_is_not_the_pinned_one(tmp_path):
    pic, end = tmp_path / "s.png", tmp_path / "e.png"
    pic.write_bytes(_png((1, 2, 3)))
    end.write_bytes(_png((3, 2, 1)))
    plan = "p" * 64
    spec = dict(_job(), start_picture=str(pic), end_picture=str(end), plan_sha256=plan, run_id=L.run_id(plan, LAUNCH),
                launch_sha=L.launch_sha(LAUNCH),
                extra={"start_sha256": hashlib.sha256(pic.read_bytes()).hexdigest(), "end_sha256": "00" * 32})
    p = tmp_path / "job.json"
    p.write_text(json.dumps(spec))
    with pytest.raises(SystemExit, match="end picture"):
        L.read_job(str(p))
    spec["extra"]["end_sha256"] = hashlib.sha256(end.read_bytes()).hexdigest()
    p.write_text(json.dumps(spec))
    assert L.read_job(str(p))["end_bytes"] == end.read_bytes()


def test_the_distilled_engine_binds_the_end_keyframe_on_the_launchs_own_pipeline_with_no_new_weights():
    job = _job(engine="distilled", settings={"image_strength": 1.0})
    assert L.kind_problems(LAUNCH, job, PINS) == []
    no_files = {k: v for k, v in LAUNCH.items() if k not in ("kind_uses", "kind_model_files")}
    assert L.kind_problems(no_files, job, PINS) == []                      # needs neither the dev transformer nor the LoRA
    cmd = L.kind_cmd(LAUNCH, job, "/t/s.png", "/o/c.mp4", end_png="/t/e.png")
    s = " ".join(cmd)
    assert cmd[2] == LAUNCH["module"] == "ltx_pipelines.distilled" and "dev-transformer" not in s and "--distilled-lora" not in s
    assert "--image /t/s.png 0 1.0 replace" in s and "--image /t/e.png 200 1.0 guide" in s
    rec = L.kind_record(LAUNCH, job, cmd)
    assert rec["engine"] == "distilled" and rec["pipeline"] == "DistilledPipeline" and "dev_transformer" not in rec
    assert rec["spatial_upsampler"]["sha256"] == LAUNCH["model_files"][LAUNCH["uses"]["spatial_upsampler"]]
    assert L.kind_record(LAUNCH, _job(), L.kind_cmd(LAUNCH, _job(), "s", "m", end_png="e"))["engine"] == "guided"
    assert any("engine" in p for p in L.kind_problems(LAUNCH, _job(engine="turbo"), PINS))
