#!/bin/bash
# Route-test Qwen asset pod (2026-11-06): Qwen-Image-2.1 + xworld_v2 checkpoint 3000 at 0.7 draws ~50 route-test pictures (backdrops, hero sheets,
# one hero in four places, six scenes, fix edits) on ONE 48 GB card. Plan: the Fable thread's OR-23 plan (creator "კი" 2026-11-06 07:37 UTC),
# brief ltx_gap_review_2026-11-06/ASSET_POD_BRIEF.md; every setting is in route_assets.json (next to route_assets.py).
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop (every picture reaches HF within five minutes, OR-33), the money
# dead-man, the end word and the stop. This script installs, checks the job files, then runs route_assets.py, which writes under $EE_OUT.
# The wrapper downloads only this file: the three job files are fetched from HF code/route_assets/ and must match the sha256 below.
# heartbeat: datasets/vano1919/tmr-artifacts:route_test_2026-11/assets/beat.txt
# stall-minutes: 15
# needs: none
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 XW_GPU_MODE=model_cpu_offload
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"

# install: the pinned commits and versions of config/cloud_pins.json (the same as p12b.sh), plus open_clip_torch for the identity scores
pip install -q "huggingface_hub==1.33.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations || { ev install_failed "\"step\":\"deps\""; exit 1; }
pip install -q open_clip_torch || ev install_warn "\"step\":\"open_clip (identity scores will be skipped)\""
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item(), torch.cuda.get_device_properties(0).total_memory/2**30)" || { ev cuda_failed; exit 1; }
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

# the job files: the vault copy, checked against the sha256 pinned here (a changed file means a changed script text)
JOB=/workspace/job
mkdir -p "$JOB"
python3 -c "
from huggingface_hub import hf_hub_download
for f in ('route_assets.py', 'route_assets.json', 'xworld_v1_test.py'):
    hf_hub_download('vano1919/tmr-artifacts', 'code/route_assets/' + f, repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/route_assets/route_assets.py" "$JOB/dl/code/route_assets/route_assets.json" "$JOB/dl/code/route_assets/xworld_v1_test.py" "$JOB/"
printf '%s  %s\n' 7bbd3bb8ad4665413f90e0938db2f9c97d341e8e5656a0e0d5101417cb152321 "$JOB/route_assets.py" cb9cdd78709a8f41a9f84a93dd88104bc32b0b0084107881daa8145a910716bd "$JOB/route_assets.json" 6bca3fe7df907d0aaf448b61e1f3f72b9a190ea49b8630389d6499ddee84f469 "$JOB/xworld_v1_test.py" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check   # CR-18
cd "$JOB" && python3 route_assets.py
exit $?
