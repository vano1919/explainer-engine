# Overlay for `v-newsjack-fact-check`: Checking a hard claim, method by method (layer L1, stage S1)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from elvisun/newsjack, page `fact-check` (MIT, commit `be1368c38e`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for our own history scripts: the "speaker" whose burden of
proof we test is our narrator, and the claim we check is a row in the episode's claim map, not a line of PR copy. The
upstream text, with its press-release examples, is this folder's `SKILL.md`; there are no upstream
reference files.

## Where it fits

Skill `science-grounding` builds the claim map; skill `v-fact-check-workflow` walks the whole script before approval;
skill `v-source-verification` checks one source's identity and provenance. This page is the deep method for the few
claims that most often go wrong in history video: superlatives ("the largest", "the first"), counts ("a hundred
thousand men"), famous quotes, single causes ("the war ended because..."), and anything said about today.

## Doctrine, in our terms

- The burden of proof is on our narrator. A line is "fine" only after its row has evidence; plausibility is not
  evidence, and neither is model memory.
- Each claim on its own. A well-sourced paragraph does not lend its rows to the sentence beside it.
- A citation is a link to a page that says it. "Historians say" and "records show" are not citations.
- Keep doubt visible: in the row ("estimates vary"), in the dossier, and in the words the narrator says.
- Research from Gemini and Argon is guidance at about 90 % reliability (creator, 2026-11-07): this deep method is
  for its absolute, unopened claims and for on-screen numbers, not for every line it produced.

## The six methods, in order

1. **Triage.** Sort the script's sentences: story action and feeling (not claims), trivial facts (light check), and
   check-worthy facts (verifiable and consequential if wrong: numbers, superlatives, quotes, causes, dates on screen).
   Write each check-worthy one as `{claim, who says it}`: "{about 100,000 men took part, narrator}".
2. **Lateral reading.** Before trusting a page, leave it: search who publishes it, who funds it, who cites it. A
   handsome heritage site run by a tour company is weaker than a plain archive page.
3. **Climb the tiers.** Tertiary (encyclopedia, listicle) leads to secondary (a historian's book or article) leads to
   primary (the war diary, the letter, the official record, the dataset). A number, a superlative, a quote and a date
   want the highest tier reachable; SCRIPTING_SPEC grades A-D record where you stopped.
4. **Provenance.** For a quote, picture or document: is this the original or a copy of a copy; who made it; when was
   it made versus when it surfaced; where; why does it exist. A famous quote often first appears decades later.
5. **Triangulate.** A fact is established when two or more independent evidence types agree (D-59's two-type logic,
   carried over from the rules registry). Five websites copying one book are one source.
6. **Calibrated rating.** Ask: is it literally true; is there another reading; what does the line assume? A true
   number used to imply something false fails. Then rate.

## The four statuses and our labels

| Status | Means | Claim map result | Script result |
|---|---|---|---|
| Verified | a credible, on-topic source supports it directly | `E` (or `M` for one study or model) with link | keep the wording |
| Disputed | credible evidence contradicts it or the source says something else | row rewritten to what the evidence says | rewrite or cut; a famous myth may become a beat that corrects it |
| Unverifiable | searches do not settle it, or the evidence is too indirect | `G` with a hedge, or no row | hedge the ear can hear, or cut |
| Missing source | the line needs a citation and none can be traced | no row yet | cut until a source exists |

Indirect evidence leans to Unverifiable, never to Verified.

## History-specific traps

| Trap | Example | What to do |
|---|---|---|
| the legend outgrows the record | "the whole front stopped for Christmas" | find the scope the sources give ("parts of the line") |
| a count nobody made | "exactly 100,000 took part" | say "about", note that no count exists |
| a quote first printed much later | a general's famous line | trace to the earliest print; if late, attribute as "reportedly" or drop |
| one local event read as general | one sector's ending as the war's | name the place ("at Houplines") |
| present-day comparison gone stale | "still the record today" | needs a current source; recency words need a fresh check |
| a single cause for a big outcome | "won because of one invention" | label `R`, give the steps and the counter-case |

Recency matters only where the line speaks about now ("today", "still", "the latest"): such a row needs a source
checked this production cycle, and an old one makes it Unverifiable.

## Separate the work

Extraction, verification and adjudication are cleaner apart: build the list first, then gather evidence, then judge.
The script critic is a fresh reader for that reason (`.claude/agents/script-critic.md`); cross-reviews may also go to
the Claude API (`explainer_engine/llm/claude_api.py`) where quality holds (OR-35).

## Output

No separate verdict document. The result lives in the claim map row (label, links), the dossier line (what was
opened, tier reached, conflicts) and, for anything still weak, a sentence in the hand-over to the creator: the
invariant 5 statement of what was and was not verified. Low confidence on a line that matters means the line does not
go to approval as written.

## Checks in code

`explainer_engine/scripting/claims.py` (PV-37: ids resolve, `E`/`M` rows carry links, numbers carry ids); the editorial
gate `python -m explainer_engine.production.editorial_gate <script> --review <review.json>`. Whether a page truly says
what the row says is a reading job and stays by hand.

## Not used from upstream

The PR and pitch framing, the sender-context inputs, the role and byline staleness table (our subjects are not job
titles), the mandatory `## Warning` heading (our hand-over statement does that job), and the references to
`skills/ETHICS.md` and `skills/WHY-NOT-SPAM.md`, which do not exist in this repository.
