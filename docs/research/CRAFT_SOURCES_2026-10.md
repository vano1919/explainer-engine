# Craft curriculum sources (P3b sub-step 1), access date 2026-10-29

Sources only; no curriculum prose. Input: `recheck/p3_craft.json` (17 `curriculum_gaps`, the `storage_recommendation` constants,
12 `unverified` items, 78 inventory items). Grading follows D-59 (`docs/SOURCED_RULES.md`): binding = two of three source types
(A article/official/study, B book, C video); otherwise hypothesis (REVIEW only).

## Method and honesty notes

- "Opened" means the page or PDF text was fetched in this session and the quoted/paraphrased content was read there. A search snippet alone
  is never marked opened. The fetch tool summarises pages through a small model; direct quotes below are from PDFs I converted to text
  myself (marked `[pdftotext]`) or are short paraphrases.
- No YouTube page could be opened (the fetch returns only footer text). Every type C item is therefore **not opened**; a video is named only
  when a search result or an article about it exists, and never counts toward "two types" until someone watches it.
- Books were not available. A book is cited by edition only and marked "not re-opened"; a secondary page that confirms a statement is named.
  Under D-59 a "not re-opened" book is a claim of type B that nobody has checked, so I propose **hypothesis** wherever a B claim is the only
  second type.
- Verdicts: SUPPORTED (source says it), PARTIAL (source supports the idea, not the number or not all of the rule), NOT FOUND (nothing opened
  supports it; the number stays a hypothesis or is dropped). No URL, page number or figure below is guessed.
