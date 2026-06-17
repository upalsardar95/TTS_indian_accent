"""Typer CLI for the Hinglish storytelling TTS engine.

Examples
--------
  indian-tts say "नमस्ते! Once upon a time, एक छोटी सी चिड़िया थी." -o outputs/hello.wav
  indian-tts file examples/sample_story.txt --voice energetic-rhyme -o outputs/story.wav
  indian-tts voices
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

from ..core.presets import list_preset_names
from ..core.synthesize import synthesize_to_file
from ..engine.registry import DEFAULT_BACKEND, available_backends

app = typer.Typer(
    add_completion=False,
    help="Offline Hinglish (English + Hindi) storytelling & rhyme TTS, Indian accent.",
)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _bar(done: int, total: int) -> None:
    typer.echo(f"\r  chunk {done}/{total}", nl=(done == total))


def _generate(text: str, out: Path, voice: str, backend: str, line_pause, stanza_pause,
              max_chars: int, no_numbers: bool, verbose: bool) -> None:
    _setup_logging(verbose)
    if not text.strip():
        typer.secho("No text to synthesize.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    typer.echo(f"Synthesizing with voice={voice!r} backend={backend!r} -> {out}")
    synthesize_to_file(
        text,
        out,
        voice=voice,
        backend=backend,
        line_pause=line_pause,
        stanza_pause=stanza_pause,
        max_chars=max_chars,
        normalize_numbers=not no_numbers,
        progress=_bar,
    )
    typer.secho(f"Done: {out}", fg=typer.colors.GREEN)


# Shared options
_VoiceOpt = typer.Option("classic-storyteller", "--voice", "-v", help="Voice preset name.")
_BackendOpt = typer.Option(DEFAULT_BACKEND, "--backend", "-b",
                           help=f"TTS backend ({', '.join(available_backends())}).")
_OutOpt = typer.Option(Path("outputs/output.wav"), "--out", "-o", help="Output .wav/.flac/.ogg.")
_LinePauseOpt = typer.Option(None, "--line-pause", help="Override per-line pause (seconds).")
_StanzaPauseOpt = typer.Option(None, "--stanza-pause", help="Override per-stanza pause (seconds).")
_MaxCharsOpt = typer.Option(200, "--max-chars", help="Max characters per synthesis chunk.")
_NoNumbersOpt = typer.Option(False, "--no-numbers", help="Do not spell out digits as words.")
_VerboseOpt = typer.Option(False, "--verbose", help="Verbose logging.")


@app.command()
def say(
    text: str = typer.Argument(..., help="Text to speak (use quotes)."),
    voice: str = _VoiceOpt,
    backend: str = _BackendOpt,
    out: Path = _OutOpt,
    line_pause: float = _LinePauseOpt,
    stanza_pause: float = _StanzaPauseOpt,
    max_chars: int = _MaxCharsOpt,
    no_numbers: bool = _NoNumbersOpt,
    verbose: bool = _VerboseOpt,
) -> None:
    """Speak a line of text given on the command line."""
    _generate(text, out, voice, backend, line_pause, stanza_pause, max_chars, no_numbers, verbose)


@app.command()
def file(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Text file to narrate."),
    voice: str = _VoiceOpt,
    backend: str = _BackendOpt,
    out: Path = _OutOpt,
    line_pause: float = _LinePauseOpt,
    stanza_pause: float = _StanzaPauseOpt,
    max_chars: int = _MaxCharsOpt,
    no_numbers: bool = _NoNumbersOpt,
    verbose: bool = _VerboseOpt,
) -> None:
    """Narrate a whole story/rhyme from a text file."""
    text = path.read_text(encoding="utf-8")
    _generate(text, out, voice, backend, line_pause, stanza_pause, max_chars, no_numbers, verbose)


_ModelOpt = typer.Option("qwen2.5", "--model",
                         help="Ollama model for the Hindi analysis (default qwen2.5, Apache-2.0).")
_NoAnalysisOpt = typer.Option(False, "--no-analysis",
                              help="Skip the LLM step; narrate only the extracted story.")


@app.command()
def image(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Story image (jpg/png/…)."),
    voice: str = _VoiceOpt,
    out: Path = _OutOpt,
    model: str = _ModelOpt,
    no_analysis: bool = _NoAnalysisOpt,
    line_pause: float = _LinePauseOpt,
    stanza_pause: float = _StanzaPauseOpt,
    max_chars: int = _MaxCharsOpt,
    no_numbers: bool = _NoNumbersOpt,
    verbose: bool = _VerboseOpt,
) -> None:
    """Read a story image: OCR -> Hindi explanation (Ollama) -> narrate as audio."""
    _setup_logging(verbose)
    from ..core.story_image import process_image

    typer.echo(f"Reading image: {path}")
    try:
        result = process_image(path, model=model, analyze=not no_analysis)
    except (RuntimeError, ValueError) as err:
        typer.secho(str(err), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    typer.echo("\n--- Extracted story ---")
    for line in result.lines:
        typer.echo(f"  {line}")
    if result.analysis:
        typer.echo("\n--- Hindi explanation + moral ---")
        typer.echo(result.analysis)

    typer.echo(f"\nSynthesizing with voice={voice!r} -> {out}")
    synthesize_to_file(
        result.narration,
        out,
        voice=voice,
        line_pause=line_pause,
        stanza_pause=stanza_pause,
        max_chars=max_chars,
        normalize_numbers=not no_numbers,
        progress=_bar,
    )
    typer.secho(f"Done: {out}", fg=typer.colors.GREEN)


@app.command()
def voices() -> None:
    """List available voice presets."""
    for name in list_preset_names():
        typer.echo(f"  {name}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(7860, help="Port to bind."),
    share: bool = typer.Option(False, help="Create a public Gradio share link."),
) -> None:
    """Launch the local web UI."""
    from ..web.app import build_demo, preload

    _setup_logging(True)
    preload()  # load + warm the model now so the first click is fast
    build_demo().launch(server_name=host, server_port=port, share=share)


@app.command(name="serve-api")
def serve_api(
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8000, help="Port to bind."),
) -> None:
    """Launch the HTTP REST API (for calling TTS from another project)."""
    import os

    import uvicorn

    os.environ.setdefault("INDIAN_TTS_API_HOST", host)
    os.environ.setdefault("INDIAN_TTS_API_PORT", str(port))
    uvicorn.run("indian_tts.api.server:app", host=host, port=port)


def run() -> None:
    """Console-script entry point."""
    # Windows consoles default to cp1252 and crash when printing Devanagari.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    app()


if __name__ == "__main__":
    run()
