"""The one-minute multi-scene pilot (guide step 6, D-116): route shots -> each shot's clip from its route (J5 Blender 2.5D
render, J2/J4 LTX clips from the route-test pod, H Python helper) -> the master frame -> ``build_video_v2`` -> one mp4, with the
narration track laid under it when one is given. Free and local; it renders nothing itself and pays for nothing.

    python -m explainer_engine.production.pilot <route_shots.json> <out dir> [--seconds 60 | --shots S01-01,S01-02,...]
           [--j5 <dir of <shot>.mp4>] [--helper <dir of <shot>.mp4>] [--ltx <pod out dir>] [--base ltx25|ltx23]
           [--pick S02-02.c1=<job id>,...] [--audio narration.wav] [--slates]

- J5 and H: ``<dir>/<shot>.mp4``, or an ``assemble_25d`` render folder ``<dir>/<shot>/frames/frame_NNNNNN.png`` (with a
  ``handles.json`` beside ``frames/``, as the lean pod writes, the shot starts after its ``head`` frames).
- The window: whole shots in script order while they fit ``--seconds`` (60 by default; the route test's first 59.5 s are S01,
  S02 and S03-01..03: J5, H, J4 and J2 shots, three scenes), or the shots ``--shots`` names.
- J2/J4: the upscaled copy ``ltx_up/<job>.mp4`` of the pod (``finish/upscale`` ROUTE_TEST chain), else its raw clip; per clip the
  job ``--pick`` names, else the first job of ``ltx_jobs.json`` for that clip on ``--base`` whose sidecar says it ran. A chained clip
  drops the frames it shares with the clip before it (``overlap_frames_with_previous``), so a J4 shot of two clips is one take.
- Every clip is conformed to the master (BP-167: 2560x1440, 24 fps: ``finish/upscale.video_filter`` for a 1088-row LTX clip, a
  plain scale for a 1440p render). A clip shorter than its shot is refused by ``build_video_v2``, never stretched.
- ``pilot.build`` is always a route-comparison preview. ``--slates`` puts a flat card in the route's colour where a clip is
  missing; even when every clip exists, this route-shots input has not passed ``cut_plan.gate`` and is never a final cut.
- The film_shots/3, audio_spine/2 and edit_and_grade_manifest/1 the assembler reads are written next to the video (straight cuts on
  the shot boundaries; the spine is the shots' clock unless ``--spine`` gives the read's own).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from explainer_engine.core import contracts, delivery
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

SUB = re.compile(r"^(V([1-9]|10)|S[1-7]|H[1-6])\b")
SLATE = {"J5": "0x5a6a7a", "J2": "0x5d7a4e", "J4": "0x8a6a3a", "H": "0x6a5a7a"}   # route colours of a missing clip's card
SIZE_OF = {"S4": "INSERT", "S3": "INSERT", "V3": "MCU", "V8": "MCU", "S1": "WS", "V1": "EWS", "V9": "WS", "V7": "MS"}


def select(route_shots: dict, *, seconds: float = 60.0, ids: list[str] | None = None) -> list[dict]:
    shots = route_shots["shots"]
    if ids:
        by = {s["id"]: s for s in shots}
        missing = [i for i in ids if i not in by]
        if missing:
            raise ContractError(f"no such shots in the route shots: {', '.join(missing)}")
        return [by[i] for i in ids]
    out, total = [], 0.0
    for s in shots:
        if total + s["seconds"] > seconds + 1e-6:
            break
        out.append(s)
        total += s["seconds"]
    if not out:
        raise ContractError(f"no shot fits {seconds} s")
    return out


def _sub(shot: dict) -> str | None:
    m = SUB.match(shot.get("kind") or "")
    return m.group(1) if m else None


def lane_fields(shot: dict) -> dict:
    """The film_shots/3 lane block of one route shot (D-97 as amended by D-116)."""
    route, sub = shot["route"], _sub(shot)
    if route == "H":
        return {"lane": "HELPER", "helper_archetype": shot["helper"]["archetype"]}
    still = (shot.get("assembly") or {}).get("still_mode")
    if route == "J5" and still:
        return {"lane": "STILL_3D", "render_profile": "eevee_full", "still_mode": still}
    kind = (shot.get("kind") or "").lower()
    lips = bool(shot.get("dialogue")) and "mouth" in kind and "no mouth" not in kind
    return {"lane": "VIDEO_3D", "render_profile": "eevee_full", "lipsync": lips}


def film_shots(route_shots: dict, chosen: list[dict], fps: int) -> dict:
    """A film_shots/3 of the window (the shot clock the assembler and the sound director read)."""
    from explainer_engine.core.contracts import _bible_version
    w, h = delivery.size()
    shots = []
    for s in chosen:
        sub, d = _sub(s), s.get("dialogue")
        mode = "scene" if d else {"S1": "establish", "S3": "insert", "S4": "insert"}.get(sub or "", "narrated")
        row = {"id": s["id"], "scene": s["scene"], "mode": mode, "beat": s.get("narration") or (d or {}).get("text") or s["kind"],
               "seconds": s["seconds"], "frame": {"size": SIZE_OF.get(sub or "", "WS"), "place": s.get("place") or "none"},
               "source": "keyframe", "archetype": None, "duration_frames": round(s["seconds"] * fps), "width": w, "height": h,
               "lens_tier": "normal", "focal_xy": [0.5, 0.5], "continuity_ref": None, "blocking_ref": None, "route": s["route"],
               **lane_fields(s)}
        if sub:
            row["sub_category"] = sub
        if s.get("narration") and not d:
            row["narration"] = s["narration"]
        if d:
            row["dialogue"] = {"who": d["who"], "to": "room", "text": d["text"], **({"delivery": d["delivery"]} if d.get("delivery") else {})}
            row["dialogue_cover"] = "on_screen" if row.get("lipsync") else "off_screen"
        if s["route"] in ("J2", "J4"):
            row["ltx_clips"] = ([{"seconds": round(c["frames"] / fps, 3), "frames": c["frames"], "width": 1920, "height": 1088,
                                  "overlap_frames": c.get("overlap_frames_with_previous", 0)} for c in s["clips"]] if s.get("clips")
                                else [{"seconds": round(s["ltx"]["frames"] / fps, 3), "frames": s["ltx"]["frames"],
                                       "width": s["ltx"]["size"][0], "height": s["ltx"]["size"][1]}])
        shots.append(row)
    places = {k: v for k, v in (route_shots.get("places") or {}).items()} or {"none": "unnamed"}
    places.setdefault("none", "unnamed")
    cast = {k: {"tag": v["tag"]} for k, v in (route_shots.get("cast") or {}).items()}
    return {"schema": "film_shots/3", "episode": route_shots.get("episode", "pilot"), "fps": fps,
            "style": {"house_look": "ink_chronicle", "bible_version": _bible_version() or "1.5"}, "cast": cast, "places": places,
            "shots": shots}


def spine_of(film: dict) -> dict:
    """audio_spine/2 on the shots' clock: one segment per scene, starting where its first shot starts (no words: the read's own
    spine replaces it when the narration exists)."""
    fps, frame, segs = film["fps"], 0, []
    for s in film["shots"]:
        if not segs or segs[-1]["id"] != s["scene"]:
            segs.append({"id": s["scene"], "start_frame": frame})
        frame += s["duration_frames"]
    return {"schema": "audio_spine/2", "fps": fps, "duration_s": round(frame / fps, 3), "total_frames": frame, "words": [],
            "post_hoc_shots": [], "segments": segs}


def edit_manifest(film: dict, film_ref: dict, spine_ref: dict) -> dict:
    scenes, frame, prev = [], 0, None
    for s in film["shots"]:
        if not scenes or scenes[-1]["scene_id"] != s["scene"]:
            scenes.append({"scene_id": s["scene"], "key_master_frame": None, "grade": None, "cuts": []})
        if prev is not None:
            scenes[-1]["cuts"].append({"from_shot": prev, "to_shot": s["id"], "cut_type": "STRAIGHT_CUT", "at_frame": frame,
                                       "audio_lead_frames": 0})
        prev, frame = s["id"], frame + s["duration_frames"]
    return {"schema": "edit_and_grade_manifest/1", "film_shots": film_ref, "audio_spine": spine_ref, "scenes": scenes}


# --- the clips of each route ---------------------------------------------------------------------------------------------------

def ltx_pick(ltx: Path, clip_id: str, *, base: str | None = None, pick: dict | None = None) -> tuple[Path | None, str | None]:
    """(clip path, job id) for one LTX clip of the pod's out folder: the upscaled copy first, the raw clip else."""
    ltx = Path(ltx)
    jobs_file = next((p for p in (ltx / "ltx_jobs.json", ltx / "ltx" / "ltx_jobs.json") if p.exists()), None)
    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))["jobs"] if jobs_file else []
    want = (pick or {}).get(clip_id)
    cands = [want] if want else [j["id"] for j in jobs if j["clip_id"] == clip_id and (base is None or j["base"] == base)]
    if not jobs and not want:   # no jobs file: any clip of that id
        cands = sorted(p.stem for p in (ltx / "ltx").glob(f"{clip_id}.*.mp4"))
    for jid in cands:
        side = ltx / "ltx" / f"{jid}.json"
        if side.exists() and json.loads(side.read_text(encoding="utf-8")).get("rc") not in (0, None):
            continue
        for p in (ltx / "ltx_up" / f"{jid}.mp4", ltx / "ltx" / f"{jid}.mp4"):
            if p.exists():
                return p, jid
    return None, None


