# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/design/palette.py`
# Target Module : explainer_engine/design/palette.py
# Target Classes/Symbols : def load(), def _linear(), def luminance(), def contrast(), def _rgb_linear(), def _lab(), def delta_e(), def faction_findings(), def check(), def report()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
        if not pair.get("mark_a") or not pair.get("mark_b") or pair.get("mark_a") == pair.get("mark_b"):
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
