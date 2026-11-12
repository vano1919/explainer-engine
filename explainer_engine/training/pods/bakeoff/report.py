"""The bake-off's free half (local, no GPU): every clip of a run is fetched from HF, upscaled to the delivery frame
(2560x1440 at 24 fps, ``finish/upscale``: centre crop, Lanczos, cas 0.4; LTX keeps its own sound), measured, and put in one
report beside its price.

    python -m explainer_engine.training.pods.bakeoff.report <run id> --out <folder> [--upload]

What is measured per clip (numbers only, no threshold: none is sourced yet, D-59; the creator's eyes decide):
- ``start_diff``: mean absolute difference of frame 0 to the start picture (0..255), how faithfully the clip starts.
- ``motion``: mean absolute difference between neighbouring frames (0..255), how much moves.
- ``longest_still``: the longest run of frames without visible change (BP-164's frozen threshold), a frozen picture.
- ``flicker``: the standard deviation of the frame-to-frame change of mean brightness, a pumping picture.
- ``sharpness``: the mean Laplacian variance of three frames of the 2K file, detail after the upscale.
- ``drift``: the CIE76 distance of the last frame's mean colour to the start picture's, how far the look wanders.
The start picture is cropped to each variant's own aspect before both are scaled to the analysis size (Fable audit B5), and
every 2K file is conformed to 24 fps like the episode's timeline (audit B6; a 16 fps Wan clip repeats frames, no new pixels).
Cost per variant: the ledger's settled amount (the measured wall seconds of the call, start-up included) when the ledger is
given, else the worker's ``body_s`` plus the plan's cold start; a variant that left a beat but no ``measured.json`` is charged at
its cap and marked (audit A3). Split over the shots by their generation seconds. Modal's usage page is the bill of record.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from explainer_engine.training.pods.bakeoff import modal_bakeoff as B

FROZEN = 0.4   # BP-164 frozen_diff_max, the same "no visible change" step the Wan QA uses
ANALYSIS = (320, 180)


def read_frames(path, size=ANALYSIS):
    import cv2
    cap, out = cv2.VideoCapture(str(path)), []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2RGB), size, interpolation=cv2.INTER_AREA).astype(np.float32))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return out, fps


def metrics(frames, start=None) -> dict:
    """The motion numbers of one clip's frames (RGB float arrays of one size) against its start picture (same size)."""
    if not frames:
        return {"frames": 0}
    diffs = [float(np.abs(b - a).mean()) for a, b in zip(frames, frames[1:])]
    longest, run = 1, 1
    for d in diffs:
        run = run + 1 if d < FROZEN else 1
        longest = max(longest, run)
    luma = [float(f.mean()) for f in frames]
    out = {"frames": len(frames), "motion": round(float(np.mean(diffs)) if diffs else 0.0, 3), "longest_still": longest,
           "flicker": round(float(np.std(np.diff(luma))) if len(luma) > 2 else 0.0, 3)}
    if start is not None:
        out["start_diff"] = round(float(np.abs(frames[0] - start).mean()), 2)
        out["drift"] = round(delta_e([float(x) / 255 for x in frames[-1].reshape(-1, 3).mean(0)],
                                           [float(x) / 255 for x in start.reshape(-1, 3).mean(0)]), 3)
    return out


def _lab(srgb):
    """CIE L*a*b* (D65) of a display sRGB triple in 0..1."""
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (min(max(x, 0.0), 1.0) for x in srgb)]
    r, g, b = lin
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a, b) -> float:
    """CIE76 dE between two display sRGB triples."""
    return sum((p - q) ** 2 for p, q in zip(_lab(a), _lab(b))) ** 0.5


