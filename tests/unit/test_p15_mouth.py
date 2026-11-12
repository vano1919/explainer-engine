"""The J5 mouth-variant job: 16 pictures, fixed seeds, short prompts with every tag once, the masked composite that leaves every pixel outside the
mask bit-identical, and the pins. No GPU, no network."""
import numpy as np

from explainer_engine.training.pods.p15 import p15_mouth as M


def test_sixteen_jobs_with_fixed_seeds_and_short_prompts():
    cfg = M.load_cfg()
    js = M.jobs(cfg)
    assert len(js) == 16 and [j["hero"] for j in js] == ["H2"] * 8 + ["H1"] * 8
    assert [j["tag"] for j in js[:8]] == ["A", "B", "C", "D", "E", "F", "blink_half", "blink_full"]
    assert len({j["seed"] for j in js}) == 16 and js == M.jobs(cfg)                      # fixed, distinct, repeatable
    assert len({j["name"] for j in js}) == 16
    for j in js:
        words = j["prompt"].split()
        assert len(words) <= 90
        tag = M.SHAPE_TAGS[j["tag"]]
        assert j["prompt"].count(tag) == 1                                                  # each tag once
        assert ("eyes" in j["prompt"].split(":")[0]) == (j["kind"] == "blink")


def test_inputs_are_pinned_by_sha256_on_the_input_folder():
    cfg = M.load_cfg()
    for hero in cfg["heroes"].values():
        assert set(hero["files"]) == {"sheet", "cut", "mask"}
        for f in hero["files"].values():
            assert len(f["sha256"]) == 64 and f["path"].startswith("route_test_2026-11/j5_dialogue/mouth_variants_input/")


def test_the_composite_changes_nothing_outside_the_mask_and_the_check_says_so():
    cfg = M.load_cfg()
    hero = cfg["heroes"]["H1"]
    rng = np.random.default_rng(3)
    sheet = rng.integers(0, 256, (704, 1280, 3), dtype=np.uint8)
    for kind in ("mouth", "blink"):
        box = M.crop_box(hero, kind)
        x0, y0, x1, y1 = box
        assert 0 <= x0 < x1 <= 1280 and 0 <= y0 < y1 <= 704
        mask = M.feature_mask(hero, kind)
        assert mask.max() > 0.99 and mask[:5].max() == 0.0
        assert np.count_nonzero(mask[y0:y1, x0:x1]) == np.count_nonzero(mask)            # the whole mask lies inside the crop
        edited = rng.integers(0, 256, (y1 - y0, x1 - x0, 3), dtype=np.uint8)
        out = M.composite(sheet, edited, box, mask)
        assert M.check_outside(sheet, out, mask) == 0 and (out != sheet).any()
        broken = out.copy()
        broken[0, 0] ^= 1                                                                    # one pixel outside the mask is caught
        assert M.check_outside(sheet, broken, mask) == 1


def test_a_full_mask_pixel_takes_the_edit_and_a_zero_pixel_keeps_the_original():
    sheet = np.full((704, 1280, 3), 100, np.uint8)
    hero = M.load_cfg()["heroes"]["H2"]
    box = M.crop_box(hero, "mouth")
    mask = M.feature_mask(hero, "mouth")
    edited = np.full((box[3] - box[1], box[2] - box[0], 3), 200, np.uint8)
    out = M.composite(sheet, edited, box, mask)
    cx, cy = int(hero["mouth"][0]), int(hero["mouth"][1] + hero["mouth"][4] * 0.5)
    assert out[cy, cx, 0] == 200 and out[0, 0, 0] == 100
