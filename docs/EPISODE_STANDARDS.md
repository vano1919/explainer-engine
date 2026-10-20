# Episode standards: the per-episode rulebook (D-51)

Canonical for the episode rulebook (`episode_rules.json`), its checks (ES-xx), how the legal, platform and creative
questions of one video are decided, the engagement gate (section 7), story hypotheses (section 8) and the upload disclosure
(section 9). Written by the `episode-standards-director` agent
([.claude/agents/episode-standards-director.md](../.claude/agents/episode-standards-director.md)), loaded by the
`orchestrator` ([ORCHESTRATION](ORCHESTRATION.md) OR-11, OR-12) and passed to every downstream step. Schema:
[`explainer_engine/schemas/episode_rules.schema.json`](../explainer_engine/schemas/episode_rules.schema.json); code:
`explainer_engine/standards/`; verified sources: `explainer_engine/standards/policy_baseline.json` (log: MARKET_RESEARCH
V-13..V-24).

**Principle: constrain specific risks, not creativity.** The rulebook names the few things that are actually risky in
this episode (an asset, a likeness, a passage) and changes only those. A whole topic is never blocked because one asset
has a problem, a keyword never decides anything, and compliance must not make every episode the same story, look or sound.

**What it can and cannot do.** It records evidence, reduces identifiable risk and makes the decisions traceable. It cannot
say that a video is lawful, fair, monetisable or immune from claims: courts decide fair use and fair dealing case by case
(V-17, V-19), YouTube decides its policies, and a PASS only means "no material issue found in the checks performed". Material
uncertainty goes to REVIEW, and to qualified legal review when the creator wants it. Nothing here is legal advice.

## 1. When it runs (checkpoints)

