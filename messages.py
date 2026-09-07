"""One sentence per game outcome, shared by both interfaces.

This lives outside hangman/ on purpose: it is wording shown to a player, not a
rule of the game. main.py prints these; gui.py puts them in a label.
"""

from hangman.game import GuessResult

MESSAGES = {
    GuessResult.CORRECT: "Correct!",
    GuessResult.WRONG: "Wrong, you lose one life.",
    GuessResult.ALREADY_GUESSED: "You already tried that letter, pick another.",
    GuessResult.INVALID: "Invalid input: type exactly one letter (a-z).",
    GuessResult.GAME_OVER: "This round is already over.",
    GuessResult.HINT: "Hint: one letter revealed, and it cost you a life.",
    GuessResult.HINT_UNAVAILABLE: "You have already used your hint this round.",
}
