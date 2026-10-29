"""P0c cost / wall-time backing numbers from the subagent transcripts (JSONL under the session's tasks folder).

    python docs/research/agent_ab_2026-10/cost.py <tasks_dir> <label>=<id>[,<id>...] ...   > cost.json

Units: input-price units = input + 1.25 x cache_write + 0.1 x cache_read + 5 x output (Anthropic list ratios for one model).
Active time = sum of gaps between consecutive transcript entries shorter than 10 minutes (a usage-limit stall is excluded).
"""
import collections, datetime as dt, json, sys
from pathlib import Path


def one(f: Path) -> dict:
    t, n, ts = collections.Counter(), 0, []
    for line in f.read_text().splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("timestamp"):
            ts.append(dt.datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00")))
        m = o.get("message") or {}
        u = m.get("usage") if isinstance(m, dict) else None
        if u and m.get("role") == "assistant":
            n += 1
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                t[k] += u.get(k, 0) or 0
    active = sum((b - a).total_seconds() for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() < 600)
    units = t["input_tokens"] + 1.25 * t["cache_creation_input_tokens"] + 0.1 * t["cache_read_input_tokens"] + 5 * t["output_tokens"]
    return {"turns": n, **t, "units": round(units), "active_s": round(active)}


def main(tasks: str, specs: list[str]) -> dict:
    out = {}
    for spec in specs:
        label, ids = spec.split("=")
        rows = {i: one(Path(tasks) / f"{i}.output") for i in ids.split(",")}
        tot = collections.Counter()
        for r in rows.values():
            tot.update(r)
        out[label] = {"agents": rows, "total": dict(tot)}
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2:]), indent=1))
