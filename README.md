# LexFlow

LexFlow is a lightweight desktop application designed to help users learn English vocabulary efficiently.  
The application allows users to import vocabulary lists and practice words through a simple and intuitive interface.

---

## Features

- Import vocabulary from **CSV** or **XLSX**
- Random vocabulary practice
- **Multiple-choice answer mode** to test vocabulary knowledge
- **Text-to-Speech pronunciation** to help users hear how words are pronounced
- **Improved and cleaner user interface**
- Lightweight and fast
- Designed for efficient daily vocabulary learning

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

## How to Create a Vocabulary File

You can create the vocabulary file using Microsoft Excel or any spreadsheet software.

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

After saving the file, you can load it into LexFlow to start learning vocabulary.

---

## Running LexFlow

### Option 1 — Run the executable file

Download and run:

LexFlow.exe

Then open the application and load your vocabulary file.

---

### Option 2 — Run using Python source code

If you want to run LexFlow using Python, make sure the following libraries are installed.

Required libraries:

- customtkinter
- pandas
- openpyxl

Install them using pip:

pip install customtkinter pandas openpyxl

Then run the program:

python GUI.py

---

## Built With

- Python
- CustomTkinter
- Pandas

---

## Author

Nguyễn Lê Anh Tuấn  

Keep learning. Keep growing.
