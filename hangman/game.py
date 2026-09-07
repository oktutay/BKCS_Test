"""The rules of Hangman.

Pure logic: no print, no input, no files, no `import random`. Everything this
module needs is passed in as an argument, which is why it can be tested without
mocking anything. See README.md section 4.
"""

import string
from enum import Enum

ALPHABET = frozenset(string.ascii_lowercase)  # the only letters a guess may use
DEFAULT_LIVES = 6  # the rules allow 6 wrong guesses


class GuessResult(Enum):
    """What one turn did. The core returns this; main.py turns it into a sentence."""

    CORRECT = "correct"
    WRONG = "wrong"
    ALREADY_GUESSED = "already_guessed"
    INVALID = "invalid"
    GAME_OVER = "game_over"
    HINT = "hint"
    HINT_UNAVAILABLE = "hint_unavailable"


class GameState(Enum):
    PLAYING = 0
    LOST = 1
    WON = 2


class HangmanGame:
    """One round.

    The caller supplies the secret word, so this class never picks one and
    never needs `random`.
    """

    def __init__(self, secret_word, lives=DEFAULT_LIVES):
        word = secret_word.strip().lower()
        if not word or not set(word) <= ALPHABET:
            # A word with a space or an accent could never be typed by the
            # player, so the round would be unwinnable. Fail now, loudly.
            raise ValueError(f"secret word must be letters a-z only, got {secret_word!r}")
        if lives < 1:
            raise ValueError(f"lives must be at least 1, got {lives}")

        self.secret_word = word
        self.lives = lives
        self.max_lives = lives
        self.correct_letters = set()  # letters guessed right
        self.wrong_letters = []       # letters guessed wrong, in order
        self.hint_used = False        # one hint per round

    # --- Views on the state. All computed on read, so nothing can go stale. ---

    @property
    def guessed_letters(self):
        """Every letter tried so far, right or wrong."""
        return self.correct_letters | set(self.wrong_letters)

    @property
    def available_letters(self):
        """Letters not tried yet: the alphabet minus ALL guesses, right and wrong."""
        return sorted(ALPHABET - self.guessed_letters)

    @property
    def hidden_letters(self):
        """Distinct letters of the word that are still covered up."""
        return sorted(set(self.secret_word) - self.correct_letters)

    @property
    def masked_word(self):
        """The word with unguessed letters hidden, e.g. 'p_th_n'.

        Rebuilt from the word plus the correct guesses every time it is read,
        so every position of a repeated letter is revealed automatically.
        """
        return "".join(c if c in self.correct_letters else "_" for c in self.secret_word)

    @property
    def state(self):
        if not self.hidden_letters:
            return GameState.WON  # checked first: finishing the word wins
        if self.lives < 1:
            return GameState.LOST
        return GameState.PLAYING

    @property
    def is_over(self):
        return self.state is not GameState.PLAYING

    @property
    def won(self):
        return self.state is GameState.WON

    # --- The two actions that change the state. ---

    def guess(self, raw):
        """Play one letter. Returns a GuessResult and never raises."""
        if self.is_over:
            return GuessResult.GAME_OVER

        letter = raw.strip().lower()  # "A" and "a" are the same letter (F4)

        # Each check below returns before anything changes, so an invalid or
        # repeated guess can never cost a life (F3).
        if len(letter) != 1 or letter not in ALPHABET:
            return GuessResult.INVALID
        if letter in self.guessed_letters:
            return GuessResult.ALREADY_GUESSED

        if letter in self.secret_word:
            # One check for the whole guess, not one per position: looping over
            # positions would take a life for every letter that did not match.
            self.correct_letters.add(letter)
            return GuessResult.CORRECT

        self.wrong_letters.append(letter)
        self.lives -= 1
        return GuessResult.WRONG

    def hint(self, rng):
        """Reveal one random hidden letter for the price of a life. Once per round.

        `rng` is passed in (the random module, or a random.Random) so this file
        does not import random and the tests can make the choice predictable.
        """
        if self.is_over:
            return GuessResult.GAME_OVER
        if self.hint_used:
            return GuessResult.HINT_UNAVAILABLE

        self.correct_letters.add(rng.choice(self.hidden_letters))
        self.hint_used = True
        self.lives -= 1
        # If that was the last letter, `state` says WON, because it checks for
        # a win before it checks for a loss.
        return GuessResult.HINT
