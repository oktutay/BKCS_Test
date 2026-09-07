"""Click-based desktop interface (A6), built with tkinter from the standard library.

Like main.py, this file holds no game rules. It clicks letters into
game.guess(), asks game for the state, and draws it. `hangman/game.py` did not
change at all to make this window exist -- that is the whole point of keeping
the rules separate from the screen.
"""

import random
import shutil
import string
import tkinter as tk
from tkinter import filedialog, messagebox

from hangman.game import HangmanGame
from hangman.scores import SCORE_FILE, best_scores, save_score
from hangman.words import DIFFICULTIES, WordDataError, random_word, topic_names
from messages import MESSAGES

ALL_TOPICS = "All topics"
MONO = ("Consolas", 22, "bold")


class HangmanApp:
    def __init__(self, root):
        self.root = root
        self.game = None
        self.topic = tk.StringVar(value=ALL_TOPICS)
        self.difficulty = tk.StringVar(value="Medium")

        self._build_controls()
        self._build_board()
        self._build_letters()
        self._build_footer()
        self.new_game()

    # --- building the window ---------------------------------------------

    def _build_controls(self):
        bar = tk.Frame(self.root, pady=8)
        bar.pack()

        tk.Label(bar, text="Topic:").pack(side=tk.LEFT)
        topics = [ALL_TOPICS] + [name.capitalize() for name in topic_names()]
        tk.OptionMenu(bar, self.topic, *topics).pack(side=tk.LEFT, padx=(2, 12))

        tk.Label(bar, text="Difficulty:").pack(side=tk.LEFT)
        labels = [DIFFICULTIES[k]["label"] for k in ("easy", "medium", "hard")]
        tk.OptionMenu(bar, self.difficulty, *labels).pack(side=tk.LEFT, padx=2)

        tk.Button(bar, text="New game", command=self.new_game).pack(side=tk.LEFT, padx=12)

    def _build_board(self):
        self.word_label = tk.Label(self.root, font=MONO, pady=10)
        self.word_label.pack()
        self.info_label = tk.Label(self.root)
        self.info_label.pack()
        self.message_label = tk.Label(self.root, fg="navy", pady=6)
        self.message_label.pack()

    def _build_letters(self):
        grid = tk.Frame(self.root, pady=6)
        grid.pack()
        self.letter_buttons = {}
        for i, letter in enumerate(string.ascii_lowercase):
            button = tk.Button(
                grid,
                text=letter.upper(),
                width=3,
                command=lambda c=letter: self.on_letter(c),
            )
            button.grid(row=i // 13, column=i % 13, padx=1, pady=1)
            self.letter_buttons[letter] = button

        self.hint_button = tk.Button(
            self.root, text="Hint (costs 1 life)", command=self.on_hint
        )
        self.hint_button.pack(pady=4)

    def _build_footer(self):
        self.best_label = tk.Label(self.root, pady=6)
        self.best_label.pack()
        tk.Button(
            self.root, text="Details (save scores.csv)", command=self.on_details
        ).pack(pady=(0, 10))

    # --- the three things a click can do ---------------------------------

    def new_game(self):
        topic = None if self.topic.get() == ALL_TOPICS else self.topic.get().lower()
        difficulty = self.difficulty.get().lower()
        try:
            secret = random_word(topic=topic, difficulty=difficulty)
        except WordDataError as exc:
            messagebox.showerror("Word data error", str(exc))
            return

        self.game = HangmanGame(secret)
        self.round_topic = topic
        self.round_difficulty = difficulty
        for button in self.letter_buttons.values():
            button.config(state=tk.NORMAL)
        self.message_label.config(text="Click a letter to guess.")
        self.refresh()

    def on_letter(self, letter):
        result = self.game.guess(letter)
        self.letter_buttons[letter].config(state=tk.DISABLED)
        self.message_label.config(text=MESSAGES[result])
        self.after_turn()

    def on_hint(self):
        result = self.game.hint(random)
        self.message_label.config(text=MESSAGES[result])
        # The hint reveals a letter, so grey out its button too.
        for letter in self.game.correct_letters:
            self.letter_buttons[letter].config(state=tk.DISABLED)
        self.after_turn()

    def on_details(self):
        """Save a copy of the score history wherever the player wants it."""
        if not SCORE_FILE.exists():
            messagebox.showinfo("No scores yet", "Finish a round first.")
            return
        target = filedialog.asksaveasfilename(
            title="Save score history",
            defaultextension=".csv",
            initialfile="scores.csv",
            filetypes=[("CSV file", "*.csv")],
        )
        if target:
            shutil.copyfile(SCORE_FILE, target)
            messagebox.showinfo("Saved", f"Score history saved to:\n{target}")

    # --- redrawing --------------------------------------------------------

    def refresh(self):
        game = self.game
        self.word_label.config(text=" ".join(game.masked_word.upper()))
        wrong = ", ".join(game.wrong_letters) or "(none)"
        self.info_label.config(
            text=f"Lives: {game.lives}/{game.max_lives}     Wrong: {wrong}"
        )
        self.hint_button.config(
            state=tk.DISABLED if game.hint_used or game.is_over else tk.NORMAL
        )
        self.show_best_scores()

    def after_turn(self):
        """Redraw, and wrap the round up if that click ended it."""
        self.refresh()
        if self.game.is_over:
            self.finish_round()
            self.show_best_scores()

    def finish_round(self):
        game = self.game
        for button in self.letter_buttons.values():
            button.config(state=tk.DISABLED)
        self.word_label.config(text=" ".join(game.secret_word.upper()))
        save_score(game, self.round_topic, self.round_difficulty)
        outcome = "YOU WIN!" if game.won else "YOU LOSE."
        self.message_label.config(
            text=f"{outcome}  The word was {game.secret_word.upper()}."
            f"  Click 'New game' to play again."
        )

    def show_best_scores(self):
        best = best_scores()
        parts = [
            f"{DIFFICULTIES[k]['label']}: {best.get(k, 0)}"
            for k in ("easy", "medium", "hard")
        ]
        self.best_label.config(text="Best score  |  " + "   ".join(parts))


def run():
    root = tk.Tk()
    root.title("Hangman")
    HangmanApp(root)
    # Let tk work out how much room the widgets need BEFORE freezing the size,
    # otherwise the window keeps its default width and clips the letter grid.
    root.update_idletasks()
    root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    run()
