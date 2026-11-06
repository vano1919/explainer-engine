"""Route-test Qwen asset pod, the pod side (2026-11-06; route_assets.sh starts it; settings in route_assets.json).

One 48 GB card, Qwen-Image-2.1 + xworld_v2 checkpoint 3000 at weight 0.7 (config/cloud_pins.json loras.xworld_v2), the loader, the LoRA merge
and the draw call of xworld_v1_test.py (round 3b). Nothing here is a new setting: sizes, steps, cfg, seed and the negative prompt are the
registered ones (qa/style_prompt.INFERENCE, NEGATIVE; cfg 2.5 for edit jobs as round 3b did).

Phase 1 (in this order, so the useful pictures come first): D scenes (seed 11), A 360-degree backdrops (2048x1024, TURN-style, with the
left/right edge difference measured), B hero sheets (3 heroes x 4 angles, a flat-light line on every prompt), C hero 1 front placed in each
backdrop by reference (2 seeds), P at most two pictures with the 2.1 panorama outpaint LoRA on backdrop A1 (an experiment: loaded or dropped,
no retries), then the identity scores (CLIP ViT-B-32, the embedder of training/embed.py) of C and of the other angles against hero 1's front.
Phase 2: ``phase1_done.txt`` is written, then the pod waits up to ``wait_picks_s`` for ``e_picks.json`` on HF (the worker's own vision judgement
of phase 1: which D scenes to redraw with seeds 12 and 13, which three pictures get a fix edit and what the defect is); no file = it ends.

Every picture is a file under ``$EE_OUT/<group>/`` with a sidecar (prompt, seed, cfg, size, refs, loras, sha256, seconds) and a line in
``manifest.jsonl`` as soon as it is drawn; the wrapper uploads ``$EE_OUT`` every five minutes (OR-33). The keyframe gate's 72B judge does not fit
beside the image model on 48 GB, so the gate answers come from the worker's reading of the pictures after phase 1.

    python route_assets.py --list            # the job list and the prompt check, no GPU
    python route_assets.py                   # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "route_assets.json").read_text(encoding="utf-8"))
SAMP = CFG["sampler"]
TRIGGER = CFG["style_lora"]["trigger"]
STYLE = ("style", CFG["style_lora"]["weight"])
PANO = ("pano", CFG["pano_lora"]["weight"])


def hero_prompt(h, angle_words):
    """B: the p2s sheet wording per angle, the creator's flat-light line (plan section 9.2) on every prompt."""
    return (f"{TRIGGER}, model sheet of one person, {angle_words}, neutral pose, {CFG['flat']}. "
            f"{CFG['heroes'][h]['look']}")


def jobs(cfg=CFG):
    """Phase 1 as dicts: name, group, prompt, seed, cfg, size, refs (names of earlier pictures, '<name>:view' = the 16:9 view), lora, kind."""
    s = cfg["sampler"]
    out = []
    for name, pr in cfg["scenes"]:
        out.append({"name": name, "group": "D", "prompt": pr, "seed": s["seed"], "cfg": s["cfg_text"], "size": s["size"], "refs": [],
                    "lora": "style", "kind": "t2i"})
    for name, pr in cfg["backdrops"]:
        out.append({"name": name, "group": "A", "prompt": pr, "seed": s["seed"], "cfg": s["cfg_text"], "size": s["erp_size"],
                    "refs": [], "lora": "style", "kind": "t2i"})
    for h in cfg["heroes"]:
        for key, words in cfg["angles"]:
            out.append({"name": f"B_{h}_{key}", "group": "B", "prompt": hero_prompt(h, words), "seed": s["seed"], "cfg": s["cfg_text"],
                        "size": s["size"], "refs": [], "lora": "style", "kind": "t2i"})
    for bname, _ in cfg["backdrops"]:
        for seed in cfg["seeds_pair"]:
            out.append({"name": f"C_H1_{bname}_s{seed}", "group": "C", "seed": seed, "cfg": s["cfg_edit"], "size": s["size"],
                        "prompt": cfg["hero_in_place"].format(name=cfg["heroes"]["H1"]["name"]),
                        "refs": ["B_H1_front", f"{bname}:view"], "lora": "style", "kind": "edit"})
    return out


