# Market research — seed-evidence register and limitations

Canonical home of: the seed-evidence register (SE-xx), the targeted verification log (V-xx), the reference-library
statement, the topic/format comparison and the vidIQ ledger. Other documents cite these IDs; they do not copy them.
This is **not** an instruction to repeat broad research (directive section 4): new entries are added only when one
specific fact would change a decision.

Inputs: "Faceless YouTube Channel Analysis" (Georgian, 25 secondary sources) = **R**; "youtube_top100_channel_technique_matrix"
(vidIQ-index rows plus a small sample of video titles/views; sheets: matrix, method legend, pattern assessment) = **M**.
Neither is a reproducible census: R has no channel-level table with URLs and consistent timestamps, and M's own method
sheet says it is "not an independently verified global ranking" and that thumbnails, SEO traffic, retention and private
analytics are unconfirmed. Statements are labelled: **[OBS]** observed in a source, **[MEAS]** measured by us, **[VER]**
verified against an official source on the stated date, **[INF]** inference, **[REC]** recommendation, **[HYP]** hypothesis,
**[UNK]** unknown.

## B.1 Seed-evidence register (from the supplied report "R" and matrix "M")

Source quality: R = secondary blogs/social posts, no channel-level table with URLs or timestamps; M = vidIQ index rows + a small
sample of video titles/views pulled earlier (method legend: "OBS" seen in sample, "inferred" = from name only, blank = no evidence).

