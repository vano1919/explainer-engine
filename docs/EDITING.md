# Editing rules (ED-xx)

Creator notes of 2026-10-17 after the first full cut of Episode 1: audible jumps between read chunks (worst in Day 1), a zoom
that snaps back to the default view on the same picture, two music tracks plus the tick plus a bed all under the voice, and a
request for a faster final cut and a more mysterious feel at no extra cost. How to apply them: skill `editing-style`.

| ID | Rule | Enforced by |
|---|---|---|
| ED-01 | **Chunks join without a seam.** Every read chunk is levelled to the same gated loudness (spread of chunk loudness at most 1.5 dB) before the join, and each chunk edge gets a 30 ms fade inside the silence, so the join adds no click and moves no word. | [code] `audio/seams.py`, `production words` report `seams` |
| ED-02 | **A zoom never snaps back.** When consecutive shots show the same picture, the next shot starts exactly where the previous one ended (zoom and horizontal offset). The zoom may keep growing up to 1.25; past that the next shot eases out, never jumps. A different picture starts at its own default view, on a cut or a dissolve. | [code] `production/continuity.py`, check ZOOM-1 in `check_timed` |
| ED-03 | **One music at a time.** Music tracks never overlap except in a crossfade of at most 3 s (the earlier track fades out while the next fades in). The tick (`clockwork_loop`) is music and obeys this too; it sits at least 6 dB under every other music track and stays under 24 dB below the voice. At most two background layers (music or bed) at any moment, plus the voice. | [code] PV-29, `timing` crossfade extension |
| ED-04 | **Few transition types, one look.** Hard cut is the default. A 1 s dissolve (UR-14) opens every period after the first; the episode opens with a 1 s fade from black and closes with a 1.5 s fade to black. No other transition type (no wipes, spins, flashes). One constant film look over the whole episode (slight vignette, fine grain), never switched on and off. | [code] `assemble` (`transition` per shot, `look`) |
| ED-05 | **Pace by content.** Dangerous or uncertain beats cut faster (3-5 s); wonder and big reveals hold longer (7-9 s); a joke lands on a cut right after its last word; a period boundary breathes (dissolve plus half a second of silence). Cuts stay inside punctuated pauses (UR-12). | [editorial] skill `editing-style`; UR-12, UR-31 code |
| ED-06 | **Speed is a finishing step.** A faster final cut is made from the finished video by time-compressing picture and sound together (pitch kept), never by re-synthesising the voice. The creator is shown 1.05, 1.10 and 1.15 on the same two excerpts and picks one; only then is the final file made. Shorts keep their own tempo (SH rules). | [code] `finish/speed.py` |
| ED-07 | **Look and listen before reporting.** After a change to the cut, open frames on both sides of three joins of the same picture and three picture changes, and listen to the three loudest chunk joins; write what was seen and heard. | [editorial] OR-07 |

**Not allowed without the creator's yes:** a paid effect pack, a stock clip, a new music track, any step that costs money.
Every effect above is made by our own code at no cost.
