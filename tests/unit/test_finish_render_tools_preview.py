"""W7 (P-8): tools/render_tools is preview only: every entry prints "preview only" and refuses --final / --master."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "render_tools"


def _preview():
    sys.path.insert(0, str(TOOLS))
    try:
        import _preview
        return _preview
    finally:
        sys.path.remove(str(TOOLS))


def test_guard_prints_the_banner(capsys):
    _preview().guard("mix", [])
    assert "PREVIEW ONLY" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--final", "--master", "--final=1"])
def test_guard_refuses_a_final_flag(flag, capsys):
    with pytest.raises(SystemExit) as e:
        _preview().guard("build_segments", ["S01", flag])
    assert e.value.code == 2 and "refused" in capsys.readouterr().err


@pytest.mark.parametrize("script", ["mix.py", "build_segments.py"])
def test_each_entry_point_calls_the_guard_before_any_heavy_import(script):
    src = (TOOLS / script).read_text(encoding="utf-8")
    import re
    first_import = re.search(r"^(?:import|from) (?!__future__)\w+", src, re.M).start()
    assert 0 < src.index("_preview.guard(") < first_import


@pytest.mark.parametrize("script", ["mix.py", "build_segments.py"])
def test_running_a_script_with_final_exits_2_and_says_preview_only(script):
    r = subprocess.run([sys.executable, str(TOOLS / script), "--final"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and "PREVIEW ONLY" in r.stdout and "refused" in r.stderr
