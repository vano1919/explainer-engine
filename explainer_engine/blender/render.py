"""The headless Blender adapter with frame-level durable recovery (roadmap section 11 and 10.4; OR-03, OR-33, D-96).

    python -m explainer_engine.blender.render smoke --out D [--binary B] [--vault-dir V]   # the CI smoke of roadmap 12.4 step 1

``HeadlessRender.run(spec, work)`` renders one ``shot_spec/2`` on the pinned binary (``project.BlenderProject.resolve``):

    blender --background --factory-startup --python-exit-code 1 --python bpy/render_shot.py -- <job.json>

and holds every frame to the three states of ``render_checkpoint/1``. ``RENDERED``: the PNG is in place and passed the local check
(a complete PNG, the expected size, the expected index, not all black unless the job allows it). ``DURABLY_STORED``: the frame is
uploaded to ``blender/<job_id>/<shot_key>/frames/`` and the vault lists it with the same sha256. ``COMMITTED``: the checkpoint that
lists it was written atomically and is itself verified on the vault. Frames are committed in chunks of at most ``chunk_size`` (8)
while Blender keeps rendering. Rules of 10.4, as code:

1. a run first reads the REMOTE checkpoint, verifies each COMMITTED frame's remote hash and renders only the missing or mismatching
   frames (a frame that is only local, or only RENDERED, is rendered again);
2. a stop (kill, crash, cap, failed check) first commits what is good, then raises: paid frames are kept;
3. the clip (``mkv_ffv1``, or the ``png_seq`` list) is built only when every frame is COMMITTED; it is probed, hashed, uploaded and
   verified, and only then the spec enters the shot cache;
4. a failed upload or verify raises ``UploadFailed``: the pod script exits non-zero, so the wrapper never sends DONE (VT-02).

The work folder of a shot mirrors the vault: ``<work>/<shot_key>/`` holds exactly what is uploaded (frames, checkpoint, frame times,
log, spec, clip, render manifest), so ``python -m explainer_engine.vault check-uploaded <work> --to blender/<job_id>`` proves all of
it (VT-01). Transient files (the job file, the progress lines) live in ``<work>/.cache/<shot_key>/``, which that check skips.

The smoke renders an 8-frame ``shot_spec/2`` of the 2560x1440 master with the Workbench engine at 12.5 % (320x180, ``SMOKE``). Its
render manifest names engine ``workbench`` and the real 320x180 output, so CN-17's master-size FAIL on it is expected and is the
only finding the smoke accepts (a ``render_scale``-aware CN-18 is proposed to ICW-07); a smoke row never enters job_speeds or the
shot cache.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

from explainer_engine import vault as V
from explainer_engine.blender import profiles as P
from explainer_engine.blender.project import BlenderBinary, BlenderProject
from explainer_engine.core import contracts as C
from explainer_engine.core import shot_cache
from explainer_engine.core.errors import ContractError, EngineError
from explainer_engine.core.store import write_json_atomic

SCRIPT = Path(__file__).resolve().parent / "bpy" / "render_shot.py"
FRAME_NAME = "frame_{index:06d}.png"
CHUNK_MAX = 8  # render_checkpoint/1: at most 8 frames per uploaded chunk (roadmap 10.4)
PNG_SIG = b"\x89PNG\r\n\x1a\n"


class RenderFailed(EngineError):
    """Blender exited non-zero, a frame failed its check, or a cap stopped the render (committed frames are kept)."""


class UploadFailed(EngineError):
    """A frame, the checkpoint or the clip is not on the vault with the same hash: never DONE (VT-02)."""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- the vault the frames go to ----------------------------------------------------------------------------------------------

class LocalVault:
    """A folder standing in for the vault (the CI smoke, the tests). Same interface as ``HFVault``."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def listing(self, prefix: str) -> dict:
        base, out = self.root / prefix, {}
        if base.exists():
            for p in base.rglob("*"):
                if p.is_file():
                    sha, blob, size = V.file_hashes(p)
                    out[p.relative_to(self.root).as_posix()] = {"size": size, "sha256": sha, "blob": blob}
        return out

    def upload_many(self, pairs: list[tuple[Path, str]], message: str = "") -> None:
        for local, remote in pairs:
            dst = self.root / remote
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local, dst)

    def download(self, remote: str, local: Path) -> bool:
        src = self.root / remote
        if not src.is_file():
            return False
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, local)
        return True


