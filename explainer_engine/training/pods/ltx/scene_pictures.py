"""The start pictures of an LTX scene of cuts (D-132; the creator 2026-11-12 20:44 UTC): one picture per shot from the
Gemini API batch tier (``imagegen/gemini.GeminiClient.submit_batch``, half price), in stages, so an earlier stage's picture
(the heroes' sheet) is a reference of the next one (the two-stage reference chain). Every picture is looked at before the
next stage; ``pin`` fits each shot's picture to the LTX size and writes the manifest whose sha256s the scene's job spec
pins (``scene_run.job_spec``).

    python -m explainer_engine.training.pods.ltx.scene_pictures estimate <scene.json>             # free: the price per stage
    EXPLAINER_GEMINI_API=on EE_PICTURES_GO=<cmsg>:<scene sha[:12]> \\
    python -m explainer_engine.training.pods.ltx.scene_pictures submit  <scene.json> <stage>      # paid: one batch
    python -m explainer_engine.training.pods.ltx.scene_pictures collect <scene.json> <stage> [--wait S]
    python -m explainer_engine.training.pods.ltx.scene_pictures pin     <scene.json>              # free: fit + manifest
    python -m explainer_engine.training.pods.ltx.scene_pictures upload  <scene.json>              # the pictures to HF, checked

The batch price is reserved in the scene's ledger (``gemini_usd``) before the POST; a stage is submitted at most once (the
ledger item and the client's pending file refuse a repeat); the scene's ``budget.pictures_usd`` caps every stage together.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path

from explainer_engine.core.ledger import Run
from explainer_engine.core.store import write_json_atomic
from explainer_engine.imagegen.gemini import BATCH_PRICES, REFERENCE_USD, GeminiClient
from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
HF_REPO = "vano1919/tmr-artifacts"


def load(scene_path) -> dict:
    return json.loads(Path(scene_path).read_text(encoding="utf-8"))


def scene_sha(scene_path) -> str:
    return hashlib.sha256(Path(scene_path).read_bytes()).hexdigest()


def stage_items(scene: dict, stage: str) -> list[dict]:
    st = scene["pictures"]["stages"]
    if stage not in st:
        raise SystemExit(f"no stage {stage!r}; the scene has {list(st)}")
    return st[stage]


def item_price(pics: dict, it: dict) -> float:
    return BATCH_PRICES[pics["model"]][pics["size"]] + len(it.get("refs") or []) * REFERENCE_USD


def estimate(scene: dict) -> dict:
    pics = scene["pictures"]
    out = {s: round(sum(item_price(pics, it) for it in items), 4) for s, items in pics["stages"].items()}
    out["total"] = round(sum(out.values()), 4)
    return out


def manifest(scene: dict) -> dict:
    p = Path(scene["pictures"]["manifest"])
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"made": {}, "shots": {}, "batches": {}}


def save_manifest(scene: dict, m: dict) -> None:
    write_json_atomic(Path(scene["pictures"]["manifest"]), m)


def style_bytes(scene: dict, fetch=None) -> bytes:
    """The channel's main style picture, from the HF vault, checked against the scene's pin."""
    st = scene["pictures"]["style"]
    local = Path(scene["pictures"]["dir"]) / "style.png"
    if not local.exists():
        if fetch is None:
            from huggingface_hub import hf_hub_download
            fetch = lambda path: Path(hf_hub_download(HF_REPO, path, repo_type="dataset")).read_bytes()  # noqa: E731
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(fetch(st["hf"]))
    data = local.read_bytes()
    if hashlib.sha256(data).hexdigest() != st["sha256"]:
        raise SystemExit(f"the style picture {local} is not the one the scene pins")
    return data


def refs_of(scene: dict, it: dict, m: dict, fetch=None) -> list[bytes]:
    """The item's references in order: ``style`` is the main style picture, any other id a picture made by an earlier stage
    (its sha256 as collected; a changed or missing file refuses the stage)."""
    out = []
    for r in it.get("refs") or []:
        if r == "style":
            out.append(style_bytes(scene, fetch))
            continue
        made = m["made"].get(r)
        if not made:
            raise SystemExit(f"{it['id']}: its reference {r!r} is not made yet; collect that stage first")
        data = Path(made["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != made["sha256"]:
            raise SystemExit(f"{it['id']}: the reference {r!r} changed after it was collected")
        out.append(data)
    return out


def go_gate(scene_path, env=os.environ) -> str:
    """EE_PICTURES_GO = ``<the creator's message id>:<sha256[:12] of the scene file he said yes to>`` (OR-23)."""
    v = env.get("EE_PICTURES_GO", "")
    mm = GO.match(v)
    if not mm or mm.group(2) != scene_sha(scene_path)[:12]:
        raise SystemExit("EE_PICTURES_GO must be '<the creator's message id>:<this scene file's sha256[:12]>'; nothing was sent")
    return v


def open_ledger(scene: dict) -> Run:
    led = scene["ledger"]
    return Run.open(led["path"], caps=led["caps"], what=f"LTX scene {scene['id']}")


def client(scene: dict, run: Run | None, **kw) -> GeminiClient:
    d = Path(scene["pictures"]["dir"])
    return GeminiClient(d, cap_usd=float(scene["budget"]["pictures_usd"]), run=run, cache_dir=d / "cache", **kw)


