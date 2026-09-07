"""Reads data/words.json and picks a secret word.

All file reading and all randomness happen here, which is what keeps game.py
free of both.
"""

import json
import random
import string
from pathlib import Path

# Built from this file's location, not the current folder, so `python main.py`
# works no matter which directory you run it from.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "words.json"

LETTERS = set(string.ascii_lowercase)

# Difficulty is about WHICH WORD to pick, not about the rules, so it lives here
# and not in game.py. It is worked out from the length of the word, so
# words.json needs no difficulty labels: a new word lands in the right group by
# itself. Only the length changes -- every difficulty keeps the same 6 lives.
DIFFICULTIES = {
    "easy": {"label": "Easy", "min_length": 3, "max_length": 5},
    "medium": {"label": "Medium", "min_length": 6, "max_length": 8},
    "hard": {"label": "Hard", "min_length": 9, "max_length": 99},
}

MODES = {1: "easy", 2: "medium", 3: "hard"}  # what the player types in the menu


class WordDataError(Exception):
    """The word file is missing, broken, or has no word we can use."""


def load_words(path=DATA_FILE):
    """Read the file and return {topic: [word, ...]}, cleaned up.

    Words are lowercased, and anything that is not plain a-z is dropped. A word
    with a space or an accent would be impossible to guess, so it must not
    reach the game.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise WordDataError(f"word file not found: {path}")
    except json.JSONDecodeError as exc:
        raise WordDataError(f"word file is not valid JSON: {exc}")

    topics = {}
    for topic, words in raw.items():
        clean = sorted({w.strip().lower() for w in words})
        clean = [w for w in clean if w and set(w) <= LETTERS]
        if clean:
            topics[topic] = clean

    if not topics:
        raise WordDataError("word file contains no usable word")
    return topics


def all_words(path=DATA_FILE):
    """Every word from every topic, in one list."""
    topics = load_words(path)
    return sorted({w for words in topics.values() for w in words})


def topic_names(path=DATA_FILE):
    """The topics in the file, e.g. ['animal', 'food']."""
    return sorted(load_words(path))


def words_for(topic=None, difficulty=None, path=DATA_FILE):
    """The words for a topic and/or a difficulty.

    topic=None means all topics; difficulty=None means any length.
    """
    if topic is None:
        words = all_words(path)
    else:
        topics = load_words(path)
        if topic not in topics:
            raise WordDataError(f"unknown topic: {topic!r}")
        words = topics[topic]

    if difficulty is not None:
        if difficulty not in DIFFICULTIES:
            raise WordDataError(f"unknown difficulty: {difficulty!r}")
        level = DIFFICULTIES[difficulty]
        words = [w for w in words if level["min_length"] <= len(w) <= level["max_length"]]

    return words


def random_word(topic=None, difficulty=None, path=DATA_FILE, rng=random):
    """Pick one word at random.

    `rng` is an argument so a test can pass random.Random(42) and always get
    the same word back.
    """
    words = words_for(topic, difficulty, path)
    if not words:
        # Better than letting random.choice([]) raise a confusing IndexError.
        raise WordDataError(f"no word for topic={topic!r} difficulty={difficulty!r}")
    return rng.choice(words)
