"""P1's Qwen part (EXEC_QUEUE.md P1): the p15 restyle runner on p16's own jobs (the three battle stills the p15 pod did not draw).
Everything else (loader, LoRA merge, draw call, first frames, sidecars, manifest.jsonl per picture: OR-33) is ``p15_qwen``'s."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.training.pods.p15 import p15_qwen as Q15

HERE = Path(__file__).resolve().parent


def load_cfg() -> dict:
    return json.loads((HERE / "p16.json").read_text(encoding="utf-8"))


Q15.load_cfg = load_cfg      # p15_qwen.run / jobs read their config through this name

if __name__ == "__main__":
    sys.exit(Q15.main())
