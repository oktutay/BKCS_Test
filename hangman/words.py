"""Vocabulary access: loads data/words.json and picks a secret word.

All file I/O and all randomness live here, which is what keeps game.py pure.
"""

import json
import random
import string
from collections import namedtuple
from pathlib import Path

# Anchored to this file, not the current directory, so `python main.py` works
# no matter where it is launched from.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "words.json"

_ALPHABET = frozenset(string.ascii_lowercase)

# Difficulty is a word-SELECTION policy, not a game rule, which is why it lives
# here and not in game.py. It is derived from len(word), so the data file needs
# no difficulty tags: adding a word puts it in the right bucket automatically.
#
# Difficulty changes the word length ONLY. Every mode keeps the 6 wrong guesses
# the rules allow, so the number of lives is not part of this table.
Difficulty = namedtuple("Difficulty", "key label min_length max_length")

DIFFICULTIES = {
    "easy": Difficulty("easy", "Dễ", 3, 5),
    "medium": Difficulty("medium", "Trung bình", 6, 8),
    "hard": Difficulty("hard", "Khó", 9, 99),
}

# The 1/2/3 the player types at the menu.
MODES = {1: "easy", 2: "medium", 3: "hard"}


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


def topics(path=DATA_FILE):
    """The topic names available in the data file, e.g. ['animal', 'food']."""
    return sorted(load_words(path))


def words_for(topic=None, difficulty=None, path=DATA_FILE):
    """Words matching a topic and/or a difficulty.

    topic=None means every topic; difficulty=None means any length.
    """
    if topic is None:
        pool = all_words(path)
    else:
        loaded = load_words(path)
        if topic not in loaded:
            raise WordDataError("khong co chu de %r" % (topic,))
        pool = loaded[topic]

    if difficulty is not None:
        if difficulty not in DIFFICULTIES:
            raise WordDataError("khong co do kho %r" % (difficulty,))
        level = DIFFICULTIES[difficulty]
        pool = [w for w in pool if level.min_length <= len(w) <= level.max_length]
    return pool


def random_word(topic=None, difficulty=None, path=DATA_FILE, rng=random):
    """Pick one word at random from the chosen topic and difficulty.

    `rng` is a parameter so tests can pass random.Random(42) for a deterministic
    result without monkeypatching the random module.
    """
    words = words_for(topic, difficulty, path)
    if not words:
        # Raise instead of letting random.choice([]) throw an opaque IndexError.
        raise WordDataError(
            "khong co tu nao cho chu de=%r do kho=%r" % (topic, difficulty)
        )
    return rng.choice(words)
