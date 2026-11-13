"""The lean step-3 pod, stage D (STEP3_POD_PLAN_LEAN_ka.md section 1): BiRefNet cut-outs of the 12 hero-sheet pictures that passed the
asset pod (3 heroes x 4 angles; the scout's three-quarter left is its fix edit ``E_B_H2_left34``). Question: are the alpha edges clean
enough for the 2.5D cards of the J5 route?

Per picture (``p14_stages.json`` D.pictures, each held to the sha256 of the asset pod's manifest): the BiRefNet matte at the pinned
revision (``edit/cutout.birefnet_mask``, ``config/cloud_pins.json`` models.cutout_birefnet), the card (``edit/cutout.finish``: 2 px
feather, defringe), the edge width in pixels (``edit/cutout.edge_width`` on the matte and on the card) and the card checks (AC-15 + the
SA-04 halo, ``edit/cutout.check``). Writes ``<out>/cutout/<name>.png`` (RGBA), ``<name>.mask.png`` and one line per picture in
``<out>/cutout/report.jsonl``, then ``report.json``. The model runs on the card when CUDA is there (it is small next to Qwen and LTX).

    python3 -m explainer_engine.training.pods.p14.p14_cutout --out <step3 dir> --assets <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from explainer_engine.edit import cutout as CUT
from explainer_engine.training.pods.p14.p14_qwen import load_cfg, sha256_file


def fetch(ref: dict, assets: Path) -> Path:
    p = Path(assets) / ref["path"].split("/", 1)[1]
    if not p.exists():
        from huggingface_hub import hf_hub_download
        p = Path(hf_hub_download("vano1919/tmr-artifacts", ref["path"], repo_type="dataset", local_dir=str(assets)))
    got = sha256_file(p)
    if got != ref["sha256"]:
        raise ValueError(f"{ref['name']}: sha256 {got} is not the pinned {ref['sha256']}")
    return p


def one(ref: dict, assets: Path, d: Path, *, mask_fn, device: str) -> dict:
    import numpy as np
    from PIL import Image
    src = fetch(ref, assets)
    t0 = time.time()
    mask = mask_fn(src, device=device)
    mask.save(d / f"{ref['name']}.mask.png")
    card = CUT.finish(Image.open(src), mask)
    out = d / f"{ref['name']}.png"
    card.save(out)
    alpha = np.asarray(card.getchannel("A"), dtype=np.float64) / 255.0
    return {"name": ref["name"], "hero": ref["hero"], "angle": ref["angle"], "source_sha256": ref["sha256"],
            "edge_width_px_matte": round(CUT.edge_width(CUT.load_mask(mask)), 3), "edge_width_px_card": round(CUT.edge_width(alpha), 3),
            "halo": round(CUT.halo_score(card), 4), "findings": CUT.check(card), "seconds": round(time.time() - t0, 1),
            "path": f"cutout/{out.name}", "sha256": sha256_file(out), "status": "ok"}


def run(out: Path, assets: Path, *, mask_fn=None, device: str | None = None) -> int:
    cfg = load_cfg()
    d = Path(out) / "cutout"
    d.mkdir(parents=True, exist_ok=True)
    if device is None:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    mask_fn = mask_fn or CUT.birefnet_mask
    rows = []
    for ref in cfg["D"]["pictures"]:
        try:
            row = one(ref, assets, d, mask_fn=mask_fn, device=device)
        except Exception as e:   # noqa: BLE001 - one bad picture must not end the stage
            row = {"name": ref["name"], "hero": ref["hero"], "angle": ref["angle"], "status": "failed", "error": repr(e)[:300]}
        rows.append(row)
        with open(d / "report.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")
        print(row["name"], row["status"], row.get("edge_width_px_card", ""), flush=True)
    ok = [r for r in rows if r["status"] == "ok"]
    (d / "report.json").write_text(json.dumps({"schema": "p14_cutout/1", "question": cfg["D"]["question"], "device": device,
                                               "ok": len(ok), "pictures": rows}, indent=1), encoding="utf-8")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lean step-3 pod: BiRefNet cut-outs")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--assets", type=Path, required=True)
    a = ap.parse_args(argv)
    return run(a.out, a.assets)


if __name__ == "__main__":
    sys.exit(main())
