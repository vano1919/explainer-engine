# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file>
#   --script-url <its HF copy> (OR-21, OR-23).
# xworld_v2 round 0 (D-80; review 2026-10-26 + ვანო's choice): the BASE Qwen-Image-2.1, no LoRA, draws the three v2 scenes
# (xworld_v2_scenes.py: P1, P2, P3, P2F x seeds 11 and 23), Qwen3-VL measures them (xworld_v2_judge.py), sheets are made
# (xworld_v2_sheet.py). It shows how well the base model keeps the scene logic before any training. Pictures and the log go
# to HF (train_xworld_v2/round0) every 5 min and at the end; the pod stops when this returns.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
P=lora_plan_2026-10-26
up(){ python - <<'PY'
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", repo_id="vano1919/tmr-artifacts", repo_type="dataset",
                          path_in_repo="lora_plan_2026-10-26/train_xworld_v2/round0")
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
nvidia-smi || true
( while true; do sleep 300; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
timeout 120 python -c "import torch;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi
timeout 900 pip install -q -U "huggingface_hub[hf_transfer]<2" peft || true
# the whole model on the card only when it holds it (>= 80 GB); a 48 GB card keeps the tested CPU offload
MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1); [ "${MEM:-0}" -ge 80000 ] && export XW_GPU_MODE=model_full_load
echo "gpu mem $MEM mode ${XW_GPU_MODE:-model_cpu_offload}"
timeout 900 pip install -q -U "git+https://github.com/huggingface/diffusers" || true
( cd /workspace && timeout 600 git clone -q --depth 1 https://github.com/aigc-apps/VideoX-Fun.git \
  && timeout 900 pip install -q --break-system-packages einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy \
     func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations \
  && cd VideoX-Fun && python -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" )
python - <<'PY'
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/train_xworld_v2/code/**"])
s("Qwen/Qwen-Image-2.1")
s("Qwen/Qwen3-VL-8B-Instruct")
print("dl ok", flush=True)
PY
C=/workspace/dl/$P/train_xworld_v2/code
O=/workspace/out/round0
( cd $C && timeout 4200 python xworld_v2_scenes.py $C/scenes $O base ); echo "SCENES EXIT $?"
up
( cd $C && timeout 900 python xworld_v2_judge.py $C/scenes $O ); echo "JUDGE EXIT $?"
( cd $C && python xworld_v2_sheet.py $C/scenes $O "base (round 0)" ); echo "SHEET EXIT $?"
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
# returns: the start command (runpod.script_cmd) stops the pod at once
