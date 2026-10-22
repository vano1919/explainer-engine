# Tooling research (stage A of the 2026-10-22 master brief)

Research date: **2026-10-22** (every price and licence below was read on that day unless a row says otherwise; re-read
before any number enters `config/spend_caps.json`, a skill or a paint plan). This is the synthesis the master brief asked
for; the full notes with every source URL and evidence tag are the four appendices:

- [research/TOOLING_IMAGE_2026-10-22](research/TOOLING_IMAGE_2026-10-22.md): image generation and editing, open anime bases,
  consistency tooling, LoRA training, marketplaces, embeddings (tags V = verified on the vendor page, T = third party, I = arithmetic)
- [research/TOOLING_VIDEO_VOICE_2026-10-22](research/TOOLING_VIDEO_VOICE_2026-10-22.md): image-to-video, 2.5D motion,
  narration voices, multimodal reviewers (tags V / S / NV / I)
- [research/TOOLING_INFRA_2026-10-22](research/TOOLING_INFRA_2026-10-22.md): GPU providers, serverless vs pod, storage, watchdogs,
  phone kill-switch (tags V / 3P / INF)
- [research/REPO_AUDIT_2026-10-22](research/REPO_AUDIT_2026-10-22.md): what the code really does today vs what the documents say

Nothing was generated, rented or paid for during this research. The decision this research feeds is
[D-70](DECISIONS_AND_OPEN_QUESTIONS.md) (an approval gate: the creator chooses). The plan that uses it is
[ARCHITECTURE_PLAN_2026-10-22](ARCHITECTURE_PLAN_2026-10-22.md). [TOOL_STRATEGY](TOOL_STRATEGY.md) stays the home of the
*current* routing until D-70 is decided; this document is the home of the *candidates*.

## 1. What changed under us (verified on vendor pages, 2026-10-22)

| Fact | Consequence for the repo |
|---|---|
| RunPod REST **v1 is retired on 2026-11-15**; v2 is "beta" and adds `status`, `cost`, `runtime.gpus[].util`, SSE logs, `/v2/billing/pods` | `explainer_engine/cloud/runpod.py` targets `rest.runpod.io/v1`: it stops working in three weeks unless ported (stage B, first item) |
| Veo 3.1 preview endpoints on the Gemini API shut down 2026-10-22; Sora 2 API shut down 2026-09-24; Hume Octave TTS ends 2026-11-13; PlayHT closed 2025-12-31; OpenAI `tts-1`/`gpt-4o-mini-tts` end 2027-01-06 | none of these may be adopted; `docs/TOOL_STRATEGY.md`'s Veo row is history |
| FLUX 3 Image Klein (BFL, 2026-10-15): open weights 5.6B, 10 references, bounding-box edits, API $0.009 per 1K image, FLUX Kommunity License (commercial outputs under US$5M revenue; LoRA derivatives clause ambiguous) | the cheapest multi-reference editor; one week old, anime quality unmeasured |
| Nano Banana 2.1 (Google, GA 2026-10-06): $0.0336 per 1K image standard / $0.0168 batch, 14 references, no seed, SynthID on every image | the creator's "too expensive" verdict was on Nano Banana Pro ($0.134); 2.1 is four times cheaper but keeps the watermark and the no-seed posture |
| Wan 2.6 (Alibaba API) image-to-video `i2v-flash` $0.025 per second silent / $0.05 with audio; Kling 3.0 $0.084 per second (first+last frame, "elements" references); Gemini Omni Flash ~$0.10 per second | generated motion for a handful of hero shots costs $2.5-10 per episode; a fully generated 10-minute video $30-120+ |
| Cloudflare Workers cron on the free plan (5 crons, 100k requests/day) and R2 (10 GB free, zero egress, user checksums); GitHub Actions cron is 10-30 min late and sometimes dropped | a watchdog that outlives the Claude session costs $0; GitHub cron is only a backup |

## 2. Image generation and editing (the "one world, continuous scenes" problem)

The brief splits into two problems that no single model verifiably solves today: the **anime-like look** (open SDXL anime
checkpoints are the proven anchor) and **shot-to-shot continuity through multi-reference editing** (hosted editors are far
ahead). No independent benchmark of *anime character identity across edits* exists for any model; the pilot is the evidence.

