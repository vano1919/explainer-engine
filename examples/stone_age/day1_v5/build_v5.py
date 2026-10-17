"""Day 1 v5 (D-41): the v4 beats re-planned for one engine: every picture is a full Gemini frame in look v2, painted with its
heroes and its world in one go (no sprite over a plate). Cuts come from the real read (Scribe words, padded pauses).
Run from the repository root:  python examples/stone_age/day1_v5/build_v5.py
Outputs: shots.json (the edit), prompts.json (pictures to paint), report.md (rule findings)."""
from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.edit import prompt_v2  # noqa: E402
from explainer_engine.edit import shot_rules as R  # noqa: E402
from explainer_engine.world import resolver  # noqa: E402

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v4", HERE.parent / "day1_v4" / "build_shots.py")
V4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V4)
WORLD = resolver.resolve(json.loads((HERE / "world_spec.json").read_text()))
LOOK = json.loads((HERE.parent / "look.json").read_text())
WORDS_DOC = json.loads((HERE / "words.json").read_text())
WORDS, END = WORDS_DOC["words"], WORDS_DOC["duration"]
V4.WORDS, V4.END = WORDS, END  # the anchors and cuts use the real read
NOTES: list[str] = []
BEAT_NO = {"hook": 1, "rules": 2, "meadow": 3, "water": 4, "dusk": 5, "fire": 6, "night": 7, "end": 8}
VISITOR_COSTUME = "muddy frock coats, waistcoats, long skirts and spectacles of the 1700s to 1900s"
HERO = {
    "franklin": "Benjamin Franklin: balding crown with long grey hair, round spectacles, plump weathered face, brown frock coat",
    "newton": "Isaac Newton: long wavy shoulder-length wig, long pale stern face, dark coat with a white cravat",
    "nansen": "Fridtjof Nansen: tall rugged Norwegian explorer, strong jaw, fair moustache, weathered face, heavy wool jacket",
    "einstein": "young Albert Einstein of 1905: dark untidy hair, moustache, rumpled suit, round reading glasses",
    "darwin": "Charles Darwin: heavy brow, long white beard, dark frock coat",
    "wallace": "Alfred Russel Wallace: high forehead, full brown beard, field jacket",
    "snow": "John Snow: pale thoughtful clean-shaven physician, dark coat of the 1850s",
    "curie": "Marie Curie: dark hair in a bun, serious intense face, dark dress",
    "tesla": "Nikola Tesla: tall thin man, slicked-back dark hair, narrow moustache, dark suit",
}
POSE = {"dismay": "stricken, hands on head", "shock": "frozen in shock, mouth open", "think": "thoughtful, chin on hand",
        "amazed": "wide-eyed, amazed", "argue": "arguing, pointing a finger", "point": "pointing sharply",
        "smug": "smug, arms folded", "scheme": "scheming, rubbing chin", "struggle": "straining with effort",
        "triumph": "raising a fist, triumphant", "plead": "pleading, hands cupped", "recoil": "recoiling in alarm",
        "lecture": "lecturing with a raised finger", "exhausted": "slumped, exhausted"}
EXTRA = {  # subjects for the v4 rows that reused old pictures
    "s03_close_drill": "two raw hands working a wooden bow drill against a block of wood, a thin thread of smoke, ash on the wrists",
    "s07_close_spark": "cupped cold hands shielding one tiny glowing ember in dry grass, a held breath, sparks",
    "s09_close_flame": "cupped hands around a small new flame growing from tinder, the wind pulling at it",
    "s10_wide_night": "a hundred people sitting in the dark around one small campfire in a vast black valley, stars above",
}


BEAT_START = {"hook": None, "rules": "right.", "meadow": "day", "water": "so,", "dusk": "the sun drops,", "fire": "now.",
              "night": "almost", "end": "one spring,"}
IDEAL = {"A": 6.0, "B": 4.2, "C": 3.2}


def _beat_times() -> dict:
    """Start time of every beat: the first word (after the previous beat's start) matching its opening words."""
    out, after = {"hook": 0.0}, 0.0
    for beat, key in BEAT_START.items():
        if key is None:
            continue
        toks = key.split()
        for i, w in enumerate(WORDS):
            if w["s"] > after + 5 and [x.lower() for x in (w["w"],)] == [toks[0]] or (
                    w["s"] > after + 5 and w["w"].lower().strip(",.") == toks[0].strip(",.")):
                out[beat] = w["s"]
                after = w["s"]
                break
        else:
            raise SystemExit(f"beat {beat}: opening {key!r} not found")
    return out


