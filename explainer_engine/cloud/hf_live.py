"""The live-pod registry on Hugging Face (docs/CLOUD_RUNBOOK.md CR-07, CR-12): ``create`` writes what a watchdog needs to judge
a pod without any local session file, and the watchdog (GitHub Actions, any machine with the tokens) reads it.

    runpod/live/<pod name>.json      {name, pod, job, heartbeat, created, price, disk_per_h, max_usd, max_hours, until}
    runpod/closed/<pod name>.json    the same record after the pod is no longer live (P1c settles the bill from it)
    runpod/watchdog.json             {last_run}: the proof that a session-independent stop path ran lately (CR-07b)

stdlib only (HF commit API with an NDJSON body); ``transport(method, url, data, headers) -> (status, text)`` is injectable. The
repo is the private vault dataset (D-73); ``HF_TOKEN`` needs write access to it.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ.get("EE_LIVE_REPO", "datasets/vano1919/tmr-artifacts")
LIVE, CLOSED, WATCHDOG = "runpod/live", "runpod/closed", "runpod/watchdog.json"
UA = "explainer-engine"


class LiveError(RuntimeError):
    pass


def _urllib(method, url, data, headers):
    req = urllib.request.Request(url, data, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except OSError as e:
        raise LiveError(f"{method} {url}: no answer ({e})") from e


class Live:
    def __init__(self, token=None, *, repo=REPO, transport=_urllib):
        self.token, self.repo, self.transport = token or os.environ.get("HF_TOKEN", ""), repo, transport
        if not self.token:
            raise LiveError("no HF_TOKEN: the live-pod registry cannot be read or written")

    def _call(self, method, url, data=None, ctype="application/json"):
        headers = {"Authorization": "Bearer " + self.token, "User-Agent": UA, "Content-Type": ctype}
        return self.transport(method, url, data, headers)

    def _commit(self, ops, summary):
        lines = [{"key": "header", "value": {"summary": summary}}] + ops
        status, text = self._call("POST", f"https://huggingface.co/api/{self.repo}/commit/main",
                                  "\n".join(json.dumps(x) for x in lines).encode(), "application/x-ndjson")
        if status >= 300:
            raise LiveError(f"HF commit {summary!r}: HTTP {status} {text[:200]}")

    def put(self, path, obj):
        body = base64.b64encode(json.dumps(obj, indent=1, sort_keys=True).encode()).decode()
        self._commit([{"key": "file", "value": {"path": path, "content": body, "encoding": "base64"}}], f"runpod: {path}")

    def get(self, path):
        status, text = self._call("GET", f"https://huggingface.co/{self.repo}/resolve/main/{urllib.parse.quote(path)}")
        if status == 404:
            return None
        if status >= 300:
            raise LiveError(f"HF read {path}: HTTP {status}")
        return json.loads(text)

    def ls(self, folder):
        status, text = self._call("GET", f"https://huggingface.co/api/{self.repo}/tree/main/{urllib.parse.quote(folder)}")
        if status == 404:
            return []
        if status >= 300:
            raise LiveError(f"HF list {folder}: HTTP {status}")
        return [r["path"] for r in json.loads(text) if r.get("type") == "file"]

    def delete(self, path):
        self._commit([{"key": "deletedFile", "value": {"path": path}}], f"runpod: remove {path}")

    # --- the registry ---------------------------------------------------------------------------------------------------
    def write_spec(self, spec):
        self.put(f"{LIVE}/{spec['name']}.json", spec)

    def specs(self):
        """{pod name: spec} of every live record."""
        out = {}
        for path in self.ls(LIVE):
            if path.endswith(".json"):
                spec = self.get(path)
                if spec:
                    out[spec.get("name") or path.rsplit("/", 1)[-1][:-5]] = spec
        return out

    def close_spec(self, name):
        spec = self.get(f"{LIVE}/{name}.json")
        if spec:
            self.put(f"{CLOSED}/{name}.json", {**spec, "closed": time.time()})
            self.delete(f"{LIVE}/{name}.json")

    def drop_spec(self, name):
        """A create that never made a pod: the record goes."""
        try:
            self.delete(f"{LIVE}/{name}.json")
        except LiveError:
            pass

    def mark_run(self, now=None):
        self.put(WATCHDOG, {"last_run": time.time() if now is None else now})

    def watchdog_age(self, now=None):
        """Seconds since the watchdog last ran, or None when it never wrote its record."""
        rec = self.get(WATCHDOG)
        return None if not rec else (time.time() if now is None else now) - float(rec["last_run"])
