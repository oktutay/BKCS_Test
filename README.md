# Hangman

A console word-guessing game in plain Python — **no third-party packages required**.

The player picks a **topic** and a **difficulty**, then guesses the secret word one letter at a
time. A correct guess reveals every position holding that letter and **costs nothing**; a wrong
guess costs one life. **6 wrong guesses** are allowed, in every difficulty.

---

## 1. Install & run

Requires **Python 3.7+** (tested on Python 3.11.8, Windows 10). No dependencies.

```bash
cd BKCS_Test
python main.py
```

## 2. Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

> The `-t .` flag is required: it makes the project root the top-level directory. Without it,
> `unittest` treats `tests/` as the root and `import hangman` inside the tests fails.

**37 tests**, against the required minimum of 5. Result: `Ran 37 tests — OK`.

## 3. Project layout

```
BKCS_Test/
├── main.py                 # INTERFACE — the only file that calls print() / input()
├── data/
│   └── words.json          # 90 words in 2 topics (animal / food)
├── hangman/
│   ├── game.py             # PURE LOGIC — no print/input/file access, no `import random`
│   └── words.py            # loads the word file, filters by topic/difficulty, picks a word
└── tests/
    ├── test_game.py        # 24 tests for the rules (including the hint)
    └── test_words.py       # 13 tests for the word data, topics and difficulty
```

The dependency direction is one-way, with no cycles:

```
main.py  →  hangman/words.py  →  data/words.json
        ↘   hangman/game.py   (imports nothing from this project)
```

## 4. Design decisions

### 4.1 Separating the logic from the interface (requirement 3.2)

The assignment calls this its most important criterion, so the whole architecture is built
around it.

`hangman/game.py` **imports only `enum` and `string`** — no `print`, no `input`, no `open`, no
`random`, and nothing from this project. That is checkable mechanically:

```bash
python -c "import ast,pathlib; print(sorted(n.names[0].name if isinstance(n,ast.Import) else n.module for n in ast.walk(ast.parse(pathlib.Path('hangman/game.py').read_text(encoding='utf-8'))) if isinstance(n,(ast.Import,ast.ImportFrom))))"
# ['enum', 'string']
```

The concrete payoff: **the rule tests need no mocked `stdin`, no captured `stdout` and no
patched `random`** — they just build `HangmanGame("python")` and call `guess()`. Logic tangled up
with `input()` cannot be tested that way.

The core reports to the outside world by **returning a `GuessResult`**, never by printing:

```python
class GuessResult(Enum):
    CORRECT, WRONG, ALREADY_GUESSED, INVALID, GAME_OVER, HINT, HINT_UNAVAILABLE
```

`main.py` is then just a `dict` mapping each enum member to a sentence. Swapping in a web UI or
another language means rewriting `main.py` and leaving `game.py` untouched.

### 4.2 State is DERIVED, never STORED

`masked_word`, `remaining` and `state` are all `@property` values recomputed on every read from
the only two things actually stored, `_secret` and `_correct`:

```python
@property
def masked_word(self):
    return "".join(c if c in self._correct else "_" for c in self._secret)
```

Keeping a display string and mutating it in place would mean **two sources of truth** for one
fact, and they drift — especially on words with repeated letters like `letter`. Deriving it makes
"reveal *every* position holding that letter" fall out for free instead of being a special case.

Likewise `remaining` counts **distinct** letters still hidden (`len(set(secret) - correct)`)
rather than positions. Counting positions would mean `letter` — 6 characters but only 4 distinct
letters — never wins at the right moment.

### 4.3 Input validation belongs to the logic, not the interface

`main.py` contains **no game rules at all**: no `len(x) != 1`, no alphabet check. It reads a raw
string and hands it straight to `game.guess()`.

Put the validation in the UI instead and F3 ("invalid input must not cost a life") becomes a
guarantee of the *interface* — untestable without simulating a keyboard, and void the moment
anything else calls the core. Inside `guess()`, it holds for **every** caller, and
`test_invalid_input_never_costs_a_life` is a few lines long.

