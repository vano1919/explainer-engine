"""ICW-04 (roadmap section 11 and 10.4, OR-33): the headless Blender adapter against a fake ``blender`` on PATH and a folder vault.
Proves the argument order, exit-code propagation, the frame protocol (kill at frame N -> the resume renders only N..; a corrupted
remote frame is rendered again; a failed upload never reaches DONE; the checkpoint write is atomic) and the manifest contract.
No Blender, no network, no money."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from explainer_engine.blender import profiles as P
from explainer_engine.blender import render as R
from explainer_engine.blender.project import BlenderProject
from explainer_engine.core import contracts as C
from explainer_engine.core import store
from explainer_engine.core.errors import ContractError
from explainer_engine.core.shot_cache import ShotCache, key

FAKE = Path(__file__).resolve().parent / "_fake_blender.py"


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """Put the fake ``blender`` first on PATH; return (resolved binary, log reader)."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    if os.name == "nt":
        (bindir / "blender.cmd").write_text(f'@"{sys.executable}" "{FAKE}" %*\n', encoding="utf-8")
    else:
        sh = bindir / "blender"
        sh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n', encoding="utf-8")
        sh.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.delenv("EE_BLENDER", raising=False)
    logf = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_BLENDER_LOG", str(logf))
    for k in ("FAKE_BLENDER_DIE_AFTER", "FAKE_BLENDER_RC", "FAKE_BLENDER_BLACK", "FAKE_BLENDER_VERSION"):
        monkeypatch.delenv(k, raising=False)

    def calls():
        if not logf.exists():
            return []
        return [json.loads(ln) for ln in logf.read_text(encoding="utf-8").splitlines() if '"frames"' in ln]

    return BlenderProject().resolve(), calls


def _adapter(binary, vault, chunk=2):
    return R.HeadlessRender(binary, vault, chunk_size=chunk, poll_s=0.01)


def _smoke(frames=6):
    return R.smoke_spec(frames=frames)


def test_the_command_is_the_roadmaps_one_in_order(fake):
    binary, _ = fake
    cmd = R.HeadlessRender(binary, R.LocalVault("v")).command("job.json")
    assert cmd[1:7] == ["--background", "--factory-startup", "--python-exit-code", "1", "--python", str(R.SCRIPT)]
    assert cmd[7:] == ["--", "job.json"] and cmd[0] == binary.path
    assert R.SCRIPT.name == "render_shot.py" and R.SCRIPT.parent.name == "bpy"


def test_a_smoke_render_commits_every_frame_and_writes_a_valid_manifest(fake, tmp_path):
    binary, calls = fake
    vault = R.LocalVault(tmp_path / "vault")
    m = _adapter(binary, vault).run(_smoke(6), tmp_path / "work", smoke=P.SMOKE)
    assert m["frames_written"] == 6 and m["engine"] == "workbench" and m["profile"] == "eevee_fast"
    assert m["output"]["codec"] == "png" and (m["output"]["width"], m["output"]["height"]) == (320, 180)
    assert m["seconds_per_frame"] == pytest.approx(0.5) and m["blender"]["version"] == "5.2.3"
    assert calls()[0]["frames"] == list(range(6))
    job = json.loads((tmp_path / "work" / ".cache" / m["cache_key"] / "job.json").read_text(encoding="utf-8"))
    assert (job["width"], job["height"], job["percent"]) == (320, 180, 100)  # Blender's percentage is an integer: 12.5 -> 307x172
    sdir = tmp_path / "work" / m["cache_key"]
    ck = json.loads((sdir / "render_checkpoint.json").read_text(encoding="utf-8"))
    assert C.errors(ck) == [] and [f["state"] for f in ck["frames"]] == ["COMMITTED"] * 6
    findings = C.errors(json.loads((sdir / "render_manifest.json").read_text(encoding="utf-8")))
    assert not [f for f in findings if f["rule"] == "CN-01"]
    assert all(f["rule"] == "CN-17" and "master" in f["detail"] for f in findings)  # the declared smoke size, nothing else
    prefix = f"blender/smoke/{m['cache_key']}"
    from explainer_engine import vault as V
    assert V.check_uploaded(sdir, prefix, vault.listing(prefix)) == []  # VT-01: the mirrored folder is on the vault
    assert m["_session"] == {"frames": 6, "seconds": 3.0}


