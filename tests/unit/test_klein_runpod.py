"""W5 (plan RUNPOD_AB_PLAN.md section 5): the Klein picture pod. No pod, no money, no network, no GPU: a fake generator and a fake HF
API stand in. Same pattern as test_ltx_runpod: refusals before create, L2 first, one smoke picture, cap clock from EE_CREATED, each
picture uploaded and verified before the next; open pins are refused, never guessed."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.training.pods.klein import klein_jobs as K
from explainer_engine.training.pods.ltx import modal_ltx_jobs as M

SHA = "cd" * 32
REV = "3b767ff9b5261d71645e2ec49d87d298d955238d"


@pytest.fixture
def launch():
    """A launch with every open pin filled in a TEST copy (the real file keeps them null until proven)."""
    lf = copy.deepcopy(K.LAUNCH)
    m = lf["models"][lf["model"]]
    m["files"] = {"transformer/model.safetensors": SHA, "vae/model.safetensors": "ef" * 32}
    lf.update(pipeline_class="FakePipeline", diffusers_version="0.0.0", image="ghcr.io/x/y@sha256:" + "0" * 64, cap_usd=0.6)
    return lf


def _job(i, kind="sample", **kw):
    j = {"id": i, "kind": kind, "prompt": "a plain test picture", "seed": 7, "width": 512, "height": 512, "settings": {"num_inference_steps": 4}}
    if kind == "edit":
        j["refs"] = [{"hf_path": "vault/S07_SH008_start.png", "sha256": SHA}]
    return dict(j, **kw)


def _batch(n=2, **kw):
    return dict({"card": "NVIDIA RTX PRO 4500 Blackwell", "price": 0.72, "cap_usd": 0.6, "prefix": "klein_out/ab",
                 "smoke": _job("L3_smoke"), "jobs": [_job(f"P{i}", "edit") for i in range(n)]}, **kw)


def test_the_real_launch_keeps_every_open_pin_null_and_refuses():
    lf = K.LAUNCH
    m = lf["models"][lf["model"]]
    assert m["repo"] == "black-forest-labs/flux-3-image-klein" and m["revision"] == REV and m["gated"] is True
    assert lf["cap_usd"] == 0.6 and "cmsg_01Hnu5zB86sjUj5GtTgaUkPWSuqhe7svtHM5ptNMiw84V4" in lf["cap_why"]   # the owner's own word
    assert m["files"] is None and lf["pipeline_class"] is None and lf["diffusers_version"] is None and lf["image"] is None
    assert "prompt upsampler" in m["layout"] or "pup" in m["layout"]
    pins = K.open_pins(lf)
    assert any("file list" in p for p in pins) and any("pipeline class" in p for p in pins) and any("no pinned image" in p for p in pins)
    out = K.batch_problems(lf, _batch(), price=0.72, cap_usd=0.6)
    assert out and K.script_problems()                                         # the script template is unbuilt too


def test_a_fully_pinned_batch_passes_and_the_refusals_work(launch):
    assert K.open_pins(launch) == []
    assert K.batch_problems(launch, _batch(), price=0.72, cap_usd=0.6) == []
    p = lambda b, **kw: K.batch_problems(launch, b, price=0.72, **dict({"cap_usd": 0.6}, **kw))      # noqa: E731
    assert any("no cap for this batch" in x for x in p(_batch(), cap_usd=None))
    assert any("recorded launch cap_usd" in x for x in p(_batch(), cap_usd=0.9))
    nocap = copy.deepcopy(launch)
    nocap["cap_usd"] = None
    assert any("no recorded cap" in x for x in K.batch_problems(nocap, _batch(), price=0.72, cap_usd=0.6))
    assert any("no smoke job" in x for x in p({k: v for k, v in _batch().items() if k != "smoke"}))
    assert any("no prompt" in x for x in p(_batch(jobs=[_job("A", prompt="")])))
    assert any("settings are not written out" in x for x in p(_batch(jobs=[_job("A", settings={})])))
    assert any("start picture" in x for x in p(_batch(jobs=[_job("A", "edit", refs=[])])))
    assert any("sha256" in x for x in p(_batch(jobs=[_job("A", "edit", refs=[{"hf_path": "x"}])])))
    assert any("its own model" in x for x in p(_batch(jobs=[_job("A", model="other")])))
    assert any("own id" in x for x in p(_batch(jobs=[_job("A"), _job("A")])))
    assert any("max_pictures" in x for x in p(_batch(jobs=[_job(f"P{i}") for i in range(30)])))
    assert any("expected estimate" in x for x in p(_batch(jobs=[_job(f"P{i}") for i in range(24)]), cap_usd=0.15))


def test_the_plans_estimate_for_18_pictures_fits_sixty_cents(launch):
    est = K.estimate(launch, 17, 0.72)               # + the smoke picture = 18 pictures
    assert est["expected"]["usd"] < 0.6 and est["max"]["usd"] <= 0.6 + 0.2
    assert est["min"]["usd"] < est["expected"]["usd"] < est["max"]["usd"]


class Gen:
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def __call__(self, job, launch, refs, png):
        self.calls.append(job["id"])
        if self.fail_on == job["id"]:
            raise RuntimeError("boom")
        Path(png).write_bytes(b"png:" + job["id"].encode())


class Api:
    def __init__(self, break_on=None):
        self.files, self.order, self.break_on = {}, [], break_on

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        for op in operations:
            self.files[op.path_in_repo] = op.path_or_fileobj
        self.order.append("upload")

    def get_paths_info(self, repo, paths, repo_type=None, expand=None):
        return [SimpleNamespace(path=p, blob_id=None, lfs={"sha256": "bad" if self.break_on and self.break_on in p else
                                                           hashlib.sha256(Path(self.files[p]).read_bytes()).hexdigest()})
                for p in paths if p in self.files]


def Op(path_in_repo, path_or_fileobj):
    return SimpleNamespace(path_in_repo=path_in_repo, path_or_fileobj=path_or_fileobj)


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


def _kw(tmp_path, launch, **kw):
    ok_dl = lambda repo, rev, files, root: [((Path(root) / f).parent.mkdir(parents=True, exist_ok=True), (Path(root) / f).write_bytes(b"x")) for f in files]  # noqa: E731
    return dict({"launch": launch, "download": ok_dl, "fetch": lambda spec, dest: Path(dest), "vol_root": str(tmp_path / "dl"),
                 "tmp": str(tmp_path / "in"), "upload_op": Op}, **kw)


@pytest.fixture
def sha_ok(monkeypatch, launch):
    want = launch["models"][launch["model"]]["files"]

    def fake(p):
        n = Path(p).name
        for f, h in want.items():
            if str(p).endswith(f):
                return h
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    monkeypatch.setattr(M, "_sha", fake)


def test_l2_fails_before_any_load(tmp_path, launch, monkeypatch):
    gen = Gen()
    res = K.run(_batch(), tmp_path / "out", api=Api(), generate=gen, **_kw(tmp_path, launch, download=lambda *a: None))
    assert res["end"] == "L2_FAILED" and gen.calls == [] and "L3" not in res["steps"]
    monkeypatch.setattr(M, "_sha", lambda p: "0" * 64)
    res = K.run(_batch(), tmp_path / "out2", api=Api(), generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "L2_FAILED" and gen.calls == [] and any("sha256 mismatch" in p for p in res["steps"]["L2"]["problems"])


def test_a_smoke_failure_stops_the_pod(tmp_path, launch, sha_ok):
    gen = Gen(fail_on="L3_smoke")
    res = K.run(_batch(), tmp_path / "out", api=Api(), generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "L3_FAILED" and gen.calls == ["L3_smoke"]


def test_each_picture_is_verified_on_hf_before_the_next(tmp_path, launch, sha_ok):
    order, api = [], Api()
    gen = Gen()
    orig_commit = api.create_commit
    api.create_commit = lambda **kw: (order.append("upload"), orig_commit(**kw))[1]

    def g(job, lf, refs, png):
        order.append(job["id"])
        gen(job, lf, refs, png)
    res = K.run(_batch(3), tmp_path / "out", api=api, generate=g, **_kw(tmp_path, launch))
    assert res["end"] == "DONE" and [p["id"] for p in res["pictures"]] == ["P0", "P1", "P2"] and all(p["verified"] for p in res["pictures"])
    i = {k: order.index(k) for k in ("P0", "P1", "P2")}
    assert "upload" in order[i["P0"] + 1:i["P1"]] and "upload" in order[i["P1"] + 1:i["P2"]]
    rec = json.loads((tmp_path / "out" / "P0.record.json").read_text())
    assert rec["revision"] == REV and rec["refs"][0]["sha256"] == SHA and rec["prompt"] and rec["seed"] == 7 and rec["settings"]
    assert any(k.endswith("P2.record.json") for k in api.files) and any(k.endswith("L3_smoke.record.json") for k in api.files)


def test_an_unverified_picture_stops_the_batch(tmp_path, launch, sha_ok):
    gen, api = Gen(), Api(break_on="P0.png")
    res = K.run(_batch(3), tmp_path / "out", api=api, generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "UPLOAD_FAILED" and gen.calls == ["L3_smoke", "P0"]


def test_a_failed_picture_stops_the_batch(tmp_path, launch, sha_ok):
    gen = Gen(fail_on="P1")
    res = K.run(_batch(3), tmp_path / "out", api=Api(), generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "PICTURE_FAILED" and gen.calls == ["L3_smoke", "P0", "P1"]


def test_the_cap_clock_starts_at_the_pods_birth(tmp_path, launch, sha_ok, monkeypatch):
    clock, gen = Clock(), Gen()
    res = K.run(_batch(3), tmp_path / "out", api=Api(), generate=gen, clock=clock, created=clock() - 3600 * 0.7,
                **_kw(tmp_path, launch))                                # 0.7 h at $0.72 = $0.50 > 80 % of $0.60
    assert res["end"] == "CAPPED" and gen.calls == ["L3_smoke"] and res["spent_usd"] >= 0.5 - 0.01
    monkeypatch.setenv("EE_CREATED", str(clock() - 600))
    res = K.run(_batch(2), tmp_path / "out2", api=Api(), generate=Gen(), clock=clock, **_kw(tmp_path, launch))
    assert res["end"] == "DONE" and res["spent_usd"] == pytest.approx(0.12, abs=0.01)


def test_the_pod_refuses_a_cap_or_max_usd_above_the_recorded_one(tmp_path, launch, monkeypatch):
    gen = Gen()
    res = K.run(_batch(cap_usd=1.0), tmp_path / "o1", api=Api(), generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "REFUSED" and "L2" not in res["steps"] and gen.calls == []
    monkeypatch.setenv("EE_MAX_USD", "3.5")
    res = K.run(_batch(), tmp_path / "o2", api=Api(), generate=gen, **_kw(tmp_path, launch))
    assert res["end"] == "REFUSED" and any("EE_MAX_USD" in p for p in res["problems"]) and gen.calls == []


def test_the_real_launch_pod_refuses_to_run_with_open_pins(tmp_path):
    gen = Gen()
    res = K.run(_batch(), tmp_path / "out", api=Api(), generate=gen, vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"))
    assert res["end"] == "REFUSED" and gen.calls == []


def test_the_pod_script_passes_lint_and_is_unbuilt_until_the_pins_are_filled():
    from explainer_engine.cloud import dryrun, runpod
    text = K.LAUNCHER.read_text(encoding="utf-8")
    assert runpod.lint_pod_script(text) == [] and runpod.is_wrapper_script(text) and dryrun.static_problems(text.replace("@@DIFFUSERS_VERSION@@", "0.0.0").replace("@@EE_SRC_SHA256@@", SHA)) == []
    assert "klein_jobs run" in text and "/workspace/dl" in text
    assert K.script_problems(text)
    assert K.script_problems(text.replace("@@DIFFUSERS_VERSION@@", "0.0.0").replace("@@EE_SRC_SHA256@@", SHA)) == []


def test_plan_reads_the_batch_file_only(tmp_path):
    bp = tmp_path / "b.json"
    bp.write_text(json.dumps(_batch()))
    out = K.plan(str(bp))
    assert out["ok"] is False and out["problems"] and out["estimate"]["expected"]["usd"] > 0 and out["card"].startswith("NVIDIA RTX PRO 4500")


def test_the_retired_guard_lets_only_the_two_ab_launchers_through(tmp_path):
    from explainer_engine.core.errors import ConfigError
    from explainer_engine.episode import retired
    ep = tmp_path / "ep"
    ep.mkdir()
    (ep / "episode.json").write_text(json.dumps({"schema": "episode_manifest/1"}))
    klein = "explainer_engine/training/pods/klein/klein_pod.sh"
    retired.refuse("runpod", ep / "production", env={}, cwd=tmp_path, script=klein)
    retired.refuse("runpod", ep / "production", env={}, cwd=tmp_path, script="/repo/" + klein)
    for other in ("explainer_engine/training/pods/p14/p14.sh", "explainer_engine/training/pods/klein/klein_pod.sh.bak",
                  "other/klein/klein_pod.sh", "explainer_engine/training/pods/xworld_v1.sh", None):
        with pytest.raises(ConfigError, match="retired for a v4.3 episode"):
            retired.refuse("runpod", ep / "production", env={}, cwd=tmp_path, script=other)
    assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPWSuqhe7svtHM5ptNMiw84V4" in retired.load()["tools"]["runpod"]["exception"]["decided"]
    assert retired.excepted("ltx", klein) is False              # the ltx entry keeps only its own launcher
    assert retired.excepted("qwen_image", klein) is False
