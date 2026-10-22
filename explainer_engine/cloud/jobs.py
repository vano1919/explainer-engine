"""The job record of a cloud job (the Guardian's memory, master brief 2026-10-22 stage B): one directory per job with
``state.json`` (where the job is now), ``events.jsonl`` (every transition, with time and reason) and ``heartbeat.json``
(the last sign of life). Code polls; a person or an agent reads "what changed since my last look" from the events.

    jobs/cloud/<slug>/job-NNN_<date>/{state.json, events.jsonl, heartbeat.json}

States (the brief's vocabulary): QUEUED -> PROVISIONING -> STARTING -> MODEL_LOADING -> READY -> RUNNING -> CHECKPOINTING ->
UPLOADING -> SUCCEEDED, with FAILED, RETRYING, STALLED, STOPPING, STOPPED and RECOVERY_REQUIRED on the side. ``TRANSITIONS``
says which moves are legal; an illegal move raises instead of writing a lie into the record. ``observe()`` maps what the
provider shows (a RunPod pod's status and ports, the conductor's status line) onto these states, so the guard and the
watchdog write the record without knowing the provider's vocabulary. ``stall()`` says when a live state has gone quiet
for too long (per-state limits, measured where we have numbers). Nothing here talks to the network.

The record lives under ``jobs/`` (gitignored, on this machine); ``cloud/store.py`` copies it to the durable store with the
job's outputs, so a new session or another machine can read it. ``core/store.JobStore`` (stage artifacts of the local
pipeline) is a different record: stage outputs, not cloud lifecycle.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from explainer_engine.core.jobs import next_job_dir
from explainer_engine.core.store import write_json_atomic

STATES = ("QUEUED", "PROVISIONING", "STARTING", "MODEL_LOADING", "READY", "RUNNING", "CHECKPOINTING", "UPLOADING",
          "SUCCEEDED", "FAILED", "RETRYING", "STALLED", "STOPPING", "STOPPED", "RECOVERY_REQUIRED")
TERMINAL = ("SUCCEEDED", "STOPPED")
LIVE = ("PROVISIONING", "STARTING", "MODEL_LOADING", "READY", "RUNNING", "CHECKPOINTING", "UPLOADING", "RETRYING", "STALLED",
        "STOPPING")  # a resource may be billing
WAITING = ("QUEUED", "FAILED", "RECOVERY_REQUIRED")  # nothing should bill; a person or an agent decides
_SIDE = ("FAILED", "STALLED", "STOPPING", "STOPPED", "RECOVERY_REQUIRED")
TRANSITIONS = {
    "QUEUED": ("PROVISIONING", "STOPPED", "FAILED"),
    "PROVISIONING": ("STARTING", "MODEL_LOADING", "READY", "RUNNING") + _SIDE,
    "STARTING": ("MODEL_LOADING", "READY", "RUNNING") + _SIDE,
    "MODEL_LOADING": ("READY", "RUNNING") + _SIDE,
    "READY": ("RUNNING", "MODEL_LOADING", "UPLOADING", "SUCCEEDED") + _SIDE,
    "RUNNING": ("CHECKPOINTING", "UPLOADING", "MODEL_LOADING", "SUCCEEDED") + _SIDE,
    "CHECKPOINTING": ("RUNNING", "UPLOADING", "SUCCEEDED") + _SIDE,
    "UPLOADING": ("RUNNING", "SUCCEEDED") + _SIDE,
    "SUCCEEDED": ("STOPPING", "STOPPED"),  # the resource may still need to go
    "FAILED": ("RETRYING", "STOPPING", "STOPPED", "RECOVERY_REQUIRED"),
    "RETRYING": ("PROVISIONING", "STARTING", "RUNNING", "FAILED", "STOPPING", "STOPPED", "RECOVERY_REQUIRED"),
    "STALLED": ("RUNNING", "UPLOADING", "FAILED", "STOPPING", "STOPPED", "RECOVERY_REQUIRED", "SUCCEEDED"),
    "STOPPING": ("STOPPED", "FAILED", "RECOVERY_REQUIRED"),
    "STOPPED": ("RETRYING", "QUEUED"),  # a resume
    "RECOVERY_REQUIRED": ("RETRYING", "STOPPING", "STOPPED", "QUEUED", "FAILED"),
}
# how long a live state may go without a heartbeat before it is STALLED (seconds). PROVISIONING/STARTING: RunPod boots in
# 2-8 min (TMR incidents 2026-10-10/11, 16 min when the start command broke the container); MODEL_LOADING: 40 GB of models
# took ~100 s, a torch venv ~5 min, llama.cpp CUDA build 5-20 min on a loaded host; RUNNING: the stage's own limit (the
# manifest) or 30 min; UPLOADING: a 3.5 GB push ran ~30 min at 2 MB/s.
STALL_AFTER = {"PROVISIONING": 15 * 60, "STARTING": 10 * 60, "MODEL_LOADING": 25 * 60, "READY": 10 * 60, "RUNNING": 30 * 60,
               "CHECKPOINTING": 10 * 60, "UPLOADING": 40 * 60, "RETRYING": 15 * 60, "STOPPING": 10 * 60}
LOADING_WORDS = ("setup", "model", "fetch", "install", "build", "download", "venv")
UPLOAD_WORDS = ("push", "upload", "store", "publish")


class IllegalMove(ValueError):
    pass


def inputs_hash(payload) -> str:
    """What a job is asked to do, hashed: a finished job with the same hash is not run again (scenario 14)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


