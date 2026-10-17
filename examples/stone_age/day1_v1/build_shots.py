"""Build the Day 1 shot list (shots.json, timing.md) from the measured narration (words.json) and the look.

Each shot ends at the pause after a phrase of the narration; the cut sits in that pause (UR-12), nudged inside it when
the midpoint would break the shot's duration range (UR-11). Pod prompts are subject + mood clause + style suffix
(UR-07, UR-09). Run from the repository root:  python examples/stone_age/day1_v1/build_shots.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.edit import shot_rules as R  # noqa: E402

HERE = Path(__file__).resolve().parent
LOOK = json.loads((HERE.parent / "look.json").read_text(encoding="utf-8"))
WORDS_DOC = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
WORDS = WORDS_DOC["words"]
END = WORDS_DOC["duration"]
CLOSE = ", no faces, no background detail"
PLATE = ", empty of people, open space in the centre foreground for one standing figure"

# (beat, type, emotion, ends after phrase, picture, source, face, subject or reuse note, palette, sound)
# source: new = a new pod picture from `subject`; reuse = a picture of pictures_v0 or an earlier shot.
# face: caricature:<name>[+<name>] = our sprite over the plate; faceless = drawn from behind / hands; none = A or C.
SHOTS = [
    ("hook", "C", "tension", "Age?", "d1_c_mud_hand", "new", "none",
     "extreme close-up of a hand in a tweed coat sleeve pressing into cold wet mud beside a dark flint nodule" + CLOSE,
     ["umber", "charcoal", "ochre"], "seam_shimmer__v1"),
    ("hook", "B", "fear", "coming.", "d1_b_ridge_dusk", "new", "faceless",
     "medium shot of a lone man in a nineteenth-century greatcoat seen from behind on a grassy ridge, the sun sinking "
     "behind distant hills, his long shadow on the grass", ["night blue", "dawn rose", "charcoal"], "swish__v1"),
    ("rules", "C", "discovery", "scientists.", "d1_c_boots", "new", "none",
     "extreme close-up of many pairs of old leather boots and buckled shoes from different centuries standing in wet "
     "meadow grass" + CLOSE, ["umber", "ochre", "river teal"], "footstep_grass__v1"),
    ("rules", "B", "joy", "ago.", "d1_plate_riverbank", "new", "caricature:darwin",
     "medium shot of a river bank with tall wild grasses and grain heads, a wide shallow river and limestone hills "
     "behind" + PLATE, ["ochre", "river teal", "dawn rose"], "pop_in__v1"),
    ("rules", "C", "discovery", "work,", "d1_c_ink_hand", "new", "none",
     "extreme close-up of an ink-stained hand resting on a mossy stone, fingertips smudged with old ink" + CLOSE,
     ["umber", "charcoal", "ochre"], "page_flip__v1"),
    ("rules", "C", "humour", "pockets.", "d1_c_pocket", "new", "none",
     "extreme close-up of the contents of a coat pocket spilled on grass: round spectacles, a pencil stub, a folded "
     "handkerchief and two old coins" + CLOSE, ["ochre", "umber", "river teal"], "cloth_rustle__v1"),
    ("rules", "B", "humour", "magic.", "s02_plate_clearing", "reuse", "caricature:curie+tesla", None,
     ["ochre", "dawn rose"], "pop_in__v1"),
    ("rules", "C", "discovery", "real.", "d1_c_flint_grain", "new", "none",
     "extreme close-up of a flint nodule, a few ears of wild einkorn wheat and a smooth river pebble lying on dark "
     "earth" + CLOSE, ["charcoal", "ochre", "umber"], "glow_ping__v1"),
    ("rules", "A", "calm", "invention.", "s01_wide_valley", "reuse", "none", None,
     ["ochre", "river teal", "dawn rose"], "swish__v2"),
    ("meadow", "A", "humour", "first.", "d1_a_meadow_crowd", "new", "none",
     "epic wide establishing shot of a sunny highland meadow in a river valley, a hundred tiny distant figures "
     "standing in scattered arguing clusters, limestone cliffs and a huge sky, late morning",
     ["ochre", "river teal", "dawn rose"], None),
    ("meadow", "B", "humour", "Nansen,", "d1_plate_meadow", "new", "caricature:nansen",
     "medium shot of a patch of trampled meadow grass with a few boulders, the meadow and hills behind" + PLATE,
     ["ochre", "umber", "river teal"], "pop_in__v1"),
    ("meadow", "B", "tension", "question.", "d1_b_raised_hand", "new", "faceless",
     "medium shot of a weathered man in a heavy wool sweater seen from behind, raising one hand to quiet a crowd of "
     "people in old coats", ["umber", "ochre", "charcoal"], "throat_clear__v1"),
    ("meadow", "C", "tension", "matches?", "d1_c_empty_palms", "new", "none",
     "extreme close-up of two open empty palms held up, cold reddened fingers, nothing in them" + CLOSE,
     ["umber", "charcoal", "night blue"], None),
    ("meadow", "C", "humour", "unsure.", "d1_c_two_hands", "new", "none",
     "extreme close-up of two hands rising only halfway above a row of shoulders, fingers hesitant and half curled, "
     "against a bright sky" + CLOSE, ["ochre", "river teal", "umber"], "hmm_thinking__v1"),
    ("meadow", "B", "joy", "rule.", "d1_plate_table_rock", "new", "caricature:franklin",
     "medium shot of a flat rock in the meadow like a table, a few walking sticks leaning on it" + PLATE,
     ["ochre", "dawn rose", "umber"], "pop_in__v1"),
    ("meadow", "A", "calm", "safety.", "d1_a_circle", "new", "none",
     "epic wide establishing shot of a hundred tiny distant figures sitting in a wide circle on a hillside around a "
     "flat rock, a long valley and a river below, afternoon light", ["ochre", "river teal", "umber"], "swish__v1"),
    ("meadow", "B", "humour", "simple:", "d1_plate_meadow", "reuse", "caricature:newton", None,
     ["ochre", "umber", "river teal"], "pleased_mmhm__v1"),
    ("meadow", "C", "tension", "food.", "d1_c_three_marks", "new", "none",
     "extreme close-up of a hand scratching three short marks into bare earth with a pointed stick" + CLOSE,
     ["umber", "ochre", "charcoal"], "pencil_scribble__v1"),
    ("water", "B", "discovery", "ground.", "d1_b_spring", "new", "faceless",
     "medium shot of a bearded man in a linen shirt seen from behind, kneeling between mossy rocks where clear water "
     "bubbles out of the ground", ["river teal", "ochre", "umber"], None),
    ("water", "C", "tension", "months.", "d1_c_arrow_mud", "new", "none",
     "extreme close-up of a sharpened stick drawing an arrow in wet mud pointing downhill, away from a small pool"
     + CLOSE, ["umber", "charcoal", "river teal"], "pencil_scribble__v2"),
    ("water", "C", "calm", "spring.", "d1_c_spring_water", "new", "none",
     "extreme close-up of clear spring water trickling over smooth stones and green moss" + CLOSE,
     ["river teal", "ochre"], "swish__v2"),
    ("dusk", "A", "fear", "freezing,", "d1_a_dusk_wind", "new", "none",
     "epic wide establishing shot of the river valley at dusk, wind bending the tall grass in long waves, storm grey "
     "clouds rolling over the hills, one tiny cluster of distant figures", ["night blue", "charcoal", "dawn rose"], None),
    ("dusk", "C", "fear", "together.", "d1_c_wet_sleeve", "new", "none",
     "extreme close-up of a damp wool coat sleeve beaded with water and a clenched shivering hand" + CLOSE,
     ["night blue", "charcoal", "umber"], "shiver_brr__v1"),
    ("dusk", "B", "tension", "against it.", "d1_b_windbreak", "new", "faceless",
     "medium shot of two people seen from behind stacking long branches into a slanting windbreak against a boulder, "
     "armfuls of dry grass at their feet", ["umber", "ochre", "charcoal"], "effort_hup__v1"),
    ("dusk", "C", "calm", "is.", "d1_c_dry_grass", "new", "none",
     "extreme close-up of two hands pressing a thick loose bundle of dry grass and dead leaves" + CLOSE,
     ["ochre", "umber"], "cloth_rustle__v2"),
    ("fire", "C", "tension", "drill.", "s03_close_drill", "reuse", "none", None,
     ["umber", "ochre", "charcoal"], None),
    ("fire", "B", "tension", "smoke.", "s02_plate_clearing", "reuse", "caricature:nansen", None,
     ["umber", "ochre", "charcoal"], "groan_ugh__v1"),
    ("fire", "C", "calm", "waits.", "d1_c_tinder_nest", "new", "none",
     "extreme close-up of two cupped hands holding a nest of dry shredded bark and grass, sheltering it from the wind"
     + CLOSE, ["ochre", "umber"], "cloth_rustle__v3"),
    ("fire", "C", "discovery", "glasses.", "d1_c_spectacles", "new", "none",
     "extreme close-up of a hand lifting a pair of small round reading spectacles, sunlight glinting on the lens"
     + CLOSE, ["fire amber", "ochre"], "monocle_pop__v1"),
    ("fire", "B", "discovery", "grass.", "s04_plate_cave", "reuse", "caricature:einstein", None,
     ["fire amber", "umber"], "pop_in__v1"),
    ("fire", "C", "tension", "breath.", "s07_close_spark", "reuse", "none", None,
     ["fire amber", "charcoal"], "gasp_inhale__v1"),
    ("fire", "C", "joy", "making it.", "s09_close_flame", "reuse", "none", None,
     ["fire amber", "charcoal"], "reveal_sting__v1"),
    ("fire", "B", "joy", "company,", "d1_plate_overhang_fire", "new", "caricature:franklin",
     "medium shot of a rock overhang camp lit by a small new fire, firewood stacked by the wall" + PLATE,
     ["fire amber", "umber", "charcoal"], "laugh_warm__v1"),
    ("night", "A", "calm", "nuts,", "s10_wide_night", "reuse", "none", None,
     ["night blue", "fire amber", "charcoal"], "swish__v1"),
    ("night", "C", "calm", "grain.", "d1_c_food_hands", "new", "none",
     "extreme close-up of two hands holding a few hazelnuts, two small speckled eggs and some ears of wild grain"
     + CLOSE, ["ochre", "umber", "fire amber"], None),
    ("night", "B", "tension", "know.", "d1_plate_unknown_plants", "new", "caricature:darwin",
     "medium shot of a firelit patch of ground with unfamiliar wild plants and berries laid out on a flat stone"
     + PLATE, ["fire amber", "umber", "charcoal"], "hmm_thinking__v1"),
    ("end", "A", "calm", "anything.", "d1_a_valley_stars", "new", "none",
     "epic wide establishing shot of the whole river valley at night under a sky full of stars, one tiny fire glowing "
     "beside a slanting windbreak far below", ["night blue", "charcoal", "fire amber"], None),
    ("end", "B", "calm", "do. <", "d1_b_tired_pair", "new", "faceless",
     "medium shot of two tired people in old coats seen from behind, sitting slumped against a windbreak of branches, "
     "looking into a small fire", ["fire amber", "charcoal", "night blue"], "sigh_tired__v1"),
    ("end", "C", "discovery", "pot.", "d1_c_clay", "new", "none",
     "extreme close-up of two hands holding a lump of wet grey river clay with thumbprints pressed into it" + CLOSE,
     ["umber", "river teal", "charcoal"], "glow_ping__v1"),
]


def _norm(w: str) -> str:
    return w.lower().strip("\"'”’")


def phrase_end(phrase: str, after: float) -> int:
    """Index of the last word of the first occurrence of ``phrase`` that starts after ``after``."""
    toks = [_norm(t) for t in phrase.split() if t != "<"]
    for i in range(len(WORDS) - len(toks) + 1):
        if WORDS[i]["s"] + 1e-6 < after:
            continue
        if [_norm(w["w"]) for w in WORDS[i:i + len(toks)]] == toks:
            return i + len(toks) - 1
    raise SystemExit(f"phrase {phrase!r} not found after {after:.2f} s")


def cut_after(i: int, start: float, kind: str, early: bool = False) -> float:
    """The cut in the pause after word ``i``: its middle (or its start, ``early``, to leave the next shot room)."""
    if i == len(WORDS) - 1:
        return END
    a, b = WORDS[i]["e"], WORDS[i + 1]["s"]
    lo, hi = a + R.EDGE, b - R.EDGE
    t = lo if early else (a + b) / 2
    dlo, dhi = R.DURATIONS[kind]
    if start < R.FIRST_WINDOW:
        dhi = dlo + R.FIRST_SLACK
    t = min(max(t, start + dlo), start + dhi)  # nudge inside the pause toward the allowed length
    return round(min(max(t, lo), hi), 3)


def motion(kind: str, d: float, k: int) -> dict:
    if kind == "A":
        return {"kind": "pan", "z0": 1.06, "z1": 1.06, "dx": round(0.05 * d / 5.0, 4) * (1 if k % 2 else -1)}
    if kind == "B":
        return {"kind": "push", "z0": 1.0, "z1": 1.06}
    return {"kind": "static", "z0": 1.0, "z1": 1.0} if k % 2 else {"kind": "pull", "z0": 1.06, "z1": 1.0}


def sentences() -> list[tuple[float, float, str]]:
    out, cur = [], []
    for w in WORDS:
        cur.append(w)
        if re.search(r"[.?!][\"'”’)]*$", w["w"]):
            out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
    if cur:
        out.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
    return out


def build() -> list[dict]:
    sents = sentences()
    shots, start = [], 0.0
    for k, (beat, kind, emo, phrase, pic, source, face, subject, palette, sound) in enumerate(SHOTS):
        end = cut_after(phrase_end(phrase, start), start, kind, early=phrase.endswith(" <"))
        shot = {"id": f"d1-{k + 1:02d}", "beat": beat, "phase": "day1", "type": kind, "emotion": emo,
                "start": round(start, 3), "end": end,
                "sentences": [j for j, (a, b, _) in enumerate(sents) if a < end and b > start],
                "motion": motion(kind, end - start, k), "transition": "cut", "picture": pic, "source": source,
                "face": face if kind == "B" else "none", "palette": palette,
                "grade": R.grade_for(emo)}
        if subject:
            shot["prompt"] = R.compose_prompt(subject, emo, LOOK)
        if sound:
            shot["sound"] = sound
            if k == 0:
                shot["sound_at"] = 0.0
        if k == len(SHOTS) - 1:
            shot["tail"] = True
        shots.append(shot)
        start = end
    return shots


def timing_md(shots: list[dict]) -> str:
    sents = sentences()
    lines = ["# Day 1: timing (measured Kokoro narration, cuts in pauses)", "",
             f"Narration: {WORDS_DOC['source']}. Duration {END:.2f} s, {len(WORDS)} words. Built by `build_shots.py`; "
             "checked by `explainer_engine.edit.shot_rules` (UR-01..UR-15).", "",
             "| # | in | out | len | type | emotion | picture | source | face | narration over the shot |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in shots:
        text = " ".join(w["w"] for w in WORDS if s["start"] <= w["s"] < s["end"])
        lines.append(f"| {s['id']} | {s['start']:.2f} | {s['end']:.2f} | {s['end'] - s['start']:.2f} | {s['type']} | "
                     f"{s['emotion']} | {s['picture']} | {s['source']} | {s['face']} | {text} |")
    lines += ["", "## Sentences", "", "| # | in | out | sentence |", "|---|---|---|---|"]
    lines += [f"| {j} | {a:.2f} | {b:.2f} | {t} |" for j, (a, b, t) in enumerate(sents)]
    return "\n".join(lines) + "\n"


def sound_ids() -> set[str]:
    m = json.loads((ROOT / "assets/audio/library/manifest.json").read_text(encoding="utf-8"))
    return {x["id"] for x in m["items"]}


if __name__ == "__main__":
    shots = build()
    (HERE / "shots.json").write_text(json.dumps({"version": 1, "segment": "day1", "duration": END, "shots": shots},
                                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "timing.md").write_text(timing_md(shots), encoding="utf-8")
    found = R.check_shots(shots, WORDS, LOOK, sound_ids=sound_ids())
    report = ["# Day 1: Universal Rule Base check", ""]
    report += [f"- {f['severity']} {f['rule']} {f['shot']}: {f['detail']}" for f in found] or ["- no findings"]
    fails = sum(f["severity"] == "FAIL" for f in found)
    report += ["", f"{len(shots)} shots, {fails} FAIL, {len(found) - fails} REVIEW"]
    (HERE / "check_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    raise SystemExit(1 if fails else 0)
