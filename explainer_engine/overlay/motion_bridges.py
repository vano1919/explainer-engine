"""Broadcast YouTube Motion Bridges (GSAP 3.13 + SplitText + DrawSVG + Headless Chrome 24fps RGBA).

Replaces static PIL black rectangles with true broadcast documentary motion graphics:
1. ``kinetic_title_reveal``: Cinzel + Cormorant Garamond SplitText mask reveal + expanding amber DrawSVG hairline.
2. ``geological_timeline``: Frosted obsidian glass timeline bar with animated DrawSVG track + pulsing active era node.
3. ``stat_counter_card``: Tabular JetBrains Mono live-counting stat + DrawSVG radial gauge + Lucide icon.
4. ``callout_spec_pointer``: Glowing radar origin dot + angled DrawSVG leader line + sleek telemetry spec tag.
5. ``split_era_card``: Dual-column documentary comparison card with animated horizontal bars and center hairline.

Renders frame-accurately at 24fps with alpha transparency (``omit_background=True``) via
Playwright Chromium into RGBA MOV/PNG streams and composites cleanly onto 2K footage via FFmpeg.
"""
from __future__ import annotations

import html
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from explainer_engine.design_system.tokens import (
    PALEO_ICE_AGE_THEME,
    build_font_face_css,
    resolve_vendor_js,
)

VALID_MOTION_BRIDGE_TEMPLATES = frozenset(
    {
        "kinetic_title_reveal",
        "geological_timeline",
        "stat_counter_card",
        "callout_spec_pointer",
        "split_era_card",
    }
)


@dataclass(slots=True)
class MotionBridgeSpec:
    bridge_id: str
    template: str
    title: str
    subtitle: str = ""
    start_s: float = 0.0
    duration_s: float = 4.0
    position: str = "bottom_left"  # bottom_left, bottom_center, top_left, center, custom
    accent_color: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.template not in VALID_MOTION_BRIDGE_TEMPLATES:
            raise ValueError(
                f"Unsupported motion bridge template {self.template!r}; "
                f"expected one of {sorted(VALID_MOTION_BRIDGE_TEMPLATES)}"
            )
        if self.duration_s < 1.0:
            raise ValueError(f"Motion bridge duration_s must be >= 1.0s, got {self.duration_s}")


