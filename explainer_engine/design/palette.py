"""Colour tokens and WCAG contrast checks. stdlib only. ``palette.json`` is the single source of the hex values."""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

PALETTE_PATH = Path(__file__).with_name("palette.json")
TEXT_MIN = SR.T("BP-28", "contrast_min")  # WCAG 2.x AA, normal text (BP-28)
LARGE_TEXT_MIN = SR.T("BP-28", "contrast_large_min")  # AA, large text (BP-28's large_px and up)
GRAPHIC_MIN = 3.0       # AA 1.4.11, meaningful graphics


def load(path: Path = PALETTE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# Machado, Oliveira and Fernandes 2009, severity 1.0, applied to linear RGB
CVD = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _rgb_linear(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))  # type: ignore[return-value]


def _lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(v: float) -> float:
        return v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str, vision: str | None = None) -> float:
    """CIE76 distance of two hex colours, as seen by a colour-blind viewer when ``vision`` is protan, deutan or tritan."""
    pair = []
    for h in (a, b):
        rgb = _rgb_linear(h)
        if vision:
            m = CVD[vision]
            rgb = tuple(min(1.0, max(0.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3))  # type: ignore[assignment]
        pair.append(_lab(rgb))
    return sum((p - q) ** 2 for p, q in zip(*pair)) ** 0.5


def faction_findings(palette: dict | None = None) -> list[dict]:
    """BP-151: every faction pair stays apart for all three colour-blind simulations and is told apart by a mark (REVIEW)."""
    pal = palette or load()
    hexes = {name: t["hex"] for name, t in pal["tokens"].items()}
    need, out = SR.T("BP-151", "faction_delta_e_min"), []
    for pair in pal.get("faction_pairs", []):
        a, b = hexes[pair["a"]], hexes[pair["b"]]
        if not pair.get("mark_a") or pair.get("mark_a") == pair.get("mark_b"):
            out.append({"check": "faction_mark", "detail": f"{pair['a']}/{pair['b']} need two different marks (never colour alone)"})
        for vision in CVD:
            d = delta_e(a, b, vision)
            if d < need:
                out.append({"check": "faction_cvd", "detail": f"{pair['a']}/{pair['b']} are {d:.0f} apart for {vision} viewers (< {need})"})
    return out


def check(palette: dict | None = None) -> list[dict]:
    """Findings for every rule the palette file states about itself (empty = consistent)."""
    pal = palette or load()
    hexes = {name: t["hex"] for name, t in pal["tokens"].items()}
    findings = []

    def add(check_id: str, detail: str) -> None:
        findings.append({"check": check_id, "detail": detail})

    for name, h in hexes.items():
        if len(h) != 7 or not h.startswith("#"):
            add("hex_format", f"{name}: {h!r} is not #RRGGBB")
    for pair in pal["text_pairs"]:
        ratio = contrast(hexes[pair["text"]], hexes[pair["on"]])
        if ratio < TEXT_MIN:
            add("text_contrast", f"{pair['text']} on {pair['on']} is {ratio:.2f}:1 (< {TEXT_MIN})")
    for pair in pal["large_text_only"]:
        ratio = contrast(hexes[pair["text"]], hexes[pair["on"]])
        if not LARGE_TEXT_MIN <= ratio < TEXT_MIN:
            add("large_text_class", f"{pair['text']} on {pair['on']} is {ratio:.2f}:1: not a large-text-only pair")
    listed = {(p["text"], p["on"]) for p in pal["text_pairs"] + pal["large_text_only"]}
    for name in pal["fill_only"]:
        if contrast(hexes[name], hexes["paper"]) >= GRAPHIC_MIN and name != "false_red":
            continue
        if ("ink", name) not in listed:
            add("fill_only_text", f"{name} is fill-only on paper but has no ink text pair")
    findings += faction_findings(pal)
    return findings


def report(palette: dict | None = None) -> str:
    pal = palette or load()
    hexes = {name: t["hex"] for name, t in pal["tokens"].items()}
    rows = ["| token | vs paper | vs ink | vs night |", "|---|---|---|---|"]
    for name, h in hexes.items():
        rows.append(f"| `{name}` | {contrast(h, hexes['paper']):.2f} | {contrast(h, hexes['ink']):.2f} | "
                    f"{contrast(h, hexes['night']):.2f} |")
    return "\n".join(rows)


if __name__ == "__main__":  # python -m explainer_engine.design.palette
    print(report())
    problems = check()
    for p in problems:
        print("FAIL", p["check"], p["detail"])
    raise SystemExit(1 if problems else 0)
