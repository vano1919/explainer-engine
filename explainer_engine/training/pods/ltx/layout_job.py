"""The ``layout_job/1`` of the Layout-To-Render worker (S3, brief BRIEFS_S3_T0B_AND_T1_CARD_ka.md item 1): the job format, its free
validation, the ``ltx_pipelines.ic_lora`` command, the hand-over frame of a chain, and the sha256-named batch tar the container fetches.

Pure: stdlib (numpy and PIL only inside the functions that need them; ffprobe/ffmpeg through an injectable ``sh``), no ``modal``, no repo
import, so the same file runs on the creator's side (``pack``), in the CPU rehearsal and inside the container (the image holds it
beside ``modal_layout_jobs.py``; see ``docs/LTX_LAYOUT_JOBS.md``).

A job (all paths relative to the folder the job file is in, so the folder packs as is)::

    {"schema": "layout_job/1", "shot_id": "t1_a", "seed": 42, "seconds": 10.0, "fps": 24, "width": 1280, "height": 704,
     "layout_mp4": "t0_a1/layout.mp4", "layout_sha256": "<64 hex>", "layout_report": "t0_a1/report.json",   # report optional
     "first_picture": "t1/first.png", "first_picture_sha256": "<64 hex>",                                    # the Gemini picture
     "motion_prompt": "One or two sentences about the finished shot.", "film_line": "optional film_style.prompt_line",
     "chain": [{"shot_id": "t1_a2", "seed": 43, "seconds": 10.0, "layout_mp4": ..., "layout_sha256": ..., "motion_prompt": ...,
                "hop": 1, "continue_frame": {"pick": "best_tail", "window_s": 1.5}}],       # hop = depth in the chain (CT-1)
     "hop3_word": "<cmsg id of the owner's yes>"}                                           # only a hop of 3 or more needs it

A chain row may carry ``"start": "first_picture"`` (a sibling: the same first picture, its own prompt/film_line, hop 0, no hand-over;
the T1 pair A and B) and its own ``film_line`` (else the job's applies).

Rules (each a ``problem`` that refuses the job; warnings are recorded, never block):
- LR-1 size 1280x704 at 24 fps (CH-02, D-133), sides in 64, frames 8k+1 and not above the launch's ``native.max_frames``;
- LR-2 the layout file's sha256 is the one in the job (and in its ``report.json`` ``video.sha256`` when named), and the layout is
  really 1280x704 at 24 fps with exactly the job's frame count (ffprobe, counted packets, not the container's claim);
- LR-3 the first picture exists, is an image, and its sha256 is the one in the job;
- LR-4 the prompt is 1-2 sentences and holds none of the words the model card forbids ("clay", "3D", "Unreal");
- LR-5 a chain: each hop equals its place (1, 2, ...), at most 2 without ``hop3_word`` (CT-1), a chained row continues from the
  previous clip's frame and brings no picture of its own.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
import tarfile
from pathlib import Path

SCHEMA = "layout_job/1"
CMSG = re.compile(r"^cmsg_\w+$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
# the model card (Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render, revision bd765d55): 'Do not write "clay," "3D," or "Unreal."'
FORBIDDEN_PROMPT = re.compile(r"\bclay\b|\b3[\s-]?d\b|\bunreal\b", re.IGNORECASE)
MAX_SENTENCES = 2            # the card: "One or two sentences describing the finished shot"
MAX_HOP_FREE = 2             # CT-1 (W5): hop 3 and further only on the owner's word
WRAPPER = "ic_lora_run.py"   # runs the CLI module in this process and writes torch's peak memory when it ends


# --- small facts -------------------------------------------------------------------------------------------------------------

def ltx_frames(seconds: float, fps: int) -> int:
    """LTX draws 8k+1 frames: the smallest such count that holds the shot (the same rule as modal_ltx_jobs.ltx_frames)."""
    n = max(1, int(round(seconds * fps)))
    return 8 * math.ceil((n - 1) / 8) + 1


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if s.strip()])


def forbidden_words(*texts) -> list[str]:
    return sorted({m.group(0).lower() for t in texts for m in FORBIDDEN_PROMPT.finditer(str(t or ""))})


def compose_prompt(row: dict, film_line: str | None = None) -> str:
    """The prompt the CLI gets: the shot's sentence(s), then the optional film line (variant B)."""
    return " ".join(x.strip() for x in (row.get("motion_prompt"), film_line) if x and str(x).strip())


