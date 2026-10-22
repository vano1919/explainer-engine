"""AI-video route (2026-10-22): shots.json / timeline.json checks, keyframe references, montage plan, money schedule."""
import copy, json, os
from explainer_engine.aivideo import shotplan as sp

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "aivideo")
SHOTS = json.load(open(os.path.join(FIX, "shots.json"), encoding="utf-8"))
TL = json.load(open(os.path.join(FIX, "timeline.json"), encoding="utf-8"))


def test_night_test_video_inputs_are_consistent():
    assert sp.check_shots(SHOTS) == []
    assert sp.check_timeline(TL, SHOTS) == []
    assert TL["end"] - TL["intro_end"] > 90  # a real two-minute test, not a stub


def test_check_shots_catches_unknown_character_plate_and_empty_prompt():
    d = copy.deepcopy(SHOTS)
    d["shots"][0]["chars"].append("ghost")
    d["shots"][1]["plate"] = "moon"
    d["shots"][2]["motion"] = " "
    d["shots"].append(dict(d["shots"][3]))
    bad = " | ".join(sp.check_shots(d))
    assert "unknown character 'ghost'" in bad and "unknown plate 'moon'" in bad
    assert "empty motion" in bad and "repeated" in bad


def test_no_trigger_word_is_refused():
    d = dict(SHOTS, trigger="")
    assert any("trigger" in p for p in sp.check_shots(d))


def test_timeline_gap_and_missing_shot_are_found():
    tl = copy.deepcopy(TL)
    tl["segments"][3]["t0"] += 0.5
    tl["segments"].append({"id": "c99", "t0": tl["end"], "t1": tl["end"] + 1})
    bad = " | ".join(sp.check_timeline(tl, SHOTS))
    assert "starts at" in bad and "c99: no shot" in bad and "narration ends" in bad


def test_keyframe_refs_cap_sheets_and_add_the_plate():
    sheets = {c: c + ".png" for c in SHOTS["characters"]} | {"tundra": "tundra.png"}
    shot = {"chars": ["rosa", "tom", "maya", "walter"], "plate": "tundra"}
    assert sp.keyframe_refs(shot, sheets) == ["rosa.png", "tom.png", "maya.png", "tundra.png"]


def test_prompt_starts_with_the_trigger():
    assert sp.prompt(SHOTS, "a bus").startswith(SHOTS["trigger"] + ", a bus")


def test_montage_plan_holds_keyframe_before_short_clip_and_marks_gaps():
    tl = {"intro_end": 0, "end": 12, "segments": [{"id": "a", "t0": 0, "t1": 8}, {"id": "b", "t0": 8, "t1": 10},
                                                   {"id": "c", "t0": 10, "t1": 11}, {"id": "d", "t0": 11, "t1": 12}]}
    plan = {p["id"]: p for p in sp.montage_plan(tl, {"a": 5.06, "b": 5.06}, {"a", "b", "c"})}
    assert plan["a"]["how"] == "hold+clip" and abs(plan["a"]["hold"] - 2.94) < 1e-6
    assert plan["b"]["how"] == "clip" and plan["b"]["hold"] == 0
    assert plan["c"]["how"] == "still" and plan["d"]["how"] == "MISSING"


def test_night_schedule_fits_the_money_ceiling():
    # pod up to $0.79/h, ceiling $2.4: training stops at 85 min, clips at 150, the first late upload at 165 (watchdog.py)
    assert sp.affordable_minutes(2.4, 0.79) == 182
    assert sp.schedule_fits([85, 150, 165], 2.4, 0.79)
    assert not sp.schedule_fits([160, 225, 375], 2.85, 0.79)  # pod.sh's own clock, written for a $0.35 A40


def test_pod_code_follows_the_rules():
    pod = os.path.join(os.path.dirname(sp.__file__), "pod")
    launch = open(os.path.join(pod, "launch.py"), encoding="utf-8").read()
    assert "preflight_create" in launch and "guard_detached" in launch and "Run.open" in launch  # invariant 1 + ledger
    assert "volume=0" in launch  # container disk only: no volume that bills while stopped (a missing key gave 20 GB)
    sh = open(os.path.join(pod, "pod.sh"), encoding="utf-8").read()
    assert "stopself" in sh and "fatal" in sh
    assert 'huggingface_hub[hf_transfer]<2"' in sh  # hub 2.x breaks transformers: it killed try 2's smoke and training
    assert '|| fatal "SMOKE KF"' in sh and '|| fatal "SMOKE CLIPS"' in sh  # a failed smoke ends the pod, not the night
    for f in ("pod.sh", "kf.py", "clips.py", "launch.py", "watchdog.py", "montage.py"):
        txt = open(os.path.join(pod, f), encoding="utf-8").read()
        assert "hf_" not in txt.replace("hf_transfer", "").replace("hf_hub", "").replace("hf_whoami", ""), f  # no tokens
    assert "lora" not in json.dumps(SHOTS["characters"]).lower()  # no character LoRAs (the creator, 2026-10-22)
