"""Narration lint: the mechanical part of the `narration-script` skill (.claude/skills/narration-script/SKILL.md).

    python -m explainer_engine.scripting.narration_lint examples/stone_age/day1_v3/narration_tts.txt

Reads a TTS narration file (one paragraph = one beat; ElevenLabs v4 audio tags allowed) and reports FAIL / REVIEW
findings, rule ids N-01..N-15 as in the skill. It cannot judge whether a line is funny or intriguing; it catches the
defects the creator heard in the first reads: questions that fall, stress on the wrong word, too many slowing
ellipses, beats that end closed, no conversational colour, stage directions read aloud. Every number comes from the
sourced rules registry (``standards/sourced_rules.py``, docs/SOURCED_RULES.md): N-01 BP-03 (the four hook forms),
N-03 BP-16 (ellipses per beat), N-05 BP-06 (sentence length), N-06/N-07 BP-17 (questions, interjections), N-10 BP-18
(question contour), N-11 BP-04 (the 30-second contract), N-12 BP-07 (spoken register), N-13 BP-08 (numerals), N-14 BP-15
(press-release lines, one lexicon with SC-07), N-15 BP-10 (no narration hold over one second). Each finding's severity is
its rule's severity in the registry (the FAIL band of a rule; its review band stays REVIEW). N-02, N-04, N-08 and N-09
have no number.

On a production script, ``doc_findings`` lints what only the script knows: N-14 on the narrator's lines (a hero may name
a date inside a scene, SC-07) and N-15 on each narration line's ``pause_after``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

from explainer_engine.edit import shot_rules as SHOT
from explainer_engine.standards import sourced_rules as SR

TAG = re.compile(r"\[([^\]\n]*)\]")
YES_NO = {"can", "could", "would", "will", "is", "are", "was", "were", "do", "does", "did", "has", "have", "had",
          "should", "shall", "may", "might", "must", "isn't", "aren't", "wasn't", "don't", "doesn't", "didn't",
          "won't", "wouldn't", "couldn't", "can't"}
WH = {"what", "who", "whom", "whose", "which", "where", "when", "why", "how"}
INTERJECTIONS = {"hmm", "mm", "mmm", "oh", "ah", "aha", "uh-oh", "well", "right", "okay", "huh", "eh", "oops",
                 "wow", "yep", "nope", "ugh"}
LOOP_OPENERS = ("but", "and then", "then", "until", "except", "tomorrow", "now", "so", "and yet", "which means",
                "unless", "only", "still", "and tomorrow", "because")
DELIVERY_TAGS = {"curious", "excited", "happy", "sad", "angry", "nervous", "sarcastic", "surprised", "tired",
                 "warmly", "whispers", "whispering", "softly", "dramatically", "mischievously", "cautiously",
                 "slowly", "quickly", "deep voice", "raspy", "breathless", "laughs", "laughs softly", "chuckles",
                 "sighs", "exhales", "gasps", "clears throat", "short pause", "pause", "long pause", "playfully",
                 "conspiratorially", "matter of fact", "impressed", "amused", "thoughtful", "suspenseful",
                 "intrigued", "deadpan", "hesitant", "triumphant"}
STAGE = re.compile(r"\b(standing|pacing|walking|grinning|smiling|music|sound effect|sfx|camera|cut to)\b", re.I)
ACRONYMS = {"TV", "UK", "US", "USA", "DNA", "NASA", "OK", "BC", "BCE", "AD", "CE", "GTA", "IRS", "LCN", "BAWSAQ", "MP"}
# BP-03: edit/shot_rules.GREETINGS (welcome, hello, hi, hey, today's video, in this video, subscribe) widened with the
# channel-name and "today we look at" openers YouTube names as the lines that are not a hook.
GREETINGS = re.compile(SHOT.GREETINGS.pattern + r"|\b(today we('ll| will| are going to)? (look|talk|dive|explore|see)"
                       r"|my name is|this is (the )?channel|on this channel)\b", re.I)
PREVIEW = re.compile(r"\b(you'?ll see|you will see|watch what happens|by the end|here'?s what happens|let'?s find out"
                     r"|we'?re about to|what happens when)\b", re.I)
NUMBER_WORDS = re.compile(r"\b(hundred|thousand|million|billion|dozen)\b", re.I)
NUMERAL = re.compile(r"\d[\d,.]*")
TURN = re.compile(r"\b(but|until|except|unless|and yet)\b", re.I)  # BP-04: the gap opens on a question or a turn
YOU = re.compile(r"\b(you|your|yours|you'?re|you'?ll|you'?ve|you'?d)\b", re.I)
# BP-07 passive heuristic: a form of "be" (or "get"), an optional adverb, then a regular -ed participle (at least two
# letters before "ed", so "red" and "fed" do not count) or a common irregular one. "is seven" and "was open" never
# match; "is tired" does (an adjective, but it reads as passive to the ear anyway).
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being|get|gets|got)\s+(\w+ly\s+)?(\w{2,}ed|given|taken|broken|written|"
                     r"driven|eaten|forgotten|seen|known|shown|thrown|grown|blown|drawn|worn|torn|born|built|bought|"
                     r"brought|caught|taught|thought|sold|told|held|found|lost|made|paid|said|sent|spent|kept|left|met|"
                     r"put|set|shot|cut|hit|won|run|done|gone|begun|sung|hung|struck|stuck|beaten|chosen|frozen|"
                     r"hidden|ridden|stolen|spoken|woken)\b", re.I)
MAX_SENTENCE_WORDS = SR.T("BP-06", "max_words")  # BP-06: over this REVIEW
HARD_MAX_SENTENCE_WORDS = SR.T("BP-06", "hard_max_words")  # BP-06: over this FAIL
MEDIAN_SENTENCE_WORDS = SR.T("BP-06", "median_max")
MAX_COLD_OPEN_WORDS = SR.T("BP-03", "max_cold_open_words")
CONTRACT_WORDS = SR.T("BP-04", "contract_words")
BANNED_CONTRACTIONS = {c.lower() for c in SR.T("BP-07", "banned_contractions")}
PASSIVE_SHARE_MAX = SR.T("BP-07", "passive_share_max")
YOU_PER_WORDS = SR.T("BP-07", "you_per_words")
NUMERALS_PER_SENTENCE = SR.T("BP-08", "numerals_per_sentence_max")
PRESS_PHRASES = [p.lower() for p in SR.T("BP-15", "phrases")]
PRESS_PATTERNS = [re.compile(x, re.I) for x in SR.T("BP-15", "patterns")]  # BP-15: the one lexicon N-14 and SC-07 share
WORDS_PER_QUESTION = SR.T("BP-17", "words_per_question")  # N-06 (hypothesis, REVIEW)
WORDS_PER_INTERJECTION = SR.T("BP-17", "words_per_interjection")  # N-07 (hypothesis, REVIEW)
WH_QUESTION_MAX_WORDS = SR.T("BP-18", "wh_question_max_words")  # N-10 (hypothesis, REVIEW)
ELLIPSES_PER_BEAT, ELLIPSES_FAIL_OVER = SR.T("BP-16", "ellipses_per_beat_max"), SR.T("BP-16", "ellipses_fail_over")  # N-03
MAX_HOLD_S = SR.T("BP-10", "max_hold_s")  # N-15: a narration hold never over this (BP-10)
HOOK_FORMS = tuple(SR.T("BP-03", "hook_forms"))  # N-01: the forms, in the registry's order


def sev(rule_id: str) -> str:
    """The severity a rule's (FAIL-band) finding carries: the registry's, so a rule's severity changes in the JSON only."""
    return SR.rule(rule_id).get("severity", "REVIEW")


