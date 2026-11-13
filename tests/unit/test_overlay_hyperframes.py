"""Stage B5 (v4.3 plan 9.2): the HyperFrames overlay layer. The spec is a pure function of the shot and its word spine, the project
carries no CDN, and (when a local HyperFrames CLI is given in EXPLAINER_HYPERFRAMES) a render has the right size, alpha and length."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.overlay import hyperframes as HF
from explainer_engine.overlay import sample, spec as OS

CARD = (1408, 96, 1056, 594)


def _spec(shot_id="S02_SH010"):
    s, _ = sample.build(shot_id)
    return s


def test_scribe_words_become_frames_and_split_dashes():
    sc = [{"text": "Hello", "start": 0.5, "end": 0.9, "type": "word"}, {"text": " ", "start": 0.9, "end": 0.95, "type": "spacing"},
          {"text": "ocean—but", "start": 1.0, "end": 1.5, "type": "word"}]
    sp = OS.spine_from_scribe(sc, 24)
    assert [w["word"] for w in sp] == ["hello", "ocean", "but"]
    assert [w["start_frame"] for w in sp] == [12, 24, 30]


def test_each_item_starts_on_its_spoken_word():
    for shot_id in ("S02_SH010", "S01_SH008"):
        s, scribe = sample.build(shot_id)
        sp = OS.spine_from_scribe(scribe, 24)
        by_word = {}
        for i, w in enumerate(sp):
            by_word.setdefault(w["word"], []).append(w["start_frame"])
        for it in s["items"]:
            first = it["word"].split()[0].lower()
            assert it["start"] in by_word[first], (shot_id, it)
        assert s["items"] == sorted(s["items"], key=lambda i: i["start"])


def test_spec_is_deterministic_and_in_card_pixels():
    a, b = _spec(), _spec()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["schema"] == OS.SCHEMA and a["card"] == {"x": 1408, "y": 96, "w": 1056, "h": 594, "radius": a["card"]["radius"]}
    for it in a["items"]:
        for key in ("at", "origin", "target"):
            if key in it:
                assert -50 <= it[key][0] <= 1056 + 50 and -50 <= it[key][1] <= 594 + 50, (it["kind"], key, it[key])


def test_zoom_and_card_shots_are_refused():
    shot, script, places = sample.load_shot("S02_SH001")      # a zoom shot: the camera is Python's
    with pytest.raises(ContractError):
        OS.build(shot, script, places, 24, card=CARD)
    shot, script, places = sample.load_shot("S01_SH008")
    shot["actions"] = [{"kind": "counter", "at_word": "four thousand", "value": 4000, "unit": "miles"}]
    with pytest.raises(ContractError):
        OS.build(shot, script, places, 24, card=CARD)        # no place: a card, no map to overlay


def test_project_has_no_cdn_and_vendors_gsap(tmp_path):
    proj = HF.write_project(_spec(), tmp_path / "p")
    html = (proj / "index.html").read_text(encoding="utf-8")
    urls = set(re.findall(r"https?://[^\s\"'`)]+", html))
    assert urls <= {"http://www.w3.org/2000/svg"}, urls            # GSAP is vendored, never a CDN (plan 9.2)
    assert re.search(r'<script src="vendor/gsap-[\d.]+\.min\.js">', html)
    assert (proj / "vendor").glob("gsap-*.min.js") and (proj / "fonts" / "Inter.ttf").exists()
    pkg = json.loads((HF.TEMPLATE_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg["dependencies"]["hyperframes"] == HF.HF_VERSION       # exact pin, no range
    assert "__SPEC__" not in html and "__FPS__" not in html


@pytest.mark.skipif(not os.environ.get("EXPLAINER_HYPERFRAMES") or not shutil.which("ffmpeg"),
                    reason="needs a local HyperFrames CLI (EXPLAINER_HYPERFRAMES) and ffmpeg; free, but slow")
def test_render_is_transparent_and_frame_exact(tmp_path):
    s = _spec("S01_SH008")
    s = {**s, "frames": 96}
    proj = HF.write_project(s, tmp_path / "p")
    out = tmp_path / "o.webm"
    HF.render_overlay(proj, out, quality="draft")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_tags=alpha_mode",
                            "-of", "json", str(out)], capture_output=True, text=True, check=True)
    st = json.loads(probe.stdout)["streams"][0]
    assert (st["width"], st["height"]) == (2560, 1440) and st["tags"]["ALPHA_MODE"] == "1"
    a = sample._alpha_frames(out, tmp_path, "alpha")           # decoded with the vp9 decoder that keeps the alpha plane
    assert len(a) == 96                                         # one frame per frame of the spec
    assert a[:, 0:20, 0:20].max() == 0                          # the corner is transparent
    assert a[80].max() > 200                                    # the card chrome is drawn
