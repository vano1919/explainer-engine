"""OR-V56: every LTX clip is trimmed from the clip's end to its shot length, and the trim is at most 0.33 s (rounded up).

The edit plan is a JSON ``{"shots": [{"id": "S1", "clip_length_s": 5.2, "shot_length_s": 5.0, "trim_s": 0.2}, ...]}``. The 0.33 s is the owner's number, but
only from his card answer (Q4 = A, 2026-11-06, as recorded in the lead's gap table); it is NOT in ``standards/sourced_rules.json``. It lives in
``trim_record_tolerances.json`` marked ``house`` with that source, until the owner's typed word puts it into the registry.

Codes (each has a test): TR-01 a shot lacks a field (NOT_RUN: not an edit plan we can judge); TR-02 the clip is shorter than its shot (trim below 0: FAIL);
TR-03 the trim is over the limit (FAIL); TR-04 the recorded ``trim_s`` differs from ``clip_length_s - shot_length_s`` (compared to 2 decimals, the
precision of the limit: FAIL). ``value`` is the largest trim in seconds.
"""
from __future__ import annotations

import json
from pathlib import Path

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"
TOLERANCES = Path(__file__).with_name("trim_record_tolerances.json")
FIELDS = ("clip_length_s", "shot_length_s", "trim_s")


def trim_max_s() -> float:
    return float(json.loads(TOLERANCES.read_text(encoding="utf-8"))["trim_max_s"]["value"])


def trim_record(path) -> dict:
    """OR-V56 adapter: reads an edit plan file. A ``.json`` that is not an edit plan with a ``shots`` list is NOT_RUN."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    shots = doc.get("shots") if isinstance(doc, dict) else None
    if not isinstance(shots, list) or not shots:
        return {"status": NOT_RUN, "value": None, "detail": "not an edit plan (no shots list): nothing to measure"}
    limit = trim_max_s()
    bad, worst = [], 0.0
    for i, s in enumerate(shots):
        sid = s.get("id", i + 1) if isinstance(s, dict) else i + 1
        if not isinstance(s, dict) or any(not isinstance(s.get(k), (int, float)) or isinstance(s.get(k), bool) for k in FIELDS):
            return {"status": NOT_RUN, "value": None, "detail": f"TR-01 shot {sid} lacks one of {', '.join(FIELDS)}: not judged"}
        diff = round(s["clip_length_s"] - s["shot_length_s"], 2)
        worst = max(worst, diff)
        if diff < 0:
            bad.append(f"TR-02 shot {sid}: clip is {-diff} s shorter than the shot")
        elif diff > limit:
            bad.append(f"TR-03 shot {sid}: trim {diff} s is over {limit} s")
        if round(s["trim_s"], 2) != diff:
            bad.append(f"TR-04 shot {sid}: recorded trim_s {s['trim_s']} but clip minus shot is {diff}")
    tag = f"(OR-V56, {limit} s is the owner's card answer, not in the registry)"
    if bad:
        return {"status": FAIL, "value": round(worst, 2), "detail": "; ".join(bad[:3]) + (f" (+{len(bad) - 3} more)" if len(bad) > 3 else "") + f" {tag}"}
    return {"status": PASS, "value": round(worst, 2), "detail": f"{len(shots)} shot(s), largest trim {round(worst, 2)} s {tag}"}


trim_record.kinds = (".json",)
