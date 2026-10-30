"""Canvas.line's dashed walk always terminates (explainer_engine/maps/draw.py): the float floor, the guards and the box bound."""

from __future__ import annotations

import itertools
import math
import signal
import time

import numpy as np
import pytest

from explainer_engine.maps import draw as D

needs_alarm = pytest.mark.skipif(not hasattr(signal, "setitimer"), reason="no SIGALRM on this platform")

# found by search: with no floor the walk stalls (pos + step == pos) on this pattern
STALL = (2.2872328120450134, 3.173234010681308, 100.0)
BOX = (-10.0, -10.0, 1e6, 1e6)


class Spin(Exception):
    pass


def within(seconds: float, fn):
    def fire(*_):
        raise Spin()
    old = signal.signal(signal.SIGALRM, fire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@needs_alarm
def test_the_float_floor_is_what_keeps_the_walk_moving(monkeypatch):
    on, off, length = STALL
    pts = [(0.0, 0.0), (length, 0.0)]
    runs = within(5, lambda: list(D.dash_runs(pts, on, off, BOX)))
    assert 15 < len(runs) < 30                                    # about 100 / 5.46 dashes
    monkeypatch.setattr(D, "DASH_FLOOR", 0.0)                     # the same input without the floor stalls: the case is real
    with pytest.raises(Spin):
        within(2, lambda: list(D.dash_runs(pts, on, off, BOX)))


def test_a_dash_of_zero_negative_or_non_finite_is_refused():
    c = D.Canvas(40, 20, (255, 255, 255), 1)
    for bad in ((0, 0), (-3, 2), (3, -1), (math.nan, 2), (3, math.inf), (1e-9, -1e-9)):
        with pytest.raises(ValueError):
            c.line([(0, 5), (30, 5)], (0, 0, 0, 255), 2, dash=bad)


def test_non_finite_coordinates_are_refused_on_a_dashed_line():
    c = D.Canvas(40, 20, (255, 255, 255), 1)
    for pts in ([(0, 0), (math.inf, 5)], [(0, 0), (math.nan, 5)], [(-math.inf, 0), (5, 5)]):
        with pytest.raises(ValueError):
            c.line(pts, (0, 0, 0, 255), 2, dash=(4, 3))


@needs_alarm
def test_a_hugely_long_line_costs_the_box_not_the_length():
    c = D.Canvas(80, 20, (255, 255, 255), 1)
    t = time.perf_counter()
    within(5, lambda: c.line([(-1e12, 10), (1e12, 10)], (0, 0, 0, 255), 2, dash=(4, 3)))
    within(5, lambda: c.line([(0, 0), (1e12, 1e12)], (0, 0, 0, 255), 2, dash=(4, 3)))
    assert time.perf_counter() - t < 2.0
    row = np.asarray(c.image().convert("L"))[10]
    assert 0.3 < (row < 128).mean() < 0.8                        # the visible part is dashed


@needs_alarm
def test_a_sub_pixel_dash_is_a_solid_line_and_ends_quickly():
    c = D.Canvas(80, 20, (255, 255, 255), 1)
    within(5, lambda: c.line([(0, 10), (79, 10)], (0, 0, 0, 255), 2, dash=(1e-9, 1e-9)))
    assert (np.asarray(c.image().convert("L"))[10, 2:78] < 128).all()


def test_the_phase_still_advances_over_the_part_outside_the_box():
    inside = list(D.dash_runs([(0.0, 5.0), (100.0, 5.0)], 4.0, 3.0, (0.0, 0.0, 100.0, 10.0)))
    shifted = list(D.dash_runs([(-70.0, 5.0), (100.0, 5.0)], 4.0, 3.0, (0.0, 0.0, 100.0, 10.0)))
    assert inside[0][0][0] == 0.0
    assert shifted[0][0][0] == pytest.approx(0.0, abs=1e-9)      # 70 = 10 periods: the pattern lands in phase
    odd = list(D.dash_runs([(-71.0, 5.0), (100.0, 5.0)], 4.0, 3.0, (0.0, 0.0, 100.0, 10.0)))
    assert odd[0][0][0] == pytest.approx(0.0, abs=1e-9) and odd[0][1][0] == pytest.approx(3.0, abs=1e-9)   # one unit into the dash
