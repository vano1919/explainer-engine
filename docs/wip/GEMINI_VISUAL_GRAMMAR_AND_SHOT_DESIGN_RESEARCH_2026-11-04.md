# Independent Research Brief — Cinematic Audio-Visual Craft, Production Techniques and Tool Implementation

**Research brief version:** 2.0  
**Date:** 2026-11-04  
**Intended research team:** Gemini / Argon Deep Research  
**Output language:** Georgian prose, with English technical terminology, technique names, tool names and parameter names preserved  
**Research mode:** Independent, evidence-based craft and technical research  
**Execution boundary:** Research and recommendations only. Do not inspect or audit the Explainer Engine repository, edit project files, generate production assets, call paid APIs, launch GPU pods, render a production episode, or publish anything.

---

## 1. Mission

Act as an independent research group combining the expertise of:

- a film director and visual storyteller;
- a cinematographer and camera operator;
- a production designer and lighting director;
- an animation director and storyboard artist;
- a film editor and post-production supervisor;
- a colorist and compositing artist;
- a motion-graphics and data-visualisation designer;
- a sound designer, Foley artist and re-recording mixer;
- a dialogue editor and voice director;
- a film-score composer and music supervisor;
- a Blender technical director;
- a generative-video researcher specialising in LTX;
- a Python / FFmpeg media-engineering specialist;
- a YouTube audience-retention and creator-education researcher;
- a sceptical technical researcher who verifies every important claim.

Your task is to research **the actual professional techniques used to make cinematic video and audio**, explain what each technique does, identify the situations in which it works, explain when it is unsuitable, and show how it can be reproduced or approximated with the following production methods:

1. LTX-family image-to-video and text-to-video generation, distinguishing exact local and hosted products;
2. Blender, including 2D/2.5D/3D scene construction, camera animation, previs, compositing and simulation;
3. Python-based deterministic image/video production, compositing and motion graphics;
4. FFmpeg-based editing, filtering, compositing and audio post-production;
5. Hybrid workflows combining two or more of these tools.

The purpose is to build a **professional technique reference library**. It must teach a later production system how to choose an appropriate visual and audio technique from the story's meaning, rather than blindly applying generic camera moves, sound effects, transitions or graphics.

Do not return generic advice such as “use cinematic lighting”, “add dramatic music”, “use dynamic camera movement” or “make the edit engaging”. Give exact technique names, the conditions that justify them, their intended effect, practical execution steps, alternatives, limitations and QA methods.

The research should be independent of any one repository or codebase. A separate reviewer will later decide which findings fit the project's current architecture. Do not spend time performing that repository-to-architecture mapping.

## 2. Production context and non-negotiable boundaries

Use this context to make the research relevant. These are production constraints, not a request to audit their implementation.

The intended format is a **12-minute English-language animated historical / counterfactual docudrama and explainer**. It combines:

- a narrator who guides the audience through the story;
- voiced character dialogue and acted scenes;
- generated animated action;
- composed still images that can be layered, moved or animated;
- explanatory maps, charts, timelines, statistics, comparisons and diagrams;
- background score and music transitions;
- environmental ambience and room tone;
- Foley and synchronised sound effects;
- editing, compositing, colour treatment and final audio mastering.

The overall target is a coherent illustrated / animated visual universe with cinematic staging, expressive characters, historically appropriate environments and a consistent design language. The research must explain how to create cinematic impact without assuming that the output should become photorealistic live-action. Do not prescribe a new art style. Explain which cinematic principles transfer across illustrated animation, 2D, 2.5D and 3D.

### 2.1 Visual runtime allocation — 60 / 30 / 10

Keep these categories strictly separate:

| Visual lane | Target | Meaning |
|---|---:|---|
| VIDEO | 60% | Generated moving video, including non-dialogue action |
| STILL | 30% | Still-image compositions, including images with programmatic motion, layers, object movement or parallax |
| HELPER | 10% | Maps, diagrams, calculations, counters, progress indicators, timelines and other explanatory graphics |

The existing planning tolerance is ±5 percentage points. Treat this as a production target, not a requirement to damage storytelling or force a weak technique into a particular lane.

A VIDEO shot may carry narration, character dialogue, music, ambience, Foley, effects or silence. A STILL or HELPER shot may also carry any appropriate audio. Visual lane does not determine who speaks.

### 2.2 Spoken-word allocation — narrator / dialogue

Keep this independent from the visual allocation:

- Narrator: 70–80% of audible spoken words.
- Voiced character dialogue: 20–30% of audible spoken words.
- Planning midpoint: 75% narrator / 25% voiced dialogue.
- The upper dialogue boundary is therefore 30% dialogue / 70% narrator.
- Lines explicitly marked non-voiced are excluded from the spoken-word calculation.

Do not interpret this as a visual runtime allocation. Do not infer the spoken-word ratio from shot count, VIDEO duration, number of dialogue scenes or wall-clock runtime. Spoken-word share and actual elapsed audio duration are different measurements.

Music, ambience, Foley, sound effects and silence are not spoken words and do not enter this ratio.

### 2.3 Shot duration boundaries

Use these as planning boundaries, not universal provider guarantees:

- Visible character dialogue / lip-sync coverage: maximum 5-second planning target.
- Non-dialogue VIDEO action: may use 10–15 seconds when uninterrupted choreography, geography or camera movement is more effective as a continuous shot.
- Fifteen seconds is a planning ceiling only. The exact model, endpoint, resolution, FPS, generation mode and frame-count rules determine what can actually be generated.
- Do not cut non-dialogue action into arbitrary five-second clips merely because dialogue coverage has a shorter target.
- Keep STILL hold constraints separate from VIDEO duration constraints.

The report must preserve these boundaries and explain the craft decisions that can be made inside them. Do not invent additional creator-approved ratios or fixed segment durations.

## 3. Research rules: evidence, depth and honesty

### 3.1 Research the technique, not just the name

For every important technique, explain:

1. What is its accepted professional name?
2. What does it physically or editorially do?
3. What does the audience perceive?
4. What narrative or emotional purpose does it serve?
5. What type of scene or story beat justifies it?
6. What visual or audio conditions must be present for it to work?
7. When should it not be used?
8. What is the exact execution process?
9. What are the common amateur mistakes?
10. What are its limitations in generated or animated media?
11. How can it be recreated using LTX, Blender, Python and/or FFmpeg?
12. How can the finished result be checked?

