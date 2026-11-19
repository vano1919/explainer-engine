"""The per-shot state machine of plan 5.1, bound to asset hashes: a changed file can never keep an old QA pass.

PLANNED -> VOICE_READY -> IMAGE_GENERATED -> IMAGE_OBSERVED -> (IMAGE_RETRY <= 2) -> IMAGE_ACCEPTED -> VIDEO_GENERATED ->
VIDEO_OBSERVED -> (VIDEO_RETRY <= 2 | FALLBACK_25D) -> CLIP_ACCEPTED -> SCENE_QA -> CREATOR_APPROVAL -> READY_FOR_ASSEMBLY.

Each state in a shot's history stores the sha256 of the file it was reached with. ``check`` re-hashes every stored file; the
first state whose file changed (or is gone) is dropped together with every later state, so the observation and acceptance
that rested on the old bytes no longer count. Stored per episode in ``production/shot_state.json``
(``schemas/shot_state.schema.json``). The runner records what a stage made with ``bind`` (a hash, no verdict); a state beyond
IMAGE_GENERATED is reached only by ``advance`` from an observation (W4), never by a stage run alone.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

SCHEMA = "shot_state/1"
REL = "production/shot_state.json"
RETRY_CAP = 2
STATES = ("PLANNED", "VOICE_READY", "IMAGE_GENERATED", "IMAGE_OBSERVED", "IMAGE_RETRY", "IMAGE_ACCEPTED", "VIDEO_GENERATED",
          "VIDEO_OBSERVED", "VIDEO_RETRY", "FALLBACK_25D", "CLIP_ACCEPTED", "SCENE_QA", "CREATOR_APPROVAL",
          "READY_FOR_ASSEMBLY")
# run.py makes the pictures before the read (STAGES order), so a shot may go PLANNED -> IMAGE_GENERATED and have its voice later.
NEXT = {
    "PLANNED": ("VOICE_READY", "IMAGE_GENERATED"),
    "VOICE_READY": ("IMAGE_GENERATED",),
    "IMAGE_GENERATED": ("IMAGE_OBSERVED",),
    "IMAGE_OBSERVED": ("IMAGE_ACCEPTED", "IMAGE_RETRY"),
    "IMAGE_RETRY": ("IMAGE_GENERATED",),
    "IMAGE_ACCEPTED": ("VIDEO_GENERATED",),
    "VIDEO_GENERATED": ("VIDEO_OBSERVED",),
    "VIDEO_OBSERVED": ("CLIP_ACCEPTED", "VIDEO_RETRY", "FALLBACK_25D"),
    "VIDEO_RETRY": ("VIDEO_GENERATED",),
    "FALLBACK_25D": ("VIDEO_GENERATED",),
    "CLIP_ACCEPTED": ("SCENE_QA",),
    "SCENE_QA": ("CREATOR_APPROVAL",),
    "CREATOR_APPROVAL": ("READY_FOR_ASSEMBLY",),
    "READY_FOR_ASSEMBLY": (),
}
ASSET_STATES = {"IMAGE_GENERATED": "image", "IMAGE_OBSERVED": "image", "IMAGE_ACCEPTED": "image", "VIDEO_GENERATED": "clip",
                "VIDEO_OBSERVED": "clip", "CLIP_ACCEPTED": "clip", "SCENE_QA": "clip", "CREATOR_APPROVAL": "clip",
                "READY_FOR_ASSEMBLY": "clip", "VOICE_READY": "voice"}
NEEDS_SHA = frozenset(ASSET_STATES)


class ShotStateError(ContractError):
    pass


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_of(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class ShotStates:
    """``episodes/<ep>/production/shot_state.json`` for one episode folder."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / REL
        self.doc = {"schema": SCHEMA, "episode_id": self.root.name, "shots": {}}
        if self.path.is_file():
            self.doc = json.loads(self.path.read_text(encoding="utf-8"))

    # -- storage
    def save(self) -> None:
        contracts.validate(self.doc)
        write_json_atomic(self.path, self.doc)

    def shot(self, sid: str) -> dict:
        return self.doc["shots"].setdefault(sid, {"state": "PLANNED", "history": [], "retries": {"image": 0, "video": 0},
                                                  "assets": {}, "resets": []})

    def state(self, sid: str) -> str:
        return self.shot(sid)["state"]

    def sha(self, sid: str, state: str) -> str | None:
        return next((h["sha256"] for h in reversed(self.shot(sid)["history"]) if h["state"] == state), None)

    def has_valid(self, sid: str, state: str) -> bool:
        """Whether ``state`` was reached and its file still has the hash it was reached with (re-hashed now)."""
        h = next((h for h in reversed(self.shot(sid)["history"]) if h["state"] == state), None)
        if h is None:
            return False
        return h["sha256"] is None or (h["path"] is not None and sha256_of(self.root / h["path"]) == h["sha256"])

    # -- moves
    def advance(self, sid: str, state: str, sha: str | None = None, path: str | None = None) -> dict:
        s = self.shot(sid)
        if state not in NEXT.get(s["state"], ()):
            raise ShotStateError(f"{sid}: {s['state']} -> {state} is not allowed (next: {', '.join(NEXT[s['state']]) or 'none'})")
        if state in NEEDS_SHA and not sha:
            raise ShotStateError(f"{sid}: {state} must store the asset sha256")
        if state in ("IMAGE_RETRY", "VIDEO_RETRY"):
            k = "image" if state == "IMAGE_RETRY" else "video"
            if s["retries"][k] >= RETRY_CAP:
                raise ShotStateError(f"{sid}: {state} already used {RETRY_CAP} times (cap); take FALLBACK_25D or stop")
            s["retries"][k] += 1
        s["history"].append({"state": state, "sha256": sha, "path": path, "at": _now()})
        s["state"] = state
        return s

    def reset_after(self, sid: str, state: str, why: str = "reset") -> list[str]:
        """Drop every state after ``state`` (and with it their QA); return the dropped state names."""
        s = self.shot(sid)
        idx = max((i for i, h in enumerate(s["history"]) if h["state"] == state), default=-1)
        if state != "PLANNED" and idx < 0:
            raise ShotStateError(f"{sid}: {state} was never reached")
        dropped = [h["state"] for h in s["history"][idx + 1:]]
        s["history"] = s["history"][: idx + 1]
        s["state"] = state
        if dropped:
            s["resets"].append({"after": state, "dropped": dropped, "why": why, "at": _now()})
        return dropped

    def bind(self, sid: str, kind: str, path: str) -> dict:
        """Record that ``path`` (relative to the episode folder) is the shot's current ``kind`` asset ("image", "clip", ...).
        A first image binding moves PLANNED/VOICE_READY to IMAGE_GENERATED; a changed hash resets what rested on the old one.
        A clip binding stores the hash only: VIDEO_GENERATED needs an accepted picture (W4), so the state does not move."""
        sha = sha256_of(self.root / path)
        if sha is None:
            raise ShotStateError(f"{sid}: cannot bind {path}: no such file")
        s = self.shot(sid)
        old = s["assets"].get(kind)
        if old and old["sha256"] != sha:
            self._reset_kind(sid, kind, f"{kind} changed since it was bound")
        s["assets"][kind] = {"sha256": sha, "path": path, "at": _now()}
        if kind == "image" and s["state"] in ("PLANNED", "VOICE_READY"):
            self.advance(sid, "IMAGE_GENERATED", sha, path)
        return s

    def mark_assembled(self, sid: str, master_sha: str | None) -> None:
        s = self.shot(sid)
        s["assembled"] = {"master_sha256": master_sha, "clip_sha256": (s["assets"].get("clip") or {}).get("sha256"),
                          "at": _now()}

    def _reset_kind(self, sid: str, kind: str, why: str) -> list[str]:
        s = self.shot(sid)
        first = next((h["state"] for h in s["history"] if ASSET_STATES.get(h["state"]) == kind), None)
        if first is None:
            return []
        prior = [h["state"] for h in s["history"]]
        back = prior[prior.index(first) - 1] if prior.index(first) else "PLANNED"
        s["assembled"] = None
        return self.reset_after(sid, back, why)

    def check(self, sid: str | None = None) -> list[dict]:
        """Re-hash every stored file; reset what rested on a changed or missing one. Returns the resets made."""
        out = []
        for k in ([sid] if sid else sorted(self.doc["shots"])):
            s = self.shot(k)
            for kind, a in list(s["assets"].items()):
                now = sha256_of(self.root / a["path"])
                if now != a["sha256"]:
                    dropped = self._reset_kind(k, kind, f"{kind} {'missing' if now is None else 'changed'}: {a['path']}")
                    del s["assets"][kind]
                    out.append({"shot": k, "asset": kind, "path": a["path"], "dropped": dropped})
            for h in list(s["history"]):   # a history file the asset map no longer covers (hand-edited state)
                if h["sha256"] and sha256_of(self.root / (h["path"] or "")) != h["sha256"]:
                    dropped = self.reset_after(k, s["history"][s["history"].index(h) - 1]["state"] if s["history"].index(h)
                                               else "PLANNED", f"{h['state']} file changed")
                    out.append({"shot": k, "asset": ASSET_STATES.get(h["state"]), "path": h["path"], "dropped": dropped})
                    break
        return out


