"""Common interface every TTS backend implements.

The rest of the app (CLI, web UI, synthesis orchestrator) talks only to this
interface, never to a concrete model. That is what lets us add another engine
later (e.g. XTTS-v2) without touching anything above the engine layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from ..core.presets import VoicePreset


@dataclass
class SynthesisResult:
    """A single synthesized chunk: mono float32 audio in [-1, 1] plus its rate."""

    audio: np.ndarray
    sample_rate: int


class TTSBackend(ABC):
    """Base class for all speech backends."""

    #: Stable identifier used by the registry / CLI ``--backend`` flag.
    name: str = "base"

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory. Called once before the first synth."""

    @abstractmethod
    def synth(self, text: str, preset: VoicePreset) -> SynthesisResult:
        """Synthesize a *single* chunk of text using the given voice preset.

        Implementations read whatever they need from ``preset`` (Kokoro uses
        ``kokoro_voice`` + ``speed``).
        """

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Native output sample rate of the loaded model, in Hz."""
