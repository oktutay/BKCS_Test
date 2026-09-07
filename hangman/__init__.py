"""Hangman game package.

`game` holds the rules and is free of any I/O; `words` handles the data file.
The console interface lives outside this package, in main.py.
"""

from .game import DEFAULT_LIVES, GameState, GuessResult, HangmanGame

__all__ = ["HangmanGame", "GameState", "GuessResult", "DEFAULT_LIVES"]
