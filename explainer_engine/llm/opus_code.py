"""Tier 3 of the code-writing tiers (docs: .claude/skills/deepseek-worker, section 4): the hard task goes to Claude Opus through
the Claude API (explainer_engine/llm/claude_api.py: key, ledger, caps, cache, stream proof), never through an app thread.

The loop is the DeepSeek worker's (``deepseek_api.code``: brief + files -> edit blocks -> applied, tested, a red round leaves no
trace, ``patch.diff``); only the model call is different. Money: the ``opus_code`` line of ``claude_api.jobs`` in
``config/spend_caps.json`` (reserved before every call by claude_api), plus the job's own ``--max-usd``. The model and effort
come from the task class in ``config/model_routing.json`` (default class ``opus-code``); a class that is not there is refused,
never guessed. A real call needs ``--card-ref``: the id of the creator's card message that allowed this paid call.

    python -m explainer_engine.llm.opus_code code --brief brief.md --files a.py b.py --test "python -m pytest -q t.py" \\
        --max-usd 3 --dry-run                                     # worst-case estimate, spends nothing
    python -m explainer_engine.llm.opus_code code ... --card-ref cmsg_...      # the paid call
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import EngineError
from explainer_engine.llm import claude_api as CA
from explainer_engine.llm import deepseek_api as DS

ROOT = DS.ROOT
DEFAULT_CLASS = "opus-code"
JOB = "opus_code"            # the line of claude_api.jobs in config/spend_caps.json


class OpusCodeError(EngineError):
    """A refusal of this module (no card, over the job's limit)."""


class ClaudeWorker:
    """Quacks like ``deepseek_api.Worker`` for ``deepseek_api.code``: ``cfg``, ``job``, ``job_usd`` and ``complete``."""

    def __init__(self, *, job: str = JOB, max_usd: float = 1.0, task_class: str = DEFAULT_CLASS, api: Any = None,
                 cfg: dict | None = None, routing_cfg: dict | None = None, max_tokens: int = 24000) -> None:
        self.cfg = cfg or DS.config()          # never_paths and limits are the DeepSeek worker's, one set for every writer
        self.job, self.max_usd, self.job_usd = job, float(max_usd), 0.0
        self.task_class, self.max_tokens = task_class, max_tokens
        self.api, self.routing_cfg = api, routing_cfg
        self.calls = 0

    def _request(self, messages: list[dict]) -> CA.Request:
        self.calls += 1
        turns = []
        for m in messages[1:]:
            tag = "TASK" if m["role"] == "user" else "YOUR PREVIOUS ANSWER"
            turns.append(f"=== {tag} ===\n{m['content']}")
        return CA.Request(id=f"{self.job}-{self.calls}", user="\n\n".join(turns), task_class=self.task_class, job=self.job,
                          system=[messages[0]["content"]], max_tokens=self.max_tokens)

    def estimate(self, messages: list[dict]) -> float:
        req = self._request(messages)
        self.calls -= 1
        r = CA.route(req.task_class, req.model, req.effort, cfg=self.routing_cfg)
        return CA.worst_usd(r.model, CA.build_params(req, r))

    def complete(self, messages: list[dict], *, model: str = "opus", think: bool = True, max_tokens: int | None = None,
                 sink: Path | None = None, json_mode: bool = False) -> str:
        worst = self.estimate(messages)
        if self.job_usd + worst > self.max_usd + 1e-9:
            raise OpusCodeError(f"job {self.job}: ${self.job_usd:.3f} spent + ${worst:.3f} worst case would pass its "
                                f"--max-usd ${self.max_usd:g}")
        api = self.api or CA.ClaudeAPI()
        res = api.complete(self._request(messages))
        self.job_usd += float(res.usd)
        if sink is not None:
            sink.parent.mkdir(parents=True, exist_ok=True)
            DS.write_text_atomic(sink, res.text)
        return res.text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.llm.opus_code", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("code")
    p.add_argument("--brief", required=True, type=Path)
    p.add_argument("--files", nargs="*", default=[])
    p.add_argument("--test", default=None)
    p.add_argument("--rounds", type=int, default=None)
    p.add_argument("--max-usd", required=True, type=float, help="the job's own hard limit")
    p.add_argument("--task-class", default=DEFAULT_CLASS)
    p.add_argument("--job", default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true", help="print the worst-case estimate of one round, send nothing")
    p.add_argument("--card-ref", default=None, help="id of the creator's card message that allowed this paid call")
    a = ap.parse_args(argv)
    try:
        brief = a.brief.read_text(encoding="utf-8")
        job = a.job or a.brief.stem
        out = a.out or ROOT / "jobs" / "opus_code" / job
        w = ClaudeWorker(max_usd=a.max_usd, task_class=a.task_class)
        first = [{"role": "system", "content": DS.CODE_SYSTEM},
                 {"role": "user", "content": DS.pack(a.files, ROOT, w.cfg) + "\n=== BRIEF ===\n" + brief}]
        if a.dry_run:
            r = CA.route(a.task_class)
            print(json.dumps({"job": job, "model": r.model, "effort": r.effort, "worst_usd_per_round": round(w.estimate(first), 4),
                              "key_present": CA.api_key() is not None}))
            return 0
        if not (a.card_ref or "").startswith("cmsg_"):
            raise OpusCodeError("a paid Opus call needs --card-ref <the creator's card message id>: nothing was sent")
        if CA.api_key() is None:
            raise CA.KeyAbsent("no Claude API key in " + " or ".join(CA.KEY_ENV_NAMES) + ": nothing was sent")
        res = DS.code(w, brief, a.files, test=a.test, model="opus", rounds=a.rounds, out=out)
        res["card_ref"] = a.card_ref
        DS.write_json_atomic(out / "summary.json", res)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("status") == "PASS" else 1
    except EngineError as e:
        print(json.dumps({"status": "REFUSED", "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
