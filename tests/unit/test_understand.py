"""P1 (roadmap 2026-11-14 B.2): picture understanding into a ``scene_layers/1`` folder, on a synthetic picture with fake model
runners (no model, no network): depth kept at full size and never blurred, the director's near/far checks, SAM masks cleaned
of stray islands, BiRefNet only inside the edge band, flames from the warm pixels of the director's disc, LaMa replacing only
the hole, and the cache key."""
from __future__ import annotations

import json

import numpy as np
from PIL import Image

from explainer_engine.production import understand as U

H, W = 120, 200


def _picture(tmp_path):
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (70, 90, 140)                       # sky
    img[60:] = (110, 90, 60)                     # ground
    img[50:100, 40:70] = (30, 30, 30)            # a dark "man"
    img[70:76, 150:154] = (255, 200, 60)         # a flame: warm and bright
    p = tmp_path / "pic.png"
    Image.fromarray(img).save(p)
    return p, img


def _depth_runner(rgb):
    h, w = rgb.shape[:2]
    d = np.repeat(np.linspace(0.1, 1.0, 64, dtype=np.float32)[:, None], 100, axis=1)   # small model output, bottom near
    d[25:50, 20:35] = 1.2                                                            # the man: nearest
    return {"disparity": d}


def _sam_runner(rgb, prompts):
    out = []
    for pr in prompts:
        m = np.zeros(rgb.shape[:2], np.float32)
        m[50:100, 40:70] = 1.0
        m[5:7, 190:193] = 1.0                    # a stray island SAM sometimes adds far away
        out.append({"mask": m, "score": 0.93})
    return out


def _lama_runner(img, mask):
    out = img.copy()
    out[mask > 0] = (200, 0, 200)                # a fill nobody could mistake for the picture
    return out


SEEN = {"objects": [{"id": "man", "points": [[0.27, 0.6]]}],
        "lights": [{"id": "flame", "kind": "fire", "point": [0.76, 0.6], "radius": 0.05}],
        "depth_checks": [{"near": [0.5, 0.95], "far": [0.5, 0.2]}, {"near": [0.27, 0.6], "far": [0.5, 0.2]}]}


def test_depth_is_full_size_normalised_and_not_blurred():
    rgb = np.zeros((H, W, 3), np.uint8)
    r = U.estimate_depth(rgb, "da_v2_small", runner=_depth_runner)
    assert r["depth"].shape == (H, W)
    assert 0.0 <= r["depth"].min() and r["depth"].max() <= 1.0
    # a step in the model's output stays a step (cubic resize only): no Gaussian softening as in production/depth.py
    col = r["depth"][:, int(0.27 * W)]
    assert np.abs(np.diff(col)).max() > 0.1


def test_depth_checks_count_the_directors_pairs():
    d = U.estimate_depth(np.zeros((H, W, 3), np.uint8), "da_v2_small", runner=_depth_runner)["depth"]
    c = U.depth_checks(d, SEEN["depth_checks"])
    assert (c["right"], c["of"]) == (2, 2)
    flipped = U.depth_checks(1 - d, SEEN["depth_checks"])
    assert flipped["right"] == 0


def test_clean_mask_drops_stray_islands_and_keeps_the_pointed_part():
    m = np.zeros((H, W), np.float32)
    m[50:100, 40:70] = 1
    m[5:7, 190:193] = 1
    m[70:72, 50:52] = 0                          # a pin hole inside the man
    out = U.clean_mask(m, [[55, 75]])
    assert out[6, 191] == 0 and out[60, 50] == 1 and out[71, 51] == 1


def test_birefnet_only_redraws_the_edge_band():
    rgb = np.zeros((H, W, 3), np.uint8)
    coarse = np.zeros((H, W), np.float32)
    coarse[40:80, 60:120] = 1
    out = U.refine_fine_edges(rgb, coarse, runner=lambda crop: np.zeros(crop.shape[:2], np.float32))
    assert out[60, 90] == 1.0                    # deep inside: SAM's decision stays
    assert out[40, 90] == 0.0                    # on the edge band: BiRefNet's (here: nothing)
    assert out[5, 5] == 0.0                      # far outside: never added


def test_light_mask_takes_the_warm_core_inside_the_disc():
    _, img = _picture_tmp()
    m = U.light_mask(img, (0.76, 0.6), 0.05, "fire")
    assert m[73, 152] > 0.5
    assert m[73, 120] < 0.05 and m[20, 152] < 0.05


def _picture_tmp():
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (70, 90, 140)
    img[70:76, 150:154] = (255, 200, 60)
    return None, img


