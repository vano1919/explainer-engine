#!/bin/bash
# P12b pod: the Qwen run (Q1 MVA hard pair, Q4 host collage, Q2 strength sweep, Q3 second pair) of the paid-tests plan, section 3.3.
# Plan: blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md sections 3.1, 3.3, 3.3a, 3.5; every setting is in p12b.json (next to p12b.py).
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only installs, then runs p12b.py, which writes under $EE_OUT: progress.txt, t.jsonl, stages.txt, the pictures and their sidecars.
# Weights go to /workspace/models, never under $EE_OUT. Pins (commits, versions) are those of config/cloud_pins.json.
# The wrapper downloads only this file: p12b.py and p12b.json are fetched from HF code/p12/ and must match the sha256 below.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12b/beat.txt
# stall-minutes: 15
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"

# install: pinned commits and versions only
pip install -q "huggingface_hub==1.33.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations || { ev install_failed "\"step\":\"deps\""; exit 1; }
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item())" || { ev cuda_failed; exit 1; }
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

# the job files: from the vault copy, checked against the sha256 pinned here (a changed file means a changed script text)
JOB=/workspace/job
mkdir -p "$JOB"
python3 -c "
from huggingface_hub import hf_hub_download
for f in ('p12b.py', 'p12b.json'):
    hf_hub_download('vano1919/tmr-artifacts', 'code/p12/' + f, repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/p12/p12b.py" "$JOB/dl/code/p12/p12b.json" "$JOB/"
printf '%s  %s\n' f7727e1987a5306cf9d13e28e03f12c2cf31ed2056bdcf81022faca12fbe449e "$JOB/p12b.py" 43e03437524c981623a116b44310896b0e14f6bf040b6ea79a878609782814e2 "$JOB/p12b.json" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
python3 "$JOB/p12b.py"
exit $?
