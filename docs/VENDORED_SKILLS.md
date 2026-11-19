# Vendored public skills (W1, P-1, P-2)

Public skill folders copied byte-for-byte at a pinned commit into `.claude/skills/v-<name>/`, each with a `SOURCE.md`
(repo, path, commit, commit date, author, licence, stars seen, what was left out, `sha256  path` for every file).
`python tools/vendor_skill.py verify` re-hashes them and exits 1 on any change; `tests/unit/test_vendored_skills.py` runs it.
Upstream files are never edited. Our rules live in the overlays named in `.claude/skills/INDEX.md` (`story-engine`,
`narration-script`, `film-direction`, ...) and in the validators; the old per-topic skills are in `.claude/skills/_archive/`
and their rule ids in [SKILL_RULE_MAP](SKILL_RULE_MAP.md).

**Why flat `v-` folders and not `vendor/<name>/`:** Claude Code loads a project skill only from
`.claude/skills/<skill-name>/SKILL.md`. Checked 2026-11-19 against https://code.claude.com/docs/en/skills ("Choose where
skills load"): the table lists `Project: .claude/skills/<skill-name>/SKILL.md` and `Nested: <subdir>/.claude/skills/<skill-name>/SKILL.md`;
the nested form means a `.claude/skills` folder inside a sub-directory of the project, not a sub-folder inside `.claude/skills`.
A `vendor/<name>/SKILL.md` would never load. The folder name is the skill name; upstream frontmatter names differ
(for example `cinematic-director` in `v-director-cinematic`), recorded as `name_clash` in each `SOURCE.md`, upstream files untouched.

**Vendoring tool:** `python tools/vendor_skill.py add <owner/repo> <path> <commit> --as v-<name>` (public `git fetch --depth 1 <sha>`,
no credentials), `verify`, `table`. Left out of every copy and listed in `SOURCE.md`: `.git`, `.github`, `.claude` (a nested
`.claude/skills` would load), media and model binaries and secret-looking names (`tests/unit/test_repo_hygiene.py`), files over 1 MiB,
and for the kajisho5 packages the tests, brand, assets, demo and site folders. `tools/` is gitignored in this repo, so the script is
added with `git add -f` like `tools/render_tools`. Licences: all MIT except `smixs/visual-skills` (CC-BY-4.0, `LICENSE` and `NOTICE`
kept: credit Serge Shima). Stars for the S1-S3 additions come from W8's document; others: the GitHub API is blocked in this environment, so the figures in the plan are cited as the plan's, not re-verified.

## Counts

Vendored 39 (below), skipped 15 (with reason, next section), archived 6. The S1-S3 list follows W8's SK-1 verdicts (`docs/SK1_STORY_LAYER_2026-11-20.md` section 5, PR #207) as relayed by the plan thread. The story-layer overlays (`story-engine`, `narration-script`, `dialogue-scenes`, `science-grounding`) are W8 phase B's; W1 leaves them untouched. Note: `v-sw-story-structure` and its siblings link to `../sw-workflow/terms.md`; that relative link points at the upstream layout, the file is in `v-sw-workflow/terms.md`.

## Vendored

