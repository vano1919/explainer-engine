"""Calibration of the free observers on a labelled set (W4, OB-1 point 6; report docs/OBSERVATION_CALIBRATION_2026-11-20.md).

Runs the ffmpeg and transcript observers on labelled raw clips in a scratch episode folder (it never writes into the real episode),
reads the session's look from a ``claude`` answers file, and counts per observer: TP, FP, FN, TN.

* positive of an observer = it recorded at least one defect of severity major or minor (info does not count);
* an asset is truly positive for an observer when a labelled defect has the kind that observer can see
  (``transcript`` -> transcript, ``visual`` -> claude/gemini; ffmpeg sees TECH-* only, none is labelled, so every labelled defect is
  outside its reach and counts as FN in the "all known defects" column, and a TECH-* alarm on a labelled-good clip is a FP);
* ``not_evaluable`` assets are listed and left out of the counts.

    python -m explainer_engine.qa.observers.calibration <clips dir> <labels.json> <whisper.json> <shot_plan.json> [--claude answers.json]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from explainer_engine.qa.observers import ffmpeg as OF
from explainer_engine.qa.observers import transcript as OT

SEES = {"ffmpeg": ("tech",), "transcript": ("transcript",), "claude": ("visual",)}


def expected_text(shot_plan: dict, shot: str) -> str:
    sh = next(s for s in shot_plan["shots"] if s["shot"] == shot)
    return " ".join(t for who, t in sh["lines"] if who != "none" and not t.startswith("("))


def positive(rec: dict) -> bool:
    return any(d["severity"] in ("major", "minor") for d in rec["defects"])


def tally(truth: dict, called: dict) -> dict:
    """truth/called: {shot: bool}. Returns TP/FP/FN/TN with the shot lists."""
    out = {"TP": [], "FP": [], "FN": [], "TN": []}
    for s, t in sorted(truth.items()):
        c = called[s]
        out[("TP" if c else "FN") if t else ("FP" if c else "TN")].append(s)
    return out


def run(clips: Path, labels: dict, whisper: Path, plan: dict, claude: dict | None = None) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="obs_cal_"))
    try:
        ep = tmp / "ep_cal"
        ep.mkdir()
        shots = [s for s, v in labels["clips"].items() if v["label"] != "not_evaluable"]
        recs = {"ffmpeg": {}, "transcript": {}, "claude": {}}
        for s in shots:
            shutil.copy(clips / f"{s}.mp4", ep / f"{s}.mp4")
            recs["ffmpeg"][s] = OF.observe(ep, s, "clip", f"{s}.mp4")
            words = OT.load_words(whisper, s)
            recs["transcript"][s] = OT.observe(ep, s, "clip", f"{s}.mp4", expected_text(plan, s), words)
            if claude and s in claude:
                recs["claude"][s] = {"defects": claude[s].get("defects", [])}
        report = {"shots": shots, "not_evaluable": [s for s, v in labels["clips"].items() if v["label"] == "not_evaluable"], "observers": {}}
        for obs, kinds in SEES.items():
            if not recs[obs]:
                report["observers"][obs] = "NOT_RUN: no answers file"
                continue
            truth = {s: any(d["kind"] in kinds for d in labels["clips"][s].get("defects", [])) for s in shots}
            called = {s: positive(recs[obs][s]) for s in shots}
            t = tally(truth, called)
            known = [s for s in shots if labels["clips"][s]["label"] == "defect"]
            out_of_scope = [s for s in known if not truth[s]]
            n_pos = len(t["TP"]) + len(t["FN"])
            report["observers"][obs] = {"counts": {k: len(v) for k, v in t.items()}, "assets": t,
                                        "recall_in_scope": f"{len(t['TP'])} of {n_pos}" if n_pos else "no labelled defect of this kind",
                                        "known_defect_clips_outside_this_observer": out_of_scope,
                                        "records": {s: [f"{d['code']} {d['where']}" for d in recs[obs][s]["defects"]] +
                                                    ([recs[obs][s].get('note')] if recs[obs][s].get("note") else [])
                                                    for s in shots}}
        return report
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clips")
    ap.add_argument("labels")
    ap.add_argument("whisper")
    ap.add_argument("shot_plan")
    ap.add_argument("--claude")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    claude = json.loads(Path(a.claude).read_text(encoding="utf-8")) if a.claude else None
    rep = run(Path(a.clips), json.loads(Path(a.labels).read_text(encoding="utf-8")), Path(a.whisper),
              json.loads(Path(a.shot_plan).read_text(encoding="utf-8")), claude)
    text = json.dumps(rep, indent=1, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
