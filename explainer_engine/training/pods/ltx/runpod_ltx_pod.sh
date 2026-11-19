#!/bin/bash
# The RunPod pod script of the LTX A/B (W5, plan RUNPOD_AB_PLAN.md, D-132; the platform chosen by the creator, decision
# cmsg_01Hnu5zB86sjUj5GtTgaUkPWYBU8BqKt8DFFsw46f9xMHj; NO spend approved by that choice). Runs inside pod_wrapper.sh: the wrapper owns
# beat.txt, the upload of $EE_OUT, the money dead-man, the end word and the stop. This script only works: install the pinned LTX-2
# code, then `runpod_ltx_jobs run` does L2 (every file downloaded and sha256-checked FIRST, the pod ends at once on any fail), L3
# (one smoke clip on this card) and L4 (the batch, each clip verified on HF before the next). Weights go to /workspace/dl, never $EE_OUT.
# heartbeat: datasets/vano1919/tmr-artifacts:ltx_route/runpod_beat/beat.txt
# stall-minutes: 30
# needs: /workspace/job/ee_src.tar.gz 1000000
# needs: /workspace/job/batch.tar.gz 100
# (why: the code bundle and the batch (prompts, job specs, pictures) are two separate sha256-pinned files, below)
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 EE_LTX_VOL_ROOT=/workspace/dl
trap 'exit 143' TERM
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
mkdir -p /workspace/dl
# keep pip from replacing the image's torch (a multi-GB download and a possible CUDA mismatch, paid on the card): every install below is constrained to it
python3 -c "import torch; print('torch==' + torch.__version__)" > /workspace/dl/constraints.txt || exit 1
export PIP_CONSTRAINT=/workspace/dl/constraints.txt
pip install -q "huggingface_hub==1.33.0" || exit 1
git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines || exit 1
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee /workspace/batch
# the pins first: the files are fetched by a name that carries their own sha256 (never a name on main that a later upload can replace), and checked below
printf '%s  %s\n' 4215a94af7d04c2a6a3ca1d7f1081d4b0f09af64529672833dc5020dc8ca40bb "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
printf '%s  %s\n' @@BATCH_SHA256@@ "$JOB/batch.tar.gz" >> "$JOB/sha.txt"
python3 -c "
import shutil
from huggingface_hub import hf_hub_download
shas = {l.split()[1].rsplit('/', 1)[1]: l.split()[0] for l in open('$JOB/sha.txt')}
for stem, name in (('ee_src', 'ee_src.tar.gz'), ('batch', 'batch.tar.gz')):
    got = hf_hub_download('vano1919/tmr-artifacts', f'code/ltx_ab/{stem}-{shas[name]}.tar.gz', repo_type='dataset', local_dir='$JOB/dl')
    shutil.copyfile(got, '$JOB/' + name)
" || exit 1
sha256sum --strict -c "$JOB/sha.txt" || exit 3
ee_needs_check
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || exit 1
tar -xzf "$JOB/batch.tar.gz" -C /workspace/batch || exit 1
cd /workspace/ee || exit 1
if [ "${DRY:-0}" = "1" ]; then exit 0; fi
python3 -m explainer_engine.training.pods.ltx.runpod_ltx_jobs run /workspace/batch/batch.json
exit $?
