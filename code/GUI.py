import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import os
import sys
import datetime

from newword_backend import (
    WordTrainer,
    get_weekly_stats, get_total_stats,
    get_due_stages, get_stage_word_count, get_review_summary,
    get_mistake_count,
    REVIEW_STAGES, MISTAKE_FILE,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ════════════════════════════════════════════════
# Global state
# ════════════════════════════════════════════════
trainer          = None
waiting_for_next = False
all_words_pool   = []
current_choices  = []
choice_buttons   = []
mc_answered      = False
vocab_csv_path   = None

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
# Tab switching
# ════════════════════════════════════════════════

def show_tab(tab):
    if tab == "learn":
        vocab_frame.pack_forget()
        learn_frame.pack(fill="both", expand=True)
        tab_learn_btn.configure(fg_color="#1a73e8")
        tab_vocab_btn.configure(fg_color=("gray25","gray20"))
    else:
        learn_frame.pack_forget()
        vocab_frame.pack(fill="both", expand=True)
        tab_vocab_btn.configure(fg_color="#1a73e8")
        tab_learn_btn.configure(fg_color=("gray25","gray20"))

# ════════════════════════════════════════════════
# LEARN TAB — load & quiz
# ════════════════════════════════════════════════

def _start_trainer(path):
    """Khởi tạo trainer từ path, reset toàn bộ UI."""
    global trainer, all_words_pool, waiting_for_next, mc_answered

    trainer = WordTrainer(path, mode_option.get())
    all_words_pool   = list(trainer.words)
    waiting_for_next = False
    mc_answered      = False

    progress_bar.set(0)
    streak_label.configure(text="🔥 0")
    result_label.configure(text="")
    example_label.configure(text="")

    basename = os.path.basename(path)
    if trainer._is_mistake:
        color = "#ea4335"
        tag   = f"💀 Từ sai ({len(all_words_pool)} từ)"
    elif trainer._is_review:
        color = "#fbbc04"
        tag   = f"📋 Ôn tập: {basename}  ({len(all_words_pool)} từ)"
    else:
        color = "#8ab4f8"
        tag   = f"📂 {basename}  ({len(all_words_pool)} từ)"

    file_info_label.configure(text=tag, text_color=color)

    show_tab("learn")
    switch_quiz_mode()
    next_question()


def load_file():
    path = filedialog.askopenfilename(
        filetypes=[
            ("Data files", "*.csv *.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*"),
        ]
    )
    if path:
        _start_trainer(path)


def load_mistake_file():
    if not os.path.exists(MISTAKE_FILE):
        messagebox.showinfo("Thông báo", "Chưa có từ sai nào được lưu!")
        return
    if get_mistake_count() == 0:
        messagebox.showinfo("Thông báo", "File mistake.csv trống — chưa có từ sai!")
        return
    _start_trainer(MISTAKE_FILE)


def load_review_stage(stage):
    path = f"review_{stage}.csv"
    if not os.path.exists(path) or get_stage_word_count(stage) == 0:
        messagebox.showinfo("Thông báo", f"review_{stage}.csv chưa có từ nào!")
        return
    _start_trainer(path)


def switch_quiz_mode(*args):
    if quiz_mode_var.get() == "typing":
        mc_frame.pack_forget()
        answer_entry.pack(pady=14)
        answer_entry.focus()
    else:
        answer_entry.pack_forget()
        mc_frame.pack(pady=14)


def next_question():
    global waiting_for_next, mc_answered, current_choices

    waiting_for_next = False
    mc_answered      = False

    if trainer is None:
        return

    word = trainer.next_word()
    if word is None:
        show_completion_screen()
        return

    q = trainer.get_question()
    word_label.configure(text=q["question"])
    type_label.configure(text=f"({q['type']})" if q["type"] else "")
    direction_label.configure(
        text="English → Vietnamese" if trainer.current_mode == "en_vi" else "Vietnamese → English"
    )
    result_label.configure(text="")
    example_label.configure(text="")

    total = len(all_words_pool)
    done  = total - len(trainer.words)
    progress_bar.set(done / total if total > 0 else 0)
    remain_label.configure(text=f"{done}/{total} từ")
    update_stats()

    if quiz_mode_var.get() == "multiple_choice":
        current_choices = trainer.get_choices(all_words_pool)
        render_choices(current_choices)
    else:
        answer_entry.delete(0, tk.END)
        answer_entry.focus()


def render_choices(choices):
    for btn in choice_buttons:
        btn.configure(state="normal", fg_color=("gray20","gray25"), text_color="white")
    for i, choice in enumerate(choices):
        if i < len(choice_buttons):
            choice_buttons[i].configure(
                text=choice["text"], state="normal",
                fg_color=("gray20","gray25"), text_color="white",
                command=lambda c=choice: on_choice_click(c)
            )


def on_choice_click(choice):
    global mc_answered, waiting_for_next
    if mc_answered or trainer is None:
        return
    mc_answered = True

    correct_text = trainer.get_question()["answer"]
    for btn in choice_buttons:
        t = btn.cget("text")
        if t == correct_text:
            btn.configure(fg_color="#34a853", text_color="white")
        elif t == choice["text"] and not choice["correct"]:
            btn.configure(fg_color="#ea4335", text_color="white")
        btn.configure(state="disabled")

    is_correct, word = trainer.check_answer(choice["text"])
    _handle_result(is_correct, word)


def submit_answer(event=None):
    global waiting_for_next
    if trainer is None:
        return
    if waiting_for_next:
        next_question()
        return
    answer = answer_entry.get().strip()
    if not answer:
        return
    is_correct, word = trainer.check_answer(answer)
    _handle_result(is_correct, word)


def _handle_result(is_correct, word):
    global waiting_for_next

    if is_correct:
        streak_label.configure(text=f"🔥 {trainer.streak}")
        show_example(word)
        if word["example"] or word["example_vi"]:
            waiting_for_next = True
            result_label.configure(text="✔ Correct! — nhấn Enter để tiếp tục", text_color="#34a853")
        else:
            result_label.configure(text="✔ Correct!", text_color="#34a853")
            root.after(1000, next_question)
    else:
        result_label.configure(
            text=f"✘ Sai → {trainer.get_question()['answer']}", text_color="#ea4335"
        )
        streak_label.configure(text="🔥 0")
        example_label.configure(text="")
        root.after(2000, next_question)

    update_stats()
    # Cập nhật badge mistake realtime
    update_mistake_badge()


def show_example(word):
    parts = []
    if word["example"]:
        parts.append(f"📖 {word['example']}")
    if word["example_vi"]:
        parts.append(f"🇻🇳 {word['example_vi']}")
    example_label.configure(text="\n".join(parts))


def update_stats():
    if trainer:
        total_ans = trainer.correct_count + trainer.wrong_count
        acc = int(trainer.correct_count / total_ans * 100) if total_ans > 0 else 0
        progress_label.configure(
            text=f"✅ {trainer.correct_count}  ❌ {trainer.wrong_count}  |  Accuracy: {acc}%  |  Best streak: 🔥{trainer.best_streak}"
        )


def show_completion_screen():
    word_label.configure(text="🎉 Hoàn thành!")
    type_label.configure(text="")
    direction_label.configure(text="")
    result_label.configure(text="")
    remain_label.configure(text="")
    progress_bar.set(1.0)

    # Lưu kết quả session vào SRS
    if trainer:
        trainer.finish_session()

    if trainer:
        total = trainer.correct_count + trainer.wrong_count
        acc   = int(trainer.correct_count / total * 100) if total > 0 else 0
        note  = ""

        if trainer._is_mistake:
            note = f"\n\n💀 Từ sai: đúng sẽ bị xóa, sai vẫn còn trong file."
        elif trainer._is_review and trainer._stage:
            next_s = {"30min":"1day","1day":"3day","3day":"7day","7day":"30min"}[trainer._stage]
            note  = (f"\n\n✅ {len(trainer._passed)} từ đúng → review_{next_s}"
                     f"\n🔁 {len(trainer._failed)} từ sai → ở lại review_{trainer._stage}")
        else:
            note = f"\n\n⏰ Từ đúng đã lưu vào review_30min.csv — nhớ ôn sau 30 phút!"

        example_label.configure(
            text=f"📊 Kết quả:\n✅ {trainer.correct_count}  ❌ {trainer.wrong_count}"
                 f"  |  Accuracy: {acc}%  |  🔥 Best: {trainer.best_streak}{note}"
        )

    update_review_badges()
    update_mistake_badge()


# ════════════════════════════════════════════════
# REVIEW BADGE + POPUP
# ════════════════════════════════════════════════

STAGE_LABELS = {"30min":"30 phút","1day":"1 ngày","3day":"3 ngày","7day":"7 ngày"}


def update_review_badges():
    summary = get_review_summary()
    for stage, btn in review_badge_btns.items():
        info  = summary[stage]
        count = info["count"]
        if count == 0:
            btn.configure(text=f"⏳ {STAGE_LABELS[stage]}\n—",
                          fg_color=("gray25","gray20"), text_color="gray")
        elif info["is_due"]:
            btn.configure(text=f"🔔 {STAGE_LABELS[stage]}\n{count} từ",
                          fg_color="#ea4335", text_color="white")
        else:
            due = info["due_time"]
            if due:
                delta = due - datetime.datetime.now()
                mins  = int(delta.total_seconds() / 60)
                time_str = f"{mins}p nữa" if mins < 60 else (f"{mins//60}h nữa" if mins < 1440 else f"{mins//1440}d nữa")
            else:
                time_str = "—"
            btn.configure(text=f"📚 {STAGE_LABELS[stage]}\n{count} · {time_str}",
                          fg_color=("gray25","gray20"), text_color="#8ab4f8")


def update_mistake_badge():
    count = get_mistake_count()
    if count == 0:
        mistake_btn.configure(text="💀 Từ sai\n—", fg_color=("gray25","gray20"), text_color="gray")
    else:
        mistake_btn.configure(text=f"💀 Từ sai\n{count} từ", fg_color="#9c27b0", text_color="white")


def check_due_on_startup():
    due_stages = get_due_stages()
    mistake_c  = get_mistake_count()

    messages = []
    if due_stages:
        lines = [f"  • review_{s}: {get_stage_word_count(s)} từ" for s in due_stages]
        messages.append("⏰ Từ cần ôn tập SRS:\n" + "\n".join(lines))
    if mistake_c > 0:
        messages.append(f"💀 Bạn có {mistake_c} từ sai chưa ôn lại.")

    if not messages:
        return

    msg = "\n\n".join(messages) + "\n\nBắt đầu ôn ngay không?"
    if messagebox.askyesno("Nhắc nhở", msg):
        if due_stages:
            show_review_picker(due_stages)
        elif mistake_c > 0:
            load_mistake_file()


def show_review_picker(due_stages):
    if len(due_stages) == 1:
        load_review_stage(due_stages[0])
        return

    popup = ctk.CTkToplevel(root)
    popup.title("Chon stage on tap")
    popup.geometry("360x300")
    popup.grab_set()

    ctk.CTkLabel(popup, text="Chọn bài ôn:", font=("Arial", 16, "bold")).pack(pady=14)
    for stage in due_stages:
        count = get_stage_word_count(stage)
        s = stage
        ctk.CTkButton(
            popup,
            text=f"review_{stage}  —  {count} từ  ({STAGE_LABELS[stage]})",
            font=("Arial", 14), height=44,
            command=lambda st=s: [popup.destroy(), load_review_stage(st)]
        ).pack(fill="x", padx=30, pady=5)
    ctk.CTkButton(popup, text="Để sau", fg_color="gray", command=popup.destroy).pack(pady=8)


def show_stats_popup():
    popup = ctk.CTkToplevel(root)
    popup.title("Thong ke")
    popup.geometry("540x400")
    popup.grab_set()

    ctk.CTkLabel(popup, text="📊 Thống kê 7 ngày", font=("Arial", 18, "bold")).pack(pady=14)
    weekly = get_weekly_stats()
    total_c, total_w = get_total_stats()

    canvas_frame = ctk.CTkFrame(popup)
    canvas_frame.pack(fill="both", expand=True, padx=20, pady=8)
    canvas = tk.Canvas(canvas_frame, bg="#1a1a2e", highlightthickness=0, height=220)
    canvas.pack(fill="both", expand=True)

    def draw_chart(event=None):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return
        max_val = max((d["correct"]+d["wrong"]) for d in weekly) or 1
        gap = w // len(weekly)
        bar_w = gap // 3
        pad_b, pad_t = 40, 10
        for i, day in enumerate(weekly):
            xc = gap*i + gap//2
            total_day = day["correct"] + day["wrong"]
            bar_h = int((total_day/max_val)*(h-pad_b-pad_t))
            c_h   = int((day["correct"]/max_val)*(h-pad_b-pad_t)) if total_day else 0
            w_h   = bar_h - c_h
            if w_h > 0:
                canvas.create_rectangle(xc-bar_w, h-pad_b-c_h-w_h, xc+bar_w, h-pad_b-c_h, fill="#ea4335", outline="")
            if c_h > 0:
                canvas.create_rectangle(xc-bar_w, h-pad_b-c_h, xc+bar_w, h-pad_b, fill="#34a853", outline="")
            canvas.create_text(xc, h-pad_b+8, text=day["label"], fill="#aaa", font=("Arial", 10))
            if total_day:
                canvas.create_text(xc, h-pad_b-bar_h-10, text=str(total_day), fill="white", font=("Arial", 9))

    canvas.bind("<Configure>", draw_chart)
    canvas.after(50, draw_chart)

    leg = ctk.CTkFrame(popup, fg_color="transparent")
    leg.pack(pady=4)
    ctk.CTkLabel(leg, text="■ Đúng", text_color="#34a853", font=("Arial", 12)).pack(side="left", padx=10)
    ctk.CTkLabel(leg, text="■ Sai",  text_color="#ea4335", font=("Arial", 12)).pack(side="left", padx=10)
    ctk.CTkLabel(popup, text=f"Tổng đúng: {total_c}  |  Tổng sai: {total_w}",
                 font=("Arial", 13), text_color="gray").pack(pady=6)


# ════════════════════════════════════════════════
# VOCAB TAB
# ════════════════════════════════════════════════

HEADERS     = ["word", "type", "meaning", "example", "translate_example"]
DEFAULT_DIR = os.path.abspath(".")
vocab_preview_rows = []


def vocab_new_file():
    global vocab_csv_path
    path = filedialog.asksaveasfilename(
        initialdir=DEFAULT_DIR, defaultextension=".csv",
        filetypes=[("CSV files","*.csv")], title="Tạo file CSV mới"
    )
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(HEADERS)
    vocab_csv_path = path
    vocab_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    vocab_status_label.configure(text="File mới đã tạo. Bắt đầu nhập từ!", text_color="#34a853")
    vocab_preview_clear()
    vocab_clear_entries()
    vocab_entries[0].focus()


def vocab_open_file():
    global vocab_csv_path
    path = filedialog.askopenfilename(
        initialdir=DEFAULT_DIR,
        filetypes=[("CSV files","*.csv"),("All files","*.*")],
        title="Chọn file CSV"
    )
    if not path:
        return
    vocab_csv_path = path
    vocab_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    vocab_preview_clear()
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        data_rows = rows[1:] if rows and rows[0][0].lower() in ("word","english") else rows
        for row in data_rows:
            vocab_preview_add((row+["","","","",""])[:5])
        vocab_status_label.configure(text=f"Đã load {len(data_rows)} từ.", text_color="#8ab4f8")
    except Exception as e:
        vocab_status_label.configure(text=f"Lỗi: {e}", text_color="#ea4335")
    vocab_clear_entries()
    vocab_entries[0].focus()


def vocab_save_row(event=None):
    if vocab_csv_path is None:
        messagebox.showwarning("Chưa chọn file", "Vui lòng tạo hoặc mở file CSV trước!")
        return
    values = [e.get().strip() for e in vocab_entries]
    if not values[0] or not values[2]:
        vocab_status_label.configure(text="⚠ Phải nhập ít nhất Word và Meaning!", text_color="#fbbc04")
        return
    file_exists = os.path.exists(vocab_csv_path)
    with open(vocab_csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADERS)
        writer.writerow(values)
    word_saved = values[0]
    vocab_clear_entries()
    vocab_entries[0].focus()
    vocab_status_label.configure(text=f'✅ Đã lưu "{word_saved}"', text_color="#34a853")
    vocab_preview_add(values)


def vocab_clear_entries():
    for e in vocab_entries:
        e.delete(0, tk.END)


def vocab_preview_clear():
    for row_widgets in vocab_preview_rows:
        for lbl in row_widgets:
            lbl.destroy()
    vocab_preview_rows.clear()


def vocab_preview_add(values):
    row_idx    = len(vocab_preview_rows) + 1
    col_widths = [140, 80, 140, 200, 200]
    row_widgets = []
    for col, (val, w) in enumerate(zip(values, col_widths)):
        lbl = ctk.CTkLabel(vocab_table_frame, text=val if val else "—",
            font=("Arial", 12), width=w, anchor="w", text_color="#ccc")
        lbl.grid(row=row_idx, column=col, padx=4, pady=2, sticky="w")
        row_widgets.append(lbl)
    vocab_preview_rows.append(row_widgets)
    vocab_table_scroll.after(50, lambda: vocab_table_scroll._parent_canvas.yview_moveto(1.0))


# ════════════════════════════════════════════════
# ROOT WINDOW
# ════════════════════════════════════════════════

root = ctk.CTk()
root.title("LexFlow - Cre: Nguyen Le Anh Tuan  |  MOMO: 0835787489  |  MBbank: 240120076868")
try:
    root.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass
root.geometry("860x740")
root.minsize(720, 620)

# ── Header ─────────────────────────────────────
header = ctk.CTkFrame(root, fg_color=("gray18","gray12"), corner_radius=0)
header.pack(fill="x")

ctk.CTkLabel(header, text="⚡ LexFlow", font=("Arial", 24, "bold")).pack(side="left", padx=20, pady=10)

tab_bar = ctk.CTkFrame(header, fg_color="transparent")
tab_bar.pack(side="left", padx=8)

tab_learn_btn = ctk.CTkButton(tab_bar, text="📚 Học từ", width=110, height=32,
    command=lambda: show_tab("learn"), fg_color="#1a73e8", corner_radius=8)
tab_learn_btn.pack(side="left", padx=4)

tab_vocab_btn = ctk.CTkButton(tab_bar, text="✏️ Thêm từ", width=110, height=32,
    command=lambda: show_tab("vocab"), fg_color=("gray25","gray20"), corner_radius=8)
tab_vocab_btn.pack(side="left", padx=4)

stats_btn = ctk.CTkButton(header, text="📊 Thống kê", width=100, height=30,
    command=show_stats_popup, fg_color=("gray30","gray25"))
stats_btn.pack(side="right", padx=20)

# ════════════════════════════════════════════════
# LEARN FRAME
# ════════════════════════════════════════════════

learn_frame = ctk.CTkFrame(root, fg_color="transparent")
learn_frame.pack(fill="both", expand=True)

# ── Review + Mistake badges ────────────────────
badge_outer = ctk.CTkFrame(learn_frame, fg_color=("gray16","gray10"), corner_radius=8)
badge_outer.pack(fill="x", padx=16, pady=(10,4))

ctk.CTkLabel(badge_outer, text="⏰ SRS:", font=("Arial", 12, "bold"), text_color="#fbbc04").pack(side="left", padx=10)

review_badge_btns = {}
for stage in REVIEW_STAGES:
    btn = ctk.CTkButton(
        badge_outer,
        text=f"⏳ {STAGE_LABELS[stage]}\n—",
        width=128, height=44, font=("Arial", 11), corner_radius=8,
        fg_color=("gray25","gray20"), text_color="gray",
        command=lambda s=stage: load_review_stage(s)
    )
    btn.pack(side="left", padx=4, pady=6)
    review_badge_btns[stage] = btn

# Separator
ctk.CTkLabel(badge_outer, text="|", text_color="gray", font=("Arial", 18)).pack(side="left", padx=6)

mistake_btn = ctk.CTkButton(
    badge_outer,
    text="💀 Từ sai\n—",
    width=110, height=44, font=("Arial", 11), corner_radius=8,
    fg_color=("gray25","gray20"), text_color="gray",
    command=load_mistake_file
)
mistake_btn.pack(side="left", padx=4, pady=6)

# ── Controls ───────────────────────────────────
ctrl_bar = ctk.CTkFrame(learn_frame, fg_color="transparent")
ctrl_bar.pack(fill="x", padx=16, pady=6)

mode_option = ctk.CTkOptionMenu(ctrl_bar, values=["random","en_vi","vi_en"], width=110)
mode_option.pack(side="left", padx=(0,8))

quiz_mode_var = tk.StringVar(value="typing")
quiz_mode_var.trace_add("write", switch_quiz_mode)
ctk.CTkSegmentedButton(ctrl_bar, values=["typing","multiple_choice"],
    variable=quiz_mode_var, width=230).pack(side="left", padx=8)

streak_label = ctk.CTkLabel(ctrl_bar, text="🔥 0", font=("Arial", 17, "bold"), text_color="#fbbc04")
streak_label.pack(side="left", padx=12)

load_button = ctk.CTkButton(ctrl_bar, text="📂 Load file", command=load_file, width=110)
load_button.pack(side="right")

# File info
file_info_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 12))
file_info_label.pack(anchor="w", padx=20)

