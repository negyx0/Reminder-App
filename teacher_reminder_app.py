import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import datetime
import threading
import time
from plyer import notification

# -----------------------------
# DATABASE SETUP
# -----------------------------
conn = sqlite3.connect("reminders.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        remind_time TEXT NOT NULL
    )
""")
conn.commit()

# -----------------------------
# FUNCTIONS
# -----------------------------
def add_reminder():
    title = title_entry.get()
    desc = desc_entry.get("1.0", "end-1c")
    remind_time = time_entry.get()

    if not title or not remind_time:
        messagebox.showerror("Error", "Please fill in all required fields.")
        return

    try:
        datetime.datetime.strptime(remind_time, "%Y-%m-%d %H:%M")
    except ValueError:
        messagebox.showerror("Error", "Invalid date/time format. Use YYYY-MM-DD HH:MM.")
        return

    cursor.execute("INSERT INTO reminders (title, description, remind_time) VALUES (?, ?, ?)",
                   (title, desc, remind_time))
    conn.commit()
    messagebox.showinfo("Success", "Reminder added successfully!")
    load_reminders()
    title_entry.delete(0, tk.END)
    desc_entry.delete("1.0", tk.END)
    time_entry.delete(0, tk.END)


def delete_reminder():
    selected = reminder_table.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a reminder to delete.")
        return
    item = reminder_table.item(selected)
    reminder_id = item["values"][0]
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    load_reminders()


def load_reminders():
    for row in reminder_table.get_children():
        reminder_table.delete(row)
    cursor.execute("SELECT * FROM reminders")
    for row in cursor.fetchall():
        reminder_table.insert("", "end", values=row)


def check_reminders():
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("SELECT * FROM reminders WHERE remind_time = ?", (now,))
        reminders = cursor.fetchall()
        for reminder in reminders:
            notification.notify(
                title=f"Reminder: {reminder[1]}",
                message=reminder[2] or "No description",
                timeout=10
            )
        time.sleep(60)  # Check every 60 seconds


# -----------------------------
# UI SETUP
# -----------------------------
app = tk.Tk()
app.title("Automated Teacher Reminder System")
app.geometry("700x500")
app.configure(bg="#f0f4f7")

tk.Label(app, text="Automated Teacher Reminder System", font=("Montserrat Semibold", 16), bg="#f0f4f7").pack(pady=10)

frame = tk.Frame(app, bg="#f0f4f7")
frame.pack(pady=10)

tk.Label(frame, text="Title:", bg="#f0f4f7").grid(row=0, column=0, padx=5, pady=5)
title_entry = tk.Entry(frame, width=40)
title_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(frame, text="Description:", bg="#f0f4f7").grid(row=1, column=0, padx=5, pady=5)
desc_entry = tk.Text(frame, height=3, width=40)
desc_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(frame, text="Remind Time (YYYY-MM-DD HH:MM):", bg="#f0f4f7").grid(row=2, column=0, padx=5, pady=5)
time_entry = tk.Entry(frame, width=40)
time_entry.grid(row=2, column=1, padx=5, pady=5)

add_btn = tk.Button(frame, text="Add Reminder", command=add_reminder, bg="#4CAF50", fg="white", width=15)
add_btn.grid(row=3, column=1, pady=10, sticky="e")

# Reminder table
columns = ("ID", "Title", "Description", "Remind Time")
reminder_table = ttk.Treeview(app, columns=columns, show="headings")
for col in columns:
    reminder_table.heading(col, text=col)
    reminder_table.column(col, width=150)
reminder_table.pack(pady=10)

delete_btn = tk.Button(app, text="Delete Selected", command=delete_reminder, bg="#E53935", fg="white", width=15)
delete_btn.pack(pady=5)

load_reminders()

# -----------------------------
# BACKGROUND THREAD
# -----------------------------
thread = threading.Thread(target=check_reminders, daemon=True)
thread.start()

app.mainloop()
