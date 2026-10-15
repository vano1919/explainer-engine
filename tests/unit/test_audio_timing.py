"""Word alignment from phoneme timings, the talking mouth, and the loudness fallback.
Adapted from vano1919/tmr-video-script-engine@d88ba8f: tests/unit/test_timings.py, test_celestial.py (viseme part),
test_character.py."""

from __future__ import annotations

import wave

import numpy as np

from explainer_engine.audio import envelope, timings as tm, visemes


def _timed(words: list[str], step: float = 0.1, gap: float = 0.1, start: float = 0.1) -> list[list]:
    """Fake Kokoro timings: one token per character, a space token between words; '.' closes a sentence."""
    out, t = [], start
    for i, word in enumerate(words):
        for ch in word:
            out.append([ch, round(t, 3), round(t + step, 3)])
            t += step
        if i < len(words) - 1:
            out.append([" ", round(t, 3), round(t + gap, 3)])
            t += gap
    return out


def _phones(word_specs: list[tuple[str, float]]) -> list[list]:
    out = []
    for text, t in word_specs:
        for ch in text:
            out.append([ch, round(t, 3), round(t + 0.1, 3)])
            t += 0.1
    return out


def test_one_to_one_words_take_their_phoneme_times():
    words = tm.align("Hello there.", _timed(["hɛloʊ", "ðɛɹ."]))
    assert [w["w"] for w in words] == ["Hello", "there."]
    assert words[0]["s"] == 0.1 and words[0]["e"] == 0.6
    assert words[1]["s"] == 0.7


def test_an_acronym_spoken_as_one_phoneme_word_keeps_the_words_in_order():
    timings = _timed(["ɐmazən", "eɪdʌbəljuːɛs", "tʃɑːdʒᵻz."])
    words = tm.align("Amazon AWS charges.", timings)
    assert [w["w"] for w in words] == ["Amazon", "AWS", "charges."]
    assert words[0]["s"] < words[1]["s"] < words[2]["s"]
    assert words[1]["s"] == tm.phoneme_words(timings)[1]["start"]  # snapped to the phoneme word boundary


def test_numbers_spoken_as_several_words_stay_one_written_word():
    timings = _timed(["tuː", "pɔɪnt", "faɪv", "sɛnts."])
    words = tm.align("2.5 cents.", timings)
    assert [w["w"] for w in words] == ["2.5", "cents."]
    assert abs(words[1]["s"] - tm.phoneme_words(timings)[3]["start"]) < 1e-6


def test_sentence_marks_anchor_each_sentence():
    timings = _timed(["wʌn.", "tuː", "θɹiː."])
    words = tm.align("One. Two three.", timings)
    assert [w["s"] for w in words] == [w["start"] for w in tm.phoneme_words(timings)]


def test_estimate_shares_a_clip_by_word_length():
    words = tm.estimate("a longer word", 3.0)
    assert words[0]["s"] == 0.0 and abs(words[-1]["e"] - 3.0) < 1e-3
    assert words[1]["e"] - words[1]["s"] > words[0]["e"] - words[0]["s"]


def test_mouth_shapes_follow_the_phonemes():
    assert visemes.shape_of("u") == "talk_o" and visemes.shape_of("æ") == "talk_e" and visemes.shape_of("m") == "neutral"
    assert visemes.shape_of("t") is None  # a consonant keeps the vowel's shape
    assert visemes.opening_of("ɑ") == 1.0 > visemes.opening_of("ə") > visemes.opening_of("i") > visemes.opening_of("t") > 0.0
    assert visemes.opening_of("m") == 0.0 == visemes.opening_of(" ") and visemes.opening_of("ː") is None


def test_the_mouth_glides_open_and_shut_with_the_sounds():
    phones = _phones([("ɡuːd", 1.0), ("mɑːn", 2.0)])
    opening, shape = visemes.mouth_open(phones, 30.0, 0, 120)
    assert opening[0] == 0.0 and opening[int(1.6 * 30)] == 0.0  # silence closes the mouth
    assert shape[int(1.15 * 30)] == "talk_o" and shape[int(2.2 * 30)] == "talk_e"
    assert opening[int(2.2 * 30)] > 0.9  # a long wide vowel opens it fully
    assert max(abs(a - b) for a, b in zip(opening, opening[1:])) < 0.6  # it glides: never shut to wide in one frame


def test_the_mouth_depends_only_on_the_frame_time():
    phones = _phones([("hɛloʊ", 0.5), ("wɜːld", 1.2)])
    whole, _ = visemes.mouth_open(phones, 30.0, 0, 90)
    part, _ = visemes.mouth_open(phones, 30.0, 40, 20)
    assert part == whole[40:60]  # any scene chunk renders the same mouth as the full timeline


def test_blinks_wait_for_a_silence():
    phones = _phones([("a" * 200, 0.0)])  # 20 s of speech
    for a, b in visemes.blinks("seed", 40.0, phones):
        assert a >= 20.0 or b <= 0.0  # never while a word is spoken


def test_emphasis_at_most_once_per_sentence():
    phones = [["ˈ", 1.0, 1.1], ["a", 1.1, 1.3], ["ˈ", 1.5, 1.6], ["o", 1.6, 1.8], ["ˈ", 5.0, 5.1], ["e", 5.1, 5.3]]
    times = visemes.emphasis(phones, lambda t: 1.0, sentence_ends=[2.0, 6.0], share=1.0)
    assert times == [1.1, 5.1] or times == [1.6, 5.1]
    assert visemes.tilt_at(1.1 + 0.27, [1.1]) > visemes.tilt_at(0.5, [1.1]) + 1.0


def test_loudness_mouth_moves_only_while_speaking_and_never_flutters():
    levels = [0.0] * 24 + [0.2, 0.05, 0.2, 0.2, 0.05, 0.05] * 4 + [0.0] * 12
    speaking = [False] * 24 + [True] * 24 + [False] * 12
    states = envelope.mouth_states(levels, speaking)
    assert set(states[:24]) == {0} and set(states[-12:]) == {0} and max(states[24:48]) > 0
    runs, k = [], 0
    while k < len(states):
        j = k
        while j < len(states) and states[j] == states[k]:
            j += 1
        runs.append(j - k)
        k = j
    assert min(runs[1:-1]) >= 2  # every inner state lasts at least two steps


def test_envelope_measures_a_wav_in_twelfths(tmp_path):
    rate = 24000
    tone = (0.5 * np.sin(2 * np.pi * 220 * np.arange(rate) / rate) * 32767).astype(np.int16)
    silence = np.zeros(rate, np.int16)
    path = tmp_path / "v.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate([tone, silence]).tobytes())
    levels = envelope.envelope(path)
    assert len(levels) == 24
    assert min(levels[:12]) > 0.3 and max(levels[12:]) == 0.0
