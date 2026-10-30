# Craft sources from the Claude API (J3, 2026-10-30)

Opus 5.5 high with web search, one request per department, input = the department's craft checklist. Every URL below was returned by that response's web search results (`explainer_engine/llm/cite_check.py`); lines that cited any other URL were dropped (count per department in the heading). These are leads for a free, separate step (checklists/skills); **nothing here is binding** (D-59: two source types, and a person or the session must open the pages; 'snippet' rows were not read). Cost $5.56 of J3's $12.

---

## animation (lines dropped by the citation check: 0)

# Animation craft checklist: sources found for the 16 CRAFT-ANI rows

**Read this first**
- **The search tool stopped after 10 queries.** It hit its usage limit, so I never ran the planned searches for blink rate, foot sliding, lip-sync offset, SyncNet, ArcFace or cartoon identity thresholds. Where a row says NO SOURCE FOUND, it means I didn't search for it, not that no source exists.
- **I read only search extracts, not full pages.** Each result came back as an extract of about 1,500 characters, so every row below is marked "snippet". For YouTube results I saw only the title and description. I watched no videos.
- **Dates.** Where the extract showed no date, the table says "no date seen". Dates taken from a URL or from the page's metadata are labelled that way.
- **Rule values I can't check.** The checklist doesn't give the values of KP-12, KP-16, KP-29, BP-23, BP-132 or BP-133, so I can't say whether a source disagrees with those numbers. BP-107, BP-109 and D-55 are internal repository rules that no outside source can confirm.
- **One page left out.** A pdfcoffee.com page appears to host an unauthorised copy of *The Illusion of Life*. I left it out and suggest you don't use it.
- **Type labels.** "Article" covers web pages and documentation. "Book" covers listings and excerpts. "Video" covers video pages and transcripts. A page that transcribes a YouTube video is labelled video (transcript).

---

## CRAFT-ANI-01: squash and stretch keep the volume
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.studiobinder.com/blog/what-are-the-12-principles-of-animation/ | article | no date seen | snippet | Two rules for squash and stretch: "The object should never change volume." Also, more squash and stretch makes an object read as softer. | supports |
| https://learn.toonboom.com/modules/animation-principles/topic/squash-and-stretch-principle | article (vendor training) | no date seen | snippet | When you squash, you must stretch sideways in proportion, or the object seems to shrink. Volume must be kept throughout. Hard objects need less squash. | supports |
| https://www.animationmentor.com/blog/squash-and-stretch-the-12-basic-principles-of-animation/ | article | no date seen | snippet | Volume must be kept so the object doesn't seem to grow. It also says exact mathematical volume may not look right and can be cheated to taste. | partly (adds a tolerance: visual volume, not exact) |
| https://www.netguru.com/blog/illustrators-eye-12-principles-of-animation | article | no date seen | snippet | Uses Thomas and Johnston's half-filled flour sack: it squashes and stretches but never changes volume. | supports |
| https://www.cgspectrum.com/blog/12-principles-of-animation | article | metadata: published 2020-09-12, modified 2024-10-28 | snippet | Says it is important to keep the object's overall volume so it doesn't look unnatural. | supports |
| https://www.youtube.com/watch?v=9U2smn_golI | video | no date seen | snippet (description only) | Description says a key idea of this principle is to "maintain volume". | supports (description level only) |

**Verdict: TWO TYPES FOUND** (article and video). The video counts only on its description.

## CRAFT-ANI-02: anticipation before every big action (KP-12)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.animatron.com/blog/12-basic-principles-of-animation/ | article | no date seen | snippet | Almost nothing happens suddenly. Anticipation prepares the audience for the main action. | supports |
| https://www.nyfa.edu/student-resources/12-principles-of-animation/ | article | no date seen | snippet | Anticipation readies the viewer for an action and involves "a short pause before the act". | supports |
| https://ytscribe.com/v/uDqjIdI4bF4 | video (transcript of Alan Becker, "12 Principles of Animation (Official Full Series)") | no date seen | snippet | Shows a jump with no anticipation. Says no anticipation makes a weak punch. Describes stacking several levels of anticipation. | supports |

**Verdict: TWO TYPES FOUND.** No source says "every" big action, so the checklist's wording is stricter than the sources.

## CRAFT-ANI-03: staging, one idea read at a glance
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.nyfa.edu/student-resources/12-principles-of-animation/ | article | no date seen | snippet | Staging presents a scene so it clearly shows what is happening, through composition, lighting and camera angle. | partly |
| https://www.scribd.com/document/50432815/Principles-of-Animation | article (user-uploaded document, author unknown) | no date seen | snippet | Staging should clearly get an attitude or idea across. Background detail should not compete with the animation. | partly |
| https://ytscribe.com/v/uDqjIdI4bF4 | video (transcript) | no date seen | snippet | Becker shows an example of bad staging, then reworks the scene "with the staging treatment". | partly |

**Verdict: TWO TYPES FOUND** (topic level). No source gives "at a glance" as a measurable test.

## CRAFT-ANI-04: pose to pose; keyframe and next pose carry the action, the model fills between
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | article | no date seen | snippet | Computer animation still uses pose to pose because it helps composition. The other principles still need to be checked. | supports |
| https://www.scribd.com/document/50432815/Principles-of-Animation | article | no date seen | snippet | Straight-ahead animation can lose size, volume and proportion, but it has spontaneity. | partly (the trade-off) |
| https://books.google.com/books/about/The_Animator_s_Survival_Kit.html?id=hARi0QEACAAJ | listing of a DVD masterclass (Richard Williams, Blue Sky Studios, 2008); book or video, unclear | 2008 | snippet | Chapter list includes "Extremes and Inbetweens" and "The Unthinking Assistant". | partly (topic only) |

**Verdict: ONE TYPE** (article). The Williams listing is a library entry for a video course, so you need to decide which type it counts as.

## CRAFT-ANI-05: follow-through and overlapping action (KP-16)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | article | no date seen | snippet | Loose parts keep moving after the character stops, then are pulled back toward the centre of mass, with damped oscillation. | supports |
| https://cgiacademyhub.com/blog/overlapping-action-drag-animacion-3d | article | no date seen | snippet | When every part freezes on the same frame, overlap and drag are missing. Hands, hair and cloth should arrive late. Each swing is smaller than the last. | supports |
| https://dantes.io/resource/the-animators-survival-kit | book (catalogue page for Williams' book) | no date seen | snippet | Lists overlapping action among the book's topics. | partly (topic only) |

**Verdict: ONE TYPE** (article). The book counts only through a catalogue line.

## CRAFT-ANI-06: slow in and slow out on limbs, not only on the camera (BP-23)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | article | no date seen | snippet | Fewer drawings in the middle of a move to show faster action (the easing idea). | partly |
| https://www.youtube.com/watch?v=fQBFsTqbKhY | video ("6. Slow In & Slow Out – 12 Principles of Animation"; a school handout attributes the series to Alan Becker) | no date seen | snippet (title and description) | Part 6 of the series. Content not seen. | partly (topic only) |
| https://books.google.com/books/about/The_Animator_s_Survival_Kit.html?id=hARi0QEACAAJ | listing of Williams' DVD course | 2008 | snippet | Chapter "Easing out and Easing In". | partly |

**Verdict: TWO TYPES FOUND** (topic level only). No source covers the "limbs, not only camera" part.

## CRAFT-ANI-07: actions move on arcs
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.animationexploration.org/2020/01/07/fundamentals-flipped/ | article (lecture notes) | 7 Jan 2020 (on page) | snippet | Puts arcs among the fundamentals most useful to spot in finished work. | partly |
| https://learn.toonboom.com/modules/animation-principles/topic/squash-and-stretch-principle | article | no date seen | snippet | The module has an "Arcs of Rotation Principle" topic (title only). Also says living shapes don't move rigidly from position to position. | partly |
| https://books.google.com/books/about/The_Animator_s_Survival_Kit.html?id=hARi0QEACAAJ | listing of Williams' DVD course | 2008 | snippet | Chapter "Arcs". | partly |

**Verdict: ONE TYPE** (thin). None of the extracts I saw actually defines the rule.

## CRAFT-ANI-08: secondary action (hair, cloth, breath) is free (KP-29)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.youtube.com/watch?v=MjBHWw1TbP4 | video ("8. Secondary Action – 12 Principles of Animation") | no date seen | snippet (title) | Topic only. | partly |
| https://www.oreilly.com/library/view/blender-2-5-character/9781849513203/ch09s03.html | book (excerpt from *Blender 2.5 Character Animation Cookbook*) | no date seen | snippet | The table of contents includes "It's time for secondary actions". | partly |
| https://cgiacademyhub.com/blog/overlapping-action-drag-animacion-3d | article | no date seen | snippet | Files hands, hair and cloth that arrive late under overlapping action and drag, not secondary action. | contradicts (the checklist files these under the wrong principle) |
| https://www.animationexploration.org/2020/01/07/fundamentals-flipped/ | article | 7 Jan 2020 | snippet | Says students often confuse follow-through, overlapping action and secondary action. | partly |

**Verdict: TWO TYPES FOUND** (topic level). Hair and cloth lag probably belongs under ANI-05. Breathing comes up under moving holds (ANI-13). No source supports "is free".

## CRAFT-ANI-09: timing, shot rhythm and hold share (BP-107, BP-109)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://books.google.com/books/about/Timing_for_Animation.html?id=E0epwBql7p4C | book (Google Books listing, Whitaker and Halas, Taylor & Francis) | 2002 edition | snippet | Contents include "Timing a Slow Action", "Timing a Fast Action" and "Timing for Television vs Timing for Feature Films". | partly |
| https://www.perlego.com/book/2061486/timing-for-animation-40th-anniversary-edition-pdf | book (listing, 40th anniversary edition, with Tom Sito) | no date seen | snippet | Contents include "The Basic Unit of Time in Animation" and "The Use of Timing to Suggest Mood". | partly |
| https://www.youtube.com/watch?v=BarOk2p38LQ | video ("9. Timing – 12 Principles of Animation") | no date seen | snippet (title) | Topic only. | partly |
| https://www.scribd.com/document/50432815/Principles-of-Animation | article | no date seen | snippet | Says most animation is done on twos (one drawing for every two frames). | partly |

**Verdict: TWO TYPES FOUND** for timing as a principle. **NONE** for the BP-107 and BP-109 values, which are internal measurements of the creator's own cartoons.

## CRAFT-ANI-10: exaggeration in the caricature, never in the facts
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://learn.toonboom.com/modules/animation-principles/topic/squash-and-stretch-principle | article | no date seen | snippet | More squash and stretch reads as more cartoony. There is an Exaggeration topic (title only). | partly |
| https://www.animatron.com/blog/12-basic-principles-of-animation/ | article | no date seen | snippet | Even slight exaggeration of shortening and widening adds a realistic feel. | partly |

**Verdict: ONE TYPE.** The "never in the facts" part is an editorial rule. I found no source for it.

## CRAFT-ANI-11: solid drawing, no duplicated or missing limbs
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://kcdd78688wordpress.wordpress.com/2019/02/14/twelve-principles-of-animation/ | article (student blog) | 14 Feb 2019 (URL) | snippet | Solid drawing makes forms feel three-dimensional, with volume, weight and balance. | partly |
| https://www.scribd.com/document/50432815/Principles-of-Animation | article | no date seen | snippet | The basics of form, weight, volume and solidity apply. | partly |

**Verdict: ONE TYPE.** The check for AI artefacts (duplicated or missing limbs) has no source.

## CRAFT-ANI-12: appeal, the hero stays on model (D-55)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.animatron.com/blog/12-basic-principles-of-animation/ | article | no date seen | snippet | Appeal means the viewer finds the character real and interesting, not necessarily likeable. | partly |
| https://kcdd78688wordpress.wordpress.com/2019/02/14/twelve-principles-of-animation/ | article | 14 Feb 2019 (URL) | snippet | Appeal means charisma. Vary shapes and keep designs simple, because too much detail is harder to animate. | partly |

**Verdict: ONE TYPE.** I found nothing on keeping a character on model.

## CRAFT-ANI-13: a held character breathes; blink cadence and a moving hold on long holds (BP-132)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation | article | no date seen | snippet | A moving hold animates between two very similar poses, such as breathing, so the character doesn't look lifeless. | supports (no numbers) |
| https://www.oreilly.com/library/view/blender-2-5-character/9781849513203/ch09s03.html | book (excerpt) | no date seen | snippet | A character shouldn't stay completely still at the end of an action, or it looks frozen. Notes this matters most in CG, which runs on ones. | supports (no numbers) |
| http://fliponline.blogspot.com/2007/02/quick-trick-moving-holds.html | article (blog) | 6 Apr 2007 | snippet | Suggests a short moving hold after a blink to settle the eyelid. Build a basic moving hold by copying the last pose's keys "20 or 30 frames later". | partly (the number is how far apart the keys sit, not a 2 s trigger) |
| https://animationapprentice.blogspot.com/2018/10/how-to-keep-your-cg-characters-alive.html | article (blog) | 22 Oct 2018 | snippet | In 2D, a held drawing can be very attractive. CG characters, by contrast, "die" when they stop. | contradicts (if the rule is applied to every 2D hold) |
| https://digicel.net/animation-holds/ | article | no date seen | snippet | A deliberate still pose can be powerful. Use a moving hold only when the scene needs life but no new action. | partly / contradicts "always" |

**Verdict: TWO TYPES FOUND** for the moving hold as a qualitative idea. **NONE** for "blink every 2–4 s" or "moving hold after 2 s". Two sources warn that static holds work in 2D.

## CRAFT-ANI-14: a planted foot does not slide
**NO SOURCE FOUND.** I didn't search this because of the limit.
**Verdict: NONE**

## CRAFT-ANI-15: lip-sync offset and confidence measured (BP-133)
| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://books.google.com/books/about/Timing_for_Animation.html?id=E0epwBql7p4C | book (listing) | 2002 edition | snippet | Has a chapter "Synchronizing Animation to Speech" (p. 125). Content not seen. | partly (topic only) |

I found nothing on the SyncNet method or any millisecond limit; those searches never ran.
**Verdict: NONE** for the rule. There is only one topic-level book listing.

