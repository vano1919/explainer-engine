# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file>
#   --script-url <its HF copy> (OR-21, OR-23; LT-15 boot 25 min).
# xworld_v1 (D-80): one LoRA on Qwen-Image-2.1 for the R&M look and the scene sequence (LT-69); plan agreed by ვანო
# 2026-10-26 02:15 Tbilisi ("ყველა კი"). Checkpoints, samples and logs to HF every 5 min; the pod stops when this returns.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<'PY'
from huggingface_hub import HfApi
import os
a = HfApi(); R = "vano1919/tmr-artifacts"; P = "lora_plan_2026-10-26/train_xworld_v1"
try:
    a.upload_folder(folder_path="/workspace/out", path_in_repo=P + "/log", repo_id=R, repo_type="dataset")
    if os.path.exists("/workspace/train.log"):
        a.upload_file(path_or_fileobj="/workspace/train.log", path_in_repo=P + "/train.log", repo_id=R, repo_type="dataset")
    if os.path.isdir("/workspace/output/xworld_v1"):
        a.upload_folder(folder_path="/workspace/output/xworld_v1", path_in_repo=P + "/output", repo_id=R, repo_type="dataset",
                        ignore_patterns=["*.pt", "optimizer*", "_latent_cache/*", "**/_latent_cache/*"])
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
stage setup
nvidia-smi || true; free -g || true
( while true; do sleep 240; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & EARLY=$!
timeout 120 python -c "import torch;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi
pip install -q -U "huggingface_hub[hf_transfer]<2" || true
stage download
python - <<'PY'
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/dataset_xworld_v1/*", "lora_plan_2026-10-26/dataset_xworld_v1/**",
                  "lora_plan_2026-10-26/train_xworld_v1/code/*", "lora_plan_2026-10-26/caption_xworld_v1/captions_reviewed.jsonl"])
s("Qwen/Qwen-Image-2.1", allow_patterns=["*.json", "processor/*", "scheduler/*", "*.txt"])
print("dl ok", flush=True)
PY
D=/workspace/dl/lora_plan_2026-10-26
python $D/train_xworld_v1/code/xworld_v1_build.py $D/dataset_xworld_v1 $D/caption_xworld_v1/captions_reviewed.jsonl \
  /workspace/ds $D/train_xworld_v1/code/xworld_v1.yaml /workspace/cfg.yaml || { echo "BUILD FAILED"; up; exit 1; }
cp /workspace/cfg.yaml /workspace/out/cfg.yaml
stage install
# the image's ai-toolkit predates Qwen-Image 2.1 (arch qwen_image_2): a fresh clone on the image's packages (qi21 v1, 10-25)
git clone -q --depth 1 https://github.com/ostris/ai-toolkit /workspace/aitk && cd /workspace/aitk && git log -1 --format=%H \
  && python -c "import sys; sys.path.insert(0,'.'); from extensions_built_in.diffusion_models.qwen_image_2.qwen_image_2 import QwenImage2Model; print('arch ok')"
up
stage train
kill $EARLY 2>/dev/null
( while true; do sleep 300; date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
cd /workspace/aitk
python run.py /workspace/cfg.yaml > /workspace/train.log 2>&1
echo "TRAIN EXIT $?"
kill $LOOP 2>/dev/null
stage done
up
# what the upload skips (optimizer state, latent cache) moves aside so the vault check sees exactly the uploaded set
mkdir -p /workspace/aside /workspace/ee/explainer_engine /workspace/ee/config
cp $D/train_xworld_v1/code/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp $D/train_xworld_v1/code/vault.json /workspace/ee/config/vault.json
cd /workspace/output/xworld_v1 && find . \( -name "*.pt" -o -name "optimizer*" -o -path "*_latent_cache*" \) -type f -exec mv --backup=numbered {} /workspace/aside/ \;
find /workspace/output/xworld_v1 -type d -empty -delete
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/output/xworld_v1 --to lora_plan_2026-10-26/train_xworld_v1/output --repo datasets/vano1919/tmr-artifacts
# returns: the start command (runpod.script_cmd) stops the pod at once
