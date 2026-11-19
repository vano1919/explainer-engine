"""Step 1.5 (D-139 decision 2): one render path. mix.py is preview only and never writes into a master folder."""
import json
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


# --- parity: the nine build_segments DIPS vs the script's authored transitions (plan owner decision (a), 2026-11-19) ---------

NINE = {"S01_SH005", "S02_SH009", "S03_SH010", "S04_SH015", "S05_SH021", "S06_SH012", "S07_SH008", "S08_SH003", "S08_SH004"}
AUTHORED = {"S01_SH005": "fade_to_black", "S02_SH009": "hard_cut", "S03_SH010": "cross_dissolve_8f", "S04_SH015": "hard_cut",
            "S05_SH021": "hard_cut", "S06_SH012": "cross_dissolve_8f", "S07_SH008": "cross_dissolve_8f",
            "S08_SH003": "fade_to_black", "S08_SH004": "hard_cut"}


def test_the_nine_dips_are_a_documented_difference_not_a_tolerance_hole():
    """G9 honours the script's own ``transition_out`` (D-131: the episode folder is the single source). build_segments' DIPS
    (a 10-frame end fade, a mix side effect) is NOT ported; seven of the nine differ by authored choice. Any change to these
    nine authored values or to the DIPS set must change this test on purpose."""
    import re
    root = Path(__file__).resolve().parents[2]
    bs = (root / "tools" / "render_tools" / "build_segments.py").read_text(encoding="utf-8")
    dips = set(re.findall(r'"(S\d\d_SH\d\d\d)"', bs.split("DIPS = {", 1)[1].split("}", 1)[0]))
    assert dips == NINE
    script = json.loads((root / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    got = {s["shot_id"]: s.get("transition_out") for s in script["shots"] if s["shot_id"] in NINE}
    assert got == AUTHORED
    differ = [sid for sid, t in got.items() if t != "fade_to_black"]
    assert len(differ) == 7
    known = json.loads((root / "episodes" / "ep_truce_1914" / "qa" / "known_review_items.json").read_text(encoding="utf-8"))
    assert any("DIPS not ported: 7 of 9" in x for x in known["items"])           # the watch check shows it (unresolved_reviews)
