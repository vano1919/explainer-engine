"""The 60 s pilot minute (EXEC_QUEUE.md P1; the creator 2026-11-06 16:18 UTC): the ten LTX clips of the p15 and p16 pods and the
room clock insert cut into one 2560x1440 video, and one page that sets Blender still | Qwen still | LTX clip side by side for every
shot. Free and local: it renders nothing paid. The clips are conformed with ``finish/upscale`` (the ROUTE_TEST chain: Lanczos, CAS,
grain 6), each trimmed to its shot's seconds (the clip is the next valid length up; the creator's Q4), the clock insert is a J5-style
push-in on its Qwen still (``p14_pod.move_cmd``, no LTX).

    python -m explainer_engine.production.pilot_minute --p15 <p15 out> --p16 <p16 out> --blender <dir of the Blender stills> --out <dir>
                                                        [--size 2560x1440] [--allow-missing]

``--p15`` / ``--p16``: the pods' output folders (``ltx/<job>.mp4``, ``qwen/<shot>.png``). ``--blender``: ``<shot>.png`` of the Blender
stills (the HF ``route_test_2026-11/pilot/blender/`` copy). Writes ``pilot_minute.mp4``, ``compare.html`` (+ ``page/``) and ``minute.json``.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.finish import upscale as U

FPS = 24
SEED = 42
# (id, shot id, seconds in the cut, pod whose clip it is, frames of that clip); the clock has no clip
MINUTE = (
    ("M01", "room_establishing", 6.0, "p16", 145), ("M02", "room_two_shot", 7.7, "p15", 185), ("M03", "room_close_host", 6.0, "p16", 145),
    ("M04", "room_close_guest", 6.0, "p16", 145), ("M05", "room_reverse", 6.0, "p16", 145), ("M06", "room_insert_table", 4.0, "p16", 97),
    ("M07", "room_insert_clock", 3.0, None, 0), ("M08", "battle_f000_colour", 7.7, "p15", 185),
    ("M09", "battle_wide_high", 6.0, "p16", 145), ("M10", "battle_front_mid", 6.0, "p16", 145), ("M11", "battle_f200_colour", 5.0, "p16", 121),
)
CLOCK_ZOOM = 1.12


def total_seconds() -> float:
    return round(sum(m[2] for m in MINUTE), 3)


def resolve_shots(blender: Path, p16: Path | None = None) -> dict[str, str]:
    """The camera-named battle shots (``battle_wide_high``) -> the still's id (``battle_wide_high_f112_colour``) from the files."""
    out = {}
    for _, shot, *_ in MINUTE:
        if shot in ("battle_wide_high", "battle_front_mid"):
            found = sorted(Path(blender).glob(f"{shot}_f*_colour.png"))
            out[shot] = found[-1].stem if found else shot
        else:
            out[shot] = shot
    return out


def job_path(root: Path, shot_id: str, frames: int) -> Path:
    return Path(root) / "ltx" / f"pilot.{shot_id}.ltx25.i2v.f{frames}.s{SEED}.mp4"


def plan(roots: dict[str, Path], blender: Path) -> list[dict]:
    ids = resolve_shots(blender)
    rows = []
    for mid, shot, secs, pod, frames in MINUTE:
        sid = ids[shot]
        row = {"id": mid, "shot": sid, "seconds": secs, "pod": pod, "frames": frames,
               "blender": Path(blender) / f"{sid}.png", "qwen": None, "clip": None}
        if pod:
            row["clip"] = job_path(roots[pod], sid, frames)
            row["qwen"] = Path(roots[pod]) / "qwen" / f"{sid}.png"
        else:   # the clock: the p15 pod restyled it, no clip
            row["qwen"] = Path(roots["p15"]) / "qwen" / f"{sid}.png"
        if frames and secs > frames / FPS + 1e-6:
            raise ContractError(f"{mid} {sid}: {secs} s is longer than its clip ({frames} frames = {frames / FPS:.2f} s)")
        rows.append(row)
    return rows


def conform_cmd(src: Path, dst: Path, seconds: float, size: tuple[int, int]) -> list[str]:
    w, h = U.probe_size(src)
    return ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", f"{seconds:.3f}",
            "-vf", U.video_filter(w, h, size, **U.ROUTE_TEST), "-an", "-c:v", "libx264", "-crf", str(U.CRF), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(dst)]


def slate_cmd(seconds: float, dst: Path, size: tuple[int, int]) -> list[str]:
    return ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x5a6a7a:s={size[0]}x{size[1]}:r={FPS}", "-t", f"{seconds:.3f}",
            "-c:v", "libx264", "-crf", str(U.CRF), "-pix_fmt", "yuv420p", str(dst)]


def _run(cmd: list[str]) -> None:
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise ConfigError(f"{cmd[0]} failed: {done.stderr.strip()[:300]}")


