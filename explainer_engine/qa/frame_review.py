"""Claude's own look at a render before the creator sees it (standing order 12, docs/PRODUCTION_RULES.md; the creator,
2026-10-20: "why can't you watch and evaluate it yourself?"). Free and local: ffmpeg + PIL, no paid call.

    python -m explainer_engine.qa.frame_review <timed.json> <video.mp4> [--from S --to S] [--offset S]
                                               [--pictures DIR ...] --out DIR

1. The moments that matter inside the range, read from ``timed.json`` (``production/timing``): every cut (0.15 s before and
   after), every bubble's start / middle / end, every visual beat's start, every change of the dialogue face frame
   (``production/faces.composite``: the keyed close-up over the blurred scene), every dissolve's midpoint. Each moment's frame
   is pulled from the video (``WIDTH`` px wide), labelled with its time and what it is, and laid out on contact sheets
   (``sheet_NN.jpg``) that Claude opens and looks at, every one, before anything is shown to the creator.
2. Deterministic checks on the timing data, the same timeline the renderer draws (FR rules, the repo's FAIL / REVIEW):

   FR-BUBBLE-CUT    FAIL    a bubble's interval crosses a cut (it is cut off mid-line or lands on another picture)
   FR-BUBBLE-FACE   FAIL    a bubble's interval crosses a change of the face frame (the close-up eases in or out, or swaps
                            hero, under a still bubble: its tail then points at nothing)
   FR-BUBBLE-WHO    FAIL    a bubble shown over the close-up of a different hero than its speaker (one hero's words on
                            another's face); REVIEW over its own speaker's close-up (the tail is laid out on the scene)
   FR-BUBBLE-TAIL   REVIEW  the speaker has no face point in the shot's picture (the tail points at a default spot)
   FR-RING-FACE     FAIL    a picture-bound mark (highlight ring, label) drawn while a close-up fills the frame: it points
                            into a picture that is not on screen
   FR-RING-HERO     FAIL    a ring on a named hero (its ``at`` names him) that does not enclose his face point
   FR-RING-LOOK     REVIEW  every other ring: the timing data carries no prop points, so it is checked on the sheet
   FR-FACE-RATE     REVIEW  more than ``SWAP_MAX`` face-frame changes in ``SWAP_WINDOW_S``
   FR-FACE-HOLD     REVIEW  a face shown shorter than BP-33's hold
   FR-FACE-GHOST    REVIEW  a close-up cross-fading within ``GHOST_S`` of a cut (the hero shows twice right after it)
   FR-TEXT-CUT      REVIEW  a screen-bound mark (text, symbol, prop, chart) carried across a cut into another picture
   FR-LOUDNESS      BP-50 verdict on the rendered range (``qa/targets``)

Exit 1 on any FAIL. ``review.json`` in ``--out`` lists every moment, every finding and the sheets.
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from explainer_engine.core.store import write_json_atomic
from explainer_engine.production import accents as ACC
from explainer_engine.production import faces as FACES
from explainer_engine.qa import targets as TG
from explainer_engine.standards import sourced_rules as SR

SCHEMA = "frame_review/1"
CUT_PAD_S = 0.15  # frames this far before and after each cut: the last frame of one picture and the first of the next
WIDTH = 480  # px of each extracted frame: enough to see a face, a ring or a bubble's tail, small enough for a sheet
COLS, ROWS = 4, 5  # tiles per contact sheet
# House heuristic (REVIEW only, no sourced rule yet): the creator, 2026-10-20, on the first Titans preview: "faces swap every
# 1-2 s". More than 3 face-frame changes in 5 s means a face lasts under ~1.7 s on average; Claude looks at those spans.
SWAP_WINDOW_S = 5.0
SWAP_MAX = 3
RING_R = 0.13  # beats.draw: a ring's radius is 0.13 of the frame's short side, its height 0.8 of that
RING_ASPECT = 0.8
# A ring meant for a hero is centred on him: his face point within half the ring's radius of its centre. The 2026-10-20
# preview's "Elon Musk" ring held his point at 0.77 of the radius and on the sheet it circled the wall beside his face.
RING_CENTRE = 0.5
# House heuristic (REVIEW): a close-up that starts cross-fading within this long of a cut doubles the hero (the scene's figure
# and the big face at once) right after the cut, read as a stutter on the 2026-10-20 preview (SH016 at 94.8 s).
GHOST_S = 0.5
OVERLAY = ("text", "symbol", "prop", "chart")  # beats.draw's screen-bound marks: they are not cut off by their shot


def _f(out: list, rule: str, sev: str, where: str, detail: str, t: float | None = None) -> None:
    row = {"rule": rule, "severity": sev, "where": where, "detail": detail}
    out.append(row if t is None else dict(row, t=round(t, 3)))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --- the face frame, as faces.composite draws it -----------------------------------------------------------------------------

def close_up_beats(timed: dict, s: dict, picture_dirs: list[Path] | None) -> list[dict]:
    """The expression beats of shot ``s`` that the renderer turns into a close-up (VB-09). With ``picture_dirs`` exactly the
    painted ones (assemble.beats_for_shot); without them every expression of a hero who has a face sheet (the render's case
    once the sheet is painted)."""
    beats = [b for b in timed.get("visual_beats", []) if b["kind"] == "expression" and b.get("shot") == s["id"]]
    sheets = timed.get("face_sheets", {})
    if picture_dirs is not None:
        cast = {who: {"face_sheet": sh} for who, sh in sheets.items()}
        painted = {(b["start_frame"], b["who"]) for b in FACES.sheet_beats(beats, cast, picture_dirs)}
        beats = [b for b in beats if (b["start_frame"], b.get("who")) in painted]
    else:
        beats = [b for b in beats if b.get("who") in sheets]
    return sorted(beats, key=lambda b: b["start_frame"])


def face_at(faces: list[dict], f: int, fps: int) -> tuple[str, str] | None:
    """(hero, expression) of the close-up filling frame ``f`` of a shot whose close-up beats are ``faces``, or None when the
    scene is on screen. Mirrors faces.composite: the span is eased in and out over EASE_S, a change lands EXPR_LEAD_FRAMES
    before its word."""
    if not faces:
        return None
    lead = ACC.EXPR_LEAD_FRAMES
    ease = FACES.EASE_S * fps
    s0 = min(b["start_frame"] for b in faces) - lead
    s1 = max(b["end_frame"] for b in faces)
    if not s0 - ease < f < s1 + ease:  # the weight is 0 at both ends of the eased span
        return None
    cur = [b for b in faces if b["start_frame"] - lead <= f]
    b = cur[-1] if cur else faces[0]
    return (b.get("who"), b.get("expression"))


def face_track(timed: dict, picture_dirs: list[Path] | None) -> tuple[dict, list[dict]]:
    """{shot id: close-up beats} and the face frame's runs over the whole film: [{start, end, face}] with face None for the
    scene, one run per change, cuts included."""
    fps = timed["fps"]
    per_shot = {s["id"]: close_up_beats(timed, s, picture_dirs) for s in timed["shots"]}
    runs: list[dict] = []
    for s in timed["shots"]:
        faces = per_shot[s["id"]]
        for f in range(s["start_frame"], s["end_frame"]):
            st = face_at(faces, f, fps)
            if runs and runs[-1]["face"] == st and runs[-1]["end_frame"] == f:
                runs[-1]["end_frame"] = f + 1
            else:
                runs.append({"face": st, "start_frame": f, "end_frame": f + 1, "shot": s["id"]})
    for r in runs:
        r["start"], r["end"] = r["start_frame"] / fps, r["end_frame"] / fps
    return per_shot, runs


# --- checks ------------------------------------------------------------------------------------------------------------------

def _in(t0: float, t1: float, lo: float | None, hi: float | None) -> bool:
    return (lo is None or t1 > lo) and (hi is None or t0 < hi)


def check(timed: dict, picture_dirs: list[Path] | None = None, t_from: float | None = None,
          t_to: float | None = None) -> list[dict]:
    """The FR findings of the timing data inside [t_from, t_to)."""
    out: list[dict] = []
    fps = timed["fps"]
    pics = timed.get("pictures", {})
    per_shot, runs = face_track(timed, picture_dirs)
    shots = timed["shots"]
    cuts = [s["start"] for s in shots[1:]]

    for s in shots:
        faces = per_shot[s["id"]]
        speakers = pics.get(s["picture"], {}).get("speakers") or {}
        for b in s.get("bubbles") or []:
            if not _in(b["start"], b["end"], t_from, t_to):
                continue
            where = f"{s['id']} {b['text'][:40]!r}"
            if b["start"] < s["start"] - 1e-6 or b["end"] > s["end"] + 1e-6:
                _f(out, "FR-BUBBLE-CUT", "FAIL", where, f"bubble {b['start']:.2f}-{b['end']:.2f} s runs past its shot "
                   f"{s['start']:.2f}-{s['end']:.2f} s: end the bubble before the cut or move the cut", b["start"])
            else:
                crossed = [c for c in cuts if b["start"] + 1e-6 < c < b["end"] - 1e-6]
                if crossed:
                    _f(out, "FR-BUBBLE-CUT", "FAIL", where, f"a cut at {crossed[0]:.2f} s inside the bubble", crossed[0])
            if b.get("who") and b["who"] not in speakers and b.get("kind", "speech") != "narration":
                _f(out, "FR-BUBBLE-TAIL", "REVIEW", where, f"{b['who']} has no face point in {s['picture']}: the tail points at "
                   "a default spot of the frame", b["start"])
            f0, f1 = max(b["start_frame"], s["start_frame"]), min(b["end_frame"], s["end_frame"])
            seen = [face_at(faces, f, fps) for f in range(f0, f1)]
            if not seen:
                continue
            changes = [f0 + i for i in range(1, len(seen)) if seen[i] != seen[i - 1]
                       and (seen[i] is None or seen[i - 1] is None or seen[i][0] != seen[i - 1][0])]
            if changes:
                a, z = seen[changes[0] - f0 - 1], seen[changes[0] - f0]
                _f(out, "FR-BUBBLE-FACE", "FAIL", where, f"the face frame changes under the bubble at "
                   f"{changes[0] / fps:.2f} s ({_name(a)} -> {_name(z)}): a bubble starts and ends on one frame", changes[0] / fps)
            others = sorted({st[0] for st in seen if st is not None and st[0] != b.get("who")})
            if others:
                first = next(f0 + i for i, st in enumerate(seen) if st is not None and st[0] != b.get("who"))
                _f(out, "FR-BUBBLE-WHO", "FAIL", where, f"{b.get('who')}'s words over {', '.join(others)}'s close-up from "
                   f"{first / fps:.2f} s: show the speaker's face while he speaks, or end the close-up first", first / fps)
            elif any(st is not None for st in seen):
                first = next(f0 + i for i, st in enumerate(seen) if st is not None)
                _f(out, "FR-BUBBLE-WHO", "REVIEW", where, f"bubble over {b.get('who')}'s own close-up from {first / fps:.2f} s: "
                   "its tail is laid out on the scene, check where it points", first / fps)

    by_id = {s["id"]: s for s in shots}
    for b in timed.get("visual_beats", []):
        if b["kind"] not in ("highlight", "label") or not _in(b["start"], max(b["end"], b["start"] + 1 / fps), t_from, t_to):
            continue
        s = by_id.get(b.get("shot"))
        if s is None:
            continue
        where = f"{s['id']} {b['kind']} {b.get('at', '')!r}"
        faces = per_shot[s["id"]]
        e = max(b["end_frame"], b["start_frame"] + 1)
        on_face = [f for f in range(max(b["start_frame"], s["start_frame"]), min(e, s["end_frame"])) if face_at(faces, f, fps)]
        if on_face:
            _f(out, "FR-RING-FACE", "FAIL", where, f"drawn over {face_at(faces, on_face[0], fps)[0]}'s close-up at "
               f"{on_face[0] / fps:.2f} s: it points into a picture that is not on screen", on_face[0] / fps)
        if b["kind"] != "highlight":
            continue
        pic = pics.get(s["picture"], {})
        speakers = pic.get("speakers") or {}
        aspect = pic.get("aspect") or 16 / 9
        rx = RING_R * (b.get("strength") or 1.0) / aspect  # the short side is the height: x in picture widths
        ry = RING_R * RING_ASPECT * (b.get("strength") or 1.0)
        pos = b.get("pos") or (0.5, 0.5)
        dist = {w: math.hypot((p[0] - pos[0]) / rx, (p[1] - pos[1]) / ry) for w, p in speakers.items()}
        inside = [w for w, r in dist.items() if r <= 1]
        named = [w for w in _heroes(timed) if w in _norm(b.get("at", ""))]
        if named:
            for w in named:
                if w not in speakers:
                    _f(out, "FR-RING-LOOK", "REVIEW", where, f"rings {w}, who has no face point in {s['picture']}: check the "
                       "sheet", b["start"])
                elif dist[w] > RING_CENTRE:
                    p = speakers[w]
                    _f(out, "FR-RING-HERO", "FAIL", where, f"ring at ({pos[0]:.2f}, {pos[1]:.2f}) misses {w} at "
                       f"({p[0]:.2f}, {p[1]:.2f}) ({dist[w]:.2f} of its radius off centre, at most {RING_CENTRE}): centre the "
                       "ring on him", b["start"])
        else:
            what = f"on {', '.join(inside)}" if inside else "on no hero point"
            _f(out, "FR-RING-LOOK", "REVIEW", where, f"ring at ({pos[0]:.2f}, {pos[1]:.2f}) {what}; the timing data has no prop "
               f"points: check on the sheet that it circles {b.get('at', 'its thing')!r}", b["start"])

    for b in timed.get("visual_beats", []):
        if b["kind"] not in OVERLAY or not _in(b["start"], b["end"], t_from, t_to):
            continue
        crossed = [c for c in cuts if b["start"] + 1e-6 < c < b["end"] - 1e-6]
        if crossed:
            _f(out, "FR-TEXT-CUT", "REVIEW", f"{b.get('shot')} {b['kind']} {b.get('at', '')!r}",
               f"stays on screen across the cut at {crossed[0]:.2f} s into another picture: end it with its shot unless it is "
               "meant to carry over", crossed[0])

    ease = FACES.EASE_S * fps
    for s in shots:
        faces = per_shot[s["id"]]
        if not faces or not _in(s["start"], s["end"], t_from, t_to):
            continue
        s0 = min(b["start_frame"] for b in faces) - ACC.EXPR_LEAD_FRAMES
        s1 = max(b["end_frame"] for b in faces)
        f0, f1, g = s["start_frame"], s["end_frame"] - 1, GHOST_S * fps
        if f0 - g < s0 - ease < f0 + g or s0 - ease < f0 < s0 + ease or s1 < f1 < s1 + ease:
            _f(out, "FR-FACE-GHOST", "REVIEW", s["id"], "the close-up cross-fades in or out within "
               f"{GHOST_S} s of the cut: the hero shows twice (scene and close-up) right after a cut; open the shot on the close-up "
               "or let the scene hold first", s["start"])

    hold = float(SR.T("BP-33", "hold_min_s"))
    seen_runs = [r for r in runs if _in(r["start"], r["end"], t_from, t_to)]
    for r in seen_runs:
        if r["face"] is not None and r["end"] - r["start"] < hold - 1e-6:
            _f(out, "FR-FACE-HOLD", "REVIEW", r["shot"], f"{_name(r['face'])} on screen {r['end'] - r['start']:.2f} s < "
               f"{hold} s (BP-33)", r["start"])
    changes = [r["start"] for r in seen_runs[1:]]
    k = 0
    while k < len(changes):
        n = sum(1 for c in changes if changes[k] <= c < changes[k] + SWAP_WINDOW_S)
        if n > SWAP_MAX:
            last = max(c for c in changes if c < changes[k] + SWAP_WINDOW_S)
            _f(out, "FR-FACE-RATE", "REVIEW", f"{changes[k]:.1f}-{last:.1f} s", f"{n} face-frame changes in {SWAP_WINDOW_S:g} s "
               f"(at most {SWAP_MAX}): faces swap faster than the eye settles", changes[k])
            k = next((i for i, c in enumerate(changes) if c >= changes[k] + SWAP_WINDOW_S), len(changes))
        else:
            k += 1
    return out


def _name(st) -> str:
    return "the scene" if st is None else f"{st[0]} {st[1]}"


def _heroes(timed: dict) -> list[str]:
    ids = set(timed.get("face_sheets", {}))
    for p in timed.get("pictures", {}).values():
        ids |= set(p.get("heroes") or []) | set(p.get("speakers") or {})
    return sorted(i for i in ids if len(_norm(i)) >= 3)


# --- moments and frames -------------------------------------------------------------------------------------------------------

def moments(timed: dict, picture_dirs: list[Path] | None = None, t_from: float | None = None,
            t_to: float | None = None) -> list[dict]:
    """Every moment that matters inside the range, in time order: {t, kind, what}."""
    fps = timed["fps"]
    out: list[dict] = []

    def add(t: float, kind: str, what: str) -> None:
        if (t_from is None or t >= t_from) and (t_to is None or t < t_to) and t >= 0:
            out.append({"t": round(t, 3), "kind": kind, "what": what})

    shots = timed["shots"]
    for prev, s in zip(shots, shots[1:]):
        add(s["start"] - CUT_PAD_S, "cut-before", f"{prev['id']} {prev['picture']} (last frame before the cut)")
        add(s["start"] + CUT_PAD_S, "cut-after", f"{s['id']} {s['picture']} (first frame after the cut)")
        if s.get("transition") == "dissolve":
            add(s["start"] + float(s.get("transition_seconds", 1.0)) / 2, "dissolve", f"{prev['id']} -> {s['id']} midpoint")
    for s in shots:
        for b in s.get("bubbles") or []:
            for label, t in (("start", b["start"] + 2 / fps), ("middle", (b["start"] + b["end"]) / 2),
                             ("end", b["end"] - 2 / fps)):
                add(t, f"bubble-{label}", f"{s['id']} {b.get('who')}: {b['text'][:40]!r}")
    for b in timed.get("visual_beats", []):
        if b["kind"] == "accent":
            add(b["start"] + 2 / fps, "beat", f"{b['shot']} accent {b.get('effect', '')} {b.get('at', '')!r}")
            continue
        if b["kind"] == "expression":
            continue  # the face frame's own changes below are what the viewer sees
        life = max(1 / fps, b["end"] - b["start"])
        add(b["start"] + min(0.4, life / 2), "beat", f"{b['shot']} {b['kind']} {b.get('at', '')!r} pos={b.get('pos')}")
    _, runs = face_track(timed, picture_dirs)
    for prev, r in zip(runs, runs[1:]):
        if prev["shot"] == r["shot"]:
            add(r["start"] + 0.1, "face", f"{r['shot']} {_name(prev['face'])} -> {_name(r['face'])}")
    out.sort(key=lambda m: m["t"])
    return out


def _extract(video: Path, t: float, dest: Path) -> bool:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(video),
           "-frames:v", "1", "-vf", f"scale={WIDTH}:-2", "-q:v", "4", str(dest)]
    return subprocess.run(cmd, capture_output=True).returncode == 0 and dest.exists()


def extract_frames(video: Path, ms: list[dict], out: Path, offset: float = 0.0) -> None:
    """One small JPEG per moment (``frames/NNNN_<t>.jpg``); video time = timed time - offset."""
    d = out / "frames"
    d.mkdir(parents=True, exist_ok=True)

    def one(i_m):
        i, m = i_m
        dest = d / f"{i:04d}_{m['t']:08.3f}.jpg"
        m["frame"] = str(dest.relative_to(out)) if _extract(video, m["t"] - offset, dest) else None

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, enumerate(ms)))


def _font(size: int):
    try:
        return ImageFont.truetype(str(Path(__file__).resolve().parents[2] / "assets" / "fonts" / "ComicNeue-Bold.ttf"), size)
    except OSError:
        return ImageFont.load_default(size)


def contact_sheets(ms: list[dict], out: Path, flagged: dict[float, str]) -> list[str]:
    """Labelled tiles, COLS x ROWS per sheet; a tile near a FAIL / REVIEW finding gets a red / amber label."""
    tiles = [m for m in ms if m.get("frame")]
    sheets = []
    th = round(WIDTH * 9 / 16)
    lab = 40
    font = _font(15)
    for n in range(0, len(tiles), COLS * ROWS):
        part = tiles[n:n + COLS * ROWS]
        rows = math.ceil(len(part) / COLS)
        sheet = Image.new("RGB", (COLS * (WIDTH + 6) + 6, rows * (th + lab + 6) + 6), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for i, m in enumerate(part):
            x, y = 6 + (i % COLS) * (WIDTH + 6), 6 + (i // COLS) * (th + lab + 6)
            with Image.open(out / m["frame"]) as im:
                im = im.convert("RGB")
                sheet.paste(im.resize((WIDTH, th)) if im.size != (WIDTH, th) else im, (x, y + lab))
            sev = flagged.get(m["t"])
            col = {"FAIL": (200, 40, 40), "REVIEW": (190, 130, 20)}.get(sev, (60, 60, 60))
            d.rectangle([x, y, x + WIDTH, y + lab - 2], fill=col)
            d.text((x + 6, y + 2), f"{m['t']:.2f}s  {m['kind']}" + (f"  [{sev}]" if sev else ""), fill="white", font=font)
            d.text((x + 6, y + 20), m["what"][:62], fill="white", font=font)
        p = out / f"sheet_{n // (COLS * ROWS) + 1:02d}.jpg"
        sheet.save(p, quality=85)
        sheets.append(str(p))
    return sheets


def _flags(ms: list[dict], findings: list[dict], fps: int) -> dict[float, str]:
    """Moment time -> the worst finding within half a second of it."""
    rank = {"REVIEW": 1, "FAIL": 2}
    out: dict[float, str] = {}
    for f in findings:
        if "t" not in f or f["severity"] not in rank:
            continue
        for m in ms:
            if abs(m["t"] - f["t"]) <= 0.5 and rank[f["severity"]] > rank.get(out.get(m["t"]), 0):
                out[m["t"]] = f["severity"]
    return out


def loudness(video: Path, t_from: float | None, t_to: float | None, offset: float = 0.0) -> dict:
    """BP-50 on the rendered range: ffmpeg's ebur128 parsed and judged by qa/targets."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if t_from is not None:
        cmd += ["-ss", f"{max(0.0, t_from - offset):.3f}"]
    if t_to is not None:
        cmd += ["-t", f"{t_to - (t_from or 0.0):.3f}"]
    cmd += ["-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]
    meas = TG.parse_ebur128(subprocess.run(cmd, capture_output=True, text=True).stderr)
    if "lufs" not in meas:
        return {"error": "no loudness measured"}
    return {**meas, **TG.verdicts(meas, "long")}


def run(timed_path: Path, video: Path, out: Path, t_from: float | None = None, t_to: float | None = None,
        offset: float = 0.0, picture_dirs: list[Path] | None = None, frames: bool = True) -> dict:
    import json
    timed = json.loads(Path(timed_path).read_text(encoding="utf-8"))
    if picture_dirs is None:
        guess = Path(timed_path).resolve().parent.parent / "pictures"
        picture_dirs = [guess] if guess.is_dir() else None
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    findings = check(timed, picture_dirs, t_from, t_to)
    ms = moments(timed, picture_dirs, t_from, t_to)
    sheets: list[str] = []
    loud: dict = {}
    if frames:
        extract_frames(Path(video), ms, out, offset)
        sheets = contact_sheets(ms, out, _flags(ms, findings, timed["fps"]))
        loud = loudness(Path(video), t_from, t_to, offset)
        sev = loud.get("loudness_verdict")
        if sev in ("FAIL", "REVIEW"):
            _f(findings, "FR-LOUDNESS", sev, "range", f"{loud['lufs']} LUFS on the rendered range (BP-50)")
        elif "error" in loud:
            _f(findings, "FR-LOUDNESS", "REVIEW", "range", loud["error"])
    report = {"schema": SCHEMA, "timed": str(timed_path), "video": str(video), "from": t_from, "to": t_to, "offset": offset,
              "picture_dirs": [str(p) for p in picture_dirs] if picture_dirs else None,
              "counts": {s: sum(1 for f in findings if f["severity"] == s) for s in ("FAIL", "REVIEW")},
              "findings": findings, "loudness": loud, "sheets": sheets, "moments": ms,
              "looked_at": False}  # Claude sets it after opening every sheet (standing order 12)
    write_json_atomic(out / "review.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.qa.frame_review", description=__doc__.split("\n")[0])
    p.add_argument("timed")
    p.add_argument("video")
    p.add_argument("--from", dest="t_from", type=float)
    p.add_argument("--to", dest="t_to", type=float)
    p.add_argument("--offset", type=float, default=0.0, help="timed-time of the video's first frame (a part rendered later)")
    p.add_argument("--pictures", action="append", type=Path, help="picture folders (default <job>/pictures): which close-ups "
                   "are painted")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    r = run(Path(a.timed), Path(a.video), a.out, a.t_from, a.t_to, a.offset, a.pictures)
    print(f"frame review: {len(r['moments'])} moments, {len(r['sheets'])} sheets, {r['counts']['FAIL']} FAIL, "
          f"{r['counts']['REVIEW']} REVIEW; loudness {r['loudness'].get('lufs')} LUFS "
          f"({r['loudness'].get('loudness_verdict', '-')})")
    for f in r["findings"]:
        if f["severity"] == "FAIL":
            print(f"  FAIL {f['rule']} {f['where']}: {f['detail']}")
    for s in r["sheets"]:
        print(f"  sheet {s}")
    print(f"  {a.out / 'review.json'}: open every sheet before the creator sees the render (standing order 12)")
    return 1 if r["counts"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
