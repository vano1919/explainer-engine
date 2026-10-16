"""The Universal Rule Base checks (docs/UNIVERSAL_RULE_BASE.md, UR-01..UR-15) over a shot list. stdlib only.

A shot list is the edit: ``[{id, beat, phase, type A|B|C, emotion, sentences, start, end, motion, transition,
time_jump, place_change, palette, prompt, face, sound}]`` with times in seconds on the narration clock. ``words`` is
the narration's ``[{w, s, e}]`` (``audio/timings.align`` shifted to the programme clock). ``look`` is the episode's
look file (style suffix, cast names, palette per phase). Every finding names its rule; ``FAIL`` blocks, ``REVIEW``
goes to the creator. ``solve_cuts`` places cuts only inside narration pauses (UR-12).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

MOODS_FILE = Path(__file__).with_name("moods.json")
DURATIONS = {"A": (5.0, 7.0), "B": (3.5, 5.0), "C": (2.5, 4.0)}  # UR-11
FIRST_WINDOW = 30.0  # UR-02
FIRST_SLACK = 1.0  # a shot in the first 30 s stays within its minimum + this
FIRST_MIN_SHOTS = 6
HOOK_SECONDS = 5.0  # UR-01
FIRST_SOUND = 1.0
MAX_ZOOM = 1.15  # UR-13
A_ZOOM = (1.05, 1.08)
A_PAN_PER_5S = 0.06  # share of the frame width
B_PUSH_MAX = 1.10
C_PULL_MAX = 1.08
DISSOLVE_SECONDS = 1.0  # UR-14
DISSOLVE_SHARE = 0.10
EDGE = 0.05  # UR-12: a cut keeps this far from both words
CUT_MARKS = ",.:;?!—…"
BANNED = re.compile(r"\b(hyper-?realistic|photo-?realistic|photo(graph|graphy)?|unreal( engine)?|octane|3d render|"
                    r"cinematic photography)\b", re.I)
FACE_WORDS = re.compile(r"\b(face|faces|portrait|eyes|smil(e|es|ing)|grin(s|ning)?|looking at (the )?camera)\b", re.I)
FACE_NEGATIONS = re.compile(r"\b(no (visible )?faces?|faceless|faces? (hidden|not visible|turned away)|without faces?)\b",
                            re.I)
GREETINGS = re.compile(r"\b(welcome|hello|hi|hey|today'?s video|in this video|subscribe)\b", re.I)


def load_moods(path: Path = MOODS_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["moods"]


def mood_clause(emotion: str, moods: dict | None = None) -> str:
    return (moods or load_moods())[emotion]["clause"]


def grade_for(emotion: str, moods: dict | None = None) -> dict:
    return dict((moods or load_moods())[emotion]["grade"])


def compose_prompt(subject: str, emotion: str, look: dict, moods: dict | None = None) -> str:
    """subject (with its composition) + the mood clause + the episode's style suffix (UR-07, UR-09)."""
    return f"{subject.rstrip(' ,.')}, {mood_clause(emotion, moods)}{look['style_suffix']}"


def pauses_from_words(words: list[dict], edge: float = EDGE) -> list[tuple[float, float, str]]:
    """(after, before, mark): gaps after a punctuated word that leave room for a cut ``edge`` from both words."""
    out = []
    for a, b in zip(words, words[1:]):
        mark = a["w"].rstrip("\"'”’)")[-1:]
        if mark and mark in CUT_MARKS and b["s"] - a["e"] >= 2 * edge:
            out.append((float(a["e"]), float(b["s"]), mark))
    return out


def cut_ok(t: float, words: list[dict], edge: float = EDGE) -> bool:
    """A cut at ``t`` is inside a punctuated pause, at least ``edge`` from the word before and after (UR-12)."""
    before = [w for w in words if w["s"] < t]
    after = [w for w in words if w["s"] >= t]
    if not before:
        return after[0]["s"] - t >= edge  # before the first word
    if not after:
        return t - before[-1]["e"] >= edge  # after the last word
    last, nxt = before[-1], after[0]
    mark = last["w"].rstrip("\"'”’)")[-1:]
    return bool(mark) and mark in CUT_MARKS and t - last["e"] >= edge and nxt["s"] - t >= edge


