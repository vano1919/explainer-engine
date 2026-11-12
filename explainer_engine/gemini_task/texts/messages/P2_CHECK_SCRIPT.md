# P2: check the script (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P2 and the review form. Sent after the creator approved the short story (OR-15) and
before he approves the script (OR-17). The approved short story is already on Drive as `short_story.md`; Gemini proves
it opened that file by quoting its first line.

`{{script}}` is the script as plain text, one line per spoken line, each starting with its scene id and speaker:
`S03 | NARRATOR | ...` or `S03 | KAEL to MIRA | ...`, with each scene's header (present, whose scene, wants) on the
line before its first spoken line. The BP numbers are filled from `explainer_engine/standards/sourced_rules.json` at
export (`03_SCRIPT_RULES.md` cites the same rows).

Placeholders: `episode_id`, `sha8` (of the script), `round`, `era_line`, `script`, `drive_root`,
`bp:BP-01.wpm_target`, `bp:BP-104.narration_block_max_s`, `bp:BP-72.turn_words_max`, `bp:BP-76.turn_gap_s`,
`bp:BP-105.nominal_narrator_share|percent`.

=====BEGIN MESSAGE=====
CHECK | P2 script | episode {{episode_id}} | sha {{sha8}} | round {{round}}

Make no picture. This is a check: you read, judge and advise in words.

READ on Drive, and nothing else: {{drive_root}}/rules/03_SCRIPT_RULES.md, {{drive_root}}/rules/07_REVIEW_PROTOCOL.md, the approved story {{drive_root}}/episodes/{{episode_id}}/short_story.md, and for facts {{drive_root}}/episodes/{{episode_id}}/claim_map.md.

INPUT: the full script, every spoken line with its scene and speaker. The episode's era: {{era_line}}
-----BEGIN SCRIPT-----
{{script}}
-----END SCRIPT-----

DO:
1. Compare the script with the approved story first. List every change: an added or missing event, another ending, a hero who wants something else.
2. Write STORY FIRST: does it still work as a story, and what is its weakest part.
3. Check it against 03: story, scenes and dialogue, narration, the two strict rules line by line, facts, era and picture sense.
4. Count words at {{bp:BP-01.wpm_target}} words a minute and fill MEASURED.
5. If you can write to Drive, save the same answer as {{drive_root}}/episodes/{{episode_id}}/reviews/script_round{{round}}.md.

DO NOT:
- rewrite a line, a scene or the script; propose the smallest fix;
- treat a change against the story as a defect by itself: name it;
- change any other file on Drive.

ANSWER exactly in this form:
REVIEW script {{episode_id}} {{sha8}} round {{round}}
VERDICT: APPROVE | APPROVE_WITH_NOTES | REVISE
STORY FIRST: <two or three sentences>
CHANGES AGAINST THE APPROVED STORY
APPROVED STORY OPENED: "<its first line>" | FAILED <reason>
C1 | ADDED|REMOVED|CHANGED | "<story words or ->" | "<script words or ->"
FINDINGS
F1 | BLOCKER|SHOULD|IDEA | <rule id, claim id or URL> | "<quote>" | <problem> | <proposed fix>
MEASURED: narrator share <x> % of spoken words (nominal {{bp:BP-105.nominal_narrator_share|percent}}); longest narration block <n> words ≈ <s> s (frame {{bp:BP-104.narration_block_max_s}} s); longest spoken turn <n> words (frame {{bp:BP-72.turn_words_max}}); longest stretch without a turn ≈ <s> s (limit {{bp:BP-76.turn_gap_s}} s)
NOT CHECKED: <what you could not open or verify, or ->
=====END MESSAGE=====
