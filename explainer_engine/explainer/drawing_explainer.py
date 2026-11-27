"""Animated Visual-Essay Drawing & Archival Explainer Engine (GSAP 3.13 + DrawSVG + Rough.js + Bespoke Plates).

Produces full-screen 6-10s animated illustrated visual-essay segments connecting dramatic live-action
docudrama scenes, uniting:
- Bespoke archival charcoal/parchment illustrations with subtle editorial camera drift and organic grain.
- Multi-stage GSAP 3.13 + DrawSVG + Rough.js hand-drawn data choreography (chalk circles, curved arrows,
  hatched deficit bars, chemical spark trajectories, anatomical highlights, and a 24-hour Ice Age clock).
- Zero PowerPoint/SaaS boxes: pure boxless filmic typography + tactile hand-sketched ink geometry.

Supported built-in visual-essay scenes:
1. ``caloric_trap`` (~8s): Raw foraging 1,350 kcal / 6h chewing vs 3,400 kcal Ice Age survival deficit.
2. ``stone_chemistry`` (~7s): Flint SiO2 shaving pyrite FeS2 shards igniting at 1,200°C in O2.
3. ``brain_revolution`` (~10s): Shrinking jaw & gut freeing 20% resting energy to grow the human neocortex.
4. ``night_hours`` (~7s): +4 hours stolen from the Ice Age dark on a 24-hour clock for language, myth & cave art.
"""
from __future__ import annotations

import base64
import html
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from explainer_engine.design_system.tokens import (
    PALEO_ICE_AGE_THEME,
    build_font_face_css,
    resolve_vendor_js,
)

VALID_EXPLAINER_SCENES = frozenset(
    {
        "caloric_trap",
        "stone_chemistry",
        "brain_revolution",
        "night_hours",
        "roman_omens",
        "roman_conspiracy",
        "ides_closing_essay",
    }
)


@dataclass(slots=True)
class DrawingExplainerSpec:
    explainer_id: str
    scene_kind: str
    title: str
    subtitle: str
    illustration_path: Path
    duration_s: float = 8.0
    era_stamp: str = "ICE AGE FIELD NOTES"
    accent_warm: str = "#E39B43"
    accent_cool: str = "#7CC4E8"
    accent_crimson: str = "#D4523B"
    meta: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.scene_kind not in VALID_EXPLAINER_SCENES:
            raise ValueError(
                f"Unsupported drawing explainer scene_kind {self.scene_kind!r}; "
                f"expected one of {sorted(VALID_EXPLAINER_SCENES)}"
            )
        if not (5.0 <= self.duration_s <= 20.0):
            raise ValueError(f"Drawing explainer duration_s should be in [5.0, 20.0], got {self.duration_s}")
        if not self.illustration_path.is_file():
            raise FileNotFoundError(f"Explainer archival illustration not found: {self.illustration_path}")


