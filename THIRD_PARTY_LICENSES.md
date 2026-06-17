# Third-Party Licenses

This project (`indian-tts`) is licensed under the Apache License 2.0 — see
[`LICENSE`](LICENSE). It bundles or depends on the third-party components below.
**All are Apache-2.0 and cleared for commercial use.** When you redistribute an
application built on this project, retain these notices (Apache-2.0 §4).

| Component | Role | License | Source |
| --- | --- | --- | --- |
| **Kokoro-82M** (`hexgrad/Kokoro-82M`) | TTS model weights + voices (`hf_alpha`, `hf_beta`, `hm_omega`) | Apache-2.0 | https://huggingface.co/hexgrad/Kokoro-82M |
| **misaki** | grapheme-to-phoneme (g2p) | Apache-2.0 | https://github.com/hexgrad/misaki |
| **Transformers** (Hugging Face) | runs Kokoro's ALBERT text model | Apache-2.0 | https://github.com/huggingface/transformers |
| **PyTorch** / **torchaudio** | tensor + audio runtime | BSD-3-Clause | https://github.com/pytorch/pytorch |
| **Typer** | CLI framework | MIT | https://github.com/fastapi/typer |
| **Gradio** | local web UI | Apache-2.0 | https://github.com/gradio-app/gradio |
| **soundfile**, **numpy**, **num2words**, **pyyaml**, **sentencepiece**, **protobuf** | audio/text/util libs | BSD/MIT/Apache-2.0 | (PyPI) |
| **pytesseract** | Tesseract OCR wrapper | Apache-2.0 | https://github.com/madmaze/pytesseract |
| **Pillow** | image loading | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| **ollama** (python client) | local LLM client | MIT | https://github.com/ollama/ollama-python |

A full copy of the Apache License 2.0 is in [`LICENSE`](LICENSE).

## External tools used by the image pipeline (not bundled)

The "From image" feature shells out to tools you install separately:

| Tool | Role | License | Notes |
| --- | --- | --- | --- |
| **Tesseract OCR** | OCR engine | Apache-2.0 | Commercial-safe. |
| **Ollama** (app/server) | runs local LLMs | MIT | Commercial-safe. |
| **LLM model** (default `qwen2.5`) | the analysis | **model-specific** | ⚠️ See below. |

**⚠️ The LLM model carries its own license, separate from everything above.** The
default is **`qwen2.5` (7B), which is Apache-2.0** — chosen so the image pipeline is
commercial-safe by default. Other permissive choices via `--model`:
- `mistral` — Apache-2.0
- `phi3` — MIT

**Avoid `llama3`** for a commercial product unless you comply with the **Meta Llama 3
Community License** — usage restrictions (incl. a large-scale MAU threshold), an
acceptable-use policy, and a "Built with Llama" attribution requirement; it is **not**
OSI-permissive. Whichever model you ship, review and comply with that model's license.

## Notes for commercial / monetized use

- **No gated TTS dependencies.** The optional Indic Parler-TTS backend (which was gated
  on Hugging Face and carried a separate access agreement) has been removed; the TTS path
  requires no model-specific terms. (The optional image pipeline's *LLM model* is the one
  exception — see the ⚠️ note above.)
- **Trademarks:** Apache-2.0 grants no trademark rights. Do not imply endorsement by
  Kokoro or its authors.
- **Outputs / voice likeness:** Generated audio is generally yours to use. Resembling a
  real, identifiable person's voice (right of publicity) is a separate legal matter —
  low risk with these synthetic preset voices.
- **Not legal advice.** For a revenue product, have an IP attorney confirm.
