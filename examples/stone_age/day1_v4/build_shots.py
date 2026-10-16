"""Build the Day 1 shot plan under rule base 2 (UR-01..UR-20): stakes in every frame, named heroes in every B shot.

The pictures are decided by the narration beats (day1_v4/narration_tts.txt); the cuts are placed by the solver inside
punctuated pauses (UR-12) from the measured words.json. Until the full v4 read exists this uses the timings of the
v2 read (same story beats, different words), so the cut times are provisional and are recomputed with the real read.
Run from the repository root:  python examples/stone_age/day1_v4/build_shots.py
Outputs: shots.json, timing.md, check_report.md, pod_job.json (the pictures to paint), sprite_needs.md (poses to make).
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
WORDS, END = WORDS_DOC["words"], WORDS_DOC["duration"]
CLOSE = ", no faces, no background detail"
# a plate never names people (UR-20): the model paints them whatever "empty" says. Room for the sprites is described as ground.
PLATE = ", wide deserted open ground across the centre foreground, nothing standing on it"


def row(beat, kind, emo, anchor, pic, subject, stakes, palette, sound=None, heroes=None, plate=False, friction=False,
        reuse=False):
    return dict(beat=beat, type=kind, emotion=emo, anchor=anchor, picture=pic, subject=subject, stakes=stakes,
                palette=palette, sound=sound, heroes=heroes or [], plate=plate, friction=friction, reuse=reuse)


def H(name, pose):
    return {"name": name, "pose": pose}


SHOTS = [
    row("hook", "A", "tension", "tools.", "d1_a_hook_storm",
        "epic wide establishing shot of a vast windswept river valley at dusk under a bruised storm sky, long shadows "
        "over the bare grass, a tiny huddled cluster of a hundred distant strangers in old coats on the open ground, "
        "no shelter anywhere", "a hundred strangers stand exposed with no shelter as a storm and the night close in",
        ["night blue", "dawn rose", "charcoal"], "seam_shimmer__v1"),
    row("hook", "B", "fear", "coming.", "d1_plate_ridge_storm",
        "medium shot of a bare windswept ridge at dusk, a darkening storm sky, cold grass bending in the wind, long "
        "shadows" + PLATE, "night is coming and nobody has fire or shelter", ["night blue", "dawn rose", "charcoal"],
        "swish__v1", [H("franklin", "dismay")], plate=True),
    row("rules", "C", "tension", "rules.", "d1_c_boots_mud",
        "extreme close-up of many pairs of muddy buckled boots and polished city shoes of different centuries sinking "
        "into cold wet clay, frost on the grass blades" + CLOSE,
        "city shoes were never made for this ground and every foot is already soaked", ["umber", "ochre", "charcoal"],
        "footstep_grass__v1"),
    row("rules", "B", "tension", "Anatolia,", "d1_plate_river_overcast",
        "medium shot of a wide shallow river under an overcast sky, wind bending the wild grain, dark limestone cliffs "
        "and long shadows" + PLATE, "an unknown valley in an unknown age and no way home",
        ["river teal", "charcoal", "umber"], "pop_in__v1", [H("darwin", "shock")], plate=True),
    row("rules", "A", "fear", "work,", "d1_a_arrival_wind",
        "epic wide establishing shot of scattered tiny strangers in top hats and long coats stumbling out of a swirl of "
        "pale light on a windswept hillside, long shadows, an empty hostile horizon, storm clouds gathering",
        "they arrive confused, dressed for a different century, in the open", ["ochre", "charcoal", "dawn rose"],
        "swish__v2"),
    row("rules", "B", "humour", "pockets.", "d1_plate_stones_wind",
        "medium shot of a stony hillside in a cold wind, dust blowing, long shadows" + PLATE,
        "all they own is what happens to be in their pockets", ["ochre", "umber", "charcoal"], "cloth_rustle__v1",
        [H("newton", "dismay"), H("einstein", "think")], plate=True, friction=True),
    row("rules", "B", "tension", "magic.", "d1_plate_clearing_dusk",
        "medium shot of a stony clearing under a threatening grey sky, wind whipping the dust, long shadows" + PLATE,
        "they can talk to each other, and that is the only help they get", ["ochre", "dawn rose", "charcoal"],
        "pop_in__v1", [H("curie", "amazed"), H("tesla", "argue")], plate=True, friction=True),
    row("rules", "C", "tension", "physics...", "d1_c_flint_cracked",
        "extreme close-up of a cracked flint nodule with a razor edge beside a few ears of raw wild einkorn wheat and a "
        "pebble on cold dark earth" + CLOSE, "a sharp edge and raw grain are the whole toolbox",
        ["charcoal", "ochre", "umber"], "glow_ping__v1"),
    row("rules", "C", "humour", "real.", "d1_c_pocket_shaking",
        "extreme close-up of a trembling hand turning out a coat pocket onto cold grass: round spectacles, a pencil stub, "
        "a folded handkerchief and two old coins" + CLOSE, "four small things against a whole prehistoric world",
        ["ochre", "umber", "river teal"], "page_flip__v1"),
    row("rules", "A", "tension", "invention.", "d1_a_lost_valley",
        "epic wide establishing shot of a hundred tiny figures in old coats standing lost in an enormous empty river valley "
        "under a vast overcast sky, wind bending the wild grain, no shelter anywhere",
        "a hundred geniuses and not one roof", ["ochre", "river teal", "charcoal"]),
    row("meadow", "C", "tension", "morning.", "d1_c_watch_frost",
        "extreme close-up of cold trembling fingers over an old pocket watch whose hands are stopped, frost on the glass"
        + CLOSE, "time as they knew it has stopped, and the cold has not", ["ochre", "river teal", "charcoal"]),
    row("meadow", "A", "humour", "first.", "d1_a_arguing_clusters",
        "epic wide establishing shot of a windswept highland meadow where a hundred tiny figures stand in scattered "
        "arguing clusters, pointing in different directions, limestone cliffs and long shadows, a bruised sky",
        "a hundred leaders, no plan and the light is already moving", ["ochre", "river teal", "dawn rose"]),
    row("meadow", "C", "humour", "happens.", "d1_c_fist_clench",
        "extreme close-up of a fist clenching and unclenching in frustration, cracked dry knuckles, cold reddened skin"
        + CLOSE, "an hour passes and nothing is done", ["ochre", "umber", "river teal"], "hmm_thinking__v1"),
    row("meadow", "B", "tension", "skis,", "d1_plate_meadow_wind",
        "medium shot of trampled meadow grass bending in a cold wind, scattered boulders, long shadows" + PLATE,
        "someone has to break the deadlock before dark", ["ochre", "umber", "charcoal"], "pop_in__v1",
        [H("nansen", "point")], plate=True),
    row("meadow", "B", "tension", "matches?", "d1_plate_meadow_crowdedge",
        "medium shot of the edge of a windswept meadow with dry trampled grass, dark clouds and long shadows" + PLATE,
        "one question exposes that nobody can make fire", ["umber", "ochre", "charcoal"], "throat_clear__v1",
        [H("nansen", "point"), H("franklin", "dismay")], plate=True, friction=True),
    row("meadow", "C", "humour", "halfway.", "d1_c_two_hands_half",
        "extreme close-up of two hands rising only halfway above a row of shoulders, fingers hesitant and half curled, "
        "shaking slightly against a stormy sky" + CLOSE, "two hands, and neither is sure", ["ochre", "river teal", "umber"]),
    row("meadow", "C", "fear", "unsure.", "d1_c_empty_palms",
        "extreme close-up of two open empty palms held up, cold reddened trembling fingers, nothing in them" + CLOSE,
        "empty hands against the coming dark", ["umber", "charcoal", "night blue"]),
    row("meadow", "B", "humour", "rule.", "d1_plate_table_rock_wind",
        "medium shot of a flat rock like a table in a meadow where the wind bends the grass, walking sticks leaning on it, dark clouds" + PLATE,
        "someone must take control before panic does", ["ochre", "dawn rose", "umber"], "pop_in__v1",
        [H("franklin", "scheme"), H("newton", "argue")], plate=True, friction=True),
    row("meadow", "A", "tension", "safety.", "d1_a_ring_dusk",
        "epic wide establishing shot of a hundred tiny figures sitting in a wide ring on a hillside around a flat rock as "
        "the sky darkens, wind pulling at their coats, a long cold valley below", "a hundred people agree on one rule "
        "because the dark is coming", ["ochre", "river teal", "umber"], "swish__v1"),
    row("meadow", "B", "humour", "down.", "d1_plate_meadow_wind",
        "medium shot of trampled meadow grass bending in a cold wind, scattered boulders, long shadows" + PLATE,
        "even the loudest critic has to give in", ["ochre", "umber", "charcoal"], "pleased_mmhm__v1",
        [H("newton", "smug"), H("einstein", "think")], plate=True, friction=True, reuse=True),
    row("meadow", "A", "tension", "food.", "d1_a_three_tasks",
        "epic wide establishing shot of three tiny groups scattering across an unforgiving valley, one toward the river, "
        "one gathering wood on a stony slope, one scanning bare ground for food, a storm building overhead",
        "warmth, water, food: three jobs and one evening", ["ochre", "river teal", "umber"], "swish__v1"),
    row("water", "B", "tension", "ground.", "d1_plate_spring_rocks",
        "medium shot of mossy rocks where clear cold water seeps out of the ground, wet stones, long shadows" + PLATE,
        "clean water is the difference between life and a bad week", ["river teal", "ochre", "umber"], None,
        [H("wallace", "triumph")], plate=True),
    row("water", "C", "tension", "Snow,", "d1_c_ink_map",
        "extreme close-up of an ink-stained shaking hand drawing a map of a stream with a stick in wet mud" + CLOSE,
        "a wrong guess about where the water goes will make everyone sick", ["umber", "charcoal", "ochre"], "page_flip__v2"),
    row("water", "C", "fear", "months.", "d1_c_arrow_mud",
        "extreme close-up of a sharpened stick drawing an arrow in wet mud pointing downhill, away from a small pool"
        + CLOSE, "one arrow in the mud decides who stays healthy", ["umber", "charcoal", "river teal"], "pencil_scribble__v2"),
    row("water", "B", "tension", "spring.", "d1_plate_stream_marker",
        "medium shot of a cold clear stream with damp stones, a flat marker stone and a stuck twig far downstream, dim grey light, long shadows"
        + PLATE, "the wrong place for the latrine ends the expedition", ["river teal", "ochre", "umber"], "swish__v2",
        [H("snow", "point"), H("wallace", "argue")], plate=True, friction=True),
    row("dusk", "A", "fear", "arrives.", "d1_a_dusk_wind",
        "epic wide establishing shot of the river valley at dusk, wind bending the tall grass in long waves, storm grey "
        "clouds rolling over the hills, one tiny cluster of distant figures with no fire", "the wind rises and they have "
        "no fire", ["night blue", "charcoal", "dawn rose"]),
    row("dusk", "C", "fear", "clothes —", "d1_c_wet_sleeve",
        "extreme close-up of a damp wool coat sleeve beaded with water and a clenched shivering hand" + CLOSE,
        "cold, wind and wet clothes are the real killers", ["night blue", "charcoal", "umber"], "shiver_brr__v1"),
    row("dusk", "B", "tension", "branches,", "d1_plate_boulder_dusk",
        "medium shot of a big boulder at dusk with armfuls of long branches and dry grass scattered on the cold ground"
        + PLATE, "a windbreak must stand before the temperature drops", ["umber", "ochre", "charcoal"], "effort_hup__v1",
        [H("einstein", "struggle"), H("tesla", "argue")], plate=True, friction=True),
    row("dusk", "C", "tension", "against it.", "d1_c_branch_armful",
        "extreme close-up of two scraped arms pushing an armful of dry grass and thin branches against a slanting "
        "windbreak" + CLOSE, "every gap in the wall lets the wind in", ["umber", "ochre", "charcoal"], "cloth_rustle__v2"),
    row("dusk", "C", "calm", "is.", "d1_c_dry_grass",
        "extreme close-up of two hands pressing a thick loose bundle of dry grass and dead leaves, gripping it against "
        "the wind" + CLOSE, "trapped air is the only insulation they have", ["ochre", "umber"], "cloth_rustle__v3"),
    row("fire", "B", "tension", "drill.", "d1_plate_fire_pit",
        "medium shot of a shallow fire pit scraped in dry ground at dusk, a ring of stones, thin smoke, cold wind" + PLATE,
        "no fire means no night", ["umber", "ochre", "charcoal"], None, [H("nansen", "struggle")], plate=True),
    row("fire", "C", "tension", "smoke.", "s03_close_drill", "", "a dozen tries, sore hands and only smoke",
        ["umber", "ochre", "charcoal"], "groan_ugh__v1", reuse=True),
    row("fire", "B", "tension", "Then —", "d1_plate_tinder_wind",
        "medium shot of a flat stone with a nest of dry bark shreds and grass sheltered from a cold wind behind a "
        "boulder, thin smoke" + PLATE, "one gust and the tinder is gone", ["ochre", "umber", "fire amber"], None,
        [H("franklin", "plead")], plate=True),
    row("fire", "C", "discovery", "glasses.", "d1_c_spectacles",
        "extreme close-up of a hand lifting a pair of small round reading spectacles, last sunlight glinting on the lens, "
        "cold fingers trembling" + CLOSE, "the only tool in the valley sits on a nose", ["fire amber", "ochre"],
        "monocle_pop__v1"),
    row("fire", "C", "discovery", "sun.", "d1_c_lens_sun",
        "extreme close-up of a glass lens held above dry grass, a tiny bright point of sunlight focused on one blade, "
        "a thread of smoke starting" + CLOSE, "the sun is setting and this is the last chance", ["fire amber", "ochre", "umber"]),
    row("fire", "B", "discovery", "smoke...", "d1_plate_grass_smoke",
        "medium shot of a bare patch of dry grass at dusk with a thin thread of smoke rising, long shadows, wind dropping"
        + PLATE, "one bright point stands between them and a freezing night", ["fire amber", "umber"], "pop_in__v1",
        [H("einstein", "amazed"), H("franklin", "struggle")], plate=True, friction=True),
    row("fire", "C", "tension", "Fire!", "s07_close_spark", "", "a single spark must survive one careful breath",
        ["fire amber", "charcoal"], "gasp_inhale__v1", reuse=True),
    row("fire", "C", "joy", "keeping it.", "s09_close_flame", "", "a new flame is fragile and the wind is rising",
        ["fire amber", "charcoal"], "reveal_sting__v1", reuse=True),
    row("fire", "A", "tension", "shifts.", "s10_wide_night", "", "one small fire in an endless dark valley",
        ["night blue", "fire amber", "charcoal"], "swish__v1", reuse=True),
    row("night", "C", "fear", "nuts,", "d1_c_nuts_hand",
        "extreme close-up of a thin cupped trembling hand holding a few hazelnuts and a small speckled egg, hungry, "
        "fire shadows" + CLOSE, "a hundred people and a handful of food", ["ochre", "umber", "fire amber"]),
    row("night", "C", "fear", "grain.", "d1_c_food_hands",
        "extreme close-up of two hands holding a few hazelnuts, two small speckled eggs and some ears of raw wild grain, "
        "bare scraps in firelight" + CLOSE, "raw wild grain is not dinner, it is a gamble", ["ochre", "umber", "fire amber"]),
    row("night", "B", "tension", "know.", "d1_plate_unknown_plants",
        "medium shot of a firelit patch of ground with unfamiliar wild plants and berries laid out on a flat stone, deep "
        "shadows" + PLATE, "one wrong berry could poison someone tonight", ["fire amber", "umber", "charcoal"],
        "hmm_thinking__v1", [H("darwin", "recoil"), H("wallace", "argue")], plate=True, friction=True),
    row("end", "B", "tension", "rule.", "d1_plate_overhang_fire",
        "medium shot of a rock overhang lit by a small new fire, firewood stacked by the wall, long flickering shadows, "
        "cold night behind" + PLATE, "the fire must not die before dawn", ["fire amber", "umber", "charcoal"],
        "laugh_warm__v1", [H("franklin", "lecture"), H("nansen", "exhausted")], plate=True, friction=True),
    row("end", "A", "fear", "do.", "d1_a_valley_eyes",
        "epic wide establishing shot of the whole river valley at night under a sky full of stars, one tiny fire glowing "
        "beside a slanting windbreak, and far away on the dark treeline a pack of wolves watching from the shadows",
        "a tiny fire and a hundred people in an unforgiving valley", ["night blue", "charcoal", "fire amber"]),
    row("end", "C", "humour", "opinions.", "d1_c_blisters",
        "extreme close-up of two raw blistered palms held open to a small fire, cracked skin, flickering amber light"
        + CLOSE, "the first day cost everyone their hands", ["fire amber", "charcoal", "umber"], "sigh_tired__v1"),
    row("end", "C", "discovery", "pot.", "d1_c_clay",
        "extreme close-up of two hands holding a lump of wet grey river clay with thumbprints pressed into it, cold "
        "river mud dripping" + CLOSE, "the next problem has a shape: a pot", ["umber", "river teal", "charcoal"],
        "glow_ping__v1"),
]


def _norm(w: str) -> str:
    return w.lower().strip("\"'”’")


def phrase_end(phrase: str, after: float) -> int:
    """Index of the word holding the last token of the first occurrence of ``phrase`` that starts after ``after``."""
    toks = [_norm(t) for t in phrase.split()]
    flat = [(_norm(t), i) for i, w in enumerate(WORDS) for t in w["w"].split()]
    for k in range(len(flat) - len(toks) + 1):
        if WORDS[flat[k][1]]["s"] + 1e-6 < after:
            continue
        if [t for t, _ in flat[k:k + len(toks)]] == toks:
            return flat[k + len(toks) - 1][1]
    raise SystemExit(f"phrase {phrase!r} not found after {after:.2f} s")


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
    targets, prev = [], 0.0
    for r in SHOTS:
        i = phrase_end(r["anchor"], prev)
        t = END if i == len(WORDS) - 1 else (WORDS[i]["e"] + WORDS[i + 1]["s"]) / 2
        targets.append(t)
        prev = t
    cuts = R.solve_cuts([{"type": r["type"], "target": t} for r, t in zip(SHOTS, targets)], WORDS, END)
    if cuts is None:
        raise SystemExit("no cut layout fits this read: change a shot type, merge shots or add a clause pause (UR-12)")
    bounds = [0.0] + cuts + [END]
    shots = []
    for k, r in enumerate(SHOTS):
        start, end = round(bounds[k], 3), round(bounds[k + 1], 3)
        heroes = r["heroes"]
        shot = {"id": f"d1-{k + 1:02d}", "beat": r["beat"], "phase": "day1", "type": r["type"], "emotion": r["emotion"],
                "start": start, "end": end, "sentences": [j for j, (a, b, _) in enumerate(sents) if a < end and b > start],
                "motion": motion(r["type"], end - start, k), "transition": "cut", "picture": r["picture"],
                "source": "reuse" if r["reuse"] else "new",
                "face": ("caricature:" + "+".join(h["name"] for h in heroes)) if heroes else "none",
                "palette": r["palette"], "grade": R.grade_for(r["emotion"]), "stakes": r["stakes"]}
        if heroes:
            shot["heroes"] = heroes
        if r["plate"]:
            shot["plate"] = True
        if r["friction"]:
            shot["friction"] = True
        if r["subject"]:
            shot["prompt"] = R.compose_prompt(r["subject"], r["emotion"], LOOK)
        if r["sound"]:
            shot["sound"] = r["sound"]
            if k == 0:
                shot["sound_at"] = 0.0
        if k == len(SHOTS) - 1:
            shot["tail"] = True
        shots.append(shot)
    return shots


def timing_md(shots: list[dict]) -> str:
    lines = ["# Day 1 (rule base 2): timing", "", f"Words: {WORDS_DOC['source']}. Duration {END:.2f} s, {len(WORDS)} words. "
             "Provisional until the full v4 read exists.", "",
             "| # | in | out | len | type | emotion | picture | heroes | stakes | narration over the shot |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in shots:
        text = " ".join(w["w"] for w in WORDS if s["start"] <= w["s"] < s["end"])
        heroes = ", ".join(f"{h['name']}:{h['pose']}" for h in s.get("heroes", [])) or "-"
        lines.append(f"| {s['id']} | {s['start']:.2f} | {s['end']:.2f} | {s['end'] - s['start']:.2f} | {s['type']} | "
                     f"{s['emotion']} | {s['picture']} | {heroes} | {s['stakes']} | {text} |")
    return "\n".join(lines) + "\n"


def sprite_needs(shots: list[dict]) -> str:
    bank = LOOK.get("pose_bank", {})
    need: dict[str, set[str]] = {}
    base_missing = set()
    for s in shots:
        for h in s.get("heroes", []):
            if h["name"] not in LOOK.get("caricatures", []):
                base_missing.add(h["name"])
            if h["pose"] not in bank.get(h["name"], []):
                need.setdefault(h["name"], set()).add(h["pose"])
    n = sum(len(v) for v in need.values()) + len(base_missing)
    lines = ["# Hero sprites to make (reusable channel assets, Gemini allowed, about $0.067 each)", "",
             f"{n} images: {len(base_missing)} new heroes (base design) + {sum(len(v) for v in need.values())} poses.", ""]
    if base_missing:
        lines += ["New heroes (no caricature yet): " + ", ".join(sorted(base_missing)), ""]
    lines += [f"- {name}: {', '.join(sorted(poses))}" for name, poses in sorted(need.items())]
    return "\n".join(lines) + "\n"


def sound_ids() -> set[str]:
    m = json.loads((ROOT / "assets/audio/library/manifest.json").read_text(encoding="utf-8"))
    return {x["id"] for x in m["items"]}


def pod_job(shots: list[dict]) -> dict:
    seen, pics, seed = set(), [], 102
    for s in shots:
        if s["source"] == "new" and s["picture"] not in seen:
            seen.add(s["picture"])
            pics.append({"id": s["picture"], "shot": s["id"], "type": s["type"], "emotion": s["emotion"],
                         "prompt": s["prompt"], "seed": seed})
            seed += 1
    return {"name": "stone_age_day1_v2", "width": 1920, "height": 1088, "steps": 9,
            "suffix": LOOK["style_suffix"], "note": "Day 1 under rule base 2 (UR-16..UR-20): built by "
            "explainer-engine examples/stone_age/day1_v4/build_shots.py; plates are painted without people, heroes are "
            "our sprites.", "pictures": pics}


if __name__ == "__main__":
    shots = build()
    (HERE / "shots.json").write_text(json.dumps({"version": 2, "segment": "day1", "duration": END, "shots": shots},
                                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "timing.md").write_text(timing_md(shots), encoding="utf-8")
    (HERE / "pod_job.json").write_text(json.dumps(pod_job(shots), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "sprite_needs.md").write_text(sprite_needs(shots), encoding="utf-8")
    found = R.check_shots(shots, WORDS, LOOK, sound_ids=sound_ids())
    report = ["# Day 1 (rule base 2): Universal Rule Base check", ""]
    report += [f"- {f['severity']} {f['rule']} {f['shot']}: {f['detail']}" for f in found] or ["- no findings"]
    fails = sum(f["severity"] == "FAIL" for f in found)
    report += ["", f"{len(shots)} shots, {fails} FAIL, {len(found) - fails} REVIEW"]
    (HERE / "check_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    raise SystemExit(1 if fails else 0)
