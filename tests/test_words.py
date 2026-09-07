"""Tests for the vocabulary file and its loader.

These assert F1 mechanically: the word list is external, and it is big enough.
"""

import random
import unittest

from hangman.game import HangmanGame
from hangman.words import all_words, load_words, random_word


class TestWordData(unittest.TestCase):
    def test_word_file_has_at_least_30_words(self):
        self.assertGreaterEqual(len(all_words()), 30)

    def test_topics_are_present_and_non_empty(self):
        topics = load_words()
        self.assertIn("animal", topics)
        self.assertIn("food", topics)
        for name, words in topics.items():
            with self.subTest(topic=name):
                self.assertTrue(words)

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


if __name__ == "__main__":
    unittest.main()
