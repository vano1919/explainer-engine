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
