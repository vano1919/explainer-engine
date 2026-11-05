"""The pinned Blender binary (BP-175, D-96; roadmap 10.2, section 11): ``BlenderProject.resolve`` names the binary a render runs
on and refuses one that is not the pinned version; ``install`` puts the official archive in place only after its sha256 equals the
pin. The pin is the ``blender`` entry of ``config/cloud_pins.json`` (version, series, the archives' sha256); it moves only by a
decision-log row, so a newer Blender release never moves it. stdlib only: the CI smoke and the render pod run it before anything else
is installed.

    python -m explainer_engine.blender.project pin                                   # the pin as JSON
    python -m explainer_engine.blender.project install --dest D [--archive F] [--platform linux-x64]   # verify + extract, prints the binary
    python -m explainer_engine.blender.project resolve [--binary B] [--device cpu|gpu]                 # version check, prints JSON

The binary is found from ``--binary``, then ``$EE_BLENDER``, then ``blender`` on PATH. ``--version`` must print the pinned
``Blender X.Y.Z``; the build hash it prints is kept for the render manifest (``blender_render_manifest/1``).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from explainer_engine.core.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / "config" / "cloud_pins.json"
VERSION_LINE = re.compile(r"^Blender (\d+\.\d+\.\d+)\b", re.M)
HASH_LINE = re.compile(r"build hash:\s*([0-9a-f]{6,40})", re.I)
CHUNK = 1 << 20


class BlenderPinError(ConfigError):
    """The binary or archive is not the pinned Blender (BP-175): refused, never used."""


@dataclass(frozen=True)
class BlenderBinary:
    path: str
    version: str
    build_hash: str | None
    device: str  # cpu | gpu
    gpu: str | None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, target: Path) -> None:
    tmp = target.with_name(target.name + ".part")
    with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, CHUNK)
    tmp.replace(target)


def _run(cmd: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def gpu_name(run=_run, *, system: str | None = None, machine: str | None = None) -> str | None:
    """The GPU a render can use, or None: the first NVIDIA card (``nvidia-smi``), else on Apple silicon the chip (its GPU is
    on the chip; Blender uses it through Metal: EEVEE always, Cycles with compute type METAL), named by ``sysctl``."""
    if shutil.which("nvidia-smi") is not None:
        try:
            p = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 20)
            name = (p.stdout or "").strip().splitlines()
            if p.returncode == 0 and name and name[0].strip():
                return name[0].strip()
        except (OSError, subprocess.SubprocessError):
            pass
    if (system or platform.system()) == "Darwin" and (machine or platform.machine()) == "arm64":
        try:
            p = run(["sysctl", "-n", "machdep.cpu.brand_string"], 20)
        except (OSError, subprocess.SubprocessError):
            return None
        name = (p.stdout or "").strip()
        return name if p.returncode == 0 and name.startswith("Apple") else None
    return None


class BlenderProject:
    """The Blender pin of ``config/cloud_pins.json`` and the checks that hold a binary to it."""

    def __init__(self, pins: dict | None = None, pins_path: Path | str | None = None) -> None:
        data = pins if pins is not None else json.loads(Path(pins_path or PINS).read_text(encoding="utf-8"))
        pin = data.get("blender")
        if not isinstance(pin, dict) or not pin.get("version") or not isinstance(pin.get("archives"), dict):
            raise BlenderPinError("config/cloud_pins.json has no blender entry with a version and archives (BP-175)")
        for plat, a in pin["archives"].items():
            if not re.fullmatch(r"[0-9a-f]{64}", str(a.get("sha256", ""))) or not str(a.get("url", "")).startswith("https://"):
                raise BlenderPinError(f"blender archive {plat}: needs an https url and a sha256 (BP-175)")
        self.pin = pin

    @property
    def version(self) -> str:
        return self.pin["version"]

    def archive(self, platform: str = "linux-x64") -> dict:
        a = self.pin["archives"].get(platform)
        if a is None:
            raise BlenderPinError(f"no pinned Blender archive for {platform} (pinned: {', '.join(sorted(self.pin['archives']))})")
        return a

    def verify_archive(self, path: Path | str, platform: str = "linux-x64") -> str:
        """The archive's sha256 when it is the pinned one; BlenderPinError otherwise."""
        want = self.archive(platform)["sha256"]
        got = _sha256(Path(path))
        if got != want:
            raise BlenderPinError(f"{Path(path).name}: sha256 {got} is not the pinned {want} (Blender {self.version}, BP-175)")
        return got

    def install(self, dest: Path | str, *, platform: str = "linux-x64", archive: Path | str | None = None,
                download=_download) -> Path:
        """Put the pinned Blender under ``dest`` and return its binary. An archive that is given (a CI cache) or downloaded is
        checked against the pin before anything is extracted; an existing install is reused only when its archive still
        verifies. Linux archives only: on macOS the creator installs the pinned .dmg by hand and ``resolve`` checks it."""
        if not platform.startswith("linux"):
            raise BlenderPinError(f"install handles the Linux archives; for {platform} install the pinned image by hand")
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        url = self.archive(platform)["url"]
        name = url.rsplit("/", 1)[-1]
        src = Path(archive) if archive else dest / name
        if not src.exists():
            if archive:
                raise BlenderPinError(f"{src} does not exist")
            download(url, src)
        self.verify_archive(src, platform)
        folder = dest / name.removesuffix(".tar.xz")
        binary = folder / "blender"
        if not binary.exists():
            with tarfile.open(src, "r:xz") as tar:
                top = {m.name.split("/", 1)[0] for m in tar.getmembers()}
                if top != {folder.name}:
                    raise BlenderPinError(f"{name} does not unpack into one folder {folder.name} ({sorted(top)[:3]})")
                tar.extractall(dest, filter="data")  # no absolute paths or links out of dest
        if not binary.exists():
            raise BlenderPinError(f"{binary} is missing after extracting {name}")
        return binary

    def find(self, binary: Path | str | None = None) -> str:
        cand = str(binary) if binary else os.environ.get("EE_BLENDER") or shutil.which("blender")
        if not cand:
            raise BlenderPinError("no Blender binary: pass --binary, set EE_BLENDER, or put the pinned blender on PATH")
        return cand

    def resolve(self, binary: Path | str | None = None, *, device: str = "cpu", run=_run) -> BlenderBinary:
        """The binary a render runs on, held to the pin: ``--version`` must print ``Blender <pinned version>``. ``device`` gpu
        needs an NVIDIA card or Apple silicon (``gpu_name``); its name goes into the render manifest. ``auto`` = gpu when there
        is one, else cpu (a CI runner: EEVEE then draws through Mesa's software OpenGL, which is the CPU)."""
        if device not in ("cpu", "gpu", "auto"):
            raise BlenderPinError(f"device {device!r} is cpu, gpu or auto")
        path = self.find(binary)
        try:
            p = run([path, "--factory-startup", "--version"], 120)
        except (OSError, subprocess.SubprocessError) as e:
            raise BlenderPinError(f"{path} --version failed: {e}") from e
        text = (p.stdout or "") + "\n" + (p.stderr or "")
        m = VERSION_LINE.search(text)
        if p.returncode != 0 or m is None:
            raise BlenderPinError(f"{path} --version did not print a Blender version (rc {p.returncode}): {text.strip()[:200]}")
        if m.group(1) != self.version:
            raise BlenderPinError(f"{path} is Blender {m.group(1)}, not the pinned {self.version} (BP-175); the pin moves only "
                                  "by a decision-log row")
        h = HASH_LINE.search(text)
        gpu = gpu_name(run) if device in ("gpu", "auto") else None
        if device == "gpu" and gpu is None:
            raise BlenderPinError("device gpu asked for, but there is no NVIDIA card (nvidia-smi) and no Apple silicon GPU")
        if device == "auto":
            device = "gpu" if gpu else "cpu"
        return BlenderBinary(path=path, version=m.group(1), build_hash=h.group(1) if h else None, device=device, gpu=gpu)


def _opt(argv: list[str], name: str, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("pin", "install", "resolve"):
        print(__doc__)
        return 2
    proj = BlenderProject()
    try:
        if argv[0] == "pin":
            print(json.dumps(proj.pin, indent=1))
        elif argv[0] == "install":
            if not _opt(argv, "--dest"):
                print("install needs --dest <folder>")
                return 2
            print(proj.install(_opt(argv, "--dest"), platform=_opt(argv, "--platform", "linux-x64"), archive=_opt(argv, "--archive")))
        else:
            print(json.dumps(asdict(proj.resolve(_opt(argv, "--binary"), device=_opt(argv, "--device", "cpu"))), indent=1))
    except BlenderPinError as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
