"""Expression sheets (VB-09, docs/STORY_ENGINE.md; the creator, 2026-10-19): a speaking hero's face changes about once a
second in dialogue (VB-02), so the hero is not painted again into every place. Each speaking hero gets ONE sheet of about
ten close-up expressions on a flat chroma-green background, painted once from the hero's reference picture (invariant 6:
the same face, never redrawn from scratch) and reused in every scene and every episode. During dialogue the frame is the
scene's own picture, zoomed in and blurred, with the keyed close-up of the current expression over it.

    cast.<id>.face_sheet = {"id": "einstein_faces_v1", "ref": "<the hero's reference picture>", "set": [10 expressions]}
    cast.<id>.expressions = {expression: file}    optional; a painted sheet file is otherwise <sheet id>_<expression>.png

    lint(doc, dirs)          VB-09 findings: set size and base expressions, beats inside the set, a reference, the key;
                             with painted files also BP-34 (docs/SOURCED_RULES.md): the close-up against its backdrop
    needed(doc)              the expressions the episode shows (film and Shorts beats) + neutral: only these are painted
    to_paint(doc)            paint-plan items for the needed close-ups not painted yet (``paint plan --faces``)
    saving(doc, items, usd)  what the sheet costs against a full picture for every face change (in the plan)
    composite(...)           the dialogue frame: blurred zoomed environment + keyed close-up (free, deterministic)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.production import accents as ACC
from explainer_engine.standards import sourced_rules as SR

SET_MIN, SET_TARGET, SET_MAX = 8, 10, 12
# the five basic emotions the enum has (Ekman's six without disgust) and the resting face: every sheet has them
BASE = ("neutral", "joyful", "sad", "scared", "angry", "surprised")
DEFAULT_SET = BASE + ("curious", "confused", "smug", "determined")
DESCRIBE = {  # what the painter is asked for: the face's muscles, not a mood word alone
    "neutral": "a calm resting face, mouth closed, eyes open and attentive",
    "curious": "head tilted a little, one brow raised, eyes narrowed with interest, lips slightly parted",
    "surprised": "brows high, eyes wide open, mouth open in a small round O",
    "joyful": "a broad open smile with teeth, cheeks lifted, eyes creased with laughter lines",
    "amused": "a lopsided half smile, one corner of the mouth up, eyes twinkling",
    "smug": "a closed-mouth smirk, chin up, eyelids half lowered",
    "confused": "brows knitted unevenly, one higher, mouth pulled to one side",
    "doubtful": "one brow down, lips pressed, eyes looking sideways with suspicion",
    "worried": "inner brows raised and pinched together, lips tight, a crease between the eyes",
    "scared": "eyes very wide, brows raised and drawn together, mouth stretched open, head pulled back",
    "angry": "brows pulled down hard, eyes glaring, nostrils flared, jaw clenched, teeth showing",
    "sad": "inner brows up, eyelids heavy, the corners of the mouth turned down, eyes glistening",
    "determined": "brows low and level, jaw set, lips pressed firm, a steady look ahead",
    "deadpan": "a completely flat face, eyelids half lowered, mouth a straight line",
}
KEY_LO, KEY_HI = 0.06, 0.22  # green dominance (g - max(r, b)) from where a pixel starts to key out to where it is gone
BORDER_KEYED = 0.85  # a painted close-up's frame edge must be at least this share key green (else the key leaves a halo)
# the environment behind a close-up: zoom about the face, blur (share of the height), dim. ZOOM is a fixed framing of the
# blurred backdrop behind the keyed inset, not a camera move on a still, so BP-20's scale window does not govern it (BP-20)
# BLUR 0.014 -> 0.024: the creator 2026-10-20 picked the blurred-backdrop dialogue frame "with a slightly more blurred background"
ZOOM, BLUR, DIM = 1.3, 0.024, 0.82
FACE_H, EASE_S, POP_S, POP = 0.94, 0.22, 0.16, 0.035  # close-up height (share of the frame), cross-fade in/out, swap pop
PORTRAIT_W = 2.0  # in a 9:16 Short the 16:9 close-up is at most this many frame widths wide, its middle (the hero) centred
_PALETTE = Path(__file__).resolve().parents[1] / "design" / "palette.json"


def key_rgb() -> tuple[int, int, int]:
    h = json.loads(_PALETTE.read_text(encoding="utf-8"))["tokens"]["chroma_key"]["hex"].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def key_hex() -> str:
    return "#%02X%02X%02X" % key_rgb()


def sheet_of(doc_or_cast: dict, who: str | None) -> dict | None:
    cast = doc_or_cast.get("cast", doc_or_cast)
    return (cast.get(who or "", {}) or {}).get("face_sheet")


def sheet_id(who: str, sheet: dict) -> str:
    return sheet.get("id") or f"{who}_faces"


def file_name(who: str, hero: dict, expression: str) -> str | None:
    """The close-up's file name: ``cast.<id>.expressions`` wins, else the sheet's own name for it."""
    named = (hero.get("expressions") or {}).get(expression)
    if named:
        return named
    sheet = hero.get("face_sheet")
    if sheet and expression in sheet.get("set", []):
        return f"{sheet_id(who, sheet)}_{expression}.png"
    return None


def prompt(doc: dict, who: str, expression: str) -> str:
    hero = doc["cast"][who]
    return (f"Close-up portrait of {hero['card'].strip(' .')}. Expression: {expression}: {DESCRIBE[expression]}. Head and "
            "shoulders, the face large and centred, turned a little toward the person they talk to; exactly the same face, "
            "hair, age and clothes as the reference picture. Background: one flat, even chroma-key green "
            f"({key_hex()}), no shadow or gradient on it, no scenery, no props, nothing else in the frame. "
            "Keep exactly the same painted graphic-novel style as the reference: thick dark ink outlines, textured painted "
            "colour. Adult proportions. No text, no letters, no speech bubbles.")


def _used(doc: dict) -> dict[str, list[tuple[str, str, str]]]:
    """who -> [(expression, picture id, where)] for every expression beat."""
    out: dict = {}
    for seg in doc.get("segments", []):
        pic = None
        shots = seg.get("shots", [])
        if shots:
            p = shots[0].get("picture")
            pic = p["id"] if isinstance(p, dict) else p
        for i, ln in enumerate(seg.get("lines", []), 1):
            for b in ln.get("visual_beats", []):
                who = b.get("who") or ln.get("speaker")
                if b.get("kind") == "expression" and who:
                    out.setdefault(who, []).append((b.get("expression"), pic, f"{seg['id']} line {i}"))
    return out


def needed(doc: dict) -> dict[str, set[str]]:
    """who -> the expressions this episode really shows (the film's and the Shorts' expression beats) plus ``neutral``, the
    resting face of every close-up between beats. Only these are painted (the creator 2026-10-20: "faces only as needed";
    Titans used 56 of 93 template close-ups). The rest of a sheet's ``set`` is painted by the episode that first uses it."""
    out: dict[str, set[str]] = {}
    for who, uses in _used(doc).items():
        out.setdefault(who, set()).update(e for e, _, _ in uses if e)
    shorts = doc.get("shorts")
    items = shorts if isinstance(shorts, list) else (shorts or {}).get("items", (shorts or {}).get("set", []))
    for sh in items if isinstance(items, list) else []:
        for ln in sh.get("lines", []):
            for b in ln.get("visual_beats", []):
                who = b.get("who") or ln.get("speaker")
                if b.get("kind") == "expression" and who and b.get("expression"):
                    out.setdefault(who, set()).add(b["expression"])
    for who in out:
        out[who].add("neutral")
    return out


