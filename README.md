# Hangman

A console word-guessing game in plain Python. **No third-party packages.**

The player picks a topic and a difficulty, then guesses the secret word one letter at a time.
A correct guess reveals every position holding that letter and costs nothing; a wrong guess
costs one life. **6 wrong guesses** are allowed, in every difficulty.

---

## 1. Install & run

Requires **Python 3.7+** (tested on 3.11.8, Windows 10). No dependencies.

```bash
cd BKCS_Test
python gui.py     # click-based window (A6)
python main.py    # or the console version
```

Both interfaces use the same `hangman/game.py`. Nothing in the rules changed to
make the window exist.

## 2. Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

> `-t .` is required. It makes the project root the top-level directory; without it `unittest`
> treats `tests/` as the root and `import hangman` inside the tests fails.

**46 tests**, against the required minimum of 5. Result: `Ran 46 tests — OK`.

## 3. Project layout

```
BKCS_Test/
├── gui.py                  # INTERFACE 1 — click-based window (tkinter)
├── main.py                 # INTERFACE 2 — console, the only file using print/input
├── messages.py             # the sentence for each outcome, shared by both interfaces
├── data/
│   ├── words.json          # 90 words in 2 topics (animal / food)
│   └── scores.csv          # score history, created on the first finished round
├── hangman/
│   ├── game.py             # RULES — no print/input, no file access, no `import random`
│   ├── words.py            # reads the word file, filters it, picks a word
│   └── scores.py           # scoring, and reading/writing scores.csv
└── tests/
    ├── test_game.py        # 23 tests for the rules
    ├── test_words.py       # 13 tests for the word data, topics and difficulty
    └── test_scores.py      # 10 tests for scoring and the CSV
```

`game.py` imports nothing from this project, so the arrows only ever point one way — and
**two different interfaces sit on top of the same rules**:

```
gui.py  ─┐
         ├─→  hangman/game.py        (the rules; imports only enum + string)
main.py ─┘
         ├─→  hangman/words.py   →  data/words.json
         └─→  hangman/scores.py  →  data/scores.csv
```

## 4. How it works, step by step

What happens from `python main.py` to the end of a round:

```
python main.py
  │
  ├─ 1. choose_topic()                      main.py
  │        asks words.topic_names(), which reads words.json
  │        prints "1. Animal  2. Food  3. All topics"
  │        returns "animal" | "food" | None            (None = all topics)
  │
  ├─ 2. choose_difficulty()                 main.py
  │        prints the three modes from words.DIFFICULTIES
  │        returns "easy" | "medium" | "hard"
  │
  ├─ 3. random_word(topic, difficulty)      words.py
  │        load_words()  read the JSON, lowercase, drop anything not a-z
  │        words_for()   keep the chosen topic, keep words in the length range
  │        rng.choice()  pick one                      ->  e.g. "dolphin"
  │
  ├─ 4. HangmanGame("dolphin")              game.py
  │        checks the word is a-z only, sets lives = 6, nothing guessed yet
  │
  ├─ 5. play_round(game)                    main.py - repeats while not game.is_over
  │        a. print(render_status(game))    reads masked_word, wrong_letters, lives, ...
  │        b. read_line()                   one line of text from the player
  │        c. "?" -> game.hint(random)      anything else -> game.guess(text)
  │        d. print(MESSAGES[result])       turns the returned enum into a sentence
  │
  ├─ 6. render_ending(game)                 win or lose, and the word either way
  │
  └─ 7. ask_play_again()                    "y" -> back to step 1,  "n" -> quit
```

### Inside one turn (step 5c)

`game.guess("a")` runs these checks in order and **returns at the first one that matches**:

| # | Check | Returns | Life lost? |
|---|---|---|---|
| 1 | Round already finished? | `GAME_OVER` | no |
| 2 | After `.strip().lower()`, exactly one letter a-z? | `INVALID` if not | **no** (F3) |
| 3 | Already tried this letter? | `ALREADY_GUESSED` | **no** (F3) |
| 4 | Is the letter in the word? | `CORRECT` | no |
| 5 | Otherwise | `WRONG` | **yes, exactly one** |

Checks 1-3 return *before* anything is modified, which is why a bad or repeated guess can never
cost a life. Only step 5 touches `self.lives`, and it subtracts exactly 1.

