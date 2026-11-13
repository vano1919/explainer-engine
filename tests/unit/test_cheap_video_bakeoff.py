"""The cheaper-video test (the creator, 2026-11-12 22:21 UTC: "$3 on Modal" for the open models that run there, against LTX,
on the battle pictures): the bake-off worker reads a second plan named by EE_BAKEOFF_PLAN, makes several sizes in one container,
a subset of shots per variant, and HunyuanVideo 1.5 image-to-video with the deadline inside the denoising; the plan stays under
the creator's line; the session hook binds the GO to the named plan. No Modal, GPU or HF call: the container steps are faked
(the real-library CPU rehearsal is v4_3_plan_2026-11-12/cheap_video/rehearsal/hunyuan_cpu_rehearsal.py)."""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from explainer_engine.cloud import hooks as H
from explainer_engine.training.pods.bakeoff import modal_bakeoff as B

NAME = "plan_cheap_2026-11-12.json"
PLAN = B.load_plan(B.plan_path({"EE_BAKEOFF_PLAN": NAME}))
LINE = {"per_run_usd": 1.2, "tests_total_usd": 3.0}


def test_the_plan_is_named_by_file_name_only_in_the_bakeoff_folder():
    assert B.plan_path({}).name == "plan_v43.json"
    assert B.plan_path({"EE_BAKEOFF_PLAN": NAME}) == Path(B.__file__).with_name(NAME)
    assert B.plan_path({"EE_BAKEOFF_PLAN": "../../../etc/" + NAME}).parent == Path(B.__file__).parent


def test_the_cheap_plan_holds_under_the_creators_three_dollars():
    assert B.plan_problems(PLAN) == []
    B.preflight(PLAN, line=LINE)
    assert PLAN["asked_by"]["message_id"] == "cmsg_01Hnu5zB86sjUj5GtTgaUkPWBzaDXEQGLrQnKpeqMBwkj9"
    assert PLAN["spend_line"] == "modal_cheap_video" and PLAN["total_cap_usd"] == 3.0
    caps = sum(v["cap_usd"] for v in PLAN["variants"]) + PLAN["stage"]["cap_usd"]
    assert caps <= 3.0
    for v in PLAN["variants"]:
        assert (PLAN["cold_start_s"] + B.timeout_of(PLAN, v)) * B.rate_of(v) / 3600 <= v["cap_usd"]
    with pytest.raises(SystemExit, match="above the creator"):
        B.preflight(PLAN, line={"per_run_usd": 0.5, "tests_total_usd": 3.0})
    with pytest.raises(SystemExit, match="tests_total_usd"):
        B.preflight(PLAN, line={"per_run_usd": 1.2, "tests_total_usd": 2.0})


def test_the_spend_line_is_one_of_the_creators_modal_test_lines():
    from explainer_engine.core import spend_caps
    bad = json.loads(json.dumps(PLAN))
    bad["spend_line"] = "modal"
    assert any("spend_line" in b for b in B.plan_problems(bad))
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.modal_test_line("runpod")
    line = spend_caps.modal_test_line("modal_cheap_video")
    assert line["tests_total_usd"] == 3.0 and "cmsg_01Hnu5zB86sjUj5GtTgaUkPWBzaDXEQGLrQnKpeqMBwkj9" in line["decided"]


def test_ltx_makes_every_size_of_every_shot_with_the_battle_runs_prompt_and_seed():
    v = B.variant(PLAN, "ltx_low")
    jobs = B.jobs_of(PLAN, v)
    assert [j["tag"] for j in jobs] == ["b4_1024x576", "b3_1024x576", "b4_768x448", "b3_768x448"]
    scene = json.loads((Path(B.__file__).parents[1] / "ltx" / "scenes" / "battle_2026-11-12.json").read_text())
    by_pic = {s["picture"]: s for s in scene["shots"]}
    for j in jobs:
        cmd = B.ltx_cmd(PLAN, v, j["shot"], "/tmp/p.png", "/o/x.mp4", size=(j["width"], j["height"]))
        assert cmd[cmd.index("--width") + 1] == str(j["width"]) and cmd[cmd.index("--height") + 1] == str(j["height"])
        assert cmd[cmd.index("--prompt") + 1] == by_pic[j["shot"]["id"]]["motion_prompt"]
        assert j["shot"]["seed"] == by_pic[j["shot"]["id"]]["seed"]


