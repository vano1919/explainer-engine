"""Shared guard of tools/render_tools (final plan P-8, W7): everything here is PREVIEW ONLY. The master comes from
``python -m explainer_engine.episode run <episode> --to qa`` (sound from G8 audio/stems, one render path). Every entry point calls
``guard(name, argv)`` first: it prints the banner and refuses a ``--final`` flag (and ``--master``, its spelling in older notes)."""
from __future__ import annotations

import sys

BANNER = "PREVIEW ONLY: {name} makes a preview, never a master. Masters come from `python -m explainer_engine.episode run <episode> --to qa`."
REFUSED_FLAGS = ("--final", "--master")


def guard(name: str, argv: list[str] | None = None, out=None) -> None:
    """Print the preview-only banner; exit 2 when a refused flag is among ``argv``."""
    out = out or sys.stdout
    argv = list(sys.argv[1:] if argv is None else argv)
    print(BANNER.format(name=name), file=out, flush=True)
    bad = [a for a in argv if a in REFUSED_FLAGS or a.startswith(tuple(f + "=" for f in REFUSED_FLAGS))]
    if bad:
        print(f"refused: {bad[0]} - {name} has no final mode (P-8: one render path, episode/run.py)", file=sys.stderr, flush=True)
        raise SystemExit(2)
