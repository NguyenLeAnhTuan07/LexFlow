import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from newword_backend import WordTrainer


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

trainer = None
waiting_for_next = False


def load_file():

    global trainer

    path = filedialog.askopenfilename(
        filetypes=[
            ("Data files", "*.csv *.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
    )

    if not path:
        return

    trainer = WordTrainer(path, mode_option.get())

    next_question()


def next_question():

    global waiting_for_next

    waiting_for_next = False

    if trainer is None:
        return

    word = trainer.next_word()

    if word is None:

        word_label.configure(text="🎉 Hoàn thành!")
        type_label.configure(text="")
        direction_label.configure(text="")
        remain_label.configure(text="")

        return

    q = trainer.get_question()

    word_label.configure(text=q["question"])

    type_label.configure(text=f"({q['type']})")

    # hiển thị hướng dịch
    if trainer.current_mode == "en_vi":
        direction_label.configure(text="English → Vietnamese")
    else:
        direction_label.configure(text="Vietnamese → English")

    result_label.configure(text="")

    example_label.configure(text="")

    answer_entry.delete(0, tk.END)

    answer_entry.focus()

    update_stats()

    remain_label.configure(text=f"Remaining: {len(trainer.words)}")


def submit_answer(event=None):

    global waiting_for_next

    if trainer is None:
        return

    # nếu đang đọc example
    if waiting_for_next:
        next_question()
        return

    answer = answer_entry.get().strip()

    if answer == "":
        return

    correct, word = trainer.check_answer(answer)

    if correct:

        result_label.configure(
            text="✔ Correct",
            text_color="green"
        )

        example_text = ""

        if word["example"]:
            example_text += f"Example:\n{word['example']}\n"

        if word["example_vi"]:
            example_text += f"{word['example_vi']}"

        example_label.configure(text=example_text)

        if word["example"] or word["example_vi"]:

            waiting_for_next = True

            result_label.configure(
                text="✔ Correct (press Enter to continue)",
                text_color="green"
            )

        else:

            root.after(1000, next_question)

    else:

        result_label.configure(
            text=f"✘ Wrong → {trainer.get_question()['answer']}",
            text_color="red"
        )

        example_label.configure(text="")

        root.after(2000, next_question)

    update_stats()


def update_stats():

    progress_label.configure(
        text=f"Correct: {trainer.correct_count} | Wrong: {trainer.wrong_count}"
    )


def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def on_closing():
    root.quit()
    root.destroy()
    sys.exit()

root = ctk.CTk()

root = ctk.CTk()
root.title("LexFlow")

root.iconbitmap("icon.ico")

root.title("Cre: Nguyễn Lê Anh Tuấn - Donate (MOMO): 0835787489 - MBbank: 240120076868")

root.geometry("700x600")


title = ctk.CTkLabel(
    root,
    text="LexFlow",
    font=("Arial", 30)
)

title.pack(pady=20)


mode_option = ctk.CTkOptionMenu(
    root,
    values=["random", "en_vi", "vi_en"]
)

mode_option.pack(pady=10)


load_button = ctk.CTkButton(
    root,
    text="Load CSV, XLSX",
    command=load_file
)

load_button.pack(pady=10)


direction_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 16)
)

direction_label.pack()


word_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 26)
)

word_label.pack(pady=20)


type_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 18)
)

type_label.pack()


answer_entry = ctk.CTkEntry(
    root,
    width=320,
    height=40,
    font=("Arial", 18)
)

answer_entry.pack(pady=20)

answer_entry.bind("<Return>", submit_answer)


result_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 18)
)

result_label.pack(pady=10)


example_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 16),
    wraplength=550,
    justify="left"
)

example_label.pack(pady=20)


progress_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 14)
)

progress_label.pack()


remain_label = ctk.CTkLabel(
    root,
    text="",
    font=("Arial", 14)
)

remain_label.pack()

# ===== Credit + lời chúc =====
credit_label = ctk.CTkLabel(
    root,
    text="Cre: Nguyễn Lê Anh Tuấn | Chúc mọi người học tốt 🚀\nDonate - MOMO: 0835787489 | MBbank: 240120076868",
    font=("Arial", 12),
    text_color="gray"
)

credit_label.pack(side="bottom", pady=10)
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
