"""v4.3 P8: one runner over the stages (records, refusal, staleness, rehearsal), the voice stage's clock and the chunked
assembly (RN-01..RN-06 in docs/EPISODE_FIRST.md)."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN
from explainer_engine.episode import timing as TM
from explainer_engine.qa import gates as G

ROOT = Path(__file__).resolve().parents[2]
TOBA = ROOT / "episodes" / "ep_toba"
FPS = 24


def _script(shot_ids=("S01_SH001", "S01_SH005", "S01_SH006"), durations=(1.0, 1.25, 1.0)) -> dict:
    doc = json.loads((TOBA / "story" / "production_script.json").read_text(encoding="utf-8"))
    by = {s["shot_id"]: s for s in doc["shots"]}
    shots = [dict(copy.deepcopy(by[sid]), target_duration_seconds=d) for sid, d in zip(shot_ids, durations)]
    lines = {lid for s in shots for lid in s.get("audio_line_ids") or []}
    segs = {s["segment_id"] for s in shots}
    doc["shots"] = shots
    doc["audio_lines"] = [l for l in doc["audio_lines"] if l["line_id"] in lines]
    doc["segments"] = [s for s in doc["segments"] if s["segment_id"] in segs]
    return doc


def _episode(tmp_path: Path, script: dict | None = None) -> Path:
    root = tmp_path / "ep_toba"
    (root / "story").mkdir(parents=True)
    shutil.copy(TOBA / "episode.json", root / "episode.json")
    (root / "story" / "production_script.json").write_text(json.dumps(script or _script()), encoding="utf-8")
    return root


def _fake(status_by_stage: dict):
    def make(stage):
        def fn(ep, rehearsal):
            st = status_by_stage.get(stage, G.PASS)
            if st == "raise":
                raise ContractError(f"{stage} cannot go on")
            return [G.row(f"{stage}_gate", st == G.PASS, "fake", level=G.REVIEW if st == G.REVIEW else G.FAIL)], {"n": 1}
        return fn
    return {s: make(s) for s in RUN.STAGES}


# --- records, refusal, staleness, rehearsal ------------------------------------------------------------------------------

def test_a_stage_refuses_to_start_without_the_record_before_it(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}))
    ep = RUN.Episode(_episode(tmp_path))
    with pytest.raises(RUN.StageRefused, match="needs the record of script"):
        RUN.run_stage(ep, "sound_plan")
    rec = RUN.run_stage(ep, "G1")       # a gate id names its stage
    assert rec["stage"] == "script" and rec["verdict"]["status"] == G.PASS
    assert RUN.record_path(ep.root, "script").is_file()
    assert RUN.run_stage(ep, "G4")["stage"] == "sound_plan"


def test_a_fail_stops_the_chain_and_a_rehearsal_goes_on_but_never_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"pictures": G.FAIL}))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert [r["stage"] for r in recs] == ["script", "sound_plan", "pictures"]
    with pytest.raises(RUN.StageRefused, match="pictures ended FAIL"):
        RUN.run_stage(RUN.Episode(root), "voice")
    recs = RUN.run_to(RUN.Episode(root, rehearsal=True), "qa")
    assert recs[-1]["stage"] == "qa" and all(r["rehearsal"] for r in recs[3:])
    assert not any(r.get("rehearsal") for r in recs[:3])
    qa = recs[-1]
    assert qa["verdict"]["status"] == G.FAIL and "not_a_rehearsal" in qa["verdict"]["failed"]


def test_a_passing_chain_is_not_a_rehearsal_even_with_the_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}))
    recs = RUN.run_to(RUN.Episode(_episode(tmp_path), rehearsal=True), "qa")
    assert recs[-1]["verdict"]["status"] == G.PASS and not recs[-1]["rehearsal"]


def test_a_review_lets_the_next_stage_start(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    recs = RUN.run_to(RUN.Episode(_episode(tmp_path)), "qa")
    assert recs[1]["verdict"]["status"] == G.REVIEW and recs[-1]["verdict"]["status"] == G.PASS


def test_a_changed_input_makes_the_record_stale_and_the_next_stage_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "sound_plan")
    doc = json.loads((root / "story" / "production_script.json").read_text())
    doc["shots"][0]["target_duration_seconds"] = 1.5
    (root / "story" / "production_script.json").write_text(json.dumps(doc))
    ep = RUN.Episode(root)
    assert [s["fresh"] for s in RUN.state(ep)][:2] == [False, False]
    with pytest.raises(RUN.StageRefused, match="stale"):
        RUN.run_stage(ep, "pictures")
    recs = RUN.run_to(ep, "pictures")      # --to runs the stale ones again, in order
    assert [r.get("reused", False) for r in recs] == [False, False, False]


def test_fresh_records_are_kept_and_force_runs_them_again(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "voice")
    again = RUN.run_to(RUN.Episode(root), "voice")
    assert all(r.get("reused") for r in again)
    forced = RUN.run_to(RUN.Episode(root, force=True), "voice")
    assert not any(r.get("reused") for r in forced)


def test_a_contract_error_in_a_stage_is_its_fail_row_on_record(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"script": "raise"}))
    rec = RUN.run_stage(RUN.Episode(_episode(tmp_path)), "script")
    assert rec["verdict"]["status"] == G.FAIL and rec["rows"][0]["gate"] == "script_ran"
    assert "cannot go on" in rec["rows"][0]["detail"]


def test_the_cli_says_refused_and_lists_the_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}))
    root = _episode(tmp_path)
    assert RUN.main(["run", str(root), "--stage", "assemble"]) == 2
    assert RUN.main(["run", str(root), "--to", "G4"]) == 0
    assert RUN.main(["status", str(root)]) == 0
    out = capsys.readouterr().out
    assert "sound_plan" in out and "fresh" in out and "not run" in out


def test_a_file_outside_the_episode_is_refused(tmp_path):
    ep = RUN.Episode(_episode(tmp_path))
    with pytest.raises(ContractError, match="outside the episode"):
        ep.path("../elsewhere/x.json")


def test_paid_ledger_lines_need_an_approved_plan(tmp_path):
    from explainer_engine.episode.acceptance import gates
    root = _episode(tmp_path)
    (root / "logs").mkdir()
    (root / "logs" / "wan_ledger.jsonl").write_text(
        json.dumps({"shot_id": "A", "event": "submit", "estimate_usd": 0.3, "plan_id": "OR23-1"}) + "\n"
        + json.dumps({"shot_id": "A", "event": "done", "estimate_usd": 0.0}) + "\n")
    kw = dict(root=root, script=_script(), shot_records=[], transition_plans=None, audio=None, stem_audit=None,
              video=None, fps=FPS)
    row = lambda rep: next(r for r in rep["gates"] if r["gate"] == "paid_calls_approved")  # noqa: E731
    assert row(gates(**kw, paid=RUN.paid_lines(root)))["status"] == G.PASS
    with open(root / "logs" / "wan_ledger.jsonl", "a") as f:
        f.write(json.dumps({"shot_id": "B", "event": "submit", "estimate_usd": 0.3}) + "\n")
    bad = row(gates(**kw, paid=RUN.paid_lines(root)))
    assert bad["status"] == G.FAIL and bad["measured"] == ["wan_ledger.jsonl:B"]


# --- the voice stage's clock -----------------------------------------------------------------------------------------------

def _transcript(script: dict, starts: list[float], word_s: float = 0.12, gap: float = 0.03) -> tuple[dict, list]:
    """Scribe-like words for every line, line k starting at ``starts[k]``; returns the transcript and each line's span."""
    words, spans = [], []
    lines = {l["line_id"]: l for l in script["audio_lines"]}
    for lid, t in zip(TM.read_order(script), starts):
        a = t
        for w in lines[lid]["text"].split():
            words.append({"text": w, "start": round(t, 3), "end": round(t + word_s, 3), "type": "word"})
            t += word_s + gap
        spans.append((a, t - gap))
    return {"words": words}, spans


