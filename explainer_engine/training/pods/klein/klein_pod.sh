#!/bin/bash
# The RunPod pod script of the Klein pictures (W5, plan RUNPOD_AB_PLAN.md section 5; the creator's word
# cmsg_01Hnu5zB86sjUj5GtTgaUkPWU9kS1kT1CnB6HveYkz5rfQ; NO spend approved by it). Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the
# upload of $EE_OUT, the money dead-man, the end word and the stop. `klein_jobs run` does L2 (the model files downloaded and sha256-checked
# FIRST, the pod ends on any fail before a load), L3 (one smoke picture on this card) and L4 (the pictures, each uploaded and verified
# on HF before the next). Weights go to /workspace/dl, never $EE_OUT.
# heartbeat: datasets/vano1919/tmr-artifacts:klein_out/beat.txt
# stall-minutes: 20
# needs: /workspace/job/ee_src.tar.gz 1000000
# needs: /workspace/job/batch.tar.gz 100
# (why: the code bundle and the batch (prompts, settings, refs) are two separate sha256-pinned files, below; diffusers 0.43.0 is the pinned release)
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 EE_KLEIN_VOL_ROOT=/workspace/dl
trap 'exit 143' TERM
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
pip install -q "huggingface_hub==1.33.0" "diffusers==0.43.0" "transformers==5.22.2" || exit 1
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee /workspace/batch
python3 -c "
from huggingface_hub import hf_hub_download
for f in ('code/klein/ee_src.tar.gz', 'code/klein/batch.tar.gz'):
    hf_hub_download('vano1919/tmr-artifacts', f, repo_type='dataset', local_dir='$JOB/dl')
" || exit 1
cp "$JOB/dl/code/klein/ee_src.tar.gz" "$JOB/ee_src.tar.gz"
cp "$JOB/dl/code/klein/batch.tar.gz" "$JOB/batch.tar.gz"
printf '%s  %s\n' @@EE_SRC_SHA256@@ "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
printf '%s  %s\n' @@BATCH_SHA256@@ "$JOB/batch.tar.gz" >> "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || exit 3
ee_needs_check
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || exit 1
tar -xzf "$JOB/batch.tar.gz" -C /workspace/batch || exit 1
cd /workspace/ee || exit 1
if [ "${DRY:-0}" = "1" ]; then exit 0; fi
python3 -m explainer_engine.training.pods.klein.klein_jobs run /workspace/batch/batch.json
exit $?
