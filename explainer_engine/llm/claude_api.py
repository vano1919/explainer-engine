"""The Claude API client of the project (P0d, docs/LLM_API.md): the one place that calls Anthropic.

Model and effort come from ``config/model_routing.json`` by task class (never a model string in a job file); the key is read
by the SDK from ``ANTHROPIC_API_KEY`` and never printed; every paid call is reserved in the job ledger before it is made
and written to ``jobs/llm_ledger/calls.jsonl`` after; the caps live only in ``config/spend_caps.json`` (``claude_api``,
invariant 2); an identical request is answered from ``jobs/llm_cache`` and paid once. The SDK is imported lazily, so the
tests run with a fake client and no network.

    python -m explainer_engine.llm.claude_api estimate job.json     # tokens and dollars, spends nothing
    python -m explainer_engine.llm.claude_api run job.json --out DIR
    python -m explainer_engine.llm.claude_api status | void UID [--usd X]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from explainer_engine.core import spend_caps
from explainer_engine.core.errors import ConfigError, EngineError
from explainer_engine.core.ledger import STOP_FRACTION, CapReached, Run
from explainer_engine.core.store import write_json_atomic, write_text_atomic

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "claude_api_usd"
BASE_URL = "https://api.anthropic.com"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
BATCH_MIN = 20            # a job with at least this many requests goes through the Batch API
CHARS_PER_TOKEN = 3.0     # offline upper bound for the reservation, never for the bill
OVERLOAD_WAIT_S = 900     # 429 / overloaded for longer than this stops the job (plan stop rule)
UNCHARGED = (400, 401, 403, 404, 413, 422, 429, 500, 502, 503, 529)  # statuses where no tokens were billed
RETRYABLE = (429, 500, 502, 503, 529)
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# F6: parameters that return a 400 (or are refused by the 2026-10-21 API version) on the current models; never sent.
# F15: measured 2026-10-30: Fable 5.1 at effort max used more than 40000 tokens on thinking alone (the $3.45 change-plan run, no answer
# text); 64000 is the skill's streaming default. Thinking is billed as output and counts toward max_tokens, so these efforts need room.
MIN_MAX_TOKENS_BY_EFFORT = {"max": 64000, "xhigh": 32000}
FORBIDDEN_PARAMS = ("temperature", "top_p", "top_k", "budget_tokens", "tool_choice", "prefill")

# F7: the patterns tests/unit/test_repo_hygiene.py guards (file names) plus key shapes in text.
SECRET_NAMES = re.compile(r"(api_key|token[^/]*\.json$|secret|credentials|id_ed25519|\.pem$|^\.env$)", re.I)
SECRET_NAMES_MORE = re.compile(r"(^\.env(\..*)?$|^id_rsa|^id_dsa|^\.netrc$|\.key$|\.p12$|\.pfx$|^\.npmrc$|^\.pypirc$)", re.I)
SECRET_TEXT = re.compile(
    r"(sk-ant-[A-Za-z0-9_-]{10,}|ANTHROPIC_API_KEY\s*=\s*\S|hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|rpa_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|aws_secret_access_key\s*[=:]"
    r"|sk-proj-[A-Za-z0-9_-]{20,}|sk_[a-f0-9]{40,}|xox[abprs]-[A-Za-z0-9-]{10,}|Bearer\s+[A-Za-z0-9._~+/=-]{20,}"
    r"|(?:API_KEY|_KEY|SECRET|TOKEN|PASSWORD|_B64)\s*[=:]\s*[\"']?[A-Za-z0-9+/_=.-]{20,})", re.I)
SKIP_DIRS = {".git", "tools", "node_modules", "__pycache__"}


def secret_name(name: str) -> bool:
    return bool(SECRET_NAMES.search(name) or SECRET_NAMES_MORE.search(name))


KEY_ENV_NAMES = ("ANTHROPIC_API_KEY", "EE_ANTHROPIC_API_KEY")  # the second: environment settings refuse the first name


def api_key() -> str | None:
    """The key from the environment (first non-empty of KEY_ENV_NAMES); only the SDK client ever sees it, nothing prints it."""
    for n in KEY_ENV_NAMES:
        if os.environ.get(n):
            return os.environ[n]
    return None


class LLMError(EngineError):
    """Base of the client's own refusals."""


class KeyAbsent(LLMError):
    """``ANTHROPIC_API_KEY`` is not in the environment (the plan's stop rule: report, do not look for it elsewhere)."""


class NotApproved(LLMError):
    """``config/spend_caps.json`` claude_api.approval is empty: no real call before the creator's word is recorded."""


class RoutingError(LLMError):
    """The task class, model or effort is not allowed by ``config/model_routing.json``."""


class PriceMissing(LLMError):
    """A model has no price line in ``config/llm_prices.json``."""


class SecretInPrompt(LLMError):
    """A prompt, file or tool result matches the secret patterns (F7)."""


class LedgerGap(LLMError):
    """A call has a start line and no result line: fix the ledger before any further call (OR-24 stop rule)."""


class Overloaded(LLMError):
    """429 / overloaded for longer than OVERLOAD_WAIT_S."""


class CacheCold(LLMError):
    """A tool loop's history is not being read from cache: it is billed as fresh input every turn (the J1b scope A state, $5.02)."""


class OutputTruncated(LLMError):
    """The answer hit max_tokens; it was paid and recorded but is not cached. ``text`` is what was paid for (F3: ``main`` writes it
    to ``<id>.truncated.md``), ``result`` the same as a Result when there is one, ``thinking`` the summarized thinking (F13: ``main``
    writes it to ``<id>.thinking.md``); thinking is billed as output and counts toward max_tokens, so it can use all of it."""

    def __init__(self, message: str, text: str | None = None, result: "Result | None" = None, thinking: str | None = None) -> None:
        super().__init__(message)
        self.text, self.result, self.thinking = text, result, thinking


class StreamBroken(LLMError):
    """The connection broke after text had arrived (F2): not retried, booked at the reservation; ``path`` holds the text so far."""

    def __init__(self, message: str, path: Path | None = None, text: str = "") -> None:
        super().__init__(message)
        self.path, self.text = path, text


class Refused(LLMError):
    """A safety refusal (stop_reason ``refusal``). Reported, never retried with a reworded prompt."""

    def __init__(self, category: str | None, explanation: str | None, result: "Result | None" = None) -> None:
        self.category, self.explanation, self.result = category, explanation, result
        super().__init__(f"refusal ({category or 'no category'}): {explanation or ''}".strip())


# --- files -------------------------------------------------------------------------------------------------------------
def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name) or default)


def prices() -> dict:
    return json.loads(_env_path("EXPLAINER_LLM_PRICES", ROOT / "config" / "llm_prices.json").read_text(encoding="utf-8"))


def routing() -> dict:
    p = _env_path("EXPLAINER_MODEL_ROUTING", ROOT / "config" / "model_routing.json")
    if not p.exists():
        raise RoutingError(f"{p} is missing (config/model_routing.json comes with P0b, PR #30): no model can be chosen")
    return json.loads(p.read_text(encoding="utf-8"))


def cache_dir() -> Path:
    return _env_path("EXPLAINER_LLM_CACHE", ROOT / "jobs" / "llm_cache")


def ledger_dir() -> Path:
    return _env_path("EXPLAINER_LLM_LEDGER", ROOT / "jobs" / "llm_ledger")


def caps() -> dict:
    c = spend_caps.load().get("claude_api")
    if not isinstance(c, dict) or "max_usd" not in c or not isinstance(c.get("jobs"), dict):
        raise ConfigError("config/spend_caps.json has no claude_api {max_usd, jobs} line: spending needs the creator's yes")
    return c


def lines_below_spent(c: dict, spent_by_job: dict[str, float]) -> dict[str, float]:
    """Job lines that are lower than what the job has already spent (money moved out of a line must be unspent money); {job: spent - line}."""
    return {j: round(v - float(c["jobs"].get(j, 0.0)), 6) for j, v in spent_by_job.items() if v > float(c["jobs"].get(j, 0.0)) + 1e-9}


# --- routing -----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Route:
    class_id: str
    alias: str
    model: str
    effort: str


