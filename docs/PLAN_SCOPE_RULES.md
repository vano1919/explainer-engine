# Plan Scope Rules

**Status:** Binding rules for every plan. Owner's words, 2026-11-22.

## SC-1: Every owner requirement is listed

Every plan lists every owner requirement.
That includes every new skill the owner asked for.
A requirement is never dropped from a plan.

## SC-2: Current code protection is not a reason to skip a requirement

Protecting the current code is never a reason to skip a requirement.
"Keep the current code working" is a constraint on how a requirement is built.
It is not a reason to leave a requirement out.

## SC-3: Scope reduction is invalid

A plan that reduces the scope of an owner requirement is not valid and does not apply.
The plan must be rejected.
The rejection must be reported to the coordinator.

## SC-4: Requirements coverage section

Every plan has a section titled "Requirements coverage".
That section has this table:

| Owner requirement id | Quote or pointer | Where the plan covers it | Status |
|---|---|---|---|
| ... | ... | ... | covered / missing |

Any "missing" row blocks the plan.

## Forbidden pattern example

V4.1 was judged invalid because it did not add the new skills.
It only protected the current code.
V4.1 is disqualified under these rules.

## Scope of application

These rules apply to all plans, all threads, and all agents.
They apply to all future CLAUDE.md text and all future skill text.

## Enforcement

`tests/unit/test_plan_scope_rules.py` checks that this file exists.
It checks that this file is linked from `docs/INDEX.md`.
It checks that this file contains the words "Requirements coverage" and rules SC-1 to SC-4.