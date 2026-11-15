"""Free rule check of a paid jobs file, run on the local side of every Modal launcher BEFORE ``.remote()`` (the creator, 2026-11-07
22:23 UTC: the Gemini review found that the c3 LTX prompt broke KP-04, KP-22 and KP-55 and the minute-1 cut broke DL-04, and no code
had run those checks before money was spent). A FAIL stops the launcher; nothing is started.

- LTX jobs (``ltx_jobs.py`` shape: ``{"names": [...], "jobs": [{"id", "prompt", "frames", "fps", "held_props"?, "camera_end"?,
  "prop_change"?, "exit"?}]}``) -> ``scripting/shot_prompt_lint`` as route J2 video shots (KP-04, KP-11, KP-22, KP-55, KP-59..KP-62),
  plus VL-17 start-picture inventory checks (Audit #2 & C3: every physical object/prop noun in the prompt must exist in ``seen`` /
  ``start_picture_objects`` or in declared entering/held props ``prop_change`` / ``held_props``, and positive prompts must not contain
  negative instructions like ``does not`` / ``never``).
  A jobs file without ``names`` (the story names of the heroes) fails: KP-22 cannot be checked.
- Qwen jobs (``qwen_jobs.py`` shape) -> ``production/scene_reuse.check_all`` (RF-01, RF-04, RF-05, HI-01, HI-04, HI-08, ...).

    python -m explainer_engine.production.paid_preflight ltx|qwen <jobs.json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.production import scene_reuse
from explainer_engine.scripting import shot_prompt_lint

_CHECKED_PROPS = (
    "flag", "banner", "rifle", "gun", "pistol", "bayonet", "spade", "shovel", "mug", "cup", "tin",
    "cigarette", "cigar", "lantern", "torch", "candle", "brazier", "photograph", "photo", "letter",
    "book", "bible", "football", "ball", "ladder", "box", "crate", "table", "chair", "harmonica",
    "watch", "compass", "bell", "whistle", "sword", "shield", "spear", "bow", "kettle", "pot",
    "pan", "helmet", "wire", "sandbag", "tree", "trees", "fir", "pine", "willow", "branch",
    "bottle", "jug", "flask", "canteens", "canteen", "pack", "rucksack", "bag", "sack", "blanket",
    "newspaper", "paper", "map", "card", "coin", "button", "medal", "cross", "ring", "pipe",
    "match", "matches", "lighter", "knife", "dagger", "axe", "hammer", "pickaxe", "plank",
    "duckboard", "parapet", "stake", "post", "fence", "gate", "door", "window", "bench", "stool",
    "barrel", "drum", "bucket", "pail", "rope", "chain", "stretcher", "wagon", "cart", "horse",
    "dog", "bird", "bicycle", "motorcycle", "car", "truck", "cannon", "mortar", "shell", "grenade",
    "accordion", "violin", "flute", "drum", "bugle", "trumpet", "bread", "chocolate", "ration",
    "apple", "sausage", "cheese", "wine", "beer", "tea", "coffee", "soup", "plate", "bowl", "spoon",
    "fork", "pencil", "pen", "diary", "notebook", "envelope", "parcel", "package", "gift", "ribbon",
    "scarf", "gloves", "glove", "mittens", "boots", "boot", "cap", "hat", "coat", "greatcoat",
    "tunic", "jerkin", "uniform", "cloak", "shawl", "towel", "cloth", "rag", "bandage",
)
# General non-object words so syntactic noun-phrase extraction catches any physical noun not in seen:
_NON_OBJECT_WORDS = frozenset({
    # Articles, determiners, prepositions, conjunctions, pronouns, auxiliaries
    "a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their",
    "one", "two", "three", "four", "five", "six", "both", "all", "some", "any", "no", "none", "each", "every",
    "other", "another", "same", "such", "own", "only", "just", "even", "still", "also", "very", "too", "so",
    "more", "most", "less", "least", "much", "many", "few", "several", "half", "whole", "entire", "full", "empty",
    "in", "on", "at", "by", "for", "with", "without", "from", "to", "into", "onto", "out", "of", "off", "over",
    "above", "under", "below", "beneath", "across", "through", "along", "around", "about", "against", "among",
    "between", "behind", "beside", "near", "next", "toward", "towards", "up", "down", "inside", "outside",
    "before", "after", "during", "until", "till", "since", "while", "when", "where", "as", "than", "like",
    "and", "or", "but", "nor", "yet", "if", "though", "although", "because", "he", "she", "it", "they", "we",
    "him", "them", "us", "himself", "herself", "themselves", "who", "whom", "whose", "which", "what", "there", "here",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must", "not", "never",
    # Motion / action verbs & participles
    "raises", "raise", "raising", "raised", "lifts", "lift", "lifting", "lifted", "holds", "hold", "holding", "held",
    "carries", "carry", "carrying", "carried", "takes", "take", "taking", "took", "taken", "gives", "give", "giving",
    "gave", "given", "hands", "handing", "handed", "offers", "offer", "offering", "offered", "extends", "extend",
    "extending", "extended", "reaches", "reach", "reaching", "reached", "puts", "put", "putting", "sets", "set",
    "setting", "places", "place", "placing", "placed", "lays", "lay", "laying", "laid", "drops", "drop", "dropping",
    "dropped", "throws", "throw", "throwing", "threw", "pulls", "pull", "pulling", "pulled", "pushes", "push",
    "pushing", "pushed", "opens", "open", "opening", "opened", "closes", "close", "closing", "closed", "turns",
    "turn", "turning", "turned", "steps", "step", "stepping", "stepped", "walks", "walk", "walking", "walked",
    "runs", "run", "running", "ran", "stands", "stand", "standing", "stood", "sits", "sit", "sitting", "sat",
    "kneels", "kneel", "kneeling", "knelt", "leans", "lean", "leaning", "leaned", "rests", "rest", "resting", "rested",
    "looks", "look", "looking", "looked", "watches", "watch", "watching", "watched", "stares", "stare", "staring",
    "stared", "gazes", "gaze", "gazing", "gazed", "glances", "glance", "glancing", "glanced", "blinks", "blink",
    "blinking", "nods", "nod", "nodding", "nodded", "shakes", "shake", "shaking", "shook", "smiles", "smile",
    "smiling", "smiled", "speaks", "speak", "speaking", "spoke", "says", "say", "saying", "said", "calls", "call",
    "calling", "called", "shouts", "shout", "shouting", "shouted", "whispers", "whisper", "whispering", "sings",
    "sing", "singing", "sang", "breathes", "breathe", "breathing", "exhales", "exhale", "exhaling", "inhales",
    "waves", "wave", "waving", "waved", "points", "point", "pointing", "pointed", "beckons", "salutes", "salute",
    "Waits", "waits", "wait", "waiting", "waited", "stays", "stay", "staying", "stayed", "remains", "remain",
    "moves", "move", "moving", "moved", "shifts", "shift", "shifting", "creeps", "creep", "creeping", "climbs",
    "climb", "climbing", "climbed", "crawls", "crawl", "crawling", "marches", "march", "marching", "falls", "fall",
    "falling", "fell", "rises", "rise", "rising", "rose", "drifts", "drift", "drifting", "thins", "thin", "thinning",
    "glows", "glow", "glowing", "flickers", "flicker", "flickering", "shines", "shine", "shining", "hangs", "hang",
    "hanging", "hung", "ties", "tie", "tying", "wraps", "wrap", "wrapping", "pours", "pour", "pouring", "drinks",
    "drink", "drinking", "eats", "eat", "eating", "smokes", "smoke", "smoking", "cleans", "clean", "cleaning",
    "reads", "read", "reading", "writes", "write", "writing", "folds", "fold", "folding", "unfolds", "tucks", "tuck",
    "grips", "grip", "gripping", "clutches", "clutch", "clutching", "lowers", "lower", "lowering", "aims", "aim",
    "fires", "fire", "firing", "shoots", "shoot", "shooting", "strikes", "strike", "striking", "digs", "dig", "digging",
    # Adjectives & adverbs
    "young", "old", "elder", "bearded", "weathered", "freckled", "tall", "short", "small", "large", "big", "little",
    "tiny", "huge", "vast", "heavy", "light", "warm", "cold", "cool", "freezing", "frozen", "icy", "frosty", "snowy",
    "muddy", "wet", "damp", "dry", "dirty", "clean", "dark", "bright", "dim", "faint", "pale", "deep", "soft", "hard",
    "firm", "rough", "smooth", "sharp", "blunt", "thin", "thick", "wide", "narrow", "high", "low", "long", "brief",
    "slow", "slowly", "quick", "quickly", "fast", "quiet", "quietly", "silent", "silently", "calm", "calmly",
    "steady", "steadily", "gentle", "gently", "careful", "carefully", "faintly", "softly", "firmly", "tightly",
    "loosely", "distant", "far", "near", "close", "closer", "left", "right", "upper", "lower", "front", "back",
    "forward", "forwards", "backward", "backwards", "upward", "upwards", "downward", "downwards", "sideways",
    "white", "black", "grey", "gray", "brown", "red", "blue", "green", "yellow", "orange", "gold", "golden",
    "silver", "amber", "brass", "copper", "iron", "steel", "wooden", "wool", "woolen", "leather", "mud", "earth",
    "british", "german", "french", "saxon", "scottish", "english", "belgian", "russian", "austrian",
    "embossed", "folded", "broken", "ruined", "tattered", "worn", "stained", "rusty", "polished", "lit", "unlit",
    "glowing", "burning", "smoking", "steaming", "falling", "drifting", "rising", "standing", "sitting", "waiting",
    # Human roles, body parts, camera/scene/time/abstract nouns
    "man", "men", "woman", "women", "person", "people", "soldier", "soldiers", "private", "sergeant", "corporal",
    "officer", "captain", "lieutenant", "general", "troop", "troops", "infantry", "sentry", "guard", "guards",
    "comrade", "comrades", "enemy", "enemies", "friend", "friends", "hero", "figure", "figures", "silhouette",
    "crowd", "group", "pair", "boy", "girl", "child", "father", "mother", "brother", "son",
    "body", "bodies", "head", "heads", "face", "faces", "eye", "eyes", "brow", "forehead", "cheek", "cheeks",
    "nose", "mouth", "lips", "lip", "chin", "jaw", "beard", "mustache", "hair", "ear", "ears", "neck", "throat",
    "shoulder", "shoulders", "arm", "arms", "elbow", "wrist", "hand", "hands", "palm", "palms", "finger", "fingers",
    "thumb", "knuckle", "fist", "chest", "breast", "rib", "ribs", "waist", "hip", "hips", "leg", "legs", "thigh",
    "knee", "knees", "shin", "ankle", "foot", "feet", "heel", "toe", "toes", "skin", "bone", "bones", "heart",
    "breath", "voice", "word", "words", "name", "names", "sound", "sounds", "silence", "noise", "song", "carol",
    "gaze", "look", "glance", "expression", "smile", "nod", "gesture", "posture", "stance", "step", "pace", "stride",
    "camera", "frame", "shot", "scene", "view", "angle", "lens", "focus", "foreground", "midground", "background",
    "screen", "edge", "center", "centre", "top", "bottom", "side", "sides", "left", "right", "middle", "corner",
    "distance", "horizon", "space", "place", "spot", "point", "area", "zone", "sector", "line", "lines", "front",
    "trench", "trenches", "field", "fields", "land", "ground", "soil", "dirt", "snow", "ice", "frost", "fog", "mist",
    "haze", "air", "wind", "breeze", "sky", "cloud", "clouds", "sun", "sunrise", "sunset", "dawn", "dusk", "twilight",
    "morning", "noon", "afternoon", "evening", "night", "midnight", "day", "days", "hour", "hours", "minute",
    "moment", "second", "seconds", "time", "winter", "christmas", "eve", "december", "year", "war", "truce", "peace",
    "battle", "light", "lighting", "shadow", "shadows", "darkness", "warmth", "cold", "heat", "motion", "movement",
    "action", "direction", "way", "part", "end", "start", "beginning", "rest", "hold", "push", "pull", "pan", "tilt",
})
_NP_HEAD_RE = re.compile(
    r"\b(?:a|an|the|his|her|their|its|this|that|these|those|two|three|some|another|each|every|"
    r"with|into|onto|from|over|under|against|beside|behind|near|holding|carrying|lifting|raising|opening|taking|waving)\s+"
    r"(?:[a-zA-Z]+[- ]\s*){0,2}([a-zA-Z]{3,})\b",
    re.I,
)
_NEGATION_RE = re.compile(
    r"\b(does\s+not|do\s+not|doesn't|don't|did\s+not|didn't|never\s+\w+|without\s+\w+ing|no\s+one\s+\w+)\b",
    re.I,
)


def _stem_noun(w: str) -> str:
    w = w.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ves") and len(w) > 4:
        return w[:-3] + "f"
    if w.endswith("es") and len(w) > 4 and w[-4:-2] in ("sh", "ch", "ss", "ox", "zz"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _extract_tokens(val) -> set[str]:
    texts: list[str] = []
    if isinstance(val, str):
        texts.append(val)
    elif isinstance(val, (list, tuple, set)):
        for x in val:
            texts.extend(_extract_tokens(x))
        return set(texts)
    elif isinstance(val, dict):
        for k, v in val.items():
            if str(k).lower() not in ("id", "what", "prompt", "names", "kind", "enter", "prop", "props", "objects", "living", "lights", "held_props", "prop_change"):
                if isinstance(v, (str, list, dict)):
                    texts.extend(_extract_tokens(v))
            else:
                texts.extend(_extract_tokens(v))
        return set(texts)
    out: set[str] = set()
    for t in texts:
        for w in re.findall(r"[a-zA-Z]+", str(t)):
            wl = w.lower()
            out.add(wl)
            out.add(_stem_noun(wl))
    return out


def _seen_tokens_of_job(job: dict, doc_names: list[str] | None = None) -> set[str] | None:
    """Return the set of normalized object/prop tokens visible in the start picture OR declared as entering/held props
    (``held_props``, ``prop_change``, ``entering_objects``) when the job supplies ``seen`` or ``start_picture_objects``;
    return ``None`` when no start-picture inventory was attached."""
    seen = job.get("seen")
    raw_list = job.get("start_picture_objects")
    if seen is None and raw_list is None:
        return None
    tokens = _extract_tokens(seen) | _extract_tokens(raw_list)
    for k in ("held_props", "prop_change", "entering_objects", "entering_props", "enter"):
        if job.get(k) is not None:
            tokens |= _extract_tokens(job[k])
    for n in (doc_names or []) + list(job.get("names") or []):
        tokens |= _extract_tokens(n)
    return tokens


def _candidate_prop_nouns(prompt: str, extra_vocab: set[str] | None = None) -> list[str]:
    """C3: extract physical object/prop nouns from ``prompt`` both via general syntactic noun-phrase heads (following
    determiners/prepositions/transitive verbs) and via the known/episode object vocabulary, excluding general non-object
    words (verbs, adjectives, body parts, human roles, camera/time/abstract terms)."""
    known_vocab = set(_CHECKED_PROPS) | {_stem_noun(p) for p in _CHECKED_PROPS} | set(extra_vocab or set())
    candidates: list[str] = []
    # 1. Any word matching known/episode physical object vocabulary
    for w in re.findall(r"[a-zA-Z]+", prompt):
        wl = w.lower()
        stem = _stem_noun(wl)
        if (wl in known_vocab or stem in known_vocab) and wl not in _NON_OBJECT_WORDS and stem not in _NON_OBJECT_WORDS:
            if wl not in candidates:
                candidates.append(wl)
    # 2. General noun-phrase heads (catches unlisted physical nouns like 'kettle', 'sandbag', 'gramophone', 'periscope', etc.)
    for m in _NP_HEAD_RE.finditer(prompt):
        head = m.group(1).lower()
        stem = _stem_noun(head)
        if head in _NON_OBJECT_WORDS or stem in _NON_OBJECT_WORDS:
            continue
        if head.endswith(("ing", "ed", "ly", "ness", "ment", "tion", "sion")) and head not in known_vocab and stem not in known_vocab:
            continue
        if head not in candidates:
            candidates.append(head)
    return candidates


def check_prompt_against_start_picture(job: dict, *, names: list[str] | None = None,
                                       object_vocab: set[str] | None = None) -> list[dict]:
    """VL-17 (Audit #2 & C3): refuse LTX prompts that name physical objects/props absent from the start picture's ``seen``
    inventory (unless declared in ``prop_change`` / ``held_props`` / ``entering_objects``), or that use negative phrasing
    (``does not``, ``never``, ``without ...ing``) in a positive video prompt."""
    sid = str(job.get("id") or job.get("shot_id") or "?")
    prompt = str(job.get("prompt") or "")
    out: list[dict] = []
    neg_hit = _NEGATION_RE.search(prompt)
    if neg_hit:
        out.append({
            "severity": "FAIL",
            "rule": "VL-17",
            "where": sid,
            "detail": f"LTX positive prompt contains negative phrasing {neg_hit.group(0)!r}; LTX ignores negations and animates the named action",
        })
    seen_tokens = _seen_tokens_of_job(job, doc_names=names)
    if seen_tokens is not None:
        missing_props = []
        for w in _candidate_prop_nouns(prompt, extra_vocab=object_vocab):
            stem = _stem_noun(w)
            if w not in seen_tokens and stem not in seen_tokens:
                if w not in missing_props:
                    missing_props.append(w)
        if missing_props:
            out.append({
                "severity": "FAIL",
                "rule": "VL-17",
                "where": sid,
                "detail": f"prompt names object(s) {missing_props} absent from the start picture's seen inventory",
            })
    return out


def ltx_shots(doc: dict) -> list[dict]:
    shots = []
    for j in doc["jobs"]:
        fps = float(j.get("fps", 24) or 24)
        shots.append({"id": j["id"], "kind": "video", "route": "J2", "ltx": True, "prompt": j["prompt"],
                      "seconds": float(j.get("frames", 0)) / fps, "neg": j.get("negative_prompt", ""),
                      **{k: j[k] for k in ("held_props", "camera_end", "prop_change", "exit", "mode", "people", "seen", "start_picture_objects") if k in j}})
    return shots


def ltx(doc: dict) -> list[str]:
    if not doc.get("names"):
        return ["FAIL KP-22 jobs file: no 'names' list (the heroes' story names), so story names in prompts cannot be found"]
    found = list(shot_prompt_lint.check(ltx_shots(doc), names=doc["names"]))
    ep_vocab = _extract_tokens(doc.get("object_vocabulary"))
    for j in doc.get("jobs", []):
        found.extend(check_prompt_against_start_picture(j, names=doc["names"], object_vocab=ep_vocab))
    return [f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}" for f in found if f["severity"] == "FAIL"]


def qwen(doc: dict) -> list[str]:
    return [f"{sev} {rule} {text}" for rule, sev, text in scene_reuse.check_all(doc) if sev == "FAIL"]


def refuse(kind: str, path) -> None:
    """Raise SystemExit with every FAIL of the jobs file at ``path``; return quietly when it passes."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = (ltx if kind == "ltx" else qwen)(doc)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def check_cloud_allowed(*, allow_paid_cloud: bool = False, env=None) -> None:
    """Gate paid cloud preflight behind explicit --allow-paid-cloud (EXPLAINER_LOCAL_ONLY=1 default, D-123)."""
    from explainer_engine import vault
    if vault.is_local_only(env) and not allow_paid_cloud:
        raise SystemExit(
            "DEPRECATED / BLOCKED BY DEFAULT (D-123): paid_preflight is disabled when EXPLAINER_LOCAL_ONLY=1. "
            "Use `python -m explainer_engine.production --check-local` (local_preflight.py) or pass `--allow-paid-cloud`."
        )


def main(argv: list[str]) -> int:
    allow_cloud = '--allow-paid-cloud' in argv
    argv = [a for a in argv if a != '--allow-paid-cloud']
    check_cloud_allowed(allow_paid_cloud=allow_cloud)
    kind, path = argv
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = (ltx if kind == "ltx" else qwen)(doc)
    print("\n".join(bad) or "pass")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