| ID | Claim (source) | Quality | Relevance to 2D explainer | Limitation | Treatment | Decision affected |
|---|---|---|---|---|---|---|
| SE-01 | 100 fast-growing channels created Apr–Oct 2026; 7 excluded (B), 93 kept (R §1, M) | Medium (vidIQ index, single pull) | Context only | Not a census; growth ≠ cause | Context | — |
| SE-02 | US-tagged channels: ~701 views/sub vs IN 166, ID 132 (R §2) | Low (aggregate of 20 channels, mixed formats) | Language/market | Confounded by IP-animation channels | Test as hypothesis: English, global/US | D-01 language |
| SE-03 | Happening Zukan 1,530 subs / 10.3M views (R §2, M row 100) | Low ("ownership/content/history unverified" per M) | Small facts channel can travel | One outlier, no per-video data | Reference only; inspect if a design question needs it | — |
| SE-04 | Niche clusters: 43 general auto-Shorts, 15 facts/edu, 8 gaming, 8 meme, 6 Demon-Hunter IP, 4 kids, 3 recaps, 3 Countryballs, 3 Mario IP (R §3) | Medium-low | Shows facts/edu is a real cluster | Labels inferred from names for most rows | Adopt as context | D-01 |
| SE-05 | Serialized recurring characters build familiarity / binge sessions (R §3.1) | Low (mechanism asserted, examples are IP-dependent) | High | Causality unproven | Test: recurring mascot + series naming | D-04 |
| SE-06 | IP-dependent 3D (Mario, K-pop Demon Hunters) gets billions (R §3.1–3.2, M) | Medium (aggregates observed) | Negative: rights/YPP risk | IP | **Reject** as identity (directive §3) | D-04 |
| SE-07 | Simple 2D visual grammar (Countryballs) cuts production cost (R §3.3) | Low-medium | High (cost) | Political topics = risk | Adopt principle (simple shape grammar), reject geopolitics | D-04, D-02 |
| SE-08 | Facts/edu depend on script quality, narration pace, accuracy (R §3.3) | Low (asserted) | High | Not measured | Adopt as principle | D-12, QA |
| SE-09 | "Explore and Exploit" Shorts distribution model (R §4) | Very low (blog sources) | — | Not official | **Reject as fact**; no rule built on it | — |
| SE-10 | Swipe-away in first 1–3 s is "the most critical signal" (R §4.1) | Low | Shorts hooks | YouTube does show "viewed vs swiped away" metric [VER, Shorts analytics help] but no threshold | Test: first-frame premise; measure viewed-vs-swiped | D-07 hooks |
| SE-11 | 70 % completion / 50 % replay thresholds (R §4.2) | Very low | — | Invented thresholds | **Reject** | — |
| SE-12 | Perfect loop endings boost replays (R §4.2) | Low | Shorts | Can weaken payoff | Optional per Short, never forced | D-05 |
| SE-13 | Outcome-first titles, 3–5 word thumbnail text, high contrast (R §4.3) | Low-medium (common practice) | High | No CTR data | Adopt as starting template, test | TITLE_THUMBNAIL |
| SE-14 | 48-hour 2–3 thumbnail A/B as SOP (R §4.3) | Low | Packaging | Only valid with YouTube's own Test & Compare where available | Use only if feature verified on the channel | Analytics |
| SE-15 | 5 finished videos in 2 h; 24 min/video (R §5) | Very low | — | Marketing claim | **Reject**; use own time log | Cost model |
| SE-16 | ElevenLabs ~$22/mo, "dominates" TTS, voice quality correlates with retention (R §5.2) | Low (price undated) | TTS choice | Price/claim unverified | Test via listening panel; no subscription by default | D-12 |
| SE-17 | Shorts RPM $0.05–0.15, music carve-out math, 45 % share (R §6.2) | Low (secondary, undated) | Business model | Not needed for any current decision | Not relevant now; no RPM numbers in plans | — |
| SE-18 | YPP thresholds 1,000 subs + 4,000 h or 10M Shorts views/90 d (R §6.1) | Medium (matches official pattern; unverified today) | Later | — | Verify when monetisation is near | — |
| SE-19 | AI/Kling/3D "fully solves" visual originality (R §6.1) | Very low | Policy | Contradicts official framing (value + original insight) | **Reject** | D-15 |
| SE-20 | Scene cut every 2–3 s (R §7.20) | Very low | Animation | Universal rule claim | **Reject** as rule; measure own retention | Animation params |
| SE-21 | Payoff withheld to the last seconds (R §7.18) | Low | Script | Risk of baiting | Reject as rule; "answer early, deepen after" for long-form | SCRIPTING |
| SE-22 | Channel factory / cloning (R §7.21) | Low | — | Inauthentic-content risk | **Reject** | — |
| SE-23 | Repeat winners: Facto Explano (15.0M, 12.2M, 8.7M, 7.3M story Shorts), Lihat Lah (16.9M, 12.7M…), Tresdatos numbered facts (18.7M, 6.3M, 5.7M; wide variance) (M rows 17, 19, 20) | Medium (sampled views) | High | Small sample; formats inferred | Adopt as **direction to test**: short story-led facts | D-01, D-05 |
| SE-24 | Ranking compilations (Balbi Lindo) repeatable but rights/originality risk (M sheet 3) | Medium | Format | Third-party clips | Rankings only with original material | D-03 |
| SE-25 | Puzzle/sequence Shorts (Junao) — some 1M+, many low (M) | Medium | Shorts experiment idea | No retention | Optional Short format later | — |
| SE-26 | High upload frequency ≠ success; Double Trouble not faceless (M sheet 3) | Medium | Cadence | — | Adopt: cadence from own capacity | D-06 |
| SE-27 | Data anomalies: FactMint AI 827K subs/105.8K views; Antra Movies 1.29M subs/17,447 views; Bobby Viral 1 video (M) | — | Data quality | Index errors | Flag: do not cite these rows | — |
| SE-28 | Matrix gap list: no full video lists, real thumbnails, traffic sources, retention, ownership (M sheet 3) | — | All | — | Adopt as the register's main limitation | All |

## B.2 Targeted verification log (only facts that change a decision)

