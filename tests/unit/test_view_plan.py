"""The shot's view plan (faces.views) and what hangs on it: close-ups never shorter than BP-84's insert floor and never past
a cut, bubbles that never cross a change of the face frame nor sit on another hero's close-up, the face point reaching the
beats, the camera at rest at a cut inside one picture, rings on the named hero (the creator's QA of 2026-10-20, CC-01,
CC-03, CC-06; frame review FR-BUBBLE-FACE, FR-BUBBLE-WHO, FR-RING-HERO, FR-RING-FACE, FR-TEXT-CUT)."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.production import accents as ACC
from explainer_engine.production import assemble as A
from explainer_engine.production import beats as BEATS
from explainer_engine.production import faces as FACES
from explainer_engine.standards import sourced_rules as SR

FPS = 30
FLOOR = round(SR.T("BP-84", "min_insert_s") * FPS)


def _expr(who, f, end, expression="curious", shot="SH001", **kw):
    return dict({"kind": "expression", "who": who, "expression": expression, "start_frame": f, "end_frame": end,
                 "start": f / FPS, "end": end / FPS, "shot": shot, "picture": "duo"}, **kw)


def _bubble(who, f, end, text="Hello there."):
    return {"who": who, "text": text, "kind": "speech", "start_frame": f, "end_frame": end, "start": f / FPS, "end": end / FPS}


def _close_up(path, face=(210, 150, 110)):
    im = Image.new("RGB", (160, 90), FACES.key_rgb())
    d = ImageDraw.Draw(im)
    d.ellipse([50, 8, 90, 52], fill=face)  # the head, left of centre (painters do not centre the hero)
    d.rectangle([30, 50, 110, 90], fill=(40, 40, 60))
    im.save(path)
    return path


def test_views_absorb_short_face_swaps_and_stay_inside_the_shot():
    # the preview's SH010: 1.1 s of scene, 2.4 s oleary, 1 s musk to the cut -> every view at least BP-84's floor
    faces = [_expr("oleary", 40, 75), _expr("musk", 110, 140, "determined")]
    vs = FACES.views(faces, 0, 135, FPS)
    assert vs[0]["start_frame"] == 0 and vs[-1]["end_frame"] == 135
    assert all(v["end_frame"] - v["start_frame"] >= FLOOR for v in vs)
    assert all(a["end_frame"] == b["start_frame"] for a, b in zip(vs, vs[1:]))
    # one hero's expression changes inside his view are face swaps, not views
    vs = FACES.views([_expr("a", 10, 60), _expr("a", 40, 120, "sad")], 0, 150, FPS)
    assert [v["who"] for v in vs] == ["a", None] or [v["who"] for v in vs] == ["a"]


def test_a_bubble_never_crosses_a_view_change_nor_sits_on_another_heros_close_up():
    faces = [_expr("oleary", 60, 100), _expr("musk", 100, 140, "doubtful"), _expr("oleary", 200, 260, "smug")]
    bubbles = [_bubble("musk", 50, 130), _bubble("oleary", 180, 250)]
    vs = FACES.views(faces, 0, 300, FPS, bubbles=bubbles)
    for b in bubbles:
        seen = {FACES.view_at(vs, f)["who"] for f in range(b["start_frame"], b["end_frame"])}
        assert len(seen) == 1 and seen <= {None, b["who"]}, (b, vs)


def test_composite_with_views_cuts_in_and_out_with_its_view(tmp_path):
    frame = Image.fromarray((np.random.default_rng(1).random((180, 320, 3)) * 255).astype(np.uint8))
    b = _expr("einstein", 60, 150, close_up=_close_up(tmp_path / "f.png"), face=None)
    vs = [{"start_frame": 0, "end_frame": 60, "who": None}, {"start_frame": 60, "end_frame": 150, "who": "einstein"}]
    assert FACES.composite(frame, [b], 59, FPS, ["einstein"], vs) is frame
    first = np.asarray(FACES.composite(frame, [b], 60, FPS, ["einstein"], vs)).astype(int)
    later = np.asarray(FACES.composite(frame, [b], 120, FPS, ["einstein"], vs)).astype(int)
    assert np.abs(first[:, 250:] - later[:, 250:]).max() < 3  # the backdrop is already fully zoomed: no ramp, a cut
    assert FACES.composite(frame, [b], 150, FPS, ["einstein"], vs) is frame  # past the plan (the cut): nothing


def test_beats_for_shot_gives_expressions_their_face_point():
    s = {"id": "SH001", "start_frame": 0, "end_frame": 90}
    pics = {"duo": {"speakers": {"a": [0.3, 0.4], "b": [0.7, 0.4]}}}
    on = A.beats_for_shot([_expr("a", 10, 40), _expr("b", 40, 80)], s, pics, {}, [])
    assert [b["face"] for b in on] == [[0.3, 0.4], [0.7, 0.4]]


def test_face_lean_glides_between_speakers_and_rests_at_a_cut_inside_one_picture():
    box = (0.0, 0.0, 320.0, 180.0)
    beats = [dict(_expr("a", 0, 40), face=[0.2, 0.4]), dict(_expr("b", 40, 90), face=[0.8, 0.4])]
    xs = [BEATS.face_camera(box, 320, 180, beats, f, FPS)[0] for f in range(30, 60)]
    assert max(abs(x - y) for x, y in zip(xs, xs[1:])) < 2.0  # the pivot switch used to jump ~8 px here
    s = {"id": "SH001", "start_frame": 0, "end_frame": 60, "render_motion": {"ein": True, "eout": False}}
    assert A.rest_weight(s, 59, FPS) == 0.0 and A.rest_weight(s, 20, FPS) == 1.0
    s2 = {"id": "SH002", "start_frame": 60, "end_frame": 120, "render_motion": {"ein": False, "eout": True}}
    assert A.rest_weight(s2, 60, FPS) == 0.0


def test_a_held_punch_is_back_at_rest_on_the_last_frame_before_the_same_picture_continues():
    im = Image.fromarray((np.random.default_rng(2).random((180, 320, 3)) * 255).astype(np.uint8))
    m = {"kind": "push", "z0": 1.0, "z1": 1.05, "ein": True, "eout": False}
    s = {"id": "SH001", "start_frame": 0, "end_frame": 60, "motion": m, "render_motion": m,
         "accents": ACC.resolve([{"kind": "punch", "strength": 1.0}], 0.0, 2.0, lambda p: None, FPS)}
    box = A.motion_box(m, 320, 180, 1.0)
    plain = np.asarray(im.resize((320, 180), Image.BICUBIC, box=box)).astype(int)
    got = np.asarray(A.finish_frame(im, box, s, 59, FPS, (320, 180), [], {}, [], [])).astype(int)
    assert np.abs(got - plain).mean() < 1.0
    mid = np.asarray(A.finish_frame(im, box, s, 30, FPS, (320, 180), [], {}, [], [])).astype(int)
    assert np.abs(mid - plain).mean() > 5  # the punch itself still lands


def test_bubble_on_the_speakers_close_up_points_at_the_close_ups_mouth(tmp_path):
    cu = _close_up(tmp_path / "a_curious.png")
    s = {"id": "SH001", "start_frame": 0, "end_frame": 150, "motion": {"kind": "static", "z0": 1.0, "z1": 1.0},
         "bubbles": [_bubble("a", 10, 100, "I can build anything.")]}
    s["views"] = FACES.views([_expr("a", 5, 140, close_up=cu)], 0, 150, FPS, bubbles=s["bubbles"])
    assert s["views"][0]["who"] == "a"
    sb = [_expr("a", 5, 140, close_up=cu)]
    b = A.shot_bubbles(s, {"speakers": {"a": [0.8, 0.4]}}, (320, 180), (640, 360), sb, FPS, ["a"])[0]
    mouth, head = FACES.mouth_and_head(dict(sb[0], start_frame=5), ["a"], (640, 360))
    assert not b.covers_face and not (b.box[0] < head[2] and head[0] < b.box[2] and b.box[1] < head[3] and head[1] < b.box[3])
    assert abs(mouth[0] - 640 * 0.43) < 640 * 0.12  # the measured head (left of centre), not the picture's 0.8


def test_an_old_bubble_crossing_a_view_change_ends_with_its_view():
    s = {"id": "SH001", "start_frame": 0, "end_frame": 150, "motion": {"kind": "static", "z0": 1.0, "z1": 1.0},
         "bubbles": [_bubble("a", 10, 120)],
         "views": [{"start_frame": 0, "end_frame": 90, "who": None}, {"start_frame": 90, "end_frame": 150, "who": "b"}]}
    b = A.shot_bubbles(s, {"speakers": {"a": [0.3, 0.4]}}, (320, 180), (640, 360), [], FPS, ["a", "b"])[0]
    assert abs(b.end - 90 / FPS) < 1e-6


def test_fit_to_views_rings_the_named_hero_and_keeps_marks_off_close_ups():
    shots = [{"id": "SH001", "picture": "duo", "start": 0.0, "end": 4.0, "start_frame": 0, "end_frame": 120, "visual_beats": 3,
              "views": [{"start_frame": 0, "end_frame": 60, "who": None}, {"start_frame": 60, "end_frame": 120, "who": "musk"}]}]
    pics = {"duo": {"speakers": {"musk": [0.62, 0.42], "oleary": [0.3, 0.4]}}}
    ring = {"kind": "highlight", "at": "Elon Musk", "pos": [0.62, 0.5], "shot": "SH001", "segment": "S01", "line": 1,
            "start": 0.5, "end": 1.8, "start_frame": 15, "end_frame": 54}
    label = {"kind": "label", "at": "the deal", "text": "DEAL", "pos": [0.5, 0.5], "shot": "SH001", "segment": "S01", "line": 2,
             "start": 2.5, "end": 3.5, "start_frame": 75, "end_frame": 105}
    text = {"kind": "text", "at": "forty", "text": "$40", "pos": [0.5, 0.2], "shot": "SH001", "segment": "S01", "line": 2,
            "start": 2.2, "end": 5.0, "start_frame": 66, "end_frame": 150}
    probs: list = []
    out = BEATS.fit_to_views(shots, [ring, label, text], pics, {"musk": {}, "oleary": {}}, FPS, probs)
    assert ring["pos"] == [0.62, 0.42] and label not in out and probs and probs[0]["severity"] == "REVIEW"
    assert text["end"] == 4.0 and text["end_frame"] == 120  # ends with its shot: still readable there (BP-27)


def test_timing_plan_marks_every_shot_with_views():
    shots = [{"id": "SH001", "start_frame": 0, "end_frame": 120, "bubbles": []}]
    cast = {"a": {"face_sheet": {"id": "a_faces", "set": ["curious"]}}}
    FACES.plan_shots(shots, [_expr("a", 10, 110)], cast, FPS)
    assert shots[0]["views"] and shots[0]["views"][-1]["end_frame"] == 120
    assert any(v["who"] == "a" for v in shots[0]["views"])


def test_the_face_lean_never_jumps_like_a_cut():
    """PX-CUT-EXTRA on titans at 99.8 s: the lean zoomed 14 % in a quarter second on an expression beat; now it glides."""
    from explainer_engine.production import beats as B
    W, H, fps = 1920, 1080, 30
    box = (0.0, 0.0, float(W), float(H))
    beat = {"start_frame": 30, "end_frame": 150, "face": (0.3, 0.4), "shot": "SH1"}
    widths = [B.face_camera(box, W, H, [beat], f, fps) for f in range(0, 220)]
    zoom = [W / (b[2] - b[0]) for b in widths]
    assert max(abs(a - b) for a, b in zip(zoom, zoom[1:])) < 0.006   # under 0.6 % a frame: a move, never a cut
    assert max(zoom) <= 1 + B.FACE_HOLD + B.FACE_POP + 1e-9
    assert abs(zoom[31] - zoom[30]) < 0.0005   # it starts gently: no jolt on the first frame of the lean


def test_a_renderer_change_redraws_the_chunks(monkeypatch):
    """The chunk stamp carries the renderer's code: a fixed renderer never reuses chunks drawn before the fix."""
    from explainer_engine.production import assemble as A
    timed = {"shots": [], "fps": 30}
    a = A.plan_stamp(timed, (1280, 720), 18, None, [], {}, [])
    monkeypatch.setattr(A, "render_code", lambda: "changed")
    assert A.plan_stamp(timed, (1280, 720), 18, None, [], {}, []) != a


