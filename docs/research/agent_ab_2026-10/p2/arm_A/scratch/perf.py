import re, json
from helper import load, save
STOP = set("""a an the and or but so of to in on at for with by from into than then that this these those it its is are was were be been has have had do does did not no as if when while who what where why how one all any each every some more most very just only also here there their them they he she his her him we our you your i me my out up down off now still yet sire sir will would could can cannot can't don't won't i'm i'll we've they're it's that's let's about back over here's".split()""".split())
NARR = {"S01":"ominous","S02":"wry","S03":"matter-of-fact","S04":"tense","S05":"wry","S06":"tense","S07":"worried","S08":"hushed","S09":"building dread",
        "S10":"urgent","S11":"heavy","S12":"dry","S13":"ceremonial","S14":"reflective","S15":"quiet","S16":"warm"}
SPK = {"napoleon":("clipped, low, controlled","controlled"),"murat":("loud, theatrical, quick","eager"),
       "genghis":("slow, flat, patient","calm"),"kerim":("quick, dry, careful","wary")}
NTONE = "steady, quick, storyteller"
def auto_emph(text):
    words = re.findall(r"[A-Za-z0-9']+", text)
    for w in reversed(words):
        if len(w) >= 4 and w.lower() not in STOP: return w
    return None
O = {}   # (sid, prefix) -> dict(tags, emph, tone, emo, pause, interj, noemph)
def P(sid, prefix, tags=None, emph="auto", tone=None, emo=None, pause=None, interj=None):
    O[(sid, prefix)] = dict(tags=tags, emph=emph, tone=tone, emo=emo, pause=pause, interj=interj)
def apply():
    d = load()
    used = set()
    for s in d["segments"]:
        sid = s["id"]
        for l in s["lines"]:
            spk = l.get("speaker")
            tone, emo = (SPK[spk] if spk else (NTONE, NARR[sid]))
            ov = None
            for (osid, pre), v in O.items():
                if osid == sid and l["text"].startswith(pre):
                    ov = v; used.add((osid, pre)); break
            ov = ov or {}
            tags = ov.get("tags")
            emph = ov.get("emph", "auto")
            if emph == "auto":
                emph = auto_emph(l["text"]) if len(l["text"].split()) >= 3 else None
            if tags: l["tags"] = tags
            else: l.pop("tags", None)
            if emph: l["emphasis"] = [emph]
            else: l.pop("emphasis", None)
            l["tone"] = ov.get("tone") or tone
            l["emotion"] = ov.get("emo") or emo
            if ov.get("pause"): l["pause_after"] = ov["pause"]
            else: l.pop("pause_after", None)
            ij = ov.get("interj")
            if ij and not l["text"].startswith(ij):
                body = l["text"]
                if ij.endswith(",") and not re.match(r"(I\b|I'|Napoleon|Murat|Kerim|Genghis)", body):
                    body = body[0].lower() + body[1:]
                l["text"] = ij + " " + body
    miss = [k for k in O if k not in used]
    print("unused overrides:", miss)
    save(d)
