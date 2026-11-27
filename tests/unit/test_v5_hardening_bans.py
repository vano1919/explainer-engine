"""v5 cinema hardening: no cropped coverage plates, no cutout compositing, no clipped dialogue (BP-214..217),
gentle dialogue polish with speaker loudness parity, and J-cut / L-cut continuity over one room-tone bed."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pyloudnorm as pyln
import pytest
import soundfile as sf

from explainer_engine.audio import narrator_polish as NP
from explainer_engine.audio.broadcast_cinema_mix import consolidate_scene_room_tone, render_dialogue_scene_track
from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.episode.word_timeline_compiler import (
    DialogueWordClippedError,
    compile_word_locked_timeline,
    enforce_dialogue_breath_tail,
)
from explainer_engine.qa.cinema_gates import check_no_cropped_seed_plates, check_no_cutout_compositing
from explainer_engine.videolane.multishot_scene_director import (
    extract_axis_locked_coverage_plates,
    plan_dialogue_j_l_cuts,
    stitch_scene_zero_stretch,
)

ROOT = Path(__file__).resolve().parents[2]
SR = 48000
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


# --- cropped coverage plates ---------------------------------------------------------------------------------------

def test_extracting_coverage_plates_always_raises(tmp_path: Path) -> None:
    expected = "Cropped coverage plates are permanently banned; generate native full-frame camera angles per shot."
    with pytest.raises(RuntimeError) as err:
        extract_axis_locked_coverage_plates(tmp_path / "wide.png", [{"shot_id": "cu"}], tmp_path / "out")
    assert str(err.value) == expected
    with pytest.raises(RuntimeError):
        extract_axis_locked_coverage_plates()
    assert not (tmp_path / "out").exists()


def _scene_picture(path: Path, seed: int) -> Path:
    """A textured 640x360 picture with large shapes, different for every seed."""
    rng = np.random.default_rng(seed)
    img = cv2.resize(rng.integers(0, 255, (18, 32, 3), dtype=np.uint8), (640, 360), interpolation=cv2.INTER_CUBIC)
    for _ in range(40):
        x, y = int(rng.integers(0, 600)), int(rng.integers(0, 330))
        colour = tuple(int(c) for c in rng.integers(0, 255, 3))
        if rng.random() < 0.5:
            cv2.rectangle(img, (x, y), (x + int(rng.integers(8, 90)), y + int(rng.integers(8, 70))), colour, -1)
        else:
            cv2.circle(img, (x, y), int(rng.integers(5, 40)), colour, -1)
    assert cv2.imwrite(str(path), img)
    return path


def _crop_of(master: Path, out: Path, x: int, y: int, width: int) -> Path:
    """What the banned helper did: a 16:9 window of the wide plate, enlarged to full frame and sharpened."""
    img = cv2.imread(str(master))
    height = round(width * 9 / 16)
    up = cv2.resize(img[y:y + height, x:x + width], (640, 360), interpolation=cv2.INTER_LANCZOS4)
    sharp = cv2.addWeighted(up, 1.8, cv2.GaussianBlur(up, (0, 0), 1.1), -0.8, 0)
    assert cv2.imwrite(str(out), sharp)
    return out


def test_native_full_frame_plates_pass(tmp_path: Path) -> None:
    specs = [
        {"shot_id": f"s{i}", "seed_plate_path": _scene_picture(tmp_path / f"p{i}.png", i).name}
        for i in range(1, 5)
    ]
    result = check_no_cropped_seed_plates(specs, base_dir=tmp_path)
    assert result["status"] == "PASS", result["findings"]
    assert result["plates_compared"] == 4


@pytest.mark.parametrize("window", [(40, 30, 200), (230, 90, 330), (100, 20, 500)])
def test_a_plate_cut_out_of_another_plate_fails_without_any_declaration(tmp_path: Path, window) -> None:
    wide = _scene_picture(tmp_path / "wide.png", 11)
    close = _crop_of(wide, tmp_path / "close.png", *window)
    result = check_no_cropped_seed_plates(
        [{"shot_id": "wide", "plate_path": str(wide)}, {"shot_id": "close", "start_picture": str(close)}]
    )
    assert result["status"] == "FAIL"
    assert result["matches"][0]["kind"] == "sub_rectangle"
    assert result["matches"][0]["cropped_shots"] == ["close"]


def test_a_renamed_copy_of_another_plate_fails(tmp_path: Path) -> None:
    wide = _scene_picture(tmp_path / "wide.png", 12)
    copy = tmp_path / "copy.jpg"
    cv2.imwrite(str(copy), cv2.imread(str(wide)), [cv2.IMWRITE_JPEG_QUALITY, 90])
    specs = [{"shot_id": "a", "plate_path": str(wide)}, {"shot_id": "b", "plate_path": str(copy)}]
    result = check_no_cropped_seed_plates(specs)
    assert result["status"] == "FAIL"
    assert result["matches"][0]["kind"] == "perceptual_duplicate"
    # the handoff frame of a chained shot is meant to match its parent
    specs[1]["chained_from"] = "a"
    assert check_no_cropped_seed_plates(specs)["status"] == "PASS"


@pytest.mark.parametrize(
    "declaration",
    [
        {"crop_from_master": True},
        {"rel_w": 0.45},
        {"provenance": {"rel_h": 0.5}},
        {"plate": {"crop_box": [0, 0, 100, 56]}},
        {"extra": {"source_master": "wide.png"}},
    ],
)
def test_a_declared_crop_fails(declaration) -> None:
    result = check_no_cropped_seed_plates([{"shot_id": "s1", **declaration}])
    assert result["status"] == "FAIL"


def test_plates_that_cannot_be_proven_native_fail(tmp_path: Path) -> None:
    assert check_no_cropped_seed_plates([])["status"] == "FAIL"
    missing = check_no_cropped_seed_plates([{"shot_id": "s1", "seed_plate_path": str(tmp_path / "gone.png")}])
    assert missing["status"] == "FAIL"
    assert "missing or unreadable" in missing["findings"][0]


# --- cutout compositing --------------------------------------------------------------------------------------------

def _repo_and_job(tmp_path: Path) -> tuple[Path, Path]:
    repo, job = tmp_path / "repo", tmp_path / "job"
    (repo / "explainer_engine").mkdir(parents=True)
    job.mkdir()
    return repo, job


@pytest.mark.parametrize(
    "script",
    [
        "import cv2\nmask = cv2.grabCut(img, m, rect, b, f, 5)\n",
        "from cv2 import grabCut as gc\n",
        "from rembg import remove\n",
        "import importlib\nremover = importlib.import_module('rembg')\n",
        "model = AutoModel.from_pretrained('briaai/RMBG-1.4')\n",
        "MODEL_ID = 'briaai/RMBG-2.0'\n",
        "import subprocess\nsubprocess.run(['rembg', 'i', 'a.png', 'b.png'])\n",
        "def composite_person_onto_bg(person, bg):\n    return bg\n",
        "plate = composite_clean(person, bg)\n",
        "from explainer_engine.edit.cutout import birefnet_mask\n",
    ],
)
def test_a_job_script_that_cuts_people_out_fails(tmp_path: Path, script: str) -> None:
    repo, job = _repo_and_job(tmp_path)
    (job / "scripts").mkdir()
    (job / "scripts" / "build_plates.py").write_text(script, encoding="utf-8")
    result = check_no_cutout_compositing(repo, job)
    assert result["status"] == "FAIL", script
    assert "build_plates.py" in result["findings"][0]


def test_production_code_shell_scripts_and_manifests_are_scanned(tmp_path: Path) -> None:
    repo, job = _repo_and_job(tmp_path)
    (repo / "explainer_engine" / "paste.py").write_text("import rembg\n", encoding="utf-8")
    (job / "cut.sh").write_text("rembg p in out\n", encoding="utf-8")
    (job / "provenance.json").write_text(
        json.dumps({"shots": [{"shot_id": "s1", "method": "rembg then alpha paste"}]}), encoding="utf-8"
    )
    (job / "broken.json").write_text("{", encoding="utf-8")
    (job / "broken.py").write_text("def (:\n", encoding="utf-8")
    findings = "\n".join(check_no_cutout_compositing(repo, job)["findings"])
    for name in ("paste.py", "cut.sh", "provenance.json", "broken.json", "broken.py"):
        assert name in findings


def test_clean_native_plates_pass_and_words_in_docs_are_not_code(tmp_path: Path) -> None:
    repo, job = _repo_and_job(tmp_path)
    (job / "gen.py").write_text(
        '"""Never use rembg or grabCut here."""\n# composite_clean is banned\nprint("generate native plates")\n',
        encoding="utf-8",
    )
    (job / "alignment.json").write_text(json.dumps({"characters": ["C", "a", "e"]}), encoding="utf-8")
    (job / "shots.json").write_text(
        json.dumps({"shots": [
            {"shot_id": "s1", "characters": ["caesar", "calpurnia"], "plate_method": "multi_reference_anchor"},
            {"shot_id": "s2", "characters": ["caesar"], "location": "atrium",
             "provenance": {"plate_method": "blender_blocked_render"}},
        ]}),
        encoding="utf-8",
    )
    result = check_no_cutout_compositing(repo, job, require_provenance=True)
    assert result["status"] == "PASS", result["findings"]
    assert result["character_shots_declared"] == 2


def test_a_repository_below_a_folder_named_venv_is_still_scanned(tmp_path: Path) -> None:
    repo, job = _repo_and_job(tmp_path / "venv")
    (job / "paste.py").write_text("import rembg\n", encoding="utf-8")
    assert check_no_cutout_compositing(repo, job)["status"] == "FAIL"


def test_character_plates_must_declare_a_native_method(tmp_path: Path) -> None:
    repo, job = _repo_and_job(tmp_path)
    unproven = check_no_cutout_compositing(repo, job, require_provenance=True)
    assert unproven["status"] == "FAIL"
    shot = {"shot_id": "s1", "characters": ["caesar"], "location": "forum", "plate_method": "alpha_paste"}
    result = check_no_cutout_compositing(repo, job, shot_specs=[shot])
    assert result["status"] == "FAIL"
    assert any("plate_method" in f for f in result["findings"])
    assert check_no_cutout_compositing(repo, tmp_path / "no_job")["status"] == "FAIL"


def test_this_repository_has_no_cutout_compositing(tmp_path: Path) -> None:
    result = check_no_cutout_compositing(ROOT, tmp_path)
    assert result["status"] == "PASS", result["findings"]
    assert result["python_files_scanned"] > 100


# --- dialogue is never clipped -------------------------------------------------------------------------------------

def _line(**overrides) -> dict:
    return {"shot_id": "d1", "scene_id": "atrium", "has_dialogue": True, "speaker": "caesar",
            "speech_start_s": 0.5, "speech_end_s": 4.0, "duration_s": 4.35, **overrides}


def test_the_exact_breath_tail_passes() -> None:
    assert enforce_dialogue_breath_tail(_line())["tail_s"] == pytest.approx(0.35)


@pytest.mark.parametrize(
    "overrides",
    [
        {"duration_s": 3.6},                                    # mid-word
        {"duration_s": 4.34},                                   # inside the breath tail
        {"trim_end_s": 4.2},
        {"max_duration_s": 4.1},
        {"source_duration_s": 4.2},
        {"source_duration_s": 4.5, "trim_tail_s": 0.3},
        {"trim_tail_s": 0.1},                                   # cannot be proven
        {"trim_start_s": 0.8, "duration_s": 4.0},               # first word cut off
        {"speech_end_s": None},
        {"speech_start_s": None},
        {"speech_end_s": float("nan")},
    ],
)
def test_a_cut_into_dialogue_fails_closed(overrides) -> None:
    with pytest.raises(DialogueWordClippedError):
        enforce_dialogue_breath_tail(_line(**overrides))


def test_the_floor_cannot_be_lowered() -> None:
    assert issubclass(DialogueWordClippedError, ContractError)
    with pytest.raises(DialogueWordClippedError):
        enforce_dialogue_breath_tail(_line(duration_s=4.1), min_tail_s=0.05)


def test_the_compiler_refuses_a_clipped_line() -> None:
    assert compile_word_locked_timeline([_line()], [], []).status == "PASS"
    with pytest.raises(DialogueWordClippedError, match="d1"):
        compile_word_locked_timeline([_line(duration_s=3.9)], [], [])
    with pytest.raises(DialogueWordClippedError):
        compile_word_locked_timeline([{"shot_id": "d2", "duration_s": 5.0, "has_dialogue": True}], [], [])
    with pytest.raises(DialogueWordClippedError):
        compile_word_locked_timeline([_line(has_dialogue=False, start_s=10.0, end_s=14.0)], [], [])


@needs_ffmpeg
def test_the_stitcher_refuses_a_clipped_line(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=24:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-shortest", "-pix_fmt", "yuv420p", str(clip)],
        check=True,
    )
    spec = _line(clip_path=str(clip), speech_start_s=0.2, speech_end_s=2.0, num_frames=48)
    with pytest.raises(DialogueWordClippedError):
        stitch_scene_zero_stretch([spec], tmp_path / "out.mp4", work_dir=tmp_path / "work", width=320, height=180)
    assert not (tmp_path / "out.mp4").exists()


# --- gentle dialogue polish and speaker parity ---------------------------------------------------------------------

def _voice(path: Path, amplitude: float, pitch: float, seconds: float = 4.0, seed: int = 3) -> Path:
    """Syllable-like bursts of harmonics over a faint room floor, with a pause at each end."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    tone = sum(np.sin(2 * np.pi * pitch * k * t) / k for k in range(1, 12))
    syllables = np.clip(np.sin(2 * np.pi * 3.0 * t), 0.0, None) ** 0.5
    envelope = np.where((t > 0.6) & (t < seconds - 0.9), syllables, 0.0)
    signal = amplitude * tone * envelope + 0.002 * rng.standard_normal(len(t))
    sf.write(str(path), signal.astype(np.float32), SR, subtype="PCM_24")
    return path


