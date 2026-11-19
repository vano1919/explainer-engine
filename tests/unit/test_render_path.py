"""Step 1.5 (D-139 decision 2): one render path. mix.py is preview only and never writes into a master folder."""
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError


def _mix():
    import importlib.util
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("render_mix", root / "tools" / "render_tools" / "mix.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_a_work_dir_inside_renders_final_is_refused(tmp_path):
    m = _mix()
    with pytest.raises(ContractError, match="preview only"):
        m.refuse_master_destination(tmp_path / "ep" / "renders" / "final", tmp_path / "ep")
    with pytest.raises(ContractError, match="preview only"):
        m.refuse_master_destination(tmp_path / "ep" / "renders" / "final" / "sub", None)


def test_dotdot_and_symlinks_do_not_get_around_the_refusal(tmp_path):
    m = _mix()
    (tmp_path / "ep" / "renders" / "final").mkdir(parents=True)
    (tmp_path / "ep" / "work").mkdir()
    with pytest.raises(ContractError):
        m.refuse_master_destination(tmp_path / "ep" / "work" / ".." / "renders" / "final", tmp_path / "ep")
    link = tmp_path / "innocent"
    link.symlink_to(tmp_path / "ep" / "renders" / "final", target_is_directory=True)
    with pytest.raises(ContractError):
        m.refuse_master_destination(link, tmp_path / "ep")


def test_a_preview_folder_is_allowed(tmp_path):
    m = _mix()
    m.refuse_master_destination(tmp_path / "ep" / "work" / "preview", tmp_path / "ep")
    m.refuse_master_destination(tmp_path / "renders" / "finalists", None)   # a name that only starts the same way


def test_run_mix_refuses_before_reading_anything(tmp_path):
    m = _mix()
    with pytest.raises(ContractError, match="preview only"):
        m.run_mix(episode_dir=tmp_path / "ep", work_dir=tmp_path / "ep" / "renders" / "final")


def test_the_report_of_a_mix_says_it_is_a_preview():
    src = (Path(__file__).resolve().parents[2] / "tools" / "render_tools" / "mix.py").read_text(encoding="utf-8")
    assert 'report["preview_only"] = True' in src
