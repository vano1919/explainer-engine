"""AC-16..AC-19: the episode look. A safety layer ON TOP of the style LoRA that keeps colour and light consistent between
the pictures of one episode, while places, eras and countries change scene to scene. It never replaces the style: the
LT-66 absolutes (qa/style_prompt.ABSOLUTES) stay as they are, and the look only adds a few colour and light words and a
gentle, bounded colour match. ვანო, 2026-10-25 03:04 Tbilisi.

Two parts:
1. Words (AC-17): the episode's colour/light phrase (at most 10 words, colour and light vocabulary only) is added to every
   style-LoRA prompt of the episode; the whole prompt must still pass `style_prompt.check` (40 words), so scene words
   shrink, never the absolutes. A scene may use one of the episode's named light variants (night, interior ...).
2. Pixels (AC-18, AC-19): the look is MEASURED from the episode's approved key frame (Lab mean and spread, hue
   histogram, 6 palette colours; no hex is stored in code). Every new picture's colour distance to it is reported
   (REVIEW when far: a hypothesis, D-59), and a composed frame may be graded toward it at a strength of at most 0.35, on
   the colour channels fully and on lightness at half, so the ink lines and the drawing stay. Originals are kept.

Look file (``episode_look/1``, in the episode folder): ``{"schema", "episode", "key_frame", "phrase", "lights": {name:
phrase}, "lab_mean", "lab_std", "hue_hist", "palette_lab", "grade_max"}``.

    python -m explainer_engine.compose.episode_look make <key_frame> --phrase "..." --out look.json [--episode id]
    python -m explainer_engine.compose.episode_look check <look.json> <image> [--grade out.png]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

from explainer_engine.qa import style_prompt as SP

PHRASE_WORDS = 10        # AC-17
GRADE_MAX = 0.35         # AC-19: the strongest colour match ever applied
DRIFT_REVIEW = 0.35      # AC-18: colour distance above this -> REVIEW (calibrate on the first episode)
COLOUR_WORDS = re.compile(
    r"^(warm|cool|cold|soft|deep|rich|muted|earthy|vivid|glowing|golden|amber|honey|ochre|rust|brick|copper|bronze|"
    r"teal|turquoise|cyan|blue|navy|indigo|violet|purple|lilac|pink|rose|magenta|crimson|red|scarlet|orange|peach|"
    r"yellow|lemon|olive|green|emerald|moss|sage|brown|umber|sepia|cream|ivory|white|grey|gray|charcoal|black|dusk|dawn|"
    r"sunset|sunrise|evening|morning|noon|midday|night|moonlit|candlelit|firelit|lamplit|neon|light|lights|glow|haze|"
    r"hazy|misty|shadows?|tones?|palette|accents?|highlights?|sky|sun|sunlight|moonlight|firelight|torchlight|and|with|"
    r"of|a|the|low|high|dark|bright|pale|dusty|smoky|lit|tinted|washed)$", re.I)


def check_phrase(phrase: str) -> list[dict]:
    """AC-17: colour and light words only, at most 10, and nothing that fights the absolutes."""
    out = []
    words = re.findall(r"[A-Za-z-]+|\d+", phrase)
    if len(words) > PHRASE_WORDS:
        out.append({"rule": "AC-17", "severity": "FAIL", "detail": f"{len(words)} words; at most {PHRASE_WORDS}"})
    other = [w for w in words if not COLOUR_WORDS.match(w)]
    if other:
        out.append({"rule": "AC-17", "severity": "FAIL", "detail": f"not colour or light words: {', '.join(other)}"})
    for rx, rule in ((SP.STYLE_CLASH, "A8"), (SP.LAYOUT, "A6")):
        m = rx.search(phrase)
        if m:
            out.append({"rule": "AC-17", "severity": "FAIL", "detail": f"'{m.group(0)}' breaks {rule}"})
    if SP.TRIGGER in phrase.lower() or SP.STYLE_TAIL[:20] in phrase:
        out.append({"rule": "AC-17", "severity": "FAIL", "detail": "the trigger or the tail belongs to A1/A5, not the look"})
    return out


def apply(prompt: str, look: dict, light: str | None = None) -> tuple[str, list[dict]]:
    """The prompt with the episode phrase (or the scene's light variant) at its end; then the LT-65/66 check of the whole."""
    phrase = look["lights"][light] if light else look["phrase"]
    p = SP.shaped(prompt)
    out = SP.shaped(f"{p}, {phrase}") if phrase.lower() not in p.lower() else p
    return out, check_phrase(phrase) + SP.check(out)


# --- pixels: sRGB -> CIE Lab (D65), numpy only ---------------------------------------------------------------------
def _lab(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def _rgb(lab: np.ndarray) -> np.ndarray:
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16 / 116) / 7.787) * np.array([0.95047, 1.0, 1.08883])
    m = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    c = xyz @ m.T
    c = np.where(c > 0.0031308, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055, 12.92 * c)
    return (np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)


