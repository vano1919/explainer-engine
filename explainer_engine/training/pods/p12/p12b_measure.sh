#!/bin/bash
# P12b measurement pod (RP-01, Fable's advice 2026-11-01, creator's YES on the card of 2026-10-31 06:50 UTC, cap $0.30 pod): measures
# the fixed setup of p12b.sh on the cloud P12b will use: the pip/git install (the same lines as p12b.sh), then the Qwen-Image-2.1
# download at the pinned revision, first 120 s with HF_XET_HIGH_PERFORMANCE=0, then the rest with =1 (same files, resumed), so the
# creator-asked speed-up of p12b.sh is measured, not assumed. No model load, no GPU work (a CUDA check only), no pictures, no video model.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. Output under
# $EE_OUT: progress.txt, t.jsonl (install_done, dl_a, dl_b, done), setup_measure.json. Weights go to /workspace/models, never under $EE_OUT.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12b_measure/beat.txt
# stall-minutes: 10
# needs: none
mkdir -p "$EE_OUT"
export HF_HOME=/workspace/dl/hf PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
ev() { printf '{"t":"%s","ev":"%s"%s}\n' "$(date -u +%FT%TZ)" "$1" "${2:+,$2}" >> "$EE_OUT/t.jsonl"; }
trap 'exit 143' TERM
T0=$(date +%s)
ev script_start "\"pod\":\"${RUNPOD_POD_ID:-}\",\"uptime_s\":$(cut -d. -f1 /proc/uptime),\"gpu\":\"$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)\""
printf '%s start\n' "$(date -u +%T)" > "$EE_OUT/progress.txt"
# progress writer from the first second: a slow install must not look like a stall (audit 2026-11-01, blocker 2)
( while sleep 60; do printf '%s alive %s s\n' "$(date -u +%T)" "$(( $(date +%s) - T0 ))" > "$EE_OUT/progress.txt"; done ) & PROG0=$!

# install: the same pinned lines as p12b.sh (tests/unit/test_p12b_measure.py keeps them equal)
pip install -q "huggingface_hub==1.33.0" "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" "git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e" || { ev install_failed "\"step\":\"pip\""; exit 1; }
git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead || { ev install_failed "\"step\":\"VideoX-Fun\""; exit 1; }
pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout "imageio[ffmpeg]" opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations || { ev install_failed "\"step\":\"deps\""; exit 1; }
( cd /workspace/VideoX-Fun && python3 -c "from videox_fun.pipeline import QwenImage21Pipeline; print('videox import ok')" ) || { ev install_failed "\"step\":\"import\""; exit 1; }
timeout 120 python3 -c "import torch; x=torch.ones(8,device='cuda'); print('cuda ok', torch.cuda.get_device_name(0), (x*2).sum().item())" || { ev cuda_failed; exit 1; }
T1=$(date +%s)
kill "$PROG0" 2>/dev/null
ev install_done "\"sec\":$((T1 - T0))"
if [ "${DRY:-0}" = "1" ]; then exit 0; fi

DL=/workspace/models/qwen
used() { du -sb "$DL" 2>/dev/null | cut -f1; }
dl() { python3 -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen-Image-2.1', revision='d26bb61231c349cf6b7896fa83353113880e1ba3', local_dir='$DL')"; }
( while sleep 60; do printf '%s dl %s bytes\n' "$(date -u +%T)" "$(used)" > "$EE_OUT/progress.txt"; done ) & PROG=$!

# phase A: 120 s without the xet setting
B0=$(used); B0=${B0:-0}; TA=$(date +%s)
HF_XET_HIGH_PERFORMANCE=0 timeout 120 bash -c "$(declare -f dl); DL=$DL; dl"
SA=$(( $(date +%s) - TA )); BA=$(( $(used) - B0 ))
ev dl_a "\"xet_high_performance\":0,\"sec\":$SA,\"bytes\":$BA,\"MBps\":$(( BA / (SA > 0 ? SA : 1) / 1000000 ))"
printf '%s phase A done %s bytes\n' "$(date -u +%T)" "$(used)" > "$EE_OUT/progress.txt"

# phase B: the rest with the setting p12b.sh uses, capped at 25 minutes
B1=$(used); B1=${B1:-0}; TB=$(date +%s)
HF_XET_HIGH_PERFORMANCE=1 timeout 1500 bash -c "$(declare -f dl); DL=$DL; dl"; RC=$?
SB=$(( $(date +%s) - TB )); BB=$(( $(used) - B1 )); BT=$(used)
ev dl_b "\"xet_high_performance\":1,\"sec\":$SB,\"bytes\":$BB,\"MBps\":$(( BB / (SB > 0 ? SB : 1) / 1000000 )),\"complete\":$([ "$RC" = 0 ] && echo true || echo false),\"total_bytes\":$BT"
kill "$PROG" 2>/dev/null
TE=$(date +%s)
printf '{"install_sec":%s,"dl_a_sec":%s,"dl_a_bytes":%s,"dl_b_sec":%s,"dl_b_bytes":%s,"complete":%s,"total_bytes":%s,"setup_sec_without_load":%s,"gpu":"%s","pod":"%s","date":"%s"}\n' \
  "$((T1 - T0))" "$SA" "$BA" "$SB" "$BB" "$([ "$RC" = 0 ] && echo true || echo false)" "$BT" "$((TE - T0))" \
  "$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)" "${RUNPOD_POD_ID:-}" "$(date -u +%F)" > "$EE_OUT/setup_measure.json"
ev done "\"setup_sec_without_load\":$((TE - T0))"
exit 0
