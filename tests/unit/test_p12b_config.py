"""T10: p12b.json holds every pin of the combined P12 pod (PAID_TESTS_PLAN 3.1-3.5: Qwen stages Q1-Q3, LTX-2.5 stages L1/L3/L2/AV); no host stage (D-89); the video weights are pinned."""
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
    assert c["drop_order"] == ["Q3", "L3", "Q2"]                  # what the creator's soft stop and a short clock drop, in order
    assert not {"hosts", "prompt_hosts"} & {k.lower() for _, k, _ in _walk(c)}   # D-89: no host stage, no hosts block
    assert set(c["stages"]) == {"Q1", "Q2", "Q3", "L1", "L3", "L2", "AV"} and "hosts" not in c["outputs"]
    assert set(c["drop_order"]) <= set(c["stages"]) and not any(c["stages"][n]["essential"] for n in c["drop_order"])
    assert {c["stages"][n]["kind"] for n in c["stages"]} == {"qwen_mva", "ltx_i2v", "ltx_ic", "ltx_a2v"}
    assert c["style_lora"]["weight"] == 0.7                       # the creator's call of 2026-10-31 (it was 1.0)
    assert c["prompt_mva"].startswith("<mva>")
    for p in ("napoleon", "general", "baker", "legionary"):
        assert c["references"][p].endswith(".png")
    pins = json.loads((ROOT / "config" / "cloud_pins.json").read_text(encoding="utf-8"))
    assert c["image_pin"] in pins["images"]


def test_the_style_lora_and_the_video_weights_agree_with_config_cloud_pins():
    """One xworld_v2 file everywhere (repo, path, sha256, weight); the LTX-2.5 repo, revision and Layout LoRA of the pod are the router's pins."""
    c = json.loads(CFG.read_text(encoding="utf-8"))
    pins = json.loads((ROOT / "config" / "cloud_pins.json").read_text(encoding="utf-8"))
    models = pins["models"]
    lora, sl = models["loras"]["xworld_v2"], c["style_lora"]
    assert (lora["hf"], lora["path"], lora["sha256"], lora["weight"]) == (sl["hf"], sl["path"], sl["sha256"], sl["weight"])
    lt, ll = c["ltx"], c["ltx"]["layout_lora"]
    assert (lt["repo"], lt["revision"]) == (models["video_ltx"]["id"], models["video_ltx"]["revision"])
    pin = models["video_ltx_layout_lora"]
    assert (ll["repo"], ll["revision"], ll["file"]) == (pin["id"], pin["revision"], pin["file"])
    assert models["keyframe"]["revision"] == c["base"]["revision"]
    for key in ("video_ltx", "video_ltx_layout_lora", "video_wan"):
        assert HEX40.match(models[key]["revision"]), key             # the creator: no null video revision
    git = pins["git"]["Lightricks/LTX-2"]
    assert lt["code"]["url"] == git["url"] and lt["code"]["sha"] == git["sha"]


def test_the_plan_numbers_meet_rp01_and_the_hard_pod_cap():
    from explainer_engine.cloud import batching
    plan = json.loads(CFG.read_text(encoding="utf-8"))["plan"]
    s, w = plan["fixed_setup_minutes"], plan["planned_work_minutes"]
    assert batching.rp01(w, s) == [] and w >= 3 * s                 # RP-01
    assert (s + w) / 60 * plan["price_per_hour_usd"] <= plan["hard_pod_usd"] == 2.40
    assert "NOT measured" in plan["note"]                          # the 20 min download is a target, not a measurement


def test_the_ltx_block_lists_every_file_it_downloads_and_its_reserve_adds_up():
    lt = json.loads(CFG.read_text(encoding="utf-8"))["ltx"]
    assert set(lt["sizes"]) <= set(lt["av_files"]) and len(lt["files"]) == 5 and len(lt["av_files"]) == 2
    assert lt["expected_gb"] >= sum(lt["sizes"].values()) / 2 ** 30 and lt["margin_gb"] > 0
    assert lt["reserve_min"] == sum(lt["reserve_parts_min"].values()) and lt["reserve_measured"] is False
