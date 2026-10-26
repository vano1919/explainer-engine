"""Cast sheet for xworld v2: 100 invented people, full body in full costume on a plain background (ვანო 2026-10-26 12:01-12:02
Tbilisi, with his reference picture `style_ref` = four labelled figures: Napoleonic officer, caveman, Renaissance man,
space cadet).

His brief: the line stays close to the training show's line; the costume, the face style and the colour palette differ from
it; the palette and the drawing are those of his reference; every prompt = ONE shared style block (STYLE, word for word in
all 100) + the person's own description, so the pictures differ only by person. The faces follow LT-79
(`pods.xworld_v1_story.face_parts` / `show_traits`): each names its shape, eyes, nose, brows, jaw or chin and mouth, and none uses
a trait or name of the show's people. Pictures go into training only after ვანო picks them.

    python -m explainer_engine.training.cast.sheet list            # the 100 prompts (free)
    python -m explainer_engine.training.cast.sheet check           # LT-79 and the style block (free)
    python -m explainer_engine.training.cast.sheet draw <out> --ids 0,1,2,3 [--ref style_ref.jpg] --yes   # paid (BFL Klein)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

from explainer_engine.training.pods.xworld_v1_story import FACE_PARTS_MIN, face_parts, show_traits

# One shared style core for every picture of the new world; each kind (person, place, object) has its own fixed frame
# sentence in front, so pictures differ only by subject. A person, a place and an object are never in one picture
# (ვანო 2026-10-26 12:11 Tbilisi: places without people, people without things beyond what they wear or hold).
CORE = ("Bold clean black ink outlines of even medium-thick weight, flat saturated cel colours with one soft shadow "
        "tone, a few fine hatch lines in hair, beard and fabric folds. Colour palette: rich navy blue, crimson red, golden "
        "yellow, ochre orange, forest green, burgundy, warm skin tones, cream and charcoal black.")
FRAMES = {
    "person": ("Flat 2D adult TV cartoon character design, one person, full body from head to shoes, standing in a relaxed "
               "three-quarter pose, centred, on a plain warm off-white paper background with nothing else in the picture "
               "and no text."),
    "place": ("Flat 2D adult TV cartoon background painting, an empty location with no people, no animals and no text, "
              "seen as a wide establishing shot."),
    "object": ("Flat 2D adult TV cartoon prop design, one single object, centred, on a plain warm off-white paper "
               "background with nothing else in the picture, no people, no hands and no text."),
}
EYES_NOTE = "Eyes are almond-shaped with dark irises and clearly drawn upper eyelids."
STYLE = f"{FRAMES['person']} {CORE} {EYES_NOTE}"
STYLES = {"person": STYLE, "place": f"{FRAMES['place']} {CORE}".replace(", a few fine hatch lines in hair, beard and fabric folds", ", a few fine hatch lines on wood, stone and fabric"),
          "object": f"{FRAMES['object']} {CORE}".replace(", a few fine hatch lines in hair, beard and fabric folds", ", a few fine hatch lines on wood, metal and fabric")}
ASPECTS = {"person": "3:4", "place": "16:9", "object": "1:1"}

# Sample places and objects (ვანო 12:11: "show me some examples" before the whole world)
PLACES = [
    ("p000", "A Roman street at noon: stone paving, a fountain, shuttered shops with awnings, laundry lines, a temple at the end."),
    ("p001", "Inside a large canvas army tent at night: a map table with wooden figures, a hanging brass lantern, a folded cot, an iron-bound chest."),
    ("p002", "A wide green meadow at dawn seen from a grassy hilltop: distant blue hills, a winding river, morning mist, a pale orange sky."),
    ("p003", "A Stone Age cave interior: a crackling fire, painted animals on the rock wall, furs on the floor, the cave mouth showing a snowy valley."),
    ("p004", "A starship cockpit: two empty pilot seats, glowing control panels, a curved window onto a ringed planet and stars."),
    ("p005", "A Renaissance painter's workshop: easels with half-finished canvases, jars of pigment, a tall window, wooden beams."),
]
OBJECTS = [
    ("o000", "An antique brass spyglass, extended, with leather grip bands."),
    ("o001", "A wooden campaign map table with a rolled map, brass dividers and small carved army figures on it."),
    ("o002", "A Roman two-wheeled racing chariot with red painted panels and bronze fittings."),
    ("o003", "A Stone Age flint-tipped spear leaning on a large rough stone, with a bone necklace hanging from it."),
    ("o004", "A chunky retro-futuristic ray gun with brass coils and a glowing green glass tank."),
    ("o005", "A medieval blacksmith's anvil on a tree stump, with tongs and a glowing horseshoe."),
]


MODEL, SIZE = "flux-3-image-klein", "1k"
REF_NOTE = "Image 1 shows only the drawing style and colour palette to use; draw a new, different person."
KEY_ENV = ("BFL_API_kay", "BFL_API_KEY")  # 2026-10-26: the first answers 403 "Not authenticated", the second works

# 50 roles x 2 people (a man and a woman, or two ages): era, role, costume and one held object
ROLES = [
    ("Roman", "legion centurion", "a red tunic, segmented steel armour, a transverse red-crested helmet, leather sandals", "a short sword"),
    ("Roman", "senator", "a white toga with a broad purple border over a tunic, leather sandals", "a wax tablet"),
    ("Egyptian", "temple scribe", "a white linen kilt, a broad beaded collar, a shaved head band, reed sandals", "a papyrus roll"),
    ("Greek", "hoplite", "a bronze cuirass, a crested Corinthian helmet pushed up, a red cloak, greaves", "a round bronze shield"),
    ("Viking", "raider", "a quilted wool tunic, a fur-trimmed cloak, a plain iron helmet, leather boots with wrappings", "a bearded axe"),
    ("medieval", "blacksmith", "a soot-stained leather apron over a rough linen shirt, rolled sleeves, heavy boots", "a hammer"),
    ("medieval", "knight", "a full suit of plate armour with a blue surcoat bearing a gold lion", "a helmet under one arm"),
    ("medieval", "monk", "a coarse brown habit with a rope belt and a hood down, sandals", "a heavy book"),
    ("Mongol", "horse archer", "a padded deel coat with a sash, a fur-trimmed pointed hat, riding boots", "a recurve bow"),
    ("Ottoman", "janissary", "a long red kaftan, a tall white felt cap, baggy trousers, curled slippers", "a musket"),
    ("Samurai-era Japanese", "ronin", "a faded indigo kimono with hakama trousers, straw sandals", "a sheathed sword"),
    ("Chinese imperial", "court official", "a long embroidered silk robe with a square badge, a black winged hat", "a folded fan"),
    ("Aztec", "eagle warrior", "a feathered eagle helmet, a quilted cotton armour suit, sandals", "an obsidian-edged club"),
    ("Renaissance", "painter", "a paint-spattered smock over doublet and hose, a soft beret", "a palette and brush"),
    ("Renaissance", "merchant banker", "a fur-lined velvet gown over a doublet, a gold chain, a flat cap", "a ledger"),
    ("Elizabethan", "actor", "a slashed doublet, a white ruff collar, puffed breeches, stockings", "a skull prop"),
    ("Age of Sail", "pirate captain", "a long coat with brass buttons, a tricorne hat, a sash, tall boots", "a spyglass"),
    ("Age of Sail", "navy cabin cook", "a striped shirt, a stained apron, a knotted neckerchief, bare feet", "a ladle"),
    ("colonial American", "printer", "a waistcoat over a linen shirt, breeches, an ink-stained apron", "a freshly printed pamphlet"),
    ("French Revolution", "street orator", "a red Phrygian cap, a short jacket, striped trousers, a tricolour sash", "a rolled pamphlet"),
    ("Napoleonic", "grenadier", "a tall bearskin hat, a blue tailcoat with red facings, white breeches, black gaiters", "a musket"),
    ("Napoleonic", "army doctor", "a dark green coat, a bloodied apron, a bicorne hat, boots", "a leather medical bag"),
    ("Victorian", "chimney sweep", "a sooty jacket and cap, patched trousers, worn boots", "a long round brush"),
    ("Victorian", "inventor", "a tweed waistcoat, rolled shirt sleeves, brass goggles pushed onto the forehead", "a small brass contraption"),
    ("Victorian", "police constable", "a dark blue tunic with silver buttons, a custodian helmet, a belt", "a wooden truncheon"),
    ("Wild West", "sheriff", "a leather vest with a star badge, a wide-brimmed hat, chaps, spurred boots", "a lasso"),
    ("Wild West", "saloon pianist", "a striped shirt with sleeve garters, a bowler hat, a waistcoat", "sheet music"),
    ("Edwardian", "polar explorer", "a fur parka with a deep hood thrown back, mittens on a cord, snow boots", "an ice axe"),
    ("1920s", "jazz trumpeter", "a pinstriped suit, a loosened bow tie, two-tone shoes", "a trumpet"),
    ("1920s", "aviator", "a leather flight jacket, a white scarf, a leather cap with goggles, jodhpurs", "a map case"),
    ("1940s", "radio operator", "an olive field uniform, headphones around the neck, a webbing belt", "a microphone"),
    ("1950s", "diner waitress", "a mustard uniform dress with a white apron and a small cap", "a coffee pot"),
    ("1960s", "space-race engineer", "a short-sleeved white shirt with a narrow tie, a pocket protector, dark trousers", "a slide rule"),
    ("1970s", "disco roller skater", "a crimson jumpsuit with a wide collar, knee pads, roller skates", "a boombox"),
    ("1980s", "arcade mechanic", "navy overalls over a striped T-shirt, a tool belt, sneakers", "a screwdriver"),
    ("modern", "TV news reporter", "a burgundy blazer over a cream blouse, dark trousers, low heels", "a microphone"),
    ("modern", "construction worker", "a hard hat, a high-visibility orange vest over a navy shirt, work boots", "a rolled blueprint"),
    ("modern", "museum guard", "a charcoal uniform jacket with a badge, pressed trousers, polished shoes", "a radio"),
    ("modern", "street food cook", "a red bandana, a stained white jacket, checked trousers, clogs", "a spatula"),
    ("modern", "marathon runner", "a numbered running vest, shorts, a sweatband, running shoes", "a water bottle"),
    ("near future", "drone courier", "a padded navy jacket with reflective stripes, a cargo harness, sturdy boots", "a parcel"),
    ("near future", "deep-sea diver", "a heavy ochre diving suit with a brass collar, weighted boots", "a round brass helmet"),
    ("far future", "starship pilot", "a fitted navy flight suit with gold piping, gloves, magnetic boots", "a flight helmet"),
    ("far future", "Mars farmer", "a dusty ochre pressure suit with patches, a utility belt, heavy boots", "a seedling in a pot"),
    ("far future", "robot repair tech", "a burgundy coverall with many pockets, a tool harness, welding gloves", "a glowing wrench"),
    ("Stone Age", "cave painter", "a hide wrap tied at the shoulder, a fur belt, bare feet", "a handful of ochre pigment"),
    ("Stone Age", "mammoth hunter", "layered hides and furs, a bone necklace, wrapped hide boots", "a long spear"),
    ("Bronze Age", "trader", "a dyed wool tunic with a fringed shawl, a leather pouch belt, sandals", "a copper ingot"),
    ("Persian", "royal messenger", "a long belted coat, trousers, a soft rounded cap, riding boots", "a sealed scroll"),
    ("Byzantine", "chariot racer", "a laced leather vest in team green, a padded cap, wrapped forearms", "a whip"),
]

SHAPES = ["a long narrow face", "a square face", "a heart-shaped face", "a wide flat face", "a long oval face",
          "a gaunt bony face", "a fleshy jowly face", "a triangular face", "a broad rectangular face", "a pear-shaped face"]
EYES = ["small hooded eyes", "narrow almond eyes", "deep-set heavy-lidded eyes", "wide-set almond eyes", "sleepy half-closed eyes",
        "sharp slanted eyes", "close-set squinting eyes", "large almond eyes with long lashes"]
NOSES = ["a long hooked nose", "a short upturned nose", "a broad flat nose", "a thin pointed nose", "a bulbous nose",
         "a straight Roman nose", "a crooked broken nose", "a small button nose"]
BROWS = ["heavy dark eyebrows", "thin arched eyebrows", "bushy grey eyebrows", "straight thick eyebrows",
         "sparse pale eyebrows", "angled stern eyebrows"]
JAWS = ["a heavy square jaw", "a pointed chin", "a double chin", "a cleft chin", "a weak receding chin", "a long jutting jaw"]
MOUTHS = ["thin tight lips", "a wide grin", "full lips", "a small pursed mouth", "a lopsided smirk", "a downturned mouth"]
HAIR = ["short black curls", "a grey ponytail", "a shaved head", "thick auburn hair in a bun", "long straight black hair",
        "a receding hairline", "short cropped blond hair", "wild white hair", "two dark braids", "slicked-back brown hair"]
PEOPLE = [("man", "middle-aged"), ("woman", "young"), ("man", "old"), ("woman", "middle-aged"), ("man", "young"),
          ("woman", "old")]


def cast(seed: int = 26):
    """The 100 people: [{id, era, role, person, face, outfit, desc}]; deterministic for a seed."""
    rng, out = random.Random(seed), []
    for i in range(100):
        era, role, outfit, prop = ROLES[i // 2]
        sex, age = PEOPLE[(i // 2 + i) % len(PEOPLE)]
        he = "He" if sex == "man" else "She"
        face = (f"{he} has {rng.choice(SHAPES)} with {rng.choice(EYES)}, {rng.choice(BROWS)}, {rng.choice(NOSES)}, "
                f"{rng.choice(JAWS)} and {rng.choice(MOUTHS)}, and {rng.choice(HAIR)}.")
        if role.endswith("monk"):
            face = face.rsplit(", and ", 1)[0] + ", and a tonsured head."
        person = f"A {age} {era} {role}, a {sex}"
        desc = f"{person}, wearing {outfit}, holding {prop}. {face}"
        out.append({"id": f"c{i:03d}", "era": era, "role": role, "person": person, "face": face, "outfit": outfit, "desc": desc})
    return out


def prompt(c, ref=False):
    kind = c.get("kind", "person")
    label = {"person": "Character", "place": "Location", "object": "Object"}[kind]
    return f"{STYLES[kind]} {REF_NOTE + ' ' if ref else ''}{label}: {c['desc']}"


def problems(people=None):
    """LT-79 on every face, plus: one shared style block, unique faces, unique descriptions."""
    people = people or cast()
    out = []
    for c in people:
        parts = face_parts(c["face"])
        if len(parts) < FACE_PARTS_MIN:
            out.append(f"{c['id']}: face names {parts}")
        show = show_traits(c["desc"])
        if show:
            out.append(f"{c['id']}: trait of the training show's people: {show}")
        if not prompt(c).startswith(STYLE):
            out.append(f"{c['id']}: the prompt does not start with the shared style block")
    if len({c["face"] for c in people}) != len(people):
        out.append("two people share a face")
    if len({c["desc"] for c in people}) != len(people):
        out.append("two people share a description")
    return out


def _key():
    for k in KEY_ENV:
        if os.environ.get(k, "").strip():
            return os.environ[k].strip()
    raise SystemExit(f"no BFL key in {KEY_ENV}")


def draw(out, ids, ref=None, ledger=None, key_env=None):
    """Paid: one BFL Klein picture per id (cached by request; a seed per person so a redraw is the same picture)."""
    from explainer_engine.core.ledger import Run
    from explainer_engine.imagegen.providers.bfl import BFL
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    run = Run.open(ledger, caps={"bfl_usd": 3.0}) if ledger else None
    key = os.environ[key_env].strip() if key_env else _key()
    p = BFL(out, run=run, key=key)
    refs = [Path(ref).read_bytes()] if ref else []
    people = {c["id"]: c for c in cast()}
    people.update({i: {"id": i, "kind": "place", "desc": d} for i, d in PLACES})
    people.update({i: {"id": i, "kind": "object", "desc": d} for i, d in OBJECTS})
    rows = []
    for i in ids:
        c = people[i]
        name = f"{i}{'_ref' if ref else ''}"
        kind = c.get("kind", "person")
        r = p.generate(name, prompt(c, bool(ref)), model=MODEL, size=SIZE, refs=refs, seed=1000 + int(i[1:]),
                       extra={"aspect_ratio": ASPECTS[kind], "safety_tolerance": 2})
        rows.append({"name": name, "id": i, "usd": r.usd_settled if r.usd_settled is not None else r.usd, "cached": r.cached})
        print(name, rows[-1]["usd"], flush=True)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.training.cast.sheet")
    ap.add_argument("cmd", choices=["list", "check", "draw"])
    ap.add_argument("out", nargs="?")
    ap.add_argument("--ids", default="")
    ap.add_argument("--ref")
    ap.add_argument("--ledger")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for c in cast():
            print(json.dumps({"id": c["id"], "prompt": prompt(c)}, ensure_ascii=False))
        return 0
    if a.cmd == "check":
        pr = problems()
        print("\n".join(pr) or "ok: 100 people, one style block, LT-79 faces")
        return 1 if pr else 0
    if problems():
        raise SystemExit("refused: `check` has problems")
    ids = [f"c{int(x):03d}" if x.isdigit() else x for x in a.ids.split(",") if x] or [c["id"] for c in cast()]
    usd = round(BFLPRICE * len(ids), 3)
    if not a.yes:
        print(f"estimate {len(ids)} pictures x ${BFLPRICE} = ${usd}; add --yes after the creator's OK")
        return 0
    draw(a.out, ids, ref=a.ref, ledger=a.ledger)
    return 0


BFLPRICE = 0.009  # Klein 1k (imagegen/providers/bfl.py PRICES, checked 2026-10-22)

if __name__ == "__main__":
    sys.exit(main())