def _img_data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _build_explainer_html(spec: DrawingExplainerSpec, *, width: int, height: int) -> str:
    theme = dict(PALEO_ICE_AGE_THEME)
    font_css = build_font_face_css(
        ["Cinzel", "Cormorant Garamond", "Plus Jakarta Sans", "IBM Plex Mono", "JetBrains Mono"]
    )
    gsap_uri = resolve_vendor_js("gsap.min.js").as_uri()
    split_uri = resolve_vendor_js("SplitText.min.js").as_uri()
    draw_uri = resolve_vendor_js("DrawSVGPlugin.min.js").as_uri()
    ease_uri = resolve_vendor_js("CustomEase.min.js").as_uri()
    rough_uri = resolve_vendor_js("rough.js").as_uri()

    art_uri = _img_data_uri(spec.illustration_path)
    scale = height / 1080.0
    safe_title = html.escape(spec.title)
    safe_sub = html.escape(spec.subtitle)
    safe_era = html.escape(spec.era_stamp)
    dur = float(spec.duration_s)

    if spec.scene_kind == "caloric_trap":
        scene_dom = f"""
        <div class="header-block header-tl">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="460" height="22" viewBox="0 0 460 22"></svg>
          <div class="ex-sub">{safe_sub}</div>
        </div>
        <div class="annot" id="a-raw" style="left:82px; bottom:58px; width:560px;">
          <div class="tag-mono mono cool">RAW FORAGING YIELD</div>
          <div class="big-stat mono" id="num-raw">0 kcal</div>
          <div class="annot-desc">~6 hours/day chewing frozen roots &amp; raw sinew</div>
        </div>
        <div class="annot" id="a-need" style="left:820px; top:225px; width:470px;">
          <div class="tag-mono mono warm">−30°C SURVIVAL DEMAND</div>
          <div class="big-stat mono" id="num-need">0 kcal</div>
          <div class="annot-desc">Ice Age body heat &amp; hunting burn</div>
        </div>
        <div class="annot" id="a-def" style="left:820px; top:560px; width:460px;">
          <div class="tag-mono mono crimson">DAILY ENERGY DEFICIT</div>
          <div class="big-stat mono crimson" id="num-def">0 kcal</div>
          <div class="annot-italic">Without heat, the body starves in slow motion.</div>
        </div>
        """
    elif spec.scene_kind == "stone_chemistry":
        scene_dom = f"""
        <div class="header-block header-tl" style="max-width:560px;">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="460" height="22" viewBox="0 0 460 22"></svg>
          <div class="ex-sub" style="font-size:26px;">{safe_sub}</div>
        </div>
        <div class="annot" id="a-flint" style="left:755px; top:145px; width:430px;">
          <div class="tag-mono mono cool">STRIKER · MOHS 7</div>
          <div class="mid-stat">FLINT <span class="chem mono">SiO₂</span></div>
          <div class="annot-desc">Razor-hard silica shaves pyrite</div>
        </div>
        <div class="annot" id="a-pyrite" style="left:82px; bottom:56px; width:490px;">
          <div class="tag-mono mono warm">SPARK SOURCE</div>
          <div class="mid-stat">IRON PYRITE <span class="chem mono">FeS₂</span></div>
          <div class="annot-desc">Microscopic iron-sulfide shards ignite in O₂</div>
        </div>
        <div class="annot" id="a-temp" style="left:835px; top:345px; width:420px; text-align:center;">
          <div class="tag-mono mono warm">PYROPHORIC FLASH</div>
          <div class="big-stat mono warm" id="num-temp">0°C</div>
        </div>
        <div class="annot" id="a-tinder" style="right:76px; top:215px; width:460px; text-align:right;">
          <div class="tag-mono mono warm">IGNITION NEST</div>
          <div class="mid-stat">BIRCH BARK &amp; MOSS</div>
          <div class="annot-italic">Catches a single glowing shard into flame</div>
        </div>
        """
    elif spec.scene_kind == "brain_revolution":
        scene_dom = f"""
        <div class="header-block header-tc">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="540" height="22" viewBox="0 0 540 22"></svg>
        </div>
        <div class="annot" id="a-left" style="left:68px; bottom:52px; width:500px;">
          <div class="tag-mono mono cool">BEFORE COOKING · RAW DIET</div>
          <div class="mid-stat">HEAVY JAW &amp; LONG GUT</div>
          <div class="annot-desc">Digesting raw food consumes massive resting energy</div>
        </div>
        <div class="annot" id="a-mid" style="left:700px; top:435px; width:510px; text-align:center;">
          <div class="tag-mono mono warm">EXTERNAL PRE-DIGESTION</div>
          <div class="mid-stat warm">2X USABLE CALORIES</div>
          <div class="annot-desc">Heat breaks starch &amp; protein before chewing</div>
        </div>
        <div class="annot" id="a-right-top" style="right:44px; top:112px; width:400px; text-align:right;">
          <div class="tag-mono mono warm">EXPANDED NEOCORTEX</div>
          <div class="big-stat mono warm" id="num-brain">0%</div>
          <div class="annot-desc" style="font-size:20px;">Of resting energy redirected to the brain</div>
        </div>
        <div class="annot" id="a-right-bot" style="right:54px; bottom:52px; width:460px; text-align:right;">
          <div class="tag-mono mono cool">ANATOMICAL TRADE-OFF</div>
          <div class="mid-stat">−30% JAW &amp; GUT MASS</div>
          <div class="annot-italic">Fire literally rewired the human skull.</div>
        </div>
        """
    elif spec.scene_kind == "roman_omens":
        scene_dom = f"""
        <div class="roman-dark-wash"></div>
        <div class="header-block header-tl" style="max-width:740px;">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="520" height="22" viewBox="0 0 520 22"></svg>
          <div class="ex-sub">{safe_sub}</div>
        </div>
        <div class="annot" id="a-dream" style="left:82px; top:385px; width:510px;">
          <div class="tag-mono mono warm">01 · CALPURNIA'S NIGHTMARE</div>
          <div class="mid-stat">COLLAPSING ROOF</div>
          <div class="annot-desc">Plutarch notes she was never superstitious — until this dawn</div>
        </div>
        <div class="annot" id="a-priests" style="left:705px; top:385px; width:500px;">
          <div class="tag-mono mono crimson">02 · HARUSPEX SACRIFICES</div>
          <div class="big-stat mono crimson" id="num-omens">0 / 0</div>
          <div class="annot-desc">Every morning reading returns catastrophic</div>
        </div>
        <div class="annot" id="a-caesar" style="right:76px; top:385px; width:490px; text-align:right;">
          <div class="tag-mono mono cool">03 · CAESAR'S HESITATION</div>
          <div class="mid-stat">SHAKEN &amp; DIZZY</div>
          <div class="annot-italic">For once, Rome's boldest commander genuinely wavers.</div>
        </div>
        <div class="annot" id="a-omen-verdict" style="left:50%; bottom:74px; transform:translateX(-50%); width:1240px; text-align:center;">
          <div class="tag-mono mono warm">DAWN AT THE DOMUS PUBLICA</div>
          <div class="mid-stat warm">EVERY SIGN WARNS HIM NOT TO GO</div>
        </div>
        """
    elif spec.scene_kind == "roman_conspiracy":
        scene_dom = f"""
        <div class="roman-dark-wash"></div>
        <div class="header-block header-tl" style="max-width:780px;">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="520" height="22" viewBox="0 0 520 22"></svg>
          <div class="ex-sub">{safe_sub}</div>
        </div>
        <div class="annot" id="a-senators" style="left:84px; top:385px; width:500px;">
          <div class="tag-mono mono crimson">01 · THE CONSPIRACY</div>
          <div class="big-stat mono crimson" id="num-senators">0 SENATORS</div>
          <div class="annot-desc">Sixty rival politicians guarding one explosive secret</div>
        </div>
        <div class="annot" id="a-window" style="left:705px; top:385px; width:510px; text-align:center;">
          <div class="tag-mono mono warm">02 · DEPARTURE DEADLINE</div>
          <div class="big-stat mono warm" id="num-days">0 DAYS</div>
          <div class="annot-desc">Until Caesar leaves Rome for his eastern war</div>
        </div>
        <div class="annot" id="a-decimus" style="left:1340px; top:385px; width:500px; text-align:left;">
          <div class="tag-mono mono cool">03 · PARTHIA CAMPAIGN</div>
          <div class="big-stat mono cool" id="num-legions" style="font-size:48px;line-height:1.15;white-space:nowrap;">LOYAL LEGIONS</div>
          <div class="annot-desc">Once surrounded by his army in the east, the plot is dead</div>
        </div>
        <div class="annot" id="a-consp-bottom" style="left:84px; bottom:74px; width:1740px; text-align:center;">
          <div class="tag-mono mono warm">WHY DELAYING ONE SINGLE DAY KILLS THE PLOT</div>
          <div class="mid-stat">TODAY IS THEIR ONLY WINDOW</div>
        </div>
        """
    elif spec.scene_kind == "ides_closing_essay":
        scene_dom = f"""
        <div class="roman-dark-wash"></div>
        <div class="header-block header-tc">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="560" height="22" viewBox="0 0 560 22"></svg>
          <div class="ex-sub">{safe_sub}</div>
        </div>
        <div class="annot" id="a-p1" style="left:88px; top:375px; width:470px;">
          <div class="tag-mono mono cool">PILLAR I · DAWN</div>
          <div class="mid-stat">DOUBT</div>
          <div class="annot-desc">Calpurnia's nightmare nearly stopped history at the doorway</div>
        </div>
        <div class="annot" id="a-p2" style="left:725px; top:375px; width:470px; text-align:center;">
          <div class="tag-mono mono warm">PILLAR II · PERSUASION</div>
          <div class="mid-stat warm">FRIENDSHIP</div>
          <div class="annot-desc">Decimus Brutus turned trust and irony into a weapon</div>
        </div>
        <div class="annot" id="a-p3" style="right:88px; top:375px; width:470px; text-align:right;">
          <div class="tag-mono mono crimson">PILLAR III · THE WALK</div>
          <div class="mid-stat crimson">PRIDE</div>
          <div class="annot-desc">No bodyguards, an unread scroll, and one step into shadow</div>
        </div>
        <div class="annot" id="a-legacy" style="left:50%; bottom:72px; transform:translateX(-50%); width:1260px; text-align:center;">
          <div class="tag-mono mono warm">MARCH 15, 44 BCE</div>
          <div class="big-stat mono" id="num-years">0 YEARS</div>
          <div class="annot-italic">One fragile morning turned a Republic into an Empire.</div>
        </div>
        """
    else:  # night_hours
        scene_dom = f"""
        <div class="header-block header-tl" style="max-width:480px;">
          <div class="era mono">{safe_era}</div>
          <h1 class="ex-title" id="ex-title">{safe_title}</h1>
          <svg id="title-rule" width="420" height="22" viewBox="0 0 420 22"></svg>
          <div class="ex-sub" style="font-size:26px;">{safe_sub}</div>
        </div>
        <div class="clock-center" id="a-clock-center">
          <div class="tag-mono mono warm" style="margin-bottom:2px;">RECLAIMED NIGHT</div>
          <div class="big-stat mono warm" id="num-hours">+0 HRS</div>
          <div class="annot-desc" style="font-size:21px;margin-top:4px;">24-HR ICE AGE CYCLE</div>
        </div>
        <div class="annot" id="a-day" style="right:72px; top:130px; width:420px; text-align:right;">
          <div class="tag-mono mono cool">PLEISTOCENE WINTER</div>
          <div class="mid-stat">10 HRS DAYLIGHT</div>
          <div class="annot-desc">Hunting, foraging &amp; survival travel</div>
        </div>
        <div class="annot" id="a-dark" style="left:72px; bottom:92px; width:420px;">
          <div class="tag-mono mono cool">BEFORE FIRE</div>
          <div class="mid-stat">14 HRS DARKNESS</div>
          <div class="annot-desc">Forced immobility in freezing caves</div>
        </div>
        <div class="annot" id="a-culture" style="right:72px; bottom:84px; width:450px; text-align:right;">
          <div class="tag-mono mono warm">BIRTH OF HUMAN CULTURE</div>
          <div class="mid-stat warm">LANGUAGE · MYTH · ART</div>
          <div class="annot-italic">Stories around the hearth built civilization.</div>
        </div>
        """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: {width}px; height: {height}px; overflow: hidden; background: #10141A;
  font-family: {theme["font_sans"]}; color: {theme["text_primary"]};
  -webkit-font-smoothing: antialiased;
}}
#stage-root {{
  width: 1920px; height: 1080px;
  transform: scale({scale:.6f}); transform-origin: top left;
  position: relative; overflow: hidden; background: #10141A;
}}
#art-wrap {{
  position: absolute; inset: -36px; will-change: transform;
}}
#art-img {{
  width: 100%; height: 100%; object-fit: cover; display: block;
  filter: contrast(1.06) brightness(0.92);
}}
.roman-dark-wash {{
  position: absolute; inset: 0; pointer-events: none; z-index: 3;
  background: linear-gradient(180deg, rgba(16,12,9,0.72) 0%, rgba(18,14,10,0.68) 52%, rgba(14,10,7,0.82) 100%);
}}
.archival-vignette {{
  position: absolute; inset: 0; pointer-events: none; z-index: 2;
  background: radial-gradient(ellipse 84% 80% at 50% 50%, rgba(12,16,22,0.08) 45%, rgba(6,9,14,0.72) 100%);
}}
.paper-grain {{
  position: absolute; inset: 0; pointer-events: none; z-index: 3; opacity: 0.08;
  filter: url(#paper-noise);
}}
#sketch-svg {{
  position: absolute; inset: 0; width: 1920px; height: 1080px; z-index: 4;
  overflow: visible; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.85));
}}
.mono {{ font-family: {theme["font_mono"]}; font-variant-numeric: tabular-nums; }}
.warm {{ color: {spec.accent_warm}; }}
.cool {{ color: {spec.accent_cool}; }}
.crimson {{ color: {spec.accent_crimson}; }}

