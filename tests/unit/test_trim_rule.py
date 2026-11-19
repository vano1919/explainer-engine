"""V4.1 Step 1.2 (D-139, MA-06): one trim rule from the clip's own sound. A word counts only where a voice is heard (voicing
classifier, not band energy), its times are clamped to the voiced span, and the ingest cut and ``whisper_edit_points`` use the
same filters. Synthetic adversarial cases only: the verdicts on the six real 1914 clips wait for the blind listen (amendments
v1.1). ``speech_spans`` (band energy) is NOT a voice detector and is not what decides here."""
import sys
import types

import numpy as np

from explainer_engine.videolane import ingest as I

R = 16000
RNG = np.random.default_rng(7)


def _db(x):
    return 10 ** (x / 20)


def noise(dur, lvl):
    x = RNG.standard_normal(int(dur * R))
    return x / np.std(x) * _db(lvl)


def lowpass(x, fc):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1 / R) > fc] = 0
    return np.fft.irfft(X, len(x))


def voice(dur, lvl=-20, f0=120):
    t = np.arange(int(dur * R)) / R
    ph = 2 * np.pi * np.cumsum(f0 * (1 + 0.03 * np.sin(2 * np.pi * 5 * t))) / R
    x = sum(np.sin(k * ph) / k for k in range(1, 12)) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t) ** 2)
    return x / np.max(np.abs(x)) * _db(lvl) * 1.4


def gunshot(lvl=-6, dur=0.4):
    t = np.arange(int(dur * R)) / R
    return noise(dur, 0) * np.exp(-t / 0.04) * _db(lvl)


def place(total, parts):
    x = np.zeros(int(total * R))
    for t0, s in parts:
        a = int(t0 * R)
        x[a:a + len(s)] += s[:len(x) - a]
    return x


def W(text, a, b):
    return {"text": text, "word": text, "start": a, "end": b}


def test_a_voice_is_found_where_it_sounds_and_the_detector_is_named():
    x = place(4, [(0, noise(4, -62)), (1.0, voice(1.5))])
    spans, name = I.voiced_spans(x, R)
    assert name == "harmonicity" and len(spans) == 1
    assert abs(spans[0][0] - 1.0) < 0.06 and abs(spans[0][1] - 2.5) < 0.06


def test_a_gunshot_with_a_hallucinated_word_is_no_speech():
    x = place(4, [(0, noise(4, -62)), (1.0, gunshot()), (2.0, gunshot())])
    acc = I.accept_voiced_words([W("BANG!", 0.95, 1.4), W("BANG!", 1.95, 2.4)], x, R)
    assert acc["kept"] == [] and len(acc["rejected"]) == 2 and acc["voiced"] == []


def test_steady_loud_ambience_is_no_speech_and_a_word_over_it_is_rejected():
    for fc in (3000, 400):   # a hiss and a low wind
        x = lowpass(noise(6, -22), fc)
        acc = I.accept_voiced_words([W("You", 2.9, 4.3)], x, R)
        assert acc["kept"] == [], fc


def test_quiet_speech_over_a_low_floor_is_heard_and_loud_ambience_does_not_hide_a_voice():
    quiet = place(4, [(0, noise(4, -68)), (1.0, voice(1.5, lvl=-40))])
    assert I.accept_voiced_words([W("Hello", 1.0, 2.4)], quiet, R)["kept"]
    amb = place(6, [(0, lowpass(noise(6, -30), 3000)), (2.0, voice(2.0, lvl=-18))])
    got = I.accept_voiced_words([W("Hello", 2.0, 3.9)], amb, R)["kept"]
    assert got and abs(got[0]["start"] - 2.0) < 0.08


def test_a_zero_speech_clip_keeps_no_word_and_adds_no_span():
    x = noise(4, -62)
    d = I.trim_decision([], [W("Stand", 1.0, 1.4), W("to.", 1.4, 1.8)], "Stand to.", spoken=True, dur=4.0, audio=x, rate=R)
    assert d["spans"] == [] and len(d["rejected"]) == 2 and d["detector"] == "harmonicity"


def test_a_word_dated_far_before_the_sound_is_clamped_to_the_voiced_span_and_never_keeps_the_raw_start():
    """S03_SH007-like: "Oh, my God" dated 0.00-2.8 s over a floor whose only event is a voice at 2.4-2.8 s."""
    x = place(4, [(0, noise(4, -62)), (2.4, voice(0.4))])
    got = I.accept_voiced_words([W("Oh,", 0.0, 0.9), W("my", 0.9, 1.4), W("God", 1.4, 2.8)], x, R)
    assert [k["text"] for k in got["kept"]] == ["God"]
    assert got["kept"][0]["raw_start"] == 1.4 and got["kept"][0]["start"] >= 2.35
    assert {r["text"] for r in got["rejected"]} == {"Oh,", "my"}


def test_the_trim_adds_only_voiced_words_and_marks_the_tail_after_the_last_voiced_word():
    x = place(8, [(0, noise(8, -62)), (1.0, voice(1.0)), (6.0, gunshot())])
    words = [W("Stand", 1.0, 1.5), W("to.", 1.5, 2.0), W("BANG", 6.0, 6.4)]
    d = I.trim_decision([], words, "Stand to. BANG", spoken=True, dur=8.0, audio=x, rate=R)
    assert len(d["spans"]) == 1 and abs(d["spans"][0][0] - 1.0) < 0.1 and d["spans"][0][1] < 2.1
    assert [r["text"] for r in d["rejected"]] == ["BANG"] and abs(d["mute_tail_from_s"] - (2.0 + I.MUTE_TAIL_AFTER_S)) < 0.1
    assert I.speech_with_words([], words, "Stand to. BANG", spoken=True, dur=8.0, audio=x, rate=R) == d["spans"]


