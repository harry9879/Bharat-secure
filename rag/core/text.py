"""One text form for everything that is embedded or shown: Roman Hinglish,
lowercase, no punctuation ."""

import re

from .translit import to_roman

_STAGE = re.compile(r"\([^)]*\)|\[[^\]]*\]|\*[^*]*\*")
_RUPEE = re.compile(r"₹\s*")
_NON_WORD = re.compile(r"[^a-z0-9\s]")
_SPACES = re.compile(r"\s+")


def clean(text: str) -> str:
    text = to_roman(text)
    text = _STAGE.sub(" ", text)
    text = _RUPEE.sub(" rupees ", text)
    text = text.lower().replace("'", "")
    text = _NON_WORD.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def last_words(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[-n:])
