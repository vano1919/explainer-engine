# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file> --script-url <its HF copy>
#   --heartbeat datasets/vano1919/tmr-artifacts:lora_plan_2026-10-26/train_xworld_v2/p2s/out/beat.txt (OR-21, OR-23, OR-24, OR-25).
# FIRST the regular image test of the same checkpoint (xworld_v2_scenes.py round, as after every training round), THEN
# the P2S reference test (xworld_v2_p2s.py): master + model sheets vs master only, cfg 4.0 vs 2.5, LoRA weight 1.0 vs 0.7, on ONE
# checkpoint of the xworld_v2 run (CKPT below, from HF). No training. Everything goes to HF every 5 min and at the end.
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
    HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="lora_plan_2026-10-26/train_xworld_v2/p2s/out",
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
  allow_patterns=["lora_plan_2026-10-26/train_xworld_v2/code/**", "lora_plan_2026-10-26/train_xworld_v2/output/$CKPT"])
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
up
stage round_test
R=/workspace/out/round_${CKPT:12:4}
( cd $C && timeout 1800 /workspace/vx/bin/python xworld_v2_scenes.py $C/scenes $R $D/output/$CKPT 1.0 round ); echo "SCENES EXIT $?"
( cd $C && python xworld_v2_sheet.py $C/scenes $R "step ${CKPT:12:4}" round ); echo "ROUND DONE $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt
up
stage p2s
O=/workspace/out/p2s
( cd $C && timeout 3000 /workspace/vx/bin/python xworld_v2_p2s.py $C/scenes $O $D/output/$CKPT ); echo "P2S EXIT $?"
( cd $C && python xworld_v2_p2s_sheet.py $O "$CKPT" ); echo "P2S DONE $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
python - <<PY
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl2", allow_patterns=["lora_plan_2026-10-26/train_xworld_v1/code/vault*"])
PY
mkdir -p /workspace/ee/explainer_engine /workspace/ee/config
cp /workspace/dl2/$P/train_xworld_v1/code/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp /workspace/dl2/$P/train_xworld_v1/code/vault.json /workspace/ee/config/vault.json
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/out --to lora_plan_2026-10-26/train_xworld_v2/p2s/out --repo datasets/vano1919/tmr-artifacts
# returns: the start command (runpod.script_cmd) stops the pod at once
