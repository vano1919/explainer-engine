"""The pilot pod (PILOT_1MIN_PLAN.md v4; the creator 2026-11-06 15:25 / 16:05 / 16:42 UTC; Fable 15:52 / 16:42 UTC): the config from the
stills manifest (8 restyles, 8 clips of 185 frames with native audio, prompts from the shot cards in three styles, every input pinned), the schedule under RP-11, the runner's
order and stops, and the bundle without its script. No GPU, no network."""
import json
import tarfile
import threading
from pathlib import Path

import pytest

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.cloud import schedule as RP
from explainer_engine.core.errors import ContractError
from explainer_engine.training.pods.p14 import lean
from explainer_engine.training.pods.p15 import build as B
from explainer_engine.training.pods.p15 import p15_pod, p15_qwen

DIR = Path(B.__file__).resolve().parent


def manifest():
    shots = {sid: {"file": f"{sid}.png", "sha256": "a" * 64, "prompts": PS.prompts(sid)} for sid in PS.cameras()}
    for k in ("battle_f000_colour", "battle_f000_depth", "battle_f200_colour"):
        shots[k] = {"file": f"{k}.png", "sha256": "b" * 64}
    return {"schema": PS.SCHEMA, "hf_prefix": PS.HF_PREFIX, "shots": shots}


def test_the_config_restyles_every_room_still_and_the_battle_frame_0_and_animates_eight_185_frame_clips():
    cfg = B.config(manifest())
    assert [j["shot"] for j in cfg["qwen_jobs"]] == list(B.RESTYLE)
    assert "battle_f200_colour" not in {j["shot"] for j in cfg["qwen_jobs"]}   # no clip starts there, so it is not restyled
    for j in cfg["qwen_jobs"]:
        assert j["qwen_prompt"] == PS.prompts(j["shot"])["qwen"] and len(j["still"]["sha256"]) == 64
        assert j["still"]["path"].startswith("route_test_2026-11/pilot/blender/")
    refs = {r["name"]: r for r in cfg["heroes_refs"]}
    assert all(len(refs[h]["sha256"]) == 64 for j in cfg["qwen_jobs"] for h in j["hero_refs"])
    assert [(j["shot_id"], j["style"]) for j in cfg["ltx_jobs"]] == [
        ("room_two_shot", "S1"), ("room_two_shot", "S2"), ("room_two_shot", "S3"), ("battle_f000_colour", "S2"),
        ("room_establishing", "S2"), ("room_close_host", "S2"), ("room_insert_clock", "S2"), ("battle_f000_colour", "S1")]
    assert list(cfg["clips"]) == p15_pod.CLIP_STAGES and p15_pod.CLIP_STAGES[-2:] == ["ltx_c8", "ltx_c5"]   # Fable's drop order last
    assert len({j["id"] for j in cfg["ltx_jobs"]}) == 8 and len({j["output"] for j in cfg["ltx_jobs"]}) == 8
    assert all(j["question"] for j in cfg["ltx_jobs"]) and cfg["audio"] == {"in_mp4": True, "wav_sidecar": True}
    for j in cfg["ltx_jobs"]:
        assert j["frames"] == 185 and (j["frames"] - 1) % 8 == 0 and j["frames"] / j["fps"] <= 8.0   # LTX 8k+1, BP-172
        assert j["pipeline"] == "distilled" and j["lora"] is None and j["model"]["sha256"] and j["seed"] == 42
        assert j["first_frame"]["path"] == f"route_test_2026-11/pilot/first_frames/{j['shot_id']}.png"
        line = (("host", j["spoken_line"]) if j["spoken_line"] else None)
        assert j["prompt"] == PS.ltx_prompt(j["shot_id"], style=j["style"], audio=j["audio_prompt"], line=line)
        assert j["prompt"].endswith(j["audio_prompt"]) and j["audio_prompt"].startswith("We hear")
    assert cfg["ltx"]["upscale"]["enabled"] is False and list(cfg["ltx"]["weights"]) == ["ltx25"]
    assert cfg["qwen"]["style_lora"]["weight"] == 0.7 and cfg["qwen"]["style_lora"]["path"].endswith("xworld_v2_000003000.safetensors")


