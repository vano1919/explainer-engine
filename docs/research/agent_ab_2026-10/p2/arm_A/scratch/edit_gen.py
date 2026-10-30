import json, re, sys, copy, shutil
sys.path.insert(0, "/home/user/explainer-engine")
from explainer_engine.production import script as SC
import edit_pics as EP
import edit_rows2 as ER
ROOT = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
RATE = 0.010

def build():
    d = json.load(open(ROOT + "s03_performer.json"))
    toks = SC.tokens(d)
    segs = {s["id"]: s for s in d["segments"]}
    defined = set()
    cur = {}  # picture -> (z, dx) after its last shot
    for si, seg in enumerate(d["segments"]):
        rows = ER.ROWS[seg["id"]]
        idx = [i for i, t in enumerate(toks) if t["seg"] == si]
        lo, hi = idx[0], idx[-1] + 1
        # line start token index and times
        ls, tm, t = {}, {}, 0.0
        for li, line in enumerate(seg["lines"]):
            first = next(i for i in idx if toks[i]["line"] == li)
            n = len([i for i in idx if toks[i]["line"] == li])
            ls[li] = (first, n)
            tm[li] = t
            t += n / 2.6 + (line.get("pause_after") or 0.3)
        seg_end = t
        # positions of each row
        pos = []
        for (li, sub, pic, mot, o) in rows:
            first, n = ls[li]
            if sub:
                k = SC.find_phrase(toks, sub, first, first + n)
                if k is None:
                    raise SystemExit(f"{seg['id']} line {li}: sub {sub!r} not found")
            else:
                k = first
            pos.append(k)
            tstart = tm[li] + (k - first) / 2.6
            o["_t"] = tstart
        shots, prev_k = [], lo - 1
        for r, ((li, sub, pic, mot, o), k) in enumerate(zip(rows, pos)):
            t0 = o["_t"]
            t1 = rows[r + 1][4]["_t"] if r + 1 < len(rows) else seg_end
            dur = max(1.0, t1 - t0)
            # phrase: shortest word run from k that first matches at k searching from prev_k+1
            words = [toks[j]["w"].split()[0] for j in range(k, min(hi, k + 12))]
            phrase = None
            for m in range(min(3, len(words)), len(words) + 1):
                cand = " ".join(words[:m])
                f = SC.find_phrase(toks, cand, prev_k + 1, hi)
                if f == k:
                    phrase = cand
                    break
            if phrase is None:
                raise SystemExit(f"{seg['id']} row {r}: no unique phrase at {k}")
            prev_k = k
            typ, framing, heroes, cut_away, subject = EP.PICS[pic]
            # motion
            z, dx = cur.get(pic, (None, 0.0))
            new = z is None
            amt = min(0.09, RATE * dur)
            PUSH_MAX = 1.10
            if mot == "P":
                z0 = 1.0 if new else z
                if z0 + amt > PUSH_MAX:
                    mot = "L"
                else:
                    z1 = round(z0 + amt, 4)
                    m = {"kind": "push", "z0": z0, "z1": z1}
            if mot == "L":
                if new:
                    z0 = round(1.0 + amt, 4); z1 = 1.0
                else:
                    z0 = z; z1 = round(max(1.0, z - amt), 4)
                    if z1 >= z0:
                        z1 = z0; 
                m = {"kind": "pull", "z0": z0, "z1": z1}
                if m["z0"] == m["z1"]:
                    m = {"kind": "hold", "z0": z0, "z1": z0}
            if mot == "H":
                z0 = 1.0 if new else z
                m = {"kind": "hold", "z0": z0, "z1": z0}
            if mot in ("R", "Lf"):
                z0 = 1.06 if new or z < 1.04 else z
                m = {"kind": "pan", "z0": z0, "z1": z0, "dx": 0.05 if mot == "R" else -0.05}
            if m["kind"] in ("push", "pull") and abs(m["z1"] - m["z0"]) / dur < 0.0055:
                m = {"kind": "hold", "z0": m["z0"], "z1": m["z0"]}
            cur[pic] = (m["z1"], m.get("dx", 0.0))
            shot = {"at": phrase, "type": typ}
            if pic not in defined:
                defined.add(pic)
                p = {"id": pic, "engine": "gemini", "subject": subject, "framing": framing}
                if heroes:
                    p["heroes"] = heroes
                    p["speakers"] = EP.SPEAKERS.get(pic) or {h: [0.5, 0.38] for h in heroes}
                crowd = re.search(r"soldier|rider|horsemen|archer|gunner|men |troop|column|herder|colonel|army|artillery", subject)
                p["people"] = bool(heroes or crowd)
                if cut_away:
                    p["cut_away"] = True
                shot["picture"] = p
                shot["reuse"] = "unique"
            else:
                shot["picture"] = pic
                shot["reuse"] = "reuse"
            shot["motion"] = m
            if o.get("tr") == "dissolve":
                shot["transition"] = "dissolve"
                shot["cut"] = {"why": o.get("cut", "change of place or time")}
            if framing == "insert":
                shot["insert"] = True
            if typ == "A" and heroes:
                shot["heroes_ok"] = True
            shot["purpose"] = o["pu"]
            if o.get("reveal"):
                shot["reveal"] = o["reveal"]
            acc = list(o.get("acc", []))
            if not acc and dur >= 3.0:
                acc.append({"kind": "wobble", "strength": 0.3})
            if acc:
                shot["accents"] = acc
            shots.append(shot)
        seg["shots"] = shots
    return d

if __name__ == "__main__":
    d = build()
    json.dump(d, open(ROOT + "production_script.json", "w"), indent=1, ensure_ascii=False)
    n = sum(len(s["shots"]) for s in d["segments"])
    print("shots", n)
