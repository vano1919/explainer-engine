LIGHTS = {1: "hot neon pink and cyan signs against a soft sunset-orange sky, humid haze",
          2: "night street lit by neon pink and cyan signs, wet asphalt reflections, deep blue shadows",
          3: "low sunset-orange sun, pink clouds, long warm shadows",
          4: "a single warm desk lamp, amber pool of light, deep teal shadows",
          5: "night street lit by neon pink and cyan signs, wet asphalt reflections, deep blue shadows",
          6: "hard white subtropical noon sun, short shadows, cyan sky",
          7: "hot neon pink and cyan signs against a soft sunset-orange sky",
          8: "a single warm desk lamp, amber pool of light, deep teal shadows",
          9: "low sunset-orange sun over a palm-lined causeway, pink clouds, long warm shadows"}
used = set()
LIB = {}
def P(pid):
    if pid in used or pid in LIB:
        return pid
    used.add(pid)
    return PICS[pid]
def add(pid, subject, beat=None, **kw):
    sub = subject + (", " + LIGHTS[beat] if beat and kw.get("engine", "pod_ref") == "pod_ref" else "")
    PICS[pid] = pic(pid, sub, **kw)
def card(pid, name):
    LIB[pid] = {"file": f"{pid}.png", "engine": "existing", "heroes": [], "shows": []}

for c in ["sc_all", "sc_capone", "sc_vito", "sc_mizuno", "sc_shelby", "sc_capone_out", "sc_vito_out", "sc_mizuno_out", "sc_final"]:
    card(c, c)

# --- portraits (premium: identity references reused by every hero picture, the Shorts and the thumbnail) ------------------
for h in CARDS:
    pass
REASON = "identity reference reused by every picture of this hero in the video, the Shorts and the thumbnail"
add("p_capone", "character-select portrait, waist-up, facing slightly left with a confident half-smile, hat tilted, against a flat dark backdrop with one thin neon pink edge line, no buildings, no signs, no lettering, lit by soft neon pink and cyan rim light. The subject: " + CARDS["capone"], None, tier="premium", reason=REASON)
add("p_vito", "character-select portrait, waist-up, facing slightly right with a calm patient expression, one hand resting on the other, against a flat dark backdrop with one thin neon pink edge line, no buildings, no signs, no lettering, lit by soft neon pink and cyan rim light. The subject: " + CARDS["vito"], None, tier="premium", reason=REASON)
add("p_mizuno", "character-select portrait, waist-up, facing front with a composed neutral expression, briefcase held in front, against a flat dark backdrop with one thin neon pink edge line, no buildings, no signs, no lettering, lit by soft neon pink and cyan rim light. The subject: " + CARDS["mizuno"], None, tier="premium", reason=REASON)
add("p_shelby", "character-select portrait, waist-up, facing slightly left with a calm confident half-smile, hands in coat pockets, against a flat dark backdrop with one thin neon pink edge line, no buildings, no signs, no lettering, lit by soft neon pink and cyan rim light. The subject: " + CARDS["shelby"], None, tier="premium", reason=REASON)

# --- scene pictures ------------------------------------------------------------------------------------------------------
add("s01_skyline", "wide establishing view of an invented neon coastal city at sunset, a long palm-lined causeway leading to a skyline of stucco towers with wordless neon signs, speedboats on the bay, nobody in the foreground, a huge sense of heat and glow", 1, engine="gemini")
add("s01_phones", "tight insert, a forest of raised hands holding glowing phones toward the camera, screens lit neon cyan and pink, one lens in the middle, shaded faces behind", 1)
add("s01_four", "four tall silhouettes standing in a row on the causeway at sunset seen from behind, one in a white fedora and pinstripe suit, one in a dark double-breasted suit and homburg, one in a slim business suit with a briefcase, one in a long overcoat and flat cap, long shadows toward the viewer, phone lights glowing in the crowd beyond", 1)
add("s02_chairs", "an empty round table in a dim neon-lit back room with four empty chairs and a single unlit ceiling lamp, a stack of folded newspapers with no readable text on the table, ominous and quiet", 1)
add("s02_history", "tight insert, an old yellowed newspaper page whose headlines and columns are only grey bars and loose scribble, no letters or words at all, with a round rubber stamp mark made of plain rings, resting under a brass lamp", 4)
add("s08_paths", "four glowing neon corridors diverging from one starting line on wet asphalt at night, each corridor lit in a different colour, a single phone-screen eye at the far end of each", 2)
add("s08_eye", "tight insert, a phone camera lens as a huge glowing eye reflecting a neon street, tiny silhouettes of people reflected in the lens", 2)
add("c09_press", "a crowded 1930s city street at sunset, newspaper vendors in flat caps holding up front pages with wordless headline blocks, a long black car passing with a man in a white fedora waving from the back seat", 3, heroes=["capone"], costume=COSTUME["capone"])
add("c09_soup", "a long line of ordinary people in worn 1930s coats waiting at a soup-kitchen counter, a large pot steaming, the heavy-set boss in a cream suit ladling a bowl with a beaming showman's smile, a photographer's flash popping", 3, heroes=["capone"], costume=COSTUME["capone"])
add("c10_viral", "the heavy-set boss in a cream suit and white fedora handing out sandwiches on a neon boardwalk to a delighted crowd, every person holding a phone up to film him, he smiles broadly, a clearly comic moment", 3, heroes=["capone"], costume=COSTUME["capone"])
add("c10_plate", "tight insert, a phone screen filming the rear bumper of a long cream vintage car, a glowing red tracking box drawn around the blank licence plate, a cursor tapping it", 3)
add("c10_map", "wide top-down view of a neon city map on a phone screen, dozens of glowing pins converging on one small car icon, a thin red line tracing the route back to a single building", 3)
add("c11_ledger", "tight insert, a ledger book open under a warm desk lamp, a finger on one handwritten line of figures with no readable text, a fountain pen beside it", 4)
add("c11_agent", "a patient tax investigator in a rumpled grey suit and round glasses sitting at a desk piled with ledgers, a stamped line circled in red ink, a quiet moment of discovery under a warm desk lamp", 4)
add("c11_verdict", "a wide 1930s courtroom, the heavy-set boss in a cream suit small at the defence table, a judge's bench towering above him, jurors in rows, dust in the lamp light, a heavy silence", 4, heroes=["capone"], costume=COSTUME["capone"])
add("c12_palm", "a quiet white house on a palm-fringed island at sunset, an empty wooden chair on the veranda, calm water, a long pink horizon, an ending that feels peaceful and lonely", 4)
add("v13_table", "a candlelit family dinner table in a warm back room with a neon sign glowing through the window behind, the grey-haired patriarch seated at the head of the table with folded hands, calm and attentive, family silhouettes at the edges", 5, heroes=["vito"], costume=COSTUME["vito"])
add("v14_oil", "tight insert, wooden crates of olive-oil tins stacked on a neon pier at dusk, a stencil of an invented olive-branch mark, a forklift shadow, water reflecting the signs", 5)
add("v14_judge", "an older patriarch in a dark suit sharing a quiet handshake with a judge in a robe and a politician in a sash across a small table in a back room, all three smiling thinly, a sense of old obligations", 5, heroes=["vito"], costume=COSTUME["vito"])
add("v14_no", "across a small table a stranger in a flashy suit slides a thick envelope forward, the grey-haired patriarch calmly pushes it back with two fingers and a firm gentle look, a closed door behind him", 5, heroes=["vito"], costume=COSTUME["vito"])
add("v15_dock", "wide view of a neon harbour at night, a row of people on a railing all holding glowing phones toward a crate being loaded onto a truck, the crate stencilled with an olive-branch mark, red recording dots floating over their phones", 5)
add("v15_phone", "the grey-haired patriarch alone at a desk in a dim room staring at a black rotary telephone that does not ring, an untouched address book beside it, neon light striping the wall, a heavy loneliness", 5, heroes=["vito"], costume=COSTUME["vito"])
add("v16_garden", "a vegetable garden of staked tomato plants at golden sunset with a single empty wooden chair, long shadows, a peaceful ending", 5)
add("m17_card", "a composed businessman in a slim charcoal suit offering a plain white business card with a small bow, in a glass-walled neon-lit office, a skyline behind him at dusk", 6, heroes=["mizuno"], costume=COSTUME["mizuno"])
add("m17_tower", "wide view of a gleaming glass tower at noon, pink and cyan reflections, a shadow of a bridge over the lobby entrance, quiet and powerful", 6)
add("m18_board", "a wall of glowing line charts and ticker symbols in cyan and pink inside a trading room, invented wordless logos, every line spiking upward, empty chairs", 6)
add("m18_phone", "tight insert, a phone screen showing a jagged glowing stock chart, a thumb hovering over a button, neon reflections on the glass", 6)
add("m19_sign", "a long polished conference table, the composed businessman in a charcoal suit calmly signing a contract while rivals in loud suits sign eagerly across from him, handshake in the foreground, glass skyline behind", 6, heroes=["mizuno"], costume=COSTUME["mizuno"])
add("f20_flamingo", "a comic wide shot, a giant pink flamingo-shaped speedboat on wheels crashing through a car wash, foam flying, a surprised driver in sunglasses and a Hawaiian shirt waving both hands, a police car behind, bright exaggerated Florida chaos", 6)
add("f20_gator", "a comic tight insert, a seagull wearing a tiny captain's hat standing triumphantly on top of a police cruiser's lights beside a flustered officer, bright exaggerated Florida chaos", 6)
add("m21_lobby", "the composed businessman in a charcoal suit standing perfectly still in a glass lobby as a giant pink flamingo-shaped boat bursts through the doors behind him, glass flying, phones raised all around, his eyebrow barely lifting", 6, heroes=["mizuno"], costume=COSTUME["mizuno"])
add("m22_watch", "wide night shot of a rooftop at the edge of a neon skyline, one dark figure in a long overcoat and a flat cap watching the city through the dark, phone lights glittering far below like stars", 7, refs=["p_shelby"])
add("s23_street", "exactly one man, the only one dressed in old-fashioned clothes, walking through a neon street full of ordinary modern people in casual clothes filming with phones, none of them looking at him, he moves with perfect calm", 7, heroes=["shelby"], costume=COSTUME["shelby"])
add("s24_proxy", "the lean man in a long overcoat handing a thin envelope to a cheerful influencer holding a ring-light phone rig on a neon boardwalk, a sly nod, the influencer grinning at the camera", 7, heroes=["shelby"], costume=COSTUME["shelby"])
add("s24_ledger", "tight insert, a leather ledger and a pocket watch on a dark wooden desk under a warm lamp, a neat column of handwritten figures with no readable text, a razor-sharp pencil", 8)
add("s24_decoy", "split composition: on the left a bright noisy neon club with a crowd of phones all pointed at one man in a flashy jacket, on the right a dark quiet back street where a van is quietly loaded, the contrast is the whole joke", 7)
add("s25_calm", "the lean man in a long overcoat standing perfectly still in a bright doorway while a blur of phones flashes around him, his face blank and bored, a deliberately dull moment", 8, heroes=["shelby"], costume=COSTUME["shelby"])
add("s26_behind", "the lean man in a long overcoat and flat cap walking away down a causeway at sunset, behind him a long line of glowing phone lights forming a trailing constellation, he does not look back", 9, heroes=["shelby"], costume=COSTUME["shelby"])
add("s29_end", "the four bosses seen from behind on the causeway at sunset, small against a huge sky, a ring of phone lights glowing around them", 9)