Do not confuse a professional technique with an effect or a preset. Explain the underlying principle and the observable result.

### 3.2 Separate evidence types

Classify each important claim as one of:

- **PRIMARY / OFFICIAL:** official technical documentation, standards, manufacturer manuals, official educational curricula or official platform guidance;
- **RESEARCH:** peer-reviewed study or recognised academic publication;
- **PROFESSIONAL PRACTICE:** experienced practitioner, professional institution, production case study or documented workflow;
- **MEASURED TEST:** an actual repeatable test with method, configuration and results;
- **ANECDOTAL:** community report, individual demonstration or unsystematic observation;
- **HYPOTHESIS:** plausible but not yet sufficiently supported.

Do not present a hypothesis as a technical fact. Do not turn an aesthetic preference into a universal law.

### 3.3 Source requirements

Use direct, relevant sources. Prioritise:

1. Official documentation for software, codecs, models, APIs and standards.
2. Film schools, cinematography institutions, professional camera / lighting organisations and structured training curricula.
3. Audio-engineering institutions, professional sound organisations and recognised mixing / mastering education.
4. Professional editing and colour-grading education, including official software training.
5. Animation schools, professional animation education and recognised animation references.
6. Peer-reviewed research where empirical claims are made.
7. Documented professional case studies and practitioner demonstrations.
8. Communities only as secondary evidence, clearly labelled.

Provide at least **30 distinct, useful sources overall**, with at least 4 strong sources for each major discipline represented in the research. Do not pad the source list with irrelevant links. Every source must support a specific finding or technique.

For each source record:
- exact title;
- author, institution or publisher;
- direct URL;
- publication / revision date, if available;
- access date;
- source category and quality;
- exact claim or technique it supports;
- limitations or conflicts with other sources.

Do not cite a documentation homepage as evidence for a specific feature. Link to the exact page, manual section, standard or course curriculum.

### 3.4 Resolve conflicts

When professional sources disagree:
- explain the disagreement;
- identify the conditions under which each approach is appropriate;
- distinguish a convention from a hard technical constraint;
- recommend a practical decision rule.

Do not claim that one editing rhythm, lens, musical tempo, sound level, camera move or transition is universally correct.

---

## 4. Education and academy research — required

Find and evaluate structured educational resources. The goal is to identify where the production team can learn professional craft systematically, not merely collect random tutorial links.

### 4.1 YouTube creator education

Research current official YouTube learning resources, including the current state of YouTube Creator Academy / YouTube Creators education and relevant YouTube Help material.

Find material on:
- storytelling and audience expectation;
- titles, thumbnails and the opening promise;
- opening hooks and early viewer comprehension;
- audience retention and satisfaction;
- visual clarity and information density;
- pacing and chapter structure;
- narration and presentation;
- analytics that can distinguish a story problem from an editing problem;
- accessibility, captions and viewer experience.

Separate actual platform guidance from creator folklore. Do not assume that advice from a viral personality is an official YouTube requirement. Explain which guidance applies to a 12-minute historical animated explainer and which applies mainly to other formats.

### 4.2 Film, directing and cinematography education

Find current and accessible courses, curricula, learning paths or professional education from credible film schools and cinematography organisations.

Research:
- directing actors and animated characters;
- visual storytelling and blocking;
- cinematography and camera grammar;
- lens choice and perspective;
- camera movement;
- lighting and production design;
- shot planning and storyboarding;
- composition and visual continuity;
- historical / period visual research;
- action and battle staging.

Investigate credible organisations and providers such as film schools, cinematography societies, camera and lighting manufacturers' educational programmes, and recognised specialist training platforms. Verify each specific course or resource rather than assuming a brand's existence means it offers the relevant material.

### 4.3 Editing and colour education

Find structured courses and official training covering:
- film editing grammar;
- continuity editing and montage;
- rhythm and pacing;
- sound-led editing;
- visual transitions;
- compositing;
- colour correction and colour grading;
- shot matching;
- delivery and finishing.

Include official DaVinci Resolve / Blackmagic Design training, Adobe video education, Avid education or other directly relevant providers where current resources exist. Evaluate the actual curriculum, not just the provider.

### 4.4 Audio engineering and sound-design education

Find current professional training from recognised audio-engineering schools, professional associations, audio software / hardware educators and established mixing practitioners.

Cover:
- dialogue recording and editing;
- voice performance and production;
- EQ and dynamics;
- compression and limiting;
- loudness and true peak;
- spatial audio and stereo;
- sound effects and Foley;
- ambience and sound perspective;
- reverb and acoustic space;
- music scoring and orchestration;
- film / television sound mixing;
- mastering and delivery.

Investigate organisations and resources such as Berklee Online, Audio Engineering Society, Dolby educational resources, iZotope learning, Sound On Sound, recognised mixing education and other credible institutions. Verify course availability and the actual lessons.

### 4.5 Animation, 2.5D, Blender and motion graphics education

Find structured education for:
- the principles of animation;
- staging and silhouette;
- character acting;
- camera animation;
- 2.5D scene construction;
- compositing and depth;
- particles, smoke, dust and atmosphere;
- environment and crowd workflows;
- motion graphics and typography;
- data visualisation;
- Blender scene / camera / Geometry Nodes workflows.

Include official Blender education and credible animation / motion-design schools or courses where relevant.

### 4.6 Academy and course catalogue

Produce a useful catalogue with:

| Provider / institution | Exact course or learning path | Discipline | Relevant lessons | Free / paid | Access status | Direct URL | Why it matters |
|---|---|---|---|---|---|---|---|

Do not use “academy” as a marketing label unless it really is a structured educational offering. Distinguish a full curriculum, a course, a documentation tutorial and an individual video.

Recommend a practical learning sequence for someone building a production workflow, prioritising the most relevant learning rather than the longest list of courses.

---

## 5. Visual storytelling and script-to-screen technique research

Research how story meaning becomes an image and an edit.

At minimum cover:

