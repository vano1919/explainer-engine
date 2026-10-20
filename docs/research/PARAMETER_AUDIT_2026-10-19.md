# Parameter audit against evidence (2026-10-19)

The creator's ask: check every parameter from the first word to the final edit against what the best videos do and what
research and official sources say; break the Shorts down by type and stage; then change the rules where there is
confirmed evidence that something else works better. The rules are ours, so they can change.

How to read the verdicts:
- **holds**: a study, a standard or an official platform page supports the value.
- **changed**: evidence pointed elsewhere, and the rule now says so (the change is listed in the last section).
- **hypothesis**: no evidence for or against; the value is our choice and is measured on our own videos.
- **refuted as evidence**: the number came from advice without data; it stays only if we choose it as a hypothesis.

Evidence kinds: **study** (peer-reviewed), **meta** (meta-analysis), **data** (a large log analysis with a stated method),
**official** (YouTube, ElevenLabs, EBU, Netflix), **practice** (a named practitioner), **vidIQ** (one video analysed by
vidIQ), **blog** (advice without data). Three research workers collected the sources on 2026-10-19; the full source lists are
at the end. [STORY_EDIT_VOICE_2026-10-19](STORY_EDIT_VOICE_2026-10-19.md) holds the earlier, adversarially verified run.

## 0. The creator's own channel (vidIQ, 2026-10-19)

