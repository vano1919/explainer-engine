# from vano1919/tmr-video-script-engine@f0abe62:cloud/rp.py
"""RunPod pod manager: create, wait, guard, stop, sweep and settle the cost. stdlib only. REST v2 (api.runpod.io/v2).

    python -m explainer_engine.cloud.runpod check | balance | list | sweep [--dry-run] [--delete --yes]
    python -m explainer_engine.cloud.runpod create --yes --max-usd X --max-hours H [--gpu default|cheap|big] [--boot <manifest>]
           --ledger <episode run.json> [--volume GB] [--min-ram GB] [--name base] [--on-cap stop|delete] [--no-guard]
           [--vram GB [--ref-hours H] [--only <card id substring>[,<more>]] [--cloud COMMUNITY|SECURE] [--wait-stock 15m]]   the cheapest JOB among the cards with stock now (pick_gpus), not a fixed pool
           [--script pod.sh --script-url <HF url of the same file>] [--heartbeat datasets/<o>/<r>:<file>] [--image I] [--disk GB] [--boot-minutes M]
    python -m explainer_engine.cloud.runpod dryrun --script pod.sh [--offline]   everything knowable before a pod bills (P1b, CR-18)
    python -m explainer_engine.cloud.runpod pins <pins.txt>   a pod's pins.txt against config/cloud_pins.json
    python -m explainer_engine.cloud.runpod cards --vram GB [--ref-hours H] [--job <type> --units N [--setup-min M]]   what the job costs per card
    python -m explainer_engine.cloud.runpod status|logs|wait-ready|guard|stop|cost <pod> ;  delete <pod> --yes ;  start <pod> --yes ...
    python -m explainer_engine.cloud.runpod delete-volume <network volume id> [--global] --yes

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

import hashlib
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
# boot pods retired (OR-21, N-01): a scriptless `create` and a body without pod_wrapper.sh refuse; IMAGE and BOOT_REPO stay as history
OR21 = ("pods start only with their script committed under explainer_engine/training/pods/ (OR-21); the TMR boot pod is retired")
PREFLIGHT_KEY = "_ee_preflight"  # written only by preflight_create(body=...); popped by create() before the HTTP call
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

    def delete_global_volume(self, vid):
        """``DELETE /global-volumes/{id}``; verified by listing again (the creator's word only, the data is lost)."""
        try:
            self.request("DELETE", f"/global-volumes/{vid}")
        except NotFound:
            pass
        return "STILL THERE" if any(v["id"] == vid for v in self.global_volumes()) else "GONE"

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


def pick_gpus(api, *, vram_gb, ref_hours, clouds=("COMMUNITY", "SECURE"), min_cuda=CUDA_VERSIONS[0], max_price=None, limit=6,
              job=None, units=None, setup_min=None, refused=None):
    """The cards to try, cheapest estimated job first: rows {gpu, cloud, price, speed, hours, est_usd, availability, basis,
    setup_share}. ``ref_hours`` = the job's length on an A100 80GB. Only cards with at least ``vram_gb``, stock now and a price at
    or under ``max_price`` (the creator's runaway ceiling per hour). How a card's hours are known (``basis``, P1c): a row measured
    for ``job`` x card in ``config/job_speeds.json`` (with ``units``) wins; else the SPEED estimate; a card neither knows is NOT
    skipped but taken at the slowest known speed times ``margin_unmeasured`` (it sorts last, never out). With a setup time
    (``setup_min`` or the measured row's) a card whose fixed setup is over ``setup_share_max`` of the pod's time is dropped
    (RP-09; the reasons are appended to ``refused``)."""
    from explainer_engine.cloud import batching, speeds as S
    sp, rows = speeds(), []
    tab = S.load()
    for cloud in clouds:
        for g in api.catalog(cloud, min_cuda):
            gid, price = g.get("id", ""), float(((g.get("price") or {}).get(cloud.lower())) or 0)
            if "MIG" in gid or (g.get("memory") or 0) < vram_gb or price <= 0:
                continue
            if g.get("availability", "NONE") not in AVAIL_RANK or (max_price and price > max_price + 1e-9):
                continue
            m = S.estimate(job, gid, units, tab) if job else None
            if m:
                hours, basis, setup_h = m["work_h"], "measured", (setup_min / 60 if setup_min is not None else m["setup_h"] if m["setup_known"] else None)
                speed = None
            elif gid in sp:
                hours, basis, speed, setup_h = ref_hours / sp[gid], "estimate", sp[gid], (setup_min / 60 if setup_min is not None else None)
            else:
                speed = min(sp.values())
                hours, basis, setup_h = ref_hours / speed * float(tab["margin_unmeasured"]), f"unknown card x{tab['margin_unmeasured']:g}", \
                    (setup_min / 60 if setup_min is not None else None)
            share = S.setup_share(setup_h, hours) if setup_h is not None else None
            total = hours + (setup_h or 0)
            rows.append({"gpu": gid, "cloud": cloud, "price": price, "speed": speed, "hours": round(total, 2),
                         "est_usd": round(price * total, 3), "availability": g["availability"], "basis": basis,
                         "setup_share": None if share is None else round(share, 3)})
    rows = batching.rp09(rows, share_max=float(tab["setup_share_max"]), refused=refused)
    rows.sort(key=lambda r: (r["est_usd"], AVAIL_RANK[r["availability"]]))
    return rows[:limit]


def only_cards(picks, only):
    """The creator names the card (2026-10-26): keep the picks whose id contains ``only``; ``only`` may be a comma list of such
    names (a pick is kept when it contains any of them). Every name must match a card with stock: one that matches none is
    refused with a did-you-mean (a typo used to be dropped silently and the pod landed on whichever card was left, G15)."""
    if only is None:
        return picks
    names = [n.strip() for n in only.split(",") if n.strip()]
    if not names:
        raise SystemExit(f"--only {only!r} names no card: give a card id or part of one (a comma list is fine)")
    for n in names:
        if not any(n in r["gpu"] for r in picks):
            import difflib
            ids = sorted({r["gpu"] for r in picks})
            near = difflib.get_close_matches(n, ids, n=1, cutoff=0.4)
            raise SystemExit(f"--only {only!r}: no card with stock matches {n!r}"
                             + (f" (did you mean {near[0]!r}?)" if near else f" (cards with stock now: {', '.join(ids) or 'none'})"))
    return [r for r in picks if any(n in r["gpu"] for n in names)]


CLOUDS = ("COMMUNITY", "SECURE")


# What ``create`` reads (a flag that is not here is refused, so a typo or a flag from another command is never silently ignored, G15).
CREATE_VALUE_FLAGS = ("--boot", "--boot-minutes", "--cap-grace-s", "--cloud", "--disk", "--drill", "--gpu", "--heartbeat", "--image",
                      "--job", "--job-type", "--ledger", "--max-hours", "--max-usd", "--min-ram", "--name", "--on-cap", "--only",
                      "--pass-s", "--hw-extra-retries", "--hw-extra-reason", "--ref-hours", "--rules", "--script", "--script-url", "--second-pod-reason", "--setup-min", "--test", "--units",
                      "--upload-grace-s", "--volume", "--vram", "--wait-stock", "--work-min")
CREATE_BOOL_FLAGS = ("--measure", "--no-guard", "--yes")
PICK_ONLY_FLAGS = ("--only", "--cloud", "--ref-hours", "--wait-stock")  # read only when --vram picks the card


def create_flag_problems(rest):
    """Refusals for the flags of a ``create`` command line (empty = fine): an unknown flag, and a flag that only means something
    with ``--vram`` given without it (it used to be ignored, and the pod landed on the default pool at its dearer price)."""
    import difflib
    out, known, i = [], CREATE_VALUE_FLAGS + CREATE_BOOL_FLAGS, 0
    while i < len(rest):
        t = rest[i]
        if t.startswith("--"):
            if t not in known:
                near = difflib.get_close_matches(t, known, n=1)
                out.append(f"unknown flag {t}" + (f" (did you mean {near[0]}?)" if near else "") + ": create reads only its own flags")
            elif t in CREATE_VALUE_FLAGS:
                if i + 1 >= len(rest) or not rest[i + 1].strip() or rest[i + 1] in known:
                    out.append(f"{t} needs a value")  # an empty value used to count as 'not given' and fell back to the default
                i += 1
        i += 1
    if "--vram" not in rest:
        out += [f"{f} only works with --vram GB (without it the default pool is used and {f} is ignored)" for f in PICK_ONLY_FLAGS if f in rest]
    cloud = _opt(rest, "--cloud")
    if cloud is not None and cloud.upper() not in CLOUDS:
        out.append(f"--cloud {cloud!r} is not one of {CLOUDS}")
    if "--vram" in rest and "--cloud" not in rest:  # both clouds mixed: EE_PRICE (the dead-man's price) is the dearest of the two
        out.append(f"--vram needs --cloud {'|'.join(CLOUDS)} (without it both clouds are mixed and the dead-man's price is the dearer one)")
    return out


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
                price_ceiling=None, job=None, heartbeat=None, stall_s=None, extra=None):
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
                       "answered": False, "ended": None, "job": str(job) if job else None, "heartbeat": heartbeat,
                       "stall_s": stall_s, **(extra or {})})


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
WATCHDOG_FRESH_S = 3600  # CR-07b
UPLOAD_FAIL_PUSH, UPLOAD_FAIL_RECOVERY = 3, 6  # consecutive failed uploads (CR-10)
UPLOAD_GRACE_S, CAP_GRACE_S = 900, 300  # the pod's final upload before a normal end / before a cap stop (CR-04, CR-11)
HEAVY_STEP = re.compile(r"snapshot_download|hf_hub_download|from_pretrained|pip install|git clone|\brun\.py\b|"
                        r"\bpython3?\s+(?!-)\S+\.py\b")
