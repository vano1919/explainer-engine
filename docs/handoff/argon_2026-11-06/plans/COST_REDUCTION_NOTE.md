# Cost-reduction note (creator's reminder, 2026-11-06 16:46 UTC; postponed, due again after the 8-clip pilot)

Source: the project memory entry written when the creator asked for a reminder. Every number below is an estimate from that entry,
not a measurement (`config/job_speeds.json` has no measured LTX or Qwen row yet).

- The creator's target for an episode is US$10-15. The 11-06 recount puts a 12-minute episode at about **$13-15**, and 15 minutes at
  about $17-19: at or above the target.
- The 12-minute breakdown: LTX for 60 % of the runtime = about 430 s of clips, about $10-11 with retries (the plain rate quoted is about
  $0.016 per second, which would be about $6.9 for 430 s with no retries; the gap is the retry allowance, not measured); Qwen about $3;
  the pod's fixed part about $0.5.
- Ideas on record, none decided: fewer failures (retries are the biggest soft cost); a still with a camera move (free) instead of an
  LTX clip wherever the shot does not need real motion; reuse and cut clips; reuse stills across shots (reuse planner R0-R5).
- The creator's 2026-11-06 18:54 UTC order (Fable thread) widens this into the Argon task: LTX minimisation, shots derived from the
  script, reusability, pictures built from assets, measure what makes everything several times cheaper. See `../README.md`.
- Due: the cost-reduction plan on 2026-11-07 10:00 Tbilisi (memory entry), to be raised again after the 8-clip pilot results.