- visual exposition versus verbal exposition;
- show-don't-tell through action;
- establishing geography before close action;
- visual cause and effect;
- action / reaction;
- reveal and delayed reveal;
- visual contrast and juxtaposition;
- visual metaphor;
- match cut and recurring visual motif;
- montage and time compression;
- cross-cutting between simultaneous events;
- point of view and subjective camera;
- visual hierarchy and directing the viewer's attention;
- staging a central action in a crowded frame;
- visual proof for a factual claim;
- the relationship between narration, dialogue and picture;
- avoiding literal duplication of what the narrator says;
- using reaction shots to communicate meaning;
- pacing visual changes around information, not a mechanical timer.

For each technique, specify the story beat it best serves, the audience information it communicates, how it should affect shot size and duration, and what the editor should preserve across the cut.

---

## 6. Cinematography and camera-language technique library

Research professional terminology and practical use cases. Cover at least the following families.

### 6.1 Shot size and framing

- Extreme Wide Shot, Wide Shot, Full Shot;
- Medium Wide / Cowboy Shot;
- Medium Shot;
- Medium Close-Up;
- Close-Up and Extreme Close-Up;
- Insert and detail shots;
- Two-shot and group shot;
- Over-the-Shoulder;
- Point of View;
- profile, frontal and three-quarter views;
- foreground framing and frame-within-frame;
- over-the-head, ground-level and overhead compositions.

Explain what information and emotion each framing communicates, how to choose a sequence of sizes, and when changing the size is more useful than adding camera movement.

### 6.2 Lens, perspective and depth

Research:
- wide-angle, normal and telephoto lens character;
- field of view versus perspective;
- focal length and camera distance;
- perspective compression;
- depth of field and focus hierarchy;
- deep focus versus shallow focus;
- rack focus;
- foreground / midground / background separation;
- parallax and camera-relative movement;
- distortion and spatial readability.

Explain which effects can be recreated convincingly in 2D / 2.5D and which need actual 3D geometry.

### 6.3 Camera movement

Research and compare:
- static / locked-off camera;
- pan and tilt;
- push-in / dolly-in and pull-out / dolly-out;
- optical zoom versus physical dolly;
- tracking / trucking;
- lateral tracking;
- crane / jib / pedestal;
- orbit / arc;
- aerial drift / drone-style movement;
- handheld and controlled handheld simulation;
- whip pan;
- follow camera;
- tracking with a moving vehicle or subject;
- dolly zoom / Vertigo effect;
- speed changes and camera acceleration;
- motivated camera movement versus decorative movement.

For each move explain:
- the narrative / emotional purpose;
- what the camera is physically doing;
- what should remain fixed in the frame;
- the ideal starting composition;
- movement direction and screen-space consequences;
- easing, acceleration and deceleration;
- what the move must reveal;
- when it is distracting or technically risky;
- how to approximate it with each relevant tool.

Explicitly distinguish camera movement from digital image scaling. A zoompan filter, a 2.5D push and a true 3D dolly do not produce identical perspective.

### 6.4 Blocking, geography and continuity

Research:
- 180-degree axis;
- 30-degree rule;
- eyeline match;
- screen direction;
- match on action;
- entrances and exits;
- maintaining geography across cuts;
- master shot and coverage;
- cross-axis moves and motivated axis changes;
- group blocking;
- action geography in battles and chases;
- continuity of props, costume, environment and lighting.

Explain how these principles apply to animated / generated scenes where the source image and next generated shot can drift.

---

## 7. Lighting, production design, colour and image treatment

Research the visual tools used to create a coherent cinematic mood.

### 7.1 Lighting

Cover:
- key, fill and rim / back light;
- three-point lighting and when to break it;
- motivated lighting;
- practical lights;
- hard versus soft light;
- high-key and low-key lighting;
- chiaroscuro;
- silhouette lighting;
- firelight and flicker;
- moonlight, dusk, dawn and overcast daylight;
- volumetric light, haze and atmospheric depth;
- bounce and negative fill;
- contrast ratio and exposure control;
- lighting continuity across cuts.

For each setup explain which subject, emotion and environment it supports. Explain practical simulations in Blender and compositing tools, and prompt-level approximations in LTX.

### 7.2 Colour design and grading

Cover:
- palette design;
- warm / cool contrast;
- complementary and analogous colour relationships;
- saturation control;
- value hierarchy;
- colour as faction / character / location identity;
- scene-to-scene colour continuity;
- colour temperature;
- day-for-night and stylised time-of-day treatment;
- contrast curves, lift / gamma / gain;
- LUTs and their limitations;
- shot matching;
- selective colour and accent colour;
- smoke, dust and atmosphere colour;
- accessibility and colour-blind-safe encoding in information graphics.

Provide sample role-based palette structures, such as dominant, secondary, accent, shadow and atmosphere. Do not dictate one universal palette.

### 7.3 Production design and historical authenticity

Research how to create credible:
- architecture and interiors;
- battlefields and landscapes;
- clothing, armour and weapons;
- tools, props and materials;
- weather and environmental conditions;
- crowds and background extras;
- era-specific lighting sources and practicals.

Explain how historical accuracy, visual readability and style consistency can coexist. Distinguish a historically grounded detail from a decorative cinematic invention.

---

## 8. Animation and action choreography

Research the 12 principles of animation and their relevance to stylised, illustrated and generated video:

- squash and stretch;
- anticipation;
- staging;
- straight ahead / pose-to-pose;
- follow-through and overlapping action;
- slow in / slow out;
- arcs;
- secondary action;
- timing;
- exaggeration;
- solid drawing / spatial integrity;
- appeal.

Also cover:
- weight and contact;
- foot planting;
- character identity consistency;
- facial acting and eye direction;
- lip-sync and dialogue coverage;
- crowd motion;
- mass and momentum;
- collisions and impacts;
- cloth, hair, flags and secondary motion;
- particles, dust, debris and smoke;
- battle formation movement;
- loops versus one-off actions;
- keyframe, intermediate pose and end-state planning.

Explain how to write a first pose, anticipation pose, action peak and settle pose. Explain what must be deterministic and what can be delegated to a generative model.

Do not assume generated motion reliably follows physics. Describe how to identify and mitigate common failures such as sliding feet, rubber limbs, identity drift, teleporting props, duplicated people, inconsistent crowd motion and impossible collisions.

