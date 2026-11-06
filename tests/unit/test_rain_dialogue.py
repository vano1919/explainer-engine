"""WP-Q4: the two-line dialogue for the Rain lead (pure Python tracks for the rig_blend 'visemes' key)."""
import json
import math
from pathlib import Path

import pytest

from explainer_engine.blender import rain_dialogue as D

HERE = Path(D.__file__).parent


def _lines():
    j = json.loads((HERE / "rain_dialogue_synthetic.json").read_text(encoding="utf-8"))
    return [{**l, "cues": HERE / l["cues"]} for l in j["lines"]], j["frames"]


def test_tracks_cover_mouth_head_neck_and_arm_in_radians():
    lines, frames = _lines()
    out = D.dialogue(lines, frames)["visemes"]
    for k in ("MSTR-Jaw|rotation_euler|0", "FK-Head|rotation_euler|1", "FK-Neck|rotation_euler|1", "FK-Head|rotation_euler|0",
              "FK-Forearm.R|rotation_euler|0", "FK-Upperarm.R|rotation_euler|0"):
        assert k in out
        assert out[k][0][0] == 0 and out[k][-1][0] == frames - 1
    assert max(v for _, v in out["MSTR-Jaw|rotation_euler|0"]) < math.radians(60)   # radians, not degrees
    assert max(v for _, v in out["FK-Forearm.R|rotation_euler|0"]) > math.radians(55)   # the explain gesture reaches its peak


def test_head_turns_per_line_and_gesture_rests_between_lines():
    lines, frames = _lines()
    out = D.dialogue(lines, frames)["visemes"]
    yaw = dict(out["FK-Head|rotation_euler|1"])
    assert yaw[36] > 0 > yaw[108]                                   # line 1 turns right, line 2 left
    arm = dict(out["FK-Forearm.R|rotation_euler|0"])
    assert arm[84] == pytest.approx(math.radians(D.REST_FOREARM_DEG), abs=1e-3)   # no gesture on the second (nod) line


def test_swapping_the_cue_file_changes_only_the_mouth():
    lines, frames = _lines()
    a = D.dialogue(lines, frames)["visemes"]
    quiet = {"mouthCues": [{"start": 0.0, "end": 2.08, "value": "X"}], "metadata": {"duration": 2.08}}
    b = D.dialogue([{**lines[0], "cues": quiet}, lines[1]], frames)["visemes"]
    assert a["FK-Head|rotation_euler|1"] == b["FK-Head|rotation_euler|1"] and a["FK-Forearm.R|rotation_euler|0"] == b["FK-Forearm.R|rotation_euler|0"]
    assert a["MSTR-Jaw|rotation_euler|0"] != b["MSTR-Jaw|rotation_euler|0"]


def test_unknown_gesture_and_empty_dialogue_are_refused():
    lines, frames = _lines()
    with pytest.raises(ValueError):
        D.dialogue([{**lines[0], "gesture": "wave"}], frames)
    with pytest.raises(ValueError):
        D.dialogue([], frames)


def test_two_speakers_rain_mouth_only_on_her_line_and_villager_lipsync_offset():
    j = json.loads((HERE / "rain_dialogue_two_speakers_synthetic.json").read_text(encoding="utf-8"))
    lines = [{**l, "cues": HERE / l["cues"]} for l in j["lines"]]
    out = D.dialogue(lines, 120, speaker="rain")["visemes"]
    jaw = dict(out["MSTR-Jaw|rotation_euler|0"])
    assert max(v for f, v in jaw.items() if f > 70) == 0.0                     # line 2 (from 2.6 s = frame 62.4) is not hers
    assert max(v for f, v in jaw.items() if f < 50) > 0.0
    plan = D.lipsync_plan(lines, 120, "villager")
    assert plan["shapes"][:62] == "X" * 62 and set(plan["shapes"][63:110]) - {"X"}   # rests, then speaks from line 2's start
    assert plan["frames"] == 120
    with pytest.raises(ValueError):
        D.lipsync_plan(lines, 120, "nobody")


def test_cli_writes_both_speakers(tmp_path):
    out = tmp_path / "t.json"
    assert D.main(["--dialogue", str(HERE / "rain_dialogue_two_speakers_synthetic.json"), "--frames", "120", "--out", str(out),
                   "--shape-speaker", "villager"]) == 0
    j = json.loads(out.read_text(encoding="utf-8"))
    assert "visemes" in j["rain"] and "lipsync" in j["villager"]


def test_a_cut_window_shifts_every_line_and_keeps_a_lipsync_shot_under_the_cap():
    j = json.loads((HERE / "rain_dialogue_two_speakers_synthetic.json").read_text(encoding="utf-8"))
    lines = [{**l, "cues": HERE / l["cues"]} for l in j["lines"]]
    plan = D.lipsync_plan(lines, 120, "villager", window_s=2.0)          # his line (2.6 s) starts 0.6 s into the cut
    assert plan["shapes"][:14] == "X" * 14 and set(plan["shapes"][15:60]) - {"X"}
    with pytest.raises(ValueError):                                       # BP-108: a lip-synced shot is at most 5 s
        D.lipsync_plan(lines, 200, "villager")