add("s01_boardwalk", "a wide neon boardwalk at dusk packed with tourists and locals all filming the sunset and each other on phones, palm trees, a roller coaster glowing in the distance, a sense of being watched from every direction", 1)
add("w13_stars", "tight insert, a row of five glowing neon-pink stars hanging over an empty night street, a police car's blue light washing across a wet wall, the stars flickering on one by one", 2)
add("v13_window", "seen from a dark street through a lit window, a family dinner at a long table with the grey-haired patriarch at its head, in the foreground the black silhouette of a hand holding up a glowing phone lens toward the window", 5, heroes=["vito"], costume=COSTUME["vito"])
add("v15_driver", "a delivery driver in a bright uniform on a neon loading dock holding up a phone to film a crate being slid into a van, a nervous half-smile, a moustache, wide eyes", 5)
add("m18_two", "two tall glowing towers facing each other across a neon street at night, the left tower built of one lone figure's glowing footprints, the right tower built of a swarming crowd of tiny phones, a chart line crossing between them", 6)
add("m21_trend", "tight insert, a phone screen showing a shaky video of a pink flamingo-shaped boat in a glass lobby, a red falling chart in the corner, a thumb frantically scrolling", 6)
add("s24_hall", "a grand 1930s debating hall with rows of leather benches, the lean man in a long overcoat standing quietly among well-fed men in top hats, a single lamp, whispers travelling along the benches", 7, heroes=["shelby"], costume=COSTUME["shelby"])
add("w02_keys", "small green islands and a boat yard on turquoise water at dusk, old fishing boats, coiled ropes and stacked crates on a weathered dock, nobody in view, a quiet coast with a long history of smuggling", 3)
add("w02_studio", "a neon-lit recording studio entrance on a neon coastal city street at night, an invented wordless sign shaped like a gold record, a velvet rope, parked sports cars, a phone held up in the foreground filming", 2)
add("s03_cursor", "tight insert, a glowing neon-pink arrow cursor sliding across a row of four empty portrait frames on a dark screen, one frame lit cyan, a satisfying game-menu energy, no text", 2)

def G(gid, seg_no, at, title, claim, marks, span, hold=4.5):
    return {"id": gid, "segment": f"S{seg_no:02d}", "at": at, "kind": "timeline", "title": title, "hold": hold, "claim": claim,
            "side": "right", "marks": [{"at": a, "label": l} for a, l in marks], "span": span}
GRAPHICS = [
  G("G01", 1, "Could a gangster", "Two worlds", "C-16", [(0.0, "1930s: Capone's era"), (1.0, "Our invented present")], "one invented city"),
  G("G02", 2, "Rockstar's page", "What is official", "C-01", [(0.0, "No story year given"), (1.0, "Nov 19, 2026: release")], "official page"),
  G("G03", 8, "Fourth card", "Shelby's era", "C-28", [(0.0, "Elected MP (in the story)"), (1.0, "1933: Series 6")], "1930s Birmingham"),
  G("G04", 10, "In 1930", "Capone, public figure", "C-19", [(0.0, "1930: Public Enemy list"), (1.0, "Depression: soup kitchen")], "1930s Chicago"),
  G("G05", 11, "In the 1930s", "Press then, phones now", "C-27", [(0.0, "1930s: newspapers"), (1.0, "Today: phones")], "our reading"),
  G("G06", 12, "In October", "The real case", "C-16", [(0.0, "The ledger line found"), (1.0, "Oct 1931: convicted")], "one year", 5.0),
  G("G07", 13, "He did end up", "The real ending", "C-18", [(0.0, "1931: convicted"), (1.0, "1947: dies in Florida")], "sixteen years"),
  G("G08", 18, "In the story", "Vito's end (story)", "C-25", [(0.0, "Film-era Don"), (1.0, "Mid-1950s: dies in his garden")], "in the story"),
]

def D(who, text, tags=None, emph=None, claims=None, pause=None):
    """A hero's own line (D-45): invented, in their manner (cast.<id>.speech), voiced by their own cast voice."""
    return dict(L(text, tags, emph, pause, claims), speaker=who)


def SL(text, tags=None, emph=None, claims=None, pause=None):
    return L(text, tags, emph, pause, claims)
def SS_(at, picture, crop, zoom=1.0):
    return {"at": at, "picture": picture, "crop_x": crop, "zoom": zoom}
def SD(who, text, tags=None):
    return dict(SL(text, tags), speaker=who)
