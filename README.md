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
python main.py
```

## 2. Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

> `-t .` is required. It makes the project root the top-level directory; without it `unittest`
> treats `tests/` as the root and `import hangman` inside the tests fails.

**36 tests**, against the required minimum of 5. Result: `Ran 36 tests — OK`.

## 3. Project layout

```
BKCS_Test/
├── main.py                 # INTERFACE — the only file that calls print() / input()
├── data/
│   └── words.json          # 90 words in 2 topics (animal / food)
├── hangman/
│   ├── game.py             # RULES — no print/input, no file access, no `import random`
│   └── words.py            # reads the word file, filters it, picks a word
└── tests/
    ├── test_game.py        # 23 tests for the rules
    └── test_words.py       # 13 tests for the word data, topics and difficulty
```

Three files, one job each. `game.py` imports nothing from this project, so the arrows only
ever point one way:

```
main.py  →  hangman/words.py  →  data/words.json
        ↘   hangman/game.py
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

## 5. Design decisions

### 5.1 The rules are separate from the screen (requirement 3.2)

The assignment calls this its most important criterion, so everything else follows from it.

`hangman/game.py` **imports only `enum` and `string`** - no `print`, no `input`, no `open`, no
`random`, and nothing from this project. You can check that mechanically:

```bash
python -c "import ast,pathlib; print(sorted(n.names[0].name if isinstance(n,ast.Import) else n.module for n in ast.walk(ast.parse(pathlib.Path('hangman/game.py').read_text(encoding='utf-8'))) if isinstance(n,(ast.Import,ast.ImportFrom))))"
# ['enum', 'string']
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

### 5.7 Smaller choices

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
| - | At least 5 unit tests | Done - 36 tests |
| - | README | Done - this file |
| A1 | Difficulty easy/medium/hard | Done - modes 1/2/3, changes word length (assumption 7) |
| A2 | One hint per round, reveals a letter, costs a turn | Done - type `?` |
| A3 | Words grouped by topic, chosen by the player | Done - Animal / Food / All topics |
| A4, A5, A6 | Scoring, Vietnamese diacritics, GUI | Not done - see section 8 |

## 8. What I would do next

Roughly in priority order. None of the first three requires touching `game.py`, which is the
point of the layering:

- **ASCII gallows drawing.** Pure presentation, lives in `main.py`, picks one of 7 frames from
  `len(game.wrong_letters)`.
- **A4 - Scoring and a leaderboard.** A separate `score.py` with a pure
  `compute_score(game) -> int`, saved as JSON.
- **A6 - A web interface.** The core knows nothing about the console, so it is reusable as-is.
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
