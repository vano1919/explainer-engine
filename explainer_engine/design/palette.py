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