def test_make_ltx_writes_one_file_per_size_and_shot(tmp_path):
    from PIL import Image
    pic = tmp_path / "p.png"
    Image.new("RGB", (2752, 1536)).save(pic)
    seen = []

    def sh(cmd, **kw):
        seen.append(cmd[cmd.index("--output-path") + 1])
        Path(seen[-1]).write_bytes(b"mp4")
        return SimpleNamespace(returncode=0)
    v = B.variant(PLAN, "ltx_low")
    rows = B.make_ltx(PLAN, v, tmp_path, {"b4": pic, "b3": pic}, B.Deadline(900, margin_s=0), {}, beat_fn=lambda *a, **k: None,
                      sh=sh, tmp=str(tmp_path / "in"))
    assert [r["state"] for r in rows] == ["DONE"] * 4
    assert [Path(p).name for p in seen] == ["b4_1024x576.mp4", "b3_1024x576.mp4", "b4_768x448.mp4", "b3_768x448.mp4"]
    assert B.run_state(rows, len(B.jobs_of(PLAN, v)), {}) == "DONE"
    assert Image.open(tmp_path / "in" / "b4_768x448.png").size == (768, 448)


def test_the_hunyuan_variant_is_one_clip_per_shot_at_its_bucket():
    v = B.variant(PLAN, "hunyuan15_480p_distilled")
    assert [j["tag"] for j in B.jobs_of(PLAN, v)] == ["b4", "b3", "b2"]
    assert B.sizes_of(v) == [[848, 480]] and v["frames"] == 121 and v["settings"]["num_inference_steps"] == 12
    assert 4.9 <= B.shot_seconds(v) <= 5.1
    w = PLAN["weights"][v["weights"][0]]
    assert all(B.H.match(h) for h in w["files"].values()) and "South Korea" in w["license"]
    bad = json.loads(json.dumps(PLAN))
    bad["variants"][1]["clips"] = 2
    assert any("one clip per shot" in b for b in B.plan_problems(bad))
    bad = json.loads(json.dumps(PLAN))
    bad["variants"][1]["shots"] = ["b9"]
    assert any("not the plan's shots" in b for b in B.plan_problems(bad))


def test_the_guarded_forward_raises_the_deadline_between_steps():
    class Mod:
        n = 0

        def forward(self, x):
            Mod.n += 1
            return x
    m = B.guard_forward(Mod(), B.Deadline(100, margin_s=0))
    assert m.forward(3) == 3 and Mod.n == 1
    late = B.Deadline(100, margin_s=0)
    late.end = 0
    B.guard_forward(m, late)
    with pytest.raises(B.DeadlineHit):
        m.forward(4)


class FakeHyPipe:
    calls = []

    def __init__(self):
        self.vae = SimpleNamespace(enable_tiling=lambda: FakeHyPipe.calls.append("tiling"))
        self.transformer = SimpleNamespace(forward=lambda *a, **k: None)

    @classmethod
    def from_pretrained(cls, path, **kw):
        FakeHyPipe.calls.append(("load", path))
        return cls()

    def to(self, d):
        return self

    def __call__(self, image, prompt, num_frames, output_type, generator, num_inference_steps):
        self.transformer.forward()
        FakeHyPipe.calls.append(("call", image.size, num_frames, num_inference_steps))
        w, h = image.size
        return SimpleNamespace(frames=[np.zeros((num_frames, h, w, 3), np.float32)])