def test_a_kill_at_frame_n_keeps_the_committed_frames_and_the_resume_renders_only_the_rest(fake, tmp_path, monkeypatch):
    binary, calls = fake
    vault = R.LocalVault(tmp_path / "vault")
    monkeypatch.setenv("FAKE_BLENDER_DIE_AFTER", "5")
    with pytest.raises(R.RenderFailed, match="exited 137.*5/8 frames committed"):
        _adapter(binary, vault).run(_smoke(8), tmp_path / "pod1", smoke=P.SMOKE)
    monkeypatch.delenv("FAKE_BLENDER_DIE_AFTER")
    m = _adapter(binary, vault).run(_smoke(8), tmp_path / "pod2", smoke=P.SMOKE)  # a new pod: an empty disk, the same vault
    assert [c["frames"] for c in calls()] == [list(range(8)), [5, 6, 7]]
    assert m["frames_written"] == 8 and m["_session"]["frames"] == 3 and m["output"] is not None


def test_a_corrupted_remote_frame_is_rendered_again(fake, tmp_path):
    binary, calls = fake
    vault = R.LocalVault(tmp_path / "vault")
    m = _adapter(binary, vault).run(_smoke(6), tmp_path / "pod1", smoke=P.SMOKE)
    bad = tmp_path / "vault" / f"blender/smoke/{m['cache_key']}/frames/frame_000003.png"
    bad.write_bytes(b"not the frame")
    _adapter(binary, vault).run(_smoke(6), tmp_path / "pod2", smoke=P.SMOKE)
    assert calls()[-1]["frames"] == [3]
    assert R.check_png(bad, 320, 180) is None  # the vault holds the good frame again


def test_a_frame_only_on_the_pods_disk_does_not_count(fake, tmp_path):
    """Rule 2: only COMMITTED frames count; a lost remote checkpoint means everything is rendered again."""
    binary, calls = fake
    vault = R.LocalVault(tmp_path / "vault")
    m = _adapter(binary, vault).run(_smoke(4), tmp_path / "work", smoke=P.SMOKE)
    (tmp_path / "vault" / f"blender/smoke/{m['cache_key']}/render_checkpoint.json").unlink()
    _adapter(binary, vault).run(_smoke(4), tmp_path / "work", smoke=P.SMOKE)
    assert calls()[-1]["frames"] == [0, 1, 2, 3]


class _BrokenVault(R.LocalVault):
    """Uploads succeed, but the vault lists a different hash for every frame (a silent corruption)."""

    def listing(self, prefix):
        out = super().listing(prefix)
        return {k: dict(v, sha256="f" * 64) if "/frames/" in k else v for k, v in out.items()}


class _DeadVault(R.LocalVault):
    def upload_many(self, pairs, message=""):
        raise OSError("503 from the hub")


@pytest.mark.parametrize("vault_cls,match", [(_BrokenVault, "not on the vault"), (_DeadVault, "upload failed")])
def test_a_failed_upload_or_verify_raises_and_no_frame_is_committed(fake, tmp_path, vault_cls, match):
    binary, _ = fake
    vault = vault_cls(tmp_path / "vault")
    with pytest.raises(R.UploadFailed, match=match):
        _adapter(binary, vault).run(_smoke(4), tmp_path / "work", smoke=P.SMOKE)
    k = key(_smoke(4))
    ck = json.loads((tmp_path / "work" / k / "render_checkpoint.json").read_text(encoding="utf-8"))
    assert C.errors(ck) == [] and "COMMITTED" not in {f["state"] for f in ck["frames"]}
    assert not (tmp_path / "vault" / f"blender/smoke/{k}/render_checkpoint.json").exists()