---

## 9. Editing craft and visual rhythm

Research the editor's craft in detail.

### 9.1 Cut and transition grammar

Cover:
- hard cut;
- cut on action;
- match cut;
- eyeline cut;
- reaction cut;
- insert cut;
- J-cut and L-cut;
- cross-cutting / parallel editing;
- smash cut;
- jump cut;
- invisible cut;
- dissolve;
- fade to / from black;
- wipe and motivated graphic transition;
- whip-pan transition;
- speed ramp;
- freeze frame and held tableau.

For each, explain its narrative function, when it works, when it weakens the scene, its typical continuity requirements and how to reproduce it with FFmpeg, Blender or Python where relevant.

### 9.2 Rhythm and pacing

Research:
- shot duration as a function of action and information;
- rhythm variation;
- tension build and release;
- fast / slow contrast;
- montage density;
- dialogue pauses and reaction timing;
- visual change around narration;
- silence and held frames;
- when a long take is stronger than multiple cuts;
- how to prevent repetitive equal-length shots;
- how to make an edit feel deliberate rather than algorithmic.

Do not prescribe one cuts-per-minute number for every scene. Explain how battle, dialogue, travel, exposition, reveals and aftermath require different rhythms.

### 9.3 Editing for explanatory clarity

Explain how to combine:
- narrator-led footage;
- character scenes;
- maps;
- charts and counters;
- document inserts;
- diagrams;
- visual comparisons;
- animated text and labels;
- data-driven changes.

Explain how to prevent information overload, text collisions, excessive transitions and graphics that compete with dialogue or action.

---

## 10. Audio direction: narration, dialogue and voice performance

Treat audio as a complete cinematic department, not a final music layer.

### 10.1 Narration craft

Research:
- conversational narration versus formal documentary delivery;
- sentence length and breath groups;
- spoken-word pacing;
- stress and emphasis;
- intonation and question contours;
- pause placement;
- rhetorical questions;
- reveal timing;
- emotional colour;
- humour and dry delivery;
- pronunciation and name handling;
- narration-to-picture alignment;
- avoiding narration that merely describes the image;
- using narration to add context, contrast or meaning.

Explain how to direct an AI narrator through text, punctuation, tags, chunking and post-processing. Distinguish controls genuinely exposed by each exact TTS model from prompt tricks or unsupported assumptions.

### 10.2 Character dialogue and voice acting

Research:
- character voice identity;
- vocal contrast between characters;
- emotional delivery;
- subtext and conversational intention;
- turn-taking and interruption;
- silence as a response;
- dialogue pace;
- breath and vocal texture;
- dialogue editing;
- visible lip-sync versus voice-over dialogue;
- scene coverage and reaction timing;
- dialogue versus narration hand-offs.

Explain when a character should visibly speak, when to show the listener, when to cover a line with action or an insert, and when reported narration is more effective than lip-sync.

### 10.3 TTS-specific production

For ElevenLabs and other relevant current TTS approaches, verify:
- exact model / version;
- available voice and delivery controls;
- supported emotion / audio tags;
- chunking and context handling;
- pronunciation controls;
- speech alignment / word timing;
- consistency and repeatability;
- voice licensing and consent boundaries;
- limitations of synthetic acting;
- audio editing requirements after generation.

Do not invent parameters that the current API does not expose. Clearly separate native model controls from text-based prompting and external audio processing.

---

## 11. Music direction and score design

Research how professional film and documentary music supports narrative structure.

### 11.1 Score techniques

Cover:
- leitmotif and character theme;
- recurring melodic motif;
- harmonic tension and release;
- ostinato;
- drone and sustained textures;
- percussion patterns;
- orchestral layering;
- rhythmic pulse;
- dissonance;
- tonal shift;
- instrumentation and timbre;
- low-frequency emphasis;
- crescendo and decrescendo;
- riser, impact and sting;
- transition cue;
- emotional contrast;
- silence / music dropout;
- diegetic versus non-diegetic music.

For each technique explain:
- the narrative purpose;
- the emotion it can create;
- which scene types benefit;
- what musical change should accompany a story turn;
- when music should remain absent;
- when a motif should return or evolve;
- how to avoid generic trailer music and constant emotional overstatement.

### 11.2 Music across a 12-minute story

Propose a sample score map for a 12-minute historical docudrama. The map should include possible music states and transitions, but remain flexible to story structure.

Explain:
- opening / hook music;
- context and exposition beds;
- character-scene music;
- escalation;
- battle / action;
- reveal;
- climax;
- aftermath;
- ending / resolution;
- intentional no-music stretches.

Show how to design musical arcs instead of generating one unrelated track per segment. Explain when one continuous cue, multiple cues, a recurring motif or a deliberate silence is best.

### 11.3 AI music generation

Research current music-generation approaches, particularly their actual controls for:
- duration;
- instrumental / vocal selection;
- genre and instrumentation;
- tempo and energy;
- emotional progression;
- structure and ending;
- loopability;
- editability and stems;
- consistency across multiple cues;
- licensing and commercial use.

Distinguish what a text-to-music prompt can request from what the model can guarantee. Explain how to create cue briefs that describe the musical arc rather than merely a list of moods.

Do not recommend prompts that imitate a living composer or copy a named film score. Describe underlying musical techniques instead.

---

## 12. Sound design, Foley and environmental audio

### 12.1 Sound layers and perspective

Research the difference and interaction between:
- dialogue;
- narration;
- ambience;
- room tone;
- environmental effects;
- Foley;
- hard sound effects;
- designed cinematic effects;
- diegetic music;
- non-diegetic score;
- silence.

Explain how sound changes according to:
- distance from the listener;
- indoor / outdoor acoustics;
- material and environment;
- camera perspective / point of audition;
- foreground and background action;
- character point of view;
- location changes;
- scale of action.

### 12.2 Foley and action sync

Research Foley and sound synchronisation for:
- footsteps by surface and weight;
- cloth and armour movement;
- weapons and tools;
- horse movement;
- impacts and collisions;
- fire, water, wind and weather;
- doors, objects and handling;
- battle crowd layers;
- crafting and manual work;
- movement through different spaces.

