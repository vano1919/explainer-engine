# P4: Claude's reply to the findings (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P4; Q14; `07_REVIEW_PROTOCOL.md` "The rounds after a check" and "The deadlock block".
Sent after a P1, P2 or P3 answer. Reply round 1 lets Gemini HOLD with a new source; reply round 2 allows only CONCEDE or
DEADLOCK. There is no round 3: each DEADLOCK block becomes a decision card for the creator (options A = Claude's
version, B = Gemini's), and the stage waits for his pick.

`{{replies}}`: one line per finding, written by Claude:
`F1 | ACCEPT | <the change made, one line>`, `F2 | REJECT | <source> | <reason, one line>`, `F3 | NOTED` (an IDEA not
taken). In round 2 only the findings Gemini held. `{{revised_text}}` is the revised artefact after the ACCEPTed changes
(the whole text, so the message stands alone, Q1), or the single line `NO CHANGE` when nothing was accepted;
`{{sha8}}` is its hash. `{{stage}}` is `short_story`, `script` or `video_script`; `{{review_sha8}}` is the hash in the
REVIEW line being answered.

Placeholders: `episode_id`, `stage`, `sha8`, `review_sha8`, `reply_round` (1 or 2), `replies`, `revised_text`,
`drive_root`.

=====BEGIN MESSAGE=====
CHECK | P4 reply round {{reply_round}} | episode {{episode_id}} | stage {{stage}} | sha {{sha8}} | answers review {{review_sha8}}

Make no picture. This is a check: you answer Claude's replies to your findings, in words.

READ on Drive, and nothing else: {{drive_root}}/rules/07_REVIEW_PROTOCOL.md.

INPUT: Claude's reply to each finding, then the revised text.
-----BEGIN REPLIES-----
{{replies}}
-----END REPLIES-----
-----BEGIN REVISED TEXT-----
{{revised_text}}
-----END REVISED TEXT-----

DO:
1. Each ACCEPT: find the change in the revised text. FIXED, or NOT FIXED with the quote.
2. Each REJECT: CONCEDE, or HOLD with a NEW source that neither side has cited. In reply round 2 there is no HOLD: CONCEDE, or write a DEADLOCK block.
3. A finding closed in an earlier round stays closed. Raise a new finding only if a fix broke something, as BROKEN BY F<n>.
4. If you can write to Drive, save the same answer as {{drive_root}}/episodes/{{episode_id}}/reviews/{{stage}}_reply{{reply_round}}.md.

DO NOT:
- argue a NOTED idea or reopen a closed finding;
- HOLD on the same source again: that is a CONCEDE;
- rewrite the text or change any other file on Drive.

ANSWER exactly in this form:
REPLY {{stage}} {{episode_id}} {{sha8}} round {{reply_round}}
F1 | FIXED | NOT FIXED "<quote>"
F2 | CONCEDE | HOLD | <new source> | <one sentence>
N1 | BLOCKER|SHOULD | BROKEN BY F<n> | <source> | "<quote>" | <problem> | <proposed fix>
DEADLOCK {{stage}} {{episode_id}} F<n>
CLAUDE: <its position, one sentence> | SOURCE: <its source>
GEMINI: <your position, one sentence> | SOURCE: <your source>
FOR THE VIEWER: A = <what Claude's version gives>; B = <what yours gives>
OPEN: <finding ids still held, or -> | STAGE: PASS | NOT YET | CREATOR
=====END MESSAGE=====