Then the caller reads `game.state`, which is recomputed on the spot:

```python
if not self.hidden_letters:  return GameState.WON    # word finished
if self.lives < 1:           return GameState.LOST   # out of lives
return GameState.PLAYING
```

Win is checked **before** loss, so finishing the word on your last life is a win.

### The same steps in the window

`gui.py` runs the identical pipeline; only the input and output change:

| Step | Console (`main.py`) | Window (`gui.py`) |
|---|---|---|
| 1-2. Pick topic and difficulty | numbered menus | two drop-downs, then "New game" |
| 3-4. Get a word, start a round | `random_word()` -> `HangmanGame(...)` | **the same two calls** |
| 5b. Player chooses a letter | types it and presses Enter | clicks one of 26 buttons |
| 5c. Play the turn | `game.guess(text)` | **`game.guess(letter)` - the same call** |
| 5d. Show the outcome | `print(MESSAGES[result])` | the same dict, into a label |
| 6. Round over | print the result | reveal the word, grey out the buttons, save the score |
| 7. Again? | `y`/`n` prompt | click "New game" |

Only rows 1-2, 5b, 5d and 7 differ, and every one of those is about *showing* or *collecting*
something. The middle of the pipeline is shared code.

## 5. Design decisions

### 5.1 The rules are separate from the screen (requirement 3.2)

The assignment calls this its most important criterion, so everything else follows from it.

`hangman/game.py` **imports only `enum` and `string`** - no `print`, no `input`, no `open`, no
`random`, and nothing from this project. That is the complete import list at the top of the file:

```python
import string
from enum import Enum
```

And nothing sneaks in further down, which you can check in one command:

```bash
grep -nE "print\(|input\(|open\(" hangman/game.py     # prints nothing
```

The payoff is concrete: **the rule tests mock nothing** - no fake `stdin`, no captured `stdout`,
no patched `random`. They build `HangmanGame("python")` and call `guess()`. Rules tangled up with
`input()` cannot be tested that way.

The core talks to the outside world by **returning a `GuessResult`**, never by printing:

```python
class GuessResult(Enum):
    CORRECT, WRONG, ALREADY_GUESSED, INVALID, GAME_OVER, HINT, HINT_UNAVAILABLE
```

`main.py` is then just a dictionary from each enum member to a sentence. Replacing the console
with a web page means rewriting `main.py` and leaving `game.py` alone.

### 5.2 State is worked out, not stored

`masked_word`, `hidden_letters` and `state` are recomputed on every read from the only two
things actually kept, `secret_word` and `correct_letters`:

```python
@property
def masked_word(self):
    return "".join(c if c in self.correct_letters else "_" for c in self.secret_word)
```

Storing a display string and editing it in place would mean **two sources of truth for one
fact**, and they drift apart - especially on words with repeated letters like `letter`. Working
it out instead makes "reveal *every* position of that letter" fall out for free rather than being
a special case. There is also no `remaining` counter: `len(hidden_letters)` already says it, and
one fact should have one home.

### 5.3 Input checking belongs to the rules, not the screen

`main.py` contains **no game rules at all** - no `len(x) != 1`, no alphabet check. It reads a
line and passes it straight to `game.guess()`.

Put that check in the interface instead and F3 ("invalid input must not cost a life") becomes a
promise of the *interface*: untestable without faking a keyboard, and broken the moment anything
else calls the core. Inside `guess()` it holds for **every** caller, and the test for it is four
lines long.

### 5.4 The word list lives outside the code (F1)

`data/words.json` holds 90 words grouped by topic:

```json
{ "animal": ["cat", "dog"], "food": ["egg", "rice"] }
```

Pure data, with **no difficulty labels** - difficulty comes from `len(word)` at run time, so a new
word lands in the right group by itself.

`words.py` cleans the data as it loads: lowercase everything, drop duplicates, drop anything that
is not plain a-z. That is not tidiness. A word like `"ice cream"` would make a round
**unwinnable**, because the player can never type a space. `HangmanGame.__init__` raises
`ValueError` on such a word too, and `test_every_word_builds_a_playable_game` checks that
**every** word in the file can actually be won.