CUDA_PROBE = re.compile(r"\bpython3?\s+-c\b.*\bcuda\b")
BAD_HOST = "BAD_HOST"  # the wrapper writes this word when its GPU check fails or hangs (CR-06)
END_WORDS = ("DONE", "FAILED", "FAILED_UPLOAD", "CAPPED", "BAD_HOST")  # the pod's last word in beat.txt (CR-02)
BEAT_WORDS = ("ALIVE",) + END_WORDS
BEAT_LINE = re.compile(r"^(?P<word>FAILED_UPLOAD|ALIVE|DONE|FAILED|CAPPED|BAD_HOST)(?:\s+rc=(?P<rc>-?\d+))?(?:\s+(?P<ts>\d{4}-\d\d-\d\dT\S+))?"
                       r"(?:\s+progress=(?P<progress>.*?)\s+upload_fail=(?P<fail>\d+)\s+unstored=(?P<unstored>\d+))?\s*$")
BOOT_LINE = re.compile(r"^BOOT\s+(.*)$")
JOB_ENDED = re.compile(r"^\s*(DONE|FAILED)\b", re.M)  # kept for old-style heartbeat files
UPLOAD_LOOP = re.compile(r"while\s+true;\s*do\s+sleep\s+(\d+);[^\n]*?\b(up|upload|upload_folder|hf\s+upload)\b[^\n]*?done\s*\)?\s*&")
SELF_STOP = re.compile(r"(^|[;&|(\s])self_stop(\s|$|;)|/action\b.*\bstop\b|/stop\b|runpodctl\s+(stop\s+pod|pod\s+stop)")
WRAPPER = Path(__file__).with_name("pod_wrapper.sh")


def parse_beat(text):
    """beat.txt (CR-02) as a dict: ``boot`` {key, job, pod, price, deadline} from the BOOT line, and from the last status line
    ``word`` (ALIVE/DONE/FAILED/FAILED_UPLOAD/CAPPED/BAD_HOST or None for an old-style date-only heartbeat), ``rc``, ``ts``,
    ``progress``, ``upload_fail``, ``unstored``. Old files (``DONE 2026-10-24T17:00Z``, ``FAILED rc=1``) still parse."""
    out = {"boot": {}, "word": None, "rc": None, "ts": None, "progress": "", "upload_fail": 0, "unstored": 0}
    for raw in (text or "").splitlines():
        line = raw.strip()
        m = BOOT_LINE.match(line)
        if m:
            out["boot"] = dict(kv.split("=", 1) for kv in m.group(1).split() if "=" in kv)
            continue
        m = BEAT_LINE.match(line)
        if m:
            out.update(word=m.group("word"), rc=int(m.group("rc")) if m.group("rc") is not None else None, ts=m.group("ts"),
                       progress=(m.group("progress") or "").strip(), upload_fail=int(m.group("fail") or 0),
                       unstored=int(m.group("unstored") or 0))
        elif BAD_HOST in line:  # an old script writing "BAD_HOST <why>"
            out.update(word=BAD_HOST)
    return out


def deadline_of(created, lifetime_s, max_usd, price, disk_per_h=0.0, grace=CAP_GRACE_S):
    """The pod's own money/time deadline (epoch, CR-05): created + min(lifetime, max_usd / (price + disk per hour)) - grace.
    The wrapper computes the same number with awk; ``test_pod_wrapper`` keeps the two together."""
    secs = float(lifetime_s or 0)
    if max_usd and (price + disk_per_h) > 0:
        by_money = max_usd / (price + disk_per_h) * 3600
        secs = by_money if secs <= 0 or by_money < secs else secs
    return int(created + secs - grace)


def is_wrapper_script(text):
    """A job script written for ``pod_wrapper.sh``: it declares its heartbeat or writes under ``$EE_OUT``. The scripts under
    ``training/pods/`` from before P1a run their own loop and write their own DONE; P1b rewrites the ones that are reused."""
    return heartbeat_of_script(text) is not None or "EE_OUT" in (text or "")


def lint_pod_script(text):
    """Problems of a pod job script that runs inside ``pod_wrapper.sh`` (empty = fine, CR-08): the wrapper owns beat.txt, the
    upload loop, the end word and the stop, so a script that writes them, idles, touches CUDA without ``timeout`` or sends
    base weights to the vault is refused. VT-01/02 (the vault check) stay. A pre-P1a script (``is_wrapper_script`` false) is
    judged by its own old rules; ``preflight_create`` refuses to run it under the wrapper."""
    if not is_wrapper_script(text):
        from explainer_engine import vault
        return lint_own_upload_loop(text) + vault.lint_pod_script(text)
    lines = text.splitlines()
    code = [(i, ln) for i, ln in enumerate(lines) if not ln.lstrip().startswith("#")]
    out = []
    for i, ln in code:
        if "beat.txt" in ln or re.search(r"\becho\s+['\"]?(DONE|FAILED)\b", ln):
            out.append(f"line {i + 1} writes the heartbeat or an end word ({ln.strip()[:60]}): the pod wrapper owns beat.txt and DONE/FAILED "
                       "(write progress to $EE_OUT/progress.txt instead)")
        if "tail -f /dev/null" in ln or "sleep infinity" in ln:
            out.append(f"line {i + 1} idles ({ln.strip()[:40]}): the wrapper stops the pod when the script ends")
        if CUDA_PROBE.search(ln) and not ln.lstrip().startswith("timeout "):
            # chain pod 2026-10-24: a driver-550 host never returned from the first CUDA call and $0.6 went on a hung probe
            out.append(f"line {i + 1} touches CUDA without `timeout` ({ln.strip()[:60]}): a bad host hangs there; wrap it "
                       "(`timeout 120 python -c ...`); the wrapper already runs the GPU check")
        if re.search(r"snapshot_download|hf_hub_download|huggingface-cli\s+download|hf\s+download", ln) and re.search(r"/workspace/out|\$EE_OUT|\$\{EE_OUT\}", ln):
            out.append(f"line {i + 1} downloads into the output folder ({ln.strip()[:60]}): the wrapper uploads $EE_OUT whole, base weights must "
                       "never reach the vault (download to /workspace/dl)")
        if re.search(r"HF_HOME=\S*(/workspace/out|\$EE_OUT|\$\{EE_OUT\})", ln):
            out.append(f"line {i + 1} puts the HF cache under the output folder: it would be uploaded to the vault")
        if "upload_folder" in ln and re.search(r"folder_path\s*=\s*[\"'][^\"']*(/dl|/hf|cache|HF_HOME)", ln):
            out.append(f"line {i + 1} uploads a download or cache directory: only results go to the vault")
    from explainer_engine import vault  # D-73 (VT-01/02): a training script proves its weights are on HF before it stops
    out += vault.lint_pod_script(text)
    return out


def lint_own_upload_loop(text):
    """The pre-wrapper rule (kept for scripts that still run their own loop, e.g. boot manifests of other repos): the script
    uploads its log in the background at least every HEARTBEAT_EVERY_S seconds, starting before its first heavy step."""
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
            out.append("the upload loop must rewrite its heartbeat file every pass (`date > out/beat.txt; up`): an unchanged "
                       "file is not re-uploaded and looks silent")
    for i, ln in enumerate(lines):
        if CUDA_PROBE.search(ln) and not ln.lstrip().startswith(("#", "timeout ")):
            out.append(f"line {i + 1} touches CUDA without `timeout` ({ln.strip()[:60]}): a bad host hangs there; wrap it "
                       f"(`timeout 120 python -c ...`) and on failure write {BAD_HOST} to the heartbeat file so the guard stops the pod")
    code = [ln for ln in lines if not ln.lstrip().startswith("#")]
    if any("tail -f /dev/null" in ln for ln in code) and not any(SELF_STOP.search(ln) for ln in code):
        out.append("the script idles in `tail -f /dev/null` and never stops its pod: end it with `self_stop` (2026-10-24 a finished test "
                   "idled 31 min, $0.7)")
    return out