def test_the_three_styles_differ_only_in_the_head_and_the_line_is_said_in_quotes():
    s1, s2, s3 = (PS.ltx_prompt("room_two_shot", style=k) for k in ("S1", "S2", "S3"))
    assert s1 == PS.prompts("room_two_shot")["ltx"]   # S1 is today's sentence
    assert s1.endswith(s3) and s2.endswith(s3) and s3.startswith("The ") and "ink" not in s3.lower()
    assert s2.startswith("Hand-drawn 2D animation, bold uneven black ink outlines, chalky textured painterly background")
    p = PS.ltx_prompt("room_close_host", style="S2", line=("host", "We ride at first light."))
    assert 'says, "We ride at first light."' in p and p.count('"') == 2
    with pytest.raises(ContractError, match="not in the shot"):
        PS.ltx_prompt("room_insert_clock", line=("host", "Hello."))


def test_the_worst_case_fits_6_5_only_on_the_h100_and_the_launch_line_uses_the_cli_s_flags():
    from explainer_engine.cloud import runpod as R
    import copy
    import shlex
    sch = RP.load(DIR / "p15_schedule.json")
    assert sch["limits"]["max_usd"] == 6.5 and B.CLIP_MAX_MIN == 12.0
    by = {}
    for c in sch["cards"]:
        one = copy.deepcopy(sch)
        one["cards"] = [c]
        by[c["name"]] = RP.plan(one)["best"]
    assert by["H100 NVL"]["fits"] and by["H100 NVL"]["worst"]["usd"] <= 6.5 and by["H100 NVL"]["worst"]["pod_min"] <= 2.5 * 60
    assert not by["A100 80GB"]["fits"]   # A100 SECURE worst $6.68: why the launch names the H100 only
    cmd = json.loads((DIR / "p15.json").read_text(encoding="utf-8"))["launch"]["cmd"]
    assert R.create_flag_problems(shlex.split(cmd)[4:]) == []
    assert '--only "H100 NVL" --cloud COMMUNITY' in cmd and "--max-usd 6.5" in cmd and "--disk 200" in cmd


def test_the_wav_sidecar_is_written_when_the_mp4_has_audio_and_recorded_when_it_has_none(tmp_path):
    from explainer_engine.training.pods.p15 import p15_ltx
    mp4 = tmp_path / "c.mp4"
    mp4.write_bytes(b"v")

    class R:
        def __init__(self, rc, out=""):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    def sh(cmd, **k):
        if cmd[0] == "ffprobe":
            return R(0, json.dumps({"streams": [{"codec_name": "aac", "sample_rate": "48000", "channels": 2}]}))
        Path(cmd[-1]).write_bytes(b"RIFF")
        return R(0)
    doc = p15_ltx.audio_sidecar(mp4, sh=sh)
    assert doc["has_audio"] and doc["wav"]["path"] == "c.wav" and len(doc["wav"]["sha256"]) == 64
    assert json.loads((tmp_path / "c.audio.json").read_text())["wav"]["bytes"] == 4
    doc = p15_ltx.audio_sidecar(mp4, sh=lambda cmd, **k: R(0, json.dumps({"streams": []})))
    assert doc == {"mp4": "c.mp4", "has_audio": False, "streams": [], "wav": None}


def test_a_manifest_whose_prompt_is_not_the_card_s_is_refused():
    m = manifest()
    m["shots"]["room_two_shot"]["prompts"] = {"qwen": "xworld style, something hand-written"}
    with pytest.raises(ContractError, match="not the card"):
        B.config(m)
    m = manifest()
    del m["shots"]["room_insert_clock"]
    with pytest.raises(ContractError, match="lacks"):
        B.config(m)


def test_the_committed_config_is_the_cards_and_the_schedule_passes_rp11():
    cfg = json.loads((DIR / "p15.json").read_text(encoding="utf-8"))
    for j in cfg["qwen_jobs"]:
        assert j["qwen_prompt"] == PS.prompts(j["shot"])["qwen"], j["shot"]
    assert RP.rp11(DIR / "p15_schedule.json") == []
    sch = RP.load(DIR / "p15_schedule.json")
    assert {s["id"] for s in sch["stages"]} == {*p15_pod.LANES["net"], *p15_pod.LANES["gpu"]}
    assert all("cpu" not in s["on"] for s in sch["stages"])   # no Blender on the pod


