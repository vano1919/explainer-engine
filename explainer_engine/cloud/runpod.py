# from vano1919/tmr-video-script-engine@f0abe62:cloud/rp.py
"""RunPod pod manager: create, wait, guard, stop, sweep and settle the cost. stdlib only.

    python -m explainer_engine.cloud.runpod check (alias: doctor) | balance | list | sweep [--dry-run] [--delete --yes]
    python -m explainer_engine.cloud.runpod delete-volume <volume id> --yes
    python -m explainer_engine.cloud.runpod create --yes --max-usd X --max-hours H [--gpu default|cheap|big] [--boot <manifest>]
           --ledger <episode run.json> [--volume GB] [--min-ram GB] [--name base] [--on-cap stop|delete] [--no-guard]
    python -m explainer_engine.cloud.runpod status|wait-ready|guard|stop|cost <pod> ;  delete <pod> --yes ;  start <pod> --yes ...

What TMR's rp.py did and what changed here (docs/TOOL_STRATEGY.md "Money control for RunPod" has the facts from RunPod's API reference, checked 2026-10-19):
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
* ``check`` covers every billing category, not only pods (added 2026-10-22, after the balance questions of 10-19/10-22):
  network volumes ($0.07/GB/month even when nothing uses them) and serverless endpoints with always-on workers are
  PROBLEM lines too, so no category can bill invisibly; ``delete-volume`` removes a volume on the creator's word.
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
BASE = "https://rest.runpod.io/v1"
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
# disk prices, docs.runpod.io/pods/pricing (2026-10-19): running $0.10/GB/month (container + volume), stopped volume $0.20
GB_MONTH_RUNNING, GB_MONTH_STOPPED, HOURS_PER_MONTH = 0.10, 0.20, 730.0
GB_MONTH_NETWORK = 0.07  # network volume, docs.runpod.io/storage/network-volumes (2026-10-22): $0.07/GB/month under 1 TB
BOOT_MINUTES = 10  # the pod must answer (status page or ssh port) within this long, else it never booted
GONE = ("TERMINATED",)


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
    req = urllib.request.Request(url, body, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


class Api:
    """RunPod REST + GraphQL. ``transport(method, url, body, headers, timeout) -> (status, text)``; it raises OSError (incl.
    timeouts) when no answer came. Reads, stop and delete are retried with backoff; create is not."""

    def __init__(self, key=None, *, base=BASE, gql=GQL, transport=_urllib, sleep=time.sleep, retries=4, timeout=60):
        self.key, self.base, self.gql, self.transport, self.sleep = key, base, gql, transport, sleep
        self.retries, self.timeout = retries, timeout

    def _headers(self):
        return {"Authorization": "Bearer " + (self.key or api_key()), "Content-Type": "application/json", "User-Agent": UA}

    def request(self, method, path, body=None, *, retry=True, url=None):
        data = json.dumps(body).encode() if body is not None else (b"{}" if method == "POST" else None)
        last = None
        for attempt in range(self.retries + 1 if retry else 1):
            if attempt:
                self.sleep(min(60, 2 ** attempt))
            try:
                status, text = self.transport(method, url or self.base + path, data, self._headers(), self.timeout)
            except OSError as e:
                last = Unclear(f"{method} {path}: no answer ({e})")
                continue
            if status == 404:
                raise NotFound(f"{method} {path}: 404", 404)
            if status == 429 or status >= 500:
                last = Unclear(f"{method} {path}: HTTP {status} {text[:200]}", status)
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
        """The pod record, or None when RunPod no longer knows it."""
        try:
            p = self.request("GET", f"/pods/{pid}")
        except NotFound:
            return None
        return None if not p or p.get("desiredStatus") in GONE else p

    def pods(self, **filters):
        q = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in filters.items())
        return self.request("GET", "/pods" + ("?" + q if q else "")) or []

    def balance(self):
        return self.graphql("query { myself { clientBalance currentSpendPerHr spendLimit } }")["myself"]

    def network_volumes(self):
        return self.request("GET", "/networkvolumes") or []

    def serverless_endpoints(self):
        return self.request("GET", "/endpoints") or []

    def delete_network_volume(self, vid):
        """Verified delete: done when the volume no longer appears in the list."""
        try:
            self.request("DELETE", f"/networkvolumes/{vid}")
        except (NotFound, Unclear):
            pass
        if any(v.get("id") == vid for v in self.network_volumes()):
            raise RunPodError(f"{vid}: still listed after DELETE; it may still bill")
        return "DELETED"

    def billing(self, pid, start, end=None):
        """RunPod's billed amount (compute and disks, stopped pods included) for one pod, or the whole account when ``pid``
        is None, since ``start`` (epoch s): (usd, billed seconds). Hour buckets; the newest hour can lag."""
        iso = lambda t: time.strftime("%Y-%m-%dT%H:00:00Z", time.gmtime(t))  # noqa: E731
        q = f"/billing/pods?bucketSize=hour&grouping=podId&startTime={iso(start)}" + (f"&podId={pid}" if pid else "")
        q += f"&endTime={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(end or time.time() + 3600))}"
        rows = [r for r in self.request("GET", q) or [] if pid is None or r.get("podId") in (None, pid)]
        return round(sum(float(r.get("amount") or 0) for r in rows), 4), round(sum(int(r.get("timeBilledMs") or 0) for r in rows) / 1000)


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


def new_session(pod, *, max_usd, max_hours, on_cap="stop", ledger=None, now=None, status_token="", boot_minutes=BOOT_MINUTES):
    now = time.time() if now is None else now
    return sess_write({"pod": pod["id"], "name": pod.get("name", ""), "started": now, "price": pod.get("costPerHr"),
                       "pod_shape": {"volumeInGb": pod.get("volumeInGb"), "containerDiskInGb": pod.get("containerDiskInGb")},
                       "max_usd": max_usd, "max_hours": max_hours, "until": until_of(pod.get("name")) or now + max_hours * 3600,
                       "boot_deadline": now + boot_minutes * 60, "on_cap": on_cap, "ledger": ledger, "status_token": status_token,
                       "answered": False, "ended": None})


# --- verified lifecycle ---------------------------------------------------------------------------------------------
def wait_status(api, pid, want, *, timeout=180, poll=5, clock=time.time, sleep=time.sleep):
    """Poll until desiredStatus is in ``want`` ("GONE" = deleted). Returns the status seen; raises TimeoutError."""
    end = clock() + timeout
    while True:
        try:
            p = api.pod(pid)
            st = "GONE" if p is None else p.get("desiredStatus")
            if st in want:
                return st
        except Unclear:
            pass
        if clock() >= end:
            raise TimeoutError(f"pod {pid} did not reach {'/'.join(want)} in {timeout} s")
        sleep(poll)


def stop(api, pid, *, timeout=180, **kw):
    """Idempotent, verified stop: done when GET shows EXITED or the pod is gone. REST first, GraphQL podStop second."""
    p = api.pod(pid)
    if p is None or p.get("desiredStatus") == "EXITED":
        return "GONE" if p is None else "EXITED"
    errors = []
    for how in ("rest", "graphql"):
        try:
            if how == "rest":
                api.request("POST", f"/pods/{pid}/stop")
            else:
                api.graphql('mutation { podStop(input: {podId: "%s"}) { id desiredStatus } }' % pid)
        except NotFound:
            return "GONE"
        except RunPodError as e:
            errors.append(str(e))
            continue  # this way was refused: try the next one at once
        try:
            return wait_status(api, pid, ("EXITED", "GONE"), timeout=timeout, **kw)
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
    return [p for p in api.pods(name=name) if p.get("name") == name and p.get("desiredStatus") not in GONE]


def create(api, body, *, max_price, sleep=time.sleep, lookups=6):
    """POST /pods once. After an unclear answer (timeout, 5xx) the pod is looked up by its unique name instead of POSTing
    again: a second POST could rent a second pod. A card dearer than ``max_price`` is deleted at once (nothing is on it)."""
    pod, err = None, None
    for wait in (10, 30, 60, None):
        try:
            pod = api.request("POST", "/pods", body, retry=False)
            break
        except Unclear as e:
            err = e
            if e.status != 429 or wait is None:  # 429 = refused before anything happened: the only safe re-POST
                break
            sleep(wait)
    if pod is None:
        for _ in range(lookups):
            sleep(10)
            try:
                found = find_by_name(api, body["name"])
            except Unclear:
                continue
            if len(found) > 1:
                raise RunPodError(f"{len(found)} pods named {body['name']}: check and stop them by hand") from err
            if found:
                pod = found[0]
                break
        if pod is None:
            raise RunPodError(f"create: no clear answer and no pod named {body['name']} appeared; nothing is billing "
                              f"(run sweep to be sure): {err}") from err
    price = float(pod.get("costPerHr") or 0)
    if price > max_price:
        delete(api, pod["id"])
        raise RunPodError(f"pod {pod['id']} costs ${price}/h, over the ${max_price}/h ceiling: deleted")
    return pod


def ready(pod):
    """Ports are mapped and the pod has a public address: the container is up (empty while initialising)."""
    return bool(pod and pod.get("desiredStatus") == "RUNNING" and pod.get("publicIp") and pod.get("portMappings"))


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
            raise TimeoutError(f"pod {pid} not ready after {timeout} s (status {p.get('desiredStatus')}, ip {p.get('publicIp')})")
        sleep(poll)


# --- guard ----------------------------------------------------------------------------------------------------------
def guard_check(sess, pod, now, conductor=None):
    """One look: (action, why). action is "ok", "end" (nothing left to guard) or "stop" (a cap or the boot deadline).
    ``conductor`` is the first line of the pod's status page ("STATUS DONE ...") or None when it did not answer."""
    if pod is None:
        return "end", "pod is gone"
    if pod.get("desiredStatus") != "RUNNING":
        return "end", f"pod is {pod.get('desiredStatus')}"
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