class HFVault:
    """The creator's Hugging Face dataset (``config/vault.json`` primary). One commit per chunk (``upload_many``); hashes are read
    from the tree API without downloading (``vault.remote_files``). huggingface_hub is imported only on the pod."""

    def __init__(self, repo: str | None = None) -> None:
        self.repo = repo or V.config()["primary"]
        self.kind, self.rid = V._split(self.repo)

    def listing(self, prefix: str) -> dict:
        return V.remote_files(self.repo, prefix)

    def upload_many(self, pairs: list[tuple[Path, str]], message: str = "") -> None:
        from huggingface_hub import CommitOperationAdd, HfApi
        ops = [CommitOperationAdd(path_in_repo=remote, path_or_fileobj=str(local)) for local, remote in pairs]
        HfApi().create_commit(repo_id=self.rid, repo_type=self.kind[:-1], operations=ops, commit_message=message or "blender frames")

    def download(self, remote: str, local: Path) -> bool:
        url = f"{V.HUB}/{self.kind}/{self.rid}/resolve/main/{remote}"
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        try:
            V._download(url, V.token(), local)
        except Exception as e:  # noqa: BLE001  (a 404 is "not there"; the caller decides what that means)
            if "404" in str(e):
                return False
            raise
        return True


def _remote_has(vault, meta: dict | None, sha: str, remote: str, tmp: Path) -> bool:
    """The vault holds ``remote`` with sha256 ``sha``: from the listed LFS sha256, else by downloading and hashing it."""
    if meta is None:
        return False
    if meta.get("sha256"):
        return meta["sha256"] == sha
    probe = tmp / ("probe_" + remote.replace("/", "_"))
    if not vault.download(remote, probe):
        return False
    ok = C.sha256_file(probe) == sha
    probe.unlink(missing_ok=True)
    return ok


# --- the local frame check (RENDERED) -----------------------------------------------------------------------------------------

def check_png(path: Path | str, width: int, height: int, *, allow_black: bool = False) -> str | None:
    """None when ``path`` is a complete 8-bit RGB/RGBA PNG of ``width`` x ``height`` that is not all black; else the reason. stdlib
    only (zlib): a pod needs no Pillow. All-zero filtered rows are exactly an all-zero image, so the black test needs no unfiltering."""
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        return f"unreadable ({e})"
    if not data.startswith(PNG_SIG):
        return "not a PNG"
    pos, idat, w, h = 8, [], None, None
    depth = ctype = None
    seen_end = False
    while pos + 8 <= len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        crc = data[pos + 8 + n:pos + 12 + n]
        if len(body) != n or len(crc) != 4 or zlib.crc32(kind + body) & 0xFFFFFFFF != struct.unpack(">I", crc)[0]:
            return f"chunk {kind!r} is cut or its CRC is wrong"
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            seen_end = True
            break
        pos += 12 + n
    if not seen_end or w is None or not idat:
        return "incomplete PNG (no IHDR, IDAT or IEND)"
    if (w, h) != (width, height):
        return f"{w}x{h}, expected {width}x{height}"
    if depth != 8 or ctype not in (2, 6):
        return f"bit depth {depth} colour type {ctype}: expected 8-bit RGB or RGBA"
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as e:
        return f"image data does not decode ({e})"
    stride = 1 + w * (3 if ctype == 2 else 4)
    if len(raw) != stride * h:
        return f"image data is {len(raw)} bytes, expected {stride * h}"
    if not allow_black:
        if ctype == 2:
            lit = any(raw[r * stride + 1:(r + 1) * stride].count(0) != stride - 1 for r in range(h))
        else:  # RGBA: alpha does not count as light
            lit = any(any(raw[r * stride + 1 + i:(r + 1) * stride:4].count(0) != w for i in range(3)) for r in range(h))
        if not lit:
            return "all black (not declared)"
    return None


# --- the checkpoint (render_checkpoint/1) --------------------------------------------------------------------------------------

