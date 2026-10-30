import json, sys
sys.path.insert(0, "/home/user/explainer-engine/scratch")
sys.path.insert(0, "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/scratch")
import edit_gen
ROOT = edit_gen.ROOT

STAGING = {
"S04": dict(scene_id="rise", location="a wet green rise above the halted column",
  layout="a low grassy crest: the emperor at its centre, the marshal's horse to his left, the Mameluke with the second horse to his right; the halted column below behind them, the far ridge opposite",
  fixed=["wet green grass", "thin fog tearing off the far ridge", "the halted column below the crest"],
  roster=["napoleon", "murat", "kerim"],
  positions={"napoleon": "standing at the crest, centre", "murat": "mounted, left of the emperor", "kerim": "on foot holding the second horse, right"},
  master="p_rise_wide"),
"S06": dict(scene_id="wagons", location="the edge of the wagon park at dusk",
  layout="heavy wagons in a loose line, horses lying between the wheels, open grass behind; the emperor on foot beside a wagon, the marshal riding in from the left",
  fixed=["red dusk light", "horses lying between the wagon wheels"],
  roster=["napoleon", "murat", "kerim"],
  positions={"napoleon": "on foot beside a wagon, centre", "murat": "mounted on a lathered horse, left", "kerim": "on foot, right"},
  master="p_wagon_wide"),
"S08": dict(scene_id="tent", location="the khan's felt tent behind a river-cut",
  layout="a round felt tent with a fire of dung and sagebrush in the middle; the khan sits cross-legged on the left of the fire, the prisoner kneels on the right, the herder in the corner",
  fixed=["felt walls", "a fire of dung and sagebrush", "the herder in the corner"],
  roster=["genghis", "kerim"],
  positions={"genghis": "cross-legged on the left of the fire", "kerim": "kneeling with bound hands on the right"},
  master="p_tent_wide"),
"S10": dict(scene_id="valley", location="the slope at the mouth of the valley",
  layout="long guns in battery at the centre of the slope, the squares behind them, the wagon line at the back, the ridge opposite across the valley",
  fixed=["long bronze guns in a row", "grey dawn light", "the ridge opposite"],
  roster=["napoleon", "murat", "kerim"],
  positions={"napoleon": "standing beside the central gun, centre", "murat": "mounted on a wagon horse, left", "kerim": "on foot at the emperor's right elbow"},
  master="p_slope_wide"),
"S11": dict(scene_id="burnt_wagons", location="behind the burnt wagon line",
  layout="black axles and smoke behind the wagon line; the emperor on the left facing the Mameluke on the right",
  fixed=["black axles and drifting smoke", "ash on the ground"],
  roster=["napoleon", "kerim"],
  positions={"napoleon": "standing on the left", "kerim": "standing on the right"},
  master="p_smoke_wide"),
"S13": dict(scene_id="parley", location="a felt carpet on open grass between the two armies",
  layout="a square felt carpet on open grass; the emperor sits at its left edge, the khan at its right edge, the Mameluke kneels between them, the herder behind him; the two armies far off on either side",
  fixed=["a felt carpet on open grass", "the two armies far off on either side"],
  roster=["napoleon", "genghis", "kerim"],
  positions={"napoleon": "sitting on the left edge", "genghis": "sitting on the right edge", "kerim": "kneeling in the middle"},
  master="p_carpet_wide"),
}

MUSIC = [
 {"track": "clockwork_loop__v1", "from": "<start>", "to": "Dusk, the sixth day.", "gain_db": -31, "fade_s": 2.0},
 {"track": "sneaky_pizzicato__v1", "from": "Behind him, horses lie down", "to": "Kerim rides into the French", "gain_db": -29, "fade_s": 2.0},
 {"track": "clockwork_loop__v1", "from": "The emperor hears the khan's", "to": "They never wanted my guns.", "gain_db": -30, "fade_s": 2.0},
 {"track": "sneaky_pizzicato__v1", "from": "And they knew exactly where", "to": "A felt carpet on open", "gain_db": -29, "fade_s": 2.0},
 {"track": "clockwork_loop__v1", "from": "Kerim kneels between them", "to": "The last man steps into", "gain_db": -31, "fade_s": 3.0},
]
COUNTER = [("S01", "DAY 1"), ("S03", "OCT 1812"), ("S04", "DAY 1"), ("S05", "DAY 6"), ("S07", "DAY 7"), ("S09", "DAY 8"),
           ("S14", "DAY 9"), ("S15", "OCT 1812")]
GRAPHICS = [{"id": "g_gap", "segment": "S01", "at": "Now the grass is green", "kind": "calc", "claim": "C-21", "hold": 3.5,
             "title": "THE GAP", "side": "right", "lines": ["1812", "- 1223", "= 589 years"]}]

