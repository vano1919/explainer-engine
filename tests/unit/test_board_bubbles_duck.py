"""D-42: storyboard timing and story-state checks, speech bubbles, music ducking under world sounds."""
import numpy as np
import pytest

from explainer_engine.audio import duck
from explainer_engine.edit import board as B


def _words(text: str, gap_after_punct: float = 0.4) -> list[dict]:
    out, t = [], 0.2
    for w in text.split():
        out.append({"w": w, "s": round(t, 3), "e": round(t + 0.3, 3)})
        t += 0.3 + (gap_after_punct if w[-1] in ".,!?" else 0.05)
    return out


TEXT = ("Nansen tries a bow drill. Nothing but smoke. Then Einstein takes off his glasses. Oh. A convex lens. "
        "One bright point. One careful breath, and fire! Franklin sets a night watch.")
HEROES = {"nansen": ["nansen"], "einstein": ["einstein"], "franklin": ["franklin"]}


def _board(shots, pictures=None):
    pics = {"drill": {"heroes": ["nansen"], "shows": ["smoke"]},
            "glasses": {"heroes": ["einstein"], "speakers": {"einstein": [0.6, 0.3]}},
            "camp": {"heroes": [], "shows": ["fire"]},
            "franklin_glasses": {"heroes": ["franklin"]}}
    pics.update(pictures or {})
    return {"heroes": HEROES, "events": [{"thing": "fire", "at": "and fire"}], "pictures": pics, "shots": shots}


def _build(shots, pictures=None):
    words = _words(TEXT)
    return B.build(_board(shots, pictures), {"words": words, "duration": words[-1]["e"] + 0.5})


def test_cuts_land_in_the_pause_before_the_phrase():
    timed, _ = _build([{"at": "Nansen", "picture": "drill"}, {"at": "Then Einstein", "picture": "glasses"}])
    s = timed["shots"][1]
    assert s["cut_legal"] and s["start"] < timed["shots"][1]["end"]
    assert "Then Einstein" in s["text"] and "smoke." not in s["text"]


def test_a_picture_showing_fire_before_its_word_fails():
    _, f = _build([{"at": "Nansen", "picture": "drill"}, {"at": "Then Einstein", "picture": "camp"},
                   {"at": "Franklin sets", "picture": "camp"}])
    state = [x for x in f if x["rule"] == "STATE-1"]
    assert len(state) == 1 and "fire" in state[0]["detail"]


def test_fire_on_its_own_word_passes():
    _, f = _build([{"at": "Nansen", "picture": "drill"}, {"at": "Then Einstein", "picture": "glasses"},
                   {"at": "and fire", "picture": "camp"}])
    assert not [x for x in f if x["rule"] == "STATE-1"]


def test_wrong_hero_for_the_line_fails():
    _, f = _build([{"at": "Nansen", "picture": "drill"}, {"at": "Then Einstein", "picture": "franklin_glasses"}])
    assert [x for x in f if x["rule"] == "HERO-1"]


def test_bubbles_are_timed_from_their_phrase_and_need_a_speaker():
    timed, f = _build([{"at": "Nansen", "picture": "drill"},
                       {"at": "Then Einstein", "picture": "glasses",
                        "bubbles": [{"at": "Oh.", "who": "einstein", "text": "Oh. A convex lens!"},
                                    {"at": "One bright", "who": "franklin", "text": "Careful."}]}])
    b = timed["shots"][1]["bubbles"]
    assert b[0]["start"] < b[1]["start"] <= timed["shots"][1]["end"]
    assert [x for x in f if x["rule"] == "BUBBLE-3" and "franklin" in x["detail"]]


def test_rhythm_flags_too_many_pictures_and_dead_holds():
    words = _words(" ".join([TEXT] * 6))  # about 70 s: a rate is measured over at least a minute
    many = [{"at": w["w"], "picture": "drill", "heroes_ok": True} for w in words if w["w"][0].isupper()]
    _, f = B.build(_board(many), {"words": words, "duration": words[-1]["e"]})
    assert [x for x in f if x["rule"] == "RHYTHM-1"]
    _, f2 = B.build(_board([{"at": "Nansen", "picture": "drill"}]), {"words": words, "duration": 30.0})
    assert [x for x in f2 if x["rule"] == "RHYTHM-3"]


