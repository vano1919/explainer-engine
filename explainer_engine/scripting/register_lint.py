"""The AI register (Blueprint P3, docs/STORY_ENGINE.md "Register (RG)", D-86). stdlib only.

The words and the shapes a language model overuses read as machine writing to a listener, and the creator's point 1 of
2026-10-29 is that no script may sound like that. One module, one lexicon (the registry, never copied): tier 1 is BP-140
(house, FAIL), tier 2 and the structure densities are BP-114 (hypothesis, REVIEW).

    RG-01  a tier-1 word, or a sentence-initial Additionally/Moreover/Furthermore,        FAIL (BP-140)
    RG-02  more soft words and phrases in one segment than BP-114 allows                   REVIEW
    RG-03  structure densities per 1,000 spoken words (narration only)                     REVIEW
    RG-04  a summarising opener on a segment's first line or the script's last line        REVIEW
    RG-05  an allow-list entry without a reason or a note (the term still fires)           FAIL (invariant 7)

Scope: what the viewer hears or reads (narrator and hero lines, bubbles, cards, HUD text). Prompt text for image and video
models is never read here. Matching is plain, not negation-aware: "never delve" is still the register. Dialogue gets words
and phrases but no structure densities (a hero may speak in triplets).

Call sites: ``production/validate`` PV-61 (``doc_findings``), ``narration_lint.lint`` N-16/N-17 (``findings``),
``film_shots.check`` KP-46 (``film_shots_findings``), the script-critic page (this module's report).

    python -m explainer_engine.scripting.register_lint <script.json | film_shots.json | text.md> [--allow FILE] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

RULES = ("RG-01", "RG-02", "RG-03", "RG-04", "RG-05")
ALLOW_FILE = "register_allow.json"
REASONS = ("literal", "quote", "name")
TAG = re.compile(r"\[[^\]\n]*\]")  # delivery tags are not words
QUOTED = re.compile(r"[\"“”][^\"“”]+[\"“”]")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")

REVIEW_HITS = SR.T("BP-114", "review_hits_per_300_words")
DENSITY_LIMITS = {
    "triplet": SR.T("BP-114", "rule_of_three_per_1000"),
    "negation_pivot": SR.T("BP-114", "negation_pivot_per_1000"),
    "participial_tail": SR.T("BP-114", "participial_tail_per_1000"),
    "em_dash": SR.T("BP-114", "em_dash_per_1000"),
}
RATHER_THAN_CHAIN = SR.T("BP-114", "rather_than_chain_min")

TRIPLET = re.compile(r"\b[\w'-]+, [\w'-]+,? (?:and|or) [\w'-]+\b", re.I)
NEGATION_PIVOT = re.compile(r"\b(?:it'?s|this is|that'?s|it was|that was) not [^.;!?]{1,60}?[.;,—-]\s*(?:it'?s|but|that'?s|this is|it was|that was)\b"
                            r"|\bnot (?:just|only|merely) [^.;!?]{1,60}?\bbut\b", re.I)
PARTICIPIAL_TAIL = re.compile(r", (?!and\b|or\b|but\b)[a-z]+ing\b [^.!?]{3,}[.!?]")
RATHER_THAN = re.compile(r"\brather than\b", re.I)
EM_DASH = re.compile(r"—| -- | – ")
NOMINALISATION = re.compile(r"\b\w{4,}(?:tion|ment|ness|ity)s?\b", re.I)


def _norm(s: str) -> str:
    return TAG.sub("", s).replace("’", "'").replace("‘", "'")


def _compile(terms: list[str], *, whole: bool = True) -> re.Pattern:
    alt = "|".join(sorted((re.escape(t.replace("’", "'")).replace(r"\ ", r"\s+") for t in terms), key=len, reverse=True))
    return re.compile(rf"(?<![\w'-])(?:{alt})(?![\w'-])" if whole else rf"(?:{alt})", re.I)


_CACHE: dict = {}


def lexicon() -> dict:
    """The compiled lists, built once from the registry: ``tier1`` (BP-140 words), ``tier1_openers`` (the sentence-initial
    connectors), ``tier2`` (BP-114 words and phrases), ``openers`` (summarising openers), ``watch`` (counted only)."""
    if not _CACHE:
        openers1 = [p.rstrip(",") for p in SR.T("BP-140", "register_phrases")]
        _CACHE.update(
            tier1=_compile(SR.T("BP-140", "register_words")),
            tier1_openers=re.compile(r"(?:%s)," % "|".join(re.escape(p) for p in openers1), re.I),
            tier2=_compile(list(SR.T("BP-114", "lexicon")) + list(SR.T("BP-114", "phrases"))),
            openers=re.compile(r"(?:%s)" % "|".join(re.escape(p.rstrip(",")) for p in SR.T("BP-114", "openers")) + r"\b,?", re.I),
            watch=_compile(list(SR.T("BP-114", "watch"))),
        )
    return _CACHE


def sentence_initial(text: str, pos: int) -> bool:
    head = text[:pos].rstrip(" \t\"'“‘([—-")
    return head == "" or head[-1] in ".!?\n:"


def _quoted_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in QUOTED.finditer(text)]


def check_allow(allow: list[dict] | None) -> list[dict]:
    """RG-05: an entry needs a reason (literal, quote, name) and a note; the findings, the valid entries are ``valid_allow``."""
    out = []
    for e in allow or []:
        if e.get("reason") not in REASONS or not str(e.get("note", "")).strip() or not str(e.get("term", "")).strip():
            out.append({"rule": "RG-05", "where": str(e.get("term", "?")), "severity": "FAIL",
                        "detail": f"allow-list entry {e.get('term')!r} needs a reason ({', '.join(REASONS)}) and a note naming the "
                                  "segment or line it covers (or 'all'); the term is not exempted"})
    return out


def valid_allow(allow: list[dict] | None) -> list[dict]:
    return [e for e in allow or [] if e.get("reason") in REASONS and str(e.get("note", "")).strip() and str(e.get("term", "")).strip()]


def _allowed(term: str, where: str, allow: list[dict]) -> bool:
    for e in allow:
        t = e["term"].lower().strip()
        if not term.lower().startswith(t):
            continue
        toks = set(re.findall(r"[A-Za-z0-9_.-]+", e["note"].lower()))
        if "all" in toks or where.lower() in e["note"].lower() or (where.split()[:1] and where.split()[0].lower() in toks):
            return True
    return False


def scan(text: str, *, kind: str = "narration", allow: list[dict] | None = None, where: str = "") -> list[dict]:
    """Every register hit of ``text``: ``{rule, tier, term, start, end, sentence}`` (tier 1, 2 or ``watch``). Exempt: a match in
    a quotation of a line that cites a claim is the caller's call (``doc_findings``), a capitalised proper noun in the middle of a
    sentence, and an allow-list entry whose note covers ``where``. ``kind`` is narration, dialogue or card."""
    text = _norm(text)
    lex = lexicon()
    allow = valid_allow(allow)
    hits = []

    def add(rule, tier, m):
        if tier != "watch" and _allowed(m.group(), where, allow):
            return
        if tier in (1, 2) and m.group()[:1].isupper() and not sentence_initial(text, m.start()):
            return  # a name ("the Renowned"), not the register
        s0 = max(text.rfind(".", 0, m.start()), text.rfind("!", 0, m.start()), text.rfind("?", 0, m.start())) + 1
        e0 = min([i for i in (text.find(".", m.end()), text.find("!", m.end()), text.find("?", m.end())) if i >= 0] or [len(text) - 1])
        hits.append({"rule": rule, "tier": tier, "term": m.group(), "start": m.start(), "end": m.end(),
                     "sentence": text[s0:e0 + 1].strip()})

    for m in lex["tier1"].finditer(text):
        add("RG-01", 1, m)
    for m in lex["tier1_openers"].finditer(text):
        if sentence_initial(text, m.start()):
            add("RG-01", 1, m)
    for m in lex["tier2"].finditer(text):
        add("RG-02", 2, m)
    for m in lex["watch"].finditer(text):
        add("RG-02", "watch", m)
    return sorted(hits, key=lambda h: h["start"])


def densities(text: str) -> dict[str, float]:
    """Counts and per-1,000-word densities of the structural tells (narration only); nominalisations are reported, not judged."""
    t = _norm(text)
    n = max(1, len(WORD.findall(t)))
    counts = {"triplet": len(TRIPLET.findall(t)), "negation_pivot": len(NEGATION_PIVOT.findall(t)),
              "participial_tail": len(PARTICIPIAL_TAIL.findall(t)), "em_dash": len(EM_DASH.findall(t)),
              "rather_than": len(RATHER_THAN.findall(t)), "nominalisation": len(NOMINALISATION.findall(t))}
    out: dict = {"words": n}
    for k, c in counts.items():
        out[k] = c
        out[f"{k}_per_1000"] = round(c * 1000 / n, 2)
    return out


def _f(rule: str, where: str, detail: str, bp: str) -> dict:
    return {"rule": rule, "where": where, "severity": SR.level(bp), "detail": detail}


def _unit(text: str, *, kind: str, where: str, allow: list[dict] | None, opener_text: str | None = None,
          structure: bool = True, closer_text: str | None = None, quoted_ok: bool = False) -> list[dict]:
    """The findings of one unit (a segment, a scene, a whole narration text)."""
    out = []
    hits = scan(text, kind=kind, allow=allow, where=where)
    if quoted_ok:
        spans = _quoted_spans(_norm(text))
        hits = [h for h in hits if not any(a <= h["start"] and h["end"] <= b for a, b in spans)]
    for h in [h for h in hits if h["tier"] == 1]:
        out.append(_f("RG-01", where, f"AI-register word {h['term']!r} (BP-140): {h['sentence'][:80]!r}; say it plainly, or if the "
                                      "sense is literal add an allow-list entry with a note (RG-05)", "BP-140"))
    soft = [h for h in hits if h["tier"] == 2]
    n = max(1, len(WORD.findall(_norm(text))))
    if len(soft) > max(1.0, REVIEW_HITS * n / 300):
        out.append(_f("RG-02", where, f"{len(soft)} soft AI-register hits in {n} words ({', '.join(sorted({h['term'].lower() for h in soft}))}); "
                                      f"at most {REVIEW_HITS} per 300 (BP-114)", "BP-114"))
    if structure:
        d = densities(text)
        for k, limit in DENSITY_LIMITS.items():
            if d[k] > max(1.0, limit * d["words"] / 1000):
                out.append(_f("RG-03", where, f"{d[k]} {k.replace('_', ' ')}(s) in {d['words']} words, over {limit} per 1,000 (BP-114): "
                                              "the repetition is the tell", "BP-114"))
        if d["rather_than"] >= RATHER_THAN_CHAIN:
            out.append(_f("RG-03", where, f"'rather than' {d['rather_than']} times (a chain of {RATHER_THAN_CHAIN} or more, BP-114)", "BP-114"))
    lex = lexicon()
    for label, line in (("opens", opener_text), ("closes", closer_text)):
        if line and lex["openers"].match(_norm(line).lstrip(" \"'“")):
            out.append(_f("RG-04", where, f"the {'segment' if label == 'opens' else 'script'} {label} with a summarising connector "
                                          f"({_norm(line)[:30]!r}, BP-114): start on the story", "BP-114"))
    return out


def findings(text: str, *, kind: str = "narration", where: str = "-", allow: list[dict] | None = None) -> list[dict]:
    """RG-01..RG-04 on one free text (``narration_lint.lint`` calls this); RG-05 on the allow-list is added once per call."""
    first = next((p for p in text.splitlines() if p.strip()), "")
    last = next((p for p in reversed(text.splitlines()) if p.strip()), "")
    return check_allow(allow) + _unit(text, kind=kind, where=where, allow=allow, opener_text=first, closer_text=last,
                                      structure=(kind == "narration"))


def _lines(doc: dict):
    for seg in doc.get("segments", []):
        yield seg["id"], seg.get("lines", [])
    for sh in doc.get("shorts", []):
        yield f"short {sh.get('id', '?')}", sh.get("lines", [])


def doc_findings(doc: dict, *, allow: list[dict] | None = None) -> list[dict]:
    """PV-61 on a ``production_script/3``: narrator lines get RG-01..RG-04, hero lines RG-01 and RG-02 only; a quotation inside a
    line that cites a claim is exempt; RG-04 also on the script's last line."""
    out = check_allow(allow)
    narr_all: list[str] = []
    units = list(_lines(doc))
    for ui, (sid, lines) in enumerate(units):
        narr = [ln["text"] for ln in lines if not ln.get("speaker")]
        narr_all += narr if not sid.startswith("short") else []
        cited_quotes = {ln["text"] for ln in lines if ln.get("claims")}
        for k, ln in enumerate(lines, 1):
            where = f"{sid} line {k}"
            kind = "dialogue" if ln.get("speaker") else "narration"
            for f in _unit(ln["text"], kind=kind, where=where, allow=allow, structure=False, quoted_ok=bool(ln.get("claims"))):
                if f["rule"] == "RG-01":
                    out.append(f)
        whole = " ".join(ln["text"] for ln in lines)
        first, last = (lines[0]["text"] if lines else None), (lines[-1]["text"] if ui == len(units) - 1 and lines else None)
        for f in _unit(whole, kind="dialogue", where=sid, allow=allow, structure=False, opener_text=first, closer_text=last,
                       quoted_ok=bool(cited_quotes)):
            if f["rule"] != "RG-01":
                out.append(f)
    text = "\n".join(narr_all)
    if text.strip():
        for f in _unit(text, kind="narration", where="narration", allow=allow, structure=True):
            if f["rule"] == "RG-03":
                out.append(f)
    return out