def _first_stuck(types: list[str]) -> int | None:
    """Index of the first shot with no legal cut layout (None when the whole sequence fits). Same rules as solve_cuts."""
    cands = set()
    for a, b, _ in R.pauses_from_words(WORDS, R.EDGE):
        lo, hi = math.ceil((a + R.EDGE) * 1000 + 1e-6) / 1000, math.floor((b - R.EDGE) * 1000 - 1e-6) / 1000
        if hi >= lo:
            cands.update(round(min(max(lo + (hi - lo) * f, lo), hi), 3) for f in (0.0, 0.25, 0.5, 0.75, 1.0))
    pts = [0.0] + sorted(c for c in cands if 0 < c < END) + [END]
    reach = {0.0}
    for k, kind in enumerate(types):
        lo, hi = R.DURATIONS[kind]
        new = set()
        for s in reach:
            h = lo + R.FIRST_SLACK if s < R.FIRST_WINDOW else hi
            new |= {p for p in pts if p > s and lo - 1e-9 <= p - s <= h + 1e-9 and ((p == END) == (k == len(types) - 1))}
        if not new:
            return k
        reach = new
    return None if END in reach else len(types) - 1


def _swap(a: int, b: int) -> None:
    """Exchange two neighbouring shots' content (type, picture, heroes...) but not their anchors or beats: the slot stays tied
    to the words it illustrates."""
    keep = ("anchor", "beat")
    A, B = V4.SHOTS[a], V4.SHOTS[b]
    for k in set(A) | set(B):
        if k in keep:
            continue
        A[k], B[k] = B.get(k), A.get(k)


def fix_order() -> list[str]:
    """When no layout fits, swap neighbouring shots inside a beat (same picture list, other order) until one does. Returns notes."""
    notes = []
    for _ in range(40):
        k = _first_stuck([r["type"] for r in V4.SHOTS])
        if k is None:
            return notes
        best = None
        for a in range(max(0, k - 3), min(len(V4.SHOTS) - 1, k + 2)):
            b = a + 1
            if V4.SHOTS[a]["beat"] != V4.SHOTS[b]["beat"] or V4.SHOTS[a]["type"] == V4.SHOTS[b]["type"]:
                continue
            _swap(a, b)
            k2 = _first_stuck([r["type"] for r in V4.SHOTS])
            _swap(a, b)
            if k2 is None or k2 > k:
                if best is None or (k2 is None) or (best[0] is not None and k2 > best[0]):
                    best = (k2, a, b)
        if best is None:
            raise SystemExit(f"no layout and no neighbour swap helps at shot {k + 1}: edit the text or add a clause pause (UR-12)")
        _, a, b = best
        notes.append(f"swapped shots {a + 1} and {b + 1} ({V4.SHOTS[a]['picture']} / {V4.SHOTS[b]['picture']}) so cuts fit pauses")
        _swap(a, b)
    raise SystemExit("order search did not converge")


