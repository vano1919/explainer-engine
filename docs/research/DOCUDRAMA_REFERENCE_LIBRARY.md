# Historical Docudrama Reference Library

Purpose: help Claude research and improve CrossWorld Chronicles' historical docudrama storytelling without replacing the existing Story Engine or copying full copyrighted scripts into the repository.

**Access audit date:** 2026-10-24  
**Important:** This document is a reference index and analysis brief, not a transcript archive. Availability can change. A page loading does not prove that the complete text or video is accessible. Do not claim to have read material that you could not retrieve.

## Project target

CrossWorld Chronicles is moving from narrated image collages toward original animated historical docudramas. The intended structure combines:
- A short cold open that teases consequential moments from later in the story.
- Brief, conversational narration that establishes context and stakes.
- Dramatized scenes with specific character objectives, conflicting wants, action, dialogue, and a meaningful turn.
- Narrator interludes that add context or explain consequences without repeating the scene.
- A continuous causal story, escalating stakes, payoffs, and a satisfying ending.

The output remains a modern YouTube video, not a slow traditional documentary. Preserve the current pipeline and contracts. Research and propose a minimal extension before changing production code.

## Reference index and observed access

### 1. Wyatt Earp and the Cowboy War

- Episode transcript index: https://transcripts.foreverdreaming.org/viewforum.php?f=3272
- Episode 1 transcript: https://transcripts.foreverdreaming.org/viewtopic.php?t=172143
- Official Netflix page: https://www.netflix.com/title/81572104

**Observed access:** The index and a full Episode 1 transcript page were accessible during the audit. The page contains narration and character dialogue, plus some production cues. This is a transcript, not a verified original production screenplay. Access to the complete episode video was not independently established.

**Study for:** cold opens, narrator-to-reenactment transitions, character conflict, escalation, and how a scene changes what the audience understands.

### 2. Rise of Empires: Ottoman

- Subtitle collection: https://www.azsubtitles.com/rise-of-empires-ottoman
- English subtitle listing: https://www.azsubtitles.com/rise-of-empires-ottoman/english-1256755
- Official Netflix page: https://www.netflix.com/title/80990771

**Observed access:** An English subtitle listing was accessible. The collection/index may be more accessible than every individual file. Check that the actual subtitle text can be downloaded or previewed before claiming a complete transcript is available. Full video access was not established.

**Study for:** military decisions, political pressure, strategy, large-scale events, and connecting individual choices to outcomes.

### 3. Roman Empire

- Season 1 English subtitle page: https://subdl.com/subtitle/sd1302208/roman-empire/first-season/english
- Season 2 subtitle page: https://subdl.com/s/info/Uha8YxSv26/roman-empire

**Observed access:** The Season 1 URL appeared to list only limited episode material rather than a complete season transcript library. The Season 2 page exposed an English subtitle listing and a text preview. Treat both as subtitle sources, not production scripts; verify exact episode coverage before using them.

**Study for:** character-driven conflict, ambition, rivalry, political intrigue, and personal motives behind historical events.

### 4. The World Wars

- English subtitle listing: https://subdl.com/s/info/tF92TFzyKh/the-world-wars

**Observed access:** The subtitle page and text preview were accessible, including narration. The listing appeared to cover the three-part miniseries. Confirm the actual subtitle files and episode coverage before analysis. Full video access was not established.

**Study for:** connecting multiple people, time periods, and conflicts into one comprehensible narrative.

### 5. The Food That Built America

- Subtitle listing: https://subdl.com/en/subtitle/sd1324373/the-food-that-built-america/first-season
- Alternative Episode 1 text preview: https://subtitlecat.com/subs/183/The.Food.That.Built.America.S01E01.WEBRip.x264-ION10.English.html

**Observed access:** An alternative Episode 1 English subtitle text preview with timestamps was accessible during the audit. Do not infer that every season or episode is available from the supplied first-season page.

**Study for:** business rivalry, ambition, innovation, setbacks, decisions, and building dramatic stakes without warfare.

### 6. Epic History TV — Napoleon's invasion of Russia

- YouTube video: https://www.youtube.com/watch?v=byH2WhzXjcQ
- Transcript derived from published English captions: https://prepublish.ai/youtube-transcript/byH2WhzXjcQ

**Observed access:** A full transcript of approximately 63 minutes, derived from published YouTube captions, was available through the transcript page. The direct video page did not yield a complete readable video inspection in the audit. This is primarily a narration-led historical account, not an example of the full reenactment format.

