# Packaging rules: thumbnail, title, tags, description (TN-)

One package, one promise: the thumbnail shows it, the title says it, the first line of the description repeats its keyword,
the first seconds of the video pay it off. `python -m explainer_engine.publish thumbnail <episode>` prices and, after the
creator's OK, paints the long video's thumbnail (D-56); `publish stage` checks the rest. Layout templates, palette and the
general packaging QA stay in [TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md).

Evidence: [thumbnail_research_2026-10-19](research/thumbnail_research_2026-10-19.md) (five passes, every URL dated 2026-10-19;
also V-49). Its honest finding: **platform and policy facts are solid, element rules are weak.** No randomized dataset isolates one
thumbnail element; the large observational studies find small or no differences for face, colour and brightness; nothing is
published on illustrated thumbnails, silhouettes or recurring motifs. So each rule below carries a grade:

- **P** policy or platform fact (YouTube Help), binding;
- **S** supported by a study, with its limits named;
- **H** hypothesis from theory or practitioners: used as our default and **tested on our own channel** (plan below), never
  quoted as a law, never as a CTR promise.

The line we hold: **curiosity yes, deception no.** A thumbnail may hide the answer; it may never show or promise what the video
does not contain. Test & Compare picks winners by watch time, not clicks, and Help says clickbait tends to have high CTR and low
average view duration, which makes a video less likely to be recommended.

## Thumbnail

| ID | Grade | Rule | Source |
|---|---|---|---|
| TN-01 | P | One promise the video keeps: the picture shows the real conflict or question (a hero, a stake, a moment that appears in the video). `thumbnail.concept` names it in one sentence before anything is painted. | Help 9229980 ("misleads viewers to think they're about to view something that's not in the video"); Help 2801973 ("maliciously misleading titles, thumbnails ... to trick users") |
| TN-02 | S+H | Curiosity gap with a concrete anchor: show a named hero or event and withhold exactly one thing (who falls, what breaks); never an outcome the video does not reach. Pure vagueness does not reliably win. | Le Quere & Matias 2025, Sci. Reports (8,977 headline experiments, concreteness effect is curvilinear); Loewenstein 1994 |
| TN-03 | H | One focal subject, big; at most one or two pointers (arrow, ring). Face share is not decisive: Eden found a face in 84.2 % of breakouts and 82.2 % of underperformers (noise), 1of10 found little difference, so our drawn hero's face is used when it is the story, not by rule. | Eden 2026 (507,478 videos), vidIQ 2026 (500 breakouts, no control group), 1of10 via SEJ |
| TN-04 | H | Headline of at most 4 words that adds to the title instead of repeating it, set by us in the channel font, never lettered by the model. Evidence is thin: Eden's largest gap was 4-6 words (30.6 % vs 26.5 % of breakouts), vidIQ's median is 5 and its most common pattern is no text; the cap of 4 is our default and is test variable T-2. | Eden; vidIQ |
| TN-05 | H | Legibility, not colour theory: light against dark, the headline in the paper-on-night text pair with an ink outline, readable at 168 x 94 px and in greyscale. Measured colour differences between breakouts and underperformers were nil (Eden: brightness 40.9 vs 40.5, saturation 35.2 vs 34.7), so colour is a design choice, not a CTR claim. 168 x 94 is a community stress test, not a YouTube spec. | Eden; vidIQ ("baseline, not differentiator") |
| TN-06 | H | Keep the lower-right corner free (duration stamp) and text off the edges that feeds crop. | vidIQ 2026; Help 72431 |
| TN-07 | P | Never: nudity or sexual imagery (see TN-12), gore or blood, violent imagery meant to shock or disgust, vulgar words, impersonation or a copied logo, key art or title font of a franchise ([RIGHTS_AND_FAIR_USE](RIGHTS_AND_FAIR_USE.md)), "18+"/"21+" or any sexual text or link. Real victims or realistic blood never appear. | Help 9229980; Help 6162278 |
| TN-08 | H | The pull is allowed to be strong in colour and stakes but not in hype: horror-style faces, wide mouths, red arrows and "shocking" words are left out (a vendor case saw CTR rise 5.6 % to 6.4 % after removing them; confounded). | AIR Media-Tech case (vendor) |
| TN-09 | P | File: 16:9, JPEG or PNG; we export 1280 x 720 JPEG under 2 MB (every upload path takes it; Help recommends 3840 x 2160 and a 50 MB desktop limit; under 720p, Test & Compare downscales to 480p). | Help 72431, 13861714; thumbnails.set |
| TN-10 | P | Before staging the creator looks at it: does every element appear in the video, does it read at phone size, would a viewer feel cheated at minute two? (review checklist below) | TN-01 |
| TN-19 | H | Main subject (observed in the niche, not proven): the story's two or more **named heroes or opponents**, drawn big and face-forward in one drawn world, bright background, one clear expression each; a versus layout (left against right, a number or one word between) for rivalry episodes. Dark, moody frames are for the video, not the thumbnail. | research Appendix G |
| TN-20 | H | One template for the channel: the same title position, headline font and size, outline, palette and cameo slot on every thumbnail, so a viewer knows the channel before reading. | Appendix G; Romaniuk 2018 |
| TN-11 | P | Shorts: custom Shorts thumbnails are set in Studio on a computer (9:16); the API behaviour on Shorts is unverified, so none is sent. | Help 72431 |

