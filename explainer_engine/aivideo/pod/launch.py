# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/aivideo/pod/launch.py`
# Target Module : explainer_engine/aivideo/pod/launch.py
# Target Classes/Symbols : (module-level definitions)
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""RETIRED by D-80 (2026-10-26): starts a pod outside the CLI (no script lint, no heartbeat, no pins, no ledger-per-test)
and pulls pod.sh that loads the banned wldnk_wan22_v1 LoRA. Kept as history (invariant 8: deletion only on the creator's
word); never run.

Create the night-run pod through the one pod manager (preflight, ledger, guard). Run from an explainer-engine checkout."""
# before any import: run as a script, the explainer_engine import fails without PYTHONPATH, so a guard below it never prints
raise SystemExit("RETIRED by D-80: this launcher never runs; pods start only through "
                 "python -m explainer_engine.cloud.runpod create (OR-21)")
import base64, json, sys
from explainer_engine.cloud import runpod as rp
from explainer_engine.core.ledger import Run

MAX_USD, MAX_H = 2.4, 7.5  # under 80 % of the ledger cap 3.6 (the ledger's stop rule), minus ~$0.45 of tries 1-2
CAP = 3.6
LEDGER = "/mnt/project-files/explainer-engine/hybrid_model_2026-10-22/night_run/night_run_ledger.json"
POD_SH = "/mnt/project-files/explainer-engine/hybrid_model_2026-10-22/night_run/pod/pod.sh"
api = rp.Api()
why = rp.preflight_create(api, max_usd=MAX_USD, max_hours=MAX_H, gpu="default")
if why:
    raise SystemExit("refused: " + "; ".join(why))
run = Run.open(LEDGER, caps={"runpod_usd": CAP}, purpose="night run: Wan 2.2 style LoRA + 2-min test video (ვანო 22:50-22:54)")
run.reserve("runpod_usd", MAX_USD, item="pod:pending")
body = rp.create_body(rp.pod_name("ee-night", MAX_H), "default", min_ram=40, volume=0)  # container disk only: nothing bills once stopped
body.pop("volumeMountPath", None)
body.update(imageName="ostris/aitoolkit:latest", containerDiskInGb=200, ports=["22/tcp"], gpuTypePriority="custom")
URL = "https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/night_run_2026-10-22/code/pod.sh"
body["dockerStartCmd"] = ["bash", "-c", 'mkdir -p /workspace; curl -fsSL -H "Authorization: Bearer $HF_TOKEN" ' + URL +
                          ' -o /workspace/pod.sh && bash /workspace/pod.sh; tail -f /dev/null']
body["allowedCudaVersions"] = ["12.4", "12.6", "12.8", "12.9", "13.0"]
pod = None
for cloud, gpus in [("COMMUNITY", ["NVIDIA A40", "NVIDIA RTX A6000", "NVIDIA L40S", "NVIDIA L40", "NVIDIA RTX 6000 Ada Generation"]),
                    ("SECURE", ["NVIDIA A40", "NVIDIA RTX A6000", "NVIDIA L40S", "NVIDIA L40", "NVIDIA RTX 6000 Ada Generation"])]:
    body.update(cloudType=cloud, gpuTypeIds=gpus, name=rp.pod_name("ee-night", MAX_H))
    try:
        pod = rp.create(api, body, max_price=0.8)
        print("cloud", cloud)
        break
    except rp.RunPodError as e:
        print(cloud, "unavailable:", str(e)[:900])
if pod is None:
    Run.open(LEDGER).settle("runpod_usd", "pod:pending", 0.0)
    raise SystemExit("no GPU")
Run.open(LEDGER).rename_reservation("pod:pending", f"pod:{pod['id']}")
rp.new_session(pod, max_usd=MAX_USD, max_hours=MAX_H, on_cap="stop", ledger=LEDGER)
m = pod.get("machine") if isinstance(pod.get("machine"), dict) else {}
print("pod", pod["id"], body["name"], pod.get("costPerHr"), m.get("gpuDisplayName"))
print("guard pid", rp.guard_detached(pod["id"]))
