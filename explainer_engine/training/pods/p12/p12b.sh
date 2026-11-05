#!/bin/bash
# P12 combined pod: stage M (setup measurement) + the Qwen run (Q1 MVA hard pair, Q2 strength sweep, Q3 second pair; no host
# stage, D-89) in process 1 (p12b.py), then the LTX-2.5 22B stages (L1 plain I2V, L3, L2 Layout IC, AV audio-driven) in
# process 2 (p12c_ltx.py), started only when process 1 ended rc=0 and the creator's soft stop was not hit.
# Plan: blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md sections 3.1-3.5 and R3; every setting is in p12b.json.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only installs, then runs the two processes, which write under $EE_OUT: progress.txt, t.jsonl, stages.txt, measure.json, the
# pictures, the clips and their sidecars. Weights go to /workspace/models, never under $EE_OUT. Pins are those of cloud_pins.json.
# The wrapper downloads only this file: p12b.py, p12b.json and p12c_ltx.py are fetched from HF code/p12/ and must match the sha256.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12b/beat.txt
# stall-minutes: 25
# needs: none
# (why: the three job files are sha256-pinned below; the weights are fetched inside p12b.py and not listed here)
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
# huggingface_hub 1.33.0 (pinned below) downloads through hf_xet and ignores HF_HUB_ENABLE_HF_TRANSFER (it only warns), so the
# setting that works is HF_XET_HIGH_PERFORMANCE; both are set. Stage M (measure.json) records the download rate it gives.
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
# progress writer from the first second: a slow install must not look like a stall (audit 2026-11-01); p12b.py takes progress.txt over
T0=$(date +%s)
( while sleep 60; do printf '%s install alive %s s\n' "$(date -u +%T)" "$(( $(date +%s) - T0 ))" > "$EE_OUT/progress.txt"; done ) & PROG0=$!

# install: pinned commits and versions only
pip install -q "huggingface_hub==1.33.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations || { ev install_failed "\"step\":\"deps\""; exit 1; }
# LTX-2 at e98f6d9 (docs/pods/P12_LTX_FLAGS.md): the README's way is `uv sync --frozen` at the repo root (README.md:21), which
# builds a separate .venv that sys.executable in p12c_ltx.py would not see. ltx-pipelines depends on "ltx-core"
# (pyproject.toml:7), the sibling package packages/ltx-core (README.md:5, ../ltx-core/), so both go in one pip call and pip takes
# ltx-core from the checkout; the build backend is uv_build (pyproject.toml:19-20), fetched by pip for the PEP 517 build.
# UNVERIFIED: packages/ltx-core/pyproject.toml was not read (its build backend and whether it re-pins torch)
git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines || { ev install_failed "\"step\":\"ltx\""; exit 1; }
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"import\""; exit 1; }
python3 -c "import ltx_pipelines; print('ltx import ok')" || { ev install_failed "\"step\":\"ltx_import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item())" || { ev cuda_failed; exit 1; }
kill "$PROG0" 2>/dev/null
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

# the job files: from the vault copy, checked against the sha256 pinned here (a changed file means a changed script text)
JOB=/workspace/job
mkdir -p "$JOB"
python3 -c "
from huggingface_hub import hf_hub_download
for f in ('p12b.py', 'p12b.json', 'p12c_ltx.py'):
    hf_hub_download('vano1919/tmr-artifacts', 'code/p12/' + f, repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/p12/p12b.py" "$JOB/dl/code/p12/p12b.json" "$JOB/dl/code/p12/p12c_ltx.py" "$JOB/"
printf '%s  %s\n' PLACEHOLDER_SHA_P12B_PY "$JOB/p12b.py" PLACEHOLDER_SHA_P12B_JSON "$JOB/p12b.json" PLACEHOLDER_SHA_P12C_LTX_PY "$JOB/p12c_ltx.py" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check   # CR-18: the wrapper lists the `# needs:` files above; a missing one ends the pod FAILED rc=66 before p12b.py touches the GPU
python3 "$JOB/p12b.py"
rc=$?
[ $rc -ne 0 ] && exit $rc
[ -f "$EE_OUT/control/stopped_after.txt" ] && exit 0
python3 "$JOB/p12c_ltx.py"
exit $?
