"""The paid Gemini API as the backup of the Gemini chat (the creator, 2026-11-12 20:26 UTC): when the chat's Task limit is
used up, the same picture blocks go to the API batch tier with the same references, word for word.

Only the PICTURE blocks of a message written by this package (T0, P6, P7, P8, P10) are read: each block's ``PROMPT:`` line
is the exact text, ``REFERENCES`` names the files. Nothing is rewritten, so the API run is a direct check of the prompts
against the chat run. Money: ``imagegen/gemini.GeminiClient.submit_batch`` reserves the batch price, refuses past 80 % of
the cap and records the batch on disk before the POST; ``collect`` writes every picture as it is read (OR-33).

CLI::

    python -m explainer_engine.gemini_task.api_backup estimate <message.md> [--model M] [--size 2K]
    EXPLAINER_GEMINI_API=on python -m explainer_engine.gemini_task.api_backup submit <message.md> --out DIR --cap USD
    EXPLAINER_GEMINI_API=on python -m explainer_engine.gemini_task.api_backup collect --out DIR [--wait S]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from explainer_engine.imagegen import gemini as G

REPO = Path(__file__).resolve().parents[2]
DEFAULT_MODEL, DEFAULT_SIZE = "gemini-nano-banana-2.1", "2K"
_HEAD = re.compile(r"^PICTURE (\d+) of (\d+) \| id (\S+)")
_REF = re.compile(r"\d+ = (\S+)")


def picture_blocks(message: str) -> list[dict]:
    """[{id, prompt, refs: [file names in order]}] from the PICTURES section, in order. Refuses a block without a prompt."""
    body = message.split("-----BEGIN PICTURES-----", 1)[-1].split("-----END PICTURES-----", 1)[0]
    out, cur = [], None
    for line in body.splitlines():
        m = _HEAD.match(line.strip())
        if m:
            cur = {"id": m.group(3), "prompt": None, "refs": []}
            out.append(cur)
        elif cur is not None and line.startswith("REFERENCES"):
            cur["refs"] = _REF.findall(line.split(":", 1)[1])
        elif cur is not None and line.startswith("PROMPT: "):
            cur["prompt"] = line[len("PROMPT: "):].strip()
    if not out:
        raise G.GeminiError("no PICTURE blocks in the message")
    for b in out:
        if not b["prompt"]:
            raise G.GeminiError(f"{b['id']}: no PROMPT line")
    return out


def find_ref(name: str, roots: list[Path]) -> Path:
    for root in roots:
        hits = sorted(Path(root).rglob(name))
        if hits:
            return hits[0]
    raise G.GeminiError(f"reference {name} not found under {[str(r) for r in roots]}")


def items(message_file: Path, ref_roots: list[Path] | None = None) -> list[dict]:
    roots = ref_roots or [REPO / "assets" / "style", Path(message_file).resolve().parents[1]]
    return [{"name": b["id"], "prompt": b["prompt"], "refs": [find_ref(r, roots).read_bytes() for r in b["refs"]],
             "ref_names": b["refs"]} for b in picture_blocks(Path(message_file).read_text(encoding="utf-8"))]


def estimate(its: list[dict], model: str = DEFAULT_MODEL, size: str = DEFAULT_SIZE) -> float:
    return round(sum(G.BATCH_PRICES[model][size] + len(i["refs"]) * G.REFERENCE_USD for i in its), 4)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.gemini_task.api_backup")
    ap.add_argument("cmd", choices=["estimate", "submit", "collect"])
    ap.add_argument("message", nargs="?")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--cap", type=float, default=0.0)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--size", default=DEFAULT_SIZE)
    ap.add_argument("--wait", type=float, default=0.0)
    a = ap.parse_args(argv)
    if a.cmd in ("estimate", "submit"):
        its = items(Path(a.message))
        cost = estimate(its, a.model, a.size)
        print(json.dumps({"pictures": len(its), "model": a.model, "size": a.size, "batch_usd": cost,
                          "ids": [i["name"] for i in its]}, indent=1))
        if a.cmd == "estimate":
            return 0
        client = G.GeminiClient(a.out, cap_usd=a.cap)
        name = client.submit_batch([{k: i[k] for k in ("name", "prompt", "refs")} for i in its], model=a.model,
                                   size=a.size)
        (a.out / "prompts_sent.json").write_text(json.dumps(
            [{"id": i["name"], "prompt": i["prompt"], "refs": i["ref_names"]} for i in its], indent=1), encoding="utf-8")
        print(json.dumps({"batch": name}))
        return 0
    client = G.GeminiClient(a.out, cap_usd=a.cap)
    res = {}
    for f in sorted((a.out / "batches").glob("batches_*.json")):
        meta = json.loads(f.read_text())
        if not meta.get("settled"):
            got = client.collect_batch(meta["name"], wait_s=a.wait)
            res[meta["name"]] = {"state": got["state"], "done": got["done"],
                                 "items": {k: str(v) for k, v in got["items"].items()}}
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
