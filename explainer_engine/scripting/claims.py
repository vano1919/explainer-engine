# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2: Factual Claim & Counterfactual Premise Verification (`D-83`, `D-90`)
# Target Module : explainer_engine/scripting/claims.py
# Target Classes/Symbols : def parse_map(), def load_map(), def from_editorial(), def check()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Update `explainer_engine/scripting/claims.py`:
#    - Distinguish grounding factual claims (which require source citations in `grounding` and `coda` tension zones) from explicitly marked counterfactual premises (`cold_open_type == "reversed_premise"` or counterfactual `escalation` projections).
#    - Ensure historical character quotes (`D-90`) carry either a historical source citation or an explicit `"counterfactual_dramatization": true` marker so factual QA does not conflate dramatic what-if dialogue with unverified factual assertions.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `claims.py` treats all segments uniformly without consulting `/4` `tension_zone` or `cold_open_type`, which can flag `reversed_premise` cold opens or counterfactual dramatic dialogue (`D-90`) as unverified factual claims.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Aligns claim verification with Master Mold v2.1.0's tension-zone architecture: strict factual grounding in `grounding`/`coda` and clearly labeled counterfactual modeling in `cold_open`/`escalation`.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Claims resolve to sources (invariant 5; PV-37, audit 2026-10-19 M1). stdlib only.

The episode's ``claim_map.md`` (next to the production script) is the one place a claim lives: a table row
``| C-01 | sentence | label | source |`` with the labels of the claim map (E established, M a model or one study, R our
reasoning, G a guess, I the episode's invention). The script's lines carry claim ids (``line.claims``). This check is the
deterministic half: every id resolves, every E/M claim names a link, numbers on screen or in the voice have a claim. Whether a
source really says what the sentence says is a reading job (the script critic's claim pass, docs/QA_SPECIFICATION.md).
"""

from __future__ import annotations

import re
from pathlib import Path

ROW = re.compile(r"^\|\s*([A-Z]-?\d{2,3})\s*\|(.*)$")  # C-01, and the C02 / I01 ids of the Napoleon draft (P0c)
URL = re.compile(r"https?://\S+")
NUMBER = re.compile(r"\b\d[\d,.]*\b")
SOURCED = ("E", "M")  # labels that claim the world says so: they need a link


def parse_map(text: str) -> dict[str, dict]:
    """Rows ``| C-01 | sentence | label | source |``; a header row naming its columns (``claim``, ``label``, ``source`` or
    ``note``) is followed instead, so older maps with more columns read too."""
    out = {}
    cols = None
    for line in text.splitlines():
        s = line.strip()
        m = ROW.match(s)
        if not m:
            if s.startswith("|") and not set(s) <= set("|-: ") and cols is None:
                head = [c.strip().lower() for c in s.strip("|").split("|")][1:]
                if "label" in head:
                    cols = head
            continue
        cells = [c.strip() for c in m.group(2).rstrip("|").split("|")]
        if cols:
            row = dict(zip(cols, cells + [""] * len(cols)))
            out[m.group(1)] = {"sentence": row.get("claim") or row.get("sentence", ""), "label": row.get("label", ""),
                               "source": row.get("source") or row.get("note", "")}
        else:
            sentence, label, source = (cells + ["", "", ""])[:3]
            out[m.group(1)] = {"sentence": sentence, "label": label, "source": source}
    return out


def load_map(script_path: Path | str) -> dict[str, dict] | None:
    p = Path(script_path).parent / "claim_map.md"
    return parse_map(p.read_text(encoding="utf-8")) if p.exists() else None


def from_editorial(doc: dict) -> dict[str, dict] | None:
    """The script's own ``editorial`` contract (``production/editorial_gate.py``, EG rules) as a claim map: one home for the
    claims when a script carries them inline, so PV-37 and the editorial gate read the same list."""
    ed = doc.get("editorial") or {}
    if not ed.get("claims"):
        return None
    urls = {s.get("id"): s.get("url", "") for s in ed.get("sources") or [] if isinstance(s, dict)}
    label = {"fact": "E", "estimate": "M", "interpretation": "R", "allegation": "M", "speculation": "G"}
    return {c["id"]: {"sentence": c.get("text", ""), "label": label.get(c.get("type"), "R"),
                      "source": " ".join(urls.get(s, "") for s in c.get("source_ids", []))}
            for c in ed["claims"] if isinstance(c, dict) and c.get("id")}


def check(doc: dict, cmap: dict[str, dict] | None) -> list[dict]:
    """PV-37 findings: [{rule, severity, where, detail}]. Without ``claim_map.md`` the script's ``editorial`` claims count."""
    out = []
    if cmap is None:
        cmap = from_editorial(doc)

    def add(where, detail, sev="FAIL"):
        out.append({"rule": "PV-37", "severity": sev, "where": where, "detail": detail})

    lines = [(f"{seg['id']}#{k + 1}", ln) for seg in doc["segments"] for k, ln in enumerate(seg["lines"])]
    for sh in doc.get("shorts") or []:
        lines += [(f"{sh.get('id', 'short')}#{k + 1}", ln) for k, ln in enumerate(sh.get("lines", []))]
    used = {c for _, ln in lines for c in ln.get("claims", [])}
    if cmap is None:
        if used:
            add("claims", f"lines cite {len(used)} claim ids but there is no claim_map.md next to the script")
        else:
            add("claims", "no claim_map.md next to the script: facts are not tied to sources", "REVIEW")
        return out
    for where, ln in lines:
        for cid in ln.get("claims", []):
            if cid not in cmap:
                add(where, f"claim {cid} is not in claim_map.md")
        if not ln.get("claims") and NUMBER.search(ln["text"]):
            add(where, f"a number with no claim id: {ln['text'][:60]!r}", "REVIEW")
    for cid, row in cmap.items():
        if row["label"][:1] in SOURCED and not URL.search(row["source"]):
            add(cid, f"label {row['label']} but no link in the source column", "REVIEW")
    if cmap and not used:
        add("claims", f"claim_map.md has {len(cmap)} claims but no line cites one: put the ids on the lines", "REVIEW")
    return out