## CRAFT-ANI-16: identity score against the hero sheet (BP-133)
**NO SOURCE FOUND** for ArcFace or for any cartoon identity threshold. I didn't search this because of the limit.
**Verdict: NONE**

---

## Sources useful beyond the rows
- https://archive.org/details/illusionoflifedi0000thom is the Internet Archive's lending copy of *The Illusion of Life* (Hyperion, 1995, 575 pages, access restricted). Borrowing it and citing page numbers is the most direct way to turn rows 01–12 into real book-type sources.
- https://www.mhscomputergraphics.com/uploads/1/5/1/3/1513764/a1-00_12_principles_of_animation.pdf is a school handout that maps each principle to an Alan Becker video. It names video IDs for anticipation, staging, pose to pose, follow-through, arcs, exaggeration, solid drawing and appeal. I haven't listed them because no search returned them as results. Searching for them would give the video type for ANI-04, 05, 07, 10, 11 and 12.
- http://www.theanimatorssurvivalkit.com/volumes_1_4.html is the official page for Williams' *Animator's Survival Kit – Animated* DVD set: Starting Right, Timing and Spacing, Working Methods, More Timing More Spacing. It counts as a practitioner's video course.
- https://www.sciencedirect.com/book/9780240521602/timing-for-animation and https://www.awn.com/animationworld/timing-animation-harold-whitaker-and-john-halas are the publisher page for the 2009 second edition of *Timing for Animation* and an AWN review of the book. Useful for timing, holds and speech sync.
- https://www.linkedin.com/pulse/why-all-animators-need-master-moving-hold-time-n-space and https://rbossert27.wixsite.com/mysite-2/post/the-moving-hold give more practice on moving holds. Bossert advises moving body parts at different speeds and warns that too much drift looks floaty.

**Searches to run next session:** human blink-rate studies (for BP-132), foot sliding or foot contact, AV-sync tolerance standards (ITU-R BT.1359, EBU R37), Chung and Zisserman's "Out of time" (SyncNet) paper, Deng et al.'s ArcFace paper, and face recognition on anime or cartoon characters.

---

## cartography (lines dropped by the citation check: 0)

# Cartography checklist: sources found (search run cut short)

**Read this first.**
- **Search budget.** The search tool stopped working after about 14 queries. Several planned searches never ran. These include all the video searches for colour, scale, projection and camera, and searches on zoom and fly-to timing (van Wijk & Nuij, Mapbox `flyTo`). So a NONE or ONE TYPE for CART-03, 05, 06 and 07 means "not searched enough." It does not mean "no source exists."
- **What "read" means here.** I could not open any page directly. The search tool returns a block of text pulled from each page. I mark a source as **extract** when that block contained real body text, and **snippet** when it held only metadata or a teaser. Nothing below was read in full.
- **Dates.** Ages like "N days ago" in the search results show when the page was crawled, not when it was published. I only give a date when the page text itself showed one.

---

## CRAFT-CART-01: a map frame stays simple (label and unit caps, inactive terrain dimmed) [BP-124]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://cartographicperspectives.org/index.php/journal/article/view/cp44-harrower | article (journal) | Published 2003-03-01 | snippet (metadata only) | Harrower, "Tips for Designing Effective Animated Maps," *Cartographic Perspectives* 44, pp. 63–65, DOI 10.14714/CP44.516. Confirms the source the checklist cites; no body text. | partly (citation only) |
| https://cartographicperspectives.org/index.php/journal/article/download/cp44-harrower/pdf/2665 | article (journal PDF) | Number 44, Winter 2003 | extract (garbled scraps) | Broken fragments of the original. They include "Many animated maps try to do too [much]," a point that readers "do not know *where*" to look, and that effective animated maps are often highly [simplified]. Consistent with the checklist's summary, but the scraps give no numbers. | partly |
| https://www.researchgate.net/publication/228897062_Human_interaction_with_animated_maps_The_portrayal_of_the_passage_of_time | article (secondary) | no date in extract | extract | Says many animations are too complex and too fast to perceive accurately, and credits Harrower (2003) with the need for animation without too much detail: "include as few details as possible to be effective." | supports (the principle, not the caps) |
| https://www.researchgate.net/publication/228412707_Effects_of_Animations_in_Zooming_and_Panning_Operations_on_Web_maps_A_Web-based_Experiment | article (secondary) | no date in extract | extract | Repeats that Harrower stresses animations without too many details. | partly |
| https://nellomaps.com/2021/01/10/principles-of-geovisualization-in-map-animations/ | article (blog) | 2021-01-10 (from the URL) | extract | Lists Harrower's four kinds of change and warns that overusing animation variables risks exceeding the viewer's capacity to process information. | partly |

**Not found:** any number for a label cap or unit cap, and any source for "dim inactive terrain."
**Verdict: ONE TYPE** (article only; the caps have NO SOURCE)

---

## CRAFT-CART-02: one change at a time; highlight the changed thing before it moves [BP-124]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.researchgate.net/publication/233615293_Change_Blindness_in_Animated_Choropleth_Maps_An_Empirical_Study | article (journal, CaGIS) | 2011 (year shown in a citing paper's reference list) | extract (fragments) | Fish, Goldsberry & Battersby. Viewers are often change-blind and regularly fail to notice basic changes in animated choropleth maps. The study also tested tweening. | partly (supports the reason for the rule) |
| https://github.com/tmcw/perception | article (curated research summary) | no date | extract | Summary of Fish et al.: people miss abrupt colour and shape transitions, and "Animating value changes improves the awareness and measurement of change." | partly (supports animating or flagging the change) |
| https://www.tandfonline.com/doi/full/10.1080/15230406.2017.1308836 | article (journal) | no date in extract | extract | Removing unnecessary change signals and simplifying patterns should help viewers spot important changes they would otherwise miss. Cites Goldsberry & Battersby's point that possible transitions multiply as the number of classes grows. | partly (closest to "one change at a time") |
| https://arxiv.org/html/2202.11562 | article (preprint) | no date in extract | extract | Cites Goldsberry & Battersby's three levels of change detection: noticing a change, telling what kind it is, and understanding what it means. Says users should be able to follow changes, not just notice them. | partly |
| https://doi.org/10.3390/ijgi11050273 | article (journal, IJGI) | no date in extract | extract | Eye-tracking study: viewers mostly watched the centre of the map and only now and then looked at the edges. This is linked to change blindness. | partly (suggests putting changes centrally or flagging them) |

**Not found:** an explicit "one at a time" rule, or "highlight before it moves." This matches the checklist's own PARTIAL.
**Verdict: ONE TYPE** (article)

---

## CRAFT-CART-03: a temporal legend or date chip whenever map time advances [ED-15]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://geography.name/temporal-animated-maps/ | article | no date | extract | States that "Temporal legends should be included in any animated map of temporal data." Names three kinds: digital clock, cyclical time wheel, linear bar. Graphic legends show both the current moment and where it sits in the whole run. | **supports** (the clearest statement found) |
| https://www.researchgate.net/publication/228742648_Cartographic_animation_and_legends_for_temporal_maps_Exploration_and_or_interaction | article (conference paper) | ICC 1997 (shown on the record below) | extract (fragments) | Kraak, Edsall & MacEachren. The temporal legend tells the time (linking display time to world time) and can let the viewer move through time. Compares clock and slide-bar legends, and warns that some legend types distract from the main display. | supports |
| https://research.utwente.nl/en/publications/cartographic-animation-and-legends-for-temporal-maps-exporation-a | article (repository record) | 1997, Stockholm, ICA | snippet (metadata) | Confirms the bibliographic details of the Kraak et al. paper. | partly (citation) |
| https://en.wikipedia.org/wiki/Animated_mapping | article (encyclopedia) | no date | extract | Temporal maps should have a legend that tells the time and lets users move through it. Animated legends can distract, so they should sit unobtrusively. | supports |
| https://www.researchgate.net/publication/228897062_Human_interaction_with_animated_maps_The_portrayal_of_the_passage_of_time | article | no date in extract | extract | Surveys ways to show time: analog clock hand, sliding map, legends below the map. Notes that a temporal legend as wide as the map may be easier to read than a small one. | partly (how, not whether) |
| https://link.springer.com/chapter/10.1007/978-3-540-36651-5_22 | book (publisher's chapter page: Kraak 2007, in *Multimedia Cartography*) | 2007 | snippet (only the reference list showed) | Chapter "Cartography and the use of animation." Its reference list cites Kraak et al. 1997 on temporal legends. The extract does **not** state the rule. | lead only; does not support yet |
| https://pro.arcgis.com/en/pro-app/latest/help/mapping/animation/animate-through-time.htm | article (software docs) | no date | extract | ArcGIS Pro builds time animations from time-aware keyframes and a time slider. A tool convention; it does not require an on-screen legend. | partly |

**Not found:** a "date chip" rule as such.
**Verdict: ONE TYPE** (article; the Springer book chapter would need opening to count)

---

## CRAFT-CART-04: labels never cross a line feature, keep one offset and a halo, size by feature class [P-64]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://courses.ems.psu.edu/geog486/node/557 | article (university course text, Penn State GEOG 486) | no date | extract | Labels should follow line features but not cross perpendicular lines; place labels above lines; avoid labelling across boundaries where sensible. If a label must cross, keep it legible. | partly: says "generally" and "avoid," **not "never"** |
| https://colorado.pressbooks.pub/makingmaps/chapter/typography/ | book (open textbook *Making Maps*, ch. 12) | no date | extract | Halos help labels stand out but should not be too large. For labels that must cross roads, rivers or boundaries, use halos "but minimize the frequency." | partly; **softer than the checklist**: crossing is allowed but kept rare, so "never" is stricter than this source |
| https://slcc.pressbooks.pub/maps/chapter/9-4/ | book (open textbook, §9.4) | no date | extract | Keep label orientation consistent. Avoid overprinting; if you can't, use a halo, mask, callout or shadow. Line labels go above their feature without touching it and read left to right. | supports (halo, offset) |
| https://mlpp.pressbooks.pub/flexiblegisworkbookpro/chapter/1-6-label-features/ | book (open workbook) | no date | extract | Point labels sit at one corner of their symbol, not directly in line with it. Line labels follow the line and are never upside down. A halo is the most common label effect. | supports (one offset, halo) |
| https://docs.os.uk/more-than-maps/geographic-data-visualisation/guide-to-cartography/text-on-maps | article (Ordnance Survey cartography guide) | no date | extract | Text for linear features goes alongside and parallel to the feature, not touching it. Road and river labels should not cross junctions. A small halo is fine but must not hide key detail. | supports |
| https://en.wikipedia.org/wiki/Labeling_(map_design) | article (encyclopedia) | no date | extract | Lists the aims of association and conflict avoidance. Labels crossing symbols are less legible; halos or masks are common where overlap can't be avoided. | partly |
| https://cartographicperspectives.org/index.php/journal/article/download/cp60-kern-brewer/pdf | article (journal, Kern & Brewer) | Number 60, Spring 2008 | extract | Says Imhof (1962, 1975) compiled the first set of label-placement rules, later extended by others. Quotes Imhof's preferred point position, to the right of the symbol (Imhof 1975, p. 131). | partly (secondary for Imhof; the "one offset" idea) |
| https://scispace.com/papers/positioning-names-on-maps-1wppkck2fy | article (abstract page) | 1975 (Vol. 2, Iss. 2, pp. 128–144) | snippet (abstract only) | Imhof's abstract: each name has only one best position on the map. | partly; the primary is still unopened, as the checklist says |
| https://books.google.com/books/about/Designing_Better_Maps.html?id=7isZAQAAMAAJ | book (Brewer, *Designing Better Maps*, ESRI Press) | 2005 | snippet (book listing) | Description says the book covers halos and using text styling to show feature location, category and hierarchy. | partly (the closest thing to "size by feature class") |
| https://www.youtube.com/watch?v=xRx2QkevzJQ | video (software tutorial) | no date in extract | snippet | Short ArcMap tutorial on matching a label's halo colour to the fill behind it. Technique only; not a practitioner stating the rule. | partly (weak) |

**Verdict: TWO TYPES FOUND** (article + book).
- **Contradiction:** the sources say avoid or minimise crossings; none says *never*.
- The open textbooks are classed as "book." That is debatable for your project's rules.
- The only video is weak.

---

## CRAFT-CART-05: sequential or diverging palettes for quantities; colour-blind-safe faction pairs, never colour-only [D-22]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/ColorBrewer | article (encyclopedia) | no date | extract | ColorBrewer launched in 2002 (Brewer, Harrower, Penn State). Schemes are suggested by data type (sequential, diverging, qualitative), with colour-blind-safe options. Cites Olson & Brewer 1997 on map users with colour-vision impairments. | supports |
| https://sounny.github.io/colorbrewer/version2/ | article (tool page; **a github.io mirror, not the official ColorBrewer site**) | no date | extract | Tool interface: nature of data (sequential, diverging, qualitative) plus filters for colour-blind safe, print friendly and photocopy safe. | supports (confirm against the official site) |
| https://www.strandbooks.com/designing-better-maps-a-guide-for-gis-users-9781589484405.html | book (retailer listing; Brewer, *Designing Better Maps*, 2nd ed., Esri Press) | © 2015 | extract (listing) | Description says the book covers colour selection and describes Brewer's ColorBrewer application. | partly (topic only; no rule text) |
| https://www.esri.com/about/newsroom/announcements/new-esri-book-teaches-the-principles-of-good-map-design | article (publisher news) | no date in extract | extract | Announcement of the 2nd edition: covers colour selection and has a section on ColorBrewer. | partly |

**Not found:** "never colour-only" (pairing colour with a pattern, label or shape).
**Verdict: TWO TYPES FOUND** for the palette-type rule, but the book side is a listing that names the topic only. Opening a page of Brewer's book would make it firm. "Never colour-only": NO SOURCE FOUND.

---

## CRAFT-CART-06: one projection and north-up per episode; scale bar on meso and micro maps; legend only with more than two symbol classes [no BP]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.esri.com/about/newsroom/announcements/new-esri-book-teaches-the-principles-of-good-map-design | article | no date in extract | extract | Says Brewer's book covers basemaps, legends, scales and projections. No rule given. | lead only |
| https://slcc.pressbooks.pub/maps/chapter/9-4/ | book (open textbook) | no date | extract | Says map elements should be used carefully and guided by purpose, audience and scale. No specifics in the extract. | lead only |

