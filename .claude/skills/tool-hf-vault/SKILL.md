---
name: tool-hf-vault
description: Keep every output of this channel safe in the owner's private Hugging Face dataset vano1919/tmr-artifacts - upload as each file arrives, verify each file's sha256 (or git blob id) on Hugging Face before a machine is released or a result is called saved, record pictures and clips in the asset vault, never delete or overwrite, and keep the token in the environment, never printed. Use when a run, a batch, a render or a test produces files, before stopping any paid compute, when a file must be restored, and when someone says "saved" or "uploaded".
---

# Hugging Face vault, the tool (cross-layer: G5, G7, every paid run)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for D-73's vault and OR-33's rule
that paid outputs are saved as they arrive. Money and run planning are skill `modal-operations` and skill
`cloud-cost-audit`; this page is only about getting bytes to the vault and proving they are there.

## When to use, when not

- Use for every file worth keeping: Gemini originals and masters, clips, layout pictures, test sets, stems, masters,
  reports, pod or worker code, and the plan files of a paid run.
- Use before releasing compute: a Modal container, a pod, a long local job. A run is not done until its outputs are on
  HF with matching hashes (rule 8 of `.claude/rules/cloud-platforms.md`).
- Not for secrets (VT-05): HF tokens, YouTube tokens, API keys never enter the vault, a prompt, a log or git.
- Not a scratch disk: Modal Volumes, session scratchpads and project files are working space, never the only copy.

## Where things live

| Copy | What |
|---|---|
| Primary: private HF dataset `vano1919/tmr-artifacts` (`config/vault.json` `primary`) | everything we made |
| Pinned day: HF tag `vault-<date>` | the primary as it was (VT-04) |
| Second copy: the owner's own disk (`vault pull`) | the critical globs of `config/vault.json` |
| Asset records: `episodes/<ep>/assets/asset_records.jsonl` (committed) | one line per original picture, clip or take |

Rules VT-01..VT-05 in [docs/VAULT.md](../../../docs/VAULT.md).

## Our tools (read before citing)

| Job | Code | CLI |
|---|---|---|
| Is a local folder fully on HF, same hashes? | `explainer_engine/vault.py` (`check_uploaded`; LFS files by sha256, small files by git blob id; exit 1 on any miss) | `python -m explainer_engine.vault check-uploaded <dir> --to <prefix>` |
| Snapshot, verify, second copy | `explainer_engine/vault.py` | `python -m explainer_engine.vault snapshot|verify|pull` |
| Push a folder with a sha256 sidecar; refuse damaged files | `explainer_engine/cloud/store.py` | `python -m explainer_engine.cloud.store push|verify <local> <repo_path>` |
| Record an original, read-only, versioned by parent | `explainer_engine/imagegen/vault.py` | `python -m explainer_engine.imagegen.vault ingest|list|verify [--hf]` |
| Paid worker uploads as it goes, then checks | `verify_uploads` in `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` (D-132) | runs inside the worker |

The official `hf` command line (huggingface/skills, page `hf-cli`) is fine for a one-off upload or download of files we
then verify with our own check. Read `hf upload --help` on the installed version first: the current official page names the
repo type flag `--type`, while older releases and our VAULT.md use `--repo-type`.

## The procedure

1. **Name the prefix before the run**: `<project>/<topic>_<date>/<run or batch>/`, e.g.
   `explainer-engine/demo_truce_1914/blocking_2026-11-19/`. A new version gets a new name; never reuse a path (VT-03).
2. **Upload as files arrive** (OR-33): a worker or job flushes each output as soon as it is written, with retries and
   backoff; the local or Volume copy is the safety net, not the record.
3. **Verify on HF**: `python -m explainer_engine.vault check-uploaded <local dir> --to <prefix>` (or `cloud.store verify`).
   Exit 0 is the only proof. Never mute it (VT-02); a failure leaves the machine as it is and someone reads the log.
4. **Record assets**: pictures and clips go through `imagegen.vault ingest` with the episode, shot, kind, provider,
   model and prompt; the same bytes again return the existing record. `verify --ep <ep> --hf` checks the HF copies.
5. **Only then release compute** and write the report: HF paths, sha256 per file, what was verified, what was not.
6. **After an approved episode or set**: `vault snapshot`, a `vault-<date>` tag, and tell the owner how large the second
   copy's update is (VT-04).

## Tokens

- Read from the environment only: `HF_TOKEN` (or `HUGGING_FACE_HUB_TOKEN`) in the session, a Modal Secret inside a worker.
  Never pass a token as a command argument, never `echo` it, never write it to a file in the repo or the vault.
- A read-only look at the dataset may use the Hugging Face connector tools (`hf_fs`); writes go through our code or the
  `hf` command line, so they can be verified the same way.
- If a token is missing, say so and stop; do not ask for it in chat.

## Hard rules at this layer

- Nothing is deleted, renamed away or overwritten without the owner's word (VT-03); `hf repos delete-files` is never run
  on our own initiative.
- "Saved", "uploaded" or "done" only after a passing hash check in this turn (skill
  `v-superpowers-verification-before-completion`).
- Damaged files are not pushed: `cloud.store` checks before pushing; a picture that failed intake is not a vault asset.
- Large media stays out of git (`tests/unit/test_repo_hygiene.py`); git holds code and the JSONL records only.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `missing on HF` after a run | an upload failed silently or the run stopped early | re-upload from the local or Volume copy, verify again, then release |
| `hash differs on HF` | a re-encoded or partial file, or a name reused | upload under a new name; keep both; report |
| `not checked: <Error>` | API or network failure during the check | retry the check; never count it as verified |
| Two writers on one path | parallel jobs on one prefix | one writer per job prefix (last write wins on HF and Volumes) |
| A token visible in a log | printed by a script | rotate it (owner), scrub the log; never commit |

## Sources (idea sources only, no text copied)

- huggingface/skills, page `hf-cli` (Apache-2.0, commit `5291c2b936`): the official command line for upload, download,
  buckets and repo settings.
- gary149/huggingface-hub-skill (no licence file, commit `d5e8f2bd76`): read for the idea of Python SDK uploads only.
