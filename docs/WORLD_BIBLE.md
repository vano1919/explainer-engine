# World Bible and asset library

The two registers that carry one visual world across episodes (D-70 stage C, the creator's brief of 2026-10-22): the
**World Bible** (`explainer_engine/world/bible.json`, code `world/bible.py`, schema `schemas/world_bible.schema.json`)
versions the look; the **asset library** (`assets/library.json`, code `explainer_engine/assets/library.py`, schema
`schemas/asset_library.schema.json`) records every asset that outlives an episode. Three levels: bible -> library -> episode
pack (a script's `picture_dirs`). The look itself lives in its parts ([VISUAL_WORLD_ARCHITECTURE](VISUAL_WORLD_ARCHITECTURE.md):
`world/look_v2.json`, `world/eras.json`, `design/palette.json`); the bible pins them, it never restates them.

| ID | Rule | Enforced by |
|---|---|---|
| WB-01 | **One bible, one version.** The visual world has exactly one current version (`bible.json`: version, status draft / approved / superseded, date, reason, the pinned parts by sha256, camera language, graphics style, era-change rules, characters, motion default, banned drift, approved anchor asset ids, changelog). Nothing else defines "the look". | `world.bible.validate` (schema), `tests/unit/test_world_bible.py` |
| WB-02 | **A changed part is a new version.** When `look_v2.json`, `eras.json` or `palette.json` changes, the bible drifts; `bible check` fails until `bible bump --reason` writes the next version (minor for palette, era and rule edits; `--major` for a change of drawing grammar). The old version stays in the changelog as it was. | `world.bible.drift`, `check`, `bump`; the committed bible is tested against its parts |
| WB-03 | **Approval is recorded, never implied.** `status: approved` needs `approved_by` and `approved_at`; `bible approve --by` is refused while a part has drifted (what is approved is what is on disk). A new version starts as a draft. | `world.bible.approve`, `check` |
| WB-04 | **Every record cites the version.** `world.resolver.resolve` writes `bible` into every world.json; `imagegen.plan.make` writes it into every paint plan (outside the approved hash) and `paint plan` lists the library assets its references are (`plan.assets`); every library record carries `bible_version`. A change of look is therefore visible in the records, never silent. | `resolver.resolve`, `plan.make`, `paint.reference_assets`, `library.verify` (a version that never existed is a finding) |
| WB-05 | **Anchors are library assets.** The approved reference pictures that define a version (`anchors`) are asset ids; an id that is not in the library is a `check` finding. Until the stage D pilot the list is empty: no version is approved before the creator has seen anchors drawn under it. | `world.bible.check` |
| WB-06 | **One record per asset.** `assets/library.json` holds every channel asset: id `<kind>.<name>[.<variant>]` (P-66; kinds reference, anchor, sheet, sprite, picture, plate, prop, collage, lora, prompt, sound, music, font), file (repo-relative) and sha256, size, tags, description, `bible_version`, `made_with` (provider, model and version, prompt, params, seed, reference asset ids, LoRA, cost), licence, approval, lineage (parent), origin (episode that paid, created, source). The per-medium libraries (sounds `audio/sfx_library.py`; pictures `imagegen/picture_library.py` once PR #15 lands) keep their files; a record points at them through `origin.source`. | `library.make_record`, `register`, the schema |
| WB-07 | **Verify reports, never deletes.** `library verify` lists schema errors, duplicate ids, an id that does not start with its kind, an unknown parent, a bible version that never existed, an approval without a name, a missing or changed file. The committed library verifies clean in the test suite. | `library.verify`, `tests/unit/test_asset_library.py` |
| WB-08 | **A duplicate is a warning, never a veto.** Registering compares the new record with the library (identical bytes; same prompt, model and seed; shared tags of the same kind) and prints the matches as warnings; the person decides. Search is by tags, kind and version; embedding search (SigLIP-2 / DINOv2) is not built and comes with the stage D pilot. | `library.similar`, `register`, `find` |
| WB-09 | **A machine look never counts.** `approval.status` moves from `not_looked` only through `library approve --by <name>` (approved, rejected, superseded); rejected and superseded assets are hidden from `find` unless asked for. Lineage keeps them: a superseded sprite still names what was derived from it. | `library.approve`, `find`, `children` |
| WB-10 | **Reusable paid pictures become records.** When a paint plan is marked `reusable` (face sheets, channel assets), every picture it paints is copied under `assets/library/picture/` and registered with the plan's provider, model, prompt, references (as asset ids where the plan knew them) and share of the estimate, `approval: not_looked`. A plan for one episode's own pictures registers nothing. | `library.record_painted`, `paint.shelve` (sync and batch runs) |

## Commands

```powershell
.venv\Scripts\python -m explainer_engine.world.bible show | check | bump --reason "..." [--major] | approve --by "..."
.venv\Scripts\python -m explainer_engine.assets.library add <file> --id <kind>.<name> --kind <kind> --tags a,b [--prompt ...]
.venv\Scripts\python -m explainer_engine.assets.library find --tags a,b [--kind sprite] [--all]
.venv\Scripts\python -m explainer_engine.assets.library approve <id> --by "..." [--reject | --supersede]
.venv\Scripts\python -m explainer_engine.assets.library verify
```

## State (2026-10-22)

Bible v1.0 is a **draft**: the look v2 thread, the thirteen-era codex and the palette pinned; no anchors, no approval
(the creator approves the first version on the pilot's anchor pictures, stage D). The library holds the nine records the
repository already had a provenance for (`assets/characters/scientists_v0/generation_ledger.jsonl`: eight look-v1 sprites and
their analyst style reference), all `superseded` by look v2 (D-41) and kept for lineage. The creator's two reference images
in `assets/style_samples/` are not registered: their origin and licence are the creator's to state.
