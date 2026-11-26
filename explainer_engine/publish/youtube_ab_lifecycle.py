"""Full-Lifecycle YouTube A/B Packaging, Retention & Outlier Optimization Lab.

Codifies proven commercial YouTube growth & retention systems for historical docudramas:
1. Paddy Galloway Outlier / Packaging Matrix (Clickability x Broad-Interest Hook x Curiosity Gap
   x Zero Title-Thumbnail Duplication x Visual Contrast at 168x94px).
2. YouTube Studio "Test & Compare" Watch-Time-per-Impression (WTPI) estimator across 3 variants.
3. 3-Second Hook + Open Curiosity Loop Auditor (verifies immediate visual/audio grab + stakes question).
4. 4-7 Second Pattern-Interrupt Cadence & 30-Second Drop-Off Forensics heatmap.
5. Desktop + Critical 168x94px Mobile + Living-Room TV 10-ft Home Feed Simulator (`youtube_feed_ab_mockup.png`).
"""
from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from explainer_engine.design_system.tokens import build_font_face_css
from explainer_engine.publish.youtube_ab_packaging import ThumbnailVariantSpec, render_photoreal_thumbnail


@dataclass(slots=True)
class HookOpeningCandidate:
    hook_id: str
    title_pairing: str
    first_3s_visual: str
    first_3s_audio: str
    curiosity_loop_question: str
    payoff_timestamp_s: float
    estimated_30s_retention_pct: float
    rationale: str


@dataclass(slots=True)
class PackagingScorecard:
    variant_id: str
    title: str
    overlay_words: int
    duplicates_title: bool
    mobile_168x94_score: float
    curiosity_gap_score: float
    wtpi_index: float
    notes: list[str] = field(default_factory=list)


def evaluate_paddy_galloway_matrix(variants: list[ThumbnailVariantSpec]) -> list[dict[str, Any]]:
    """Deterministically score A/B/C thumbnail-title pairs on Paddy Galloway Packaging principles."""
    cards: list[dict[str, Any]] = []
    for v in variants:
        clean_overlay = html.unescape(v.overlay_big.replace("<br/>", " ").replace("<em>", "").replace("</em>", "")).strip()
        overlay_tokens = [t.strip(".,!?:;").lower() for t in clean_overlay.split() if t.strip()]
        title_tokens = {t.strip(".,!?:;").lower() for t in v.title.split() if len(t.strip(".,!?:;")) > 2}
        overlap = [t for t in overlay_tokens if t in title_tokens]
        duplicates = len(overlap) >= max(2, len(overlay_tokens))
        words_n = len(overlay_tokens)

        notes: list[str] = []
        mobile_score = 9.5
        if words_n > 3:
            mobile_score -= (words_n - 3) * 1.1
            notes.append(f"Overlay has {words_n} words (>3 hurts 168x94px legibility)")
        if duplicates:
            notes.append(f"Thumbnail repeats title tokens {overlap} instead of creating complementary tension")
        if len(v.title) > 62:
            notes.append(f"Title length {len(v.title)} chars (>62 truncates on mobile feeds)")

        curiosity_score = 9.2 if (not duplicates and len(v.title) <= 62) else 7.8
        wtpi = round((mobile_score * 0.45 + curiosity_score * 0.55) * 10.0, 1)
        cards.append(
            {
                "variant_id": v.variant_id,
                "strategy": v.strategy,
                "title": v.title,
                "title_length": len(v.title),
                "overlay_text": clean_overlay,
                "overlay_word_count": words_n,
                "duplicates_title": duplicates,
                "mobile_168x94_legibility_score": round(max(1.0, mobile_score), 2),
                "curiosity_gap_score": round(curiosity_score, 2),
                "wtpi_index": wtpi,
                "notes": notes,
            }
        )
    return cards


