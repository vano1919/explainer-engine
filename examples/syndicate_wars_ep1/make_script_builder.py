"""Builder for jobs/syndicate_wars/production_script.json (scratch tool; the JSON is the artifact)."""
import json, sys

CARDS = {
 "capone": ("a heavy-set 1930s Chicago crime boss, broad round face with three thin old scars on the left cheek, slicked-back dark hair, "
            "cream wide-lapel pinstripe suit, white fedora, a flower in the lapel, theatrical confident posture"),
 "vito": ("an older heavy-set patriarch of the 1950s, bald crown with a white fringe, round full face, thick grey eyebrows, small round "
          "spectacles, dark double-breasted suit with a white pocket square, a gold signet ring, soft-spoken courtly posture"),
 "mizuno": ("a composed middle-aged Japanese businessman, short crew cut streaked with silver, thin rimless glasses, slim charcoal "
            "suit, crisp white shirt, slim black briefcase, upright disciplined posture"),
 "shelby": ("a stocky square-jawed man in his thirties, side-parted wavy auburn hair, thick eyebrows, warm brown eyes, a neat trimmed "
            "moustache, a soft brown tweed cap with a short brim, grey three-piece suit with a watch chain, long charcoal overcoat, "
            "calm confident posture"),
}
NAMES = {"capone": ["capone", "al capone"], "vito": ["vito", "vito corleone"], "mizuno": ["mizuno", "haruto mizuno"],
         "shelby": ["shelby", "tommy shelby"]}
COSTUME = {"capone": "1930s pinstripe suits and fedoras", "vito": "1950s dark double-breasted suits",
           "mizuno": "slim modern business suits", "shelby": "1930s wool overcoats and three-piece suits"}

PICS = {}   # id -> dict
def pic(pid, subject, heroes=(), tier="standard", engine="pod_ref", refs=None, reason=None, costume=None, file=None):
    d = {"id": pid}
    if file:
        d.update({"file": file, "engine": "existing", "heroes": list(heroes), "shows": []})
        return d
    d["engine"] = engine
    d["subject"] = subject
    if heroes:
        d["heroes"] = list(heroes)
    if engine == "pod_ref":
        r = list(refs) if refs is not None else []
        for h in heroes:
            if f"p_{h}" not in r:
                r.insert(0, f"p_{h}")
        if "s01_skyline" not in r:
            r.append("s01_skyline")
        d["refs"] = r
    if tier != "standard":
        d["tier"] = tier
    if reason:
        d["tier_reason"] = reason
    if costume:
        d["costume"] = costume
    return d

SEGS = []
def seg(sid, job, light, feel, lines, shots):
    SEGS.append((f"S{len(SEGS)+1:02d}", job, light, feel, lines, shots))

def L(text, tags=None, emph=None, pause=None, claims=None, tone=None):
    d = {"text": text}
    if tags: d["tags"] = tags
    if emph: d["emphasis"] = [emph]
    if pause: d["pause_after"] = pause
    if claims: d["claims"] = claims
    if tone: d["tone"] = tone
    return d

def S(at, typ, picture, purpose, motion=("push", 1.0, 1.06), cut=None, reuse=None, heroes_ok=False):
    d = {"at": at, "type": typ, "picture": picture, "purpose": purpose,
         "motion": {"kind": motion[0], "z0": motion[1], "z1": motion[2]}}
    if cut: d["cut"] = {"why": cut}
    if reuse: d["reuse"] = reuse
    if heroes_ok: d["heroes_ok"] = True
    return d

exec(open(sys.argv[1]).read())   # defines segments via seg()/pic()

doc = {
 "schema": "production_script/1",
 "episode": {"id": "syndicate_wars", "title": "Syndicate Wars: Classic Mafia Bosses in GTA 6's Leonida", "fps": 30,
             "size": [1920, 1080], "grade": "neon_dusk", "rulebook": "episode_rules.json",
             "notes": "Invented crossover scenario; commentary target in rights_manifest.json; stats are the channel's own rating."},
 "voice": {"provider": "elevenlabs", "model": "eleven_v4", "voice_id": None, "name": None,
           "style": "warm, mature baritone storyteller with dry humour; unhurried but lively, gently amused; emotion carried quietly, a held breath, a dry smile",
           "pace_wpm": [150, 172], "default_tags": ["warmly"], "candidates": []},
 "world": {"topic": "four classic crime bosses in a neon Florida-style city", "host": {"era": "modern_neon_florida",
           "place": "an invented neon coastal city of causeways and palms (Vice City in plain words only)", "when": "our assumed present day"},
           "visitors": [], "light_owner": "host",
           "day_arc": [{"beat": 1, "light": "neon_dusk"}, {"beat": 2, "light": "night_neon"}, {"beat": 3, "light": "sunset_causeway"},
                       {"beat": 4, "light": "ledger_lamp"}, {"beat": 5, "light": "night_neon"}, {"beat": 6, "light": "harsh_day"},
                       {"beat": 7, "light": "neon_dusk"}, {"beat": 8, "light": "ledger_lamp"}, {"beat": 9, "light": "sunset_causeway"}]},
 "look": {"style_refs": [], "default_engine": "pod_ref"},
 "cast": {h: {"names": NAMES[h], "card": CARDS[h]} for h in CARDS},
 "story": {"events": [], "forbidden_props": ["gun fired in public", "blood", "drugs on display"]},
 "picture_dirs": ["pictures"],
 "sound_dirs": [],
 "library": LIB if "LIB" in globals() else {},
 "music": [],
 "segments": [],
 "graphics": GRAPHICS,
 "shorts": SHORTS,
}
for sid, job, light, feel, lines, shots in SEGS:
    doc["segments"].append({"id": sid, "beat": job, "job": job, "light_beat": light, "feel": feel, "purpose": feel,
                            "rules": ["ER-07", "ER-02"] if any("Capone" in l["text"] or "capone" in str(shots).lower() for l in lines) else ["ER-07"],
                            "lines": lines, "shots": shots})
json.dump(doc, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
words = sum(len(l["text"].split()) for _, _, _, _, ls, _ in SEGS for l in ls)
npics = len({(s["picture"] if isinstance(s["picture"], str) else s["picture"]["id"]) for g in doc["segments"] for s in g["shots"]})
print("segments", len(SEGS), "words", words, "shots", sum(len(g["shots"]) for g in doc["segments"]), "pictures", npics)