| ID | Question | Result | Source (accessed 2026-10-15) | Decision |
|---|---|---|---|---|
| V-01 | Reused vs inauthentic content | Inauthentic (renamed from "repetitious" on 2025-07-15) targets templated/mass-produced, interchangeable, low-value videos; series with distinct storylines and the same intro/outro are allowed; AI fine when the result shows creative vision and value | support.google.com/youtube/answer/1311392 | D-15, QA editorial gate |
| V-02 | Altered/synthetic disclosure | Required for *realistic* content (real person, real event/place, realistic scene, AI music as main focus); "non-realistic content made with AI" and AI help with outline/script are not required | support.google.com/youtube/answer/14328491 (+15447836 label page) | D-16: no blanket disclosure; per-video checklist |
| V-03 | Made for kids & cartoons | Animated characters are a listed factor, but "animated content that appeals to everyone" is a general-audience example; general-audience content → "not made for kids" | support.google.com/youtube/answer/9528076 | D-17: adult/teen tone, topics, language; never kid-targeted packaging |
| V-04 | Remotion licence | Free for individuals and for-profit orgs ≤ 3 employees; Company Licence for 4+; licence "will slightly change" in Remotion 5.0 | remotion.dev/license, GitHub LICENSE.md (search 2026-10-15) | D-10; re-check at install and at any 5.0 upgrade |
| V-05 | Motion Canvas headless rendering | No official headless CLI confirmed; Revideo (fork) has headless API but current maintenance unconfirmed | search 2026-10-15 | D-10 (rejects both as primary) |
| V-06 | vidIQ account | Balance 395 credits (125 renewable + 270 add-on), resets 2026-11-08; **0 spent** (balance call costs 0) | vidIQ MCP `vidiq_balance` | Ledger, B.5 |
| V-07 | YouTube fair use guidance | four factors; credit and "no infringement intended" do not make a use fair; "entertainment only" does not help; adding new expression or meaning is more likely fair; factual more likely than fictional; the "heart" of a work; market harm; courts decide | support.google.com/youtube/answer/9783148 (accessed 2026-10-16) | D-26, RIGHTS_AND_FAIR_USE |
| V-08 | YouTube copyright strikes | a strike follows a valid removal request, not a Content ID claim; disputing a claim without a valid reason can lead to a removal request and a strike; 3 strikes = termination; expiry 90 days with Copyright School; retraction or counter notification | support.google.com/youtube/answer/2814000 (accessed 2026-10-16) | RR-13 |
| V-09 | YouTube trademark policy | prohibits use "likely to cause confusion" about the source; YouTube forwards complaints and removes clear cases; titles for commentary are not addressed on the page | support.google.com/youtube/answer/6154218 (accessed 2026-10-16) | RR-08, RR-09 |
| V-10 | US Copyright Office on fair use | 17 U.S.C. 107 four factors; transformative = "add something new, with a further purpose or different character", should not substitute; no safe percentage | copyright.gov/fair-use (accessed 2026-10-16) | RR-01, RR-05 |
| V-11 | Andy Warhol Foundation v. Goldsmith (US Supreme Court, 18 May 2023, 7-2) | same or highly similar purpose + commercial use weighs against fair use; new meaning is only one consideration | case summaries found by search 2026-10-16 (full opinion not read) | RR-01, RR-06 |
| V-12 | Warner Bros. v. RDR Books (S.D.N.Y. 2008, Harry Potter Lexicon) | reference work partly transformative but took more than its purpose needed and its plot summaries were substantially similar: not fair use; the judge said such reference works "should be encouraged" | US Copyright Office fair use index summary (copyright.gov/fair-use/summaries/warnerbros-rdrbooks-sdny2008.pdf), search 2026-10-16 | RR-04, RR-05 |
| V-13 | Altered/synthetic disclosure, re-checked for the episode rulebook (D-45) | unchanged from V-02: realistic content needs the label (real person made to say/do what they did not, altered real footage, realistic scene that did not occur, AI music as the main focus); fantasy, fully animated content, minor aesthetic edits and AI help with script, titles, thumbnails or captions do not; the label is set under "AI use" in Studio's upload flow | support.google.com/youtube/answer/14328491 (accessed 2026-10-17) | ES-08, `standards/policy_baseline.json` B-01 |
| V-14 | YPP inauthentic and reused content, re-checked | renamed 2025-07-15; template-made or interchangeable videos (same situation and outcome repeated, slideshows or scrolling text with little narrative) are ineligible; reused content needs a meaningful difference; readings of material the creator did not write are ineligible; the policy applies even with permission and is separate from copyright | support.google.com/youtube/answer/1311392 (accessed 2026-10-17) | ES-13, ES-14, B-02 |
| V-15 | Privacy removal of synthetic likeness | a uniquely identifiable person (or a representative) can ask to remove a realistic altered or synthetic version of their likeness; factors: disclosure, identifiability, realism, parody/satire/public interest, a public figure in sensitive behaviour | support.google.com/youtube/answer/2801895 (accessed 2026-10-17) | ES-08, B-03 |
| V-16 | Impersonation policy | misleading impersonation not allowed; an AI likeness or voice implying a person owns or authorises the content, or a fake speech passed off as real, are listed violations; disclosure is "not a free pass"; parody and satire are weighed | support.google.com/youtube/answer/2801947 (accessed 2026-10-17) | ES-08, B-04 |
| V-17 | US fair use page, re-checked | four factors case by case; transformative = adds something new and does not substitute; no safe amount; the "heart" can fail; page updated July 2026 | copyright.gov/fair-use (accessed 2026-10-17) | ES-10, B-05 |
| V-18 | US copyright duration | life + 70 for works created from 1978; anonymous, pseudonymous, for-hire 95 years from publication or 120 from creation; pre-1978 works depend on several factors | copyright.gov/help/faq/faq-duration.html (accessed 2026-10-17) | ES-09 (no universal age rule), B-06 |
| V-19 | UK copyright exceptions | fair dealing for criticism, review, quotation (sufficient acknowledgement unless impractical) and caricature, parody, pastiche (limited amounts, fair dealing only); "fact, degree and impression" | gov.uk/guidance/exceptions-to-copyright (accessed 2026-10-17) | ES-10, B-07 |
| V-20 | Georgia copyright law | Law No. 2112-IIS, consolidated to 15 Dec 2023: life + 70 (Art. 31); quotation for scientific, research, polemical, critical or informational purposes, to the extent justified, naming author and source (Art. 23); no parody exception found in the 2017 English text. **Partly verified**: the 2023 text was read in Georgian through a machine summary | wipo.int/wipolex/en/legislation/details/22704 and /18224 (accessed 2026-10-17) | ES-15, B-08 |
| V-21 | EU DSM Directive Art. 17(7) | the EUR-Lex page returned no text: **not verified** | eur-lex.europa.eu/eli/dir/2019/790/oj (accessed 2026-10-17) | B-09 (verified: false) |
| V-22 | ElevenLabs use policy | no impersonating a living person's voice, identity or likeness without explicit informed consent; deceased people where harm or post-mortem rights; no false endorsement or affiliation; disclose AI where law requires or where not doing so would materially mislead; keep watermarks | elevenlabs.io/use-policy (accessed 2026-10-17) | ES-08, PV-10, B-10 |
| V-23 | Google generative AI prohibited use policy | no IP or privacy violations; no impersonating a person (living or dead) without explicit disclosure in order to deceive; no claiming AI output is solely human-made in order to deceive | policies.google.com/terms/generative-ai/use-policy (accessed 2026-10-17) | ES-08, B-11 |
| V-24 | Claude Code subagent files | frontmatter `name`, `description` required; `tools`, `disallowedTools`, `model`, `skills` (preloaded), `memory`, `effort` and others optional; unknown fields are ignored silently; a subagent may spawn subagents unless `Agent` is left out of `tools` | code.claude.com/docs/en/sub-agents (accessed 2026-10-17) | `.claude/agents/episode-standards-director.md` |
| V-25 | YouTube Shorts length | square or vertical videos up to 3 minutes count as Shorts (standard channels from 15 Oct 2024) | support.google.com/youtube/answer/15424877 (accessed 2026-10-17) | P-11, Q-T12 |
| V-26 | YouTube recommended upload settings | MP4, no edit lists, moov atom at the front; AAC-LC (or Opus) 48 kHz, 384 kbps stereo; H.264 High, progressive, CABAC; frame rate as recorded; 1080p SDR 8 Mbps at 24-30 fps, 1440p 16 Mbps; BT.709; **no loudness target on the page** | support.google.com/youtube/answer/1722171 (accessed 2026-10-17) | Q-T19, P-90 label |
| V-27 | YouTube Data API disclosure field | `status.containsSyntheticMedia` (boolean) lets the owner disclose realistic altered or synthetic content on insert or update | developers.google.com/youtube/v3/docs/videos (accessed 2026-10-17) | ES-08 (recorded, never set: no upload code) |
| V-28 | ElevenLabs terms and Music Terms | paid plans may use output commercially, Free is non-commercial; the user keeps rights in Output, which may not be unique; Music Terms (updated 9 Oct 2026): media rights by plan, film/TV/radio/studio games only on Enterprise Music, attribution only on Free, streaming distribution not on Free/Starter, follow platform AI-disclosure rules; nothing on YouTube monetisation or Content ID | elevenlabs.io/terms-of-use, elevenlabs.io/music-terms (accessed 2026-10-17) | AUDIO_SYSTEM, rulebook music risks |
| V-29 | ElevenLabs connector schemas | `eleven_v4`: voice, `language_code`; `eleven_music_v2_5`: `duration_seconds` 3-600, `instrumental`, `lyrics_type`, `lyrics`; `eleven_text_to_sound_v2`: `duration_seconds` 0.5-30, `prompt_influence`, `loop`; `generations_count` defaults to 4 | ElevenLabs MCP `creative_get_model_schema` and tool schemas (read 2026-10-17) | EL-10, hook |
| V-30 | Gemini image prices, batch tier | per picture, batch: Nano Banana 2.1 1K $0.0168, 2K $0.0252, 4K $0.0567; Flash 3.1 Image 2K $0.050; Flash-Lite 1K $0.0168; Gemini 3 Pro Image 1K/2K $0.067, 4K $0.12 (half the standard tier); page updated 2026-10-16 | ai.google.dev/gemini-api/docs/pricing (accessed 2026-10-17) | D-46, `imagegen/routing.py` |
| V-31 | Claude Code hooks | PreToolUse hooks match MCP tools by regex (`mcp__<server>__.*`), receive `tool_name`/`tool_input` on stdin, and deny with `hookSpecificOutput.permissionDecision: "deny"` (or exit 2) | code.claude.com/docs/en/hooks (accessed 2026-10-17) | `.claude/settings.json`, `standards/hook.py` |
| V-32 | Loudness for streaming (secondary only) | AES TD1008 reportedly recommends a distribution loudness of about -16 LUFS for music and -18 for speech; YouTube's playback normalisation to about -14 LUFS is reported by third parties, not by YouTube; neither was read in the original | productionadvice.co.uk/td1008, productionadvice.co.uk/youtube-loudness (accessed 2026-10-17) | P-90 stays a house target, labelled as such |
| V-33 | Rockstar/Take-Two fan-content policy | non-commercial fan use tolerated, machinima welcomed, takedown at any time; film/TV/streaming/ads outside the policy, licence requests to Take-Two; **not read first-hand** (page 503, summary via search) | support.rockstargames.com/articles/200153756 (accessed 2026-10-17, partial) | B-14 (verified: false), Syndicate Wars RK-02 |
| V-34 | YouTube violent criminal organizations policy | praise/promotion/aid, recruitment and glorifying insignia not allowed; EDSA exceptions need context inside the video; no fiction exception stated | support.google.com/youtube/answer/9229472 (accessed 2026-10-17) | B-15 |
| V-35 | YouTube advertiser-friendly guidelines | violence/crime: artistic or documentary context helps, glorification earns nothing, graphic game violence in thumbnail or first 7 s limits ads | support.google.com/youtube/answer/6162278 (accessed 2026-10-17; page shows no update date) | B-16 |
| V-36 | California post-mortem publicity | Civ. Code 3344.1: 70 years after death, commercial use of name, voice, likeness; transferable; domicile limit per one court; **statute page not read**, secondary summaries only | leginfo.legislature.ca.gov (accessed 2026-10-17, partial) | B-17 (verified: false) |
| V-37 | GTA VI official facts | Rockstar page: 'Coming November 19, 2026', PS5 and Xbox Series X\|S, 'Vice City, USA', state of Leonida, Jason and Lucia; no in-game social app, stock exchange or year named; not released at the check date | rockstargames.com/VI (accessed 2026-10-17) | B-18 |
| V-38 | US doctrine behind RR-14..RR-16 and ES-19 (secondary: a model-written research report, 2026-10-17; case names and citations match the primary record, the full texts are not yet read) | nominative fair use: New Kids on the Block v. News America, 971 F.2d 302 (9th Cir. 1992), three prongs; parody is strongly transformative, Campbell v. Acuff-Rose (1994); commercial use with the same purpose as the original is weak, Andy Warhol Foundation v. Goldsmith, 598 U.S. 508 (2023); a parody mark used as a source identifier on a product gets ordinary infringement analysis, Jack Daniel's v. VIP Products, 599 U.S. 140 (2023), expressive works stay protected | secondary report only | verified: false until the opinions are read | 2026-10-17 |