SHORTS = [
 # 1 fact_bomb, short band: the ledger
 {"id": "SH01", "style": "fact_bomb", "ending": "pointer", "hook": "Could one line in a ledger bring down Al Capone?", "lines": [
   SL("Could one line in a ledger bring down Al Capone?", ["curious"], "capone", ["C-21"]),
   SL("What brought Capone down wasn't a rival. Or a bullet. It was a LEDGER.", ["dramatically"], "ledger", ["C-16"]),
   SL("An IRS investigator, Frank J. Wilson, found a line in a book. About seventeen thousand five hundred dollars, paid for Al.", claims=["C-21"]),
   SL("In October 1931, Capone was convicted of tax evasion. Eleven years in prison.", claims=["C-16"]),
   SL("The full video is Syndicate Wars, on the channel.", ["warmly"])],
  "shots": [SS_("Could one line", "c11_ledger", 0.4, 1.0), SS_("bring down Al Capone", "p_capone", 0.5, 1.1),
            SS_("What brought Capone", "c09_press", 0.5, 1.0), SS_("It was a LEDGER", "c11_ledger", 0.6, 1.3),
            SS_("An IRS investigator", "c11_agent", 0.8, 1.0), SS_("About seventeen", "c11_agent", 0.4, 1.3),
            SS_("In October", "c11_verdict", 0.3, 1.0), SS_("Eleven years", "c11_verdict", 0.6, 1.25),
            SS_("The full video", "sc_capone_out", 0.5, 1.0)]},
 # 2 dialogue_clash, short band: the flamingo argument
 {"id": "SH02", "style": "dialogue_clash", "ending": "question", "hook": "Who lost to a flamingo?", "lines": [
   SL("Who lost to a flamingo?", ["mischievously"], "flamingo"),
   SL("Made up, every word: our invented boss Haruto Mizuno, in our invented Vice City.", claims=["C-49"]),
   SL("A flamingo boat crashes into his lobby. Someone films it. A rumour trends."),
   SD("mizuno", "A flamingo. In my lobby.", ["deadpan"]),
   SL("His biggest partner panics before his lawyers wake up."),
   SD("mizuno", "This was not in the plan.", ["tense"]),
   SD("capone", "Third? He lost to a flamingo!", ["laughs"]),
   SD("mizuno", "The flamingo was not my fault.", ["annoyed"]),
   SL("Whose fault was it? Tell us, then watch the full video, Syndicate Wars.", ["warmly"])],
  "shots": [SS_("Who lost", "f20_flamingo", 0.5, 1.0), SS_("a flamingo?", "m21_lobby", 0.6, 1.0),
            SS_("Someone films it", "m21_trend", 0.5, 1.0), SS_("A flamingo. In my", "p_mizuno", 0.5, 1.15),
            SS_("His biggest partner", "m21_trend", 0.4, 1.3), SS_("This was not", "p_mizuno", 0.5, 1.35),
            SS_("Third?", "p_capone", 0.5, 1.15), SS_("The flamingo was", "m21_lobby", 0.3, 1.25),
            SS_("Whose fault", "sc_mizuno_out", 0.5, 1.0)]},
 # 3 pov_you, long band: you land in Leonida
 {"id": "SH03", "style": "pov_you", "ending": "question", "hook": "You're a 1930s crime boss, and you just landed in Leonida.", "lines": [
   SL("You're a 1930s crime boss, and you just landed in Leonida.", ["curious"], "leonida"),
   SL("And Leonida isn't empty. Rockstar's page names six places. Vice City, the Leonida Keys, Grassrivers, Port Gellhorn, Ambrosia and Mount Kalaga.", claims=["C-51"]),
   SL("It already has its own crime. Boobie Ike built an empire from the street up. Real estate, a strip club, a recording studio.", claims=["C-52"]),
   SL("The Real Dimez chase viral videos. Raul Bautista robs banks. And in the Keys, an old smuggler, Brian Heder, still works the water.", claims=["C-53", "C-54", "C-55"]),
   SL("Not a film set. A causeway, a neon sunset, and every phone pointing at you."),
   SL("That's Rockstar's world. Our four bosses are only guests in it.", ["warmly"], claims=["C-48"]),
   SL("So where would you hide, if every phone in Leonida pointed at you? Four bosses tried it in the full video, Syndicate Wars.", ["warmly"])],
  "shots": [SS_("You're a 1930s", "s02_chairs", 0.5, 1.0), SS_("just landed in Leonida", "s01_skyline", 0.5, 1.0),
            SS_("Rockstar's page names", "s01_skyline", 0.2, 1.3), SS_("Grassrivers", "s03_cursor", 0.5, 1.0),
            SS_("Ambrosia and", "s03_cursor", 0.3, 1.3), SS_("It already has", "w02_studio", 0.5, 1.0),
            SS_("Real estate", "w02_studio", 0.3, 1.3), SS_("The Real Dimez", "c10_viral", 0.5, 1.0),
            SS_("Raul Bautista", "c10_viral", 0.3, 1.3), SS_("And in the Keys", "w02_keys", 0.5, 1.0),
            SS_("still works the water", "w02_keys", 0.7, 1.3), SS_("Not a film set", "s01_boardwalk", 0.5, 1.0), SS_("every phone pointing", "s08_eye", 0.5, 1.0),
            SS_("That's Rockstar's world", "s02_history", 0.5, 1.0),
            SS_("So where would", "m22_watch", 0.5, 1.0), SS_("Four bosses tried", "s02_chairs", 0.3, 1.3)]},
 # 4 myth_buster, long band: the quiet boss is not safe
 {"id": "SH04", "style": "myth_buster", "ending": "pointer", "hook": "Is the quiet, legal business always the safe one?", "lines": [
   SL("Is the quiet, legal business always the safe one?", ["curious"], "safe"),
   SL("Vito rules with favours, not fists. Judges. Politicians. And a very long memory.", ["softly"], claims=["C-24"]),
   SL("So Vito leaves the noise of Vice City for Ambrosia, another place on Rockstar's page. He runs his import business from there. Legal. Boring. Safe.", ["warmly"], claims=["C-51"]),
   SD("vito", "Olive oil. Nobody films olive oil.", ["calm"]),
   SL("A favour works on people who know you. Strangers with phones don't.", emph="know"),
   SL("One delivery driver films a crate going into a van. The clip spreads. And the judge who owed Vito a favour stops answering his calls. Invented, but it tracks."),
   SD("vito", "He doesn't call back. He always calls back.", ["softly"]),
   SL("Vito doesn't lose a fight. He loses a phone call. That round is in the full video, Syndicate Wars.", ["softly"])],
  "shots": [SS_("Is the quiet", "v14_oil", 0.5, 1.0), SS_("always the safe", "v13_table", 0.5, 1.0),
            SS_("Vito rules", "p_vito", 0.5, 1.1), SS_("Judges", "v14_judge", 0.5, 1.0),
            SS_("So Vito leaves", "v15_dock", 0.5, 1.0), SS_("Legal. Boring", "v14_oil", 0.3, 1.3),
            SS_("Olive oil", "p_vito", 0.5, 1.3), SS_("A favour works", "v13_window", 0.5, 1.0),
            SS_("Strangers with phones", "v13_window", 0.2, 1.3), SS_("One delivery driver", "v15_driver", 0.5, 1.0),
            SS_("The clip spreads", "v15_dock", 0.2, 1.3), SS_("And the judge", "v15_phone", 0.5, 1.0),
            SS_("He doesn't call", "p_vito", 0.4, 1.4), SS_("Vito doesn't lose", "v15_phone", 0.6, 1.3)]},
 # 5 ranked_three, short band: the order of the falls
 {"id": "SH05", "style": "ranked_three", "ending": "question", "hook": "Four crime bosses in our invented Vice City test. Who falls first?", "lines": [
   SL("Four crime bosses in our invented Vice City test. Who falls first?", ["curious"], "first"),
   SL("So that's the order. Capone first, loud and famous. Vito second. Mizuno third.", claims=["C-48"]),
   SL("Shelby last. Quietest of all.", ["deadpan"]),
   SL("Shelby. That's why he wins. Mostly.", ["deadpan"]),
   SD("shelby", "Mostly?", ["surprised"]),
   SL("Would you rank them the same? The full video is Syndicate Wars.", ["warmly"])],
  "shots": [SS_("Four crime bosses", "s01_four", 0.5, 1.0), SS_("Who falls first", "sc_all", 0.5, 1.0),
            SS_("Capone first", "sc_capone_out", 0.5, 1.0), SS_("Vito second", "sc_vito_out", 0.5, 1.0),
            SS_("Mizuno third", "sc_mizuno_out", 0.5, 1.0), SS_("Shelby last", "p_shelby", 0.5, 1.0),
            SS_("That's why", "s26_behind", 0.4, 1.0), SS_("Mostly?", "p_shelby", 0.5, 1.4),
            SS_("Would you rank", "sc_final", 0.5, 1.0)]},
 # 6 anti_intuition, long band: don't hide from the cameras
 {"id": "SH06", "style": "anti_intuition", "ending": "pointer", "hook": "If everyone films you, don't hide from them, feed them the wrong thing.", "lines": [
   SL("If everyone films you, don't hide from them, feed them the wrong thing.", ["mischievously"], "wrong"),
   SL("Right. Shelby never hides from attention. He feeds it.", ["softly"]),
   SL("In Leonida, Shelby picks the Keys, where Rockstar says smugglers still work the water.", claims=["C-55"]),
   SD("shelby", "Let them film. Just not the right thing.", ["quietly"]),
   SL("In our invented Vice City, Shelby wouldn't post. He'd pay someone else to post the wrong thing. In the wrong place.", ["mischievously"], claims=["C-28"]),
   SL("A decoy here. The real ledger there. Every phone points at the decoy. And the real business moves."),
   SL("But in Vice City, violence is content. So he does the one thing nobody else did.", ["softly"]),
   SL("Shelby makes himself BORING on camera.", emph="boring"),
   SD("shelby", "Lovely weather. Nothing to report.", ["deadpan"]),
   SL("Is it enough to win? Watch the full video, Syndicate Wars.", ["warmly"])],
  "shots": [SS_("If everyone films", "s23_street", 0.5, 1.0), SS_("don't hide", "s25_calm", 0.5, 1.0),
            SS_("Right. Shelby", "s24_proxy", 0.2, 1.0), SS_("He feeds it", "s24_proxy", 0.6, 1.3),
            SS_("In Leonida", "w02_keys", 0.3, 1.0), SS_("still work the water", "w02_keys", 0.7, 1.25),
            SS_("Let them film", "p_shelby", 0.5, 1.2), SS_("In our invented", "s24_decoy", 0.2, 1.0),
            SS_("In the wrong place", "s24_decoy", 0.8, 1.2), SS_("A decoy here", "s24_ledger", 0.5, 1.0),
            SS_("And the real business", "s24_ledger", 0.3, 1.3), SS_("But in Vice City", "s24_decoy", 0.5, 1.3),
            SS_("So he does", "s25_calm", 0.3, 1.0), SS_("Shelby makes himself", "s25_calm", 0.6, 1.3),
            SS_("Lovely weather", "p_shelby", 0.5, 1.35), SS_("Is it enough", "s26_behind", 0.5, 1.0)]},
 # 7 would_you, short band: the boardroom or the street
 {"id": "SH07", "style": "would_you", "ending": "question", "hook": "Would you rather win the boardroom or the street?", "lines": [
   SL("Would you rather win the boardroom or the street?", ["curious"], "street"),
   SL("And in our scenario, our invented boss Haruto Mizuno takes an office in Vice City and wins the boardroom.", ["softly"]),
   SD("mizuno", "Sign here. And here. Thank you.", ["calm"]),
   SL("Clean contracts. Patient partners. Rivals sign. Rivals smile. Rivals pay.", ["deadpan"]),
   SL("He wins the boardroom. He loses the STREET.", ["dramatically"], "street"),
   SL("Which would you pick? The full video is Syndicate Wars.", ["warmly"])],
  "shots": [SS_("Would you rather", "m17_tower", 0.5, 1.0), SS_("the boardroom", "m19_sign", 0.5, 1.0),
            SS_("And in our scenario", "m17_card", 0.5, 1.0), SS_("Sign here", "m19_sign", 0.3, 1.3),
            SS_("Clean contracts", "m18_board", 0.5, 1.0), SS_("Rivals pay", "m18_phone", 0.5, 1.0),
            SS_("He wins", "m21_lobby", 0.5, 1.0), SS_("He loses the STREET", "f20_flamingo", 0.5, 1.0),
            SS_("Which would", "p_mizuno", 0.5, 1.0)]},
 # 8 cold_open_cliffhanger, long band: the video's opening
 {"id": "SH08", "style": "cold_open_cliffhanger", "ending": "cliffhanger", "hook": "Could a gangster from the 1930s survive a world where everybody has a CAMERA?", "lines": [
   SL("Could a gangster from the 1930s survive a world where everybody has a CAMERA?", ["curious"], "camera", ["C-16"]),
   SL("Welcome to Vice City, in the state of Leonida.", claims=["C-02"]),
   SL("Rockstar's next game lives there. And we're about to drop four crime bosses into it."),
   SL("Four bosses. Four ways of ruling."),
   SL("In a world where everybody films everything, who realises FIRST that attention is both power and danger?", ["dramatically"], "first"),
   SL("And only one of them understands what a phone camera REALLY is.", ["warmly"], "really"),
   SL("Which one? The full video, Syndicate Wars, has the answer.", ["warmly"])],
  "shots": [SS_("Could a gangster", "c09_press", 0.5, 1.0), SS_("everybody has a CAMERA", "s01_phones", 0.5, 1.0),
            SS_("Welcome to Vice City", "s01_skyline", 0.5, 1.0), SS_("Rockstar's next game", "s01_boardwalk", 0.4, 1.0),
            SS_("drop four crime", "s01_four", 0.5, 1.0), SS_("Four bosses", "sc_all", 0.5, 1.0),
            SS_("In a world", "s08_eye", 0.5, 1.0), SS_("who realises FIRST", "s08_paths", 0.5, 1.0),
            SS_("power and danger", "c10_map", 0.5, 1.0), SS_("And only one", "s01_phones", 0.3, 1.3),
            SS_("Which one", "s29_end", 0.5, 1.0)]},
 # 9 countdown_hud, short band: the stars drop
 {"id": "SH09", "style": "countdown_hud", "ending": "cliffhanger", "hook": "What happens to a crime boss's stars in a city of phones?", "lines": [
   SL("What happens to a crime boss's stars in a city of phones?", ["curious"], "stars"),
   SL("In GTA V, commit a crime and your wanted stars climb.", claims=["C-50"]),
   SL("In a city of phones, we're guessing it climbs when ANYBODY sees you.", emph="anybody", claims=["C-27"]),
   SL("Capone's intimidation, down to two. Vito's influence, down to three once you leave his circle. Mizuno's discipline, four. Shelby's strategy, four.", claims=["C-44", "C-45", "C-46", "C-47"]),
   SL("Every star is our opinion. The reasons are in the full video, Syndicate Wars.", ["warmly"])],
  "shots": [SS_("What happens", "w13_stars", 0.5, 1.0), SS_("a city of phones", "s01_phones", 0.5, 1.0),
            SS_("In GTA V", "w13_stars", 0.3, 1.3), SS_("In a city of phones", "s08_eye", 0.5, 1.0),
            SS_("ANYBODY sees", "s01_boardwalk", 0.5, 1.0), SS_("Capone's intimidation", "sc_capone", 0.5, 1.0),
            SS_("Vito's influence", "sc_vito", 0.5, 1.0), SS_("Mizuno's discipline", "sc_mizuno", 0.5, 1.0),
            SS_("Shelby's strategy", "sc_shelby", 0.5, 1.0), SS_("Every star", "sc_final", 0.5, 1.0)]},
 # 10 loop, short band: certainty
 {"id": "SH10", "style": "loop", "ending": "loop", "hook": "Could the smartest boss in Vice City still lose?", "lines": [
   SL("Could the smartest boss in Vice City still lose?", ["curious"], "lose"),
   SL("Shelby's flaw isn't weakness. It's CERTAINTY.", ["dramatically"], "certainty"),
   SD("shelby", "I'm always three steps ahead.", ["confident"]),
   SL("He believes he's always several steps ahead. And a man like that never checks behind him.", ["softly"]),
   SL("In a city of cameras, behind him is exactly where the cameras are.", ["whispers"]),
   SL("And that's why, in the full video, Syndicate Wars, the smartest boss in Vice City could still lose. So:", ["softly"])],
  "shots": [SS_("Could the smartest", "m22_watch", 0.5, 1.0), SS_("still lose", "p_shelby", 0.5, 1.0),
            SS_("It's CERTAINTY", "p_shelby", 0.5, 1.35), SS_("I'm always", "s25_calm", 0.5, 1.2),
            SS_("He believes", "s26_behind", 0.5, 1.0), SS_("never checks", "s26_behind", 0.2, 1.3),
            SS_("In a city of cameras", "s08_eye", 0.5, 1.0), SS_("exactly where", "s01_phones", 0.6, 1.25),
            SS_("And that's why", "m22_watch", 0.3, 1.3)]},
]