def to_paint(doc: dict, dirs: list[Path] | None = None) -> list[dict]:
    """Paint-plan items for every close-up the episode needs (``needed``) that has no file yet (a file found in ``dirs`` is
    reused: a close-up is painted once for the channel, not once per episode)."""
    from explainer_engine.production import beats as BEATS
    style = doc.get("look", {}).get("style_refs", [])
    need = needed(doc)
    items = []
    for who, hero in doc.get("cast", {}).items():
        sheet = hero.get("face_sheet")
        if not sheet:
            continue
        for e in [e for e in sheet.get("set", []) if e in need.get(who, set())]:
            name = file_name(who, hero, e)
            if dirs is not None and BEATS.find_file(name, dirs):
                continue
            ref = sheet.get("ref")
            items.append({"id": Path(name).stem, "prompt": prompt(doc, who, e),
                          "refs": ([f"{ref}.png"] if ref else []) + [f"{r}.png" for r in style][:2],
                          "first_use": f"face sheet {sheet_id(who, sheet)}", "kind": "face", "who": who, "expression": e})
    return items


def saving(doc: dict, items: list[dict], usd_each: float) -> dict:
    """The sheet against the alternative (a full hero-in-place picture for every distinct expression in every picture)."""
    combos = {(who, e, pic) for who, uses in _used(doc).items() for e, pic, _ in uses if sheet_of(doc, who)}
    changes = sum(len(u) for who, u in _used(doc).items() if sheet_of(doc, who))
    sheet_usd = round(len(items) * usd_each, 4)
    instead = round(len(combos) * usd_each, 4)
    return {"expression_changes": changes, "close_ups": len(items), "full_pictures_instead": len(combos),
            "usd_sheet": sheet_usd, "usd_instead": instead, "usd_saved": round(instead - sheet_usd, 4),
            "note": "the sheet is reused by every later episode, which then pays nothing for faces"}