**Verdict: NONE.** NO SOURCE FOUND for any of the three sub-rules. The search budget ran out before I could search for map elements, scale bars, north arrows or legends.

---

## CRAFT-CART-07: a change of map altitude takes its eased duration [BP-125, Blueprint 4–8 s]

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.researchgate.net/publication/228412707_Effects_of_Animations_in_Zooming_and_Panning_Operations_on_Web_maps_A_Web-based_Experiment | article | no date in extract | extract | A web experiment on animated zoom and pan. The extract lists duration as one of the dynamic variables but gives **no** timing values. | lead only |

**Verdict: NONE.** NO SOURCE FOUND for 4–8 s. The planned searches (van Wijk & Nuij 2003 on smooth zooming, Mapbox `flyTo` duration and speed, ArcGIS fly-through timing) never ran.

---

## CRAFT-CART-08: map type follows the style bible (Fredoka, Inter), not the Blueprint's set [no BP]

**NO SOURCE FOUND.** This is a repository rule; it settles an internal conflict rather than following outside craft guidance. I did not search for it. External sources would only back general type advice, such as a consistent hierarchy, which CART-04 already covers.
**Verdict: NONE** (an outside source may not be needed)

---

## Useful sources beyond the checklist rows
- https://www.researchgate.net/publication/220144122_The_Cognitive_Limits_of_Animated_Maps (extract): summarises Mayer's multimedia principles. Two matter for narrated map videos. Spatial contiguity: put on-screen text near what it explains. Redundancy: use animation plus narration rather than also repeating the narration as on-screen text. The extract also has the advice "split the legend elements, but make it close to the explained elements." This affects where to put date chips and legends.
- https://doi.org/10.3390/ijgi11050273: its reference list points to Battersby & Goldsberry 2010, "Considerations in Design of Transition Behaviors for Dynamic Thematic Maps" (*Cartographic Perspectives* 65). That paper is a likely firmer source for CART-02 (not opened).
- https://cartographicperspectives.org/index.php/journal/article/download/cp60-kern-brewer/pdf: a route to Imhof's 1975 rules and to Wood (2000), who extended them. Useful for upgrading CART-04 from secondary summaries.
- https://www.researchgate.net/publication/228897062_Human_interaction_with_animated_maps_The_portrayal_of_the_passage_of_time: a catalogue of ways to show the passage of time. Useful design options for a date chip.
- https://geography.name/temporal-animated-maps/: also says frame rates as low as 5 fps can give a passable animation effect, about 24 fps looks smooth. Relevant to how fast map steps advance.

## Next steps to make rules binding
1. **Video searches.** Look for talks by working cartographers on animated maps, map colour, and labelling (for example, conference talks).
2. **CART-07 timing.** Look up van Wijk & Nuij 2003 and the Mapbox or ArcGIS docs for zoom and fly-to durations.
3. **Open Brewer's book.** A Google Books preview page of *Designing Better Maps* would cover CART-05 and CART-06 as a book source.

---

## cinematography (lines dropped by the citation check: 0)

I ran out of search budget after about 14 queries. Searches covered only rows **CIN-01 to CIN-04**, plus a few hits that happened to touch CIN-06 and CIN-08. Rows **CIN-05, 06, 07, 09, 10 and 11 got no searches of their own**. They are marked NO SOURCE FOUND because they weren't searched, not because sources don't exist.

**How to read the tables:**
- **"Read or snippet":** I didn't open any full page. Every entry is the search engine's extract of the page, about 1,600 characters.
- **Dates:** No extract showed a publication date, except SceneOS (see the last list). So "date" gives the search index's page age (for example "idx ~450 d"). That is not a date shown on the page.
- **No inline citations:** The results came back through a code tool without citation indices, so each claim is tied to the URL in its row instead.

---

## CRAFT-CIN-01: lens tier motivated by the beat (long = compression, wide = space)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://www.videomaker.com/how-to/shooting/composition/what-is-lens-compression/ | article | no date (idx ~1364 d) | snippet | Long lenses make foreground and background look closer; wide lenses do the opposite and stretch distance. **But it also says telephoto lenses "do not cause compression inherently."** | partly |
| https://petapixel.com/is-lens-compression-fact-or-fiction/ | article | no date (idx ~1694 d) | snippet | Says compression comes from the camera-to-subject distance, not the focal length. It is just easier to see on a long lens. | **contradicts the mechanism** (the visual tendency still holds) |
| https://www.studiobinder.com/camera-shots/camera-lenses/telephoto-lens-shot/ | article | no date (idx ~370 d) | snippet | Telephoto is about 70 mm and up and is known for compressing space. Wide is about 24–35 mm. | supports |
| https://www.premiumbeat.com/blog/various-focal-lengths-for-images/ | article | no date (idx ~1736 d) | snippet | Wide angle greatly exaggerates depth and z-axis movement. Telephoto squeezes foreground, mid-ground and background together. **Its tiers differ:** wide 21–35 mm, telephoto 135 mm+. | supports (tier boundaries disagree with StudioBinder and Artlist) |
| https://artlist.io/blog/telephoto-lens/ | article | no date (idx ~1603 d) | snippet | Telephoto means over 70 mm. Compression makes subjects at different distances look similar in size. Normal is about 50 mm. | supports |
| https://www.indepthcine.com/videos/focal-length | video (companion page of an In Depth Cine video essay) | no date (idx ~284 d) | snippet | 35–50 mm is "normal"; wide lenses distort space and telephoto lenses compress it. | supports |
| https://www.youtube.com/watch?v=Y0TKVDlOGk4 | video | no date (idx ~2488 d) | snippet | The description says focal length affects distortion, perspective, compression and depth of field. | partly |
| https://www.youtube.com/watch?v=Rpc1mYfPips | video | no date (idx ~716 d) | snippet | "30 Filmmaking Tips, Day 11": the focal length you choose shapes the story. The extract is cut off before the breakdown. | partly |

**Verdict: TWO TYPES FOUND (article + video).** No book was found. Two cautions: tier boundaries vary between sources (70 vs 135 mm), and PetaPixel and Videomaker say compression is really caused by distance.

## CRAFT-CIN-02: camera height low / eye / high motivated (low reads strong)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Low-angle_shot | article | no date | snippet | A low-angle shot makes the subject look "strong and powerful." | supports |
| https://www.studiobinder.com/blog/types-of-camera-shot-angles-in-film/ | article | no date (idx ~493 d) | snippet | Low and high angles show power between characters and are often used as a pair. | supports |
| https://www.videomaker.com/how-to/shooting/composition/your-complete-guide-to-camera-angles/ | article | no date (idx ~1298 d) | snippet | High and low angles suggest power or the lack of it. | supports |
| https://www.researchgate.net/publication/352135520_The_influence_of_camera_angle_in_film_narratives | article (academic) | no date seen | snippet | Review: "consistent evidence" of a camera-angle effect on how powerful a subject seems. | supports |
| https://experimental.psychologie.uni-mainz.de/files/2024/06/2018BaranowskiHecht_Camera_Angle.pdf | article (academic) | 2018 (inferred from the file name only) | snippet | Viewers judge angles relative to each other, and the effect shows up only when angles are used sparingly. | partly (the effect is relative, not absolute) |
| https://www.sciencedirect.com/science/article/pii/S2451958823000180 (also on ResearchGate: https://www.researchgate.net/publication/370074801_The_impact_of_camera_usage_and_angle_on_perceptions_of_power_during_videoconferencing) | article (academic) | no date (idx ~1292 d) | snippet | Calls the relationship "complex." It cites a 2023 study in which a *higher* angle went with higher perceived power. | **contradicts in part** |
| https://www.creatoressentials.com/glossary/camera-angle/ | article | no date | snippet | Lists as a common mistake assuming that every low angle means power and every high angle means weakness. | partly / cautions |
| https://youtube.com/watch?pp=0gcJCfcAhR29_xXO&v=ZwDjq9sUEII | video | no date (idx ~2097 d) | snippet | "Power" camera angles: using high and low shots to empower or isolate people. | supports |
| https://videohighlight.com/v/wLfZL9PZI9k | video (third-party summary of a YouTube video, "Shot List, Ep. 3") | no date (idx ~842 d) | snippet | A low angle sits below the subject's eyeline and makes the subject look powerful. | supports |
| https://www.robertcmorton.com/the-5-cs-of-cinematography/ | article (summary of Mascelli's 1965 book) | no date (idx ~224 d) | snippet | Mascelli: a three-quarter low angle with a wide lens adds speed and power to moving vehicles. | partly |

**Verdict: TWO TYPES FOUND (article + video).** The research says "low = strong" depends on context and on how angles are used relative to each other. The critic should accept a motivated exception.

## CRAFT-CIN-03: two shots of one subject in a row change angle by 30° or lens by 20 mm

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/30-degree_rule | article | no date | snippet | Moving less than 30° can look like a jump cut. A focal-length change of less than 20 mm feels the same, which is why it is called the "20 mm/30 degree rule." | supports both numbers |
| https://www.filmmakersacademy.com/glossary/30-degree-rule/ | article | no date (idx ~449 d) | snippet | Change the focal length by at least 20 mm *or* the angle by at least 30°. A big shot-size jump, such as medium to extreme close-up, also works. | supports, and adds a shot-size option |
| https://learnaboutfilm.com/film-language/sequence/ | article | no date | snippet | The camera position should change by at least 30° between shots. | supports (30°) |
| https://restream.io/learn/what-is/30-degree-rule/ | article | no date (idx ~827 d) | snippet | Move the camera at least 30° between shots of the same subject. | supports (30°) |
| https://www.thefilmlook.com/thefilmlook-video/how-to-use-the-30-degree-rule | video (tutorial page) | no date (idx ~2215 d) | snippet | Orbit the camera more than 30° around the subject; this also applies across shot types. No mm figure seen. | supports (30°) |
| https://www.robertcmorton.com/the-5-cs-of-cinematography/ | article (summary of Mascelli) | no date (idx ~224 d) | snippet | Mascelli: the angle, the lens, "or preferably both" should change each time the camera stops during continuous action. | partly: no number, and he prefers both, not either |

**Verdict: TWO TYPES FOUND for 30° (article + video). ONE TYPE (article only) for 20 mm.** One concern of my own, not from a source: a fixed 20 mm step isn't proportional. 24→44 mm is a big change, 200→220 mm is a tiny one. Consider a ratio or shot-size step instead.

## CRAFT-CIN-04: screen sides and the axis hold inside a scene

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://diyvideoeditor.com/how-to-hide-jump-cuts-in-your-videos/ | article | no date (idx ~586 d) | snippet | 180-degree rule: always stay on one side of the subjects' imaginary axis so viewers don't get confused. | supports |
| https://www.studiobinder.com/blog/what-is-continuity-editing-in-film/ | article (with an embedded video) | no date (idx ~1147 d) | snippet | Lists the 180-degree rule as a continuity technique that matters when cutting between characters. | supports |
| https://en.wikipedia.org/wiki/Continuity_editing | article | no date | snippet | Lists the 180-degree rule, eyeline match and match on action as parts of continuity editing. | partly (no detail seen) |
| https://www.thefilmlook.com/thefilmlook-video/how-to-use-the-30-degree-rule | video | no date (idx ~2215 d) | snippet | The 180 rule keeps characters facing the correct screen direction; don't cross the line. | supports |
| https://books.google.com/books/about/The_Five_C_s_of_Cinematography.html?id=0gBMAQAAIAAJ | book (Google Books listing, Silman-James 1998, 251 pp.) | 1998 edition | snippet | The book description lists "screen direction" as a topic; the Continuity chapter starts on p. 67. The rule's text was not seen. | partly |

**Verdict: TWO TYPES FOUND (article + video).** The book is only a listing that names the topic, so it doesn't yet count as a source for the rule.

## CRAFT-CIN-05: headroom / lead room toward the gaze
NO SOURCE FOUND (not searched).

## CRAFT-CIN-06: foreground / midground / background named on the card
NO SOURCE FOUND. One tangential hit: PremiumBeat (row 01) names foreground, mid-ground and background layers, but only to explain lens compression. It doesn't support a depth-staging rule.

## CRAFT-CIN-07: focal point stays within BP-30's shift across a hard cut
NO SOURCE FOUND (not searched). Nothing was found on the 0.18 value either.

## CRAFT-CIN-08: shot-size variety inside a scene

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://www.robertcmorton.com/the-5-cs-of-cinematography/ | article (summary of Mascelli) | no date (idx ~224 d) | snippet | Changing angle and lens results in "decided changes in image size, camera angle, and lens height." | partly (about cut to cut, not a whole scene) |
| https://www.filmmakersacademy.com/glossary/30-degree-rule/ | article | no date (idx ~449 d) | snippet | A big shot-size change gives a smooth transition. | partly |

**Verdict: ONE TYPE (partly).** Neither source states a scene-level variety rule or number.

## CRAFT-CIN-09: per-segment intensity rises toward the climax
NO SOURCE FOUND (not searched).

## CRAFT-CIN-10: lane shares follow dramatisability within run caps
NO SOURCE FOUND (not searched). Neither YouTube Help 9314415 nor the 60/90 s caps were checked.

## CRAFT-CIN-11: stakes and named heroes in every frame
NO SOURCE FOUND (not searched).

---

### Sources useful beyond the checklist rows
- **Camera-angle research** (ResearchGate 352135520, the Baranowski & Hecht PDF, ScienceDirect S2451958823000180): measured effects of angle on how powerful, trustworthy and charismatic a subject seems. These could ground a rule that angles work relative to each other within a scene.
- **https://sceneos.io/kb/five-cs-of-cinematography/** (article, shows "v1.0 Aug 17, 2026"; snippet): a review of Mascelli for AI video, written as prompt decisions. It quotes Mascelli on the point-of-view close-up. It's useful for turning Mascelli into shot-card fields.
- **Mascelli on Google Books** (link in CIN-04): contents show Camera Angles p. 11, Continuity p. 67, Cutting p. 147. If you open those pages, Mascelli could become the book source for CIN-02, 03, 04 and 05.
- **https://www.creatoressentials.com/glossary/camera-angle/**: has a section on camera angles for YouTube videos and a list of common mistakes.

