"""Backend factory + process-wide cache.

Models are expensive to load, so each backend is instantiated and loaded once,
then reused for every subsequent request (CLI run, web request, etc.).
"""

from __future__ import annotations

from .base import TTSBackend

_BUILDERS = {
    "kokoro": lambda **kw: _build_kokoro(**kw),
}

_INSTANCES: dict[str, TTSBackend] = {}

# Kokoro-82M is the only backend: non-gated, Apache-2.0, fast, and small enough
# for any GPU — safe for commercial use with no gated dependencies.
DEFAULT_BACKEND = "kokoro"


def _build_kokoro(**kw) -> TTSBackend:
    from .kokoro_backend import KokoroBackend

    return KokoroBackend(**kw)


def available_backends() -> list[str]:
    return list(_BUILDERS)


def get_backend(name: str = DEFAULT_BACKEND, **kwargs) -> TTSBackend:
    """Return a loaded backend instance, building+loading it on first use."""
    if name not in _BUILDERS:
        raise ValueError(
            f"Unknown backend {name!r}. Available: {', '.join(_BUILDERS)}"
        )
    if name not in _INSTANCES:
        backend = _BUILDERS[name](**kwargs)
        backend.load()
        _INSTANCES[name] = backend
    return _INSTANCES[name]
