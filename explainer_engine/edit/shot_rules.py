"""The Universal Rule Base checks (docs/UNIVERSAL_RULE_BASE.md, UR-01..UR-15) over a shot list. stdlib only.

A shot list is the edit: ``[{id, beat, phase, type A|B|C, emotion, sentences, start, end, motion, transition,
time_jump, place_change, palette, prompt, face, sound}]`` with times in seconds on the narration clock. ``words`` is
the narration's ``[{w, s, e}]`` (``audio/timings.align`` shifted to the programme clock). ``look`` is the episode's
look file (style suffix, cast names, palette per phase). Every finding names its rule; ``FAIL`` blocks, ``REVIEW``
goes to the creator. ``solve_cuts`` places cuts only inside narration pauses (UR-12).

The numbers are the creator's house set of the Universal Rule Base (BP-85, D-37) and the sourced motion rules (BP-20, BP-22,
BP-31); the hook's form is BP-03 (one of its four forms, never a greeting), not a question by 5 s. Each numeric check takes its
rule's severity from the registry (docs/SOURCED_RULES.md).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

STAKES_FILE = Path(__file__).with_name("stakes.json")
MOODS_FILE = Path(__file__).with_name("moods.json")
DURATIONS = {k: tuple(float(x) for x in SR.T("BP-85", f"{k.lower()}_shot_s")) for k in "ABC"}  # UR-11 (BP-85)
FIRST_WINDOW = float(SR.T("BP-85", "first_window_s"))  # UR-02
FIRST_SLACK = float(SR.T("BP-85", "first_slack_s"))  # a shot in the first window stays within its minimum + this
FIRST_MIN_SHOTS = int(SR.T("BP-85", "first_min_shots"))
HOOK_FORMS = set(SR.T("BP-03", "hook_forms"))  # UR-01 / BP-03: the first sentence takes one of these forms
FIRST_SOUND = float(SR.T("BP-85", "first_sound_s"))
MAX_ZOOM = SR.T("BP-20", "scale_max")  # UR-13 / BP-20
A_ZOOM = tuple(float(x) for x in SR.T("BP-85", "a_zoom"))
A_PAN_PER_5S = SR.T("BP-22", "pan_default_width_per_s") * 5  # share of the frame width (BP-22's house default)
B_PUSH_MAX = SR.T("BP-20", "push_default_max")
C_PULL_MAX = float(SR.T("BP-85", "c_pull_max"))
DISSOLVE_SECONDS = SR.T("BP-31", "dissolve_s")  # UR-14 / BP-31: the default dissolve, and the shortest
DISSOLVE_MAX = SR.T("BP-31", "dissolve_max_s")  # BP-31 (the creator, 2026-10-20 21:14): a dissolve lasts 1-2 s (RX-08)
DISSOLVE_SHARE = float(SR.T("BP-85", "dissolve_share_max"))  # the hard-cut convention BP-31 names, the creator's (BP-85)
EDGE = float(SR.T("BP-85", "cut_edge_s"))  # UR-12: a cut keeps this far from both words
CUT_MARKS = ",.:;?!—…"
BANNED = re.compile(r"\b(hyper-?realistic|photo-?realistic|realistic|lifelike|natural proportions|photo(graph|graphy)?|"
                    r"unreal( engine)?|octane|3d render|cinematic photography|documentary|film still)\b", re.I)
FACE_WORDS = re.compile(r"\b(face|faces|portrait|eyes|smil(e|es|ing)|grin(s|ning)?|looking at (the )?camera)\b", re.I)
FACE_NEGATIONS = re.compile(r"\b(no (visible )?faces?|faceless|faces? (hidden|not visible|turned away)|without faces?)\b",
                            re.I)
GREETINGS = re.compile(r"\b(welcome|hello|hi|hey|today'?s video|in this video|subscribe)\b", re.I)  # BP-03: never the hook


def load_stakes(path: Path = STAKES_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def has_word(text: str, words: list[str]) -> list[str]:
    """The listed words/phrases that occur in ``text`` as whole words (case-insensitive)."""
    low = text.lower()
    return [w for w in words if re.search(rf"(?<![a-z]){re.escape(w.lower())}(?![a-z])", low)]


def load_moods(path: Path = MOODS_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["moods"]


def mood_clause(emotion: str, moods: dict | None = None) -> str:
    return (moods or load_moods())[emotion]["clause"]


def grade_for(emotion: str, moods: dict | None = None) -> dict:
    return dict((moods or load_moods())[emotion]["grade"])


def compose_prompt(subject: str, emotion: str, look: dict, moods: dict | None = None) -> str:
    """subject (with its composition) + the mood clause + the episode's style suffix (UR-07, UR-09)."""
    return f"{subject.rstrip(' ,.')}, {mood_clause(emotion, moods)}{look.get('universe_thread', '')}{look['style_suffix']}"


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


