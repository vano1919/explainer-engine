"""Shorts carry the same visual-beat layer as the long video (SS-09, PV-44; measured 2026-10-19: viewers stay past the hook
but likes per view are 0.4-1.0 % and the Shorts showed 1.4 changes every 10 s): the VB lint and cadence check run on every
Short on its own estimated read, and production/shorts.py draws the beats and mixes their cues the way assemble does."""
import copy

import numpy as np
from PIL import Image

from explainer_engine.production import assemble as ASM
from explainer_engine.production import beats as BEATS
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import shorts as SHORTS
from explainer_engine.production import validate as V

from test_visual_beats import _b, beats_doc


def short_doc_with_beats() -> dict:
    """beats_doc() with one Short: a hook, two lines of the video (their beats come with them) and a pointer."""
    d = beats_doc()
    s1, s2 = d["segments"][0]["lines"], d["segments"][1]["lines"]
    d["shorts"] = [{"id": "SH01", "hook": "Could they survive the night?", "style": "fact_bomb", "ending": "pointer", "lines": [
        {"text": "Could they survive the night?",
         "visual_beats": [_b("survive", "symbol", "asks if they survive", "blip", symbol="question", pos=[0.5, 0.2]),
                          _b("night", "symbol", "the night: a clock", "tick", symbol="clock")]},
        copy.deepcopy(s1[1]), copy.deepcopy(s2[1]),
        {"text": "The full video is on the channel.",
         "visual_beats": [_b("full video", "text", "points to the full video", "pop", text="FULL VIDEO"),
                          _b("channel", "symbol", "on the channel: go", "chime", symbol="check")]}],
        "shots": [{"at": "Could", "picture": "valley", "crop_x": 0.5}, {"at": "night", "picture": "camp", "crop_x": 0.4},
                  {"at": "Oh.", "picture": "duo", "crop_x": 0.7}, {"at": "full video", "picture": "valley", "crop_x": 0.3}]}]
    return d


def _short(found, sev=None):
    return [f for f in found if f["rule"].startswith("PV-44") and f["where"].startswith("SH01")
            and (sev is None or f["severity"] == sev)]


def test_schema_takes_beats_on_short_lines():
    assert not S.schema_errors(short_doc_with_beats())


def test_a_short_with_its_beats_passes_and_a_long_gap_is_bp45s():
    """A Short's pace is BP-45 (a change at least every max_still_s, beats counted), not VB-01's 1.5 s metronome, which
    BP-45 superseded for Shorts (2026-10-20: this test pinned VB-01 /2 FAIL before; the gap is now PV-34 BP-45 at the
    registry's severity)."""
    from explainer_engine.standards import sourced_rules as SR
    d = short_doc_with_beats()
    assert not _short(V.short_beat_findings(d), "FAIL"), _short(V.short_beat_findings(d), "FAIL")
    found = V.check_script(C.compile_doc(d))
    assert not _short(found, "FAIL")
    assert not [f for f in found if f["rule"] == "PV-34" and f["where"] == "SH01" and "nothing changes" in f["detail"]]
    gap = copy.deepcopy(d)
    gap["shorts"][0]["lines"][1].pop("visual_beats")  # "Nobody knows, not even the bravest ..." holds one picture
    assert not [f for f in V.short_beat_findings(gap) if f["rule"] == "PV-44 VB-01"]  # no metronome on a Short
    found = V.check_script(C.compile_doc(gap))  # the validator runs BP-45 on the Short's estimated read
    hold = [f for f in found if f["rule"] == "PV-34" and f["where"] == "SH01" and "nothing changes" in f["detail"]]
    assert hold and hold[0]["severity"] == SR.rule("BP-45")["severity"], hold


def test_a_short_without_beats_fails_on_v2_and_is_quiet_on_a_legacy_script():
    d = short_doc_with_beats()
    for ln in d["shorts"][0]["lines"]:
        ln.pop("visual_beats", None)
    found = V.short_beat_findings(d)
    assert [f["where"] for f in found if f["severity"] == "FAIL"] == ["SH01"]
    d["schema"] = "production_script/1"
    assert V.short_beat_findings(d) == []


def test_short_lint_reports_by_short_and_line():
    d = short_doc_with_beats()
    d["shorts"][0]["lines"][0]["visual_beats"][0]["at"] = "dawn"  # not a word of the hook
    found = _short(V.short_beat_findings(d), "FAIL")
    assert any(f["rule"] == "PV-44 VB-03" and f["where"] == "SH01 line 1 beat 1" for f in found), found


def _timed_short(d):
    sd = BEATS.short_doc(d, d["shorts"][0])
    return SHORTS.time_short(d, d["shorts"][0], V.short_words(sd)["words"], V.short_words(sd)["duration"])


