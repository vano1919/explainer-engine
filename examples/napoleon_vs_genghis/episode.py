"""Napoleon vs Genghis Khan: the shot list (template D, docs/STORY_ENGINE.md; script engine v1, docs/SCRIPT_ENGINE.md).

The story: in September 1812 the Grande Armee walks into a fog outside Moscow and comes out on the steppe of 1223, where
Genghis Khan's army waits. Everything the narrator states as history carries a claim id (CLAIMS, with sources); the fold,
the khan's presence in the west, every line of dialogue, Kemal, Bars, Bayan, Sergeant Brun and the battles are
invented and listed as such (I01..I04). The khan was in fact back in Central Asia in 1223 (C19).
"""

WIKI = "https://en.wikipedia.org/wiki/"

META = {
    "schema": "film_shots/1",
    "engine": "script_engine/1",
    "episode": "What If Napoleon Marched Into Genghis Khan? (15-minute animated docudrama, template D)",
    "script": "script.md",
    "style": {
        "trigger": "wldnk style",
        "video_sentence": "Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright "
                          "colours; snappy cartoon timing, poses hold between quick moves.",
    },
    "cast": {
        "napoleon": {"name": "Napoleon", "tag": "the short general in a grey greatcoat and a black bicorne hat",
                     "voice": "a quick, clipped, slightly hoarse man's voice with a French accent"},
        "murat": {"name": "Murat", "tag": "the tall marshal with long black curls and a white-plumed fur hat",
                  "voice": "a loud, bright, boastful man's voice with a southern French accent"},
        "kemal": {"name": "Kemal", "tag": "the mameluke rider in a white turban and a red embroidered vest",
                  "voice": "a soft, careful young man's voice with a Crimean Tatar accent"},
        "brun": {"name": "Brun", "tag": "the grey-moustached grenadier in a tall black bearskin cap",
                 "voice": "a gravelly, tired old soldier's voice with a French accent"},
        "infantry": {"tag": "the ranks of French infantry in dark blue coats with white crossbelts"},
        "gunners": {"tag": "the French gun crew in dark blue jackets beside a bronze cannon"},
        "genghis": {"name": "Genghis", "tag": "the tall khan with a long grey beard and a blue fur-trimmed robe",
                    "voice": "a deep, slow, quiet man's voice with a Mongolian accent"},
        "subutai": {"name": "Subutai", "tag": "the stocky general with a shaved head and bronze scale armour",
                    "voice": "a flat, dry, practical man's voice with a Mongolian accent"},
        "bars": {"name": "Bars", "tag": "the young interpreter with a braided forelock and a green felt cap",
                 "voice": "a quick, high young man's voice with a Turkic accent"},
        "bayan": {"name": "Bayan", "tag": "the young scout with a scar on his cheek and a fox-fur hat",
                  "voice": "a breathless young man's voice with a Mongolian accent"},
        "riders": {"tag": "the line of Mongol horse archers in brown felt coats on short shaggy horses"},
        "cavalry": {"tag": "the French cuirassiers in steel breastplates and brass helmets on big horses"},
        "drummer": {"name": "Petit", "tag": "the young drummer in a white shako with a red plume",
                    "voice": "a thin, hungry teenage voice with a French accent"},
        "scouts": {"tag": "the two Mongol scouts in brown felt coats with bows on their backs"},
        "guards": {"tag": "the handful of French camp guards in grey greatcoats with long muskets"},
        "geniuses": {"tag": "the crowd of modern people in bright jackets around a Stone Age campfire"},
        "stranded": {"tag": "the group of stranded travellers in winter coats on the Ice Age snow"},
    },
    "places": {
        "fog": "a dirt road through a birch forest swallowed by thick white fog, early morning",
        "steppe": "an endless open grass steppe under a huge pale sky, low rolling hills on the horizon",
        "ridge": "a long low grassy ridge on the open steppe",
        "camp": "a French army camp on the open steppe, white canvas tents, stacked muskets and bronze cannons",
        "tent": "inside a canvas campaign tent, a folding wooden table with two candles",
        "mgcamp": "a Mongol camp of round white felt yurts on the steppe, horse herds grazing, cooking smoke rising",
        "yurt": "inside a large round felt yurt, red carpets on the floor, a low fire in the middle, a wooden lattice wall",
        "valley": "a shallow grassy valley between two low hills on the open steppe",
        "wagons": "a long camp of covered supply wagons on the open steppe",
        "moscow": "a city of wooden houses and onion-domed churches burning at night",
        "stoneage": "a rocky valley of the Stone Age with a cave mouth and a campfire",
        "iceage": "a frozen Ice Age plain of snow and blue ice under a grey sky",
    },
    "channel": {"worlds_on": ["the Stone Age"], "worlds_coming": ["the Ice Age"]},
    "claims": {
        "C01": {"kind": "fact", "text": "The first wave of the Grande Armee crossed the Neman on 24 June 1812: more than "
                "450,000 men and over 150,000 horses.", "source": WIKI + "French_invasion_of_Russia"},
        "C02": {"kind": "fact", "text": "About 100,000 French troops entered Moscow on 14 September 1812.",
                "source": WIKI + "French_invasion_of_Russia"},
        "C04": {"kind": "fact", "text": "Napoleon trained as an artillery officer; he preferred the offensive and aimed "
                "to destroy the enemy's army in battle.", "source": WIKI + "Napoleon"},
        "C05": {"kind": "fact", "text": "The Gribeauval 12-pounder: effective range about 900 m with round shot and "
                "600 m with canister; a crew of 15.", "source": WIKI + "Canon_de_12_Gribeauval"},
        "C06": {"kind": "fact", "text": "The Charleville musket was effective to about 100 yards (90 m), two or three "
                "shots a minute.", "source": WIKI + "Charleville_model_1777_musket"},
        "C07": {"kind": "fact", "text": "Infantry squares held their volley until cavalry was very close; a steady square "
                "was rarely broken by cavalry alone, artillery was its main danger.", "source": WIKI + "Infantry_square"},
        "C08": {"kind": "fact", "text": "Each Mongol soldier kept three or four horses and changed mounts on the march.",
                "source": WIKI + "Mongol_military_tactics_and_organization"},
        "C09": {"kind": "fact", "text": "Mongol composite bows: aimed shots at about 150-175 m, ballistic shots up to "
                "about 400 m; a quiver of 60 arrows.", "source": WIKI + "Mongol_military_tactics_and_organization"},
        "C10": {"kind": "fact", "text": "Kalka River, 31 May 1223: the Rus princes had killed the Mongol envoys; Jebe and "
                "Subutai drew them on in a feigned retreat of about nine days and destroyed them; captured princes were "
                "crushed under a victory platform.", "source": WIKI + "Battle_of_the_Kalka_River"},
        "C11": {"kind": "fact", "text": "Genghis Khan promoted by merit and loyalty, kept the enemy archer Jebe who had shot "
                "his horse and admitted it, and recruited skilled men from defeated enemies.",
                "source": WIKI + "Genghis_Khan"},
        "C12": {"kind": "fact", "text": "Moscow was abandoned by Kutuzov's army and burned (Governor Rostopchin); "
                "Alexander I refused to negotiate; the French left on 19 October after about five weeks.",
                "source": WIKI + "French_invasion_of_Russia"},
        "C13": {"kind": "fact", "text": "Murat was the best cavalry commander of the Grande Armee and showed a total lack "
                "of concern for the well-being of his horses.", "source": WIKI + "Joachim_Murat"},
        "C14": {"kind": "fact", "text": "The Mameluke company of the Imperial Guard served in Russia in 1812 (109 riders on "
                "1 July); its men came from Crimea, Georgia, Circassia, Syria, Egypt and elsewhere.",
                "source": WIKI + "Mamelukes_of_the_Imperial_Guard"},
        "C15": {"kind": "fact", "text": "Crimean Tatar and Cuman (the Kipchak of the 13th-century steppe) are both "
                "Kipchak Turkic languages.", "source": WIKI + "Kipchak_languages"},
        "C16": {"kind": "fact", "text": "The army's supply rested on heavy wagons unfit for Russian tracks; foraging along "
                "the road fed the rest ('the Army must live by the sword', Colonel Pion).",
                "source": WIKI + "French_invasion_of_Russia"},
        "C19": {"kind": "fact", "text": "Genghis Khan stopped his Central Asian campaign in 1221 and was back in Mongolia by "
                "1225; in 1223 he was not on the western steppe.", "source": WIKI + "Genghis_Khan"},
        "C20": {"kind": "fact", "text": "A tumen was a Mongol unit of 10,000 men.",
                "source": WIKI + "Mongol_military_tactics_and_organization"},
        "C21": {"kind": "fact", "text": "1812 - 1223 = 589 years.", "source": "arithmetic"},
        "CH1": {"kind": "fact", "text": "The channel's episodes: 100 geniuses in the Stone Age (on the channel); 100 people "
                "dropped into the Ice Age (coming next).", "source": "CrossWorld Chronicles, the creator's plan 2026-10-24"},
        "I01": {"kind": "invented", "text": "The fog that drops the army from 1812 into the steppe of 1223, and back.",
                "source": "the episode's premise"},
        "I02": {"kind": "invented", "text": "Genghis Khan himself on the western steppe in 1223 with about two tumens.",
                "source": "the episode's premise (against C19)"},
        "I03": {"kind": "invented", "text": "The skirmish, the valley battle, the burning of the wagons and their numbers.",
                "source": "the episode's story"},
        "I04": {"kind": "invented", "text": "The parley and the two guns left to the khan.", "source": "the episode's story"},
    },
}

GRASS = "standing in the dry steppe grass"
# the sound of a place when a montage shot leaves its scene's place
AMBIENCE = {"fog": "a slow marching drum in the fog", "steppe": "wind over open grass", "ridge": "wind over the ridge",
            "camp": "a busy army camp, distant shouted orders", "tent": "a candle guttering, canvas creaking",
            "mgcamp": "horses grazing, a far-off horn", "yurt": "a fire crackling, wind against felt",
            "valley": "wind, distant horns, horses", "wagons": "wind, a wagon creaking", "moscow": "a city burning, timbers cracking",
            "stoneage": "a crackling campfire", "iceage": "an icy wind howling"}


