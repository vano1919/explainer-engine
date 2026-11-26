"""YouTube A/B/C Packaging Lab (Photorealistic 1280x720 Thumbnails + Desktop & 168x94 Mobile Feed Mockup).

Replaces legacy cartoon ``Bangers-Regular.ttf`` thumbnail generation with super-realistic
35mm documentary photography + modern SIL OFL display typography (``Oswald`` / ``Cinzel``)
rendered via Playwright Headless Chrome, plus a realistic YouTube Home Feed A/B/C comparison
mockup (both Desktop 3-column grid and critical **168x94px Mobile** scale!) and ready-to-upload
YouTube Studio "Test & Compare" export folder.
"""
from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from explainer_engine.design_system.tokens import build_font_face_css


@dataclass(slots=True)
class ThumbnailVariantSpec:
    variant_id: str  # "A", "B", "C"
    strategy: str  # e.g., "Survival Stakes", "Curiosity / Scale", "Documentary Awe"
    title: str
    overlay_top: str  # 1-2 short eyebrow words (optional)
    overlay_big: str  # MAX 2-3 punchy words for 168x94px mobile readability!
    image_path: Path
    accent_hex: str = "#E39B43"
    text_align: str = "left"  # left or bottom


def _img_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render_photoreal_thumbnail(spec: ThumbnailVariantSpec, out_jpg: Path) -> dict[str, Any]:
    """Render one crisp 1280x720 YouTube photoreal thumbnail via Playwright + modern SIL OFL typography."""
    if not spec.image_path.is_file():
        raise FileNotFoundError(f"Thumbnail photo not found: {spec.image_path}")
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    font_css = build_font_face_css(["Oswald", "Cinzel", "IBM Plex Mono", "Plus Jakarta Sans"])
    img_data = _img_uri(spec.image_path)

    scrim_css = (
        "linear-gradient(90deg, rgba(4,7,12,0.88) 0%, rgba(4,7,12,0.52) 44%, rgba(4,7,12,0.06) 78%)"
        if spec.text_align == "left"
        else "linear-gradient(0deg, rgba(4,7,12,0.92) 0%, rgba(4,7,12,0.46) 42%, rgba(4,7,12,0.08) 76%)"
    )
    pos_css = (
        "left: 58px; top: 50%; transform: translateY(-50%); text-align: left; max-width: 640px;"
        if spec.text_align == "left"
        else "left: 58px; bottom: 48px; text-align: left; max-width: 960px;"
    )

    page_html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"/>
<style>
{font_css}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1280px; height: 720px; overflow: hidden; background: #000; }}
.frame {{
  position: relative; width: 1280px; height: 720px; overflow: hidden;
}}
.bg {{
  position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
  filter: contrast(1.12) saturate(1.14);
}}
.scrim {{ position: absolute; inset: 0; background: {scrim_css}; }}
.vignette {{
  position: absolute; inset: 0;
  box-shadow: inset 0 0 110px rgba(0,0,0,0.68);
}}
.copy {{ position: absolute; {pos_css} z-index: 5; }}
.eyebrow {{
  display: inline-block; padding: 6px 14px; margin-bottom: 14px;
  font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase;
  background: rgba(8,12,18,0.82); color: {spec.accent_hex};
  border-left: 4px solid {spec.accent_hex};
}}
.big {{
  font-family: 'Oswald', sans-serif; font-size: 124px; font-weight: 700;
  line-height: 0.96; letter-spacing: 0.02em; text-transform: uppercase;
  color: #FFFFFF;
  text-shadow: 0 8px 30px rgba(0,0,0,0.96), 0 3px 8px rgba(0,0,0,0.95);
}}
.big em {{ font-style: normal; color: {spec.accent_hex}; }}
</style>
</head>
<body>
<div class="frame">
  <img class="bg" src="{img_data}" />
  <div class="scrim"></div>
  <div class="vignette"></div>
  <div class="copy">
    {f'<div class="eyebrow">{html.escape(spec.overlay_top)}</div>' if spec.overlay_top else ''}
    <div class="big">{spec.overlay_big}</div>
  </div>