def heartbeat_of_script(text):
    """``# heartbeat: datasets/<owner>/<repo>:<path>/beat.txt`` declared in the script (CR-07), or None."""
    m = re.search(r"^#\s*heartbeat:\s*(\S+)", text or "", re.M)
    return m.group(1) if m else None


def stall_minutes_of_script(text):
    """``# stall-minutes: N``: how long the script's progress line may stand still while beats stay fresh (CR-09), or None."""
    m = re.search(r"^#\s*stall-minutes:\s*(\d+)", text or "", re.M)
    return int(m.group(1)) if m else None


def self_stop_sh():
    """Shell for a ``self_stop`` function (v2 ``action stop``, then GraphQL ``podStop``; no v1 route, CR-15). ``pod_wrapper.sh``
    carries the same function; ``boot_cmd`` uses this one. ``RUNPOD_POD_ID`` and a key are set by RunPod in every pod; the
    restricted key from ``pod_env`` wins when present. When no key can stop the pod, the guard and the watchdog still do."""
    v2 = ('curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" '
          "-d '{\"action\":\"stop\"}' \"https://api.runpod.io/v2/pods/$RUNPOD_POD_ID/action\"")
    gql = ('curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" '
           "-d \"{\\\"query\\\":\\\"mutation { podStop(input: {podId: \\\\\\\"$RUNPOD_POD_ID\\\\\\\"}) { id } }\\\"}\" https://api.runpod.io/graphql")
    return f"self_stop() {{ {v2} >/dev/null 2>&1 || {gql} >/dev/null 2>&1 || echo 'self_stop: no key could stop this pod'; }}"


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
    """One heartbeat look for the guard (CR-09/10): a fresh upload marks the pod as answered; the beat is parsed (``parse_beat``) and
    its word, progress and upload failures are kept in the session. Returns "bad_host" (the wrapper's GPU check failed),
    "done" (DONE / FAILED / FAILED_UPLOAD / CAPPED: the job ended, stop at once), "silent" (no upload for SILENT_ALERT_MIN, alert
    only: silence is never a reason to stop), "waiting" (nothing uploaded yet), "alive" or None (no heartbeat configured or HF
    unreachable). ``sess["progress_at"]`` is the time of the last change of the script's progress line (stall rule of the guard)."""
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
            b = parse_beat(said)
            if b["boot"].get("key") and sess.get("key") != b["boot"]["key"]:
                sess["key"] = b["boot"]["key"]
                if sess["key"] != "200" and push:
                    push("Pod cannot stop itself", f"{sess['pod']}: the in-pod key probe answered {sess['key']}; only the guard and "
                                                    "the watchdog can stop this pod", "high")
            if b["progress"] != sess.get("progress"):
                sess.update(progress=b["progress"], progress_at=t)
            elif sess.get("progress_at") is None:
                sess["progress_at"] = t
            sess.update(upload_fail=b["upload_fail"], unstored=b["unstored"], word=b["word"])
            if b["word"] == BAD_HOST or (b["word"] is None and BAD_HOST in said):
                sess["bad_host"] = said.strip()[:200]
            elif b["word"] in END_WORDS:
                sess["job_ended"] = f"{b['word']}" + (f" rc={b['rc']}" if b["rc"] is not None else "")
                if b["word"] == "FAILED_UPLOAD":
                    sess["job_ended_unstored"] = b["unstored"]
            elif b["word"] is None and JOB_ENDED.search(said):  # an old-style file
                m = JOB_ENDED.search(said)
                sess["job_ended"] = said[m.start():].strip()[:200]
            if push and b["upload_fail"] >= UPLOAD_FAIL_PUSH and sess.get("upload_fail_pushed", 0) < b["upload_fail"] // UPLOAD_FAIL_PUSH:
                sess["upload_fail_pushed"] = b["upload_fail"] // UPLOAD_FAIL_PUSH
                push("Pod uploads are failing", f"{sess['pod']}: {b['upload_fail']} uploads in a row failed, {b['unstored']} file(s) "
                                                "not on HF yet; the pod is not stopped for it", "urgent" if b["upload_fail"] >= UPLOAD_FAIL_RECOVERY else "high")
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


def beat_stall(sess, now, limit_s=None):
    """(why) when a script pod's beats are fresh but its progress line has not changed for longer than the limit (CR-09), else
    ''. A script that never writes progress.txt cannot be judged: beats alone are life. ``limit_s`` defaults to the session's
    ``stall_s`` or the RUNNING limit of the job record."""
    from explainer_engine.cloud import jobs as J
    limit = limit_s or sess.get("stall_s") or J.STALL_AFTER["RUNNING"]
    if not sess.get("progress") or sess.get("progress_at") is None or sess.get("heartbeat_at") is None:
        return ""
    if now - sess["heartbeat_at"] > 2 * HEARTBEAT_EVERY_S + 120:
        return ""  # the beats are not fresh: that is silence, handled elsewhere
    quiet = now - sess["progress_at"]
    return f"progress {sess['progress']!r} unchanged for {quiet / 60:.0f} min (limit {limit / 60:.0f})" if quiet > limit else ""


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


def preflight_stamp(body: dict) -> str:
    """sha256 of the body without its stamp: ``create()`` sends only the exact body ``preflight_create`` passed (N-01)."""
    core = {k: v for k, v in body.items() if k != PREFLIGHT_KEY}
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def create(api, body, *, max_price, sleep=time.sleep, lookups=6, gpus=None):
    """POST /pods once per GPU type. After an unclear answer (timeout, 5xx) the pod is looked up by its unique name instead
    of POSTing again: a second POST could rent a second pod. A clear refusal (4xx: no capacity for that card) moves on to the
    next type of the pool; after an unclear answer with no pod found, nothing more is tried. A card dearer than ``max_price``
    is deleted at once (nothing is on it). ``gpus`` items are a GPU id, a ``(gpu id, cloud)`` pair or a ``(gpu id, cloud, $/h)`` triple (``pick_gpus``).
    The body must keep ``gpu.allowedCudaVersions`` (chain pod 2026-10-24: without the filter RunPod gave a driver-550 host,
    CUDA 12.4, to a CUDA 13 image and its first GPU call never returned; LT-19).
    Only a body stamped by ``preflight_create(body=...)`` is sent (N-01): the CLI's refusals cannot be skipped by calling this
    function directly, and a body changed after the preflight is refused too. The stamp guards against a forgotten preflight,
    not against code that forges it (``preflight_stamp`` is public): what the body alone decides is checked here again, so even
    a forged stamp sends no boot pod and no unpinned image, and the session hook refuses a Python create outside the CLI."""
    stamp = body.pop(PREFLIGHT_KEY, None)
    if stamp is None or stamp != preflight_stamp(body):
        raise RunPodError("refused: create() takes only a body stamped by preflight_create (OR-21, D-56); "
                          "use python -m explainer_engine.cloud.runpod create")
    from explainer_engine.cloud import pins
    why = ([] if body.get("cmd") == script_cmd() else [f"the body does not run pod_wrapper.sh ({OR21})"])
    why += [f"image: {p} (config/cloud_pins.json)" for p in pins.check_image(body.get("image"))]
    if why:
        raise RunPodError("refused: " + "; ".join(why))
    if not (body.get("gpu") or {}).get("allowedCudaVersions"):
        raise RunPodError("create: the body has no gpu.allowedCudaVersions; an old-driver host can hang a new image "
                          f"(keep {CUDA_VERSIONS})")
    gpus = gpus or [body["gpu"]["id"]]
    pod, err = None, None
    for item in gpus:
        gpu, cloud, *rest = item if isinstance(item, (tuple, list)) else (item, body.get("cloud", "SECURE"))
        req = {**body, "gpu": {**body["gpu"], "id": gpu}, "cloud": cloud}
        if rest and "EE_PRICE" in (body.get("env") or {}):  # the wrapper's dead-man runs on this card's price (CR-05)
            req["env"] = {**body["env"], "EE_PRICE": str(rest[0])}
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
        raise RunPodError(f"create: no pod could be made for {[g[0] if isinstance(g, (tuple, list)) else g for g in gpus]}: {err}") from err
    pod = norm(pod)
    price = float(pod.get("costPerHr") or 0)
    if price > max_price:
        delete(api, pod["id"])
        raise RunPodError(f"pod {pod['id']} costs ${price}/h, over the ${max_price}/h ceiling: deleted")
    return pod