def test_a_label_naming_a_hero_points_at_his_face_point():
    """The S02 label "KEVIN O'LEARY" pointed at an empty wall (CC-03): a label naming a hero, in its phrase or only in its
    tag, snaps to his face point the way a ring does; a label naming nobody keeps its pos."""
    shots = [{"id": "SH001", "picture": "duo", "start": 0.0, "end": 4.0, "start_frame": 0, "end_frame": 120, "visual_beats": 3}]
    pics = {"duo": {"speakers": {"musk": [0.62, 0.42], "oleary": [0.3, 0.4]}}}
    by_phrase = {"kind": "label", "at": "Kevin O'Leary", "text": "KEVIN O'LEARY", "pos": [0.18, 0.4], "shot": "SH001",
                 "segment": "S02", "line": 1, "start": 0.5, "end": 1.8, "start_frame": 15, "end_frame": 54}
    by_tag = dict(by_phrase, at="the shark", text="O'LEARY", pos=[0.9, 0.2])
    prop = dict(by_phrase, at="the contract", text="CONTRACT", pos=[0.5, 0.7])
    out = BEATS.fit_to_views(shots, [by_phrase, by_tag, prop], pics, {"musk": {}, "oleary": {}}, FPS, [])
    assert len(out) == 3
    assert by_phrase["pos"] == [0.3, 0.4] and by_phrase["on_hero"] == "oleary"
    assert by_tag["pos"] == [0.3, 0.4] and prop["pos"] == [0.5, 0.7] and "on_hero" not in prop
