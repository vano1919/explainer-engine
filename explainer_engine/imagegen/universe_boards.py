"""Candidate animated universes (four, plus the creator's own reference as a fifth), one concept board each (the creator's brief of 2026-10-22, "Define the Original
Animation Universe Before Production", deliverables 2, 3 and 6): the same four environments (A a modern city street, B a Mars
outpost, C a prehistoric river camp, D a drowned alternate-future city) and the same three-character line-up are painted in
each direction, so the boards compare DIRECTIONS and nothing else. The four directions differ in shape language, line,
material, dimensional feel and palette logic, not in colour alone (brief point 6); each is described in our own words, no
show, studio, artist or character is named (look_v2 ``no_names``, RIGHTS_AND_FAIR_USE, invariant 5), and the prompts carry
none of look v2's child cues or banned look words (adult proportions, no photo-realism; UR-24).

Flow (D-50, invariant 2): ``estimate`` prices every picture before anything is sent; ``run`` is refused without the
creator's recorded approval of exactly this plan's hash on the ledger; every picture is cached by request (never bought
twice); ``board`` composes the four environments and the line-up into ONE labelled image per direction with PIL (the labels
are drawn by us, not asked of the model, which misspells). Default candidate: FLUX 3 Image Klein 1k at $0.009 a picture,
the cheapest text-to-image adapter in ``imagegen/providers``; Seedream 4.5 and Gemini are the alternatives.

    python -m explainer_engine.imagegen.universe_boards estimate [--takes 1] [--candidates bfl:flux-3-image-klein:1k,...]
    python -m explainer_engine.imagegen.universe_boards run --out jobs/universe/<date> --approved-by "ვანო" --ref <message>
    python -m explainer_engine.imagegen.universe_boards board --out jobs/universe/<date>
    python -m explainer_engine.imagegen.universe_boards prompts         # the ready-to-use prompts, for any tool
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.core.store import write_json_atomic
from explainer_engine.imagegen import providers
from explainer_engine.imagegen.providers.base import AccountError, ChargeUncertain, ProviderError

# The same scene text in every direction (only the style words change between boards). Each has named people doing
# something (PRODUCTION_RULES: stakes and heroes in every frame) so the board also shows how figures sit in the world.
ENVIRONMENTS = [
    ("A", "modern city", "a rain-wet downtown street at dusk: a corner diner with a lit sign, parked cars, apartment "
          "windows glowing, a woman in a long coat crossing with an umbrella while a man waves to her from the diner door"),
    ("B", "science fiction", "a research outpost on Mars at sunrise: red dunes, three domed habitats joined by tubes, a six-wheeled "
          "rover, two figures in suits walking toward the camera, one pointing at a dust storm on the horizon"),
    ("C", "prehistoric", "a prehistoric river valley camp at dawn: hide tents, a smoking fire, birch and pine, a hunter in furs "
          "standing on a rock pointing at a line of mammoths on the far ridge while two others look up from the fire"),
    ("D", "alternate future", "a drowned city years after the flood: towers standing waist-deep in a calm sea, rope bridges and "
          "market boats between them, an old man and a girl fishing from a tenth-floor window as the sun sets"),
]
LINEUP = ("a character line-up on a plain neutral background, full body, all three the same height scale, standing on one "
          "ground line: a modern city woman in a long coat with an umbrella; a prehistoric hunter in furs with a spear; an "
          "astronaut in a worn orange suit holding the helmet; each shown twice side by side, once calm and once alarmed, "
          "adult proportions, the same drawing hand for all six figures")
NO_TEXT = ", no text, no letters, no logo, no watermark"

# id, name, one-line idea, the universe core (shape language, figure, line, material, light, composition, palette logic), and
# how its production works (the feasibility notes the board is judged with; brief point 7).
DIRECTIONS = [
    {
        "id": "paper_stage",
        "name": "Paper Stage",
        "idea": "a layered cut-paper theatre: every scene is a stack of flat cut shapes with real depth between the layers",
        "core": ("flat cut-paper illustration, every object a hard-edged cut shape with no ink outline, visible paper grain, "
                 "soft drop shadows between the layers that give real depth, adult figures of simple geometric cut shapes with "
                 "hinged limbs, faces made of a few cut pieces (brows, eyes, one mouth shape) that read from far away, "
                 "one key light per scene, strong readable silhouettes, each scene a limited palette of five colours with one "
                 "accent, saturated and harmonious, wide theatrical staging with foreground, middle and far layers"),
        "production": {
            "characters": "the easiest to rig: a figure is 10-14 cut pieces on hinges; a turn is a swap to a side or back piece",
            "expressions": "6-8 brow + mouth combinations cover most scenes; emotion lives in posture and the light",
            "environments": "the strongest reuse: layers are assets by construction (a tree layer, a wall layer, a sky layer); "
                            "recolour by palette swap",
            "dimension": "2D cut-outs on a 2.5D stage; the depth-map parallax of PR #18 becomes true layer parallax",
            "camera": "pans, pushes and layer parallax are native; a true orbit is not (flat pieces)",
            "closeups": "weakest point: a cut face in close-up is bold but coarse; close-ups must be designed as their own pieces",
            "settings": "stretches well: paper reads as one material in every era; the risk is that everything feels gentle",
            "fragile": "a model that paints paper grain inconsistently; drop-shadow direction drifting between pictures",
            "fit": "closest to the current pipeline: PNG layers + PIL compositing + the parallax module; no new runtime",
        },
    },
    {
        "id": "ink_cel",
        "name": "Ink and Cel",
        "idea": "a classic television cel look: one bold ink line, flat colour with one shadow tone, painted skies",
        "core": ("bold hand-drawn animation illustration, one uniform thick dark ink outline around every figure and prop, flat "
                 "cel colours with exactly one darker shadow tone and one highlight, adult proportions of about six and a half "
                 "heads with slightly exaggerated hands, jaws and shoulders, clear readable silhouettes, backgrounds painted in a "
                 "looser softer line than the figures with gentle gradient skies, one key light per scene with cast shadows, "
                 "eye-level cinematic framing, warm saturated palette with cooler shadows"),
        "production": {
            "characters": "a standard cut-out rig: head, torso, upper and lower arms, hands, legs, feet; 3 angles (front, three-quarter, side)",
            "expressions": "8-10 faces per angle plus 6 mouth shapes; a line-and-flat face redraws cheaply",
            "environments": "good reuse of props and buildings as line-and-flat pieces; painted skies are a shared layer",
            "dimension": "pure 2D with painted depth; parallax works on separated layers",
            "camera": "angles come from the 3 drawn views; a figure walking toward the camera needs its own cycle",
            "closeups": "excellent: the line carries a face at any size",
            "settings": "proven across eras on television for decades; the line unifies very different places",
            "fragile": "line weight is the thing image models drift on most; every asset needs the same reference set or a LoRA",
            "fit": "closest to look v2 (ink-shadowed silhouettes, adult proportions); the era codex applies unchanged",
        },
    },
    {
        "id": "soft_volume",
        "name": "Soft Volume",
        "idea": "rounded sculpted volumes with painted soft shading and no outlines, the feel of a big-screen feature in 2D",
        "core": ("rounded sculpted illustration with no outlines, every form a soft volume shaded by one warm key light and a "
                 "cool fill, matte painted surfaces, adult figures with exaggerated but believable body shapes: broad or narrow "
                 "frames, big expressive hands, strong noses and jaws, faces shaded like clay, environments built of chunky "
                 "simplified volumes with soft atmospheric haze between planes, rich saturated colour with complementary "
                 "shadows, cinematic depth of field in wide shots"),
        "production": {
            "characters": "the hardest: shading is baked into the sprite, so every pose and angle is a new painted piece or a 3D model",
            "expressions": "10-12 faces per angle; a shaded face does not swap mouths cleanly without a matching light",
            "environments": "volumes recolour well, but relighting a baked volume needs a repaint; fewer shared pieces",
            "dimension": "looks 3D; produced honestly it is either many 2D sprites or real 3D (out of scope today)",
            "camera": "wide and medium shots are superb; new angles are the expensive part",
            "closeups": "very attractive; consistent only with a strong identity lock (LoRA or many references)",
            "settings": "stretches well visually; the cost is the same in every era",
            "fragile": "most paid pictures per minute; the most sensitive to model drift; the slowest to automate",
            "fit": "needs the stage E identity work (LoRA) before anything moves; the parallax module helps the wide shots only",
        },
    },
    {
        "id": "poster_graphic",
        "name": "Poster Graphic",
        "idea": "angular graphic design: hard-edged shapes, two or three colours and an accent, silhouettes and negative space",
        "core": ("angular graphic poster illustration, hard-edged geometric shapes, no outlines, a limited palette of two or "
                 "three colours plus one hot accent per scene, bold silhouettes and large areas of negative space, subtle grain and "
                 "halftone texture, adult figures with long limbs and sharp simplified faces drawn with a few shapes and strong "
                 "brows, a single dramatic key light with deep flat shadows, widescreen cinematic composition with a strong "
                 "horizon and layered depth"),
        "production": {
            "characters": "simple to rig: a silhouette of 8-12 flat shapes; turns are shape swaps",
            "expressions": "6-8 brow and mouth shapes; faces are deliberately few shapes, so the set stays small",
            "environments": "excellent reuse: shapes recolour to the scene palette; a wall is a wall in every era",
            "dimension": "2D graphic; layer parallax reads well because depth is already drawn as flat planes",
            "camera": "wide shots are the style's home; medium shots work; low and high angles are cheap to draw",
            "closeups": "striking but cool: warmth and comedy need care in the brows and timing",
            "settings": "serious, adventure and science fiction come naturally; broad comedy is the stretch",
            "fragile": "the restrained palette fights an image model's habit of adding colour; prompts must name the palette",
            "fit": "fits the palette rule (colours only from palette.json) and the drawn text objects of the bible best",
        },
    },
    {
        "id": "wild_ink",
        "name": "Wild Ink",
        "idea": "the creator's reference picture (2026-10-22 14:15), its qualities only: a loose uneven ink line, bulging eyes, painterly worlds",
        "core": ("loose hand-inked cartoon illustration, a thick, uneven, energetic dark ink outline that varies in weight, big round "
                 "bulging white eyes with small dark pupils, rubbery expressive mouths with visible teeth and tongue, adult "
                 "characters with lanky or stocky exaggerated bodies, scraggly hair drawn in quick strokes, backgrounds painted "
                 "loosely with visible brush texture and watercolour bleeding, saturated colours with glowing neon accents for "
                 "anything strange or magical, one key light per scene, comedic but able to turn tense"),
        "production": {
            "characters": "a standard cut-out rig, like Ink and Cel; the uneven line hides small seams between pieces",
            "expressions": "10-12 faces (the bulging eyes do most of the acting) + 6 mouths; big mouths need teeth/tongue variants",
            "environments": "painterly plates are rich but each is a painting; props reuse well, plates less (texture shows repeats)",
            "dimension": "2D cut-outs over painted plates; layer parallax works on separated plates",
            "camera": "angles from 3 drawn views; strong in medium shots and reactions",
            "closeups": "excellent and funny: the face is the show",
            "settings": "very flexible for weird and sci-fi; serious history needs the comedy dialled down in the faces",
            "fragile": "the line weight and the eye style drift between generations; the look sits close to famous adult cartoons, "
                       "so every design must stay original (no borrowed motifs, no recognisable characters)",
            "fit": "same production path as Ink and Cel; the creator's reference picture is used for its qualities only, never as an input image",
        },
    },
]
# look v2's guards are reused as a plain word list test (the resolver checks real prompts; the boards are a candidate set)
BANNED_NAMES = ("madagascar", "rick", "morty", "samurai jack", "spongebob", "shrek", "dreamworks", "nickelodeon", "cartoon network",
                "adult swim", "pixar", "disney", "ghibli", "tartakovsky", "hillenburg")
DEFAULT_CANDIDATES = ["bfl:flux-3-image-klein:1k"]
ALT_CANDIDATES = {"seedream": "fal:seedream-4.5-t2i:2K_wide", "gemini": "gemini:gemini-3.1-flash-image:1K",
                  "nano21": "gemini:gemini-nano-banana-2.1:2K"}


GRID = ("one image divided into a 2 x 2 grid of four panels with thin white gutters, the same art style and the same drawing hand "
        "in all four panels: top-left panel, {A}; top-right panel, {B}; bottom-left panel, {C}; bottom-right panel, {D}")


def grid_prompt(direction: dict) -> dict:
    """ONE picture with the four places A-D as panels (the creator, 2026-10-22 14:15: one reference picture per world with
    four places): one generation keeps the four panels in one hand, and costs one picture."""
    scenes = {slot: scene for slot, _t, scene in ENVIRONMENTS}
    return {"slot": "G", "title": "four places in one picture", "prompt": f"{GRID.format(**scenes)}; {direction['core']}{NO_TEXT}"}


def prompts(direction: dict, mode: str = "tiles") -> list[dict]:
    if mode == "grid":
        return [grid_prompt(direction)]
    """The five pictures of one board: A-D environments and the line-up, each prompt = scene + the direction's core."""
    rows = [{"slot": slot, "title": title, "prompt": f"{scene}; {direction['core']}{NO_TEXT}"} for slot, title, scene in ENVIRONMENTS]
    rows.append({"slot": "L", "title": "character line-up", "prompt": f"{LINEUP}; {direction['core']}{NO_TEXT}"})
    return rows


