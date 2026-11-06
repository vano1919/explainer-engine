"""P1's LTX part (EXEC_QUEUE.md P1): the p15 one-clip-per-process runner on p16's jobs (8 clips, 97-145 frames, seed 42)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.training.pods.p15 import p15_ltx as X15

HERE = Path(__file__).resolve().parent


def load_cfg() -> dict:
    return json.loads((HERE / "p16.json").read_text(encoding="utf-8"))


X15.load_cfg = load_cfg      # p15_ltx.main reads its config through this name

if __name__ == "__main__":
    sys.exit(X15.main())
