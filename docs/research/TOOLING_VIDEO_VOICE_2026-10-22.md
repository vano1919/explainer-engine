# Video motion, narration voice and multimodal QA models — research as of 2026-10-22

Scope: a solo creator's ~10-minute, 2D anime-like illustrated explainer (one English narrator, no character
voices), produced in the cloud (APIs + rented GPU), managed from a phone, budget-conscious. Today's pipeline
animates approved stills with PIL/ffmpeg (pans, zooms, cuts), ElevenLabs narration + sound effects, ElevenLabs
Scribe for word timings. **Research only — no paid calls were made and nothing was generated.**

## How to read the evidence tags

| Tag | Meaning |
|---|---|
| **[V]** | Read on the vendor's own page on 2026-10-22 (URL in the source list) |
| **[S]** | Secondary source (blog, aggregator, reseller page) that cites the vendor; the vendor page itself could not be read |
| **[NV]** | Not verified: could not find a source, or sources conflict |
| **[I]** | My inference from the facts above; not a sourced fact |

A few things I expected to find were different from what the official pages say today; they are flagged in
bold where they matter. Prices are USD list prices; resellers (fal, Replicate, Runware, OpenRouter…) differ.

---

## Part 1 — image-to-video and motion for illustrated stills

### 1a. Hosted video APIs

Legend: I2V = image-to-video (first frame). FLF = first+last frame. Ref = reference images (characters). Cam =
camera-motion control. "Moderation" = what the docs say about people/faces/safety filters.