.header-block {{ position: absolute; z-index: 6; }}
.header-tl {{ top: 54px; left: 82px; max-width: 780px; }}
.header-tc {{ top: 34px; left: 50%; transform: translateX(-50%); text-align: center; width: 1100px; }}
.header-tc svg {{ margin: 4px auto 0; display: block; }}
.era {{
  font-size: 18px; font-weight: 600; letter-spacing: 0.24em; text-transform: uppercase;
  color: {spec.accent_warm}; margin-bottom: 6px;
  text-shadow: 0 3px 14px rgba(0,0,0,0.95);
}}
.ex-title {{
  font-family: {theme["font_display"]}; font-size: 54px; font-weight: 700;
  letter-spacing: 0.09em; color: #F7F9FC; line-height: 1.08;
  text-shadow: 0 8px 28px rgba(0,0,0,0.95);
}}
.ex-sub {{
  font-family: {theme["font_editorial"]}; font-style: italic; font-size: 30px; font-weight: 600;
  color: #D8E4F0; margin-top: 6px; text-shadow: 0 4px 16px rgba(0,0,0,0.95);
}}

.annot {{ position: absolute; z-index: 6; opacity: 0; }}
.clock-center {{
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  text-align: center; width: 340px; z-index: 6; opacity: 0;
}}
.tag-mono {{
  font-size: 16px; font-weight: 700; letter-spacing: 0.20em; text-transform: uppercase;
  margin-bottom: 4px; text-shadow: 0 2px 10px rgba(0,0,0,0.98);
}}
.big-stat {{
  font-family: 'JetBrains Mono', monospace; font-size: 68px; font-weight: 700; line-height: 1.0;
  color: #FFFFFF; letter-spacing: -0.02em;
  text-shadow: 0 8px 26px rgba(0,0,0,0.98), 0 2px 6px rgba(0,0,0,0.95);
}}
.mid-stat {{
  font-family: {theme["font_display"]}; font-size: 36px; font-weight: 700; line-height: 1.12;
  letter-spacing: 0.05em; color: #FFFFFF;
  text-shadow: 0 6px 22px rgba(0,0,0,0.98);
}}
.chem {{ color: {spec.accent_cool}; font-size: 30px; margin-left: 8px; }}
.annot-desc {{
  font-family: {theme["font_sans"]}; font-size: 23px; font-weight: 500; color: #DDE7F2;
  margin-top: 6px; line-height: 1.28; text-shadow: 0 3px 14px rgba(0,0,0,0.98);
}}
.annot-italic {{
  font-family: {theme["font_editorial"]}; font-style: italic; font-size: 29px; font-weight: 600;
  color: #F4E6CE; margin-top: 8px; line-height: 1.22; text-shadow: 0 4px 16px rgba(0,0,0,0.98);
}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute">
  <defs>
    <filter id="paper-noise">
      <feTurbulence type="fractalNoise" baseFrequency="0.72" numOctaves="3" stitchTiles="stitch" />
      <feColorMatrix type="saturate" values="0"/>
    </filter>
  </defs>
</svg>
<div id="stage-root">
  <div id="art-wrap"><img id="art-img" src="{art_uri}" /></div>
  <div class="archival-vignette"></div>
  <div class="paper-grain"></div>
  <svg id="sketch-svg" viewBox="0 0 1920 1080" width="1920" height="1080"></svg>
  {scene_dom}
</div>

<script src="{gsap_uri}"></script>
<script src="{split_uri}"></script>
<script src="{draw_uri}"></script>
<script src="{ease_uri}"></script>
<script src="{rough_uri}"></script>
<script>
gsap.registerPlugin(SplitText, DrawSVGPlugin, CustomEase);
const easeOut = CustomEase.create("expOut", "M0,0 C0.16,1 0.3,1 1,1");
const KIND = {json.dumps(spec.scene_kind)};
const DUR = {dur:.3f};
const WARM = {json.dumps(spec.accent_warm)};
const COOL = {json.dumps(spec.accent_cool)};
const CRIMSON = {json.dumps(spec.accent_crimson)};
const META = {json.dumps(spec.meta)};

const sketchSvg = document.getElementById("sketch-svg");
const rc = rough.svg(sketchSvg);
const titleSvg = document.getElementById("title-rule");
const rcTitle = rough.svg(titleSvg);

function collectPaths(node) {{
  const out = [];
  node.querySelectorAll("path").forEach((p) => {{
    p.setAttribute("stroke-linecap", "round");
    p.setAttribute("stroke-linejoin", "round");
    out.push(p);
  }});
  return out;
}}

function addSketch(node) {{
  sketchSvg.appendChild(node);
  return collectPaths(node);
}}

// Draw hand-sketched Rough.js underline under header
const tw = parseInt(titleSvg.getAttribute("width"), 10);
const titleRuleNode = rcTitle.line(8, 10, tw - 12, 9, {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.7, bowing: 1.5, seed: 12 }});
titleSvg.appendChild(titleRuleNode);
const titleRulePaths = collectPaths(titleRuleNode);

