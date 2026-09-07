# Trò chơi Đoán chữ (Hangman)

Game đoán chữ chạy trên console, viết bằng Python thuần — **không cần cài thêm thư viện nào**.

Người chơi chọn **chủ đề** và **độ khó**, rồi đoán từng chữ cái của một từ bí mật được chọn ngẫu
nhiên. Đoán đúng thì mọi vị trí chứa chữ đó lộ ra và **không mất lượt**; đoán sai thì mất 1 lượt.
Mặc định (độ khó Trung bình) là tối đa **6 lần sai**.

---

## 1. Cài đặt & chạy

Yêu cầu: **Python 3.7 trở lên** (đã kiểm thử trên Python 3.11.8, Windows 10). Không có dependency.

```bash
cd BKCS_Test
python main.py
```

## 2. Chạy test

```bash
python -m unittest discover -s tests -t . -v
```

> Cờ `-t .` là bắt buộc: nó đặt thư mục gốc dự án làm top-level, nếu không `import hangman`
> bên trong test sẽ báo lỗi.

Hiện có **27 test**, vượt yêu cầu tối thiểu 5. Kết quả: `Ran 27 tests — OK`.

## 3. Cấu trúc dự án

```
BKCS_Test/
├── main.py                 # GIAO DIỆN — file DUY NHẤT có print() / input()
├── data/
│   └── words.json          # 90 từ, chia 2 chủ đề (animal / food)
├── hangman/
│   ├── game.py             # LOGIC THUẦN — không hề có print/input/file/random
│   └── words.py            # đọc file từ vựng, lọc theo chủ đề / độ khó, chọn ngẫu nhiên
└── tests/
    ├── test_game.py        # 15 test cho luật chơi
    └── test_words.py       # 12 test cho dữ liệu, chủ đề và độ khó
```

Chiều phụ thuộc — luôn đi một chiều, không có vòng lặp:

```
main.py  →  hangman/words.py  →  data/words.json
        ↘   hangman/game.py   (không import gì từ dự án)
```

## 4. Quyết định thiết kế

### 4.1 Tách biệt logic và giao diện (yêu cầu 3.2)

Đây là tiêu chí đề bài nhấn mạnh nhất, nên toàn bộ kiến trúc xoay quanh nó.

`hangman/game.py` **chỉ import `enum` và `string`** — không `print`, không `input`, không
`open`, không `random`, không import bất cứ module nào khác của dự án. Có thể kiểm chứng bằng máy:

```bash
python -c "import ast,pathlib; print(sorted(n.names[0].name if isinstance(n,ast.Import) else n.module for n in ast.walk(ast.parse(pathlib.Path('hangman/game.py').read_text(encoding='utf-8'))) if isinstance(n,(ast.Import,ast.ImportFrom))))"
# ['enum', 'string']
```

Hệ quả cụ thể: **toàn bộ 15 test luật chơi không cần mock `stdin`, không cần capture `stdout`,
không cần seed `random`** — chỉ việc `HangmanGame("python")` rồi gọi `guess()`. Nếu logic mà dính
`input()` thì không test được như vậy.

Lõi game giao tiếp với bên ngoài bằng cách **trả về `GuessResult`**, không phải bằng cách in ra:

```python
class GuessResult(Enum):
    CORRECT, WRONG, ALREADY_GUESSED, INVALID, GAME_OVER
```

`main.py` chỉ có một `dict` ánh xạ enum → câu tiếng Việt. Muốn đổi sang giao diện web hay
tiếng Anh chỉ cần thay `main.py`, `game.py` giữ nguyên không sửa một dòng.

### 4.2 Trạng thái được TÍNH, không được LƯU

`masked_word`, `remaining`, `state` đều là `@property` tính lại mỗi lần đọc từ hai nguồn duy nhất
là `_secret` và `_correct`:

```python
@property
def masked_word(self):
    return "".join(c if c in self._correct else "_" for c in self._secret)
```

Lý do: nếu lưu sẵn một chuỗi hiển thị rồi cập nhật dần thì có **hai nguồn sự thật** cho cùng một
thông tin, rất dễ lệch nhau — đặc biệt với từ có chữ lặp như `letter`. Cách tính trực tiếp khiến
"lộ ra **mọi** vị trí chứa chữ cái đó" là hệ quả tự nhiên, không phải thứ phải xử lý riêng.

