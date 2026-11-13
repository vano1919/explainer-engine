# The sound library (D-134, 2026-11-13)

The channel's own collection of real recordings, catalogued so a shot's sound is chosen, not improvised. It extends the W1 library
(`assets/audio/library/manifest.json`, schema `sfx_manifest.schema.json` v1; D-133) instead of standing beside it: the same
manifest, the same `audio/sfx_library` API, more fields. The scene-aware design that uses it (the per-shot design, the cue sheet,
the mix check) is SP-03..SP-07 of [EPISODE_FIRST](EPISODE_FIRST.md).

What lives where:

| What | Where | In git |
|---|---|---|
| the manifest (every item, its licence, catalog, original, QC) | `assets/audio/library/manifest.json` | yes |
| the 48 kHz working copies | `assets/audio/library/<category>/<id>.wav` | no (HF vault) |
| the untouched originals (or the head of a long one, see LIB-02) | `assets/audio/originals/<source>/` | no |
| the classification dimensions | `assets/audio/taxonomy.json` | yes |
| the pick lists (what was taken, from where, and why) | `assets/audio/free_picks_2026-11-13.json`, `bbc_picks_2026-11-13.json` | yes |
| the import reports | `assets/audio/import_reports/` | yes |
| the search index (rebuilt on demand) | `assets/audio/library/catalog.sqlite` | no |
| previews (mp3 excerpt, spectrogram, html page) | `assets/audio/previews/` | no |

| ID | Rule | Checked by | Severity |
|---|---|---|---|
| LIB-01 | **One library, extended in place.** New sounds enter `manifest.json` through `audio/free_import.run2` (pick lists of schema `free_sound_picks/2`) or the older paths (`audio/register.py`, `build_library`); nothing overwrites a stored take (same id = a new take number) and no binary enters git. | `sfx_library.validate`, `tests/unit/test_committed_sound_library.py`, `.gitignore` | FAIL |
| LIB-02 | **The original is kept and described.** Every imported item records its original: path, file name, sha256, format, codec, rate, channels, bit depth, length, size, url and the date. A long archive recording may be fetched as its head only (the samples a loop uses, never the whole 70 MB file); the item then says `partial` with the seconds and bytes. An existing original is never downloaded again. | `free_import._download`, `_resolve`; schema `original` | FAIL (schema) |
| LIB-03 | **Sources are read, never bypassed.** A source is used only through its public pages or its own public API, one item at a time with a pause (Mixkit User Terms 9: no scripted mass download); a source that answers with a bot challenge, a 403 or a rate limit is listed in `sources.BLOCKED` with the date and left alone (Freesound, Sonniss, Pixabay, Zapsplat, Wikimedia Commons, BigSoundBank on 2026-11-13). | `audio/sources.py` readers (OpenGameArt, Mixkit, Incompetech, BBC) | — |
| LIB-04 | **Every item carries its licence fields**: type, url, source url, creator, attribution needed and its text, commercial use, modification, redistribution, AI processing, the date it was read, what it was judged for (`use`: music or sfx) and the verdict `production` (verified, quarantine, rejected). | `sources.licence_record`; schema `licence` | FAIL (schema) |
| LIB-05 | **Licence matters for the music; an effect is chosen by quality** (the creator, 2026-11-13 07:24 UTC: "licence does not interest me, quality does; licence concerns only the background music"; 07:49 UTC card: "yes, BBC too"). Music keeps the licence gate (commercial use, no share-alike, the credit line in the description: Incompetech CC BY 4.0). An effect's licence is recorded as information; the BBC Sound Effects archive (RemArc, non-commercial) is verified for effects by his recorded word, a temporary exception to CLAUDE.md invariant 5 for sound effects only, never for music. Quarantined items (unverified generated takes) never play in production: `find(usable=True)` hides them. | `sources.verdict(use=)`, `SFX_EXCEPTIONS`; `sfx_library.production_status`, `find`; `episode/cue_sheet` gate `music_licence` | FAIL (music) |
| LIB-06 | **The catalog has the brief's dimensions.** Each item's `catalog` block (values from `taxonomy.json`): Freesound's Broad Sound Taxonomy top level, sound category and subcategory, genres and scene types, historical era, environment, materials, action tags, mood, intensity 1-5, distance, interior/exterior, width, usage, loopable; an item classified from its tags only says `inferred: true`. | `audio/catalog.migrate`, `infer_catalog`; schema `catalog` | FAIL (schema) |
| LIB-07 | **QC before an item enters**: it decodes, is not empty or mostly digital silence (FAIL); clipping (flat runs at full scale), a DC offset, a noise floor under a one-shot, a loop seam (BP-58) and a lossy original are REVIEW or INFO; the working copy is 48 kHz; an exact copy (same original sha256) is refused; near duplicates are found by a spectral fingerprint (`asset_qc.near_duplicates`). A PASS means technically usable, never "sounds good": `review.human` stays `not_listened` until the creator listens. | `audio/asset_qc.check`, `measure`, `fingerprint`; `catalog requalify`, `duplicates` | FAIL / REVIEW |
| LIB-08 | **Search and preview from the command line** (below): every filter is one dimension of LIB-06, `--playable` keeps only verified items whose working copy is here, `preview` writes an excerpt, a spectrogram and a page to listen through, `credits` prints the description's credit lines for the items a cut used. | `audio/catalog.search`, `preview`, `credits` | — |

