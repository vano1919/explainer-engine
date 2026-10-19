# Research: story, edit, sound and voice for dialogue what-if videos (2026-10-19)

This report is the evidence behind D-48. The rules themselves live in [STORY_ENGINE](../STORY_ENGINE.md).

There are three inputs:
1. **Episode 1's own production script**, measured in code. These are hard numbers, given in STORY_ENGINE.
2. **vidIQ, 110 credits.** One comment-insights run, two long-form watches and three Shorts analyses. These are AI analyses of the videos, not a frame count. Treat them as observations of single videos.
3. **A web research run**: 5 search angles, 15 fetched sources and 25 central claims. Each claim got three adversarial verifiers with fresh context, and a claim stood unless at least 2 of 3 refuted it.

**Verdicts:**
- **holds**: no verifier refuted it, or one did.
- **qualified**: the core is right but the claim overreaches, and we use only the core.
- **refuted**: at least 2 of 3 verifiers refuted it as worded.
- **not verified**: the claim was extracted from a fetched source but was not among the 25 that went to the verifiers.

**What was not verified:**
- No retention data from our own channel. Episode 1 is not published.
- No listening or viewing panel.
- The vendor pacing numbers (a visual change every 3-5 s, 5-10 s, 10-20 s) are advice without data. MO-01's 5 s is our own planning choice and labelled as such.

## Synthesis of the web run (finished 2026-10-19)

The run fetched 25 sources and extracted 113 claims. The 25 most central claims were sent to the verifiers: 14 survived and 11 were refuted. After duplicates were merged, 8 findings stand.

**Strong** (primary sources, 3-0):
- The writing pipeline: plan top-down (logline, characters, beat outline tied to settings and characters, then dialogue), with programmatic gates between the steps and a critic with an explicit rubric.
- The but/therefore rule.
- ElevenLabs Voice Design's prompt template.
- ElevenLabs' ban on impersonation, which applies whether or not a voice is on the no-go list.

**Medium:**
- Story first, technical layer second (DSR, a preprint).
- Kurzgesagt's sources-experts-drafts process (the studio describing itself).
- The Short-to-video link (a 2023 announcement; the current placement comes from YouTube Help).

**Refuted as evidence:** every numeric retention or editing rule found: a change every 5-10 s, a loop every 2-3 min, a surprise every 20-30 s, the title proven within 10 s, tension by 10-15 s, the biggest drop at 15-30 s. These were 0-3 votes, from blogs that cite no data. The MO thresholds and the beat-grid timings are therefore our own product hypotheses, labelled as such.

**No verified evidence (open questions):**
- competitor practice beyond Kurzgesagt;
- shot lengths, kinetic type and 2D rigs;
- YouTube loudness and mix levels (the existing mix rules stay as they are);
- Shorts hook styles and lengths, and which of them actually move viewers to the long video;
- what ElevenLabs' prohibited-use policy allows for a parody voice inspired by a historical figure.

The vidIQ watches and our own A/B results across the 10 Shorts styles are how we answer these.

## Story structure