def test_time_short_places_beats_and_cues_on_the_shorts_own_shots():
    d = short_doc_with_beats()
    timed = _timed_short(d)
    assert [s["picture"] for s in timed["shots"]] == ["valley", "camp", "duo", "valley"]
    assert timed["shots"][2]["crop_x"] == 0.7 and timed["shots"][0]["start"] == 0.0
    n = sum(len(ln.get("visual_beats", [])) for ln in d["shorts"][0]["lines"])
    assert len(timed["visual_beats"]) == n and all(b["segment"] == "SH01" for b in timed["visual_beats"])
    assert len(timed["audio"]["cues"]) == sum(1 for b in timed["visual_beats"] if b["cue"]["sound"] != "none")
    bus = ASM.cue_bus(timed["audio"]["cues"], int(timed["duration"] * ASM.SR))
    assert np.abs(bus).max() > 0  # the cues the Short's read gets (shorts.with_cues)


def test_short_frame_draws_the_beats_in_9_16_without_ffmpeg():
    d = short_doc_with_beats()
    timed = _timed_short(d)
    im = Image.fromarray((np.random.default_rng(0).random((180, 320, 3)) * 120).astype(np.uint8))
    row = timed["shots"][0]
    beats = [b for b in timed["visual_beats"] if b["shot"] == row["id"]]
    sb = ASM.beats_for_shot(beats, row, timed["pictures"], {}, [])
    f = beats[0]["start_frame"] + 4
    plain = SHORTS.short_frame(im, row, f, timed["fps"], [], {}, [])
    drawn = SHORTS.short_frame(im, row, f, timed["fps"], sb, {}, [])
    again = SHORTS.short_frame(im, row, f, timed["fps"], sb, {}, [])
    assert drawn.size == (SHORTS.W, SHORTS.H)
    assert np.abs(np.asarray(drawn, dtype=int) - np.asarray(plain, dtype=int)).sum() > 0
    assert np.array_equal(np.asarray(drawn), np.asarray(again))  # deterministic


def test_crop_and_spots_stay_inside_the_short():
    row = {"id": "SH001", "crop_x": 0.9, "zoom": 1.2}
    x0, y0, x1, y1 = SHORTS.crop_box(row, 1600, 900, 0.0)
    assert 0 <= x0 < x1 <= 1600 and abs((x1 - x0) / (y1 - y0) - 9 / 16) < 1e-6
    z = SHORTS.crop_box(row, 1600, 900, 1.0)
    assert z[2] - z[0] < x1 - x0  # the push
    beats = [{"kind": "label", "pos": [0.05, 0.5], "shot": "SH001"}, {"kind": "text", "pos": [0.05, 0.5], "shot": "SH001"}]
    assert SHORTS.fit_spots(beats, row, 1600, 900) == 1
    assert x0 <= beats[0]["pos"][0] * 1600 <= x1 and beats[1]["pos"] == [0.05, 0.5]


def test_stage_guard_lets_the_beat_writer_write_short_beats_and_nothing_else():
    from explainer_engine.scripting import stage_guard as G
    before = short_doc_with_beats()
    for ln in before["shorts"][0]["lines"]:
        ln.pop("visual_beats", None)
    after = short_doc_with_beats()
    assert not G.violations("beats", before, after)
    worded = copy.deepcopy(after)
    worded["shorts"][0]["lines"][0]["text"] = "Could anyone survive the night?"
    assert G.violations("beats", before, worded)  # the beat-writer never changes a Short's words


def test_a_stat_card_is_fitted_whole_in_the_short_and_its_spots_move_with_it():
    card = Image.new("RGB", (1920, 1080), (30, 20, 60))
    card.paste((250, 250, 250), (0, 0, 1920, 60))  # the title band across the whole width
    beats = [{"shot": "SH001", "kind": "label", "pos": [0.0, 0.0]}, {"shot": "SH002", "kind": "label", "pos": [0.0, 0.0]}]
    row = {"id": "SH001", "picture": "sc_final", "crop_x": 0.2, "zoom": 1.4}
    im = SHORTS.fit_screen(card, beats, row)
    assert im.size == (SHORTS.W, SHORTS.H) and row["crop_x"] == 0.5 and row["zoom"] == 1.0
    box = SHORTS.crop_box(row, *im.size, 0.0)
    assert box[0] <= 0 + 1e-6 and box[2] >= SHORTS.W - 1e-6  # the crop shows the whole width: nothing of the card is cut
    a = np.asarray(im)
    x0 = round(SHORTS.W * SHORTS.SCREEN_MARGIN)
    y0 = (SHORTS.H - round(1080 * (SHORTS.W - 2 * x0) / 1920)) // 2
    assert a[y0 + 5, x0 + 5].min() > 200 and a[y0 + 5, SHORTS.W - x0 - 5].min() > 200  # both ends of the title band
    assert abs(beats[0]["pos"][0] * SHORTS.W - x0) < 2 and abs(beats[0]["pos"][1] * SHORTS.H - y0) < 2
    assert beats[1]["pos"] == [0.0, 0.0]  # another shot's spot stays
