#!/bin/bash
# The pod protocol of every script pod (docs/CLOUD_RUNBOOK.md CR-01..CR-06, CR-15). `runpod.script_cmd` embeds this file as the
# pod's start command; the script of the job is downloaded from EE_SCRIPT_URL and run inside it. The wrapper owns beat.txt,
# the upload loop, the money dead-man, the end word, the final upload + verify and the stop. The script only works and
# writes its results under $EE_OUT (and one line of progress to $EE_OUT/progress.txt).
#
# Inputs (pod env, set by runpod.create_body): EE_SCRIPT_URL, HF_TOKEN, EE_CREATED, EE_LIFETIME_S, EE_MAX_USD, EE_PRICE,
# EE_DISK_H, EE_JOB, EE_HF_REPO, EE_HF_PREFIX, optional EE_OUT, EE_PASS_S, EE_UPLOAD_GRACE_S, EE_CAP_GRACE_S, EE_RETRY_S,
# EE_KILL_WAIT_S, EE_STOP_RETRY_S, EE_MAX_STOPS, EE_POLL_S, EE_UPLOAD_CMD (a command; default: the huggingface_hub uploader).
# EE_HF_PIN (the huggingface_hub version of config/cloud_pins.json, installed when the image lacks it), EE_FORCE_HF_CHECK (tests).
# EE_DRILL (no_self_stop | drop_key | upload_fail) exists for the P12a smoke only: `runpod create --drill` refuses it unless the
# ledger says test=p12a_smoke, so a production pod can never carry one. EE_DEADLINE is exported to the job script (its own cut-off).
EE_OUT=${EE_OUT:-/workspace/out}
EE_PASS_S=${EE_PASS_S:-300}
EE_UPLOAD_GRACE_S=${EE_UPLOAD_GRACE_S:-900}
EE_CAP_GRACE_S=${EE_CAP_GRACE_S:-300}
EE_RETRY_S=${EE_RETRY_S:-30}
EE_KILL_WAIT_S=${EE_KILL_WAIT_S:-30}
EE_STOP_RETRY_S=${EE_STOP_RETRY_S:-60}
EE_MAX_STOPS=${EE_MAX_STOPS:-1000000}
EE_POLL_S=${EE_POLL_S:-1}
EE_SCRIPT=${EE_SCRIPT:-/workspace/pod.sh}
ST=${EE_STATE:-/workspace/.ee}
BEAT="$EE_OUT/beat.txt"
mkdir -p "$EE_OUT" "$ST" "$(dirname "$EE_SCRIPT")"
echo 0 > "$ST/fail"
: > "$ST/boot"

self_stop() {
  [ -n "$RUNPOD_API_KEY" ] || { echo "self_stop: no key could stop this pod"; return 1; }
  curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \
    -d '{"action":"stop"}' "https://api.runpod.io/v2/pods/$RUNPOD_POD_ID/action" >/dev/null 2>&1 \
  || curl -fsS -m 30 -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \
    -d "{\"query\":\"mutation { podStop(input: {podId: \\\"$RUNPOD_POD_ID\\\"}) { id desiredStatus } }\"}" \
    https://api.runpod.io/graphql >/dev/null 2>&1 \
  || echo "self_stop: no key could stop this pod"
}

# --- beat.txt: line 1 = BOOT (once), line 2 = the current word (CR-02) -------------------------------------------------
write_beat() { # $1 word  $2 rc (optional)
  local prog unst fail word="$1"
  prog=$(head -c 60 "$EE_OUT/progress.txt" 2>/dev/null | tr '\n\r' '  ')
  fail=$(cat "$ST/fail" 2>/dev/null || echo 0)
  if [ -f "$ST/verified" ]; then
    unst=$(find "$EE_OUT" -type f ! -name beat.txt -newer "$ST/verified" 2>/dev/null | wc -l)
  else
    unst=$(find "$EE_OUT" -type f ! -name beat.txt 2>/dev/null | wc -l)
  fi
  [ -n "$2" ] && word="$word rc=$2"
  { cat "$ST/boot"; printf '%s %s progress=%s upload_fail=%s unstored=%s\n' "$word" "$(date -u +%FT%TZ)" "$prog" "$fail" "$(echo $unst)"; } > "$BEAT.tmp" \
    && mv "$BEAT.tmp" "$BEAT"
}