def test_the_read_times_every_shot_and_the_shots_tile_it():
    doc = _script(("S01_SH005", "S01_SH006", "S01_SH007"), (3.0, 3.0, 3.0))
    starts = [0.2, 3.4, 7.9]
    tr, spans = _transcript(doc, starts)
    read_s = spans[-1][1] + 0.6
    tm = TM.retime(doc, TM.align_read(doc, tr, read_s), FPS, read_s)
    sh = [tm["shots"][s["shot_id"]] for s in doc["shots"]]
    assert sh[0]["start_frame"] == 0 and sum(s["frames"] for s in sh) == tm["total_frames"] == round(read_s * FPS)
    assert all(a["start_frame"] + a["frames"] == b["start_frame"] for a, b in zip(sh, sh[1:]))
    mid = (spans[0][1] + spans[1][0]) / 2          # the cut sits in the middle of the pause between two lines
    assert abs(sh[1]["start_frame"] - mid * FPS) <= 1
    sp = tm["spines"]["S01_SH006"]
    assert sp[0]["start_frame"] == round(starts[1] * FPS) - sh[1]["start_frame"] and sp[0]["word"] == "what"
    timed = TM.timed_script(doc, tm)
    assert [round(s["target_duration_seconds"] * FPS) for s in timed["shots"]] == [s["frames"] for s in sh]
    assert doc["shots"][0]["target_duration_seconds"] == 3.0       # the script itself is not edited


