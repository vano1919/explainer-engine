# The vault: nothing we made is lost

The creator's order (2026-10-24, thread "დაცვა: ნაშრომი არ დაიკარგოს"): every trained file, dataset and piece of code stays in
his hands and survives the loss of any one place. Decision [D-73](DECISIONS_AND_OPEN_QUESTIONS.md). Tool:
`python -m explainer_engine.vault` (`explainer_engine/vault.py`, stdlib only); what counts as critical: `config/vault.json`;
the list with hashes: `docs/VAULT_MANIFEST.json` (critical rows only; the full list lives on the primary copy at
`vault/VAULT_MANIFEST_full_<date>.json`).

## Where things live

| Copy | What | Owner | Survives |
|---|---|---|---|
| Primary: Hugging Face dataset `vano1919/tmr-artifacts` (private) | everything: weights, datasets, footage, videos, pod code | the creator's HF account | pods, sessions, project files |
| Pinned revision: HF tag `vault-<date>` | the primary as it was that day | same | an accidental delete or overwrite on `main` (the history keeps the bytes) |
| Code: GitHub `vano1919/explainer-engine`, `vano1919/tmr-video-script-engine` + git bundles of every branch on HF `vault/code/` | all code, open PRs included | the creator | a deleted branch, a lost GitHub repo |
| Second copy: the creator's own disk (`vault pull`) | the critical set (~8.1 GB on 2026-10-24) | the creator, offline | the loss of the HF account or token |
| Not a copy: RunPod pods and volumes, session scratchpads, project files | working space only | | nothing: anything there must reach HF first |

## Rules

| ID | Rule | Enforced by |
|---|---|---|
| VT-01 | A pod script that trains or writes weights ends with `python -m explainer_engine.vault check-uploaded <out> --to <hf prefix>` after its last upload: every output file on HF with the same sha256 (LFS) or git blob id. | `vault.lint_pod_script`, `tests/unit/test_vault.py` |
| VT-02 | That check is never muted (`\|\| true`): when it fails the pod is left as it is (stopped, never deleted) and someone reads the log. | `vault.lint_pod_script` |
| VT-03 | Nothing in the manifest is deleted, renamed away or overwritten without the creator's word; a new version gets a new name. | review; `vault verify` exits 1 on any MISSING/CHANGED row |
| VT-04 | After every approved LoRA, dataset or episode: `vault snapshot`, a new HF tag `vault-<date>`, and the creator is told how big the second copy's update is. | the thread that made it |
| VT-05 | Secrets are never part of the vault (HF token, RunPod key, YouTube tokens): they stay in env vars or gitignored `tools/`. | `tests/unit/test_repo_hygiene.py` |

## Commands

```powershell
python -m explainer_engine.vault snapshot                    # re-list HF with hashes -> docs/VAULT_MANIFEST.json
python -m explainer_engine.vault verify                      # PASS when every manifest row is still on HF, same hash
python -m explainer_engine.vault pull --dest D:\wldnk_vault  # the second copy (critical set); re-run = re-check, downloads only what changed
python -m explainer_engine.vault pull --dest D:\wldnk_vault --all   # everything (~49 GB on 2026-10-24)
python -m explainer_engine.vault check-uploaded output --to scene_lora_2026-10-24/train_v1/output   # on a pod, before it stops
```

Restore: weights and data from HF (`hf download vano1919/tmr-artifacts --repo-type dataset --include "<path>"`, or `--revision
vault-<date>` for a pinned day) or from the second copy; code with `git clone <bundle> <dir>` and `git branch -a`.