def lint(text: str, look: dict | None = None) -> list[str]:
    """Words a board prompt may not carry: other works' names, look v2's child cues and banned look words."""
    from explainer_engine.world import resolver as R
    look = look or R.load_look()
    low = text.lower()
    bad = [n for n in BANNED_NAMES if n in low]
    bad += R.words_in(text, look["child_cues"]) + R.words_in(text, look["banned_words"])
    return bad


def parse(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"{spec!r}: a candidate is provider:model:size")
    return {"provider": parts[0], "model": parts[1], "size": parts[2], "id": "_".join(parts).replace(".", "_").replace("-", "_")}


def plan(candidates: list[str] | None = None, *, takes: int = 1, mode: str = "tiles", directions: list[str] | None = None) -> dict:
    """Every picture priced before anything is sent; the hash binds the creator's approval to exactly this plan."""
    rows = []
    for spec in candidates or DEFAULT_CANDIDATES:
        c = parse(spec)
        klass = providers.cls(c["provider"])
        usd = klass.PRICES[c["model"]][c["size"]]
        boards = []
        for d in _dirs(directions):
            pics = prompts(d, mode)
            for p in pics:
                bad = lint(p["prompt"])
                if bad:
                    raise ValueError(f"{d['id']} {p['slot']}: {bad} in the prompt (no_names / UR-24)")
            boards.append({"direction": d["id"], "name": d["name"], "pictures": pics, "usd": round(usd * len(pics) * takes, 4)})
        rows.append({**c, "service": klass.service, "usd_each": usd, "takes": takes, "boards": boards,
                     "usd": round(sum(b["usd"] for b in boards), 4), "prices_checked": klass.PRICES_CHECKED})
    p = {"schema": "universe_boards_plan/1", "takes": takes, "mode": mode, "candidates": rows, "usd": round(sum(r["usd"] for r in rows), 4),
         "by_service": {}, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    for r in rows:
        p["by_service"][r["service"]] = round(p["by_service"].get(r["service"], 0.0) + r["usd"], 4)
    p["hash"] = hashlib.sha256(json.dumps([takes, [(r["provider"], r["model"], r["size"]) for r in rows],
                                           [[q["prompt"] for q in prompts(d, mode)] for d in _dirs(directions)]], sort_keys=True).encode()).hexdigest()[:16]
    return p


def _dirs(ids: list[str] | None) -> list[dict]:
    if not ids:
        return DIRECTIONS
    known = {d["id"]: d for d in DIRECTIONS}
    bad = [i for i in ids if i not in known]
    if bad:
        raise ValueError(f"unknown direction(s) {bad}; known: {sorted(known)}")
    return [known[i] for i in ids]


def table(p: dict) -> str:
    n = sum(len(b["pictures"]) for b in p["candidates"][0]["boards"]) if p["candidates"] else 0
    lines = [f"{'candidate':42} {'pictures':>9} {'usd each':>9} {'usd':>8}"]
    for r in p["candidates"]:
        lines.append(f"{r['provider'] + ':' + r['model'] + ':' + r['size']:42} {n * r['takes']:>9} {r['usd_each']:>9.4f} {r['usd']:>8.3f}")
    lines.append(f"{'total':42} {'':>9} {'':>9} {p['usd']:>8.3f}   per service: " + ", ".join(f"{k} {v:.2f}" for k, v in p["by_service"].items()))
    lines.append(f"plan hash {p['hash']}; {len(p['candidates'][0]['boards'])} boards, {p.get('mode', 'tiles')} mode, {p['takes']} take(s); "
                 f"three-fold rerun margin {p['usd'] * 3:.2f}")
    return "\n".join(lines)


def run(p: dict, out: Path, ledger: Run, *, factory=providers.get, log=print, only: list[str] | None = None) -> dict:
    """Paint the plan, candidate by candidate, board by board (seeds 1..takes; Gemini takes none). Refused without the
    creator's approval of this plan's hash; stops at a cap; an account error stops that candidate after one call."""
    out = Path(out)
    if not ledger.approved("boards", p["hash"]):
        raise PermissionError(f"the boards plan {p['hash']} has no recorded approval on {ledger.path}: `universe_boards run --approved-by --ref`")
    path = out / "results.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": "universe_boards_results/1", "plan_hash": p["hash"], "candidates": {}}
    stopped = None
    for c in p["candidates"]:
        if only and c["id"] not in only:
            continue
        cdir = out / c["id"]
        cdir.mkdir(parents=True, exist_ok=True)
        prov = factory(c["provider"], root=cdir / "_raw", run=ledger)
        rec = res["candidates"].setdefault(c["id"], {"provider": c["provider"], "model": c["model"], "size": c["size"], "pictures": {}})
        rec.pop("account_error", None)
        for b in c["boards"]:
            for q in b["pictures"]:
                for take in range(1, c["takes"] + 1):
                    key = f"{b['direction']}_{q['slot']}_t{take}"
                    if rec["pictures"].get(key, {}).get("file"):
                        continue
                    try:
                        r = prov.generate(key, q["prompt"], model=c["model"], size=c["size"],
                                          seed=None if c["provider"] == "gemini" else take, extra={"aspect_ratio": "16:9"})
                        (cdir / f"{key}.png").write_bytes(r.data)
                        rec["pictures"][key] = {"file": f"{key}.png", "seconds": r.seconds, "seed": r.seed, "cached": r.cached,
                                                "usd": r.usd_settled if r.usd_settled is not None else r.usd_estimated}
                        log(f"{c['id']} {key}: {r.seconds}s ${rec['pictures'][key]['usd']:.4f}{' (cached)' if r.cached else ''}")
                    except CapReached as exc:
                        stopped = str(exc)
                        log("STOP:", stopped)
                        break
                    except AccountError as exc:
                        rec["pictures"][key] = {"error": "account", "detail": str(exc)[:200]}
                        rec["account_error"] = str(exc)[:200]
                        log(f"{c['id']}: account unusable, skipping this candidate: {str(exc)[:160]}")
                        break
                    except ChargeUncertain as exc:
                        rec["pictures"][key] = {"error": "charge uncertain", "detail": str(exc)[:200]}
                    except ProviderError as exc:
                        rec["pictures"][key] = {"error": "refused" if "Moderated" in str(exc) or "nsfw" in str(exc).lower() else "failed",
                                                "detail": str(exc)[:200]}
                    write_json_atomic(path, res)
                if stopped or rec.get("account_error"):
                    break
            if stopped or rec.get("account_error"):
                break
        rec["usd"] = round(sum(t.get("usd", 0.0) for t in rec["pictures"].values()), 4)
        rec["failures"] = sum(1 for t in rec["pictures"].values() if "error" in t)
        write_json_atomic(path, res)
        if stopped:
            break
    res["stopped"] = stopped
    write_json_atomic(path, res)
    return res