STEPPE = "amb_steppe_wind__v1"
AUDIO = {
 "S02": {"sfx": [{"at": "run away first", "sound": "swish__v2", "gain_db": -26, "purpose": "the quick push-in on the enemy that runs away", "yields_to": ["voice"]}]},
 "S12": {"beds": [{"at": "So, who won?", "sound": STEPPE, "gain_db": -33, "purpose": "the open steppe after the smoke", "yields_to": ["voice"]}],
         "sfx": [{"at": "found his dinner", "sound": "pop_in__v1", "gain_db": -26, "purpose": "the dry punch on the line that lands the joke", "yields_to": ["voice"]}]},
 "S01": {"beds": [{"at": "An arrow stands", "sound": STEPPE, "gain_db": -32, "purpose": "the steppe wind under the cold open", "yields_to": ["voice"]}],
         "sfx": [{"at": "Now the grass is green", "sound": "seam_shimmer__v1", "gain_db": -24, "purpose": "the fog carries the army across 589 years", "yields_to": ["voice"]}]},
 "S03": {"beds": [{"at": "Back in Moscow", "sound": "amb_burnt_garage_dawn__v1", "gain_db": -32, "purpose": "burning Moscow in 1812", "yields_to": ["voice"]},
                  {"at": "On this steppe there is", "sound": STEPPE, "gain_db": -32, "purpose": "back to the empty steppe", "yields_to": ["voice"]}]},
 "S04": {"beds": [{"at": "On a wet green", "sound": STEPPE, "gain_db": -32, "purpose": "the open rise above the halted column", "yields_to": ["voice"]}]},
 "S06": {"beds": [{"at": "Dusk, the sixth day.", "sound": STEPPE, "gain_db": -33, "purpose": "dusk at the wagon park", "yields_to": ["voice"]}]},
 "S08": {"beds": [{"at": "A felt tent behind", "sound": "amb_motel_pool_night__v1", "gain_db": -32, "purpose": "night outside the khan's tent: crickets and a camp", "yields_to": ["voice"]}]},
 "S09": {"beds": [{"at": "Kerim rides into the French", "sound": STEPPE, "gain_db": -33, "purpose": "pre-dawn wind at the French lines", "yields_to": ["voice"]}]},
 "S10": {"beds": [{"at": "Dawn on the eighth", "sound": STEPPE, "gain_db": -32, "purpose": "the valley at dawn", "yields_to": ["voice"]},
                  {"at": "They went round the ridge", "sound": "amb_burnt_garage_dawn__v1", "gain_db": -30, "purpose": "the wagons burn behind the French line", "yields_to": ["voice"]}],
         "sfx": [{"at": "At nothing, sire?", "sound": "cannon_boom__v1", "gain_db": -22, "offset_s": -0.19, "purpose": "the one round the guns fire, on the hard shake", "yields_to": ["voice"]},
                 {"at": "They wanted my bread.", "sound": "reveal_sting__v1", "gain_db": -24, "purpose": "breaks the music dropout on the line that explains the whole battle", "yields_to": ["voice"]}]},
 "S11": {"beds": [{"at": "Behind the wagon line", "sound": "amb_burnt_garage_dawn__v1", "gain_db": -33, "purpose": "smoke and embers behind the burnt wagons", "yields_to": ["voice"]}]},
 "S13": {"beds": [{"at": "A felt carpet on open", "sound": STEPPE, "gain_db": -34, "purpose": "wind over the carpet between the armies", "yields_to": ["voice"]}]},
 "S15": {"beds": [{"at": "The last man steps", "sound": STEPPE, "gain_db": -34, "purpose": "the wind at the fog's edge", "yields_to": ["voice"]}],
         "sfx": [{"at": "Then the fog closes", "sound": "seam_shimmer__v1", "gain_db": -26, "purpose": "the fog takes the army home, echoing the arrival", "yields_to": ["voice"]}]},
}
ACC = {  # (segment, shot index by picture first use) hard accents
}

def main():
    d = edit_gen.build()
    segs = {s["id"]: s for s in d["segments"]}
    for sid, st in STAGING.items():
        segs[sid]["staging"] = st
    for sid, a in AUDIO.items():
        segs[sid]["audio"] = a
    d["music"] = MUSIC
    d["counter"] = [{"segment": s, "label": l} for s, l in COUNTER]
    d["graphics"] = GRAPHICS
    d["look"] = {"default_engine": "gemini"}
    json.dump(d, open(ROOT + "production_script.json", "w"), indent=1, ensure_ascii=False)
    print("written", sum(len(s["shots"]) for s in d["segments"]), "shots")

if __name__ == "__main__":
    main()
