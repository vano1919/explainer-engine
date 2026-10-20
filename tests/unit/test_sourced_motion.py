"""The sourced motion, text, face and rhythm rules (BP-20..BP-35, BP-40, BP-41; docs/SOURCED_RULES.md, D-59): every number a
validator enforces comes from the registry, and each check fires on a small synthetic timed script."""
import numpy as np
from PIL import Image, ImageDraw

from test_production_script import mini, words_for

from explainer_engine.edit import board as B
from explainer_engine.edit import motion_lint as M
from explainer_engine.edit import shot_rules as R
from explainer_engine.production import accents as ACC
from explainer_engine.production import continuity
from explainer_engine.production import faces as FACES
from explainer_engine.production import fill_holds as F
from explainer_engine.production import timing as T
from explainer_engine.standards import sourced_rules as SR

FPS = 30


def _shot(i, start, end, pic, motion=None, accents=(), **kw):
    s = {"id": f"SH{i:03d}", "segment": kw.pop("segment", "S01"), "picture": pic, "start": float(start), "end": float(end),
         "start_frame": int(start * FPS), "end_frame": int(end * FPS), "accents": list(accents), "bubbles": [],
         "motion": motion or {"kind": "push", "z0": 1.0, "z1": 1.06}, "transition": "cut", "text": "a quiet line of narration"}
    s.update(kw)
    return s


def _timed(shots, duration=None, **extra):
    t = {"fps": FPS, "duration": float(duration or shots[-1]["end"]), "shots": shots, "visuals": [], "cards": [],
         "visual_beats": []}
    t.update(extra)
    return t


def _acc(kind, start, **kw):
    a = {"kind": kind, "start": float(start), "start_frame": int(start * FPS), "strength": 0.6, "text": "", "pos": [0.5, 0.2]}
    a.update(kw)
    return a


def _rules(found, rule):
    return [f for f in found if f["rule"] == rule]


# --- the numbers come from the registry ---------------------------------------------------------------------------------

def test_every_enforced_number_is_read_from_the_registry():
    assert M.ENTRY_MIN_GAP == SR.T("BP-25", "entry_min_gap_s")
    assert R.MAX_ZOOM == SR.T("BP-20", "scale_max") and R.B_PUSH_MAX == SR.T("BP-20", "push_default_max")
    assert continuity.ZMAX == SR.T("BP-20", "scale_max")
    assert R.DISSOLVE_SECONDS == SR.T("BP-31", "dissolve_s")
    assert B.MAX_PER_MIN == SR.T("BP-40", "pictures_per_min_max")
    assert (B.HOOK_WINDOW, B.HOOK_STILL, B.BODY_REVIEW, B.BODY_FAIL) == tuple(
        SR.T("BP-40", k) for k in ("hook_window_s", "hook_max_still_s", "body_review_still_s", "body_fail_still_s"))
    assert B.INTERRUPT == SR.T("BP-41", "window_s")
    assert F.MAX_GAP == SR.T("BP-40", "body_review_still_s") and F.HOOK_GAP == SR.T("BP-40", "hook_max_still_s")
    assert ACC.FLASH_FRAMES == SR.T("BP-26", "flash_frames") and ACC.FLASH_WHITE == SR.T("BP-26", "flash_white_max")
    assert ACC.SHAKE_S <= SR.T("BP-24", "decay_max_s") and ACC.SHAKE_AMP <= SR.T("BP-24", "amplitude_max_h")
    lo, hi = SR.T("BP-32", "lead_frames")
    assert lo <= ACC.EXPR_LEAD_FRAMES <= hi
    assert "BP-03" in open(R.__file__, encoding="utf-8").read()  # the greetings list is BP-03's enforcement point


def test_a_hypothesis_or_house_rule_never_fails():
    for rid in ("BP-24", "BP-26", "BP-27", "BP-28"):
        assert M._sev(rid) == "REVIEW"
    assert M._sev("BP-20") == "FAIL" and M._sev("BP-31") == "FAIL" and M._sev("BP-22") == "FAIL"


# --- BP-20..23: scale, rate, pan, easing ---------------------------------------------------------------------------------

