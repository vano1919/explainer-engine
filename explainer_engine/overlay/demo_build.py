"""Build the free 2-minute overlay demo (OVERLAY_INTEGRATION_RULES section 10), stage by stage, in chunks (RULE-R1: one shot = one chunk).

    python -m explainer_engine.overlay.demo_build specs|bg|overlay|measure|comp|sound|final|ab|all [--shots 2,3] [--work DIR]

Free only: Kokoro scratch narration, procedural sound, the repo's maps, HyperFrames on this machine, ffmpeg. No ElevenLabs, LTX, Gemini API,
pod or Modal. Every stage writes its files and is skipped when its output exists (``--force`` redoes it).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

from explainer_engine.core.store import write_text_atomic
from explainer_engine.overlay import demo_assets as A
from explainer_engine.overlay import demo_bg as BG
from explainer_engine.overlay import demo_mix as MIX
from explainer_engine.overlay import demo_script as D
from explainer_engine.overlay import hyperframes as HF
from explainer_engine.overlay import spec2

HERE = Path(__file__).resolve().parent
PLAN = Path("/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12")
LTX_CLIP = PLAN / "bakeoff_report/ltx_distilled/action_2k.mp4"
NARR = Path("/tmp/claude-0/work/narr/narration.json")
HF_CLI = "/tmp/claude-0/hf/node_modules/.bin/hyperframes"
W, H, FPS = 2560, 1440, 24


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class Work:
    def __init__(self, root: Path):
        self.root = root
        for d in ("specs", "bg", "ov", "comp", "meas", "sound", "cache", "final", "proj"):
            (root / d).mkdir(parents=True, exist_ok=True)

    def p(self, *a) -> Path:
        return self.root.joinpath(*a)


def style() -> dict:
    return json.loads((HERE / "demo_style.json").read_text())


def narration() -> list[dict]:
    """The scratch read: word times from the repo (``demo_words.json``), the wav paths of the local Kokoro render."""
    words = json.loads((HERE / "demo_words.json").read_text())
    wavs = {l["no"]: l["wav"] for l in json.loads(NARR.read_text())}
    return [{**l, "wav": wavs[l["no"]]} for l in words]


def shot_of(no: int) -> dict:
    return next(s for s in D.SHOTS if s["no"] == no)


def make_specs(w: Work, nos: list[int], variant: dict | None = None) -> dict[int, dict]:
    st, narr = style(), narration()
    assets = {pid: A.info(pid, w.p("cache")) for pid in A.PHOTOS}
    out = {}
    for no in nos:
        sh = shot_of(no)
        sp = spec2.build(sh, next((n for n in narr if n["no"] == no), None), st, assets)
        out[no] = sp
        write_text_atomic(w.p("specs", f"shot_{no:02d}.json"), json.dumps(sp, indent=1))
    return out


def load_spec(w: Work, no: int) -> dict:
    return json.loads(w.p("specs", f"shot_{no:02d}.json").read_text())


def stage_bg(w: Work, nos: list[int], force: bool) -> None:
    st = style()["tokens"]
    for no in nos:
        out = w.p("bg", f"bg_{no:02d}.mp4")
        if out.exists() and not force:
            continue
        sh, sp = shot_of(no), load_spec(w, no)
        if sh["route"] == "ltx":
            continue
        t = time.time()
        BG.render(sh, sp, out, w.p("cache"), st)
        log("bg", no, round(time.time() - t, 1), "s")


def project_for(w: Work, sp: dict) -> Path:
    no = sp["shot_no"]
    proj = HF.write_project(sp, w.p("proj", f"s{no:02d}"), "template2.html")
    for p in sp["panels"]:
        if p.get("plate_file"):
            d = proj / "plates"
            d.mkdir(exist_ok=True)
            BG.map_plate(p["view"], (p["box"][2], p["box"][3]), style()["tokens"], d / "p0.png", ss=2)
    return proj


def stage_overlay(w: Work, nos: list[int], force: bool) -> None:
    os.environ["EXPLAINER_HYPERFRAMES"] = HF_CLI
    for no in nos:
        sp = load_spec(w, no)
        if not sp["items"]:
            continue
        out = w.p("ov", f"ov_{no:02d}.webm")
        if out.exists() and not force:
            continue
        proj = project_for(w, sp)
        t = time.time()
        HF.render_overlay(proj, out, fmt="webm", quality="looks")
        log("overlay", no, round(time.time() - t, 1), "s")


def stage_measure(w: Work, nos: list[int], force: bool) -> None:
    """The settled layout of every item (frame pixels), read from the real composition in headless Chrome (node + playwright)."""
    for no in nos:
        sp = load_spec(w, no)
        out = w.p("meas", f"boxes_{no:02d}.json")
        if not sp["items"] or (out.exists() and not force):
            continue
        proj = w.p("proj", f"s{no:02d}")
        if not (proj / "index.html").exists():
            proj = project_for(w, sp)
        env = {**os.environ, "NODE_PATH": subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()}
        subprocess.run(["node", str(HERE / "hyperframes" / "measure.cjs"), str(proj / "index.html"), str(out)], check=True, env=env)
        log("measure", no, len(json.loads(out.read_text())["boxes"]), "boxes")


def mask_png(box, radius, out: Path) -> Path:
    im = Image.new("L", (box[2], box[3]), 0)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, box[2] - 1, box[3] - 1), radius=radius, fill=255)
    im.save(out)
    return out


def compose_cmd(sp: dict, bg: Path, ov: Path | None, masks: list[Path], out: Path) -> list[str]:
    n = sp["frames"]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(bg)]
    idx = 1
    chain, cur = [], "[0:v]"
    glass = [p for p in sp["panels"] if p["surface"] == "glass" and p["start"] is not None]
    for k, p in enumerate(glass):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(masks[k])]
        x, y, w_, h_ = p["box"]
        s, e = p["start"] / FPS, (p["end"] - spec2.EXIT) / FPS
        chain += [f"{cur}split[a{k}][b{k}]",
                  f"[b{k}]crop={w_}:{h_}:{x}:{y},gblur=sigma={p['blur_px']}:steps=2,format=rgba[bl{k}]",
                  f"[{idx}:v]format=gray[mk{k}]",
                  f"[bl{k}][mk{k}]alphamerge,fade=t=in:st={s:.4f}:d={spec2.ENTER / FPS:.4f}:alpha=1,fade=t=out:st={e:.4f}:d={spec2.EXIT / FPS:.4f}:alpha=1[bf{k}]",
                  f"[a{k}][bf{k}]overlay={x}:{y}:format=auto[g{k}]"]
        cur = f"[g{k}]"
        idx += 1
    if ov is not None:
        cmd += ["-c:v", "libvpx-vp9", "-i", str(ov)]
        chain.append(f"{cur}[{idx}:v]overlay=0:0:format=auto:shortest=1[o]")
    else:
        chain.append(f"{cur}null[o]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[o]", "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)]
    return cmd


def stage_comp(w: Work, nos: list[int], force: bool, tag: str = "") -> None:
    for no in nos:
        out = w.p("comp", f"comp_{no:02d}{tag}.mp4")
        if out.exists() and not force:
            continue
        sp = load_spec(w, no)
        if shot_of(no)["route"] == "ltx":
            t = time.time()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(LTX_CLIP), "-t", str(sp["frames"] / FPS), "-an", "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}",
                            "-frames:v", str(sp["frames"]), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(out)], check=True)
            log("comp", no, "LTX clip, no overlay", round(time.time() - t, 1), "s")
            continue
        glass = [p for p in sp["panels"] if p["surface"] == "glass" and p["start"] is not None]
        masks = [mask_png(p["box"], p["radius"], w.p("comp", f"mask_{no:02d}_{p['id']}.png")) for p in glass]
        ov = w.p("ov", f"ov_{no:02d}.webm") if sp["items"] else None
        t = time.time()
        subprocess.run(compose_cmd(sp, w.p("bg", f"bg_{no:02d}.mp4"), ov, masks, out), check=True)
        log("comp", no, round(time.time() - t, 1), "s")


def stage_sound(w: Work, force: bool) -> dict:
    rep = w.p("sound", "mix_report.json")
    specs = [load_spec(w, s["no"]) for s in D.SHOTS]
    res = MIX.build(D.SHOTS, specs, narration(), LTX_CLIP, w.p("sound"))
    write_text_atomic(rep, json.dumps(res["report"], indent=1))
    mx = MIX.mix_range(res["stems"], 0, sum(s["dur"] for s in D.SHOTS))
    sf.write(w.p("sound", "mix.wav"), mx, MIX.SR)
    log("sound", json.dumps({k: res["report"][k] for k in ("groups", "sfx_under_scene_lu")}))
    return res


GRADE = "eq=saturation=0.97:contrast=1.03:gamma=0.98,noise=alls=3:allf=t+u"      # the episode's last pass: grade and grain over the COMPOSITE (OV-12)


def label_clip(src: Path, text: str, out: Path) -> None:
    """A plain caption on an A/B clip (an annotation for the viewer of the comparison, not part of the demo's overlay)."""
    font = HERE / "hyperframes" / "fonts" / "Inter.ttf"
    dt = f"drawtext=fontfile={font}:text='{text}':x=60:y=h-110:fontsize=54:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", dt + "," + GRADE, "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(out)], check=True)


def stage_ab(w: Work, force: bool) -> None:
    """ab_surface.mp4: shot 6 as glass and as bare (10 s each); ab_sound.mp4: shot 2 with the overlay sounds at the OV-53 level and 6 LU louder."""
    st, narr = style(), narration()
    assets = {pid: A.info(pid, w.p("cache")) for pid in A.PHOTOS}
    sh = {**shot_of(6), "variant": "bare"}
    sp = spec2.build(sh, next(n for n in narr if n["no"] == 6), st, assets)
    sp["shot_no"] = 6
    write_text_atomic(w.p("specs", "shot_06b.json"), json.dumps(sp, indent=1))
    os.environ["EXPLAINER_HYPERFRAMES"] = HF_CLI
    ov = w.p("ov", "ov_06b.webm")
    if force or not ov.exists():
        proj = HF.write_project(sp, w.p("proj", "s06b"), "template2.html")
        HF.render_overlay(proj, ov, fmt="webm", quality="looks")
    comp = w.p("comp", "comp_06b.mp4")
    if force or not comp.exists():
        subprocess.run(compose_cmd(sp, w.p("bg", "bg_06.mp4"), ov, [], comp), check=True)
    stems = {k: sf.read(w.p("sound", f"stem_{k}.wav"), dtype="float32")[0] for k in ("narr", "amb", "sfx", "clip")}
    t6 = MIX.starts(D.SHOTS)[6]
    t2 = MIX.starts(D.SHOTS)[2]
    ab = w.p("final", "ab_surface.mp4")
    a_, b_ = w.p("final", "ab_a.mp4"), w.p("final", "ab_b.mp4")
    label_clip(w.p("comp", "comp_06.mp4"), "A: glass inset", a_)
    label_clip(comp, "B: bare, no panel", b_)
    audio = MIX.mix_range(stems, t6, t6 + 10)
    sf.write(w.p("final", "ab_surface.wav"), np.concatenate([audio, audio]), MIX.SR)
    lst = w.p("final", "ab_surface.txt")
    lst.write_text(f"file '{a_}'\nfile '{b_}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(w.p("final", "ab_surface.wav")), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", str(ab)], check=True)
    c_, d_ = w.p("final", "ab_c.mp4"), w.p("final", "ab_d.mp4")
    label_clip(w.p("comp", "comp_02.mp4"), "A: overlay sounds at the OV-53 level", c_)
    label_clip(w.p("comp", "comp_02.mp4"), "B: overlay sounds 6 LU louder", d_)
    n2 = D.SHOTS[1]["dur"]
    sf.write(w.p("final", "ab_sound.wav"), np.concatenate([MIX.mix_range(stems, t2, t2 + n2), MIX.mix_range(stems, t2, t2 + n2, sfx_db=6.0)]), MIX.SR)
    lst2 = w.p("final", "ab_sound.txt")
    lst2.write_text(f"file '{c_}'\nfile '{d_}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst2), "-i", str(w.p("final", "ab_sound.wav")), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", str(w.p("final", "ab_sound.mp4"))], check=True)
    log("ab files written")