def anchor_spacing(rows: list[dict], slack: float = 0.5) -> list[dict]:
    """UR-28: the plan fits the read. ``rows`` are ``{id, type, target}`` in order (target = the second the picture's phrase ends).
    Each shot needs at least its type's minimum (UR-11), so a target closer than that to the previous one cannot be met: the
    picture will land late and every picture after it drifts. Returns one finding per offender plus the drift they cause."""
    found, prev, slip = [], 0.0, 0.0
    for r in rows:
        lo = DURATIONS[r["type"]][0]
        gap = r["target"] - prev
        if gap + slack < lo:
            slip += lo - gap
            found.append({"rule": "UR-28", "shot": r["id"], "severity": "REVIEW",
                          "detail": f"{r['type']} shot needs {lo:.1f} s but its phrase ends {gap:.1f} s after the previous one "
                                    f"(cumulative drift {slip:.1f} s): drop or merge a picture, or plan the shots from the real read"})
        prev = max(prev, r["target"])
    return found


def apply_cuts(shots: list[dict], cuts: list[float], end: float) -> list[dict]:
    bounds = [0.0] + list(cuts) + [end]
    return [dict(s, start=round(bounds[i], 3), end=round(bounds[i + 1], 3)) for i, s in enumerate(shots)]


def hook_form(sentence: str) -> str | None:
    """BP-03's form of a first sentence (the narration lint's own classifier, imported late: it imports this module)."""
    from explainer_engine.scripting import narration_lint
    return narration_lint.hook_form(sentence)


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

    house = SR.rule("BP-85").get("severity", "REVIEW")  # the numeric UR checks: the creator's house set
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
        lead = " ".join(w["w"] for w in _first_sentence(words))
        bp03 = SR.rule("BP-03").get("severity", "REVIEW")
        if GREETINGS.search(lead):
            add("UR-01", first["id"], "the first sentence greets instead of hooking (BP-03)", bp03)
        elif hook_form(lead) not in HOOK_FORMS:
            add("UR-01", first["id"], "the first sentence is none of BP-03's hook forms (a question, a short cold-open line, a "
                                      "claim with a number, a preview of what the viewer will see)", bp03)
        sound = first.get("sound_at")
        if words[0]["s"] > FIRST_SOUND and (sound is None or sound > FIRST_SOUND):
            add("UR-01", first["id"], f"no sound event in the first {FIRST_SOUND:.0f} s", house)

    # UR-02 first 30 s
    early = [s for s in shots if s["start"] < FIRST_WINDOW]
    if shots[-1]["end"] >= FIRST_WINDOW and len(early) < FIRST_MIN_SHOTS:
        add("UR-02", "-", f"{len(early)} shots start in the first {FIRST_WINDOW:.0f} s; needs >= {FIRST_MIN_SHOTS}", house)
    for s in early:
        d = s["end"] - s["start"]
        cap = DURATIONS.get(s["type"], (0.0, 0.0))[0] + FIRST_SLACK
        if s["type"] in DURATIONS and d > cap + 1e-6:
            add("UR-02", s["id"], f"{s['type']} shot of {d:.2f} s in the first {FIRST_WINDOW:.0f} s (max {cap:.1f})", house)

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
            add("UR-11", sid, f"{s['type']} shot of {d:.2f} s (allowed {lo}-{hi})", house)
        # UR-12 cuts in pauses
        if i > 0 and words and not cut_ok(s["start"], words):
            add("UR-12", sid, f"cut at {s['start']:.3f} s is not inside a punctuated pause", house)
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
                add("UR-13", sid, f"A shot zoom {z0:.2f}->{z1:.2f}; hold one zoom in {A_ZOOM}", house)
        elif s["type"] == "B":
            if kind != "push" or not z1 > z0 or z1 > B_PUSH_MAX + 1e-9:
                add("UR-13", sid, f"B shot {kind} {z0:.2f}->{z1:.2f}; needs a slow push-in to <= {B_PUSH_MAX}")
        else:
            if kind not in ("static", "pull") or z1 > z0 + 1e-9 or z0 > C_PULL_MAX + 1e-9 or dx > 0:
                add("UR-13", sid, f"C shot {kind} {z0:.2f}->{z1:.2f}; needs static or a pull-out from <= {C_PULL_MAX}", house)
        # UR-14 transitions
        if i > 0:
            tr = s.get("transition", "cut")
            if tr == "dissolve":
                dissolves += 1
                if not (s.get("time_jump") or s.get("place_change")):
                    add("UR-14", sid, "dissolve without a time jump or place change")
                if not DISSOLVE_SECONDS - 1e-6 <= float(s.get("transition_seconds", DISSOLVE_SECONDS)) <= DISSOLVE_MAX + 1e-6:
                    add("UR-14", sid, f"dissolve of {s.get('transition_seconds')} s; must be {DISSOLVE_SECONDS}-{DISSOLVE_MAX} (BP-31)")
            elif tr != "cut":
                add("UR-14", sid, f"transition {tr!r}; only cut or dissolve")
        # UR-15 sound at cuts
        snd = s.get("sound")
        if snd and sound_ids is not None and snd not in sound_ids:
            add("UR-15", sid, f"sound {snd!r} is not in the sound library")
        prev = s
    if len(shots) > 1 and dissolves / (len(shots) - 1) > DISSOLVE_SHARE + 1e-9:
        add("UR-14", "-", f"{dissolves} of {len(shots) - 1} transitions are dissolves (max {DISSOLVE_SHARE:.0%})", house)
    if int(look.get("rule_base", 1)) >= 2:
        found += check_stakes(shots, look)
    return found


