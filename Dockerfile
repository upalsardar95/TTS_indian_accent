# CPU container for the Indian-TTS HTTP API. Generic across hosts (Hugging Face
# Spaces, Render, Railway, Fly, a plain VPS). No GPU required.
FROM python:3.11-slim

# System libs: libsndfile1 for soundfile I/O, espeak-ng for Kokoro's Hindi g2p.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the CPU build of torch first, then the rest of the deps.
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir torch==2.4.1 torchaudio==2.4.1 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-cpu.txt

# Install the package itself (editable so the src layout + config/ resolve).
COPY . .
RUN pip install --no-cache-dir -e .

# 7860 is the Hugging Face Spaces default port. HF_HOME keeps the ~330 MB Kokoro
# model cache inside the container's working dir. INDIAN_TTS_API_KEY should be set
# as a host secret to require the X-API-Key header.
ENV INDIAN_TTS_API_HOST=0.0.0.0 \
    INDIAN_TTS_API_PORT=7860 \
    HF_HOME=/app/hf_cache

EXPOSE 7860

CMD ["python", "-m", "indian_tts.api.server"]
