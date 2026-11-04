# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/cloud/incidents.py`
# Target Module : explainer_engine/cloud/incidents.py
# Target Classes/Symbols : def classify(), def fingerprint(), def load_known(), def load_local(), def all_incidents(), def score(), def match(), def repeats(), def record(), def doctor()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this cloud execution module with the 4-tier hybrid visual pipeline (`Tier 1 parallax_25d`, `Tier 2 qwen_nextpose`, `Tier 3 ltx_1080p`, `Tier 4 ltx_portrait_720p`), locking `xworld_v2` LoRA weight at `0.7` (`CD-02`), enforcing `8k+1` LTX frame buckets with frame-exact tail trim metadata, enforcing `CD-06` (`living == False`) before dispatching Tier 4 audio-to-video jobs, and recording per-zone (`cold_open..coda`) GPU wall-clock telemetry (`CD-05`) under hard `try/finally` pod termination (`D-78` / `BP-148`).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this cloud module targets the pre-Master-Mold v2/v3 worker contract and does not propagate `/4` `tension_zone`, `scene_type`, `character_id` voice-clearance tokens (`CD-06`), or per-zone timing telemetry (`CD-05`).
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Prevents wasted GPU spend on invalid payloads, guarantees pod teardown (`$0.00` idle storage leak), and aligns worker execution with `config/cloud_pins.json`.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] RunPod Pods Pricing & Per-Second Billing
#        URL: https://docs.runpod.io/pods/pricing
#        Rationale: Details per-second GPU billing for RTX PRO 6000 Blackwell ($1.89/hr Secure Cloud) and H200 SXM ($3.59/hr), requiring hard budget caps and empirical runtime measurement.
#    [2] RunPod Account Billing & Storage Costs
#        URL: https://docs.runpod.io/accounts-billing/billing
#        Rationale: Documents that stopped pods still incur container/volume storage charges until terminated (`runpodctl remove pod`), grounding D-78 / BP-148 auto-teardown.
#    [3] PyTorch torch.compile Tutorial & Cold-Start Behavior
#        URL: https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html
#        Rationale: Explains why compilation overhead is avoided (`compile_mode: none` for <=2 segments in cloud_pins.json) and why cold-start must be amortized.
#    [4] GitHub Docs — About Protected Branches
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
#        Rationale: Specifies required status checks (`quality`), PR-only merge enforcement, and branch protection rules required by GATE-EXT-MAIN-PROTECT.
#    [5] GitHub Docs — Managing Rulesets for a Repository
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
#        Rationale: Specifies ruleset protections preventing force-pushes, accidental branch deletion, and unreviewed merges into main.
#    [6] Python 3.12 What's New — PEP 701 Syntactic Formalization of f-strings
#        URL: https://docs.python.org/3/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
#        Rationale: Explains why nested double-quotes inside an f-string expression (`blind_check.py:36`) raise SyntaxError on Python 3.11 even though Python 3.12+ permits them.
# =============================================================================

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
