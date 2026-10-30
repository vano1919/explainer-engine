#!/bin/bash
# P12a smoke pod C: upload failures are counted, pushed and do not stop the pod (run with --drill upload_fail, guard ON).
# Plan: the paid-tests plan, section 2.4 (blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md); docs/CLOUD_RUNBOOK.md CR-17, CR-19, CR-20.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only writes under $EE_OUT: progress.txt (its content changes every minute: the stall rule) and t.jsonl (one JSON line per event).
# No model, no training, nothing is installed.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12a/C/beat.txt
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

# ten minutes: a new 1 KB file under $EE_OUT/parts/ every minute (the drill makes every folder upload fail; the beat-only upload works)
mkdir -p "$EE_OUT/parts"
for k in 1 2 3 4 5 6 7 8 9 10; do
  head -c 1024 /dev/urandom > "$EE_OUT/parts/part_$k.bin"
  progress "part $k/10"
  nap "$STEP_S"
done
exit 0
