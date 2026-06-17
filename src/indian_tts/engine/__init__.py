"""TTS backend implementations behind a common interface."""

from .base import SynthesisResult, TTSBackend
from .registry import available_backends, get_backend

__all__ = ["SynthesisResult", "TTSBackend", "get_backend", "available_backends"]
