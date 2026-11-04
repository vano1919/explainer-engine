# Gemini / Argon Research Brief — Visual Grammar, Shot Design and Image-to-Video Continuity

**Date:** 2026-11-04  
**Repository:** https://github.com/vano1919/explainer-engine  
**Review branch:** claude/master-mold-ready-2026-11-04  
**Working rule:** READ-ONLY RESEARCH AND DESIGN. Do not edit files, generate production assets, run paid APIs, launch GPU pods, change settings, commit, push, merge, upload or publish.

## 1. Your role

Act as an independent research and architecture team combining:
- an animation director and storyboard artist;
- a cinematographer / camera-layout specialist;
- a generative image and image-to-video engineer;
- an editor who understands visual rhythm and continuity;
- a QA architect who can translate creative intent into testable shot contracts;
- a skeptical technical reviewer who can distinguish real implementation from proposals.

Do not validate the current repository merely because it exists. Do not recommend a rewrite because a new technique is fashionable. Preserve working systems and creator decisions. Find the missing visual-design logic, research it, and propose the smallest coherent extension that gives the story team meaningful creative control.

The report must answer one core question:

**How should the system decide, from the story and script stage onward, what the audience should see, how the first image should be composed, how the shot should move, what camera language it should use, and how the image prompt and video prompt stay visually consistent?**

The goal is controlled creative freedom: a strong shared visual language with flexible scene-specific choices, not a rigid checklist that makes every episode look identical.

## 2. Project context — treat the repository as evidence

The project is CrossWorld Chronicles / Explainer Engine: an English-language, YouTube-oriented animated historical / counterfactual docudrama and explainer workflow. The repository, not this paragraph, is the authority for actual implementation and current creative decisions. Inspect the current branch HEAD before relying on any SHA, file path, model, provider, resolution or implementation claim.

The currently recorded creator rules that must remain separate are:

### Speech mix — D-95
- Target 70–80% narrator narration and 20–30% voiced character dialogue, measured by audible spoken-word count at script/variant validation.
- Planning midpoint: 75/25.
- Exclude lines marked `voiced: false`.
- This is not a visual-lane ratio and does not mean 20–30% of all shots must show characters speaking.
- The spoken-word ratio is an authoring proxy, not proof of the final wall-clock audio-time ratio.

### Visual runtime mix — D-93 / BP-109
- 60% VIDEO, including non-dialogue generated action.
- 30% STILL, including still compositions that may be layered, animated or moved programmatically.
- 10% HELPER, including maps, diagrams, calculations, counters, progress indicators and similar explanatory graphics.
- Existing tolerance is ±5 percentage points. Read the canonical registry for exact enforcement semantics; do not reinterpret the tolerance or make percentages add up by independently changing each lane.
- These are visual runtime categories, not speech categories. A VIDEO shot can carry narration, dialogue, sound design, music or silence. STILL and HELPER can also sit under narration.

### Shot duration — D-95 / BP-108
- Visible character dialogue / lip-sync coverage has a 5-second maximum planning target.
- Non-dialogue VIDEO action may use 10–15-second shots when an uninterrupted action, geography or camera move benefits from continuity.
- Fifteen seconds is a planning ceiling, not a provider guarantee. Actual selected model, API/adapter, resolution, frame rate, generation mode and frame quantization control what can be rendered.
- Do not impose the dialogue limit on non-dialogue VIDEO. Do not apply STILL-specific hold limits to VIDEO.
- Treat shot count and shot duration as different dimensions. For example, a ten-second continuous shot is not the same thing as a sequence of ten shots.

Read the canonical decision log, sourced rule registry, Master Mold, current production schemas, agents, skills, validators, tests, current configuration and relevant progress history before proposing changes. D-95 is documented here:
https://github.com/vano1919/explainer-engine/blob/claude/master-mold-ready-2026-11-04/docs/wip/CREATOR_OVERRIDE_NARRATION_VISUAL_SHOT_DURATIONS_2026-11-04.md