def board(out: Path, candidate_id: str, direction_id: str, *, take: int = 1, cell: tuple[int, int] = (640, 360)) -> Path:
    """ONE image per direction: the four environments in a labelled 2 x 2 grid and the line-up strip under them (brief
    point 6). Labels are drawn by us; a missing picture shows its reason."""
    from PIL import Image, ImageDraw
    out = Path(out)
    res = json.loads((out / "results.json").read_text(encoding="utf-8"))
    rec = res["candidates"][candidate_id]
    d = next(x for x in DIRECTIONS if x["id"] == direction_id)
    if f"{direction_id}_G_t{take}" in rec["pictures"]:
        return grid_board(out, candidate_id, d, rec, take)
    w, h = cell
    label, strip = 26, h
    sheet = Image.new("RGB", (2 * w, label * 2 + 2 * (h + label) + strip + label), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 6), f"{d['name']}: {d['idea']}", fill=(235, 235, 235))
    dr.text((10, 6 + label), f"{rec['provider']} {rec['model']} {rec['size']}, take {take}  ${rec.get('usd', 0):.2f}", fill=(160, 160, 160))

    def put(key: str, x: int, y: int, bw: int, bh: int, title: str) -> None:
        info = rec["pictures"].get(key, {})
        f = out / candidate_id / (info.get("file") or "-")
        if info.get("file") and f.exists():
            im = Image.open(f).convert("RGB")
            im.thumbnail((bw - 4, bh - 4))
            sheet.paste(im, (x + 2, y + 2))
        else:
            dr.rectangle([x + 2, y + 2, x + bw - 2, y + bh - 2], outline=(90, 90, 90))
            dr.text((x + 12, y + 12), (info.get("error") or "missing")[:40], fill=(220, 120, 120))
        dr.text((x + 8, y + bh + 5), title, fill=(240, 220, 120))

    for i, (slot, title, _scene) in enumerate(ENVIRONMENTS):
        x, y = (i % 2) * w, label * 2 + (i // 2) * (h + label)
        put(f"{direction_id}_{slot}_t{take}", x, y, w, h, f"{slot}. {title}")
    put(f"{direction_id}_L_t{take}", 0, label * 2 + 2 * (h + label), 2 * w, strip, "character line-up: calm / alarmed")
    path = out / f"board_{direction_id}_{candidate_id}_t{take}.png"
    sheet.save(path)
    return path


def grid_board(out: Path, candidate_id: str, d: dict, rec: dict, take: int, width: int = 1600) -> Path:
    """The one grid picture with a title band and the four place letters drawn at the quadrant corners."""
    from PIL import Image, ImageDraw
    info = rec["pictures"].get(f"{d['id']}_G_t{take}", {})
    f = out / candidate_id / (info.get("file") or "-")
    band = 34
    if info.get("file") and f.exists():
        im = Image.open(f).convert("RGB")
        im = im.resize((width, int(im.height * width / im.width)))
    else:
        im = Image.new("RGB", (width, width * 9 // 16), (30, 30, 30))
        ImageDraw.Draw(im).text((20, 20), (info.get("error") or "missing")[:60], fill=(220, 120, 120))
    sheet = Image.new("RGB", (im.width, im.height + band), (18, 18, 18))
    sheet.paste(im, (0, band))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 10), f"{d['name']}: {d['idea']}", fill=(235, 235, 235))
    W, H = im.size
    for (slot, title, _), (x, y) in zip(ENVIRONMENTS, ((0, 0), (W // 2, 0), (0, H // 2), (W // 2, H // 2))):
        dr.rectangle((x + 8, band + y + 8, x + 8 + 9 * (len(title) + 3), band + y + 30), fill=(18, 18, 18))
        dr.text((x + 14, band + y + 13), f"{slot}. {title}", fill=(240, 220, 120))
    path = out / f"board_{d['id']}_{candidate_id}_t{take}.png"
    sheet.save(path)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prompts")
    for name in ("estimate", "run", "board"):
        s = sub.add_parser(name)
        s.add_argument("--takes", type=int, default=1)
        s.add_argument("--mode", choices=("tiles", "grid"), default="tiles", help="grid = ONE picture with the four places")
        s.add_argument("--directions", default="", help="comma-separated direction ids (default: all)")
        s.add_argument("--candidates", default=",".join(DEFAULT_CANDIDATES),
                       help=f"provider:model:size, comma-separated; alternatives {ALT_CANDIDATES}")
        if name != "estimate":
            s.add_argument("--out", required=True)
        if name == "run":
            s.add_argument("--approved-by", default="")
            s.add_argument("--ref", default="", help="where the creator said yes (message id or date and words)")
            s.add_argument("--only", default="", help="comma-separated candidate ids")
    a = ap.parse_args(argv)
    if a.cmd == "prompts":
        for d in DIRECTIONS:
            print(f"\n## {d['name']} ({d['id']}): {d['idea']}")
            for q in prompts(d):
                print(f"\n[{q['slot']}] {q['title']}\n{q['prompt']}")
        return 0
    dirs = [x for x in a.directions.split(",") if x] or None
    p = plan([c for c in a.candidates.split(",") if c], takes=a.takes, mode=a.mode, directions=dirs)
    if a.cmd == "estimate":
        print(table(p))
        print("nothing is sent: `universe_boards run --approved-by --ref` records the creator's yes on this hash first")
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out / "plan.json", p)
    if a.cmd == "board":
        for c in p["candidates"]:
            for d in _dirs(dirs):
                for t in range(1, c["takes"] + 1):
                    print(board(out, c["id"], d["id"], take=t))
        return 0
    ledger = Run.open(out / "run.json", caps={s: round(v * 3, 2) for s, v in p["by_service"].items()}, boards=p["hash"])
    if a.approved_by and a.ref:
        ledger.approve("boards", p["hash"], by=a.approved_by, ref=a.ref, provider=",".join(sorted({c["provider"] for c in p["candidates"]})), usd=p["usd"])
    print(table(p))
    try:
        res = run(p, out, ledger, only=[x for x in a.only.split(",") if x] or None)
    except PermissionError as exc:
        print("refused:", exc)
        return 2
    for cid, rec in res["candidates"].items():
        print(f"{cid}: ${rec.get('usd', 0):.3f}, failures {rec.get('failures', 0)}")
        for d in _dirs(dirs):
            for t in range(1, p["takes"] + 1):
                print("  ", board(out, cid, d["id"], take=t))
    print("spent:", {s: ledger.spent(s) for s in p["by_service"]}, "stopped:" if res.get("stopped") else "", res.get("stopped") or "")
    return 3 if res.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
