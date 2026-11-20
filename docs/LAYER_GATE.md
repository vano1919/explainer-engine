# Layer gate (MS-6, skills team plan 2026-11-20)

A layer of the film pipeline (L1..L33 of `final_plan_2026-11-19/SKILLS_REWRITE_50_BRIEF.md`) is changed only after its record
`docs/layers/<layer>.json` shows that the mandatory steps MS-1..MS-5 were done. The code is
`explainer_engine/governance/layer_gate.py`; its tests are `tests/unit/test_layer_gate.py` (one negative test per missing part).
Why: the owner found requirements ignored (2026-11-20, see [D-140](DECISIONS_AND_OPEN_QUESTIONS.md)); text rules alone did not stop it.

```
python -m explainer_engine.governance layers [--layer L9] [--strict]   # exit 0 PASS, 1 BLOCK, 2 NOT_RUN
python -m explainer_engine.governance check                           # also fails for a BLOCK in a FINAL record
```
In code before a layer is vendored or run: `layer_gate.require_pass("L9")`. It raises `ContractError` for a BLOCK or a draft and
`NeedsReview` for a NOT_RUN or a layer whose lower groups are not ready.

**A licence is information only** (owner, 2026-11-20 08:10 UTC, [D-141](DECISIONS_AND_OPEN_QUESTIONS.md)): `licence`,
`licence_source` and `monetised_ok` on a candidate are optional, are never required and never checked against a choice, and exclude
no candidate. The RR rules about what the viewer sees and hears are a different thing and stay as they are.

## Status
- **BLOCK**: a part of MS-1..MS-5 is missing or wrong (the codes below).
- **NOT_RUN**: the record is complete, but a sub-question has only trials that were not run, or run with a bad configuration
  (`config_ok` false). Never a pass.
- **PASS**: everything is present and every sub-question has a trial that ran and was looked at.
- `state: "draft"` is reported only. `state: "final"` needs `signed_by` and `signed_at` (the team lead), the MS-7 owner check
  (`owner_check`, `owner_seen`) and a BLOCK in it fails `governance check`. `require_pass` accepts only a final record.
- **Group order** (team plan section 3): `GROUPS` lists the layers of the ten groups and a record must carry its layer's group.
  `require_pass` for a layer of group N raises `NeedsReview` while any layer of a lower group is not ready. A layer is ready when
  its record is final and PASS. A final NOT_RUN is ready only with `not_run_waiver`, the `cmsg_` id of the owner's own word on
  it. A BLOCK is never ready. `layers` prints per group whether it is ready or what it waits on.

## Record `layer_record/1`
| Field | Content |
|---|---|
| `schema`, `layer`, `name`, `group` (1-10), `state` | identity; the file name is `<layer>.json`; the group is the layer's group in `layer_gate.GROUPS` |
| `signed_by`, `signed_at`, `owner_check[]`, `owner_seen` (final only) | the team lead's signature; MS-7: links the owner can watch, each `{url (https) and/or sha256}`; `owner_seen` is the owner's `cmsg_` id or `"pending"` (allowed, but printed as pending; never allowed for `keep_ours`) |
| `not_run_waiver` (optional) | the owner's `cmsg_` id that lets a final NOT_RUN layer open the next group |
| `sub_questions[]` | `{id, text, few_candidates_reason?}` |
| `requirements[]` (MS-1) | `{id, text, source: {kind: message / decision / memory / rule, ref}, ours_meets?, complaint?: {open, fix_seen}}`; a message ref is a `cmsg_` id, a decision ref a D- id that exists in the decision log; `ours_meets` and `complaint` matter only for `keep_ours` |
| `tool_capabilities[]` (MS-1) | `{id, tool, capability, use: used / not_used, reason}` (a reason for both) |
| `candidates[]` (MS-2) | `{id, sub_question, kind: repo / doc, url (https), author, stars + commit (repo) or retrieved date (doc), teaches, fit 1-5}`; optional information: `licence`, `licence_source`, `monetised_ok`; for `keep_ours`: `top` (a doc candidate that is the most-starred equivalent), `state_of_the_art`, `configured_per` (https docs url), `config_log` (`{ref, sha256}`); at least 3 in the layer and 3 per sub-question unless the sub-question gives a `few_candidates_reason` |
| `trials[]` (MS-3) | `{id, sub_question, status: RUN / NOT_RUN}`; RUN: `looked_at_by`, `observation`, `links[] {ref, kind: file / page, sha256 (file), seen}`; NOT_RUN: `not_run_reason`; optional `candidate_ids` (the candidates of the sub-question this trial ran) and `config_ok` (false = badly configured, counts as NOT_RUN) |
| `decisions[]` (MS-4) | one per sub-question: `{sub_question, choice: adopt / enrich / keep_ours / idea_only, candidate_ids, reason, evidence: [trial ids], beats, ours_author, blind_judge}`; `idea_only` means: use the idea, copy nothing; `keep_ours` is the strict case below |
| `mapping[]` (MS-5) | `{requirement: <requirement or used capability id>, target: {kind: skill_line (path:line, the line exists) / validator (a RULE_ID of `validators/`) / sourced_rule (a BP id) / validator_planned (ref + wave, refused by `--strict`), ref}}`; every requirement and every used capability is mapped |