| Folder | Stage | Upstream | Path | Commit | Commit date | Licence | Files |
|---|---|---|---|---|---|---|---|
| `v-animate-characters` | S8 | codepawl/creator-generalist | `plugins/3d-generalist/skills/animate-characters` | `007290c354` | 2026-11-17 | MIT | 12 |
| `v-audio-production-skill` | S13 | kajisho5/audio-production-skill | `.` | `03000d0d32` | 2026-11-19 | MIT | 34 |
| `v-color-grading-skill` | S15 | kajisho5/color-grading-skill | `.` | `92da7062a6` | 2026-11-19 | MIT | 31 |
| `v-design-sound` | S13 | codepawl/creator-generalist | `plugins/design-sound/skills/design-sound` | `007290c354` | 2026-11-17 | MIT | 32 |
| `v-director-cinematic` | S4 | wuwangzhang1216/DirectorSKILL | `.` | `c65ae0d144` | 2026-08-31 | MIT | 43 |
| `v-edit-video` | S14 | codepawl/creator-generalist | `plugins/2d-generalist/skills/edit-video` | `007290c354` | 2026-11-17 | MIT | 19 |
| `v-elevenlabs-music` | S11 | elevenlabs/skills | `music` | `97478d1b23` | 2026-11-18 | MIT | 4 |
| `v-elevenlabs-sound-effects` | S11 | elevenlabs/skills | `sound-effects` | `97478d1b23` | 2026-11-18 | MIT | 3 |
| `v-elevenlabs-speech-to-text` | S11 | elevenlabs/skills | `speech-to-text` | `97478d1b23` | 2026-11-18 | MIT | 8 |
| `v-elevenlabs-text-to-speech` | S11 | elevenlabs/skills | `text-to-speech` | `97478d1b23` | 2026-11-18 | MIT | 5 |
| `v-fact-check-workflow` | S1 | jamditis/claude-skills-journalism | `journalism-core/skills/fact-check-workflow` | `a6383bd0c4` | 2026-11-11 | MIT | 3 |
| `v-ffmpeg-skill` | S14 | kajisho5/ffmpeg-skill | `.` | `5055a42e1c` | 2026-11-19 | MIT | 115 |
| `v-hook-writing` | S3 | TheCraigHewitt/skills | `youtube/hook-writing` | `fdbf39b61f` | 2026-05-21 | MIT | 2 |
| `v-ltxv2-video` (D-132) | S9 | artokun/comfyui-mcp | `plugin/skills/ltxv2-video` | `090f9e8fcd` | 2026-11-18 | MIT | 3 |
| `v-media-analysis-skill` | S16 | kajisho5/media-analysis-skill | `.` | `af49b926ff` | 2026-11-19 | MIT | 55 |
| `v-newsjack-fact-check` | S1 | elvisun/newsjack | `skills/fact-check` | `be1368c38e` | 2026-11-16 | MIT | 2 |
| `v-qc-skill` | S16 | kajisho5/qc-skill | `.` | `6fba4efc7c` | 2026-11-19 | MIT | 52 |
| `v-scenario-consistency` | S6/S15/S16 | scenario-labs/skills | `skills/scenario-consistency` | `a14d061fe5` | 2026-11-16 | MIT | 2 |
| `v-scenario-quality-gate` | S6/S15/S16 | scenario-labs/skills | `skills/scenario-quality-gate` | `a14d061fe5` | 2026-11-16 | MIT | 2 |
| `v-scenario-storyboards` | S6/S15/S16 | scenario-labs/skills | `skills/scenario-storyboards` | `a14d061fe5` | 2026-11-16 | MIT | 2 |
| `v-scenario-video-color-grade` | S6/S15/S16 | scenario-labs/skills | `skills/scenario-video-color-grade` | `a14d061fe5` | 2026-11-16 | MIT | 16 |
| `v-source-verification` | S1 | jamditis/claude-skills-journalism | `journalism-core/skills/source-verification` | `a6383bd0c4` | 2026-11-11 | MIT | 12 |
| `v-subtitle-skill` | S18 | kajisho5/subtitle-skill | `.` | `abbf8effae` | 2026-11-19 | MIT | 54 |
| `v-superpowers-subagent-driven-development` | dev | obra/superpowers | `skills/subagent-driven-development` | `22f0b463e7` | 2026-11-03 | MIT | 16 |
| `v-superpowers-systematic-debugging` | dev | obra/superpowers | `skills/systematic-debugging` | `22f0b463e7` | 2026-11-03 | MIT | 7 |
| `v-superpowers-test-driven-development` | dev | obra/superpowers | `skills/test-driven-development` | `22f0b463e7` | 2026-11-03 | MIT | 3 |
| `v-superpowers-verification-before-completion` | dev | obra/superpowers | `skills/verification-before-completion` | `22f0b463e7` | 2026-11-03 | MIT | 2 |
| `v-sw-dialogue` | S2 | jtydhr88/screenwriting-skills | `plugins/screenwriting/skills/sw-dialogue` | `51115f18d1` | 2026-10-02 | MIT | 4 |
| `v-sw-premise-theme` | S2 | jtydhr88/screenwriting-skills | `plugins/screenwriting/skills/sw-premise-theme` | `51115f18d1` | 2026-10-02 | MIT | 4 |
| `v-sw-scene-craft` | S2 | jtydhr88/screenwriting-skills | `plugins/screenwriting/skills/sw-scene-craft` | `51115f18d1` | 2026-10-02 | MIT | 4 |
| `v-sw-story-structure` | S2 | jtydhr88/screenwriting-skills | `plugins/screenwriting/skills/sw-story-structure` | `51115f18d1` | 2026-10-02 | MIT | 4 |
| `v-sw-workflow` | S2 | jtydhr88/screenwriting-skills | `plugins/screenwriting/skills/sw-workflow` | `51115f18d1` | 2026-10-02 | MIT | 5 |
| `v-thumbnail-skill` | S18 | kajisho5/thumbnail-skill | `.` | `751f21a741` | 2026-11-19 | MIT | 38 |
| `v-transcription-skill` | S12 | kajisho5/transcription-skill | `.` | `4be7156228` | 2026-11-19 | MIT | 66 |
| `v-video-editing-skill` | S14 | kajisho5/video-editing-skill | `.` | `2f77b39f55` | 2026-11-19 | MIT | 37 |
| `v-viral-hooks` | S3 | vyralcontent/content-skills | `skills/viral-hooks` | `349e495d97` | 2026-06-22 | MIT | 10 |
| `v-viral-youtube-shorts` | S19 | vyralcontent/content-skills | `skills/viral-youtube-shorts` | `349e495d97` | 2026-06-22 | MIT | 11 |
| `v-visual-skills-image` | S5 | smixs/visual-skills | `image` | `61a60d317f` | 2026-11-06 | CC-BY-4.0 | 26 |
| `v-visual-skills-video` | S5 | smixs/visual-skills | `video` | `61a60d317f` | 2026-11-06 | CC-BY-4.0 | 15 |