def sharpness(path) -> float:
    import cv2
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    vals = []
    for i in sorted({0, n // 2, max(0, n - 1)}):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = cap.read()
        if ok:
            vals.append(float(cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()))
    cap.release()
    return round(float(np.mean(vals)), 1) if vals else 0.0


def ledger_usd(ledger_data, rid) -> dict:
    """Settled money per variant of one run from the bake-off ledger (``core/ledger.Run`` data)."""
    out = {}
    for item, r in (ledger_data or {}).get("reserved", {}).items():
        parts = item.split("/")
        if len(parts) >= 3 and parts[0] == "bakeoff" and parts[1] == rid and r.get("settled"):
            out[parts[2]] = round(out.get(parts[2], 0.0) + float(r["amount"]), 4)
    return out


def costs(plan, measured: dict, settled: dict | None = None, no_record=()) -> dict:
    """Per variant: the ledger's settled money, else the container seconds + the cold start; a variant with a beat and no
    record at its cap (the money it may have cost). Split over its shots by generation time."""
    out = {}
    for vid in list(measured) + [x for x in no_record if x not in measured]:
        v, m = B.variant(plan, vid), measured.get(vid)
        rate = B.usd_per_h(v["gpu"], v["cpu"], v["memory_gib"])
        if m is None:
            out[vid] = {"usd": float(v["cap_usd"]), "seconds": None, "usd_per_h": rate, "estimate_usd": v["estimate_usd"],
                        "cap_usd": v["cap_usd"], "state": "NO_RECORD (charged at its cap)", "per_shot_usd": {}, "source": "cap"}
            continue
        secs = float(m.get("body_s") or 0.0) + float(plan["cold_start_s"])
        if settled and vid in settled:
            total, src = settled[vid], "ledger"
        else:
            total, src = round(secs * rate / 3600.0, 4), "body_s + cold start"
        gen = {r["shot"]: float(r.get("gen_s") or 0.0) for r in m.get("shots") or []}
        g = sum(gen.values()) or 1.0
        out[vid] = {"usd": total, "seconds": round(secs, 1), "usd_per_h": rate, "estimate_usd": v["estimate_usd"],
                    "cap_usd": v["cap_usd"], "state": m.get("state"), "source": src,
                    "per_shot_usd": {s: round(total * x / g, 4) for s, x in gen.items()}}
    return out


def has_audio(path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        str(path)], capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def to_2k(src: Path, dst: Path, fps: int = 24) -> Path:
    """The delivery frame (finish/upscale, cas 0.4) at the timeline's rate (``wan_adapter.conform``); a clip with its own sound
    keeps it."""
    from explainer_engine.aivideo import wan_adapter as WA
    from explainer_engine.finish import upscale as U
    silent = dst.with_name(dst.stem + ".video.mp4")
    up = dst.with_name(dst.stem + ".up.mp4")
    U.upscale(src, up, sharpen="cas")
    WA.conform(up, silent, fps=fps, width=2560, height=1440)
    up.unlink()
    if has_audio(src):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(src), "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"audio mux failed: {r.stderr[-200:]}")
        silent.unlink()
    else:
        silent.replace(dst)
    return dst


def contact_sheet(rows, out_png: Path, thumb=(384, 216)):
    """One row per clip: its first, middle and last frame, labelled by variant and shot."""
    from PIL import Image, ImageDraw
    import cv2
    sheet = Image.new("RGB", (thumb[0] * 3 + 260, thumb[1] * len(rows)), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        cap = cv2.VideoCapture(str(r["file_2k"]))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
        for j, k in enumerate((0, n // 2, n - 1)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, k)
            ok, f = cap.read()
            if ok:
                im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize(thumb)
                sheet.paste(im, (260 + j * thumb[0], i * thumb[1]))
        cap.release()
        d.text((10, i * thumb[1] + 10), f"{r['variant']}\n{r['shot']}\n${r.get('usd', 0):.3f}", fill=(235, 235, 235))
    sheet.save(out_png)
    return out_png


def build(plan, rid, folder: Path, fetch, upload=None, ledger_data=None) -> dict:
    """Fetch, upscale, measure and report one run. ``fetch(hf_path, local)`` downloads a file (raises when it is not there);
    ``upload(local, hf_path)`` puts the 2K files and the report back on HF; ``ledger_data`` is the bake-off ledger's data."""
    from PIL import Image
    folder.mkdir(parents=True, exist_ok=True)
    measured, rows, no_record = {}, [], []
    for v in plan["variants"]:
        base = f"{plan['hf_out']}/{rid}/{v['id']}"
        try:
            local = fetch(f"{base}/measured.json", folder / v["id"] / "measured.json")
            measured[v["id"]] = json.loads(Path(local).read_text())
        except Exception:  # noqa: BLE001 - this variant has not run, or it died: a beat without a record costs up to its cap
            try:
                fetch(f"{base}/beat.json", folder / v["id"] / "beat.json")
                no_record.append(v["id"])
            except Exception:  # noqa: BLE001
                pass
            continue
        for s in plan["shots"]:
            try:
                raw = Path(fetch(f"{base}/{s['id']}.mp4", folder / v["id"] / f"{s['id']}.mp4"))
            except Exception:  # noqa: BLE001
                rows.append({"variant": v["id"], "shot": s["id"], "state": "missing"})
                continue
            pic = Path(fetch(s["picture"], folder / "in" / Path(s["picture"]).name))
            start = np.asarray(B.fit_picture(Image.open(pic), v["width"], v["height"]).resize(ANALYSIS), dtype=np.float32)
            frames, fps = read_frames(raw)
            two_k = to_2k(raw, folder / v["id"] / f"{s['id']}_2k.mp4", fps=int(plan["delivery"]["fps"]))
            row = {"variant": v["id"], "shot": s["id"], "state": "made", "native": f"{v['width']}x{v['height']}@{v['fps']}",
                   "seconds": round(len(frames) / fps, 2) if fps else None, "sound": has_audio(raw), "file_2k": str(two_k),
                   **metrics(frames, start), "sharpness_2k": sharpness(two_k)}
            if upload:
                row["hf_2k"] = upload(two_k, f"{base}/{s['id']}_2k.mp4")
            rows.append(row)
    money = costs(plan, measured, ledger_usd(ledger_data, rid) if ledger_data else None, no_record)
    for r in rows:
        r["usd"] = (money.get(r["variant"]) or {}).get("per_shot_usd", {}).get(r["shot"])
    made = [r for r in rows if r.get("state") == "made"]
    sheet = contact_sheet(made, folder / "contact_sheet.png") if made else None
    rep = {"schema": "video_bakeoff_report/2", "run_id": rid, "plan_sha256": B.plan_sha(), "rows": rows, "money": money,
           "total_usd": round(sum(m["usd"] for m in money.values()), 4), "contact_sheet": str(sheet) if sheet else None}
    (folder / "report.json").write_text(json.dumps(rep, indent=1))
    (folder / "report.md").write_text(markdown(rep))
    if upload:
        for f in ("report.json", "report.md") + (("contact_sheet.png",) if sheet else ()):
            upload(folder / f, f"{plan['hf_out']}/{rid}/{f}")
    return rep


def markdown(rep) -> str:
    lines = [f"# Video bake-off {rep['run_id']}", "", f"Total (container seconds at the dated price): ${rep['total_usd']:.3f}", "",
             "| variant | shot | native | s | sound | $ | start diff | motion | longest still | flicker | drift | sharp 2K |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rep["rows"]:
        if r.get("state") != "made":
            lines.append(f"| {r['variant']} | {r['shot']} | {r.get('state')} | | | | | | | | | |")
            continue
        lines.append(f"| {r['variant']} | {r['shot']} | {r['native']} | {r['seconds']} | {'yes' if r['sound'] else 'no'} | "
                     f"{(r.get('usd') or 0):.3f} | {r.get('start_diff')} | {r['motion']} | {r['longest_still']} | {r['flicker']} | "
                     f"{r.get('drift')} | {r['sharpness_2k']} |")
    lines += ["", "| variant | state | billed est. $ | estimate $ | cap $ | seconds |", "|---|---|---|---|---|---|"]
    for vid, m in rep["money"].items():
        lines.append(f"| {vid} | {m['state']} | {m['usd']:.3f} | {m['estimate_usd']} | {m['cap_usd']} | {m['seconds']} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bakeoff.report")
    ap.add_argument("run_id")
    ap.add_argument("--out", required=True)
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args(argv)
    import os
    from huggingface_hub import HfApi, hf_hub_download
    plan = B.load_plan()
    tok = os.environ.get("HF_TOKEN")

    def fetch(path, local):
        p = hf_hub_download(plan["hf_repo"], path, repo_type="dataset", token=tok, local_dir=str(Path(a.out) / "_hf"))
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        Path(local).write_bytes(Path(p).read_bytes())
        return local

    def upload(local, path):
        HfApi(token=tok).upload_file(path_or_fileobj=str(local), path_in_repo=path, repo_id=plan["hf_repo"], repo_type="dataset",
                                     commit_message=f"bakeoff report {Path(local).name}")
        return f"https://huggingface.co/datasets/{plan['hf_repo']}/blob/main/{path}"
    lp = Path(plan["ledger"]["path"])
    led = json.loads(lp.read_text()) if lp.is_file() else None
    rep = build(plan, a.run_id, Path(a.out), fetch, upload if a.upload else None, led)
    print(json.dumps({"total_usd": rep["total_usd"], "rows": len(rep["rows"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
