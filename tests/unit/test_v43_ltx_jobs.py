"""The LTX worker of the video route (D-132, the creator 2026-11-12 19:10 UTC): the launch file holds the bake-off's pins and
the creator's modal_ltx line; the timeouts come from the caps; the preflight refuses an unpinned or over-cap run, an end
picture and a chained shot without its prompt; the GPU body writes every clip, chains the next shot from the previous clip's
last frame, stops a chain the deadline cannot finish, copies to the Volume, checks HF and returns plain JSON; a rescheduled
input is refused; the session hook frees only the CPU rungs. No Modal, GPU or HF call: every container step is faked."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.cloud import hooks as H
from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

LAUNCH = L.load_launch()
WORKER = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"


def test_the_launch_file_is_pinned_with_the_bakeoffs_weights_and_priced_from_the_table():
    assert L.launch_problems(LAUNCH) == []
    assert LAUNCH["module"] == "ltx_pipelines.distilled" and LAUNCH["gpu"] == "H100"
    assert set(LAUNCH["uses"].values()) <= set(LAUNCH["model_files"])
    assert abs(L.schedule_rate(LAUNCH) - L.usd_per_h(LAUNCH)) <= 0.01 * L.schedule_rate(LAUNCH)
    assert LAUNCH["scaledown_window_s"] <= 5                      # nothing stays warm


def test_every_timeout_comes_from_its_cap_and_leaves_the_end_path():
    smoke, run = L.TIMEOUTS
    h, c = L.usd_per_h(LAUNCH), LAUNCH["caps"]
    for t, cap in ((smoke, c["smoke_usd"]), (run, c["run_usd"])):
        assert t > L.MARGIN_S and (t + c["cold_start_s"]) * h / 3600 <= cap
    with pytest.raises(ValueError):
        L.check_timeout(L.MARGIN_S, 1.0, h, 60)


def test_frames_are_8k_plus_1_and_a_shot_past_the_longest_clip_is_refused():
    assert L.ltx_frames(9.5, 24) == 233 and (L.ltx_frames(9.5, 24) - 1) % 8 == 0
    assert L.native_spec(LAUNCH, 10.0)["frames"] == 241
    with pytest.raises(ValueError):
        L.native_spec(LAUNCH, 10.5)


def test_preflight_needs_the_creators_modal_ltx_line_and_a_whole_chain(monkeypatch):
    from explainer_engine.core import spend_caps
    job = {"shot_id": "c1", "seconds": 9.5, "seed": 1, "motion_prompt": "two people talk",
           "chain": [{"shot_id": "c2", "seconds": 9.5, "seed": 2, "motion_prompt": "they go on"}]}
    monkeypatch.setattr(spend_caps, "modal_ltx", lambda episode=False: {"per_run_usd": 2.0})
    L.preflight(LAUNCH, job)
    for broken in ({"chain": [{"shot_id": "c2", "seconds": 9.5, "seed": 2, "motion_prompt": " "}]},
                   {"chain": [{"shot_id": "c2", "seconds": 12.0, "seed": 2, "motion_prompt": "x"}]},
                   {"end_picture": "e.png"}, {"seed": None}):
        with pytest.raises(SystemExit):
            L.preflight(LAUNCH, dict(job, **broken))
    monkeypatch.setattr(spend_caps, "modal_ltx", lambda episode=False: {"per_run_usd": LAUNCH["caps"]["run_usd"] / 0.8 - 0.01})
    with pytest.raises(SystemExit, match="above 80 %"):
        L.preflight(LAUNCH)

    def zero(episode=False):
        raise spend_caps.OverCeiling("no modal_ltx line: a zero budget")
    monkeypatch.setattr(spend_caps, "modal_ltx", zero)
    with pytest.raises(SystemExit, match="zero budget"):
        L.preflight(LAUNCH)


def test_the_creators_line_is_in_the_one_budget_file():
    from explainer_engine.core import spend_caps
    assert float(spend_caps.modal_ltx()["per_run_usd"]) == 1.5
    assert L.LAUNCH["caps"]["run_usd"] <= 0.8 * 1.5 + 1e-9


def test_the_ltx_command_names_the_pinned_files_the_start_picture_and_the_frames():
    job = {"shot_id": "c1", "seconds": 9.5, "seed": 5, "fps": 24, "width": 1280, "height": 704, "motion_prompt": "p"}
    s = " ".join(L.ltx_cmd(LAUNCH, job, "/tmp/in/p.png", "/o/.c1_seed5.mp4"))
    for f in LAUNCH["uses"].values():
        assert f in s
    assert "--image /tmp/in/p.png 0 1.0" in s and "--num-frames 233" in s and "--frame-rate 24" in s and "--seed 5" in s


def test_a_rescheduled_input_is_refused_by_its_attempt_marker(tmp_path):
    job = {"run_id": "r", "shot_id": "s", "nonce": "n1"}
    assert L.attempt_guard(tmp_path, job) is None
    assert L.attempt_guard(tmp_path, job) == "REFUSED_SECOND_ATTEMPT"
    assert L.attempt_guard(tmp_path, dict(job, nonce="n2")) is None


def test_no_code_path_kills_its_own_process_and_libs_are_plain_strings():
    src = Path(L.__file__).read_text()
    assert "os._exit(" not in src and "threading.Timer" not in src
    assert all(v is None or isinstance(v, str) for v in L.libs().values())


class FakeApi:
    def __init__(self, fail=0):
        self.store, self.fail = {}, fail

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        if self.fail:
            self.fail -= 1
            raise RuntimeError("429")
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
    Image.new("RGB", (2752, 1536), color).save(b, "PNG")
    return b.getvalue()


@pytest.fixture
def container(tmp_path, monkeypatch):
    import huggingface_hub
    monkeypatch.setattr(huggingface_hub, "CommitOperationAdd",
                        lambda path_in_repo, path_or_fileobj: SimpleNamespace(path_in_repo=path_in_repo, path_or_fileobj=path_or_fileobj))
    launch = copy.deepcopy(LAUNCH)
    root = tmp_path / "w" / "model" / launch["model_repo"]
    for f in launch["model_files"]:
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"w")
    monkeypatch.setattr(L, "weights_root", lambda la, vol_root="/w": root)
    calls, clock = [], [0.0]

    def sh(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "ffmpeg":                       # the last frame of the clip named after -i
            src = Path(cmd[cmd.index("-i") + 1]).read_bytes()
            Path(cmd[-1]).write_bytes(_png((len(src) % 255, 0, 0)))
        else:
            clock[0] += 80.0
            pic = Path(cmd[cmd.index("--image") + 1]).read_bytes()
            Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"mp4:" + hashlib.sha256(pic).hexdigest().encode())
        return SimpleNamespace(returncode=0)
    pic = _png((10, 20, 30))
    job = {"shot_id": "c1", "seconds": 9.5, "seed": 1, "fps": 24, "width": 1280, "height": 704, "motion_prompt": "talk",
           "run_id": "rid", "launch_sha": L.launch_sha(launch), "nonce": "n1", "start_bytes": pic,
           "start_sha256": hashlib.sha256(pic).hexdigest(),
           "chain": [{"shot_id": "c2", "seconds": 9.5, "seed": 2, "motion_prompt": "more"},
                     {"shot_id": "c3", "seconds": 9.5, "seed": 3, "motion_prompt": "kiss"}]}
    return SimpleNamespace(launch=launch, job=job, sh=sh, calls=calls, clock=clock, tmp=tmp_path)


def _run(c, timeout_s=582, api=None):
    return L.body(c.job, c.launch, timeout_s, vol_root=c.tmp / "w", api=api if api is not None else FakeApi(), sh=c.sh,
                  now=lambda: c.clock[0], out_root=c.tmp / "out")


def test_a_chain_makes_every_clip_from_the_last_frame_before_it_and_checks_hf(container, monkeypatch):
    monkeypatch.setattr(L, "fit_picture", lambda img, w, h: img)
    res = _run(container)
    assert json.loads(json.dumps(res)) == res and res["state"] == "DONE"
    assert [r["state"] for r in res["chain"]] == ["DONE"] * 3
    clis = [c for c in container.calls if c[0] != "ffmpeg"]
    starts = [Path(c[c.index("--image") + 1]).name for c in clis]
    assert len(clis) == 3 and starts[0].startswith("c1_") and starts[1].startswith("c2_") and starts[2].startswith("c3_")
    out = container.tmp / "out" / "rid" / "c1"
    assert (out / "c2.start.png").is_file() and (out / "c3.start.png").is_file()
    assert set(res["verified"].values()) == {"ok"} and {"c1_seed1.mp4", "c2_seed2.mp4", "c3_seed3.mp4"} <= set(res["verified"])
    vol = container.tmp / "w" / L.VOL_OUT / "rid" / "c1"
    assert (vol / "c3_seed3.mp4").is_file() and (vol / "c1.measured.json").is_file()


def test_a_chain_the_deadline_cannot_finish_keeps_what_it_made(container, monkeypatch):
    monkeypatch.setattr(L, "fit_picture", lambda img, w, h: img)
    res = _run(container, timeout_s=L.MARGIN_S + 200)        # room for two clips of 80 s, not for a third
    assert [r["state"] for r in res["chain"]] == ["DONE", "DONE", "PARTIAL"]
    assert res["state"] == "PARTIAL" and "not started" in res["chain"][2]["why"]
    assert (container.tmp / "w" / L.VOL_OUT / "rid" / "c1" / "c2_seed2.mp4").is_file()


def test_with_hf_down_the_clips_stay_on_the_volume_and_the_state_says_so(container, monkeypatch):
    monkeypatch.setattr(L, "fit_picture", lambda img, w, h: img)
    real = L.upload_round
    monkeypatch.setattr(L, "upload_round", lambda *a, **k: real(*a, **dict(k, sleep=lambda s: None)))
    res = _run(container, api=FakeApi(fail=99))
    assert res["state"] == "UPLOAD_UNVERIFIED"
    assert (container.tmp / "w" / L.VOL_OUT / "rid" / "c1" / "c3_seed3.mp4").is_file()


def test_a_second_attempt_of_the_same_launch_runs_nothing(container):
    _run(container)
    n = len(container.calls)
    assert _run(container)["state"] == "REFUSED_SECOND_ATTEMPT" and len(container.calls) == n


def test_the_session_hook_frees_only_the_ltx_cpu_rungs():
    for entry in ("check", "weights"):
        assert H.modal_refusal(f"modal run {WORKER}::{entry}", env={}) is None
    for entry in ("smoke", "main", "stage"):
        assert "EE_MODAL_GO" in (H.modal_refusal(f"modal run {WORKER}::{entry}", env={}) or "")
        assert H.modal_refusal(f"EE_MODAL_GO=cmsg_abc:{'a' * 12} modal run {WORKER}::{entry}", env={}) is None
    assert "refused" in (H.modal_refusal(f"modal shell {WORKER}", env={}) or "")


def test_the_scene_test_spec_pins_its_picture_plan_and_chain_and_the_ledger_refuses_a_repeat(tmp_path, monkeypatch):
    from PIL import Image
    from explainer_engine.core import spend_caps
    from explainer_engine.training.pods.ltx import scene_run as SR
    monkeypatch.setattr(spend_caps, "modal_ltx", lambda episode=False: {"per_run_usd": 2.0})
    real = json.loads((Path(L.__file__).parent / "scenes" / "love_2026-11-12.json").read_text(encoding="utf-8"))
    assert [s["shot_id"] for s in real["shots"]] == ["love_c1", "love_c2", "love_c3"]
    assert all(s["seconds"] <= L.max_seconds(LAUNCH) for s in real["shots"]) and "lantern" not in json.dumps(real["shots"])
    pic = tmp_path / "start.png"
    Image.new("RGB", (1181, 650), (9, 9, 9)).save(pic)
    scene = dict(real, start_picture={"path": str(pic), "sha256": hashlib.sha256(pic.read_bytes()).hexdigest()})
    sp = tmp_path / "scene.json"
    sp.write_text(json.dumps(scene))
    spec = SR.job_spec(sp)
    assert spec["plan_sha256"] == SR.plan_sha(sp) and spec["run_id"] == L.run_id(spec["plan_sha256"], LAUNCH)
    assert (spec["fps"], spec["width"], spec["height"]) == (24, 1280, 704)
    assert [c["shot_id"] for c in spec["chain"]] == ["love_c2", "love_c3"]
    out = tmp_path / "spec.json"
    out.write_text(json.dumps(spec))
    assert L.read_job(str(out))["start_sha256"] == scene["start_picture"]["sha256"]
    led = tmp_path / "led.json"
    assert SR.reserve(spec, path=led) == LAUNCH["caps"]["run_usd"]
    with pytest.raises(SystemExit, match="already holds"):
        SR.reserve(spec, path=led)
    assert SR.settle(spec, 360, path=led) == round(360 * L.usd_per_h(LAUNCH) / 3600, 4)
    data = json.loads(led.read_text())
    assert data["reserved"][SR.item(spec)]["settled"] and abs(data["spent"]["modal_ltx"] - 360 * L.usd_per_h(LAUNCH) / 3600) < 1e-3
    pic.write_bytes(b"changed")
    with pytest.raises(SystemExit, match="not the one the scene pins"):
        SR.job_spec(sp)
