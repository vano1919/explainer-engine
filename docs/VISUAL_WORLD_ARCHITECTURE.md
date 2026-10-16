# Visual world architecture: era-true worlds, one look, hybrid generation

Status: **proposal, awaiting the creator's decision (D-41).** Nothing here is built or paid for yet. Written 2026-10-16 after
the creator rejected the six style-bridge pictures ("they look like children on a school excursion") and asked for a
system that, for every topic, works out which period and world belong in the picture and shows it the way cinema and mass
culture show that period, while keeping every rule already agreed (UR-01..UR-22, PRODUCTION_RULES).

## 1. Why the style-bridge pictures failed (evidence, not guesses)

The six prompts are in TMR `cloud/jobs/stone_age_style_bridge.json`; the pictures in the pod store
`pictures/stone_age_style_bridge`. Causes found in the prompts themselves:

| Symptom the creator saw | Cause in our text | Fix in this architecture |
|---|---|---|
| Adults read as children | `figure_style` asks for "head about 1.6x oversized", "storybook caricature", "quirky, gently exaggerated", "rounded wobbly": big round heads and soft shapes are the visual code for children | Look v2 (section 5): adult proportions, the caricature lives in faces, hands and posture, never in head size |
| Excursion, not survival | phase mood "bright even daylight, clean light colours" was appended to every prompt, even to the storm and firelight ones: two light keys in one prompt, the brighter one wins | one light key per prompt, taken from the beat (section 6), and a lint that refuses a second one |
| Modern clothes, striped T-shirts | "a hundred tiny figures" with no costume: the model fills the gap with its default (modern kids) | the world resolver gives every extra a costume and a material list (section 3) |
| Plates and close-ups look like two painters | style held only by words; Z-Image and Gemini read the same words differently | the style is anchored by pictures (reference frames and a trained style LoRA), not by adjectives (section 6) |
| Postcard sky and green grass | nothing told the picture what the era looks like on screen | the era codex (section 4) carries the screen language of the period |