def solve_cuts(shots: list[dict], words: list[dict], end: float, edge: float = EDGE) -> list[float] | None:
    """Cut times (shot starts after the first) inside pauses, each shot inside its UR-11 range (UR-02 in the first
    30 s), closest to the planned lengths (``planned`` or ``end - start``), or, when a shot has ``target`` (the time
    its picture's phrase ends), closest to that time. None when no placement exists: then hold, merge, or add a
    clause pause (UR-12); never cut mid-sentence."""
    cands = set()  # five cut positions inside each pause, rounded inward so cut_ok holds exactly
    for a, b, _ in pauses_from_words(words, edge):
        lo, hi = math.ceil((a + edge) * 1000 + 1e-6) / 1000, math.floor((b - edge) * 1000 - 1e-6) / 1000
        if hi >= lo:
            cands.update(round(min(max(lo + (hi - lo) * f, lo), hi), 3) for f in (0.0, 0.25, 0.5, 0.75, 1.0))
    cands = sorted(cands)
    planned = [float(s["planned"]) if "planned" in s else float(s.get("end", 0) - s.get("start", 0)) for s in shots]
    n = len(shots)
    points = [0.0] + [c for c in cands if 0 < c < end] + [end]
    # best[k][j] = (cost, previous j) for shot k ending at points[j]
    best: list[dict[int, tuple[float, int]]] = [dict() for _ in range(n)]
    for k in range(n):
        starts = {0: (0.0, -1)} if k == 0 else best[k - 1]
        for i, (cost, _) in starts.items():
            lo, hi = DURATIONS[shots[k]["type"]]
            if points[i] < FIRST_WINDOW:
                hi = lo + FIRST_SLACK  # UR-02
            for j in range(i + 1, len(points)):
                if (j == len(points) - 1) != (k == n - 1):
                    continue
                d = points[j] - points[i]
                if d > hi + 1e-9:
                    break
                if d < lo - 1e-9:
                    continue
                c = cost + ((points[j] - shots[k]["target"]) ** 2 if "target" in shots[k] else (d - planned[k]) ** 2)
                if j not in best[k] or c < best[k][j][0]:
                    best[k][j] = (c, i)
    last = len(points) - 1
    if last not in best[n - 1]:
        return None
    cuts, j = [], last
    for k in range(n - 1, 0, -1):
        j = best[k][j][1]
        cuts.append(points[j])
    return list(reversed(cuts))


def apply_cuts(shots: list[dict], cuts: list[float], end: float) -> list[dict]:
    bounds = [0.0] + list(cuts) + [end]
    return [dict(s, start=round(bounds[i], 3), end=round(bounds[i + 1], 3)) for i, s in enumerate(shots)]


def _first_sentence(words: list[dict]) -> list[dict]:
    out = []
    for w in words:
        out.append(w)
        if re.search(r"[.?!][\"'”’)]*$", w["w"]):
            break
    return out