def test_bp20_scale_outside_the_band_fails_and_a_tall_push_is_a_review():
    big = _timed([_shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.3})])
    f = _rules(M.check_sourced(big), "BP-20")
    assert f and f[0]["severity"] == "FAIL"
    tall = _timed([_shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.12})])
    f = _rules(M.check_sourced(tall), "BP-20")
    assert f and f[0]["severity"] == "REVIEW" and "default push" in f[0]["detail"]
    assert not _rules(M.check_sourced(_timed([_shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.08})])), "BP-20")
    # a punch accent stacks on the move and is exempt
    punched = _timed([_shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.08}, [_acc("punch", 1.0, strength=1.0)])])
    assert not _rules(M.check_sourced(punched), "BP-20") and not _rules(M.check_sourced(punched), "BP-21")


def test_bp21_scale_rate_slow_fast_and_rushed():
    rushed = M.check_sourced(_timed([_shot(1, 0, 1, "a", {"kind": "push", "z0": 1.0, "z1": 1.12})]))
    assert any("rushed" in f["detail"] for f in _rules(rushed, "BP-21"))
    fast = _rules(M.check_sourced(_timed([_shot(1, 0, 2, "a", {"kind": "push", "z0": 1.0, "z1": 1.08})])), "BP-21")
    assert fast and "rushed" not in fast[0]["detail"] and fast[0]["severity"] == "REVIEW"
    slow = _rules(M.check_sourced(_timed([_shot(1, 0, 10, "a", {"kind": "push", "z0": 1.0, "z1": 1.02})])), "BP-21")
    assert slow and "not seen" in slow[0]["detail"]
    assert not _rules(M.check_sourced(_timed([_shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.06})])), "BP-21")
    assert not _rules(M.check_sourced(_timed([_shot(1, 0, 4, "a", {"kind": "hold", "z0": 1.0, "z1": 1.0})])), "BP-21")


def test_bp22_pan_faster_than_a_seventh_of_the_width_a_second_fails():
    fast = _rules(M.check_sourced(_timed([_shot(1, 0, 2, "a", {"kind": "pan", "z0": 1.05, "z1": 1.05, "dx": 0.5})])), "BP-22")
    assert fast and fast[0]["severity"] == "FAIL"
    calm = _timed([_shot(1, 0, 5, "a", {"kind": "pan", "z0": 1.05, "z1": 1.05, "dx": 0.06})])
    assert not _rules(M.check_sourced(calm), "BP-22")
    chained = _shot(1, 0, 1, "a", {"kind": "pan", "z0": 1.05, "z1": 1.05, "dx": 0.02},
                    render_motion={"kind": "pan", "z0": 1.05, "z1": 1.05, "x0": -0.1, "x1": 0.1, "ein": True,
                                   "eout": True})
    assert _rules(M.check_sourced(_timed([chained])), "BP-22")  # the drawn move (render_motion) is what is judged


def test_bp23_linear_or_unheld_brisk_moves_are_reviews():
    linear = _shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.06, "easing": "linear"})
    assert any("linear" in f["detail"] for f in _rules(M.check_sourced(_timed([linear])), "BP-23"))
    brisk = _shot(1, 0, 2, "a", {"kind": "push", "z0": 1.0, "z1": 1.08},
                  render_motion={"kind": "push", "z0": 1.0, "z1": 1.08, "x0": 0, "x1": 0, "ein": False, "eout": True, "chained": True})
    assert any("ease both ends" in f["detail"] for f in _rules(M.check_sourced(_timed([brisk])), "BP-23"))
    short = _shot(1, 0, 0.4, "a", {"kind": "push", "z0": 1.0, "z1": 1.04})
    assert any("hold" in f["detail"] for f in _rules(M.check_sourced(_timed([short])), "BP-23"))
    calm = _shot(1, 0, 4, "a", {"kind": "push", "z0": 1.0, "z1": 1.06},
                 render_motion={"kind": "push", "z0": 1.0, "z1": 1.06, "x0": 0, "x1": 0, "ein": False, "eout": False, "chained": True})
    assert not _rules(M.check_sourced(_timed([calm])), "BP-23")  # a slow chained move may run through the cut