def stage_final(w: Work, force: bool) -> Path:
    out = w.p("final", "demo_overlay_2min.mp4")
    lst = w.p("final", "concat.txt")
    lst.write_text("".join(f"file '{w.p('comp', f'comp_{s['no']:02d}.mp4')}'\n" for s in D.SHOTS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(w.p("sound", "mix.wav")), "-vf", GRADE, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)]
    t = time.time()
    subprocess.run(cmd, check=True)
    write_text_atomic(w.p("final", "render_order.json"), json.dumps({"order": ["composite", "grade"], "grade": GRADE, "chunks": [f"comp_{s['no']:02d}.mp4" for s in D.SHOTS]}))
    log("final", round(time.time() - t, 1), "s")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--shots", default="")
    ap.add_argument("--work", default="/tmp/claude-0/work/demo")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    w = Work(Path(a.work))
    nos = [int(x) for x in a.shots.split(",") if x] or [s["no"] for s in D.SHOTS]
    stages = ["specs", "bg", "overlay", "measure", "comp", "sound", "final", "ab", "report"] if a.stage == "all" else [a.stage]
    for s in stages:
        log("stage", s, nos if s not in ("sound", "final") else "")
        if s == "specs":
            make_specs(w, nos)
        elif s == "bg":
            stage_bg(w, nos, a.force)
        elif s == "overlay":
            stage_overlay(w, nos, a.force)
        elif s == "measure":
            stage_measure(w, nos, a.force)
        elif s == "comp":
            stage_comp(w, nos, a.force)
        elif s == "sound":
            stage_sound(w, a.force)
        elif s == "final":
            stage_final(w, a.force)
        elif s == "ab":
            stage_ab(w, a.force)
        elif s == "report":
            from explainer_engine.overlay import demo_report
            rep = demo_report.run(w)
            log("report", len(rep["fails"]), "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
