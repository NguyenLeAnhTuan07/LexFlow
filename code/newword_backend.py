import csv
import os
import random
import json
import datetime
import pandas as pd


# ============================================================
# SRS (Spaced Repetition System) - lưu trạng thái từng từ
# ============================================================
SRS_FILE = "srs_data.json"

SRS_INTERVALS = [1, 3, 7, 14, 30]  # phút giữa các lần ôn


def load_srs_data():
    if os.path.exists(SRS_FILE):
        with open(SRS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_srs_data(data):
    with open(SRS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_srs_key(word):
    return f"{word['en']}|{word['vi']}"


def update_srs(word, correct):
    data = load_srs_data()
    key = get_srs_key(word)

    entry = data.get(key, {"level": 0, "next_review": None, "correct": 0, "wrong": 0})

    if correct:
        entry["level"] = min(entry["level"] + 1, len(SRS_INTERVALS) - 1)
        entry["correct"] = entry.get("correct", 0) + 1
    else:
        entry["level"] = max(entry["level"] - 1, 0)
        entry["wrong"] = entry.get("wrong", 0) + 1

    interval_minutes = SRS_INTERVALS[entry["level"]]
    next_time = datetime.datetime.now() + datetime.timedelta(minutes=interval_minutes)
    entry["next_review"] = next_time.isoformat()

    data[key] = entry
    save_srs_data(data)

    return interval_minutes


def get_srs_level(word):
    data = load_srs_data()
    key = get_srs_key(word)
    return data.get(key, {}).get("level", 0)


# ============================================================
# Stats tracking - lưu lịch sử học theo ngày
# ============================================================
STATS_FILE = "study_stats.json"


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_stat(correct):
    data = load_stats()
    today = datetime.date.today().isoformat()

    if today not in data:
        data[today] = {"correct": 0, "wrong": 0, "sessions": 0}

    if correct:
        data[today]["correct"] += 1
    else:
        data[today]["wrong"] += 1

    save_stats(data)


def get_weekly_stats():
    data = load_stats()
    result = []
    for i in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        entry = data.get(day, {"correct": 0, "wrong": 0})
        result.append({
            "date": day,
            "label": (datetime.date.today() - datetime.timedelta(days=i)).strftime("%d/%m"),
            "correct": entry["correct"],
            "wrong": entry["wrong"]
        })
    return result


def get_total_stats():
    data = load_stats()
    total_correct = sum(v["correct"] for v in data.values())
    total_wrong = sum(v["wrong"] for v in data.values())
    return total_correct, total_wrong


# ============================================================
# WordTrainer - core logic
# ============================================================

class WordTrainer:

    def __init__(self, filename, mode="random"):

        self.filename = filename
        self.basename = os.path.basename(filename).lower()
        self.mode = mode

        self.words = self.read_csv(filename)

        random.shuffle(self.words)

        self.current = None
        self.current_mode = None

        self.correct_count = 0
        self.wrong_count = 0

        # streak
        self.streak = 0
        self.best_streak = 0

    # -------------------------
    def read_csv(self, filename):

        words = []

        if not os.path.exists(filename):
            return words

        if filename.endswith(".csv"):
            df = pd.read_csv(filename)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(filename)
        else:
            return words

        df = df.fillna("")

        for _, row in df.iterrows():

            english = str(row.iloc[0]).strip()
            pos = str(row.iloc[1]).strip()
            vietnamese = str(row.iloc[2]).strip()

            example = ""
            example_vi = ""

            if len(row) >= 4:
                example = str(row.iloc[3]).strip()
            if len(row) >= 5:
                example_vi = str(row.iloc[4]).strip()

            if english and vietnamese:
                words.append({
                    "en": english,
                    "vi": vietnamese,
                    "pos": pos,
                    "example": example,
                    "example_vi": example_vi
                })

        return words

    # -------------------------
    def normalize(self, text):
        return text.strip().lower()

    def choose_mode(self):
        if self.mode == "random":
            return random.choice(["en_vi", "vi_en"])
        return self.mode

    def next_word(self):
        if not self.words:
            return None
        self.current = self.words.pop(0)
        self.current_mode = self.choose_mode()
        return self.current

    def get_question(self):
        if not self.current:
            return None
        if self.current_mode == "en_vi":
            return {
                "question": self.current["en"],
                "type": self.current["pos"],
                "answer": self.current["vi"]
            }
        else:
            return {
                "question": self.current["vi"],
                "type": self.current["pos"],
                "answer": self.current["en"]
            }

    # -------------------------
    # Multiple choice: lấy 4 đáp án (1 đúng + 3 sai ngẫu nhiên)
    # -------------------------
    def get_choices(self, all_words):
        """
        all_words: toàn bộ danh sách từ (để lấy đáp án sai)
        Trả về list 4 dict {"text": ..., "correct": bool}
        """
        q = self.get_question()
        correct_answer = q["answer"]

        # lấy pool đáp án sai
        if self.current_mode == "en_vi":
            pool = [w["vi"] for w in all_words if w["vi"] != correct_answer]
        else:
            pool = [w["en"] for w in all_words if w["en"] != correct_answer]

        wrong_choices = random.sample(pool, min(3, len(pool)))

        choices = [{"text": correct_answer, "correct": True}]
        for w in wrong_choices:
            choices.append({"text": w, "correct": False})

        random.shuffle(choices)
        return choices

    # -------------------------
    def check_answer(self, answer):

        correct = self.normalize(self.get_question()["answer"])
        user = self.normalize(answer)

        if user == correct:

            self.correct_count += 1
            self.streak += 1
            if self.streak > self.best_streak:
                self.best_streak = self.streak

            record_stat(True)
            interval = update_srs(self.current, True)

            if self.basename == "mistake.csv":
                self.remove_mistake()

            return True, self.current, interval

        else:

            self.wrong_count += 1
            self.streak = 0

            self.words.append(self.current)
            self.add_mistake()

            record_stat(False)
            update_srs(self.current, False)

            return False, self.current, 0

    # -------------------------
    def get_srs_info(self):
        if not self.current:
            return 0
        return get_srs_level(self.current)

    # -------------------------
    def add_mistake(self):

        if self.basename == "mistake.csv":
            return

        filename = "mistake.csv"
        file_exists = os.path.exists(filename)

        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["english", "pos", "vietnamese", "example", "example_vi"])
            writer.writerow([
                self.current["en"],
                self.current["pos"],
                self.current["vi"],
                self.current["example"],
                self.current["example_vi"]
            ])

    def remove_mistake(self):

        if not os.path.exists("mistake.csv"):
            return

        new_rows = []

        with open("mistake.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3:
                    continue
                if (
                    self.normalize(row[0]) == self.normalize(self.current["en"])
                    and
                    self.normalize(row[2]) == self.normalize(self.current["vi"])
                ):
                    continue
                new_rows.append(row)

        with open("mistake.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)
