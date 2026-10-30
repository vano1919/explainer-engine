# Prompt given to the blind Opus critic (same content, paths shortened; 2026-10-29)
You are an independent, READ-ONLY critic. Do not edit, create or delete any file under /home/user/explainer-engine (you may write nothing at all except your reply). Do not run network or paid calls.

Two writers' rooms produced a script for the same brief: an 8-segment, ~5-minute animated dialogue "what if" docudrama, "What if Napoleon marched into Genghis Khan?", for a faceless 2D YouTube channel whose goal is a STORYTELLER: an interesting idea, told well. Shared facts: .../jobs/ab_agents_2026-10/blind/claim_map.md (C* = facts, I* = invented premise). Candidates (labels are random): reading_X.md and reading_Y.md (plain reading text), and the full production scripts script_X.json / script_Y.json in the same folder. Reference for the rules: docs/STORY_ENGINE.md, .claude/skills/story-engine/SKILL.md. Read the 77 lines of each reading file in full first; then the JSON as needed.

Judge ONLY the results, blind to how they were made. Deliver (<= 90 lines, English):
1. Story first, 1-5 each with 2-3 evidence quotes: premise and dramatic question; escalation and the turn of each scene; character voice distinctness (show don't tell, SC-12; no meta disclaimers SC-11); dialogue craft; ending/payoff of the set-ups; would a viewer stay past 30 s / 2 min.
2. Facts: any spoken fact not backed by the claim map or contradicting it, and any claim id cited that does not support the line.
3. Rule-focus loss: concrete places where a rule of the pages was visibly missed or one layer undermines another. Count them per script.
4. Whole-script coherence: does the edit/sound/shot layer serve the story?
5. Verdict: which script is the better PRODUCT overall, by how much, the 3 most decisive reasons; which differences are noise vs likely systematic. Do not guess how they were made.
