import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import os
import sys
import datetime
import random
import pandas as pd

from newword_backend import (
    WordTrainer,
    get_weekly_stats, get_total_stats,
    get_due_stages, get_stage_word_count, get_review_summary,
    get_mistake_count,
    REVIEW_STAGES, MISTAKE_FILE,
)

# Thư mục chứa GUI.py — dùng làm gốc lưu tất cả file data
# Khi chạy .exe (PyInstaller), dùng thư mục chứa .exe
# Khi chạy .py thường, dùng thư mục chứa .py
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ════════════════════════════════════════════════
# Global state — Vocab trainer
# ════════════════════════════════════════════════
trainer              = None
waiting_for_next     = False
all_words_pool       = []
choice_buttons       = []
mc_answered          = False
vocab_csv_path       = None
current_review_stage = None
review_passed_words  = []
review_failed_words  = []

# ════════════════════════════════════════════════
# Global state — Quiz (trắc nghiệm)
# ════════════════════════════════════════════════
quiz_questions       = []   # list of dict
quiz_queue           = []   # câu hỏi còn lại trong session
quiz_current         = None
quiz_correct         = 0
quiz_wrong           = 0
quiz_total_session   = 0
quiz_answered        = False
quiz_mistake_file    = os.path.join(BASE_DIR, "quiz_mistakes.csv")
quiz_timer_id        = None   # after() id cho timer
quiz_time_left       = 0
QUIZ_HEADERS         = ["question", "answer", "A", "B", "C", "D"]
QUIZ_ADD_HEADERS     = ["question", "answer", "A", "B", "C", "D"]
quiz_add_csv_path    = None
quiz_add_preview_rows = []
quiz_in_mistake_mode  = False   # True khi đang luyện quiz_mistakes

STAGE_LABELS = {"30min":"30 phút","1day":"1 ngày","3day":"3 ngày","7day":"7 ngày"}

# ════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = BASE_DIR
    return os.path.join(base_path, relative_path)

def set_popup_icon(popup):
    try:
        popup.after(200, lambda: popup.wm_iconbitmap(resource_path("icon.ico")))
    except Exception:
        pass

def on_closing():
    root.quit()
    root.destroy()
    sys.exit()

# ════════════════════════════════════════════════
# Tab switching
# ════════════════════════════════════════════════
ALL_TABS = ["learn", "vocab", "quiz", "quiz_add"]

def show_tab(tab):
    frames = {
        "learn"   : learn_frame,
        "vocab"   : vocab_frame,
        "quiz"    : quiz_frame,
        "quiz_add": quiz_add_frame,
    }
    btns = {
        "learn"   : tab_learn_btn,
        "vocab"   : tab_vocab_btn,
        "quiz"    : tab_quiz_btn,
        "quiz_add": tab_quiz_add_btn,
    }
    for t, f in frames.items():
        if t == tab:
            f.pack(fill="both", expand=True)
            btns[t].configure(fg_color="#1a73e8")
        else:
            f.pack_forget()
            btns[t].configure(fg_color=("gray25","gray20"))

# ════════════════════════════════════════════════
# LEARN TAB — logic
# ════════════════════════════════════════════════

def load_file():
    global trainer, all_words_pool, waiting_for_next, mc_answered
    global current_review_stage, review_passed_words, review_failed_words

    path = filedialog.askopenfilename(filetypes=[
        ("Data files","*.csv *.xlsx *.xls"),("CSV","*.csv"),
        ("Excel","*.xlsx *.xls"),("All","*.*")])
    if not path:
        return
    _init_trainer(path)

def _init_trainer(path):
    global trainer, all_words_pool, waiting_for_next, mc_answered
    global current_review_stage, review_passed_words, review_failed_words

    trainer = WordTrainer(path, mode_option.get())
    all_words_pool       = list(trainer.words)
    waiting_for_next     = False
    mc_answered          = False
    current_review_stage = None
    review_passed_words  = []
    review_failed_words  = []

    basename = os.path.basename(path)
    for s in REVIEW_STAGES:
        if basename == f"review_{s}.csv":
            current_review_stage = s
            break

    progress_bar.set(0)
    streak_label.configure(text="🔥 0")
    result_label.configure(text="")
    example_label.configure(text="")
    file_info_label.configure(
        text=f"{'📋 Ôn tập: ' if current_review_stage else '📂 '}{basename}  ({len(all_words_pool)} từ)",
        text_color="#fbbc04" if current_review_stage else "#8ab4f8"
    )
    show_tab("learn")
    switch_quiz_mode()
    next_question()

def load_review_stage(stage):
    _init_trainer(f"review_{stage}.csv")
    global current_review_stage
    current_review_stage = stage

def load_mistake_file():
    if not os.path.exists(MISTAKE_FILE) or get_mistake_count() == 0:
        messagebox.showinfo("Mistake", "Chưa có từ nào sai! Cố lên 💪")
        return
    _init_trainer(MISTAKE_FILE)

def switch_quiz_mode(*args):
    if quiz_mode_var.get() == "typing":
        mc_frame.pack_forget()
        answer_entry.pack(pady=14)
        answer_entry.focus()
    else:
        answer_entry.pack_forget()
        mc_frame.pack(pady=14)

def next_question():
    global waiting_for_next, mc_answered

    waiting_for_next = False
    mc_answered      = False

    if trainer is None:
        return
    word = trainer.next_word()
    if word is None:
        show_learn_completion()
        return

    q = trainer.get_question()
    word_label.configure(text=q["question"])
    type_label.configure(text=f"({q['type']})" if q["type"] else "")
    direction_label.configure(
        text="English → Vietnamese" if trainer.current_mode=="en_vi" else "Vietnamese → English")
    result_label.configure(text="")
    example_label.configure(text="")

    total = len(all_words_pool)
    done  = total - len(trainer.words)
    progress_bar.set(done/total if total else 0)
    remain_label.configure(text=f"{done}/{total} từ")
    update_learn_stats()

    if quiz_mode_var.get() == "multiple_choice":
        choices = trainer.get_choices(all_words_pool)
        _render_mc(choices)
    else:
        answer_entry.delete(0, tk.END)
        answer_entry.focus()

def _render_mc(choices):
    for btn in learn_mc_buttons:
        btn.configure(state="normal", fg_color=("gray20","gray25"),
                      text_color="white", command=lambda: None)
    for i, ch in enumerate(choices[:4]):
        b = learn_mc_buttons[i]
        b.configure(text=ch["text"], command=lambda c=ch: _on_learn_mc(c))

