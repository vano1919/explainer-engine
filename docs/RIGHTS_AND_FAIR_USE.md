# Rights and fair use rules (crossover episodes of fictional worlds)

Canonical home of the rights rules (RR-xx). They apply to every episode that discusses someone else's fictional world
(books, film, TV, games), decided in D-26. Code enforces the checkable part: `explainer_engine/rights/ip_check.py` runs on
each episode's rights manifest and blocks the package on any FAIL.

**What these rules can and cannot do.** Fair use is a legal defence that courts decide case by case; no rule, percentage,
credit line or disclaimer makes a use safe ([V-07](MARKET_RESEARCH.md), [V-10](MARKET_RESEARCH.md)). These rules keep our
episodes on the side courts and YouTube describe as more likely fair: commentary and analysis with a new purpose, little
taken, nothing that substitutes for the original. They lower the risk; they do not remove it. This is not legal advice:
before monetising franchise episodes, and whenever a removal request arrives, the creator decides whether to ask a
lawyer.

**Scope.** These rules are the floor for franchise episodes; every episode's wider legal, platform and creative questions
(people, likeness, voices, licences, jurisdictions, originality) are decided in its rulebook ([EPISODE_STANDARDS](EPISODE_STANDARDS.md),
ES-17 links the two). The sources below are US law and YouTube policy; other jurisdictions (Georgia, UK) are in V-19, V-20.

## What the sources say (verified 2026-10-16, see MARKET_RESEARCH B.2)
- YouTube: credit does not make a use fair, "no infringement intended" does not protect, "entertainment only" does not
  help; adding new expression or meaning is more likely fair; factual works are more likely fair than fiction; taking the
  "heart" of a work can fail even when small; market harm counts against (V-07).
- Strikes come from valid removal requests, not from Content ID claims; disputing a claim without a valid reason can lead
  to a removal request and then a strike; 3 strikes = channel termination; a strike expires after 90 days with Copyright
  School (V-08).
- Trademarks: use that is "likely to cause confusion" about the source is prohibited (V-09).
- US Copyright Office: transformative uses "add something new, with a further purpose or different character" and should
  not substitute for the original; large portions weigh against; no word count is safe (V-10).
- Warhol v. Goldsmith (2023): a new style or meaning is not enough when the use serves the same purpose commercially; the
  purpose must differ (V-11). Harry Potter Lexicon case (2008): a fan reference work lost because it took more than its
  analytic purpose needed and its plot summaries were too close to the books (V-12).

## The rules
| ID | Rule | Checked by |
|---|---|---|
| RR-01 | Purpose is analysis, commentary or criticism: every scene asks or answers something about the worlds (rules, logistics, power, economics, history parallels). No episode is a retelling, a "what happens next" story or a fan sequel. | rights manifest `purpose`; editorial QA |
| RR-02 | Zero third-party media: no footage, stills, screenshots, trailers, posters, key art, maps, music, sound effects, voice clips, fonts or logos from the books, films, shows or games. | `third_party_media` must be empty (FAIL) |
| RR-03 | All pictures are our own drawings in our style. Characters are our own interpretations from text descriptions or neutral archetypes; never traced, never imitating a production's designs, costumes, sets, props, actor likenesses or official maps. No image-generator prompt names a franchise, a character, an actor or "in the style of" one. | `art` block (FAIL) |
| RR-04 | Quote little: only lines we analyse, attributed, at most 2 sentences / 40 words each, at most 6 per episode; never read passages aloud at length. | `quotes` (FAIL / REVIEW) |
| RR-05 | Recap only what the analysis needs: plot recap at most 20 % of the narration (REVIEW above 20 %, FAIL above 35 %); never "the complete story of" a franchise. | `recap_words / narration_words` |
| RR-06 | Add something the original does not: sourced analysis, real-history or science parallels, original scenarios argued from each world's own rules. The original's purpose is the story; ours is the test. | editorial QA (rubric "Originality" >= 4 for franchise episodes) |
| RR-07 | Fan theories: name and link the person or thread, summarise in our words, never copy their text or art (fan art is its creator's copyright); using their wording or pictures needs written permission. | `fan_theories` (FAIL) |
| RR-08 | Names only to identify the subject, in plain text (title, description, narration); no logos, no official title lettering, nothing implying endorsement. The description carries: "Unofficial fan analysis. Not affiliated with or endorsed by the rights holders." (against confusion; it does not create fair use). | `description_has_unofficial_note`, thumbnail block |
| RR-09 | Thumbnails: our own art only; no actor faces, key art, logos or screenshots. | `thumbnail` block (FAIL) |
| RR-10 | Never leaked, unaired or pirated *material* (files, footage, screenshots, code, drafts, copies) as a source or drawing reference. Leaked *information* may be discussed (creator 2026-10-17: the channel is entertainment) when it is labelled "reported leak", comes from a named outlet, and does not directly and unambiguously harm a person (private data, safety, a person's livelihood); doubt means leave it out. | `uses_leaks` (FAIL; means leaked material) |
| RR-11 | Music and sound: own, CC0 or licensed with a record; never a franchise theme or a sound-alike of it. | licence register (Q-T16) |
| RR-12 | The channel stays itself: the mascot, the "worlds collide" frame and the public-domain episodes remain; franchise episodes are a series inside it, not the identity (directive section 3). Share of franchise episodes is a parameter (P-121). | publishing plan |
| RR-13 | When a claim or removal request arrives: do not dispute a Content ID claim without a real reason; record it in the incident log; for a strike, stop new franchise uploads, complete Copyright School, consider a retraction request or a counter notification only with a genuine fair use basis, and decide with the creator (and a lawyer if needed). | incident log in `channel/incidents.json` |
| RR-14 | Every franchise episode states its **commentary target**: what it says about the source work itself (its systems, tropes, economy), in one full sentence, and each act serves it. A story that only puts characters into a new adventure shares the source's commercial purpose and is the weak case (Warhol v. Goldsmith; strongest case is parody or criticism of the source, Campbell v. Acuff-Rose; V-38). A risk heuristic, never a guarantee. | `commentary_target` (FAIL) |
| RR-15 | Official screenshots, trailer frames or key art are private study only: never an image input, reference upload or "in the style of this picture" to a generator (Google generative AI use policy, B-11; the output may resemble the input). | `official_images_as_generator_input` (FAIL) |
| RR-16 | Invented parody brands and the franchise name stay narrative props: never on merchandise, an app or anything sold (Jack Daniel's v. VIP, V-38). Plain-text name in title, description and narration is allowed (nominative use, RR-08); the stylised logo, font or game's mark is not. | `merch_or_product_use` (FAIL) |

## Real historical people as characters (creator's decision 2026-10-16, D-40)
Episodes may use real historical figures (Einstein, Newton, Franklin, Darwin, Curie...) as named caricature heroes in a
commentary and parody format, drawn by us (`assets/characters/scientists_v0`), never traced from a photograph. What this
decision does not do: it does not make every use safe. Rules of work: (1) the narration says plainly that what the people say
and do is invention (the Day 1 intro does); (2) no endorsement, no claim a person said a real quote unless it is one; (3) no
merchandise or ads built on a likeness; (4) before publishing, check whether an estate licenses the name or likeness
(Albert Einstein's rights are actively managed, to verify) and record the result in the rights manifest; (5) a takedown or
claim follows RR-13. Nothing here is legal advice; the creator carries the decision.

