---
name: deepseek-worker
description: MANDATORY way of working since 2026-11-21 (creator) - Claude only plans and checks, DeepSeek writes everything else (code, tests, tools, scripts, documents, script drafts, routine edits) through `python -m explainer_engine.llm.deepseek_api`, Gemini Neon checks at two fixed points. Use BEFORE writing or editing any code, test, script, document or draft in any thread, before opening a thread for such work, when choosing DeepSeek Flash or Pro, and when estimating what a task costs.
---

# DeepSeek writes, Claude plans and checks

**The creator's rule (2026-11-21):** quality at the lowest total price. Claude tokens are the expensive part, so a Claude thread
never writes what DeepSeek can write. A thread that is about to type code, a test, a tool, a document or a draft itself stops and
sends a brief instead. The only exceptions are the never-list (section 6) and a task DeepSeek failed on after the full loop.

Facts (prices, model names, peak hours, limits) live in `config/deepseek.json`; the money ceiling is the `deepseek_api` line of
`config/spend_caps.json`; the tool is `explainer_engine/llm/deepseek_api.py`. This page links to them and does not restate limits.

## 1. Who does what

| Step | Who | Cost rule |
|---|---|---|
| Plan a topic, cut it into tasks | Claude (the model the coordinator chose) | one plan per topic, tasks of 1-3 files |
| Check the plan's structure | Gemini Neon, high | ONE prompt per topic, only for a topic of 5+ tasks or a new design |
| Write the brief | Claude | 25 lines at most (section 3) |
| Write code, tests, scripts, documents, drafts | DeepSeek Flash | the default; Pro by section 4 |
| Run the tests, feed failures back | the tool itself | no Claude turn inside the loop |
| Review each diff | DeepSeek Pro (`review`) | automatic, cents; only for a diff over 40 changed lines or a risky area |
| Check the result | Claude | the summary line, the diff stat, the review verdict (section 5) |
| Final check of a finished batch or PR | Gemini Neon, high | ONE bundle per PR, never per task |
| Hard code (tier 3, section 4) | Claude Opus 5.5, medium effort, through the Claude API | never opened by a thread: ask the coordinator for a card first |
| Merge, money, governance | Claude and the creator | never delegated |

Gemini is kept out of the per-task loop on purpose: its chat needs a browser driver (Claude tokens on every prompt) and its quota
is needed for pictures. Neon gets at most the two prompts above per topic; Hydrogen is only the fallback writer when DeepSeek is
down or its ceiling is reached.

## 2. The loop

1. **Brief.** Write `brief.md` (section 3). Choose the files: only what the writer must read or change, 1-3 files, plus the test file.
2. **Estimate** (free): `python -m explainer_engine.llm.deepseek_api code --brief brief.md --files <files> --max-usd 0.50 --dry-run`.
3. **Run:** `python -m explainer_engine.llm.deepseek_api code --brief brief.md --files <files> --test "python -m pytest -q <test file>" --max-usd 0.50`.
   The tool sends the brief and the files, applies the returned edit blocks, runs the test command and sends a failure back, up to
   the round limit; the last round runs on Pro. It prints ONE JSON line: status, rounds, models, files, plus/minus lines, dollars.
4. **Read only that line.** `PASS`: go to section 5. `FAIL`: the working tree is untouched; read `last_failure`, narrow or split the
   brief ONCE and run again. A second `FAIL`: Claude does the task itself and notes it in the progress fragment.
5. **Review** when section 1 asks for it: `... deepseek_api review --brief brief.md --diff jobs/deepseek/<job>/patch.diff --max-usd 0.20`.
   `FIX` findings go back as a new brief (the finding text is the brief); never fix them by hand unless it is one line.
6. **Commit** on the work branch, with the test. Text work (documents, script drafts, reports, data clean-up) uses
   `... deepseek_api text --brief brief.md --files <material> --out <file> --max-usd 0.30` and the same checks.

Never paste the model's raw answer, a whole diff or a long test log into the thread: they stay in `jobs/deepseek/<job>/`.

## 3. The brief (25 lines at most)

