"""A stand-in for the Blender binary (ICW-04 tests): ``--version`` prints a version line, and a render call must be exactly

    --background --factory-startup --python-exit-code 1 --python <.../render_shot.py> -- <job.json>

It then does what ``bpy/render_shot.py`` does on the outside: one PNG per listed frame (written under a temporary name, then moved),
one progress line per frame, a report at the end. Knobs (env): FAKE_BLENDER_LOG (every call's argv and job frames, one JSON line
each), FAKE_BLENDER_VERSION, FAKE_BLENDER_DIE_AFTER=N (exit 137 after N frames, as a killed process), FAKE_BLENDER_RC (exit code
after all frames), FAKE_BLENDER_BLACK (comma list of black frame indices). stdlib only."""
import json
import os
import struct
import sys
import zlib


def png(w, h, rgb):
    row = b"\x00" + bytes(rgb) * w
    raw = zlib.compress(row * h, 9)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def main():
    argv = sys.argv[1:]
    log = os.environ.get("FAKE_BLENDER_LOG")
    if "--version" in argv:
        if log:
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"argv": argv}) + "\n")
        print(f"Blender {os.environ.get('FAKE_BLENDER_VERSION', '5.2.3')}\n\tbuild date: 2026-10-22\n\tbuild hash: 0123456789ab")
        return 0
    want = ["--background", "--factory-startup", "--python-exit-code", "1", "--python"]
    if argv[:5] != want or len(argv) != 8 or not argv[5].endswith("render_shot.py") or argv[6] != "--":
        print(f"fake blender: unexpected arguments {argv}", file=sys.stderr)
        return 2
    with open(argv[7], encoding="utf-8") as f:
        job = json.load(f)
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"argv": argv, "frames": job["frames"]}) + "\n")
    die = int(os.environ.get("FAKE_BLENDER_DIE_AFTER", "-1"))
    black = {int(x) for x in os.environ.get("FAKE_BLENDER_BLACK", "").split(",") if x}
    w, h = round(job["width"] * job["percent"] / 100), round(job["height"] * job["percent"] / 100)
    os.makedirs(job["frames_dir"], exist_ok=True)
    with open(job["progress"], "a", encoding="utf-8") as prog:
        for n, idx in enumerate(job["frames"]):
            if n == die:
                return 137
            name = job["frame_name"].format(index=idx)
            tmp = os.path.join(job["frames_dir"], ".part_" + name)
            with open(tmp, "wb") as f:
                f.write(png(w, h, (0, 0, 0) if idx in black else (40 + idx % 200, 90, 160)))
            os.replace(tmp, os.path.join(job["frames_dir"], name))
            prog.write(json.dumps({"index": idx, "file": name, "seconds": 0.5}) + "\n")
            prog.flush()
    with open(job["report"], "w", encoding="utf-8") as f:
        json.dump({"blender_version": "5.2.3", "build_hash": "0123456789ab", "engine_id": job["engine"], "applied": {},
                   "missing": [], "objects": {}, "frames": len(job["frames"])}, f)
    return int(os.environ.get("FAKE_BLENDER_RC", "0"))


if __name__ == "__main__":
    sys.exit(main())
