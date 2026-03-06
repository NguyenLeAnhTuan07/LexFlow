import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
import sys
import os

from newword_backend import WordTrainer, get_weekly_stats, get_total_stats

# ────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
# ────────────────────────────────────────────────

trainer = None
waiting_for_next = False
all_words_pool = []          # giữ toàn bộ từ để tạo đáp án sai (MC)
current_choices = []         # đáp án trắc nghiệm hiện tại
choice_buttons = []          # widget buttons trắc nghiệm
mc_answered = False          # đã trả lời chưa (tránh click 2 lần)

# ════════════════════════════════════════════════
# TTS  (pyttsx3 offline — không cần internet)
# ════════════════════════════════════════════════
try:
    import pyttsx3
    _tts_engine = pyttsx3.init()
    _tts_engine.setProperty("rate", 160)
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False


def speak(text):
    if not TTS_AVAILABLE or not tts_var.get():
        return
    def _speak():
        try:
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_speak, daemon=True).start()


# ════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════

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


# ════════════════════════════════════════════════
# Load file
# ════════════════════════════════════════════════

def load_file():
    global trainer, all_words_pool, waiting_for_next, mc_answered

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
    all_words_pool = list(trainer.words)   # bản sao để tạo đáp án sai
    waiting_for_next = False
    mc_answered = False

    # reset UI
    progress_bar.set(0)
    streak_label.configure(text="🔥 0")
    result_label.configure(text="")
    example_label.configure(text="")

    switch_quiz_mode()   # áp dụng chế độ hiển thị
    next_question()


# ════════════════════════════════════════════════
# Switch giữa typing & multiple choice
# ════════════════════════════════════════════════

def switch_quiz_mode(*args):
    mode = quiz_mode_var.get()
    if mode == "typing":
        mc_frame.pack_forget()
        answer_entry.pack(pady=14)
        answer_entry.focus()
    else:
        answer_entry.pack_forget()
        mc_frame.pack(pady=14)


# ════════════════════════════════════════════════
# Next question
# ════════════════════════════════════════════════

def next_question():
    global waiting_for_next, mc_answered, current_choices

    waiting_for_next = False
    mc_answered = False

    if trainer is None:
        return

    word = trainer.next_word()

    if word is None:
        show_completion_screen()
        return

    q = trainer.get_question()

    # ── hiển thị câu hỏi ──
    word_label.configure(text=q["question"])
    type_label.configure(text=f"({q['type']})" if q["type"] else "")

    if trainer.current_mode == "en_vi":
        direction_label.configure(text="English → Vietnamese")
        if tts_var.get():
            speak(q["question"])
    else:
        direction_label.configure(text="Vietnamese → English")

    # ── SRS level badge ──
    lvl = trainer.get_srs_info()
    srs_colors = ["#555", "#1a73e8", "#34a853", "#fbbc04", "#ea4335", "#9c27b0"]
    srs_label.configure(
        text=f"SRS lv.{lvl}",
        fg_color=srs_colors[min(lvl, len(srs_colors)-1)]
    )

    result_label.configure(text="")
    example_label.configure(text="")

    # ── progress bar ──
    total = len(all_words_pool)
    done = total - len(trainer.words)
    progress_bar.set(done / total if total > 0 else 0)
    remain_label.configure(text=f"{done}/{total} từ")

    update_stats()

    # ── chế độ trắc nghiệm ──
    if quiz_mode_var.get() == "multiple_choice":
        current_choices = trainer.get_choices(all_words_pool)
        render_choices(current_choices)
    else:
        answer_entry.delete(0, tk.END)
        answer_entry.focus()


# ════════════════════════════════════════════════
# Render multiple choice buttons
# ════════════════════════════════════════════════

def render_choices(choices):
    for btn in choice_buttons:
        btn.configure(state="normal", fg_color=("gray20", "gray25"), text_color="white")

    for i, choice in enumerate(choices):
        if i < len(choice_buttons):
            choice_buttons[i].configure(
                text=choice["text"],
                state="normal",
                fg_color=("gray20", "gray25"),
                text_color="white",
                command=lambda c=choice: on_choice_click(c)
            )