def test_a_failed_upload_ends_the_pod_non_zero_so_the_wrapper_never_writes_done(fake, tmp_path):
    from explainer_engine.training.pods import blender_render as POD
    vault = _DeadVault(tmp_path / "vault")
    spec, job = _pod_job(tmp_path / "vault")
    rc = POD.render("blender/job-001/pod_job.json", None, tmp_path / "out", tmp_path / "render", vault=vault)
    assert rc == POD.RC_UPLOAD
    assert "UPLOAD FAILED" in (tmp_path / "out" / "progress.txt").read_text(encoding="utf-8")
    assert not (tmp_path / "out" / "units.json").exists()


def test_the_checkpoint_write_is_atomic(fake, tmp_path, monkeypatch):
    """A crash during a checkpoint write leaves the previous checkpoint whole (write_json_atomic: temp file, then replace)."""
    ck = R.Checkpoint.new("job-001", "a" * 64, "b" * 64, 4, 2)
    path = tmp_path / "render_checkpoint.json"
    ck.save(path)
    before = path.read_bytes()
    ck.frames[0] = {"index": 0, "state": "RENDERED", "file": "frame_000000.png", "local_sha256": "c" * 64, "remote_sha256": None,
                    "stored_at": None}

    def crash(tmp, target, attempts=20):
        raise OSError("power cut")

    monkeypatch.setattr(store, "replace_file", crash)
    with pytest.raises(OSError):
        ck.save(path)
    assert path.read_bytes() == before and C.errors(json.loads(before)) == []


def test_an_invalid_checkpoint_is_never_written(tmp_path):
    ck = R.Checkpoint.new("job-001", "a" * 64, "b" * 64, 2, 2)
    ck.frames[5] = {"index": 5, "state": "RENDERED", "file": "frame_000005.png", "local_sha256": "c" * 64, "remote_sha256": None,
                    "stored_at": None}
    with pytest.raises(ContractError, match="CN-18"):
        ck.save(tmp_path / "ck.json")
    assert not (tmp_path / "ck.json").exists()


def test_a_non_zero_exit_after_all_frames_fails_the_shot_but_keeps_the_frames(fake, tmp_path, monkeypatch):
    binary, _ = fake
    monkeypatch.setenv("FAKE_BLENDER_RC", "1")
    vault = R.LocalVault(tmp_path / "vault")
    with pytest.raises(R.RenderFailed, match="exited 1"):
        _adapter(binary, vault).run(_smoke(4), tmp_path / "work", smoke=P.SMOKE)
    m = json.loads((tmp_path / "work" / key(_smoke(4)) / "render_manifest.json").read_text(encoding="utf-8"))
    assert m["frames_written"] == 4 and m["output"] is None and m["finished_at"] is None


def test_a_black_frame_fails_its_check_unless_the_job_allows_it(fake, tmp_path, monkeypatch):
    binary, _ = fake
    monkeypatch.setenv("FAKE_BLENDER_BLACK", "2")
    with pytest.raises(R.RenderFailed, match="frame 2 failed the local check: all black"):
        _adapter(binary, R.LocalVault(tmp_path / "v1")).run(_smoke(4), tmp_path / "w1", smoke=P.SMOKE)
    m = _adapter(binary, R.LocalVault(tmp_path / "v2")).run(_smoke(4), tmp_path / "w2", smoke=P.SMOKE, allow_black=True)
    assert m["frames_written"] == 4


def test_the_pinned_version_is_enforced(fake, monkeypatch):
    from explainer_engine.blender.project import BlenderPinError
    monkeypatch.setenv("FAKE_BLENDER_VERSION", "5.3.0")
    with pytest.raises(BlenderPinError, match="not the pinned 5.2.3"):
        BlenderProject().resolve()


def test_check_png_finds_cut_wrong_size_and_black_frames(tmp_path):
    sys.path.insert(0, str(FAKE.parent))
    import _fake_blender as F
    good = tmp_path / "g.png"
    good.write_bytes(F.png(32, 18, (10, 20, 30)))
    assert R.check_png(good, 32, 18) is None
    assert "expected 64x36" in R.check_png(good, 64, 36)
    cut = tmp_path / "c.png"
    cut.write_bytes(good.read_bytes()[:-20])
    assert R.check_png(cut, 32, 18) is not None
    blk = tmp_path / "b.png"
    blk.write_bytes(F.png(32, 18, (0, 0, 0)))
    assert "black" in R.check_png(blk, 32, 18) and R.check_png(blk, 32, 18, allow_black=True) is None


