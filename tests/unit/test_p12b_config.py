"""T10: p12b.json holds every pin of the Qwen-only P12b (PAID_TESTS_PLAN 3.1, 3.3, 3.3a)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "explainer_engine" / "training" / "pods" / "p12" / "p12b.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "/" + k, k, v
            yield from _walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, f"{path}[{i}]")


def test_p12b_json_is_pinned_complete_and_qwen_only():
    c = json.loads(CFG.read_text(encoding="utf-8"))
    assert c["base"]["revision"] == "d26bb61231c349cf6b7896fa83353113880e1ba3"
    for _, k, v in _walk(c):
        if k == "revision" or k == "sha":
            assert HEX40.match(v), (k, v)
    assert re.match(r"^[0-9a-f]{64}$", c["style_lora"]["sha256"])
    assert len(c["azimuths"]) == 12
    assert c["drop_order"] == ["Q3", "Q2"]
    assert not {"ltx", "layout", "av"} & {k.lower() for _, k, _ in _walk(c)}
    assert set(c["stages"]) == {"Q1", "Q2", "Q3", "Q4"}
    for name in ("Q1", "Q2", "Q3"):
        assert c["prompt_mva"].startswith("<mva>")
    for p in c["prompt_hosts"].values():
        assert p.startswith("xworld style")
    for p in ("napoleon", "general", "baker", "legionary"):
        assert c["references"][p].endswith(".png")
    pins = json.loads((ROOT / "config" / "cloud_pins.json").read_text(encoding="utf-8"))
    assert c["image_pin"] in pins["images"]
