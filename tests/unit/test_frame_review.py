"""Claude's self-review of a render (standing order 12; the creator, 2026-10-20: errors in the first preview Claude should have
seen): the timing checks of qa/frame_review on a tiny synthetic timed dict, no ffmpeg."""
from explainer_engine.production import accents as ACC
from explainer_engine.qa import frame_review as FR

FPS = 30


def _shot(sid, start, end, picture="pic", bubbles=()):
    return {"id": sid, "picture": picture, "start": start, "end": end, "start_frame": round(start * FPS),
            "end_frame": round(end * FPS), "transition": "cut", "bubbles": [_bubble(*b) for b in bubbles]}


def _bubble(who, text, start, end):
    return {"who": who, "text": text, "kind": "speech", "start": start, "end": end, "start_frame": round(start * FPS),
            "end_frame": round(end * FPS)}


def _face(shot, who, expression, start, end):
    return {"kind": "expression", "shot": shot, "picture": "pic", "who": who, "speaker": who, "expression": expression,
            "start": start, "end": end, "start_frame": round(start * FPS), "end_frame": round(end * FPS), "at": expression}


def _timed(shots, beats=()):
    return {"fps": FPS, "shots": shots, "visual_beats": list(beats),
            "face_sheets": {"ann": {"id": "ann_faces_v1", "set": []}, "bob": {"id": "bob_faces_v1", "set": []}},
            "pictures": {"pic": {"heroes": ["ann", "bob"], "speakers": {"ann": [0.3, 0.4], "bob": [0.7, 0.4]}}}}


def _rules(findings, sev="FAIL"):
    return {f["rule"] for f in findings if f["severity"] == sev}


def test_a_clean_dialogue_passes():
    # each hero's close-up covers his own whole line, the bubbles sit inside one face run, no cut inside a bubble
    t = _timed([_shot("SH1", 0.0, 3.0, bubbles=[("ann", "Hello there.", 0.6, 2.4)]),
                _shot("SH2", 3.0, 6.0, bubbles=[("bob", "Hi.", 3.6, 5.4)])],
               [_face("SH1", "ann", "joyful", 0.2, 3.0), _face("SH2", "bob", "curious", 3.2, 6.0)])
    found = FR.check(t)
    assert not _rules(found), found
    assert FR.moments(t)  # cuts, bubbles and face changes are listed for the sheets


def test_a_bubble_across_a_cut_fails():
    t = _timed([_shot("SH1", 0.0, 3.0, bubbles=[("ann", "This runs too long.", 2.0, 3.8)]), _shot("SH2", 3.0, 6.0)])
    assert "FR-BUBBLE-CUT" in _rules(FR.check(t))


def test_a_bubble_crossing_a_face_frame_change_fails():
    # the bubble starts on the scene, then ann's close-up eases in under it: its tail then points at nothing
    t = _timed([_shot("SH1", 0.0, 4.0, bubbles=[("ann", "You can still build things?", 0.3, 2.0)])],
               [_face("SH1", "ann", "curious", 1.2, 4.0)])
    assert "FR-BUBBLE-FACE" in _rules(FR.check(t))


def test_a_bubble_on_another_heros_close_up_fails():
    # bob speaks while ann's reaction close-up fills the frame: bob's words sit on ann's face (Titans S02, 64.6 s)
    t = _timed([_shot("SH1", 0.0, 4.0, bubbles=[("bob", "I can build anything.", 1.0, 3.0)])],
               [_face("SH1", "ann", "smug", 0.2, 4.0)])
    found = FR.check(t)
    assert "FR-BUBBLE-WHO" in _rules(found)
    assert any("bob's words over ann's close-up" in f["detail"] for f in found)


def test_face_at_mirrors_the_renderers_lead_and_ease():
    faces = [_face("SH1", "ann", "joyful", 1.0, 2.0)]
    lead = ACC.EXPR_LEAD_FRAMES
    assert FR.face_at(faces, 30 - lead, FPS) == ("ann", "joyful")
    assert FR.face_at(faces, 0, FPS) is None and FR.face_at(faces, 75, FPS) is None


def test_rings_on_a_named_hero_must_be_centred_on_him_and_rings_over_a_close_up_fail():
    ring = {"kind": "highlight", "shot": "SH1", "picture": "pic", "at": "Bob", "pos": [0.7, 0.5], "start": 0.2, "end": 1.0,
            "start_frame": 6, "end_frame": 30}
    t = _timed([_shot("SH1", 0.0, 3.0)], [ring])
    assert "FR-RING-HERO" in _rules(FR.check(t))  # 0.1 below his point: 0.96 of the ring's height off centre
    t = _timed([_shot("SH1", 0.0, 3.0)], [dict(ring, pos=[0.7, 0.42])])
    assert not _rules(FR.check(t))
    t = _timed([_shot("SH1", 0.0, 3.0)], [dict(ring, at="the papers", pos=[0.5, 0.8])])
    assert "FR-RING-LOOK" in _rules(FR.check(t), "REVIEW")  # no prop points in the data: Claude looks at the sheet
    t = _timed([_shot("SH1", 0.0, 3.0)], [dict(ring, pos=[0.7, 0.42]), _face("SH1", "ann", "smug", 0.1, 3.0)])
    assert "FR-RING-FACE" in _rules(FR.check(t))


def test_faces_swapping_faster_than_the_window_allows_are_a_review():
    beats = [_face("SH1", "ann" if k % 2 == 0 else "bob", "joyful", 0.3 + 0.8 * k, 0.3 + 0.8 * (k + 1)) for k in range(6)]
    found = FR.check(_timed([_shot("SH1", 0.0, 6.0)], beats))
    assert "FR-FACE-RATE" in _rules(found, "REVIEW")
    assert not _rules(found)


def test_a_planned_shot_is_read_from_its_view_plan_like_the_renderer():
    # the old eased path: ann's close-up eases in under a bubble that started on the scene (FAIL). The same shot with the view
    # plan timing writes (shots[].views, production/faces.views): ann's close-up holds the whole shot, so the bubble starts
    # and ends on one frame, over its own speaker, and nothing cross-fades near the cut (no FR-FACE-GHOST)
    shot = _shot("SH1", 0.0, 4.0, bubbles=[("ann", "You can still build things?", 0.3, 2.0)])
    beats = [_face("SH1", "ann", "curious", 1.2, 4.0)]
    assert "FR-BUBBLE-FACE" in _rules(FR.check(_timed([shot], beats)))
    planned = dict(shot, views=[{"start_frame": 0, "end_frame": 120, "who": "ann"}])
    found = FR.check(_timed([planned], beats))
    assert not _rules(found) and not _rules(found, "REVIEW") & {"FR-FACE-GHOST", "FR-BUBBLE-WHO"}
    views = planned["views"]
    assert FR.face_at(beats, 0, FPS, views) == ("ann", "curious")  # the view shows the expression it is about to need
    scene = [{"start_frame": 0, "end_frame": 60, "who": None}, {"start_frame": 60, "end_frame": 120, "who": "ann"}]
    assert FR.face_at(beats, 59, FPS, scene) is None and FR.face_at(beats, 60, FPS, scene) == ("ann", "curious")
    _, runs = FR.face_track(_timed([dict(shot, views=scene)], beats), None)
    assert [r["start_frame"] for r in runs] == [0, 60]  # the face frame changes exactly where the view does