### The recurring motif (the creator's request, 2026-10-19)

| ID | Grade | Rule |
|---|---|---|
| TN-12 | H + P | The channel's signature (the creator, 2026-10-19: "a little sexiness, like the GTA VI cover woman"): **our own glamorous, confident woman** in a game-cover mood (sunglasses, crop top or dress, jeans, sunset and neon colours, a knowing look), in one fixed slot and style on every thumbnail. She must appear in the video too (a character of the story, TN-01). Never Rockstar's Lucia, key art or poses (RIGHTS_AND_FAIR_USE: our own art only). The focus is her face and attitude. **Not allowed** (YouTube's wording, Help 9229980 and 2802002): breasts, buttocks or groin as the focal point; a pose or clothing "intended to sexually arouse" (a bikini in the foreground, bent over, arched back, hip thrust, the camera on the buttocks); a skin-coloured or nudity-implying form; sexualised text. The policy applies to illustrated and animated content (Help 6162278: "real and computer-generated visuals"). The cost of a miss is age restriction, removal or limited ads ("titles or thumbnails with sexualized themes"), which can hit the whole video; it is judged by a reviewer, so she keeps a clear margin below the wording. The niche's thumbnails are bright and face-forward (Appendix G), so she sits beside the heroes, not alone in the dark. The motif is a hypothesis, tested in T-4. |
| TN-13 | H | The silhouette is drawn once as a reference sheet and reused (the same discipline as the heroes' face sheets, D-55); its look is chosen from ONE collage of variants that the creator approves before any thumbnail is painted (the creator's standing rule for a new character style). The model's lettering is never used; headlines are composited by us (exact spelling, one typeface). Every Gemini picture carries SynthID. Check hands and faces by eye. |

## Title, tags, description, Shorts (the rest of the package)

| ID | Grade | Rule | Source |
|---|---|---|---|
| TN-14 | P+H | Title: at most 100 characters (Studio limit; no < or >). The topic and hook come first, because feeds cut long titles; about 60-70 characters is the working target (sources disagree: 30-50 to 50-70). One strong emotional word, no all-caps word, no "%" or "boring" (our title rules). It adds context to the thumbnail instead of repeating it. Curiosity yes, a broken promise no. | vidIQ title guide; Help 2801973; [TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md) |
| TN-15 | P | Tags: few and accurate, plus common misspellings of the key names. Help: tags "play a minimal role" in discovery and excessive tags break the spam policy. Total 500 characters including commas and quotes; the tool drops the rest. Tags are judged metadata, so none that mislead. | Help 146402; V-45 |
| TN-16 | P+H | Description: the first 100-160 characters carry the keyword and the promise (what shows before "more"); sources and an honest note after; chapters as `0:00 Label` lines (the first at 0:00, at least three, each at least 10 seconds); at most 3 hashtags in the description (only the first three show above the title; over 60 are all ignored); no keyword stuffing; no sexual or "18+" wording. Under about 1000 characters is a vidIQ habit, not a rule. | Help 12948449, 6390658; vidIQ |
| TN-17 | H | Shorts: title 20-40 characters with the hook in the first 40 (feeds cut there); a 1-2 sentence description, the full video's title and link, 3-5 hashtags at most; "#shorts" is not required (secondary source only); the Short's related video is set in Studio. | vidIQ Shorts titles |
| TN-18 | H | One package: before staging, say in one line what the thumbnail shows, what the title promises and where in the video it is paid off (timestamp). If the three do not name the same promise, fix the weakest. | vidIQ; TN-01 |

## Review checklist (human, before staging; TN-10)

1. One sentence: what does the thumbnail promise? Is that moment in the video, at what time?
2. Squint at 168 x 94 px and in greyscale: subject and headline still readable?
3. Headline: at most 4 words, adds to the title, spelled right, lower-right corner clear?
4. The signature woman: in the video too, face and attitude as the focus, no bikini, bent or arched pose, no body part as the focus, not Rockstar's art? (TN-12)
5. No franchise logo, key art, real person's likeness, blood, weapon pointed at the viewer?
6. Title: hook first, about 60-70 characters, no all-caps word, no repetition of the headline?
7. First description line carries the keyword and the promise? Hashtags at most 3? Sources below?
8. Would a viewer who clicked feel cheated at minute two? If yes, change the thumbnail or the video.

## A/B plan for the first videos (YouTube Test & Compare, TN-18)

What YouTube says (Help 16391400, 13861714): up to 3 variants of thumbnail, title or both; the winner is the highest **watch
time** share, not the highest CTR; a small control group sees only the default; a test runs a few days up to two weeks; no
minimum traffic is published and low impressions often end "Inconclusive" or "Performed same"; desktop Studio only; not for Shorts,
made-for-kids, mature-audience or private videos; editing the title or thumbnail mid-test ends it; use clearly different variants,
at least 1280 x 720; early impressions lean to people who already know the channel. Typical CTR: half of channels sit between 2 %
and 10 % (Help 7628154), wider for new videos and videos under 100 views, and it differs by traffic source: compare like with like.

Sample size (planning aid for CTR, our computation, two-sided alpha 0.05, power 80 %): n per variant = (1.96 x sqrt(2 p(1-p)) +
0.8416 x sqrt(p1(1-p1) + p2(1-p2)))^2 / (p2-p1)^2. At a 4 % baseline: a 20 % relative lift needs about 10,300 impressions per
variant; 30 % about 4,800; 50 % about 1,900; 10 % about 39,500. A channel with a few thousand impressions per video can only
see large differences, so **test bold differences, one variable at a time**, and read "Inconclusive" as "no detectable
difference", not as failure.

| Test | Variable (one only) | Variants | Why |
|---|---|---|---|
| T-1 | Headline presence | no text / 2 words | the evidence on text is thin and contradictory |
| T-2 | Headline length | 2 words / 4 words | our cap of 4 is a default, Eden's gap favoured 4-6 |
| T-3 | Subject | the hero's face / the object or document at stake | the face evidence is a wash |
| T-4 | The signature woman | with her / the same picture without her | nothing published; also the recognition hypothesis |
| T-5 | Title | curiosity title / keyword title (vidIQ's "title flip") | which promise the audience follows to the end |

Run T-4 first on the first long video, on the video's 2nd to 3rd week if it is old enough to give impressions; Shorts cannot be
tested, so the Shorts only borrow what won on the long video. Record every test in `publish/ab_log.json`: variant, dates,
impressions, impressions CTR, average view duration, Studio's verdict. Conclusions need at least three comparable videos
([PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md), learning loop).

## What the tool checks and what stays human

`publish/thumbnail.py`: concept present, headline at most 4 words (TN-04), 1280 x 720 and under 2 MB (TN-09), the paid gate.
`publish/plan.py`: title and description limits, no < or >, all-caps word, "%" or "boring", title over 70 characters,
more than 3 hashtags in a description, "18+"/"21+" wording, chapters. Everything else (TN-01, 03, 05, 07, 08, 12, 18) is the
checklist above, answered by the creator.
