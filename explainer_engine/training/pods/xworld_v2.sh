# Started by: python -m explainer_engine.cloud.runpod create --image ostris/aitoolkit:latest --script <this file>
#   --script-url <its HF copy> --ref-hours 1.0 (OR-21, OR-23, OR-24; LT-15 boot 30 min). Plan confirmed by ვანო's decisions and the Opus thread
#   2026-10-26 12:52 (docs/PROGRESS.md): 20-step smoke run, then training in rounds of 750 steps up to 3000 (a checkpoint every 250);
#   after each round the checkpoint draws ROUND_TESTS (xworld_v2_scenes.py `round`: P3, P2F, P2R) and the sheets (xworld_v2_sheet.py
#   `round`) are made. No judge: ვანო rates the sheets by eye. Everything goes to HF every 5 min and at the end of every round;
#   the vault check (VT-01) ends the script and the pod stops when this returns.
set -x
mkdir -p /workspace/out
exec > /workspace/out/pod.log 2>&1
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
P=lora_plan_2026-10-26
stage(){ echo "=== STAGE $1 $(date -u +%H:%M:%S)"; echo "$1 $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt; }
up(){ python - <<'PY'
import os
from huggingface_hub import HfApi
a = HfApi(); R = "vano1919/tmr-artifacts"; P = "lora_plan_2026-10-26/train_xworld_v2"
try:
    a.upload_folder(folder_path="/workspace/out", path_in_repo=P + "/out", repo_id=R, repo_type="dataset")
    if os.path.exists("/workspace/train.log"):
        a.upload_file(path_or_fileobj="/workspace/train.log", path_in_repo=P + "/train.log", repo_id=R, repo_type="dataset")
    if os.path.isdir("/workspace/output/xworld_v2"):
        a.upload_folder(folder_path="/workspace/output/xworld_v2", path_in_repo=P + "/output", repo_id=R, repo_type="dataset",
                        ignore_patterns=["*.pt", "optimizer*", "_latent_cache/*", "**/_latent_cache/*"])
except Exception as e:
    print("UPLOAD FAILED", e)
PY
}
stage setup
nvidia-smi || true; free -g || true
( while true; do sleep 300; grep -q BAD_HOST /workspace/out/beat.txt 2>/dev/null || date -u +%H:%M:%S > /workspace/out/beat.txt; up; done ) & LOOP=$!
timeout 120 python -c "import torch;x=torch.ones(8,device='cuda');print('cuda ok',torch.cuda.get_device_name(0),(x*2).sum().item(),flush=True)"; rc=$?
if [ $rc -ne 0 ]; then echo "BAD_HOST cuda check rc=$rc" > /workspace/out/beat.txt; up; exit 1; fi
timeout 900 pip install -q -U "huggingface_hub[hf_transfer]<2" || true
stage download
python - <<'PY'
from huggingface_hub import snapshot_download as s
s("vano1919/tmr-artifacts", repo_type="dataset", local_dir="/workspace/dl",
  allow_patterns=["lora_plan_2026-10-26/dataset_xworld_v1/**", "lora_plan_2026-10-26/dataset_xworld_v2/**",
                  "lora_plan_2026-10-26/train_xworld_v2/code/**", "lora_plan_2026-10-26/train_xworld_v1/code/vault*",
                  "lora_plan_2026-10-26/caption_xworld_v1/captions_reviewed.jsonl"])
s("Qwen/Qwen-Image-2.1")
print("dl ok", flush=True)
PY
D=/workspace/dl/$P; C=$D/train_xworld_v2/code
python $C/xworld_v2_build.py $D/dataset_xworld_v1 $D/caption_xworld_v1/captions_reviewed.jsonl $D/dataset_xworld_v2 $C/scenes \
  /workspace/ds $C/xworld_v2.yaml /workspace/cfg.yaml || { echo "BUILD FAILED"; up; exit 1; }
cp /workspace/cfg.yaml /workspace/out/cfg.yaml
stage install
# training: a fresh ai-toolkit (the image's predates Qwen-Image 2.1); drawing: VideoX-Fun in its own venv, so its newer
# diffusers never touches the trainer's packages
git clone -q --depth 1 https://github.com/ostris/ai-toolkit /workspace/aitk && cd /workspace/aitk && git log -1 --format=%H \
  && python -c "import sys; sys.path.insert(0,'.'); from extensions_built_in.diffusion_models.qwen_image_2.qwen_image_2 import QwenImage2Model; print('arch ok')"
python -m venv --system-site-packages /workspace/vx
timeout 900 /workspace/vx/bin/pip install -q -U peft "git+https://github.com/huggingface/diffusers" || true
( cd /workspace && timeout 600 git clone -q --depth 1 https://github.com/aigc-apps/VideoX-Fun.git \
  && timeout 900 /workspace/vx/bin/pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy \
     func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations \
  && cd VideoX-Fun && /workspace/vx/bin/python -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) \
  || { echo "VIDEOX FAILED"; up; exit 1; }
up
test_round(){  # $1 = round label (step), $2 = the LoRA file
  stage "test_$1"
  O=/workspace/out/round_$1
  ( cd $C && timeout 3600 /workspace/vx/bin/python xworld_v2_scenes.py $C/scenes $O $2 1.0 round ); echo "SCENES EXIT $?"
  ( cd $C && python xworld_v2_sheet.py $C/scenes $O "step $1" round ); echo "ROUND $1 DONE $(date -u +%H:%M:%S)" >> /workspace/out/stages.txt
  up
}
# smoke run: 20 steps in a copy of the config, to see that the paired and the plain dataset mix before the real run is paid
stage smoke
sed -e "s/^        steps: .*/        steps: 20/" -e 's/name: "xworld_v2"/name: "xworld_v2_smoke"/' -e 's#/workspace/output#/workspace/smoke#' /workspace/cfg.yaml > /workspace/cfg_smoke.yaml
( cd /workspace/aitk && python run.py /workspace/cfg_smoke.yaml >> /workspace/smoke.log 2>&1 ); rc=$?; echo "SMOKE EXIT $rc"
cp /workspace/smoke.log /workspace/out/smoke.log; up
if [ $rc -ne 0 ]; then echo "SMOKE FAILED" > /workspace/out/beat.txt; up; exit 1; fi
rm -rf /workspace/smoke
for S in 750 1500 2250 3000; do
  stage "train_$S"
  sed -i "s/^        steps: .*/        steps: $S/" /workspace/cfg.yaml
  ( cd /workspace/aitk && python run.py /workspace/cfg.yaml >> /workspace/train.log 2>&1 ); echo "TRAIN EXIT $?"
  OUT=/workspace/output/xworld_v2
  CK=$OUT/xworld_v2_$(printf %09d $S).safetensors
  [ -f "$CK" ] || cp $OUT/xworld_v2.safetensors "$CK"
  python - "$CK" "$S" <<'PY' || { echo "RESUME CHECK FAILED"; up; exit 1; }
import json, sys
from safetensors import safe_open
meta = safe_open(sys.argv[1], "pt").metadata() or {}
info = json.loads(meta.get("training_info", "{}") or "{}")
step = info.get("step") or info.get("global_step")
print("checkpoint", sys.argv[1], "step", step, flush=True)
if step is not None and int(step) < int(sys.argv[2]) - 1:
    sys.exit(1)
PY
  up
  test_round $S "$CK"
done
kill $LOOP 2>/dev/null
stage done
up
# what the upload skips (optimizer state, latent cache) moves aside so the vault check sees exactly the uploaded set
mkdir -p /workspace/aside /workspace/ee/explainer_engine /workspace/ee/config
cp $D/train_xworld_v1/code/vault.py /workspace/ee/explainer_engine/vault.py; touch /workspace/ee/explainer_engine/__init__.py
cp $D/train_xworld_v1/code/vault.json /workspace/ee/config/vault.json
cd /workspace/output/xworld_v2 && find . \( -name "*.pt" -o -name "optimizer*" -o -path "*_latent_cache*" \) -type f -exec mv --backup=numbered {} /workspace/aside/ \;
find /workspace/output/xworld_v2 -type d -empty -delete
echo "DONE $(date -u +%H:%M:%S)" > /workspace/out/beat.txt; up
cd /workspace/ee && python -m explainer_engine.vault check-uploaded /workspace/output/xworld_v2 --to lora_plan_2026-10-26/train_xworld_v2/output --repo datasets/vano1919/tmr-artifacts
# returns: the start command (runpod.script_cmd) stops the pod at once