def _pod_job(vroot: Path, frames: int = 3):
    """A production-size shot (2560x1440 master, eevee_full) with its scene file and pod job on a folder vault."""
    spec = json.loads((Path(__file__).resolve().parents[1] / "fixtures/contracts/shot_spec/valid_v2.json").read_text(encoding="utf-8"))
    spec["clock"]["frames"] = frames
    spec["render"]["output"] = "png_seq"
    (vroot / "blender/job-001/specs").mkdir(parents=True, exist_ok=True)
    (vroot / "blender/job-001/specs/s1.json").write_text(json.dumps(spec), encoding="utf-8")
    (vroot / "blender/job-001/scenes").mkdir(parents=True, exist_ok=True)
    blend = vroot / "blender/job-001/scenes/s1.blend"
    blend.write_bytes(b"BLENDER-v502 stand-in")
    job = {"job": "blender_pod_job/1", "job_id": "job-001", "device": "cpu", "chunk_size": 2,
           "shots": [{"spec": "blender/job-001/specs/s1.json",
                      "scene": {"path": "blender/job-001/scenes/s1.blend", "sha256": C.sha256_file(blend)}}]}
    (vroot / "blender/job-001/pod_job.json").write_text(json.dumps(job), encoding="utf-8")
    return spec, job


def test_the_pod_renders_a_master_shot_writes_units_and_proves_the_vault(fake, tmp_path):
    from explainer_engine.training.pods import blender_render as POD
    vault = R.LocalVault(tmp_path / "vault")
    spec, _ = _pod_job(tmp_path / "vault")
    rc = POD.render("blender/job-001/pod_job.json", None, tmp_path / "out", tmp_path / "render", vault=vault)
    assert rc == 0, (tmp_path / "out" / "progress.txt").read_text(encoding="utf-8")
    units = json.loads((tmp_path / "out" / "units.json").read_text(encoding="utf-8"))
    assert units == {"job_type": "blender_frame_eevee_full_1440", "units": 3, "work_s": 1.5}
    man = json.loads((tmp_path / "out" / "manifests" / "s1.json").read_text(encoding="utf-8"))
    assert C.errors(man) == [] and man["output"]["width"] == 2560 and man["engine"] == "eevee"


def test_a_production_shot_enters_the_shot_cache_only_when_complete(fake, tmp_path):
    binary, _ = fake
    vault = R.LocalVault(tmp_path / "vault")
    spec, job = _pod_job(tmp_path / "vault", frames=2)
    scene = {"kind": "blend", "path": str(tmp_path / "vault" / job["shots"][0]["scene"]["path"]), "sha256": job["shots"][0]["scene"]["sha256"]}
    cache = ShotCache(tmp_path / "cache")
    m = _adapter(binary, vault).run(spec, tmp_path / "work", scene=scene, cache=cache)
    assert C.errors({k: v for k, v in m.items() if not k.startswith("_")}) == []
    assert cache.get(spec) is not None


def test_a_production_shot_needs_its_scene_and_a_matching_scene_hash(fake, tmp_path):
    binary, _ = fake
    vault = R.LocalVault(tmp_path / "vault")
    spec, job = _pod_job(tmp_path / "vault", frames=2)
    with pytest.raises(ContractError, match="no scene"):
        _adapter(binary, vault).run(spec, tmp_path / "work")
    scene = {"kind": "blend", "path": str(tmp_path / "vault" / job["shots"][0]["scene"]["path"]), "sha256": "0" * 64}
    with pytest.raises(ContractError, match="sha256 differs"):
        _adapter(binary, vault).run(spec, tmp_path / "work", scene=scene)


def test_chunk_size_is_held_to_the_checkpoint_contract():
    with pytest.raises(ValueError):
        R.HeadlessRender(None, None, chunk_size=9)