| Checkpoint | When | What must be true (`python -m explainer_engine.standards gate <rules> --at <checkpoint>`) |
|---|---|---|
| `provisional` | topic and format known | identity, jurisdictions, first risks; REVIEW items may stay open |
| `final` | premise, people and characters, asset sources and approach known; before the script is committed | status `final`, no open BLOCK, every role has its instructions |
| `script_lock` | the script is approved (approval #1) | ADAPT items that change the script are applied (`resolved`); the stamp matches this script |
| `paid_assets` | before any paid or high-cost generation (voice, pictures, music) | no open REVIEW or ADAPT, every exception decided, sources fresh; the stamp matches this script |
| `final_qa` | technical and editorial QA, before approval #2 | licences verified, no placeholder credits; the stamp matches the final script |

A changed script or a new rulebook version makes the last stamp stale (ES-16). The agent then re-checks only the rules the change
touches (a new person, a new asset, a new passage) and stamps with a `scope` that says what it re-checked; a broad re-check is
needed only when the premise, the format or the jurisdictions change.

## 2. Decisions on a risk

| Status | Meaning |
|---|---|
| `PASS` | no material issue identified in the checks performed (not a guarantee) |
| `ADAPT` | make the smallest change that resolves or reduces the concern; keep the dramatic purpose, contrast, conflict and stakes |
| `REVIEW` | evidence insufficient: the uncertainty is written down and the creator (or counsel) decides; the decision is recorded |
| `BLOCK` | a clear prohibition, a known rights violation or another substantiated hard constraint; the element is removed or replaced, the topic stays |

Every non-PASS item records the evidence, the affected element, a rationale in sentences, the mitigation and its downstream
dependencies (ES-04).

## 3. Rules (ES-xx)

| ID | Rule | Kind | Checked by |
|---|---|---|---|
| ES-01 | The rulebook matches its versioned schema (unknown fields refused). | project invariant | `standards.rulebook.check` FAIL |
| ES-02 | Every rule cites at least one source with URL, check date and kind (law, platform policy, provider terms, project invariant, measured threshold, creative heuristic); law, policy and terms pages older than 180 days are re-read (REVIEW, FAIL from `paid_assets`); an unverified source is said to be unverified. | project invariant | `check` |
| ES-03 | A creative heuristic is never presented as binding: a rule backed only by heuristics cannot be `mandatory`. | project invariant | `check` FAIL |
| ES-04 | Every ADAPT, REVIEW or BLOCK carries evidence, rationale (a reason, not a keyword), mitigation and dependencies. | project invariant | `check` FAIL |
| ES-05 | Ids are unique and every reference (risk to rule, credit to risk) resolves. | project invariant | `check` FAIL |
| ES-06 | No open BLOCK in a final rulebook: the element is removed or replaced (`removed: true`). | project invariant | `check` |
| ES-07 | ADAPT is applied before the script locks (asset-only ADAPTs before `paid_assets`); REVIEW has a recorded decision before `paid_assets`. | project invariant | `check` |
| ES-08 | Real people (section 4.1, 4.5): a realistic depiction that implies endorsement, sensitive or criminal conduct or a false fact cannot be PASS; any realistic depiction of a real person turns the disclosure on; imitating a living person's voice needs recorded consent; a deceased person's synthetic voice is a REVIEW. | platform policy, provider terms (V-13, V-15, V-16, V-22, V-23) | `check` FAIL / REVIEW |
| ES-09 | Every licensed, public-domain or user-provided asset has its licence record (path, provider, owner, basis, scope, attribution, restrictions, territories, term, monetisation, modification, redistribution, evidence, verified date); an unknown basis or an unlicensed third-party item is never PASS. | project invariant (Q-T16) | `check` FAIL |
| ES-10 | A use that relies on a copyright exception names the jurisdiction and provision, argues it (purpose, amount, market effect, the jurisdiction's own conditions) and has a recorded decision before `paid_assets`. | law (V-17, V-19, V-20) | `check` |
| ES-11 | Notices and disclaimers say only what is true: a non-affiliation note or a credit informs viewers; no notice is described as creating permission or fair use, and no "fair use" or "no infringement intended" text is added by default. | platform policy (V-07) | `check` FAIL / REVIEW |
| ES-12 | Credits may be placeholders while planning; final metadata uses only verified owner, licence and source; nothing is invented. | invariant 5 | `check` FAIL at `final_qa` |
| ES-13 | Originality is assessed separately from copyright: at least two named contributions beyond the sources (an original voiceover alone is not one); narration never reads text the channel did not write; third-party footage needs commentary on it. | platform policy (V-14) | `check` |
| ES-14 | Anti-monotony: an episode whose question, angle or mechanism is close to an earlier episode's, or that shares a template, is reviewed; from the second episode on, the rulebook lists the patterns it avoids. | platform policy (V-14) + creative heuristic | `check` REVIEW |
| ES-15 | Jurisdictions are named per episode (at least the creator's residence, the platform's, the main audience's) and confirmed by the creator; a risk or exception argued under another jurisdiction is refused. | project invariant | `check` |
| ES-16 | A checkpoint passes only with a stamp made on this rulebook version and on the script exactly as it is now; a stamp is refused while the checkpoint has a FAIL. | project invariant | `gate`, `stamp` |
| ES-17 | Episodes with franchise or character risks keep the RR rules: the rulebook names the rights manifest and the gate merges `rights/ip_check.py`. | project invariant (D-26) | `gate` |
| ES-18 | Every downstream role (research, script, voice, image, music, sound, edit, metadata, QA) has its instructions in the rulebook and reads them with `standards brief --role`; no agent writes its own legal policy, licence assumptions or art direction. | project invariant | `check`, orchestrator |
| ES-19 | Source quality: a primary page read first-hand (rights holder, court, statute, platform help page, provider terms) outranks a secondary summary (encyclopaedia, press, fan wiki), which outranks an unsourced inference. A model-written research report, a fan site tagged "official", or a leaked document is never a rule's source until the primary page is read; "not found" is a valid answer. Pirated or unattributable hosts (dokumen.pub, scribd and similar) are refused. | project invariant (V-38) | `check` FAIL on a refused host; the rest by review |

## 4. How the hard questions are handled (guidance for the agent; contextual, never keyword rules)

**4.0 Sources are never spoken (BP-15, the creator 2026-10-19).** A rule that asks for a labelled source (official / reported /
speculation / inference, ES-19) is satisfied in the claim map and the video description, never by the narration reading the
source, a release date, a price or a feature list out loud; `rulebook.brief` tells the script, research, metadata and qa roles
so, and `narration_lint` N-14 flags press-release lines. This supersedes the source-citing wording older rulebooks carried
(ER-07 / RK-08 / RK-16 / RR-10 / SR-04).

**4.1 Public and historical figures.** Not prohibited subjects. Napoleon fighting a dragon, Caesar meeting a robot or
Einstein debating an invented scientist are obviously fictional and fully animated: no disclosure is required for that (V-13),
and the channel already uses named historical caricatures (D-40, RIGHTS_AND_FAIR_USE). The agent assesses the treatment:
could it be mistaken for real footage, does it imply an endorsement, a crime or a false statement of fact, is a likeness
exploited commercially, is the person alive. A stylised scene and a realistic fake endorsement are different cases.
Public-figure status neither authorises every use nor forbids any.

**4.2 Historical and public-domain material.** Facts, events, ideas, folklore and myths stay free to use. There is no
universal age rule: each layer (the original work, an edition, a translation, an adaptation, an artwork, a recording, a
photograph, film footage, a character design) has its own status, and terms differ by jurisdiction and kind of work (US:
V-18; Georgia: life + 70, V-20). When in doubt, keep the historical or narrative purpose and use verified public-domain,
licensed or newly made material.

**4.3 Franchises and crossovers.** Discussing a franchise, its lore, comparing characters or arguing a crossover premise is
not rejected on sight. The agent separates: discussion of facts; original analysis or commentary; original expression from
general ideas and tropes; reproduction of a recognisable protected character or design; use of specific artwork, frames,
dialogue, recordings or logos. Where a risk is material it changes only what is needed and keeps the dramatic purpose,
thematic contrast, conflict and stakes. Stylising, a disclaimer or commentary do not by themselves resolve a copyright
issue. The RR rules ([RIGHTS_AND_FAIR_USE](RIGHTS_AND_FAIR_USE.md)) stay the floor for these episodes (ES-17).

**4.4 Styles and prompts.** Broad styles and techniques (anime, watercolour, comic book, cinematic realism, stop-motion,
stylised 3D) are allowed; copying a specific artist's protected work or a source's distinctive expressive elements is the
risk. A risky prompt keeps its action, mood, composition, conflict and story function and changes the risky component only.
No universal negative-prompt list is added to every request; negative prompts are model-specific (the pod's
`compile.POD_NEGATIVE` is a style control for one model) and a prompt change is tested, not assumed better.

**4.5 Actor likeness, synthetic voices, publicity.** No blanket rule that every screen character becomes generic. The agent
decides whether the output is a literary or historical description, a recognisable screen-specific design, a depiction meant
to resemble an actor, a convincing synthetic person, or an apparent endorsement or impersonation, and prefers an adaptation
that keeps the fictional purpose without an actor's face, performance, cloned voice or implied endorsement. Stylisation is not
an automatic cure; unresolved, material likeness or voice-consent questions are REVIEW. Legal rights, YouTube's privacy and
impersonation policies (V-15, V-16) and provider terms (V-22, V-23) are recorded separately.

**4.6 Music, sound, footage, images.** Original, properly licensed or verified public-domain assets first, each with its
licence record (ES-09). Attribution, a purchase, a "royalty-free" label or a disclaimer is not by itself permission for every
use. No request reproduces a film score, an exact soundtrack, a distinctive cue, a frame or official artwork without a
documented rights basis; a replacement is described by its own musical or visual qualities, never as a close imitation.
Content ID matches cannot be ruled out, even for licensed material: keep the records. Unclear terms are never treated as
cleared: pick a lower-risk asset or escalate.

**4.7 Fair use, attribution, notices.** No Section 107 notice is generated by default. When an exception may matter, the
agent checks it under the episode's jurisdictions (US fair use, UK fair dealing, Georgian quotation; the EU text is not yet
verified, V-21) and writes the analysis (ES-10). Attribution and non-affiliation notes are used when useful and accurate,
and described correctly: they do not create permission or fair use (ES-11). The RR-08 franchise note stays a project rule.

**4.8 Originality, reused and inauthentic content.** Assessed separately from copyright (V-14). The video must show its own
analysis, argument, drawn proof or entertainment; a voiceover over someone else's material is not enough. The rulebook lists
the contributions and the patterns of earlier episodes to avoid (ES-13, ES-14).

## 5. Default jurisdictions

`US` is always relevant: YouTube is operated from the US, the channel is in English for a general audience (D-09) and the US is
the main market (the creator, 2026-10-17, D-52). The creator lives in Georgia (`GE`, confirmed 2026-10-17), the target audience is the US, so the default jurisdictions are
`["US", "GE"]` (`standards/policy_baseline.json`, `channel`); a claim or a publicity question can also arise where the publisher lives. A known large audience in
another country (UK, EU) adds it. The agent does not apply one country's exceptions or terms to another.

## 6. Current state and gaps (audit of `systemic/next-video` at a182195, 2026-10-17)

| Capability | State | Evidence |
|---|---|---|
| Rights rules for crossover episodes | implemented and tested | RIGHTS_AND_FAIR_USE RR-01..13, `rights/ip_check.py`, `tests/unit/test_rights_and_fans.py` |
| Real historical people as caricatures | documented, not enforced | RIGHTS_AND_FAIR_USE "Real historical people" (D-40): estate check "to verify", no field or check; now ES-08 in the rulebook |
| Per-episode rule layer, risk register with statuses | missing | no episode-level rules file; `rights_manifest` covers franchises only; now `episode_rules.json` + ES-01..18 |
| Legal sources jurisdiction-aware | US-only, partly | V-07..V-12 are US and YouTube; no Georgia, UK or EU source; RIGHTS_AND_FAIR_USE assumes US fair use; now V-17..V-21, section 5 |
| Disclosure decision per video | documented, manual | QA_SPECIFICATION policy checklist, V-02; now a rulebook field checked against realistic people (ES-08) |
| Originality / reused / inauthentic content | documented, manual | QA policy checklist, RR-12; now ES-13/14 with a comparison against earlier rulebooks |
| Licence register for every asset | documented, partly implemented | Q-T16, `audio/sfx_library.py` (sounds only); `test_committed_sound_library` fails on this branch because the WAVs are not committed; pictures and music have no licence record; now ES-09 |
| Synthetic voice of a real person | implemented for the narrator | PV-10 (voice described as a sound, never a person), D-39; nothing for character voices; now ES-08 |
| Paid steps gated on rights | missing | `production/paint.py` checked only money caps; now refuses a paid run when the rulebook's `paid_assets` gate fails |
| Rechecks after a script change | missing | no link between a rights check and the script version; now ES-16 (script hash in every stamp) |
| Downstream agents share one rule set | missing | the orchestrator passed CLAUDE.md and PRODUCTION_RULES only; skills carried their own copies of rights hints; now `standards brief --role` |
| Universal negative prompt | not a problem found | `compile.POD_NEGATIVE` is a model-specific style control, not a safety list (4.4) |
| Contradiction: channel scope | contradictory | CLAUDE.md said "public-domain worlds only, D-25" while D-26 allows franchise analysis episodes; CLAUDE.md now cites both |
| Loudness targets | contradictory | P-90 FAIL outside -16..-13 vs scorecard -17.5..-11; Shorts renderer -15 LUFS vs P-101 -14; voice gap 10 dB (P-93, Q-T08) vs 14 dB (scorecard); now one `qa/targets.py`, stricter value kept |
| Shorts length | outdated | P-11 and Q-T12 failed Shorts over 60 s; YouTube counts up to 3 minutes (V-25); now the length bands of BP-12 (REVIEW), over 180 s FAIL (not a Short) |
| Picture routing | contradictory | D-36 (pod for scene pictures) vs D-44 practice (Gemini for Episode 1) vs PRODUCTION_RULES order 5; now D-52: Gemini batch tiers for every picture, PV-40 |
| ElevenLabs takes | money leak | connector default `generations_count` is 4 (V-29); EL-10 said 1 in prose only; now enforced by the PreToolUse hook |
| Deterministic enforcement in Claude Code | missing | no `.claude/settings.json` hooks; now one PreToolUse hook on the ElevenLabs connector |
| Story alternatives, beat jobs, engagement check | missing | no record of rejected premises; segments had `purpose` text only; now `story_hypotheses.json`, `job`, `qa/engagement.py` |
| Duplicate orchestrator or pipeline | none | one orchestrator, one production script (D-43); this layer adds no second pipeline |

## 7. The engagement gate (anti-boredom, Q-E16)

Run `python -m explainer_engine.qa.engagement <production_script.json>` before script approval and again before the final render.
The code names the measurably weak beats: ENG-1 no question in the opening, ENG-2 a flat run of three beats with the same job or
no reveal/payoff at all, ENG-3 a spoken number that nothing on screen shows (ED-10), ENG-4 wording repeated from another beat,
ENG-5 an ending that never returns to the central question, ENG-6 a beat longer than about 100 s without a turn. Each is REVIEW: a
person answers it with a revision of that beat (cite the segment) or a reason to keep it. Then the seven questions of the gate are
answered for the whole script: a compelling and accurate opening question; each section changes knowledge, expectations, stakes or
feeling; evidence is shown where a claim benefits from being seen; reveals are carried by the edit and the sound; no repetitive
narration, needless explanation, generic visuals or purposeless music; memorable moments specific to this topic; an ending that
answers. The fix is a better beat, never more cuts, more sound effects or another colour. The episode passes only when it is both
reasonably compliant under the checks performed and meaningfully engaging.

Retention without deception: hooks are accurate, a delayed answer is delivered, uncertainty is never invented, thumbnails and
titles keep the video's promise (Q-E03, Q-E10). Visual variety comes from motivated changes inside one art bible (shot size,
angle, depth, light direction, diagrams, maps, quiet moments), not from switching styles (UR-22); a deliberate style change is
written into the rulebook with its purpose.

## 8. Story hypotheses before the treatment (Q-E17)

Before the narrative is committed, at least three genuinely different premises are written into `story_hypotheses.json`
([schema](../explainer_engine/schemas/story_hypotheses.schema.json)) with question, audience reason, stakes, surprise, payoff,
evidence for and against (claim ids or URLs), uncertainties, counterarguments, visual and audio opportunities and rights risks.
Each is researched fairly with the `science-grounding` skill and scored twice, separately: `evidence` (sources, without the story)
and `narrative` (stakes, surprise, payoff, without the evidence). `python -m explainer_engine.research.hypotheses <file>` refuses
fewer than three, a selected premise with evidence under 3 (a good story never makes up for weak evidence), and a beat sheet without a
payoff; it asks why a premise lost that scored higher on both. The selected premise's beat sheet (each beat with its job: hook,
question, explanation, evidence, complication, reveal, emotional pause, humour, payoff, transition) becomes the production script's
segment `job`s (PV-39), and its rights risks become rulebook risks.

## 9. Disclosure at upload (4.9)

The rulebook records which AI uses the video contains (`platform.disclosure.ai_uses`: script help, stylised imagery, a realistic
person, altered real footage, a realistic scene that never happened, a synthetic voice, AI music as the main focus, minor aesthetic
edits). A realistic use turns the disclosure on (ES-08, V-13); script help, clearly stylised or fantastical drawn imagery and minor
edits do not by themselves. A required disclosure carries `upload_action` (YouTube Studio upload flow, Attributes, "AI use": Yes;
the API field is `status.containsSyntheticMedia`, V-27). The staging upload (D-57) sends that field from the episode's
`publish.json` disclosure decision; `submitted` stays false here, and the creator confirms the flag in Studio before going public.