# --- upload + verify (CR-04): exit 0 only when every local file is on HF with the same size ---------------------------------
ee_upload() {
  [ "$EE_DRILL" = upload_fail ] && return 1   # drill: the folder upload always fails, the beat upload still works (CR-10 becomes visible)
  if [ -n "$EE_UPLOAD_CMD" ]; then $EE_UPLOAD_CMD; return $?; fi
  python3 - <<'PY'
import os, sys
from huggingface_hub import HfApi
out, repo, prefix = os.environ.get("EE_OUT", "/workspace/out"), os.environ["EE_HF_REPO"], os.environ.get("EE_HF_PREFIX", "").strip("/")
api = HfApi()
try:
    api.upload_folder(folder_path=out, path_in_repo=prefix or None, repo_id=repo, repo_type="dataset")
    remote = {r.path: r.size for r in api.list_repo_tree(repo, path_in_repo=prefix or None, repo_type="dataset", recursive=True) if hasattr(r, "size")}
except Exception as e:  # noqa: BLE001
    print("UPLOAD FAILED", e); sys.exit(1)
# a loop pass checks only files that were settled when the pass began (EE_SETTLED_REF = a file touched at that moment): a log the
# script is still writing differs between upload and listing on a healthy pod. The end sequence checks every file.
ref = os.environ.get("EE_SETTLED_REF")
ref_t = os.path.getmtime(ref) if ref else None
bad = 0
for root, _, files in os.walk(out):
    for f in files:
        p = os.path.join(root, f)
        if f == "beat.txt" or (ref_t is not None and os.path.getmtime(p) > ref_t):  # beat.txt is rewritten by the loop itself
            continue
        key = (prefix + "/" if prefix else "") + os.path.relpath(p, out).replace(os.sep, "/")
        if remote.get(key) != os.path.getsize(p):
            bad += 1
print("unverified", bad)
sys.exit(1 if bad else 0)
PY
}

ee_upload_beat() { # the beat alone: the guard and the watchdog read it even when the folder upload keeps failing
  if [ -n "$EE_UPLOAD_BEAT_CMD" ]; then $EE_UPLOAD_BEAT_CMD; return $?; fi
  [ -n "$EE_UPLOAD_CMD" ] && return 0
  python3 - <<'PY'
import os, sys
from huggingface_hub import HfApi
out, repo, prefix = os.environ.get("EE_OUT", "/workspace/out"), os.environ["EE_HF_REPO"], os.environ.get("EE_HF_PREFIX", "").strip("/")
try:
    HfApi().upload_file(path_or_fileobj=os.path.join(out, "beat.txt"), path_in_repo=(prefix + "/" if prefix else "") + "beat.txt",
                        repo_id=repo, repo_type="dataset")
except Exception as e:  # noqa: BLE001
    print("BEAT UPLOAD FAILED", e); sys.exit(1)
PY
}

ee_pass() { # one pass of the loop
  write_beat ALIVE
  touch "$ST/passref"
  if EE_SETTLED_REF="$ST/passref" ee_upload; then
    echo 0 > "$ST/fail"; touch -r "$ST/passref" "$ST/verified"; write_beat ALIVE
  else
    echo $(( $(cat "$ST/fail") + 1 )) > "$ST/fail"; write_beat ALIVE
    ee_upload_beat
  fi
}

# --- deadline: created + min(lifetime, max_usd / (price + disk per hour)) - cap grace (CR-05) -----------------------------
deadline_calc() { # price -> epoch
  awk -v c="${EE_CREATED:-0}" -v l="${EE_LIFETIME_S:-0}" -v m="${EE_MAX_USD:-0}" -v p="$1" -v d="${EE_DISK_H:-0}" -v g="$EE_CAP_GRACE_S" \
    'BEGIN { s = l; if (m > 0 && p + d > 0) { t = m / (p + d) * 3600; if (l <= 0 || t < l) s = t }; printf "%d", c + s - g }'
}

# --- 1. key boot-probe (CR-03) --------------------------------------------------------------------------------------------
code=none
real=""
[ "$EE_DRILL" = drop_key ] && unset RUNPOD_API_KEY   # drill: the pod has no key (key=none; only the guard and the watchdog can stop it)
if [ -n "$RUNPOD_API_KEY" ] && [ -n "$RUNPOD_POD_ID" ]; then
  code=$(curl -s -m 20 -o "$ST/pod.json" -w '%{http_code}' -H "Authorization: Bearer $RUNPOD_API_KEY" \
         "https://api.runpod.io/v2/pods/$RUNPOD_POD_ID" 2>/dev/null) || code=000
  [ "$code" = 200 ] && real=$(grep -o '"cost": *[0-9.]*' "$ST/pod.json" 2>/dev/null | head -1 | grep -o '[0-9.]*$')
fi
# --- 1b. the uploader (CR-18): the very first beat upload needs huggingface_hub, and an image may not carry it ---------------------
if { [ -z "$EE_UPLOAD_CMD" ] || [ -n "$EE_FORCE_HF_CHECK" ]; } && ! python3 -c "import huggingface_hub" >/dev/null 2>&1 && [ -n "$EE_HF_PIN" ]; then
  timeout 180 pip install -q "huggingface_hub==$EE_HF_PIN" >/dev/null 2>&1 \
    || timeout 180 pip install -q --break-system-packages "huggingface_hub==$EE_HF_PIN" >/dev/null 2>&1
