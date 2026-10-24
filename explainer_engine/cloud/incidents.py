"""The incident log of the Guardian (master brief 2026-10-22, stage B): every cloud failure has a fingerprint (provider,
resource type, stage, error class), a cause, the fix that lives in code and what it cost. ``doctor`` searches it before any
diagnosis, so the same failure is recognised the second time and its known fix is named instead of guessed.

Two files: ``incidents.json`` next to this module (the committed knowledge, seeded from TMR's prose log) and
``tools/runpod/incidents.jsonl`` (what this machine saw, appended by the guard, the watchdog and ``incidents add``).
``classify(text)`` turns an error text into an error class; ``match()`` ranks known incidents by fingerprint overlap.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KNOWN = HERE / "incidents.json"
LOCAL = HERE.parents[1] / "tools" / "runpod" / "incidents.jsonl"

# error classes, in the order they are tried: the first regex that matches wins
CLASSES = [
    ("no_capacity", r"no capacity|not enough free gpu|no (?:longer )?available|out of stock|capacity"),
    ("rate_limited", r"\b429\b|rate.?limit|too many requests"),
    ("http_403", r"\b403\b|user-agent"),
    ("auth", r"\b401\b|unauthori[sz]ed|forbidden|invalid api key|bad credentials"),
    ("not_found", r"\b404\b|not found|no such pod|does not exist"),
    ("boot_timeout", r"never (?:answered|became ready|reached)|not ready after|boot deadline"),
    ("timeout", r"timed? ?out|no answer|deadline|unreachable|connection (?:reset|refused)|name resolution"),
    ("stage_limit", r"stage limit|command timed out|killed after|time cap|exceeded .*limit"),
    ("money_cap", r"money cap|budget|cap reached|passes? \d+ ?%|over the \$"),
    ("oom", r"out of memory|cuda out of memory|oom|killed process|exit code 137"),
    ("disk_full", r"no space left|disk full|enospc"),
    ("missing_dependency", r"no module named|not found: |command not found|exit 127|cannot import|notfound\b|has no attribute"),
    ("damaged_file", r"damaged|truncated|cut off|unreadable|empty file|no moov"),
    ("sole_copy_lost", r"lost|sole copy|only copy"),
    ("stopped_disk_billing", r"stopped .*disk|disk .*bills|/day"),
    ("left_running", r"still running|stayed on|never stopped|cannot stop|unstopped"),
    ("service_not_ready", r"never became ready|not ready|connection refused"),
    ("script_error", r"syntax error|invalid option|bad interpreter|\\r|crlf"),
    ("config", r"is not set|missing (?:env|variable|token)|no runpod key|config"),
    ("disk_wiped", r"virtual environment already exists|wiped on stop|unable to locate package"),
    ("idle_timeout", r"idle|without a decision|no decision"),
    ("self_match", r"pkill|pgrep|matched its own"),
    ("hidden_exit_code", r"hid the exit code|exit code hidden|passed although"),
    ("stage_order", r"before the stage|ran before|stage order"),
    ("wrong_price", r"price|overstat"),
    ("pod_error", r"\berror\b state|in error|status error"),
    ("pod_gone", r"pod is gone|terminated|gone"),
    ("stalled", r"stall|quiet for|no progress|no heartbeat"),
]


def classify(text):
    low = (text or "").lower()
    for name, pattern in CLASSES:
        if re.search(pattern, low):
            return name
    return "unknown"


def fingerprint(provider="runpod", resource="pod", stage="any", error_class="unknown", text=None):
    """The four fields that make incidents comparable. ``text`` fills in ``error_class`` when given."""
    return {"provider": provider, "resource": resource, "stage": stage or "any",
            "error_class": classify(text) if text and error_class == "unknown" else error_class}


def load_known(path=None):
    return json.loads(Path(path or KNOWN).read_text(encoding="utf-8"))["incidents"]


def load_local(path=None):
    p = Path(path or LOCAL)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def all_incidents(known=None, local=None):
    return load_known(known or KNOWN) + load_local(local or LOCAL)


def score(fp, inc):
    """How alike two fingerprints are: the error class weighs most, then resource, stage, provider."""
    f = inc.get("fingerprint") or {}
    s = 0
    if f.get("error_class") == fp.get("error_class") and fp.get("error_class") != "unknown":
        s += 4
    if f.get("resource") == fp.get("resource"):
        s += 2
    if f.get("stage") == fp.get("stage") and fp.get("stage") != "any":
        s += 2
    elif f.get("stage") == "any" or fp.get("stage") == "any":
        s += 1
    if f.get("provider") == fp.get("provider"):
        s += 1
    return s


def match(fp, incidents=None, limit=3, min_score=5):
    """Known incidents that look like this fingerprint, best first (empty when nothing is close enough)."""
    incidents = all_incidents() if incidents is None else incidents
    ranked = sorted(((score(fp, i), i) for i in incidents), key=lambda t: -t[0])
    return [i for s, i in ranked if s >= min_score][:limit]


def repeats(fp, incidents=None):
    """How many recorded incidents share this exact fingerprint."""
    incidents = all_incidents() if incidents is None else incidents
    return sum(1 for i in incidents if (i.get("fingerprint") or {}) == fp)


def record(fp, symptom, *, cause="unknown", fix="", cost_usd=0.0, source="guard", job=None, now=None, path=None):
    """Append what happened to this machine's log (never a secret, never a log tail with a key). Returns the row."""
    p = Path(path or LOCAL)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = load_local(p)
    row = {"id": f"LOC-{len(rows) + 1:03d}", "date": time.strftime("%Y-%m-%d", time.gmtime(now or time.time())),
           "fingerprint": fp, "symptom": symptom[:300], "cause": cause[:300], "fix": fix[:300], "cost_usd": round(float(cost_usd), 3),
           "source": source, "job": job, "repeat_of": [i["id"] for i in match(fp, load_known() + rows, limit=3)]}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def doctor(symptom, *, provider="runpod", resource="pod", stage="any", incidents=None):
    """Diagnosis lines for a symptom: its class, how often this fingerprint was seen, the known causes and fixes."""
    fp = fingerprint(provider, resource, stage, text=symptom)
    incidents = all_incidents() if incidents is None else incidents
    hits = match(fp, incidents)
    lines = [f"symptom: {symptom[:160]}", f"class: {fp['error_class']} ({resource}/{stage}); seen before with this fingerprint: {repeats(fp, incidents)}"]
    if not hits:
        lines.append("no known incident is close: read the log, find the cause, then `incidents add` it with its fix")
    for i in hits:
        lines.append(f"{i['id']} {i.get('date', '')}: {i.get('symptom', '')[:100]}")
        lines.append(f"   cause: {i.get('cause', '')[:140]}")
        lines.append(f"   fix:   {i.get('fix', '')[:140]}")
    return lines