# Progress bar
prog_frame = ctk.CTkFrame(learn_frame, fg_color="transparent")
prog_frame.pack(fill="x", padx=16, pady=(2,4))
progress_bar = ctk.CTkProgressBar(prog_frame, height=8)
progress_bar.set(0)
progress_bar.pack(fill="x", side="left", expand=True, padx=(0,8))
remain_label = ctk.CTkLabel(prog_frame, text="0/0 từ", font=("Arial", 11), width=70)
remain_label.pack(side="right")

direction_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 13), text_color="#8ab4f8")
direction_label.pack()

word_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 30, "bold"), wraplength=700)
word_label.pack(pady=(12,4))

type_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 15), text_color="gray")
type_label.pack()

answer_entry = ctk.CTkEntry(learn_frame, width=340, height=42, font=("Arial", 17),
    placeholder_text="Nhập đáp án…")
answer_entry.bind("<Return>", submit_answer)

mc_frame = ctk.CTkFrame(learn_frame, fg_color="transparent")
choice_buttons = []
for row_i in range(2):
    for col_i in range(2):
        btn = ctk.CTkButton(mc_frame, text="", width=310, height=48, font=("Arial", 14),
            corner_radius=10, fg_color=("gray20","gray25"), hover_color=("gray30","gray35"),
            command=lambda: None)
        btn.grid(row=row_i, column=col_i, padx=8, pady=6)
        choice_buttons.append(btn)

