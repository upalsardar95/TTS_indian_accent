"""Kokoro-82M backend (the only backend).

A tiny (~82M) Apache-2.0 model that runs in real time even on modest hardware
and is not gated on Hugging Face. Uses the Hindi pipeline (``lang_code='h'``),
whose phonemizer handles English words inside Hindi text (code-switching) with
an Indian-accented voice — a low-VRAM default that's cleared for commercial use.
"""

from __future__ import annotations

import logging

import numpy as np

from ..core.presets import VoicePreset
from .base import SynthesisResult, TTSBackend

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 24000
_REPO_ID = "hexgrad/Kokoro-82M"


class KokoroBackend(TTSBackend):
    name = "kokoro"

    def __init__(self, lang_code: str = "h"):
        # "h" = Hindi voices; "a" = American English, "b" = British English.
        self._lang_code = lang_code
        self._pipeline = None

    def load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from kokoro import KPipeline
        except ImportError as err:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Kokoro backend requires the optional 'kokoro' package. "
                "Install it with: pip install kokoro"
            ) from err
        logger.info("Loading Kokoro-82M (lang_code=%s)...", self._lang_code)
        self._pipeline = KPipeline(lang_code=self._lang_code, repo_id=_REPO_ID)
        self._warmup()

    def _warmup(self) -> None:
        """Run one throwaway synth so CUDA context init / kernel JIT happens now.

        The very first GPU call pays a large one-time cost (lazy CUDA init,
        cuDNN autotuning, kernel compilation) — ~tens of seconds on older
        drivers. Paying it here, during load, means the user's first *real*
        generation is fast instead of stalling for nearly a minute.
        """
        try:
            for _ in self._pipeline("नमस्ते, hello.", voice="hf_alpha", speed=1.0):
                pass
            logger.info("Kokoro warm-up complete; generation is now hot.")
        except Exception as err:  # noqa: BLE001 - warm-up must never break load
            logger.warning("Kokoro warm-up skipped (%s).", err)

    @property
    def sample_rate(self) -> int:
        return _SAMPLE_RATE

    def synth(self, text: str, preset: VoicePreset) -> SynthesisResult:
        if self._pipeline is None:
            self.load()
        import torch

        chunks = []
        with torch.inference_mode():
            for item in self._pipeline(text, voice=preset.kokoro_voice, speed=preset.speed):
                chunks.append(_extract_audio(item))
        chunks = [c for c in chunks if c is not None and c.size]
        audio = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
        return SynthesisResult(audio=audio, sample_rate=_SAMPLE_RATE)


def _extract_audio(item) -> np.ndarray | None:
    """Pull the audio array out of a Kokoro yield (Result object or tuple)."""
    audio = getattr(item, "audio", None)
    if audio is None and isinstance(item, (tuple, list)) and item:
        audio = item[-1]
    if audio is None:
        return None
    if hasattr(audio, "detach"):  # torch tensor
        audio = audio.detach().cpu().numpy()
    return np.asarray(audio, dtype=np.float32)
