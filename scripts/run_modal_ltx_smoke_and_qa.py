"""Local-first and CI-compatible runner for MODAL1 LTX L0-L3 smoke clip + Gemini multimodal QA.

Hard rules enforced:
- --check-only requires zero paid credentials and zero approvals, and causes zero side effects.
- Live paid runs require an explicit --card-ref registered in config/owner_approvals.json bound to
  the full 64-character SHA-256 of the canonical operation manifest.
- Never passes HF_TOKEN on the command line and never overwrites Modal secrets with --force.
- L2 weights check never silently stages paid weights unless --stage-weights is explicitly passed.
- L0 runs the full required unit gate with zero -k exclusions.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from explainer_engine.cloud import modal_run as MR  # noqa: E402
from explainer_engine.cloud import night_budget as NB  # noqa: E402
from explainer_engine.core import approvals  # noqa: E402
from explainer_engine.core.env_loader import load_project_env  # noqa: E402
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ  # noqa: E402


def _bind_modal1_env(env: dict[str, str]) -> dict[str, str]:
    """Always prefer MODAL1_TOKEN_ID / MODAL1_TOKEN_SECRET when set."""
    if env.get("MODAL1_TOKEN_ID") and env.get("MODAL1_TOKEN_SECRET"):
        env["MODAL_TOKEN_ID"] = env["MODAL1_TOKEN_ID"]
        env["MODAL_TOKEN_SECRET"] = env["MODAL1_TOKEN_SECRET"]
    if env.get("HF_TOKEN") and not env.get("HUGGING_FACE_HUB_TOKEN"):
        env["HUGGING_FACE_HUB_TOKEN"] = env["HF_TOKEN"]
    return env


def _prepend_homebrew_path(env: dict[str, str]) -> None:
    extra_bins = [d for d in ("/opt/homebrew/bin", "/usr/local/bin") if Path(d).is_dir()]
    if extra_bins:
        new_path = os.pathsep.join(extra_bins + [env.get("PATH", "")])
        env["PATH"] = new_path
        os.environ["PATH"] = new_path


def check_prerequisites(env: dict[str, str], plan: Path, pic: Path, *, check_only: bool) -> list[str]:
    problems: list[str] = []
    if not plan.is_file():
        problems.append(f"plan file missing: {plan}")
    if not pic.is_file():
        problems.append(f"picture file missing: {pic}")
    if shutil.which("ffmpeg") is None:
        problems.append("ffmpeg not found on PATH")
    problems.extend(MLJ.launch_problems(MLJ.LAUNCH))

    if not check_only:
        if shutil.which("modal") is None:
            try:
                import modal  # noqa: F401
            except ImportError:
                problems.append("modal package not installed (run: pip install modal)")
        for key in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "HF_TOKEN", "GEMINI_API_KEY"):
            if not env.get(key):
                problems.append(f"missing environment variable: {key}")
    return problems


def build_operation_manifest(
    *,
    head_sha: str,
    plan: Path,
    pic: Path,
    operation_mode: str,
    estimated_usd: float,
) -> dict[str, Any]:
    return {
        "schema_version": "operation_manifest/1",
        "git_head_sha": head_sha,
        "provider": "modal_modal1",
        "operation_mode": operation_mode,
        "gpu": MLJ.LAUNCH.get("gpu"),
        "launch_sha256": MLJ.launch_sha(MLJ.LAUNCH),
        "worker_sha256": MLJ.worker_sha(),
        "plan_path": str(plan.relative_to(REPO_ROOT)) if plan.is_relative_to(REPO_ROOT) else plan.name,
        "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "picture_sha256": hashlib.sha256(pic.read_bytes()).hexdigest(),
        "estimated_max_usd": round(float(estimated_usd), 4),
    }


def _verify_modal_secret_present() -> None:
    """Verify the required Modal secret exists without passing token values on CLI or using --force."""
    import modal

    try:
        modal.Secret.from_name(MLJ.SECRET_NAME, required_keys=["HF_TOKEN"])
    except Exception as exc:
        raise SystemExit(
            f"Modal-ზე სეკრეტი '{MLJ.SECRET_NAME}' (გასაღებით HF_TOKEN) არ მოიძებნა ან არასწორია.\n"
            f"შექმენი ხელით Modal Dashboard-ში (MODAL1 პროფილზე) და ხელახლა გაუშვი. დეტალი: {type(exc).__name__}"
        ) from None


def _modal_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "modal", *args]


def _is_worktree_clean() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return p.returncode == 0 and not p.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run MODAL1 LTX L0-L3 smoke clip and Gemini multimodal perceptual QA")
    ap.add_argument("--plan", type=Path, default=REPO_ROOT / "explainer_engine/training/pods/ltx/scenes/battle_2026-11-12.json")
    ap.add_argument("--picture", type=Path, default=REPO_ROOT / "assets/style/main_style_5709.png")
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "jobs/smoke_qa")
    ap.add_argument("--env-file", type=Path, default=None, help="optional .env file path")
    ap.add_argument(
        "--card-ref",
        default=None,
        help="Explicit owner approval ID from config/owner_approvals.json (required for live paid runs; forbidden to default)",
    )
    ap.add_argument("--approvals-file", type=Path, default=None, help="optional path to owner_approvals.json")
    ap.add_argument("--stage-weights", action="store_true", help="explicitly authorize paid L2 weight staging if missing")
    ap.add_argument("--check-only", action="store_true", help="verify dependencies and L0 tests without credentials or spending")
    args = ap.parse_args(argv)

    if not args.check_only:
        load_project_env(args.env_file)
    env = _bind_modal1_env(dict(os.environ))
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{existing_pp}" if existing_pp else str(REPO_ROOT)
    _prepend_homebrew_path(env)

    plan = args.plan.resolve()
    pic = args.picture.resolve()
    out_dir = args.out_dir.resolve()

    problems = check_prerequisites(env, plan, pic, check_only=args.check_only)
    if problems:
        print("PREREQUISITE CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 2

    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    out_dir.mkdir(parents=True, exist_ok=True)
    ladder_path = out_dir / "ltx_ladder.json"
    env["EE_LTX_LADDER"] = str(ladder_path)
    if not args.check_only:
        env["EE_NIGHT_LEDGER"] = str(NB.default_night_ledger_path())

    # L0: full local unit gate with zero -k exclusions and zero paid credential leakage
    paid_env_keys = {
        "EE_MODAL_GO",
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "MODAL1_TOKEN_ID",
        "MODAL1_TOKEN_SECRET",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "ELEVENLABS_API_KEY",
        "RUNPOD_API_KEY",
        "BFL_API_KEY",
        "FAL_KEY",
    }
    l0_env = {k: v for k, v in env.items() if k not in paid_env_keys}
    print(f"[L0] Running full LTX unit gate on HEAD {head_sha[:12]}...")
    subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            "tests/unit/test_v43_ltx_jobs.py",
            "tests/unit/test_ltx_inproc.py",
            "tests/unit/test_videolane.py",
            "tests/unit/test_cloud_hooks_modal.py",
        ],
        cwd=REPO_ROOT,
        env=l0_env,
        check=True,
    )
    if _is_worktree_clean():
        MR.record_rung(ladder_path, "L0", True, commit=head_sha, note="clean worktree L0 gate")
    else:
        print("[L0] Worktree has uncommitted changes; skipping release-quality L0 stamp.")

    if args.check_only:
        print("[check-only] All prerequisites and full L0 tests passed ($0.00 spent).")
        return 0

    # Strict approval verification bound to 64-character SHA-256 operation manifest BEFORE any paid side effect
    op_mode = "modal-ltx-stage-and-smoke" if args.stage_weights else "modal-ltx-smoke"
    smoke_est = MLJ.hard_bill_usd(MLJ.LAUNCH, MLJ.TIMEOUTS[0])
    stage_est = MLJ.stage_hard_bill_usd() if args.stage_weights else 0.0
    est_usd = round(smoke_est + stage_est, 4)
    manifest = build_operation_manifest(
        head_sha=head_sha,
        plan=plan,
        pic=pic,
        operation_mode=op_mode,
        estimated_usd=est_usd,
    )
    manifest_sha256 = approvals.canonical_manifest_sha256(manifest)
    try:
        approvals.verify_approval(
            args.card_ref,
            provider="modal_modal1",
            operation_mode=op_mode,
            manifest_sha256=manifest_sha256,
            requested_usd=est_usd,
            registry_path=args.approvals_file,
        )
    except approvals.ApprovalError as exc:
        print(f"APPROVAL VERIFICATION FAILED: {exc}")
        return 3

    plan_sha = manifest["plan_sha256"]
    env["EE_MODAL_GO"] = f"{args.card_ref}:{plan_sha[:12]}"
    env["EE_MODAL_APPROVAL_MANIFEST_SHA256"] = manifest_sha256
    env["EE_MODAL_OPERATION_MODE"] = op_mode
    env["EE_MODAL_ESTIMATED_USD"] = f"{est_usd:.4f}"

    # Verify Modal secret safely (no CLI token args, no --force overwrite)
    _verify_modal_secret_present()
    subprocess.run(_modal_cmd("volume", "create", "ee-weights"), cwd=REPO_ROOT, env=env, check=False)

    worker = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"

    print("[L1] Running remote import check on MODAL1...")
    subprocess.run(_modal_cmd("run", f"{worker}::check"), cwd=REPO_ROOT, env=env, check=True)

    print("[L2] Checking LTX weights on MODAL1 volume...")
    w_res = subprocess.run(_modal_cmd("run", f"{worker}::weights"), cwd=REPO_ROOT, env=env, check=False)
    if w_res.returncode != 0:
        if not args.stage_weights:
            print("[L2] Weights check failed. Pass --stage-weights with an explicit stage approval to stage weights.")
            return 4
        print("[L2] Staging LTX weights to MODAL1 volume (explicitly authorized)...")
        subprocess.run(_modal_cmd("run", f"{worker}::stage", "--plan", str(plan)), cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(_modal_cmd("run", f"{worker}::weights"), cwd=REPO_ROOT, env=env, check=True)

    print("[L3] Generating 2s smoke clip on MODAL1 (single attempt, no auto-retry)...")
    l3_res = subprocess.run(
        _modal_cmd("run", f"{worker}::smoke", "--picture", str(pic), "--plan", str(plan)),
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    if l3_res.returncode != 0:
        print(f"[L3] Smoke generation failed with exit code {l3_res.returncode}; stopping without retry.")
        return l3_res.returncode

    rid = MLJ.run_id(plan_sha, MLJ.LAUNCH)
    remote_mp4 = f"{MLJ.VOL_OUT}/{rid}/{MLJ.SMOKE_JOB['shot_id']}/{MLJ.SMOKE_JOB['shot_id']}_seed{MLJ.SMOKE_JOB['seed']}.mp4"
    local_mp4 = out_dir / f"{MLJ.SMOKE_JOB['shot_id']}_seed{MLJ.SMOKE_JOB['seed']}.mp4"
    subprocess.run(
        _modal_cmd("volume", "get", "--force", "ee-weights", remote_mp4, str(local_mp4)),
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    qa_report = out_dir / "perceptual_qa_report.json"
    qa_proc = subprocess.run(
        [
            sys.executable, "-m", "explainer_engine.qa.perceptual_qa",
            "--video", str(local_mp4), "--out", str(qa_report), "--gemini",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    if not qa_report.is_file():
        print(f"[QA] Missing expected perceptual QA report: {qa_report}")
        return 5
    print("=== PERCEPTUAL QA REPORT ===")
    print(qa_report.read_text(encoding="utf-8"))
    return qa_proc.returncode


if __name__ == "__main__":
    sys.exit(main())