## Commands

```bash
python -m explainer_engine.audio.sources bbc-search "horse and cart"      # the BBC archive's own search (id, length, channels, CD)
python -m explainer_engine.audio.sources bbc 07050159                    # one item: licence, credit, file url
python -m explainer_engine.audio.sources mixkit https://mixkit.co/free-sound-effects/war/
python -m explainer_engine.audio.sources incompetech "Crusade"
python -m explainer_engine.audio.sources blocked                         # the sources left alone, with the reason and date
python -m explainer_engine.audio.free_import assets/audio/bbc_picks_2026-11-13.json [--only name1,name2]
python -m explainer_engine.audio.catalog migrate       # infer catalog + licence fields for older items (never overwrites hand-made ones)
python -m explainer_engine.audio.catalog requalify     # QC again over the working copies and originals that are here
python -m explainer_engine.audio.catalog index         # build catalog.sqlite
python -m explainer_engine.audio.catalog search --category weapons --era bronze_age --playable
python -m explainer_engine.audio.catalog search --scene battlefield --mood aggressive --distance distant
python -m explainer_engine.audio.catalog preview --category vehicles --out assets/audio/previews/carts
python -m explainer_engine.audio.catalog duplicates
python -m explainer_engine.audio.catalog search --source bbc --category weapons     # --source / --licence-type match one column
python -m explainer_engine.audio.catalog credits <out>/stems/cue_sheet.json            # the credit lines of what a cut played
python -m explainer_engine.audio.catalog report
```

## The library on 2026-11-13

260 items: Mixkit 74 (Mixkit Sound Effects Free License), OpenGameArt 63 + 1 arranged (CC0), BBC 34 (RemArc, effects only), Incompetech
15 tracks (CC BY 4.0, credit lines recorded), ElevenLabs 12, procedural 45 (preview placeholders only), Gemini TTS 15 + Lyria 1
(quarantine: provider terms not checked). Kinds: 161 one-shots, 84 loops, 15 tracks. QC: 118 PASS, 69 REVIEW, 73 NOT_RUN (their working
copies are in the vault, not in this container; `requalify` measures them where they are). Classified by hand: 123; the rest inferred.

The BBC picks fill the gaps the brief named: wooden carts and two-horse carts (the closest real recordings to chariot wheels), period
battle atmospheres, swords and axes, battle crowds taunting and charging, cavalry, marching soldiers, archery, a horn call, war-time drum
tattoos, a sailing ship's deck and cabin, a harbour wall with gulls, bonfires and small fires, church bells, a thunderstorm, woodland,
a village edge, a blacksmith and a drawbridge. Nobody has listened to them yet; they were picked by the archive's own descriptions
(recording, perspective, period) and measured.
