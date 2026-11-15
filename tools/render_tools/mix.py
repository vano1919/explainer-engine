"""Mixer (Upgraded for Truce 1914 Rebuild Steps 1, 4 & 5 + Creator Correction C1):
- Uses Whisper-trimmed [in, out] durations and mutes LTX hallucinated 'You' tails (mute_tail_from_s).
- Frame-locks map drawing sounds (pencil_line__v1, chalk_line__v1) strictly to active drawing spans (ds/df > 0).
- Replaces -9 dB broadband crush with dynamic presence-band (280-3600 Hz) carving (-5.5 dB presence / -1.8 dB outer)
  so wind and fire beds stay alive under narration.
"""
import json, re, glob, sys, os
from pathlib import Path
import numpy as np, av
from scipy import signal

SR = 48000
FPS = 24
H = Path(os.environ.get("TRUCE_HF_DIR", "/Users/vano_tatulashvili/Documents/hf_truce"))
R = Path(os.environ.get("TRUCE_EPISODE_DIR", "/Users/vano_tatulashvili/Documents/explainer-engine-truce/episodes/ep_truce_1914"))
T = json.load(open(H / "dl/explainer-engine/demo_truce_1914/full_film_2026-11-15/inputs/clock/timing.json"))
PLAN = {s["shot"]: s for s in json.load(open(H / "latest_shot_plan.json"))["shots"]}
EP = json.load(open(R / "planning/full_film_2026-11-15/edit_points.json"))["clips"]
ADD = H / "explainer-engine/sound_library_2026-11-15_additions"
LIB = H / "merged_library"
REF = -23.0  # voice level, dBFS RMS

# Step 4 Fix: exact active drawing spans (seconds within shot) where map lines actually draw (ds/df > 0)
MAP_DRAW_SPANS_S = {
    "S02_SH001": (0.20, 4.10),
    "S02_SH002": (0.25, 3.25),
    "S02_SH003": (0.15, 1.85),
    "S05_SH001": (0.20, 2.40),
    "S05_SH002": (0.15, 2.25),
}


def load(path, mono=True):
    c = av.open(str(path))
    rs = av.AudioResampler(format="fltp", layout="mono", rate=SR)
    out = []
    for fr in c.decode(audio=0):
        for f in rs.resample(fr) or []:
            out.append(f.to_ndarray()[0])
    for f in rs.resample(None) or []:
        out.append(f.to_ndarray()[0])
    c.close()
    return np.concatenate(out).astype(np.float32) if out else np.zeros(0, np.float32)


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120


def at_level(x, db):
    return x * 10 ** ((db - rms_db(x)) / 20)


