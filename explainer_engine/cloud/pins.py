# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/cloud/pins.py`
# Target Module : explainer_engine/cloud/pins.py
# Target Classes/Symbols : class PinError (methods: ), def load(), def image_ref(), def resolve_image(), def entry_of(), def check_image(), def boot_minutes_needed(), def pins_txt_expected(), def compare()
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

"""``config/cloud_pins.json``: the digest of every pod image, the sha of every cloned repo and the version of every pip package a
pod job may depend on (P1b, CR-18). stdlib only. ``runpod create`` refuses a script pod whose image is not one of these, by
digest; ``compare`` checks the ``pins.txt`` a pod wrote against the file; ``boot_minutes_needed`` is the image-cache rule.

A pin enters the file as a registry / GitHub lookup (``looked_up``) and carries ``smoke_verified: false`` until a pod has shown it
works. A value that is ``null`` was not decided: nothing here guesses it (Rule one, OR-22).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS_FILE = ROOT / "config" / "cloud_pins.json"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
# An image the pins file has no measured pull speed for may take this long to arrive on a COMMUNITY host (a cold host pulls it
# whole): docs/LORA_TRAINING.md LT-15 / lora_rules.json ``boot_minutes_aitoolkit``, and the P1b card (unknown image on COMMUNITY).
UNKNOWN_COMMUNITY_BOOT_MINUTES = 25
DEFAULT_IMAGE = "tmr_pod"  # what a script pod runs when ``--image`` is not given (decision B3: same image, by digest)


# TODO [CLAUDE-CLASS-SYNC: PinError] (BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization)): Synchronize class `PinError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class PinError(Exception):
    pass


def load(path=None):
    p = Path(path or PINS_FILE)
    data = json.loads(p.read_text(encoding="utf-8"))
    for key in ("images", "git", "pip"):
        if not isinstance(data.get(key), dict):
            raise PinError(f"{p}: no '{key}' table")
    return data


def image_ref(key, pins=None):
    """``repo@sha256:...`` of a pinned image key; PinError when it has no digest yet."""
    pins = pins or load()
    e = pins["images"].get(key)
    if e is None:
        raise PinError(f"no image pin '{key}' in cloud_pins.json (known: {', '.join(sorted(pins['images']))})")
    if not e.get("digest"):
        raise PinError(f"image pin '{key}' ({e['repo']}) has no digest yet: it is not decided (cloud_pins.json)")
    if not DIGEST.match(e["digest"]):
        raise PinError(f"image pin '{key}': '{e['digest']}' is not a sha256 digest")
    return f"{e['repo']}@{e['digest']}"


def resolve_image(arg, pins=None):
    """``--image`` value -> the image string: a pin key (``smoke``, ``aitoolkit``) becomes ``repo@digest``; anything else is kept
    as typed (``check_image`` judges it)."""
    pins = pins or load()
    return image_ref(arg, pins) if arg in pins["images"] else arg


def entry_of(image, pins=None):
    """(key, entry) of the pin an image string names (repo and digest both match), or (None, None)."""
    pins = pins or load()
    repo, _, digest = (image or "").partition("@")
    for key, e in pins["images"].items():
        if e["repo"] == repo and e.get("digest") and e["digest"] == digest:
            return key, e
    return None, None


def check_image(image, pins=None):
    """Refusals for the image of a script pod (empty = allowed): a digest, and one that cloud_pins.json lists."""
    pins = pins or load()
    if "@" not in (image or ""):
        return [f"image {image!r} is not pinned by digest: use a key of config/cloud_pins.json ({', '.join(sorted(pins['images']))}) "
                "or repo@sha256:... (CR-18)"]
    key, _ = entry_of(image, pins)
    if key is None:
        repo = image.partition("@")[0]
        known = [k for k, e in pins["images"].items() if e["repo"] == repo]
        if known and not pins["images"][known[0]].get("digest"):
            return [f"image pin '{known[0]}' ({repo}) has no digest yet: it is not decided (cloud_pins.json)"]
        return [f"image {image} is not in config/cloud_pins.json: a changed pin is a PR, not a flag (CR-18)"]
    return []


def boot_minutes_needed(image, cloud, pins=None, base=10.0):
    """The boot deadline a pod needs for this image (CR-18, the image-cache rule). A measured pull speed
    (``pull_mb_per_s``) gives ``base`` + the pull time of ``size_gb``; without a measurement an image on a COMMUNITY host needs
    ``UNKNOWN_COMMUNITY_BOOT_MINUTES``, one on SECURE the ``base``."""
    key, e = entry_of(image, pins)
    if e is None:
        return UNKNOWN_COMMUNITY_BOOT_MINUTES if str(cloud).upper() == "COMMUNITY" else base
    mbps, size = e.get("pull_mb_per_s"), e.get("size_gb")
    if mbps and size:
        return base + math.ceil(size * 1024 / float(mbps) / 60)
    return UNKNOWN_COMMUNITY_BOOT_MINUTES if str(cloud).upper() == "COMMUNITY" else base


def pins_txt_expected(pins=None):
    """``{key: value}`` of every pin as a pod writes it into ``$EE_OUT/pins.txt`` (one ``key=value`` per line):
    ``image=<digest>``, ``git:<owner>/<repo>=<sha>``, ``pip:<name>=<version>``."""
    pins = pins or load()
    out = {f"git:{k}": e["sha"] for k, e in pins["git"].items() if e.get("sha")}
    out.update({f"pip:{k}": e["version"] for k, e in pins["pip"].items() if e.get("version")})
    return out


def compare(pins_txt, pins=None):
    """Problems of a pod's ``pins.txt`` against the pins file (empty = it ran what the file says). Only keys the pod reports are
    compared: a pin the job never used is not a mismatch; an ``image=`` line must be one of the pinned digests."""
    pins = pins or load()
    want = pins_txt_expected(pins)
    digests = {e["digest"] for e in pins["images"].values() if e.get("digest")}
    out = []
    for raw in (pins_txt or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = (s.strip() for s in line.split("=", 1))
        if k == "image":
            if v not in digests:
                out.append(f"image {v} is not a digest of config/cloud_pins.json")
        elif k in want and v != want[k]:
            out.append(f"{k}: the pod ran {v}, the pins say {want[k]}")
        elif k.startswith(("git:", "pip:")) and k not in want:
            out.append(f"{k}={v}: not a pin of config/cloud_pins.json")
    return out
