#!/bin/bash
# Route-test pod, LTX part (guide step 3, D-116): every job of ltx_jobs.json (ltx_job/1, edit/ltx_jobs.py) as one ic_lora call at
# Lightricks/LTX-2@e98f6d9 on its base (LTX-2.5 + Layout-To-Render, LTX-2.3 + Union-Control), then the free FFmpeg upscale.
# The matrix, the cap and the GPU are the OR-23 plan's (the Fable thread), confirmed by the plan thread, audited (OR-34) and
# worded by the creator before `runpod create`. This file only installs, fetches the three job files and runs p14_ltx.py.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop of $EE_OUT (every clip lands there as it finishes: OR-33),
# the money dead-man, the end word and the stop. Weights go to /workspace/models, never under $EE_OUT.
# The wrapper downloads only this file: p14_ltx.py, p14.json and ltx_jobs.json are fetched from HF code/p14/ and must match the
# sha256 below (regenerate with `python -m explainer_engine.edit.ltx_jobs <route shots> <out> --pod`, then this line).
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p14/beat.txt
# stall-minutes: 25
# needs: none
# (why: the three job files are sha256-pinned below; the weights are fetched inside p14_ltx.py and their sha256 checked there)
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
T0=$(date +%s)
( while sleep 60; do printf '%s install alive %s s\n' "$(date -u +%T)" "$(( $(date +%s) - T0 ))" > "$EE_OUT/progress.txt"; done ) & PROG0=$!

# install: pinned commits and versions only (the LTX-2 install of p12b.sh, docs/pods/P12_LTX_FLAGS.md)
pip install -q "huggingface_hub==1.33.0" || { ev install_failed "\"step\":\"pip\""; exit 1; }
git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines || { ev install_failed "\"step\":\"ltx\""; exit 1; }
python3 -c "import ltx_pipelines.ic_lora; print('ltx import ok')" || { ev install_failed "\"step\":\"ltx_import\""; exit 1; }
command -v ffmpeg >/dev/null || { apt-get -qq update && apt-get -qq install -y ffmpeg; } || { ev install_failed "\"step\":\"ffmpeg\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item())" || { ev cuda_failed; exit 1; }
kill "$PROG0" 2>/dev/null
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

JOB=/workspace/job
mkdir -p "$JOB"
python3 -c "
from huggingface_hub import hf_hub_download
for f in ('p14_ltx.py', 'p14.json', 'ltx_jobs.json'):
    hf_hub_download('vano1919/tmr-artifacts', 'code/p14/' + f, repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/p14/p14_ltx.py" "$JOB/dl/code/p14/p14.json" "$JOB/dl/code/p14/ltx_jobs.json" "$JOB/"
printf '%s  %s\n' be3f932d91ed30ffcac8adc128b3ac4692ef4b38904f4125151d16ba7c015456 "$JOB/p14_ltx.py" 78883becd0d45cc617f75c7dbccb8e965eb9b6afb2a5005f38d7887cf75d062f "$JOB/p14.json" cf74ecd8c79269f1c4e4adc14916e1ebd880023522a20050c06fb231dab55c44 "$JOB/ltx_jobs.json" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check
python3 "$JOB/p14_ltx.py"
exit $?