def fit(x, n, fade=0.4):
    if len(x) == 0:
        return np.zeros(n, np.float32)
    if len(x) < n:
        x = np.tile(x, int(np.ceil(n / len(x))))
    x = x[:n].copy()
    k = int(fade * SR)
    k = min(k, n // 2)
    if k:
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
    return x


def pan_st(x, p):
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


ALIAS = {
    "cloth_rustle__v1": "cloth_move__v1",
    "cloth_rustle__v2": "cloth_move__v2",
    "cloth_rustle__v3": "cloth_move__v3",
    "cloth_move__v1..v4": "cloth_move__v1",
    "footstep_snow__v1..v3": "step_dirt_kenney__v1",
    "step_leather__v1..v4": "step_armour__v1",
    "laugh_warm__v1": "fair_people_laughter__v1",
    "pencil_scribble__v1": "pencil_line__v1",
}


def find(tok):
    kind, name = tok[0], tok[2:]
    if kind == "L" and name in ALIAS:
        SUBST.append((name, ALIAS[name]))
        name = ALIAS[name]
    if kind == "L":
        for pat in (f"foley/{name}.wav", f"music/{name}.wav"):
            if (LIB / pat).exists():
                return LIB / pat
        g = glob.glob(str(LIB / "*" / f"{name}*.wav"))
        return Path(g[0]) if g else None
    g = glob.glob(str(ADD / "mixkit" / f"mixkit_{name}_*"))
    return Path(g[0]) if g else None


_cache = {}


def snd(tok):
    if tok not in _cache:
        p = find(tok)
        _cache[tok] = load(p) if p else None
        if p is None:
            GAPS.add(tok)
    return _cache[tok]


GAPS = set()
LOG = []
SUBST = []
total = T["total_frames"]
N = int(total / FPS * SR) + SR
voice = np.zeros(N, np.float32)
diag = np.zeros(N, np.float32)
bus = np.zeros((2, N), np.float32)
music = np.zeros((2, N), np.float32)

# 1. narrator on the film clock
nar = load(R / "audio/narration.wav")
nar = at_level(nar, REF)
ins = sorted(T["inserts"], key=lambda i: i["at_read_frame"])
cuts = sorted({i["at_read_frame"] for i in ins})
bounds = [0] + cuts + [int(len(nar) / SR * FPS) + 1]
for a, b in zip(bounds[:-1], bounds[1:]):
    shift = sum(i["frames"] for i in ins if i["at_read_frame"] <= a)
    seg = nar[int(a / FPS * SR):int(b / FPS * SR)]
    s0 = int((a + shift) / FPS * SR)
    voice[s0:s0 + len(seg)] += seg[:max(0, N - s0)]

# 2. LTX audio: dialogue at full, the rest under the voice, with hallucinated 'You' tail muting
sc = {s["shot_id"]: s for s in json.load(open(R / "story/production_script.json"))["shots"]}
spoken = {i["shot_id"] for i in ins}
for sid, t in T["shots"].items():
    if sc[sid]["route"] != "video":
        continue
    rec = json.load(open(R / "production/video" / f"{sid}.json"))
    e = EP.get(sid, {}) if isinstance(EP.get(sid), dict) else {}
    if e.get("clip_audio") == "mute":
        continue
    ss = float(e["in"]) if "in" in e else (float(rec.get("in_s", 0.0)) if sid in spoken else 0.0)
    raw_x = load(R / rec["raw_path"])
    if e.get("mute_tail_from_s") is not None:
        m_idx = int(float(e["mute_tail_from_s"]) * SR)
        if 0 <= m_idx < len(raw_x):
            fade_n = min(int(0.08 * SR), len(raw_x) - m_idx)
            if fade_n > 0:
                raw_x[m_idx:m_idx + fade_n] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
            raw_x[m_idx + fade_n:] = 0.0
    x = raw_x[int(ss * SR):int((ss + t["frames"] / FPS) * SR)]
    if len(x) < 100:
        continue
    s0 = int(t["start_frame"] / FPS * SR)
    if sid in spoken:
        x = at_level(x, REF)
        diag[s0:s0 + len(x)] += x[:N - s0]
    else:
        x = at_level(x, REF + float(e.get("clip_audio_db", -12)))
        bus[0, s0:s0 + len(x)] += x[:N - s0] * 0.7
        bus[1, s0:s0 + len(x)] += x[:N - s0] * 0.7


# 3. beds and spots from the plan (with Step 4 frame-locked map drawing spans)
def word_t(sid, word):
    for w in T["spines"].get(sid, []):
        if re.sub(r"\W", "", str(w.get("word", ""))).lower() == word.lower():
            return (w.get("frame", w.get("start_frame", 0)) - T["shots"][sid]["start_frame"]) / FPS
    return None


def when_t(sid, when, dur, sound_tok=""):
    w = (when or "").lower()
    if sid in MAP_DRAW_SPANS_S and ("while" in w or "line" in w or "pencil" in sound_tok or "chalk" in sound_tok):
        s_draw, e_draw = MAP_DRAW_SPANS_S[sid]
        return s_draw, max(0.2, min(dur - s_draw, e_draw - s_draw))
    if not w or "whole" in w or w.startswith("while") or "loop" in w:
        return 0.0, dur
    m = re.search(r"'([^']+)'", w)
    if m:
        t = word_t(sid, m.group(1).split()[0])
        if t is not None:
            return t, None
    m = re.search(r"(\d+(?:\.\d+)?)\s*s", w)
    if m:
        return min(float(m.group(1)), max(0, dur - 0.3)), None
    return dur * 0.3, None


def place(x, sid, t0, level, pan, loop_dur=None, lp=None, hp=None):
    st = T["shots"][sid]
    s0 = int((st["start_frame"] / FPS + t0) * SR)
    if loop_dur:
        x = fit(x, int(loop_dur * SR), 0.35)
    if lp:
        x = signal.sosfilt(signal.butter(2, lp, "low", fs=SR, output="sos"), x)
    if hp:
        x = signal.sosfilt(signal.butter(2, hp, "high", fs=SR, output="sos"), x)
    x = at_level(x, REF + level) if rms_db(x) > -100 else x
    y = pan_st(x, pan)
    e = min(N, s0 + y.shape[1])
    bus[:, s0:e] += y[:, :e - s0]


for sid in T["shots"]:
    p = PLAN.get(sid)
    if not p or not p.get("audio"):
        continue
    a = p["audio"]
    dur = T["shots"][sid]["frames"] / FPS
    bed = a.get("bed") or ""
    if bed and bed.strip().lower() != "none":
        lp = float(re.search(r"low-passed\s*(\d+(?:\.\d+)?)\s*kHz", bed).group(1)) * 1000 if re.search(r"low-passed\s*(\d+(?:\.\d+)?)\s*kHz", bed) else None
        hp = float(re.search(r"high-pass\s*(\d+)\s*Hz", bed).group(1)) if re.search(r"high-pass\s*(\d+)\s*Hz", bed) else None
        for m in re.finditer(r"\b([LM]:[A-Za-z0-9_\.\-]+)[^+]*?(?:(?<=\s)|^)(-\d+)", bed):
            x = snd(m.group(1))
            if x is None:
                continue
            seg = bed[m.start():].split("+")[0]
            pn = re.search(r"pan\s*([+-]?\d*\.?\d+)", seg)
            place(x, sid, 0.0, float(m.group(2)), float(pn.group(1)) if pn else 0.0, loop_dur=dur, lp=lp, hp=hp)
    for sp in a.get("spots") or []:
        s = sp.get("sound", "")
        tok = re.search(r"\b([LM]:[A-Za-z0-9_\.\-]+)", s)
        if not tok:
            continue
        x = snd(tok.group(1))
        if x is None:
            continue
        t0, ld = when_t(sid, sp.get("when"), dur, sound_tok=tok.group(1))
        place(x[:int(min(len(x), 6 * SR))] if not ld else x, sid, t0, float(sp.get("level_db", -24)), float(sp.get("pan", 0)), loop_dur=ld)

# 4. music accents (clock seconds)
MUS = [
    ("mus_echoes_of_time__v1", 0.5, 29.0, -30, 4),
    ("mus_dark_times__v1", 46.0, 56.0, -32, 0),
    ("mus_lightless_dawn__v1", 143.8, 165.8, -32, 0),
    ("mus_village_consort__v1", 204.4, 246.0, -33, 0),
    ("mus_despair_and_triumph__v1", 298.2, 320.0, -31, 0),
    ("mus_thunder_dreams__v1", 341.0, 352.0, -34, 0),
    ("mus_ancient_rite__v1", 352.8, 378.0, -31, 0),
]
for name, a, b, lv, _ in MUS:
    x = snd("L:" + name)
    if x is None:
        continue
    x = fit(x, int((b - a) * SR), 2.0)
    x = at_level(x, REF + lv)
    s0 = int(a * SR)
    music[:, s0:s0 + len(x)] += np.stack([x, x]) * 0.7
sil = ADD / "music/km_silent_night.mp3"
if sil.exists():
    x = load(sil)
    x = x[:int(5.5 * SR)]
    x = fit(x, len(x), 1.5)
    x = at_level(x, REF - 28)
    s0 = int(374.4 * SR)
    music[:, s0:s0 + len(x)] += np.stack([x, x]) * 0.7

# 5. Step 5 Fix: Dynamic presence-band (280-3600 Hz) ducking instead of -9 dB broadband crush
env = np.abs(voice + diag)
win = int(0.12 * SR)
env = np.convolve(env, np.ones(win, dtype=np.float32) / win, "same")
gate = (env > 10 ** ((REF - 14) / 20)).astype(np.float32)
gate = np.clip(np.convolve(gate, np.ones(int(0.32 * SR), dtype=np.float32) / int(0.32 * SR), "same"), 0.0, 1.0)
bg_total = bus + music
sos_bp = signal.butter(2, [280.0, 3600.0], btype="bandpass", fs=SR, output="sos")
bg_presence = signal.sosfilt(sos_bp, bg_total, axis=-1).astype(np.float32)
bg_outer = bg_total - bg_presence
duck_pres = 10 ** (-5.5 * gate / 20)
duck_outer = 10 ** (-1.8 * gate / 20)
mix = np.stack([voice + diag, voice + diag]) + bg_presence * duck_pres + bg_outer * duck_outer
mix = mix[:, :int(total / FPS * SR)]
pk = np.max(np.abs(mix))
print("peak", pk, "gaps", sorted(GAPS))
import wave
out = H / "work/mix_raw.wav"
pcm = (np.clip(mix / max(1.0, pk), -1, 1) * 32767).astype(np.int16).T.copy()
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
json.dump({"gaps": sorted(GAPS), "substituted": sorted(set(SUBST))}, open(H / "work/audio_gaps.json", "w"), indent=1)
print("written", out)
