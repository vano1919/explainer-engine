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
`NeedsReview` for a NOT_RUN.

## Status
- **BLOCK**: a part of MS-1..MS-5 is missing or wrong (the codes below).
- **NOT_RUN**: the record is complete, but a sub-question has only trials that were not run (each says why). Never a pass.
- **PASS**: everything is present and every sub-question has a trial that ran and was looked at.
- `state: "draft"` is reported only. `state: "final"` needs `signed_by` and `signed_at` (the team lead), the MS-7 owner check
  (`owner_check`, `owner_seen`) and a BLOCK in it fails `governance check`. `require_pass` accepts only a final record.
- **Group order** (team plan section 3): `GROUPS` lists the layers of the ten groups and a record must carry its layer's group.
  `require_pass` for a layer of group N raises `NeedsReview` while any layer of a lower group has no final, non-BLOCK record;
  `layers` prints per group whether it is ready or what it waits on.

## Record `layer_record/1`
| Field | Content |
|---|---|
| `schema`, `layer`, `name`, `group` (1-10), `state` | identity; the file name is `<layer>.json`; the group is the layer's group in `layer_gate.GROUPS` |
| `signed_by`, `signed_at`, `owner_check[]`, `owner_seen` (final only) | the team lead's signature; MS-7: links the owner can watch, each `{url (https) and/or sha256}`; `owner_seen` is the owner's `cmsg_` id or `"pending"` (allowed, but printed as pending) |
| `sub_questions[]` | `{id, text, few_candidates_reason?}` |
| `requirements[]` (MS-1) | `{id, text, source: {kind: message / decision / memory / rule, ref}}`; a message ref is a `cmsg_` id, a decision ref a D- id that exists in the decision log |
| `tool_capabilities[]` (MS-1) | `{id, tool, capability, use: used / not_used, reason}` (a reason for both) |
| `candidates[]` (MS-2) | `{id, sub_question, kind: repo / doc, url (https), author, stars + commit + licence_source (repo; the https url of the LICENSE file at the commit, or `"none"`, which forces `monetised_ok` false) or retrieved date (doc), licence, monetised_ok (true / false), teaches, fit 1-5}`; at least 3 in the layer and 3 per sub-question unless the sub-question gives a `few_candidates_reason` |
| `trials[]` (MS-3) | `{id, sub_question, status: RUN / NOT_RUN}`; RUN: `looked_at_by`, `observation`, `links[] {ref, kind: file / page, sha256 (file), seen}`; NOT_RUN: `not_run_reason` |
| `decisions[]` (MS-4) | one per sub-question: `{sub_question, choice: adopt / enrich / keep_ours / idea_only, candidate_ids, reason, evidence: [trial ids], beats}`; `adopt` and `enrich` need `monetised_ok` true, `idea_only` is for a candidate whose licence refuses a monetised channel, `keep_ours` needs a RUN trial of the sub-question as evidence and `beats` listing every candidate of it |
| `mapping[]` (MS-5) | `{requirement: <requirement or used capability id>, target: {kind: skill_line (path:line, the line exists) / validator (a RULE_ID of `validators/`) / sourced_rule (a BP id) / validator_planned (ref + wave, refused by `--strict`), ref}}`; every requirement and every used capability is mapped |

## Error codes
`LG-SCHEMA`, `LG-DUP`, `LG-SIGN`, `LG-OWNER`, `MS1-REQ-NONE`, `MS1-REQ-FIELD`, `MS1-REQ-SOURCE`, `MS1-CAP-NONE`, `MS1-CAP-FIELD`, `MS2-SUBQ`,
`MS2-CAND-MIN`, `MS2-CAND-FIELD`, `MS3-TRIAL-NONE`, `MS3-TRIAL-FIELD`, `MS4-DEC-MISSING`, `MS4-DEC-FIELD`, `MS4-LICENCE`,
`MS4-KEEP-EVIDENCE`, `MS5-MAP-MISSING`, `MS5-MAP-TARGET`.
The gate checks that the parts exist and are well formed and that references resolve; whether a candidate is the right choice is
the team lead's call and is not judged by code.
