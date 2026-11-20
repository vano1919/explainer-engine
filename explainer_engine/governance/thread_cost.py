"""Context-cost rule CC-1 (owner 2026-11-20 14:01 and 14:04 UTC; ``docs/ORCHESTRATION.md`` OR-38): every thread watches its own cost and says so.

Every model step re-reads the whole history, so cost is steps x context size. A thread whose context is over ``context_tokens`` or whose
steps since it started (or was last compacted) are over ``steps`` (both in ``config/thread_cost.json``, ONE place, a hypothesis that changes
only on the owner's word) must, before it does anything else:

1. post ONE short line containing the request phrase ("I am expensive now: compact me or hand me over") to the thread, the coordinator or
   the lead (a ``post_message``, ``message_thread``, ``message_coordinator`` or ``send_message`` call), and
2. write its handover file ``HANDOVER_<session id>.md`` (sections goal, state, paths, open questions; nothing else, size-capped).

Two hooks make it automatic: ``prompt`` (UserPromptSubmit) injects the instruction while a thread is over the limit and has not done both;
``stop`` (Stop) refuses to end the turn until both are done (after ``max_stop_blocks`` refusals it lets go and records an incident in
``jobs/_cost/incidents.jsonl``, so a broken tool can never trap a thread). Both fail OPEN when the transcript cannot be read.

Honest limit: a hook can warn and block a turn, it cannot compact a thread. The coordinator or the owner compacts it or opens a fresh
thread that gets only the handover file and the files it names (``docs/ORCHESTRATION.md`` OR-38). The measure reads the session transcript
(the harness' JSONL): context = input + cache-read + cache-creation tokens of the last main-thread model message, steps = distinct model
messages since the last ``compact_boundary``; sub-agent (sidechain) messages are not counted. stdlib only.

usage: ``python -m explainer_engine.governance.thread_cost prompt|stop`` (hook, event JSON on stdin) or ``report <transcript.jsonl>``."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from explainer_engine.governance import root_dir

CONFIG = Path("config") / "thread_cost.json"
STATE_DIR = Path("jobs") / "_cost"
POST_TOOLS = ("mcp__hearthbot__post_message", "mcp__hearthbot__message_thread", "mcp__hearthbot__message_coordinator",
              "mcp__claude-code-remote__send_message")
TOKEN_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
_SESSION = re.compile(r"[A-Za-z0-9_-]{1,80}")


class CostConfigError(Exception):
    pass


def load_config(root=None) -> dict:
    path = root_dir(root) / CONFIG
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CostConfigError(f"{CONFIG}: unreadable: {exc}") from exc
    errs = [k for k in ("context_tokens", "steps", "max_stop_blocks", "max_request_chars", "min_handover_bytes", "max_handover_bytes")
            if not (isinstance(cfg.get(k), int) and not isinstance(cfg.get(k), bool) and cfg[k] > 0)]
    if not (isinstance(cfg.get("sections"), list) and cfg["sections"] and all(isinstance(s, str) and s for s in cfg["sections"])):
        errs.append("sections")
    if not (isinstance(cfg.get("handover_dirs"), list) and cfg["handover_dirs"]):
        errs.append("handover_dirs")
    if not (isinstance(cfg.get("request_phrase"), str) and cfg["request_phrase"].strip()):
        errs.append("request_phrase")
    if errs:
        raise CostConfigError(f"{CONFIG}: bad or missing keys: {', '.join(errs)}")
    return cfg


def _epoch(ts) -> float | None:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _phrase_key(cfg: dict) -> str:
    return re.sub(r"\W+", " ", cfg["request_phrase"].lower()).strip()


def _texts(block: dict) -> str:
    """Every string a tool call carries, for the phrase search."""
    return json.dumps(block.get("input") or {}, ensure_ascii=False)


def measure(transcript: Path, cfg: dict) -> dict:
    """{context_tokens, steps, compactions, boundary_ts, request_posted, request_chars, model} for the part of the session after the last compaction."""
    key = _phrase_key(cfg)
    ids: set[str] = set()
    ctx, compactions, boundary_ts, model = 0, 0, None, None
    posted, posted_chars = False, 0
    with Path(transcript).open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            kind = o.get("type")
            if kind == "system" and o.get("subtype") == "compact_boundary":
                ids, ctx, compactions, boundary_ts, posted, posted_chars = set(), 0, compactions + 1, o.get("timestamp"), False, 0
                continue
            if kind != "assistant" or o.get("isSidechain"):
                continue
            msg = o.get("message") or {}
            ids.add(str(msg.get("id") or o.get("uuid")))
            usage = msg.get("usage") or {}
            if usage:
                ctx = sum(int(usage.get(k) or 0) for k in TOKEN_KEYS)
            model = msg.get("model") or model
            content = msg.get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in POST_TOOLS:
                    text = _texts(block)
                    if key in re.sub(r"\W+", " ", text.lower()):
                        posted, posted_chars = True, len(text)
    return {"context_tokens": ctx, "steps": len(ids), "compactions": compactions, "boundary_ts": boundary_ts, "request_posted": posted,
            "request_chars": posted_chars, "model": model}


def over_reasons(m: dict, cfg: dict) -> list[str]:
    out = []
    if m["context_tokens"] > cfg["context_tokens"]:
        out.append(f"context {m['context_tokens']:,} tokens is over {cfg['context_tokens']:,}")
    if m["steps"] > cfg["steps"]:
        out.append(f"{m['steps']} model steps since the start or the last compaction is over {cfg['steps']}")
    return out


def handover_file(root: Path, session_id: str, cfg: dict) -> Path:
    """``HANDOVER_<session id>.md`` in the first existing handover dir (an absolute project-files dir, else the repo's ``jobs/_handover``)."""
    name = f"HANDOVER_{session_id}.md"
    for d in cfg["handover_dirs"]:
        p = Path(d)
        if p.is_absolute() and p.is_dir():
            return p / name
        if not p.is_absolute():
            return Path(root) / p / name
    return Path(root) / STATE_DIR.parent / "_handover" / name


def handover_problems(path: Path, cfg: dict, since_ts: str | None = None) -> list[str]:
    """What is wrong with the handover file (empty = fine): missing, stale (older than the last compaction), too small or too big (a recap),
    or a required section missing or empty."""
    if not path.is_file():
        return [f"handover file {path} is not written"]
    problems: list[str] = []
    size = path.stat().st_size
    if since_ts and (_epoch(since_ts) or 0) > path.stat().st_mtime:
        problems.append("the handover file is older than the last compaction: write a fresh one")
    if size < cfg["min_handover_bytes"]:
        problems.append(f"the handover file is {size} bytes (at least {cfg['min_handover_bytes']})")
    if size > cfg["max_handover_bytes"]:
        problems.append(f"the handover file is {size} bytes (at most {cfg['max_handover_bytes']}: goal, state, paths, open questions, no recap)")
    text = path.read_text(encoding="utf-8", errors="replace")
    for sec in cfg["sections"]:
        m = re.search(rf"^#{{1,6}}[ \t]*{re.escape(sec)}\b[^\n]*\n(.*?)(?=^#{{1,6}}[ \t]|\Z)", text, re.I | re.S | re.M)
        if not m or not m.group(1).strip():
            problems.append(f"section '{sec}' is missing or empty")
    return problems


def status(event: dict, root=None) -> dict | None:
    """The full picture for one hook event, or None when the transcript cannot be read (fail open)."""
    root = root_dir(root)
    cfg = load_config(root)
    tp = event.get("transcript_path")
    if not tp or not Path(tp).is_file():
        return None
    sid = str(event.get("session_id") or "")
    if not _SESSION.fullmatch(sid):
        return None
    m = measure(Path(tp), cfg)
    reasons = over_reasons(m, cfg)
    problems: list[str] = []
    if reasons:
        if not m["request_posted"]:
            problems.append(f"post ONE line saying \"{cfg['request_phrase']}\" to the thread, your coordinator or the lead")
        elif m["request_chars"] > cfg["max_request_chars"]:
            problems.append(f"the request line is {m['request_chars']} characters (at most {cfg['max_request_chars']}): one short line, no recap")
        hf = handover_file(root, sid, cfg)
        problems += [f"write {hf}: " + p if "not written" not in p else p for p in handover_problems(hf, cfg, m["boundary_ts"])]
    return {"measure": m, "reasons": reasons, "problems": problems, "over": bool(reasons), "satisfied": bool(reasons) and not problems,
            "handover": str(handover_file(root, sid, cfg)), "session_id": sid, "config": cfg}


def instruction(st: dict) -> str:
    cfg = st["config"]
    return (f"CC-1 (context-cost rule): you are expensive now: {'; '.join(st['reasons'])}. Before any other work: "
            + " AND ".join(st["problems"]) + f". The handover file holds only: {', '.join(cfg['sections'])} (no recap of old chats). "
            "Then wait for the coordinator or owner to compact you or hand you over. A hook cannot compact you; this turn cannot end until it is done.")


def prompt_hook(event: dict, root=None) -> str:
    """Text for UserPromptSubmit (stdout becomes context): the instruction while over the limit and not yet done, else nothing."""
    st = status(event, root)
    return instruction(st) if st and st["over"] and not st["satisfied"] else ""


def _record_incident(root: Path, key: str, st: dict) -> None:
    d = root / STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    row = {"at": time.time(), "session": st["session_id"], "key": key, "reasons": st["reasons"], "problems": st["problems"]}
    with (d / "incidents.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stop_hook(event: dict, root=None) -> int:
    """0 = the turn may end; 2 = refused (the message goes back to the thread). After ``max_stop_blocks`` refusals it lets go and records an incident."""
    root = root_dir(root)
    st = status(event, root)
    counter = root / STATE_DIR / "stop_blocks.json"
    try:
        counts = json.loads(counter.read_text(encoding="utf-8")) if counter.is_file() else {}
    except ValueError:
        counts = {}
    if not st:
        return 0
    key = f"{st['session_id']}:{st['measure']['boundary_ts']}"
    if not st["over"] or st["satisfied"]:
        if key in counts:
            counts.pop(key)
            counter.write_text(json.dumps(counts), encoding="utf-8")
        return 0
    n = int(counts.get(key, 0)) + 1
    counter.parent.mkdir(parents=True, exist_ok=True)
    if n > st["config"]["max_stop_blocks"]:
        _record_incident(root, key, st)
        counts.pop(key, None)
        counter.write_text(json.dumps(counts), encoding="utf-8")
        print("CC-1: let go after repeated refusals; the incident is in jobs/_cost/incidents.jsonl", file=sys.stderr)
        return 0
    counts[key] = n
    counter.write_text(json.dumps(counts), encoding="utf-8")
    print(instruction(st), file=sys.stderr)
    return 2


def report(transcript: Path, root=None) -> dict:
    cfg = load_config(root)
    m = measure(Path(transcript), cfg)
    return {**m, "limits": {"context_tokens": cfg["context_tokens"], "steps": cfg["steps"]}, "over": over_reasons(m, cfg)}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    what = argv[0] if argv else ""
    if what == "report" and len(argv) > 1:
        print(json.dumps(report(Path(argv[1])), indent=1))
        return 0
    if what not in ("prompt", "stop"):
        raise SystemExit(__doc__)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    try:
        if what == "prompt":
            text = prompt_hook(event)
            if text:
                print(text)
            return 0
        return stop_hook(event)
    except Exception as exc:                                       # every failure of the check itself lets the thread go (fail open)
        print(f"thread_cost {what} skipped: {type(exc).__name__}: {str(exc)[:120]}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