def route(task_class: str, model: str | None = None, effort: str | None = None, *, cfg: dict | None = None) -> Route:
    """Model and effort of a task class. ``model`` (alias or id) and ``effort`` may narrow the class, never leave it (F5: the
    effort is always sent, the API default differs per model)."""
    cfg = cfg or routing()
    row = next((c for c in cfg["classes"] if c["id"] == task_class), None)
    if row is None:
        raise RoutingError(f"unknown task class {task_class!r}")
    if not row["models"]:
        raise RoutingError(f"task class {task_class!r} is not an API call (no model in config/model_routing.json)")
    ids = cfg["models"]
    alias = model
    if model and model in ids.values():
        alias = next(a for a, i in ids.items() if i == model)
    alias = alias or row["models"][0]
    if alias not in row["models"]:
        raise RoutingError(f"{task_class}: model {alias!r} is not allowed (allowed: {row['models']})")
    eff = effort or row["efforts"][0]
    if eff not in row["efforts"]:
        raise RoutingError(f"{task_class}: effort {eff!r} is not allowed (allowed: {row['efforts']})")
    story = cfg.get("fable_story_stages") or {}
    if alias == "fable" and task_class == "script-story-stages" and not story.get("enabled"):
        raise RoutingError("Fable on the story stages is switched off in config/model_routing.json (fable_story_stages.enabled)")
    return Route(task_class, alias, ids[alias], eff)


# --- money -------------------------------------------------------------------------------------------------------------
def usd_of(model: str, u: dict, *, batch: bool = False, pr: dict | None = None) -> float:
    """Dollars of one response. ``u`` keys: input, output, cache_read, write_5m, write_1h, searches."""
    pr = pr or prices()
    p = pr["models"].get(model)
    if p is None:
        raise PriceMissing(f"{model} has no line in config/llm_prices.json")
    rin, rout = p["in"], p["out"]
    long = p.get("long_prompt")
    if long and u["input"] + u["cache_read"] + u["write_5m"] + u["write_1h"] > long["over_tokens"]:
        rin, rout = long["in"], long["out"]
    total = (u["input"] * rin + u["output"] * rout + u["cache_read"] * p["cache_read"]
             + u["write_5m"] * rin * pr["cache_write_5m_factor"] + u["write_1h"] * rin * pr["cache_write_1h_factor"]) / 1e6
    if batch:
        total *= pr["batch_factor"]
    return total + u["searches"] * pr["web_search_usd_per_1000"] / 1000.0   # F2: search is not discounted nor token-priced


def usage_of(resp: Any, ttl: str = "5m") -> dict:
    u = getattr(resp, "usage", None)

    def n(name: str, obj: Any = u) -> int:
        return int(getattr(obj, name, 0) or 0)

    write = n("cache_creation_input_tokens")
    cc = getattr(u, "cache_creation", None)
    w5, w1 = (n("ephemeral_5m_input_tokens", cc), n("ephemeral_1h_input_tokens", cc)) if cc is not None else (0, 0)
    if w5 + w1 == 0 and write:
        w5, w1 = (write, 0) if ttl == "5m" else (0, write)
    tool = getattr(u, "server_tool_use", None)
    return {"input": n("input_tokens"), "output": n("output_tokens"), "cache_read": n("cache_read_input_tokens"),
            "write_5m": w5, "write_1h": w1, "searches": n("web_search_requests", tool) if tool is not None else 0}


def iterations_usd(resp: Any, ttl: str, pr: dict, *, batch: bool = False) -> tuple[float, list[dict]]:
    """Dollars of the attempts listed in ``usage.iterations`` (a refused attempt and the fallback that answered), each at its own
    model. Entries without a model or tokens are skipped; (0.0, []) when the response lists none."""
    total, rows = 0.0, []
    for it in getattr(getattr(resp, "usage", None), "iterations", None) or []:
        model = getattr(it, "model", None)
        if not model or not isinstance(getattr(it, "input_tokens", None), int):
            continue
        u = usage_of(NS_(usage=it), ttl)
        usd = usd_of(model, u, batch=batch, pr=pr)
        total += usd
        rows.append({"model": model, "usd": round(usd, 6)})
    return total, rows


class NS_:   # a tiny namespace so usage_of can read an iteration entry like a response
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


def _chars(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=lambda o: getattr(o, "__dict__", str(o))))


def worst_usd(model: str, params: dict, ttl: str = "5m", *, batch: bool = False, input_tokens: int | None = None) -> float:
    """Upper bound reserved BEFORE the call: the whole prompt as cache writes, max_tokens of output, and every allowed search."""
    toks = input_tokens if input_tokens is not None else math.ceil(_chars({k: params.get(k) for k in ("system", "messages", "tools")}) / CHARS_PER_TOKEN)
    searches = sum(int(t.get("max_uses", 0) or 0) for t in params.get("tools") or [] if str(t.get("type", "")).startswith("web_search"))
    key = "write_5m" if ttl == "5m" else "write_1h"
    return usd_of(model, {"input": 0, "output": params["max_tokens"], "cache_read": 0, "write_5m": 0, "write_1h": 0, "searches": searches,
                          key: toks}, batch=batch)


