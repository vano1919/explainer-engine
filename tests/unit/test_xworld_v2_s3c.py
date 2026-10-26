"""The S3c depth-ControlNet test: LoRA key matching, the two prompts, the picture list, the pod wiring."""
from pathlib import Path

from explainer_engine.training.pods import xworld_v2_s3c as C
from explainer_engine.training.pods.xworld_v2_scenes import load

PODS = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods"


def _scenes():
    return [s for s in load(PODS / "stories" / "v2") if s["name"] in C.SCENES]


def test_key_match_reads_both_key_styles_and_reports_every_miss():
    keys = ["transformer.transformer_blocks.0.attn.to_q.lora_A.weight", "transformer.transformer_blocks.0.attn.to_q.lora_B.weight",
            "lora_unet_transformer_blocks_1_attn_to_k.lora_down.weight", "lora_unet_transformer_blocks_1_attn_to_k.lora_up.weight",
            "transformer.transformer_blocks.2.nope.lora_A.weight", "transformer.transformer_blocks.2.nope.alpha"]
    mods = ["transformer_blocks.0.attn.to_q", "transformer_blocks.1.attn.to_k", "control_blocks.0.attn.to_q"]
    ok, total, miss = C.match_report(keys, mods)
    assert (ok, total) == (2, 3) and miss == ["transformer_blocks_2_nope"]
    assert C.match_report(keys[:4], mods)[:2] == (2, 2)


def test_picture_list_is_pass_a_at_full_scale_plus_one_sweep_shot_per_scene_then_pass_b_at_full_scale_only():
    j = C.jobs(_scenes())
    a = [x for x in j if x["pass"] == "A"]; b = [x for x in j if x["pass"] == "B"]
    assert len(a) == 2 * 4 + 2 * 2 + 1 and len(b) == 2 * 4 and len(j) == 21  # + the cfg 1.0 vs 2.5 pair
    assert {x["scale"] for x in b} == {1.0} and j.index(b[0]) > j.index(a[-1])
    assert {x["shot"] for x in a if x["scale"] != 1.0} == set(C.SWEEP_SHOT.values())
    assert [x["cfg"] for x in a if "cfg" in x] == [1.0]
    assert len({x["name"] for x in j}) == len(j)


def test_prompts_state_the_place_and_pass_b_names_three_images_and_keeps_the_layout():
    for sc in _scenes():
        for shot in sc["shots"][1:]:
            a = C.pass_a_prompt(sc, shot)
            assert sc["place"][:40] in a and "sandals" not in a if shot["size"] != "wide" else True
            b, role = C.pass_b_prompt(sc, shot)
            assert "Keep the composition, camera and poses of Image 1 exactly" in b and "Image 2" in b
            assert ("Image 3" in b) == bool(role)


def test_the_s3c_pod_script_stops_on_step_0_runs_the_script_and_ends_with_the_vault_check():
    sh = (PODS / "xworld_v2_s3c.sh").read_text(encoding="utf-8")
    assert "xworld_v2_s3c.py" in sh and sh.index("xworld_v2_s3c.py") < sh.index("vault check-uploaded")
    assert "s3c/out" in sh and "*_depth.png" in sh and "*_sheet_*.png" in sh and "p2s/out" not in sh.split("vault check-uploaded")[1]


def test_the_sheets_build_from_whatever_pictures_exist(tmp_path):
    from PIL import Image
    from explainer_engine.training.pods import xworld_v2_s3 as S3
    for n in ("tent_s1_A1.0", "tent_s1_B1.0", "tent_s1_A0.6", "tent_s1_block", "tent_s1_S1"):
        Image.new("RGB", (64, 36), (10, 20, 30)).save(tmp_path / f"{n}.png")
    assert C.sheet(tmp_path).exists() and S3.sheet(tmp_path, ("tent",)).exists()


def test_control_branch_load_check_fails_on_a_missing_or_unexpected_control_key_and_ignores_base_keys():
    assert C.control_load_ok(["transformer_blocks.0.attn.to_q.weight"], [])[0]
    assert not C.control_load_ok([], ["control_blocks.3.attn.to_q.weight"])[0]
    assert not C.control_load_ok(["control_img_in.weight"], [])[0]