def probe_video(path, sh=subprocess.run) -> dict:
    """What ffprobe COUNTS in the file (``-count_packets``: the container's ``nb_frames`` is a claim): size, frame rate, frames, sound."""
    r = sh(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
            "stream=codec_type,width,height,r_frame_rate,nb_read_packets", "-of", "json", str(path)],
           capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise ValueError(f"ffprobe cannot read {path}: {(r.stderr or '')[-160:]}")
    streams = json.loads(r.stdout or "{}").get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not v:
        raise ValueError(f"{path} has no video stream")
    num, _, den = str(v.get("r_frame_rate", "0/1")).partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"width": int(v["width"]), "height": int(v["height"]), "fps": round(fps, 3),
            "frames": int(v.get("nb_read_packets") or 0), "audio": any(s.get("codec_type") == "audio" for s in streams)}


# --- the job -----------------------------------------------------------------------------------------------------------------

def rows(job: dict) -> list[dict]:
    """The shot and the shots chained after it, each with the run's size and rate (chained rows may omit them)."""
    keep = ("fps", "width", "height")
    top = {k: job.get(k) for k in keep}
    out, depth = [dict(job, hop=0, chain=None)], 0
    for c in job.get("chain") or []:
        depth = 0 if is_sibling(c) else depth + 1          # a sibling restarts from the job's picture: its own depth 0
        out.append({**top, **c, "hop": c.get("hop", depth), "depth": depth})
    return out


def is_sibling(row: dict) -> bool:
    """A row with ``"start": "first_picture"`` is NOT a continuation: it starts from the job's own first picture (the T1 pair: the same
    shot twice with another prompt), so it has no hand-over and no hop."""
    return row.get("start") == "first_picture"


