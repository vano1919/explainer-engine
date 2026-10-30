"""The audio spine (Blueprint P4, docs/CONTRACTS.md ``audio_spine/1`` and ``/2``, D-88): every word of the narrator's read in
seconds and frames on ONE clock that the picture, the compensators and the sound all lock to. The spine is compiled from
``audio/words.json`` (the measured read) and ``timed.json`` (``production_timed/1``), never written by hand and never repaired:
words out of order, a word past the read, or a timed file that is not the same read raise ``ContractError`` (CN-01).

A word belongs to the timed line that holds its midpoint (a word between two lines, a padded pause, goes to the previous line);
the spine's ``line`` is the GLOBAL 0-based index into ``timed.lines`` and its ``segment`` is that line's segment. Frames are
``round(seconds * fps)`` with the timed file's fps, the rule CN-01 checks.

Post-hoc windows (D-88): a shot whose dialogue the video model speaks itself (LTX-native) is timed from its rendered clip, not
from the read. The spine reserves a window of the planned length right after ``after_word`` (the last read word before the
shot's line), every later word moves by it, and the narrator never plays inside it. The clip's measured length replaces the
planned one through the lifecycle back path ``retime`` (``retime_post_hoc`` returns the new spine; it edits nothing in place).
Which line is native is the lane decision of P6; until it marks them (``native_lines``), ``windows`` returns ``[]``.

    python -m explainer_engine.audio.spine <job folder> [--words FILE] [--timed FILE] [--film-shots FILE] [--out FILE]

Writes ``<job>/audio/audio_spine.json`` (``core/store.write_json_atomic``). numpy-free, stdlib only.
"""

from __future__ import annotations

import bisect
import copy
import json
import re
import sys
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

POST_HOC_LANES = ("DIALOGUE_CU", "KEYFRAME_LTX")  # the lanes whose clip may speak its own line (D-88)
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _sec(x: float) -> float:
    return round(float(x), 3)  # times in a contract are seconds with three decimals


def check_read(words_doc: dict, timed: dict) -> None:
    """CN-01 on the two inputs, before anything is derived: one read, words in order, none past the end. Raises, never repairs."""
    fps = timed["fps"]
    words, tol = words_doc["words"], 1.0 / fps
    if not words:
        raise ContractError("words.json holds no words")
    if abs(float(timed["duration"]) - float(words_doc["duration"])) > tol:
        raise ContractError(f"timed.json is {timed['duration']} s and words.json {words_doc['duration']} s: not the same read "
                            f"(more than one frame, {tol:.3f} s, apart)")
    prev = -1.0
    for i, w in enumerate(words):
        if w["e"] < w["s"] or w["s"] < prev:
            raise ContractError(f"word {i} ({w['w']!r}, {w['s']}..{w['e']} s) is out of order; the compiler never sorts")
        if w["e"] > float(words_doc["duration"]) + tol:
            raise ContractError(f"word {i} ({w['w']!r}) ends at {w['e']} s, past the {words_doc['duration']} s of the read")
        prev = w["s"]
    lines = timed["lines"]
    for k in range(1, len(lines)):
        if lines[k]["start"] < lines[k - 1]["start"]:
            raise ContractError(f"timed line {k} starts before line {k - 1}: the lines are out of order")


def word_segments(words: list[dict], lines: list[dict]) -> list[tuple[str, int]]:
    """For each word the ``(segment id, global line index)`` of the timed line that holds its midpoint; a word between lines goes
    to the previous line. A word before the first line has no line and raises (nothing is invented for it)."""
    if not lines:
        raise ContractError("timed.json holds no lines")
    starts = [ln["start"] for ln in lines]
    out = []
    for i, w in enumerate(words):
        k = bisect.bisect_right(starts, (w["s"] + w["e"]) / 2) - 1
        if k < 0:
            raise ContractError(f"word {i} ({w['w']!r}) at {w['s']} s lies before the first timed line ({starts[0]} s)")
        out.append((lines[k]["segment"], k))
    return out


def native_lines(film_shots: dict | None, lines: list[dict]) -> list[dict]:
    """The shots whose dialogue the video model speaks: ``[{shot_id, line, frames}]`` with ``line`` the global index into
    ``timed.lines`` and ``frames`` the shot's ``duration_frames`` (lanes in ``POST_HOC_LANES``). P6 decides which line is native and
    adds the marker (docs/CONTRACTS.md, D-88); no marker exists yet, so nothing is native and this returns ``[]``."""
    return []


