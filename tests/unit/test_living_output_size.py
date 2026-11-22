import numpy as np

from explainer_engine.fx25d import living


def test_output_size_constants_and_helper():
    assert living.W_OUT == 1920
    assert living.H_OUT == 1080
    assert living.OUT_SIZE == "1920x1080"
    frame = np.zeros((living.H, living.W, 3), np.uint8)
    out = living.output_size_frame(frame)
    assert out.shape == (living.H_OUT, living.W_OUT, 3)
    # run() builds the ffmpeg -s argument inline; no function builds the command, so this test checks the helper and
    # the OUT_SIZE constant that run() passes to ffmpeg. ffmpeg is not run here.


def test_output_size_frame_accepts_bool_mask():
    mask = np.zeros((living.H, living.W), bool)
    out = living.output_size_frame(mask)
    assert out.shape == (living.H_OUT, living.W_OUT)


def test_output_size_frame_accepts_float16_mask():
    mask = np.zeros((living.H, living.W), np.float16)
    out = living.output_size_frame(mask)
    assert out.shape == (living.H_OUT, living.W_OUT)
