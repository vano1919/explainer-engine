"""The episode rulebook (docs/EPISODE_STANDARDS.md, ES-xx, decision D-51): one versioned ``episode_rules.json`` per video,
written by the ``episode-standards-director`` agent and read by every other step.

What code decides here: only what is objectively checkable (schema, missing evidence, a PASS that contradicts its own
facts, stale sources, open BLOCK/REVIEW items before a paid or irreversible step, a script changed since the last check).
What code never decides: whether a use is lawful, fair or "transformative". Those are contextual calls that the agent
writes down with evidence, and REVIEW sends to the creator or a lawyer. A keyword never blocks a topic (ES intro).

Findings are ``{check, rule, severity, where, detail}`` with severity FAIL (blocks), REVIEW (a person answers it) or INFO.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "episode_rules.schema.json"
BASELINE_PATH = Path(__file__).resolve().with_name("policy_baseline.json")
CHECKPOINTS = ("provisional", "final", "script_lock", "paid_assets", "final_qa")
ROLES = ("research", "script", "voice", "image", "music", "sound", "edit", "metadata", "qa")
# ES-19: hosts that carry pirated or unattributable copies; a rule never cites them
UNUSABLE_SOURCE_HOSTS = ("dokumen.pub", "scribd.com", "z-lib", "libgen", "pdfcoffee.com", "vdoc.pub")
SOURCE_MAX_AGE_DAYS = 180    # ES-02: re-check a policy page older than this (TMR's registry_age rule)
MIN_RATIONALE_WORDS = 8      # ES-04: a non-PASS decision says why in a sentence, not a keyword
MIN_EXCEPTION_WORDS = 20     # ES-10: an exception (fair use, quotation, parody) is argued, not named
SIMILAR = 0.80               # ES-14: two episodes this alike in question/angle/mechanism look interchangeable
# ES-11: wording that claims a notice creates permission or protection (YouTube: credit and "no infringement intended" do
# not make a use fair, V-07); a REVIEW, never an automatic decision
PROTECTIVE = re.compile(r"no copyright infringement intended|fair use|section 107|all rights (?:go|belong) to|"
                        r"i do not own|not my (?:music|footage)", re.I)
PERMISSION_CLAIM = re.compile(r"\b(?:grants?|gives?|creates?|guarantees?)\b.*\b(?:permission|right|licen[cs]e|fair use)\b|"
                              r"\b(?:makes?|keeps?) (?:it|this|the (?:use|video)) (?:legal|lawful|safe)\b", re.I)
REALISTIC_USES = {"realistic_person", "altered_real_footage", "realistic_scene_never_happened", "ai_music_main_focus"}
LEGAL_REVIEW = ("real_person", "actor_likeness", "synthetic_voice", "defamation", "privacy", "franchise", "character")
PLACEHOLDER = re.compile(r"\bTBD\b|<[^>]+>|\?\?\?")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def baseline() -> dict:
    """The channel's verified policy baseline: reusable rule sources with their check dates (MARKET_RESEARCH V-13..)."""
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def load(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def script_hash(script: Path | None) -> str:
    """sha256 of the production script the rulebook was checked against ('none' before a script exists)."""
    if script is None or not Path(script).exists():
        return "none"
    return hashlib.sha256(Path(script).read_bytes()).hexdigest()


def _words(text: str | None) -> int:
    return len((text or "").split())


def _age(day: str, today: date) -> int:
    return (today - date.fromisoformat(day)).days


def _at_least(checkpoint: str, other: str) -> bool:
    return CHECKPOINTS.index(checkpoint) >= CHECKPOINTS.index(other)


def check(rules: dict, checkpoint: str = "provisional", *, today: date | None = None,
          previous: list[dict] | None = None) -> list[dict]:
    """Every check that does not need the script file: run it at the checkpoint the episode is at."""
    if checkpoint not in CHECKPOINTS:
        raise ValueError(f"unknown checkpoint {checkpoint!r}; one of {CHECKPOINTS}")
    today = today or date.today()
    out: list[dict] = []

    def add(check_id: str, rule: str, severity: str, where: str, detail: str) -> None:
        out.append({"check": check_id, "rule": rule, "severity": severity, "where": where, "detail": detail})

    errors = sorted(jsonschema.Draft202012Validator(_schema()).iter_errors(rules), key=lambda e: list(e.path))
    for err in errors:
        add("schema", "ES-01", "FAIL", "/".join(map(str, err.path)) or "(root)", err.message)
    if errors:
        return out
    late = _at_least(checkpoint, "script_lock")      # the script is written to these rules from here on
    paid = _at_least(checkpoint, "paid_assets")      # money or an irreversible step follows
    if _at_least(checkpoint, "final") and rules["status"] != "final":
        add("status", "ES-16", "FAIL", "status", f"checkpoint {checkpoint} needs a final rulebook, this one is provisional")

    # ES-02 / ES-03: every rule has a dated source, and a heuristic is never presented as a binding rule
    rule_ids = [r["id"] for r in rules["rules"]]
    for dup in sorted({i for i in rule_ids if rule_ids.count(i) > 1}):
        add("duplicate_rule", "ES-05", "FAIL", dup, "rule id used twice")
    for r in rules["rules"]:
        kinds = {s["kind"] for s in r["sources"]}
        if r["strength"] == "mandatory" and kinds <= {"creative_heuristic"}:
            add("heuristic_as_mandatory", "ES-03", "FAIL", r["id"], "a creative heuristic cannot be 'mandatory': make it "
                "'recommended' or 'internal_quality', or cite the law, policy, terms or invariant that binds it")
        for s in r["sources"]:
            age = _age(s["checked"], today)
            if age > SOURCE_MAX_AGE_DAYS and s["kind"] in ("law", "platform_policy", "provider_terms"):
                add("stale_source", "ES-02", "FAIL" if paid else "REVIEW", r["id"],
                    f"{s['url']} checked {age} days ago (> {SOURCE_MAX_AGE_DAYS}): re-read the page")
            if any(h in s["url"].lower() for h in UNUSABLE_SOURCE_HOSTS):
                add("unusable_source", "ES-19", "FAIL", r["id"], f"{s['url']} hosts pirated or unattributable copies: cite "
                    "the original publication or a primary page")
            if s.get("verified") is False and r["strength"] == "mandatory":
                add("unverified_source", "ES-02", "REVIEW", r["id"], f"{s['url']} is not verified; say so where it is used")
        if r.get("uncertainty"):
            add("uncertainty", "ES-02", "INFO", r["id"], r["uncertainty"])

    # ES-15 jurisdictions
    juris = rules["jurisdictions"]
    if not juris.get("confirmed_by_creator"):
        add("jurisdictions", "ES-15", "REVIEW", "jurisdictions", f"relevant {juris['relevant']} not confirmed by the "
            "creator (where they live, where the channel is registered, the main audience)")

    # ES-04..ES-12 risk register
    risk_ids = [k["id"] for k in rules["risks"]]
    for dup in sorted({i for i in risk_ids if risk_ids.count(i) > 1}):
        add("duplicate_risk", "ES-05", "FAIL", dup, "risk id used twice")
    disclosure = rules["platform"]["disclosure"]
    has_franchise = False
    for k in rules["risks"]:
        rid, st = k["id"], k["status"]
        if k.get("removed"):
            add("removed", "ES-06", "INFO", rid, f"{k['element']}: removed from the episode")
            continue
        for ref in k.get("rules", []):
            if ref not in rule_ids:
                add("unknown_rule", "ES-05", "FAIL", rid, f"cites {ref}, which the rulebook does not define")
        for j in k.get("jurisdictions", []):
            if j not in juris["relevant"]:
                add("jurisdiction_scope", "ES-15", "FAIL", rid, f"{j} is not among the relevant jurisdictions")
        if st != "PASS":
            missing = [f for f in ("evidence", "rationale", "mitigation") if not (k.get(f) or "").strip()]
            if "dependencies" not in k:
                missing.append("dependencies")
            if missing:
                add("non_pass_record", "ES-04", "FAIL", rid, f"{st} needs {', '.join(missing)}")
            elif _words(k["rationale"]) < MIN_RATIONALE_WORDS:
                add("thin_rationale", "ES-04", "FAIL", rid, "the rationale is a keyword, not a reason "
                    f"(< {MIN_RATIONALE_WORDS} words): say what in the use creates the risk")
        if st == "BLOCK":
            add("block_open", "ES-06", "FAIL" if _at_least(checkpoint, "final") else "REVIEW", rid,
                f"{k['element']}: BLOCK; remove it (removed: true) or replace it before the script is final")
        if st == "ADAPT" and not (k.get("resolved") or "").strip():
            asset_only = k["category"] in ("music", "sound", "image", "footage")  # adapted when the asset is made
            if paid or (late and not asset_only):
                add("adapt_open", "ES-07", "FAIL", rid, f"{k['element']}: ADAPT not applied yet; write what changed in "
                    "'resolved'")
        if st == "REVIEW" and not k.get("decision"):
            who = "creator or legal counsel" if k["category"] in LEGAL_REVIEW else "creator"
            add("review_open", "ES-07", "FAIL" if paid else "REVIEW", rid, f"{k['element']}: waits for a decision ({who})")
        if k["category"] in ("franchise", "character"):
            has_franchise = True

        p = k.get("person")
        if p:
            harmful = p.get("implies_endorsement") or p.get("criminal_or_sensitive_conduct") or p.get("false_statement_of_fact")
            if p["realistic"] and harmful and st == "PASS":
                add("person_realistic_harm", "ES-08", "FAIL", rid, f"{p['name']}: a realistic depiction that implies "
                    "endorsement, sensitive conduct or a false fact cannot be PASS (YouTube 14328491, 2801895, 2801947)")
            if p["realistic"] and not disclosure["required"]:
                add("disclosure", "ES-08", "FAIL", rid, f"{p['name']} is shown realistically: the altered/synthetic "
                    "content disclosure is required (YouTube 14328491)")
            if p.get("voice_imitated") and p["living"] and not (p.get("consent_evidence") or "").strip() \
                    and st in ("PASS", "ADAPT"):
                add("voice_consent", "ES-08", "FAIL", rid, f"{p['name']}: imitating a living person's voice needs "
                    "recorded consent (ElevenLabs use policy s.3); without it the item is REVIEW or BLOCK")
            if p.get("voice_imitated") and not p["living"] and st == "PASS":
                add("voice_deceased", "ES-08", "REVIEW", rid, f"{p['name']}: a synthetic voice of a deceased person; "
                    "check post-mortem rights and provider terms, and whether the voice is needed at all")

        lic = k.get("license")
        if k["source_type"] == "third_party_unlicensed" and st == "PASS":
            add("unlicensed_pass", "ES-09", "FAIL", rid, f"{k['element']}: an unlicensed third-party item cannot be PASS")
        if k["source_type"] in ("licensed", "public_domain", "user_provided") and not lic:
            add("license_missing", "ES-09", "FAIL", rid, f"{k['element']}: {k['source_type']} needs its licence record")
        if lic:
            if lic["basis"] == "unknown" and st == "PASS":
                add("license_unknown", "ES-09", "FAIL", rid, f"{k['element']}: rights basis unknown, so not cleared")
            if lic["verified"] == "not_verified" and st == "PASS":
                add("license_unverified", "ES-09", "FAIL" if _at_least(checkpoint, "final_qa") else "REVIEW", rid,
                    f"{k['element']}: licence not verified yet")
            if lic["basis"] == "exception" and not k.get("exception"):
                add("exception_missing", "ES-10", "FAIL", rid, "a use that relies on an exception names it and argues it")
        exc = k.get("exception")
        if exc:
            if exc["jurisdiction"] not in juris["relevant"]:
                add("exception_scope", "ES-10", "FAIL", rid, f"exception argued under {exc['jurisdiction']}, "
                    "which is not a relevant jurisdiction")
            if _words(exc["analysis"]) < MIN_EXCEPTION_WORDS:
                add("exception_thin", "ES-10", "FAIL", rid, "the exception is named, not argued: purpose, amount, "
                    "market effect and the jurisdiction's conditions")
            if not k.get("decision"):
                add("exception_decision", "ES-10", "FAIL" if paid else "REVIEW", rid, "an exception is decided case by "
                    "case: the creator (and counsel when material) records the decision")

    # ES-08 the disclosure follows the declared AI uses (YouTube 14328491, V-13) and says what the creator does at upload
    realistic_uses = REALISTIC_USES & set(disclosure.get("ai_uses", []))
    if realistic_uses and not disclosure["required"]:
        add("disclosure_uses", "ES-08", "FAIL", "platform.disclosure", f"declared AI uses {sorted(realistic_uses)} are "
            "realistic altered or synthetic content: the disclosure is required")
    if disclosure["required"] and not (disclosure.get("upload_action") or "").strip():
        add("disclosure_action", "ES-08", "FAIL" if _at_least(checkpoint, "final_qa") else "REVIEW", "platform.disclosure",
            "write the upload action: YouTube Studio upload flow, Attributes section, 'AI use': Yes (V-13; the API "
            "field is status.containsSyntheticMedia, V-27, sent by `publish stage` from publish.json, D-56)")

    # ES-11 / ES-12 metadata notices and credits
    meta = rules["platform"]["metadata"]
    for n in meta["notices"]:
        if PROTECTIVE.search(n["text"]):
            add("protective_notice", "ES-11", "REVIEW", n["text"][:40], "a notice does not create permission or fair use "
                "(V-07); keep it only for an accurate purpose (non-affiliation, credit)")
        if PERMISSION_CLAIM.search(n["purpose"]):
            add("notice_purpose", "ES-11", "FAIL", n["text"][:40], f"purpose '{n['purpose']}' claims the notice gives "
                "permission or protection; it can only inform viewers")
    for c in meta["credits"]:
        if c.get("placeholder") or PLACEHOLDER.search(c["text"]):
            add("credit_placeholder", "ES-12", "FAIL" if _at_least(checkpoint, "final_qa") else "INFO", c["text"][:40],
                "a placeholder credit; final metadata uses verified owner, licence and source only")
        if c.get("risk") and c["risk"] not in risk_ids:
            add("credit_risk", "ES-05", "FAIL", c["text"][:40], f"credit points to unknown risk {c['risk']}")

    # ES-13 originality and reused content (YPP, V-14)
    plat = rules["platform"]
    if len(plat["original_contribution"]) < 2:
        add("contribution", "ES-13", "REVIEW", "platform", "name at least two things this video adds that a reader of "
            "the sources would not get (analysis, argument, drawn proof, comparison); a voiceover alone is not one")
    reuse = plat["reuse_risk"]
    if reuse["reads_external_text"]:
        add("reads_external_text", "ES-13", "FAIL", "platform", "the narration reads text the channel did not write "
            "(YPP reused content: readings of others' material)")
    if reuse["third_party_footage_seconds"] > 0:
        add("third_party_footage", "ES-13", "REVIEW", "platform", f"{reuse['third_party_footage_seconds']} s of "
            "third-party footage: needs commentary on it and a rights record per clip")
    if reuse["template_shared_with"]:
        add("template", "ES-14", "REVIEW", "platform", f"shares its template with {reuse['template_shared_with']}: "
            "the substance must differ (YPP inauthentic content)")

    # ES-14 anti-monotony against earlier episodes
    prev = [p for p in (previous or []) if p.get("episode_id") != rules["episode_id"]]
    for p in prev:
        for field in ("central_question", "unique_angle"):
            a, b = rules["identity"][field].lower(), p.get("identity", {}).get(field, "").lower()
            if b and difflib.SequenceMatcher(a=a, b=b).ratio() >= SIMILAR:
                add("same_" + field, "ES-14", "REVIEW", field, f"close to {p['episode_id']}: '{b[:70]}'")
        b = p.get("creative", {}).get("mechanism", "").lower()
        if b and difflib.SequenceMatcher(a=rules["creative"]["mechanism"].lower(), b=b).ratio() >= SIMILAR:
            add("same_mechanism", "ES-14", "REVIEW", "creative.mechanism", f"close to {p['episode_id']}'s mechanism")
    if prev and not rules["creative"]["avoid_patterns"]:
        add("avoid_patterns", "ES-14", "REVIEW", "creative", "earlier episodes exist: list their patterns this one avoids")

    # ES-17 crossover episodes keep the RR rules and their checker
    if has_franchise and not rules["execution"].get("rights_manifest"):
        add("rights_manifest", "ES-17", "FAIL" if late else "REVIEW", "execution",
            "a franchise or character risk needs the RR rights manifest (rights/ip_check.py)")

    # ES-18 every downstream role has its instructions
    missing_roles = [r for r in ROLES if r not in rules["execution"]["roles"]]
    if missing_roles:
        add("roles", "ES-18", "FAIL" if _at_least(checkpoint, "final") else "REVIEW", "execution.roles",
            f"no instructions for {missing_roles}")
    return out


def gate(rules_path: Path, checkpoint: str, script: Path | None = None, *, today: date | None = None,
         previous: list[dict] | None = None) -> list[dict]:
    """``check`` plus the staleness rule (ES-16): a checkpoint passes only when a check record for it exists, made on this
    rulebook version and on the script exactly as it is now. Crossover episodes add the RR checker's findings (ES-17)."""
    rules = load(rules_path)
    found = check(rules, checkpoint, today=today, previous=previous)
    if any(f["check"] == "schema" for f in found):
        return found
    digest = script_hash(script)
    if checkpoint != "provisional":
        recs = [c for c in rules["checks"] if c["checkpoint"] == checkpoint]
        good = [c for c in recs if c.get("rulebook_version", 0) == rules["rulebook_version"]
                and (c["script_sha256"] == digest or checkpoint == "final" and c["script_sha256"] == "none")]
        if not recs:
            found.append({"check": "not_checked", "rule": "ES-16", "severity": "FAIL", "where": checkpoint,
                          "detail": f"no '{checkpoint}' check recorded: the agent re-checks the affected rules, then stamps"})
        elif not good:
            found.append({"check": "stale_check", "rule": "ES-16", "severity": "FAIL", "where": checkpoint,
                          "detail": "the script or the rulebook changed since the last check: re-check the rules the change "
                                    "touches, then stamp again"})
    manifest = rules["execution"].get("rights_manifest")
    if manifest:
        from explainer_engine.rights import ip_check
        mpath = (Path(rules_path).parent / manifest)
        if not mpath.exists():
            found.append({"check": "rights_manifest", "rule": "ES-17", "severity": "FAIL", "where": manifest,
                          "detail": "rights manifest named but missing"})
        else:
            for f in ip_check.check(load(mpath)):
                found.append({"check": f"ip_check.{f['check']}", "rule": f["rule"], "severity": f["verdict"],
                              "where": manifest, "detail": f["detail"]})
    return found


def stamp(rules_path: Path, checkpoint: str, *, by: str, scope: str, script: Path | None = None,
          today: date | None = None, previous: list[dict] | None = None) -> dict:
    """Record that the rules were re-checked at a checkpoint. Refused while the checkpoint still has a FAIL (other than the
    missing stamp itself): a stamp records a review, it never replaces one."""
    from explainer_engine.core.store import write_json_atomic
    found = [f for f in gate(rules_path, checkpoint, script, today=today, previous=previous)
             if f["severity"] == "FAIL" and f["check"] not in ("not_checked", "stale_check")]
    if found:
        raise ValueError(f"cannot stamp {checkpoint}: {len(found)} FAIL ({found[0]['rule']} {found[0]['detail']})")
    rules = load(rules_path)
    rec = {"checkpoint": checkpoint, "date": (today or date.today()).isoformat(), "by": by,
           "script_sha256": script_hash(script), "rulebook_version": rules["rulebook_version"], "scope": scope}
    rules["checks"].append(rec)
    write_json_atomic(Path(rules_path), rules)
    return rec


def brief(rules: dict, role: str) -> str:
    """What one downstream agent must follow, from the one rulebook (no agent writes its own policy)."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; one of {ROLES}")
    ident, ex = rules["identity"], rules["execution"]["roles"].get(role, {"must": []})
    lines = [f"# {rules['episode_id']} rulebook v{rules['rulebook_version']} ({rules['status']}): brief for '{role}'", "",
             f"Question: {ident['central_question']}", f"Angle: {ident['unique_angle']}", f"Tone: {ident['tone']}",
             f"Mechanism: {rules['creative']['mechanism']}", "", "## Must"]
    lines += [f"- {m}" for m in ex["must"]]
    for key in ("inputs", "outputs", "machine_checks", "human_review", "fallbacks"):
        if ex.get(key):
            lines += ["", f"## {key.replace('_', ' ').capitalize()}"] + [f"- {x}" for x in ex[key]]
    mine = [r for r in rules["rules"] if not r.get("roles") or role in r["roles"]]
    lines += ["", "## Rules"] + [f"- {r['id']} ({r['strength']}, {'/'.join(sorted({s['kind'] for s in r['sources']}))}): "
                                 f"{r['requirement']}" for r in mine]
    open_risks = [k for k in rules["risks"] if k["status"] != "PASS" and not k.get("removed")]
    if open_risks:
        lines += ["", "## Risks with a treatment"] + [f"- {k['id']} {k['status']} {k['element']}: {k.get('mitigation', '')}"
                                                      + (f" (done: {k['resolved']})" if k.get("resolved") else "")
                                                      for k in open_risks]
    if role in ("script", "image", "edit", "sound", "music"):
        c = rules["creative"]
        lines += ["", "## Keep", *[f"- {x}" for x in c["visual_invariants"]], "", "## Free to vary",
                  *[f"- {x}" for x in c["may_vary"]], "", "## Avoid (earlier episodes)",
                  *[f"- {a['pattern']} ({a['seen_in']})" for a in c["avoid_patterns"]]]
    lines += ["", "## Escalate", *[f"- {x}" for x in rules["execution"]["escalation"]]]
    return "\n".join(lines) + "\n"


def render(rules: dict) -> str:
    """A human-readable view, generated (never edited by hand: the JSON is the one source)."""
    i = rules["identity"]
    out = [f"<!-- generated from episode_rules.json by explainer_engine.standards render; do not edit -->",
           f"# Episode rules: {rules['episode_id']} (v{rules['rulebook_version']}, {rules['status']})", "",
           f"**Question.** {i['central_question']}  ", f"**Angle.** {i['unique_angle']}  ",
           f"**Beyond a summary.** {i['beyond_a_summary']}  ", f"**Tone / arc.** {i['tone']} / {i['emotional_arc']}  ",
           f"**Stakes / payoff.** {i['stakes']} / {i['payoff']}", "",
           f"Jurisdictions: {', '.join(rules['jurisdictions']['relevant'])} ({rules['jurisdictions']['basis']})", "",
           "## Rules", "", "| Id | Requirement | Strength | Sources (checked) |", "|---|---|---|---|"]
    for r in rules["rules"]:
        src = "; ".join(f"[{s['kind']}]({s['url']}) {s['checked']}" for s in r["sources"])
        out.append(f"| {r['id']} | {r['requirement']} | {r['strength']} | {src} |")
    out += ["", "## Risks", "", "| Id | Element | Status | Treatment |", "|---|---|---|---|"]
    for k in rules["risks"]:
        out.append(f"| {k['id']} | {k['element']} | {k['status']}{' (removed)' if k.get('removed') else ''} | "
                   f"{k.get('mitigation') or k.get('rationale') or ''} |")
    d = rules["platform"]["disclosure"]
    out += ["", f"Disclosure required: {'yes' if d['required'] else 'no'} ({d['reason']})", "",
            "## Checks", ""] + [f"- {c['date']} {c['checkpoint']} by {c['by']}: {c['scope']}" for c in rules["checks"]]
    return "\n".join(out) + "\n"


def summary(found: list[dict]) -> str:
    n = {s: sum(f["severity"] == s for f in found) for s in ("FAIL", "REVIEW", "INFO")}
    return f"{n['FAIL']} FAIL, {n['REVIEW']} REVIEW, {n['INFO']} INFO"


def previous_rulebooks(root: Path, exclude: Path | None = None) -> list[dict]:
    """Earlier episodes' rulebooks in the repository and the job store (ES-14)."""
    found = []
    for p in sorted(list(root.glob("examples/**/episode_rules.json")) + list(root.glob("jobs/**/episode_rules.json"))):
        if exclude is not None and p.resolve() == Path(exclude).resolve():
            continue
        try:
            found.append(load(p))
        except ValueError:
            continue
    return found