def windows(film_shots: dict | None, words: list[dict], lines: list[dict], fps: int, *, native: list[dict] | None = None) -> list[dict]:
    """The post-hoc windows, in timeline order: ``[{shot_id, after_word, frames}]``. ``after_word`` is the last read word of any line
    before the native line (-1 = before the first word). ``native`` injects the marker's answer (``[{shot_id, line, frames}]``) so the
    window math is testable before P6; by default it comes from ``native_lines(film_shots, lines)``."""
    found = native_lines(film_shots, lines) if native is None else native
    if not found:
        return []
    word_line = [k for _seg, k in word_segments(words, lines)]
    out = []
    for n, row in enumerate(sorted(enumerate(found), key=lambda p: (p[1]["line"], p[0]))):
        shot = row[1]
        if not 0 <= shot["line"] < len(lines):
            raise ContractError(f"{shot['shot_id']}: line {shot['line']} is not a timed line (0..{len(lines) - 1})")
        if shot["frames"] <= 0:
            raise ContractError(f"{shot['shot_id']}: a window needs a positive length, not {shot['frames']} frames")
        before = [i for i, k in enumerate(word_line) if k < shot["line"]]
        out.append({"shot_id": shot["shot_id"], "after_word": before[-1] if before else -1, "frames": int(shot["frames"])})
    return out


def _moved(seconds: float, old_frame: int, shift: int, fps: int) -> tuple[float, int]:
    """A word edge moved by ``shift`` frames: the frame is exactly old + shift; the seconds are the old ones plus the shift, or the
    frame's own time when rounding would put them on the neighbouring frame (CN-01: frame == round(seconds * fps))."""
    frame = old_frame + shift
    moved = _sec(seconds + shift / fps)
    return (moved, frame) if round(moved * fps) == frame else (_sec(frame / fps), frame)  # at most half a frame from the exact seconds


def compile_spine(words_doc: dict, timed: dict, *, film_shots: dict | None = None, refs: dict[str, dict],
                  native: list[dict] | None = None) -> dict:
    """``audio_spine/2`` when the job has ``film_shots`` or a window, else ``/1`` (every older reader and fixture is unchanged).
    ``refs`` is ``{"words": {path, sha256}, "timed": {...}, "film_shots": {...}}``, paths relative to the job folder (CN-02)."""
    check_read(words_doc, timed)
    fps, words, lines = timed["fps"], words_doc["words"], timed["lines"]
    placed = word_segments(words, lines)
    seg_ids = [s["id"] for s in timed["segments"]]
    order = list(dict.fromkeys(seg for seg, _k in placed))
    if any(seg not in seg_ids for seg in order) or order != [s for s in seg_ids if s in order]:
        raise ContractError(f"the words visit the segments {order}, not in the timed order {seg_ids}")
    if film_shots is not None and "film_shots" not in refs:
        raise ContractError("film_shots given without its file reference in refs (CN-02 needs its sha256)")
    wins = windows(film_shots, words, lines, fps, native=native)

    shift = [0] * len(words)  # frames every word is moved by: the windows opened before it
    for h in wins:
        for i in range(h["after_word"] + 1, len(words)):
            shift[i] += h["frames"]
    out_words = []
    for i, (w, (seg, k)) in enumerate(zip(words, placed)):
        s, e = _sec(w["s"]), _sec(w["e"])
        sf, ef = round(s * fps), round(e * fps)
        if shift[i]:
            s, sf = _moved(s, sf, shift[i], fps)
            e, ef = _moved(e, ef, shift[i], fps)
        out_words.append({"i": i, "text": w["w"], "start_s": s, "end_s": e, "start_frame": sf, "end_frame": ef, "segment": seg, "line": k})

    segments = []
    for sid in seg_ids:
        idx = [w["i"] for w in out_words if w["segment"] == sid]
        if not idx:
            raise ContractError(f"segment {sid} has no word in the read: the read skipped it")
        if idx != list(range(idx[0], idx[-1] + 1)):
            raise ContractError(f"the words of segment {sid} are not one run")
        segments.append({"id": sid, "start_frame": out_words[idx[0]]["start_frame"], "end_frame": out_words[idx[-1]]["end_frame"]})

    post_hoc, opened = [], {}  # opened: frames already opened after the same word (several windows may share an anchor)
    for h in wins:
        a = h["after_word"]
        base = 0 if a < 0 else out_words[a]["end_frame"]
        start = base + opened.get(a, 0)
        opened[a] = opened.get(a, 0) + h["frames"]
        post_hoc.append({"shot_id": h["shot_id"], "start_frame": start, "end_frame": start + h["frames"], "after_word": a,
                         "source": "planned", "clip_sha256": None})
    v2 = film_shots is not None or bool(wins)
    if not v2:
        post_hoc = []
    derived = {"words": refs["words"], "timed": refs["timed"]}
    if film_shots is not None:
        derived["film_shots"] = refs["film_shots"]
    extra = sum(h["frames"] for h in wins)
    doc = {"schema": "audio_spine/2" if v2 else "audio_spine/1", "derived_from": derived, "fps": fps,
           "duration_s": _sec(words_doc["duration"] + extra / fps), "total_frames": int(timed["frames"]) + extra,
           "words": out_words, "segments": segments, "post_hoc_shots": post_hoc}
    contracts.validate(doc)
    return doc