class Ledger:
    """``calls.jsonl``: a ``start`` line before every paid call and a ``done`` (or ``void``) line after it. A start without a
    result is a LedgerGap (a call the meter did not see); the total is the only meter we have (F8)."""

    def __init__(self, path: Path | None = None) -> None:
        self.dir = Path(path) if path else ledger_dir()
        self.file = self.dir / "calls.jsonl"
        self._lock = threading.Lock()

    def rows(self) -> list[dict]:
        if not self.file.exists():
            return []
        return [json.loads(line) for line in self.file.read_text(encoding="utf-8").splitlines() if line.strip()]

    def append(self, row: dict) -> None:
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            with self.file.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **row}, ensure_ascii=False) + "\n")

    def total(self) -> float:
        return round(sum(r.get("usd", 0.0) for r in self.rows() if r["ev"] == "done"), 6)

    def by_job(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for r in self.rows():
            if r["ev"] == "done":
                out[r["job"]] = round(out.get(r["job"], 0.0) + r["usd"], 6)
        return out

    def open_calls(self) -> list[dict]:
        rows = self.rows()
        closed = {r["uid"] for r in rows if r["ev"] in ("done", "void")}
        return [r for r in rows if r["ev"] == "start" and r["uid"] not in closed and not r.get("batch")]

    def check_gap(self) -> None:
        gap = self.open_calls()
        if gap:
            raise LedgerGap(f"{len(gap)} call(s) have no result line ({', '.join(r['uid'] for r in gap[:5])}): find what they cost "
                            "in the Console and close them with `claude_api void UID [--usd X]`")


# --- the request -------------------------------------------------------------------------------------------------------
@dataclass
class Request:
    id: str
    user: str
    task_class: str
    job: str = "adhoc"
    system: list[str] = field(default_factory=list)   # the stable prefix first (stage page, rules); the job text is `user`
    model: str | None = None
    effort: str | None = None
    max_tokens: int = 16000
    schema: dict | None = None                         # output_config.format (JSON) instead of prefill
    web_search_max_uses: int = 0
    cache_ttl: str = "5m"
    cache_salt: str = ""                               # e.g. the PR head sha of a tool-loop review
    tools_root: str | None = None                      # read-only repo tools over this folder (J1, J1b)
    max_turns: int = 24
    fallback_to: tuple[str, str] | None = None         # (alias, effort) when the model answers 400 (Fable retention)
    max_effort_reason: str = ""                        # F16: why a single-shot request needs effort max (plans and audits run at xhigh)


@dataclass
class Result:
    id: str
    text: str
    model: str
    effort: str
    usd: float
    cached: bool = False
    stop_reason: str | None = None
    usage: dict = field(default_factory=dict)
    fallback_ran: bool = False
    fell_back_to: str | None = None
    request_id: str | None = None
    ledger_total: float = 0.0
    turns: int = 1
    sources: list = field(default_factory=list)   # URLs of the web_search_tool_result blocks (J3: a cited URL must be one of them)

    def json(self) -> Any:
        return json.loads(self.text)


def check_secrets(text: str, where: str) -> None:
    m = SECRET_TEXT.search(text)
    if m:
        raise SecretInPrompt(f"{where}: matches a secret pattern ({m.group(0)[:6]}...); nothing was sent")


def redact(text: str) -> tuple[str, int]:
    """Replace key-shaped strings by a marker (a diff or a file the reviewer reads may hold fake keys in tests); returns (text, count)."""
    return SECRET_TEXT.subn("[REDACTED-SECRET-LIKE]", text)


def check_secret_path(path: str | Path, where: str = "file") -> None:
    p = Path(os.path.normpath(str(path)))
    if p.parts and p.parts[0] == ".." or SKIP_DIRS & set(p.parts) or secret_name(p.name) or any(secret_name(x) for x in p.parts):
        raise SecretInPrompt(f"{where}: {path} is a secret-like, tools/ or .git path; nothing was sent")


def _with_breakpoint(msgs: list, ttl: str = "5m") -> list:
    """A copy of the conversation with two breakpoints on its tail: the LAST content block (this turn's write) and the last block of
    the turn before (where the previous call wrote its cache, so this call's lookup always finds it: the API only looks back about
    20 blocks from a breakpoint, and a turn with more than ~10 parallel tool results adds more than that). With the system prefix and
    the first message that is four, the API's limit. A last block that is an SDK object (a turn that ended on an assistant message,
    ``pause_turn``) gets none and that turn falls back to an uncached history; the repo tools are client tools, so it does not occur."""
    cc = {"type": "ephemeral"} if ttl == "5m" else {"type": "ephemeral", "ttl": "1h"}
    out = list(msgs)

    def mark(i: int) -> None:
        m = out[i]
        if isinstance(m["content"], list) and m["content"] and isinstance(m["content"][-1], dict):
            blocks = list(m["content"])
            blocks[-1] = {**blocks[-1], "cache_control": cc}
            out[i] = {**m, "content": blocks}
    mark(len(out) - 1)
    if len(out) >= 3:
        mark(len(out) - 3)
    return out


def _block_json(b: Any) -> dict:
    if isinstance(b, dict):
        return {k: v for k, v in b.items() if k != "cache_control"}
    t = getattr(b, "type", None)
    if t == "text":
        return {"type": "text", "text": b.text}
    if t == "tool_use":
        return {"type": "tool_use", "name": b.name, "input": dict(b.input)}
    if t == "thinking":   # F13: the summarized thinking of a turn is paid for, so it is kept
        return {"type": "thinking", "thinking": getattr(b, "thinking", "") or ""}
    return {"type": str(t)}


def save_partial(req: Request, msgs: list, turns: int, usd: float, err: BaseException | str) -> Path | None:
    """What a stopped tool loop had so far: every assistant text and tool call, and the tool results cut to their first 400 characters
    (the checkout still has the files). Written atomically; returns None when even that fails (the original error goes on).
    ``err`` may be a plain string: the per-turn checkpoint (F4) of a loop that is still running."""
    try:
        turns_out = []
        for m in msgs[1:]:
            blocks = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
            row = [_block_json(b) for b in blocks]
            for b in row:
                if b.get("type") == "tool_result":
                    b["content"] = str(b.get("content", ""))[:400]
                elif b.get("type") == "thinking":   # redacted like a tool result: it is written to disk
                    b["thinking"] = redact(str(b.get("thinking", "")))[0]
            turns_out.append({"role": m["role"], "blocks": row})
        path = ledger_dir() / f"partial_{req.job}_{req.id}.json"
        write_json_atomic(path, {"job": req.job, "id": req.id, "turns": turns, "usd_so_far": round(usd, 6),
                                 "stopped_by": err if isinstance(err, str) else f"{type(err).__name__}: {err}",
                                 "messages": turns_out})
        return path
    except Exception:  # noqa: BLE001 - saving must never hide the error that stopped the loop
        return None


def max_effort_ok(req: Request, r: Route) -> bool:
    return r.effort != "max" or bool(req.tools_root) or bool(req.max_effort_reason.strip())


def check_max_tokens(req: Request, r: Route) -> None:
    """F15/F16: refuse, before anything is reserved or sent, a request whose max_tokens is under the floor of its effort, and a
    single-shot request at effort max that states no reason (``max_effort_reason`` in the job file; long single-shot outputs run at xhigh)."""
    if not max_effort_ok(req, r):
        raise ConfigError(f"request {req.id}: a single-shot request at effort max needs a non-empty \"max_effort_reason\" in the job file "
                          "(plans, specs and audits run at xhigh); nothing was sent")
    floor = MIN_MAX_TOKENS_BY_EFFORT.get(r.effort, 0)
    if req.max_tokens < floor:
        raise ConfigError(f"request {req.id}: effort {r.effort} needs max_tokens >= {floor} (thinking is billed as output and counts toward "
                          f"max_tokens; at max it used more than 40000 tokens with no answer, the $3.45 run), got {req.max_tokens}; nothing was sent")


def build_params(req: Request, r: Route) -> dict:
    """The request body. Only these keys are ever set (F6): adaptive thinking with ``display: summarized`` (F12: thinking is always on
    and billed either way, the default ``omitted`` would leave nothing to save; never ``budget_tokens``, never disabled), no sampling,
    tool_choice or prefill; the effort always (F5)."""
    for t in [req.user, *req.system]:
        check_secrets(t, f"request {req.id}")
    cc = {"type": "ephemeral"} if req.cache_ttl == "5m" else {"type": "ephemeral", "ttl": "1h"}
    out_cfg: dict = {"effort": r.effort}
    if req.schema:
        out_cfg["format"] = {"type": "json_schema", "schema": req.schema}
    params: dict = {"model": r.model, "max_tokens": req.max_tokens, "output_config": out_cfg,
                    "thinking": {"type": "adaptive", "display": "summarized"},
                    "messages": [{"role": "user", "content": req.user}]}
    if req.system:
        blocks = [{"type": "text", "text": t} for t in req.system]
        blocks[-1]["cache_control"] = cc          # the stable prefix is cached; the job text comes after it
        params["system"] = blocks
    tools: list[dict] = []
    if req.web_search_max_uses:
        tools.append({"type": "web_search_20260209", "name": "web_search", "max_uses": req.web_search_max_uses})
    if req.tools_root:
        tools += REPO_TOOLS
    if tools:
        params["tools"] = tools
    if req.tools_root:   # the big first message (a diff) is re-sent every turn: cache it too
        params["messages"] = [{"role": "user", "content": [{"type": "text", "text": req.user, "cache_control": cc}]}]
    assert not [k for k in FORBIDDEN_PARAMS if k in params]
    return params


def cache_key(params: dict, salt: str = "") -> str:
    body = json.dumps({"p": params, "salt": salt}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | None = None) -> None:
        self.dir = Path(path) if path else cache_dir()

    def get(self, key: str) -> dict | None:
        p = self.dir / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def put(self, key: str, row: dict) -> None:
        write_json_atomic(self.dir / f"{key}.json", row)


# --- read-only repo tools (J1, J1b) ------------------------------------------------------------------------------------
REPO_TOOLS = [
    {"name": "list_dir", "description": "List the entries of a folder of the checkout (relative path, '.' for the root).",
     "strict": True, "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"],
                                      "additionalProperties": False}},
    {"name": "read_file", "description": "Read a text file of the checkout (lines start..end, 1-based; at most 400 lines per call).",
     "strict": True, "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"},
                                                                       "end": {"type": "integer"}},
                                      "required": ["path", "start", "end"], "additionalProperties": False}},
    {"name": "grep", "description": "Search a regular expression in the text files under a path; returns up to 60 'file:line: text' rows.",
     "strict": True, "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
                                      "required": ["pattern", "path"], "additionalProperties": False}},
]
MAX_READ_LINES = 400
MAX_GREP_ROWS = 60
MAX_TOOL_CHARS = 30000
MAX_TOOL_CHARS_PER_TURN = 60000   # F10: all tool results of ONE turn together; the rest become an error line, so new tokens per turn have a ceiling
WRAP_UP_TEXT = "Budget or turns are nearly used up: write your final answer now from what you have; do not call tools."


def _safe(root: Path, rel: str) -> Path:
    r = root.resolve()
    p = (r / rel).resolve()           # symlinks are followed HERE, so the checks below see where the path really leads
    if r not in (p, *p.parents):
        raise SecretInPrompt(f"{rel}: outside the checkout")
    check_secret_path(p.relative_to(r), "tool")
    return p


def _visible(entry: Path, r: Path) -> bool:
    """A grep / list candidate: not a link, inside the checkout, not secret-like, not a skipped folder."""
    if entry.is_symlink():
        return False
    try:
        rel = entry.resolve().relative_to(r)
        check_secret_path(rel, "tool")
    except (SecretInPrompt, ValueError, OSError):
        return False
    return True


def run_repo_tool(root: Path, name: str, args: dict) -> str:
    """Execute one read-only tool call. No write, no exec; links, secret-like paths and secret-looking content never leave."""
    try:
        r = root.resolve()
        if name == "list_dir":
            p = _safe(root, args["path"])
            rows = [f"{e.name}{'/' if e.is_dir() else ''}" for e in sorted(p.iterdir()) if _visible(e, r)]
            return "\n".join(rows) or "(empty)"
        if name == "read_file":
            p = _safe(root, args["path"])
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            a, b = max(1, int(args["start"])), min(len(lines), int(args["end"]), int(args["start"]) + MAX_READ_LINES - 1)
            text, hidden = redact("\n".join(f"{i}: {lines[i - 1]}" for i in range(a, b + 1)))
            if hidden:
                text += f"\n({hidden} secret-like string(s) hidden)"
            return text[:MAX_TOOL_CHARS] + (f"\n(file has {len(lines)} lines)" if b < len(lines) else "")
        if name == "grep":
            base = _safe(root, args["path"])
            rx = re.compile(args["pattern"])
            hits: list[str] = []
            files: list[Path] = []
            if base.is_file():
                files = [base]
            else:
                for dirpath, dirs, names in os.walk(base, followlinks=False):
                    dirs[:] = sorted(d for d in dirs if _visible(Path(dirpath) / d, r))
                    files += [Path(dirpath) / n for n in sorted(names) if _visible(Path(dirpath) / n, r)]
            for q in files:
                rel = q.resolve().relative_to(r)
                try:
                    for i, line in enumerate(q.read_text(encoding="utf-8").splitlines(), 1):
                        if rx.search(line) and not SECRET_TEXT.search(line):
                            hits.append(f"{rel}:{i}: {line[:200]}")
                            if len(hits) >= MAX_GREP_ROWS:
                                return "\n".join(hits)
                except (UnicodeDecodeError, OSError):
                    continue
            return "\n".join(hits) or "(no match)"
    except (SecretInPrompt, OSError, re.error, KeyError, ValueError) as e:
        return f"error: {e}"
    return f"error: unknown tool {name}"