def on_choice_click(choice):
    global mc_answered, waiting_for_next

    if mc_answered or trainer is None:
        return

    mc_answered = True

    # highlight đúng / sai
    correct_text = trainer.get_question()["answer"]

    for btn in choice_buttons:
        t = btn.cget("text")
        if t == correct_text:
            btn.configure(fg_color="#34a853", text_color="white")
        elif t == choice["text"] and not choice["correct"]:
            btn.configure(fg_color="#ea4335", text_color="white")
        btn.configure(state="disabled")

    # check
    is_correct, word, interval = trainer.check_answer(choice["text"])

    if is_correct:
        result_label.configure(
            text=f"✔ Correct! (SRS: ôn lại sau {interval} phút)",
            text_color="#34a853"
        )
        show_example(word)
        streak_label.configure(text=f"🔥 {trainer.streak}")
        if trainer.current_mode == "en_vi" and tts_var.get():
            speak(word["en"])

        if not (word["example"] or word["example_vi"]):
            root.after(1200, next_question)
        else:
            waiting_for_next = True
            result_label.configure(
                text=f"✔ Correct! — nhấn Enter để tiếp tục",
                text_color="#34a853"
            )
    else:
        result_label.configure(
            text=f"✘ Sai → Đáp án đúng: {correct_text}",
            text_color="#ea4335"
        )
        streak_label.configure(text=f"🔥 0")
        root.after(2000, next_question)

    update_stats()


# ════════════════════════════════════════════════
# Submit (typing mode)
# ════════════════════════════════════════════════

def submit_answer(event=None):
    global waiting_for_next

    if trainer is None:
        return

    if waiting_for_next:
        next_question()
        return

    answer = answer_entry.get().strip()
    if answer == "":
        return

    is_correct, word, interval = trainer.check_answer(answer)

    if is_correct:
        result_label.configure(
            text=f"✔ Correct! (SRS: ôn lại sau {interval} phút)",
            text_color="#34a853"
        )
        streak_label.configure(text=f"🔥 {trainer.streak}")
        if trainer.current_mode == "en_vi" and tts_var.get():
            speak(word["en"])

        show_example(word)

        if word["example"] or word["example_vi"]:
            waiting_for_next = True
            result_label.configure(
                text=f"✔ Correct! — nhấn Enter để tiếp tục",
                text_color="#34a853"
            )
        else:
            root.after(1000, next_question)
    else:
        result_label.configure(
            text=f"✘ Sai → {trainer.get_question()['answer']}",
            text_color="#ea4335"
        )
        streak_label.configure(text="🔥 0")
        example_label.configure(text="")
        root.after(2000, next_question)

    update_stats()


def show_example(word):
    parts = []
    if word["example"]:
        parts.append(f"📖 {word['example']}")
    if word["example_vi"]:
        parts.append(f"🇻🇳 {word['example_vi']}")
    example_label.configure(text="\n".join(parts))


# ════════════════════════════════════════════════
# Stats update
# ════════════════════════════════════════════════

def update_stats():
    if trainer:
        acc = 0
        total_ans = trainer.correct_count + trainer.wrong_count
        if total_ans > 0:
            acc = int(trainer.correct_count / total_ans * 100)
        progress_label.configure(
            text=f"✅ {trainer.correct_count}  ❌ {trainer.wrong_count}  |  Accuracy: {acc}%  |  Best streak: 🔥{trainer.best_streak}"
        )


# ════════════════════════════════════════════════
# Completion screen
# ════════════════════════════════════════════════

def show_completion_screen():
    word_label.configure(text="🎉 Hoàn thành session!")
    type_label.configure(text="")
    direction_label.configure(text="")
    result_label.configure(text="")
    example_label.configure(text="")
    remain_label.configure(text="")
    progress_bar.set(1.0)

    if trainer:
        total = trainer.correct_count + trainer.wrong_count
        acc = int(trainer.correct_count / total * 100) if total > 0 else 0
        example_label.configure(
            text=f"📊 Kết quả session:\n"
                 f"✅ Đúng: {trainer.correct_count}  |  ❌ Sai: {trainer.wrong_count}\n"
                 f"🎯 Accuracy: {acc}%  |  🔥 Best streak: {trainer.best_streak}"
        )