def test_profiles_match_the_contract_recipes_and_job_speed_rows():
    rows = json.loads((Path(__file__).resolve().parents[2] / "config/job_speeds.json").read_text(encoding="utf-8"))["jobs"]
    for name, prof in P.PROFILES.items():
        assert C.BLENDER_RECIPES[name] == prof.recipe and prof.job_type() in rows
    assert P.get("eevee_full").max_s_per_frame_1440 == 10.0       # roadmap 12.4 rule 5
    assert (P.SMOKE.engine, P.SMOKE.frames, P.SMOKE.width, P.SMOKE.height) == ("workbench", 8, 320, 180)
    assert round(2560 * P.SMOKE.percent / 100) == 320 and round(1440 * P.SMOKE.percent / 100) == 180
    assert C.errors(R.smoke_spec()) == []


def test_only_the_bpy_script_imports_bpy():
    root = Path(__file__).resolve().parents[2] / "explainer_engine"
    hits = [p.relative_to(root).as_posix() for p in root.rglob("*.py") if "import bpy" in p.read_text(encoding="utf-8")]
    assert sorted(hits) == ["blender/bpy/assemble_25d.py", "blender/bpy/check_eevee_api.py", "blender/bpy/crowd_bake.py", "blender/bpy/make_rain_lead.py",
                    "blender/bpy/measure_clips.py",
                    "blender/bpy/render_shot.py"]  # the Blender-side scripts, nothing else
    text = R.SCRIPT.read_text(encoding="utf-8")
    assert "progress" in text and "os.replace" in text and "fsync" in text and "pin_version" in text


# ---- WP-Q0: Blender 5.x API names in bpy/render_shot.py (apply_settings, set_engine) ----------------------------------------------

def _load_render_shot():
    from pathlib import Path
    src = (Path(R.SCRIPT)).read_text(encoding="utf-8")
    src = src.replace("import bpy  #", "bpy = None  #").replace("from mathutils import Vector  #", "Vector = None  #")
    ns = {"__name__": "render_shot_under_test"}
    exec(compile(src.rstrip()[:-len("main()")], "render_shot.py", "exec"), ns)  # noqa: S102  (our own file, without its main())
    return ns


class _Strict:
    """An object that knows only the attributes it was given, as Blender's RNA: setting an unknown one is a missing switch."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_the_first_eevee_engine_id_tried_is_blender_eevee():
    rs = _load_render_shot()
    assert rs["ENGINE_IDS"]["eevee"] == ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT")
    tried = []

    class Render:
        @property
        def engine(self):
            return tried[-1]

        @engine.setter
        def engine(self, v):
            tried.append(v)

    assert rs["set_engine"](_Strict(render=Render()), "eevee") == "BLENDER_EEVEE"
    assert tried == ["BLENDER_EEVEE"]


def _apply(ao):
    rs = _load_render_shot()
    ee = _Strict(taa_render_samples=0, use_raytracing=False, use_fast_gi=False, fast_gi_method="GLOBAL_ILLUMINATION")
    scene = _Strict(render=_Strict(engine="", use_motion_blur=False), eevee=ee)
    job = {"engine": "eevee", "settings": {"samples": 64, "raytracing": True, "ambient_occlusion": ao}}
    applied, missing = rs["apply_settings"](scene, job)
    return ee, applied, missing


def test_eevee_full_ambient_occlusion_is_fast_gi_ao_only_and_not_use_gtao():
    ee, applied, missing = _apply(P.get("eevee_full").ambient_occlusion)
    assert P.get("eevee_full").ambient_occlusion is True
    assert ee.use_fast_gi is True and ee.fast_gi_method == "AMBIENT_OCCLUSION_ONLY"
    assert applied["eevee.use_fast_gi"] is True and applied["eevee.fast_gi_method"] == "AMBIENT_OCCLUSION_ONLY"
    assert applied["engine_id"] == "BLENDER_EEVEE"
    assert missing == [] and not hasattr(ee, "use_gtao") and "eevee.use_gtao" not in applied


def test_ambient_occlusion_none_sets_nothing_and_false_switches_fast_gi_off():
    ee, applied, missing = _apply(None)
    assert ee.use_fast_gi is False and "eevee.use_fast_gi" not in applied and missing == []
    ee, applied, missing = _apply(False)
    assert applied["eevee.use_fast_gi"] is False and "eevee.fast_gi_method" not in applied and missing == []