def adopt_pending(api, lv, *, job, heartbeat, now=None):
    """CR-12 / T22 / T24: a create that wrote its live spec and then lost the answer (the process died, the POST timed out) left a spec
    with no pod. Before a new create POSTs again, every such spec of this job and heartbeat is looked up by its pod name: a pod
    found is adopted (its id is written into the spec, the caller makes no POST); no pod and a lifetime that has passed moves the stale
    spec to ``closed`` (as the watchdog does); no pod and time left is left alone (the old POST may still land: the watchdog sees the
    name). Returns (pod, spec) of the adopted pod, or (None, None). A listing that fails is a refusal: no blind second POST."""
    from explainer_engine.cloud import hf_live
    now = time.time() if now is None else now
    for name, spec in hf_live.pending(lv.specs(), job=job, heartbeat=heartbeat).items():
        try:
            found = find_by_name(api, name)
        except Unclear as e:
            raise RunPodError(f"create: the pods could not be listed to check the earlier create {name} ({e}); not POSTing again") from e
        if len(found) > 1:
            raise RunPodError(f"{len(found)} pods named {name}: check and stop them by hand")
        if found:
            pod = norm(found[0])
            spec = {**spec, "pod": pod["id"]}
            lv.write_spec(spec)
            return pod, spec
        if (until_of(name) or spec.get("until") or 0) < now:
            lv.close_spec(name)
    return None, None


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


def notify_topic():
    return os.environ.get("NTFY_TOPIC") or ((RP / "ntfy_topic.txt").read_text().strip() if (RP / "ntfy_topic.txt").exists() else "")


