# Night run pod (2026-10-22/23): Wan 2.2 style LoRA + keyframes (klein + photo LoRA) + FLF2V clips + SeedVR2.
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
python - <<'PY' > /workspace/out/download.log 2>&1 &
from huggingface_hub import snapshot_download as s
import os, shutil, glob
s("vano1919/tmr-artifacts", repo_type="dataset", allow_patterns="lora_plan_2026-10-22/dataset_style_v1/*", local_dir="/workspace/dl")
os.makedirs("/workspace/ds", exist_ok=True)
for f in glob.glob("/workspace/dl/lora_plan_2026-10-22/dataset_style_v1/*"): shutil.copy(f, "/workspace/ds/")
print("dataset", len(os.listdir("/workspace/ds")), flush=True)
s("ai-toolkit/Wan2.2-T2V-A14B-Diffusers-bf16"); print("t2v ok", flush=True)
s("Wan-AI/Wan2.2-I2V-A14B-Diffusers", allow_patterns=["text_encoder/*", "tokenizer/*", "vae/*", "model_index.json", "scheduler/*"]); print("base parts ok", flush=True)
s("ai-toolkit/Wan2.2-I2V-A14B-Diffusers-bf16"); print("i2v ok", flush=True)
s("lightx2v/Wan2.2-Distill-Loras", allow_patterns=["*i2v*"]); print("light ok", flush=True)
s("black-forest-labs/FLUX.2-klein-base-4B"); print("klein ok", flush=True)
open("/workspace/dl/ALL_DONE", "w").write("ok")
PY
DL=$!
# the dataset and T2V weights come first; training can start as soon as they are there
for i in $(seq 1 120); do grep -q "t2v ok" /workspace/out/download.log && break; sleep 15; done
grep -q "t2v ok" /workspace/out/download.log || fatal "T2V download did not finish in 30 min"
up

stage smoke
for i in $(seq 1 80); do [ -f /workspace/dl/ALL_DONE ] && break; sleep 15; done
getcode; cd /workspace/code
mkdir -p /workspace/smoke/kf
timeout 900 python kf.py shots.json none /workspace/out/smoke_kf --smoke > /workspace/out/smoke_kf.log 2>&1 || fatal "SMOKE KF"
cp "$(ls /workspace/ds/*.jpg | head -1)" /workspace/smoke/kf/c01_first.png
timeout 1500 python clips.py shots.json /workspace/smoke/kf /workspace/out/smoke_clips --res 480 --smoke > /workspace/out/smoke_clips.log 2>&1 || fatal "SMOKE CLIPS"
python -c "import torch,gc;gc.collect();torch.cuda.empty_cache()"
up

stage train
getcode
cd /app/ai-toolkit 2>/dev/null || cd /workspace/ai-toolkit || fatal "no ai-toolkit"
( while true; do sleep 600; up; done ) & LOOP=$!
timeout $(left $(at 160)) python run.py /workspace/code/wan_lora.yaml > /workspace/out/train.log 2>&1
echo "TRAIN EXIT $?"
kill $LOOP 2>/dev/null
pkill -f run.py 2>/dev/null; sleep 5
python -c "import torch,gc;gc.collect();torch.cuda.empty_cache()"
up


stage photo_lora
python - <<'PY' > /workspace/out/photo_lora.txt 2>&1
# control.json on HF (night_run_2026-10-22/control.json) may name the photo LoRA; else the final or newest checkpoint
import json, os, re
from huggingface_hub import HfApi, hf_hub_download
a = HfApi(); R = "vano1919/tmr-artifacts"
fs = a.list_repo_files(R, repo_type="dataset")
ctl = {}
if "night_run_2026-10-22/control.json" in fs:
    ctl = json.load(open(hf_hub_download(R, "night_run_2026-10-22/control.json", repo_type="dataset", force_download=True)))
cands = [f for f in fs if f.startswith("lora_plan_2026-10-22/train_style_v1/output/") and f.endswith(".safetensors")]
pick = ctl.get("photo_lora")
if not pick and cands:
    final = [f for f in cands if re.search(r"wldnk_style_v1\.safetensors$", f)]
    pick = final[0] if final else sorted(cands)[-1]
print("PICK", pick, "STRENGTH", ctl.get("photo_strength", 1.0))
if pick:
    p = hf_hub_download(R, pick, repo_type="dataset", local_dir="/workspace/photo_lora")
    open("/workspace/photo_lora.path", "w").write(p)
open("/workspace/photo_lora.strength", "w").write(str(ctl.get("photo_strength", 1.0)))
PY
cat /workspace/out/photo_lora.txt
PL=$(cat /workspace/photo_lora.path 2>/dev/null); PS=$(cat /workspace/photo_lora.strength 2>/dev/null || echo 1.0)

stage keyframes
getcode; cd /workspace/code
timeout $(left $(at 225)) python kf.py shots.json "$PL" /workspace/out/kf --strength $PS > /workspace/out/kf.log 2>&1
echo "KF EXIT $?"
up

stage clips
HIGH=$(ls -t /workspace/out/train/wldnk_wan22_v1/*_high_noise.safetensors 2>/dev/null | head -1)
LOW=$(ls -t /workspace/out/train/wldnk_wan22_v1/*_low_noise.safetensors 2>/dev/null | head -1)
STYLE=""; [ -n "$HIGH" ] && [ -n "$LOW" ] && STYLE="--style $HIGH $LOW --style-strength 0.8"
echo "STYLE $STYLE"
# resolution by the time left: 720p when at least 16 x 9 min remain, else 480p
REM=$(left $(at 375)); RES=480; [ $REM -gt 8640 ] && RES=720
getcode; cd /workspace/code
( while true; do sleep 600; up; done ) & LOOP=$!
timeout $(left $(at 385)) python clips.py shots.json /workspace/out/kf /workspace/out/clips --res $RES $STYLE --deadline $(at 375) > /workspace/out/clips.log 2>&1
echo "CLIPS EXIT $?"
kill $LOOP 2>/dev/null
up

stage upscale
if [ $(left $(at 430)) -gt 900 ] && ls /workspace/out/clips/*.mp4 >/dev/null 2>&1; then
  cd /workspace && git clone -q --depth 1 https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler seedvr2 && cd seedvr2 && \
  pip install -q rotary_embedding_torch gguf omegaconf --break-system-packages >/dev/null 2>&1
  timeout $(left $(at 430)) python inference_cli.py /workspace/out/clips/ --output /workspace/out/up/ --resolution 1440 \
     --batch_size 21 --uniform_batch_size --temporal_overlap 3 --dit_model seedvr2_ema_3b_fp16.safetensors \
     --model_dir /workspace/seedvr2_models --vae_encode_tiled --vae_decode_tiled --dit_offload_device cpu \
     --vae_offload_device cpu --cache_dit --cache_vae --video_backend ffmpeg > /workspace/out/upscale.log 2>&1
  echo "UPSCALE EXIT $?"
fi

stage done
up
stopself
sleep 900
