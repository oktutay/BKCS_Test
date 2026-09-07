"""Unit tests for the game rules.

Every test builds HangmanGame with a fixed word, so there is no file access and
no stdout capture anywhere in this file. The only randomness is the seeded
Random(0) handed to hint(), which the core takes as an argument precisely so
the tests can pin it down. That is all possible because the logic is fully
separated from the interface.
"""

import random
import unittest

from hangman.game import GameState, GuessResult, HangmanGame

WORD = "python"  # 6 letters, all distinct


class TestHangmanGame(unittest.TestCase):
    def setUp(self):
        self.game = HangmanGame(WORD)

    # --- the five cases named in the assignment -----------------------

    def test_correct_guess_reveals_letter_and_keeps_lives(self):
        result = self.game.guess("p")
        self.assertIs(result, GuessResult.CORRECT)
        self.assertEqual(self.game.lives, 6)  # a correct guess is free
        self.assertEqual(self.game.masked_word, "p_____")
        self.assertIs(self.game.state, GameState.PLAYING)

    def test_wrong_guess_costs_exactly_one_life(self):
        result = self.game.guess("z")
        self.assertIs(result, GuessResult.WRONG)
        self.assertEqual(self.game.lives, 5)  # exactly one, not one per position
        self.assertEqual(self.game.wrong_letters, ["z"])
        self.assertEqual(self.game.masked_word, "______")

    def test_duplicate_guess_costs_nothing(self):
        self.game.guess("p")
        self.assertIs(self.game.guess("p"), GuessResult.ALREADY_GUESSED)
        self.assertEqual(self.game.lives, 6)

        self.game.guess("z")
        self.assertIs(self.game.guess("z"), GuessResult.ALREADY_GUESSED)
        self.assertEqual(self.game.lives, 5)  # the repeat did not cost a second life
        self.assertEqual(self.game.wrong_letters, ["z"])

    def test_win_when_all_letters_revealed(self):
        for letter in set(WORD):
            self.game.guess(letter)
        self.assertIs(self.game.state, GameState.WON)
        self.assertTrue(self.game.won)
        self.assertTrue(self.game.is_over)
        self.assertEqual(self.game.remaining, 0)
        self.assertEqual(self.game.masked_word, WORD)

    def test_lose_after_six_wrong_guesses(self):
        for letter in "qwrszx":
            self.game.guess(letter)
        self.assertIs(self.game.state, GameState.LOST)
        self.assertFalse(self.game.won)
        self.assertEqual(self.game.lives, 0)
        self.assertIn("_", self.game.masked_word)
        self.assertEqual(self.game.secret_word, WORD)  # still readable for the reveal

    # --- additional coverage of the F requirements --------------------

    def test_invalid_input_never_costs_a_life(self):
        for bad in ("", " ", "  ", "ab", "1", "!", "\n", "é", None, 5):
            with self.subTest(value=bad):
                game = HangmanGame(WORD)
                self.assertIs(game.guess(bad), GuessResult.INVALID)
                self.assertEqual(game.lives, 6)
                self.assertEqual(game.guessed_letters, set())
                self.assertIs(game.state, GameState.PLAYING)

    def test_guessing_is_case_insensitive(self):
        self.assertIs(self.game.guess("P"), GuessResult.CORRECT)
        self.assertIs(self.game.guess("p"), GuessResult.ALREADY_GUESSED)
        self.assertEqual(self.game.lives, 6)

    def test_surrounding_spaces_are_ignored(self):
        self.assertIs(self.game.guess(" p "), GuessResult.CORRECT)

    def test_repeated_letters_are_all_revealed(self):
        game = HangmanGame("letter")
        self.assertIs(game.guess("t"), GuessResult.CORRECT)
        self.assertEqual(game.masked_word, "__tt__")
        self.assertEqual(game.remaining, 3)  # l, e, r still hidden

    def test_available_letters_exclude_correct_and_wrong_guesses(self):
        self.game.guess("p")  # correct
        self.game.guess("z")  # wrong
        self.assertNotIn("p", self.game.available_letters)
        self.assertNotIn("z", self.game.available_letters)
        self.assertEqual(len(self.game.available_letters), 24)

    def test_win_on_the_last_life(self):
        for letter in "qwrsz":
            self.game.guess(letter)
        self.assertEqual(self.game.lives, 1)
        for letter in set(WORD):
            self.game.guess(letter)
        self.assertIs(self.game.state, GameState.WON)

    def test_guess_after_game_over_is_inert(self):
        for letter in "qwrszx":
            self.game.guess(letter)
        self.assertIs(self.game.guess("p"), GuessResult.GAME_OVER)
        self.assertEqual(self.game.lives, 0)
        self.assertNotIn("p", self.game.guessed_letters)

    def test_initial_state(self):
        self.assertEqual(self.game.masked_word, "______")
        self.assertEqual(self.game.remaining, 6)
        self.assertEqual(self.game.lives, 6)
        self.assertIs(self.game.state, GameState.PLAYING)
        self.assertFalse(self.game.is_over)

    def test_invalid_secret_word_is_rejected(self):
        for bad in ("", "   ", "two words", "café", "co-ca"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    HangmanGame(bad)
        with self.assertRaises(ValueError):
            HangmanGame(WORD, lives=0)

    def test_properties_return_copies(self):
        self.game.guess("p")
        self.game.correct_letters.add("z")
        self.game.wrong_letters.append("z")
        self.assertNotIn("z", self.game.guessed_letters)


class TestHint(unittest.TestCase):
    """A2: one hint per round, reveals a random hidden letter, costs one life."""

    def setUp(self):
        self.game = HangmanGame(WORD)
        self.rng = random.Random(0)  # seeded, so these tests are deterministic

    def test_hint_reveals_a_hidden_letter_and_costs_one_life(self):
        self.assertIs(self.game.hint(self.rng), GuessResult.HINT)
        self.assertEqual(self.game.lives, 5)
        self.assertEqual(self.game.remaining, 5)
        self.assertEqual(len(self.game.correct_letters), 1)
        self.assertTrue(self.game.hint_used)

    def test_only_one_hint_per_round(self):
        self.game.hint(self.rng)
        self.assertIs(self.game.hint(self.rng), GuessResult.HINT_UNAVAILABLE)
        self.assertEqual(self.game.lives, 5)  # the refused hint cost nothing
        self.assertEqual(self.game.remaining, 5)

    def test_hint_only_reveals_letters_from_the_word(self):
        self.game.hint(self.rng)
        revealed = self.game.correct_letters
        self.assertTrue(revealed <= set(WORD))

    def test_hinted_letter_counts_as_already_guessed(self):
        self.game.hint(self.rng)
        letter = next(iter(self.game.correct_letters))
        self.assertIs(self.game.guess(letter), GuessResult.ALREADY_GUESSED)
        self.assertNotIn(letter, self.game.available_letters)

    def test_hint_never_repeats_an_already_revealed_letter(self):
        self.game.guess("p")
        self.game.hint(self.rng)
        self.assertEqual(len(self.game.correct_letters), 2)

    def test_hint_completing_the_word_on_the_last_life_is_a_win(self):
        game = HangmanGame("cat", lives=1)
        game.guess("c")
        game.guess("a")
        self.assertIs(game.hint(self.rng), GuessResult.HINT)
        self.assertEqual(game.lives, 0)
        self.assertIs(game.state, GameState.WON)  # not LOST: WON is checked first

    def test_hint_that_spends_the_last_life_without_winning_loses(self):
        game = HangmanGame(WORD, lives=1)
        self.assertIs(game.hint(self.rng), GuessResult.HINT)
        self.assertIs(game.state, GameState.LOST)

    def test_hint_after_game_over_is_inert(self):
        for letter in "qwrszx":
            self.game.guess(letter)
        self.assertIs(self.game.hint(self.rng), GuessResult.GAME_OVER)
        self.assertFalse(self.game.hint_used)

    def test_hidden_letters_shrink_as_the_word_is_revealed(self):
        self.assertEqual(self.game.hidden_letters, sorted(set(WORD)))
        self.game.guess("p")
        self.assertNotIn("p", self.game.hidden_letters)


if __name__ == "__main__":
    unittest.main()
