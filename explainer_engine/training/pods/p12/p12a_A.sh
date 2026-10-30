#!/bin/bash
# P12a smoke pod A: the plain path with no guard: wrapper accepted, key probe, real uploader, the in-pod stop, boot and download speed.
# Plan: the paid-tests plan, section 2.2 (blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md); docs/CLOUD_RUNBOOK.md CR-17, CR-19, CR-20.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only writes under $EE_OUT: progress.txt (its content changes every minute: the stall rule) and t.jsonl (one JSON line per event).
# No model, no training, nothing is installed.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12a/A/beat.txt
# stall-minutes: 4
mkdir -p "$EE_OUT"
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
nap() { sleep "$1" & wait $!; }
STEP_S=${P12_STEP_S:-60}   # a minute per step; only the offline test shortens it
progress() { printf '%s %s\n' "$(date -u +%T)" "$1" > "$EE_OUT/progress.txt"; }
trap 'exit 143' TERM
trap 'rc=$?; ev exit "\"rc\":$rc"' EXIT
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"drill\":\"${EE_DRILL:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
progress start

# a progress line every minute for the whole script, so the stall rule never sees a long download as a hang
( while true; do progress alive; nap "$STEP_S"; done ) &
PROG=$!
trap 'rc=$?; kill $PROG 2>/dev/null; ev exit "\"rc\":$rc"' EXIT

# A-1 boot facts: card, driver, CUDA, disk, RAM, python and library versions; only names of non-secret variables (the env holds keys)
F="$EE_OUT/boot_facts.txt"
{
  echo "== gpu"; timeout 60 nvidia-smi -L
  timeout 60 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  echo "== disk"; df -h /
  echo "== ram"; grep -E 'MemTotal|MemAvailable' /proc/meminfo
  echo "== python"; python3 --version
  echo "== pod"; for v in RUNPOD_POD_ID RUNPOD_DC_ID RUNPOD_GPU_COUNT RUNPOD_CPU_COUNT CUDA_VERSION EE_JOB EE_PRICE EE_LIFETIME_S EE_MAX_USD; do echo "$v=${!v}"; done
} >> "$F" 2>&1
timeout 120 python3 -c "import huggingface_hub, torch; print('huggingface_hub', huggingface_hub.__version__, 'torch', torch.__version__, 'cuda', torch.version.cuda)" >> "$F" 2>&1
ev boot_facts "\"file\":\"boot_facts.txt\""

# A-2 download one weight shard OUTSIDE $EE_OUT (the wrapper uploads $EE_OUT whole; base weights never go to the vault) and time it.
# Shard 00002 of Qwen/Qwen-Image-2.1 at the pinned revision (4,261,951,904 bytes; shard 00001 is 9.97 GB: too big for pod A's cap) is
# found by its name prefix and checked by its size before it is fetched; the file name is written to $DL/.shard for the timing below.
export DL=${P12_DL:-/workspace/dl} HF_HOME=${P12_DL:-/workspace/dl}/hf   # P12_DL: only the offline test moves it
mkdir -p "$DL"
ev dl_start "\"prefix\":\"transformer/diffusion_pytorch_model-00002-of-00002\",\"expected_bytes\":4261951904"
t0=$(date +%s)
timeout 480 python3 - <<'PY'
import os
from huggingface_hub import HfApi, hf_hub_download
REV = "d26bb61231c349cf6b7896fa83353113880e1ba3"
info = HfApi().model_info("Qwen/Qwen-Image-2.1", revision=REV, files_metadata=True)
hits = [s for s in info.siblings if s.rfilename.startswith("transformer/diffusion_pytorch_model-00002-of-00002")]
assert len(hits) == 1 and hits[0].size == 4261951904, [(s.rfilename, s.size) for s in hits]
open(os.path.join(os.environ["DL"], ".shard"), "w").write(hits[0].rfilename)
hf_hub_download("Qwen/Qwen-Image-2.1", hits[0].rfilename, revision=REV, local_dir=os.environ["DL"])
PY
rc_dl=$?
secs=$(( $(date +%s) - t0 ))
bytes=$(stat -c %s "$DL/$(cat "$DL/.shard" 2>/dev/null)" 2>/dev/null || echo 0)
mbs=$(awk -v b="$bytes" -v s="$secs" 'BEGIN { printf "%.1f", (s > 0 ? b / 1e6 / s : 0) }')
ev dl_end "\"rc\":$rc_dl,\"bytes\":$bytes,\"seconds\":$secs,\"mb_per_s\":$mbs"
rm -rf "$DL"

# A-3 the layer sizes of the aitoolkit image (manifest only, no pull), for P12b's boot estimate; skipped when skopeo is absent
if command -v skopeo > /dev/null 2>&1; then
  timeout 120 skopeo inspect --raw "docker://ostris/aitoolkit@sha256:fadfc236117b7b4820c5d946272a5a60738dbb044ab272b4635d9ea4400c2c1d" \
    > "$EE_OUT/aitoolkit_manifest.json" 2> "$EE_OUT/skopeo.err"
  ev skopeo "\"rc\":$?"
else
  ev skopeo "\"skipped\":\"no skopeo in the image\""
fi
progress done
exit 0
