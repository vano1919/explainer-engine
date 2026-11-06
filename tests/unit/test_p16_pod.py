"""P1's pod (EXEC_QUEUE.md P1; the creator 2026-11-06 16:18 UTC): the rest of the 60 s minute after the p15 pod. The config from the
extra battle stills' manifest and p15's pins (8 clips of 8k+1 frames, 3 restyles), the schedule under RP-11, the runner's order and
stops, and the bundle without its script. No GPU, no network."""
import json
import tarfile
import threading
import time
from pathlib import Path

import pytest

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.cloud import schedule as RP
from explainer_engine.core.errors import ContractError
from explainer_engine.training.pods.p14 import lean
from explainer_engine.training.pods.p16 import build as B
from explainer_engine.training.pods.p16 import p16_pod

DIR = Path(B.__file__).resolve().parent
WIDE, MID = "battle_wide_high_f096_colour", "battle_front_mid_f100_colour"


def extra():
    shots = {sid: {"file": f"{sid}.png", "sha256": "c" * 64, "camera_name": cam, "prompts": PS.prompts(sid)}
             for sid, cam in ((WIDE, "wide_high"), (MID, "front_mid"))}
    return {"schema": PS.EXTRA_SCHEMA, "hf_prefix": PS.HF_PREFIX, "shots": shots}


def stills():
    return {"schema": PS.SCHEMA, "hf_prefix": PS.HF_PREFIX,
            "shots": {"battle_f200_colour": {"file": "battle_f200_colour.png", "sha256": "d" * 64}}}


def test_the_config_restyles_the_three_new_battle_stills_and_animates_eight_clips_of_8k_plus_1_frames():
    cfg = B.config(extra(), stills())
    assert [j["shot"] for j in cfg["qwen_jobs"]] == ["battle_f200_colour", WIDE, MID]
    for j in cfg["qwen_jobs"]:
        assert j["qwen_prompt"] == PS.prompts(j["shot"])["qwen"] and j["hero_refs"] == [] and len(j["still"]["sha256"]) == 64
        assert j["still"]["path"].startswith("route_test_2026-11/pilot/blender/")
    assert len(cfg["ltx_jobs"]) == 8 and set(cfg["clips"]) == set(p16_pod.ROOM_CLIPS) | set(p16_pod.BATTLE_CLIPS)
    for j in cfg["ltx_jobs"]:
        assert (j["frames"] - 1) % 8 == 0 and j["frames"] / j["fps"] <= 8.0 and j["frames"] >= 97   # LTX 8k+1, BP-172
        assert j["pipeline"] == "distilled" and j["lora"] is None and j["model"]["sha256"] and j["seed"] == 42
        assert j["prompt"] == PS.prompts(j["shot_id"])["ltx"] and j["output"].startswith("route_test_2026-11/pilot/p16/ltx/")
    by = {c["first_frame_of"]: c for c in cfg["clips"].values()}
    ff = {j["shot_id"]: j["first_frame"]["path"] for j in cfg["ltx_jobs"]}
    for room in ("room_establishing", "room_close_host", "room_close_guest", "room_reverse", "room_insert_table"):
        assert by[room]["from"] == "p15" and ff[room] == f"route_test_2026-11/pilot/first_frames/{room}.png"   # reused, not re-paid
    for shot in ("battle_f200_colour", WIDE, MID):
        assert by[shot]["from"] == "qwen_restyle" and ff[shot] == f"route_test_2026-11/pilot/p16/first_frames/{shot}.png"
    assert "room_two_shot" not in ff and "battle_f000_colour" not in ff     # p15 already animated these two
    assert sum(c["frames"] for c in cfg["clips"].values()) == 1088
    assert cfg["hf_root"] == "route_test_2026-11/pilot/p16"