def border_keyed(im: Image.Image) -> float:
    """Share of the close-up's frame edge that keys out (1 = a clean flat green)."""
    a = np.asarray(keyed(im).getchannel("A"), dtype=np.float32) / 255
    edge = np.concatenate([a[:4].ravel(), a[-4:].ravel(), a[:, :4].ravel(), a[:, -4:].ravel()])
    return float((edge < 0.5).mean())


# --- BP-34: the keyed close-up against its backdrop (anti-sticker) ---------------------------------------------------------
_LUMA = np.array([0.2126, 0.7152, 0.0722])
_FRINGE_ALPHA = 0.98  # a pixel of the cut-out that is not fully opaque, or still green-tinted, is key fringe
_FRINGE_GREEN = 0.02


def _stats(rgb: np.ndarray) -> tuple[float, float]:
    """(mean luma, mean warmth R - B) of float RGB pixels, the measures of qa/scorecard.picture_stats."""
    if rgb.size == 0:
        return 0.0, 0.0
    return float((rgb @ _LUMA).mean()), float((rgb[..., 0] - rgb[..., 2]).mean())


def _erode(m: np.ndarray) -> np.ndarray:
    p = np.pad(m, 1, constant_values=False)
    return m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]


def halo_px(im: Image.Image, max_px: int | None = None) -> int:
    """Width in pixels of the key fringe round the cut-out: rings from its border inward that are mostly half-keyed or
    green-tinted pixels (the rim the key leaves when the painter's green bled into the hero). Stops at ``max_px`` + 1."""
    max_px = SR.T("BP-34", "halo_px_max") if max_px is None else max_px
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255
    r, g, b = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    dom = g - np.maximum(r, b)
    alpha = np.asarray(keyed(im).getchannel("A"), dtype=np.float32) / 255
    cur = alpha > 0.02
    fringe = cur & ((alpha < _FRINGE_ALPHA) | (dom > _FRINGE_GREEN))
    width = 0
    for _ in range(int(max_px) + 1):
        inner = _erode(cur)
        ring = cur & ~inner
        if not ring.any() or fringe[ring].mean() <= 0.5:
            break
        width += 1
        cur = inner
    return width


def composite_match(close_up: Path, backdrop: Path) -> dict:
    """BP-34 measures: the keyed close-up's own pixels against the picture it is composited over: the difference in mean
    luma and in warmth (R - B, as qa/scorecard.picture_stats measures pictures), and the key fringe in px."""
    im = Image.open(close_up)
    k = np.asarray(keyed(im), dtype=np.float32) / 255
    face = k[k[..., 3] > 0.5][:, :3]
    back = np.asarray(Image.open(backdrop).convert("RGB"), dtype=np.float32) / 255
    fl, fw = _stats(face)
    bl, bw = _stats(back)
    return {"d_luma": round(fl - bl, 4), "d_warm": round(fw - bw, 4), "halo_px": halo_px(im)}


