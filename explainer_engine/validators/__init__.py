"""Validators (final plan SK-2, P-4, W2): one module per stage, every numeric or yes/no rule of the skills as tested code.

A module ``validators/<stage>.py`` declares ``RULE_IDS`` (the old CRAFT-xx ids and the new VAL-xx ids it enforces) and functions that
return ``qa.gates`` rows (PASS, REVIEW, RETRY, FAIL=BLOCK, NOT_RUN: ``qa/status.py``). Thresholds are read through
``sourced_rules.T`` only; a hypothesis rule (or a BP id the registry lacks) can only be REVIEW, never BLOCK (D-59). A rule of kind
``critic`` is a field-presence check that returns REVIEW, never PASS: taste is judged by a person (REVIEW -> CREATOR_APPROVAL).

The stage names are fixed in ``wave1_briefs/COMMON.md``; ``STAGES`` lists them, ``MODULES`` the ones built so far.
"""
STAGES = ("story", "narration", "shots", "prompts", "pictures", "clips", "voice", "timing", "mix", "edit", "color", "tech_qa",
          "observe", "subtitles", "thumbnail", "shorts")
MODULES = ("story", "narration", "shots", "prompts", "voice", "mix", "edit", "color", "tech_qa", "subtitles", "shorts")


def load(stage: str):
    """The module of one stage (ImportError for a stage not built yet)."""
    import importlib
    if stage not in STAGES:
        raise ValueError(f"unknown validator stage {stage!r}: one of {', '.join(STAGES)}")
    return importlib.import_module(f"explainer_engine.validators.{stage}")


def rule_index() -> dict[str, str]:
    """rule id -> stage, over every built module (the unit test keeps the ids unique)."""
    out: dict[str, str] = {}
    for stage in MODULES:
        for rid in load(stage).RULE_IDS:
            out.setdefault(rid, stage)
    return out