def _on_learn_mc(choice):
    global mc_answered
    if mc_answered or trainer is None:
        return
    mc_answered = True
    correct_text = trainer.get_question()["answer"]
    for btn in learn_mc_buttons:
        t = btn.cget("text")
        btn.configure(state="disabled",
            fg_color="#34a853" if t==correct_text else ("#ea4335" if t==choice["text"] else ("gray20","gray25")))
    is_correct, word = trainer.check_answer(choice["text"])
    _handle_learn_result(is_correct, word)

def submit_answer(event=None):
    global waiting_for_next
    if trainer is None:
        return
    if waiting_for_next:
        next_question()
        return
    ans = answer_entry.get().strip()
    if not ans:
        return
    is_correct, word = trainer.check_answer(ans)
    _handle_learn_result(is_correct, word)

def _handle_learn_result(is_correct, word):
    global waiting_for_next, review_passed_words, review_failed_words
    rd = {"word":word["en"],"type":word["pos"],"meaning":word["vi"],
          "example":word["example"],"translate_example":word["example_vi"]}
    if is_correct:
        streak_label.configure(text=f"🔥 {trainer.streak}")
        _show_example(word)
        if word["example"] or word["example_vi"]:
            waiting_for_next = True
            result_label.configure(text="✔ Correct! — nhấn Enter để tiếp tục", text_color="#34a853")
        else:
            result_label.configure(text="✔ Correct!", text_color="#34a853")
            root.after(1000, next_question)
        if current_review_stage:
            review_passed_words.append(rd)
    else:
        result_label.configure(text=f"✘ Sai → {trainer.get_question()['answer']}", text_color="#ea4335")
        streak_label.configure(text="🔥 0")
        example_label.configure(text="")
        root.after(2000, next_question)
        if current_review_stage:
            review_failed_words.append(rd)
    update_learn_stats()
    update_mistake_badge()

def _show_example(word):
    parts = []
    if word["example"]:    parts.append(f"📖 {word['example']}")
    if word["example_vi"]: parts.append(f"🇻🇳 {word['example_vi']}")
    example_label.configure(text="\n".join(parts))

def update_learn_stats():
    if trainer:
        tot = trainer.correct_count + trainer.wrong_count
        acc = int(trainer.correct_count/tot*100) if tot else 0
        progress_label.configure(
            text=f"✅ {trainer.correct_count}  ❌ {trainer.wrong_count}  |  Accuracy: {acc}%  |  Best🔥 {trainer.best_streak}")

def show_learn_completion():
    word_label.configure(text="🎉 Hoàn thành!")
    type_label.configure(text="")
    direction_label.configure(text="")
    result_label.configure(text="")
    remain_label.configure(text="")
    progress_bar.set(1.0)
    if trainer:
        tot = trainer.correct_count + trainer.wrong_count
        acc = int(trainer.correct_count/tot*100) if tot else 0
        msg = f"📊 Kết quả:\n✅ {trainer.correct_count}  ❌ {trainer.wrong_count}\n🎯 {acc}%  |  🔥 {trainer.best_streak}"
        if current_review_stage:
            from newword_backend import finish_review_stage
            next_s = {"30min":"1day","1day":"3day","3day":"7day","7day":"30min"}[current_review_stage]
            finish_review_stage(current_review_stage, review_passed_words, review_failed_words)
            if review_passed_words: msg += f"\n✅ {len(review_passed_words)} từ → review_{next_s}"
            if review_failed_words: msg += f"\n🔁 {len(review_failed_words)} từ sai → ôn lại"
        else:
            trainer.finish_session()
            msg += "\n\n⏰ Từ đúng đã lưu vào review_30min.csv"
        example_label.configure(text=msg)
    update_review_badges()
    update_mistake_badge()

def show_stats_popup():
    popup = ctk.CTkToplevel(root)
    popup.title("Thong ke")
    popup.geometry("540x400")
    popup.grab_set()
    set_popup_icon(popup)
    ctk.CTkLabel(popup, text="📊 Thống kê 7 ngày", font=("Arial",18,"bold")).pack(pady=14)
    weekly = get_weekly_stats()
    total_c, total_w = get_total_stats()
    cf = ctk.CTkFrame(popup); cf.pack(fill="both", expand=True, padx=20, pady=8)
    canvas = tk.Canvas(cf, bg="#1a1a2e", highlightthickness=0, height=220)
    canvas.pack(fill="both", expand=True)
    def draw(event=None):
        canvas.delete("all")
        w,h = canvas.winfo_width(), canvas.winfo_height()
        if w<10 or h<10: return
        mx = max((d["correct"]+d["wrong"]) for d in weekly) or 1
        gap,bar_w,pb,pt = w//len(weekly), w//len(weekly)//3, 40, 10
        for i,day in enumerate(weekly):
            xc = gap*i+gap//2
            td = day["correct"]+day["wrong"]
            bh = int((td/mx)*(h-pb-pt))
            ch = int((day["correct"]/mx)*(h-pb-pt)) if td else 0
            wh = bh-ch
            if wh>0: canvas.create_rectangle(xc-bar_w,h-pb-ch-wh,xc+bar_w,h-pb-ch,fill="#ea4335",outline="")
            if ch>0: canvas.create_rectangle(xc-bar_w,h-pb-ch,xc+bar_w,h-pb,fill="#34a853",outline="")
            canvas.create_text(xc,h-pb+8,text=day["label"],fill="#aaa",font=("Arial",10))
            if td: canvas.create_text(xc,h-pb-bh-10,text=str(td),fill="white",font=("Arial",9))
    canvas.bind("<Configure>", draw); canvas.after(50, draw)
    leg = ctk.CTkFrame(popup, fg_color="transparent"); leg.pack(pady=4)
    ctk.CTkLabel(leg, text="■ Đúng", text_color="#34a853", font=("Arial",12)).pack(side="left", padx=10)
    ctk.CTkLabel(leg, text="■ Sai",  text_color="#ea4335", font=("Arial",12)).pack(side="left", padx=10)
    ctk.CTkLabel(popup, text=f"Tổng đúng: {total_c}  |  Tổng sai: {total_w}",
                 font=("Arial",13), text_color="gray").pack(pady=6)

# ════════════════════════════════════════════════
# Review badges
# ════════════════════════════════════════════════

def update_review_badges():
    summary = get_review_summary()
    for stage, btn in review_badge_btns.items():
        info  = summary[stage]
        count = info["count"]
        if count == 0:
            btn.configure(text=f"⏳ {STAGE_LABELS[stage]}\n—", fg_color=("gray25","gray20"), text_color="gray")
        elif info["is_due"]:
            btn.configure(text=f"🔔 {STAGE_LABELS[stage]}\n{count} từ", fg_color="#ea4335", text_color="white")
        else:
            due = info["due_time"]
            if due:
                delta = due - datetime.datetime.now()
                mins  = int(delta.total_seconds()/60)
                ts    = f"{mins}p" if mins<60 else (f"{mins//60}h" if mins<1440 else f"{mins//1440}d")
            else: ts = "—"
            btn.configure(text=f"📚 {STAGE_LABELS[stage]}\n{count}·{ts}", fg_color=("gray25","gray20"), text_color="#8ab4f8")

