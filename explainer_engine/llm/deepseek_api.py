"""The DeepSeek worker: a short brief plus the needed files go out, a tested diff comes back (skill deepseek-worker).

Claude plans and checks; DeepSeek writes. One command runs the whole loop without a Claude turn in between: send the brief and the
files, parse the edit blocks, apply them, run the test command, send the failure back (at most ``max_rounds``, the last round on Pro),
then print ONE summary line. The thread reads that line and ``patch.diff``, never the model's raw answer.

    python -m explainer_engine.llm.deepseek_api code   --brief B.md --files a.py b.py --test "python -m pytest -q tests/unit/test_a.py" --max-usd 0.50
    python -m explainer_engine.llm.deepseek_api review --brief B.md --diff patch.diff --max-usd 0.20
    python -m explainer_engine.llm.deepseek_api text   --brief B.md --files notes.md --out draft.md --max-usd 0.30
    python -m explainer_engine.llm.deepseek_api spent | balance          # add --dry-run to code/review/text for the estimate only

Money (invariants 1-2, OR-33): prices and limits are facts in ``config/deepseek.json``; the ceiling is the ``deepseek_api`` line of
``config/spend_caps.json`` and a real call is refused without it. Every call is estimated at the peak price first and refused past 80 %
of the ceiling or past the job's ``--max-usd``; the answer is written to a file as it streams; every call is one ledger line. Secrets
never leave: the paths and the text are checked with the Claude client's checks. Files in ``never_paths`` (governance, money, hooks,
paid code) are refused as edit targets: Claude writes those itself.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterator

from explainer_engine.core import spend_caps
from explainer_engine.core.errors import EngineError
from explainer_engine.core.ledger import STOP_FRACTION
from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.llm.claude_api import check_secret_path, check_secrets, redact

ROOT = Path(__file__).resolve().parents[2]
UTC = datetime.timezone.utc
M_SEARCH, M_SPLIT, M_REPLACE = "<" * 7 + " SEARCH", "=" * 7, ">" * 7 + " REPLACE"   # built, so no file holds a conflict marker
HEADER = re.compile(r"^### FILE: *(\S.*?) *$", re.M)
BLOCK = re.compile(re.escape(M_SEARCH) + r"\n(.*?)^" + re.escape(M_SPLIT) + r"\n(.*?)^" + re.escape(M_REPLACE), re.S | re.M)

CODE_SYSTEM = f"""You are the code writer of a Python repository. Do exactly the task of the brief and nothing else: no refactor,
no renamed symbols, no new dependency, no changed test expectations unless the brief says so. Match the style of the files you see
(line length about 120). Answer ONLY with edit blocks, no prose:

### FILE: path/from/repo/root.py
{M_SEARCH}
exact existing lines, copied character for character, enough of them to occur exactly once in the file
{M_SPLIT}
the new lines
{M_REPLACE}

One header per file, then one block per change. A NEW file is one block with an EMPTY search part. You may change only the files you
were given and create new files; never rewrite a whole existing file."""
REVIEW_SYSTEM = """You review a diff against its brief. Look for: a wrong result, a broken caller, a missed case of the brief, a weakened
test, work outside the brief. Ignore style. Answer with JSON only: {"verdict": "PASS" | "FIX", "findings": [{"file": "...", "line": 0,
"severity": "high" | "low", "problem": "...", "fix": "..."}]}; at most 5 findings, the worst first; PASS means no high finding."""
TEXT_SYSTEM = "Do exactly the task of the brief with the material you are given. Answer with the finished text only: no preface, no notes."


class DeepSeekError(EngineError):
    """A DeepSeek call was refused or failed."""


class NotApproved(DeepSeekError):
    """config/spend_caps.json has no deepseek_api line, or the key is absent."""


class CapReached(DeepSeekError):
    """The call would pass 80 % of the ceiling or the job's own limit."""


class StreamBroken(DeepSeekError):
    """The answer stopped before its usage line; the partial text is in the sink file."""


def config() -> dict:
    return json.loads(Path(os.environ.get("EXPLAINER_DEEPSEEK_CONFIG") or ROOT / "config" / "deepseek.json").read_text(encoding="utf-8"))


def cap_line() -> dict:
    c = spend_caps.load().get("deepseek_api")
    if not isinstance(c, dict) or "max_usd" not in c:
        raise NotApproved("config/spend_caps.json has no deepseek_api {max_usd, period} line: spending needs the creator's yes")
    return c


