"""Collision-free HUD placement and colour-blind contrast utilities (G-04a)."""

from __future__ import annotations

from collections.abc import Sequence

Box = tuple[float, float, float, float]
RGB = tuple[int, int, int]

DEFAULT_AVOID_MARGIN: float = 8.0
DEFAULT_SAFE_MARGIN: float = 48.0
DEFAULT_MIN_CONTRAST_RATIO: float = 3.0
DEFAULT_MIN_DELTA_E: float = 20.0
DEFAULT_CORNER_PREFERENCE: tuple[str, ...] = (
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
)

OKABE_ITO: dict[str, RGB] = {
    "black": (0, 0, 0),
    "orange": (230, 159, 0),
    "sky_blue": (86, 180, 233),
    "bluish_green": (0, 158, 115),
    "yellow": (240, 228, 66),
    "blue": (0, 114, 178),
    "vermillion": (213, 94, 0),
    "reddish_purple": (204, 121, 167),
}

# Machado, Oliveira & Fernandes (2009), severity 1.0 linear-RGB matrices.
_MACHADO_2009_SEVERITY_1: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

# sRGB (D65) -> CIE XYZ (D65)
_SRGB_TO_XYZ: tuple[tuple[float, float, float], ...] = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)

# CIE D65 reference white point
_D65_WHITE_XYZ: tuple[float, float, float] = (0.95047, 1.00000, 1.08883)


class HudLayoutError(Exception):
    """Raised when a HUD element cannot be placed without collisions."""


def boxes_overlap(a: Box, b: Box, margin: float = 0.0) -> bool:
    """Return True if the axis-aligned gap between boxes `a` and `b` is strictly < `margin`."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    gap_x = max(ax0 - bx1, bx0 - ax1)
    gap_y = max(ay0 - by1, by0 - ay1)
    return max(gap_x, gap_y) < margin


def place_counter(
    frame: tuple[int, int],
    counter_size: tuple[float, float],
    avoid: Sequence[Box],
    prefer: Sequence[str] = DEFAULT_CORNER_PREFERENCE,
    safe_margin: float = DEFAULT_SAFE_MARGIN,
) -> Box:
    """Place a counter box in the first preferred corner that fits inside safe margins and avoids obstacles."""
    frame_w, frame_h = float(frame[0]), float(frame[1])
    box_w, box_h = float(counter_size[0]), float(counter_size[1])
    margin = float(safe_margin)

    inner_x0 = margin
    inner_y0 = margin
    inner_x1 = frame_w - margin
    inner_y1 = frame_h - margin

    candidates: dict[str, Box] = {
        "top_left": (inner_x0, inner_y0, inner_x0 + box_w, inner_y0 + box_h),
        "top_right": (inner_x1 - box_w, inner_y0, inner_x1, inner_y0 + box_h),
        "bottom_left": (inner_x0, inner_y1 - box_h, inner_x0 + box_w, inner_y1),
        "bottom_right": (inner_x1 - box_w, inner_y1 - box_h, inner_x1, inner_y1),
    }

    for corner in prefer:
        if corner not in candidates:
            raise ValueError(f"Unknown corner preference: {corner!r}")
        cand = candidates[corner]
        x0, y0, x1, y1 = cand
        if x0 < inner_x0 or y0 < inner_y0 or x1 > inner_x1 or y1 > inner_y1:
            continue
        if any(boxes_overlap(cand, obstacle, margin=DEFAULT_AVOID_MARGIN) for obstacle in avoid):
            continue
        return (float(x0), float(y0), float(x1), float(y1))

    raise HudLayoutError("no free slot")


def _srgb_channel_to_linear(channel: int) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb_channel(linear: float) -> int:
    clamped = min(1.0, max(0.0, linear))
    if clamped <= 0.0031308:
        srgb = 12.92 * clamped
    else:
        srgb = 1.055 * (clamped ** (1.0 / 2.4)) - 0.055
    return int(round(min(1.0, max(0.0, srgb)) * 255.0))


def _relative_luminance(rgb: RGB) -> float:
    r = _srgb_channel_to_linear(rgb[0])
    g = _srgb_channel_to_linear(rgb[1])
    b = _srgb_channel_to_linear(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: RGB, bg: RGB) -> float:
    """Compute WCAG 2.1 contrast ratio between `fg` and `bg`."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def simulate_cvd(rgb: RGB, kind: str) -> RGB:
    """Simulate colour vision deficiency using Machado 2009 severity 1.0 matrices on linear RGB."""
    if kind not in _MACHADO_2009_SEVERITY_1:
        raise ValueError(f"Unsupported CVD simulation kind: {kind!r}")
    matrix = _MACHADO_2009_SEVERITY_1[kind]
    lr = _srgb_channel_to_linear(rgb[0])
    lg = _srgb_channel_to_linear(rgb[1])
    lb = _srgb_channel_to_linear(rgb[2])

    sim_r = matrix[0][0] * lr + matrix[0][1] * lg + matrix[0][2] * lb
    sim_g = matrix[1][0] * lr + matrix[1][1] * lg + matrix[1][2] * lb
    sim_b = matrix[2][0] * lr + matrix[2][1] * lg + matrix[2][2] * lb

    return (
        _linear_to_srgb_channel(sim_r),
        _linear_to_srgb_channel(sim_g),
        _linear_to_srgb_channel(sim_b),
    )


