# P1: check the short story (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P1 and the review form; Q13-Q15. Sent in the episode's one chat after P0, before the
creator sees the story (OR-15). The answer is parsed by A2's review intake (form of `07_REVIEW_PROTOCOL.md`).
`{{short_story}}` is the text the creator will read, unchanged; `{{round}}` counts full checks of this stage (1 unless
the story was rewritten after the creator's notes).

Placeholders: `episode_id`, `sha8` (of the short story), `round`, `era_line`, `short_story`, `drive_root`.

=====BEGIN MESSAGE=====
CHECK | P1 short story | episode {{episode_id}} | sha {{sha8}} | round {{round}}

Make no picture. This is a check: you read, judge and advise in words.

READ on Drive, and nothing else: {{drive_root}}/rules/02_SHORT_STORY_RULES.md, {{drive_root}}/rules/07_REVIEW_PROTOCOL.md, and for facts {{drive_root}}/episodes/{{episode_id}}/claim_map.md.

INPUT: the short story Claude wrote for the creator. The episode's era: {{era_line}}
-----BEGIN SHORT STORY-----
{{short_story}}
-----END SHORT STORY-----

DO:
1. Read it once as a viewer would. Then write STORY FIRST: does it work, and what is its weakest part.
2. Check it against sections A to E of 02, in that order. If section A fails, say so first and go easy on craft.
3. Check every factual sentence you doubt against the claim map and the claim's source.
4. Write each finding with its severity, source, quote and the smallest fix (07).
5. If you can write to Drive, save the same answer as {{drive_root}}/episodes/{{episode_id}}/reviews/short_story_round{{round}}.md.

DO NOT:
- rewrite the story or anything longer than the quoted words;
- block on taste: a finding without a source is an IDEA;
- change any other file on Drive.

ANSWER exactly in this form:
REVIEW short_story {{episode_id}} {{sha8}} round {{round}}
VERDICT: APPROVE | APPROVE_WITH_NOTES | REVISE
STORY FIRST: <two or three sentences>
FINDINGS
F1 | BLOCKER|SHOULD|IDEA | <rule id, claim id or URL> | "<quote>" | <problem> | <proposed fix>
MEASURED: parts <n>; turning points <n>, one in the middle third yes|no; parts fact/reasoned/invented <a>/<b>/<c>; words <n>
NOT CHECKED: <what you could not open or verify, or ->
=====END MESSAGE=====
