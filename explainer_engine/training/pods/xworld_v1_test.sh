# Started by: python -m explainer_engine.cloud.runpod create --script <this file> --script-url <its HF copy> (OR-21, OR-23).
# Prompt-type test of xworld_v1 on held-out R&M scenes (D-80, LT-75); agreed by ვანო 2026-10-26 02:15 Tbilisi ("ყველა კი").
# The two checkpoints come from code/picks.json (Claude picks them from the training samples before this pod starts).
# Pictures and the log go to HF every 5 min; the pod stops when this returns.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1
up(){ python - <<'PY'
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="lora_plan_2026-10-26/test_xworld_v1/out",
                          repo_id="vano1919/tmr-artifacts", repo_type="dataset")
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
nvidia-smi || true
( while true; do sleep 300; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
timeout 120 python -c "import torch;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi
timeout 900 pip install -q -U "huggingface_hub[hf_transfer]<2" peft || true
timeout 900 pip install -q -U "git+https://github.com/huggingface/diffusers" || true
( cd /workspace && timeout 600 git clone -q --depth 1 https://github.com/aigc-apps/VideoX-Fun.git \
  && timeout 900 pip install -q --break-system-packages einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy \
     func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations \
  && cd VideoX-Fun && python -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" )
python - <<'PY'
import json
from huggingface_hub import snapshot_download as s, hf_hub_download as d
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/dataset_xworld_v1/manifest.json", "lora_plan_2026-10-26/dataset_xworld_v1/frames/*",
                  "lora_plan_2026-10-26/test_xworld_v1/code/*", "lora_plan_2026-10-26/caption_xworld_v1/captions_reviewed.jsonl"])
picks = json.load(open("/workspace/dl/lora_plan_2026-10-26/test_xworld_v1/code/picks.json"))
for k, f in picks.items():
    p = d("vano1919/tmr-artifacts", f, repo_type="dataset")
    open(f"/workspace/lora_{k}.txt", "w").write(p)
s("Qwen/Qwen-Image-2.1")
print("dl ok", flush=True)
PY
D=/workspace/dl/lora_plan_2026-10-26
python $D/test_xworld_v1/code/xworld_v1_test.py $D/dataset_xworld_v1 $D/caption_xworld_v1/captions_reviewed.jsonl \
  /workspace/out "$(cat /workspace/lora_A.txt)" "$(cat /workspace/lora_B.txt)"
echo "TEST EXIT $?"
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
# returns: the start command (runpod.script_cmd) stops the pod at once
