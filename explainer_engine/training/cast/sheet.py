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
import time
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

# Places and objects: the first 6 of each were the samples ვანო saw (12:11 "show me some examples"); the rest follow the
# same eras as the people (12:30 "start")
PLACES = [
    ("p000", "A Roman street at noon: stone paving, a fountain, shuttered shops with awnings, laundry lines, a temple at the end."),
    ("p001", "Inside a large canvas army tent at night: a map table with wooden figures, a hanging brass lantern, a folded cot, an iron-bound chest."),
    ("p002", "A wide green meadow at dawn seen from a grassy hilltop: distant blue hills, a winding river, morning mist, a pale orange sky."),
    ("p003", "A Stone Age cave interior: a crackling fire, painted animals on the rock wall, furs on the floor, the cave mouth showing a snowy valley."),
    ("p004", "A starship cockpit: two empty pilot seats, glowing control panels, a curved window onto a ringed planet and stars."),
    ("p005", "A Renaissance painter's workshop: easels with half-finished canvases, jars of pigment, a tall window, wooden beams."),
    ("p006", 'A Roman Colosseum arena floor at midday: sand, wooden trapdoors, tiered stone seats, striped awnings above.'),
    ("p007", 'A Roman villa courtyard: a rectangular pool, painted columns, potted lemon trees, mosaic floor.'),
    ("p008", 'A Roman legion camp at dusk: rows of leather tents, a palisade wall, standards on poles, cooking fires.'),
    ("p009", 'An Egyptian temple hall: giant painted columns, hieroglyph walls, shafts of sunlight, a stone altar.'),
    ("p010", 'The Nile riverbank at sunset: papyrus reeds, a moored reed boat, distant pyramids, palm trees.'),
    ("p011", 'A Greek agora: a colonnaded stoa, market stalls with amphorae, a stone altar, olive trees.'),
    ("p012", 'A Greek hilltop temple ruin under a stormy sky: broken columns, scattered marble blocks, wild grass.'),
    ("p013", 'A Viking longhouse interior: a long central hearth, carved wooden pillars, shields on the walls, benches with furs.'),
    ("p014", 'A Viking fjord at dawn: steep cliffs, a longship pulled up on a pebble beach, still green water.'),
    ("p015", 'A medieval castle great hall: banners, a long feast table with pewter plates, a huge fireplace, stone arches.'),
    ("p016", 'A medieval village square on market day: half-timbered houses, a well, empty stalls with cloth roofs, a church tower.'),
    ("p017", "A medieval blacksmith's forge: a glowing furnace, bellows, an anvil, tools hung on the wall."),
    ("p018", 'A medieval monastery library: tall shelves of chained books, reading desks, candles, a rose window.'),
    ("p019", 'A castle battlement at night: crenellated walls, a torch in a bracket, a view over moonlit fields.'),
    ("p020", 'A muddy medieval battlefield after rain: broken lances, abandoned shields, trampled banners, grey sky.'),
    ("p021", "A Mongol yurt camp on the steppe: round felt tents, tethered horses' posts, endless grass, a huge sky."),
    ("p022", 'Inside a Mongol yurt: a central stove, painted wooden roof ring, rugs, chests, a low table.'),
    ("p023", 'An Ottoman bazaar street: hanging lamps, carpet stalls, spice sacks, a domed mosque in the distance.'),
    ("p024", 'A Japanese castle garden: a koi pond, a red arched bridge, stone lanterns, pine trees, the castle keep behind.'),
    ("p025", 'A Japanese village street in the rain: wooden houses with sliding doors, paper lanterns, puddles.'),
    ("p026", 'A Chinese imperial palace courtyard: red walls, golden roof tiles, marble stairs, bronze incense burners.'),
    ("p027", 'An Aztec city plaza: a stepped pyramid temple, canals, flower boats, volcanoes on the horizon.'),
    ("p028", 'A jungle temple ruin: vines over carved stone heads, a collapsed stairway, mist, a dense green canopy.'),
    ("p029", 'A Renaissance city piazza: a domed cathedral, a marble fountain, arcades, terracotta rooftops.'),
    ("p030", "A Renaissance banker's counting house: a long table with scales and coin piles, ledgers, tapestries."),
    ("p031", 'An Elizabethan theatre stage: a wooden thrust stage, a painted balcony, an open-air pit, thatched galleries.'),
    ("p032", "A pirate ship deck at sea: masts and furled sails, cannons, coiled ropes, a ship's wheel, open ocean."),
    ("p033", 'A pirate cove: a sandy beach, a wrecked rowing boat, palm trees, a treasure chest half buried, a cave mouth.'),
    ("p034", "A ship's captain's cabin: a stern window with sea view, charts on a table, a swinging lantern, a sea chest."),
    ("p035", 'A colonial American print shop: a wooden printing press, type cases, hanging paper sheets, ink pots.'),
    ("p036", 'A Paris street during the Revolution: cobblestones, a barricade of carts and furniture, tricolour flags, tall houses.'),
    ("p037", 'A Napoleonic battlefield at noon: smoke over rolling hills, abandoned cannons, a broken wagon wheel, a farmhouse.'),
    ("p038", "A Napoleonic field hospital tent: cots, bandage rolls, a surgeon's table, lanterns, rain at the entrance."),
    ("p039", 'A snowy Russian forest road in winter: tall birches, deep snow, an abandoned wagon, grey sky.'),
    ("p040", 'A Victorian London street at night: gas lamps, fog, a horse-drawn cab waiting, shop windows, wet cobbles.'),
    ("p041", "A Victorian inventor's laboratory: brass machines, glass tubes, blackboards with diagrams, a skylight."),
    ("p042", 'A Victorian railway station: an iron and glass roof, a steam locomotive at the platform, luggage carts.'),
    ("p043", 'A Victorian rooftop at dusk: chimney stacks, slate roofs, smoke, the dome of a cathedral far away.'),
    ("p044", 'A Wild West main street at noon: a saloon, a general store, hitching posts, a water trough, dust.'),
    ("p045", 'A Wild West saloon interior: a long bar, an upright piano, swinging doors, card tables, a moose head.'),
    ("p046", 'A desert canyon at sunset: red rock mesas, cacti, a dry riverbed, long shadows.'),
    ("p047", 'A gold rush river camp: canvas tents, sluice boxes, pans, pine forest, a wooden cabin.'),
    ("p048", 'An Edwardian polar camp: a canvas tent in snow, a sledge, flags, ice cliffs, a pale sun.'),
    ("p049", 'A 1920s jazz club: a small stage with a drum kit, round tables with lamps, a bar, smoke haze.'),
    ("p050", 'A 1920s airfield: a biplane on a grass strip, a wooden hangar, a windsock, fuel barrels.'),
    ("p051", 'A 1940s radio room in a bunker: switchboards, maps with pins, a microphone, a single bulb.'),
    ("p052", 'A 1950s diner interior: a chrome counter with stools, red booths, a jukebox, a pie display.'),
    ("p053", 'A 1950s suburban street: identical houses with lawns, a mailbox, a parked rounded car, a picket fence.'),
    ("p054", 'A 1960s rocket launch control room: rows of consoles, big wall screens, coffee cups, ashtrays.'),
    ("p055", 'A 1970s roller disco: a glittering mirror ball, a wooden rink, coloured lights, a DJ booth.'),
    ("p056", 'A 1980s video arcade: rows of cabinets with glowing screens, a carpet with patterns, a change machine.'),
    ("p057", 'A modern TV news studio: a curved anchor desk, cameras on pedestals, screens, studio lights.'),
    ("p058", 'A modern construction site: a crane, steel beams, scaffolding, cement mixers, a site office.'),
    ("p059", 'A modern museum hall: dinosaur skeleton, glass display cases, marble floor, a skylight.'),
    ("p060", 'A modern night market: food stalls with steam, string lights, plastic stools, painted wooden signs.'),
    ("p061", 'A modern city rooftop: water tanks, antennas, a skyline at sunset, a pigeon coop.'),
    ("p062", 'A modern subway platform: tiled walls, a bench, a timetable board, an empty train with doors open.'),
    ("p063", 'A near-future drone delivery hub: landing pads, parcel racks, charging docks, a glass control tower.'),
    ("p064", 'A deep-sea research station interior: round portholes onto dark water with fish, pipes, a control desk.'),
    ("p065", 'A Mars farm dome: rows of green plants under a glass dome, red desert and dust outside, irrigation pipes.'),
    ("p066", 'A Mars surface at noon: red rocks, a parked rover, a habitat module, a pale pink sky.'),
    ("p067", 'A far-future space station corridor: curved walls, glowing strips, hatch doors, a window onto Earth.'),
    ("p068", 'A far-future robot repair shop: robot parts on shelves, a workbench, hanging cables, sparks frozen in air.'),
    ("p069", 'An alien jungle planet: giant mushroom trees, glowing plants, two moons in the sky, a crashed pod.'),
    ("p070", 'A futuristic city skyline at night: towers with lights, flying-car lanes, holographic billboards without letters.'),
    ("p071", 'A Stone Age river valley: a mammoth trail, birch trees, a smoking campfire, distant snowy peaks.'),
    ("p072", 'A Stone Age hunting camp: hide tents, drying racks with meat, stone tools on a log, a fire pit.'),
    ("p073", 'A Bronze Age harbour: wooden ships with square sails, clay jars on the quay, mud-brick warehouses.'),
    ("p074", 'A Persian palace hall: tall columns with bull capitals, a throne platform, hanging carpets, braziers.'),
    ("p075", 'A Byzantine hippodrome: a sand racetrack, a central spine with obelisks, packed empty stands, bronze horses.'),
    ("p076", 'A dark old library at midnight: towering shelves, a rolling ladder, a desk with an open book and candle.'),
    ("p077", 'A mountain pass in a snowstorm: a narrow path, rocks, a wooden signpost, swirling snow.'),
    ("p078", 'A peaceful farm at sunrise: a red barn, a windmill, a haystack, a fenced field, a hay cart.'),
    ("p079", "A lighthouse on a rocky cliff at night: a beam of light, crashing waves, a small keeper's cottage."),
]
OBJECTS = [
    ("o000", "An antique brass spyglass, extended, with leather grip bands."),
    ("o001", "A wooden campaign map table with a rolled map, brass dividers and small carved army figures on it."),
    ("o002", "A Roman two-wheeled racing chariot with red painted panels and bronze fittings."),
    ("o003", "A Stone Age flint-tipped spear leaning on a large rough stone, with a bone necklace hanging from it."),
    ("o004", "A chunky retro-futuristic ray gun with brass coils and a glowing green glass tank."),
    ("o005", "A medieval blacksmith's anvil on a tree stump, with tongs and a glowing horseshoe."),
    ("o006", 'A Roman legionary helmet with a red crest.'),
    ("o007", 'An Egyptian golden mask on a stand.'),
    ("o008", 'A Greek clay amphora with painted figures.'),
    ("o009", 'A Viking round shield with a painted dragon.'),
    ("o010", 'A medieval longsword in a leather scabbard.'),
    ("o011", "A knight's full suit of armour on a stand."),
    ("o012", 'An illuminated manuscript book, open, with a ribbon.'),
    ("o013", 'A Mongol composite bow with a quiver of arrows.'),
    ("o014", 'A samurai katana on a lacquered stand.'),
    ("o015", 'A Chinese bronze incense burner.'),
    ("o016", 'An Aztec feathered ceremonial headdress on a stand.'),
    ("o017", "A Renaissance artist's easel with a blank canvas."),
    ("o018", 'A heavy iron-bound treasure chest, open, full of gold coins.'),
    ("o019", "A ship's wheel made of dark wood and brass."),
    ("o020", "A pirate's flintlock pistol."),
    ("o021", 'A colonial wooden printing press.'),
    ("o022", 'A Napoleonic bicorne hat on a wooden head stand.'),
    ("o023", 'A brass field cannon on a wooden carriage.'),
    ("o024", 'A Victorian pocket watch with its chain.'),
    ("o025", 'A steam locomotive, side view.'),
    ("o026", 'A Victorian brass telephone.'),
    ("o027", 'A Wild West revolver in a leather holster.'),
    ("o028", 'An old wooden covered wagon.'),
    ("o029", 'A 1920s biplane, side view.'),
    ("o030", 'A 1920s gramophone with a large horn.'),
    ("o031", 'A 1940s military radio set with headphones.'),
    ("o032", 'A 1950s jukebox.'),
    ("o033", 'A 1950s rounded red car.'),
    ("o034", 'A 1960s rocket on its launch pad.'),
    ("o035", 'A 1980s arcade cabinet.'),
    ("o036", 'A modern drone with four rotors.'),
    ("o037", 'A brass deep-sea diving helmet.'),
    ("o038", 'A Mars rover with six wheels.'),
    ("o039", 'A far-future starfighter, side view.'),
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


LEDGER_HELP = ("the run ledger (run.json); every BFL call reserves against config/spend_caps.json per_episode.bfl_usd and stops at 80 % "
               "(D-56, CN-10)")
NO_LEDGER = "refused: paid BFL calls run only inside a ledger (D-56); pass --ledger"


def _run(ledger, budget_usd=None):
    """The run ledger every paid BFL call reserves on (N-02): its bfl_usd cap is config/spend_caps.json's per_episode.bfl_usd for a
    new ledger (``Run.open``), and the 80 % stop is the ledger's. A ``budget_usd`` above that cap is refused, never raised to it."""
    from explainer_engine.core.ledger import Run
    if not ledger:
        raise ValueError(NO_LEDGER)
    run = Run.open(ledger)
    cap = run.data["caps"].get("bfl_usd")
    if budget_usd is not None and (cap is None or budget_usd > cap + 1e-9):
        raise ValueError(f"refused: --budget {budget_usd} is above the ledger's bfl_usd cap {cap} (config/spend_caps.json "
                         "per_episode.bfl_usd); the cap changes only on the creator's word")
    return run


def draw(out, ids, ref=None, ledger=None, key_env=None):
    """Paid: one BFL Klein picture per id (cached by request; a seed per person so a redraw is the same picture).
    Only inside a ledger (N-02): the BFL client gets its run and reserves every call."""
    from explainer_engine.imagegen.providers.bfl import BFL
    run = _run(ledger)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
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


def items():
    """Every picture of the new world: {id: {id, kind, desc, ...}} (100 people, the places, the objects)."""
    out = {c["id"]: {**c, "kind": "person"} for c in cast()}
    out.update({i: {"id": i, "kind": "place", "desc": d} for i, d in PLACES})
    out.update({i: {"id": i, "kind": "object", "desc": d} for i, d in OBJECTS})
    return out


def world(out, ids, *, budget_usd, tries=3, workers=6, key=None, generate=None, judge=None, ledger=None):
    """Draw every id, check it at once (cast.check), redraw a FAIL with the next seed (at most `tries` pictures per id)
    until `budget_usd` is spent; REVIEW and PASS stay for Claude's look and ვანო's pick. Writes <out>/report.jsonl (one
    row per picture drawn, kept or thrown away) and returns the rows. `generate(name, item, seed) -> usd` and
    `judge(rows) -> rows` are injected by tests. The real (BFL) path runs only inside a ledger (N-02): every call reserves on it
    and `budget_usd` may not pass its bfl_usd cap; the local `spent` counter is the budget display, the ledger is the stop."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from explainer_engine.training.cast import check
    out = Path(out)
    every = items()
    run = _run(ledger, budget_usd) if (ledger or generate is None) else None
    out.mkdir(parents=True, exist_ok=True)
    lock, spent, rows = threading.Lock(), [0.0], []
    if generate is None:
        from explainer_engine.imagegen.providers.bfl import BFL
        k = key or _key()

        def generate(name, it, seed):
            r = BFL(out, run=run, key=k).generate(name, prompt(it), model=MODEL, size=SIZE, seed=seed,
                                         extra={"aspect_ratio": ASPECTS[it["kind"]], "safety_tolerance": 2})
            return 0.0 if r.cached else (r.usd_settled if r.usd_settled is not None else r.usd)
    judge = judge or check.score

    def one(i):
        it = every[i]
        for t in range(tries):
            with lock:
                if spent[0] + BFLPRICE > budget_usd:
                    return
                spent[0] += BFLPRICE
            name = i if t == 0 else f"{i}_t{t}"
            try:
                usd = generate(name, it, 1000 + int(i[1:]) + 100000 * t)
            except Exception as e:  # a refused or failed request: recorded and printed, the next seed is tried
                err = {"name": name, "id": i, "kind": it["kind"], "try": t, "verdict": "ERROR",
                       "why": [f"{type(e).__name__}: {str(e)[:200]}"]}
                with lock:
                    spent[0] -= BFLPRICE  # BFL bills only finished pictures (credits checked 2026-10-26)
                    rows.append(err)
                    with (out / "report.jsonl").open("a", encoding="utf-8") as f:
                        f.write(json.dumps(err, ensure_ascii=False) + "\n")
                print(name, "ERROR", err["why"], flush=True)
                time.sleep(5)
                continue
            with lock:
                spent[0] += usd - BFLPRICE
            row = judge([{"name": name, "id": i, "kind": it["kind"], "path": str(out / f"{name}.png")}])[0]
            row.update({"try": t, "usd": usd})
            with lock:
                rows.append(row)
                with (out / "report.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(name, row["verdict"], row.get("why"), flush=True)
            if row["verdict"] != "FAIL":
                return

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, ids))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.training.cast.sheet")
    ap.add_argument("cmd", choices=["list", "check", "draw", "world"])
    ap.add_argument("--budget", type=float, default=0.0)
    ap.add_argument("out", nargs="?")
    ap.add_argument("--ids", default="")
    ap.add_argument("--ref")
    ap.add_argument("--ledger", help=LEDGER_HELP)
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
    if a.yes and not a.ledger:  # N-02: the paid path (--yes) only inside a ledger; the estimate without --yes stays free
        ap.error(f"{a.cmd} --yes needs --ledger <run.json>: {LEDGER_HELP}")
    if a.cmd == "world":
        ids = [x for x in a.ids.split(",") if x] or sorted(items())
        if not a.yes or a.budget <= 0:
            print(f"{len(ids)} pictures, at most ${a.budget}; add --budget and --yes after the creator's OK")
            return 0
        world(a.out, ids, budget_usd=a.budget, ledger=a.ledger)
        return 0
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
