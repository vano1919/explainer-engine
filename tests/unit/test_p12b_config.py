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
    assert s <= 45 and 170 <= w <= 180                              # the combined plan's numbers (docs/wip/P12_COMBINED_PLAN, 3.F); a change is a new plan
    assert batching.rp01(w, s) == [] and w >= 3 * s                 # RP-01
    assert (s + w) / 60 * plan["price_per_hour_usd"] <= plan["hard_pod_usd"] == 2.40
    assert "NOT measured" in plan["note"]                          # the 20 min download is a target, not a measurement


def test_the_ltx_block_lists_every_file_it_downloads_and_its_reserve_adds_up():
    lt = json.loads(CFG.read_text(encoding="utf-8"))["ltx"]
    assert len(lt["files"]) == 5 and len(lt["av_files"]) == 2
    # a size for EVERY downloaded file (audit 2026-11-01 #11): verify_weights stops a stage whose file is truncated
    assert set(lt["sizes"]) == set(lt["files"]) | set(lt["av_files"]) | {lt["layout_lora"]["file"]}
    assert lt["expected_gb"] >= sum(lt["sizes"].values()) / 2 ** 30 and lt["margin_gb"] > 0     # 114.8 GiB of files, 119 planned
    assert lt["reserve_min"] == sum(lt["reserve_parts_min"].values()) and lt["reserve_measured"] is False
    assert set(lt["optional_reserve_min"]) == {"L3"} and "NOT measured" in lt["optional_reserve_note"]


def test_the_prompts_file_is_the_same_text_as_the_prompts_block():
    """docs/pods/P12_PROMPTS.md names p12b_prompts.json as the copy of ltx.prompts; they must not drift (audit 2026-11-01 #12)."""
    copy = json.loads((CFG.parent / "p12b_prompts.json").read_text(encoding="utf-8"))
    c = json.loads(CFG.read_text(encoding="utf-8"))["ltx"]
    assert copy["prompts"] == c["prompts"] and copy["prompt_source"] == c["prompt_source"]


def test_the_silent_p12_prompts_name_a_fast_action_and_no_slow_filler():
    """WP-R3 (BP-172, KP-47): the six silent shots are linted as hyped-zone shots; the AV prompts are driven by the take."""
    from explainer_engine.scripting.shot_prompt_lint import check_shot
    c = json.loads(CFG.read_text(encoding="utf-8"))["ltx"]["prompts"]
    for name in ("tent_s0", "tent_s1", "tent_s2", "tent_s3", "tent_s4", "ship_s2"):
        found = [f for f in check_shot({"id": name, "kind": "video", "prompt": c[name], "fast_action": True, "seconds": 5})
                 if f["rule"] == "KP-47"]
        assert found == [], (name, found)
        assert not re.search(r"slow breath|tilts his head down|slowly|gently", c[name], re.I), name


def test_one_plain_clip_is_rendered_at_73_frames_and_the_rest_at_121():
    c = json.loads(CFG.read_text(encoding="utf-8"))["ltx"]["render"]
    assert c["frames"] == 121 and c["frames_by_shot"] == {"tent_s1": 73}
    assert all((n - 1) % 8 == 0 for n in [c["frames"], *c["frames_by_shot"].values()])   # LTX takes 8k+1 frames