const tl = gsap.timeline({{ paused: true }});

// Continuous subtle living editorial drift across entire duration (ZERO static slide feel!)
tl.fromTo("#art-wrap",
  {{ scale: 1.0, x: 0, y: 0 }},
  {{ scale: 1.045, x: -16, y: -8, duration: DUR, ease: "none" }},
  0
);

// Header intro choreography
const titleSplit = new SplitText("#ex-title", {{ type: "words" }});
tl.from(".era", {{ opacity: 0, y: 12, duration: 0.4, ease: easeOut }}, 0.12)
  .from(titleSplit.words, {{ opacity: 0, y: 26, stagger: 0.07, duration: 0.55, ease: easeOut }}, 0.18)
  .from(titleRulePaths, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, 0.35)
  .from(".ex-sub", {{ opacity: 0, y: 14, duration: 0.5, ease: easeOut }}, 0.48);

if (KIND === "caloric_trap") {{
  const cRaw = addSketch(rc.ellipse(425, 560, 660, 440, {{ stroke: COOL, strokeWidth: 3.4, roughness: 2.0, seed: 101 }}));
  const barRaw = addSketch(rc.rectangle(822, 412, 165, 26, {{ stroke: COOL, fill: "rgba(124,196,232,0.40)", fillStyle: "hachure", hachureGap: 6, strokeWidth: 2.4, roughness: 1.5, seed: 102 }}));
  const barNeed = addSketch(rc.rectangle(822, 452, 415, 26, {{ stroke: WARM, fill: "rgba(227,155,67,0.38)", fillStyle: "hachure", hachureGap: 6, strokeWidth: 2.4, roughness: 1.5, seed: 103 }}));
  const arrow1 = addSketch(rc.curve([[770, 500], [1030, 515], [1305, 425]], {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.6, seed: 104 }}));
  const arrowTip = addSketch(rc.linearPath([[1278, 416], [1305, 425], [1288, 448]], {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.3, seed: 105 }}));
  const defLine = addSketch(rc.line(820, 692, 1230, 690, {{ stroke: CRIMSON, strokeWidth: 4.0, roughness: 1.9, seed: 106 }}));

  const oRaw = {{ v: 0 }}, oNeed = {{ v: 0 }}, oDef = {{ v: 0 }};
  tl.from(cRaw, {{ drawSVG: "0%", duration: 0.95, ease: easeOut }}, 0.85)
    .to("#a-raw", {{ opacity: 1, y: 0, duration: 0.45, ease: easeOut }}, 1.1)
    .to(oRaw, {{ v: 1350, duration: 1.25, ease: easeOut, onUpdate: () => {{ document.getElementById("num-raw").textContent = Math.round(oRaw.v).toLocaleString("en-US") + " kcal"; }} }}, 1.15)
    .from(barRaw, {{ drawSVG: "0%", stagger: 0.02, duration: 0.7, ease: easeOut }}, 1.9)
    .from([...arrow1, ...arrowTip], {{ drawSVG: "0%", stagger: 0.06, duration: 0.8, ease: easeOut }}, 2.75)
    .to("#a-need", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 3.0)
    .to(oNeed, {{ v: 3400, duration: 1.25, ease: easeOut, onUpdate: () => {{ document.getElementById("num-need").textContent = Math.round(oNeed.v).toLocaleString("en-US") + " kcal"; }} }}, 3.05)
    .from(barNeed, {{ drawSVG: "0%", stagger: 0.02, duration: 0.85, ease: easeOut }}, 3.5)
    .to("#a-def", {{ opacity: 1, duration: 0.5, ease: easeOut }}, 4.65)
    .to(oDef, {{ v: -2050, duration: 1.15, ease: easeOut, onUpdate: () => {{ document.getElementById("num-def").textContent = Math.round(oDef.v).toLocaleString("en-US") + " kcal"; }} }}, 4.7)
    .from(defLine, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, 5.4);
}} else if (KIND === "stone_chemistry") {{
  const pFlint = addSketch(rc.curve([[742, 195], [645, 230], [565, 295]], {{ stroke: COOL, strokeWidth: 3.0, roughness: 1.5, seed: 201 }}));
  const pPyrite = addSketch(rc.curve([[310, 915], [330, 860], [360, 815]], {{ stroke: WARM, strokeWidth: 3.0, roughness: 1.5, seed: 202 }}));
  const sparkArc = addSketch(rc.curve([[650, 625], [960, 445], [1390, 560]], {{ stroke: WARM, strokeWidth: 4.2, roughness: 1.8, seed: 203 }}));
  const sparkTip = addSketch(rc.linearPath([[1364, 538], [1390, 560], [1358, 574]], {{ stroke: WARM, strokeWidth: 3.8, roughness: 1.3, seed: 204 }}));
  const cNest = addSketch(rc.ellipse(1475, 705, 560, 390, {{ stroke: WARM, strokeWidth: 3.4, roughness: 2.0, seed: 205 }}));

  const oTemp = {{ v: 20 }};
  tl.from(pFlint, {{ drawSVG: "0%", duration: 0.65, ease: easeOut }}, 0.8)
    .to("#a-flint", {{ opacity: 1, duration: 0.4, ease: easeOut }}, 0.95)
    .from(pPyrite, {{ drawSVG: "0%", duration: 0.65, ease: easeOut }}, 1.6)
    .to("#a-pyrite", {{ opacity: 1, duration: 0.4, ease: easeOut }}, 1.75)
    .from([...sparkArc, ...sparkTip], {{ drawSVG: "0%", stagger: 0.05, duration: 1.05, ease: easeOut }}, 2.55)
    .to("#a-temp", {{ opacity: 1, duration: 0.35, ease: easeOut }}, 2.85)
    .to(oTemp, {{ v: 1200, duration: 1.15, ease: easeOut, onUpdate: () => {{ document.getElementById("num-temp").textContent = Math.round(oTemp.v).toLocaleString("en-US") + "°C"; }} }}, 2.9)
    .from(cNest, {{ drawSVG: "0%", duration: 0.9, ease: easeOut }}, 4.25)
    .to("#a-tinder", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 4.55);
}} else if (KIND === "brain_revolution") {{
  const cJaw = addSketch(rc.ellipse(420, 565, 310, 220, {{ stroke: COOL, strokeWidth: 3.2, roughness: 1.9, seed: 301 }}));
  const sweep = addSketch(rc.curve([[730, 370], [960, 325], [1165, 360]], {{ stroke: WARM, strokeWidth: 4.5, roughness: 1.7, seed: 302 }}));
  const sweepTip = addSketch(rc.linearPath([[1135, 338], [1165, 360], [1132, 380]], {{ stroke: WARM, strokeWidth: 4.2, roughness: 1.3, seed: 303 }}));
  const cBrain = addSketch(rc.ellipse(1445, 305, 520, 330, {{ stroke: WARM, strokeWidth: 4.2, roughness: 2.1, seed: 304 }}));
  const cJawSmall = addSketch(rc.ellipse(1295, 595, 250, 180, {{ stroke: COOL, strokeWidth: 2.8, roughness: 1.8, seed: 305 }}));

  const oBrain = {{ v: 8 }};
  tl.from(cJaw, {{ drawSVG: "0%", duration: 0.85, ease: easeOut }}, 1.0)
    .to("#a-left", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 1.25)
    .from([...sweep, ...sweepTip], {{ drawSVG: "0%", stagger: 0.06, duration: 1.0, ease: easeOut }}, 3.2)
    .to("#a-mid", {{ opacity: 1, duration: 0.5, ease: easeOut }}, 3.55)
    .from(cBrain, {{ drawSVG: "0%", duration: 1.1, ease: easeOut }}, 5.1)
    .to("#a-right-top", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 5.45)
    .to(oBrain, {{ v: 20, duration: 1.35, ease: easeOut, onUpdate: () => {{ document.getElementById("num-brain").textContent = Math.round(oBrain.v) + "%"; }} }}, 5.5)
    .from(cJawSmall, {{ drawSVG: "0%", duration: 0.85, ease: easeOut }}, 7.1)
    .to("#a-right-bot", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 7.4);
}} else if (KIND === "roman_omens") {{
  const c1 = addSketch(rc.line(82, 358, 560, 356, {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.7, seed: 501 }}));
  const arr1 = addSketch(rc.curve([[595, 465], [642, 448], [688, 465]], {{ stroke: WARM, strokeWidth: 3.2, roughness: 1.4, seed: 502 }}));
  const arr1Tip = addSketch(rc.linearPath([[670, 452], [688, 465], [668, 476]], {{ stroke: WARM, strokeWidth: 3.2, roughness: 1.2, seed: 512 }}));
  const c2 = addSketch(rc.line(705, 358, 1185, 356, {{ stroke: CRIMSON, strokeWidth: 3.8, roughness: 1.8, seed: 503 }}));
  const arr2 = addSketch(rc.curve([[1225, 465], [1278, 448], [1332, 465]], {{ stroke: CRIMSON, strokeWidth: 3.2, roughness: 1.4, seed: 504 }}));
  const arr2Tip = addSketch(rc.linearPath([[1314, 452], [1332, 465], [1312, 476]], {{ stroke: CRIMSON, strokeWidth: 3.2, roughness: 1.2, seed: 514 }}));
  const c3 = addSketch(rc.line(1360, 358, 1844, 356, {{ stroke: COOL, strokeWidth: 3.4, roughness: 1.7, seed: 505 }}));
  const botRule = addSketch(rc.line(340, 868, 1580, 866, {{ stroke: WARM, strokeWidth: 3.6, roughness: 1.8, seed: 506 }}));

  const oOmen = {{ v: 0 }};
  tl.from(c1, {{ drawSVG: "0%", duration: 0.75, ease: easeOut }}, 0.85)
    .to("#a-dream", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 1.0)
    .from([...arr1, ...arr1Tip], {{ drawSVG: "0%", stagger: 0.05, duration: 0.55, ease: easeOut }}, 2.15)
    .from(c2, {{ drawSVG: "0%", duration: 0.75, ease: easeOut }}, 2.45)
    .to("#a-priests", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 2.65)
    .to(oOmen, {{ v: 3, duration: 1.15, ease: easeOut, onUpdate: () => {{ document.getElementById("num-omens").textContent = "0 / " + Math.max(1, Math.round(oOmen.v)) + " SAFE"; }} }}, 2.75)
    .from([...arr2, ...arr2Tip], {{ drawSVG: "0%", stagger: 0.05, duration: 0.55, ease: easeOut }}, 4.25)
    .from(c3, {{ drawSVG: "0%", duration: 0.75, ease: easeOut }}, 4.55)
    .to("#a-caesar", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 4.75)
    .from(botRule, {{ drawSVG: "0%", duration: 0.85, ease: easeOut }}, 6.1)
    .to("#a-omen-verdict", {{ opacity: 1, duration: 0.5, ease: easeOut }}, 6.35);
}} else if (KIND === "roman_conspiracy") {{
  const boxS = addSketch(rc.line(84, 356, 560, 354, {{ stroke: CRIMSON, strokeWidth: 4.0, roughness: 1.8, seed: 601 }}));
  const bar60 = addSketch(rc.rectangle(84, 678, 460, 24, {{ stroke: CRIMSON, fill: "rgba(212,82,59,0.40)", fillStyle: "hachure", hachureGap: 7, strokeWidth: 2.4, roughness: 1.5, seed: 602 }}));
  const arrMid = addSketch(rc.curve([[595, 476], [642, 462], [688, 476]], {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.3, seed: 603 }}));
  const arrMidTip = addSketch(rc.linearPath([[670, 464], [688, 476], [668, 488]], {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.2, seed: 613 }}));
  const topDays = addSketch(rc.line(715, 356, 1195, 354, {{ stroke: WARM, strokeWidth: 4.0, roughness: 1.7, seed: 604 }}));
  const barDays = addSketch(rc.rectangle(765, 678, 380, 24, {{ stroke: WARM, fill: "rgba(227,155,67,0.38)", fillStyle: "hachure", hachureGap: 7, strokeWidth: 2.4, roughness: 1.5, seed: 614 }}));
  const arrRight = addSketch(rc.curve([[1225, 476], [1278, 462], [1332, 476]], {{ stroke: COOL, strokeWidth: 3.4, roughness: 1.3, seed: 605 }}));
  const arrRightTip = addSketch(rc.linearPath([[1314, 464], [1332, 476], [1312, 488]], {{ stroke: COOL, strokeWidth: 3.4, roughness: 1.2, seed: 615 }}));
  const lineRight = addSketch(rc.line(1340, 356, 1828, 354, {{ stroke: COOL, strokeWidth: 3.8, roughness: 1.7, seed: 606 }}));
  const barLegions = addSketch(rc.rectangle(1340, 678, 460, 24, {{ stroke: COOL, fill: "rgba(139,196,222,0.36)", fillStyle: "hachure", hachureGap: 7, strokeWidth: 2.4, roughness: 1.5, seed: 616 }}));
  const botLine = addSketch(rc.line(320, 868, 1600, 866, {{ stroke: WARM, strokeWidth: 3.8, roughness: 1.8, seed: 607 }}));

  const bt = Array.isArray(META.beat_times) && META.beat_times.length >= 4 ? META.beat_times : [1.0, 3.25, 5.55, 7.3];
  const t1 = bt[0], t2 = bt[1], t3 = bt[2], t4 = bt[3];
  const oSen = {{ v: 0 }}, oDays = {{ v: 10 }};
  tl.from(boxS, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, Math.max(0.4, t1 - 0.15))
    .to("#a-senators", {{ opacity: 1, duration: 0.45, ease: easeOut }}, t1)
    .to(oSen, {{ v: 60, duration: 1.15, ease: easeOut, onUpdate: () => {{ document.getElementById("num-senators").textContent = Math.round(oSen.v) + " SENATORS"; }} }}, t1 + 0.05)
    .from(bar60, {{ drawSVG: "0%", stagger: 0.02, duration: 0.75, ease: easeOut }}, t1 + 0.7)
    .from([...arrMid, ...arrMidTip], {{ drawSVG: "0%", stagger: 0.05, duration: 0.55, ease: easeOut }}, Math.max(t1 + 0.9, t2 - 0.4))
    .from(topDays, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, Math.max(t1 + 1.1, t2 - 0.15))
    .to("#a-window", {{ opacity: 1, duration: 0.45, ease: easeOut }}, t2)
    .to(oDays, {{ v: 3, duration: 1.0, ease: easeOut, onUpdate: () => {{ document.getElementById("num-days").textContent = Math.round(oDays.v) + " DAYS"; }} }}, t2 + 0.08)
    .from(barDays, {{ drawSVG: "0%", stagger: 0.02, duration: 0.7, ease: easeOut }}, t2 + 0.65)
    .from([...arrRight, ...arrRightTip], {{ drawSVG: "0%", stagger: 0.05, duration: 0.55, ease: easeOut }}, Math.max(t2 + 0.9, t3 - 0.4))
    .from(lineRight, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, Math.max(t2 + 1.1, t3 - 0.15))
    .to("#a-decimus", {{ opacity: 1, duration: 0.45, ease: easeOut }}, t3)
    .from(barLegions, {{ drawSVG: "0%", stagger: 0.02, duration: 0.75, ease: easeOut }}, t3 + 0.55)
    .from(botLine, {{ drawSVG: "0%", duration: 0.85, ease: easeOut }}, Math.max(t3 + 0.8, t4 - 0.25))
    .to("#a-consp-bottom", {{ opacity: 1, duration: 0.45, ease: easeOut }}, t4);
}} else if (KIND === "ides_closing_essay") {{
  const l1 = addSketch(rc.line(88, 348, 540, 346, {{ stroke: COOL, strokeWidth: 3.4, roughness: 1.6, seed: 701 }}));
  const l2 = addSketch(rc.line(725, 348, 1195, 346, {{ stroke: WARM, strokeWidth: 3.8, roughness: 1.6, seed: 702 }}));
  const l3 = addSketch(rc.line(1362, 348, 1832, 346, {{ stroke: CRIMSON, strokeWidth: 3.8, roughness: 1.6, seed: 703 }}));
  const convL = addSketch(rc.curve([[315, 635], [580, 725], [880, 760]], {{ stroke: COOL, strokeWidth: 3.0, roughness: 1.5, seed: 704 }}));
  const convC = addSketch(rc.line(960, 635, 960, 752, {{ stroke: WARM, strokeWidth: 3.2, roughness: 1.4, seed: 705 }}));
  const convR = addSketch(rc.curve([[1605, 635], [1340, 725], [1040, 760]], {{ stroke: CRIMSON, strokeWidth: 3.0, roughness: 1.5, seed: 706 }}));

  const oYrs = {{ v: 0 }};
  tl.from(l1, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, 0.9)
    .to("#a-p1", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 1.1)
    .from(l2, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, 2.4)
    .to("#a-p2", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 2.6)
    .from(l3, {{ drawSVG: "0%", duration: 0.7, ease: easeOut }}, 3.9)
    .to("#a-p3", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 4.1)
    .from([...convL, ...convC, ...convR], {{ drawSVG: "0%", stagger: 0.08, duration: 0.9, ease: easeOut }}, 5.45)
    .to("#a-legacy", {{ opacity: 1, duration: 0.5, ease: easeOut }}, 6.0)
    .to(oYrs, {{ v: 2000, duration: 1.45, ease: easeOut, onUpdate: () => {{ document.getElementById("num-years").textContent = Math.round(oYrs.v).toLocaleString("en-US") + " YEARS"; }} }}, 6.1);
}} else {{
  // night_hours: Hand-drawn 24-hour Ice Age clock right inside the circular art dial!
  const cx = 960, cy = 540, rOuter = 232, rInner = 192;
  const ring1 = addSketch(rc.circle(cx, cy, rOuter * 2, {{ stroke: "rgba(232,240,248,0.55)", strokeWidth: 2.4, roughness: 1.5, seed: 401 }}));
  const tickPaths = [];
  for (let h = 0; h < 24; h++) {{
    const ang = (h / 24.0) * Math.PI * 2 - Math.PI / 2;
    const r0 = (h % 6 === 0) ? rOuter - 20 : rOuter - 10;
    const x1 = cx + Math.cos(ang) * r0, y1 = cy + Math.sin(ang) * r0;
    const x2 = cx + Math.cos(ang) * rOuter, y2 = cy + Math.sin(ang) * rOuter;
    tickPaths.push(...addSketch(rc.line(x1, y1, x2, y2, {{ stroke: "rgba(232,240,248,0.72)", strokeWidth: h % 6 === 0 ? 3.0 : 1.6, roughness: 0.9, seed: 410 + h }})));
  }}
  // Glowing amber +4 hour reclaimed arc along the lower evening/hearth rim
  const arcEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
  const aStart = 0.20 * Math.PI, aEnd = 0.80 * Math.PI;
  const ax1 = cx + Math.cos(aStart) * (rOuter + 14), ay1 = cy + Math.sin(aStart) * (rOuter + 14);
  const ax2 = cx + Math.cos(aEnd) * (rOuter + 14), ay2 = cy + Math.sin(aEnd) * (rOuter + 14);
  arcEl.setAttribute("d", `M ${{ax1.toFixed(1)}} ${{ay1.toFixed(1)}} A ${{rOuter + 14}} ${{rOuter + 14}} 0 0 1 ${{ax2.toFixed(1)}} ${{ay2.toFixed(1)}}`);
  arcEl.setAttribute("fill", "none");
  arcEl.setAttribute("stroke", WARM);
  arcEl.setAttribute("stroke-width", "12");
  arcEl.setAttribute("stroke-linecap", "round");
  sketchSvg.appendChild(arcEl);

  const ptrCulture = addSketch(rc.curve([[1180, 740], [1310, 785], [1410, 815]], {{ stroke: WARM, strokeWidth: 3.4, roughness: 1.6, seed: 460 }}));
  const oHrs = {{ v: 0 }};

  tl.from(ring1, {{ drawSVG: "0%", duration: 0.9, ease: easeOut }}, 0.8)
    .from(tickPaths, {{ opacity: 0, stagger: 0.02, duration: 0.35 }}, 1.15)
    .to("#a-day", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 1.45)
    .to("#a-dark", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 2.15)
    .from(arcEl, {{ drawSVG: "0%", duration: 1.25, ease: easeOut }}, 2.85)
    .to("#a-clock-center", {{ opacity: 1, duration: 0.4, ease: easeOut }}, 3.0)
    .to(oHrs, {{ v: 4, duration: 1.15, ease: easeOut, onUpdate: () => {{ document.getElementById("num-hours").textContent = "+" + Math.round(oHrs.v) + " HRS"; }} }}, 3.05)
    .from(ptrCulture, {{ drawSVG: "0%", duration: 0.75, ease: easeOut }}, 4.45)
    .to("#a-culture", {{ opacity: 1, duration: 0.45, ease: easeOut }}, 4.75);
}}

