# Deploying the Indian-TTS HTTP API

This hosts the `/synthesize` REST API on a server so it's reachable from anywhere —
**including while your own PC is off**. The model runs on **CPU** (no GPU needed); the
container needs roughly **2–3 GB RAM**, which rules out the smallest (512 MB) free tiers.

A `Dockerfile` is included and works on any host that can build/run a container. The
first request downloads the ~330 MB Kokoro model from Hugging Face, so the very first
call after a cold start is slow (~20–40 s); subsequent calls are fast.

## API key

Set the env var **`INDIAN_TTS_API_KEY`** on the host to require an `X-API-Key` header on
every `/synthesize`, `/voices`, and `/backends` request (`/health` stays open for health
checks). If the var is unset, the API is open. Generate a strong value, e.g.
`python -c "import secrets; print(secrets.token_urlsafe(24))"`.

Callers then send the header:

```bash
curl -X POST https://YOUR-HOST/synthesize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"text":"नमस्ते! Hello.","voice":"bedtime"}' --output out.wav
```

## Option A — Hugging Face Spaces (free, recommended)

Free CPU Spaces give 2 vCPU + 16 GB RAM and run while your PC is off (they sleep after
~48 h idle and auto-wake on the next request).

1. Create a new **Space** → SDK **Docker** → Blank.
2. Push this repo to the Space's git remote (or connect it to your GitHub repo).
3. The Space README needs Docker metadata at the very top. Either add this front-matter
   block to the top of `README.md`, or set it in the Space's own README:
   ```yaml
   ---
   title: Indian TTS API
   sdk: docker
   app_port: 7860
   ---
   ```
4. In **Settings → Variables and secrets**, add secret `INDIAN_TTS_API_KEY`.
5. Your endpoint is `https://<user>-<space>.hf.space/synthesize`.

## Option B — Render / Railway (managed PaaS)

1. New **Web Service** → **Deploy from a Git repo** → pick this repo.
2. Environment: **Docker** (it auto-detects the `Dockerfile`).
3. These hosts inject `$PORT`; the server already honors it (`main()` reads `$PORT`).
4. Add env var `INDIAN_TTS_API_KEY`.
5. Pick an instance with **≥ 2 GB RAM** (free 512 MB tiers won't fit torch).

## Option C — Any VPS with Docker (always-on, no sleep)

```bash
docker build -t indian-tts .
docker run -d --restart unless-stopped \
  -e INDIAN_TTS_API_KEY=YOUR_KEY \
  -p 8000:7860 indian-tts
# now reachable at http://SERVER_IP:8000  (put a reverse proxy + HTTPS in front for production)
```

Oracle Cloud's Always-Free ARM instances (up to 24 GB RAM) are a good zero-cost,
always-on option here.
