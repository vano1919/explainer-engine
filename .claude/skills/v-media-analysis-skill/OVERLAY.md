# Overlay for `v-media-analysis-skill`: Measuring media (layer L23, stages G7 intake, G9 and G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/media-analysis-skill, page `media-analysis` (MIT, commit `af49b926ff`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel that already measures its files in its own
gates. The upstream text is this folder's `SKILL.md`; the package under `src/` is not installed and not run;
`docs/observation.md` and `docs/tools.md` describe its observation model if we extend ours.

## The principle we keep

A measurement says what is in the file; it never says what to do. "Silence from 0 to 3 s" is the observation, "trim it" is
a decision made later by a stage or a person. Every number we report names the file (and its sha256 when it matters), the
tool and the parameters that produced it. A gate that did not measure says NOT_RUN, never PASS (EP-03). A machine PASS on
sound is never a listen (`human: not_listened`).

## What we measure, and with what

| Question | Our tool | Upstream analyzer it matches |
|---|---|---|
| container, streams, fps, length of a clip | ffprobe (skill `v-ffmpeg-skill` for probes); `videolane/ingest.py` on every LTX clip | `media_probe`, `video_format`, `audio_format`, `duration` |
| picture and sound of one length, frame count, fps of the master | `videolane/master_qa.py` (VL-12) | `timing` |
| black or frozen runs inside a video shot | `videolane/master_qa.py` (BP-164) | `scene_detection`, `edit_style` |
| real cuts against planned cuts | `videolane/cuts.py` (VL-11) | `scene_detection` |
| loudness and true peak of a delivered file | `qa/targets.measure_file` (ffmpeg ebur128; BP-50, BP-61) | `loudness` |
| voice against music and background, clipping, digital silence | `audio/mix_check.check` (BP-52, BP-161) | `silence`, `noise_floor` |
| dropouts, dead dialogue, pauses, sound across cuts, map motion heard | `qa/sound_realism` on the master (BP-189..BP-193) | `silence`, `audio_events` |
| where speech is in a clip | `videolane/ingest.speech` (the realism gate's band-energy spans, used for trims) and `ingest.voiced_spans` (Silero VAD when installed, else harmonicity) | `speech_regions` |
| a sound take before it enters the library | `audio/asset_qc.py` (LIB-07: decodes, clipping, DC, noise floor, seam) | `integrity`, `noise_floor` |

## Procedure

1. **Probe first, cheaply.** `ffprobe -v error -show_streams -show_format -of json <file>` tells codec, rate, fps mode and
   length; a variable frame rate from a generator is normal at intake and is normalised by the ingest step.
2. **Measure the delivered file, never the plan.** `python -m explainer_engine.qa.sound_realism <master.mp4> --timeline qa/scene_timeline.json`;
   loudness through `qa/targets.measure_file` on the encoded MP4, because an AAC encode moves the true peak.
3. **Run the gate that owns the number.** The G10 stage (`python -m explainer_engine.episode run episodes/<id> --stage G10`)
   runs `episode/acceptance`, the master QA and the realism rows and writes them into `production/stages/qa.json`.
   Rerun a stage rather than hand-measuring around it.
4. **Trace a surprising number** to its file: open the record, take the path and the parameters, measure again by hand
   with the same parameters. If the two disagree, the gate has a bug: report it with both values.
5. **Write what was not measured.** Upstream's rule: anything not measurable is null or not performed. Ours: the row is
   NOT_RUN with the reason (missing read, missing master, an optional detector not installed).

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| loudness passes on the WAV, fails on YouTube's copy | measured before encode | measure the MP4 (`qa/targets.measure_file`) |
| picture and sound differ by frames | a clip's audio longer than its picture at a join | master QA row names the shot; re-ingest that clip |
| "frozen" in a still_25d shot | the check reads a deliberate hold | frozen runs are judged inside `video` shots only; a 2.5D hold is the motion plan's business |
| speech found under a battle bed | band-energy detector, not a voice detector | VAD when installed; else listen; say which detector ran |
| a G10 row NOT_RUN | an input missing | find the earlier stage's record; never fill the row by hand |
| integrated loudness below the gate | a mostly silent file | check for a missing stem in the mix before any gain |

The final plan's technical-QA starting values (black and freeze lengths, silence length) are W2 work awaiting the
creator's confirmation; until then only the registry's BP rows decide. Any FFmpeg call beyond ffprobe goes through
`explainer_engine/finish/ffwrap.py` (planned, W2) once it exists. Reading a G10 report as a whole is skill `v-qc-skill`.

## References: when to open which

| File | Open when |
|---|---|
| `docs/observation.md` | shaping a new measurement record (identity, parameters, provenance, null for not measured) |
| `docs/tools.md` | checking what an analyzer measures and its parameters before writing ours |
| `docs/decisions.md` | why speech regions and audio events use fixed small classifiers, and their licences |
| `src/media_analysis/analyzers/timing.py` | comparing our A/V length check with its start-offset and gap logic |
| `contract/contract.json` | never at run time; only to compare tool tables |

## Not used from upstream

Its CLI, cache and budget engine (not installed; our stages cache by fingerprint already), highlight and applause
detection (we cut from the script, not from audience reactions), clip-library indexing, edit-style profiles of other
people's videos, and its default thresholds (ours come from the registry).