def test_make_hunyuan_loads_once_writes_each_clip_and_stops_before_one_that_cannot_finish(tmp_path, monkeypatch):
    from PIL import Image
    pic = tmp_path / "p.png"
    Image.new("RGB", (2752, 1536)).save(pic)
    d = SimpleNamespace(HunyuanVideo15ImageToVideoPipeline=FakeHyPipe)
    t = SimpleNamespace(bfloat16=None, Generator=lambda dev=None: SimpleNamespace(manual_seed=lambda s: None))
    monkeypatch.setattr(B, "write_clip", lambda frames, path, fps: (Path(path).write_bytes(b"x" * len(frames)), path)[1])
    FakeHyPipe.calls = []
    v = B.variant(PLAN, "hunyuan15_480p_distilled")
    pics = {s: pic for s in ("b4", "b3", "b2")}
    rows = B.make_hunyuan(PLAN, v, tmp_path, pics, B.Deadline(900, margin_s=0), {}, beat_fn=lambda *a, **k: None,
                          diffusers=d, torch=t)
    assert [r["state"] for r in rows] == ["DONE"] * 3 and sum(1 for c in FakeHyPipe.calls if c[0] == "load") == 1
    assert ("call", (848, 480), 121, 12) in FakeHyPipe.calls and "tiling" in FakeHyPipe.calls
    assert all((tmp_path / f"{s}.mp4").is_file() and (tmp_path / f"{s}.measured.json").is_file() for s in pics)
    assert rows[0]["width"] == 848 and rows[0]["height"] == 480 and "note" not in rows[0]
    class Short(B.Deadline):
        asked = 0

        def fits(self, seconds):
            Short.asked += 1
            return Short.asked < 3                     # the third clip would not finish in the time left
    (tmp_path / "x").mkdir()
    rows = B.make_hunyuan(PLAN, v, tmp_path / "x", pics, Short(900, margin_s=0), {}, beat_fn=lambda *a, **k: None,
                          diffusers=d, torch=t)
    assert [r.get("state") for r in rows] == ["DONE", "DONE", "PARTIAL"]
    assert rows[-1]["state"] == "PARTIAL" and "would not finish" in rows[-1]["why"]


def test_the_hook_binds_the_go_to_the_plan_the_command_names():
    worker = "explainer_engine/training/pods/bakeoff/modal_bakeoff.py"
    want = H.bakeoff_go_sha(plan_name=NAME)
    assert want == B.go_sha(B.plan_sha(B.plan_path({"EE_BAKEOFF_PLAN": NAME})))
    assert want != H.bakeoff_go_sha()
    ok = f"EE_BAKEOFF_PLAN={NAME} EE_MODAL_GO=cmsg_x:{want[:12]} modal run {worker}::stage"
    assert H.modal_refusal(ok, env={}) is None
    other = f"EE_MODAL_GO=cmsg_x:{want[:12]} modal run {worker}::stage"   # the GO of the cheap plan, the default plan on disk
    assert "another plan" in H.modal_refusal(other, env={})


def test_stage_does_not_hash_a_set_whose_stamp_already_holds(tmp_path):
    w = {"repo": "o/r", "revision": "a" * 40, "files": {"a.bin": hashlib.sha256(b"a").hexdigest()}}
    root = tmp_path / "model" / "o/r"
    root.mkdir(parents=True)
    (root / "a.bin").write_bytes(b"a")
    assert B.stage_weights({"weights": {"w": w}}, str(tmp_path)) == []
    hashed = []
    real = B.check_weights
    B_check = lambda w_, vol_root="/w": hashed.append(w_["repo"]) or real(w_, vol_root)  # noqa: E731
    import unittest.mock as um
    with um.patch.object(B, "check_weights", B_check):
        assert B.stage_weights({"weights": {"w": w}}, str(tmp_path)) == []
    assert hashed == []


def test_libs_are_plain_strings_a_client_without_torch_can_read():
    for v in B.libs().values():
        assert v is None or type(v) is str


def test_the_wan_plan_is_one_clip_under_the_same_line_and_ledger():
    wan = B.load_plan(B.plan_path({"EE_BAKEOFF_PLAN": "plan_cheap_wan_2026-11-12.json"}))
    assert B.plan_problems(wan) == []
    B.preflight(wan, line=LINE)
    assert wan["spend_line"] == PLAN["spend_line"] and wan["ledger"] == PLAN["ledger"]
    assert [j["tag"] for v in wan["variants"] for j in B.jobs_of(wan, v)] == ["b4"]
    assert H.bakeoff_go_sha(plan_name="plan_cheap_wan_2026-11-12.json") != H.bakeoff_go_sha(plan_name=NAME)
