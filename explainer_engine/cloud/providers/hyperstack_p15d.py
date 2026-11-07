"""p15d on a Hyperstack VM (PREPARED, NOT ENABLED): the cloud-init that starts the job, the name that carries the deadline, and the
external guard that DELETEs the VM (D-56 money control, creator 2026-11-07: Hyperstack/Modal as the fallback after RunPod).

Why it exists: ``HyperstackAdapter.submit_job`` boots a bare Ubuntu VM and nothing else; RunPod's wrapper (``pod_wrapper.sh``: upload loop,
money dead-man, end word in ``beat.txt``) stops a pod by the RunPod API, which a VM does not have. On Hyperstack the wrapper still runs
inside the same pinned image, writes the same ``beat.txt`` to HF and cannot stop the VM (``SHUTOFF`` would bill 100 %): the VM is DELETEd
from outside, by ``sweep`` (the session) and by the same function in the Actions watchdog. The API key never goes on the VM.
Nothing here calls the network by itself; every function takes the adapter or the text it needs.
"""

from __future__ import annotations

import base64
import re
import shlex
from pathlib import Path
from typing import Any, Callable

from explainer_engine.cloud.providers.base import ProviderError, WorkloadSpec

# p15d = 24 Qwen pictures + 2 mouth sheets + 1 battle clip of 121 frames (RunPod schedule p15qc1: 34 min of GPU on an A100, 8 min setup).
P15D_WORKLOAD = WorkloadSpec(
    workload_id="p15d_qwen24_sheets2_ltx121", kind="combined_p12_p14", min_vram_gb=80, min_ram_gb=96, min_disk_gb=200,
    ref_a100_work_minutes=34.0, setup_minutes_cold=16.0, setup_minutes_warm=3.0, egress_gb=1.0, max_budget_usd=3.1,
)
END_WORDS = ("DONE", "FAILED", "CAPPED", "FAILED_UPLOAD", "BAD_HOST")   # what pod_wrapper.sh writes as the last word of beat.txt
NAME_RE = re.compile(r"^ee-[a-z0-9-]+-until-(\d{9,11})$")
WRAPPER = Path(__file__).resolve().parents[1] / "pod_wrapper.sh"
SECRET_NAMES = ("HF_TOKEN",)   # passed at create time from the environment, never written into a file of this repository


def vm_name(job: str, deadline_epoch: int) -> str:
    """``ee-<job>-until-<epoch>``, at most 50 characters (Hyperstack's limit); the epoch is the dead-man the guard reads."""
    slug = re.sub(r"[^a-z0-9-]+", "-", job.lower()).strip("-")[: 50 - len("ee--until-") - 10]
    return f"ee-{slug}-until-{int(deadline_epoch)}"


def deadline_of(name: str) -> int | None:
    m = NAME_RE.match(name or "")
    return int(m.group(1)) if m else None


def cloud_init(image_ref: str, env: dict[str, str], *, secrets: dict[str, str] | None = None) -> str:
    """The cloud-config ``user_data`` that runs the wrapper in the pinned image on the VM. ``env`` = ``runpod.wrapper_env(...)`` (EE_*, no
    secrets); ``secrets`` (HF_TOKEN) are put in a root-only env file at create time, so the text of a commit never holds one."""
    if "@sha256:" not in image_ref:
        raise ProviderError(f"image {image_ref!r} is not pinned by digest (decision B3)")
    for k in (secrets or {}):
        if k not in SECRET_NAMES:
            raise ProviderError(f"unexpected secret {k!r}: only {SECRET_NAMES} may reach the VM")
    if any(k in env for k in SECRET_NAMES) or any(re.search(r"api[_-]?key|token", k, re.I) for k in env):
        raise ProviderError("secrets go through `secrets=`, not `env`")
    wrapper_b64 = base64.b64encode(WRAPPER.read_bytes()).decode()
    env_lines = "\n".join(f"{k}={shlex.quote(str(v))}" for k, v in sorted(env.items()))
    secret_lines = "\n".join(f"{k}={shlex.quote(v)}" for k, v in sorted((secrets or {}).items()))
    return f"""#cloud-config
write_files:
  - path: /root/ee/wrapper.sh.b64
    permissions: '0600'
    content: {wrapper_b64}
  - path: /root/ee/job.env
    permissions: '0600'
    content: |
{_indent(env_lines + chr(10) + secret_lines, 6)}
runcmd:
  - [ bash, -c, "base64 -d /root/ee/wrapper.sh.b64 > /root/ee/wrapper.sh && docker run -d --name ee-job --gpus all --env-file /root/ee/job.env {image_ref} bash /dev/stdin < /root/ee/wrapper.sh || docker run -d --name ee-job --gpus all --env-file /root/ee/job.env -v /root/ee/wrapper.sh:/w.sh {image_ref} bash /w.sh" ]
"""


def _indent(text: str, n: int) -> str:
    return "\n".join(" " * n + line for line in text.splitlines())


def last_word(beat_text: str | None) -> str | None:
    """The end word in a ``beat.txt`` (the first token that is one of END_WORDS), else None while the job still runs."""
    for tok in re.split(r"\s+", beat_text or ""):
        if tok in END_WORDS:
            return tok
    return None


def decision(vm: dict[str, Any], beat_text: str | None, now: float, *, grace_s: int = 120) -> tuple[str, str]:
    """("delete" | "keep", why) for one VM. Only VMs named ``ee-*-until-<epoch>`` are ours; any other VM is left alone."""
    name = str(vm.get("name", ""))
    until = deadline_of(name)
    if until is None:
        return "keep", "not an ee VM"
    status = str(vm.get("status", "")).upper()
    if status == "SHUTOFF":
        return "delete", "SHUTOFF bills 100 % of the GPU rate: delete"
    if now >= until + grace_s:
        return "delete", f"dead-man: past the deadline {until}"
    word = last_word(beat_text)
    if word:
        return "delete", f"the job ended: {word} (uploads are verified before the end word)"
    return "keep", "running within its deadline"


def sweep(adapter: Any, now: float, read_beat: Callable[[str], str | None], *, dry_run: bool = True) -> list[dict[str, str]]:
    """Walk every VM of the account; DELETE the ones ``decision`` says (never ``stop``). ``read_beat(name)`` returns the job's beat.txt text
    from HF (or None). ``dry_run`` (default) only reports. Returns one row per ee VM."""
    rows = []
    for vm in adapter.list_vms():
        name = str(vm.get("name", ""))
        verdict, why = decision(vm, read_beat(name) if deadline_of(name) is not None else None, now)
        if deadline_of(name) is None:
            continue
        row = {"name": name, "id": str(vm.get("id", "")), "verdict": verdict, "why": why, "done": "no"}
        if verdict == "delete" and not dry_run:
            adapter.cancel_job(row["id"], mode="delete")
            row["done"] = "deleted"
        rows.append(row)
    return rows