def test_clean_plate_replaces_only_the_hole():
    img = np.full((H, W, 3), 100, np.uint8)
    hole = np.zeros((H, W), np.uint8)
    hole[50:70, 80:100] = 1
    plate, tiles = U.clean_plate(img, hole, runner=_lama_runner)
    assert tiles
    assert tuple(plate[60, 90]) == (200, 0, 200)
    far = plate[:30, :30]
    assert (far == 100).all()


def test_understand_writes_scene_layers_and_reuses_the_cache(tmp_path):
    p, _ = _picture(tmp_path)
    runners = {"da_v2_small": _depth_runner, "sam": _sam_runner, "lama": _lama_runner}
    man = U.understand(p, SEEN, runners=runners)
    assert man["schema"] == "scene_layers/1" and man["depth"]["bits"] == 16 and man["depth"]["blur_px"] == 0
    assert man["picture_sha256"] == U.sha256_file(p)
    folder = U.layers_dir(p)
    for f in ("depth.png", "plate.png", "hole.png", "masks/man.png", "lights/flame.png", "manifest.json"):
        assert (folder / f).exists(), f
    L = U.load(folder)
    assert L["masks"]["man"][6, 191] == 0        # the stray island was cleaned
    assert L["depth"].dtype == np.float32 and L["depth"].shape == (H, W)
    assert man["masks"]["objects"][0]["depth_median"] > 0.8
    calls = []
    U.understand(p, SEEN, runners={"da_v2_small": lambda rgb: calls.append(1) or _depth_runner(rgb), "sam": _sam_runner,
                                   "lama": _lama_runner})
    assert not calls                              # same picture + same prompts: cached
    seen2 = json.loads(json.dumps(SEEN))
    seen2["objects"][0]["points"] = [[0.3, 0.6]]
    sam_calls = []
    U.understand(p, seen2, runners={"da_v2_small": lambda rgb: calls.append(1) or _depth_runner(rgb),
                                    "sam": lambda rgb, pr: sam_calls.append(1) or _sam_runner(rgb, pr), "lama": _lama_runner})
    assert sam_calls and not calls                # new prompts: the mask is made again, the depth of the same picture is reused


def test_edge_alignment_prefers_steps_on_the_object_outline():
    mask = np.zeros((H, W), np.float32)
    mask[40:80, 60:120] = 1
    sharp = np.where(mask > 0, 0.9, 0.2).astype(np.float32)
    import cv2
    soft = cv2.GaussianBlur(sharp, (0, 0), 6)
    assert U.edge_alignment(sharp, {"o": mask}) > U.edge_alignment(soft, {"o": mask})


def test_each_unites_one_prompt_per_point_and_unchanged_masks_are_reused(tmp_path):
    p, _ = _picture(tmp_path)
    seen_prompts = []

    def sam(rgb, prompts):
        seen_prompts.extend(prompts)
        out = []
        for pr in prompts:
            m = np.zeros(rgb.shape[:2], np.float32)
            x, y = map(int, pr["points"][0])
            m[max(0, y - 5):y + 5, max(0, x - 5):x + 5] = 1.0
            out.append({"mask": m, "score": 0.9})
        return out
    seen = {"objects": [{"id": "row", "points": [[0.2, 0.5], [0.6, 0.5]], "each": True}], "lights": []}
    runners = {"da_v2_small": _depth_runner, "sam": sam, "lama": _lama_runner}
    U.understand(p, seen, runners=runners)
    assert len(seen_prompts) == 2                  # one prompt per point
    m = U.load(U.layers_dir(p))["masks"]["row"]
    assert m[60, 40] == 1 and m[60, 120] == 1      # both parts in the one mask
    seen_prompts.clear()
    seen2 = dict(seen, lights=[{"id": "flame", "kind": "fire", "point": [0.76, 0.6], "radius": 0.05}])
    depth_calls = []
    man = U.understand(p, seen2, runners=dict(runners, da_v2_small=lambda rgb: depth_calls.append(1) or _depth_runner(rgb)))
    assert not seen_prompts and not depth_calls    # only the lights changed: masks and depth are reused
    assert man["masks"]["objects"][0]["reused"] is True


def test_a_candle_mask_keeps_its_white_core():
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (40, 30, 30)
    img[60:80, 140:156] = (255, 170, 40)          # warm outer flame
    img[64:76, 144:152] = (250, 250, 245)         # white-hot core, no saturation
    m = U.light_mask(img, (148 / W, 70 / H), 0.06, "candle")
    assert m[70, 148] > 0.9                        # the core is in the flame, not a hole in a ring
