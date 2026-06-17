"""Audio post-processing: trim, stitch with pauses, normalize, save."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf


def trim_silence(audio: np.ndarray, sample_rate: int, threshold_db: float = -45.0,
                 pad_ms: float = 30.0) -> np.ndarray:
    """Trim leading/trailing near-silence so chunk joins sound tight."""
    if audio.size == 0:
        return audio
    amp = np.abs(audio)
    ref = float(amp.max()) or 1.0
    threshold = ref * (10.0 ** (threshold_db / 20.0))
    above = np.where(amp > threshold)[0]
    if above.size == 0:
        return audio
    pad = int(sample_rate * pad_ms / 1000.0)
    start = max(0, above[0] - pad)
    end = min(len(audio), above[-1] + pad)
    return audio[start:end]


def _silence(seconds: float, sample_rate: int) -> np.ndarray:
    return np.zeros(int(max(0.0, seconds) * sample_rate), dtype=np.float32)


def concat_with_pauses(segments: list[tuple[np.ndarray, float]],
                       sample_rate: int) -> np.ndarray:
    """Join (audio, pause_after_seconds) segments into one track."""
    if not segments:
        return np.zeros(0, dtype=np.float32)
    parts: list[np.ndarray] = []
    for audio, pause in segments:
        parts.append(np.asarray(audio, dtype=np.float32))
        if pause > 0:
            parts.append(_silence(pause, sample_rate))
    return np.concatenate(parts)


def normalize_peak(audio: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """Scale so the loudest sample sits at ``peak`` (avoids clipping on save)."""
    if audio.size == 0:
        return audio
    m = float(np.abs(audio).max())
    if m == 0:
        return audio
    return (audio / m * peak).astype(np.float32)


def save_audio(audio: np.ndarray, sample_rate: int, path: str | Path) -> Path:
    """Write a mono float track. Format inferred from extension (wav/flac/ogg)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".mp3":
        raise ValueError(
            "MP3 output is not supported by the bundled writer. Use .wav/.flac/.ogg "
            "(or convert afterwards with ffmpeg)."
        )
    sf.write(str(path), audio, sample_rate)
    return path


def encode_audio(audio: np.ndarray, sample_rate: int, fmt: str = "WAV") -> bytes:
    """Encode a mono float track to in-memory bytes (WAV/FLAC/OGG).

    Mirrors :func:`save_audio` but never touches disk — used by the HTTP API to
    stream audio straight back in the response body.
    """
    fmt = fmt.upper()
    if fmt == "MP3":
        raise ValueError(
            "MP3 output is not supported by the bundled writer. Use wav/flac/ogg."
        )
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format=fmt)
    return buf.getvalue()