for _h in CARDS:
    LIB[f"p_{_h}"] = {"file": f"p_{_h}.png", "engine": "existing", "heroes": [_h], "shows": []}
LIB["s01_skyline"] = {"file": "s01_skyline.png", "engine": "existing", "heroes": [], "shows": []}
seg("S01", "hook", 1, "Curiosity: a yes/no question and four bosses dropped into a city of cameras.", [
  L("Could a gangster from the 1930s survive a world where everybody has a CAMERA?", ["curious"], "camera", claims=["C-16"]),
  L("Not a film set. A causeway, a neon sunset, and every phone pointing at you."),
  L("Welcome to Vice City, in the state of Leonida.", claims=["C-02"], pause=0.3),
  L("Rockstar's next game lives there. And we're about to drop four crime bosses into it."),
  L("Four bosses. Four ways of ruling.", pause=0.3),
  L("And only one of them understands what a phone camera REALLY is.", ["warmly"], "really"),
], [S("Could a gangster", "A", P("s01_skyline"), "Open on the place: neon, heat, scale, no violence in the first 7 seconds", ("push", 1.0, 1.06)),
    S("Not a film set", "C", P("s01_phones"), "The threat of the video in one image: every phone is a witness", ("push", 1.0, 1.07), cut="the question lands, then the images answer"),
    S("Welcome to Vice City", "B", P("s01_boardwalk"), "The place named: everybody filming everybody", ("pull", 1.07, 1.0)),
    S("Rockstar's next game", "A", P("s01_four"), "Promise the four bosses before anyone is named", ("push", 1.0, 1.05)),
    S("And only one", "C", "s01_phones", "The phones return as the sting of the hook", ("push", 1.03, 1.1), reuse="reuse")])

