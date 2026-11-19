"""W5 (plan RUNPOD_AB_PLAN.md section 3): the RunPod runner of the LTX A/B. No pod, no money, no network: a fake CLI process and a
fake HF API stand in. It reuses the Modal worker's pure functions, so the same job gives the same CLI arguments; L2 ends the pod
before any model load; a cap stop starts no new clip; no clip starts before the previous one is verified on HF (OR-33); the retired
guard lets this one launcher through and nothing else."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from explainer_engine.episode import retired
from explainer_engine.core.errors import ConfigError
from explainer_engine.training.pods.ltx import modal_ltx_jobs as M
from explainer_engine.training.pods.ltx import runpod_ltx_jobs as R

ROOT = Path(M.__file__).resolve().parents[4]
PINS = json.loads((ROOT / "config" / "cloud_pins.json").read_text())["models"]["video_ltx"]
LAUNCH = M.load_launch()
SHA = "ab" * 32


def _png():
    b = io.BytesIO()
    Image.new("RGB", (64, 48), (90, 60, 30)).save(b, "PNG")
    return b.getvalue()


def _clip(shot="S07_SH008", **kw):
    pic = _png()
    return dict({"shot_id": shot, "seconds": 2.0, "fps": 24, "width": 1280, "height": 704, "seed": 7112,
                 "motion_prompt": "Thomas climbs down.", "start_bytes": pic, "start_sha256": hashlib.sha256(pic).hexdigest()}, **kw)


def _guided(shot="S07_SH008", **kw):
    return _clip(shot, kind="keyframes", end_picture="e.png", end_frame=47, end_bytes=_png(), extra={"end_sha256": SHA},
                 settings={k: LAUNCH["kind_defaults"][k] for k in M.KIND_SETTINGS} | {"image_strength": 1.0}, **kw)


@pytest.fixture
def launch():
    lf = copy.deepcopy(LAUNCH)
    lf["runpod"]["image"] = "ghcr.io/x/y@sha256:" + "0" * 64
    return lf


def test_the_launch_has_a_runpod_section_with_open_items_marked():
    sec = LAUNCH["runpod"]
    assert [c["gpu"] for c in sec["cards"]][0].startswith("NVIDIA RTX PRO 6000 Blackwell")
    assert sec["image"] is None and "OPEN" in sec["image_why"] and sec["cap_usd"] is None   # nothing is assumed (OR-22)
    assert "network volume" in sec["container_disk_why"]
    assert R.card_of(LAUNCH) == ("NVIDIA RTX PRO 6000 Blackwell Server Edition", 1.69)


def test_the_same_job_gives_the_same_cli_arguments_on_modal_and_runpod(monkeypatch):
    modal = {k: M.kind_cmd(LAUNCH, _guided(), "/t/s.png", "/o/c.mp4", end_png="/t/e.png", python="py") for k in ("g",)}["g"]
    clip_modal = M.ltx_cmd(LAUNCH, _clip(), "/t/s.png", "/o/c.mp4", python="py")
    monkeypatch.setenv("EE_LTX_VOL_ROOT", "/workspace/dl")
    pod = M.kind_cmd(LAUNCH, _guided(), "/t/s.png", "/o/c.mp4", end_png="/t/e.png", python="py")
    clip_pod = M.ltx_cmd(LAUNCH, _clip(), "/t/s.png", "/o/c.mp4", python="py")
    swap = lambda cmd: [a.replace("/workspace/dl/", "/w/") for a in cmd]      # noqa: E731
    assert swap(pod) == modal and swap(clip_pod) == clip_modal
    assert any(a.startswith("/workspace/dl/model/") for a in pod) and not any(a.startswith("/w/") for a in pod)


def test_batch_files_hold_the_guided_files_only_for_a_batch_that_needs_them():
    clip_only = R.batch_files(LAUNCH, [_clip()])
    guided = R.batch_files(LAUNCH, [_clip(), _guided()])
    assert not set(LAUNCH["kind_model_files"]) & set(clip_only)
    assert set(LAUNCH["kind_model_files"]) <= set(guided)
    assert set(LAUNCH["model_files"]) <= set(clip_only)


def test_the_local_refusals(launch):
    ok = R.batch_problems(launch, [_clip()], price=1.69, cap_usd=3.5, pins=PINS)
    assert ok == []
    assert any("no pinned image" in p for p in R.batch_problems(LAUNCH, [_clip()], price=1.69, cap_usd=3.5, pins=PINS))
    assert any("no cap" in p for p in R.batch_problems(launch, [_clip()], price=1.69, cap_usd=None, pins=PINS))
    assert any("per_pod_usd" in p for p in R.batch_problems(launch, [_clip()], price=1.69, cap_usd=99.0, pins=PINS))
    assert any("CT1_MAX_HOP" in p for p in R.batch_problems(launch, [_clip(hop=3)], price=1.69, cap_usd=3.5, pins=PINS))
    assert not any("CT1_MAX_HOP" in p for p in R.batch_problems(launch, [_clip(hop=2)], price=1.69, cap_usd=3.5, pins=PINS))
    # the Modal worker's own job refusals: an unpinned guided file, a job naming its own checkpoint
    unpinned = copy.deepcopy(launch)
    unpinned["kind_uses"].pop("dev_transformer")
    assert R.batch_problems(unpinned, [_guided()], price=1.69, cap_usd=3.5, pins=PINS)
    assert any("checkpoint_path" in p for p in R.batch_problems(launch, [_clip(kind="retake", checkpoint_path="/x")], price=1.69,
                                                                 cap_usd=3.5, pins=PINS))
    # an estimate over the owner's cap, and one run alone over it
    many = [_guided(f"S{i}") for i in range(6)]
    assert any("over the cap" in p for p in R.batch_problems(launch, many, price=1.69, cap_usd=3.5, pins=PINS))
    assert any("one run alone" in p for p in R.batch_problems(launch, [_guided()], price=1.69, cap_usd=0.2, pins=PINS))


def test_the_estimate_is_the_plans_table(launch):
    est = R.estimate(launch, [_clip()] * 8 + [_guided()] * 3, 1.69)   # the plan's all-shots batch (arm a of S07_SH008 is reused there)
    assert est["min"]["minutes"] < est["expected"]["minutes"] < est["max"]["minutes"]
    assert abs(est["expected"]["minutes"] - 79.0) < 1.0            # the plan's all-shots expected minutes
    assert est["expected"]["usd"] == pytest.approx(est["expected"]["minutes"] / 60 * 1.69, abs=0.01)


# --- the pod side with fakes ------------------------------------------------------------------------------------------------
class FakeSh:
    def __init__(self, rc=0):
        self.calls, self.rc = [], rc

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        if "--output-path" in cmd and self.rc == 0:
            Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"mp4:" + cmd[cmd.index("--seed") + 1].encode() + str(len(self.calls)).encode())
        return SimpleNamespace(returncode=self.rc)


def Op(path_in_repo, path_or_fileobj):
    return SimpleNamespace(path_in_repo=path_in_repo, path_or_fileobj=path_or_fileobj)


class FakeApi:
    def __init__(self, break_on=None):
        self.files, self.commits, self.break_on = {}, [], break_on

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        for op in operations:
            self.files[op.path_in_repo] = op.path_or_fileobj
        self.commits.append([op.path_in_repo for op in operations])

    def get_paths_info(self, repo, paths, repo_type=None, expand=None):
        out = []
        for p in paths:
            if p in self.files:
                sha = hashlib.sha256(Path(self.files[p]).read_bytes()).hexdigest()
                out.append(SimpleNamespace(path=p, lfs={"sha256": "bad" if self.break_on and self.break_on in p else sha}, blob_id=None))
        return out


class Clock:
    def __init__(self, step=0.0):
        self.t, self.step = 1000.0, step

    def __call__(self):
        return self.t

    def jump(self, s):
        self.t += s


def _stage_ok(monkeypatch, tmp_path, launch):
    """Every pinned file present with its sha (``_sha`` is read from the pin, files are tiny stand-ins)."""
    want = {**launch["model_files"], **launch["kind_model_files"]}
    root = M.weights_root(launch, str(tmp_path))
    real = M._sha

    def fake_sha(p):
        try:
            return want[Path(p).relative_to(root).as_posix()]
        except ValueError:                                         # a clip, not a weight: its real hash
            return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    monkeypatch.setattr(M, "_sha", fake_sha)

    def download(repo, rev, files, root):
        for f in files:
            (Path(root) / f).parent.mkdir(parents=True, exist_ok=True)
            (Path(root) / f).write_bytes(b"x")
    return download


def _batch(**kw):
    return dict({"card": "NVIDIA RTX PRO 6000 Blackwell Server Edition", "price": 1.69, "cap_usd": 3.5, "prefix": "ltx_route/runpod_ab"}, **kw)


def test_l2_fails_before_any_model_load_and_the_pod_ends(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    sh = FakeSh()
    bad_download = lambda repo, rev, files, root: None            # nothing arrives: every file missing        # noqa: E731
    res = R.run(_batch(), [_guided()], tmp_path / "out", api=FakeApi(), sh=sh, download=bad_download, vol_root=str(tmp_path / "dl"),
                tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "L2_FAILED" and sh.calls == [] and "L3" not in res["steps"]
    assert any(p.startswith("missing") for p in res["steps"]["L2"]["problems"])
    assert json.loads((tmp_path / "out" / "run_record.json").read_text())["end"] == "L2_FAILED"
    # a sha mismatch is the same end
    monkeypatch.setattr(M, "_sha", lambda p: "0" * 64)
    ok_files = lambda repo, rev, files, root: [((Path(root) / f).parent.mkdir(parents=True, exist_ok=True), (Path(root) / f).write_bytes(b"x")) for f in files]  # noqa: E731
    res = R.run(_batch(), [_clip()], tmp_path / "out2", api=FakeApi(), sh=sh, download=ok_files, vol_root=str(tmp_path / "dl2"),
                tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "L2_FAILED" and sh.calls == [] and any("sha256 mismatch" in p for p in res["steps"]["L2"]["problems"])


def test_a_smoke_failure_stops_the_pod_before_the_batch(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    dl = _stage_ok(monkeypatch, tmp_path / "dl", launch)
    sh = FakeSh(rc=1)
    res = R.run(_batch(), [_clip()], tmp_path / "out", api=FakeApi(), sh=sh, download=dl, vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "L3_FAILED" and len(sh.calls) == 1 and res["steps"]["L3"]["card"].startswith("NVIDIA RTX PRO 6000")


def test_the_batch_runs_each_clip_verified_before_the_next(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    dl = _stage_ok(monkeypatch, tmp_path / "dl", launch)
    order = []
    api, sh = FakeApi(), FakeSh()
    orig_commit, orig_call = api.create_commit, sh.__call__
    api.create_commit = lambda **kw: (order.append("upload"), orig_commit(**kw))[1]
    sh2 = lambda cmd, **kw: (order.append("clip"), orig_call(cmd, **kw))[1]                    # noqa: E731
    res = R.run(_batch(), [_clip("A"), _clip("B", seed=8)], tmp_path / "out", api=api, sh=sh2, download=dl,
                vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "DONE" and [c["state"] for c in res["clips"]] == ["DONE", "DONE"] and all(c["verified"] for c in res["clips"])
    clip_idx = [i for i, w in enumerate(order) if w == "clip"]
    assert len(clip_idx) == 3                                       # smoke + 2
    assert "upload" in order[clip_idx[1] + 1:clip_idx[2]], "the first clip must be uploaded before the second starts"


def test_a_clip_that_is_not_verified_on_hf_stops_the_batch(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    dl = _stage_ok(monkeypatch, tmp_path / "dl", launch)
    sh, api = FakeSh(), FakeApi(break_on="S07_SH008")
    res = R.run(_batch(), [_clip("S07_SH008"), _clip("B", seed=8)], tmp_path / "out", api=api, sh=sh, download=dl,
                vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "UPLOAD_FAILED" and len(sh.calls) == 2      # smoke + the first clip; B never started
    assert any("hash differs" in p or "not verified" in p for p in res["problems"])


def test_the_cap_stops_new_clips_at_80_percent(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    dl = _stage_ok(monkeypatch, tmp_path / "dl", launch)
    clock, api = Clock(), FakeApi()
    sh0 = FakeSh()

    def sh(cmd, **kw):
        r = sh0(cmd, **kw)
        clock.jump(2400)                                           # every process takes 40 min of pod time
        return r
    res = R.run(_batch(), [_clip("A"), _clip("B", seed=8), _clip("C", seed=9)], tmp_path / "out", api=api, sh=sh, download=dl,
                clock=clock, vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "CAPPED" and any("PROBLEM" in p for p in res["problems"])
    assert len(sh0.calls) < 4
    assert len(res.get("clips", [])) < 3


def test_an_over_cap_batch_is_refused_in_the_pod_too(monkeypatch, tmp_path, launch):
    monkeypatch.setattr(M, "LAUNCH", launch)
    sh = FakeSh()
    res = R.run(_batch(cap_usd=0.3), [_clip()], tmp_path / "out", api=FakeApi(), sh=sh, download=lambda *a: None,
                vol_root=str(tmp_path / "dl"), tmp=str(tmp_path / "in"), upload_op=Op)
    assert res["end"] == "REFUSED" and sh.calls == []


# --- the retired guard and the pod script ----------------------------------------------------------------------------------
@pytest.fixture
def episode(tmp_path):
    ep = tmp_path / "ep"
    ep.mkdir()
    (ep / "episode.json").write_text(json.dumps({"schema": "episode_manifest/1"}))
    return ep


def test_the_retired_guard_lets_only_this_launcher_through(episode, tmp_path):
    mine = "explainer_engine/training/pods/ltx/runpod_ltx_pod.sh"
    for tool in ("runpod", "ltx"):
        retired.refuse(tool, episode / "production", env={}, cwd=tmp_path, script=mine)                      # excepted
        retired.refuse(tool, episode / "production", env={}, cwd=tmp_path, script="/repo/" + mine)
        for other in ("explainer_engine/training/pods/p14/p14.sh", "explainer_engine/training/pods/p15/modal_ltx_jobs_v1.py",
                      "explainer_engine/training/pods/ltx/runpod_ltx_pod.sh.bak", "x/runpod_ltx_pod.sh", None):
            with pytest.raises(ConfigError, match="retired for a v4.3 episode"):
                retired.refuse(tool, episode / "production", env={}, cwd=tmp_path, script=other)
    ex = retired.load()["tools"]["runpod"]["exception"]
    assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPWYBU8BqKt8DFFsw46f9xMHj" in ex["decided"] and ex["launchers"] == [mine]
    assert retired.excepted("qwen_image", mine) is False                       # Qwen stays retired everywhere


def test_the_pod_script_passes_the_lint_and_the_dryrun_rules_but_is_unbuilt():
    from explainer_engine.cloud import dryrun, runpod
    text = R.LAUNCHER.read_text(encoding="utf-8")
    assert runpod.lint_pod_script(text) == [] and runpod.is_wrapper_script(text)
    assert dryrun.static_problems(text) == []
    assert "runpod_ltx_jobs run" in text and "/workspace/dl" in text and "network" not in text.split("\n", 12)[-1]
    assert R.script_problems(text)                                            # the bundle sha is a placeholder until built
    assert R.script_problems(text.replace("@@EE_SRC_SHA256@@", SHA)) == []
    rec = dryrun.run(text.replace("@@EE_SRC_SHA256@@", SHA), offline=True, folder=R.LAUNCHER.parent)
    assert isinstance(rec, dict) and "sha256" in rec


def test_plan_reads_job_files_only_and_refuses_without_image_and_cap(tmp_path):
    out = R.plan([], cap_usd=None)
    assert out["ok"] is False and any("no pinned image" in p for p in out["problems"]) and any("no cap" in p for p in out["problems"])
    assert any("sha256" in p for p in out["problems"])                        # the unbuilt script
    assert out["estimate"] is None and out["card"].startswith("NVIDIA RTX PRO 6000")


def test_runpod_create_hands_its_script_to_the_retired_guard():
    src = (ROOT / "explainer_engine" / "cloud" / "runpod.py").read_text(encoding="utf-8")
    assert 'script=_opt(rest, "--script")' in src and 'retired.refuse("runpod"' in src
