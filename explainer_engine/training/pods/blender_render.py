"""The Blender render pod (OR-21, D-96; roadmap section 11 and 10.4). ``blender_render.sh`` runs it inside ``pod_wrapper.sh``:

    python3 -m explainer_engine.training.pods.blender_render render --job <vault path of the pod job> --binary <blender>
            --out "$EE_OUT" --render /workspace/render
    python -m explainer_engine.training.pods.blender_render bundle --out ee_src.tar.gz     # the code the pod runs (git archive of HEAD)

The pod job (``blender_pod_job/1``, a small JSON on the vault, written by the session before the pod is created):

    {"job": "blender_pod_job/1", "job_id": "...", "device": "gpu", "chunk_size": 8, "reserve_s": 600,
     "shots": [{"spec": "<vault path of a shot_spec/2>", "scene": {"path": "<vault path of the .blend>", "sha256": "..."}}]}

For each shot it pulls the spec and the scene, holds the scene to its sha256, and runs ``blender.render.HeadlessRender`` with the
vault as the frame store (every frame RENDERED -> DURABLY_STORED -> COMMITTED; a resumed pod renders only the frames the vault's
checkpoint does not hold). It writes ``progress.txt`` and the shots' render manifests under ``$EE_OUT`` (the wrapper uploads that
folder), and ``units.json`` (``{job_type, units, work_s}``) for ``runpod cost`` when every shot rendered at one profile on the
1440p master. It ends with the vault check of the whole render folder (VT-01) and exits non-zero on any render, upload or check
failure, so the wrapper never writes DONE before every paid frame is proven on the vault (rule 4 of 10.4, VT-02).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine import vault as V
from explainer_engine.blender import profiles as P
from explainer_engine.blender.project import BlenderPinError, BlenderProject
from explainer_engine.blender.render import HFVault, HeadlessRender, RenderFailed, UploadFailed
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_PATHS = ("explainer_engine", "config")
RC_RENDER, RC_UPLOAD, RC_CHECK, RC_JOB = 3, 4, 5, 6


def _progress(out: Path, text: str) -> None:
    write_text_atomic(out / "progress.txt", f"{time.strftime('%H:%M:%S', time.gmtime())} {text}\n")


def load_job(vault, path: str, tmp: Path) -> dict:
    local = tmp / "pod_job.json"
    if not vault.download(path, local):
        raise ContractError(f"the pod job {path} is not on the vault")
    job = json.loads(local.read_text(encoding="utf-8"))
    if job.get("job") != "blender_pod_job/1" or not job.get("job_id") or not isinstance(job.get("shots"), list) or not job["shots"]:
        raise ContractError(f"{path} is not a blender_pod_job/1 with a job_id and shots")
    if job.get("device", "gpu") not in ("cpu", "gpu"):
        raise ContractError(f"device {job.get('device')!r} is cpu or gpu")
    return job


def fetch_shot(vault, shot: dict, tmp: Path) -> tuple[dict, dict]:
    spec_local = tmp / "specs" / Path(shot["spec"]).name
    if not vault.download(shot["spec"], spec_local):
        raise ContractError(f"the shot spec {shot['spec']} is not on the vault")
    spec = json.loads(spec_local.read_text(encoding="utf-8"))
    C.validate(spec)
    sc = shot.get("scene") or {}
    if not sc.get("path") or not sc.get("sha256"):
        raise ContractError(f"{spec['shot_id']}: the pod job names no scene (.blend path and sha256, ICW-06)")
    blend = tmp / "scenes" / Path(sc["path"]).name
    if not vault.download(sc["path"], blend) or C.sha256_file(blend) != sc["sha256"]:
        raise ContractError(f"{spec['shot_id']}: the scene {sc['path']} is missing on the vault or differs from its sha256")
    return spec, {"kind": "blend", "path": str(blend), "sha256": sc["sha256"]}


def units_line(manifests: list[dict]) -> dict | None:
    """``units.json`` for ``runpod cost``: one job type (one profile, every shot at the 1440p master), frames rendered by THIS pod."""
    jobs = {m["_job_type"] for m in manifests}
    rendered = sum(m["_session"]["frames"] for m in manifests)
    if len(jobs) != 1 or None in jobs or rendered == 0:
        return None
    return {"job_type": jobs.pop(), "units": rendered, "work_s": round(sum(m["_session"]["seconds"] for m in manifests), 3)}


def render(argv_job: str, binary_path: str | None, out: Path, render_root: Path, *, vault=None, project=None,
           popen=subprocess.Popen, deadline: float | None = None) -> int:
    from explainer_engine.episode import retired
    retired.refuse("blender_scene", out)   # Q10, D-131: retired inside a v4.3 episode
    vault = vault or HFVault()
    out.mkdir(parents=True, exist_ok=True)
    tmp = render_root / "_pod"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        job = load_job(vault, argv_job, tmp)
        binary = (project or BlenderProject()).resolve(binary_path, device=job.get("device", "gpu"))
    except (ContractError, BlenderPinError) as e:
        _progress(out, f"refused: {e}")
        print(f"refused: {e}", flush=True)
        return RC_JOB
    jdir = render_root / job["job_id"]
    adapter = HeadlessRender(binary, vault, chunk_size=int(job.get("chunk_size", 8)), popen=popen)
    reserve = float(job.get("reserve_s", 600))
    manifests: list[dict] = []
    for k, shot in enumerate(job["shots"], 1):
        try:
            spec, scene = fetch_shot(vault, shot, tmp)
            left = None if deadline is None else deadline - time.time() - reserve
            if left is not None and left <= 0:
                raise RenderFailed("no time left before the pod's deadline")
            _progress(out, f"shot {k}/{len(job['shots'])} {spec['shot_id']} rendering")
            m = adapter.run(spec, jdir, scene=scene, max_seconds=left)
        except UploadFailed as e:
            _progress(out, f"UPLOAD FAILED: {e}")
            print(f"UPLOAD FAILED: {e}", flush=True)
            return RC_UPLOAD
        except (RenderFailed, ContractError) as e:
            _progress(out, f"RENDER FAILED: {e}")
            print(f"RENDER FAILED: {e}", flush=True)
            return RC_RENDER
        at_master = spec["frame"]["render_scale"] == 1.0 and (spec["frame"]["width"], spec["frame"]["height"]) == (2560, 1440)
        m["_job_type"] = P.get(m["profile"]).job_type() if at_master else None
        manifests.append(m)
        write_json_atomic(out / "manifests" / f"{spec['shot_id']}.json", {k2: v for k2, v in m.items() if not k2.startswith("_")})
        _progress(out, f"shot {k}/{len(job['shots'])} {spec['shot_id']} committed {m['frames_written']}/{m['frames_expected']}")
    line = units_line(manifests)
    if line:
        write_json_atomic(out / "units.json", line)
    bad = V.check_uploaded(jdir, f"blender/{job['job_id']}", vault.listing(f"blender/{job['job_id']}"))
    if bad:
        _progress(out, f"VAULT CHECK FAILED: {bad[:3]}")
        print("VAULT CHECK FAILED:\n" + "\n".join(bad), flush=True)
        return RC_CHECK
    _progress(out, f"all {len(manifests)} shots committed and on the vault")
    return 0


def bundle(out: Path, ref: str = "HEAD") -> str:
    """The code the pod runs: ``git archive`` of ``explainer_engine/`` and ``config/`` at ``ref`` (byte-stable for one commit). Its
    sha256 is written into ``blender_render.sh`` by the DRY gate before a pod; the file goes to the vault under ``code/blender_render/``."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tar = out.with_suffix("")
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", "-o", str(tar), ref, *BUNDLE_PATHS], check=True)
    subprocess.run(["gzip", "-n", "-9", "-f", str(tar)], check=True)
    if Path(str(tar) + ".gz") != out:
        os.replace(str(tar) + ".gz", out)
    return C.sha256_file(out)


def _opt(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["bundle"] and _opt(argv, "--out"):
        print(bundle(Path(_opt(argv, "--out")), _opt(argv, "--ref", "HEAD")))
        return 0
    if argv[:1] != ["render"] or not _opt(argv, "--job") or not _opt(argv, "--out"):
        print(__doc__)
        return 2
    dl = os.environ.get("EE_DEADLINE")
    return render(_opt(argv, "--job"), _opt(argv, "--binary"), Path(_opt(argv, "--out")),
                  Path(_opt(argv, "--render", "/workspace/render")), deadline=float(dl) if dl else None)


if __name__ == "__main__":
    sys.exit(main())
