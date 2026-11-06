"""The J5 variant sheet: one layout constant, the cut, the alignment (translation and scale, recovered to a pixel on a synthetic sheet made
of the painted mouth), the per-cell checks and the swap that leaves everything outside the mask alone."""
import numpy as np
import pytest

from explainer_engine.blender import j5_face as F
from explainer_engine.blender import j5_variant_sheet as V

FEAT = F.FEATURES["B_H1_left34"]


def head_sheet():
    rng = np.random.default_rng(5)
    sheet = (rng.random((704, 1280, 3)) * 40 + 90).astype(np.uint8)
    import cv2
    sheet = cv2.GaussianBlur(sheet, (0, 0), 2.0)                        # a textured, smooth-ish stand-in for a painted sheet
    x0, y0, s = V.head_window(FEAT)
    yy, xx = np.mgrid[y0:y0 + s, x0:x0 + s]
    sheet[y0:y0 + s, x0:x0 + s, 0] = np.clip(sheet[y0:y0 + s, x0:x0 + s, 0] + 60 * np.sin(xx / 9.0) * np.cos(yy / 7.0), 0, 255)
    return sheet


def test_layout_constant_is_consistent_and_cells_do_not_overlap():
    assert len(V.ORDER) == V.COLS * V.ROWS == 8 and V.ORDER[:6] == ("A", "B", "C", "D", "E", "F") and V.ORDER[6:] == ("blink_half", "blink_full")
    assert V.SHEET_SIZE == (2208, 1120) and all(n % 16 == 0 for n in V.SHEET_SIZE)
    boxes = [V.cell_box(i) for i in range(8)]
    assert boxes[0][:2] == (V.MARGIN, V.MARGIN) and boxes[7][2:] == (V.SHEET_SIZE[0] - V.MARGIN, V.SHEET_SIZE[1] - V.MARGIN)
    for i, a in enumerate(boxes):
        assert a[2] - a[0] == V.CELL[0] and a[3] - a[1] == V.CELL[1]
        for b in boxes[i + 1:]:
            assert a[2] + V.GUTTER <= b[0] or b[2] + V.GUTTER <= a[0] or a[3] + V.GUTTER <= b[1] or b[3] + V.GUTTER <= a[1]
    assert V.IN_NAME.format(hero="H1") == "H1__variants_in.png" and V.OUT_NAME.format(hero="H1") == "H1__variants.png"


def test_input_sheet_cuts_back_into_eight_identical_heads():
    sheet = head_sheet()
    ins = V.build_input_sheet(sheet, FEAT)
    assert ins.shape == (1120, 2208, 3)
    cells = V.cut_cells(ins)
    assert list(cells) == list(V.ORDER) and all(np.array_equal(cells["A"], c) for c in cells.values())
    with pytest.raises(ValueError):
        V.cut_cells(ins[:-16])


@pytest.mark.parametrize("scale,dx,dy", [(1.0, 0, 0), (1.03, 6, -4), (0.97, -9, 7)])
def test_alignment_recovers_a_known_shift_and_scale(scale, dx, dy):
    import cv2
    ref = V.cut_cells(V.build_input_sheet(head_sheet(), FEAT))["A"]
    h = ref.shape[0]
    M = np.array([[scale, 0, (1 - scale) * h / 2 + dx], [0, scale, (1 - scale) * h / 2 + dy]], np.float32)
    moved = cv2.warpAffine(ref, M, (h, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    r = V.align(ref, moved)
    assert abs(r["scale"] - 1 / scale) < 0.02 and r["score"] > 0.9
    assert r["reg_error_px"] < 1.0
    back = np.abs(r["aligned"][80:-80, 80:-80].astype(int) - ref[80:-80, 80:-80].astype(int)).mean()
    assert back < 6.0


def test_check_cell_flags_a_redrawn_face_and_accepts_a_changed_mouth():
    sheet = head_sheet()
    ref = V.cut_cells(V.build_input_sheet(sheet, FEAT))["A"]
    import cv2
    x0, y0, side = V.head_window(FEAT)
    part = cv2.resize(V.moving_mask(FEAT, 'mouth')[y0:y0 + side, x0:x0 + side], V.CELL) > 0.5
    mouth_changed = ref.copy()
    mouth_changed[part] = (30, 10, 10)                                                    # a dark mouth, inside the moving part only
    assert V.check_cell(ref, mouth_changed, FEAT)["identity"] > 0.97
    rng = np.random.default_rng(9)
    other = np.clip(ref.astype(int) + rng.normal(0, 40, ref.shape), 0, 255).astype(np.uint8)
    other[:200] = rng.integers(0, 255, other[:200].shape, dtype=np.uint8)                # a different face
    assert V.check_cell(ref, other, FEAT)["identity"] < 0.9


def test_variant_sheet_changes_only_the_masked_part_and_blend_follows_the_weights():
    sheet = head_sheet()
    ref = V.cut_cells(V.build_input_sheet(sheet, FEAT))["A"]
    hole = V.cell_hole(FEAT)
    open_cell = ref.copy()
    open_cell[hole] = (20, 5, 5)
    vs = V.variant_sheets(sheet, {"C": open_cell}, FEAT)
    m = V.moving_mask(FEAT, "mouth")
    assert (vs["C"][m <= 0] == sheet[m <= 0]).all() and (vs["C"] != sheet).any()
    half = V.blend_sheet(sheet, vs, {"A": 0.5, "C": 0.5})
    full = V.blend_sheet(sheet, vs, {"C": 1.0})
    assert np.array_equal(full, vs["C"]) and np.abs(half.astype(int) - sheet.astype(int)).max() <= np.abs(full.astype(int) - sheet.astype(int)).max() / 2 + 1