Every rejection path returns **before** touching `_lives` or `_correct`, so losing a life by
accident is structurally impossible.

### 4.4 The word list lives outside the code (F1)

`data/words.json` holds 90 words grouped by topic:

```json
{ "animal": ["cat", "dog", ...], "food": ["egg", "rice", ...] }
```

It is pure data with **no difficulty tags** — difficulty is derived from `len(word)` at runtime,
so adding a word drops it into the right bucket with no other change.

`hangman/words.py` filters the data as it loads: empty entries, words with spaces, accents or
hyphens, and duplicates are all dropped. This is not tidiness. A word like `"ice cream"` would
make a round **unwinnable**, because the player can never type a space. `HangmanGame.__init__`
also raises `ValueError` on a malformed word — two layers — and
`test_every_word_builds_a_playable_game` checks automatically that **every** word in the file can
actually be won.

### 4.5 Difficulty (A1) and topics (A3) live in the data layer

Both were added **without changing a single line of `game.py`** — verifiable in
`git show --stat` for that commit, where `game.py` simply does not appear among the changed
files. That is the most concrete evidence the separation is real rather than decorative.

The reason: *which* word to play is a **word-selection policy**, not a rule of the game. So the
difficulty table sits in `words.py`:

| Mode | Difficulty | Word length | Lives | Words per topic |
|---|---|---|---|---|
| 1 | Easy | 3–5 letters | 6 | 24 |
| 2 | Medium | 6–8 letters | 6 | 13 |
| 3 | Hard | 9+ letters | 6 | 8 |

**Difficulty changes the word length only, never the number of lives** — every mode keeps the 6
wrong guesses from rule 2.4. `Difficulty` therefore has no `lives` field at all: a field that is
always 6 would only suggest it can vary. `test_difficulty_changes_word_length_only_not_lives`
pins that down.

Topic names are read straight from the data file and shown capitalised, so adding a topic stays a
data-only change with no code edit.

### 4.6 The hint (A2), and how it stays out of the core's way

One hint per round, in every difficulty. It reveals one **random letter that is still hidden**
and costs one life.

This is the one feature that genuinely needs randomness inside the rules, which would normally
force `import random` into `game.py` and break the claim in §4.1. Instead the caller supplies the
random source:

```python
def hint(self, rng):
    ...
    self._correct.add(rng.choice(hidden))
```

`main.py` passes the `random` module; the tests pass `random.Random(0)`. So the **rules** stay in
the core (one per round, costs a life, only picks hidden letters) while the **source of
randomness** is the caller's business. `game.py` still imports nothing but `enum` and `string`,
and the hint tests are fully deterministic.

This is also where the win-before-lose ordering in `state` earns its keep: a hint that reveals the
last letter *and* spends the last life is a **win**, not a loss.
`test_hint_completing_the_word_on_the_last_life_is_a_win` covers it.

### 4.7 Smaller deliberate details

- **`guess()` accepts any type.** `game.guess(None)` returns `INVALID` rather than raising
  `AttributeError`. F3 says "must not crash", so an odd value should not take the core down.
- **`state` checks WIN before LOSS.** Guessing the final letter on your last life wins.
- **Properties return copies** (`list(self._wrong)`), so the interface cannot corrupt game state
  by accident. `test_properties_return_copies` locks it in.
- **Output is pure ASCII**, which sidesteps the Windows console codepage problem entirely — no
  `UnicodeEncodeError`, no `chcp` juggling, nothing for the reviewer to configure.
- **`fgets`-style input handling**: `read_line()` catches `EOFError`/`KeyboardInterrupt` so Ctrl+C
  or a closed pipe exits with "Goodbye!" instead of a traceback.
- **Replaying builds a new `HangmanGame`** instead of resetting the old one, so no state leaks
  between rounds.

## 5. Assumptions (points the assignment left open)

1. **Input is `.strip()`ed before use.** `" a "` counts as guessing `a` (an accidental space
   should not be punished). A string of only spaces becomes empty and is rejected, as required.