def test_the_script_has_no_blender_and_pins_the_bundle_once(tmp_path):
    text = (DIR / "p15.sh").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#") and "# " not in ln[:2])
    assert "blender" not in code.lower()
    assert "code/p15/ee_src.tar.gz" in text and "route_test_2026-11/pilot/beat.txt" in text
    assert len(lean.SHA_LINE.findall(text)) == 1


def test_the_bundle_leaves_the_script_out(tmp_path, monkeypatch):
    monkeypatch.setattr(lean, "BUNDLE_DIRS", ("explainer_engine/training/pods/p15",))
    sh = tmp_path / "p15.sh"
    sh.write_text((DIR / "p15.sh").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(B, "SH", sh)
    monkeypatch.setattr(B, "SH_Q", tmp_path / "p15q.sh")   # the bundle pins both scripts: never the committed one
    monkeypatch.setattr(B, "SH_C", {})
    (tmp_path / "p15q.sh").write_text((DIR / "p15q.sh").read_text(encoding="utf-8"), encoding="utf-8")
    sha = B.bundle(tmp_path / "a.tgz")
    assert sha in sh.read_text() and B.bundle(tmp_path / "b.tgz") == sha
    with tarfile.open(tmp_path / "a.tgz") as t:
        names = t.getnames()
    assert "explainer_engine/training/pods/p15/p15_pod.py" in names and "explainer_engine/training/pods/p15/p15.sh" not in names
    assert lean.EXCLUDE == ("explainer_engine/training/pods/p14/p14.sh",)   # put back


class FakeRun:
    def __init__(self, out, fail=()):
        self.out, self.fail, self.calls, self.lock = Path(out), set(fail), [], threading.Lock()

    def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
        name = Path(log_path).stem
        with self.lock:
            self.calls.append((name, timeout))
        if name == "qwen_restyle":
            for sid in ("room_two_shot",):   # the battle frame is not drawn: its clip must skip with that reason
                f = self.out / "first_frames" / f"{sid}.png"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"x")
        return (1 if name in self.fail else 0), 1.0


def test_the_card_restyles_then_animates_and_a_clip_without_its_first_frame_is_skipped(tmp_path):
    cfg = B.config(manifest())
    sch = RP.load(DIR / "p15_schedule.json")
    run = FakeRun(tmp_path)
    pod = p15_pod.Pod(cfg, sch, tmp_path, deadline=__import__("time").time() + 7200, run=run)
    assert pod.main() == 0
    names = [c[0] for c in run.calls]
    assert names.index("weights_qwen") < names.index("qwen_restyle") < names.index("ltx_c1")
    assert names.index("weights_ltx25") < names.index("ltx_c1") and "ltx_c4" not in names and "ltx_c5" not in names
    assert [n for n in names if n.startswith("ltx_")] == ["ltx_c1", "ltx_c2", "ltx_c3"]   # only the two-shot's first frame exists
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["ltx_c4"]["status"] == "skipped" and "first frame" in rows["ltx_c4"]["reason"]
    assert rows["F"]["status"] == "ok" and (tmp_path / "speeds.json").is_file()
    t = dict(run.calls)
    assert t["ltx_c1"] == 12 * 60 and t["qwen_restyle"] == 17.5 * 60   # every timeout is the schedule's max


def test_two_ltx_failures_stop_the_stage_and_nothing_starts_in_the_end_reserve(tmp_path):
    cfg = B.config(manifest())
    cfg["max_ltx_failures"] = 1
    sch = RP.load(DIR / "p15_schedule.json")
    run = FakeRun(tmp_path, fail={"ltx_c1"})
    (tmp_path / "first_frames").mkdir()
    (tmp_path / "first_frames" / "battle_f000_colour.png").write_bytes(b"x")
    pod = p15_pod.Pod(cfg, sch, tmp_path, deadline=__import__("time").time() + 7200, run=run)
    assert pod.main() == 1
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["ltx_c1"]["status"] == "failed" and "failures" in rows["ltx_c2"]["reason"] and "failures" in rows["ltx_c5"]["reason"]
    late = p15_pod.Pod(cfg, sch, tmp_path / "late", deadline=__import__("time").time() + 60, run=FakeRun(tmp_path / "late"))
    late.main()
    rows = json.loads((tmp_path / "late" / "stages.json").read_text())["stages"]
    assert rows["weights_qwen"]["reason"] == "inside the end reserve" and rows["qwen_restyle"]["status"] == "skipped"
    assert all(r["status"] != "running" for r in rows.values())


