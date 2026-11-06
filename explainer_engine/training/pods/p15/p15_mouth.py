"""J5 mouth variants on the p15 pod, the SHEET way (ვანო 2026-11-06 19:41 UTC): ONE Qwen-Image-2.1 + xworld_v2 picture per hero holds all
8 variants (6 Rhubarb mouth shapes + 2 blink frames) in the grid of ``mouth_grid`` (4 x 2), same face in every cell; the cells are cut and
aligned by free Python afterwards (J5 thread). It runs after the 24 pictures with the SAME loaded pipeline: an edit with the hero's own
sheet as Image 1 (identity), 1280x720, seed 11; a sheet whose cells fail the structure check (``cells_ok``) is redrawn with the next seed,
at most ``SEEDS`` = 3 tries per hero (6 pictures at most). Every picture lands as it is drawn (OR-33): ``<out>/mouth_variants/``.
Identity (cosine of every cut cell to the hero sheet) is a free host-side step: ``python -m ...p15_mouth --check <dir> --sheets <dir>``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from explainer_engine.training.pods.p15 import mouth_grid as G

HERE = Path(__file__).resolve().parent
SEEDS = (11, 12, 13)
MIN_CELL_STD = 12.0   # a cell of flat colour has std ~0; a drawn head on a plain background is far above this (structure check only)
MIN_CELL_DIFF = 6.0   # mean abs difference between two cells: a sheet that repeats one cell eight times is not a variant sheet


def load_spec() -> dict:
    return json.loads((HERE / "mouth_spec.json").read_text(encoding="utf-8"))


def words(s: str) -> int:
    return len(s.split())


def prompt(hero: dict) -> str:
    """The grid prompt, built from the sheet's own description (<= 90 words, each tag once)."""
    who = hero["prompt"].split("plain neutral background.", 1)[-1].strip().rstrip(".")
    rows = [", ".join(G.WORDS[n] for n in G.ORDER[r * G.COLS:(r + 1) * G.COLS]) for r in range(G.ROWS)]
    return (f"xworld style, expression sheet, a grid of 8 head portraits, 4 columns and 2 rows, of the same person, the same face in every cell, "
            f"flat ambient lighting, no cast shadows, plain neutral background. Mouths in row one: {rows[0]}. Row two: {rows[1]}. {who}.")


def cells_ok(im) -> tuple[bool, str]:
    """Structure only (the identity check is separate): every cell has drawn content and the cells are not copies of one another."""
    import numpy as np
    cells = {n: np.asarray(c.convert("L").resize((64, 64)), np.float32) for n, c in G.cut(im).items()}
    flat = [n for n, a in cells.items() if a.std() < MIN_CELL_STD]
    if flat:
        return False, f"empty cells {flat}"
    same = [(a, b) for i, a in enumerate(G.ORDER) for b in G.ORDER[i + 1:] if float(np.abs(cells[a] - cells[b]).mean()) < MIN_CELL_DIFF]
    return (not same), (f"identical cells {same[:3]}" if same else "ok")


def fetch_sheet(spec: dict, hero: str, work: Path) -> Path:
    from huggingface_hub import hf_hub_download
    p = Path(hf_hub_download("vano1919/tmr-artifacts", f"{spec['hf']}/{hero}.png", repo_type="dataset", local_dir=str(work)))
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != spec["sheets"][hero]["png_sha256"]:
        raise ValueError(f"{hero}: sha256 {got} is not the pinned {spec['sheets'][hero]['png_sha256']}")
    return p


def run_all(pipe, cfg: dict, out: Path, work: Path, say, draw, max_streak: int = 3) -> tuple[int, int]:
    """Returns (sheets made, pictures drawn). Stops after ``max_streak`` exceptions in a row."""
    from PIL import Image
    spec = load_spec()
    md = Path(out) / "mouth_variants"
    md.mkdir(parents=True, exist_ok=True)
    made = drawn = streak = 0
    for hero, e in spec["sheets"].items():
        ref = None
        for seed in SEEDS:
            p = md / f"{hero}__sheet_s{seed}.png"
            if p.exists():
                continue
            t1 = time.time()
            try:
                ref = ref or Image.open(fetch_sheet(spec, hero, work)).convert("RGB")
                j = {"prompt": prompt(e), "seed": seed, "cfg": cfg["qwen"]["cfg_edit"], "size": G.CANVAS}
                im = draw(pipe, cfg, j, [ref]).convert("RGB")
            except Exception as ex:   # noqa: BLE001 - one failed picture must not end the stage
                streak += 1
                say("FAIL", hero, seed, repr(ex)[:300])
                if streak >= max_streak:
                    say("STOP:", streak, "mouth sheets failed in a row")
                    return made, drawn
                continue
            streak = 0
            drawn += 1
            ok, why = cells_ok(im)
            im.save(p)
            side = {"hero": hero, "seed": seed, "prompt": j["prompt"], "words": words(j["prompt"]), "cfg": j["cfg"], "size": list(G.CANVAS),
                    "layout": {"cols": G.COLS, "rows": G.ROWS, "margin": G.MARGIN, "order": list(G.ORDER)}, "structure_ok": ok, "structure": why,
                    "seconds": round(time.time() - t1, 1), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "lora": cfg["qwen"]["style_lora"],
                    "ref": {"path": f"{spec['hf']}/{hero}.png", "sha256": e["png_sha256"]}}
            p.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False), encoding="utf-8")
            with open(md / "manifest.jsonl", "a") as f:
                f.write(json.dumps(side, ensure_ascii=False) + "\n")
            say("sheet", hero, seed, "structure", why, side["seconds"], "s")
            if ok:
                made += 1
                break
    return made, drawn


def identity(mouth_dir: Path, sheets_dir: Path, embedder=None) -> dict:
    """Free, host side: cut every drawn sheet and report the cosine of each cell to the hero's sheet picture (qa/identity.hero_identity)."""
    from explainer_engine.qa import identity as ID
    spec = load_spec()
    rep = {}
    for hero in spec["sheets"]:
        ref = Path(sheets_dir) / f"{hero}.png"
        for sp in sorted(Path(mouth_dir).glob(f"{hero}__sheet_s*.png")):
            cells = G.cut_files(sp, f"{hero}__{sp.stem.split('_s')[-1]}", Path(mouth_dir) / "cells")
            per = {}
            for c in cells:
                per[c.stem.split("__")[-1]] = round(ID.hero_identity([c], [ref], embedder)["mean"], 4)
            rep[sp.stem] = {"per_cell": per, "min": min(per.values()), "mean": round(sum(per.values()) / len(per), 4)}
    (Path(mouth_dir) / "identity.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="mouth sheets: print the prompts, or run the free identity check")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", type=Path, help="the mouth_variants folder of a finished pod")
    ap.add_argument("--sheets", type=Path, help="folder with the hero sheet pictures (B_H1_left34.png ...)")
    a = ap.parse_args(argv)
    if a.check:
        print(json.dumps(identity(a.check, a.sheets), indent=1))
        return 0
    for h, e in load_spec()["sheets"].items():
        pr = prompt(e)
        print(h, words(pr), "words:", pr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
