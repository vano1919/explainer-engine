"""Unified Final-Frame QA Stage (B-14): measures every frame of a delivered output against the graded source.

NOTE: Default thresholds in ``DEFAULT_RANGES`` are starting engineering bands (not hard quotas) and require
calibration against owner-approved painted material before promotion to strict blocking gates.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_RANGES: dict[str, Any] = {
    "needs_owner_calibration": True,
    "key_object_margin_min": 0.03,
    "lost_mask_area_pass": 0.001,
    "lost_mask_area_review": 0.005,
    "valid_coverage_pass": 0.9995,
    "valid_coverage_review": 0.998,
    "edge_density_ratio_pass": (0.90, 1.15),
    "edge_density_ratio_review": (0.75, 1.30),
    "hf_band_ratio_pass": (0.85, 1.20),
    "hf_band_ratio_review": (0.65, 1.35),
    "halo_overshoot_pass": 0.05,
    "halo_overshoot_review": 0.08,
    "grain_spectrum_ratio_pass": (0.80, 1.20),
    "grain_spectrum_ratio_review": (0.65, 1.35),
    "channel_shift_pass": 2.0,
    "channel_shift_review": 4.0,
    "delta_e_pass": 2.0,
    "delta_e_review": 4.0,
    "lantern_clip_delta_pp_pass": 0.1,
    "lantern_clip_delta_pp_review": 0.5,
    "face_identity_cosine_pass": 0.92,
    "face_identity_cosine_review": 0.88,
    "temporal_static_flow_p95_pass": 0.5,
    "upscaler_default": "native",
}


def _radial_band_energy(gray: np.ndarray, low_frac: float = 0.25, high_frac: float = 0.75) -> tuple[float, float]:
    """Return (mid_high_energy, high_grain_energy) from 2D radial FFT power spectrum."""
    f = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32)))
    pwr = np.abs(f) ** 2
    h, w = gray.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - cx) / max(1.0, cx), (yy - cy) / max(1.0, cy))
    tot = float(pwr.sum()) + 1e-9
    mid_high = float(pwr[(r >= low_frac) & (r <= high_frac)].sum()) / tot
    high_grain = float(pwr[r > high_frac].sum()) / tot
    return mid_high, high_grain


def _edge_halo_overshoot(gray: np.ndarray) -> float:
    """Measure local luminance overshoot/undershoot around strong edges as a fraction of edge contrast."""
    import cv2

    g = gray.astype(np.float32)
    edges = cv2.Canny(np.clip(g, 0, 255).astype(np.uint8), 80, 180) > 0
    if not edges.any():
        return 0.0
    dil = cv2.dilate(g, np.ones((5, 5), np.uint8))
    ero = cv2.erode(g, np.ones((5, 5), np.uint8))
    contrast = np.maximum(dil - ero, 1.0)
    ring = cv2.dilate(edges.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    lap = np.abs(cv2.Laplacian(g, cv2.CV_32F, ksize=3))
    rel = (lap[ring] / (4.0 * contrast[ring]))
    return float(np.percentile(rel, 95)) if rel.size else 0.0


def _rgb_to_lab_delta_e(a_rgb: np.ndarray, b_rgb: np.ndarray) -> float:
    import cv2

    a_u8 = np.clip(a_rgb, 0, 255).astype(np.uint8)
    b_u8 = np.clip(b_rgb, 0, 255).astype(np.uint8)
    la = cv2.cvtColor(a_u8, cv2.COLOR_RGB2LAB).astype(np.float32)
    lb = cv2.cvtColor(b_u8, cv2.COLOR_RGB2LAB).astype(np.float32)
    return float(np.sqrt(np.sum((la - lb) ** 2, axis=-1)).mean())


def build_resize_encode_manifest(
    ops: list[dict[str, Any]] | None = None,
    *,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Build an authoritative manifest of every resize and lossy encode operation."""
    entries = [dict(x) for x in (ops or [])]
    probe: dict[str, Any] = {}
    if output_path is not None and Path(output_path).is_file():
        p = Path(output_path)
        probe["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name,r_frame_rate",
             "-of", "json", str(p)],
            capture_output=True, text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                streams = json.loads(res.stdout).get("streams") or []
                if streams:
                    probe.update(streams[0])
            except json.JSONDecodeError:
                pass
    resize_count = sum(1 for e in entries if e.get("op") == "resize" or e.get("resized"))
    encode_count = sum(1 for e in entries if e.get("op") == "encode" or e.get("encoded"))
    return {
        "schema": "resize_encode_manifest/1",
        "resize_count": resize_count,
        "encode_count": encode_count,
        "operations": entries,
        "output_probe": probe,
    }


