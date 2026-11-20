"""W2: validators for mix, edit, color, subtitles and shorts: a passing and a failing fixture per rule; critic rules never PASS."""
from __future__ import annotations

import numpy as np

from explainer_engine.qa import gates as G
from explainer_engine.validators import color as K
from explainer_engine.validators import edit as E
from explainer_engine.validators import mix as M
from explainer_engine.validators import shorts as SH
from explainer_engine.validators import subtitles as SUB


def _st(rows):
    rows = rows if isinstance(rows, list) else [rows]
    return [r["status"] for r in rows]


def _gates(rows):
    return {r["gate"].split(":")[0] for r in rows}


# --- mix ------------------------------------------------------------------------------------------------------------------

def test_loudness_bands():
    assert M.loudness({"lufs": -14.2})["status"] == G.PASS
    assert M.loudness({"lufs": -14.8})["status"] == G.REVIEW           # inside BP-50's band, outside BP-208's tight band
    assert M.loudness({"lufs": -18.0})["status"] == G.FAIL             # outside BP-50's binding band
    assert M.loudness({})["status"] == G.NOT_RUN


def test_true_peak():
    assert M.true_peak({"true_peak": -1.5})["status"] == G.PASS
    assert M.true_peak({"true_peak": -0.2})["status"] == G.FAIL
    assert M.true_peak({})["status"] == G.NOT_RUN


def test_voice_over_music_gap():
    assert M.voice_over_music({"voice_lufs": -16, "music_lufs": -28})["status"] == G.PASS   # 12 LU
    assert M.voice_over_music({"voice_lufs": -16, "music_lufs": -26})["status"] == G.REVIEW  # 10 LU
    assert M.voice_over_music({"voice_lufs": -16})["status"] == G.NOT_RUN


def test_three_effects_per_scene():
    assert _st(M.effects_per_scene([{"scene_id": "A", "effects": [1, 2, 3]}])) == [G.PASS]
    assert _st(M.effects_per_scene([{"scene_id": "A", "effects": [1, 2]}])) == [G.REVIEW]
    assert _st(M.effects_per_scene([])) == [G.NOT_RUN]


def test_one_continuous_bed():
    assert M.one_continuous_bed([{"start": 0, "end": 60}], 60)["status"] == G.PASS
    assert M.one_continuous_bed([{"start": 0, "end": 30}, {"start": 30, "end": 60}], 60)["status"] == G.REVIEW   # two layers
    assert M.one_continuous_bed([{"start": 5, "end": 60}], 60)["status"] == G.REVIEW                             # gap at the start
    assert M.one_continuous_bed([], 60)["status"] == G.NOT_RUN


def test_mix_critic_rows_and_the_aggregate():
    layers = [{"id": "n", "colour": "encoded"}, {"id": "x"}]
    r = M.encoded_embodied(layers)
    assert r["status"] == G.REVIEW and r["measured"]["missing"] == ["colour of layer x"]
    assert M.motifs([{"owner": "kael", "motif": "horn"}, {"owner": "sena"}])["measured"]["missing"] == ["motif of sena"]
    rows = M.check_measurements({"lufs": -14.0, "true_peak": -1.2, "voice_lufs": -16, "music_lufs": -30},
                                scenes=[{"effects": [1, 2, 3]}], beds=[{"start": 0, "end": 10}], duration_s=10,
                                layers=layers, owners=[{"owner": "a", "motif": "m"}])
    assert _gates(rows) == set(M.RULE_IDS)


def test_mix_check_file_is_not_run_without_ffmpeg(monkeypatch):
    monkeypatch.setattr("explainer_engine.validators.mix.shutil.which", lambda _: None)
    assert _st(M.check_file("x.wav")) == [G.NOT_RUN, G.NOT_RUN]


# --- edit -----------------------------------------------------------------------------------------------------------------

def test_cut_lands_after_onset():
    assert _st(E.cut_after_onset([{"cut_id": "c1", "cut_frame": 103, "motion_onset_frame": 100}])) == [G.PASS]
    assert _st(E.cut_after_onset([{"cut_id": "c1", "cut_frame": 101, "motion_onset_frame": 100}])) == [G.REVIEW]
    assert _st(E.cut_after_onset([{"cut_id": "c1", "cut_frame": 101}])) == [G.NOT_RUN]


