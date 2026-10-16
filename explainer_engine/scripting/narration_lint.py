"""Narration lint: the mechanical part of the `narration-script` skill (.claude/skills/narration-script/SKILL.md).

    python -m explainer_engine.scripting.narration_lint examples/stone_age/day1_v3/narration_tts.txt

Reads a TTS narration file (one paragraph = one beat; ElevenLabs v4 audio tags allowed) and reports FAIL / REVIEW
findings, rule ids N-01..N-10 as in the skill. It cannot judge whether a line is funny or intriguing; it catches the
defects the creator heard in the first reads: questions that fall, stress on the wrong word, too many slowing
ellipses, beats that end closed, no conversational colour, stage directions read aloud.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
ACRONYMS = {"TV", "UK", "US", "USA", "DNA", "NASA", "OK", "BC", "BCE", "AD", "CE"}
MAX_SENTENCE_WORDS = 22
WORDS_PER_QUESTION = 150
WORDS_PER_INTERJECTION = 60


def sentences(text: str) -> list[str]:
    """Sentences of one paragraph, tags kept; a sentence ends at . ? ! (an ellipsis inside does not end it)."""
    parts = re.findall(r".+?(?:(?<!\.)[.?!](?!\.)[\"'”’)]*|$)(?=\s|$)", text.strip())
    return [p.strip() for p in parts if p.strip() and TAG.sub("", p).strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", TAG.sub(" ", text))


def first_word(s: str) -> str:
    w = words(s)
    return w[0].lower().replace("’", "'") if w else ""


def lint(text: str) -> list[dict]:
    found: list[dict] = []

    def add(rule: str, where: str, detail: str, severity: str = "REVIEW") -> None:
        found.append({"rule": rule, "where": where, "severity": severity, "detail": detail})

    paras = [p.strip() for p in text.splitlines() if p.strip()]
    if not paras:
        add("N-01", "-", "empty narration", "FAIL")
        return found
    all_words = words(text)
    # N-01 the hook is a question by 5 s (UR-01), ideally one that rises
    first = sentences(paras[0])[0]
    if not TAG.sub("", first).strip().endswith("?"):
        add("N-01", "p1", "the first sentence is not a question (UR-01)", "FAIL")
    elif first_word(first) in WH:
        add("N-01", "p1", "the hook is a wh-question, which falls in pitch; prefer a yes/no question "
                          "(\"Could...\", \"Would...\") or end it on the stressed word")
    questions = 0
    interjections = 0
    for i, p in enumerate(paras, 1):
        where = f"p{i}"
        sents = sentences(p)
        # N-03 slowing ellipses
        n_ell = len(re.findall(r"\.\.\.|…", p))
        if n_ell > 2:
            add("N-03", where, f"{n_ell} ellipses; at most 1 per beat (each one slows the read)", "FAIL")
        elif n_ell == 2:
            add("N-03", where, "2 ellipses; at most 1 per beat")
        for j, s in enumerate(sents, 1):
            at = f"{where}.s{j}"
            plain = TAG.sub("", s).strip()
            # N-04 stress marks
            caps = [w for w in words(plain) if len(w) > 1 and w.isupper() and w not in ACRONYMS]
            if len(caps) > 1 and not (len(caps) == 2 and " ".join(caps) in plain):
                add("N-04", at, f"{len(caps)} capitalised words ({', '.join(caps)}); one stressed word per sentence",
                    "FAIL")
            # N-05 length
            n = len(words(plain))
            if n > MAX_SENTENCE_WORDS:
                add("N-05", at, f"{n} words; split it (spoken sentences stay under {MAX_SENTENCE_WORDS})")
            if plain.endswith("?"):
                questions += 1
                # N-10 a question broken by an ellipsis loses its contour
                if re.search(r"\.\.\.|…", plain[:-1]):
                    add("N-10", at, "an ellipsis inside a question breaks its intonation")
                if first_word(plain) in WH and len(words(plain)) > 12:
                    add("N-10", at, "a long wh-question falls before it lands; shorten it or make it yes/no")
            # N-07/N-08 interjections open a sentence (followed by a mark) or stand alone; sounds never sit mid-sentence
            m = re.match(r"^([A-Za-z'’-]+)\s*([,.!?…]|\.\.\.|$)", plain)
            if m and m.group(1).lower() in INTERJECTIONS:
                interjections += 1
            for w in [w.lower() for w in words(plain)][1:]:
                if w in ("hmm", "mm", "mmm", "ah", "uh-oh", "huh", "eh"):
                    add("N-08", at, f"'{w}' in the middle of a sentence; give it its own beat")
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
    # N-06 questions keep the viewer asking
    if all_words and questions * WORDS_PER_QUESTION < len(all_words):
        add("N-06", "-", f"{questions} questions in {len(all_words)} words; at least one per {WORDS_PER_QUESTION}")
    # N-07 conversational colour, in small doses
    if interjections == 0:
        add("N-07", "-", "no conversational interjection (hmm, oh, well, right...); the read will sound recited")
    elif interjections > len(all_words) / WORDS_PER_INTERJECTION + 1.5:  # about one per 60 words, a little slack
        add("N-07", "-", f"{interjections} interjections in {len(all_words)} words; at most one per "
                         f"{WORDS_PER_INTERJECTION}")
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