CrossWorld Chronicles (2 subscribers, 6 videos, published 2026-10-17/18): the long video 4Ut2oPgiraw (17:09) has 53 views;
five Shorts (27-36 s) have 529-1,148 views and 5-12 likes each, which is **0.4-1.0 % likes per view**. Benchmarks for
short-form (OverseerOS, Aug 2026, 2,251 videos, (likes+comments)/views): median 2.71 %, channels under 10k subscribers
median 1.71 %, 90th percentile 6.67 %. Animated what-if breakouts in our niche (vidIQ outliers, channels ≤ 50k): 1.8-5.1 %.
So the creator's "20 % engagement" cannot be likes per view; it is most likely *viewed vs swiped away* or *average
percentage viewed* in Studio (creator advice without data puts a healthy viewed-vs-swiped at 70-80 %; YouTube publishes no
benchmark and compares only with the channel's own typical performance). **Answered by the creator (2026-10-19): it is
viewed vs swiped away, about 80 % viewed and 20 % swiped away.** So the hook holds and the Shorts lose people in the middle:
the low likes per view and the 1.4 changes every 10 s point at the body, which now carries the visual-beat layer (SS-09 in
[STORY_ENGINE](../STORY_ENGINE.md)). YouTube Analytics for these videos was empty on 2026-10-19 (the data lags about two
days); the retention curves are read after 2026-10-21.

vidIQ scene analyses of two of the Shorts (5kUfczk30AM, the best; _UrjFke0Sgc, the weakest):
- 1 cut every 7 s (4-5 scenes in 28-36 s); the first picture holds 4-8 s; every picture is a still with a slow zoom.
- the hook question is complete at 2.5-3.5 s; captions start at 0 s in 2-3-word chunks, no word highlight; no loop; the
  pointer line "The full story is on the channel" closes both.
- vidIQ's swipe risks in the first 3 s: a static picture, a concept-heavy hook ("explode seven pots in a row"), and 4-8 s
  on one picture before a character or an action.

Breakout animated what-if Shorts in the same search (Hour Seven 100 s, Zaylen 66 s, PureFocus 54 s, thus spoke cef 65 s,
Brainhub 38 s) run 38-100 s, 3-6 changes every 10 s (the three watched on 2026-10-19), a HUD counter, word-highlight
captions and a cliffhanger or question ending. Ours are 27-36 s with 1.4 changes every 10 s.

## 1. Words and story

| Parameter | Our rule | Evidence | Verdict |
|---|---|---|---|
| Heard pace | 155 wpm (P-52), 155-175 (PRODUCTION_RULES), 140-175 accepted (EL-12) | Guo, Kim & Rubin 2014 (data, 6.9 M sessions): engagement rises with speaking rate, "don't slow down"; Rodero 2020 (study, N=200, audio ads): 180 wpm best for attention, arousal and recall, 200 worse; Murphy 2022 (study, N=231): comprehension holds to about 330 wpm; ACX: audiobooks about 155 wpm; BBC bulletins 168 measured, radio texts recommend 160-180 (Rodero 2012) | **changed**: target 170 wpm, accepted 155-185 |
| Sentence length | mostly 4-12 words, under 22 (N-05); 8-18 (P-35) | no study on spoken sentence length for video; radio practice favours short sentences | hypothesis (kept) |
| Conversational style, "you" | contractions (N rules) | Mayer 2014 personalization: d = 0.79 (14 of 17 tests); Ginns, Martin & Marsh 2013 (meta): retention d = 0.30, transfer d = 0.54, the effect fades in lessons over 35 min | holds; **added DW-10**: the narrator addresses the viewer as "you" |
| Questions | one per 150 words (N-06); the hook is a question within 5 s (N-01, UR-01) | Murphy 2020 (study, Gruber lab): a curiosity question boosts memory for what comes 2 s after it; the boost is gone by 6-8 s. Frede 2026 (study, 2 preregistered experiments): showing a partial knowledge gap raised reading odds 3-8x, a total gap or no gap did not. YouTube Help 9314415: only the first 30 s and gradual declines are named, no question rule | holds; **added ST-11**: a question that is not a declared loop is answered within seconds; the hook names what the viewer already knows and what they do not |
| Open loops every 2-3 min, stakes every 60-90 s | ST-05, beat grid | no experiment on cliffhangers in educational video; blog numbers refuted in the earlier run | hypothesis |
| Story over exposition | the ST layer, D-48 | Mar et al. 2021 (meta, 150 effect sizes, N = 33,078): narrative beats expository, g = 0.55 overall, memory g = 0.72, listening g = 0.61; Dahlstrom 2014 (PNAS review): narratives read about twice as fast and are recalled about twice as well, with an accuracy risk | **holds (strong)** |
| But/therefore | ST-02 | Parker and Stone (practice, 2011 NYU class) | holds as craft; no measurement |
| Dialogue between heroes | DW-01 dialogue is conflict | Chi, Kang & Yaghmourian 2017 (study, N = 40): observers of tutor-tutee dialogue gained on transfer (d = 1.08) where monologue did not; Qian, Hong & Chi 2024 (study, N = 416 and 74): dialogue videos beat monologue, mostly on inference questions, and work for solo viewers. The dialogue in both is a learner who errs and is corrected, not two experts bantering | **changed: added DW-09**, one hero is the learner who guesses wrong and is corrected on each key fact |
| Humour | ≤ 1 verbal joke / 60 s (P-05); humour from situation, never a false fact (DW-07, UR-21) | Bolkan, Griffin & Goodboy 2018 (study, N = 87 + 93): humorous examples integrated into the explanation cut exam scores 13-17 %; humour beside the content is neutral to positive for mood; Zhou & Lee 2025 (study, N = 25): related humour helped recall and motivation, small sample | **changed: DW-07 tightened**: a joke never carries the explanation; the fact is said straight, the joke is the reaction to it |
| Segments of 40-90 s, period cards | ED-09, beat grid | Mayer & Pilegard 2014 segmenting d = 0.79 (10 of 10 tests); Rey et al. 2019 (meta, 56 studies): small to medium effect on retention and transfer; signaling: Alpizar, Adesope & Wong 2020 (meta, 29 studies, N = 2,726) d = 0.38 | holds (strong) |
| Objectivity labels | ST-09 fact / reasoned / invented | Dahlstrom 2014: narrative persuades even when known to be fiction, so accuracy must be guarded; Kurzgesagt's own process (sources, expert review, source sheet) | holds |
| The 6-minute rule | not a rule of ours | Guo 2014 (MOOC data): median engagement ≤ 6 min; Lagerstrom 2015: "the six-minute rule does not capture the full truth"; voluntary YouTube viewing is a different setting | not adopted |

## 2. Performance and voice

| Parameter | Our rule | Evidence | Verdict |
|---|---|---|---|
| Tags per line | ≤ 2 (PF-01), few and plain (EL-05) | ElevenLabs audio-tags list (official, 2026-10-15): "use one tag per clause"; prompting guide: prompts over 250 characters, Creative/Natural stability for tags | holds |
| One stressed word, last in the sentence | PF-02, N-04, EL-06 | no study found; broadcast practice | hypothesis |
| Pause before a reveal 0.4-0.8 s, after a punchline 0.3-0.6 s | PF-03, P-53 | Van Loon 2000 (study, L2 listeners): 500 ms pauses at syntactic junctures aided comprehension; Attardo & Pickering 2011 (study, 20 joke performances): **no evidence that punchlines are preceded by pauses**; de Diego-Balaguer 2015: even 25 ms pauses aid segmentation | **changed wording**: 0.5 s before a reveal (weak), the punchline pause is a style choice, not a rule |
| Interjections | PF-04 ≤ 1 in 5 lines a speaker | no study | hypothesis |
| Voice casting from traits, no imitation | VC-01, VC-02, PV-10 | ElevenLabs Voice Design docs (official): the structured template; Prohibited Use Policy (updated 2026-10-09): impersonation section; No-go voices (official): clones of prominent figures are restricted; the Voice Library has **no "famous" category** today (licensed famous voices live in the separate Iconic Marketplace) | holds; the "famous category" check in `audio/casting.py` is harmless and now documented as a guard against a marketplace listing |
| Human voice vs TTS | ElevenLabs v4 | Mayer 2014 voice principle d = 0.74, tested with old TTS; relevance to today's voices unknown | no verdict |

## 3. Picture, motion and cut

| Parameter | Our rule | Evidence | Verdict |
|---|---|---|---|
| A visual event at most every 5 s (MO-01); a cut or bubble at least every 9 s (UR-31) | ours | Cutting et al. 2011 (study, 160 films): average shot length fell from about 10 s (1930s-40s) to under 4 s after 2000; Lang et al. 2000 (study, TV): arousal, attention and memory **rose** with edit rate (cuts trigger orienting responses), no per-minute number; Kim, Guo et al. 2014 (data, edX): 61 % of rewind peaks sit next to a visual transition, "avoid abrupt visual transitions"; Gritz et al. 2025 (data, 8,180 sessions): a new **text** element predicts pauses, rewinds and dropouts, a new picture does not; YouTube Help 9314415: no N-seconds rule | **hypothesis, kept at 5 s**: cuts and motion do hold attention (Lang), no study fixes a number; the "3-5 s" and "5-10 s" blog rules are refuted as evidence; the defensible floor is no motionless still beyond the classic 10 s |
| Variety of events, ≥ 3 kinds a minute (MO-02); half the shots alive (MO-06) | ours, from Episode 1 (4 % alive) | Lang 2000 (orienting responses to change); Kurzgesagt and Infographics watches (vidIQ): 85 % of scenes with continuous motion, 2.5-4 s changes | holds as the measured gap between Episode 1 and the breakouts |
| Whips and flashes only at story turns (MO-04, ED-04) | ours | Kim 2014: abrupt transitions are where viewers rewind or leave; Kurzgesagt watch: transitions motivated, no dissolves | holds |
| Words on screen ≤ 4, 12 s apart (MO-05); label hold ≥ 1.5 s + 0.3 s per word (P-71) | ours | Mayer signaling d ≈ 0.4 (keywords help), redundancy d ≈ 0.86 (narrating on-screen sentences verbatim hurts); Gritz 2025: every new text element is a pause or dropout trigger; Dolić 2024 (study, N = 60, weak): animated text at 120 wpm worst, 90 wpm most attractive | holds; **changed: pop/slam text hold follows P-71** (`accents.text_hold`: 1.5 s + 0.3 s a word; the fixed 1.6 s was too short for 4 words) |
| Dangerous beats 3-5 s, wonder 7-9 s (ED-05); shot ranges A 5-7, B 3.5-5, C 2.5-4 s (UR-11) | creator's style | film shot-length data only; no explainer measurement | hypothesis |
| ≤ 10 pictures a minute, no shot under 2.5 s (UR-31) | creator, after v5's 14.3 a minute | no study; the breakouts change faster but with motion inside one picture | hypothesis (kept; motion inside the picture is the lever, MO-06) |
| Data visuals every period (ED-10) | ours | Mayer signaling; Infographics watch: spec info-dumps were the weak spots, so a visual carries the arithmetic | holds |
| Burned captions on Shorts, sidecar on long-form (P-18) | ours | Verizon/Publicis 2019 survey (5,616 US adults): 69 % watch muted in public, 25 % at home; Mayer redundancy: on-screen sentences identical to narration hurt learning, so long-form keeps captions optional | holds |

## 4. Sound

| Parameter | Our rule | Evidence | Verdict |
|---|---|---|---|
| Mix −14 LUFS ± 1, true peak ≤ −1 dBTP (P-90, P-91) | ours | YouTube Help 14106294 / 16619284: "Stable volume" on by default, **no LUFS target published**; Youlean 2020 (measurement): about −14 LUFS, louder uploads turned down, quieter not raised; AES TD1008: −18 LUFS for speech streaming; EBU R128: −1 dBTP | holds, labelled "inferred" |
| Music ≥ 10 dB under speech (P-93); bed ≤ −12 dB (AL-04) | ours | Torcoli et al. 2019 (study, JAES): listeners prefer commentary ≥ 10 LU over music and **≥ 15 LU over ambience**; EBU Tech 3343: loudness-to-dialogue ratio ≤ 5 LU for foreground sounds; Netflix: effects within 4 LU of dialogue; Tang, Fazenda & Cox 2018: producers' rule music about −20 dB; BBC: about 60 % of UK viewers have some difficulty with programme speech | holds for music; **changed: AL-04 bed cap −12 → −15 dB** |
| ≤ 2 effects at once, ≤ 4 layers (AL-01); one music at a time (ED-03) | ours | Walter Murch's "two and a half" (practice): the mind follows 1-2 similar sounds, gives up at 3; Randy Thom (practice): density is worst under dialogue, leave pauses for sound | holds (practice) |
| 4-20 effects a minute (AL-02); an effect on every hard move (AL-03) | ours, from the Kurzgesagt watch ("every motion has a sound") | no measured effect-density data for explainers exists | hypothesis |
| World sounds duck music 9 dB (UR-32) | creator | consistent with Torcoli and EBU | holds |

## 5. Shorts

| Parameter | Our rule | Evidence | Verdict |
|---|---|---|---|
| The metric | viewed vs swiped away (SH-05) | YouTube Help 12942217 (official): the metric exists, no benchmark, compared with the channel's own typical performance; Help 11914225: ranking uses chose-to-view share, average view duration, average percentage viewed, likes, surveys; since 2025 public views count from the first frame and replays, "engaged views" do not | holds; read our numbers after 2026-10-21 |
| Hook: one question within 3 s (SH-01), a statement for two styles (SS-05) | ours | no measured comparison of question vs statement exists; YouTube's Shorts deep-dive (Hoyos, creator opinion on an official blog): "one second to hook"; 99.9 % of views come from the feed, so the first frame is the hook, not a thumbnail; our own Shorts: the hook completes at 2.5-3.5 s on a still held 4-8 s | **changed: added SS-07**: the hook's key words are on screen from frame 0 and the first cut lands inside the hook line (about 2 s) |
| Cut rate | none | no study; observed: breakouts 3-6 changes every 10 s (vidIQ), ours 1.4 | **changed: added SS-08** (hypothesis from observation): at least 3 visual events every 10 s |
| Length 45 s (25-60), 40-130 words (P-11, PV-28) | ours | Sherman (YouTube, 2023, official): no length is favoured; quso.ai 2026 (data, 108,138 Shorts): median views peak at 11-20 s (901), 21-30 s 542, 31-45 s 347, 46-60 s 188; FanpageKarma (data, 32k TikToks): 0-10 s highest completion, 30-90 s about 2x interaction; breakout animated what-ifs in our niche run 38-100 s | **changed: added SS-06**: the set spans two length bands (at least three Shorts of 15-30 s and three of 45-75 s) so the channel's own data decides |
| Word-highlight captions, HUD counter | observed in breakouts | muted viewing is common (Verizon 2019); no Shorts-specific study on highlight captions | hypothesis (kept) |
| Loop ending | SS-04 `loop` | official mechanics: replays count as views and raise average percentage viewed; no data that loops raise distribution | hypothesis (kept, one style of ten) |
| Related-video link, pointer line (SS-03) | ours | YouTube Help 14075157 (official): one related video per Short, own channel, public or unlisted, shown under the handle, needs advanced features; no click-through data; Help 16559651: separate recommendation systems, cross-format watching "not common behavior"; Rajendran 2024 (data, 250 creators ≥ 100k): long-form views fell after a channel's first Short, significant only above 5 M subscribers; Spotter (n = 1): Shorts posted within 3 days of the long video drove the most long-form views | holds; **added**: post the set within 3 days of the video (weak evidence) |
| 10 Shorts per video | SH-05 | YouTube (official): no cadence minimum, volume does not drive traction, each Short is judged on its own, a flop does not hurt the channel, delete-and-repost reads as spam | holds; the only documented downside is viewers repeatedly stopping, which SS-01's variety guards |
| Engagement | not a rule | OverseerOS 2026: short-form median 2.71 %, under-10k channels 1.71 %; ours 0.4-1.0 % | below the median; the hook and motion changes above are the fix to test |

## 6. The Shorts styles, stage by stage

Every style shares the same spine; the table says what differs. Times are for a 30 s Short and stretch for a 60 s one.
"Changes" counts cuts, reframes, accents, text pops and HUD updates (SS-08, at least 3 every 10 s).

| Style | 0-1 s (frame 0 + first words) | 1-3 s (the hook) | Body | Text and HUD | Sound | Ending | Band |
|---|---|---|---|---|---|---|---|
| cold_open_cliffhanger | the worst moment, mid-action; title words on screen | the dramatic question | the scene cut at its peak, 4-5 changes / 10 s | title card, then captions | the scene's own effects, music rising | cliffhanger: "Part 2 is the full video" | 15-30 s |
| anti_intuition | the wrong move on screen ("everyone runs to...") | one statement: "Don't. Everyone else will." (SS-05) | why, in 3 facts, each a cut | the rule as a 3-word pop | a hit on the "Don't" | pointer | 15-30 s |
| countdown_hud | HUD "DAY 1" on frame 0 | the question | one step per HUD tick, a cut on each | HUD top, counter animates | tick or whoosh per step | cliffhanger at the last tick | 45-75 s |
| dialogue_clash | two heroes already mid-argument | the point of dispute in one line | 4-6 fast turns, a cut on every turn, reaction close-ups 0.5-1.5 s | speaker name pops | turn hits, a silence before the punchline | question to the viewer | 15-30 s |
| fact_bomb | the number large on screen | "How can that number be true?" | the number built as a data visual (ED-10) in 3 steps | the visual is the text | a pop per step | pointer | 15-30 s |
| pov_you | "You wake up in 1347." text and picture | the statement (SS-05) | what you see, hear, must do, second person throughout | sparse pops | ambience first, music late | question: "what would you do?" | 45-75 s |
| myth_buster | the belief on screen, struck through at 2 s | "Did you know that's wrong?" | the record in 3 beats | the "MYTH" strike-through | a strike sound | pointer | 15-30 s |
| ranked_three | "3" HUD | the question | three outcomes, worst to best, HUD counting down | HUD 3-2-1 | a sting per rank | question: "which would you pick?" | 45-75 s |
| loop | a line that only makes sense after the last line | the question | the scene | minimal | music that loops at the bar | loop: the last line completes the first | 15-30 s |
| would_you | the choice as two pictures | "Would you...?" | the consequence of each choice | A / B labels | a hit per choice | question | 45-75 s |

Common to all ten: captions from frame 0 (muted viewing), the long video's exact title said aloud once, the related-video
link and a pinned comment set at upload by hand, the video's own pictures (SH-03), and the set posted within three days of
the video.

## 7. Episode 1's five Shorts against these rules

All five: 1.4 changes every 10 s (SS-08 wants 3), a still held 4-8 s before anything moves (SS-07), the hook complete at
2.5-3.5 s with no title words on frame 0 (SS-07), 27-36 s all in one band (SS-06), no word-highlight captions, no HUD, no
loop, the same pointer line closing every one, and the same style (a narrated scene) five times (SS-01). Likes per view
0.4-1.0 % against a median of 1.7 % for channels this size. The one thing they did right by the evidence: a question hook,
sound effects on the actions, and each Short on its own scene.

What the next set changes, in order of expected effect: motion in every shot (MO-06, SS-08), the hook on frame 0 with
the first cut inside it (SS-07), six styles and two length bands (SS-01, SS-06), word-highlight captions and HUDs, posting
within three days of the video.

## 8. Changes made to the rules (D-49)

| Rule | Before | After | Evidence grade |
|---|---|---|---|
| P-52, EL-12, PRODUCTION_RULES, narration-script | heard pace 155 (135-175); 155-175 | target 170 wpm, accepted 155-185 | data + study (Guo, Rodero, Murphy) |
| DW-07 | humour from situation, never a false fact | plus: a joke never carries the explanation | study (Bolkan 2018) |
| DW-09 (new) | | one hero is the learner who guesses wrong and is corrected | study (Chi 2017, Qian 2024) |
| DW-10 (new) | | the narrator speaks to "you" | meta (Ginns 2013, Mayer 2014) |
| ST-11 (new) | | a question outside a declared loop is answered within seconds; the hook names what is known and what is not | study (Murphy 2020, Frede 2026) |
| PF-03 | pause before a reveal 0.4-0.8 s, after a punchline 0.3-0.6 s | 0.5 s before a reveal; a punchline pause is a style choice | study (Van Loon 2000, Attardo 2011) |
| AL-04 | bed ≤ −12 dB | bed ≤ −15 dB | study (Torcoli 2019) |
| `accents` text hold | 1.6 s fixed | 1.5 s + 0.3 s a word (P-71) | study (Mayer signaling; Dolić 2024 weak) |
| SS-06 (new) | | the set spans 15-30 s and 45-75 s bands | data (quso.ai, FanpageKarma) |
| SS-07 (new) | | hook words on frame 0, first cut inside the hook line | official mechanics (feed, first frame) + vidIQ of our own Shorts |
| SS-08 (new) | | ≥ 3 visual events every 10 s | observation (vidIQ breakouts); hypothesis |
| SS-03 | | plus: post the set within three days of the video | weak (Spotter, n = 1) |
| MO-01 | 5 s | unchanged, labelled hypothesis | Lang 2000 supports cuts, no number exists |

Not changed, for lack of evidence either way: MO-01's 5 s, AL-02's 4-20 effects a minute, P-05's joke budget, UR-11's shot
ranges, ED-05's pace by content, the loop style, word-highlight captions. Each is measured on the next videos.

## Sources

Words and story: Guo, Kim & Rubin 2014 https://www.cs.rochester.edu/hci/pubs/pdfs/edX-MOOC-video-production-and-engagement_LAS-2014.pdf ·
Murphy et al. 2022 https://castel.psych.ucla.edu/wp-content/uploads/sites/111/2022/03/Applied-Cognitive-Psychology-2021-Murphy-Learning-in-double-time-The-effect-of-lecture-video-speed-on-immediate-and.pdf ·
Rodero 2020 https://thearf.org/access-knowledge-2/publications/journal-of-advertising-research/do-your-ads-talk-too-fast-to-your-audio-audience-how-speech-rates-of-audio-commercials-influence-cognitive-and-physiological-outcomes/ ·
Rodero 2012 https://www.degruyterbrill.com/document/doi/10.1515/text-2012-0019/pdf · ACX https://help.acx.com/s/article/how-long-will-my-narrated-audiobook-be ·
Mayer 2014 (segmenting) https://cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-managing-essential-processing-in-multimedia-learning-segmenting-pretraining-and-modality-principles/DD24C2F48B9B1277CE59F78276110258 ·
Rey et al. 2019 https://is.tuebingen.mpg.de/publications/rey2018segmenting · Alpizar, Adesope & Wong 2020 https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/A-meta-analysis-of-signaling-principle-in/99900601052901842 ·
Mayer 2014 (personalization) https://www.cambridge.org/core/product/3841340D8AD820C26DBCD39AE664BCEC · Ginns, Martin & Marsh 2013 https://researchers.westernsydney.edu.au/en/publications/designing-instructional-text-in-a-conversational-style-a-meta-ana/ ·
Lagerstrom et al. 2015 https://peer.asee.org/the-myth-of-the-six-minute-rule-student-engagement-with-online-videos · Mar et al. 2021 https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/ ·
Dahlstrom 2014 https://uvm.edu/~mjk/195%20Winter%20Tracking%20Specialty/Using%20narratives%20and%20storytelling%20to%20communicate%20science%20with%20nonexpert%20audiences.pdf ·
Murphy et al. 2020 https://hmlpubs.faculty.ucdavis.edu/wp-content/uploads/sites/214/2022/05/2020_Murphy.pdf · Frede et al. 2026 https://journalofcognition.org/articles/10.5334/joc.501 ·
Bolkan, Griffin & Goodboy 2018 https://www.natcom.org/publications-library/using-humor-classroom-beneficial-or-detrimental-student-learning/ · Zhou & Lee 2025 https://ir.unimas.my/id/eprint/49596/1/The%20Role%20of%20Related%20Humor.pdf ·
Chi, Kang & Yaghmourian 2017 https://education.asu.edu/sites/default/files/lcl/why_students_learn_more_from_dialogue.pdf · Qian, Hong & Chi 2024 https://stemeducationjournal.springeropen.com/articles/10.1186/s40594-024-00505-3

Picture and cut: Cutting et al. 2011 https://pmc.ncbi.nlm.nih.gov/articles/PMC3485803/ · Lang et al. 2000 https://scholars.cityu.edu.hk/en/publications/the-effects-of-edits-on-arousal-attention-and-memory-for-televisi/ ·
Kim, Guo et al. 2014 https://cs.rochester.edu/hci/pubs/pdfs/edX-MOOC-in-video-dropouts-peaks_LAS-2014.pdf · Gritz et al. 2025 https://arxiv.org/pdf/2505.01753 · YouTube Help 9314415 https://support.google.com/youtube/answer/9314415 ·
Dolić et al. 2024 https://www.grid.uns.ac.rs/symposium/download/2024/89.pdf · Verizon/Publicis 2019 https://www.streamingmedia.com/Articles/News/Online-Video-News/80-of-Video-Caption-Users-Arent-Hearing-Impaired-Finds-Verizon-131860.aspx

Sound and voice: YouTube Help 14106294 https://support.google.com/youtube/answer/14106294?hl=en · 16619284 https://support.google.com/youtube/answer/16619284?hl=en · Youlean https://youlean.co/?p=30813 ·
AES TD1008 via https://productionadvice.co.uk/td1008/ · EBU R128 https://tech.ebu.ch/docs/r/r128s1.pdf · EBU Tech 3343 https://tech.ebu.ch/docs/tech/tech3343.pdf ·
Netflix mix spec via https://www.production-expert.com/home-page/2018/8/23/has-netflix-turned-the-clock-back-10-years-or-is-their-new-loudness-delivery-spec-a-stroke-of-genius · Torcoli et al. 2019 https://cris.fau.de/publications/234640600 ·
Tang, Fazenda & Cox 2018 https://www.mdpi.com/2076-3417/8/1/59/htm · Murch via https://wrightonfilm.com/2010/10/28/rules-and-anarchy/ · Thom https://filmsound.org/articles/designing_for_sound.htm ·
Van Loon 2000 https://dspace.library.uvic.ca/items/2498862b-739a-486e-a6c6-baef9574fad7/full · Attardo & Pickering 2011 https://lair.etamu.edu/chssa-faculty-publications/8/ · de Diego-Balaguer 2015 https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.01478/pdf ·
ElevenLabs tags https://elevenlabs.io/blog/elevenlabs-audio-tags-list · prompting https://elevenlabs.io/docs/best-practices/prompting · Voice Design https://elevenlabs.io/docs/eleven-creative/voices/voice-design.md · use policy https://elevenlabs.io/use-policy ·
no-go voices https://elevenlabs.io/docs/help-center/legal/what-are-no-go-voices.md · voice library https://elevenlabs.io/docs/help-center/product/voices/voice-library/what-is-the-voice-library.md · Iconic Marketplace https://elevenlabs.io/iconic-marketplace

Shorts: YouTube Help 12942217 https://support.google.com/youtube/answer/12942217?hl=en&co=YOUTUBE._YTVideoType%3Dshorts · 11914225 https://support.google.com/youtube/answer/11914225?hl=en-GB&co=YOUTUBE._YTVideoType%3Dshorts ·
16559651 https://support.google.com/youtube/answer/16559651 · 14075157 https://support.google.com/youtube/answer/14075157?hl=en · Shorts deep dive https://blog.youtube/creator-and-artist-stories/youtube-shorts-deep-dive/ ·
myths https://blog.youtube/creator-and-artist-stories/debunking-common-myths-about-youtube-shorts/ · engaged views https://blog.youtube/inside-youtube/engaged-views-youtube-explained/ ·
Sherman Q&A https://techcrunch.com/2023/08/25/youtube-demystifies-the-shorts-algorithm-views-and-answers-other-creator-questions/ · views change https://9to5google.com/2025/03/26/youtube-shorts-views-metric/ ·
quso.ai https://quso.ai/research/youtube-shorts-length · FanpageKarma https://www.fanpagekarma.com/insights/optimal-tiktok-video-length/ · Rajendran et al. 2024 https://arxiv.org/pdf/2402.18208 ·
Spotter https://spottercommunity.beehiiv.com/p/increase-views-from-related-shorts · OverseerOS https://www.overseeros.com/blog/youtube-engagement-rate-benchmarks · vidIQ looping https://vidiq.com/blog/post/double-youtube-watch-time-looping-shorts/
