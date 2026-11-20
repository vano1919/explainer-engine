---
name: gemini-coding
description: The default way of writing code in this project, for every thread and every topic - Gemini (Hydrogen) writes through Google Drive, Claude plans, gives tasks and checks, and the code comes back to GitHub safely. Covers which tasks go to Gemini, how the task, tests and context are packed, how its answer is taken in, checked and merged. Use whenever any thread is about to write or change code, whenever the creator says "move it to Gemini", and whenever a Gemini answer arrives on Drive.
---

# Gemini coding lane: the general way we write code (creator 2026-11-20, 13:09, 13:15 and 13:21 UTC)

**The creator's rule:** use Gemini as much as possible for writing code; Claude plans and checks it. This is the **general working method** of the project. It is not tied to one change, team or topic: episodes, pipeline stages, tools, the rebuild, fixes, everything.

**Roles in any thread or team:**
| role | who | does |
|---|---|---|
| planner | the highest Claude thread present (Opus) | cuts the work into Gemini-sized tasks, decides what stays Claude's |
| task giver | the thread that owns the work (team lead, or the working thread itself when alone) | writes TASK.md, uploads the packet, collects the answer |
| writer | Gemini Hydrogen (Code mode), one new chat per task | writes code, tests (separate chat), docs |
| checker | Sonnet high (tester thread, or a Sonnet subagent when alone) | intake, tests, mutation spot-check, requirement check |
| driver | a cheap browser routine (Haiku/Sonnet), or the creator | moves files between Drive and the Gemini chat |

**Model choice (creator 2026-11-20, 13:26 UTC):**
- **Hydrogen** writes every task by default.
- **Neon** is used **only for especially hard code**, such as a new algorithm, tricky numerical or geometry work, or a task Hydrogen failed twice. The planner marks the task `model: neon` in TASK.md and gives the reason.
- No other Gemini model writes code.

**When a thread works alone** (no team), it takes the planner and task giver roles itself. It gives the check to a Sonnet subagent and the Gemini driving to a Haiku subagent. Writing the code itself is still the exception (section 2).

**Stores:**
- **GitHub (`vano1919/explainer-engine`)** is the main repository. It is the only truth, and every merge lands there.
- **Drive (`Explainer_Engine_V4_Main/gemini_dev`, folder id `1X0vnWugfJ4oUcRLqib3Hx6d9UreJwnwN`)** is the intermediate repository. Gemini reads and writes only there. It cannot see GitHub, cannot run code and cannot see later commits.

## 1. What goes to Gemini (default: everything not listed in section 2)
- New modules with a clear interface: effect renderers, validators, map and chart scripts, Blender `bpy` scripts, converters, report builders, CLI wrappers.
- Changes to existing non-governance modules, as hunks only (section 4).
- Tests: a **separate** Gemini chat writes them from the requirement ids, never the same chat that writes the code. The tester checks every test against the requirement before Gemini sees the code task.
- Docs drafts, PROGRESS entries, skill text, fixtures and sample data.
- A second-opinion review of Claude's code, as information only.

## 2. What never goes to Gemini (Claude writes, Sonnet high reviews)
- Governance and enforcement:
  - `explainer_engine/governance/`;
  - hooks and `.claude/settings.json`;
  - CI workflows;
  - the owner-requirements registry and its checks;
  - `qa/send_validators.py` thresholds.
- Money:
  - `config/spend_caps.json`;
  - `core/ledger.py`;
  - paid launchers (Modal, RunPod, ElevenLabs, Gemini API);
  - anything that bills (OR-34).
- Secrets and auth, and anything that needs a key to run.
- The lane's own tools: `tools/gemini_pack.py` and `tools/gemini_intake.py`.
- Merges, pushes and branch protection.
- A task where Gemini came back red twice.

## 3. Task packet (Drive `gemini_dev/<task-id>/in/`)
1. **`TASK.md`, written by the lead from the plan thread's cut.** It contains:
   - goal in two lines;
   - the requirement ids (OR-V.., LP-.., BP-..) it must meet;
   - the exact paths to create, and the exact paths it may change;
   - function signatures with types;
   - the inputs and outputs, with one example;
   - what it must NOT touch;
   - the pinned base commit sha;
   - the answer format (section 4).