def film_shots_findings(doc: dict, *, allow: list[dict] | None = None) -> list[dict]:
    """KP-46 on ``film_shots/1|2``: shot narration (full lint, joined per scene and for the film), dialogue and card or HUD text
    (words and phrases only)."""
    out = check_allow(allow)
    by_scene: dict[str, list[str]] = {}
    shots = doc.get("shots", [])
    for sh in shots:
        if isinstance(sh.get("narration"), str):
            by_scene.setdefault(sh.get("scene", "-"), []).append(sh["narration"])
        d = sh.get("dialogue")
        if isinstance(d, dict) and isinstance(d.get("text"), str):
            out += [f for f in _unit(d["text"], kind="dialogue", where=f"{sh['id']} dialogue", allow=allow, structure=False)
                    if f["rule"] == "RG-01"]
        for key in ("hud", "card", "bubble", "label"):
            if isinstance(sh.get(key), str):
                out += [f for f in _unit(sh[key], kind="card", where=f"{sh['id']} {key}", allow=allow, structure=False) if f["rule"] == "RG-01"]
    scenes = list(by_scene)
    for i, sc in enumerate(scenes):
        lines = by_scene[sc]
        for f in _unit(" ".join(lines), kind="narration", where=sc, allow=allow, structure=False, opener_text=lines[0],
                       closer_text=lines[-1] if i == len(scenes) - 1 else None):
            out.append(f)
    allnarr = "\n".join(l for sc in scenes for l in by_scene[sc])
    if allnarr.strip():
        out += [f for f in _unit(allnarr, kind="narration", where="narration", allow=allow, structure=True) if f["rule"] == "RG-03"]
    return out


