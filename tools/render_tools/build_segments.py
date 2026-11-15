"""Assembler Step 1 (Upgraded for Truce 1914 Rebuild Steps 1-3):
- Respects Whisper-measured [in, out] trim points from edit_points.json (restoring all 14+ KEEP-TRIM shots).
- Prefers a single continuous 2.5D shot clip (production/shot_clips/<sid>.mp4) over split [a-z].mp4 sub-clips so zoom never jumps.
- Composites silent_beat on_screen_text (S08_SH004) and visual_bridge callouts when present.
"""
import json, subprocess, sys, glob, os
from pathlib import Path

R = Path(os.environ.get("TRUCE_EPISODE_DIR", "/Users/vano_tatulashvili/Documents/explainer-engine-truce/episodes/ep_truce_1914"))
W = Path(os.environ.get("TRUCE_WORK_DIR", "/Users/vano_tatulashvili/Documents/hf_truce/work"))
(W / "seg").mkdir(parents=True, exist_ok=True)
T_PATH = Path(os.environ.get("TRUCE_TIMING_JSON", "/Users/vano_tatulashvili/Documents/hf_truce/dl/explainer-engine/demo_truce_1914/full_film_2026-11-15/inputs/clock/timing.json"))
T = json.load(open(T_PATH))
EP = json.load(open(R / "planning/full_film_2026-11-15/edit_points.json"))["clips"]
SC = {s["shot_id"]: s for s in json.load(open(R / "story/production_script.json"))["shots"]}
DIPS = {"S01_SH005", "S02_SH009", "S03_SH010", "S04_SH015", "S05_SH021", "S06_SH012", "S07_SH008", "S08_SH003", "S08_SH004"}
FPS = 24


def run(*a):
    subprocess.run(a, check=True, capture_output=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def build(sid):
    sh = SC[sid]
    route = sh["route"]
    out = W / "seg" / f"{sid}.mp4"
    if out.exists():
        return sid, "cached"
    e = EP.get(sid, {}) if isinstance(EP.get(sid), dict) else {}
    n = int(T["shots"][sid]["frames"])
    src = None
    ss = 0.0
    if route == "video":
        rec = json.load(open(R / "production/video" / f"{sid}.json"))
        src = R / rec["raw_path"]
        raw_d = dur(src)
        ss = float(e["in"]) if "in" in e else (float(rec.get("in_s", 0.0)) if rec.get("clip_spoken") else 0.0)
        if "out" in e and e["out"] != "end":
            t_out = min(raw_d, float(e["out"]))
            n = max(FPS, int(round((t_out - ss) * FPS)))
            T["shots"][sid]["frames"] = n
        elif e.get("out") == "end":
            n = max(FPS, int(round((raw_d - ss) * FPS)))
            T["shots"][sid]["frames"] = n
        avail_frames = max(1, int(round((raw_d - ss) * FPS)))
        pad = max(0, n - avail_frames)
        vf = f"fps={FPS}" + (f",tpad=stop_mode=clone:stop={pad},tmix=frames=3:weights='1 2 1'" if pad > 0 else "")
    else:
        # Step 2 Fix: prefer one continuous full-shot render {sid}.mp4 before falling back to legacy split [a-z].mp4
        full_clip = R / f"production/shot_clips/{sid}.mp4"
        if full_clip.exists():
            src = full_clip
        else:
            parts = sorted(glob.glob(str(R / f"production/shot_clips/{sid}[a-z].mp4"))) or [str(full_clip)]
            lst = W / f"{sid}.concat.txt"
            lst.write_text("".join(f"file '{p}'\n" for p in parts))
            cat = W / f"{sid}.cat.mp4"
            run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(cat))
            src = cat
        pad = max(0, n - int(round(dur(src) * FPS)))
        vf = f"fps={FPS}" + (f",tpad=stop_mode=clone:stop={pad}" if pad > 0 else "")
    vf += ",scale=2560:1440:flags=lanczos,setsar=1,format=yuv420p"
    # Step 3 Fix: render epilogue on-screen text on S08_SH004
    ost = sh.get("on_screen_text")
    if isinstance(ost, str) and ost.strip():
        safe_txt = ost.strip().replace(":", "\\:").replace("'", "\\'")
        vf += f",drawtext=text='{safe_txt}':fontsize=58:fontcolor=0xFCF6E8:box=1:boxcolor=0x0E0D0C@0.62:boxborderw=24:x=(w-text_w)/2:y=(h-text_h)/2"
    if sid in DIPS:
        vf += f",fade=t=out:st={max(0.0, (n - 10) / FPS):.3f}:d={10 / FPS:.3f}"
    run("ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.4f}", "-i", str(src), "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(out))
    return sid, "ok"


if __name__ == "__main__":
    for sid in sys.argv[1:]:
        print(*build(sid), flush=True)
