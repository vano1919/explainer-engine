"""Quick gate check of the 2.5D stills of a script (short, low-res rehearsal render): usage test_stills.py SCRIPT.json OUTDIR WIDTH SECONDS SHOT..."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "/home/user/explainer-engine")
from explainer_engine.production import layers25d as L
script = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
w = int(sys.argv[3]); secs = float(sys.argv[4]); ids = sys.argv[5:]
F = json.load(open("/mnt/project-files/explainer-engine/demo_truce_1914/pictures/final_scene_frames_A.json"))["frames"]
base = "/mnt/project-files/explainer-engine/demo_truce_1914/pictures/"
S = {s["shot_id"]: s for s in script["shots"]}
for sid in ids or [s["shot_id"] for s in script["shots"] if s["route"] == "still_25d"]:
    sh = dict(S[sid]); sh["target_duration_seconds"] = min(secs, sh["target_duration_seconds"]) if secs else sh["target_duration_seconds"]
    t = time.time()
    try:
        r = L.render_clip(sh, Path(base + F[sid + "_start"]["file"]), out / f"{sid}.mp4", width=w, height=w * 9 // 16, fps=24, script=script)
        g = r["gates"]
        bad = [(x["id"] if "id" in x else x.get("name"), x.get("status")) for x in g.get("rows", g.get("checks", [])) if x.get("status") not in ("PASS", None)]
        print(sid, g["status"], r["families"], bad, f"{time.time()-t:.0f}s", flush=True)
    except Exception as e:
        print(sid, "ERROR", type(e).__name__, str(e)[:300], flush=True)