Explain when a sound should be recorded / generated separately, reused from a library, layered, processed or omitted. Explain how to avoid repeated identical samples, excessive effects and sounds that do not match the visible action.

### 12.3 Cinematic sound effects

Research:
- whoosh and transition effects;
- impact and low-frequency hit;
- riser and reverse effect;
- boom / sub impact;
- metallic transient;
- debris and environmental layers;
- crowd walla;
- weapon and battle textures;
- tension textures;
- sound bridges;
- pre-lap and post-lap;
- dynamic perspective and panning;
- reverb tails and decay.

For each sound design technique, identify the specific visual or story event that earns it. Explain why a sound on every cut makes a production feel artificial.

### 12.4 Sound for specific scene types

Provide sound-design recipes for:
- large battle;
- small fight / duel;
- dialogue and negotiation;
- travel / marching / riding / sailing;
- manual crafting / building;
- discovery / reveal;
- environmental establishing shot;
- map / tactical explanation;
- aftermath and loss;
- climax and payoff.

Each recipe must describe dialogue / narration, score, ambience, Foley, effects, perspective, timing and intentional silence.

---

## 13. Audio engineering, mixing and mastering

Research the complete post-production chain.

At minimum cover:
- gain staging;
- dialogue editing and noise control;
- high-pass filtering where justified;
- corrective and tonal EQ;
- de-essing;
- compression;
- parallel compression;
- limiting;
- automation;
- sidechain ducking;
- music under dialogue;
- ambience under dialogue;
- effects masking speech;
- loudness measurement;
- integrated versus short-term loudness;
- loudness range;
- true peak;
- clipping and inter-sample peaks;
- stereo width and mono compatibility;
- panning;
- reverb and delay;
- bus routing;
- separate stems;
- final mix validation;
- export codec, sample rate and bit depth.

### 13.1 Standards and delivery

Verify the current authoritative versions and applicability of relevant audio standards and delivery guidance, including ITU-R BS.1770, EBU R128, ATSC A/85 where relevant, and current official YouTube upload / audio guidance.

Do not assume that a broadcast target is automatically the correct YouTube target. Distinguish:
- formal measurement standards;
- broadcast delivery conventions;
- platform recommendations;
- project-specific mix decisions;
- subjective creative choices.

Provide a recommended measurement and QA workflow. Cite exact standards and official documents. Do not fabricate a universal YouTube loudness requirement.

### 13.2 Mix recipes

Provide practical starting-point recipes for:
- narration-led scene;
- character dialogue scene;
- music-led montage;
- battle / action;
- quiet reveal;
- ambience-led travel;
- climax;
- silence-to-impact transition.

For each recipe state the relative priority of layers and the mix decisions. Any numeric ranges must be sourced, labelled as starting points rather than universal truths, and adjusted after listening and measurement.

---

## 14. Maps, diagrams, statistics and motion graphics

Research how professional documentary and explainer productions turn information into readable moving graphics.

Cover:
- geographic maps;
- strategic / battle maps;
- route and movement maps;
- territory changes;
- timelines;
- counters and tickers;
- bar charts;
- line and step charts;
- comparisons;
- tables / ledgers;
- network and dependency diagrams;
- process flows;
- cutaway / exploded views;
- technical HUDs;
- labels and lower thirds;
- animated typography;
- data-driven graphics;
- historical document / archive treatments.

For each type explain:
- what type of information it communicates;
- when it is better than a cinematic scene;
- when a cinematic scene is better;
- how much information can be shown at once;
- hierarchy, layout and typography;
- colour and accessibility;
- animation order and reading time;
- how the narrator should direct the audience's attention;
- how to distinguish verified data from illustrative explanation;
- how to avoid inventing historical facts or misleading scale.

Explain which elements should be built deterministically with vector graphics / Python / Blender and which parts can be generated as background imagery. Text, precise labels and numerical data must not depend on a generative image model rendering legible text.

---

## 15. Tool implementation research — LTX, Blender, Python and FFmpeg

This is a central deliverable. Do not simply state that a technique is possible. Research **how** it is achieved, which tool is best suited, what the limitations are and what a reliable hybrid workflow looks like.

### 15.1 LTX video generation

Research exact current LTX products and variants, separating:
- local open-weight / local inference implementations;
- official hosted APIs;
- third-party hosted endpoints;
- different model versions and revisions;
- image-to-video versus text-to-video;
- keyframe / first-frame / last-frame conditioning;
- any actual audio-to-video or native-audio capability.

For every exact variant report:
- exact model and version / revision;
- exact local entry point, package or hosted endpoint;
- source-image requirements;
- supported resolution and aspect ratio;
- FPS and duration options;
- frame-count quantisation rules;
- conditioning / reference support;
- camera and motion controls, including exact parameter names if they exist;
- whether camera control is an explicit parameter or only a natural-language prompt request;
- prompt and negative-prompt behaviour;
- keyframe / extension / continuation support;
- audio generation / conditioning support;
- reproducibility and seed behaviour;
- concurrency, hardware and memory requirements;
- current availability and pricing, where verifiable;
- licence and commercial-use terms;
- known limitations and failure patterns.

Do not transfer a rule from a local model to a hosted API simply because both use the LTX name. Do not assume that a cinematic camera move written in a prompt is reliably executed. Classify every capability as verified, partially verified, unknown or not tested.

### 15.2 Blender production techniques

Research Blender as a deterministic production tool, not merely as a 3D modelling application.

Cover practical use of:
- camera rigs and focal length animation;
- dolly, crane, orbit, tracking and handheld rigs;
- proxy geometry and animatics;
- low-poly / greybox scene blocking;
- digital doubles and stylised characters;
- Geometry Nodes and instancing;
- crowd and formation simulation;
- rigid-body interactions;
- particles and debris;
- smoke, dust, fire and volumetrics;
- cloth, flags and secondary motion;
- depth, normal, shadow and vector passes;
- compositing;
- camera projection and 2.5D projection;
- scene lighting and rendering;
- render layers and passes;
- motion blur;
- camera matching and continuity;
- use of Blender as a previs / camera-control layer for generated imagery.

Explain which tasks should use simple proxies rather than expensive detailed assets. Identify where Blender gives precise control that LTX cannot guarantee, and where Blender is unnecessary overhead.

