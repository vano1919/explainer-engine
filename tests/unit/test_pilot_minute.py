"""The pilot minute's cut (EXEC_QUEUE.md P1): eleven shots from the p15 and p16 pods' clips, trimmed to their seconds, the clock insert
as a push-in on its still, one compare page. Synthetic clips and stills; needs ffmpeg."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.production import pilot_minute as PM

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
SMALL = (320, 180)


def clip(path: Path, frames: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=352x198:r=24", "-frames:v", str(frames), "-pix_fmt",
                    "yuv420p", str(path)], check=True)


def png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=352x198", "-frames:v", "1", str(path)], check=True)


def world(tmp_path: Path, skip=()):
    roots = {"p15": tmp_path / "p15", "p16": tmp_path / "p16"}
    blender = tmp_path / "blender"
    ids = PM.resolve_shots(blender)
    for mid, shot, secs, pod, frames in PM.MINUTE:
        sid = {"battle_wide_high": "battle_wide_high_f112_colour", "battle_front_mid": "battle_front_mid_f100_colour"}.get(shot, shot)
        png(blender / f"{sid}.png")
        png(Path(roots[pod or "p15"]) / "qwen" / f"{sid}.png")
        if pod and sid not in skip:
            clip(PM.job_path(roots[pod], sid, frames), frames)
    return roots, blender, ids


def test_the_cut_table_is_a_minute_of_8k_plus_1_clips_and_no_shot_is_longer_than_its_clip():
    assert 60.0 <= PM.total_seconds() <= 66.0
    for mid, shot, secs, pod, frames in PM.MINUTE:
        if pod:
            assert (frames - 1) % 8 == 0 and secs <= frames / 24 + 1e-6, mid
    assert sum(1 for m in PM.MINUTE if m[3]) == 10 and [m[1] for m in PM.MINUTE if not m[3]] == ["room_insert_clock"]
    assert {m[3] for m in PM.MINUTE if m[3]} == {"p15", "p16"} and sum(1 for m in PM.MINUTE if m[3] == "p15") == 2


def test_the_battle_still_ids_follow_the_files(tmp_path):
    b = tmp_path / "b"
    b.mkdir()
    assert PM.resolve_shots(b)["battle_wide_high"] == "battle_wide_high"
    (b / "battle_wide_high_f112_colour.png").write_bytes(b"x")
    assert PM.resolve_shots(b)["battle_wide_high"] == "battle_wide_high_f112_colour"


def test_the_minute_is_built_from_the_clips_trimmed_to_their_shots_with_a_page(tmp_path):
    roots, blender, _ = world(tmp_path)
    doc = PM.build(roots, blender, tmp_path / "out", size=SMALL)
    assert doc["seconds"] == pytest.approx(PM.total_seconds(), abs=0.1) and doc["preview"] is False
    assert [s["id"] for s in doc["shots"]] == [m[0] for m in PM.MINUTE]
    assert all(s["frames"] == round(s["seconds"] * 24) for s in doc["shots"]) and PM._frames(tmp_path / "out" / "pilot_minute.mp4") == sum(
        s["frames"] for s in doc["shots"])
    html = (tmp_path / "out" / "compare.html").read_text(encoding="utf-8")
    assert html.count("<section>") == 11 and "Blender still" in html and "Qwen restyle" in html and "J5 push-in" in html
    assert json.loads((tmp_path / "out" / "minute.json").read_text())["sha256"] == doc["sha256"]


def test_a_missing_clip_stops_the_cut_unless_a_preview_slate_is_allowed(tmp_path):
    roots, blender, _ = world(tmp_path, skip=("room_reverse",))
    with pytest.raises(ContractError, match="room_reverse"):
        PM.build(roots, blender, tmp_path / "out", size=SMALL)
    doc = PM.build(roots, blender, tmp_path / "out2", size=SMALL, allow_missing=True)
    assert doc["preview"] is True and [s["shot"] for s in doc["shots"] if s["slate"]] == ["room_reverse"]


def test_a_clip_shorter_than_its_shot_is_refused(tmp_path):
    roots, blender, _ = world(tmp_path)
    clip(PM.job_path(roots["p16"], "room_insert_table", 97), 40)   # 1.67 s of a 4 s shot
    with pytest.raises(ContractError, match="frames, the shot needs"):
        PM.build(roots, blender, tmp_path / "out", size=SMALL)
