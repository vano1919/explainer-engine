"""Before a LoRA pod starts: the dataset audit and the config check (docs/LORA_TRAINING.md LT-01..LT-15). Free, local.

Every finding is ``{"rule": "LT-xx", "status": "FAIL"|"WARN"|"INFO", "msg": ...}``; any FAIL means no pod. The numbers come
from ``lora_rules.json``. Images need Pillow; video clips are read from a manifest (``frames``, ``width``, ``height``,
``caption``) that the run operator writes with ffprobe on the pod or locally.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

RULES = json.loads((Path(__file__).with_name("lora_rules.json")).read_text(encoding="utf-8"))
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
STOP = {"a", "an", "the", "and", "with", "of", "in", "on", "at", "to", "by", "for", "from", "his", "her", "their", "its",
        "is", "are", "behind", "below", "above", "near", "into", "other", "two", "three", "four", "five", "style"}


def finding(rule, status, msg):
    return {"rule": rule, "status": status, "msg": msg}


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def strip_trigger(caption, trigger):
    c = caption.strip()
    return c[len(trigger):].lstrip(" ,.:;") if trigger and c.lower().startswith(trigger.lower()) else c


def dhash(path):
    from PIL import Image
    with Image.open(path) as im:
        g = im.convert("L").resize((9, 8))
        px = [int(v) for v in g.tobytes()]
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (px[r * 9 + c] > px[r * 9 + c + 1])
    return bits


def image_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def scan(folder):
    """Images of a folder (not recursive) with their caption text ('' when the .txt is missing)."""
    out = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() in IMAGE_EXT:
            txt = p.with_suffix(".txt")
            out.append({"path": p, "caption": txt.read_text(encoding="utf-8").strip() if txt.exists() else None,
                        "folder": Path(folder).name})
    return out


# ---- captions (shared by all three kinds) ----------------------------------------------------------------------------

def caption_findings(items, trigger, *, need_trigger=True):
    d = RULES["dataset"]
    f = []
    missing = [i["path"].name for i in items if i["caption"] is None]
    if missing:
        f.append(finding("LT-01", "FAIL", f"{len(missing)} items without a caption file: {missing[:5]}"))
    caps = [i for i in items if i["caption"] is not None]
    if need_trigger and trigger:
        no_trig = [i["path"].name for i in caps if not i["caption"].lower().startswith(trigger.lower())]
        if no_trig:
            f.append(finding("LT-01", "FAIL", f"{len(no_trig)} captions do not start with '{trigger}': {no_trig[:5]}"))
    lens = [(len(words(strip_trigger(i["caption"], trigger))), i["path"].name) for i in caps]
    short = [n for k, n in lens if k < d["caption_words_min"]]
    long_ = [n for k, n in lens if k > d["caption_words_max"]]
    if short:
        f.append(finding("LT-03", "WARN", f"{len(short)} captions under {d['caption_words_min']} words: {short[:5]}"))
    if long_:
        f.append(finding("LT-03", "WARN", f"{len(long_)} captions over {d['caption_words_max']} words: {long_[:5]}"))
    f += shared_phrase_findings([strip_trigger(i["caption"], trigger) for i in caps])
    return f


def shared_phrases(captions, n=None):
    """Phrases of n words found in many captions: share of captions -> phrase (v2 lesson: a phrase in every caption takes
    the style the trigger was meant to carry)."""
    n = n or RULES["dataset"]["shared_ngram_words"]
    seen = Counter()
    for c in captions:
        w = words(c)
        grams = {" ".join(w[k:k + n]) for k in range(len(w) - n + 1)}
        grams = {g for g in grams if sum(t not in STOP for t in g.split()) >= 2}
        seen.update(grams)
    total = max(len(captions), 1)
    return sorted(((cnt / total, g) for g, cnt in seen.items() if cnt > 1), reverse=True)


def shared_phrase_findings(captions):
    d = RULES["dataset"]
    f = []
    for share, g in shared_phrases(captions)[:20]:
        if share >= d["shared_ngram_fail_share"]:
            f.append(finding("LT-02", "FAIL", f"'{g}' is in {share:.0%} of captions: the style binds to it, not the trigger"))
        elif share >= d["shared_ngram_warn_share"]:
            f.append(finding("LT-02", "WARN", f"'{g}' is in {share:.0%} of captions: it will appear unasked (or binds to them)"))
    seen = Counter()
    for c in captions:
        seen.update(set(words(c)) - STOP)
    total = max(len(captions), 1)
    hot = [(w, k / total) for w, k in seen.most_common(10) if k / total >= d["word_warn_share"]]
    if hot:
        f.append(finding("LT-02", "WARN", "words in many captions (they may appear unasked): "
                                          + ", ".join(f"{w} {s:.0%}" for w, s in hot)))
    return f


def duplicate_findings(items):
    d = RULES["dataset"]
    f = []
    by_hash = {}
    for i in items:
        by_hash.setdefault(hashlib.sha1(i["path"].read_bytes()).hexdigest(), []).append(i["path"].name)
    same = [v for v in by_hash.values() if len(v) > 1]
    if same:
        f.append(finding("LT-04", "FAIL", f"{len(same)} byte-identical groups (use repeats, not copies): {same[:3]}"))
    hashes = [(dhash(i["path"]), i["path"].name) for i in items]
    near = []
    for a in range(len(hashes)):
        for b in range(a + 1, len(hashes)):
            if bin(hashes[a][0] ^ hashes[b][0]).count("1") <= d["near_duplicate_hamming"]:
                near.append((hashes[a][1], hashes[b][1]))
    if near:
        f.append(finding("LT-04", "WARN", f"{len(near)} near-duplicate pairs (check they are meant, e.g. crops): {near[:4]}"))
    caps = Counter(i["caption"] for i in items if i["caption"])
    twins = [c[:60] for c, k in caps.items() if k > 1]
    if twins:
        f.append(finding("LT-04", "WARN", f"{len(twins)} captions used for several images (a crop should say 'close-up'): "
                                          f"{twins[:2]}"))
    return f


def size_findings(items):
    d = RULES["dataset"]
    f = []
    small, tiny = [], []
    for i in items:
        s = min(image_size(i["path"]))
        if s < d["short_side_fail_px"]:
            tiny.append(f"{i['path'].name} ({s}px)")
        elif s < d["short_side_warn_px"]:
            small.append(f"{i['path'].name} ({s}px)")
    if tiny:
        f.append(finding("LT-05", "FAIL", f"{len(tiny)} images under {d['short_side_fail_px']}px: {tiny[:5]}"))
    if small:
        f.append(finding("LT-05", "WARN", f"{len(small)} images under {d['short_side_warn_px']}px (upscaled in training): "
                                          f"{small[:5]}"))
    return f


def weighted_share(items, repeats, creator_folders):
    """Share of training exposures (images x repeats of their folder) that come from the creator's own folders."""
    tot = mine = 0.0
    for i in items:
        r = float(repeats.get(i["folder"], 1))
        tot += r
        mine += r if i["folder"] in creator_folders else 0.0
    return mine / tot if tot else 0.0


