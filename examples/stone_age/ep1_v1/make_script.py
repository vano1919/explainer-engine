"""One-off: Episode 1 as ONE video (creator 2026-10-16): Day 1 + Week 1 (trimmed) + Month 1 + Year 1 + Year 10 + Year 100
+ the comparison with the real record. Built from day1_v7 and week1_v1 plus the new chapters below. Refuses to overwrite an
edited script (--force); afterwards the JSON is edited directly. Pictures of new chapters are painted by reference editing
(engine pod_ref prompts, sent to Gemini this episode only: D-44)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "production_script.json"
if OUT.exists() and "--force" not in sys.argv:
    raise SystemExit("refused: production_script.json exists and is edited directly now (--force to rebuild)")
D1 = json.loads((HERE.parent / "day1_v7" / "production_script.json").read_text())
W1 = json.loads((HERE.parent / "week1_v1" / "production_script.json").read_text())

PUSH = {"kind": "push", "z0": 1.0, "z1": 1.06}


def mo(kind, d=0.05):
    if kind == "pan":
        return {"kind": "pan", "z0": 1.06, "z1": 1.06, "dx": d}
    return dict(PUSH)


LOCALS = ("local hunter-gatherers of about 10,000 BCE: lean weathered adults in hide cloaks and fur, dark hair tied back, bone and "
          "shell ornaments, flint-tipped spears")
P = {}


def pic(pid, refs, heroes, subject, edit, **kw):
    P[pid] = {"id": pid, "engine": "pod_ref", "refs": refs, "heroes": heroes, "shows": [], "subject": subject, "edit": edit, **kw}


pic("w1_log_roll", ["v5_d1-10"], [], "a log rolls loose down the slope as people scatter",
    "Edit the picture: a big log rolls loose down the grassy slope and a crowd of scientists in muddy 1700s to 1900s coats scatter and dive out of its way. Grey overcast sky.")

# ---- Month 1 -------------------------------------------------------------------------------------------------------
pic("m1_valley_kiln", ["v5_d1-01"], [], "the valley a month on: the camp has grown, a pit kiln smokes at the river bank",
    "Edit the picture: the same valley a month later under flat grey overcast daylight. Rows of crude shelters of poles and hides, tiny figures at work, and at the river bank a low mound with a thin plume of smoke, a pit kiln. No sunset glow.")
pic("m1_curie_clay", ["v5_d1-08", "v5_d1-18"], ["curie"], "Curie kneels at the river bank digging grey clay with her hands, mud to the elbows, intent",
    "Edit the picture: the woman in the dark high-collared dress kneels on a river bank digging grey clay out of the bank with her bare hands, mud to her elbows, intent and pleased. Remove the man. Grey overcast daylight.")
pic("m1_straw_clay", ["v5_d1-17"], [], "hands knead grey clay mixed with chopped straw and sand on a flat stone",
    "Edit the picture: two hands in muddy sleeves knead a lump of grey clay mixed with chopped straw and sand on a flat stone, close view, grey daylight.")
pic("m1_pots_cracked", ["v5_d1-07"], [], "a row of clay pots on the ground, every one split by cracks, shards beside them",
    "Edit the picture: remove the wheat and the round stone; a row of crude clay pots stands on flat ground and every one is split by long cracks, broken shards beside them, grey overcast daylight.")
pic("m1_newton_pot", ["v5_d1-06", "v5_d1-36"], ["newton"], "Newton measures a clay pot with a notched stick, frowning, Franklin shaking his head behind",
    "Edit the picture: Isaac Newton in his dark coat and long wig frowns and measures a crude clay pot with a notched stick, absorbed. Remove the other man. Grey overcast daylight.")
pic("m1_pit_kiln", ["v5_d1-21", "v5_d1-19"], [], "a pit kiln: clay pots buried under glowing embers and turf, tiny figures standing round with wooden tongs",
    "Edit the picture: a wide pit in the ground filled with clay pots under glowing orange embers and turf, thin smoke rising, tiny figures in muddy coats stand round it with long wooden poles. Grey overcast sky, cold light, the glow is small and low.")
pic("m1_soup", ["v5_d1-25", "v5_d1-36"], ["snow"], "Snow ladles steaming soup from the first clay pot into a wooden bowl, moved almost to tears",
    "Edit the picture: the pale physician with round spectacles ladles steaming soup out of a clay pot into a wooden bowl held by a grateful man, moved, eyes shining. Steam rising. Remove the bearded man.")
pic("m1_smoke_ridge", ["v5_d1-01"], [], "a thin column of smoke rises from a distant ridge, far from the camp",
    "Edit the picture: the same valley at last light, the camp small in the foreground, and on the far ridge a single thin column of smoke rising that is not theirs. Low last sun, long amber shadows.")
pic("m1_hunters_ridge", ["v5_d1-18", "v5_d1-01"], [], f"{LOCALS} stand on the ridge and look down at the camp, wary and curious",
    f"Edit the picture: a group of six {LOCALS}, stands on a rocky ridge and looks down at the valley camp far below, wary and curious. Low last sun, long amber shadows. Adult proportions.")
pic("m1_franklin_offer", ["v5_d1-41", "v5_d1-18"], ["franklin"], "Franklin holds out a clay pot to wary local hunters with a hopeful smile",
    f"Edit the picture: Benjamin Franklin in his brown frock coat holds out a clay pot with both hands and a hopeful smile to three {LOCALS}, who stand at a distance, wary. Low last sun, long amber shadows. Remove the other man.")
pic("m1_hunter_knock", ["v5_d1-14", "v5_d1-18"], [], "a local hunter knocks on the pot with one knuckle and listens, a half smile",
    f"Edit the picture: a tall {LOCALS}, holds a clay pot up by his ear and knocks on it with one knuckle, listening, a half smile. Franklin's frock-coated shoulder at the edge of the picture. Low last sun.")
pic("m1_first_snow", ["v5_d1-01"], [], "the first snow falls on the camp's shelters and the pit kiln, smoke rising",
    "Edit the picture: the same valley at dusk with the first snow falling, a thin white layer on the shelters and the pit kiln, smoke rising, cold blue light, no people in the foreground.")

# ---- Year 1 --------------------------------------------------------------------------------------------------------
pic("y1_cairns", ["v5_d1-01", "v5_d1-18"], [], "spring meadow: five small stone cairns and a few figures standing with bowed heads",
    "Edit the picture: a green spring meadow at cold dawn with five small stone cairns in a row and a few figures in muddy coats standing round them with bowed heads, melting snow patches, thin mist.")
pic("y1_snow_ledger", ["v5_d1-25", "v5_d1-36"], ["snow"], "Snow writes in a charcoal ledger on a bark slab, grim and exact",
    "Edit the picture: the pale physician with round spectacles sits and writes small columns on a slab of bark with a charcoal stick, grim and exact. Remove the bearded man. Cold dawn light.")
pic("y1_darwin_sow", ["v5_d1-03", "v5_d1-42"], ["darwin"], "Darwin scatters seed on cleared ground, bearded and hopeful",
    "Edit the picture: Charles Darwin, white-bearded in his dark frock coat, walks across a patch of cleared brown ground and scatters seed from his hand, hopeful. Remove the other man. Harsh noon sun, short shadows.")
pic("y1_hill_bare", ["v5_d1-21"], [], "a golden hillside with a big bare stripped patch where the colony has been cutting",
    "Edit the picture: a golden hillside of wild wheat with a huge bare stripped patch of brown stubble in the middle where the colony has been cutting, tiny figures at the edge. Harsh noon sun.")
pic("y1_field_edge", ["v5_d1-19", "v5_d1-21"], [], "a small neat field of green shoots beside the shelters",
    "Edit the picture: beside a row of crude shelters lies a small neat field of bright green wheat shoots in rows, a few figures weeding it. Harsh noon sun, short shadows.")
pic("y1_ears_shatter", ["v5_d1-07"], [], "a ripe wheat ear bursts and its grains fall to the ground",
    "Edit the picture: remove the stone; one ripe golden wheat ear in close view bursts apart and its grains scatter and fall to the ground, harsh noon sun.")
pic("y1_darwin_select", ["v5_d1-03", "v5_d1-42"], ["darwin"], "Darwin holds up a single ear that has held on to its grain, delighted, and drops it in a sack",
    "Edit the picture: Charles Darwin kneels in a wheat field and holds up one ear of wheat that has held on to all its grain, delighted, while an open sack waits beside him. Remove the other man. Harsh noon sun.")
pic("y1_baby", ["v5_d1-08", "v5_d1-18"], ["curie"], "Curie holds a newborn baby wrapped in hide, tender and astonished",
    "Edit the picture: the woman in the dark high-collared dress holds a newborn baby wrapped in a soft hide, tender and astonished, the camp behind her in warm low light. Remove the man.")
pic("y1_school", ["v5_d1-19", "v5_d1-36"], ["franklin"], "an open-air school: Franklin teaches a ring of small children, writing with a stick in the dust",
    "Edit the picture: Benjamin Franklin in his brown frock coat kneels and writes numbers in the dust with a stick, a ring of small children in hide wraps watching, a few scientists also sitting in the ring. Harsh noon sun. Remove the other man.")
pic("y1_kiln_tablets", ["v5_d1-21", "v5_d1-19"], [], "a kiln glowing with flat clay tablets stacked inside, marked with tidy rows of signs",
    "Edit the picture: a low clay kiln with its door open, glowing orange inside, and rows of small flat clay tablets stacked inside, each pressed with tidy rows of signs; two figures in muddy coats watch. Cold dusk light.")
pic("y1_library", ["v5_d1-24"], [], "a shelf of baked clay tablets, the colony's first library",
    "Edit the picture: close view of a rough stone shelf holding rows of baked clay tablets with tidy marks, a little dust, soft warm light. Remove the stick and the puddle.")

# ---- Year 10 -------------------------------------------------------------------------------------------------------
pic("y10_children", ["v5_d1-19", "v5_d1-36"], [], "children aged ten sit reading clay tablets in a row, solemn and a little smug",
    "Edit the picture: a row of ten-year-old children in hide tunics sit reading small clay tablets, solemn and a little smug, a few scientists in muddy coats laughing in the background. Harsh noon sun.")
pic("y10_malachite", ["v5_d1-17"], [], "a hand holds a green lump of malachite ore, a heap of crushed green rock beside it",
    "Edit the picture: a hand in a muddy sleeve holds up a bright green lump of malachite ore, a heap of crushed green rock beside it on a flat stone, harsh noon sun, close view.")
pic("y10_furnace", ["v5_d1-21", "v5_d1-19"], [], "a clay furnace with a hide bellows pumped by two figures, white-hot glow at the mouth",
    "Edit the picture: a squat clay furnace with a hide bellows pumped by two figures in muddy coats, a pipe leading air in, white-hot glow at the furnace mouth, sparks, charcoal heaps, cold dusk light.")
pic("y10_bead", ["v5_d1-24"], [], "a small bright bead of copper in a pair of wooden tongs, held up",
    "Edit the picture: wooden tongs hold up a small bright red-gold bead of copper beside a pile of dark slag, close view, warm light. Remove the stick and the puddle.")
pic("y10_tesla_curie", ["v5_d1-08", "v5_d1-18"], ["curie", "tesla"], "Tesla asks eagerly about electricity, Curie answers with a tired look",
    "Edit the picture: the tall dark-haired man with a narrow moustache points eagerly at a coil of copper wire in his hand, the woman in the dark dress looks at him with a tired, patient stare, arms folded. Harsh noon sun.")
pic("y10_axe_bend", ["v5_d1-07"], [], "a copper axe head bent like a banana next to a chipped stone axe",
    "Edit the picture: remove the wheat and the round stone; a copper axe head bent like a banana lies next to a sharp chipped stone axe on bare ground, harsh noon sun.")
pic("y10_nansen_map", ["v5_d1-14", "v5_d1-31"], ["nansen"], "Nansen studies a scratched map of hills, scowling at a tiny empty mark where tin should be",
    "Edit the picture: Fridtjof Nansen in his heavy wool jacket crouches over a map scratched into the dirt with hills and rivers, scowling and tapping an empty spot with his stick. Remove the pointing and the others. Harsh noon sun.")
pic("y10_iron_hills", ["v5_d1-21"], [], "rust-red and yellow hills of iron ore above the valley",
    "Edit the picture: a hillside of rust-red and yellow rock above the valley, bare and striped, tiny figures with baskets collecting ore, harsh noon sun.")
pic("y10_charcoal", ["v5_d1-19", "v5_d1-21"], [], "giant stacks of charcoal and a hillside stripped of trees around a bloomery furnace",
    "Edit the picture: a smoking clay bloomery furnace surrounded by giant stacks of dark charcoal, and behind it a hillside stripped of its trees, stumps everywhere, tiny figures carrying wood, cold dusk light.")

# ---- Year 100 ------------------------------------------------------------------------------------------------------
pic("y100_village", ["v5_d1-01", "v5_d1-19"], [], "the valley a hundred years on: a village of mud-brick houses, fields, smoke from many kilns",
    "Edit the picture: the same valley a hundred years later in warm low light. A village of rounded mud-brick houses climbs the slope, green fields around it, thin smoke from many kilns, many people at work. Last sun.")
pic("y100_hill", ["v5_d1-01", "v5_d1-18"], [], "a quiet hill with nine tall stone pillars carved with simple figures, villagers laying wheat sheaves",
    "Edit the picture: a quiet green hill with a ring of nine tall stone pillars carved with simple figures, villagers in simple wool tunics laying wheat sheaves at their feet, last sun, long amber shadows.")
pic("y100_wheat", ["v5_d1-21"], [], "tall golden wheat in rows whose ears stand full, women and children harvesting with sickles",
    "Edit the picture: tall golden wheat in neat rows whose ears stand full and heavy, women and children harvesting with small copper-bladed sickles, harsh noon sun.")
pic("y100_kilns", ["v5_d1-19", "v5_d1-21"], [], "a street of mud-brick workshops with a kiln glowing at every door",
    "Edit the picture: a street of mud-brick workshops with a kiln glowing at every door, potters carrying jars, children running, smoke, cold dusk light.")
pic("y100_school", ["v5_d1-24"], [], "a room lined to the ceiling with shelves of clay tablets, a child reading by firelight",
    "Edit the picture: a room lined to the ceiling with shelves of clay tablets, a child sitting on the floor reading one by warm firelight, an old teacher beside her.")
pic("y100_boil", ["v5_d1-12"], [], "children ritually boiling water in a clay pot while a carved figure of a bespectacled man watches",
    "Edit the picture: a small ring of children kneeling round a clay pot of boiling water in a solemn ritual, and behind them a rough wooden carving of a pale thoughtful man with round spectacles. Cold dusk light.")
pic("y100_pillar", ["v5_d1-18", "v5_d1-37"], ["franklin"], "a stone pillar carved with a bald man with round spectacles, a kite, and a coin",
    "Edit the picture: a tall carved stone pillar showing a balding man with round spectacles and a frock coat, a kite and a coin carved beside him, villagers kneeling at its foot. Last sun.")
pic("y100_road", ["v5_d1-01"], [], "a trail of traders carrying clay pots and tablets over the hills to other villages",
    "Edit the picture: a long trail of traders carrying clay pots and tablets on their backs winds over green hills toward distant smoke from other villages, harsh noon sun.")

# ---- Comparison ----------------------------------------------------------------------------------------------------
pic("c_road", ["v5_d1-01"], [], "a long road across the whole picture with stone milestones: pot, furnace, tablet, plough, iron, engine, flask",
    "Edit the picture: a long road winding across the whole picture from the valley to the far horizon, lined with stone milestones carved with a pot, a furnace, a tablet, a plough, an iron blade, a steam engine and a flask. Warm low light.")
pic("c_tiny_crowd", ["v5_d1-01", "v5_d1-18"], [], "a tiny huddle of figures on a vast empty plain under a huge sky",
    "Edit the picture: a tiny huddle of figures in muddy coats on a vast empty plain under a huge sky, the horizon far away, harsh noon sun, enormous sense of scale.")
pic("c_boring_mill", ["v5_d1-19"], [], "an 18th-century ironworks interior where a huge iron cylinder is bored by a rotating bar, sparks and workers",
    "Edit the picture: inside an 18th-century ironworks, a huge iron cylinder lies in a frame while a long rotating boring bar drives into it, sparks flying, sweating workers in waistcoats pulling levers, dark smoky light.")
pic("c_pencil", ["v5_d1-24"], [], "a single pencil on a table with strands of wood, graphite and brass lines leading off the page",
    "Edit the picture: a single pencil lies on a wooden table and from it thin drawn lines lead off to little scenes of a forest, a mine and a rubber tree, warm soft light.")
pic("c_winter_fail", ["v5_d1-43", "v5_d1-14"], ["nansen"], "Nansen alone at the grave cairns in a blizzard, grim",
    "Edit the picture: Fridtjof Nansen in his heavy wool jacket stands alone in a blizzard beside a row of small stone cairns, snow driving sideways, grim and determined. Remove the other man. Cold dusk light.")
pic("c_steam", ["v5_d1-19"], [], "a first atmospheric steam engine pumping at a mine, beam rocking, steam rising",
    "Edit the picture: an early atmospheric steam engine pumping at a mine head, the huge wooden beam rocking, white steam rising, miners watching in awe, grey overcast daylight.")
pic("c_penicillin", ["v5_d1-24"], [], "a petri dish with a ring of clear space around a green mould, a gloved hand holding it up",
    "Edit the picture: close view of a glass petri dish where a green mould blooms and a clear ring surrounds it, a hand holds it up to a window, soft light.")
pic("c_shrug", ["v5_d1-36", "v5_d1-18"], ["franklin", "einstein"], "Franklin and Einstein look at the viewer with a shrug and a smile",
    "Edit the picture: Benjamin Franklin and young Einstein face the viewer side by side with a shrug and a wry smile, Franklin raising one eyebrow, Einstein holding up his reading glasses, the camp behind them in warm low light.")

SEG = []


def seg(sid, beat, light, period, lines, shots, audio=None):
    L = []
    for ln in lines:
        if isinstance(ln, str):
            L.append({"text": ln})
        else:
            t, *rest = ln
            L.append({"text": t, **(rest[0] if rest else {})})
    s = {"id": sid, "period": period, "beat": beat, "light_beat": light, "lines": L, "shots": []}
    for at, typ, pid, *rest in shots:
        sh = {"at": at, "type": typ, "motion": mo("pan" if typ == "A" else "push"), "picture": pid}
        if rest:
            sh.update(rest[0])
        s["shots"].append(sh)
    if audio:
        s["audio"] = audio
    SEG.append(s)


W = lambda **k: k  # noqa: E731

# Month 1 -------------------------------------------------------------------------------------------------------------
seg("M01", "pot", 15, "month1", [
    ("Day thirty.", W(tags=["warmly"], emotion="gentle irony")),
    ("The pot!", W(tags=["amused"], emotion="pride")),
    ("Which is awkward, because the oldest pottery we know of is already eight thousand years old.", W(emphasis=["already"], emotion="dry wit")),
    "In China. Not here. The people living nearby won't have a single pot for another three thousand years.",
    ("So Marie Curie goes looking for clay.", W(emotion="curiosity")),
    "River clay, chopped straw, a little sand.",
    "Why the straw? Because plain clay shrinks as it dries, and then it cracks.",
    ("Seven pots. Seven explosions.", W(tags=["deadpan"], emotion="dry humour")),
    "Newton looks at the pieces. Then he does what Newton does.",
    ("He measures.", W(emphasis=["measures"])),
    "Dry them slowly. Heat them slowly. Bury them in a pit, and cover the pit with glowing wood.",
    ("Eleven days later, one pot holds water.", W(tags=["softly"], emotion="quiet triumph", pause_after=0.5)),
    "And then, at last, there is soup.",
    ("Nobody has ever been so moved by soup.", W(tags=["warmly"], emotion="warm humour")),
], [
    ("Day thirty.", "A", "m1_valley_kiln"),
    ("Which is awkward", "B", "m1_curie_clay"),
    ("So Marie Curie", "B", "m1_curie_clay"),
    ("River clay,", "C", "m1_straw_clay"),
    ("Seven pots.", "C", "m1_pots_cracked"),
    ("Newton looks", "B", "m1_newton_pot"),
    ("Dry them slowly.", "A", "m1_pit_kiln"),
    ("And then, at last,", "B", "m1_soup"),
], {"beds": [{"at": "Day thirty.", "sound": "wind_day"}]})

seg("M02", "neighbours", 16, "month1", [
    ("Day thirty-three.", W(tags=["slowly"], emotion="unease")),
    "A column of smoke rises from the next ridge.",
    ("Not theirs.", W(tags=["whispers"], emotion="held breath", pause_after=0.6)),
    ("Somebody else lives here.", W(tags=["softly"], emotion="realisation")),
    "Hunters have lived in this country for thousands of years. Within a few hundred, people like these will raise the oldest stone temple we know: Göbekli Tepe, not far from here.",
    "There's one small problem. The magic that lets the hundred understand each other doesn't work on anybody else.",
    ("So Franklin tries diplomacy. He holds out a pot.", W(emotion="dry humour")),
    "The hunters look at the pot. They look at Franklin. Then one of them knocks on it, listens, and says something that, in any language, means: how much?",
    ("The first deal in the colony's history: one pot, for a haunch of gazelle.", W(tags=["chuckles"], emotion="dry humour")),
    "And that changes everything. A hundred adults are a camp. A people needs more.",
    ("But winter is nearly here. Will they have a village by spring, or a graveyard?", W(tags=["softly"], emphasis=["graveyard"], emotion="foreboding")),
], [
    ("Day thirty-three.", "A", "m1_smoke_ridge"),
    ("Somebody else", "B", "m1_hunters_ridge"),
    ("There's one small", "B", "m1_hunters_ridge"),
    ("So Franklin tries", "B", "m1_franklin_offer"),
    ("Then one of", "B", "m1_hunter_knock"),
    ("And that changes", "A", "m1_valley_kiln"),
    ("But winter is", "A", "m1_first_snow"),
], {"beds": [{"at": "Day thirty-three.", "sound": "wind_day"}]})

# Year 1 --------------------------------------------------------------------------------------------------------------
seg("Y01", "winter", 19, "year1", [
    ("Spring.", W(tags=["softly"], emotion="relief")),
    ("Not everybody sees it.", W(tags=["slowly"], emotion="grief")),
    "The first winter takes five of the hundred. A fever, a bad tooth, a fall on the ice.",
    "That number is our invention, but not a wild one: hunter-gatherers lose a few adults in every hundred each year.",
    "John Snow writes down the causes in charcoal, on bark.",
    ("And one thing is different from the cave-man winters you've seen. Nobody died of the water.", W(tags=["warmly"], emphasis=["water"], emotion="quiet pride")),
], [
    ("Spring.", "A", "y1_cairns"),
    ("John Snow writes", "B", "y1_snow_ledger"),
    ("And one thing", "A", "y1_cairns"),
], {"beds": [{"at": "Spring.", "sound": "wind_day"}]})

seg("Y02", "wheat", 20, "year1", [
    ("Now it's Darwin's turn.", W(emotion="anticipation")),
    "He clears a patch of ground beside the camp and sows wild einkorn from the seed they saved.",
    ("And here's the twist. Wild wheat is generous.", W(emotion="dry wit")),
    "In the nineteen-sixties, the botanist Jack Harlan cut wild wheat by hand in these same hills, with a stone-bladed sickle. His estimate: a family could gather a year's grain in about three weeks.",
    ("So why farm at all?", W(emphasis=["farm"])),
    "Darwin has the answer. A hundred people can't live on wild wheat in one place. They'd strip the hillside bare in a single season.",
], [
    ("Now it's Darwin's turn.", "B", "y1_darwin_sow"),
    ("In the nineteen-sixties,", "A", "w1_grain_hill"),
    ("So why farm", "B", "y1_darwin_sow"),
    ("Darwin has", "A", "y1_hill_bare"),
])

seg("Y03", "selection", 21, "year1", [
    ("Then Darwin does the cleverest thing anyone does all year.", W(tags=["intrigued"], emotion="intrigue")),
    "Wild wheat has a flaw, from a farmer's point of view. When an ear is ripe, it shatters, and the grain falls to the ground.",
    ("But every so often, one plant holds on to its grain.", W(emphasis=["holds"])),
    "Darwin saves only those. Every harvest. Year after year.",
    "In the real world, say the archaeologists, wheat took a thousand to two thousand years to change like this.",
    "Some computer models say it could happen in twenty to a hundred years, if you choose the seed on purpose.",
    ("Who's right? Nobody knows.", W(tags=["short pause"], emotion="honest doubt")),
], [
    ("Then Darwin does", "B", "y1_darwin_select"),
    ("Wild wheat has", "C", "y1_ears_shatter"),
    ("Darwin saves only", "B", "y1_darwin_select"),
    ("In the real world,", "A", "y1_field_edge"),
])

seg("Y04", "baby", 22, "year1", [
    ("But the biggest event of year one isn't wheat.", W(tags=["softly"], emotion="warmth")),
    ("It's a baby.", W(tags=["warmly"], emotion="wonder", pause_after=0.5)),
    ("And with babies comes a problem nobody planned for.", W(tags=["slowly"], emotion="unease")),
    "A hundred adults can survive a winter. But can they keep every skill alive?",
    "One famous study argues that when rising seas cut off Tasmania, its four thousand people slowly lost bone tools, warm clothing, even fishing. Other researchers disagree.",
    ("A hundred people is a lot smaller than four thousand.", W(emphasis=["smaller"], emotion="dry understatement")),
    "So Franklin calls a meeting. Everyone teaches. Everyone writes.",
], [
    ("But the biggest event", "B", "y1_baby"),
    ("And with babies", "A", "y1_school"),
    ("One famous study", "A", "c_tiny_crowd"),
    ("So Franklin calls", "A", "y1_school"),
])

seg("Y05", "tablets", 23, "year1", [
    ("Writing doesn't exist yet. Not for another sixty-seven hundred years.", W(emphasis=["yet"], emotion="dry wit")),
    "These people brought it with them.",
    "They press signs into wet clay, then bake the tablets in the new kiln. Fire doesn't destroy them. It saves them.",
    ("The colony's first library. Knowledge, backed up.", W(tags=["amused"], emotion="dry humour")),
    "But writing down a recipe isn't the same as cooking it.",
    ("So ten years from now, can they make metal?", W(tags=["intrigued"], emphasis=["metal"], emotion="promise")),
], [
    ("Writing doesn't", "A", "y1_kiln_tablets"),
    ("The colony's first", "C", "y1_library"),
    ("But writing down", "B", "y1_school"),
], {"beds": [{"at": "Writing doesn't", "sound": "ember_crackle"}]})

# Year 10 -------------------------------------------------------------------------------------------------------------
seg("T01", "children", 24, "year10", [
    ("Year ten.", W(tags=["warmly"], emotion="gentle irony")),
    ("The first children are ten years old, and every one of them can read.", W(emotion="pride")),
    "Which makes them the best-educated ten-year-olds on Earth, and the rudest.",
    "The colony is bigger now: about a hundred and thirty people, counting neighbours who married in. That's our estimate.",
    ("And everybody stares at the same problem. Stone tools break.", W(emphasis=["break"], emotion="concern")),
    ("Metal doesn't.", W(tags=["softly"], emotion="longing")),
], [
    ("Year ten.", "A", "y10_children"),
    ("The colony is bigger", "A", "y100_road"),
    ("Metal doesn't.", "A", "y10_children"),
], {"beds": [{"at": "Year ten.", "sound": "wind_day"}]})

seg("T02", "copper", 25, "year10", [
    ("Marie Curie has found a green rock in the next valley.", W(emotion="excitement")),
    "Malachite.",
    "Crush it. Mix it with charcoal. Put it in the hottest kiln they own, and blow air through a hide bellows.",
    ("Hours later the ash breaks open, and there it is: a small red-gold bead of copper.", W(tags=["whispers"], emphasis=["copper"], emotion="held breath")),
    "Near here, people will begin hammering raw lumps of copper into beads within a thousand years or so. Real smelting? That's five thousand years away.",
    ("Then Tesla asks the question nobody wants to hear. So where does the electricity come in?", W(tags=["amused"], emotion="dry humour")),
    ("Not now, Nikola.", W(tags=["deadpan"], emotion="tired patience")),
], [
    ("Marie Curie has", "C", "y10_malachite"),
    ("Crush it.", "A", "y10_furnace"),
    ("Hours later", "C", "y10_bead"),
    ("Then Tesla asks", "B", "y10_tesla_curie"),
], {"beds": [{"at": "Crush it.", "sound": "fire"}]})

seg("T03", "tin", 26, "year10", [
    ("But copper is soft. A copper axe bends where a stone axe would chip.", W(emotion="concern")),
    "Bronze is harder. Bronze is copper plus tin.",
    ("And tin is the problem. It's rare, and there's almost none of it near here.", W(emphasis=["rare"], emotion="foreboding")),
    "Archaeologists still argue about where the ancient Near East found its tin.",
    ("A hundred of the cleverest people in history, defeated by one silvery metal that isn't there.", W(tags=["sighs"], emotion="dry humour")),
], [
    ("But copper is soft.", "C", "y10_axe_bend"),
    ("And tin is", "B", "y10_nansen_map"),
    ("A hundred of the", "B", "y10_nansen_map"),
])

seg("T04", "iron", 27, "year10", [
    ("So Curie suggests skipping bronze. Go straight to iron.", W(emotion="resolve")),
    "Iron ore is everywhere: whole hills the colour of rust.",
    "But iron needs a furnace well over a thousand degrees, and a mountain of charcoal.",
    "In modern experiments, a block of iron under two kilograms swallows about forty kilograms of charcoal.",
    ("A single knife costs a forest.", W(tags=["slowly"], emphasis=["forest"], emotion="foreboding")),
    "Real humans took until about twelve hundred BCE to make iron an everyday metal.",
    ("Can the hundred beat that? Let's see what a century does.", W(tags=["intrigued"], emotion="promise")),
], [
    ("So Curie suggests", "A", "y10_iron_hills"),
    ("But iron needs", "A", "y10_charcoal"),
    ("A single knife", "A", "y10_charcoal"),
], {"beds": [{"at": "But iron needs", "sound": "fire"}]})

# Year 100 ------------------------------------------------------------------------------------------------------------
seg("H01", "gone", 28, "year100", [
    ("Year one hundred.", W(tags=["softly"], emotion="solemn")),
    ("Nobody who arrived on Day One is alive.", W(tags=["slowly"], emphasis=["alive"], emotion="solemn", pause_after=0.6)),
    "Not Newton. Not Curie. Not even the stubborn ones.",
    "How many people live here now? Probably between one and three thousand. If the colony grew three percent a year, it's about nineteen hundred. But growth like that never lasts.",
    ("So what did a hundred geniuses leave behind?", W(tags=["intrigued"], emotion="intrigue")),
], [
    ("Year one hundred.", "A", "y100_village"),
    ("Not Newton.", "A", "y100_hill"),
    ("How many people", "A", "y100_village"),
], {"beds": [{"at": "Year one hundred.", "sound": "wind_day"}]})

seg("H02", "remains", 29, "year100", [
    ("Wheat that holds on to its grain. Almost.", W(emphasis=["almost"], emotion="quiet pride")),
    "Copper tools. A kiln at every door.",
    "A school with a library of four thousand clay tablets.",
    ("And one strange custom. Every child boils their water, and nobody remembers why.", W(tags=["amused"], emphasis=["why"], emotion="warm humour")),
    "It's a rule from the old spirits.",
    "Franklin is now the spirit of thrift. Newton is the grumpy ghost of levers.",
    "And the neighbours? They learned pottery from the colony. The next valley learned it from them.",
    ("Because ideas don't spread by magic. They travel with people who meet.", W(tags=["warmly"], emphasis=["meet"], emotion="wisdom")),
    ("So did the hundred beat history?", W(tags=["intrigued"], emphasis=["history"], emotion="promise")),
], [
    ("Wheat that holds", "A", "y100_wheat"),
    ("A school with", "B", "y100_school"),
    ("And one strange", "B", "y100_boil"),
    ("Franklin is now", "B", "y100_pillar"),
    ("And the neighbours?", "A", "y100_road"),
], {"beds": [{"at": "Wheat that holds", "sound": "wind_day"}]})

# Comparison ----------------------------------------------------------------------------------------------------------
seg("K01", "record", 30, "compare", [
    ("Now let's check the real record.", W(tags=["warmly"], emotion="curiosity")),
    "Wheat that no longer drops its grain: a thousand to two thousand years.",
    "Writing: six thousand seven hundred years from this valley.",
    "Copper smelting: five thousand.",
    "Everyday iron: eight thousand eight hundred.",
    ("The hundred did writing on Day One. Smelting by year ten.", W(emphasis=["Day"], emotion="dry wit")),
    ("So yes, knowledge is a time machine. For discoveries.", W(tags=["thoughtful"], emphasis=["discoveries"], emotion="wisdom")),
    "But discovery was never the only cost.",
], [
    ("Now let's check", "A", "c_road"),
    ("Writing:", "A", "c_road"),
    ("The hundred did", "B", "y10_tesla_curie"),
    ("But discovery", "A", "c_road"),
], {"beds": [{"at": "Now let's check", "sound": "wind_day"}]})

seg("K02", "bottlenecks", 31, "compare", [
    ("People.", W(emotion="gravity")),
    "In ten thousand BCE the whole planet holds about four million. By eighteen hundred, nearly a billion.",
    "More people, more ideas: the economist Michael Kremer built a famous model of exactly that.",
    ("Materials. No tin.", W(emphasis=["tin"])),
    "Fuel. Forty kilograms of charcoal for one small block of iron.",
    "And tools that make tools. James Watt waited years for someone who could bore a steam cylinder true. John Wilkinson finally did it in seventeen seventy-four.",
    ("Then there's trade. A famous essay called I, Pencil points out that no single person on Earth knows how to make a pencil.", W(tags=["amused"], emotion="dry humour")),
    "The wood, the graphite, the rubber, the brass: all from people who never meet.",
    ("A hundred geniuses is not a civilization.", W(tags=["slowly"], emphasis=["not"], emotion="gravity")),
], [
    ("People.", "A", "c_tiny_crowd"),
    ("In ten thousand", "A", "c_tiny_crowd"),
    ("And tools that", "A", "c_boring_mill"),
    ("Then there's trade.", "C", "c_pencil"),
    ("A hundred geniuses", "A", "c_tiny_crowd"),
])

seg("K03", "verdict", 32, "compare", [
    ("So here's our verdict.", W(tags=["warmly"], emotion="resolve")),
    "Early on, the hundred beat history. Farming, writing, metal: in centuries, not millennia. We'd bet on that.",
    ("Then they hit the wall.", W(emphasis=["wall"])),
    "They could fail three ways. A bad winter. A plague. Or the Tasmania problem, skills dying faster than children can learn them.",
    "Or they could win in a quieter way. Shortcut the first ten thousand years, and the world reaches the steam engine in maybe half the time. That's a guess, not a fact.",
    "Real history took eleven thousand seven hundred years to get from this valley to the first working steam engine, and nearly twelve thousand to penicillin.",
], [
    ("So here's our verdict.", "A", "c_road"),
    ("They could fail", "B", "c_winter_fail"),
    ("Or they could win", "A", "c_steam"),
    ("Real history took", "C", "c_penicillin"),
])

seg("K04", "end", 33, "compare", [
    ("Which would you bet on? The hundred, or the winter?", W(tags=["intrigued"], emphasis=["winter"], emotion="playful")),
    ("Tell me below.", W(tags=["warmly"], emotion="warm")),
    ("And tell me which two worlds should collide next.", W(tags=["warmly"], emphasis=["next"], emotion="promise")),
], [
    ("Which would you", "B", "c_shrug"),
])

# ---- assemble ------------------------------------------------------------------------------------------------------
doc = copy.deepcopy(D1)
doc["episode"] = {"id": "stone_age_ep1", "title": "100 greatest scientists dropped into the Stone Age", "fps": 30,
                  "size": [1920, 1080], "grade": "prehistory"}
doc["picture_dirs"] = ["pictures", "../day1_v7/pictures"]
doc["sound_dirs"] = ["../day1_v7/sounds", "../week1_v1/sounds", "sounds"]
doc["look"] = {"style_refs": ["v5_d1-36", "v5_d1-18", "v5_d1-42"], "default_engine": "pod_ref"}

lib = copy.deepcopy(D1["library"])
for k, v in W1["library"].items():
    if k in lib:
        lib[k]["heroes"] = sorted(set(lib[k].get("heroes", [])) | set(v.get("heroes", [])))
    else:
        lib[k] = v

day1 = copy.deepcopy(D1["segments"])
for s in day1:
    s["period"] = "day1"

# Week 1: inline pictures become library entries (so shots can be dropped or re-pointed freely), then the trim
w1 = copy.deepcopy(W1["segments"])
for s in w1:
    for sh in s["shots"]:
        pc = sh["picture"]
        if isinstance(pc, dict):
            lib[pc["id"]] = {k: v for k, v in pc.items() if k not in ("prompt", "first_use", "uses", "source")}
            sh["picture"] = pc["id"]
for pid, pc in P.items():
    lib[pid] = pc

DROP_LINES = {"Nansen runs the sum again. Hoping it changes.", "It doesn't.", "Well. They're alive.", "Hmm.", "Golden, free and absolutely everywhere.",
              "And grinding it takes even longer than cutting it.", "Then comes the knapping.", "And a great many bandaged fingers.",
              "Levers. Rollers. A sledge. A grooved pulley that turns a pull the other way.",
              "Eight people on a rope, a log on the pulley, everybody pulling together.", "A charcoal filter makes the water clearer.",
              "Not safer.", "Only boiling does that.", "They're alive. But only just ahead.", "Oh, that's clever."}
EDIT = {  # (old segment, shot 'at') -> None to drop, or a dict of changes
    ("S01", "But scientists"): None,
    ("S02", "Every."): None, ("S02", "Hoping it"): None, ("S02", "And grinding"): None,
    ("S03", "Nobody, except"): {"picture": "w1_darwin_nodule"}, ("S03", "He started"): None,
    ("S03", "Newton hits"): {"picture": "w1_newton_flint"}, ("S03", "Then wet sinew"): None, ("S03", "Oh, that's"): None,
    ("S04", "Newton and Franklin"): {"picture": "w1_franklin_newton_lever"}, ("S04", "Levers."): None, ("S04", "The problem?"): None,
    ("S04", "SNAP."): {"picture": "w1_log_roll", "type": "A"}, ("S04", "Materials are"): None,
    ("S05", "Hiss."): None, ("S05", "It smells awful."): None, ("S05", "A charcoal filter"): None,
    ("S06", "Two people"): None, ("S06", "Next:"): {"at": "And a month"}, ("S06", "They're alive."): None,
}
LINE_EDIT = {
    "But there's no pot.": ["But there's no pot.", {"text": "Day one promised one. Day one was optimistic.", "tags": ["deadpan"], "emotion": "dry humour"}],
    "Next: Month One. And somebody finally invents the POT.": [
        {"text": "And a month from now?", "tags": ["softly", "intrigued"], "emotion": "promise"},
        {"text": "Somebody finally invents the POT.", "tags": ["amused"], "emphasis": ["POT"], "emotion": "dry humour"}],
}
MAP = {"S01": "W01", "S02": "W02", "S03": "W03", "S04": "W04", "S05": "W05", "S06": "W06"}
for s in w1:
    old = s["id"]
    lines = []
    for ln in s["lines"]:
        if ln["text"] in DROP_LINES:
            continue
        if ln["text"] in LINE_EDIT:
            for x in LINE_EDIT[ln["text"]]:
                lines.append(ln if x == ln["text"] else x)
        else:
            lines.append(ln)
    s["lines"] = lines
    shots = []
    for sh in s["shots"]:
        key = (old, sh["at"])
        if key in EDIT:
            if EDIT[key] is None:
                continue
            sh.update(EDIT[key])
        shots.append(sh)
    s["shots"] = shots
    s["id"], s["period"], s["light_beat"] = MAP[old], "week1", s["light_beat"] + 8

segments = day1 + w1 + SEG
for n, s in enumerate(segments, 1):
    s["id"] = f"S{n:02d}"
doc["segments"] = segments
doc["library"] = lib
doc["cast"] = {**D1["cast"], **W1["cast"]}

arc = list(D1["world"]["day_arc"])
for st in W1["world"]["day_arc"]:
    arc.append({"beat": st["beat"] + 8, "light": st["light"]})
arc += [{"beat": 15, "light": "overcast_day"}, {"beat": 16, "light": "last_sun"}, {"beat": 17, "light": "overcast_day"},
        {"beat": 19, "light": "cold_dawn"}, {"beat": 20, "light": "harsh_noon"}, {"beat": 22, "light": "last_sun"},
        {"beat": 23, "light": "storm_dusk"}, {"beat": 24, "light": "harsh_noon"}, {"beat": 27, "light": "storm_dusk"},
        {"beat": 28, "light": "last_sun"}, {"beat": 30, "light": "harsh_noon"}]
doc["world"] = dict(D1["world"], topic="100 greatest scientists dropped into the Stone Age", day_arc=arc)
doc["story"] = D1["story"]
doc["music"] = D1["music"]
doc["periods"] = [
    {"id": "day1", "question": "Can they survive the first night?", "bottleneck": "fire and warmth",
     "tone": {"drama": 0.35, "humour": 0.25, "doubt": 0.4}},
    {"id": "week1", "question": "Can knowledge replace calluses?", "bottleneck": "food, tools and clean water",
     "tone": {"drama": 0.35, "humour": 0.25, "doubt": 0.4}},
    {"id": "month1", "question": "Will they have a village by spring?", "bottleneck": "pots, neighbours and winter",
     "tone": {"drama": 0.4, "humour": 0.25, "doubt": 0.35}},
    {"id": "year1", "question": "Can they keep their skills alive?", "bottleneck": "people and teaching",
     "tone": {"drama": 0.4, "humour": 0.15, "doubt": 0.45}},
    {"id": "year10", "question": "Can they make metal?", "bottleneck": "tin, fuel and furnaces",
     "tone": {"drama": 0.35, "humour": 0.2, "doubt": 0.45}},
    {"id": "year100", "question": "What did they leave behind?", "bottleneck": "population and contact",
     "tone": {"drama": 0.45, "humour": 0.15, "doubt": 0.4}},
    {"id": "compare", "question": "Did they beat real history?", "bottleneck": "people, materials, tools and trade",
     "tone": {"drama": 0.3, "humour": 0.15, "doubt": 0.55}}]
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(segments), "segments,", sum(len(s["shots"]) for s in segments), "shots,", len(P), "new pictures defined")