def _build_bridge_html(spec: MotionBridgeSpec, *, width: int, height: int) -> str:
    theme = dict(PALEO_ICE_AGE_THEME)
    accent = spec.accent_color or theme["accent_amber"]
    accent_secondary = str(spec.meta.get("accent_secondary") or theme["accent_glacial"])

    font_css = build_font_face_css(
        [
            "Cinzel",
            "Cormorant Garamond",
            "Plus Jakarta Sans",
            "Space Grotesk",
            "IBM Plex Mono",
            "JetBrains Mono",
        ]
    )
    gsap_uri = resolve_vendor_js("gsap.min.js").as_uri()
    split_uri = resolve_vendor_js("SplitText.min.js").as_uri()
    draw_uri = resolve_vendor_js("DrawSVGPlugin.min.js").as_uri()
    ease_uri = resolve_vendor_js("CustomEase.min.js").as_uri()
    lucide_uri = resolve_vendor_js("lucide.min.js").as_uri()

    # Scale UI proportionally to target canvas height (reference = 1080p)
    scale = height / 1080.0
    safe_title = html.escape(spec.title)
    safe_sub = html.escape(spec.subtitle)
    eyebrow = html.escape(str(spec.meta.get("eyebrow") or "PLEISTOCENE ARCHIVE"))
    icon_name = html.escape(str(spec.meta.get("icon") or "flame"))

    if spec.template == "kinetic_title_reveal":
        body_html = f"""
        <div id="stage" class="stage-center">
          <div class="title-scrim"></div>
          <div class="kinetic-wrap" id="bbox-root">
            <div class="eyebrow mono">{eyebrow}</div>
            <h1 class="hero-title" id="hero-title">{safe_title}</h1>
            <svg class="rule-svg" viewBox="0 0 640 16" fill="none">
              <line id="rule-l" x1="320" y1="8" x2="20" y2="8" stroke="{accent}" stroke-width="1.6" stroke-linecap="round"/>
              <line id="rule-r" x1="320" y1="8" x2="620" y2="8" stroke="{accent}" stroke-width="1.6" stroke-linecap="round"/>
              <polygon id="rule-diamond" points="320,3 326,8 320,13 314,8" fill="{accent}" />
            </svg>
            <p class="hero-sub">{safe_sub}</p>
          </div>
        </div>
        """
    elif spec.template == "geological_timeline":
        stops = spec.meta.get("stops") or [
            {"label": "100,000 BCE", "sub": "Early Dispersal"},
            {"label": "70,000 BCE", "sub": "Toba / Bottleneck", "active": True},
            {"label": "45,000 BCE", "sub": "Ice Age Europe"},
            {"label": "12,000 BCE", "sub": "Holocene Thaw"},
        ]
        badge = html.escape(str(spec.meta.get("badge") or "-6.2°C GLOBAL DROP"))
        stops_html = []
        active_idx = 1
        for i, st in enumerate(stops):
            if st.get("active"):
                active_idx = i
            cls = "tl-stop active" if st.get("active") else "tl-stop"
            stops_html.append(
                f'<div class="{cls}"><div class="tl-dot"></div>'
                f'<div class="tl-lbl mono">{html.escape(str(st.get("label", "")))}</div>'
                f'<div class="tl-sub">{html.escape(str(st.get("sub", "")))}</div></div>'
            )
        active_pct = int(round((active_idx / max(1, len(stops) - 1)) * 100))
        body_html = f"""
        <div id="stage" class="stage-bottom-center">
          <div class="glass-card timeline-card" id="bbox-root">
            <div class="tl-head">
              <div>
                <div class="eyebrow mono">{eyebrow}</div>
                <div class="card-title">{safe_title}</div>
              </div>
              <div class="stat-pill mono"><i data-lucide="snowflake"></i><span>{badge}</span></div>
            </div>
            <div class="tl-track-wrap">
              <svg class="tl-svg" viewBox="0 0 1000 20" preserveAspectRatio="none">
                <line x1="20" y1="10" x2="980" y2="10" stroke="rgba(232,240,248,0.18)" stroke-width="2" />
                <line id="tl-progress" x1="20" y1="10" x2="{20 + int(9.6 * active_pct)}" y2="10" stroke="{accent}" stroke-width="3" stroke-linecap="round" />
              </svg>
              <div class="tl-stops">{''.join(stops_html)}</div>
            </div>
          </div>
        </div>
        """
    elif spec.template == "stat_counter_card":
        start_val = float(spec.meta.get("start_val", 0))
        end_val = float(spec.meta.get("end_val", 300))
        prefix = html.escape(str(spec.meta.get("prefix", "+")))
        suffix = html.escape(str(spec.meta.get("suffix", "%")))
        arc_pct = max(5, min(100, int(spec.meta.get("arc_pct", 78))))
        body_html = f"""
        <div id="stage" class="stage-bottom-left">
          <div class="glass-card stat-card" id="bbox-root"
               data-start="{start_val}" data-end="{end_val}" data-prefix="{prefix}" data-suffix="{suffix}">
            <div class="stat-ring-wrap">
              <svg viewBox="0 0 120 120" class="stat-ring">
                <circle cx="60" cy="60" r="48" stroke="rgba(232,240,248,0.14)" stroke-width="5" fill="none"/>
                <circle id="stat-arc" cx="60" cy="60" r="48" stroke="{accent}" stroke-width="5.5"
                        stroke-linecap="round" fill="none" transform="rotate(-90 60 60)"
                        data-pct="{arc_pct}"/>
              </svg>
              <div class="stat-icon"><i data-lucide="{icon_name}"></i></div>
            </div>
            <div class="stat-body">
              <div class="eyebrow mono">{eyebrow}</div>
              <div class="stat-num mono" id="stat-num">{prefix}{int(start_val)}{suffix}</div>
              <div class="card-title">{safe_title}</div>
              <div class="card-sub">{safe_sub}</div>
            </div>
          </div>
        </div>
        """
    elif spec.template == "callout_spec_pointer":
        anchor_x = int(spec.meta.get("anchor_x_pct", 34))
        anchor_y = int(spec.meta.get("anchor_y_pct", 56))
        spec_val = html.escape(str(spec.meta.get("spec_value") or "1,200°C SPARK"))
        ax = int(1920 * anchor_x / 100.0)
        ay = int(1080 * anchor_y / 100.0)
        ex = min(1450, ax + 190)
        ey = max(180, ay - 135)
        body_html = f"""
        <div id="stage" class="stage-full">
          <svg class="callout-svg" viewBox="0 0 1920 1080" fill="none">
            <circle id="pulse-outer" cx="{ax}" cy="{ay}" r="22" stroke="{accent}" stroke-width="1.5" opacity="0.5"/>
            <circle id="pulse-core" cx="{ax}" cy="{ay}" r="6.5" fill="{accent}"/>
            <polyline id="leader-line" points="{ax},{ay} {ax + 85},{ey} {ex},{ey}"
                      stroke="{accent}" stroke-width="2" fill="none" stroke-linejoin="round"/>
          </svg>
          <div class="glass-card callout-tag" id="bbox-root" style="left:{ex / 19.2:.2f}%; top:{(ey - 54) / 10.8:.2f}%;">
            <div class="callout-corners"></div>
            <div class="eyebrow mono">{eyebrow}</div>
            <div class="callout-val mono">{spec_val}</div>
            <div class="card-title">{safe_title}</div>
            <div class="card-sub">{safe_sub}</div>
          </div>
        </div>
        """
    else:  # split_era_card
        left_lbl = html.escape(str(spec.meta.get("left_label") or "RAW FORAGING"))
        left_val = html.escape(str(spec.meta.get("left_value") or "1,400 kcal / day"))
        left_pct = int(spec.meta.get("left_pct", 36))
        right_lbl = html.escape(str(spec.meta.get("right_label") or "FIRE-COOKED DIET"))
        right_val = html.escape(str(spec.meta.get("right_value") or "3,800+ kcal / day"))
        right_pct = int(spec.meta.get("right_pct", 92))
        stage_cls = "stage-top-center" if spec.position == "top_center" else "stage-bottom-center"
        body_html = f"""
        <div id="stage" class="{stage_cls}">
          <div class="glass-card split-card" id="bbox-root">
            <div class="split-header">
              <div class="eyebrow mono">{eyebrow}</div>
              <div class="card-title">{safe_title}</div>
            </div>
            <div class="split-grid">
              <div class="split-col">
                <div class="split-lbl mono">{left_lbl}</div>
                <div class="split-val">{left_val}</div>
                <div class="bar-bg"><div class="bar-fill bar-cool" id="bar-left" data-w="{left_pct}%"></div></div>
              </div>
              <div class="split-divider"></div>
              <div class="split-col">
                <div class="split-lbl mono accent">{right_lbl}</div>
                <div class="split-val">{right_val}</div>
                <div class="bar-bg"><div class="bar-fill bar-warm" id="bar-right" data-w="{right_pct}%"></div></div>
              </div>
            </div>
          </div>
        </div>
        """

    dur = float(spec.duration_s)
    out_start = max(0.8, dur - 0.55)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: {width}px; height: {height}px; overflow: hidden; background: transparent;
  font-family: {theme["font_sans"]}; color: {theme["text_primary"]};
  -webkit-font-smoothing: antialiased;
}}
#viewport-scale {{
  width: 1920px; height: 1080px;
  transform: scale({scale:.6f});
  transform-origin: top left;
  position: relative;
}}
.mono {{ font-family: {theme["font_mono"]}; font-variant-numeric: tabular-nums; }}
.stage-center {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
.stage-top-center {{ position: absolute; inset: 0; display: flex; align-items: flex-start; justify-content: center; padding-top: 64px; }}
.stage-bottom-center {{ position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 58px; }}
.stage-bottom-left {{ position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: flex-start; padding: 0 0 62px 76px; }}
.stage-full {{ position: absolute; inset: 0; }}

.title-scrim {{
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 76% 46% at 50% 50%, rgba(4,7,13,0.88) 0%, rgba(4,7,13,0.52) 56%, rgba(4,7,13,0.08) 100%);
  opacity: 0;
}}
.kinetic-wrap {{ position: relative; text-align: center; max-width: 1520px; padding: 34px 56px; }}
.eyebrow {{
  font-size: 21px; letter-spacing: 0.24em; text-transform: uppercase;
  color: {accent}; margin-bottom: 14px; font-weight: 600;
  text-shadow: 0 3px 14px rgba(0,0,0,0.95);
}}
.hero-title {{
  font-family: {theme["font_display"]}; font-size: 86px; font-weight: 700;
  letter-spacing: 0.12em; line-height: 1.1; color: #FFFFFF;
  text-shadow: 0 10px 36px rgba(0,0,0,0.98), 0 3px 8px rgba(0,0,0,0.95);
}}
.rule-svg {{ width: 680px; height: 20px; margin: 20px auto 16px; display: block; filter: drop-shadow(0 0 10px {theme["accent_amber_glow"]}); }}
.hero-sub {{
  font-family: {theme["font_editorial"]}; font-style: italic; font-size: 42px; font-weight: 600;
  letter-spacing: 0.03em; color: #EDF2F8;
  text-shadow: 0 5px 22px rgba(0,0,0,0.98), 0 2px 6px rgba(0,0,0,0.95);
}}

