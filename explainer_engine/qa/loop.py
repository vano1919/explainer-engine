"""The QA loop: time, render a pair of chunks, review it (data + pixels), classify every finding, stop with a report
(standing order 12, docs/PRODUCTION_RULES.md; the creator, 2026-10-20: check the video after every two rendered parts, fix
the code when a problem is systemic and the script when it is the script's, re-render, until it is clean).

    python -m explainer_engine.qa.loop <script.json> --read DIR --out DIR --chunks A:B [--pics DIR ...] [--snd DIR ...]
                                       [--timed FILE] [--render DIR] [--no-assemble] [--no-pixels] [--ledger run.json]

1. ``production time <script> <read>/words.json`` -> ``<out>/timed.json`` (``--timed FILE`` reuses a timing instead). A
   timing FAIL stops the loop before the render (fix the script or the code first; ``--render-on-fail`` renders anyway for a
   look, it never makes a FAIL pass).
2. ``production assemble <script> <timed> <read>/narration.wav --out <render> --chunks A:B`` (RULE-R1: only these chunks;
   ``--no-assemble`` reviews the chunks already in ``<render>/chunks``).
3. The chunks A..B-1 joined (stream copy) with their stretch of ``<render>/audio.wav`` into ``<out>/review/pair_A_B.mp4``;
   ``qa/frame_review`` on it: the data checks (FR rules) and the pixel checks (``qa/pixels``, PX rules).
4. Every finding is classified: **systemic** (the code: the same rule on ``SYSTEMIC_MIN_SHOTS`` or more shots, a range-wide
   finding, or the pixels contradicting a shot whose plan data is clean) or **script** (one shot's data, or a picture's
   declared face point that ``qa/face_points`` finds away from the painted face, FP-OFF; a prop ring or label that
   ``qa/prop_points`` finds away from its thing, PB-OFF, or whose thing it finds nowhere, PB-NONE), with the owner file
   to fix. The loop never edits code or the script: it writes ``<out>/loop_report.json`` and stops, the session fixes the
   owners and runs the same command again.
5. Iterations are counted in the report. A finding still there after ``MAX_ITERATIONS`` runs stops the loop (exit 3): stop
   and report to the creator (CLAUDE.md supervision rule).

Exit 0 = no FAIL (each REVIEW is fixed or named to the creator), 1 = findings to fix, 3 = stopped after MAX_ITERATIONS.

Paid allowance: the loop may spend at most ``allowances.qa_loop.per_run`` ElevenLabs credits per run on re-reads of script
lines it changed (config/spend_caps.json, the creator 2026-10-20), only through ``reserve_reread`` (core/ledger
``Run.reserve_allowance``: a reserve above it refuses; the run's own ElevenLabs cap and its 80 % stop still apply).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

SCHEMA = "qa_loop/1"
MAX_ITERATIONS = 5  # CLAUDE.md supervision rule: stop after 5 iterations on the same issue and report
SYSTEMIC_MIN_SHOTS = 2  # the same kind of finding on this many shots is the code's, not one shot's data
ALLOWANCE = "qa_loop"

# rule (prefix) -> the file to fix: "code" when the finding is systemic, "script" when it is one shot's data
OWNERS = {
    "FR-BUBBLE": {"code": "explainer_engine/production/assemble.py (shot_bubbles) + production/faces.py (views)",
                  "script": "the line's bubble and pictures.<id>.speakers in the script"},
    "FR-RING": {"code": "explainer_engine/production/beats.py (fit_to_views, draw)",
                "script": "the beat's pos / at in the script (visual_beats)"},
    "FR-FACE": {"code": "explainer_engine/production/faces.py (views, composite)",
                "script": "the expression beats of the shot in the script"},
    "FR-TEXT": {"code": "explainer_engine/production/beats.py (fit_to_views)",
                "script": "the beat's timing in the script (ends with its shot)"},
    "FR-LOUDNESS": {"code": "explainer_engine/qa/targets.py + production/assemble.py (mix)", "script": "-"},
    "PX-CUT": {"code": "explainer_engine/production/assemble.py (finish_frame, chunks)",
               "script": "the shot list in the script (pictures that look alike)"},
    "PX-FROZEN": {"code": "explainer_engine/production/assemble.py (the frame loop)", "script": "-"},
    "PX-BLACK": {"code": "explainer_engine/production/assemble.py (chunk_look, fades)", "script": "-"},
    "PX-CAM": {"code": "explainer_engine/production/assemble.py (finish_frame, rest_weight) + production/continuity.py",
               "script": "the shot's motion / accents in the script"},
    "PX-JUMP-CUT": {"code": "explainer_engine/production/continuity.py (chain)",
                    "script": "the two shots' picture and motion in the script (a full framing step, BP-30)"},
    "FP-OFF": {"code": "explainer_engine/qa/face_points.py (detection / matching)",
               "script": "pictures.<id>.speakers in the script (python -m explainer_engine.qa.face_points <script> --apply "
                         "rewrites the confident ones)"},
    "PB-": {"code": "explainer_engine/qa/prop_points.py (detection, SCORE_MIN)",
            "script": "the beat's pos in the script (python -m explainer_engine.qa.prop_points <script> --apply moves the found "
                      "ones and removes the ones found nowhere)"},
    "PX-BUBBLE": {"code": "explainer_engine/production/assemble.py (shot_bubbles) + finish/bubbles.py",
                  "script": "pictures.<id>.speakers in the script (the speaker's point)"},
}
TIMING_OWNER = {"code": "explainer_engine/production/timing.py (or the validator named by the rule)",
                "script": "the script lines / shots named in the finding"}
_SHOT = re.compile(r"\bSH\d{3,4}\b")


def owner_of(rule: str) -> dict:
    for k in sorted(OWNERS, key=len, reverse=True):
        if rule.startswith(k):
            return OWNERS[k]
    return TIMING_OWNER


def shot_of(f: dict) -> str | None:
    if f.get("shot"):
        return f["shot"]
    m = _SHOT.search(str(f.get("where", "")))
    return m.group(0) if m else None


def classify(findings: list[dict]) -> list[dict]:
    """Each FAIL / REVIEW finding with ``class`` (systemic / script), ``why`` and ``owner`` (the file to fix)."""
    rows = [dict(f, shot=shot_of(f)) for f in findings if f.get("severity") in ("FAIL", "REVIEW")]
    shots_by_rule: dict[str, set] = {}
    data_shots: set = set()
    for f in rows:
        if f["shot"]:
            shots_by_rule.setdefault(f["rule"], set()).add(f["shot"])
            if f.get("source") != "pixels":
                data_shots.add(f["shot"])
    out = []
    for f in rows:
        n = len(shots_by_rule.get(f["rule"], ()))
        if f.get("source") == "face_points":
            cls, why = "script", "a declared face point of a picture: the script's data (the painted face is elsewhere)"
        elif f.get("source") == "prop_points":
            cls, why = "script", "a prop ring or label written without seeing the picture: the beat's pos (CC-03)"
        elif f["shot"] is None:
            cls, why = "systemic", "a range-wide finding (no single shot)"
        elif f.get("source") == "pixels" and f["shot"] not in data_shots:
            cls, why = "systemic", "the pixels contradict a shot whose plan data is clean: the renderer drew it"
        elif n >= SYSTEMIC_MIN_SHOTS:
            cls, why = "systemic", f"{f['rule']} on {n} shots: the same kind of finding in several places is the code's"
        else:
            cls, why = "script", f"{f['rule']} on one shot only: that shot's data"
        own = owner_of(f["rule"])
        out.append(dict(f, **{"class": cls, "why": why, "owner": own["code"] if cls == "systemic" else own["script"]}))
    return out


def signature(f: dict) -> str:
    return f"{f['rule']}|{f.get('shot') or '-'}|{f.get('where', '')}"


def streaks(prev: dict | None, rows: list[dict]) -> dict[str, int]:
    """How many consecutive iterations each finding has been there (this one included)."""
    before = (prev or {}).get("streaks", {})
    return {signature(f): before.get(signature(f), 0) + 1 for f in rows}


# --- the steps -------------------------------------------------------------------------------------------------------------

def _run(cmd: list[str], log: list[dict]) -> int:
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.append({"cmd": cmd, "returncode": r.returncode, "seconds": round(time.time() - t0, 1),
                "tail": (r.stdout + r.stderr)[-1500:]})
    return r.returncode


def _prod(*args: str) -> list[str]:
    return [sys.executable, "-m", "explainer_engine.production", *args]


def chunk_range(timed: dict, render: Path, a: int, b: int) -> dict:
    """The shots, frames and seconds of chunks [a, b) (the bounds the assembler wrote in chunks/plan.json, else its
    chunk_bounds), and the chunk files."""
    plan = render / "chunks" / "plan.json"
    if plan.exists():
        bounds = json.loads(plan.read_text(encoding="utf-8"))["bounds"]
    else:
        from explainer_engine.production import assemble as A
        bounds = A.chunk_bounds(timed["shots"], timed["fps"], timed["frames"])
    if not 0 <= a < b <= len(bounds):
        raise SystemExit(f"--chunks {a}:{b} is outside the {len(bounds)} chunks of this render")
    shots = timed["shots"]
    f0, f1 = shots[bounds[a][0]]["start_frame"], shots[bounds[b - 1][1] - 1]["end_frame"]
    fps = timed["fps"]
    return {"bounds": bounds[a:b], "start_frame": f0, "end_frame": f1, "from": f0 / fps, "to": f1 / fps,
            "files": [render / "chunks" / f"c_{i:04d}.mp4" for i in range(a, b)]}


def join_pair(files: list[Path], audio: Path | None, t_from: float, t_to: float, dest: Path) -> Path:
    """The chunk files joined without re-encoding, with their stretch of the mix when there is one (the loudness check)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files), encoding="utf-8")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if audio is not None and audio.exists():
        cmd += ["-ss", f"{t_from:.3f}", "-t", f"{t_to - t_from:.3f}", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "copy", str(dest)]
    subprocess.run(cmd, check=True)
    lst.unlink()
    return dest