def sources(chosen: list[dict], *, j5: Path | None = None, helper: Path | None = None, ltx: Path | None = None,
            base: str | None = None, pick: dict | None = None) -> list[dict]:
    """Per shot its parts [{path, skip}] (a J4 shot has one per clip) or ``missing`` with the reason."""
    out = []
    for s in chosen:
        row = {"shot": s["id"], "route": s["route"], "parts": [], "missing": None, "jobs": []}
        if s["route"] in ("J5", "H"):
            folder = j5 if s["route"] == "J5" else helper
            p = Path(folder) / f"{s['id']}.mp4" if folder else None
            seq = Path(folder) / s["id"] / "frames" if folder else None   # an assemble_25d render dir: frames/frame_NNNNNN.png
            if p is not None and p.exists():
                row["parts"].append({"path": p, "skip": 0})
            elif seq is not None and any(seq.glob("frame_*.png")):
                hd = seq.parent / "handles.json"   # the lean pod's J5 renders carry 12-frame handles (BP-128): the shot starts after them
                head = int(json.loads(hd.read_text(encoding="utf-8")).get("head", 0)) if hd.exists() else 0
                row["parts"].append({"path": seq / "frame_%06d.png", "skip": head, "frames": True})
            else:
                row["missing"] = f"no {s['route']} clip {s['id']}.mp4 or {s['id']}/frames/ in {folder}"
        else:
            clips = s.get("clips") or [{"clip": s["id"], "overlap_frames_with_previous": 0}]
            for c in clips:
                p, jid = ltx_pick(ltx, c["clip"], base=base, pick=pick) if ltx else (None, None)
                if p is None:
                    row["missing"] = f"no LTX clip for {c['clip']}" + (f" on {base}" if base else "")
                    row["parts"] = []
                    break
                row["parts"].append({"path": p, "skip": int(c.get("overlap_frames_with_previous") or 0)})
                row["jobs"].append(jid)
        out.append(row)
    return out