# --- the two hook calls of episode/run.py ------------------------------------------------------------------------------
def check_all(root: Path) -> list[dict]:
    """Start of every stage: reset what a changed file invalidated. Writes only when something changed."""
    st = ShotStates(root)
    if not st.doc["shots"]:
        return []
    found = st.check()
    if found:
        st.save()
    return found


def record_stage(root: Path, stage: str) -> int:
    """After a stage wrote its record: bind the files it made to their shots (pictures -> image, clips -> clip, assemble ->
    the master's hash on every clip it used). Returns the number of bindings."""
    root = Path(root)
    n = 0
    st = ShotStates(root)
    if stage == "pictures":
        p = root / "production" / "pictures.json"
        pics = json.loads(p.read_text(encoding="utf-8"))["pictures"] if p.is_file() else {}
        for pid, v in sorted(pics.items()):
            sid, _, which = pid.rpartition("_")
            if which == "start":
                st.bind(sid, "image", v["file"])
                n += 1
    elif stage in ("clips", "assemble"):
        p = root / "production" / "shot_records.json"
        recs = json.loads(p.read_text(encoding="utf-8"))["shots"] if p.is_file() else []
        master = None
        if stage == "assemble":
            m = root / "production" / "master.json"
            mp = json.loads(m.read_text(encoding="utf-8")).get("master_mp4_path") if m.is_file() else None
            master = sha256_of(mp if Path(mp).is_absolute() else root / mp) if mp else None
        for r in recs:
            cp = r.get("clip_path")
            if not cp or not Path(cp).is_file() and not (root / cp).is_file():
                continue
            rel = str(Path(cp).resolve().relative_to(root.resolve())) if Path(cp).is_absolute() else cp
            if stage == "clips":
                st.bind(r["shot_id"], "clip", rel)
            else:
                st.mark_assembled(r["shot_id"], master)
            n += 1
    if n:
        st.save()
    return n
