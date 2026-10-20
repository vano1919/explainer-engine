"""Paint plans (audit 2026-10-19, PP-01..PP-07): the image provider is chosen for every batch, the creator says yes to that batch,
and only then is anything painted. stdlib only.

A plan is one batch of pictures with its provider, model, size and price, frozen by a hash. ``options`` prices the same batch
at every provider the repo knows, so the question to the creator is one table. ``paint approve`` records the creator's yes in
the run ledger with the plan's hash; ``paint run`` refuses a plan whose hash has no approval. The prompts are the compiled ones
(``production compile``: prompt_v2 slots, POD_SUFFIX, the hero references of PV-26): a provider never changes them.

Claude does not generate images (Anthropic's vision docs: "an image understanding model only"). Claude prepares the plan,
asks, and runs the approved provider; the pixels come from that provider at that provider's price.
"""

from __future__ import annotations

import hashlib
import json
import time

from explainer_engine.imagegen import gemini

SCHEMA = "paint_plan/1"
# Every provider the repo can plan for. ``paints_here``: the repo has its client; otherwise the plan is the hand-off (the
# TMR ``cloud/`` pod runner, or a local SDXL/FLUX run) and the ledger records what that run reports.
PROVIDERS = {
    "gemini": {"service": "gemini_usd", "paints_here": True, "max_refs": gemini.MAX_REFERENCES,
               "note": "Gemini API list prices (imagegen/gemini.py PRICES); SynthID in every picture, C2PA on some models"},
    "pod": {"service": "runpod_usd", "paints_here": False, "max_refs": 3,
            "usd_per_picture": round(22.7 / 3600 * 0.89, 4),  # measured: 22.7 s a picture on an RTX 4090 at $0.89/h (PRODUCTION_RULES 4)
            "boot_usd": 0.10, "note": "RunPod reference painter (D-42, TMR cloud/); a pod needs its own price and time cap (OR-06)"},
    "local": {"service": None, "paints_here": False, "max_refs": 4, "usd_per_picture": 0.0,
              "note": "the creator's or a free machine (SDXL / FLUX.1-schnell, Apache-2.0); never FLUX.1-dev (non-commercial)"},
}


def item_hash(item: dict) -> str:
    return hashlib.sha256(json.dumps([item["id"], item["prompt"], sorted(item.get("refs", []))]).encode()).hexdigest()[:16]


def plan_hash(plan: dict) -> str:
    """What the creator approves: the pictures, their prompts and references, the provider, model, size and tier."""
    core = [plan["provider"], plan.get("model"), plan.get("size"), bool(plan.get("batch")),
            sorted((i["id"], item_hash(i)) for i in plan["items"])]
    return hashlib.sha256(json.dumps(core).encode()).hexdigest()[:20]


def price(provider: str, model: str | None, size: str | None, refs: int, batch: bool = False) -> float:
    """USD for one picture with ``refs`` reference pictures."""
    if provider == "gemini":
        table = gemini.BATCH_PRICES if batch else gemini.PRICES
        try:
            base = table[model][size]
        except KeyError:
            raise ValueError(f"no {'batch ' if batch else ''}price for {model} at {size}") from None
        return base + refs * gemini.REFERENCE_USD
    return PROVIDERS[provider]["usd_per_picture"]


def estimate(plan: dict) -> float:
    cost = sum(price(plan["provider"], plan.get("model"), plan.get("size"), len(i.get("refs", [])), plan.get("batch", False))
               for i in plan["items"])
    if plan["provider"] == "pod" and plan["items"]:
        cost += PROVIDERS["pod"]["boot_usd"]
    return round(cost, 4)


