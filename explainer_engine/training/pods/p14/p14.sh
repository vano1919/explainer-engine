#!/bin/bash
# The lean step-3 pod (guide step 3, D-116; plan STEP3_POD_PLAN_LEAN_ka.md, the creator 2026-11-06 13:21 UTC, stage G 13:25 UTC, the
# extras X1-X6 13:33 UTC): ONE pod runs, in order, A Blender layout passes (CPU), B Qwen line-drawing edits, C 150-word pictures,
# D BiRefNet cut-outs, E the five lean LTX jobs, then X1/X2/X5/X3/X6 on the card, G the J5 shots of the pilot window (CPU, beside E),
# X4 the fix edit and F speeds.json. Every stage is its own process and one failed stage never ends the pod (p14_pod.py).
# Fix 2026-11-06 14:44/14:49 UTC (pod ygg2ztmflr8pv2): the card never waits for the battle's line frame 0 (C, X6, D at once; B
# when the frames 0 exist, the duel alone if the battle's was cut at 600 s; E's jobs as their own inputs land); A.preflight
# puts Blender (A, G) on the card when NVIDIA's EGL draws its frame within 120 s, else on the CPU; the stage graph is
# p14_schedule.json.
# No upscale on the pod (p14.json upscale.enabled false). Caps, card loop and the OR-23 plan are the Fable thread's; create only after
# the OR-34 audit and the creator's word. Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop of $EE_OUT (every
# output lands on HF as it is written: OR-33), the money dead-man, the end word and the stop. $EE_OUT/layouts -> route_test_2026-11/
# layouts, $EE_OUT/step3 -> route_test_2026-11/step3 (the heartbeat below sets the wrapper's prefix). Weights stay under /workspace.
# The wrapper downloads only this file: the code bundle (python -m explainer_engine.training.pods.p14.lean bundle --ref <commit>) is
# fetched from HF code/p14/ee_src.tar.gz and must match the sha256 below (lean.py build writes that line).
# heartbeat: datasets/vano1919/tmr-artifacts:route_test_2026-11/beat.txt
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

# install: Blender's runtime libraries + Mesa's software EGL (the CPU lane renders without the card), ffmpeg, then pinned versions only
apt-get update -qq && apt-get install -y -qq --no-install-recommends libegl1 libegl-mesa0 libgl1 libgl1-mesa-dri libgbm1 libxi6 libxrender1 libxfixes3 libxkbcommon0 libsm6 libxext6 libx11-6 xz-utils ffmpeg || { ev install_failed "\"step\":\"apt\""; exit 1; }
pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
# Qwen-Image-2.1 (VideoX-Fun at the asset pod's commit, its dependency list as route_assets.sh)
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations kornia || { ev install_failed "\"step\":\"deps\""; exit 1; }
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"videox_import\""; exit 1; }
# LTX-2 at the P12 code pin (docs/pods/P12_LTX_FLAGS.md)
git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines || { ev install_failed "\"step\":\"ltx\""; exit 1; }
python3 -c "import ltx_pipelines.ic_lora, ltx_pipelines.distilled; print('ltx import ok')" || { ev install_failed "\"step\":\"ltx_import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item(), torch.cuda.get_device_properties(0).total_memory/2**30)" || { ev cuda_failed; exit 1; }

# the code bundle, checked against the sha256 pinned here (a changed bundle means a changed script text)
JOB=/workspace/job
mkdir -p "$JOB" /workspace/ee
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download('vano1919/tmr-artifacts', 'code/p14/ee_src.tar.gz', repo_type='dataset', local_dir='$JOB/dl')
" || { ev job_files_failed; exit 1; }
cp "$JOB/dl/code/p14/ee_src.tar.gz" "$JOB/ee_src.tar.gz"
printf '%s  %s\n' 251bf12ffc0e6cbf261422ec1ab0c384558c4c1f57b13cfcb93cabf3c1dd24d4 "$JOB/ee_src.tar.gz" > "$JOB/sha.txt"
sha256sum -c "$JOB/sha.txt" || { ev job_files_sha_mismatch; exit 3; }
ee_needs_check   # CR-18
tar -xzf "$JOB/ee_src.tar.gz" -C /workspace/ee || { ev bundle_unpack_failed; exit 1; }
cd /workspace/ee || exit 1
BIN=$(python3 -m explainer_engine.blender.project install --dest /workspace/blender | tail -n 1) || { ev install_failed "\"step\":\"blender\""; exit 1; }
timeout 300 python3 -m explainer_engine.blender.project resolve --binary "$BIN" --device cpu || { ev blender_resolve_failed; exit 1; }
kill "$PROG0" 2>/dev/null
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

python3 -m explainer_engine.training.pods.p14.p14_pod --binary "$BIN"
rc=$?
ev script_end "\"rc\":$rc"
exit $rc
