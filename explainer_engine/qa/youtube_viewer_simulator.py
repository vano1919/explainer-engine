"""YouTube Real-Viewer Panel Report Validator & Retention Curve Visualizer.

Validates the Clean-Room 3-Persona Real-Viewer Panel JSON (``youtube_viewer_panel/1``),
renders a broadcast-grade ``youtube_retention_curve.png`` showing the 15-second audience
retention trajectory alongside the YouTube 72% @ 0:30 benchmark line, and enforces
fail-closed release thresholds.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def verify_viewer_panel_report(
    report_path: Path,
    *,
    expected_sha256: str | None = None,
    min_retention_30s_pct: float = 72.0,
    min_avg_view_pct: float = 58.0,
    min_readiness_score: float = 8.5,
) -> dict[str, Any]:
    """Verify ``youtube_viewer_panel/1`` fail-closed against retention & A/B CTR targets."""
    findings: list[str] = []
    if not report_path.is_file():
        return {"status": "FAIL", "findings": [f"Missing viewer panel report: {report_path}"]}
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "findings": [f"Malformed viewer panel JSON: {exc}"]}

    if data.get("schema") != "youtube_viewer_panel/1":
        findings.append(f"Invalid schema {data.get('schema')!r}")
    if expected_sha256 and str(data.get("video_sha256", "")).lower() != expected_sha256.lower():
        findings.append("video_sha256 mismatch in viewer panel report")

    ret30 = float(data.get("aggregate_retention_at_30s_pct", 0.0))
    avg_pct = float(data.get("aggregate_avg_view_pct", 0.0))
    score = float(data.get("overall_youtube_readiness_score", 0.0))
    crit = list(data.get("critical_drop_off_defects") or [])
    personas = list(data.get("personas") or [])

    if len(personas) < 3:
        findings.append(f"Viewer panel requires >= 3 personas, got {len(personas)}")
    if ret30 < min_retention_30s_pct:
        findings.append(f"Retention @ 0:30 is {ret30:.1f}% < required {min_retention_30s_pct:.1f}%")
    if avg_pct < min_avg_view_pct:
        findings.append(f"Average view percentage is {avg_pct:.1f}% < required {min_avg_view_pct:.1f}%")
    if score < min_readiness_score:
        findings.append(f"YouTube readiness score {score:.2f} < required {min_readiness_score:.2f}")
    if crit:
        findings.append(f"Viewer panel flagged {len(crit)} critical drop-off defect(s)")
    if data.get("verdict") != "APPROVE":
        findings.append(f"Viewer panel verdict is {data.get('verdict')!r} (expected 'APPROVE')")

    winner = ((data.get("ab_packaging") or {}).get("winner")) or ""
    if winner not in {"A", "B", "C"}:
        findings.append(f"Missing valid A/B/C packaging winner, got {winner!r}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "retention_at_30s_pct": round(ret30, 1),
        "avg_view_pct": round(avg_pct, 1),
        "overall_youtube_readiness_score": round(score, 2),
        "ab_winner": winner,
        "findings": findings,
    }


def render_retention_curve_png(report_data: dict[str, Any], out_png: Path) -> Path:
    """Render a clean dark-studio YouTube Audience Retention Curve chart PNG."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1400, 760
    img = np.full((h, w, 3), (18, 15, 11), dtype=np.uint8)  # BGR deep obsidian

    pad_l, pad_r, pad_t, pad_b = 110, 70, 110, 95
    pw = w - pad_l - pad_r
    ph = h - pad_t - pad_b

    # Title
    cv2.putText(
        img,
        "YOUTUBE 3-PERSONA AUDIENCE RETENTION CURVE",
        (pad_l, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.95,
        (245, 247, 250),
        2,
        cv2.LINE_AA,
    )
    ret30 = float(report_data.get("aggregate_retention_at_30s_pct", 0.0))
    avg_v = float(report_data.get("aggregate_avg_view_pct", 0.0))
    winner = (report_data.get("ab_packaging") or {}).get("winner", "?")
    cv2.putText(
        img,
        f"Retention @ 0:30: {ret30:.1f}%  |  Avg View: {avg_v:.1f}%  |  A/B Winner: Variant {winner}",
        (pad_l, 86),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (232, 196, 124),
        1,
        cv2.LINE_AA,
    )

    # Grid lines 0..100%
    for pct in (0, 20, 40, 60, 72, 80, 100):
        y = int(round(pad_t + ph * (1.0 - pct / 100.0)))
        color = (70, 145, 215) if pct == 72 else (45, 42, 38)
        thick = 2 if pct == 72 else 1
        cv2.line(img, (pad_l, y), (pad_l + pw, y), color, thick, cv2.LINE_AA)
        lbl = f"{pct}% (30s Target)" if pct == 72 else f"{pct}%"
        cv2.putText(img, lbl, (18, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (185, 195, 205), 1, cv2.LINE_AA)

    pts_raw = list(report_data.get("retention_curve_15s") or [])
    if pts_raw:
        max_t = max(float(p.get("time_s", 1.0)) for p in pts_raw) or 180.0
        coords: list[tuple[int, int]] = []
        for p in pts_raw:
            ts = float(p.get("time_s", 0.0))
            val = p.get("retention_pct") if p.get("retention_pct") is not None else p.get("pct", 0.0)
            pct = max(0.0, min(100.0, float(val)))
            x = int(round(pad_l + (ts / max_t) * pw))
            y = int(round(pad_t + ph * (1.0 - pct / 100.0)))
            coords.append((x, y))
            mm = int(ts) // 60
            ss = int(ts) % 60
            cv2.putText(
                img,
                f"{mm}:{ss:02d}",
                (x - 18, pad_t + ph + 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (170, 180, 192),
                1,
                cv2.LINE_AA,
            )

        # Shaded fill under curve
        poly = np.array(coords + [(coords[-1][0], pad_t + ph), (coords[0][0], pad_t + ph)], dtype=np.int32)
        overlay = img.copy()
        cv2.fillPoly(overlay, [poly], (67, 155, 227))
        cv2.addWeighted(overlay, 0.22, img, 0.78, 0, img)

        for i in range(len(coords) - 1):
            cv2.line(img, coords[i], coords[i + 1], (67, 165, 235), 4, cv2.LINE_AA)
        for (x, y), p in zip(coords, pts_raw, strict=False):
            val = p.get("retention_pct") if p.get("retention_pct") is not None else p.get("pct", 0.0)
            cv2.circle(img, (x, y), 6, (255, 245, 230), -1, cv2.LINE_AA)
            cv2.circle(img, (x, y), 6, (67, 165, 235), 2, cv2.LINE_AA)
            cv2.putText(
                img,
                f"{int(round(float(val)))}%",
                (x - 16, y - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (245, 247, 250),
                1,
                cv2.LINE_AA,
            )

    cv2.imwrite(str(out_png), img)
    return out_png
