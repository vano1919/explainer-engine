"""The v4.3 video bake-off (the creator, 2026-11-12 15:01 UTC; variants 1, 4, 5 at 15:12 UTC): the plan holds every pin, size,
length and cap before a paid call; timeouts come from the caps; the GO binds the plan's bytes; the stage-in downloads only
what is missing; LTX's command line names the pinned files; a Wan shot is two clips chained on frame[-5]; the local report
upscales, measures and prices every clip. No Modal, GPU or HF call: every container step is faked."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.cloud import modal_schedule as MS
from explainer_engine.training.pods.bakeoff import modal_bakeoff as B
from explainer_engine.training.pods.bakeoff import report as R

PLAN = B.load_plan()


def test_the_committed_plan_holds_and_keeps_only_the_creators_three_variants():
    assert B.plan_problems(PLAN) == []
    assert [v["id"] for v in PLAN["variants"]] == ["ltx_distilled", "wan_a14b_lightning", "wan_ti2v_5b"]
    assert PLAN["variants_chosen"]["message_id"].startswith("cmsg_")
    caps = sum(v["cap_usd"] for v in PLAN["variants"]) + PLAN["stage"]["cap_usd"]
    assert caps <= PLAN["total_cap_usd"] + 1e-9
    for v in PLAN["variants"]:
        assert 9.5 <= B.shot_seconds(v) <= 10.5


def test_prices_equal_the_modal_schedule_table():
    for g, usd in B.USD_S.items():
        assert MS.GPUS[g]["usd_s"] == usd
    assert (B.CPU_CORE_S, B.MEM_GIB_S) == (MS.CPU_CORE_S, MS.MEM_GIB_S)


def test_every_timeout_comes_from_its_cap():
    for v in PLAN["variants"]:
        rate = B.usd_per_h(v["gpu"], v["cpu"], v["memory_gib"])
        t = B.timeout_of(PLAN, v)
        assert (PLAN["cold_start_s"] + t) * rate / 3600 <= v["cap_usd"]
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
])
def test_a_broken_plan_is_refused(break_it, why):
    p = copy.deepcopy(PLAN)
    break_it(p)
    assert any(why in b for b in B.plan_problems(p))


def test_preflight_needs_the_creators_modal_line_over_every_cap():
    B.preflight(PLAN, spend_line=10.0)
    with pytest.raises(SystemExit, match="above the creator"):
        B.preflight(PLAN, spend_line=1.0)


def test_the_go_binds_the_plans_bytes():
    sha = B.plan_sha()
    assert B.go_gate({"EE_MODAL_GO": f"cmsg_1A:{sha[:12]}"}, sha) == "cmsg_1A"
    with pytest.raises(SystemExit, match="another plan"):
        B.go_gate({"EE_MODAL_GO": "cmsg_1A:000000000000"}, sha)
    with pytest.raises(SystemExit):
        B.go_gate({}, sha)


def test_join_shows_the_anchor_frame_once_like_the_splice_spec():
    from explainer_engine.aivideo import wan_optimizer as WO
    a, b = list(range(81)), list(range(100, 181))     # b[0] is made from a[76] = frame[-5]
    j = B.join_clips([a, b], 5)
    spec = WO.compute_continuation_splice_spec(81, 81, offset_from_end=5, fps=16)
    assert len(j) == spec["prev_clip_play_frames_before_splice"] + 81 and j[75] == 75 and j[76] == 100
    v = B.variant(PLAN, "wan_a14b_lightning")
    assert B.chained_frames(v) == len(j)


def test_fit_picture_centre_crops_to_the_clip():
    from PIL import Image
    im = Image.new("RGB", (2752, 1536), (10, 20, 30))
    out = B.fit_picture(im, 1280, 704)
    assert out.size == (1280, 704)


def test_stage_downloads_only_what_is_missing_and_checks_every_sha(tmp_path):
    plan = {"weights": {"w": {"repo": "o/r", "revision": "a" * 40, "files": {}}}}
    root = tmp_path / "model" / "o/r"
    root.mkdir(parents=True)
    (root / "have.bin").write_bytes(b"have")
    plan["weights"]["w"]["files"] = {"have.bin": hashlib.sha256(b"have").hexdigest(),
                                     "new.bin": hashlib.sha256(b"new").hexdigest()}
    asked = []

    def dl(repo, rev, files, r):
        asked.append((repo, rev, list(files)))
        (Path(r) / "new.bin").write_bytes(b"new")
    assert B.stage_weights(plan, str(tmp_path), dl) == []
    assert asked == [("o/r", "a" * 40, ["new.bin"])]
    (root / "new.bin").write_bytes(b"changed")
    assert any("mismatch" in b for b in B.stage_weights(plan, str(tmp_path), dl))


def test_the_ltx_command_names_the_pinned_files_and_the_start_picture():
    v = B.variant(PLAN, "ltx_distilled")
    cmd = B.ltx_cmd(PLAN, v, PLAN["shots"][0], "/tmp/in/p.png", "/o/dialogue.mp4")
    s = " ".join(cmd)
    assert cmd[:3] == ["python3", "-m", "ltx_pipelines.distilled"]
    for f in PLAN["weights"]["ltx25"]["files"]:
        assert f in s
    assert "--image /tmp/in/p.png 0 1.0" in s and "--num-frames 241" in s and "--frame-rate 24" in s
    assert "--distilled-lora" not in s


def test_make_ltx_records_each_shot_with_a_fake_cli(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(B, "Path", Path)
    pics = {}
    for s in PLAN["shots"]:
        p = tmp_path / f"{s['id']}.png"
        Image.new("RGB", (640, 360)).save(p)
        pics[s["id"]] = p
    (tmp_path / "in").mkdir()
    real = Path

    def fake_sh(cmd, **kw):
        mp4 = cmd[cmd.index("--output-path") + 1]
        real(mp4).write_bytes(b"video" if "dialogue" in mp4 else b"")
        return subprocess.CompletedProcess(cmd, 0 if "dialogue" in mp4 else 1)
    v = B.variant(PLAN, "ltx_distilled")
    monkeypatch.setattr(B, "fit_picture", lambda img, w, h: img)
    orig = B.make_ltx.__globals__["Path"]
    monkeypatch.setitem(B.make_ltx.__globals__, "Path", lambda x="": real(str(x).replace("/tmp/in", str(tmp_path / "in"))))
    res = B.make_ltx(PLAN, v, str(tmp_path), pics, beat_fn=lambda *a, **k: None, sh=fake_sh)
    monkeypatch.setitem(B.make_ltx.__globals__, "Path", orig)
    rows = {r["shot"]: r for r in res["shots"]}
    assert rows["dialogue"]["rc"] == 0 and rows["dialogue"]["sha256"]
    assert rows["action"]["rc"] == 1 and "sha256" not in rows["action"]


def test_metrics_find_motion_frozen_runs_and_start_faithfulness():
    start = np.full((18, 32, 3), 100.0, dtype=np.float32)
    frames = [start + i * 2 for i in range(10)] + [start + 18] * 6
    m = R.metrics(frames, start)
    assert m["frames"] == 16 and m["start_diff"] == 0.0
    assert m["longest_still"] == 7 and m["motion"] > 0
    assert m["drift"] > 0
    assert R.metrics([]) == {"frames": 0}


def test_costs_split_the_containers_seconds_over_its_shots():
    measured = {"wan_ti2v_5b": {"state": "DONE", "body_s": 600.0,
                                "shots": [{"shot": "dialogue", "gen_s": 200}, {"shot": "action", "gen_s": 200}]}}
    c = R.costs(PLAN, measured)["wan_ti2v_5b"]
    v = B.variant(PLAN, "wan_ti2v_5b")
    want = (600 + PLAN["cold_start_s"]) * B.usd_per_h(v["gpu"], v["cpu"], v["memory_gib"]) / 3600
    assert abs(c["usd"] - want) < 1e-3
    assert abs(c["per_shot_usd"]["dialogue"] - want / 2) < 1e-3


def _clip(path, frames=24, size=(320, 176), fps=16, audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size[0]}x{size[1]}:rate={fps}:duration={frames / fps}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={frames / fps}", "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_report_upscales_measures_and_prices_every_clip(tmp_path):
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
            files[f"{base}/{s['id']}.mp4"] = _clip(src / f"{v['id']}_{s['id']}.mp4", audio=v["family"] == "ltx")
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
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", r["file_2k"]], capture_output=True, text=True).stdout.strip()
        assert p == "2560,1440"
        assert r["usd"] > 0 and r["motion"] > 0
    assert any(r["sound"] for r in made) and not all(r["sound"] for r in made)
    assert R.has_audio(Path([r for r in made if r["sound"]][0]["file_2k"]))
    assert "wan_ti2v_5b" not in rep["money"]                     # not run: no row, no price
    assert (tmp_path / "out" / "report.md").read_text().count("| made") == 0
    assert "contact_sheet.png" in " ".join(up)
