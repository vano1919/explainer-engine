"""Reference study: what the docudrama niche's videos do, measured against how viewers react (plan v2, 2026-10-25,
docs/research/STYLE_AND_TRANSITIONS_PLAN_2026-10-25.md section 5). Free, CPU: PySceneDetect (via training/footage) + the
``.info.json`` that ``yt-dlp --write-info-json`` saves beside each video (views, duration, chapters, ``heatmap`` =
YouTube's "Most replayed" curve).

    python -m explainer_engine.research.reference_study <refs dir> [--out <dir>]

Per video: cuts, shots per minute, median shot, cuts in the first 30 s, and the cut density in the heatmap's peak and low
windows. Per channel: its most-viewed videos against its least-viewed (the contrast the plan asks for). Writes
``reference_study.json`` and ``reference_study.md``. Numbers only; frames are not kept.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
OPEN_S = 30.0  # the window vidIQ's 30-second retention metric looks at
PEAK_SHARE = 0.2  # heatmap windows in the top / bottom fifth count as peaks / lows


def info_for(video: Path) -> dict:
    """The yt-dlp metadata beside a video (``<stem>.info.json``); an empty dict when it is missing."""
    p = video.with_suffix(".info.json")
    if not p.exists():
        return {}
    j = json.loads(p.read_text(encoding="utf-8"))
    return {k: j.get(k) for k in ("id", "title", "channel", "view_count", "like_count", "duration", "upload_date",
                                   "chapters", "heatmap")}


def shot_stats(cuts: list[float], duration: float) -> dict:
    """Cut times (s) -> shots per minute, median shot (s) and cuts in the opening window."""
    bounds = [0.0] + sorted(c for c in cuts if 0 < c < duration) + [duration]
    lengths = [b - a for a, b in zip(bounds, bounds[1:]) if b > a]
    return {"shots": len(lengths), "shots_per_min": round(len(lengths) / max(duration / 60, 1e-9), 2),
            "median_shot_s": round(statistics.median(lengths), 2) if lengths else None,
            "cuts_first_30s": sum(1 for c in cuts if 0 < c <= OPEN_S)}


def heatmap_windows(heatmap: list[dict] | None) -> tuple[list[dict], list[dict]]:
    """The heatmap's peak and low windows (top and bottom ``PEAK_SHARE`` by value)."""
    if not heatmap:
        return [], []
    ranked = sorted(heatmap, key=lambda w: w["value"])
    n = max(1, round(len(ranked) * PEAK_SHARE))
    return ranked[-n:], ranked[:n]


def cuts_per_min_in(cuts: list[float], windows: list[dict]) -> float | None:
    """Cut density (cuts per minute) inside a set of heatmap windows."""
    span = sum(w["end_time"] - w["start_time"] for w in windows)
    if span <= 0:
        return None
    n = sum(1 for c in cuts for w in windows if w["start_time"] <= c < w["end_time"])
    return round(n / (span / 60), 2)


def study_video(video: Path, cuts: list[float] | None = None) -> dict:
    meta = info_for(video)
    if cuts is None:
        from explainer_engine.training import footage
        cuts = [s for s, _ in footage.split_file(video, min_len_s=0.0)][1:]
        duration = meta.get("duration") or footage.probe(video)["duration"]
    else:
        duration = meta.get("duration") or (max(cuts) if cuts else 0.0)
    peaks, lows = heatmap_windows(meta.get("heatmap"))
    row = {"file": video.name, "title": meta.get("title"), "channel": meta.get("channel") or "unknown",
           "views": meta.get("view_count"), "duration_s": duration, **shot_stats(cuts, duration),
           "cuts_per_min_peaks": cuts_per_min_in(cuts, peaks), "cuts_per_min_lows": cuts_per_min_in(cuts, lows),
           "peak_times_s": sorted(round(w["start_time"]) for w in peaks), "cuts": [round(c, 2) for c in cuts]}
    return row


def compare(rows: list[dict], top: int = 3) -> dict:
    """Per channel: the median of each measure over its ``top`` most-viewed videos against the rest."""
    out = {}
    keys = ("shots_per_min", "median_shot_s", "cuts_first_30s", "cuts_per_min_peaks", "cuts_per_min_lows")
    by = {}
    for r in rows:
        by.setdefault(r["channel"], []).append(r)
    for ch, rs in by.items():
        rs = sorted(rs, key=lambda r: r.get("views") or 0, reverse=True)
        hi, lo = rs[:top], rs[top:]

        def med(group, k):
            v = [r[k] for r in group if r.get(k) is not None]
            return round(statistics.median(v), 2) if v else None
        out[ch] = {"top": [r["file"] for r in hi], "rest": [r["file"] for r in lo],
                   **{k: {"top": med(hi, k), "rest": med(lo, k)} for k in keys}}
    return out


def report_md(rows: list[dict], cmp: dict) -> str:
    lines = ["# Reference study", "", "| Video | Channel | Views | Shots/min | Median shot s | Cuts in 30 s | "
             "Cuts/min at peaks | Cuts/min at lows |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["channel"], -(r.get("views") or 0))):
        lines.append(f"| {r['title'] or r['file']} | {r['channel']} | {r.get('views') or ''} | {r['shots_per_min']} | "
                     f"{r['median_shot_s']} | {r['cuts_first_30s']} | {r['cuts_per_min_peaks']} | {r['cuts_per_min_lows']} |")
    lines += ["", "## Most-viewed against the rest, per channel (medians)", ""]
    for ch, c in cmp.items():
        parts = [f"{k} {v['top']} vs {v['rest']}" for k, v in c.items() if isinstance(v, dict)]
        lines.append(f"- **{ch}**: " + "; ".join(parts))
    return "\n".join(lines) + "\n"


def run(ref_dir: Path, out_dir: Path) -> dict:
    from explainer_engine.core.store import write_json_atomic, write_text_atomic
    videos = sorted(p for p in Path(ref_dir).iterdir() if p.suffix.lower() in VIDEO_EXT)
    rows = [study_video(v) for v in videos]
    cmp = compare(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {"videos": rows, "compare": cmp}
    write_json_atomic(out_dir / "reference_study.json", doc)
    write_text_atomic(out_dir / "reference_study.md", report_md(rows, cmp))
    return doc


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    ref = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ref / "study"
    doc = run(ref, out)
    print(f"{len(doc['videos'])} videos -> {out / 'reference_study.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