def pano_jobs(cfg=CFG):
    p = cfg["pano_lora"]
    return [{"name": f"P_A1_pano_s{seed}", "group": "P", "seed": seed, "cfg": 1.0, "steps": 25, "size": p["canvas"], "refs": ["A1_tent:canvas"],
             "prompt": p["trigger"] + " Fill the green area with the rest of the same tent camp at dusk, canvas tents, banners and hills "
                       "around it, the light of a low orange sun. Keep the placed picture as it is.",
             "lora": "style+pano", "kind": "edit"} for seed in cfg["seeds_pair"]]


def picks_jobs(picks, cfg=CFG):
    """Phase 2 from the worker's picks file: {"redraw": [{"job": "D3_tent", "seeds": [12, 13]}], "fix": [{"image": "D1_ford", "defect": "..."}]}."""
    s, by = cfg["sampler"], {j["name"]: j for j in jobs(cfg)}
    out = []
    for r in picks.get("redraw", []):
        base = by[r["job"]]
        for seed in r["seeds"][:2]:
            out.append(dict(base, name=f"{r['job']}_redraw{seed}", seed=seed, group="D"))
    for f in picks.get("fix", [])[:3]:
        src = by[f["image"]]
        out.append({"name": f"E_{f['image']}", "group": "E", "seed": s["seed"], "cfg": s["cfg_edit"], "size": src["size"], "refs": [f["image"]],
                    "prompt": f"{TRIGGER}, Image 1 is the picture. Change nothing else; fix: {f['defect']}", "lora": "style", "kind": "edit"})
    return out


def prompt_problems(cfg=CFG):
    """The style-prompt check (qa/style_prompt.check) on the plain text prompts of groups A, B, D; the edit prompts name images by position and are not
    style prompts (their lead is the p2s one)."""
    from explainer_engine.qa import style_prompt
    return [(j["name"], f) for j in jobs(cfg) if j["kind"] == "t2i" for f in style_prompt.check(j["prompt"])]


# ---------------------------------------------------------------- pure picture helpers (PIL / numpy only)
def view_of(img, size=(1280, 720)):
    """The middle 16:9 part of a 2:1 picture, resized: what a camera looking straight ahead would see (a plain crop, not a reprojection)."""
    w, h = img.size
    cw = int(h * size[0] / size[1])
    x0 = (w - cw) // 2
    return img.crop((x0, 0, x0 + cw, h)).resize(size)


def pano_canvas(img, cfg=CFG):
    """The panorama LoRA's input: the view on a 2:1 canvas, everything else pure green #00FF00."""
    from PIL import Image
    p = cfg["pano_lora"]
    canvas = Image.new("RGB", tuple(p["canvas"]), (0, 255, 0))
    x0, y0, x1, y1 = p["view_box"]
    canvas.paste(view_of(img, (x1 - x0, y1 - y0)), (x0, y0))
    return canvas


