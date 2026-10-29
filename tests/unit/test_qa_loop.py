"""The QA loop (qa/loop.py; the creator, 2026-10-20: review after every two rendered parts, fix code or script, re-render
until clean): classification, the iteration counter and its stop after 5, a run on two tiny chunks, the re-read allowance."""
import json
import subprocess

import pytest

from explainer_engine.core.ledger import AllowanceReached
from explainer_engine.qa import loop as L

FPS = 30


def _f(rule, where, sev="FAIL", source=None, shot=None):
    f = {"rule": rule, "severity": sev, "where": where, "detail": "x"}
    if source:
        f["source"] = source
    if shot:
        f["shot"] = shot
    return f


def test_findings_are_classed_systemic_or_script_with_their_owner():
    rows = L.classify([
        _f("FR-BUBBLE-WHO", "SH010 'a'"), _f("FR-BUBBLE-WHO", "SH012 'b'"),  # the same kind on two shots: the code's
        _f("FR-RING-HERO", "SH003 highlight 'Musk'"),  # one shot's data: the script's
        _f("PX-CAM-JUMP", "SH005", "REVIEW", "pixels", "SH005"),  # pixels contradict a clean plan: the renderer
        _f("PX-JUMP-CUT", "SH003", "REVIEW", "pixels", "SH003"),  # the plan of SH003 already has a finding: one shot
        _f("FR-LOUDNESS", "range", "REVIEW"),  # range-wide: the code
        _f("FP-OFF", "s02_signing belfort", "REVIEW", "face_points"),  # a picture's declared face point: the script
        _f("PV-20", "SH009", "INFO"),  # neither FAIL nor REVIEW: not a finding to fix
    ])
    by = {(r["rule"], r["shot"]): r for r in rows}
    assert len(rows) == 7
    assert by[("FR-BUBBLE-WHO", "SH010")]["class"] == "systemic" and "assemble.py" in by[("FR-BUBBLE-WHO", "SH010")]["owner"]
    assert by[("FR-RING-HERO", "SH003")]["class"] == "script" and "script" in by[("FR-RING-HERO", "SH003")]["owner"]
    assert by[("PX-CAM-JUMP", "SH005")]["class"] == "systemic"
    assert by[("PX-JUMP-CUT", "SH003")]["class"] == "script"
    assert by[("FR-LOUDNESS", None)]["class"] == "systemic"
    assert by[("FP-OFF", None)]["class"] == "script" and "--apply" in by[("FP-OFF", None)]["owner"]


def test_streaks_count_iterations_of_the_same_finding():
    rows = L.classify([_f("FR-RING-HERO", "SH003 highlight 'Musk'")])
    s1 = L.streaks(None, rows)
    s2 = L.streaks({"streaks": s1}, rows)
    assert list(s2.values()) == [2]
    assert L.streaks({"streaks": s2}, []) == {}  # fixed: the count ends


def _video(path, seconds: float, color: str):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r={FPS}:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def _job(tmp_path):
    """A timed file of three shots, two chunks already rendered, and a mix: the loop reviews chunks 0:2 without timing or
    assembling. SH002's bubble runs across the cut into SH003 (FR-BUBBLE-CUT, a FAIL that stays until it is fixed)."""
    shots = []
    for i, (a, b, pic) in enumerate([(0, 60, "p1"), (60, 120, "p2"), (120, 180, "p1")]):
        shots.append({"id": f"SH{i + 1:03d}", "picture": pic, "start": a / FPS, "end": b / FPS, "start_frame": a,
                      "end_frame": b, "transition": "cut", "render_motion": {"kind": "hold", "z0": 1.0, "z1": 1.0},
                      "bubbles": []})
    shots[1]["bubbles"] = [{"who": "ann", "text": "Too long.", "kind": "speech", "start": 3.0, "end": 4.5,
                            "start_frame": 90, "end_frame": 135}]
    timed = {"fps": FPS, "frames": 180, "shots": shots, "visual_beats": [], "face_sheets": {},
             "pictures": {"p1": {"speakers": {"ann": [0.3, 0.4]}}, "p2": {"speakers": {"ann": [0.3, 0.4]}}},
             "findings": []}
    (tmp_path / "timed.json").write_text(json.dumps(timed))
    ch = tmp_path / "render" / "chunks"
    ch.mkdir(parents=True)
    (ch / "plan.json").write_text(json.dumps({"stamp": "x", "bounds": [[0, 2], [2, 3]]}))
    _video(ch / "c_0000.mp4", 4.0, "navy")
    _video(ch / "c_0001.mp4", 2.0, "olive")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-ar", "48000",
                    str(tmp_path / "render" / "audio.wav")], check=True)
    return tmp_path / "timed.json"


def test_the_loop_reviews_a_chunk_pair_and_stops_after_five_iterations_on_one_finding(tmp_path):
    timed = _job(tmp_path)
    out = tmp_path / "loop"
    kw = dict(timed_file=timed, render=tmp_path / "render", assemble=False, pixels=False)
    for k in range(1, L.MAX_ITERATIONS):
        r = L.run(tmp_path / "script.json", None, out, (0, 2), **kw)
        assert r["iteration"] == k and r["status"] == "FIX"
    assert r["range"]["from"] == 0.0 and r["range"]["to"] == 6.0
    fail = [f for f in r["findings"] if f["rule"] == "FR-BUBBLE-CUT"]
    assert fail and fail[0]["class"] == "script" and fail[0]["shot"] == "SH002"
    assert r["allowance"]["service"] == "elevenlabs_credits" and r["allowance"]["per_run"] == 2000
    assert (out / "review" / "pair_0_2.mp4").exists() and r["sheets"]
    r = L.run(tmp_path / "script.json", None, out, (0, 2), **kw)
    assert r["status"] == "STOPPED" and r["stuck"] and "creator" in r["next"]
    saved = json.loads((out / "loop_report.json").read_text())
    assert saved["iteration"] == L.MAX_ITERATIONS and len(saved["history"]) == L.MAX_ITERATIONS
    # another chunk pair starts its own count; the CLI's exit code says FIX
    assert L.main(["s.json", "--out", str(tmp_path / "loop2"), "--chunks", "0:1", "--timed", str(timed), "--render",
                   str(tmp_path / "render"), "--no-assemble", "--no-pixels"]) in (0, 1)


def test_a_timing_fail_stops_the_loop_before_any_render(tmp_path):
    timed = _job(tmp_path)
    t = json.loads(timed.read_text())
    t["findings"] = [{"rule": "PV-24", "severity": "FAIL", "where": "SH001", "detail": "bubble over a face"}]
    timed.write_text(json.dumps(t))
    r = L.run(tmp_path / "script.json", None, tmp_path / "loop", (0, 2), timed_file=timed, render=tmp_path / "render",
              assemble=False, pixels=False)
    assert r["status"] == "FIX" and "before anything is rendered" in r["stop"] and r["video"] is None


def test_rereads_go_through_the_allowance(tmp_path):
    from explainer_engine.core.ledger import Run
    ledger = tmp_path / "run.json"
    Run.open(ledger, caps={"elevenlabs_credits": 23000})
    L.reserve_reread(ledger, ["S02 L4"], 1999, "qa_reread_1")
    with pytest.raises(AllowanceReached):
        L.reserve_reread(ledger, ["S02 L5"], 2, "qa_reread_2")
    assert json.loads(ledger.read_text())["allowances"]["qa_loop"]["used"] == 1999