Still to verify at implementation (each blocks only its own step): Kokoro voice licence (already Apache-2.0 in repo, re-check),
SFX library licence per pack, font licences (Fredoka, Inter: OFL), Gemini current image price (repo `imagegen.PRICES` dated
2026-10-08), chapter rules and thumbnail size limits (YouTube Help), Claude Code `.claude/rules` path-scoping and hook syntax for
the installed version.

## B.3 Reference library
Nothing was watched, listened to or frame-inspected in this session. The only video-level observations are the matrix's sampled
titles/views/durations [OBS]. "Everything Professor" was **not** inspected. Phase 2 may add ≤ 5 targeted references, only where a
specific design choice needs one (e.g. caption density in a 2D explainer), each recorded with URL, title, date, observation date,
duration, views and inspection limits.

## B.4 Topic/format comparison (anchored ratings)

Anchors: **H** = clear evidence or clear advantage for this creator; **M** = mixed/plausible; **L** = weak evidence or clear
disadvantage. Not scores; read the row.

| Candidate | Demand evidence (conf.) | Feasibility in 2D/solo | Editorial risk | Evergreen | Source availability | Visual/humour potential | Research burden | Asset reuse | Shorts extraction | Topic supply | Leading counterargument | Cheapest experiment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Everyday mechanisms + incentives + origins (chosen)** | M (facts/edu cluster, SE-04/23; low conf.) | H | L–M | H | H (papers, standards, company docs) | H (cutaways, visual metaphors) | M | H (kitchen, shop, street, factory sets) | H | H | Crowded "how it works" space | Prototype + 3 long-forms, 9 Shorts |
| Personal finance / money traps | M (no sample evidence) | H | **H** (advice, regulation, outdated numbers) | M | M | M | H | M | H | H | Advice liability, fast-changing figures | Fallback trigger only |
| Economics / business models | M | H | M | H | M | H | M–H | M | M | M | Can feel abstract/lecture | Folded into P2 |
| History / documented revelations | M | M (period settings = more assets) | M (contested readings) | H | M | M | H | L–M | M | H | Asset cost per era | Folded into P3, light |
| Political systems / geopolitics (Countryballs-like) | M (SE-07) | H | **H** (controversy, bias claims) | L | M | H | H | M | H | M | Brand risk, derivative style | Rejected |
| Counterintuitive facts / myths | M (SE-23) | H | M (myths are often half-true) | H | M | H | M | M | **H** | H | "Fact listicle" sameness | Shorts format within P1–P3 |
| Human behaviour / psychology | M | H | **H** (replication crisis, health-adjacent) | M | L–M | H | H | M | H | H | Weak science invites errors | Rejected for launch |