def job_problems(job: dict, root, launch: dict, probe=probe_video, smoke: bool = False) -> tuple[list[str], list[str]]:
    """(problems, warnings) of a job against the files under ``root`` and the launch's native limits. Free: ffprobe and hashes only."""
    root, bad, warn = Path(root), [], []
    if job.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"], []
    nat = launch["native"]
    for k in ("shot_id", "layout_mp4", "layout_sha256", "first_picture", "first_picture_sha256", "motion_prompt", "seconds", "fps",
              "width", "height", "seed"):
        if job.get(k) in (None, ""):
            bad.append(f"job.{k} is not set")
    if bad:
        return bad, warn
    ids = [job["shot_id"]] + [c.get("shot_id") for c in job.get("chain") or []]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", i) for i in ids):
        bad.append(f"shot ids must be unique plain names, got {ids}")
    hop3 = job.get("hop3_word")
    for i, r in enumerate(rows(job)):
        sid = r.get("shot_id")
        if i:
            for k in ("shot_id", "layout_mp4", "layout_sha256", "motion_prompt", "seconds", "seed"):
                if r.get(k) in (None, ""):
                    bad.append(f"{sid}: chained row has no {k}")
            if r.get("first_picture") or r.get("first_picture_sha256"):
                bad.append(f"{sid}: a chained row continues from the previous clip's frame and brings no picture of its own "
                           "(a cut is a job of its own)")
            if r.get("start") not in (None, "first_picture"):
                bad.append(f"{sid}: start must be absent (a continuation) or 'first_picture' (a sibling of the first clip)")
            elif is_sibling(r):
                if r["hop"] != 0 or r.get("continue_frame"):
                    bad.append(f"{sid}: a row that starts from the first picture has hop 0 and no continue_frame")
            else:
                if r["hop"] != r["depth"]:
                    bad.append(f"{sid}: hop {r['hop']} is not its place {r['depth']} in the chain")
                if r["depth"] > MAX_HOP_FREE and not (isinstance(hop3, str) and CMSG.match(hop3)):
                    bad.append(f"{sid}: hop {r['depth']} needs the owner's word (job.hop3_word = his message id; CT-1, Q6 open)")
                cf = r.get("continue_frame") or {}
                if cf.get("pick", "last") not in ("best_tail", "last"):
                    bad.append(f"{sid}: continue_frame.pick must be best_tail or last")
        w, h, fps = r.get("width"), r.get("height"), r.get("fps")
        if [w, h] != nat["use"] or fps != nat["fps"]:
            bad.append(f"CH-02: {sid} asks {w}x{h}@{fps}, not the native {nat['use'][0]}x{nat['use'][1]}@{nat['fps']}")
        if w and h and (w % 64 or h % 64):
            bad.append(f"{sid}: sides {w}x{h} must be multiples of 64 (two stages work at half size)")
        try:
            frames = ltx_frames(float(r["seconds"]), int(fps))
        except (TypeError, ValueError):
            bad.append(f"{sid}: seconds/fps are not numbers")
            continue
        if (frames - 1) % 8:
            bad.append(f"{sid}: {frames} frames is not 8k+1")
        if frames > nat["max_frames"]:
            bad.append(f"{sid}: {frames} frames are longer than the model's {nat['max_frames']}")
        if not isinstance(r.get("seed"), int) or isinstance(r.get("seed"), bool):
            bad.append(f"{sid}: seed must be a whole number")
        # the layout
        lay = root / str(r.get("layout_mp4") or "")
        if not lay.is_file():
            bad.append(f"{sid}: layout {r.get('layout_mp4')} does not exist")
        elif not HEX64.match(str(r.get("layout_sha256") or "")):
            bad.append(f"{sid}: layout_sha256 is not a 64-hex sha256")
        else:
            if sha256_file(lay) != r["layout_sha256"]:
                bad.append(f"{sid}: the layout's sha256 is not the one in the job (V7: the layout is the file that was approved)")
            try:
                p = probe(lay)
                if [p["width"], p["height"]] != nat["use"] or round(p["fps"], 2) != float(nat["fps"]):
                    bad.append(f"CH-02: {sid} layout is {p['width']}x{p['height']}@{p['fps']}, not "
                               f"{nat['use'][0]}x{nat['use'][1]}@{nat['fps']}")
                if p["frames"] != frames:
                    bad.append(f"{sid}: the layout has {p['frames']} frames, the job asks {frames} (8k+1; the layout drives every frame)")
            except (ValueError, OSError, KeyError) as exc:
                bad.append(f"{sid}: layout cannot be probed: {str(exc)[:120]}")
        rep = r.get("layout_report")
        if rep:
            try:
                data = json.loads((root / rep).read_text(encoding="utf-8"))
                if (data.get("video") or {}).get("sha256") != r.get("layout_sha256"):
                    bad.append(f"{sid}: report.json video.sha256 is not the job's layout_sha256")
                if data.get("status") == "FAIL":
                    bad.append(f"{sid}: report.json status is FAIL: a layout that failed its validators is not rendered")
            except (OSError, ValueError):
                bad.append(f"{sid}: layout_report {rep} cannot be read")
        # the words
        fl = r.get("film_line", job.get("film_line"))
        words = forbidden_words(r.get("motion_prompt"), fl)
        if words:
            bad.append(f"{sid}: the prompt holds {words}: the model card forbids 'clay', '3D' and 'Unreal'")
        n = sentences(r.get("motion_prompt"))
        if not 1 <= n <= MAX_SENTENCES:
            bad.append(f"{sid}: motion_prompt is {n} sentences, the card asks for one or two")
        if fl and sentences(compose_prompt(r, fl)) > MAX_SENTENCES:
            warn.append(f"{sid}: with the film line the prompt is {sentences(compose_prompt(r, fl))} sentences "
                        f"(the card says one or two): recorded, not refused (docs/LTX_LAYOUT_JOBS.md Q-L4)")
    # the first picture (the one the chain's first clip starts from)
    pic = root / str(job["first_picture"])
    if not pic.is_file():
        bad.append(f"first picture {job['first_picture']} does not exist")
    else:
        if not HEX64.match(str(job["first_picture_sha256"])) or sha256_file(pic) != job["first_picture_sha256"]:
            bad.append("the first picture's sha256 is not the one in the job")
        try:
            from PIL import Image
            with Image.open(pic) as im:
                im.verify()
            with Image.open(pic) as im:
                small = im.convert("RGB").resize((32, 32))
            if not smoke and _colour_spread(small) < GREY_SPREAD:
                warn.append("the first picture is almost grey: the card says a grey clay frame as the first frame gives a grey result "
                            "(engineering heuristic, not a source rule)")
        except Exception as exc:  # noqa: BLE001 - any unreadable image is a refusal, never a crash
            bad.append(f"the first picture is not a readable image: {type(exc).__name__}")
    return bad, warn