def press_release(text: str, patterns: bool = True) -> str | None:
    """BP-15: the press-release phrase or pattern a line uses, or None (N-14 and SC-07 both call this). ``patterns`` False
    keeps to the phrases: a production_script/1 or /2 keeps its old contract (D-58), whose rules asked the narration to
    cite its sources, so the announcement-register patterns (SC-07's, now in BP-15) bind from /3 on."""
    low = TAG.sub("", text).lower().replace("’", "'")
    for phrase in PRESS_PHRASES:
        if phrase in low:
            return phrase
    for pat in PRESS_PATTERNS if patterns else ():
        m = pat.search(low)
        if m:
            return m.group(0)
    return None


def sentences(text: str) -> list[str]:
    """Sentences of one paragraph, tags kept; a sentence ends at . ? ! (an ellipsis inside does not end it)."""
    parts = re.findall(r".+?(?:(?<!\.)[.?!](?!\.)[\"'”’)]*|$)(?=\s|$)", text.strip())
    return [p.strip() for p in parts if p.strip() and TAG.sub("", p).strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", TAG.sub(" ", text))


def first_word(s: str) -> str:
    w = words(s)
    return w[0].lower().replace("’", "'") if w else ""


_HOOK_TESTS = {
    "question": lambda s: s.endswith("?"),
    "preview": lambda s: bool(PREVIEW.search(s)),
    "claim_with_number": lambda s: bool(NUMERAL.search(s) or NUMBER_WORDS.search(s)),
    "cold_open": lambda s: len(words(s)) <= MAX_COLD_OPEN_WORDS,
}
assert set(HOOK_FORMS) <= set(_HOOK_TESTS), f"BP-03 names a hook form with no test: {set(HOOK_FORMS) - set(_HOOK_TESTS)}"
_HOOK_ORDER = ("question", "preview", "claim_with_number", "cold_open")  # the most specific form first


def hook_form(sentence: str) -> str | None:
    """BP-03: which of the registry's hook forms a (tag-free) first sentence takes, or None."""
    plain = sentence.strip()
    return next((f for f in _HOOK_ORDER if f in HOOK_FORMS and _HOOK_TESTS[f](plain)), None)


def lint(text: str, press: bool = True) -> list[dict]:
    """N-01..N-13 on a narration text; N-14 too unless ``press`` is False (a production script lints its narrator lines
    with ``doc_findings`` instead, so a hero's line is not read as narration)."""
    found: list[dict] = []

    def add(rule: str, where: str, detail: str, severity: str = "REVIEW") -> None:
        found.append({"rule": rule, "where": where, "severity": severity, "detail": detail})

    paras = [p.strip() for p in text.splitlines() if p.strip()]
    if not paras:
        add("N-01", "-", "empty narration", "FAIL")
        return found
    all_words = words(text)
    # N-01 the first spoken sentence is the hook, in one of the four forms of BP-03; never a greeting or branding
    first = TAG.sub("", sentences(paras[0])[0]).strip()
    if GREETINGS.search(first):
        add("N-01", "p1", "the first sentence greets, brands or announces the video instead of hooking (BP-03): "
                          "branding, if any, comes after the hook", sev("BP-03"))
    else:
        form = hook_form(first)
        if form is None:
            add("N-01", "p1", f"the first sentence is none of the hook forms of BP-03 ({', '.join(HOOK_FORMS)}; a cold open "
                              f"is at most {MAX_COLD_OPEN_WORDS} words)")
        elif form == "question" and first_word(first) in WH:
            add("N-01", "p1", "the hook is a wh-question, which falls in pitch; prefer a yes/no question "
                              "(\"Could...\", \"Would...\") or end it on the stressed word")
    questions = 0
    interjections = 0
    lengths: list[int] = []
    passive = 0
    contract_window: list[str] = []  # the sentences that start inside the first CONTRACT_WORDS words (BP-04)
    seen_words = 0
    for i, p in enumerate(paras, 1):
        where = f"p{i}"
        sents = sentences(p)
        # N-03 slowing ellipses (BP-16; BP-10: emphasis comes from the text, never a held pause)
        n_ell = len(re.findall(r"\.\.\.|…", p))
        if n_ell > ELLIPSES_FAIL_OVER:
            add("N-03", where, f"{n_ell} ellipses; at most {ELLIPSES_PER_BEAT} per beat (each one slows the read; BP-16)",
                sev("BP-16"))
        elif n_ell > ELLIPSES_PER_BEAT:
            add("N-03", where, f"{n_ell} ellipses; at most {ELLIPSES_PER_BEAT} per beat (BP-16)")
        for j, s in enumerate(sents, 1):
            at = f"{where}.s{j}"
            plain = TAG.sub("", s).strip()
            if seen_words < CONTRACT_WORDS:
                contract_window.append(plain)
            # N-04 stress marks
            caps = [w for w in words(plain) if len(w) > 1 and w.isupper() and w not in ACRONYMS]
            if len(caps) > 1 and not (len(caps) == 2 and " ".join(caps) in plain):
                add("N-04", at, f"{len(caps)} capitalised words ({', '.join(caps)}); one stressed word per sentence",
                    "FAIL")
            # N-05 length (BP-06)
            n = len(words(plain))
            seen_words += n
            lengths.append(n)
            if n > HARD_MAX_SENTENCE_WORDS:
                add("N-05", at, f"{n} words; over {HARD_MAX_SENTENCE_WORDS} (BP-06): split it", sev("BP-06"))
            elif n > MAX_SENTENCE_WORDS:
                add("N-05", at, f"{n} words; split it (spoken sentences stay at most {MAX_SENTENCE_WORDS} words, BP-06)")
            if plain.endswith("?"):
                questions += 1
                # N-10 a question broken by an ellipsis loses its contour
                if re.search(r"\.\.\.|…", plain[:-1]):
                    add("N-10", at, "an ellipsis inside a question breaks its intonation")
                if first_word(plain) in WH and len(words(plain)) > WH_QUESTION_MAX_WORDS:
                    add("N-10", at, f"a wh-question over {WH_QUESTION_MAX_WORDS} words falls before it lands; shorten it or "
                                    "make it yes/no (BP-18)")
            # N-07/N-08 interjections open a sentence (followed by a mark) or stand alone; sounds never sit mid-sentence
            m = re.match(r"^([A-Za-z'’-]+)\s*([,.!?…]|\.\.\.|$)", plain)
            if m and m.group(1).lower() in INTERJECTIONS:
                interjections += 1
            for w in [w.lower() for w in words(plain)][1:]:
                if w in ("hmm", "mm", "mmm", "ah", "uh-oh", "huh", "eh"):
                    add("N-08", at, f"'{w}' in the middle of a sentence; give it its own beat")
            # N-12 spoken register (BP-07): no -'ve contractions, active voice
            for w in words(plain):
                if w.lower().replace("’", "'") in BANNED_CONTRACTIONS:
                    add("N-12", at, f"'{w}' is misheard as 'of'; say the words or use another contraction (BP-07)")
            if PASSIVE.search(plain):
                passive += 1
            # N-13 numbers for the ear (BP-08)
            n_num = len(NUMERAL.findall(plain))
            if n_num > NUMERALS_PER_SENTENCE:
                add("N-13", at, f"{n_num} numerals in one sentence; at most {NUMERALS_PER_SENTENCE} (BP-08): one number per "
                                "sentence, rounded unless the exact figure is the point")
            # N-14 press-release lines (BP-15)
            hit = press_release(plain) if press else None
            if hit:
                add("N-14", at, f"press-release line: {hit!r} (BP-15); the fact lives in the claim map, the line in the story",
                    sev("BP-15"))
        # N-09 tags are delivery, not stage directions
        for tag in TAG.findall(p):
            t = tag.strip().lower()
            if STAGE.search(t):
                add("N-09", where, f"[{tag}] is a stage direction; v4 does not perform it", "FAIL")
            elif t not in DELIVERY_TAGS:
                add("N-09", where, f"[{tag}] is not in the known delivery tags; check it on a test read")
        # N-02 every beat but the last ends on an open loop; the last one teases the next episode
        last = TAG.sub("", sents[-1]).strip() if sents else ""
        low = last.lower()
        if not (last.endswith("?") or low.startswith(LOOP_OPENERS) or " but " in low or "tomorrow" in low):
            add("N-02", where, f"the beat ends closed (\"{last[:60]}\"); end on the next question or danger")
    # N-05 the median sentence length (BP-06)
    if lengths and statistics.median(lengths) > MEDIAN_SENTENCE_WORDS:
        add("N-05", "-", f"median sentence length {statistics.median(lengths):g} words; at most {MEDIAN_SENTENCE_WORDS} for "
                         "the ear (BP-06): more fragments, one idea per sentence")
    # N-11 the 30-second contract (BP-04): a question or a turn inside the first CONTRACT_WORDS words
    window = " ".join(contract_window)
    if "?" not in window and not TURN.search(window):
        add("N-11", "p1", f"no question or turn (but, until, except, unless, and yet) in the first {CONTRACT_WORDS} words: the "
                          "30-second contract opens no gap (BP-04)")
    # N-12 continued (BP-07): passive share, and "you" to one listener at least once per YOU_PER_WORDS words
    if lengths and passive / len(lengths) > PASSIVE_SHARE_MAX:
        add("N-12", "-", f"{passive} of {len(lengths)} sentences read as passive ({passive / len(lengths):.0%} > "
                         f"{PASSIVE_SHARE_MAX:.0%}); active voice, subject first (BP-07)")
    marks = [k for k, w in enumerate(all_words) if YOU.fullmatch(w.replace("’", "'"))]
    edges = [0] + [k + 1 for k in marks] + [len(all_words)]
    gaps = [b - a for a, b in zip(edges, edges[1:])]
    if gaps and max(gaps) > YOU_PER_WORDS:
        add("N-12", "-", f"{max(gaps)} words in a row without 'you' or 'your'; speak to one listener at least once per "
                         f"{YOU_PER_WORDS} words (BP-07)")
    # N-06 questions keep the viewer asking
    if all_words and questions * WORDS_PER_QUESTION < len(all_words):
        add("N-06", "-", f"{questions} questions in {len(all_words)} words; at least one per {WORDS_PER_QUESTION} (BP-17)")
    # N-07 conversational colour, in small doses
    if interjections == 0:
        add("N-07", "-", "no conversational interjection (hmm, oh, well, right...); the read will sound recited")
    elif interjections > len(all_words) / WORDS_PER_INTERJECTION + 1.5:  # about one per 60 words, a little slack
        add("N-07", "-", f"{interjections} interjections in {len(all_words)} words; at most one per "
                         f"{WORDS_PER_INTERJECTION} (BP-17)")
    return found


def doc_findings(doc: dict, press: bool = True) -> list[dict]:
    """What only the production script knows: N-14 on the narrator's lines (a line with a ``speaker`` is a hero's, and a
    hero may name a date inside a scene, SC-07) and N-15, a narration line's held ``pause_after`` over BP-10's hold. The
    dialogue scene's scripted silence (skill dialogue-scenes) is a scene device, not a narration hold, so speaker lines are
    not held to it. N-14 here uses BP-15's phrases only: it runs on /1 and /2 (D-58 keeps their contract), while a /3
    script's narrator lines get the whole lexicon from SC-07 (``validate`` passes ``press=False`` there)."""
    found: list[dict] = []
    for seg in doc.get("segments", []):
        for k, ln in enumerate(seg.get("lines", []), 1):
            if ln.get("speaker"):
                continue
            where = f"{seg['id']} line {k}"
            hit = press_release(ln["text"], patterns=False) if press else None
            if hit:
                found.append({"rule": "N-14", "where": where, "severity": sev("BP-15"),
                              "detail": f"press-release line: {hit!r} (BP-15); the fact lives in the claim map, the line in the story"})
            hold = float(ln.get("pause_after", 0) or 0)
            if hold > MAX_HOLD_S:
                found.append({"rule": "N-15", "where": where, "severity": sev("BP-10"),
                              "detail": f"a {hold:g} s hold after a narration line; emphasis comes from the text, never a hold "
                                        f"over {MAX_HOLD_S:g} s, and no pause before a punch line (BP-10)"})
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("path")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    found = lint(Path(a.path).read_text(encoding="utf-8"))
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