class Job:
    """One job directory. ``state`` is a dict (read on open, written on every change)."""

    def __init__(self, path):
        self.dir = Path(path)
        self.state = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    # --- creation and lookup ----------------------------------------------------------------------------------------
    @classmethod
    def create(cls, root, slug, *, kind, provider, inputs=None, caps=None, ledger=None, now=None, reuse_finished=True):
        """A new job under ``root/slug``. With ``reuse_finished`` a SUCCEEDED job with the same inputs is returned
        instead (its outputs are stored; running it again would only spend money)."""
        now = time.time() if now is None else now
        h = inputs_hash(inputs or {})
        if reuse_finished:
            for old in cls.list(root, slug):
                if old.state["state"] == "SUCCEEDED" and old.state.get("inputs_hash") == h:
                    old.event("reused", f"same inputs as this finished job; not run again", now=now)
                    return old
        d = next_job_dir(Path(root), slug)
        d.mkdir(parents=True, exist_ok=False)
        state = {"id": d.name, "slug": slug, "kind": kind, "provider": provider, "resource": None, "ledger": ledger,
                 "inputs_hash": h, "inputs": inputs or {}, "caps": caps or {}, "state": "QUEUED", "since": now, "created": now,
                 "updated": now, "stage": None, "outputs": [], "stored": [], "attempts": 0, "reason": "created"}
        write_json_atomic(d / "state.json", state)
        job = cls(d)
        job.event("created", "job created", now=now, state="QUEUED")
        return job

    @classmethod
    def list(cls, root, slug=None):
        root = Path(root)
        dirs = (root / slug).glob("job-*") if slug else root.glob("*/job-*")
        out = []
        for d in sorted(p for p in dirs if (p / "state.json").exists()):
            try:
                out.append(cls(d))
            except ValueError:
                continue
        return out

    @classmethod
    def by_resource(cls, root, resource):
        """The newest job that holds this provider resource (a pod id)."""
        hits = [j for j in cls.list(root) if j.state.get("resource") == resource]
        return hits[-1] if hits else None

    # --- the record --------------------------------------------------------------------------------------------------
    def save(self, now=None):
        self.state["updated"] = time.time() if now is None else now
        write_json_atomic(self.dir / "state.json", self.state)

    def event(self, kind, text, *, now=None, **detail):
        row = {"ts": time.time() if now is None else now, "kind": kind, "text": text, **detail}
        with open(self.dir / "events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def events(self, since=None):
        p = self.dir / "events.jsonl"
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []
        return [r for r in rows if since is None or r["ts"] > since]

    def move(self, state, reason, *, now=None, force=False, **detail):
        """A legal transition, written to both files. Moving to the current state only records the reason."""
        now = time.time() if now is None else now
        cur = self.state["state"]
        if state not in STATES:
            raise IllegalMove(f"unknown state {state}")
        if state == cur:
            if reason != self.state.get("reason"):
                self.state["reason"] = reason
                self.save(now)
            return False
        if state not in TRANSITIONS[cur] and not force:
            raise IllegalMove(f"{self.state['id']}: {cur} -> {state} is not a legal move ({reason})")
        self.event("move", reason, now=now, **{"from": cur, "to": state}, **detail)
        self.state.update(state=state, since=now, reason=reason)
        if state in ("RETRYING",):
            self.state["attempts"] = self.state.get("attempts", 0) + 1
        self.save(now)
        return True

    def attach(self, resource, now=None, **info):
        self.state["resource"] = resource
        self.state.update(info)
        self.event("resource", f"{self.state['provider']} resource {resource}", now=now, resource=resource)
        self.save(now)

    def heartbeat(self, stage=None, note="", *, now=None, source="guard"):
        """The last sign of life: who saw what, when. Written often, so it is not an event."""
        now = time.time() if now is None else now
        write_json_atomic(self.dir / "heartbeat.json", {"ts": now, "stage": stage, "note": note, "source": source})
        if stage and stage != self.state.get("stage"):
            self.event("stage", f"stage {stage}", now=now, stage=stage)
            self.state["stage"] = stage
            self.save(now)

    def last_heartbeat(self):
        p = self.dir / "heartbeat.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def record_output(self, path, *, now=None, stored=None):
        """A produced file with its sha256: what must exist in the store before any disk is deleted."""
        path = Path(path)
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        row = {"path": str(path), "sha256": h, "bytes": path.stat().st_size, "stored": stored}
        self.state["outputs"] = [o for o in self.state["outputs"] if o["path"] != row["path"]] + [row]
        self.save(now)
        return row

    def mark_stored(self, where, paths=None, *, now=None):
        """The durable copy exists (verified by the store): the outputs may leave the pod disk."""
        for o in self.state["outputs"]:
            if paths is None or o["path"] in paths:
                o["stored"] = where
        self.state["stored"] = sorted(set(self.state["stored"]) | {where})
        self.event("stored", f"outputs stored at {where}", now=now, where=where)
        self.save(now)

    def unstored_outputs(self):
        return [o for o in self.state["outputs"] if not o.get("stored")]

    def safe_to_release(self):
        """True when the resource may be stopped/deleted without losing work: nothing produced, or everything stored."""
        return not self.unstored_outputs()

    # --- reading -------------------------------------------------------------------------------------------------------
    def summary(self, now=None, since=None):
        """Lines a phone can read: state, how long, last sign of life, and what changed since ``since``."""
        now = time.time() if now is None else now
        s = self.state
        hb = self.last_heartbeat()
        lines = [f"{s['id']} [{s['slug']}] {s['state']} for {(now - s['since']) / 60:.0f} min: {s.get('reason', '')}"
                 + (f"; stage {s['stage']}" if s.get("stage") else "") + (f"; {s['provider']} {s['resource']}" if s.get("resource") else "")]
        if hb:
            lines.append(f"  last sign of life {(now - hb['ts']) / 60:.0f} min ago ({hb.get('source')}: {hb.get('note') or hb.get('stage') or ''})")
        if s["outputs"]:
            lines.append(f"  outputs {len(s['outputs'])}, stored {len(s['outputs']) - len(self.unstored_outputs())}")
        new = self.events(since) if since is not None else []
        for r in new[-8:]:
            lines.append(f"  + {time.strftime('%H:%M', time.gmtime(r['ts']))} {r['kind']}: {r['text']}")
        return lines


# --- mapping the provider's view onto the job ------------------------------------------------------------------------
def state_from_pod(pod, ready, conductor=None):
    """What a RunPod pod (flat record from ``runpod.norm``) and the conductor's first status line mean for the job:
    (state, reason, stage). ``pod`` None = gone."""
    st = pod.get("status") if pod else None
    if pod is None or st == "TERMINATED":
        return None, "the pod is gone", None  # the job's own history says whether that is success, failure or a stop
    if st == "ERROR":
        return "RECOVERY_REQUIRED", "the pod is in ERROR", None
    if st == "EXITED":
        return None, "the pod stopped", None
    if st == "PROVISIONING":
        return "PROVISIONING", "RunPod is finding a machine", None
    if st == "STARTING" or (st == "RUNNING" and not ready and not conductor):
        return "STARTING", "the container is starting", None
    if conductor:  # an answering conductor outranks the port mapping: the container is up
        head = conductor.split()
        word = head[1] if len(head) > 1 and head[0] == "STATUS" else ""
        stage = head[head.index("stage") + 1] if "stage" in head and head.index("stage") + 1 < len(head) else None
        if stage in ("None", ""):
            stage = None
        if word == "DONE":
            return "SUCCEEDED", conductor[:160], stage
        if word == "CAPPED":
            return "STOPPED", conductor[:160], stage
        if word == "STOPPED":
            return "FAILED", conductor[:160], stage
        if word == "BLOCKED":
            return "RECOVERY_REQUIRED", conductor[:160], stage
        if word == "RUNNING" and stage:
            low = stage.lower()
            if any(w in low for w in UPLOAD_WORDS):
                return "UPLOADING", conductor[:160], stage
            if any(w in low for w in LOADING_WORDS):
                return "MODEL_LOADING", conductor[:160], stage
            return "RUNNING", conductor[:160], stage  # the whole line: "2/5 done" changing is progress
        return "READY", "the pod answers; no stage running", None
    return "READY", "the pod runs and its ports are mapped", None


def observe(job, pod, ready, conductor=None, *, now=None):
    """One look from the guard: write the heartbeat and move the job if the provider's view changed. Returns the move."""
    now = time.time() if now is None else now
    state, reason, stage = state_from_pod(pod, ready, conductor)
    alive = pod is not None and pod.get("status") in ("RUNNING", "PROVISIONING", "STARTING")
    progressed = False
    if alive or conductor:
        # a sign of LIFE is progress, not an API answer: the status line changed, the stage changed, or the GPU is busy
        hb = job.last_heartbeat()
        busy = bool(pod) and (pod.get("util") or 0) > 5
        if hb is None or hb.get("note") != reason or hb.get("stage") != stage or busy:
            job.heartbeat(stage, reason, now=now)
            progressed = True
    cur = job.state["state"]
    if cur == "STALLED" and state in LIVE and not progressed:
        return None  # the provider still says "running"; only progress ends a stall
    if state is None:  # EXITED or gone: close what was open
        if cur in ("SUCCEEDED", "STOPPED", "FAILED", "RECOVERY_REQUIRED", "QUEUED"):
            return None
        if cur in ("STOPPING",):
            state = "STOPPED"
        elif job.unstored_outputs():
            state, reason = "RECOVERY_REQUIRED", f"{reason} while {cur} with {len(job.unstored_outputs())} unstored output(s)"
        else:
            state, reason = "FAILED", f"{reason} while {cur}"
    if state == cur or cur in TERMINAL and state not in ("STOPPING", "STOPPED", "RETRYING", "QUEUED"):
        return None
    if state not in TRANSITIONS[cur]:
        if state in ("PROVISIONING", "STARTING", "READY") and cur in ("MODEL_LOADING", "RUNNING", "UPLOADING", "CHECKPOINTING"):
            return None  # a blind look or a proxy hiccup must not move a job backwards
        job.move(state, reason, now=now, force=True, forced_from=cur)
        return state
    job.move(state, reason, now=now)
    return state


def stall(job, now=None, limits=None):
    """(why) when a live job has gone quiet past its state's limit, else ''. The limit is the stage's own expected
    duration when the job's inputs carry one (``inputs.stage_limits[stage]``), else ``STALL_AFTER``."""
    now = time.time() if now is None else now
    st = job.state["state"]
    if st not in LIVE or st == "STALLED":
        return ""
    limits = {**STALL_AFTER, **(limits or {})}
    hb = job.last_heartbeat()
    quiet_since = hb["ts"] if hb else job.state["since"]
    limit = limits.get(st, STALL_AFTER["RUNNING"])
    stage = job.state.get("stage")
    per_stage = (job.state.get("inputs") or {}).get("stage_limits") or {}
    if st == "RUNNING" and stage and stage in per_stage:
        limit = float(per_stage[stage])
        quiet_since = job.state["since"]  # a stage's budget counts from its start, heartbeats or not
    if now - quiet_since > limit:
        return f"{st}{' stage ' + stage if stage else ''} quiet for {(now - quiet_since) / 60:.0f} min (limit {limit / 60:.0f})"
    return ""