def update_mistake_badge():
    count = get_mistake_count()
    if count == 0:
        mistake_btn.configure(text="⚠️ Mistakes\n—", fg_color=("gray25","gray20"), text_color="gray")
    else:
        mistake_btn.configure(text=f"⚠️ Mistakes\n{count} từ", fg_color="#9c27b0", text_color="white")

def check_due_on_startup():
    due = get_due_stages()
    if not due: return
    lines = [f"  • review_{s}: {get_stage_word_count(s)} từ" for s in due]
    if messagebox.askyesno("⏰ Nhắc ôn tập", "Có từ cần ôn:\n\n"+"\n".join(lines)+"\n\nÔn ngay không?"):
        _show_review_picker(due)

def _show_review_picker(due):
    if len(due)==1:
        load_review_stage(due[0]); return
    popup = ctk.CTkToplevel(root)
    popup.title("Chon stage")
    popup.geometry("360x300")
    popup.grab_set()
    set_popup_icon(popup)
    ctk.CTkLabel(popup, text="Chọn bài ôn:", font=("Arial",16,"bold")).pack(pady=14)
    for s in due:
        ctk.CTkButton(popup, text=f"review_{s}  —  {get_stage_word_count(s)} từ  ({STAGE_LABELS[s]})",
            font=("Arial",14), height=44,
            command=lambda st=s: [popup.destroy(), load_review_stage(st)]
        ).pack(fill="x", padx=30, pady=5)
    ctk.CTkButton(popup, text="Để sau", fg_color="gray", command=popup.destroy).pack(pady=8)

# ════════════════════════════════════════════════
# VOCAB TAB — logic
# ════════════════════════════════════════════════
VOCAB_HEADERS  = ["word","type","meaning","example","translate_example"]
vocab_preview_rows = []

def _vocab_word_key(row): return (str(row[0]).strip().lower(), str(row[2]).strip().lower())

def vocab_new_file():
    global vocab_csv_path
    path = filedialog.asksaveasfilename(initialdir=BASE_DIR,
        defaultextension=".csv", filetypes=[("CSV","*.csv")], title="Tạo file CSV mới")
    if not path: return
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        csv.writer(f).writerow(VOCAB_HEADERS)
    vocab_csv_path = path
    vocab_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    vocab_status_label.configure(text="File mới tạo xong!", text_color="#34a853")
    vocab_preview_clear(); vocab_clear_entries(); vocab_entries[0].focus()

