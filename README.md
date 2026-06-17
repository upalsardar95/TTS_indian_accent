# 📖 Indian-accent Hinglish Storytelling TTS

An **offline** text-to-speech engine for **storytelling and rhymes**, speaking
**English + Hindi (Hinglish)** with an **Indian accent**. Built with a reusable
Python core, a CLI, and a local web UI, behind a pluggable backend layer.

- **Engine:** [Kokoro-82M] — tiny, fast, Apache-2.0, **not gated**, and cleared
  for **commercial use**. Uses the Hindi pipeline whose phonemizer reads English
  words inside Hindi text (code-switching) with an Indian-accented voice.

[Kokoro-82M]: https://huggingface.co/hexgrad/Kokoro-82M

## Features

- **Hinglish**: handles English, Hindi, and code-mixed text.
- **Expressive presets** — `classic-storyteller`, `bedtime`, `energetic-rhyme`.
- **Rhythm-aware**: stories are chunked by line/stanza with tunable pauses so
  rhymes don't sound rushed.
- **Three ways to use it**: import the core, run the CLI, or open the web UI.
- **Pluggable backend** layer behind one interface (Kokoro today; easy to extend).

## Requirements

- **Python 3.10–3.12** (Kokoro and its g2p stack require 3.10+). This project was
  set up and verified on **Python 3.11**.
- NVIDIA GPU optional. Kokoro is real-time even on CPU; it will use CUDA if
  available. The pinned PyTorch wheels are **CUDA 11.8** builds (compatible with
  older drivers such as 457.49 on a GTX 1650).

## Install

**Quick setup (recommended):** one script creates the venv, installs everything, and
verifies the environment — use it on any fresh machine after cloning:

```powershell
.\scripts\setup.ps1
# or, if `py` isn't available:  .\scripts\setup.ps1 -PythonLauncher "C:\Python311\python.exe"
```

<details><summary>Manual steps (what the script runs)</summary>

```powershell
# Use Python 3.11 explicitly to create the venv
& "$env:LocalAppData\Programs\Python\Python311\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt   # torch (cu118) + kokoro + everything else
pip install -e .                  # installs the `indian-tts` / `indian-tts-web` commands
```
</details>

For a CPU-only server / container, skip the venv and use the [Dockerfile](Dockerfile)
(`requirements-cpu.txt`) — see [DEPLOY.md](DEPLOY.md).

The Kokoro model (~330 MB) downloads automatically on first use. No login needed.

> **Windows tip:** set `$env:PYTHONUTF8 = "1"` so the console can print Devanagari,
> and optionally `$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"` to quiet a cache warning.

## Usage

### CLI

```powershell
# Speak a line (Devanagari, Latin, or mixed)
indian-tts say "नमस्ते बच्चों! Once upon a time, ek choti si chidiya thi." -o outputs/hello.wav

# Narrate a whole story file with an expressive rhyme voice
indian-tts file examples/sample_story.txt --voice energetic-rhyme -o outputs/story.wav

# List voices, or launch the web UI
indian-tts voices
indian-tts serve
```

Useful flags: `--voice/-v`, `--backend/-b` (`kokoro`),
`--line-pause`, `--stanza-pause`, `--max-chars`, `--no-numbers`, `--verbose`.

### Web UI

```powershell
indian-tts-web         # or: indian-tts serve
```

Open http://127.0.0.1:7860 — the **From text** tab takes typed/pasted text; the
**From image** tab takes a story photo (see below). Pick a voice, generate, then
play or download.

### From an image (OCR → Hindi explanation → narration)

Read a picture of a story, get a sentence-by-sentence **Hindi explanation + moral**
from a local LLM, then narrate the **story first, then the explanation**:

```powershell
indian-tts image story_image.jpg -o outputs/story.wav
indian-tts image story_image.jpg --model mistral -o outputs/story.wav   # different model
indian-tts image story_image.jpg --no-analysis -o outputs/story.wav     # narrate story only
```

This step needs two external tools (both free, run locally):

