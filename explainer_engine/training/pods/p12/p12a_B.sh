#!/bin/bash
# P12a smoke pod B: the guard stops a pod that cannot stop itself (run with --drill no_self_stop, guard ON).
# Plan: the paid-tests plan, section 2.3 (blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md); docs/CLOUD_RUNBOOK.md CR-17, CR-19, CR-20.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only writes under $EE_OUT: progress.txt (its content changes every minute: the stall rule) and t.jsonl (one JSON line per event).
# No model, no training, nothing is installed.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12a/B/beat.txt
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

# three minutes of progress, then a failure the wrapper turns into the end word FAILED rc=1
for k in 1 2 3; do
  progress "step $k/3"
  nap "$STEP_S"
done
progress "failing on purpose"
exit 1