result_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 15))
result_label.pack(pady=4)

example_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 13),
    wraplength=700, justify="left", text_color="#ccc")
example_label.pack(pady=6)

progress_label = ctk.CTkLabel(learn_frame, text="", font=("Arial", 12), text_color="gray")
progress_label.pack()

ctk.CTkLabel(learn_frame,
    text="Cre: Nguyen Le Anh Tuan  |  MOMO: 0835787489  |  MBbank: 240120076868",
    font=("Arial", 20), text_color="#444").pack(side="bottom", pady=6)

switch_quiz_mode()

# ════════════════════════════════════════════════
# VOCAB FRAME
# ════════════════════════════════════════════════

vocab_frame = ctk.CTkFrame(root, fg_color="transparent")

file_action_bar = ctk.CTkFrame(vocab_frame, fg_color="transparent")
file_action_bar.pack(fill="x", padx=20, pady=(14,4))
ctk.CTkButton(file_action_bar, text="📄 Tạo file mới",   width=140,
    command=vocab_new_file, fg_color="#34a853").pack(side="left", padx=(0,10))
ctk.CTkButton(file_action_bar, text="📂 Mở file có sẵn", width=150,
    command=vocab_open_file, fg_color="#1a73e8").pack(side="left")
vocab_file_label = ctk.CTkLabel(file_action_bar, text="Chưa chọn file",
    font=("Arial", 13), text_color="gray")
