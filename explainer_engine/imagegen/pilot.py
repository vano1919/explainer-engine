"""The stage D model pilot (D-70; the creator's card of 2026-10-22): the same six shots on every candidate, four takes each,
priced before anything is sent, run only with the creator's recorded approval, every picture cached and logged, one
collage per candidate for the creator's eyes (OR-16). stdlib + PIL for the collage.

Shots (TOOLING_RESEARCH section 2): 1 hero turnaround sheet; 2 two heroes in a named room; 3 the reverse angle of shot 2 as
an EDIT of it; 4 a close-up expression change as an EDIT of shot 2; 5 the same heroes in another era, same style; 6 an
in-style sign with legible text. Editors (Qwen-Image-Edit) start from a blank canvas on shots 1, 2, 5 and 6, which is
recorded in the results: they are judged as continuity editors, not as composers.

Scoring here is what code can do for free and honestly: exact cost, wall-clock, refusals and errors per take, and the
collage; the SigLIP-2 / DINOv2 similarity scores of the research need a model download and are NOT computed by this
module (results say ``"embedding_scores": "not computed"``). The creator's 1-5 on the look is the deciding score.

    python -m explainer_engine.imagegen.pilot estimate [--takes 4] [--candidates bfl:flux-3-image-klein:1k,...]
    python -m explainer_engine.imagegen.pilot run --out jobs/pilot/<date> --approved-by "ვანო" --ref <message> [--takes 4]
    python -m explainer_engine.imagegen.pilot collage --out jobs/pilot/<date>
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
from pathlib import Path

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.core.store import write_json_atomic
from explainer_engine.imagegen import providers
from explainer_engine.imagegen.providers.base import AccountError, ChargeUncertain, ProviderError

STYLE = ("colourful hand-drawn 2D animation illustration, clean confident ink lines, flat cel shading with soft painted light, "
         "expressive adult faces, consistent character design, one artist's hand throughout, no text unless asked, no logo")
HEROES = ("MIRA, a tall woman of about forty with short grey-streaked black hair, a scar over the left eyebrow, a dark green "
          "field jacket; and TEO, a stocky young man with round glasses, curly red hair, a mustard scarf and a brown satchel")
ROOM = "a cramped 1890s telegraph office: brass instruments, paper tape on the floor, one green-shaded lamp, rain on the window"
# (id, title, prompt, kind, source shot) — kind: t2i (no source), ref (source as a reference), edit (source edited)
SHOTS = [
    ("s1_sheet", "hero sheet", f"character turnaround sheet of {HEROES}: front, side and back views of each, neutral grey background, {STYLE}", "t2i", None),
    ("s2_room", "two heroes in the room", f"{HEROES} arguing over a telegram inside {ROOM}; Mira stands left by the window, Teo sits right at the desk, medium shot, {STYLE}", "ref", "s1_sheet"),
    ("s3_reverse", "reverse angle (edit)", "the same scene from the opposite side of the room: now Teo at the desk is on the left and Mira by the window on the right, same lamp, same rain, same clothes, nothing added or removed", "edit", "s2_room"),
    ("s4_closeup", "expression change (edit)", "close-up of Teo's face from the same scene, his expression changing to alarmed surprise, glasses and scarf unchanged, same lamp light", "edit", "s2_room"),
    ("s5_era", "era jump, same style", f"{HEROES} standing in a 1969 mission control room, rows of green consoles, cigarette haze, same drawing style and faces as the reference", "ref", "s1_sheet"),
    ("s6_sign", "legible sign text", "a wooden shop sign hanging over the telegraph office door that reads exactly 'WESTERN UNION' in painted serif letters, rain-wet, same style", "ref", "s2_room"),
]
# The style step (the creator, 2026-10-22: "show me style variants to approve"): one scene, six looks, one take each, on the
# two text-to-image candidates; the creator picks the look the model comparison then runs in (OR-16: one collage per choice).
# The six looks are the creator's own mix of reference qualities (below).
STYLE_SCENE = f"{HEROES} arguing over a telegram inside {ROOM}; Mira stands left by the window, Teo sits right at the desk, medium shot"
# The creator's mix (2026-10-22 12:31): the volume and character acting of a big-studio animal comedy, the clean repeatable
# character design of an adult sci-fi cartoon, the composition and cinematic environments of a stylised samurai series, the
# comedic squash-and-stretch faces of an undersea cartoon. Six blends of those QUALITIES, described in our own words: no
# show, studio, artist or character is named in a prompt (look_v2 "no_names", RIGHTS_AND_FAIR_USE, invariant 5).
QUALITIES = {
    "volume": "soft rounded 3D-like volumes with exaggerated body shapes, strong personality in every pose",
    "clean_design": "clean simple consistent character designs with uniform line weight, easy to redraw from any angle",
    "cinematic": "bold graphic cinematic composition, wide framing with strong silhouettes, negative space, stylised flat-colour environments",
    "elastic_faces": "rubbery squash-and-stretch faces with big comedic expressions and readable mouth shapes",
}
STYLES = [
    ("mix_volume_cinematic", "volume + cinematic", f"{QUALITIES['volume']}; {QUALITIES['cinematic']}; warm saturated palette"),
    ("mix_volume_faces", "volume + comic faces", f"{QUALITIES['volume']}; {QUALITIES['elastic_faces']}; bright playful palette"),
    ("mix_clean_cinematic", "clean design + cinematic", f"{QUALITIES['clean_design']}; {QUALITIES['cinematic']}; limited bold palette with one accent colour"),
    ("mix_clean_faces", "clean design + comic faces", f"{QUALITIES['clean_design']}; {QUALITIES['elastic_faces']}; flat bright colours, thin dark outlines"),
    ("mix_all_four", "all four, balanced", f"{QUALITIES['volume']}; {QUALITIES['clean_design']}; {QUALITIES['cinematic']}; {QUALITIES['elastic_faces']}"),
    ("mix_cinematic_dark", "cinematic, dramatic", f"{QUALITIES['cinematic']}; {QUALITIES['volume']}; dramatic single key light, deep shadows, moody palette"),
]
BANNED_NAMES = ("madagascar", "rick", "morty", "samurai jack", "spongebob", "dreamworks", "nickelodeon", "cartoon network", "adult swim", "tartakovsky", "hillenburg")
STYLE_CANDIDATES = ["bfl:flux-3-image-klein:1k", "fal:seedream-4.5-t2i:2K_wide"]
NO_TEXT = ", no text, no letters, no logo"

DEFAULT_CANDIDATES = ["bfl:flux-3-image-klein:1k", "fal:seedream-4.5:2K_wide", "fal:qwen-image-edit-2511:1K_wide"]
EDIT_ONLY = {"qwen-image-edit-2511"}
T2I_FOR = {"seedream-4.5": "seedream-4.5-t2i"}  # the model a candidate uses for a shot without a source


def blank_canvas(w: int = 1344, h: int = 768) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), (128, 128, 128)).save(b, "PNG")
    return b.getvalue()


def parse(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"{spec!r}: a candidate is provider:model:size")
    return {"provider": parts[0], "model": parts[1], "size": parts[2], "id": "_".join(parts).replace(".", "_").replace("-", "_")}


def plan(candidates: list[str] | None = None, *, takes: int = 4) -> dict:
    """Every request priced before anything is sent; the hash binds the creator's approval to exactly this plan."""
    rows = []
    for spec in candidates or DEFAULT_CANDIDATES:
        c = parse(spec)
        klass = providers.cls(c["provider"])
        shots = []
        for sid, title, prompt, kind, source in SHOTS:
            model = c["model"]
            if kind == "t2i" and model in T2I_FOR:
                model = T2I_FOR[model]
            canvas = kind == "t2i" and model in EDIT_ONLY
            usd = klass.PRICES[model][c["size"]]
            shots.append({"shot": sid, "title": title, "prompt": prompt, "kind": kind, "source": source, "model": model, "from_blank_canvas": canvas,
                          "takes": takes, "usd_each": usd, "usd": round(usd * takes, 4)})
        rows.append({**c, "service": klass.service, "shots": shots, "usd": round(sum(s["usd"] for s in shots), 4),
                     "prices_checked": klass.PRICES_CHECKED})
    p = {"schema": "pilot_plan/1", "takes": takes, "candidates": rows, "usd": round(sum(r["usd"] for r in rows), 4),
         "by_service": {}, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for r in rows:
        p["by_service"][r["service"]] = round(p["by_service"].get(r["service"], 0.0) + r["usd"], 4)
    p["hash"] = hashlib.sha256(json.dumps([p["takes"], [(r["provider"], r["model"], r["size"]) for r in rows], SHOTS], sort_keys=True).encode()).hexdigest()[:16]
    return p


def table(p: dict) -> str:
    lines = [f"{'candidate':42} {'shots x takes':>14} {'usd':>8}"]
    for r in p["candidates"]:
        lines.append(f"{r['provider'] + ':' + r['model'] + ':' + r['size']:42} {len(r['shots'])} x {r['takes'] if 'takes' in r else p['takes']:<10} {r['usd']:>8.3f}")
    lines.append(f"{'total':42} {'':>14} {p['usd']:>8.3f}   per service: " + ", ".join(f"{k} {v:.2f}" for k, v in p["by_service"].items()))
    lines.append(f"plan hash {p['hash']}; three-fold rerun margin {p['usd'] * 3:.2f}; the card's ceiling 15.00")
    return "\n".join(lines)


def style_plan(candidates: list[str] | None = None) -> dict:
    """The style step priced before sending: one picture per style per candidate; its own hash and approval."""
    rows = []
    for spec in candidates or STYLE_CANDIDATES:
        c = parse(spec)
        klass = providers.cls(c["provider"])
        usd = klass.PRICES[c["model"]][c["size"]]
        if klass.MAX_REFS.get(c["model"], 0) and c["model"] in EDIT_ONLY:
            raise ValueError(f"{c['model']} is an editor; the style step needs a text-to-image model")
        styles = [{"style": sid, "title": t, "prompt": f"{STYLE_SCENE}, {look}{NO_TEXT}"} for sid, t, look in STYLES]
        for st in styles:
            hit = [n for n in BANNED_NAMES if n in st["prompt"].lower()]
            if hit:
                raise ValueError(f"style {st['style']} names {hit}: describe the quality, never the work (no_names)")
        rows.append({**c, "service": klass.service, "usd_each": usd, "usd": round(usd * len(STYLES), 4), "styles": styles})
    p = {"schema": "pilot_style_plan/1", "candidates": rows, "usd": round(sum(r["usd"] for r in rows), 4), "by_service": {},
         "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for r in rows:
        p["by_service"][r["service"]] = round(p["by_service"].get(r["service"], 0.0) + r["usd"], 4)
    p["hash"] = hashlib.sha256(json.dumps([[(r["provider"], r["model"], r["size"]) for r in rows], STYLE_SCENE, STYLES], sort_keys=True).encode()).hexdigest()[:16]
    return p


def run_styles(p: dict, out: Path, ledger: Run, *, factory=providers.get, log=print) -> dict:
    """Paint the style step (refused without the creator's approval of its hash) and build one sheet per candidate."""
    out = Path(out)
    if not ledger.approved("styles", p["hash"]):
        raise PermissionError(f"the style plan {p['hash']} has no recorded approval on {ledger.path}")
    path = out / "styles.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": "pilot_styles/1", "plan_hash": p["hash"], "candidates": {}}
    stopped = None
    for c in p["candidates"]:
        cdir = out / "styles" / c["id"]
        cdir.mkdir(parents=True, exist_ok=True)
        prov = factory(c["provider"], root=cdir / "_raw", run=ledger)
        rec = res["candidates"].setdefault(c["id"], {"provider": c["provider"], "model": c["model"], "size": c["size"], "styles": {}})
        for st in c["styles"]:
            if rec["styles"].get(st["style"], {}).get("file"):
                continue
            try:
                r = prov.generate(f"style_{st['style']}", st["prompt"], model=c["model"], size=c["size"], seed=1)
                (cdir / f"{st['style']}.png").write_bytes(r.data)
                rec["styles"][st["style"]] = {"file": f"{st['style']}.png", "seconds": r.seconds, "seed": r.seed,
                                              "usd": r.usd_settled if r.usd_settled is not None else r.usd_estimated}
                log(f"{c['id']} {st['style']}: {r.seconds}s")
            except CapReached as exc:
                stopped = str(exc)
                break
            except AccountError as exc:
                rec["styles"][st["style"]] = {"error": "account", "detail": str(exc)[:200]}
                log(f"{c['id']}: account unusable: {str(exc)[:160]}")
                break
            except (ProviderError, ChargeUncertain) as exc:
                rec["styles"][st["style"]] = {"error": "failed", "detail": str(exc)[:200]}
            write_json_atomic(path, res)
        write_json_atomic(path, res)
        if stopped:
            break
    res["stopped"] = stopped
    write_json_atomic(path, res)
    return res


def style_sheet(out: Path, candidate_id: str, *, cell: tuple[int, int] = (480, 270)) -> Path:
    """Six looks side by side, numbered 1-6 with their names: the creator answers with a number (OR-16)."""
    from PIL import Image, ImageDraw
    out = Path(out)
    rec = json.loads((out / "styles.json").read_text(encoding="utf-8"))["candidates"][candidate_id]
    w, h = cell
    cols, label = 3, 24
    rows = (len(STYLES) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, label + (h + label) * rows), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    d.text((8, 5), f"{rec['provider']} {rec['model']} {rec['size']}: one scene, six looks", fill=(230, 230, 230))
    for i, (sid, title, _look) in enumerate(STYLES):
        x, y = (i % cols) * w, label + (i // cols) * (h + label)
        info = rec["styles"].get(sid, {})
        f = out / "styles" / candidate_id / (info.get("file") or "-")
        if info.get("file") and f.exists():
            im = Image.open(f).convert("RGB")
            im.thumbnail((w - 4, h - 4))
            sheet.paste(im, (x + 2, y + 2))
        else:
            d.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline=(90, 90, 90))
            d.text((x + 10, y + 10), (info.get("error") or "missing")[:40], fill=(220, 120, 120))
        d.text((x + 6, y + h + 4), f"{i + 1}. {title}", fill=(240, 220, 120))
    path = out / f"styles_{candidate_id}.png"
    sheet.save(path)
    return path


def run(p: dict, out: Path, ledger: Run, *, factory=providers.get, log=print, only: list[str] | None = None) -> dict:
    """Paint the plan: candidate by candidate, shot by shot, take by take (seeds 1..takes). Refuses without the creator's
    approval of this plan's hash on the ledger; stops at a cap; records every take in results.json as it goes."""
    out = Path(out)
    if not ledger.approved("pilot", p["hash"]):
        raise PermissionError(f"the pilot plan {p['hash']} has no recorded approval on {ledger.path}: `pilot run --approved-by --ref`")
    results = json.loads((out / "results.json").read_text(encoding="utf-8")) if (out / "results.json").exists() else {"schema": "pilot_results/1", "plan_hash": p["hash"], "candidates": {}, "embedding_scores": "not computed (SigLIP-2 / DINOv2 need a model download; the creator's 1-5 decides)"}
    stopped = None
    for c in p["candidates"]:
        if only and c["id"] not in only:
            continue
        cdir = out / c["id"]
        cdir.mkdir(parents=True, exist_ok=True)
        prov = factory(c["provider"], root=cdir / "_raw", run=ledger)
        rec = results["candidates"].setdefault(c["id"], {"provider": c["provider"], "model": c["model"], "size": c["size"], "takes": {}})
        rec.pop("account_error", None)
        for s in c["shots"]:
            for take in range(1, p["takes"] + 1):
                key = f"{s['shot']}_t{take}"
                if key in rec["takes"] and rec["takes"][key].get("file"):
                    continue
                refs = []
                if s["kind"] == "t2i" and s["model"] in EDIT_ONLY:
                    refs = [blank_canvas()]
                elif s["source"]:
                    src = cdir / f"{s['source']}_t1.png"
                    if not src.exists():
                        rec["takes"][key] = {"skipped": f"source {s['source']}_t1 was not painted"}
                        continue
                    refs = [src.read_bytes()]
                try:
                    if s["kind"] == "edit":
                        res = prov.edit(key, s["prompt"], model=s["model"], size=c["size"], refs=refs, seed=None if c["provider"] == "gemini" else take)
                    else:
                        res = prov.generate(key, s["prompt"], model=s["model"], size=c["size"], refs=refs, seed=None if c["provider"] == "gemini" else take)
                    (cdir / f"{key}.png").write_bytes(res.data)
                    rec["takes"][key] = {"file": f"{key}.png", "seconds": res.seconds, "seed": res.seed, "usd": res.usd_settled if res.usd_settled is not None else res.usd_estimated,
                                         "cached": res.cached, "model_version": res.model_version, "from_blank_canvas": bool(s["kind"] == "t2i" and s["model"] in EDIT_ONLY)}
                    log(f"{c['id']} {key}: {res.seconds}s ${rec['takes'][key]['usd']:.4f}{' (cached)' if res.cached else ''}")
                except CapReached as exc:
                    stopped = str(exc)
                    log("STOP:", stopped)
                    break
                except AccountError as exc:
                    rec["takes"][key] = {"error": "account", "detail": str(exc)[:200]}
                    rec["account_error"] = str(exc)[:200]
                    log(f"{c['id']}: account unusable, skipping this candidate: {str(exc)[:160]}")
                    break
                except ChargeUncertain as exc:
                    rec["takes"][key] = {"error": "charge uncertain", "detail": str(exc)[:200]}
                    log(f"{c['id']} {key}: uncertain charge, not retried")
                except ProviderError as exc:
                    rec["takes"][key] = {"error": "refused" if "Moderated" in str(exc) or "nsfw" in str(exc).lower() else "failed", "detail": str(exc)[:200]}
                    log(f"{c['id']} {key}: {rec['takes'][key]['error']}: {str(exc)[:120]}")
                write_json_atomic(out / "results.json", results)
            if stopped or rec.get("account_error"):
                break
        rec["usd"] = round(sum(t.get("usd", 0.0) for t in rec["takes"].values()), 4)
        rec["seconds"] = round(sum(t.get("seconds", 0.0) for t in rec["takes"].values()), 1)
        rec["refusals"] = sum(1 for t in rec["takes"].values() if t.get("error") == "refused")
        rec["failures"] = sum(1 for t in rec["takes"].values() if t.get("error") in ("failed", "charge uncertain", "account"))
        write_json_atomic(out / "results.json", results)
        if stopped:
            break
    results["stopped"] = stopped
    write_json_atomic(out / "results.json", results)
    return results


def collage(out: Path, candidate_id: str, *, cell: tuple[int, int] = (320, 180)) -> Path:
    """One sheet per candidate: a row per shot, a column per take, labelled; what the creator looks at (OR-16)."""
    from PIL import Image, ImageDraw
    out = Path(out)
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    rec = results["candidates"][candidate_id]
    takes = max([int(k.rsplit("_t", 1)[1]) for k in rec["takes"]] or [1])
    w, h = cell
    label = 22
    sheet = Image.new("RGB", (160 + w * takes, label + (h + label) * len(SHOTS)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), f"{rec['provider']} {rec['model']} {rec['size']}  ${rec.get('usd', 0):.2f}  {rec.get('seconds', 0)}s  refusals {rec.get('refusals', 0)}", fill=(230, 230, 230))
    for row, (sid, title, *_rest) in enumerate(SHOTS):
        y = label + row * (h + label)
        d.text((8, y + h // 2), title[:22], fill=(200, 200, 200))
        for t in range(1, takes + 1):
            x = 160 + (t - 1) * w
            info = rec["takes"].get(f"{sid}_t{t}", {})
            if info.get("file") and (out / candidate_id / info["file"]).exists():
                im = Image.open(out / candidate_id / info["file"]).convert("RGB")
                im.thumbnail((w - 4, h - 4))
                sheet.paste(im, (x + 2, y + 2))
            else:
                d.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline=(90, 90, 90))
                d.text((x + 8, y + 8), (info.get("error") or info.get("skipped") or "missing")[:30], fill=(220, 120, 120))
            d.text((x + 4, y + h + 4), f"t{t} seed {info.get('seed')} {info.get('seconds', '')}s", fill=(160, 160, 160))
    path = out / f"collage_{candidate_id}.png"
    sheet.save(path)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("styles-estimate", "styles"):
        s = sub.add_parser(name)
        if name == "styles":
            s.add_argument("--out", required=True)
            s.add_argument("--approved-by", default="")
            s.add_argument("--ref", default="")
    for name in ("estimate", "run", "collage"):
        s = sub.add_parser(name)
        s.add_argument("--takes", type=int, default=4)
        s.add_argument("--candidates", default=",".join(DEFAULT_CANDIDATES))
        if name != "estimate":
            s.add_argument("--out", required=True)
        if name == "run":
            s.add_argument("--approved-by", default="")
            s.add_argument("--ref", default="", help="where the creator said yes (message id or date and words)")
            s.add_argument("--only", default="", help="comma-separated candidate ids")
    a = ap.parse_args(argv)
    if a.cmd in ("styles-estimate", "styles"):
        sp = style_plan()
        for r in sp["candidates"]:
            print(f"{r['provider']}:{r['model']}:{r['size']:10} {len(r['styles'])} looks x ${r['usd_each']:.3f} = ${r['usd']:.3f}")
        print(f"total ${sp['usd']:.3f}, hash {sp['hash']}")
        if a.cmd == "styles-estimate":
            print("nothing is sent: `pilot styles --approved-by --ref` records the creator's yes on this hash first")
            return 0
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        write_json_atomic(out / "style_plan.json", sp)
        ledger = Run.open(out / "styles_run.json", caps={s_: round(v * 3, 2) for s_, v in sp["by_service"].items()}, styles=sp["hash"])
        if a.approved_by and a.ref:
            ledger.approve("styles", sp["hash"], by=a.approved_by, ref=a.ref, provider=",".join(sorted({c["provider"] for c in sp["candidates"]})), usd=sp["usd"])
        try:
            res = run_styles(sp, out, ledger)
        except PermissionError as exc:
            print("refused:", exc)
            return 2
        for cid in res["candidates"]:
            print(cid, "->", style_sheet(out, cid))
        return 3 if res.get("stopped") else 0
    p = plan([c for c in a.candidates.split(",") if c], takes=a.takes)
    if a.cmd == "estimate":
        print(table(p))
        print("nothing is sent: `pilot run --approved-by --ref` records the creator's yes on this hash first")
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out / "plan.json", p)
    if a.cmd == "collage":
        for c in p["candidates"]:
            print(collage(out, c["id"]))
        return 0
    ledger = Run.open(out / "run.json", caps={s: round(v * 3, 2) for s, v in p["by_service"].items()}, pilot=p["hash"])
    if a.approved_by and a.ref:
        ledger.approve("pilot", p["hash"], by=a.approved_by, ref=a.ref, provider=",".join(sorted({c["provider"] for c in p["candidates"]})), usd=p["usd"])
    print(table(p))
    try:
        res = run(p, out, ledger, only=[x for x in a.only.split(",") if x] or None)
    except PermissionError as exc:
        print("refused:", exc)
        return 2
    for cid, rec in res["candidates"].items():
        print(f"{cid}: ${rec.get('usd', 0):.3f}, {rec.get('seconds', 0)} s, refusals {rec.get('refusals', 0)}, failures {rec.get('failures', 0)} -> {collage(out, cid)}")
    print("spent:", {s: ledger.spent(s) for s in p["by_service"]}, "stopped:" if res.get("stopped") else "", res.get("stopped") or "")
    return 3 if res.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