| Candidate | Multi-ref | Edit | Seed | Licence for a monetised channel | Price per 1K image | Verdict |
|---|---|---|---|---|---|---|
| **FLUX 3 Image Klein** (BFL API or self-hosted FP8) | 10 | instruction + bounding boxes | Diffusers yes, API undocumented | Kommunity: outputs OK under US$5M; LoRA derivatives ambiguous | **$0.009** | pilot #1 |
| **Seedream 4.5** (via fal) | 10 | edit endpoint | 3.x had one; 4.5 not verified | "commercial via fal partner agreement"; BytePlus terms unread | $0.04 | pilot #2 (anime reputation, vendor claims only) |
| **Qwen-Image-Edit-2511** (fal or self-hosted, Apache-2.0) | 1-3 | strong in-context editing | yes (local) | Apache-2.0 | $0.03 per MP | pilot #3 as the *continuity editor* of a locked master frame |
| Nano Banana 2.1 (Google) | 14 | prompt only, no mask | **no** | Gemini terms; SynthID + C2PA | $0.0336 / $0.0168 batch | optional Google control; already judged by the creator |
| GPT Image 2.5 (OpenAI) | 16 | prompt masks | no | OpenAI terms | opaque, ~$0.03-0.13+ | too dear for 60+ shots; hero sheet or thumbnail at most |
| Illustrious XL v2.0 / Animagine XL 4.0 + ControlNet Union (self-hosted SDXL) | none native (IP-Adapter, LoRA) | inpaint | yes | OpenRAIL-M / OpenRAIL++-M (commercial stated for Animagine) | ~$0.001-0.003 on a RunPod 4090 community pod | the **style anchor** and LoRA-dataset source, not the editor |
| Excluded | | | | NoobAI-XL and merges (commercial use of outputs prohibited); FLUX.2 [dev], FLUX.2 klein 9B, Kontext [dev] (non-commercial); Qwen-Image-2.1 (research licence); UNO (CC BY-NC); InstantID / PuLID / IP-Adapter FaceID (InsightFace non-commercial, photo faces); Midjourney and NovelAI (no API) | | |

Techniques the pilot tests (all vendor-blog hypotheses, none measured independently; D-59 says they stay REVIEW until our
own numbers exist): canonical character sheet first, then multi-reference; **master frame per location + regional edits**
for every other shot of the scene; re-anchor every 10-20 frames from an updated clean frame; seed lock where the API has
one; a LoRA only for series-wide identity, trained on an Apache base; characters on flat backgrounds composited later.
Embeddings for reference search and duplicates: SigLIP 2 (Apache) for identity/style distance, DINOv2 for near-duplicates,
Gemini Embedding 2 ($0.00012 per image) as the zero-ops fallback.

**Pilot (needs the creator's provider choice, D-50, and a ledger cap first):** the same six shots on every candidate (hero
turnaround sheet; two heroes in a named room; the reverse angle as an *edit*; a close-up expression change as an *edit*; an
era jump in the same style; legible in-style sign text), four generations per shot, 24 images per candidate. Scored free:
SigLIP-2 cosine hero-to-sheet, DINOv2 room similarity shot 2 to shot 3, human 1-5 on the shonen look, legibility, refusals,
wall-clock, exact cost. Estimate: Klein $0.22, Seedream $0.96, Qwen-Edit about $1.08, optional Nano Banana 2.1 about $0.97,
Illustrious sheet + 40 LoRA images on a 4090 community pod about $0.51; **about $3-4 in total, at most $12 with a three-fold
rerun margin; proposed ceiling $15**.

## 3. Motion: generated video versus the controlled still

