"""blender/rigs.py (roadmap 21.5 #4 and #9, 21.11): Rhubarb's JSON -> one shape per frame at 24 fps with X on silence ->
shape-key tracks with a one-frame blend; overlapping cues are refused; the Rhubarb command; animations play on a rig only
with its skeleton (the retarget is ICW-06's)."""
import pytest

from explainer_engine.blender import rigs as R

# the README's own example (0.47 s, "hi"), plus a gap and a trailing pause added by the test
HI = {"metadata": {"soundFile": "hi.wav", "duration": 0.47},
      "mouthCues": [{"start": 0.00, "end": 0.05, "value": "X"}, {"start": 0.05, "end": 0.27, "value": "D"},
                    {"start": 0.27, "end": 0.31, "value": "C"}, {"start": 0.31, "end": 0.43, "value": "B"},
                    {"start": 0.43, "end": 0.47, "value": "X"}]}


def test_one_shape_per_frame_from_the_cue_holding_its_start_time():
    shapes = R.LipSync().frames(HI)
    assert len(shapes) == 12  # ceil(0.47 x 24)
    # frame f starts at f/24 s: 0 -> X, 1 (0.042) -> X, 2 (0.083) .. 6 (0.25) -> D, 7 (0.292) -> C, 8..10 -> B, 11 (0.458) -> X
    assert "".join(shapes) == "XXDDDDDCBBBX"


def test_silence_and_gaps_and_the_tail_rest_on_x_or_on_a_without_x():
    gap = {"metadata": {"duration": 0.5}, "mouthCues": [{"start": 0.1, "end": 0.2, "value": "F"}, {"start": 0.3, "end": 0.35, "value": "G"}]}
    shapes = R.LipSync().frames(gap, frames=14)
    assert shapes[0] == "X" and shapes[3] == "F" and shapes[5] == "X" and shapes[-1] == "X"
    assert set(R.LipSync(extended="GH").frames(gap)) <= {"A", "F", "G"}  # Rhubarb's rest is A when X is not drawn


def test_tracks_key_a_one_frame_blend_and_exactly_one_shape_is_full_on_every_change():
    tr = R.LipSync().tracks(HI)
    assert sorted(tr) == sorted(R.DEFAULT_KEYS.values())
    d = dict(map(tuple, tr["mouth_D"]))
    assert d[0] == 0.0 and d[1] == 0.0 and d[2] == 1.0 and d[6] == 1.0 and d[7] == 0.0
    x = dict(map(tuple, tr["mouth_X"]))
    assert x[0] == 1.0 and x[1] == 1.0 and x[2] == 0.0 and x[10] == 0.0 and x[11] == 1.0
    shapes = R.LipSync().frames(HI)
    for f in range(len(shapes)):  # on every keyed frame the keyed values sum to one: never two mouths, never none
        vals = [dict(map(tuple, keys))[f] for keys in tr.values() if f in dict(map(tuple, keys))]
        if len(vals) == len(tr):
            assert sum(vals) == 1.0, f
    cut = R.LipSync(blend_frames=0).tracks(HI)
    assert 1 not in dict(map(tuple, cut["mouth_X"])) and dict(map(tuple, cut["mouth_X"]))[2] == 0.0  # a hard cut: no f-1 key
    assert [k for k in cut["mouth_C"]] == [[0, 0.0], [7, 1.0], [8, 0.0], [11, 0.0]]
    with pytest.raises(ValueError, match="blend_frames"):
        R.tracks(shapes, blend_frames=2)


def test_overlapping_unsorted_or_unknown_cues_are_refused():
    bad = {"mouthCues": [{"start": 0.0, "end": 0.2, "value": "A"}, {"start": 0.1, "end": 0.3, "value": "B"}]}
    with pytest.raises(ValueError, match="overlap"):
        R.load_cues(bad)
    with pytest.raises(ValueError, match="unknown mouth shape"):
        R.load_cues({"mouthCues": [{"start": 0.0, "end": 0.2, "value": "Q"}]})
    with pytest.raises(ValueError, match="not after"):
        R.load_cues({"mouthCues": [{"start": 0.2, "end": 0.2, "value": "A"}]})


def test_apply_keys_the_heads_shape_keys_from_the_shots_first_frame():
    class Key:
        def __init__(self):
            self.value, self.keys = 0.0, []

        def keyframe_insert(self, data_path, frame):
            self.keys.append((data_path, frame, self.value))

    tr = R.LipSync().tracks(HI)
    head = {name: Key() for name in tr}
    n = R.LipSync.apply(tr, head, start_frame=101)
    assert n == sum(len(v) for v in tr.values())
    assert head["mouth_D"].keys[0] == ("value", 101, 0.0) and ("value", 103, 1.0) in head["mouth_D"].keys
    with pytest.raises(KeyError, match="mouth_A"):
        R.LipSync.apply(tr, {k: v for k, v in head.items() if k != "mouth_A"})


def test_the_rhubarb_command_gives_json_the_dialog_text_and_the_wav_last():
    argv = R.rhubarb_argv("line.wav", "line.txt", "shot.json")
    assert argv == ["rhubarb", "-r", "pocketSphinx", "-f", "json", "--extendedShapes", "GHX", "-d", "line.txt", "-o", "shot.json",
                    "line.wav"]
    with pytest.raises(ValueError):
        R.rhubarb_argv("a.wav", "a.txt", "a.json", recognizer="whisper")


def test_rig_adapter_plays_the_same_skeleton_and_plans_a_retarget_otherwise():
    rig = {"id": "rig.ubc", "kind": "rig", "three_d": {"skeleton_id": "skeleton.ubc_humanoid_v1", "rig_profile": "ubc_humanoid"}}
    walk = {"id": "animation.walk", "kind": "animation", "three_d": {"skeleton_id": "skeleton.ubc_humanoid_v1"}}
    wave = {"id": "animation.wave", "kind": "animation", "three_d": {"skeleton_id": "skeleton.mixamo_v1"}}
    assert R.RigAdapter.plan(walk, rig)["action"] == "play"
    p = R.RigAdapter.plan(wave, rig)
    assert p["action"] == "retarget" and (p["from"], p["to"]) == ("skeleton.mixamo_v1", "skeleton.ubc_humanoid_v1")
    with pytest.raises(ValueError):
        R.RigAdapter.plan(rig, walk)
    lib = {"schema": "asset_library/2", "items": [
        dict(rig, tags=["rig"], approval={"status": "not_looked"}, bible_version="1.5"),
        dict(walk, tags=["walk"], approval={"status": "not_looked"}, bible_version="1.5"),
        dict(wave, tags=["wave"], approval={"status": "not_looked"}, bible_version="1.5")]}
    assert [a["id"] for a in R.RigAdapter(lib).playable("rig.ubc")] == ["animation.walk"]