def audit_style(folders, *, repeats=None, creator_folders=("his",), trigger=None):
    """LT-01..LT-07 for a photo style dataset (one or more ai-toolkit folders)."""
    trigger = RULES["dataset"]["trigger"] if trigger is None else trigger
    items = [i for fo in folders for i in scan(fo)]
    f = caption_findings(items, trigger) + duplicate_findings(items) + size_findings(items)
    lo, hi = RULES["dataset"]["size"]["style"]
    if not lo <= len(items) <= hi:
        f.append(finding("LT-07", "WARN", f"{len(items)} images; a style LoRA wants {lo}-{hi} good ones"))
    share = weighted_share(items, repeats or {}, set(creator_folders))
    stat = "FAIL" if share < RULES["dataset"]["creator_share_min"] else "INFO"
    f.append(finding("LT-06", stat, f"creator's own pictures = {share:.0%} of training exposures "
                                     f"(min {RULES['dataset']['creator_share_min']:.0%})"))
    per = Counter(i["folder"] for i in items)
    return {"kind": "style", "items": len(items), "per_folder": dict(per), "creator_share": round(share, 3),
            "findings": f}


def audit_edit(target_dir, control_dirs, *, trigger=None):
    """LT-08 + captions for an image-edit pair dataset: targets/0001.png must have control_k/0001.png in every control."""
    trigger = "" if trigger is None else trigger
    items = scan(target_dir)
    f = caption_findings(items, trigger, need_trigger=bool(trigger))
    for cd in control_dirs:
        have = {p.stem for p in Path(cd).iterdir() if p.suffix.lower() in IMAGE_EXT}
        miss = [i["path"].name for i in items if i["path"].stem not in have]
        extra = sorted(have - {i["path"].stem for i in items})
        if miss:
            f.append(finding("LT-08", "FAIL", f"{len(miss)} targets without a control in {Path(cd).name}: {miss[:5]}"))
        if extra:
            f.append(finding("LT-08", "WARN", f"{len(extra)} controls in {Path(cd).name} without a target: {extra[:5]}"))
    lo, hi = RULES["dataset"]["size"]["edit"]
    if not lo <= len(items) <= hi:
        f.append(finding("LT-07", "WARN", f"{len(items)} pairs; an edit LoRA wants {lo}+ (guides: 60-200)"))
    return {"kind": "edit", "items": len(items), "findings": f}


