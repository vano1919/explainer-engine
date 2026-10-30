"""``python -m explainer_engine.cloud.secrets_check [NAME ...]``: the pre-pod gate for the GitHub repository secrets the cloud
workflows read (CR-19). It prints, for each name, only ``present`` or ``MISSING`` and exits 1 when any is missing or blank. It never
prints a value, a prefix, a length or a hash, so a log line cannot leak or hint at a secret. stdlib only.

It runs in ``.github/workflows/secrets_check.yml`` (manual: "Run workflow"), where the secrets are mapped into the environment by
``${{ secrets.NAME }}``; GitHub passes an unset secret as an empty string, which counts as missing here. What it proves is that
the repository secret exists and is not blank; it does not prove the token is valid or has the right scope (the watchdog's first
pass and the P12a smoke test show that).
"""
from __future__ import annotations

import os
import sys

# What the cloud workflows need (``.github/workflows/watchdog.yml`` header): the RunPod key to stop pods, the Hugging Face token to read
# the heartbeats and live records, the ntfy topic for the push to the creator's phone. The workflow maps exactly these names.
REQUIRED = ("HF_TOKEN", "RUNPOD_API_KEY", "NTFY_TOPIC")


def check(names=REQUIRED, env=None):
    """[(name, present)] in the order given; a value that is empty or only whitespace is not present."""
    env = os.environ if env is None else env
    return [(n, bool((env.get(n) or "").strip())) for n in names]


def report(rows):
    return "\n".join(f"{n}: {'present' if ok else 'MISSING'}" for n, ok in rows)


def main(names=(), env=None):
    names = tuple(names) or REQUIRED
    rows = check(names, env)
    print(report(rows))
    missing = [n for n, ok in rows if not ok]
    if missing:
        print(f"::error::missing repository secret(s): {', '.join(missing)} (Settings > Secrets and variables > Actions)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
