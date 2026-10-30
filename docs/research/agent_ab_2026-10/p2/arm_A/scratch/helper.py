import json, sys, re
ROOT = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
PS = ROOT + "production_script.json"
def load(): return json.load(open(PS))
def save(d): json.dump(d, open(PS, "w"), indent=1, ensure_ascii=False)
def line(t):
    if t[0] == "N":
        d = {"text": t[1]}
        if len(t) > 2 and t[2]: d["claims"] = t[2]
    else:
        spk, to, intent, text = t[:4]
        d = {"text": text, "speaker": spk, "to": to, "intent": intent}
        if len(t) > 4 and t[4]: d["claims"] = t[4]
    return d
def set_lines(sid, tuples):
    d = load()
    s = next(x for x in d["segments"] if x["id"] == sid)
    old = s["lines"]
    s["lines"] = [line(t) for t in tuples]
    save(d)
    w = sum(len(l["text"].split()) for l in s["lines"])
    print(sid, len(s["lines"]), "lines", w, "words")
def set_beats(sid, mapping):
    """mapping: {line_index (0-based): [beat dicts]}"""
    d = load()
    s = next(x for x in d["segments"] if x["id"] == sid)
    for i, b in mapping.items():
        s["lines"][i]["visual_beats"] = b
    save(d)

def _b(kind, at, why, **kw):
    d = {"at": at, "kind": kind, "why": why}
    cue = kw.pop("cue", None)
    d.update({k: v for k, v in kw.items() if v is not None})
    if cue:
        snd, ev, cwhy = cue
        d["cue"] = {"sound": snd, "gain_db": -26, "max_ms": 200, "event": ev, "why": cwhy}
    return d
def T(at, text, pos, why, **k): return _b("text", at, why, text=text, pos=pos, **k)
def LB(at, text, pos, why, **k): return _b("label", at, why, text=text, pos=pos, **k)
def HL(at, pos, why, **k): return _b("highlight", at, why, pos=pos, **k)
def SY(at, symbol, pos, why, **k): return _b("symbol", at, why, symbol=symbol, pos=pos, **k)
def AC(at, effect, strength, why, **k): return _b("accent", at, why, effect=effect, strength=strength, **k)
def PR(at, thing, why, **k): return _b("prop", at, why, thing=thing, **k)
def CH(at, chart, values, claim, why, unit=None, labels=None, **k): return _b("chart", at, why, chart=chart, values=values, claim=claim, unit=unit, labels=labels, **k)
def EX(at, who, expression, why, **k): return _b("expression", at, why, who=who, expression=expression, **k)

def ins(sid, after_prefix, tuples):
    """insert new lines after the line whose text starts with after_prefix (existing lines keep their beats)"""
    d = load()
    s = next(x for x in d["segments"] if x["id"] == sid)
    k = next(i for i, l in enumerate(s["lines"]) if l["text"].startswith(after_prefix))
    s["lines"][k + 1:k + 1] = [line(t) for t in tuples]
    save(d)
def repl(sid, prefix, tup):
    """replace one line's words (its beats are dropped: the beat-writer must run again for it)"""
    d = load()
    s = next(x for x in d["segments"] if x["id"] == sid)
    k = next(i for i, l in enumerate(s["lines"]) if l["text"].startswith(prefix))
    s["lines"][k] = line(tup)
    save(d)
def report():
    d = load()
    tn = td = 0
    for s in d["segments"]:
        n = sum(len(l["text"].split()) for l in s["lines"] if not l.get("speaker"))
        h = sum(len(l["text"].split()) for l in s["lines"] if l.get("speaker"))
        tn += n; td += h
        print(s["id"], "narr", n, "dial", h, "total", n + h)
    print("narr", tn, "dial", td, "total", tn + td, "share %.1f%%" % (100 * tn / (tn + td)))
def set_beats(sid, mapping):
    """mapping keys: int line index, or a str = prefix of the line's text"""
    d = load()
    s = next(x for x in d["segments"] if x["id"] == sid)
    for i, b in mapping.items():
        if isinstance(i, str):
            i = next(k for k, l in enumerate(s["lines"]) if l["text"].startswith(i))
        s["lines"][i]["visual_beats"] = b
    save(d)