seg("S02", "explanation", 1, "Trust: we say what is official, what is our guess, and what is history.", [
  L("Quick honesty first.", ["softly"], pause=0.3),
  L("Rockstar's page gives a release date, November 19, 2026. It gives no year for the story.", claims=["C-01", "C-04"]),
  L("So the year is OUR assumption. The scenario is our invention. Every word the bosses say here is made up.", claims=["C-48"], emph="our"),
  L("The history? That part is real. We'll tell you when it is."),
], [S("Quick honesty", "A", "s01_skyline", "Back to the place while the official facts are said", ("pull", 1.08, 1.02), reuse="reuse"),
    S("So the year", "A", P("s02_chairs"), "An empty table: the stage is set but the story is invented", ("push", 1.0, 1.05)),
    S("The history", "C", P("s02_history"), "A tactile cue for what is real history", ("push", 1.0, 1.06), cut="the switch to the real marks the honesty line")])

seg("S03", "explanation", 1, "Context: Rockstar's own Leonida already has its own crime; our bosses are guests in it.", [
  L("And Leonida isn't empty. Rockstar's page names six places. Vice City, the Leonida Keys, Grassrivers, Port Gellhorn, Ambrosia and Mount Kalaga.", claims=["C-51"]),
  L("It already has its own crime. Boobie Ike built an empire from the street up. Real estate, a strip club, a recording studio.", claims=["C-52"]),
  L("The Real Dimez chase viral videos. Raul Bautista robs banks. And in the Keys, an old smuggler, Brian Heder, still works the water.", claims=["C-53", "C-54", "C-55"]),
  L("That's Rockstar's world. Our four bosses are only guests in it.", ["warmly"], claims=["C-48"]),
], [S("And Leonida", "A", "s01_skyline", "The state and its city again while the official places are named", ("pull", 1.06, 1.0), reuse="reuse"),
    S("It already has", "B", P("w02_studio"), "Leonida's own crime as a business: a studio front, no Rockstar character drawn", ("push", 1.0, 1.06)),
    S("The Real Dimez", "C", "s01_phones", "Viral videos: the phones again", ("push", 1.02, 1.08), reuse="reuse"),
    S("And in the Keys", "A", P("w02_keys"), "The Keys: islands and a boat yard, the smugglers' water", ("push", 1.0, 1.05), cut="from the city to the water"),
    S("That's Rockstar's world", "A", "s01_four", "Our guests arrive", ("push", 1.0, 1.05), reuse="reuse")])

seg("S03", "explanation", 2, "Fun: the video-game character-select screen and our rating rule.", [
  L("Now. Choose your boss.", ["excited"], pause=0.4),
  L("Five stats each, out of five stars. These ratings are OURS. Opinions, not facts. And we'll show our reasons.", claims=["C-44"], emph="ours"),
], [S("Now. Choose", "B", "sc_all", "The character-select grid: the video's central visual", ("push", 1.0, 1.04)),
    S("Five stats each", "C", P("s03_cursor"), "The cursor moves across the frames while the rule is said", ("push", 1.0, 1.07))])

seg("S04", "evidence", 2, "Understand why Capone is rated brutal but brittle.", [
  L("First card. Al Capone.", ["dramatically"]),
  L("Brutality, five stars. Intimidation, four.", claims=["C-44"]),
  L("But adaptability? One star. Tech-savviness? One star.", ["deadpan"], claims=["C-44"]),
  L("Our reasoning: Capone ran on fear. And fear needs a room to work in. Not a FEED.", emph="feed", claims=["C-44"]),
], [S("First card", "B", "sc_capone", "Capone's card with the stars", ("push", 1.0, 1.05)),
    S("Our reasoning", "B", P("p_capone"), "The portrait that carries his face for the whole video", ("push", 1.0, 1.06), cut="the card gives way to the face when the reasoning starts")])

seg("S05", "evidence", 2, "Understand that Vito is a network, not a fist.", [
  L("Second card. Vito Corleone, the Don from The Godfather films.", ["warmly"]),
  L("Influence and networking, five stars. Strategy, four.", claims=["C-45"]),
  L("Brutality, just two. Tech-savviness, one.", claims=["C-45"]),
  L("Vito rules with favours, not fists. Judges. Politicians. And a very long memory.", ["softly"], claims=["C-24"]),
], [S("Second card", "B", "sc_vito", "Vito's card with the stars", ("push", 1.0, 1.05)),
    S("Vito rules", "B", P("p_vito"), "The portrait that carries his face for the whole video", ("push", 1.0, 1.06))])

seg("S06", "complication", 2, "Curiosity: a disciplined boss with one hidden weakness.", [
  L("Third card. Haruto Mizuno, our invented Yakuza boss. No real person. No real group.", claims=["C-46"]),
  L("Discipline, five stars. Brutality, four. Adaptability, four. Tech, four.", claims=["C-46"]),
  L("But chaos management?", ["deadpan"], pause=0.3),
  L("Two. Remember that.", ["whispers"], claims=["C-46"], pause=0.4),
], [S("Third card", "B", "sc_mizuno", "Mizuno's card with the stars", ("push", 1.0, 1.05)),
    S("But chaos", "B", P("p_mizuno"), "The portrait; the held look plants the open loop", ("push", 1.0, 1.06))])

seg("S07", "evidence", 2, "Understand why Shelby is the planner.", [
  L("Fourth card. Tommy Shelby, from the TV series Peaky Blinders, in his Birmingham years around 1930.", claims=["C-28"]),
  L("Adaptability, five. Tech-savviness, five. Strategy, five.", claims=["C-47"]),
  L("Influence, four. Brutality, three.", claims=["C-47"]),
  L("Our reasoning: Shelby treats information like CASH.", emph="cash", claims=["C-47"]),
], [S("Fourth card", "B", "sc_shelby", "Shelby's card with the stars", ("push", 1.0, 1.05)),
    S("Our reasoning", "B", P("p_shelby"), "The portrait that carries his face for the whole video", ("push", 1.0, 1.06))])

seg("S08", "question", 2, "Stakes: the question of the whole video and what it tests.", [
  L("So here's what this video asks.", ["curious"], pause=0.3),
  L("In a world where everybody films everything, who realises FIRST that attention is both power and danger?", ["dramatically"], "first"),
  L("We'll test it on four things: the phone, the feed, the money and the wanted level.", claims=["C-43"]),
  L("What the new game does with any of them, Rockstar hasn't said. We can only guess.", claims=["C-43"]),
  L("Four rounds. Loudest first.", ["mischievously"]),
], [S("So here's", "A", P("s08_paths"), "Four routes to one test: the structure of the video", ("push", 1.0, 1.05)),
    S("In a world", "C", P("s08_eye"), "The phone as the thing under test", ("push", 1.0, 1.07)),
    S("We'll test it", "C", "s01_phones", "The things tested, again as a crowd of phones", ("push", 1.0, 1.06), reuse="reuse"),
    S("Four rounds", "A", "s08_paths", "Return to the four paths for the countdown", ("pull", 1.07, 1.0), reuse="reuse")])