### 5.5 Difficulty (A1) and topics (A3)

Both were added **without changing one line of `game.py`** - check `git show --stat` on that
commit and `game.py` is simply not in the list of changed files. That is the clearest evidence
the separation is real rather than decorative.

The reason: *which word to play* is a word-picking policy, not a rule of the game, so the table
lives in `words.py`:

| Mode | Difficulty | Word length | Lives | Words per topic |
|---|---|---|---|---|
| 1 | Easy | 3-5 letters | 6 | 24 |
| 2 | Medium | 6-8 letters | 6 | 13 |
| 3 | Hard | 9+ letters | 6 | 8 |

**Difficulty changes the word length only, never the lives** - every mode keeps the 6 wrong
guesses from rule 2.4. So the table has no `lives` entry at all: a value that is always 6 would
only suggest it can vary. `test_difficulty_changes_word_length_only_not_lives` pins that down.

Topic names are read from the data file and shown capitalised, so adding a topic is a data-only
change.

### 5.6 The hint (A2)

One hint per round in every difficulty. It reveals one **random letter that is still hidden** and
costs one life.

This is the only feature whose rules genuinely need randomness, which would normally drag
`import random` into `game.py` and break the claim in section 5.1. Instead the caller supplies it:

```python
def hint(self, rng):
    self.correct_letters.add(rng.choice(self.hidden_letters))
```

`main.py` passes the `random` module; the tests pass `random.Random(0)`. The **rules** stay in the
core (once per round, costs a life, only picks hidden letters) while **where randomness comes
from** is the caller's business. One extra argument, and `game.py` still imports nothing but
`enum` and `string`.

This is also where the win-before-loss ordering earns its keep: a hint that reveals the last
letter *and* spends the last life is a **win**.

### 5.7 The window (A6)

`gui.py` is a tkinter window, so it needs nothing installed. The player **clicks letters**
instead of typing them: 26 buttons, each greyed out once used, which also removes the whole
category of invalid input by construction.

It was written **without changing one line of `hangman/game.py`**. The window calls exactly the
same `game.guess(letter)` and `game.hint(random)` the console version calls, and reads the same
`masked_word`, `lives` and `state`. Two interfaces on one set of rules is the clearest proof the
separation is real, and it is why `main.py` was kept rather than replaced.

Like `main.py`, `gui.py` holds **no game rules**. It does not check whether a letter is valid or
already used; it clicks the letter in and renders whatever `GuessResult` comes back, using the
same sentences from `messages.py`.

### 5.8 Score and history (A4)

The score is one line, and a loss is worth nothing:

```python
def compute_score(game):
    if not game.won:
        return 0
    return game.lives * 10 + len(game.secret_word) * 5
```

Lives kept and word length both count. **The hint needs no separate penalty** — it already costs
a life, so it already shows up in the score. That falls out of the design rather than being
another rule to remember, and `test_the_hint_lowers_the_score_because_it_costs_a_life` checks it.

Every finished round is appended to `data/scores.csv`, one row, seven columns:

```
played_at,topic,difficulty,word,result,lives_left,score
2026-09-07 16:59:52,animal,easy,cat,win,6,75
```

The window shows the **best score for each of the three difficulties**, read back from that file,
so it survives between runs. The **"Details" button** saves a copy of the whole history wherever
the player chooses, through the normal save dialog.

`scores.py` takes the file path as an argument everywhere, so the tests write to a temporary
directory and never touch the real history.

### 5.9 Smaller choices

- **`state` checks WIN before LOSS**, so the last letter on the last life wins.
- **Output is pure ASCII**, which sidesteps the Windows console codepage problem entirely - no
  `UnicodeEncodeError`, no `chcp`, nothing to configure.
- **`read_line()` catches `EOFError` and `KeyboardInterrupt`**, so Ctrl+C or a closed pipe prints
  "Goodbye!" instead of a traceback.
- **Replaying builds a new `HangmanGame`** rather than resetting the old one, so nothing leaks
  between rounds.
- **Attributes are plain and public.** `guess()` is the only thing that changes them, and keeping
  them simple is worth more here than defending against a caller who edits them by hand.

## 6. Assumptions (points the assignment left open)

