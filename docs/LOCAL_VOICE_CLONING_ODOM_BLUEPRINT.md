# Local Emotion-Controlled Odom Voice Cloning Blueprint (Future Episodes)

> **Policy Note:** For *The First Fire* v3 (Master Prompt v3.2), the final master strictly uses real **ElevenLabs Odom** (`CcSJ2r3qw0XU9gJpEPyk`, `eleven_v4`) + `explainer_engine/audio/narrator_polish.py`. This blueprint defines the lightweight local voice-cloning lane for future episodes once verified by the creator's ears and legal/terms review.

## 1. Objective
Reproduce Odom's deep, resonant, dramatic documentary timbre **locally on GPU/Modal at near-$0 marginal cost** with explicit **per-sentence emotion, pacing, and emphasis control** — passing the exact same `explainer_engine/audio/narrator_polish.py` chain and `voice_check.py` timbre gate.

## 2. Candidate Lightweight Local Voice-Cloning Models (2026)

| Model | Size / VRAM | License | Emotion & Prosody Control | Zero-Shot Ref Audio | Best Fit |
|---|---|---|---|---|---|
| **Chatterbox / Chatterbox-Turbo** (Resemble AI) | `350M–500M` (~2–4 GB VRAM, runs fast on L4/T4 or Mac M-series) | MIT | Direct continuous `exaggeration` (`0.0–1.0`) + `cfg_weight` pacing control + paralinguistic tags (`[sigh]`, `[pause]`) | 10–15 s clean mono WAV | **Primary Recommendation** — lightest, sharpest English documentary prosody, easiest per-line emotion slider |
| **CosyVoice2-0.5B** (FunAudioLLM) | `0.5B` (~3 GB VRAM) | Apache-2.0 | Natural-language emotion/style instruct prompt (e.g., *"Speak in a hushed, grave documentary whisper"*) | 5–10 s clean WAV | Best for explicit style-instruction switching (whisper vs triumphant climax) |
| **Orpheus-3B-0.1-ft** (Canopy Labs) | `3B` (~6–8 GB VRAM, 4-bit GGUF/AWQ works on 6 GB) | Apache-2.0 | Native inline tags (`<gasp>`, `<sigh>`, `<chuckle>`) + LLM-level dramatic cadence | Reference-conditioned / LoRA fine-tune | Highest human-like phrasing if fine-tuned with a 10–20 min LoRA |
| **F5-TTS** | `335M` (~2.5 GB VRAM) | MIT | Prosody transferred from matched-mood reference clips (Multi-Mood Reference Bank) | 8–12 s per mood | Ultra-fast, rock-solid pronunciation; pair with 4 mood reference clips |

## 3. Recommended Pipeline Architecture (`explainer_engine/audio/local_odom_clone.py` — Future Lane)

1. **Multi-Mood Reference Bank (`assets/audio/voices/odom_refs/`):**
   Slice 4 clean, noise-free `10–12s` 48 kHz mono reference takes from approved ElevenLabs Odom sessions (pre-polish raw audio so polish is applied once at the end):
   - `odom_ref_hook_urgent.wav` — tight, urgent, high-stakes opening cadence
   - `odom_ref_narration_calm.wav` — warm, authoritative documentary explanation
   - `odom_ref_tension_hushed.wav` — dark, low, suspenseful predator/crisis tone
   - `odom_ref_climax_triumph.wav` — resonant, sweeping awe for payoff beats
2. **Per-Line Emotion Control Schema (`narration_script.json`):**
   ```json
   {
     "id": "line_07",
     "text": "One spark changes the chemistry of survival forever.",
     "mood": "climax_triumph",
     "exaggeration": 0.62,
     "cfg_weight": 0.45,
     "speed": 0.94,
     "dramatic_breather_after_s": 1.4
   }
   ```
3. **Post-Synthesis Parity Chain (Identical to ElevenLabs Odom):**
   - Resample to 48 kHz PCM -> run [`explainer_engine/audio/narrator_polish.py`](../explainer_engine/audio/narrator_polish.py) (`highpass=60`, `afftdn`, `+12 dB @ 150 Hz`, `-2 dB @ 300 Hz`, `alimiter=0.95`).
   - Align word timestamps via `faster-whisper` (`small.en` / `base.en`) + verify `WER <= 5%` and 100% proper nouns via `check_tts_pronunciation_asr()`.
   - Run **Timbre Similarity Gate** (`explainer_engine/audio/voice_check.py` + Resemblyzer / WavLM cosine similarity >= `0.85` against Odom baseline) before accepting any line.
4. **Rights & Commercial Safety Checklist:**
   - Before deploying a cloned voice commercially on YouTube, verify ElevenLabs Terms of Service / voice actor license for `Odom` (`CcSJ2r3qw0XU9gJpEPyk`, library voice) — alternatively, train/condition the exact same local emotion-controlled pipeline on an **owned voice actor recording** or **public-domain/CC0 voice donor** for 100% perpetual commercial ownership with zero licensing ambiguity.
