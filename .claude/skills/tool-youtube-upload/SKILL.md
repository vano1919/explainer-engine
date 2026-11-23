---
name: tool-youtube-upload
description: Stage a finished episode and its Shorts on YouTube as unlisted or private through our own publish package - never public - only after the owner's recorded approval and a clean publish checklist, with made-for-kids false, the synthetic-media flag from the disclosure checklist, the right channel confirmed, video ids written to the state file the moment they exist so a rerun never uploads twice, resumable sessions, and the daily quota counted first. Use when an approved episode or Short is ready to stage, when an upload was interrupted, when sign-in is needed, and when anyone suggests another upload tool or a public setting.
---

# YouTube staging upload, the tool (layer L32, after packaging)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for D-57's staging flow. The
words that ship (title, description, chapters, tags) are skill `tool-vidiq-metadata`; the thumbnail is skill
`v-thumbnail-skill`; Shorts are skill `shorts-for-video`. Going public is the owner's click in Studio, never ours.

## When to use, when not

- Use for each piece as soon as it passed its own checks (standing order 9 in
  [docs/PRODUCTION_RULES.md](../../../docs/PRODUCTION_RULES.md)): the long video, then each Short, one at a time.
- Not to publish, schedule or flip visibility. There is no public option anywhere in the package, no `publishAt`, and no
  `videos.update`; the OAuth scopes cannot change visibility after upload.
- Not through any other uploader: the vidIQ connector's upload and update tools, a community CLI, or a raw API script.
  `explainer_engine/publish/` is the only upload code (invariant 4).

## The package (read before citing)

| Part | Code | Role |
|---|---|---|
| CLI | `python -m explainer_engine.publish stage|thumbnail|auth|auth-url|auth-finish` | dry run by default |
| Plan | `explainer_engine/publish/plan.py` | builds each `videos.insert` body from `publish.json` and the script; field rules; pure |
| Stage | `explainer_engine/publish/stage.py` | gate, channel check, uploads, state, quota, review checklist |
| Client | `explainer_engine/publish/youtube.py` | stdlib Data API v3: token refresh, resumable insert, `thumbnails.set`, read-only lists; refuses any privacy outside `STAGE_PRIVACY` (unlisted, private) |
| Sign-in | `explainer_engine/publish/auth.py` | one-time consent; token to gitignored `tools/youtube/token.json` or the env var `YOUTUBE_TOKEN_B64`; never printed |
| Thumbnail | `explainer_engine/publish/thumbnail.py` | the paid premium paint, only with `--generate --approved-by` |
| Checklist | `explainer_engine/qa/publish_check.py` | PC-01..PC-10, free |

## The procedure

1. **The OK is recorded** (PC-08, invariant 4): unlisted staging of a piece that passed its tests rests on the owner's
   standing order 9 of 2026-10-19, cited in `--confirm`; anything that order does not cover (a re-stage of a changed
   file, a case you are unsure of) needs his own message, named the same way. Without a recorded OK `stage` blocks.
2. **Checklist clean**: `python -m explainer_engine.qa.publish_check <episode>/publish.json --episode <episode>` with no
   FAIL; PC-09 needs the rulebook's `final_qa` stamp and a scorecard without FAIL.
3. **Sign-in** (once per token): on the owner's PC `publish auth <client_secret.json>`, or from the cloud
   `publish auth-url`, the owner consents on his phone, then `publish auth-finish '<the 127.0.0.1 address>'`. A fresh link
   per upload session. The token never goes into chat, logs, git or the vault (VT-05).
4. **Dry run**: `python -m explainer_engine.publish stage <episode>` writes `<episode>/publish/youtube_stage.json` and
   prints every body, the quota estimate and the Studio review list. Read it: title, privacy, `selfDeclaredMadeForKids`
   false (PC-02, D-17), `containsSyntheticMedia` as the disclosure checklist decided (PC-03), category and language.
5. **Channel check**: the token's channel must equal `EXPLAINER_YT_CHANNEL`; a mismatch stops before any upload. The
   wrong Google account is the commonest failure.
6. **Stage**: `stage <episode> --yes --confirm '<who said OK, where>' [--privacy private] [--only long,SH01]`. Order: the
   long video, its thumbnail, then each Short with a link back to the long video.
7. **State and resume**: every video id is written to `<episode>/publish/youtube_state.json` the moment the API returns
   it, keyed by the file's sha256; a rerun skips what is there. An interrupted upload resumes from its session file
   (`.sessions.json`, gitignored). A same-titled upload on the channel that is not in the state is refused; if it is that
   file, `--adopt SH01=<id>` records it without uploading again.
8. **Read back and report**: the ids, the privacy each came back with, processing status, and the Studio steps left to
   the owner (thumbnail check, location, end screens, going public).

## Quota

`stage` estimates before sending. From the docstring (developers.google.com quota page, read 2026-10-19, V-47):
`videos.insert` has its own daily bucket of calls; `thumbnails.set` and list calls draw from the shared daily units.
Re-read the official page when a new quota error appears; a `quotaExceeded` waits for the Pacific midnight reset, an
`uploadLimitExceeded` is the channel's own limit.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `refusing: --confirm` | no recorded OK | ask the owner; record who and where |
| Channel mismatch | the consent used another account | new `auth-url` with the right account |
| Thumbnail 403 | custom thumbnails need a verified account | owner verifies the account; rerun only the thumbnail |
| Same title refused | an earlier run uploaded but lost the state | check the video in Studio, then `--adopt` |
| Token expired | refresh token revoked or old | `auth-url` / `auth-finish` again |
| Chapters missing after upload | PC-01 failed or the block was edited | fix `publish.json`, re-run the checklist |

## Audit checklist (from laurigates/claude-plugins, page `youtube-upload`, used as a list, not a dependency)

Check our package against it after any change: private or unlisted default and no public path; the kids flag explicit,
never inferred; the synthetic-media flag a recorded decision; a dry run that prints the exact body without network; the
channel shown before writing; read-back after every write; the token outside the repo; field limits and chapter rules
checked before upload. Where we differ on purpose: no `videos.update` at all (their tool merges and resends parts; we
leave edits to Studio so nothing can flip visibility).

## Sources (what each taught; licence noted in one line)

- laurigates/claude-plugins, page `youtube-upload` (MIT, commit `fba5be185c`): the audit list above.
- ericrisco/rsc-harness, page `youtube-api` (MIT, commit `28a51a9100`): user OAuth instead of a service account,
  resumable insert, quota facts in one place.
- mengbingrock/youtube-upload-skill (no licence file, commit `652dd16056`): read for the idea of a local token folder only.