</div>
</body>
</html>"""

    html_tmp = out_jpg.with_suffix(".html")
    html_tmp.write_text(page_html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(html_tmp.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.screenshot(path=str(out_jpg), type="jpeg", quality=93)
        b.close()

    return {
        "variant_id": spec.variant_id,
        "strategy": spec.strategy,
        "title": spec.title,
        "overlay_top": spec.overlay_top,
        "overlay_big": spec.overlay_big,
        "thumbnail_path": str(out_jpg),
        "width": 1280,
        "height": 720,
    }


def render_youtube_feed_ab_mockup(
    rendered_variants: list[dict[str, Any]],
    out_png: Path,
    *,
    channel_name: str = "DEEP TIME CHRONICLES",
    duration_label: str = "3:00",
) -> Path:
    """Build a realistic YouTube Dark-Mode Desktop + Mobile (168x94px) Home Feed A/B/C comparison mockup."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    font_css = build_font_face_css(["Plus Jakarta Sans", "IBM Plex Mono"])

    desktop_cards = []
    mobile_cards = []
    for v in rendered_variants:
        uri = _img_uri(Path(v["thumbnail_path"]))
        vid = html.escape(str(v["variant_id"]))
        strat = html.escape(str(v["strategy"]))
        title = html.escape(str(v["title"]))
        desktop_cards.append(
            f"""
            <div class="yt-card">
              <div class="var-badge">VARIANT {vid} — {strat}</div>
              <div class="thumb-wrap">
                <img src="{uri}" />
                <span class="dur">{duration_label}</span>
              </div>
              <div class="meta">
                <div class="avatar">DT</div>
                <div>
                  <div class="yt-title">{title}</div>
                  <div class="yt-sub">{html.escape(channel_name)} • 412K views • 2 days ago</div>
                </div>
              </div>
            </div>"""
        )
        mobile_cards.append(
            f"""
            <div class="mob-row">
              <div class="mob-thumb-wrap">
                <img src="{uri}" />
                <span class="mob-dur">{duration_label}</span>
              </div>
              <div class="mob-meta">
                <div class="mob-tag">VARIANT {vid}</div>
                <div class="mob-title">{title}</div>
                <div class="mob-sub">{html.escape(channel_name)} • 412K views</div>
              </div>
            </div>"""
        )

    mockup_html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"/>
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  width: 1600px; height: 1020px; background: #0F0F0F; color: #F1F1F1;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif; padding: 36px 44px;
}}
h2 {{
  font-family: 'IBM Plex Mono', monospace; font-size: 16px; letter-spacing: 0.16em;
  color: #E39B43; text-transform: uppercase; margin-bottom: 18px;
}}
.desktop-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; margin-bottom: 42px; }}
.var-badge {{
  font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #7CC4E8;
  margin-bottom: 8px; letter-spacing: 0.1em;
}}
.thumb-wrap {{ position: relative; width: 100%; aspect-ratio: 16/9; border-radius: 12px; overflow: hidden; background: #181818; }}
.thumb-wrap img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.dur {{
  position: absolute; right: 8px; bottom: 8px; background: rgba(0,0,0,0.85);
  color: #FFF; font-size: 12px; font-weight: 600; padding: 2px 6px; border-radius: 4px;
}}
.meta {{ display: flex; gap: 12px; margin-top: 12px; }}
.avatar {{
  width: 36px; height: 36px; border-radius: 50%; background: #263547; color: #E39B43;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0;
}}
.yt-title {{ font-size: 16px; font-weight: 600; line-height: 1.3; color: #F1F1F1; }}
.yt-sub {{ font-size: 13px; color: #AAAAAA; margin-top: 4px; }}

.mobile-section {{
  border-top: 1px solid #272727; padding-top: 28px;
}}
.mobile-strip {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }}
.mob-row {{
  display: flex; gap: 12px; background: #161616; padding: 14px; border-radius: 12px;
  border: 1px solid #262626; align-items: flex-start;
}}
.mob-thumb-wrap {{
  position: relative; width: 168px; height: 94px; border-radius: 8px; overflow: hidden; flex-shrink: 0;
}}
.mob-thumb-wrap img {{ width: 168px; height: 94px; object-fit: cover; display: block; }}
.mob-dur {{
  position: absolute; right: 4px; bottom: 4px; background: rgba(0,0,0,0.86);
  color: #FFF; font-size: 10px; font-weight: 600; padding: 1px 4px; border-radius: 3px;
}}
.mob-tag {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #E39B43; margin-bottom: 4px; }}
.mob-title {{ font-size: 13px; font-weight: 600; line-height: 1.3; color: #F1F1F1; }}
.mob-sub {{ font-size: 11px; color: #AAAAAA; margin-top: 4px; }}
</style>
</head>
<body>
  <h2>YouTube Home Feed A/B/C Test &amp; Compare — Desktop Scale</h2>
  <div class="desktop-grid">{''.join(desktop_cards)}</div>
  <div class="mobile-section">
    <h2>Critical Mobile Up-Next / Search Scale (Exact 168×94px Readability Test)</h2>
    <div class="mobile-strip">{''.join(mobile_cards)}</div>
  </div>
</body>
</html>"""

    tmp_html = out_png.with_suffix(".html")
    tmp_html.write_text(mockup_html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1600, "height": 1020}, device_scale_factor=1)
        page.goto(tmp_html.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.screenshot(path=str(out_png), type="png")
        b.close()
    return out_png


def export_youtube_studio_ab_bundle(
    variants: list[ThumbnailVariantSpec],
    out_dir: Path,
    *,
    chapters: list[tuple[str, str]] | None = None,
    duration_label: str = "3:00",
) -> dict[str, Any]:
    """Generate all 3 photoreal A/B/C thumbnails, Desktop+Mobile Feed Mockup, and Studio upload bundle."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    for v in variants:
        jpg = out_dir / f"thumb_{v.variant_id}.jpg"
        rendered.append(render_photoreal_thumbnail(v, jpg))

    mockup_png = out_dir / "youtube_feed_ab_mockup.png"
    render_youtube_feed_ab_mockup(rendered, mockup_png, duration_label=duration_label)

    (out_dir / "titles_ab.json").write_text(
        json.dumps({"schema": "youtube_ab_bundle/1", "variants": rendered}, indent=2),
        encoding="utf-8",
    )
    if chapters:
        lines = [f"{tc} {lbl}" for tc, lbl in chapters]
        (out_dir / "chapters.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "schema": "youtube_ab_bundle/1",
        "out_dir": str(out_dir),
        "mockup_png": str(mockup_png),
        "variants": rendered,
    }