def test_a_shot_without_a_line_shares_the_pause_it_sits_in():
    doc = _script(("S01_SH005", "S01_SH006", "S01_SH007"), (2.0, 1.0, 3.0))
    doc["shots"][1]["audio_line_ids"] = []
    doc["audio_lines"] = [l for l in doc["audio_lines"] if l["line_id"] != "S01_L006"]
    tr, spans = _transcript(doc, [0.1, 6.0])
    read_s = spans[-1][1] + 0.3
    tm = TM.retime(doc, TM.align_read(doc, tr, read_s), FPS, read_s)
    a, b, c = (tm["shots"][s["shot_id"]] for s in doc["shots"])
    assert a["start_frame"] + a["frames"] == round((spans[0][1] + TM.PAD_S) * FPS)    # the line keeps its air
    assert c["start_frame"] == round((6.0 - TM.PAD_S) * FPS)
    assert b["frames"] > 0 and tm["spines"]["S01_SH006"] == []


def test_a_line_carried_twice_or_without_words_is_refused():
    doc = _script(("S01_SH005", "S01_SH006"), (2.0, 2.0))
    doc["shots"][1]["audio_line_ids"] = list(doc["shots"][0]["audio_line_ids"])
    with pytest.raises(ContractError, match="carried by two shots"):
        TM.read_order(doc)
    doc = _script(("S01_SH005",), (2.0,))
    doc["audio_lines"][0]["text"] = "[pause]"
    with pytest.raises(ContractError, match="without words"):
        TM.align_read(doc, {"words": []}, 1.0)


# --- the chunked assembly --------------------------------------------------------------------------------------------------

