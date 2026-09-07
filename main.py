"""Console interface for the Hangman game.

This is the ONLY module in the project that calls print() or input(). It holds
no game rules: it reads a raw string, hands it to the game, and renders
whatever comes back.
"""

import random

from hangman.game import GuessResult, HangmanGame
from hangman.words import DIFFICULTIES, MODES, WordDataError, random_word, topics

HINT_COMMAND = "?"

MESSAGES = {
    GuessResult.CORRECT: "Correct!",
    GuessResult.WRONG: "Wrong, you lose one life.",
    GuessResult.ALREADY_GUESSED: "You already tried that letter, pick another.",
    GuessResult.INVALID: "Invalid input: type exactly one letter (a-z).",
    GuessResult.GAME_OVER: "This round is already over.",
    GuessResult.HINT: "Hint used: one letter revealed, and it cost you one life.",
    GuessResult.HINT_UNAVAILABLE: "You have already used your hint this round.",
}


def render_status(game):
    """Build the per-turn status screen (F2). Returns a string, does not print."""
    hint = "used" if game.hint_used else "available (type '?')"
    return "\n".join(
        [
            "",
            "Word     : %s" % " ".join(game.masked_word),
            "Guessed  : %s" % (", ".join(sorted(game.guessed_letters)) or "(none)"),
            "Wrong    : %s" % (", ".join(game.wrong_letters) or "(none)"),
            "Lives    : %d/%d" % (game.lives, game.max_lives),
            "Hint     : %s" % hint,
        ]
    )


def render_ending(game):
    """Build the end-of-round screen: result plus the secret word (F5)."""
    banner = "YOU WIN!" if game.won else "YOU LOSE."
    return "\n%s\nThe word was: %s" % (banner, game.secret_word.upper())


def read_line(prompt):
    """input() that exits cleanly on Ctrl+C or end of input instead of a traceback."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def play_round(game):
    """Run one full round to its end."""
    while not game.is_over:
        print(render_status(game))
        answer = read_line("Your letter (or '?' for a hint): ")
        if answer.strip() == HINT_COMMAND:
            result = game.hint(random)
        else:
            result = game.guess(answer)
        print(MESSAGES[result])
    print(render_status(game))
    print(render_ending(game))


def ask_play_again():
    """F5: ask whether to start another round."""
    while True:
        answer = read_line("\nPlay again? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def choose_number(prompt, options):
    """Ask the player to pick one numbered option. Re-asks until the answer is valid."""
    while True:
        answer = read_line(prompt).strip()
        if answer.isdigit() and int(answer) in options:
            return options[int(answer)]
        print("Please enter one of the numbers listed above.")


def choose_difficulty():
    """A1: pick a difficulty. Returns its key, e.g. 'medium'."""
    print("\nChoose a difficulty:")
    for mode, key in sorted(MODES.items()):
        level = DIFFICULTIES[key]
        if level.max_length >= 99:  # open-ended top bucket
            length = "%d letters or more" % level.min_length
        else:
            length = "%d-%d letters" % (level.min_length, level.max_length)
        print("  %d. %-8s (%s)" % (mode, level.label, length))
    return choose_number("Your choice: ", dict(MODES))


def choose_topic():
    """A3: pick a topic, or all of them. Returns a topic name or None for all."""
    options = {i: name for i, name in enumerate(topics(), start=1)}
    options[len(options) + 1] = None  # the "all topics" entry

    print("\nChoose a topic:")
    for number, name in sorted(options.items()):
        # Topic names come straight from the data file, so adding a topic there
        # needs no change here.
        print("  %d. %s" % (number, "All topics" if name is None else name.capitalize()))
    return choose_number("Your choice: ", options)


def main():
    print("=== HANGMAN ===")
    print("Guess the word one letter at a time. You may miss 6 times.")
    while True:
        try:
            topic = choose_topic()
            difficulty = choose_difficulty()
            secret = random_word(topic=topic, difficulty=difficulty)
        except WordDataError as exc:
            print("Word data error: %s" % exc)
            return 1

        # Difficulty only changes the word length; every mode keeps 6 lives.
        print(
            "\nTopic: %s | Difficulty: %s"
            % (
                "All topics" if topic is None else topic.capitalize(),
                DIFFICULTIES[difficulty].label,
            )
        )
        play_round(HangmanGame(secret))

        if not ask_play_again():
            break
    print("Thanks for playing!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