def seam_score(img):
    """Left/right edge difference of a 2:1 picture: mean absolute difference of the first and last columns, divided by the mean difference between
    neighbouring columns inside the picture (about 1.0 = the edge joins as smoothly as the picture itself; far above 1 = a visible seam)."""
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=float)
    edge = np.abs(a[:, 0] - a[:, -1]).mean()
    inner = np.abs(a[:, 1:] - a[:, :-1]).mean()
    return round(float(edge / max(inner, 1e-6)), 3)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Run:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()
        self.deadline = float(os.environ.get("EE_DEADLINE") or 0) or None
        self.soft = self.t0 + 0.8 * (self.deadline - self.t0) if self.deadline else None  # 80 % of the time cap: no new picture after it
        self.secs = []
        self.log = open(self.out / "pod.log", "a")
        self.done = 0

    def say(self, *a):
        line = time.strftime("%H:%M:%S ") + " ".join(map(str, a))
        print(line, flush=True)
        self.log.write(line + "\n")
        self.log.flush()

    def event(self, ev, **kw):
        with open(self.out / "t.jsonl", "a") as f:
            f.write(json.dumps({"t": time.strftime("%FT%TZ", time.gmtime()), "ev": ev, **kw}) + "\n")

    def progress(self, text):
        (self.out / "progress.txt").write_text(text + "\n")

    def est(self):
        s = sorted(self.secs)
        return s[len(s) // 2] if s else 150.0

    def can_start(self):
        if self.soft and time.time() + self.est() > self.soft:
            return False
        return not (self.deadline and time.time() + self.est() * 1.3 + 240 > self.deadline)

    def path(self, j):
        return self.out / j["group"] / f"{j['name']}.png"


def draw(R, pipe, j, refs):
    import torch
    g = torch.Generator(device="cuda").manual_seed(j["seed"])
    with torch.no_grad():
        return pipe(j["prompt"], image=refs or None, negative_prompt=SAMP["negative"], height=j["size"][1], width=j["size"][0], generator=g,
                    num_inference_steps=j.get("steps", SAMP["steps"]), true_cfg_scale=j["cfg"]).images[0]


def load_ref(R, ref):
    """A reference by name: '<name>' = the picture, '<name>:view' = its 16:9 view, '<name>:canvas' = the green panorama canvas."""
    from PIL import Image
    name, _, how = ref.partition(":")
    hit = next(R.out.glob(f"*/{name}.png"))
    im = Image.open(hit).convert("RGB")
    return view_of(im) if how == "view" else pano_canvas(im) if how == "canvas" else im


def make(R, loras, pipe, j):
    """Draw one job, save it, its sidecar and its manifest line. A failed job is logged and the queue goes on."""
    if R.path(j).exists():
        return True
    if not R.can_start():
        R.say("STOP before", j["name"], "(time cap 80 %)")
        R.event("time_stop", job=j["name"])
        return False
    t = time.time()
    try:
        pipe = loras(j["lora"]) or pipe
        im = draw(R, pipe, j, [load_ref(R, r) for r in j["refs"]]).convert("RGB")
    except Exception as e:  # noqa: BLE001 - one failed picture must not end the pod
        import traceback
        R.say("FAIL", j["name"], repr(e)[:300], traceback.format_exc()[-500:].replace("\n", " | "))
        R.event("job_failed", job=j["name"], err=repr(e)[:200])
        return True
    p = R.path(j)
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p)
    sec = round(time.time() - t)
    R.secs.append(sec)
    side = {k: j[k] for k in ("name", "group", "prompt", "seed", "cfg", "size", "refs", "lora", "kind")}
    side.update(steps=j.get("steps", SAMP["steps"]), negative=SAMP["negative"], seconds=sec, sha256=sha256_file(p))
    if j["group"] == "A" or j["group"] == "P":
        side["seam_score"] = seam_score(im)
    p.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(R.out / "manifest.jsonl", "a") as f:
        f.write(json.dumps(side, ensure_ascii=False) + "\n")
    R.done += 1
    R.progress(f"{R.done} pictures, last {j['name']} {sec}s")
    R.say("made", j["name"], sec, "s", side.get("seam_score", ""))
    return True


def identity(R):
    """CLIP cosine of every C picture and of the other hero angles to hero 1's front (the embedder of training/embed.py); skipped, with the reason, if open_clip is missing."""
    try:
        import numpy as np
        import open_clip
        import torch
        from PIL import Image
        m, _, pre = open_clip.create_model_and_transforms("ViT-B-32", "laion2b_s34b_b79k")
        m.eval()

        def emb(p):
            with Image.open(p) as im, torch.no_grad():
                v = m.encode_image(pre(im.convert("RGB")).unsqueeze(0))[0].numpy()
            return v / np.linalg.norm(v)
        ref = R.out / "B" / "B_H1_front.png"
        r = emb(ref)
        res = {p.stem: round(float(emb(p) @ r), 4) for g in ("C", "B") for p in sorted((R.out / g).glob("*.png")) if p != ref}
        (R.out / "identity.json").write_text(json.dumps({"embedder": "open_clip ViT-B-32 laion2b_s34b_b79k", "reference": "B_H1_front",
                                                          "cosine": res}, indent=1), encoding="utf-8")
        R.say("identity", len(res), "scores")
    except Exception as e:  # noqa: BLE001
        (R.out / "identity.json").write_text(json.dumps({"skipped": repr(e)[:300]}), encoding="utf-8")
        R.say("identity skipped", repr(e)[:200])