def match_findings(pairs: dict[tuple[Path, Path], str]) -> list[dict]:
    """BP-34 findings for (close-up file, backdrop file) -> where it is used; files that cannot be read are skipped. The
    rule id is the registry's own (not a PV-44 VB finding)."""
    out: list[dict] = []
    sev = SR.rule("BP-34").get("severity", "REVIEW")
    lt, wt, hp = SR.T("BP-34", "luma_tolerance"), SR.T("BP-34", "warmth_tolerance"), SR.T("BP-34", "halo_px_max")

    def add(where, detail):
        out.append({"rule": "BP-34", "severity": sev, "where": where, "detail": detail})

    for (cu, bd), where in pairs.items():
        try:
            m = composite_match(cu, bd)
        except (OSError, ValueError):
            continue
        if abs(m["d_luma"]) > lt or abs(m["d_warm"]) > wt:
            add(where, f"{cu.name} over {bd.name} reads as a sticker: luma differs by {m['d_luma']:+.2f} (tolerance {lt}), "
                       f"warmth by {m['d_warm']:+.2f} (tolerance {wt}); grade the close-up to the backdrop's light and colour "
                       "temperature")
        if m["halo_px"] > hp:
            add(where, f"{cu.name}: a key halo about {m['halo_px']} px wide round the hero (at most {hp} px); repaint with a "
                       "flat key or tighten the key")
    return out


def lint(doc: dict, dirs: list[Path] | None = None) -> list[dict]:
    from explainer_engine.production import beats as BEATS
    out: list[dict] = []
    if not BEATS.has_beats(doc) and not BEATS.binding(doc):
        return out
    used = _used(doc)
    need = needed(doc)
    for who, hero in doc.get("cast", {}).items():
        sheet = hero.get("face_sheet")
        if not sheet:
            if who in used:
                BEATS._f(out, "VB-09", BEATS._sev(doc, True), f"cast.{who}", f"{who} changes expression in dialogue "
                         f"({len(used[who])} beats) but has no face_sheet: give the hero one sheet of about {SET_TARGET} "
                         "close-ups on chroma green, painted once and reused")
            continue
        where = f"cast.{who}.face_sheet"
        s = sheet.get("set", [])
        if len(set(s)) != len(s):
            BEATS._f(out, "VB-09", "FAIL", where, "an expression is listed twice")
        if not SET_MIN <= len(set(s)) <= SET_MAX:
            BEATS._f(out, "VB-09", "FAIL", where, f"{len(set(s))} expressions; a sheet has {SET_MIN}-{SET_MAX} "
                     f"(about {SET_TARGET})")
        missing = [e for e in BASE if e not in s]
        if missing:
            BEATS._f(out, "VB-09", "FAIL", where, f"missing the base expressions {', '.join(missing)} (every sheet has "
                     f"{', '.join(BASE)})")
        if not sheet.get("ref"):
            BEATS._f(out, "VB-09", "FAIL", where, "no ref: the close-ups are painted from the hero's reference picture so the "
                     "face stays the same (invariant 6)")
        for e, _, w in used.get(who, []):
            if e not in s:
                BEATS._f(out, "VB-09", "FAIL", w, f"{who} {e!r} is not in the face sheet ({', '.join(s)}): use one of them "
                         "or add it to the sheet (and paint it)")
        if dirs is not None:
            for e in [e for e in s if e in need.get(who, set())]:  # only the faces this episode shows must exist
                p = BEATS.find_file(file_name(who, hero, e), dirs)
                if p is None:
                    BEATS._f(out, "VB-09", "REVIEW", where, f"{e} is not painted yet ({file_name(who, hero, e)}): "
                             "`paint plan --faces`")
                elif border_keyed(Image.open(p)) < BORDER_KEYED:
                    BEATS._f(out, "VB-09", "REVIEW", where, f"{p.name}: the background is not a flat key green at the "
                             f"edges (under {BORDER_KEYED:.0%} keys out); repaint it or the cut-out keeps a halo")
            pairs: dict[tuple[Path, Path], str] = {}  # BP-34: each painted close-up against each picture it is used over
            for e, pic, w in used.get(who, []):
                cu = BEATS.find_file(file_name(who, hero, e), dirs)
                bd = BEATS.find_file(f"{pic}.png", dirs) if pic else None
                if cu is not None and bd is not None:
                    pairs.setdefault((cu, bd), w)
            out += match_findings(pairs)
    return out


