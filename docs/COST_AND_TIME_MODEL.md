# Cost and time model

All prices are estimates unless a source and date are given. Budget caps are ceilings, not targets (invariant 2);
before any paid call the ledger below is updated with the estimate, and at 80 % of a cap work stops for a decision.

## Ledger
| Budget | Cap | Spent in this project | Notes |
|---|---|---|---|
| Gemini API / AI Studio | US$10 total | about $3.28 (estimate at list price; 44 pictures + about $0.26 of audio: Gemini TTS about $0.14 including one uncapped $0.10 mistake, Lyria 3 x $0.04; of which 2 world pictures at 1K were wasted and replaced by 2K; includes the first kit test and the discarded child-faced bank; real billing not yet read) | free-tier use is not assumed equal to paid cost; TMR's earlier spend (about $2.40) belongs to that project |
| vidIQ credits | 200 | 130 (2026-10-15: 60 niche research + 70 worlds-collide research; see the spend log) | account balance read 2026-10-15: 395, later 445 (an add-on top-up of 50 that is not our spend), 385 after the research batch (65 renewable, resets 2026-11-08; 320 add-on); the balance call costs 0; a call's cost is read from its tool description first |
| RunPod | US$3 hard cap (D-31) | $0.00 | balance read 2026-10-16: $7.37 (the account is shared with TMR); no pod running; every pod needs an approved price and time cap |
| ElevenLabs (D-39, connector, the creator's account credits) | 3 short samples now; the Day 1 read (~2,400 characters) only after the creator picks a voice (creator, 2026-10-16) | 849 credits ≈ $0.15 for 3 samples + 2,337 credits ≈ $0.42 for the Day 1 Clyde read (estimates read first, actuals equal); Scribe 0 credits (estimate 0); after the creator's review, a v3 test of the first 3 sections (creator-approved, 1,011 credits ≈ $0.18); total about $0.75; full v3 re-read estimated 2,809 credits ≈ $0.51, waits for approval | per-call price read with `estimate_only` first; never re-run a generation to retry; Scribe for timings is a separate small charge, estimated before the call |
| Subscriptions | none planned | $0/month | any paid voice or tool is an explicit approved line item |

### vidIQ spend log (written before each batch; actuals filled after)
| Date | Batch | Planned | Actual | Balance before -> after | Question it answers |
|---|---|---|---|---|---|
| 2026-10-15 | niche-demand research, outlier searches (6 x 5 credits, English long-form, small channels) | 30 | 30 | 445 -> 415 | which candidate niche (A-F in the creator conversation) has real small-channel breakouts |
| 2026-10-15 | keyword demand and competition (6 calls; 5 credits each, read from the balance; 1 of the 6 used a too-generic seed and returned unusable troubleshooting questions) | about 30 | 30 | 415 -> 385 | search demand and competition per niche |
| 2026-10-15 | "worlds collide" concept research: about 8 outlier searches + 5 keyword researches (5 credits each) | about 65, hard limit 100 (creator) | 70 (8 long-form outlier searches, 5 keyword researches, 1 Shorts outlier search whose results were off-topic) | 385 -> 315 | does the creator's cross-world idea have demand, which variants, and does it beat or extend D-24 |
Creator approved up to about 60 credits for this batch on 2026-10-15; cap for the project stays 200. The creator set a 100-credit limit for the cross-world research batch (2026-10-15); project total stays under 200.

Planned use: Gemini at most about $2 (Kit concept exploration, reusable props, thumbnail elements); vidIQ 0-60 credits,
only for a question that would change a title or topic.

## Cost classes
One-time development: Node.js LTS, Remotion (free for this use, V-04), fonts, CC0 sound effects: $0. Per video (lean,
local): $0 money; Kokoro runs on the CPU; renders on the CPU. Recurring monthly: $0. Optional paid: cloud TTS (only if
the listening test rejects Kokoro; price re-checked at that time, not assumed), extra generated assets.
Scenarios: lean (all local, hand-built SVG) = baseline; normal (a few generated reusable assets within the cap);
higher quality (a paid voice, more generated props) needs approval and a monthly line.

## Machine time [estimates; replaced by measurements in Phases 4-6]
Kokoro about 2-3x real time on this CPU (TMR measurement); 7 min of narration about 15-20 min. Scene rendering: unknown
until the benchmark; the gate is a 10-minute episode in under 2 hours. Disk: a 7-minute 1080p30 episode's scene files plus
final about 1-2 GB (estimate); jobs are cleaned by the protected-run rule.

## Human time per long-form [estimates]
research 2-3 h, script review 1 h, storyboard and asset review 1-3 h (falls as the library grows), QA 0.5-1 h, packaging
0.5-1 h, upload 0.25 h: about 6-10 h at first, a target of 4-6 h once assets repeat. A Short about 1-1.5 h. Revisions and
failed-job recovery are logged separately. The report's claims "5 videos in 2 hours" and "24 minutes per video" (SE-15) are
not used. Nothing here is described as fully automated: research, script approval, asset creation, review and upload
remain human work.

## Time log
`jobs/<slug>/time_log.json` records minutes per activity per video (research, scripting, storyboard, assets, narration
fixes, QA, revisions, packaging, upload) and the machine time per stage; the cadence decision (D-06) reads it.
