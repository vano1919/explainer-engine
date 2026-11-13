"""The route-test verdict page (guide step 4, D-116): one card per generated clip of the J5 / J2 / J4 routes, with the same
numbers on every card, so the creator compares the routes on facts and Fable writes the direct evaluation (OR-25).

    python -m explainer_engine.qa.verdict_page <out dir> --ltx <pod out dir> [--jobs ltx_jobs.json] [--j5 <dir of J5 mp4s>]
           [--background <dir of overnight Blender pngs/mp4s>] [--first-frames <dir>] [--ref rhythm.json] [--usd-per-hour 0.89]

Per clip (free, CPU, ``training/video_qa``; nothing here is a threshold of its own, D-59):
- identity: the Qwen first frame against the clip's frame 0 and its last frame (``shot_identity``: palette distance, ink ratio =
  line weight, and the LT-60/61 REVIEW rows of ``judge_identity``); the mean-colour CIE76 dE of the last frame against the first
  frame (``blender/grade.delta_e``; the eras-sheet dE when ``--style-ref`` names that sheet);
- line share: the share of ink pixels (BP-166 ink_max) on the first and last frame;
- motion: hold share and speed (``rhythm``) against the cartoon footage reference when ``--ref`` is given (LT-56/57), flicker,
  morphing and line loss (``judge``: LT-51..54);
- cost: seconds per clip from the pod's sidecar (``ltx/<job>.json``) and dollars at ``--usd-per-hour``;
- upscale: ``finish/upscale.compare`` of ``ltx/<job>.mp4`` against ``ltx_up/<job>.mp4`` when both exist.

Writes ``VERDICT.html`` (cards grouped by route and shot, three frames each) and ``verdict.json`` (every number) into ``out``.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROUTES = ("J5", "J2", "J4", "background")


def _ink_share(frame) -> float:
    from explainer_engine.standards import sourced_rules as SR
    from explainer_engine.training import video_qa as VQ
    return round(float((VQ._gray(frame) < SR.T("BP-166", "ink_max")).mean()), 4)


def _clean(d: dict) -> dict:
    """Drops the empty hero table and turns NaN (a flat frame's correlation) into None, so the JSON stays valid."""
    return {k: (None if isinstance(v, float) and v != v else v) for k, v in d.items() if k != "heroes"}


def _mean_rgb(frame) -> list[float]:
    import numpy as np
    return [float(v) / 255 for v in np.asarray(frame, dtype=float).reshape(-1, 3).mean(axis=0)]


def _image(path, like):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB").resize((like.shape[1], like.shape[0]), Image.LANCZOS))


def measure(clip: Path, *, first_frame: Path | None = None, style_ref: Path | None = None, ref: dict | None = None) -> dict:
    """Every number of one card. ``clip`` is an mp4 (or a single png for a still background row)."""
    from explainer_engine.blender import grade
    from explainer_engine.training import video_qa as VQ
    if clip.suffix.lower() == ".png":
        import numpy as np
        from PIL import Image
        f = np.asarray(Image.open(clip).convert("RGB"))
        w = VQ.SMALL
        f = np.asarray(Image.fromarray(f).resize((w, int(round(f.shape[0] * w / f.shape[1])))))
        frames, fps = np.stack([f]), 24.0
    else:
        frames, fps = VQ.read_video(clip)
    if len(frames) == 0:
        raise ValueError(f"{clip}: no frames")
    m = {"frames": int(len(frames)), "seconds": round(len(frames) / fps, 2),
         "line_share": {"first": _ink_share(frames[0]), "last": _ink_share(frames[-1])}}
    findings = []
    if len(frames) > 1:
        a = VQ.analyse(frames, fps)
        m["motion"] = {"flicker_max": a["flicker_max"], "morph_p95": a["morph_p95"], "edges_min_vs_start": a["edges_min_vs_start"],
                       "breaks_at_second": a["breaks_at_second"], **a["rhythm"]}
        findings += VQ.judge(a, ref)
    if len(frames) > 1:
        m["drift"] = VQ.shot_identity(frames[0], frames[-1])
        findings += VQ.judge_identity(m["drift"], "first -> last frame")
        m["drift"] = _clean(m["drift"])
    if first_frame and Path(first_frame).exists():
        ff = _image(first_frame, frames[0])
        ident = VQ.shot_identity(ff, frames[0])
        findings += VQ.judge_identity(ident, "Qwen first frame -> clip frame 0")
        m["identity"] = _clean(ident)
        m["delta_e_last_vs_first_frame"] = round(grade.delta_e(_mean_rgb(frames[-1]), _mean_rgb(ff)), 3)
    if style_ref and Path(style_ref).exists():
        m["delta_e_vs_style_ref"] = round(grade.delta_e(_mean_rgb(frames[len(frames) // 2]),
                                                        _mean_rgb(_image(style_ref, frames[0]))), 3)
    m["findings"] = [f for f in findings if f.get("status") != "PASS"]
    m["_thumbs"] = [frames[0], frames[len(frames) // 2], frames[-1]]
    return m


def cards(ltx: Path | None, *, jobs: dict | None = None, j5: Path | None = None, background: Path | None = None,
          first_frames: Path | None = None) -> list[dict]:
    """The card list before measuring: route, shot, label, clip path, its first frame and its pod sidecar."""
    out = []
    by_id = {j["id"]: j for j in (jobs or {}).get("jobs", [])}
    if ltx and (Path(ltx) / "ltx").is_dir():
        for mp4 in sorted((Path(ltx) / "ltx").glob("*.mp4")):
            jid = mp4.stem
            job = by_id.get(jid, {})
            side_p = mp4.with_suffix(".json")
            side = json.loads(side_p.read_text(encoding="utf-8")) if side_p.exists() else {}
            ff = (Path(first_frames) / f"{job['clip_id']}.png") if first_frames and job else None
            up = Path(ltx) / "ltx_up" / mp4.name
            out.append({"route": job.get("route", "J2/J4"), "shot": job.get("shot_id", jid.split(".")[0]), "label": jid,
                        "base": job.get("base"), "variant": job.get("variant"), "seed": job.get("seed"), "clip": mp4,
                        "first_frame": ff, "seconds_gen": side.get("seconds"), "upscaled": up if up.exists() else None})
    for route, folder in (("J5", j5), ("background", background)):
        if folder and Path(folder).is_dir():
            for p in sorted([*Path(folder).glob("*.mp4"), *Path(folder).glob("*.png")]):
                shot = p.stem.split(".")[0].split("_")[0]
                ff = (Path(first_frames) / f"{p.stem}.png") if first_frames and route == "J5" else None
                out.append({"route": route, "shot": shot, "label": p.stem, "clip": p, "first_frame": ff,
                            "seconds_gen": None, "upscaled": None})
    return out


def build(out: Path, rows: list[dict], *, style_ref: Path | None = None, ref: dict | None = None,
          usd_per_hour: float | None = None) -> dict:
    from PIL import Image

    from explainer_engine.finish import upscale
    out = Path(out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    doc = {"schema": "route_verdict/1", "usd_per_hour": usd_per_hour, "cards": []}
    for r in rows:
        m = measure(Path(r["clip"]), first_frame=r.get("first_frame"), style_ref=style_ref, ref=ref)
        thumbs = []
        for k, f in enumerate(m.pop("_thumbs")):
            name = f"thumbs/{r['label']}_{k}.jpg"
            Image.fromarray(f).save(out / name, quality=85)
            thumbs.append(name)
        card = {k: (str(v) if isinstance(v, Path) else v) for k, v in r.items()}
        card.update(metrics=m, thumbs=thumbs)
        if r.get("seconds_gen") is not None and usd_per_hour:
            card["usd"] = round(r["seconds_gen"] * usd_per_hour / 3600, 3)
        if r.get("upscaled"):
            card["upscale"] = upscale.compare(r["clip"], r["upscaled"], r.get("first_frame") if r.get("first_frame") and
                                              Path(r["first_frame"]).exists() else None)
        doc["cards"].append(card)
    (out / "verdict.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    (out / "VERDICT.html").write_text(render_html(doc), encoding="utf-8")
    return doc


def _num(v):
    return "–" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def _card_html(c: dict) -> str:
    m = c["metrics"]
    mo, idt = m.get("motion") or {}, m.get("identity") or {}
    rows = [("identity: palette (Qwen frame → clip)", idt.get("palette_dist")), ("identity: ink × (line weight)", idt.get("ink_ratio")),
            ("drift: palette first → last", (m.get("drift") or {}).get("palette_dist")), ("ΔE last vs first frame", m.get("delta_e_last_vs_first_frame")),
            ("ΔE vs style sheet", m.get("delta_e_vs_style_ref")), ("line share first / last",
                                                                  f"{_num(m['line_share']['first'])} / {_num(m['line_share']['last'])}"),
            ("hold share", mo.get("hold_share")), ("speed p90 (widths/s)", mo.get("speed_p90")), ("flicker max", mo.get("flicker_max")),
            ("morph p95", mo.get("morph_p95")), ("seconds per clip", c.get("seconds_gen")), ("US$ per clip", c.get("usd"))]
    up = c.get("upscale")
    if up:
        f0 = up["frames"][0]
        rows.append(("upscale ink × / sharp ×", f"{_num(f0['ink_ratio'])} / {_num(f0['sharp_ratio'])}"))
    table = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(_num(v) if not isinstance(v, str) else v)}</td></tr>"
                    for k, v in rows)
    finds = "".join(f"<li>{html.escape(f['rule'])} {html.escape(f['status'])}: {html.escape(f['msg'])}</li>"
                    for f in m["findings"])
    imgs = "".join(f'<img src="{html.escape(t)}" alt="">' for t in c["thumbs"])
    meta = " · ".join(str(x) for x in (c.get("base"), c.get("variant"), c.get("seed") and f"seed {c['seed']}") if x)
    return (f'<article class="card"><h3>{html.escape(c["label"])}</h3><p class="meta">{html.escape(meta)}</p>'
            f'<div class="strip">{imgs}</div><table>{table}</table>'
            + (f'<ul class="finds">{finds}</ul>' if finds else '<p class="ok">no REVIEW row</p>') + "</article>")


def render_html(doc: dict) -> str:
    groups = []
    for route in ROUTES + ("J2/J4",):
        cs = [c for c in doc["cards"] if c["route"] == route]
        if not cs:
            continue
        shots = sorted({c["shot"] for c in cs})
        body = "".join(f"<h2>{html.escape(route)} · {html.escape(s)}</h2><div class='grid'>"
                       + "".join(_card_html(c) for c in cs if c["shot"] == s) + "</div>" for s in shots)
        groups.append(f"<section>{body}</section>")
    css = (":root{--bg:#f6f3ec;--fg:#1d1b18;--mut:#6b655c;--card:#fff;--line:#ddd5c8}"
           "@media (prefers-color-scheme:dark){:root{--bg:#17150f;--fg:#ece6da;--mut:#a39b8d;--card:#221f18;--line:#3a352b}}"
           "body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0;padding:16px}"
           "h1{font-size:20px}h2{font-size:16px;margin:24px 0 8px}.grid{display:grid;gap:12px;"
           "grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}.card{background:var(--card);border:1px solid var(--line);"
           "border-radius:8px;padding:10px}.card h3{font-size:13px;margin:0;word-break:break-all}.meta{color:var(--mut);margin:2px 0 6px}"
           ".strip{display:flex;gap:2px}.strip img{width:33%;height:auto;border-radius:3px}table{width:100%;border-collapse:collapse;"
           "margin-top:6px;font-size:12px}td{border-top:1px solid var(--line);padding:2px 4px}td:last-child{text-align:right;"
           "font-variant-numeric:tabular-nums}.finds{font-size:12px;color:#a4432c;padding-left:18px}.ok{font-size:12px;color:var(--mut)}")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
            f"initial-scale=1'><title>Route test verdict</title><style>{css}</style></head><body><h1>Route test: J5 · J2 · J4</h1>"
            f"<p class='meta'>Every number comes from training/video_qa and finish/upscale; REVIEW rows only, no route is ranked "
            f"here (the creator picks, guide step 4).</p>{''.join(groups)}</body></html>")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--ltx", type=Path)
    ap.add_argument("--jobs", type=Path)
    ap.add_argument("--j5", type=Path)
    ap.add_argument("--background", type=Path)
    ap.add_argument("--first-frames", type=Path)
    ap.add_argument("--style-ref", type=Path)
    ap.add_argument("--ref", type=Path, help="footage rhythm (training footage-rhythm) for LT-56/57")
    ap.add_argument("--usd-per-hour", type=float)
    a = ap.parse_args(argv)
    jobs = json.loads(a.jobs.read_text(encoding="utf-8")) if a.jobs else None
    rows = cards(a.ltx, jobs=jobs, j5=a.j5, background=a.background, first_frames=a.first_frames)
    if not rows:
        print("no clips found", file=sys.stderr)
        return 1
    ref = json.loads(a.ref.read_text(encoding="utf-8")) if a.ref else None
    doc = build(a.out, rows, style_ref=a.style_ref, ref=ref, usd_per_hour=a.usd_per_hour)
    print(f"{len(doc['cards'])} cards -> {a.out / 'VERDICT.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