def _rgb_to_lab(rgb: RGB) -> tuple[float, float, float]:
    lr = _srgb_channel_to_linear(rgb[0])
    lg = _srgb_channel_to_linear(rgb[1])
    lb = _srgb_channel_to_linear(rgb[2])

    x = _SRGB_TO_XYZ[0][0] * lr + _SRGB_TO_XYZ[0][1] * lg + _SRGB_TO_XYZ[0][2] * lb
    y = _SRGB_TO_XYZ[1][0] * lr + _SRGB_TO_XYZ[1][1] * lg + _SRGB_TO_XYZ[1][2] * lb
    z = _SRGB_TO_XYZ[2][0] * lr + _SRGB_TO_XYZ[2][1] * lg + _SRGB_TO_XYZ[2][2] * lb

    def _f(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta ** 3:
            return t ** (1.0 / 3.0)
        return t / (3.0 * delta * delta) + (4.0 / 29.0)

    fx = _f(x / _D65_WHITE_XYZ[0])
    fy = _f(y / _D65_WHITE_XYZ[1])
    fz = _f(z / _D65_WHITE_XYZ[2])

    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)
    return (l_star, a_star, b_star)


def _delta_e_cie76(c1: RGB, c2: RGB) -> float:
    l1, a1, b1 = _rgb_to_lab(c1)
    l2, a2, b2 = _rgb_to_lab(c2)
    return ((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5


def check_palette(
    colors: dict[str, RGB],
    bg: RGB,
    min_ratio: float = DEFAULT_MIN_CONTRAST_RATIO,
    min_delta_e: float = DEFAULT_MIN_DELTA_E,
) -> list[str]:
    """Validate foreground contrast against `bg` and pairwise CVD distinguishability."""
    problems: list[str] = []

    for name, rgb in colors.items():
        ratio = contrast_ratio(rgb, bg)
        if ratio < min_ratio:
            problems.append(
                f"Low contrast for {name!r}: {ratio:.2f} < {min_ratio:.2f}"
            )

    items = list(colors.items())
    cvd_kinds = ("protanopia", "deuteranopia", "tritanopia")

    for idx_a in range(len(items)):
        name_a, rgb_a = items[idx_a]
        for idx_b in range(idx_a + 1, len(items)):
            name_b, rgb_b = items[idx_b]
            for kind in cvd_kinds:
                sim_a = simulate_cvd(rgb_a, kind)
                sim_b = simulate_cvd(rgb_b, kind)
                de = _delta_e_cie76(sim_a, sim_b)
                if de < min_delta_e:
                    problems.append(
                        f"Low {kind} separation between {name_a!r} and {name_b!r}: "
                        f"deltaE {de:.2f} < {min_delta_e:.2f}"
                    )
                    break

    return problems