def _lufs(path: Path) -> float:
    data, rate = sf.read(str(path), dtype="float32")
    return float(pyln.Meter(rate).integrated_loudness(data))


def test_dialogue_polish_constants_are_gentle() -> None:
    assert NP.DIALOGUE_RNNOISE_MIX == 0.45
    assert NP.DIALOGUE_HIGHPASS_HZ == 95
    assert NP.DIALOGUE_MAX_PAUSE_REDUCTION_DB == 14.0
    assert (NP.DIALOGUE_TARGET_LUFS, NP.DIALOGUE_TOLERANCE_LU) == (-17.5, 0.8)


@needs_ffmpeg
def test_cleaned_stems_of_two_speakers_match_and_keep_a_room_floor(tmp_path: Path, monkeypatch) -> None:
    commands: list[list[str]] = []
    real_run = subprocess.run

    def spy(cmd, *args, **kwargs):
        commands.append([str(part) for part in cmd])
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(NP.subprocess, "run", spy)
    out = {}
    for speaker, amplitude, pitch in (("spurinna", 0.03, 140.0), ("caesar", 0.22, 105.0)):
        raw = _voice(tmp_path / f"{speaker}_raw.wav", amplitude, pitch)
        out[speaker] = tmp_path / f"{speaker}.wav"
        stats = NP.clean_ltx_dialogue_stem(raw, out[speaker], pause_atten_db=-42.0)
        assert stats["used_rnnoise"] == 1.0
        assert stats["pause_atten_db"] == -14.0  # a deeper gate is limited
        assert _lufs(out[speaker]) == pytest.approx(-17.5, abs=0.8)
        data, _ = sf.read(str(out[speaker]), dtype="float32")
        assert float(np.sqrt(np.mean(data[int(0.1 * SR) : int(0.4 * SR)] ** 2))) > 0.0
    assert abs(_lufs(out["spurinna"]) - _lufs(out["caesar"])) <= 0.8
    chain = " ".join(commands[0])
    assert "highpass=f=95" in chain and "mix=0.45" in chain
    assert chain.count("arnndn") == 1 and "afftdn" not in chain


