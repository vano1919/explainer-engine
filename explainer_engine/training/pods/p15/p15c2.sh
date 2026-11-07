#!/bin/bash
# VARIANT (the creator 2026-11-06 21:41 UTC, scope card): the 24 Qwen look-variant pictures AND 2 LTX-2.5 clips on one pod. Runner: p15_pod --only qwen --clips 2
# (stage graph p15qc2_schedule.json, RP-11). Clip first frames are first_frames/<shot>__<style tag>.png. Everything below is p15.sh.
# The pilot pod (PILOT_1MIN_PLAN.md v3; the creator 2026-11-06 15:25 UTC scope, 16:05 UTC "run it"; Fable 15:52 UTC: Qwen on the pod,
# 185 frames, the room clip is the two-shot): Qwen-Image-2.1 + xworld_v2 ck3000 w0.7 restyles the 7 room stills and the battle colour
# frame 0 (rendered free with Blender, on HF route_test_2026-11/pilot/blender/, pinned by sha256 in p15.json), then LTX-2.5 distilled
# i2v animates ONE 185-frame clip per scene (the room two-shot, the battle frame 0). No Blender on the pod. The stage graph is
# p15_schedule.json (RP-11). Caps and the OR-23 plan are the Fable thread's; create only after the OR-34 audit and the creator's word.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop of $EE_OUT (every output lands on HF as it is written: OR-33),
# the money dead-man, the end word and the stop. $EE_OUT -> route_test_2026-11/pilot (the heartbeat below sets the wrapper's prefix).
# The wrapper downloads only this file: the code bundle (python -m explainer_engine.training.pods.p15.build bundle --ref <commit>) is
# fetched from HF code/p15/ee_src.tar.gz and must match the sha256 below (build.py bundle writes that line).
# heartbeat: datasets/vano1919/tmr-artifacts:route_test_2026-11/pilot/beat.txt
# stall-minutes: 30
# needs: /workspace/job/ee_src.tar.gz 1000000
# (why: the bundle is sha256-pinned below; the weights are fetched inside the stages and their sha256 checked there)
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
ev script_start "\"deadline\":\"${EE_DEADLINE:-}\",\"pod\":\"${RUNPOD_POD_ID:-}\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
T0=$(date +%s)
( while sleep 60; do printf '%s install alive %s s\n' "$(date -u +%T)" "$(( $(date +%s) - T0 ))" > "$EE_OUT/progress.txt"; done ) & PROG0=$!

# install: ffmpeg, then pinned versions only (the step-3 pod's stack, p14.sh, without Blender)
apt-get update -qq && apt-get install -y -qq --no-install-recommends ffmpeg || { ev install_failed "\"step\":\"apt\""; exit 1; }
pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
# Qwen-Image-2.1 (VideoX-Fun at the asset pod's commit, its dependency list as route_assets.sh)
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations kornia || { ev install_failed "\"step\":\"deps\""; exit 1; }
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"videox_import\""; exit 1; }
# LTX-2 at the P12 code pin (docs/pods/P12_LTX_FLAGS.md)
git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines || { ev install_failed "\"step\":\"ltx\""; exit 1; }
python3 -c "import ltx_pipelines.distilled; print('ltx import ok')" || { ev install_failed "\"step\":\"ltx_import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item(), torch.cuda.get_device_properties(0).total_memory/2**30)" || { ev cuda_failed; exit 1; }

# the code bundle, checked against the sha256 pinned here (a changed bundle means a changed script text)
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download('vano1919/tmr-artifacts', 'code/p15/ee_src.tar.gz', repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/p15/ee_src.tar.gz" "$JOB/ee_src.tar.gz"
printf '%s  %s\n' 359f8f535882d061be2bfc4f5c8402d457c4d0ef17f72eca9a13b91b17c3a1d0 "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check   # CR-18
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || { ev bundle_unpack_failed; exit 1; }
cd /workspace/ee || exit 1
kill "$PROG0" 2>/dev/null
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

python3 -m explainer_engine.training.pods.p15.p15_pod --only qwen --clips 2
rc=$?
ev script_end "\"rc\":$rc"
exit $rc
