"""The P2 visual judge, core logic (Qwen3-VL as an automatic frame judge; docs: project files explainer-engine/tests_paid_2026-11-20/P2/).

One question per defect (``deformed_hand``, ``deformed_face``, ``extra_limbs``, ``identity_mismatch``), asked of one model at a time,
temperature 0 (greedy). The answer's first token is YES or NO; the probability is the softmax of the YES and NO first-token logits, so
it is a real number from the model, not a guess it wrote. Everything is saved step by step (OR-33): after every (model, frame) a
record file is written atomically and handed to ``on_step`` (the container commits the Volume and uploads every few frames).

Pure Python plus lazy ``torch`` / ``transformers`` (only ``HFJudge`` imports them): the logic is tested on CPU with a fake judge and
rehearsed once with a tiny random Qwen3-VL (``rehearse_cpu.py``). Nothing here knows Modal.

The verdict thresholds are PLACEHOLDERS (``launch_a100.json`` ``verdict``, marked provisional): the raw probabilities are the data;
the thresholds are refitted offline, for free, on the creator's PASS/FAIL (``compare.py``). Nothing is decided by them."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

DEFECTS = ("deformed_hand", "deformed_face", "extra_limbs", "identity_mismatch")
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
SCHEMA_BATCH = "judge_batch/1"
SCHEMA_RESULT = "judge_result/1"
MAX_SIDE = 1024                     # frames are shrunk to this longest side before the model sees them (deterministic, LANCZOS)
MAX_NEW_TOKENS = 40
MIN_EXAMPLES, MAX_EXAMPLES = 3, 5   # the brief: 3-5 approved frames chosen by the creator (never invented)
ANSWER = re.compile(r"^\s*(YES|NO)\b", re.I)


class DeadlineReached(Exception):
    """The run's own clock ran out between two asks: a clean stop (the end path still saves and uploads what exists)."""


class BatchProblem(ValueError):
    pass


# --- prompts: files, hashed ------------------------------------------------------------------------------------------------

def load_prompts(prompt_dir=PROMPT_DIR) -> dict:
    """``{"system": text, "defects": {name: text}, "sha256": {file: sha}, "prompts_sha": combined}``; the hash is written into every result."""
    d = Path(prompt_dir)
    files = {"system": d / "system.txt", **{k: d / f"{k}.txt" for k in DEFECTS}}
    texts, shas = {}, {}
    for k, p in files.items():
        raw = p.read_bytes()
        texts[k] = raw.decode("utf-8").strip()
        shas[p.name] = hashlib.sha256(raw).hexdigest()
    combined = hashlib.sha256("".join(f"{n}:{shas[n]}\n" for n in sorted(shas)).encode()).hexdigest()
    return {"system": texts.pop("system"), "defects": texts, "sha256": shas, "prompts_sha": combined}


# --- the batch ---------------------------------------------------------------------------------------------------------------

def batch_problems(batch: dict, root: Path | None = None) -> list[str]:
    """What is wrong with a ``judge_batch/1``: schema, 3-5 examples, unique frames, an anchor for the identity question, files present."""
    bad = []
    if batch.get("schema") != SCHEMA_BATCH:
        bad.append(f"schema must be {SCHEMA_BATCH}")
    ex = batch.get("style_examples") or []
    if not MIN_EXAMPLES <= len(ex) <= MAX_EXAMPLES:
        bad.append(f"{len(ex)} style examples: the brief wants {MIN_EXAMPLES}-{MAX_EXAMPLES} approved frames the creator chose")
    frames = batch.get("frames") or []
    ids = [f.get("id") for f in frames]
    if not frames or len(set(ids)) != len(ids) or any(not i or not re.fullmatch(r"[A-Za-z0-9_.-]+", str(i)) for i in ids):
        bad.append("frames need unique ids of letters, digits and _.-")
    if not str(batch.get("prefix") or "").strip():
        bad.append("batch.prefix (the HF output folder) is missing")
    for f in frames:
        if not f.get("file"):
            bad.append(f"{f.get('id')}: no file")
        if "identity_mismatch" in (batch.get("defects") or DEFECTS) and not f.get("anchor"):
            bad.append(f"{f.get('id')}: no anchor picture (the identity question needs one)")
    for d in batch.get("defects") or []:
        if d not in DEFECTS:
            bad.append(f"unknown defect {d!r}")
    if root is not None:
        paths = [e.get("file") for e in ex] + [f.get("file") for f in frames] + [f.get("anchor") for f in frames if f.get("anchor")]
        bad += [f"missing file {p}" for p in paths if p and not (Path(root) / p).is_file()]
    return bad


def open_image(path, max_side: int = MAX_SIDE):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_side:
        k = max_side / max(im.size)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    return im


# --- asking ------------------------------------------------------------------------------------------------------------------

