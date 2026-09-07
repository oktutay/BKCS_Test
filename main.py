"""Console interface for Hangman.

The only file that calls print() or input(). It holds no game rules: it reads a
line of text, hands it to the game, and prints whatever comes back.

The functions are written in the order they run, top to bottom:
    main -> choose_topic -> choose_difficulty -> random_word
         -> play_round (show status -> read a line -> guess or hint)
         -> show the result -> ask_play_again
"""

import random

from hangman.game import HangmanGame
from hangman.words import DIFFICULTIES, MODES, WordDataError, random_word, topic_names
from messages import MESSAGES

HINT_COMMAND = "?"


def read_line(prompt):
    """input() that quits politely on Ctrl+C or end of input."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def ask_menu(prompt, options):
    """Show nothing, just read a number until it matches one of `options`."""
    while True:
        answer = read_line(prompt).strip()
        if answer.isdigit() and int(answer) in options:
            return options[int(answer)]
        print("Please type one of the numbers listed above.")


# --- Step 1: pick a topic -------------------------------------------------

def choose_topic():
    """Returns a topic name, or None meaning "all topics"."""
    options = dict(enumerate(topic_names(), start=1))
    options[len(options) + 1] = None

    print("\nChoose a topic:")
    for number, name in sorted(options.items()):
        # Names come straight from words.json, so a new topic needs no code change.
        print(f"  {number}. {'All topics' if name is None else name.capitalize()}")
    return ask_menu("Your choice: ", options)


# --- Step 2: pick a difficulty --------------------------------------------

def choose_difficulty():
    """Returns a difficulty key, e.g. 'medium'."""
    print("\nChoose a difficulty:")
    for mode, key in sorted(MODES.items()):
        level = DIFFICULTIES[key]
        if level["max_length"] >= 99:
            length = f"{level['min_length']} letters or more"
        else:
            length = f"{level['min_length']}-{level['max_length']} letters"
        print(f"  {mode}. {level['label']:<8} ({length})")
    return ask_menu("Your choice: ", dict(MODES))


# --- Step 3: draw the screen ----------------------------------------------

def render_status(game):
    """The per-turn screen (F2). Returns text, does not print it."""
    hint = "used" if game.hint_used else "available, type '?'"
    wrong = ", ".join(game.wrong_letters) or "(none)"
    return "\n".join([
        "",
        f"Word     : {' '.join(game.masked_word)}",
        f"Wrong    : {wrong}",
        f"Lives    : {game.lives}/{game.max_lives}",
        f"Hint     : {hint}",
        f"Letters  : {' '.join(game.available_letters)}",
    ])


def render_ending(game):
    """The end-of-round screen: the result, and the word either way (F5)."""
    banner = "YOU WIN!" if game.won else "YOU LOSE."
    return f"\n{banner}\nThe word was: {game.secret_word.upper()}"


# --- Step 4: play one round -----------------------------------------------

def play_round(game):
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


# --- Step 5: play again? --------------------------------------------------

def ask_play_again():
    while True:
        answer = read_line("\nPlay again? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def main():
    print("=== HANGMAN ===")
    print("Guess the word one letter at a time. You may miss 6 times.")

    while True:
        try:
            topic = choose_topic()
            difficulty = choose_difficulty()
            secret = random_word(topic=topic, difficulty=difficulty)
        except WordDataError as exc:
            print(f"Word data error: {exc}")
            return 1

        shown_topic = "All topics" if topic is None else topic.capitalize()
        print(f"\nTopic: {shown_topic} | Difficulty: {DIFFICULTIES[difficulty]['label']}")

        play_round(HangmanGame(secret))

        if not ask_play_again():
            break

    print("Thanks for playing!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
