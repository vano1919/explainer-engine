# Stone Age episode — shot plan v0 (Day 1, narration 0–28 s)

Status: **PLAN for creator review.** Nothing generated yet. Rule D-36: scene pictures are made on the local pod
(Z-Image-Turbo text prompts); Gemini is not used for them. Shot rhythm alternates WIDE → MEDIUM → CLOSE-UP.

## How each shot type is made (decides who does what)
| Type | Frame content | Source | Why |
|---|---|---|---|
| WIDE | World, massive scale; people tiny (≤ 5 % of height) or absent | pod picture, one prompt | scale is the point; no recognisable faces needed |
| MEDIUM | Max 2 people, ~50 % of frame height, mid-distance | pod **plate** (empty ground, no people) + our reusable caricature sprite(s) + code animation | keeps the scientists' faces identical across the episode and avoids prompting real people's names into an image model |
| CLOSE-UP | Hands, object, light, ember; no environment | pod picture, one prompt (macro, no faces) | action focus; the model draws hands/objects well, faces are not needed |
| Face reaction (rare) | Head and shoulders | reusable sprite bust (a new Gemini asset only if it will be reused in later episodes) | identity |

Cut every 3–6 s, never longer than 8 s on one picture. Each picture gets code motion (slow push, parallax from a depth map,
smoke/glow overlays, sprite pop/squash) and the sound library events; fade 0.2 s or hard cut on a sound.

## Style suffix (same on every prompt, kept in one file so the look cannot drift)
`painterly storybook illustration, warm hand-painted colours, visible ink linework, soft watercolour texture, 16:9`
Style targets for the pod: `assets/style_samples/stone_age_look_v0/*.jpg` (made earlier with Gemini; not episode assets).
No text, no modern objects, no buildings in any prompt.

## Shots
| # | Type | Time | Narration beat | Pod prompt (before suffix) | Overlay / motion |
|---|---|---|---|---|---|
| 1 | WIDE | 0–4.2 | "Day one. A hundred of the greatest minds… no matches." | Wide epic shot, massive limestone cliff with a cave mouth above a vast river valley at dawn, far mountains, mist, extreme distance, a few tiny figures far away | slow push-in, parallax |
| 2 | MEDIUM | 4.2–8.6 | "Nansen has the skill: a bow drill" | Empty rocky clearing below a cliff, flat ground in the foreground, morning light, mid-distance, no people | sprite Nansen kneeling (bow drill), smoke particles, scribble foley |
| 3 | CLOSE | 8.6–11.0 | "…and sore hands." | Extreme close-up, tight macro of rough weathered hands pushing a wooden bow across a spinning spindle in a notched board, thin smoke, shallow depth of field | handheld shake, smoke |
| 4 | MEDIUM | 11.0–15.0 | "Franklin keeps the tinder dry" | Mouth of a large cave, dry earth floor, soft light from the entrance, mid-distance, no people | sprite Franklin crouching with tinder bundle |
| 5 | CLOSE | 15.0–18.6 | "Einstein has a reading lens, and the Sun." | Extreme close-up, a round glass lens held in fingers focusing a bright point of sunlight onto a nest of dry grass, light rays, blurred meadow behind | flare pulse |
| 6 | WIDE | 18.6–21.0 | "It takes six tries…" | Wide shot, a small group of tiny figures crouched together at the foot of a huge cliff, thin line of smoke rising, vast empty valley, extreme distance | slow pull-back |
| 7 | CLOSE | 21.0–24.3 | "one lucky spark" | Extreme close-up macro, a single orange spark landing in a bundle of dry grass and bark fibres, glowing ember, dark background | spark travel, glow |
| 8 | MEDIUM | 24.3–25.3 | "…and one very careful breath." | Same cave-mouth plate as shot 4, slightly later light | sprite Franklin blowing, ember glow grows |
| 9 | CLOSE | 25.3–26.3 | "Fire." | Extreme close-up, the first small yellow flame climbing through dry grass tinder, sparks, warm glow | pop, glow ping |
| 10 | WIDE | 26.3–28.0 | (beat of silence, crackle) | Wide night shot, huge cliff and cave mouth glowing orange from one small campfire, starry sky, tiny figures with arms raised, extreme distance | embers, slow pull-back |

Picture count for this scene: 6 pod pictures with people-free or tiny-people content + 2 plates + 2 closer macros = 10 pictures,
plus 2 reused plates (shots 4 and 8 share one). Rough scale for a 10-minute episode: 150–200 pictures; at ~14 s each (TMR
measurement, 1536×864, Z-Image-Turbo with CPU offload) ≈ 35–50 min of GPU time. **[estimate]**

## Pod plan (needs your explicit approval before anything starts)
- Card: the secure RTX 4090 that TMR accepted at **$0.89/h** (`cloud/rp.py` price ceiling $0.95/h; anything dearer is deleted at once).
- Preflight (≤ 20 min, ≤ $0.30): GPU visible, disk, Z-Image-Turbo loads, **3 test pictures** (shot 1, 3, 7), `picture_check`.
- Then the 10 pictures for this scene (≈ 5 min), download, delete the pod.
- **Time cap 45 min total, price cap $0.95/h → at most ≈ $0.72.** RunPod hard cap $3 (D-31); last balance read $7.37.
- Rules: `rp.py guard`, ntfy pushes, `rp.py sweep` at start and end, nothing running at the end, report the balance.

## Open questions for you
1. Faces: OK that MEDIUM shots use our fixed caricature sprites over pod plates (no model draws real scientists' faces)?
2. Approve the pod plan above (price ≤ $0.95/h, ≤ 45 min, ≈ $0.72 max)?