# --- BP-24..28: shake, flashes, text ------------------------------------------------------------------------------------

def test_bp24_shake_needs_an_impact_word_and_stays_small_and_short():
    talk = _shot(1, 0, 4, "a", accents=[_acc("shake", 1.0)], text="they talk quietly by the fire")
    f = _rules(M.check_sourced(_timed([talk])), "BP-24")
    assert f and "impact" in f[0]["detail"] and f[0]["severity"] == "REVIEW"
    hit = _shot(1, 0, 4, "a", accents=[_acc("shake", 1.0)], text="the wall crashes down on them")
    assert not _rules(M.check_sourced(_timed([hit])), "BP-24")
    huge = _shot(1, 0, 4, "a", accents=[_acc("shake", 1.0, strength=5.0, decay_s=2.0)], text="the wall crashes down")
    found = _rules(M.check_sourced(_timed([huge])), "BP-24")
    assert any("amplitude" in f["detail"] for f in found) and any("decays" in f["detail"] for f in found)
    assert all(f["severity"] == "REVIEW" for f in found)  # a house rule never FAILs


def test_bp26_more_than_three_flashes_in_a_second_is_a_review():
    shots = [_shot(k + 1, k * 0.25, k * 0.25 + 0.25, f"p{k}", accents=[_acc("flash_in", k * 0.25)], segment=f"S{k:02d}")
             for k in range(4)]
    f = _rules(M.check_sourced(_timed(shots, 4.0)), "BP-26")
    assert f and f[0]["severity"] == "REVIEW" and "4 flashes" in f[0]["detail"]
    assert not _rules(M.check_sourced(_timed(shots[:3], 4.0)), "BP-26")
    frame = Image.new("RGB", (64, 36), (0, 0, 0))
    acc = ACC.resolve([{"kind": "flash_in"}], 0, 2, lambda p: None, FPS)
    first = np.asarray(ACC.draw(frame.copy(), acc, 0, FPS, 0, 60, None, None)).mean() / 255
    assert first <= SR.T("BP-26", "flash_white_max") + 0.01  # never whiter than the registry allows
    assert np.array_equal(np.asarray(ACC.draw(frame.copy(), acc, ACC.FLASH_FRAMES, FPS, 0, 60, None, None)), np.asarray(frame))


def test_bp27_text_holds_are_bounded_below_and_above():
    assert ACC.text_hold("Fire.") == 1.8  # P-71 stays inside BP-27's band
    assert ACC.text_hold(" ".join(["word"] * 30)) == SR.T("BP-27", "hold_max_s")
    cut = _shot(1, 0, 3, "a", accents=[_acc("pop_text", 2.8, text="ONE WORD")])
    f = _rules(M.check_sourced(_timed([cut])), "BP-27")
    assert f and "readable for" in f[0]["detail"]
    assert not _rules(M.check_sourced(_timed([_shot(1, 0, 6, "a", accents=[_acc("pop_text", 1.0, text="ONE WORD")])])), "BP-27")
    long_beat = _timed([_shot(1, 0, 12, "a")], visual_beats=[{"kind": "text", "text": "GRAIN", "start": 1.0, "end": 10.0,
                                                               "segment": "S01", "line": 1}])
    f = _rules(M.check_sourced(long_beat), "BP-27")
    assert f and "at most 7 s" in f[0]["detail"]


def test_bp28_text_outside_the_safe_area_is_a_review():
    edge = _shot(1, 0, 6, "a", accents=[_acc("pop_text", 1.0, text="EDGE", pos=[0.05, 0.2])])
    assert _rules(M.check_sourced(_timed([edge])), "BP-28")
    assert not _rules(M.check_sourced(_timed([_shot(1, 0, 6, "a", accents=[_acc("pop_text", 1.0, text="MID")])])), "BP-28")
    low = _timed([_shot(1, 0, 6, "a")], visual_beats=[{"kind": "label", "text": "LOW", "start": 1.0, "end": 3.0, "pos": [0.5, 0.97],
                                                        "segment": "S01", "line": 1}])
    assert _rules(M.check_sourced(low), "BP-28")