A useful outside check: the art director of *Primal* (Tartakovsky's prehistoric series) says the team avoided sky blues and
green grass so that every colour carried meaning ([Keyframe via scienceandfilm.org](https://scienceandfilm.org/articles/3346/genndy-tartakovskys-primal-art-director-scott-wills),
[Blu-ray review](https://digitalbits.com/item/primal-s1-2021-bd)). Our bridge pictures did exactly the opposite.

## 2. Requirements

1. **Logic of the world, per topic.** Before any prompt is written, the system knows which world(s) the episode shows, when
   and where, what exists there and what does not (anachronisms), who lives there and what they wear, and, in a crossover,
   who is the visitor and whose world sets the light.
2. **The period looks the way the audience knows it from cinema and popular culture** (light, palette, atmosphere, set and
   costume language), without copying any film's frames, characters or designs (RIGHTS_AND_FAIR_USE).
3. **One universe (UR-22) stays the primary rule.** Inside one episode everything is drawn by "one hand". The channel keeps one
   drawing grammar across all topics; the era changes light, palette, materials and costume, not the drawing grammar.
4. **Adults look like adults**; named heroes are recognisable caricatures and keep the same face in every shot.
5. **Every agreed rule still holds**: stakes and named heroes (UR-16..UR-21), ABC grammar and timing (UR-01..UR-15), money rules,
   Gemini only where the spend is justified and recorded, look at the output before reporting.
6. **Works for every topic**: Stone Age, Rome, the Vikings, the Space Race, a public-domain fictional world.

## 3. Layer 1: world resolver (per topic, free)

Input: the topic, the script and the claim map. Output: `world.json` in the episode folder (new schema
`schemas/world.schema.json`).

```
worlds: [
  { id: "host",    role: "host",    era: "prehistory_neolithic_early", place: "SE Anatolia, limestone uplands near the
    Euphrates tributaries", when: "about 10,000 BCE (12,000 years ago)", season_light: "late autumn, cold dusk",
    landscape: [...], material_culture: [...], absent: ["pottery", "metal", "wheel", "woven cloth (to verify)", ...],
    inhabitants: { who: "hunter-gatherer adults and families", costume: [...], hair: [...] } },
  { id: "visitors", role: "visitor", era: "modern_1600_1950", people: ["newton", "einstein", ...],
    costume: "the clothes of their own decade, getting dirtier day by day" }
]
light_owner: "host"          # whose world sets light, grade and atmosphere for every frame
day_arc: [ {beat: 1, light: "storm dusk"}, {beat: 2, light: "night firelight"}, ... ]
sources: { claim ids for every landscape, material and costume line }
```

Rules the resolver applies (they make the picture logical):

- **Crossover ("X dropped into Y"):** Y is the host; it owns landscape, light, grade, extras and props. X are visitors; they keep
  the costume and props of their own time, drawn in the same look and lit by the host's light. The visitors' clothes age with
  the story (dirt, tears), which is also free storytelling.
- **Single-period history:** one world; it is both host and light owner.
- **Two eras meeting** (a Roman in the Space Race): the place where the scene happens is the host for that scene; a scene list
  can switch host per beat, never inside a shot.
- **Fictional public-domain worlds:** the world comes from the text (claims), the screen language from the closest era entry;
  never from a film adaptation's designs.
- **Everything visible is accounted for:** each prop, costume and building in a prompt is either in the era's material list or in
  the claim map; anything in `absent` is a FAIL (the visual judge checks it again on the picture, section 8).
- **Uncertain facts stay out of the picture** or are marked as reconstruction (a claim with a disputed source never becomes a
  prop).

## 4. Layer 2: era codex (channel-wide, grows with each topic)

`explainer_engine/world/eras.json`, one entry per era, reused by every episode in that era. Each entry has:

- `screen_refs`: films, series, animation and games that define how mass culture *sees* the era (studied for codes only;
  never named in prompts, never copied);
- `light_keys`: the 3-5 lighting situations the era is known for on screen (each a short prompt phrase);
- `palette`: ids in `design/palette.json` (hex colours live only there);
- `atmosphere`: dust, smoke, mist, rain, heat haze;
- `production_design`: materials, architecture, tools;
- `costume`: silhouettes and materials for ordinary people, by class;
- `grade`: the finishing grade id (section 7);
- `cliches_to_avoid`: the screen clichés that would make it silly or wrong (cavemen with clubs, dinosaurs, horned Viking
  helmets);
- `sources` and an evidence label (`product_hypothesis` until a stills study confirms it).

Seed entries (working hypotheses from widely known works; to be confirmed by a stills study per era before first use):

| Era id | Screen references (study only) | Light and palette on screen | Atmosphere and design | Clichés to avoid |
|---|---|---|---|---|
| prehistory | *Quest for Fire* (1981), *Alpha* (2018), *Primal* (2019), *The Clan of the Cave Bear* (1986) | firelight amber on skin against cold blue dusk; ochre, umber, charcoal; no postcard sky | smoke, mist, wind, hides, flint, bone; open steppe and rock | clubs, dinosaurs, grunting brutes, Flintstones gags |
| ancient_egypt | *The Prince of Egypt* (1998), *Assassin's Creed Origins* | hard white sun, deep shadow; sand, gold, lapis | heat haze, dust, painted stone | everyone in gold, pyramids in every frame |
| classical_greece_rome | *Gladiator* (2000), *Rome* (HBO, 2005), *300* (stylised) | warm gold and dust by day, torchlight by night; marble, crimson, bronze | dust, smoke of sacrifice, crowds | pure white marble (statues were painted), togas on everyone |
| norse_viking | *Vikings* (2013), *The Northman* (2022) | grey-blue overcast, fire inside long halls; slate, wool brown, iron | mist, sea spray, snow | horned helmets |
| medieval_europe | *The Last Duel* (2021), *Kingdom of Heaven* (2005), *Wolfwalkers* (2020, 2D) | overcast muted daylight, candle and hearth at night; mud, wool, stone | rain, mud, smoke | spotless armour, everyone filthy all the time |
| feudal_japan | *Seven Samurai* (1954), *Blue Eye Samurai* (2023, animated), *Ghost of Tsushima* | rain and mist, strong silhouettes; ink black, paper white, one accent red | wind in grass, wood and paper | ninjas everywhere |
| age_of_sail | *Master and Commander* (2003) | grey sea light, lantern below deck; tar, canvas, salt | spray, fog, rope and timber | pirates as default |
| renaissance_baroque | Caravaggio and Rembrandt paintings (chiaroscuro), period dramas | single window or candle key, deep shadow; umber, gold, velvet | interiors, workshops | everyone a genius in a toga |
| industrial_victorian | *Sherlock Holmes* (2009), *Peaky Blinders* (2013) | gaslight, soot, sickly green-brown; brick, iron, steam | smoke, fog, rain on cobbles | steampunk gears on everything |
| wild_west | *The Good, the Bad and the Ugly* (1966), *True Grit* (2010) | golden hour, harsh noon; dust, leather, sky | heat, wind, open land | |
| world_wars | *1917* (2019), *Saving Private Ryan* (1998) | desaturated, low contrast or bleach-bypass; khaki, mud, grey | smoke, rain, ruins | glory shots |
| space_race_1960s | *Apollo 13* (1995), *First Man* (2018) | film-grain warm interiors, cold hard light in space; beige, orange, chrome | control rooms, smoke of launches | |

The resolver picks the entry; a topic with no entry gets a new one researched first (web + vidIQ transcripts of the top
videos on that era, stills study), written, and approved with the episode's world.

## 5. Layer 3: channel look v2 (the constant thread, every topic)

The thread of UR-22 stays, but its content changes from "storybook" to a **cinematic painted graphic-novel look**:

- **Adult proportions** (head about 1/6-1/7 of the body for adults); the caricature lives in the face (nose, brows, jaw, hair,
  wrinkles, stubble), the hands and the posture. Named heroes keep their recognisable traits (Einstein's hair, Newton's wig and
  long face, Franklin's spectacles and bald crown).
- **Ink-shadowed shapes**: bold silhouettes, a dark ink shadow pass, simple planes of colour, painted textured backgrounds
  (the "graphic-novel" quality *Primal* is praised for), one artist's line.
- **Cinematic lighting**: one key light per frame, real shadows, atmosphere between planes; the era codex chooses the key.
- **Banned child cues** (lint): storybook, cute, chibi, kawaii, oversized head, big eyes, quirky, wobbly, pastel, primary-colour
  T-shirts, "tiny figures" without costume.
- Inside one episode one look; across episodes the same drawing grammar, so the channel stays recognisable while each era
  looks like itself.

This replaces `look.figure_style` ("head about 1.6x oversized") and the storybook `style_suffix`. It changes the creator's
earlier decision on caricature size, so it is part of D-41. The eight `scientists_v0` sprites (1.6x heads) would be redrawn
from new hero sheets.

## 6. Layer 4: generation engine, anchored by pictures, routed by shot

Words alone do not hold a style across two generators (section 1). Three anchors replace them:

1. **Look bible (Gemini, paid once, reusable):** about 4 master frames per look made with Nano Banana Pro (`gemini-3-pro-image`,
   $0.134 at 1K-2K, up to 3 style references, 5 character references, 14 references in all, official pages
   [pricing](https://ai.google.dev/gemini-api/docs/pricing), [image generation](https://ai.google.dev/gemini-api/docs/image-generation)),
   then about 20 more anchor frames across eras and shot types (wide, medium, close, hands, crowd, interior, firelight, daylight)
   with Nano Banana 2.1 (`gemini-nano-banana-2.1`, $0.050 at 2K, half in the Batch API) using the masters as references. The
   creator approves the masters once: this is the real look test.
2. **Hero sheets (Gemini Pro, paid once per hero, reusable in every topic):** one turnaround and expression sheet per named
   hero in look v2; the reference for every shot of that hero.
3. **Channel style LoRA (pod, paid once):** a Z-Image-Turbo LoRA trained on the ~24 approved anchors (community reports: 10-30
   curated images, rank 32, about 3,000 steps, 40 minutes to 1.5 hours on an RTX 4090; not verified by us:
   [RunComfy guide](https://www.runcomfy.com/trainer/ai-toolkit/z-image-turbo-lora-training),
   [example style LoRA](https://huggingface.co/frankbarbs/darkroom-noir-zimage),
   [time estimates](https://apatero.com/blog/best-settings-character-lora-z-image-turbo-guide-2025)). Then the cheap bulk
   pictures on the pod speak the same visual language as the Gemini frames.

**Routing table** (`shot_rules.route`, one generator per shot, decided before any spend):

| Shot | Generator | Anchors | Why |
|---|---|---|---|
| A: wide establishing, plates | pod, Z-Image + channel LoRA | era light key, palette | many, cheap (about $0.006 each) |
| C: hands, props, inserts | pod + LoRA | costume and material from the world | cheap; hands were the one thing the bridge got right |
| Crowds and extras | pod + LoRA, costume mandatory | world inhabitants | cheap; judged for adults and era (section 8) |
| B: named heroes acting (UR-17) | Gemini Nano Banana 2.1 (Pro when more than 4 heroes share a frame) | hero sheets + 1-2 anchor frames as style references | identity and acting across shots is where open models still trail closed ones ([MultiBanana benchmark](https://arxiv.org/pdf/2511.22989)) |
| Heroes that move (rig, lip, blink) | sprite cut from the hero sheet's pose, composited | grade pass | animation needs parts |
| Thumbnails | Gemini Pro | hero sheets | reusable channel asset |

Open alternative for B shots (free per picture, weaker): Qwen-Image-Edit-2509 (Apache-2.0, person + scene with 1-3 inputs,
[model card](https://huggingface.co/Panod/Qwen-Image-Edit-2509)) on the pod. Z-Image-Edit is announced but not released
([Z-Image README](https://cdn.jsdelivr.net/gh/Tongyi-MAI/Z-Image@main/README.md)). Measured in the validation step, not assumed.

**Prompt v2** (`edit/prompt_v2.py`): fixed slots in this order, short: shot type, subject + action + one emotion, world
(costume, materials from `world.json`), one light key from the beat, atmosphere, the look tokens. Lints: exactly one light key;
every person has a costume; no word from `absent`; no child cue; no artist or film name; the universe thread present (UR-22).

## 7. Layer 5: finishing grade (local, free)

Every picture (pod, Gemini, sprite) passes one grade before the edit: the era grade from the codex (a 3D LUT or curves),
shared grain and paper texture, black level and saturation matched to the anchor set, light wrap on composited sprites. One
grade over everything is the cheapest and strongest consistency lever; colourists use the same method to tie mixed sources
together. `explainer_engine/finish/grade.py` (numpy, tested on fixtures).

## 8. Layer 6: visual QA gate (before the creator sees anything)

1. **Judge** (`qa/visual_judge.py`): a vision model answers fixed questions per picture: do all people read as adults? any
   modern or out-of-world object or clothing (from `absent`)? people in a plate (UR-20)? text or letters? is the named hero
   recognisable (against the sheet)? one light direction? Local Qwen3-VL-2B (already in TMR `cloud/models.json`) on the same pod,
   or Gemini Flash vision (about $0.0004 a picture at $0.30 per million input tokens). Answers are JSON; a FAIL repaints that
   picture with a new seed (at most 2), then goes to the creator as a flagged picture.
2. **Style distance** (`qa/style_distance.py`): each picture's style embedding against the anchor set (CSD, ECCV 2024,
   [paper](https://arxiv.org/pdf/2404.01292)); raw CSD cosine is not calibrated across styles
   ([2026 critique](https://arxiv.org/pdf/2605.09030)), so it only ranks outliers inside one episode for a human look, never
   accepts or rejects alone.
3. **Contact sheet by eye** (standing order 6), then the creator.

## 9. Money (estimates; the estimate before each call is the number that counts)

One-time, reusable across all topics:

| Item | Units | Price | Estimate |
|---|---|---|---|
| Look v2 master frames (Gemini Pro) | 4 + 2 alternates | $0.134 | about $0.80 |
| Anchor frames (Nano Banana 2.1, 2K) | 20 | $0.050 | about $1.00 |
| Hero sheets (Gemini Pro) | 10 heroes | $0.134 | about $1.34 |
| Channel LoRA training (pod 4090) | 40-90 min | $0.89/h | about $0.7-1.4 (cap $2, 2.5 h) |
| A new era later | 6 anchors | $0.050 | about $0.30 |

Per 10-minute episode (about 155 shots, 140 unique pictures):

| Item | Units | Estimate |
|---|---|---|
| B hero shots, Gemini Nano Banana 2.1 2K | about 45 | about $2.3 (about $1.1 in the Batch API, up to 24 h) |
| Pod pictures with LoRA (A, C, crowds) | about 95 at 22.7 s | about $0.65 with boot |
| Visual judge | 140 | under $0.10 |
| Repaints (about 15 %) | about 20 | about $0.4 |
| **Pictures total** | | **about $2.5-3.5** (today pod-only: about $1.0) |

Gemini cap: $3.28 of $10 used. The one-time set ($3.1) brings it to about $6.4; the first episode's B shots pass 80 % of the
cap. Hybrid production needs the creator to raise the Gemini cap or to keep B shots on the open model.

## 10. Engine and tool changes (all free to build; built only after D-41 is decided)

explainer-engine:
- `world/resolver.py`, `world/eras.json`, `schemas/world.schema.json` + tests (crossover host/visitor, absent-object FAIL).
- `edit/prompt_v2.py` (slots, lints) replacing `compose_prompt`'s suffix chain; `look.json` v3 (look v2 tokens, grade id).
- `shot_rules.route` (generator per shot) and the cost estimate per route.
- `imagegen/gemini.py`: ported from TMR `render/imagegen.py` (provenance header): references, Batch API, price table including
  Nano Banana 2.1, budget guard, cache by prompt + references.
- `finish/grade.py`, `qa/visual_judge.py`, `qa/style_distance.py`.
- `production_gate`: new gates "world" (before the script is final), "look bible" and "LoRA" (once per channel / era).
TMR `cloud/`:
- `train_lora` stage (ai-toolkit pinned, added to `models.json`), LoRA loading in `gen_pictures.py`, a judge stage, a
  `lora_train` row in `job_speeds.json` measured on the first run.

## 11. Rule changes (numbers assigned in UNIVERSAL_RULE_BASE when approved)

- UR-22 stays primary. Its thread becomes look v2 (drawing grammar + adult proportions). The era codex may change light,
  palette, grade, materials and costume per world; nothing may change the drawing grammar. Inside an episode the light
  owner's grade covers every frame, visitors included.
- New: **world fidelity** (every visible object, costume and building comes from the world's material list or the claim map;
  `absent` objects FAIL in prompt and picture).
- New: **adults read as adults** (no child cues in prompts; the judge's adult check on every picture with people).
- New: **anchored generation** (no picture from words alone: LoRA or reference frames on every generator).
- New: **one light key per prompt** and **one grade over every picture**.
- New: **visual QA gate** before the contact sheet goes to the creator.
- `figure_style` and UR-07's caricature wording move to look v2. D-36 (pod for scene pictures, Gemini for reusable assets) is
  amended by D-41: Gemini also for B hero-acting shots, by the routing table, within an approved per-episode cap.

## 12. Rollout, each step with its own approval

1. **Look test (Gemini, about $0.80):** 4 Stone Age masters in look v2 (storm dusk wide with the hundred visitors; Franklin and
   Newton arguing by a dying fire; adult hunter-gatherers watching from the rocks; raw hands at the fire), 2 alternates. The
   creator approves or redirects the look. Nothing else starts before this yes.
2. **Anchors + hero sheets (about $2.3).**
3. **LoRA training on the pod (cap $2, 2.5 h)**, then the 6 bridge pictures again with the LoRA (about $0.15) and the judge.
4. **Day 1 production** by the routing table (estimate shown first).
Free work that can go first: world resolver, era codex seed, prompt v2 lints, grade pass, judge questions, tests.

## 13. Not verified, risks

- Reference limits and prices are from Google's pages read 2026-10-16; Nano Banana 2.1's reference limits are not listed there
  (only Pro and 3.1 Flash are): check before the first call. Gemini 2.5 Flash Image was due to shut down on 2026-10-02 per the pricing page, so it is not an option.
- LoRA training times and settings are community reports; our first run measures them.
- The era codex rows are working hypotheses from well-known works; a stills study per era confirms them. No frames, characters
  or designs of those works are copied or named in prompts.
- Hybrid generation still mixes two generators; the LoRA, the shared references and the grade reduce the gap, the judge and the
  creator decide whether it is closed.
- Real-person likenesses in Gemini: policy refusals for some living-era figures are possible; the sheets test this first.
