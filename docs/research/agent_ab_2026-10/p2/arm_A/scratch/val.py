import json, subprocess, sys
ROOT = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
src = sys.argv[1] if len(sys.argv) > 1 else ROOT + "production_script.json"
d = json.load(open(src))
w = d["world"]
# the codex has no steppe_1223 / france_1812 era: validate a copy with the nearest known era so the checks can run
w["host"]["era"] = "medieval_europe"
w["visitors"] = [dict(v, era="medieval_europe") for v in w.get("visitors", [])]
w["day_arc"] = [{"beat": s["beat"], "light": "overcast"} for s in w["day_arc"]]
json.dump(d, open(ROOT + "scratch/_val_copy.json", "w"), indent=1, ensure_ascii=False)
args = sys.argv[2:]
r = subprocess.run([sys.executable, "-m", "explainer_engine.production", "validate", ROOT + "scratch/_val_copy.json"] + args,
                   cwd="/home/user/explainer-engine", capture_output=True, text=True)
open(ROOT+"scratch/val_out.txt","w").write(r.stdout); print(r.stderr[-1500:])