def test_handles():
    assert _st(E.handles([{"shot_id": "a", "handle_in_frames": 12, "handle_out_frames": 16}])) == [G.PASS]
    assert _st(E.handles([{"shot_id": "a", "handle_in_frames": 4, "handle_out_frames": 16}])) == [G.REVIEW]
    assert _st(E.handles([{"shot_id": "a"}])) == [G.NOT_RUN]


def test_occlusion_wipe_is_an_eye_row():
    ok = E.occlusion_wipes([{"shot_id": "a", "type": "occlusion_wipe", "invisible": True, "silhouette_crosses_lens": True}])
    bad = E.occlusion_wipes([{"shot_id": "a", "type": "occlusion_wipe", "invisible": False}])
    assert ok["status"] == bad["status"] == G.REVIEW
    assert ok["measured"]["missing"] == [] and bad["measured"]["missing"] == ["invisible/silhouette_crosses_lens on a"]


def test_accent_durations():
    good = [{"type": "whip", "frames": 9}, {"type": "speed_ramp", "speeds": [1.0, 1.6, 0.45], "seconds": 0.6},
            {"type": "rack_focus", "seconds": 0.4}]
    assert _st(E.accents(good)) == [G.PASS] * 3
    bad = [{"type": "whip", "frames": 20}, {"type": "speed_ramp", "speeds": [1.0, 2.0], "seconds": 0.6}, {"type": "rack_focus", "seconds": 1.2}]
    assert _st(E.accents(bad)) == [G.REVIEW] * 3
    assert _st(E.accents([])) == [G.NOT_RUN]


def test_graphic_easing():
    ok = {"id": "g", "enter_ease": "ease_out", "exit_ease": "ease_in", "enter_ms": 300, "exit_ms": 200}
    assert _st(E.graphic_easing([ok])) == [G.PASS]
    assert _st(E.graphic_easing([dict(ok, enter_ease="linear")])) == [G.REVIEW]
    assert _st(E.graphic_easing([dict(ok, exit_ms=900)])) == [G.REVIEW]
    assert _st(E.graphic_easing([])) == [G.NOT_RUN]


def test_counters_tick_and_land_on_the_spoken_number():
    ok = {"id": "c", "steps_per_s": 8, "lands_at_s": 10.05, "word_start_s": 10.0}
    assert _st(E.counters([ok])) == [G.PASS]
    assert _st(E.counters([dict(ok, steps_per_s=30)])) == [G.REVIEW]
    assert _st(E.counters([dict(ok, lands_at_s=9.9)])) == [G.REVIEW]     # lands 100 ms early: early is worse than late
    assert _st(E.counters([dict(ok, lands_at_s=10.4)])) == [G.REVIEW]    # 400 ms late
    assert _st(E.counters([{"id": "c"}])) == [G.NOT_RUN]


def test_at_most_one_graphic_moves_at_a_time():
    assert E.moving_elements([{"start": 0, "end": 1}, {"start": 1, "end": 2}])["status"] == G.PASS
    assert E.moving_elements([{"start": 0, "end": 2}, {"start": 1, "end": 3}])["status"] == G.REVIEW
    assert E.moving_elements([])["status"] == G.NOT_RUN


def test_edit_critic_rows_never_pass_and_name_missing_fields():
    full = {"cuts": [{"rule_of_six": "emotion", "reason": "reaction"}], "segments": [{"intensity": 3}], "beats": [{"new_information": "5,000"}],
            "frames": [{"focus": "map"}], "captions": {"burned": False}, "chapter_cards": ["I"], "first_30s_names_and_sides": True,
            "host_shots": [{"acts": True}]}
    rows = E.critic_rows(full)
    assert len(rows) == 9 and all(r["status"] == G.REVIEW and r["measured"]["missing"] == [] for r in rows)
    empty = E.critic_rows({"cuts": [{}], "segments": [{}], "beats": [{}], "frames": [{}], "host_shots": [{}]})
    assert all(r["status"] == G.REVIEW and r["measured"]["missing"] for r in empty)
    assert _gates(E.validate({**full, "cuts": [{"cut_id": "a", "cut_frame": 3, "motion_onset_frame": 0, "rule_of_six": "x", "reason": "y"}]})) \
        >= set(E.RULE_IDS) - {"CRAFT-EDC-04", "CRAFT-EDC-06", "CRAFT-EDC-08", "CRAFT-MOG-01", "CRAFT-MOG-02", "CRAFT-MOG-03"}


