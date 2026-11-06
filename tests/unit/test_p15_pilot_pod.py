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