Keep the controlled pan/zoom over approved art (`production/assemble.py`) as the default for every shot: it is the only
option that satisfies invariants 5 and 6 by construction and costs nothing. Next motion tier: **2.5D parallax** from a depth
map (Depth-Anything-3 BASE, Apache; DepthFlow itself is AGPL, so write the displacement in numpy) with hand-layered PNGs for
the hero. Generated video earns its cost only on 5-10 hero shots per episode where atmosphere carries the beat (weather,
crowds, fire, water), with **both first and last frame being approved stills**, in this trial order: Wan 2.6 i2v-flash →
Kling 3.0 Standard → Gemini Omni Flash → Luma Ray3.2 (Runway Gen-4.x has no last frame; Seedance via fal is $0.30 per second).
Never generate: text, maps, diagrams, numbers; the hero's face as the point of the shot (D-55); beats under 3 s; line-heavy
flat frames; anything that must survive fact QA. Open weights worth a pod only if the pilot proves generated motion is worth
it at volume: Wan 2.2 TI2V-5B (Apache, 24 GB, under 9 min per 5 s clip), HunyuanVideo 1.5 (14 GB; licence excludes EU/UK/KR),
FramePack (Apache, 6 GB). Licence traps: LTX-2.x (revenue clause and remote-restriction clause), MiniMax-H3 and SkyReels-V3
("other"). No independent frame-level test of line-art stability exists; the pilot must measure it (edge-map IoU frame 0 to
frame N, flicker as frame-to-frame edge delta).

## 4. Narration voice and sound

Stay on ElevenLabs (v4 or Multilingual v2 for long-form stability, $0.08 per 1k characters; Flash/Turbo $0.04 for test reads;
about $0.70 per 10-minute script; paid plans grant commercial use, ToS 2026-10-09). Two savings found: the TTS
`/with-timestamps` endpoint returns character-level alignment at generation time, so Scribe v2 ($0.22 per hour) is only
needed on the final mix; and SFX is $0.12 per minute. Worth one parallel test for proper-noun pronunciation: Azure Neural HD
(full SSML phonemes, `WordBoundary` events, 500k characters per month free). Gemini 3.8 Flash TTS is about five times
cheaper but has no word timestamps. Open-weight TTS only on CPU for test reads (Kokoro, Apache); F5-TTS (CC BY-NC) and
Higgs ("other") are out for a monetised channel.

## 5. Automated reviewers (multimodal QA)

Gemini 2.5/3.x Flash accept whole videos with audio (about 100 tokens per second at low resolution, 32 for audio; $0.02-0.16
for a 10-minute episode) for semantic passes (unplanned object, wrong hero, illegible text, continuity). Claude (Haiku 5.5
$0.02, Sonnet 5.5 $0.38 per 120 frames) and GPT accept frames only; `qa/sheet_review.py` already runs Claude in-session for
free. Qwen3-VL-Plus accepts video but ignores the audio track. 1 fps sampling misses single-frame flicker: the deterministic
gates (`edit/motion_lint.py`, loudness targets) stay the gate; the VLM answers semantic questions.

## 6. GPU, storage and the watchdog

| Workload | Cheapest reliable route (verified prices) | Why not a pod |
|---|---|---|
| 1-50 images, FLUX/Qwen class, LoRA sometimes | hosted per-output APIs: fal (FLUX.2 $0.012 per MP, Seedream 4.5 $0.04, Qwen-Edit $0.03 per MP, FLUX LoRA $2 per run), Replicate as fallback | 40 images cost $1 hosted vs $0.2-0.3 in raw GPU seconds, but a forgotten L40S pod bills $26 a day |
| custom ComfyUI graphs, Wan LoRA | Modal (per second, Volumes 1 TiB free, workspace budget that **stops workloads**, server-side cron, $30 monthly credit) or RunPod serverless + worker-comfyui | serverless is cheaper below about 60 % utilisation; our pods were busy far less |
| 5-10 s image-to-video | hosted (Wan 2.2 via fal $0.20-0.40 per clip, LTX $0.20) | 30-80 GB weights and 5-17 min per clip on a self-hosted H100 |
| 10-minute ffmpeg/PIL render | the Claude session (RULE-R1 chunks); Modal CPU function about $0.25 or GitHub Actions as the session-independent fallback | — |
| interactive debugging | RunPod pod, `-until-<epoch>` name, in-pod self-stop, terminated at the end (a stopped pod bills its volume at $0.20 per GB-month and may restart with zero GPUs) | RunPod's incident page lists about 29 regional network/storage incidents in Aug-Oct 2026; a network volume pins one DC |

