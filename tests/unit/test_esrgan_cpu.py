"""The free local 2x picture upscale on a CPU (D-131, GC-14): the network has the shape of Real-ESRGAN x2, tiles give the size
of the whole, weights are loaded as a state dict only, and a missing weights file says where to put it."""
from __future__ import annotations

import pickle

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from explainer_engine.core.errors import ConfigError
from explainer_engine.finish import esrgan_cpu as E


def test_the_network_doubles_the_size_and_tiles_keep_it():
    torch.manual_seed(0)
    net = E._net().eval()
    rgb = (np.random.default_rng(1).random((40, 56, 3)) * 255).astype(np.uint8)
    whole = E.upscale_array(rgb, net, tile=64)
    tiled = E.upscale_array(rgb, net, tile=24, pad=8)
    assert whole.shape == tiled.shape == (80, 112, 3) and whole.dtype == np.uint8
    assert (E.upscale_array(rgb, net, tile=24, pad=8) == tiled).all()    # the same pixels twice


def test_the_state_dict_keys_are_those_of_the_released_x2_weights():
    keys = set(E._net().state_dict())
    assert {"conv_first.weight", "body.0.rdb1.conv1.weight", "body.22.rdb3.conv5.bias", "conv_up2.weight", "conv_last.bias"} <= keys
    assert E._net().state_dict()["conv_first.weight"].shape == (64, 12, 3, 3)    # x2 reads the picture pixel-unshuffled by 2


def test_missing_weights_say_where_they_go(tmp_path):
    with pytest.raises(ConfigError, match="tools/esrgan"):
        E.load(tmp_path / "none.pth")


def test_weights_load_as_a_state_dict_and_never_run_code(tmp_path):
    good = tmp_path / "good.pth"
    torch.save({"params_ema": E._net().state_dict()}, good)
    assert isinstance(E.load(good), torch.nn.Module)
    evil = tmp_path / "evil.pth"

    class Boom:
        def __reduce__(self):
            return (eval, ("1+1",))
    evil.write_bytes(pickle.dumps(Boom()))
    with pytest.raises(Exception):    # weights_only refuses anything but tensors and plain containers
        E.load(evil)


def test_the_face_aware_mix_takes_faces_from_lanczos_and_the_rest_from_esrgan():
    from PIL import Image
    rgb = (np.random.default_rng(2).random((60, 80, 3)) * 255).astype(np.uint8)
    esr = np.full((120, 160, 3), 200, np.uint8)
    out, n = E.face_aware_mix(rgb, esr, [{"box": (30.0, 20.0, 50.0, 40.0)}])
    assert n == 1 and out.shape == esr.shape
    assert (out[0:8, 0:8] == 200).all() and (out[112:, 152:] == 200).all()          # far from the face: ESRGAN untouched
    assert abs(int(out[60, 80, 0]) - 200) > 20 or abs(int(out[60, 81, 1]) - 200) > 20   # inside it: Lanczos pixels
    assert len(set(out[60, 40:120, 0].tolist())) > 5                                    # a feathered edge, not a hard box
    none, k = E.face_aware_mix(rgb, esr, [])
    assert k == 0 and (none == 200).all()
