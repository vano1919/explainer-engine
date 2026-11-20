# Overlay for `v-superpowers-test-driven-development`: Test first, in this repository (layer L33, every stage)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from obra/superpowers, page `test-driven-development` (MIT, commit `22f0b463e7`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a Python pipeline with about four hundred unit test
files, a rules registry and a docs linter. The upstream text is this folder's `SKILL.md`; its
`writing-good-tests.md` stays usable as background on test quality (open it when a test feels brittle or mock-heavy).

## The rule here

Every meaningful change ships with a focused test and a `docs/PROGRESS.md` entry, plus the decision log when a decision
moved (CLAUDE.md invariant 11). Writing that test first is how we make sure it tests the change and not the code we
happened to write. "Meaningful" covers code, validators, schemas, runner stages, hooks, and rule text that a test pins
(skills, agent pages, docs that `docs_lint` reads). It does not cover a typo in prose nobody checks.

A creator note becomes a rule with a test (OR-09): the test is the proof the note was heard.

## The cycle

1. **Red.** Write one test that states the behaviour in its name, as a sentence:
   `test_a_line_with_a_number_and_no_claim_id_is_review`. Use the real module and a small fixture; put shared inputs
   under `tests/fixtures/`. Run only that test: `python -m pytest -q tests/unit/test_x.py::test_name`.
2. **Check the failure.** It must fail because the behaviour is missing (an assertion), not because of an import error,
   a typo or a missing fixture. A test that passes at once tests something that already exists: rewrite it.
3. **Green.** The smallest change in `explainer_engine/` that makes it pass. No extra options, no refactor of
   neighbours (invariant 8 forbids unrelated refactors anyway).
4. **Re-run** that test, then the files around it (`python -m pytest -q tests/unit/test_x.py`).
5. **Clean up** with the test green; match the hand style (no formatter, lines about 120).
6. **Suite.** Run the whole suite once: `python -m pytest -q`. If something else broke, re-run only the failures
   (`python -m pytest -q --lf`, or the failing node ids) while fixing; finish with one more full run.

For a bug: the first step is a test that reproduces it on the smallest input (often lifted from the failing episode
record), then the fix. The PROGRESS entry names the cause and the general fix, the way recent entries do.

## What makes a test right here

- **Numbers come from the registry.** A threshold that a validator enforces lives in
  `explainer_engine/standards/sourced_rules.json` (BP-xx, D-59). The test reads it through
  `explainer_engine/standards/sourced_rules.py` (`T("BP-77", "quotes_max")`) or builds inputs on both sides of it; a
  literal copy of the number in a test is a second home that drifts. `tests/unit/test_sourced_rules.py` keeps registry,
  table and code together.
- **One home per ID.** Rule ids (BP-, PV-, RR-, MA-, VL-, D-) are defined once; a test asserts behaviour, it does not
  restate the rule text. `python -m explainer_engine.docs_lint` must stay clean when docs change.
- **No money and no network.** No ElevenLabs, Gemini, Modal or HF call in a test. Provider clients get a fake at the
  boundary; paid paths prove their save-as-it-arrives behaviour (OR-33) and their ledger reservation
  (`explainer_engine/core/ledger.py`) with fakes.
- **No media in the repo.** Fixtures are small JSON or text; generated files go to `tmp_path`.
  `tests/unit/test_repo_hygiene.py` guards media and keys.
- **Writes go through the atomic helpers** (`explainer_engine/core/store.py`), so tests that write files behave the same
  on the creator's Windows PC.
- **Names that agents and skills cite must exist.** `tests/unit/test_agent_governance.py` fails on a missing module,
  path or skill; a planned one carries "(planned, W2)".
- **Measure or say NOT_RUN.** A gate test checks that the row reports NOT_RUN when its input is absent, never a silent
  PASS (the v4.3 runner's contract).

## Never

- Weaken, skip or delete a test or an acceptance criterion to make a phase pass (invariant 10). A test that now
  contradicts a newer creator decision is changed in the same change that records the decision, and the PROGRESS entry
  says so.
- Mark a test `xfail` or wrap an assertion in `try` to get green.
- Change a number in `config/spend_caps.json` or `config/model_routing.json` to make a test pass; both change only on
  the creator's word (hooks refuse it).
- Keep code written before its test "as reference". Delete it, write the test, write the code again from the test.

## Excuses and answers

| Excuse | Answer |
|---|---|
| "It is only a skill or doc edit" | if a test reads it (governance, ICW-01 wording, craft checklists), run that test |
| "The full suite is slow" | run it once at the end; iterate on the focused file and `--lf` |
| "I tested it by hand on the episode" | a hand run leaves nothing for the next change; write the test from that run's input |
| "The rule is obvious" | obvious rules drift the fastest; the registry exists because 211 contradictions did (D-59) |
| "The fix is one line" | one line, one test, one PROGRESS line |

## When stuck

If the test is hard to write, the design is usually the problem: too many collaborators, a function doing two stages'
work. Ask the planning thread on the higher model before redesigning (OR-24, OR-26); a material conflict with the
approved architecture stops at the boundary with evidence and options (invariant 12).

## Not used from upstream

The TypeScript examples, the "your human partner" framing (here: the creator, who decides rules but does not review
code), and the debugging hand-off name (ours is skill `v-superpowers-systematic-debugging`). Before saying a change is
done, skill `v-superpowers-verification-before-completion` applies.
