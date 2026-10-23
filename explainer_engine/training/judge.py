"""During and after a LoRA run: score every checkpoint and decide CONTINUE / STOP (docs/LORA_TRAINING.md LT-20..LT-45).

Pure numpy on embeddings and frames, so it is tested without a GPU; ``embed.py`` turns pictures into embeddings.
The key method (why CLIP is usable for style although it also sees content): every sample prompt keeps its seed across
checkpoints, so the change of one prompt's picture from step 0 (the base model) to step N is the LoRA's change, not a
change of content. Progress = how far that move goes toward the creator's reference pictures, 0 = base, 1 = as close as
his own pictures are to each other.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .audit import RULES, finding

SAMPLE_NAME = re.compile(r"__(\d{9})_(\d+)\.(?:jpg|jpeg|png|webp)$", re.I)


def unit(x):
    x = np.asarray(x, dtype=np.float64)
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12, None)


def parse_samples(paths):
    """ai-toolkit sample files ``<ts>__<step:09d>_<prompt>.jpg`` -> {step: {prompt_index: path}} (newest wins)."""
    out = {}
    for p in sorted(map(Path, paths)):
        m = SAMPLE_NAME.search(p.name)
        if m and ".thumbs" not in p.parts:
            out.setdefault(int(m.group(1)), {})[int(m.group(2))] = p
    return out


def ref_ceiling(refs):
    """Mean cosine of each reference picture to the others: how alike the creator's own pictures are."""
    r = unit(refs)
    if len(r) < 2:
        return 1.0
    s = r @ r.T
    return float((s.sum() - np.trace(s)) / (len(r) * (len(r) - 1)))


def step_metrics(samples, refs, *, base=None, train=None, texts=None, heldout=None, no_trigger=()):
    """samples: {prompt_index: embedding} of one checkpoint; base: the same for step 0. Returns the LT-2x numbers."""
    idx = sorted(samples)
    s = unit([samples[i] for i in idx])
    r = unit(refs)
    style = float((s @ r.T).mean())
    m = {"style": round(style, 4), "prompts": len(idx)}
    if len(idx) > 1:
        g = s @ s.T
        m["sameness"] = round(float((g.sum() - np.trace(g)) / (len(idx) * (len(idx) - 1))), 4)
    if texts is not None:
        t = unit([texts[i] for i in idx])
        m["adherence"] = round(float((s * t).sum(-1).mean()), 4)
    if train is not None and len(train):
        held = [k for k, i in enumerate(idx) if heldout is None or heldout.get(i, True)]
        if held:
            m["memorization"] = round(float((s[held] @ unit(train).T).max()), 4)
    if base is not None:
        b = unit([base[i] for i in idx if i in base])
        common = [k for k, i in enumerate(idx) if i in base]
        m["move_from_base"] = round(float(1 - (s[common] * b).sum(-1).mean()), 4) if common else None
        m["base_style"] = round(float((b @ r.T).mean()), 4) if common else None
        off = [k for k, i in enumerate(idx) if i in no_trigger and i in base]
        if off:
            bo = unit([base[idx[k]] for k in off])
            m["trigger_off_keep"] = round(float((s[off] * bo).sum(-1).mean()), 4)
    return m


def score_run(by_step, refs, *, train=None, texts=None, heldout=None, no_trigger=()):
    """{step: {prompt: emb}} -> list of metric rows sorted by step, with progress and the overfit flags (LT-20..LT-25)."""
    j = RULES["judge"]
    steps = sorted(by_step)
    if not steps:
        return []
    base = by_step[steps[0]] if steps[0] == 0 else None
    ceil = ref_ceiling(refs)
    rows = []
    for st in steps:
        m = step_metrics(by_step[st], refs, base=base, train=train, texts=texts, heldout=heldout, no_trigger=no_trigger)
        m["step"] = st
        rows.append(m)
    b = rows[0] if base is not None else None
    for m in rows:
        flags = []
        if b is not None:
            b_style = m.get("base_style") if m.get("base_style") is not None else b["style"]  # same prompts only
            m["progress"] = round((m["style"] - b_style) / max(ceil - b_style, 1e-6), 3)
            if "adherence" in m and b.get("adherence") is not None and b["adherence"] - m["adherence"] > j["adherence_drop_max"]:
                flags.append("LT-22 prompt ignored")
            if "sameness" in m and m["sameness"] > max(ceil, b.get("sameness", 0)) + j["collapse_margin"]:
                flags.append("LT-24 every prompt looks alike")  # more alike than the creator's own pictures are
        if m.get("memorization", 0) >= j["memorization_cos"] and m["step"] > 0:
            flags.append("LT-23 copies a training picture")
        if m.get("trigger_off_keep") is not None and m["trigger_off_keep"] < j["trigger_off_keep_min"]:
            m["note"] = "LT-25 LoRA acts without its trigger"
        m["flags"] = flags
        m["ceiling"] = round(ceil, 4)
    return rows


