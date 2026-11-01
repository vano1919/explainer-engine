"""WP-1a2: every LTX module of p12c_ltx.py is resolved (no PLACEHOLDER), names a file of the e98f6d9 listing, and the L1/L3
command uses the distilled pipeline with only flags its parser declares. No network, no GPU, no pod."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "explainer_engine" / "training" / "pods" / "p12"
LISTING = ROOT / "tests" / "fixtures" / "ltx2_listing_e98f6d9.txt"   # LTX-2 files at e98f6d9, kept in the repo (CI has no jobs/)
SRC = "packages/ltx-pipelines/src/"


def _load():
    spec = importlib.util.spec_from_file_location("p12c_ltx_under_test", DIR / "p12c_ltx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _cfg():
    return {"ltx": {
        "local": "ltx",
        "files": ["transformer/distilled-transformer.safetensors", "text_encoders/gemma.safetensors",
                  "vae/video-vae.safetensors", "vae/audio-vae.safetensors", "latent_upscale_models/x2.safetensors"],
        "av_files": [],
        "layout_lora": {"file": "loras/layout.safetensors"},
        "render": {"width": 1408, "height": 800, "frames": 121, "fps": 24, "seed": 7},
    }}


def test_flags_resolved():
    m = _load()
    assert set(m.CMDS) <= set(m.MODULES)
    listing = set(LISTING.read_text(encoding="utf-8").split())
    for kind, mod in m.MODULES.items():
        assert mod and "PLACEHOLDER" not in mod.upper(), kind
        assert SRC + mod.replace(".", "/") + ".py" in listing, (kind, mod)
    assert m.MODULES["ltx_i2v"] == "ltx_pipelines.distilled"
    for key, flag in m.FLAGS.items():
        assert flag is None or flag.startswith("--"), key

    cmd = [str(c) for c in m.cmd_ltx_i2v(_cfg(), "s01", {"image": "/x/s01.png", "prompt": "p", "out": "/x/s01_i2v.mp4"})]
    assert cmd[1:3] == ["-m", "ltx_pipelines.distilled"]
    i = cmd.index("--image")
    assert cmd[i + 1:i + 4] == ["/x/s01.png", "0", "1.0"]
    for key in ("transformer", "prompt", "output", "upsampler", "num_frames", "text_encoder", "video_vae", "audio_vae"):
        assert m.FLAGS[key] in cmd, key
    # The distilled parser (args.py:1590) has no --distilled-lora, --video-conditioning or --audio-path.
    for key in ("distilled_lora", "video_cond", "audio", "audio_max", "stage2_ic"):
        assert m.FLAGS[key] not in cmd, key
    assert "--quantization=fp8-cast" in cmd


# audit 2026-11-01 #17: the clip's audio is re-encoded, so it is compared by samples, not by the sha256 of a container
import shutil
import subprocess
import wave

import numpy as np
import pytest

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _wav(path, freq, seconds=2.0, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    x = (0.4 * np.sin(2 * np.pi * freq * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t)) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(x.tobytes())


def _clip(path, wav):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x64:d=2:r=24", "-i", str(wav),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


@needs_ffmpeg
def test_audio_corr_finds_the_take_in_a_reencoded_clip_where_the_container_sha_cannot(tmp_path):
    import hashlib
    from explainer_engine.training.pods.p12 import p12c_ltx as L
    take, other, clip = tmp_path / "take.wav", tmp_path / "other.wav", tmp_path / "clip.mp4"
    _wav(take, 220), _wav(other, 517)
    _clip(clip, take)
    got = L.audio_corr(clip, take)
    assert got and got["corr"] > 0.95 and abs(got["lag_s"]) < 0.1 and abs(got["clip_s"] - got["take_s"]) < 0.2
    assert L.audio_matches(clip, hashlib.sha256(take.read_bytes()).hexdigest()) is False      # why the old criterion could never pass
    assert L.audio_corr(clip, other)["corr"] < 0.5                                              # a different voice does not pass
    assert L.audio_corr(tmp_path / "missing.mp4", take) is None


# the tests the combined-pod plan (section 3.F) asks for, restored in WP-1d after the audit of 2026-11-01 (#22)
import ast
import json
import subprocess as _sp
import types


def _real_cfg():
    return json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))


def test_p12c_commands_come_only_from_the_flags_table():
    tree = ast.parse((DIR / "p12c_ltx.py").read_text(encoding="utf-8"))
    flags_node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "FLAGS")
    inside = {id(x) for x in ast.walk(flags_node)}
    loose = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and n.value.startswith("--") and id(n) not in inside]
    assert loose == []                                            # a flag typed in the code would dodge the table and its audit


def test_p12c_skips_everything_when_qwen_was_stopped_by_the_creator(tmp_path, monkeypatch):
    m = _load()
    (tmp_path / "control").mkdir()
    (tmp_path / "control" / "stopped_after.txt").write_text("Q1\n", encoding="utf-8")
    monkeypatch.setenv("EE_OUT", str(tmp_path))

    def boom(*a, **k):
        raise AssertionError("no subprocess may start after the creator's stop")
    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m.main() == 0


def test_p12c_skips_l_stages_when_weights_are_missing(tmp_path, monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    p12b = m.load_p12b()
    log = p12b.Log(tmp_path / "out")
    assert m.run(_real_cfg(), tmp_path / "out", 10 ** 12, log, p12b) == 0
    assert "skipped L1 L2 L3 AV (weights missing)" in (tmp_path / "out" / "stages.txt").read_text(encoding="utf-8")


def _stage_run(tmp_path, monkeypatch, kind, shots, completed):
    """run_stage over one stage with a fake ffmpeg-free subprocess; returns (result, sidecar json of the first shot)."""
    m = _load()
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    p12b = m.load_p12b()
    cfg = _real_cfg()
    out = tmp_path / "out"
    log = p12b.Log(out)
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: completed)
    monkeypatch.setattr(m, "audio_matches", lambda *a: False)
    monkeypatch.setattr(m, "audio_corr", lambda *a: {"corr": 0.9, "lag_s": 0.0, "clip_s": 2.0, "take_s": 2.0})
    inputs = {s: {"image": tmp_path / f"{s}.png", "keyframe_sha256": "k", "prompt": "p", "clay": None, "clay_sha256": None,
                  "wav": tmp_path / f"{s}.wav", "take_sha256": "t", "voice_id": "v", "seconds": 2.0} for s in shots}
    st = {"kind": kind, "shots": shots, "essential": True, "order": 1}
    res = m.run_stage("X", st, cfg, out, log, inputs, {})
    side = json.loads(m.out_path(out, kind, shots[0]).with_suffix(".json").read_text(encoding="utf-8"))
    return m, res, side


def test_p12c_av_oom_is_recorded_and_the_script_exits_0(tmp_path, monkeypatch):
    done = _sp.CompletedProcess([], 1, stdout="", stderr="torch.OutOfMemoryError: CUDA out of memory")
    m, res, side = _stage_run(tmp_path, monkeypatch, "ltx_a2v", ["av1", "av2"], done)
    assert res == {"ok": 0, "failed": 1, "oom": True}             # the second clip is not tried after an OOM
    assert side["oom"] is True and side["rc"] == 1 and "CUDA out of memory" in side["stderr_tail"]
    # run(): an AV stage that ends in OOM makes the whole script exit 0 (a recorded fact, not a pod failure)
    p12b = m.load_p12b()
    cfg = _real_cfg()
    monkeypatch.setattr(m, "verify_weights", lambda c, names: [])
    monkeypatch.setattr(m, "prepare_inputs", lambda c, o, l: {s: {"prompt": "p", "wav": "w", "image": "i"} for s in ("av1", "av2")})
    monkeypatch.setattr(m, "run_stage", lambda *a: {"ok": 0, "failed": 1, "oom": True})
    monkeypatch.setattr(p12b, "stop_here", lambda *a: False)
    cfg["stages"] = {"AV": cfg["stages"]["AV"]}
    assert m.run(cfg, tmp_path / "out2", 10 ** 12, p12b.Log(tmp_path / "out2"), p12b) == 0


def test_p12c_sidecar_has_every_field(tmp_path, monkeypatch):
    ok = _sp.CompletedProcess([], 0, stdout="", stderr="")
    _, res, side = _stage_run(tmp_path, monkeypatch, "ltx_a2v", ["av1"], ok)
    assert res["ok"] == 1
    assert set(side) >= {"stage", "shot", "kind", "seed", "width", "height", "frames", "fps", "steps", "cmd", "seconds", "rc", "oom",
                         "stderr_tail", "inputs", "model_files", "audio_sha_match", "audio_corr"}
    assert set(side["inputs"]) == {"keyframe_sha256", "clay_sha256", "take_sha256", "voice_id"}
    assert side["audio_corr"]["corr"] == 0.9 and side["rc"] == 0 and side["stderr_tail"] == ""
    assert side["frames"] is None and side["steps"] is None and side["audio_max_s"] == 2.0     # AV: length from the take, not L1's numbers


def test_p12c_drop_order_and_essentials():
    c = _real_cfg()
    assert c["drop_order"] == ["Q3", "L3", "Q2"]
    st = c["stages"]
    assert [n for n in st if st[n]["essential"]] == ["Q1", "L1", "L2", "AV"]
    assert all(not st[n]["essential"] for n in c["drop_order"])


def test_run_stage_draws_no_clip_inside_the_end_reserve(tmp_path):
    """Audit #14: an essential LTX stage also stops at the end reserve; main exits 0 when it starts inside it."""
    import json
    import time
    m = _load()
    p12b = m.load_p12b()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    log = p12b.Log(tmp_path)
    deadline = time.time() + cfg["end_reserve_min"] * 60 - 5          # 5 s inside the reserve
    st = cfg["stages"]["L1"]
    res = m.run_stage("L1", st, cfg, tmp_path, log, {}, {}, deadline, p12b)
    assert res == {"ok": 0, "failed": 0, "oom": False}
    evs = [json.loads(x)["ev"] for x in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert evs == ["unit_skipped"]


# audit 2026-11-01 #19: keyframes are sha256-pinned and a stage is "done" only when every shot is ok
def test_every_keyframe_is_pinned_and_a_wrong_file_is_refused(tmp_path, monkeypatch):
    import hashlib
    import json
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    kf = cfg["ltx"]["keyframes"]
    assert set(kf["sha256"]) == set(kf["paths"]) and all(len(v) == 64 for v in kf["sha256"].values())
    good = tmp_path / "good.png"
    good.write_bytes(b"picture")
    kf["sha256"] = {s: hashlib.sha256(b"picture").hexdigest() for s in kf["paths"]}
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    monkeypatch.setattr(m, "fetch", lambda repo, path, local: good)
    monkeypatch.setattr(m, "fit_frame", lambda src, dst, w, h: dst.write_bytes(b"fit"))
    cfg["ltx"]["av"]["takes"] = {}
    cfg["ltx"]["clay"]["sha256"] = {}
    p12b = m.load_p12b()
    log = p12b.Log(tmp_path / "out")
    inputs = m.prepare_inputs(cfg, tmp_path / "out", log)
    assert "tent_s0" in inputs and inputs["tent_s0"]["image"].read_bytes() == b"fit"
    # a file that is not the pinned one: the shot gets no input and the mismatch is logged
    for p in (tmp_path / "models" / "p12c" / "in").glob("*.png"):
        p.unlink()
    good.write_bytes(b"another picture")
    inputs = m.prepare_inputs(cfg, tmp_path / "out", log)
    assert "tent_s0" not in inputs
    evs = [json.loads(x) for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert any(e["ev"] == "sha256_mismatch" for e in evs) and any(e["ev"] == "input_failed" and e["what"] == "keyframe" for e in evs)


def test_a_stage_is_done_only_when_every_shot_is_ok():
    src = (DIR / "p12c_ltx.py").read_text(encoding="utf-8")
    assert 'res["ok"] == len(st["shots"])' in src and 'f"done {name}" if res["ok"] else' not in src


def test_no_log_call_passes_name_as_a_keyword():
    """Log.ev(self, name, **kw) already has ``name``: ``log.ev(..., name=...)`` raises TypeError (found by the keyframe pin test)."""
    import ast
    for f in ("p12b.py", "p12c_ltx.py"):
        for node in ast.walk(ast.parse((DIR / f).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "ev":
                assert "name" not in {k.arg for k in node.keywords}, (f, node.lineno)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_the_whole_ltx_process_runs_end_to_end_with_stubbed_weights_and_commands(tmp_path, monkeypatch):
    """Every LTX stage of the real p12b.json runs through run(): inputs fetched and sha-checked, commands built, sidecars written,
    AV audio compared by samples, the stage lines and the end word. Only the HF fetch, the weights check and the GPU command are
    stubbed (the stub writes a 1 s clip, with the take as its audio for AV). This is the free stand-in for the code paths a pod
    would otherwise reach first (2026-11-01: three log.ev(name=...) TypeErrors were found only by reading)."""
    import hashlib
    import json
    import time
    from PIL import Image
    m = _load()
    p12b = m.load_p12b()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    cfg.pop("control", None)                                    # no creator stop file on HF in a test
    lt = cfg["ltx"]
    src = tmp_path / "src"
    src.mkdir()
    png = src / "kf.png"
    Image.new("RGB", (2560, 1408), (200, 180, 150)).save(png)
    clay = src / "clay.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=gray:s=320x192:d=1:r=24", "-pix_fmt", "yuv420p",
                    str(clay)], check=True)
    wav = src / "take.wav"
    rate = 24000
    t = np.arange(int(rate * 1.0)) / rate
    pcm = (0.3 * np.sin(2 * np.pi * 220 * t) * np.sin(2 * np.pi * 3 * t) * 32767).astype("<i2")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate), w.writeframes(pcm.tobytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    lt["keyframes"]["sha256"] = {s: sha(png) for s in lt["keyframes"]["paths"]}
    lt["clay"]["sha256"] = {s: sha(clay) for s in lt["clay"]["sha256"]}
    for take in lt["av"]["takes"].values():
        take.update(sha256=sha(wav), voice_id="test-voice", seconds=1.0)
    out = tmp_path / "out"
    out.mkdir()
    q1 = tmp_path / "q1.png"
    Image.new("RGB", (900, 1400), (120, 120, 160)).save(q1)
    (out / "qwen_done.txt").write_text(str(q1) + "\n", encoding="utf-8")

    def fetch(repo, path, local):
        return {"clay": clay, "audio": wav}.get(Path(local).name, png)
    ran = []

    def run_cmd(cmd, timeout, log, label):
        cmd = [str(c) for c in cmd]
        dst = cmd[cmd.index(m.FLAGS["output"]) + 1]
        ran.append((label, cmd))
        args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=white:s=320x192:d=1:r=24"]
        if m.FLAGS["audio"] in cmd:
            args += ["-i", cmd[cmd.index(m.FLAGS["audio"]) + 1], "-c:a", "aac", "-shortest"]
        subprocess.run(args + ["-pix_fmt", "yuv420p", dst], check=True)
        return 0, ""
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    monkeypatch.setattr(m, "verify_weights", lambda cfg, names: [])
    monkeypatch.setattr(m, "fetch", fetch)
    monkeypatch.setattr(m, "run_cmd", run_cmd)
    log = p12b.Log(out)
    assert m.run(cfg, out, time.time() + 3 * 3600, log, p12b) == 0

    stages = (out / "stages.txt").read_text(encoding="utf-8")
    for name in ("L1", "L3", "L2", "AV"):
        assert f"done {name}" in stages, stages
    assert len(ran) == sum(len(st["shots"]) for st in cfg["stages"].values() if st.get("kind", "").startswith("ltx_"))
    for kind, shot in [("ltx_i2v", "tent_s0"), ("ltx_ic", "tent_s3"), ("ltx_a2v", "av1"), ("ltx_a2v", "av2")]:
        side = json.loads(m.out_path(out, kind, shot).with_suffix(".json").read_text(encoding="utf-8"))
        assert side["rc"] == 0 and side["kind"] == kind
        assert side["inputs"]["keyframe_sha256"]
        if kind == "ltx_ic":
            assert side["inputs"]["clay_sha256"] == sha(clay) and (out / "ltx" / "clay" / f"{shot}.mp4").is_file()
        if kind == "ltx_a2v":
            assert side["frames"] is None and side["audio_max_s"] == 1.0 and side["inputs"]["voice_id"] == "test-voice"
            assert side["audio_corr"]["corr"] > 0.9                  # the clip carries the take's samples (re-encoded to AAC)
    evs = [json.loads(x)["ev"] for x in (out / "t.jsonl").read_text().splitlines()]
    assert "sha256_mismatch" not in evs and "input_failed" not in evs and "stage_skipped" not in evs
    assert (out / "progress.txt").read_text(encoding="utf-8").strip().endswith("done")