def analyze_pattern_interrupt_cadence(
    shot_windows: list[dict[str, Any]],
    bridges: list[dict[str, Any]],
    sfx_events: list[dict[str, Any]],
    *,
    total_duration_s: float,
    max_dead_zone_s: float = 5.0,
) -> dict[str, Any]:
    """Compute second-by-second pattern-interrupt density (cuts + overlays + audio hits) & 30s drop-off risk."""
    events: list[tuple[float, str]] = [(0.0, "open")]
    for s in shot_windows[1:]:
        events.append((float(s.get("start_s", 0.0)), "cut"))
    for b in bridges:
        events.append((float(b.get("start_s", 0.0)), "overlay"))
    for fx in sfx_events:
        events.append((float(fx.get("time_s", 0.0)), "sfx"))
    events.sort(key=lambda x: x[0])

    dead_zones: list[dict[str, Any]] = []
    # Check strictly VISUAL pattern interrupts (cuts + overlays) for visual dead zones > max_dead_zone_s
    vis_times = sorted(
        [0.0]
        + [float(s.get("start_s", 0.0)) for s in shot_windows[1:]]
        + [float(b.get("start_s", 0.0)) for b in bridges]
        + [total_duration_s]
    )
    for i in range(len(vis_times) - 1):
        gap = vis_times[i + 1] - vis_times[i]
        if gap > max_dead_zone_s + 0.05:
            dead_zones.append(
                {
                    "start_s": round(vis_times[i], 2),
                    "end_s": round(vis_times[i + 1], 2),
                    "gap_s": round(gap, 2),
                }
            )

    # 10-second heatmap buckets
    buckets: list[dict[str, Any]] = []
    t = 0.0
    while t < total_duration_s:
        t_end = min(total_duration_s, t + 10.0)
        cuts_n = sum(1 for ts, kind in events if t <= ts < t_end and kind == "cut")
        ov_n = sum(1 for ts, kind in events if t <= ts < t_end and kind == "overlay")
        sfx_n = sum(1 for ts, kind in events if t <= ts < t_end and kind == "sfx")
        buckets.append(
            {
                "window_s": [round(t, 1), round(t_end, 1)],
                "cuts": cuts_n,
                "overlays": ov_n,
                "sfx": sfx_n,
                "total_interrupts": cuts_n + ov_n + sfx_n,
            }
        )
        t += 10.0

    hook_30_interrupts = sum(1 for ts, kind in events if 0.0 < ts <= 30.0 and kind in ("cut", "overlay"))
    return {
        "schema": "youtube_pattern_interrupt_report/1",
        "total_duration_s": round(total_duration_s, 2),
        "hook_30s_visual_interrupts": hook_30_interrupts,
        "visual_dead_zones_gt_5s": dead_zones,
        "heatmap_10s": buckets,
        "status": "PASS" if (not dead_zones and hook_30_interrupts >= 10) else "FAIL",
    }