## 3. Problem to solve

The project has broad visual lanes, but the system needs a more explicit visual-grammar layer that maps story meaning to visual execution.

At present, a script beat may establish what happens and what is said without sufficiently determining:
- whether the audience needs a wide geography shot, a medium action shot, a close-up, a reaction, an overhead layout, a tracking move, a map, a diagram or a layered still;
- the composition required in the initial generated image;
- the camera position, camera height, viewing angle, shot size, lens / virtual field of view, depth and perspective;
- the spatial relationship and screen direction of multiple characters, objects, groups or armies;
- the main subject's action and its start/end state;
- what should move, what must remain stable, and what the camera should do over time;
- the correct visual duration and whether the action should be one continuous shot or multiple motivated cuts;
- the color palette, lighting, atmosphere, environment and visual hierarchy;
- how the image-generation prompt and the LTX / other image-to-video prompt describe the same shot rather than contradict each other.

This causes a critical risk: the first image can be composed for one kind of scene, while the video prompt asks the model to animate a different scene. The result may be visually incoherent, difficult to animate, or structurally unsuitable for the story.

Do not solve this by adding many hard-coded prohibitions. First create a taxonomy and decision framework that helps the system choose the right technique.

## 4. Audit the actual repository before recommending architecture

Inspect the latest branch state and cite immutable commit SHAs and exact repository paths/line ranges. At minimum, inspect:

1. Project entry points and the actual lifecycle from research/story/script to shot planning, image generation, video generation, assembly, QA and delivery.
2. Master Mold Markdown, JSON contract, verified shot digest, D-93, D-95, BP-109, BP-108, BP-170 and other relevant visual rules.
3. The actual story, scene, beat, shot, continuity and prompt data structures.
4. Image-generation and image-editing providers, reference-image handling, style/character references, image dimensions and aspect-ratio decisions.
5. Video-generation adapters and model routing, especially any actual LTX pipeline. Verify whether LTX-2.5, another LTX version, a hosted LTX API, a local pipeline, or only a proposed stub exists. Do not assume a TODO-only file is working production code.
6. Still-image composition, parallax, Python layers, object movement, maps, diagrams and helper graphics.
7. Character identity, cast references, pose, facial expression, camera, environment, lighting and continuity systems.
8. Shot-duration logic, frame quantization, output resolution, frame rate, editing timeline and provider limits.
9. Prompt compilers, agents, skills, validators, lint rules, tests, fixtures and downstream callers.
10. Current style references and approved visual look. Distinguish creator-approved decisions from experimental or retired styles.

For each important component, classify it as:
- VERIFIED IMPLEMENTED;
- PARTIALLY IMPLEMENTED;
- DOCUMENTED BUT NOT IMPLEMENTED;
- TODO-ONLY STUB;
- MISSING;
- DEPRECATED / RETIRED;
- UNVERIFIED.

Do not confuse a module path with a working feature. Trace caller-to-callee and input/output contracts. If a file or referenced source cannot be found, state that plainly.

## 5. Build a scene-to-visual-technique taxonomy

Research and propose a useful taxonomy of scene archetypes. These are candidate families, not an exhaustive list or fixed quota:

1. Large-scale battle / army movement / siege.
2. Small-scale fight / duel / physical confrontation.
3. Two-person dialogue / negotiation / argument.
4. Group dialogue / council / assembly.
5. Solitary character emotion / realization / reaction.
6. Crafting / building / repairing / hunting / preparing / manual work.
7. Travel / marching / riding / sailing / traversal.
8. Exploration / discovery / entering an unknown place.
9. Reveal / surprise / object discovery / reversal.
10. Chase / escape / pursuit.
11. Environmental establishing / weather / landscape / city / camp.
12. Map / route / tactical geography / change of territory.
13. Abstract explanation / mechanism / calculation / comparison.
14. Transformation / construction / destruction / passage of time.
15. Crowd / ceremony / ritual / public event.
16. Aftermath / loss / quiet reflection / transition.
17. Any additional archetypes that repository and research evidence justify.