# --- BP-31: dissolves only on a period boundary ---------------------------------------------------------------------------

def test_bp31_dissolve_inside_a_period_fails_and_a_long_one_is_a_review():
    a, b = _shot(1, 0, 5, "a"), _shot(2, 5, 10, "b", transition="dissolve")
    f = _rules(M.check_sourced(_timed([a, b])), "BP-31")
    assert f and f[0]["severity"] == "FAIL"
    assert not _rules(M.check_sourced(_timed([a, dict(b, time_jump=True)])), "BP-31")
    assert not _rules(M.check_sourced(_timed([a, b], cards=[{"period": "p2", "start": 5.0}])), "BP-31")
    assert not _rules(M.check_sourced(_timed([dict(a, period="p1"), dict(b, period="p2")])), "BP-31")
    slow = _rules(M.check_sourced(_timed([a, dict(b, time_jump=True, transition_seconds=2.5)])), "BP-31")
    assert slow and slow[0]["severity"] == "REVIEW"


def test_timing_dissolves_at_the_registry_length_on_period_changes():
    d = mini()
    d["periods"] = [{"id": "p1"}, {"id": "p2"}]
    d["segments"][0]["period"], d["segments"][1]["period"] = "p1", "p2"
    timed = T.time_script(d, words_for(d))
    dis = [s for s in timed["shots"] if s["transition"] == "dissolve"]
    assert len(dis) == 1 and dis[0]["time_jump"] and dis[0]["transition_seconds"] == R.DISSOLVE_SECONDS
    assert not _rules(M.check_sourced(timed), "BP-31")


# --- BP-32 / BP-33: expression lead and hold ----------------------------------------------------------------------------

def _expr(start, who="einstein", expression="surprised", offset=0.0, end=None, **kw):
    b = {"kind": "expression", "who": who, "expression": expression, "at": "oh", "offset": offset, "start": start,
         "start_frame": int(round(start * FPS)), "end": start + 1.0 if end is None else end, "segment": "S02", "line": 2}
    b.update(kw)
    return b


def test_bp32_an_expression_lands_just_before_its_word_never_after():
    ok = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(2.0)])
    assert not _rules(M.check_sourced(ok), "BP-32")  # the render leads the beat by EXPR_LEAD_FRAMES
    late = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(2.2, offset=0.2)])
    f = _rules(M.check_sourced(late), "BP-32")
    assert f and "after its word" in f[0]["detail"] and f[0]["severity"] == M._sev("BP-32")
    early = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(1.5, offset=-0.5)])
    f = _rules(M.check_sourced(early), "BP-32")
    assert f and "before its word" in f[0]["detail"]


def test_bp33_expressions_hold_half_a_second_and_changes_keep_apart():
    quick = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(2.0, end=2.3), _expr(2.3, expression="curious")])
    f = _rules(M.check_sourced(quick), "BP-33")
    assert f and "apart" in f[0]["detail"]
    short = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(2.0, end=2.2)])
    f = _rules(M.check_sourced(short), "BP-33")
    assert f and "holds" in f[0]["detail"]
    fine = _timed([_shot(1, 0, 6, "duo")], visual_beats=[_expr(2.0, end=3.0), _expr(3.0, expression="curious", end=4.0)])
    assert not _rules(M.check_sourced(fine), "BP-33")


def _close_up(path, face=(210, 150, 110), bg=None, rim=None, rim_px=4, size=(60, 80)):
    im = Image.new("RGB", size, bg or FACES.key_rgb())
    d = ImageDraw.Draw(im)
    if rim:
        d.ellipse([12 - rim_px, 10 - rim_px, 48 + rim_px, 70 + rim_px], fill=rim)
    d.ellipse([12, 10, 48, 70], fill=face)
    im.save(path)
    return path