- Failed or blocked fetches (recorded so nobody retries blindly): transom.org (empty), designingsound.org (excerpt only), m3.material.io
  (title only, JS page), teaching.pitt.edu PDF (HTTP 503), Dartmouth KB (503), twut.nd.edu (host not allowed in this session's network),
  colour-transfer PDF at cs.tau.ac.il (404), Wikipedia "Low-angle shot" high-angle part absent, YouTube search page (no content).

Short ids: **M** = Murch "Dense Clarity - Clear Density" PDF copy, `https://rompus-public.pages.dev/portfolio/dense_clarity_by_walter_murch.pdf`
(a third-party host of the Transom Review essay; text read `[pdftotext]`; the Transom original at transom.org was not readable).

---

## 1. Screenwriting: AI-register lexicon (N-15)

| rule / number | what the source says | type | URL (opened 2026-10-29) / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Word-frequency shift after LLMs: banned-word list basis | arXiv 2404.01268 abstract page: 950,965 papers, 2020-Feb 2024, LLM-modified share up to 17.5 % (CS). The abstract page does NOT name delve/intricate/meticulous; word-level analysis would be in the full text, not read. Title on arXiv is "Mapping the Increasing Use of LLMs in Scientific Papers" (the repo's input list has a different title: correct it) | A | https://arxiv.org/abs/2404.01268 | PARTIAL (existence of LLM drift yes; the named words not confirmed) | hypothesis |
| Excess-vocabulary method | arXiv 2406.07016, Kobak, Gonzalez-Marquez, Horvat, Lause: 15M PubMed abstracts 2010-2024; "at least 13.5 % of 2024 abstracts were processed with LLMs"; sudden rise of style words. Real title: "Delving into LLM-assisted writing in biomedical publications through excess vocabulary" (input list had a different title) | A | https://arxiv.org/abs/2406.07016 | PARTIAL (supports "style words rose"; specific list not read on the abstract page) | hypothesis |
| Specific words: delve, tapestry, realm, landscape, "testament to", "it's important to note", "Picture this", triplets, rhetorical questions | Search-result summaries of Substack and blog lists say delve and tapestry are the strongest tells; structure and density matter more than a single word; one source warns a single hit proves nothing. Only search snippets; these pages were NOT opened | A (weak, blogs) | not opened: carly.substack.com/p/spotting-machine-made-prose, plusdocs.com/blog/the-most-overused-chatgpt-words | NOT FOUND (as opened source) | hypothesis |
| Density thresholds (>1 per 300 words REVIEW, >3 FAIL) | No source gives a threshold | - | - | NOT FOUND | house number only |
| Second type (C video on AI tells) | Search returned no YouTube result | C | - | NOT FOUND | still needs C |

## 2. Sound design

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Law of two-and-a-half | M: "five layers is the maximum that can be tolerated ... if you want the experience to be simultaneously Dense and Clear" but only when layers are spread evenly across the conceptual spectrum; "If the sounds stack up in one region (one color), the limit shrinks to two-and-a-half." | A (essay) + B (Murch is also in print) | M [pdftotext] | SUPPORTED, with correction: 2.5 applies to sounds of the SAME "colour"; 5 total when spread. The repo rule "no more than two foreground ideas" is the same-colour case | A confirmed; B (book form) not needed; essay is the primary. Hypothesis until a second type (C) is opened |
| Encoded vs embodied | M: "The clearest example of Encoded sound is speech. The clearest example of Embodied sound is music." | A | M | SUPPORTED | hypothesis (one source) |
| Narration centred, music wide, spot SFX moves with action | M: dialogue "always placed in the center no matter what the actual position of the actors"; effects of the "yellow" variety "routinely ... moved around the screen with the action"; music comes from all speakers | A | M | SUPPORTED (qualitative). The +-0.45 pan range: NOT FOUND | hypothesis; number NOT FOUND |
| Acoustic perspective matches shot; wide = HF roll-off + wet, CU = dry | No opened source. Holman, "Sound for Film and Television", 3rd ed., Focal Press 2010, ISBN 978-0-240-81330-1 exists (front matter listing in search); chapter/page for perspective not re-opened | B | not re-opened | NOT FOUND (numbers -4 dB >6 kHz, 22 % wet, 95 % dry, +2 dB @140 Hz) | hypothesis |
| Point of audition (Chion/Sonnenschein) | Search could not confirm Chion's edition or definition. Chion, "Audio-Vision", Columbia UP, 1994 (edition from the input file; unverified here) | B | not re-opened | NOT FOUND | hypothesis |
| Frequency masking: dynamic EQ dip 2.2 kHz Q 1.2, 2.5-3.5 dB; HPF 80-85 Hz | EBU Tech 3343 v4 (Nov 2023) opened `[pdftotext]`: covers loudness-to-dialogue ratio (LDR, "sometimes more than 15 LU" in cinematic content), not EQ or masking bands. Nothing found on the notch numbers | A | https://tech.ebu.ch/docs/tech/tech3343.pdf | PARTIAL (dialogue vs programme loudness is real; the EQ numbers are NOT FOUND) | hypothesis |
| Pixflow guide cited by the Blueprint | not opened | A | - | NOT FOUND | - |
| Three-layer composite hit bands (<80 Hz / 200-2 k / 4-10 k), <=50 ms | No source | - | - | NOT FOUND | hypothesis |
| Room tone band -32..-38 dBFS | Wikipedia "Room tone": qualitative only (record in same mic position, intercut with dialogue to smooth edits); no level | A (encyclopedia) | https://en.wikipedia.org/wiki/Room_tone | PARTIAL (idea yes, number NOT FOUND) | hypothesis |
| J-cut -0.4..-1.0 s, L-cut +0.5..+1.2 s | Wikipedia "J cut": definition only ("the audio from a following scene overlaps the picture from the preceding scene"); "no guidance on how long the overlap should be" | A | https://en.wikipedia.org/wiki/J_cut | PARTIAL (technique yes; durations NOT FOUND) | hypothesis |
| Pre-twist vacuum 0.8-1.2 s to -42 dBFS; micro-cue -22 dBFS; Shepard-tone outro | No source | - | - | NOT FOUND | hypothesis |
| Duck depth (conflict BP-53 6-12 dB vs plan 3-5 dB) | Search summaries only (CapCut guide starting duck 6-12 dB, attack 30-80 ms, release 250-700 ms; Vindral docs: -6..-12 dB "gentle dip", -20 dB typical): pages NOT opened. See section 17 | A (weak) | not opened | PARTIAL (snippet only) | hypothesis |

## 3. Music

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Leitmotif: theme tied to person/event/place; returns with its owner; instrumentation and tempo change by scene | Article about the Nerdwriter video on Howard Shore's LOTR score: four leitmotifs (Lothlorien, Ring, Shire, Fellowship) that "play off and into each other"; opened article has no embedded link. The video itself was not opened | A (about C) | https://theplaylist.net/watch-8-minute-video-essay-praises-the-magic-of-howard-shores-the-lord-of-the-rings-score-20160219/ | PARTIAL (concept supported; "never for the other side" and the 1/8-note beat grid are NOT FOUND) | hypothesis |
| Video essay (C) | "Lord of the Rings: How Music Elevates Story", Nerdwriter1, about 7:44 (from search listing only) | C | not opened (no YouTube URL obtained) | NOT FOUND (as opened) | needs C opened |
| Karlin & Wright "On the Track" (Routledge); Davis "Complete Guide to Film Scoring" (Berklee Press) | no page found or opened | B | not re-opened | NOT FOUND | hypothesis |
| Cut on beat within 1/8 note | no source | - | - | NOT FOUND | hypothesis |

## 4. 2D animation principles

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| The 12 principles list (squash/stretch, anticipation, staging, straight-ahead/pose-to-pose, follow-through/overlap, slow in/out, arc, secondary action, timing, exaggeration, solid drawing, appeal) | Wikipedia opened, attributes the list to Thomas & Johnston, "The Illusion of Life: Disney Animation", 1981 (1997 Hyperion reprint cited in a related article) | A (encyclopedia) + B (secondary-confirmed) | https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation ; https://en.wikipedia.org/wiki/Squash_and_stretch | SUPPORTED (list). Book chapter/page not re-opened | hypothesis until C opened (A + B-by-secondary is two types if the creator accepts a secondary confirmation) |
| Moving holds / blink every 2-4 s / foot-slide px / hold >2 s has a moving hold | not in any opened source (Williams, "The Animator's Survival Kit", not re-opened) | B | not re-opened | NOT FOUND | hypothesis, measured on own cartoons |
| Alan Becker "12 Principles of Animation" | Search results describe a series of 12 videos, each at most 3 minutes, based on Thomas and Johnston; no YouTube page opened | C | not opened | NOT FOUND (as opened) | needs C opened |

## 5. Lip-sync and identity measurement

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| SyncNet lip-sync offset and confidence | Chung & Zisserman, "Out of time: automated lip sync in the wild" (Oxford VGG) `[pdftotext]`: two-stream ConvNet, joint audio/mouth embedding learned from unlabelled data, "used to determine the lip-sync error"; offset found by sliding window over +-1 s; a "confidence score" is defined from distances. Photo/real faces only; cartoons not tested | A | https://www.robots.ox.ac.uk/~vgg/publications/2016/Chung16a/chung16a.pdf | SUPPORTED (method). Venue "ACCV workshops 2016" in the input is not shown on the PDF text I read: unverified | hypothesis |
| ArcFace cosine embeddings for identity | arXiv 1801.07698: Deng, Guo, Yang, Xue, Kotsia, Zafeiriou; additive angular margin; TPAMI version noted | A | https://arxiv.org/abs/1801.07698 | SUPPORTED (method). Threshold 0.65 on cartoon faces: NOT FOUND | hypothesis; threshold calibrate on own sheets |
| A/V sync tolerance (for lip-sync limits) | BT.1359-1 per secondary article: detectability audio leads +45 ms / lags -125 ms; acceptability +90 / -185 ms (sign: positive = audio ahead). Same page's glossary gives -60/+40 (EBU R37), conflicting with its main text. Study was on a newsreader | A (secondary of ITU) | https://www.forasoft.com/learn/audio-for-video/articles-audio/lip-sync-itu-r-bt-1359-tolerance-windows ; also https://arxiv.org/pdf/2212.01686 (search only, not opened) | SUPPORTED for BT.1359 numbers (primary ITU text not opened). "<= 80 ms" blueprint limit: NOT FOUND | hypothesis |
| C source | none | C | - | NOT FOUND | needs C |

## 6. Cartography

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Animated maps: viewers miss changes ("blink and you miss it"); keep frames simple; extra information competes for attention | Harrower, "Tips for Designing Effective Animated Maps", Cartographic Perspectives No. 44, Winter 2003, pp. 63-65 `[pdftotext]`. Quote: "individual frames of the animation should be relatively simple since small details are unlikely to be noticed" | A | https://cartographicperspectives.org/index.php/journal/article/download/cp44-harrower/pdf/2665 | SUPPORTED (replaces the Harrower & Fabrikant 2008 chapter, which was only seen via search; DOI 10.1002/9780470987643.CH4 reported) | hypothesis |
| Change ONE thing at a time; highlight before moving | Harrower 2003: "decay" images where features linger; "sequencing" depicts information in a logical, predefined sequence; let viewer slow/loop. The explicit "one change at a time" is NOT in the opened text | A | same | PARTIAL | hypothesis |
| Temporal legend / date chip | Harrower: temporal exaggeration so short events are not missed; no explicit date-chip rule | A | same | PARTIAL | hypothesis |
| Label placement (no overlap with lines, hierarchy by type) | Imhof, "Positioning Names on Maps", The American Cartographer 2(2), 1975, pp. 128-144 (translation of 1962 German essay). Only secondary summaries seen in search: names must not overlap other content, show feature extent, reflect hierarchy; Imhof says rules conflict. Primary NOT opened | A | not opened | PARTIAL (secondary, snippet) | hypothesis |
| Sequential/diverging/qualitative palettes, colour-blind-safe filter | ColorBrewer: scheme types sequential, diverging, qualitative; "colorblind safe" filter; Brewer, Harrower, Penn State | A | https://colorbrewer2.org/ | SUPPORTED | hypothesis (B Brewer "Designing Better Maps" not re-opened) |
| Min label 40/56 px, scale bar, one projection, 40 % dim, caps 3/4, altitude change 4-8 s | no source | - | - | NOT FOUND | hypothesis / house |
| MacEachren "How Maps Work" (Guilford) | cited inside Harrower 2003 as MacEachren 1995 ("perceptual power of motion ... decrease in the ability of map-readers to notice differences in non-dynamic visual variables") | B (via A) | Harrower 2003 p. 63 | PARTIAL | hypothesis |
| Kings and Generals map video (C) | not opened | C | - | NOT FOUND | needs C |

## 7. Visual lane balance

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Use the channel's own retention curve to tune lane caps | YouTube Help 9314415 (opened): Intro = share kept after the first 30 s; Top moments = almost no drop-off; Spikes = rewatched/shared; Dips = skipped/left. Key moments only for videos >= 60 s with >= 100 views; data takes 1-2 days | A | https://support.google.com/youtube/answer/9314415 | SUPPORTED (as measurement tool). 60 s / 90 s hard caps: NOT FOUND | hypothesis |
| McKee "Story" (scene = value change); Katz "Film Directing Shot by Shot" | not re-opened | B | not re-opened | NOT FOUND | hypothesis |

## 8. Cinematography

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Low angle reads strong/powerful | Wikipedia: "the effect of the low-angle shot is that it makes the subject look strong and powerful"; sole reference is a Dictionary.com entry; high-angle/vulnerability is NOT on the page | A (weak) | https://en.wikipedia.org/wiki/Low-angle_shot | PARTIAL (low = power only) | hypothesis |
| Long lens compression / intimacy, wide lens isolation | Wikipedia "Telephoto lens": groups "short/portrait" telephoto at 85-135 mm (35 mm format); says nothing on compression or wide-angle exaggeration | A | https://en.wikipedia.org/wiki/Telephoto_lens | PARTIAL (85 mm portrait class only) | hypothesis |
| 24/50/85 mm tiers | 85 mm is portrait-class (above); 24 and 50 not sourced | A | same | PARTIAL | hypothesis |
| 30-degree rule | Wikipedia: move camera >= 30 degrees between shots of the same subject, otherwise a jump cut; lens change <20 mm at same angle also reads as a jump ("20 mm/30 degree rule"). Cites Hurbis-Cherrier "Voice & Vision" 2nd ed. 2011, Corrigan & White "The Film Experience" 3rd ed. 2013, Murch "In the Blink of an Eye" 2001 p. 146. Mascelli/Katz NOT on the page | A (secondary B) | https://en.wikipedia.org/wiki/30-degree_rule | SUPPORTED | hypothesis (A + B-by-secondary) |
| Headroom, nose room, depth staging, frame balance | no opened source (Mascelli "The Five C's", Block "The Visual Story", Katz: not re-opened) | B | not re-opened | NOT FOUND | hypothesis |

## 9. Visual intensity curve

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Contrast makes intensity, affinity makes stillness; intensity graph follows the story | Only mirror/review pages seen in search (a blog review of Block "The Visual Story", 3rd ed., Routledge 2021); the earlier 2nd ed. Focal Press cited in the input. No primary or reliable page opened | B | not re-opened | NOT FOUND (secondary snippet only) | hypothesis |
| Bordwell & Thompson "Film Art" | not re-opened | B | not re-opened | NOT FOUND | hypothesis |

## 10. Editing

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Rule of Six order | nofilmschool (opened): emotion, story, rhythm, eye trace, 2D plane of screen, 3D space of action; sacrifice from the bottom up; emotion "51 %" more than the other five combined. Only the 51 % is on this page | A | https://nofilmschool.com/2016/11/6-rules-good-cutting-according-oscar-winning-editor-walter-murch | SUPPORTED (order, 51 %). Full set 51/23/10/7/5/4 seen in search snippet of a UT Austin wiki, not opened | hypothesis (A + B Murch "In the Blink of an Eye", 2nd ed., not re-opened) |
| Cut on action 2-4 frames after the motion begins; cut on the blink | the opened nofilmschool page does NOT cover cut-on-action or the blink | - | - | NOT FOUND | hypothesis |
| Dmytryk "On Film Editing" 1984 seven rules | Wikipedia page for the book gave 404 | B | not opened | NOT FOUND | hypothesis |
| 30-degree rule at cuts | see section 8 | A | see 8 | SUPPORTED | hypothesis |
| Eye-trace 0.10 vs 0.18; 6 % overscan, 12 % crop nudge | editmentor page cited by the Blueprint not opened | - | - | NOT FOUND (see section 17) | hypothesis |
| Handles 12-16 f, speed ramp 1.0/1.6/0.45 x 0.6 s, whip 8-10 f, wipe 10 f | no source | - | - | NOT FOUND | hypothesis |

## 11. Colour

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Match mean and std per channel between images | Reinhard, Ashikhmin, Gooch, Shirley, "Color Transfer between Images", IEEE CG&A 21(5), 2001, pp. 34-41, DOI 10.1109/38.946629 (bibliographic data from search results). Method in the l-alpha-beta space (not CIE LAB); mean and std per axis; common software ports use CIE Lab. Primary PDF not opened; one 404 | A | not opened (search summaries only) | PARTIAL (method known; citation data from search) | hypothesis |
| Blend <= 0.65 | the paper has no blend limit in anything seen | - | - | NOT FOUND | house/hypothesis |
| delta-E bands for hero swatches | no source | - | - | NOT FOUND | hypothesis |
| Hullfish 2nd ed. Focal; Van Hurkman "Color Correction Handbook" Peachpit | not re-opened | B | not re-opened | NOT FOUND | hypothesis |
| Vignette 12 %, grain `noise=c0s=5` | no source | - | - | NOT FOUND | hypothesis |

## 12. Voice selection

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Moderate pace helps attention and memory | Rodero, Journal of Advertising Research 60(3), Sept 2020 (ARF page, opened): 160/180/200 wpm tested, best 180 wpm; 200 adults, English and Spanish speakers; "phonological loop can fulfill its function" at 180. Search snippet (not opened): Rodero 2015, Media Psychology, recall best at 170-190 wpm | A | https://thearf.org/access-knowledge-2/publications/journal-of-advertising-research/do-your-ads-talk-too-fast-to-your-audio-audience-how-speech-rates-of-audio-commercials-influence-cognitive-and-physiological-outcomes/ | SUPPORTED for 180 wpm (ads, not explainers). See BP-01 in section 17 | hypothesis |
| Voice-difference margins (F0 >= 3 st, rate >= 15 %, centroid >= 20 %) | no source | - | - | NOT FOUND | hypothesis |
| Lowenthal & Platt "Voice-Over Voice Actor" | not re-opened | B | not re-opened | NOT FOUND | hypothesis |
| ElevenLabs voice guidance (C) | not found | C | - | NOT FOUND | needs C |

## 13. Packaging

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Test & Compare: up to 3 titles and thumbnails | YouTube Help 13861714 (opened): "up to 3 different titles and thumbnails"; titles only, thumbnails only or both; finishes within about two weeks; winner by watch time share (chosen over CTR) | A | https://support.google.com/youtube/answer/13861714 | SUPPORTED. The "three structural angles" are a house idea | hypothesis (A only) |
| Intro/top moments/spikes/dips mapped to segments | see section 7, same page 9314415 | A | https://support.google.com/youtube/answer/9314415 | SUPPORTED | hypothesis |
| Information-gap theory (Loewenstein 1994) | not opened | A | - | NOT FOUND (in this session) | hypothesis |
| Shorts length | YouTube Help 15424877 (opened): Shorts up to three minutes; square or vertical aspect; rule applies to standard channels for uploads after 2024-10-15 | A | https://support.google.com/youtube/answer/15424877 | SUPPORTED | hypothesis (A only) |
| TikTok/IG caps, Shorts windows per platform | not researched this round | - | - | NOT FOUND | hypothesis |
| Retention gates 60 %/50 %, twist <= 4.5 s | no source (YouTube page gives no thresholds) | - | - | NOT FOUND | hypothesis |

## 14. Mayer multimedia principles

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| The 12 principles | Lucidea blog (opened) lists: coherence, signaling, redundancy, spatial contiguity, temporal contiguity, segmenting, pre-training, modality, multimedia, personalization, voice, image (embodiment). Note: the "image" item says adding the speaker's image "doesn't necessarily improve learning", which differs from the repo row "embodiment (hosts gesture at the thing)" | A | https://lucidea.com/blog/mayers-12-principles-of-multimedia-learning | SUPPORTED (list). The embodiment row is NOT supported as worded | hypothesis; B Mayer "Multimedia Learning", 3rd ed., Cambridge UP 2020 not re-opened |
| Effect sizes (temporal contiguity d = 1.30; coherence 0.70; redundancy 0.87; spatial 0.79; segmenting 0.70; signaling and pre-training 0.46) | search snippet of a J. Computer Assisted Learning review; the review itself was not opened | A | not opened | NOT FOUND (as opened) | informational only |
| Pitt checklist, FutureLearn PDF | Pitt PDF HTTP 503; FutureLearn not opened | A | - | NOT FOUND | - |

## 15. Motion graphics

| rule / number | what the source says | type | URL / edition | verdict | proposed status |
|---|---|---|---|---|---|
| Ease-out on entry, ease-in on exit | Search results only (third-party Material token mirrors): emphasized decelerate for entering, cubic-bezier(0.05,0.7,0.1,1); emphasized accelerate for exiting, cubic-bezier(0.3,0,0.8,0.15); a Flutter port lists 400 ms enter / 200 ms exit. Official m3.material.io returned title only | A (secondary) | not opened (official); mirrors not opened | PARTIAL (snippet only). 200-400 / 150-250 ms: NOT FOUND from an opened page | hypothesis |
| Counter <= 10 increments/s; one element in motion; fixed HUD slot | no source | - | - | NOT FOUND | hypothesis |
| Krasner "Motion Graphic Design" (Focal) | not re-opened | B | not re-opened | NOT FOUND | hypothesis |

## 16. Other constants from `storage_recommendation`

| number | what an opened source says | type | URL | verdict | status |
|---|---|---|---|---|---|
| Universal Shorts safe zone 250/480/240/60 (Blueprint) vs BP-29 | Google official vertical-video example, 1080x1920: top 288, bottom 672, left 48, right 192 (from `safe_zone_2026-10-29.md`, which says the PDF image was read earlier in the day; I did NOT re-open it). The Blueprint's 250/480/240/60 has no source | A | services.google.com/fh/files/misc/universalsafezones-youtube.pdf (via the note) | 288/672/48/192 SUPPORTED by the note; 250/480/240/60 NOT FOUND | hypothesis (A only) |
| Frame rate | YouTube Help 1722171 (opened): upload at the recorded rate; common 24, 25, 30, 48, 50, 60 fps; audio AAC-LC/Opus, 48 kHz; no loudness target on that page | A | https://support.google.com/youtube/answer/1722171 | SUPPORTED (24 and 30 both accepted; no preference) | hypothesis |
| LUFS target | see section 17 | A | - | PARTIAL | hypothesis |
| Lip-sync <= 80 ms | see section 5 | A | - | PARTIAL | hypothesis |
| Event window 2.0-3.5 s, 4.0 s flag; breathing 0.4 Hz +-4 px; rack focus 0.4 s; occlusion wipe 10 f; handles; particles; 30 deg | only the 30-degree rule found (section 8); the rest no source | - | - | NOT FOUND | hypothesis |

---

## 17. Conflicts with existing repo rules: external evidence for each side (not resolved)

| conflict | evidence for side 1 | evidence for side 2 |
|---|---|---|
| -14 vs -16 LUFS (BP-50) | Wikipedia "Audio normalization" (search snippet, not opened) and Youlean (snippet): YouTube's preferred level is -14 LUFS, lowers louder audio, does not raise quieter audio. Frame.io (opened): "YouTube tends to shoot for -12 to -14 LUFS", "doesn't release exact values". Videvo (snippet): YouTube does not publish a standard | EBU Tech 3343 v4 section 9.2 Streaming (opened `[pdftotext]`): streaming "-20.0 to -16.0 LUFS" range and an example of -18 LUFS prepared before streaming, plus "-23 or -20..-16 LUFS" in a figure. YouTube's own help page 1722171 states no target | no official YouTube figure was found; both numbers are third-party or broadcast guidance |
| BP-01 wpm (repo 170 vs Blueprint 135-145) | Rodero 2020 (opened): best at 180 wpm among 160/180/200 (ads, 200 adults); Rodero 2015 snippet: recall best 170-190 wpm (radio news, not opened) | No opened source supports 135-145 wpm. Harrower is irrelevant here. Slow-pace evidence exists only in the sister repo's own viewer notes, not external |
| BP-53 duck (3-5 vs 6-12 dB) | Snippets only: CapCut guide starts at 6-12 dB; Vindral docs call -6..-12 dB "gentle", -20 dB typical | Snippet reading by the search tool: 3-6 dB is "subtle". No broadcast standard found for either |
| ED-04 / BP-43 (1.5 s fade vs hard-cut outro) | Nothing external opened on either | - (no source) |
| BP-31 (dissolves only at place/time change) vs 12 f dissolve on match cuts | No source opened | - |
| BP-30 eye-trace 0.10 vs 0.18 | editmentor page cited by the Blueprint not opened; Murch Rule of Six gives eye-trace only 7 % weight (secondary, UT wiki seen in search) | - (no numeric source) |
| BP-36/BP-40 event window 2.0-3.5 s vs 4.0 s flag | No source opened for either | - |
| fps 24 vs 30 | YouTube Help 1722171 (opened): 24, 25, 30, 48, 50, 60 all common; "upload at the rate recorded" | - (no external preference; repo decision) |
| Safe zone 250/480/240/60 vs BP-29 | Google example 288/672/48/192 (note) | Third-party organic estimates in `safe_zone_2026-10-29.md` (adaptlypost ~180/390/100, postplanify 120/300/96, wildandfree 150/400): unverified, not re-opened here |
| Perlin breathing vs BP-24; Calibri/Cinzel vs Fredoka/Inter; dossier stamp vs SC-11 | No external research done (creator-card items) | - |

## 18. "Areas missing from the Blueprint"

The file does not contain a list titled "17 areas missing". What it has: **17 `curriculum_gaps`** (one row-group each in sections 1-15; section 2 holds the perspective, masking and two-and-a-half gaps), and the inventory status counts **covered 8, partial 49, missing 21** of 78. The 21 `missing` inventory items (Mode B 20/80 compositor, composite-hit builder, pan field unused, shot-to-audio matrix, acoustic perspective/IR, zero-fade outro, archetypes 2/3/6/9/10/12, map laws 1/2/5, optical-flow trim, eye-trace auto-reframe, speed ramp, rack focus/particle layer, facial gates, one reverb tail per scene) are listed in `p3_craft.json` -> `inventory` with `status: "missing"`; the 17 gaps are the ones that needed external sources. If the "17 areas" refers to something else, it is not in the file.

## 19. Summary

Row counts by verdict (rows of sections 1-16; each table row counted once):

SUPPORTED 19, PARTIAL 18, NOT FOUND 39 (76 rows; "SUPPORTED" rows are mostly method or definition, rarely a project number).

Binding candidates under D-59: none yet. Every row has at most one verified source type (A). Type B was never re-opened (books), and
type C could not be opened at all (YouTube pages return no content in this environment).

Still needing a second source type:
- Type C (video) for every area: AI-lexicon, leitmotif (Nerdwriter LOTR essay named, not watched), animation (Alan Becker series named, not watched),
  cartography (Kings and Generals, not opened), visual intensity, voice casting, motion-graphics easing, two-and-a-half density.
- Type B confirmation (page or chapter) for: Murch "In the Blink of an Eye" (rule of six, 30-degree rule p. 146 per Wikipedia), Thomas & Johnston 1981,
  Holman 3rd ed. 2010, Chion 1994, Block, Mascelli, Katz, Dmytryk, Hullfish, Van Hurkman, Brewer, MacEachren, Krasner, Mayer 2020, Rodero.
- Type A primary (replace secondary): ITU-R BT.1359-1 text, Imhof 1975, Reinhard 2001 PDF, Harrower & Fabrikant 2008 chapter, m3.material.io tokens,
  the Google safe-zone PDF re-opened.
- No source of any type found for: all dB/Hz/ms/px constants in storage_recommendation except the 30-degree rule, ITU sync windows and Google safe zone.

Corrections to the input list: arXiv 2404.01268 and 2406.07016 carry different titles than `p3_craft.json`; Murch's "two and a half" is a
same-colour limit (five when spread); Mayer's last principle is about the speaker's image and the opened source says it need not help learning;
the Rodero source supports 180 wpm, not the repo's 170 nor the Blueprint's 135-145.