### 15.3 Python production techniques

Research realistic deterministic workflows using appropriate Python libraries and techniques, such as:
- Pillow / PIL;
- NumPy;
- OpenCV;
- vector drawing / SVG workflows;
- Matplotlib or other chart renderers where suitable;
- image masks and alpha compositing;
- perspective transforms;
- image registration and tracking;
- optical flow;
- depth-map based parallax;
- 2.5D layer separation;
- easing and keyframe interpolation;
- camera pan / zoom / crop;
- animated objects and typography;
- procedural particles;
- map projection and vector geography;
- frame-by-frame deterministic rendering;
- automated audio / video QA and measurement.

For each workflow state its strengths, limits, likely artefacts and performance implications. Do not recommend machine-learning dependencies when deterministic geometry or vector drawing is sufficient.

### 15.4 FFmpeg techniques

Research exact current FFmpeg filters and practical uses for:
- scale, crop, pad and rotate;
- zoompan;
- overlay;
- drawtext;
- blend and compositing;
- xfade and transitions;
- color balance / curves / eq / LUT workflows;
- blur and sharpening;
- vignette and grain;
- motion blur approximations;
- speed changes and interpolation;
- audio mixing and routing;
- volume automation;
- EQ and compression filters;
- sidechaincompress;
- loudnorm and true-peak-aware mastering workflows;
- acrossfade, adelay, afade and amix;
- channel layout and stereo processing;
- frame-rate conversion and final encoding.

For every filter or filter chain, link the official FFmpeg documentation and explain its actual semantics. Distinguish a visual approximation from a physically correct camera or sound process.

### 15.5 Technique-to-tool matrix

For every significant technique, compare the best practical implementation:

| Technique | LTX | Blender | Python | FFmpeg | Recommended route | Main limitation |
|---|---|---|---|---|---|---|

Use capability labels:
- native / directly supported;
- prompt-driven / probabilistic;
- deterministic / scripted;
- approximate / simulated;
- unsupported;
- unknown / not verified.

Do not mark a technique as natively supported merely because a prompt can describe it.

### 15.6 Hybrid production recipes

Provide step-by-step hybrid workflows for at least these examples:

1. A continuous overhead battle move: Blender or Python geography / blocking, first-frame composition, LTX animation, deterministic edit and sound sync.
2. A close-up character action: identity reference, anticipation / peak / settle, LTX motion, continuity and Foley.
3. A dialogue scene: master scene layout, camera coverage, dialogue timing, reaction shots, audio-led cuts and final mix.
4. A dramatic reveal: controlled first frame, focus / framing strategy, sound dropout, reveal cue and reaction.
5. A moving historical map: verified geographic data, vector rendering, camera progression, labels, date / event timing and sound design.
6. A statistic / comparison graphic: sourced values, Python rendering, animation timing, typography and narration sync.
7. A still-image cinematic shot: depth map, segmentation, parallax, particles / atmosphere, compositing and final movement.
8. A battle aftermath: restrained camera movement, environmental ambience, limited score, Foley and intentional silence.

Each workflow should identify which steps are deterministic, which depend on generative output, which must be reviewed by a human and which can be automatically validated.

---

## 16. Scene archetype library — visual AND audio grammar

Create a practical taxonomy. Add archetypes if evidence supports them; do not force every scene into a fixed list.

At minimum cover:

1. Large-scale battle / army movement / siege.
2. Small-scale fight / duel / physical confrontation.
3. Two-person dialogue / negotiation / argument.
4. Group dialogue / council / assembly.
5. Solitary emotion / realisation / reaction.
6. Crafting / building / repairing / hunting / preparing / manual work.
7. Travel / marching / riding / sailing / traversal.
8. Exploration / discovery / entering an unknown place.
9. Reveal / surprise / object discovery / reversal.
10. Chase / escape / pursuit.
11. Environmental establishing / weather / landscape / city / camp.
12. Map / route / tactical geography / territorial change.
13. Abstract explanation / mechanism / calculation / comparison.
14. Transformation / construction / destruction / passage of time.
15. Crowd / ceremony / ritual / public event.
16. Aftermath / loss / quiet reflection / transition.
17. Narrator-only explanation over visual evidence.
18. Opening hook / cold open.
19. Climax / payoff.
20. Ending / coda.

For each archetype create a structured technique card with:

- narrative purpose;
- audience takeaway;
- emotional objective;
- visual scale and hierarchy;
- preferred shot sequence patterns;
- suitable shot sizes and camera positions;
- useful lens / perspective choices;
- camera movement and subject movement;
- blocking and continuity requirements;
- composition and depth;
- lighting, palette and atmosphere;
- animation / motion principles;
- preferred visual lane or justified lane alternatives;
- first-frame requirements;
- image prompt structure;
- video motion prompt structure;
- suitable duration range and motivated split points;
- edit and transition grammar;
- narration / dialogue relation;
- music / score direction;
- ambience;
- Foley and sound effects;
- intentional silence opportunities;
- best tool route across LTX / Blender / Python / FFmpeg;
- common failure modes;
- visual QA;
- audio QA;
- evidence references.

The archetype must produce a distinct visual and sonic language. A battle should not look and sound like a crafting scene with extra movement. A quiet reveal should not use the same editing and score treatment as a chase.

Do not force every archetype into VIDEO. Explain when STILL or HELPER carries the information better. Do not sacrifice continuity or clarity to meet the visual percentages.

---

## 17. Required worked examples

Work through these examples in detail. Each must include a storyboard / edit plan, visual technique choices, sound design, music direction, tool pathway and QA.

### Example A — Large-scale battle

Two historical armies approach, manoeuvre, clash and one side begins to retreat.

Design a cinematic sequence that communicates:
- battlefield geography;
- opposing sides and their positions;
- the scale of both forces;
- the tactical cause of the clash;
- the moment of impact;
- the change in the battlefield;
- the consequence.