def read_time(spine: dict, frame: int) -> float:
    """An episode frame as seconds in the narrator's read: the windows opened before it are taken out (the inverse of the shift in
    ``compile_spine``). A frame inside a window has no read time; the read waits at the window's start, so that is returned."""
    gone = 0
    for h in spine["post_hoc_shots"]:
        if frame >= h["end_frame"]:
            gone += h["end_frame"] - h["start_frame"]
        elif frame > h["start_frame"]:
            return (h["start_frame"] - gone) / spine["fps"]
        else:
            break
    return (frame - gone) / spine["fps"]


def retime_post_hoc(spine: dict, shot_id: str, clip_frames: int, clip_sha256: str) -> dict:
    """The spine after P7 measured the rendered clip: the window takes the clip's length (source ``clip``) and everything after it
    moves by the difference. Returns a new, validated ``audio_spine/2``; a changed length is the lifecycle back path ``retime``
    (docs/CONTRACTS.md), so nothing downstream is edited in place."""
    if spine.get("schema") != "audio_spine/2":
        raise ContractError("only an audio_spine/2 has anchored windows to retime")
    if clip_frames <= 0 or not _SHA.match(clip_sha256 or ""):
        raise ContractError(f"a measured clip is a positive frame count and a sha256, not {clip_frames!r} and {clip_sha256!r}")
    new = copy.deepcopy(spine)
    hits = [h for h in new["post_hoc_shots"] if h["shot_id"] == shot_id]
    if len(hits) != 1:
        raise ContractError(f"{shot_id}: the spine has {len(hits)} windows for it, not one")
    hit, fps = hits[0], new["fps"]
    delta = clip_frames - (hit["end_frame"] - hit["start_frame"])
    old_end = hit["end_frame"]
    hit.update(end_frame=hit["start_frame"] + clip_frames, source="clip", clip_sha256=clip_sha256)
    if delta:
        for w in new["words"]:
            if w["start_frame"] >= old_end:
                w["start_s"], w["start_frame"] = _moved(w["start_s"], w["start_frame"], delta, fps)
                w["end_s"], w["end_frame"] = _moved(w["end_s"], w["end_frame"], delta, fps)
        for other in new["post_hoc_shots"]:
            if other is not hit and other["start_frame"] >= old_end:
                other["start_frame"] += delta
                other["end_frame"] += delta
        for seg in new["segments"]:
            first = next(w for w in new["words"] if w["segment"] == seg["id"])
            last = [w for w in new["words"] if w["segment"] == seg["id"]][-1]
            seg["start_frame"], seg["end_frame"] = first["start_frame"], last["end_frame"]
        new["total_frames"] += delta
        new["duration_s"] = _sec(new["duration_s"] + delta / fps)
    contracts.validate(new)
    return new


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ref(job: Path, path: Path) -> dict:
    return {"path": path.resolve().relative_to(job.resolve()).as_posix(), "sha256": contracts.sha256_file(path)}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts = {}
    for flag in ("--words", "--timed", "--film-shots", "--out"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1] if i + 1 < len(args) else ""
            del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    job = Path(args[0])
    words_path = Path(opts["--words"]) if "--words" in opts else next(
        (p for p in (job / "audio" / "words.json", job / "words.json") if p.exists()), job / "audio" / "words.json")
    timed_path = Path(opts["--timed"]) if "--timed" in opts else job / "timed.json"
    shots_path = Path(opts["--film-shots"]) if "--film-shots" in opts else job / "film_shots.json"
    out = Path(opts["--out"]) if "--out" in opts else job / "audio" / "audio_spine.json"
    try:
        shots = _load(shots_path) if shots_path.exists() else None
        refs = {"words": _ref(job, words_path), "timed": _ref(job, timed_path)}
        if shots is not None:
            refs["film_shots"] = _ref(job, shots_path)
        doc = compile_spine(_load(words_path), _load(timed_path), film_shots=shots, refs=refs)
        contracts.validate(doc, job)
    except (ContractError, FileNotFoundError, ValueError) as exc:
        print(f"audio spine: {exc}")
        return 1
    write_json_atomic(out, doc)
    print(f"{out}: {doc['schema']}, {len(doc['words'])} words, {len(doc['segments'])} segments, {doc['total_frames']} frames at "
          f"{doc['fps']} fps, {len(doc['post_hoc_shots'])} window(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