def decide(rows, total_steps):
    """LT-26..LT-28: CONTINUE, STOP_KEEP_BEST (plateau or overfit after a good checkpoint), STOP_FAIL, DONE_KEEP_BEST."""
    j = RULES["judge"]
    trained = [r for r in rows if r["step"] > 0 and "progress" in r]
    if not trained:
        return {"action": "CONTINUE", "best": None, "why": "no checkpoint after the base yet"}
    clean = [r for r in trained if not r["flags"]]
    best = max(clean, key=lambda r: r["progress"]) if clean else None
    last = trained[-1]
    pick = best["step"] if best else None
    if last["step"] >= total_steps:
        return {"action": "DONE_KEEP_BEST", "best": pick, "why": "last step reached"}
    if last["flags"] and best and best["step"] < last["step"]:
        return {"action": "STOP_KEEP_BEST", "best": pick, "why": f"step {last['step']}: {', '.join(last['flags'])}"}
    if last["flags"] and not best:
        return {"action": "STOP_FAIL", "best": None, "why": f"overfit signs before any clean gain: {last['flags']}"}
    top = best["progress"] if best else 0.0
    if last["step"] >= j["min_steps_for_fail"] and top < j["progress_fail_below"]:
        return {"action": "STOP_FAIL", "best": pick,
                "why": f"progress {top} < {j['progress_fail_below']} after {last['step']} steps: not learning the style "
                       "(check trigger, captions, LR)"}
    w = j["plateau_window"]
    if len(trained) > w:
        gain = trained[-1]["progress"] - trained[-1 - w]["progress"]
        if gain < j["plateau_gain_min"]:
            return {"action": "STOP_KEEP_BEST", "best": pick,
                    "why": f"plateau: +{gain:.3f} over the last {w} checkpoints (min {j['plateau_gain_min']})"}
    trend = "rising" if len(trained) < 2 or last["progress"] >= trained[-2]["progress"] else "falling"
    return {"action": "CONTINUE", "best": pick,
            "why": f"progress {last['progress']} ({trend}; best {top} at step {pick}), no overfit sign"}


# ---- video motion LoRA (LT-30..LT-33) ----------------------------------------------------------------------------------