def make(plan_id: str, episode: str, items: list[dict], *, provider: str, model: str | None = None, size: str | None = None,
         batch: bool = False, purpose: str = "", reusable: bool = False) -> dict:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; known: {sorted(PROVIDERS)}")
    items = [{"id": i["id"], "prompt": i["prompt"], "refs": list(i.get("refs", [])), "first_use": i.get("first_use")}
             for i in items]
    plan = {"schema": SCHEMA, "id": plan_id, "episode": episode, "provider": provider, "model": model, "size": size,
            "batch": batch, "purpose": purpose, "reusable": reusable, "items": items,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    plan["estimate_usd"] = estimate(plan)
    plan["hash"] = plan_hash(plan)
    return plan


def options(items: list[dict]) -> list[dict]:
    """The same batch priced at every provider and Gemini tier: the table the creator chooses from."""
    rows = []
    for model, sizes in gemini.PRICES.items():
        for size in sizes:
            for batch in (False, True):
                if batch and size not in gemini.BATCH_PRICES.get(model, {}):
                    continue
                usd = sum(price("gemini", model, size, len(i.get("refs", [])), batch) for i in items)
                rows.append({"provider": "gemini", "model": model, "size": size, "batch": batch, "usd": round(usd, 4)})
    for name in ("pod", "local"):
        p = PROVIDERS[name]
        rows.append({"provider": name, "model": None, "size": None, "batch": False,
                     "usd": round(len(items) * p["usd_per_picture"] + (p.get("boot_usd", 0) if items else 0), 4)})
    return sorted(rows, key=lambda r: r["usd"])


def check(plan: dict, doc: dict | None = None) -> list[dict]:
    """PP findings for one plan: [{rule, severity, where, detail}]. Any FAIL stops ``paint run``."""
    out = []

    def add(rule, where, detail, sev="FAIL"):
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    if plan.get("schema") != SCHEMA:
        add("PP-01", plan.get("id"), f"not a {SCHEMA} file")
        return out
    prov = PROVIDERS.get(plan["provider"])
    if prov is None:
        add("PP-01", plan["id"], f"unknown provider {plan['provider']!r}")
        return out
    if plan_hash(plan) != plan.get("hash"):
        add("PP-02", plan["id"], "the plan was edited after it was made: make it again (its hash no longer matches)")
    if plan["provider"] == "gemini":
        try:
            price("gemini", plan.get("model"), plan.get("size"), 0, plan.get("batch", False))
        except ValueError as exc:
            add("PP-03", plan["id"], str(exc))
    for it in plan["items"]:
        if len(it.get("refs", [])) > prov["max_refs"]:
            add("PP-03", it["id"], f"{len(it['refs'])} references; {plan['provider']} takes at most {prov['max_refs']}")
        if not it.get("prompt", "").strip():
            add("PP-04", it["id"], "empty prompt: run `production compile --write` first")
    # PP-05 (D-50 supersedes D-19's "Gemini only for reusable assets"): the creator picks the provider per batch and the
    # approval is bound to this plan's hash (PP-02), so Gemini on one episode's pictures is allowed; the reusable question
    # stays a note for the creator, never a refusal.
    if plan["provider"] == "gemini" and not plan.get("reusable"):
        exc = ((doc or {}).get("episode") or {}).get("gemini_exception")
        if not exc:
            add("PP-05", plan["id"], "Gemini for one episode's pictures (not marked reusable): the creator's provider choice for this "
                                     "batch is the decision (D-50); say in the approval that it is this episode's spend", "REVIEW")
    if doc is not None:
        from explainer_engine.production import compile as C
        from explainer_engine.production import faces as FACES
        from explainer_engine.production import script as S
        pics, _ = S.pictures(doc)
        faces = {i["id"]: i for i in FACES.to_paint(doc)}
        for it in plan["items"]:
            p = pics.get(it["id"])
            if p is None and it["id"] in faces:  # a close-up of an expression sheet (VB-09)
                if faces[it["id"]]["prompt"] != it["prompt"]:
                    add("PP-06", it["id"], "the hero's card or the sheet changed since the plan was made: make the plan again")
            elif p is None:
                add("PP-06", it["id"], "not a picture of this script")
            elif p.get("prompt") and p["prompt"].replace(C.POD_SUFFIX, "") != it["prompt"].replace(C.POD_SUFFIX, ""):
                add("PP-06", it["id"], "the script's prompt changed since the plan was made: make the plan again")
    if not plan.get("purpose", "").strip():
        add("PP-07", plan["id"], "say what the batch is for (the creator's rule: every paid call states its purpose)", "REVIEW")
    for it in plan["items"]:  # OR-18 (D-63): the picture library had matches when the plan was made; the creator decides
        if it.get("library"):
            add("PP-08", it["id"], "the picture library may already have this: " + ", ".join(it["library"]) +
                " (fetch with python -m explainer_engine.imagegen.picture_library fetch, or say in the approval why not)",
                "REVIEW")
    return out


def table(rows: list[dict], chosen: dict | None = None) -> str:
    lines = ["provider  model                          size  tier    USD"]
    for r in rows:
        mark = " <" if chosen and all(r[k] == chosen.get(k) for k in ("provider", "model", "size", "batch")) else ""
        lines.append(f"{r['provider']:9} {str(r['model'] or '-'):30} {str(r['size'] or '-'):5} "
                     f"{'batch' if r['batch'] else 'sync':7} {r['usd']:.3f}{mark}")
    return "\n".join(lines)