# --- the client --------------------------------------------------------------------------------------------------------
class StreamSink:
    """F1: one call on disk as it arrives, ``<ledger>/stream/<uid>.txt``: a header line, then ``[thinking]`` with the summarized thinking
    and ``[answer]`` with the text (F13: thinking is billed and can use all of max_tokens, so a call with no text still leaves a file).
    Written one complete line at a time, each line through ``redact`` (a key-shaped string split across deltas is never half-written),
    and flushed; ``close`` writes the unfinished tail, also redacted. A kill loses at most the unfinished line. ``n`` (answer chars),
    ``thinking_chars`` and ``text`` stay in memory and unredacted."""

    def __init__(self, path: Path, header: str | None = None) -> None:
        self.path, self.n, self.thinking_chars, self.parts, self.buf, self._f = path, 0, 0, [], "", None
        self.section, self.pos, self.answer_at = None, 0, None
        if header is not None:
            self._out(header + "\n")

    def _out(self, text: str) -> None:
        if self._f is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._f = self.path.open("a", encoding="utf-8")
        self._f.write(text)
        self._f.flush()
        self.pos += len(text)

    def _tail(self) -> None:
        if self.buf:
            self._out(redact(self.buf)[0] + "\n")
            self.buf = ""

    def mark(self, section: str) -> None:
        """Start the ``thinking`` or ``answer`` part (a no-op when it is the current one)."""
        if section == self.section:
            return
        self._tail()
        self._out(f"[{section}]\n")
        self.section = section
        if section == "answer" and self.answer_at is None:
            self.answer_at = self.pos

    def _put(self, text: str) -> None:
        self.buf += text
        if "\n" in self.buf:
            *lines, self.buf = self.buf.split("\n")
            self._out("".join(redact(x)[0] + "\n" for x in lines))

    def write(self, text: str) -> None:
        if text:
            self.mark("answer")
            self.n += len(text)
            self.parts.append(text)
            self._put(text)

    def write_thinking(self, text: str) -> None:
        if text:
            self.mark("thinking")
            self.thinking_chars += len(text)
            self._put(text)

    @property
    def received(self) -> int:
        """Characters that arrived and are billed, thinking included (F2)."""
        return self.n + self.thinking_chars

    def close(self) -> None:
        try:
            if self.buf:
                self._out(redact(self.buf)[0])
                self.buf = ""
        finally:
            if self._f is not None:
                self._f.close()
                self._f = None

    def answer_on_disk(self) -> str | None:
        """What the file holds after the ``[answer]`` line (None when no answer part was written)."""
        if self.answer_at is None or not self.path.exists():
            return None
        return self.path.read_text(encoding="utf-8")[self.answer_at:]

    @property
    def text(self) -> str:
        return "".join(self.parts)


def _status(exc: BaseException) -> int | None:
    return getattr(exc, "status_code", None)