For each archetype, explain:
- narrative purpose and the audience information it must communicate;
- ideal visual scale and hierarchy;
- recommended shot sequence patterns (not mandatory shot counts);
- suitable shot sizes: extreme wide, wide, full, medium, medium close-up, close-up, extreme close-up, insert, overhead, etc.;
- camera position and height: eye-level, low, high, overhead / top-down, ground-level, profile, three-quarter, POV, over-the-shoulder, and other justified views;
- camera movement: static, pan, tilt, push-in, pull-out, tracking, orbit, crane / aerial drift, handheld-like movement or other movements that fit the style and model;
- subject movement, background movement and object-state changes;
- spatial blocking, screen direction, eye-lines and continuity requirements;
- composition, depth layers, negative space, focus hierarchy and perspective;
- color palette, lighting, atmosphere and environment treatment;
- whether the scene should use VIDEO, STILL or HELPER, and why;
- whether image-to-video conditioning is useful or text-to-video is better;
- the initial image composition required for successful animation;
- the video prompt's motion plan;
- recommended duration range and when to split into motivated cuts;
- common failure modes and how to prevent them without over-constraining creativity.

Do not force every archetype into VIDEO. Do not choose VIDEO solely to satisfy the 60% target if it produces worse storytelling, more cost or weaker continuity. Explain how the overall target can be achieved naturally through scene choices.

## 6. Work through these concrete examples in detail

These are required worked examples. Use them to demonstrate the visual grammar, not as the only approved styles.

### Example A — large battle / overhead tactical choreography

Imagine a historical battle where two forces approach and clash across a readable battlefield. The shot may need to run around ten seconds as one continuous action if model capability and visual clarity support it.

Design:
- initial frame with clear battlefield geography and opposing sides;
- elevated / aerial / top-down or oblique overhead view where appropriate;
- readable army formations, scale, direction of movement and central point of conflict;
- clear foreground / middle-ground / background layers;
- no arbitrary floating labels, arrows, UI or textual annotations in a cinematic frame;
- avoid model-hostile demands for exact counts of hundreds of individuals unless a precise count is narratively important;
- specify which groups move, in which direction, at what pace, and what the camera does;
- maintain spatial continuity and avoid changing the battlefield layout between the reference image and the video.

Provide:
1. a storyboard / shot breakdown;
2. a first-frame image prompt;
3. an image-to-video prompt for LTX or the verified current video model;
4. a separate text-to-video alternative if it is demonstrably useful;
5. duration and frame-rate recommendation based on the actual selected model;
6. QA checks for geography, direction, composition, motion and continuity.

### Example B — two-character dialogue / confrontation

Design a scene where two characters talk in a historically grounded environment.

Specify:
- environment layout, entrances, windows, fires, tables, props and spatial anchors;
- who stands or sits where, body orientation and eye-lines;
- master / establishing shot, over-the-shoulder coverage, singles, reverse angles, close-ups and listener reactions where motivated;
- camera height, angle, distance, composition and movement;
- facial expression and the emotional change through the line;
- continuity of screen direction, eye-line and the 180-degree axis;
- which character is visibly speaking, when to show the listener, and when narration can carry the information instead;
- how to cover dialogue without forcing every spoken line into visible lip-sync;
- the five-second visible-dialogue planning target from D-95.

Provide a shot-by-shot example with matching image prompts and video prompts. Explain how each angle is derived from the same scene geography and how the edit avoids continuity errors. Do not turn conventional coverage into a rigid requirement when a single strong composition is better.

### Example C — Stone Age / historical manual work or crafting

Design a character making a tool, building a shelter, preparing food, shaping stone, working wood or completing another physical task.

