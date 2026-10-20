# Research: scene-based storytelling and editing (production_script/3, 2026-10-19)

This is the evidence home for the /3 rewrite: the SC scene rules, the DW rewrite, ST-12/ST-13 and the three beat
templates, the VB inversion (VB-01/02/08, VB-10/VB-11), MO-07, ED-14, the AL-02 change and the audio loop/variant
fixes. The rules themselves live in [STORY_ENGINE](../STORY_ENGINE.md) and [EDITING](../EDITING.md); this file holds
their sources and nothing else. Raw notes: `/home/user/research_notes/სთორითელინგის და მონტაჟის კვლევა/*.md`.

**What failed.** The internal audit of Syndicate Wars (notes, `internal_system_audit.md`) found all four visible
defects enforced by our own rules, not caused by bugs around them: a silent narration beat was a FAIL, so 414 cues
(~33/min) played with the same tone up to 4 times in one line; the schema had no scene object, so "dialogue" was 14
isolated quips in which heroes answer the narrator and no two heroes share a place; ER-07/RK-16 required source-citing
narration ("Rockstar's page says..."); and `story_lint` returned after one REVIEW when `drama` was missing, so the
script shipped with no premise, question or arcs. The /3 contract inverts this: nothing is included by default —
every scene turns a value (McKee), every cut has a reason (Murch), every sound maps to a story event, or it is deleted.

