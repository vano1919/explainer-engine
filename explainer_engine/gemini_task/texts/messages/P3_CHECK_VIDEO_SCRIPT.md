# P3: check the video script (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P3 and the review form. Sent after the voice is recorded and timed (the durations come
from the timed read, RN-03) and before P5 saves `shot_queue.json` on Drive. The approved script is on Drive as
`script.md`.

`{{shot_list_json}}` is the shot list exactly as it will be saved (the fields of `04_VIDEO_SCRIPT_RULES.md`: `shot_id`,
the covered line, `route` and its reason, `duration_s`, `shot_type`, `cast`, `place`, `references`, `prompt`, `target`).
The style pack table that names the shot types is in `05_STYLE.md` on Drive.

Placeholders: `episode_id`, `sha8` (of the shot list), `round`, `era_line`, `shot_list_json`, `drive_root`.

=====BEGIN MESSAGE=====
CHECK | P3 video script | episode {{episode_id}} | sha {{sha8}} | round {{round}}

Make no picture. This is a check: you read, judge and advise in words.

READ on Drive, and nothing else: {{drive_root}}/rules/04_VIDEO_SCRIPT_RULES.md, {{drive_root}}/rules/05_STYLE.md, {{drive_root}}/rules/07_REVIEW_PROTOCOL.md, and the approved script {{drive_root}}/episodes/{{episode_id}}/script.md.

INPUT: the shot list as JSON, one object per shot, in viewing order. The episode's era: {{era_line}}
-----BEGIN SHOT LIST-----
{{shot_list_json}}
-----END SHOT LIST-----

DO:
1. Read only the shot descriptions, in order, as if the sound were off. STORY FIRST: can you follow who wants what and what changes, and where do you lose it?
2. Check that every spoken line of the script is covered, in order, and that no shot covers words the script does not have.
3. Check every prompt against "The prompt" of 04 and the words of 05. Quote the shot id and the words of each miss.
4. Check the whole list: references before the shots that need them, reference order, batches, variety, heroes and stakes in frame.
5. Add up seconds per route and fill MEASURED.
6. If you can write to Drive, save the same answer as {{drive_root}}/episodes/{{episode_id}}/reviews/video_script_round{{round}}.md.

DO NOT:
- edit a prompt or the list; propose the fix;
- force the route shares: report them;
- save shot_queue.json or change any other file on Drive.

ANSWER exactly in this form:
REVIEW video_script {{episode_id}} {{sha8}} round {{round}}
VERDICT: APPROVE | APPROVE_WITH_NOTES | REVISE
STORY FIRST: <two or three sentences>
FINDINGS
F1 | BLOCKER|SHOULD|IDEA | <rule id, claim id or URL> | "<shot id>: <quote>" | <problem> | <proposed fix>
MEASURED: shots <n>; spoken lines covered <a> of <b>; seconds map_action/still_25d/video <x>/<y>/<z> %; prompts with a miss <n> of <m>; shots before their references <n>
NOT CHECKED: <what you could not open or verify, or ->
=====END MESSAGE=====