Show why this requires different visual grammar from a battle or a dialogue scene:
- establish the environment and task;
- show the character's body mechanics and tool use;
- use appropriate medium shots and hand / tool inserts;
- show meaningful material or object-state changes;
- track cause and effect across the process;
- use camera distance and angle that make the work legible;
- avoid repetitive generic close-ups or arbitrary cuts;
- preserve prop continuity, hand position, tool identity and the direction of work.

Provide a continuous-action option and a cut-based option, with the required initial image and motion prompts.

### Example D — discovery / reveal / emotional reaction

Design a reveal where a character notices something significant. Use staging, gaze, camera distance, focus and reaction timing to guide attention. Separate the discovery image from the movement and reaction prompt. Explain when to show the object first, the character first, or both in one composition.

### Example E — explanatory geography / strategy or concept

Show how to choose between a cinematic visual, HELPER map/diagram and STILL composition. Explain how the information should be layered, animated and labeled without putting unnecessary text into a generative image. Identify which elements should be generated and which should be deterministic Python graphics.

## 7. Define one coherent visual-intent contract

Propose the smallest useful structured representation that carries visual intent from script to final prompts. Do not create a large schema before proving each field is needed.

Consider these fields and challenge them:
- story beat ID and source-script reference;
- narrative purpose / audience takeaway;
- scene archetype and shot archetype;
- visual lane: VIDEO / STILL / HELPER;
- key subjects, characters, props and environment;
- time period and location;
- action verb, action phase and causal outcome;
- start state and intended end state;
- composition and subject placement;
- shot size, camera angle, camera position / height and virtual lens or field of view;
- foreground / middle-ground / background;
- character blocking, screen direction, eye-lines and action axis;
- subject motion, camera motion and environmental motion;
- focus hierarchy, depth, lighting and palette;
- first-frame / keyframe requirements;
- reference images and continuity anchors;
- audio relation: narrator, voiced dialogue, sound design, music or silence;
- intended duration, frame rate and frame count;
- model, adapter and generation mode;
- image prompt, video prompt and negative constraints;
- split / extend / retake rationale;
- QA assertions.

For each proposed field, state:
- why it is needed;
- whether it belongs at story, scene, shot, asset or generation-adapter level;
- whether it is a hard requirement, optional, inferred or generated later;
- how the value is validated;
- which existing repository field can already hold it;
- whether adding a new field would duplicate a current source of truth.

Recommend one canonical visual-intent object and a compilation path:
1. script / story beat → semantic visual intention;
2. visual planner → scene and shot grammar;
3. asset planner → VIDEO / STILL / HELPER and reference strategy;
4. keyframe or image prompt compiler → exact static composition;
5. video prompt compiler → compatible temporal motion / camera plan;
6. provider adapter → model-specific dimensions, frames, duration and parameters;
7. edit / assembly → motivated cuts and continuity;
8. QA → semantic match, composition, motion and consistency.

A script writer should know the visual intent early, but do not force the writer to manually invent every low-level camera parameter. Decide which details should be authored, suggested by a planner, inferred from scene context or set by the provider adapter.


### 7.1 Keep visual intent, asset provenance and provider capabilities separate

Do not overload the visual-intent object with every execution detail. Research whether two small supporting records are needed, and prefer existing contracts where they already serve the purpose.

**Asset / generation provenance record — candidate fields to evaluate:**
- stable shot ID and source story-beat ID;
- canonical visual-intent reference and hash/version;
- input reference-image IDs and hashes;
- for I2V, the exact accepted starting-frame asset ID and SHA-256;
- image/video prompt text or prompt hash, with compiler/version;
- provider, exact model ID, model revision, adapter/endpoint and local-vs-hosted mode;
- seed and generation parameters that materially affect output;
- parent/derived asset relationship (accepted keyframe → generated video);
- output asset path/ID and SHA-256;
- actual output width, height, FPS, frame count and duration;
- generation/acceptance status and any retake/extension lineage.

Explain which data already exists in the job manifest, route, shot spec, cache key or asset library. Do not duplicate it merely to create a new manifest. The key requirement is that every rendered asset can be traced to the intent, source frame, prompt compiler, model/version and parameters that produced it.

