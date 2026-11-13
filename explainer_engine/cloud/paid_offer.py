"""CH-07: the paid offer, checked before any thread offers the creator a paid Modal run (D-133 as amended 2026-11-13 14:47 UTC).

The creator, 2026-11-13 14:37 UTC (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPW4rpktDxvJ3cn9nLY9QaMLC), with his card answer at 14:47 UTC
(relayed by the coordinator: "free" = the free credit or balance first, then the GPU cards): before any thread offers him a paid
option it (1) checks Modal's free credit and what this month has used, so free credit is spent before real money and the offer
says how much is free and how much is paid; (2) checks which GPU types Modal offers now and their per-second price, and takes the
cheapest card that fits the job's VRAM (a measured or known number, never a guess: the 2026-11-13 L3 smoke ran out of memory on
an H100) and its time; (3) compares at least two full combinations (card + model loaded once + batching + container reuse + clip
length) with their prices; (4) only then posts the offer card with the cheapest combination, the free/paid split, the cap and
the watchdog. The rule text is CH-07 in docs/CLOUD_RUNBOOK.md; ``cheapest.offer_refusal`` makes the hook refuse a paid LTX
rung whose ``EE_PAID_OFFER`` file is missing, stale or fails here.

What Modal lets us read (checked 2026-11-13, all free and read-only):
- the credit: ``modal billing summary --json`` (``Workspace.billing.summary``: ``metered_cost`` is this month's cost before the
  plan credit; free left = the Starter credit minus it). It needs Modal's gRPC API, which the cloud container's proxy does not
  carry, so a thread there falls back to the project ledgers' Modal spend of the month (``ledger_sum``, a lower bound of the
  use, labelled so in the offer) or the creator's own number (``creator``, his message id);
- the cards and prices: ``modal billing rates --json`` (gRPC again) or the public page https://modal.com/pricing (parsed here);
- availability: Modal publishes no free-capacity figure (its GPU guide: a list of cards is a fallback order, the first free one
  is taken). The check is that the card is on today's price list and that status.modal.com reports Functions operational
  (``https://status.modal.com/index.json``); notices (a planned maintenance) go into the offer.
stdlib only; every fetch takes an injectable getter so the tests run offline."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "paid_offer/1"
PRICING_URL = "https://modal.com/pricing"
STATUS_URL = "https://status.modal.com/index.json"
MONTHLY_FREE_USD = 30.0          # Modal Starter: $30 of compute credit a month (modal.com/pricing, checked 2026-11-13)
CREDIT_HOURS = 24                # a credit check older than this is stale
GPU_HOURS = 6                    # a card/price/status check older than this is stale
COST_TOL = 0.05                  # a combination's stated price within 5 % of gpu_s x its rate
CREDIT_SOURCES = ("modal_billing_summary", "ledger_sum", "creator")
GPU_SOURCES = ("modal_billing_rates", "modal_pricing_page")
VRAM_BASES = ("measured", "known")
SPEED_BASES = ("measured", "estimate")
WATCHDOG_MODEL = "haiku"         # project rule 11: a cheap Haiku low-effort watchdog beside every paid run
PAGE_NAMES = {"B300": "B300", "B200": "B200", "H200 SXM": "H200", "H100 SXM5": "H100", "RTX PRO 6000": "RTX-PRO-6000",
              "A100, 80 GB": "A100-80GB", "A100, 40 GB": "A100-40GB", "L40S": "L40S", "A10": "A10", "L4": "L4", "T4": "T4"}


def _iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _http_get(url: str, timeout: float = 20.0) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "explainer-engine-paid-offer/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310 - fixed https URLs above
        return r.read().decode("utf-8", "replace")


def _modal_cli(args: list[str], timeout: float = 40.0) -> str | None:
    """``modal <args>`` (read-only billing commands only), or None when the CLI or its gRPC API is not reachable."""
    if args[:1] != ["billing"] or args[1:2] not in (["summary"], ["rates"]):
        raise ValueError("only `modal billing summary|rates` are read here")
    try:
        r = subprocess.run(["modal", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 and r.stdout.strip() else None


# ---- (1) the free credit -------------------------------------------------------------------------------------------------

def credit_from_summary(raw: str, now: dt.datetime) -> dict:
    """``modal billing summary --json``: this month's ``metered_cost`` (before the plan credit) and ``billed_cost``."""
    d = json.loads(raw)
    used = float(d["metered_cost"])
    return {"checked_at": _iso(now), "source": "modal_billing_summary", "ref": "modal billing summary --json (this month)",
            "monthly_free_usd": MONTHLY_FREE_USD, "used_usd": round(used, 4), "billed_usd": float(d.get("billed_cost", 0)),
            "free_left_usd": round(max(0.0, MONTHLY_FREE_USD - used), 4)}