Durable storage: **Cloudflare R2** ($0.015 per GB-month, zero egress, 10 GB free, user-specified SHA-256 checksums, event
notifications; object versioning not verified) for every job's outputs, state and heartbeat; Backblaze B2 if versioning is
required; the HF dataset `vano1919/tmr-artifacts` stays for finished deliverables (git repos are "not meant as a database with
a lot of writes"; rate limits); a RunPod network volume is a model cache, never an archive.

Watchdog that outlives the session: a **Cloudflare Worker cron every 5 min** (free plan is enough for one RunPod GET and one
ntfy POST) reading `state.json`/`heartbeat.json` from R2 and the pod list, with rules: orphan pod → stop; heartbeat older than
10 min → alert, 20 min → stop; GPU utilisation under 5 % for 20 min → alert; uptime past the plan cap → stop; STARTING over
15 min → terminate; any pod without `-until-<epoch>` → stop. GitHub Actions cron every 30 min as the backup path running the
existing `python -m explainer_engine.cloud.runpod check`. Phone: ntfy `http` action button "STOP ALL" → the Worker's kill
endpoint; GitHub Mobile `workflow_dispatch` "kill-all" as the second path; Pushover emergency priority repeats until acknowledged.

## 7. Chosen, rejected, revisit (proposed; D-70 decides)

| Area | Proposed choice | Rejected (why) | Revisit when |
|---|---|---|---|
| Pictures | pilot FLUX 3 Klein, Seedream 4.5, Qwen-Image-Edit-2511; Illustrious/Animagine as the style anchor; provider per batch stays the creator's (D-50) | Nano Banana Pro (price, already judged); GPT Image 2.5 (opaque price, no seed); NoobAI, FLUX.2 dev/klein 9B, Qwen-Image-2.1, UNO, InstantID family (licence); Midjourney, NovelAI (no API) | the pilot's measured scores; a Klein anime sample; BFL's answer on the LoRA clause; Seedream's official terms |
| Motion | stills + 2.5D parallax default; hosted I2V for 5-10 hero shots with first+last frame | fully generated video (cost, invariants 5/6); Runway for I2V (no last frame); Sora, Veo preview (gone) | the pilot's edge-stability numbers |
| Voice | ElevenLabs v4 / Multilingual v2 + `/with-timestamps`; Scribe only on the mix | Hume, PlayHT, OpenAI TTS (ending); F5-TTS, Higgs (licence) | ElevenLabs price or ToS change; an Azure pronunciation test |
| Reviewers | Gemini Flash on the whole video for semantics; Claude in-session on frames | Qwen3-VL-Plus as primary (no audio) | Claude gains video input |
| GPU | hosted APIs first; Modal or RunPod serverless for custom graphs; pods only interactive and time-boxed | persistent pods as the default (idle risk, incidents) | a job that needs more than an hour of continuous GPU |
| Storage | R2 for jobs; HF for finished deliverables | Wasabi (1 TB minimum); RunPod volume as archive | R2 versioning verified or B2 needed |
| Watchdog | Cloudflare Worker cron + ntfy; GitHub Actions backup; RunPod REST v2 | GitHub cron as primary (late, dropped) | RunPod v2 leaves beta; Worker free limits hit |

## 8. Uncertainties the pilot or the creator must close

1. Anime quality of FLUX 3 Klein, FLUX 3 and Qwen-Edit-2511: no sample or benchmark exists.
2. FLUX Kommunity License: derivatives (LoRA) non-commercial versus commercial outputs "including from Derivatives"; ask BFL
   or train LoRAs on an Apache base.
3. Seedream 4.5 official terms, watermark default, seed and reference limits (BytePlus pages did not render).
4. Seed support on the FLUX 3 API; Kling, Vidu, PixVerse, Pika, BytePlus official prices (JavaScript pages); Azure dollar prices.
5. R2 object versioning; HF Storage Buckets pricing; fal and Replicate spend caps; Modal budget alerts.
6. Prices move monthly (Hyperbolic tripled in three months; Modal repriced Volumes in June 2026); every number carries its
   read date.
7. Every "what creators do" technique is anecdotal; nothing here becomes a sourced rule (D-59) before our own measurements.
