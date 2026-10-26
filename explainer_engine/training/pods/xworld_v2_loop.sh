# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file> --script-url <its HF copy>
#   --heartbeat datasets/vano1919/tmr-artifacts:lora_plan_2026-10-26/train_xworld_v2/loop/round_${ROUND}/out/beat.txt (OR-21, OR-23, OR-24, OR-25).
# Strategy loop, one round (xworld_v2_loop_run.py, Opus plan STRATEGY_LOOP_PLAN_2026-10-26.md section 8): the control inputs are
# rendered first (free geometry, on the pod CPU), then the control rows (M2E50, M4E50, M4, M5) and the plain rows (S2T, S2E) are drawn
# on ONE checkpoint of the xworld_v2 run. ROUND picks code/loop/round_N.json. No training. Everything goes to HF every 5 min and at the end.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
export XW_GPU_MODE=${XW_GPU_MODE:-model_full_load}  # round 3a: a 80 GB card keeps everything loaded (about twice as fast as offload); load_pipeline falls back to offload on an error
P=lora_plan_2026-10-26
ROUND=${ROUND:-3a}
CKPT=${CKPT:-xworld_v2_000003000.safetensors}  # ვანო 16:32Z: the 3000 image test and P2S on ONE new pod; the training pod stops once 3000 is on HF
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<PY
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="lora_plan_2026-10-26/train_xworld_v2/loop/round_${ROUND}/out",
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
                    "lora_plan_2026-10-26/train_xworld_v2/p2s/out/p2s/jobs.json"])
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
up
stage inputs
O=/workspace/out/loop; IN=/workspace/out/inputs; M=$D/p2s/out/p2s; CFG=$C/loop/round_${ROUND}.json
mkdir -p $O $IN
( cd $C && timeout 900 /workspace/vx/bin/python xworld_v2_loop_run.py inputs $CFG scenes scenes/more scenes/sets $M $IN ); echo "INPUTS EXIT $?"
up
stage draw
( cd $C && timeout 5400 /workspace/vx/bin/python xworld_v2_loop_run.py draw $CFG scenes scenes/more $IN $M $O $D/output/$CKPT ); echo "LOOP EXIT $?"
echo "LOOP DONE $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt
kill $LOOP 2>/dev/null
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
python - <<PY
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl2", allow_patterns=["lora_plan_2026-10-26/train_xworld_v1/code/vault*"])
PY
mkdir -p /workspace/ee/explainer_engine /workspace/ee/config
cp /workspace/dl2/$P/train_xworld_v1/code/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp /workspace/dl2/$P/train_xworld_v1/code/vault.json /workspace/ee/config/vault.json
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/out --to lora_plan_2026-10-26/train_xworld_v2/loop/round_${ROUND}/out --repo datasets/vano1919/tmr-artifacts
# returns: the start command (runpod.script_cmd) stops the pod at once
