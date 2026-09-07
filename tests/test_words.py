"""Tests for the vocabulary file and its loader.

These assert F1 mechanically: the word list is external, and it is big enough.
"""

import random
import unittest

from hangman.game import DEFAULT_LIVES, HangmanGame
from hangman.words import (
    DIFFICULTIES,
    MODES,
    WordDataError,
    all_words,
    load_words,
    random_word,
    topics,
    words_for,
)


class TestWordData(unittest.TestCase):
    def test_word_file_has_at_least_30_words(self):
        self.assertGreaterEqual(len(all_words()), 30)

    def test_topics_are_present_and_non_empty(self):
        by_topic = load_words()
        self.assertIn("animal", by_topic)
        self.assertIn("food", by_topic)
        for name, words in by_topic.items():
            with self.subTest(topic=name):
                self.assertTrue(words)
        self.assertEqual(topics(), sorted(by_topic))

    def test_every_word_is_lowercase_ascii_letters(self):
        for word in all_words():
            with self.subTest(word=word):
                self.assertTrue(word.isalpha())
                self.assertTrue(word.islower())
                self.assertTrue(word.isascii())

    def test_every_word_builds_a_playable_game(self):
        # Guards against a word that could never be completed.
        for word in all_words():
            with self.subTest(word=word):
                game = HangmanGame(word)
                for letter in set(word):
                    game.guess(letter)
                self.assertTrue(game.won)

    def test_random_word_is_deterministic_with_a_seeded_rng(self):
        first = random_word(rng=random.Random(42))
        second = random_word(rng=random.Random(42))
        self.assertEqual(first, second)
        self.assertIn(first, all_words())


class TestDifficultyAndTopic(unittest.TestCase):
    """A1 (difficulty) and A3 (topics), both handled entirely in the data layer."""

    def test_difficulty_filter_respects_length_bounds(self):
        for key, level in DIFFICULTIES.items():
            with self.subTest(difficulty=key):
                for word in words_for(difficulty=key):
                    self.assertGreaterEqual(len(word), level.min_length)
                    self.assertLessEqual(len(word), level.max_length)

    def test_every_topic_and_difficulty_bucket_has_words(self):
        # Guards against random_word() raising because a bucket came out empty.
        for topic in topics():
            for key in DIFFICULTIES:
                with self.subTest(topic=topic, difficulty=key):
                    self.assertTrue(words_for(topic=topic, difficulty=key))

    def test_topic_filter_returns_only_that_topic(self):
        by_topic = load_words()
        for topic in topics():
            with self.subTest(topic=topic):
                self.assertEqual(words_for(topic=topic), by_topic[topic])

    def test_modes_map_to_real_difficulties(self):
        self.assertEqual(sorted(MODES), [1, 2, 3])
        for mode, key in MODES.items():
            with self.subTest(mode=mode):
                self.assertIn(key, DIFFICULTIES)

    def test_difficulty_changes_word_length_only_not_lives(self):
        # The rules allow 6 wrong guesses in every mode, so difficulty carries
        # no lives value and every mode plays with the same DEFAULT_LIVES.
        self.assertEqual(DEFAULT_LIVES, 6)
        for key in DIFFICULTIES:
            with self.subTest(difficulty=key):
                self.assertFalse(hasattr(DIFFICULTIES[key], "lives"))
                word = random_word(difficulty=key, rng=random.Random(0))
                self.assertEqual(HangmanGame(word).lives, 6)

    def test_difficulty_buckets_do_not_overlap(self):
        levels = sorted(DIFFICULTIES.values(), key=lambda d: d.min_length)
        for lower, upper in zip(levels, levels[1:]):
            with self.subTest(pair=(lower.key, upper.key)):
                self.assertLess(lower.max_length, upper.min_length)

    def test_random_word_respects_topic_and_difficulty(self):
        word = random_word(topic="food", difficulty="hard", rng=random.Random(0))
        self.assertIn(word, load_words()["food"])
        self.assertGreaterEqual(len(word), DIFFICULTIES["hard"].min_length)

    def test_unknown_topic_or_difficulty_raises(self):
        with self.assertRaises(WordDataError):
            words_for(topic="khong-ton-tai")
        with self.assertRaises(WordDataError):
            words_for(difficulty="impossible")


if __name__ == "__main__":
    unittest.main()