def end_pod(api, sess, why, *, push=notify, sleep=time.sleep):
    """Stop (or with the creator's ``on_cap: delete``, delete) and never give up: a failed attempt is pushed and retried."""
    for attempt in range(1, 1000):
        try:
            st = delete(api, sess["pod"]) if sess.get("on_cap") == "delete" else stop(api, sess["pod"])
            break
        except (RunPodError, TimeoutError) as e:
            if attempt in (1, 3, 10) or attempt % 30 == 0:
                push("GUARD CANNOT STOP THE POD", f"{sess['pod']}: {why}; attempt {attempt}: {str(e)[:120]}")
            sleep(30)
    sess.update(closed=time.time(), close_why=why, close_status=st)
    sess_write(sess)
    disk = disk_per_hour(sess.get("pod_shape") or {}, running=False) * 24
    tail = f"; its disk bills ${disk:.2f}/day until deleted" if st == "EXITED" else ""
    push("Guard ended the pod", f"{sess['pod']} {st}: {why}; estimate ${spent_estimate(sess, time.time())}{tail}", "high")
    return st


def guard(api, pid, *, clock=time.time, sleep=time.sleep, push=notify, page=status_page, poll=30, report_min=10, log=print):
    """Watch one pod until it is gone or stopped; stop it at a cap, at the end of its approved lifetime, when it never booted,
    or when its conductor ended. A blind API is never a reason to stop guarding; the local money clock keeps running and a
    cap reached while blind still triggers the stop attempts."""
    sess = sess_read(pid)
    if not sess:
        raise SystemExit(f"no session for {pid}: create it with this tool, or `adopt` it with its caps")
    blind, last_report, last_line = 0, 0.0, None
    while True:
        now = clock()
        try:
            pod = api.pod(pid)
            blind = 0
        except (Unclear, RunPodError):
            blind += 1
            if blind in (4, 20):
                push("Guard is blind", f"cannot reach RunPod for {blind * poll} s; {pid} may still be billing")
            pod = {"id": pid, "desiredStatus": "RUNNING", "costPerHr": sess.get("price")}  # assume the worst
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
        st, pid = p.get("desiredStatus"), p["id"]
        label = f"{pid} {p.get('name')} ${p.get('costPerHr')}/h"
        try:
            if st == "RUNNING" and expired(p.get("name"), now):
                if not dry:
                    stop(api, pid)
                rows["stopped"].append(label)
            elif st == "RUNNING":
                rows["running_ok"].append(label)
            elif st == "EXITED":
                day = disk_per_hour(p, running=False) * 24
                if delete_exited and not dry:
                    delete(api, pid)
                    rows["deleted"].append(f"{label} (disk ${day:.2f}/day)")
                else:
                    rows["exited"].append(f"{pid} {p.get('name')}: disk {p.get('volumeInGb')} GB = ${day:.2f}/day")
        except (RunPodError, TimeoutError) as e:
            rows["failed"].append(f"{label}: {str(e)[:120]}")
    return rows