class Checkpoint:
    def __init__(self, doc: dict) -> None:
        self.doc = doc
        self.frames = {f["index"]: f for f in doc["frames"]}

    @classmethod
    def new(cls, job_id: str, shot_key: str, spec_sha256: str, frames_expected: int, chunk_size: int) -> "Checkpoint":
        return cls({"schema": "render_checkpoint/1", "job_id": job_id, "shot_key": shot_key, "spec_sha256": spec_sha256,
                    "frames_expected": frames_expected, "chunk_size": chunk_size,
                    "vault_prefix": f"blender/{job_id}/{shot_key}/frames/", "frames": [], "updated_at": now()})

    def to_doc(self) -> dict:
        doc = dict(self.doc, frames=[self.frames[i] for i in sorted(self.frames)], updated_at=now())
        bad = [f for f in C.errors(doc) if f["severity"] == "FAIL"]
        if bad:
            raise ContractError("render_checkpoint/1: " + "; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
        return doc

    def save(self, path: Path) -> dict:
        doc = self.to_doc()
        write_json_atomic(path, doc)
        return doc

    def committed(self) -> list[int]:
        return sorted(i for i, f in self.frames.items() if f["state"] == "COMMITTED")


# --- the adapter ----------------------------------------------------------------------------------------------------------------

class HeadlessRender:
    """One shot spec -> frames on the vault -> clip -> ``blender_render_manifest/1``. ``popen`` and ``sleep`` are injectable for
    the fake-Blender tests; everything else is the production path."""

    def __init__(self, binary: BlenderBinary, vault, *, chunk_size: int = CHUNK_MAX, poll_s: float = 1.0,
                 popen=subprocess.Popen, sleep=time.sleep, clock=time.monotonic, script: Path | str = SCRIPT) -> None:
        if not 1 <= chunk_size <= CHUNK_MAX:
            raise ValueError(f"chunk_size {chunk_size} is outside 1..{CHUNK_MAX} (render_checkpoint/1)")
        self.binary, self.vault, self.chunk_size, self.poll_s = binary, vault, chunk_size, poll_s
        self.popen, self.sleep, self.clock, self.script = popen, sleep, clock, str(script)

    def command(self, job_path: Path | str) -> list[str]:
        """The one Blender command line of the roadmap (section 11): factory settings, no UI, a Python error is a non-zero exit."""
        return [self.binary.path, "--background", "--factory-startup", "--python-exit-code", "1",
                "--python", self.script, "--", str(job_path)]

    # -- resume (rule 1) --
    def _resume(self, ck: Checkpoint, prefix: str, sdir: Path, tdir: Path) -> Checkpoint:
        remote_ck = tdir / "remote_checkpoint.json"
        remote_ck.unlink(missing_ok=True)
        if not self.vault.download(prefix + "render_checkpoint.json", remote_ck):
            return ck
        doc = json.loads(remote_ck.read_text(encoding="utf-8"))
        C.validate(doc)
        if (doc["shot_key"], doc["frames_expected"]) != (ck.doc["shot_key"], ck.doc["frames_expected"]):
            raise ContractError("the vault's checkpoint is another shot's (shot_key or frame count differs)")
        listed = self.vault.listing(doc["vault_prefix"])
        keep = {}
        for fr in doc["frames"]:
            if fr["state"] != "COMMITTED":
                continue
            remote = doc["vault_prefix"] + fr["file"]
            if not _remote_has(self.vault, listed.get(remote), fr["remote_sha256"], remote, tdir):
                continue  # missing or corrupted on the vault: render it again
            local = sdir / "frames" / fr["file"]
            if not local.is_file() or C.sha256_file(local) != fr["local_sha256"]:
                if not self.vault.download(remote, local) or C.sha256_file(local) != fr["local_sha256"]:
                    continue
            keep[fr["index"]] = fr
        ck.frames = keep
        return ck

    # -- commit a chunk (DURABLY_STORED -> COMMITTED) --
    def _commit(self, ck: Checkpoint, idxs: list[int], sdir: Path, tdir: Path, prefix: str, times: dict) -> None:
        if not idxs:
            return
        pairs = [(sdir / "frames" / ck.frames[i]["file"], ck.doc["vault_prefix"] + ck.frames[i]["file"]) for i in idxs]
        try:
            self.vault.upload_many(pairs, f"blender {ck.doc['shot_key'][:12]} frames {idxs[0]}-{idxs[-1]}")
            listed = self.vault.listing(ck.doc["vault_prefix"])
        except Exception as e:  # noqa: BLE001
            ck.save(sdir / "render_checkpoint.json")
            raise UploadFailed(f"frames {idxs[0]}-{idxs[-1]}: upload failed ({e})") from e
        stamp = now()
        for (local, remote), i in zip(pairs, idxs):
            if not _remote_has(self.vault, listed.get(remote), ck.frames[i]["local_sha256"], remote, tdir):
                ck.save(sdir / "render_checkpoint.json")
                raise UploadFailed(f"frame {i}: {remote} is not on the vault with sha256 {ck.frames[i]['local_sha256'][:12]}")
            ck.frames[i].update(state="DURABLY_STORED", remote_sha256=ck.frames[i]["local_sha256"], stored_at=stamp)
        ck.save(sdir / "render_checkpoint.json")
        for i in idxs:
            ck.frames[i]["state"] = "COMMITTED"
        ck_path, times_path = sdir / "render_checkpoint.json", sdir / "render_times.json"
        ck.save(ck_path)
        write_json_atomic(times_path, {str(k): v for k, v in sorted(times.items())})

        def back_to_stored():  # the vault's checkpoint does not list them: locally they are stored, not committed
            for i in idxs:
                ck.frames[i]["state"] = "DURABLY_STORED"
            ck.save(ck_path)

        self._put_verified([(ck_path, prefix + "render_checkpoint.json"), (times_path, prefix + "render_times.json")], prefix, tdir,
                           on_fail=back_to_stored)

    def _put_verified(self, pairs, prefix: str, tdir: Path, on_fail=None) -> None:
        try:
            self.vault.upload_many(pairs, "blender " + ", ".join(Path(r).name for _, r in pairs))
            listed = self.vault.listing(prefix)
        except Exception as e:  # noqa: BLE001
            if on_fail:
                on_fail()
            raise UploadFailed(f"upload of {', '.join(r for _, r in pairs)} failed ({e})") from e
        for local, remote in pairs:
            if not _remote_has(self.vault, listed.get(remote), C.sha256_file(local), remote, tdir):
                if on_fail:
                    on_fail()
                raise UploadFailed(f"{remote} is not on the vault with the local sha256")

    def run(self, spec: dict, work: Path | str, *, smoke: P.SmokeOverride | None = None, scene: dict | None = None,
            allow_black: bool = False, max_seconds: float | None = None, cache: shot_cache.ShotCache | None = None) -> dict:
        """Render ``spec`` (shot_spec/2) under ``work``; returns the render manifest (validated: schema, CN-18). ``scene`` is the
        scene to open (``{"kind": "blend", "path", "sha256"}``, written by the scene builder of ICW-06); the smoke builds its own."""
        if spec.get("schema") != "shot_spec/2":
            raise ContractError("HeadlessRender renders shot_spec/2 only (Blender lanes, D-96)")
        C.validate(spec)
        if scene is None and smoke is None:
            raise ContractError("no scene: a production shot opens the .blend of its scene builder (ICW-06)")
        if scene is not None and scene.get("kind") == "blend" and C.sha256_file(scene["path"]) != scene["sha256"]:
            raise ContractError(f"{scene['path']}: sha256 differs from the scene the job names")
        key = shot_cache.key(spec)
        job_id, sid = spec["job_id"], spec["shot_id"]
        prefix = f"blender/{job_id}/{key}/"
        sdir, tdir = Path(work) / key, Path(work) / ".cache" / key  # vault check-uploaded skips .cache (transient files)
        (sdir / "frames").mkdir(parents=True, exist_ok=True)
        tdir.mkdir(parents=True, exist_ok=True)
        spec_path = sdir / "spec.json"
        write_json_atomic(spec_path, spec)
        prof = P.get(spec["render"]["profile"])
        engine = smoke.engine if smoke else prof.engine
        percent = smoke.percent if smoke else spec["frame"]["render_scale"] * 100
        width, height = spec["frame"]["width"], spec["frame"]["height"]
        out_w, out_h = round(width * percent / 100), round(height * percent / 100)
        n, fps = spec["clock"]["frames"], spec["clock"]["fps"]
        started = now()
        ck = Checkpoint.new(job_id, key, C.sha256_file(spec_path), n, self.chunk_size)
        ck = self._resume(ck, prefix, sdir, tdir)
        times_file = tdir / "remote_times.json"
        times: dict[int, float] = {}
        if ck.frames and self.vault.download(prefix + "render_times.json", times_file):
            times = {int(k): float(v) for k, v in json.loads(times_file.read_text(encoding="utf-8")).items() if int(k) in ck.frames}
        todo = [i for i in range(n) if i not in ck.frames or ck.frames[i]["state"] != "COMMITTED"]
        for i in todo:
            ck.frames.pop(i, None)
        log_path = sdir / "blender.log"
        report: dict = {}
        failure: str | None = None
        if todo:
            report, failure = self._render(spec, ck, todo, sdir, tdir, prefix, times, engine, width, height, percent, out_w, out_h,
                                           fps, smoke, scene, allow_black, max_seconds, prof, log_path)
        committed = ck.committed()
        output = None
        if failure is None and len(committed) == n:
            output = self._clip(spec, sdir, tdir, prefix, out_w, out_h, fps, n)
        if not log_path.exists():
            log_path.write_text("", encoding="utf-8")
        known = [times[i] for i in committed if i in times]
        total = sum(known) * len(committed) / len(known) if known else 0.0
        manifest = {
            "schema": "blender_render_manifest/1", "job_id": job_id, "shot_id": sid,
            "spec": {"path": "spec.json", "sha256": C.sha256_file(spec_path)}, "cache_key": key,
            "blender": {"version": self.binary.version, "build_hash": report.get("build_hash") or self.binary.build_hash},
            "engine": engine, "device": self.binary.device, "gpu": self.binary.gpu, "profile": prof.name,
            "frames_expected": n, "frames_written": len(committed), "seconds_total": round(total, 4),
            "seconds_per_frame": round(total / len(committed), 4) if committed else None, "output": output,
            "log": {"path": "blender.log", "sha256": C.sha256_file(log_path)}, "started_at": started,
            "finished_at": now() if output is not None else None,
        }
        findings = C.errors(manifest)
        allowed = [f for f in findings if smoke is not None and f["rule"] == "CN-17" and "master" in f["detail"]]
        blocking = [f for f in findings if f["severity"] == "FAIL" and f not in allowed]
        write_json_atomic(sdir / "render_manifest.json", manifest)
        record = [log_path, spec_path, sdir / "render_manifest.json"] + ([sdir / "bpy_report.json"] if (sdir / "bpy_report.json").exists() else [])
        self._put_verified([(f, prefix + f.name) for f in record], prefix, tdir)
        if failure is not None:
            raise RenderFailed(f"{sid}: {failure} ({len(committed)}/{n} frames committed and kept)")
        if blocking:
            raise ContractError("blender_render_manifest/1: " + "; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in blocking))
        if cache is not None and smoke is None and output is not None:
            cache.put(spec, {"clip": sdir / output["path"]}, job_id=job_id)
        fresh = [i for i in todo if i in committed]
        manifest["_findings"] = findings
        manifest["_session"] = {"frames": len(fresh), "seconds": round(sum(times.get(i, 0.0) for i in fresh), 4)}
        return manifest

    def _render(self, spec, ck, todo, sdir, tdir, prefix, times, engine, width, height, percent, out_w, out_h, fps, smoke, scene,
                allow_black, max_seconds, prof, log_path):
        progress = tdir / "progress.jsonl"
        progress.unlink(missing_ok=True)
        report_path = tdir / "bpy_report.json"
        report_path.unlink(missing_ok=True)
        job = {"job": "render_shot/1", "pin_version": self.binary.version, "shot_id": spec["shot_id"], "frames": todo,
               "frame_start": 1, "fps": fps, "width": width, "height": height, "percent": percent, "engine": engine,
               "device": self.binary.device, "settings": prof.settings(spec["render"]), "seed": spec["seed"],
               "scene": scene or {"kind": "smoke", "frames_total": spec["clock"]["frames"]},
               "frames_dir": str(sdir / "frames"), "frame_name": FRAME_NAME, "progress": str(progress), "report": str(report_path)}
        job_path = tdir / "job.json"
        write_json_atomic(job_path, job)
        want = set(todo)
        pending: list[int] = []
        failure = None
        t0 = self.clock()
        budget = prof.max_s_per_frame_1440 if (smoke is None and percent == 100 and (width, height) == (2560, 1440)) else None
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"=== {now()} {' '.join(self.command(job_path))}\n")
            log.flush()
            proc = self.popen(self.command(job_path), stdout=log, stderr=subprocess.STDOUT)
            offset = 0
            while True:
                rc = proc.poll()
                lines, offset = _new_lines(progress, offset)
                for rec in lines:
                    i = rec.get("index")
                    if i not in want:
                        failure = failure or f"Blender reported frame {i}, which the job did not ask for"
                        continue
                    if rec.get("file") != FRAME_NAME.format(index=i):
                        failure = failure or f"frame {i} was written as {rec.get('file')!r}"
                        continue
                    f = sdir / "frames" / rec["file"]
                    bad = check_png(f, out_w, out_h, allow_black=allow_black)
                    if bad:
                        failure = failure or f"frame {i} failed the local check: {bad}"
                        continue
                    ck.frames[i] = {"index": i, "state": "RENDERED", "file": rec["file"], "local_sha256": C.sha256_file(f),
                                    "remote_sha256": None, "stored_at": None}
                    times[i] = float(rec.get("seconds") or 0.0)
                    want.discard(i)
                    pending.append(i)
                if pending and (len(pending) >= self.chunk_size or rc is not None or failure):
                    ck.save(sdir / "render_checkpoint.json")
                    self._commit(ck, pending, sdir, tdir, prefix, times)
                    pending = []
                if rc is not None:
                    break
                elapsed = self.clock() - t0
                done = len(todo) - len(want)
                if failure is None and max_seconds is not None and elapsed > max_seconds:
                    failure = f"wall-clock cap {max_seconds:g} s reached"
                if failure is None and budget is not None and done and sum(times[i] for i in todo if i in times) / done > budget:
                    failure = f"{prof.name} is slower than {budget:g} s/frame at 1440p (roadmap 12.4 rule 5)"
                if failure is not None:
                    _stop(proc)
                    continue  # one more pass commits whatever finished before the stop
                self.sleep(self.poll_s)
        if failure is None and rc != 0:
            failure = f"Blender exited {rc}"
        if failure is None and want:
            failure = f"Blender exited 0 but {len(want)} frames are missing ({sorted(want)[:5]})"
        report = {}
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            write_json_atomic(sdir / "bpy_report.json", report)
        return report, failure

    def _clip(self, spec, sdir, tdir, prefix, w, h, fps, n) -> dict:
        """Rule 3: the shot's output once every frame is COMMITTED. ``png_seq``: the sha256 list of the frames (``frames.sha256``);
        ``mkv_ffv1``: an FFV1 MKV encoded from the frames, probed (codec, size, frame count) before it is hashed and uploaded."""
        if spec["render"]["output"] == "png_seq":
            lines = "".join(f"{C.sha256_file(sdir / 'frames' / FRAME_NAME.format(index=i))}  frames/{FRAME_NAME.format(index=i)}\n"
                            for i in range(n))
            path = sdir / "frames.sha256"
            path.write_text(lines, encoding="utf-8")
            codec = "png"
        else:
            path = sdir / "shot.mkv"
            tmp = tdir / "shot.mkv"
            cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", "0",
                   "-i", str(sdir / "frames" / "frame_%06d.png"), "-frames:v", str(n), "-c:v", "ffv1", "-level", "3",
                   "-g", "1", "-pix_fmt", "yuv444p", str(tmp)]
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                raise RenderFailed(f"ffmpeg could not build the FFV1 clip: {p.stderr.strip()[:300]}")
            probe = _probe(tmp)
            if probe != ("ffv1", w, h, n):
                raise RenderFailed(f"the clip probes as {probe}, expected ('ffv1', {w}, {h}, {n})")
            os.replace(tmp, path)
            codec = "ffv1"
        self._put_verified([(path, prefix + path.name)], prefix, tdir)
        return {"path": path.name, "sha256": C.sha256_file(path), "codec": codec, "width": w, "height": h, "fps": fps}


