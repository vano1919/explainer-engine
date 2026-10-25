"""Register an already-generated sound into the reusable library (D-34, D-76): the ElevenLabs connector's music and
sound effects arrive as MP3/stereo files, this converts them to the library's 16-bit mono WAV (ffmpeg) and records id,
tags, source (model, prompt, cost), licence and review through ``sfx_library.add``, so future episodes find them by
tags instead of paying again (OR-18).

    python -m explainer_engine.audio.register <file.mp3|wav> --name heist_tension --category music --tags tense,heist
        [--take 1] [--loop | --one-shot] [--model eleven_music_v2_5] [--prompt "..."] [--cost-usd 0.5]
        [--licence-status generated_terms_verified] [--licence-note "..."] [--root assets/audio/library]

Defaults: music is a loop, foley/vocal a one-shot (BP-58). The licence default cites the verified ElevenLabs music
terms (V-28, ``standards/policy_baseline.json``); pass the real status for anything else.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from explainer_engine.audio import sfx_library

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
DEFAULT_LICENCE_NOTE = ("ElevenLabs Creator plan music/SFX terms as verified in standards/policy_baseline.json (V-28); "
                        "re-check before use outside YouTube")


def load_any(path: Path):
    """16-bit mono WAV is read directly; anything else (MP3, stereo, other widths) goes through ffmpeg."""
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            return sfx_library.read_wav(path)
        except Exception:
            pass  # stereo or another width: convert below
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "mono.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-ac", "1", "-acodec", "pcm_s16le", str(out)],
                       check=True)
        return sfx_library.read_wav(out)


def register(file: Path, *, root: Path = ROOT, name: str, take: int, category: str, tags: list[str],
             loop: bool | None = None, model: str = "", prompt: str = "", cost_usd: float = 0.0,
             licence_status: str = "generated_terms_verified", licence_note: str = DEFAULT_LICENCE_NOTE,
             machine_review: str = "none") -> dict:
    samples, rate = load_any(file)
    if loop is None:
        loop = category == "music"  # BP-58's default: music beds loop, foley and vocal reactions play once
    source = {"kind": "elevenlabs", "model": model, "prompt": prompt, "cost_usd_estimate": cost_usd}
    return sfx_library.add(root, name=name, take=take, category=category, tags=tags, samples=samples, rate=rate,
                           source=source, licence={"status": licence_status, "note": licence_note},
                           machine_review=machine_review, loop=loop)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--name", required=True)
    p.add_argument("--take", type=int, default=1)
    p.add_argument("--category", required=True, choices=["music", "foley", "vocal"])
    p.add_argument("--tags", required=True, help="comma-separated")
    kind = p.add_mutually_exclusive_group()
    kind.add_argument("--loop", action="store_true", default=None)
    kind.add_argument("--one-shot", dest="loop", action="store_false")
    p.add_argument("--model", default="")
    p.add_argument("--prompt", default="")
    p.add_argument("--cost-usd", type=float, default=0.0)
    p.add_argument("--licence-status", default="generated_terms_verified",
                   choices=["own_procedural", "generated_terms_unverified", "generated_terms_verified", "licensed", "cc0"])
    p.add_argument("--licence-note", default=DEFAULT_LICENCE_NOTE)
    p.add_argument("--machine-review", default="none")
    a = p.parse_args(argv)
    entry = register(Path(a.file), root=Path(a.root), name=a.name, take=a.take, category=a.category,
                     tags=[t for t in a.tags.split(",") if t], loop=a.loop, model=a.model, prompt=a.prompt,
                     cost_usd=a.cost_usd, licence_status=a.licence_status, licence_note=a.licence_note,
                     machine_review=a.machine_review)
    print(f"registered {entry['id']} ({entry['file']}, {entry['seconds']} s, "
          f"{'loop' if entry.get('loop', True) else 'one-shot'}); the creator has not listened yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
