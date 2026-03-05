import csv
import os
import random
import pandas as pd


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

    # =========================
    # đọc csv bằng pandas
    # =========================
    def read_csv(self, filename):

        words = []

        if not os.path.exists(filename):
            return words

        # pandas tự nhận định dạng
        if filename.endswith(".csv"):
            df = pd.read_csv(filename)

        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(filename)

        else:
            return words

        # sửa lỗi NaN của pandas
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

            words.append({
                "en": english,
                "vi": vietnamese,
                "pos": pos,
                "example": example,
                "example_vi": example_vi
            })

        return words

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

    # =========================
    # thêm mistake
    # =========================
    def add_mistake(self):

        if self.basename == "mistake.csv":
            return

        filename = "mistake.csv"

        file_exists = os.path.exists(filename)

        with open(filename, "a", newline="", encoding="utf-8-sig") as f:

            writer = csv.writer(f)

            # nếu file chưa tồn tại -> tạo header
            if not file_exists:
                writer.writerow([
                    "english",
                    "pos",
                    "vietnamese",
                    "example",
                    "example_vi"
                ])

            writer.writerow([
                self.current["en"],
                self.current["pos"],
                self.current["vi"],
                self.current["example"],
                self.current["example_vi"]
            ])

    # =========================
    # xóa mistake
    # =========================
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

    # =========================
    # check answer
    # =========================
    def check_answer(self, answer):

        correct = self.normalize(self.get_question()["answer"])
        user = self.normalize(answer)

        if user == correct:

            self.correct_count += 1

            if self.basename == "mistake.csv":
                self.remove_mistake()

            return True, self.current

        else:

            self.wrong_count += 1

            self.words.append(self.current)

            self.add_mistake()

            return False, self.current