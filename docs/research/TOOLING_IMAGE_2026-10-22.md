# Image models for a consistent anime-like 2D/2.5D explainer world — research, 2026-10-22

Scope: hosted APIs with multi-reference + editing (A), open weights on a rented GPU (B), hosted marketplaces (C),
consistency techniques used by indie creators (D), visual-embedding tools (E). Research only: no paid call was made,
nothing was generated. Prices are in USD, as published on the day of reading (2026-10-22). Every row says whether
the fact was read on an official page (**V** = verified on vendor page / model card / licence text), comes from a
third-party page only (**T** = third-party, not verified), or is my own arithmetic/inference (**I**). "not verified"
means exactly that: do not budget on it.

Reading guide for the creator's situation: the channel is a solo creator with revenue far under US$5M, cloud-first,
managed from a phone; the look wanted is a colourful Naruto-era shonen aesthetic with original characters, one
style identity across episodes, and shot-to-shot continuity (same room, same people, same positions). The
"anime look" and "continuity" are separate problems: the open anime checkpoints win the first and lose the second;
the multi-reference editors win the second and are unproven on the first. That tension drives the recommendation.

---

## 1. Comparison table

Legend: Anime = expected quality for anime illustration (evidence level in brackets); Multi-ref = reference
images per request; Edit = instruction editing / masks / regional; Control = seed, pose/structure control, style
lock; Price = per image at ~1K unless noted.