def test_scene_levelling_uses_one_gain_per_speaker(tmp_path: Path) -> None:
    loud = _voice(tmp_path / "c1.wav", 0.20, 105.0, seed=1)
    quiet = _voice(tmp_path / "c2.wav", 0.10, 105.0, seed=2)
    other = _voice(tmp_path / "s1.wav", 0.02, 150.0, seed=4)
    before = _lufs(loud) - _lufs(quiet)
    report = NP.match_scene_speaker_loudness(
        [{"speaker": "caesar", "wav_path": loud}, {"speaker": "caesar", "wav_path": quiet},
         {"speaker": "spurinna", "wav_path": other}]
    )
    assert report["speaker_spread_lu"] <= 0.8
    for speaker in report["speakers"].values():
        assert speaker["lufs_after"] == pytest.approx(-17.5, abs=0.8)
    assert _lufs(loud) - _lufs(quiet) == pytest.approx(before, abs=0.2)


def test_silence_cannot_be_levelled(tmp_path: Path) -> None:
    silent = tmp_path / "silent.wav"
    sf.write(str(silent), np.zeros(SR * 2, dtype=np.float32), SR)
    with pytest.raises(ConfigError):
        NP.match_scene_speaker_loudness([{"speaker": "caesar", "wav_path": silent}])