2. **Tests: `tests/unit/test_<task>.py`.** They are written first and checked by the tester. They are the acceptance contract.
3. **`CONTEXT_<task>.md`, made by `tools/gemini_pack.py <task-dir>`.** The task folder holds `TASK.md` and `task.json` (`gemini_task/1`: task, base_sha, team_branch, and the path lists `create`, `change`, `read`, `tests`, `suites`). The tool reads only from the pinned commit (`git show <sha>:<path>`, never the working tree) and writes `in/` with `TASK.md` (placeholder sha filled), the context with a path and sha256 per file, the tests, `task.json` and `PACK.json`. It refuses (exit 2, nothing written) the never-list of section 2 (`.env`, secrets, `config/spend_caps.json`, governance, hooks, settings, CI, the registry, the lane tools, paid launchers), a file missing at the pinned commit, a `create` file that already exists, symlinks, binary files, secret patterns in any file, and anything over 3 MB. Same commit, same bytes.
4. **Size:** keep a packet under about 3 MB per file (the Drive limit). Upload it as files, never paste into the chat (pastes are cut at about 16k characters).

## 4. Gemini's answer (Drive `gemini_dev/<task-id>/out/`)
- `MANIFEST.json`: `{base_sha, files: [{path, kind: "new"|"patch", sha256}]}`.
- New files are written in full.
- Existing files come back **only as unified-diff hunks** against `base_sha`, never as whole files.
- `NOTES.md` covers what it assumed and what it did not do.

**Fixed instruction for the Gemini chat** (Code mode, model Hydrogen; one new chat per task):

> "Read TASK.md, CONTEXT and the tests. Write code that passes the tests. New files: full content. Existing files: unified diff hunks against base_sha only. Do not touch any path not listed in TASK.md. Do not shorten or stub existing code. Return MANIFEST.json, the files and NOTES.md to the out folder."

## 5. Intake (developer thread, `python tools/gemini_intake.py <task-dir>`)
**Refuse, with the reason written to `out/INTAKE.json` (exit 2, the repo is not touched; the code names are the tool's):**
- a path not in TASK.md (`outside_task_list`; also a diff that names another path);
- a whole-file body for an existing file (`whole_file_rewrite`; a patch for a missing file is `patch_of_missing`);
- a hunk that does not apply to `base_sha` (`hunk_does_not_apply`);
- an existing file that shrinks by more than 30 % (`shrinks`) or loses a public function or method (`loses_public_function`);
- any path on the never-list (section 2) (`never_list`);
- edited or deleted tests (`edited_test`, `deleted`);
- a sha mismatch with MANIFEST (`sha_mismatch`, `base_sha_mismatch`);
- also: an unsafe or duplicate path, a bad kind, an unlisted or missing file, a secret pattern, code that does not compile.

**If accepted:**
1. Apply it on branch `claude/<team-branch>-gemini-<task-id>` (a throw-away worktree: the working tree and the team branch are not touched).
2. Run the task tests and the affected suites (`suites` in task.json); a red run is reported as `accepted_red`, never hidden.
3. Write `out/PR_BODY.md` (MANIFEST rows and metrics). The tool has no GitHub access: the thread pushes the branch (`--push`) and opens the DRAFT PR against the team branch with the GitHub MCP tool.

## 6. Check (Sonnet high, tester thread)
- Read the whole diff.
- Run the validators of the layer.
- Do a mutation spot-check: break 3 lines and confirm a test fails.
- Confirm no test or threshold was weakened (invariant 10).
- Confirm the requirement ids are really met, not only the tests.

**Outcomes:**
- **Green:** the lead merges into the team branch. The GitHub default branch still needs the creator's word.
- **Red:** the failing output and the reviewer's notes go to `gemini_dev/<task-id>/round2/in/`, once.
- **Second red:** Claude writes it, and the cause is recorded.

## 7. Keeping Drive current
After every merge on the team branch, write a text snapshot of the changed files (and of the files the next tasks will read) to `gemini_dev/snapshots/<sha>/`. Write the current sha to `gemini_dev/HEAD.txt`. The next packet pins that sha.

## 8. Metrics (each task, in `gemini_dev/METRICS.md`)
Record per task:
- Gemini rounds and minutes;
- intake result;
- tests passed on the first try;
- reviewer findings;
- Claude-side work (task, tests, intake, review);
- a rough count of the Claude tokens saved against writing it ourselves.

After every 5 tasks, the plan thread reports the share of the code written by Gemini, and whether to widen or narrow section 1.

## 9. Lessons that made these rules (do not repeat)
- **2026-11-07, PR #154/#155:** whole files from an older base would have reverted newer docs and rules. 40 KB modules came back as 0.9 KB stubs. Rule ids collided. This is why section 4 allows hunks only, and section 5 refuses shrinks.
- **2026-11-19:** a Gemini baseline lived only on Drive and was pushed by hand. This is why section 7 keeps the snapshot and HEAD.txt current.