fi
PRICE=$(awk -v a="${EE_PRICE:-0}" -v b="${real:-0}" 'BEGIN { print (b + 0 > a + 0) ? b : a }')
DEADLINE=$(deadline_calc "$PRICE")
echo "BOOT key=$code job=${EE_JOB:-none} pod=${RUNPOD_POD_ID:-none} price=$PRICE deadline=$DEADLINE" > "$ST/boot"
write_beat ALIVE
ee_upload_beat >/dev/null 2>&1 &  # the guard's boot deadline is lifted by the first upload: do not wait for the first loop pass

# --- 2. the upload loop starts before anything heavy -------------------------------------------------------------------------
( while true; do sleep "$EE_PASS_S"; ee_pass; done ) &
LOOP=$!

end_seq() { # $1 word  $2 rc  $3 grace seconds
  local word="$1" rc="$2" grace="$3" ok=0 limit n=0 final
  pkill -P "$LOOP" 2>/dev/null; kill "$LOOP" 2>/dev/null; wait "$LOOP" 2>/dev/null  # the loop and its sleep
  limit=$(( $(date +%s) + grace ))
  while true; do
    if ee_upload; then ok=1; echo 0 > "$ST/fail"; touch "$ST/verified"; break; fi
    echo $(( $(cat "$ST/fail") + 1 )) > "$ST/fail"
    [ "$(date +%s)" -ge "$limit" ] && break
    sleep "$EE_RETRY_S"
  done
  final="$word"; [ "$ok" = 1 ] || final=FAILED_UPLOAD
  write_beat "$final" "$rc"
  for _ in 1 2 3; do ee_upload_beat && break; sleep 2; done
  # PID 1 stays alive: a returning start command would restart the container in a loop
  while [ "$n" -lt "$EE_MAX_STOPS" ]; do
    [ "$EE_DRILL" = no_self_stop ] || self_stop   # drill: the guard or the watchdog must stop this pod
    n=$((n + 1)); sleep "$EE_STOP_RETRY_S"
  done
  exit "$rc"
}

# --- 2b. no uploader at all: nothing could ever reach HF, so end the pod now instead of billing blind (CR-18) --------------------
if { [ -z "$EE_UPLOAD_CMD" ] || [ -n "$EE_FORCE_HF_CHECK" ]; } && ! python3 -c "import huggingface_hub" >/dev/null 2>&1; then
  echo "BAD_HOST: no uploader (huggingface_hub is missing and could not be installed${EE_HF_PIN:+ at $EE_HF_PIN})"
  end_seq BAD_HOST 1 1
fi

# --- 3. bad host (CR-06) ----------------------------------------------------------------------------------------------------
if command -v nvidia-smi >/dev/null 2>&1 || [ -n "$EE_REQUIRE_GPU_CHECK" ]; then
  timeout 120 nvidia-smi >/dev/null 2>&1; rc=$?
  if [ $rc -eq 0 ] && python3 -c "import torch" >/dev/null 2>&1; then
    timeout 120 python3 -c "import torch; x = torch.ones(8, device='cuda'); print((x * 2).sum().item())" >/dev/null 2>&1; rc=$?
  fi
  if [ $rc -ne 0 ]; then echo "BAD_HOST: GPU check rc=$rc"; end_seq BAD_HOST "$rc" "$EE_CAP_GRACE_S"; fi
fi

# --- 4. the job -------------------------------------------------------------------------------------------------------------
if ! curl -fsSL -m 300 -H "Authorization: Bearer $HF_TOKEN" "$EE_SCRIPT_URL" -o "$EE_SCRIPT"; then
  echo "could not download the pod script"; end_seq FAILED 22 "$EE_UPLOAD_GRACE_S"
fi
export EE_OUT EE_DEADLINE="$DEADLINE"
setsid bash "$EE_SCRIPT" &
SPID=$!
capped=0
while kill -0 "$SPID" 2>/dev/null; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    capped=1; echo "approved money/time limit reached: stopping the script"
    write_beat CAPPED
    kill -TERM -- "-$SPID" 2>/dev/null
    for _ in $(seq 1 "$EE_KILL_WAIT_S"); do kill -0 "$SPID" 2>/dev/null || break; sleep 1; done
    kill -KILL -- "-$SPID" 2>/dev/null
    break
  fi
  sleep "$EE_POLL_S"
done
wait "$SPID" 2>/dev/null; rc=$?
if [ "$capped" = 1 ]; then end_seq CAPPED "$rc" "$EE_CAP_GRACE_S"; fi
if [ "$rc" -eq 0 ]; then end_seq DONE 0 "$EE_UPLOAD_GRACE_S"; else end_seq FAILED "$rc" "$EE_UPLOAD_GRACE_S"; fi