Tương tự, `remaining` đếm số chữ cái **khác nhau** chưa lộ (`len(set(secret) - correct)`), không
đếm theo vị trí — nếu đếm theo vị trí thì `letter` (6 ký tự nhưng chỉ 4 chữ khác nhau) sẽ không
bao giờ thắng đúng lúc.

### 4.3 Kiểm tra input nằm trong logic, không nằm ở giao diện

`main.py` **không có một dòng luật chơi nào**: không `len(x) != 1`, không kiểm tra bảng chữ cái.
Nó đọc chuỗi thô rồi đưa thẳng cho `game.guess()`.

Nếu đặt phần kiểm tra ở giao diện thì F3 ("input sai không được trừ lượt") chỉ là bảo đảm của
tầng UI — không test được nếu không giả lập bàn phím, và sẽ bị vi phạm ngay khi có người gọi
lõi game từ chỗ khác. Đặt trong `guess()` thì bảo đảm đó đúng với **mọi** caller, và
`test_invalid_input_never_costs_a_life` chỉ dài vài dòng.

Mọi nhánh từ chối đều `return` **trước khi** chạm vào `_lives` hay `_correct`, nên về mặt cấu trúc
là không thể trừ nhầm lượt.

### 4.4 Danh sách từ nằm ngoài code (F1)

`data/words.json` chứa 80 từ, gom theo chủ đề:

```json
{ "animal": ["cat", "dog", ...], "food": ["egg", "rice", ...] }
```

Chỉ là dữ liệu thuần, **không gắn nhãn độ khó** — độ khó sẽ suy ra từ `len(word)` lúc chạy, nên
thêm từ mới vào file là tự động vào đúng nhóm, không phải sửa gì thêm.

`hangman/words.py` lọc dữ liệu ngay lúc nạp: bỏ từ rỗng, từ có khoảng trắng / dấu / gạch nối, và
khử trùng lặp. Đây không phải chuyện thẩm mỹ: một từ như `"ice cream"` sẽ khiến ván đấu **không
bao giờ thắng được** vì người chơi không thể gõ dấu cách. Ngoài ra `HangmanGame.__init__` cũng
raise `ValueError` nếu nhận từ bẩn — chặn hai lớp, và `test_every_word_builds_a_playable_game`
kiểm tra tự động rằng **mọi** từ trong file đều thắng được.

### 4.5 Độ khó (A1) và chủ đề (A3) nằm ở tầng dữ liệu

Cả hai được cài đặt **không sửa một dòng nào trong `game.py`** — có thể kiểm chứng bằng
`git show --stat` của commit thêm hai tính năng này: `game.py` không có mặt trong danh sách file
thay đổi. Đây là bằng chứng cụ thể nhất cho thấy việc tách lớp có giá trị thật.

Lý do: chọn từ nào để chơi là **chính sách chọn từ**, không phải luật chơi. Nên bảng độ khó nằm
trong `words.py`:

| Mode | Độ khó | Độ dài từ | Số lượt sai | Số từ mỗi chủ đề |
|---|---|---|---|---|
| 1 | Dễ | 3–5 chữ cái | 6 | 24 |
| 2 | Trung bình | 6–8 chữ cái | 6 | 13 |
| 3 | Khó | ≥9 chữ cái | 6 | 8 |

**Độ khó chỉ đổi độ dài từ, không đổi số lượt** — mọi chế độ đều đúng 6 lượt sai như luật gốc ở
mục 2.4 của đề bài. Vì vậy `Difficulty` không hề có trường `lives`; giữ một trường luôn bằng 6 chỉ
là thừa và dễ gây hiểu nhầm là nó thay đổi được. Có
`test_difficulty_changes_word_length_only_not_lives` chốt điều này.

Chủ đề thì `data/words.json` đã gom sẵn, chỉ cần thêm menu ở `main.py`.

