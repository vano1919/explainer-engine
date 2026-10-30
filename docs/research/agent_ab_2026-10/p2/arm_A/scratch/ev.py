import json, sys
sys.path.insert(0, "/home/user/explainer-engine")
from explainer_engine.production import timing as T, validate as V
from explainer_engine.edit import motion_lint as M
d = json.load(open("/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/scratch/_val_copy.json"))
timed = T.time_script(d, V.estimated_words(d))
ev = M.events(timed)
print("duration", timed["duration"])
t = 0
while t < timed["duration"]:
    ks = sorted({k for x, k in ev if t <= x < t + 60})
    n = sum(1 for s in timed["shots"] if t <= s["start"] < t + 60)
    print(f"{t:4d}-{t+60:4d} shots {n:2d} kinds {len(ks)} {ks}")
    t += 60
if len(sys.argv) > 1:
    a, b = float(sys.argv[1]), float(sys.argv[2])
    for s in timed["shots"]:
        if a <= s["start"] < b:
            print(f"{s['id']} {s['segment']} {s['start']:7.1f} {s['end']-s['start']:5.1f}s {s['picture']:16s} {s['at']}")