1. **Tesseract OCR** — install the engine
   ([Windows builds](https://github.com/UB-Mannheim/tesseract/wiki)). The standard
   install path (`C:\Program Files\Tesseract-OCR`) is auto-detected — no setup needed.
   Only if you install it elsewhere, point to it:
   `$env:TESSERACT_CMD = "D:\path\to\tesseract.exe"`.
2. **Ollama** — install [ollama.com](https://ollama.com), start the app, and pull the
   default model: `ollama pull qwen2.5` (or your chosen `--model`).

> **Licensing for monetized apps:** the default model is **`qwen2.5` (Apache-2.0)**,
> chosen so the image pipeline is commercial-safe out of the box. Other permissive
> options via `--model`: `mistral` (Apache-2.0), `phi3` (MIT). Avoid `llama3` in a
> commercial product unless you accept **Meta's Llama 3 Community License** (usage
> restrictions + "Built with Llama" attribution). Tesseract and the
> `pytesseract`/`ollama`/`pillow` libraries are permissively licensed.

### Python API

```python
from indian_tts.core.synthesize import synthesize_to_file

synthesize_to_file(
    "Twinkle twinkle little star, तुम कितने प्यारे हो!",
    "outputs/rhyme.wav",
    voice="energetic-rhyme",
)
```

### HTTP API (call from another project / language)

To use the TTS feature from a **separate project** without installing the heavy
`torch`/`kokoro` stack there, run it as an HTTP service. The model loads once in the
server process; callers just send plain HTTP and get audio bytes back.

Start the server (in this project's venv):

```powershell
indian-tts-api                       # serves http://127.0.0.1:8000
indian-tts serve-api --port 9000     # or via the CLI, custom port
```

To reach it from another machine, bind all interfaces first:
`$env:INDIAN_TTS_API_HOST = "0.0.0.0"` (or `--host 0.0.0.0`).

Endpoints: `POST /synthesize` (returns audio), `GET /voices`, `GET /backends`,
`GET /health`. Interactive docs at `http://127.0.0.1:8000/docs`.

Call it from any other Python project (only `requests` needed there):

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8000/synthesize",
    json={"text": "नमस्ते! Once upon a time, एक छोटी सी चिड़िया थी।",
          "voice": "classic-storyteller", "format": "wav"},
    timeout=300,
)
resp.raise_for_status()
with open("out.wav", "wb") as f:
    f.write(resp.content)
```

`/synthesize` accepts the same knobs as the Python API: `voice`, `backend`,
`line_pause`, `stanza_pause`, `max_chars`, `normalize_numbers`, and `format`
(`wav`/`flac`/`ogg`). Any HTTP client works — e.g. with `curl`:

```powershell
curl -s -X POST http://127.0.0.1:8000/synthesize -H "Content-Type: application/json" `
  -d '{"text":"नमस्ते! Hello.","voice":"bedtime"}' --output test.wav
```

**API key (for public/hosted servers):** set the env var `INDIAN_TTS_API_KEY` and the
API requires a matching `X-API-Key` header on `/synthesize`, `/voices`, and `/backends`
(`/health` stays open). If the var is unset, the API is open — convenient for local use.

```powershell
$env:INDIAN_TTS_API_KEY = "your-secret-key"; indian-tts-api
# then callers add:  -H "X-API-Key: your-secret-key"
```

**Hosting it online** (so it runs while your PC is off): a `Dockerfile`, CPU-only
`requirements-cpu.txt`, and step-by-step instructions for Hugging Face Spaces,
Render/Railway, and a VPS are in [DEPLOY.md](DEPLOY.md).

## Tips for best Hinglish results

- Kokoro renders **Hindi best in Devanagari** (`नमस्ते`) and English words inline;
  the Hindi voice gives the English an Indian accent. Pure-romanized Hindi
  ("namaste") is read more like English.
- Keep one sentence per line / use blank lines between stanzas — the chunker turns
  those into natural pauses (tune with `--line-pause` / `--stanza-pause`).

## Voices

`config/voices.yaml` maps each preset to a Kokoro voice id (`kokoro_voice`):

| preset | kokoro_voice | character |
| --- | --- | --- |
| `classic-storyteller` | `hf_alpha` (f) | expressive, moderate pace |
| `bedtime` | `hf_beta` (f) | slow, soft, soothing |
| `energetic-rhyme` | `hm_omega` (m) | lively, playful, faster |

Add or tune voices by editing `config/voices.yaml`. Kokoro Hindi voice ids start
with `hf_` (female) / `hm_` (male).

## Running offline

Kokoro caches after first use; to forbid any network access afterwards:

```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
```

## Project layout

```
config/voices.yaml          # voice presets (edit to add/tune voices)
src/indian_tts/engine/      # backend abstraction + Kokoro backend
src/indian_tts/core/        # text preprocessing, chunking, audio, orchestration
                            #   + story_image.py (OCR + Ollama image pipeline)
src/indian_tts/cli/         # Typer CLI
src/indian_tts/web/         # Gradio web UI
scripts/check_env.py        # environment diagnostic
scripts/bench.py            # load/generation timing benchmark
examples/sample_story.txt   # Hinglish sample
```

## Licensing

This project and every model/library it ships are **Apache-2.0**, which permits
**commercial use** (royalty-free, no non-commercial clause). No gated dependencies.

| Component | License |
| --- | --- |
| This project | Apache-2.0 (`LICENSE`) |
| Kokoro-82M (`hexgrad/Kokoro-82M`) + its voices | Apache-2.0 |
| misaki (g2p) | Apache-2.0 |
| transformers | Apache-2.0 |

When you distribute an app built on this, retain the license/attribution notices —
see [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Notes:
- Apache-2.0 grants **no trademark** rights — don't imply endorsement by Kokoro/its authors.
- Model **outputs** are generally yours; *voice likeness* (resembling a real,
  identifiable person) is a separate legal area — low risk with these synthetic voices.
- Voice cloning (mimic a specific narrator) is not included; it could be added via an
  XTTS-v2 backend behind the same interface (note: **XTTS-v2 is non-commercial** — keep
  it out if you monetize).

_This is informational, not legal advice; for a revenue product, have an IP attorney confirm._