# --- render ------------------------------------------------------------------------------------------------------------

_KEYED: dict = {}


def keyed(im: Image.Image) -> Image.Image:
    """Chroma key: green-dominant pixels become transparent with a soft edge; the green spill on the hero is removed."""
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    dom = g - np.maximum(r, b)
    alpha = 1 - np.clip((dom - KEY_LO) / (KEY_HI - KEY_LO), 0, 1)
    g2 = np.where(dom > 0, np.maximum(r, b), g)  # despill
    out = np.stack([r, g2, b, a * alpha], -1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


def close_up(path: Path) -> Image.Image:
    if path not in _KEYED:
        _KEYED.clear() if len(_KEYED) > 40 else None
        _KEYED[path] = keyed(Image.open(path))
    return _KEYED[path]


def _ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def sheet_beats(shot_beats: list[dict], cast: dict, dirs: list[Path]) -> list[dict]:
    """The shot's expression beats that have a painted close-up, with its path."""
    from explainer_engine.production import beats as BEATS
    out = []
    for b in shot_beats:
        if b["kind"] != "expression" or not b.get("who"):
            continue
        hero = cast.get(b["who"], {})
        if not hero.get("face_sheet"):
            continue
        p = BEATS.find_file(file_name(b["who"], hero, b["expression"]), dirs)
        if p is not None:
            out.append(dict(b, close_up=p))
    return out


def _side(b: dict, order: list[str]) -> float:
    """Where the close-up stands: at the hero's face point when the picture has one, else alternating sides."""
    if b.get("face") is not None:
        return min(max(b["face"][0], 0.3), 0.7)
    return 0.36 if order.index(b["who"]) % 2 == 0 else 0.64


# BP-84 (house, the creator 2026-10-16): an insert holds at least this long. A close-up is an insert into the shot, so the
# view plan never shows a close-up or a return to the scene for less (CC-03, 2026-10-20: face swaps every 1-2 s)
MIN_VIEW_S = float(SR.T("BP-84", "min_insert_s"))


def views(faces: list[dict], f0: int, f1: int, fps: int, min_s: float = MIN_VIEW_S,
          bubbles: list[dict] = ()) -> list[dict]:
    """What the frames [f0, f1) of one shot show: the scene (``who`` None) or one hero's close-up, as consecutive views.

    1. Raw views start EXPR_LEAD_FRAMES before each close-up beat (BP-32), never before the shot and never after it (a
       close-up never crosses a cut) and end with the shot's last expression.
    2. Bubbles (the shot's speech, D-62) bind the frame: while a bubble is up the view does not change, and it is the
       speaker's own close-up (when the raw plan shows him anywhere under the bubble) or the scene (both heroes on screen),
       never another hero's close-up (the creator 2026-10-20, CC-01; frame review FR-BUBBLE-FACE and FR-BUBBLE-WHO).
    3. Every view shorter than ``min_s`` (BP-84's insert floor) is absorbed: a short close-up becomes the scene; a short
       stretch of scene joins the close-up before it (or after it) when no bubble of another speaker is up in it, else the
       shorter neighbouring close-up becomes the scene too (CC-03: no face swaps every 1-2 s).
    Expression changes of one hero inside one view are not views: they swap the face, they do not cut."""
    if f1 <= f0:
        return [{"start_frame": f0, "end_frame": f1, "who": None}]
    n = f1 - f0
    lab: list = [None] * n
    fs = sorted((dict(b, start_frame=min(max(f0, b["start_frame"] - ACC.EXPR_LEAD_FRAMES), f1)) for b in faces),
                key=lambda b: b["start_frame"])
    if fs:
        end = min(f1, max(b["end_frame"] for b in faces))
        for i, b in enumerate(fs):
            a = b["start_frame"]
            z = fs[i + 1]["start_frame"] if i + 1 < len(fs) else max(a, end)
            for f in range(a, z):
                lab[f - f0] = b["who"]
    speakers: list[set] = [set() for _ in range(n)]
    for b in bubbles:
        for f in range(max(f0, b["start_frame"]), min(f1, b["end_frame"])):
            speakers[f - f0].add(b.get("who"))
    k = 0
    while k < n:  # each run of frames under bubbles (a cluster) gets one label
        if not speakers[k]:
            k += 1
            continue
        e = k
        who: set = set()
        while e < n and speakers[e]:
            who |= speakers[e]
            e += 1
        one = next(iter(who)) if len(who) == 1 else None
        keep = one if one is not None and one in lab[k:e] else None
        for f in range(k, e):
            lab[f] = keep
        k = e

    segs: list[list] = []
    for i, w in enumerate(lab):
        if segs and segs[-1][2] == w:
            segs[-1][1] = f0 + i + 1
        else:
            segs.append([f0 + i, f0 + i + 1, w])

    def merged(xs):
        out = []
        for x in xs:
            if out and out[-1][2] == x[2]:
                out[-1][1] = x[1]
            else:
                out.append(list(x))
        return out

    def allowed(seg, who) -> bool:
        said = set().union(*speakers[seg[0] - f0:seg[1] - f0]) if seg[1] > seg[0] else set()
        return not said or said == {who}

    floor = round(min_s * fps)
    for _ in range(4 * len(segs) + 4):  # each step turns a close-up into scene or removes a view: it ends
        short = [i for i, x in enumerate(segs) if x[1] - x[0] < floor]
        if len(segs) < 2 or not short:
            break
        i = short[0]
        if segs[i][2] is not None:
            segs[i][2] = None
        else:
            nb = [j for j in (i - 1, i + 1) if 0 <= j < len(segs)]
            ok = next((j for j in nb if allowed(segs[i], segs[j][2])), None)
            if ok is not None:
                segs[i][2] = segs[ok][2]
            else:
                j = min(nb, key=lambda j: segs[j][1] - segs[j][0])
                segs[j][2] = None
        segs = merged(segs)
    if len(segs) == 1 and segs[0][2] is not None and segs[0][1] - segs[0][0] < floor:
        segs[0][2] = None  # a whole shot too short for an insert stays on the scene
    return [{"start_frame": a, "end_frame": z, "who": w} for a, z, w in segs]


def view_at(vs: list[dict], f: int) -> dict | None:
    return next((v for v in vs if v["start_frame"] <= f < v["end_frame"]), None)


def face_in_view(faces: list[dict], view: dict, f: int) -> dict | None:
    """The beat whose close-up a view shows at frame ``f``: the hero's latest expression (word - lead) up to ``f``, else
    the hero's first one in the view (a view extended to the shot's start shows the expression it is about to need)."""
    mine = sorted((dict(b, start_frame=b["start_frame"] - ACC.EXPR_LEAD_FRAMES) for b in faces if b.get("who") == view["who"]),
                  key=lambda b: b["start_frame"])
    if not mine:
        return None
    cur = [b for b in mine if b["start_frame"] <= f]
    return cur[-1] if cur else next((b for b in mine if b["start_frame"] >= view["start_frame"]), mine[0])


def piece_box(b: dict, order: list[str], frame: tuple[int, int], face_size: tuple[int, int], pop: float = 0.0):
    """(x, y, w, h) of the keyed close-up on a frame of ``frame`` size: FACE_H of the height, standing on the bottom edge, at
    the hero's side (``_side``); in a 9:16 Short centred and at most PORTRAIT_W widths wide."""
    OW, OH = frame
    h = int(OH * FACE_H * (1 + pop))
    portrait = OH > OW  # a Short (QA 2026-10-19: the 16:9 close-up was pinned to the left edge, the hero fell off frame)
    if portrait:
        h = min(h, int(PORTRAIT_W * OW * face_size[1] / max(1, face_size[0]) * (1 + pop)))
    fw = max(1, int(face_size[0] * h / max(1, face_size[1])))
    x = int(OW / 2 - fw / 2) if portrait else min(max(int(_side(b, order) * OW - fw / 2), 0), max(0, OW - fw))
    return x, max(0, OH - h), fw, max(1, h)


def mouth_and_head(b: dict, order: list[str], frame: tuple[int, int]) -> tuple[tuple[float, float], tuple]:
    """Where a bubble's tail points on a close-up of hero ``b`` (the mouth, frame pixels) and the head box it must keep
    clear of, measured on the keyed silhouette (``_profile``: the head's top and centre; the painters do not centre the
    hero, QA 2026-10-20). The head is taken as 0.52 of the close-up's height from its top, the mouth at 0.82 of it."""
    face = close_up(b["close_up"])
    x, y, fw, h = piece_box(b, order, frame, face.size)
    try:
        _, y0, cx = _profile(face)
        top = y + y0 * h / max(1, round(PROFILE_W * face.height / face.width))
    except ValueError:
        cx, top = 0.5, y + 0.08 * h
    hx, hh = x + cx * fw, 0.52 * h
    mouth = (hx, top + 0.82 * hh)
    return mouth, (hx - 0.32 * hh, top, hx + 0.32 * hh, top + hh)


def composite(frame: Image.Image, faces: list[dict], f: int, fps: int, order: list[str],
              views_: list[dict] | None = None) -> Image.Image:
    """The dialogue frame at ``f``: the environment (``frame``) zoomed and blurred behind the current close-up.

    With ``views_`` (``views`` of the shot, what assemble passes): the frame shows exactly the view at ``f``; a close-up
    cuts in and out with its view (no zoom ramp of the backdrop, which read as the camera resetting, CC-06) and never
    outlives its shot. Without it (older callers): cross-fades in and out over EASE_S at the ends of the face span. Either
    way each change swaps the close-up with a small pop, landing accents.EXPR_LEAD_FRAMES before the beat's word (BP-32)."""
    if not faces:
        return frame
    if views_ is not None:
        v = view_at(views_, f)
        if v is None or v["who"] is None:
            return frame
        b = face_in_view(faces, v, f)
        if b is None:
            return frame
        return _draw_close(frame, b, f, fps, order, 1.0, pop_on=True)
    faces = [dict(b, start_frame=b["start_frame"] - ACC.EXPR_LEAD_FRAMES) for b in faces]
    s0 = min(b["start_frame"] for b in faces)
    s1 = max(b["end_frame"] for b in faces)
    ease = EASE_S * fps
    if not s0 - ease <= f < s1 + ease:
        return frame
    w = min(_ease((f - (s0 - ease)) / ease), _ease((s1 + ease - f) / ease))
    if w <= 0:
        return frame
    cur = [b for b in faces if b["start_frame"] <= f]
    b = cur[-1] if cur else faces[0]
    return _draw_close(frame, b, f, fps, order, w, pop_on=bool(cur))


def _draw_close(frame: Image.Image, b: dict, f: int, fps: int, order: list[str], w: float, pop_on: bool) -> Image.Image:
    OW, OH = frame.size
    cx = (b["face"][0] if b.get("face") is not None else 0.5) * OW
    cy = (b["face"][1] if b.get("face") is not None else 0.45) * OH
    z = 1 + (ZOOM - 1) * w
    box = (cx - cx / z, cy - cy / z, cx + (OW - cx) / z, cy + (OH - cy) / z)
    back = frame.resize((OW, OH), Image.BICUBIC, box=box).filter(ImageFilter.GaussianBlur(BLUR * OH * w))
    back = Image.eval(back, lambda v: int(v * (1 - (1 - DIM) * w)))
    face = close_up(b["close_up"])
    pop = POP * np.sin(np.pi * min(max((f - b["start_frame"]) / (POP_S * fps), 0.0), 1.0)) if pop_on else 0.0
    x, y, fw, h = piece_box(b, order, (OW, OH), face.size, pop)
    piece = face.resize((fw, h), Image.BICUBIC)
    if w < 1:
        piece.putalpha(piece.getchannel("A").point(lambda v: int(v * w)))
    out = back.convert("RGBA")
    out.alpha_composite(piece, (x, y))
    return out.convert("RGB")


# --- one framing per sheet (QA 2026-10-19: the painter framed some close-ups tighter, so a face change jumped in size) ----
PROFILE_W = 688  # the alpha silhouette is measured at this width
PROFILE_HEAD = 0.3  # share of the silhouette (from its top) compared: hat, head and neck, before the frame cuts the shoulders
SCALES = np.exp(np.linspace(np.log(0.4), np.log(2.5), 200))


def _profile(im: Image.Image) -> tuple[np.ndarray, int, float]:
    """Silhouette width per row from the top of the hero down (at PROFILE_W), the top row and the head's centre x (0..1)."""
    a = keyed(im).getchannel("A").resize((PROFILE_W, max(1, round(PROFILE_W * im.height / im.width))), Image.BILINEAR)
    m = np.asarray(a) > 127
    rows = np.where(m.sum(1) > 2)[0]
    if not len(rows):
        raise ValueError("no hero on the close-up: the whole picture keys out")
    y0 = int(rows[0])
    any_ = m.any(1)
    left = np.where(any_, m.argmax(1), 0)
    right = np.where(any_, m.shape[1] - m[:, ::-1].argmax(1), 0)
    w = (right - left).astype(float)
    head = slice(y0, y0 + max(2, int(PROFILE_HEAD * (len(w) - y0))))
    cx = float(((left[head] + right[head]) / 2).mean() / PROFILE_W)
    return w[y0:], y0, cx


def relative_scale(ref: Image.Image, cand: Image.Image) -> tuple[float, float]:
    """(s, error): resizing ``cand`` by s makes its hero the size of ``ref``'s, matched on the head silhouette."""
    wr, _, _ = _profile(ref)
    wc, _, _ = _profile(cand)
    n = max(2, int(PROFILE_HEAD * len(wr)))
    y = np.arange(n)
    best = (np.inf, 1.0)
    for s in SCALES:
        yc = y / s
        if yc[-1] >= len(wc) - 1:
            continue
        err = float(np.mean(np.abs(s * np.interp(yc, np.arange(len(wc)), wc) - wr[:n])) / max(1e-6, np.mean(wr[:n])))
        if err < best[0]:
            best = (err, float(s))
    return best[1], best[0]


def same_framing(paths: list[Path], ref: Path) -> dict[Path, Image.Image]:
    """Every close-up of one sheet re-framed like the tightest one: scaled up (never down, which would leave the body
    floating above the frame's bottom edge), the head's top and centre at the tightest one's place, key green filled in."""
    ims = {p: Image.open(p).convert("RGB") for p in paths}
    r = ims[ref]
    scale = {p: relative_scale(r, im)[0] for p, im in ims.items()}
    tight = min(paths, key=lambda p: scale[p])
    _, ty0, tcx = _profile(ims[tight])
    out = {}
    for p, im in ims.items():
        f = scale[p] / scale[tight]
        _, y0, cx = _profile(im)
        k = im.width / PROFILE_W
        big = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        ox = round(cx * im.width * f - tcx * im.width)  # where the target canvas starts inside the enlarged picture
        oy = round(y0 * k * f - ty0 * k)
        canvas = Image.new("RGB", im.size, key_rgb())
        canvas.paste(big, (-ox, -oy))
        out[p] = canvas
    return out


def plan_shots(shots: list[dict], beats: list[dict], cast: dict, fps: int) -> None:
    """Timing writes each shot's ``views`` (``views``) into the timed file, so the render, the frame review and the bubble
    check read one plan. A close-up is planned for every expression of a hero whose face sheet (or ``expressions``) names a
    file for it; a file not painted yet shows the scene at render time (a draft)."""
    for s in shots:
        close = [b for b in beats if b["kind"] == "expression" and b.get("shot") == s["id"] and b.get("who")
                 and (cast.get(b["who"]) or {}).get("face_sheet") and file_name(b["who"], cast[b["who"]], b["expression"])]
        s["views"] = views(close, s["start_frame"], s["end_frame"], fps, bubbles=s.get("bubbles") or [])