class ClaudeAPI:
    """``complete(request)`` for one call (or a tool loop), ``run_job(job)`` for a job (batch from BATCH_MIN requests).
    ``client`` is injected by the tests; ``None`` builds the real SDK client on first use (key + approval checked then)."""

    def __init__(self, client: Any = None, *, ledger: Ledger | None = None, cache: ResponseCache | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
                 exact_count: bool = True) -> None:
        self._client = client
        self.ledger = ledger or Ledger()
        self.cache = cache or ResponseCache()
        self.sleep, self.clock, self.exact_count = sleep, clock, exact_count
        self._runs: dict[str, Run] = {}

    # -- setup --
    def client(self) -> Any:
        if self._client is None:
            if not api_key():
                raise KeyAbsent("ANTHROPIC_API_KEY (or EE_ANTHROPIC_API_KEY) is not set in this environment; no call was made")
            if not (caps().get("approval") or {}).get("ref"):
                raise NotApproved("config/spend_caps.json claude_api.approval is empty: record the OR-24 verdict first")
            import anthropic  # lazy: the tests and the offline estimate do not need the SDK
            self._client = anthropic.Anthropic(api_key=api_key(), base_url=os.environ.get("EXPLAINER_ANTHROPIC_BASE_URL", BASE_URL), max_retries=2)
        return self._client

    def run_for(self, job: str) -> Run:
        c = caps()
        cap = c["jobs"].get(job)
        if cap is None:
            raise ConfigError(f"claude_api.jobs has no cap for job {job!r} in config/spend_caps.json: add it on the creator's word")
        if cap > c["max_usd"] + 1e-9:
            raise spend_caps.OverCeiling(f"job cap {cap} is above claude_api.max_usd {c['max_usd']}")
        if job not in self._runs:
            run = Run.open(ledger_dir() / f"job_{job}.json")
            run.data["caps"][SERVICE] = float(cap)   # config/spend_caps.json is the only home of the number (invariant 2)
            run.save()
            self._runs[job] = run
        return self._runs[job]

    def _reserve(self, job: str, item: str, amount: float) -> None:
        self.ledger.check_gap()
        c = caps()
        if self.ledger.total() + amount > c["max_usd"] * STOP_FRACTION + 1e-9:
            raise CapReached(f"claude_api total {self.ledger.total() + amount:.2f} would pass {int(STOP_FRACTION * 100)} % of "
                             f"{c['max_usd']}; stop and report")
        self.run_for(job).reserve(SERVICE, amount, item)

    # -- one paid call --
    def _count(self, params: dict) -> int | None:
        if not self.exact_count or self._client is None and not api_key():
            return None
        try:
            kw = {k: params[k] for k in ("model", "messages", "system", "tools") if k in params}
            return int(self.client().messages.count_tokens(**kw).input_tokens)
        except Exception:  # noqa: BLE001 - the heuristic is the fallback of an estimate, never a reason to stop
            return None

    def _send(self, params: dict, model: str, *, fallbacks: bool, sink: StreamSink) -> Any:
        """One request with the SDK, always streamed (F1: the text goes to ``sink`` as it arrives); waits and retries a 429 /
        overloaded up to OVERLOAD_WAIT_S in all, but never once text has arrived (F2: that call may be billed; it is not re-sent)."""
        c = self.client()
        if hasattr(c, "with_options"):
            c = c.with_options(max_retries=0)   # F11: the SDK's silent re-send of a timed-out call could bill twice; only this loop retries
        kw = dict(params)
        ns = c.messages
        if fallbacks:
            ns, kw["betas"], kw["fallbacks"] = c.beta.messages, [FALLBACK_BETA], "default"   # F3/F4: direct calls only
        started, delay = self.clock(), 15.0
        while True:
            try:
                with ns.stream(**kw) as s:
                    for ev in s:
                        et, d = getattr(ev, "type", None), getattr(ev, "delta", None)
                        if et == "content_block_start" and getattr(getattr(ev, "content_block", None), "type", None) in ("thinking", "text"):
                            sink.mark("answer" if ev.content_block.type == "text" else "thinking")
                        elif et == "content_block_delta" and getattr(d, "type", None) == "text_delta":
                            sink.write(ev.delta.text)
                        elif et == "content_block_delta" and getattr(d, "type", None) == "thinking_delta":   # signature_delta is ignored
                            sink.write_thinking(ev.delta.thinking)
                    return s.get_final_message()
            except Exception as e:  # noqa: BLE001
                if _status(e) in RETRYABLE and sink.received == 0:
                    if self.clock() - started + delay > OVERLOAD_WAIT_S:
                        raise Overloaded(f"HTTP {_status(e)} for more than {OVERLOAD_WAIT_S // 60} minutes; stop and report") from e
                    self.sleep(delay)
                    delay = min(delay * 2, 240.0)
                    continue
                raise

    def _paid(self, req: Request, r: Route, params: dict, item: str, *, batch: bool = False) -> tuple[Any, Route, float, dict]:
        """Reserve -> send -> settle -> ledger line. Returns (response, route actually used, usd, usage). A 400 from Fable (30-day
        retention) is answered once by the fallback route the request declares (plan), as a second, separately reserved attempt."""
        self.client()      # key and approval are checked before anything is reserved or logged
        try:
            return self._attempt(req, r, params, item, batch, None)
        except Exception as e:  # noqa: BLE001
            if _status(e) == 400 and req.fallback_to and r.alias == "fable":
                alias, eff = req.fallback_to
                rb = Route(r.class_id, alias, routing()["models"][alias], eff)
                check_max_tokens(req, rb)   # the fallback route obeys the same floor and max-effort rule, before it is reserved
                pb = {**params, "model": rb.model, "output_config": {**params["output_config"], "effort": eff}}
                return self._attempt(req, rb, pb, item + "~fb", batch, r.model)
            raise

    def _attempt(self, req: Request, r: Route, params: dict, item: str, batch: bool, fell_from: str | None) -> tuple[Any, Route, float, dict]:
        pr = prices()
        uid = uuid.uuid4().hex[:12]
        est = worst_usd(r.model, params, req.cache_ttl, input_tokens=self._count(params))
        self._reserve(req.job, item, est)
        sink = StreamSink(ledger_dir() / "stream" / f"{uid}.txt",
                          f"--- {item} {r.model} effort={r.effort} max_tokens={params['max_tokens']} ---")
        self.ledger.append({"ev": "start", "uid": uid, "job": req.job, "id": req.id, "model": r.model, "reserved": round(est, 6),
                            "stream": str(sink.path)})
        try:
            resp = self._send(params, r.model, fallbacks=pr["models"][r.model].get("fallbacks") == "default", sink=sink)
        except BaseException as e:
            if sink.received and isinstance(e, Exception):    # F2: text or thinking arrived, then the stream broke: billed for an unknown amount, never re-sent
                note = f"stream broke after {sink.received} chars; billing unknown, reserved amount booked"
                self.run_for(req.job).settle(SERVICE, item, est)
                self.ledger.append({"ev": "done", "uid": uid, "job": req.job, "id": req.id, "model": r.model, "usage": {},
                                    "usd": round(est, 6), "batch": batch, "note": note, "stream": str(sink.path)})
                raise StreamBroken(f"{req.id}: {note} ({type(e).__name__}: {e}); the text so far is in {sink.path}", sink.path,
                                   sink.text) from e
            if _status(e) in UNCHARGED or isinstance(e, Overloaded):
                self.run_for(req.job).refund(SERVICE, est)
                self.ledger.append({"ev": "void", "uid": uid, "job": req.job, "id": req.id, "why": f"{type(e).__name__} {_status(e)}"})
            raise   # anything else (timeout, kill) may have been billed: the open start line stops the next call
        finally:
            sink.close()
        use = usage_of(resp, req.cache_ttl)
        note = None
        try:
            usd = usd_of(getattr(resp, "model", None) or r.model, use, batch=batch, pr=pr)
            it_usd, it_rows = iterations_usd(resp, req.cache_ttl, pr, batch=batch)
            usd = max(usd, it_usd)    # the list may or may not repeat the answering attempt: never read low
        except PriceMissing as e:     # the call is paid: book the reservation instead of losing the answer and the line
            usd, it_rows, note = est, [], f"price missing, booked the reserved amount: {e}"
        self.run_for(req.job).settle(SERVICE, item, usd)
        fb_ran = any(getattr(i, "type", None) == "fallback_message" for i in (getattr(resp.usage, "iterations", None) or []))
        self.ledger.append({"ev": "done", "uid": uid, "job": req.job, "id": req.id, "model": getattr(resp, "model", r.model),
                            "effort": r.effort, "usage": use, "usd": round(usd, 6), "batch": batch, "fallback_ran": fb_ran,
                            "iterations": it_rows, "note": note, "fell_back_from": fell_from, "stop": resp.stop_reason,
                            "request_id": getattr(resp, "_request_id", None)})
        if not batch:
            self._stream_proof(uid, resp, r, sink)
        return resp, r, usd, use

    def _stream_proof(self, uid: str, resp: Any, r: Route, sink: StreamSink) -> None:
        """Gate: the first direct call whose stream file holds exactly the (redacted) answer writes ``stream_proof.json``, once. Until it
        exists ``main run`` refuses everything but a tiny proof job."""
        proof = ledger_dir() / "stream_proof.json"
        try:
            on_disk, text = sink.answer_on_disk(), self._text(resp)   # only the [answer] part: thinking is not the answer
            if proof.exists() or on_disk is None:
                return
            on_disk = on_disk.strip()
            if on_disk and on_disk == redact(text)[0].strip():
                write_json_atomic(proof, {"uid": uid, "model": getattr(resp, "model", r.model), "chars": len(text),
                                          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                          "request_id": getattr(resp, "_request_id", None)})
        except OSError:   # the proof is a gate, never a reason to lose a paid answer
            return

    @staticmethod
    def _thinking(resp: Any) -> str:
        return "\n".join(getattr(b, "thinking", "") or "" for b in resp.content if getattr(b, "type", None) == "thinking")

    @staticmethod
    def _sources(resp: Any) -> list[str]:
        urls: list[str] = []
        for b in resp.content:
            if getattr(b, "type", None) == "web_search_tool_result" and isinstance(getattr(b, "content", None), list):
                for i in b.content:
                    u = getattr(i, "url", None)
                    if u and u not in urls:
                        urls.append(u)
        return urls

    @staticmethod
    def _text(resp: Any) -> str:
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    def _finish(self, req: Request, resp: Any, orig: Route, r_used: Route, usd: float, use: dict, *, turns: int = 1) -> Result:
        if resp.stop_reason == "refusal":
            d = getattr(resp, "stop_details", None)
            raise Refused(getattr(d, "category", None), getattr(d, "explanation", None))
        res = Result(req.id, self._text(resp), getattr(resp, "model", r_used.model), r_used.effort, usd, False, resp.stop_reason, use,
                     fell_back_to=r_used.model if r_used is not orig else None,
                     request_id=getattr(resp, "_request_id", None), ledger_total=self.ledger.total(), turns=turns,
                     sources=self._sources(resp))
        if resp.stop_reason == "max_tokens":   # F3: the paid text travels with the error, F13: so does the thinking
            thinking = self._thinking(resp)
            why = (f"; thinking used the whole max_tokens {req.max_tokens} (output tokens {use['output']}), no answer text; raise "
                   "max_tokens or lower effort") if not res.text.strip() else ""
            raise OutputTruncated(f"{req.id}: hit max_tokens {req.max_tokens} (paid ${usd:.4f}, recorded, not cached){why}", res.text, res,
                                  thinking or None)
        return res

    def complete(self, req: Request) -> Result:
        r = route(req.task_class, req.model, req.effort)
        check_max_tokens(req, r)
        params = build_params(req, r)
        key = cache_key(params, req.cache_salt)
        hit = self.cache.get(key)
        if hit:
            self.ledger.append({"ev": "done", "uid": "cache-" + key[:8], "job": req.job, "id": req.id, "model": hit["model"],
                                "usd": 0.0, "cached": True, "key": key[:12]})
            return Result(req.id, hit["text"], hit["model"], hit["effort"], 0.0, True, hit.get("stop_reason"), hit.get("usage", {}),
                          sources=hit.get("sources", []), ledger_total=self.ledger.total())
        res = self._tool_loop(req, r, params) if req.tools_root else self._single(req, r, params)
        self.cache.put(key, {"text": res.text, "model": res.model, "effort": res.effort, "stop_reason": res.stop_reason,
                             "usage": res.usage, "sources": res.sources, "usd_when_paid": round(res.usd, 6), "id": req.id})
        return res

    def _single(self, req: Request, r: Route, params: dict) -> Result:
        resp, r_used, usd, use = self._paid(req, r, params, f"{req.id}#{uuid.uuid4().hex[:6]}")
        return self._finish(req, resp, r, r_used, usd, use)

    def wrap_up_reason(self, req: Request, r: Route, params: dict, msgs: list, turn: int) -> str | None:
        """F5: why turn ``turn`` must be the wrap-up turn (None = it need not): it is the last allowed turn, or the room under the job's
        80 % stop (and the total's) cannot hold two worst-case turns, so the loop would end abruptly with no answer. Never on turn 1
        and only when the newest message is the tool-result message the wrap-up text can ride on."""
        last = msgs[-1]
        if turn < 2 or last.get("role") != "user" or not isinstance(last.get("content"), list):
            return None
        if turn >= req.max_turns:
            return f"turn {turn} is the last of {req.max_turns}"
        c = caps()
        room = min(c["jobs"][req.job] * STOP_FRACTION - self.run_for(req.job).spent(SERVICE), c["max_usd"] * STOP_FRACTION - self.ledger.total())
        need = 2 * worst_usd(r.model, {**params, "messages": msgs}, req.cache_ttl)
        if room < need:
            return f"room ${room:.2f} under the stop is less than two worst-case turns (${need:.2f})"
        return None

    def _tool_loop(self, req: Request, r: Route, params: dict) -> Result:
        """The reviewer's read-only tools: every turn is reserved and settled on its own. Ends on end_turn; max_turns stops it.

        The cache breakpoint moves to the last block of the conversation every turn (``_with_breakpoint``): without it only the
        system prefix is a cache read and the whole growing history is billed as fresh input again each turn (the J1b scope A
        run, 2026-10-30: $0.03 on turn 2, $0.50 on turn 18). The turns so far are checkpointed to ``partial_<job>_<id>.json`` in the
        ledger folder after EVERY turn (F4), and again with the reason whatever stops the loop (a cap, an overload, Ctrl+C, SIGTERM).
        The last allowed turn, or a turn with too little room left, is a wrap-up turn (F5): one more text block asks for the final
        answer and the tools list is unchanged (the cache prefix stays); a wrap-up turn that still calls tools stops the loop."""
        root = Path(req.tools_root).resolve()
        msgs = list(params["messages"])
        total, tot_use = 0.0, {"input": 0, "output": 0, "cache_read": 0, "write_5m": 0, "write_1h": 0, "searches": 0}
        turn, prev_read, prev_prompt = 0, 0, 0
        try:
            for turn in range(1, req.max_turns + 1):
                sent = msgs
                wrap = self.wrap_up_reason(req, r, params, msgs, turn)
                if wrap:   # on the copy only: a wrap-up turn is the last one, so the transcript keeps the plain conversation
                    sent = [*msgs[:-1], {**msgs[-1], "content": [*msgs[-1]["content"], {"type": "text", "text": WRAP_UP_TEXT}]}]
                p = {**params, "messages": _with_breakpoint(sent, req.cache_ttl)}
                resp, r_used, usd, use = self._paid(req, r, p, f"{req.id}#t{turn}-{uuid.uuid4().hex[:4]}")
                total += usd
                cold = cache_guard(turn, use, prev_read, prev_prompt)
                prev_read, prev_prompt = use["cache_read"], use["input"] + use["cache_read"] + use["write_5m"] + use["write_1h"]
                wants_tools = resp.stop_reason in ("tool_use", "pause_turn")
                if wants_tools:   # F6: the paid turn is in the transcript before any stop below
                    msgs.append({"role": "assistant", "content": resp.content})
                if cold and wants_tools:   # a final answer is kept, whatever its cache did
                    raise CacheCold(f"{req.id}: turn {turn}: {cold}; the loop was stopped after paying ${total:.4f} instead of running to the "
                                    "80 % stop (check the cache breakpoints and the 5-minute TTL)")
                tot_use = {k: tot_use[k] + use[k] for k in tot_use}
                if wants_tools:
                    results, chars = [], 0
                    for b in resp.content:
                        if getattr(b, "type", None) == "tool_use":
                            out = run_repo_tool(root, b.name, dict(b.input)) if b.name in {t["name"] for t in REPO_TOOLS} else "error: unknown tool"
                            if chars + len(out) > MAX_TOOL_CHARS_PER_TURN:   # F10: the loop's new tokens per turn have a ceiling
                                out = "error: per-turn tool output limit reached; ask for less at once"
                            chars += len(out)
                            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
                    if results:
                        msgs.append({"role": "user", "content": results})
                    save_partial(req, msgs, turn, total, f"checkpoint after turn {turn} (the loop is still running)")   # F4
                    if wrap:
                        raise OutputTruncated(f"{req.id}: wrap-up turn still called tools ({wrap}; paid ${total:.4f}, recorded)",
                                              self._text(resp) or None)
                    if not results and resp.stop_reason == "tool_use":
                        break
                    continue
                return self._finish(req, resp, r, r_used, total, tot_use, turns=turn)
            raise OutputTruncated(f"{req.id}: no final answer after {req.max_turns} turns (paid ${total:.4f}, recorded)")
        except BaseException as e:   # F4: Ctrl+C and SIGTERM (as KeyboardInterrupt) save too
            where = save_partial(req, msgs, turn, total, e)
            if where is not None:
                e.add_note(f"partial transcript of {turn} turn(s) saved to {where}")
            raise

    # -- jobs and batches --
    def run_job(self, reqs: list[Request], *, wait: bool = True,
                on_result: Callable[[Request, "Result | Exception"], None] | None = None) -> dict[str, Result | Exception]:
        """Direct calls below BATCH_MIN requests (in order, cache first), the Batch API from BATCH_MIN (tool loops never).
        ``on_result(request, result_or_error)`` is called the moment each result exists (F7), cache hits too, so the caller can write
        its file at once. An error on one direct request stops the job: it is recorded for that id, every later id gets a
        ``not_run`` error, and the finished results are returned instead of being lost."""
        out: dict[str, Result | Exception] = {}

        def put(q: Request, res: Result | Exception) -> None:
            out[q.id] = res
            if on_result is not None:
                on_result(q, res)
        batchable = len(reqs) >= BATCH_MIN and not any(q.tools_root for q in reqs)
        todo = []
        for q in reqs:
            r = route(q.task_class, q.model, q.effort)
            hit = self.cache.get(cache_key(build_params(q, r), q.cache_salt))
            if hit:
                put(q, self.complete(q))
            else:
                todo.append(q)
        if not batchable:
            for n, q in enumerate(todo):
                try:
                    put(q, self.complete(q))
                except (Refused, OutputTruncated) as e:
                    put(q, e)
                except (LLMError, CapReached) as e:
                    put(q, e)
                    for later in todo[n + 1:]:
                        put(later, LLMError(f"not_run: job stopped after {q.id}: {e}"))
                    return out
            return out
        self._batch(todo, wait=wait, put=put)
        return out

    def _batch(self, reqs: list[Request], *, wait: bool, put: Callable[[Request, Result | Exception], None]) -> None:
        bad = [q.id for q in reqs if not SAFE_ID.match(q.id)]
        if bad:
            raise ConfigError(f"batch custom_id must match [A-Za-z0-9_-]{{1,64}}: {bad[:3]}")
        if not reqs:
            return
        job = reqs[0].job
        tag = f"batch-{job}-{hashlib.sha256('|'.join(sorted(q.id for q in reqs)).encode()).hexdigest()[:10]}"
        state_file = ledger_dir() / f"{tag}.json"
        routes = {q.id: route(q.task_class, q.model, q.effort) for q in reqs}
        for q in reqs:
            check_max_tokens(q, routes[q.id])
        params = {q.id: build_params(q, routes[q.id]) for q in reqs}
        by_id = {q.id: q for q in reqs}
        c = self.client()
        if state_file.exists():
            batch_id = json.loads(state_file.read_text(encoding="utf-8"))["batch_id"]   # resume: nothing is paid twice
        else:
            est = sum(worst_usd(routes[i].model, params[i], by_id[i].cache_ttl, batch=True) for i in params)
            self._reserve(job, tag, est)
            for i in params:
                self.ledger.append({"ev": "start", "uid": f"b-{i}", "batch": True, "job": job, "id": i, "model": routes[i].model})
            b = c.messages.batches.create(requests=[{"custom_id": i, "params": params[i]} for i in params])   # F3: no fallbacks here
            batch_id = b.id
            write_json_atomic(state_file, {"batch_id": batch_id, "ids": list(params), "reserved": round(est, 6)})
        while True:
            b = c.messages.batches.retrieve(batch_id)
            if b.processing_status == "ended" or not wait:
                break
            self.sleep(60)
        if b.processing_status != "ended":
            return
        pr, spent = prices(), 0.0
        closed = {x["uid"]: x.get("usd", 0.0) for x in self.ledger.rows() if x["ev"] in ("done", "void")}   # F8: collected before a crash
        for row in c.messages.batches.results(batch_id):
            i = row.custom_id
            q, rt = by_id[i], routes[i]
            if f"b-{i}" in closed:   # a rerun after a crash in this loop: never book the item (or pay its refusal rerun) twice
                spent += closed[f"b-{i}"]
                hit = self.cache.get(cache_key(params[i], q.cache_salt))
                put(q, Result(i, hit["text"], hit["model"], hit["effort"], 0.0, True, hit.get("stop_reason"), hit.get("usage", {}),
                              ledger_total=self.ledger.total()) if hit else LLMError(f"{i}: already collected (see the ledger)"))
                continue
            if row.result.type != "succeeded":
                self.ledger.append({"ev": "void", "uid": f"b-{i}", "job": job, "id": i, "why": row.result.type})
                put(q, LLMError(f"{i}: batch result {row.result.type}"))
                continue
            msg = row.result.message
            use = usage_of(msg, q.cache_ttl)
            usd = usd_of(msg.model, use, batch=True, pr=pr)
            spent += usd
            self.ledger.append({"ev": "done", "uid": f"b-{i}", "job": job, "id": i, "model": msg.model, "effort": rt.effort, "usage": use,
                                "usd": round(usd, 6), "batch": True, "stop": msg.stop_reason})
            if msg.stop_reason == "refusal":      # F3: re-run ONCE as a direct call with fallbacks; never reworded
                try:
                    put(q, self.complete(q))
                except (Refused, OutputTruncated) as e:   # reported; the other results of the batch are still collected
                    put(q, e)
                continue
            res = Result(i, self._text(msg), msg.model, rt.effort, usd, False, msg.stop_reason, use, ledger_total=self.ledger.total())
            if msg.stop_reason == "max_tokens":   # F3: the paid text is kept with the error
                put(q, OutputTruncated(f"{i}: hit max_tokens in the batch (paid, recorded)", res.text, res, self._thinking(msg) or None))
                continue
            self.cache.put(cache_key(params[i], q.cache_salt), {"text": res.text, "model": res.model, "effort": res.effort,
                                                                "stop_reason": res.stop_reason, "usage": use, "id": i})
            put(q, res)
        self.run_for(job).settle(SERVICE, tag, spent)