def test_a_silent_shot_is_cut_as_before_and_no_audio_means_no_word_is_added():
    detector = [(1.0, 2.0)]
    words = [W("Stand", 1.0, 1.5)]
    assert I.trim_decision(detector, words, "Stand", spoken=False, dur=4.0, audio=noise(4, -50), rate=R)["spans"] == detector
    d = I.trim_decision(detector, words, "Stand", spoken=True, dur=4.0, audio=None, rate=R)
    assert d["spans"] == detector and d["detector"] == "none"


def test_the_ingest_cut_and_whisper_edit_points_share_the_same_filters():
    maybe = [W("Maybe.", 0.0, 0.6), W("Maybe.", 1.72, 1.92)]
    assert I.drop_word_artifacts(maybe)[0] == maybe[1:]                               # the duplicate opening word
    tail = [W("Stand", 1.0, 1.5), W("You", 4.0, 4.3)]
    clean, mute = I.drop_word_artifacts(tail)
    assert [w["text"] for w in clean] == ["Stand"] and mute == round(1.5 + I.MUTE_TAIL_AFTER_S, 3)
    script = {"shots": [{"shot_id": "S1", "route": "video", "audio_line_ids": ["L"]}],
              "audio_lines": [{"line_id": "L", "speaker_type": "character", "speaker_id": "a", "text": "Stand"}]}
    doc = {"clips": {"S1": {"duration": 6.0, "words": tail}}}
    ep = I.whisper_edit_points(doc, script)["clips"]["S1"]
    assert ep["mute_tail_from_s"] == mute and ep["detector"] == "none"                # no audio given: said so
    x = place(6, [(0, noise(6, -62)), (1.0, voice(0.5)), (4.0, gunshot())])
    ep2 = I.whisper_edit_points(doc, script, audio_by_shot={"S1": (x, R)})["clips"]["S1"]
    assert ep2["detector"] == "harmonicity" and abs(ep2["speech_start_s"] - 1.0) < 0.1


def test_a_clip_whose_words_have_no_voice_under_them_is_marked_so_not_cut_on_invented_words():
    script = {"shots": [{"shot_id": "S1", "route": "video", "audio_line_ids": ["L"]}],
              "audio_lines": [{"line_id": "L", "speaker_type": "character", "speaker_id": "a", "text": "I'll see you next time"}]}
    doc = {"clips": {"S1": {"duration": 8.0, "words": [W("I'll", 0.0, 1.0), W("see", 1.0, 2.0), W("next", 2.0, 7.64)]}}}
    x = place(8, [(0, noise(8, -62)), (7.8, gunshot(dur=0.15))])
    ep = I.whisper_edit_points(doc, script, audio_by_shot={"S1": (x, R)})["clips"]["S1"]
    assert ep["no_voice_heard"] is True and ep["rejected_words"]


def test_silero_vad_is_used_when_installed_and_the_record_says_so(monkeypatch):
    vad = types.ModuleType("faster_whisper.vad")
    vad.VadOptions = lambda **kw: kw
    vad.get_speech_timestamps = lambda audio, opts, sampling_rate=16000: [{"start": int(1.0 * 16000), "end": int(2.0 * 16000)}]
    fw = types.ModuleType("faster_whisper")
    fw.vad = vad
    monkeypatch.setitem(sys.modules, "faster_whisper", fw)
    monkeypatch.setitem(sys.modules, "faster_whisper.vad", vad)
    spans, name = I.voiced_spans(np.zeros(4 * R, np.float32), R)
    assert name == "silero_vad" and spans == [(1.0, 2.0)]
    acc = I.accept_voiced_words([W("Hi", 0.2, 0.6), W("there", 1.2, 1.8)], np.zeros(4 * R, np.float32), R)
    assert acc["detector"] == "silero_vad" and [k["text"] for k in acc["kept"]] == ["there"]


def test_the_clip_record_names_the_detector_and_the_muted_tail(tmp_path):
    """Real ffmpeg media (the video lane's own synthetic clip): a hallucinated trailing "You" over a gunshot is dropped; the
    record says which voicing check ran and where the tail is muted."""
    from tests.unit import test_videolane_media as M
    rate = M.RATE
    t = np.arange(int(rate * 1.2)) / rate
    v = sum(np.sin(2 * np.pi * 120 * k * t) / k for k in range(1, 12)) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t) ** 2)
    audio = np.zeros(int(5.0 * rate), np.float32)
    audio[int(0.8 * rate):int(0.8 * rate) + len(v)] = (0.2 * v / np.abs(v).max()).astype(np.float32)
    g = np.random.default_rng(3).standard_normal(int(0.3 * rate)) * np.exp(-np.arange(int(0.3 * rate)) / rate / 0.04)
    audio[int(4.0 * rate):int(4.0 * rate) + len(g)] += (0.5 * g / np.abs(g).max()).astype(np.float32)
    raw = M.write_clip(tmp_path / "C_raw.mp4", M.moving(120, 1.0), fps=24, audio=audio)
    words = [{"text": "Three", "start": 0.8, "end": 1.3}, {"text": "days", "start": 1.3, "end": 2.0},
             {"text": "You", "start": 4.0, "end": 4.3}]
    doc = M.scene_script()
    rec = I.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "C", "path": str(raw)}], M.FPS, words_fn=lambda p: words)[0]
    assert rec["speech_detector"] == "harmonicity" and rec["mute_tail_from_s"] == round(2.0 + I.MUTE_TAIL_AFTER_S, 3)
    assert rec["speech_words"] == "local whisper"
