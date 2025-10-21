import sqlite3
import os
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from apscheduler.schedulers.background import BackgroundScheduler
from plyer import notification

# ---------- Config ----------
DB_PATH = os.path.join(os.path.expanduser("~"), ".teacher_reminder.db")
DATE_FORMAT = "%Y-%m-%d %H:%M"
# ----------------------------

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        recurring TEXT DEFAULT '',
        done INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def add_reminder_db(title, remind_at_str, recurring=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO reminders (title, remind_at, recurring) VALUES (?, ?, ?)",
              (title, remind_at_str, recurring))
    conn.commit()
    conn.close()

def delete_reminder_db(rem_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id = ?", (rem_id,))
    conn.commit()
    conn.close()

def get_all_reminders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, remind_at, recurring, done FROM reminders ORDER BY remind_at")
    rows = c.fetchall()
    conn.close()
    return rows
# ----------------------------

# ---------- Notification / Scheduler ----------
scheduler = BackgroundScheduler()

def show_notification(title, message):
    # plyer handles cross-platform notifications reasonably; OS behavior may vary.
    notification.notify(title=title, message=message, app_name="Teacher Reminder", timeout=10)

def schedule_job(rem_id, title, remind_time):
    run_date = remind_time
    job_id = f"rem_{rem_id}"
    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    scheduler.add_job(func=notify_and_mark, trigger='date', run_date=run_date, args=[rem_id, title], id=job_id)
    
def notify_and_mark(rem_id, title):
    show_notification("Reminder", title)
    # For MVP we won't mark recurring; just show notification.
    # Could update DB (e.g., mark done) if desired.
# ----------------------------

# ---------- GUI ----------
class ReminderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automated Teacher Reminder - MVP")
        self.geometry("640x420")
        self.create_widgets()
        self.refresh_list()
        # Start scheduler
        scheduler.start()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Add reminder form
        input_frame = ttk.LabelFrame(frm, text="Add Reminder")
        input_frame.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(input_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.title_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(input_frame, text="Date & Time (YYYY-MM-DD HH:MM):").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.dt_var = tk.StringVar(value=(datetime.now().strftime(DATE_FORMAT)))
        ttk.Entry(input_frame, textvariable=self.dt_var, width=25).grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Button(input_frame, text="Add Reminder", command=self.add_reminder).grid(row=2, column=0, columnspan=2, pady=8)

        # Reminders list
        list_frame = ttk.LabelFrame(frm, text="Scheduled Reminders")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tree = ttk.Treeview(list_frame, columns=("id","title","time"), show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("time", text="Remind At")
        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("title", width=320)
        self.tree.column("time", width=180)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_list).pack(side=tk.LEFT, padx=6)

    def add_reminder(self):
        title = self.title_var.get().strip()
        dt_str = self.dt_var.get().strip()
        if not title or not dt_str:
            messagebox.showwarning("Input error", "Please provide title and date/time.")
            return
        try:
            dt = datetime.strptime(dt_str, DATE_FORMAT)
        except Exception as e:
            messagebox.showerror("Format error", f"Date/time format incorrect. Use {DATE_FORMAT}")
            return
        add_reminder_db(title, dt_str)
        # Get ID of last inserted row to schedule (simpler: reload all and schedule)
        self.refresh_list()
        messagebox.showinfo("Added", "Reminder added and scheduled.")

    def refresh_list(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = get_all_reminders()
        for r in rows:
            rid, title, remind_at, recurring, done = r
            self.tree.insert("", tk.END, values=(rid, title, remind_at))
            # schedule if in future
            try:
                dt = datetime.strptime(remind_at, DATE_FORMAT)
                if dt > datetime.now():
                    schedule_job(rid, title, dt)
            except Exception:
                pass

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a reminder to delete.")
            return
        item = sel[0]
        vals = self.tree.item(item, "values")
        rem_id = vals[0]
        delete_reminder_db(rem_id)
        try:
            scheduler.remove_job(f"rem_{rem_id}")
        except Exception:
            pass
        self.refresh_list()
        messagebox.showinfo("Deleted", "Reminder deleted.")

if __name__ == "__main__":
    init_db()
    # Run GUI in main thread (APScheduler runs background threads)
    app = ReminderApp()
    app.mainloop()
    # Shutdown scheduler when app closes
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