# --- jobs from files and the command line ------------------------------------------------------------------------------
def load_job(path: Path) -> list[Request]:
    """Job file: {job, task_class, model?, effort?, max_tokens?, system?, system_files?, schema?, web_search_max_uses?, cache_ttl?,
    tools_root?, max_turns?, fallback_to?, requests: [{id, user | user_file, cache_salt?}]}. Paths are relative to the job file."""
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(path).resolve().parent

    def read(rel: str) -> str:
        p = (base / rel)
        check_secret_path(rel, f"job file {rel}")
        t = p.read_text(encoding="utf-8")
        check_secrets(t, f"job file {rel}")
        return t

    system = list(spec.get("system", [])) + [read(f) for f in spec.get("system_files", [])]
    common = {k: spec[k] for k in ("task_class", "model", "effort", "max_tokens", "schema", "web_search_max_uses", "cache_ttl",
                                   "max_turns", "max_effort_reason") if k in spec}
    if spec.get("tools_root") and spec.get("cache_ttl") == "1h" and not float(spec.get("measured_turn_gap_s") or 0) > SLOW_TURN_GAP_S:
        raise ConfigError("a tool loop with cache_ttl 1h needs \"measured_turn_gap_s\" > 300 in the job file (the gap between turns "
                          "measured in an earlier run's ledger); the 1h TTL writes cost 2x and are an option, not a default")
    if spec.get("tools_root"):
        common["tools_root"] = str((base / spec["tools_root"]).resolve())
    if spec.get("fallback_to"):
        common["fallback_to"] = tuple(spec["fallback_to"])
    return [Request(id=q["id"], user=q["user"] if "user" in q else read(q["user_file"]), job=spec["job"], system=system,
                    cache_salt=q.get("cache_salt", ""), **common) for q in spec["requests"]]


