# Asset system

A compact library built around the chosen strategy, not an exhaustive one: Kit; backgrounds; domain props (kitchen first);
generic props; diagram parts; labels and icons; speech bubbles; transitions; thumbnail elements. Stable ids, editable
vector first, every file with provenance and a licence.

## Asset record
`id` (P-66: `<kind>.<name>[.<variant>]`), `path`, `format` (svg first), `viewBox` or pixel size, `style` (stroke, palette
tokens used), `dependencies` (parts, fonts), `origin` (original | generated | third_party), `creator`, `source`,
`license`, `commercial_use` (yes/no/unknown: unknown blocks use), `variants`, `editable_layers`, `validation` (checks
passed + date), `reuse_rights`, `fallback` (asset id), `tags`, `used_by`.

## Rules
- Prefer SVG components for anything placed, recoloured, scaled, rigged or animated deterministically; raster only when
  its benefit outweighs the lost editability (then record why).
- Colours only from `explainer_engine/design/palette.json`; fonts only OFL faces (Fredoka and Inter for titles and captions; Comic Neue Bold and Bangers for speech bubbles, D-42, in `assets/fonts/` with their OFL texts); a lint rejects other colours.
- Characters: fixed silhouette, proportions, facial geometry, line weight, palette and expression/pose conventions
  (the Kit sheet). Never regenerate "an approximate Kit" per scene; poses are assembled from the parts (D-04).
- Reuse search before creation (OR-17, D-61): tags and kind are matched against the library manifests before anything
  new is generated, and the search is recorded in the episode's `asset_reuse.json` (`python -m explainer_engine.assets_reuse`).
  Raster channel assets live in the picture library `assets/pictures/library/` (`explainer_engine/imagegen/picture_library.py`:
  `add`, `find`, `fetch`, `validate`; schema `picture_manifest.schema.json`; kinds prop, background, texture, character,
  thumbnail_part), `paint plan` lists a prompt's matches on the plan (PP-08), and a new asset is created only when
  nothing fits. Media backup: HF `datasets/vano1919/tmr-artifacts/library/pictures/`.
- A missing asset has a named fallback; the job stops at QA rather than shipping a placeholder (P-77).
- One-off assets are marked `reuse: new` and need a fallback; reusable assets are promoted after their first use.

## Generated assets (Gemini or similar)
Allowed only for assets that stay useful independent of any single topic: the mascot's concept exploration, props or
backgrounds the library will reuse, thumbnail design elements (D-19; the producer's rule of 2026-10-11). Never for one
topic's own pictures. Before any paid call: state what it is for, whether the result is reusable, the estimated cost and
the remaining budget; if it is not reusable, stop and ask. Under D-27 (painted look) generated output may also be used directly as a raster layer
(mascot pose, world background, prop), provided it is part of a reusable kit with a recorded source image, prompt
and cost; one-topic pictures stay forbidden. Otherwise it is a reference, not the final vector: it is traced or
redrawn into the SVG parts, and tested for consistency, layer separation, animation
usefulness, editability, time saved and cost. No-cost fallback when the budget is exhausted: hand-built SVG shapes and
CC0 resources.

## Licence register
`docs/` plus `assets/LICENSES.json` (created in Phase 4): one entry per font, SFX, music or third-party file: name,
source URL, licence, commercial-use status, access date, file hash. Commercial use is never inferred from availability
online; "unknown" blocks the asset.

## Manifest per episode
`jobs/<slug>/.../asset_manifest.json` lists every asset the storyboard references with `reuse|new|generated|manual|third_party`
and its record; `qa` checks that every reference resolves and every record is valid.