## Skipped, with the reason

| Plan row | Candidate | Reason |
|---|---|---|
| S1 | `Jamie-BitFlight/claude_skills` | could not be opened: anonymous `git clone` asks for credentials (private or removed) on 2026-11-19; nothing copied |
| S2 | `danjdewhurst/story-skills` (plot-structure, premise-workshop, scene-craft) | opened and rejected by W8 (wrong scale for a 10-minute explainer); plan thread: do not vendor. A first copy was made and removed |
| S2 | `jtydhr88` `sw-writers-room`, `sw-truby-anatomy` | opened and rejected by W8 (wrong scale); plan thread: do not vendor. A first copy was made and removed |
| S3 | `mohitagw15856` `youtube-script-writer` | W8: rule conflict with our narration rules; not vendored (first copy removed) |
| S1 | `daymade/fact-checker`, `akitaonrails/fact-check` | W8: daymade is for technical specifications; akitaonrails has no licence file: not vendorable |
| S1 | `szoloth/skills` (fact-checker-investigator) | same: not openable anonymously; `v-fact-check-workflow` covers the method, `scripting/claims.py` the citation check |
| S7 | Gemini Chat, `gemini-nano-banana-2.1` API, BFL Klein | services, not skills |
| S9 | `Lightricks/LTX-2` pipelines | opened: its only skill is `.claude/skills/train` (LoRA training), and LoRA training is retired (D-131); the pipelines are code we call through `training/pods/ltx/`, not text to vendor |
| S10 | `codepawl` `2d-generalist` (maps reference) | row says "as a reference" and our maps are code (`maps/`, 34 laws); nothing to load |
| S12 | WhisperX 3.8.6 | a PyPI package, not a skill; `v-transcription-skill` and `v-elevenlabs-speech-to-text` are the vendored text |
| S16 | PySceneDetect, FFmpeg detectors | tools, not skills; `v-qc-skill` and `v-media-analysis-skill` wrap the measurements |
| S17 | Gemini video understanding | Google service docs, not a skill; the defect vocabulary comes from `v-director-cinematic` |
| cartography | any public cartography skill | none stated a licence or none was credible; `cartography` stays ours (SK-1 verdict in the plan) |

## Warnings recorded while vendoring

- `v-design-sound` says licences are only warned about; our rule rejects YouTube-blockable sources (the BBC RemArc set): see `film-direction`.
- `v-scenario-*` assume the Scenario MCP/API; used as method text only (`film-direction`).
- `v-elevenlabs-*` show raw API calls; ours go through the connector and its PreToolUse hook (`elevenlabs-voice`).
- A grep for telemetry, beacons and analytics in the vendored text found none that sends data (`v-ffmpeg-skill/PRIVACY.md` says it sends none).
