"""Names the reader says slightly differently (Blueprint P3): a small phonetic key so the word timings of a read can mark "Nay" as
the heard form of the written "Ney". stdlib only.

It is a reduced in-repo key, not Double Metaphone: no phonetic library is installed and a faithful port is several hundred lines
for one narrow need. The key is used ONLY inside an aligned replace span of equal length (``audio/scribe_words.align(entities=)``),
so a short key such as ``N`` can never match a word the alignment did not already put opposite the name.

    >>> key("Ney"), key("Nay"), key("Subutai"), key("Subotai")
    ('N', 'N', 'SBT', 'SBT')
"""

from __future__ import annotations

import re

VOWELS = "aeiou"
REWRITES = (("ph", "f"), ("ck", "k"), ("dg", "j"), ("q", "k"), ("x", "ks"), ("z", "s"))


def key(word: str) -> str:
    """The reduced phonetic key of one word: letters only; ph/ck/dg/q/x/z and soft c rewritten; a leading kn, gn or wr is n, n or r;
    gh dropped except at the start; the first letter kept, later vowels and any w, y or h after a vowel dropped, repeats collapsed."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    for pat, rep in (("kn", "n"), ("gn", "n"), ("wr", "r")):
        if w.startswith(pat):
            w = rep + w[len(pat):]
    for pat, rep in REWRITES:
        w = w.replace(pat, rep)
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    w = w[0] + w[1:].replace("gh", "")
    out, prev = [w[0]], w[0]
    for ch in w[1:]:
        after_vowel = prev in VOWELS
        prev = ch
        if ch in VOWELS or (ch in "wyh" and after_vowel):
            continue
        if ch != out[-1]:
            out.append(ch)
    return "".join(out).upper()


def _edit(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (ca != cb)))
        row = new
    return row[-1]


def same(a: str, b: str) -> bool:
    """Two spellings of one sound: equal keys, or keys one edit apart when both have at least three letters."""
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return False
    return ka == kb or (min(len(ka), len(kb)) >= 3 and _edit(ka, kb) <= 1)


def heard(text_words: list[str], heard_words: list[str], *, names: set[str] | frozenset = frozenset()) -> list[bool]:
    """For each written word opposite a heard word: the same word, or (when it is one of ``names``) the same sound."""
    low = {n.lower() for n in names}
    return [t.lower() == h.lower() or (t.lower() in low and same(t, h)) for t, h in zip(text_words, heard_words)]
