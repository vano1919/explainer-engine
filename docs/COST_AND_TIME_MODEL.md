# Cost and time model

All prices are estimates unless a source and date are given. Budget caps are ceilings, not targets (invariant 2);
before any paid call the ledger below is updated with the estimate, and at 80 % of a cap work stops for a decision.

## Ledger
| Budget | Cap | Spent in this project | Notes |
|---|---|---|---|
| Gemini API / AI Studio | US$10 total | about $8.0 (80 % of the cap, STOP; 2026-10-16: look test 6 Pro pictures $0.804; Day 1 v5 67 Nano Banana 2.1 pictures at 2K = $3.598 by the spend log (46 + 16 + 3 + 2 repaints); about $0.3 of judge calls, estimated; the earlier part) about $3.28 (estimate at list price; 44 pictures + about $0.26 of audio: Gemini TTS about $0.14 including one uncapped $0.10 mistake, Lyria 3 x $0.04; of which 2 world pictures at 1K were wasted and replaced by 2K; includes the first kit test and the discarded child-faced bank; real billing not yet read) | free-tier use is not assumed equal to paid cost; TMR's earlier spend (about $2.40) belongs to that project |
| vidIQ credits | 200 | 155 (2026-10-15: 60 niche research + 70 worlds-collide research; 2026-10-16: 25 narration research; see the spend log; 2026-10-19: 110 + 45 = 155 for the D-48/D-49 research under the creator's separate allowance of up to 200 credits for that research (80 % reached at 160: stop), so the original 200 cap covers the earlier 155) | account balance read 2026-10-15: 395, later 445 (an add-on top-up of 50 that is not our spend), 385 after the research batch (65 renewable, resets 2026-11-08; 320 add-on); the balance call costs 0; a call's cost is read from its tool description first |
| RunPod | US$3 hard cap (D-31) | about $0.81 (2026-10-16: 13-picture Day 1 run about $0.20; 35-picture v2 run $0.28 by the guard, **pictures lost**: the stage hit its 15-minute limit and the fatal stop skipped the push; manifest fixed; 35-picture re-run $0.26; 6-picture style-bridge test $0.07 by the guard, cap $0.25) | balance read 2026-10-16 after the bridge test: $3.64 (the account is shared with TMR; the drop since the previous reading is larger than this project's guard figures and is to be checked in RunPod billing); no pod running; every pod needs an approved price and time cap |
| ElevenLabs (D-39, connector, the creator's account credits) | 3 short samples now; the Day 1 read (~2,400 characters) only after the creator picks a voice (creator, 2026-10-16) | 849 credits ≈ $0.15 for 3 samples + 2,337 credits ≈ $0.42 for the Day 1 Clyde read (estimates read first, actuals equal); Scribe 0 credits (estimate 0); after the creator's review, a v3 test of the first 3 sections (creator-approved, 1,011 credits ≈ $0.18); total about $0.75; full v3 re-read estimated 2,809 credits ≈ $0.51, waits for approval | per-call price read with `estimate_only` first; never re-run a generation to retry; Scribe for timings is a separate small charge, estimated before the call |
| Subscriptions | none planned | $0/month | any paid voice or tool is an explicit approved line item |

### vidIQ spend log (written before each batch; actuals filled after)
| Date | Batch | Planned | Actual | Balance before -> after | Question it answers |
|---|---|---|---|---|---|
| 2026-10-15 | niche-demand research, outlier searches (6 x 5 credits, English long-form, small channels) | 30 | 30 | 445 -> 415 | which candidate niche (A-F in the creator conversation) has real small-channel breakouts |
| 2026-10-15 | keyword demand and competition (6 calls; 5 credits each, read from the balance; 1 of the 6 used a too-generic seed and returned unusable troubleshooting questions) | about 30 | 30 | 415 -> 385 | search demand and competition per niche |
| 2026-10-15 | "worlds collide" concept research: about 8 outlier searches + 5 keyword researches (5 credits each) | about 65, hard limit 100 (creator) | 70 (8 long-form outlier searches, 5 keyword researches, 1 Shorts outlier search whose results were off-topic) | 385 -> 315 | does the creator's cross-world idea have demand, which variants, and does it beat or extend D-24 |
| 2026-10-16 | narration research for the narration-script skill: 1 YouTube search + 4 transcripts (5 credits each) | 25, kept under 80 % of the project cap | 25 | 315 -> 290 | how successful narrated stone-age/what-if videos place questions, reactions and open loops |
| 2026-10-19 | story/edit/Shorts research for D-48 (creator allowance up to 200 credits for this research): comment insights, 2 long-form and 3 Shorts video watches | up to 200 | 110 | 245 -> 135 | what competitors' what-if videos and Shorts do in story, pace, motion and sound; what viewers ask for |
| 2026-10-19 | D-49 parameter audit: the creator's channel videos (5), analytics x3 (15; empty, the data lags 2 days), 2 Shorts watches (20), 1 Shorts outlier search (5) | within the same 200 allowance | 45 | 135 -> 90 | how the creator's own Shorts are cut against breakouts; engagement benchmarks |
Creator approved up to about 60 credits for this batch on 2026-10-15; cap for the project stays 200. The creator set a 100-credit limit for the cross-world research batch (2026-10-15); project total stays under 200.

Planned use: Gemini at most about $2 (Kit concept exploration, reusable props, thumbnail elements); vidIQ 0-60 credits,
only for a question that would change a title or topic.

## Cost classes
One-time development: Node.js LTS, Remotion (free for this use, V-04), fonts, CC0 sound effects: $0. Per video (lean,
local): renders on the CPU. Narration is ElevenLabs credits (D-39, D-52; estimated and logged before every read; Kokoro of
D-12 is retired). Recurring monthly: the ElevenLabs plan. Optional paid: extra generated assets.
Scenarios: lean (all local, hand-built SVG) = baseline; normal (a few generated reusable assets within the cap);
higher quality (a paid voice, more generated props) needs approval and a monthly line.

## Machine time [estimates; replaced by measurements in Phases 4-6]
an ElevenLabs read returns in well under real time; word timings (local Whisper) about real time. Scene rendering: unknown
until the benchmark; the gate is a 10-minute episode in under 2 hours. Disk: a 7-minute 1080p30 episode's scene files plus
final about 1-2 GB (estimate); jobs are cleaned by the protected-run rule.

## GPU pods: cost per unit, and no network volume (P1c, RP-01..10 in [CLOUD_RUNBOOK](CLOUD_RUNBOOK.md))
**Per unit.** `runpod cost <pod>` divides the pod's billed dollars by the units its `units.json` reports and writes the row into
`config/job_speeds.json` (seconds per unit, fixed setup minutes, MB/s per cloud, `usd_per_unit`) and into the ledger item of the pod.
A plan quotes dollars per picture, clip or training step from those rows; a job type with no row has no per-unit price yet and says so
(P12a and P12b write the first rows). Nothing in this file is a per-unit price until a pod measured it.

**No network volume (RP-03).** Facts read 2026-10-29 (docs.runpod.io/storage/network-volumes and runpod.io/pricing, re-check before
changing the rule): a network volume costs $0.07 per GB-month (100 GB = $7/month), exists on Secure Cloud only and ties a pod to one
datacenter, which can reduce GPU stock. Its saving is the model download of each pod (about $0.25 on a $1.69/h card, $0.03-0.09 on the
$0.16-0.35/h cards); the Secure premium (about +$0.80/h on the $1.69 card, +$0.24/h on a $0.35 card) is larger than that saving for any
job over about 20 minutes. Break-even from the p9 re-check: at least 28 pods a month of 20 minutes or less on the big card. Until a
production week needs ten or more short Secure pods a day, the model is downloaded once per batch (RP-01, RP-02) with `hf_transfer`
and the pinned images (CR-18) cached on hosts.

## Human time per long-form [estimates]
research 2-3 h, script review 1 h, storyboard and asset review 1-3 h (falls as the library grows), QA 0.5-1 h, packaging
0.5-1 h, upload 0.25 h: about 6-10 h at first, a target of 4-6 h once assets repeat. A Short about 1-1.5 h. Revisions and
failed-job recovery are logged separately. The report's claims "5 videos in 2 hours" and "24 minutes per video" (SE-15) are
not used. Nothing here is described as fully automated: research, script approval, asset creation, review and upload
remain human work.

## Time log
`jobs/<slug>/time_log.json` records minutes per activity per video (research, scripting, storyboard, assets, narration
fixes, QA, revisions, packaging, upload) and the machine time per stage; the cadence decision (D-06) reads it.
