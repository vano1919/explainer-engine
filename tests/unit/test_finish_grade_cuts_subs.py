"""W7: grade once (33^3 LUT), blended cuts and J/L offsets, captions, thumbnail through the vendored skills, the new validator rows,
and the continuity-card edit fields."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.finish import cut_check, ffwrap, grade as GR, subtitles as SUB
from explainer_engine.validators import color as VC, edit as VE, tech_qa as VQ

ROOT = Path(__file__).resolve().parents[2]
needs_ff = pytest.mark.skipif(not ffwrap.available(), reason="ffmpeg or the vendored ffmpeg-skill is missing")


def _ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _imgs(mean, std, seed):
    return np.clip(np.random.default_rng(seed).normal(mean, std, (36, 64, 3)), 0, 1)


# ---- grade once -------------------------------------------------------------------------------------------------------------
def test_lut_is_33_cubed_and_matches_the_transfer():
    f, k = _imgs(0.35, 0.1, 0), _imgs(0.55, 0.15, 1)
    p = GR.transfer_params(f, k)
    lat = GR.build_lut(p, 0.5)
    assert lat.shape == (33 ** 3, 3)
    x = np.random.default_rng(2).random((60, 1, 3))
    assert np.abs(GR.lut_apply(lat, x) - GR.apply_transfer(x, p, 0.5)).max() < 0.02


def test_cube_file_roundtrip_and_red_runs_fastest(tmp_path):
    lat = GR.build_lut(GR.transfer_params(_imgs(0.4, 0.1, 3), _imgs(0.5, 0.1, 4)), 0.0)   # blend 0 = identity LUT
    sha = GR.write_cube(tmp_path / "k.cube", lat)
    size, rows = GR.read_cube(tmp_path / "k.cube")
    assert size == 33 and len(sha) == 64 and np.allclose(rows[1], [1 / 32, 0, 0], atol=1e-5) and np.allclose(rows[33], [0, 1 / 32, 0], atol=1e-5)


def test_the_blend_is_capped_at_bp130():
    top = GR.blend_cap(10.0)
    assert top[1] is True and top[0] < 1.0


@needs_ff
def test_grade_master_applies_once_and_refuses_a_second_time(tmp_path):
    _ff("-f", "lavfi", "-i", "testsrc=size=160x90:rate=24:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp_path / "m.mp4"))
    key = _imgs(0.6, 0.15, 5)
    frames = np.stack([_imgs(0.3, 0.1, 6)])
    rec = GR.grade_master(tmp_path / "m.mp4", tmp_path / "g.mp4", key, frames)
    assert rec["schema"] == GR.GRADE_RECORD and rec["lut_size"] == 33 and GR.graded(tmp_path / "g.mp4")
    assert (tmp_path / "g.cube").is_file() and not GR.graded(tmp_path / "m.mp4")
    with pytest.raises(ContractError, match="applied once"):
        GR.grade_master(tmp_path / "g.mp4", tmp_path / "gg.mp4", key, frames)
    assert VC.graded_once(tmp_path / "g.mp4")["status"] == "PASS"
    assert VC.graded_once(tmp_path / "m.mp4")["status"] == "NOT_RUN"
    (tmp_path / "g.mp4").write_bytes(b"changed")
    assert VC.graded_once(tmp_path / "g.mp4")["status"] == "REVIEW"


def test_master_vs_key_row():
    key = (_imgs(0.5, 0.1, 7) * 255).astype(np.uint8)
    assert VC.master_vs_key(key, key)["status"] == "PASS"
    far = (_imgs(0.2, 0.05, 8) * 255).astype(np.uint8)
    assert VC.master_vs_key(far, key)["status"] == "REVIEW"
    assert VC.master_vs_key(np.zeros((0, 4, 4, 3)), key)["status"] == "NOT_RUN"


# ---- cuts -------------------------------------------------------------------------------------------------------------------
@needs_ff
def test_a_dissolve_is_found_and_a_hard_cut_is_not(tmp_path):
    for n, src in (("a", "testsrc2"), ("b", "smptebars")):
        _ff("-f", "lavfi", "-i", f"{src}=size=160x90:rate=24:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp_path / f"{n}.mp4"))
    _ff("-i", str(tmp_path / "a.mp4"), "-i", str(tmp_path / "b.mp4"), "-filter_complex", "xfade=transition=fade:duration=1:offset=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp_path / "dissolve.mp4"))
    _ff("-i", str(tmp_path / "a.mp4"), "-i", str(tmp_path / "b.mp4"), "-filter_complex", "concat=n=2:v=1:a=0", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(tmp_path / "hard.mp4"))
    assert VE.blended_cuts(tmp_path / "dissolve.mp4")["status"] == "REVIEW"
    assert VE.blended_cuts(tmp_path / "hard.mp4")["status"] == "PASS"
    assert VE.blended_cuts(tmp_path / "dissolve.mp4", allow=5)["status"] == "PASS"


def test_blended_row_not_run_for_a_missing_file(tmp_path):
    assert cut_check.blended_row(tmp_path / "x.mp4")["status"] == "NOT_RUN"


def test_jl_offsets_use_bp117_bands_by_cut_kind():
    cards = [{"shot_id": "A", "edit": {"j_offset_frames": 10}},                       # 0.42 s dialogue/action: inside 0.3-0.6
             {"shot_id": "B", "edit": {"l_offset_frames": 3}},                        # 0.125 s: too short
             {"shot_id": "C", "is_master": True, "edit": {"j_offset_frames": 17}},   # 0.71 s scene boundary: inside 0.4-0.8
             {"shot_id": "D", "edit": {"j_offset_frames": 0}}, {"shot_id": "E"}]      # none: skipped
    rows = {r["gate"]: r["status"] for r in VE.jl_offsets(cards)}
    assert rows == {"VAL-EDT-02:A:j": "PASS", "VAL-EDT-02:B:l": "REVIEW", "VAL-EDT-02:C:j": "PASS"}
    assert VE.jl_offsets([{"shot_id": "E"}])[0]["status"] == "NOT_RUN"


def test_edit_validate_adds_the_two_rows_only_with_their_inputs():
    gates = {r["gate"].split(":")[0] for r in VE.validate({"cards": [{"shot_id": "A", "edit": {"j_offset_frames": 10}}]})}
    assert "VAL-EDT-02" in gates and "VAL-EDT-01" not in gates


def test_continuity_card_schema_accepts_edit_fields_and_refuses_others():
    import copy
    from explainer_engine.scripting import continuity
    bundle = json.loads((ROOT / "episodes/ep_truce_1914/story/shot_cards_60s.json").read_text(encoding="utf-8"))
    card = bundle["cards"][0]
    assert "edit" in json.loads((ROOT / "explainer_engine/schemas/continuity_card.schema.json").read_text())["$defs"]["shot"]["properties"]
    assert continuity.schema_findings(card) == []                                     # without the field: valid as before
    with_edit = copy.deepcopy(card)
    with_edit["shots"][0]["edit"] = {"j_offset_frames": 10, "l_offset_frames": 0}
    assert continuity.schema_findings(with_edit) == []                                # with it: valid
    for bad in ({"j_offset_frames": -1}, {"j_offset_frames": 2.5}, {"boundary": "scene"}):
        broken = copy.deepcopy(card)
        broken["shots"][0]["edit"] = bad
        assert continuity.schema_findings(broken), bad


# ---- captions ---------------------------------------------------------------------------------------------------------------
def test_cues_respect_bp210_and_keep_every_word():
    text = "The truce began on a quiet night and nobody on either side could say who fired the last shot of the war."
    words = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(text.split())]
    cues = SUB.build_cues(words)
    assert " ".join(c["text"].replace("\n", " ") for c in cues) == text
    assert all(len(line) <= 42 for c in cues for line in c["text"].split("\n"))
    assert all(r["status"] == "PASS" for r in SUB.rows(cues))
    assert all(a["end"] <= b["start"] + 1e-9 for a, b in zip(cues, cues[1:]))


def test_a_cue_too_fast_to_read_is_kept_and_flagged_not_cut():
    words = [{"word": w, "start": i * 0.05, "end": i * 0.05 + 0.04} for i, w in enumerate("one two three four five six seven eight nine ten.".split())]
    cues = SUB.build_cues(words)
    assert " ".join(c["text"].replace("\n", " ") for c in cues) == "one two three four five six seven eight nine ten."


def test_srt_is_written_by_the_vendored_skill(tmp_path):
    cues = [{"id": "c1", "start": 0.0, "end": 2.0, "text": "Hello there"}, {"id": "c2", "start": 2.0, "end": 4.0, "text": "General Kenobi"}]
    srt = SUB.write_srt(cues, tmp_path)
    assert "00:00:02,000 --> 00:00:04,000" in srt.read_text(encoding="utf-8")
    with pytest.raises(ContractError, match="subtitle-skill generate failed"):
        SUB.write_srt([{"id": "c1", "start": 3.0, "end": 1.0, "text": "bad"}], tmp_path, "bad.srt")


@needs_ff
def test_soft_track_is_muxed_without_touching_the_streams(tmp_path):
    _ff("-f", "lavfi", "-i", "testsrc=size=160x90:rate=24:duration=2", "-f", "lavfi", "-i", "sine=duration=2", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", str(tmp_path / "m.mp4"))
    srt = SUB.write_srt([{"id": "c1", "start": 0.0, "end": 2.0, "text": "Hello there"}], tmp_path)
    SUB.mux_soft(tmp_path / "m.mp4", srt, tmp_path / "s.mp4")
    assert ffwrap.probe(tmp_path / "s.mp4")["subtitle_streams"] == 1


# ---- thumbnail through the vendored skill ----------------------------------------------------------------------------------------
def test_thumbnail_renders_through_the_skill_at_1280x720(tmp_path):
    from PIL import Image
    from explainer_engine.publish import thumbnail as T
    Image.new("RGB", (1920, 1080), (40, 60, 90)).save(tmp_path / "pic.png")
    out = T.compose_via_skill(tmp_path / "pic.png", "Who falls first", tmp_path / "t.jpg")
    assert T.check_image(out) == []
    with pytest.raises(RuntimeError):
        T.compose_via_skill(tmp_path / "missing.png", "x", tmp_path / "u.jpg")


def test_the_vendored_folders_stay_byte_identical():
    from tools import vendor_skill as vendor  # noqa: F401
    r = subprocess.run(["python3", "tools/vendor_skill.py", "verify"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-400:]


def test_tech_qa_rows_are_registered():
    assert {"VAL-QA-07", "VAL-QA-08"} <= set(VQ.RULE_IDS) and {"VAL-CLR-01", "VAL-CLR-02"} <= set(VC.RULE_IDS)
    assert VQ.skill_check(ROOT / "nope.mp4")["status"] == "NOT_RUN"