def _probe(path: Path) -> tuple[int, int]:
    from explainer_engine.finish import upscale
    return upscale.probe_size(path)


def conform_cmd(parts: list[dict], dst: Path, fps: int) -> list[str]:
    """One ffmpeg call: every part to the master frame (crop the LTX 1088 rows, Lanczos), the shared frames of a chained part
    dropped, the parts joined."""
    from explainer_engine.finish import upscale
    w, h = delivery.size()
    cmd, chains = ["ffmpeg", "-v", "error", "-y"], []
    for k, p in enumerate(parts):
        if p.get("frames"):   # a PNG sequence at the master clock
            from PIL import Image
            first = sorted(Path(p["path"]).parent.glob("frame_*.png"))[0]
            cmd += ["-framerate", str(fps), "-start_number", first.stem.split("_")[-1].lstrip("0") or "0", "-i", str(p["path"])]
            sw, sh = Image.open(first).size
        else:
            cmd += ["-i", str(p["path"])]
            sw, sh = _probe(p["path"])
        vf = upscale.video_filter(sw, sh) if (sw, sh) != (w, h) else f"fps={fps}"
        trim = f"trim=start_frame={p['skip']},setpts=PTS-STARTPTS," if p["skip"] else ""
        chains.append(f"[{k}:v]{trim}{vf},setsar=1,format=yuv420p[v{k}]")
    graph = ";".join(chains) + ";" + "".join(f"[v{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[out]"
    return cmd + ["-filter_complex", graph, "-map", "[out]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                  "-pix_fmt", "yuv420p", str(dst)]


def slate_cmd(route: str, frames: int, dst: Path, fps: int) -> list[str]:
    w, h = delivery.size()
    return ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={SLATE[route]}:s={w}x{h}:r={fps}", "-frames:v", str(frames),
            "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p", str(dst)]


def _ref(job: Path, path: Path) -> dict:
    return {"path": str(path.relative_to(job)), "sha256": contracts.sha256_file(path)}


def build(route_shots: dict, out: Path, *, seconds: float = 60.0, ids: list[str] | None = None, j5: Path | None = None,
          helper: Path | None = None, ltx: Path | None = None, base: str | None = None, pick: dict | None = None,
          audio: Path | None = None, spine: Path | None = None, slates: bool = False, run=subprocess.run) -> dict:
    from explainer_engine.production import assemble as ASM
    out = Path(out)
    shots_dir = out / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    fps = delivery.fps()
    chosen = select(route_shots, seconds=seconds, ids=ids)
    film = film_shots(route_shots, chosen, fps)
    contracts.validate(film)
    rows = sources(chosen, j5=j5, helper=helper, ltx=ltx, base=base, pick=pick)
    missing = [r for r in rows if r["missing"]]
    if missing and not slates:
        raise ContractError("clips missing (render them, or pass --slates for a timing preview): "
                            + "; ".join(r["missing"] for r in missing))
    frames_of = {s["id"]: s["duration_frames"] for s in film["shots"]}
    for r in rows:
        dst = shots_dir / f"{r['shot']}.mp4"
        cmd = slate_cmd(r["route"], frames_of[r["shot"]], dst, fps) if r["missing"] else conform_cmd(r["parts"], dst, fps)
        run(cmd, check=True)
        r["clip"] = str(dst.relative_to(out))
        r["parts"] = [{**p, "path": str(p["path"])} for p in r["parts"]]
    write_json_atomic(out / "film_shots.json", film)
    spine_doc = json.loads(Path(spine).read_text(encoding="utf-8")) if spine else spine_of(film)
    write_json_atomic(out / "audio_spine.json", spine_doc)
    manifest = edit_manifest(film, _ref(out, out / "film_shots.json"), _ref(out, out / "audio_spine.json"))
    write_json_atomic(out / "edit_and_grade_manifest.json", manifest)
    picture = out / "pilot_picture.mp4"
    derived = ASM.build_video_v2(manifest, shots_dir, picture, job=out, name="pilot")
    video = picture
    if audio:
        video = out / "pilot.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "320k", "-shortest", str(video)], check=True)
    secs = {}
    for s in film["shots"]:
        secs[s["lane"]] = round(secs.get(s["lane"], 0) + s["seconds"], 2)
    total = sum(s["seconds"] for s in film["shots"])
    report = {"schema": "pilot/1", "video": str(video.relative_to(out)), "preview": True,
              "preview_reason": "route_shots are not a validated cut_plan/1; final assembly must pass cut_plan.gate",
              "seconds": total,
              "scenes": sorted({s["scene"] for s in film["shots"]}), "routes": sorted({s["route"] for s in film["shots"]}),
              "lane_share": {k: round(v / total, 3) for k, v in secs.items()}, "shots": rows,
              "slates": [r["shot"] for r in missing], "findings": derived.get("findings", [])}
    write_json_atomic(out / "pilot.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("route_shots", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--shots")
    ap.add_argument("--j5", type=Path)
    ap.add_argument("--helper", type=Path)
    ap.add_argument("--ltx", type=Path)
    ap.add_argument("--base", choices=["ltx25", "ltx23"])
    ap.add_argument("--pick", help="clip=job,... the LTX take per clip")
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--spine", type=Path)
    ap.add_argument("--slates", action="store_true")
    a = ap.parse_args(argv)
    rs = json.loads(a.route_shots.read_text(encoding="utf-8"))
    pick = dict(x.split("=", 1) for x in a.pick.split(",")) if a.pick else None
    rep = build(rs, a.out, seconds=a.seconds, ids=a.shots.split(",") if a.shots else None, j5=a.j5, helper=a.helper, ltx=a.ltx,
                base=a.base, pick=pick, audio=a.audio, spine=a.spine, slates=a.slates)
    print(f"{rep['video']}: {rep['seconds']} s, scenes {', '.join(rep['scenes'])}, routes {', '.join(rep['routes'])}; PREVIEW"
          + (f", slates for {', '.join(rep['slates'])}" if rep["slates"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
