"""Create the night-run pod through the one pod manager (preflight, ledger, guard). Run from an explainer-engine checkout."""
import base64, json, sys
from explainer_engine.cloud import runpod as rp
from explainer_engine.core.ledger import Run

MAX_USD, MAX_H = 2.4, 7.5  # under 80 % of the ledger cap 3.6 (the ledger's stop rule), minus ~$0.45 of tries 1-2
CAP = 3.6
LEDGER = "/mnt/project-files/explainer-engine/hybrid_model_2026-10-22/night_run/night_run_ledger.json"
POD_SH = "/mnt/project-files/explainer-engine/hybrid_model_2026-10-22/night_run/pod/pod.sh"
api = rp.Api()
why = rp.preflight_create(api, max_usd=MAX_USD, max_hours=MAX_H, gpu="default")
if why:
    raise SystemExit("refused: " + "; ".join(why))
run = Run.open(LEDGER, caps={"runpod_usd": CAP}, purpose="night run: Wan 2.2 style LoRA + 2-min test video (ვანო 22:50-22:54)")
run.reserve("runpod_usd", MAX_USD, item="pod:pending")
body = rp.create_body(rp.pod_name("ee-night", MAX_H), "default", min_ram=40, volume=0)  # container disk only: nothing bills once stopped
body.pop("volumeMountPath", None)
body.update(imageName="ostris/aitoolkit:latest", containerDiskInGb=200, ports=["22/tcp"], gpuTypePriority="custom")
URL = "https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/night_run_2026-10-22/code/pod.sh"
body["dockerStartCmd"] = ["bash", "-c", 'mkdir -p /workspace; curl -fsSL -H "Authorization: Bearer $HF_TOKEN" ' + URL +
                          ' -o /workspace/pod.sh && bash /workspace/pod.sh; tail -f /dev/null']
body["allowedCudaVersions"] = ["12.4", "12.6", "12.8", "12.9", "13.0"]
pod = None
for cloud, gpus in [("COMMUNITY", ["NVIDIA A40", "NVIDIA RTX A6000", "NVIDIA L40S", "NVIDIA L40", "NVIDIA RTX 6000 Ada Generation"]),
                    ("SECURE", ["NVIDIA A40", "NVIDIA RTX A6000", "NVIDIA L40S", "NVIDIA L40", "NVIDIA RTX 6000 Ada Generation"])]:
    body.update(cloudType=cloud, gpuTypeIds=gpus, name=rp.pod_name("ee-night", MAX_H))
    try:
        pod = rp.create(api, body, max_price=0.8)
        print("cloud", cloud)
        break
    except rp.RunPodError as e:
        print(cloud, "unavailable:", str(e)[:900])
if pod is None:
    Run.open(LEDGER).settle("runpod_usd", "pod:pending", 0.0)
    raise SystemExit("no GPU")
Run.open(LEDGER).rename_reservation("pod:pending", f"pod:{pod['id']}")
rp.new_session(pod, max_usd=MAX_USD, max_hours=MAX_H, on_cap="stop", ledger=LEDGER)
m = pod.get("machine") if isinstance(pod.get("machine"), dict) else {}
print("pod", pod["id"], body["name"], pod.get("costPerHr"), m.get("gpuDisplayName"))
print("guard pid", rp.guard_detached(pod["id"]))
