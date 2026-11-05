"""ICW-04 (BP-175, roadmap 10.2): the Blender pin of config/cloud_pins.json is the only binary a render runs on. An archive is
extracted only when its sha256 is the pin's; a binary whose --version is not the pinned version is refused. No download."""
import io
import json
import tarfile
from pathlib import Path

import pytest

from explainer_engine.blender.project import BlenderPinError, BlenderProject
from explainer_engine.core.contracts import sha256_file
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_the_pin_is_bp175s_version_with_both_archives():
    p = BlenderProject()
    assert p.version == SR.T("BP-175", "blender_version") == "5.2.3" and p.pin["series"] == SR.T("BP-175", "series")
    for plat in ("linux-x64", "macos-arm64"):
        a = p.archive(plat)
        assert a["url"].startswith("https://download.blender.org/release/Blender5.2/") and len(a["sha256"]) == 64
    assert p.pin["image"] is None  # the pod image is named by ICW-09's OR-23 plan, not here


def _archive(tmp_path, top="blender-5.2.3-linux-x64"):
    path = tmp_path / "blender-5.2.3-linux-x64.tar.xz"
    with tarfile.open(path, "w:xz") as tar:
        data = b"#!/bin/sh\necho Blender 5.2.3\n"
        info = tarfile.TarInfo(f"{top}/blender")
        info.size, info.mode = len(data), 0o755
        tar.addfile(info, io.BytesIO(data))
    return path


def _pins_for(path):
    pins = json.loads((ROOT / "config/cloud_pins.json").read_text(encoding="utf-8"))
    pins["blender"]["archives"]["linux-x64"]["sha256"] = sha256_file(path)
    return pins


def test_install_extracts_only_the_pinned_archive(tmp_path):
    arc = _archive(tmp_path)
    with pytest.raises(BlenderPinError, match="is not the pinned"):
        BlenderProject().install(tmp_path / "dest", archive=arc)  # the real pin: this stand-in is not Blender
    assert not (tmp_path / "dest" / "blender-5.2.3-linux-x64").exists()
    binary = BlenderProject(_pins_for(arc)).install(tmp_path / "dest", archive=arc)
    assert binary == tmp_path / "dest" / "blender-5.2.3-linux-x64" / "blender" and binary.exists()


def test_install_downloads_into_dest_when_no_archive_is_given(tmp_path):
    (tmp_path / "src").mkdir()
    arc = _archive(tmp_path / "src")
    got = []

    def download(url, target):
        got.append(url)
        target.write_bytes(arc.read_bytes())

    proj = BlenderProject(_pins_for(arc))
    binary = proj.install(tmp_path / "dest", download=download)
    assert got == [proj.archive()["url"]] and binary.exists()


def test_an_archive_that_unpacks_elsewhere_is_refused(tmp_path):
    arc = _archive(tmp_path, top="other")
    with pytest.raises(BlenderPinError, match="does not unpack into one folder"):
        BlenderProject(_pins_for(arc)).install(tmp_path / "dest", archive=arc)


def test_resolve_reads_version_and_build_hash_and_refuses_another_version():
    class P:
        def __init__(self, out, rc=0):
            self.stdout, self.stderr, self.returncode = out, "", rc

    proj = BlenderProject()
    b = proj.resolve("/opt/blender", run=lambda cmd, t: P("Blender 5.2.3\n\tbuild hash: 1a2b3c4d5e6f\n"))
    assert (b.version, b.build_hash, b.device, b.gpu) == ("5.2.3", "1a2b3c4d5e6f", "cpu", None)
    with pytest.raises(BlenderPinError, match="not the pinned 5.2.3"):
        proj.resolve("/opt/blender", run=lambda cmd, t: P("Blender 5.3.0\n"))
    with pytest.raises(BlenderPinError, match="did not print a Blender version"):
        proj.resolve("/opt/blender", run=lambda cmd, t: P("Segmentation fault", rc=139))


def test_a_pin_without_hashes_is_refused():
    pins = json.loads((ROOT / "config/cloud_pins.json").read_text(encoding="utf-8"))
    pins["blender"]["archives"]["linux-x64"]["sha256"] = ""
    with pytest.raises(BlenderPinError, match="needs an https url and a sha256"):
        BlenderProject(pins)
