"""A finished master (not a single shot) must carry an audio stream. A missing stream on the whole master is never intended: ``silent_by_design``
(OR-C04) is per shot and means a silent bed inside a stream, not a missing one. Whether the owner wants a master without sound allowed was left to
ask once; until he says so this is a FAIL.

``audio_present(path) -> {"status", "value", "detail"}``; ``value`` is the number of audio streams. ffprobe missing is NOT_RUN, never a pass; a file ffprobe
cannot read raises (the send gate BLOCKs). ``audio_present.kinds`` lists the suffixes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"


def audio_present(path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"{p} is not a file")
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "json", str(p)],
                           capture_output=True, timeout=300)
    except FileNotFoundError:
        return {"status": NOT_RUN, "value": None, "detail": "ffprobe is missing: audio not checked"}
    if r.returncode != 0:
        raise RuntimeError("ffprobe could not read the file: " + r.stderr.decode("utf-8", "replace")[-200:])
    n = len(json.loads(r.stdout.decode() or "{}").get("streams", []))
    if n == 0:
        return {"status": FAIL, "value": 0, "detail": "the master has no audio stream"}
    return {"status": PASS, "value": n, "detail": f"{n} audio stream(s)"}


audio_present.kinds = (".mp4", ".mov", ".mkv", ".avi", ".webm")


def main(argv=None) -> int:
    """``python -m explainer_engine.qa.audio_present <master>...``: one line per file, exit 1 on a FAIL, 2 on an error."""
    worst = 0
    for f in (argv if argv is not None else sys.argv[1:]):
        try:
            r = audio_present(f)
        except Exception as exc:
            print(f"BLOCK {f}: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        print(f"{r['status']:8} {'' if r['value'] is None else r['value']!s:>7}  {f}  {r['detail']}")
        worst = max(worst, 1 if r["status"] == FAIL else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())
