"""AC-16..AC-19 (episode look) and LT-66 (prompt absolutes)."""

import numpy as np
from PIL import Image

from explainer_engine.compose import episode_look as EL
from explainer_engine.qa import style_prompt as SP
from explainer_engine.training import lora_rules

T = lora_rules.trigger()  # D-80: the one home (N-09)

ERAS = (f"{T}, a thin caveman leaps back from a roaring campfire in a dark cave, his lanky friend laughing, "
        "warm firelight on rough stone walls")


def _pic(rgb, noise=0):
    a = np.full((64, 96, 3), rgb, np.uint8)
    if noise:
        a = np.clip(a + np.random.default_rng(1).integers(-noise, noise, a.shape), 0, 255).astype(np.uint8)
    return Image.fromarray(a)


def test_absolutes_are_frozen():
    # LT-66: changing one of these needs ვანო's word and a new LoRA version, never a quiet edit
    assert [a[0] for a in SP.ABSOLUTES] == [f"A{i}" for i in range(1, 11)]
    assert SP.NEGATIVE == "text, lettering, letters, words, watermark, signature, photo, 3d render"
    assert SP.INFERENCE == {"base": "Qwen/Qwen-Image-2.1", "lora": None, "lora_weight": 1.0,
                            "dtype": "bfloat16", "size": [1280, 720], "steps": 30, "true_cfg": 4.0}  # D-80
    assert SP.TRIGGER == T == "xworld style"  # D-80: the xworld LoRA's trigger (N-09)


def test_style_clash_fails():
    assert not [f for f in SP.check(ERAS) if f["severity"] == "FAIL"]
    bad = SP.check(ERAS + ", cinematic photoreal render")
    assert any(f["rule"] == "LT-66" and f["severity"] == "FAIL" for f in bad)


def test_phrase_rules():
    assert EL.check_phrase("muted ochre and teal, warm amber glow") == []
    assert EL.check_phrase("cinematic teal and orange")                       # a style word
    assert EL.check_phrase("warm amber glow, wide shot")                       # layout
    assert EL.check_phrase("a dragon breathing amber fire")                    # not colour words
    assert EL.check_phrase("warm " * 11)                                       # too long


def test_apply_keeps_prompt_valid():
    look = {"phrase": "muted ochre and teal, warm amber glow", "lights": {"night": "deep indigo night, amber firelight"}}
    p, found = EL.apply(ERAS, look)
    assert p.startswith(T) and p.endswith("warm amber glow")
    assert not [f for f in found if f["severity"] == "FAIL"]
    p2, _ = EL.apply(p, look)
    assert p2 == p                                                             # never added twice
    pn, _ = EL.apply(ERAS, look, "night")
    assert "indigo" in pn
    long = f"{T}, " + " ".join(["word"] * 34)
    assert any(f["severity"] == "FAIL" for f in EL.apply(long, look)[1])        # 40 words still binds


def test_measure_drift_grade():
    warm, cold = _pic((170, 110, 60), 20), _pic((60, 110, 170), 20)
    look = EL.make(warm, "warm amber glow")
    assert look["schema"] == "episode_look/1" and len(look["palette_lab"]) == 6
    assert EL.drift(warm, look)["severity"] == "PASS"
    far = EL.drift(cold, look)
    assert far["severity"] == "REVIEW" and far["rule"] == "AC-18"
    graded = EL.grade(cold, look, strength=0.9)                                # capped at GRADE_MAX
    assert EL.drift(graded, look)["drift"] < far["drift"]
    before = np.asarray(cold).copy()
    EL.grade(cold, look)
    assert (np.asarray(cold) == before).all()                                  # original untouched
    g = np.asarray(graded).astype(int) - np.asarray(cold).astype(int)
    assert np.abs(g).max() < 120                                               # bounded, not a repaint


def test_lab_round_trip():
    a = np.random.default_rng(0).integers(0, 256, (20, 20, 3)).astype(np.uint8)
    assert np.abs(EL._rgb(EL._lab(a)).astype(int) - a).max() <= 2
