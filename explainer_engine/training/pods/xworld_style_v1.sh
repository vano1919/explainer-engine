# Started by: python -m explainer_engine.cloud.runpod create --script <this file> --script-url <its HF copy> (OR-21).
# Style LoRA xworld_style_v1 on Qwen-Image-2512 from 95 Rick and Morty frames (ვანო 2026-10-26 00:03 Tbilisi: "აიღე ეს ვიდეოები და დაიწყე დასწავლა").
# rank 16 (less copying), content-only captions with the main cast named, samples every 500 steps test our prompt rules.
set -x
mkdir -p /workspace/out /workspace/w
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1
P=lora_plan_2026-10-22/train_xworld_v1
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<'PY'
from huggingface_hub import HfApi
import os
a = HfApi(); R = "vano1919/tmr-artifacts"; P = "lora_plan_2026-10-22/train_xworld_v1"
try:
    a.upload_folder(folder_path="/workspace/out", path_in_repo=P + "/log", repo_id=R, repo_type="dataset")
    if os.path.exists("/workspace/train.log"):
        a.upload_file(path_or_fileobj="/workspace/train.log", path_in_repo=P + "/train.log", repo_id=R, repo_type="dataset")
    if os.path.isdir("/workspace/output/xworld_style_v1"):
        a.upload_folder(folder_path="/workspace/output/xworld_style_v1", path_in_repo=P + "/output", repo_id=R, repo_type="dataset",
                        ignore_patterns=["*.pt", "optimizer*", "_latent_cache/*", "**/_latent_cache/*"])
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
stage setup
nvidia-smi || true; free -g || true
( while true; do sleep 240; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & EARLY=$!
timeout 120 python -c "import torch,sys;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?; echo "cuda check rc=$rc"
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi   # the start command stops the pod
pip install -q -U "huggingface_hub[hf_transfer]<2" || true
stage download
python - <<'PY'
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl", allow_patterns=["lora_plan_2026-10-22/dataset_xworld_v1/train/*",
  "lora_plan_2026-10-22/train_xworld_v1/code/*"])
print("dl ok", flush=True)
PY
mkdir -p /workspace/ds /workspace/ee/explainer_engine /workspace/ee/config
cp -r /workspace/dl/lora_plan_2026-10-22/dataset_xworld_v1/train /workspace/ds/
C=/workspace/dl/lora_plan_2026-10-22/train_xworld_v1/code
cp $C/cfg.yaml /workspace/cfg.yaml; cp $C/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp $C/vault.json /workspace/ee/config/vault.json
ls /workspace/ds/train | wc -l
up
stage train
kill $EARLY 2>/dev/null
( while true; do sleep 300; date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
cd /app/ai-toolkit   # the image's own ai-toolkit (Qwen-Image-2512 arch qwen_image); nothing is cloned
pwd
python run.py /workspace/cfg.yaml > /workspace/train.log 2>&1
echo "TRAIN EXIT $?"
kill $LOOP 2>/dev/null
stage done
up
# what the upload skips (optimizer state, latent cache) moves aside so the vault check sees exactly the uploaded set
mkdir -p /workspace/aside && cd /workspace/output/xworld_style_v1 && find . \( -name "*.pt" -o -name "optimizer*" -o -path "*_latent_cache*" \) -type f -exec mv --backup=numbered {} /workspace/aside/ \;
find /workspace/output/xworld_style_v1 -type d -empty -delete
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/output/xworld_style_v1 --to $P/output --repo datasets/vano1919/tmr-artifacts
echo "VAULT $?"
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
# returns: the start command (runpod.script_cmd) stops the pod at once