| Vendor / model (current) | I2V | FLF | Ref | Cam | Duration / resolution | List price (per second) | Moderation / terms | API maturity | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **Google Gemini Omni Flash** `gemini-omni-1.1-flash` (Gemini API, stable) | yes (text+image+video inputs) | "keyframe interpolation" listed on the models page; last-frame support was "coming soon" at the June 2026 preview post | "maintaining character, object, and style consistency" claimed; reference-image API shape not read | prompt only (no documented param) | "scene extension to 40s", 360p–4K [S]; 720p default | **~$0.10/s at 720p** (page: 5,792 output tokens per second of 720p; $17.50/1M output tokens) [V]; other tiers [S] | C2PA + SynthID on by default [V]; person-generation controls not read | GA Aug 27 2026 [S]; stable in Gemini API models list [V] | [V] pricing + models page; [V] Cloud blog 2026-06-30; capability details [S] |
| **Google Veo 3.1** `veo-3.1-generate-preview` / `-fast-` / `-lite-` | yes | **yes** (`image` + `lastFrame`) | **yes**, up to 3 `asset` images (not on Lite) | prompt terms (dolly, aerial…) | 4/6/8 s; 720p/1080p/4K (1080p/4K need 8 s); extension to 148 s at 720p | Standard $0.40 (720p/1080p), $0.60 4K; Fast $0.10/$0.12/$0.30; Lite $0.05/$0.08 | `personGeneration` = `allow_adult` only for I2V/FLF/Ref; SynthID; videos stored 2 days; blocked videos not charged | **Preview models "will be shut down on October 22, 2026"** (today) on the Gemini API; Google points to Omni Flash or "GA Veo models on Gemini Enterprise Agent Platform" (Vertex successor) — Vertex price not read | **[V]** docs/veo + pricing page (page dated 2026-10-19) |
| **Kling 3.0 / 3.0 Turbo / O1 (Kling API)** | yes | **yes** (`image` + `image_tail`; fal: `end_image_url`) | **yes** "elements" (image sets or video, @Element1 in prompt) | legacy `camera_control` (pan/tilt/zoom/roll/dolly) documented for older versions; not used on v3 per wrappers [S] | 3–15 s (fal); 720p/1080p/4K | 3.0 no audio: $0.084 (720p), $0.112 (1080p), $0.42 (4K); with audio $0.126/$0.168; 3.0 Turbo w/ audio $0.112/$0.14; 2.5 Turbo no audio $0.042/$0.07 (list, 1 unit = $0.14, checked 2026-10-13 by FrameSurfer) [S]; fal mirrors $0.084/$0.126 [V fal] | safety checker on by default (fal); Kling terms not read | official pricing page is JS-rendered and could not be read [NV]; prepaid units, 30-day trial packs; Kling 4.0 announced, no API price [S] | [S] FrameSurfer citing kling.ai; [V] fal model page |
| **Runway** Gen-4 Turbo `gen4_turbo`, Gen-4.5 `gen4.5`, Aleph 2.0 `aleph2` | yes | **no** for gen4.5/gen4_turbo (first frame only, per Sept-2026 reading of Runway's endpoint docs) [S]; `promptImage position: last` existed in API version 2024-11-06 [V] | `references` array exists but is mutually exclusive with keyframes [S] | not documented | 5 or 10 s, 720p 24fps (Turbo) [S] | **Gen-4 Turbo $0.05/s; Gen-4.5 $0.12/s; Aleph 2.0 $0.28/s (56-credit min); Act-Two $0.05/s** ($0.01/credit) | content moderation page exists, not read | mature REST API, dated model releases (Gen-4.5 2026-02-10, Aleph 2.0 2026-06-02) | **[V]** docs.dev.runwayml.com pricing + models |
| **Luma Ray3.2 (Luma API)** | yes (same price as T2V) | **yes** (`start_frame` + `end_frame`) + Multi-Keyframe up to 16 keyframes | not stated | not stated; "Reframe" product separate | 5 s or 10 s blocks; 540p/720p/1080p; HDR 2×, HDR+EXR 3× | 5 s: $0.15 (540p) / $0.30 (720p) / $1.20 (1080p) = $0.03 / $0.06 / $0.24 per s [I from per-clip prices]; 10 s: $0.45/$0.90/$3.60 | not stated on pricing page | mature; pricing page has internal inconsistencies (FAQ vs table) | **[V]** lumalabs.ai/api/pricing |
| **MiniMax** — current **MiniMax-H3 / H3-Max**; **Hailuo 2.3 / 2.3 Fast are "Legacy"** | yes (image input priced: first 5 free then $0.04/image on H3) | Hailuo 02 had FLF [NV for H3] | H3 tags: "reference-to-audio-video" (open weights) | not stated | H3 768p / 2K; Hailuo 2.3: 6 s or 10 s, 768p / 1080p | **H3 $0.08/s (768p), $0.13/s (2K); H3-Max $0.05/s (480p), $0.08/s (768p)**; Hailuo 2.3 Fast per clip $0.19 (768p 6 s), $0.32 (768p 10 s), $0.33 (1080p 6 s); Hailuo 2.3 $0.28/$0.56/$0.49 | not stated | H3 "not supported yet" for prepaid packages; pay-as-you-go only | **[V]** platform.minimax.io pricing-video |
| **ByteDance Seedance 2.0 / 2.5 (BytePlus ModelArk)** | yes | **yes** (fal: `end_image_url`) | 2.0: reference video input priced separately [S] | "motion prompts" only | 4–15 s or auto; 480p/720p/1080p/4K; aspect auto/21:9/16:9/4:3/1:1/3:4/9:16 | ModelArk is **token-priced**: tokens = (input s + output s) × W × H × fps ÷ 1024; secondary figures ~$0.12–0.15/s 720p, ~$0.37/s 1080p for 2.0 [S]; **fal: $0.3034/s 720p, $0.682/s 1080p** [V fal] | fal page: no safety notes; BytePlus terms not read; "not sold in the US" claim for 2.5 [NV] | official pricing page could not be read (nav only) [NV] | [V] fal; [S] framesurfer/anikuku/cometapi |
| **Alibaba Wan 2.6 (Model Studio API)** `wan2.6-i2v`, `-flash`, `wan2.6-r2v` | yes | not stated on model page [NV] | `wan2.6-r2v-flash` reference-to-video model exists | "intelligent shot scheduling" only | up to 15 s; 720p/1080p; audio in+out | **wan2.6-i2v $0.10/s (720p), $0.15/s (1080p)** (Singapore); US-Virginia global $0.086/$0.143; **i2v-flash $0.05/$0.075 with audio, $0.025/$0.0375 silent**; older **wan2.2-i2v-flash $0.015/s (480p), $0.036/s (720p)**; wan2.2-i2v-plus $0.02/$0.10 | not stated | 50 s free quota per model (Singapore, 90 days); RPM 300 | **[V]** alibabacloud.com model-pricing (dated 2026-10-22) + wan2.6-i2v page (2026-10-11) |
| **OpenAI Sora 2 API** | — | — | — | — | — | — | — | **"The Sora 2 models and Videos API were shut down on September 24, 2026… No one-to-one replacement API is available."** Input images with human faces were rejected. | **[V]** developers.openai.com video-generation + deprecations |
| **Vidu Q3 / Q4 (Vidu Open Platform)** | yes | Q2 had start/end mode [S] | **yes**, Q2 ref up to 7 images [S]; Q3 "reference-to-video mix" | not found | per-model | $0.005/credit [S]; Q3 reported 9/20/24 credits per s at 540p/720p/1080p ($0.045/$0.10/$0.12) [S]; official page is JS-rendered [NV] | failed/moderated jobs not charged (Q4 claim) [S] | credits are separate from web plans | [S] magichour, flowith, omniakey; [NV] platform.vidu.com |
| **PixVerse V5.6 (platform.pixverse.ai)** | yes | "end-frame support" [S] | Fusion (reference-to-video) 45–120 credits per 5 s on V5 [S] | effects/templates | 5 s / 8 s, 360p–1080p | credits; USD per credit **conflicting** ($0.0044–$0.01) [NV]; fal $0.07/s [S] | not found | docs pricing URL returned 404 [NV] | [S] atlascloud, verna, vidcost |
| **Pika 2.5 (Pika API Club)** | yes | not found | not found | not found | 720p/1080p | $10/month membership + usage; I2V ~$0.04/s 720p, $0.06–0.09/s 1080p [S]; official page exposes prices only via catalog JSON [NV] | not found | async jobs, webhooks, OpenAPI 3.1 [S] | [S] apiframe; [V] dev.pika.art/pricing (no numbers) |

**Things that changed vs. common knowledge (verified today):** Veo 3.1 preview endpoints on the Gemini API
end today (Google's replacement is Omni Flash at roughly a quarter of Veo Standard's price); Sora 2's API is
gone; MiniMax moved Hailuo 2.3 to "Legacy" behind MiniMax-H3 (which also has open weights, see 1b); Wan 2.5/2.6
are API-only (no open weights). Runway is the one major API where first+last frame is *not* available on the
current I2V models.

### 1b. Open-weight video models for a rented GPU

| Model | Licence | VRAM (official) | Speed per ~5 s clip (official or quoted) | Control (keyframes/pose/depth/camera) | Anime / line-art evidence | Evidence |
|---|---|---|---|---|---|---|
| **Wan 2.2 TI2V-5B** (Jul 28 2025) | **Apache-2.0** | "at least 24GB VRAM (e.g. RTX 4090)"; ComfyUI claims 8 GB with offload [S] | "5-second 720P video in under 9 minutes" on a consumer GPU (24 fps, 1280×704) | single input image; no FLF in 2.2 README. **Wan2.1-FLF2V-14B-720P** (first-last frame) and **Wan2.1-VACE-1.3B/14B** (reference, pose/depth, inpaint, extension) exist on HF under Apache-2.0 | vendor claims only; one anime-focused blog says Wan (API 2.7) "most reliably keeps anime looking drawn" [S]; **no independent line-art flicker test found** [NV] | **[V]** GitHub README; **[V]** HF org listing |
| **Wan 2.2 I2V-A14B / T2V-A14B** (MoE 27B) | Apache-2.0 | "at least 80GB VRAM" single GPU officially; FP8 community runs on 24 GB [S] | not stated | as above | as above | [V] README |
| **Wan-AI org status** | — | — | — | newest repos: Wan2.2-Animate-2-14B (Aug 2026), Wan-Dancer-14B (Jul 2026). **No Wan 2.5/2.6/2.7/3.0 weights on the official org** | — | **[V]** HF listing 2026-10-22 |
| **LTX-2 (19B) / LTX-2.3 / LTX-2.5 (22B)** (Lightricks; 2.5 Aug 2026) | **LTX-2 Community License** (dated Jan 5 2026, "applicable to all LTX-2 versions released since"): free incl. commercial use **unless the entity has annual revenue ≥ $10,000,000**, which needs a paid Commercial Use Agreement; derivatives must stay under the same licence; Lightricks may remotely restrict use | not on model card; FP8/FP4 checkpoints + CPU offload offered; community: 16–28 GB for FP8 [S] | distilled 8-step variant; secondary: 2–5 min for 10 s 1080p on a 4090 [S]; "18× faster than Wan 2.2" is a vendor claim [S] | **first-last-frame Space for LTX-2.3**; "Ingredients" (reference) IC-LoRA for 2.5; native audio | none specific | **[V]** LICENSE text on HF; [V] HF listing; model cards |
| **HunyuanVideo 1.5** (8.3B, Nov 20–21 2025) | **Tencent Hunyuan Community License**: territory **excludes EU, UK, South Korea**; separate licence needed above **100 million MAU**; otherwise royalty-free incl. commercial (within AUP) | **"Minimum GPU Memory: 14 GB (with model offloading enabled)"** | step-distilled 480p I2V: "a single RTX 4090 can generate videos within 75 seconds" (−75 %); 121 frames default; 1080p via SR net | I2V checkpoints (480p/720p); no FLF stated | none specific; one source scores it best "stylized" without method [S] | **[V]** GitHub README + LICENSE raw |
| **MiniMax-H3** (33B, Aug 2026) | **"other"** — community licence reportedly **excludes US, EU, UK, South Korea; authorization above $20M revenue** [S] — read the LICENSE before any use | not read | not read | tags: reference-to-audio-video, I2V, V2V, native audio | none | [V] HF listing (licence: other); terms [S] |
| **SkyReels-V3** (Skywork, Jan 28 2026; R2V-14B, A2V-19B, V2V-14B; Wan-architecture) | **"other"** on HF (licence file not read) [NV] | not read | not read | R2V = multi-subject reference-to-video; A2V audio-guided | none | [V] HF listing |
| **FramePack / FramePack-F1 / P1** (lllyasviel, 2025) | **Apache-2.0** | **"At least 6GB GPU memory"** (13B HunyuanVideo-based) | "2.5 seconds/frame (unoptimized) or 1.5 seconds/frame (teacache)" on RTX 4090 → ~3.5–6 min for 5 s at 30 fps [I] | I2V, very long clips (60 s); F1 variant forward-only | none | **[V]** GitHub README |
| **CogVideoX 1.5-5B-I2V** (Zhipu) | 2B Apache-2.0; **5B under "CogVideoX LICENSE"** (custom, "other") | ~ (older) | — | I2V; 10 s | none | [V] HF (licence: other); [S] GitHub |
| **Mochi 1 preview** (Genmo, 10B) | Apache-2.0 | high | — | **text-to-video only**, 480p | n/a | [V] HF |
| **Depth-Anything 3** (for 2.5D, see 1c) | **DA3-BASE Apache-2.0**; DA3-GIANT / NESTED-GIANT-LARGE **CC BY-NC 4.0**; DA3-LARGE disputed | small (135M params for BASE) | seconds | depth maps | — | [V] HF DA3-BASE; [S] HF discussions |

Verdict on open weights for this channel [I]: only **Wan 2.2 (Apache)**, **FramePack (Apache)** and
**HunyuanVideo 1.5 (if the creator and channel are outside EU/UK/KR — the project is US-market, so check the
creator's own jurisdiction)** are clean for a monetised channel without reading further paperwork. LTX-2.x is
fine for a sub-$10M creator but the derivative and remote-restriction clauses are unusual. MiniMax-H3's reported
US exclusion would make it unusable here if confirmed.

### 1c. Lightweight alternatives for illustrated 2D (what the current PIL/ffmpeg pipeline can grow into)

| Technique | Tooling | Licence | What it gives | Risks | Evidence |
|---|---|---|---|---|---|
| **2.5D parallax from a depth map** (the "living picture" / Immersity-style effect) | Depth-Anything-3 BASE (Apache) or V2 Small (Apache) → per-pixel displacement in a shader or numpy; **DepthFlow** (BrokenSource, **AGPL-3.0**, updated Oct 2026; ComfyUI-Depthflow-Nodes AGPL) | model Apache; DepthFlow AGPL (fine to *use* internally; distributing a modified tool or hosting it as a service triggers AGPL) | the source image stays pixel-exact; camera dolly/orbit/parallax; zero generation cost; deterministic | thin edges stretch on strong moves ("use gentle moves", 12 % overscan, soften depth edges); flat anime shading gives weak depth cues → layer separation by hand (character / mid / background) works better than monocular depth [I] | [V] HF licences; [S] GitHub DepthFlow, parallax write-ups |
| **Layered cut-out animation** (export character and background as separate PNGs, animate layers) | PIL/ffmpeg already in pipeline; Live2D Cubism / Spine 2D (not researched further, proprietary) | n/a | eye blinks, breathing, hand gestures, mouth flaps on the hero; keeps D-55 identity exactly | needs layered source art from the image model (or a `separate-image-layers` step; Canva connector exposes one, terms per D-53 unverified) | [I] |
| **Cartoon interpolation** (ToonCrafter) | Doubiiu/ToonCrafter, **Apache-2.0** code, SIGGRAPH Asia 2024; Replicate ~$0.064/run [S] | Apache | in-betweens between two drawn keyframes, 16 frames at 512×320 | low resolution, 2024-era, no active development found; morphing on complex scenes | [V] GitHub/HF; [S] replicate |
| **AnimateDiff** | SD1.5-era motion modules | OK | motion on SD images | 2023 tech; flicker/identity drift; nothing current found | [NV] |
| **Hosted "effects"**: Kling motion brush, PixVerse effects, Midjourney video (5 s, extend to ~21 s, in every subscription) | per vendor | per vendor ToS | quick "light motion" on stills | Midjourney has no API for video; motion-brush requires the web UI (hard from a phone) | [S] |

**What indie channels actually do (2025–2026):** every workflow write-up found describes the same
stills-first pipeline — lock the look with an image model (Midjourney/Niji), then add "subtle camera movements,
such as slow panning and zoom-ins" with Kling/Luma/Hailuo on a *subset* of shots, cut to the voice-over rhythm,
unify with a grade. Hailuo is repeatedly named the cheap "iteration engine" and the stylised/anime pick; Kling for
motion quality; Veo for style consistency. These are blog/creator posts, not measurements [S]. No channel
documented frame-exact line-art stability tests [NV].

### 1d. Judgement against the stated criteria

| Criterion | Controlled pan/zoom over an approved still (today) | 2.5D parallax | Hosted I2V (Kling/Omni/Wan 2.6/Luma) | Open I2V on a pod (Wan 2.2 5B / Hunyuan 1.5) |
|---|---|---|---|---|
| Keeps source structure | perfect | perfect except edge stretch | good at low motion; identity drift on faces/hands with larger moves [S] | same, somewhat worse |
| Natural motion | none (camera only) | camera only | yes (wind, hair, smoke, crowds) | yes |
| Morphing / texture flicker | none | none | present; worst on fast action and thin ink lines [S] | present; mitigated by negative prompts, more steps |
| Camera stability | exact | exact | prompt-dependent; FLF constrains it | same |
| No unplanned objects | guaranteed | guaranteed | not guaranteed (hallucinated extras, text, faces) | not guaranteed |
| Shot-to-shot continuity | guaranteed (same art) | guaranteed | each clip re-interprets the still | same |
| Cost per finished minute | ~$0 compute | ~$0 (CPU/GPU seconds) | $3–$10 list for 60 s with no retakes; realistic 2–3 takes → $6–$30/min | GPU time only (see pilot) |
| Phone-manageable | yes | yes | yes (async APIs, webhooks) | yes via RunPod CLI, slower |
| Rights (invariant 5/6) | own art | own art | vendor ToS; outputs may carry watermarks (SynthID/C2PA on Google) | own weights, own output |

**When a controlled pan over an approved still is likely better than generated video** [I]:
1. Any shot where the hero's face/identity must be exactly the approved sheet (D-55) — generation re-draws it.
2. Shots with on-screen text, maps, diagrams, numbers (claims, dates): generators invent or smear glyphs.
3. Short beats (< 3 s) and dense cut rhythms: motion barely registers and the retake cost dominates.
4. Line-heavy, flat-shaded frames: the documented failure mode is exactly "linework warps on fast action".
5. Anything that must survive editorial QA on facts: a generated clip can add an object that contradicts the claim map.

**Where generated video earns its cost** [I]: 5–10 "hero" shots per episode where atmosphere carries the
beat (weather, crowds, fire, water, a slow turn of the head), the Short's hook shot, and loopable backgrounds —
with FLF (both frames approved stills) to pin composition, and a negative prompt against morphing.

---

## Part 2 — narration voice

Script size assumed: ~1,500 words ≈ **8,500–9,000 characters** incl. spaces and punctuation ≈ 10 minutes
of read. Cost column = that one read, at list, no retakes.

| Provider / model | Naturalness & emotion control | Pauses / rhythm | Pronunciation control | Consistency across segments | Word timestamps | Licence / commercial | API stability | Price per 1M chars | Cost per 10-min script | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| **ElevenLabs Eleven v4** `eleven_v4` | "highest-quality", "control over how voices are performed", multi-speaker; docs recommend `eleven_v4` or `eleven_multilingual_v2` for video narration; v4 "perfect for long-form narration with complex emotional delivery" | audio tags (v3/v4 family), `<break>`; 10,000 chars/request | pronunciation dictionaries (IPA/CMU) on v2 family; v3/v4 tag-driven [S]; `apply_text_normalization` | request stitching/previous_text supported on v2 [S]; **Multilingual v2 is "most stable on long-form generations"** | **`/with-timestamps` returns character-level `alignment` + `normalized_alignment` (start/end seconds) at TTS time; Scribe v2 $0.22/h, "precise word-level timestamps"** | ToS (updated 2026-10-09): free = non-commercial only; **"paid subscribers may use the Services for commercial purposes"**; you retain rights to Output; no YouTube-specific clause | mature; model churn (v3 → v4 within a year; Flash v2.5 numbers not normalized) | **v4 $80; v4 Turbo $40; v3 $80; v3 Conversational $40; Multilingual v2 $80; Flash/Turbo $40** ($0.08 / $0.04 per 1k) | **$0.68–0.72** (v4 / v2); **$0.34–0.36** (Flash/Turbo); + Scribe $0.04 for 10 min; **SFX $0.12/min** | **[V]** pricing/api, docs/models, with-timestamps, terms |
| **Google Gemini 3.8 Flash TTS** `gemini-3.8-flash-tts` (stable; 130 languages) / Flash-Lite TTS | prompt-steerable style ("say this in a tired whisper"), 30 prebuilt voices [S] | prompt-driven; no SSML | prompt-driven; no phoneme control | one request per segment; no stitching feature | **no word timestamps from TTS** (transcription has them) [S] | Gemini API terms (not read) | 3.8 stable Oct 2026; 2.5 TTS limited to prior users; 3.1 TTS "legacy" | output $9/1M **tokens** (25 tokens per second of audio) → **$0.00225 per 10 s** of audio; text input $0.50/1M tokens; doubles Jan 1 2027 | **~$0.14** (600 s × $0.000225) | **[V]** Gemini pricing (2026-10-19) + models page |
| **OpenAI** `gpt-4o-mini-tts` (and tts-1/-hd) | `instructions` steer accent, emotion, intonation, speed, whisper; 13 voices, "marin"/"cedar" recommended; "optimized for English" | prompt-driven; no SSML | prompt-driven only | per request | **none stated** | usage policy **requires disclosure to end users that the voice is AI** | **deprecated: tts-1, tts-1-hd, gpt-4o-mini-tts shut down January 6, 2027 → `gpt-realtime-2.1-mini` via Realtime API** (not available on /v1/audio/speech) | $12/1M audio output tokens + $0.60/1M text ≈ **$0.015/min** [S]; tts-1 $15, tts-1-hd $30 per 1M chars | **~$0.15** (mini-tts) / $0.13 (tts-1) / $0.27 (hd) | **[V]** pricing, TTS guide, deprecations |
| **Azure AI Speech (Neural / Neural HD)** | large catalogue, SSML styles/roles; HD voices | **full SSML** `<break>`, `<prosody>`, `<phoneme>`, `<lexicon>` | **best in class** (IPA phoneme + custom lexicon) | deterministic per voice; stable across requests | **`WordBoundary` event: AudioOffset, Duration, Text, TextOffset, WordLength** [V] | Azure terms; outputs usable commercially (not re-read) | very mature; MAI voices promo till 2026-12-31 | page masks prices [NV]; secondary: **~$16/1M neural, $22/1M HD (cut from $30 in March 2026)**, 500k chars/month free | **~$0.14–0.20**; **free within the 0.5M/month F0 tier [V]** | [V] docs (word boundary, free tier); prices [S] texttolab/knowara |
| **Cartesia Sonic-3.6** | expressive, low latency; emotion tags | `<break>` tags (1 credit each) | custom pronunciations [S] | per request | **`add_timestamps` → word-level; `add_phoneme_timestamps`** [V docs via search] | **Pro $5/mo lists "Commercial use license"**; Free does not | fast model churn (3 → 3.5 → 3.6) | 1 credit = 1 char; Pro $5 = 100k credits (~133 min); overage $65/1M (Pro), $45 (Startup), $38 (Scale) | **~$5/month covers ~11 scripts**; marginal ≈ $0.55 at Pro overage | **[V]** cartesia.ai/pricing |
| **Hume Octave 2** | strongest acting-direction prompts; word+phoneme timestamps (`include_timestamp_types`, version 2) | prompt | prompt | — | yes | — | **Hume announced on Oct 2 2026 that the TTS (Octave) and EVI APIs end on November 13, 2026** (changelog + docs) — **do not adopt** | n/a | n/a | n/a | **[V]** dev.hume.ai changelog via search; [S] Cartesia posts |
| **PlayHT / PlayAI** | — | — | — | — | — | — | **acquired by Meta (July 2025); platform shut down December 31, 2025**; playhtai.com is a copycat [S] | n/a | n/a | n/a | [S] several, consistent |
| **MiniMax Speech 2.8 HD / Turbo** (2.6 now "Legacy") | strong emotion/voice design ($3/voice), rapid clone $1.5/voice | prompt + markers | limited [NV] | per request | **ASR with srt/vtt $0.38/h; no TTS timestamps priced** [NV] | MiniMax terms (not read) | 2.6 → 2.8 within months | **HD $100; Turbo $60** | **$0.85 (HD) / $0.51 (Turbo)** | **[V]** platform.minimax.io pricing-speech |
| **Fish Audio S2.1 Pro / S2 Pro** | good; wins vendor blind tests [S, vendor] | prompt | limited | per request | marketing lists "word-level timestamps" [S]; parameters not read | API wallet separate from web plans; commercial terms not read [NV] | model names churn (S1 → S2 → S2.1) | **$15 per 1M UTF-8 bytes** (= chars for English) [V docs via search]; free `s2.1-pro-free` fair-use till 2026-11-30 [S] | **~$0.13** | [V] docs.fish.audio pricing (via search) |
| **Kokoro-82M** (open, CPU) | clean but flat; no emotion knob (the TMR project measured 178 wpm at speed 1.0, pitch variation 2.8–4.6 st, no SSML) | per-sentence pauses only | phonemizer-level (misaki); custom pronunciations in project | deterministic, very consistent | phoneme durations from the timed ONNX export (project's `timings.py`) | **Apache-2.0** | stable; last model update Apr 2025 | $0 | **$0** (CPU minutes) | [V] HF; project CLAUDE.md |
| **Chatterbox / Chatterbox-Turbo** (Resemble) | expressive, exaggeration knob, zero-shot clone; **outputs watermarked** (Perth) [S] | prompt | limited | per request | none built in → forced alignment needed | **MIT** | active (updated Jun 2026); 23 languages | $0 | $0 + GPU | [V] HF licence |
| **CosyVoice 3** (Alibaba FunAudioLLM) | good, instruct-style control; project already uses CosyVoice for S2V | instruct tags | limited | per request | none built in | Apache-2.0 per several sources [S]; **exact HF repo id not confirmed** [NV] | active | $0 | $0 + GPU | [S] |
| **F5-TTS** | good clone; flat prosody | — | — | — | none | **weights CC-BY-NC-4.0** → not for a monetised channel | — | — | — | **[V]** HF licence |
| **Orpheus 3B** | expressive tags (`<laugh>` etc.) | tags | — | — | none | Apache-2.0 on HF **but Llama-3.2-based** → Llama licence constraints flagged by reviewers [S] | 2025 | $0 | $0 + GPU | [V] HF; [S] |
| **Dia 1.6B** | dialogue-oriented, non-verbal tags | tags | — | poor seed-to-seed consistency reported [S] | none | Apache-2.0 | 2025 | $0 | $0 + GPU | [V] HF |
| **Higgs Audio v2 / higgs-tts-2** (Boson) | strong | — | — | — | none | HF licence "other"; v3 reported research-only [S] | — | $0 | — | [V] HF (other) |

**Reading** [I]: for *one* English narrator with emotional direction, word timings and a clean commercial
licence, ElevenLabs v4/Multilingual v2 remains the default and its TTS-time `alignment` can replace the
separate Scribe pass for the narration track (Scribe stays useful for the final mixed audio). Azure is the only
contender with phoneme-exact pronunciation plus word boundaries and a free 500k/month tier — worth a parallel
test for proper nouns (history/science names) if ElevenLabs mispronounces. Gemini 3.8 Flash TTS is ~5× cheaper
than ElevenLabs but has no timestamps and would need Scribe or a forced aligner. Do not build on Hume (ends
Nov 13), PlayHT (gone) or OpenAI's current TTS (ends Jan 6 2027). Open-weight TTS only makes sense on CPU
(Kokoro) for test reads; none offers ElevenLabs-level direction plus a permissive licence plus timestamps.

---

## Part 3 — multimodal reviewers for automated frame/video QA

| Model | Video input? | How video is billed | Audio understood? | Price (input) | Rough cost to review a 10-min episode | Evidence |
|---|---|---|---|---|---|---|
| **Gemini 2.5 Flash / 3 Flash / 3.6 Flash / 3.8 Flash / 3.1 Pro** | **yes (file/URL, up to 10 videos/request; 3 h at low res, 1 h at high res)** | **~100 tokens/s at default (low) media resolution (66 tokens/frame at 1 fps), ~300 tokens/s at high; audio 32 tokens/s** | **yes — "both the audio and visual streams"**; note the task said to treat audio as not implied: here it IS included, but at 1 kbps mono | 2.5 Flash $0.30/1M; 3 Flash Preview $0.50; 3.6/3.8 Flash $0.75 (→ $1.50 in 2027); 3.1 Pro $2.00 (≤200k) | 600 s × (100+32) tokens ≈ 79k tokens → **$0.02 (2.5 Flash) to $0.16 (3.1 Pro)**; high res ≈ 200k tokens → $0.40 on Pro | **[V]** video-understanding doc + pricing |
| **Claude Opus 5.5 / Sonnet 5.5 / Haiku 5.5** | **no — images only** (JPEG/PNG/GIF/WebP; "Animations are unsupported, and only the first frame is used"); up to 600 images/request (100 on 200k models); >20 images → 2000 px cap | per image: ⌈w/28⌉×⌈h/28⌉ visual tokens; 1920×1080 = 2,691 tokens on the high-res tier (4.7+), 1,560 if pre-resized to 1456×819 | **no** | Opus 5.5 $4/1M; Sonnet 5.5 $2/1M; Haiku 5.5 $0.10/1M (≤100k prompts) | 120 frames (1 per 5 s) pre-resized ≈ 190k tokens → **Haiku 5.5 $0.02, Sonnet 5.5 $0.38, Opus 5.5 $0.75**; the project's `qa/sheet_review.py` runs Claude inside the session at no API cost | **[V]** platform.claude.com vision; claude-api skill price table (cached 2026-10-06) |
| **OpenAI GPT-5.x / GPT-6 family** | **no direct video**: images only (up to 1,500 images / 512 MB per request); patch-based tokens (32×32 patches × multiplier) | per image | no (realtime models take audio separately) | gpt-5-mini $0.25; gpt-5.4-mini $0.75; gpt-5.6-luna $0.20; gpt-6-luna $0.10; gpt-5.5 $5.00 per 1M | comparable to Claude; frames only | **[V]** images-vision guide + pricing |
| **Qwen3-VL-Plus (Alibaba API)** | **yes** (file URL ≤2 GB, up to 1 h for qwen3-vl-plus; 2 h for qwen3.5–3.8 series; `fps` sampling 0.1–10, default 2; or frame list 4–2,000 images) | **32×32 pixels per token** per sampled frame, frames counted in pairs | **"The model does not support understanding the audio track of video files"** | $0.20/1M (≤32k), $0.30 (≤128k), $0.60 (≤256k) in Singapore; output $1.60 | 600 s at 2 fps, 720p frames ≈ ~1,200 frames × ~900 tokens /2 ≈ 0.5M tokens → **~$0.15–0.30**; lower fps cuts it linearly | **[V]** model-pricing (2026-10-22) + vision doc |
| **Qwen open weights** (Qwen3-VL-8B Apache-2.0, Oct 2025; **Qwen3.8-27B Apache-2.0, Aug 2026, image+video**) | yes (frame lists) | GPU time | no | $0 + pod | a 27B VLM needs a 48–80 GB pod or quantisation [I] | **[V]** HF licences |

Caveats for QA design [I]: Gemini's 1 fps sampling will miss single-frame flicker and sub-second morphing; for
a "did a line wobble" check, extract frames at the cut points and 2–4 fps around motion and send them as images
(Claude/GPT/Qwen) or raise Gemini media resolution. Keep the project's existing deterministic measures
(`edit/motion_lint.py`, loudness targets) as the gate; use the VLM for semantic questions (unplanned object, wrong
hero, illegible text, continuity between shots).

---

## Ranked recommendation

1. **Keep the controlled-still pipeline as the default for every shot** (pan/zoom/cut over approved art). It
   is the only option that satisfies invariants 5 and 6 by construction and costs nothing. Add **2.5D parallax**
   (Depth-Anything-3 BASE, Apache) as the next motion tier inside `production/assemble.py` — same determinism,
   visible depth, zero vendor risk. Prefer hand-layered PNGs for the hero over monocular depth.
2. **Pilot generated video only for 5–10 hero shots per episode, with first+last frame both being approved
   stills**, in this order of trial: **Alibaba Wan 2.6 i2v-flash** (cheapest serious API: $0.05/s with audio,
   $0.025/s silent, 50 s free quota) → **Kling 3.0 Standard no-audio** ($0.084/s, FLF + elements, best motion
   reputation) → **Gemini Omni Flash** ($0.10/s, keyframe interpolation, SynthID/C2PA, Google's long-term path)
   → **Luma Ray3.2 720p** ($0.06/s, 16 keyframes). Hailuo 2.3 Fast is the cheapest per clip ($0.19 per 6 s) but is
   now "Legacy". Skip Runway for I2V (no last frame on Gen-4.x), skip Seedance via fal ($0.30/s), Sora (gone).
3. **Open weights on a RunPod GPU only if the pilot shows generated motion is worth it at volume**: Wan 2.2
   TI2V-5B (Apache, 24 GB, <9 min per 5 s) or HunyuanVideo 1.5 distilled (14 GB, ~75 s per 480p clip on a 4090)
   — both run in ComfyUI on an A5000/4090-class pod; keep `cloud.runpod` caps. Expect 2–3 takes per shot.
4. **Narration: stay on ElevenLabs** (v4 or Multilingual v2 for stability; Flash v2.5 for test reads at half
   price) and **switch the word timings for the narration track to the free `/with-timestamps` alignment**,
   keeping Scribe v2 ($0.22/h) for the final mix. Run a one-off Azure Neural HD comparison for pronunciation
   of proper nouns (free tier). Price risk is low either way (≈ $1 per episode).
5. **QA reviewer: Gemini 2.5/3.x Flash for whole-video semantic passes** (video+audio, pennies) and **Claude
   Haiku 5.5 / Sonnet 5.5 on extracted frames** for frame-exact questions (current `sheet_review.py` pattern);
   Qwen3-VL-Plus as a cheap second opinion that ignores audio.

**When NOT to use video generation**: text/diagram/map shots; any shot where the hero's face is the point;
beats under 3 s; episodes whose rights manifest forbids third-party-styled output; whenever the retake budget
would push the episode past 80 % of the cap in `config/spend_caps.json`.

## Pilot cost estimates (list prices, [I] arithmetic)

| Pilot | Assumptions | Estimated spend |
|---|---|---|
| **A. Current pipeline, one 10-min episode** | 8,700 chars ElevenLabs v4 ($0.70) + Scribe 10 min ($0.04) + ~2 min of SFX ($0.24) + 2.5D parallax on GPU/CPU ($0) | **≈ $1.0** audio; $0 video |
| **B. Hybrid: 10 hero shots × 5 s, 2 takes each = 100 s generated** | Wan 2.6 i2v-flash silent $2.50 / with audio $5.00; Kling 3.0 no-audio 720p $8.40; Omni Flash $10.00; Luma 720p $6.00; Hailuo 2.3 Fast ≈ 20 clips × $0.19 = $3.80; Runway Gen-4 Turbo $5.00 (no FLF) | **$2.50–$10 per episode** (+ $1 audio) |
| **C. Fully generated 10 min, 2 takes (1,200 s)** | Wan 2.6 flash $30–60; Kling 3.0 $101; Omni Flash $120; Luma 720p $72; Veo 3.1 Standard (was) $480 | **$30–$120+** — not recommended |
| **D. Open-weight pilot on a pod** | 20 clips Wan 2.2 5B @ ≤9 min each ≈ 3 h on a 24 GB pod; A5000 ≈ $0.27/h (project runbook figure, not re-verified) → ≈ $1; 4090-class pods cost more [NV] | **≈ $1–3 GPU** + setup time |
| **E. QA pass per episode** | Gemini 2.5 Flash full video ≈ $0.02; Claude Sonnet 5.5 on 120 frames ≈ $0.38 (Haiku 5.5 ≈ $0.02); Qwen3-VL-Plus ≈ $0.2 | **< $1** |

All of these are below the 80 %-of-cap threshold only if `config/spend_caps.json` says so — check before any run.

## Uncertainties

- **Kling, Vidu, PixVerse, Pika, BytePlus official pricing pages are JavaScript-rendered or 404 here**; their
  numbers are from dated secondary pages (Kling checked 2026-10-13 by FrameSurfer; fal mirrors Kling's $0.084/$0.126).
- **Veo on Vertex / "Gemini Enterprise Agent Platform"** GA pricing and Omni Flash's first/last-frame API shape
  were not read from a Google page (the Omni Flash doc URL 404'd); the models page says "keyframe interpolation".
- **No independent, frame-level test of line-art stability for any I2V model exists in what I found**; the
  anime claims (Hailuo stylised, Wan "keeps lines", Kling motion, Veo style) are blog opinions. The pilot must
  measure this itself (e.g. edge-map IoU between frame 0 and frame N, flicker as frame-to-frame edge delta).
- Azure TTS dollar prices are masked on the pricing page; the $16/$22 per 1M figures are secondary.
- Fish Audio and MiniMax commercial-use terms for API output were not read.
- MiniMax-H3 and SkyReels-V3 licences are "other" on HF; the territorial/revenue clauses reported for H3 are
  secondary.
- CosyVoice 3's exact repository and licence were not confirmed.
- Claude/Anthropic prices come from the claude-api skill's cached table (2026-10-06), not a live fetch.
- Everything about "what indie channels use" is anecdotal; no measured adoption data.

## Dated source list

Official pages read 2026-10-22 unless noted ([V]):
- Google Gemini API pricing (page footer "Last updated 2026-10-19"): https://ai.google.dev/gemini-api/docs/pricing
- Google Veo 3.1 docs (shutdown Oct 22 2026, FLF, reference images, personGeneration): https://ai.google.dev/gemini-api/docs/veo
- Google Gemini video docs (Omni Flash recommendation): https://ai.google.dev/gemini-api/docs/video
- Google Gemini models list (Omni Flash stable, TTS models): https://ai.google.dev/gemini-api/docs/models
- Google Gemini video understanding (tokens/s, 1 fps, audio): https://ai.google.dev/gemini-api/docs/video-understanding
- Google Cloud blog, 2026-06-30, Gemini Omni Flash preview, $0.10/s: https://cloud.google.com/blog/products/ai-machine-learning/nano-banana-2-lite-and-gemini-omni-flash-available
- Runway API pricing: https://docs.dev.runwayml.com/guides/pricing/ ; models: https://docs.dev.runwayml.com/guides/models/
- Luma API pricing (Ray3.2): https://lumalabs.ai/api/pricing
- MiniMax video pricing (H3, Hailuo legacy): https://platform.minimax.io/docs/guides/pricing-video
- MiniMax speech pricing (2.8, 2.6 legacy): https://platform.minimax.io/docs/guides/pricing-speech
- Alibaba Model Studio model pricing ("Last Updated: Oct 22, 2026"): https://www.alibabacloud.com/help/en/model-studio/model-pricing
- Alibaba wan2.6-i2v model page ("Oct 11, 2026"): https://www.alibabacloud.com/help/en/model-studio/wan2-6-i2v
- Alibaba vision / video input limits: https://www.alibabacloud.com/help/en/model-studio/vision
- OpenAI video generation (Sora shutdown 2026-09-24): https://developers.openai.com/api/docs/guides/video-generation
- OpenAI deprecations (TTS Jan 6 2027; Sora; transcribe Feb 26 2027): https://developers.openai.com/api/docs/deprecations
- OpenAI pricing: https://developers.openai.com/api/docs/pricing ; TTS guide: https://developers.openai.com/api/docs/guides/text-to-speech ; vision: https://developers.openai.com/api/docs/guides/images-vision
- fal.ai Kling v3 standard I2V (price, end_image_url, elements): https://fal.ai/models/fal-ai/kling-video/v3/standard/image-to-video/llms.txt
- fal.ai Seedance 2.0 I2V (price, end_image_url): https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt
- Pika API pricing page (no numbers rendered): https://dev.pika.art/pricing
- ElevenLabs API pricing: https://elevenlabs.io/pricing/api ; models: https://elevenlabs.io/docs/overview/models ; with-timestamps: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps ; terms ("Last Updated: 09 October 2026"): https://elevenlabs.io/terms-of-use
- Cartesia pricing: https://cartesia.ai/pricing ; timestamps docs: https://docs.cartesia.ai/examples/tts-sse-with-timestamps
- Hume TTS sunset (changelog 2026-10-02, ends 2026-11-13): https://dev.hume.ai/voice/changelog ; https://dev.hume.ai/docs/text-to-speech-tts/overview ; timestamps: https://dev.hume.ai/docs/text-to-speech-tts/timestamps
- Fish Audio pricing & rate limits: https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits
- Azure Speech pricing (prices masked in fetch): https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/ ; WordBoundary: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis
- Anthropic vision docs: https://platform.claude.com/docs/en/build-with-claude/vision
- Wan2.2 GitHub README (Apache-2.0, 24 GB / 80 GB, <9 min): https://github.com/Wan-Video/Wan2.2
- Hugging Face org listings (Wan-AI, Lightricks, MiniMaxAI, Qwen, Skywork) and model cards: https://huggingface.co/Wan-AI , https://huggingface.co/Lightricks/LTX-2 (LICENSE dated January 5, 2026), https://huggingface.co/Lightricks/LTX-2.5 , https://huggingface.co/MiniMaxAI/MiniMax-H3 , https://huggingface.co/Skywork/SkyReels-V3-R2V-14B , https://huggingface.co/hexgrad/Kokoro-82M , https://huggingface.co/ResembleAI/chatterbox , https://huggingface.co/SWivid/F5-TTS , https://huggingface.co/canopylabs/orpheus-3b-0.1-ft , https://huggingface.co/nari-labs/Dia-1.6B , https://huggingface.co/bosonai/higgs-tts-2-3b-base , https://huggingface.co/genmo/mochi-1-preview , https://huggingface.co/zai-org/CogVideoX1.5-5B-I2V , https://huggingface.co/depth-anything/DA3-BASE , https://huggingface.co/Qwen/Qwen3.8-27B , https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct
- HunyuanVideo-1.5 README and LICENSE ("Release Date: November 21, 2025"): https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5 ; https://raw.githubusercontent.com/Tencent-Hunyuan/HunyuanVideo-1.5/main/LICENSE
- FramePack README (Apache-2.0, 6 GB, 1.5–2.5 s/frame): https://github.com/lllyasviel/FramePack
- ToonCrafter: https://github.com/Doubiiu/ToonCrafter ; DepthFlow (AGPL-3.0): https://github.com/BrokenSource/DepthFlow

Secondary sources used ([S]):
- Kling API prices "checked October 13, 2026": https://framesurfer.com/blogs/kling-ai-pricing ; Kling 3.0 endpoint behaviour: https://www.krea.ai/blog/kling-3-0-api-access-guide-pricing-code-examples-for-multi-shot-ai-video
- Seedance BytePlus token pricing: https://framesurfer.com/blogs/seedance-2-0-pricing ; https://anikuku.com/blog/seedance-2-api-pricing-guide-2026 ; https://www.cometapi.com/seedance-2-5-api-pricing/
- Gemini Omni 1.1 Flash GA/prices: https://www.eesel.ai/blog/gemini-omni-1-1-flash-pricing ; https://shattered.io/gemini-omni-1-1-flash-video-2026/
- Vidu: https://magichour.ai/blog/vidu-ai-review ; https://omniakey.com/blog/vidu-q4-preview ; PixVerse: https://www.atlascloud.ai/blog/tips/pixverse-v5 ; https://verna.one/models/pixverse-v5.6-image-to-video ; Pika: https://apiframe.ai/guides/pika-labs-api-guide
- Runway keyframe support by model (Sept 2026): https://runware.ai/docs/models/runway-aleph-2-0 ; https://mcpservers.org/agent-skills/runwayml/rw-api-reference ; API 2024-11-06: https://docs.dev.runwayml.com/api-details/versions/2024-11-06/
- Wan weights status: https://www.runpod.io/articles/guides/wan-2-7-runpod ; https://localaimaster.com/blog/wan-2-7-open-source
- LTX-2 licence summaries: https://www.sume.com/blog/ltx-2-open-source-video-model ; https://www.canirun.ai/license/ltx-2-community/
- MiniMax-H3 licence terms: https://fuser.studio/articles/best-open-source-video-models
- Anime I2V opinions: https://morphed.app/blog/ai-video-generator-for-anime ; https://pixverse.ai/en/blog/best-ai-anime-video-generators-2026 ; https://www.noviai.ai/video-tips/chinese-image-to-video-ai/ ; https://www.piclumen.com/blog/4-best-ai-animation-models/
- Indie workflows: https://medium.com/@alex.braun.77/automating-a-childrens-story-for-youtube-using-ai-my-workflow-with-chatgpt-midjourney-kling-ai-da287b80d34b ; https://kling2-6.com/en/blog/kling-2-6-niji-7-anime-workflow ; https://chillframe.com/blog/ai-youtube-channel
- Depth Anything 3 licence split: https://huggingface.co/depth-anything/DA3-LARGE/discussions/2 ; https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3
- Azure TTS prices: https://texttolab.com/blog/azure-text-to-speech-pricing ; https://knowara.com/ai-tools/voice/microsoft-azure-ai-speech/
- OpenAI mini-tts per-minute: https://tokenmix.ai/blog/gpt-4o-mini-tts-cheapest-tts-api-2026 ; Gemini TTS no timestamps: https://www.llmreference.com/model/gemini-2.5-flash-preview-tts
- PlayHT shutdown: https://www.agilelogics.com/news/playht ; https://texttolab.com/blog/play-ht-shutdown-alternatives
- Open TTS licence/quality round-ups: https://www.cartesia.ai/learn/open-source-tts ; https://offlinetts.com/blog/tts-model-ranking-2026/ ; https://localaimaster.com/blog/best-local-tts-models
- Qwen3.8 27B Apache: https://openrouter.ai/qwen ; Qwen3-VL-Plus price: https://ai-api-hub.com/providers/alibaba/models/alibaba-qwen3-vl-plus/
