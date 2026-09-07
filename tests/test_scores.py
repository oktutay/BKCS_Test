"""Tests for scoring and the CSV score history (A4).

Every test writes to a temporary file, so running them never touches the real
data/scores.csv.
"""

import tempfile
import unittest
from pathlib import Path

from hangman.game import HangmanGame
from hangman.scores import best_scores, compute_score, load_scores, save_score


def play_win(word="cat", wrong_guesses=""):
    """A finished, won game with however many wrong guesses you ask for."""
    game = HangmanGame(word)
    for letter in wrong_guesses:
        game.guess(letter)
    for letter in set(word):
        game.guess(letter)
    return game


def play_loss(word="cat"):
    game = HangmanGame(word)
    for letter in "bdefgh":
        game.guess(letter)
    return game


class TestComputeScore(unittest.TestCase):
    def test_a_loss_is_worth_nothing(self):
        self.assertEqual(compute_score(play_loss()), 0)

    def test_a_clean_win_pays_for_lives_and_word_length(self):
        # 6 lives * 10 + 3 letters * 5
        self.assertEqual(compute_score(play_win("cat")), 75)

    def test_wrong_guesses_lower_the_score(self):
        self.assertLess(compute_score(play_win("cat", "bd")), compute_score(play_win("cat")))

    def test_a_longer_word_is_worth_more(self):
        self.assertGreater(compute_score(play_win("dolphin")), compute_score(play_win("cat")))

    def test_the_hint_lowers_the_score_because_it_costs_a_life(self):
        import random

        with_hint = HangmanGame("cat")
        with_hint.hint(random.Random(0))
        for letter in "cat":
            with_hint.guess(letter)
        self.assertTrue(with_hint.won)
        self.assertEqual(compute_score(with_hint), compute_score(play_win("cat")) - 10)


class TestScoreFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "scores.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_file_yet_means_no_scores(self):
        self.assertEqual(load_scores(self.path), [])
        self.assertEqual(best_scores(self.path), {})

    def test_a_saved_round_can_be_read_back(self):
        save_score(play_win("cat"), "animal", "easy", self.path)
        rows = load_scores(self.path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["word"], "cat")
        self.assertEqual(rows[0]["result"], "win")
        self.assertEqual(rows[0]["difficulty"], "easy")
        self.assertEqual(rows[0]["score"], "75")

    def test_rounds_are_appended_not_overwritten(self):
        save_score(play_win("cat"), "animal", "easy", self.path)
        save_score(play_loss("cat"), "food", "hard", self.path)
        self.assertEqual(len(load_scores(self.path)), 2)

    def test_all_topics_is_recorded_as_all(self):
        save_score(play_win("cat"), None, "easy", self.path)
        self.assertEqual(load_scores(self.path)[0]["topic"], "all")

    def test_best_scores_keeps_the_highest_per_difficulty(self):
        save_score(play_win("cat", "bd"), "animal", "easy", self.path)  # lower
        save_score(play_win("cat"), "animal", "easy", self.path)        # higher
        save_score(play_loss("cat"), "food", "hard", self.path)
        best = best_scores(self.path)
        self.assertEqual(best["easy"], 75)
        self.assertEqual(best["hard"], 0)
        self.assertNotIn("medium", best)  # never played
