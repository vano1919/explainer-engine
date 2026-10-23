# Night run, clips only (2026-10-23): the trained Wan 2.2 style LoRA + the keyframes from HF -> FLF2V clips at 720p (480p once the time runs short).
# Every stage has a deadline; logs and results go to HF after every stage; the pod stops itself at the end or on a fatal error.
set -x
mkdir -p /workspace/out /workspace/code
exec > /workspace/out/pod.log 2>&1
T0=$(date +%s); echo $T0 > /workspace/T0
H=vano1919/tmr-artifacts; P=night_run_2026-10-22
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1
stopself(){ curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID/stop"; }
at(){ echo $((T0 + $1 * 60)); }           # minutes after start -> epoch
left(){ echo $(( $1 - $(date +%s) )); }    # seconds until an epoch
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S) ($(( ($(date +%s)-T0)/60 )) min)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - "$@" <<'PY'
import os, sys
from huggingface_hub import HfApi
a = HfApi()
try:
    a.upload_folder(folder_path="/workspace/out", path_in_repo="night_run_2026-10-22", repo_id="vano1919/tmr-artifacts",
                    repo_type="dataset", ignore_patterns=["train/**/_latent_cache/**", "train/**/*.pt", "train/**/optimizer*",
                                                          "train/**/.job_config*", "**/*.tmp"])
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
fatal(){ echo "FATAL $1"; up; stopself; sleep 900; exit 1; }

stage setup
nvidia-smi || true; free -g || true; df -h /workspace || true
# datacenter GPUs (A40, L40S) need the image's CUDA forward-compat libs on an older driver; consumer cards fail with them (804)
python -c "import torch;torch.zeros(1).cuda();print('first cuda check ok')" 2>&1 | tail -3
if ! python -c "import torch,sys;sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
  mv /usr/local/cuda/compat /usr/local/cuda/compat.off 2>/dev/null || true
  rm -f /etc/ld.so.conf.d/*compat* 2>/dev/null; ldconfig 2>/dev/null || true
  export LD_LIBRARY_PATH=$(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -v compat | paste -sd:)
fi
python -c "import torch;print('torch check', torch.__version__, torch.cuda.is_available())" || true
# a pip that must uninstall debian's numpy aborts halfway (try 4: torch half-replaced): never uninstall, install beside
python -c "import torch,sys;sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null || pip install -q --ignore-installed torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128 --break-system-packages
python -c "import torch;print('cuda ok',torch.cuda.is_available(),torch.version.cuda,torch.cuda.get_device_name(0))" || fatal "CUDA BROKEN"
pip install -q -U "huggingface_hub[hf_transfer]<2" --break-system-packages || pip install -q -U "huggingface_hub[hf_transfer]<2" || true
# the code lives on HF and is fetched again before every stage, so a fix uploaded at night reaches the running pod
getcode(){ python - <<'PY'
from huggingface_hub import HfApi, hf_hub_download
import shutil
a = HfApi()
for f in a.list_repo_files("vano1919/tmr-artifacts", repo_type="dataset"):
    if f.startswith("night_run_2026-10-22/code/"):
        p = hf_hub_download("vano1919/tmr-artifacts", f, repo_type="dataset", force_download=True)
        shutil.copy(p, "/workspace/code/" + f.rsplit("/", 1)[1])
print("code ok")
PY
}
getcode || fatal "no code"

stage download
pip install -q imageio-ffmpeg --break-system-packages || pip install -q imageio-ffmpeg || true
python - <<'PY' > /workspace/out/download.log 2>&1
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["night_run_2026-10-22/kf/*", "night_run_2026-10-22/train/wldnk_wan22_v1/wldnk_wan22_v1_*_noise.safetensors"])
print("kf+lora ok", flush=True)
s("Wan-AI/Wan2.2-I2V-A14B-Diffusers", allow_patterns=["text_encoder/*", "tokenizer/*", "vae/*", "model_index.json", "scheduler/*"]); print("base parts ok", flush=True)
s("ai-toolkit/Wan2.2-I2V-A14B-Diffusers-bf16"); print("i2v ok", flush=True)
s("lightx2v/Wan2.2-Distill-Loras", allow_patterns=["*i2v*"]); print("light ok", flush=True)
PY
grep -q "light ok" /workspace/out/download.log || fatal "download"
up

stage clips
# minutes this pod may draw clips: control_clips.json (written by the launcher from the real price), else 26
MIN=$(python - <<'PY'
import json
from huggingface_hub import hf_hub_download
try:
    print(int(json.load(open(hf_hub_download("vano1919/tmr-artifacts", "night_run_2026-10-22/control_clips.json",
                                              repo_type="dataset", force_download=True)))["minutes"]))
except Exception:
    print(26)
PY
)
echo "CLIP MINUTES $MIN"
getcode; cd /workspace/code
L=/workspace/dl/night_run_2026-10-22/train/wldnk_wan22_v1
( while true; do sleep 300; up; done ) & LOOP=$!
timeout $(left $(at $((MIN + 4)))) python clips.py shots.json /workspace/dl/night_run_2026-10-22/kf /workspace/out/clips2 --res 720 \
  --style $L/wldnk_wan22_v1_high_noise.safetensors $L/wldnk_wan22_v1_low_noise.safetensors --style-strength 0.8 \
  --deadline $(at $MIN) > /workspace/out/clips2.log 2>&1
echo "CLIPS EXIT $?"
kill $LOOP 2>/dev/null

stage done
up
stopself
sleep 900