GREY_SPREAD = 6.0   # engineering heuristic: mean distance of the channels from their grey, on 0..255; below it the picture is "grey"


def _colour_spread(img) -> float:
    px = list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())
    return sum(max(p) - min(p) for p in px) / max(1, len(px))


# --- the command -------------------------------------------------------------------------------------------------------------

def weights(launch: dict, vol_root="/w") -> dict:
    """Where the pinned files live on the Volume: the base split files (staged by W5) and the IC-LoRA file."""
    base = Path(vol_root) / "model" / launch["model_repo"]
    u = launch["uses"]
    return {"transformer": base / u["transformer"], "text_encoder": base / u["text_encoder"], "video_vae": base / u["video_vae"],
            "audio_vae": base / u["audio_vae"], "spatial_upsampler": base / u["spatial_upsampler"],
            "lora": Path(vol_root) / launch["lora"]["dir"] / launch["lora"]["file"]}


def layout_cmd(launch: dict, row: dict, picture, layout, mp4, prompt: str, *, vol_root="/w", python=None, wrapper=None,
               vram_json=None) -> list[str]:
    """``python -m ltx_pipelines.ic_lora`` of ONE clip, every argument read from the module's argparse at the pinned commit
    (docs/LTX_LAYOUT_JOBS.md section 2): the split weights of the distilled LTX-2.5, the IC-LoRA at the launch's strength, the layout as
    ``--video-conditioning PATH STRENGTH`` (required by the CLI), the first picture as ``--image PATH 0 STRENGTH`` and
    ``--stage-2-ic-lora`` when the launch says so. The distilled parser has no --negative-prompt and no CFG flag."""
    w, st = weights(launch, vol_root), launch["settings"]
    head = [python or sys.executable]
    if wrapper:                                   # the wrapper runs the module in its own process and writes torch's peak memory
        head += [str(wrapper), launch["module"], str(vram_json)]
    else:
        head += ["-m", launch["module"]]
    cmd = head + ["--transformer-path", str(w["transformer"]), "--text-encoder-path", str(w["text_encoder"]),
                  "--video-vae-path", str(w["video_vae"]), "--audio-vae-path", str(w["audio_vae"]),
                  "--spatial-upsampler-path", str(w["spatial_upsampler"]),
                  "--lora", str(w["lora"]), str(st["lora_strength"]),
                  "--video-conditioning", str(layout), str(st["video_conditioning_strength"]),
                  "--image", str(picture), str(st["first_frame_index"]), str(st["image_strength"])]
    if st.get("stage_2_ic_lora"):
        cmd += ["--stage-2-ic-lora"]
    return cmd + ["--prompt", prompt, "--height", str(row["height"]), "--width", str(row["width"]),
                  "--num-frames", str(ltx_frames(float(row["seconds"]), int(row["fps"]))), "--frame-rate", str(row["fps"]),
                  "--seed", str(row["seed"]), "--output-path", str(mp4)]