def load_allow(where: Path | str) -> list[dict]:
    """``register_allow.json`` next to a script file, or inside an episode folder."""
    where = Path(where)
    p = (where if where.is_dir() else where.parent) / ALLOW_FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def stale(today: date | None = None) -> dict | None:
    """BP-140's lexicon is dated: one REVIEW once ``recheck_days`` have passed since ``checked_on`` (the list drifts per model)."""
    checked = date.fromisoformat(SR.T("BP-140", "checked_on"))
    age = ((today or date.today()) - checked).days
    if age > SR.T("BP-140", "recheck_days"):
        return {"rule": "RG-02", "where": "lexicon", "severity": "REVIEW",
                "detail": f"the AI-register lexicon was last checked on {checked} ({age} days ago): re-check it (BP-140)"}
    return None


def report(doc_or_text, *, allow: list[dict] | None = None) -> list[dict]:
    """Findings of a document or a text, plus the one stale-lexicon REVIEW; what the critic reads."""
    if isinstance(doc_or_text, dict):
        found = film_shots_findings(doc_or_text, allow=allow) if str(doc_or_text.get("schema", "")).startswith("film_shots") \
            else doc_findings(doc_or_text, allow=allow)
    else:
        found = findings(doc_or_text, allow=allow)
    s = stale()
    return found + ([s] if s else [])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("path")
    p.add_argument("--allow")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    path = Path(a.path)
    allow = json.loads(Path(a.allow).read_text(encoding="utf-8")) if a.allow else load_allow(path)
    raw = path.read_text(encoding="utf-8")
    found = report(json.loads(raw) if path.suffix == ".json" else raw, allow=allow)
    if a.json:
        print(json.dumps(found, indent=1))
    else:
        for f in found:
            print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
        fails = sum(f["severity"] == "FAIL" for f in found)
        print(f"{fails} FAIL, {len(found) - fails} REVIEW")
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