# --- J-cuts, L-cuts and one room-tone bed --------------------------------------------------------------------------

def _conversation() -> list[dict]:
    shots = []
    for i, speaker in enumerate(["calpurnia", "caesar", "calpurnia", "caesar"], start=1):
        shots.append(_line(shot_id=f"t{i}", speaker=speaker, speech_start_s=0.5, speech_end_s=3.0, duration_s=3.6))
    return shots


def test_speaker_turns_alternate_j_and_l_cuts_in_sync() -> None:
    plan = plan_dialogue_j_l_cuts(_conversation())
    assert plan == plan_dialogue_j_l_cuts(_conversation())
    assert [c["kind"] for c in plan["cuts"]] == ["j", "l", "j"]
    for cut in plan["cuts"]:
        assert 0.20 <= cut["audio_overlap_s"] <= 0.35
    shots = plan["shots"]
    for prev, cur, cut in zip(shots, shots[1:], plan["cuts"], strict=False):
        assert prev["picture_end_s"] == pytest.approx(cur["picture_start_s"])
        # voices never collide: the incoming word starts after the outgoing one has ended
        prev_speech_end = prev["audio_start_s"] + prev["speech_end_s"]
        assert cur["audio_start_s"] + cur["speech_start_s"] >= prev_speech_end
        gap = cut["picture_cut_s"] - cur["audio_start_s"]
        assert gap == pytest.approx(cut["audio_overlap_s"] if cut["kind"] == "j" else 0.0)
    for shot in shots:
        origin = shot["audio_start_s"] - shot["audio_source_in_s"]
        assert shot["picture_start_s"] - shot["picture_source_in_s"] == pytest.approx(origin)
    assert sum(s["picture_num_frames"] for s in shots) == round(plan["total_duration_s"] * 24)


