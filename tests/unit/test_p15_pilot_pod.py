"""The pilot pod (PILOT_1MIN_PLAN.md v3; the creator 2026-11-06 15:25 / 16:05 UTC; Fable 15:52 UTC): the config from the stills
manifest (8 restyles, 2 clips of 185 frames, prompts from the shot cards, every input pinned), the schedule under RP-11, the runner's
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


def test_the_config_restyles_every_room_still_and_the_battle_frame_0_and_animates_two_185_frame_clips():
    cfg = B.config(manifest())
    assert [j["shot"] for j in cfg["qwen_jobs"]] == list(B.RESTYLE)
    assert "battle_f200_colour" not in {j["shot"] for j in cfg["qwen_jobs"]}   # no clip starts there, so it is not restyled
    for j in cfg["qwen_jobs"]:
        assert j["qwen_prompt"] == PS.prompts(j["shot"])["qwen"] and len(j["still"]["sha256"]) == 64
        assert j["still"]["path"].startswith("route_test_2026-11/pilot/blender/")
    refs = {r["name"]: r for r in cfg["heroes_refs"]}
    assert all(len(refs[h]["sha256"]) == 64 for j in cfg["qwen_jobs"] for h in j["hero_refs"])
    assert [j["shot_id"] for j in cfg["ltx_jobs"]] == ["room_two_shot", "battle_f000_colour"]
    for j in cfg["ltx_jobs"]:
        assert j["frames"] == 185 and (j["frames"] - 1) % 8 == 0 and j["frames"] / j["fps"] <= 8.0   # LTX 8k+1, BP-172
        assert j["pipeline"] == "distilled" and j["lora"] is None and j["model"]["sha256"] and j["seed"] == 42
        assert j["first_frame"]["path"] == f"route_test_2026-11/pilot/first_frames/{j['shot_id']}.png"
        assert j["prompt"] == PS.prompts(j["shot_id"])["ltx"]
    assert cfg["ltx"]["upscale"]["enabled"] is False and list(cfg["ltx"]["weights"]) == ["ltx25"]
    assert cfg["qwen"]["style_lora"]["weight"] == 0.7 and cfg["qwen"]["style_lora"]["path"].endswith("xworld_v2_000003000.safetensors")


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
    assert names.index("weights_qwen") < names.index("qwen_restyle") < names.index("ltx_room")
    assert names.index("weights_ltx25") < names.index("ltx_room") and "ltx_battle" not in names
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["ltx_battle"]["status"] == "skipped" and "first frame" in rows["ltx_battle"]["reason"]
    assert rows["F"]["status"] == "ok" and (tmp_path / "speeds.json").is_file()
    t = dict(run.calls)
    assert t["ltx_room"] == 17.5 * 60 and t["qwen_restyle"] == 17.5 * 60   # every timeout is the schedule's max


def test_two_ltx_failures_stop_the_stage_and_nothing_starts_in_the_end_reserve(tmp_path):
    cfg = B.config(manifest())
    cfg["max_ltx_failures"] = 1
    sch = RP.load(DIR / "p15_schedule.json")
    run = FakeRun(tmp_path, fail={"ltx_room"})
    (tmp_path / "first_frames").mkdir()
    (tmp_path / "first_frames" / "battle_f000_colour.png").write_bytes(b"x")
    pod = p15_pod.Pod(cfg, sch, tmp_path, deadline=__import__("time").time() + 7200, run=run)
    assert pod.main() == 1
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["ltx_room"]["status"] == "failed" and "failures" in rows["ltx_battle"]["reason"]
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
