
"""Scene and dialogue rules SC-01..SC-10 (docs/STORY_ENGINE.md, the 2026-10-19 rewrite) on a production_script/3,
wired as PV-48. stdlib only, free, run by ``production validate`` before any paid step.

The Syndicate Wars review (the creator, 2026-10-19): "no dialogue - characters speak out of context, never meet, no
scene is set"; the audit traced it to the schema having no scene object and the DW rules having no code. These rules
make a scene a contract: a place with people in it, opposing wants, a value that turns (open_charge != close_charge,
McKee's nonevent test), lines addressed to someone present (a hero never talks to the narrator), a real back-and-forth,
subtext never spoken, and a narration register that tells the story instead of citing sources ("Rockstar's page
says..." x7 was required by the old rules; now one honesty beat carries the disclosure). Evidence per rule:
docs/research/STORYTELLING_EDITING_2026-10-19.md. The numbers and the severities of SC-05, SC-08 and SC-09 live in the
sourced rules registry (BP-70..BP-73, docs/SOURCED_RULES.md); SC-07 reads BP-15's one press-release lexicon through
``narration_lint.press_release`` (N-14 uses the same one). SC-11 (full immersion, BP-88) and SC-12 (show, don't tell, BP-87)
are the creator's strict storytelling rules 1 and 2 (2026-10-20, D-61); their lexicons live in the registry.

    python -m explainer_engine.scripting.scene_lint production_script.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.scripting import narration_lint as NL
from explainer_engine.standards import sourced_rules as SR

SCENE_SCHEMA = "production_script/3"
ADDRESS_EXTRA = {"self", "room"}
MAX_TURN_WORDS = SR.T("BP-72", "turn_words_max")  # SC-09 hard cap; a longer turn is split or given to the narrator
SPEECH_WORDS = SR.T("BP-72", "speech_words")  # SC-09: a turn this long is the scene's speech
MAX_SPEECHES = SR.T("BP-72", "speeches_per_scene_max")  # SC-09: one speech per scene, at its peak
REVIEW_TURN_WORDS = SR.T("BP-73", "turn_words_review")  # SC-09: the default spoken turn is 5-15 words
MAX_QA_CHAIN = SR.T("BP-73", "qa_chain_max")  # SC-09/DW-12: more consecutive ?-turns read as an interview
MIN_EXCHANGE = SR.T("BP-70", "min_exchange_lines")  # SC-05: at least one run of this many character lines
MIN_EXCHANGE_SHORT = SR.T("BP-70", "min_exchange_lines_short")  # episode.short_form (a pilot of about 3 minutes): REVIEW only
MIN_EXCHANGE_SPEAKERS = SR.T("BP-70", "min_exchange_speakers")  # SC-05: ... from at least this many speakers
MAX_DISCLAIMER_SEGMENTS = SR.T("BP-71", "disclaimer_segments_max")  # SC-08: no spoken honesty beat since BP-88 (0)
GREETING = re.compile(r"^\s*(hello|hi there|hi[,.! ]|hey there|hey[,.! ]|good (morning|evening|afternoon)|welcome)\b", re.I)
WRAP_UP = re.compile(r"^\s*(so that's|anyway|in conclusion|to sum up|well, that settles)\b", re.I)
DISCLAIMER = re.compile(r"\b((this|that|it|all of this|the rest) (is|was|part is|part was) (invented|made up)|we invented"
                        r"|made (it |this |that )?up|we['’]re guessing|we can only guess|our (own )?assumption"
                        r"|none of this happened|our invention)\b", re.I)


def _lexicon(phrases: list[str]) -> re.Pattern:
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(p).replace("'", "['’]") for p in phrases) + r")(?![a-z])", re.I)


IMMERSION = _lexicon(SR.T("BP-88", "frames"))  # SC-11: a line that steps outside the story, from anyone
HEDGE = _lexicon(SR.T("BP-88", "hedges"))  # SC-11: the narrator doubting the story itself (a hero may doubt in a scene)
SHOW_TRAITS = SR.T("BP-87", "traits")  # SC-12: the narrator states a trait instead of showing it
TELL = _lexicon(SR.T("BP-87", "phrases"))
RATING = re.compile("|".join(SR.T("BP-87", "ratings")), re.I)
STAT_PICTURES = tuple(SR.T("BP-87", "picture_prefixes"))  # select_screen.py's stat cards (Syndicate Wars, /2)
_TRAIT = r"(" + "|".join(re.escape(t) for t in SHOW_TRAITS) + r")"
_LINK = (r"\s+(is|was|are|were|has always been|had always been|is known as|was known as|is famously)\s+"
         r"((a|an|so|very|extremely|famously|notoriously|incredibly|deeply|naturally|truly|the most|a true|a real)\s+)*")


def _trait_pattern(doc: dict) -> re.Pattern:
    """'he is charismatic', 'Musk was a risk-taker': a person (pronoun, cast id or name) linked to a trait word."""
    who = {"he", "she", "they", "the man", "the woman", "this man", "this woman"}
    for cid, c in doc.get("cast", {}).items():
        who.add(cid.replace("_", " "))
        for name in (c or {}).get("names", []):
            who.add(name)
            who.update(part for part in name.split() if len(part) > 2)
    subj = "|".join(sorted((re.escape(w) for w in who), key=len, reverse=True))
    return re.compile(rf"\b(({subj}){_LINK}|(he|she|they)['’](s|re)\s+(a\s+|an\s+|so\s+|very\s+)*){_TRAIT}(?![a-z])", re.I)


def _screen_texts(doc: dict):
    """(where, text) of every word the viewer reads: bubbles, accents, beats, period cards, graphics titles."""
    for seg in doc.get("segments", []):
        for li, ln in enumerate(seg.get("lines", [])):
            for b in ln.get("visual_beats") or []:
                for key in ("text", "label"):
                    if b.get(key):
                        yield f"{seg['id']} line {li + 1} beat", b[key]
        for si, sh in enumerate(seg.get("shots", [])):
            for key in ("bubbles", "accents"):
                for item in sh.get(key) or []:
                    if item.get("text"):
                        yield f"{seg['id']} shot {si + 1} {key}", item["text"]
    for pi, per in enumerate(doc.get("periods", [])):
        if (per.get("card") or {}).get("title"):
            yield f"period {pi + 1} card", per["card"]["title"]
    for gi, g in enumerate(doc.get("graphics", [])):
        if g.get("title"):
            yield f"graphic {gi + 1}", g["title"]


def immersion_and_showing(doc: dict) -> list[dict]:
    """SC-11 (BP-88) and SC-12 (BP-87) on the whole script: lines, Shorts and on-screen words."""
    out: list[dict] = []
    traits = _trait_pattern(doc)
    spoken = [(f"{seg['id']} line {li + 1}", ln) for seg in doc.get("segments", []) for li, ln in enumerate(seg["lines"])]
    spoken += [(f"short {sh.get('id', si + 1)} line {li + 1}", ln) for si, sh in enumerate(doc.get("shorts", []))
               for li, ln in enumerate(sh.get("lines", []))]
    for where, ln in spoken:
        text, narr = ln.get("text", ""), not ln.get("speaker")
        m = IMMERSION.search(text) or (HEDGE.search(text) if narr else None)
        if m:
            _f(out, "SC-11", where, f"{m.group(0)!r} steps outside the story (BP-88): no meta disclaimer, no hedge on the "
               "story itself; the title and the description carry the what-if, the story plays as if it happens now",
               sev("BP-88"))
        if narr:
            m = traits.search(text) or TELL.search(text) or RATING.search(text)
            if m:
                _f(out, "SC-12", where, f"the narrator tells instead of showing ({m.group(0)!r}, BP-87): show the trait "
                   "through what the hero does, says, gets wrong or decides; never a trait list, a rating or a biography",
                   sev("BP-87"))
    for where, text in _screen_texts(doc):
        if IMMERSION.search(text):
            _f(out, "SC-11", where, f"on-screen text {text!r} steps outside the story (BP-88)", sev("BP-88"))
        if RATING.search(text) or TELL.search(text):
            _f(out, "SC-12", where, f"on-screen text {text!r} rates or describes a hero (BP-87): no stat cards or star "
               "ratings; show it in a scene", sev("BP-87"))
    pics = {sh.get("picture") if isinstance(sh.get("picture"), str) else (sh.get("picture") or {}).get("id")
            for seg in doc.get("segments", []) for sh in seg.get("shots", [])}
    for pid in sorted(p for p in pics if p and p.startswith(STAT_PICTURES)):
        _f(out, "SC-12", pid, "a stat card (select_screen.py) rates the heroes on screen (BP-87): not on a /3 episode",
           sev("BP-87"))
    return out


def _f(out, rule, where, detail, sev):
    out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})


sev = NL.sev  # a registered rule's severity is the registry's (BP-15, BP-70..BP-73)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def binding(doc: dict) -> bool:
    return doc.get("schema") == SCENE_SCHEMA


def lint(doc: dict) -> list[dict]:
    if doc.get('schema_version') == '4.0.0':
        return lint_v4(doc)
    """SC findings on a /3 script; an earlier schema gets none (its contract is unchanged)."""
    out: list[dict] = []
    if not binding(doc):
        return out
    cast = doc.get("cast", {})
    disclaimer_segs: list[str] = []
    for seg in doc["segments"]:
        sid = seg["id"]
        lines = seg["lines"]
        dialogue = [ln for ln in lines if ln.get("speaker")]
        scene = seg.get("scene")
        for li, ln in enumerate(lines):
            hit = None if ln.get("speaker") else NL.press_release(ln["text"])
            if hit:
                _f(out, "SC-07", f"{sid} line {li + 1}", f"press-release register in narration ({hit!r} in {ln['text'][:60]!r}, "
                   "BP-15): tell the story; a date or spec enters only inside a scene as stakes or ammunition", sev("BP-15"))
        if any(DISCLAIMER.search(ln["text"]) for ln in lines if not ln.get("speaker")):
            disclaimer_segs.append(sid)
        if not dialogue:
            continue
        if not scene:
            _f(out, "SC-01", sid, "a segment with dialogue has no scene: write scene {place, present, pov, want, "
               "obstacle_want, value, open_charge, close_charge, exit} before the lines", "FAIL")
            continue
        for who in scene.get("present", []):
            if who not in cast:
                _f(out, "SC-01", sid, f"scene.present names {who!r}, not in the cast", "FAIL")
        present = set(scene.get("present", []))
        if scene.get("pov") not in present:
            _f(out, "SC-01", sid, f"scene.pov {scene.get('pov')!r} is not present in the scene", "FAIL")
        if scene.get("open_charge") == scene.get("close_charge"):
            _f(out, "SC-02", sid, f"the value {scene.get('value', '?')!r} opens and closes {scene.get('open_charge')!r}: "
               "a scene whose charge does not turn is a nonevent - cut it or give it a turn", "FAIL")
        if len(_words(scene.get("turn", ""))) < 3:
            _f(out, "SC-02", sid, "scene.turn names the beat where the scene turns, in one sentence", "FAIL")
        want, ow = scene.get("want", "").strip().lower(), scene.get("obstacle_want", "").strip().lower()
        if want and want == ow:
            _f(out, "SC-03", sid, "want and obstacle_want are the same: no conflict, no scene; someone present must "
               "want something that collides", "FAIL")
        if not scene.get("surface_topic") or not scene.get("real_subject"):
            _f(out, "SC-10", sid, "no surface_topic / real_subject: say what they talk about and what the scene is "
               "really about (the subtext)", "REVIEW")
        real = (scene.get("real_subject") or "").strip().lower()
        speakers_seen: set[str] = set()
        speeches = 0
        qa_chain = 0
        run, best_run, run_speakers, best_speakers = 0, 0, set(), set()
        for li, ln in enumerate(lines):
            where = f"{sid} line {li + 1}"
            spk = ln.get("speaker")
            if not spk:
                run, run_speakers = 0, set()
                continue
            run += 1
            run_speakers = run_speakers | {spk}
            if run > best_run or (run == best_run and len(run_speakers) > len(best_speakers)):
                best_run, best_speakers = run, set(run_speakers)
            speakers_seen.add(spk)
            if spk not in present:
                _f(out, "SC-04", where, f"{spk} speaks but is not in scene.present: a hero talks only inside a scene "
                   "they are in", "FAIL")
            to = ln.get("to")
            if not to:
                _f(out, "SC-04", where, f"{spk}'s line has no 'to': every line is said to someone present (or 'self' / "
                   "'room'); a hero never answers the narrator", "FAIL")
            elif to not in present | ADDRESS_EXTRA:
                _f(out, "SC-04", where, f"'to': {to!r} is not present in the scene (and the narrator is never an "
                   "addressee: the fourth wall stands)", "FAIL")
            elif to == spk:
                _f(out, "SC-04", where, f"{spk} addresses themselves by id; use 'self'", "REVIEW")
            n = len(_words(ln["text"]))
            if n > MAX_TURN_WORDS:
                _f(out, "SC-09", where, f"a {n}-word turn (cap {MAX_TURN_WORDS}, BP-72): split it, cut it, or give the "
                   "summary to the narrator", sev("BP-72"))
            elif n >= SPEECH_WORDS:
                speeches += 1
                if speeches > MAX_SPEECHES:
                    _f(out, "SC-09", where, f"speech {speeches} ({n} words) in one scene: at most {MAX_SPEECHES} long turn per "
                       f"scene, at its peak; everything else is 5-{REVIEW_TURN_WORDS} words (BP-72)", sev("BP-72"))
            elif n > REVIEW_TURN_WORDS:
                _f(out, "SC-09", where, f"{n} words in one turn (default 5-{REVIEW_TURN_WORDS}, BP-73): people speak in jabs; "
                   "save length for the scene's one speech", sev("BP-73"))
            qa_chain = qa_chain + 1 if ln["text"].rstrip().endswith("?") else 0
            if qa_chain == MAX_QA_CHAIN + 1:
                _f(out, "SC-09", where, f"{qa_chain} question-turns in a row read as an interview: answer sideways - "
                   "deflect, change the subject, counterattack (DW-12, BP-73)", sev("BP-73"))
            if real and len(real) >= 4 and real in ln["text"].lower():
                _f(out, "SC-10", where, f"the line states the real subject ({scene['real_subject']!r}) out loud: "
                   "subtext is never spoken; let the surface carry it", "FAIL")
            if ln.get("intent") == "reveal":
                nxt = lines[li + 1] if li + 1 < len(lines) else None
                reacted = (nxt is not None and nxt.get("speaker") and nxt["speaker"] != spk) or any(
                    b["kind"] == "expression" and b.get("who") not in (None, spk)
                    for b in (ln.get("visual_beats") or []) + ((nxt or {}).get("visual_beats") or []))
                if not reacted:
                    _f(out, "SC-05", where, "a reveal lands and nobody reacts: the next beat is another character's "
                       "line or a listener's expression (DW-05, Kuleshov: show the face the line affects)", "REVIEW")
        # D-63 / BP-70: the narrator may report the exchange instead (the creator, 2026-10-20 21:14/21:17)
        from explainer_engine.scripting.story_lint import reported_turns
        told = [h for ln in lines if not ln.get("speaker") for h in reported_turns(ln["text"], cast, sorted(present))]
        short = bool(doc.get("episode", {}).get("short_form"))
        need = MIN_EXCHANGE_SHORT if short else MIN_EXCHANGE
        reported = len(told) >= need and len(set(told)) >= MIN_EXCHANGE_SPEAKERS
        if len(present) >= 2 and not reported and (best_run < need or len(best_speakers) < MIN_EXCHANGE_SPEAKERS):
            _f(out, "SC-05", sid, f"no real exchange: the longest unbroken run is {best_run} character line(s) "
               f"({len(best_speakers)} speaker(s)); a scene plays at least {need} character lines in a row, "
               f"{MIN_EXCHANGE_SPEAKERS} voices, no narrator inside, or the narrator reports at least {need} turns "
               f"of {MIN_EXCHANGE_SPEAKERS} named speakers (found {len(told)}; BP-70)", "REVIEW" if short else sev("BP-70"))
        silent = present - speakers_seen - {b.get("who") for ln in lines for b in (ln.get("visual_beats") or [])
                                            if b["kind"] == "expression"}
        if silent:
            _f(out, "SC-05", sid, f"{', '.join(sorted(silent))} present but never speaks or reacts: everyone in a "
               "scene is in the scene", "REVIEW")
        first = dialogue[0]["text"]
        if GREETING.match(first):
            _f(out, "SC-06", sid, f"the scene opens on a greeting ({first[:30]!r}): enter late, in the middle of the "
               "action", "REVIEW")
        if WRAP_UP.match(lines[-1]["text"]):
            _f(out, "SC-06", sid, f"the scene closes on a wrap-up ({lines[-1]['text'][:30]!r}): leave early, within a "
               "line or two of the turn", "REVIEW")
    if len(disclaimer_segs) > MAX_DISCLAIMER_SEGMENTS:
        _f(out, "SC-08", ",".join(disclaimer_segs[:6]), f"{len(disclaimer_segs)} segments carry invention disclaimers "
           f"(at most {MAX_DISCLAIMER_SEGMENTS}, BP-71): the story is never interrupted to say it is invented; the title "
           "and the description carry it, the claim map labels each segment (ST-09, BP-88)", sev("BP-71"))
    out += immersion_and_showing(doc)
    return out


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    doc = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    found = lint(doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    n_fail = sum(f["severity"] == "FAIL" for f in found)
    print(f"{n_fail} FAIL, {len(found) - n_fail} REVIEW")
    return 1 if n_fail else 0




def lint_v4(doc: dict) -> list[dict]:
    """Validate played dramatic scenes (SC-01..SC-06, SC-10), character dialogue turns, speaker/addressee IDs,
    anti-isolated-interruption rules, and lip-sync flags on a v4.0 production_script."""
    out: list[dict] = []
    wb = doc.get("world_bible") or {}
    chars_list = wb.get("characters", [])
    known_chars = {c.get("character_id") for c in chars_list if c.get("character_id")}

    # Map character_id -> distinctive name tokens (for third-person self-reference detection)
    char_self_tokens: dict[str, set[str]] = {}
    for c in chars_list:
        cid = str(c.get("character_id") or "")
        tokens: set[str] = set()
        parts = [p for p in re.split(r"[^a-zA-Z]+", cid.replace("char_", "")) if len(p) >= 4 and not p.isdigit()]
        tokens.update(p.lower() for p in parts)
        for nm_field in ("name", "display_name"):
            nm_val = str(c.get(nm_field) or "")
            for p in re.split(r"[^a-zA-Z]+", nm_val):
                if len(p) >= 4 and p.lower() not in {"general", "marshal", "duke", "emperor", "lord", "chief", "hunter", "elder"}:
                    tokens.add(p.lower())
        if cid:
            char_self_tokens[cid] = tokens

    audio_lines = doc.get("audio_lines", [])
    segments = doc.get("segments", [])
    shots = doc.get("shots", [])
    seen_char_texts: dict[str, str] = {}

    for line in audio_lines:
        lid = line.get("line_id", "?")
        stype = line.get("speaker_type")
        if stype == "narrator" and line.get("requires_visible_lipsync") is True:
            out.append({
                "rule": "SC-V4-LIPSYNC",
                "severity": "FAIL",
                "where": lid,
                "detail": "Narrator voiceover line cannot set requires_visible_lipsync=True",
            })
        elif stype == "character":
            spk = line.get("speaker_id")
            addr = line.get("addressee_id")
            ltext = str(line.get("text") or "").strip()

            if known_chars and spk not in known_chars:
                out.append({
                    "rule": "SC-V4-SPEAKER",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": f"Character speaker_id {spk!r} is not defined in world_bible.characters",
                })
            if not str(line.get("delivery_direction", "")).strip():
                out.append({
                    "rule": "SC-V4-DELIVERY",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": "Character dialogue line must specify a non-empty delivery_direction",
                })
            if not addr:
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": f"{spk}'s line has no addressee_id: every character line must address a co-present character, 'self', or 'room'",
                })
            elif addr in ("narrator", "narrator_main"):
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": f"{spk} addresses {addr!r}: a character never addresses the narrator (fourth wall stands)",
                })
            elif addr == spk:
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": f"{spk} addresses themselves by character_id; use 'self' for soliloquy",
                })
            elif known_chars and addr not in (known_chars | ADDRESS_EXTRA):
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": lid,
                    "detail": f"addressee_id {addr!r} is not in world_bible.characters or {sorted(ADDRESS_EXTRA)}",
                })

            # Check third-person self-reference (e.g. char_wellington_1815 saying "before Wellington reinforces...")
            for own_tok in char_self_tokens.get(str(spk), set()):
                if re.search(rf"\b{re.escape(own_tok)}\b", ltext, re.I):
                    out.append({
                        "rule": "SC-04",
                        "severity": "FAIL",
                        "where": lid,
                        "detail": f"Speaker {spk} refers to themselves in the third person ({own_tok!r}) inside {ltext[:60]!r}",
                    })
                    break

            norm_txt = " ".join(ltext.lower().split())
            if len(norm_txt) >= 15:
                if norm_txt in seen_char_texts:
                    out.append({
                        "rule": "SC-V4-DUPLICATE-DIALOGUE",
                        "severity": "FAIL",
                        "where": lid,
                        "detail": f"Character line duplicates verbatim text from {seen_char_texts[norm_txt]} ({ltext[:50]!r})",
                    })
                else:
                    seen_char_texts[norm_txt] = lid

    # Segment-level played scene vs. narration-led validation
    for seg in segments:
        sid = seg.get("segment_id", "?")
        seg_mode = seg.get("segment_mode")
        scene = seg.get("scene")
        seg_lines = [l for l in audio_lines if l.get("segment_id") == sid]
        char_lines = [l for l in seg_lines if l.get("speaker_type") == "character"]

        if not char_lines:
            if seg_mode == "played_scene" or isinstance(scene, dict):
                out.append({
                    "rule": "SC-01",
                    "severity": "FAIL",
                    "where": sid,
                    "detail": f"Segment {sid} is marked as a played_scene / defines a scene object but has 0 character lines",
                })
            continue

        # v4.3 (the creator, 2026-11-12, plan P1.3): dialogue lives inside scenes; a hero line in a segment that is not a
        # played scene is a FAIL, never an aside dropped into narration or a visual-action run.
        if seg_mode is not None and seg_mode != "played_scene":
            out.append({
                "rule": "SC-01",
                "severity": "FAIL",
                "where": char_lines[0].get("line_id", sid),
                "detail": (f"Segment {sid} is {seg_mode!r} but carries {len(char_lines)} character line(s): dialogue belongs "
                           "only in a played_scene segment (v4.3, 2026-11-12)"),
            })

        # Measure contiguous character runs in seg_lines
        runs: list[tuple[int, set[str], list[str]]] = []
        cur_len = 0
        cur_spks: set[str] = set()
        cur_lids: list[str] = []
        for l in seg_lines:
            if l.get("speaker_type") == "character":
                cur_len += 1
                if l.get("speaker_id"):
                    cur_spks.add(str(l["speaker_id"]))
                cur_lids.append(str(l.get("line_id", "?")))
            else:
                if cur_len > 0:
                    runs.append((cur_len, set(cur_spks), list(cur_lids)))
                    cur_len, cur_spks, cur_lids = 0, set(), []
        if cur_len > 0:
            runs.append((cur_len, set(cur_spks), list(cur_lids)))

        best_run = max((r[0] for r in runs), default=0)
        best_spks = max((len(r[1]) for r in runs), default=0)
        isolated_runs = [r for r in runs if r[0] < 2 or len(r[1]) < 2]

        if best_run < 2 or best_spks < 2 or isolated_runs:
            bad_where = isolated_runs[0][2][0] if isolated_runs and isolated_runs[0][2] else sid
            out.append({
                "rule": "SC-05",
                "severity": "FAIL",
                "where": bad_where,
                "detail": (
                    f"Isolated character interruption in {sid} (best contiguous run={best_run} line(s), {best_spks} speaker(s)): "
                    "characters must never drop 1-line shouts inside narration. Use pure narration or play a real multi-turn exchange "
                    "(>=2 contiguous character lines from >=2 co-present speakers)."
                ),
            })

        if not isinstance(scene, dict):
            out.append({
                "rule": "SC-01",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Segment {sid} has character dialogue but no scene object {{place, present, pov, want, obstacle_want, value, open_charge, close_charge, turn, exit}}",
            })
            continue

        present_list = scene.get("present") or []
        present = set(present_list)
        if len(present) < 2:
            out.append({
                "rule": "SC-01",
                "severity": "FAIL",
                "where": sid,
                "detail": f"scene.present in {sid} must include at least 2 co-present characters, got {present_list!r}",
            })
        for who in present:
            if known_chars and who not in known_chars:
                out.append({
                    "rule": "SC-01",
                    "severity": "FAIL",
                    "where": sid,
                    "detail": f"scene.present in {sid} names unknown character {who!r}",
                })
        if scene.get("pov") not in present:
            out.append({
                "rule": "SC-01",
                "severity": "FAIL",
                "where": sid,
                "detail": f"scene.pov {scene.get('pov')!r} is not in scene.present {sorted(present)}",
            })
        if scene.get("open_charge") == scene.get("close_charge"):
            out.append({
                "rule": "SC-02",
                "severity": "FAIL",
                "where": sid,
                "detail": f"scene value {scene.get('value', '?')!r} opens and closes at {scene.get('open_charge')!r}: charge must turn (+/-)",
            })
        if len(_words(str(scene.get("turn") or ""))) < 3:
            out.append({
                "rule": "SC-02",
                "severity": "FAIL",
                "where": sid,
                "detail": "scene.turn must state the beat where the scene turns in at least 3 words",
            })
        want = str(scene.get("want") or "").strip().lower()
        ow = str(scene.get("obstacle_want") or "").strip().lower()
        if not want or not ow or want == ow:
            out.append({
                "rule": "SC-03",
                "severity": "FAIL",
                "where": sid,
                "detail": "scene.want and scene.obstacle_want must be non-empty and opposing",
            })
        real_subj = str(scene.get("real_subject") or "").strip().lower()

        for cl in char_lines:
            clid = cl.get("line_id", sid)
            cspk = cl.get("speaker_id")
            caddr = cl.get("addressee_id")
            ctext = str(cl.get("text") or "")
            if cspk not in present:
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": clid,
                    "detail": f"{cspk} speaks in {sid} but is not in scene.present {sorted(present)}",
                })
            if caddr and caddr not in (present | ADDRESS_EXTRA):
                out.append({
                    "rule": "SC-04",
                    "severity": "FAIL",
                    "where": clid,
                    "detail": f"{cspk} addresses {caddr!r} who is not co-present in scene.present {sorted(present)}",
                })
            if real_subj and len(real_subj) >= 4 and real_subj in ctext.lower():
                out.append({
                    "rule": "SC-10",
                    "severity": "FAIL",
                    "where": clid,
                    "detail": f"Character line states scene.real_subject ({real_subj!r}) out loud; subtext must stay unspoken",
                })
        if GREETING.match(str(char_lines[0].get("text") or "")):
            out.append({
                "rule": "SC-06",
                "severity": "FAIL",
                "where": char_lines[0].get("line_id", sid),
                "detail": "Scene opens on a small-talk greeting; enter late in the middle of the conflict",
            })

        # Multi-shot coverage check for played scenes
        char_line_ids = {cl.get("line_id") for cl in char_lines if cl.get("line_id")}
        scene_shots = [sh for sh in shots if sh.get("segment_id") == sid and set(sh.get("audio_line_ids") or []) & char_line_ids]
        if len(char_lines) >= 2 and len([sh for sh in shots if sh.get("segment_id") == sid]) >= 2 and len(scene_shots) < 2:
            out.append({
                "rule": "SC-V4-SCENE-COVERAGE",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Played scene in {sid} has {len(char_lines)} character turns but only {len(scene_shots)} shot covering them; use multi-shot action/reaction coverage",
            })

    return out


check = lint


if __name__ == "__main__":
    raise SystemExit(main())