Độ khó **suy ra từ `len(word)` lúc chạy**, file dữ liệu không gắn nhãn độ khó. Thêm một từ mới vào
`words.json` là nó tự vào đúng nhóm, không phải sửa gì thêm. Có
`test_every_topic_and_difficulty_bucket_has_words` kiểm tra mọi tổ hợp (chủ đề × độ khó) đều còn
từ, để `random_word()` không bao giờ rơi vào tình huống chọn từ một danh sách rỗng.

Tên chủ đề hiển thị bằng tiếng Việt qua `TOPIC_LABELS` trong `main.py` (chuyện trình bày thì để ở
tầng trình bày). Chủ đề nào chưa có nhãn vẫn chạy bình thường, chỉ hiện tên gốc — nên thêm chủ đề
mới vẫn chỉ là sửa dữ liệu.

### 4.6 Vài chi tiết nhỏ nhưng có chủ đích

- **`guess()` nhận mọi kiểu dữ liệu.** `game.guess(None)` trả `INVALID` chứ không ném
  `AttributeError`. F3 nói "không được crash", nên lõi không nên sập vì một giá trị lạ.
- **`state` kiểm tra THẮNG trước THUA.** Đoán đúng chữ cuối cùng khi chỉ còn 1 lượt là thắng.
  Thứ tự này sẽ càng quan trọng nếu sau này thêm gợi ý (vừa mở chữ vừa trừ lượt).
- **Các property trả về bản sao** (`list(self._wrong)`), nên giao diện không thể vô tình phá
  trạng thái game. Có `test_properties_return_copies` để chốt.
- **Sửa encoding cho console Windows.** `main.py` gọi `sys.stdout.reconfigure(encoding="utf-8")`.
  Nếu không, `cmd.exe` dùng codepage mặc định sẽ ném `UnicodeEncodeError` khi in tiếng Việt có
  dấu — với người chấm thì đó trông y hệt một cú crash.
- **Chơi lại tạo `HangmanGame` mới** thay vì `reset()` đối tượng cũ, tránh sót trạng thái cũ.

## 5. Giả định (những điểm đề bài không nói rõ)

1. **Input được `.strip()` trước khi xử lý.** Gõ `" a "` vẫn tính là đoán `a` (lỡ chạm phím cách).
   Còn chuỗi chỉ toàn khoảng trắng thì sau khi strip là rỗng → không hợp lệ, đúng như đề yêu cầu.
2. **Chỉ đoán từng chữ cái, không đoán cả từ.** Đề bài mục 2.3 ghi "đoán từng chữ cái".
3. **Từ vựng chỉ gồm `a-z` không dấu**, mỗi từ là một token liền, không khoảng trắng/gạch nối.
4. **Điều kiện thắng đếm theo chữ cái khác nhau**, không theo số ký tự.
5. **Gõ lại chữ đã đoán** (dù trước đó đúng hay sai) đều tính là "đã đoán rồi" và không trừ lượt.
6. **Câu hỏi chơi lại** nhận `c`/`k` (có/không), cũng chấp nhận `y`/`n`. Trả lời sai thì hỏi lại
   chứ không thoát.
7. **Số lượt sai luôn là 6 ở mọi độ khó.** Đề bài mục 2.4 quy định tối đa 6 lượt sai, còn A1 lại
   gợi ý độ khó "ảnh hưởng tới số lượt được phép" — hai chỗ này mâu thuẫn nhau. Tôi chọn giữ
   đúng luật gốc: **6 lượt cho mọi chế độ**, độ khó chỉ ảnh hưởng độ dài từ.
8. **Chọn lại chủ đề và độ khó ở mỗi ván mới**, thay vì giữ nguyên lựa chọn cũ.

## 6. Đối chiếu yêu cầu

