"""Local Gradio web UI: type/paste a story, pick a voice, play & download.

Runs entirely offline (after models are cached). The same synthesis core powers
this and the CLI, so behavior is identical.
"""

from __future__ import annotations

import logging

import gradio as gr

from ..core.presets import list_preset_names
from ..core.synthesize import synthesize_text
from ..engine import get_backend
from ..engine.registry import DEFAULT_BACKEND, available_backends

logger = logging.getLogger(__name__)

_SAMPLE = (
    "नमस्ते बच्चों! Once upon a time, एक छोटी सी चिड़िया थी।\n"
    "She loved to sing, और पेड़ों पर उड़ती थी।\n\n"
    "Twinkle twinkle little star,\n"
    "तुम कितने प्यारे हो, कितने दूर!"
)


def _synthesize(text, voice, backend, line_pause, stanza_pause):
    if not text or not text.strip():
        raise gr.Error("Please enter some text to narrate.")
    audio, sample_rate = synthesize_text(
        text,
        voice=voice,
        backend=backend,
        line_pause=line_pause,
        stanza_pause=stanza_pause,
    )
    return (sample_rate, audio)


def _synthesize_image(image_path, voice, model, analyze):
    """OCR an image, optionally explain it in Hindi, then narrate story + analysis."""
    if not image_path:
        raise gr.Error("Please upload a story image.")
    from ..core.story_image import process_image

    try:
        result = process_image(image_path, model=model, analyze=analyze)
    except (RuntimeError, ValueError) as err:
        raise gr.Error(str(err))

    audio, sample_rate = synthesize_text(result.narration, voice=voice)
    analysis_md = result.analysis if result.analysis else "_(analysis skipped)_"
    return result.story, analysis_md, (sample_rate, audio)


def build_demo() -> gr.Blocks:
    presets = list_preset_names()
    default_voice = "classic-storyteller" if "classic-storyteller" in presets else presets[0]

    with gr.Blocks(title="Indian-accent Storytelling TTS") as demo:
        gr.Markdown(
            "# 📖 Hinglish Storytelling TTS\n"
            "Offline English + Hindi narration with an Indian accent."
        )

        with gr.Tabs():
            with gr.Tab("From text"):
                with gr.Row():
                    with gr.Column(scale=3):
                        text = gr.Textbox(
                            label="Story / rhyme text",
                            value=_SAMPLE,
                            lines=10,
                            placeholder="Type or paste your story here (English, Hindi, or mixed)...",
                        )
                    with gr.Column(scale=1):
                        voice = gr.Dropdown(presets, value=default_voice, label="Voice preset")
                        backend = gr.Dropdown(
                            available_backends(), value=DEFAULT_BACKEND, label="Backend"
                        )
                        line_pause = gr.Slider(0.0, 1.5, value=0.35, step=0.05,
                                               label="Pause between lines (s)")
                        stanza_pause = gr.Slider(0.0, 2.5, value=0.75, step=0.05,
                                                 label="Pause between stanzas (s)")
                        go = gr.Button("🔊 Generate", variant="primary")
                out = gr.Audio(label="Narration", type="numpy")

                go.click(
                    _synthesize,
                    inputs=[text, voice, backend, line_pause, stanza_pause],
                    outputs=out,
                )

            with gr.Tab("From image"):
                gr.Markdown(
                    "Upload a picture of a story. It's read with OCR, optionally "
                    "explained in Hindi by a local Ollama model, then narrated "
                    "(story first, then the explanation + moral)."
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        image_in = gr.Image(type="filepath", label="Story image")
                    with gr.Column(scale=1):
                        img_voice = gr.Dropdown(presets, value=default_voice, label="Voice preset")
                        model_in = gr.Textbox(value="qwen2.5", label="Ollama model")
                        analyze_chk = gr.Checkbox(
                            value=True, label="Add Hindi explanation + moral (Ollama)"
                        )
                        img_go = gr.Button("🔊 Read image", variant="primary")
                with gr.Row():
                    extracted = gr.Textbox(label="Extracted story", lines=6)
                    analysis_out = gr.Markdown(label="Hindi explanation + moral")
                img_audio = gr.Audio(label="Narration", type="numpy")

                img_go.click(
                    _synthesize_image,
                    inputs=[image_in, img_voice, model_in, analyze_chk],
                    outputs=[extracted, analysis_out, img_audio],
                )
    return demo


def preload(backend: str = DEFAULT_BACKEND) -> None:
    """Load + warm the model before serving so the first request is fast.

    Without this the model loads lazily on the user's first click, which on a
    cold GPU means a ~2-minute stall (model load + one-time CUDA warm-up).
    Doing it up front moves that cost to server startup; generations stay hot.
    """
    logger.info("Preloading backend %r (load + warm-up)...", backend)
    get_backend(backend)
    logger.info("Backend ready; generations will be fast.")


def main() -> None:
    """Console-script entry point (`indian-tts-web`)."""
    logging.basicConfig(level=logging.INFO)
    preload()
    build_demo().launch()


if __name__ == "__main__":
    main()
