"""Hinglish-aware text preparation.

Two jobs:
  1. Clean/normalize text (whitespace, quotes, common abbreviations, numbers).
  2. Chunk a story or rhyme into bite-sized pieces with a pause tagged after each.

Chunking is what keeps rhymes rhythmic: we break on stanzas (blank lines) and
lines, and only fall back to sentence/clause splits when a line is too long for
the model to handle comfortably (which also keeps GPU memory low).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from num2words import num2words

# Devanagari danda (।) and double danda (॥) act as sentence terminators in Hindi.
_SENTENCE_END = re.compile(r"(?<=[.!?।॥])\s+")
_CLAUSE_SPLIT = re.compile(r"(?<=[,;:।])\s+")
_INTEGER = re.compile(r"\b\d{1,9}\b")

_ABBREVIATIONS = {
    "Dr.": "Doctor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Miss",
    "&": " and ",
    "etc.": "etcetera",
}


@dataclass
class Chunk:
    text: str
    pause_after: float  # seconds of silence to append after this chunk


def _has_devanagari(text: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("—", " - ").replace("–", " - ")
    for abbr, full in _ABBREVIATIONS.items():
        text = text.replace(abbr, full)
    # Collapse runs of spaces/tabs but preserve newlines (they drive chunking).
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def expand_numbers(text: str) -> str:
    """Spell out standalone integers. Uses Hindi words for Devanagari lines."""
    lang = "hi" if _has_devanagari(text) else "en"

    def _repl(match: re.Match) -> str:
        try:
            return num2words(int(match.group()), lang=lang)
        except (NotImplementedError, OverflowError):
            return match.group()

    return _INTEGER.sub(_repl, text)


def _split_long(piece: str, max_chars: int) -> list[str]:
    """Break an over-long piece on clauses, then on word boundaries if needed."""
    if len(piece) <= max_chars:
        return [piece]
    parts: list[str] = []
    buf = ""
    for clause in _CLAUSE_SPLIT.split(piece):
        candidate = f"{buf} {clause}".strip()
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                parts.append(buf)
            buf = clause
    if buf:
        parts.append(buf)
    # Hard wrap any clause still too long.
    wrapped: list[str] = []
    for part in parts:
        while len(part) > max_chars:
            cut = part.rfind(" ", 0, max_chars) or max_chars
            cut = cut if cut > 0 else max_chars
            wrapped.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            wrapped.append(part)
    return wrapped


def chunk_story(
    text: str,
    *,
    line_pause: float,
    stanza_pause: float,
    max_chars: int = 200,
    normalize_numbers: bool = True,
) -> list[Chunk]:
    """Split cleaned text into chunks, each tagged with the pause that follows it."""
    text = clean_text(text)
    if normalize_numbers:
        text = expand_numbers(text)

    chunks: list[Chunk] = []
    stanzas = re.split(r"\n\s*\n", text)
    for stanza in stanzas:
        lines = [ln.strip() for ln in stanza.splitlines() if ln.strip()]
        if not lines:
            continue
        for line in lines:
            sentences = [s for s in _SENTENCE_END.split(line) if s.strip()] or [line]
            for sentence in sentences:
                for piece in _split_long(sentence.strip(), max_chars):
                    if piece:
                        chunks.append(Chunk(text=piece, pause_after=line_pause))
        # Longer breath after a stanza.
        if chunks:
            chunks[-1] = Chunk(text=chunks[-1].text, pause_after=stanza_pause)

    return chunks
