"""B1/G9 (OR-29 audit pass 1): the five P12a pod scripts exist, pass the free dry-run rules (lint, static rules, bash -n) and, run under
the real ``pod_wrapper.sh`` with a stubbed machine and short steps, do what the paid plan says each pod does. No network, no pod, no money.
The Hugging Face existence check of ``runpod dryrun`` is the one thing this test does not do (it needs the network)."""
import json
import subprocess
from pathlib import Path

import pytest
from test_pod_wrapper import _exe, pod  # noqa: F401 - the fixture running the real wrapper

from explainer_engine.cloud import dryrun as D, pins, runpod as R

DIR = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"
NAMES = "ABCDE"


def text(x):
    return (DIR / f"p12a_{x}.sh").read_text(encoding="utf-8")


@pytest.mark.parametrize("x", NAMES)
def test_each_script_passes_the_free_dryrun_rules_and_declares_its_heartbeat_and_stall(x):
    t = text(x)
    assert subprocess.run(["bash", "-n", str(DIR / f"p12a_{x}.sh")]).returncode == 0
    assert R.is_wrapper_script(t) and R.lint_pod_script(t) == [] and D.static_problems(t, pins.load()) == []
    assert R.heartbeat_of_script(t) == f"datasets/vano1919/tmr-artifacts:runs/p12a/{x}/beat.txt"
    assert R.stall_minutes_of_script(t) == 4
    assert "beat.txt" not in "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#"))   # the wrapper owns it
    assert [r for r in D.repo_ids(t) if r[1] == "model"] == ([("Qwen/Qwen-Image-2.1", "model")] if x == "A" else [])


def test_pod_a_downloads_shard_00002_at_the_pinned_revision_and_the_image_digest_is_the_pinned_one():
    t = text("A")
    assert "d26bb61231c349cf6b7896fa83353113880e1ba3" in t and "00002-of-00002" in t and "4261951904" in t
    assert "safetensors" not in t and "safe\"" not in t                                       # found by prefix and size: no weight-file name, assembled or not
    assert pins.load()["images"]["aitoolkit"]["digest"].split(":")[1] in t                    # the manifest A-3 reads is the pinned image's
    assert "$EE_OUT" not in "".join(ln for ln in t.splitlines() if "hf_hub_download" in ln)   # base weights never go to the vault


def _run(pod, x, **env):
    return pod(text(x), P12_STEP_S="0.1", **env)


def test_pod_b_fails_on_purpose_so_the_wrapper_ends_with_failed_rc_1_and_the_events_are_on_the_vault_side(pod):
    p, b, stops, stub = _run(pod, "B", EE_DRILL="no_self_stop")
    assert b["word"] == "FAILED" and b["rc"] == 1 and not stops                                # the drill: the pod never stops itself
    ev = [json.loads(ln) for ln in (stub / "hf" / "t.jsonl").read_text().splitlines()]
    assert [e["ev"] for e in ev] == ["script_start", "exit"] and ev[0]["drill"] == "no_self_stop" and ev[1]["rc"] == 1


def test_pod_e_ends_done_and_without_a_key_nobody_inside_stops_it(pod):
    p, b, stops, stub = _run(pod, "E", EE_DRILL="drop_key")
    assert b["word"] == "DONE" and b["boot"]["key"] == "none" and not stops


def test_pod_c_writes_ten_parts_and_pod_d_a_part_per_step(pod):
    p, b, stops, stub = _run(pod, "C")
    assert b["word"] == "DONE" and len(list((stub / "hf" / "parts").glob("part_*.bin"))) == 10
    assert all(f.stat().st_size == 1024 for f in (stub / "hf" / "parts").glob("part_*.bin"))


def test_pod_d_writes_its_parts_and_ends_when_the_cap_comes_with_every_part_uploaded(pod):
    p, b, stops, stub = pod(text("D"), P12_STEP_S="1", EE_DRILL="no_self_stop", EE_LIFETIME_S="5", EE_CAP_GRACE_S="1")
    assert b["word"] == "CAPPED" and not stops
    parts = sorted(f.name for f in (stub / "hf" / "parts").glob("part_*.bin"))
    assert len(parts) >= 2                                                                    # the script was killed mid-loop, files were uploaded first
    ev = [json.loads(ln)["ev"] for ln in (stub / "hf" / "t.jsonl").read_text().splitlines()]
    assert ev[0] == "script_start" and ev[-1] == "exit"                                       # the TERM reached the exit trap


def test_pod_a_records_boot_facts_the_download_speed_and_deletes_the_shard(pod, tmp_path):
    dl = tmp_path / "dl"
    fake_python = """#!/bin/bash
case "$1" in
  --version) echo "Python 3.11.9";;
  -c) echo "huggingface_hub 0.0 torch 0.0 cuda 12.4";;
  -) mkdir -p "$DL/transformer"; echo -n transformer/shard-00002 > "$DL/.shard"; head -c 5000000 /dev/zero > "$DL/transformer/shard-00002"; cat > /dev/null;;
esac
"""
    smi = "#!/bin/bash\n[ \"$1\" = -L ] && echo 'GPU 0: NVIDIA RTX A5000 (UUID: GPU-x)' || echo 'NVIDIA RTX A5000, 570.1, 24564 MiB'\n"
    bin_ = pod.out.parent / "bin"
    bin_.mkdir(exist_ok=True)
    _exe(bin_ / "python3", fake_python)
    p, b, stops, stub = pod(text("A"), smi=smi, P12_STEP_S="0.1", P12_DL=str(dl))
    assert b["word"] == "DONE" and b["rc"] == 0
    ev = {json.loads(ln)["ev"]: json.loads(ln) for ln in (stub / "hf" / "t.jsonl").read_text().splitlines()}
    assert {"script_start", "boot_facts", "dl_start", "dl_end", "skopeo", "exit"} <= set(ev)
    assert ev["dl_end"]["rc"] == 0 and ev["dl_end"]["bytes"] == 5000000 and "mb_per_s" in ev["dl_end"]
    assert ev["skopeo"].get("skipped") or "rc" in ev["skopeo"]
    facts = (stub / "hf" / "boot_facts.txt").read_text()
    assert "RTX A5000" in facts and "MemTotal" in facts and "Python 3.11" in facts and "RUNPOD_POD_ID=pp" in facts
    assert "RUNPOD_API_KEY" not in facts and "HF_TOKEN" not in facts                          # the pod's env holds keys: none of them is written
    assert not dl.exists() and not list((stub / "hf").rglob("*.safetensors"))                 # the shard is deleted and never went to the vault