## B.5 vidIQ ledger
Cap 200 credits (ceiling). Spent: **0**. Planned: **0** for planning. Optional in Phase 9 only: keyword/title checks on the first
3 topics *if* a specific question (e.g. which of two phrasings people search) would change the title; each call's cost read from
the tool description first and logged in `docs/COST_AND_TIME_MODEL.md` ledger before calling. Stop when the question is answered.

## B.7 vidIQ niche research, 2026-10-15 (60 credits; the creator asked for real data on the topic choice)
Method: six vidIQ outlier searches (English long-form videos from the last 6 months, channels up to 100,000 subscribers,
at least 100,000 views, top 10 by breakout score = views relative to the channel's own average) and six keyword
researches. Everything below is **[OBS]** from those calls; the limits are listed at the end. Raw results are in the
tool output of the session, summarised here.

| ID | Niche (creator-conversation letter) | Observation [OBS] | Reading [INF] |
|---|---|---|---|
| SE-29 | A everyday mechanisms | Small channels with 100k-1.4M views at 7-11 minutes: Logic Made Simple (5.8k subs) "What Actually Happens Inside a Garbage Truck?" 592k views, 10 min; The Ordinary Mystery (8.3k) "Why Do Planes Fly Across the Atlantic at Night?" 1.39M, 11 min; Logic Made Simple "Why Do Ships Say Port and Starboard..." 278k, 7 min; SIMPLE WHY (16.3k) "Why Semi-Trucks Have Spikes on Their Wheels" 151k, 8 min | real breakouts exist in exactly our target format and length; four of five are about vehicles and transport, so the proven sub-theme is "why do vehicles/infrastructure do this" more than kitchen objects |
| SE-30 | A | keyword "how things work": about 143k searches a month, competition 46/100; "how everyday things work": 22k, growing 42 % | demand is real and competition is moderate; searches come mostly from Pakistan, the US, India and Vietnam |
| SE-31 | B business incentives | breakouts are mostly 20-minute documentary-style videos (PowerChip mattress 155k, Ground Break makeup 161k, Global Status Costco 1.8M) plus many "tips/savings" lists; breakout multiples 20-63x except one grocery video (2,117x, 5.7 min) | works, but at roughly 20 minutes and in a documentary or listicle style, longer than our 7-minute target |
| SE-32 | C myths | results are dominated by 1-2 hour compilations and "AI-labelled" list videos (Easy History Explained 69 min; Oddly Factual 111 min); one 5-minute example (TechXplainer, 1.7k subs, 277k views) | the myth niche exists but mostly as long listicles; short explainer evidence is thin; keyword "myths debunked" about 4,100 searches a month |
| SE-33 | D original animated stories | almost all hits are children's 3D animation (farm and rescue stories) or fan stories using other people's characters (Paw Patrol, K-pop Demon Hunters); one original non-kids example: Three-Quarter Town, 28k subs, 202k views, 5 min, AI-animated | the demand is real but sits in kids and third-party-IP content, which our rules exclude; only a very narrow original, non-kids slice is visible |
| SE-34 | E money/finance | the broadest set of breakouts: Estate Sense (1.8k subs) "Buying a New Car vs Used Car: The Math Nobody Shows You" 469k views, 9 min; Econ sketch (539 subs) "America's $40 Trillion Debt Explained Like You're 5" 176k, 6 min; Money Bureau (21.9k) bonds 1.12M, 19 min; Mark Invests rent vs buy 495k; MindCraft "Rule of 72" 213k, 10 min | strongest and widest evidence of small-channel breakouts, in 5-19 minute explainers; keyword "compound interest explained" 57k searches a month, competition 40/100 and falling (-10 %); the editorial risk (advice, ageing figures) is the cost |
| SE-35 | F what-if / space | strong numbers on small channels: Astropyre (9.4k) "The Terrifying Truth Behind Deja Vu" 1.24M, 22 min; Fossil (38k) 11.5M, 16 min; CosmoMis (1.2k subs) two videos of 119k and 171k at 4.5 and 5.7 minutes; Timeline Runner (1.5k) 380k | very strong raw views; framing is dark and "terrifying"; keywords "what if earth" 65k a month (growing 64 %), "space" 1.98M but competition 59/100; many results carry an AI label |
| SE-36 | all | "interesting facts" 1.79M searches a month (competition 52); top markets for these keywords are India, Pakistan, the US and Vietnam | demand is large but a large share of it is outside the US |

**Limits of this evidence (do not over-read it):** one query per niche, ten results each; a breakout score divides by
the channel's own average, so very small channels inflate it; a video's visual style (animated or not) is not visible in
these results; retention, revenue and the creator's actual workload are not measured; competition values are vidIQ
scores, not a count of rivals; most results carry AI labels or are unlabelled, so "AI-made videos can break out" is
observed but says nothing about audience loyalty; the keyword "why does it work" returned only technical-support
questions and was discarded (5 credits wasted, logged in the cost ledger).

## B.8 "Worlds collide" research, 2026-10-15 (70 credits; the creator's idea, the creator set a 100-credit limit)
The creator proposed a channel built on collisions of worlds ("what would happen if this were here": one film or game
world in another, one historical era in another). Same method as B.7 (English long-form, last 6 months, channels up to
100k subscribers, at least 100k views, top 10 by breakout), eight variants, five keyword researches and one Shorts search.

| ID | Variant | Observation [OBS] | Reading [INF] |
|---|---|---|---|
| SE-37 | you in another era (survival, daily life) | Flint (895 subs) "What Ancient Humans Had to Do to Survive the Ice Age" 253k; Bro Said So (1.4k) "What Did Ancient Humans Do For Pleasure?" 385k, 8 min; Through the Ages (2.2k) 195k and 440k; Do you mind? (3.1k) "Top 5 Worst Years to Be Alive in Human History" 1.55M, 8 min; Fossil (38k) "How Long You'd Last in Every Prehistoric Era" 11.5M | the broadest and strongest small-channel evidence seen in either research round |
| SE-38 | era meets era, past meets present | Ten Minute Historian (1.4k) "What If Medieval Europe Fought The Roman Empire?" 184k, 11 min; Plot Twist Files (14.7k, tags "animated history", "Clash of Eras") "Could 50 Modern Soldiers Conquer the Roman Empire?" 319k, 10 min; many 1.5-2.5 hour AI "portal to ancient times" dramas with 100k-360k views | demand is real; an animated "clash of eras" channel already exists (competition); the drama form is a different product |
| SE-39 | mechanism or money across eras | Runic (3.4k) "How Did Humans Survive -40 Nights Inside a Massive Medieval Castle?" 376k; Doodle Gulch (2.0k, a doodle-style channel) "What Cowboys REALLY Did With Their Money" 253k, 7.6 min; SPQR Chronicles (7.1k) "What Happened on a Roman Soldier's Last Day Before Retirement?" 1.14M; Rome Unscrolled (16k) "What Did People in Ancient Rome Actually Do All Day?" 2.17M; Lit With Rosie (1.3k) "How Rich Is Mr. Darcy... What Does 10,000 a Year Mean" 144k | the earlier arms (A how it works, E money) work inside the era frame, at our 7-12 minute length, and at least one is in doodle style |
| SE-40 | nature and science meet today | Mystic Evidence (1.8k) "8 Extinct Animals That Could Still Be Alive" 973k; Evolution Explained (3.8k) 287k; Humanity World (736 subs) "What If Dinosaurs Never Went Extinct?" 134k | works; many results are AI-labelled list videos |
| SE-41 | film-universe crossovers (third-party IP) | demand exists (RecapToon 4.2M MCU recap; Toasted Water "What If Marvel Had All the Rights" 1.05M; fan trailers 100k+) | every hit depends on someone else's characters; excluded by the creator's directive (section 3) and copyright/reused-content risk |
| SE-42 | game-world crossovers (third-party IP) | fan trailers (Mario, Zelda), "What if Trevor died in GTA 5" 315k, AI Mario/Sonic fan stories 662k | same exclusion as SE-41 |
| SE-43 | mythology meets today | Greek-myth "movies" (often AI), "Thor Norse Mythology: The Shocking Truth Marvel Hid From You" (1.6k subs) 139k; Lucky You (1.3k) animated "POV: Everyone Gets Superpowers Overnight" 105k at 1,317 views/hour | myths are public domain and usable; the franchise comparison works as commentary, not as a crossover |
| SE-44 | keywords | "how long would you survive" 50k/month (+150 %, competition 60); "prehistoric survival" 62k (competition 40); "daily life in ancient rome" 59k (+305 %); "ancient rome" 472k (+65 %); "roman history" 153k (competition 45); "middle ages" 93k (+51 %); "medieval peasants" 30k (+49 %); "alternate history" 96k (competition 47; the related term is an established channel's name); "time traveler" 33k (-30 %) | strong, mostly rising demand for the era side; the 30-day jumps for Rome may be a temporary spike |
| SE-45 | Shorts | one Shorts search (title-matched) returned unrelated films and edits | no Shorts conclusion from this batch |

**Limits:** as in B.7 (one query per variant, ten results, breakout inflated for tiny channels, no view of the visuals,
retention or revenue, many AI-labelled results). Competitors exist (Fossil, Plot Twist Files, Alternate History Hub).

## B.6 Data-quality flags (do not cite these rows)
M rows with internally inconsistent numbers: FactMint AI (827K subs vs 105.8K lifetime views), Antra Movies (1.29M subs vs
17,447 views), Bobby Viral (2.8M subs, index lists 1 video). Rows marked "name only" in M (most rows below rank 20) carry
no content evidence: their niche labels are guesses from the channel name.