def settle(api, pid, ledger_path=None):
    """RunPod's billed amount for the pod's session, written over the reservation in the run ledger (``runpod_usd``)."""
    sess = sess_read(pid) or {}
    usd, secs = api.billing(pid, sess.get("started") or time.time() - 86400)
    ledger_path = ledger_path or sess.get("ledger")
    if ledger_path:
        from explainer_engine.core.ledger import Run
        run = Run.open(ledger_path)
        run.settle("runpod_usd", f"pod:{pid}", usd)
        run.done("pods", pid, cost={"runpod_usd": usd}, billed_s=secs, source="runpod billing", name=sess.get("name"))
    if sess:
        sess.update(billed_usd=usd, billed_s=secs, settled=time.time())
        sess_write(sess)
    return usd, secs


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


def check(api, now=None):
    """The account as it bills now: problems (anything spending money that nobody approved or guards) and info lines.
    Run at the start and end of every session and after every pod job; the session hooks run it (cloud/hooks.py)."""
    now = time.time() if now is None else now
    keep = set(spend_caps.runpod().get("keep_stopped_pods", []))
    problems, info = [], []
    for p in api.pods():
        st, pid, name = p.get("desiredStatus"), p["id"], p.get("name")
        if st == "RUNNING":
            sess = sess_read(pid)
            line = f"{pid} {name} RUNNING ${p.get('costPerHr')}/h"
            if expired(name, now):
                problems.append(f"{line}: no approved lifetime left; stop it (`runpod sweep`)")
            elif sess and not sess.get("closed") and not live_guard(pid):
                problems.append(f"{line}: its guard is not running here; `runpod guard {pid}` or stop it")
            else:
                info.append(f"{line}, approved until {time.strftime('%H:%M UTC', time.gmtime(until_of(name)))}")
        elif st == "EXITED":
            day = disk_per_hour(p, running=False) * 24
            line = f"{pid} {name} STOPPED, disk {p.get('volumeInGb')} GB bills ${day:.2f}/day"
            (info if pid in keep else problems).append(line + ("" if pid in keep else
                                                               "; delete it with the creator's word (`runpod delete <pod> --yes`) or list it in keep_stopped_pods"))
    keep_nv = set(spend_caps.runpod().get("keep_network_volumes", []))
    try:
        for v in api.network_volumes():
            vid, gb = v.get("id"), float(v.get("size") or 0)
            line = f"{vid} {v.get('name')} NETWORK VOLUME {gb:g} GB bills ${gb * GB_MONTH_NETWORK * 24 / HOURS_PER_MONTH:.2f}/day"
            (info if vid in keep_nv else problems).append(line + ("" if vid in keep_nv else
                                                                  "; delete it with the creator's word (`runpod delete-volume <id> --yes`) or list it in keep_network_volumes"))
        for ep in api.serverless_endpoints():
            line = f"{ep.get('id')} {ep.get('name')} SERVERLESS ENDPOINT workersMin={ep.get('workersMin')}"
            if int(ep.get("workersMin") or 0) > 0:
                problems.append(line + ": always-on workers bill constantly; set workersMin 0 or remove it in the console")
            else:
                info.append(line + " (bills only while a job runs)")
    except RunPodError as e:  # unreadable = possibly billing invisibly, so a PROBLEM, not an info line
        problems.append(f"network volumes/endpoints not read ({str(e)[:80]}); the account may bill invisibly, check again")
    try:
        usd, _ = api.billing(None, now - 86400)
        bal = api.balance()
        info.append(f"billed in the last 24 h ${usd:.2f} of ${spend_caps.runpod()['per_24h_usd']}; balance ${float(bal['clientBalance']):.2f}, "
                    f"spending ${float(bal.get('currentSpendPerHr') or 0):.3f}/h now")
    except RunPodError as e:
        info.append(f"billing not read: {str(e)[:80]}")
    return {"problems": problems, "info": info}