**Source rule (the creator's requirement).** Every new or changed rule below rests on at least 2 of 3 source types:
**(web)** a concrete internet source with URL; **(book)** a named book/author; **(yt)** a named YouTube channel/video
or a published interview with that editor. Where a number is our synthesis rather than a cited figure, the row says
**"engineering hypothesis; the channel's retention decides"** — that honest label is itself required, and the row still
names the nearest real sources. No number below is invented: each is either cited or labelled a hypothesis.

Recurring sources, abbreviated in the tables:
- (book) McKee, *Story*: ["Do Your Scenes Turn?"](https://mckeestory.com/do-your-scenes-turn/) (his own site);
  scene analysis per *Story* p.257 via [Evergreen](https://archives.evergreen.edu/webpages/curricular/2009-2010/writingmatters/2009/10/06/assignment-4-scene-analysis/index.html).
- (book) McKee, *Dialogue: The Art of Verbal Action*: chapter structure and conflict taxonomy via
  [ICPL](https://search.icpl.org/Record/1475711); "exposition as ammunition" via the
  [Gotham Writers Q&A](https://www.writingclasses.com/toolbox/author-q-a/robert-mckee).
- (book) Snyder, *Save the Cat*: 15 beats and percentage mapping via [FilmDaft](https://filmdaft.com/save-the-cat-beat-sheet/)
  and [StudioBinder](https://www.studiobinder.com/blog/what-is-save-the-cat-screenwriting/).
- (book) Storr, *The Science of Storytelling*: metaphor/concreteness via [Human Journey](https://humanjourney.us/library-book/the-science-of-storytelling);
  sacred flaw via [Volkov](https://angelavolkov.substack.com/p/a-flawed-model-of-the-world).
- (book) Murch, *In the Blink of an Eye*: Rule of Six via [UT Austin](https://cloud.wikis.utexas.edu/wiki/spaces/rtf318/pages/80022510/Murch+s+Rule+of+Six)
  and [FilmDaft](https://filmdaft.com/walter-murchs-rule-of-six-the-editors-formula-for-choosing-the-right-cut/); blink thesis via
  [Porchlight](https://www.porchlightbooks.com/product/in-the-blink-of-an-eye-a-perspective-on-film-editing--walter-murch/isbn/9781879505629);
  "Law of Two and a Half" via [Designing Sound](https://designingsound.org/2009/10/15/walter-murch-special-womb-tone-and-dense-clarityclear-density/).
- (book) Dancyger, *The Technique of Film and Video Editing* (rhythm, pacing, surprise):
  [Routledge](https://www.routledge.com/The-Technique-of-Film-and-Video-Editing-History-Theory-and-Practice/Dancyger/p/book/9781032859118).
- (yt) Murch interview: [BLDGBLOG](https://greg.org/2007/04/titius-has-a-po.html) (~14 new angles/min).
- (yt) HillierSmith (Streamy-winning YouTube editor): [Musicbed interview](https://www.musicbed.com/articles/?p=7556).
- (yt) Sven Pape, This Guy Edits: [NoFilmSchool summary](https://nofilmschool.com/2018/02/7-simple-editing-tips-will-help-you-edit-pro),
  [Busyboy summary](https://www.busyboyproductions.com/?p=13076).
- (yt) Mario Joos (ex-MrBeast retention strategist): [Vidpros account](https://vidpros.com/retention-editing-what-you-can-learn-from-mario-joos/);
  MrBeast's own 2024 slowdown: [Gigazine on the Washington Post piece](https://gigazine.net/gsc_news/en/20240403-retention-editing-beastification-may-be-end).
- (yt) Trey Parker, NYU masterclass ("but/therefore"), via [The Hustle](https://thehustle.co/storytelling-secrets-netted-matt-stone-trey-parker-600-million).
- (web) Antony Johnston, [Scene Writing 101](https://antonyjohnston.com/forwriters/scenewriting101.php).
- (web) John August, [Scriptnotes transcript](https://johnaugust.com/?p=14759).
- (web) [Autonolab three-act guide](https://blog.autonolab.com/blog/2025-08-21-the-three-act-structure-for-youtube-storytelling-that-retains/);
  (web) [AIR Media-Tech retention patterns](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8);
  (web) [Pixflow retention guide](https://pixflow.net/blog/?p=93140).

Film Booth (Ed Lawrence) was searched for as asked: no written version of his frameworks surfaced, only podcast pages
noting he teaches story and "editing as a content retention strategy"
([Creator Science](https://podcast.creatorscience.com/ed-lawrence/)) — so no rule below rests on him.

## SC-01..SC-10 — scenes and dialogue (home: STORY_ENGINE.md; code scripting/scene_lint.py, PV-48, /3 only)

| Rule | Numbers | Sources |
|---|---|---|
| SC-01 scene header required and complete on dialogue segments | all fields of the `scene` object; pov/present in cast | (book) McKee *Story* value/charge analysis; (web) Johnston's 8 questions (want, stopping, turn, contrast, thinking, unsaid, say less, set-up) |
| SC-02 the scene turns: open_charge != close_charge, `turn` names the beat | FAIL | (book) McKee: unchanged charge = "nonevent", cut it ([Do Your Scenes Turn?](https://mckeestory.com/do-your-scenes-turn/)); (web) [Writers Helping Writers](https://writershelpingwriters.net/2023/12/scene-mastery-navigating-common-goal-driven-scene-pitfalls/) turning-point types |
| SC-03 opposing wants: want != obstacle_want, both concrete | FAIL | (web) August: explaining = "a meeting", no conflict no drama; (book) McKee *Dialogue*: desire + tactic under every line ([Big Ben Comedy](https://www.bigbencomedy.com/archives/tag/dialogue/)) |
| SC-04 every line addressed (`to` in present \| self \| room); a hero never talks to the narrator | FAIL | (book) McKee *Story*: a scene is action through conflict between present characters; (web) Johnston: someone PRESENT opposes the want. The fourth-wall split is our fix for the audit's hero-answers-narrator failure |
| SC-05 a real exchange: ≥2 present → one run of ≥4 consecutive character lines (≥2 speakers, no narrator inside); every present character speaks or reacts | FAIL / REVIEW | (book) McKee beat budget: the model *Casablanca* scene runs ~11 action→reaction beats ([Wikipedia](https://en.wikipedia.org/wiki/Beat_(filmmaking)), Evergreen); (web) [Pixar rule 13](https://laughingsquid.com/22-rules-of-storytelling-by-pixar-storyboard-artist/): passive characters are "poison" |
| SC-06 enter late, leave early: no greeting opener, no wrap-up closer | REVIEW | (web) [No Film School](https://nofilmschool.com/start-late-leave-early) / [Scott Myers](https://movieintheair.com/wp-content/uploads/2022/06/Screenwriting-Mantra-Enter-Late-Exit-Early-by-Scott-Myers-Jun-2022-Go-Into-The-Story.pdf) (Goldman/Field/Mamet maxim, cut-from-the-top test); (yt) Pape: "come late, leave early" in the edit too |
| SC-07 no press-release register in narration ("X's page says", "announced", "is set to release"...) | FAIL on /3; dates/specs only inside a scene as stakes | (book) McKee: "skill in exposition means making it invisible" ([NOWW](https://www.nowwwriters.ca/noww-blog/dialogue-shouldnt-say-it-out-loud)); (web) [Arc Studio](https://www.arcstudiopro.com/blog/the-dangers-of-expository-dialogue), [Somers "as you know"](https://www.jeffreysomers.com/blather/?p=5512); (web) [OutlierKit](https://outlierkit.com/channel/crimelensmedia1): breakouts are contradiction-led, not recaps |
| SC-08 one honesty beat: disclaimer phrases in ONE segment (+ ≤1 callback); >2 segments FAIL | FAIL on /3 | (book) McKee: pure-information scenes get cut, the facts move; (web) AIR: cold opens that explain give an exit within 20 s. Consolidation into one beat + on-screen labels + description is an **engineering hypothesis; the channel's retention decides** (ST-09's duty stays satisfied) |
| SC-09 turn-taking: line >35 words FAIL; >15 words REVIEW unless the scene's one `speech`; ≤1 turn of ≥25 words per scene; >3 consecutive "?" turns REVIEW | 35 / 15 / 25 / 3 | (web) [Follows](https://stephenfollows.com/p/are-movies-becoming-more-simplistic): line verbosity falls for 80 years; (yt) [Tarantino/Jackson, MovieMaker interview](https://www.moviemaker.com/first-draft-mastering-the-art-of-conversation/): rhythm from short repeated beats. Exact word counts are an **engineering hypothesis; the channel's retention decides** |
| SC-10 subtext: surface_topic + real_subject declared (REVIEW if absent); a line stating real_subject verbatim FAILs | FAIL / REVIEW | (book) McKee *Dialogue*: verbal action hides the real fight; (web) [Final Draft](https://www.finaldraft.com/blog/mastering-subtext-in-screenwriting), [The Write Practice](https://thewritepractice.com/subtext-examples/): on-the-nose = speaking the subtext, the canonical failure |

## ST additions: ST-00 (FAIL), ST-12, ST-13, and the three templates (home: STORY_ENGINE.md)

| Rule | Numbers | Sources |
|---|---|---|
| ST-00 on /3: missing `drama` is a FAIL (was REVIEW) | — | (book) McKee: no scene (or script) without a value at stake; (web) Autonolab: the named failure modes (sagging middle, no central question) all start from a missing spine. Trigger: Syndicate Wars shipped without one (audit §0.1) |
| ST-12 midpoint placement: the midpoint/reversal segment at 40–60 % of the script's words (REVIEW, ≥8 segments) | 40–60 % | (web) Autonolab: midpoint at 50 % must be a real pivot, timestamp within 45–55 %; (book) Snyder: Midpoint = 50 %, a false victory or false defeat. The word-share proxy (40–60 %) is an **engineering hypothesis; the channel's retention decides** |
| ST-13 turn cadence: no stretch between hook and resolution longer than ~150 s (at 2.5 words/s) without a turn-function segment or drama.turn "but" | ~150 s | (web) Autonolab: retention spikes at sequence transitions every 2–4 min, "dead zone" test; (web) [Subscribr](https://subscribr.ai/p/true-crime-youtube-video-ideas): a reveal every ~2 min; (book) Snyder via FilmDaft: stakes rise every 10–15 % of runtime |

**The three beat templates** (replace the old beat grid; one validator, times for 10:00, scale by length):

| Template | Shape | Sources |
|---|---|---|
| A. Three-act / 7-point (default) | hook 0:00–0:15 (core tension inside 15 s), stakes by 0:45, inciting ~1:00, central question by 1:30, 3–5 escalating sequences with pinches ~2:30 / ~7:30, midpoint pivot 45–55 %, low point + decision 7:30–9:00, climax 9:00–9:30, mirror-the-opening button ≤30 s after the answer | (web) Autonolab (the full timed table); (web) [OverseerOS](https://www.overseeros.com/blog/youtube-hook-framework-7-openings-that-keep-viewers-watching): tension within 10–15 s, "still setting up context at 20 seconds is too long" |
| B. Save-the-Cat compressed | percent-mapped: catalyst ~11 %, midpoint 50 %, all-is-lost ~75 %, break-into-three ~80 % | (book) Snyder (Catalyst at page 12/110 ≈ 11 %); (web) FilmDaft porting rule (position = beat % × length, guardrails not laws). Only ~11 % and 50 % are source-confirmed; the rest is community convention, so labelled |
| C. Mystery reveal ladder | cold-open contradiction, a reframing reveal every ~2:00, chronology written BEFORE suspense | (web) Subscribr true-crime (reveals ~2-min spaced; chronology first so the hook cannot distort facts); (book) Storr/Loewenstein: curiosity = a specific, closeable gap ([Golman & Loewenstein](https://www.cmu.edu/dietrich/sds/docs/golman/golman_loewenstein_curiosity.pdf), Human Journey) |

Checks regardless of template: stakes strictly escalate per sequence (web Autonolab; book Snyder); the central question
is never answered before ~85 % (web Autonolab: "early over-resolution" is a named exit trigger); the final image
mirrors the opening image's subject (book Snyder: Final Image mirrors Opening Image). Scene-to-scene joins stay
but/therefore, never and-then ((yt) Parker NYU class via The Hustle) — ST-02 unchanged.

## DW rewrite (home: STORY_ENGINE.md; encoded parts in scene_lint)

| Rule | Numbers | Sources |
|---|---|---|
| DW-01 conflict (encoded via SC-03/SC-05); two heroes never agree >2 lines in a row | 2 | (web) August: conflict = different wants; (book) McKee *Dialogue* forces of antagonism |
| DW-02 enter late leave early (encoded SC-06) | — | see SC-06 |
| DW-04 subtext (encoded SC-10) | — | see SC-10 |
| DW-05 a reaction after every reveal: a "reveal" line is followed by another character's line or a listener expression beat | REVIEW | (web) [FilmDaft L/J cuts](https://filmdaft.com/the-l-cut-and-j-cut-how-film-editors-use-audio-to-control-time/): show the words landing on the hearer; (yt) Pape / (web) [Artlist Kuleshov](https://artlist.io/blog/kuleshov-effect-or-how-an-editor-shapes-and-strengthens-an-actors-performance/): the reaction's meaning is made by juxtaposition |
| DW-06 turn length: default 5–15 words, hard cap 35, one 25–60-word speech per scene at its peak | 5–15 / 35 / 25–60 | (web) Follows verbosity decline; (yt) Sorkin interview via [No Film School](https://nofilmschool.com/interruptions-dialogue): dialogue as music, "rhythm, beats, rests". Exact bands are an **engineering hypothesis; the channel's retention decides** |
| DW-09 softened: the learner-corrected scene is ONE conflict mode among balanced/asymmetric/indirect/comic/minimal, varied across the episode | — | (book) McKee *Dialogue*: conflict case studies = balanced, comic, asymmetric, indirect, minimal (ICPL record); (web) Johnston Q4: contrast — a rational debate instead of a shouting match. The Chi 2017 learner evidence stays, scoped to one mode |
| DW-12 (new): ≤3 clean question→answer pairs in a row; ≥2 non-direct responses per scene (deflect, question back, silence, counterattack) | 3 / 2, REVIEW | (web) [ScriptShadow](https://scriptshadow.net/ten-quick-dialogue-hacks/): questions may hang or be ignored; (book) Sol Stein's deflection forms ([Goodreads author blog](https://www.goodreads.com/author_blog_posts/15720529-deflection-in-dialogue)) |
| DW-13 (new): exposition as ammunition — K/K facts only as weapons/stakes, U/U facts to the narrator; ~1 dialogue-borne fact per 2–3 beats | 1 per 2–3 beats | (book) McKee: "convert exposition to ammunition" (Gotham Q&A); (web) Arc Studio: the "no audience watching" test; (web) August: encode information into dramatic scenes. The ration is an **engineering hypothesis; the channel's retention decides** |

Supporting craft the skills teach (same source rule): the narrator↔scene hand-off unit and the ~40–60 % narration /
scene every 60–90 s split — (web) [Bold Content](https://boldcontentvideo.com/the-animation-process-script-writing/)
(voice switch = re-engagement; ~150–225 wpm), (book) McKee/August (play the conflicts, narrate the facts) — the split
itself is a **labelled hypothesis** (no retention data compares formats; notes `dialogue_craft.md` §6). Voice bibles —
(web) [Wikipedia, Bible (screenwriting)](https://en.wikipedia.org/wiki/Bible_(screenwriting)) (Roddenberry's 1967 guide
told writers HOW THE CHARACTERS SPOKE); (web) Pixar rule 13; the ~80 % cover-the-names threshold is an
**engineering hypothesis**. Scripted silence 1.5–3 s vs 0.4–0.8 s normal gaps, interruptions as a dash + ≤0.1 s gap —
(yt) Sorkin ("I script all of it", em dashes), (web) No Film School interruptions; timings are **engineering
hypotheses** (no produced-script timing data exists).

## VB changes on /3 (home: STORY_ENGINE.md; code production/beats.py)

| Rule | Numbers | Sources |
|---|---|---|
| VB-01 /3: the 1.5 s metronome is retired; pacing follows NEW INFORMATION. While the narrator speaks: REVIEW >8 s with nothing new, FAIL >15 s (MO-01's 5 s dead-air REVIEW stays). Guidance: hook/climax an event every 3–8 s, body 10–25 s, one pattern interrupt at 25–35 s of the hook | 8 / 15; 3–8 / 10–25; 25–35 s | (yt) Joos: "It's not the cutting speed, it's the speed at which you introduce progressive novel information"; (yt) MrBeast slowed 38→23 cuts/min in 2024 and views "skyrocketed" (Gigazine); (web) AIR: hook every 10–20 s then 25–40 s, over-editing lowers retention for 25+; (web) Pixflow: interrupt at 25–35 s. The 8/15 s gates are an **engineering hypothesis; the channel's retention decides** |
| VB-02 /3: every dialogue line still needs ≥1 expression change (FAIL if none); the 1 s metronome is retired: REVIEW >4 s without a change, FAIL >6 s; flicker cap: two changes of one face <0.7 s apart REVIEW; on a "reveal" line prefer the LISTENER's face (who != speaker) | 4 / 6 / 0.7 | (web) Artlist Kuleshov: the same face reads by what it is cut against; (yt) Pape: a hidden/neutral face lets the viewer project the emotion. No published expression-cadence numbers exist (notes `youtube_editing_practice.md` §2 gap): 4/6/0.7 s are an **engineering hypothesis; the channel's retention decides** |
| VB-08 /3 INVERTED: a silent beat is the default and never a finding; a cue REQUIRES `event` (reveal \| impact \| transition \| build \| diegetic \| take \| place); a cue with no event FAILs. Duration/level/no-doubling rules stay | — | (web) [Sonilo](https://sonilo.com/blog/guides/transition-effect-sound-video-edits): subtractive test, "more connected with the sound than without it? no → delete"; a whoosh on every cut = "a slideshow that really wanted your attention"; (web) [Krotos](https://krotos.studio/blog/film-sound-design): choosing which hits to KEEP is the job; (book) Murch: encoded–embodied spectrum, every sound classifiable (Designing Sound) |
| VB-10 (new): same cue sound on two consecutive cues REVIEW; 3+ times within 30 s FAIL; the mixer auto-varies playback (3 deterministic pitch variants, round-robin per sound) | 2 / 3 / 30 s; 3 variants | (web) [IRPR](https://sounddesign.irpr.agency/solutions/game-audio-repetitive/) / [Bugnet](https://bugnet.io/blog/how-to-fix-unity-sfx-sounds-identical-every-play-no-variation): the "machine gun effect" — an identical sample back-to-back reads as a bug; keep 3–5 variants, shuffle without immediate repeat; (yt) HillierSmith: strip the language away so its return feels earned ("less is more"). The 30 s window is an **engineering hypothesis** |
| VB-11 (new): density — >8 cues/min REVIEW, >14/min FAIL; >3 cues in any 10 s REVIEW; emphasis cues (thud, chime, rise, fall) ≤1 per line (FAIL); cues count toward AL-02 | 8 / 14 / 3-in-10 s / 1 | (book) Murch's Law of Two and a Half: >~2.5 similar layers turns the mix to mud (Designing Sound); (web) Pixflow: "viewers over 35 retain worse when every sentence has a zoom and a whoosh"; (web) AIR: "if every subtitle pops, your video feels over-processed". No published cues-per-minute figure exists (notes `audio_cues.md` §3): 8/14 are an **engineering hypothesis; the channel's retention decides**. Syndicate Wars measured ~33/min (audit §3.1) |

**Cue event grammar** (what each `event` is for): diegetic ↔ a visible on-screen action; impact ↔ a reveal/punchline
beat the edit declares important; build (riser) ↔ anticipation, ending exactly ON the reveal frame; transition
(whoosh) ↔ a fast camera move or scene change; place (ambience change) ↔ a location change; take ↔ the one big
expression a line; reveal (sting) ↔ an emotional turn. Sources: (web)
[Routenote](https://licensing.routenote.com/blog/?p=9534) / [Morphic](https://morphic.com/resources/sounds/whoosh-sound-effect)
taxonomy; (web) [Violet Recording](https://violetrecording.com/sound-design-for-trailers/): "time your risers so their
peak lands exactly on the impact", near-silence before a hit multiplies it; (book) Murch encoded–embodied spectrum.

## MO-07 — rhythm is variance (home: STORY_ENGINE.md; code edit/motion_lint.py)

| Rule | Numbers | Sources |
|---|---|---|
| MO-07: >3 consecutive shot holds within ±15 % of each other REVIEW; a segment of ≥5 shots with hold-length CV < 0.2 REVIEW | 3 / ±15 % / CV 0.2 | (web) David Bordwell's statistical analysis via [16:9](https://16-9.dk/?p=24578): scene-to-scene tempo contrast is what modern films exploit; (web) [FilmDaft rhythmic editing](https://filmdaft.com/rhythmic-editing-how-cut-timing-controls-the-audience/) / [ProVideo Coalition](https://www.provideocoalition.com/pacing-and-rhythm-in-editing/): a constant tempo (even cutting on every beat) "gets really monotonous"; (book) Dancyger: rhythm and pacing as central craft, a chapter on surprise. The ±15 % and CV 0.2 thresholds are an **engineering hypothesis; the channel's retention decides** |

## ED-14 — dialogue coverage grammar (home: EDITING.md; editorial, code to be built like ED-09)

| Part | Numbers | Sources |
|---|---|---|
| Open a scene on an establishing/two-shot | 2–4 s | (web) [How to Film School](https://howtofilmschool.com/dictionary/shot-reverse-shot/): establishing → coverage is the classical pattern; (book) Murch: 3D spatial continuity (the room stays clear) |
| Listener's reaction on every 2nd–4th line and on news/insult/revelation | 2–4 | (web) FilmDaft/[SpotlightFX](https://spotlightfx.com/blog/what-are-j-cuts-and-l-cuts-professional-dialogue-editing-explained): words land on the hearer's face; (yt) Pape + (web) Artlist Kuleshov. "Every 2nd–4th" is an **engineering hypothesis** (no published frequency exists) |
| Never >4 strict A/B alternations without a pattern break | 4 | (web) FilmDaft: "ping pong" is the named monotony failure; (book) Dancyger: schedule surprise. The count 4 is an **engineering hypothesis** |
| J/L cuts: audio leads or trails the picture by 0.5–2 s on about a third of scene cuts | 0.5–2 s / ~1/3 | (web) [Premiumbeat](https://www.premiumbeat.com/blog/what-is-j-cut-and-l-cut-in-video-editing/) / [Epidemic Sound](https://www.epidemicsound.com/blog/j-cuts-and-l-cuts/): split edits, invisible when done well; (yt) Murch (BLDGBLOG): sound and picture boundaries interleave. Offsets/share are **engineering hypotheses** |
| Hold bands: dialogue 3–6 s, action 1.5–3 s, contemplative 6–12 s — labelled hypotheses | 3–6 / 1.5–3 / 6–12 s | (web) 16:9 / [Follows](https://stephenfollows.com/many-shots-average-movie/): ASL data (2007 US mean 2.5 s; action ~25 cuts/min; horror ~15.7 s); (book) Murch blink thesis: cut where the thought completes (clause end + 0–400 ms). The bands are an **engineering hypothesis; the channel's retention decides** (no stills-pipeline data exists) |
| ≤14 never-before-seen framings per minute; reused framings are free (also the image budget) | 14 | (yt) Murch, BLDGBLOG interview: ~14 untemplated angles/min keeps action "thrilling yet comprehensible", repeated angles process faster; (book) Murch, *In the Blink of an Eye* (the comprehension argument) |
| One music track per story chapter (2–4 changes per 10 min), changed only when the emotion changes; ONE planned full dropout of 0.5–2 s before the biggest reveal, broken by an intentional sound | 2–4 / 0.5–2 s / 1 | (yt) HillierSmith: note the emotions, one feel per chapter, strip it for the gravest moment; (web) AIR: change tracks when the story shifts, ~1 s strategic silence; (web) Violet: "dropping everything out for a beat makes the next impact feel enormous". The dropout cap of one per video is an **engineering hypothesis** (The Last Jedi's 10 s silence read as a malfunction — [Pedestrian.tv](https://www.pedestrian.tv/film-tv/theatres-warning-punters-last-jedi/)) |

## AL-02 (changed; code audio/layers.py)

| Rule | Numbers | Sources |
|---|---|---|
| Effects AND cues count: 4–20 sound events a minute | 4–20 | (book) Murch 2.5-layer limit (the cap's shape: restraint); (web) AIR/Pixflow over-processing warnings. The audit found AL-02 counted effects only, so 33 cues/min passed unseen (audit §0.3). The 4–20 band predates /3 and stays an **engineering hypothesis** |

## Audio loop/variant fixes (code sfx_manifest.schema.json, assemble.py, shorts.py, audio/cues.py, timing)

These close the audit's "one press → many sounds" mechanisms (audit §3.3 A–F). They are defect fixes, each still
double-sourced:

| Fix | Sources |
|---|---|
| Manifest items gain `loop` (bool) and `intended_seconds`; a one-shot is never looped by `loop_to`, and Shorts never give it `-stream_loop -1`. Trigger: `reveal_sting__v1` prompted as "one clean ~4 s hit", stored 30.772 s as music | (web) [Bugnet FMOD](https://bugnet.io/blog/how-to-fix-fmod-round-robin-container-repeats-same-sample): a reset container replays the same sample — state must persist; (book) Murch: a repeated identical element reads as one mechanical layer (Law of 2.5 corollary) |
| `audio/cues.py` renders 3 deterministic pitch variants per cue (1.0 / 0.94 / 1.06); the cue bus round-robins them, so two consecutive plays of one sound are never the identical sample | (web) Bugnet Unity: 3–5 variants, pitch ~±5 %, pick avoiding the last used; (web) IRPR "machine gun effect"; (yt) HillierSmith restraint-and-variation. 0.94/1.06 sit inside the cited ±5–6 % band |
| Timing de-stack: two beats landing on the same word instant (unmatched-token fallback) collapse to the first; the dropped one is reported (REVIEW), not stacked into a doubled sound | (web) [Netflix Backlot](https://backlothelp.netflix.com/hc/en-us/articles/115000533952-Sync-Effects): ≥2 frames off is reportable — stacked cues cannot all be in sync; (web) [Beverly Boy](https://beverlyboy.com/blog/transition-sound-design-that-strengthens-commercial-video-editing): pros offset layers by frames, never stack peaks on one instant |
| Ambience is a property of the LOCATION: one bed per place, reused on returns, pre-lap 0.5–2 s, crossfade at boundaries; a mid-scene bed change needs a declared acoustic story event | (web) [Morphic ambience](https://morphic.com/ai-glossary/ambience) / [Beverly Boy room tone](https://beverlyboy.com/filmmaking/what-is-room-tone-in-film/): one continuous bed = one place; (web) [StudioBinder J-cut](https://www.studiobinder.com/blog/what-is-a-j-cut/): pre-lap the new location's sound. Pre-lap length 0.5–2 s is an **engineering hypothesis** |

## What is NOT claimed

No public dataset ties any number above to retention for 8–12 min animated story video. Every band and cap is a
practitioner default or our synthesis, labelled where so, and the channel's own retention curves are the arbiter —
the same discipline D-49's parameter audit applied to the /2 numbers. One counterweight on record: some long,
unedited videos outperform "optimized" ones — substance drives, style supports
((web) Gigazine quoting consultant Noah Kettle; (web) [Descript](https://descript.com/blog/article/advice-for-video-editors-from-youtube-video-editors):
effects do not fix a weak story).
