"""Voice presets: friendly names -> voice id + timing knobs.

A preset bundles everything the orchestrator and backend need to give a story a
consistent character: a Kokoro voice id, a speaking speed, and the silence
inserted between lines / stanzas. (``description`` is a free-text human note kept
for reference; the Kokoro backend reads ``kokoro_voice`` + ``speed``.)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

# Project root = .../TTS_indian_accent ; this file = src/indian_tts/core/presets.py
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG = _PROJECT_ROOT / "config" / "voices.yaml"


@dataclass
class VoicePreset:
    name: str
    description: str
    kokoro_voice: str = "hf_alpha"
    speed: float = 1.0
    line_pause: float = 0.35  # seconds of silence after each line / sentence
    stanza_pause: float = 0.7  # seconds of silence after a blank-line break


def _config_path(path: str | os.PathLike | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("INDIAN_TTS_VOICES")
    return Path(env) if env else _DEFAULT_CONFIG


@lru_cache(maxsize=8)
def load_presets(path: str | None = None) -> dict[str, VoicePreset]:
    cfg = _config_path(path)
    if not cfg.exists():
        raise FileNotFoundError(
            f"Voice config not found at {cfg}. Set INDIAN_TTS_VOICES or pass --voices."
        )
    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    voices = data.get("voices", {})
    presets: dict[str, VoicePreset] = {}
    for name, fields in voices.items():
        presets[name] = VoicePreset(name=name, **fields)
    if not presets:
        raise ValueError(f"No voices defined in {cfg}.")
    return presets


def get_preset(name: str, path: str | None = None) -> VoicePreset:
    presets = load_presets(path)
    if name not in presets:
        raise ValueError(
            f"Unknown voice {name!r}. Available: {', '.join(sorted(presets))}"
        )
    return presets[name]


def list_preset_names(path: str | None = None) -> list[str]:
    return sorted(load_presets(path))
