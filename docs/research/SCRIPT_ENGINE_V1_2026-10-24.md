# Script engine v1: the numbers behind the episode rules (research, 2026-10-24)

**What this is.** ვანო asked (2026-10-24) for one full 15-minute episode prompt written with "zero improvisation": where
a rule for a prompt or script dimension did not exist yet, it is researched first, then written as a rule. This file
keeps the evidence behind the new episode rules KP-35..KP-40 ([SHOT_PROMPTS.md](../SHOT_PROMPTS.md)), their numbers
BP-106..BP-110 ([SOURCED_RULES.md](../SOURCED_RULES.md)) and the engine rules ZI-01..ZI-06
([SCRIPT_ENGINE.md](../SCRIPT_ENGINE.md)). The two plans it reconciles are the critic's plan review (2026-10-23, the
creator's project files `plan_review_2026-10-23/`) and `lora_plan_2026-10-22/COST_OPTIMIZATION_2026-10-23_ka.md`.

## 1. Shot rhythm: measured on the creator's own reference cartoons

3517 shots of the creator's footage (Inside Job, Rick and Morty, Solar Opposites; shots of 2 s or more), measured
2026-10-24 (project files `lora_plan_2026-10-24/ANIMATION_DENSITY_COST_2026-10-24_ka.md`):

| Show | shots/min | median shot | near-static (still talking) | static camera, moving figures | moving camera |
|---|---|---|---|---|---|
| Inside Job | 17 | 3.1 s | 33 % | 53 % | 9 % |
| Rick and Morty | 11 | 4.0 s | 36 % | 42 % | 19 % |
| Solar Opposites | 15 | 2.9 s | 29 % | 43 % | 17 % |

Hand-labelled 120 shots: 78 % show two people or fewer (BP-101), 77 % of frames hold (drawn on twos or threes).
"Near-static" is not a still picture: the characters talk, blink and breathe. A pure still with a camera move is a rare
establishing shot, about 5-10 % of screen time.

What it means: 11-17 shots a minute with a median of 2.5-4.5 s (BP-107); at most 10 % of the shots a held picture with
a camera move (BP-109); a moving camera on at most 20 % of the shots (BP-110). The average shot length of English-language
films has fallen to about 4 s and keeps falling (Cutting, DeLong and Nothelfer 2010), so the band agrees with the wider
norm.

## 2. Correction to the critic's plan

The critic's plan review proposed 40 % still + camera, 35 % light animation and 25 % full animation, a key pose every
2.5-4 s, and a 1440p upscale (about $19-25 a 15-minute episode). The key-pose interval and the upscale stand (LT-18:
test films at the base size, release at 1440p). The 40 % still share does not: the creator's cartoons hold a still on
5-10 % of the time, and our night tests showed a held still reads as a slideshow beside acting shots. The tiers keep
their names with measured shares: hold at most 10 %, light about the cartoons' near-static third, full the rest; every
line of dialogue and every peak is full (KP-37).

## 3. Clip length and key poses: our own night tests and the model's limits

- Night tests 2026-10-24 (project files `lora_plan_2026-10-22/ic_test/NIGHT_VIDEO_TESTS_2026-10-24_ka.md`): plain LTX
  from one picture is clean at 10 s; at 15 s a person was duplicated and the set changed; at 20 s the heroes turned
  translucent. IC-LoRA conditioning needs strength 1.0 (0.6 and 0.4 turned grey).
- LTX-2.5 on fal: the Pro tier renders 6, 8 or 10 s; the Fast tier up to 20 s; 24, 25 or 50 fps; a start image and an
  optional end image (fal.ai, "How to use LTX-2.5"). LTX's own guide: frames are 8k+1 and sizes multiples of 32.
- So a clip is at most 10 s (BP-108), and a shot longer than 5 s that changes pose gets a drawn last frame, which gives
  a key pose every 2.5-4 s inside the clip, as the critic proposed.

## 4. The outro: a channel pointer, not a subscribe call

BP-43 bans the dry sign-off ("don't forget to subscribe"). The creator's call (2026-10-24): the last lines point to the
channel by its worlds: which worlds are already there, which are coming, and "subscribe if you don't want to miss them".
The channel runs from the Stone Age to the future. That is BP-106, a house rule, checked by KP-40.

## 5. What was not verified

- The tier shares are measured on three shows the creator chose; no study ties them to retention.
- The cost of a 15-minute episode at this density is an estimate from the eras clips (≈$10-12 per 10 minutes at full
  quality; LT-18 test films first).
- Sizes in the prompts stay words (a third, half) until test T1 (words against numbers) reports (ZI-05).
