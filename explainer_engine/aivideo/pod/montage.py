"""Assemble the night test video: black 'what if' opening with the title, then one shot per narration segment. A shot
longer than its clip first holds the clip's first keyframe with a slow push, then plays the clip (the clip starts on that
same frame); a shorter one plays the clip from its start. Output 3840x2160 24 fps H.264 + the narration (AAC).
Usage: python montage.py NIGHT_DIR CLIPS_DIR KF_DIR OUT.mp4 [--size 3840x2160]"""
import json, os, subprocess, sys, tempfile

night, clips, kf, out = sys.argv[1:5]
size = sys.argv[sys.argv.index("--size") + 1] if "--size" in sys.argv else "3840x2160"
Wd, Hd = map(int, size.split("x"))
tl = json.load(open(os.path.join(night, "timeline.json")))
FPS = 24
tmp = tempfile.mkdtemp(prefix="montage_")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(" ".join(cmd)[:300] + "\n" + r.stderr[-1500:])


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout.strip() or 0)


scale = f"scale={Wd}:{Hd}:force_original_aspect_ratio=increase:flags=lanczos,crop={Wd}:{Hd},setsar=1"
parts = []
# 1) the black opening with the title in the last second and a half
t_open = tl["intro_end"]
title = os.path.join(tmp, "open.mp4")
draw = (f"drawtext=text='100 PEOPLE vs THE ICE AGE':fontcolor=white:fontsize={Hd // 14}:x=(w-tw)/2:y=(h-th)/2:"
        f"alpha='if(lt(t,{max(0, t_open - 2.2):.2f}),0,min(1,(t-{max(0, t_open - 2.2):.2f})/0.6))'")
run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={Wd}x{Hd}:r={FPS}:d={t_open:.3f}", "-vf", draw,
     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", title])
parts.append(title)
report = []
for seg in tl["segments"]:
    sid, d = seg["id"], seg["t1"] - seg["t0"]
    clip = next((p for p in (os.path.join(clips, f"{sid}.mp4"), os.path.join(clips, f"{sid}_out.mp4")) if os.path.exists(p)), None)
    first = os.path.join(kf, f"{sid}_first.png")
    piece = os.path.join(tmp, f"{sid}.mp4")
    if clip:
        L = dur(clip)
        if d > L + 0.05 and os.path.exists(first):  # hold the first keyframe (slow push), then the clip
            hold = d - L
            n = max(1, round(hold * FPS))
            zp = (f"{scale},zoompan=z='1+0.04*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={Wd}x{Hd}:fps={FPS}")
            h = os.path.join(tmp, f"{sid}_hold.mp4")
            run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", first, "-vf", zp, "-frames:v", str(n), "-c:v", "libx264",
                 "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", h])
            c = os.path.join(tmp, f"{sid}_clip.mp4")
            run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", f"{scale},zoompan=z='1.04':x='iw/2-(iw/zoom/2)':"
                 f"y='ih/2-(ih/zoom/2)':d=1:s={Wd}x{Hd}:fps={FPS}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-pix_fmt", "yuv420p", c])
            lst = os.path.join(tmp, f"{sid}.txt")
            open(lst, "w").write(f"file '{h}'\nfile '{c}'\n")
            run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-t", f"{d:.3f}", "-c:v", "libx264",
                 "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", piece])
            how = f"hold {hold:.1f}s + clip"
        else:
            run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", f"fps={FPS},{scale}", "-t", f"{d:.3f}", "-an", "-c:v",
                 "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", piece])
            how = "clip"
    elif os.path.exists(first):  # no clip: the keyframe with a slow push
        n = max(1, round(d * FPS))
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", first, "-vf", f"{scale},zoompan=z='1+0.06*on/{n}':"
             f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={Wd}x{Hd}:fps={FPS}", "-frames:v", str(n), "-c:v", "libx264",
             "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", piece])
        how = "still"
    else:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={Wd}x{Hd}:r={FPS}:d={d:.3f}", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", piece])
        how = "MISSING"
    parts.append(piece)
    report.append({"id": sid, "seconds": round(d, 2), "how": how})
lst = os.path.join(tmp, "all.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(night, "narration.mp3"),
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
     "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-t", f"{tl['end']:.3f}", "-movflags", "+faststart", out])
json.dump(report, open(out + ".json", "w"), indent=1)
print("MONTAGE", out, round(dur(out), 2), "s;", sum(r["how"] == "MISSING" for r in report), "missing")
