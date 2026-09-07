"""Hangman game rules.

Pure logic: this module has no print(), no input() and no file access, and it
does not import `random` -- hint() takes the random source as an argument
instead. It can be driven from a REPL, a unit test, a web handler or a GUI
without changing a line. That independence is the point -- see README.md.
"""

import string
from enum import Enum

# The only characters that count as a guess (the "whitelist").
# Built from string.ascii_lowercase rather than typed out, so it cannot have typos.
ALPHABET = frozenset(string.ascii_lowercase)

# The rules allow at most 6 wrong guesses.
DEFAULT_LIVES = 6

MASK = "_"


class GuessResult(Enum):
    """What a single guess did. Returned to the caller, never printed."""

    CORRECT = "correct"
    WRONG = "wrong"
    ALREADY_GUESSED = "already_guessed"
    INVALID = "invalid"
    GAME_OVER = "game_over"
    HINT = "hint"
    HINT_UNAVAILABLE = "hint_unavailable"


class GameState(Enum):
    """Whether the round is still running, lost or won."""

    PLAYING = 0
    LOST = 1
    WON = 2


def normalize(raw):
    """Fold a raw input into a single a-z letter, or None if it is not a legal guess.

    Lowercasing happens BEFORE the alphabet check so that "A" is accepted (F4).
    Accepts any object, so a stray None or int returns None instead of raising (F3).
    """
    if not isinstance(raw, str):
        return None
    letter = raw.strip().lower()
    if len(letter) != 1 or letter not in ALPHABET:
        return None
    return letter


class HangmanGame:
    """One round of Hangman.

    The secret word is supplied by the caller; this class never picks one. That
    keeps it free of `random` and lets tests use a fixed word with no mocking.
    """

    def __init__(self, secret_word, lives=DEFAULT_LIVES):
        word = secret_word.strip().lower() if isinstance(secret_word, str) else ""
        if not word:
            raise ValueError("secret word must not be empty")
        if not set(word) <= ALPHABET:
            # A word with spaces or accents could never be fully guessed, which
            # would silently make the round unwinnable. Fail loudly instead.
            raise ValueError("secret word must contain only a-z, got %r" % (secret_word,))
        if lives < 1:
            raise ValueError("lives must be >= 1, got %r" % (lives,))

        self._secret = word
        self._lives = lives
        self._max_lives = lives
        self._correct = set()
        self._wrong = []  # kept in order, so the UI can list them as they happened
        self._hint_used = False  # one hint per round, in every difficulty

    # ------------------------------------------------------------------
    # Read-only views. The UI renders the whole screen from these (F2).
    # Everything below is derived on read, so no two pieces of state can
    # ever drift out of sync.
    # ------------------------------------------------------------------

    @property
    def secret_word(self):
        """The answer. The UI only reveals it once the round is over (F5)."""
        return self._secret

    @property
    def lives(self):
        """Wrong guesses still allowed."""
        return self._lives

    @property
    def max_lives(self):
        return self._max_lives

    @property
    def correct_letters(self):
        return set(self._correct)  # a copy: callers cannot corrupt our state

    @property
    def wrong_letters(self):
        return list(self._wrong)

    @property
    def guessed_letters(self):
        """Every letter already tried, right or wrong."""
        return self._correct | set(self._wrong)

    @property
    def available_letters(self):
        """Letters not yet tried -- the alphabet minus ALL guesses, right or wrong."""
        return sorted(ALPHABET - self.guessed_letters)

    @property
    def masked_word(self):
        """The word with unrevealed letters hidden, e.g. 'p_th_n'.

        Derived from the secret and the correct guesses, so revealing every
        occurrence of a repeated letter is automatic.
        """
        return "".join(c if c in self._correct else MASK for c in self._secret)

    @property
    def remaining(self):
        """How many DISTINCT letters are still hidden."""
        return len(set(self._secret) - self._correct)

    @property
    def state(self):
        """PLAYING / LOST / WON, computed fresh so it can never be stale."""
        if self.remaining == 0:
            # Checked first: completing the word wins, even on the last life.
            return GameState.WON
        if self._lives <= 0:
            return GameState.LOST
        return GameState.PLAYING

    @property
    def is_over(self):
        return self.state is not GameState.PLAYING

    @property
    def won(self):
        return self.state is GameState.WON

    @property
    def hint_used(self):
        """Whether this round's single hint has been spent."""
        return self._hint_used

    @property
    def hidden_letters(self):
        """The distinct letters of the secret that are still not revealed."""
        return sorted(set(self._secret) - self._correct)

    # ------------------------------------------------------------------
    # The two methods that change state.
    # ------------------------------------------------------------------

    def guess(self, raw):
        """Play one letter and return a GuessResult.

        Never raises on bad input and never costs more than one life (F3).
        Every rejection path returns before any state is touched.
        """
        if self.is_over:
            return GuessResult.GAME_OVER

        letter = normalize(raw)
        if letter is None:
            # Empty, blank, more than one character, or not a letter.
            return GuessResult.INVALID
        if letter in self.guessed_letters:
            return GuessResult.ALREADY_GUESSED

        if letter in self._secret:
            # One membership test decides the whole guess. Deliberately not a
            # per-position loop: that would deduct a life per non-matching
            # position and end the game on the first wrong guess.
            self._correct.add(letter)
            return GuessResult.CORRECT

        self._wrong.append(letter)
        self._lives -= 1
        return GuessResult.WRONG

    def hint(self, rng):
        """Reveal one random hidden letter, at the cost of one life.

        Only one hint per round, whatever the difficulty.

        `rng` must be supplied by the caller -- the `random` module itself, or a
        random.Random instance. Taking it as an argument is what lets this
        module stay free of `import random`, so the rules remain deterministic
        under test while the caller decides where randomness comes from.
        """
        if self.is_over:
            return GuessResult.GAME_OVER
        if self._hint_used:
            return GuessResult.HINT_UNAVAILABLE

        hidden = self.hidden_letters
        if not hidden:
            return GuessResult.HINT_UNAVAILABLE

        self._correct.add(rng.choice(hidden))
        self._hint_used = True
        self._lives -= 1
        # If that revealed the last letter, `state` reports WON rather than
        # LOST even when the cost took the final life: it checks WON first.
        return GuessResult.HINT
