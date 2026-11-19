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