FACELESS_SHARE = float(SR.T("BP-85", "faceless_share_max"))  # UR-17: at most this share of the B shots faceless, with a reason
MIN_STAKES_WORDS = int(SR.T("BP-85", "stakes_words_min"))


def check_stakes(shots: list[dict], look: dict, stakes: dict | None = None) -> list[dict]:
    """UR-16..UR-20 (D-40): no passive scenery, named heroes in every B shot, friction, archetypes, empty plates.
    Enabled by ``look["rule_base"] >= 2``; ``look["pose_bank"]`` lists the sprite poses that exist per hero."""
    stakes = stakes or load_stakes()
    found: list[dict] = []

    def add(rule: str, shot: str, detail: str, severity: str = "FAIL") -> None:
        found.append({"rule": rule, "shot": shot, "severity": severity, "detail": detail})

    cues = [w for group in stakes["cues"].values() for w in group]
    bank = look.get("pose_bank", {})
    archetypes = look.get("archetypes", {})
    caricatures = look.get("caricatures", [])
    b_shots = [s for s in shots if s.get("type") == "B"]
    faceless = [s for s in b_shots if s.get("face") == "faceless"]
    if b_shots and len(faceless) / len(b_shots) > FACELESS_SHARE + 1e-9:
        add("UR-17", "-", f"{len(faceless)} of {len(b_shots)} B shots are faceless (max {FACELESS_SHARE:.0%}): the heroes "
                          "must be seen, not hidden behind anonymous backs", SR.rule("BP-85").get("severity", "REVIEW"))
    for s in shots:
        sid = s["id"]
        # UR-16 stakes in the plan and in the prompt
        text = str(s.get("stakes", "")).strip()
        if len(text.split()) < MIN_STAKES_WORDS:
            add("UR-16", sid, f"no `stakes` line (>= {MIN_STAKES_WORDS} words): what is at risk in this frame?",
                SR.rule("BP-85").get("severity", "REVIEW"))
        prompt = s.get("prompt")
        if prompt:
            passive = has_word(prompt, stakes["passive"])
            if passive:
                add("UR-16", sid, f"passive scenery words in the pod prompt: {passive}")
            if not has_word(prompt, cues):
                add("UR-16", sid, "the pod prompt has no stakes cue (weather, fire, danger, hunger, conflict, strain, "
                                  "darkness, crowd, scale): it would paint a neutral picture")
            # UR-22 primary rule: every prompt carries the universe thread (the same drawing rules, any era or place)
            thread = str(look.get("universe_thread", "")).strip(" ,.").lower()
            if not thread:
                add("UR-22", sid, "the look has no `universe_thread`: nothing ties this picture to one drawn universe")
            elif thread not in prompt.lower():
                add("UR-22", sid, "the pod prompt lacks the universe thread: the picture could be drawn in another style")
            # UR-22 one world: any person or body part painted by the pod uses the cast's design language
            fig = str(look.get("figure_style", "")).strip().lower()
            bare = prompt.replace(str(look.get("style_suffix", "")), "").replace(str(look.get("universe_thread", "")), "")
            if not s.get("plate") and has_word(bare, stakes["people_words"] + stakes["body_words"]):
                if not fig:
                    add("UR-22", sid, "the look has no `figure_style`: people and hands cannot match our cast sprites")
                elif fig.strip(" ,.") not in prompt.lower():
                    add("UR-22", sid, "people or hands in the pod prompt without the look's `figure_style`: they would be "
                                      "painted in a different world than our sprites")
            if s.get("plate"):  # UR-20: a plate never names people (the model paints them, whatever "empty" says)
                people = has_word(prompt, stakes["people_words"])
                if people:
                    add("UR-20", sid, f"plate prompt names people ({people}): describe empty ground, never 'empty of people'")
        # UR-17 / UR-18 heroes
        if s.get("type") == "B":
            heroes = s.get("heroes") or []
            if s.get("face") == "faceless":
                if not str(s.get("faceless_reason", "")).strip():
                    add("UR-17", sid, "faceless B shot without a `faceless_reason`")
            elif not 1 <= len(heroes) <= 2:
                add("UR-17", sid, "a B shot shows 1-2 named heroes (`heroes`: [{name, pose}])")
            for h in heroes:
                name, pose = h.get("name", ""), h.get("pose", "")
                if name not in caricatures:
                    add("UR-17", sid, f"hero {name!r} has no caricature sprite")
                if pose not in stakes["poses"]:
                    add("UR-17", sid, f"pose {pose!r} is not an emotional pose ({', '.join(stakes['poses'])}); no idle standing")
                elif bank and pose not in bank.get(name, []):
                    add("UR-17", sid, f"pose {pose!r} of {name} is not in the sprite bank yet: generate it (reusable asset)",
                        "REVIEW")
                if name and name not in archetypes:
                    add("UR-19", sid, f"hero {name!r} has no archetype line in the look", "REVIEW")
    for name, phase in (look.get("phases") or {}).items():  # time travel never breaks the style
        changed = [k for k in ("universe_thread", "style_suffix", "figure_style", "style") if k in (phase or {})]
        if changed:
            add("UR-22", "-", f"phase {name!r} overrides {changed}: the era changes props and clothes, never the style")
    if not (look.get("style_bridge") or {}).get("approved"):
        add("UR-22", "-", "the style-bridge sheet (sprite + pod-painted person and hand in one frame) is not approved yet", "REVIEW")
    # UR-18 friction: a beat with several B shots has at least one with friction or two heroes
    beats: dict[str, list[dict]] = {}
    for s in b_shots:
        beats.setdefault(s.get("beat", ""), []).append(s)
    for beat, items in beats.items():
        if len(items) >= 2 and not any(s.get("friction") or len(s.get("heroes") or []) == 2 for s in items):
            add("UR-18", items[0]["id"], f"beat {beat!r} has {len(items)} B shots and no friction (an argument, a failure, "
                                          "two heroes disagreeing)", "REVIEW")
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
