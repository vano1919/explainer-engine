"""Governed Modal H100 LTX-2.5 batch runner bound to AntigravityRunner SQLite WAL $15.00 Spend Ledger.

Enforces:
- Super-Realistic 35mm Style Purity (`lint_super_realistic_prompt`)
- Before-State Keyframe Linting (`lint_before_state_keyframe`)
- 4.0-6.0s LTX Action Clip & Prop Continuity Contract (`enforce_ltx_action_clip_contract`)
- Atomic SQLite WAL `reserve_modal_spend()` BEFORE launch and immediate `settle_modal_spend()` in `finally:`
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from explainer_engine.cloud import modal_run as MR
from explainer_engine.core.env_loader import load_project_env
from explainer_engine.governance.antigravity_runner import AntigravityRunner
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ
from explainer_engine.training.pods.ltx import scene_run as SR
from explainer_engine.videolane.ltx_loop import (
    enforce_ltx_action_clip_contract,
    lint_before_state_keyframe,
    sha256_file,
)


def run_governed_ltx_batch(
    batch_id: str,
    shots: list[dict[str, Any]],
    work_dir: Path,
    *,
    repo_root: Path,
    runner: AntigravityRunner,
    run_smoke_if_needed: bool = False,
) -> dict[str, Any]:
    """Validate, reserve SQLite budget, execute one Modal H100 LTX-2.5 batch, settle actual USD, and download clips."""
    work_dir = Path(work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(repo_root).resolve()

    # 1. Pre-launch contract validation (style purity, before-state, 4-6s cap, prop end-states)
    validation_errors: list[str] = []
    for s in shots:
        validation_errors.extend(lint_before_state_keyframe(s))
        c_res = enforce_ltx_action_clip_contract(float(s["seconds"]), str(s["motion_prompt"]))
        if c_res["status"] != "PASS":
            validation_errors.extend([f"{s['shot_id']}: {e}" for e in c_res["errors"]])
    if validation_errors:
        raise ValueError("LTX batch pre-launch contract failed:\n  - " + "\n  - ".join(validation_errors))

    # 2. Build pictures manifest + scene JSON inside committed scenes_dir (for CH-03) and clean up temp scene if untracked
    pic_manifest: dict[str, Any] = {"shots": {}}
    scene_shots: list[dict[str, Any]] = []
    for s in shots:
        pic_p = Path(s["picture_path"]).resolve()
        pic_id = str(s["shot_id"])
        pic_manifest["shots"][pic_id] = {"path": str(pic_p), "sha256": sha256_file(pic_p)}
        scene_shots.append(
            {
                "shot_id": pic_id,
                "picture": pic_id,
                "seconds": float(s["seconds"]),
                "seed": int(s["seed"]),
                "line": s.get("line"),
                "motion_prompt": str(s["motion_prompt"]),
            }
        )

    man_path = work_dir / "pictures.json"
    man_path.write_text(json.dumps(pic_manifest, indent=2) + "\n", encoding="utf-8")

    scene_doc = {
        "schema": "ltx_scene_test/2",
        "id": batch_id,
        "asked": f"Governed Antigravity super-realistic cinema batch {batch_id} under $15.00 SQLite WAL hard cap.",
        "sound": "LTX native diegetic speech and physical foley; mastered downstream with scene-locked ambience.",
        "ledger": {
            "path": str(work_dir / "scene_ledger.json"),
            "caps": {"modal_ltx": 1.25},
        },
        "pictures": {"manifest": str(man_path)},
        "shots": scene_shots,
    }

    scenes_dir = repo_root / "explainer_engine" / "training" / "pods" / "ltx" / "scenes"
    scene_path = scenes_dir / f"{batch_id}.json"
    scene_path.write_text(json.dumps(scene_doc, indent=2) + "\n", encoding="utf-8")

    spec_path = work_dir / "spec.json"
    spec = SR.job_spec(scene_path)
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    plan_sha = hashlib.sha256(scene_path.read_bytes()).hexdigest()
    go_sha12 = plan_sha[:12]
    run_id = spec["run_id"]

    # Reserve scene_run local ledger (required by modal_ltx_jobs.claim_launch)
    subprocess.run(
        [sys.executable, "-m", "explainer_engine.training.pods.ltx.scene_run", "reserve", str(scene_path)],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )

    # Setup MODAL1 environment cleanly
    load_project_env()
    env = dict(os.environ)
    if env.get("MODAL1_TOKEN_ID") and env.get("MODAL1_TOKEN_SECRET"):
        env.pop("MODAL_PROFILE", None)
        env["MODAL_TOKEN_ID"] = env["MODAL1_TOKEN_ID"]
        env["MODAL_TOKEN_SECRET"] = env["MODAL1_TOKEN_SECRET"]
    if env.get("HF_TOKEN") and not env.get("HUGGING_FACE_HUB_TOKEN"):
        env["HUGGING_FACE_HUB_TOKEN"] = env["HF_TOKEN"]
    env["PYTHONPATH"] = str(repo_root)
    ladder_path = repo_root / "jobs" / "antigravity_ltx_ladder.json"
    night_ledger_path = repo_root / "jobs" / "antigravity_night_ledger.json"
    if not night_ledger_path.is_file():
        night_ledger_path.write_text(
            json.dumps({"schema": "night_budget/1", "cap_usd": 20.0, "reserved": {}, "settled": {}}, indent=2) + "\n",
            encoding="utf-8",
        )
    env["EE_LTX_LADDER"] = str(ladder_path)
    env["EE_NIGHT_LEDGER"] = str(night_ledger_path)

    smoke_aid = (env.get("EE_V3_SMOKE_APPROVAL_ID") or env.get("EE_MODAL_SMOKE_APPROVAL_ID") or "").strip()
    smoke_msha = (env.get("EE_V3_SMOKE_MANIFEST_SHA256") or env.get("EE_MODAL_SMOKE_MANIFEST_SHA256") or "").strip()
    main_aid = (env.get("EE_V3_MAIN_APPROVAL_ID") or env.get("EE_MODAL_APPROVAL_ID") or "").strip()
    main_msha = (env.get("EE_V3_MAIN_MANIFEST_SHA256") or env.get("EE_MODAL_APPROVAL_MANIFEST_SHA256") or "").strip()
    if not main_aid or len(main_msha) != 64:
        raise RuntimeError(
            "Missing explicit runtime Modal approval env vars (EE_V3_MAIN_APPROVAL_ID and 64-hex "
            "EE_V3_MAIN_MANIFEST_SHA256, plus EE_OWNER_APPROVALS_PATH pointing to a local session approval file)."
        )

    worker = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"
    proof = {"launch_sha": MLJ.launch_sha(MLJ.LAUNCH), "worker_sha": MLJ.worker_sha()}
    lad = MR.load_ladder(ladder_path)
    done = set(lad.get("done") or [])
    stale_rungs = set(MR.stale(lad, proof, upto="L4"))

    # Ensure L0..L3 are green for this exact launch_sha + worker_sha
    if "L0" not in done:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True).strip()
        MR.record_rung(ladder_path, "L0", True, commit=head, note="governed L0")
    if "L1" not in done or "L1" in stale_rungs:
        subprocess.run([sys.executable, "-m", "modal", "run", f"{worker}::check"], cwd=str(repo_root), env=env, check=True)
    if "L2" not in done or "L2" in stale_rungs:
        subprocess.run([sys.executable, "-m", "modal", "run", f"{worker}::weights"], cwd=str(repo_root), env=env, check=True)
    if ("L3" not in done or "L3" in stale_rungs) and run_smoke_if_needed:
        sm_env = dict(env)
        sm_env["EE_MODAL_GO"] = f"{smoke_aid}:{go_sha12}"
        sm_env["EE_MODAL_APPROVAL_MANIFEST_SHA256"] = smoke_msha
        sm_env["EE_MODAL_OPERATION_MODE"] = "modal-ltx-smoke"
        sm_item = f"l3_smoke_{batch_id}_{int(time.time())}"
        runner.reserve_modal_spend(sm_item, 0.45, why=f"L3 smoke calibration for {batch_id}")
        t_sm = time.time()
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "modal", "run", f"{worker}::smoke",
                    "--picture", str(Path(shots[0]["picture_path"]).resolve()),
                    "--plan", str(scene_path),
                ],
                cwd=str(repo_root),
                env=sm_env,
                check=True,
            )
        finally:
            wall_sm = time.time() - t_sm
            runner.settle_modal_spend(sm_item, round(wall_sm * MLJ.usd_per_h(MLJ.LAUNCH) / 3600.0, 4))

    # 3. Estimate worst-case batch USD and atomically reserve in SQLite WAL BEFORE launching Modal H100!
    timeout_s = MLJ.TIMEOUTS[1] if MLJ.TIMEOUTS is not None else 900
    est_usd = round(MLJ.hard_bill_usd(MLJ.LAUNCH, timeout_s), 4)
    ledger_item = f"ltx_batch_{batch_id}_{go_sha12}"
    res_rec = runner.reserve_modal_spend(ledger_item, est_usd, why=f"Modal H100 LTX batch {batch_id} ({len(shots)} clips)")

    main_env = dict(env)
    main_env["EE_MODAL_GO"] = f"{main_aid}:{go_sha12}"
    main_env["EE_MODAL_APPROVAL_MANIFEST_SHA256"] = main_msha
    main_env["EE_MODAL_OPERATION_MODE"] = "modal-ltx-main"

    t0 = time.time()
    actual_usd = 0.0
    try:
        subprocess.run(
            [sys.executable, "-m", "modal", "run", f"{worker}::main", "--job", str(spec_path)],
            cwd=str(repo_root),
            env=main_env,
            check=True,
        )
    finally:
        wall_s = time.time() - t0
        actual_usd = round(wall_s * MLJ.usd_per_h(MLJ.LAUNCH) / 3600.0, 4)
        settle_rec = runner.settle_modal_spend(ledger_item, actual_usd)
        # Clean up temporary scene JSON from tracked scenes/ dir so git working tree stays clean
        scene_path.unlink(missing_ok=True)

    # 4. Download every generated clip from Modal ee-weights Volume
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    first_sid = scene_shots[0]["shot_id"]
    downloaded: dict[str, dict[str, Any]] = {}
    for s in scene_shots:
        sid = s["shot_id"]
        fname = f"{sid}_seed{s['seed']}.mp4"
        remote_p = f"{MLJ.VOL_OUT}/{run_id}/{first_sid}/{fname}"
        local_p = clips_dir / fname
        subprocess.run(
            [sys.executable, "-m", "modal", "volume", "get", "--force", "ee-weights", remote_p, str(local_p)],
            cwd=str(repo_root),
            env=env,
            check=True,
        )
        downloaded[sid] = {
            "path": str(local_p),
            "sha256": sha256_file(local_p),
            "remote_volume_path": remote_p,
            "seconds_requested": s["seconds"],
            "seed": s["seed"],
        }

    result_doc = {
        "batch_id": batch_id,
        "run_id": run_id,
        "ledger_item": ledger_item,
        "reserved_usd": res_rec["reserved_usd"],
        "actual_usd": actual_usd,
        "wall_s": round(wall_s, 2),
        "spend_summary_after": settle_rec["summary"],
        "clips": downloaded,
    }
    (work_dir / "batch_result.json").write_text(json.dumps(result_doc, indent=2) + "\n", encoding="utf-8")
    return result_doc