```
GOAL: one sentence, the behaviour that must exist afterwards.
CHANGE: file -> what changes in it (function names, signatures).
NEW FILES: path -> purpose (tests included; say which cases the test covers).
MUST KEEP: the callers, formats and rules that may not change.
DONE WHEN: the exact test command passes.
NOT IN SCOPE: what the writer must not touch.
```

No history, no reasons, no pasted code: the files carry the code. One task = one behaviour. A task that needs more than 3 files to
be read, or more than about 150 changed lines, is cut in two before it is sent.

## 4. The three tiers, then Flash or Pro

**The three tiers (creator, 2026-11-21, confirmed on a card).** Claude threads stay minimal: a thread plans and checks, and writes only the never-list.
1. **Simple = DeepSeek V4.1 Flash** (`deepseek-flash`): the default for everything below.
2. **Medium = DeepSeek Pro** (`deepseek-v4-pro`, the regular Pro): the four Pro cases below.
3. **Hard = Claude Opus 5.5 at medium effort** (`claude-opus-5-5`), sent through the Claude API (`explainer_engine/llm/claude_api.py`, the
   Console credit), never through an app thread. Hard means: the code and test design of a new method, a new module boundary or schema,
   logic across more than 3 modules, or two red Pro rounds on the same task. A thread never opens this tier itself: it asks the
   coordinator for a card (the coordinator passes the brief and the money line), and the first paid Opus call waits for the owner's card.

### Flash or Pro (tiers 1 and 2)

**Flash is the default** (thinking on). Use it for: code from a clear brief, tests, tools and one-off scripts, fixtures, documents,
reports, data clean-up, routine edits, and anything with a picture input (only Flash reads pictures).
**Flash with `--no-think`:** mechanical work where nothing is decided: formatting, renames, moving text, extraction, tables.

**Pro only when one of these is true:**
1. Flash came back red twice on the same task (the tool does this by itself in its last round).
2. The task designs something new: a new algorithm, a new module boundary, a schema, or logic spread over more than 3 modules.
3. It is a review of a Flash diff (`review` uses Pro by default: a second model sees what the first one missed).
4. The text is what the viewer hears or reads, or a long structured piece where the first draft's quality saves rounds: a scenario
   variant, a script draft, a research synthesis.

Pro costs about four times Flash, so "it might be hard" is not a reason. Start with `--model pro` only for points 2-4.

## 5. What Claude checks, cheaply

- The summary line: `PASS`, `tested: true`, the file list is the one the brief named, the line counts are plausible.
- `git diff --stat`, then only the hunks of the risky part, never the whole diff of a routine task.
- The review verdict when one was run. A `high` finding blocks the commit.
- The focused test passed in the loop; do not run it again unless a file changed afterwards.
- For a draft or a document: the first and the last paragraph and one in the middle against the brief; a script still passes the
  repository's own gates (`scripting/story_lint.py`, the creator's approval) exactly as before.

## 6. Never sent to DeepSeek

- Secrets, keys, tokens, `.env`, `tools/` (the tool refuses them; do not work around it).
- Edits of governance, hooks, money and paid code: the `never_paths` of `config/deepseek.json`. Claude writes those itself.
- Merges, pod plans, spending decisions, the creator's approvals.
- A decision that is the creator's (rule one, OR-22): DeepSeek writes variants, the creator chooses.

## 7. Money

- A real call needs the `deepseek_api` line in `config/spend_caps.json` (the creator's word) and the key in the environment
  variable named in `config/deepseek.json`; without them the tool refuses and prints why.
- Every job has its own `--max-usd`; the tool refuses past it and past 80 % of the ceiling. The answer is written to a file as it
  streams and every call is one ledger line (`... deepseek_api spent`; the account itself: `... deepseek_api balance`).
- Prices are half outside the peak hours of `config/deepseek.json`. Work that can wait (batches, documents, drafts) runs off-peak.
- The Opus tier (3) has its own ceiling line in `config/spend_caps.json` and is not live until the creator names it.
- Ask DeepSeek once per task, not three variants "to compare": the test and the review are the quality gate.
- Measured numbers of this way of working go into the progress fragment after every batch: tasks, rounds, PASS share, dollars,
  Claude turns per task. Until the first five real tasks are measured, the cost table of the plan is an estimate.