def _new_lines(path: Path, offset: int) -> tuple[list[dict], int]:
    """Complete JSON lines appended to ``path`` after ``offset`` (a half-written last line waits for the next pass)."""
    if not path.exists():
        return [], offset
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read()
    end = chunk.rfind(b"\n")
    if end < 0:
        return [], offset
    out = [json.loads(ln) for ln in chunk[:end].decode("utf-8").splitlines() if ln.strip()]
    return out, offset + end + 1


def _stop(proc) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _probe(path: Path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=codec_name,width,height,nb_read_frames", "-of", "json", str(path)], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    s = (json.loads(p.stdout).get("streams") or [{}])[0]
    return s.get("codec_name"), s.get("width"), s.get("height"), int(s.get("nb_read_frames") or 0)


# --- the smoke (roadmap 12.4 step 1) -------------------------------------------------------------------------------------------

def smoke_spec(job_id: str = "smoke", frames: int = P.SMOKE.frames) -> dict:
    """An 8-frame shot_spec/2 of the master (2560x1440, 24 fps, eevee_fast): valid as a contract; the smoke renders it with the
    Workbench override at 12.5 %. Asset ids are placeholders: the smoke scene is built in bpy/render_shot.py, nothing is loaded."""
    z = "0" * 64
    ref = lambda i: {"id": i, "sha256": z}  # noqa: E731
    return {
        "schema": "shot_spec/2", "job_id": job_id, "shot_id": "smoke_01", "lane": "VIDEO_3D", "recipe": "blender_eevee/1",
        "clock": {"fps": 24, "frames": frames, "start_frame": 0},
        "frame": {"width": 2560, "height": 1440, "render_scale": 1.0},
        "scene": {"template_asset": ref("scene_template.smoke"), "era": "smoke", "set_assets": [], "characters": [],
                  "camera": {"rig": "dolly", "start": {"pos": [0, -12, 4], "yaw_deg": 0, "pitch_deg": -15},
                             "end": {"pos": [3, -8, 3], "yaw_deg": 20, "pitch_deg": -15}, "lens_mm": 50, "ease": "linear"},
                  "light_rig": "smoke_sun", "weather": None, "props": []},
        "performance": {"lipsync": False, "rhubarb": None, "mouth_shapes": 8, "dialogue_cover": None},
        "look": {"bible_version": "1.5", "line_weight_px": 2.0, "crease_deg": 134, "shading_steps": 3, "view_transform": "AgX",
                 "grade_look": "Medium High Contrast", "paper": {"asset": ref("texture.smoke_paper"), "opacity": 0.12}},
        "render": {"profile": "eevee_fast", "samples": 16, "motion_blur": False, "denoise": False, "output": "png_seq"},
        "seed": 1,
    }


def _opt(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "smoke" or not _opt(argv, "--out"):
        print(__doc__)
        return 2
    out = Path(_opt(argv, "--out"))
    binary = BlenderProject().resolve(_opt(argv, "--binary"))
    vault = LocalVault(_opt(argv, "--vault-dir", str(out / "vault")))
    m = HeadlessRender(binary, vault).run(smoke_spec(), out / "work", smoke=P.SMOKE)
    sdir = out / "work" / m["cache_key"]
    bad = V.check_uploaded(sdir, f"blender/{m['job_id']}/{m['cache_key']}", vault.listing(f"blender/{m['job_id']}/{m['cache_key']}"))
    summary = {"blender": m["blender"], "engine": m["engine"], "frames_written": m["frames_written"],
               "seconds_per_frame": m["seconds_per_frame"], "output": m["output"],
               "findings": m["_findings"], "vault_check": bad or "every file is on the vault with the same hash",
               "frames_dir": str(sdir / "frames"),
               "bpy_report": json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8")) if (sdir / "bpy_report.json").exists() else None}
    write_json_atomic(out / "smoke_summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