.glass-card {{
  position: relative;
  background: linear-gradient(155deg, rgba(9,14,22,0.92) 0%, rgba(5,8,14,0.95) 100%);
  border: 1.5px solid rgba(232,240,248,0.28);
  border-radius: 12px;
  box-shadow: 0 26px 70px rgba(0,0,0,0.82), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(22px);
  overflow: hidden;
}}
.glass-card::before {{
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, {accent} 0%, {accent_secondary} 65%, transparent 100%);
}}
.card-title {{
  font-family: {theme["font_sans"]}; font-size: 33px; font-weight: 700; letter-spacing: -0.01em; color: #FFFFFF;
}}
.card-sub {{
  font-family: {theme["font_sans"]}; font-size: 23px; font-weight: 500; color: #DCE6F2; margin-top: 6px; line-height: 1.3;
}}

.timeline-card {{ width: 1580px; padding: 30px 48px 34px; }}
.tl-head {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 26px; }}
.stat-pill {{
  display: inline-flex; align-items: center; gap: 10px; padding: 11px 22px;
  border-radius: 999px; background: rgba(124,196,232,0.20);
  border: 1.5px solid rgba(124,196,232,0.58); color: #C2E8FA; font-size: 20px; font-weight: 700;
}}
.stat-pill svg {{ width: 22px; height: 22px; stroke: #C2E8FA; }}
.tl-track-wrap {{ position: relative; padding-top: 10px; }}
.tl-svg {{ width: 100%; height: 22px; display: block; filter: drop-shadow(0 0 10px {theme["accent_amber_glow"]}); }}
.tl-stops {{ display: flex; justify-content: space-between; margin-top: -19px; position: relative; z-index: 2; }}
.tl-stop {{ display: flex; flex-direction: column; align-items: center; min-width: 220px; }}
.tl-dot {{
  width: 17px; height: 17px; border-radius: 50%; background: #1B2635;
  border: 2.5px solid rgba(232,240,248,0.65); margin-bottom: 12px;
}}
.tl-stop.active .tl-dot {{
  background: {accent}; border-color: #FFF4E0;
  box-shadow: 0 0 0 7px rgba(227,155,67,0.34), 0 0 20px {accent};
}}
.tl-lbl {{ font-size: 22px; font-weight: 700; color: #FFFFFF; }}
.tl-stop.active .tl-lbl {{ color: {accent}; }}
.tl-sub {{ font-size: 19px; font-weight: 500; color: #DCE6F2; margin-top: 4px; }}

.stat-card {{ display: flex; align-items: center; gap: 32px; padding: 30px 42px; min-width: 720px; }}
.stat-ring-wrap {{ position: relative; width: 132px; height: 132px; flex-shrink: 0; }}
.stat-ring {{ width: 132px; height: 132px; filter: drop-shadow(0 0 12px {theme["accent_amber_glow"]}); }}
.stat-icon {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
.stat-icon svg {{ width: 40px; height: 40px; stroke: {accent}; stroke-width: 1.9; }}
.stat-num {{ font-size: 64px; font-weight: 700; line-height: 1.05; color: #FFFFFF; letter-spacing: -0.02em; margin-bottom: 6px; }}

.callout-svg {{ position: absolute; inset: 0; width: 1920px; height: 1080px; filter: drop-shadow(0 0 8px {theme["accent_amber_glow"]}); }}
.callout-tag {{ position: absolute; width: 520px; padding: 26px 32px; }}
.callout-val {{ font-size: 38px; font-weight: 700; color: {accent}; margin: 4px 0 6px; }}

.split-card {{ width: 1340px; padding: 30px 46px 34px; }}
.split-header {{ margin-bottom: 22px; }}
.split-grid {{ display: grid; grid-template-columns: 1fr 1.5px 1fr; gap: 44px; align-items: center; }}
.split-divider {{ width: 1.5px; height: 118px; background: linear-gradient(180deg, transparent, rgba(232,240,248,0.38), transparent); }}
.split-lbl {{ font-size: 20px; font-weight: 700; letter-spacing: 0.14em; color: #A6DDF7; margin-bottom: 8px; }}
.split-lbl.accent {{ color: {accent}; }}
.split-val {{ font-size: 40px; font-weight: 700; color: #FFFFFF; margin-bottom: 16px; }}
.bar-bg {{ width: 100%; height: 13px; border-radius: 99px; background: rgba(232,240,248,0.16); overflow: hidden; }}
.bar-fill {{ height: 100%; width: 0%; border-radius: 99px; }}
.bar-cool {{ background: linear-gradient(90deg, #4E8BB0, {accent_secondary}); }}
.bar-warm {{ background: linear-gradient(90deg, #C76F28, {accent}); box-shadow: 0 0 16px {theme["accent_amber_glow"]}; }}
</style>
</head>
<body>
<div id="viewport-scale">{body_html}</div>
<script src="{gsap_uri}"></script>
<script src="{split_uri}"></script>
<script src="{draw_uri}"></script>
<script src="{ease_uri}"></script>
<script src="{lucide_uri}"></script>
<script>
gsap.registerPlugin(SplitText, DrawSVGPlugin, CustomEase);
if (window.lucide) lucide.createIcons();
const easeOut = CustomEase.create("docOut", "M0,0 C0.16,1 0.3,1 1,1");
const tl = gsap.timeline({{ paused: true }});
const template = {json.dumps(spec.template)};
const outStart = {out_start:.3f};

if (template === "kinetic_title_reveal") {{
  const split = new SplitText("#hero-title", {{ type: "words,chars" }});
  tl.to(".title-scrim", {{ opacity: 1, duration: 0.55, ease: "power2.out" }}, 0)
    .from(".eyebrow", {{ opacity: 0, y: 14, duration: 0.45, ease: easeOut }}, 0.08)
    .from(split.chars, {{ opacity: 0, y: 34, stagger: 0.018, duration: 0.65, ease: easeOut }}, 0.12)
    .from("#rule-l, #rule-r", {{ drawSVG: "0%", duration: 0.65, ease: easeOut }}, 0.32)
    .from("#rule-diamond", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.35, ease: "back.out(2)" }}, 0.30)
    .from(".hero-sub", {{ opacity: 0, y: 18, duration: 0.55, ease: easeOut }}, 0.48)
    .to("#stage", {{ opacity: 0, y: -12, duration: 0.48, ease: "power2.in" }}, outStart);
}} else if (template === "geological_timeline") {{
  tl.from(".timeline-card", {{ opacity: 0, y: 42, duration: 0.55, ease: easeOut }}, 0)
    .from("#tl-progress", {{ drawSVG: "0%", duration: 1.05, ease: easeOut }}, 0.25)
    .from(".tl-stop", {{ opacity: 0, y: 14, stagger: 0.12, duration: 0.45, ease: easeOut }}, 0.22)
    .to(".timeline-card", {{ opacity: 0, y: 24, duration: 0.45, ease: "power2.in" }}, outStart);
}} else if (template === "stat_counter_card") {{
  const card = document.querySelector(".stat-card");
  const sVal = parseFloat(card.dataset.start);
  const eVal = parseFloat(card.dataset.end);
  const pref = card.dataset.prefix || "";
  const suff = card.dataset.suffix || "";
  const pct = document.getElementById("stat-arc").dataset.pct || "78";
  const counter = {{ v: sVal }};
  tl.from(".stat-card", {{ opacity: 0, x: -46, duration: 0.55, ease: easeOut }}, 0)
    .fromTo("#stat-arc", {{ drawSVG: "0%" }}, {{ drawSVG: pct + "%", duration: 1.25, ease: easeOut }}, 0.18)
    .to(counter, {{
      v: eVal, duration: 1.35, ease: easeOut,
      onUpdate: () => {{
        const val = Math.round(counter.v).toLocaleString("en-US");
        document.getElementById("stat-num").textContent = pref + val + suff;
      }}
    }}, 0.18)
    .to(".stat-card", {{ opacity: 0, x: -24, duration: 0.45, ease: "power2.in" }}, outStart);
}} else if (template === "callout_spec_pointer") {{
  tl.from("#pulse-core", {{ scale: 0, transformOrigin: "center", duration: 0.3, ease: "back.out(2.2)" }}, 0)
    .fromTo("#pulse-outer", {{ scale: 0.3, opacity: 0.9, transformOrigin: "center" }}, {{ scale: 1.7, opacity: 0, duration: 1.2, repeat: 2, ease: "power1.out" }}, 0.05)
    .from("#leader-line", {{ drawSVG: "0%", duration: 0.55, ease: easeOut }}, 0.12)
    .from(".callout-tag", {{ opacity: 0, x: 24, duration: 0.45, ease: easeOut }}, 0.38)
    .to("#stage", {{ opacity: 0, duration: 0.42, ease: "power2.in" }}, outStart);
}} else {{
  const lw = document.getElementById("bar-left").dataset.w;
  const rw = document.getElementById("bar-right").dataset.w;
  tl.from(".split-card", {{ opacity: 0, y: 40, duration: 0.55, ease: easeOut }}, 0)
    .to("#bar-left", {{ width: lw, duration: 0.95, ease: easeOut }}, 0.35)
    .to("#bar-right", {{ width: rw, duration: 1.15, ease: easeOut }}, 0.45)
    .to(".split-card", {{ opacity: 0, y: 24, duration: 0.45, ease: "power2.in" }}, outStart);
}}

window.__setTime = function(t) {{
  tl.time(t, false);
}};
window.__getBBox = function() {{
  const el = document.getElementById("bbox-root");
  if (!el) return [0, 0, 0, 0];
  const r = el.getBoundingClientRect();
  return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
}};
</script>
</body>
</html>"""


def render_motion_bridge_rgba(
    spec: MotionBridgeSpec,
    out_mov: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    render_width: int = 1920,
    render_height: int = 1080,
) -> dict[str, Any]:
    """Render a GSAP 3.13 HTML5/SVG motion bridge to transparent RGBA MOV at exact fps."""
    import base64

    spec.validate()
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_mov.with_suffix(".html")
    html_path.write_text(_build_bridge_html(spec, width=render_width, height=render_height), encoding="utf-8")

    total_frames = max(2, int(round(spec.duration_s * fps)))
    bbox = [0, 0, 0, 0]
    sx = width / float(render_width)
    sy = height / float(render_height)
    vf = f"scale={width}:{height}:flags=lanczos" if (render_width, render_height) != (width, height) else "null"

    ff_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-vf",
        vf,
        "-c:v",
        "qtrle",
        "-pix_fmt",
        "argb",
        str(out_mov),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
        )
        page = browser.new_page(viewport={"width": render_width, "height": render_height}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.evaluate(f"() => window.__setTime({spec.duration_s * 0.5:.3f})")
        raw_bb = list(page.evaluate("() => window.__getBBox()"))
        bbox = [int(round(raw_bb[0] * sx)), int(round(raw_bb[1] * sy)), int(round(raw_bb[2] * sx)), int(round(raw_bb[3] * sy))]

        cdp = page.context.new_cdp_session(page)
        cdp.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})

        for f_idx in range(total_frames):
            t_s = f_idx / float(fps)
            page.evaluate(f"() => window.__setTime({t_s:.4f})")
            res = cdp.send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            proc.stdin.write(base64.b64decode(res["data"]))

        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg RGBA bridge encode failed with exit code {ret}")

    return {
        "bridge_id": spec.bridge_id,
        "template": spec.template,
        "path": str(out_mov),
        "width": width,
        "height": height,
        "fps": fps,
        "start_s": spec.start_s,
        "end_s": round(spec.start_s + spec.duration_s, 3),
        "duration_s": spec.duration_s,
        "bbox": bbox,
    }


def composite_motion_bridges(
    base_video: Path,
    bridge_renders: list[dict[str, Any]],
    out_video: Path,
) -> Path:
    """Composite pre-rendered RGBA GSAP motion bridge MOVs onto ``base_video`` via FFmpeg."""
    if not bridge_renders:
        raise ValueError("bridge_renders must be non-empty")
    out_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(base_video)]
    for br in bridge_renders:
        cmd += ["-i", str(br["path"])]

    filters: list[str] = []
    prev = "[0:v]"
    for idx, br in enumerate(bridge_renders):
        s = float(br["start_s"])
        e = float(br["end_s"])
        lbl = f"[b{idx}]"
        out = f"[v{idx}]"
        filters.append(f"[{idx + 1}:v]format=rgba,setpts=PTS+{s:.3f}/TB{lbl}")
        filters.append(f"{prev}{lbl}overlay=0:0:eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'{out}")
        prev = out

    cmd += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        prev,
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(out_video),
    ]
    subprocess.run(cmd, check=True)
    return out_video
