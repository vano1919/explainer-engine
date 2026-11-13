"""The in-process LTX runner (``runner: inproc``; the creator 2026-11-13 06:40 UTC asked why a 22 s scene cost ~$0.60, the
coordinator: free code, do it): one pipeline per container, every prompt encoded in one Gemma load, the transformer built
once and held for all clips, the CLI's own ``main`` body per clip. The fake-library tests always run; the last test runs the
pinned LTX-2 code itself (``ltx_pipelines`` installed, as in the CPU rehearsal venv) and checks that the CLI's ``main`` and
``LtxSession.clip`` hand the pipeline the same arguments for the same command line."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

LAUNCH = L.load_launch()


def test_the_launch_runs_in_process_and_names_its_runner():
    assert L.runner_of(LAUNCH) == "inproc" and L.launch_problems(LAUNCH) == []
    assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPWXt3bQhg6DyxmXs3TumdzYg" in LAUNCH["runner_why"]
    assert any("runner" in p for p in L.launch_problems(dict(LAUNCH, runner="daemon")))
    assert L.runner_of({k: v for k, v in LAUNCH.items() if k != "runner"}) == "cli"


def test_the_in_process_arguments_are_the_clis_own():
    job = {"shot_id": "c1", "seconds": 10, "fps": 24, "width": 1280, "height": 704, "seed": 5, "motion_prompt": "charge"}
    cmd = L.ltx_cmd(LAUNCH, job, "/tmp/p.png", "/o/.c1.mp4")
    assert cmd[1:3] == ["-m", "ltx_pipelines.distilled"] and L.ltx_argv(LAUNCH, job, "/tmp/p.png", "/o/.c1.mp4") == cmd[3:]


# ---------------------------------------------------------------- a fake pinned library: what the session asks of it

class FakeStage:
    def __init__(self, log):
        self.log, self.held, self.model = log, False, None
        self.video_scale_factors = "vsf"

    @contextmanager
    def resident(self):
        self.log.append("resident_in")
        self.held = True
        try:
            yield
        finally:
            self.held, self.model = False, None
            self.log.append("resident_out")

    def _transformer_ctx(self, **kw):
        if not self.held:
            self.log.append("build")
            return nullcontext("t")
        if self.model is None:
            self.log.append("build")
            self.model = "t"
        return nullcontext(self.model)

    def __call__(self, *a, **kw):
        with self._transformer_ctx():
            self.log.append("denoise")


class FakePipe:
    made = 0

    def __init__(self, log, **kw):
        FakePipe.made += 1
        self.kw, self.log, self.stage = kw, log, FakeStage(log)
        self.prompt_encoder = self._encode

    def _encode(self, prompts, **kw):
        self.log.append(("gemma", tuple(prompts)))
        return [f"emb:{p}" for p in prompts]

    def stream_chunks(self, **kw):
        enc = self.prompt_encoder([kw["prompt"]])
        self.log.append(("prepare", kw["prompt"], enc[0]))
        self.stage()                                   # stage 1
        self.stage()                                   # stage 2
        return iter(["chunk"]), 241, "tiling"


def fake_ltx(log, written):
    import argparse

    def parser_factory(params=None, supports_auto_duration=True):
        p = argparse.ArgumentParser()
        for f in ("--transformer-path", "--text-encoder-path", "--video-vae-path", "--audio-vae-path",
                  "--spatial-upsampler-path", "--prompt", "--output-path"):
            p.add_argument(f)
        p.add_argument("--image", nargs=3, action="append", dest="images")
        for f in ("--width", "--height", "--num-frames", "--seed"):
            p.add_argument(f, type=int)
        p.add_argument("--frame-rate", type=float)
        return p

    def finish(args):
        args.model_paths = (args.transformer_path, args.text_encoder_path)
        for k in ("lora", "quantization", "compile", "prompt_enhancer_gemma_root", "marker_root_path", "hdr"):
            setattr(args, k, None)
        args.offload_mode, args.diffvae_optimization = "none", "chunked_eager"
        args.enhance_prompt = args.enhance_static_cache = args.decode_with_keyframes = False
        args.num_generated_keyframes = 0
        return args

    class Parser:
        def __init__(self, p):
            self.p = p

        def parse_args(self, argv):
            log.append(("argv0", sys.argv[0]))
            return finish(self.p.parse_args(argv))

    D = SimpleNamespace(
        resolve_cli_params=lambda distilled: "params", default_2_stage_distilled_arg_parser=parser_factory,
        add_generated_keyframes_arg=lambda p: p, add_keyframe_decode_arg=lambda p: p,
        add_chunk_layout_args=lambda p: Parser(p), DistilledPipeline=lambda **kw: FakePipe(log, **kw),
        resolve_hdr_color_space=lambda images, hdr: None, markers_from_args=lambda a, device, color_space: (None, None),
        get_device=lambda: "cpu", vae_dtype_for_hdr=lambda hdr, d: d, chunk_config_from_args=lambda a: None,
        AUTO_TILING="auto", get_video_chunks_number=lambda n, t: 1,
        pipeline_output_from_chunks=lambda chunks, num_frames, tiling_config: SimpleNamespace(
            video=list(chunks), audio="a", num_frames=num_frames, tiling_config=tiling_config),
        encode_video=lambda **kw: (written.append(kw["output_path"]), Path(kw["output_path"]).write_bytes(b"mp4")))
    @contextmanager
    def inference_mode():
        log.append("inference_in")
        try:
            yield
        finally:
            log.append("inference_out")
    torch = SimpleNamespace(inference_mode=inference_mode, bfloat16="bf16")
    return SimpleNamespace(D=D, torch=torch, cleanup=lambda: log.append("cleanup"))


def argv(prompt, out, seed=1):
    return ["--transformer-path", "/w/t", "--text-encoder-path", "/w/g", "--video-vae-path", "/w/v", "--audio-vae-path",
            "/w/a", "--spatial-upsampler-path", "/w/u", "--image", "/tmp/p.png", "0", "1.0", "--prompt", prompt,
            "--width", "1280", "--height", "704", "--num-frames", "241", "--frame-rate", "24", "--seed", str(seed),
            "--output-path", str(out)]


def test_three_clips_load_the_pipeline_gemma_and_the_transformer_once(tmp_path):
    log, written = [], []
    FakePipe.made = 0
    s = L.LtxSession(["charge", "clash", "charge", "fall"], ltx=fake_ltx(log, written))
    for i, p in enumerate(["charge", "clash", "fall"]):
        s.clip(argv(p, tmp_path / f"c{i}.mp4", seed=i))
    s.close()
    assert FakePipe.made == 1 and [e for e in log if e == "build"] == ["build"]
    assert [e for e in log if isinstance(e, tuple) and e[0] == "gemma"] == [("gemma", ("charge", "clash", "fall"))]
    assert [e[1:] for e in log if isinstance(e, tuple) and e[0] == "prepare"] == [
        ("charge", "emb:charge"), ("clash", "emb:clash"), ("fall", "emb:fall")]
    assert log.count("denoise") == 6 and log.index("build") < log.index("denoise") and log[-1] == "resident_out"
    assert log.index("build") < next(i for i, e in enumerate(log) if isinstance(e, tuple) and e[0] == "prepare")
    assert [Path(w).name for w in written] == ["c0.mp4", "c1.mp4", "c2.mp4"]
    assert set(s.setup) == {"pipeline_s", "prompts_s", "prompts", "transformer_s"} and s.setup["prompts"] == 3
    assert ("argv0", "ltx_pipelines.distilled") in log and sys.argv[0] != "ltx_pipelines.distilled"


def test_the_session_opens_gemma_and_the_transformer_inside_inference_mode(tmp_path):
    """L3 of 2026-11-13 (CUDA out of memory on the H100, run 8462e18a7e41): the library's Gemma ``encode`` has no no_grad of
    its own and relies on the CLI's ``@torch.inference_mode()`` main; the session's ``_open`` ran outside it, so the cached
    prompt embeddings held an autograd graph that kept Gemma's weights on the GPU. Every pipeline, Gemma and transformer step
    of the session now happens inside inference mode, as in the CLI."""
    log, written = [], []
    s = L.LtxSession(["a", "b"], ltx=fake_ltx(log, written))
    s.clip(argv("a", tmp_path / "a.mp4"))
    s.clip(argv("b", tmp_path / "b.mp4"))
    depth, where = 0, {}
    for e in log:
        depth += 1 if e == "inference_in" else -1 if e == "inference_out" else 0
        key = e[0] if isinstance(e, tuple) else e
        if key in ("gemma", "build", "denoise", "resident_in", "prepare"):
            where.setdefault(key, set()).add(depth > 0)
    assert where["gemma"] == where["build"] == where["resident_in"] == where["denoise"] == {True}


def test_more_than_four_prompts_are_encoded_in_groups_of_four(tmp_path):
    log = []
    s = L.LtxSession([f"p{i}" for i in range(6)], ltx=fake_ltx(log, []))
    s.clip(argv("p0", tmp_path / "c.mp4"))
    assert [len(e[1]) for e in log if isinstance(e, tuple) and e[0] == "gemma"] == [4, 2]


def test_a_prompt_not_encoded_first_or_other_model_arguments_are_refused(tmp_path):
    s = L.LtxSession(["charge"], ltx=fake_ltx([], []))
    s.clip(argv("charge", tmp_path / "a.mp4"))
    with pytest.raises(RuntimeError, match="not encoded"):
        s.clip(argv("surprise", tmp_path / "b.mp4"))
    other = argv("charge", tmp_path / "c.mp4")
    other[other.index("--transformer-path") + 1] = "/w/other"
    with pytest.raises(RuntimeError, match="model arguments differ"):
        s.clip(other)
    with pytest.raises(RuntimeError, match="enhancement"):
        s.pipe.prompt_encoder(["charge"], enhance_first_prompt=True)


def test_the_deadline_stops_a_clip_before_its_denoising_pass(tmp_path):
    d = L.Deadline(1000, margin_s=0)
    s = L.LtxSession(["charge", "clash"], deadline=d, ltx=fake_ltx([], []))
    s.clip(argv("charge", tmp_path / "a.mp4"))
    d.end = d.now() - 1
    with pytest.raises(L.DeadlineHit):
        s.clip(argv("clash", tmp_path / "b.mp4"))
    log_path = tmp_path / "c.log"
    row = L.in_process_clip(s, argv("clash", tmp_path / "b.mp4"), log_path)
    assert row["rc"] is None and "deadline" in row["why"] and log_path.is_file()


def test_a_clip_that_raises_is_a_failed_row_with_its_traceback_in_the_log(tmp_path):
    class Boom:
        setup = {}

        def clip(self, a):
            raise MemoryError("CUDA out of memory")
    row = L.in_process_clip(Boom(), [], tmp_path / "x.log")
    assert row["rc"] == 1 and "MemoryError" in row["why"] and "Traceback" in (tmp_path / "x.log").read_text()


# ---------------------------------------------------------------- the worker's body with the in-process runner

def _png(rgb):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (64, 36), rgb).save(b, format="PNG")
    return b.getvalue()


class FakeApi:
    def __init__(self):
        self.files = {}

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        for op in operations:
            self.files[op.path_in_repo] = Path(op.path_or_fileobj).read_bytes()

    def get_paths_info(self, repo_id, paths, repo_type, expand=False):
        out = []
        for p in paths:
            if p in self.files:
                d = self.files[p]
                out.append(SimpleNamespace(path=p, lfs=SimpleNamespace(sha256=hashlib.sha256(d).hexdigest()),
                                           blob_id=hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()))
        return out


class RecSession:
    made = []

    def __init__(self, prompts, deadline=None, now=None, fail_at=None):
        self.prompts, self.calls, self.closed, self.fail_at = prompts, [], False, fail_at
        self.setup = {"pipeline_s": 1.0, "prompts_s": 9.0, "prompts": len(set(prompts)), "transformer_s": 20.0}
        RecSession.made.append(self)

    def clip(self, a):
        self.calls.append(a)
        fail = self.fail_at if isinstance(self.fail_at, (set, frozenset)) else {self.fail_at}
        if len(self.calls) in fail:
            raise RuntimeError("CUDA error")
        pic = Path(a[a.index("--image") + 1]).read_bytes()
        Path(a[a.index("--output-path") + 1]).write_bytes(b"mp4:" + hashlib.sha256(pic).hexdigest().encode())

    def close(self):
        self.closed = True


@pytest.fixture
def box(tmp_path, monkeypatch):
    import types
    hub = types.ModuleType("huggingface_hub")
    hub.CommitOperationAdd = lambda path_in_repo, path_or_fileobj: SimpleNamespace(path_in_repo=path_in_repo,
                                                                                   path_or_fileobj=path_or_fileobj)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    launch = copy.deepcopy(LAUNCH)
    root = tmp_path / "w" / "model" / launch["model_repo"]
    for f in launch["model_files"]:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"w")
    monkeypatch.setattr(L, "weights_root", lambda la, vol_root="/w": root)

    def sh(cmd, **kw):
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(_png((len(Path(cmd[cmd.index("-i") + 1]).read_bytes()) % 255, 0, 0)))
            return SimpleNamespace(returncode=0)
        raise AssertionError("the in-process runner starts no LTX process")
    pic = _png((10, 20, 30))
    job = {"shot_id": "c1", "seconds": 9.5, "seed": 1, "fps": 24, "width": 1280, "height": 704, "motion_prompt": "talk",
           "run_id": "rid", "launch_sha": L.launch_sha(launch), "nonce": "n1", "start_bytes": pic,
           "start_sha256": hashlib.sha256(pic).hexdigest(),
           "chain": [{"shot_id": "c2", "seconds": 9.5, "seed": 2, "motion_prompt": "more"},
                     {"shot_id": "c3", "seconds": 9.5, "seed": 3, "motion_prompt": "kiss"}]}
    RecSession.made = []
    return SimpleNamespace(launch=launch, job=job, sh=sh, tmp=tmp_path)


def _body(b, factory, api=None):
    return L.body(b.job, b.launch, 582, vol_root=b.tmp / "w", api=api or FakeApi(), sh=b.sh, out_root=b.tmp / "out",
                  session_factory=factory)


def test_the_body_makes_the_whole_chain_on_one_session_and_records_its_setup(box):
    api = FakeApi()
    res = _body(box, RecSession, api)
    s, = RecSession.made
    assert res["state"] == "DONE" and res["runner"] == "inproc" and s.closed
    assert s.prompts == ["talk", "more", "kiss"] and len(s.calls) == 3
    assert [r["state"] for r in res["chain"]] == ["DONE"] * 3 and res["chain"][0]["setup"]["transformer_s"] == 20.0
    assert "setup" not in res["chain"][1] and res["setup"]["prompts"] == 3
    assert all(v == "ok" for v in res["verified"].values()) and any(k.endswith("c3_seed3.mp4") for k in api.files)


def test_a_clip_that_fails_twice_ends_the_chain_and_still_closes_the_session(box):
    """P5 / RT-07 (the creator 2026-11-13): a failed clip gets one retry with seed + SEED_STEP on the same session; when the
    retry fails too, the chain ends there (was: the first failure ended it, before the worker-side retry existed)."""
    res = _body(box, lambda prompts, deadline=None, now=None: RecSession(prompts, fail_at={2, 3}))
    s, = RecSession.made
    assert [r["state"] for r in res["chain"]] == ["DONE", "FAILED"] and "CUDA error" in res["chain"][1]["why"]
    assert [a["seed"] for a in res["chain"][1]["attempts"]] == [2, 2 + L.SEED_STEP] and len(s.calls) == 3
    assert res["state"] == "PARTIAL" and s.closed


def test_a_clip_that_fails_once_is_made_again_with_a_new_seed_and_the_chain_goes_on(box):
    """P5 / RT-07: one retry inside the container, its seed in the clip's name, both attempts in the row; the next clip
    chains from the retried clip."""
    api = FakeApi()
    res = _body(box, lambda prompts, deadline=None, now=None: RecSession(prompts, fail_at=2), api)
    s, = RecSession.made
    c2 = res["chain"][1]
    assert [r["state"] for r in res["chain"]] == ["DONE"] * 3 and res["state"] == "DONE" and len(s.calls) == 4
    assert c2["seed"] == 2 + L.SEED_STEP and c2["clip"] == f"c2_seed{2 + L.SEED_STEP}.mp4"
    assert [(a["seed"], a["state"]) for a in c2["attempts"]] == [(2, "FAILED"), (2 + L.SEED_STEP, "DONE")]
    assert "CUDA error" in c2["attempts"][0]["why"] and res["chain"][2]["chain_from_frame"]["clip"] == c2["clip"]
    assert any(k.endswith(c2["clip"]) for k in api.files) and "attempts" not in res["chain"][0]


def test_a_session_that_cannot_open_is_a_failed_job_with_nothing_left_open(box):
    class NoGpu(RecSession):
        def __init__(self, *a, **kw):
            raise RuntimeError("no CUDA device")
    res = _body(box, NoGpu)
    assert res["state"] == "FAILED" and "no CUDA device" in res["error"]


# ---------------------------------------------------------------- the pinned LTX-2 code itself (CPU rehearsal venv)

def test_with_the_pinned_ltx_code_main_and_the_session_hand_the_pipeline_the_same_arguments(tmp_path, monkeypatch):
    D = pytest.importorskip("ltx_pipelines.distilled")
    from safetensors.torch import save_file
    import torch
    w = tmp_path / "w"
    w.mkdir()
    save_file({"x": torch.zeros(1)}, str(w / "t.safetensors"), metadata={"model_version": "2.5.0"})
    for f in ("g.safetensors", "v.safetensors", "a.safetensors", "u.safetensors"):
        save_file({"x": torch.zeros(1)}, str(w / f))
    pic = tmp_path / "p.png"
    pic.write_bytes(_png((1, 2, 3)))
    seen = {"main": [], "session": []}
    who = ["main"]

    class Pipe:
        def __init__(self, **kw):
            seen[who[0]].append(("init", sorted((k, repr(v)) for k, v in kw.items())))
            self.stage = FakeStage([])
            self.prompt_encoder = lambda prompts, **k: [f"emb:{p}" for p in prompts]

        def stream_chunks(self, **kw):
            seen[who[0]].append(("stream", sorted((k, repr(v)) for k, v in kw.items())))
            return iter(["chunk"]), kw["num_frames"], "tiling"
    monkeypatch.setattr(D, "DistilledPipeline", Pipe)
    monkeypatch.setattr(D, "pipeline_output_from_chunks", lambda chunks, num_frames, tiling_config: SimpleNamespace(
        video="v", audio="a", num_frames=num_frames, tiling_config=tiling_config))
    monkeypatch.setattr(D, "get_video_chunks_number", lambda n, t: 1)
    monkeypatch.setattr(D, "encode_video", lambda **kw: seen[who[0]].append(
        ("encode", sorted((k, repr(v)) for k, v in kw.items()))))
    launch = dict(LAUNCH, uses={k: v for k, v in LAUNCH["uses"].items()})
    monkeypatch.setattr(L, "weights_root", lambda la, vol_root="/w": w)
    launch["uses"] = {"transformer": "t.safetensors", "text_encoder": "g.safetensors", "video_vae": "v.safetensors",
                      "audio_vae": "a.safetensors", "spatial_upsampler": "u.safetensors"}
    job = {"shot_id": "c1", "seconds": 10, "fps": 24, "width": 1280, "height": 704, "seed": 5404,
           "motion_prompt": "The two armies charge across the plain."}
    a = L.ltx_argv(launch, job, pic, tmp_path / ".c1.mp4")
    monkeypatch.setattr(sys, "argv", ["ltx_pipelines.distilled", *a])
    D.main()
    who[0] = "session"
    monkeypatch.setattr(sys, "argv", ["pytest"])
    s = L.LtxSession([job["motion_prompt"]])
    s.clip(a)
    s.close()
    assert seen["main"] == seen["session"] and [e[0] for e in seen["main"]] == ["init", "stream", "encode"]
    stream = dict(seen["main"][1][1])
    assert stream["seed"] == "5404" and stream["num_frames"] == "241" and stream["width"] == "1280"
    assert json.dumps(seen["main"])                           # plain, comparable values


def test_with_the_pinned_ltx_code_a_resident_stage_builds_the_transformer_once_and_releases_it_at_the_end():
    """The two internals the session leans on: ``DiffusionStage.resident`` and ``_transformer_ctx`` (LTX-2 e98f6d9)."""
    pytest.importorskip("ltx_pipelines.distilled")
    import torch
    from ltx_pipelines.utils.blocks.diffusion_stage import DiffusionStage
    built = []

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.w = torch.nn.Linear(2, 2)

    class Builder:
        model_sd_ops = module_ops = None
        loras = ()
        builds_per_shape = keeps_gpu_resident_weights = False
        checkpoint = "t.safetensors"

        def with_module_ops(self, ops):
            return self

        with_sd_ops = with_module_ops

        def with_loras(self, loras):
            return self

        def build(self, device=None, **kw):
            built.append(Net())
            return built[-1]
    stage = DiffusionStage(Builder(), torch.float32, torch.device("cpu"))
    with stage.resident():
        with stage._transformer_ctx() as a:
            pass
        with stage._transformer_ctx() as b:
            pass
        assert a is b and len(built) == 1 and built[0].w.weight.device.type == "cpu"
    assert built[0].w.weight.device.type == "meta"                  # released at the block's end
    with stage._transformer_ctx():
        pass
    assert len(built) == 2 and built[1].w.weight.device.type == "meta"   # outside a block: a build per call, as the CLI