def _frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def build(roots: dict[str, Path], blender: Path, out: Path, *, size: tuple[int, int] = (2560, 1440), allow_missing: bool = False) -> dict:
    from explainer_engine.training.pods.p14 import p14_pod as P
    out = Path(out)
    parts_dir = out / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    rows = plan(roots, blender)
    missing = [str(r["clip"]) for r in rows if r["clip"] and not r["clip"].is_file()] + \
              [str(r["qwen"]) for r in rows if r["qwen"] and not r["qwen"].is_file() and r["clip"] is None]
    if missing and not allow_missing:
        raise ContractError("the minute lacks: " + ", ".join(missing))
    files, report = [], []
    for r in rows:
        dst = parts_dir / f"{r['id']}_{r['shot']}.mp4"
        slate = False
        if r["clip"] is None and r["qwen"].is_file():
            _run(P.move_cmd(r["qwen"], dst, seconds=r["seconds"], size=size, zoom_end=CLOCK_ZOOM, fps=FPS))
        elif r["clip"] is not None and r["clip"].is_file():
            _run(conform_cmd(r["clip"], dst, r["seconds"], size))
        else:
            _run(slate_cmd(r["seconds"], dst, size))
            slate = True
        n = _frames(dst)
        want = round(r["seconds"] * FPS)
        if not slate and n < want:
            raise ContractError(f"{r['id']} {r['shot']}: {n} frames, the shot needs {want}")
        files.append(dst)
        report.append({"id": r["id"], "shot": r["shot"], "seconds": r["seconds"], "frames": n, "pod": r["pod"], "slate": slate,
                       "sha256": contracts.sha256_file(dst)})
    listing = parts_dir / "concat.txt"
    listing.write_text("".join(f"file '{f.resolve()}'\n" for f in files), encoding="utf-8")
    final = out / "pilot_minute.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(final)])
    page = write_page(rows, report, out, final)
    doc = {"schema": "pilot_minute/1", "size": list(size), "fps": FPS, "seconds": round(sum(x["frames"] for x in report) / FPS, 3),
           "preview": any(x["slate"] for x in report), "video": final.name, "sha256": contracts.sha256_file(final), "page": page.name,
           "shots": report}
    write_json_atomic(out / "minute.json", doc)
    return doc


def write_page(rows: list[dict], report: list[dict], out: Path, final: Path) -> Path:
    """``compare.html``: per shot the Blender still, the Qwen still and the conformed LTX clip, side by side (relative paths)."""
    pg = Path(out) / "page"
    pg.mkdir(parents=True, exist_ok=True)

    def take(src: Path | None, name: str) -> str | None:
        if src and Path(src).is_file():
            shutil.copyfile(src, pg / name)
            return f"page/{name}"
        return None
    cells = []
    for r, rep in zip(rows, report):
        b = take(r["blender"], f"{r['id']}_blender.png")
        q = take(r["qwen"], f"{r['id']}_qwen.png")
        v = f"parts/{r['id']}_{r['shot']}.mp4"
        img = lambda p, t: f'<figure><img src="{p}" alt="{t}"><figcaption>{t}</figcaption></figure>' if p else f"<figure><p>{t}: none</p></figure>"  # noqa: E731
        vid = (f'<figure><video src="{v}" controls loop muted preload="metadata"></video><figcaption>'
               f'{"LTX clip" if r["clip"] else "J5 push-in on the Qwen still"}, {rep["seconds"]} s{" (slate: missing)" if rep["slate"] else ""}'
               "</figcaption></figure>")
        cells.append(f'<section><h2>{html.escape(r["id"])} {html.escape(r["shot"])}</h2><div class="row">'
                     f'{img(b, "Blender still")}{img(q, "Qwen restyle")}{vid}</div></section>')
    doc = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>Pilot minute: Blender, Qwen, LTX</title><style>body{font:15px system-ui;margin:16px;background:#111;color:#eee}"
           ".row{display:flex;gap:8px;flex-wrap:wrap}figure{margin:0;flex:1 1 320px}img,video{width:100%;display:block;border-radius:4px}"
           "figcaption{font-size:12px;color:#aaa;padding:2px 0}h2{font-size:16px;margin:18px 0 6px}</style>"
           f"<h1>Pilot minute ({sum(x['frames'] for x in report) / FPS:.1f} s)</h1>"
           f'<video src="{final.name}" controls style="max-width:960px;width:100%"></video>' + "".join(cells))
    p = Path(out) / "compare.html"
    p.write_text(doc, encoding="utf-8")
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--p15", type=Path, required=True)
    ap.add_argument("--p16", type=Path, required=True)
    ap.add_argument("--blender", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", default="2560x1440")
    ap.add_argument("--allow-missing", action="store_true")
    a = ap.parse_args(argv)
    w, h = (int(x) for x in a.size.split("x"))
    doc = build({"p15": a.p15, "p16": a.p16}, a.blender, a.out, size=(w, h), allow_missing=a.allow_missing)
    print(json.dumps({k: doc[k] for k in ("video", "seconds", "preview", "sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