def wait_picks(R):
    """Phase 2 input: e_picks.json on HF next to the pictures; None after wait_picks_s."""
    from huggingface_hub import hf_hub_download
    repo, prefix = os.environ.get("EE_HF_REPO", "vano1919/tmr-artifacts"), os.environ.get("EE_HF_PREFIX", "route_test_2026-11/assets").strip("/")
    until = min(time.time() + CFG["wait_picks_s"], (R.deadline or 1e18) - 600)
    while time.time() < until:
        try:
            p = hf_hub_download(repo, f"{prefix}/e_picks.json", repo_type="dataset", local_dir="/workspace/picks", force_download=True)
            return json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - not there yet
            time.sleep(60)
    return None


def pod_loras(t, pipe, tr, say):
    """Merges the style LoRA (and for the experiment the panorama one) in the order given; one place for the gate_up fix of xworld_v1_test.Loras."""
    from huggingface_hub import hf_hub_download
    from videox_fun.utils import merge_lora, unmerge_lora
    import torch
    paths = {"style": hf_hub_download(CFG["style_lora"]["hf"], CFG["style_lora"]["path"], repo_type="dataset")}
    if sha256_file(paths["style"]) != CFG["style_lora"]["sha256"]:
        raise SystemExit("style LoRA sha256 mismatch: not the checkpoint the creator approved")
    L = t.Loras(pipe, tr, paths, say)
    state = {"cur": ()}
    wanted = {"style": ((("style", CFG["style_lora"]["weight"]),)), "style+pano": (("style", CFG["style_lora"]["weight"]), ("pano", CFG["pano_lora"]["weight"]))}

    def use(key):
        want = wanted[key]
        if want == state["cur"]:
            return L.pipe
        if "pano" in dict(want) and "pano" not in paths:
            paths["pano"] = hf_hub_download(CFG["pano_lora"]["repo"], CFG["pano_lora"]["file"])
            say("pano lora", CFG["pano_lora"]["repo"], paths["pano"], sha256_file(paths["pano"]))
        for k, w in reversed(state["cur"]):
            L.pipe = unmerge_lora(L.pipe, paths[k], w, device="cuda", dtype=torch.bfloat16)
            L.gate_up(paths[k], -w)
        for k, w in want:
            L.pipe = merge_lora(L.pipe, paths[k], w, device="cuda", dtype=torch.bfloat16)
            say("lora", k, w, "gate_up", L.gate_up(paths[k], w))
        state["cur"] = want
        return L.pipe
    return use


def main():
    sys.path.insert(0, str(HERE))
    import xworld_v1_test as t
    R = Run(os.environ.get("EE_OUT", "/workspace/out"))
    R.event("script_start", deadline=os.environ.get("EE_DEADLINE", ""))
    try:
        bad = prompt_problems()
    except ImportError:  # the pod has no explainer_engine; the check ran in the unit tests and before the pod
        bad = "not run on the pod"
    R.say("prompt check:", bad or "clean")
    pipe, tr = t.load_pipeline()
    use = pod_loras(t, pipe, tr, R.say)
    R.say("loaded")
    todo = jobs()
    for j in todo:
        if not make(R, use, pipe, j):
            break
    else:
        R.say("pano experiment (at most two pictures, no retries)")
        try:
            for j in pano_jobs():
                if not make(R, use, pipe, j):
                    break
        except Exception as e:  # noqa: BLE001 - dropped, as agreed
            R.say("pano dropped", repr(e)[:300])
            R.event("pano_dropped", err=repr(e)[:200])
        identity(R)
    (R.out / "phase1_done.txt").write_text(time.strftime("%FT%TZ", time.gmtime()) + f" pictures={R.done}\n")
    R.progress(f"phase 1 done, {R.done} pictures, waiting for e_picks.json")
    picks = wait_picks(R)
    if picks is None:
        R.say("no picks file: the pod ends here")
        R.event("no_picks")
    else:
        for j in picks_jobs(picks):
            if not make(R, use, pipe, j):
                break
    R.progress(f"done, {R.done} pictures")
    R.event("done", pictures=R.done)
    R.say("ROUTE ASSETS DONE")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--list"]:
        for j in jobs() + pano_jobs():
            print(j["group"], j["name"], j["size"], j["seed"], j["cfg"], len(j["prompt"].split()), "words |", j["prompt"][:100])
        print("prompt problems:", prompt_problems() or "none")
    else:
        main()