def preflight_create(api, *, max_usd, max_hours, gpu, now=None, ignore=None):
    """Every reason to refuse a new pod (empty = allowed): the creator's ceilings, the last 24 h of billing, the balance and
    a clean account first (no stray pod, no unkept stopped disk)."""
    now = time.time() if now is None else now
    c = spend_caps.runpod()
    why = []
    if max_usd > c["per_pod_usd"]:
        why.append(f"--max-usd {max_usd} is above per_pod_usd {c['per_pod_usd']}")
    if max_hours > c["max_hours_per_pod"]:
        why.append(f"--max-hours {max_hours} is above max_hours_per_pod {c['max_hours_per_pod']}")
    if MAX_PRICE[gpu] > c["max_price_per_hour"] + 1e-9:
        why.append(f"the {gpu} card ceiling ${MAX_PRICE[gpu]}/h is above max_price_per_hour {c['max_price_per_hour']}")
    usd, _ = api.billing(None, now - 86400)
    if usd + max_usd > c["per_24h_usd"] + 1e-9:
        why.append(f"billed ${usd:.2f} in the last 24 h + this pod's ${max_usd} passes per_24h_usd {c['per_24h_usd']}")
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
    env = {"STATUS_TOKEN": status_token, "NTFY_TOPIC": secret("ntfy_topic.txt", "NTFY_TOPIC"),
           "HEARTBEAT_URL": secret("heartbeat_url.txt", "HEARTBEAT_URL"), "HF_TOKEN": secret("hf_token.txt", "HF_TOKEN"),
           "GITHUB_TOKEN": secret("github_token.txt", "GITHUB_TOKEN_RO") or secret("github_token.txt", "GITHUB_TOKEN"),
           "PUBLIC_KEY": secret("id_ed25519.pub", "RUNPOD_PUBLIC_KEY"), "TMR_BRANCH": os.environ.get("TMR_BRANCH", "")}
    return {k: v for k, v in env.items() if v}