| Model (version, date) | Anime quality | Multi-ref | Edit | Control | Licence for this creator | Price / image | API / infra | Moderation | Main risks |
|---|---|---|---|---|---|---|---|---|---|
| **FLUX 3 Image Klein** (BFL, open weights, 2026-10-15) **V** | Unknown: no anime sample or benchmark found (brand new) | up to 10 refs **V** | instruction edits; bounding boxes [top,left,bottom,right] on 0–1000 grid for placement/local edits (guide, not hard mask) **V** | seed in Diffusers example; API seed field not documented **V**; `safety_tolerance` 0–7 (default 2) on FLUX 3 API **V**; Base variant trainable (LoRA) **V** | FLUX Kommunity License: commercial use of Outputs allowed for "Qualifying User" (<US$5M revenue incl. affiliates) **V**; Derivatives (fine-tunes/LoRA) restricted to non-commercial use (§2.b) while §2.a(ii) allows commercial Outputs "including Outputs from Derivatives" — internal tension, see §3 **V** | BFL API: $0.008 (768²), **$0.009 (1K)**, $0.011 (1.5K), $0.014 (2K), $0.036 (4K); T2I and edit same price **V**; fal "planned" $0.027 (1K) **V** | BFL API GA 2026-10-15; HF weights (5.6B; 11.2 GB BF16 / 5.6 GB FP8; INT8 runs on 8 GB RTX) **V**; Diffusers via ModularPipeline (main branch) **V**; ComfyUI: BFL says RTX 4070 <9 s/1MP in ComfyUI **V** | BFL safety tiers; no watermark statement found | Needs its prompt upsampler ("do not use without") **V**; one week old; anime untested; LoRA-derivative licence ambiguity |
| **FLUX 3 Image** (BFL, API only, 2026-10-01) **V** | AA T2I Elo 1117 (rank 8–15, Oct 2026) **V**; anime: not measured | up to 10 **V** | same editing model incl. bounding boxes; grounding (web/image search) on by default **V** | `safety_tolerance` 0–7; `resolution` 768sq/1k/1.5k/2k/4k; 15 aspect ratios; seed not documented **V** | API output; weights not public **V** | $0.041 (768²), **$0.048 (1K)**, $0.100 (2K), $0.607 (4K) **V** (release notes) | BFL async API (poll); OpenRouter, fal **V** | as above | 5× Klein's price; weights closed |
| **FLUX.2 [pro] / [flex] / [max]** (BFL, 2025-11-25) **T** | AA anime snapshot (undated) listed FLUX.2 [pro] 2nd, [max] 3rd behind GPT Image 1.5 **T** | up to 8–10 **T** | editing, multi-ref **T** | seed on FLUX.2 endpoints **T** (not re-read today) | API output | Together: pro $0.03, flex $0.03 per image **V**; max $0.07/MP **V**; BFL own calculator cells did not render **V** | BFL API, Together, fal, OpenRouter | BFL tiers | Superseded by FLUX 3 for new work (BFL: "FLUX.2 remains fully supported") **V** |
| **FLUX.2 [klein] 4B** (open) **V** / **9B** | Unknown for anime | multi-ref editing **V** | edit **V** | seed (local) | 4B **Apache 2.0** **V**; 9B FLUX Non-Commercial **V** | BFL "from $0.014" **T**; fal/Replicate ~$0.015–0.016 **T** | ~13 GB VRAM **V**; Civitai trainer supports Klein 4B/9B Base **V** | — | Lower quality than FLUX 3 Klein (BFL: +91 Elo T2I, +70 edit vs klein 9B) **V** |
| **FLUX.2 [dev]** (open, 32B) **V** | Unknown for anime | single + multi-ref (character/object/style) **V** | yes | seed (local) | **FLUX Non-Commercial License**: model may be used only for Non-Commercial Purposes; "revenue-generating activity" is commercial; §2(d) says Outputs may be used commercially but §4(a)(i) bars commercial/production use of the model and "any data produced" — unresolved conflict **V** | no hosted BFL endpoint (local only) **V**; Together $0.0154 **V**; fal $0.012/MP **V** | RTX 4090/5090 "possible" (no GB figure) **V** | — | Licence unfit for a monetised channel's production run without a paid self-hosted licence |
| **FLUX.1 Kontext [dev]** **T** | — | 1 (in-context edit) | yes | seed | non-commercial weights **T**; Kontext [pro] API $0.04/MP (Together) **V** | | | | Generation behind FLUX.2/3 |
| **Nano Banana 2.1** (`gemini-nano-banana-2.1`, Google, GA 2026-10-06) **V** | AA T2I Elo 1176 (rank 3–6) **V**; anime: vendor blogs say NB family is weaker than Seedream on anime consistency **T** | up to **14** per prompt (10 objects + 4 characters; no style slot) **V** | prompt editing, multi-turn; "inpainting" by prompt; no mask API **V** | **no seed** ("seed, topK, logprobs, temperature, topP aren't supported … returns an API error") **V**; resolutions 1K/2K/4K **V** | Gemini API terms (paid tier: data not used for training) **V** | **$0.0336 (1K)**, $0.0504 (2K), $0.113 (4K) standard; batch $0.0168 / $0.0252 / $0.0567 **V**; input image 1,120 tokens → ≈ $0.0017 per reference (std) **I** | Gemini API + Vertex, GA; batch 24 h **V** | SynthID on all images **V**; C2PA **V**; targeted IP blocks (Disney C&D reported) **T**; community reports of stricter filters since NB2 **T** | No determinism; watermark; the creator already judged Gemini images "too expensive and not good enough" (that was Pro at $0.134; 2.1 is 4× cheaper) |
| **Nano Banana Pro** (`gemini-3-pro-image`, 2025-11) **V** | AA Elo 1118 **V** | 6 objects + 5 characters + **3 style refs** **V** | yes | no seed **T**; thinking always on **V** | as above | $0.134 (1K/2K), $0.24 (4K); batch $0.067 / $0.12 **V** | GA | SynthID | Price; already rejected by creator |
| **Nano Banana 2 Lite** (`gemini-3.1-flash-lite-image`) **V** | AA Elo 1107 **V** | 14 objects; "not optimized for multiple reference inputs or multi-turn sequential editing" **V** | weak | no seed | as above | $0.0336 (1K) / batch $0.0168 **V** | GA | SynthID | Not an editor |
| **GPT Image 2.5 Sunburst / Flare** (OpenAI, snapshot 2026-09-08) **V** | AA T2I #1/#2 (Elo 1222 / 1207) **V**; anime: AA undated anime snapshot had GPT Image 1.5 (high) #1 **T** | up to **16** input images on `/v1/images/edits` **V** | prompt-based masks (mask applied to first image), inpainting **V** | no seed documented **I**; `moderation` auto/low **V**; quality low/medium/high/xhigh/max **V**; arbitrary WxH (multiples of 16, ≤3:1, max 3840×2160) **V** | OpenAI terms | tokens: image out $30/M, image in $8/M, text $5/M; batch half **V**; no official per-image table for 2.5 ("models can use different token counts for the same quality") **V**; earlier-model token counts 272/1056/4160 (low/med/high @1024²) → $0.008/$0.032/$0.125 **I**; third-party 2.5/2 estimates $0.006–$0.211 **T** | Images API + Responses API; batch **V** | OpenAI safety; `low` moderation available **V** | Cost opaque per image; no seed; style drift between calls is the common complaint **T** |
| **Seedream 4.5** (ByteDance, via fal) **V** | Vendor comparisons: better anime/stylised consistency than NB Pro in "a documented AI anime production" **T** (no primary source found) | up to **10** image URLs **V** | edit endpoint; multi-image composition **V** | seed param existed on 3.0 (default −1) **T**; 4.5 seed not verified; watermark param default true in ComfyUI node schema **T** | "Commercial use via fal Partner agreement" **V**; BytePlus ModelArk terms not read (pages did not render) | fal **$0.04** per image, up to 4 MP **V**; BytePlus official $0.04 **T** | fal, Replicate ($0.03 for 4.0 **V**), BytePlus ModelArk (ap-southeast) **T** | "AI Generated" label when watermark on **T** | Official docs unreachable today; ByteDance data/ToS questions for US-market channel |
| **Seedream 5.0 Pro / Lite / Flash** (2026) **T** | — | Pro ≤10; Lite ≤14 **T** | yes **T** | | | Pro $0.045 (≤2.36 MP), +$0.003 per extra ref; Flash $0.018; Lite ~$0.035 **T** | BytePlus, fal, GMI | | all figures third-party; not verified |
| **Qwen-Image-Edit-2511** (Alibaba, open 20B, 2025-12) **V** | Anime community LoRAs exist (style only) **T**; base anime quality unmeasured | multi-image (example uses 2; Replicate: "works best with 1 to 3") **V** | instruction edits; "character consistency has been significantly improved", multi-person fusion **V**; built-in popular LoRAs **V** | seed (local); LoRA stackable **V**; ControlNet not in card | **Apache 2.0** **V** | fal **$0.03/MP** **V**; Replicate ~$0.04 **T** | fal, Replicate, ComfyUI native (Lightning 4-step LoRA) **V**; FP8 ≈16 GB, BF16 ≈40 GB **T** | none built in | 1–3 refs only; heavy to self-host |
| **Qwen-Image-2.1** (open 7B, 2026-09-20) **V** | — | up to 10 refs **V** | local edits by circles/annotations/mask; RGBA output **V** | seed (local) | **Qwen Research License**: non-commercial only ("research or evaluation"); commercial licence by email **V** | — | HF weights | — | Excluded for production unless Alibaba grants a licence |
| **Qwen-Image-2.0 / 2.0 Pro** (API only) **T** | AA lists both (2026) **T** | up to 6 images (edit API) **T** | yes | | Alibaba Model Studio terms | $0.035 (Singapore) **T** (official page via search snippet); Together $0.04 / $0.08 **V** | Alibaba, Together | | pricing/limits not read on the official page today |
| **Krea 3** (Krea API) **V** | — | up to **8** refs **V** | `regional_edit` (needs ≥1 ref) **V** | **seed**, negative prompt **V**; style refs & LoRAs "coming soon" **V** | commercial licence of outputs: claimed on features page (search snippet) — not confirmed in my read → not verified | $0.03 (1K) / $0.06 (2K) + $0.02 per 1K ref (+$0.07 per 2K ref), +$0.02 `high`; `ultra` +$0.20 (Max plan) **V** | available to every workspace **V** | — | Refs are charged (4 refs = +$0.08 → ≈$0.11/img) |
| **Ideogram 3.0 / 4.x** **T** | Not anime-focused | character reference (1 image) + style refs **T** | edit/remix/reframe **T** | | Ideogram terms | 3.0 Turbo/Default/Quality $0.03/$0.06/$0.09; **character ref $0.10/$0.15/$0.20**; 4.5 low/med/high $0.03/$0.06/$0.10 **T**; official table did not render ("Loading current prices"; pay-as-you-go 1¢/credit) **V** | API GA | | Character surcharge 3× makes it the dearest option |
| **Recraft V4 / V4.1 / V4 Styles** (V4 Feb 2026) **V** | Design/vector-oriented; anime not a focus | V4 Styles: 1–10 refs build a reusable style **T** | **no prompt-based editing in V4** ("not yet supported") **V**; img2img/inpaint only on V3 ($0.04) **V** | style ID reuse **V** | Recraft terms | V4.1 raster $0.035; V4 Styles $0.035 + $0.005 style creation **V** | API GA | | Not an editor → weak for continuity |
| **Stability Stable Image Ultra / Core / SD3.5 / Control** **V** | Core/Ultra generic; not anime-tuned | Style Guide / Style Transfer control (1 ref) **V** | Inpaint $0.05, Search&Replace $0.05 **V** | Control: Structure/Sketch $0.05 **V** | Community licence free under $1M revenue **T** | Ultra $0.08, Core $0.03, SD3.5 Large $0.065 **V** | API GA | | Single-ref only |
| **Midjourney V8.2** **T** | strong stylised look **T** | Omni Reference only via `--v 7` **T** | | | **no official API** (Oct 2026); third-party wrappers risk bans **T** | subscription | web/Discord | | Unusable for an automated phone-driven pipeline |
| **NovelAI Diffusion V5** **T** | anime-native | Vibe Transfer / Precise Reference / Character Reference **not in V5 at launch** (NovelAI's own V5 page via search) **T** | | | subscription ($10/$15/$25 Anlas) **T**; **no official public developer API** (third-party wrapper says image endpoint deprecated 2024-03-21) **T** | | | | Excluded: no API, no refs on V5 |
| **Imagen 4** | — | — | — | seed (Vertex) **T** | | Vertex ~$0.02/$0.04/$0.06 **T** | Gemini API docs call Imagen "legacy … (shut down)" **V**; Vertex status not verified | | Excluded |
| **Illustrious XL v2.0** (Onoma, SDXL, open) **V** | Community consensus: top anime base with the largest LoRA/ControlNet ecosystem **T** | none native; via IP-Adapter / ControlNet / LoRA | inpaint via SDXL tooling | full seed determinism; ControlNet Union SDXL (Apache 2.0: openpose, depth, lineart, anime-lineart, canny …) **V** | HF licence tag **creativeml-openrail-m** **V** (OpenRAIL-M permits commercial use with use restrictions; Onoma's early v0 text "discourages" monetisation **T**); v3.x licence not found → not verified | self-host: RunPod 4090 community $0.34/h **V** → ≈$0.001–0.003/image **I** | ComfyUI; Civitai trainer supports "Illustrious" base **V** | none | Weak native multi-ref; consistency needs LoRA + ControlNet discipline |
| **Animagine XL 4.0** (Cagliostro, 2025-01-24) **V** | Anime-native (8.4M images) **V**; community says less popular than Illustrious/NoobAI **T** | as above | as above | seed; 1024 training res **V** | **CreativeML Open RAIL++-M**, commercial use permitted **V** | self-host | ComfyUI | none | Older ecosystem |
| **NoobAI-XL 1.1** **V** | community favourite for character knowledge **T** | — | — | — | **commercialisation prohibited incl. generated products** (added Section II) **V** | — | — | — | **Excluded** (and most merges inherit it) |
| **Pony Diffusion V6 XL** | — | — | — | — | licence not read today → not verified | | | | — |
| **Z-Image / Z-Image-Turbo** (Tongyi, 6B, Apache 2.0, 2025-11/2026-01) **V** | photoreal focus; anime not assessed **T** | none (Edit/Omni-Base "to be released") **V** | not yet | seed; ≤16 GB **V** | Apache 2.0 **V** | self-host | | | No editing yet |
| **HiDream-I1** (17B, MIT transformer; Llama-3.1 text encoder) **V** / **E1.1 edit** (2025-07-16) **V** | — | 1 | yes | | MIT + Llama licence **V** | self-host, large | | | Heavy; ecosystem small |
| **Lumina-Image 2.0** (2B, Apache 2.0) **V** | — | — | — | | Apache 2.0 **V** | | | | Small, no editing |
| **OmniGen2** (4B, Apache 2.0, 2025-06-16) **V** | OmniGen2's own report: below FLUX.1 Kontext max on some tables **T** | multi-subject in-context (humans, objects, scenes) **V** | instruction edits **V** | ~17 GB VRAM **V** | Apache 2.0 **V** | self-host | | | Quality behind 2026 editors **T** |
| **UNO** (ByteDance) **T** | — | multi-subject | — | | weights **CC BY-NC 4.0** (code Apache) **T** | | | | Excluded (NC) |
| **DreamO** (ByteDance) **V** | — | identity/style/multi-subject customisation **T** | — | | HF tag apache-2.0 **V** | | | | FLUX.1-dev-based (licence of base applies) **T** |
| **IP-Adapter (h94)** **V** | works on SDXL anime bases **T** | 1–N image prompts | — | | Apache 2.0 **V** | | | | FaceID variants need InsightFace |
| **InstantID / PuLID / IP-Adapter FaceID** **T** | photo-face models, poor fit for anime faces **I** | 1 face | — | | depend on InsightFace antelopev2: **non-commercial research only** (insightface.ai) **T** | | | | Excluded for a monetised channel |

---

## 2. Independent benchmarks found (dated)

- Artificial Analysis Text-to-Image leaderboard (read 2026-10-22, "AA-Image-T2I v2.1"): GPT Image 2.5 Sunburst 1222,
  GPT Image 2.5 Flare 1207, GPT Image 2 (high) 1186, Nano Banana 2.1 1176, MAI-Image-2.6 1166, Grok Imagine Image 2.0 1166,
  Nano Banana 2 1140, Muse Image 1127, GPT Image 1.5 1123, MAI-Image-2.6-Flash 1119, Nano Banana Pro 1118, MAI-Image-2.5 1118,
  **FLUX 3 Image 1117**, MAI-Image-2.5-Pro 1114, Nano Banana 2 Lite 1107. **V** No anime category was reachable today; the
  image-editing leaderboard returned 404. A search snippet of an undated AA "style/anime" page listed GPT Image 1.5 (high) first,
  FLUX.2 [pro] second, FLUX.2 [max] third, Seedream 4.0 #8 — **T**, undated, treat as a hint only.
- BFL's own numbers for FLUX 3 Image Klein (internal, 2026-10-15): first in T2I, multi-reference and editing among open
  models; +91 Elo T2I and +70 edit vs FLUX.2 [klein] 9B with 38% fewer parameters. **V but vendor-internal**.
- No independent, dated head-to-head on *anime character identity across edits* was found for any model. This is the
  central gap the pilot must close.

---

## 3. One paragraph per serious candidate

**FLUX 3 Image Klein (BFL).** Released 2026-10-15 with open weights (5.6B generator; 11.2 GB BF16, 5.6 GB FP8, INT8 on
8 GB RTX) and a $0.009-per-1K-image API where text-to-image and editing cost the same; up to ten references, instruction
editing, and bounding boxes that place or confine edits on a 0–1000 grid. It is the only model in this list that is at once
cheap, hosted, multi-reference, editable, self-hostable, and trainable (the separate "Klein Base" checkpoint exists for
fine-tuning/LoRA). The FLUX Kommunity License lets a "Qualifying User" (<US$5M revenue incl. affiliates) use Outputs
commercially; §2.a(ii) even says "including Outputs from Derivatives", but §2.b restricts creating/using Derivatives to
Non-Commercial Purposes — so a house-style LoRA on Klein Base used for a monetised channel sits in an ambiguity the licence
does not resolve (ask BFL, or keep LoRA work on an Apache base). Unknowns: anime look (no sample found), seed support on
the API (undocumented; present in the Diffusers example), and BFL's warning not to run it without its prompt upsampler.
Verdict: first pilot candidate on price and feature fit; quality is the open question.

**Nano Banana 2.1 (Google).** GA 2026-10-06; AA Elo 1176; 14 references per prompt (10 objects + 4 characters, no style
slot — style slots exist only on Pro); multi-turn editing; 1K/2K/4K; $0.0336 per 1K image standard, $0.0168 batch, plus
~$0.0017 per reference image (1,120 tokens × $1.50/M; my arithmetic). No seed (API error if set), SynthID watermark on every
image, C2PA, and rights-holder blocks (Disney reported). The creator previously judged Gemini images too expensive and not
good enough; that was Nano Banana Pro at $0.134. 2.1 is a different price class, but the same family and the same
watermark/moderation posture, and vendor comparisons consistently put the family behind Seedream on anime styling.
Verdict: include as the hosted control in the pilot only if the creator wants to re-test Google; otherwise skip.

**Seedream 4.5 (ByteDance) via fal.** $0.04 per image on fal, up to 10 input images, up to 4 MP, "Commercial use via fal
Partner agreement". Several (vendor) comparisons call it the better anime/stylised model and cite a "documented AI anime
production" where it held character and style better than Nano Banana Pro — I could not reach the primary source. Official
BytePlus docs did not render today, so reference limits, seed, watermark default and official price are not verified
(third-party: $0.04, watermark on by default with an "AI Generated" corner label, Seedream 5.0 Pro $0.045 + $0.003 per extra
reference). Verdict: strong pilot candidate on anime reputation; treat ToS/data-handling and the watermark default as
things to read before any paid batch.

**Qwen-Image-Edit-2511 (Alibaba, Apache 2.0).** 20B open editor; model card: character consistency "significantly
improved", multi-person fusion, built-in community LoRAs, ComfyUI native with a 4-step Lightning LoRA; fal $0.03/MP;
FP8 ≈16 GB / BF16 ≈40 GB (third-party). Only 1–3 inputs work well, so it is an *editor of a locked master frame*, not a
10-reference composer. Apache 2.0 removes all licence doubt, and the Qwen-Edit "multiple angle" LoRA tutorials (2026) are the
closest thing found to a documented shot-to-shot workflow. Its successor Qwen-Image-2.1 (10 refs, RGBA, masks) is
research-licence only — unusable for the channel without a written commercial licence. Verdict: candidate #3, best as the
continuity editor on top of whichever model wins the look.

**Illustrious XL v2.0 / Animagine XL 4.0 + ControlNet Union + character LoRA (self-hosted).** The community's anime
standard, with the deepest LoRA/ControlNet ecosystem; deterministic seeds; ControlNet Union SDXL (Apache 2.0) gives
openpose/depth/lineart/anime-lineart; Illustrious v2.0 carries the creativeml-openrail-m tag, Animagine 4.0 OpenRAIL++-M
(commercial use stated). NoobAI and its merges are out (commercial use prohibited, including generated products).
Consistency comes from a character LoRA (Civitai on-site trainer from 500 Buzz, supports an "Illustrious" base; fal/Replicate
trainers ~$2 per FLUX run; RunPod 4090 community pod $0.34/h) plus pose/depth control and a fixed seed — the 2023-era recipe,
still the most *predictable* anime look, but weakest at "same room, same people, same positions" without manual control
maps. Verdict: keep as the style anchor and LoRA-dataset generator; not the primary editor.

**GPT Image 2.5 (OpenAI).** Top of the AA leaderboard, up to 16 input images, prompt-based masks, `moderation: low`,
arbitrary sizes to 3840×2160. Price per image is opaque for 2.5 (token counts vary per quality; earlier-model counts give
≈$0.03 medium / ≈$0.13 high at 1024², plus input tokens), no seed, and style drift between calls is the common user
complaint. Verdict: too expensive for 60+ shots per episode; useful at most for a hero sheet or thumbnail.

**Krea 3.** Honest API: seed, negative prompt, regional edit, up to 8 refs, $0.03 base — but each 1K reference adds $0.02,
so a 4-reference shot is ≈$0.11; style refs and LoRAs "coming soon". Verdict: watch; not for the pilot.

**Ideogram / Recraft / Stability / Midjourney / NovelAI.** Ideogram's character-reference surcharge ($0.10–0.20) and
non-anime bias; Recraft V4 has no prompt editing; Stability is single-reference; Midjourney has no official API; NovelAI
V5 has no public API and shipped without Vibe Transfer/Character Reference. None fits a phone-driven, automated pipeline.

---

## 4. Open-weight consistency tooling (B) — what is usable and what is not

| Tool | Licence | Fit |
|---|---|---|
| IP-Adapter (h94) | Apache 2.0 **V** | style/identity hint on SDXL anime bases; weak for exact identity **T** |
| IP-Adapter FaceID, InstantID, PuLID | code permissive; **InsightFace antelopev2 weights non-commercial** **T** | excluded for a monetised channel; also photo-trained, poor on anime faces **I** |
| ControlNet Union SDXL (xinsir) | Apache 2.0 **V** | openpose/depth/lineart/anime-lineart/canny; multi-condition; "compatible with other open-source SDXL models" **V** (Illustrious-specific CN not verified) |
| Reference-only (A1111/Comfy) | code | mild consistency, free |
| LoRA (character + style) | depends on base | the strongest identity lock reported across all guides **T**; Civitai trainer bases: SDXL, Pony, Illustrious, Flux.1/2 dev, Flux2 Klein 4B/9B Base, Qwen-Image, Z-Image **V** |
| Kontext-style in-context editing | FLUX.1 Kontext dev NC **T**; Qwen-Image-Edit-2511 Apache **V**; FLUX 3 Klein Kommunity **V** | the practical "edit the master frame" route |
| OmniGen2 / UNO / DreamO | Apache / CC BY-NC / Apache **V,T,V** | 2025 generation; quality behind 2026 editors **T** |

LoRA training cost and workflow (what the sources say): 15–30 images typical, 100+ for a character-true first epoch (Patreon
guide) **T**; ~1,500–2,000 steps **T**; fal fast FLUX LoRA ≈$2 per run, FLUX.2 trainer $0.008/step **V**; Replicate "fast,
under $2" (2025-05 changelog) **V** but the current trainer page lists 8×H200 at $0.0122/s **T** → verify before use; Civitai
on-site from 500 Buzz for SDXL/Illustrious **V** (Buzz→USD not verified); RunPod RTX 4090 community pod $0.34/h **V** →
a 30–60 min Illustrious LoRA ≈ $0.20–0.35 **I**.

VRAM: FLUX 3 Klein 8 GB INT8 (BFL) **V**; FLUX.2 klein 4B 13 GB **V**; Qwen-Image-Edit-2511 ≈16 GB FP8 **T**; OmniGen2 17 GB **V**;
Z-Image-Turbo ≤16 GB **V**; SDXL/Illustrious ≈8–12 GB **T**.

---

## 5. Hosted inference marketplaces (C) — prices read 2026-10-22

| Provider | Image prices read | GPU rates | LoRA | Notes |
|---|---|---|---|---|
| **fal.ai** **V** | FLUX.2 $0.012/MP; FLUX.2 Edit $0.012/MP in+out (1K edit with 512² input = $0.024); Seedream 4.5 $0.04; "Nano Banana" $0.0398; FLUX.1 dev + LoRA $0.035/MP; Qwen-Image-Edit-2511 $0.03/MP; FLUX 3 Klein Base "planned" $0.027 (1K) | H100 $4.50/h list ($2.49 "as low as"); B200/H200/RTX PRO 6000 listed | FLUX LoRA trainers ($2/run; $0.008/step FLUX.2) | billed per second; "Commercial use" tags; Seedream via partner agreement |
| **Replicate** **V** | flux-dev $0.025; flux-1.1-pro $0.04; flux-schnell $0.003; ideogram-v3-quality $0.09; recraft-v3 $0.04; Seedream 4 $0.03 **T**; qwen-image-edit-2511 ≈$0.04 **T** | T4 $0.81/h, A100 80GB $5.04/h, H100/H200 $5.49/h | fast-flux-trainer | cold start on custom models varies (not measured) |
| **Together** **V** | FLUX.2 pro $0.03, flex $0.03, dev $0.0154 per image; max $0.07/MP; Kontext pro $0.04/MP; Qwen Image 2.0 $0.04 / Pro $0.08; Seedream 4.0 $0.03/MP | — | — | no FLUX 3 image listing yet (FLUX 3 only in video table) |
| **RunPod** **V** (page updated 2026-10-08) | — | Serverless: RTX 4090 $1.10/h, A40/A6000 $1.22/h, L40S $1.75/h, A100 $2.72/h, H100 $4.79/h; flex vs active per-second split not on page (third-party: 4090 $0.00031/$0.00021 s) **T**; Pods secure/community: 4090 $0.89/$0.34, A40 $0.59/$0.35, A5000 $0.27/$0.16, L40S $1.09/$0.79, A100 $1.79/$1.19–1.39, H100 PCIe $2.89/$1.99 | own ComfyUI | per-second billing; cold start billed from worker start until handler ready; idle timeout default 5 s; $80/h default spend limit; the project's existing `cloud/runpod.py` already governs pods **V** |
| **Hugging Face Inference Providers** **V** | pass-through at provider prices, "no markup"; routes images to fal, Replicate, Together, etc. **T** | — | — | Free users: no credits; PRO $2/month credits |
| Fireworks | not verified | | | |

---

## 6. Practical consistency techniques reported by creators 2025–2026 (D)

Evidence quality is low: almost every source is a tool vendor's blog. Patterns that recur across them, with the little
primary evidence found:

1. **Canonical character sheet first, then multi-reference.** Generate 4–6 front views, pin one, build a turnaround
   + expression sheet, feed it as references for every shot (Nano Banana / Seedream / FLUX guides) **T**. The project's own
   D-55 (hero references + expression sheets, never redraw from scratch) is the same rule.
2. **Master frame + edit.** Lock one wide "establishing" frame per location; make every other shot of that scene an
   *edit* of it (angle/expression/prop change) rather than a fresh generation; mask or bounding-box only the region that
   changes (FLUX 3 bounding boxes, Krea `regional_edit`, Qwen-Edit) **T/V**. This is the strongest reported route to
   "same room, same positions".
3. **Re-anchoring against drift.** After ~10–20 frames, re-reference from an *updated* clean frame instead of the first
   one; regenerate only the drifted frame; composite a consistent face onto a new pose (storyboard guides) **T**.
4. **Seed locking** gives "mild" consistency and only exists where the API exposes seeds (FLUX, Krea, Seedream 3.x, all
   local models); Nano Banana and GPT Image do not **V**.
5. **LoRA** for a locked identity/style across a whole series ("near-perfect" per guides, no measurements) **T**; one
   documented Qwen-Edit multiple-angle LoRA tutorial (stable-diffusion-art.com, 2026) and the VNCCS Qwen-based
   character-sheet LoRA toolset on HF are the closest things to reproducible workflows **T**.
6. **Flat/white backgrounds for characters, composite later** (write-up of an "Every Explained"-style channel using
   Nano Banana Pro via OpenArt for 2D cartoon assets + ElevenLabs) **T** — the only explainer-channel workflow found.
7. **Per-episode QA against a character bible** (face, wardrobe, palette) before publish **T** — maps onto the project's
   `qa/visual_judge` + `sheet_review.py`.

Real results with numbers: none independent. A vendor "93% consistency" figure cites ZDNET without a link. Treat all of D
as hypotheses for the pilot to test, not as sourced rules (D-59).

---

## 7. Visual embeddings for reference search / dedup (E)

| Option | Licence / price | Notes |
|---|---|---|
| **Gemini Embedding 2** (`gemini-embedding-2`, multimodal) **V** | image $0.45/M tokens ≈ **$0.00012 per image** standard, $0.00006 batch; free tier "free of charge" (data used for product improvement on free tier) **V** | simplest hosted option; same vendor as Nano Banana |
| **SigLIP 2** (google, open) **V** | Apache 2.0 **V** | best open text↔image retrieval encoder; self-host on any small GPU/CPU |
| **DINOv2 / DINOv3** (Meta) | DINOv2 Apache 2.0 **T**; **DINOv3 "DINOv3 License"** (gated; terms not read) **V** | vision-only; best for near-duplicate and pose/layout similarity; use DINOv2 unless DINOv3 terms are checked |
| **CLIP ViT-L/14 on Replicate** (`andreasjansson/clip-features`) **V** | ≈$0.00022 per run, T4, ~1 s **V** | quick hosted CLIP |
| **Jina embeddings v5-omni / v4 / jina-clip-v2** **V** | token-priced; 600×600 image ≈ 363 tokens (v5-omni), 4,840 (v4), 16,000 (clip-v2); per-token price not shown **V** | hosted multimodal |
| Vertex multimodalembedding | ≈$0.0001/image **T** | not verified today |

Recommendation: SigLIP 2 (Apache) self-hosted next to the image pipeline for style/identity scoring, DINOv2 for dedup;
Gemini Embedding 2 as the zero-ops hosted fallback (≈$0.12 per 1,000 images).

---

## 8. Ranked recommendation for a small pilot (same 6 shots across candidates)

Ranking is by *fit to the brief* (anime-like look, multi-ref, editing, licence, price, phone-driven cloud), not by
leaderboard Elo.

1. **FLUX 3 Image Klein via BFL API** (fallback: self-host the FP8 weights on a RunPod 4090 community pod). Cheapest
   capable editor ($0.009/1K), 10 refs, bounding-box edits, open weights, Kommunity licence covers this creator's
   commercial outputs. Must prove it can hold a shonen look; test with and without a style LoRA later (licence question
   first).
2. **Seedream 4.5 via fal** ($0.04). The anime-reputation candidate. Read BytePlus/fal terms and the watermark default
   before the batch; test seed support.
3. **Qwen-Image-Edit-2511 via fal** ($0.03/MP, Apache 2.0) — as the *continuity editor* over the winner's master frames
   (1–3 inputs). If the creator wants a Google control, swap in **Nano Banana 2.1** ($0.0336 + refs) instead; its SynthID
   and no-seed posture are known and were already judged against.

Open-weight anime anchor (parallel, almost free): **Illustrious XL v2.0 or Animagine XL 4.0 + ControlNet Union** on a
RunPod 4090 community pod, to produce the hero's turnaround sheet and 20–40 LoRA training images in the chosen look; those
sheets then feed candidates 1–3 as references. NoobAI and merges are excluded (licence).

### The 6 test shots (identical prompts/references for every candidate)
1. Hero A turnaround sheet (front / ¾ / side / back) on flat background — identity source.
2. Hero A + Hero B in a named room (e.g. 1860s telegraph office), wide shot, A left, B right.
3. Same room, reverse angle, same positions, same lighting — **edit of shot 2**.
4. Hero A close-up, expression change (worried → grin) — **edit of shot 3**.
5. Era jump: Hero A in a Roman market, same style identity, different palette era.
6. On-screen prop text: a sign reading "WORLDS COLLIDE" legibly, in-style.

Scoring (free): SigLIP-2 cosine between each shot's hero crop and the sheet; DINOv2 similarity of shots 2↔3 for room
continuity; human 1–5 on "shonen look", legibility of text, refusal count, wall-clock per image, exact cost from the
response `cost` fields (BFL) or fal usage.

### Estimated pilot cost (my arithmetic from the verified prices above; 4 generations per shot incl. 2 edits = 24 images per candidate)
| Item | Basis | Estimate |
|---|---|---|
| FLUX 3 Klein (BFL) 24 × $0.009 (1K) | V | $0.22 |
| Seedream 4.5 (fal) 24 × $0.04 | V | $0.96 |
| Qwen-Image-Edit-2511 (fal) 24 × ≈1.5 MP × $0.03 | V + I | ≈$1.08 |
| (optional) Nano Banana 2.1: 24 × ($0.0336 + 4 refs × $0.0017) | V + I | ≈$0.97 |
| Illustrious/Animagine sheet + 40 LoRA images on RunPod 4090 community, ~1.5 h × $0.34 | V + I | ≈$0.51 (+ storage; stop the pod) |
| Embedding scoring (Gemini Embedding 2) ~150 images × $0.00012, or self-hosted SigLIP 2 | V | ≈$0.02 / $0 |
| **Total** | | **≈$3–4; with a 3× rerun margin ≤ $12.** Proposed ceiling for `config/spend_caps.json`: $15 (creator's call). |

Nothing above runs without the creator's provider choice (D-50) and the ledger entry (invariant 2).

---

## 9. Open uncertainties (ranked by how much they change the decision)

1. **Anime quality of FLUX 3 Klein / FLUX 3 / Qwen-Edit-2511** — no sample, benchmark or creator report exists; the
   pilot is the evidence.
2. **FLUX Kommunity License and LoRAs** — §2.b (Derivatives non-commercial) vs §2.a(ii) (commercial Outputs from
   Derivatives for Qualifying Users). Ask BFL before training a house-style LoRA on Klein Base for the channel; or train
   LoRAs on an Apache base (FLUX.2 klein 4B, Qwen-Image-Edit-2511, Illustrious/Animagine).
3. **Seedream official terms, watermark default, seed, reference limits** — BytePlus docs did not render; fal says 10
   refs/4 MP/$0.04/"partner agreement". Read before any paid batch.
4. **Seed on the FLUX 3 API** — not in the fields I could read; verify with one free/cheap call or the API reference.
5. **Illustrious licence lineage** — v2.0 tagged creativeml-openrail-m on HF; newer Onoma releases (3.x) not found; many
   Civitai merges inherit NoobAI's commercial ban. Check each checkpoint's licence file.
6. **GPT Image 2.5 real per-image cost** — OpenAI publishes no table for 2.5; only measure if ever used.
7. **Nano Banana filters for anime prompts** — reports of higher block rates on anime-style prompts are anecdotal (vendor
   page); SynthID is certain.
8. **Prices move monthly** — every number here carries its read date (2026-10-22); FLUX 3 Klein is seven days old,
   fal's Klein price is "planned".
9. **D-techniques have no independent measurements** — treat §6 as hypotheses (D-59 REVIEW), to be promoted to rules only
   after the pilot's measured results.

---

## 10. Sources (URL — what was read — date read 2026-10-22 unless noted; page dates where shown)

Official / primary (V):
- https://ai.google.dev/gemini-api/docs/pricing — Nano Banana 2.1 / 2 / 2 Lite / Pro per-image and token prices; Gemini Embedding 2 prices; "Last updated 2026-10-19".
- https://ai.google.dev/gemini-api/docs/image-generation — reference limits per model (2.1: 10 objects + 4 characters, "mix up to 14"; Pro: 6+5+3 style), resolutions, SynthID, Imagen "legacy (shut down)".
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/nano-banana-2-1 — "Release date: October 6, 2026", GA; seed/temperature/topP unsupported (API error); max 14 images per prompt; 1,120 tokens per input image; C2PA.
- https://developers.openai.com/api/docs/pricing — gpt-image-2.5-sunburst/flare, gpt-image-2, 1.5, 1-mini, 1 token prices (standard/batch).
- https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst — snapshot 2026-09-08, quality tiers, inpainting, rate limits.
- https://developers.openai.com/api/docs/guides/image-generation — moderation auto/low, prompt-based masks, sizes, earlier-model token table (272/1056/4160).
- https://developers.openai.com/api/docs/api-reference/images/createEdit — "up to 16 images", size rules (multiples of 16, ≤3:1, max 3840×2160), input_fidelity.
- https://bfl.ai/blog/flux-3-image-klein — release 2026-10-15, 5.6B, 10 refs, bounding boxes, 4K, Kommunity License (<$5M), "$0.009 per 1K image", VRAM, HF links, internal Elo deltas.
- https://docs.bfl.ai/release-notes — FLUX 3 Image (2026-10-01) prices $0.041/$0.048/$0.100/$0.607; FLUX 3 Image Klein (2026-10-15) prices $0.008–$0.036; open weights under Kommunity License.
- https://docs.bfl.ml/quick_start/pricing.md and https://docs.eu.bfl.ai/quick_start/pricing — 1 credit = $0.01; Klein table; FLUX.2 [dev] "local only"; other cells did not render.
- https://docs.bfl.ml/flux_3/flux3_image_overview.md, https://docs.bfl.ml/flux_3/flux3_image_klein.md, https://docs.bfl.ml/guides/prompting_unified_technical.md, https://docs.bfl.ml/api-reference/utility/generate-an-image-with-flux-3 — 10 refs, bounding boxes, grounding default on, resolution tiers, 15 aspect ratios, safety_tolerance 0–7 default 2, response `cost`/`input_mp`/`output_mp`; prompt upsampler warning; Distilled vs Base variants.
- https://bfl.ai/pricing — calculator showed "$0.048 / image" default (matches FLUX 3 Image 1K); model list incl. FLUX 3 Image Klein.
- https://huggingface.co/black-forest-labs/flux-3-image-klein and .../blob/main/LICENSE.md — Kommunity License v1.0 text: Qualifying User <US$5,000,000; §2.a(ii) commercial Outputs; §2.b Derivatives non-commercial; §2.d no ownership of Outputs; VRAM on B200; Diffusers ModularPipeline.
- https://huggingface.co/black-forest-labs/FLUX.2-dev and .../blob/main/LICENSE.md — FLUX Non-Commercial License clauses (§1(c), §2(a)(b)(d), §4(a)(i)); 32B.
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B — Apache 2.0, 13 GB VRAM, 9B under non-commercial licence.
- https://huggingface.co/Qwen/Qwen-Image-Edit-2511 — Apache 2.0, 20B, multi-image example, character consistency, built-in LoRAs.
- https://huggingface.co/Qwen/Qwen-Image-2.1 and .../blob/main/LICENSE — Qwen Research License Agreement: non-commercial ("research or evaluation purposes only"), commercial licence via model-business@notice.qwencloud.com; 7B; up to 10 refs; RGBA; masks.
- https://github.com/Tongyi-MAI/Z-Image — Apache 2.0; Turbo 2025-11-26, Z-Image 2026-01-27; Edit/Omni-Base "to be released"; ≤16 GB.
- https://huggingface.co/HiDream-ai/HiDream-I1-Full — MIT transformer; 17B; E1 (2025-04-28) / E1.1 (2025-07-16).
- https://huggingface.co/Alpha-VLLM/Lumina-Image-2.0 — Apache 2.0; 2B.
- https://huggingface.co/OmniGen2/OmniGen2 — Apache 2.0; 4B; ~17 GB; 2025-06-16.
- https://huggingface.co/ByteDance/DreamO — licence tag apache-2.0; paper 2025-04-23.
- https://huggingface.co/OnomaAIResearch/Illustrious-XL-v2.0 — licence tag creativeml-openrail-m.
- https://huggingface.co/cagliostrolab/animagine-xl-4.0 — CreativeML Open RAIL++-M, commercial use permitted; 2025-01-24; 8.4M images; settings.
- https://huggingface.co/Laxhar/noobai-XL-1.1/raw/main/README.md — fair-ai-public-license-1.0-sd + added Section II: commercialisation prohibited incl. "model-generated products".
- https://huggingface.co/h94/IP-Adapter — Apache 2.0.
- https://huggingface.co/xinsir/controlnet-union-sdxl-1.0 — Apache 2.0; openpose/depth/lineart/anime-lineart/canny/…; SDXL finetune compatibility.
- https://huggingface.co/google/siglip2-base-patch16-224 — Apache 2.0; paper 2025-02-20.
- https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m — "DINOv3 License", gated; paper 2025-08-13.
- https://fal.ai/pricing — FLUX.2 $0.012/MP; FLUX.2 Edit; Seedream 4.5 $0.04; Nano Banana $0.0398; FLUX.1 dev LoRA $0.035/MP; H100 $4.50/h.
- https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit — $0.04, up to 10 images, 4 MP, "Commercial use via fal Partner agreement".
- https://fal.ai/models/fal-ai/qwen-image-edit-2511 — $0.03/MP, "Commercial use" tag.
- https://fal.ai/models/fal-ai/flux-2/edit — $0.012/MP in+out, example $0.024.
- https://fal.ai/models/blackforestlabs/flux-3/klein/base/text-to-image — "planned" $0.024–$0.108 by resolution; seed in sample output.
- https://replicate.com/pricing — flux-dev $0.025, flux-1.1-pro $0.04, ideogram-v3-quality $0.09, recraft-v3 $0.04; T4/A100/H100/H200 per-second rates.
- https://replicate.com/qwen/qwen-image-edit-2511 — "works best with 1 to 3 input images".
- https://replicate.com/andreasjansson/clip-features — ≈$0.00022/run on T4.
- https://replicate.com/changelog/2025-05-23-faster-flux-trainer — "under 2 minutes, under $2" (2025-05-23).
- https://www.together.ai/pricing — FLUX.2 pro/flex/dev, max, Kontext, Qwen Image 2.0, Seedream prices.
- https://www.runpod.io/pricing (updated 2026-10-08) and https://docs.runpod.io/serverless/pricing — serverless hourly, pod secure/community prices, billing rules, idle timeout, $80/h default limit.
- https://huggingface.co/docs/inference-providers/pricing — no markup pass-through; PRO $2 credits; free users none.
- https://www.recraft.ai/docs/api-reference/pricing and https://www.recraft.ai/docs/recraft-models/recraft-V4 — V4/V4.1/V4 Styles prices; V4 released Feb 2026; prompt-based editing "not yet supported".
- https://www.krea.ai/docs/developers/krea-3/overview and https://www.krea.ai/features/api — 8 refs, regional_edit, seed, prices incl. per-reference charges, style refs/LoRAs "coming soon".
- https://docs.stability.ai/pricing — credits per service; 1 credit = $0.01.
- https://ideogram.ai/pricing/?pricing_tab=api — table did not render ("Loading current prices"); 1¢/credit.
- https://artificialanalysis.ai/image/leaderboard/text-to-image — AA-Image-T2I v2.1 top 15 with Elo and release months.
- https://education.civitai.com/using-civitai-the-on-site-lora-trainer/ — from 500 Buzz for SD1.5/SDXL; base model list incl. Illustrious, Flux2 Klein 4B/9B Base, Qwen-Image, Z-Image; log entry 2026-04-01.

Third-party / community (T) — used only where marked:
- https://venturebeat.com/technology/black-forest-labs-opens-flux-3-image-klein-weights-with-free-commercial-use-limited-to-smaller-businesses ; https://the-decoder.com/black-forest-labs-open-weights-image-model-flux-3-image-klein-runs-on-consumer-gpus-with-just-8-gb-of-vram/ (2026-10).
- https://www.kingy.ai/ai-launch-tracker/flux-3-image-2026-10-01/ — FLUX 3 Image launch profile (vendor-attributed prices).
- https://openrouter.ai/black-forest-labs/flux-3-image — input_references up to 10.
- https://help.apiyi.com/en/nano-banana-pro-seed-parameter-not-supported-alternatives-en.html — NB Pro no seed.
- https://www.androidauthority.com/google-gemini-blocks-disney-generation-3639914 — Disney blocks.
- https://influencerstudio.com/models/compare/nano-banana-pro-vs-seedream-4-5/anime ; https://invideo.io/faq/seedream-45-vs-nano-banana-pro-which-ai-model-is-better/ ; https://picsart.com/blog/nano-banana-vs-seedream-comparison/ — vendor anime comparisons.
- https://www.therundown.ai/tools/seedream-5-0-pro ; https://kie.ai/blog/what-is-seedream-5 ; https://docs.gmicloud.ai/model-quickstarts/image/seedream-5-0-pro — Seedream 5.0 refs/prices/watermark label.
- https://www.alibabacloud.com/help/en/model-studio/qwen-image-2-0 (via search snippet) — $0.035/image Singapore.
- https://aiweekly.co/alerts/alibaba-ships-qwen-image-21-7b-dit-with-native-2048x2048-and-rgba-drops-apache ; https://www.eesel.ai/blog/qwen-image-2-1 — Qwen-Image-2.1 2026-09-20 coverage.
- https://insiderllm.com/guides/best-anime-stylized-checkpoints-local-image-generation/ ; https://localaimaster.com/blog/best-local-anime-image-model ; https://note.com/ai_image_journey/n/n4982b466f663 — anime checkpoint rankings/licence discussion; https://huggingface.co/OnomaAIResearch/Illustrious-XL-v2.0/discussions/1 — Onoma relicensing note.
- https://www.insightface.ai/ ; https://huggingface.co/InstantX/InstantID/discussions/2 — InsightFace non-commercial weights.
- https://huggingface.co/spaces/altarcomputing/UNO-FLUX/blame/main/README.md — UNO weights CC BY-NC 4.0.
- https://stable-diffusion-art.com/qwen-image-edit-multiple-angle-lora/ ; https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511 ; https://blog.comfy.org/p/qwen-image-edit-2511-and-qwen-image — Qwen-Edit workflows.
- https://flowith.io/blog/nano-banana-consistent-characters-storyboard/ ; https://sider.ai/blog/ai-image/nano-banana-pro-storyboard-creation-guide-for-video ; https://rangy.ai/blog/ai-character-consistency/ ; https://higgsfield.ai/blog/keep-characters-consistent-ai-animated-series ; https://alici.ai/formulas/media/aicenturyclips/... (Every-Explained-style workflow) — creator technique guides (vendor).
- https://unifically.com/blogs/midjourney-api ; https://javisreview.com/review/midjourney-review-2026/ — no official Midjourney API (Oct 2026).
- https://novelai.net/v5 (via search) ; https://github.com/HanaokaYuzu/NovelAI-API — V5 reference features absent at launch; wrapper notes image API deprecation 2024-03-21.
- https://www.spheron.network/blog/multimodal-embedding-models-gpu-cloud-siglip2-jinaclip-cohere/ ; https://www.edenai.co/post/best-image-embeddings — embedding cost comparisons.
- https://developer.puter.com/tutorials/ideogram-api-pricing/ ; https://www.wireflow.ai/blog/ideogram-api-pricing — Ideogram per-image and character-reference rates.
- https://tech-insider.org/train-custom-ai-image-lora-2026/ ; https://civitai.com/articles/21257/... ; https://www.patreon.com/Haxivus/posts/train-character-137625934 — LoRA dataset/step guidance.