Include:
- wide geography / overhead or elevated composition;
- tactical map alternative;
- formation movement;
- ground-level action;
- close-up inserts where justified;
- screen direction and spatial continuity;
- camera choreography;
- dust, smoke, flags, debris and environmental motion;
- score arc, percussion, low-frequency impacts and silence;
- battlefield ambience and Foley layers;
- narration placement and any character dialogue;
- one approximately ten-second continuous non-dialogue action shot where model capability supports it;
- first-frame image prompt;
- matching image-to-video motion prompt;
- Blender / Python alternative for exact geography;
- LTX capability caveats;
- edit and sound-sync plan;
- QA for geography, motion, direction, visual clarity and audio perspective.

Do not copy the look of a named film or television series. Study the underlying cinematic techniques of large-scale battle staging.

### Example B — Two-character confrontation

Two historically grounded characters negotiate, disagree or threaten one another.

Include:
- environment geography and fixed landmarks;
- master / two-shot;
- over-the-shoulder and reverse coverage;
- close-ups and listener reactions;
- 180-degree axis and eyelines;
- camera height, lens and movement;
- facial acting and subtext;
- narration hand-off;
- visible lip-sync versus off-screen dialogue;
- J-cuts / L-cuts and reaction timing;
- voice distinction and performance;
- room tone, location ambience and small Foley;
- score restraint and any silence beat;
- matched first-frame and video prompts;
- tool choices and QA.

Do not require every line to have a visible speaking face or every dialogue scene to use identical shot/reverse-shot coverage.

### Example C — Historical crafting / manual work

A character creates a tool, constructs a shelter, prepares food or repairs equipment.

Include:
- establishing the task and environment;
- readable body mechanics;
- medium action coverage;
- hands / tool inserts;
- cause and effect;
- material state changes;
- prop continuity;
- sound perspective and detailed Foley;
- relevant room / environmental ambience;
- score choice or deliberate absence of music;
- continuous-action and motivated-cut alternatives;
- LTX, Blender and 2.5D / Python options.

### Example D — Discovery and reveal

A character sees something that changes the audience's understanding.

Include:
- what the audience sees first;
- when the character notices it;
- gaze direction and framing;
- object-first versus character-first reveal;
- focus / depth or compositing alternative;
- reaction shot;
- music dropout or tension cue;
- sound reveal / sting timing;
- how the edit preserves surprise.

### Example E — Explanatory geography / tactical strategy

Explain a strategic change using a combination of cinematic shots and a map.

Include:
- when the map is more informative than a generated cinematic scene;
- geographic truth and source verification;
- faction / route / territory encoding;
- camera scale progression;
- label and legend hierarchy;
- event timing;
- narration-to-map synchronisation;
- sound and music restraint;
- transitions from map to physical scene;
- exact Python / Blender / FFmpeg roles.

### Example F — Travel / traversal

A character or group travels through a changing environment.

Include:
- establishing geography;
- direction and destination;
- tracking versus static coverage;
- weather and environmental motion;
- transitions across time and distance;
- pace, ambience, Foley and music evolution.

### Example G — Aftermath / loss / quiet reflection

A battle, disaster or major decision has consequences.

Include:
- composition and scale;
- restrained camera movement;
- environmental details;
- human reaction;
- reduced music and sound density;
- silence / room tone;
- colour and light changes;
- a meaningful transition into the next story beat.

### Example H — Opening hook and final payoff

Design two contrasting sequences:
- the opening promise that creates curiosity without explaining everything;
- the final payoff that answers the dramatic question and rewards the opening setup.

Explain visual motifs, sound motifs, music callback / transformation, pacing, contrast and final image design.

---

## 18. Twelve-minute audiovisual blueprint

Provide a practical **12-minute reference blueprint**, not a rigid formula.

It should show how story structure, visuals, spoken content, music and sound can evolve together across an episode.

Include:
- narrative phase / function;
- audience question or information need;
- emotional state;
- visual technique families;
- possible VIDEO / STILL / HELPER uses;
- narration / character dialogue purpose;
- music state and transition;
- ambience / Foley / SFX strategy;
- editing rhythm and transition choices;
- opportunities for intentional silence;
- continuity requirements;
- estimated duration range.

Demonstrate the two independent planning dimensions:
1. 60 / 30 / 10 visual-runtime target, with its tolerance;
2. 70–80 / 20–30 narrator/dialogue spoken-word target, midpoint 75/25, with 30% dialogue / 70% narration as the upper dialogue boundary.

Do not force these percentages to line up in time. Show examples where:
- narration runs over VIDEO;
- narration runs over STILL;
- narration runs over HELPER;
- dialogue occurs over a short lip-sync shot;
- a dialogue scene continues over reaction shots / inserts;
- a VIDEO action shot has no dialogue;
- silence and music-only sections occur without changing the spoken-word calculation.

Explain how to measure the targets accurately and what can only be confirmed after the actual edit and final audio are assembled.

---

## 19. Reusable technique-card format

For consistency, every researched technique should be documented in this structure:

### Technique: [exact professional name]

- **Discipline:** cinematography / editing / lighting / colour / animation / motion graphics / narration / dialogue / music / sound design / mixing / mastering.
- **What it is:** clear technical definition.
- **What the audience experiences:** perceptual result.
- **Purpose:** narrative or emotional function.
- **Use it when:** concrete story / scene / beat conditions.
- **Avoid it when:** concrete counterconditions.
- **Visual requirements:** composition, subject, environment and starting state.
- **Audio requirements:** voice, score, ambience, Foley, effects and silence as applicable.
- **Execution steps:** practical sequence.
- **LTX route:** native support, prompt-based approximation, unsupported or unknown; exact model evidence.
- **Blender route:** concrete scene / camera / animation / render process.
- **Python route:** relevant deterministic operations and library classes / functions.
- **FFmpeg route:** exact filters / filter chain where appropriate.
- **Hybrid route:** recommended division of labour.
- **Common failures:** what goes wrong and why.
- **Quality check:** how to judge or measure the result.
- **Cost / complexity:** low / medium / high, with explanation; no invented dollar figures.
- **Evidence:** direct sources and their quality.
- **Confidence:** verified / partially verified / hypothesis.

If a technique does not apply to one of the four tools, explicitly mark it as not applicable rather than inventing a workaround.

---

## 20. Technical and quality verification

Research how to verify the result, not just how to create it.

### Visual QA