# ════════════════════════════════════════════════
# Stats popup (biểu đồ 7 ngày)
# ════════════════════════════════════════════════

def show_stats_popup():
    popup = ctk.CTkToplevel(root)
    popup.title("📊 Thống kê học tập")
    popup.geometry("540x400")
    popup.grab_set()

    ctk.CTkLabel(popup, text="📊 Thống kê 7 ngày gần nhất", font=("Arial", 18, "bold")).pack(pady=16)

    weekly = get_weekly_stats()
    total_c, total_w = get_total_stats()

    # ── canvas bar chart ──
    canvas_frame = ctk.CTkFrame(popup)
    canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)

    canvas = tk.Canvas(canvas_frame, bg="#1a1a2e", highlightthickness=0, height=220)
    canvas.pack(fill="both", expand=True)

    def draw_chart(event=None):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return

        max_val = max((d["correct"] + d["wrong"]) for d in weekly) or 1
        bar_w = w // (len(weekly) * 3)
        gap = w // len(weekly)
        pad_bottom = 40
        pad_top = 10

        for i, day in enumerate(weekly):
            x_center = gap * i + gap // 2
            total_day = day["correct"] + day["wrong"]
            bar_h = int((total_day / max_val) * (h - pad_bottom - pad_top))

            c_h = int((day["correct"] / max_val) * (h - pad_bottom - pad_top)) if total_day else 0
            w_h = bar_h - c_h

            # wrong (đỏ) — phần dưới
            if w_h > 0:
                canvas.create_rectangle(
                    x_center - bar_w, h - pad_bottom - c_h - w_h,
                    x_center + bar_w, h - pad_bottom - c_h,
                    fill="#ea4335", outline=""
                )
            # correct (xanh) — phần trên
            if c_h > 0:
                canvas.create_rectangle(
                    x_center - bar_w, h - pad_bottom - c_h,
                    x_center + bar_w, h - pad_bottom,
                    fill="#34a853", outline=""
                )

            canvas.create_text(
                x_center, h - pad_bottom + 8,
                text=day["label"], fill="#aaa", font=("Arial", 10)
            )
            if total_day:
                canvas.create_text(
                    x_center, h - pad_bottom - bar_h - 10,
                    text=str(total_day), fill="white", font=("Arial", 9)
                )

    canvas.bind("<Configure>", draw_chart)
    canvas.after(50, draw_chart)

    # legend
    leg = ctk.CTkFrame(popup, fg_color="transparent")
    leg.pack(pady=4)
    ctk.CTkLabel(leg, text="■ Đúng", text_color="#34a853", font=("Arial", 12)).pack(side="left", padx=10)
    ctk.CTkLabel(leg, text="■ Sai", text_color="#ea4335", font=("Arial", 12)).pack(side="left", padx=10)

    # tổng
    ctk.CTkLabel(
        popup,
        text=f"Tổng từ đúng: {total_c}  |  Tổng từ sai: {total_w}",
        font=("Arial", 13), text_color="gray"
    ).pack(pady=6)


# ════════════════════════════════════════════════
# ROOT WINDOW
# ════════════════════════════════════════════════

root = ctk.CTk()
root.title("LexFlow — Nâng cấp")

try:
    root.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass

root.geometry("720x680")
root.minsize(600, 580)

# ── Title bar ──────────────────────────────────
top_bar = ctk.CTkFrame(root, fg_color="transparent")
top_bar.pack(fill="x", padx=20, pady=(16, 0))

ctk.CTkLabel(top_bar, text="⚡ LexFlow", font=("Arial", 28, "bold")).pack(side="left")

streak_label = ctk.CTkLabel(top_bar, text="🔥 0", font=("Arial", 20, "bold"), text_color="#fbbc04")
streak_label.pack(side="left", padx=16)

stats_btn = ctk.CTkButton(
    top_bar, text="📊 Thống kê", width=110, height=32,
    command=show_stats_popup, fg_color="#1a73e8"
)
stats_btn.pack(side="right")

# ── Controls bar ───────────────────────────────
ctrl_bar = ctk.CTkFrame(root, fg_color="transparent")
ctrl_bar.pack(fill="x", padx=20, pady=10)