def parse_answer(text: str) -> tuple[bool | None, str]:
    """(flag, reason) from ``YES\\none sentence``; flag None when the first word is neither YES nor NO."""
    m = ANSWER.match(text or "")
    flag = None if not m else m.group(1).upper() == "YES"
    rest = (text or "")[m.end():] if m else (text or "")
    return flag, " ".join(rest.split())[:300]


def build_question(prompts: dict, defect: str, has_anchor: bool, n_examples: int) -> dict:
    """The words around the pictures of one question: ``intro`` (system text, the examples' caption), ``target`` caption, ``ask``."""
    parts = [prompts["system"]]
    if n_examples:
        parts.append(f"First come {n_examples} APPROVED example frames of the film's style: they show how a good frame looks.")
    return {"intro": "\n\n".join(parts), "examples_caption": "APPROVED style example:", "anchor_caption": "ANCHOR (the hero as he must look):",
            "target_caption": "TARGET frame to inspect:", "ask": prompts["defects"][defect], "has_anchor": has_anchor and defect == "identity_mismatch"}


def verdict(probs: dict, review_at: float, retry_at: float) -> str:
    """PASS / REVIEW / RETRY from the highest probability (placeholder thresholds, see the module doc)."""
    top = max(probs.values()) if probs else 0.0
    return "RETRY" if top >= retry_at else "REVIEW" if top >= review_at else "PASS"


def ask_frame(judge, prompts: dict, frame: dict, images: dict, defects, examples: list, th: dict) -> dict:
    """All defect questions of one frame for one model: ``{"defects": {name: {flag, probability, reason, answer}}, "verdict", "reason"}``."""
    out = {}
    for d in defects:
        use_anchor = d == "identity_mismatch"
        q = build_question(prompts, d, use_anchor and "anchor" in images, len(examples))
        text, p_yes = judge.ask(q, examples, images.get("anchor") if use_anchor else None, images["frame"])
        flag, reason = parse_answer(text)
        out[d] = {"flag": bool(p_yes >= 0.5) if flag is None else flag, "probability": round(float(p_yes), 6), "reason": reason,
                  "answer": (text or "")[:120], "unparsed": flag is None}
    probs = {d: v["probability"] for d, v in out.items()}
    v = verdict(probs, th["review_at"], th["retry_at"])
    flagged = [d for d, x in out.items() if x["probability"] >= th["review_at"]]
    return {"defects": out, "verdict": v, "reason": (", ".join(flagged) + " flagged") if flagged else "no defect above the review line"}


class HFJudge:
    """One Qwen3-VL model on one GPU (or CPU in the rehearsal): ``ask`` returns (answer text, P(YES)). Greedy decoding."""

    def __init__(self, path: str, dtype: str = "bfloat16", device: str = "cuda", model_cls: str = "AutoModelForImageTextToText",
                 experts: str | None = None):
        import torch
        import transformers
        from transformers import AutoProcessor
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(path)
        cls = getattr(transformers, model_cls)
        kw = {"dtype": getattr(torch, dtype)}
        if experts:                      # MoE only: "eager" runs on every card; "grouped_mm" needs a torch kernel the card may not have
            kw["experts_implementation"] = experts
        self.model = cls.from_pretrained(path, device_map=device if device != "cpu" else None, **kw)
        if device == "cpu":
            self.model.to("cpu")
        self.model.eval()
        self.device = device
        tok = self.processor.tokenizer
        self.yes_ids = self._ids(tok, ("YES", "Yes", "yes"))
        self.no_ids = self._ids(tok, ("NO", "No", "no"))
        if not self.yes_ids or not self.no_ids or set(self.yes_ids) & set(self.no_ids):
            raise RuntimeError("the tokenizer has no clean single-token YES / NO")

    @staticmethod
    def _ids(tok, words):
        ids = []
        for w in words:
            t = tok.encode(w, add_special_tokens=False)
            if len(t) == 1 and t[0] not in ids:
                ids.append(t[0])
        return ids

    def ask(self, q: dict, examples: list, anchor, frame):
        torch = self.torch
        content = [{"type": "text", "text": q["intro"]}]
        for im in examples:
            content += [{"type": "text", "text": q["examples_caption"]}, {"type": "image", "image": im}]
        if q["has_anchor"] and anchor is not None:
            content += [{"type": "text", "text": q["anchor_caption"]}, {"type": "image", "image": anchor}]
        content += [{"type": "text", "text": q["target_caption"]}, {"type": "image", "image": frame}, {"type": "text", "text": q["ask"]}]
        inputs = self.processor.apply_chat_template([{"role": "user", "content": content}], tokenize=True, add_generation_prompt=True,
                                                    return_dict=True, return_tensors="pt")
        inputs = inputs.to(self.model.device)
        with torch.inference_mode():
            gen = self.model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, temperature=None, top_p=None, top_k=None,
                                      output_scores=True, return_dict_in_generate=True)
        logits = gen.scores[0][0].float()
        lse = lambda ids: torch.logsumexp(logits[ids], dim=0)   # noqa: E731
        p_yes = float(torch.sigmoid(lse(self.yes_ids) - lse(self.no_ids)))
        new = gen.sequences[0, inputs["input_ids"].shape[1]:]
        return self.processor.tokenizer.decode(new, skip_special_tokens=True), p_yes