def test_the_keyed_close_up_swaps_before_the_words_frame(tmp_path):
    frame = Image.new("RGB", (320, 180), (40, 40, 60))
    a = {"start_frame": 30, "end_frame": 90, "who": "einstein", "close_up": _close_up(tmp_path / "a.png"), "face": None}
    b = dict(a, start_frame=60, close_up=_close_up(tmp_path / "b.png", face=(200, 60, 60)))  # not green: it must not key out
    lead = ACC.EXPR_LEAD_FRAMES

    def colour(f):
        px = np.asarray(FACES.composite(frame, [a, b], f, FPS, ["einstein"])).astype(int)
        return px[100, 115]

    assert abs(colour(60 - lead) - np.array([200, 60, 60])).max() < 6  # the second face already at word - lead
    assert abs(colour(60 - lead - 1) - np.array([210, 150, 110])).max() < 6  # one frame earlier the first face


# --- BP-34: the close-up against its backdrop --------------------------------------------------------------------------

def test_bp34_sticker_and_halo_are_measured_against_the_backdrop(tmp_path):
    clean = _close_up(tmp_path / "clean.png")
    dark = tmp_path / "dark.png"
    Image.new("RGB", (120, 68), (20, 30, 60)).save(dark)
    warm = tmp_path / "warm.png"
    Image.new("RGB", (120, 68), (205, 150, 115)).save(warm)
    m = FACES.composite_match(clean, dark)
    assert m["halo_px"] == 0 and abs(m["d_luma"]) > SR.T("BP-34", "luma_tolerance")
    assert abs(FACES.composite_match(clean, warm)["d_luma"]) < SR.T("BP-34", "luma_tolerance")
    found = FACES.match_findings({(clean, dark): "S02 line 2", (clean, warm): "S02 line 3"})
    assert len(found) == 1 and "sticker" in found[0]["detail"] and found[0]["severity"] == "REVIEW"
    haloed = _close_up(tmp_path / "halo.png", rim=(150, 180, 140), rim_px=4)
    assert FACES.halo_px(Image.open(haloed)) > SR.T("BP-34", "halo_px_max")
    f = FACES.match_findings({(haloed, warm): "S02 line 2"})
    assert f and "halo" in f[0]["detail"]
    assert FACES.match_findings({(tmp_path / "missing.png", warm): "x"}) == []  # missing files are skipped


def test_bp34_runs_inside_the_face_lint_when_pictures_exist(tmp_path):
    from test_visual_beats import beats_doc
    d = beats_doc()
    for e in FACES.DEFAULT_SET:
        _close_up(tmp_path / f"einstein_faces_v1_{e}.png")
    assert not [f for f in FACES.lint(d, [tmp_path]) if f["rule"] == "BP-34"]  # no picture file: nothing to compare
    Image.new("RGB", (120, 68), (20, 30, 60)).save(tmp_path / "duo.png")  # the dialogue's picture, dark and cold
    found = [f for f in FACES.lint(d, [tmp_path]) if f["rule"] == "BP-34"]
    assert found and all(f["severity"] == "REVIEW" for f in found) and "duo.png" in found[0]["detail"]


# --- BP-30: the same framing twice ---------------------------------------------------------------------------------------

def _rm(z0, z1, x0=0.0, x1=0.0):
    return {"kind": "push" if z1 > z0 else "static", "z0": z0, "z1": z1, "x0": x0, "x1": x1, "ein": True, "eout": True}


def test_bp30_same_framing_of_the_same_picture_twice_is_a_review():
    a = {"id": "SH001", "picture": "a", "render_motion": _rm(1.0, 1.06)}
    b = {"id": "SH002", "picture": "a", "render_motion": _rm(1.06, 1.06)}
    f = continuity.findings([a, b])
    assert [x["rule"] for x in f] == ["BP-30"] and f[0]["severity"] == "REVIEW"
    assert continuity.findings([a, {"id": "SH002", "picture": "a", "render_motion": _rm(1.06, 1.10)}]) == []
    assert continuity.findings([a, {"id": "SH002", "picture": "b", "render_motion": _rm(1.06, 1.06)}]) == []
    snap = {"id": "SH002", "picture": "a", "render_motion": _rm(1.0, 1.06)}
    assert [x["rule"] for x in continuity.findings([a, snap])] == ["ED-02 ZOOM-1"]  # a snap is reported once, as the snap


# --- BP-40 / BP-41: section-aware rhythm ----------------------------------------------------------------------------------

