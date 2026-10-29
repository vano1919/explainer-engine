# LLM API (Claude API client, P0d)

The one place the pipeline calls Anthropic: `explainer_engine/llm/claude_api.py`. Plan and caps: project files
`blueprint_2026-10-29/CLAUDE_API_PLAN_2026-10-29.md` and its verdict `CLAUDE_API_PLAN_OR24.md` (the OR-24 changes F1-F8 are built in). Money
ceilings live only in `config/spend_caps.json` (`claude_api`, invariant 2); list prices only in `config/llm_prices.json`; model and effort
only in `config/model_routing.json` (P0b, D7).

## What it does

| Part | Rule |
|---|---|
| Key | `ANTHROPIC_API_KEY` from the environment, read by the SDK; never printed, logged or put in a prompt. Absent key = `KeyAbsent`, nothing else is tried. The base URL is pinned to `api.anthropic.com` (`EXPLAINER_ANTHROPIC_BASE_URL` overrides). |
| Approval | A real client is built only when `claude_api.approval.ref` is set in `spend_caps.json` (the recorded word). Tests inject a fake client. |
| Model, effort | By task class from `config/model_routing.json`; a job may narrow inside the class, never leave it. `output_config.effort` is always sent (Opus 5.5 and Haiku 5.5 default to `medium`, not `high`). Fable on the story stages follows the `fable_story_stages.enabled` flag. |
| Never sent | `thinking` (adaptive by default), `budget_tokens`, `temperature`, `top_p`, `top_k`, assistant prefill, forced `tool_choice`. JSON output uses `output_config.format`. |
| Cache of money | An identical request (body + `cache_salt`) is answered from `jobs/llm_cache/<sha256>.json`. The system prefix (stage page, rules) carries `cache_control`; the job text comes last. Cache writes (5 min 1.25x, 1 h 2x) and reads are priced. |
| Ledger | `jobs/llm_ledger/calls.jsonl`: a `start` line before a paid call, a `done` or `void` line after. A start with no result stops the next call (`LedgerGap`). Per-job `Run` ledger (80 % stop) plus the total over all jobs (80 % of `max_usd`). The reservation is the whole prompt as cache writes plus `max_tokens` of output plus every allowed search; it is settled from `usage`. |
| Web search | $10 per 1,000 searches, counted from `usage.server_tool_use.web_search_requests`, not batch-discounted. Dynamic filtering's code execution is not priced separately here. |
| Fallbacks | `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) on direct calls to Fable, Opus and Sonnet; none for Haiku; none on the Batch API. A refused batch item is reported, then re-run once as a direct call; never reworded. A refusal on a direct call raises `Refused`. |
| Fable 400 | A request that declares `fallback_to` (alias, effort) is re-run once on that route and the ledger line says `fell_back_from`. |
| Batch | From 20 requests, no tool loop. State in `jobs/llm_ledger/batch_<job>_<hash>.json`, so a second run collects instead of submitting again. Half price on all tokens. |
| Overload | 429 / 5xx / overloaded: wait with backoff up to 15 minutes in all, then `Overloaded` (stop and report). |
| Secrets | A prompt, job file or tool result that matches a key pattern, or a file named like `tests/unit/test_repo_hygiene.py` guards (or under `tools/`), is refused before the request. |
| Repo tool loop | `tools_root` gives the model `list_dir`, `read_file`, `grep` over a checkout: read-only, inside the root, secret-like paths and content refused. Every turn is reserved and settled on its own. Used by the PR review and the final audit. |

## Commands

```
python -m explainer_engine.llm.claude_api estimate job.json [--expected-output N] [--offline]   # spends nothing
python -m explainer_engine.llm.claude_api run job.json [--out DIR] [--no-wait]
python -m explainer_engine.llm.claude_api status                                               # key present?, caps, totals
python -m explainer_engine.llm.claude_api void UID --usd X                                     # close a call the ledger lost
```

Job file: `{job, task_class, model?, effort?, max_tokens?, system?, system_files?, schema?, web_search_max_uses?, cache_ttl?, tools_root?,
max_turns?, fallback_to?, requests: [{id, user | user_file, cache_salt?}]}`; the `job` must have a line in `claude_api.jobs`.

## What it cannot see

The ledger is the only meter; the promo balance is visible only in the Console. The ledger total is printed with every job. A timed-out
call may have been billed: its start line stays open until it is closed by hand. A call that fell back server-side is priced at the model
named in the response.