**Provider capability record — keep it adapter-specific:**
- exact provider and model/API identifier;
- local package/checkpoint versus hosted endpoint;
- model revision/API version and date checked;
- supported input/output dimensions and aspect ratios;
- supported FPS and duration options/limits;
- frame-count quantization requirements;
- image/reference conditioning support;
- documented camera/motion controls;
- prompt and negative-prompt semantics;
- audio conditioning/generation support, if applicable;
- capability state: supported, unsupported, unknown or not-tested;
- source URL and the exact claim supported.

Do not merge provider capabilities into creator-approved visual rules. A provider capability can change without changing the creative intent.

## 8. Image prompt and video prompt must be a matched pair

This is one of the most important requirements.

For an image-conditioned video shot:
- The image prompt defines the exact starting composition: subject identity, layout, positions, environment, props, camera framing, perspective, palette, lighting and action pre-state.
- The video prompt defines the temporal evolution: subject motion, camera motion, environmental motion, pace, direction, interaction and intended end state.
- The two prompts must not demand different characters, locations, props, camera sides, lighting or spatial layouts.
- Do not blindly repeat a long description of the still image in the video prompt if the model already receives that image. Determine the correct prompt semantics from the actual model/API documentation and test them.
- State what should remain stable and what should change.
- Do not ask a model to invent a completely new scene when the intention is to animate the supplied composition.
- When image conditioning is not the best approach, explain why text-to-video or a deterministic STILL / HELPER approach is preferable.

Research and report model-specific differences. For example, official Google image-to-video guidance recommends using a clear source image and concentrating the video prompt on motion rather than re-describing the entire image. Treat this as a useful principle to verify—not as proof that every LTX version behaves identically:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/best-practice

Start with the actual LTX documentation and verify the precise model and API that this repository uses:
https://docs.ltx.video/

## 9. Technical compatibility research — current, exact and provider-specific

Do not assume product capabilities from memory or from a model family name. Inspect the repo's pinned versions and exact adapter first. Then verify official current documentation for each relevant integration.

