"""Vocabulary access: loads data/words.json and picks a secret word.

All file I/O and all randomness live here, which is what keeps game.py pure.
"""

import json
import random
import string
from pathlib import Path

# Anchored to this file, not the current directory, so `python main.py` works
# no matter where it is launched from.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "words.json"

_ALPHABET = frozenset(string.ascii_lowercase)


class WordDataError(Exception):
    """The vocabulary file is missing, malformed, or has no usable word."""


def _clean(word):
    """Lowercase a word, or return '' if it is unusable.

    Words with spaces, hyphens or accents are dropped: the player can only type
    a-z, so such a word could never be completed.
    """
    if not isinstance(word, str):
        return ""
    w = word.strip().lower()
    return w if w and set(w) <= _ALPHABET else ""


def load_words(path=DATA_FILE):
    """Return {topic: [word, ...]} with every word cleaned and deduplicated."""
    try:
        with open(path, encoding="utf-8") as f:  # explicit utf-8: Windows defaults to ANSI
            raw = json.load(f)
    except FileNotFoundError:
        raise WordDataError("khong tim thay file tu vung: %s" % (path,))
    except json.JSONDecodeError as exc:
        raise WordDataError("file tu vung khong hop le: %s" % (exc,))

    if not isinstance(raw, dict):
        raise WordDataError("file tu vung phai la mot doi tuong JSON {chu_de: [tu, ...]}")

    topics = {}
    for topic, words in raw.items():
        cleaned = sorted({w for w in map(_clean, words) if w})
        if cleaned:
            topics[topic] = cleaned
    if not topics:
        raise WordDataError("file tu vung khong co tu nao dung duoc")
    return topics


def all_words(path=DATA_FILE):
    """Every word from every topic, merged into one sorted list."""
    topics = load_words(path)
    return sorted({w for words in topics.values() for w in words})


def random_word(path=DATA_FILE, rng=random):
    """Pick one word at random.

    `rng` is a parameter so tests can pass random.Random(42) for a deterministic
    result without monkeypatching the random module.
    """
    words = all_words(path)
    if not words:
        raise WordDataError("khong co tu nao de chon")
    return rng.choice(words)