def ledger_path() -> Path:
    env = os.environ.get("EXPLAINER_DEEPSEEK_LEDGER")
    if env:
        return Path(env)
    shared = Path("/mnt/project-files/")
    return (shared / "explainer-engine/deepseek/ledger.jsonl") if shared.is_dir() else ROOT / "jobs" / "deepseek" / "ledger.jsonl"


def is_peak(when: datetime.datetime, cfg: dict) -> bool:
    p = cfg["peak_utc"]
    when = when.astimezone(UTC)
    return when.weekday() in p["weekdays"] and any(a <= when.hour < b for a, b in p["hours"])


def usd_of(model: str, usage: dict, when: datetime.datetime, cfg: dict) -> float:
    m = cfg["models"][model]
    hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    miss = int(usage.get("prompt_cache_miss_tokens") or max(0, int(usage.get("prompt_tokens") or 0) - hit))
    usd = (hit * m["cache_read"] + miss * m["in"] + int(usage.get("completion_tokens") or 0) * m["out"]) / 1e6
    return usd * (1.0 if is_peak(when, cfg) else cfg["off_peak_factor"])


def worst_usd(model: str, input_chars: int, max_tokens: int, cfg: dict) -> float:
    """The most this call can cost: the peak price, no cache hit, the whole output allowance used."""
    m = cfg["models"][model]
    return (input_chars / cfg["limits"]["chars_per_token"] * m["in"] + max_tokens * m["out"]) / 1e6


def period_start(period: str, now: datetime.datetime) -> datetime.datetime:
    day = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return day - datetime.timedelta(days=day.weekday())
    if period == "month":
        return day.replace(day=1)
    return datetime.datetime.min.replace(tzinfo=UTC)


def http_stream(url: str, headers: dict, body: dict, timeout: float = 900.0) -> Iterator[str]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            yield raw.decode("utf-8", "replace")


class Worker:
    """One DeepSeek job: its ceiling, its ledger and its transport (tests pass a fake transport, a cap and a clock)."""

    def __init__(self, *, job: str = "job", max_usd: float = 0.5, cfg: dict | None = None, cap: dict | None = None,
                 ledger: Path | None = None, transport: Callable[..., Iterator[str]] | None = None,
                 now: Callable[[], datetime.datetime] | None = None, sleep: Callable[[float], None] = time.sleep, key: str | None = None):
        self.cfg = cfg or config()
        self.cap = cap
        self.job, self.max_usd, self.job_usd = job, float(max_usd), 0.0
        self.ledger = Path(ledger) if ledger else ledger_path()
        self.transport, self.sleep = transport or http_stream, sleep
        self.now = now or (lambda: datetime.datetime.now(UTC))
        self.key = key

    # --- money
    def entries(self) -> list[dict]:
        if not self.ledger.exists():
            return []
        return [json.loads(x) for x in self.ledger.read_text(encoding="utf-8").splitlines() if x.strip()]

    def spent(self) -> float:
        start = period_start((self.cap or {}).get("period", "total"), self.now()).isoformat()
        return sum(float(e["usd"]) for e in self.entries() if e["ts"] >= start)

    def reserve(self, estimate: float) -> None:
        if self.cap is None:
            self.cap = cap_line()
        limit = float(self.cap["max_usd"]) * STOP_FRACTION
        if self.spent() + estimate > limit + 1e-9:
            raise CapReached(f"DeepSeek: ${self.spent():.3f} spent + ${estimate:.3f} would pass {STOP_FRACTION:.0%} of the "
                             f"${float(self.cap['max_usd']):g} ceiling (config/spend_caps.json deepseek_api); stop and ask the creator")
        if self.job_usd + estimate > self.max_usd + 1e-9:
            raise CapReached(f"job {self.job}: ${self.job_usd:.3f} spent + ${estimate:.3f} would pass its --max-usd ${self.max_usd:g}")

    def _log(self, model: str, served: str, usage: dict, usd: float, uncertain: bool) -> None:
        self.job_usd += usd
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        line = {"ts": self.now().astimezone(UTC).isoformat(), "job": self.job, "model": model, "served": served, "usage": usage,
                "usd": round(usd, 6), "uncertain": uncertain}
        with self.ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")

    # --- one call
    def complete(self, messages: list[dict], *, model: str = "flash", think: bool = True, max_tokens: int | None = None,
                 sink: Path | None = None, json_mode: bool = False) -> str:
        if model not in self.cfg["models"]:
            raise DeepSeekError(f"model {model!r} is not in config/deepseek.json: refused, never guessed")
        lim = self.cfg["limits"]
        max_tokens = min(int(max_tokens or lim["max_output_tokens"]), lim["max_output_tokens"])
        chars = sum(len(m["content"]) for m in messages)
        if chars > lim["max_input_chars"]:
            raise DeepSeekError(f"{chars} input characters pass the limit {lim['max_input_chars']}: send fewer files")
        for i, m in enumerate(messages):
            check_secrets(m["content"], f"message {i}")
        worst = worst_usd(model, chars, max_tokens, self.cfg)
        self.reserve(worst)
        key = self.key or os.environ.get(self.cfg["key_env"])
        if not key:
            raise NotApproved(f"{self.cfg['key_env']} is not set: nothing was sent")
        body: dict[str, Any] = {"model": self.cfg["models"][model]["id"], "messages": messages, "stream": True, "max_tokens": max_tokens,
                                "stream_options": {"include_usage": True}, "thinking": {"type": "enabled" if think else "disabled"}}
        if think:
            body["reasoning_effort"] = "high"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "text/event-stream"}
        text, usage, served, finish, got = [], None, "", None, False
        if sink:
            sink.parent.mkdir(parents=True, exist_ok=True)
            sink.write_text("", encoding="utf-8")
        for attempt in range(4):
            try:
                for line in self.transport(self.cfg["base_url"] + "/chat/completions", headers, body):
                    line = line.strip()
                    if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                        continue                              # keep-alive comments and empty lines
                    ev = json.loads(line[5:])
                    got, served = True, ev.get("model") or served
                    usage = ev.get("usage") or usage
                    for ch in ev.get("choices") or []:
                        finish = ch.get("finish_reason") or finish
                        piece = (ch.get("delta") or {}).get("content")
                        if piece:
                            text.append(piece)
                            if sink:                          # OR-33: the paid answer is on disk as it arrives
                                with sink.open("a", encoding="utf-8") as f:
                                    f.write(piece)
                break
            except urllib.error.HTTPError as e:
                if got or e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    if got:
                        self._log(model, served, {}, worst, True)
                    raise DeepSeekError(f"HTTP {e.code} from DeepSeek") from e
                self.sleep((2, 8, 20)[attempt])
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if got or attempt == 3:
                    if got:
                        self._log(model, served, {}, worst, True)
                    raise StreamBroken(f"the stream broke ({type(e).__name__}); partial answer in {sink}") from e
                self.sleep((2, 8, 20)[attempt])
        if usage is None:                                     # no usage line: charge the worst case, flagged
            self._log(model, served, {}, worst, True)
            raise StreamBroken(f"the answer ended without a usage line; charged the estimate ${worst:.3f}; partial answer in {sink}")
        self._log(model, served, usage, usd_of(model, usage, self.now(), self.cfg), False)
        if finish == "length":
            raise DeepSeekError(f"the answer hit max_tokens {max_tokens}: split the task")
        return "".join(text)