def evaluate_final_frame_qa(
    delivered_frames: list[np.ndarray],
    source_frames: list[np.ndarray] | None = None,
    *,
    object_masks: list[dict[str, np.ndarray]] | None = None,
    valid_masks: list[np.ndarray] | None = None,
    hole_masks: list[np.ndarray] | None = None,
    lantern_masks: list[np.ndarray] | None = None,
    views: list[dict[str, Any]] | None = None,
    face_similarities: list[float | None] | None = None,
    resize_encode_ops: list[dict[str, Any]] | None = None,
    output_path: Path | str | None = None,
    ranges: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the unified final-frame QA stage across EVERY delivered frame, reporting worst-frame indices."""
    import cv2

    cfg = dict(DEFAULT_RANGES)
    if ranges:
        cfg.update(ranges)

    if not delivered_frames:
        return {"schema": "final_frame_qa/1", "status": "NOT_RUN", "passed": False, "reason": "no frames",
                "needs_owner_calibration": bool(cfg.get("needs_owner_calibration", True))}

    n = len(delivered_frames)
    H, W = delivered_frames[0].shape[:2]

    worst_margin = {"value": 1.0, "frame": 0}
    worst_lost_area = {"value": 0.0, "frame": 0}
    worst_valid_cov = {"value": 1.0, "frame": 0}
    worst_hole_exposed = {"value": 0.0, "frame": 0}
    worst_edge_ratio = {"value": 1.0, "frame": 0, "dev": 0.0}
    worst_hf_ratio = {"value": 1.0, "frame": 0, "dev": 0.0}
    worst_grain_ratio = {"value": 1.0, "frame": 0, "dev": 0.0}
    worst_halo = {"value": 0.0, "frame": 0}
    worst_chan_shift = {"value": 0.0, "frame": 0}
    worst_delta_e = {"value": 0.0, "frame": 0}
    worst_lantern_clip_pp = {"value": 0.0, "frame": 0}
    worst_face_cos: dict[str, Any] = {"value": None, "frame": None}
    worst_temporal_flow = {"value": 0.0, "frame": 0}

    g_prev = cv2.cvtColor(np.clip(delivered_frames[0], 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)

    for idx in range(n):
        fr = np.clip(delivered_frames[idx], 0, 255).astype(np.uint8)
        g = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # 1. Key-object/face margins & lost mask area
        if object_masks and idx < len(object_masks):
            for _oid, m in (object_masks[idx] or {}).items():
                m_bin = (np.asarray(m, dtype=np.float32) > 0.5)
                if m_bin.any():
                    ys, xs = np.nonzero(m_bin)
                    m_left = float(xs.min()) / W
                    m_right = float(W - 1 - xs.max()) / W
                    m_top = float(ys.min()) / H
                    m_bot = float(H - 1 - ys.max()) / H
                    min_m = min(m_left, m_right, m_top, m_bot)
                    if min_m < worst_margin["value"]:
                        worst_margin = {"value": round(min_m, 4), "frame": idx}
                    border_touch = float((m_bin[0, :].sum() + m_bin[-1, :].sum() + m_bin[:, 0].sum() + m_bin[:, -1].sum())) / max(1, m_bin.sum())
                    if border_touch > worst_lost_area["value"]:
                        worst_lost_area = {"value": round(border_touch, 4), "frame": idx}

        # 2. Valid-source coverage & exposed holes / black bars
        if valid_masks and idx < len(valid_masks) and valid_masks[idx] is not None:
            vc = float((np.asarray(valid_masks[idx], dtype=np.float32) > 0.5).mean())
            if vc < worst_valid_cov["value"]:
                worst_valid_cov = {"value": round(vc, 5), "frame": idx}
        else:
            # Check for pure black border rows/cols
            row_black = (fr.mean(axis=(1, 2)) < 2.0).mean()
            col_black = (fr.mean(axis=(0, 2)) < 2.0).mean()
            vc = 1.0 - max(float(row_black), float(col_black))
            if vc < worst_valid_cov["value"]:
                worst_valid_cov = {"value": round(vc, 5), "frame": idx}

        if hole_masks and idx < len(hole_masks) and hole_masks[idx] is not None:
            hc = float((np.asarray(hole_masks[idx], dtype=np.float32) > 0.5).mean())
            if hc > worst_hole_exposed["value"]:
                worst_hole_exposed = {"value": round(hc, 5), "frame": idx}

        # 3-6. Source-referenced comparisons (edge density, HF/grain spectrum, halo, colour/clipping)
        if source_frames and idx < len(source_frames) and source_frames[idx] is not None:
            src_fr = np.clip(source_frames[idx], 0, 255).astype(np.uint8)
            if src_fr.shape[:2] != (H, W):
                src_fr = cv2.resize(src_fr, (W, H), interpolation=cv2.INTER_LANCZOS4)
            sg = cv2.cvtColor(src_fr, cv2.COLOR_RGB2GRAY).astype(np.float32)

            e_del = float((cv2.Canny(fr, 80, 180) > 0).mean())
            e_src = float((cv2.Canny(src_fr, 80, 180) > 0).mean())
            er = e_del / max(1e-6, e_src) if e_src > 1e-6 else 1.0
            if abs(er - 1.0) > worst_edge_ratio["dev"]:
                worst_edge_ratio = {"value": round(er, 4), "frame": idx, "dev": abs(er - 1.0)}

            mh_d, hg_d = _radial_band_energy(g)
            mh_s, hg_s = _radial_band_energy(sg)
            hfr = mh_d / max(1e-9, mh_s) if mh_s > 1e-9 else 1.0
            grr = hg_d / max(1e-9, hg_s) if hg_s > 1e-9 else 1.0
            if abs(hfr - 1.0) > worst_hf_ratio["dev"]:
                worst_hf_ratio = {"value": round(hfr, 4), "frame": idx, "dev": abs(hfr - 1.0)}
            if abs(grr - 1.0) > worst_grain_ratio["dev"]:
                worst_grain_ratio = {"value": round(grr, 4), "frame": idx, "dev": abs(grr - 1.0)}

            cs = float(np.max(np.abs(fr.astype(np.float32).mean(axis=(0, 1)) - src_fr.astype(np.float32).mean(axis=(0, 1)))))
            if cs > worst_chan_shift["value"]:
                worst_chan_shift = {"value": round(cs, 3), "frame": idx}

            de = _rgb_to_lab_delta_e(fr, src_fr)
            if de > worst_delta_e["value"]:
                worst_delta_e = {"value": round(de, 3), "frame": idx}

            lm = (lantern_masks[idx] > 0.3) if (lantern_masks and idx < len(lantern_masks) and lantern_masks[idx] is not None) else np.ones((H, W), bool)
            if lm.any():
                clip_d = float((g[lm] >= 250.0).mean() * 100.0)
                clip_s = float((sg[lm] >= 250.0).mean() * 100.0)
                d_pp = max(0.0, clip_d - clip_s)
                if d_pp > worst_lantern_clip_pp["value"]:
                    worst_lantern_clip_pp = {"value": round(d_pp, 3), "frame": idx}

        # 5. Halo overshoot
        ho = _edge_halo_overshoot(g)
        if ho > worst_halo["value"]:
            worst_halo = {"value": round(ho, 4), "frame": idx}

        # 7. Face identity
        if face_similarities and idx < len(face_similarities) and face_similarities[idx] is not None:
            sim = float(face_similarities[idx])
            if worst_face_cos["value"] is None or sim < worst_face_cos["value"]:
                worst_face_cos = {"value": round(sim, 4), "frame": idx}

        # 8. Temporal flicker (camera-compensated)
        if idx > 0:
            if views and idx < len(views):
                v0, vi = views[idx - 1], views[idx]
                ds = float(vi.get("s", 1.0)) / max(1e-6, float(v0.get("s", 1.0)))
                dcx = (float(vi.get("cx", 0.5)) - float(v0.get("cx", 0.5))) * W
                dcy = (float(vi.get("cy", 0.5)) - float(v0.get("cy", 0.5))) * H
                mat = np.float32([[ds, 0.0, (1.0 - ds) * (W * 0.5) - dcx], [0.0, ds, (1.0 - ds) * (H * 0.5) - dcy]])
                g_al = cv2.warpAffine(g, mat, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
            else:
                flow0 = cv2.calcOpticalFlowFarneback(g_prev, g, None, 0.5, 2, 15, 2, 5, 1.1, 0)
                mat = np.float32([[1.0, 0.0, -float(np.median(flow0[..., 0]))], [0.0, 1.0, -float(np.median(flow0[..., 1]))]])
                g_al = cv2.warpAffine(g, mat, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            res_flow = cv2.calcOpticalFlowFarneback(g_prev, g_al, None, 0.5, 2, 15, 2, 5, 1.1, 0)
            p95_f = float(np.percentile(np.hypot(res_flow[..., 0], res_flow[..., 1]), 95))
            if p95_f > worst_temporal_flow["value"]:
                worst_temporal_flow = {"value": round(p95_f, 4), "frame": idx}
        g_prev = g

    manifest = build_resize_encode_manifest(resize_encode_ops, output_path=output_path)

    failures: list[str] = []
    reviews: list[str] = []
    if worst_valid_cov["value"] < cfg["valid_coverage_review"]:
        failures.append(f"valid_coverage={worst_valid_cov['value']}@{worst_valid_cov['frame']}")
    elif worst_valid_cov["value"] < cfg["valid_coverage_pass"]:
        reviews.append(f"valid_coverage={worst_valid_cov['value']}@{worst_valid_cov['frame']}")
    if worst_lost_area["value"] > cfg["lost_mask_area_review"]:
        failures.append(f"lost_mask_area={worst_lost_area['value']}@{worst_lost_area['frame']}")
    elif worst_lost_area["value"] > cfg["lost_mask_area_pass"]:
        reviews.append(f"lost_mask_area={worst_lost_area['value']}@{worst_lost_area['frame']}")
    if worst_halo["value"] > cfg["halo_overshoot_review"]:
        failures.append(f"halo_overshoot={worst_halo['value']}@{worst_halo['frame']}")
    elif worst_halo["value"] > cfg["halo_overshoot_pass"]:
        reviews.append(f"halo_overshoot={worst_halo['value']}@{worst_halo['frame']}")
    if worst_face_cos["value"] is not None:
        if worst_face_cos["value"] < cfg["face_identity_cosine_review"]:
            failures.append(f"face_identity={worst_face_cos['value']}@{worst_face_cos['frame']}")
        elif worst_face_cos["value"] < cfg["face_identity_cosine_pass"]:
            reviews.append(f"face_identity={worst_face_cos['value']}@{worst_face_cos['frame']}")

    status = "FAIL" if failures else ("REVIEW" if reviews else "PASS")
    return {
        "schema": "final_frame_qa/1",
        "status": status,
        "passed": status == "PASS",
        "frames_checked": n,
        "needs_owner_calibration": bool(cfg.get("needs_owner_calibration", True)),
        "ranges": cfg,
        "metrics": {
            "key_object_margin": worst_margin,
            "lost_mask_area": worst_lost_area,
            "valid_coverage": worst_valid_cov,
            "hole_exposed": worst_hole_exposed,
            "edge_density_ratio": {k: v for k, v in worst_edge_ratio.items() if k != "dev"},
            "hf_spectrum_ratio": {k: v for k, v in worst_hf_ratio.items() if k != "dev"},
            "grain_spectrum_ratio": {k: v for k, v in worst_grain_ratio.items() if k != "dev"},
            "halo_overshoot": worst_halo,
            "channel_shift": worst_chan_shift,
            "delta_e": worst_delta_e,
            "lantern_clip_delta_pp": worst_lantern_clip_pp,
            "face_identity": worst_face_cos if worst_face_cos["value"] is not None else {"status": "NOT_MEASURED"},
            "temporal_flicker_p95": worst_temporal_flow,
        },
        "resize_encode_manifest": manifest,
        "failures": failures,
        "reviews": reviews,
    }