// Crisp cut-in without a black frame flash at t=0
tl.from("#stage-root", {{ opacity: 0.94, duration: 0.16, ease: "power1.out" }}, 0);

window.__setTime = function(t) {{ tl.time(t, false); }};
</script>
</body>
</html>"""


def render_drawing_explainer(
    spec: DrawingExplainerSpec,
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    render_width: int = 1920,
    render_height: int = 1080,
) -> dict[str, Any]:
    """Render a full-screen 2K 24fps animated archival charcoal + Rough.js + GSAP drawing explainer."""
    spec.validate()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_mp4.with_suffix(".html")
    html_path.write_text(_build_explainer_html(spec, width=render_width, height=render_height), encoding="utf-8")

    total_frames = max(2, int(round(spec.duration_s * fps)))
    vf = f"scale={width}:{height}:flags=lanczos" if (render_width, render_height) != (width, height) else "null"
    ff_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": render_width, "height": render_height}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        cdp = page.context.new_cdp_session(page)

        for f_idx in range(total_frames):
            t_s = f_idx / float(fps)
            page.evaluate(f"() => window.__setTime({t_s:.4f})")
            res = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 95})
            proc.stdin.write(base64.b64decode(res["data"]))

        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg drawing explainer encode failed with exit code {ret}")

    return {
        "explainer_id": spec.explainer_id,
        "scene_kind": spec.scene_kind,
        "path": str(out_mp4),
        "illustration_path": str(spec.illustration_path),
        "duration_s": spec.duration_s,
        "width": width,
        "height": height,
        "fps": fps,
    }