def audit_video(manifest, *, trigger=None):
    """LT-07 + captions for a video clip manifest: [{path, frames, width, height, caption}]. LTX needs (F-1)%8==0 and
    width/height multiples of 32; motion captions must not name characters (the motion LoRA learns movement only)."""
    d = RULES["dataset"]
    clips = json.loads(Path(manifest).read_text(encoding="utf-8")) if not isinstance(manifest, list) else manifest
    items = [{"path": Path(c["path"]), "caption": c.get("caption"), "folder": ""} for c in clips]
    f = caption_findings(items, trigger or "", need_trigger=bool(trigger))
    bad_f = [c["path"] for c in clips if (int(c["frames"]) - 1) % d["video_frames_mod"]]
    bad_d = [c["path"] for c in clips if int(c["width"]) % d["video_dims_mod"] or int(c["height"]) % d["video_dims_mod"]]
    if bad_f:
        f.append(finding("LT-07", "FAIL", f"{len(bad_f)} clips with frames-1 not a multiple of {d['video_frames_mod']}: "
                                          f"{bad_f[:4]}"))
    if bad_d:
        f.append(finding("LT-07", "FAIL", f"{len(bad_d)} clips whose size is not a multiple of {d['video_dims_mod']}: "
                                          f"{bad_d[:4]}"))
    lo, hi = d["size"]["video"]
    if not lo <= len(clips) <= hi:
        f.append(finding("LT-07", "WARN", f"{len(clips)} clips; a motion LoRA wants {lo}-{hi} short coherent clips"))
    return {"kind": "video", "items": len(clips), "findings": f}


# ---- config ------------------------------------------------------------------------------------------------------------

def _aitk_process(cfg):
    return (cfg.get("config", {}).get("process") or [{}])[0]


def config_view(cfg):
    """The few numbers the check needs, from an ai-toolkit YAML or an ltx-trainer YAML."""
    if "config" in cfg:  # ai-toolkit
        p = _aitk_process(cfg)
        tr, net, save, smp = p.get("train", {}), p.get("network", {}), p.get("save", {}), p.get("sample", {})
        prompts = [s.get("prompt", "") for s in smp.get("samples", [])] or list(smp.get("prompts", []))
        ds = p.get("datasets", [])
        return {"trainer": "ai-toolkit", "rank": net.get("linear"), "alpha": net.get("linear_alpha"), "lr": tr.get("lr"),
                "steps": tr.get("steps"), "save_every": save.get("save_every"),
                "keep": save.get("max_step_saves_to_keep"), "sample_every": smp.get("sample_every"),
                "sample_steps": smp.get("sample_steps"), "prompts": prompts, "seed": smp.get("seed"),
                "trigger": p.get("trigger_word"), "cache_te": bool(tr.get("cache_text_embeddings")),
                "caption_dropout": max([float(x.get("caption_dropout_rate", 0) or 0) for x in ds] or [0]),
                "repeats": {Path(x.get("folder_path", "")).name: x.get("num_repeats", 1) for x in ds},
                "model": p.get("model", {}).get("name_or_path"), "size": (smp.get("width"), smp.get("height"))}
    lora, opt, ck, val = cfg.get("lora", {}), cfg.get("optimization", {}), cfg.get("checkpoints", {}), cfg.get("validation", {})
    return {"trainer": "ltx-trainer", "rank": lora.get("rank"), "alpha": lora.get("alpha"),
            "lr": opt.get("learning_rate"), "steps": opt.get("steps"), "save_every": ck.get("interval"),
            "keep": ck.get("keep_last_n"), "sample_every": val.get("interval"), "sample_steps": val.get("inference_steps"),
            "prompts": [s.get("prompt", "") for s in val.get("samples", [])], "seed": val.get("seed"),
            "trigger": None, "cache_te": False, "caption_dropout": 0.0, "repeats": {}, "model": cfg.get("model", {}),
            "size": tuple(val.get("video_dims", [])[:2])}