mode_option = ctk.CTkOptionMenu(
    ctrl_bar, values=["random", "en_vi", "vi_en"], width=120
)
mode_option.pack(side="left", padx=(0, 10))

quiz_mode_var = tk.StringVar(value="typing")
quiz_mode_var.trace_add("write", switch_quiz_mode)

ctk.CTkSegmentedButton(
    ctrl_bar,
    values=["typing", "multiple_choice"],
    variable=quiz_mode_var,
    width=240
).pack(side="left", padx=10)

tts_var = tk.BooleanVar(value=TTS_AVAILABLE)
tts_check = ctk.CTkCheckBox(
    ctrl_bar, text="🔊 TTS" if TTS_AVAILABLE else "🔊 (cần pyttsx3)",
    variable=tts_var, state="normal" if TTS_AVAILABLE else "disabled"
)
tts_check.pack(side="left", padx=10)

load_button = ctk.CTkButton(
    ctrl_bar, text="📂 Load file", command=load_file, width=110
)
load_button.pack(side="right")

# ── Progress bar ───────────────────────────────
prog_frame = ctk.CTkFrame(root, fg_color="transparent")
prog_frame.pack(fill="x", padx=20, pady=(0, 4))

progress_bar = ctk.CTkProgressBar(prog_frame, height=10)
progress_bar.set(0)
progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 10))

remain_label = ctk.CTkLabel(prog_frame, text="0/0 từ", font=("Arial", 12), width=70)
remain_label.pack(side="right")

# ── Direction + SRS badge ──────────────────────
badge_row = ctk.CTkFrame(root, fg_color="transparent")
badge_row.pack(pady=(4, 0))

direction_label = ctk.CTkLabel(badge_row, text="", font=("Arial", 14), text_color="#8ab4f8")
direction_label.pack(side="left", padx=10)

srs_label = ctk.CTkLabel(
    badge_row, text="SRS lv.0", font=("Arial", 12),
    fg_color="#555", corner_radius=8, padx=8, pady=2
)
srs_label.pack(side="left", padx=6)

# ── Word display ───────────────────────────────
word_label = ctk.CTkLabel(root, text="", font=("Arial", 30, "bold"), wraplength=620)
word_label.pack(pady=(16, 4))

type_label = ctk.CTkLabel(root, text="", font=("Arial", 16), text_color="gray")
type_label.pack()

# ── Typing answer entry ────────────────────────
answer_entry = ctk.CTkEntry(root, width=340, height=44, font=("Arial", 18), placeholder_text="Nhập đáp án…")
answer_entry.bind("<Return>", submit_answer)

# ── Multiple choice frame ──────────────────────
mc_frame = ctk.CTkFrame(root, fg_color="transparent")

choice_buttons = []
for row_i in range(2):
    for col_i in range(2):
        btn = ctk.CTkButton(
            mc_frame,
            text="",
            width=300,
            height=50,
            font=("Arial", 15),
            corner_radius=10,
            fg_color=("gray20", "gray25"),
            hover_color=("gray30", "gray35"),
            command=lambda: None
        )
        btn.grid(row=row_i, column=col_i, padx=8, pady=6)
        choice_buttons.append(btn)

# ── Result ─────────────────────────────────────
result_label = ctk.CTkLabel(root, text="", font=("Arial", 16))
result_label.pack(pady=6)

# ── Example ────────────────────────────────────
example_label = ctk.CTkLabel(
    root, text="", font=("Arial", 14),
    wraplength=580, justify="left", text_color="#ccc"
)
example_label.pack(pady=8)

# ── Stats bar ──────────────────────────────────
progress_label = ctk.CTkLabel(root, text="", font=("Arial", 13), text_color="gray")
progress_label.pack()

# ── Credit ─────────────────────────────────────
ctk.CTkLabel(
    root,
    text="Cre: Nguyễn Lê Anh Tuấn | Chúc mọi người học tốt 🚀\nDonate — MOMO: 0835787489 | MBbank: 240120076868",
    font=("Arial", 11), text_color="#555"
).pack(side="bottom", pady=10)

# ── apply quiz mode default ────────────────────
switch_quiz_mode()

# ════════════════════════════════════════════════
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()