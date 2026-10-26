# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file> --script-url <its HF copy>
#   --heartbeat datasets/vano1919/tmr-artifacts:lora_plan_2026-10-26/train_xworld_v2/s3c/out/beat.txt (OR-21, OR-23, OR-24, OR-25).
# The S3c depth-ControlNet test (xworld_v2_s3c.py, the Opus plan S3C_CONTROLNET_PLAN_2026-10-26.md): step 0 (does the LoRA match the
# control transformer? stops at < 100 %), pass A (control pipeline + depth) and pass B (edit pipeline with the master and the sheet)
# on ONE checkpoint of the xworld_v2 run. Reads the P2S master and sheets and the S3 depth renders that the earlier pod put on HF.
# No training. Everything goes to HF every 5 min and at the end.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
P=lora_plan_2026-10-26
CKPT=${CKPT:-xworld_v2_000003000.safetensors}  # ვანო 16:32Z: the 3000 image test and P2S on ONE new pod; the training pod stops once 3000 is on HF
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<'PY'
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="lora_plan_2026-10-26/train_xworld_v2/s3c/out",
                          repo_id="vano1919/tmr-artifacts", repo_type="dataset")
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
stage setup
nvidia-smi || true
( while true; do sleep 300; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
timeout 120 python -c "import torch;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi
timeout 900 pip install -q -U "huggingface_hub[hf_transfer]<2" || true
stage download
python - <<PY
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/train_xworld_v2/code/**", "lora_plan_2026-10-26/train_xworld_v2/output/$CKPT",
                    "lora_plan_2026-10-26/train_xworld_v2/p2s/out/p2s/*_s0.png", "lora_plan_2026-10-26/train_xworld_v2/p2s/out/p2s/*_sheet_*.png",
                    "lora_plan_2026-10-26/train_xworld_v2/p2s/out/s3/*_depth.png"])
s("Qwen/Qwen-Image-2.1")
print("dl ok", flush=True)
PY
D=/workspace/dl/$P/train_xworld_v2; C=$D/code
stage install
python -m venv --system-site-packages /workspace/vx
timeout 900 /workspace/vx/bin/pip install -q -U peft "git+https://github.com/huggingface/diffusers" || true
( cd /workspace && timeout 600 git clone -q --depth 1 https://github.com/aigc-apps/VideoX-Fun.git \
  && timeout 900 /workspace/vx/bin/pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy \
     func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations \
  && cd VideoX-Fun && /workspace/vx/bin/python -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) \
  || { echo "VIDEOX FAILED"; up; exit 1; }
( cd /workspace/VideoX-Fun && grep -rn "depth\|control_image\|def __call__" videox_fun/pipeline/pipeline_qwenimage21.py 2>/dev/null | head -30 > /workspace/out/pipeline_inputs.txt; ls videox_fun/pipeline | grep -i qwen >> /workspace/out/pipeline_inputs.txt )
up
stage install
python -m venv --system-site-packages /workspace/vx
timeout 900 /workspace/vx/bin/pip install -q -U peft "git+https://github.com/huggingface/diffusers" || true
( cd /workspace && timeout 600 git clone -q --depth 1 https://github.com/aigc-apps/VideoX-Fun.git \
  && timeout 900 /workspace/vx/bin/pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy \
     func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations \
  && cd VideoX-Fun && /workspace/vx/bin/python -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) \
  || { echo "VIDEOX FAILED"; up; exit 1; }
( cd /workspace/VideoX-Fun && grep -rn "depth\|control_image\|def __call__" videox_fun/pipeline/pipeline_qwenimage21.py 2>/dev/null | head -30 > /workspace/out/pipeline_inputs.txt; ls videox_fun/pipeline | grep -i qwen >> /workspace/out/pipeline_inputs.txt )
up
up
stage s3c
O=/workspace/out/s3c
M=$D/p2s/out/p2s; S3=$D/p2s/out/s3
( cd $C && timeout 2400 /workspace/vx/bin/python xworld_v2_s3c.py $C/scenes $M $S3 $O $D/output/$CKPT tent,rome 2.5 ); echo "S3C EXIT $?"
( cd $C && python xworld_v2_s3c.py sheet $O ); echo "S3C DONE $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
python - <<PY
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl2", allow_patterns=["lora_plan_2026-10-26/train_xworld_v1/code/vault*"])
PY
mkdir -p /workspace/ee/explainer_engine /workspace/ee/config
cp /workspace/dl2/$P/train_xworld_v1/code/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp /workspace/dl2/$P/train_xworld_v1/code/vault.json /workspace/ee/config/vault.json
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/out --to lora_plan_2026-10-26/train_xworld_v2/s3c/out --repo datasets/vano1919/tmr-artifacts
# returns: the start command (runpod.script_cmd) stops the pod at once
