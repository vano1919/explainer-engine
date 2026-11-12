# How a check is written, answered and closed

Sources: the creator's message of 2026-11-12 (15:25 UTC: disagreements are settled by sources, a deadlock goes to him);
`docs/GEMINI_CONSISTENCY_RULES.md` (GC-26: every stage needs a closed review record or a creator decision);
the storyteller rule of 2026-10-20 in the project's `CLAUDE.md`.

This file holds for every check: the short story, the script and the video script, and every reply round after them.

## The form of a check

Answer a check in exactly this form, and write nothing before or after it:

```
REVIEW <stage> <episode_id> <sha8> round <n>
VERDICT: APPROVE | APPROVE_WITH_NOTES | REVISE
STORY FIRST: <two or three sentences: does it work, and what is its weakest part>
FINDINGS
F1 | BLOCKER|SHOULD|IDEA | <rule id, claim id or URL> | "<quote>" | <problem> | <proposed fix>
MEASURED: <the numbers the message asks for>
NOT CHECKED: <what you could not open or verify, or ->
```

- `<stage>` is `short_story`, `script` or `video_script`; `<sha8>` and `<n>` are copied from the message header.
- The script check adds a block `CHANGES AGAINST THE APPROVED STORY` between STORY FIRST and FINDINGS (the message
  gives its form). No other block is added.
- One finding per line, numbered F1, F2, ... from the most important down. Many small misses of one kind are one
  finding with up to three quotes.
- The quote is the exact words of the text, short. In a video script it starts with the shot id: `S04: "..."`.
- If there is nothing to report, write `FINDINGS` and `-` on the next line.

## Story first

The channel is a storyteller: an interesting idea, told well. Say first whether the story works and where it is
weakest, then the craft. A check that lists twenty rule misses and never says the middle is dull has missed the one
finding that matters.

## Severity

| Severity | Means | Needs |
|---|---|---|
| BLOCKER | The stage cannot pass: a false fact, an object or event that breaks the era, a rights problem, a broken rule of this pack, or a change against something the creator decided. | a source, always |
| SHOULD | A real weakness Claude must answer: a rule of this pack at review level, a weak turn, a confusing line. | a source |
| IDEA | Advice: what would make it better. Welcome, and never blocks. | nothing |

A finding without a source is an IDEA, whatever it says.

## Sources

A source is one of: a rule id of this pack (the full rule in the document the pack names), a claim id of the episode's
claim map, a dated decision of the creator, or a public page with its URL and the sentence it supports. "I think" and
"viewers prefer" without a page are not sources.

When two sources disagree, this order decides:
1. the creator's dated decision;
2. a rule of this pack, and the repository document over the pack's digest of it;
3. the episode's claim map;
4. an outside page with its URL.

If you find that a digest line differs from the full rule, report it as a finding: that is help.

## Advice is welcome, rewriting is not

The fix is the smallest change that solves the problem, in one sentence, or replacement words for the quoted words
only. Never rewrite a paragraph, a scene or the whole text, and never send a new version. Claude writes; the creator
decides.

## Numbers are a frame

Every number in this pack (words, seconds, shares, counts) is a frame, not a template. The story decides how long a
phrase, a turn or a scene runs; the frame keeps it near what viewers follow easily. A measure within 10 % of a frame
number, over or under, is never a finding. Beyond 10 % it is a finding only if you can say what it does to the viewer;
the finding then needs a source like any other. Never ask for a rewrite just to land a number, and never propose a shape
that exists only to make the arithmetic come out.

## MEASURED and NOT CHECKED

- MEASURED holds the numbers you counted. Mark an estimate with `≈` and say what you counted from.
- NOT CHECKED lists everything the message asked for that you could not do: a file you could not open, a source you
  could not reach, a part you skipped. It is required and it is honest. `-` means you checked everything asked.

## The verdict

- REVISE: at least one BLOCKER.
- APPROVE_WITH_NOTES: no BLOCKER, at least one SHOULD or IDEA.
- APPROVE: nothing, or IDEAs only.

## The rounds after a check

1. **Claude answers every finding**: `ACCEPT` with the change made, `REJECT` with a source, or `NOTED` for an IDEA it
   does not take. With accepted changes it sends the revised text.
2. **Reply round 1.** You answer each REJECT with `CONCEDE`, or `HOLD` with a NEW source (one neither side has cited;
   a HOLD without one counts as CONCEDE). You check each ACCEPT in the revised text: `FIXED` or `NOT FIXED`.
3. **Reply round 2**, only if something is still held. You answer `CONCEDE`, or write a DEADLOCK block. There is no
   third round.

Closed findings stay closed. A new finding in a reply round is allowed only when a fix broke something; it is written
`BROKEN BY F<n>`. New ideas wait for the next stage.

## The deadlock block

```
DEADLOCK <stage> <episode_id> F<n>
CLAUDE: <its position, one sentence> | SOURCE: <its source>
GEMINI: <your position, one sentence> | SOURCE: <your source>
FOR THE VIEWER: A = <what Claude's version gives>; B = <what yours gives>
```

The creator reads it and picks A or B. Neither side argues further.

## When a stage passes

A stage passes when the verdict is APPROVE or APPROVE_WITH_NOTES, or when every BLOCKER is fixed, conceded or decided by
the creator. A deadlock waits for him.

## Never

- Never make a picture in a check.
- Never change a file on Drive except your own review file (`08_FILES_AND_STATE.md`).
- Never reopen what the creator has decided; you may name a risk in it as an IDEA.
