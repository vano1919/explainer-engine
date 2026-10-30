# Craft curriculum (P3b, 2026-10-29)

The professional knowledge of each department (screenwriting, sound, cartography, cinematography, editing and colour,
animation, voice, packaging, motion graphics) in the three layers the repository already uses: a **skill page** (the
judgement, `.claude/skills/<skill>/SKILL.md`), a **checklist** (`explainer_engine/standards/craft_checklists/<dept>.json`,
the shape of `training/video_criteria.json`: one row per check with its kind, the artefact field it reads, its sourced
rules, its source and the code that enforces it) and the **sourced rules** (every number, [SOURCED_RULES](SOURCED_RULES.md),
D-59). This page is the index; it defines no ID. A checklist id (CRAFT-<dept>-nn) has its one home in its JSON; the
skill's CHECKLIST table and the index below are rendered copies (`python -m explainer_engine.standards.craft write`;
`tests/unit/test_craft_checklists.py` fails when a copy differs, when a row lacks a source or `enforced_by`, or when a cited
BP id is not in the registry).

Sources: [research/CRAFT_SOURCES_2026-10.md](research/CRAFT_SOURCES_2026-10.md) (sub-step 1, every URL opened on 2026-10-29
or marked not opened) is the only source a row may cite. A row's `source` is that file's section with its verdict
(SUPPORTED or PARTIAL), a repository rule already in force, or "Blueprint 2026-10 (unverified)" when no opened source
supports the number.

**Nothing in this curriculum is binding.** Under D-59 a rule binds only with two of the three source types (article, book,
video). The research opened articles only: no book was re-opened and no YouTube page could be read in the session, so every
new rule is a **hypothesis, REVIEW** (BP-114..138), and many numbers have no source at all beyond the Blueprint. The
checklists' code rows name validators that do not exist yet; they carry the plan phase that writes them (`planned`: P3,
P4, P4b, P5, P6, P7, P8, P9, P10). Until then a row is ticked by the critic or by eye. No existing threshold was changed.

## Departments

<!-- craft-index:begin -->
| department | skill | checklist | ids | code / critic / eye / manual | sourced rules |
|---|---|---|---|---|---|
| animation | `animation-principles` | `standards/craft_checklists/animation.json` | CRAFT-ANI-01..16 (16) | 3 / 0 / 13 / 0 | BP-23, BP-107, BP-109, BP-132, BP-133 |
| cartography | `cartography` | `standards/craft_checklists/cartography.json` | CRAFT-CART-01..08 (8) | 4 / 2 / 2 / 0 | BP-124, BP-125 |
| cinematography | `shot-visuals` | `standards/craft_checklists/cinematography.json` | CRAFT-CIN-01..11 (11) | 5 / 4 / 2 / 0 | BP-30, BP-103, BP-126, BP-127 |
| editing_colour | `video-editing-architect` | `standards/craft_checklists/editing_colour.json` | CRAFT-EDC-01..12 (12) | 7 / 2 / 3 / 0 | BP-25, BP-31, BP-128, BP-129, BP-130, BP-131 |
| motion_graphics | `video-editing-architect` | `standards/craft_checklists/motion_graphics.json` | CRAFT-MOG-01..15 (15) | 6 / 6 / 3 / 0 | BP-07, BP-28, BP-38, BP-54, BP-93, BP-134 |
| packaging | `shorts-for-video` | `standards/craft_checklists/packaging.json` | CRAFT-PKG-01..10 (10) | 3 / 2 / 2 / 3 | BP-11, BP-12, BP-29, BP-48, BP-135, BP-136, BP-137 |
| screenwriting | `narration-script` | `standards/craft_checklists/screenwriting.json` | CRAFT-SCR-01..07 (7) | 5 / 2 / 0 / 0 | BP-06, BP-07, BP-87, BP-88, BP-114, BP-115, BP-140 |
| sound | `editing-style` | `standards/craft_checklists/sound.json` | CRAFT-SND-01..14 (14) | 12 / 2 / 0 / 0 | BP-50, BP-53, BP-54, BP-56, BP-62, BP-116, BP-117, BP-118, BP-119, BP-120, BP-121, BP-122, BP-123 |
| voice | `elevenlabs-voice` | `standards/craft_checklists/voice.json` | CRAFT-VOX-01..09 (9) | 5 / 2 / 0 / 2 | BP-01, BP-10, BP-14, BP-138 |
<!-- craft-index:end -->

Code paths each department's validators will live in (planned): screenwriting `scripting/register_lint.py`,
`scripting/syllables.py` (P3); sound `audio/sound_director.py`, the `pan` field in `production/assemble.py` (P4);
voice `audio/voice_audition.py`, `audio/voice_check.py` (P4b); cartography `explainer_engine/maps/`, lanes
`edit/visual_compensator.py` (P5); shot-card lens and height fields (P6); editing, colour and graphic motion
`production/assemble.py`, `finish/grade.py`, `edit/motion_lint.py` (P7); animation and acting `qa/identity.py`,
the departmental layers of `qa/editorial_review.py` that tick every critic row (P8); Shorts
`shorts/planner.py` (P9); retention and foot-slide checks have no phase yet (eye rows). The performance-director stage page points to the voice
checklist.

