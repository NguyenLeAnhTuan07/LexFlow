import csv
import os
import random
import json
import datetime
import pandas as pd

# Thư mục chứa backend — dùng làm gốc lưu tất cả file data
import sys as _sys
if getattr(_sys, 'frozen', False):
    BASE_DIR = os.path.dirname(_sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _data_path(filename):
    """Trả về đường dẫn tuyệt đối trong cùng thư mục với script."""
    return os.path.join(BASE_DIR, filename)

# ============================================================
# CONSTANTS
# ============================================================

REVIEW_STAGES = ["30min", "1day", "3day", "7day"]

REVIEW_INTERVALS = {
    "30min": datetime.timedelta(minutes=30),
    "1day" : datetime.timedelta(days=1),
    "3day" : datetime.timedelta(days=3),
    "7day" : datetime.timedelta(days=7),
}

NEXT_STAGE = {
    "30min": "1day",
    "1day" : "3day",
    "3day" : "7day",
    "7day" : "30min",
}

CSV_HEADERS  = ["word", "type", "meaning", "example", "translate_example"]
MISTAKE_FILE = _data_path("mistake.csv")
META_FILE    = _data_path("review_meta.json")


# ============================================================
# FILE HELPERS — dùng chung cho review + mistake
# ============================================================

def _norm(text):
    return str(text).strip().lower()


def _read_csv_dicts(path):
    """Đọc file CSV, trả về list of dict. Tự map cột dù header khác nhau."""
    if not os.path.exists(path):
        return []
    words = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Chuẩn hoá về cùng key set
            values = [v or "" for v in row.values()]
            while len(values) < 5:
                values.append("")
            words.append({
                "word"             : values[0].strip(),
                "type"             : values[1].strip(),
                "meaning"          : values[2].strip(),
                "example"          : values[3].strip(),
                "translate_example": values[4].strip(),
            })
    return words


def _write_csv_dicts(path, words):
    """Ghi toàn bộ list of dict ra file (overwrite)."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for w in words:
            writer.writerow({h: w.get(h, "") for h in CSV_HEADERS})


def _word_key(w):
    """Key duy nhất để so sánh trùng."""
    return (_norm(w.get("word", "")), _norm(w.get("meaning", "")))


def _append_unique(path, new_words):
    """
    Thêm new_words vào cuối path, bỏ qua từ đã có (so sánh word+meaning).
    Tạo file mới với header nếu chưa tồn tại.
    """
    existing = _read_csv_dicts(path)
    existing_keys = {_word_key(w) for w in existing}

    to_add = [w for w in new_words if _word_key(w) not in existing_keys]
    if not to_add:
        return 0

    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        for w in to_add:
            writer.writerow({h: w.get(h, "") for h in CSV_HEADERS})
    return len(to_add)


def _remove_word_from_file(path, word_dict):
    """Xóa 1 từ khỏi file (so sánh word+meaning)."""
    if not os.path.exists(path):
        return
    target = _word_key(word_dict)
    words  = _read_csv_dicts(path)
    new    = [w for w in words if _word_key(w) != target]
    _write_csv_dicts(path, new)


# ============================================================
# REVIEW FILE API
# ============================================================

def _load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_meta(meta):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _review_path(stage):
    return _data_path(f"review_{stage}.csv")


def add_words_to_review(words):
    """Học từ mới xong → thêm vào review_30min (bỏ trùng)."""
    added = _append_unique(_review_path("30min"), words)
    if added > 0:
        meta = _load_meta()
        if "30min_due" not in meta:
            due = datetime.datetime.now() + REVIEW_INTERVALS["30min"]
            meta["30min_due"] = due.isoformat()
            _save_meta(meta)
    return added


def finish_review_stage(stage, passed_words, failed_words):
    """
    Sau khi ôn xong stage:
    - passed → chuyển sang stage kế (bỏ trùng)
    - failed  → ở lại stage hiện tại (bỏ trùng)
    - Xóa file stage hiện tại, cập nhật meta
    """
    next_stage = NEXT_STAGE[stage]
    path       = _review_path(stage)

    # Xóa file stage hiện tại
    if os.path.exists(path):
        os.remove(path)

    meta = _load_meta()
    meta.pop(f"{stage}_due", None)
    _save_meta(meta)

    if passed_words:
        _append_unique(_review_path(next_stage), passed_words)
        meta = _load_meta()
        if f"{next_stage}_due" not in meta:
            due = datetime.datetime.now() + REVIEW_INTERVALS[next_stage]
            meta[f"{next_stage}_due"] = due.isoformat()
            _save_meta(meta)

    if failed_words:
        _append_unique(_review_path(stage), failed_words)
        meta = _load_meta()
        due  = datetime.datetime.now() + REVIEW_INTERVALS[stage]
        meta[f"{stage}_due"] = due.isoformat()
        _save_meta(meta)


def get_due_stages():
    meta = _load_meta()
    now  = datetime.datetime.now()
    due  = []
    for stage in REVIEW_STAGES:
        path  = _review_path(stage)
        words = _read_csv_dicts(path)
        if not words:
            continue
        key = f"{stage}_due"
        if key in meta:
            if now >= datetime.datetime.fromisoformat(meta[key]):
                due.append(stage)
        else:
            due.append(stage)
    return due


def get_stage_word_count(stage):
    return len(_read_csv_dicts(_review_path(stage)))


def get_review_summary():
    meta   = _load_meta()
    now    = datetime.datetime.now()
    result = {}
    for stage in REVIEW_STAGES:
        words    = _read_csv_dicts(_review_path(stage))
        due_key  = f"{stage}_due"
        due_time = None
        is_due   = False
        if due_key in meta:
            due_time = datetime.datetime.fromisoformat(meta[due_key])
            is_due   = now >= due_time
        elif words:
            is_due = True
        result[stage] = {"count": len(words), "due_time": due_time, "is_due": is_due}
    return result


# ============================================================
# MISTAKE FILE API
# ============================================================

def get_mistake_count():
    return len(_read_csv_dicts(MISTAKE_FILE))


def add_to_mistake(word_dict):
    """Thêm từ vào mistake.csv (bỏ trùng)."""
    _append_unique(MISTAKE_FILE, [word_dict])


def remove_from_mistake(word_dict):
    """Xóa từ khỏi mistake.csv."""
    _remove_word_from_file(MISTAKE_FILE, word_dict)


def add_back_to_mistake(word_dict):
    """
    Sai trong mistake mode → xóa vị trí cũ, thêm lại cuối file.
    Đảm bảo từ luôn ở cuối để ôn lại.
    """
    _remove_word_from_file(MISTAKE_FILE, word_dict)
    _append_unique(MISTAKE_FILE, [word_dict])


# ============================================================
# Stats
# ============================================================
STATS_FILE = _data_path("study_stats.json")


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_stat(correct):
    data  = load_stats()
    today = datetime.date.today().isoformat()
    if today not in data:
        data[today] = {"correct": 0, "wrong": 0}
    if correct:
        data[today]["correct"] += 1
    else:
        data[today]["wrong"] += 1
    save_stats(data)


def get_weekly_stats():
    data   = load_stats()
    result = []
    for i in range(6, -1, -1):
        d     = datetime.date.today() - datetime.timedelta(days=i)
        entry = data.get(d.isoformat(), {"correct": 0, "wrong": 0})
        result.append({"date": d.isoformat(), "label": d.strftime("%d/%m"),
                        "correct": entry["correct"], "wrong": entry["wrong"]})
    return result


def get_total_stats():
    data = load_stats()
    return sum(v["correct"] for v in data.values()), sum(v["wrong"] for v in data.values())


# ============================================================
# WordTrainer
# ============================================================

class WordTrainer:

    def __init__(self, filename, mode="random"):
        self.filename     = filename
        self.basename     = os.path.basename(filename).lower()
        self.mode         = mode

        # Xác định loại file
        self._review_stages = [f"review_{s}.csv" for s in REVIEW_STAGES]
        self._is_mistake    = (self.basename == MISTAKE_FILE)
        self._is_review     = (self.basename in self._review_stages)
        self._stage         = None
        for s in REVIEW_STAGES:
            if self.basename == f"review_{s}.csv":
                self._stage = s

        raw = self._read_file(filename)
        random.shuffle(raw)
        self.words         = raw
        self.current       = None
        self.current_mode  = None
        self.correct_count = 0
        self.wrong_count   = 0
        self.streak        = 0
        self.best_streak   = 0

        # Theo dõi kết quả session
        self._passed = []   # từ trả lời đúng (review/mới)
        self._failed = []   # từ trả lời sai  (review)

    # ── đọc file ──────────────────────────────
    def _read_file(self, filename):
        """Đọc CSV hoặc XLSX, chuẩn hoá về dict en/vi/pos/example/example_vi."""
        words = []
        if not os.path.exists(filename):
            return words
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(filename)
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(filename)
            else:
                return words
        except Exception:
            return words

        df = df.fillna("")
        for _, row in df.iterrows():
            cols = [str(row.iloc[i]).strip() if i < len(row) else "" for i in range(5)]
            en, pos, vi, ex, ex_vi = cols
            if en and vi:
                words.append({"en": en, "vi": vi, "pos": pos,
                               "example": ex, "example_vi": ex_vi})
        return words

    def _to_review_dict(self, w):
        return {"word": w["en"], "type": w["pos"], "meaning": w["vi"],
                "example": w["example"], "translate_example": w["example_vi"]}

    # ── core ──────────────────────────────────
    def normalize(self, text):
        return str(text).strip().lower()

    def choose_mode(self):
        if self.mode == "random":
            return random.choice(["en_vi", "vi_en"])
        return self.mode

    def next_word(self):
        if not self.words:
            return None
        self.current      = self.words.pop(0)
        self.current_mode = self.choose_mode()
        return self.current

    def get_question(self):
        if not self.current:
            return None
        if self.current_mode == "en_vi":
            return {"question": self.current["en"], "type": self.current["pos"], "answer": self.current["vi"]}
        return {"question": self.current["vi"], "type": self.current["pos"], "answer": self.current["en"]}

    def get_choices(self, all_words):
        q      = self.get_question()
        correct = q["answer"]
        if self.current_mode == "en_vi":
            pool = [w["vi"] for w in all_words if _norm(w["vi"]) != _norm(correct)]
        else:
            pool = [w["en"] for w in all_words if _norm(w["en"]) != _norm(correct)]
        wrong = random.sample(pool, min(3, len(pool)))
        choices = [{"text": correct, "correct": True}] + [{"text": w, "correct": False} for w in wrong]
        random.shuffle(choices)
        return choices

    def check_answer(self, answer):
        correct = self.normalize(self.get_question()["answer"])
        user    = self.normalize(answer)
        rd      = self._to_review_dict(self.current)

        if user == correct:
            self.correct_count += 1
            self.streak        += 1
            if self.streak > self.best_streak:
                self.best_streak = self.streak
            record_stat(True)
            self._passed.append(rd)

            if self._is_mistake:
                # Đúng trong mistake mode → xóa luôn khỏi file
                remove_from_mistake(rd)
            # Không thêm lại vào words (từ đúng thì bỏ qua)
            return True, self.current
        else:
            self.wrong_count += 1
            self.streak       = 0
            record_stat(False)
            self._failed.append(rd)

            # Luôn thêm vào mistake.csv (bỏ trùng)
            add_to_mistake(rd)

            if self._is_mistake:
                # Sai trong mistake mode → xóa vị trí cũ, thêm lại cuối
                add_back_to_mistake(rd)
                # Thêm lại vào queue để hỏi lại trong session
                self.words.append(self.current)
            else:
                # File thường → hỏi lại trong session
                self.words.append(self.current)

            return False, self.current

    def finish_session(self):
        """
        Gọi khi hết session.
        - Nếu học từ mới  → passed vào review_30min
        - Nếu ôn review   → gọi finish_review_stage
        - Nếu mistake mode → không làm gì thêm (đã xử lý real-time)
        """
        if self._is_mistake:
            return

        if self._is_review and self._stage:
            finish_review_stage(self._stage, self._passed, self._failed)
        else:
            # Học từ mới
            if self._passed:
                add_words_to_review(self._passed)