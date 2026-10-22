"""Night-run watchdog (started once by kf.py --smoke). The pod's money ceiling ($2.4 at up to $0.79/h) ends the session after
about 182 min, earlier than pod.sh's stage clock assumed, so: stop training at TRAIN_END (checkpoints are saved every 100 steps),
and upload the upscaled clips shortly before the guard stops the pod."""
import os, subprocess, time
POD_START = int(open("/workspace/T0").read())  # written by pod.sh
TRAIN_END = POD_START + 85 * 60
UP_AT = (POD_START + 165 * 60, POD_START + 174 * 60)
def wait(t):
    while time.time() < t:
        time.sleep(20)
wait(TRAIN_END)
subprocess.run(["pkill", "-f", "run.py /workspace/code/wan_lora.yaml"])
print("train stop sent", flush=True)
for t in UP_AT:
    wait(t)
    try:
        from huggingface_hub import HfApi
        if os.path.isdir("/workspace/out/up"):
            HfApi().upload_folder(folder_path="/workspace/out/up", path_in_repo="night_run_2026-10-22/up",
                                  repo_id="vano1919/tmr-artifacts", repo_type="dataset")
        HfApi().upload_file(path_or_fileobj="/workspace/out/pod.log", path_in_repo="night_run_2026-10-22/pod.log",
                            repo_id="vano1919/tmr-artifacts", repo_type="dataset")
        print("uploaded", t, flush=True)
    except Exception as e:
        print("upload failed", e, flush=True)
