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
mkdir -p /workspace/dl
# keep pip from replacing the image's torch (a multi-GB download and a possible CUDA mismatch, paid on the card): every install below is constrained to it
python3 -c "import torch; print('torch==' + torch.__version__)" > /workspace/dl/constraints.txt || exit 1
export PIP_CONSTRAINT=/workspace/dl/constraints.txt
pip install -q "huggingface_hub==1.33.0" "diffusers==0.43.0" "transformers==5.22.2" || exit 1
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee /workspace/batch
# the pins first: the files are fetched by a name that carries their own sha256 (never a name on main that a later upload can replace), and checked below
printf '%s  %s\n' f06b4fc06a9a543b1913919ba43e2e716081f472ec5d4be6c17672286f4319b8 "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
printf '%s  %s\n' e177fcd1407c9ea24a9b21733f2cf00a41db9fa3b3ff051550f24c2470ab090b "$JOB/batch.tar.gz" >> "$JOB/sha.txt"
python3 -c "
import shutil
from huggingface_hub import hf_hub_download
shas = {l.split()[1].rsplit('/', 1)[1]: l.split()[0] for l in open('$JOB/sha.txt')}
for stem, name in (('ee_src', 'ee_src.tar.gz'), ('batch', 'batch.tar.gz')):
    got = hf_hub_download('vano1919/tmr-artifacts', f'code/klein/{stem}-{shas[name]}.tar.gz', repo_type='dataset', local_dir='$JOB/dl')
    shutil.copyfile(got, '$JOB/' + name)
" || exit 1
sha256sum --strict -c "$JOB/sha.txt" || exit 3
ee_needs_check
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || exit 1
tar -xzf "$JOB/batch.tar.gz" -C /workspace/batch || exit 1
cd /workspace/ee || exit 1
if [ "${DRY:-0}" = "1" ]; then exit 0; fi
python3 -m explainer_engine.training.pods.klein.klein_jobs run /workspace/batch/batch.json
exit $?
