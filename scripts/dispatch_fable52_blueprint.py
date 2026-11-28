"""Dispatch the adversarial review + 2-hour execution-plan prompt to Claude Fable 5.2 (creator request 2026-11-28).

One paid Claude API run, capped in dollars, that packages a clean code packet from a git ref (no checkout needed:
every file is read with ``git show <ref>:<path>``), sends it with the master mega-prompt to ``claude-fable-5-2`` with
adaptive thinking at high effort and the server-side web search tool, streams the answer to a ``.partial`` file as it
arrives (OR-33), resumes ``pause_turn`` while the cap allows, and writes the blueprint plus a usage record.

    python scripts/dispatch_fable52_blueprint.py --ref <ref> --dry-run      # free: packet, token count, model check
    python scripts/dispatch_fable52_blueprint.py --ref <ref> --live         # paid, refuses above --max-usd
    python scripts/dispatch_fable52_blueprint.py --check docs/CLAUDE_FABLE_52_MEGA_BLUEPRINT_FOR_GEMINI.md

The key is read from ANTHROPIC_API_KEY (or EE_ANTHROPIC_API_KEY) and is never printed.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL = "claude-fable-5-2"
# Claude Fable 5.2 list prices (USD per token), checked 2026-11-28 against the Claude API skill's model table.
PRICE_IN = 8.00 / 1e6
PRICE_CACHE_WRITE = 10.00 / 1e6     # 5-minute cache write = 1.25 x input
PRICE_CACHE_READ = 0.20 / 1e6
PRICE_OUT = 40.00 / 1e6             # output + thinking
PRICE_SEARCH = 10.00 / 1000         # web search, per request
MAX_PACKET_TOKENS = 140_000

CORE_FILES = [
    "explainer_engine/cloud/modal_comfy_deploy.py",
    "explainer_engine/cloud/modal_cinema_studio.py",
    "explainer_engine/cloud/hybrid_api_clients.py",
    "explainer_engine/cloud/modal_ltx_governed.py",
    "explainer_engine/core/spend_ledger.py",
    "explainer_engine/videolane/hybrid_escalation_router.py",
    "explainer_engine/videolane/lipsync_pipeline.py",
    "explainer_engine/videolane/ltx_loop.py",
    "explainer_engine/videolane/multishot_scene_director.py",
    "explainer_engine/videolane/plan.py",
    "explainer_engine/studio/contact_sheet_slicer.py",
    "explainer_engine/studio/scenebuilder.py",
    "explainer_engine/edit/otio_exporter.py",
    "explainer_engine/episode/mvp_drama_poc.py",
    "explainer_engine/episode/word_timeline_compiler.py",
    "explainer_engine/cli/stack2_runner.py",
    "explainer_engine/audio/broadcast_cinema_mix.py",
    "explainer_engine/qa/cinema_gates.py",
    "tests/unit/test_v6_modal_studio_stack2.py",
    "tests/unit/test_v6_stack2_full_launchers.py",
    "tests/unit/test_v5_loop5_acting_lipsync_hardening.py",
]
# Named by the mega-prompt (Part 3.7, Section 5); added only while the packet stays under MAX_PACKET_TOKENS.
EXTRA_FILES = ["explainer_engine/qa/identity_lock.py", "explainer_engine/imagegen/turn_pack.py"]
# Files that may be cut to their key functions when the packet is too large (everything else stays verbatim).
CINEMA_GATES = "explainer_engine/qa/cinema_gates.py"
GATE_KEYWORDS = ("mouth", "acting", "freeze", "dialogue", "lip", "dramatic", "seventy", "70", "narrator_share",
                 "share", "speech")
MIX_FILE = "explainer_engine/audio/broadcast_cinema_mix.py"

BOOTSTRAP_IDS = ["1VfDq2uODqMTHhYwjEfjtvuE2RXewz9M9", "1M99oAMs4xvEEKU24uHhuYmeFjToCQYxa",
                 "1lfj-uqJ0eiLsmWCYN9EsYGUp50pgGpE0"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def git_show(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def numbered(text: str, start: int = 1) -> str:
    return "\n".join(f"{i:5d}| {line}" for i, line in enumerate(text.splitlines(), start))


def tree(ref: str, root: str, depth: int = 3) -> str:
    paths = git("ls-tree", "-r", "--name-only", ref, root).splitlines()
    keep = set()
    for p in paths:
        if "__pycache__" in p:
            continue
        parts = p.split("/")
        keep.add("/".join(parts[: depth + 1]) + ("/" if len(parts) > depth + 1 else ""))
    return "\n".join(sorted(keep))


def key_sections(text: str, keywords: tuple[str, ...]) -> str:
    """Top-level functions/classes whose name has a keyword, verbatim with their real line numbers."""
    lines = text.splitlines()
    tree_ = ast.parse(text)
    head_end = next((n.lineno - 1 for n in tree_.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))), 60)
    out = [f"# [excerpt] module header, lines 1-{head_end}", numbered("\n".join(lines[:head_end]))]
    for node in tree_.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and any(
                k in node.name.lower() for k in keywords):
            start = node.lineno - len(node.decorator_list)
            seg = "\n".join(lines[start - 1: node.end_lineno])
            out.append(f"# [excerpt] {node.name}, lines {start}-{node.end_lineno}")
            out.append(numbered(seg, start))
    names = [n.name for n in tree_.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    out.append("# [index] every top-level name in the module: " + ", ".join(names))
    return "\n".join(out)


def build_packet(ref: str) -> tuple[str, dict]:
    sha = git("rev-parse", "--short=8", ref).strip()
    info: dict = {"ref": ref, "commit": sha, "files": {}, "missing": [], "excerpted": []}
    blocks = [f'<repository_metadata ref="{ref}" commit="{sha}">',
              "## git log --oneline -n 20", git("log", "--oneline", "-n", "20", ref).strip(),
              "## tree explainer_engine/ (depth 3)", tree(ref, "explainer_engine"),
              "## tree tests/unit/ (depth 3)", tree(ref, "tests/unit")]
    for cfg in ("pyproject.toml", "requirements.txt"):
        txt = git_show(ref, cfg)
        if txt is not None:
            blocks += [f"## {cfg}", txt.strip()]
    blocks.append("</repository_metadata>")
    meta = "\n".join(blocks)

    texts: dict[str, str] = {}
    for path in CORE_FILES:
        txt = git_show(ref, path)
        if txt is None:
            info["missing"].append(path)
        else:
            texts[path] = txt

    def render(path: str, txt: str, excerpt: bool) -> str:
        n = len(txt.splitlines())
        if excerpt:
            kws = GATE_KEYWORDS if path == CINEMA_GATES else ("mix", "loud", "lufs", "duck", "stem", "jl", "cut")
            body, kind = key_sections(txt, kws), "key sections (verbatim, real line numbers)"
        else:
            body, kind = numbered(txt), "full, verbatim"
        return f'<file path="{path}" lines="{n}" content="{kind}">\n{body}\n</file>'

    excerpt = set()
    rendered = {p: render(p, t, False) for p, t in texts.items()}

    def total() -> int:
        return (len(meta) + sum(len(v) for v in rendered.values())) // 4

    for path in (CINEMA_GATES, MIX_FILE):          # the only files the brief allows to shorten
        if total() > MAX_PACKET_TOKENS and path in texts:
            rendered[path] = render(path, texts[path], True)
            excerpt.add(path)
    for path in EXTRA_FILES:
        txt = git_show(ref, path)
        if txt is not None:
            cand = render(path, txt, False)
            if total() + len(cand) // 4 <= MAX_PACKET_TOKENS:
                rendered[path] = cand
    info["excerpted"] = sorted(excerpt)
    info["files"] = sorted(rendered)
    missing_note = ""
    if info["missing"]:
        missing_note = ("<missing_files note=\"named in the brief but absent at this commit\">\n"
                        + "\n".join(info["missing"]) + "\n</missing_files>\n")
    packet = (f'<codebase_context ref="{ref}" commit="{sha}">\n{meta}\n{missing_note}'
              + "\n".join(rendered.values()) + "\n</codebase_context>")
    info["est_tokens"] = len(packet) // 4
    return packet, info


SYSTEM = """You are the Principal Adversarial Systems Auditor and Execution-Plan Author described in the master prompt.
The full source of the repository files you must audit is in <codebase_context>, with real line numbers (cite them as
path:line). You cannot reach the private repository or Google Drive; the packet is the code. Use the web search tool for
the live verification the master prompt demands (GitHub source of ComfyUI and custom nodes, Hugging Face repos, vendor
API docs) and mark every fact you could not open yourself as "Requires live credential test" or "Unverified".
You write no code changes yourself; your one deliverable is the self-contained Markdown mega-blueprint for a new Gemini
chat. Start it with the REPOSITORY & GOOGLE DRIVE BOOTSTRAP BLOCK copied verbatim, then Sections 1-5 exactly as Part 5
orders, each under a level-2 heading that begins "## Section N". Finish the whole document; if space runs short,
shorten prose, never drop a section. Leave the final line exactly "<!-- API_RUN_USAGE -->" so the dispatcher can append
the token count and cost of this run."""


def usage_cost(u) -> dict:
    inp = getattr(u, "input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    out = getattr(u, "output_tokens", 0) or 0
    stu = getattr(u, "server_tool_use", None)
    ws = (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
    usd = inp * PRICE_IN + cw * PRICE_CACHE_WRITE + cr * PRICE_CACHE_READ + out * PRICE_OUT + ws * PRICE_SEARCH
    return {"input": inp, "cache_write": cw, "cache_read": cr, "output_and_thinking": out, "web_searches": ws,
            "usd": round(usd, 4)}


def client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EE_ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY (or EE_ANTHROPIC_API_KEY) is not set")
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", max_retries=2, timeout=3600)


def request_params(prompt: str, packet: str, args) -> dict:
    return {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "system": SYSTEM,
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": args.effort},
        "tools": [{"type": "web_search_20260209", "name": "web_search", "max_uses": args.max_searches}],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "<master_prompt>\n" + prompt + "\n</master_prompt>"},
            {"type": "text", "text": packet, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "Begin the adversarial inspection and live verification now, then write the "
                                     "complete mega-blueprint."},
        ]}],
    }


def worst_case_usd(in_tokens: int, args, cached: bool) -> float:
    # One request: input (cache write first time, cache read after) + the extra search context the server adds
    # (bounded at 8k tokens per search) + every output token + every search.
    inp = in_tokens * (PRICE_CACHE_READ if cached else PRICE_CACHE_WRITE)
    return inp + args.max_searches * (8000 * PRICE_IN + PRICE_SEARCH) + args.max_tokens * PRICE_OUT


def live(args, prompt: str, packet: str, info: dict) -> int:
    c = client()
    params = request_params(prompt, packet, args)
    out = Path(args.out)
    partial = out.with_suffix(out.suffix + ".partial")
    out.parent.mkdir(parents=True, exist_ok=True)
    in_tokens = c.messages.count_tokens(**{k: v for k, v in params.items()
                                           if k in ("model", "system", "messages", "tools", "thinking")}).input_tokens
    first = worst_case_usd(in_tokens, args, cached=False)
    print(f"exact input tokens (count_tokens): {in_tokens:,}; worst case of request 1: ${first:.2f}; "
          f"cap ${args.max_usd:.2f}")
    if first > args.max_usd:
        print("REFUSED: the first request's worst case is above the cap")
        return 2
    spent, runs, texts, stop = 0.0, [], [], None
    t0 = time.time()
    with partial.open("w", encoding="utf-8") as fp:
        for turn in range(args.max_continuations + 1):
            print(f"\n=== request {turn + 1} ===", flush=True)
            last_beat = time.time()
            with c.messages.stream(**params) as stream:
                for ev in stream:
                    et = getattr(ev, "type", "")
                    if et == "content_block_start":
                        b = ev.content_block
                        if b.type == "server_tool_use":
                            print(f"\n[web_search] {json.dumps(getattr(b, 'input', {}) or {})[:160]}", flush=True)
                        elif b.type == "thinking":
                            print("\n[thinking]", flush=True)
                    elif et == "content_block_delta":
                        d = ev.delta
                        if d.type == "text_delta":
                            fp.write(d.text)
                            fp.flush()
                            sys.stdout.write(d.text)
                            sys.stdout.flush()
                        elif d.type == "thinking_delta" and d.thinking:
                            sys.stdout.write(d.thinking)
                            sys.stdout.flush()
                    if time.time() - last_beat > 60:
                        print(f"\n[alive {int(time.time() - t0)} s]", flush=True)
                        last_beat = time.time()
                msg = stream.get_final_message()
            u = usage_cost(msg.usage)
            spent += u["usd"]
            runs.append({"request": turn + 1, "stop_reason": msg.stop_reason, **u})
            texts += [b.text for b in msg.content if b.type == "text"]
            stop = msg.stop_reason
            print(f"\n--- request {turn + 1}: stop={stop} usage={u} total=${spent:.4f}", flush=True)
            if stop != "pause_turn":
                break
            if spent + worst_case_usd(in_tokens, args, cached=True) > args.max_usd:
                print("STOPPED: another continuation could pass the cap")
                break
            params["messages"] = params["messages"][:1] + [{"role": "assistant", "content": msg.content}]
    tot = {k: sum(r[k] for r in runs) for k in ("input", "cache_write", "cache_read", "output_and_thinking",
                                                 "web_searches")}
    tot["usd"] = round(spent, 4)
    record = {"model": args.model, "effort": args.effort, "ref": info["ref"], "commit": info["commit"],
              "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "wall_seconds": round(time.time() - t0), "final_stop_reason": stop, "requests": runs, "total": tot,
              "prices_usd_per_mtok": {"input": 8, "cache_write": 10, "cache_read": 0.2, "output": 40},
              "web_search_usd_each": PRICE_SEARCH, "packet": info}
    body = "".join(texts).rstrip()
    footer = (f"\n\n---\n## API run usage (appended by the dispatcher)\n\n"
              f"- Model `{args.model}`, effort `{args.effort}`, adaptive thinking, web search; code at commit "
              f"`{info['commit']}`; final stop reason `{stop}`; {len(runs)} request(s), {record['wall_seconds']} s.\n"
              f"- Input tokens {tot['input']:,}; cache write {tot['cache_write']:,}; cache read {tot['cache_read']:,}; "
              f"output + thinking {tot['output_and_thinking']:,}; web searches {tot['web_searches']}.\n"
              f"- Cost **${tot['usd']:.4f}** at $8 / $10 cache write / $0.20 cache read / $40 per MTok and $0.01 per "
              f"search (cap ${args.max_usd:.2f}).\n")
    body = body.replace("<!-- API_RUN_USAGE -->", "").rstrip() + footer
    out.write_text(body, encoding="utf-8")
    out.with_suffix(".usage.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"\nSaved {out} ({len(body):,} chars) and {out.with_suffix('.usage.json')}")
    print(json.dumps(tot, indent=2))
    return 0 if stop == "end_turn" else 1


def check(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    head = text[:6000]
    rows = [("bootstrap block at the top", "BOOTSTRAP" in head.upper() and all(i in head for i in BOOTSTRAP_IDS))]
    for n in range(1, 6):
        rows.append((f"Section {n} heading", f"## Section {n}" in text or f"# Section {n}" in text))
    rows.append(("file:line references in Section 1", text.count(".py:") >= 20))
    rows.append(("usage footer with USD", "API run usage" in text and "$" in text.split("API run usage")[-1]))
    usage = Path(path).with_suffix(".usage.json")
    stop = json.loads(usage.read_text())["final_stop_reason"] if usage.exists() else "unknown"
    rows.append(("not truncated (final stop end_turn)", stop == "end_turn"))
    for name, ok in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in rows) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--prompt-file", default=str(REPO / "docs/prompts/CLAUDE_ADVERSARIAL_REVIEW_AND_2H_EXECUTION_PLAN_PROMPT.md"))
    ap.add_argument("--out", default=str(REPO / "docs/CLAUDE_FABLE_52_MEGA_BLUEPRINT_FOR_GEMINI.md"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--max-searches", type=int, default=25)
    ap.add_argument("--max-continuations", type=int, default=4)
    ap.add_argument("--max-usd", type=float, default=20.0)
    ap.add_argument("--allow-missing", action="store_true", help="run live although brief files are absent")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--check", metavar="BLUEPRINT")
    args = ap.parse_args()
    if args.check:
        return check(args.check)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    packet, info = build_packet(args.ref)
    print(f"ref {info['ref']} = {info['commit']}; files in packet {len(info['files'])}; "
          f"missing {len(info['missing'])}; excerpted {info['excerpted']}")
    for m in info["missing"]:
        print(f"  MISSING {m}")
    print(f"estimated packet tokens (len//4): {info['est_tokens']:,}; prompt ~{len(prompt) // 4:,}")
    if args.dry_run:
        c = client()
        m = c.models.retrieve(args.model)
        print(f"model {m.id}: max_input {getattr(m, 'max_input_tokens', '?')}, max_output {getattr(m, 'max_tokens', '?')}")
        params = request_params(prompt, packet, args)
        n = c.messages.count_tokens(**{k: v for k, v in params.items()
                                       if k in ("model", "system", "messages", "tools", "thinking")}).input_tokens
        print(f"exact input tokens (count_tokens, free): {n:,}; worst case of request 1: "
              f"${worst_case_usd(n, args, cached=False):.2f} (cap ${args.max_usd:.2f})")
        return 0
    if info["missing"] and not args.allow_missing:
        print("REFUSED: brief files are missing at this ref (push the right commit or pass --allow-missing)")
        return 2
    return live(args, prompt, packet, info)


if __name__ == "__main__":
    sys.exit(main())