# --- edit blocks -> files
def parse_edits(answer: str) -> list[tuple[str, str, str]]:
    """(path, search, replace) for every block of the answer, in order."""
    out, heads = [], list(HEADER.finditer(answer))
    for i, h in enumerate(heads):
        section = answer[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(answer)]
        out += [(h.group(1).strip("`"), s, r) for s, r in BLOCK.findall(section)]
    return out


def never(path: str, cfg: dict) -> bool:
    return any(path == n or (n.endswith("/") and path.startswith(n)) for n in cfg["never_paths"])


def plan_edits(edits: list[tuple[str, str, str]], root: Path, allowed: set[str], cfg: dict) -> tuple[dict[str, str], list[str]]:
    """The new content of every touched file, and the reasons it may not be written (any reason: nothing is written)."""
    new: dict[str, str] = {}
    errs: list[str] = []
    if not edits:
        return new, ["no edit block found: answer only with '### FILE:' headers and SEARCH/REPLACE blocks"]
    for path, search, replace in edits:
        norm = os.path.normpath(path).replace("\\", "/")
        if os.path.isabs(path) or norm.startswith("..") or never(norm, cfg):
            errs.append(f"{path}: this path may not be edited by the worker")
            continue
        try:
            check_secret_path(norm)
        except EngineError as e:
            errs.append(str(e))
            continue
        target = root / norm
        if not search.strip():
            if target.exists() or norm in new:
                errs.append(f"{norm}: exists already; an empty SEARCH would rewrite the whole file, send blocks instead")
            else:
                new[norm] = replace
            continue
        if norm not in allowed:
            errs.append(f"{norm}: was not sent to you, so it may not be changed")
            continue
        text = new.get(norm, target.read_text(encoding="utf-8") if target.exists() else "")
        if text.count(search) != 1 and text.count(search.rstrip("\n")) == 1:
            search, replace = search.rstrip("\n"), replace.rstrip("\n")
        if text.count(search) != 1:
            errs.append(f"{norm}: a SEARCH part occurs {text.count(search)} times, it must occur exactly once: {search[:80]!r}")
            continue
        new[norm] = text.replace(search, replace)
    for norm, text in new.items():
        old = (root / norm).read_text(encoding="utf-8") if (root / norm).exists() else ""
        if len(old) > 400 and len(text) < len(old) * (1 - cfg["limits"]["max_shrink"]):
            errs.append(f"{norm}: shrinks by more than {cfg['limits']['max_shrink']:.0%}; keep the existing code")
    return new, errs


