# Thumbnail rules: click-worthy, never misleading (TN-)

The long video's thumbnail is made by `python -m explainer_engine.publish thumbnail <episode>` (D-56): it prices one picture
on Gemini's premium image model, paints it only after the creator's OK, sets the headline in our own font and checks the
machine-checkable rules below. The layout templates, palette and the general packaging QA stay in
[TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md); this file holds the rules for *how hard a thumbnail may pull*. Every
rule is a heuristic from the cited sources unless it says "policy"; none predicts a click rate
([TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md), "What a score may and may not mean"). Sources were read on 2026-10-19
(V-49 in [MARKET_RESEARCH](MARKET_RESEARCH.md)); vidIQ's figures are vidIQ's own sample, not YouTube data.

The line we hold: **curiosity yes, deception no.** A thumbnail may hide the answer; it may never show or promise what the
video does not contain. YouTube's own test of title and thumbnail picks the winner by watch time, not clicks, so a pull the
video does not pay back loses there too.

| ID | Rule | Kind | Source | Checked by |
|---|---|---|---|---|
| TN-01 | One promise: the picture shows the video's real conflict or question (a scene, a hero, a stake that appears in the video). `thumbnail.concept` names it in one sentence before anything is painted. | policy + heuristic | Thumbnails policy, support.google.com/youtube/answer/9229980 ("misleads viewers to think they're about to view something that's not in the video"); spam and deceptive practices, answer/2801973 ("malicious clickbait") | `thumbnail.py` refuses an empty concept; human: TN-10 |
| TN-02 | Curiosity gap, not a lie: show the moment *before* the answer (who falls, what breaks), never an outcome the video does not reach. A cross-out, a question mark or a "?" headline is fine when the video answers it. | heuristic | YouTube Blog, "Master these 4 metrics" (2025-09-03): high CTR with low retention means the thumbnail "may be making a promise the video doesn't deliver on" | human: TN-10 |
| TN-03 | One focal subject, big; at most one or two pointers (arrow, ring). A clear face with a readable emotion (our drawn hero's face counts) at about a quarter to a third of the frame; an exaggerated "shock face" is not needed. | heuristic | vidIQ, "YouTube thumbnail design tips: best practices for 2026" (updated 2026-07-14; 500 breakout videos: 69 % show a face, about 1 in 20 an exaggerated expression) | prompt (`thumbnail.STYLE`); human |
| TN-04 | Headline of at most 4 words that **adds** to the title rather than repeating it; set by us in the channel font, never lettered by the model. | heuristic | vidIQ 2026 (median 5 words where text is used; more than 5-6 hard to read at feed size); [TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md) keeps our cap at 4 | `thumbnail.check_text` |
| TN-05 | High contrast: light against dark, the headline in the paper-on-night text pair with an ink outline; it must read at 168 x 94 px and in greyscale. | heuristic | vidIQ 2026 (56 % high-contrast colour; 89 % a face, high contrast or both) | `thumbnail.compose` (palette tokens); human at 168 x 94 |
| TN-06 | Keep the lower-right corner free (the duration stamp) and keep text off the edges that mobile feeds crop. | heuristic | vidIQ 2026; Help answer/72431 (a vertical video with a 16:9 thumbnail also gets a 4:5 crop on some surfaces) | prompt rule; headline placed top-left or top-right |
| TN-07 | Never: sexual imagery, gore or blood, violent imagery meant to shock, vulgar words, a weapon aimed at the viewer, a logo, key art or title font of a franchise ([RIGHTS_AND_FAIR_USE](RIGHTS_AND_FAIR_USE.md)). | policy | answer/9229980; RR rules | prompt rule (`thumbnail.RULES`); human |
| TN-08 | One variable at a time when testing: Studio's "Test & compare" (up to 3 thumbnails or titles, desktop Studio, advanced features on; not for Shorts, made-for-kids or private videos) picks by watch time. Results are recorded as "Winner / Performed same / Inconclusive", never as a CTR prediction. | heuristic + platform fact | Help answer/16391400 | creator in Studio |
| TN-09 | File: 16:9, 1280 x 720 JPEG under 2 MB (the mobile limit; desktop and the API take 50 MB since 2026-09-14). | platform fact | Help answer/72431; developers.google.com/youtube/v3/docs/thumbnails/set | `thumbnail.check_image` |
| TN-10 | Before staging, the creator looks at it: does every element appear in the video? Does it read at phone size? Would a viewer feel cheated at minute two? | human | TN-01, TN-02 | the review checklist of `publish stage` |
| TN-11 | Shorts: no API thumbnail (Help says custom Shorts thumbnails are added in Studio on a computer; the API behaviour on Shorts is unverified). Optional 9:16 frame chosen in Studio. | platform fact | Help answer/72431 | the review checklist |

Not adopted (unverified): the leaked "MrBeast production guide" (authenticity never confirmed), dark-mode colour rules (no
data-backed source found), Paddy Galloway and Think Media advice (no first-hand page found on 2026-10-19).
