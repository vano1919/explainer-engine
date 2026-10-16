"""One-off: Day 1 v6 (board.json + narration + the v6 sound plan) -> the D-43 production script. Kept for the record;
from now on production_script.json itself is edited (segment by segment) and this file is not run again."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.scripting.narration_lint import sentences  # noqa: E402

if "--force" not in sys.argv:  # 2026-10-16: a re-run overwrote compiled prompts, the six extra shots and the sounds
    raise SystemExit("refused: production_script.json is edited directly now; this one-off would overwrite it (--force)")
HERE = Path(__file__).parent
V6 = HERE.parent / "day1_v6"
board = json.loads((V6 / "board.json").read_text())
paras = [p for p in (V6 / "narration.txt").read_text().splitlines() if p.strip()]
world = json.loads((V6 / "world_spec.json").read_text())
BEATS = [("hook", 1), ("rules", 2), ("meadow", 3), ("meadow", 3), ("water", 4), ("dusk", 5), ("fire", 6), ("fire", 6),
         ("night", 7), ("end", 8)]
# delivery for a soft, deep, calm narrator: warmth by default, quiet surprise, dry humour; tags only where it changes
DELIVERY = {
    "Could the greatest": dict(tags=["softly", "intrigued"], emphasis=["age"], tone="hushed question", emotion="intrigue"),
    "And night is": dict(tags=["slowly"], emotion="unease", pause_after=0.6),
    "Right.": dict(tags=["warmly"], tone="storyteller settling in", emotion="calm amusement"),
    "They can all": dict(emphasis=["only"], emotion="dry wit"),
    "The scientists are": dict(tags=["thoughtful"], emotion="sincere"),
    "So who takes": dict(tags=["amused"], emotion="curiosity", pause_after=0.5),
    "Day one,": dict(tags=["warmly"], emotion="gentle irony"),
    "Can anyone here": dict(emphasis=["matches"], emotion="quiet urgency"),
    "Two hands go": dict(tags=["short pause"], emotion="wry"),
    "Two!": dict(tags=["chuckles"], emotion="dry humour"),
    "Hmm.": dict(tags=["thoughtful"], emotion="musing"),
    "Somebody write that": dict(tags=["amused"], emotion="dry humour"),
    "But a rule": dict(tags=["softly"], emotion="concern"),
    "And John Snow,": dict(emphasis=["that"], emotion="admiration"),
    "Uh-oh.": dict(tags=["slowly"], emotion="foreboding", pause_after=0.5),
    "The sun drops,": dict(tags=["suspenseful"], emotion="danger"),
    "It buys them": dict(tags=["softly"], emotion="tension", pause_after=0.6),
    "Now.": dict(tags=["slowly"], emotion="focus"),
    "Nothing but smoke.": dict(tags=["sighs"], emotion="frustration"),
    "Then Einstein takes": dict(tags=["intrigued"], emotion="discovery"),
    "Oh.": dict(tags=["softly"], emotion="wonder"),
    "A thread of": dict(tags=["whispers"], emotion="held breath"),
    "One careful breath...": dict(emphasis=["fire"], emotion="quiet triumph"),
    "Well, the hard": dict(tags=["warmly"], emphasis=["keeping"], emotion="wisdom"),
    "Almost nothing.": dict(tags=["deadpan"], emotion="dry humour"),
    "Wise.": dict(tags=["thoughtful"], emotion="respect"),
    "One spring.": dict(tags=["slowly"], emotion="reflective"),
    "Nobody has invented": dict(emphasis=["anything"], emotion="gentle irony"),
    "And tomorrow?": dict(tags=["softly", "intrigued"], emotion="promise"),
}
segments = []
shots = board["shots"]
pics = board["pictures"]
lib, defined = {}, set()
for pid, p in pics.items():
    if pid.startswith("v5_"):
        lib[pid] = {"id": pid, "file": f"{pid}.png", "engine": "existing", **{k: v for k, v in p.items() if k in ("heroes", "shows", "speakers")}}
# new pictures (painted by the pod reference painter from the Gemini frames)
NEW = {
    "v6_franklin_tinder": {"engine": "pod_ref", "refs": ["v5_d1-33"], "heroes": ["franklin"], "shows": [],
                           "subject": "Benjamin Franklin kneels and shields a dry, unlit nest of grass with his coat against the cold dusk wind",
                           "edit": "Edit the picture: remove every fire, flame, ember and glow, including the small fires in the background; the people behind him sit in the cold with nothing burning. Benjamin Franklin kneels and shields a dry, unlit nest of grass on the flat stone with the flap of his coat against the wind, looking up anxiously at the sky. Cold dusk light only.",
                           "stand_in": "v5_d1-30"},
    "v6_einstein_glasses": {"engine": "pod_ref", "refs": ["v5_d1-36"], "heroes": ["einstein", "franklin"], "shows": [],
                            "props": [{"thing": "reading glasses", "held_by": "einstein"}],
                            "speakers": {"einstein": [0.66, 0.27]},
                            "subject": "young Einstein takes off his round reading glasses and lifts them toward the low sun while Franklin cups a dry unlit grass nest",
                            "edit": "Edit the picture: remove the small flame and all smoke, the dry grass nest on the ground in front of the two men is cold and unlit, nothing burns or glows anywhere. The dark-haired man on the right (young Albert Einstein, moustache, rumpled suit) has taken off his small round wire reading glasses and holds them up in one hand toward the low sun, eyes wide with a sudden idea. The bald man on the left (Benjamin Franklin, round spectacles still on his nose) cups the dry grass nest with both hands and looks at the glasses, surprised."},
    "v6_lens_point": {"engine": "pod_ref", "refs": ["v5_d1-35", "v5_d1-34"], "heroes": [], "shows": ["smoke"],
                      "props": [{"thing": "reading glasses", "held_by": "einstein"}],
                      "subject": "one round lens of the reading glasses focuses the afternoon sun into a single bright point on dry grass, a thread of smoke",
                      "edit": "Edit picture 1: replace the large round magnifying glass with the small pair of round wire-rimmed reading spectacles from picture 2, held by one arm between finger and thumb. One lens focuses the low sun into a single tiny bright point on one blade of dry grass, a thin thread of smoke rises from it. No flame, no fire, no glow except the one bright point."},
}
for pid in ("v5_d1-33", "v5_d1-35", "v5_d1-34"):  # references only (never on screen)
    lib.setdefault(pid, {"id": pid, "file": f"{pid}.png", "engine": "existing", "heroes": [], "shows": []})
lib["v5_d1-34"]["props"] = [{"thing": "reading glasses", "held_by": "franklin"}]  # why it is a reference, not a shot
lib["v5_d1-35"]["props"] = [{"thing": "magnifying glass", "held_by": None}]
# segment shots: board shots grouped by the paragraph their phrase starts in
def tok(s): return re.sub(r"[^a-z0-9']", "", s.lower())
flat = [(tok(w), pi) for pi, p in enumerate(paras) for w in p.split()]
def para_of(phrase, after):
    want = [tok(w) for w in phrase.split()]
    for i in range(after, len(flat) - len(want) + 1):
        if [x for x, _ in flat[i:i + len(want)]] == want:
            return flat[i][1], i + 1
    raise SystemExit(phrase)
by_para, cur = {i: [] for i in range(len(paras))}, 0
for k, s in enumerate(shots):
    pi, cur = para_of(s["at"], cur) if k else (0, 1)
    by_para[pi].append(s)
# S06 opens on its own words (PV-04): the dusk picture moves from "Uh-oh." to "The sun drops,"
for s in by_para[4]:
    if s["at"] == "Uh-oh.":
        s["at"] = "The sun drops,"
        by_para[4].remove(s)
        by_para[5].insert(0, s)
        break
SFX = {"Right.": ("landing_thud__v1", -16, 0.6), "For a whole hour": ("tick_loop_4s__v1", -22, 2.4),
       "Somebody write that": ("pencil_scribble__v2", -20, 1.0), "Latrines go": ("footstep_dirt__v2", -20, 0.5),
       "So they build": ("cloth_rustle__v2", -17, 1.2), "Why grass?": ("cloth_rustle__v3", -18, 1.0),
       "Now. Fire.": ("cloth_rustle__v1", -18, 0.8), "Then Einstein takes": ("cloth_rustle__v2", -20, 0.7),
       "One careful breath": ("gasp_inhale__v1", -24, 0.9), "and fire": ("whoosh", -15, 0.9)}
BEDS = {0: [("Could", "wind_storm")], 1: [("Right.", "wind_day")], 5: [("The sun drops,", "wind_storm")], 6: [("and fire", "fire")]}
for pi, p in enumerate(paras):
    lines = []
    for sent in sentences(p):
        d = next((v for k, v in DELIVERY.items() if sent.startswith(k)), {})
        lines.append({"text": sent, **d})
    seg_shots = []
    for s in by_para[pi]:
        pid = s["picture"]
        row = {"at": s["at"], "type": "A" if s["motion"]["kind"] in ("pan", "pull") else "B", "motion": s["motion"]}
        if s.get("insert"):
            row["insert"] = True; row["type"] = "C"
        for k in ("reveal", "heroes_ok", "bubbles"):
            if s.get(k):
                row[k] = s[k]
        if pid in NEW and pid not in defined:
            row["picture"] = {"id": pid, **NEW[pid]}
            defined.add(pid)
        else:
            row["picture"] = pid
        seg_shots.append(row)
    audio = {}
    if pi in BEDS:
        audio["beds"] = [{"at": a, "sound": b} for a, b in BEDS[pi]]
    sfx = []
    for phrase, (snd, g, mx) in SFX.items():
        low = " " + " ".join(tok(w) for w in p.split()) + " "
        if " " + " ".join(tok(w) for w in phrase.split()) + " " in low:
            sfx.append({"at": phrase, "sound": snd, "gain_db": g, "max_s": mx})
    if sfx:
        audio["sfx"] = sfx
    beat, light = BEATS[pi]
    segments.append({"id": f"S{pi + 1:02d}", "beat": beat, "light_beat": light, "lines": lines, "shots": seg_shots,
                     **({"audio": audio} if audio else {})})
doc = {
    "schema": "production_script/1",
    "episode": {"id": "stone_age_day1", "title": "100 greatest scientists dropped into the Stone Age, Day 1", "fps": 30,
                "size": [1920, 1080], "grade": "prehistory"},
    "voice": {"provider": "elevenlabs", "model": "eleven_v4", "voice_id": "NOpBlnGInO9m6vDvFkFC", "name": "Grandpa Spuds Oxley",
              "style": "soft, deep, calm, warm and mature baritone storyteller; unhurried, intimate, gently amused; "
                       "emotion carried quietly (a held breath, a dry smile), never shouted",
              "pace_wpm": [140, 158], "default_tags": ["warmly"],
              "candidates": [
                  {"voice_id": "HSBWXljo3oivWhybh3YX", "name": "Mr Wellington", "why": "rich older baritone, warmth, gravitas"},
                  {"voice_id": "xkDz8dF9GIt1kG06c9Of", "name": "Ron 2", "why": "deep and soothing"},
                  {"voice_id": "Ovio1nb5Thj5cZeW3MPS", "name": "Alec", "why": "calm, warm, cinematic documentary"},
                  {"voice_id": "8wePOEVMsHVU2qfSJbtC", "name": "Lawrence", "why": "deep, subtly emotional, warm"}]},
    "world": world,
    "look": {"style_refs": ["v5_d1-36", "v5_d1-18", "v5_d1-42"], "default_engine": "pod_ref"},
    "cast": {
        "nansen": {"names": ["nansen", "fridtjof nansen"], "card": "Fridtjof Nansen: tall rugged Norwegian explorer, strong jaw, fair moustache, weathered face, heavy wool jacket"},
        "franklin": {"names": ["franklin", "benjamin franklin"], "card": "Benjamin Franklin: balding crown with long grey hair, round spectacles, plump weathered face, brown frock coat"},
        "newton": {"names": ["newton"], "card": "Isaac Newton: long wavy shoulder-length wig, long pale stern face, dark coat with a white cravat"},
        "einstein": {"names": ["einstein"], "card": "young Albert Einstein of 1905: dark untidy hair, moustache, rumpled suit, round reading glasses", "props": ["reading glasses"]},
        "darwin": {"names": ["darwin"], "card": "Charles Darwin: heavy brow, long white beard, dark frock coat"},
        "wallace": {"names": ["wallace", "alfred russel wallace"], "card": "Alfred Russel Wallace: high forehead, full brown beard, field jacket"},
        "snow": {"names": ["snow", "john snow"], "card": "John Snow: pale thoughtful clean-shaven physician, dark coat of the 1850s"}},
    "story": {"events": [{"thing": "smoke", "at": "Now. Fire."}, {"thing": "windbreak", "at": "So they build"},
                         {"thing": "fire", "at": "and fire"}],
              "forbidden_props": ["magnifying glass", "magnifier", "matches", "lighter"]},
    "picture_dirs": ["pictures"],
    "sound_dirs": ["sounds"],
    "library": {k: {kk: vv for kk, vv in v.items() if kk != "id"} for k, v in sorted(lib.items())},
    "music": [{"track": "clockwork_loop__v1", "from": "<start>", "to": "So, the order.", "gain_db": -20},
              {"track": "sneaky_pizzicato__v1", "from": "Day one,", "to": "Now. Fire.", "gain_db": -21},
              {"track": "clockwork_loop__v1", "from": "Now. Fire.", "to": None, "gain_db": -20}],
    "segments": segments,
}
(HERE / "production_script.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(len(segments), "segments", sum(len(s["shots"]) for s in segments), "shots", sum(len(s["lines"]) for s in segments), "lines")