### Suggested queries for the next pass
- CIN-05: "lead room nose room headroom"
- CIN-06: "depth staging foreground midground background"
- CIN-07: "Murch eye trace cut"
- CIN-08: "shot size variety scene coverage"
- CIN-09: "Bruce Block intensity graph"
- CIN-10: "YouTube Help 9314415"
- CIN-11: "show the stakes visual storytelling"
- CIN-03: a YouTube video that gives the 20 mm figure
- Books: Mascelli p. 147 and Murch p. 146 on Google Books

---

## editing_colour (lines dropped by the citation check: 0)

I could only verify five of the twelve rows. My web searches hit their limit after about a dozen queries. Rows 06 to 12 were never searched, so they show NO SOURCE FOUND. That means nothing was looked up, not that nothing exists.

- **CRAFT-EDC-01 (Rule of Six)** is the only row with two source types that state the rule itself: articles and a book excerpt.
- **CRAFT-EDC-04 (handles)** has two types, but they support keeping handles in general. None of them gives 12–16 frames as the norm. The video says 8.
- **CRAFT-EDC-03 (2–4 frames)** found its number on only one article site, and other sources disagree with it.

**What "read" means here:** "read" means I read the page text the search tool returned, which is often only part of the page. I did not open pages in a browser, and I did not watch any video. "Snippet" means I saw only the title or description line. "Index age" is how old the search index says the page is, not a date printed on the page.

---

## CRAFT-EDC-01: Rule of Six, in order (BP-128)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://blogs.ischool.berkeley.edu/i290-viznarr-s12/the-rule-of-six-walter-murch/ | book (excerpt of *In the Blink of an Eye*, pp. 17–20, posted on a 2012 UC Berkeley course blog) | course "Sp 2012"; no post date | read | Murch's own text. It gives the six criteria with their weights and says emotion is worth more than the other five combined. It also gives the order of sacrifice: "don't ever give up emotion before story", then story before rhythm, and so on down. He calls the percentages "slightly tongue-in-cheek, but not completely." | supports (order and sacrifice from the bottom). The weights are partly a joke by his own account. |
| https://nofilmschool.com/editing-emotion-using-walter-murchs-rule-six-non-narrative-content | article | no date shown (index age ≈1514 days) | read | Lists the six with their weights (Emotion 51%, Story 23%, Rhythm 10%, Eye Trace 7%, 2D 5%, 3D 4%). Applies them to non-narrative content. | supports |
| https://www.metaphorex.org/entries/the-rule-of-six/ | article | no date | read | Credits the rule to *In the Blink of an Eye* (1995). Emotion gets 51%. Notes the weights come from one editor's intuition. | supports, with a caveat |
| https://filmdaft.com/walter-murchs-rule-of-six-the-editors-formula-for-choosing-the-right-cut/ | article | no date shown (index ≈331 d) | read | Ranked table with emotion first at 51%. Mentions YouTube and Reels formats. | supports |
| https://www.ormsdirect.co.za/blogs/cinematography-news/how-to-create-cuts-that-work-walter-murchs-rule-of-six-in-editing | article | no date shown (index ≈839 d) | read | 51% / 23% / 10% weights. Says a companion OrmsTV video exists, but I found no URL for it. | supports |
| https://movieintheair.com/wp-content/uploads/2022/01/Walter-Murch-and-The-Rule-of-Six.-When-this-notable-figure-in-cinema%E2%80%A6-by-Scott-Myers-Jan-2022-.pdf | article (PDF of Scott Myers piece) | Jan 2022 (in filename) | read | All six weights. Emotion ranked first. | supports |
| https://vimeo.com/350689397 | video ("ACE Film Editor Walter Murch explains 'Rule of Six'") | no date shown (index ≈32 d) | read the page text only; video not watched | Description repeats the rules with their weights. Quotes Murch: an ideal cut "(for me)" meets all six at once. I can't confirm Murch is on camera. | supports (page text) |
| https://www.youtube.com/watch?v=p9dF-ZT9u1k | video ("Walter Murch and the Rule of Six", Film Friday ep. 1) | no date shown (index ≈2365 d) | snippet | A third-party creator explains the rule. No detail visible. | partly (topic only) |

**Verdict: TWO TYPES FOUND** (article and book excerpt; the video is weak). Caveat: the Berkeley page is a copy of the book on a course blog. Before the rule binds, check pp. 17–20 against a published edition.

## CRAFT-EDC-02: Never cut without a reason

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.provideocoalition.com/seven_rules_for_film_and_video_editors/ | article | no date shown (index ≈6625 d) | read | Says Dmytryk lists seven rules in *On Film Editing* (Focal Press, 1984). Rule One: "Never make a cut without a positive reason." | supports |
| https://nevalalee.wordpress.com/2014/08/09/the-seven-rules-of-cutting/ | article (quotes the book) | 9 Aug 2014 (URL) | read | Quotes all seven rules, credited to *On Film Editing*. Rule 1 is the same as above. | supports |
| https://www.nyfa.edu/student-resources/what-you-can-learn-from-edward-dmytryks-7-rules-of-cutting/ | article | no date shown (index ≈3493 d) | read | Rule 1, plus Dmytryk's point that you don't cut just because the shot feels long. | supports |
| https://www.chicagomediaworks.com/2instructworks/3editing_doc/3editing_docdymytryk.html | article (course notes) | no date | read | Same rule. Cut to another shot only when it better serves the scene. | supports |
| https://medium.com/@edwardneilwalker/edward-dmytry-s-7-rules-of-editing-d52a5bcd13dc | article | no date shown (index ≈3877 d) | read | Rule 1, with commentary. | supports |
| https://www.oreilly.com/library/view/on-film-editing/9780240517384/ | book (publisher/library listing) | listing says November 2012 | read | Listing for *On Film Editing*, Focal Press, 148 pp. **The rule text is not shown.** | partly (proves the book exists, not the rule) |
| https://openlibrary.org/books/OL2842340M/On_film_editing | book (library listing) | 1984 edition | read | Bibliographic record only. | partly |
| https://www.youtube.com/watch?v=7e43lPpnOww | video (student coursework) | no date shown (index ≈5351 d) | snippet | Examples of "3 out of the 7" Dmytryk rules. It doesn't say which three. | partly (weak) |

