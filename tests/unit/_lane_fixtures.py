"""Three small film_shots/3 episodes for the lane planner (ICW-03, roadmap 15 "three fixture scripts"), built in memory from
compact rows so each one is readable here: a narrated battle documentary, a drama with a council and an exchange, and a
talk-heavy script whose seen dialogue alone is over BP-109's video band (the planner must report it, never rewrite it).
The Napoleon example (``examples/napoleon_vs_genghis/film_shots.json``) is the fourth, real one."""

from __future__ import annotations

CAST = {"anna": {"name": "Anna", "tag": "the tall captain in a red coat"},
        "ivo": {"name": "Ivo", "tag": "the old engineer with a grey beard"},
        "mara": {"name": "Mara", "tag": "the young scout with a braided cap"},
        "army": {"tag": "the ranks of grey infantry"}, "riders": {"tag": "the line of riders in brown"}}
PLACES = {"field": "an open field", "hall": "a stone hall", "road": "a dirt road", "fort": "a hill fort"}


def card(sid: str, scene: str, mode: str, size: str, seconds: float, beat: str, *, who=(), line=None, narr=None, claims=(),
         act=True, loud=False, camera="static", place="field") -> dict:
    s = {"id": sid, "scene": scene, "mode": mode, "beat": beat, "seconds": seconds,
         "frame": {"size": size, "angle": "eye", "camera": camera, "place": place, "light": "grey morning light"},
         "tier": "full", "source": "keyframe", "lane": "VIDEO_3D", "archetype": None, "duration_frames": round(seconds * 24),
         "width": 2560, "height": 1440, "lens_tier": "normal", "focal_xy": [0.5, 0.5], "continuity_ref": None,
         "blocking_ref": None, "render_profile": "eevee_full", "lipsync": False, "sound": {"ambience": "wind"}}
    if who:
        s["blocking"] = [{"who": w, "where": "center", "facing": "camera"} for w in who]
    if act and who:
        s["action"] = {"who": who[0], "start": "stands still", "peak": "moves", "settle": "stops"}
    if loud:
        s["sound"]["loudest"] = "a crash"
    if narr:
        s["narration"] = narr
    if claims:
        s["claims"] = list(claims)
    if line:
        s["dialogue"] = {"who": line[0], "to": line[1], "text": line[2]}
        s["lipsync"], s["dialogue_cover"] = True, "on_screen"
    return s


def doc(shots: list[dict], name: str) -> dict:
    claims = {c: {"text": "a sourced fact", "source": "https://example.org"} for s in shots for c in s.get("claims", [])}
    return {"schema": "film_shots/3", "fps": 24, "engine": "script_engine/1", "episode": name,
            "style": {"house_look": "ink_chronicle", "bible_version": "1.5"}, "cast": CAST, "places": PLACES,
            "claims": claims, "shots": shots}


def battle_documentary() -> dict:
    """Mostly narrated: maps and numbers to explain, a battle to play, two short exchanges."""
    rows = []
    for k in range(6):
        sc = f"S{k + 1:02d}"
        rows += [
            card(f"{sc}-01", sc, "establish", "EWS", 4, "The valley at dawn.", who=["army"], narr="The valley lay quiet at dawn."),
            card(f"{sc}-02", sc, "narrated", "WS", 4, "The road east, a route on the ridge.", who=["riders"],
                 narr=f"The riders were {k + 3} hundred metres away, out of range on the ridge.", claims=[f"C{k}a"]),
            card(f"{sc}-03", sc, "narrated", "WS", 4, "The army marches on the road.", who=["army"],
                 narr="The army marched along the road for days."),
            card(f"{sc}-04", sc, "scene", "WS", 4, "The charge.", who=["riders"], narr="Then the riders charged.", loud=True),
            card(f"{sc}-05", sc, "scene", "MS", 4, "The volley.", who=["army"], narr="The volley broke the charge.", loud=True),
            card(f"{sc}-06", sc, "scene", "MCU", 4, "Anna orders the guns forward.", who=["anna", "ivo"],
                 line=("anna", "ivo", "Bring the guns up now.")),
            card(f"{sc}-07", sc, "scene", "MCU", 3, "Ivo answers.", who=["ivo", "anna"], line=("ivo", "anna", "They are coming.")),
            card(f"{sc}-08", sc, "insert", "INSERT", 3, "A hand on the drum.", narr="The drum kept time."),
            card(f"{sc}-09", sc, "narrated", "MS", 4, "Losses counted.", who=["army"],
                 narr=f"About {k + 2} thousand men fell that day, the counts say.", claims=[f"C{k}b"]),
            card(f"{sc}-10", sc, "establish", "EWS", 4, "Smoke over the field.", narr="Smoke rose over the field.", act=False),
        ]
    return doc(rows, "Battle documentary (fixture)")


def council_drama() -> dict:
    """A council, a duel of words, a ride and its cost: more dialogue, fewer numbers."""
    rows = []
    for k in range(6):
        sc = f"S{k + 1:02d}"
        rows += [
            card(f"{sc}-01", sc, "establish", "WS", 4, "The hall of the fort.", who=["anna", "ivo", "mara"], place="hall",
                 narr="The council met in the stone hall."),
            card(f"{sc}-02", sc, "scene", "MS", 4, "Anna speaks.", who=["anna", "ivo", "mara"], place="hall",
                 line=("anna", "ivo", "We ride tonight, all of us.")),
            card(f"{sc}-03", sc, "scene", "MCU", 4, "Ivo refuses.", who=["ivo"], place="hall", line=("ivo", "anna", "Not with these horses.")),
            card(f"{sc}-04", sc, "scene", "CU", 4, "Mara looks at the map.", who=["mara"], place="hall",
                 narr="Mara had seen the road before."),
            card(f"{sc}-05", sc, "narrated", "WS", 5, "The road north, a route past the fort.", who=["riders"], place="road",
                 narr=f"The road ran {k + 4} miles north, past the fort and out of range.", claims=[f"D{k}a"]),
            card(f"{sc}-06", sc, "scene", "WS", 4, "They ride out.", who=["riders"], place="road", narr="They rode out at dusk."),
            card(f"{sc}-07", sc, "scene", "MS", 4, "Anna rides at the head.", who=["anna"], place="road",
                 narr="Anna rode at the head of the column."),
            card(f"{sc}-08", sc, "establish", "EWS", 4, "The fort at night.", place="fort", narr="The fort was dark.", act=False),
            card(f"{sc}-09", sc, "insert", "INSERT", 3, "A letter on the table.", place="hall",
                 narr=f"The letter, dated the {k + 2}th, is still in the record.", claims=[f"D{k}b"]),
            card(f"{sc}-10", sc, "scene", "CU", 4, "Ivo's face.", who=["ivo"], place="hall", narr="Ivo said nothing more."),
        ]
    return doc(rows, "Council drama (fixture)")


def talk_heavy() -> dict:
    """Seen dialogue on most of the runtime: no plan can bring VIDEO_3D into the band without cutting lines."""
    rows = []
    for k in range(8):
        sc = f"S{k + 1:02d}"
        rows += [card(f"{sc}-{j + 1:02d}", sc, "scene", "MCU", 5, "An exchange.", who=["anna", "ivo"],
                      line=("anna" if j % 2 else "ivo", "ivo" if j % 2 else "anna", "We talk and we talk and we talk.")) for j in range(8)]
        rows.append(card(f"{sc}-09", sc, "establish", "EWS", 4, "The hall.", place="hall", narr="The hall was cold.", act=False))
    return doc(rows, "Talk-heavy (fixture)")