# --- color ----------------------------------------------------------------------------------------------------------------

def _img(rgb, noise=0.0):
    a = np.full((16, 16, 3), rgb, dtype=np.float64)
    if noise:
        a += np.random.default_rng(1).normal(0, noise, a.shape)
    return np.clip(a, 0, 255).astype(np.uint8)


def test_boundary_frame_within_a_bounded_transfer_of_the_master():
    master = _img((120, 100, 80), 12)
    assert K.boundary_vs_master(_img((122, 101, 80), 12), master)["status"] == G.PASS
    assert K.boundary_vs_master(_img((20, 40, 200), 12), master)["status"] == G.REVIEW
    assert K.boundary_vs_master(_img((120, 100, 80), 0.5), master)["status"] == G.REVIEW   # spread collapsed


def test_hero_swatches_stay_in_a_delta_e_band():
    sheet = {"cloak": (150, 110, 70), "skin": (224, 172, 105)}
    ok = K.hero_swatches(sheet, {"cloak": [(152, 110, 72), (148, 108, 70)], "skin": [(222, 170, 104)]})
    assert _st(ok) == [G.PASS, G.PASS]
    bad = K.hero_swatches(sheet, {"cloak": [(60, 60, 200)], "skin": []})
    assert _st(bad) == [G.REVIEW, G.NOT_RUN]
    assert K.delta_e((10, 20, 30), (10, 20, 30)) == 0.0


# --- subtitles ------------------------------------------------------------------------------------------------------------

def test_caption_line_length_and_reading_speed():
    ok = [{"start": 0.0, "end": 2.0, "text": "Eight billion people\nalive today."}]
    assert _st(SUB.validate(ok)) == [G.PASS, G.PASS]
    long = [{"start": 0.0, "end": 9.0, "text": "x" * 43}]
    assert _st(SUB.chars_per_line(long)) == [G.REVIEW]        # BP-210 is a hypothesis: a miss is REVIEW, never BLOCK
    fast = [{"start": 0.0, "end": 1.0, "text": "y" * 30}]
    assert SUB.reading_speed(fast)["status"] == G.REVIEW
    assert SUB.chars_per_line([])["status"] == G.NOT_RUN
    assert {r["gate"] for r in SUB.validate(ok)} == set(SUB.RULE_IDS)


def test_srt_parsing():
    srt = "1\n00:00:00,000 --> 00:00:02,000\nHello there\nfriend\n\n2\n00:00:02,000 --> 00:00:03,500\nBye\n"
    cues = SUB.parse_srt(srt)
    assert cues == [{"start": 0.0, "end": 2.0, "text": "Hello there\nfriend"}, {"start": 2.0, "end": 3.5, "text": "Bye"}]
    assert _st(SUB.validate(srt)) == [G.PASS, G.PASS]


# --- shorts ---------------------------------------------------------------------------------------------------------------

def test_a_short_stays_inside_the_limit():
    assert SH.short_length(25)["status"] == G.PASS
    assert SH.short_length(40)["status"] == G.REVIEW        # inside the 180 s limit, outside BP-12's bands
    assert SH.short_length(200)["status"] == G.REVIEW         # BP-137 is a hypothesis: over the limit is REVIEW, not BLOCK
    assert SH.short_length(None)["status"] == G.NOT_RUN


def test_packaging_promise_is_a_critic_row():
    ok = SH.promise_paid({"promise": "What if Rome met Westeros", "first_seconds_text": "Rome has one problem."})
    bad = SH.promise_paid({"promise": "x"})
    assert ok["status"] == bad["status"] == G.REVIEW
    assert ok["measured"]["missing"] == [] and bad["measured"]["missing"] == ["first_seconds_text"]
    assert {r["gate"].split(":")[0] for r in SH.validate({"promise": "p", "first_seconds_text": "t"}, [25])} == set(SH.RULE_IDS)
