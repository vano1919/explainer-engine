"""One-off: Week 1 (the second part of episode 1) -> a D-43 production script. Written for the same narrator and the same
drawn world as Day 1 (day1_v7). Refuses to overwrite an edited script (--force); from then on the JSON is edited directly."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "production_script.json"
if OUT.exists() and "--force" not in sys.argv:
    raise SystemExit("refused: production_script.json exists and is edited directly now (--force to rebuild)")
day1 = json.loads((HERE.parent / "day1_v7" / "production_script.json").read_text())

STYLE_TAIL = " Same painted graphic-novel hand as the reference."
PUSH, PAN = ("push", 1.0, 1.06), ("pan", 1.06, 1.06)


def mo(kind, d=0.05):
    if kind == "pan":
        return {"kind": "pan", "z0": 1.06, "z1": 1.06, "dx": d}
    return {"kind": "push", "z0": 1.0, "z1": 1.06}


# pictures: id -> (refs, heroes, subject, edit)
P = {}


def pic(pid, refs, heroes, subject, edit, **kw):
    P[pid] = {"id": pid, "engine": "pod_ref", "refs": refs, "heroes": heroes, "shows": [], "subject": subject, "edit": edit, **kw}


pic("w1_camp_wide", ["v5_d1-01"], [], "the same valley one week on: a row of crude pole-and-hide shelters, small cookfires, tiny figures at work",
    "Edit the picture: the same valley one week later under flat grey overcast daylight. Along the slope stands a row of crude shelters of poles and hides, thin smoke from small cookfires, many tiny figures in muddy coats walking and working. No sunset glow.")
pic("w1_franklin_bark", ["v5_d1-02"], ["franklin"], "Franklin crouches with a flat slab of bark and a charcoal stick, tallying, worried",
    "Edit the picture: Benjamin Franklin crouches in the camp and counts on a flat slab of bark with a charcoal stick, mouth pursed, brow furrowed. His hands are busy, not on his head. The camp of shelters and small fires behind him.")
pic("w1_newton_flint", ["v5_d1-06"], ["newton", "einstein"], "Newton holds a flint upside down while Einstein squints at it, both baffled",
    "Edit the picture: Isaac Newton holds a lump of flint upside down and turns it, frowning. Einstein beside him leans in and squints at it, baffled, one eyebrow raised. Both sit on the same rocks, no hands on heads.")
pic("w1_testing_crowd", ["v5_d1-12"], [], "scientists crouch around little heaps of sticks, stones and grass, each examining one intently",
    "Edit the picture: many men and women in muddy 1700s to 1900s coats crouch around small separate heaps of sticks, stones, clay and grass, each one examining a single object very closely, curious rather than scared. No fires in the middle of the picture.")
pic("w1_darwin_grain", ["v5_d1-04"], ["darwin"], "Darwin holds a pinch of wild grain up to the light: scientists test, they do not guess",
    "Edit the picture: Charles Darwin holds up a small pinch of wild wheat grains between finger and thumb and studies them closely, curious. Behind him the camp of shelters, small fires, grey overcast sky.")
pic("w1_grain_hill", ["v5_d1-21"], [], "golden hillside of wild einkorn with a long line of tiny bent figures cutting it",
    "Edit the picture: a golden hillside covered with wild wheat. A long line of tiny bent figures in muddy coats cuts the grain with small stone sickles, heading across the slope. Grey overcast sky, river far below.")
pic("w1_grain_ears", ["v5_d1-07"], [], "ripe ears of wild einkorn, a flint sickle blade beside them",
    "Edit the picture: remove the round stone; show a bundle of golden wild wheat ears lying in the dirt next to a small flint sickle blade with a sharp edge. Grey daylight.")
pic("w1_wallace_sickle", ["v5_d1-22"], ["wallace"], "Wallace cuts a fistful of grain with a flint sickle, sweating, pleased then puzzled",
    "Edit the picture: Alfred Russel Wallace, bearded in his field jacket, stands in tall golden wild wheat and cuts a fistful with a short flint-bladed sickle, sweating, pleased then puzzled. Remove the waterfall and the stream; a hillside of wheat behind him.")
pic("w1_grain_palms", ["v5_d1-17"], [], "lunch: two cupped palms hold a small heap of golden grain",
    "Edit the picture: two hands in muddy sleeves held cupped and open, holding a small heap of golden wheat grains. Blurred golden hillside behind them.")
pic("w1_nansen_sum", ["v5_d1-14"], ["nansen"], "Nansen scratches big numbers in the dirt with a stick, then stares at them appalled",
    "Edit the picture: Fridtjof Nansen crouches and scratches large numbers in the dirt with a stick, then stares at the sum, appalled, mouth open. Remove the pointing arm and the campfire group behind him; grassland and camp in the distance.")
pic("w1_quern_hand", ["v5_d1-24"], [], "a hand pushes a round grinding stone along a flat saddle quern, a small heap of flour",
    "Edit the picture: a hand in a muddy sleeve pushes a rounded stone back and forth over a flat stone slab, a small heap of pale flour beside it, grey daylight, no stick and no puddle.")
pic("w1_grinders_rows", ["v5_d1-19"], [], "rows of kneeling figures grinding grain at flat stones, a third of the colony",
    "Edit the picture: instead of a circle, many kneeling figures in muddy coats sit in long rows grinding grain on flat stones; fine pale dust rises, small cookfires between the rows. Grey overcast sky.")
pic("w1_limestone_climbers", ["v5_d1-21"], [], "a limestone outcrop above the valley with white flint nodules in the rock face and two tiny climbers",
    "Edit the picture: a steep pale limestone outcrop above the valley, rows of white rounded flint nodules in the rock face, two tiny climbers in muddy coats working at it with sticks. Grey overcast sky.")
pic("w1_darwin_nodule", ["v5_d1-04"], ["darwin"], "Darwin holds a white flint nodule up at a limestone face, delighted",
    "Edit the picture: Charles Darwin stands at a pale limestone rock face and holds up a rounded white flint nodule, delighted, eyes bright. Remove the fire and the crowd; rocky hillside behind him.")
pic("w1_knap_hands", ["v5_d1-24"], [], "hands strike a flint with a hammerstone, flakes flying",
    "Edit the picture: two hands in muddy sleeves strike a flint core with a rounded hammerstone, sharp flakes flying off in the grey light, no stick and no puddle.")
pic("w1_newton_cut", ["v5_d1-06"], ["newton"], "Newton sits on a rock sucking his bleeding finger, scowling at a flint flake",
    "Edit the picture: Isaac Newton sits alone on a rock, scowling at a sharp flint flake in one hand while he sucks the bleeding finger of the other. Remove the other man; the long grassland behind him.")
pic("w1_knap_floor", ["v5_d1-12"], [], "many scientists knap flint on the ground among heaps of flakes, fingers bandaged",
    "Edit the picture: many men and women in muddy coats sit on the ground knapping flint, heaps of sharp flakes, scrapers and crude hand axes beside them, many fingers wrapped in rag bandages. A few small fires.")
pic("w1_axe_head", ["v5_d1-07"], [], "a flint axe head lashed to a wooden handle, resin glistening",
    "Edit the picture: a flint axe head lashed to a wooden handle with thin dark strips of sinew, dark glossy resin around the joint, lying on the ground in grey light. Remove the wheat and the round stone.")
pic("w1_einstein_resin", ["v5_d1-20"], ["einstein"], "Einstein smears pine resin mixed with charcoal on a stone head, tongue out, concentrating",
    "Edit the picture: young Einstein sits and smears a black sticky paste of pine resin and charcoal onto a flint axe head with a small stick, tongue poking out in concentration. Remove the other man.")
pic("w1_log_yard", ["v5_d1-21"], [], "a log yard at the edge of camp: rollers, logs, a sledge, small teams",
    "Edit the picture: a log yard at the edge of the camp, long poles and logs lying on round rollers, a simple wooden sledge, small teams of figures in muddy coats shifting loads. Grey overcast sky.")
pic("w1_franklin_newton_lever", ["v5_d1-18"], ["franklin", "newton"], "Franklin and Newton test a long lever under a big stone",
    "Edit the picture: Benjamin Franklin and Isaac Newton heave on a long wooden pole used as a lever under a large stone, Franklin red in the face, Newton calm and pointing at the pivot. No fire.")
pic("w1_tesla_sketch", ["v5_d1-08"], ["curie", "tesla"], "Tesla sketches a grand machine in the dirt while Curie looks doubtful",
    "Edit the picture: the tall dark-haired man with a moustache crouches and sketches a huge machine in the dirt with a stick, eager and proud, while the woman in the dark dress stands over it with her arms folded, doubtful.")
pic("w1_haul_pull", ["v5_d1-21"], [], "eight people haul on a rope over a wooden pulley lifting a log",
    "Edit the picture: eight people in muddy coats haul on a rope that runs over a wooden pulley hanging from a tripod of poles, lifting a big log, everyone straining. Grey sky.")
pic("w1_pin_snap", ["v5_d1-24"], [], "a wooden pin snaps in a pulley block",
    "Edit the picture: close view of a wooden pulley block with a grooved wheel where the wooden pin has snapped in two, splinters flying, a taut rope whipping away. Grey daylight.")
pic("w1_log_roll", ["v5_d1-10"], [], "a log rolls loose down the slope as people scatter",
    "Edit the picture: a big log rolls loose down the grassy slope and a crowd of scientists in muddy coats scatter and dive out of its way. Grey overcast sky.")
pic("w1_franklin_dust", ["v5_d1-02"], ["franklin"], "Franklin lies on his back in the dust, spectacles crooked, a log just past his feet",
    "Edit the picture: Benjamin Franklin lies flat on his back in the dust, spectacles crooked on his nose, a thick log lying right next to his feet, dazed. Camp behind him.")
pic("w1_snow_rule", ["v5_d1-25"], ["snow", "wallace"], "Snow points at a muddy river pool: boil it; thirsty Wallace objects",
    "Edit the picture: the pale physician with round spectacles points at the muddy river pool and shakes his head, the bearded man in the field jacket points back at the water, both arguing. No tents or crates.")
pic("w1_pit_steam", ["v5_d1-12"], [], "a hide-lined pit in the ground with steam rising, tiny figures round it",
    "Edit the picture: a round pit in the ground lined with animal hide, filled with water, thick steam rising from it, tiny figures in muddy coats crouch round it with wooden tongs. A small fire at the side.")
pic("w1_stone_steam", ["v5_d1-24"], [], "a glowing stone dropped into water, a burst of steam",
    "Edit the picture: a glowing red-hot stone held in wooden tongs drops into water in a hide-lined pit, a big burst of white steam, no stick.")
pic("w1_cobble_crack", ["v5_d1-07"], [], "a river cobble cracks apart in the fire, fragments flying",
    "Edit the picture: a round river cobble lies in glowing embers and bursts apart, sharp fragments flying outward, sparks, grey daylight, remove the wheat.")
pic("w1_franklin_cuts", ["v5_d1-02"], ["franklin"], "Franklin picks stone splinters out of his coat and cheek, wincing",
    "Edit the picture: Benjamin Franklin sits and picks tiny stone splinters out of his coat sleeve, small cuts on his cheek, wincing, one hand up near his face. Camp behind him.")
pic("w1_curie_soap", ["v5_d1-08"], ["curie"], "Curie stirs a pot of fat and wood-ash lye, pinching her nose",
    "Edit the picture: the woman in the dark dress stirs a bubbling pit of animal fat and grey wood ash with a long stick, pinching her nose, grimacing. Remove the man.")
pic("w1_camp_night", ["v5_d1-19"], [], "the camp at night: shelters in a row, small fires, a few figures sit up",
    "Edit the picture: the camp at night under a starry sky, a row of crude shelters of poles and hides, small fires, a few figures sitting up awake. Remove the stone and the circle.")
pic("w1_wrist_hand", ["v5_d1-17"], [], "a bandaged wrist rests on a knee in the firelight",
    "Edit the picture: a single hand with a wrist wrapped in a rag bandage resting on a knee in warm firelight, close view.")
pic("w1_nansen_watch", ["v5_d1-14"], ["nansen"], "Nansen stands watch looking toward the dark valley, worried",
    "Edit the picture: Fridtjof Nansen stands at the edge of the camp at dusk, arms crossed, looking out toward the dark valley, worried. Remove the pointing and the group behind him; a row of shelters far behind.")
pic("w1_valley_dusk", ["v5_d1-01"], [], "the valley at last light, the camp small in the distance, a cold wind coming",
    "Edit the picture: the same valley at last light seen from the hill, the camp tiny and orange-lit in the distance, grey clouds rolling in from the north, no figures in the foreground.")
pic("w1_tally_hand", ["v5_d1-23"], [], "a hand marks charcoal tallies on a bark slab: one column full, the other nearly empty",
    "Edit the picture: close view of a hand in a muddy sleeve holding a charcoal stick over a flat slab of bark. On the bark two columns of charcoal tally marks: the left column long, the right column only four marks. Grey daylight.")
pic("w1_sinew_hands", ["v5_d1-17"], [], "hands pull wet sinew tight around the joint of a stone axe head and a handle",
    "Edit the picture: two hands in muddy sleeves pull a wet strip of sinew tight around the joint of a stone axe head and a wooden handle, close view.")
pic("w1_peg_hand", ["v5_d1-17"], [], "a hand holds a small wooden peg, the only axle they can make",
    "Edit the picture: one hand in a muddy sleeve holds up a small roughly carved wooden peg; the other hand is out of frame. Blurred camp behind.")
pic("w1_sick_figure", ["v5_d1-12"], [], "a sick figure lies wrapped in hide while a worried friend kneels beside, a muddy water cup between them",
    "Edit the picture: a pale sick man lies wrapped in an animal hide on the ground, a worried woman in a muddy dress kneels at his side holding a wooden cup of cloudy water, small fires and shelters behind them, grey daylight.")
pic("w1_snow_filter", ["v5_d1-25"], ["snow"], "Snow holds up a cup of charcoal-filtered water: clearer, not safer",
    "Edit the picture: the pale physician with round spectacles holds up a wooden cup of clear water and shakes his head slowly. Behind him a hide-lined pit and a pile of black charcoal. Remove the bearded man and the tents.")
pic("w1_wash_hands", ["v5_d1-17"], [], "hands lather with grey soap suds in a wooden trough",
    "Edit the picture: two hands in rolled-up muddy sleeves wash in a wooden trough of water with grey soap suds, close view.")

pic("w1_frost_grass", ["v5_d1-07"], [], "a winter is coming: the first frost on blades of grass, a thin white rim on everything",
    "Edit the picture: remove the wheat and the stones; a close view of dry grass blades at dawn, each rimmed with white frost, cold blue light, the first hard frost.")

SEG = []


def seg(sid, beat, light, lines, shots, audio=None):
    L = []
    for ln in lines:
        if isinstance(ln, str):
            L.append({"text": ln})
        else:
            t, *rest = ln
            L.append({"text": t, **(rest[0] if rest else {})})
    s = {"id": sid, "beat": beat, "light_beat": light, "lines": L, "shots": []}
    for at, typ, pid, *rest in shots:
        sh = {"at": at, "type": typ, "motion": mo("pan" if typ == "A" else "push"), "picture": pid}
        if rest:
            sh.update(rest[0])
        s["shots"].append(sh)
    if audio:
        s["audio"] = audio
    SEG.append(s)


seg("S01", "hook", 1, [
    ("Could a hundred of history's greatest minds survive a week of this?", {"tags": ["softly", "intrigued"], "emphasis": ["week"], "emotion": "intrigue"}),
    ("Day seven.", {"tags": ["warmly"], "emotion": "gentle irony"}),
    ("Well. They're alive.", {"tags": ["deadpan"], "emotion": "dry humour"}),
    "Franklin runs a census.",
    "On bark. With charcoal.",
    "Column one: who has done this before?",
    ("Six names.", {"emotion": "wry", "pause_after": 0.5}),
    "Column two: who has ever chipped a flint?",
    ("Four.", {"tags": ["short pause"], "emotion": "deadpan", "pause_after": 0.5}),
    ("Everybody else knows exactly WHY things work.", {"emphasis": ["why"], "emotion": "dry wit"}),
    "They've just never done any of them.",
    ("Hmm.", {"tags": ["thoughtful"], "emotion": "musing", "pause_after": 0.6}),
    "Ninety brilliant theories, and no calluses.",
    ("But scientists have one superpower.", {"tags": ["intrigued"], "emotion": "curiosity"}),
    ("They don't guess. They TEST.", {"emphasis": ["test"], "emotion": "conviction"}),
    ("And the first test is lunch.", {"tags": ["slowly"], "emotion": "foreboding", "pause_after": 0.5}),
], [("Could a hundred", "A", "w1_camp_wide"), ("Franklin runs", "B", "w1_franklin_bark", {"heroes_ok": True}),
    ("Column one:", "C", "w1_tally_hand", {"insert": True}),
    ("Column two:", "B", "w1_franklin_bark", {"heroes_ok": True}),
    ("Everybody else", "B", "w1_newton_flint", {"heroes_ok": True}), ("Ninety brilliant", "A", "w1_testing_crowd"),
    ("But scientists", "B", "w1_darwin_grain", {"heroes_ok": True})],
    {"beds": [{"at": "Could a hundred", "sound": "wind_day"}]})

seg("S02", "grain", 2, [
    ("Because a hundred adults need about two hundred and fifty thousand calories.", {"tags": ["warmly"], "emotion": "matter-of-fact"}),
    ("Every. Day.", {"emphasis": ["day"], "emotion": "dry humour"}),
    "Luckily, wild einkorn grows right there on the hillside.",
    ("Golden, free and absolutely everywhere.", {"emotion": "delight"}),
    "So Wallace picks up a flint sickle and starts cutting.",
    ("About two kilograms an hour.", {"tags": ["deadpan"], "emphasis": ["hour"], "emotion": "dry humour"}),
    ("Nansen does the sum.", {"tags": ["slowly"], "emotion": "dread"}),
    "To feed everyone, that's seventy-five kilograms of grain. A day.",
    ("And grinding it takes even longer than cutting it.", {"emphasis": ["longer"], "emotion": "dismay"}),
    "By the end of the week, a third of the colony does nothing but grain.",
    ("Nansen runs the sum again. Hoping it changes.", {"tags": ["amused"], "emotion": "dry humour", "pause_after": 0.4}),
    ("It doesn't.", {"emotion": "deadpan", "pause_after": 0.6}),
    ("And cutting grain needs sharp stone. So who knows stone?", {"tags": ["intrigued"], "emphasis": ["stone"], "emotion": "open loop"}),
], [("Because a hundred", "A", "w1_camp_wide"), ("Every.", "C", "w1_grain_palms", {"insert": True}),
    ("Luckily, wild", "A", "w1_grain_hill"), ("So Wallace", "B", "w1_wallace_sickle", {"heroes_ok": True}), ("Nansen does", "B", "w1_nansen_sum", {"heroes_ok": True}), ("And grinding", "C", "w1_quern_hand", {"insert": True}),
    ("By the end", "A", "w1_grinders_rows"), ("Hoping it", "C", "w1_grain_ears", {"insert": True})],
    {"beds": [{"at": "Because a hundred", "sound": "wind_day"}]})

seg("S03", "stone", 3, [
    ("Nobody, except Darwin. He started out as a geologist, and he spots white lumps in the limestone.", {"tags": ["warmly"], "emotion": "discovery"}),
    ("Flint!", {"emotion": "delight", "pause_after": 0.5}),
    "Then comes the knapping.",
    ("Newton hits a flint. The flint wins.", {"tags": ["amused"], "emphasis": ["wins"], "emotion": "dry humour"}),
    "By day four, they have a heap of flakes, scrapers and crude axes.",
    ("And a great many bandaged fingers.", {"emotion": "wry"}),
    ("But the real leap is hafting.", {"tags": ["intrigued"], "emphasis": ["hafting"], "emotion": "wonder"}),
    "Einstein mixes pine resin with charcoal, and it turns into glue.",
    ("Then wet sinew is wrapped around the joint. As it dries, it SHRINKS, and the head locks tight.", {"emphasis": ["shrinks"], "emotion": "quiet awe"}),
    ("Oh, that's clever.", {"tags": ["softly"], "emotion": "wonder", "pause_after": 0.7}),
    ("Now they have axes. Which means somebody can finally build something.", {"tags": ["intrigued"], "emphasis": ["build"], "emotion": "open loop"}),
], [("Nobody, except", "A", "w1_limestone_climbers"), ("He started", "B", "w1_darwin_nodule", {"heroes_ok": True}),
    ("Newton hits", "B", "w1_newton_cut", {"heroes_ok": True}),
    ("By day four,", "A", "w1_knap_floor"), ("But the real", "C", "w1_axe_head", {"insert": True}),
    ("Einstein mixes", "B", "w1_einstein_resin", {"heroes_ok": True}), ("Then wet sinew", "C", "w1_sinew_hands", {"insert": True}), ("Oh, that's", "C", "w1_axe_head", {"insert": True})],
    {"sfx": [{"at": "Flint!", "sound": "glass_glint", "gain_db": -20, "max_s": 1.0}]})

seg("S04", "machines", 4, [
    ("Newton and Franklin design only what wood and stone allow.", {"tags": ["warmly"], "emotion": "gentle irony"}),
    "Levers. Rollers. A sledge. A grooved pulley that turns a pull the other way.",
    ("Tesla sketches something much grander.", {"tags": ["amused"], "emotion": "dry humour"}),
    "Curie looks at it. Then at the pile of logs. Then at him.",
    ("The problem? There is no metal. Not for a pin, not for an axle. Only wood.", {"tags": ["softly"], "emphasis": ["wood"], "emotion": "concern"}),
    ("They try anyway.", {"tags": ["suspenseful"], "emotion": "tension"}),
    "Eight people on a rope, a log on the pulley, everybody pulling together.",
    ("SNAP.", {"emotion": "shock", "pause_after": 0.4}),
    ("The wooden pin breaks. The log rolls. Everybody dives.", {"tags": ["short pause"], "emphasis": ["dives"], "emotion": "chaos"}),
    ("Franklin is, technically, still alive.", {"tags": ["deadpan"], "emotion": "dry humour", "pause_after": 0.6}),
    ("Design is easy. Materials are HARD.", {"emphasis": ["hard"], "tags": ["thoughtful"], "emotion": "wisdom"}),
    ("And tonight there's an even bigger problem. The water is making people sick.", {"tags": ["slowly"], "emphasis": ["sick"], "emotion": "foreboding"}),
], [("Newton and Franklin", "A", "w1_log_yard"), ("Levers.", "B", "w1_franklin_newton_lever", {"heroes_ok": True}),
    ("Tesla sketches", "B", "w1_tesla_sketch", {"heroes_ok": True}), ("The problem?", "C", "w1_peg_hand", {"insert": True}), ("They try", "A", "w1_haul_pull"),
    ("SNAP.", "C", "w1_pin_snap", {"insert": True}), ("Franklin is,", "B", "w1_franklin_dust", {"heroes_ok": True}),
    ("Materials are", "A", "w1_sick_figure")],
    {"sfx": [{"at": "SNAP.", "sound": "wood_snap", "gain_db": -14, "max_s": 0.8}]})

seg("S05", "water", 5, [
    ("John Snow has one rule: boil it.", {"tags": ["warmly"], "emotion": "conviction"}),
    ("But there's no pot.", {"tags": ["deadpan"], "emotion": "dry humour"}),
    "So they dig a pit, line it with hide, and drop in stones that have sat in the fire.",
    ("Hiss. Steam. It works.", {"tags": ["softly"], "emotion": "relief", "pause_after": 0.6}),
    ("Until a stone explodes.", {"tags": ["suspenseful"], "emphasis": ["explodes"], "emotion": "shock"}),
    "Wet river cobbles hold water inside. Heat them, and the rock bursts.",
    ("Shrapnel. Several small cuts. Everybody learns something, mostly about shrapnel.", {"tags": ["amused"], "emotion": "dry humour"}),
    ("A charcoal filter makes the water clearer.", {"emotion": "hope"}),
    ("Not safer.", {"tags": ["sighs"], "emphasis": ["safer"], "emotion": "disappointment", "pause_after": 0.4}),
    "Only boiling does that.",
    ("Then Curie makes soap, from animal fat and wood ash.", {"tags": ["warmly"], "emotion": "determination"}),
    ("It smells awful. Nobody likes the smell. Everybody likes not dying.", {"tags": ["amused"], "emotion": "dry humour"}),
    ("But the sun is already going down.", {"tags": ["slowly"], "emotion": "unease"}),
], [("John Snow", "B", "w1_snow_rule", {"heroes_ok": True}), ("So they dig", "A", "w1_pit_steam"),
    ("Hiss.", "C", "w1_stone_steam", {"insert": True}), ("Until a stone", "C", "w1_cobble_crack", {"insert": True}),
    ("Shrapnel.", "B", "w1_franklin_cuts", {"heroes_ok": True}), ("A charcoal filter", "B", "w1_snow_filter", {"heroes_ok": True}), ("Then Curie", "B", "w1_curie_soap", {"heroes_ok": True}),
    ("It smells awful.", "C", "w1_wash_hands", {"insert": True}),
    ("But the sun", "A", "w1_valley_dusk")],
    {"sfx": [{"at": "Hiss.", "sound": "stone_hiss_steam", "gain_db": -16, "max_s": 1.6},
             {"at": "Until a stone", "sound": "cobble_crack", "gain_db": -13, "max_s": 0.8}]})

seg("S06", "end", 6, [
    ("And that's day seven.", {"tags": ["warmly"], "emotion": "calm"}),
    "A secure camp. A stock of stone tools. A water routine.",
    ("Two people are sick. One cut is infected. One wrist is broken.", {"tags": ["slowly"], "emotion": "gravity", "pause_after": 0.6}),
    ("They're alive. But only just ahead.", {"emphasis": ["ahead"], "emotion": "tension", "pause_after": 0.7}),
    ("Nansen looks at the dark valley, and at the hills beyond.", {"tags": ["softly"], "emotion": "dread"}),
    "Because the one thing they can't chop, grind or boil is time.",
    ("And a winter is coming.", {"tags": ["whispers"], "emotion": "foreboding", "pause_after": 0.6}),
    ("Next: Month One. And somebody finally invents the POT.", {"tags": ["intrigued"], "emphasis": ["pot"], "emotion": "promise"}),
], [("And that's", "A", "w1_camp_night"), ("Two people", "C", "w1_wrist_hand", {"insert": True}),
    ("They're alive.", "A", "w1_camp_wide"), ("Nansen looks", "B", "w1_nansen_watch", {"heroes_ok": True}),
    ("Because the one", "A", "w1_camp_night"), ("And a winter", "C", "w1_frost_grass", {"insert": True}),
    ("Next:", "A", "w1_pit_steam")],
    {"beds": [{"at": "And that's", "sound": "fire"}]})

doc = json.loads(json.dumps(day1))
doc["episode"] = {"id": "stone_age_week1", "title": "100 greatest scientists dropped into the Stone Age, Week 1", "fps": 30,
                  "size": [1920, 1080], "grade": "prehistory"}
doc["world"]["topic"] = "100 greatest scientists dropped into the Stone Age, week one"
doc["world"]["visitors"] = [{"era": "industrial_victorian", "people": ["nansen", "franklin", "newton", "einstein", "darwin", "wallace", "snow", "curie", "tesla"]}]
doc["world"]["day_arc"] = [{"beat": 1, "light": "overcast_day"}, {"beat": 2, "light": "overcast_day"}, {"beat": 3, "light": "overcast_day"},
                           {"beat": 4, "light": "overcast_day"}, {"beat": 5, "light": "last_sun"}, {"beat": 6, "light": "night_fire"}]
doc["cast"]["curie"] = {"names": ["curie", "marie curie"], "card": "Marie Curie: dark hair in a bun, serious pale face, long dark dress with a high collar"}
doc["cast"]["tesla"] = {"names": ["tesla", "nikola tesla"], "card": "Nikola Tesla: tall thin man, slicked dark hair, narrow moustache, long dark coat"}
doc["story"] = {"events": [], "forbidden_props": ["magnifying glass", "magnifier", "matches", "lighter", "metal tools"]}
doc["picture_dirs"] = ["../day1_v7/pictures", "pictures"]
doc["sound_dirs"] = ["../day1_v7/sounds", "sounds"]
refs_used = sorted({r for p in P.values() for r in p["refs"]})
# whose face each reference picture carries (looked at, 2026-10-16: the Day 1 library lists only some of them; d1-36 is Franklin + Einstein)
FACES = {"v5_d1-02": ["franklin"], "v5_d1-04": ["darwin"], "v5_d1-06": ["newton", "einstein"], "v5_d1-08": ["curie", "tesla"],
         "v5_d1-14": ["nansen"], "v5_d1-18": ["franklin", "newton"], "v5_d1-20": ["einstein", "newton"], "v5_d1-22": ["wallace"],
         "v5_d1-25": ["snow", "wallace"], "v5_d1-36": ["franklin", "einstein"]}
doc["library"] = {r: {**day1["library"].get(r, {"file": f"{r}.png", "engine": "existing", "shows": []}), "heroes": FACES.get(r, [])}
                  for r in refs_used}
doc["music"] = [{"track": "clockwork_loop__v1", "from": "<start>", "to": None, "gain_db": -21}]
doc["segments"] = SEG
for s in SEG:
    for sh in s["shots"]:
        if sh["picture"] in P:
            sh["picture"] = P.pop(sh["picture"])
doc["look"] = {"style_refs": day1["look"]["style_refs"], "default_engine": "pod_ref"}
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(len(SEG), "segments", sum(len(s["shots"]) for s in SEG), "shots", sum(len(s["lines"]) for s in SEG), "lines")