seg("S09", "evidence", 3, "Recognise Capone's fame as the 1930s version of going viral.", [
  L("Round one. Al Capone.", ["dramatically"], pause=0.3),
  L("In 1930, Chicago's crime commission names him Public Enemy Number One. And during the Depression, he sponsors a soup kitchen.", claims=["C-19", "C-20"]),
  L("He's not hiding. He's performing.", ["softly"], claims=["C-27"]),
  L("Our reading? Capone understood that fame is a kind of shield.", claims=["C-27"], emph="shield"),
], [S("Round one", "B", P("c09_press"), "Capone as a public figure: fame is the setting", ("push", 1.0, 1.06)),
    S("And during the Depression", "B", P("c09_soup"), "The soup kitchen: generosity as publicity", ("push", 1.0, 1.05)),
    S("Our reading", "B", "p_capone", "Face to the viewer for his reading", ("pull", 1.08, 1.0), reuse="reuse")])

seg("S10", "complication", 3, "Fun: Capone's fame turns into a trail of evidence in a city of phones.", [
  L("Now drop Capone in Vice City. Invented, remember.", ["mischievously"]),
  L("In this city, viral is a business. The Real Dimez live on it.", claims=["C-53"]),
  L("Someone films him handing out free sandwiches. Millions of views by lunch.", ["chuckles"]),
  D("capone", "Millions? For a sandwich? Print more sandwiches!", ["excited"]),
  L("Brilliant! Oh, but then someone films the car he arrived in. Then the driver. Then the licence plate."),
  D("capone", "Wait. Who filmed my car?", ["suspicious"]),
  L("In the 1930s, newspapers needed him as a story. Today, a camera makes everyone one.", claims=["C-27"]),
  L("Attention is power. Right up until it becomes a MAP.", emph="map", claims=["C-27"]),
], [S("Now drop", "B", "s01_boardwalk", "Capone arrives in the world of phones", ("push", 1.0, 1.05), reuse="reuse"),
    S("Someone films him", "B", P("c10_viral"), "The viral moment: power, and the joke", ("push", 1.0, 1.06)),
    S("Oh, but then someone films the car", "C", P("c10_plate"), "The trail starts with a plate", ("push", 1.0, 1.08), cut="from the big smile to the cold detail"),
    S("Attention is power", "A", P("c10_map"), "The map: attention turned into a route", ("pull", 1.08, 1.0))])

seg("S11", "reveal", 4, "Surprise: in real history it was a ledger, not a bullet, that ended Capone.", [
  L("And here's the part history already wrote.", ["softly"], pause=0.4),
  L("What brought Capone down wasn't a rival. Or a bullet. It was a LEDGER.", ["dramatically"], "ledger", claims=["C-16"]),
  L("An IRS investigator, Frank J. Wilson, found a line in a book. About seventeen thousand five hundred dollars, paid for Al.", claims=["C-21"]),
  L("In October 1931, Capone was convicted of tax evasion. Eleven years in prison.", claims=["C-16"]),
], [S("And here's", "C", P("c11_ledger"), "The ledger: the real tool that finished him", ("push", 1.0, 1.07)),
    S("An IRS investigator", "B", P("c11_agent"), "The patient investigator", ("push", 1.0, 1.05)),
    S("In October", "A", P("c11_verdict"), "The conviction: consequence, not spectacle", ("pull", 1.07, 1.0))])

seg("S12", "emotional_pause", 4, "Payoff of round one: Capone confused controlling people with controlling information; he falls first.", [
  L("Hmm. Capone's mistake would sink him in any century. He thought controlling people meant controlling the INFORMATION about him.", emph="information", claims=["C-27"]),
  L("It doesn't.", ["sighs"], pause=0.5, claims=["C-27"]),
  D("capone", "Nobody tells me it doesn't.", ["annoyed"]),
  L("Round one, and he's out.", ["deadpan"], pause=0.3),
  L("He did end up in Florida, though. At home on Palm Island, in 1947. A quiet ending for a loud man.", claims=["C-18"]),
  L("The next boss never makes a speech.", ["whispers"]),
], [S("Hmm. Capone's mistake", "B", "sc_capone_out", "Capone eliminated: the first fall", ("push", 1.0, 1.05)),
    S("It doesn't", "B", "p_capone", "The face as he is told it does not work", ("push", 1.03, 1.09), reuse="reuse"),
    S("He did end up", "A", P("c12_palm"), "The quiet real ending, set against the loud scenario", ("pull", 1.07, 1.0), cut="from the stamp to the stillness")])

seg("S13", "explanation", 2, "Commentary on a game system: the wanted level, and what changes when everybody has a phone.", [
  L("A quick word on stars.", ["warmly"], pause=0.3),
  L("In GTA V, commit a crime and your wanted stars climb.", claims=["C-50"]),
  L("In a city of phones, we're guessing it climbs when ANYBODY sees you.", emph="anybody", claims=["C-27"]),
  L("The stars in the corner aren't about the police any more. They're about the audience.", claims=["C-27"]),
], [S("A quick word", "C", P("w13_stars"), "The wanted stars as a neon sign: the game system under comment", ("push", 1.0, 1.07))])

seg("S14", "question", 5, "Question for round two: favours versus cameras.", [
  L("Round two. Vito Corleone.", ["dramatically"], pause=0.3),
  L("A man who wins with favours. Can Vito survive a city where every phone is a witness and nobody owes him ANYTHING?", ["curious"], "anything"),
], [S("Round two", "B", P("v13_table"), "Vito at the head of his table: a man whose power is people", ("push", 1.0, 1.05)),
    S("A man who wins", "B", P("v13_window"), "Seen from outside: a lens aimed at a private table", ("pull", 1.07, 1.0))])

seg("S15", "evidence", 5, "Understand Vito's discipline: favours, a legal front, and a refusal made for strategy.", [
  L("Vito's business is quiet.", ["softly"]),
  L("His legal front is an olive-oil import company, Genco Pura.", claims=["C-23"]),
  L("His real power is who owes him. Judges. Politicians.", claims=["C-24"]),
  L("And when someone offers Vito the heroin trade, he says no. Because those same judges and politicians would turn on him.", claims=["C-24"]),
  L("That's not morality. That's STRATEGY.", emph="strategy", claims=["C-24"]),
], [S("Vito's business", "C", P("v14_oil"), "The legal front, as a plain crate of oil", ("push", 1.0, 1.07)),
    S("His real power", "B", P("v14_judge"), "Judges and politicians: the network made visible", ("push", 1.0, 1.05)),
    S("And when someone", "B", P("v14_no"), "The refusal: strategy, shown as a gesture", ("push", 1.0, 1.06))])

seg("S16", "complication", 5, "Complication: favours do not travel to strangers with phones.", [
  L("So Vito leaves the noise of Vice City for Ambrosia, another place on Rockstar's page. He runs his import business from there. Legal. Boring. Safe.", ["warmly"], claims=["C-51"]),
  D("vito", "Olive oil. Nobody films olive oil.", ["calm"]),
  L("Safe? Well, no.", ["deadpan"], pause=0.4),
  L("A favour works on people who know you. Strangers with phones don't.", emph="know", claims=["C-45"]),
  L("One delivery driver films a crate going into a van. The clip spreads. And the judge who owed Vito a favour stops answering his calls. Invented, but it tracks."),
  D("vito", "He doesn't call back. He always calls back.", ["softly"]),
], [S("So Vito leaves", "A", P("v15_dock"), "The place and the phones: the witnesses arrive", ("pull", 1.07, 1.0)),
    S("A favour works", "B", "v13_table", "Back to the table: his world of known faces", ("push", 1.0, 1.05), reuse="reuse"),
    S("One delivery driver", "B", P("v15_driver"), "The stranger with the phone", ("push", 1.0, 1.06), cut="from the known table to the stranger"),
    S("And the judge", "B", P("v15_phone"), "The phone that does not ring: the loss", ("push", 1.0, 1.06))])

