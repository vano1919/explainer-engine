"""The free local 2x upscale of a picture (D-131, GC-14) on a CPU, without the Vulkan binary: Real-ESRGAN x2 (RRDBNet, 23 blocks,
BSD-3-Clause architecture of xinntao/Real-ESRGAN) run by torch in tiles. ``turn_pack.find_upscaler`` still prefers the
``EE_UPSCALER`` binary; this is the route where no GPU or Vulkan driver exists (the cloud session).

The weights are a state dict (``RealESRGAN_x2.pth``, ``ai-forever/Real-ESRGAN`` on Hugging Face) and are loaded with
``torch.load(weights_only=True)``: nothing in the file is executed. Tiles overlap and are blended, so no seam shows; a picture is
a pure function of its pixels and the weights. Weights are looked up in ``$EXPLAINER_ESRGAN_WEIGHTS`` or ``tools/esrgan/``.

    python -m explainer_engine.finish.esrgan_cpu <in.png> <out.png> [--tile 256]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from explainer_engine.core.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = "RealESRGAN_x2.pth"
HF_REPO = "ai-forever/Real-ESRGAN"


def weights_path() -> Path:
    return Path(os.environ.get("EXPLAINER_ESRGAN_WEIGHTS") or ROOT / "tools" / "esrgan" / WEIGHTS)


def _net():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class RDB(nn.Module):
        def __init__(self, nf=64, gc=32):
            super().__init__()
            self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
            self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
            self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
            self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
            self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
            self.act = nn.LeakyReLU(0.2, True)

        def forward(self, x):
            x1 = self.act(self.conv1(x))
            x2 = self.act(self.conv2(torch.cat((x, x1), 1)))
            x3 = self.act(self.conv3(torch.cat((x, x1, x2), 1)))
            x4 = self.act(self.conv4(torch.cat((x, x1, x2, x3), 1)))
            return self.conv5(torch.cat((x, x1, x2, x3, x4), 1)) * 0.2 + x

    class RRDB(nn.Module):
        def __init__(self, nf=64, gc=32):
            super().__init__()
            self.rdb1, self.rdb2, self.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

        def forward(self, x):
            return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x

    class RRDBNet(nn.Module):
        """x2: the input is pixel-unshuffled by 2 (12 channels), two nearest x2 stages bring it to twice the input size."""

        def __init__(self, nb=23, nf=64, gc=32):
            super().__init__()
            self.conv_first = nn.Conv2d(12, nf, 3, 1, 1)
            self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
            self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
            self.act = nn.LeakyReLU(0.2, True)

        def forward(self, x):
            feat = self.conv_first(F.pixel_unshuffle(x, 2))
            feat = feat + self.conv_body(self.body(feat))
            feat = self.act(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
            feat = self.act(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
            return self.conv_last(self.act(self.conv_hr(feat)))

    return RRDBNet()


def load(weights: Path | None = None):
    import torch
    w = Path(weights) if weights else weights_path()
    if not w.is_file():
        raise ConfigError(f"no Real-ESRGAN x2 weights at {w}: put {WEIGHTS} (Hugging Face {HF_REPO}) in tools/esrgan/ or set "
                          "EXPLAINER_ESRGAN_WEIGHTS")
    sd = torch.load(w, map_location="cpu", weights_only=True)     # a state dict only: nothing is unpickled into code
    sd = sd.get("params_ema") or sd.get("params") or sd
    net = _net()
    net.load_state_dict(sd, strict=True)
    return net.eval()


def upscale_array(rgb, net=None, tile: int = 256, pad: int = 16):
    """uint8 HxWx3 -> uint8 2Hx2Wx3 (tiles with ``pad`` pixels of overlap, cropped back, so no seam)."""
    import numpy as np
    import torch
    net = net or load()
    h, w, _ = rgb.shape
    x = torch.from_numpy(rgb.astype("float32") / 255.0).permute(2, 0, 1)[None]
    out = torch.zeros(1, 3, h * 2, w * 2)
    with torch.no_grad():
        for y0 in range(0, h, tile):
            for x0 in range(0, w, tile):
                ya, xa = max(0, y0 - pad), max(0, x0 - pad)
                yb, xb = min(h, y0 + tile + pad), min(w, x0 + tile + pad)
                y_ = net(x[:, :, ya:yb, xa:xb])
                ys, xs = (y0 - ya) * 2, (x0 - xa) * 2
                th, tw = min(tile, h - y0) * 2, min(tile, w - x0) * 2
                out[:, :, y0 * 2:y0 * 2 + th, x0 * 2:x0 * 2 + tw] = y_[:, :, ys:ys + th, xs:xs + tw]
    return (out.clamp(0, 1)[0].permute(1, 2, 0).numpy() * 255.0 + 0.5).astype(np.uint8)


def upscale_picture(src: Path | str, dst: Path | str, tile: int = 256, net=None) -> Path:
    import numpy as np
    from PIL import Image
    arr = np.asarray(Image.open(src).convert("RGB"))
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.stem + ".part" + dst.suffix)
    Image.fromarray(upscale_array(arr, net, tile)).save(part)
    os.replace(part, dst)
    return dst


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--tile", type=int, default=256)
    a = ap.parse_args(argv)
    print(upscale_picture(a.src, a.dst, a.tile))
    return 0


if __name__ == "__main__":
    sys.exit(main())