**Verdict: ONE TYPE (article)** stating the rule. The book appears only as listings that don't show the rule text. To count the book, open the rule's page in *On Film Editing* (e.g. on O'Reilly).

## CRAFT-EDC-03: Cut lands 2–4 frames after the motion begins (BP-128)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.parker.mov/tools/editologica/cutting-on-action | article | no date | read | "Frame the cut 2-4 frames into the movement, not at its initiation or completion." Cites Dmytryk, but Dmytryk's rule (below) has no frame count. | supports (the only exact match) |
| https://nevalalee.wordpress.com/2014/08/09/the-seven-rules-of-cutting/ | article (Dmytryk rule 3) | 9 Aug 2014 | read | "Whenever possible, cut 'in movement.'" No number. | partly |
| https://www.slideshare.net/slideshow/11-directing-film-techniques-and-aesthetics-michael-rabigerpdfpdf/259706427 | book (Rabiger, *Directing: Film Techniques and Aesthetics*; an uploaded copy, edition unknown) | no date shown (index ≈1179 d) | read | For fast action, a match cut needs about **four frames of the action repeated** on the incoming shot. Reason given: the eye misses the first 3–4 frames of a new image. | partly. It's an overlap rule, not "2–4 f after the motion starts". The upload may be unauthorised, so check a published edition. |
| https://cinematography.com/index.php?%2Fforums%2Ftopic%2F59879-cutting-on-movement%2F= | article (forum) | no date shown (index ≈3485 d) | read | Quotes Rabiger's 1989 edition: repeat 2–3 frames. Forum users disagree that it's needed. | partly; shows the number is disputed |
| https://zooop.ai/glossary/editing/match-on-action | article | no date | read | Cut after the move is readable, not at its start. Many editors *trim* 2–4 frames at the join so the action doesn't repeat. | partly. Same frame count, but it trims frames where Rabiger repeats them. |
| https://flashboards.yaroflasher.com/learn/editing/match-on-action/ | article | no date shown (index ≈35 d) | read | Working guide: cut about **a third of the way into the action**. | contradicts the fixed 2–4 f (proportional, not a set count) |
| https://www.screenweaver.ai/film-techniques/editing/match-on-action | article | no date shown (index ≈31 d) | read | Cut near the midpoint or just after the start. Some editors overlap a few frames. | partly |
| https://www.thefilmlook.com/thefilmlook-video/5-essential-editing-tips-for-short-films | video (page in a video section) | no date shown (index ≈1998 d) | read the page text only | For fast action, repeat a few frames after the cut so the viewer's brain can catch up. No count. | partly |

**Verdict: ONE TYPE** for the 2–4 f number (one article). Cutting during the motion is backed by an article, a book and a video. But the sources disagree on what the frames are for: repeating them (Rabiger, thefilmlook), trimming them (zooop), or placing the cut a third of the way in (flashboards). The checklist's wording should be settled before a validator measures it.

## CRAFT-EDC-04: Handles at both ends (12–16 f) (BP-128, KP-16)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://github.com/PixarAnimationStudios/OpenTimelineIO/blob/v0.14/docs/use-cases/animation-shot-frame-ranges.md | article (Pixar OpenTimelineIO docs, animation use case) | v0.14 docs; no date | read | In animation, extra frames called handles are usually agreed at the head and tail of each shot. Shots that are too short must be extended. Shots more than 12 f too long can be trimmed. | supports the rule; no handle length |
| http://effectscorner.blogspot.com/2007/10/budgeting-vfx.html | article | 25 Oct 2007 | read | VFX bids list handles of "4-16 frames on each end" of the cut shot. | partly (wider range) |
| https://playpause.io/blogs/vfx-pulls-tracked-offline-edit-through-delivery | article | no date shown (index ≈179 d) | read | Usually 8–16 frames of handle at each end. | partly (starts at 8) |
| https://doingthatwrong.com/home/viewer-frame-handles/ | article | no date shown (index ≈2774 d) | read | Plates usually come with 8 or 12 extra frames at each end. | partly |
| https://www.evanschiff.com/articles/feature-turnover-guide-vfx/ | article (Evan Schiff, ACE) | no date shown (index ≈3153 d) | read | Explains handles. Example: 8-frame handles, so 16 extra frames in total. | partly |
| https://animationapprentice.blogspot.com/2022/06/why-animators-need-handles.html | article (animation) | 15 June 2022 | read | Animators add a few frames to the start and end of every shot. Example: "four frame handles". | supports the rule; smaller number |
| https://cutaway.shift.io/vfx-demo-with-richard-sanchez | video (VFX editor demo with transcript) | no date shown (index ≈1303 d) | read the transcript text | Pulls 8 frames of handle, sometimes 24 pulled with 8 returned. | supports the rule; number lower than 12 |
| https://partnerhelp.netflixstudios.com/hc/en-us/articles/38278282194963-Netflix-VFX-Pulls-User-Guide | article (Netflix docs) | no date | read | Handle count is a setting, added to both front and tail. No default given. | partly |

**Verdict: TWO TYPES FOUND** for keeping handles at both ends (article and video). **No source gives 12–16 f as the norm.** Sources range from 4 to 16, and the commonest figure is 8. 12–16 sits at the generous end, which is fine for a minimum but isn't backed as a standard.

## CRAFT-EDC-05: Hard cut by default; dissolve only at a change of place or time (BP-31, ED-04)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://filmdaft.com/scene-transitions-in-film-definition-types-how-they-work/ | article | no date shown (index ≈28 d) | read | Takeaway: "Default to the cut", and use dissolves and other transitions only when they say something about time, place or emotion. | supports (adds emotion) |
| https://en.wikipedia.org/wiki/Dissolve_(filmmaking) | article | no date | read | A dissolve usually means time has passed. It may also mean a change of place or the start of a flashback. | supports / partly |
| https://www.toolsforfilm.com/glossary/dissolve | article | no date | read | Usual meanings: passage of time, change of location, a thematic link. The straight cut has largely replaced the dissolve. Typical length 0.5–3 s. | partly (the thematic-link use goes beyond the checklist) |
| https://www.capcut.com/resource/dissolve-transition-in-video | article | no date shown (index ≈501 d) | read | Dissolve signals passage of time or a change of location. | supports |
| https://www.quillit.app/blog/screenplay-transitions | article | no date shown (index ≈88 d) | read | CUT TO is "the default of defaults". DISSOLVE TO traditionally means time passing or memory. | supports |
| https://domer.io/blog/cinematic-transitions-advanced-video-editing-guide | article | no date shown (index ≈36 d) | read | A dissolve compresses time and signals memory, dream or time passing. | partly |

**Verdict: ONE TYPE (article).** Several sources allow dissolves for memory, flashback, tone or a thematic link, which is broader than "only place or time". Not searched yet: a book (e.g. a film-grammar textbook) and a video.

## CRAFT-EDC-06: Occlusion wipe only as an invisible cut
NO SOURCE FOUND. Not searched; the search limit was reached. (Wikipedia's *Film transition* page came up in another search. Its text mentions the invisible cut, but not the occlusion rule.)
**Verdict: NONE**

## CRAFT-EDC-07: Whips and flashes spaced, opening a story turn (BP-25)
NO SOURCE FOUND (not searched; limit reached). **Verdict: NONE**

## CRAFT-EDC-08: Whip 8–10 f, ramp 1.0/1.6/0.45 × 0.6 s, rack focus 0.4 s (BP-129)
NO SOURCE FOUND (not searched; limit reached). **Verdict: NONE**

## CRAFT-EDC-09: Boundary frames match the scene master (Reinhard transfer) (BP-130)
NO SOURCE FOUND (not searched; limit reached). **Verdict: NONE**

## CRAFT-EDC-10: Hero swatches stay inside a delta-E band
NO SOURCE FOUND (not searched; limit reached). **Verdict: NONE**

## CRAFT-EDC-11: One constant film look (ED-04, BP-131)
NO SOURCE FOUND (not searched; limit reached). **Verdict: NONE**

## CRAFT-EDC-12: Delivery at 30 fps (D-30)
NO SOURCE FOUND (not searched; limit reached). The checklist already cites YouTube Help 1722171, but my search didn't return that page, so I can't confirm or cite it. **Verdict: NONE**

---

## Useful sources beyond the checklist's rows
- **Dmytryk's other rules** (nevalalee, 2014). Rule 2: when unsure which frame to cut on, cut *long* rather than short. Rule 5: scenes begin and end with continuing action. Rule 6: cut for values, not matches. These could become checks in rows 02–04.
- **Murch's own caveat** (Berkeley excerpt): he says the weights are partly a joke. A code check should use the order of sacrifice, not the literal 51%.
- **OpenTimelineIO animation shot-frame-ranges doc** (Pixar GitHub). This is a ready-made model for the clip-length-vs-cut-length check that `assemble.py` would run, built for animation pipelines.
- **mediacollege.com, Premiere transitions and handles** (https://www.mediacollege.com/adobe/premiere/pro/transition/handles.html; snippet only). A dissolve uses up handle frames from both clips, which links rows 04 and 05. A validator should require handles of at least half the dissolve length.
- **toolsforfilm dissolve glossary.** Gives a dissolve length of 0.5–3 s, a possible number if ED-04 needs one.
- **Rabiger's perceptual-lag claim** (the eye misses the first 3–4 frames of a new shot). This is a book-level reason that could support or reshape BP-128.

**Next session:** run searches for rows 06–12. Also look for a book and a video for row 05, and a book page with the rule text for row 02.

---

## motion_graphics (lines dropped by the citation check: 0)

# Motion graphics: sources for the craft checklist (search run, session 2026-10)

I only found sources for the first three rows. **None of the 15 rows has two source types that state its rule yet.** The search tool hit its usage limit after about 14 searches. That happened before I could run any search on Mayer's principles, HUD position or counter tick rates. So rows 04 to 15 are marked NO SOURCE FOUND. That means I didn't search them, not that I searched and found nothing. Hard rule 1 means I can't fill them with URLs from memory, including the Lucidea page the checklist cites.

"Read" below means the search tool gave me the page text and I went through it. Those extracts may be shortened. "Snippet" means I only saw short matching passages.

---

## CRAFT-MOG-01: ease-out to enter, ease-in to leave

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://m3.material.io/styles/motion/easing-and-duration | article (official docs) | no date | read | Things entering the screen use "emphasized decelerate" (400 ms) or "standard decelerate" (250 ms). Things leaving use "accelerate" (200 ms). Exits are shorter because they need less attention. | supports |
| https://m1.material.io/motion/duration-easing.html | article (older Material docs) | no date | read | The deceleration curve ("ease out") is for entering. Leaving elements speed up at the start and may shrink or fade to 0%. Exits can be shorter. | supports |
| https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing | article | no date | read | "objects entering the screen should decelerate as they arrive. Objects leaving the screen should accelerate as they exit." | supports |
| https://learn.microsoft.com/en-gb/windows/apps/design/motion/timing-and-easing | article (docs) | no date | snippet (jumbled) | Uses a "fast out, slow in" curve, cubic-bezier(0,0,0,1), for things entering. A speed-up curve for things leaving is implied, but the snippet's labels are mixed up. | partly (check the page itself) |
| https://medium.com/thinking-design/ask-a-uxpert-animation-best-practices-for-avoiding-common-mistakes-f55f66d194e1 | article (interview with Val Head, author of *Designing Interface Animation*) | no date in extract (search shows it as about 7.5 years old) | read | Val Head recommends ease-out for things entering. For things leaving, ease-in, "just like an object in real life might." | supports |
| https://css-tricks.com/ease-out-in-ease-in-out/ | article | no date in extract (about 10 years old) | read | Ease-out when things move in, ease-in when they move out. Mentions older Google timings of 225 ms in and 195 ms out. Val Head's rule of thumb: 0.1 to 0.2 s for simple moves, up to 0.5 s for big ones. | supports (the timings are older than Material 3's) |
| https://vibe-hub.org/en/easing ; https://dev.to/nobody_4fb7fd10637d3b88a3/why-easing-makes-animation-feel-alive-4g3f | article (×2) | no date | snippet | Both say: ease-out for things entering, ease-in for things leaving. | supports (low authority) |
| https://www.uxmatters.com/mt/archives/2016/12/designing-interface-animation.php | book (sample chapter 3 of Val Head, *Designing Interface Animation*, Rosenfeld 2016) | December 19, 2016 | read | Judge timing by whether the motion is readable, not by one fixed duration. Bounce or elastic easing may need 20 to 30 ms more. Says nothing about entering vs leaving. | partly (book type, but not this rule) |
| https://www.youtube.com/watch?v=zBsQtjAoW_4 | video | about 287 days old (search age) | snippet | A 25-second general ease-in/ease-out tip. The snippet says nothing about entering vs leaving. | does not state the rule |

No source disagrees with the rule. Material 3 adds one thing: exits should be shorter than entrances. The checklist row doesn't say this. Check whether BP-134 does.
**Verdict: ONE TYPE (article). A book or video that states the rule is still missing.**

## CRAFT-MOG-02: a counter ticks at a readable rate and lands on its number

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://olafmotion.com/tutorials/how-to-animate-number-counters-in-after-effects/ | article | no date in extract (about 157 days old) | snippet | If a counter is hard to follow, make it last longer so each frame changes less. The last frame is "where viewers confirm the number." | partly (no rate given) |
| https://www.reochart.com/animated-number-counter | article (tool page) | no date | snippet | Its counts take 1.3, 1.9 or 2.6 s. Leave the final number on screen long enough to read. | partly |
| https://www.framer.com/community/marketplace/components/animated-counter-up/ | article (component page) | no date (about 254 days old) | snippet | For large numbers, count in bigger steps to avoid visual noise. Use fixed-width digits. | partly |
| https://www.pravinkumar.co/blog/webflow-animated-number-counter-design-2026 | article | no date in extract | snippet | The number must be fully readable the instant the motion ends. | partly (supports "lands on its number") |
| https://codefronts.com/motion/css-number-counter-animations/ | article | no date | snippet | Counts usually take 1 to 2.5 s. | partly |
| https://github.com/onepartscissors/Counter-Up | article (code docs) | no date | snippet | Its example setting waits 10 ms per step, which is about 100 steps a second. This is a sample setting, not readability advice. | note: tools run far faster than ≤10 a second |
| https://www.uxmatters.com/mt/archives/2016/12/designing-interface-animation.php | book (excerpt) | December 19, 2016 | read | Readability should decide timing. | partly (general, not about counters) |

**No source found for "≤ 10 steps a second" (BP-134).** Nothing found ties a counter to the moment its number is spoken (BP-93).
**Verdict: NONE for the number. The general idea (readable rate, clear final number) is partly backed by articles and a book excerpt.**

## CRAFT-MOG-03: at most one graphic element in motion

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://m1.material.io/motion/choreography.html | article (docs) | no date | read | Keep one clear focal point during a transition. If only one element carries over, it should lead and "control" the others. | partly. Material also lets many elements move at once if they follow one lead element, which is looser than "one element". |
| https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing | article | no date | read | Easing, timing and offsets lead the eye through the content in a set order. | partly (staggering, not one at a time) |
| https://medium.com/thinking-design/ask-a-uxpert-animation-best-practices-for-avoiding-common-mistakes-f55f66d194e1 | article | no date in extract | snippet (heading only) | Includes the advice "Don't animate all the things" and "Keep the stagger interval to a minimum." | partly |

**Verdict: ONE TYPE (article, partly). No source states "one element" as a number.**

## CRAFT-MOG-04: every HUD element keeps one slot per episode
NO SOURCE FOUND (not searched, search limit reached). **Verdict: NONE**

## CRAFT-MOG-05 to CRAFT-MOG-15: Mayer's principles
These rows are coherence, signaling, redundancy, spatial contiguity, temporal contiguity, segmenting, pre-training, modality, personalisation, voice and image. For each one: **NO SOURCE FOUND** (not searched, search limit reached). This includes the Lucidea page the checklist calls SUPPORTED: no search here returned it, so I can't confirm it. **Verdict for each of the 11 rows: NONE**

---

## Useful beyond the checklist rows
- **https://m3.material.io/styles/motion/easing-and-duration**: easing and duration pairs (enter 250 or 400 ms, exit 200 ms, on-screen moves 300 or 500 ms). Possible numbers for BP-134.
- **https://learn.microsoft.com/en-gb/windows/apps/design/motion/timing-and-easing**: exact curve values a motion checker could compare against.
- **UXmatters book excerpt (2016)**: "readability decides timing", plus extra time for bounce easing.
- **css-tricks.com**: Val Head's 0.1 to 0.5 s duration range.
- **Framer / pravinkumar**: fixed-width digits, and reserve room for the final number so the layout doesn't jump. Practical counter tips.
- **Book listings that came up but don't state the rules:** https://rosenfeldmedia.com/books/designing-interface-animation/ (listing, not read), https://alistapart.com/article/designing-interface-animation/ (chapter 9 excerpt, on brand personality and easing) and https://boxesandarrows.com/book-in-brief-designing-interface-animation/ (chapter 4 excerpt, on motion for orientation). A university-repository PDF of the same book also came up. It looks like an unauthorised copy, so I didn't use it.

**Searches to run next session:**
- Rows 05 to 15: the Lucidea Mayer page, a Cambridge University Press listing or Google Books page for *Multimedia Learning*, and a YouTube talk on Mayer's principles.
- Row 01: a video stating the entering/leaving rule, such as a School of Motion or Google Design talk.
- Row 04: consistent HUD and lower-third placement in game UI and broadcast graphics.
- Row 02: any research on how fast changing digits can be read.

---

## packaging (lines dropped by the citation check: 1)

I ran 11 searches before the search tool hit its usage limit. **Rows 06, 07, 08, 09 and 10 never got a search of their own.** Where those rows say "NO SOURCE FOUND" or show sources, that comes only from results returned for other rows. It doesn't mean no source exists.

**Read vs. snippet:** I never opened pages separately. "Read (extract)" means the search tool returned a full-text extract of the page and I read that. "Snippet" means I only saw a short excerpt. For example, the YouTube video results only gave their description text, and I didn't watch any video. None of the extracts showed a publication date, so "no date (~N days old)" uses the search engine's estimate of the page's age. Dates in a URL or in the extract are given as such.

**No book source was found for any row.**

**Result:** two rows (01 and 03) have an article and a video. Four rows have articles only. Rows 06, 07 and 10 have nothing.

---

## CRAFT-PKG-01: three title-and-thumbnail promises with different mechanisms (BP-135)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://support.google.com/youtube/answer/13861714?hl=en_ID | article (YouTube Help) | no date | read (extract) | You can test up to three titles, three thumbnails or three title+thumbnail pairs. The version with the highest watch time wins, not the highest click-through rate. Tests should finish within two weeks. Changing the title or thumbnail during a test stops it. | supports the 3 |
| https://support.google.com/youtube/answer/16391400?hl=en | article (YouTube Help, second version) | no date (~325 days) | read (extract) | Same limit of 3. Its tip "Run diverse A/B tests" says versions that are "too similar to each other can cause tests to run for longer". | supports the 3; partly supports "different mechanisms" (YouTube asks for variety but says nothing about mechanisms) |
| https://thumbnailtest.com/guides/title-test-and-compare-alternative/ | article (vendor) | no date (~108 days) | read (extract) | Studio caps a test at 3 titles, 3 thumbnails or 3 pairs and picks the winner by watch-time share. The vendor sells a tool without that cap, so it isn't neutral. | supports |
| https://www.youtube.com/watch?v=jKRiib3Xzoo | video | no date (~325 days) | snippet (description only) | Describes A/B testing as choosing up to 3 titles and/or thumbnails. I couldn't confirm which channel posted it. | supports |

**Verdict: TWO TYPES FOUND** (article + video) for the number 3. "Different mechanisms" is still the house's own idea; YouTube's "diverse tests" tip comes closest. To bind, the video sources need to be watched and their channel identified.

## CRAFT-PKG-02: the first seconds pay off the chosen promise (BP-135, 5 s)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://youseo.app/blogs/how-to-stop-viewers-clicking-away-in-the-first-30-seconds | article | no date (~148 days) | read (extract) | Says to deliver the title-and-thumbnail promise within the first 5 seconds. Its example: if the first 10 seconds are unrelated setup, you've broken the promise. | supports 5 s |
| https://mayawaters.com/youtube-intro-video/ | article | no date (~271 days) | read (extract) | Steps: define the "plot promise" in the title and thumbnail, then deliver on it in the first 5 seconds. | supports |
| https://scriptstorm.ai/blog/how-to-write-youtube-video-intros-boost-retention | article (AI-tool vendor) | no date (~201 days) | read (extract) | The first 5 seconds should confirm the title/thumbnail payoff. | supports |
| https://www.soundstripe.com/blogs/youtube-intro-ideas | article | no date (~58 days) | read (extract) | Suggests restating the title "in the first five seconds". It also says YouTube's retention report names two fixes for a low intro: change the title and thumbnail, or change the first 30 seconds. | supports |
| https://coconote.app/notes/7bf55b87-3506-4e2e-8c44-f1aeddcd9518 | article (third-party notes on a YouTube video; I don't know which video) | no date (~446 days) | read (extract) | Notes of a creator talk: "Deliver on the Plot Promise in the First 5 Seconds". The video itself wasn't found, so this doesn't count as a video source. | supports (second-hand) |
| https://yt-seo-architect.vercel.app/blog/youtube-intro-hook-first-3-seconds | article | no date (~156 days) | read (extract) | Says the first **3** seconds decide whether "60%+" of viewers stay. It gives no source for that figure. | partly; uses a stricter number than 5 s |
| https://gyre.pro/blog/how-to-improve-audience-retention-on-youtube-top-tips | article | no date (~22 days) | read (extract) | Names a mismatch between what the title and thumbnail promise and "what the first seconds deliver" as a common cause of drop-off. | partly (no number) |

**Verdict: ONE TYPE** (article only). The talk behind the Coconote notes would be the video source if it can be found.

## CRAFT-PKG-03: map Studio's intro, top moments, spikes and dips onto segment ids (BP-48)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop | article (YouTube Help) | no date | read (extract) | Defines four key moments. **Intro** is the % still watching after the first 30 s. **Top moments** are where almost no one dropped off. **Spikes** are rewatched or shared moments. **Dips** are skipped or abandoned moments. Data takes 1–2 days to process. It also mentions a separate "audience retention segments" report. | supports |
| https://www.tubefilter.com/2020/10/02/youtube-viewer-retention-analytics-creator-insider/ | article (trade press) | 2020-10-02 (from URL) | read (extract) | Reports the redesign as announced in a Creator Insider video. Back then the four moments were Intro, **Continuous Segments**, Spikes and Dips, with Intro again at 30 s. | supports; the label has since changed to "Top moments" |
| https://www.creatorhandbook.net/youtube-revised-retention-analytics-with-key-moments/ | article | no date (~2213 days) | read (extract) | Restates the same 2020 announcement. | supports |
| https://www.youtube.com/watch?v=zNy3jxmT26o | video (Creator Insider) | no date (~1855 days) | snippet | Creator Insider episode with Dan on improvements to the Key Moments card, including "Typical Audience Retention". | partly (it's about the report; I didn't watch it) |

**Verdict: TWO TYPES FOUND** (article + video). The video is snippet-only and about five years old. YouTube Help gives **no pass threshold** for the intro, so a number for BP-48 would need its own source.

## CRAFT-PKG-04: the midpoint retention gate (50 %) (BP-136, BP-48)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://prepublish.ai/guides/youtube-retention-guide | article | no date (~191 days) | read (extract) | Measures average percentage viewed (APV), not retention at the midpoint. Its benchmarks: 50–60 % is strong for 5–10 min videos, 40–50 % for 10–15 min. | partly; for our 10–15 min videos, 50 % is the top of the band, not a minimum |
| https://retti.ai/guides/what-is-a-good-retention-rate | article | no date (~19 days) | read (extract) | Calls ~50 % APV a common rule of thumb, with 40–60 % the usual range. It says YouTube "publishes no platform average". | partly; also undercuts claims that any number comes from YouTube |
| https://www.lenostube.com/en/youtube-audience-retention-average-good-and-best-benchmarks/ | article (vendor) | no date (~136 days) | read (extract) | Calls ~50–60 % good, depending on niche and length. | partly |

**Verdict: ONE TYPE.** No source states a retention-at-midpoint gate. All of them measure APV, which is a different metric. For a 10–15 min video, these benchmarks suggest 50 % may be too strict as a gate.

## CRAFT-PKG-05: a Short stays within YouTube's length limit (BP-137, BP-12)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://support.google.com/youtube/answer/15424877?hl=en | article (YouTube Help) | no date (~661 days) | read (extract) | Square or vertical videos up to 3 minutes count as Shorts (uploads from 15 Oct 2024; a 8 Dec 2025 date applies to some channel types). **Most songs can be used for only up to 90 s** of a 3-minute Short. | supports |
| https://support.google.com/youtube/answer/12921536?hl=en | article (YouTube Help) | no date | read (extract) | Shorts are vertical videos "up to 3 minutes long". | supports |
| https://blog.youtube/news-and-events/tall-updates-coming-to-shorts/ | article (official blog) | no date (~756 days) | read (extract) | From October 15, Shorts can be up to 3 minutes, for square or taller videos. | supports |
| https://www.engadget.com/entertainment/youtube/youtube-shorts-can-now-run-up-to-three-minutes-160002081.html | article (press) | no date (~756 days) | read (extract) | The limit went from 1 to 3 minutes on Oct 15. | supports |
| https://variety.com/2024/digital/news/youtube-shorts-maximum-video-length-three-minutes-1236166349/ | article (press) | 2024 (from URL) | read (extract) | The maximum tripled from 60 s to 3 minutes. | supports |

**Verdict: ONE TYPE** (article). I didn't find a video source before the search limit.

## CRAFT-PKG-06: captions, labels and the face inside the Shorts safe zone (BP-29)

**NO SOURCE FOUND.** I never searched this row; the safe-zone search was blocked by the limit. Neither pixel set (288/672/48/192 or 250/480/240/60) was checked, so conflict 13 is still open.

**Verdict: NONE.**

## CRAFT-PKG-07: the hook is spoken from the first second (BP-11)

**NO SOURCE FOUND** for Shorts specifically. The long-form "first 3 / 5 seconds" sources under PKG-02 are about long videos, not Shorts, so they don't count here.

**Verdict: NONE.**

## CRAFT-PKG-08: the thumbnail opens a gap the video closes, honestly (TN-02)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.soundstripe.com/blogs/youtube-intro-ideas | article | no date (~58 days) | read (extract) | Reports that YouTube's own fix for a low intro % is to make the title and thumbnail better reflect the content. I couldn't confirm this on the Help page, because that part of the extract was cut off. | partly |
| https://www.endavomedia.com/audience-retention/ | article (agency) | no date (~1036 days) | read (extract) | Says to drop clickbait thumbnails because retention depends on the video matching viewers' expectations. | partly (honesty; nothing about the gap) |
| https://www.thumbmagic.co/blog/ab-test-youtube-thumbnails | article (vendor) | no date | snippet | Claims misleading thumbnails lose A/B tests because YouTube judges by watch time. | partly (claim with no data) |

**Verdict: ONE TYPE** (article, found incidentally). Nothing describes the "gap" mechanism, and I never searched this row directly.

## CRAFT-PKG-09: per-platform packs (TikTok, Instagram)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.socialnewsdesk.com/blog/youtube-shorts-announces-3-minute-videos/ | article | no date (~744 days, i.e. late 2024) | read (extract) | Says TikTok's limit is 10 minutes and Instagram Reels' is 90 seconds. | partly; **may be out of date**, so check against the platforms' own help pages |
| https://www.engadget.com/entertainment/youtube/youtube-shorts-can-now-run-up-to-three-minutes-160002081.html | article | no date (~756 days) | read (extract) | Says TikTok has allowed 10-minute videos for over two years. | partly (dated) |

**Verdict: ONE TYPE**, found incidentally. These are second-hand figures from 2024. The row's "not researched" status is still correct.

## CRAFT-PKG-10: nothing goes public without the creator's recorded approval

**NO SOURCE FOUND.** I didn't search for this. It's a house rule (CLAUDE.md invariant 4), so it probably doesn't need an outside source.

**Verdict: NONE.**

---

### Useful findings beyond the checklist
- **Test & Compare picks the winner by watch time, not click-through rate**, and a test runs up to two weeks (YouTube Help 13861714 / 16391400). The packaging promise is therefore judged on retention, which links PKG-01 to PKG-02.
- **Music cap in Shorts:** most songs can be used for only up to 90 s of a 3-minute Short (Help 15424877). This could be a new rule for the Shorts planner.
- **YouTube publishes no platform-wide retention average** (retti.ai). Any retention gate is a house benchmark, not a YouTube number.
- **The Studio label changed:** "Continuous Segments" (2020, Tubefilter) is now "Top moments" (current Help 9314415). Code that reads the retention report should use the current name.

---

## screenwriting (lines dropped by the citation check: 1)

# Screenwriting checklist: source check (P3b)

**Coverage:** I checked rows 01–04. I could not check rows 05, 06 and 07 because the search tool hit its usage limit partway through. Those rows say NO SOURCE FOUND, but that means they were never searched, not that no source exists.

**How I read the pages:** I opened none of these pages in full. For every source I saw the search result, which is the title plus an extract of about 1,600 characters. So every row below is marked **snippet**. Where a date is marked "age ~N d", that is how old the search tool said the page was, not a date printed on the page.

**Verdicts at a glance**
- **SCR-01:** articles only.
- **SCR-02:** articles only for the full check. The only video candidates are about the em dash, and I saw just their titles and blurbs.
- **SCR-03:** the speaking rate has an article and a book. The 4.5 s cap has no source.
- **SCR-04:** two types (an article and a video).
- **SCR-05, 06, 07:** not searched.

---

## CRAFT-SCR-01: AI-register word density (BP-114, BP-140)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing | article (Wikipedia project guide) | no date seen (age ~470 d) | snippet | Has a section called "High density of 'AI vocabulary' words" with a watch list that includes delve, tapestry (as an abstract noun), testament, underscore, pivotal, intricate and meticulous. It says *delve* was heavily overused in 2023 to early 2024 and "dropped off sharply in 2025". It names no numeric density limit. | **partly.** It supplies the word list your sources file marks NOT FOUND. It gives no threshold. It also suggests the list goes stale as models change. |
| https://arxiv.org/html/2406.07016v1 | article (academic preprint, Kobak et al.) | no date seen. The arXiv ID points to June 2024 (v1). | snippet | Proposes measuring "excess word usage" to track how much academic writing is done with LLMs. The extract shows no word list or per-text density number. | partly (backs the method, not a limit) |
| https://arxiv.org/html/2412.11385v1 | article (academic preprint) | no date seen (age ~683 d) | snippet | "Why Does ChatGPT 'Delve' So Much?" finds 21 "focal words" that spiked in scientific abstracts and are overused by ChatGPT-3.5. Examples given: delve, intricate. | partly (word-level evidence, no density limit) |
| https://www.pangram.com/signs-of-ai-writing | article (vendor blog) | no date seen (age ~582 d) | snippet | Table of tells with paired counts and ratios. "AI Phrases" (example "delve into") shows 3 / 30 / 12×. The extract doesn't say what the two count columns measure. | partly. It's an overrepresentation ratio, not a density limit, and it's a vendor source. |
| https://www.npr.org/2025/11/10/nx-s1-5596088/inside-the-unofficial-movement-to-save-the-em-dash-from-a-i | article (news) | 2025-11-10 (from the URL) | snippet | Says in passing that a chatbot "might delve into or conceptualize or leverage a topic". | partly (anecdotal) |
| https://qz.com/words-phrases-give-away-ai-text | article (news) | no date seen (age 0 d) | snippet | Explains why "delve" became the best-known AI tell and lists 10 words and patterns. | partly |

Note: I did not re-check arXiv 2404.01268, which your sources file cites, because that search was in the batch that failed.

**Verdict: ONE TYPE (article).** I found no book or video. No source gives a numeric density limit for BP-140.

---

## CRAFT-SCR-02: structural AI tells (BP-114)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://theconversation.com/can-you-teach-yourself-to-detect-ai-writing-maybe-289236 | article (academic-authored news) | no date seen (age ~65 d) | snippet | Names "not X, but Y" and a fondness for the rule of three as part of an LLM house style. On the em dash, it says the tell "never held up particularly well", because one test found ChatGPT using em dashes and Gemini and Meta AI using none. | **supports** triplets and "not X but Y". **Contradicts** using the em dash as a reliable tell. |
| https://www.pangram.com/signs-of-ai-writing | article (vendor blog) | no date seen (age ~582 d) | snippet | Data table: em dashes 2 / 17 / 10×; "Not just X but Y" 1 / 3 / 3×. The column meanings weren't visible. | supports (em dash, not-just-X-but-Y) |
| https://blendin.ai/blog/ai-writing-tells | article (vendor blog) | no date seen (age ~117 d) | snippet | Lists "the seesaw" ("not just X, it is Y") and "the rule of three, on repeat". Also says "the em dash is a clue, not a verdict". | supports triplets and not-just. Partly on the em dash. |
| https://robotsatemyhomework.substack.com/p/ai-writing-patterns | article (blog) | no date seen (age ~171 d) | snippet | Argues against the bans on em dashes, "not X, but Y" and the rule of three. Its advice is to ration these devices, not drop them. | **contradicts** an outright ban, but fits a density limit |
| https://qz.com/words-phrases-give-away-ai-text | article | no date seen | snippet | Says Wikipedia's guide files these constructions under "negative parallelisms". | supports (not-X-but-Y) |
| https://www.youtube.com/shorts/pOQ_go4OGDs | video (Short) | no date seen (age ~139 d) | snippet (title only) | Title: "Em dashes are how AI gets caught". | partly (title only) |

None of these sources mention a sentence-initial "Imagine" or a rhetorical-question opener in every segment.

**Verdict: ONE TYPE (article)** for the full check. The em-dash item has video candidates, but I saw only their titles and blurbs. The "Imagine" and rhetorical-question items have no source.

---

## CRAFT-SCR-03: twist sentence fits its spoken length (BP-115: ≤ 4.5 s, 0.39 s a word)

0.39 s a word works out to about 154 words a minute. At that rate, 4.5 s holds about 11.5 words.

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.oreilly.com/library/view/broadcast-journalism-6th/9780240810249/xhtml/ch17.xhtml | **book** (*Broadcast Journalism*, 6th ed., ch. 17 "Newsreading mechanics", O'Reilly listing) | no date seen | snippet | Gives a comfortable reading range of 140–220 wpm. British radio uses "3 words per second, or 180 wpm", and "three words per second" is offered as a script-timing rule of thumb. It calls 150 wpm "ultra-slow" and says it is sometimes used in America. | **partly.** 0.39 s a word (154 wpm) is inside the range, but the book's working rate is 0.33 s a word. For a US audience 150 is acknowledged. |
| https://virtualspeech.com/blog/average-speaking-rate-words-per-minute | article | no date seen (age ~3 d) | snippet | Cites the National Center for Voice and Speech: US English conversation averages about 150 wpm. Audiobooks, radio hosts and podcasters run 150–160 wpm. | **supports** about 0.38–0.40 s a word |
| https://www.thevoicerealm.com/blog/voice-over-words-per-minute-script-timing/ | article | no date seen (age ~22 d) | snippet | Quotes the National Center for Voice and Speech figure of about 150 wpm and uses it for voice-over timing (30 s ≈ 75 words). | supports |
| https://en.wikipedia.org/wiki/Speech_tempo | article | no date seen | snippet | Gives a typical English rate of 4 syllables a second. BBC bulletins averaged 168 wpm. | partly (gives a per-syllable basis for syllables.py) |

**Verdict: TWO TYPES FOUND (article + book) for the rate value only**, and the book's preferred rate is faster than 0.39 s a word. **No source found for the 4.5 s twist cap.**

---

## CRAFT-SCR-04: THEREFORE / BUT, not AND-THEN (ST-02)

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://speakola.com/arts/matt-stone-trey-parker-nyu-writing-class-2014 | article (transcript) | event date 6 March 2014 (NYU) | snippet | Transcript of Parker and Stone. Between beats there should be "either the word 'therefore' or 'but'". Linking beats with "and then" is "not a story". | **supports** |
| https://www.youtube.com/watch?v=vGUNqq3jVLg | video (MTVU "Stand In", NYU) | no date seen (age ~3565 d) | snippet (description only) | South Park creators on plotting with the key words "but" and "therefore". | supports |
| https://www.youtube.com/watch?v=j9jEg9uiLOU | video | no date seen (age ~3164 d) | snippet (description only) | Same advice from the same NYU appearance. | supports |
| https://www.youtube.com/watch?v=JTUJa4ns9AM | video | no date seen | snippet (title only) | Title: "The Magic of 'BUT and THEREFORE' in Storytelling". | partly (title only) |

Also seen as titles only: aerogrammestudio.com (2014/03/06 per URL), firstwriter.com, funnyhow.substack.com.

**Verdict: TWO TYPES FOUND (article + video).** The source sets no number. It doesn't say whether one "and then" join is tolerated, so any threshold in story_lint.py is a house choice.

---

## CRAFT-SCR-05: show, don't tell / full immersion (BP-87, BP-88)
NO SOURCE FOUND. I didn't search this row because the tool limit ran out. **Verdict: NONE.**

## CRAFT-SCR-06: no double exposition (KP-20)
NO SOURCE FOUND (not searched, same reason). **Verdict: NONE.**

## CRAFT-SCR-07: sentences for the ear (BP-06, BP-07)
NO SOURCE FOUND (not searched, same reason). The *Broadcast Journalism* book above is a promising lead for this row. I saw only its newsreading-speed passage, not anything on writing for the ear. **Verdict: NONE.**

---

## Sources useful beyond the checklist rows
- **Wikipedia:Signs of AI writing.** It's a maintained, dated word list grouped by model era (for example, a "2023 to mid-2024 (GPT-4)" list). Useful for keeping register_lint.py's list current, and it warns that single words go out of fashion.
- **Broadcast Journalism, 6th ed., ch. 17.** Gives timing rules for any script: the 140–220 wpm range, and 3 words a second ≈ 20 s per 60 words. It also contrasts US and UK pace. The rest of the book is worth opening for SCR-07.
- **Wikipedia: Speech tempo.** Supports estimating length per syllable (4 syllables a second) rather than per word.
- **The Conversation and robotsatemyhomework.** Both argue against outright bans and for rationing these devices. That supports a **density limit** model over zero tolerance for SCR-02.

**Next searches for 05–07:** "show don't tell" in a craft book or a screenwriting lecture; BBC Academy or "write to pictures" guidance for "don't say what you see"; NPR Training "writing for the ear".

---

## sound (lines dropped by the citation check: 0)

# Sound department (CRAFT-SND): source check

**How far this got:** The search tool stopped me after **9 queries** ("Server tool use limit exceeded"). I only covered rows 01–05 and 14. I ran **no search at all** for rows 06–13 (vacuum, Murch, panning, perspective, motif, beat grid, spotting). Those rows say NO SOURCE FOUND because I didn't search, not because I searched and came up empty.

**Read or snippet:** I did not open any page in a browser. For each result the search tool returned an extract of about 1,500 characters, and that is everything I read. Every source below is marked **snippet (extract)**. For the YouTube pages I saw only the video description. I did not watch any video.

**Dates:** The tool gives only a relative page age ("N days ago"), not the date printed on the page. I report it as "age N d". "no date" means the tool gave nothing.

**Your BP values:** The checklist doesn't include the actual numbers for BP-116, 117, 118, 53 or 50. Where a source gives a number, I list it so you can compare it with the BP value.

---

## CRAFT-SND-01: continuous room-tone bed, no cut to digital silence (BP-116)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://filmfarm.de/en/room-tone | article (glossary) | no date | snippet | Room tone usually sits at **−40 to −35 dBFS**, dialogue at −12 to −6 dBFS, so dialogue is about **25–30 dB** louder than the tone. | supports (gives a band) |
| https://pixflow.net/blog/audio-mixing-premiere-pro/ | article | age 91 d | snippet | Room tone can be "barely-there" at about **−30 dB**. It says there is no single magic number for effect levels. | partly (about 5–10 dB above filmfarm) |
| https://mubert.com/tools/cast/docs/what-is-room-tone | article (product docs) | age 46 d | snippet | "a cut to true digital silence sounds wrong; a cut to room tone sounds like a pause." | supports (the no-silence part) |
| https://en.wikipedia.org/wiki/Presence_(sound_recording) | article | no date | snippet | Presence is intercut with dialogue to smooth edit points. If the track "goes dead", the audience hears a failure of the sound system, not silence. It cites a Focal Press book, *Sound for Digital Video*, p. 162, which I didn't open. | supports (idea; no level) |
| https://asmr.education/faq/video-production/room-tone-recording-purpose-audio-post-production | article | age 226 d | snippet | Digital silence between edits sounds unnatural; room tone keeps the sound continuous. | supports (idea) |
| https://sethero.com/blog/article/room-tone-film-set-terminology/ | article | age 132 d | snippet | Room tone is recorded silence, not real silence. The "−12 dBFS" in its text refers to recording levels, not to the bed level. | partly |
| https://kottke.org/26/06/room-tone | article (blog) | no date shown (URL path suggests 2026/06) | snippet | Criterion records 30 s of room tone at each interview so the edit sounds seamless. | partly (practice; no level) |
| https://gearspace.com/threads/how-loud-is-your-room-tone.1065447/ | article (forum) | age 14 d | snippet | Practitioners say meters are "just not very helpful" for setting room-tone level. | contradicts (any fixed level as a rule) |

**Verdict:** ONE TYPE (article only). The levels disagree: −40/−35 dBFS from filmfarm, about −30 dB from pixflow, and a forum that rejects fixed numbers.

## CRAFT-SND-02: J- or L-cut at every scene boundary, within set durations (BP-117, ED-14)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://valmera.io/glossary/j-cut-and-l-cut | article (glossary) | age 87 d | snippet | **6–12 frames (about 0.2–0.4 s)** for a quick hand-off in conversation. Under about **4 frames** the offset stops reading as a split edit. A crossfade of **2–6 frames** removes clicks. | supports (durations) |
| https://firecut.ai/blog/mastering-the-split-edit-how-j-cuts-and-l-cuts-work/ | article (vendor) | age 167 d | snippet | A J-cut offset of "typically 1–10 frames" so the audio leads the picture. | partly (its lower end, 1–3 frames, is below valmera's 4-frame threshold) |
| https://en.wikipedia.org/wiki/J_cut | article | no date | snippet | Definition: the next scene's audio starts before its picture (audio lead). No durations. | partly |
| https://m.youtube.com/watch?v=gB_rtJSyjFU | video | age 1484 d | snippet (description only) | Tutorial presenting J and L cuts as an essential editing technique. No durations in the description. | partly (technique only) |
| https://www.youtube.com/watch?v=DVSZujJDYXg | video | age 3271 d | snippet (description) | Premiere Pro tutorial using J and L cuts for scene transitions. No durations seen. | partly (transitions; no durations) |
| https://www.youtube.com/watch?v=zhaE4QRHWKY | video | age 1281 d | snippet (description) | DaVinci Resolve how-to for J and L cuts. No durations seen. | partly |

**Verdict:** TWO TYPES FOUND for using split edits at transitions (article + video). Only ONE TYPE (article) for the durations, and I haven't confirmed the videos give numbers. Also, nothing I found says to use one at *every* boundary.

## CRAFT-SND-03: music and ambience leave the voice's presence band (BP-118)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://www.sfu.ca/sonic-studio-webdav/handbook/Presence.html | article (reference handbook; the extract shows no author) | no date | snippet | Presence means bringing a voice forward by emphasising "the 2-4 kHz range where the ear is most sensitive." | supports (the band) |
| https://www.micdrop.cc/blog/frequency-eq-chart | article | no date | snippet | Lists **2–5 kHz** for presence and clarity. Recommends "carving space": cut music and SFX frequencies with EQ instead of only pulling the fader. | supports |
| https://borisfx.com/blog/frequency-masking-explained-and-how-to-fix-it/ | article | age 104 d | snippet | Vocals and pads or guitars collide in the **1–4 kHz** presence range. This is about music mixing. | partly (wider band) |
| https://nofilmschool.com/2015/05/simple-trick-will-make-your-dialogue-sound-better-stand-out | article | 2015 (from URL) | snippet | Notch the music or SFX where the dialogue sits, starting at about **−5 dB**. Some keep the notch at **1–2 kHz**. It also claims the voice sits at about 50 Hz–2 kHz. | contradicts on where the band is |
| https://www.filmmakersacademy.com/dialog-and-music/ | article | age 1546 d | snippet | Make room for the voice by cutting the music's EQ. In their example they cut **100 Hz by 7 dB**, at the voice's fundamental. | partly (carving yes, but not at presence) |
| https://melodics.com/blog/what-is-eq | article | age 361 d | snippet | Cut guitar mids around 2–4 kHz to make room for a vocal. This is music production, not narration. | partly |

**Verdict:** ONE TYPE (article). Sources put the band at 2–4, 2–5, 1–4 or 1–2 kHz. Cut depths I found are about 5–7 dB. None of these articles is a standard for a "measured gap".

## CRAFT-SND-04: every duck is a dip within BP-53's band (BP-53)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://infinitecreation.io/tutorial-ducking-music | article | age 24 d | snippet | Duck by **6–10 dB** as a starting point. A measured table (threshold −22 dBFS, 4:1, 5 ms attack) shows about −10 dB under words and how release time affects dips between words. | supports a band |
| https://www.capcut.com/create/audio-ducking-for-clear-dialogue-in-video | article (vendor) | age 79 d | snippet | Duck about **6–12 dB**, attack 30–80 ms, release 250–700 ms. | supports a band |
| https://www.skrrol.ai/blog/audio-ducking-explained | article (vendor) | age 79 d | snippet | Duck amount typically **9–12 dB**. Dialogue peaks at −12 to −6 dB, music bed at −18 to −24 dB. | supports (upper range) |
| https://www.storyblocks.com/resources/tutorials/how-to-adjust-music-behind-a-voice-track-in-premiere-pro | article | age 217 d | snippet | Dialogue at −12 to −6 dB, music at −18 to −24 dB. Its example duck is **18.5 dB**. It warns about over-ducking. | partly |
| https://gearspace.com/board/post-production-forum/1198509-ducking-music-under-dialog-your-thoughts-philosophy.html | article (forum) | age 3181 d | snippet | One mixer keeps automatic ducking transparent: "usually just 1 or 2dB. Usually 3 dB max". Another mocks 20 dB trailer ducks. | contradicts the 6–12 dB consensus (for automatic ducks) |

**Verdict:** ONE TYPE (article). The usual starting band is 6–12 dB, but the outliers run from 1–3 dB to 18.5 dB. Compare this with BP-53's band.

## CRAFT-SND-05: a major impact is a three-layer composite hit on the frame (BP-119, BP-54)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://add.app/sound-effects/movie-sound-effects/ | article | age 136 d | snippet | "A cinematic hit usually needs a transient, body, and tail." It says to let each layer do one job. | supports (three layers) |
| https://sfxengine.com/blog/impact-sound-effect | article | age 375 d | snippet | An impact has three parts: transient, body and tail. | supports |
| https://pixflow.net/blog/sound-effects-layering/ | article | age 91 d | snippet | Bands: body **80–500 Hz**, transient **4–12 kHz**, tail full range. | supports (bands) |
| https://www.myloops.net/designing-trance-risers-impacts-and-transition-effects | article (music production) | age 56 d | snippet | Three layers: sub **40–80 Hz**, body **200–500 Hz**, transient **above 3 kHz**. Put one shared reverb on the bus. | partly (a sub layer instead of a tail; different bands) |
| https://add.app/sound-effects/explosion-sound-effects/ | article | age 144 d | snippet | An explosion is a layered impact: boom, transient, pressure wave, debris and tail. That is more than three layers. | partly |
| https://valmera.io/glossary/j-cut-and-l-cut | article | age 87 d | snippet | For BP-54: citing ITU-R BT.1359-1, viewers notice sync errors at about **45 ms** of audio lead and **125 ms** of lag. ATSC IS-191 tightens this to 15 ms lead and 45 ms lag. This is second-hand; I didn't open the ITU or ATSC texts. | partly (≤50 ms is a bit looser than the 45 ms lead threshold and much looser than ATSC's 15 ms) |

**Verdict:** ONE TYPE (article). The sources agree on three layers but not on the frequency bands.

## CRAFT-SND-06: acoustic vacuum before the largest reveals (BP-120)
NO SOURCE FOUND (not searched). One related point: the Wikipedia *Presence* page above says a track that "goes dead" is heard as a system failure. That argues for keeping the dip at a level like −42 dBFS rather than going to true silence. **Verdict: NONE.**

## CRAFT-SND-07: at most 2.5 sounds of one colour, 5 when spread (BP-56, BP-121)
NO SOURCE FOUND (not searched). I couldn't re-check the Murch source in this run. **Verdict: NONE.**

## CRAFT-SND-08: narration centred, music wide, spot effects panned within range (BP-121)
NO SOURCE FOUND (not searched). The ±0.45 pan range is still unsourced. **Verdict: NONE.**

## CRAFT-SND-09: never two encoded streams at once (BP-121)
NO SOURCE FOUND (not searched). **Verdict: NONE.**

## CRAFT-SND-10: acoustic perspective follows shot size; one impulse response per scene (BP-122)
NO SOURCE FOUND. The only related point is from myloops (row 05): one shared reverb makes layers read as one sound. That is about impacts, not about scenes or shot size. **Verdict: NONE.**

## CRAFT-SND-11: one motif per faction, hero and channel (BP-123)
NO SOURCE FOUND (not searched). **Verdict: NONE.**

## CRAFT-SND-12: action cuts on the beat grid (BP-123)
NO SOURCE FOUND (not searched). **Verdict: NONE.**

## CRAFT-SND-13: music spotted on boundaries, with a planned no-music stretch (BP-62)
NO SOURCE FOUND (not searched). **Verdict: NONE.**

## CRAFT-SND-14: the delivered mix meets the loudness and true-peak gate (BP-50)

| source URL | type | date | read or snippet | what it says | verdict |
|---|---|---|---|---|---|
| https://pixflow.net/blog/audio-mixing-premiere-pro/ | article (vendor blog) | age 91 d | snippet | Dialogue-driven content for YouTube "usually lands near **−14 LUFS** integrated". This is a secondary claim, not a platform spec. | partly. It sits 2 LU louder than the Blueprint's −16 (conflict 1); compare with BP-50's value. No true-peak figure. |

**Verdict:** ONE TYPE (one weak article). I found no YouTube documentation or EBU/AES/ITU text in this run.

---

## Useful beyond the checklist rows
- **valmera.io J/L-cut glossary:** suggests 2–6-frame crossfades at audio edits to kill clicks. It also carries the ITU-R BT.1359 / ATSC IS-191 sync numbers, which could feed a general "SFX on the frame" tolerance.
- **infinitecreation.io ducking tutorial:** a measured table of release time vs. how much the music recovers between words (100 ms to 1 s). That could make a validator for "no pumping / no stuck duck".
- **Storyblocks / pixflow mixing:** reference levels for music under dialogue (about −18 to −25 dB vs dialogue at −12 to −6 dB), and Storyblocks' warning that silence under narration also distracts.
- **Wikipedia *Presence*:** points to Focal Press, *Sound for Digital Video*, p. 162 (Google Books). That's a lead for the **book** type for rows 01 and 06, but I haven't opened it, so it doesn't count yet.
- **kottke.org / Criterion:** says Criterion publishes yearly room-tone compilation videos. That's a lead for a **video** source for row 01, but the search didn't return those video URLs, so I can't cite them.

**Next session:** start with the rows I didn't search. Look for the Murch "Dense Clarity" essay (07, 09), dialogue-centre panning conventions (08), YouTube's loudness help page and EBU R128 / AES TD1008 (14), cutting on the beat (12), and spotting / leitmotif texts (11, 13). Also look for a video for rows 01, 03 and 04 to get a second type.

---

## voice (lines dropped by the citation check: 0)

I couldn't make all the searches I planned. The search tool hit its usage limit partway through, so I never searched rows VOX-02, 03, 04, 08 and 09. They show **NO SOURCE FOUND** because they weren't searched, not because searching came up empty.

**What I read:** I had no tool to open pages. Every entry comes from the page text the search tool returned. Some of these extracts run to several paragraphs, but none is a full read, so every source is marked **snippet**. "Date" is a date that appears in the extract. Where none appeared I give "no date" plus the search index's age, which may not match the page's own date. I don't know the actual numbers behind BP-01, BP-10 or BP-14. Where I flag a disagreement, it's against the numbers written in the checklist's `source` field.

---

## CRAFT-VOX-01: heard pace inside BP-01's band

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://www.academia.edu/113232345/Do_Your_Ads_Talk_Too_Fast_To_Your_Audio_Audience?uc-sb-sw=26546753 | article (Rodero, audio-ads study) | no date (index ~2,860 days) | snippet | 180 wpm gave the best recall and comprehension in audio ads; above 190 wpm hurt recognition | supports Rodero's 180; **contradicts the Blueprint's 135–145** |
| https://www.warc.com/newsandopinion/news/how-speech-delivery-speed-impacts-audio-ads/en-gb/43304 | article (trade news) | no date (index ~2,440 days) | snippet | Reports the same Rodero study: best timing is "about 180 words per minute", slightly faster than normal | supports 180; contradicts 135–145 |
| https://www.upf.edu/en/web/comunicacio/noticies/-/asset_publisher/Z43gkEdp7zFm/content/moderar-la-velocitat-de-la-parla-augmenta-l-efectivitat-del-missatge/10193 | article (university news) | no date (index ~3,900 days) | snippet | Rodero's news research: best rate is 170–190 wpm | contradicts 135–145 |
| https://www.researchgate.net/publication/259453618_A_comparative_analysis_of_speech_rate_and_perception_in_radio_bulletins | article (Rodero, Text & Talk) | May 2012 | snippet | Most radio authors recommend 160–180 wpm | contradicts 135–145 |
| https://reader.ku.edu/sites/reader/files/2024-01/How%20many%20words%20do%20we%20read%20per%20minute%20(1).pdf | article (academic review) | no date (path says 2024-01) | snippet | Cites Rodero 2016: ideal is 170 wpm for dense news, 190 for light news. Audiobooks run 140–180 wpm | partly (the band depends on how dense the content is) |
| https://www.write-out-loud.com/speech-rate.html | article | no date | snippet | People reading for radio or podcasts are often asked for 150–160 wpm | partly |
| https://www.thevoicerealm.com/count-script.php | article (VO calculator) | no date | snippet | 160 wpm is the usual pace for explainers; 140 wpm is "slow", for audiobooks and long narration | partly; puts 135–145 at the slow end |
| https://lanceblairvo.com/voiceover-script-timer/ | article (practitioner) | no date (index ~120 days) | snippet | For long-form narration such as documentaries, plan on about 140 wpm of script | supports ~140 |
| https://www.parlixa.com/blog/words-per-minute-voice-over | article | no date | snippet | Professional English narration averages 140–160 wpm | partly |
| https://frvoiceover.com/en/words-per-minute-script-timing/ | article (practitioner) | no date | snippet | Count roughly 140–160 wpm for English at a natural pace | partly |
| https://prepublish.ai/blog/youtube-script-length-word-count | article | no date | snippet | Corpus figure: a 10-minute YouTube video holds about 1,810 words (range 1,570–2,060). Calls 140–150 wpm "a planning default, not a measurement" | **contradicts 135–145** as a heard pace |
| https://flashtoolbox.com/blog/youtube-script-words-per-minute | article | no date | snippet | YouTube narration runs 140–180 (elsewhere 140–200) wpm, depending on genre | partly |

**Verdict: ONE TYPE (article only).** I found no book or video. Taken together, these sources favour about 150–180 wpm over the Blueprint's 135–145, which confirms conflict 2.

## CRAFT-VOX-02: measured profile from one test read
| — | — | — | — | NO SOURCE FOUND (not searched: search limit reached) | — |

**Verdict: NONE.**

## CRAFT-VOX-03: two cast voices differ by a measured margin (F0 3 st, rate 15 %, centroid 20 %)
| — | — | — | — | NO SOURCE FOUND (two searches failed on the limit) | — |

**Verdict: NONE.** All three margins are still unverified.

## CRAFT-VOX-04: creator picks by ear from the top three
| — | — | — | — | NO SOURCE FOUND (not searched) | — |

**Verdict: NONE.**

## CRAFT-VOX-05: one stressed word per sentence; a tag only where the delivery changes

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://assets.cambridge.org/97811076/82955/frontmatter/9781107682955_frontmatter.pdf | **book** (Gilbert, *Clear Speech*, CUP, front matter excerpt) | no date | snippet | Each thought group (sentence, clause or phrase) has a focus word. The book has a unit called "Choosing the Focus Word" | partly: one per *thought group*, not per sentence |
| https://www.thevoicerealm.com/blog/how-to-mark-up-a-voice-over-script/ | article (VO craft) | no date (index ~30 days) | snippet | Underline one word in each thought group. Quotes Baruch: the focus word "tends to be the last important word in a thought group" | partly (thought group) |
| https://www.avosjourney.com/blog/how-to-sound-conversational-reading-a-script | article (VO craft) | no date (index ~6 days) | snippet | Put the weight on one idea per sentence; stressing every word makes nothing sound important | supports |
| https://www.voicebooking.com/en/blog/8-ways-to-keep-your-voice-over-script-to-1-minute | article (VO agency) | no date | snippet (cut off) | Says that to sound natural you can only stress 1 word per se… (the text is truncated) | supports (needs the full read) |
| https://www.sej.org/sites/default/files/VoicingYourScript101912.pdf | article (Schaefer, SEJ) | March 2012 | snippet | Underline the "operative words" in each sentence (plural: the who/what/when words) | **contradicts the "one" count** |
| https://www.warehousestudio.com.au/single-post/2019/05/16/learning-lines-operative-words | article (acting studio) | 16 May 2019 (from URL) | snippet | Defines the operative word as the stressed word that gives a sentence its meaning | partly (no count) |
| https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue | article (documentation) | no date | snippet | Put the bracketed instruction "where the delivery should change" | supports the tag half |
| https://www.youtube.com/watch?v=b-GhMZ_rcJM | video | no date (index ~500 days) | snippet (title and description only) | A guide to prompting Eleven v3 with audio tags. The description gives no rule | partly; needs watching |
| https://www.youtube.com/watch?v=Fkv-KHWVBlc | video | no date (index ~17 days) | snippet (description only) | A tutorial on v3 text, audio tags and voice settings. The description gives no rule | partly; needs watching |

**Verdict: TWO TYPES FOUND (article + book) for the stress half, but only as "one per thought group".** If the rule is reworded to "one per thought group", the sources support it. The tag half has documentation only; the two videos would need watching before they count as a second type.

## CRAFT-VOX-06: no pause before a punch line; held pauses inside their limit

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://faculty.tamuc.edu/lpickering/Pdfs/Publish_11.pdf | article (Attardo & Pickering, *Humor* 24-2) | 2011 | snippet | They tested the folk idea that a pause comes before the punch line and rejected it: very few punch lines had a noticeable pause before them | **supports** |
| https://lair.etamu.edu/cgi/viewcontent.cgi?article=1006&context=chssa-faculty-publications | article (another copy of the same paper) | 2011 | snippet | Same paper; confirms what it set out to test | supports (duplicate) |
| https://www.researchgate.net/publication/271383232_Timing_in_the_performance_of_jokes | article (same paper's page, with excerpts from papers that cite it) | no date | snippet | Abstract: punch lines come at a lower pitch and a slower rate, not louder. One citing study found professional comedians lengthen the pause before punch lines | partly / **contradicts** (the citing study) |
| https://arxiv.org/pdf/2605.00143 | article (preprint) | no date (ID suggests 2026) | snippet | Comedians' pauses before highly surprising lines were 0.36 s (35.6 %) longer, and the effect was stronger in the best performers | **contradicts** |
| https://shop.bottegadelsarto.com/opinion/comedy-timing-techniques-experts-swear-by-feel-counterintuitive-669666 | article (low quality: cites no studies) | no date | snippet | Claims a pause before the punch line peaks around 650 ms | contradicts (weak; I wouldn't use it) |
| https://help.elevenlabs.io/hc/en-us/articles/13416374683665-How-can-I-add-pauses | article (documentation) | no date | snippet | Break tags handle pauses up to 3 s (Multilingual v2 and Flash). v3 does not support break tags | partly (a tool limit, not a craft limit) |

**Verdict: ONE TYPE (article).** The evidence is split. Conversational joke-telling (2011) supports "no pause", while stand-up research (the preprint and the citing study) shows a longer pause. I couldn't compare BP-10's own pause limit because I don't have its number.

## CRAFT-VOX-07: chunk size, carried context, pauses by tags and punctuation

| source URL | type | date | read or snippet | what it says | supports / partly / contradicts |
|---|---|---|---|---|---|
| https://elevenlabs.io/docs/overview/models | article (documentation) | no date (index ~8 days) | snippet | Per-request limits: v3 5,000 characters, Multilingual v2 10,000, Flash v2.5 40,000 | supports (gives the ceiling) |
| https://elevenlabs.io/docs/api-reference/text-to-speech/convert | article (API reference) | no date | snippet | `previous_text`, `next_text` and earlier `request_id`s improve continuity when a long job is split into several requests | supports (carried context) |
| https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps | article (API reference) | no date | snippet | At most 3 previous or next request_ids; the last one is the audio closest to the current request | supports |
| https://elevenlabs.io/blog/request-stitching-for-text-to-speech-api | article (vendor blog) | no date | snippet | Conditioning on neighbouring text or earlier outputs improves prosody and flow in long-form speech | supports |
| https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices | article (documentation) | no date | snippet | Break tags up to 3 s; too many cause instability. v3 and v4 don't support break tags (use dashes, ellipses, audio tags) | supports |
| https://elevenlabs.io/docs/product-guides/products/studio | article (documentation) | no date | snippet | A Studio break defaults to 1 s, maximum 3 s. Newer models may ignore break tags | supports |
| https://docs.d-id.com/docs/tts-elevenlabs | article (third-party documentation) | no date | snippet | Each ElevenLabs pause can be at most 3 s; too many break tags cause instability | supports (a second, independent page) |
| https://github.com/Kayne19/switchboard/issues/94 | article (issue thread) | no date (index ~30 days) | snippet | Stitch with up to 3 earlier request ids; `previous_text` is the weaker fallback | partly |

**Verdict: ONE TYPE (article/documentation).** I found no book. The two YouTube videos under VOX-05 might cover tags and pauses but need watching. If BP-14 sets a chunk size above 5,000 characters for v3, the documentation contradicts it.

## CRAFT-VOX-08: new take matches the voice baseline
| — | — | — | — | NO SOURCE FOUND (not searched). One weak lead: a Deepgram page (https://deepgram.com/learn/elevenlabs-languages-vs-accents-support) has a heading about accent drift in long-form speech, but the snippet is cut off and gives no metric | — |

**Verdict: NONE.**

## CRAFT-VOX-09: animated shot's line carries delivery and a visible face
| — | — | — | — | NO SOURCE FOUND (not searched) | — |

**Verdict: NONE.**

---

## Useful beyond the checklist rows
- **Attardo & Pickering 2011** (faculty.tamuc.edu PDF and the ResearchGate abstract): punch lines are delivered at a lower pitch and a slower rate, not louder. That gives a measurable delivery rule for comic lines.
- **ElevenLabs models page:** per-model character limits, needed for any chunking validator.
- **ElevenLabs best practices:** too many break tags make the model speed up or add artefacts. This could become a lint rule (a cap on breaks per request).
- **Prepublish YouTube corpus:** gives measured words per finished minute, which may suit BP-01 better than conventions from script calculators.
- **Rodero, KU review:** the best rate depends on how dense the information is (170 wpm for dense, 190 for light). That's a possible way to settle conflict 2: one band for dense explainer stretches, another for lighter narrative.

**Next searches, once the limit resets:** F0 or rate differences that let listeners tell talkers apart (VOX-03); voice-casting audition practice (VOX-04); speaker-embedding similarity as a drift metric (VOX-08); and animation acting and lip-sync books such as Richard Williams or Ed Hooks (VOX-09). For VOX-01, look for a book or a practitioner video on purpose, since pace has no second source type yet.
