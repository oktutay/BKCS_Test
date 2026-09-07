"""Scoring, and the score history kept in data/scores.csv.

compute_score() is a plain function of a finished game, so it is easy to test.
Everything else here is the CSV file: append one row per round, read them back.
"""

import csv
from datetime import datetime
from pathlib import Path

SCORE_FILE = Path(__file__).resolve().parent.parent / "data" / "scores.csv"

COLUMNS = ["played_at", "topic", "difficulty", "word", "result", "lives_left", "score"]


def compute_score(game):
    """Points for a finished round. A loss is worth nothing.

    A win pays for the lives you kept and for how long the word was. Using the
    hint needs no separate penalty: it already cost a life, so it already shows
    up here.
    """
    if not game.won:
        return 0
    return game.lives * 10 + len(game.secret_word) * 5


def save_score(game, topic, difficulty, path=SCORE_FILE):
    """Append one finished round to the CSV, writing the header if it is new."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()

    row = {
        "played_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic or "all",
        "difficulty": difficulty,
        "word": game.secret_word,
        "result": "win" if game.won else "loss",
        "lives_left": game.lives,
        "score": compute_score(game),
    }

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row


def load_scores(path=SCORE_FILE):
    """Every row from the CSV, oldest first. An empty list if there is no file yet."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def best_scores(path=SCORE_FILE):
    """The highest score for each difficulty: {"easy": 95, "medium": 0, ...}.

    A difficulty never played yet is missing from the result.
    """
    best = {}
    for row in load_scores(path):
        score = int(row["score"])
        key = row["difficulty"]
        if score > best.get(key, -1):
            best[key] = score
    return best