def write(ep):
    # ---- 1. hook (0:00-0:03) -----------------------------------------------------------------------------------
    ep.scene("S01", "fog", light="cold white morning light", ambience="a slow marching drum in the fog",
             stage={"infantry": ("center", "camera", "standing on the dirt road", "")})
    ep.shot("INSERT", 3, "The march stops on one beat: something is wrong.", mode="insert",
            act=("infantry", "a wooden drumstick hangs above a French drum in the fog",
                 "the drumstick strikes the drum skin twice", "the drumstick stops in mid-air, shaking"),
            narr="In September 1812, Napoleon marched a hundred thousand men into a fog outside Moscow.",
            claims=["C02"], loud="two sharp drum beats")
    ep.teaser("canister_hit", 2, "Teaser: a cannon blast breaks a mass of riders.")
    ep.teaser("charge_split", 2, "Teaser: lances against a wall of bayonets.")
    ep.teaser("wagons_burn", 2, "Teaser: torches on the wagons.")
    ep.shot("EWS", 3, "Reveal: an army no European has seen in six centuries.", mode="narrated", tier="light",
            who=["riders"], place="ridge", light="dawn light breaking through thin fog", src="keyframe",
            act=("riders", "sit still on their horses along the ridge", "raise their bows all at once",
                 "hold the bows high against the sky"),
            rel=["thin fog lies in front of the ridge"], lead=("above", "where the bows rise"),
            height={"riders": "quarter"}, on={"riders": "sitting on horses on the ridge top"},
            foley=["horses snorting"])
    # ---- 2. information gap (0:03-0:30) -------------------------------------------------------------------------
    ep.scene("S02", "fog", light="cold white morning light", ambience="wind over open grass",
             stage={"napoleon": ("left", "right", "sitting astride a white horse", ""),
                    "genghis": ("right", "left", "sitting astride a short dun horse", ""),
                    "infantry": ("center", "camera", "standing on the dirt road", "")})
    ep.shot("WS", 4, "The columns stop, row after row.", mode="narrated", tier="full", who=["infantry"],
            act=("infantry", "march out of the fog in long blue columns", "jerk to a halt, row after row",
                 "stand frozen with muskets on their shoulders"),
            narr="They came out of it in the year 1223.", claims=["I01"], lead=("none", ""),
            rel=["the fog bank rises behind the columns"], height={"infantry": "third"},
            foley=["boots stamping to a halt"])
    ep.shot("MS", 4, "The emperor sees what his army walked into.", mode="narrated", tier="light", who=["napoleon"],
            src="keyframe",
            act=("napoleon", "sits his white horse at the edge of the fog", "lifts a small brass telescope to his eye",
                 "holds the telescope dead still", "his brows pull together"),
            narr="And the army waiting for them belonged to Genghis Khan.", claims=["I02"], lead=("right", "where he looks"),
            foley=["a horse shifting its hooves"])
    ep.shot("CU", 4, "The khan, the man waiting on the other side.", mode="narrated", tier="light", who=["genghis"],
            place="ridge", light="dawn light", src="keyframe",
            act=("genghis", "sits his horse on the ridge, perfectly still", "lifts his chin slowly toward the fog",
                 "narrows his eyes and holds them there", "his mouth stays flat, his eyes do not blink"),
            narr="Napoleon will win the only battle the khan gives him.", lead=("left", "where he looks"))
    ep.shot("MCU", 4, "A soldier's face: the first fear.", mode="narrated", tier="light", who=["brun"],
            act=("brun", "stares ahead under his bearskin cap", "swallows hard and raises his chin",
                 "holds still, eyes wide"),
            narr="And it will be his worst victory.", lead=("right", "where he stares"),
            on={"brun": "standing on the dirt road"},
            )
    ep.shot("INSERT", 4, "Two kinds of war in two hands.", mode="insert", tier="light",
            act=("infantry", "a French musket and a Mongol bow lie crossed on the grass",
                 "a gust of wind shakes the bowstring", "the bowstring settles and hums"),
            narr="So what happens when the man who conquered Europe meets the man who conquered Asia?",
            place="steppe", light="pale morning light", src="keyframe")
    ep.shot("EWS", 4, "Title beat: the two armies, a valley apart.", mode="establish", tier="hold", who=["infantry", "riders"],
            place="steppe", light="pale morning light", src="keyframe", cam="push_in",
            end="the gap of empty grass between the two armies in the middle of the frame",
            rel=["the French columns stand on the left of the valley", "the Mongol riders stand on the right of the valley"],
            where={"infantry": "left_back", "riders": "right_back"}, facing={"infantry": "right", "riders": "left"},
            on={"riders": "sitting on horses on the grass", "infantry": GRASS}, height={"infantry": "quarter", "riders": "quarter"})
    # ---- 3. orientation (0:30-1:15) -----------------------------------------------------------------------------
    ep.scene("S03", "camp", light="warm late afternoon light", ambience="a busy army camp, distant shouted orders",
             stage={"napoleon": ("left", "right", GRASS, ""), "gunners": ("right", "left", GRASS, ""),
                    "genghis": ("right", "left", "sitting astride a short dun horse", ""),
                    "riders": ("center", "camera", "sitting on horses in the grass", ""),
                    "infantry": ("center", "right", GRASS, "")})
    ep.shot("WS", 4, "His method, shown as a drill.", mode="narrated", tier="full", who=["gunners"],
            act=("gunners", "stand ready around the cannon", "ram a cannonball down the barrel and jump clear",
                 "freeze in their places beside the wheels"),
            narr="Napoleon had trained as an artillery officer.", claims=["C04"],
            lead=("left", "where the barrel points"), height={"gunners": "third"}, foley=["a ramrod thumping"])
    ep.shot("MS", 4, "The artilleryman's hand on his own weapon.", mode="narrated", tier="light", who=["napoleon"],
            act=("napoleon", "rests one hand on a bronze cannon barrel", "slaps the barrel twice with his palm",
                 "keeps his hand flat on the bronze", "the corner of his mouth lifts"),
            narr="His method: find the enemy army, force one big battle, destroy it.", claims=["C04"], lead=("right", "the gun's barrel"),
            rel=["the bronze cannon stands on the right of him"], foley=["a palm slapping bronze"])
    ep.shot("MWS", 3, "The gun fires.", mode="narrated", tier="full", who=["gunners"],
            act=("gunners", "crouch beside the cannon with hands over their ears", "the cannon jerks back in a burst of smoke",
                 "the crew stand up in the drifting smoke"),
            narr="His guns could hit a target nine hundred metres away.", claims=["C05"], lead=("left", "where the smoke blows"),
            loud="one cannon shot")
    ep.shot("MS", 4, "The infantry's reach is short.", mode="narrated", tier="full", who=["infantry"], src="keyframe",
            act=("infantry", "stand in a line with muskets at the shoulder", "swing the muskets down and fire one volley",
                 "lower the muskets in a cloud of white smoke"),
            narr="His muskets reached about a hundred.", claims=["C06"], lead=("right", "where they fire"),
            on={"infantry": "standing on the trampled grass"}, loud="one musket volley")
    ep.shot("EWS", 4, "The other machine: a herd that is an army.", mode="establish", tier="hold", who=["riders"],
            place="mgcamp", light="golden evening light", src="keyframe", cam="pan_right",
            end="the herd stretching to the horizon",
            narr="Genghis Khan built his army to move.", lead=("right", "where the herd runs on"),
            rel=["hundreds of spare horses graze behind the riders"], height={"riders": "quarter"}, foley=["many hooves on turf"])
    ep.shot("MWS", 4, "A rider changes horses at a gallop's end.", mode="narrated", tier="full", who=["riders"],
            place="mgcamp", light="golden evening light", src="keyframe",
            act=("riders", "ride up beside a fresh spare horse", "leap from one saddle onto the other horse",
                 "sit the fresh horse, the tired one trotting beside"),
            narr="Every rider brought three or four horses.",
            claims=["C08"], lead=("right", "where they ride"), foley=["a saddle creaking"])
    ep.shot("MS", 4, "The bow: drawn, released.", mode="narrated", tier="full", who=["riders"],
            place="mgcamp", light="golden evening light", src="keyframe",
            act=("riders", "nock arrows on short curved bows", "pull the bows back and loose the arrows high",
                 "hold the bows up as the strings settle"),
            narr="His archers could drop an arrow four hundred metres away.", claims=["C09"],
            lead=("above", "where the arrows fly"), on={"riders": "sitting on horses in the grass"},
            foley=["bowstrings snapping"])
    ep.shot("MCU", 4, "The khan's way of choosing men.", mode="narrated", tier="light", who=["genghis"],
            place="mgcamp", light="golden evening light", src="keyframe",
            act=("genghis", "watches something beyond the frame", "lifts his chin once, slowly",
                 "keeps his chin raised", "his eyes crease a little at the corners"),
            narr="He promoted men for what they did, not for their fathers.", claims=["C11"],
            lead=("left", "where he looks"))
    ep.shot("INSERT", 4, "Two weapons side by side, two philosophies.", mode="insert", tier="light", place="steppe",
            light="pale morning light", src="keyframe",
            act=("infantry", "a heavy supply wagon wheel sinks in soft mud",
                 "a horse's hoof stamps down beside it and lifts away", "the wheel stays stuck in the mud"),
            foley=["mud sucking at a wheel"])
    ep.shot("EWS", 4, "The gap between the armies closes.", mode="narrated", tier="hold", who=["infantry", "riders"],
            place="steppe", light="pale morning light", src="keyframe", cam="push_in",
            end="the two armies small on each side of the empty valley",
            lead=("none", ""),
            rel=["the French columns stand on the left of the valley", "the Mongol riders stand on the right of the valley"],
            where={"infantry": "left_back", "riders": "right_back"}, facing={"infantry": "right", "riders": "left"},
            on={"riders": "sitting on horses on the grass", "infantry": GRASS}, height={"infantry": "quarter", "riders": "quarter"})
    # ---- 4. scene 1, inciting (1:15-2:45): the envoy ------------------------------------------------------------
    sh = ep.shot
    ep.scene("S04", "camp", light="warm late afternoon light", ambience="flags snapping in the wind, a quiet camp",
             stage={"napoleon": ("center", "right", GRASS, "stands with his hands behind his back"),
                    "murat": ("left", "right", GRASS, "rests one hand on his sabre hilt"),
                    "kemal": ("left_back", "right", GRASS, "holds his horse by the bridle"),
                    "bars": ("right", "left", "sitting astride a short shaggy horse", "holds the reins low"),
                    "brun": ("center_back", "right", GRASS, "leans on his musket")})
    sh("WS", 4, "A lone rider comes to the emperor's tents.", mode="establish", who=["murat", "napoleon", "kemal", "bars"],
       act=("bars", "rides up toward the tents", "pulls his horse up hard",
            "sits the horse still in front of the generals"),
       rel=["the white tents stand behind the French generals"], lead=("left", "where he rides in"),
       height={"bars": "third"}, foley=["hooves slowing on turf", "a horse snorting"])
    sh("MS", 5, "Murat wants the easy answer: violence.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       act=("murat", "leans toward the general", "jabs a gloved finger at the rider", "keeps the finger pointed",
            "his lip curls into a grin"),
       line=("murat", "napoleon", "Sire. Let me knock that ghost off his pony.", "eager, too loud"),
       lead=("right", "where he points"))
    sh("MS", 6, "Napoleon wants information first.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       act=("napoleon", "stands with his hands behind his back", "raises one hand flat to stop him",
            "holds the flat hand up", "his eyes stay on the rider"),
       line=("napoleon", "murat", "Not yet. A man who rides in alone wants to talk.", "quiet, clipped"),
       lead=("left", "where his hand goes"))
    sh("OTS", 5, "The translator problem is solved by an accident of history.", who=["napoleon", "kemal"], over="napoleon",
       act=("kemal", "stares at the rider", "steps forward and raises his hand to his chest",
            "stands with the hand on his chest", "his eyebrows lift in surprise"),
       claims=["C14", "C15"], line=("kemal", "napoleon", "Sire. He speaks the old Tatar tongue. My grandmother's.", "hushed, amazed"),
       lead=("none", ""))
    sh("CU", 4, "Napoleon registers the impossible and moves on.", tier="light", who=["napoleon"],
       act=("napoleon", "looks at the mameluke", "raises one eyebrow sharply", "holds the look"),
       lead=("left", "where he looks"))
    sh("MS", 4, "Get to the point.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"},
       facing={"kemal": "napoleon", "napoleon": "kemal"},
       act=("napoleon", "turns to the mameluke", "waves his hand toward the rider", "keeps the hand open"),
       line=("napoleon", "kemal", "Then tell me what he wants.", "fast, impatient"), lead=("left", "the mameluke"))
    sh("OTS", 6, "The khan's terms.", who=["kemal", "bars"], over="kemal",
       act=("bars", "sits straight on his horse", "lifts his chin and raises one fist", "holds the fist up"),
       line=("bars", "kemal", "The khan of all who live in felt tents says: kneel.", "formal, chanted"),
       lead=("above", "where his fist rises"))
    sh("OTS", 6, "The price of living.", who=["kemal", "bars"], over="kemal",
       act=("bars", "lowers his fist", "points at the cannons and the horses", "keeps pointing"),
       line=("bars", "kemal", "Give him your horses and your guns, and you will live.", "flat, rehearsed"),
       lead=("left", "where he points"))
    sh("MS", 4, "Murat finds it funny.", who=["murat"],
       act=("murat", "stares at the rider", "throws his head back and slaps his thigh", "shakes with laughter",
            "his mouth opens wide and his eyes squeeze shut"),
       lead=("above", "where his head goes"), foley=["a loud laugh"])
    sh("OTS", 6, "Napoleon answers with his whole biography.", who=["bars", "napoleon"], over="bars",
       act=("napoleon", "stands still in front of the rider", "jabs one finger at the ground", "keeps the finger down",
            "his eyes go hard and narrow"),
       line=("napoleon", "bars", "Tell your khan I kneel to nobody. We meet in battle.", "slow, cold, every word clear"),
       lead=("none", ""))
    sh("OTS", 5, "The envoy's warning, with a history lesson inside it.", who=["napoleon", "bars"], over="napoleon",
       act=("bars", "leans forward on his horse", "points back toward the west", "holds the pointing arm still"),
       claims=["C10"], line=("bars", "napoleon", "This spring, princes on the river killed the khan's envoys.", "low, almost kind"),
       lead=("left", "where he points"))
    sh("OTS", 4, "The punchline.", who=["napoleon", "bars"], over="napoleon",
       act=("bars", "lowers his arm", "drops his hand onto the saddle", "sits very still"),
       line=("bars", "napoleon", "Now the princes are dead.", "quiet"), lead=("none", ""))
    sh("MS", 4, "Murat goes for his pistol.", who=["murat"],
       act=("murat", "reaches for the pistol in his belt", "yanks the pistol halfway out", "freezes with it half drawn",
            "his teeth bare"),
       lead=("right", "where the pistol points"), foley=["leather creaking"])
    sh("MS", 4, "Napoleon protects the envoy, and his own plan.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       act=("napoleon", "steps toward the marshal", "grabs the marshal's wrist", "holds the wrist down"),
       line=("napoleon", "murat", "Put it away. Nobody touches an envoy.", "sharp, low"), lead=("left", "the marshal's wrist"))
    sh("OTS", 4, "The question that matters.", who=["bars", "napoleon"], over="bars",
       act=("napoleon", "turns back to the rider", "points at the horizon", "holds the point"),
       line=("napoleon", "bars", "Where is your khan's army?", "clipped"), lead=("none", ""))
    sh("OTS", 4, "The answer that is the whole strategy.", who=["napoleon", "bars"], over="napoleon",
       act=("bars", "smiles thinly", "pulls his horse's head round", "sits sideways on the turning horse"),
       line=("bars", "napoleon", "Everywhere you are not.", "almost a whisper"), lead=("right", "where he will turn"))
    sh("EWS", 3, "On the far ridge, riders watch the camp.", mode="establish", tier="light", who=["riders"], place="ridge",
       light="warm late afternoon light", src="keyframe",
       act=("riders", "sit their horses along the far ridge", "turn their heads together toward the camp",
            "sit still, watching"), lead=("left", "the camp below"), height={"riders": "quarter"}, foley=["wind over the ridge"])
    sh("WS", 4, "The envoy rides off into the empty steppe.", mode="establish", who=["murat", "napoleon", "bars"], exit=True,
       act=("bars", "turns his horse away from the tents", "kicks the horse into a trot up the slope",
            "rides small toward the horizon"),
       lead=("right", "where he rides off"), height={"bars": "quarter"}, foley=["hooves trotting away"])
    sh("MS", 5, "The order that starts the hunt.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       act=("napoleon", "watches the rider go", "swings round and points at the marshal's chest", "keeps the finger on him"),
       line=("napoleon", "murat", "Murat. Tomorrow you find me that army.", "fast, certain"), lead=("left", "the marshal"))
    sh("MCU", 4, "Murat promises speed.", who=["murat"], 
       act=("murat", "grins under his plumes", "slaps his chest with his fist", "grins wide"),
       line=("murat", "room", "Tomorrow, Sire. You'll have him by lunch.", "cocky"), lead=("none", ""))
    sh("MCU", 5, "The soldier's view of strategy.", who=["brun"],
       act=("brun", "leans on his musket", "lifts his head and sniffs the air", "keeps his nose up",
            "his moustache twitches"),
       line=("brun", "self", "Wherever it is, I hope it has bread.", "a grumble under his breath"), lead=("none", ""))
    # ---- 5. bridge (2:45-3:15) ----------------------------------------------------------------------------------
    ep.scene("S05", "wagons", light="flat grey evening light", ambience="wind over open grass, a wagon creaking",
             stage={"napoleon": ("center", "camera", "standing on the tent's wooden floor", ""),
                    "murat": ("center", "right", "sitting astride a big bay horse", ""),
                    "cavalry": ("center_back", "right", "sitting on horses in the grass", "")})
    sh("WS", 5, "Wagons: the army's stomach.", mode="establish", tier="light", who=[],
       narr="Napoleon's army ate from wagons, and from the farms along the road.", claims=["C16"],
       rel=["the covered wagons stand in a long line on the grass"], foley=["a harness jingling"])
    sh("INSERT", 4, "An empty sack.", mode="insert",
       act=("infantry", "an empty flour sack hangs from a soldier's hand", "the hand shakes the sack upside down",
            "a little white dust falls onto the grass"), narr="On this steppe, there were no farms.")
    sh("INSERT", 4, "Only grass.", mode="insert", src="keyframe", place="steppe", light="flat grey evening light",
       act=("cavalry", "a French cavalry horse tears up a mouthful of grass", "the horse lifts its head, chewing",
            "the horse stands chewing in the wind"), narr="Only grass. And grass feeds horses, not men.")
    sh("MS", 5, "The emperor's impatience.", mode="narrated", who=["napoleon"], place="tent", light="warm candlelight",
       src="keyframe",
       act=("napoleon", "bends over the table between the candles", "slams his fist down on the table",
            "leans on both fists, breathing hard", "his brows crush down over his eyes"),
       narr="So he needed his battle, and he needed it fast.", lead=("none", ""), on={"napoleon": "standing on the tent's wooden floor"},
       loud="a fist on wood")
    sh("WS", 4, "Murat's cavalry rides out at dawn.", mode="narrated", who=["murat", "cavalry"], place="steppe",
       light="cold pink dawn light", src="keyframe",
       act=("murat", "sits his horse at the head of the cavalry", "raises his sabre high and points it at the horizon",
            "holds the sabre pointed forward"),
       lead=("right", "where they will ride"),
       rel=["the cuirassiers sit their horses behind the marshal"], height={"murat": "third"}, foley=["sabre ringing"])
    # ---- 6. scene 2, escalation (3:15-5:00): the first plan fails ------------------------------------------------
    ep.scene("S06", "steppe", light="hard midday sun", ambience="wind in dry grass, far-off hooves",
             stage={"murat": ("left", "right", "sitting astride a big bay horse", ""),
                    "napoleon": ("right", "left", GRASS, ""), "kemal": ("left", "right", GRASS, ""),
                    "brun": ("center", "right", GRASS, ""), "infantry": ("center_back", "right", GRASS, ""),
                    "cavalry": ("left_back", "right", "sitting on horses in the grass", ""),
                    "gunners": ("left", "right", GRASS, ""),
                    "riders": ("right_back", "left", "sitting on horses on the far ridge", "")})
    sh("WS", 4, "The camp Murat found is already gone.", mode="establish", who=["murat"],
       act=("murat", "rides into a ring of cold campfires", "pulls up and twists round in the saddle",
            "stares at the empty trampled grass"),
       rel=["black rings of old campfires lie on the trampled grass in front of him"], lead=("right", "where he looks"),
       height={"murat": "third"}, foley=["a horse blowing"])
    sh("MS", 4, "The fires are warm: they were just here.", who=["murat"], on={"murat": "kneeling on the trampled grass"},
       act=("murat", "kneels beside a ring of ashes", "pushes his bare hand into the ashes", "holds the hand in the ashes",
            "his eyes widen"),
       line=("murat", "self", "Gone. And the ashes are warm.", "puzzled, low"), lead=("none", ""))
    sh("INSERT", 3, "An arrow from nowhere.", mode="insert",
       act=("riders", "a black-feathered arrow drops out of the sky", "the arrow slams into the turf beside a riding boot",
            "the arrow quivers upright"), loud="a hard thud")
    sh("EWS", 4, "They were watching all along, out of range.", mode="establish", who=["riders"], place="ridge",
       src="keyframe", act=("riders", "sit their horses far away on the skyline", "raise their bows and loose a volley high",
                             "hold the bows up against the sky"),
       lead=("above", "where the arrows rise"), height={"riders": "quarter"}, foley=["many bowstrings at once"])
    sh("MS", 4, "The column under arrows.", who=["brun", "infantry"], src="keyframe",
       act=("brun", "looks up at the sky", "throws himself flat in the grass", "lies flat with one arm over his head"),
       react=[("infantry", "duck behind their packs")], line=("brun", "room", "Down! Get down!", "a bellow"),
       rel=["the column of infantry stands behind the grenadier"], lead=("below", "where he will fall"),
       loud="arrows hissing down")
    sh("INSERT", 3, "A pinned pack.", mode="insert",
       act=("riders", "arrows rain down onto a soldier's pack on the grass", "an arrow pins the pack to the ground",
            "the pack lies pinned, the arrow shaking"), foley=["arrows thudding into canvas"])
    sh("MS", 4, "How far?", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"}, src="keyframe",
       facing={"kemal": "napoleon", "napoleon": "kemal"},
       act=("napoleon", "lowers his telescope", "points the telescope at the ridge", "keeps it pointed"),
       line=("napoleon", "kemal", "How far are they?", "calm, fast"), lead=("left", "where he points"))
    sh("MS", 4, "Too far.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"},
       facing={"kemal": "napoleon", "napoleon": "kemal"},
       act=("kemal", "shades his eyes with one hand", "points at the far ridge", "holds the point"),
       claims=["C09"], line=("kemal", "napoleon", "Four hundred metres, Sire. Maybe more.", "careful"), lead=("left", "where he points"))
    sh("MS", 5, "Kemal names the trick.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"}, facing={"kemal": "napoleon", "napoleon": "kemal"}, 
       act=("kemal", "watches the sky", "points straight up at the falling arrows", "keeps the arm up"),
       line=("kemal", "napoleon", "They shoot high, Sire. The arrows drop on us.", "quick, low"), lead=("none", ""))
    sh("INSERT", 3, "They keep falling.", mode="insert",
       act=("riders", "an arrow drops out of the sky", "the arrow slams into the turf beside a cannon wheel",
            "the arrow quivers upright"), loud="a hard thud")
    sh("CU", 4, "He does the arithmetic.", who=["napoleon"],
       act=("napoleon", "stares at the ridge", "shakes his head once", "holds his head still", "his jaw tightens"),
       claims=["C06"], line=("napoleon", "self", "Our muskets reach a hundred.", "flat, to himself"), lead=("none", ""))
    sh("MS", 4, "The reflex: charge.", who=["murat", "napoleon"], where={"murat": "left", "napoleon": "right"},
       facing={"murat": "napoleon", "napoleon": "murat"},
       act=("napoleon", "swings round to the marshal", "flings his arm toward the ridge", "keeps the arm out"),
       line=("napoleon", "murat", "Murat! Drive them off that ridge!", "a shout"), lead=("left", "where he flings his arm"),
       on={"murat": "sitting astride a big bay horse"})
    sh("MCU", 4, "Murat's favourite order.", who=["murat"],
       act=("murat", "grins under his plumes", "draws his sabre and raises it high", "holds the sabre up"),
       line=("murat", "room", "With pleasure!", "joyful"), lead=("above", "where the sabre goes"), foley=["steel ringing"])
    sh("WS", 4, "The French charge.", mode="establish", who=["cavalry"], src="keyframe",
       act=("cavalry", "sit in a long line of big horses", "lunge forward together in a charge",
            "thunder across the grass in a wall of steel"),
       lead=("right", "where they charge"), height={"cavalry": "third"}, loud="hundreds of hooves")
    sh("WS", 4, "The Mongols turn away and shoot backwards.", mode="establish", who=["riders"], place="ridge", src="keyframe",
       act=("riders", "wheel their horses round", "twist in their saddles and loose arrows backward",
            "ride on, still twisting round"),
       lead=("right", "where they ride"), height={"riders": "third"}, foley=["bowstrings snapping"])
    sh("MS", 4, "The French horses are spent.", who=["murat"],
       act=("murat", "sits a horse with foam on its neck", "the horse stumbles and jerks its head down",
            "the horse stands, blowing hard"), lead=("none", ""), foley=["a horse wheezing"])
    sh("WS", 4, "The Mongols' horses are not.", mode="establish", who=["riders"], place="ridge",
       act=("riders", "ride up beside a herd of fresh horses", "leap from their saddles onto the fresh horses",
            "sit the fresh horses, rested"), lead=("right", "where they ride"), height={"riders": "third"})
    sh("MS", 5, "Murat reports the impossible.", who=["murat", "napoleon"], where={"murat": "left", "napoleon": "right"},
       facing={"murat": "napoleon", "napoleon": "murat"}, on={"murat": "standing in the dry steppe grass"},
       act=("murat", "stands beside his foaming horse", "throws his plumed hat down on the grass",
            "stands with empty hands, panting"),
       claims=["C08"], line=("murat", "napoleon", "They change horses, Sire! Like shirts! We can't catch them.", "shouting, out of breath"),
       lead=("below", "where the hat lands"))
    sh("MS", 4, "Napoleon changes the plan in one breath.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       on={"murat": "standing in the dry steppe grass"},
       act=("napoleon", "turns from the marshal", "points back at the column", "keeps pointing"),
       line=("napoleon", "murat", "Then stop chasing. Bring up the guns.", "quiet, decided"), lead=("right", "the column"))
    sh("WS", 4, "The guns come up.", mode="establish", who=["gunners"], src="keyframe",
       act=("gunners", "drag a bronze cannon up the slope by ropes", "heave the cannon wheels over the crest",
            "set the cannon facing the ridge"), lead=("right", "where the gun will point"),
       height={"gunners": "third"}, foley=["wheels grinding", "ropes creaking"])
    sh("MS", 4, "The artillery officer lays the gun himself.", who=["napoleon", "gunners"],
       where={"napoleon": "right", "gunners": "left"}, facing={"napoleon": "camera", "gunners": "napoleon"},
       act=("napoleon", "bends over the cannon barrel", "pushes the barrel's aim up with both hands",
            "holds his hands on the bronze"),
       line=("napoleon", "gunners", "Up two degrees. Wait for my word.", "precise, calm"), lead=("none", ""))
    sh("CU", 3, "One word.", who=["napoleon"],
       act=("napoleon", "raises one hand", "drops the hand down sharp", "holds the hand down"),
       line=("napoleon", "room", "Fire.", "barely loud"), lead=("below", "where his hand drops"))
    sh("MWS", 3, "The gun fires.", mode="scene", who=["gunners"],
       act=("gunners", "crouch beside the cannon with hands over their ears",
            "the cannon jerks back in a burst of smoke", "the crew stand up in the drifting smoke"),
       lead=("right", "where the smoke blows"), loud="one cannon shot")
    sh("EWS", 4, "Nine hundred metres away, the ridge breaks.", mode="establish", who=["riders"], place="ridge",
       act=("riders", "sit their horses on the far ridge", "scatter as a cannonball throws up a fountain of earth",
            "spread out across the slope"), lead=("left", "where they scatter"), height={"riders": "quarter"},
       loud="a far thud of earth")
    sh("MCU", 4, "Napoleon's first smile on the steppe.", who=["napoleon"],
       act=("napoleon", "lowers his telescope", "slaps the warm cannon barrel", "keeps his hand on the bronze",
            "a thin smile pulls at his mouth"),
       claims=["C05"], line=("napoleon", "room", "Nine hundred metres. Let him outrun that.", "pleased, soft"), lead=("none", ""))
    sh("MCU", 4, "The soldier's verdict.", who=["brun"], on={"brun": "lying flat in the dry steppe grass"},
       act=("brun", "lies flat in the grass", "lifts his head and spits out a stalk of grass", "props himself on his elbows"),
       line=("brun", "self", "First thing we've hit all week.", "dry"), lead=("none", ""))
    sh("EWS", 3, "Out of range, they form again.", mode="establish", tier="light", who=["riders"], place="ridge",
       act=("riders", "ride back over the far crest", "wheel round into a new line, farther away",
            "sit their horses in the new line"),
       lead=("left", "where they wait"), height={"riders": "quarter"}, foley=["far-off hooves"])
    # ---- 7. new complication (5:00-6:00): horses and hunger ------------------------------------------------------
    ep.scene("S07", "camp", light="blue dusk light with orange campfires", ambience="campfires crackling, a horse coughing",
             stage={"murat": ("left", "right", GRASS, ""), "brun": ("left", "right", "sitting on a drum by the fire", ""),
                    "drummer": ("right", "left", "sitting on the grass by the fire", ""),
                    "napoleon": ("center", "camera", "sitting on a folding stool", ""),
                    "riders": ("center", "right", "sitting on horses on the hillside", ""),
                    "infantry": ("center", "right", GRASS, "")})
    sh("WS", 4, "The camp at dusk, thinner already.", mode="narrated", tier="light", who=["infantry"],
       act=("infantry", "sit hunched around small campfires", "lift their tin cups and drink", "lower the cups slowly"),
       narr="Murat was the best cavalry commander in the army.", claims=["C13"], lead=("none", ""),
       rel=["the tents stand behind the campfires"], height={"infantry": "third"})
    sh("MS", 4, "Murat and the horse he is using up.", mode="narrated", tier="light", who=["murat"],
       act=("murat", "pats a thin horse on the neck", "pulls his hand back from its sharp ribs", "stands looking at it"),
       narr="He spent horses the way other men spend coins.", claims=["C13"], lead=("right", "the thin horse"),
       rel=["a thin bay horse stands on the right of him"])
    sh("MCU", 4, "Murat talks to the horse he is killing.", who=["murat"], 
       act=("murat", "rubs the horse's nose", "slaps the horse's neck twice", "turns back to the fire"),
       line=("murat", "self", "Come on, old girl. One more day.", "soft, careless"), lead=("none", ""))
    sh("INSERT", 4, "The pot.", mode="insert",
       act=("infantry", "a black pot bubbles over a small fire", "a ladle lifts a chunk of grey meat out of the pot",
            "the meat drips back into the pot"),
       narr="Every dead French horse was gone for good.", foley=["a pot bubbling"])
    sh("WS", 4, "On the hills, the Mongol remounts.", mode="narrated", who=["riders"], place="ridge", src="keyframe",
       light="blue dusk light",
       act=("riders", "drive a big herd of spare horses over the hill", "swing their whips over their heads",
            "ride on beside the herd"),
       narr="Every Mongol rider had three more behind him.", claims=["C08"], lead=("right", "where the herd runs"),
       height={"riders": "quarter"}, foley=["many hooves", "a whip cracking"])
    sh("MS", 5, "Brun shares the last biscuit.", who=["brun", "drummer"], src="keyframe",
       act=("brun", "holds up a hard biscuit", "snaps the biscuit in two and pushes half into the drummer's hand",
            "keeps his own half in his fist"),
       line=("brun", "drummer", "Last biscuit. Half each, and don't argue.", "gruff, kind"),
       lead=("right", "the drummer's hand"), foley=["a biscuit cracking"])
    sh("OTS", 4, "The boy's question.", who=["brun", "drummer"], over="brun",
       act=("drummer", "holds the half biscuit", "lifts his eyes to the dark hills", "keeps looking up"),
       line=("drummer", "brun", "Sergeant, what do they eat out there?", "small, hungry"), lead=("none", ""))
    sh("OTS", 4, "The veteran's answer.", who=["drummer", "brun"], over="drummer",
       act=("brun", "chews slowly", "points his biscuit at the hills", "keeps chewing"),
       line=("brun", "drummer", "Us, if we're slow.", "flat, deadpan"), lead=("none", ""))
    sh("OTS", 4, "The drummer pushes the biscuit back.", who=["brun", "drummer"], over="brun",
       act=("drummer", "holds out his half", "pushes the biscuit back into the old hand", "drops his hands to his knees"),
       line=("drummer", "brun", "Then you keep the half, Sergeant.", "trying to sound brave"), lead=("none", ""))
    sh("EWS", 4, "The camp shrinks into the dark.", mode="establish", tier="hold", who=[], src="keyframe", cam="pull_out",
       end="the campfires small in a huge dark steppe", narr="Each night, the French ate a little less.")
    sh("WS", 4, "Stragglers.", mode="narrated", who=["infantry"], place="steppe", src="keyframe", light="blue dusk light",
       act=("infantry", "wander out of the camp with empty sacks", "stop and drop the sacks in the tall grass",
            "stand looking around in the tall grass"),
       narr="Foragers who wandered off did not come back.", claims=["I03"], lead=("right", "the dark grass"),
       height={"infantry": "third"})
    sh("MS", 4, "Napoleon rages at a plan that will not work.", mode="narrated", who=["napoleon"], place="tent",
       light="warm candlelight", src="keyframe",
       act=("napoleon", "sits alone at the table", "hurls the candlestick off the table", "stands breathing hard",
            "his face goes red and his teeth clench"),
       narr="And Napoleon could not find his battle.", claims=["C04"],
       lead=("right", "where the candlestick flies"), on={"napoleon": "standing on the tent's wooden floor"},
       loud="a candlestick clattering")
    # ---- 8. scene 3, the other side acts (6:00-7:30): the khan's yurt ------------------------------------------
    ep.scene("S08", "yurt", light="warm firelight", ambience="a fire crackling, wind against felt",
             stage={"genghis": ("right", "left", "sitting cross-legged on a carpet", ""),
                    "subutai": ("left", "right", "sitting on a carpet", ""),
                    "bars": ("center_back", "camera", "standing against the lattice wall", "holds his cap in his hands"),
                    "bayan": ("center", "right", "kneeling on the carpet", "")})
    sh("WS", 4, "The scout who lost his horse.", mode="establish", who=["subutai", "bayan", "bars", "genghis"],
       act=("bayan", "pushes through the felt door", "drops to his knees on the carpet", "kneels with his head bowed"),
       rel=["the khan sits behind the low fire"], lead=("right", "where he kneels"),
       height={"bayan": "third"}, foley=["felt flapping"])
    sh("OTS", 6, "He confesses.", who=["genghis", "bayan"], over="genghis",
       act=("bayan", "kneels with his head low", "raises his head and spreads his empty hands", "keeps the hands open",
            "his eyes are wide and wet"),
       line=("bayan", "genghis", "Great Khan. My horse is dead. An iron ball. I ran.", "breathless, fast"),
       lead=("none", ""))
    sh("OTS", 5, "The khan's question.", who=["bayan", "genghis"], over="bayan",
       act=("genghis", "sits still", "leans forward and lifts one finger toward him", "holds the finger up"),
       line=("genghis", "bayan", "You ran back to tell me the truth?", "slow, quiet"), lead=("none", ""))
    sh("MS", 3, "Yes.", tier="light", who=["bayan", "genghis"], where={"bayan": "left_front", "genghis": "right"},
       facing={"bayan": "genghis", "genghis": "bayan"},
       act=("bayan", "kneels in front of the khan", "drops his eyes to the carpet", "keeps his eyes down"),
       lead=("none", ""))
    sh("MCU", 6, "The khan rewards honesty.", who=["genghis"],
       act=("genghis", "sits back on the carpet", "raises two fingers", "holds the two fingers up",
            "his eyes crease at the corners"),
       claims=["C11"], line=("genghis", "room", "Then you are worth more than the horse. Give him two.", "warm, slow"), lead=("none", ""))
    sh("MS", 3, "The scout cannot believe it.", tier="light", who=["bayan", "genghis"], where={"bayan": "left_front", "genghis": "right"}, facing={"bayan": "genghis", "genghis": "bayan"},
       act=("bayan", "kneels in front of the khan", "drops his forehead to the carpet", "stays bowed low"),
       lead=("none", ""))
    sh("MS", 5, "The general's report.", who=["subutai", "genghis"], where={"subutai": "left", "genghis": "right"},
       facing={"subutai": "genghis", "genghis": "subutai"},
       act=("subutai", "turns to the khan", "raises his open hand high to show a long arc", "drops the hand to his knee"),
       line=("subutai", "genghis", "Their iron balls fly farther than our arrows.", "dry, factual"), lead=("above", "the arc"))
    sh("MS", 5, "The khan's rule.", who=["subutai", "genghis"], where={"subutai": "left", "genghis": "right"},
       facing={"subutai": "genghis", "genghis": "subutai"},
       act=("genghis", "looks at the fire", "shrugs and throws his hands apart", "keeps the hands apart"),
       line=("genghis", "subutai", "Then we don't stand where they land.", "simple"), lead=("none", ""))
    sh("MCU", 4, "The khan's real question.", who=["genghis"],
       act=("genghis", "strokes his beard", "points one finger at the interpreter", "holds the finger out"),
       line=("genghis", "room", "What do they eat?", "curious"), lead=("left", "where he points"))
    sh("MS", 6, "The interpreter has watched the French camp.", who=["bars"], on={"bars": "standing on the carpet"},
       act=("bars", "steps forward from the wall", "flings his arms wide", "holds the arms out"),
       line=("bars", "room", "Bread, Khan. From wagons. Many wagons, very few sheep.", "eager"), lead=("none", ""))
    sh("WS", 3, "Out in the grass, his scouts count the wagons.", mode="establish", tier="light", who=["scouts"],
       place="wagons", light="blue dusk light", src="keyframe", on={"scouts": "lying flat in the tall grass"},
       act=("scouts", "lie flat in the tall grass", "lift their heads and stare at the wagon line",
            "sink back down into the grass"),
       rel=["the covered wagons stand in a long line behind the tall grass"], lead=("right", "the wagons"),
       height={"scouts": "quarter"}, foley=["grass rustling"])
    sh("CU", 5, "The idea lands.", who=["genghis"],
       act=("genghis", "strokes his beard slowly", "drops his hand from his beard", "sits very still",
            "one corner of his mouth lifts"),
       line=("genghis", "self", "Then the wagons are the army.", "almost to himself"), lead=("none", ""))
    sh("EWS", 4, "The French march: the fighting column ahead, the wagons falling behind.", mode="establish",
       tier="light", who=["infantry"], place="steppe", light="hazy afternoon light", src="keyframe",
       act=("infantry", "march in a long blue column", "the column pulls away over a low rise",
            "the column marches on, small"),
       rel=["the covered wagons trail far behind the column on the left"], lead=("right", "where the column marches"),
       height={"infantry": "quarter"}, foley=["far-off wagon wheels creaking"])
    sh("MS", 7, "Subutai offers the move that worked at the Kalka.", who=["subutai", "genghis"],
       where={"subutai": "left", "genghis": "right"}, facing={"subutai": "genghis", "genghis": "subutai"},
       act=("subutai", "leans in toward the khan", "jabs a finger into the carpet nine times", "flattens his hand on the carpet"),
       claims=["C10"], line=("subutai", "genghis", "Like at the river this spring. Run nine days. Turn on the tenth.", "confident"),
       lead=("none", ""))
    sh("MS", 5, "The khan wants something cleverer.", who=["subutai", "genghis"],
       where={"subutai": "left", "genghis": "right"}, facing={"subutai": "genghis", "genghis": "subutai"},
       act=("genghis", "lifts his eyes from the fire", "shakes his head once", "keeps his eyes on the general"),
       line=("genghis", "subutai", "No. This one wants a battle. Give him one.", "calm"), lead=("none", ""))
    sh("MCU", 4, "Subutai does not follow.", tier="light", who=["subutai"],
       act=("subutai", "stares at the khan", "raises both eyebrows high", "holds the look"), lead=("right", "the khan"))
    sh("OTS", 6, "The plan, in one sentence.", who=["subutai", "genghis"], over="subutai",
       act=("genghis", "leans toward the fire", "raises one finger and then sweeps his hand sideways", "rests the hand on his knee"),
       line=("genghis", "subutai", "A small one. Let him win. While he wins, take his wagons.", "slow, pleased"),
       lead=("none", ""))
    sh("WS", 3, "That night, riders slip out of the camp.", mode="establish", tier="light", who=["riders"],
       place="mgcamp", light="blue moonlight", src="keyframe", on={"riders": "standing on the trampled grass beside their horses"}, exit=True,
       act=("riders", "lead their horses out between the yurts", "swing up into the saddles one by one",
            "ride off into the dark in single file"),
       lead=("left", "where they ride off"), height={"riders": "third"}, foley=["muffled hooves"])
    sh("MCU", 5, "And the guns: the khan collects talent.", who=["genghis"],
       act=("genghis", "sits back", "raises a cupped hand as if holding something heavy", "holds the hand up"),
       line=("genghis", "room", "And the iron tubes. Bring me those whole.", "firm"), lead=("none", ""))
    sh("MS", 4, "Whole?", who=["subutai", "genghis"], where={"subutai": "left", "genghis": "right"},
       facing={"subutai": "genghis", "genghis": "subutai"},
       act=("subutai", "turns to the khan", "jerks his head back in surprise", "holds his head back"),
       line=("subutai", "genghis", "Whole?", "blunt"), lead=("none", ""))
    sh("OTS", 6, "The khan's creed.", who=["subutai", "genghis"], over="subutai",
       act=("genghis", "holds a bowl of milk", "lifts the bowl toward the general", "holds the bowl out",
            "his eyes stay steady"),
       line=("genghis", "subutai", "Never break a thing you can learn from.", "a teacher's voice"), lead=("none", ""))
    sh("WS", 4, "Subutai goes to do it.", mode="establish", who=["subutai", "bars", "genghis"], exit=True,
       act=("subutai", "gets up from the carpet", "pushes out through the felt door", "the door flap swings shut"),
       lead=("left", "the door"), height={"subutai": "third"}, foley=["felt flapping"])
    # ---- 9. preparation (7:30-8:15): the trap is set ------------------------------------------------------------
    ep.scene("S09", "steppe", light="hazy afternoon light", ambience="wind, far-off hooves",
             stage={"riders": ("right", "left", "sitting on horses on the skyline", ""), "kemal": ("left", "right", "sitting astride a grey horse", ""),
                    "infantry": ("left", "right", GRASS, ""), "brun": ("center", "right", GRASS, ""),
                    "napoleon": ("center", "right", "sitting astride a white horse", ""),
                    "gunners": ("left", "right", GRASS, "")})
    sh("EWS", 4, "Riders on the skyline, every day.", mode="establish", tier="hold", who=["riders"], place="ridge",
       cam="pan_left", end="the riders small on the right edge of the frame",
       narr="For days, the khan gave Napoleon nothing to hit.", lead=("left", ""), height={"riders": "quarter"})
    sh("WS", 4, "Shoot and gone.", mode="narrated", who=["riders"], place="ridge", src="keyframe",
       act=("riders", "sit their horses on the crest", "swing their bows up and loose arrows high", "hold the bows up as the arrows fly"),
       lead=("right", "where they wheel"),
       height={"riders": "third"})
    sh("MS", 4, "Brun's view of the war.", who=["brun"], 
       act=("brun", "marches with his musket on his shoulder", "slaps at the air with one hand", "marches on"),
       line=("brun", "self", "Shoot, run. Shoot, run. Like flies.", "bitter, tired"), lead=("none", ""))
    sh("MS", 4, "The chase wears the French down.", mode="narrated", who=["brun"], src="keyframe",
       act=("brun", "marches with his head down", "stumbles and catches himself on his musket", "marches on, limping"),
       narr="Every day took them further from the fog.", claims=["I01"],
       lead=("right", "where he marches"))
    sh("MCU", 4, "Napoleon decides.", mode="narrated", tier="light", who=["napoleon"],
       act=("napoleon", "rides with his eyes on the ridge", "lifts his chin sharply", "keeps his eyes on the ridge"),
       lead=("right", "the ridge"))
    sh("MS", 6, "Napoleon finds his move.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"}, facing={"kemal": "napoleon", "napoleon": "kemal"}, 
       act=("napoleon", "rides beside the mameluke", "jabs his riding crop toward a valley ahead", "holds the crop out"),
       line=("napoleon", "kemal", "If he won't come to me, I'll give him a reason.", "a sudden grin in the voice"), lead=("none", ""))
    sh("INSERT", 4, "A line drawn in the dust.", mode="insert", src="keyframe", place="tent", light="warm candlelight",
       act=("napoleon", "a gloved finger draws a curving line in the dust on a wagon board",
            "the finger stabs down hard at the end of the line", "the finger rests on the spot"),
       narr="He set a trap.", foley=["a finger tapping wood"])
    sh("WS", 5, "The bait: one division alone.", mode="establish", who=["infantry"], place="valley", src="keyframe",
       narr="One division as bait in an open valley. The guns hidden behind the hill.",
       rel=["bronze cannons stand hidden behind the low hill on the left", "the division stands in front of the low hill"],
       height={"infantry": "third"})
    sh("MS", 5, "The guns wait behind the crest.", mode="narrated", who=["gunners"], place="valley",
       act=("gunners", "crouch behind the crest beside a cannon", "pull a grey cloth over the barrel", "lie flat beside the wheels"),
       narr="To spring it, he took every fighting man out of camp.", lead=("right", "the crest"),
       rel=["the grassy crest rises in front of the cannon"])
    sh("MS", 3, "Someone watches them hide the guns.", tier="light", who=["bayan"], place="valley", src="keyframe",
       on={"bayan": "lying flat in the tall grass"},
       act=("bayan", "lies flat in the tall grass on the far slope", "pushes the grass apart with both hands and stares",
            "lets the grass close again"), lead=("left", "the hidden guns"), foley=["grass rustling"])
    sh("WS", 4, "The wagons, nearly unguarded.", mode="establish", tier="light", who=["drummer"], place="wagons",
       src="keyframe", on={"drummer": "sitting on a wagon step"}, height={"drummer": "quarter"},
       narr="The wagons stayed behind, with a handful of guards.", rel=["the covered wagons stand behind the drummer"])
    sh("WS", 3, "Far from the valley, riders walk their horses along a dry gully.", mode="establish", tier="light",
       who=["riders"], place="steppe", light="hazy afternoon light", src="keyframe",
       on={"riders": "walking beside their horses in a dry gully"},
       act=("riders", "lead their horses along the bottom of a dry gully", "duck their heads below the rim",
            "walk on in single file"), lead=("right", "where they walk"), height={"riders": "third"},
       foley=["hooves on dry earth"])
    sh("EWS", 4, "The khan sees exactly that.", mode="narrated", tier="light", who=["genghis"], place="ridge",
       light="red evening light", src="keyframe", on={"genghis": "sitting astride a short dun horse"},
       act=("genghis", "sits his horse on the ridge", "raises a hand and closes it into a fist", "lowers the fist slowly"),
       narr="The khan had been waiting for exactly that.", lead=("left", "the valley"), height={"genghis": "quarter"})
    # ---- 10. central scene (8:15-10:45): the battle Napoleon wanted ---------------------------------------------
    ep.scene("S10", "valley", light="bright afternoon sun, drifting gun smoke", ambience="wind, distant horns, horses",
             stage={"napoleon": ("center", "right", "sitting astride a white horse", ""),
                    "kemal": ("left", "right", "sitting astride a grey horse", ""),
                    "murat": ("left", "right", "sitting astride a big bay horse", ""),
                    "brun": ("center", "right", "standing inside the square", ""),
                    "drummer": ("center", "camera", "standing inside the square", ""),
                    "infantry": ("left", "right", GRASS, ""), "gunners": ("left", "right", GRASS, ""),
                    "riders": ("right", "left", "sitting on horses on the hillside", ""),
                    "genghis": ("right", "left", "sitting astride a short dun horse", ""),
                    "subutai": ("left", "right", "sitting astride a black horse", "")})
    sh("EWS", 4, "At last, the khan comes.", mode="establish", who=["infantry", "riders"],
       act=("riders", "appear along both hilltops", "pour down the slopes in a brown flood", "spread out across the valley floor"),
       rel=["the French division stands on the valley floor", "the low hills rise on both sides of the valley"],
       lead=("left", "where the riders pour down"), height={"infantry": "quarter", "riders": "quarter"},
       where={"infantry": "center", "riders": "right_back"}, loud="a horn blast")
    sh("MS", 4, "The emperor's first order.", who=["napoleon"], src="keyframe",
       act=("napoleon", "sits his horse on the hill", "stands in his stirrups and flings his arm up", "holds the arm high"),
       line=("napoleon", "room", "Squares! Form squares!", "a parade-ground shout"), lead=("above", "where his arm goes"))
    sh("WS", 4, "The square forms.", mode="establish", who=["infantry"], src="keyframe",
       act=("infantry", "hurry into a hollow square", "slam their musket butts down with bayonets out",
            "kneel in four walls of bayonets"),
       rel=["the square stands on the open grass"], lead=("none", ""), height={"infantry": "third"},
       foley=["bayonets clicking"])
    sh("MS", 3, "At the wagons, the drummer hears hooves.", tier="light", who=["drummer"], place="wagons",
       light="bright afternoon sun", src="keyframe", on={"drummer": "sitting on a wagon step"},
       act=("drummer", "sits on the wagon step polishing his drum", "jerks his head up toward the hills",
            "freezes with the cloth in his hand"), lead=("right", "the hills"), foley=["far-off hooves growing louder"])
    sh("WS", 4, "The arrow storm.", mode="establish", who=["riders"], src="keyframe",
       act=("riders", "ride past the square at a distance", "swing their bows up and loose a dark cloud of arrows",
            "ride on, reaching for more arrows"), lead=("left", "where the arrows fly"), height={"riders": "third"},
       loud="hundreds of arrows hissing")
    sh("INSERT", 3, "Inside the square.", mode="insert",
       act=("infantry", "arrows rain down into the square", "an arrow knocks a shako off a soldier's head",
            "the shako rolls on the grass"), foley=["arrows thudding"])
    sh("MS", 4, "Brun closes the gap.", who=["brun"], src="keyframe",
       act=("brun", "stands in the square's front rank", "grabs a soldier by the collar and pulls him into the gap",
            "holds him in place"), line=("brun", "room", "Close up! Close the gap!", "a roar"), lead=("left", "the gap"),
       rel=["a line of kneeling soldiers stands in front of the grenadier"])
    sh("MCU", 5, "Steady.", who=["brun"],
       act=("brun", "wipes sweat from his eyes", "raises his musket over his head", "holds the musket up"),
       line=("brun", "room", "Steady, lads. They can't stay up there all day.", "loud, steady"), lead=("none", ""))
    sh("WS", 3, "The camp guards fire one ragged volley.", mode="establish", who=["guards"], place="wagons",
       light="bright afternoon sun", src="keyframe",
       act=("guards", "stand between two wagons with their muskets up", "fire a thin ragged volley in a puff of smoke",
            "fumble with their ramrods to reload"), lead=("right", "where the riders come"), height={"guards": "third"},
       loud="a thin musket volley")
    sh("MCU", 3, "A drum keeps the square together.", who=["drummer"],
       act=("drummer", "stands stiff with his drum", "slams his sticks down in a fast roll", "keeps the roll going"),
       lead=("none", ""), loud="a fast drum roll")
    sh("EWS", 4, "The heavy riders form for the charge.", mode="establish", who=["riders"], src="keyframe",
       act=("riders", "lower long lances in a line", "kick their horses forward into a charge", "thunder toward the square"),
       lead=("left", "where they charge"), height={"riders": "quarter"}, loud="a wall of hooves")
    sh("MS", 4, "Front rank, kneel.", who=["brun"], 
       act=("brun", "stands behind the front rank", "swings his musket down and points it forward", "holds the aim"),
       line=("brun", "room", "Front rank, kneel! Second rank, present!", "a drill roar"), lead=("none", ""))
    sh("MS", 4, "Hold.", who=["brun"],
       act=("brun", "raises his hand high", "shakes the raised hand once", "keeps the hand up, trembling"),
       line=("brun", "room", "Hold your fire. Hold.", "low, tight"), lead=("none", ""))
    sh("MWS", 3, "The front rank aims.", who=["infantry"], src="keyframe",
       act=("infantry", "aim their muskets over the bayonets", "jerk their cheeks down onto the stocks", "hold their aim"),
       lead=("right", "where they aim"))
    sh("CU", 3, "Fire.", who=["brun"],
       act=("brun", "holds his raised hand", "drops the hand like an axe", "keeps the hand down"),
       line=("brun", "room", "Fire!", "a bellow"), lead=("below", "where the hand drops"))
    sh("WS", 4, "The volley at thirty metres.", mode="establish", who=["infantry"], src="keyframe",
       act=("infantry", "kneel behind their bayonets", "fire one volley in a wall of white smoke",
            "lower the muskets in the smoke"), lead=("right", "where the smoke rolls"), loud="one huge musket volley")
    sh("WS", 4, "The charge splits around the square.", mode="establish", who=["riders"], src="keyframe",
       key="charge_split",
       act=("riders", "charge out of the smoke", "swerve around the corners of the square and pull up hard",
            "wheel away into the grass"), lead=("right", "where they wheel"), height={"riders": "third"})
    sh("MCU", 4, "The veteran's joy.", who=["brun"],
       act=("brun", "lowers his musket", "throws his head back and laughs", "grins through the smoke"),
       line=("brun", "room", "Ha! Like a rock!", "laughing"), lead=("none", ""))
    sh("MS", 4, "Now the trap closes.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"},
       facing={"kemal": "napoleon", "napoleon": "kemal"}, src="keyframe",
       act=("napoleon", "lowers his telescope", "points at the crest behind them", "keeps the arm out"),
       line=("napoleon", "kemal", "Now. Signal the guns.", "calm, quick"), lead=("left", "the crest"))
    sh("WS", 4, "The hidden guns roll over the crest.", mode="establish", who=["gunners"], src="keyframe",
       act=("gunners", "push a bronze cannon over the crest", "heave the wheels forward and swing the barrel down",
            "crouch beside the aimed cannon"), lead=("right", "where the barrel points"), height={"gunners": "third"},
       foley=["wheels grinding"])
    sh("CU", 4, "Canister.", who=["napoleon"], 
       act=("napoleon", "watches the riders come", "drops his hand down hard", "keeps the hand low"),
       claims=["C05"], line=("napoleon", "room", "Canister. Six hundred. Now!", "fast, hard"), lead=("none", ""))
    sh("MWS", 3, "Canister.", who=["gunners"],
       act=("gunners", "crouch with hands over their ears", "the cannon jerks back in a blast of smoke",
            "the crew stand up in the smoke"), lead=("right", "where the smoke blows"), loud="a cannon blast")
    sh("EWS", 4, "Six hundred metres: the Mongol mass breaks.", mode="establish", who=["riders"], src="keyframe",
       key="canister_hit",
       act=("riders", "mass together on the slope", "break apart and scatter under a hail of shot",
            "spread out up the hill"), lead=("right", "where they scatter"), height={"riders": "quarter"},
       loud="a crack of shot")
    sh("MCU", 4, "This is how Europe learned.", who=["napoleon"],
       act=("napoleon", "watches through the smoke", "slaps his gloved hand against his thigh", "sits back in the saddle",
            "a thin smile pulls at his mouth"),
       line=("napoleon", "room", "That is how Europe learned.", "quiet, chin high"), lead=("none", ""))
    sh("WS", 4, "Behind the hills, other riders reach the wagons.", mode="establish", who=["riders"], place="wagons", key="wagons_burn",
       src="keyframe", act=("riders", "ride hard between the wagons", "hurl burning torches onto the canvas covers",
                             "wheel round as the canvas catches"),
       rel=["the covered wagons stand behind the riders"], lead=("right", "where they wheel"), height={"riders": "third"},
       loud="fire roaring up")
    sh("MS", 4, "Petit runs through the fire, drumming the alarm.", who=["drummer"], place="wagons",
       light="orange firelight and smoke", src="keyframe",
       act=("drummer", "runs between the burning wagons with his drum", "slams both sticks down on the drum as he runs",
            "stops and stares at the flames, sticks raised"),
       line=("drummer", "room", "Alarm! Alarm!", "a cracked shout"), lead=("right", "where he runs"), loud="a drum alarm")
    sh("MS", 5, "Murat smells the kill.", who=["murat", "napoleon"], where={"murat": "left", "napoleon": "right"},
       facing={"murat": "napoleon", "napoleon": "murat"},
       act=("murat", "rides up beside the emperor", "raises his sabre and points it at the hills", "keeps it pointed"),
       line=("murat", "napoleon", "Let me finish them, Sire! Now, while they run!", "begging, loud"),
       lead=("right", "the hills"))
    sh("MS", 4, "Napoleon has learned the khan's lesson.", who=["murat", "napoleon"],
       where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"},
       act=("napoleon", "turns to the marshal", "grabs the marshal's bridle", "holds the bridle tight"),
       line=("napoleon", "murat", "No. They want you to chase.", "hard, low"), lead=("left", "the marshal's horse"))
    sh("MCU", 4, "Murat hates it.", who=["murat"],
       act=("murat", "glares at the emperor", "tears off his plumed hat and slaps it against his knee",
            "holds the crushed hat"), lead=("none", ""))
    sh("WS", 4, "On the far ridge, the khan watches.", mode="establish", who=["subutai", "genghis"], place="ridge",
       src="keyframe", where={"subutai": "left", "genghis": "right"}, facing={"subutai": "genghis", "genghis": "camera"},
       act=("genghis", "sits his horse on the far ridge", "raises his open hand to hold his riders back",
            "keeps the hand raised"),
       rel=["the smoky valley lies below the ridge in front of them"], lead=("none", ""), height={"genghis": "third"})
    sh("OTS", 4, "Subutai sees a defeat.", who=["genghis", "subutai"], over="genghis", place="ridge",
       act=("subutai", "watches the valley", "jabs a finger down at the smoke", "keeps the finger pointed"),
       line=("subutai", "genghis", "He is winning, Khan.", "tense"), lead=("none", ""))
    sh("OTS", 6, "The khan sees the opposite.", who=["subutai", "genghis"], over="subutai", place="ridge",
       act=("genghis", "keeps his eyes on the valley", "drops his raised hand to the saddle", "rests the hand there",
            "his face stays perfectly calm"),
       line=("genghis", "subutai", "Let him. He is winning the wrong thing.", "slow, almost gentle"), lead=("none", ""))
    sh("CU", 4, "The khan looks behind the French.", tier="light", who=["genghis"], place="ridge",
       act=("genghis", "looks at the valley", "lifts his chin toward the far smoke", "holds the look"),
       lead=("left", "where he looks"))
    sh("MS", 4, "Kemal sees it first.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"},
       facing={"kemal": "napoleon", "napoleon": "kemal"},
       act=("kemal", "twists round in the saddle", "points back over the hills", "keeps the arm out"),
       line=("kemal", "napoleon", "Sire. Smoke. Behind us.", "urgent, quiet"), lead=("left", "where he points"))
    sh("CU", 3, "Napoleon turns.", who=["napoleon"],
       act=("napoleon", "faces the valley", "jerks round in the saddle", "stares back over the hills"),
       line=("napoleon", "self", "What is that?", "sharp"), lead=("left", "where he turns"))
    sh("EWS", 4, "Black smoke where the camp was.", mode="establish", tier="hold", who=[], place="steppe",
       light="bright afternoon sun", src="keyframe", cam="push_in", end="the black smoke columns filling the sky",
       rel=["black smoke columns rise behind the low hills"])
    sh("MS", 4, "The name for it.", who=["kemal", "napoleon"], where={"kemal": "left", "napoleon": "right"},
       facing={"kemal": "napoleon", "napoleon": "kemal"},
       act=("kemal", "lowers his arm", "drops his head", "keeps his head down"),
       line=("kemal", "napoleon", "Sire. That is our camp. The wagons.", "barely audible"), lead=("none", ""))
    sh("CU", 4, "The emperor understands.", tier="full", who=["napoleon"],
       act=("napoleon", "stares at the smoke", "drops the reins from his hands", "sits with empty hands",
            "his mouth falls open and his eyes go flat"), lead=("none", ""))
    # ---- 11. turning point (10:45-11:15): the won field ---------------------------------------------------------
    ep.scene("S11", "valley", light="grey light through drifting smoke", ambience="wind, a single crow, silence",
             stage={"napoleon": ("left", "right", GRASS, ""), "brun": ("right", "left", GRASS, ""), "murat": ("right", "left", GRASS, "")})
    sh("WS", 5, "One still frame: the winner on his field.", mode="establish", tier="hold", who=["napoleon"],
       cam="push_in", end="the general small and alone in the middle of the frame",
       rel=["smoke drifts behind the general"], height={"napoleon": "quarter"})
    sh("MCU", 5, "Two words.", who=["napoleon"],
       act=("napoleon", "stands staring at the smoke", "lifts his chin and swallows", "holds very still"),
       line=("napoleon", "self", "We won.", "flat, empty"), lead=("none", ""))
    sh("MS", 5, "What victory bought.", who=["napoleon", "brun"],
       act=("brun", "holds out a black burnt loaf with both hands", "breaks the loaf open and black crumbs fall",
            "holds the two halves out"),
       line=("brun", "napoleon", "Sire. This is what's left of the bread.", "quiet"), lead=("below", "where the crumbs fall"))
    sh("MS", 4, "How much is left.", who=["napoleon", "brun"], 
       act=("napoleon", "looks at the loaf", "lifts his eyes to the grenadier", "holds the look"),
       line=("napoleon", "brun", "How much is left?", "flat"), lead=("none", ""))
    sh("MS", 4, "The answer.", who=["napoleon", "brun"], 
       act=("brun", "holds out the black loaf", "jerks his head toward the horse lines", "lowers his hands"),
       line=("brun", "napoleon", "That, Sire. And the horses.", "quiet"), lead=("none", ""))
    sh("CU", 4, "The emperor looks down.", tier="light", who=["napoleon"],
       act=("napoleon", "looks at the loaf", "drops his eyes and closes them", "keeps the eyes shut"), lead=("none", ""))
    sh("MS", 4, "Murat says it at last.", who=["napoleon", "murat"], 
       act=("murat", "walks up beside the emperor", "pulls off his plumed hat", "holds the hat at his side"),
       line=("murat", "napoleon", "They never wanted the field, Sire.", "subdued, for once"), lead=("none", ""))
    sh("EWS", 4, "The wagons, burned to their ribs.", mode="establish", tier="hold", who=[], place="wagons",
       light="grey light through drifting smoke", src="keyframe", cam="pull_out",
       end="the rows of burnt wagon frames small on the steppe",
       rel=["thin smoke rises above the burnt wagon frames"])
    # ---- 12. fallout (11:15-12:00) -------------------------------------------------------------------------------
    ep.scene("S12", "valley", light="cold grey evening light", ambience="wind over open grass",
             stage={"riders": ("right", "left", "sitting on horses in the grass", ""),
                    "infantry": ("left", "right", "sitting on the burnt grass", ""),
                    "napoleon": ("right", "left", GRASS, ""), "murat": ("left", "right", GRASS, ""),
                    "bars": ("right", "left", "sitting astride a short shaggy horse", "")})
    sh("EWS", 4, "The battlefield, quiet.", mode="establish", tier="hold", who=[], cam="pan_left",
       end="the empty valley under the evening sky", narr="On paper, it was a victory.",
       rel=["dropped lances and arrows lie on the trampled grass"])
    sh("WS", 4, "The Mongol losses are real.", mode="narrated", tier="light", who=["riders"], place="mgcamp", src="keyframe",
       act=("riders", "ride slowly into camp leading riderless horses", "lift a wounded rider down from a saddle",
            "lay him on a felt blanket"),
       narr="The khan left hundreds of riders in that valley.", claims=["I03"], lead=("left", "where they ride in"),
       height={"riders": "third"})
    sh("MS", 5, "And not one horse he couldn't replace.", mode="narrated", who=["riders"], place="mgcamp",
       act=("riders", "lead fresh horses out of a big herd", "swing up onto the fresh horses", "sit them, ready"),
       narr="But he had not lost a single horse he could not replace.", claims=["I03"], lead=("right", "the herd"))
    sh("WS", 5, "The French camp in ash.", mode="narrated", tier="light", who=["infantry"], place="wagons", src="keyframe",
       act=("infantry", "sit in the ash between the burnt wagons", "lift empty tin plates and drop them", "sit with empty hands"),
       narr="The French had lost what no battle wins back: their food.", lead=("none", ""),
       height={"infantry": "third"})
    sh("MS", 4, "The horses go into the pot.", mode="narrated", who=["infantry"], place="wagons",
       act=("infantry", "kneel beside a dead horse with knives", "pull the hide back from the meat", "work on with bent heads"),
       narr="Within days, they were eating their horses.", claims=["I03"], lead=("none", ""),
       on={"infantry": "kneeling on the burnt grass"})
    sh("MCU", 4, "The emperor, beaten by a won battle.", mode="narrated", tier="light", who=["napoleon"], place="tent",
       light="one candle", src="keyframe",
       act=("napoleon", "sits by one candle", "drops his face into his hands", "stays bent over"),
       lead=("none", ""))
    sh("WS", 4, "An invitation arrives.", mode="narrated", who=["bars"], place="camp", src="keyframe",
       act=("bars", "rides slowly into the camp", "raises a white felt banner on a pole", "sits holding the banner high"),
              lead=("left", "where he rides in"), height={"bars": "third"}, foley=["a banner flapping"])
    sh("MS", 5, "Murat smells a trap.", who=["murat", "napoleon"], place="camp", where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"}, 
       act=("murat", "steps between the emperor and the rider", "throws an arm out across his chest", "keeps the arm out"),
       line=("murat", "napoleon", "It's a trap, Sire. He'll cut your throat.", "urgent"), lead=("none", ""))
    sh("MS", 5, "Napoleon goes anyway.", who=["murat", "napoleon"], place="camp", where={"murat": "left", "napoleon": "right"}, facing={"murat": "napoleon", "napoleon": "murat"}, 
       act=("napoleon", "puts on his hat", "pushes the marshal's arm aside", "steps past him"),
       line=("napoleon", "murat", "Everything here is a trap. I'm going.", "tired, certain"), lead=("none", ""))
    # ---- 13. scene 4, the final choice (12:00-13:30): the parley ------------------------------------------------
    ep.scene("S13", "yurt", light="warm firelight", ambience="a fire crackling, wind against felt",
             stage={"napoleon": ("left", "right", "standing on the carpet", ""),
                    "kemal": ("center", "right", "standing on the carpet", "holds his hands behind his back"),
                    "genghis": ("right", "left", "sitting cross-legged on a carpet", ""),
                    "bars": ("right_back", "left", "standing against the lattice wall", "holds his cap in his hands")})
    sh("WS", 4, "The emperor enters the khan's tent.", mode="establish", who=["napoleon", "kemal", "genghis", "bars"],
       act=("napoleon", "ducks in through the low felt door", "straightens up and pulls off his hat",
            "stands holding the hat at his side"),
       rel=["the low fire burns in front of the khan"], lead=("right", "the khan"), height={"napoleon": "third"})
    sh("OTS", 6, "The khan opens with a compliment.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "sits cross-legged by the fire", "raises a bowl of mare's milk toward his guest", "holds the bowl out"),
       line=("genghis", "napoleon", "Your men stand like rocks, and your iron tubes sing.", "warm, slow"), lead=("none", ""))
    sh("OTS", 5, "Napoleon answers with the grievance.", who=["genghis", "napoleon"], over="genghis",
       act=("napoleon", "ignores the bowl", "jabs his hat toward the khan", "lowers the hat"),
       line=("napoleon", "genghis", "And still you burned my bread.", "cold"), lead=("none", ""))
    sh("OTS", 6, "The khan names the difference between them.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "sets the bowl down", "lifts one finger and taps his own chest", "rests the hand on his knee"),
       line=("genghis", "napoleon", "You came to fight a battle. I came to win a war.", "even, slow"), lead=("none", ""))
    sh("CU", 4, "The hit lands.", tier="light", who=["napoleon"],
       act=("napoleon", "stares at the khan", "drops his eyes to the fire", "keeps his eyes down"), lead=("none", ""))
    sh("OTS", 6, "The offer.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "leans forward", "throws both hands wide over the fire", "holds the hands open"),
       claims=["C20"], line=("genghis", "napoleon", "Ride with me. I will give you a tumen. Ten thousand.", "generous, plain"),
       lead=("none", ""))
    sh("MS", 5, "Kemal: he means it.", who=["napoleon", "kemal"], where={"napoleon": "left", "kemal": "center"},
       facing={"napoleon": "genghis", "kemal": "napoleon"},
       act=("kemal", "leans in to the emperor's ear", "raises a hand beside his mouth", "keeps the hand up"),
       line=("kemal", "napoleon", "Sire, he means it. He gives armies to strangers.", "a whisper"), lead=("none", ""))
    sh("OTS", 6, "Napoleon will not serve.", who=["genghis", "napoleon"], over="genghis",
       act=("napoleon", "pulls his hat against his chest", "lifts his chin high", "holds the chin up",
            "his mouth sets in a hard line"),
       line=("napoleon", "genghis", "I have given orders to kings. I do not take them.", "clipped, chin high"),
       lead=("none", ""))
    sh("MCU", 3, "The interpreter swallows.", tier="light", who=["bars"], on={"bars": "standing against the lattice wall"},
       act=("bars", "stands against the lattice wall", "pulls his cap tight against his chest with both fists", "holds the cap tight"),
       lead=("none", ""))
    sh("OTS", 5, "Then go.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "sits back on the carpet", "shrugs and throws one hand toward the door", "rests the hand"),
       line=("genghis", "napoleon", "Then go back into your fog.", "light, final"), lead=("none", ""))
    sh("MCU", 5, "And a gift that is a price.", who=["genghis"],
       act=("genghis", "picks up the bowl", "raises the bowl and drinks", "lowers the bowl"),
       line=("genghis", "room", "I will give you sheep to reach it.", "calm"), lead=("none", ""))
    sh("OTS", 4, "Napoleon asks the real question.", who=["genghis", "napoleon"], over="genghis",
       act=("napoleon", "stares at the khan", "lifts one eyebrow and jabs his hat forward", "holds still"),
       line=("napoleon", "genghis", "And the price?", "suspicious"), lead=("none", ""))
    sh("OTS", 6, "The price: the guns, and a teacher.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "sets the bowl down", "raises two fingers", "holds the fingers up"),
       line=("genghis", "napoleon", "Two of your iron tubes. And a gunner to teach mine.", "plain"), lead=("none", ""))
    sh("CU", 4, "The longest silence of his life.", tier="light", who=["napoleon"],
       act=("napoleon", "stands without moving", "lifts his eyes to the smoke hole above", "keeps the eyes up",
            "his jaw works once"), lead=("above", "where he looks"))
    sh("MS", 5, "Kemal says what the men cannot.", who=["napoleon", "kemal"], where={"napoleon": "left", "kemal": "center"},
       facing={"napoleon": "genghis", "kemal": "napoleon"},
       act=("kemal", "steps close to the emperor", "drops his voice and bends his head", "stays bent close"),
       line=("kemal", "napoleon", "Sire. The men are eating grass.", "very quiet"), lead=("none", ""))
    sh("MS", 3, "Outside, they are.", tier="light", who=["brun", "drummer"], place="wagons", light="cold grey light",
       src="keyframe", where={"brun": "left", "drummer": "right"}, facing={"brun": "drummer", "drummer": "brun"},
       on={"brun": "sitting on the burnt grass", "drummer": "sitting on the burnt grass"},
       act=("brun", "sits in the ash beside a cold fire", "pulls up a fistful of grass and chews it",
            "chews slowly, staring at nothing"), react=[("drummer", "watches him chew")], lead=("none", ""))
    sh("OTS", 6, "The choice.", who=["genghis", "napoleon"], over="genghis",
       act=("napoleon", "pulls off one glove", "slaps the glove down on the carpet", "stands with the bare hand open"),
       line=("napoleon", "genghis", "Two guns. Not one more.", "slow, each word paid for"), lead=("below", "where the glove lands"),
       foley=["leather on carpet"])
    sh("MCU", 4, "The khan's smile.", tier="light", who=["genghis"],
       act=("genghis", "looks at the glove", "lifts the corner of his mouth into a slow smile", "holds the smile"),
       lead=("none", ""))
    sh("OTS", 6, "The khan's last lesson.", who=["napoleon", "genghis"], over="napoleon",
       act=("genghis", "picks up the glove", "lifts the glove and holds it out to its owner", "keeps holding it out"),
       line=("genghis", "napoleon", "You lost nothing today but pride. Pride eats too much grass.", "kind, amused"),
       lead=("none", ""))
    sh("WS", 4, "Napoleon takes his glove and goes.", mode="establish", who=["napoleon", "kemal", "genghis", "bars"],
       exit=True, act=("napoleon", "takes the glove and puts his hat on", "turns and pushes out through the felt door",
                       "the felt flap swings shut behind him"),
       lead=("left", "the door"), height={"napoleon": "third"}, foley=["felt flapping"])
    sh("WS", 4, "The price, paid: two guns go to the khan.", mode="establish", who=["gunners", "riders"], place="steppe",
       light="pale morning light", src="keyframe", where={"gunners": "left", "riders": "right"},
       facing={"gunners": "right", "riders": "right"},
       on={"gunners": GRASS, "riders": "sitting on horses on the grass"},
       exit=True, act=("riders", "loop ropes round two bronze cannons", "drag the cannons away across the grass",
            "ride off with the cannons rolling behind"), react=[("gunners", "stand watching with their caps in their hands")],
       lead=("right", "where they drag them"), height={"gunners": "third", "riders": "third"},
       foley=["wheels creaking", "ropes straining"])
    # ---- 14. the answer (13:30-14:30) ----------------------------------------------------------------------------
    ep.scene("S14", "valley", light="pale morning light", ambience="wind, then a city's distant bells",
             stage={"infantry": ("left", "right", GRASS, ""), "riders": ("right", "left", "sitting on horses on the skyline", ""),
                    "napoleon": ("center", "right", "sitting astride a white horse", ""),
                    "brun": ("center", "right", "standing in the snow", ""),
                    "kemal": ("left", "right", "standing on a wooden floor", "")})
    sh("WS", 5, "The question again.", mode="narrated", tier="light", who=["infantry"],
       act=("infantry", "stand in a square on the grass", "raise their muskets to the shoulder", "hold them steady"),
       narr="So: can the man who conquered Europe beat the man who conquered Asia?", lead=("right", "where they aim"),
       height={"infantry": "third"})
    sh("WS", 5, "Yes, on a battlefield.", mode="narrated", who=["infantry"],
       act=("infantry", "kneel behind their bayonets", "jerk their muskets up and fire one volley in a wall of smoke", "lower the muskets"),
       narr="On a battlefield, yes. A square and a battery broke the charge.", claims=["C05", "C07"],
       lead=("right", "where the smoke rolls"), height={"infantry": "third"}, loud="a musket volley")
    sh("EWS", 5, "No, in a campaign.", mode="narrated", tier="light", who=["riders"], place="ridge", src="keyframe",
       act=("riders", "sit their horses on the skyline", "raise their bows all at once", "hold the bows against the sky"),
       narr="In a campaign, no. The khan never needed the battle. He needed the army's dinner.",
       lead=("above", "where the bows rise"), height={"riders": "quarter"})
    sh("WS", 4, "The fog comes back.", mode="narrated", who=["napoleon", "infantry"], place="fog", src="keyframe",
       act=("napoleon", "rides at the head of the column", "raises his arm and points into the fog",
            "rides on with the arm still raised"),
       narr="Then the fog came back, and the army marched into it.", claims=["I01"],
       rel=["the column of infantry marches behind the general"], lead=("right", "the fog"), height={"napoleon": "third"})
    sh("EWS", 4, "Moscow, on the right day.", mode="establish", tier="hold", who=[], place="moscow", light="pale morning light",
       src="keyframe", cam="push_in", end="the onion domes filling the frame",
       narr="It came out on the road to Moscow, on the fourteenth of September, 1812.", claims=["C02"])
    sh("MS", 4, "An empty city.", mode="narrated", who=["brun"], place="moscow", light="pale morning light",
       on={"brun": "standing on a wooden street"},
       act=("brun", "walks into an empty wooden street", "stops and swings round, looking at the shut windows",
            "stands with his musket lowered"),
       narr="The city was almost empty. The Russian army had pulled out, and Moscow burned.", claims=["C12"],
       lead=("right", "the empty street"))
    sh("MS", 4, "Kemal sees the khan's move again.", who=["kemal", "napoleon"], place="moscow", light="orange firelight", on={"kemal": "standing on a wooden floor", "napoleon": "standing on a wooden floor"}, where={"kemal": "left", "napoleon": "right"}, facing={"kemal": "napoleon", "napoleon": "kemal"}, 
       act=("kemal", "stands at the window beside him", "points out at the flames", "lowers the arm"),
       line=("kemal", "napoleon", "Sire. They burned their own city.", "hushed"), lead=("none", ""))
    sh("MS", 4, "Napoleon understands.", who=["kemal", "napoleon"], place="moscow", light="orange firelight", on={"kemal": "standing on a wooden floor", "napoleon": "standing on a wooden floor"}, where={"kemal": "left", "napoleon": "right"}, facing={"kemal": "napoleon", "napoleon": "kemal"}, 
       act=("napoleon", "stares at the flames", "drops his hands onto the sill", "leans on the sill"),
       line=("napoleon", "kemal", "Then they learned it from the khan.", "very quiet"), lead=("none", ""))
    sh("MCU", 4, "The tsar refuses.", mode="narrated", tier="light", who=["napoleon"], place="moscow", light="orange firelight",
       src="keyframe", on={"napoleon": "standing at a tall window"},
       act=("napoleon", "stands at a tall window", "drops a folded letter onto the sill", "stares out at the flames"),
       narr="The tsar refused to talk.", claims=["C12"], lead=("right", "the window"))
    sh("WS", 4, "The retreat.", mode="narrated", who=["infantry"], place="fog", light="grey snow light", src="keyframe",
       on={"infantry": "standing in deep snow"},
       act=("infantry", "trudge through falling snow", "stumble and pull each other up", "march on, bent over"),
       narr="About five weeks later, Napoleon marched out, and the long retreat began.", claims=["C12"],
       lead=("left", "where they march"), height={"infantry": "third"}, foley=["boots in snow"])
    sh("MS", 4, "The uncertain count.", mode="narrated", tier="light", who=["brun"], place="fog", light="grey snow light",
       on={"brun": "standing in deep snow"},
       act=("brun", "stands in the snow", "lifts snow off his bearskin and shakes it off", "stands still"),
       narr="How many came home is still argued over. The counts do not agree.", lead=("none", ""))
    # ---- 15. callback (14:30-14:45) -----------------------------------------------------------------------------
    ep.scene("S15", "moscow", light="orange firelight at night", ambience="a city burning, a far drum",
             stage={"napoleon": ("center", "right", "standing at a tall window", ""),
                    "drummer": ("center", "right", "standing on a wooden street", "")})
    sh("INSERT", 3, "The drumstick stops, again.", mode="insert",
       act=("drummer", "a wooden drumstick hangs above a French drum", "the drumstick strikes the drum skin twice",
            "the drumstick stops in mid-air, shaking"), loud="two drum beats")
    sh("MCU", 4, "He has seen this fire.", mode="narrated", tier="light", who=["napoleon"], src="keyframe",
       act=("napoleon", "watches the flames from the window", "lifts his chin slowly", "holds still"),
       narr="He had seen a fire like this before.", lead=("right", "the flames"))
    sh("ECU", 5, "Burning wagons in his eyes.", mode="narrated", tier="light", who=["napoleon"],
       act=("napoleon", "stares without blinking", "narrows his eyes as the flames jump", "keeps the eyes narrowed"),
       narr="Five hundred and eighty-nine years earlier.", claims=["C21", "I01"], lead=("none", ""))
    # ---- 16. channel pointer (14:45-15:00) ----------------------------------------------------------------------
    ep.scene("S16", "stoneage", light="warm campfire light", ambience="a crackling campfire",
             stage={"geniuses": ("center", "camera", "sitting on rocks around the fire", ""),
                    "stranded": ("center", "camera", "standing on the snow", ""),
                    "genghis": ("center", "right", "sitting cross-legged on a carpet", "")})
    sh("WS", 5, "The channel: the Stone Age.", mode="narrated", tier="light", who=["geniuses"],
       act=("geniuses", "sit around the campfire", "lift burning sticks and wave them at the dark", "hold the sticks up"),
       narr="On this channel, a hundred geniuses are already waiting for you in the Stone Age.", claims=["CH1"],
       lead=("none", ""), height={"geniuses": "third"})
    sh("WS", 5, "Coming: the Ice Age.", mode="narrated", tier="light", who=["stranded"], place="iceage",
       light="cold grey light", src="keyframe",
       act=("stranded", "huddle together on the snow", "raise their arms against a gust of snow", "huddle closer"),
       narr="Next: a hundred people dropped into the Ice Age. And worlds all the way to the future.",
       claims=["CH1"], lead=("none", ""), height={"stranded": "third"})
    sh("MS", 4, "The khan with a French cannonball: one last wink.", mode="narrated", who=["genghis"], place="yurt",
       light="warm firelight", src="keyframe",
       act=("genghis", "holds a heavy iron cannonball in one hand", "tosses the cannonball up and catches it",
            "weighs the ball in his palm", "a slow smile spreads under his beard"),
       narr="Subscribe if you don't want to miss them.", lead=("above", "where the ball goes"))