def _tok(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def plan_anchors() -> None:
    """Every shot ends where its anchor phrase ends in the REAL read (punctuation-tolerant match), so each picture lands on the
    words it illustrates. Anchors are time-ordered; a miss is a hard error: fix the anchor, not the match."""
    flat = [(_tok(t), i) for i, w in enumerate(WORDS) for t in w["w"].split() if _tok(t)]
    prev = 0.0
    for r in V4.SHOTS:
        want = [_tok(t) for t in r["anchor"].lstrip("@").split() if _tok(t)] if not r["anchor"].startswith("@") else None
        if want is None:
            continue
        for j in range(len(flat) - len(want) + 1):
            if WORDS[flat[j][1]]["s"] + 1e-6 < prev:
                continue
            if [x for x, _ in flat[j:j + len(want)]] == want:
                idx = flat[j + len(want) - 1][1]
                prev = WORDS[idx]["e"]
                r["anchor"] = f"@{prev:.3f}"
                break
        else:
            raise SystemExit(f"anchor {r['anchor']!r} not found after {prev:.2f} s in the real read")


# D-41: a hero is drawn inside the frame from its hero card (HERO + POSE above), not cut from a sprite bank, so UR-06/UR-17's
# "sprite exists" checks are satisfied by the card; the card itself is checked by the visual judge (hero_match).
LOOK = dict(LOOK, caricatures=sorted(HERO), pose_bank={h: sorted(POSE) for h in HERO})


def sanitize(text: str, beat: int) -> str:
    """UR-27: a not-yet word is never written into a prompt, not even as 'no fire' (the model paints what it reads)."""
    for w in resolver.not_yet(WORLD, beat):
        text = re.sub(rf"\b{w}s?\b", "warmth", text, flags=re.I)
    return text


OVERRIDE = {"d1_a_valley_eyes": "a hundred exhausted scientists in muddy frock coats and long skirts asleep in rows behind a low wall of dry branches "
            "in an enormous dark river valley under a star-filled sky, and far away on the dark treeline a pack of wolves "
            "watching from the shadows"}


def clean(s: str) -> str:
    s = s.replace(V4.CLOSE, "").replace(V4.PLATE, "")
    s = re.sub(r"^(epic wide establishing shot of|medium shot of|extreme close-up of)\s+", "", s)
    s = s.replace("tiny ", "").replace("a hundred figures", "a hundred people").replace("storm clouds", "dark storm clouds")
    return s.strip(" ,.")


def subject_of(k: int, r: dict) -> tuple[str, bool, bool, str]:
    """(subject, people, plate, costume hint) for the shot."""
    heroes = r["heroes"]
    if r["picture"] in OVERRIDE:
        return OVERRIDE[r["picture"]], True, False, VISITOR_COSTUME
    if heroes:
        setting = clean(r["subject"]) if r["subject"] else "a cold stony hillside"
        who = "; ".join(f"{HERO[h['name']]}, {POSE[h['pose']]}" for h in heroes)
        return (f"{'two named heroes' if len(heroes) == 2 else 'one named hero'} in the foreground: {who}. {r['stakes']}. "
                f"Setting: {setting}", True, False, VISITOR_COSTUME)
    sub = clean(r["subject"] or EXTRA[r["picture"]])
    people = bool(R.has_word(sub, ["hand", "hands", "fist", "fingers", "palms", "arms", "people", "figures", "strangers",
                                   "tracks", "sleeve", "coat"])) or "hundred" in sub
    return sub, people, False, VISITOR_COSTUME if people else ""


_orig_phrase_end = V4.phrase_end


def _phrase_end(phrase: str, after: float) -> int:
    if phrase.startswith("@"):
        t = float(phrase[1:])
        idx = [i for i, w in enumerate(WORDS) if w["e"] <= t + 1e-3]
        return idx[-1] if idx else 0
    return _orig_phrase_end(phrase, after)


V4.phrase_end = _phrase_end


SKIP_COST = 12.0  # seconds squared: a dropped shot costs as much as ending about 3.5 s off its phrase
CRITICAL = {"d1_c_spectacles", "d1_c_lens_sun", "s07_close_spark", "s09_close_flame", "d1_plate_grass_smoke", "d1_a_arrival_wind",
            "d1_c_flint_cracked", "d1_plate_fire_pit", "s03_close_drill", "d1_a_hook_storm"}  # the story cannot lose these
FILLER = {"d1_c_fist_clench", "d1_c_empty_palms", "d1_c_boots_mud", "d1_c_wet_sleeve", "d1_c_dry_grass", "d1_c_food_hands",
          "d1_c_branch_armful", "d1_c_two_hands_half"}  # inserts that illustrate a mood, not a fact


def skip_cost(row: dict) -> float:
    return 120.0 if row["picture"] in CRITICAL else 5.0 if row["picture"] in FILLER else SKIP_COST


def solve_with_skips(rows: list[dict]) -> tuple[list[int], list[float]]:
    """Like ``shot_rules.solve_cuts`` (cuts only in punctuated pauses, UR-11 durations, UR-02 first 30 s) but a shot may be
    DROPPED when keeping every picture would push the rest of the story off the words it illustrates. Returns (kept row indices,
    cut times between the kept shots)."""
    cands = set()
    for a, b, _ in R.pauses_from_words(WORDS, R.EDGE):
        lo, hi = math.ceil((a + R.EDGE) * 1000 + 1e-6) / 1000, math.floor((b - R.EDGE) * 1000 - 1e-6) / 1000
        if hi >= lo:
            cands.update(round(min(max(lo + (hi - lo) * f, lo), hi), 3) for f in (0.0, 0.25, 0.5, 0.75, 1.0))
    pts = [0.0] + sorted(c for c in cands if 0 < c < END) + [END]
    tgt = [float(r["anchor"][1:]) if r["anchor"].startswith("@") else None for r in rows]
    n, m = len(rows), len(pts)
    INF = float("inf")
    best = [[(INF, None)] * m for _ in range(n + 1)]  # best[k][j]: rows[:k] decided, last kept shot ends at pts[j]
    best[0][0] = (0.0, None)
    for k in range(n):
        for i in range(m):
            cost, _ = best[k][i]
            if cost == INF:
                continue
            if k < n - 1 and cost + skip_cost(rows[k]) < best[k + 1][i][0]:  # drop row k
                best[k + 1][i] = (cost + skip_cost(rows[k]), ("skip", i))
            lo, hi = R.DURATIONS[rows[k]["type"]]
            if pts[i] < R.FIRST_WINDOW:
                hi = lo + R.FIRST_SLACK
            for j in range(i + 1, m):
                d = pts[j] - pts[i]
                if d > hi + 1e-9:
                    break
                if d < lo - 1e-9 or ((j == m - 1) != (k == n - 1)):
                    continue
                c = cost + ((pts[j] - tgt[k]) ** 2 if tgt[k] is not None else 0.0)
                if c < best[k + 1][j][0]:
                    best[k + 1][j] = (c, ("keep", i))
    if best[n][m - 1][0] == INF:
        raise SystemExit("no cut layout even with dropped shots: edit the text or add a clause pause (UR-12)")
    kept, cuts, j = [], [], m - 1
    for k in range(n, 0, -1):
        kind, i = best[k][j][1]
        if kind == "keep":
            kept.append(k - 1)
            cuts.append(pts[j])
        j = i
    kept.reverse()
    return kept, sorted(cuts)[:-1]


ALL_ROWS: list[dict] = []


def build() -> list[dict]:
    plan_anchors()
    ALL_ROWS[:] = [dict(r) for r in V4.SHOTS]
    kept, cuts = solve_with_skips(V4.SHOTS)
    dropped = [r["picture"] for k, r in enumerate(V4.SHOTS) if k not in kept]
    NOTES.extend(f"dropped shot {V4.SHOTS[k]['picture']} ({V4.SHOTS[k]['type']}): no legal cut layout kept it on its words"
                 for k in range(len(V4.SHOTS)) if k not in kept)
    V4.SHOTS[:] = [V4.SHOTS[k] for k in kept]
    shots = V4._build_with(cuts)
    out, prompts = [], []
    for k, (s, r) in enumerate(zip(shots, V4.SHOTS)):
        sub, people, plate, hint = subject_of(k, r)
        beat = BEAT_NO[r["beat"]]
        sub = sanitize(sub, beat)
        p = prompt_v2.compose(r["type"], sub, WORLD, beat, people=people, plate=plate, costume_hint=hint)
        s = {k2: v for k2, v in s.items() if k2 not in ("plate", "source", "prompt", "grade", "heroes")}
        names = [h["name"] for h in r["heroes"]]
        s["heroes"] = r["heroes"]
        s["picture"] = f"v5_{s['id']}"
        s["prompt"] = p
        s["people"] = people
        s["face"] = ("caricature:" + "+".join(names)) if names else ("none" if people else "none")
        out.append(s)
        prompts.append({"id": s["picture"], "shot": s["id"], "type": r["type"], "prompt": p, "people": people,
                        "heroes": names, "stakes": r["stakes"],
                        "findings": prompt_v2.lint(p, WORLD, people=people, visitors_named=sorted(HERO), beat=beat),
                        "beat": beat, "not_yet": resolver.not_yet(WORLD, beat)})
    return out, prompts


if __name__ == "__main__":
    shots, prompts = build()
    (HERE / "shots.json").write_text(json.dumps({"version": 3, "segment": "day1", "duration": END, "shots": shots},
                                                indent=1, ensure_ascii=False) + "\n")
    (HERE / "prompts.json").write_text(json.dumps(prompts, indent=1, ensure_ascii=False) + "\n")
    found = []
    for s in shots:  # the edit grammar (UR-01..UR-15) only: stakes/hero-sprite rules belong to the sprite pipeline (v4)
        pass
    edit = R.anchor_spacing([{"id": r["picture"], "type": r["type"], "target": float(r["anchor"][1:])} for r in ALL_ROWS]) + R.check_shots([{k: v for k, v in s.items() if k not in ("prompt",)} for s in shots], WORDS, LOOK,
                         sound_ids=V4.sound_ids())
    fails = [f for f in edit if f["severity"] == "FAIL"]
    lint = [(p["id"], f) for p in prompts for f in p["findings"]]
    lines = ["# Day 1 v5 report", "", f"{len(shots)} shots, edit grammar: {len(fails)} FAIL, {len(edit) - len(fails)} REVIEW; "
             f"prompt lint: {sum(f['severity'] == 'FAIL' for _, f in lint)} FAIL, "
             f"{sum(f['severity'] == 'REVIEW' for _, f in lint)} REVIEW", ""]
    lines += [f"- NOTE {n}" for n in NOTES]
    lines += [f"- {f['severity']} {f['rule']} {f['shot']}: {f['detail']}" for f in edit]
    lines += [f"- {f['severity']} {f['rule']} {pid}: {f['detail']}" for pid, f in lint]
    (HERE / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
