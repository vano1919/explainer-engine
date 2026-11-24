"""Post-Assembly Visual-Aware Sound Spotting, Real Asset Resolution, Mixing, and Cut-Fade A/B.

Honest capability scope:
- Visual event detection uses luminance frame-difference thresholding across sampled frames
  (``detect_visual_event_timestamps``). It detects visual cuts and luminance/motion spikes;
  it does NOT perform semantic audio-visual scene understanding.
- Every accepted cue MUST resolve to a real on-disk WAV asset from a verified sound library
  manifest with matching SHA-256, valid WAV headers, and commercial-safe license metadata.
  Missing, fabricated, corrupted, or unlicensed references are rejected loudly.
- Accepted cues integrate directly into the episode sound plan and mix onto the real audio
  track with peak limiting and timing validation.
- ``measure_audio_cut_ab`` is an experimental boundary-discontinuity measurement utility
  (30ms linear crossfade vs hard cut), not a claim that 30ms is universally optimal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.scripting.docudrama_structure import validate_post_assembly_spotting

SPOTTING_SCHEMA = "post_assembly_spotting/2"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Required file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_video_duration_s(video_path: Path) -> float:
    if not video_path.is_file():
        raise ContractError(f"Video file not found: {video_path}")
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return float(p.stdout.strip())


def detect_visual_event_timestamps(
    preview_video: Path,
    work_dir: Path,
    *,
    sample_fps: float = 4.0,
    diff_threshold: float = 0.04,
) -> list[dict[str, Any]]:
    """Sample frames from ``preview_video`` and locate visual cut/luminance-change spikes."""
    if not preview_video.is_file():
        raise ContractError(f"Preview video not found: {preview_video}")
    frames_dir = work_dir / "spotting_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("f_*.png"):
        old.unlink()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(preview_video),
            "-vf",
            f"fps={sample_fps},scale=160:90",
            str(frames_dir / "f_%04d.png"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    frame_files = sorted(frames_dir.glob("f_*.png"))
    if len(frame_files) < 2:
        return []

    arrs = [np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0 for p in frame_files]
    events: list[dict[str, Any]] = []
    for idx in range(len(arrs) - 1):
        delta = float(np.abs(arrs[idx + 1] - arrs[idx]).mean())
        if delta >= diff_threshold:
            ts = round((idx + 1) / sample_fps, 3)
            event_kind = "hard_cut_candidate" if delta >= 0.18 else "transition_or_motion_peak"
            events.append(
                {
                    "visual_timestamp_s": ts,
                    "frame_delta": round(delta, 4),
                    "event_kind": event_kind,
                    "detection_method": "grayscale_frame_l1_delta",
                    "suggested_cue": "whoosh" if event_kind == "hard_cut_candidate" else "ambience_swell",
                }
            )
    return events


def _validate_wav_file(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
    except (wave.Error, OSError) as exc:
        raise ContractError(f"Invalid WAV sound asset {path}: {exc}") from exc
    if nframes <= 0 or framerate <= 0 or sampwidth != 2:
        raise ContractError(
            f"Sound asset {path} must be non-empty 16-bit PCM WAV (got frames={nframes}, sr={framerate}, width={sampwidth})"
        )
    return {
        "channels": channels,
        "sample_rate": framerate,
        "nframes": nframes,
        "duration_s": round(nframes / framerate, 4),
    }


def _validate_license_metadata(item: dict[str, Any]) -> dict[str, Any]:
    lic = item.get("licence") or item.get("license")
    if not isinstance(lic, dict):
        raise ContractError(f"Sound asset {item.get('id')!r} is missing license/licence metadata")
    lic_type = str(lic.get("type") or lic.get("status") or "").strip().lower()
    if not lic_type or lic_type in ("unknown", "unverified", "none"):
        raise ContractError(f"Sound asset {item.get('id')!r} has unverified license status {lic_type!r}")
    if lic.get("commercial_use") is not True:
        raise ContractError(f"Sound asset {item.get('id')!r} does not have commercial_use=true")
    return {
        "type": lic_type,
        "commercial_use": True,
        "attribution_required": bool(lic.get("attribution_required", False)),
        "note": str(lic.get("note") or ""),
        "url": str(lic.get("url") or lic.get("source_url") or ""),
    }


def resolve_sound_asset(
    library_root: Path,
    *,
    asset_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve and verify a real on-disk WAV sound asset from ``library_root/manifest.json``."""
    lib = Path(library_root)
    manifest_p = lib / "manifest.json"
    if not manifest_p.is_file():
        raise ContractError(f"Sound library manifest not found: {manifest_p}")
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    items = manifest.get("items") or []
    if not isinstance(items, list) or not items:
        raise ContractError(f"Sound library manifest {manifest_p} contains no items")

    chosen: dict[str, Any] | None = None
    if asset_id:
        for it in items:
            if it.get("id") == asset_id:
                chosen = it
                break
        if chosen is None:
            raise ContractError(f"Sound asset id {asset_id!r} not found in {manifest_p}")
    else:
        wanted = {t.lower() for t in (tags or []) if t}
        best_score = -1
        for it in items:
            rel_file = it.get("file")
            if not rel_file or not (lib / rel_file).is_file():
                continue
            item_tags = {str(t).lower() for t in (it.get("tags") or [])}
            score = len(wanted & item_tags) if wanted else 1
            if score > best_score:
                best_score = score
                chosen = it
        if chosen is None:
            raise ContractError(f"No on-disk WAV asset in {lib} matched tags={sorted(wanted)}")

    rel_file = chosen.get("file")
    if not rel_file:
        raise ContractError(f"Sound asset {chosen.get('id')!r} has no 'file' field")
    lib_resolved = lib.resolve()
    wav_path = (lib_resolved / str(rel_file)).resolve()
    if not wav_path.is_relative_to(lib_resolved):
        raise ContractError(f"Sound asset path escapes sound library root: {rel_file!r}")
    if not wav_path.is_file():
        raise ContractError(f"Sound asset file missing on disk: {wav_path}")

    actual_sha = sha256_file(wav_path)
    expected_sha = chosen.get("sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise ContractError(f"Sound asset {chosen.get('id')!r} lacks a valid 64-char sha256 in manifest")
    if actual_sha != expected_sha:
        raise ContractError(
            f"Sound asset {chosen.get('id')!r} SHA-256 mismatch: manifest={expected_sha}, disk={actual_sha}"
        )

    wav_info = _validate_wav_file(wav_path)
    lic_info = _validate_license_metadata(chosen)
    return {
        "asset_id": str(chosen["id"]),
        "asset_path": str(wav_path),
        "asset_rel_path": str(rel_file),
        "asset_sha256": actual_sha,
        "duration_s": wav_info["duration_s"],
        "sample_rate": wav_info["sample_rate"],
        "channels": wav_info["channels"],
        "licence": lic_info,
        "source": "free_library",
    }


def resolve_spotted_cues(
    preview_video: Path,
    candidate_events: list[dict[str, Any]],
    library_root: Path,
    *,
    asset_map: dict[str, str] | None = None,
    require_human_approval: bool = False,
) -> list[dict[str, Any]]:
    """Resolve candidate visual events into validated, provenance-tracked sound cues."""
    video_dur = probe_video_duration_s(preview_video)
    resolved_cues: list[dict[str, Any]] = []
    for idx, ev in enumerate(candidate_events):
        ts = float(ev["visual_timestamp_s"])
        if ts < 0.0 or ts > video_dur:
            raise ContractError(f"Candidate cue {idx} timestamp {ts}s outside video duration {video_dur:.3f}s")
        suggested = str(ev.get("suggested_cue") or ev.get("cue") or "whoosh")
        explicit_id = (asset_map or {}).get(suggested) or ev.get("asset_id")
        asset = resolve_sound_asset(library_root, asset_id=explicit_id, tags=[suggested])
        approval = str(ev.get("approval_status") or ("pending_review" if require_human_approval else "approved"))
        if approval not in ("approved", "pending_review", "rejected"):
            raise ContractError(f"Invalid cue approval_status: {approval!r}")
        resolved_cues.append(
            {
                "cue_id": f"spot_{idx + 1:03d}",
                "visual_timestamp_s": round(ts, 3),
                "frame_delta": float(ev.get("frame_delta", 0.0)),
                "event_kind": str(ev.get("event_kind", "visual_delta_peak")),
                "cue": suggested,
                "source": asset["source"],
                "asset_id": asset["asset_id"],
                "asset_path": asset["asset_path"],
                "asset_sha256": asset["asset_sha256"],
                "asset_duration_s": asset["duration_s"],
                "sample_rate": asset["sample_rate"],
                "licence": asset["licence"],
                "approval_status": approval,
                "gain_db": float(ev.get("gain_db", -9.0)),
            }
        )
    return resolved_cues


def build_spotting_record(
    preview_video: Path,
    cues: list[dict[str, Any]],
    *,
    out_path: Path | None = None,
    require_verified_assets: bool = False,
) -> dict[str, Any]:
    """Assemble and validate a SHA-256-pinned post-assembly sound spotting record."""
    video_sha = sha256_file(preview_video)
    if require_verified_assets:
        for idx, cue in enumerate(cues):
            if cue.get("approval_status") == "rejected":
                continue
            ap = cue.get("asset_path")
            asha = cue.get("asset_sha256")
            if not ap or not Path(str(ap)).is_file():
                raise ContractError(f"Spotted cue {idx} references missing on-disk asset: {ap!r}")
            if not isinstance(asha, str) or len(asha) != 64 or sha256_file(Path(str(ap))) != asha:
                raise ContractError(f"Spotted cue {idx} asset SHA-256 verification failed for {ap!r}")
            if not isinstance(cue.get("licence"), dict) or cue["licence"].get("commercial_use") is not True:
                raise ContractError(f"Spotted cue {idx} lacks verified commercial-safe license metadata")

    record: dict[str, Any] = {
        "schema_version": SPOTTING_SCHEMA,
        "based_on_assembled_video": True,
        "assembled_video_path": str(preview_video),
        "assembled_video_sha256": video_sha,
        "detection_method": "grayscale_frame_l1_delta",
        "cues": list(cues),
    }
    validation = validate_post_assembly_spotting(record)
    record["validation"] = validation
    if out_path is not None:
        write_json_atomic(out_path, record)
    return record


def is_spotting_fresh(record: dict[str, Any], preview_video: Path) -> bool:
    """Return True iff the spotting record still matches the exact SHA-256 of ``preview_video`` on disk."""
    if not preview_video.is_file():
        return False
    return str(record.get("assembled_video_sha256", "")) == sha256_file(preview_video)


def integrate_spotted_cues_into_sound_plan(
    sound_plan_path: Path,
    spotting_record: dict[str, Any],
    *,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Merge approved, verified spotted cues into the episode sound plan JSON."""
    if not sound_plan_path.is_file():
        raise ContractError(f"Sound plan file not found: {sound_plan_path}")
    plan = json.loads(sound_plan_path.read_text(encoding="utf-8"))
    accepted = [
        c
        for c in (spotting_record.get("cues") or [])
        if c.get("approval_status", "approved") == "approved" and c.get("asset_path")
    ]
    plan["post_assembly_spotting"] = {
        "schema_version": spotting_record.get("schema_version", SPOTTING_SCHEMA),
        "assembled_video_sha256": spotting_record.get("assembled_video_sha256"),
        "accepted_cue_count": len(accepted),
        "cues": accepted,
    }
    dest = out_path or sound_plan_path
    write_json_atomic(dest, plan)
    return plan


def _read_pcm16_mono(wav_path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def mix_spotted_cues_onto_audio(
    base_wav: Path,
    spotting_record: dict[str, Any],
    out_wav: Path,
) -> dict[str, Any]:
    """Mix approved spotted sound assets onto ``base_wav`` at their exact visual timestamps, preserving channels."""
    if not base_wav.is_file():
        raise ContractError(f"Base audio WAV not found: {base_wav}")
    with wave.open(str(base_wav), "rb") as wf:
        base_sr = wf.getframerate()
        base_ch = wf.getnchannels()
        raw_base = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    mixed = raw_base.reshape(-1, base_ch).copy()
    n_frames = mixed.shape[0]
    placed: list[dict[str, Any]] = []

    for cue in spotting_record.get("cues") or []:
        if cue.get("approval_status", "approved") != "approved":
            continue
        asset_p = Path(str(cue.get("asset_path") or ""))
        if not asset_p.is_file():
            raise ContractError(f"Spotted cue {cue.get('cue_id')} asset missing on disk: {asset_p}")
        expected_sha = str(cue.get("asset_sha256") or "")
        if len(expected_sha) != 64 or sha256_file(asset_p) != expected_sha:
            raise ContractError(f"Spotted cue {cue.get('cue_id')} failed SHA-256 check before mixing")

        sfx_sig, sfx_sr = _read_pcm16_mono(asset_p)
        if sfx_sr != base_sr:
            new_len = max(1, int(round(len(sfx_sig) * base_sr / sfx_sr)))
            sfx_sig = np.interp(
                np.linspace(0, len(sfx_sig) - 1, new_len, dtype=np.float32),
                np.arange(len(sfx_sig), dtype=np.float32),
                sfx_sig,
            ).astype(np.float32)

        gain = float(10.0 ** (float(cue.get("gain_db", -9.0)) / 20.0))
        start_idx = int(round(float(cue["visual_timestamp_s"]) * base_sr))
        if start_idx < 0 or start_idx >= n_frames:
            raise ContractError(
                f"Spotted cue {cue.get('cue_id')} timestamp {cue['visual_timestamp_s']}s out of base audio bounds"
            )
        end_idx = min(n_frames, start_idx + len(sfx_sig))
        seg_len = end_idx - start_idx
        mixed[start_idx:end_idx, :] += (sfx_sig[:seg_len] * gain)[:, None]
        placed.append(
            {
                "cue_id": cue.get("cue_id"),
                "asset_id": cue.get("asset_id"),
                "asset_sha256": expected_sha,
                "visual_timestamp_s": cue["visual_timestamp_s"],
                "actual_mix_start_s": round(start_idx / base_sr, 4),
                "mixed_duration_s": round(seg_len / base_sr, 4),
            }
        )

    peak = float(np.max(np.abs(mixed))) if n_frames else 0.0
    if peak > 0.98:
        mixed = mixed * (0.98 / peak)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(mixed.reshape(-1) * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(base_ch)
        wf.setsampwidth(2)
        wf.setframerate(base_sr)
        wf.writeframes(pcm.tobytes())

    return {
        "output_wav": str(out_wav),
        "output_sha256": sha256_file(out_wav),
        "sample_rate": base_sr,
        "channels": base_ch,
        "duration_s": round(n_frames / base_sr, 4),
        "cues_mixed": len(placed),
        "placed_cues": placed,
    }


def measure_audio_cut_ab(
    wav_a: Path,
    wav_b: Path,
    out_dir: Path,
    *,
    fade_ms: float = 30.0,
) -> dict[str, Any]:
    """Experimental A/B measurement comparing hard-cut join vs ``fade_ms`` crossfade boundary jump."""
    if not wav_a.is_file() or not wav_b.is_file():
        raise ContractError("Both wav_a and wav_b must exist for audio cut A/B comparison")
    with wave.open(str(wav_a), "rb") as wa:
        sr_a, ch_a = wa.getframerate(), wa.getnchannels()
        sig_a = np.frombuffer(wa.readframes(wa.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    with wave.open(str(wav_b), "rb") as wb:
        sr_b, ch_b = wb.getframerate(), wb.getnchannels()
        sig_b = np.frombuffer(wb.readframes(wb.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if sr_a != sr_b or ch_a != ch_b:
        raise ContractError(f"Audio format mismatch: ({sr_a}, {ch_a}) vs ({sr_b}, {ch_b})")

    if ch_a > 1:
        sig_a = sig_a.reshape(-1, ch_a).mean(axis=1)
        sig_b = sig_b.reshape(-1, ch_b).mean(axis=1)

    hard_cut = np.concatenate([sig_a, sig_b])
    boundary_idx = len(sig_a)
    hard_jump = float(abs(hard_cut[boundary_idx] - hard_cut[boundary_idx - 1])) if 0 < boundary_idx < len(hard_cut) else 0.0

    fade_n = max(1, min(int(sr_a * fade_ms / 1000.0), len(sig_a) // 2, len(sig_b) // 2))
    ramp_out = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
    ramp_in = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
    faded = np.concatenate([sig_a[:-fade_n], sig_a[-fade_n:] * ramp_out + sig_b[:fade_n] * ramp_in, sig_b[fade_n:]])
    faded_window = faded[max(0, boundary_idx - fade_n - 1) : min(len(faded), boundary_idx + 2)]
    faded_jump = float(np.max(np.abs(np.diff(faded_window)))) if len(faded_window) > 1 else 0.0

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, arr in (("ab_hard_cut.wav", hard_cut), ("ab_fade_30ms.wav", faded)):
        pcm = np.clip(arr * 32767.0, -32768, 32767).astype("<i2")
        with wave.open(str(out_dir / name), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr_a)
            wf.writeframes(pcm.tobytes())

    return {
        "experimental_note": "Single-pair boundary discontinuity measurement; not a claim of universal optimality.",
        "fade_ms": fade_ms,
        "hard_cut_boundary_jump": round(hard_jump, 5),
        "faded_boundary_max_step": round(faded_jump, 5),
        "pop_reduction_ratio": round((hard_jump - faded_jump) / hard_jump, 4) if hard_jump > 1e-6 else 0.0,
        "hard_cut_wav": str(out_dir / "ab_hard_cut.wav"),
        "faded_wav": str(out_dir / "ab_fade_30ms.wav"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.audio.post_assembly_spotting")
    ap.add_argument("preview_video", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--library", required=True, type=Path, help="Sound library folder containing manifest.json and WAVs")
    ap.add_argument("--work-dir", type=Path, default=None)
    ap.add_argument("--sound-plan", type=Path, default=None, help="Optional sound_plan.json to update")
    ap.add_argument("--base-audio", type=Path, default=None, help="Optional base WAV to mix spotted cues onto")
    ap.add_argument("--mixed-out", type=Path, default=None, help="Output path for mixed WAV")
    args = ap.parse_args(argv)
    work = args.work_dir or (args.out.parent / "spotting_work")
    events = detect_visual_event_timestamps(args.preview_video, work)
    cues = resolve_spotted_cues(args.preview_video, events, args.library)
    rec = build_spotting_record(args.preview_video, cues, out_path=args.out, require_verified_assets=True)
    if args.sound_plan:
        integrate_spotted_cues_into_sound_plan(args.sound_plan, rec)
    mix_res = None
    if args.base_audio and args.mixed_out:
        mix_res = mix_spotted_cues_onto_audio(args.base_audio, rec, args.mixed_out)
    print(
        json.dumps(
            {
                "status": rec["validation"]["status"],
                "cues": len(cues),
                "video_sha256": rec["assembled_video_sha256"],
                "mixed_out": mix_res["output_wav"] if mix_res else None,
            },
            indent=2,
        )
    )
    return 0 if rec["validation"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
