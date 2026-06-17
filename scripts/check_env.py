"""Quick environment diagnostic: Python, CUDA, backends, Kokoro language support."""

from __future__ import annotations

import inspect
import sys


def main() -> int:
    print("python:", sys.version.split()[0])

    import torch

    print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(),
          "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no-gpu")

    import kokoro
    from kokoro import KPipeline

    print("kokoro:", getattr(kokoro, "__version__", "?"))
    src = inspect.getsource(KPipeline.__init__)
    print("kokoro mentions Hindi 'h':", ("'h'" in src) or ("hindi" in src.lower()))

    import misaki  # noqa: F401

    print("misaki: ok")

    from indian_tts.core.presets import list_preset_names
    from indian_tts.engine.registry import DEFAULT_BACKEND, available_backends

    print("default backend:", DEFAULT_BACKEND)
    print("available backends:", available_backends())
    print("voice presets:", list_preset_names())
    return 0


if __name__ == "__main__":
    sys.exit(main())
