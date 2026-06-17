"""Orchestrator: text -> preprocess -> chunk -> backend -> stitched audio.

This is the single entry point shared by the CLI and the web UI.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from ..engine import get_backend
from ..engine.registry import DEFAULT_BACKEND
from .audio import (
    concat_with_pauses,
    normalize_peak,
    save_audio,
    trim_silence,
)
from .preprocess import chunk_story
from .presets import VoicePreset, get_preset

logger = logging.getLogger(__name__)


def synthesize_text(
    text: str,
    voice: str | VoicePreset = "classic-storyteller",
    *,
    backend: str = DEFAULT_BACKEND,
    line_pause: float | None = None,
    stanza_pause: float | None = None,
    max_chars: int = 200,
    normalize_numbers: bool = True,
    progress=None,
) -> tuple[np.ndarray, int]:
    """Synthesize ``text`` into a single mono float32 track.

    ``progress`` is an optional ``callable(done, total)`` for UI feedback.
    Returns ``(audio, sample_rate)``.
    """
    preset = voice if isinstance(voice, VoicePreset) else get_preset(voice)
    eng = get_backend(backend)

    lp = preset.line_pause if line_pause is None else line_pause
    sp = preset.stanza_pause if stanza_pause is None else stanza_pause

    chunks = chunk_story(
        text,
        line_pause=lp,
        stanza_pause=sp,
        max_chars=max_chars,
        normalize_numbers=normalize_numbers,
    )
    if not chunks:
        return np.zeros(0, dtype=np.float32), eng.sample_rate

    segments: list[tuple[np.ndarray, float]] = []
    total = len(chunks)
    for i, chunk in enumerate(chunks, start=1):
        logger.info("Synthesizing chunk %d/%d: %.40s", i, total, chunk.text)
        result = eng.synth(chunk.text, preset)
        audio = trim_silence(result.audio, result.sample_rate)
        segments.append((audio, chunk.pause_after))
        if progress is not None:
            progress(i, total)

    track = concat_with_pauses(segments, eng.sample_rate)
    track = normalize_peak(track)
    return track, eng.sample_rate


def synthesize_to_file(
    text: str,
    out_path: str | Path,
    voice: str | VoicePreset = "classic-storyteller",
    **kwargs,
) -> Path:
    """Synthesize and write to ``out_path``. Returns the written path."""
    audio, sample_rate = synthesize_text(text, voice, **kwargs)
    return save_audio(audio, sample_rate, out_path)