# --- the run -----------------------------------------------------------------------------------------------------------------

def _atomic(path: Path, data: dict):
    """Write JSON through a temp name beside the target (the leading dot keeps the suffix), then rename: a reader never sees half a file.
    Self-contained on purpose: the container holds this folder, not the repo."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, path)


def claim_attempt(vol_root, key: str, now=time.time, reload=lambda: None, commit=lambda: None) -> str | None:
    """One attempt per run key on the Volume: a container that Modal re-schedules after a crash finds the marker and refuses
    (a re-run with a fresh timeout would pay twice). Returns an error text, or None when this attempt owns the key."""
    reload()
    p = Path(vol_root) / "attempts" / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "x", encoding="utf-8") as f:
            json.dump({"key": key, "at": round(now(), 1), "pid": os.getpid()}, f)
    except FileExistsError:
        return f"attempt marker {p.name} exists: this run was started before; a second attempt would pay twice (feedback-modal-crash-reschedule)"
    commit()
    return None


def run(batch: dict, root, out, models: list[dict], load_judge, *, th: dict, prompts: dict | None = None, deadline: float | None = None,
        now=time.monotonic, on_step=lambda path, info: None, vram=lambda: {}, free=lambda judge: None, only_frames: int | None = None,
        upload_every: int = 5) -> dict:
    """Every model in turn (one loaded at a time), every frame, every defect. ``models`` = ``[{"key", "path", ...}]``;
    ``load_judge(model) -> judge``. Each (model, frame) record is written to ``out/<key>/<frame>.json`` the moment it exists and
    reported to ``on_step`` (``info`` = ``{"kind": "frame" | "model" | "final", ...}``). A model that cannot load (OOM) ends the run:
    its error and the memory facts are written, nothing is retried. Returns ``{"end": DONE | CAPPED | MODEL_FAILED, ...}``."""
    root, out = Path(root), Path(out)
    prompts = prompts or load_prompts()
    bad = batch_problems(batch, root)
    if bad:
        return {"end": "BAD_BATCH", "problems": bad}
    defects = tuple(batch.get("defects") or DEFECTS)
    frames = batch["frames"][:only_frames] if only_frames else batch["frames"]
    examples = [open_image(root / e["file"]) for e in batch["style_examples"]]
    res = {"schema": SCHEMA_RESULT, "prefix": batch["prefix"], "defects": list(defects), "prompts_sha": prompts["prompts_sha"],
           "prompt_files": prompts["sha256"], "thresholds": th, "n_frames": len(frames), "models": {}, "end": "DONE"}
    n_up = 0
    for m in models:
        key = m["key"]
        mres = res["models"][key] = {"path": m["path"], "frames": {}}
        t_load = time.time()
        try:
            judge = load_judge(m)
        except Exception as exc:  # noqa: BLE001 - OOM or a broken load ends the run, the facts are written, nothing is retried
            mres.update(state="LOAD_FAILED", error=f"{type(exc).__name__}: {str(exc)[:300]}", vram=vram())
            res["end"] = "MODEL_FAILED"
            _atomic(out / key / "model.json", mres)
            on_step(out / key / "model.json", {"kind": "model", "model": key})
            break
        mres.update(state="LOADED", load_s=round(time.time() - t_load, 1), vram_after_load=vram())
        _atomic(out / key / "model.json", mres)
        on_step(out / key / "model.json", {"kind": "model", "model": key})
        t_run = time.time()
        try:
            for i, f in enumerate(frames, 1):
                if deadline is not None and now() > deadline:
                    raise DeadlineReached(f"{key}: the run's clock ran out before frame {f['id']}")
                imgs = {"frame": open_image(root / f["file"])}
                if f.get("anchor"):
                    imgs["anchor"] = open_image(root / f["anchor"])
                t0 = time.time()
                rec = ask_frame(judge, prompts, f, imgs, defects, examples, th)
                rec.update(id=f["id"], model=key, seconds=round(time.time() - t0, 2))
                mres["frames"][f["id"]] = rec
                p = out / key / f"{f['id']}.json"
                _atomic(p, rec)
                on_step(p, {"kind": "frame", "model": key, "id": f["id"], "n": i, "flush": i % upload_every == 0})
            mres["state"] = "DONE"
        except DeadlineReached as exc:
            mres["state"] = "CAPPED"
            mres["error"] = str(exc)
            res["end"] = "CAPPED"
        mres.update(run_s=round(time.time() - t_run, 1), vram_peak=vram())
        _atomic(out / key / "model.json", mres)
        on_step(out / key / "model.json", {"kind": "model", "model": key})
        free(judge)
        del judge
        if res["end"] != "DONE":
            break
    _atomic(out / "results.json", res)
    on_step(out / "results.json", {"kind": "final"})
    return res
