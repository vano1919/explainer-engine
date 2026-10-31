"""T10: p12b.json holds every pin of the Qwen-drawing P12b (PAID_TESTS_PLAN 3.1, 3.3, 3.3a); no host stage (D-89); the video weights are pinned."""
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


def test_p12b_json_is_pinned_complete_and_has_no_host_stage():
    c = json.loads(CFG.read_text(encoding="utf-8"))
    assert c["base"]["revision"] == "d26bb61231c349cf6b7896fa83353113880e1ba3"
    for _, k, v in _walk(c):
        if k == "revision" or k == "sha":
            assert HEX40.match(v), (k, v)
    assert re.match(r"^[0-9a-f]{64}$", c["style_lora"]["sha256"])
    assert len(c["azimuths"]) == 12
    assert c["drop_order"] == ["Q3", "Q2"]
    assert not {"layout", "av", "hosts", "prompt_hosts"} & {k.lower() for _, k, _ in _walk(c)}   # D-89: no host stage, no hosts block
    assert set(c["stages"]) == {"Q1", "Q2", "Q3"} and "hosts" not in c["outputs"]
    assert c["style_lora"]["weight"] == 0.7                       # the creator's call of 2026-10-31 (it was 1.0)
    for name in ("Q1", "Q2", "Q3"):
        assert c["prompt_mva"].startswith("<mva>")
    for p in ("napoleon", "general", "baker", "legionary"):
        assert c["references"][p].endswith(".png")
    pins = json.loads((ROOT / "config" / "cloud_pins.json").read_text(encoding="utf-8"))
    assert c["image_pin"] in pins["images"]


def test_the_style_lora_and_the_video_weights_agree_with_config_cloud_pins():
    """One xworld_v2 file everywhere (repo, path, sha256, weight) and the video repo/revision of the pod are the router's pins."""
    c = json.loads(CFG.read_text(encoding="utf-8"))
    models = json.loads((ROOT / "config" / "cloud_pins.json").read_text(encoding="utf-8"))["models"]
    lora, sl = models["loras"]["xworld_v2"], c["style_lora"]
    assert (lora["hf"], lora["path"], lora["sha256"], lora["weight"]) == (sl["hf"], sl["path"], sl["sha256"], sl["weight"])
    assert (c["video"]["repo"], c["video"]["revision"]) == (models["video_ltx"]["id"], models["video_ltx"]["revision"])
    assert models["keyframe"]["revision"] == c["base"]["revision"]
    for key in ("video_ltx", "video_wan"):
        assert HEX40.match(models[key]["revision"]), key             # the creator: no null video revision


def test_the_plan_numbers_meet_rp01_and_the_hard_pod_cap():
    from explainer_engine.cloud import batching
    plan = json.loads(CFG.read_text(encoding="utf-8"))["plan"]
    s, w = plan["fixed_setup_minutes"], plan["planned_work_minutes"]
    assert s <= 22 and 85 <= w <= 90
    assert batching.rp01(w, s) == [] and w >= 3 * s                 # RP-01
    assert (s + w) / 60 * plan["price_per_hour_usd"] <= plan["hard_pod_usd"] == 2.40
    assert "NOT measured" in plan["note"]                          # the 22 min is the creator's target, not a measurement