| # | Yêu cầu | Trạng thái |
|---|---|---|
| F1 | Từ ngẫu nhiên từ danh sách ≥30 từ, ở file riêng | ✅ 90 từ trong `data/words.json` |
| F2 | Hiển thị trạng thái từ, chữ đã đoán, lượt còn lại | ✅ `render_status()` |
| F3 | Input không hợp lệ: không trừ lượt, không crash | ✅ rỗng / >1 ký tự / không phải chữ cái / đã đoán rồi |
| F4 | Không phân biệt hoa thường | ✅ `.lower()` trước khi kiểm tra |
| F5 | Báo thắng/thua + hiện từ bí mật + hỏi chơi lại | ✅ hiện từ bí mật ở **cả hai** trường hợp |
| 3.2 | Tách logic khỏi giao diện | ✅ `game.py` chỉ import `enum`, `string` |
| — | ≥5 unit test | ✅ 27 test |
| — | README | ✅ file này |
| A1 | Độ khó Dễ/Trung bình/Khó | ✅ mode 1/2/3, ảnh hưởng độ dài từ (xem giả định 7) |
| A3 | Phân nhóm từ vựng theo chủ đề, cho người chơi chọn | ✅ Động vật / Đồ ăn / Tất cả |
| A2, A4, A5, A6 | Gợi ý, điểm số, tiếng Việt có dấu, giao diện đồ hoạ | ❌ chưa làm, xem mục 7 |

## 7. Nếu có thêm thời gian

Ưu tiên theo thứ tự, và điều đáng nói là **hầu hết đều không cần sửa `game.py`** — đó chính là
bằng chứng việc tách lớp có giá trị thật chứ không chỉ để cho đẹp:

- **Hình ASCII giá treo cổ.** Thuần trình bày, đặt ở `main.py`, chọn khung hình theo số lần đoán
  sai (`len(game.wrong_letters)`, từ 0 đến 6). Không cần sửa `game.py`.
- **A2 — Gợi ý.** Đây là mục duy nhất phải đụng vào lõi: thêm `hint(rng)` mở 1 chữ chưa lộ và trừ
  1 lượt. Cần truyền `rng` vào làm tham số để `game.py` vẫn test được tất định.
- **A4 — Điểm số & bảng xếp hạng.** Một `score.py` riêng với hàm thuần
  `compute_score(game) -> int`, lưu JSON.
- **A5 — Tiếng Việt có dấu.** Cách xử lý dự định: chuẩn hoá `unicodedata.normalize("NFC", ...)` để
  `ế` là **một** code point thay vì `e` + dấu tổ hợp (nếu không, `len()` và việc so khớp sẽ sai).
  Sẽ so khớp **có phân biệt dấu** (`e`, `é`, `ê`, `ề` là bốn chữ khác nhau) vì đó là kỳ vọng tự
  nhiên của người chơi Việt; `đ` tính là chữ riêng, khác `d`. Các chữ ghép `ch`, `ng`, `nh` vẫn
  gõ từng ký tự một. Về code thì thay đổi rất nhỏ nhờ kiến trúc hiện tại: `ALPHABET` chuyển thành
  tham số của constructor (`HangmanGame(secret, alphabet=VIETNAMESE_ALPHABET)`) cộng thêm một file
  `data/words_vi.json` cùng schema.
- **A6 — Giao diện web.** Lõi vốn đã không biết gì về console nên dùng lại được nguyên vẹn; chỉ
  viết lớp hiển thị mới thay cho `main.py`.

## 8. Sử dụng công cụ AI

Có sử dụng **Claude (Claude Code)** trong quá trình làm bài, cụ thể:

- Bàn kiến trúc và rà soát bản thiết kế nháp ban đầu của tôi. AI chỉ ra vài lỗi trong pseudocode
  tôi phác thảo trước đó, đáng kể nhất là: nhánh trừ lượt nếu đặt **bên trong** vòng `for` duyệt
  từng vị trí sẽ trừ một lượt cho **mỗi** vị trí không khớp (đoán sai 1 lần là mất luôn 6 lượt);
  tập `avail` nếu chỉ trừ đi các chữ đoán **sai** thì chữ đã đoán **đúng** vẫn được đoán lại; và
  việc gán `now[i] = letter` sẽ lỗi vì string trong Python là immutable.
- Sinh khung code và bộ test theo thiết kế đã chốt.
- Soạn thảo file README này.

Phần ý tưởng luật chơi, cấu trúc dữ liệu (`point`/`remain`/`flag`, whitelist chữ cái, chia chủ đề
food/animal) là của tôi. Tôi đã đọc, hiểu và kiểm chứng lại toàn bộ code trong repo này và có thể
giải thích từng dòng.