def reserve_reread(ledger: Path, lines: list[str], credits: float, item: str) -> None:
    """Reserve ElevenLabs credits for re-reading script lines the loop changed, under the creator's allowance (raises
    core.ledger.AllowanceReached above it, CapReached at the cap's 80 %). The caller makes the paid call only after this."""
    from explainer_engine.core.ledger import Run
    Run.open(ledger).reserve_allowance(ALLOWANCE, credits, item, lines=lines)


def run(script: Path, read: Path | None, out: Path, chunks: tuple[int, int], *, pics: list[str] | None = None,
        snd: list[str] | None = None, timed_file: Path | None = None, render: Path | None = None, assemble: bool = True,
        pixels: bool = True, render_on_fail: bool = False, ledger: Path | None = None) -> dict:
    from explainer_engine.qa import frame_review as FR
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "loop_report.json"
    prev = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    if prev and prev.get("chunks") != list(chunks):
        prev = None  # another chunk pair starts its own count
    iteration = (prev or {}).get("iteration", 0) + 1
    a, b = chunks
    extra = [x for p in pics or [] for x in ("--pics", p)]
    log: list[dict] = []
    findings: list[dict] = []
    stop_note = ""

    timed_path = Path(timed_file) if timed_file else out / "timed.json"
    if not timed_file:
        if read is None:
            raise SystemExit("--read DIR (words.json, narration.wav) is needed to time the script")
        _run(_prod("time", str(script), str(read / "words.json"), "--out", str(timed_path), *extra), log)
    timed = json.loads(timed_path.read_text(encoding="utf-8"))
    timing = [dict(f, source="timing") for f in timed.get("findings", []) if f.get("severity") in ("FAIL", "REVIEW")]
    findings += timing
    timing_fail = any(f["severity"] == "FAIL" for f in timing)

    render = Path(render) if render else out / "render"
    review: dict = {}
    rng: dict = {}
    if timing_fail and not render_on_fail:
        stop_note = "the timing has FAIL findings: fixed before anything is rendered (--render-on-fail renders for a look)"
    else:
        if assemble:
            if read is None:
                raise SystemExit("--read DIR (narration.wav) is needed to assemble")
            code = _run(_prod("assemble", str(script), str(timed_path), str(read / "narration.wav"), "--out", str(render),
                              "--chunks", f"{a}:{b}", *extra, *[x for s in snd or [] for x in ("--snd", s)]), log)
            if code:
                stop_note = "assemble failed: see steps[-1].tail"
        if not stop_note:
            rng = chunk_range(timed, render, a, b)
            missing = [str(f) for f in rng["files"] if not f.exists()]
            if missing:
                stop_note = f"chunks not on disk: {missing}"
            else:
                pair = join_pair(rng["files"], render / "audio.wav", rng["from"], rng["to"],
                                 out / "review" / f"pair_{a}_{b}.mp4")
                dirs = [Path(p) for p in pics] if pics else None
                review = FR.run(timed_path, pair, out / "review" / f"iter_{iteration:02d}", rng["from"], rng["to"],
                                rng["from"], dirs, pixels=pixels)
                findings += [f for f in review["findings"] if f.get("source") != "timing"]

    if pics:  # the declared face points against the faces painted in the pictures this range uses (REVIEW only)
        from explainer_engine.production import script as S
        from explainer_engine.qa import face_points as FP
        lo, hi = (rng["start_frame"], rng["end_frame"]) if rng else (0, timed["frames"])
        used = {s["picture"] for s in timed["shots"] if s["start_frame"] < hi and s["end_frame"] > lo}
        doc = S.load(script)
        fp = FP.measure(doc, [Path(x) for x in pics])
        fp["pictures"] = {k: v for k, v in fp.get("pictures", {}).items() if k in used}
        findings += FP.check(doc, [Path(x) for x in pics], fp)
        # the prop rings and labels against the things the detector finds in their pictures (REVIEW only, CC-03)
        from explainer_engine.qa import prop_points as PB
        pb = PB.measure(doc, timed, [Path(x) for x in pics], only_pictures=used)
        findings += PB.check(pb)
    rows = classify(findings)
    st = streaks(prev, rows)
    stuck = sorted(s for s, n in st.items() if n >= MAX_ITERATIONS)
    fails = sum(1 for f in rows if f["severity"] == "FAIL")
    if stuck:
        status = "STOPPED"
    elif stop_note or fails:
        status = "FIX"
    else:
        status = "CLEAN"
    allowance = None
    try:
        from explainer_engine.core import spend_caps
        al = spend_caps.allowance(ALLOWANCE)
        allowance = {"service": al["service"], "per_run": al["per_run"]}
        if ledger and Path(ledger).exists():
            data = json.loads(Path(ledger).read_text(encoding="utf-8"))
            allowance["used"] = (data.get("allowances", {}).get(ALLOWANCE) or {}).get("used", 0.0)
    except Exception as e:  # noqa: BLE001 - the report says why, the loop itself spends nothing
        allowance = {"error": str(e)}
    by_owner: dict[str, int] = {}
    for f in rows:
        by_owner[f["owner"]] = by_owner.get(f["owner"], 0) + 1
    report = {
        "schema": SCHEMA, "script": str(script), "chunks": [a, b], "iteration": iteration, "status": status,
        "stop": stop_note or (f"{len(stuck)} finding(s) still there after {MAX_ITERATIONS} iterations: stop and report to "
                              "the creator" if stuck else ""),
        "stuck": stuck, "timed": str(timed_path), "range": {k: rng.get(k) for k in ("from", "to", "start_frame", "end_frame")},
        "video": review.get("video"), "sheets": review.get("sheets", []),
        "counts": {s: sum(1 for f in rows if f["severity"] == s) for s in ("FAIL", "REVIEW")},
        "classes": {c: sum(1 for f in rows if f["class"] == c) for c in ("systemic", "script")},
        "by_owner": by_owner, "findings": rows, "streaks": st, "pixels": review.get("pixels"), "allowance": allowance,
        "steps": log, "history": ((prev or {}).get("history", []) + [{"iteration": iteration, "status": status,
                                                                         "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                         "FAIL": fails}])[-20:],
        "next": {"CLEAN": "open every sheet (standing order 12), name each REVIEW to the creator or fix it",
                 "FIX": "fix each finding's owner (systemic: the code, with a focused test; script: the script), then run the "
                        "same command again",
                 "STOPPED": "stop: report the stuck findings to the creator and wait"}[status],
    }
    write_json_atomic(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.qa.loop", description=__doc__.split("\n")[0])
    p.add_argument("script")
    p.add_argument("--read", type=Path, help="the read's folder: words.json and narration.wav (production words)")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--chunks", required=True, help="FIRST:END, e.g. 0:2 = chunks 0 and 1 (RULE-R1: two at a time)")
    p.add_argument("--pics", action="append")
    p.add_argument("--snd", action="append")
    p.add_argument("--timed", type=Path, help="reuse this timed.json instead of timing the script")
    p.add_argument("--render", type=Path, help="the render folder (default <out>/render)")
    p.add_argument("--no-assemble", action="store_true", help="review the chunks already in <render>/chunks")
    p.add_argument("--no-pixels", action="store_true")
    p.add_argument("--render-on-fail", action="store_true")
    p.add_argument("--ledger", type=Path, help="the run's run.json: the report shows the allowance used")
    a = p.parse_args(argv)
    lo, hi = (int(x) for x in a.chunks.split(":"))
    r = run(Path(a.script), a.read, a.out, (lo, hi), pics=a.pics, snd=a.snd, timed_file=a.timed, render=a.render,
            assemble=not a.no_assemble, pixels=not a.no_pixels, render_on_fail=a.render_on_fail, ledger=a.ledger)
    print(f"qa loop iteration {r['iteration']} chunks {lo}:{hi}: {r['status']} - {r['counts']['FAIL']} FAIL, "
          f"{r['counts']['REVIEW']} REVIEW ({r['classes']['systemic']} systemic, {r['classes']['script']} script)")
    for f in r["findings"]:
        if f["severity"] == "FAIL":
            print(f"  FAIL {f['rule']} {f['where']} [{f['class']} -> {f['owner']}]: {f['detail'][:140]}")
    if r["stop"]:
        print(f"  stop: {r['stop']}")
    print(f"  {a.out / 'loop_report.json'}; next: {r['next']}")
    return {"CLEAN": 0, "FIX": 1, "STOPPED": 3}[r["status"]]


if __name__ == "__main__":
    sys.exit(main())
