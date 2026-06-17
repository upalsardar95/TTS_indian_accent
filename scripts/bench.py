"""Time Kokoro load vs. generation, and report the device actually used."""

from __future__ import annotations

import time

import torch

from indian_tts.core.presets import get_preset
from indian_tts.engine.kokoro_backend import KokoroBackend

print("cuda available:", torch.cuda.is_available())

t0 = time.time()
be = KokoroBackend()
be.load()
print(f"load: {time.time() - t0:.1f}s")

# What device did Kokoro put the model on?
try:
    dev = next(be._pipeline.model.parameters()).device
    print("kokoro model device:", dev)
except Exception as e:  # noqa: BLE001
    print("device introspection failed:", e)

preset = get_preset("classic-storyteller")
for i, text in enumerate(["Hello world, this is a test.", "नमस्ते बच्चों, कैसे हो आप सब?"], 1):
    t = time.time()
    res = be.synth(text, preset)
    dur = len(res.audio) / res.sample_rate
    el = time.time() - t
    print(f"chunk {i}: gen {el:.1f}s for {dur:.1f}s audio  (RTF={el/max(dur,0.01):.2f})")
