# from vano1919/tmr-video-script-engine@f0abe62:cloud/rp.py
"""RunPod pod manager: create, wait, guard, stop, sweep and settle the cost. stdlib only. REST v2 (api.runpod.io/v2).

    python -m explainer_engine.cloud.runpod check | balance | list | sweep [--dry-run] [--delete --yes]
    python -m explainer_engine.cloud.runpod create --yes --max-usd X --max-hours H [--gpu default|cheap|big] [--boot <manifest>]
           --ledger <episode run.json> [--volume GB] [--min-ram GB] [--name base] [--on-cap stop|delete] [--no-guard]
           [--vram GB [--ref-hours H]]   the cheapest JOB among the cards with stock now (pick_gpus), not a fixed pool
           [--script pod.sh --script-url <HF url of the same file>] [--heartbeat datasets/<o>/<r>:<file>] [--image I] [--disk GB]
    python -m explainer_engine.cloud.runpod cards --vram GB [--ref-hours H]   what the job would cost on each card now
    python -m explainer_engine.cloud.runpod status|logs|wait-ready|guard|stop|cost <pod> ;  delete <pod> --yes ;  start <pod> --yes ...
    python -m explainer_engine.cloud.runpod delete-volume <network volume id> --yes

What TMR's rp.py did and what changed here (docs/TOOL_STRATEGY.md "Money control for RunPod" has the facts from RunPod's API reference):
* one HTTP layer with retries (429, 5xx, timeouts, no network) for reads and for stop/delete; ``POST /pods`` is never re-sent
  blindly: RunPod has no idempotency key, so after an unclear answer the pod is looked up by its unique name and adopted (a
  blind retry is how a request is billed twice);
* stop and delete are idempotent and verified: the call counts only when ``GET`` shows EXITED (or the pod is gone);
* the money clock is per pod (``tools/runpod/sessions/<pod>.json``), not one global ``pod_meta.json``; it counts compute and
  disk, and the guard also enforces the lifetime in the pod's name (``-until-<epoch>``);
* the end of a pod is STOP by default; deletion only with the creator's word (``--on-cap delete`` or ``delete --yes``), and a
  stopped pod's disk is reported in dollars per day, because it keeps billing ($0.20/GB/month);
* ``create`` starts the guard as its own process and records the reservation in the run ledger; ``cost`` settles it with
  RunPod's billed amount (``GET /billing/pods``);
* ``PodSession`` (``with`` block) stops the pod on any error, exit or SIGTERM in Python callers;
* ``create`` refuses past the creator's ceilings in ``config/spend_caps.json`` (per pod, per 24 h of RunPod billing incl.
  stopped disks, per episode via the ledger, balance left) and while the account has a stray pod or an unkept stopped disk;
  ``check`` lists what bills now and is run by the session hooks (``hooks.py``) at the start and end of every turn.

REST v2 (docs.runpod.io/api-reference-v2, read 2026-10-22; v1 is retired on 2026-11-15): pods are ``GET /pods`` (paginated
``{pods, pagination{nextCursor, hasNextPage}}``, no name filter), ``GET /pods/{id}`` (``status`` PROVISIONING/STARTING/RUNNING/
EXITED/ERROR/TERMINATED, ``cost`` $/h, ``runtime`` with ``uptime``, ``gpus[].util``, ``ports[]`` only while RUNNING, ``disk``,
``mounts.persistent.size``), ``POST /pods`` (one ``gpu.id`` per request; 201 with status PROVISIONING), ``POST /pods/{id}/action``
``{"action": start|stop|restart|terminate}``, ``DELETE /pods/{id}`` (204), ``GET /pods/{id}/logs`` (server-sent events),
``GET /billing/pods`` (``records[].totalAmount`` per bucket; no billed seconds). The balance still comes from GraphQL ``myself``.
``norm()`` turns a v2 pod into the flat record the rest of this module and the session files use.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from explainer_engine.core import spend_caps

ROOT = Path(__file__).resolve().parents[2]
RP = ROOT / "tools" / "runpod"
BASE = "https://api.runpod.io/v2"
GQL = "https://api.runpod.io/graphql"
UA = "explainer-engine"
IMAGE = os.environ.get("TMR_POD_IMAGE", "ghcr.io/vano1919/tmr-pod:latest")  # TMR's baked image (TMR cloud/Dockerfile)
BOOT_REPO = "vano1919/tmr-video-script-engine"  # the in-pod side (bootstrap.sh, conductor, painters) stays in TMR
GPUS = {"default": ["NVIDIA GeForce RTX 4090"],
        "cheap": ["NVIDIA RTX A5000", "NVIDIA RTX 4000 Ada Generation", "NVIDIA RTX A4500", "NVIDIA GeForce RTX 4090"],
        "big": ["NVIDIA RTX A6000", "NVIDIA A40", "NVIDIA RTX 6000 Ada Generation", "NVIDIA L40S"]}
MAX_PRICE = {"default": 0.95, "cheap": 0.90, "big": 0.95}  # $/h per card, the creator's ceilings (TMR 2026-10-10/11/16)
CUDA_VERSIONS = ["12.8", "12.9", "13.0"]
CONTAINER_GB, VOLUME_GB = 80, 150
# disk prices, docs.runpod.io/pods/pricing (2026-10-19): running $0.10/GB/month (container + volume), stopped volume $0.20;
# a stand-alone network volume $0.07/GB/month (docs.runpod.io/storage/network-volumes, read 2026-10-22; $0.05 above 1 TB)
GB_MONTH_RUNNING, GB_MONTH_STOPPED, GB_MONTH_NETWORK_VOLUME, HOURS_PER_MONTH = 0.10, 0.20, 0.07, 730.0
BOOT_MINUTES = 10  # the pod must answer (status page or ssh port) within this long, else it never booted
GONE = ("TERMINATED",)
ENDED = ("EXITED", "ERROR")  # not billing compute; ERROR is reported to the creator (its disk may still bill)


class RunPodError(RuntimeError):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


class NotFound(RunPodError):
    pass


class Unclear(RunPodError):
    """The request may or may not have happened (timeout, 5xx, lost connection)."""


def api_key():
    if os.environ.get("RUNPOD_API_KEY"):
        return os.environ["RUNPOD_API_KEY"].strip()
    p = RP / "api_key.txt"
    if not p.exists():
        raise SystemExit("no RunPod key: set RUNPOD_API_KEY or write tools/runpod/api_key.txt")
    return p.read_text().strip()


def _urllib(method, url, body, headers, timeout):
    """(status, text, response headers). A transport may return only (status, text)."""
    req = urllib.request.Request(url, body, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), dict(e.headers or {})


def norm(pod):
    """A v2 pod as the flat record this module keeps: id, name, status, costPerHr, volumeInGb, containerDiskInGb, publicIp,
    portMappings, startedAt, gpu, util (GPU utilisation 0-100 or None), uptime. A record that is already flat passes through."""
    if pod is None or "status" not in pod or "costPerHr" in pod:
        return pod
    rt = pod.get("runtime") or {}
    ports = rt.get("ports") or []
    public = {str(p.get("private")): p.get("public") for p in ports if p.get("public")}
    gpus = rt.get("gpus") or []
    mounts = pod.get("mounts") or {}
    return {"id": pod["id"], "name": pod.get("name", ""), "status": pod.get("status"), "costPerHr": pod.get("cost") or 0.0,
            "volumeInGb": ((mounts.get("persistent") or {}).get("size") or 0), "containerDiskInGb": pod.get("disk") or 0,
            "publicIp": next((p.get("ip") for p in ports if p.get("ip")), None), "portMappings": public or None,
            "startedAt": pod.get("startedAt"), "gpu": (pod.get("gpu") or {}).get("id"),
            "util": (max(g.get("util") or 0 for g in gpus) if gpus else None), "uptime": rt.get("uptime")}


class Api:
    """RunPod REST v2 + GraphQL. ``transport(method, url, body, headers, timeout) -> (status, text)``; it raises OSError (incl.
    timeouts) when no answer came. Reads, stop and delete are retried with backoff; create is not."""

    def __init__(self, key=None, *, base=BASE, gql=GQL, transport=_urllib, sleep=time.sleep, retries=4, timeout=60):
        self.key, self.base, self.gql, self.transport, self.sleep = key, base, gql, transport, sleep
        self.retries, self.timeout = retries, timeout

    def _headers(self):
        return {"Authorization": "Bearer " + (self.key or api_key()), "Content-Type": "application/json", "User-Agent": UA}

    def request(self, method, path, body=None, *, retry=True, url=None):
        data = json.dumps(body).encode() if body is not None else (b"{}" if method == "POST" else None)
        last, wait = None, None
        for attempt in range(self.retries + 1 if retry else 1):
            if attempt:
                self.sleep(min(60, wait or 2 ** attempt))  # a 429 names its own wait (Retry-After); v2 quotas are per window
            try:
                status, text, *rest = self.transport(method, url or self.base + path, data, self._headers(), self.timeout)
            except OSError as e:
                last = Unclear(f"{method} {path}: no answer ({e})")
                continue
            hdrs = {k.lower(): v for k, v in (rest[0] or {}).items()} if rest and isinstance(rest[0], dict) else {}
            if status == 404:
                raise NotFound(f"{method} {path}: 404", 404)
            if status == 429 or status >= 500:
                last = Unclear(f"{method} {path}: HTTP {status} {text[:200]}", status)
                try:
                    wait = int(float(hdrs.get("retry-after", ""))) if status == 429 else None
                except ValueError:
                    wait = None
                continue
            if status >= 400:
                raise RunPodError(f"{method} {path}: HTTP {status} {text[:300]}", status)
            return json.loads(text) if text.strip() else {}
        raise last

    def graphql(self, query):
        out = self.request("POST", "graphql", {"query": query}, url=self.gql)
        if out.get("errors"):
            raise RunPodError(f"graphql: {str(out['errors'])[:300]}")
        return out.get("data") or {}

    # --- pods ------------------------------------------------------------------------------------------------------
    def pod(self, pid):
        """The pod record (flat, ``norm``), or None when RunPod no longer knows it."""
        try:
            p = self.request("GET", f"/pods/{pid}")
        except NotFound:
            return None
        return None if not p or p.get("status") in GONE else norm(p)

    def _pages(self, path, key):
        """Every row of a cursor-paginated v2 listing (``{<key>: [...], pagination{nextCursor, hasNextPage}}``)."""
        out, cursor = [], None
        while True:
            q = "?limit=1000" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
            page = self.request("GET", path + q) or {}
            rows = page.get(key, page.get("items")) if isinstance(page, dict) else page
            out += list(rows or [])
            pg = page.get("pagination") if isinstance(page, dict) else None
            cursor = (pg or {}).get("nextCursor")
            if not pg or not pg.get("hasNextPage") or not cursor:
                return out

    def pods(self):
        """Every pod of the account (all pages), flat. v2 has no name filter: callers filter."""
        return [norm(p) for p in self._pages("/pods", "pods")]

    def action(self, pid, what):
        """``POST /pods/{id}/action``: start, stop, restart or terminate."""
        return self.request("POST", f"/pods/{pid}/action", {"action": what})

    def network_volumes(self):
        """Stand-alone network volumes (``GET /network-volumes``): they bill ($0.07/GB/month) with no pod at all."""
        return [{"id": v.get("id"), "name": v.get("name", ""), "size": v.get("size") or 0, "dataCenter": v.get("dataCenter")}
                for v in self._pages("/network-volumes", "networkVolumes")]

    def global_volumes(self):
        """Global volumes (``GET /global-volumes``): listed so nothing bills unseen; their price is not modelled here."""
        return [{"id": v.get("id"), "name": v.get("name", "")} for v in self._pages("/global-volumes", "globalVolumes")]

    def endpoints(self):
        """Serverless endpoints (``GET /serverless``): one with ``workersMin`` > 0 bills while idle."""
        return [{"id": e.get("id"), "name": e.get("name", ""), "workersMin": e.get("workersMin") or 0,
                 "workersMax": e.get("workersMax") or 0} for e in self._pages("/serverless", "endpoints")]

    def delete_network_volume(self, vid):
        try:
            self.request("DELETE", f"/network-volumes/{vid}")
        except NotFound:
            pass
        return "GONE"

    def balance(self):
        """GraphQL ``myself``: the only balance source. RunPod retires GraphQL in early 2027 and v2 has no balance endpoint
        (openapi.json read 2026-10-22): revisit by 2026-12; the fallback is the creator's top-ups reconciled against
        ``billing_total`` deltas (docs/TOOL_STRATEGY.md)."""
        return self.graphql("query { myself { clientBalance currentSpendPerHr spendLimit } }")["myself"]

    def billing_total(self, start, end=None):
        """What the WHOLE account billed since ``start`` (``GET /billing``: pods, serverless, storage, clusters), in USD, and
        the itemised totals. Hour buckets; the newest hour can lag up to an hour."""
        iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731
        page = self.request("GET", f"/billing?bucketSize=hour&startTime={iso(start - start % 3600)}&endTime={iso(end or time.time() + 3600)}") or {}
        totals = ((page.get("metadata") or {}).get("totals") or {}) if isinstance(page, dict) else {}
        if "totalAmount" in totals:
            return round(float(totals["totalAmount"] or 0), 4), totals
        rows = page.get("records", []) if isinstance(page, dict) else page
        return round(sum(float(r.get("totalAmount") or 0) for r in rows), 4), totals

    def billing(self, pid, start, end=None):
        """RunPod's billed amount (compute and disks, stopped pods included) for one pod, or the whole account when ``pid``
        is None, since ``start`` (epoch s): (usd, hour buckets with a charge). Hour buckets; the newest hour can lag."""
        iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731
        q = f"/billing/pods?bucketSize=hour&startTime={iso(start - start % 3600)}&endTime={iso(end or time.time() + 3600)}"
        q += f"&podId={pid}" if pid else ""
        page = self.request("GET", q) or {}
        rows = page.get("records", []) if isinstance(page, dict) else page
        rows = [r for r in rows if pid is None or r.get("podId") in (None, pid)]
        usd = sum(float(r.get("totalAmount", r.get("amount")) or 0) for r in rows)
        return round(usd, 4), sum(1 for r in rows if float(r.get("totalAmount", r.get("amount")) or 0) > 0)

    def catalog(self, cloud="SECURE", min_cuda=None):
        """``GET /catalog/gpus?include=AVAILABILITY&product=POD``: every GPU type with its price ({community, secure,
        serverless} $/h per GPU), ``memory`` GB, ``availability`` NONE/LOW/MEDIUM/HIGH for ``cloud`` and per data centre
        (docs.runpod.io/api-reference-v2/catalog/list-gpu-types; read live 2026-10-24)."""
        q = f"/catalog/gpus?include=AVAILABILITY&product=POD&cloud={cloud}"
        q += f"&minCudaVersion={min_cuda}" if min_cuda else ""
        page = self.request("GET", q) or {}
        return list(page.get("gpus", []) if isinstance(page, dict) else page)

    def logs(self, pid, tail=100, seconds=5, opener=None):
        """The last ``tail`` log lines (``GET /pods/{id}/logs``, server-sent events; the stream never ends, so it is read for
        ``seconds`` at most). Returns ``[(ts, source, line), ...]``."""
        url = f"{self.base}/pods/{pid}/logs?tail={int(tail)}"
        req = urllib.request.Request(url, headers={**self._headers(), "Accept": "text/event-stream"})
        out, end = [], time.time() + seconds
        try:
            with (opener or urllib.request.urlopen)(req, timeout=seconds) as r:
                while time.time() < end and len(out) < tail:
                    raw = r.readline()
                    if not raw:
                        break
                    line = raw.decode(errors="replace").strip()
                    if line.startswith("data:"):
                        try:
                            ev = json.loads(line[5:].strip())
                            out.append((ev.get("ts", ""), ev.get("source", ""), ev.get("line", "")))
                        except ValueError:
                            out.append(("", "", line[5:].strip()))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(f"GET /pods/{pid}/logs: 404", 404) from e
            raise RunPodError(f"GET /pods/{pid}/logs: HTTP {e.code}", e.code) from e
        except OSError:
            pass  # the stream paused: what was read is the answer
        return out


# --- which card: the cheapest JOB, not the cheapest hour (the creator, 2026-10-24) ---------------------------------
# A fast card at a higher hourly price often finishes the job for less, and on 2026-10-23/24 the $/h ceiling kept 80 GB
# cards out for hours while cheap cards had no stock. So the card is picked by the estimated cost of the job: the price
# from the live catalog / the card's speed x the job's hours on the reference card (A100 80GB = 1.0). SPEED is an
# engineering estimate for bf16 diffusion inference and training (engineering_experiment); a measured value in
# tools/runpod/speed.json ({"<gpu id>": factor}) wins. Cards without stock (availability NONE) are skipped, and so are
# MIG slices.
SPEED = {"NVIDIA A100 80GB PCIe": 0.95, "NVIDIA A100-SXM4-80GB": 1.0, "NVIDIA H100 80GB HBM3": 2.0, "NVIDIA H100 PCIe": 1.6,
         "NVIDIA H100 NVL": 1.8, "NVIDIA H200": 2.1, "NVIDIA B200": 3.0, "NVIDIA L40S": 0.9, "NVIDIA L40": 0.75,
         "NVIDIA A40": 0.5, "NVIDIA RTX A6000": 0.5, "NVIDIA RTX 6000 Ada Generation": 0.85,
         "NVIDIA RTX PRO 6000 Blackwell Server Edition": 1.3, "NVIDIA RTX PRO 6000 Blackwell Workstation Edition": 1.3,
         "NVIDIA GeForce RTX 5090": 1.1, "NVIDIA GeForce RTX 4090": 0.8, "NVIDIA GeForce RTX 3090": 0.45,
         "NVIDIA RTX A5000": 0.35, "NVIDIA L4": 0.3}
AVAIL_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def speeds():
    p = RP / "speed.json"
    try:
        return {**SPEED, **(json.loads(p.read_text()) if p.exists() else {})}
    except ValueError:
        return dict(SPEED)


def pick_gpus(api, *, vram_gb, ref_hours, clouds=("COMMUNITY", "SECURE"), min_cuda=CUDA_VERSIONS[0], max_price=None, limit=6):
    """The cards to try, cheapest estimated job first: rows {gpu, cloud, price, speed, hours, est_usd, availability}.
    ``ref_hours`` = the job's length on an A100 80GB. Only cards with at least ``vram_gb``, a known speed, stock now and
    a price at or under ``max_price`` (the creator's runaway ceiling per hour)."""
    sp, rows = speeds(), []
    for cloud in clouds:
        for g in api.catalog(cloud, min_cuda):
            gid, price = g.get("id", ""), float(((g.get("price") or {}).get(cloud.lower())) or 0)
            if "MIG" in gid or (g.get("memory") or 0) < vram_gb or price <= 0 or gid not in sp:
                continue
            if g.get("availability", "NONE") not in AVAIL_RANK or (max_price and price > max_price + 1e-9):
                continue
            hours = ref_hours / sp[gid]
            rows.append({"gpu": gid, "cloud": cloud, "price": price, "speed": sp[gid], "hours": round(hours, 2),
                         "est_usd": round(price * hours, 3), "availability": g["availability"]})
    rows.sort(key=lambda r: (r["est_usd"], AVAIL_RANK[r["availability"]]))
    return rows[:limit]


# --- names, money -------------------------------------------------------------------------------------------------
def pod_name(base, hours, now=None):
    """Unique name carrying the approved lifetime, so any session tells an approved pod from a forgotten one, and a create
    whose answer was lost can be found again."""
    now = time.time() if now is None else now
    return f"{base}-{secrets.token_hex(3)}-until-{int(now + hours * 3600)}"


def until_of(name):
    m = re.search(r"-until-(\d+)$", name or "")
    return int(m.group(1)) if m else None


def expired(name, now=None):
    u = until_of(name)
    return u is None or u < (time.time() if now is None else now)


def disk_per_hour(pod, running=True):
    """Dollars per hour for the pod's disks: what a stopped pod keeps costing."""
    pod = norm(pod) or {}
    vol, cont = float(pod.get("volumeInGb") or 0), float(pod.get("containerDiskInGb") or 0)
    gb_usd = (vol + cont) * GB_MONTH_RUNNING if running else vol * GB_MONTH_STOPPED
    return gb_usd / HOURS_PER_MONTH


def spent_estimate(sess, now, pod=None):
    """Compute + running disk since the session started. Stopped stretches inside a session are counted as running: the
    estimate errs high, never low. ``cost`` replaces it with RunPod's billed amount."""
    price = float((pod or {}).get("costPerHr") or sess.get("price") or 0)
    disk = disk_per_hour(pod or sess.get("pod_shape") or {}, True)
    return round(max(0.0, now - sess["started"]) / 3600 * (price + disk), 4)


# --- sessions (one file per pod) ------------------------------------------------------------------------------------
def sess_path(pid):
    return RP / "sessions" / f"{pid}.json"


def sess_write(sess):
    p = sess_path(sess["pod"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(sess, indent=1))
    os.replace(tmp, p)
    return sess


def sess_read(pid):
    p = sess_path(pid)
    return json.loads(p.read_text()) if p.exists() else None


def new_session(pod, *, max_usd, max_hours, on_cap="stop", ledger=None, now=None, status_token="", boot_minutes=BOOT_MINUTES,
                price_ceiling=None, job=None, heartbeat=None):
    """``price_ceiling`` stands in while a PROVISIONING pod reports cost 0: the money clock must never run on $0/h.
    ``job`` is the job record's directory (``cloud/jobs.py``) the guard writes to. ``heartbeat`` = the HF file the pod's
    script uploads every few minutes ("datasets/<owner>/<repo>:<path>"); the guard takes a fresh upload as the pod's sign of
    life and DONE / FAILED in it as the end of the job (``heartbeat_step``)."""
    pod = norm(pod)
    now = time.time() if now is None else now
    return sess_write({"pod": pod["id"], "name": pod.get("name", ""), "started": now,
                       "price": pod.get("costPerHr") or price_ceiling or 0.0,
                       "pod_shape": {"volumeInGb": pod.get("volumeInGb"), "containerDiskInGb": pod.get("containerDiskInGb")},
                       "max_usd": max_usd, "max_hours": max_hours, "until": until_of(pod.get("name")) or now + max_hours * 3600,
                       "boot_deadline": now + boot_minutes * 60, "on_cap": on_cap, "ledger": ledger, "status_token": status_token,
                       "answered": False, "ended": None, "job": str(job) if job else None, "heartbeat": heartbeat})


# --- heartbeat (2026-10-24, ≈$1.6 lost in one morning; ported from PR #22, LT-17/LT-19) -------------------------------
# What went wrong: (1) the pod record shows no runtime, machine or public IP for running script pods too, so a training
# pod that was working was read as "never got a machine" and stopped after 72 min (≈$1.3); (2) the same record never
# satisfies ``ready()`` for our script pods, so the guard stopped a rendering pod at its boot deadline (≈$0.3); (3) the
# pod scripts uploaded nothing before their first long stage, so nothing proved them alive.
# The rule: a pod's own upload is its only trusted sign of life. Every pod script starts a background upload loop
# (<= HEARTBEAT_EVERY_S) before its first heavy step (``lint_pod_script``, refused by ``preflight_create``); the guard
# reads the upload's time (``hf_heartbeat``), counts it as the answer that lifts the boot deadline, and on silence only
# pushes an alert: silence is never a reason to stop (caps and the lifetime still stop).
# 2026-10-24 evening (≈$0.7): a test ended at 20:56 Tbilisi time and its pod idled until 21:27, because the start command
# ends in ``tail -f /dev/null`` and nobody looked. Now the script's last line writes DONE (or FAILED) into its heartbeat
# file and stops its own pod (``self_stop_sh``); the guard stops a pod whose heartbeat says DONE or FAILED at once, and a
# dead-man timer inside the pod stops it at its approved lifetime even when every watcher outside is gone.
HEARTBEAT_EVERY_S = 300
SILENT_ALERT_MIN = 20
HEAVY_STEP = re.compile(r"snapshot_download|hf_hub_download|from_pretrained|pip install|git clone|\brun\.py\b|"
                        r"\bpython3?\s+(?!-)\S+\.py\b")
CUDA_PROBE = re.compile(r"\bpython3?\s+-c\b.*\bcuda\b")
BAD_HOST = "BAD_HOST"  # a pod script writes this into its heartbeat file when its GPU check fails or hangs
JOB_ENDED = re.compile(r"^\s*(DONE|FAILED)\b", re.M)  # the script's last word in its heartbeat file
UPLOAD_LOOP = re.compile(r"while\s+true;\s*do\s+sleep\s+(\d+);[^\n]*?\b(up|upload|upload_folder|hf\s+upload)\b[^\n]*?done\s*\)?\s*&")
SELF_STOP = re.compile(r"self_stop|/action\b.*\bstop\b|/stop\b|runpodctl\s+(stop\s+pod|pod\s+stop)")


def lint_pod_script(text):
    """Problems of a pod start script (empty = fine): it must upload its log in the background at least every
    HEARTBEAT_EVERY_S seconds, starting before its first heavy step (a download, an install, a model load, a training), wrap
    every CUDA probe in ``timeout``, and stop its own pod when it ends instead of idling in ``tail -f /dev/null``."""
    lines = text.splitlines()
    heavy = next((i for i, ln in enumerate(lines) if HEAVY_STEP.search(ln) and not ln.lstrip().startswith("#")), None)
    loops = [(i, int(m.group(1))) for i, ln in enumerate(lines) for m in [UPLOAD_LOOP.search(ln)] if m]
    out = []
    if not loops:
        out.append(f"no background upload loop (`( while true; do sleep <= {HEARTBEAT_EVERY_S}; date > out/beat.txt; up; done ) &`): "
                   "the pod would be invisible until its first stage ends")
    else:
        first, every = loops[0]
        if heavy is not None and first > heavy:
            out.append(f"the upload loop starts at line {first + 1}, after the first heavy step at line {heavy + 1} "
                       f"({lines[heavy].strip()[:60]}): start it before")
        if every > HEARTBEAT_EVERY_S:
            out.append(f"the upload loop sleeps {every} s > {HEARTBEAT_EVERY_S} s")
        if ">" not in lines[first].split("while", 1)[1]:
            # an upload skips unchanged files, so a heartbeat file the loop never rewrites keeps its old commit date and the
            # guard reads a live pod as silent (scene LoRA pod, 2026-10-24: stages.txt froze for the 2 h training stage)
            out.append("the upload loop must rewrite its heartbeat file every pass (`date > out/beat.txt; up`): an unchanged "
                       "file is not re-uploaded and looks silent")
    for i, ln in enumerate(lines):
        if CUDA_PROBE.search(ln) and not ln.lstrip().startswith(("#", "timeout ")):
            # chain pod 2026-10-24: `python -c "...torch.cuda.get_device_name(0)"` on a driver-550 host never returned;
            # the upload loop kept the pod "alive" for 12 min ($0.6) while nothing ran
            out.append(f"line {i + 1} touches CUDA without `timeout` ({ln.strip()[:60]}): a bad host hangs there; wrap it "
                       f"(`timeout 120 python -c ...`) and on failure write {BAD_HOST} to the heartbeat file so the guard stops the pod")
    code = [ln for ln in lines if not ln.lstrip().startswith("#")]
    if any("tail -f /dev/null" in ln for ln in code) and not any(SELF_STOP.search(ln) for ln in code):
        out.append("the script idles in `tail -f /dev/null` and never stops its pod: end it with `self_stop_sh()` (writes DONE "
                   "or FAILED to the heartbeat file, then stops the pod); 2026-10-24 a finished test idled 31 min ($0.7)")
    from explainer_engine import vault  # D-73 (VT-01/02): a training script proves its weights are on HF before it stops
    out += vault.lint_pod_script(text)
    return out


def self_stop_sh(beat="out/beat.txt"):
    """Shell lines for the end of a pod script: a ``self_stop`` function (v2 action, then the v1 route until 2026-11-15) and
    an EXIT trap that writes DONE or FAILED into the heartbeat file, uploads once more (``up`` when the script defines it)
    and stops the pod. ``RUNPOD_POD_ID`` and a key are set by RunPod in every pod (docs.runpod.io/pods/references/
    environment-variables: "Pod-scoped API key"); the restricted key from ``pod_env`` wins when present. When no key can stop
    the pod, the guard (DONE in the heartbeat) and the dead-man timer still do."""
    v2 = ('curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" '
          "-d '{\"action\":\"stop\"}' \"https://api.runpod.io/v2/pods/$RUNPOD_POD_ID/action\"")
    v1 = 'curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID/stop"'
    return "\n".join([
        f"self_stop() {{ {v2} >/dev/null 2>&1 || {v1} >/dev/null 2>&1 || echo 'self_stop: no key could stop this pod'; }}",
        f"on_exit() {{ rc=$?; mkdir -p \"$(dirname {beat})\"; if [ $rc -eq 0 ]; then echo \"DONE $(date -u +%FT%TZ)\" > {beat}; "
        f"else echo \"FAILED rc=$rc $(date -u +%FT%TZ)\" > {beat}; fi; type up >/dev/null 2>&1 && up; self_stop; }}",
        "trap on_exit EXIT"])


def dead_man_sh(seconds):
    """A background timer that stops the pod at its approved lifetime, whatever happens to every watcher outside it."""
    return f"( sleep {int(seconds)}; echo 'dead-man timer: approved lifetime over'; self_stop ) &"


def hf_heartbeat(spec, *, fetch=None):
    """Last commit time (epoch) of an HF file "datasets/<owner>/<repo>:<path>"; None while it does not exist yet."""
    kind_repo, path = spec.split(":", 1)
    url = f"https://huggingface.co/api/{kind_repo}/paths-info/main"
    if fetch is None:
        def fetch(url, data):
            tok = os.environ.get("HF_TOKEN", "")
            req = urllib.request.Request(url, urllib.parse.urlencode(data).encode(), method="POST",
                                         headers={"User-Agent": UA, **({"Authorization": f"Bearer {tok}"} if tok else {})})
            return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    rows = fetch(url, {"paths": path, "expand": "true"})
    date = next((r.get("lastCommit", {}).get("date") for r in rows or [] if r.get("path") == path), None)
    if not date:
        return None
    import datetime as _dt
    return _dt.datetime.fromisoformat(date.replace("Z", "+00:00")).timestamp()


def hf_text(spec, *, fetch=None):
    """The text of a small HF file "datasets/<owner>/<repo>:<path>" (the heartbeat file)."""
    kind_repo, path = spec.split(":", 1)
    url = f"https://huggingface.co/{kind_repo}/resolve/main/{path}"
    if fetch is None:
        def fetch(url):
            tok = os.environ.get("HF_TOKEN", "")
            req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Authorization": f"Bearer {tok}"} if tok else {})})
            return urllib.request.urlopen(req, timeout=20).read(4096).decode("utf-8", "replace")
    return fetch(url)


def heartbeat_step(sess, now, *, beat=hf_heartbeat, push=None, text=hf_text):
    """One heartbeat look for the guard: a fresh upload marks the pod as answered; a long silence after it pushes an alert
    (never a stop). A heartbeat that says BAD_HOST (the pod's own GPU check failed or hung) returns "bad_host", one that
    says DONE or FAILED returns "done": the guard stops that pod at once. Returns "alive", "silent", "waiting", "bad_host",
    "done" or None (no heartbeat configured / unreadable)."""
    if not sess.get("heartbeat"):
        return None
    try:
        t = beat(sess["heartbeat"])
    except Exception:  # noqa: BLE001 - HF unreachable: the money clock still works
        return None
    if t is not None and t >= sess["started"] - 60:
        changed = not sess.get("answered") or sess.get("heartbeat_at") != t
        sess.update(answered=True, heartbeat_at=t)
        if changed:
            try:
                said = text(sess["heartbeat"])
            except Exception:  # noqa: BLE001 - the date alone still proves life
                said = ""
            if BAD_HOST in said:
                sess["bad_host"] = said.strip()[:200]
            m = JOB_ENDED.search(said)
            if m:
                sess["job_ended"] = said[m.start():].strip()[:200]
            sess_write(sess)
    if sess.get("bad_host"):
        return "bad_host"
    if sess.get("job_ended"):
        return "done"
    if sess.get("heartbeat_at") is None:
        return "waiting"
    if now - sess["heartbeat_at"] > SILENT_ALERT_MIN * 60:
        if push and now - sess.get("silent_pushed", 0) > SILENT_ALERT_MIN * 60:
            sess["silent_pushed"] = now
            sess_write(sess)
            push("Pod is silent", f"{sess['pod']}: no upload for {(now - sess['heartbeat_at']) / 60:.0f} min; read its last "
                                  "log before stopping it (silence alone is not proof it is stuck)", "high")
        return "silent"
    return "alive"


def _job_of(sess):
    """The job record a session belongs to, or None (adopted pods and pods made before the record existed)."""
    if not sess or not sess.get("job"):
        return None
    try:
        from explainer_engine.cloud.jobs import Job
        return Job(sess["job"])
    except (OSError, ValueError):
        return None


# --- verified lifecycle ---------------------------------------------------------------------------------------------
def wait_status(api, pid, want, *, timeout=180, poll=5, clock=time.time, sleep=time.sleep):
    """Poll until status is in ``want`` ("GONE" = deleted). Returns the status seen; raises TimeoutError."""
    end = clock() + timeout
    while True:
        try:
            p = api.pod(pid)
            st = "GONE" if p is None else p.get("status")
            if st in want:
                return st
        except Unclear:
            pass
        if clock() >= end:
            raise TimeoutError(f"pod {pid} did not reach {'/'.join(want)} in {timeout} s")
        sleep(poll)


def stop(api, pid, *, timeout=180, **kw):
    """Idempotent, verified stop: done when GET shows EXITED (or ERROR: nothing to stop) or the pod is gone. REST ``action
    stop`` first, GraphQL podStop second."""
    p = api.pod(pid)
    if p is None or p.get("status") in ENDED:
        return "GONE" if p is None else p.get("status")
    errors = []
    for how in ("rest", "graphql"):
        try:
            if how == "rest":
                api.action(pid, "stop")
            else:
                api.graphql('mutation { podStop(input: {podId: "%s"}) { id desiredStatus } }' % pid)
        except NotFound:
            return "GONE"
        except RunPodError as e:
            errors.append(str(e))
            continue  # this way was refused: try the next one at once
        try:
            return wait_status(api, pid, ENDED + ("GONE",), timeout=timeout, **kw)
        except TimeoutError as e:
            errors.append(str(e))
    raise RunPodError(f"pod {pid} is still running after stop: " + "; ".join(errors)[:400])


def delete(api, pid, *, timeout=180, **kw):
    """Idempotent, verified delete (only on the creator's word). A 404 counts as done."""
    if api.pod(pid) is None:
        return "GONE"
    try:
        api.request("DELETE", f"/pods/{pid}")
    except NotFound:
        return "GONE"
    except RunPodError:
        api.graphql('mutation { podTerminate(input: {podId: "%s"}) }' % pid)
    return wait_status(api, pid, ("GONE",), timeout=timeout, **kw)


def find_by_name(api, name):
    return [p for p in api.pods() if p.get("name") == name and p.get("status") not in GONE]


def create(api, body, *, max_price, sleep=time.sleep, lookups=6, gpus=None):
    """POST /pods once per GPU type. After an unclear answer (timeout, 5xx) the pod is looked up by its unique name instead
    of POSTing again: a second POST could rent a second pod. A clear refusal (4xx: no capacity for that card) moves on to the
    next type of the pool; after an unclear answer with no pod found, nothing more is tried. A card dearer than ``max_price``
    is deleted at once (nothing is on it). ``gpus`` items are a GPU id or a ``(gpu id, cloud)`` pair (``pick_gpus``).
    The body must keep ``gpu.allowedCudaVersions`` (chain pod 2026-10-24: without the filter RunPod gave a driver-550 host,
    CUDA 12.4, to a CUDA 13 image and its first GPU call never returned; LT-19)."""
    if not (body.get("gpu") or {}).get("allowedCudaVersions"):
        raise RunPodError("create: the body has no gpu.allowedCudaVersions; an old-driver host can hang a new image "
                          f"(keep {CUDA_VERSIONS})")
    gpus = gpus or [body["gpu"]["id"]]
    pod, err = None, None
    for item in gpus:
        gpu, cloud = item if isinstance(item, (tuple, list)) else (item, body.get("cloud", "SECURE"))
        req = {**body, "gpu": {**body["gpu"], "id": gpu}, "cloud": cloud}
        try:
            pod = _post_once(api, req, sleep)
        except Unclear as e:
            err = e
            pod = _find_after_unclear(api, body["name"], sleep, lookups, err)
            break  # found or not, a lost answer is never followed by another POST
        except RunPodError as e:
            err = e
            if e.status in (401, 402):  # no balance or no valid key: no card will do (RunPod docs); stop the loop
                raise RunPodError(f"create refused for every card: {e}", e.status) from e
            continue  # refused before anything happened (no capacity for this card, 400): the next card
        if pod is not None:
            break
    if pod is None:
        raise RunPodError(f"create: no pod could be made for {gpus}: {err}") from err
    pod = norm(pod)
    price = float(pod.get("costPerHr") or 0)
    if price > max_price:
        delete(api, pod["id"])
        raise RunPodError(f"pod {pod['id']} costs ${price}/h, over the ${max_price}/h ceiling: deleted")
    return pod


def _post_once(api, body, sleep):
    for wait in (10, 30, 60, None):
        try:
            return api.request("POST", "/pods", body, retry=False)
        except Unclear as e:
            if e.status != 429 or wait is None:  # 429 = refused before anything happened: the only safe re-POST
                raise
            sleep(wait)


def _find_after_unclear(api, name, sleep, lookups, err):
    for _ in range(lookups):
        sleep(10)
        try:
            found = find_by_name(api, name)
        except Unclear:
            continue
        if len(found) > 1:
            raise RunPodError(f"{len(found)} pods named {name}: check and stop them by hand") from err
        if found:
            return found[0]
    raise RunPodError(f"create: no clear answer and no pod named {name} appeared; nothing is billing "
                      f"(run sweep to be sure): {err}") from err


def ready(pod):
    """The pod runs and its ports are mapped (v2: ``runtime.ports`` with a public port): the container is up."""
    pod = norm(pod)
    return bool(pod and pod.get("status") == "RUNNING" and pod.get("portMappings"))


def wait_ready(api, pid, *, timeout=BOOT_MINUTES * 60, poll=10, clock=time.time, sleep=time.sleep, probe=None):
    """Wait until the pod runs, has its ports and (if ``probe``) answers. Returns the pod; raises TimeoutError, after which
    the caller stops it (the guard does so at the boot deadline anyway)."""
    end = clock() + timeout
    while True:
        try:
            p = api.pod(pid)
        except Unclear:
            p = {}
        if p is None:
            raise RunPodError(f"pod {pid} is gone")
        if ready(p) and (probe is None or probe(p)):
            return p
        if clock() >= end:
            raise TimeoutError(f"pod {pid} not ready after {timeout} s (status {p.get('status')}, ip {p.get('publicIp')})")
        sleep(poll)


# --- guard ----------------------------------------------------------------------------------------------------------
def guard_check(sess, pod, now, conductor=None):
    """One look: (action, why). action is "ok", "end" (nothing left to guard) or "stop" (a cap, the boot deadline or an
    ERROR state). ``conductor`` is the first line of the pod's status page ("STATUS DONE ...") or None when it did not answer."""
    if pod is None:
        return "end", "pod is gone"
    if pod.get("status") == "ERROR":
        return "stop", "the pod is in ERROR: stopping it; the creator decides about its disk"
    if pod.get("status") not in ("RUNNING", "PROVISIONING", "STARTING"):
        return "end", f"pod is {pod.get('status')}"
    spent = spent_estimate(sess, now, pod)
    if spent >= sess["max_usd"]:
        return "stop", f"money cap: ${spent} of ${sess['max_usd']}"
    if (now - sess["started"]) / 3600 >= sess["max_hours"]:
        return "stop", f"time cap {sess['max_hours']} h"
    if sess.get("until") and now >= sess["until"]:
        return "stop", "the approved lifetime in the pod's name is over"
    if not sess.get("answered") and now > sess["boot_deadline"]:
        return "stop", "the pod never answered by its boot deadline"
    if conductor and any(conductor.startswith("STATUS " + e) for e in ("DONE", "STOPPED", "CAPPED")):
        if sess.get("ended") and now - sess["ended"] > 120:
            return "stop", "the conductor ended but the pod is still on"
    return "ok", f"${spent} of ${sess['max_usd']}"


def status_page(pod, token, timeout=20):
    """The conductor's status page (TMR cloud/status_server.py) through RunPod's proxy; a User-Agent is needed (403 without)."""
    url = f"https://{pod['id']}-8888.proxy.runpod.net/{token}/status"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode()


def notify(title, text, priority="urgent"):
    topic = os.environ.get("NTFY_TOPIC") or ((RP / "ntfy_topic.txt").read_text().strip() if (RP / "ntfy_topic.txt").exists() else "")
    if not topic:
        return False
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", text.encode(), {"Title": title.encode("ascii", "replace").decode(),
                                                                                "Priority": priority}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except OSError:
        return False


def end_pod(api, sess, why, *, push=notify, sleep=time.sleep, attempts=1000):
    """Stop (or with the creator's ``on_cap: delete``, delete) and never give up: a failed attempt is pushed and retried.
    When every attempt failed the session says so (``close_status`` "UNSTOPPED") and the loud push stands."""
    st = "UNSTOPPED"
    for attempt in range(1, attempts):
        try:
            st = delete(api, sess["pod"]) if sess.get("on_cap") == "delete" else stop(api, sess["pod"])
            break
        except (RunPodError, TimeoutError) as e:
            if attempt in (1, 3, 10) or attempt % 30 == 0:
                push("GUARD CANNOT STOP THE POD", f"{sess['pod']}: {why}; attempt {attempt}: {str(e)[:120]}")
            sleep(30)
    sess.update(closed=time.time(), close_why=why, close_status=st)
    sess_write(sess)
    job = _job_of(sess)
    if job is not None:
        from explainer_engine.cloud import incidents, jobs as J
        if st == "UNSTOPPED":
            job.move("RECOVERY_REQUIRED", f"the guard could not stop the pod: {why}", force=True)
        elif job.state["state"] in J.LIVE:  # FAILED / SUCCEEDED / RECOVERY_REQUIRED keep their meaning; the pod is just off
            job.move("STOPPED" if st != "ERROR" else "RECOVERY_REQUIRED", f"guard: {why}", force=True)
        else:
            job.event("pod", f"guard ended the pod ({st}): {why}")
        incidents.record(incidents.fingerprint("runpod", "pod", job.state.get("stage") or "any", text=why), f"guard ended {sess['pod']}: {why}",
                         cause=why, fix="stopped by the guard" if st != "UNSTOPPED" else "", source="guard", job=job.state["id"])
    disk = disk_per_hour(sess.get("pod_shape") or {}, running=False) * 24
    tail = f"; its disk bills ${disk:.2f}/day until deleted" if st in ENDED else ""
    push("Guard ended the pod" if st != "UNSTOPPED" else "GUARD GAVE UP: THE POD MAY STILL BILL",
         f"{sess['pod']} {st}: {why}; estimate ${spent_estimate(sess, time.time())}{tail}", "high" if st != "UNSTOPPED" else "urgent")
    return st


def guard(api, pid, *, clock=time.time, sleep=time.sleep, push=notify, page=status_page, poll=30, report_min=10, log=print,
          on_look=None):
    """Watch one pod until it is gone or stopped; stop it at a cap, at the end of its approved lifetime, when it never booted,
    or when its conductor ended. A blind API is never a reason to stop guarding; the local money clock keeps running and a
    cap reached while blind still triggers the stop attempts. ``on_look(pod, action, why)`` lets a job record follow along."""
    sess = sess_read(pid)
    if not sess:
        raise SystemExit(f"no session for {pid}: create it with this tool, or `adopt` it with its caps")
    job = _job_of(sess)
    if job is not None:
        from explainer_engine.cloud import jobs as J
    blind, last_report, last_line, last_beat = 0, 0.0, None, -1e18
    while True:
        now = clock()
        if sess.get("heartbeat") and now - last_beat >= 120:
            last_beat = now
            said = heartbeat_step(sess, now, push=push)
            if said in ("bad_host", "done") and not sess.get("closed"):
                why = (f"the pod reported a bad host: {sess['bad_host'][:80]}" if said == "bad_host"
                       else f"the job ended ({sess['job_ended'][:60]}): nothing left to pay for")
                end_pod(api, sess, why, push=push, sleep=sleep)
                return why
        try:
            pod = api.pod(pid)
            blind = 0
        except (Unclear, RunPodError):
            blind += 1
            if blind in (4, 20):
                push("Guard is blind", f"cannot reach RunPod for {blind * poll} s; {pid} may still be billing")
            pod = {"id": pid, "status": "RUNNING", "costPerHr": sess.get("price")}  # assume the worst
        if pod and pod.get("costPerHr") and pod["costPerHr"] != sess.get("price"):
            sess["price"] = pod["costPerHr"]  # a PROVISIONING pod reported no price; now it does
            sess_write(sess)
        conductor = None
        if pod and blind == 0 and sess.get("status_token"):
            try:
                conductor = page(pod, sess["status_token"]).strip().splitlines()[0]
                if not sess.get("answered"):
                    sess["answered"] = True
                    sess_write(sess)
            except Exception:  # noqa: BLE001 - the page may be down; the money clock still works
                pass
        elif ready(pod) and not sess.get("answered") and not sess.get("status_token"):
            sess["answered"] = True  # no status page for this pod: mapped ports are the sign of life
            sess_write(sess)
        if conductor and conductor.startswith(("STATUS DONE", "STATUS STOPPED", "STATUS CAPPED")) and not sess.get("ended"):
            sess["ended"] = now
            sess_write(sess)
        action, why = guard_check(sess, pod, now, conductor)
        if job is not None and blind == 0:
            moved = J.observe(job, pod, ready(pod), conductor, now=now)
            if moved in ("FAILED", "RECOVERY_REQUIRED"):
                from explainer_engine.cloud import incidents
                incidents.record(incidents.fingerprint("runpod", "pod", job.state.get("stage") or "any", text=job.state["reason"]),
                                 f"{pid}: {job.state['reason']}", cause=job.state["reason"], source="guard", job=job.state["id"])
                push("Pod job " + moved, f"{pid} {job.state['id']}: {job.state['reason']}", "urgent")
            if action == "ok":
                stalled = J.stall(job, now)
                if stalled and job.state["state"] != "STALLED":
                    job.move("STALLED", stalled, now=now, force=True)
                    push("Pod job stalled", f"{pid} {job.state['id']}: {stalled}", "high")
                elif job.state["state"] == "STALLED":
                    hb = job.last_heartbeat()
                    quiet = now - (hb["ts"] if hb else job.state["since"])
                    if quiet > 2 * J.STALL_AFTER.get("RUNNING", 1800):  # a stall that never recovers is an idle pod
                        if job.safe_to_release():
                            action, why = "stop", f"job stalled for {quiet / 60:.0f} min and every output is stored"
                        elif job.state["state"] != "RECOVERY_REQUIRED":
                            job.move("RECOVERY_REQUIRED", f"stalled {quiet / 60:.0f} min with unstored outputs", now=now, force=True)
                            push("Pod job needs a hand", f"{pid}: stalled with unstored outputs; not stopped", "urgent")
        if on_look:
            on_look(pod, action, why)
        if why != last_line:
            log(f"{time.strftime('%H:%M:%S')} {pid}: {action} {why}")
            last_line = why
        if action == "end":
            return why
        if action == "stop":
            end_pod(api, sess, why, push=push, sleep=sleep)
            return why
        if now - last_report >= report_min * 60:
            last_report = now
            push("Pod status", f"{pid}: {(now - sess['started']) / 60:.0f} min, {why}", "default")
        sleep(poll)


def guard_detached(pid):
    """The guard as its own process (a tool's time limit or the session's end must not kill it, TMR 2026-10-10)."""
    lock = RP / "sessions" / f"{pid}.guard"
    if lock.exists():
        try:
            os.kill(int(lock.read_text()), 0)
            return int(lock.read_text())  # one guard per pod
        except (OSError, ValueError):
            pass
    log = open(RP / "sessions" / f"{pid}.guard.log", "ab")
    flags = (getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) if os.name == "nt" else 0
    child = subprocess.Popen([sys.executable, "-m", "explainer_engine.cloud.runpod", "guard", pid], cwd=ROOT, stdout=log,
                             stderr=log, stdin=subprocess.DEVNULL, creationflags=flags, start_new_session=(os.name != "nt"))
    lock.write_text(str(child.pid))
    return child.pid


# --- sweep, cost ----------------------------------------------------------------------------------------------------
def sweep(api, *, dry=False, delete_exited=False, now=None):
    """Stop every RUNNING pod outside its approved lifetime; list every stopped pod with what its disk costs per day.
    One failing pod never stops the sweep. Deleting stopped pods needs ``delete_exited`` (the creator's word)."""
    now = time.time() if now is None else now
    rows = {"stopped": [], "failed": [], "running_ok": [], "exited": [], "deleted": []}
    for p in api.pods():
        st, pid = p.get("status"), p["id"]
        label = f"{pid} {p.get('name')} ${p.get('costPerHr')}/h"
        try:
            if st in ("RUNNING", "PROVISIONING", "STARTING") and expired(p.get("name"), now):
                if not dry:
                    stop(api, pid)
                rows["stopped"].append(label)
            elif st in ("RUNNING", "PROVISIONING", "STARTING"):
                rows["running_ok"].append(label)
            elif st in ENDED:
                day = disk_per_hour(p, running=False) * 24
                if delete_exited and not dry:
                    delete(api, pid)
                    rows["deleted"].append(f"{label} (disk ${day:.2f}/day)")
                else:
                    rows["exited"].append(f"{pid} {p.get('name')}: disk {p.get('volumeInGb')} GB = ${day:.2f}/day"
                                          + (" (ERROR state)" if st == "ERROR" else ""))
        except (RunPodError, TimeoutError) as e:
            rows["failed"].append(f"{label}: {str(e)[:120]}")
    return rows


def settle(api, pid, ledger_path=None):
    """RunPod's billed amount for the pod's session, written over the reservation in the run ledger (``runpod_usd``).
    Returns (usd, billed hour buckets); v2 billing has no billed seconds."""
    sess = sess_read(pid) or {}
    usd, buckets = api.billing(pid, sess.get("started") or time.time() - 86400)
    ledger_path = ledger_path or sess.get("ledger")
    if ledger_path:
        from explainer_engine.core.ledger import Run
        run = Run.open(ledger_path)
        run.settle("runpod_usd", f"pod:{pid}", usd)
        run.done("pods", pid, cost={"runpod_usd": usd}, billed_buckets=buckets, source="runpod billing", name=sess.get("name"))
    if sess:
        sess.update(billed_usd=usd, billed_buckets=buckets, settled=time.time())
        sess_write(sess)
    return usd, buckets


class PodSession:
    """``with PodSession(api, pid): ...``: the pod is stopped when the block ends, on an exception, on exit and on SIGTERM."""

    def __init__(self, api, pid, *, keep=False):
        self.api, self.pid, self.keep, self._old = api, pid, keep, None

    def _term(self, signum, frame):
        self.close()
        raise SystemExit(128 + signum)

    def __enter__(self):
        import atexit
        atexit.register(self.close)
        try:
            self._old = signal.signal(signal.SIGTERM, self._term)
        except ValueError:  # not the main thread
            pass
        return self

    def close(self):
        if not self.keep and self.pid:
            pid, self.pid = self.pid, None
            stop(self.api, pid)

    def __exit__(self, *exc):
        try:
            self.close()
        finally:
            if self._old is not None:
                signal.signal(signal.SIGTERM, self._old)
        return False


# --- the creator's ceilings and the account check (D-56) -------------------------------------------------------------
def live_guard(pid):
    """True when this machine runs a guard for the pod."""
    lock = RP / "sessions" / f"{pid}.guard"
    try:
        os.kill(int(lock.read_text()), 0)
        return True
    except (OSError, ValueError):
        return False


def _quiet(call):
    """(rows, error text): a listing that fails is reported as a problem by the caller, never a crash and never silence."""
    try:
        return call() or [], ""
    except (RunPodError, OSError, ValueError, TypeError, KeyError) as e:
        return [], f"{type(e).__name__}: {str(e)[:60]}"


def check(api, now=None):
    """The account as it bills now: problems (anything spending money that nobody approved or guards) and info lines.
    Run at the start and end of every session and after every pod job; the session hooks run it (cloud/hooks.py).
    A live pod without a session on this machine (the sandbox was recycled, or the pod was made elsewhere) is a problem:
    nobody here guards it."""
    now = time.time() if now is None else now
    keep = set(spend_caps.runpod().get("keep_stopped_pods", []))
    problems, info = [], []
    for p in api.pods():
        st, pid, name = p.get("status"), p["id"], p.get("name")
        if st in ("RUNNING", "PROVISIONING", "STARTING"):
            sess = sess_read(pid)
            line = f"{pid} {name} {st} ${p.get('costPerHr')}/h"
            if expired(name, now):
                problems.append(f"{line}: no approved lifetime left; stop it (`runpod sweep`)")
            elif sess is None:
                problems.append(f"{line}: no session here guards it (made elsewhere, or this machine restarted); "
                                f"`runpod adopt {pid} --max-usd X --max-hours H` or stop it")
            elif not sess.get("closed") and not live_guard(pid):
                problems.append(f"{line}: its guard is not running here; `runpod guard {pid}` or stop it")
            else:
                info.append(f"{line}, approved until {time.strftime('%H:%M UTC', time.gmtime(until_of(name)))}")
        elif st in ENDED:
            day = disk_per_hour(p, running=False) * 24
            line = f"{pid} {name} {'STOPPED' if st == 'EXITED' else 'in ERROR'}, disk {p.get('volumeInGb')} GB bills ${day:.2f}/day"
            (info if pid in keep else problems).append(line + ("" if pid in keep else
                                                               "; delete it with the creator's word (`runpod delete <pod> --yes`) or list it in keep_stopped_pods"))
    # the three ways an account bills with no pod: network volumes, global volumes, serverless workers kept on
    keep_nv = set(spend_caps.runpod().get("keep_network_volumes", []))
    for what, call in (("network volume", api.network_volumes), ("global volume", api.global_volumes), ("serverless endpoint", api.endpoints)):
        rows, err = _quiet(call)
        if err:
            problems.append(f"{what}s could not be listed ({err}): check them in the console; they bill without a pod")
        for r in rows:
            if what == "network volume":
                day = float(r["size"]) * GB_MONTH_NETWORK_VOLUME / HOURS_PER_MONTH * 24
                line = f"{r['id']} {r['name']} network volume {r['size']} GB bills ${day:.2f}/day with no pod"
                (info if r["id"] in keep_nv else problems).append(line + ("" if r["id"] in keep_nv else
                                                                    "; `runpod delete-volume <id> --yes` or list it in keep_network_volumes"))
            elif what == "global volume":
                (info if r["id"] in keep_nv else problems).append(f"{r['id']} {r['name']} global volume exists (price not modelled here); "
                                                                  "delete it in the console or list it in keep_network_volumes")
            elif r["workersMin"] > 0:
                problems.append(f"{r['id']} {r['name']} serverless endpoint keeps {r['workersMin']} worker(s) on while idle: set min workers 0")
    try:
        usd, _ = api.billing_total(now - 86400)
        bal = api.balance()
        info.append(f"billed in the last 24 h ${usd:.2f} of ${spend_caps.runpod()['per_24h_usd']} (every resource; the newest hour may lag); "
                    f"balance ${float(bal['clientBalance']):.2f}, spending ${float(bal.get('currentSpendPerHr') or 0):.3f}/h now")
    except RunPodError as e:
        problems.append(f"billing or balance not read ({str(e)[:80]}): the 24 h ceiling cannot be checked")
    return {"problems": problems, "info": info}


def preflight_create(api, *, max_usd, max_hours, gpu, now=None, ignore=None, script=None, picks=None):
    """Every reason to refuse a new pod (empty = allowed): the creator's ceilings, the last 24 h of billing, the balance,
    a clean account first (no stray pod, no unkept stopped disk), with ``script`` (the pod's start script text) the
    ``lint_pod_script`` rules, and with ``picks`` (``pick_gpus`` rows) a job that fits its approved money and time.
    The money line is per JOB (``per_pod_usd``); ``max_price_per_hour`` is only the runaway ceiling of one card."""
    now = time.time() if now is None else now
    c = spend_caps.runpod()
    why = [f"pod script: {p}" for p in lint_pod_script(script)] if script is not None else []
    if max_usd > c["per_pod_usd"]:
        why.append(f"--max-usd {max_usd} is above per_pod_usd {c['per_pod_usd']} (the per-job ceiling)")
    if max_hours > c["max_hours_per_pod"]:
        why.append(f"--max-hours {max_hours} is above max_hours_per_pod {c['max_hours_per_pod']}")
    if picks is not None:
        if not picks:
            why.append("no card with enough memory, a known speed and stock now under the runaway ceiling "
                       f"${c['max_price_per_hour']}/h")
        elif picks[0]["est_usd"] > max_usd + 1e-9 or picks[0]["hours"] > max_hours + 1e-9:
            best = picks[0]
            why.append(f"the cheapest job is {best['gpu']} ({best['cloud']}) ≈${best['est_usd']} in ≈{best['hours']} h: "
                       f"over the approved ${max_usd} / {max_hours} h")
    elif MAX_PRICE[gpu] > c["max_price_per_hour"] + 1e-9:
        why.append(f"the {gpu} card ceiling ${MAX_PRICE[gpu]}/h is above max_price_per_hour {c['max_price_per_hour']}")
    usd, _ = api.billing_total(now - 86400)
    if usd + max_usd > c["per_24h_usd"] + 1e-9:
        why.append(f"billed ${usd:.2f} in the last 24 h (every resource) + this pod's ${max_usd} passes per_24h_usd {c['per_24h_usd']}")
    bal = float(api.balance()["clientBalance"])
    if bal - max_usd < c["min_balance_left_usd"]:
        why.append(f"balance ${bal:.2f} - ${max_usd} leaves less than min_balance_left_usd {c['min_balance_left_usd']}")
    why += [f"clean up first: {p}" for p in check(api, now)["problems"] if not (ignore and p.startswith(ignore + " "))]
    return why


# --- create body ----------------------------------------------------------------------------------------------------
def secret(name, env):
    if os.environ.get(env):
        return os.environ[env].strip()
    p = RP / name
    return p.read_text().strip() if p.exists() else ""


def pod_env(status_token):
    """What the pod gets. ``RUNPOD_API_KEY`` inside the pod is only the RESTRICTED key (``tools/runpod/pod_api_key.txt`` or
    ``RUNPOD_POD_API_KEY``, scope pods:write): the boot command's self-stop needs it; without it the self-stop is a no-op
    and the guard's boot deadline does the stopping. The account key never goes into a pod."""
    env = {"STATUS_TOKEN": status_token, "NTFY_TOPIC": secret("ntfy_topic.txt", "NTFY_TOPIC"),
           "RUNPOD_API_KEY": secret("pod_api_key.txt", "RUNPOD_POD_API_KEY"),
           "HEARTBEAT_URL": secret("heartbeat_url.txt", "HEARTBEAT_URL"), "HF_TOKEN": secret("hf_token.txt", "HF_TOKEN"),
           "GITHUB_TOKEN": secret("github_token.txt", "GITHUB_TOKEN_RO") or secret("github_token.txt", "GITHUB_TOKEN"),
           "PUBLIC_KEY": secret("id_ed25519.pub", "RUNPOD_PUBLIC_KEY"), "TMR_BRANCH": os.environ.get("TMR_BRANCH", "")}
    return {k: v for k, v in env.items() if v}


def boot_cmd(manifest, branch):
    """The pod fetches TMR's bootstrap.sh and runs the manifest itself; PID 1 then stays alive (a returning start command
    restarts the container in a loop, TMR 2026-10-11). A failed boot stops the pod (stop, not delete: the creator's rule).
    v2 ``cmd`` is the container CMD in exec form."""
    url = f"https://raw.githubusercontent.com/{BOOT_REPO}/{branch}/cloud/bootstrap.sh"
    stop_self = self_stop_sh().split("\n")[0]
    # 2026-10-24: a finished job idled in `tail -f /dev/null`; the pod now stops itself when the manifest ends either way
    return ["bash", "-lc", f'set -o pipefail; {stop_self}; curl -fsSL -H "Authorization: token $GITHUB_TOKEN" '
            f'{url} | bash -s -- {manifest}; self_stop; tail -f /dev/null']


def script_cmd(script_url, lifetime_s):
    """The start command for a script pod (the LoRA, keyframe and video pods): a dead-man timer at the approved lifetime,
    the script fetched from HF with the pod's HF token, then the pod stops itself whatever the script's exit code; PID 1
    then stays alive only until the stop lands (a returning start command restarts the container in a loop)."""
    stop_self = self_stop_sh().split("\n")[0]
    return ["bash", "-c", f'{stop_self}; {dead_man_sh(lifetime_s)} mkdir -p /workspace; curl -fsSL -H "Authorization: Bearer $HF_TOKEN" '
            f'{script_url} -o /workspace/pod.sh && bash /workspace/pod.sh; self_stop; tail -f /dev/null']


def create_body(name, gpu="default", *, volume=VOLUME_GB, min_ram=None, boot=None, status_token="", image=None,
                script_url=None, lifetime_s=None, cloud="SECURE"):
    """The v2 ``POST /pods`` body for the FIRST card of the pool; ``create()`` swaps ``gpu.id`` (and the cloud) for the next
    cards. ``gpu`` is a pool name or a GPU id (``pick_gpus``)."""
    body = {"name": name, "image": image or IMAGE, "gpu": {"id": GPUS[gpu][0] if gpu in GPUS else gpu, "count": 1,
                                                           "allowedCudaVersions": CUDA_VERSIONS},
            "cloud": cloud, "disk": CONTAINER_GB, "mounts": {"persistent": {"size": volume, "path": "/workspace"}} if volume else {},
            "ports": ["22/tcp", "8888/http"], "env": pod_env(status_token)}
    if min_ram:
        body["gpu"]["minRamPerGpu"] = int(min_ram)
    if boot:
        body["cmd"] = boot_cmd(boot, os.environ.get("TMR_BRANCH") or "main")
    elif script_url:
        body["cmd"] = script_cmd(script_url, lifetime_s or 3600)
    return body


# --- CLI ------------------------------------------------------------------------------------------------------------
def _opt(argv, name, default=None, cast=str):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


def main(argv=None, api=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    cmd, rest = argv[0], argv[1:]
    pid = rest[0] if rest and not rest[0].startswith("--") else None
    api = api or Api()
    if cmd == "balance":
        print(json.dumps(api.balance()))
    elif cmd == "check":  # start and end of every session, after every pod job (D-56)
        res = check(api)
        for line in res["problems"]:
            print("PROBLEM", line)
        for line in res["info"]:
            print("ok     ", line)
        if res["problems"]:
            raise SystemExit(1)
    elif cmd == "cards":
        for r in pick_gpus(api, vram_gb=_opt(rest, "--vram", 24, float), ref_hours=_opt(rest, "--ref-hours", 1.0, float),
                           max_price=spend_caps.runpod()["max_price_per_hour"], limit=20):
            print(f"{r['est_usd']:7.3f} $  {r['gpu']} {r['cloud']} ${r['price']}/h x {r['hours']} h ({r['availability']})")
    elif cmd == "list":
        for p in api.pods():
            print(p["id"], p.get("name"), p.get("status"), f"${p.get('costPerHr')}/h", f"{p.get('volumeInGb')} GB", p.get("gpu") or "")
    elif cmd == "sweep":
        if "--delete" in rest and "--yes" not in rest:
            raise SystemExit("refused: deleting stopped pods needs --yes (the creator's word)")
        rows = sweep(api, dry="--dry-run" in rest, delete_exited="--delete" in rest)
        for k, v in rows.items():
            for line in v:
                print(f"{k:11} {line}")
        if not any(rows.values()):
            print("sweep: no pods")
        if rows["failed"]:
            notify("Sweep could not stop a pod", "; ".join(rows["failed"])[:300])
            raise SystemExit(1)
    elif cmd == "create":
        if "--yes" not in rest:
            raise SystemExit("refused: --yes only after the creator approved this pod's price and time cap")
        max_usd, max_hours = _opt(rest, "--max-usd", None, float), _opt(rest, "--max-hours", None, float)
        if not max_usd or not max_hours:
            raise SystemExit("create needs --max-usd and --max-hours (the approved caps)")
        gpu, ledger = _opt(rest, "--gpu", "default"), _opt(rest, "--ledger")
        if not ledger:
            raise SystemExit("create needs --ledger <episode run.json>: every pod is paid for by an episode")
        script_file, script_url = _opt(rest, "--script"), _opt(rest, "--script-url")
        if script_url and not script_file:
            raise SystemExit("--script-url needs --script <the same file, local>: the pod script is linted before any money")
        script = Path(script_file).read_text() if script_file else None
        picks = None
        if _opt(rest, "--vram"):  # the cheapest job among the cards with stock now (the creator, 2026-10-24)
            picks = pick_gpus(api, vram_gb=_opt(rest, "--vram", None, float), ref_hours=_opt(rest, "--ref-hours", max_hours, float),
                              max_price=spend_caps.runpod()["max_price_per_hour"])
            for r in picks:
                print(f"card  {r['gpu']} {r['cloud']} ${r['price']}/h x {r['hours']} h ≈ ${r['est_usd']} ({r['availability']})")
        why = preflight_create(api, max_usd=max_usd, max_hours=max_hours, gpu=gpu, script=script, picks=picks)
        if why:
            raise SystemExit("refused, no pod was made:\n  " + "\n  ".join(why))
        from explainer_engine.cloud.jobs import Job
        from explainer_engine.core.ledger import Run
        Run.open(ledger).reserve("runpod_usd", max_usd, item="pod:pending")  # refuses past 80 % of the episode's cap
        token = secrets.token_urlsafe(16)
        base = _opt(rest, "--name", "ee-" + (gpu if not picks else "auto"))
        name = pod_name(base, max_hours)
        first = picks[0] if picks else None
        body = create_body(name, first["gpu"] if first else gpu, volume=_opt(rest, "--volume", VOLUME_GB, int),
                           min_ram=_opt(rest, "--min-ram"), boot=_opt(rest, "--boot"), status_token=token,
                           image=_opt(rest, "--image"), script_url=script_url, lifetime_s=int(max_hours * 3600),
                           cloud=first["cloud"] if first else "SECURE")
        if _opt(rest, "--disk"):  # container disk (GB): a model download larger than the default CONTAINER_GB
            body["disk"] = _opt(rest, "--disk", None, int)
        job = Job.create(ROOT / "jobs" / "cloud", _opt(rest, "--job", base), kind="pod", provider="runpod", ledger=ledger,
                         caps={"max_usd": max_usd, "max_hours": max_hours}, reuse_finished=False,
                         inputs={"gpu": first["gpu"] if first else gpu, "boot": _opt(rest, "--boot"), "script": script_url,
                                 "volume": (body["mounts"].get("persistent") or {}).get("size", 0)})
        job.move("PROVISIONING", "POST /pods")
        card_max = max(r["price"] for r in picks) if picks else MAX_PRICE[gpu]
        try:
            pod = create(api, body, max_price=card_max,
                         gpus=[(r["gpu"], r["cloud"]) for r in picks if r["est_usd"] <= max_usd] if picks else GPUS[gpu])
        except RunPodError as e:
            Run.open(ledger).settle("runpod_usd", "pod:pending", 0.0)
            job.move("FAILED", f"create: {str(e)[:200]}")
            from explainer_engine.cloud import incidents
            incidents.record(incidents.fingerprint("runpod", "pod", "create", text=str(e)), f"create failed: {str(e)[:200]}",
                             cause=str(e)[:200], fix="", source="create", job=job.state["id"])
            raise
        Run.open(ledger).rename_reservation("pod:pending", f"pod:{pod['id']}")
        job.attach(pod["id"], gpu=pod.get("gpu"), price=pod.get("costPerHr"), name=name)
        new_session(pod, max_usd=max_usd, max_hours=max_hours, on_cap=_opt(rest, "--on-cap", "stop"), ledger=ledger,
                    status_token=token if _opt(rest, "--boot") else "", price_ceiling=card_max, job=job.dir,
                    heartbeat=_opt(rest, "--heartbeat"))
        print("pod", pod["id"], name, f"${pod.get('costPerHr')}/h", pod.get("gpu") or "", "job", job.state["id"])
        if "--no-guard" not in rest:
            print("guard pid", guard_detached(pod["id"]), f"log tools/runpod/sessions/{pod['id']}.guard.log")
    elif cmd in ("adopt", "start") and not (_opt(rest, "--max-usd") and _opt(rest, "--max-hours")):
        raise SystemExit(f"{cmd} needs --max-usd and --max-hours (the approved caps)")
    elif cmd == "adopt":  # a pod made elsewhere (TMR rp.py, the console): give it caps and a guard
        p = api.pod(pid)
        if p is None:
            raise SystemExit(f"{pid}: no such pod")
        new_session(p, max_usd=_opt(rest, "--max-usd", None, float), max_hours=_opt(rest, "--max-hours", None, float),
                    on_cap=_opt(rest, "--on-cap", "stop"), status_token=_opt(rest, "--status-token", ""),
                    price_ceiling=max(MAX_PRICE.values()))
        print("guard pid", guard_detached(pid))
    elif cmd == "status":
        p = api.pod(pid)
        sess = sess_read(pid)
        print("GONE" if p is None else f"{p.get('status')} ${p.get('costPerHr')}/h {p.get('gpu') or ''} ip {p.get('publicIp')} "
              f"ports {p.get('portMappings')} started {p.get('startedAt')} up {p.get('uptime')} s gpu util {p.get('util')}")
        if sess and p:
            print(f"estimate ${spent_estimate(sess, time.time(), p)} of ${sess['max_usd']}")
    elif cmd == "logs":
        for ts, source, line in api.logs(pid, tail=_opt(rest, "--tail", 100, int)):
            print(ts, source, line)
    elif cmd == "wait-ready":
        print("ready", wait_ready(api, pid, timeout=_opt(rest, "--timeout", BOOT_MINUTES * 60, int)).get("publicIp"))
    elif cmd == "guard":
        print(guard(api, pid))
    elif cmd == "stop":
        print(pid, stop(api, pid))
    elif cmd == "start":
        if "--yes" not in rest:
            raise SystemExit("refused: --yes only after the creator approved this start (price and caps)")
        why = preflight_create(api, max_usd=_opt(rest, "--max-usd", None, float), max_hours=_opt(rest, "--max-hours", None, float),
                               gpu=_opt(rest, "--gpu", "default"), ignore=pid)
        if why:
            raise SystemExit("refused, the pod stays stopped:\n  " + "\n  ".join(why))
        api.action(pid, "start")
        p = wait_ready(api, pid)
        new_session(p, max_usd=_opt(rest, "--max-usd", None, float), max_hours=_opt(rest, "--max-hours", None, float),
                    on_cap=_opt(rest, "--on-cap", "stop"), price_ceiling=MAX_PRICE[_opt(rest, "--gpu", "default")])
        print("started", pid, "guard pid", guard_detached(pid))
    elif cmd == "delete":
        if "--yes" not in rest:
            raise SystemExit("refused: delete needs --yes (the creator's word); the volume is lost")
        print(pid, delete(api, pid))
    elif cmd == "delete-volume":
        if "--yes" not in rest:
            raise SystemExit("refused: delete-volume needs --yes (the creator's word); the data is lost")
        print(pid, api.delete_network_volume(pid))
    elif cmd == "cost":
        usd, buckets = settle(api, pid, _opt(rest, "--ledger"))
        print(f"{pid}: billed ${usd} over {buckets} hour bucket(s) (RunPod billing; the newest hour may still grow)")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
