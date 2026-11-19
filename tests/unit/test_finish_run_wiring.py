"""W7: the finishing chain is wired at the end of ``episode/run.py::stage_assemble``: only a master whose G9 rows are all PASS, never a
rehearsal, and a scene without an accepted keyframe has no key (VAL-CLR-01 NOT_RUN)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from explainer_engine.episode import run as RUN
from explainer_engine.episode import shot_state as SS
from explainer_engine.qa import gates as G

RECORDS = [{"shot_id": "S01_SH001", "total_frames": 24, "clip_path": "c1.mp4"}, {"shot_id": "S02_SH001", "total_frames": 24, "clip_path": "c2.mp4"}]


def _ep(tmp_path: Path):
    for rel in ("editing", "qa", "production", "audio", "renders/final"):
        (tmp_path / rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / "audio" / "mix.wav").write_bytes(b"x")
    (tmp_path / "renders/final/ep_master.mp4").write_bytes(b"x")
    return SimpleNamespace(root=tmp_path, fps=24, size=__import__("explainer_engine.core.delivery", fromlist=["size"]).size(), chunks=None, chunk_seconds=None, manifest={"episode_id": "ep"},
                           path=lambda rel: tmp_path / rel, timed_script=lambda: {"shots": []}, timing=lambda: None)


def _patch(monkeypatch, ep, total_frames, calls):
    from explainer_engine.production import assemble as ASM
    monkeypatch.setattr(RUN, "_records", lambda e: RECORDS)
    monkeypatch.setattr(RUN, "_expand_script_for_records", lambda s, r, fps: {"shots": [{}, {}]})
    monkeypatch.setattr(RUN, "DELIVERED_MIX_REL", "audio/mix.wav")
    monkeypatch.setattr(ASM, "assemble_shot_clips", lambda *a, **k: {"chunks": {"left": [], "count": 1, "reused": 0}, "total_frames": total_frames})
    monkeypatch.setattr("explainer_engine.edit.cinematic_transitions.plan_episode_cinematic_transitions", lambda *a, **k: [{}])
    monkeypatch.setattr("explainer_engine.qa.final_frame_qa.build_resize_encode_manifest", lambda *a, **k: {})
    monkeypatch.setattr(RUN, "_finish_rows", lambda e, m, r: calls.append(m) or [G.row("finish_probe", True, "ran")])


def test_a_failing_master_does_not_run_the_finishing_chain(tmp_path, monkeypatch):
    ep, calls = _ep(tmp_path), []
    _patch(monkeypatch, ep, 47, calls)                      # 47 != 48 planned: master_frames_match_the_shots FAILs
    rows, _ = RUN.stage_assemble(ep, False)
    assert any(r["gate"] == "master_frames_match_the_shots" and r["status"] != G.PASS for r in rows)
    assert not calls and not any(r["gate"] == "finish_probe" for r in rows)


def test_a_rehearsal_skips_the_finishing_chain(tmp_path, monkeypatch):
    ep, calls = _ep(tmp_path), []
    _patch(monkeypatch, ep, 48, calls)
    rows, _ = RUN.stage_assemble(ep, True)
    assert not calls


def test_a_passing_master_runs_the_chain_and_appends_its_rows(tmp_path, monkeypatch):
    ep, calls = _ep(tmp_path), []
    _patch(monkeypatch, ep, 48, calls)
    rows, _ = RUN.stage_assemble(ep, False)
    assert all(r["status"] == G.PASS for r in rows), [(r["gate"], r["status"]) for r in rows]
    assert len(calls) == 1 and rows[-1]["gate"] == "finish_probe"


def test_a_scene_without_an_accepted_keyframe_has_no_key(tmp_path, monkeypatch):
    seen = {}
    import explainer_engine.finish.chain as FIN
    monkeypatch.setattr(FIN, "finish_rows", lambda master, out, **k: seen.update(k) or [])
    img = tmp_path / "k.png"
    from PIL import Image
    Image.new("RGB", (32, 18), (120, 60, 30)).save(img)
    ss = SS.ShotStates(tmp_path)
    sha = SS.sha256_of(img)
    for st in ("IMAGE_GENERATED", "IMAGE_OBSERVED", "IMAGE_ACCEPTED"):
        ss.advance("S01_SH001", st, sha=sha, path="k.png")
    ep = SimpleNamespace(root=tmp_path, fps=24)
    rows = RUN._finish_rows(ep, tmp_path / "m.mp4", RECORDS)
    assert any(r["gate"] == "VAL-CLR-01:S02" and r["status"] == G.NOT_RUN for r in rows)
    assert "S02" not in seen["scene_keys"]