def run_settings(launch: dict, row: dict, prompt: str, cmd: list[str]) -> dict:
    """Every setting of a clip, written into its record (never reconstructed from the command line)."""
    st = launch["settings"]
    return {"module": launch["module"], "ltx_commit": launch["ltx_code"]["commit"], "model_revision": launch["model_revision"],
            "lora": {"file": launch["lora"]["file"], "revision": launch["lora"]["revision"], "sha256": launch["lora"]["sha256"],
                     "strength": st["lora_strength"]},
            "settings": dict(st), "seed": row["seed"], "frames": ltx_frames(float(row["seconds"]), int(row["fps"])), "fps": row["fps"],
            "size": [row["width"], row["height"]], "prompt": prompt, "layout_sha256": row.get("layout_sha256"),
            "argv_sha256": hashlib.sha256("\0".join(cmd).encode()).hexdigest()}


# --- the hand-over of a chain (VL-05, VL-16, BP-199: the same scoring as modal_ltx_jobs, kept equal by a test) ---------------------

HANDOVER_W = 160
HANDOVER_MOTION_W = 1.5
CROP_MIN_SIDE = 2.0 / 3.0
HANDOVER_WINDOW_S = 1.5
W_FACE = 0.6
W_BODY = 0.3
W_FRAME = 0.1


def chain_from(launch: dict, frames: int) -> int:
    """The last frame of a clip that can start the next one: ``chain.overlap_frames`` before its end (0 = the last frame)."""
    k = int(launch["chain"]["overlap_frames"])
    if not 0 <= k < frames - 1:
        raise ValueError(f"chain overlap_frames {k} does not fit a clip of {frames} frames")
    return frames - 1 - k


def _grey_frames(clip: Path, first: int, count: int, width: int = HANDOVER_W, sh=subprocess.run):
    """Frames ``first .. first+count-1`` of the clip as small grey float arrays (ffmpeg decode, numpy only: the container
    has no OpenCV)."""
    import numpy as np
    probe = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                str(clip)], check=True, timeout=60, capture_output=True, text=True)
    w0, h0 = (int(v) for v in probe.stdout.strip().split(",")[:2])
    h = max(2, int(round(width * h0 / w0 / 2)) * 2)
    raw = sh(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"select=gte(n\\,{int(first)}),scale={width}:{h},format=gray",
              "-fps_mode", "passthrough", "-frames:v", str(int(count)), "-f", "rawvideo", "-"], check=True, timeout=120,
             capture_output=True).stdout
    n = len(raw) // (width * h)
    return np.frombuffer(raw[:n * width * h], np.uint8).reshape(n, h, width).astype(np.float32)


def _lap_var_2d(g) -> float:
    import numpy as np
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return float(np.var(lap))


def _crop_norm(g, box) -> "np.ndarray":
    h, w = g.shape[:2]
    x0 = max(0, min(w - 1, int(round(box[0] * w))))
    y0 = max(0, min(h - 1, int(round(box[1] * h))))
    x1 = max(x0 + 1, min(w, int(round(box[2] * w))))
    y1 = max(y0 + 1, min(h, int(round(box[3] * h))))
    return g[y0:y1, x0:x1]


