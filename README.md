<div align="center">

# ⚡ LexFlow

**A modern vocabulary learning & quiz practice application built with Python**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-latest-green?style=flat-square)
![Pandas](https://img.shields.io/badge/Pandas-latest-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

*Chúc mọi người học tốt 🚀 — by Nguyễn Lê Anh Tuấn*

</div>

---

## 📖 Overview

**LexFlow** is a desktop application designed to help users learn English vocabulary and practice multiple-choice quizzes — built with a clean, modern dark-mode interface powered by [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

Whether you're studying for an exam or building your own question sets, LexFlow keeps everything organized in simple `.csv` / `.xlsx` files that you fully control.

---

## ✨ Features

### 📚 Vocabulary Learning
- Load vocabulary from `.csv` or `.xlsx` files
- Three learning modes: **Random**, **English → Vietnamese**, **Vietnamese → English**
- Two quiz styles: **Typing** and **Multiple Choice**
- Streak counter, accuracy tracking, and session summary
- Wrong answers automatically saved to `mistake.csv` for targeted review

### ⏰ Spaced Repetition System (SRS)
- Learned words are automatically queued for review at: **30 min → 1 day → 3 days → 7 days**
- On app startup, a popup reminds you when reviews are due
- Correct reviews advance to the next stage; wrong answers stay and repeat
- After completing all 7-day reviews, the cycle restarts from 30 min

### 📝 Multiple-Choice Quiz
- Load quiz questions from `.csv` or `.xlsx` files
- Select the number of questions via a slider (up to 150)
- Optional **countdown timer** per question (customizable seconds)
- Answer options (A/B/C/D) keep their labels but **shuffle content** each round
- Wrong answers saved to `quiz_mistakes.csv`; correct answers in mistake mode remove the entry

### ✏️ Add Vocabulary
- Create a new `.csv` file or append to an existing one
- 5 input fields: **Word · Type · Meaning · Example · Translated Example**
- Press `Enter` / `Tab` to jump between fields; last field auto-saves
- Duplicate detection before saving
- Live preview table shows all words in the loaded file

### ➕ Add Quiz Questions
- Create a new quiz file or open an existing one
- 6 input fields: **Question · Answer (A/B/C/D) · A · B · C · D**
- Validates that `Answer` is one of A, B, C, D
- Duplicate detection and live preview table

### 📊 Statistics
- Bar chart showing correct/wrong answers for the **last 7 days**
- All-time totals displayed in the stats popup

---

## 🗂️ File Formats

### Vocabulary File (`.csv` / `.xlsx`)
| word | type | meaning | example | translate_example |
|------|------|---------|---------|-------------------|
| run | v. | chạy | I run every day. | Tôi chạy mỗi ngày. |
| book | n. | quyển sách | I read a book. | Tôi đọc một quyển sách. |

### Quiz File (`.csv` / `.xlsx`)
| question | answer | A | B | C | D |
|----------|--------|---|---|---|---|
| 2 + 2 = ? | B | 3 | 4 | 5 | 6 |
| Capital of France? | C | Berlin | Rome | Paris | Madrid |

> **Note:** The `answer` column must contain **A**, **B**, **C**, or **D** — corresponding to the correct option column.

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/lexflow.git
cd lexflow
```

### 2. (Recommended) Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install customtkinter pandas openpyxl
```

| Library | Purpose | Built-in? |
|---------|---------|-----------|
| `customtkinter` | Modern UI framework | ❌ |
| `pandas` | Read CSV / Excel files | ❌ |
| `openpyxl` | Excel `.xlsx` support for pandas | ❌ |
| `tkinter` | Base GUI | ✅ |
| `csv`, `os`, `sys`, `json`, `random`, `datetime` | Standard utilities | ✅ |

---

## ▶️ Running the Application

```bash
python GUI.py
```

> Make sure `GUI.py` and `newword_backend.py` are in the **same folder**, along with your `icon.ico` file.

---

## 📁 Project Structure

```
lexflow/
├── GUI.py                  # Main application & UI
├── newword_backend.py      # Core logic (WordTrainer, SRS, stats)
├── icon.ico                # App icon
│
├── review_30min.csv        # Auto-generated SRS review files
├── review_1day.csv
├── review_3day.csv
├── review_7day.csv
├── review_meta.json        # SRS timing metadata
│
├── mistake.csv             # Vocabulary mistakes
├── quiz_mistakes.csv       # Quiz mistakes
└── study_stats.json        # Daily learning statistics
```

> All data files are **auto-generated** in the same directory as `GUI.py`. No manual setup required.

---

## 🖼️ Interface Overview

| Tab | Description |
|-----|-------------|
| 📚 **Học từ** | Vocabulary learning with SRS badges and review reminders |
| ✏️ **Thêm từ** | Add and manage vocabulary entries |
| 📝 **Trắc nghiệm** | Multiple-choice quiz with timer and mistake tracking |
| ➕ **Thêm câu** | Create and manage quiz question datasets |

---

## 🔄 SRS Workflow

```
Learn new words
      ↓
  review_30min  ──(30 min)──►  review_1day  ──(1 day)──►  review_3day  ──(3 days)──►  review_7day
      ▲                                                                                      │
      └──────────────────────────── cycle repeats ◄────────────────────────────────────────┘
```

---

## 🚀 Technologies

- **Python 3.10+**
- **CustomTkinter** — modern dark/light mode UI
- **Pandas** — fast CSV & Excel file handling
- **CSV / JSON** — lightweight local data storage

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**👨‍💻 Author: Nguyễn Lê Anh Tuấn**

💙 If this project helped you, consider supporting:

**MOMO:** `0835787489` &nbsp;|&nbsp; **MBbank:** `240120076868`

</div>