| Finding | Verdict | Source | Used in |
|---|---|---|---|
| Join beats with "but" or "therefore", never "and then". Parker and Stone's rule, explained by Trey Parker in the 2011 mtvU / NYU class video. | holds | huffingtonpost.co.uk report of the NYU class; secondary write-ups | ST-02 |
| "Matt Stone reviews scripts replacing 'and then'" | refuted as worded: it was Parker in the video, and the attribution comes from secondary sources | the same video | none (the rule is used, not the anecdote) |
| An open-loop structure (hook, build, payoff per section), stakes raised every 60-90 s, promise then payoff | not verified (practitioner method, extracted only) | creator-education blogs | ST-05, beat grid |
| "77.6 % of hooks share no content word with the title" (3,066 videos) | reported by a vendor, method not checked | vendor blog | hint only: a hook adds to the title |
| Kurzgesagt grounds scripts in books and papers, consults experts, publishes a source sheet, needs about a dozen drafts | holds (Kurzgesagt's own page) | kurzgesagt.org/youtube | ST-09, the critic's rounds |
| "Kurzgesagt *pays* experts" | refuted (2 of 3): the sources say it consults experts, not that it pays them | gist.ly summary; eur.nl TRESCA | none |
| xkcd *What If?* works through an absurd premise with serious arithmetic, with humour layered on top of accurate content | not verified (extracted from reviews) | book reviews | beat grid, DW-07 |
| OverSimplified keeps some motion in every scene and uses humour to carry dense history, but too much entertainment buries the lesson | not verified (extracted from an essay) | essay on the channel | MO-06, ST-09 |

## Writing with a language model (the agent framework)

| Finding | Verdict | Source | Used in |
|---|---|---|---|
| Writing the narrative first and formatting the screenplay second scores higher than one pass (about +2.4 on a 12-point professional scale) | holds | two-stage screenplay generation paper (DSR, 2025) | stages 1-2 before 3-4 |
| Dramatron generates top-down: logline, characters, plot of scene beats, locations, dialogue, each with its own prompt | holds | Mirowski et al., arXiv 2209.14958 | the writers' room |
| Dramatron's scene dialogue never saw earlier dialogue, so participants found it inconsistent | refuted as worded (0-3, because of the "repetitive loops" cause); the verifiers did confirm the inconsistency quotes in §5.6.3 | the same paper, §5.6.3 | the scene writer gets the last three lines |
| A detailed outline before drafting improves long-range coherence (plot coherence 67.6 % vs 45.1 % against Re3) without costing interest (60.1 % vs 39.4 %) | holds (3-0) | Yang et al., arXiv 2212.10077 | skeleton first (ST layer) |
| "The controller alone raised relevance 65.3 % vs 37.1 %" | refuted: that is the whole DOC system against Re3; the controller ablation is 73.5 vs 52.0 | the same paper, Tables 1 and 5 | none (the guard is our own controller) |
| Prompt chaining with programmatic gates between steps; evaluator-optimizer loops for creative work; strict, mistake-proof tool interfaces | holds | Anthropic, "Building effective agents" | stage guard, critic, schema |

## Editing and sound

| Finding | Verdict | Source | Used in |
|---|---|---|---|
| "On faceless videos change the picture every 5-10 s; a 30 s still loses viewers" | refuted as evidence: advice with no data (a vendor blog) | outlierkit blog | MO-01 is our own choice, not this |
| No fixed attention timer exists. Every change should clarify, emphasise, reorient, compress or contrast, and chosen stillness is a valid pacing tool. | not verified (editorial reasoning, no study) | editing guide | MO introduction, ED-05 |
| Duck the music under speech and raise it in pauses; whooshes and risers as subtle punctuation; a cut to silence for impact | not verified (practitioner guides; consistent with ED-03, UR-32) | mixing guides | AL-03, AL-04, PF-05 |
| Master to about -14 LUFS with true peak under -1 dBTP; YouTube turns louder uploads down | not verified (consistent with the existing mix) | audio guides | unchanged |
| Infographics Show F-35 what-if (642,693 views): a change every 3.5-4 s, about 85 % of scenes with continuous motion, wipes, flash tears and HUD overlays, a named hero with a personal stake, three loops, a reversal at the real limits, a twist; weak at spec info-dumps | vidIQ watch | video -YmpuNOnIn4 | beat grid, DW-08, MO |
| Kurzgesagt "Astronomy Is In Crisis" (5.4 M views): a change every 2.5-3.5 s, motivated transitions and practically no dissolves, picture beats on the operative word, 4-6 audio stems with a sound for every motion, music dropping to a drone on the crisis line | vidIQ watch | video zozEm4f_dlw | accents `at`, AL-01..AL-03, PF-05 |

## Voices

| Finding | Verdict | Source | Used in |
|---|---|---|---|
| ElevenLabs Voice Design prompt: language/accent, gender, age, quality, then persona, emotion, timbre and pacing. Each generation gives three previews; a longer preview text gives a more stable voice; avoid "foreign/exotic" and FX words. | holds | ElevenLabs docs | `casting.design_description`, VC-01 |
| ElevenLabs' prohibited-use policy bans impersonation | holds | ElevenLabs policy | VC-02, PV-10 |
| "The no-go voices filter means a public figure's voice cannot be cloned" | refuted: the filter restricts such clones but is incomplete by ElevenLabs' own description; the policy is the binding rule | ElevenLabs safeguard page | VC-02 wording |

## Shorts

| Finding | Verdict | Source | Used in |
|---|---|---|---|
| A Short can link a related video. The link shows below the channel handle, must be one of our own channel's public or unlisted videos, and is set in Studio. | qualified: the 2023 description (in the Short's description, next to a play button, any Short) is out of date | YouTube Help 14075157 | SS-03 |
| The link moves few viewers; say the long video's exact title aloud; add a pinned comment and a playlist | not verified (practitioner advice, no data) | creator blog | SS-03 |
| Shorts observed: a HUD counter as a progress bar, second person, a bookend ending, a question outro (5EscQPYIO70); an anti-intuition hook, DAY counter, 3-4 changes every 10 s, word-highlight captions, a "Part 2" cliffhanger (-VrlJIfGUuE); a conflict line in 2 s, 4-6 cuts every 10 s, a punchline ending (TqCNYzlTiUs, a clip of third-party media: structure only) | vidIQ analyses | the three Shorts | SS catalog |
| Open loops raise completion "12 % -> 35 % -> 68 %" | unverified vendor marketing (no sample) | vendor blog | not used |

## What viewers say (vidIQ comment insights, thin: 6 channels with comments, 78 threads)

- Viewers ask for specific "why did X happen" and "what if" deep dives.
- On story-led videos they write "this should be a movie".
- They call out factual errors with timestamps.

Together these support ST-09 and the critic's fact pass: a story people enjoy, on facts that hold.
