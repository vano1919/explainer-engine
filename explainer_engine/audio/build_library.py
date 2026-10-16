"""Build the procedural part of the sound library (free, deterministic): ``python -m explainer_engine.audio.build_library <root>``."""

from __future__ import annotations

import sys
from pathlib import Path

from explainer_engine.audio import foley, sfx_library

SOURCE_NOTE = "built from noise and tones in explainer_engine/audio/foley.py; no third-party material"


def build(root: Path) -> int:
    n = 0
    for name, (tags, fn, seeds) in foley.BUILD.items():
        for take, seed in enumerate(seeds, start=1):
            sfx_library.add(root, name=name, take=take, category="foley", tags=tags, samples=fn(seed), rate=foley.SR,
                            source={"kind": "procedural", "seed": seed},
                            licence={"status": "own_procedural", "note": SOURCE_NOTE},
                            machine_review="procedural placeholder: plain, replaceable by recorded foley")
            n += 1
    return n


if __name__ == "__main__":
    print(build(Path(sys.argv[1])), "sounds written")