def handover_scores(frames, face_box=None, body_box=None) -> list[dict]:
    """VL-05 / VL-16 / BP-199 (Audit #7b): score every candidate handover frame by person stillness and face sharpness
    first (``W_FACE=0.6, W_BODY=0.3, W_FRAME=0.1``) so a sharp background never overrides a moving face/body."""
    import numpy as np
    fbox = list(face_box) if face_box is not None else [0.30, 0.12, 0.70, 0.50]
    bbox = list(body_box) if body_box is not None else [0.22, 0.45, 0.78, 0.92]
    out = []
    for i, g in enumerate(frames):
        js = [j for j in (i - 1, i + 1) if 0 <= j < len(frames)]
        f_crop = _crop_norm(g, fbox)
        b_crop = _crop_norm(g, bbox)
        frame_diffs = [float(np.abs(g - frames[j]).mean()) for j in js]
        face_diffs = [float(np.abs(f_crop - _crop_norm(frames[j], fbox)).mean()) for j in js]
        body_diffs = [float(np.abs(b_crop - _crop_norm(frames[j], bbox)).mean()) for j in js]
        out.append({
            "i": i,
            "sharpness": _lap_var_2d(g),
            "motion": float(np.mean(frame_diffs)) if frame_diffs else 0.0,
            "face_sharp": _lap_var_2d(f_crop),
            "face_motion": float(np.mean(face_diffs)) if face_diffs else 0.0,
            "body_motion": float(np.mean(body_diffs)) if body_diffs else 0.0,
        })
    top_frame_s = max((o["sharpness"] for o in out), default=0.0) or 1.0
    top_face_s = max((o["face_sharp"] for o in out), default=0.0) or 1.0
    top_frame_m = max([o["motion"] for o in out] + [1.0]) or 1.0
    top_face_m = max([o["face_motion"] for o in out] + [1.0]) or 1.0
    top_body_m = max([o["body_motion"] for o in out] + [1.0]) or 1.0
    for o in out:
        face_term = (o["face_sharp"] / top_face_s) - (o["face_motion"] / top_face_m)
        body_term = -(o["body_motion"] / top_body_m)
        frame_term = (o["sharpness"] / top_frame_s) - HANDOVER_MOTION_W * (o["motion"] / top_frame_m)
        o["person_score"] = W_FACE * face_term + W_BODY * body_term + W_FRAME * frame_term
        o["score"] = o["person_score"]
    return out


def speech_floor(fps: int, speech_end_s=None, tail_s=0.0) -> int | None:
    """P5 / BP-187: the first frame at or after the clip's expected speech end plus the tail (the same bound
    ``videolane/ingest.edit_points`` checks on the real sound); None for a clip that speaks no line."""
    if speech_end_s is None:
        return None
    return int(math.ceil((float(speech_end_s) + float(tail_s or 0.0)) * fps - 1e-6))


def crop_filter(crop) -> str:
    """The ffmpeg crop of a ``[x0, y0, x1, y1]`` share box (VL-05: each side at least CROP_MIN_SIDE)."""
    x0, y0, x1, y1 = (float(v) for v in crop)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"crop {crop} is not a box inside the frame")
    if x1 - x0 < CROP_MIN_SIDE - 1e-9 or y1 - y0 < CROP_MIN_SIDE - 1e-9:
        raise ValueError(f"crop {crop} enlarges the frame more than {1 / CROP_MIN_SIDE:.2f}x: it would be soft")
    return f"crop=iw*{x1 - x0:.6f}:ih*{y1 - y0:.6f}:iw*{x0:.6f}:ih*{y0:.6f}"


def frame_png(clip: Path, index: int, png: Path, sh=subprocess.run, crop=None) -> bytes:
    """Frame ``index`` (0-based, by decode order) of the clip as a PNG: the first picture of the next chained clip, cropped
    when the continuation plan reframes it (``fit_picture`` then brings it to the clip size)."""
    vf = f"select=eq(n\\,{int(index)})" + (f",{crop_filter(crop)}" if crop else "")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf", vf, "-fps_mode", "passthrough",
        "-frames:v", "1", str(png)], check=True, timeout=60)
    if not Path(png).is_file() or Path(png).stat().st_size == 0:
        raise RuntimeError(f"frame {index} of {Path(clip).name} was not written")
    return Path(png).read_bytes()