SLOW_TURN_GAP_S = 300          # the 5-minute TTL: a loop whose turns are further apart than this loses its cache (C2)
CACHE_GUARD_FROM_TURN = 3       # the first turns have little history to lose
CACHE_GUARD_MIN_SHARE = 0.6     # (cache read + cache written) / all prompt tokens of a turn
CACHE_GUARD_MIN_READ_SHARE = 0.5  # cache READS / the previous turn's whole prompt: a hit reads at least that prefix; writes do not count
CACHE_GUARD_STUCK_INPUT = 1000  # fresh input tokens that a cache read of the same size as last turn's cannot explain


def cache_guard(turn: int, use: dict, prev_read: int, prev_prompt: int = 0) -> str | None:
    """The tool loop's self-check of the `cached` assumption behind its estimate: from turn 3, a turn whose prompt is mostly fresh
    input, or whose cache read did not grow while fresh input is large (the read stuck at the system prefix), is the state that cost
    $5.02. A turn whose cache read is under half of the previous turn's whole prompt (``prev_prompt``) is a full miss, the history
    written again every turn (F9); it is measured against the previous prompt, not this one, so one big tool result is no miss.
    Returns the reason, or None."""
    prompt = use["input"] + use["cache_read"] + use["write_5m"] + use["write_1h"]
    if turn < CACHE_GUARD_FROM_TURN or prompt < 1024:   # below the API's minimum cacheable prompt there is nothing to judge
        return None
    share = (use["cache_read"] + use["write_5m"] + use["write_1h"]) / prompt
    if share < CACHE_GUARD_MIN_SHARE:
        return f"only {share:.0%} of the prompt tokens were cache reads or writes (need {CACHE_GUARD_MIN_SHARE:.0%})"
    if use["cache_read"] <= prev_read and use["input"] >= CACHE_GUARD_STUCK_INPUT:
        return (f"the cache read stayed at {use['cache_read']} tokens while {use['input']} fresh input tokens were billed "
                "(the history is not being cached)")
    if prev_prompt >= 1024 and use["cache_read"] < CACHE_GUARD_MIN_READ_SHARE * prev_prompt:   # F9: a full miss is the dearest mode
        return (f"only {use['cache_read'] / prev_prompt:.0%} of the previous turn's prompt was read from cache (a miss re-writes the "
                "history every turn)")
    return None


LOOP_NEW_TOKENS = 2000   # tool-result tokens a repo-tool turn adds: measured on the J1b scope A run (about 1.5k a turn), rounded up
LOOP_OUT_TOKENS = 600


def loop_usd(model: str, first_tokens: int, turns: int, new_per_turn: int, out_per_turn: int, ttl: str = "5m", *,
             mode: str = "cached", final_out: int | None = None) -> float:
    """What a tool loop costs over ``turns`` turns. Each turn adds a tool result (``new_per_turn``) and the model's output
    (``out_per_turn``, billed as output the turn it is written and as input the turn after).
    ``cached``: turn 1 writes the prompt; each later turn reads the whole context so far from cache and writes only what the last
    turn added (its output and the tool result). The best case.
    ``uncached``: no cache read at all, the context is fresh input every turn (what the J1b scope A run billed, $5.02 for 18 turns).
    ``miss``: the cache never hits and everything is written again every turn (what the per-turn reservation assumes).
    ``final_out``: the output of the LAST turn (the answer; the estimate passes ``max_tokens``), where ``out_per_turn`` is a tool call."""
    key = "write_5m" if ttl == "5m" else "write_1h"
    zero = {"input": 0, "output": 0, "cache_read": 0, "write_5m": 0, "write_1h": 0, "searches": 0}
    if mode not in ("cached", "uncached", "miss"):
        raise ValueError(f"loop_usd mode {mode!r}")
    added, usd = new_per_turn + out_per_turn, 0.0
    for turn in range(turns):
        ctx = first_tokens + turn * added                  # the whole input of this turn
        if mode == "uncached":
            u = {**zero, "input": ctx}
        elif mode == "miss" or turn == 0:
            u = {**zero, key: ctx}
        else:
            u = {**zero, "cache_read": ctx - added, key: added}
        usd += usd_of(model, {**u, "output": final_out if final_out is not None and turn == turns - 1 else out_per_turn})
    return usd


