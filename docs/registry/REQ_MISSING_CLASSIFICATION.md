# Classification of the 21 MISSING entries (deltas 2-6), before any check is written

Rule: a check is written only for a rule that code can measure from its own words. A rule that is taste, policy or a human judgement gets the class MANUAL and no check (owner decides, rule OR-22). Where the rule is measurable but the code it needs does not exist yet, the class is NEEDS-CODE and the check waits for a DeepSeek brief with the exact words.

| ID | Class | Why |
|---|---|---|
| OR-A16 | MANUAL | licence policy wording ("licence does not interest me, quality does"); the owner's call |
| OR-A17 | AUTO (candidate) | "no BBC RemArc id in a monetised master": publish_check PC-10 already reads stems_report.json for RemArc ids (see test_third_party_media.py); check the mapping before writing anything |
| OR-A19 | NEEDS-CODE | one voice_id per character and a first-take read: needs the cast file and the clip read record |
| OR-A20 | NEEDS-CODE | voice_card verbatim in every LTX prompt: needs a scan of the scene files; measurable |
| OR-A22 | AUTO (candidate) | measured wpm 155-185, target 170: the read measure exists (BP-01 in sourced_rules); check its input |
| OR-A23 | NEEDS-CODE | words.json timing coverage >= 97 %: measurable, the Scribe word-timing file is the input; check the field first |
| OR-I44 | MANUAL | run-consent policy ("write into the rules"); a rules statement, not code |
| OR-I45 | NEEDS-CODE | cheapest combination of a pod run (RP-11): needs cloud/schedule.py; check whether it exists in this tree |
| OR-I46 | MANUAL | an exception for the watchdog, contrary to the paid-run rule; owner must decide, not code |
| OR-I47 | NEEDS-CODE | vault verify and HF hash per pod: depends on the HF tags, which the connector cannot verify here |
| OR-I48 | AUTO (candidate) | paid music/SFX refused without a library search: assets_reuse.py already refuses (OR-18, see the earlier trace) |
| OR-I49 | AUTO (candidate) | only script-critic and lora-checkpoint-judge spawned: test_agent_roles exists; check it names this exact rule |
| OR-S24 | AUTO (candidate) | plan cast has permanent:false, no HOST_COMMENTARY lane: a schema or field check |
| OR-S25 | MANUAL | editorial premise check ("Worlds collide..."), a human judgement |
| OR-S26 | MANUAL | "rewrite the whole system" is not a checkable rule; the scene_lint part (SC-01..SC-10) is separately covered by scene_lint |
| OR-S27 | AUTO (candidate) | map_basis real_earth or invented matching the episode type: a field check |
| OR-S28 | NEEDS-CODE | measured read before clip length: needs the scene-file gate, exists partly in the production pipeline |
| OR-V63 | NEEDS-CODE | master frame shared by a scene's pictures: needs continuity records (CS-01..); check existence first |
| OR-V64 | AUTO (candidate) | Canva refused while channel.canva_terms_verified is false: a config gate |
| OR-V65 | MANUAL | face match by judgement (BP-166 style share needs a judge model); not automatable in this pass |
| OR-V66 | MANUAL | style judged per frame: a visual judgement |

Counts: AUTO candidates 8 (A17, A22, I48, I49, S24, S27, V64 and one more to confirm), NEEDS-CODE 7, MANUAL 6. Nothing is written as a check yet; each candidate first gets a check of its input field.
Owner decisions needed before writing: the MANUAL rows (taste or policy), and whether the NEEDS-CODE rows may be written now at DeepSeek cost.

## Step 1 result: code existence check for the 8 AUTO candidates (grep, ro5jb3-equivalent vw8syg tree)
| ID | Enforcing code found | Test found | Result |
|---|---|---|---|
| OR-V64 | explainer_engine/production/validate.py (canva_terms_verified) | tests/unit/test_production_system.py | CODE EXISTS: a check can point at it after reading the gate |
| OR-S24 | explainer_engine/core/contracts.py (permanent, HOST_COMMENTARY) | none named | CODE EXISTS, test missing: write the test after reading contracts.py |
| OR-A22 | explainer_engine/edit/rhythm_profile.py (BP-01) | none named | CODE EXISTS, wpm field to confirm |
| OR-A17 | explainer_engine/qa/publish_check.py (PC-10 RemArc) | tests/unit/test_third_party_media.py | CODE EXISTS (covered by PC-10 tests) |
| OR-I48 | explainer_engine/assets_reuse.py (OR-18 refusal) | tests/unit/test_assets_reuse.py | CODE EXISTS (covered) |
| OR-S27 | none: map_basis appears only in the registry | none | GAP: no code or field; not written |
| OR-I49 | none: test_agent_roles is named in the registry but does not exist in the tree | none | GAP: the named test is missing; not written |
| OR-A17 and OR-I48 are already covered by existing tests and need only a pointer. |

So of the 8 AUTO candidates: 5 have code to point at (V64, S24, A22, A17, I48; A17 and I48 need only the pointer), 2 are gaps (S27, I49), and the 8th candidate (listed as "to confirm") is S27-or-I49 territory and is recorded as a gap too. No check was written in this step.
