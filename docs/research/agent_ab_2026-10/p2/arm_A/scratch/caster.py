import json, shutil
A = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
d = json.load(open(A + "s04_editor.json"))
d["voice"].update(
    style="a warm, quick, dry-humoured documentary storyteller, clear mid-range male or female voice, lightly amused, slows for the hard facts and lets the jokes land flat",
    pace_wpm=[175, 195],
    candidates=[])
def v(style, gender, age, temper, energy, origin, role, ethnicity=None, doc=None, living=False):
    t = {"gender": gender, "age": age, "temperament": temper, "energy": energy, "origin": origin, "role": role,
         "real_person": doc is not None}
    if ethnicity: t["ethnicity"] = ethnicity
    if doc is not None:
        t["documented"] = doc
        t["living"] = False
    return {"voice_id": None, "name": None, "style": style, "traits": t, "candidates": []}
C = d["cast"]
C["napoleon"]["voice"] = v("a low, controlled adult male voice with a light French accent; clipped, quiet, final; never raises the volume, goes flatter when angry",
    "male", "middle_aged", ["controlled", "clipped", "cold"], "low", "French, born on Corsica", "hero",
    doc=["https://en.wikipedia.org/wiki/Napoleon (aged 43 in 1812, born on Corsica, French-speaking army commander)", "C-91..C-94 are invented premise; the traits rest on the public biographical record only"])
C["murat"]["voice"] = v("a loud, bright, theatrical adult male voice with a light French accent; quick, warm, runs ahead of the sentence, cracks when he is defensive",
    "male", "middle_aged", ["theatrical", "eager", "proud"], "high", "French, from south-west France", "comic",
    doc=["https://en.wikipedia.org/wiki/Joachim_Murat (aged 45 in 1812, from Gascony in south-west France, cavalry commander)"])
C["genghis"]["voice"] = v("a slow, flat, patient older male voice with a steppe accent; low, unhurried, amused only in the eyes; long pauses before the answer",
    "male", "old", ["patient", "dry", "calm"], "low", "Mongol, Central Asian steppe", "rival", ethnicity="Mongol",
    doc=["https://en.wikipedia.org/wiki/Genghis_Khan (aged about 60 in 1223, born on the Mongolian steppe)"])
C["kerim"]["voice"] = v("a quick, dry, careful young adult male voice with a light turkic-sounding accent; wary, polite, a little bitter, drops his voice when he tells the truth",
    "male", "young", ["wary", "dry", "proud"], "medium", "Crimean Tatar, a Mameluke of the Guard", "everyman", ethnicity="Crimean Tatar")
C["kerim"]["voice"]["traits"]["real_person"] = False
json.dump(d, open(A + "production_script.json", "w"), indent=1, ensure_ascii=False)