vocab_file_label.pack(side="left", padx=16)

input_section = ctk.CTkFrame(vocab_frame, fg_color=("gray18","gray12"), corner_radius=10)
input_section.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(input_section, text="Nhập từ mới (Enter nhảy ô / lưu)",
    font=("Arial", 13, "bold")).pack(pady=(10,6))

col_labels = ["Word *","Type","Meaning *","Example","Translate Example"]
col_widths  = [140, 80, 140, 200, 200]
col_hints   = ["run","v.","chạy","I run every day.","Tôi chạy mỗi ngày."]

entry_row = ctk.CTkFrame(input_section, fg_color="transparent")
entry_row.pack(padx=14, pady=(0,14))

vocab_entries = []
for lbl, w, hint in zip(col_labels, col_widths, col_hints):
    cf = ctk.CTkFrame(entry_row, fg_color="transparent")
    cf.pack(side="left", padx=5)
    ctk.CTkLabel(cf, text=lbl, font=("Arial", 12), text_color="#8ab4f8").pack(anchor="w")
    e = ctk.CTkEntry(cf, width=w, height=36, font=("Arial", 13), placeholder_text=hint)
    e.pack()
    vocab_entries.append(e)

def make_tab_handler(idx):
    def handler(event):
        if idx < len(vocab_entries) - 1:
            vocab_entries[idx+1].focus()
        else:
            vocab_save_row()
    return handler

