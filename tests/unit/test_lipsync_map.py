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


def test_run_rhubarb_without_a_dialog_file_and_its_failure_text(tmp_path):
    out = tmp_path / "cues.json"
    seen = {}

    class P:
        returncode, stderr = 0, ""

    def run(argv, **kw):
        seen["argv"] = argv
        out.write_text(__import__("json").dumps(HI), encoding="utf-8")
        return P()
    got = R.run_rhubarb(tmp_path / "line.wav", out, exe="rh", run=run)
    assert "-d" not in seen["argv"] and seen["argv"][0] == "rh" and seen["argv"][-1].endswith("line.wav")
    assert got["cues"][1] == (0.05, 0.27, "D")

    class Bad:
        returncode, stderr = 1, "Error: cannot read file"
    with pytest.raises(RuntimeError, match="cannot read file"):
        R.run_rhubarb(tmp_path / "line.wav", out, run=lambda *a, **k: Bad())


def test_bone_map_is_exact_names_only():
    same = R.bone_map(["root", "pelvis", "Head"], ["root", "pelvis", "Head"])
    assert same["identical"] and same["unmatched_source"] == [] and same["map"]["Head"] == "Head"
    other = R.bone_map(["root", "Hips", "Head"], ["root", "pelvis", "head"])
    assert not other["identical"] and other["map"] == {"root": "root"}
    assert other["unmatched_source"] == ["Hips", "Head"] and other["unmatched_target"] == ["pelvis", "head"]


def _walk(n=32, fps=24, speed=0.8, slip=0.0):
    """An in-place walk: each foot planted for half the cycle and moving back at ``speed`` (plus ``slip`` m extra per contact)."""
    rows = []
    for f in range(n):
        ph = f / n
        row = {"root": [0, 0, 0], "pelvis": [0, 0, 1]}
        for foot, shift in (("foot_l", 0.0), ("foot_r", 0.5)):
            q = (ph + shift) % 1.0
            if q < 0.5:   # planted: slides back
                y = 0.3 - (speed + slip * fps / (n / 2)) * q * n / fps
                z = 0.1
            else:         # swing: lifted, goes forward
                y = 0.0
                z = 0.25
            row[foot] = [0.1 if foot == "foot_l" else -0.1, y, z]
        rows.append(row)
    return rows


def test_foot_slide_finds_the_natural_speed_and_a_stationary_slide():
    r = R.foot_slide(_walk(), 24)
    assert r["in_place"] and abs(r["natural_speed_mps"] - 0.8) < 1e-6 and r["slide_m"] < R.POC1_SLIDE_M and r["passed"]
    off = R.foot_slide(_walk(), 24, root_speed_mps=0.4)   # the body moved at half the clip's speed: the feet skate
    assert off["slide_m"] > R.POC1_SLIDE_M and not off["passed"]
    still = [{"root": [0, 0, 0], "foot_l": [0.1, 0, 0.1], "foot_r": [-0.1, 0.01 * k, 0.1]} for k in range(10)]
    s = R.foot_slide(still, 24, root_speed_mps=0.0)
    assert s["slide_m"] == 0.09 and not s["passed"]   # a dragged foot while standing is a slide


def test_lipsync_measure_offset_in_frames_and_open_mouth_on_silence():
    cues = {"metadata": {"duration": 2.0}, "mouthCues": [
        {"start": 0.0, "end": 0.5, "value": "X"}, {"start": 0.5, "end": 0.8, "value": "D"}, {"start": 0.8, "end": 1.2, "value": "X"},
        {"start": 1.2, "end": 1.5, "value": "C"}, {"start": 1.5, "end": 2.0, "value": "X"}]}
    words = [{"start": 0.5 - 1 / 24, "end": 0.8}, {"start": 1.2, "end": 1.5}]
    m = R.lipsync_measure(cues, words)
    assert m["mean_abs_offset_frames"] == 0.5 and m["open_on_silence_frames"] == 0 and m["passed"]
    late = R.lipsync_measure(cues, [{"start": 0.3, "end": 0.45}, {"start": 1.0, "end": 1.1}])
    assert late["mean_abs_offset_frames"] > R.POC2_OFFSET_FRAMES and late["longest_open_silence_run"] > R.POC2_OPEN_SILENCE
    assert not late["passed"]


# --- WP-Q4: bone-pose visemes for the Blender Studio rigs (mouth = CloudRig controls, no shape keys) ---
POSES = {s: {"MSTR-Jaw": {"rot": [0, 0, 0]}} for s in R.SHAPES}
POSES["D"] = {"MSTR-Jaw": {"rot": [25, 0, 0]}, "MSTR-Mouth": {"scale": [1, 1, 1.2]}}
POSES["B"] = {"ACT-Lips_Corner.L": {"loc": [0.01, 0, 0]}}


def test_action_visemes_key_each_change_with_the_previous_value_on_the_frame_before():
    av = R.ActionVisemes(POSES)
    shapes = av.lip.frames(HI)
    tr = av.tracks(HI)
    jaw = dict(map(tuple, tr["MSTR-Jaw|rotation_euler|0"]))
    f = shapes.index("D")
    assert jaw[f - 1] == 0.0 and abs(jaw[f] - 0.436332) < 1e-5          # 25 degrees in radians
    assert jaw[0] == 0.0 and jaw[len(shapes) - 1] == 0.0                # first and last frame always keyed
    assert tr["MSTR-Mouth|scale|2"][-1][1] == 1.0                        # a shape that leaves a channel out rests it
    assert tr["ACT-Lips_Corner.L|location|0"][0][1] == 0.0


def test_action_visemes_refuse_a_table_without_a_shape_or_with_a_bad_channel():
    with pytest.raises(ValueError, match="no pose for"):
        R.ActionVisemes({k: v for k, v in POSES.items() if k != "H"})
    bad = {**POSES, "A": {"MSTR-Jaw": {"rot": [1, 2]}}}
    with pytest.raises(ValueError, match="three numbers"):
        R.ActionVisemes(bad)


def test_action_visemes_apply_keys_pose_bones_and_names_a_missing_bone():
    class PB:
        def __init__(self):
            self.rotation_euler, self.location, self.scale, self.keys = [0, 0, 0], [0, 0, 0], [1, 1, 1], []

        def keyframe_insert(self, data_path, index, frame):
            self.keys.append((data_path, index, frame, list(getattr(self, data_path))[index]))

    av = R.ActionVisemes(POSES)
    tr = av.tracks(HI)
    bones = {"MSTR-Jaw": PB(), "MSTR-Mouth": PB(), "ACT-Lips_Corner.L": PB()}
    n = R.ActionVisemes.apply(tr, bones, start_frame=101)
    assert n == sum(len(v) for v in tr.values())
    assert min(k[2] for k in bones["MSTR-Jaw"].keys) == 101
    with pytest.raises(KeyError, match="MSTR-Mouth"):
        R.ActionVisemes.apply(tr, {k: v for k, v in bones.items() if k != "MSTR-Mouth"})
