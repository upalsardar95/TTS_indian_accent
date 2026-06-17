"""Image -> story text (OCR) -> Hindi explanation (local LLM) -> narration.

Pipeline that runs *before* TTS when the source is a picture of a story:

  1. **OCR** with Tesseract (via ``pytesseract``) pulls the story text out of the
     image.
  2. **Analysis** with a local **Ollama** model produces a sentence-by-sentence
     Hindi explanation plus the moral.
  3. **Narration assembly** stitches the original story and the Hindi explanation
     into one speech-ready string (markdown stripped) for the Kokoro backend.

Everything external (the Tesseract binary, the Ollama server + model) is imported
/ called lazily and fails with an actionable message, so the rest of the app keeps
working when these aren't installed.

Tesseract path: if the ``tesseract`` binary isn't on PATH, set the ``TESSERACT_CMD``
environment variable to its full path (e.g. ``C:\\Program Files\\Tesseract-OCR\\tesseract.exe``).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: Default Ollama model — "qwen2.5" (7B) is Apache-2.0, so it's safe for a
#: commercial product out of the box. Swap via the ``model`` argument / --model
#: flag. Note: "llama3" is under Meta's restrictive Llama 3 Community License
#: (usage limits + "Built with Llama" attribution), so it is opt-in only.
DEFAULT_MODEL = "qwen2.5"

_ANALYSIS_PROMPT = """\
Here is a story extracted from an image:
"{story}"

Please provide the following in simple Hindi:
1. A bulleted list explaining the story sentence by sentence (or logical parts).
2. A clear heading for the Moral of the story (इस कहानी की सीख), followed by the moral in Hindi.

Respond ONLY in Hindi with the requested format."""


@dataclass
class StoryResult:
    """Everything the image pipeline produced."""

    lines: list[str]   # cleaned OCR story lines, one per detected line
    story: str         # the lines re-joined with newlines (narratable as-is)
    analysis: str      # raw Hindi explanation + moral from the LLM ("" if skipped)
    narration: str     # speech-ready text fed to the TTS engine


#: Standard places the Tesseract binary lands on Windows when it isn't on PATH.
_TESSERACT_FALLBACKS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _configure_tesseract() -> None:
    """Make sure pytesseract can find the Tesseract binary.

    Resolution order: ``TESSERACT_CMD`` env var → binary already on PATH →
    the standard Windows install paths. This means the image feature works
    out of the box after a normal Tesseract install, with no env var needed.
    """
    import shutil

    import pytesseract

    cmd = os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        return
    if shutil.which("tesseract"):
        return  # on PATH; pytesseract's default will find it
    for path in _TESSERACT_FALLBACKS:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info("Using Tesseract at %s", path)
            return


def extract_text(image_path: str | Path) -> tuple[str, list[str]]:
    """OCR ``image_path`` and return ``(joined_story, cleaned_lines)``."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as err:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Image OCR needs the 'pytesseract' and 'pillow' packages. "
            "Install them with: pip install pytesseract pillow"
        ) from err

    _configure_tesseract()
    try:
        with Image.open(image_path) as img:
            raw_text = pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError as err:
        raise RuntimeError(
            "Tesseract OCR engine not found. Install it "
            "(https://github.com/UB-Mannheim/tesseract/wiki on Windows) and either "
            "add it to PATH or set TESSERACT_CMD to the tesseract.exe path."
        ) from err
    except Exception as err:  # noqa: BLE001 - surface a readable image error
        raise RuntimeError(f"Could not read image {image_path!r}: {err}") from err

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    return "\n".join(lines), lines


def analyze_story(story: str, model: str = DEFAULT_MODEL) -> str:
    """Ask a local Ollama model for a Hindi explanation + moral of ``story``."""
    try:
        import ollama
    except ImportError as err:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "The LLM analysis step needs the 'ollama' package. "
            "Install it with: pip install ollama (and run the Ollama app)."
        ) from err

    prompt = _ANALYSIS_PROMPT.format(story=story.replace("\n", " "))
    logger.info("Analyzing story with Ollama model %r...", model)
    try:
        # keep_alive=0 unloads the LLM from the GPU the moment it finishes, so the
        # TTS step that follows has VRAM to work with. Essential on small GPUs
        # (e.g. 4 GB) where a 7B model + Kokoro can't be resident at once.
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            keep_alive=0,
        )
    except Exception as err:  # noqa: BLE001 - server/model issues -> clear message
        raise RuntimeError(
            f"Ollama analysis failed ({err}). Is the Ollama app running, and is "
            f"the model pulled?  ->  ollama pull {model}"
        ) from err
    return response["message"]["content"].strip()


_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_HEADING = re.compile(r"^\s*#{1,6}\s*")
_EMPHASIS = re.compile(r"[*_`]{1,3}")


def clean_for_speech(text: str) -> str:
    """Strip markdown so the TTS doesn't read bullets/asterisks/hashes aloud."""
    out = []
    for line in text.splitlines():
        line = _HEADING.sub("", line)
        line = _BULLET.sub("", line)
        line = _EMPHASIS.sub("", line)
        out.append(line.rstrip())
    # Collapse 3+ blank lines down to the single blank line the chunker wants.
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def build_narration(story: str, analysis: str) -> str:
    """Combine the original story and the Hindi analysis into speech-ready text.

    A blank line between them becomes a stanza-length pause in the chunker.
    """
    story_part = clean_for_speech(story)
    if not analysis:
        return story_part
    return f"{story_part}\n\n{clean_for_speech(analysis)}".strip()


def process_image(
    image_path: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    analyze: bool = True,
) -> StoryResult:
    """Run the full image -> narratable text pipeline.

    Set ``analyze=False`` to skip the Ollama step and narrate only the OCR'd story.
    Raises ``ValueError`` if no text is found, ``RuntimeError`` for missing tools.
    """
    story, lines = extract_text(image_path)
    if not story.strip():
        raise ValueError("No text could be found in the image.")

    analysis = analyze_story(story, model=model) if analyze else ""
    narration = build_narration(story, analysis)
    return StoryResult(lines=lines, story=story, analysis=analysis, narration=narration)
