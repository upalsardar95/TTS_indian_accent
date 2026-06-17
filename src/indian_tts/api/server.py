"""FastAPI HTTP server wrapping the Hinglish TTS engine.

Lets a *separate* project (any language) call the TTS feature over HTTP without
taking on the heavy torch/kokoro dependency stack — the model loads once here.

Run it with the ``indian-tts-api`` console script (see pyproject.toml) or::

    python -m indian_tts.api.server

Endpoints:
  POST /synthesize  -> audio bytes (wav/flac/ogg)
  GET  /voices      -> available voice presets
  GET  /backends    -> available TTS backends + the default
  GET  /health      -> liveness probe
"""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..core.audio import encode_audio
from ..core.presets import list_preset_names
from ..core.synthesize import synthesize_text
from ..engine import available_backends, get_backend
from ..engine.registry import DEFAULT_BACKEND

logger = logging.getLogger(__name__)

# soundfile format -> HTTP media type
_MEDIA_TYPES = {
    "wav": "audio/wav",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
}

API_KEY_ENV = "INDIAN_TTS_API_KEY"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard endpoints with an optional API key.

    If the ``INDIAN_TTS_API_KEY`` env var is set (e.g. on a public host), requests
    must send a matching ``X-API-Key`` header. If it is unset, auth is disabled so
    local development keeps working unchanged.
    """
    expected = os.environ.get(API_KEY_ENV)
    if expected and not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


class SynthesizeRequest(BaseModel):
    """Request body mirroring :func:`indian_tts.core.synthesize.synthesize_text`."""

    text: str = Field(..., description="Text to synthesize (Hinglish: Hindi + inline English).")
    voice: str = Field("classic-storyteller", description="Voice preset name (see GET /voices).")
    backend: str = Field(DEFAULT_BACKEND, description="TTS backend (see GET /backends).")
    line_pause: float | None = Field(None, description="Override per-line pause (seconds).")
    stanza_pause: float | None = Field(None, description="Override per-stanza pause (seconds).")
    max_chars: int = Field(200, gt=0, description="Max characters per synthesis chunk.")
    normalize_numbers: bool = Field(True, description="Spell digits out as words before synthesis.")
    format: str = Field("wav", description="Audio container: wav, flac, or ogg.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the default backend on startup so the first request isn't slow."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logger.info("Preloading TTS backend %r ...", DEFAULT_BACKEND)
    try:
        get_backend(DEFAULT_BACKEND)
        logger.info("Backend %r ready.", DEFAULT_BACKEND)
    except Exception:  # noqa: BLE001 — log and keep serving; first call will retry/error
        logger.exception("Backend preload failed; will load on first request.")
    yield


app = FastAPI(
    title="Indian-TTS API",
    description="Offline Hinglish (English + Hindi) storytelling TTS with an Indian accent.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/voices", dependencies=[Depends(require_api_key)])
def voices() -> dict:
    return {"voices": list_preset_names()}


@app.get("/backends", dependencies=[Depends(require_api_key)])
def backends() -> dict:
    return {"backends": available_backends(), "default": DEFAULT_BACKEND}


@app.post(
    "/synthesize",
    dependencies=[Depends(require_api_key)],
    responses={200: {"content": {"audio/wav": {}}, "description": "Synthesized audio."}},
)
def synthesize(req: SynthesizeRequest) -> Response:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="`text` is empty.")

    fmt = req.format.lower()
    if fmt not in _MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {req.format!r}. Use one of: {', '.join(_MEDIA_TYPES)}.",
        )
    if req.voice not in list_preset_names():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice {req.voice!r}. Available: {', '.join(list_preset_names())}.",
        )
    if req.backend not in available_backends():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown backend {req.backend!r}. Available: {', '.join(available_backends())}.",
        )

    # Sync def => FastAPI runs this in a threadpool, so the blocking model call
    # doesn't stall the event loop.
    audio, sample_rate = synthesize_text(
        req.text,
        req.voice,
        backend=req.backend,
        line_pause=req.line_pause,
        stanza_pause=req.stanza_pause,
        max_chars=req.max_chars,
        normalize_numbers=req.normalize_numbers,
    )
    if audio.size == 0:
        raise HTTPException(status_code=400, detail="Text produced no synthesizable content.")

    data = encode_audio(audio, sample_rate, fmt)
    return Response(content=data, media_type=_MEDIA_TYPES[fmt])


def main() -> None:
    """Console-script entry point: launch Uvicorn."""
    import uvicorn

    host = os.environ.get("INDIAN_TTS_API_HOST", "127.0.0.1")
    # Many PaaS hosts (Render/Railway/Fly) inject the port via $PORT.
    port = int(os.environ.get("PORT") or os.environ.get("INDIAN_TTS_API_PORT", "8000"))
    uvicorn.run("indian_tts.api.server:app", host=host, port=port)


if __name__ == "__main__":
    main()
