# LexFlow ⚡

LexFlow is a lightweight desktop application designed to help users learn English vocabulary efficiently.  
The application allows users to import vocabulary lists, create new vocabulary files, and practice words through a simple and intuitive interface.

---

## Features

- Import vocabulary from **CSV** or **XLSX**
- Create a **new vocabulary file directly inside the application**
- Random vocabulary practice mode
- **Typing mode** to practice recalling words
- **Multiple-choice mode** to test vocabulary recognition
- **SRS-style review intervals** (30 minutes, 1 day, 3 days, 7 days)
- Vocabulary progress bar
- Simple and clean dark-mode interface
- Lightweight and fast

---

## Vocabulary File Format

LexFlow supports vocabulary files created using spreadsheet software such as Microsoft Excel.

Your vocabulary file must contain **5 columns** with the following headers:

| word | type | meaning | example | example_Vi |
|-----|-----|-----|-----|-----|
| apple | noun | quả táo | I eat an apple every day. | Tôi ăn một quả táo mỗi ngày |
| run | verb | chạy | He runs very fast. | Anh ấy chạy rất nhanh |

### Column Description

- **word** – the English word  
- **type** – word type (noun, verb, adjective, etc.)  
- **meaning** – Vietnamese meaning  
- **example** – example sentence in English  
- **example_Vi** – Vietnamese translation of the example sentence  

---

# Adding Vocabulary

LexFlow allows users to add vocabulary in two ways.

## Method 1 — Create a New Vocabulary File

1. Open the **Add Word** tab.
2. Click **Tạo file mới** (Create new file).
3. Choose a location to save the file.
4. You can **customize the file name** before saving.
5. After creating the file, enter vocabulary information into the input fields:

- Word
- Type
- Meaning
- Example
- Translate Example

6. Press **Enter** or click **Lưu từ** to save the word.
7. The word will appear in the vocabulary list below.

---

## Method 2 — Open an Existing CSV File

1. Go to the **Add Word** tab.
2. Click **Mở file có sẵn** (Open existing file).
3. Select a **.csv vocabulary file** from your computer.
4. After loading the file, you can continue adding new words using the input fields.
5. Press **Enter** or click **Lưu từ** to save the new vocabulary.

---

# How to Create a Vocabulary File Manually

You can create a vocabulary file using spreadsheet software such as Microsoft Excel.

### Step 1

Open Excel.

### Step 2

Create the following columns in the first row:

word | type | meaning | example | example_Vi

### Step 3

Add vocabulary data below the header.

Example:

| word | type | meaning | example | example_Vi |
|-----|-----|-----|-----|-----|
| book | noun | quyển sách | I read a book every night. | Tôi đọc sách mỗi tối |
| learn | verb | học | She learns English every day. | Cô ấy học tiếng Anh mỗi ngày |

### Step 4

Save the file as one of the following formats:

CSV (*.csv)  
or  
Excel Workbook (*.xlsx)

After saving the file, you can load it into LexFlow.

---

# Running LexFlow

## Option 1 — Run the executable file

Download and run:

LexFlow.exe

Then load your vocabulary file to begin learning.

---

## Option 2 — Run using Python source code

If you want to run LexFlow using Python, install the required libraries first.

Required libraries:

- customtkinter
- pandas
- openpyxl

Install them using pip:

pip install customtkinter pandas openpyxl

Then run the program:

python GUI.py

---

# Built With

- Python
- CustomTkinter
- Pandas

---

# Author

Nguyễn Lê Anh Tuấn

Keep learning. Keep growing.