seg("S17", "emotional_pause", 5, "Payoff of round two: his authority does not reach the people his network depends on.", [
  L("Vito doesn't lose a fight. He loses a phone call.", ["softly"], pause=0.6),
  L("Round two. The Don finds out his authority doesn't reach the people his network DEPENDS on.", emph="depends"),
  L("In the story, he dies in his garden in the mid-1950s, playing with his grandson. A gentler ending than anyone else here gets.", claims=["C-25"]),
  L("And the next boss doesn't need anyone to love him. Just to sign.", ["mischievously"]),
], [S("Vito doesn't lose", "B", "v15_phone", "The silent phone again as the line lands", ("push", 1.03, 1.09), reuse="reuse"),
    S("Round two. The Don", "B", "sc_vito_out", "Vito eliminated: the second fall", ("push", 1.0, 1.05)),
    S("In the story", "A", P("v16_garden"), "The garden: a quiet canon ending", ("pull", 1.07, 1.0)),
    S("And the next boss", "A", P("m17_tower"), "A glass tower: the next kind of power", ("push", 1.0, 1.05))])

seg("S18", "question", 6, "Question for round three: can discipline beat a feed?", [
  L("Round three. Haruto Mizuno. Invented, remember.", ["dramatically"]),
  L("Quiet voice. Slim suit. A business card that says consultant.", claims=["C-46"]),
  L("Can a man with perfect discipline be beaten by a FEED?", ["curious"], "feed"),
], [S("Round three", "B", P("m17_card"), "Mizuno introduced by manners, not menace", ("push", 1.0, 1.05)),
    S("Can a man", "A", "m17_tower", "The corporate stage he plays on", ("pull", 1.07, 1.0), reuse="reuse")])

seg("S19", "explanation", 6, "Understand what money system the invented boss plays, and that it is a guess.", [
  L("Mizuno plays the stock-market way of GTA V.", ["warmly"], claims=["C-11"]),
  L("In that game, you can trade stocks through the in-game internet.", claims=["C-11"]),
  L("Fans say there are two exchanges, LCN and BAWSAQ. One is moved by your own actions, the other by other players.", claims=["C-12"]),
  L("Whether the new game has either, nobody outside Rockstar can tell us. We're guessing."),
], [S("Mizuno plays", "A", P("m18_board"), "The money system: charts as a battlefield", ("push", 1.0, 1.05)),
    S("In that game", "C", P("m18_phone"), "The in-game market on a phone screen", ("push", 1.0, 1.08)),
    S("Fans say", "A", P("m18_two"), "Two exchanges: the player's tower and the crowd's tower", ("push", 1.0, 1.05)),
    S("Whether the new game", "A", "m18_board", "Back to the board for the honest guess", ("pull", 1.07, 1.0), reuse="reuse")])

seg("S20", "evidence", 6, "Show competence: Mizuno wins the boardroom, dignity intact.", [
  L("And in our scenario, Mizuno takes an office in Vice City and wins the boardroom.", ["softly"]),
  D("mizuno", "Sign here. And here. Thank you.", ["calm"]),
  L("Clean contracts. Patient partners. Rivals sign. Rivals smile. Rivals pay.", ["deadpan"]),
  L("A skyline of buildings that never saw a bad invoice."),
], [S("And in our scenario", "B", P("m19_sign"), "The win: contracts signed, rivals eager", ("push", 1.0, 1.05)),
    S("Clean contracts", "C", "m18_phone", "The clean numbers on the screen", ("push", 1.03, 1.09), reuse="reuse"),
    S("A skyline", "A", "m17_tower", "The skyline that never saw a bad invoice", ("push", 1.0, 1.06), reuse="reuse")])

seg("S21", "humor", 6, "Fun: invented Florida-style chaos, clearly flagged as made up.", [
  L("Meanwhile, elsewhere in Leonida.", ["mischievously"], pause=0.3),
  L("A man tries to escape the police on a flamingo-shaped boat. Straight into a car wash.", ["chuckles"]),
  L("A seagull in a tiny captain's hat takes credit for the arrest.", ["deadpan"]),
  L("None of this happened. We made it up. But it's Florida, so it feels like it should have.", ["warmly"], claims=["C-49"]),
  L("The point? Chaos does not read quarterly reports.", emph="quarterly", claims=["C-49"]),
], [S("Meanwhile", "A", P("f20_flamingo"), "Invented comic chaos, drawn in the same world", ("push", 1.0, 1.06)),
    S("A seagull", "C", P("f20_gator"), "The punchline insert", ("push", 1.0, 1.08), cut="a joke needs a quick second image"),
    S("None of this", "C", "s02_history", "The stamped page: invented, on the record", ("push", 1.0, 1.06), reuse="reuse"),
    S("The point", "A", "f20_flamingo", "Return to the chaos as the thesis for round three", ("pull", 1.08, 1.0), reuse="reuse")])

seg("S22", "reveal", 6, "Payoff of round three: wins the boardroom, loses the street.", [
  L("Now picture Mizuno stepping out of the boardroom.", ["curious"]),
  L("A flamingo boat crashes into his lobby. Someone films it. A rumour trends."),
  D("mizuno", "A flamingo. In my lobby.", ["deadpan"]),
  L("His biggest partner panics before his lawyers wake up."),
  D("mizuno", "This was not in the plan.", ["tense"]),
  L("He wins the boardroom. He loses the STREET.", ["dramatically"], "street", pause=0.4),
  L("Chaos management, two stars. We did warn you.", ["deadpan"], claims=["C-46"]),
], [S("Now picture", "B", P("m21_lobby"), "The calm man and the absurd arrival", ("push", 1.0, 1.06)),
    S("Someone films it", "C", P("m21_trend"), "The rumour trends: the street speaks", ("push", 1.0, 1.08)),
    S("He wins", "B", "sc_mizuno_out", "Mizuno eliminated: the third fall", ("push", 1.0, 1.05), cut="the stamp lands on the word street")])

seg("S23", "transition", 7, "Hook for the last round.", [
  L("Three bosses down.", ["softly"], pause=0.4),
  L("One left. And he's been watching all of this, very closely.", ["whispers"]),
], [S("Three bosses down", "A", P("m22_watch"), "A silhouette watching from the dark: the last boss arrives", ("push", 1.0, 1.06))])

seg("S24", "question", 7, "Question for round four.", [
  L("Round four. Tommy Shelby.", ["dramatically"]),
  L("Can the man who treats information like cash be beaten by a world that shares EVERYTHING?", ["curious"], "everything"),
], [S("Round four", "B", P("s23_street"), "Shelby among the phones, unbothered", ("push", 1.0, 1.05)),
    S("Can the man", "A", "m22_watch", "He watches the city that never stops sharing", ("pull", 1.07, 1.0), reuse="reuse")])

seg("S25", "evidence", 7, "Understand Shelby's method: feed the attention, hide the business.", [
  L("Right. Shelby never hides from attention. He feeds it.", ["softly"], claims=["C-47"]),
  L("In the story, he becomes an MP. He plants false information to fool a rival.", claims=["C-28"]),
  L("In Leonida, Shelby picks the Keys, where Rockstar says smugglers still work the water.", claims=["C-55"]),
  D("shelby", "Let them film. Just not the right thing.", ["quietly"]),
  L("In Vice City, Shelby wouldn't post. He'd pay someone else to post the wrong thing. In the wrong place.", ["mischievously"], claims=["C-28"]),
  L("A decoy here. The real ledger there. Every phone points at the decoy. And the real business moves."),
], [S("Right. Shelby never", "B", P("s24_proxy"), "The proxy: attention bought and aimed", ("push", 1.0, 1.05)),
    S("In the story", "B", P("s24_hall"), "The political side of Shelby", ("push", 1.0, 1.05)),
    S("In Vice City", "A", P("s24_decoy"), "The decoy: one side loud, one side quiet", ("push", 1.0, 1.06)),
    S("A decoy here", "C", P("s24_ledger"), "The real ledger: the quiet half of the trick", ("push", 1.0, 1.08))])