def _small(img, side=256):
    im = img.convert("RGB")
    im.thumbnail((side, side))
    return np.asarray(im)


def measure(img) -> dict:
    lab = _lab(_small(img)).reshape(-1, 3)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    hue = (np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) + 360) % 360
    hist = np.histogram(hue[chroma > 8], bins=12, range=(0, 360))[0].astype(float)
    hist = (hist / hist.sum()) if hist.sum() else hist
    rng = np.random.default_rng(0)                         # 6 palette colours: a few k-means steps on a sample
    pts = lab[rng.choice(len(lab), min(4000, len(lab)), replace=False)]
    cent = pts[rng.choice(len(pts), 6, replace=False)]
    for _ in range(12):
        lab_of = np.argmin(((pts[:, None] - cent[None]) ** 2).sum(-1), 1)
        cent = np.array([pts[lab_of == k].mean(0) if (lab_of == k).any() else cent[k] for k in range(6)])
    return {"lab_mean": lab.mean(0).round(2).tolist(), "lab_std": lab.std(0).round(2).tolist(),
            "hue_hist": hist.round(4).tolist(), "palette_lab": cent.round(1).tolist()}


def make(key_frame, phrase: str, episode: str = "", lights: dict | None = None, key_path: str = "") -> dict:
    found = check_phrase(phrase) + [f for p in (lights or {}).values() for f in check_phrase(p)]
    if any(f["severity"] == "FAIL" for f in found):
        raise ValueError(found)
    return {"schema": "episode_look/1", "episode": episode, "key_frame": key_path, "phrase": phrase,
            "lights": lights or {}, **measure(key_frame), "grade_max": GRADE_MAX}


def drift(img, look: dict) -> dict:
    """AC-18: how far a picture's colours are from the episode look (0 = same). Lab mean shift (in units of the look's
    spread) and hue-histogram distance, averaged. REVIEW at most."""
    m = measure(img)
    mean = np.abs(np.array(m["lab_mean"]) - np.array(look["lab_mean"])) / (np.array(look["lab_std"]) + 5)
    hue = float(np.abs(np.array(m["hue_hist"]) - np.array(look["hue_hist"])).sum()) / 2
    score = round(float(mean.mean()) * 0.5 + hue * 0.5, 3)
    return {"rule": "AC-18", "severity": "REVIEW" if score > DRIFT_REVIEW else "PASS", "drift": score,
            "detail": f"colour distance {score} (REVIEW above {DRIFT_REVIEW})"}


def grade(img, look: dict, strength: float = 0.25):
    """AC-19: a bounded colour match toward the look (Reinhard in Lab): colour channels at ``strength``, lightness at half
    of it, never above ``grade_max``. Returns a new picture; the original is untouched."""
    from PIL import Image
    s = min(float(strength), float(look.get("grade_max", GRADE_MAX)), GRADE_MAX)
    rgb = np.asarray(img.convert("RGB"))
    lab = _lab(rgb)
    mu, sd = lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0) + 1e-6
    tmu, tsd = np.array(look["lab_mean"]), np.array(look["lab_std"]) + 1e-6
    matched = (lab - mu) / sd * tsd + tmu
    w = np.array([s / 2, s, s])
    out = lab * (1 - w) + matched * w
    return Image.fromarray(_rgb(out), "RGB")


def main(argv: list[str]) -> int:
    from PIL import Image
    from explainer_engine.core.store import write_json_atomic
    if argv[0] == "make":
        phrase = argv[argv.index("--phrase") + 1]
        ep = argv[argv.index("--episode") + 1] if "--episode" in argv else ""
        look = make(Image.open(argv[1]), phrase, ep, key_path=argv[1])
        write_json_atomic(Path(argv[argv.index("--out") + 1]), look)
        print(json.dumps({k: look[k] for k in ("phrase", "lab_mean", "lab_std")}))
        return 0
    if argv[0] == "check":
        look = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        img = Image.open(argv[2])
        print(json.dumps(drift(img, look)))
        if "--grade" in argv:
            grade(img, look).save(argv[argv.index("--grade") + 1])
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