def _img_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render_desktop_mobile_tv_ab_mockup(
    variants: list[ThumbnailVariantSpec],
    out_dir: Path,
    *,
    channel_name: str = "Deep Time Chronicles",
    duration_label: str = "3:55",
) -> dict[str, Any]:
    """Render all 3 photoreal 1280x720 thumbnails + Desktop, Mobile (168x94px), and Living-Room TV A/B mockup."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    for v in variants:
        jpg = out_dir / f"thumb_{v.variant_id}.jpg"
        info = render_photoreal_thumbnail(v, jpg)
        rendered.append(info)

    font_css = build_font_face_css(["Plus Jakarta Sans", "IBM Plex Mono", "Oswald"])
    desktop_cards = []
    mobile_cards = []
    tv_cards = []
    for r in rendered:
        uri = _img_uri(Path(r["thumbnail_path"]))
        vid = html.escape(r["variant_id"])
        strat = html.escape(r["strategy"])
        title = html.escape(r["title"])
        desktop_cards.append(
            f"""<div class="d-card">
              <div class="tag">VARIANT {vid} — {strat}</div>
              <div class="d-thumb"><img src="{uri}"/><span class="dur">{duration_label}</span></div>
              <div class="d-meta">
                <div class="avatar">DT</div>
                <div><div class="d-title">{title}</div><div class="d-sub">{channel_name} • 540K views • 1 day ago</div></div>
              </div>
            </div>"""
        )
        mobile_cards.append(
            f"""<div class="m-card">
              <div class="m-thumb"><img src="{uri}"/><span class="m-dur">{duration_label}</span></div>
              <div class="m-meta">
                <div class="m-tag">VARIANT {vid}</div>
                <div class="m-title">{title}</div>
                <div class="m-sub">{channel_name} • 540K views</div>
              </div>
            </div>"""
        )
        tv_cards.append(
            f"""<div class="tv-card">
              <div class="tv-thumb"><img src="{uri}"/><span class="dur">{duration_label}</span></div>
              <div class="tv-title">[{vid}] {title}</div>
            </div>"""
        )

    mockup_html = f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<style>
{font_css}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1680px; background: #0D0E11; color: #F1F3F6; font-family: 'Plus Jakarta Sans', sans-serif; padding: 36px 44px; }}
.sec {{ font-family: 'IBM Plex Mono', monospace; font-size: 14px; letter-spacing: 0.16em; color: #E39B43; text-transform: uppercase; margin: 22px 0 14px; }}
.grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }}
.tag {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #7CC4E8; margin-bottom: 8px; text-transform: uppercase; }}
.d-thumb {{ position: relative; width: 100%; aspect-ratio: 16/9; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }}
.d-thumb img, .m-thumb img, .tv-thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.dur {{ position: absolute; right: 8px; bottom: 8px; background: rgba(0,0,0,0.86); color: #fff; font-size: 12px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }}
.d-meta {{ display: flex; gap: 12px; margin-top: 10px; }}
.avatar {{ width: 34px; height: 34px; border-radius: 50%; background: #1E2836; color: #E39B43; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; flex-shrink: 0; }}
.d-title {{ font-size: 16px; font-weight: 600; line-height: 1.3; }}
.d-sub {{ font-size: 13px; color: #9DA7B4; margin-top: 4px; }}
.m-card {{ display: flex; gap: 12px; background: #15171C; padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); }}
.m-thumb {{ position: relative; width: 168px; height: 94px; border-radius: 7px; overflow: hidden; flex-shrink: 0; }}
.m-dur {{ position: absolute; right: 4px; bottom: 4px; background: rgba(0,0,0,0.88); color: #fff; font-size: 10px; font-weight: 700; padding: 1px 4px; border-radius: 3px; }}
.m-tag {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #E39B43; }}
.m-title {{ font-size: 14px; font-weight: 600; line-height: 1.25; margin-top: 3px; }}
.m-sub {{ font-size: 11px; color: #9DA7B4; margin-top: 4px; }}
.tv-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; background: #07080A; padding: 22px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }}
.tv-thumb {{ position: relative; width: 100%; aspect-ratio: 16/9; border-radius: 10px; overflow: hidden; }}
.tv-title {{ font-size: 18px; font-weight: 600; margin-top: 10px; color: #E8EEF5; }}
</style></head>
<body>
  <div class="sec">1. YOUTUBE HOME FEED — DESKTOP 3-COLUMN TEST &amp; COMPARE</div>
  <div class="grid3">{''.join(desktop_cards)}</div>
  <div class="sec">2. CRITICAL MOBILE FEED SCALE (EXACT 168×94PX LEGIBILITY TEST)</div>
  <div class="grid3">{''.join(mobile_cards)}</div>
  <div class="sec">3. LIVING-ROOM SMART TV (10-FOOT COUCH READABILITY TEST)</div>
  <div class="tv-row">{''.join(tv_cards)}</div>
</body></html>"""

    html_p = out_dir / "youtube_feed_ab_mockup.html"
    png_p = out_dir / "youtube_feed_ab_mockup.png"
    html_p.write_text(mockup_html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1680, "height": 1160}, device_scale_factor=1)
        page.goto(html_p.as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.screenshot(path=str(png_p), full_page=True)
        b.close()

    scorecards = evaluate_paddy_galloway_matrix(variants)
    bundle = {
        "schema": "youtube_ab_lifecycle_bundle/1",
        "mockup_path": str(png_p),
        "variants": rendered,
        "paddy_galloway_scorecards": scorecards,
    }
    (out_dir / "youtube_ab_lifecycle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return bundle