## Conflicts with rules in force (13 records)

The Blueprint names numbers that contradict a rule the project already enforces. None is resolved here and none of these
numbers is in the registry: **status for every row: creator decision pending, the existing rule stays in force.** The
"proposal" column is the recheck draft's technical suggestion (2026-10-29), not a decision.

| # | topic | Blueprint | rule in force | external evidence (CRAFT_SOURCES section 17 unless noted) | proposal (not decided) |
|---|---|---|---|---|---|
| 1 | integrated loudness | -16 LUFS narration chain | [BP-50](SOURCED_RULES.md) -14 LUFS, -1 dBTP; BP-61 for Shorts; `qa/targets.py` is the one home | no official YouTube figure; Frame.io (opened) "-12 to -14", snippets say -14; EBU Tech 3343 v4 section 9.2 (opened) gives -20..-16 LUFS for streaming | BP-50/BP-61 stay |
| 2 | narration pace | 135-145 wpm | [BP-01](SOURCED_RULES.md) target 170, band 155-185 | Rodero 2020 (opened): 180 wpm best of 160/180/200 (advertising, 200 adults); nothing opened supports 135-145 | BP-01 stays |
| 3 | music duck depth | 3-5 dB, attack 25 ms, release 400 ms | [BP-53](SOURCED_RULES.md) 6-12 dB, house 9 | snippets only (CapCut 6-12 dB, Vindral -6..-12 "gentle"); no broadcast standard for either | BP-53 stays; the spectral dip becomes BP-118 (hypothesis) |
| 4 | the outro | zero-fade hard cut at 899.0 s, a Shepard-tone rise | [ED-04](EDITING.md) 1.5 s fade to black; [BP-43](SOURCED_RULES.md) narration at least 15 s under the end screen | nothing external opened for either side | ED-04/BP-43 stay; the "session bridge" may be tested as a variant |
| 5 | dissolve on match cuts | a 12-frame dissolve on the map-to-drama match cut | [BP-31](SOURCED_RULES.md) a dissolve only at a change of place or time | no source opened | BP-31 stays |
| 6 | occlusion wipe | a silhouette wipes the lens in the last 10 frames | [ED-04](EDITING.md) no wipes | no source opened | V3: an exception to ED-04 only as an invisible cut, ordinary transitions stay cut or dissolve (CRAFT-EDC-06) |
| 7 | camera breathing | 0.4 Hz, 4 px, 0.15 degree Perlin breath on tense shots | [BP-24](SOURCED_RULES.md) no shake as a move, an accent only on impact | no external research done | only as the `wobble` accent |
| 8 | frame rate | 24 fps | [D-30](DECISIONS_AND_OPEN_QUESTIONS.md) 2560x1440, 30 fps | YouTube Help 1722171 (opened, section 16): 24, 25, 30, 48, 50, 60 all common, "upload at the rate recorded" | measure in P2 (the video model's native rate vs the assembler), no pulldown, not decided blind |
| 9 | map typography | Calibri, Cinzel, JetBrains Mono | [CREATIVE_STYLE_BIBLE](CREATIVE_STYLE_BIBLE.md) Fredoka and Inter (OFL) | no external research done | the style bible stays (CRAFT-CART-08) |
| 10 | source stamp on screen | a "[HISTORICAL FACT]" / "[COUNTERFACTUAL PREMISE]" stamp on the dossier card | [D-61](DECISIONS_AND_OPEN_QUESTIONS.md) full immersion, SC-11, [BP-88](SOURCED_RULES.md) | no external research done | D-61 wins: a fact's status lives in the claim map, not on screen |
| 11 | eye-trace radius | the next subject within 0.18 of the last exit point | [BP-30](SOURCED_RULES.md) focal shift at most 0.10 | the editmentor page behind 0.18 was not opened; the Rule of Six gives eye trace a small weight (secondary) | BP-30 stays |
| 12 | stimulus window | a visual change every 2.0-3.5 s, a flag at 4.0 s | [BP-36](SOURCED_RULES.md) gap REVIEW 8 s / FAIL 15 s, [BP-40](SOURCED_RULES.md) still limits; D-64 retired the metronome | no source opened for either | BP-36/BP-40 stay; 2.0-3.5 s at most a REVIEW on narrated non-character stretches |
| 13 | Shorts safe zone | 250 / 480 / 240 / 60 px | [BP-29](SOURCED_RULES.md) x 48-888, y 288-1248 | Google's vertical-video example 288/672/48/192 (section 16, via the safe-zone note; not re-opened); third-party estimates disagree | BP-29 stays REVIEW until a screenshot test on the creator's phone |

Also recorded, not a conflict with a binding rule: the Blueprint's film look (vignette 12 %, `noise=c0s=5`) differs from the
look in `production/assemble.py` (ED-04); BP-131 keeps the Blueprint's numbers for comparison only.

## The 17 areas the curriculum adds

The research file (section 18) found no list titled "17 missing areas"; it reads the 17 as the `curriculum_gaps` of the
recheck evidence (`recheck/p3_craft.json`), the areas that needed external sources. Separately, 21 inventory items are
`missing` (of 78: 8 covered, 49 partial); they are plan items, listed in that file.

| # | area | where it lives now | what the sources support |
|---|---|---|---|
| 1 | screenwriting: the AI-register lexicon (N-15) | `narration-script`; CRAFT-SCR-01, -02; BP-114 | PARTIAL: LLM style-word drift (two arXiv papers); the word list and the density thresholds are NOT FOUND |
| 2 | sound: acoustic perspective and point of audition | `editing-style`; CRAFT-SND-10; BP-122 | NOT FOUND (Holman, Chion not re-opened) |
| 3 | sound: frequency masking under the voice | `editing-style`; CRAFT-SND-03; BP-118 | PARTIAL: EBU Tech 3343 on dialogue loudness; the EQ numbers NOT FOUND |
| 4 | sound: Murch's two and a half and the stereo field | `editing-style`; CRAFT-SND-07..09; BP-121 | SUPPORTED: Murch's essay (2.5 is the same-colour limit, 5 when spread; dialogue centred); the pan range NOT FOUND |
| 5 | music: leitmotif and tempo-to-cut | `editing-style`; CRAFT-SND-11, -12; BP-123 | PARTIAL: an article on the LOTR leitmotif essay; the beat tolerance NOT FOUND |
| 6 | the twelve principles of 2D animation | `animation-principles`; CRAFT-ANI-01..14; BP-132 | SUPPORTED: the list (Wikipedia on Thomas and Johnston); the cadences NOT FOUND |
| 7 | lip-sync and identity measurement | `animation-principles`; CRAFT-ANI-15, -16; BP-133 | SUPPORTED: SyncNet and ArcFace as methods, BT.1359 windows (secondary); the 80 ms and 0.65 numbers NOT FOUND |
| 8 | cartography design | `cartography`; CRAFT-CART-01..08; BP-124, BP-125 | SUPPORTED: Harrower 2003 (simple frames), ColorBrewer; PARTIAL: Imhof (secondary); the caps NOT FOUND |
| 9 | visual lane balance per topic | `shot-visuals`; CRAFT-CIN-10; BP-127 | SUPPORTED: YouTube Help 9314415 as the measurement tool; the 60/90 s caps are house numbers, not McKee or Katz |
| 10 | lens, camera height, composition | `shot-visuals`; CRAFT-CIN-01..06; BP-126 | SUPPORTED: the 30-degree rule; PARTIAL: low angle, the 85 mm class; composition NOT FOUND |
| 11 | the visual intensity curve | `shot-visuals`; CRAFT-CIN-09 | NOT FOUND (Block not re-opened) |
| 12 | editing: where a cut lands | `video-editing-architect`; CRAFT-EDC-01..04; BP-128 | SUPPORTED: the Rule of Six order and 51 %; cut-on-action frames and handles NOT FOUND |
| 13 | colour continuity | `video-editing-architect`; CRAFT-EDC-09..11; BP-130, BP-131 | PARTIAL: Reinhard colour transfer (search summaries); blend limit and delta-E band NOT FOUND |
| 14 | voice selection by measurement | `elevenlabs-voice`; CRAFT-VOX-02, -03, -08; BP-138 | SUPPORTED: Rodero 2020 for pace only; the casting margins NOT FOUND |
| 15 | packaging: three angles and the first-seconds promise | `shorts-for-video`; CRAFT-PKG-01..05; BP-135..137 | SUPPORTED: Test & Compare up to 3, key moments, Shorts up to three minutes; the mechanisms and gates NOT FOUND |
| 16 | Mayer's multimedia principles | `video-editing-architect`; CRAFT-MOG-05..15 | SUPPORTED: the list of twelve (Lucidea); the "embodiment" row is not supported as worded, it became the image principle |
| 17 | motion-graphics easing and HUD motion | `video-editing-architect`; CRAFT-MOG-01..04; BP-134 | PARTIAL: Material easing tokens seen only in search mirrors; the durations NOT FOUND |

## What would make a rule binding

The second source type is missing everywhere (research section 19): a **video** (type C) for every area, watched and noted;
a **book page or chapter** (type B) for Murch, Thomas and Johnston, Holman, Chion, Block, Mascelli, Katz, Dmytryk, Hullfish,
Van Hurkman, Brewer, MacEachren, Krasner, Mayer; and the **primary** of each secondary article (ITU-R BT.1359-1, Imhof 1975,
the Reinhard PDF, Harrower and Fabrikant 2008, Material motion tokens, Google's safe-zone PDF). When one arrives, the rule's
sources in `sourced_rules.json` gain it and the status moves under D-59; a FAIL also needs code that measures it.