def notify(title, text, priority="urgent"):
    """Push to the creator's phone. Every push is recorded in ``tools/runpod/notify.jsonl`` with its outcome (CR-14): a lost push
    is data, not silence. Returns whether it was delivered."""
    topic, ok = notify_topic(), False
    if topic:
        try:
            req = urllib.request.Request(f"https://ntfy.sh/{topic}", text.encode(), {"Title": title.encode("ascii", "replace").decode(),
                                                                                    "Priority": priority}, method="POST")
            urllib.request.urlopen(req, timeout=15).read()
            ok = True
        except OSError:
            ok = False
    try:
        RP.mkdir(parents=True, exist_ok=True)
        with open(RP / "notify.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "title": title[:80], "ok": ok, "topic": bool(topic)}) + "\n")
    except OSError:
        pass
    return ok


def failed_pushes(since, path=None):
    """Recorded pushes that did not arrive since ``since`` (epoch)."""
    p = path or RP / "notify.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not r.get("ok") and r.get("ts", 0) >= since:
            rows.append(r)
    return rows


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
            if sess.get("unstored"):  # CR-11: stopped (cap, lifetime) while the last beat said files were not on HF yet
                job.move("RECOVERY_REQUIRED", f"guard: {why}; the last beat said {sess['unstored']} file(s) were not on HF", force=True)
            else:
                job.move("STOPPED" if st != "ERROR" else "RECOVERY_REQUIRED", f"guard: {why}", force=True)
        else:
            job.event("pod", f"guard ended the pod ({st}): {why}")
        incidents.record(incidents.fingerprint("runpod", "pod", job.state.get("stage") or "any", text=why), f"guard ended {sess['pod']}: {why}",
                         cause=why, fix="stopped by the guard" if st != "UNSTOPPED" else "", source="guard", job=job.state["id"])
    disk = disk_per_hour(sess.get("pod_shape") or {}, running=False) * 24
    tail = f"; its disk bills ${disk:.2f}/day until deleted" if st in ENDED else ""
    if sess.get("unstored") and st != "UNSTOPPED":
        tail += f"; {sess['unstored']} file(s) were not on HF at the last beat: check the pod's volume before deleting it"
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
                ended = sess.get("job_ended") or ""
                if said == "bad_host":
                    why = f"the pod reported a bad host: {sess['bad_host'][:80]}"
                else:
                    why = f"the job ended ({ended[:60]}): nothing left to pay for"
                if (said == "bad_host" or ended.startswith("FAILED_UPLOAD")) and job is not None:
                    job.move("RECOVERY_REQUIRED", why + (f"; {sess.get('unstored', 0)} file(s) may not be on HF" if said == "done" else ""),
                             now=now, force=True)
                    push("Pod job needs a hand", f"{pid}: {why}", "urgent")
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
        script_pod = bool(sess.get("heartbeat"))
        if job is not None and blind == 0 and script_pod and pod and pod.get("status") in ("RUNNING", "PROVISIONING", "STARTING"):
            # CR-09: a script pod lives by its HF beat; the REST view never changes for it, so it never drives a stall
            if sess.get("heartbeat_at") is not None and sess.get("job_beat_at") != sess["heartbeat_at"]:
                sess["job_beat_at"] = sess["heartbeat_at"]
                job.heartbeat("script", sess.get("progress") or "beat", now=now, source="hf")
                if job.state["state"] in ("PROVISIONING", "STARTING", "MODEL_LOADING", "READY"):
                    job.move("RUNNING", "first heartbeat from the pod", now=now, force=True)
                if (sess.get("upload_fail", 0) >= UPLOAD_FAIL_RECOVERY and sess.get("unstored") and not sess.get("recovery_marked")
                        and job.state["state"] in J.LIVE):  # CR-10: a person must look; the pod keeps running (outputs are only on it)
                    sess["recovery_marked"] = True
                    job.move("RECOVERY_REQUIRED", f"{sess['upload_fail']} uploads in a row failed with {sess['unstored']} file(s) "
                                                  "not on HF; the pod is kept running until they are stored", now=now, force=True)
            limit = sess.get("stall_s") or J.STALL_AFTER["RUNNING"]
            stalled = beat_stall(sess, now)
            if action == "ok" and stalled:
                if job.state["state"] != "STALLED":
                    job.move("STALLED", stalled, now=now, force=True)
                    push("Pod job stalled", f"{pid} {job.state['id']}: {stalled}", "high")
                elif beat_stall(sess, now, 2 * limit) and not sess.get("upload_fail"):
                    action, why = "stop", f"progress stood still for {2 * limit / 60:.0f} min while the pod kept uploading: {sess.get('progress')!r}"
            elif job.state["state"] == "STALLED" and not stalled:
                job.move("RUNNING", "the progress moved again", now=now, force=True)
        elif job is not None and blind == 0:
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
AUTO_DELETE_AFTER_S = 24 * 3600  # D-92: a stopped pod with nothing on its disks is deleted 24 h after its approved life ended


def auto_delete_due(pod, now=None):
    """D-92 (creator, 2026-11-01): True for a stopped pod that bills nothing (0 GB persistent volume: whatever was on the container
    disk is gone, the results live on the vault) and whose approved lifetime (``-until-<epoch>`` in its name) ended at least 24 h
    ago. A pod without a valid until, or with any volume, is never deleted by this rule."""
    now = time.time() if now is None else now
    pod = norm(pod) or {}
    if pod.get("status") not in ENDED or float(pod.get("volumeInGb") or 0) > 0:
        return False
    until = until_of(pod.get("name"))
    return until is not None and now >= until + AUTO_DELETE_AFTER_S


def sweep(api, *, dry=False, delete_exited=False, now=None):
    """Stop every RUNNING pod outside its approved lifetime; list every stopped pod with what its disk costs per day.
    One failing pod never stops the sweep. Deleting stopped pods needs ``delete_exited`` (the creator's word)."""
    now = time.time() if now is None else now
    rows = {"stopped": [], "failed": [], "running_ok": [], "exited": [], "deleted": [], "auto_deleted": []}
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
                if auto_delete_due(p, now) and not delete_exited:
                    if dry:
                        rows["auto_deleted"].append(f"{label} (would delete: 0 GB, 24 h past its until)")
                    else:
                        delete(api, pid)
                        rows["auto_deleted"].append(f"{label} (0 GB, 24 h past its until)")
                elif delete_exited and not dry:
                    delete(api, pid)
                    rows["deleted"].append(f"{label} (disk ${day:.2f}/day)")
                else:
                    rows["exited"].append(f"{pid} {p.get('name')}: disk {p.get('volumeInGb')} GB = ${day:.2f}/day"
                                          + (" (ERROR state)" if st == "ERROR" else ""))
        except (RunPodError, TimeoutError) as e:
            rows["failed"].append(f"{label}: {str(e)[:120]}")
    return rows


def settle(api, pid, ledger_path=None, extra=None):
    """RunPod's billed amount for the pod's session, written over the reservation in the run ledger (``runpod_usd``).
    Returns (usd, billed hour buckets); v2 billing has no billed seconds."""
    sess = sess_read(pid) or {}
    usd, buckets = api.billing(pid, sess.get("started") or time.time() - 86400)
    ledger_path = ledger_path or sess.get("ledger")
    if ledger_path:
        from explainer_engine.core.ledger import Run
        run = Run.open(ledger_path)
        run.settle("runpod_usd", f"pod:{pid}", usd)
        run.done("pods", pid, cost={"runpod_usd": usd}, billed_buckets=buckets, source="runpod billing", name=sess.get("name"),
                 **(extra or {}))
    if sess:
        sess.update(billed_usd=usd, billed_buckets=buckets, settled=time.time())
        sess_write(sess)
    return usd, buckets


SETTLE_AFTER_S = 90 * 60  # RunPod's billing lags up to an hour behind the stop (RP-07)


def cost_report(api, pid, ledger_path=None, *, fetch=None, now=None):
    """``cost``: settle the pod's billed amount into the ledger (RP-06), keep the pod's outcome for the retry rule (RP-10), write
    the pod's measured speed into ``config/job_speeds.json`` from its ``units.json`` (RP-08) and return a dict with the PROGRESS-ready
    ``line``. The pod id is required: a cost without a pod is not a cost."""
    from explainer_engine.cloud import speeds
    if not pid:
        raise SystemExit("cost needs the pod id: `runpod cost <pod>` (a cost is settled per pod, RP-07)")
    sess = sess_read(pid) or {}
    hb = sess.get("heartbeat")
    texts = {}
    if hb:
        kind_repo, path = hb.split(":", 1)
        folder = path.rpartition("/")[0]
        for name in ("beat.txt", speeds.UNITS_JSON):
            try:
                texts[name] = hf_text(f"{kind_repo}:{folder + '/' if folder else ''}{name}", fetch=fetch)
            except (OSError, ValueError):
                texts[name] = None
    usd, buckets = settle(api, pid, ledger_path)  # the bill is real whatever the pod's own files say: settle before parsing them
    units_row, speed_note = None, None
    if texts.get(speeds.UNITS_JSON):
        try:
            units_row = speeds.from_units_json(texts[speeds.UNITS_JSON])
        except speeds.SpeedError as e:
            speed_note = f"no speed row: {e}"
    if units_row and (ledger_path or sess.get("ledger")):
        from explainer_engine.core.ledger import Run
        run = Run.open(ledger_path or sess["ledger"])
        run.done("pods", pid, **{**(run.data["items"].get("pods", {}).get(pid) or {}), "units": units_row["units"],
                                 "job_type": units_row["job_type"], "usd_per_unit": round(usd / float(units_row["units"]), 5)})
    if units_row and sess.get("gpu"):
        try:
            speeds.record(units_row["job_type"], sess["gpu"], cloud=sess.get("cloud") or "", units=float(units_row["units"]),
                          work_s=float(units_row["work_s"]), setup_s=units_row.get("setup_s"), mb=units_row.get("mb"),
                          download_s=units_row.get("download_s"), usd=usd, source=f"pod {pid} {sess.get('name', '')}".strip(), now=now)
            speed_note = f"speed row written: {units_row['job_type']} on {sess['gpu']}"
        except speeds.SpeedError as e:
            speed_note = f"no speed row: {e}"
    elif units_row:
        speed_note = "no speed row: the session does not know the card (adopted pod)"
    word = parse_beat(texts.get("beat.txt") or "")["word"]
    ledger = ledger_path or sess.get("ledger")
    if ledger and sess.get("job_base") and word and not sess.get("outcome_recorded"):
        from explainer_engine.core.ledger import Run
        run = Run.open(ledger)
        if word == BAD_HOST:
            run.fail(f"hw:{sess['job_base']}", f"pod {pid}: BAD_HOST")
        elif word in ("FAILED", "FAILED_UPLOAD") and sess.get("script_sha"):
            run.fail(f"script:{sess['job_base']}:{sess['script_sha'][:12]}", f"pod {pid}: {word}")
        sess = sess_read(pid) or sess  # settle() wrote settled/billed_usd after the read at the top: do not write them away
        sess["outcome_recorded"] = word
        sess_write(sess)
    per = f", ${usd / float(units_row['units']):.4f}/unit ({units_row['job_type']} x{units_row['units']})" if units_row else ""
    line = f"pod {pid} ({sess.get('name', '?')}, {sess.get('gpu', '?')} {sess.get('cloud', '')}): ${usd:.2f} billed{per}"
    RP.mkdir(parents=True, exist_ok=True)
    with open(RP / "settled.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"pod": pid, "usd": usd, "line": line, "at": time.time() if now is None else now}) + "\n")
    return {"usd": usd, "buckets": buckets, "line": line, "word": word, "speed": speed_note}


def settle_due(api, *, now=None, after_s=SETTLE_AFTER_S, fetch=None):
    """Settle every closed session whose pod stopped at least ``after_s`` ago and whose bill is not in the ledger yet (RP-07, the
    session hook runs it). Returns the PROGRESS-ready lines."""
    now = time.time() if now is None else now
    out = []
    for f in sorted((RP / "sessions").glob("*.json")):
        try:
            s = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if s.get("closed") and not s.get("settled") and s.get("ledger") and now - s["closed"] >= after_s:
            try:
                r = cost_report(api, s["pod"], fetch=fetch, now=now)
                out.append(r["line"] + (f" [{r['speed']}]" if r.get("speed") and "units.json" in r["speed"] else ""))
            except (RunPodError, OSError, ValueError, KeyError) as e:
                out.append(f"pod {s.get('pod')}: settle failed ({str(e)[:80]}); `runpod cost {s.get('pod')}`")
    return out


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
    problems, info, live_n = [], [], 0
    pods = api.pods()
    stored_day, stored_n, stored_gb = 0.0, 0, 0.0
    for p in pods:
        st, pid, name = p.get("status"), p["id"], p.get("name")
        if st in ("RUNNING", "PROVISIONING", "STARTING"):
            live_n += 1
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
            stored_day, stored_n, stored_gb = stored_day + day, stored_n + 1, stored_gb + float(p.get("volumeInGb") or 0)
            line = f"{pid} {name} {'STOPPED' if st == 'EXITED' else 'in ERROR'}, disk {p.get('volumeInGb')} GB bills ${day:.2f}/day"
            (info if pid in keep else problems).append(line + ("" if pid in keep else
                                                               "; delete it with the creator's word (`runpod delete <pod> --yes`) or list it in keep_stopped_pods"))
    if stored_n:  # P1c: one line, whatever the number of stopped pods
        info.append(f"stopped pods keep {stored_gb:g} GB of volume: ${stored_day:.2f}/day in total over {stored_n} pod(s)")
    gone = sorted(keep - {p["id"] for p in pods})
    if gone:  # the list in config/spend_caps.json is noise once RunPod no longer knows an id; removing one is the creator's edit
        info.append(f"{len(gone)} id(s) in keep_stopped_pods no longer exist on RunPod (remove them from config/spend_caps.json "
                    f"with the creator's word): {', '.join(gone[:5])}{' ...' if len(gone) > 5 else ''}")
    if live_n:  # CR-14: a live pod with no way to reach the creator is a problem
        if not notify_topic():
            problems.append(f"{live_n} live pod(s) and no NTFY_TOPIC: pushes about them go nowhere")
        lost = failed_pushes(now - 86400)
        if lost:
            problems.append(f"{len(lost)} push(es) in the last 24 h did not arrive (last: {lost[-1]['title']!r})")
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
                                                                  "`runpod delete-volume <id> --global --yes` or list it in keep_network_volumes")
            elif r["workersMin"] > 0:
                problems.append(f"{r['id']} {r['name']} serverless endpoint keeps {r['workersMin']} worker(s) on while idle: set min workers 0")
    try:
        usd, _ = api.billing_total(now - 86400)
        bal = api.balance()
        spend = float(bal.get("currentSpendPerHr") or 0)
        info.append(f"billed in the last 24 h ${usd:.2f} of ${spend_caps.runpod()['per_24h_usd']} (every resource; the newest hour may lag); "
                    f"balance ${float(bal['clientBalance']):.2f}, spending ${spend:.3f}/h now")
        if spend > 1e-6 and not live_n and not stored_gb:  # RunPod bills something this manager sees no pod and no volume for
            problems.append(f"RunPod says it spends ${spend:.3f}/h now, and no pod is live and no stopped pod keeps a volume: something bills "
                            "outside this manager (a serverless endpoint, a network volume, a pod of another account member): look in the console")
    except RunPodError as e:
        problems.append(f"billing or balance not read ({str(e)[:80]}): the 24 h ceiling cannot be checked")
    return {"problems": problems, "info": info}


def preflight_create(api, *, max_usd, max_hours, gpu, now=None, ignore=None, script=None, picks=None, heartbeat=None,
                     pod_key=False, watchdog_age=None, image=None, boot_minutes=None, cloud=None, body=None):
    """Every reason to refuse a new pod (empty = allowed): the creator's ceilings, the last 24 h of billing, the balance,
    a clean account first (no stray pod, no unkept stopped disk), with ``script`` (the pod's start script text) the
    ``lint_pod_script`` rules, a passing ``dryrun`` of exactly that text and an image pinned by digest in ``config/cloud_pins.json``
    that has the boot minutes it needs on its cloud (P1b, CR-18), and with ``picks`` (``pick_gpus`` rows) a job that fits its
    approved money and time.
    The money line is per JOB (``per_pod_usd``); ``max_price_per_hour`` is only the runaway ceiling of one card.
    With ``body`` (the ``create_body`` that will be sent: every creation passes it) a script is required, the body must run the
    wrapper and its own ``image`` must be a digest pinned in ``config/cloud_pins.json``; with no refusal the body is stamped in
    place (``PREFLIGHT_KEY``), and ``create()`` sends nothing else (N-01). Without ``body`` (``start`` of a stopped pod, the
    ceiling checks) nothing is stamped."""
    now = time.time() if now is None else now
    c = spend_caps.runpod()
    why = [f"pod script: {p}" for p in lint_pod_script(script)] if script is not None else []
    if body is not None:
        from explainer_engine.cloud import pins
        if script is None:
            why.append(f"no --script: {OR21}")
        elif body.get("cmd") != script_cmd():
            why.append("the body does not run pod_wrapper.sh (pass --script-url <the HF url of the same script>; CR-01)")
        why += [f"image: {p} (config/cloud_pins.json)" for p in pins.check_image(body.get("image"))]
    if script is not None and not is_wrapper_script(script):
        why.append("pod script: it runs its own upload loop and writes its own beat.txt/DONE (pre-P1a protocol): rewrite it for "
                   "pod_wrapper.sh (declare `# heartbeat:`, write results under $EE_OUT; CR-08, P1b)")
    if script is not None:  # CR-18 (P1b): the script was read and its repos looked up, the image is a pinned digest
        from explainer_engine.cloud import dryrun, pins
        why += [f"dryrun: {p}" for p in dryrun.passed(script)]
        img = body.get("image") if body is not None else (image or pins.image_ref(pins.DEFAULT_IMAGE))
        if body is None:  # with a body its own image was checked above
            why += [f"image: {p}" for p in pins.check_image(img)]
        cl = cloud or (picks[0]["cloud"] if picks else "SECURE")
        need = pins.boot_minutes_needed(img, cl)
        if (boot_minutes if boot_minutes is not None else BOOT_MINUTES) + 1e-9 < need:
            why.append(f"image: {img.partition('@')[0]} is not measured on a {cl} host: the pod needs --boot-minutes >= {need:g} "
                       f"(the guard would stop it at {boot_minutes if boot_minutes is not None else BOOT_MINUTES:g} min, before the image arrives)")
    if script is not None:  # CR-07: a script pod must be visible and stoppable from outside this session
        if not heartbeat:
            why.append("no heartbeat: pass --heartbeat datasets/<owner>/<repo>:<folder>/beat.txt or declare `# heartbeat: ...` in the script")
        if not pod_key and (watchdog_age is None or watchdog_age > WATCHDOG_FRESH_S):
            why.append("no stop path outside this session: there is no restricted in-pod key (RUNPOD_POD_API_KEY or tools/runpod/"
                       "pod_api_key.txt) and the GitHub watchdog has not run in the last 60 min "
                       f"({'never recorded' if watchdog_age is None else f'{watchdog_age / 60:.0f} min ago'})")
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
    if body is not None and not why:
        body[PREFLIGHT_KEY] = preflight_stamp(body)
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
    v2 ``cmd`` is the container CMD in exec form. The boot pods of TMR keep this form; script pods use ``script_cmd``.
    Retired (OR-21, N-01): kept as text; a body that runs it is refused by ``preflight_create(body=...)`` (not the wrapper), so
    ``create()`` never sends one."""
    url = f"https://raw.githubusercontent.com/{BOOT_REPO}/{branch}/cloud/bootstrap.sh"
    stop_self = self_stop_sh()
    # 2026-10-24: a finished job idled in `tail -f /dev/null`; the pod now stops itself when the manifest ends either way
    return ["bash", "-lc", f'set -o pipefail; {stop_self}; curl -fsSL -H "Authorization: token $GITHUB_TOKEN" '
            f'{url} | bash -s -- {manifest}; self_stop; tail -f /dev/null']


def script_cmd():
    """The start command of a script pod (CR-01): ``pod_wrapper.sh`` itself. The script's URL, the approved lifetime and
    money and the HF folder come in through the pod's env (``wrapper_env``), so the command is the same text for every job."""
    return ["bash", "-c", WRAPPER.read_text()]


def hf_target(heartbeat):
    """("owner/repo", "folder") of a heartbeat spec ``datasets/<owner>/<repo>:<folder>/beat.txt`` (the wrapper uploads $EE_OUT
    there, so the folder and the beat cannot disagree, CR-07a)."""
    kind_repo, path = heartbeat.split(":", 1)
    repo = kind_repo.split("/", 1)[1] if kind_repo.startswith("datasets/") else kind_repo
    folder, _, name = path.rpartition("/")
    if name != "beat.txt":
        raise RunPodError(f"heartbeat {heartbeat!r} must end in beat.txt (the wrapper's file)")
    return repo, folder


DRILLS = ("no_self_stop", "drop_key", "upload_fail")


def wrapper_env(script_url, *, heartbeat, max_usd, lifetime_s, price, job=None, created=None, volume=VOLUME_GB, container=CONTAINER_GB,
                pass_s=None, upload_grace_s=None, cap_grace_s=None, drill=None):
    """The EE_* env the wrapper reads (CR-05): what it needs for the dead-man and for the upload. ``pass_s`` / ``upload_grace_s`` /
    ``cap_grace_s`` scale the loop and the graces (the P12a drills use 120 / 300 / 120 s); ``drill`` is a P12a fault, see ``main create``."""
    repo, folder = hf_target(heartbeat)
    from explainer_engine.cloud import pins
    hf_pin = (pins.load()["pip"].get("huggingface_hub") or {}).get("version")  # the wrapper installs it when the image lacks it
    disk_h = (float(volume or 0) + float(container or 0)) * GB_MONTH_RUNNING / HOURS_PER_MONTH
    return {"EE_SCRIPT_URL": script_url, "EE_CREATED": str(int(time.time() if created is None else created)),
            "EE_LIFETIME_S": str(int(lifetime_s)), "EE_MAX_USD": str(max_usd), "EE_PRICE": str(price), "EE_DISK_H": f"{disk_h:.5f}",
            "EE_JOB": str(job or ""), "EE_HF_REPO": repo, "EE_HF_PREFIX": folder,
            **{k: str(int(v)) for k, v in (("EE_PASS_S", pass_s), ("EE_UPLOAD_GRACE_S", upload_grace_s), ("EE_CAP_GRACE_S", cap_grace_s))
               if v is not None},
            **({"EE_DRILL": drill} if drill else {}), **({"EE_HF_PIN": hf_pin} if hf_pin else {})}


def create_body(name, gpu="default", *, volume=VOLUME_GB, min_ram=None, boot=None, status_token="", image=None,
                script_url=None, lifetime_s=None, cloud="SECURE", heartbeat=None, max_usd=None, job=None, price=None, scale=None,
                drill=None):
    """The v2 ``POST /pods`` body for the FIRST card of the pool; ``create()`` swaps ``gpu.id`` (and the cloud, and EE_PRICE) for
    the next cards. ``gpu`` is a pool name or a GPU id (``pick_gpus``). A script pod needs ``heartbeat`` and ``max_usd``."""
    body = {"name": name, "image": image or IMAGE, "gpu": {"id": GPUS[gpu][0] if gpu in GPUS else gpu, "count": 1,
                                                           "allowedCudaVersions": CUDA_VERSIONS},
            "cloud": cloud, "disk": CONTAINER_GB, "mounts": {"persistent": {"size": volume, "path": "/workspace"}} if volume else {},
            "ports": ["22/tcp", "8888/http"], "env": pod_env(status_token)}
    if min_ram:
        body["gpu"]["minRamPerGpu"] = int(min_ram)
    if boot:  # retired (OR-21): a body without the wrapper's cmd is never stamped by preflight_create, so create() never sends it
        body["cmd"] = boot_cmd(boot, os.environ.get("TMR_BRANCH") or "main")
    elif script_url:
        if not heartbeat or not max_usd:
            raise RunPodError("a script pod needs a heartbeat spec and the approved money (CR-07)")
        body["cmd"] = script_cmd()
        body["ports"] = []  # RP: a script pod is reached by its heartbeat and the API, never by ssh or a web port (P1c)
        body["env"].update(wrapper_env(script_url, heartbeat=heartbeat, max_usd=max_usd, lifetime_s=lifetime_s or 3600,
                                       price=price if price is not None else MAX_PRICE.get(gpu, max(MAX_PRICE.values())), job=job,
                                       volume=volume, container=CONTAINER_GB, drill=drill, **(scale or {})))
    return body


# --- CLI ------------------------------------------------------------------------------------------------------------
def _opt(argv, name, default=None, cast=str):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


def parse_wait(text):
    """``15m`` / ``900s`` / ``2h`` -> seconds (0 for None)."""
    if not text:
        return 0
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smh]?)", text.strip())
    if not m:
        raise SystemExit(f"--wait-stock {text!r}: use 15m, 900s or 2h")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


