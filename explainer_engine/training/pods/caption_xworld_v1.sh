# Started by: python -m explainer_engine.cloud.runpod create --script <this file> --script-url <its HF copy> (OR-21, OR-23).
# Captions for the xworld_v1 material (D-80) with Qwen3-VL-8B-Instruct: 1336 descriptions + 665 change lines (plan agreed
# with the creator before the pod). Results every 5 min to HF; the start command stops the pod when this returns.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1
P=lora_plan_2026-10-26/caption_xworld_v1
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<'PY'
from huggingface_hub import HfApi
try:
    HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="lora_plan_2026-10-26/caption_xworld_v1/out",
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
pip install -q -U "huggingface_hub[hf_transfer]<2" "transformers>=4.57,<5" accelerate || true
python -c "import transformers;print('transformers',transformers.__version__)"
stage download
python - <<'PY'
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/dataset_xworld_v1/*", "lora_plan_2026-10-26/dataset_xworld_v1/**",
                  "lora_plan_2026-10-26/caption_xworld_v1/code/*", "lora_plan_2026-10-26/caption_xworld_v1/out/captions.jsonl"])
s("Qwen/Qwen3-VL-8B-Instruct")
print("dl ok", flush=True)
PY
D=/workspace/dl/lora_plan_2026-10-26
cp $D/caption_xworld_v1/out/captions.jsonl /workspace/out/ 2>/dev/null || true   # a restarted pod resumes, never pays twice
stage first8
python $D/caption_xworld_v1/code/caption_xworld_v1.py $D/dataset_xworld_v1 /workspace/out --limit 8 --batch 4
echo "FIRST8 EXIT $?"; up
stage all
python $D/caption_xworld_v1/code/caption_xworld_v1.py $D/dataset_xworld_v1 /workspace/out --batch 4
echo "ALL EXIT $?"
kill $LOOP 2>/dev/null
wc -l /workspace/out/captions.jsonl
stage done
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
# returns: the start command (runpod.script_cmd) stops the pod at once
