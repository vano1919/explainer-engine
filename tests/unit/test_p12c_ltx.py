"""WP-1a2: every LTX module of p12c_ltx.py is resolved (no PLACEHOLDER), names a file of the e98f6d9 listing, and the L1/L3
command uses the distilled pipeline with only flags its parser declares. No network, no GPU, no pod."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "explainer_engine" / "training" / "pods" / "p12"
LISTING = ROOT / "jobs" / "ltx2_src" / "listing.txt"
SRC = "packages/ltx-pipelines/src/"


def _load():
    spec = importlib.util.spec_from_file_location("p12c_ltx_under_test", DIR / "p12c_ltx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _cfg():
    return {"ltx": {
        "local": "ltx",
        "files": ["transformer/distilled-transformer.safetensors", "text_encoders/gemma.safetensors",
                  "vae/video-vae.safetensors", "vae/audio-vae.safetensors", "latent_upscale_models/x2.safetensors"],
        "av_files": [],
        "layout_lora": {"file": "loras/layout.safetensors"},
        "render": {"width": 1408, "height": 800, "frames": 121, "fps": 24, "seed": 7},
    }}


def test_flags_resolved():
    m = _load()
    assert set(m.CMDS) <= set(m.MODULES)
    listing = set(LISTING.read_text(encoding="utf-8").split())
    for kind, mod in m.MODULES.items():
        assert mod and "PLACEHOLDER" not in mod.upper(), kind
        assert SRC + mod.replace(".", "/") + ".py" in listing, (kind, mod)
    assert m.MODULES["ltx_i2v"] == "ltx_pipelines.distilled"
    for key, flag in m.FLAGS.items():
        assert flag is None or flag.startswith("--"), key

    cmd = [str(c) for c in m.cmd_ltx_i2v(_cfg(), "s01", {"image": "/x/s01.png", "prompt": "p", "out": "/x/s01_i2v.mp4"})]
    assert cmd[1:3] == ["-m", "ltx_pipelines.distilled"]
    i = cmd.index("--image")
    assert cmd[i + 1:i + 4] == ["/x/s01.png", "0", "1.0"]
    for key in ("transformer", "prompt", "output", "upsampler", "num_frames", "text_encoder", "video_vae", "audio_vae"):
        assert m.FLAGS[key] in cmd, key
    # The distilled parser (args.py:1590) has no --distilled-lora, --video-conditioning or --audio-path.
    for key in ("distilled_lora", "video_cond", "audio", "audio_max", "stage2_ic"):
        assert m.FLAGS[key] not in cmd, key
    assert "--quantization=fp8-cast" in cmd