def test_p15_s_measured_first_frames_are_pinned_into_the_room_clips(tmp_path):
    q = tmp_path / "qwen"
    q.mkdir()
    rows = [{"name": s, "status": "ok", "first_frame": {"sha256": s[:1] * 64}} for s in ("room_establishing", "room_reverse")]
    (q / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    cfg = B.config(extra(), stills(), tmp_path)
    ff = {j["shot_id"]: j["first_frame"]["sha256"] for j in cfg["ltx_jobs"]}
    assert ff["room_establishing"] == "r" * 64 and ff["room_reverse"] == "r" * 64 and ff["room_close_host"] is None


def test_a_missing_camera_or_a_prompt_that_is_not_the_card_s_is_refused():
    e = extra()
    del e["shots"][WIDE]
    with pytest.raises(ContractError, match="wide_high"):
        B.config(e, stills())
    e = extra()
    e["shots"][MID]["prompts"] = {"qwen": "xworld style, hand-written"}
    with pytest.raises(ContractError, match="not the card"):
        B.config(e, stills())
    with pytest.raises(ContractError, match="need a"):
        B.config({"schema": "x"}, stills())


def test_the_schedule_passes_rp11_once_the_ltx_speed_is_measured_and_the_committed_order_costs_the_cheapest():
    spec = B.schedule(ltx_s_per_frame=1.6, on="A100 80GB")
    assert RP.validate(spec) == []
    res = RP.plan(spec)
    own = RP.committed(spec, res["best"]["card"], p16_pod.LANES["gpu"])
    assert RP.check(spec, res, own) == []
    assert {s["id"] for s in spec["stages"]} == {*p16_pod.LANES["net"], *p16_pod.LANES["gpu"]}
    assert all("cpu" not in s["on"] for s in spec["stages"])   # no Blender on the pod
    assert res["best"]["card"] == "A100 80GB" and res["best"]["expected"]["gpu_idle_min"] == 0
    clips = [s for s in spec["stages"] if s["id"] in B.CLIPS]
    assert all(s["measured"] for s in clips)
    battle = [s for s in clips if "battle" in s["id"]]
    assert all("qwen_restyle" in s["needs"] for s in battle) and not any("qwen_restyle" in s["needs"] for s in clips if s not in battle)
    est = B.schedule()   # unmeasured: the worst case is 3 x, so the pod is not allowed to start on an estimate
    assert not all(s["measured"] for s in est["stages"] if s["id"] in B.CLIPS) and RP.check(est)


def test_the_script_has_no_blender_and_pins_the_bundle_once():
    text = (DIR / "p16.sh").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "blender" not in code.lower() and "p15" not in code
    assert "code/p16/ee_src.tar.gz" in text and "route_test_2026-11/pilot/p16/beat.txt" in text and "pods.p16.p16_pod" in text
    assert len(lean.SHA_LINE.findall(text)) == 1


def test_the_bundle_leaves_the_script_out(tmp_path, monkeypatch):
    monkeypatch.setattr(lean, "BUNDLE_DIRS", ("explainer_engine/training/pods/p16",))
    sh = tmp_path / "p16.sh"
    sh.write_text((DIR / "p16.sh").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(B, "SH", sh)
    sha = B.bundle(tmp_path / "a.tgz")
    assert sha in sh.read_text() and B.bundle(tmp_path / "b.tgz") == sha
    with tarfile.open(tmp_path / "a.tgz") as t:
        names = t.getnames()
    assert "explainer_engine/training/pods/p16/p16_pod.py" in names and "explainer_engine/training/pods/p16/p16.sh" not in names
    assert lean.EXCLUDE == ("explainer_engine/training/pods/p14/p14.sh",)   # put back


class FakeRun:
    def __init__(self, out, fail=(), draw=True):
        self.out, self.fail, self.calls, self.draw, self.lock = Path(out), set(fail), [], draw, threading.Lock()

    def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
        name = Path(log_path).stem
        with self.lock:
            self.calls.append((name, timeout))
        if name == "qwen_restyle" and self.draw:
            for sid in ("battle_f200_colour", WIDE, MID):
                f = self.out / "first_frames" / f"{sid}.png"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"x")
        return (1 if name in self.fail else 0), 1.0


def pod(tmp_path, run, *, secs=7200, fails=2):
    cfg = B.config(extra(), stills())
    cfg["max_ltx_failures"] = fails
    return p16_pod.Pod(cfg, B.schedule(1.6, "A100 80GB"), tmp_path, deadline=time.time() + secs, run=run)


def test_the_room_clips_run_before_the_restyle_and_the_battle_clips_after_it(tmp_path):
    run = FakeRun(tmp_path)
    assert pod(tmp_path, run).main() == 0
    names = [c[0] for c in run.calls]
    first_room = min(names.index(n) for n in p16_pod.ROOM_CLIPS)
    assert names.index("weights_ltx25") < first_room and names.index("weights_qwen") < names.index("qwen_restyle")
    assert max(names.index(n) for n in p16_pod.ROOM_CLIPS) < names.index("qwen_restyle") < min(names.index(n) for n in p16_pod.BATTLE_CLIPS)
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert all(rows[n]["status"] == "ok" for n in (*p16_pod.ROOM_CLIPS, *p16_pod.BATTLE_CLIPS, "qwen_restyle", "F"))
    sp = json.loads((tmp_path / "speeds.json").read_text())
    assert sp["schema"] == "p16_speeds/1"
    t = dict(run.calls)
    assert t["ltx_room_reverse"] == max(s["on"]["gpu"]["max_min"] for s in B.schedule(1.6, "A100 80GB")["stages"]
                                          if s["id"] == "ltx_room_reverse") * 60   # every timeout is the schedule's max


def test_a_battle_clip_without_its_restyled_first_frame_is_skipped_and_failures_stop_the_clips(tmp_path):
    run = FakeRun(tmp_path, draw=False)
    pod(tmp_path, run).main()
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert all(rows[n]["status"] == "skipped" and "first frame" in rows[n]["reason"] for n in p16_pod.BATTLE_CLIPS)
    assert all(rows[n]["status"] == "ok" for n in p16_pod.ROOM_CLIPS)   # their first frames are p15's, already on HF
    run = FakeRun(tmp_path / "f", fail=set(p16_pod.ROOM_CLIPS[:2]))
    assert pod(tmp_path / "f", run, fails=2).main() == 1   # two failures stop every clip after them (the plan's stop condition)
    rows = json.loads((tmp_path / "f" / "stages.json").read_text())["stages"]
    assert rows[p16_pod.ROOM_CLIPS[2]]["status"] == "skipped" and "failures" in rows[p16_pod.ROOM_CLIPS[2]]["reason"]
    assert all(rows[n]["status"] == "skipped" for n in p16_pod.BATTLE_CLIPS)


def test_nothing_starts_inside_the_end_reserve(tmp_path):
    run = FakeRun(tmp_path)
    pod(tmp_path, run, secs=60).main()
    rows = json.loads((tmp_path / "stages.json").read_text())["stages"]
    assert rows["weights_ltx25"]["reason"] == "inside the end reserve" and rows["qwen_restyle"]["status"] == "skipped"
    assert all(r["status"] != "running" for r in rows.values())


def test_the_committed_files_are_the_cards_and_the_schedule_s_when_they_exist():
    f = DIR / "p16.json"
    if not f.is_file():
        pytest.skip("p16.json is written by build.py config after the extra stills are rendered")
    cfg = json.loads(f.read_text(encoding="utf-8"))
    for j in cfg["qwen_jobs"]:
        assert j["qwen_prompt"] == PS.prompts(j["shot"])["qwen"], j["shot"]
    for j in cfg["ltx_jobs"]:
        assert j["prompt"] == PS.prompts(j["shot_id"])["ltx"], j["id"]
    sch = RP.load(DIR / "p16_schedule.json")
    assert {s["id"] for s in sch["stages"]} == {*p16_pod.LANES["net"], *p16_pod.LANES["gpu"]}