1. **Input is `.strip()`ed.** `" a "` counts as guessing `a`; a string of only spaces becomes
   empty and is rejected, as required.
2. **Letters only, never whole words** - rule 2.3 says "one letter at a time".
3. **Words are lowercase a-z**, single tokens, no spaces or hyphens.
4. **Winning is counted in distinct letters**, not characters.
5. **Re-guessing any letter** - right or wrong - is "already guessed" and costs nothing.
6. **The replay prompt** takes `y`/`n`; anything else re-asks instead of quitting.
7. **Lives are always 6.** Rule 2.4 caps wrong guesses at 6, while A1 suggests difficulty should
   change the number of turns; the two conflict. I kept the stated rule and let difficulty change
   the word length only.
8. **Topic and difficulty are chosen again each round**, not carried over.
9. **The hint costs a life even when it reveals the last letter** (the round is still won), and a
   hint already used costs nothing when asked for again.
10. **`guess()` expects a string.** It comes from `input()`, so it always is one; type-checking
    the argument would be guarding against a caller that does not exist.

## 7. Requirements checklist

| # | Requirement | Status |
|---|---|---|
| F1 | Random word from a list of >=30, in a separate file | Done - 90 words in `data/words.json` |
| F2 | Show word state, guessed letters, lives left | Done - `render_status()` |
| F3 | Invalid input costs no life and does not crash | Done - empty / >1 char / non-letter / repeat |
| F4 | Case-insensitive | Done - `.lower()` before the alphabet check |
| F5 | Announce win/loss, reveal the word, offer a replay | Done - the word is shown either way |
| 3.2 | Rules separated from the interface | Done - `game.py` imports only `enum`, `string` |
| - | At least 5 unit tests | Done - 46 tests |
| - | README | Done - this file |
| A1 | Difficulty easy/medium/hard | Done - modes 1/2/3, changes word length (assumption 7) |
| A2 | One hint per round, reveals a letter, costs a turn | Done - `?` in the console, a button in the window |
| A3 | Words grouped by topic, chosen by the player | Done - Animal / Food / All topics |
| A4 | Score, saved to a file and kept between runs | Done - `data/scores.csv` |
| A5 | Vietnamese words with diacritics | Not done - approach described in section 8 |
| A6 | Graphical interface instead of the console | Done - `python gui.py` |

## 8. What I would do next

Roughly in priority order. None of these requires touching `game.py`, which is the point of
the layering:

- **A hangman drawing.** Pure presentation: 7 frames chosen by `len(game.wrong_letters)`, as
  ASCII in `main.py` or a tkinter canvas in `gui.py`. No change to the rules.
- **A per-player leaderboard.** `scores.csv` already records every round; grouping by a player
  name would be a query over it, not a change to the game.
- **A5 - Vietnamese words with diacritics.** The approach I would take: normalise with
  `unicodedata.normalize("NFC", ...)` so `ế` is a **single** code point rather than `e` plus a
  combining accent - otherwise both `len()` and letter matching go wrong. I would match
  diacritic-sensitively (`e`, `é`, `ê`, `ề` are four different letters), because that is what a
  Vietnamese player expects, and treat `đ` as distinct from `d`. Digraphs like `ch`, `ng`, `nh`
  are still typed one character at a time. The code change is small because of the current
  design: `ALPHABET` becomes a constructor argument
  (`HangmanGame(secret, alphabet=VIETNAMESE_ALPHABET)`), plus a `data/words_vi.json` in the same
  schema.

## 9. Use of AI tools

I used **Claude (Claude Code)** while working on this:

- Discussing the architecture and reviewing my first draft design. It caught several bugs in the
  pseudocode I had sketched. The most serious: putting the life-deduction branch **inside** the
  `for` loop that scans each position takes one life per *non-matching position*, so a single
  wrong guess on a 6-letter word would have ended the game immediately. Also, an "available
  letters" set built by subtracting only the **wrong** guesses still lets the player re-guess
  letters they already got **right**; and `now[i] = letter` fails outright, because Python
  strings are immutable.
- Generating the code and the tests from the agreed design.
- Drafting this README.

The rules, the data model (`point`/`remain`/`flag`, the letter whitelist, the food/animal topic
split) were mine. I have read, understood and verified every line in this repository and can
explain any of it.