def estimate(reqs: list[Request], *, api: ClaudeAPI | None = None, expected_output: int | None = None,
             turns: int | None = None, new_tokens_per_turn: int = LOOP_NEW_TOKENS, loop_bound: str = "cached") -> dict:
    """Tokens and dollars of a job, spending nothing: exact input tokens when a client may be built, else the offline bound."""
    pr, rows = prices(), []
    for q in reqs:
        r = route(q.task_class, q.model, q.effort)
        params = build_params(q, r)
        hit = bool(ResponseCache().get(cache_key(params, q.cache_salt))) if api is None else bool(api.cache.get(cache_key(params, q.cache_salt)))
        toks = None if api is None else api._count(params)   # noqa: SLF001
        n_in = toks if toks is not None else math.ceil(_chars({k: params.get(k) for k in ("system", "messages", "tools")}) / CHARS_PER_TOKEN)
        batch = len(reqs) >= BATCH_MIN and not q.tools_root
        worst = worst_usd(r.model, params, q.cache_ttl, batch=batch, input_tokens=n_in)
        typical = usd_of(r.model, {"input": n_in, "output": expected_output or 0, "cache_read": 0, "write_5m": 0, "write_1h": 0,
                                   "searches": 0}, batch=batch, pr=pr) if expected_output is not None else None
        rows.append({"id": q.id, "model": r.model, "effort": r.effort, "max_tokens_floor_ok": q.max_tokens >= MIN_MAX_TOKENS_BY_EFFORT.get(r.effort, 0),
                     "max_effort_reason_ok": max_effort_ok(q, r),
                     "input_tokens": n_in, "exact": toks is not None, "cached": hit,
                     "batch": batch, "worst_usd": round(0.0 if hit else worst, 4),
                     "usd_at_expected_output": None if typical is None or hit else round(typical, 4)})
        if q.tools_root:   # a tool loop is many calls: the figures above are TURN 1 ONLY, the loop figures are what a run can cost
            t, out_t = turns or q.max_turns, expected_output or LOOP_OUT_TOKENS
            figs = {m: round(loop_usd(r.model, n_in, t, new_tokens_per_turn, out_t, q.cache_ttl, mode=m, final_out=q.max_tokens), 4) for m in ("cached", "uncached", "miss")}
            rows[-1]["loop"] = {"warning": "tool loop: worst_usd and usd_at_expected_output price the FIRST turn only; the loop figures assume "
                                           f"{new_tokens_per_turn} new tokens and {out_t} output tokens per turn (assumptions, not measurements; the last turn is priced "
                                           f"at max_tokens {q.max_tokens}, and the tool results of one turn are capped at {MAX_TOOL_CHARS_PER_TURN} "
                                           "characters); a cache miss costs more than uncached",
                                "turns": t, "usd_if_cached": figs["cached"], "usd_if_uncached": figs["uncached"], "usd_if_miss": figs["miss"],
                                "bound": loop_bound}
            if not hit:
                rows[-1]["worst_usd"] = max(rows[-1]["worst_usd"], figs[{"cached": "cached", "uncached": "uncached", "miss": "miss"}[loop_bound]])
    c = caps()
    job = reqs[0].job
    worst_total = round(sum(x["worst_usd"] for x in rows), 4)
    return {"job": job, "requests": rows, "worst_total_usd": worst_total, "job_cap": c["jobs"].get(job), "max_usd": c["max_usd"],
            "stop_at_job": None if c["jobs"].get(job) is None else round(c["jobs"][job] * STOP_FRACTION, 2),
            "fits_job_cap": c["jobs"].get(job) is not None and worst_total <= c["jobs"][job] * STOP_FRACTION,
            "ledger_total": Ledger().total()}


PROOF_MAX_TOKENS = 256


def proof_path() -> Path:
    return ledger_dir() / "stream_proof.json"


def _on_sigterm(signum: int, frame: Any) -> None:
    raise KeyboardInterrupt("SIGTERM")


def _out_name(q: Request) -> str:
    return f"{q.id}.json" if q.schema else f"{q.id}.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="claude_api")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("estimate")
    e.add_argument("job")
    e.add_argument("--expected-output", type=int, default=None)
    e.add_argument("--offline", action="store_true", help="never call count_tokens")
    e.add_argument("--turns", type=int, default=None, help="tool loops: turns to price (default: the job's max_turns)")
    e.add_argument("--new-tokens-per-turn", type=int, default=LOOP_NEW_TOKENS, help="tool loops: tool result tokens added per turn")
    e.add_argument("--loop-bound", choices=("cached", "uncached", "miss"), default="cached",
                   help="tool loops: which loop figure is the job's worst case (default cached, the expected case with the breakpoint fix; uncached and miss are the conservative bounds)")
    r_ = sub.add_parser("run")
    r_.add_argument("job")
    r_.add_argument("--out", default=None)
    r_.add_argument("--loop-bound", choices=("cached", "uncached", "miss"), default="cached",
                    help="tool loops: which loop figure the pre-run refusal uses (default cached, the expected case with the breakpoint fix; uncached and miss are the conservative bounds)")
    r_.add_argument("--no-wait", action="store_true", help="batch: submit (or look once) and return; run again to collect")
    sub.add_parser("status")
    v = sub.add_parser("void")
    v.add_argument("uid")
    v.add_argument("--usd", type=float, default=None, help="default: the amount reserved for that call (never reads low)")
    a = ap.parse_args(argv)
    api = ClaudeAPI()
    if a.cmd == "status":
        c = caps()
        print(json.dumps({"key_present": bool(api_key()), "approved": bool((c.get("approval") or {}).get("ref")),
                          "max_usd": c["max_usd"], "jobs": c["jobs"], "spent_total": api.ledger.total(), "spent_by_job": api.ledger.by_job(),
                          "lines_below_spent": lines_below_spent(c, api.ledger.by_job()),
                          "open_calls": [x["uid"] for x in api.ledger.open_calls()], "stream_proof": proof_path().exists()}, indent=2))
        return 0
    if a.cmd == "void":
        start = next((x for x in api.ledger.open_calls() if x["uid"] == a.uid), None)
        if start is None:
            print(f"{a.uid} is not an open call")
            return 1
        usd = a.usd if a.usd is not None else float(start.get("reserved", 0.0))
        api.ledger.append({"ev": "done", "uid": a.uid, "job": start["job"], "id": start["id"], "usd": usd,
                           "note": "closed by hand" + (" at the reserved amount" if a.usd is None else "")})
        print(f"closed {a.uid} at ${usd}")
        return 0
    reqs = load_job(Path(a.job))
    if a.cmd == "run":
        tiny = len(reqs) == 1 and not reqs[0].tools_root and reqs[0].max_tokens <= PROOF_MAX_TOKENS
        if not proof_path().exists():
            if not tiny:
                print(f"refused: {proof_path()} is missing. The first real call must be a tiny stream-proof job (one request, no tools_root, "
                      f"max_tokens <= {PROOF_MAX_TOKENS}, about $0.0001 on Haiku 5.5); it proves the answer reaches the stream file.")
                return 4
            print("this is the stream-proof call: it writes stream_proof.json when its stream file equals the answer")
        pre = estimate(reqs, loop_bound=a.loop_bound)
        low = [x["id"] for x in pre["requests"] if not x["max_tokens_floor_ok"]]
        noreason = [x["id"] for x in pre["requests"] if not x["max_effort_reason_ok"]]
        if noreason:
            print(f"refused: effort max on a single-shot request needs \"max_effort_reason\" in the job file for {noreason}; "
                  "plans, specs and audits run at xhigh")
            return 3
        if low:
            print(f"refused: max_tokens is under the floor of its effort for {low} (MIN_MAX_TOKENS_BY_EFFORT {MIN_MAX_TOKENS_BY_EFFORT}); "
                  "thinking is billed as output and can use all of it")
            return 3    # offline bound; a job whose worst case passes the job's 80 % stop does not start (it would stop half-done)
        if not pre["fits_job_cap"]:
            print(json.dumps(pre, indent=2))
            print(f"refused: the worst case ${pre['worst_total_usd']} passes the stop of job {pre['job']} (${pre['stop_at_job']}); "
                  "shrink the job or ask for a higher cap")
            return 3
    if a.cmd == "estimate":
        live = None if a.offline or not api_key() or not (caps().get("approval") or {}).get("ref") else api
        print(json.dumps(estimate(reqs, api=live, expected_output=a.expected_output, turns=a.turns,
                                 new_tokens_per_turn=a.new_tokens_per_turn, loop_bound=a.loop_bound), indent=2))
        return 0
    out = Path(a.out) if a.out else ledger_dir() / "out" / reqs[0].job
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {}

    def write_one(q: Request, res: Result | Exception) -> None:   # F7: each file is written the moment its result exists
        if isinstance(res, Result):
            write_text_atomic(out / _out_name(q), res.text)
            if res.sources:
                write_json_atomic(out / f"{q.id}.sources.json", res.sources)
            summary[q.id] = {"ok": True, "model": res.model, "usd": round(res.usd, 4), "cached": res.cached}
        else:
            summary[q.id] = {"ok": False, "error": str(res)}
            text = getattr(res, "text", None)
            if isinstance(res, OutputTruncated):   # F3: what was paid for is kept
                summary[q.id]["truncated"] = True
                if text:
                    write_text_atomic(out / f"{q.id}.truncated.{'json' if q.schema else 'md'}", redact(text)[0])
                if getattr(res, "thinking", None):   # F13: the paid thinking summary is kept too
                    write_text_atomic(out / f"{q.id}.thinking.md", redact(res.thinking)[0])
    try:
        old_term = signal.signal(signal.SIGTERM, _on_sigterm)   # F4: a kill saves and books like Ctrl+C
    except (ValueError, OSError):   # not the main thread
        old_term = None
    try:
        api.run_job(reqs, wait=not a.no_wait, on_result=write_one)
    finally:
        if old_term is not None:
            signal.signal(signal.SIGTERM, old_term)
    if not summary:
        print("batch not finished yet: run the same command again to collect it")
    summary["_ledger_total_usd"] = api.ledger.total()
    write_json_atomic(out / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if all(v.get("ok", True) for v in summary.values() if isinstance(v, dict)) else 2


if __name__ == "__main__":
    sys.exit(main())