def handover_frame(clip: Path, frames: int, fps: int, cont: dict | None, launch: dict, sh=subprocess.run,
                   speech_end_s=None, tail_s=0.0) -> dict:
    """The frame of a clip that starts its continuation. ``pick: last`` (the default, as in modal_ltx_jobs) is ``chain_from``;
    ``pick: best_tail`` (a continuation plan's choice) scores the last ``window_s`` seconds with the BP-199
    person weights. A clip whose line is not over by then has no hand-over frame (``frame`` None): the chain stops, never a cut inside the speech."""
    last = chain_from(launch, frames)
    cont = cont or {}
    pick = cont.get("pick", "last")
    floor = speech_floor(fps, speech_end_s, tail_s)
    after = {} if floor is None else {"after": floor}
    if floor is not None and floor > last:
        return {"frame": None, "pick": pick, **after,
                "why": f"the line ends at {float(speech_end_s):.3f} s and BP-187's tail adds {float(tail_s or 0):g} s (frame "
                       f"{floor}), after the clip's last frame {last}: no hand-over frame that keeps the line whole"}
    if pick == "last":
        return {"frame": last, "pick": "last", **after}
    n = max(2, min(last + 1, int(round(float(cont.get("window_s", HANDOVER_WINDOW_S)) * fps))))
    first = last + 1 - n
    if floor is not None and floor > first:
        first = floor
    scores = handover_scores(_grey_frames(clip, first, last + 1 - first, sh=sh))
    best = max(scores, key=lambda o: o["score"])
    return {"frame": first + best["i"], "pick": "best_tail", "window": [first, last], **after,
            "scores": [{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()} for s in scores]}


def fit_picture(img, width, height):
    """Crop to the clip's aspect (centred), then Lanczos to its size (modal_ltx_jobs.fit_picture without the face box)."""
    from PIL import Image
    w, h = img.size
    if w * height > h * width:
        cw, ch = round(h * width / height), h
    else:
        cw, ch = w, round(w * height / width)
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.convert("RGB").crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


# --- the batch tar -----------------------------------------------------------------------------------------------------------

def trim_layout(src, dst, frames: int, sh=subprocess.run) -> Path:
    """The first ``frames`` frames of a layout (the L3 smoke's small clip), re-encoded as the layout is (h264, yuv420p, no sound)."""
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-frames:v", str(int(frames)), "-an", "-c:v", "libx264", "-pix_fmt",
        "yuv420p", "-crf", "12", "-r", "24", str(dst)], check=True, timeout=300)
    return Path(dst)


def pack(folder, out_dir, launch: dict, *, smoke: bool = False, probe=probe_video) -> tuple[Path, str]:
    """Validate ``<folder>/job.json`` and pack the folder into ``batch-<sha256>.tar.gz`` (reproducible: sorted members, zeroed times).
    Upload it to HF ``code/layout/batch-<sha>.tar.gz`` (free) before the L3 rung; a job with a problem is never packed."""
    folder, out_dir = Path(folder), Path(out_dir)
    job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    bad, warn = job_problems(job, folder, launch, probe=probe, smoke=smoke)
    if bad:
        raise SystemExit("job refused:\n" + "\n".join(bad))
    for w in warn:
        print("WARNING", w, file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "batch.tmp.tar.gz"
    with gzip.GzipFile(tmp, "wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tf:
        for p in sorted(x for x in folder.rglob("*") if x.is_file()):
            ti = tf.gettarinfo(str(p), str(p.relative_to(folder)))
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = 0, 0, 0, "", ""
            with open(p, "rb") as f:
                tf.addfile(ti, f)
    sha = sha256_file(tmp)
    final = out_dir / f"batch-{sha}.tar.gz"
    tmp.replace(final)
    return final, sha


def main(argv=None) -> int:
    """``python -m explainer_engine.training.pods.ltx.layout_job pack <folder with job.json> <out dir> [--smoke]``: free, local."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 3 or argv[0] != "pack":
        print(main.__doc__)
        return 2
    launch = json.loads((Path(__file__).with_name("launch_layout_a100.json")).read_text(encoding="utf-8"))
    path, sha = pack(argv[1], argv[2], launch, smoke="--smoke" in argv)
    print(path, sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