def submit(scene_path, stage: str, *, env=os.environ, gc=None, fetch=None) -> str:
    scene = load(scene_path)
    go_gate(scene_path, env)
    pics, m = scene["pictures"], manifest(scene)
    if stage in m["batches"]:
        raise SystemExit(f"stage {stage} was submitted already ({m['batches'][stage]['name']}); collect it, a repeat pays twice")
    items = stage_items(scene, stage)
    total = estimate(scene)
    if total["total"] > float(scene["budget"]["pictures_usd"]) + 1e-9:
        raise SystemExit(f"the pictures cost ${total['total']} together, over the scene's pictures_usd "
                         f"${scene['budget']['pictures_usd']}")
    run = open_ledger(scene)
    gc = gc or client(scene, run)
    batch = [{"name": it["id"], "prompt": it["prompt"], "refs": refs_of(scene, it, m, fetch)} for it in items]
    name = gc.submit_batch(batch, model=pics["model"], size=pics["size"], aspect=pics["aspect"])
    m["batches"][stage] = {"name": name, "usd": total[stage], "items": [it["id"] for it in items]}
    save_manifest(scene, m)
    return name


def collect(scene_path, stage: str, *, wait_s: float = 0.0, gc=None) -> dict:
    scene = load(scene_path)
    m = manifest(scene)
    b = m["batches"].get(stage)
    if not b:
        raise SystemExit(f"stage {stage} was not submitted")
    gc = gc or client(scene, open_ledger(scene))
    res = gc.collect_batch(b["name"], wait_s=wait_s)
    for item, val in res["items"].items():
        if isinstance(val, Path):
            m["made"][item] = {"path": str(val), "sha256": hashlib.sha256(val.read_bytes()).hexdigest(), "stage": stage}
    b["state"], b["done"] = res["state"], res["done"]
    b["errors"] = {k: v for k, v in res["items"].items() if not isinstance(v, Path)}
    save_manifest(scene, m)
    return {"state": res["state"], "done": res["done"], "made": sorted(k for k, v in res["items"].items() if isinstance(v, Path)),
            "errors": b["errors"]}


def pin(scene_path, launch=None) -> dict:
    """Every shot's picture fitted to the clip size (``modal_ltx_jobs.fit_picture``: centre crop, Lanczos), so the picture
    that is looked at is the one LTX starts from; its sha256 goes into the manifest."""
    from PIL import Image
    launch = L.LAUNCH if launch is None else launch
    scene = load(scene_path)
    m = manifest(scene)
    nat = L.native_spec(launch, max(float(s["seconds"]) for s in scene["shots"]))
    for s in scene["shots"]:
        made = m["made"].get(s["picture"])
        if not made:
            raise SystemExit(f"{s['shot_id']}: picture {s['picture']} is not made yet")
        src = Path(made["path"])
        if hashlib.sha256(src.read_bytes()).hexdigest() != made["sha256"]:
            raise SystemExit(f"{s['picture']} changed after it was collected")
        dst = src.with_name(f"{s['picture']}_{nat['width']}x{nat['height']}.png")
        L.fit_picture(Image.open(io.BytesIO(src.read_bytes())), nat["width"], nat["height"]).save(dst)
        m["shots"][s["picture"]] = {"path": str(dst), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                                    "from": made["sha256"]}
    save_manifest(scene, m)
    return m["shots"]


def upload(scene_path, api=None) -> dict:
    """The made pictures, their LTX fits and the manifest to the HF vault; each checked by sha256 (OR-33)."""
    from huggingface_hub import CommitOperationAdd, HfApi
    scene = load(scene_path)
    m = manifest(scene)
    api = api or HfApi()
    files = [Path(v["path"]) for v in m["made"].values()] + [Path(v["path"]) for v in m["shots"].values()]
    files.append(Path(scene["pictures"]["manifest"]))
    pre = scene["pictures"]["hf"].rstrip("/") + "/"
    api.create_commit(repo_id=HF_REPO, repo_type="dataset", commit_message=f"{scene['id']}: start pictures",
                      operations=[CommitOperationAdd(path_in_repo=pre + f.name, path_or_fileobj=str(f)) for f in files])
    info = {i.path: i for i in api.get_paths_info(HF_REPO, [pre + f.name for f in files], repo_type="dataset", expand=True)}
    out = {}
    for f in files:
        i = info.get(pre + f.name)
        lfs = getattr(i, "lfs", None) if i else None
        want = getattr(lfs, "sha256", None) if lfs else None
        ok = i is not None and ((want == L._sha(f)) if want else getattr(i, "blob_id", None) == L.git_blob_id(f))
        out[f.name] = "ok" if ok else "hash differs on HF"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scene_pictures")
    ap.add_argument("cmd", choices=("estimate", "submit", "collect", "pin", "upload"))
    ap.add_argument("scene")
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--wait", type=float, default=0.0)
    a = ap.parse_args(argv)
    if a.cmd == "estimate":
        res = estimate(load(a.scene))
    elif a.cmd == "submit":
        res = {"batch": submit(a.scene, a.stage)}
    elif a.cmd == "collect":
        res = collect(a.scene, a.stage, wait_s=a.wait)
    elif a.cmd == "pin":
        res = pin(a.scene)
    else:
        res = upload(a.scene)
    print(json.dumps(res, default=str))


if __name__ == "__main__":
    main()