def vocab_open_file():
    global vocab_csv_path
    path = filedialog.askopenfilename(initialdir=BASE_DIR,
        filetypes=[("CSV","*.csv"),("All","*.*")], title="Chọn file CSV")
    if not path: return
    vocab_csv_path = path
    vocab_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    vocab_preview_clear()
    try:
        with open(path,newline="",encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        data = rows[1:] if rows and rows[0][0].lower() in ("word","english") else rows
        for row in data: vocab_preview_add((row+["","","","",""])[:5])
        vocab_status_label.configure(text=f"Đã load {len(data)} từ.", text_color="#8ab4f8")
    except Exception as e:
        vocab_status_label.configure(text=f"Lỗi: {e}", text_color="#ea4335")
    vocab_clear_entries(); vocab_entries[0].focus()

def vocab_save_row(event=None):
    if vocab_csv_path is None:
        messagebox.showwarning("Chưa chọn file","Tạo hoặc mở file CSV trước!"); return
    values = [e.get().strip() for e in vocab_entries]
    if not values[0] or not values[2]:
        vocab_status_label.configure(text="⚠ Cần nhập Word và Meaning!", text_color="#fbbc04"); return
    # Kiểm tra trùng
    existing = []
    if os.path.exists(vocab_csv_path):
        with open(vocab_csv_path,newline="",encoding="utf-8-sig") as f:
            existing = list(csv.reader(f))
    key = (values[0].lower(), values[2].lower())
    if any(_vocab_word_key(r)==key for r in existing[1:]):
        vocab_status_label.configure(text=f'⚠ "{values[0]}" đã có trong file!', text_color="#fbbc04"); return
    with open(vocab_csv_path,"a",newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not existing: writer.writerow(VOCAB_HEADERS)
        writer.writerow(values)
    vocab_status_label.configure(text=f'✅ Đã lưu "{values[0]}"', text_color="#34a853")
    vocab_clear_entries(); vocab_entries[0].focus()
    vocab_preview_add(values)

def vocab_clear_entries():
    for e in vocab_entries: e.delete(0, tk.END)

def vocab_preview_clear():
    for row_w in vocab_preview_rows:
        for lbl in row_w: lbl.destroy()
    vocab_preview_rows.clear()

def vocab_preview_add(values):
    row_idx = len(vocab_preview_rows)+1
    ws = [140,80,140,200,200]; rw = []
    for col,(val,w) in enumerate(zip(values,ws)):
        lbl = ctk.CTkLabel(vocab_table_frame, text=val if val else "—",
            font=("Arial",12), width=w, anchor="w", text_color="#ccc")
        lbl.grid(row=row_idx, column=col, padx=4, pady=2, sticky="w")
        rw.append(lbl)
    vocab_preview_rows.append(rw)
    vocab_table_scroll.after(50, lambda: vocab_table_scroll._parent_canvas.yview_moveto(1.0))

def make_vocab_tab_handler(idx):
    def h(e):
        if idx < len(vocab_entries)-1: vocab_entries[idx+1].focus()
        else: vocab_save_row()
    return h

# ════════════════════════════════════════════════
# QUIZ TAB — logic
# ════════════════════════════════════════════════

def quiz_load_file():
    global quiz_questions
    path = filedialog.askopenfilename(filetypes=[
        ("Data files","*.csv *.xlsx *.xls"),("CSV","*.csv"),
        ("Excel","*.xlsx *.xls"),("All","*.*")])
    if not path: return
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        df = df.fillna("")
        cols = list(df.columns)
        quiz_questions = []
        for _, row in df.iterrows():
            vals = [str(row.iloc[i]).strip() if i < len(row) else "" for i in range(6)]
            q,ans,a,b,c,d = (vals+["","","","","",""])[:6]
            if q and ans:
                quiz_questions.append({"question":q,"answer":ans.upper(),"A":a,"B":b,"C":c,"D":d})
        count = len(quiz_questions)
        quiz_file_label.configure(text=f"📄 {os.path.basename(path)}  ({count} câu)", text_color="#34a853")
        safe_max = max(2, min(count, 150))   # cap 150, CTkSlider cần to > from_
        quiz_num_slider.configure(to=safe_max, number_of_steps=safe_max-1)
        quiz_num_slider.set(min(count, 10))
        quiz_num_label.configure(text=str(min(count, 10)))
        quiz_status_label.configure(text=f"Đã load {count} câu hỏi.", text_color="#8ab4f8")
        quiz_mistake_badge_update()
        global quiz_in_mistake_mode
        quiz_in_mistake_mode = False
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không đọc được file:\n{e}")

def quiz_load_mistakes():
    global quiz_questions
    if not os.path.exists(quiz_mistake_file):
        messagebox.showinfo("Quiz Mistakes","Chưa có câu nào sai!"); return
    try:
        df = pd.read_csv(quiz_mistake_file)
        df = df.fillna("")
        quiz_questions = []
        for _, row in df.iterrows():
            vals = [str(row.iloc[i]).strip() if i < len(row) else "" for i in range(6)]
            q,ans,a,b,c,d = (vals+["","","","","",""])[:6]
            if q and ans:
                quiz_questions.append({"question":q,"answer":ans.upper(),"A":a,"B":b,"C":c,"D":d})
        count = len(quiz_questions)
        quiz_file_label.configure(text=f"⚠️ Quiz Mistakes  ({count} câu)", text_color="#ea4335")
        safe_max = max(2, count)
        quiz_num_slider.configure(to=safe_max, number_of_steps=safe_max-1)
        quiz_num_slider.set(min(count,10))
        quiz_num_label.configure(text=str(min(count,10)))
        quiz_status_label.configure(text=f"Đã load {count} câu sai.", text_color="#fbbc04")
        global quiz_in_mistake_mode
        quiz_in_mistake_mode = True
    except Exception as e:
        messagebox.showerror("Lỗi", str(e))

def quiz_start():
    global quiz_queue, quiz_correct, quiz_wrong, quiz_total_session, quiz_answered, quiz_timer_id
    if not quiz_questions:
        messagebox.showwarning("Chưa load","Hãy load file câu hỏi trước!"); return
    n = int(quiz_num_slider.get())
    pool = random.sample(quiz_questions, min(n, len(quiz_questions)))
    quiz_queue          = list(pool)
    quiz_correct        = 0
    quiz_wrong          = 0
    quiz_total_session  = len(quiz_queue)
    quiz_answered       = False
    if quiz_timer_id:
        root.after_cancel(quiz_timer_id)
        quiz_timer_id = None
    # Show quiz area
    quiz_setup_area.pack_forget()
    quiz_play_area.pack(fill="both", expand=True, padx=16, pady=8)
    quiz_next_question()

def quiz_next_question():
    global quiz_current, quiz_answered, quiz_timer_id

    quiz_answered = False

    if not quiz_queue:
        quiz_show_result()
        return

    quiz_current = quiz_queue.pop(0)
    q = quiz_current

    # Hiển thị câu hỏi
    quiz_q_label.configure(text=q["question"])
    done = quiz_total_session - len(quiz_queue) - 1
    quiz_progress_bar.set((done)/quiz_total_session if quiz_total_session else 0)
    quiz_remain_label.configure(text=f"{done}/{quiz_total_session}")
    quiz_result_label.configure(text="")

    # Đảo nội dung, giữ nguyên thứ tự label A→B→C→D
    contents = [q["A"], q["B"], q["C"], q["D"]]
    random.shuffle(contents)

    labels = ["A","B","C","D"]
    correct_label = q["answer"]   # label gốc của đáp án đúng, vd "B"
    correct_text  = q[correct_label]   # nội dung đáp án đúng

    options = []
    for label, text in zip(labels, contents):
        options.append({
            "label"     : label,
            "text"      : text,
            "is_correct": (text == correct_text),
        })

    for i, opt in enumerate(options):
        btn = quiz_choice_btns[i]
        btn.configure(
            text=f"{opt['label']}.  {opt['text']}",
            fg_color=("gray20","gray25"), text_color="white",
            state="normal",
            command=lambda o=opt: quiz_on_answer(o, options)
        )

    # Timer
    use_timer = quiz_timer_var.get()
    quiz_timer_bar.configure(progress_color="#1a73e8")
    if use_timer:
        secs = int(quiz_timer_secs.get())
        _quiz_start_timer(secs, secs)
    else:
        quiz_timer_label.configure(text="")
        quiz_timer_bar.set(0)

def _quiz_start_timer(total, left):
    global quiz_time_left, quiz_timer_id
    quiz_time_left = left
    quiz_timer_label.configure(text=f"⏱ {left}s")
    quiz_timer_bar.set(left/total if total else 0)
    if left <= 3:
        quiz_timer_bar.configure(progress_color="#ea4335")
    if left <= 0:
        # Hết giờ → sai
        quiz_on_answer(None, [])
        return
    quiz_timer_id = root.after(1000, lambda: _quiz_start_timer(total, left-1))

def quiz_on_answer(chosen_opt, options):
    global quiz_answered, quiz_correct, quiz_wrong, quiz_timer_id

    if quiz_answered: return
    quiz_answered = True

    # Dừng timer
    if quiz_timer_id:
        root.after_cancel(quiz_timer_id)
        quiz_timer_id = None

    correct_opt = next((o for o in options if o["is_correct"]), None)
    is_correct  = chosen_opt is not None and chosen_opt["is_correct"]

    # Highlight các nút
    for i, opt in enumerate(options):
        btn = quiz_choice_btns[i]
        if opt["is_correct"]:
            btn.configure(fg_color="#34a853", state="disabled")
        elif chosen_opt and opt["label"]==chosen_opt["label"]:
            btn.configure(fg_color="#ea4335", state="disabled")
        else:
            btn.configure(state="disabled")

    if is_correct:
        quiz_correct += 1
        quiz_result_label.configure(text="✔ Đúng!", text_color="#34a853")
        if quiz_in_mistake_mode:
            # Đang luyện mistakes + đúng → xóa khỏi file
            _quiz_remove_from_mistakes(quiz_current)
        # Làm bài thường đúng → không làm gì với mistake file
    else:
        quiz_wrong += 1
        ans_label = quiz_current["answer"]
        ans_text  = quiz_current.get(ans_label,"")
        quiz_result_label.configure(
            text=f"✘ Sai! Đáp án: {ans_label}. {ans_text}" if chosen_opt else f"⏱ Hết giờ! Đáp án: {ans_label}. {ans_text}",
            text_color="#ea4335")
        if quiz_in_mistake_mode:
            # Đang luyện mistakes + sai → xóa vị trí cũ, thêm lại cuối file
            _quiz_move_to_end_of_mistakes(quiz_current)
        else:
            # Làm bài thường sai → ghi vào mistakes (bỏ trùng)
            _quiz_add_to_mistakes(quiz_current)
        quiz_queue.append(quiz_current)   # hỏi lại trong session

    # Tự động qua câu kế
    root.after(2000, quiz_next_question)

def _quiz_add_to_mistakes(q):
    path = quiz_mistake_file
    existing = []
    if os.path.exists(path):
        with open(path,newline="",encoding="utf-8-sig") as f:
            existing = list(csv.reader(f))
    # Kiểm tra trùng theo question
    keys = {r[0].strip().lower() for r in existing[1:] if r}
    if q["question"].strip().lower() in keys:
        return
    with open(path,"a",newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not existing: writer.writerow(QUIZ_HEADERS)
        writer.writerow([q["question"],q["answer"],q["A"],q["B"],q["C"],q["D"]])
    quiz_mistake_badge_update()

def _quiz_remove_from_mistakes(q):
    path = quiz_mistake_file
    if not os.path.exists(path): return
    with open(path,newline="",encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    key    = q["question"].strip().lower()
    header = rows[0] if rows else QUIZ_HEADERS
    data   = [r for r in rows[1:] if r and r[0].strip().lower()!=key]
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)
    quiz_mistake_badge_update()


def _quiz_move_to_end_of_mistakes(q):
    """Sai trong mistake mode → xóa vị trí cũ, thêm lại cuối file."""
    _quiz_remove_from_mistakes(q)
    _quiz_add_to_mistakes(q)

def quiz_show_result():
    quiz_play_area.pack_forget()
    quiz_setup_area.pack(fill="both", expand=True, padx=16, pady=8)
    total = quiz_correct + quiz_wrong
    acc   = int(quiz_correct/total*100) if total else 0
    quiz_status_label.configure(
        text=f"🎉 Xong!  ✅ {quiz_correct}  ❌ {quiz_wrong}  |  {acc}%",
        text_color="#34a853" if acc>=70 else "#fbbc04"
    )
    quiz_mistake_badge_update()

def quiz_mistake_badge_update():
    if not os.path.exists(quiz_mistake_file):
        quiz_mistake_load_btn.configure(text="⚠️ Câu sai\n—", fg_color=("gray25","gray20"), text_color="gray")
        return
    try:
        df  = pd.read_csv(quiz_mistake_file)
        cnt = len(df)
    except: cnt = 0
    if cnt == 0:
        quiz_mistake_load_btn.configure(text="⚠️ Câu sai\n—", fg_color=("gray25","gray20"), text_color="gray")
    else:
        quiz_mistake_load_btn.configure(text=f"⚠️ Câu sai\n{cnt} câu", fg_color="#c0392b", text_color="white")

def quiz_slider_changed(val):
    quiz_num_label.configure(text=str(int(float(val))))

def quiz_timer_toggle():
    state = "normal" if quiz_timer_var.get() else "disabled"
    quiz_timer_secs.configure(state=state)

# ════════════════════════════════════════════════
# QUIZ ADD TAB — logic
# ════════════════════════════════════════════════

def quiz_add_new_file():
    global quiz_add_csv_path
    path = filedialog.asksaveasfilename(initialdir=BASE_DIR,
        defaultextension=".csv", filetypes=[("CSV","*.csv")], title="Tạo file câu hỏi mới")
    if not path: return
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        csv.writer(f).writerow(QUIZ_ADD_HEADERS)
    quiz_add_csv_path = path
    quiz_add_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    quiz_add_status_label.configure(text="File mới tạo xong!", text_color="#34a853")
    quiz_add_preview_clear(); quiz_add_clear_entries(); quiz_add_entries[0].focus()

def quiz_add_open_file():
    global quiz_add_csv_path
    path = filedialog.askopenfilename(initialdir=BASE_DIR,
        filetypes=[("CSV","*.csv"),("All","*.*")])
    if not path: return
    quiz_add_csv_path = path
    quiz_add_file_label.configure(text=f"📄 {os.path.basename(path)}", text_color="#34a853")
    quiz_add_preview_clear()
    try:
        with open(path,newline="",encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        data = rows[1:] if rows and rows[0][0].lower()=="question" else rows
        for row in data: quiz_add_preview_add((row+["","","","","",""])[:6])
        quiz_add_status_label.configure(text=f"Đã load {len(data)} câu.", text_color="#8ab4f8")
    except Exception as e:
        quiz_add_status_label.configure(text=f"Lỗi: {e}", text_color="#ea4335")
    quiz_add_clear_entries(); quiz_add_entries[0].focus()

def quiz_add_save_row(event=None):
    if quiz_add_csv_path is None:
        messagebox.showwarning("Chưa chọn file","Tạo hoặc mở file trước!"); return
    values = [e.get().strip() for e in quiz_add_entries]
    if not values[0] or not values[1]:
        quiz_add_status_label.configure(text="⚠ Cần nhập Question và Answer!", text_color="#fbbc04"); return
    ans = values[1].upper()
    if ans not in ("A","B","C","D"):
        quiz_add_status_label.configure(text="⚠ Answer phải là A, B, C hoặc D!", text_color="#fbbc04"); return
    values[1] = ans
    # Kiểm tra trùng
    existing = []
    if os.path.exists(quiz_add_csv_path):
        with open(quiz_add_csv_path,newline="",encoding="utf-8-sig") as f:
            existing = list(csv.reader(f))
    keys = {r[0].strip().lower() for r in existing[1:] if r}
    if values[0].lower() in keys:
        quiz_add_status_label.configure(text=f'⚠ Câu hỏi này đã có!', text_color="#fbbc04"); return
    with open(quiz_add_csv_path,"a",newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not existing: writer.writerow(QUIZ_ADD_HEADERS)
        writer.writerow(values)
    quiz_add_status_label.configure(text=f'✅ Đã lưu câu hỏi', text_color="#34a853")
    quiz_add_clear_entries(); quiz_add_entries[0].focus()
    quiz_add_preview_add(values)

def quiz_add_clear_entries():
    for e in quiz_add_entries: e.delete(0, tk.END)

def quiz_add_preview_clear():
    for rw in quiz_add_preview_rows:
        for lbl in rw: lbl.destroy()
    quiz_add_preview_rows.clear()

def quiz_add_preview_add(values):
    row_idx = len(quiz_add_preview_rows)+1
    ws = [220,60,100,100,100,100]; rw = []
    for col,(val,w) in enumerate(zip(values,ws)):
        lbl = ctk.CTkLabel(quiz_add_table_frame, text=val if val else "—",
            font=("Arial",11), width=w, anchor="w", text_color="#ccc")
        lbl.grid(row=row_idx, column=col, padx=3, pady=2, sticky="w")
        rw.append(lbl)
    quiz_add_preview_rows.append(rw)
    quiz_add_table_scroll.after(50, lambda: quiz_add_table_scroll._parent_canvas.yview_moveto(1.0))

def make_quiz_add_tab_handler(idx):
    def h(e):
        if idx < len(quiz_add_entries)-1: quiz_add_entries[idx+1].focus()
        else: quiz_add_save_row()
    return h

# ════════════════════════════════════════════════
# ROOT WINDOW
# ════════════════════════════════════════════════

root = ctk.CTk()
root.title("LexFlow")
try:
    root.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass
root.geometry("920x760")
root.minsize(800, 640)

# ── Header ─────────────────────────────────────
header = ctk.CTkFrame(root, fg_color=("gray18","gray12"), corner_radius=0)
header.pack(fill="x")

ctk.CTkLabel(header, text="⚡ LexFlow", font=("Arial",22,"bold")).pack(side="left", padx=16, pady=10)

tab_bar = ctk.CTkFrame(header, fg_color="transparent")
tab_bar.pack(side="left", padx=4)

tab_learn_btn   = ctk.CTkButton(tab_bar, text="📚 Học từ",      width=108, height=30,
    command=lambda: show_tab("learn"),    fg_color="#1a73e8", corner_radius=8)
tab_learn_btn.pack(side="left", padx=3)

tab_vocab_btn   = ctk.CTkButton(tab_bar, text="✏️ Thêm từ",    width=108, height=30,
    command=lambda: show_tab("vocab"),    fg_color=("gray25","gray20"), corner_radius=8)
tab_vocab_btn.pack(side="left", padx=3)

tab_quiz_btn    = ctk.CTkButton(tab_bar, text="📝 Trắc nghiệm", width=120, height=30,
    command=lambda: show_tab("quiz"),     fg_color=("gray25","gray20"), corner_radius=8)
tab_quiz_btn.pack(side="left", padx=3)

tab_quiz_add_btn= ctk.CTkButton(tab_bar, text="➕ Thêm câu",    width=108, height=30,
    command=lambda: show_tab("quiz_add"), fg_color=("gray25","gray20"), corner_radius=8)
tab_quiz_add_btn.pack(side="left", padx=3)

stats_btn = ctk.CTkButton(header, text="📊 Thống kê", width=100, height=30,
    command=show_stats_popup, fg_color=("gray30","gray25"))
stats_btn.pack(side="right", padx=16)

# ════════════════════════════════════════════════
# LEARN FRAME
# ════════════════════════════════════════════════

learn_frame = ctk.CTkFrame(root, fg_color="transparent")
learn_frame.pack(fill="both", expand=True)

# Badges
badge_outer = ctk.CTkFrame(learn_frame, fg_color=("gray16","gray10"), corner_radius=8)
badge_outer.pack(fill="x", padx=14, pady=(8,4))
ctk.CTkLabel(badge_outer, text="⏰ SRS:", font=("Arial",11,"bold"), text_color="#fbbc04").pack(side="left", padx=8)

review_badge_btns = {}
for stage in REVIEW_STAGES:
    b = ctk.CTkButton(badge_outer, text=f"⏳ {STAGE_LABELS[stage]}\n—",
        width=120, height=42, font=("Arial",10), corner_radius=8,
        fg_color=("gray25","gray20"), text_color="gray",
        command=lambda s=stage: load_review_stage(s))
    b.pack(side="left", padx=3, pady=5)
    review_badge_btns[stage] = b

mistake_btn = ctk.CTkButton(badge_outer, text="⚠️ Mistakes\n—",
    width=110, height=42, font=("Arial",10), corner_radius=8,
    fg_color=("gray25","gray20"), text_color="gray", command=load_mistake_file)
mistake_btn.pack(side="left", padx=3, pady=5)

# Controls
ctrl_bar = ctk.CTkFrame(learn_frame, fg_color="transparent")
ctrl_bar.pack(fill="x", padx=14, pady=4)

mode_option = ctk.CTkOptionMenu(ctrl_bar, values=["random","en_vi","vi_en"], width=105)
mode_option.pack(side="left", padx=(0,6))

quiz_mode_var = tk.StringVar(value="typing")
quiz_mode_var.trace_add("write", switch_quiz_mode)
ctk.CTkSegmentedButton(ctrl_bar, values=["typing","multiple_choice"],
    variable=quiz_mode_var, width=220).pack(side="left", padx=6)

streak_label = ctk.CTkLabel(ctrl_bar, text="🔥 0", font=("Arial",16,"bold"), text_color="#fbbc04")
streak_label.pack(side="left", padx=10)

ctk.CTkButton(ctrl_bar, text="📂 Load", command=load_file, width=90).pack(side="right")

file_info_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",11), text_color="#8ab4f8")
file_info_label.pack(anchor="w", padx=18)

prog_frame = ctk.CTkFrame(learn_frame, fg_color="transparent")
prog_frame.pack(fill="x", padx=14, pady=(2,2))
progress_bar = ctk.CTkProgressBar(prog_frame, height=8)
progress_bar.set(0)
progress_bar.pack(fill="x", side="left", expand=True, padx=(0,6))
remain_label = ctk.CTkLabel(prog_frame, text="0/0", font=("Arial",11), width=60)
remain_label.pack(side="right")

direction_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",12), text_color="#8ab4f8")
direction_label.pack()

word_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",28,"bold"), wraplength=700)
word_label.pack(pady=(10,4))

type_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",14), text_color="gray")
type_label.pack()

answer_entry = ctk.CTkEntry(learn_frame, width=320, height=40, font=("Arial",16),
    placeholder_text="Nhập đáp án…")
answer_entry.bind("<Return>", submit_answer)

mc_frame = ctk.CTkFrame(learn_frame, fg_color="transparent")
learn_mc_buttons = []
for ri in range(2):
    for ci in range(2):
        b = ctk.CTkButton(mc_frame, text="", width=290, height=46, font=("Arial",13),
            corner_radius=10, fg_color=("gray20","gray25"), hover_color=("gray30","gray35"),
            command=lambda: None)
        b.grid(row=ri, column=ci, padx=7, pady=5)
        learn_mc_buttons.append(b)

result_label  = ctk.CTkLabel(learn_frame, text="", font=("Arial",14))
result_label.pack(pady=4)

example_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",13),
    wraplength=680, justify="left", text_color="#ccc")
example_label.pack(pady=5)

progress_label = ctk.CTkLabel(learn_frame, text="", font=("Arial",11), text_color="gray")
progress_label.pack()

ctk.CTkLabel(learn_frame,
    text="Cre: Nguyen Le Anh Tuan  |  MOMO: 0835787489  |  MBbank: 240120076868",
    font=("Arial",10), text_color="#333").pack(side="bottom", pady=5)

switch_quiz_mode()

# ════════════════════════════════════════════════
# VOCAB FRAME
# ════════════════════════════════════════════════

vocab_frame = ctk.CTkFrame(root, fg_color="transparent")

fa = ctk.CTkFrame(vocab_frame, fg_color="transparent")
fa.pack(fill="x", padx=18, pady=(12,4))
ctk.CTkButton(fa, text="📄 Tạo file mới",   width=130, command=vocab_new_file, fg_color="#34a853").pack(side="left", padx=(0,8))
ctk.CTkButton(fa, text="📂 Mở file có sẵn", width=140, command=vocab_open_file, fg_color="#1a73e8").pack(side="left")
vocab_file_label = ctk.CTkLabel(fa, text="Chưa chọn file", font=("Arial",12), text_color="gray")
vocab_file_label.pack(side="left", padx=14)

vi_sec = ctk.CTkFrame(vocab_frame, fg_color=("gray18","gray12"), corner_radius=10)
vi_sec.pack(fill="x", padx=18, pady=8)
ctk.CTkLabel(vi_sec, text="Nhập từ mới (Enter = nhảy ô / lưu)", font=("Arial",12,"bold")).pack(pady=(8,4))

v_entry_row = ctk.CTkFrame(vi_sec, fg_color="transparent")
v_entry_row.pack(padx=12, pady=(0,12))

v_labels = ["Word *","Type","Meaning *","Example","Translate Example"]
v_widths  = [130,70,130,190,190]
v_hints   = ["run","v.","chạy","I run daily.","Tôi chạy mỗi ngày."]
vocab_entries = []
for lbl,w,hint in zip(v_labels, v_widths, v_hints):
    cf = ctk.CTkFrame(v_entry_row, fg_color="transparent"); cf.pack(side="left", padx=4)
    ctk.CTkLabel(cf, text=lbl, font=("Arial",11), text_color="#8ab4f8").pack(anchor="w")
    e = ctk.CTkEntry(cf, width=w, height=34, font=("Arial",12), placeholder_text=hint)
    e.pack(); vocab_entries.append(e)

for i,e in enumerate(vocab_entries):
    h = make_vocab_tab_handler(i)
    e.bind("<Return>", h); e.bind("<Tab>", h)

ctk.CTkButton(vi_sec, text="💾 Lưu từ", command=vocab_save_row,
    width=140, fg_color="#34a853").pack(pady=(0,10))

vocab_status_label = ctk.CTkLabel(vocab_frame, text="", font=("Arial",12))
vocab_status_label.pack(pady=(0,4))

ctk.CTkLabel(vocab_frame, text="Danh sách từ trong file:", font=("Arial",12,"bold")).pack(anchor="w", padx=18)

vocab_table_scroll = ctk.CTkScrollableFrame(vocab_frame, height=210)
vocab_table_scroll.pack(fill="both", expand=True, padx=18, pady=(4,14))
vocab_table_frame  = ctk.CTkFrame(vocab_table_scroll, fg_color="transparent")
vocab_table_frame.pack(fill="both", expand=True)

for col,(h,w) in enumerate(zip(VOCAB_HEADERS,[140,80,140,200,200])):
    ctk.CTkLabel(vocab_table_frame, text=h.upper(), font=("Arial",11,"bold"),
        width=w, anchor="w", text_color="#8ab4f8").grid(row=0,column=col,padx=4,pady=(0,4),sticky="w")

# ════════════════════════════════════════════════
# QUIZ FRAME
# ════════════════════════════════════════════════

quiz_frame = ctk.CTkFrame(root, fg_color="transparent")

# Setup area (hiện khi chưa làm / sau khi xong)
quiz_setup_area = ctk.CTkFrame(quiz_frame, fg_color="transparent")
quiz_setup_area.pack(fill="both", expand=True, padx=16, pady=8)

# Row 1: Load file + mistake
qr1 = ctk.CTkFrame(quiz_setup_area, fg_color="transparent")
qr1.pack(fill="x", pady=(8,4))
ctk.CTkButton(qr1, text="📂 Load file câu hỏi", width=160, fg_color="#1a73e8",
    command=quiz_load_file).pack(side="left", padx=(0,10))
quiz_mistake_load_btn = ctk.CTkButton(qr1, text="⚠️ Câu sai\n—", width=110, height=42,
    font=("Arial",11), fg_color=("gray25","gray20"), text_color="gray",
    command=quiz_load_mistakes)
quiz_mistake_load_btn.pack(side="left")
quiz_file_label = ctk.CTkLabel(qr1, text="Chưa load file", font=("Arial",12), text_color="gray")
quiz_file_label.pack(side="left", padx=14)

# Row 2: Số câu
qr2 = ctk.CTkFrame(quiz_setup_area, fg_color=("gray18","gray12"), corner_radius=10)
qr2.pack(fill="x", pady=8)
ctk.CTkLabel(qr2, text="Số câu muốn làm:", font=("Arial",13,"bold")).pack(side="left", padx=12, pady=10)
quiz_num_slider = ctk.CTkSlider(qr2, from_=1, to=150, number_of_steps=149,
    command=quiz_slider_changed, width=260)
quiz_num_slider.set(10)
quiz_num_slider.pack(side="left", padx=10)
quiz_num_label = ctk.CTkLabel(qr2, text="10", font=("Arial",14,"bold"), width=36)
quiz_num_label.pack(side="left")

# Row 3: Timer
qr3 = ctk.CTkFrame(quiz_setup_area, fg_color=("gray18","gray12"), corner_radius=10)
qr3.pack(fill="x", pady=4)
quiz_timer_var = tk.BooleanVar(value=False)
ctk.CTkCheckBox(qr3, text="⏱ Bật timer mỗi câu", variable=quiz_timer_var,
    command=quiz_timer_toggle, font=("Arial",13)).pack(side="left", padx=12, pady=10)
ctk.CTkLabel(qr3, text="Giây:", font=("Arial",12)).pack(side="left", padx=(20,4))
quiz_timer_secs = ctk.CTkEntry(qr3, width=60, height=32, font=("Arial",13))
quiz_timer_secs.insert(0,"30")
quiz_timer_secs.configure(state="disabled")
quiz_timer_secs.pack(side="left")

# Start button
ctk.CTkButton(quiz_setup_area, text="▶  Bắt đầu làm bài", height=46,
    font=("Arial",16,"bold"), fg_color="#34a853", command=quiz_start).pack(pady=14)

quiz_status_label = ctk.CTkLabel(quiz_setup_area, text="", font=("Arial",14))
quiz_status_label.pack()

# Play area (ẩn, hiện khi đang làm)
quiz_play_area = ctk.CTkFrame(quiz_frame, fg_color="transparent")

# Timer bar + label
qt_row = ctk.CTkFrame(quiz_play_area, fg_color="transparent")
qt_row.pack(fill="x", padx=14, pady=(6,2))
quiz_timer_label = ctk.CTkLabel(qt_row, text="", font=("Arial",12,"bold"), text_color="#fbbc04", width=60)
quiz_timer_label.pack(side="left")
quiz_timer_bar = ctk.CTkProgressBar(qt_row, height=8, progress_color="#1a73e8")
quiz_timer_bar.set(0)
quiz_timer_bar.pack(fill="x", side="left", expand=True, padx=6)

# Progress
qp_row = ctk.CTkFrame(quiz_play_area, fg_color="transparent")
qp_row.pack(fill="x", padx=14, pady=2)
quiz_progress_bar = ctk.CTkProgressBar(qp_row, height=8, progress_color="#34a853")
quiz_progress_bar.set(0)
quiz_progress_bar.pack(fill="x", side="left", expand=True, padx=(0,6))
quiz_remain_label = ctk.CTkLabel(qp_row, text="0/0", font=("Arial",11), width=50)
quiz_remain_label.pack(side="right")

# Question
quiz_q_label = ctk.CTkLabel(quiz_play_area, text="", font=("Arial",20,"bold"),
    wraplength=740, justify="center")
quiz_q_label.pack(pady=(14,10))

# 4 choice buttons — 2x2 grid
quiz_choices_frame = ctk.CTkFrame(quiz_play_area, fg_color="transparent")
quiz_choices_frame.pack(pady=6)
quiz_choice_btns = []
for ri in range(2):
    for ci in range(2):
        b = ctk.CTkButton(quiz_choices_frame, text="", width=350, height=56,
            font=("Arial",14), corner_radius=10,
            fg_color=("gray20","gray25"), hover_color=("gray30","gray35"),
            command=lambda: None)
        b.grid(row=ri, column=ci, padx=8, pady=6)
        quiz_choice_btns.append(b)

quiz_result_label = ctk.CTkLabel(quiz_play_area, text="", font=("Arial",15))
quiz_result_label.pack(pady=6)

ctk.CTkButton(quiz_play_area, text="⏭ Bỏ qua & kết thúc", width=180,
    fg_color="gray", command=quiz_show_result).pack(pady=4)

# ════════════════════════════════════════════════
# QUIZ ADD FRAME
# ════════════════════════════════════════════════

quiz_add_frame = ctk.CTkFrame(root, fg_color="transparent")

qa_fa = ctk.CTkFrame(quiz_add_frame, fg_color="transparent")
qa_fa.pack(fill="x", padx=18, pady=(12,4))
ctk.CTkButton(qa_fa, text="📄 Tạo file mới",   width=130, command=quiz_add_new_file, fg_color="#34a853").pack(side="left", padx=(0,8))
ctk.CTkButton(qa_fa, text="📂 Mở file có sẵn", width=140, command=quiz_add_open_file, fg_color="#1a73e8").pack(side="left")
quiz_add_file_label = ctk.CTkLabel(qa_fa, text="Chưa chọn file", font=("Arial",12), text_color="gray")
quiz_add_file_label.pack(side="left", padx=14)

qa_sec = ctk.CTkFrame(quiz_add_frame, fg_color=("gray18","gray12"), corner_radius=10)
qa_sec.pack(fill="x", padx=18, pady=8)
ctk.CTkLabel(qa_sec, text="Nhập câu hỏi mới (Enter = nhảy ô / lưu)", font=("Arial",12,"bold")).pack(pady=(8,4))

qa_entry_row = ctk.CTkFrame(qa_sec, fg_color="transparent")
qa_entry_row.pack(padx=12, pady=(0,12))

qa_labels = ["Question *","Answer *","A","B","C","D"]
qa_widths  = [220,        70,        110,110,110,110]
qa_hints   = ["2+2=?",   "B",       "3","4","5","6"]
qa_colors  = ["#8ab4f8","#fbbc04","#ccc","#ccc","#ccc","#ccc"]
quiz_add_entries = []
for lbl,w,hint,col in zip(qa_labels,qa_widths,qa_hints,qa_colors):
    cf = ctk.CTkFrame(qa_entry_row, fg_color="transparent"); cf.pack(side="left", padx=4)
    ctk.CTkLabel(cf, text=lbl, font=("Arial",11), text_color=col).pack(anchor="w")
    e = ctk.CTkEntry(cf, width=w, height=34, font=("Arial",12), placeholder_text=hint)
    e.pack(); quiz_add_entries.append(e)

for i,e in enumerate(quiz_add_entries):
    h = make_quiz_add_tab_handler(i)
    e.bind("<Return>", h); e.bind("<Tab>", h)

ctk.CTkButton(qa_sec, text="💾 Lưu câu hỏi", command=quiz_add_save_row,
    width=150, fg_color="#34a853").pack(pady=(0,10))

quiz_add_status_label = ctk.CTkLabel(quiz_add_frame, text="", font=("Arial",12))
quiz_add_status_label.pack(pady=(0,4))

ctk.CTkLabel(quiz_add_frame, text="Danh sách câu hỏi:", font=("Arial",12,"bold")).pack(anchor="w", padx=18)

quiz_add_table_scroll = ctk.CTkScrollableFrame(quiz_add_frame, height=210)
quiz_add_table_scroll.pack(fill="both", expand=True, padx=18, pady=(4,14))
quiz_add_table_frame  = ctk.CTkFrame(quiz_add_table_scroll, fg_color="transparent")
quiz_add_table_frame.pack(fill="both", expand=True)

for col,(h,w) in enumerate(zip(QUIZ_ADD_HEADERS,[220,60,100,100,100,100])):
    ctk.CTkLabel(quiz_add_table_frame, text=h.upper(), font=("Arial",11,"bold"),
        width=w, anchor="w", text_color="#8ab4f8").grid(row=0,column=col,padx=3,pady=(0,4),sticky="w")

# ════════════════════════════════════════════════
# KHỞI ĐỘNG
# ════════════════════════════════════════════════

try:
    update_review_badges()
    update_mistake_badge()
    quiz_mistake_badge_update()
    root.after(500, check_due_on_startup)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
except Exception as e:
    import traceback
    with open("error_log.txt","w",encoding="utf-8") as f:
        traceback.print_exc(file=f)
    messagebox.showerror("Lỗi", str(e)+"\n\nXem error_log.txt")