seg("S26", "complication", 8, "Complication: Shelby is violent in canon, so the win is not innocence.", [
  L("Is Shelby violent? Yes. The story shows it. An assassination attempt. Worse.", claims=["C-28"]),
  L("But in Vice City, violence is content. So he does the one thing nobody else did.", ["softly"]),
  L("Shelby makes himself BORING on camera.", emph="boring", pause=0.4),
  D("shelby", "Lovely weather. Nothing to report.", ["deadpan"]),
], [S("Is Shelby violent", "B", "s23_street", "Back to the street: canon violence acknowledged", ("pull", 1.07, 1.0), reuse="reuse"),
    S("But in Vice City", "A", "s24_decoy", "Violence as content: the loud side of the city", ("push", 1.0, 1.05), reuse="reuse"),
    S("Shelby makes himself", "B", P("s25_calm"), "Deliberate dullness: the winning move", ("push", 1.0, 1.05))])

seg("S27", "reveal", 8, "Surprise: Shelby's flaw is certainty, not weakness.", [
  L("Shelby's flaw isn't weakness. It's CERTAINTY.", ["dramatically"], "certainty", pause=0.4, claims=["C-47"]),
  L("He believes he's always several steps ahead. And a man like that never checks behind him.", ["softly"]),
  D("shelby", "I'm always three steps ahead.", ["confident"]),
  L("In a city of cameras, behind him is exactly where the cameras are.", ["whispers"]),
], [S("Shelby's flaw", "B", "p_shelby", "Face on the flaw", ("push", 1.0, 1.06), reuse="reuse"),
    S("He believes", "A", P("s26_behind"), "He walks away, and the lights follow", ("pull", 1.07, 1.0))])

seg("S28", "explanation", 9, "The order of the falls: loudest to quietest.", [
  L("So that's the order. Capone first, loud and famous. Vito second. Mizuno third.", claims=["C-48"]),
  D("capone", "Third? He lost to a flamingo!", ["laughs"]),
  D("mizuno", "The flamingo was not my fault.", ["annoyed"]),
  L("Shelby last. Quietest of all.", ["deadpan"]),
], [S("So that's the order", "B", "sc_all", "The four cards again as the order is said", ("push", 1.0, 1.05), reuse="reuse")])

seg("S29", "payoff", 9, "Answer: Shelby realised first, which is why he wins, mostly.", [
  L("So who saw it first? Who understood that attention cuts both ways?", ["curious"]),
  L("Shelby. That's why he wins. Mostly.", ["deadpan"], pause=0.4, claims=["C-47"]),
  D("shelby", "Mostly?", ["surprised"]),
  L("But he's the only one who thinks he has it under CONTROL.", emph="control"),
], [S("So who", "B", "s26_behind", "The answer on the walking figure", ("push", 1.0, 1.06), reuse="reuse"),
    S("But he's the only", "B", "p_shelby", "The face that thinks it has control", ("push", 1.0, 1.08), reuse="reuse")])

seg("S30", "evidence", 9, "Stat screen returns: the stars changed by the test.", [
  L("Here's the stat screen again, after the test.", ["warmly"]),
  L("Capone's intimidation, down to two. Vito's influence, down to three once you leave his circle. Mizuno's discipline, four. Shelby's strategy, four.", claims=["C-44", "C-45", "C-46", "C-47"]),
  L("Every star is our opinion. Every drop has a reason."),
], [S("Here's the stat", "B", "sc_final", "The screen returns with changed stars", ("push", 1.0, 1.05)),
    S("Every star", "C", "s03_cursor", "The cursor again: the player's choice returns", ("push", 1.0, 1.06), reuse="reuse")])

seg("S31", "payoff", 9, "Aftertaste: a debatable question, a smile.", [
  L("So whose old way of ruling survives phone cameras, viral fame, big money and Florida chaos?"),
  L("The quiet one, mostly. But is winning quietly a victory, or just a different way to lose?"),
  L("Who did we rate wrong? Tell us in the comments."),
  L("And smile. Somebody's FILMING.", ["mischievously"], "filming"),
], [S("So whose old way", "A", P("s29_end"), "The four bosses small against the sky: the open question", ("pull", 1.08, 1.0)),
    S("And smile", "C", "s01_phones", "The phones return: the last wink", ("push", 1.0, 1.07), reuse="reuse")])

# --- the approved scenario (PV-45), what is new (PV-38), and each speaking hero's voice, manner and faces -----------------
import hashlib as _hl
SCENARIO = {"file": "scenario.md", "approved_by": "vano1919 (creator, project thread)", "approved_at": "2026-10-19",
            "sha256": _hl.sha256(open(__import__("os").path.join(__import__("os").path.dirname(sys.argv[1]), "scenario.md"), "rb").read()).hexdigest()}
DISTINCT = {"premise": "four crime bosses from different eras and fictions (Capone, Vito Corleone, an invented Yakuza boss, Tommy Shelby) dropped into GTA VI's Leonida, each in their own place",
            "question": "who realises first that attention is both power and danger, in a city where everybody films everything?",
            "outcome": "they fall from loudest to quietest; Shelby wins, mostly, and his flaw is certainty",
            "mechanism": "old ways of ruling (fame, favours, corporate discipline, misdirection) tested against phone cameras, viral fame and the wanted level"}
_FACES = ("neutral", "joyful", "sad", "scared", "angry", "surprised")
CAST_EXTRA = {
 "capone": {
  "voice": {"voice_id": None, "name": None,
            "style": "a gravelly, warm, boisterous American baritone, big and theatrical, quick to laugh and quick to anger",
            "traits": {"gender": "male", "age": "middle_aged", "temperament": ["boastful", "theatrical", "hot-tempered"], "energy": "high",
                       "origin": "1930s American big city", "role": "rival", "real_person": True, "documented": ["C-19", "C-20"]}},
  "speech": {"basis": "public", "style": "a loud showman: short punchy exclamations, talks like a businessman and a benefactor, sure of his own fame, flares up when doubted",
             "words": ["business", "the people", "my car", "print more"], "avoid": ["algorithm", "content creator"], "sources": ["C-19", "C-20", "C-27"]},
  "face_sheet": {"id": "capone_faces_v1", "ref": "p_capone", "set": list(_FACES) + ["smug", "confused", "worried", "doubtful", "amused"]}},
 "vito": {
  "voice": {"voice_id": None, "name": None,
            "style": "a soft, low, slightly husky elderly voice, slow and courteous, never raised",
            "traits": {"gender": "male", "age": "old", "temperament": ["soft-spoken", "courtly", "patient"], "energy": "low",
                       "origin": "Italian-American, 1950s New York", "role": "mentor", "real_person": False}},
  "speech": {"basis": "public", "style": "a patriarch's quiet courtesy: few words, calm statements, loyalty and favours, never a threat said aloud",
             "words": ["friend", "favour", "respect", "always"], "avoid": ["offer he can't refuse", "dude"], "sources": ["C-23", "C-24"]},
  "face_sheet": {"id": "vito_faces_v1", "ref": "p_vito", "set": list(_FACES) + ["smug", "curious", "doubtful", "worried"]}},
 "mizuno": {
  "voice": {"voice_id": None, "name": None,
            "style": "a calm, clear, measured mid-range voice with precise diction, polite and controlled; no exaggerated accent",
            "traits": {"gender": "male", "age": "middle_aged", "temperament": ["composed", "precise", "polite"], "energy": "low",
                       "origin": "a Japanese businessman speaking English", "role": "rival", "real_person": False}},
  "speech": {"basis": "personality", "style": "clipped, polite and exact: short complete sentences, procedure and plans, thanks people, never raises his voice until the plan breaks",
             "words": ["plan", "sign here", "thank you", "not my fault"], "avoid": ["dude", "awesome"]},
  "face_sheet": {"id": "mizuno_faces_v1", "ref": "p_mizuno", "set": list(_FACES) + ["determined", "confused", "worried", "deadpan"]}},
 "shelby": {
  "voice": {"voice_id": None, "name": None,
            "style": "a quiet, low, dry voice with a soft regional English accent, flat and controlled, every word placed",
            "traits": {"gender": "male", "age": "middle_aged", "temperament": ["cold", "terse", "calculating"], "energy": "low",
                       "origin": "1930s Birmingham, England", "role": "hero", "real_person": False}},
  "speech": {"basis": "public", "style": "terse and cold: short declaratives, dry understatement, always one step ahead, never explains himself",
             "words": ["let them", "nothing", "steps ahead", "mostly"], "avoid": ["by order of", "awesome"], "sources": ["C-28"]},
  "face_sheet": {"id": "shelby_faces_v1", "ref": "p_shelby", "set": list(_FACES) + ["smug", "determined", "amused", "deadpan", "doubtful"]}},
}