def _board_shots(spans, accents=None):
    out = []
    for k, (a, b) in enumerate(spans):
        s = {"id": f"SH{k + 1:03d}", "picture": f"p{k}", "start": float(a), "end": float(b), "cut_legal": True, "at": "x",
             "text": "", "bubbles": [], "accents": list((accents or {}).get(k, []))}
        out.append(s)
    return out


def _board(shots):
    return {"pictures": {s["picture"]: {} for s in shots}, "heroes": {}, "_event_times": {}}


def test_bp40_rhythm_is_judged_by_section():
    hook = _board_shots([(0, 6), (6, 12), (12, 18), (18, 24), (24, 30), (30, 36)])
    f = [x for x in B.check(_board(hook), {"shots": hook, "duration": 36.0}) if x["rule"] == "RHYTHM-3"]
    assert len(f) == 5 and all(x["severity"] == "FAIL" and "first 30 s" in x["detail"] for x in f)
    body = _board_shots([(0, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24), (24, 27), (27, 30),
                         (30, 55), (55, 100)])
    f = [x for x in B.check(_board(body), {"shots": body, "duration": 100.0}) if x["rule"] == "RHYTHM-3"]
    assert [x["severity"] for x in f] == ["REVIEW", "FAIL"]  # 25 s in the body is a REVIEW, 45 s a FAIL
    straddle = B.still_excess(27.0, 40.0)
    assert straddle == (3.0, 10.0) and not B.still_too_long(27.0, 40.0)
    assert B.still_too_long(0.0, 6.0) and B.still_too_long(40.0, 61.0) and not B.still_too_long(40.0, 55.0)


def test_an_accent_breaks_a_still_and_the_pattern_interrupt_is_asked_for():
    shots = _board_shots([(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24), (24, 40), (40, 44)])
    f = B.check(_board(shots), {"shots": shots, "duration": 44.0})
    assert [x["rule"] for x in f if x["rule"] in ("RHYTHM-3", "BP-41")] == ["RHYTHM-3", "BP-41"]
    with_acc = _board_shots([(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24), (24, 40), (40, 44)],
                            {6: [{"kind": "punch", "start": 28.0}, {"kind": "punch", "start": 33.0},
                                 {"kind": "wobble", "start": 24.0}]})
    f = B.check(_board(with_acc), {"shots": with_acc, "duration": 44.0})
    assert not [x for x in f if x["rule"] in ("RHYTHM-3", "BP-41")]
    assert B.change_times(with_acc, 44.0).count(24.0) == 1  # the wobble is not a change
    short = _board_shots([(0, 4), (4, 8)])
    assert not [x for x in B.check(_board(short), {"shots": short, "duration": 8.0}) if x["rule"] == "BP-41"]  # too short to ask


def test_fill_holds_follows_the_section_limits_and_stops_at_accents():
    d = mini()
    for seg in d["segments"]:
        seg["shots"] = [s for s in seg["shots"] if s.get("reuse") != "reframe"]  # the bare script: two long stills in the hook
    words = words_for(d)
    before = T.time_script(d, words)
    changes = B.change_times(before["shots"], before["duration"])
    assert any(B.still_too_long(a, b) for a, b in zip(changes, changes[1:]))
    new, inserted, stuck = F.fill_holds(d, words)
    assert inserted and all(x["start"] < B.HOOK_WINDOW for x in inserted)
    after = T.time_script(new, words)
    changes = B.change_times(after["shots"], after["duration"])
    left = [(a, b) for a, b in zip(changes, changes[1:]) if B.still_too_long(a, b)]
    assert all(any(abs(a - s["from"]) < 1e-6 for s in stuck) for a, _ in left)
    # a still the accents already break gets no filler (contradiction E3: fillers stacked on beats)
    d2 = mini()
    for seg in d2["segments"]:
        seg["shots"] = [s for s in seg["shots"] if s.get("reuse") != "reframe"]
    d2["segments"][0]["shots"][1]["accents"] = [{"kind": "punch", "at": "bravest"}, {"kind": "punch", "at": "rising"}]
    _, inserted2, _ = F.fill_holds(d2, words)
    assert all(x["segment"] != "S01" for x in inserted2)