for i, e in enumerate(vocab_entries):
    e.bind("<Return>", make_tab_handler(i))
    e.bind("<Tab>",    make_tab_handler(i))

ctk.CTkButton(input_section, text="💾 Lưu từ (Enter)",
    command=vocab_save_row, width=160, fg_color="#34a853").pack(pady=(0,12))

vocab_status_label = ctk.CTkLabel(vocab_frame, text="", font=("Arial", 13))
vocab_status_label.pack(pady=(0,4))

ctk.CTkLabel(vocab_frame, text="Danh sách từ trong file:",
    font=("Arial", 13, "bold")).pack(anchor="w", padx=20)

vocab_table_scroll = ctk.CTkScrollableFrame(vocab_frame, height=230)
vocab_table_scroll.pack(fill="both", expand=True, padx=20, pady=(4,16))

vocab_table_frame = ctk.CTkFrame(vocab_table_scroll, fg_color="transparent")
vocab_table_frame.pack(fill="both", expand=True)

for col, (h_text, w) in enumerate(zip(HEADERS, col_widths)):
    ctk.CTkLabel(vocab_table_frame, text=h_text.upper(),
        font=("Arial", 12, "bold"), width=w, anchor="w", text_color="#8ab4f8"
    ).grid(row=0, column=col, padx=4, pady=(0,4), sticky="w")

# ════════════════════════════════════════════════
# KHỞI ĐỘNG
# ════════════════════════════════════════════════

update_review_badges()
update_mistake_badge()
root.after(500, check_due_on_startup)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()