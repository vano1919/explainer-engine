# Vendored: HyperFrames agent skills (HeyGen)

- Source: https://github.com/heygen-com/hyperframes, folder `skills/`, commit `32f562bbd00de00b0aa68acd5621fd00a7b4e0de`
  (2026-11-14, CLI 0.9.46). Licence: Apache-2.0 (`LICENSE`, copied unchanged).
- Taken: `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, text (`.md`, `.txt`) and helper scripts (`.mjs`) only, files
  unchanged. Left out: `hyperframes/assets/` (caption frame presets and fonts), and the skills `media-use` (HeyGen paid media,
  avatars, bundled mp3), `reverse-any-video`, `style-sampling`, `figma`, `slideshow`, `remotion-to-hyperframes`.
- Not loaded as Claude skills on purpose: the entry point is `.claude/skills/hyperframes-lanes/SKILL.md`, which puts the
  channel's rules first (lanes, pin 0.9.39, no telemetry, no HeyGen cloud, our own maps, licence per registry item).
- Update: re-copy from a newer commit, change the commit above and run `tests/unit/test_hyperframes_skills.py`.
