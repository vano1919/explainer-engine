"""Builds film_shots.json for "Napoleon vs Genghis Khan" from the compact shot list in episode.py.

Each shot is one call; this file fills the card structure the schema asks for (blocking from the scene's stage, figure
heights from the shot size, the drawn source and master, the last frame of a long acted shot) so the shot list stays
readable. Run it, then `python -m explainer_engine.scripting.film_shots check film_shots.json`.

    python examples/napoleon_vs_genghis/build_cards.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HEIGHT = {"EWS": "quarter", "WS": "third", "MWS": "two_thirds", "MS": "most", "MCU": "most", "CU": "most", "ECU": "most",
          "OTS": "most"}
KEYPOSE_AFTER_S = 5.0  # BP-108: a longer acted shot draws its last frame (the engine checks the registry's value)


class Episode:
    def __init__(self, meta: dict):
        self.doc = dict(meta, shots=[])
        self.scene_id = None
        self.n = 0
        self.keys: dict[str, str] = {}  # a payoff's key -> its shot id, for the teasers (KP-41)

    def scene(self, sid: str, place: str, *, light: str, stage: dict, ambience: str):
        """stage: cast id -> (where, facing, on, pose); the scene's standing layout, kept for screen sides (KP-26)."""
        self.scene_id, self.place, self.light, self.stage, self.ambience = sid, place, light, stage, ambience
        self.n, self.master = 0, None

    def shot(self, size: str, seconds: float, beat: str, *, who=(), mode="scene", tier="full", act=None, line=None,
             narr=None, claims=(), cam="static", end=None, angle="eye", rel=(), lead=None, react=(), foley=(),
             loud=None, src=None, over=None, place=None, light=None, pose=None, where=None, on=None, facing=None,
             height=None, exit=False, last=None, key=None):
        self.n += 1
        sid = f"{self.scene_id}-{self.n:02d}"
        pose, where, on, facing, height = pose or {}, where or {}, on or {}, facing or {}, height or {}
        blocking = []
        for w in who:
            st_where, st_facing, st_on, st_pose = self.stage.get(w, ("center", "camera", "standing on the grass", ""))
            p = {"who": w, "where": where.get(w, st_where), "facing": facing.get(w, st_facing)}
            if size == "OTS":
                p["where"] = where.get(w, "left_front" if w == over else "center")
                other = next((x for x in who if x != w), None)
                p["facing"] = facing.get(w, other or st_facing)
            elif len(who) == 1 and w not in where:
                p["where"] = "center"
            if pose.get(w, st_pose):
                p["pose"] = pose.get(w, st_pose)
            p["on"] = on.get(w, st_on)
            h = height.get(w) or (HEIGHT.get(size) if not (size == "OTS" and w == over) else "half")
            if h:
                p["height"] = h
            blocking.append(p)
        if act:
            a = dict(zip(("who", "start", "peak", "settle", "face"), act))
            a = {k: v for k, v in a.items() if v}
            for p in blocking:  # the actor's first-frame pose is the action's start (keyframe_prompt writes it)
                if p["who"] == a["who"]:
                    p.pop("pose", None)
        frame = {"size": size, "angle": angle, "camera": cam, "place": place or self.place, "light": light or self.light}
        if end:
            frame["camera_end"] = end
        if over:
            frame["over"] = over
        if rel:
            frame["relations"] = list(rel)
        if lead or act:
            side, why = lead or ("none", "")
            frame["lead_room"] = {"side": side, **({"for": why} if why else {})}
        s = {"id": sid, "scene": self.scene_id, "mode": mode, "beat": beat, "seconds": seconds, "frame": frame,
             "tier": tier}
        if blocking:
            s["blocking"] = blocking
        if act:
            s["action"] = a
        if react:
            s["reactions"] = [{"who": w, "does": d} for w, d in react]
        if line:
            d = dict(zip(("who", "to", "text", "delivery"), line))
            s["dialogue"] = {k: v for k, v in d.items() if v}
        if narr:
            s["narration"] = narr
        if claims:
            s["claims"] = list(claims)
        import episode as _ep
        here = place or self.place
        snd = {"ambience": self.ambience if here == self.place else _ep.AMBIENCE.get(here, self.ambience)}
        if foley:
            snd["foley"] = list(foley)
        if loud:
            snd["loudest"] = loud
        s["sound"] = snd
        # the drawn source: the scene's first shot (or src="keyframe") is a master; the same size and people again is a
        # next pose of it; anything else is a cut of it (KP-27)
        m = self.master
        if src == "keyframe" or m is None:
            s["source"] = "keyframe"
            self.master = s
        else:
            same = (m["frame"]["size"] == size and m["frame"]["angle"] == angle
                    and [p["who"] for p in m.get("blocking", [])] == list(who) and size != "OTS")
            s["source"] = src or ("nextpose" if same else "cut")
            s["master"] = m["id"]
        long_act = act and seconds > KEYPOSE_AFTER_S and tier != "hold"
        if last if last is not None else long_act:
            s["last_frame"] = True
        if exit:
            s["exit"] = True
        if key:
            self.keys[key] = sid
        self.doc["shots"].append(s)
        return s

    def teaser(self, of: str, seconds: float, beat: str):
        """A cold-open piece of a later shot (KP-41): filled from that shot once the whole list is written."""
        self.n += 1
        s = {"id": f"{self.scene_id}-{self.n:02d}", "scene": self.scene_id, "beat": beat, "seconds": seconds, "_of": of}
        self.doc["shots"].append(s)
        return s

    def resolve(self):
        by_id = {s["id"]: s for s in self.doc["shots"]}
        for s in self.doc["shots"]:
            if "_of" not in s:
                continue
            of = by_id[self.keys[s.pop("_of")]]
            for k in ("mode", "frame", "blocking", "action", "reactions", "sound", "tier"):
                if k in of:
                    s[k] = json.loads(json.dumps(of[k]))
            s["source"], s["teaser_of"] = "keyframe", of["id"]


def main() -> int:
    import episode

    ep = Episode(episode.META)
    episode.write(ep)
    ep.resolve()
    out = HERE / "film_shots.json"
    out.write_text(json.dumps(ep.doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(s["seconds"] for s in ep.doc["shots"])
    by_scene: dict[str, float] = {}
    for s in ep.doc["shots"]:
        by_scene[s["scene"]] = by_scene.get(s["scene"], 0) + s["seconds"]
    t = 0.0
    for sc, secs in by_scene.items():
        print(f"{sc}  {int(t // 60)}:{t % 60:04.1f}  {secs:5.1f} s")
        t += secs
    print(f"{len(ep.doc['shots'])} shots, {total:.1f} s -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