def unified(root: Path, new: dict[str, str]) -> tuple[str, int, int]:
    parts, plus, minus = [], 0, 0
    for norm, text in sorted(new.items()):
        old = (root / norm).read_text(encoding="utf-8") if (root / norm).exists() else ""
        d = list(difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"a/{norm}" if old else "/dev/null", f"b/{norm}"))
        plus += sum(1 for x in d[2:] if x.startswith("+"))
        minus += sum(1 for x in d[2:] if x.startswith("-"))
        parts.append("".join(x if x.endswith("\n") else x + "\n" for x in d))
    return "".join(parts), plus, minus


def run_test(cmd: str, root: Path, timeout: float) -> tuple[bool, str]:
    try:
        p = subprocess.run(shlex.split(cmd), cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"the test command passed {timeout:.0f} s"
    return p.returncode == 0, (p.stdout + p.stderr)[-4000:]


def pack(files: list[str], root: Path, cfg: dict) -> str:
    parts = []
    for rel in files:
        norm = os.path.normpath(rel).replace("\\", "/")
        check_secret_path(norm)
        parts.append(f"=== FILE: {norm} ===\n{(root / norm).read_text(encoding='utf-8')}\n=== END {norm} ===\n")
    return "\n".join(parts)


def code(w: Worker, brief: str, files: list[str], *, root: Path = ROOT, test: str | None = None, model: str = "flash",
         think: bool = True, rounds: int | None = None, out: Path, test_runner: Callable[..., tuple[bool, str]] = run_test) -> dict:
    """Brief + files -> applied, tested edits and ``out/patch.diff``. A failed job leaves the working tree as it was."""
    cfg = w.cfg
    rounds = min(int(rounds or cfg["limits"]["max_rounds"]), cfg["limits"]["max_rounds"])
    allowed = {os.path.normpath(f).replace("\\", "/") for f in files}
    edit_targets = [f for f in allowed if never(f, cfg)]          # a never-path may be sent as context, never changed
    messages = [{"role": "system", "content": CODE_SYSTEM},
                {"role": "user", "content": pack(files, root, cfg) + "\n=== BRIEF ===\n" + brief}]
    res: dict[str, Any] = {"job": w.job, "status": "FAIL", "rounds": 0, "models": [], "out": str(out)}
    for n in range(1, rounds + 1):
        use = "pro" if (n == rounds and rounds > 1 and model == "flash") else model      # two red rounds on Flash: Pro takes the last
        answer = w.complete(messages, model=use, think=think, sink=out / f"round{n}.md")
        res["rounds"], res["models"] = n, res["models"] + [use]
        new, errs = plan_edits(parse_edits(answer), root, allowed - set(edit_targets), cfg)
        why = "The edits were refused, nothing was written:\n- " + "\n- ".join(errs) if errs else ""
        if not errs:
            diff, plus, minus = unified(root, new)
            before = {p: ((root / p).read_text(encoding="utf-8") if (root / p).exists() else None) for p in new}
            for p, text in new.items():
                (root / p).parent.mkdir(parents=True, exist_ok=True)
                write_text_atomic(root / p, text)
            ok, tail = test_runner(test, root, cfg["limits"]["test_timeout_s"]) if test else (True, "")
            write_text_atomic(out / "patch.diff", diff)
            if ok:
                res.update(status="PASS", files=sorted(new), plus=plus, minus=minus, tested=bool(test))
                break
            for p, text in before.items():                        # a red round leaves no trace in the tree
                (root / p).unlink() if text is None else write_text_atomic(root / p, text)
            write_text_atomic(out / f"round{n}.test.txt", tail)
            why = f"The edits applied but `{test}` failed. Output tail:\n{tail}"
            res["last_failure"] = tail[-300:]
        else:
            res["last_failure"] = "; ".join(errs)[:300]
        messages += [{"role": "assistant", "content": answer},
                     {"role": "user", "content": why + "\n\nSend ALL edit blocks again, corrected, against the ORIGINAL files above."}]
    res["usd"] = round(w.job_usd, 4)
    write_json_atomic(out / "summary.json", res)
    return res


def review(w: Worker, brief: str, diff: str, *, model: str = "pro", out: Path) -> dict:
    diff, hidden = redact(diff)
    answer = w.complete([{"role": "system", "content": REVIEW_SYSTEM},
                         {"role": "user", "content": f"=== BRIEF ===\n{brief}\n=== DIFF ===\n{diff}"}],
                        model=model, max_tokens=8000, sink=out / "review.json", json_mode=True)
    try:
        data = json.loads(answer)
    except ValueError:
        data = {"verdict": "UNREADABLE", "findings": []}
    res = {"job": w.job, "verdict": data.get("verdict"), "findings": (data.get("findings") or [])[:5], "redacted": hidden,
           "usd": round(w.job_usd, 4), "out": str(out)}
    write_json_atomic(out / "review_summary.json", res)
    return res


def text(w: Worker, brief: str, files: list[str], *, root: Path = ROOT, model: str = "flash", think: bool = True, out: Path) -> dict:
    answer = w.complete([{"role": "system", "content": TEXT_SYSTEM},
                         {"role": "user", "content": pack(files, root, w.cfg) + "\n=== BRIEF ===\n" + brief}],
                        model=model, think=think, sink=out)
    return {"job": w.job, "status": "DONE", "chars": len(answer), "usd": round(w.job_usd, 4), "out": str(out)}


def balance(cfg: dict, key: str) -> dict:
    req = urllib.request.Request(cfg["base_url"] + "/user/balance", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.llm.deepseek_api", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("code", "review", "text"):
        p = sub.add_parser(name)
        p.add_argument("--brief", required=True, type=Path)
        p.add_argument("--model", choices=("flash", "pro"), default="pro" if name == "review" else "flash")
        p.add_argument("--max-usd", required=True, type=float, help="the job's own hard limit")
        p.add_argument("--job", default=None)
        p.add_argument("--dry-run", action="store_true", help="print the worst-case estimate, send nothing")
        p.add_argument("--out", required=name == "text", type=Path)
        if name != "review":
            p.add_argument("--files", nargs="*", default=[])
            p.add_argument("--no-think", action="store_true", help="mechanical work: formatting, renames, extraction")
        if name == "code":
            p.add_argument("--test", default=None, help="the command that must pass, e.g. \"python -m pytest -q tests/unit/test_x.py\"")
            p.add_argument("--rounds", type=int, default=None)
        if name == "review":
            p.add_argument("--diff", required=True, type=Path)
    sub.add_parser("spent")
    sub.add_parser("balance")
    a = ap.parse_args(argv)
    cfg = config()
    try:
        if a.cmd == "spent":
            w = Worker(cfg=cfg, cap=cap_line())
            print(json.dumps({"spent_usd": round(w.spent(), 4), "cap": w.cap, "ledger": str(w.ledger), "calls": len(w.entries())}))
            return 0
        if a.cmd == "balance":
            print(json.dumps(balance(cfg, os.environ.get(cfg["key_env"]) or "")))
            return 0
        brief = a.brief.read_text(encoding="utf-8")
        job = a.job or a.brief.stem
        out = a.out or ROOT / "jobs" / "deepseek" / job
        files = getattr(a, "files", [])
        if a.dry_run:
            chars = len(brief) + sum((ROOT / f).stat().st_size for f in files) + (a.diff.stat().st_size if a.cmd == "review" else 0)
            one = worst_usd(a.model, chars, cfg["limits"]["max_output_tokens"], cfg)
            print(json.dumps({"job": job, "model": a.model, "input_chars": chars, "worst_usd_per_round": round(one, 4),
                              "peak_now": is_peak(datetime.datetime.now(UTC), cfg)}))
            return 0
        w = Worker(job=job, max_usd=a.max_usd, cfg=cfg)
        if a.cmd == "code":
            res = code(w, brief, files, test=a.test, model=a.model, think=not a.no_think, rounds=a.rounds, out=out)
        elif a.cmd == "review":
            res = review(w, brief, a.diff.read_text(encoding="utf-8"), model=a.model, out=out)
        else:
            res = text(w, brief, files, model=a.model, think=not a.no_think, out=out)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("status") in ("PASS", "DONE") or res.get("verdict") == "PASS" else 1
    except EngineError as e:
        print(json.dumps({"status": "REFUSED", "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
