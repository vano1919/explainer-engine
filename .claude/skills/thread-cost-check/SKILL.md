---
name: thread-cost-check
description: Every thread checks its own context for waste after each block of steps (empty steps, big tool results kept, repeated reads, repeated questions) and, when it is expensive, posts the one-line request and writes its handover file. Use in every thread, every N steps (N = steps in config/thread_cost.json), and whenever the CC-1 hook speaks.
---

# Thread cost check (CC-1, OR-38; creator 2026-11-20 14:01, 14:04 and 14:09 UTC)

Every model step re-reads the whole history, so cost = steps x context size. The limits live in ONE place, `config/thread_cost.json` (`context_tokens`, `steps`; a hypothesis, changed only on the creator's word). The hooks in `.claude/settings.json` (UserPromptSubmit and Stop, `explainer_engine/governance/thread_cost.py`) warn and refuse to end a turn; this skill is the thread's own habit between them.

## When
After every `steps` steps (read the number from the config, do not remember it) and whenever the hook text "CC-1" appears. Measure first: `python tools/thread_cost.py` (exit 1 = over a limit; it prints tokens, steps, limits).

## Look for waste (one pass, no long essay)
- empty steps: calls that changed nothing and taught nothing (a re-run without a change, a status poll, a re-read to "verify" an edit that succeeded);
- big tool results still in context (page text, whole files, logs, browser dumps): next time read the needed range, grep, or let a Haiku/script thread summarise it to a file;
- the same file read more than once;
- the same question asked or the same answer re-derived.

## If over a limit, or the waste is large
1. Post ONE short line (at most `max_request_chars`) to the thread, your coordinator or the lead, containing exactly: **I am expensive now: compact me or hand me over**.
2. Write `HANDOVER_<session id>.md` (path from `handover_dirs` in the config) with only the sections `goal`, `state`, `paths`, `open questions`, between `min_handover_bytes` and `max_handover_bytes`. No recap of old chats, no dropped approaches, nothing the next thread does not need.
3. Wait for compaction or a handover; keep doing no extra work. A hook cannot compact a thread; the coordinator or creator does (OR-38).

Routine reading, browsing and uploads go to a Haiku low thread, not to this one. Never edit the limits to get under them.