def boot_cmd(manifest, branch):
    """The pod fetches TMR's bootstrap.sh and runs the manifest itself; PID 1 then stays alive (a returning start command
    restarts the container in a loop, TMR 2026-10-11). A failed boot stops the pod (stop, not delete: the creator's rule)."""
    url = f"https://raw.githubusercontent.com/{BOOT_REPO}/{branch}/cloud/bootstrap.sh"
    stop_self = ('curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" '
                 '"https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID/stop" >/dev/null 2>&1')
    return ["bash", "-lc", 'set -o pipefail; curl -fsSL -H "Authorization: token $GITHUB_TOKEN" '
            f'{url} | bash -s -- {manifest} || {{ {stop_self}; }}; tail -f /dev/null']


def create_body(name, gpu="default", *, volume=VOLUME_GB, min_ram=None, boot=None, status_token=""):
    body = {"name": name, "imageName": IMAGE, "gpuTypeIds": GPUS[gpu], "cloudType": "SECURE", "gpuCount": 1,
            "interruptible": False, "containerDiskInGb": CONTAINER_GB, "volumeInGb": volume, "volumeMountPath": "/workspace",
            "ports": ["22/tcp", "8888/http"], "env": pod_env(status_token), "allowedCudaVersions": CUDA_VERSIONS}
    if gpu != "default":
        body["gpuTypePriority"] = "custom"
    if min_ram:
        body["minRAMPerGPU"] = int(min_ram)
    if boot:
        body["dockerStartCmd"] = boot_cmd(boot, os.environ.get("TMR_BRANCH") or "main")
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
    elif cmd in ("check", "doctor"):  # start and end of every session, after every pod job (D-56)
        res = check(api)
        for line in res["problems"]:
            print("PROBLEM", line)
        for line in res["info"]:
            print("ok     ", line)
        if res["problems"]:
            raise SystemExit(1)
    elif cmd == "list":
        for p in api.pods():
            print(p["id"], p.get("name"), p.get("desiredStatus"), f"${p.get('costPerHr')}/h", f"{p.get('volumeInGb')} GB")
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
        why = preflight_create(api, max_usd=max_usd, max_hours=max_hours, gpu=gpu)
        if why:
            raise SystemExit("refused, no pod was made:\n  " + "\n  ".join(why))
        from explainer_engine.core.ledger import Run
        Run.open(ledger).reserve("runpod_usd", max_usd, item="pod:pending")  # refuses past 80 % of the episode's cap
        token = secrets.token_urlsafe(16)
        name = pod_name(_opt(rest, "--name", "ee-" + gpu), max_hours)
        body = create_body(name, gpu, volume=_opt(rest, "--volume", VOLUME_GB, int), min_ram=_opt(rest, "--min-ram"),
                           boot=_opt(rest, "--boot"), status_token=token)
        try:
            pod = create(api, body, max_price=MAX_PRICE[gpu])
        except RunPodError:
            Run.open(ledger).settle("runpod_usd", "pod:pending", 0.0)
            raise
        Run.open(ledger).rename_reservation("pod:pending", f"pod:{pod['id']}")
        new_session(pod, max_usd=max_usd, max_hours=max_hours, on_cap=_opt(rest, "--on-cap", "stop"), ledger=ledger,
                    status_token=token if body.get("dockerStartCmd") else "")
        print("pod", pod["id"], name, f"${pod.get('costPerHr')}/h")
        if "--no-guard" not in rest:
            print("guard pid", guard_detached(pod["id"]), f"log tools/runpod/sessions/{pod['id']}.guard.log")
    elif cmd in ("adopt", "start") and not (_opt(rest, "--max-usd") and _opt(rest, "--max-hours")):
        raise SystemExit(f"{cmd} needs --max-usd and --max-hours (the approved caps)")
    elif cmd == "adopt":  # a pod made elsewhere (TMR rp.py, the console): give it caps and a guard
        p = api.pod(pid)
        if p is None:
            raise SystemExit(f"{pid}: no such pod")
        new_session(p, max_usd=_opt(rest, "--max-usd", None, float), max_hours=_opt(rest, "--max-hours", None, float),
                    on_cap=_opt(rest, "--on-cap", "stop"), status_token=_opt(rest, "--status-token", ""))
        print("guard pid", guard_detached(pid))
    elif cmd == "status":
        p = api.pod(pid)
        sess = sess_read(pid)
        print("GONE" if p is None else f"{p.get('desiredStatus')} ${p.get('costPerHr')}/h ip {p.get('publicIp')} "
              f"ports {p.get('portMappings')} started {p.get('lastStartedAt')}")
        if sess and p:
            print(f"estimate ${spent_estimate(sess, time.time(), p)} of ${sess['max_usd']}")
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
        api.request("POST", f"/pods/{pid}/start")
        p = wait_ready(api, pid)
        new_session(p, max_usd=_opt(rest, "--max-usd", None, float), max_hours=_opt(rest, "--max-hours", None, float),
                    on_cap=_opt(rest, "--on-cap", "stop"))
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
        usd, secs = settle(api, pid, _opt(rest, "--ledger"))
        print(f"{pid}: billed ${usd} for {secs} s (RunPod billing; the newest hour may still grow)")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
