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

## B.6 Data-quality flags (do not cite these rows)
M rows with internally inconsistent numbers: FactMint AI (827K subs vs 105.8K lifetime views), Antra Movies (1.29M subs vs
17,447 views), Bobby Viral (2.8M subs, index lists 1 video). Rows marked "name only" in M (most rows below rank 20) carry
no content evidence: their niche labels are guesses from the channel name.

