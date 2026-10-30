#!/bin/bash
# P12a smoke pod E: only the watchdog is left (run with --drill drop_key --no-guard: no in-pod key, no guard).
# Plan: the paid-tests plan, section 2.6 (blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md); docs/CLOUD_RUNBOOK.md CR-17, CR-19, CR-20.
# Runs inside pod_wrapper.sh: the wrapper owns beat.txt, the upload loop, the money dead-man, the end word and the stop. This script
# only writes under $EE_OUT: progress.txt (its content changes every minute: the stall rule) and t.jsonl (one JSON line per event).
# No model, no training, nothing is installed.
# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12a/E/beat.txt
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

# two minutes of progress, then a clean exit; the pod cannot stop itself, so the GitHub watchdog has to
for k in 1 2; do
  progress "step $k/2"
  nap "$STEP_S"
done
exit 0
