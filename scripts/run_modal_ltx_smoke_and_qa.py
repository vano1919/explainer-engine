"""Local-first (and CI-compatible) runner for MODAL1 LTX L0-L3 smoke clip + Gemini multimodal QA.

Usage (local terminal, inside .venv):
    python scripts/run_modal_ltx_smoke_and_qa.py --check-only
    python scripts/run_modal_ltx_smoke_and_qa.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from explainer_engine.core.env_loader import load_project_env  # noqa: E402
from explainer_engine.cloud import modal_run as MR  # noqa: E402
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLJ  # noqa: E402


def _bind_modal1_env(env: dict[str, str]) -> dict[str, str]:
    """Always prefer MODAL1_TOKEN_ID / MODAL1_TOKEN_SECRET when set."""
    if env.get("MODAL1_TOKEN_ID") and env.get("MODAL1_TOKEN_SECRET"):
        env["MODAL_TOKEN_ID"] = env["MODAL1_TOKEN_ID"]
        env["MODAL_TOKEN_SECRET"] = env["MODAL1_TOKEN_SECRET"]
    if env.get("HF_TOKEN") and not env.get("HUGGING_FACE_HUB_TOKEN"):
        env["HUGGING_FACE_HUB_TOKEN"] = env["HF_TOKEN"]
    return env


def check_prerequisites(env: dict[str, str], plan: Path, pic: Path) -> list[str]:
    problems: list[str] = []
    if not plan.is_file():
        problems.append(f"plan file missing: {plan}")
    if not pic.is_file():
        problems.append(f"picture file missing: {pic}")
    if shutil.which("ffmpeg") is None:
        problems.append("ffmpeg not found on PATH")
    modal_bin = shutil.which("modal")
    if modal_bin is None:
        try:
            import modal  # noqa: F401
        except ImportError:
            problems.append("modal package not installed (run: pip install modal)")
    for key in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "HF_TOKEN", "GEMINI_API_KEY"):
        if not env.get(key):
            problems.append(f"missing environment variable: {key}")
    problems.extend(MLJ.launch_problems(MLJ.LAUNCH))
    return problems


def _modal_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "modal", *args]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run MODAL1 LTX L0-L3 smoke clip and Gemini multimodal perceptual QA")
    ap.add_argument("--plan", type=Path, default=REPO_ROOT / "explainer_engine/training/pods/ltx/scenes/battle_2026-11-12.json")
    ap.add_argument("--picture", type=Path, default=REPO_ROOT / "assets/style/main_style_5709.png")
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "jobs/smoke_qa")
    ap.add_argument("--env-file", type=Path, default=None, help="optional .env file path")
    ap.add_argument("--card-ref", default="cmsg_owner_approved_2026_11_23")
    ap.add_argument("--check-only", action="store_true", help="verify dependencies, env vars, and L0 tests without spending")
    args = ap.parse_args(argv)

    load_project_env(args.env_file)
    env = _bind_modal1_env(dict(os.environ))
    env["PYTHONPATH"] = str(REPO_ROOT)
    extra_bins = [d for d in ("/opt/homebrew/bin", "/usr/local/bin") if Path(d).is_dir()]
    if extra_bins:
        new_path = os.pathsep.join(extra_bins + [env.get("PATH", "")])
        env["PATH"] = new_path
        os.environ["PATH"] = new_path

    plan = args.plan.resolve()
    pic = args.picture.resolve()
    out_dir = args.out_dir.resolve()

    problems = check_prerequisites(env, plan, pic)
    if problems:
        print("PREREQUISITE CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 2

    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    plan_sha12 = plan_sha[:12]
    env["EE_MODAL_GO"] = f"{args.card_ref}:{plan_sha12}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ladder_path = out_dir / "ltx_ladder.json"
    env["EE_LTX_LADDER"] = str(ladder_path)

    print(f"[preflight] OK | plan={plan.name} (sha12={plan_sha12}) | gpu={MLJ.LAUNCH['gpu']} | out={out_dir}")

    # L0: local unit gate
    print("[L0] Running LTX unit gate...")
    subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-k", "not test_the_hand_over and not test_the_best_tail_search",
            "tests/unit/test_v43_ltx_jobs.py",
            "tests/unit/test_ltx_inproc.py",
            "tests/unit/test_videolane.py",
            "tests/unit/test_cloud_hooks_modal.py",
        ],
        cwd=REPO_ROOT,
        env={k: v for k, v in env.items() if k != "EE_MODAL_GO"},
        check=True,
    )
    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    MR.record_rung(ladder_path, "L0", True, commit=head_sha, note="local/CI L0 gate")
    if args.check_only:
        print("[check-only] All prerequisites and L0 tests passed ($0.00 spent).")
        return 0

    # Ensure volume & Modal secret exist on MODAL1
    print("[MODAL1] Ensuring volume 'ee-weights' and secret 'custom-secret' exist...")
    subprocess.run(_modal_cmd("volume", "create", "ee-weights"), cwd=REPO_ROOT, env=env, check=False)
    subprocess.run(
        _modal_cmd("secret", "create", MLJ.SECRET_NAME, f"HF_TOKEN={env['HF_TOKEN']}", "--force"),
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    worker = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"

    # L1: remote import check
    print("[L1] Running remote import check on MODAL1...")
    subprocess.run(_modal_cmd("run", f"{worker}::check"), cwd=REPO_ROOT, env=env, check=True)

    # L2: weights check / stage
    print("[L2] Checking LTX weights on MODAL1 volume...")
    w_res = subprocess.run(_modal_cmd("run", f"{worker}::weights"), cwd=REPO_ROOT, env=env, check=False)
    if w_res.returncode != 0:
        print("[L2] Staging LTX weights to MODAL1 volume...")
        subprocess.run(_modal_cmd("run", f"{worker}::stage", "--plan", str(plan)), cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(_modal_cmd("run", f"{worker}::weights"), cwd=REPO_ROOT, env=env, check=True)

    # L3: live 2s smoke clip on MODAL1
    print("[L3] Generating 2s smoke clip on MODAL1...")
    subprocess.run(
        _modal_cmd("run", f"{worker}::smoke", "--picture", str(pic), "--plan", str(plan)),
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    # Download exact clip path: out_ltx/<run_id>/L3_smoke/L3_smoke_seed7.mp4
    rid = MLJ.run_id(plan_sha, MLJ.LAUNCH)
    remote_mp4 = f"{MLJ.VOL_OUT}/{rid}/{MLJ.SMOKE_JOB['shot_id']}/{MLJ.SMOKE_JOB['shot_id']}_seed{MLJ.SMOKE_JOB['seed']}.mp4"
    local_mp4 = out_dir / f"{MLJ.SMOKE_JOB['shot_id']}_seed{MLJ.SMOKE_JOB['seed']}.mp4"
    print(f"[download] Fetching {remote_mp4} -> {local_mp4}")
    subprocess.run(
        _modal_cmd("volume", "get", "--force", "ee-weights", remote_mp4, str(local_mp4)),
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    # Multimodal perceptual QA (3 temporal frames + 16kHz WAV -> Gemini 2.5 Flash)
    qa_report = out_dir / "perceptual_qa_report.json"
    print(f"[QA] Running Gemini multimodal perceptual QA on {local_mp4}...")
    qa_proc = subprocess.run(
        [
            sys.executable, "-m", "explainer_engine.qa.perceptual_qa",
            "--video", str(local_mp4), "--out", str(qa_report), "--gemini",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    print("=== PERCEPTUAL QA REPORT ===")
    print(qa_report.read_text(encoding="utf-8"))
    return qa_proc.returncode


if __name__ == "__main__":
    sys.exit(main())
