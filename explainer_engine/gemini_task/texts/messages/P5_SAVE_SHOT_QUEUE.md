# P5: save the shot queue (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P5; Q3, Q13. Sent after the video script is approved, in the episode's one chat. It
saves the approved `shot_queue.json` on Drive. Skipped in `self_contained` mode when DRIVE WRITE failed in T0 (the batch
messages carry their own prompts either way, Q1). `{{shot_queue_json}}` is the file's exact text, unchanged;
`{{sha8}}` is its hash, `{{n}}` its picture count, both computed by the exporter.

Placeholders: `episode_id`, `sha8`, `n`, `shot_queue_json`, `drive_root`.

=====BEGIN MESSAGE=====
CHECK | P5 save the shot queue | episode {{episode_id}} | sha {{sha8}}

Make no picture. This is a save: you write one file and answer in three lines.

READ: nothing on Drive. Everything is in this message.

INPUT: the approved picture queue, {{n}} pictures.
-----BEGIN QUEUE-----
{{shot_queue_json}}
-----END QUEUE-----

DO:
1. Save the text between the markers, exactly as given and without any change, as {{drive_root}}/episodes/{{episode_id}}/shot_queue.json.
2. Count the pictures in it.
3. Answer in the form below.

DO NOT:
- edit, reformat, fix or improve any part of the queue;
- make any picture;
- change any other file on Drive.

ANSWER exactly in this form:
SAVED: <the full path> | FAILED <reason>
PICTURES: <the count you found>
SHA: {{sha8}}
=====END MESSAGE=====