**Study for:** efficient historical exposition, chronology, causality, escalation, and YouTube-oriented narrative pacing.

### 7. Additional script-search resources

- SimplyScripts: https://www.simplyscripts.com/
- TV Calling: https://www.tv-calling.com/
- Writers Guild Foundation — where to find scripts online: https://www.wgfoundation.org/web-resources-where-to-find-scripts-online
- UCLA Library — screenplays and scripts: https://guides.library.ucla.edu/film/screenplays

These are discovery resources, not proof that the specific historical docudrama scripts above are available. Search for relevant, legally accessible examples only when there is a clear gap in the current reference set.

## How to use these references

Do not dump every available text into one huge prompt or assume that a subtitle file is an original screenplay. Prefer a small annotated example library.

For each accessible episode, identify a handful of representative sequences and annotate:
1. **Narrative role:** hook, setup, escalation, reversal, consequence, payoff, or ending.
2. **Narrator function:** what context is necessary and what should remain for the scene to dramatize.
3. **Scene transition:** what pressure or unanswered question justifies entering the scene.
4. **Scene contract:** place/time, characters present, POV, each character's immediate want, opposing want, value at stake, turn, and exit state.
5. **Causal connection:** how this segment's result creates the next segment's problem.
6. **Viewer effect:** curiosity, suspense, surprise, fear, wonder, humour, empathy, or clarity.
7. **Transferable technique:** state the general technique without copying distinctive dialogue, scene text, or a creator's recognizable style.
8. **Evidence status:** distinguish verified historical events and documented quotations from reconstructed dialogue and uncertainty.

When video is accessible, compare the text with what is actually shown on screen: framing, reactions, action, pacing, sound, and the exact point where the edit moves between narration and a scene. A transcript alone cannot establish these visual choices.

## Workflow instructions for Claude

1. Read this file, then inspect the existing canonical documents:
   - `docs/STORY_ENGINE.md`
   - `docs/SCRIPTING_SPEC.md`
   - `.claude/skills/story-engine/SKILL.md`
   - `.claude/agents/story-architect.md`
   - `.claude/agents/scene-writer.md`
   - `.claude/skills/dialogue-scenes/SKILL.md`
   - `.claude/skills/narration-script/SKILL.md`
   - `explainer_engine/scripting/story_lint.py`
   - `explainer_engine/scripting/scene_lint.py`

2. Open each external URL and verify actual text availability. Record whether access is full, partial, metadata-only, blocked, or unavailable. If browsing/network access is unavailable in the current environment, say so and ask the creator to provide downloaded subtitle files or excerpts; do not pretend to have opened them.

3. Analyze the available sources for techniques, not for wording to reuse. Do not copy full copyrighted transcripts or subtitle files into this repository. This index intentionally stores URLs and original analytical notes, not the underlying shows' full scripts. Follow source access terms and applicable copyright requirements.

4. Compare the findings against the current Story Engine. It already has a story skeleton, scene headers, narrator/scene hand-offs, causal turns, open loops, historical claim tracking, and structural lints. Do not rebuild these by default.

5. Report:
   - What was actually accessible and analyzed.
   - The most useful techniques, with URL and episode/section references where available.
   - Which existing rules already cover those techniques.
   - Specific gaps that examples reveal.
   - The smallest justified changes, with trade-offs and tests.

6. Do not modify production code, replace the current generator, or introduce a new architecture as part of this research pass. If source access or coverage is insufficient, state the exact missing material and ask the creator for it before implementation.

## Suggested initial reference set

Start with:
- **Wyatt Earp, Episode 1** for narration plus reenactment structure.
- **Rise of Empires: Ottoman, Episode 1** for military and political conflict.
- **Epic History TV's Napoleon video** for long-form historical exposition and causal progression.

Use Roman Empire, The World Wars, and The Food That Built America as contrast cases. Add more sources only to cover a demonstrated gap.

## Rights and accuracy safeguards

- A subtitle file is not automatically an original production screenplay.
- Do not invent access results, source quotations, historical facts, or metrics.
- Do not present reconstructed dialogue as a verified historical quotation.
- Store source URLs, access date, brief summaries, and original structural annotations rather than full copyrighted transcripts.
- Any new production rule must be compared with the repository's existing evidence and validation model; do not introduce arbitrary numeric rules merely because a reference uses them.
