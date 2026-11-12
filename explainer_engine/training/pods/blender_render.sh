#!/bin/bash
# The Blender render pod (OR-21, D-96; roadmap section 11 and 10.4). Started only by:
#   python -m explainer_engine.cloud.runpod create --script explainer_engine/training/pods/blender_render.sh --script-url <its HF copy>
#     --heartbeat datasets/vano1919/tmr-artifacts:runs/blender_render/beat.txt --image <the image of the agreed OR-23 plan> --ledger <run.json>
#   with the pod env EE_BLENDER_JOB (vault path of the blender_pod_job/1) and EE_JOB_ID (its job_id).
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only installs (the Blender archive pinned by sha256 in config/cloud_pins.json, BP-175; two pip pins), fetches the code bundle
# pinned below, renders the job's shots frame by frame (RENDERED -> DURABLY_STORED -> COMMITTED on the vault, roadmap 10.4) and
# ends with the vault check of the whole render folder (VT-01). Any failed render, upload or check exits non-zero, so the wrapper
# never writes DONE before every paid frame is proven on the vault (VT-02). Frames go to /workspace/render, never under $EE_OUT;
# $EE_OUT gets progress.txt, the render manifests and units.json for `runpod cost`.
# The pod image is NOT chosen here (cloud_pins.json blender.image is null): the OR-23 plan of ICW-09 names it item by item.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/blender_render/beat.txt
# stall-minutes: 20
# needs: /workspace/job/ee_src.tar.gz 10000
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\",\"job\":\"${EE_JOB_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
[ -n "${EE_BLENDER_JOB:-}" ] && [ -n "${EE_JOB_ID:-}" ] || { ev job_env_missing; exit 6; }

# install: Blender's runtime libraries (headless: EGL, no X server), two pinned pip packages, then the pinned archive
apt-get update -qq && apt-get install -y -qq --no-install-recommends libegl1 libgl1 libxi6 libxrender1 libxfixes3 libxkbcommon0 libsm6 libxext6 libx11-6 xz-utils ffmpeg || { ev install_failed "\"step\":\"apt\""; exit 1; }
pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" || { ev install_failed "\"step\":\"pip\""; exit 1; }

# the code bundle (python -m explainer_engine.training.pods.blender_render bundle), checked against the sha256 pinned here
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download('vano1919/tmr-artifacts', 'code/blender_render/ee_src.tar.gz', repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/blender_render/ee_src.tar.gz" "$JOB/ee_src.tar.gz"
printf '%s  %s\n' PLACEHOLDER_SHA_EE_SRC_TAR_GZ "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check   # CR-18: the `# needs:` file above; a missing one ends the pod FAILED rc=66 before Blender is installed
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || { ev bundle_unpack_failed; exit 1; }
cd /workspace/ee || exit 1
BIN=$(python3 -m explainer_engine.blender.project install --dest /workspace/blender | tail -n 1) || { ev install_failed "\"step\":\"blender\""; exit 1; }
timeout 300 python3 -m explainer_engine.blender.project resolve --binary "$BIN" --device gpu || { ev blender_resolve_failed; exit 1; }
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

# the render: frames are committed to the vault while Blender works; a resumed pod renders only what the vault lacks
python3 -m explainer_engine.training.pods.blender_render render --job "$EE_BLENDER_JOB" --binary "$BIN" --out "$EE_OUT" --render /workspace/render
rc=$?
[ $rc -ne 0 ] && { ev render_failed "\"rc\":$rc"; exit $rc; }
python3 -m explainer_engine.vault check-uploaded "/workspace/render/$EE_JOB_ID" --to "blender/$EE_JOB_ID" || { ev vault_check_failed; exit 5; }
ev script_end
exit 0