def test_straight_cuts_between_scenes_and_for_one_speaker() -> None:
    shots = _conversation()[:3]
    shots[1]["speaker"] = "calpurnia"
    shots[2]["scene_id"] = "forum"
    plan = plan_dialogue_j_l_cuts(shots)
    assert [c["kind"] for c in plan["cuts"]] == ["straight", "straight"]
    assert all(c["audio_overlap_s"] == 0 for c in plan["cuts"])


@pytest.mark.parametrize("overlap", [0.1, 0.5])
def test_overlap_outside_the_window_is_refused(overlap: float) -> None:
    with pytest.raises(ValueError):
        plan_dialogue_j_l_cuts(_conversation(), overlap_s=overlap)


def test_the_planner_refuses_a_clipped_line() -> None:
    shots = _conversation()
    shots[2]["duration_s"] = 3.2
    with pytest.raises(DialogueWordClippedError):
        plan_dialogue_j_l_cuts(shots)


def test_the_dialogue_track_keeps_one_room_tone_bed_across_cuts(tmp_path: Path) -> None:
    plan = plan_dialogue_j_l_cuts(_conversation())
    stems = {}
    for shot in plan["shots"]:
        path = tmp_path / f"{shot['shot_id']}.wav"
        sf.write(str(path), np.zeros(int(3.6 * SR), dtype=np.float32), SR)
        stems[shot["shot_id"]] = path
    room = tmp_path / "room.wav"
    sf.write(str(room), (0.01 * np.random.default_rng(5).standard_normal(SR * 3)).astype(np.float32), SR)
    report = render_dialogue_scene_track(plan, stems, {"atrium": room}, tmp_path / "scene.wav")
    assert len(report["room_tone_beds"]) == 1
    data, _ = sf.read(str(tmp_path / "scene.wav"), dtype="float32")
    block = int(0.2 * SR)
    inner = data[int(0.5 * SR) : len(data) - int(0.5 * SR), 0]
    levels = [20 * np.log10(np.sqrt(np.mean(inner[i : i + block] ** 2)) + 1e-12)
              for i in range(0, len(inner) - block, block)]
    assert max(levels) - min(levels) < 3.0  # no step or dead gap at any cut
    with pytest.raises(ValueError, match="room-tone"):
        render_dialogue_scene_track(plan, stems, {}, tmp_path / "no_bed.wav")