At minimum research:
- current image model and version (for example, the repo's Qwen-Image pin if still current);
- current video model and version (LTX variant or any alternative actually configured);
- local model versus hosted API differences;
- image-to-video versus text-to-video behavior;
- supported image dimensions, aspect ratios, input references and output dimensions;
- duration choices and max duration for each resolution / frame rate / mode;
- required frame-count multiples or quantization;
- prompt and negative-prompt support;
- camera controls and motion controls;
- character / reference consistency features;
- retake, extension and keyframe support;
- audio generation or audio conditioning where relevant;
- rate limits, concurrency, model availability and regional restrictions;
- credits, billing and cost per finished second/minute;
- licensing and commercial-use restrictions;
- known failure modes, retries and reproducibility.

For every technical capability, record the exact provider, model/version, API or local package, resolution, frame rate, duration, date accessed and source. Separate official capability from observed repository behavior and from your own hypothesis. If provider documentation and local adapter disagree, report the conflict rather than silently choosing one.

Do not use a single generic duration limit across all models. The D-95 15-second ceiling is conditional on the actual model limits. Do not infer that LTX is production-ready just because a TODO mentions it.


### Adapter-specific capability matrix (required)

Return a row for every exact adapter/model combination currently configured or seriously proposed. At minimum, separate each local LTX implementation from each hosted LTX API. Do not transfer a constraint from one to the other by name alone.

The matrix must include:
- exact model and revision/API version;
- exact local entrypoint or hosted endpoint;
- image conditioning behavior and accepted image requirements;
- output aspect ratios, dimensions, FPS, durations and frame-count rules;
- whether 8k+1 frame quantization applies, with direct evidence from that exact implementation;
- camera controls and their actual parameter names/semantics;
- any maximum-duration or resolution trade-off;
- runtime/provider limitations that affect the current adapter;
- status (verified, partially verified, unknown, not tested);
- direct primary source and access date.

The code's current KEYFRAME_LTX planning status is unavailable pending a real clip-pod dryrun. Your research must not upgrade that status to production-ready. A prompt compiler or route specification is not a working generation adapter.

## 10. Visual direction and consistency

Inspect the current approved character and style references. Preserve the existing look unless evidence and creator approval justify changing it.

Research how to specify:
- palette families and contrast relationships;
- day/night and interior/exterior lighting;
- atmosphere, fog, smoke, dust, weather and depth;
- environment and architecture appropriate to the era;
- scale and silhouette readability;
- character proportions, costume and prop identity;
- material rendering and texture;
- camera language consistent with the established style;
- foreground / background separation;
- visual continuity across shots, scenes and episodes.

Avoid defining color only as vague adjectives. Propose a practical palette representation, with a small set of roles (dominant, secondary, accent, shadow / atmosphere) and how they can vary by scene while remaining in the episode's visual identity.

Separate:
- global style bible;
- episode-level visual direction;
- scene-level visual plan;
- shot-level composition and motion;
- provider-specific render settings.

Do not add a new global palette, lens, camera grammar or art style as a hard rule without showing how it coexists with the existing system.

## 11. Creative quality versus mechanical restrictions

This must not become another over-constrained Mold.

Classify every recommendation as one of:
- HARD TECHNICAL LIMIT — imposed by a verified model / API / schema;
- EXISTING CREATOR DECISION — explicitly approved and recorded;
- STRONG DEFAULT — generally useful but overridable with a reason;
- OPTIONAL TECHNIQUE — selected when it serves the shot;
- EXPERIMENTAL HYPOTHESIS — requires a test;
- CREATOR DECISION REQUIRED — affects cost, style, scope or creative ownership.

Never upgrade a recommendation to a hard FAIL merely because it sounds professional. Explain which rules should be hard FAIL, which should be REVIEW, and which should remain creative choices. Do not create quotas such as “every scene must contain an overhead shot” or “every dialogue must use shot/reverse-shot.” Recommend a variety of techniques, not mandatory repetition.

The goal is to encode what must be consistent while leaving room for unexpected but coherent cinematic solutions.

## 12. Research and citation standard

Use current web research. Prefer:
1. official model / API documentation for technical capabilities;
2. official standards and documentation for file formats and measurement;
3. film-school, cinematography and animation references for craft principles;
4. peer-reviewed research where making empirical claims;
5. credible production case studies and expert demonstrations;
6. community reports only as secondary evidence, with caveats.

For every externally sourced factual claim:
- cite a direct URL next to the claim;
- provide title, publisher/author and publication or update date where available;
- provide access date;
- identify model / version / API where applicable;
- explain exactly what the source supports;
- classify source quality as primary, peer-reviewed, practitioner or anecdotal.

Do not cite a generic documentation home page as proof of a specific feature. Do not copy the same five sources into every section. Do not fabricate citations, publication dates, measured performance or model limits. If a claim cannot be verified, label it UNVERIFIED and state the exact evidence needed.

## 13. Required deliverables

Produce one integrated report, in Georgian prose where possible while retaining English technical terms and exact repository paths. Keep technical schemas, prompt templates and field names in English.

### A. Executive findings
- What is missing today?
- What is already implemented and reusable?
- Which gaps materially harm visual coherence or increase generation waste?
- What is the smallest architecture that addresses the gap?

### B. Current repository map
A table with stage, actual file/module, status, current contract, dependencies, tests, and evidence. Clearly distinguish working code from stubs and TODOs.

### C. Scene-archetype / shot-grammar matrix
For each archetype, provide recommended visual techniques, composition, camera, motion, image/video prompt design, duration guidance, preferred lane and likely failure modes.

### D. Prompt-pair templates
Provide reusable templates for:
- image / first-frame generation;
- image-to-video motion prompt;
- text-to-video prompt;
- STILL composition / Python layer plan;
- HELPER map / diagram / graphic.

The templates must share one structured visual intent; do not let image and video prompts drift independently.

### E. Worked examples
Deliver detailed shot plans and prompt pairs for:
- a ten-second overhead battle action;
- a two-character conversation;
- a Stone Age crafting / work sequence;
- a discovery / reveal;
- an explanatory map or diagram.

For each, show shot duration separately from shot count.
For every worked example, also show: (a) exact first-frame state and geometry, (b) what the audience should notice first, (c) the relevant narration/dialogue/audio beat, (d) the timing of the action/reveal, (e) the end state, (f) the motivated cut/transition, and (g) what must remain continuous into the next shot. For the discovery/reveal example, identify the reveal beat and the visual mechanism that directs attention to it. For the explanatory map, distinguish geographic truth/labels from decorative cinematic treatment.

### F. Proposed visual-intent contract
Show a minimal JSON example and a field dictionary. Mark every field as existing, proposed, derived or adapter-specific. Do not write code or edit the repository.

### G. Pipeline integration proposal
Explain precisely how visual decisions enter at story/script time and flow to the shot plan, image, video, edit and QA stages. Include dependency order and backward compatibility.

### H. Acceptance criteria and test plan
Specify:
- unit tests for prompt compilation and model constraints;
- golden fixtures for each visual archetype;
- image/video prompt consistency checks;
- composition and continuity QA;
- duration / frame quantization checks per model;
- lane-share accounting independent from speech-share accounting;
- provenance tests proving an accepted I2V video points to the exact accepted first-frame hash and records the model/adapter/prompt lineage;
- route/adapter tests proving any layout artifact carried by the shot spec is actually consumed, not merely serialized;
- separate local-versus-hosted capability contract tests, including frame-count/duration validation;
- regression tests ensuring D-95 and D-93 are unchanged.

Do not claim tests have been run. No paid generation is authorized. Identify which visual-quality questions eventually need a small creator-approved sample render.

### I. Implementation plan and decisions
Use:
CURRENT → PROBLEM → EVIDENCE → KEEP → CHANGE → REMOVE → REPLACE → TRADE-OFFS → RECOMMENDATION.

Prioritize changes. State what should stay untouched. Identify which items are technically decidable and which require creator approval. Do not modify code or commit.

### K. Asset provenance and provider capability evidence
- Show how the accepted image and each derived video asset can be traced to a shot, visual intent, input frame hash, prompt/compiler version, model/provider revision, seed/parameters and output hash.
- Provide the adapter-specific capability matrix described in §9, separating local and hosted behavior.
- Mark existing fields/contracts versus proposed additions. Prefer reuse of route/job-manifest/cache structures; do not create duplicate registries without evidence.

### J. Source register
List every source used with direct URL, title, publisher, date/version, access date, source quality and the claim it supports.

## 14. Final questions the report must resolve

1. What visual grammar should the system have for each major scene archetype?
2. Which decisions must be known while writing the script, and which should be deferred to shot planning or the generation adapter?
3. How should the system ensure that the image's starting frame is composed for the video action that will follow?
4. How should one visual-intent object produce aligned image and LTX prompts?
5. Which camera, shot-size, framing, blocking and color fields provide useful control without making the system rigid?
6. When should the system choose VIDEO, STILL or HELPER?
7. How should a scene choose between one continuous 10–15-second non-dialogue action shot and multiple motivated shots?
8. How do we create cinematic dialogue coverage without turning every narrator-led scene into lip-sync?
9. What distinct visual techniques make battles, dialogue, manual work, travel, exploration, reveals and explanatory sequences read differently?
10. What exact repository change is justified first, and what should remain only a proposal until measured?

**Do not finish with generic advice such as “use cinematic camera angles” or “make prompts consistent.” Give exact scene-specific visual decisions and reusable prompt structures, supported by repository evidence and relevant current sources.**
