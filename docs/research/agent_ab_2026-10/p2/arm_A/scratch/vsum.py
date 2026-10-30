import subprocess, sys, collections, re
ROOT = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
r = subprocess.run([sys.executable, ROOT + "scratch/val.py"], capture_output=True, text=True)
open(ROOT + "scratch/val_out.txt", "w").write(r.stdout)
EOF_ = None
