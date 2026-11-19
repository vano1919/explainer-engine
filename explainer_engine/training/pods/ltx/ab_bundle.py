"""The two sha256-pinned files of the A/B pods (W5, D-132): the byte-stable CODE bundle (the same builder as the p14 lean pod,
``p14.lean.bundle``, minus the two pod scripts, so a pinned script never changes the bundle it pins) and the BATCH tarball (the
prompts, job specs, pictures and ``batch.json`` the plan thread writes). Both pod scripts carry ``@@EE_SRC_SHA256@@`` and
``@@BATCH_SHA256@@`` until the bytes exist; ``pin`` fills one, and the pods refuse an unfilled script (``script_problems``).

    python -m explainer_engine.training.pods.ltx.ab_bundle code <out.tar.gz> [--ref <commit>]
    python -m explainer_engine.training.pods.ltx.ab_bundle batch <out.tar.gz> <folder>
    python -m explainer_engine.training.pods.ltx.ab_bundle pin <script.sh> <EE_SRC_SHA256|BATCH_SHA256> <sha256>
Builds and pins only: nothing is uploaded here.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import re
import sys
import tarfile
from pathlib import Path

from explainer_engine.training.pods.p14 import lean

HERE = Path(__file__).resolve().parent
SCRIPTS = (HERE / "runpod_ltx_pod.sh", HERE.parent / "klein" / "klein_pod.sh")
EXCLUDE = lean.EXCLUDE + tuple(p.relative_to(lean.ROOT).as_posix() for p in SCRIPTS)
PLACEHOLDERS = ("EE_SRC_SHA256", "BATCH_SHA256")


def build_code(out, ref: str | None = None) -> str:
    """The code bundle (explainer_engine, config, assets; the two pod scripts left out): byte-stable, returns its sha256."""
    return lean.bundle(Path(out), ref, exclude=EXCLUDE)


def build_batch(out, folder) -> str:
    """The batch folder as a byte-stable tar.gz (sorted names, mode 0644, mtime 0, no owner): returns its sha256."""
    folder = Path(folder)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for p in sorted(x for x in folder.rglob("*") if x.is_file()):
            data = p.read_bytes()
            ti = tarfile.TarInfo(p.relative_to(folder).as_posix())
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0, compresslevel=9) as gz:
        gz.write(buf.getvalue())
    return hashlib.sha256(out.read_bytes()).hexdigest()


def pin(script, which: str, sha: str) -> None:
    """Fill ``@@<which>@@`` in a pod script with a 64-hex sha256; it must occur exactly once."""
    if which not in PLACEHOLDERS or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise SystemExit(f"pin: {which!r} must be one of {PLACEHOLDERS} and the value a sha256")
    script = Path(script)
    text = script.read_text(encoding="utf-8")
    if text.count(f"@@{which}@@") != 1:
        raise SystemExit(f"{script}: @@{which}@@ found {text.count(f'@@{which}@@')} times, not once")
    script.write_text(text.replace(f"@@{which}@@", sha), encoding="utf-8")


def pinned(script, which: str) -> str | None:
    """The sha256 a script carries for ``which`` (the printf line that writes it), or None while it is a placeholder."""
    key = {"EE_SRC_SHA256": "ee_src.tar.gz", "BATCH_SHA256": "batch.tar.gz"}[which]
    m = re.search(r"printf '%s  %s\\n' ([0-9a-f]{64}|@@\w+@@) \"\$JOB/" + re.escape(key), Path(script).read_text(encoding="utf-8"))
    return m.group(1) if m and not m.group(1).startswith("@@") else None


def fetch_problems(script) -> list[str]:
    """Refusals for a pod script that fetches its bundle or batch by a name a later upload can replace (an HF path on ``main`` or a
    ``resolve/main`` URL): a pinned script must keep working after any later upload, so the file name carries its own sha256
    (``code/<dir>/ee_src-<sha256>.tar.gz``) and the sha check stays."""
    return fetch_text_problems(Path(script).read_text(encoding="utf-8"), Path(script).name)


def fetch_text_problems(text: str, name: str = "script") -> list[str]:
    """``fetch_problems`` on a script text."""
    bad = []
    if re.search(r"code/\w+/(ee_src|batch)\.tar\.gz", text):
        bad.append(f"{name}: the bundle or batch is fetched by a fixed name on main: use the sha256-named file (ee_src-<sha256>.tar.gz)")
    if re.search(r"resolve/main|revision\s*=\s*['\"]main['\"]", text):
        bad.append(f"{name}: a file is fetched from main: a later upload would replace it under the pin")
    if "{stem}-{shas[name]}.tar.gz" not in text:
        bad.append(f"{name}: the bundle and batch are not fetched by their sha256-named files")
    return bad


def code_problems(script) -> list[str]:
    """Refusals for a pod script's code pin: still a placeholder, or not the sha256 of the bundle the current tree builds (a changed
    file under explainer_engine/, config/ or assets/ after the pin makes the pod run other code than the one that was reviewed)."""
    import tempfile
    want = pinned(script, "EE_SRC_SHA256")
    name = Path(script).name
    if want is None:
        return [f"{name}: the code bundle sha256 is not filled in: build it (ab_bundle code) and pin it"]
    with tempfile.TemporaryDirectory() as d:
        have = build_code(Path(d) / "ee_src.tar.gz")
    return [] if have == want else [f"{name}: the pinned code bundle {want[:12]} is not the one the current tree builds ({have[:12]}): "
                                    "rebuild, upload and pin it"]


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a.pop(0) if a else ""
    if cmd == "code" and a:
        ref = a[a.index("--ref") + 1] if "--ref" in a else None
        print(build_code(a[0], ref))
    elif cmd == "batch" and len(a) == 2:
        print(build_batch(a[0], a[1]))
    elif cmd == "pin" and len(a) == 3:
        pin(a[0], a[1], a[2])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