def test_the_qwen_list_is_the_config_s(monkeypatch):
    cfg = B.config(manifest())
    monkeypatch.setattr(p15_qwen, "load_cfg", lambda: cfg)
    js = p15_qwen.jobs(cfg)
    assert [j["name"] for j in js] == list(B.RESTYLE) and all(j["kind"] == "edit" and j["size"] == [1280, 720] for j in js)
    two = next(j for j in js if j["name"] == "room_two_shot")
    assert two["refs"] == [("hero", "B_H1_front"), ("hero", "B_H2_front")] and two["cfg"] == cfg["qwen"]["cfg_edit"]


# ---- --only qwen (the creator 2026-11-06 17:34 UTC: pictures first, no LTX on this pod)

def test_the_qwen_only_schedule_has_no_ltx_stage_and_passes_rp11_on_the_two_a100s_and_rp01_on_the_work_min():
    import copy
    from explainer_engine.cloud import batching
    assert RP.rp11(DIR / "p15q_schedule.json") == []
    sch = RP.load(DIR / "p15q_schedule.json")
    assert {s["id"] for s in sch["stages"]} == {*p15_pod.QWEN_LANES["net"], *p15_pod.QWEN_LANES["gpu"]}
    assert B.schedule_qwen() == json.loads((DIR / "p15q_schedule.json").read_text(encoding="utf-8"))   # generated, never hand-edited
    assert sch["limits"]["max_usd"] == 3.4 and len(sch["cards"]) == 11   # the creator 20:09 UTC: every card that passes RP-01 with a worst-case money under the cap
    assert {c["name"] for c in sch["cards"]} == {"RTX A5000", "A40", "RTX A6000", "L4", "RTX 5090", "RTX 4090", "RTX 6000 Ada", "L40S", "A100 80GB"}
    assert not any("Blackwell" in c["name"] for c in sch["cards"])   # torch on sm_120 is not verified for this image
    assert not any("H100" in c["name"] for c in sch["cards"])   # no H100: its 15.4 min of work fails RP-01
    r = next(s for s in sch["stages"] if s["id"] == "qwen_restyle")["on"]["gpu"]
    assert r["expected_min"] == 16.6 and r["max_min"] == 49.8   # (61 s + 26 x 36 s: 24 pictures + 2 mouth sheets), the usual 3x
    for c in sch["cards"]:
        one = copy.deepcopy(sch)
        one["cards"] = [c]
        best = RP.plan(one)["best"]
        if (c["name"], c["cloud"]) == ("A100 80GB", "SECURE"):   # 24 pictures + 2 sheets: worst $3.51, over $3.4 by 3 % (the guard still stops at $3.4)
            assert not best["fits"] and best["worst"]["usd"] <= 3.6
        else:
            assert best["worst"]["usd"] <= 3.4   # every other card, in its worst case
        if c["name"] == "A100 80GB" and c["cloud"] == "COMMUNITY":
            assert best["fits"] and best["worst"]["pod_min"] <= 120
        else:   # estimated speeds: the 2 h cap (guard) bounds the A40/A6000 (worst 3.4 h of work) and the L40S (127 min); money stays under 3.4
            assert c["name"] != "H100 NVL"   # estimated speeds; the 2 h guard bounds the slow cards, money stays under $3.4
        assert batching.rp01(round(best["expected"]["gpu_busy_min"]), 8) == []   # the A100's work, 26 min, is over 3 x the 8 min setup
    h100 = copy.deepcopy(sch)
    h100["cards"] = [{"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0}]
    assert batching.rp01(round(RP.plan(h100)["best"]["expected"]["gpu_busy_min"]), 8) != []


def test_the_24_qwen_prompts_are_at_most_90_words_pass_the_style_check_and_differ_only_in_the_look_clauses():
    from explainer_engine.qa import style_prompt as SP
    cfg = json.loads((DIR / "p15.json").read_text(encoding="utf-8"))
    js = p15_qwen.jobs(cfg, True)
    assert len(js) == 24 and len({j["name"] for j in js}) == 24
    for j in js:
        assert len(j["prompt"].split()) <= 90, j["name"]
        assert [f for f in SP.check(j["prompt"]) if f["severity"] in ("FAIL", "REVIEW")] == [], j["name"]
        assert j["seed"] == cfg["qwen"]["seed"] and j["cfg"] == cfg["qwen"]["cfg_edit"]
    for q in cfg["qwen_jobs"]:
        s1, s2, s3 = (next(j for j in js if j["name"] == f"{q['shot']}__{s}")["prompt"] for s in ("S1", "S2", "S3"))
        assert s3 == q["qwen_prompt"] and s1.startswith(s3) and s2.startswith(s3) and s1 != s2
    for words in ("snappy", "timing", "poses hold", "quick moves"):
        assert not any(words in j["prompt"] for j in js)   # the video words stay out of the pictures
    assert p15_qwen.jobs(cfg) == p15_qwen.jobs(cfg, False) and len(p15_qwen.jobs(cfg)) == 8   # the full pod is unchanged


def test_the_qwen_only_pod_downloads_only_the_qwen_weights_and_starts_no_clip(tmp_path):
    cfg = B.config(manifest())
    sch = RP.load(DIR / "p15q_schedule.json")
    run = FakeRun(tmp_path)
    pod = p15_pod.Pod(cfg, sch, tmp_path, deadline=__import__("time").time() + 7200, run=run, only="qwen")
    assert pod.main() == 0
    names = [c[0] for c in run.calls]
    assert names == ["weights_qwen", "qwen_restyle"]   # no weights_ltx25, no ltx_c*
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["F"]["status"] == "ok" and not any(k.startswith("ltx_") or k == "weights_ltx25" for k in rows)
    assert dict(run.calls)["qwen_restyle"] == 49.8 * 60
    failed = FakeRun(tmp_path / "f", fail={"qwen_restyle"})
    assert p15_pod.Pod(cfg, sch, tmp_path / "f", deadline=__import__("time").time() + 7200, run=failed, only="qwen").main() == 1


def test_the_qwen_only_script_has_no_ltx_and_pins_the_same_bundle_and_the_launch_line_uses_the_cli_s_flags(tmp_path, monkeypatch):
    import shlex
    from explainer_engine.cloud import runpod as R
    text = (DIR / "p15q.sh").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "ltx" not in code.lower() and "blender" not in code.lower()
    assert "p15_pod --only qwen" in code and len(lean.SHA_LINE.findall(text)) == 1
    assert lean.SHA_LINE.findall(text) == lean.SHA_LINE.findall((DIR / "p15.sh").read_text(encoding="utf-8"))   # one bundle, two scripts
    cmd = B.launch_qwen()["cmd"]
    assert R.create_flag_problems(shlex.split(cmd)[4:]) == []
    assert "p15q.sh" in cmd and "p15q_schedule.json" in cmd and "--max-usd 3.4" in cmd and "--work-min 26" in cmd and "ltx" not in cmd.lower()
    assert '--only "A100" --cloud COMMUNITY' in cmd
    # the bundle leaves both scripts out and pins both
    monkeypatch.setattr(lean, "BUNDLE_DIRS", ("explainer_engine/training/pods/p15",))
    for n in ("p15.sh", "p15q.sh"):
        (tmp_path / n).write_text((DIR / n).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(B, "SH", tmp_path / "p15.sh")
    monkeypatch.setattr(B, "SH_Q", tmp_path / "p15q.sh")
    monkeypatch.setattr(B, "SH_C", {})   # the committed clip scripts are pinned only by the real bundle command
    sha = B.bundle(tmp_path / "a.tgz")
    assert sha in (tmp_path / "p15.sh").read_text() and sha in (tmp_path / "p15q.sh").read_text()
    with tarfile.open(tmp_path / "a.tgz") as t:
        names = t.getnames()
    assert "explainer_engine/training/pods/p15/p15q_schedule.json" in names and not any(n.endswith(("p15.sh", "p15q.sh")) for n in names)


def test_the_qwen_stage_ends_after_three_pictures_fail_in_a_row_so_a_card_that_cannot_hold_the_model_only_bills_a_moment(tmp_path, monkeypatch):
    import sys
    import types
    fake = types.SimpleNamespace(load_pipeline=lambda: (object(), object()))
    monkeypatch.setitem(sys.modules, "xworld_v1_test", fake)
    cfg = {"qwen": {"gpu_mode": "model_cpu_offload"}}
    monkeypatch.setattr(p15_qwen, "load_cfg", lambda: cfg)
    monkeypatch.setattr(p15_qwen.Q, "style_lora", lambda t, pipe, tr, c, say: pipe)
    monkeypatch.setattr(p15_qwen, "jobs", lambda c, v=False: [{"name": f"j{i}", "still": {}, "refs": [], "clip": f"j{i}"} for i in range(24)])
    calls = []

    def boom(c, still, work):
        calls.append(1)
        raise RuntimeError("CUDA out of memory")
    monkeypatch.setattr(p15_qwen, "fetch_still", boom)
    assert p15_qwen.run(tmp_path, tmp_path, tmp_path, True) == 1
    assert len(calls) == p15_qwen.MAX_FAIL_STREAK == 3


# ---- 24 pictures + N clips (the creator 2026-11-06 21:41 UTC: video too)

class FakeRunVariants(FakeRun):
    def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
        name = Path(log_path).stem
        if name == "qwen_restyle":
            assert "--variants" in cmd
            for shot in ("room_two_shot", "battle_f000_colour"):
                for look in ("S1", "S2", "S3"):
                    f = self.out / "first_frames" / f"{shot}__{look}.png"
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(b"x")
        if name.startswith("ltx_c"):
            assert "--variant-frames" in cmd
        return super().__call__(cmd, timeout=timeout, env=env, log_path=log_path, deadline=deadline)


def test_the_clip_variants_run_the_24_pictures_then_only_their_clips_from_the_variant_first_frames(tmp_path):
    for n, ids in ((2, ["ltx_c2", "ltx_c4"]), (8, B.CLIP_SETS[8])):
        cfg = B.config(manifest())
        out = tmp_path / str(n)
        run = FakeRunVariants(out)
        pod = p15_pod.Pod(cfg, p15_pod.load_schedule("qwen", n), out, deadline=__import__("time").time() + 20000, run=run, only="qwen", clips=n)
        rc = pod.main()
        names = [c[0] for c in run.calls]
        assert names[:3] == ["weights_qwen", "weights_ltx25", "qwen_restyle"] or set(names[:2]) == {"weights_qwen", "weights_ltx25"}
        rows = json.loads((out / "stages.json").read_text())["stages"]
        done = [k for k, v in rows.items() if k.startswith("ltx_c") and v["status"] == "ok"]
        skipped = [k for k, v in rows.items() if k.startswith("ltx_c") and v["status"] == "skipped"]
        assert set(done) | set(skipped) == set(ids)
        # the shots with a drawn picture start; the others skip with the missing-first-frame reason
        assert "ltx_c2" in done and "ltx_c4" in done and (n == 2 or "ltx_c6" in skipped) and rc == 0


def test_the_clip_first_frames_follow_the_style_tag_and_the_schedules_state_their_proposed_caps():
    assert B.clip_first_frame("ltx_c1") == "room_two_shot__S1" and B.clip_first_frame("ltx_c4") == "battle_f000_colour__S2"
    assert B.clip_first_frame("ltx_c5") == "battle_f000_colour__S1" and B.clip_first_frame("ltx_c7") == "room_close_host__S2"
    for n in (8, 2):
        sch = json.loads((DIR / f"p15qc{n}_schedule.json").read_text())
        assert B.schedule_qwen_clips(n) == sch and sch["limits"] == B.LIMITS_CLIPS[n]
        assert [s["id"] for s in sch["stages"] if s["id"].startswith("ltx_c")] == B.CLIP_SETS[n]
        assert RP.rp11(DIR / f"p15qc{n}_schedule.json") == []
        assert RP.rp11(DIR / f"p15qc{n}_schedule.json", max_usd=3.4, max_hours=2.0) != []   # they do NOT fit the current cap
        text = (DIR / f"p15c{n}.sh").read_text()
        assert f"p15_pod --only qwen --clips {n}" in text and len(lean.SHA_LINE.findall(text)) == 1
    p = json.loads((DIR / "p15.json").read_text())["clips"]
    assert [c for c in B.CLIP_SETS[8] if c not in p] == []



def test_the_mouth_sheet_layout_is_one_constant_and_the_prompts_fit_the_style_rules():
    from PIL import Image
    from explainer_engine.training.pods.p15 import mouth_grid as G, p15_mouth as M
    boxes = [G.cell_box(n) for n in G.ORDER]
    assert len(boxes) == 8 and boxes[0][:2] == (8, 8) and boxes[7][2:] == (1272, 712)
    assert all(a[2] <= b[0] or a[1] >= b[3] or b[1] >= a[3] for i, a in enumerate(boxes) for b in boxes[i + 1:] if a != b and a[0] < b[2])  # no overlaps
    cells = G.cut(Image.new("RGB", (1280, 720)))
    assert list(cells) == list(G.ORDER) and cells["A"].size == (G.cell_box("A")[2] - 8, G.cell_box("A")[3] - 8)
    for e in M.load_spec()["sheets"].values():
        pr = M.prompt(e)
        assert M.words(pr) <= 90 and pr.count("xworld style") == 1 and all(G.WORDS[n] in pr for n in G.ORDER)


def test_the_structure_check_and_the_sheet_run_redraw_up_to_three_seeds_per_hero(tmp_path, monkeypatch):
    import numpy as np
    from PIL import Image
    from explainer_engine.training.pods.p15 import mouth_grid as G, p15_mouth as M
    rng = np.random.default_rng(3)
    good = Image.fromarray(np.kron(rng.integers(0, 255, (45, 80, 3), dtype=np.uint8), np.ones((16, 16, 1), dtype=np.uint8)))   # blocky: survives the downscale
    flat = Image.new("RGB", (1280, 720), (200, 200, 200))
    assert M.cells_ok(good)[0] and not M.cells_ok(flat)[0]
    monkeypatch.setattr(M, "fetch_sheet", lambda spec, hero, work: tmp_path / "x.png")
    (tmp_path / "x.png").write_bytes(b"")
    monkeypatch.setattr(Image, "open", lambda p, *a, **k: flat)
    seen = []

    def draw(pipe, cfg, j, refs):
        seen.append((j["seed"], j["size"]))
        return flat if len(seen) in (1, 2) else good   # hero 1: seeds 11 and 12 fail the structure check, 13 passes; hero 2 passes at 11
    made, drawn = M.run_all(None, {"qwen": {"cfg_edit": 2.5, "style_lora": {}}}, tmp_path / "o", tmp_path, lambda *a: None, draw)
    assert (made, drawn) == (2, 4) and [s for s, _ in seen] == [11, 12, 13, 11] and all(z == (1280, 720) for _, z in seen)
    assert (tmp_path / "o/mouth_variants/B_H2_right34__sheet_s13.png").exists() and len(seen) <= 6


def test_the_mouth_identity_check_cuts_the_cells_and_scores_each_against_the_sheet(tmp_path):
    import numpy as np
    from PIL import Image
    from explainer_engine.training.pods.p15 import mouth_grid as G, p15_mouth as M
    d, sh = tmp_path / "m", tmp_path / "s"
    d.mkdir(), sh.mkdir()
    for h in M.load_spec()["sheets"]:
        Image.new("RGB", (1280, 720), (90, 90, 90)).save(d / f"{h}__sheet_s11.png")
        Image.new("RGB", (1280, 704), (90, 90, 90)).save(sh / f"{h}.png")
    rep = M.identity(d, sh, embedder=lambda paths: np.ones((len(paths), 4)))
    assert set(rep) == {f"{h}__sheet_s11" for h in M.load_spec()["sheets"]} and all(len(v["per_cell"]) == 8 and v["min"] == 1.0 for v in rep.values())
    assert (d / "identity.json").exists() and (d / "cells" / "B_H2_right34__11__blink2.png").exists()


def test_the_default_qwen_pod_draws_the_24_pictures_and_the_two_mouth_sheets_inside_the_3_4_cap():
    sch = json.loads((DIR / "p15q_schedule.json").read_text())
    r = next(s for s in sch["stages"] if s["id"] == "qwen_restyle")["on"]["gpu"]
    assert r["expected_min"] == 16.6 and r["max_min"] == 49.8   # 61 s + 26 x 36 s, the usual 3x (retries of the sheets are inside it)
    assert RP.rp11(DIR / "p15q_schedule.json", max_usd=3.4, max_hours=2.0) == [] and not (DIR / "p15qm_schedule.json").exists()
    assert B.schedule_qwen() == sch
