"""The Modal LTX launcher's free pre-flight (the 2026-11-07 19:21 failure: first frames not under P14_LOCAL_ROOTS -> HF 404 after weights were read)."""
import importlib.util
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/p15/modal_ltx_jobs_v1.py"
spec = importlib.util.spec_from_file_location("modal_ltx_jobs_v1", P)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

DOC = {"jobs": [{"id": "a", "first_frame": {"path": "route_test_2026-11/sa_test/ltx1/first_frames/f.png"}}]}


def test_first_frame_under_the_root_and_in_inputs_passes(tmp_path):
    (tmp_path / "f.png").write_bytes(b"x")
    assert M.first_frames_resolve(DOC, [["route_test_2026-11/sa_test/ltx1", "/out"]], tmp_path) == []


def test_wrong_root_is_caught_before_any_weight(tmp_path):
    (tmp_path / "f.png").write_bytes(b"x")
    bad = M.first_frames_resolve(DOC, [["route_test_2026-11/pilot", "/out"]], tmp_path)
    assert bad and "none of the local roots" in bad[0]


def test_missing_input_is_caught(tmp_path):
    assert any("not in the inputs" in b for b in M.first_frames_resolve(DOC, [["route_test_2026-11/sa_test/ltx1", "/out"]], tmp_path))


def test_launcher_root_matches_the_jobs_file():
    import json
    doc = json.loads((Path("/home/user/in_ltx1/sa_ltx1_jobs.json")).read_text()) if Path("/home/user/in_ltx1/sa_ltx1_jobs.json").exists() else None
    if doc:
        roots = [[M.IN.replace("in_ltx1", "ltx1"), "/out"]]
        assert M.first_frames_resolve(doc, roots, "/home/user/in_ltx1") == []
