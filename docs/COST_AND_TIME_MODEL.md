# Cost and time model

All prices are estimates unless a source and date are given. Budget caps are ceilings, not targets (invariant 2);
before any paid call the ledger below is updated with the estimate, and at 80 % of a cap work stops for a decision.

## Ledger
| Budget | Cap | Spent in this project | Notes |
|---|---|---|---|
| Gemini API / AI Studio | US$10 total | $0.00 | free-tier use is not assumed equal to paid cost; TMR's earlier spend (about $2.40) belongs to that project |
| vidIQ credits | 200 | 0 | account balance read 2026-10-15: 395 (125 renewable, resets 2026-11-08; 270 add-on); the balance call costs 0; a call's cost is read from its tool description first |
| Subscriptions | none planned | $0/month | any paid voice or tool is an explicit approved line item |

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