def _clip(path: Path, frames: int, colour, size=(64, 36)) -> Path:
    w, h = size
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r",
                           str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-frames:v", str(frames),
                           str(path)], stdin=subprocess.PIPE)
    for k in range(frames):
        ff.stdin.write(np.full((h, w, 3), colour, np.uint8).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0
    return path


def _wav(path: Path, seconds: float, rate: int = 48000) -> Path:
    n = int(seconds * rate)
    x = (0.1 * np.sin(np.arange(n) * 2 * np.pi * 220 / rate) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.tobytes())
    return path


def test_the_assembly_writes_chunks_reuses_them_and_joins_once(tmp_path):
    from explainer_engine.production import assemble as ASM
    recs = [{"shot_id": f"S{i}", "clip_path": str(_clip(tmp_path / f"S{i}.mp4", 30, (40 * i, 80, 120))), "total_frames": 24}
            for i in range(6)]
    cuts = [{"transition_type": "cross_dissolve_8f", "transition_frames": 8}] + \
           [{"transition_type": "hard_cut_with_jl_bridge", "transition_frames": 0}] * 4
    audio = _wav(tmp_path / "mix.wav", 6.0)
    out = tmp_path / "final" / "m.mp4"
    part = ASM.assemble_shot_clips(recs, cuts, audio, out, fps=FPS, size=(64, 36), chunk_seconds=1.0, only=(0, 3))
    assert part["chunks"]["count"] == 4 and part["chunks"]["left"] == [3] and not out.exists()  # nothing joined yet
    full = ASM.assemble_shot_clips(recs, cuts, audio, out, fps=FPS, size=(64, 36), chunk_seconds=1.0)
    assert full["chunks"]["reused"] == 3 and full["chunks"]["drawn"] == 1
    assert full["total_frames"] == 144 and out.is_file()
    again = ASM.assemble_shot_clips(recs, cuts, audio, out, fps=FPS, size=(64, 36), chunk_seconds=1.0)
    assert again["chunks"]["reused"] == 4 and again["sha256"]
    # the dissolve between S0 and S1 blends their colours on the boundary frames
    frames = list(ASM.clip_frames(out, 20, 8))
    reds = [int(f[..., 0].mean()) for f in frames]
    assert reds[0] < 10 and any(10 < r < 30 for r in reds) and reds[-1] > 30


def test_a_clip_shorter_than_its_shot_is_refused(tmp_path):
    from explainer_engine.production import assemble as ASM
    recs = [{"shot_id": "S0", "clip_path": str(_clip(tmp_path / "S0.mp4", 10, (10, 10, 10))), "total_frames": 24}]
    with pytest.raises(ContractError, match="never stretched"):
        ASM.assemble_shot_clips(recs, [], _wav(tmp_path / "a.wav", 1.0), tmp_path / "m.mp4", fps=FPS, size=(64, 36))


# --- the whole chain on a small episode, as a rehearsal ---------------------------------------------------------------------

def test_a_small_episode_rehearses_the_whole_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    doc = _script()
    root = _episode(tmp_path, doc)
    img_dir = root / "assets" / "generated" / "images"
    img_dir.mkdir(parents=True)
    rng = np.random.default_rng(3)
    for s in doc["shots"]:
        a = np.zeros((216, 384, 3), np.uint8)
        a[:110] = (90, 120, 160)
        a[110:] = (110, 90, 60)
        a = np.clip(a + rng.integers(0, 40, a.shape), 0, 255).astype(np.uint8)
        Image.fromarray(a).save(img_dir / f"{s['shot_id']}_start.png")
    tr, spans = _transcript(doc, [0.1, 1.2, 2.6], word_s=0.06, gap=0.01)
    (root / "audio").mkdir()
    _wav(root / "audio" / "narration.wav", spans[-1][1] + 0.3)
    (root / "audio" / "narration.scribe.json").write_text(json.dumps(tr))
    ep = RUN.Episode(root, size=(192, 108), rehearsal=True, chunk_seconds=1.0)
    recs = {r["stage"]: r for r in RUN.run_to(ep, "qa")}
    assert list(recs) == list(RUN.STAGES)
    pics = {r["gate"]: r["status"] for r in recs["pictures"]["rows"]}
    assert pics["every_picture_present"] == G.PASS and pics["every_picture_taken_in"] == G.FAIL   # never through intake
    assert recs["voice"]["verdict"]["status"] in (G.PASS, G.REVIEW)
    timing = json.loads((root / "audio" / "timing.json").read_text())
    shots = json.loads((root / "production" / "shot_records.json").read_text())["shots"]
    assert [s["total_frames"] for s in shots] == [timing["shots"][s["shot_id"]]["frames"] for s in shots]
    wan = next(s for s in shots if s["route"] == "wan")
    assert wan["fallback_for_wan"] and wan["clip_path"]                    # the rehearsal draws it with the 2.5D fallback
    clips = {r["gate"]: r["status"] for r in recs["clips"]["rows"]}
    assert clips["every_wan_shot_is_a_wan_clip"] == G.FAIL
    master = json.loads((root / "production" / "master.json").read_text())
    assert master["total_frames"] == timing["total_frames"] and master["chunks"]["count"] >= 1
    qa = recs["qa"]
    rows = {r["gate"]: r["status"] for r in qa["rows"]}
    assert qa["verdict"]["status"] == G.FAIL and rows["not_a_rehearsal"] == G.FAIL
    assert rows["master_length_matches_the_script"] == G.PASS and rows["narration_is_a_real_read"] == G.PASS
    assert rows["paid_calls_approved"] == G.PASS and rows["sound_is_real"] == G.FAIL       # placeholders, missing takes
    man = json.loads((root / "production" / "production_manifest.json").read_text())
    assert man["rehearsal"] and not man["all_gates_passed"] and (root / man["contact_sheet_path"]).is_file()
    # a second run keeps every fresh record and every clip
    again = RUN.run_to(RUN.Episode(root, size=(192, 108), rehearsal=True, chunk_seconds=1.0), "qa")
    assert all(r.get("reused") for r in again)


def test_a_missing_free_tool_is_not_run_on_record_not_a_traceback(tmp_path, monkeypatch):
    """Final audit B3: a ConfigError (a missing raster, model or binary) is a NOT_RUN row that names it."""
    from explainer_engine.core.errors import ConfigError

    def boom(ep, rehearsal):
        raise ConfigError("no shaded relief raster (run: python -m explainer_engine.production.relief_fetch)")
    monkeypatch.setattr(RUN, "STAGE_FUNCS", dict(_fake({}), script=boom))
    rec = RUN.run_stage(RUN.Episode(_episode(tmp_path)), "script")
    assert rec["verdict"]["status"] == "INCOMPLETE" and rec["rows"][0]["status"] == G.NOT_RUN
    assert "relief_fetch" in rec["rows"][0]["detail"]


def test_a_map_without_actions_fails_and_a_wan_shot_without_pictures_still_counts(tmp_path):
    """Final audit B1 and B2: no fallback to the archive's fixed Toba map; a Wan shot with no picture is still counted as a
    Wan shot without its QA'd clip, never a PASS of 0."""
    doc = _script(("S01_SH001", "S01_SH008"), (1.0, 1.0))
    doc["shots"][1].pop("actions", None)
    assert doc["shots"][0]["route"] == "wan" and doc["shots"][1]["route"] == "map_action"
    rows, _ = RUN.stage_clips(RUN.Episode(_episode(tmp_path, doc), size=(192, 108)), True)
    by = {r["gate"]: r for r in rows}
    assert by["every_wan_shot_is_a_wan_clip"]["status"] == G.FAIL and by["every_wan_shot_is_a_wan_clip"]["measured"] == ["S01_SH001"]
    shots = {s["shot_id"]: s for s in json.loads((tmp_path / "ep_toba" / "production" / "shot_records.json").read_text())["shots"]}
    assert shots["S01_SH008"]["status"] == G.FAIL and "without actions" in shots["S01_SH008"]["error"]
