"""HF-7 (Truce 1914 assembly, FL-404): ``--sound-library PATH`` on ``run`` and ``status`` reaches ``Episode(sound_library=...)``
and so the fingerprint of G4 and G8 (the library's manifest sha)."""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.episode import run as RUN


def _library(path: Path, extra: str = "") -> Path:
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(json.dumps({"items": [], "note": extra}), encoding="utf-8")
    return path


def test_the_flag_reaches_the_episode_on_run_and_on_status(tmp_path, monkeypatch, capsys):
    from tests.unit import test_v43_runner as base
    root = base._episode(tmp_path)
    lib = _library(tmp_path / "view")
    seen = []
    real = RUN.Episode.__init__

    def spy(self, *a, **kw):
        real(self, *a, **kw)
        seen.append(self.sound_library)
    monkeypatch.setattr(RUN.Episode, "__init__", spy)
    monkeypatch.setattr(RUN, "run_stage", lambda ep, stage: {"gate": "G1", "stage": stage, "verdict": {"status": "PASS"}, "rows": []})
    assert RUN.main(["status", str(root), "--sound-library", str(lib)]) == 0
    assert RUN.main(["run", str(root), "--stage", "script", "--sound-library", str(lib)]) == 0
    assert seen == [lib, lib]
    seen.clear()
    RUN.main(["status", str(root)])                       # no flag: the repo's own library, as before
    assert len(seen) == 1 and seen[0] != lib and seen[0].name == "library"


def test_a_different_library_changes_the_fingerprint_of_g4_and_g8(tmp_path):
    from tests.unit import test_v43_runner as base
    root = base._episode(tmp_path)
    a, b = _library(tmp_path / "a"), _library(tmp_path / "b", "another view")
    for stage in ("sound_plan", "sound"):
        fa = RUN.fingerprint(RUN.Episode(root, sound_library=a), stage)
        fb = RUN.fingerprint(RUN.Episode(root, sound_library=b), stage)
        assert fa != fb
        assert fa == RUN.fingerprint(RUN.Episode(root, sound_library=a), stage)