def test_a_short_stem_fails_closed(tmp_path: Path) -> None:
    plan = plan_dialogue_j_l_cuts(_conversation()[:2])
    short = tmp_path / "short.wav"
    sf.write(str(short), np.zeros(int(2.0 * SR), dtype=np.float32), SR)
    with pytest.raises(DialogueWordClippedError):
        render_dialogue_scene_track(plan, {"t1": short, "t2": short}, {"atrium": short}, tmp_path / "x.wav")


def test_dramatic_scene_ambience_becomes_one_bed() -> None:
    rows = [
        {"shot_id": f"s{i}", "scene_id": "atrium", "dramatic_scene": True, "wav_path": "room.wav",
         "start_s": float(i * 4), "end_s": float(i * 4 + 4)}
        for i in range(3)
    ] + [{"shot_id": "m1", "scene_id": "map", "wav_path": "wind.wav", "start_s": 12.0, "end_s": 15.0},
         {"shot_id": "m2", "scene_id": "map", "wav_path": "wind.wav", "start_s": 15.0, "end_s": 18.0}]
    beds = consolidate_scene_room_tone(rows)
    assert [(b["shot_id"], b["start_s"], b["end_s"]) for b in beds] == [
        ("room_tone_atrium", 0.0, 12.0), ("m1", 12.0, 15.0), ("m2", 15.0, 18.0)
    ]
    # the scene window can mark the scene as dramatic too
    windows = [{"scene_id": "map", "dramatic_scene": True, "start_s": 12.0, "end_s": 18.0}]
    assert len(consolidate_scene_room_tone(rows, windows)) == 2
    rows[1]["level_dbfs"] = -30.0
    with pytest.raises(ValueError, match="single continuous room-tone bed"):
        consolidate_scene_room_tone(rows)