def test_phrase_not_found_raises():
    with pytest.raises(ValueError):
        B.find_phrase(_words(TEXT), "magnifying glass")


# --- bubbles ---------------------------------------------------------------------------------------------------------

def test_bubble_pops_and_fades_and_stays_inside_the_frame():
    from PIL import Image
    from explainer_engine.finish import bubbles as BB
    b = BB.Bubble("Oh. A convex lens!", (1800, 120), 1.0, 3.0, (1920, 1080))
    x0, y0, x1, y1 = b.box
    assert x0 >= 0 and y0 >= 0 and x1 <= 1920 and y1 <= 1080
    assert b.frame_layer(0.9) is None and b.frame_layer(3.0) is None
    small, _ = b.frame_layer(1.02)
    full, _ = b.frame_layer(2.0)
    assert small.size[0] < full.size[0]
    frame = Image.new("RGB", (1920, 1080), (40, 40, 60))
    out = BB.composite(frame, [b], 2.0)
    assert out.size == frame.size and np.asarray(out).std() > np.asarray(frame).std()


def test_second_bubble_avoids_the_first():
    from explainer_engine.finish import bubbles as BB
    a = BB.Bubble("Keep the tinder dry.", (700, 400), 0, 3, (1920, 1080))
    b = BB.Bubble("A convex lens!", (900, 400), 0, 3, (1920, 1080), avoid=[a.box])
    ax0, ay0, ax1, ay1 = a.box
    bx0, by0, bx1, by1 = b.box
    assert bx1 <= ax0 or bx0 >= ax1 or by1 <= ay0 or by0 >= ay1


def test_wrap_breaks_on_sentences_and_avoids_orphans():
    from explainer_engine.finish.bubbles import wrap
    assert wrap("Keep the tinder dry. And wait.") == ["Keep the tinder dry.", "And wait."]
    lines = wrap("anyone here make fire without matches at all")
    assert len(lines[-1].split()) > 1


def test_bubble_lines_must_be_short_and_readable():
    from explainer_engine.finish.bubbles import check_bubbles
    f = check_bubbles([{"text": "one two three", "start": 0.0, "end": 0.8},
                       {"text": " ".join(["w"] * 20), "start": 0.0, "end": 9.0}])
    assert {x["rule"] for x in f} == {"BUBBLE-1", "BUBBLE-2"}


# --- ducking ---------------------------------------------------------------------------------------------------------

SR = 48000


def _hit(at: float, length: float, n: int) -> np.ndarray:
    side = np.zeros(n)
    a, b = int(at * SR), int((at + length) * SR)
    side[a:b] = 0.5 * np.sin(np.arange(b - a) * 0.3)
    return side


def test_music_dips_under_a_sound_and_comes_back():
    n = 4 * SR
    g = duck.duck_gain(_hit(1.0, 0.4, n), SR, depth_db=9)
    db = 20 * np.log10(g)
    assert db[int(0.5 * SR)] > -0.05  # before
    assert db[int(1.3 * SR)] < -8.0  # during
    assert db[int(3.5 * SR)] > -0.3  # recovered


def test_the_dip_never_steps_like_a_cut():
    n = 3 * SR
    g = duck.duck_gain(_hit(1.0, 0.05, n), SR, depth_db=12, attack_ms=20)
    assert duck.max_step_db_per_ms(g, SR) < 1.0  # 12 dB over >= 20 ms: well under a dB per millisecond


def test_quiet_sidechain_does_not_duck():
    n = 2 * SR
    g = duck.duck_gain(_hit(0.5, 0.5, n) * 0.01, SR, threshold=0.02)
    assert np.allclose(g, 1.0)


def test_bubble_keeps_the_speakers_face_clear():
    from explainer_engine.finish import bubbles as BB
    sx, sy = 1630, 400  # a speaker near the right edge, mouth at 37 % height (Nansen, Day 1)
    b = BB.Bubble("Can anyone here make fire without matches?", (sx, sy), 0, 3, (1920, 1080))
    x0, y0, x1, y1 = b.box
    face = (sx - 0.075 * 1920, sy - 0.24 * 1080, sx + 0.075 * 1920, sy + 0.04 * 1080)
    assert x1 <= face[0] or x0 >= face[2] or y1 <= face[1] or y0 >= face[3]
