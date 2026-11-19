"""V4.1 Step 0.4a (D-139): the picture route, the retired-era list, the slice allowlists and the CI workflow are protected files:
a tool edit needs the creator's recorded word (``protected_config``), like the money caps."""
import json
from pathlib import Path

import pytest

from _gov import make_repo
from explainer_engine.governance import hooks, records

FILES = ("config/picture_route.json", "config/retired_era.json", "docs/architecture/v4_1_allowlists.json",
         ".github/workflows/quality.yml")
REPO = Path(__file__).resolve().parents[2]


def test_the_four_files_are_listed_in_the_real_routing_config():
    prot = json.loads((REPO / "config" / "model_routing.json").read_text(encoding="utf-8"))["protected_files"]
    for f in FILES:
        assert prot[f] == 60


@pytest.mark.parametrize("rel", FILES)
def test_the_hook_refuses_an_edit_until_the_creators_word_is_recorded(tmp_path, rel):
    repo = make_repo(tmp_path / "r", git=True)
    cfg = repo / "config" / "model_routing.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    real = json.loads((REPO / "config" / "model_routing.json").read_text(encoding="utf-8"))
    data["protected_files"] = real["protected_files"]            # the repo's own list under test
    cfg.write_text(json.dumps(data), encoding="utf-8")
    p = str(repo / rel)
    for tool in ("Edit", "Write"):
        assert hooks.pre_write({"tool_name": tool, "tool_input": {"file_path": p}}, repo) == 2
    records.add("protected_config", rel, "cmsg_x", "ვანო: კი", root=repo)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 0
    other = next(f for f in FILES if f != rel)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": str(repo / other)}}, repo) == 2
