"""modal_j5_smoke.py: the offline parts; the render command is checked against the real renderer's CLI at the pinned commit."""
import subprocess
import sys
from pathlib import Path

import pytest

from explainer_engine.cloud import modal_j5_smoke as J

REPO = Path(J.__file__).resolve().parents[2]


def test_gate_and_secret_and_cap():
    with pytest.raises(SystemExit):
        J.go_gate({})
    assert J.go_gate({"EE_MODAL_GO": "cmsg_x"}) == "cmsg_x"
    assert J.SECRET_NAME == "huggingface-secret"
    assert J._tok({"HF_TOKEN": "t"}) == "t"
    assert J.worst_usd() == pytest.approx(0.053, abs=0.002) and J.worst_usd() < J.CAPS["max_usd"] / 2   # image build + margin fit the cap


def test_commands_match_the_kit_readme_line():
    c = J.render_cmd(Path("/r"), Path("/k"), Path("/o"))
    assert c[3] == "render" and "--collage" in c and c[c.index("--seconds") + 1] == "0.125" and c[c.index("--size") + 1] == "1280x720"
    assert "select=eq(n\\,2)" in J.frame_cmd(Path("a.mp4"), Path("a.png"))[7]


def test_renderer_cli_accepts_the_flags_at_the_pinned_commit(tmp_path):
    if subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", J.CODE_COMMIT + "^{commit}"], capture_output=True).returncode:
        pytest.skip("pinned commit not in this clone")
    src = subprocess.run(["git", "-C", str(REPO), "show", f"{J.CODE_COMMIT}:explainer_engine/blender/j5_background.py"],
                         capture_output=True, text=True, check=True).stdout
    for flag in ("--collage", "--inputs", "--voice", "--out", "--seconds", "--size"):
        assert f'"{flag}"' in src, flag
    assert 'sub.add_parser("render"' in src or '"render"' in src


def test_pip_list_covers_the_renderer_imports():
    assert {"numpy", "pillow", "opencv-python-headless", "scipy"} <= {p.split("==")[0] for p in J.PIP}
    assert any(p.startswith("jsonschema") for p in J.PIP)   # explainer_engine.assets.library imports it (found by a local run)


def test_pip_has_every_third_party_import_of_the_function_body():
    import ast
    import inspect
    import textwrap
    names = set()
    for n in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(J.smoke_body)))):
        if isinstance(n, ast.ImportFrom) and n.module:
            names.add(n.module.split(".")[0])
        elif isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
    third = names - set(sys.stdlib_module_names)
    pip = {p.split("==")[0].replace("-", "_").lower() for p in J.PIP}
    assert third == {"huggingface_hub"} and third <= pip, (third, pip)
    # the module-level imports must be stdlib or modal (modal is only inside the Modal image by the SDK)
    mod = ast.parse(Path(J.__file__).read_text())
    top = {n.names[0].name.split(".")[0] for n in mod.body if isinstance(n, ast.Import)} | \
          {n.module.split(".")[0] for n in mod.body if isinstance(n, ast.ImportFrom) and n.module}
    assert top - set(sys.stdlib_module_names) - {"modal"} == set(), top
