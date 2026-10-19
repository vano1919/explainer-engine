# Publishing and analytics

## Workflow (manual; P-20)
Package built and QA-clean -> creator reviews the review bundle -> **approval #2 recorded** -> the creator uploads in
Studio (visibility and schedule are the creator's) -> the creator gives the video id -> `record` stores it and starts the
snapshot schedule. Studio settings checklist: audience "not made for kids"; altered/synthetic label only if the policy
checklist says so; chapters; sources in the description; no mid-roll ads decision recorded; end screen to the next video.

## YouTube staging (D-56)
The finished episode is uploaded unlisted (or private), never public, by one command; the creator reviews in Studio and
clicks Public there.

```powershell
python -m explainer_engine.publish thumbnail <episode>                 # price and prompt; nothing paid
python -m explainer_engine.publish thumbnail <episode> --generate --approved-by "<who, where>"   # after the creator's OK
python -m explainer_engine.publish stage <episode>                     # dry run: youtube_stage.json + checklist, no network
python -m explainer_engine.publish stage <episode> --yes --confirm "<who, where>"   # upload: long video, thumbnail, Shorts
```

Inputs: `publish.json` (publish/1 with `tags`, `youtube`, `thumbnail`, per-Short `title`; PC rules must have no FAIL), the
Shorts of `production_script.json`, the render (`render/video.mp4`, `render/shorts/SHxx.mp4`, or `--video` / `--shorts-dir`).
Setup, once: a Google Cloud project with the YouTube Data API v3, an OAuth client of type Desktop app, its consent screen
published ("In production"; in Testing the refresh token dies after 7 days), then `python -m explainer_engine.publish auth
<client_secret.json>` on the creator's PC; the printed channel id goes into `EXPLAINER_YT_CHANNEL` and the content of
`tools/youtube/token.b64.txt` into `YOUTUBE_TOKEN_B64`, both as variables of the cloud environment, never in the repository
or a chat. Quota per V-47: an episode of 1 + 10 videos uses 11 of 100 daily uploads and about 65 of 10,000 units.

## Cadence hypothesis (D-06; not competitor frequency)
One long-form every two weeks and two Shorts a week for the first cycle, from estimated hours
([COST_AND_TIME_MODEL](COST_AND_TIME_MODEL.md)), revisited after three long-forms. What competitors post (SE-26) and what
the data proves are different from what this creator can sustain; the time log decides.

## First production cycle
Prototype passes -> batch research for three topics at once -> 3 long-forms and 6-9 Shorts over about six weeks ->
Shorts on a fixed weekly rhythm -> review at the end of the cycle. Candidates below are hypotheses, not guarantees; each
needs its dossier before it is chosen.

| Topic (D-25) | Collision type / test arm | Evidence | Main uncertainty |
|---|---|---|---|
| How long would you last as a medieval peasant? | you_in_era / arm 1 | SE-37, SE-44 ("medieval peasants" +49 %) | well covered by others; needs a fresh angle |
| What could a Roman soldier's pay buy? | money_across_eras / arm 1 | SE-39 (Roman soldier 1.14M; cowboy money 253k) | conversions are uncertain: ranges, amber framing |
| A Roman engineer visits a modern city | past_meets_present / arm 2 | SE-38 | needs strong sourcing on Roman engineering to avoid caricature |
| What if dinosaurs never went extinct? | world_what_if / arm 2 | SE-40 | speculative science: amber, sources on the K-Pg event |
| How did people keep warm in a medieval castle? | how_it_worked / arm 1 | SE-39 (Runic 376k) | building-history sources vary |

## Metrics (current YouTube definitions; Shorts and long-form never mixed)
Impressions, impressions CTR, traffic source, video age, average view duration, average percentage viewed, retention curve
and the opening drop-off, returning viewers, subscriber conversion; for Shorts: viewed vs swiped away and the Shorts feed
metrics where shown. Also our own: production hours, cost, QA failures, revisions. Snapshots at 48 hours, 7 days and
28 days (P-104), each with video age and traffic context. Comparisons are like with like (same length band, age and
traffic source); correlation is not recorded as cause.

## Learning loop (what to change)
| Symptom | Likely area | First action |
|---|---|---|
| low impressions | topic, packaging, channel reach | check topic demand and the title/thumbnail pair |
| low CTR, normal retention | packaging | revise thumbnail or title (one change) |
| early drop (first 30 s) | hook | rewrite the hook spec |
| mid or late drop | structure, length, pacing | shorten or restructure |
| QA failures at release | pipeline | fix the stage, not the content |
Change one major variable at a time; no conclusion from fewer than three comparable videos; a pattern is retained,
changed or retired only after that sample, and the specification changes through a new versioned decision (a new D- id)
while the baseline stays visible. A/B thumbnails use YouTube's own Test and Compare only after the feature is confirmed
available on the channel; otherwise controlled manual comparisons are labelled confounded.

## Scale and revise triggers
Scale cadence only when the time log shows hours per long-form at or below the target (4-6 h) for three videos in a
row. Revisit positioning (fallback in the decision log) only on the trigger stated there.