def wait_for_stock(pick, wait_s, *, sleep=time.sleep, clock=time.time, poll=30):
    """``pick()`` until it returns cards or ``wait_s`` has passed (the creator, P1c: a card with no stock now often has one in
    minutes). ``pick`` may raise SystemExit when nothing matches; that is a "none yet" while waiting."""
    start = clock()
    while True:
        try:
            rows = pick()
        except SystemExit:
            if clock() - start >= wait_s:
                raise
            rows = []
        if rows or clock() - start >= wait_s:
            return rows
        sleep(poll)


def main(argv=None, api=None, live=None):
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
    elif cmd == "dryrun":  # P1b: no pod, no money; the record it writes is what `create` asks for
        from explainer_engine.cloud import dryrun
        sf = _opt(rest, "--script")
        if not sf:
            raise SystemExit("dryrun needs --script <pod.sh>")
        rec = dryrun.run(Path(sf).read_text(), offline="--offline" in rest)
        dryrun.record(rec)
        for r in rec["repos"]:
            print("repo   ", r["type"], r["id"], "ok" if r["ok"] else ("not checked" if r["ok"] is None else "MISSING"), r["note"])
        for line in rec["problems"]:
            print("PROBLEM", line)
        print(("dryrun ok " if rec["ok"] else "dryrun FAILED ") + f"sha256 {rec['sha256']}")
        if not rec["ok"]:
            raise SystemExit(1)
    elif cmd == "pins":  # P1b: what a pod's pins.txt says against config/cloud_pins.json
        from explainer_engine.cloud import pins
        if not pid:
            raise SystemExit("pins needs the pod's pins.txt")
        bad = pins.compare(Path(pid).read_text())
        for line in bad:
            print("PROBLEM", line)
        if bad:
            raise SystemExit(1)
        print("pins ok")
    elif cmd == "cards":
        refused = []
        for r in pick_gpus(api, vram_gb=_opt(rest, "--vram", 24, float), ref_hours=_opt(rest, "--ref-hours", 1.0, float),
                           max_price=spend_caps.runpod()["max_price_per_hour"], limit=20, job=_opt(rest, "--job"),
                           units=_opt(rest, "--units", None, float), setup_min=_opt(rest, "--setup-min", None, float), refused=refused):
            print(f"{r['est_usd']:7.3f} $  {r['gpu']} {r['cloud']} ${r['price']}/h x {r['hours']} h ({r['availability']}; {r['basis']})")
        for line in refused:
            print("refused", line)
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
        if not _opt(rest, "--script"):  # N-01: before any other check, so this is the refusal a scriptless create sees
            raise SystemExit(f"refused: runpod create needs --script ({OR21})")
        if "--yes" not in rest:
            raise SystemExit("refused: --yes only after the creator approved this pod's price and time cap")
        if create_flag_problems(rest):
            raise SystemExit("refused, no pod was made:\n  " + "\n  ".join(create_flag_problems(rest)))
        if _opt(rest, "--rules") and _opt(rest, "--test"):
            raise SystemExit("refused: a paid test has no episode rulebook: --rules and --test do not go together")
        max_usd, max_hours = _opt(rest, "--max-usd", None, float), _opt(rest, "--max-hours", None, float)
        if not max_usd or not max_hours:
            raise SystemExit("create needs --max-usd and --max-hours (the approved caps)")
        gpu, ledger = _opt(rest, "--gpu", "default"), _opt(rest, "--ledger")
        if not ledger:
            raise SystemExit("create needs --ledger <episode run.json>: every pod is paid for by an episode")
        if not Path(ledger).exists():  # a ledger made here would get the episode ceilings, not a paid test's line
            raise SystemExit(f"refused: no ledger at {ledger}; open it first (an episode: Run.open(path, caps=...); "
                             "a paid test: python -m explainer_engine.core.ledger open-test <path> <test>)")
        from explainer_engine.core.ledger import Run as _LedgerRun
        ledger_test, want_test = (_LedgerRun.open(ledger).data.get("meta") or {}).get("test"), _opt(rest, "--test")
        if ledger_test and not want_test:  # a paid test's ledger is bound to its test by name, before any RunPod call
            raise SystemExit(f"refused: ledger {ledger} belongs to paid test {ledger_test}: pass --test {ledger_test}")
        if want_test and ledger_test != want_test:
            raise SystemExit(f"refused: --test {want_test} does not match the ledger's test {ledger_test}" if ledger_test
                             else f"refused: --test given but {ledger} is not a paid-test ledger")
        rules_file = _opt(rest, "--rules")
        if rules_file:  # OR-12 (D-51): an episode's pod pictures pass the rulebook's paid_assets checkpoint, as production/paint.py does
            from explainer_engine.standards import rulebook as _RB
            rules_path = Path(rules_file)
            if not rules_path.exists():
                raise SystemExit(f"refused: no episode rulebook at {rules_path}")
            gate_fails = [f for f in _RB.gate(rules_path, "paid_assets", rules_path.with_name("production_script.json"))
                          if f["severity"] == "FAIL"]  # a BLOCK or an undecided REVIEW is a FAIL at paid_assets (ES-06, ES-07)
            if gate_fails:
                raise SystemExit("refused, no pod was made: the paid_assets gate (OR-12) fails:\n  " + "\n  ".join(
                    f"{f['rule']} {f['where']}: {f['detail']}" for f in gate_fails))
        script_file, script_url = _opt(rest, "--script"), _opt(rest, "--script-url")
        if script_url and not script_file:
            raise SystemExit("--script-url needs --script <the same file, local>: the pod script is linted before any money")
        script = Path(script_file).read_text() if script_file else None
        image = _opt(rest, "--image")
        if script is not None:  # CR-18: a script pod runs a pinned digest; a pin key is the short form
            from explainer_engine.cloud import pins
            try:
                image = pins.resolve_image(image, pins.load()) if image else pins.image_ref(pins.DEFAULT_IMAGE)
            except pins.PinError as e:
                raise SystemExit(f"refused, no pod was made:\n  image: {e}")
        picks = None
        job_type, units = _opt(rest, "--job-type"), _opt(rest, "--units", None, float)
        work_min, setup_min = _opt(rest, "--work-min", None, float), _opt(rest, "--setup-min", None, float)
        if "--vram" in rest:  # the cheapest job among the cards with stock now (the creator, 2026-10-24)
            refused = []

            def _pick():
                cloud = _opt(rest, "--cloud").upper()  # one cloud (create_flag_problems made it required): the cards tried and EE_PRICE then agree (G15)
                rows = pick_gpus(api, vram_gb=_opt(rest, "--vram", None, float), ref_hours=_opt(rest, "--ref-hours", max_hours, float),
                                 max_price=spend_caps.runpod()["max_price_per_hour"], job=job_type, units=units, setup_min=setup_min,
                                 refused=refused, clouds=(cloud,),
                                 limit=50 if _opt(rest, "--only") is not None else 6)  # --only names a card: it must not fall off the cheapest six
                return only_cards(rows, _opt(rest, "--only"))
            picks = wait_for_stock(_pick, parse_wait(_opt(rest, "--wait-stock")))
            for line in refused:
                print("refused", line)
            for r in picks:
                print(f"card  {r['gpu']} {r['cloud']} ${r['price']}/h x {r['hours']} h ≈ ${r['est_usd']} ({r['availability']})")
        from explainer_engine.core.ledger import Run
        base = _opt(rest, "--name", "ee-" + (gpu if not picks else "auto"))
        job_base = _opt(rest, "--job", base)
        batch_why, script_sha, weights = [], None, []
        if script is not None:  # RP-01/02/10 (P1c, docs/CLOUD_RUNBOOK.md): what the plan stated, what this ledger already holds
            from explainer_engine.cloud import batching, dryrun
            led = Run.open(ledger)
            script_sha = dryrun.sha256_of(script)
            weights = sorted(rid for rid, kind in dryrun.repo_ids(script) if kind == "model")
            earlier = [v.get("weights") or [] for v in led.data["items"].get("pod_plans", {}).values()]
            fails = led.data.get("failures", {})
            batch_why += batching.rp01(work_min, setup_min, measure="--measure" in rest, max_usd=max_usd, test=led.data.get("meta", {}).get("test"))
            batch_why += batching.rp02(weights, earlier, reason=_opt(rest, "--second-pod-reason", ""))
            batch_why += batching.rp10(len(fails.get(f"hw:{job_base}", [])), bool(fails.get(f"script:{job_base}:{script_sha[:12]}")), key=job_base,
                                      extra=int(_opt(rest, "--hw-extra-retries", "0") or 0), extra_reason=_opt(rest, "--hw-extra-reason", ""))
            if not _opt(rest, "--disk"):
                batch_why.append("--disk GB is required for a script pod: state the container disk (weights + outputs + margin); there is no default")
        drill = _opt(rest, "--drill")
        if drill:  # a fault for the P12a smoke only: never on a production pod
            if drill not in DRILLS:
                raise SystemExit(f"refused: --drill {drill!r} is not one of {DRILLS}")
            if script is None or Run.open(ledger).data.get("meta", {}).get("test") != "p12a_smoke":
                raise SystemExit("refused: --drill needs a script pod and a ledger opened with test=p12a_smoke")
        scale = {k: _opt(rest, f"--{f}", None, float) for k, f in (("pass_s", "pass-s"), ("upload_grace_s", "upload-grace-s"),
                                                                    ("cap_grace_s", "cap-grace-s"))}
        scale = {k: v for k, v in scale.items() if v is not None} or None
        heartbeat, declared = _opt(rest, "--heartbeat"), heartbeat_of_script(script) if script else None
        if heartbeat and declared and heartbeat != declared:
            raise SystemExit(f"refused: --heartbeat {heartbeat} and the script's `# heartbeat: {declared}` disagree (CR-07a)")
        heartbeat = heartbeat or declared
        from explainer_engine.cloud import hf_live
        lv, age = live, None
        if script is not None:
            try:
                lv = lv or hf_live.Live()
                age = lv.watchdog_age()
            except hf_live.LiveError:
                age = None
        # N-01: the body is built first and the preflight stamps exactly it; create() sends nothing else
        token = secrets.token_urlsafe(16)
        name = pod_name(base, max_hours)
        first = picks[0] if picks else None
        body, body_why = None, []
        try:
            body = create_body(name, first["gpu"] if first else gpu, volume=_opt(rest, "--volume", 0 if script is not None else VOLUME_GB, int),
                               min_ram=_opt(rest, "--min-ram"), boot=_opt(rest, "--boot"), status_token=token,
                               image=image, script_url=script_url, lifetime_s=int(max_hours * 3600),
                               cloud=first["cloud"] if first else "SECURE", heartbeat=heartbeat, max_usd=max_usd,
                               job=job_base, price=max(r["price"] for r in picks) if picks else None, scale=scale, drill=drill)  # the ceiling, not the list price
        except RunPodError as e:  # e.g. no heartbeat: the preflight below says it in its own words
            body_why.append(str(e))
        if body is not None:
            if _opt(rest, "--disk"):  # container disk (GB): a model download larger than the default CONTAINER_GB
                body["disk"] = _opt(rest, "--disk", None, int)
            if script is not None:
                from explainer_engine.cloud import batching
                if batching.rp03(body):  # RP-03: never a network volume
                    raise SystemExit("refused, no pod was made:\n  " + "\n  ".join(batching.rp03(body)))
        adopted = (None, None)
        if script is not None and lv is not None:  # CR-12 / T22 / T24: an earlier create of this job whose answer was lost: its pod is adopted, never POSTed twice
            adopted = adopt_pending(api, lv, job=job_base, heartbeat=heartbeat)
        why = preflight_create(api, max_usd=max_usd, max_hours=max_hours, gpu=gpu, script=script, picks=picks, heartbeat=heartbeat,
                               pod_key=bool(secret("pod_api_key.txt", "RUNPOD_POD_API_KEY")), watchdog_age=age, image=image,
                               boot_minutes=_opt(rest, "--boot-minutes", BOOT_MINUTES, float), body=body,
                               ignore=adopted[0]["id"] if adopted[0] is not None else None)
        why += batch_why + (body_why if not any("heartbeat" in w for w in why) else [])
        if script is not None and lv is None:
            why.append("the live-pod registry on HF cannot be written (no HF_TOKEN): the watchdog could not see this pod (CR-07c)")
        if why:
            raise SystemExit("refused, no pod was made:\n  " + "\n  ".join(why))
        from explainer_engine.cloud.jobs import Job
        from explainer_engine.core.ledger import Run
        spec = None
        if adopted[0] is not None:
            print("adopted", adopted[0]["id"], adopted[1]["name"], "(an earlier create timed out; no second POST)")
            spec, name = adopted[1], adopted[1]["name"]
        if script is not None and spec is None:  # CR-12: the watchdog judges this pod from the registry, with no session file
            env = body["env"]
            spec = {"name": name, "pod": None, "job": env.get("EE_JOB"), "heartbeat": heartbeat, "created": float(env["EE_CREATED"]),
                    "price": float(env["EE_PRICE"]), "disk_per_h": float(env["EE_DISK_H"]), "max_usd": max_usd, "max_hours": max_hours,
                    "until": until_of(name)}
            try:
                lv.write_spec(spec)
            except hf_live.LiveError as e:
                raise SystemExit(f"refused, no pod was made: the live-pod registry could not be written ({e}) (CR-07c)")
        if adopted[0] is None or "pod:pending" not in Run.open(ledger).data["reserved"]:  # an adopted pod keeps its first reservation
            Run.open(ledger).reserve("runpod_usd", max_usd, item="pod:pending")  # refuses past 80 % of the episode's cap
        job = Job.create(ROOT / "jobs" / "cloud", _opt(rest, "--job", base), kind="pod", provider="runpod", ledger=ledger,
                         caps={"max_usd": max_usd, "max_hours": max_hours}, reuse_finished=False,
                         inputs={"gpu": first["gpu"] if first else gpu, "boot": _opt(rest, "--boot"), "script": script_url,
                                 "volume": (body["mounts"].get("persistent") or {}).get("size", 0)})
        job.move("PROVISIONING", "POST /pods")
        card_max = max(r["price"] for r in picks) if picks else MAX_PRICE[gpu]
        try:
            pod = adopted[0] or create(api, body, max_price=card_max,
                                       gpus=[(r["gpu"], r["cloud"], card_max) for r in picks if r["est_usd"] <= max_usd] if picks
                                       else [(g, "SECURE", MAX_PRICE[gpu]) for g in GPUS[gpu]])
        except RunPodError as e:
            if spec is not None:
                lv.drop_spec(name)
            Run.open(ledger).settle("runpod_usd", "pod:pending", 0.0)
            Run.open(ledger).fail(f"hw:{job_base}", f"create: {str(e)[:200]}")  # RP-10: no capacity / an API refusal is the hardware try
            job.move("FAILED", f"create: {str(e)[:200]}")
            from explainer_engine.cloud import incidents
            incidents.record(incidents.fingerprint("runpod", "pod", "create", text=str(e)), f"create failed: {str(e)[:200]}",
                             cause=str(e)[:200], fix="", source="create", job=job.state["id"])
            raise
        Run.open(ledger).rename_reservation("pod:pending", f"pod:{pod['id']}")
        if script is not None:
            Run.open(ledger).done("pod_plans", name, weights=weights, job=job_base, script_sha=script_sha, pod=pod["id"],
                                  second_pod_reason=_opt(rest, "--second-pod-reason", ""))
        job.attach(pod["id"], gpu=pod.get("gpu"), price=pod.get("costPerHr"), name=name)
        if spec is not None:
            try:
                lv.write_spec({**spec, "pod": pod["id"]})
            except hf_live.LiveError as e:  # the guard still runs; say it loudly
                notify("Live spec not updated", f"{pod['id']}: {str(e)[:150]}; the watchdog sees the name only", "high")
        new_session(pod, max_usd=max_usd, max_hours=max_hours, on_cap=_opt(rest, "--on-cap", "stop"), ledger=ledger,
                    status_token=token if _opt(rest, "--boot") else "", price_ceiling=card_max, job=job.dir,
                    heartbeat=heartbeat, boot_minutes=_opt(rest, "--boot-minutes", BOOT_MINUTES, float),
                    stall_s=(stall_minutes_of_script(script) or 0) * 60 or None,
                    extra={"gpu": first["gpu"] if first else pod.get("gpu") or gpu, "cloud": first["cloud"] if first else "SECURE",
                           "job_base": job_base, "job_type": job_type, "units": units, "script_sha": script_sha})
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
        if "--allow-zero-gpu-risk" not in rest:  # RP (L7): a stopped pod can come back with zero GPUs and a wiped container disk
            raise SystemExit("refused: a stopped pod may restart with zero GPUs and a wiped container disk, and still bills. Resume as a NEW "
                             "pod that reads its checkpoint from HF; if the creator wants this start anyway, add --allow-zero-gpu-risk")
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
        print(pid, api.delete_global_volume(pid) if "--global" in rest else api.delete_network_volume(pid))
    elif cmd == "cost":
        res = cost_report(api, pid, _opt(rest, "--ledger"))
        print(f"{pid}: billed ${res['usd']} over {res['buckets']} hour bucket(s) (RunPod billing; the newest hour may still grow)")
        print("PROGRESS line:", res["line"])
        if res["speed"]:
            print(res["speed"])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