## MS-4: "keep ours" needs all five (owner, 2026-11-20 08:07 UTC)
The default is the public approach. `keep_ours` stands only when every rule holds, otherwise the gate is BLOCK and the
sub-question adopts or enriches. The older rule stays: a run trial of the sub-question is the evidence and `beats` lists every
candidate (`MS4-KEEP-EVIDENCE`).

| Code | Rule |
|---|---|
| `MS4-KEEP-REQ` | (a) every requirement of the layer has `ours_meets: true`; a `complaint` needs `open: false` and the owner's `fix_seen` message id |
| `MS4-KEEP-RUN3`, `MS4-KEEP-TOP`, `MS4-KEEP-SOTA` | (b) at least 3 distinct candidates were run (trials with status RUN, `config_ok` not false, naming them in `candidate_ids`); the most-starred repo candidate (or the doc candidate with `top: true`) and one marked `state_of_the_art: true` are among them |
| `MS4-KEEP-CONFIG` | (c) every run candidate has `configured_per` (https docs url) and `config_log` (link and sha256); a badly configured trial counts as NOT_RUN |
| `MS4-KEEP-JUDGE` | (d) the decision has `ours_author` and a `blind_judge` with `judge` other than the author, `wrote_our_code: false`, `labels_sealed` and `scores` (links with sha256), `labels_sealed_before_scoring: true` and a `method` |
| `MS4-KEEP-OWNER` | (e) `owner_seen` is the owner's `cmsg_` id, never `"pending"` (pending stays allowed for adopt and enrich) |

Example decision that passes (the record also needs its candidates, trials, requirements with `ours_meets: true` and `owner_seen`):
```json
{
  "sub_question": "SQ1",
  "choice": "keep_ours",
  "candidate_ids": [],
  "reason": "ours scored highest in the blind scoring",
  "evidence": ["TR1"],
  "beats": ["C1", "C2", "C3", "C4"],
  "ours_author": "developer thread",
  "blind_judge": {
    "judge": "fresh reviewer",
    "wrote_our_code": false,
    "labels_sealed": {"ref": "https://huggingface.co/datasets/x/y/blob/main/labels_sealed.json", "sha256": "<64 hex>"},
    "labels_sealed_before_scoring": true,
    "scores": {"ref": "https://huggingface.co/datasets/x/y/blob/main/scores.json", "sha256": "<64 hex>"},
    "method": "rubric 1-5, sealed random labels"
  }
}
```

## Error codes
`LG-SCHEMA`, `LG-DUP`, `LG-SIGN`, `LG-OWNER`, `MS1-REQ-NONE`, `MS1-REQ-FIELD`, `MS1-REQ-SOURCE`, `MS1-CAP-NONE`, `MS1-CAP-FIELD`, `MS2-SUBQ`,
`MS2-CAND-MIN`, `MS2-CAND-FIELD`, `MS3-TRIAL-NONE`, `MS3-TRIAL-FIELD`, `MS4-DEC-MISSING`, `MS4-DEC-FIELD`, `MS4-KEEP-EVIDENCE`,
`MS4-KEEP-REQ`, `MS4-KEEP-RUN3`, `MS4-KEEP-TOP`, `MS4-KEEP-SOTA`, `MS4-KEEP-CONFIG`, `MS4-KEEP-JUDGE`, `MS4-KEEP-OWNER`,
`MS5-MAP-MISSING`, `MS5-MAP-TARGET`.
The gate checks that the parts exist and are well formed and that references resolve; whether a candidate is the right choice is
the team lead's call and is not judged by code.