Cover:
- composition and focus hierarchy;
- subject readability;
- image / video prompt agreement;
- identity and costume consistency;
- prop continuity;
- spatial geography and screen direction;
- camera movement and easing;
- action start / peak / settle;
- motion artefacts;
- temporal consistency;
- lighting and colour continuity;
- text / graphic legibility;
- historical accuracy;
- lane classification and runtime accounting.

### Audio QA

Cover:
- speech intelligibility;
- voice continuity;
- word / frame sync;
- dialogue timing and interruptions;
- music masking;
- SFX masking;
- ambience continuity;
- Foley sync;
- clipping and true peak;
- loudness and dynamics;
- stereo and mono compatibility;
- silence intentionality;
- final export integrity.

### Combined audio-visual QA

Explain how to check:
- an impact sound matches the visible impact;
- a camera move has the right sound cue, or intentionally has none;
- music changes at the correct dramatic beat;
- dialogue and reaction coverage are aligned;
- a map event begins when its spoken information arrives;
- a reveal is not spoiled by the sound or picture arriving too early;
- visual and audio perspective agree;
- the ending's sound and final image provide a coherent payoff.

Separate measurable technical checks from human editorial judgement. Do not claim that an automated metric can fully determine whether a scene is cinematic or emotionally effective.

---

## 21. Required final deliverables

Return one integrated, substantial research report, primarily in Georgian, preserving exact English technical terminology.

### A. Executive summary

Identify the most important cinematic and audio techniques for a 12-minute animated historical docudrama. State the highest-value craft knowledge and the most consequential limitations of current production tools.

### B. Education / academy catalogue

List the best current structured learning sources by discipline, with course / curriculum detail, relevance, access and source evidence.

### C. Visual craft encyclopedia

Organise visual storytelling, cinematography, framing, camera, lighting, colour, animation, production design and motion graphics techniques.

### D. Editing craft encyclopedia

Explain cut grammar, transitions, pacing, continuity, montage and sound-led editing.

### E. Audio craft encyclopedia

Organise narration, dialogue, voice performance, music, ambience, Foley, SFX, mixing, mastering and delivery.

### F. Scene-archetype library

Provide distinct visual AND audio recipes for every required archetype.

### G. LTX / Blender / Python / FFmpeg capability matrix

Separate exact model / software variants, native capabilities, prompt-based approximations, deterministic operations, limitations and unknowns.

### H. Hybrid production recipes

Provide the eight worked tool workflows from Section 15.6.

### I. Twelve-minute audiovisual blueprint

Show story, visual, spoken content, music, ambience, effects and editing as coordinated but independent dimensions.

### J. Reusable technique cards

Provide complete technique cards in the format of Section 19. Prioritise techniques with the greatest likely creative value.

### K. Source register and evidence gaps

Provide direct URLs, source metadata, claim mapping, confidence and unresolved questions.

### L. Practical learning roadmap

Recommend which courses, manuals and technique families should be studied first, second and third. Separate free resources from paid education and explain the expected skill gained from each.

---

## 22. Strict exclusions — do not investigate or implement the repository

This instruction is important.

**Do not audit the Explainer Engine repository. Do not inspect GitHub branches, files, source code, schemas, tests, agents, skills, TODOs, commit history or implementation status. Do not produce a repository map, code architecture proposal, project-specific schema, migration plan or file-by-file recommendations.**

The project context and creative constraints above are sufficient for this independent craft research.

The later integration reviewer will:
- inspect the actual repository;
- determine which findings are already implemented;
- identify gaps and duplication;
- map the researched techniques to existing modules;
- recommend the smallest compatible changes.

Your role is to supply accurate, comprehensive external knowledge and tool-specific production methods so this later integration is based on evidence rather than assumptions.

Do not spend research time proving which feature currently exists in our project. Do not make claims about our implementation.

Do not edit or commit this brief. Do not generate paid images, videos, music or sound assets. Do not start cloud or GPU jobs. Use public documentation, education resources, research literature and reproducible analysis only.

---

## 23. Final research questions

The final report must answer these questions directly:

1. Which professional visual techniques are most effective for each major story / scene archetype?
2. What exactly makes a shot feel cinematic rather than merely animated?
3. How should shot size, camera position, lens, perspective, movement, blocking and lighting work together?
4. Which camera techniques can be convincingly simulated with LTX, and which need Blender or deterministic compositing?
5. Which apparent camera moves are only digital zoom / crop approximations, and what visual differences do they create?
6. How should first-frame composition be designed for the movement that follows?
7. How can historical battle scenes communicate large-scale geography, tactics, momentum, impact and aftermath?
8. How should dialogue scenes use master shots, over-the-shoulder coverage, reactions, inserts, eyelines and audio-led cuts without becoming repetitive?
9. How should maps, statistics, diagrams and motion graphics be designed for fast comprehension?
10. Which animation principles are most important for believable generated movement?
11. How should lighting, atmosphere and colour change with narrative emotion while preserving one visual identity?
12. Which editing techniques best support hooks, exposition, escalation, action, reveals, payoff and reflection?
13. How should narration and character dialogue be performed, paced and edited?
14. How do professional film scores create tension, emotional continuity, character identity and payoff?
15. How should ambience, Foley and sound effects communicate physical environment, distance, material, scale and impact?
16. How do professional mixers preserve dialogue clarity while maintaining a rich cinematic soundscape?
17. Which audio measurements and delivery standards are relevant, and which are often incorrectly treated as universal rules?
18. What can LTX do natively, what is only prompt-driven, and what remains unverified for every exact model / endpoint?
19. What should Blender do that is difficult or unreliable for LTX?
20. What should Python do deterministically instead of using generative AI?
21. What should FFmpeg do in post-production, and what should not be forced into FFmpeg?
22. What hybrid pipelines produce the best balance of quality, control, continuity, cost and repeatability?
23. How should all of these techniques work together across a 12-minute video while preserving the independent 60/30/10 visual target and 70–80 / 20–30 spoken-word target?
24. Which techniques are high-value defaults, which should remain optional creative choices, and which claims need a real sample test before being trusted?

**The standard for completion:** a production specialist should be able to take a story beat, understand what the audience needs to see and hear, choose a justified professional technique, prepare the necessary starting composition, plan the movement and sound, select the most reliable tool or hybrid route, and know how to evaluate the result. The report must make that decision process concrete, evidence-based and reusable.