Write one Markdown file with proposed text for the repo's skills and CLAUDE.md. These are PROPOSALS for the owner to paste; do not write them into the skills or CLAUDE.md themselves.

The source of truth is docs/MAP_25D_RULES.md (attached). Use its wording and status markers (APPROVED / PROPOSAL / NOT yet in place). Do not invent rules or numbers.

Output sections:

A. CLAUDE.md: one paragraph to add under the v4.3 header, pointing to docs/MAP_25D_RULES.md, stating that the five camera moves and the Liberation Serif map font rule apply to every map and 2.5D shot, that no-melt is a gate for animated shots with PROVISIONAL limits, and that film style is chosen per episode by the owner.

B. .claude/skills/cartography/SKILL.md: a replacement for the font line (the current skill text mentions Fredoka/Inter; the film presets use Liberation Serif; the raster renderer still uses Inter, state that), plus one bullet list: the five camera moves; bridges (captions repeat narration words, timed by the word clock); map text big and readable (numbers PROPOSAL, owner approves on samples); film style per episode.

C. .claude/skills/animation-principles/SKILL.md: one short section "No melting, no warping": a face is never warped; a shot marked animated must pass the no-melt gate (qa/technical_gate.check_no_melt, PROVISIONAL limits); numbers not yet measured end to end.

D. .claude/skills/shot-visuals/SKILL.md: one short section on map and 2.5D shots: the five camera moves, the film style of the episode, no static or orbit.

E. "Applies to past videos": a short paragraph saying a rule added now is checked on new renders; past videos are not re-rendered automatically; a re-check of past videos is MISSING and needs an owner decision.

Keep the whole file under 150 lines. Plain Markdown. No code changes.