2. **Letters only, never whole words** — rule 2.3 says "guesses one letter at a time".
3. **Words are lowercase `a-z`**, single tokens, no spaces or hyphens.
4. **Winning is measured in distinct letters**, not character count.
5. **Re-guessing any letter** — right or wrong — counts as "already guessed" and costs nothing.
6. **The replay prompt** accepts `y`/`n`; anything else re-asks instead of quitting.
7. **Lives are always 6, in every difficulty.** Rule 2.4 caps wrong guesses at 6 while A1 suggests
   difficulty should affect the number of turns allowed; the two conflict. I kept the stated rule
   and let difficulty affect word length only.
8. **Topic and difficulty are chosen again for each new round**, rather than carried over.
9. **The hint costs one life even if it reveals the last letter** (the round is still won), and an
   already-spent hint costs nothing when re-requested.

## 6. Requirements checklist

| # | Requirement | Status |
|---|---|---|
| F1 | Random word from a list of ≥30, in a separate file | ✅ 90 words in `data/words.json` |
| F2 | Show word state, guessed letters, lives remaining | ✅ `render_status()` |
| F3 | Invalid input costs no life and does not crash | ✅ empty / >1 char / non-letter / repeat |
| F4 | Case-insensitive | ✅ `.lower()` before the alphabet check |
| F5 | Announce win/loss + reveal the word + offer a replay | ✅ the word is shown in **both** cases |
| 3.2 | Logic separated from the interface | ✅ `game.py` imports only `enum`, `string` |
| — | ≥5 unit tests | ✅ 37 tests |
| — | README | ✅ this file |
| A1 | Difficulty easy/medium/hard | ✅ modes 1/2/3, affects word length (see assumption 7) |
| A2 | One hint per round, reveals a letter, costs a turn | ✅ type `?` |
| A3 | Words grouped by topic, chosen by the player | ✅ Animal / Food / All topics |
| A4, A5, A6 | Scoring, Vietnamese diacritics, GUI | ❌ not done — see §7 |

## 7. What I would do next

Roughly in priority order. Worth noting that **none of the first three require touching
`game.py`**, which is the point of the layering:

- **ASCII gallows drawing.** Pure presentation, lives in `main.py`, picks a frame from
  `len(game.wrong_letters)` (0–6).
- **A4 — Scoring and a leaderboard.** A separate `score.py` with a pure
  `compute_score(game) -> int`, persisted as JSON.
- **A6 — A web interface.** The core knows nothing about the console, so it is reusable as-is;
  only the presentation layer would be new.
- **A5 — Vietnamese words with diacritics.** The approach I would take: normalise with
  `unicodedata.normalize("NFC", ...)` so `ế` is a **single** code point rather than `e` plus a
  combining accent — otherwise both `len()` and letter matching are wrong. I would match
  **diacritic-sensitively** (`e`, `é`, `ê`, `ề` are four different letters), since that is what a
  Vietnamese player expects, and treat `đ` as distinct from `d`. Digraphs like `ch`, `ng`, `nh`
  would still be typed one character at a time. The code change is small thanks to the current
  design: `ALPHABET` becomes a constructor argument
  (`HangmanGame(secret, alphabet=VIETNAMESE_ALPHABET)`) plus a `data/words_vi.json` in the same
  schema.

## 8. Use of AI tools

I used **Claude (Claude Code)** while working on this, specifically:

- Discussing the architecture and reviewing my initial draft design. It caught several bugs in the
  pseudocode I had sketched beforehand. The most serious: putting the life-deduction branch
  **inside** the `for` loop that scans each position deducts one life per *non-matching position*,
  so a single wrong guess on a 6-letter word would have ended the game immediately. Also, an
  `available` set built by subtracting only the **wrong** guesses still lets the player re-guess
  letters they already got **right**; and assigning `now[i] = letter` fails outright, because
  Python strings are immutable.
- Generating the code skeleton and the test suite from the agreed design.
- Drafting this README.

The game rules, the data model (`point`/`remain`/`flag`, the letter whitelist, the food/animal
topic split) were my own. I have read, understood and verified every line in this repository and
can explain any of it.
