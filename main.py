"""Console interface for the Hangman game.

This is the ONLY module in the project that calls print() or input(). It holds
no game rules: it reads a raw string, hands it to game.guess(), and renders
whatever comes back.
"""

import sys

from hangman.game import GuessResult, HangmanGame
from hangman.words import DIFFICULTIES, MODES, WordDataError, random_word, topics

# The Windows console defaults to a codepage that cannot encode Vietnamese, so
# printing "Chúc mừng" would raise UnicodeEncodeError and look like a crash.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MESSAGES = {
    GuessResult.CORRECT: "Chính xác!",
    GuessResult.WRONG: "Sai rồi, bạn mất 1 lượt.",
    GuessResult.ALREADY_GUESSED: "Bạn đã đoán chữ này rồi, hãy thử chữ khác.",
    GuessResult.INVALID: "Không phù hợp — hãy nhập đúng 1 chữ cái (a-z).",
    GuessResult.GAME_OVER: "Ván đấu đã kết thúc.",
}

# Display names for the topics in data/words.json. A topic with no entry here
# still works -- it just shows its raw key -- so adding a topic stays a
# data-only change.
TOPIC_LABELS = {
    "animal": "Động vật",
    "food": "Đồ ăn",
}


def render_status(game):
    """Build the per-turn status screen (F2). Returns a string, does not print."""
    guessed = ", ".join(sorted(game.guessed_letters)) or "(chưa có)"
    wrong = ", ".join(game.wrong_letters) or "(chưa có)"
    return "\n".join(
        [
            "",
            "Từ cần đoán  : %s" % " ".join(game.masked_word),
            "Đã đoán      : %s" % guessed,
            "Đoán sai     : %s" % wrong,
            "Lượt còn lại : %d/%d" % (game.lives, game.max_lives),
        ]
    )


def render_ending(game):
    """Build the end-of-round screen: result plus the secret word (F5)."""
    banner = "CHÚC MỪNG, BẠN ĐÃ THẮNG!" if game.won else "RẤT TIẾC, BẠN ĐÃ THUA."
    return "\n%s\nTừ bí mật là: %s" % (banner, game.secret_word.upper())


def read_line(prompt):
    """input() that exits cleanly on Ctrl+C or end of input instead of a traceback."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nTạm biệt!")
        raise SystemExit(0)


def play_round(game):
    """Run one full round to its end."""
    while not game.is_over:
        print(render_status(game))
        result = game.guess(read_line("Nhập 1 chữ cái: "))
        print(MESSAGES[result])
    print(render_status(game))
    print(render_ending(game))


def ask_play_again():
    """F5: ask whether to start another round."""
    while True:
        answer = read_line("\nBạn có muốn chơi lại không? (c/k): ").strip().lower()
        if answer in ("c", "co", "y", "yes"):
            return True
        if answer in ("k", "khong", "n", "no"):
            return False
        print("Vui lòng nhập 'c' (có) hoặc 'k' (không).")


def choose_number(prompt, options):
    """Ask the player to pick one numbered option. Re-asks until the answer is valid."""
    while True:
        answer = read_line(prompt).strip()
        if answer.isdigit() and int(answer) in options:
            return options[int(answer)]
        print("Vui lòng nhập một số trong danh sách.")


def choose_difficulty():
    """A1: pick a difficulty. Returns its key, e.g. 'medium'."""
    print("\nChọn độ khó:")
    for mode, key in sorted(MODES.items()):
        level = DIFFICULTIES[key]
        if level.max_length >= 99:  # open-ended top bucket
            length = "từ %d chữ cái trở lên" % level.min_length
        else:
            length = "%d-%d chữ cái" % (level.min_length, level.max_length)
        print("  %d. %-12s (%s)" % (mode, level.label, length))
    return choose_number("Lựa chọn của bạn: ", dict(MODES))


def choose_topic():
    """A3: pick a topic, or all of them. Returns a topic name or None for all."""
    names = topics()
    options = {i: name for i, name in enumerate(names, start=1)}
    options[len(options) + 1] = None  # "all topics"

    print("\nChọn chủ đề:")
    for number, name in sorted(options.items()):
        label = "Tất cả" if name is None else TOPIC_LABELS.get(name, name)
        print("  %d. %s" % (number, label))
    return choose_number("Lựa chọn của bạn: ", options)


def main():
    print("=== TRÒ CHƠI ĐOÁN CHỮ (HANGMAN) ===")
    print("Đoán từng chữ cái cho tới khi ra từ bí mật.")
    while True:
        try:
            topic = choose_topic()
            difficulty = choose_difficulty()
            secret = random_word(topic=topic, difficulty=difficulty)
        except WordDataError as exc:
            print("Lỗi dữ liệu từ vựng: %s" % exc)
            return 1

        # Every difficulty keeps the 6 wrong guesses from the rules; only the
        # word length changes.
        level = DIFFICULTIES[difficulty]
        label = "Tất cả" if topic is None else TOPIC_LABELS.get(topic, topic)
        print("\nChủ đề: %s | Độ khó: %s" % (label, level.label))
        play_round(HangmanGame(secret))

        if not ask_play_again():
            break
    print("Cảm ơn bạn đã chơi!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