def _gray_small(frames, k=4):
    f = np.asarray(frames, dtype=np.float64)
    if f.ndim == 4:
        f = f.mean(-1)
    t, h, w = f.shape
    f = f[:, : h // k * k, : w // k * k].reshape(t, h // k, k, w // k, k).mean((2, 4))
    return f / (255.0 if f.max() > 1.5 else 1.0)


def video_metrics(frames, keyframes=None):
    """dynamic = mean frame-to-frame change; jitter = second difference / dynamic (flicker, wobble); keyframe = how close
    the frames at the given indexes stay to the stills ({index: still}). A frozen clip scores low jitter AND low
    dynamic, so the two are always read together (VBench pairs smoothness with dynamic degree)."""
    g = _gray_small(frames)
    d1 = np.abs(np.diff(g, axis=0)).mean() if len(g) > 1 else 0.0
    d2 = np.abs(g[2:] - 2 * g[1:-1] + g[:-2]).mean() if len(g) > 2 else 0.0
    m = {"dynamic": round(float(d1), 5), "jitter": round(float(d2 / max(d1, 1e-6)), 4)}
    if keyframes:
        sims = []
        for i, still in keyframes.items():
            s = _gray_small(np.asarray(still)[None])[0]
            sims.append(1 - float(np.abs(g[i] - s).mean()))
        m["keyframe"] = round(float(np.mean(sims)), 4)
    return m


def compare_video(base, lora, shot=""):
    """The same shot, seed and conditions with and without the LoRA."""
    v = RULES["video"]
    f = []
    if base["dynamic"] > 0 and lora["dynamic"] < v["dynamic_keep_min"] * base["dynamic"]:
        f.append(finding("LT-31", "FAIL", f"{shot}: motion {lora['dynamic']} < {v['dynamic_keep_min']} x base "
                                          f"{base['dynamic']} (the LoRA freezes the picture)"))
    if lora["jitter"] > v["jitter_rise_max"] * base["jitter"]:
        f.append(finding("LT-32", "FAIL", f"{shot}: jitter {lora['jitter']} > {v['jitter_rise_max']} x base "
                                          f"{base['jitter']} (flicker/wobble)"))
    if "keyframe" in base and "keyframe" in lora and base["keyframe"] - lora["keyframe"] > v["keyframe_drop_max"]:
        f.append(finding("LT-33", "FAIL", f"{shot}: drifts from the given stills ({lora['keyframe']} vs base "
                                          f"{base['keyframe']})"))
    return f or [finding("LT-30", "PASS", f"{shot}: motion {lora['dynamic']} (base {base['dynamic']}), jitter "
                                          f"{lora['jitter']} (base {base['jitter']})")]


# ---- image-edit "next pose" LoRA (LT-40..LT-43) ------------------------------------------------------------------------

def _border(img, frac=0.15):
    g = _gray_small(np.asarray(img)[None], k=8)[0]
    h, w = g.shape
    bh, bw = max(1, int(h * frac)), max(1, int(w * frac))
    mask = np.ones_like(g, dtype=bool)
    mask[bh:h - bh, bw:w - bw] = False
    return g, mask


def edit_pair_metrics(control, output):
    """change = mean difference over the whole frame; drift = difference on the outer band (the set and camera; the
    characters act in the middle in our frames)."""
    gc, mask = _border(control)
    go, _ = _border(output)
    d = np.abs(gc - go)
    return {"change": round(float(d.mean()), 4), "drift": round(float(d[mask].mean()), 4)}


def judge_edit(pairs, dataset_pairs, identity=None):
    """pairs/dataset_pairs: lists of edit_pair_metrics; the training pairs give the normal amount of change and drift.
    identity: optional list of cosine(output, control) on character crops."""
    e = RULES["edit"]
    med_drift = float(np.median([p["drift"] for p in dataset_pairs]))
    med_change = float(np.median([p["change"] for p in dataset_pairs]))
    f = []
    drift = float(np.median([p["drift"] for p in pairs]))
    change = float(np.median([p["change"] for p in pairs]))
    if drift > e["background_drift_max_x"] * max(med_drift, 1e-4):
        f.append(finding("LT-41", "FAIL", f"set/camera drift {drift:.4f} > {e['background_drift_max_x']} x the training "
                                          f"pairs' {med_drift:.4f}"))
    if change < e["change_min_x"] * med_change:
        f.append(finding("LT-42", "FAIL", f"change {change:.4f} < {e['change_min_x']} x the training pairs' "
                                          f"{med_change:.4f}: the output copies the input"))
    if identity is not None and float(np.mean(identity)) < e["identity_min"]:
        f.append(finding("LT-43", "FAIL", f"character identity {np.mean(identity):.3f} < {e['identity_min']}"))
    return f or [finding("LT-40", "PASS", f"drift {drift:.4f} (train {med_drift:.4f}), change {change:.4f} "
                                          f"(train {med_change:.4f})")]


# ---- progress from the trainer's log (LT-14) ---------------------------------------------------------------------------

LOG_STEP = re.compile(r"(\d+)/(\d+) \[[^\]]*?([\d.]+)s/it")


def log_progress(text):
    """Last 'N/M [... X s/it' of an ai-toolkit / tqdm log -> (done, total, sec_per_step) or None."""
    hits = LOG_STEP.findall(text.replace("\r", "\n"))
    if not hits:
        return None
    d, t, s = hits[-1]
    return int(d), int(t), float(s)