def check_shots(shots: list[dict], words: list[dict], look: dict, moods: dict | None = None,
                sound_ids: set[str] | None = None) -> list[dict]:
    """Every [code] rule of the Universal Rule Base; a list of {rule, shot, severity, detail}."""
    moods = moods or load_moods()
    found: list[dict] = []

    def add(rule: str, shot: str, detail: str, severity: str = "FAIL") -> None:
        found.append({"rule": rule, "shot": shot, "severity": severity, "detail": detail})

    if not shots:
        add("UR-03", "-", "no shots")
        return found
    cast = [c.lower() for c in look.get("cast", [])]
    suffix = look.get("style_suffix", "")
    sentence_count = len(re.findall(r"[.?!][\"'”’)]*(?:\s|$)", " ".join(w["w"] for w in words))) if words else 0

    # UR-01 hook
    first = shots[0]
    moving = first.get("motion", {}).get("kind", "static") != "static"
    if not (first["type"] == "C" or (first["type"] == "A" and moving)):
        add("UR-01", first["id"], f"opens on a {'static ' if not moving else ''}{first['type']} shot; needs C or a moving A")
    if words:
        lead = _first_sentence(words)
        if not lead[-1]["w"].rstrip("\"'”’)").endswith("?") and not any(w["w"].endswith("?") and w["e"] <= HOOK_SECONDS
                                                                        for w in words):
            add("UR-01", first["id"], f"no question asked in the first {HOOK_SECONDS:.0f} s")
        if GREETINGS.search(" ".join(w["w"] for w in lead)):
            add("UR-01", first["id"], "the first sentence greets instead of asking")
        sound = first.get("sound_at")
        if words[0]["s"] > FIRST_SOUND and (sound is None or sound > FIRST_SOUND):
            add("UR-01", first["id"], f"no sound event in the first {FIRST_SOUND:.0f} s")

    # UR-02 first 30 s
    early = [s for s in shots if s["start"] < FIRST_WINDOW]
    if shots[-1]["end"] >= FIRST_WINDOW and len(early) < FIRST_MIN_SHOTS:
        add("UR-02", "-", f"{len(early)} shots start in the first {FIRST_WINDOW:.0f} s; needs >= {FIRST_MIN_SHOTS}")
    for s in early:
        d = s["end"] - s["start"]
        cap = DURATIONS.get(s["type"], (0.0, 0.0))[0] + FIRST_SLACK
        if s["type"] in DURATIONS and d > cap + 1e-6:
            add("UR-02", s["id"], f"{s['type']} shot of {d:.2f} s in the first {FIRST_WINDOW:.0f} s (max {cap:.1f})")

    prev = None
    run = 1
    dissolves = 0
    for i, s in enumerate(shots):
        sid = s["id"]
        d = s["end"] - s["start"]
        # UR-03 arc
        if not s.get("beat"):
            add("UR-03", sid, "no beat")
        sents = s.get("sentences") or []
        if not sents:
            add("UR-03", sid, "shows no sentence of the narration")
        elif sentence_count and any(not 0 <= k < sentence_count for k in sents):
            add("UR-03", sid, f"sentence ids {sents} outside 0..{sentence_count - 1}")
        if prev is not None and abs(s["start"] - prev["end"]) > 1e-3:
            add("UR-03", sid, f"gap or overlap with the previous shot ({prev['end']:.3f} -> {s['start']:.3f})")
        # UR-04 / UR-05 types and sequence
        if s["type"] not in DURATIONS:
            add("UR-04", sid, f"unknown shot type {s['type']!r}")
            prev = s
            continue
        if prev is not None and prev["type"] == s["type"]:
            run += 1
            if run > 2:
                add("UR-05", sid, f"three {s['type']} shots in a row")
        else:
            run = 1
        if prev is not None and prev.get("beat") != s.get("beat") and s["type"] != "A" and s["start"] >= FIRST_WINDOW:
            add("UR-05", sid, f"beat {s.get('beat')!r} opens on {s['type']}, not A", "REVIEW")
        # UR-06 / UR-07 prompts
        prompt = s.get("prompt")
        if prompt:
            low = prompt.lower()
            for name in cast:
                if re.search(rf"\b{re.escape(name)}\b", low):
                    add("UR-06", sid, f"the pod prompt names {name!r}; identity comes from props or our sprite")
            if FACE_WORDS.search(FACE_NEGATIONS.sub(" ", prompt)):
                add("UR-06", sid, "the pod prompt asks for a face")
            if BANNED.search(prompt):
                add("UR-07", sid, f"banned style word {BANNED.search(prompt).group(0)!r} (the look is painted, D-27)")
            if suffix and not prompt.endswith(suffix):
                add("UR-07", sid, "the prompt does not end with the style suffix")
        face = str(s.get("face", ""))
        if s["type"] == "B" and not (face == "faceless" or face.startswith("caricature")):
            add("UR-06", sid, "B shot without a face branch (caricature:<name> | faceless)")
        if face.startswith("caricature:") and "caricatures" in look:
            missing = [n for n in face.split(":", 1)[1].split("+") if n not in look["caricatures"]]
            if missing:
                add("UR-06", sid, f"no reusable caricature for {missing}: use the faceless branch")
        # UR-08 palette
        phase = (look.get("phases") or {}).get(s.get("phase", ""), None)
        if phase is None:
            add("UR-08", sid, f"phase {s.get('phase')!r} has no palette in the look")
        else:
            outside = [c for c in s.get("palette", []) if c not in phase["palette"]]
            if not s.get("palette"):
                add("UR-08", sid, "no palette named")
            if outside:
                add("UR-08", sid, f"colours outside the phase palette: {outside}")
        # UR-09 / UR-10 emotion
        emo = s.get("emotion")
        if emo not in moods:
            add("UR-09", sid, f"emotion {emo!r} is not in the vocabulary")
        elif prompt and moods[emo]["clause"] not in prompt:
            add("UR-09", sid, f"the prompt lacks the {emo} mood clause")
        if prev is not None and emo and prev.get("emotion") and emo != prev["emotion"] \
                and prev.get("beat") == s.get("beat") and not s.get("sound"):
            add("UR-10", sid, f"emotion changes {prev['emotion']} -> {emo} inside a beat without a sound event",
                "REVIEW")
        # UR-11 durations
        lo, hi = DURATIONS[s["type"]]
        last = i == len(shots) - 1
        if d < lo - 1e-6 or (d > hi + 1e-6 and not (last and s.get("tail"))):
            add("UR-11", sid, f"{s['type']} shot of {d:.2f} s (allowed {lo}-{hi})")
        # UR-12 cuts in pauses
        if i > 0 and words and not cut_ok(s["start"], words):
            add("UR-12", sid, f"cut at {s['start']:.3f} s is not inside a punctuated pause")
        # UR-13 motion
        m = s.get("motion") or {}
        kind, z0, z1 = m.get("kind", "static"), float(m.get("z0", 1.0)), float(m.get("z1", m.get("z0", 1.0)))
        dx = abs(float(m.get("dx", 0.0)))
        if max(z0, z1) > MAX_ZOOM + 1e-9 or min(z0, z1) < 1.0 - 1e-9:
            add("UR-13", sid, f"zoom {z0:.2f}->{z1:.2f} outside 1.00-{MAX_ZOOM}")
        if float(m.get("shake", 0)) > 0:
            add("UR-13", sid, "camera shake")
        if s["type"] == "A":
            if kind != "pan" or dx <= 0:
                add("UR-13", sid, f"A shot moves by {kind!r}; needs a slow horizontal pan")
            elif dx > A_PAN_PER_5S * max(d, 1e-6) / 5.0 + 1e-9:
                add("UR-13", sid, f"pan {dx:.3f} of the width in {d:.1f} s is too fast")
            if not (A_ZOOM[0] - 1e-9 <= z0 <= A_ZOOM[1] + 1e-9 and abs(z1 - z0) < 1e-6):
                add("UR-13", sid, f"A shot zoom {z0:.2f}->{z1:.2f}; hold one zoom in {A_ZOOM}")
        elif s["type"] == "B":
            if kind != "push" or not z1 > z0 or z1 > B_PUSH_MAX + 1e-9:
                add("UR-13", sid, f"B shot {kind} {z0:.2f}->{z1:.2f}; needs a slow push-in to <= {B_PUSH_MAX}")
        else:
            if kind not in ("static", "pull") or z1 > z0 + 1e-9 or z0 > C_PULL_MAX + 1e-9 or dx > 0:
                add("UR-13", sid, f"C shot {kind} {z0:.2f}->{z1:.2f}; needs static or a pull-out from <= {C_PULL_MAX}")
        # UR-14 transitions
        if i > 0:
            tr = s.get("transition", "cut")
            if tr == "dissolve":
                dissolves += 1
                if not (s.get("time_jump") or s.get("place_change")):
                    add("UR-14", sid, "dissolve without a time jump or place change")
                if abs(float(s.get("transition_seconds", DISSOLVE_SECONDS)) - DISSOLVE_SECONDS) > 1e-6:
                    add("UR-14", sid, f"dissolve of {s.get('transition_seconds')} s; must be {DISSOLVE_SECONDS}")
            elif tr != "cut":
                add("UR-14", sid, f"transition {tr!r}; only cut or dissolve")
        # UR-15 sound at cuts
        snd = s.get("sound")
        if snd and sound_ids is not None and snd not in sound_ids:
            add("UR-15", sid, f"sound {snd!r} is not in the sound library")
        prev = s
    if len(shots) > 1 and dissolves / (len(shots) - 1) > DISSOLVE_SHARE + 1e-9:
        add("UR-14", "-", f"{dissolves} of {len(shots) - 1} transitions are dissolves (max {DISSOLVE_SHARE:.0%})")
    return found


def summary(findings: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        if f["severity"] == "FAIL":
            out[f["rule"]] = out.get(f["rule"], 0) + 1
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Check a shot list against the Universal Rule Base")
    p.add_argument("shots")
    p.add_argument("words")
    p.add_argument("look")
    a = p.parse_args(argv)
    shots = json.loads(Path(a.shots).read_text(encoding="utf-8"))
    shots = shots["shots"] if isinstance(shots, dict) else shots
    words = json.loads(Path(a.words).read_text(encoding="utf-8"))
    words = words["words"] if isinstance(words, dict) else words
    look = json.loads(Path(a.look).read_text(encoding="utf-8"))
    found = check_shots(shots, words, look)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['shot']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(f"{fails} FAIL, {len(found) - fails} REVIEW")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
