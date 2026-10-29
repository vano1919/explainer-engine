# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file> --script-url <its HF copy> (OR-21, OR-23).
# Draws a story from frame 0 with xworld_v1 2250 (D form, xworld_v1_story.py); ვანო's brief 2026-10-26 10:32 Tbilisi.
# STORY = the story's name: code and story file in lora_plan_2026-10-26/story_xworld_v1/<STORY>/code/, pictures to .../out/.
# The copy uploaded to <STORY>/code/ has its STORY= line set to that story (the start command passes no env).
# Pictures and the log go to HF every 5 min; the pod stops when this returns.
STORY=${STORY:-napoleon_tent}
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 STORY
up(){ python - <<'PY'
import os
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", repo_id="vano1919/tmr-artifacts", repo_type="dataset",
                          path_in_repo=f"lora_plan_2026-10-26/story_xworld_v1/{os.environ['STORY']}/out")
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
import json, os
from huggingface_hub import snapshot_download as s, hf_hub_download as d
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=[f"lora_plan_2026-10-26/story_xworld_v1/{os.environ['STORY']}/code/*",
                  "lora_plan_2026-10-26/test_xworld_v1/code/picks.json"])
picks = json.load(open("/workspace/dl/lora_plan_2026-10-26/test_xworld_v1/code/picks.json"))
open("/workspace/lora_A.txt", "w").write(d("vano1919/tmr-artifacts", picks["A"], repo_type="dataset"))
s("Qwen/Qwen-Image-2.1")
print("dl ok", flush=True)
PY
C=/workspace/dl/lora_plan_2026-10-26/story_xworld_v1/$STORY/code
python $C/xworld_v1_story.py $C/$STORY.json /workspace/out "$(cat /workspace/lora_A.txt)"
echo "STORY EXIT $?"
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
# returns: the start command (runpod.script_cmd) stops the pod at once