def credit_from_ledgers(folder, now: dt.datetime) -> dict:
    """The Modal spend of this month in the project ledgers (``core/ledger.Run`` files): a LOWER bound of Modal's own use
    (a run without a ledger is not in it), so the free credit it implies is an upper bound and the offer says so."""
    month, used, files = now.strftime("%Y-%m"), 0.0, []
    for p in sorted(Path(folder).glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not str(d.get("created", "")).startswith(month):
            continue
        part = sum(float(v) for k, v in (d.get("spent") or {}).items() if k.startswith("modal") and _num(v))
        if part:
            used += part
            files.append(p.name)
    return {"checked_at": _iso(now), "source": "ledger_sum", "ref": f"{folder}: {', '.join(files) or 'no Modal spend'}",
            "monthly_free_usd": MONTHLY_FREE_USD, "used_usd": round(used, 4),
            "free_left_usd": round(max(0.0, MONTHLY_FREE_USD - used), 4)}


def fetch_credit(now: dt.datetime, ledgers=None, cli=_modal_cli) -> dict:
    raw = cli(["billing", "summary", "--json"])
    if raw:
        try:
            return credit_from_summary(raw, now)
        except (ValueError, KeyError, TypeError):
            pass
    folder = ledgers or os.environ.get("EXPLAINER_LEDGER_MIRROR") or "/mnt/project-files/explainer-engine/ledgers"
    return credit_from_ledgers(folder, now)


# ---- (2) the cards, their prices and Modal's state -----------------------------------------------------------------------

def gpus_from_page(page: str) -> dict:
    """The per-second prices of https://modal.com/pricing (its text reads "Nvidia H100 SXM5 $ 0.001097 0 . 0 0 1 ... / sec")."""
    from explainer_engine.cloud import modal_schedule as MS
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    rows = []
    for m in re.finditer(r"Nvidia ([A-Za-z0-9 ,]+?) \$ ([0-9.]+) [0-9 .]+/ sec", txt):
        gpu = PAGE_NAMES.get(m.group(1))
        if gpu and gpu not in [r["gpu"] for r in rows]:
            rows.append({"gpu": gpu, "usd_s": float(m.group(2)), "vram_gb": MS.GPUS.get(gpu, {}).get("vram_gb")})
    cpu = re.search(r"CPU \$ ([0-9.]+)", txt)
    mem = re.search(r"Memory \$ ([0-9.]+)", txt)
    if not rows or not cpu or not mem:
        raise ValueError("the pricing page no longer reads as expected: no GPU rows or no CPU/memory price")
    return {"source": "modal_pricing_page", "ref": PRICING_URL, "rows": rows,
            "cpu_core_usd_s": float(cpu.group(1)), "mem_gib_usd_s": float(mem.group(1))}


def status_from_index(raw: str) -> dict:
    """status.modal.com (Better Stack): the Functions resource and every report that is not resolved."""
    d = json.loads(raw)
    res, notes = {}, []
    for x in d.get("included", []):
        a = x.get("attributes") or {}
        if x.get("type") == "status_page_resource":
            res[a.get("public_name")] = a.get("status")
        elif x.get("type") == "status_report" and a.get("aggregate_state") not in ("resolved", None):
            notes.append(f"{a.get('aggregate_state')}: {a.get('title')} ({a.get('starts_at')} .. {a.get('ends_at')})")
    return {"status_source": STATUS_URL, "functions_status": res.get("Functions", "unknown"), "notices": notes}


def fetch_gpus(now: dt.datetime, get=_http_get) -> dict:
    out = gpus_from_page(get(PRICING_URL))
    out.update(status_from_index(get(STATUS_URL)))
    out["checked_at"] = _iso(now)
    return out


# ---- (3) the combinations and (4) the offer ------------------------------------------------------------------------------

def rate(combo: dict, gpus: dict) -> float | None:
    """$ a second of one container of the combination: the card plus its CPU cores and memory (Modal bills all three)."""
    row = next((r for r in gpus.get("rows") or [] if r.get("gpu") == combo.get("gpu")), None)
    if not row or not _num(combo.get("cpu")) or not _num(combo.get("memory_gib")):
        return None
    return row["usd_s"] + combo["cpu"] * gpus["cpu_core_usd_s"] + combo["memory_gib"] * gpus["mem_gib_usd_s"]


def price(offer: dict) -> dict:
    """Fill each combination's ``est_usd`` / ``worst_usd`` from its GPU seconds, the split of the chosen one into free credit
    and paid money, and nothing else (the thread states the combinations, their seconds and the bases)."""
    for c in offer.get("combos") or []:
        r = rate(c, offer.get("gpus") or {})
        if r is not None and _num(c.get("gpu_s")) and _num(c.get("worst_gpu_s")):
            c["est_usd"] = round(c["gpu_s"] * r, 4)
            c["worst_usd"] = round(c["worst_gpu_s"] * r, 4)
    ch = next((c for c in offer.get("combos") or [] if c.get("id") == offer.get("chosen")), None)
    left = (offer.get("credit") or {}).get("free_left_usd")
    if ch and _num(ch.get("est_usd")) and _num(left):
        free = round(min(ch["est_usd"], left), 4)
        worst_free = round(min(ch["worst_usd"], left), 4)
        offer["split"] = {"free_usd": free, "paid_usd": round(ch["est_usd"] - free, 4),
                          "worst_free_usd": worst_free, "worst_paid_usd": round(ch["worst_usd"] - worst_free, 4)}
    return offer


def problems(offer: dict, now: dt.datetime | None = None) -> list[str]:
    """Every reason the offer may not be posted to the creator (CH-07); [] when it may."""
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    if offer.get("schema") != SCHEMA:
        out.append(f"schema must be {SCHEMA}")

    cr = offer.get("credit")
    if not isinstance(cr, dict):
        out.append("the free-credit check is missing (step 1: Modal's monthly credit and this month's use come first)")
    else:
        t = _parse(cr.get("checked_at"))
        if cr.get("source") not in CREDIT_SOURCES:
            out.append(f"credit source {cr.get('source')!r} is not one of {CREDIT_SOURCES}")
        if not str(cr.get("ref") or "").strip():
            out.append("the credit check names no reference (the command, the ledger files or the creator's message id)")
        if t is None or not 0 <= (now - t).total_seconds() <= CREDIT_HOURS * 3600:
            out.append(f"the credit check is older than {CREDIT_HOURS} h or undated")
        if not all(_num(cr.get(k)) for k in ("monthly_free_usd", "used_usd", "free_left_usd")):
            out.append("the credit check needs monthly_free_usd, used_usd and free_left_usd")
        elif abs(cr["free_left_usd"] - max(0.0, cr["monthly_free_usd"] - cr["used_usd"])) > 0.01:
            out.append("free_left_usd is not the monthly credit minus this month's use")

    g = offer.get("gpus")
    if not isinstance(g, dict):
        out.append("the GPU availability check is missing (step 2: today's Modal cards, prices and status)")
        g = {}
    else:
        t = _parse(g.get("checked_at"))
        if g.get("source") not in GPU_SOURCES:
            out.append(f"GPU price source {g.get('source')!r} is not one of {GPU_SOURCES}")
        if t is None or not 0 <= (now - t).total_seconds() <= GPU_HOURS * 3600:
            out.append(f"the GPU check is older than {GPU_HOURS} h or undated")
        if g.get("functions_status") != "operational":
            out.append(f"Modal Functions are {g.get('functions_status')!r} on status.modal.com, not operational: no offer now")
        if not g.get("rows") or not all(_num(r.get("usd_s")) and r["usd_s"] > 0 and _num(r.get("vram_gb"))
                                        for r in g["rows"]):
            out.append("the GPU check lists no cards with a price and VRAM")
        if not (_num(g.get("cpu_core_usd_s")) and _num(g.get("mem_gib_usd_s"))):
            out.append("the GPU check needs the CPU-core and memory prices (a container bills them too)")

    need = offer.get("need") or {}
    if not (_num(need.get("vram_gb")) and need["vram_gb"] > 0):
        out.append("the job's VRAM need is missing")
    if need.get("basis") not in VRAM_BASES or not str(need.get("ref") or "").strip():
        out.append("the VRAM need must be measured or known, with its reference, never a guess (the L3 smoke of "
                   "2026-11-13 ran out of memory on an H100)")

    combos = [c for c in offer.get("combos") or [] if isinstance(c, dict)]
    ids = [c.get("id") for c in combos]
    if len(combos) < 2 or len(set(ids)) != len(ids):
        out.append("compare at least two combinations with distinct ids (step 3)")
    vram = {r.get("gpu"): r.get("vram_gb") for r in g.get("rows") or []}
    fits = {}
    for c in combos:
        cid = c.get("id")
        r = rate(c, g) if g else None
        if c.get("gpu") not in vram:
            out.append(f"combo {cid}: card {c.get('gpu')!r} is not on today's Modal list")
            continue
        fits[cid] = _num(need.get("vram_gb")) and (vram[c["gpu"]] or 0) >= need["vram_gb"]
        if c.get("speed_basis") not in SPEED_BASES or not str(c.get("speed_ref") or "").strip():
            out.append(f"combo {cid}: state speed_basis measured/estimate with its reference")
        for k in ("model_loads_per_container", "containers", "scenes", "clips", "generated_s", "scaledown_s"):
            if not _num(c.get(k)):
                out.append(f"combo {cid}: {k} is missing (the setup is part of the combination)")
        if r is None or not (_num(c.get("gpu_s")) and _num(c.get("worst_gpu_s")) and _num(c.get("est_usd"))
                             and _num(c.get("worst_usd"))):
            out.append(f"combo {cid}: gpu_s, worst_gpu_s, cpu, memory_gib and the prices are needed")
            continue
        if abs(c["est_usd"] - c["gpu_s"] * r) > COST_TOL * max(c["gpu_s"] * r, 0.01) \
                or abs(c["worst_usd"] - c["worst_gpu_s"] * r) > COST_TOL * max(c["worst_gpu_s"] * r, 0.01):
            out.append(f"combo {cid}: the stated price is not its seconds x today's rate (run `paid_offer price`)")
        if c["worst_usd"] < c["est_usd"]:
            out.append(f"combo {cid}: the worst case is below the expected cost")

    ch = next((c for c in combos if c.get("id") == offer.get("chosen")), None)
    if ch is None:
        out.append("no chosen combination")
    else:
        from explainer_engine.cloud import cheapest
        if not fits.get(ch.get("id")):
            out.append(f"the chosen card {ch.get('gpu')} does not fit the job's {need.get('vram_gb')} GB")
        if ch.get("model_loads_per_container") != 1:
            out.append("the chosen combination loads the model more than once a container (CH-01)")
        if _num(ch.get("scaledown_s")) and ch["scaledown_s"] > cheapest.MAX_SCALEDOWN_S:
            out.append(f"the chosen combination stays warm {ch['scaledown_s']} s (CH-04: at most {cheapest.MAX_SCALEDOWN_S} s)")
        if _num(ch.get("containers")) and _num(ch.get("scenes")) and ch["containers"] > ch["scenes"]:
            out.append("the chosen combination starts more containers than it has scenes (CH-03)")
        for c in combos:
            if c is ch or not fits.get(c.get("id")) or not (_num(c.get("est_usd")) and _num(ch.get("est_usd"))):
                continue
            if c["est_usd"] < ch["est_usd"] and c.get("model_loads_per_container") == 1 \
                    and not str(c.get("not_chosen_why") or "").strip():
                out.append(f"combo {c.get('id')} ({c.get('gpu')}, ${c['est_usd']}) is cheaper than the chosen one "
                           f"(${ch['est_usd']}): take it or say why not (not_chosen_why)")
        sp = offer.get("split") or {}
        left = (cr or {}).get("free_left_usd") if isinstance(cr, dict) else None
        if not all(_num(sp.get(k)) for k in ("free_usd", "paid_usd")) or not _num(left) or not _num(ch.get("est_usd")):
            out.append("the free/paid split is missing (step 4: free credit is spent before real money)")
        elif abs(sp["free_usd"] - min(ch["est_usd"], left)) > 0.005 or abs(sp["free_usd"] + sp["paid_usd"] - ch["est_usd"]) > 0.005:
            out.append("the split does not spend the free credit first")
        cap = offer.get("cap_usd")
        if not (_num(cap) and _num(ch.get("worst_usd")) and cap >= ch["worst_usd"]):
            out.append("the cap is missing or below the chosen combination's worst case")
    wd = offer.get("watchdog") or {}
    if wd.get("model") != WATCHDOG_MODEL or not _num(wd.get("every_min")):
        out.append("the watchdog (a Haiku thread and its check interval, rule 11) is missing")
    return out


def offer_text(offer: dict) -> str:
    """The lines of the offer card, in Georgian (the creator reads Georgian)."""
    ch = next(c for c in offer["combos"] if c["id"] == offer["chosen"])
    cr, sp, g = offer["credit"], offer["split"], offer["gpus"]
    src = {"modal_billing_summary": "Modal-ის ანგარიში", "ledger_sum": "ჩვენი ledger-ები (Modal-ის ანგარიში მიუწვდომელია; "
           "გამოყენება შეიძლება მეტი იყოს)", "creator": "შენი ციფრი"}[cr["source"]]
    lines = [f"ყველაზე იაფი: {ch['gpu']}, {ch['clips']} კლიპი, {ch['generated_s']} წმ, მოდელი ერთხელ იტვირთება, "
             f"{ch['containers']} კონტეინერი; ~${ch['est_usd']} (უარესი ${ch['worst_usd']}).",
             f"უფასო კრედიტიდან ${sp['free_usd']}, ფასიანი ${sp['paid_usd']} (უფასო დარჩა ${cr['free_left_usd']} / "
             f"${cr['monthly_free_usd']}, წყარო: {src}).",
             "შედარება: " + "; ".join(f"{c['id']} {c['gpu']} ~${c['est_usd']} ({c['speed_basis']})"
                                      + (f" — {c['not_chosen_why']}" if c.get("not_chosen_why") else "")
                                      for c in offer["combos"]),
             f"ჭერი ${offer['cap_usd']}; watchdog: Haiku, ყოველ {offer['watchdog']['every_min']} წთ. "
             f"Modal: Functions {g['functions_status']}" + (f"; {'; '.join(g['notices'])}" if g.get("notices") else "")]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.cloud.paid_offer", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="steps 1-2: fill the credit and the GPU check of a draft offer (read-only, free)")
    f.add_argument("draft")
    f.add_argument("--ledgers", help="the ledger folder for the credit fallback")
    p = sub.add_parser("price", help="step 3-4: price every combination and split the chosen one into free/paid")
    p.add_argument("draft")
    c = sub.add_parser("check", help="CH-07: exit 1 and list the problems, or print the offer card's text")
    c.add_argument("offer")
    a = ap.parse_args(argv)
    from explainer_engine.core.store import write_json_atomic
    now = dt.datetime.now(dt.timezone.utc)
    path = Path(getattr(a, "draft", None) or a.offer)
    offer = json.loads(path.read_text(encoding="utf-8"))
    if a.cmd == "fetch":
        offer.setdefault("schema", SCHEMA)
        offer["credit"] = fetch_credit(now, a.ledgers)
        offer["gpus"] = fetch_gpus(now)
        write_json_atomic(path, price(offer))
        print(json.dumps({"credit": offer["credit"], "functions": offer["gpus"]["functions_status"],
                          "notices": offer["gpus"]["notices"]}, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "price":
        write_json_atomic(path, price(offer))
        return 0
    found = problems(offer, now)
    if found:
        print("CH-07 FAIL:\n- " + "\n- ".join(found), file=sys.stderr)
        return 1
    print(offer_text(offer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