def heldout(prompts, captions, trigger=""):
    """Per prompt: share of its content words that occur in the training captions. Low = a held-out prompt."""
    vocab = {w for c in captions for w in words(c) if w not in STOP}
    out = []
    for p in prompts:
        ws = [w for w in words(strip_trigger(p, trigger)) if w not in STOP]
        out.append(sum(w in vocab for w in ws) / len(ws) if ws else 1.0)
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def check_config(cfg, kind, *, captions=(), launch=None):
    """LT-10..LT-15. ``launch`` = {"image": ..., "boot_minutes": ...} from the launcher, when known."""
    c, v = RULES["config"], config_view(cfg)
    f = []
    lo, hi = c["rank"][kind]
    if v["rank"] is None or not lo <= v["rank"] <= hi:
        f.append(finding("LT-10", "WARN", f"rank {v['rank']} outside {lo}-{hi} (higher overfits sooner)"))
    lr = _num(v["lr"])  # PyYAML reads "1e-4" (no dot) as a string
    if lr is None or lr > c["lr_fail_above"]:
        f.append(finding("LT-10", "FAIL", f"learning rate {lr} (max {c['lr_fail_above']})"))
    elif not c["lr_warn"][0] <= lr <= c["lr_warn"][1]:
        f.append(finding("LT-10", "WARN", f"learning rate {lr} outside {c['lr_warn']}"))
    se = v["save_every"]
    if not se or se > c["save_every_max"]:
        f.append(finding("LT-11", "FAIL", f"save_every {se}: a checkpoint at least every {c['save_every_max']} steps"))
    elif v["keep"] not in (None, -1) and v["steps"] and v["keep"] * se < v["steps"]:
        f.append(finding("LT-11", "WARN", f"keeps only {v['keep']} checkpoints of {v['steps'] // se}: an early best is lost"))
    if v["sample_every"] and se and v["sample_every"] != se:
        f.append(finding("LT-11", "WARN", f"samples every {v['sample_every']} but saves every {se}: judge needs both"))
    pr = v["prompts"]
    if len(pr) < c["sample_prompts_min"]:
        f.append(finding("LT-12", "FAIL", f"{len(pr)} sample prompts (min {c['sample_prompts_min']})"))
    if v["seed"] is None:
        f.append(finding("LT-12", "FAIL", "no fixed sample seed: checkpoints are not comparable"))
    trig = v["trigger"] or (RULES["dataset"]["trigger"] if kind == "style" else "")
    if captions and pr:
        seen = heldout(pr, captions, trig)
        share = sum(s <= c["heldout_seen_words_max"] for s in seen) / len(seen)
        stat = "WARN" if share < c["heldout_share_min"] else "INFO"
        f.append(finding("LT-12", stat, f"held-out sample prompts {share:.0%} (seen-word share per prompt "
                                        f"{[round(s, 2) for s in seen]}; min {c['heldout_share_min']:.0%} held out)"))
    if kind == "style" and trig and pr and all(p.lower().startswith(trig.lower()) for p in pr):
        f.append(finding("LT-12", "WARN", "no sample prompt without the trigger: leakage (LoRA always on) is not visible"))
    if v["cache_te"] and v["caption_dropout"] > 0:
        f.append(finding("LT-13", "WARN", f"cache_text_embeddings with caption_dropout {v['caption_dropout']}: "
                                          "the dropout has no effect"))
    if launch and "aitoolkit" in str(launch.get("image", "")) and \
            (launch.get("boot_minutes") or 0) < c["boot_minutes_aitoolkit"]:
        f.append(finding("LT-15", "FAIL", f"boot_minutes {launch.get('boot_minutes')} for the ai-toolkit image "
                                          f"(the guard kills it before boot; min {c['boot_minutes_aitoolkit']})"))
    return {"kind": kind, "view": {k: v[k] for k in v if k != "prompts"}, "findings": f}


def project_cost(*, steps, sec_per_step, price_per_hour, n_ckpt_samples=0, n_prompts=0, sec_per_sample=0.0,
                 boot_minutes=0.0, done_steps=0, spent_usd=0.0):
    """LT-14: what the rest of a run will cost: steps left x speed + the samples of the checkpoints left + boot."""
    left = max(steps - done_steps, 0)
    sec = left * sec_per_step + n_ckpt_samples * n_prompts * sec_per_sample + boot_minutes * 60
    return {"hours_left": round(sec / 3600, 2), "usd_left": round(sec / 3600 * price_per_hour, 2),
            "usd_total": round(spent_usd + sec / 3600 * price_per_hour, 2),
            "sampling_usd": round(n_ckpt_samples * n_prompts * sec_per_sample / 3600 * price_per_hour, 2)}


def spend_findings(projection, cap_usd):
    share = projection["usd_total"] / cap_usd if cap_usd else 1.0
    if share > 1:
        return [finding("LT-14", "FAIL", f"projected ${projection['usd_total']} over the cap ${cap_usd}")]
    if share >= RULES["judge"]["spend_stop_share"]:
        return [finding("LT-14", "WARN", f"projected ${projection['usd_total']} = {share:.0%} of ${cap_usd}: stop and ask "
                                         "at 80 % (invariant 2)")]
    return [finding("LT-14", "INFO", f"projected ${projection['usd_total']} of ${cap_usd} ({share:.0%})")]


def verdict(findings):
    st = {x["status"] for x in findings}
    return "FAIL" if "FAIL" in st else "WARN" if "WARN" in st else "PASS"
