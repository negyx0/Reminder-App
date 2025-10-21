import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import threading
import time
from plyer import notification
import json
import winsound
import platform

class TeacherReminderSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Automated Teacher Reminder System")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        # Initialize database
        self.init_database()
        
        # Current user
        self.current_user = None
        
        # Start notification checker thread
        self.running = True
        self.notification_thread = threading.Thread(target=self.check_reminders, daemon=True)
        self.notification_thread.start()
        
        # Show login screen
        self.show_login_screen()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        self.conn = sqlite3.connect('teacher_reminders.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Reminders table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reminder_date DATE NOT NULL,
                reminder_time TIME NOT NULL,
                category TEXT,
                status TEXT DEFAULT 'pending',
                repeat_type TEXT DEFAULT 'once',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified INTEGER DEFAULT 0,
                advance_notified INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Settings table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                theme TEXT DEFAULT 'light',
                notification_sound INTEGER DEFAULT 1,
                email_notifications INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Migrate existing database - add advance_notified column if it doesn't exist
        self.migrate_database()
        
        self.conn.commit()
    
    def migrate_database(self):
        """Add new columns to existing database if they don't exist"""
        try:
            # Check if advance_notified column exists
            self.cursor.execute("PRAGMA table_info(reminders)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'advance_notified' not in columns:
                self.cursor.execute("ALTER TABLE reminders ADD COLUMN advance_notified INTEGER DEFAULT 0")
                print("Database migrated: Added advance_notified column")
                self.conn.commit()
        except Exception as e:
            print(f"Migration error: {e}")
    
    def show_login_screen(self):
        """Display login interface"""
        self.clear_window()
        
        # Login frame
        login_frame = tk.Frame(self.root, bg="white", relief=tk.RAISED, bd=2)
        login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=350)
        
        # Title
        tk.Label(login_frame, text="Teacher Reminder System", 
                font=("Arial", 20, "bold"), bg="white", fg="#2c3e50").pack(pady=20)
        
        # Username
        tk.Label(login_frame, text="Username:", font=("Arial", 12), 
                bg="white").pack(pady=5)
        self.username_entry = tk.Entry(login_frame, font=("Arial", 12), width=30)
        self.username_entry.pack(pady=5)
        
        # Password
        tk.Label(login_frame, text="Password:", font=("Arial", 12), 
                bg="white").pack(pady=5)
        self.password_entry = tk.Entry(login_frame, font=("Arial", 12), 
                                      width=30, show="*")
        self.password_entry.pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(login_frame, bg="white")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Login", command=self.login, 
                 bg="#3498db", fg="white", font=("Arial", 12), 
                 width=12, cursor="hand2").grid(row=0, column=0, padx=5)
        
        tk.Button(btn_frame, text="Register", command=self.show_register_screen,
                 bg="#2ecc71", fg="white", font=("Arial", 12),
                 width=12, cursor="hand2").grid(row=0, column=1, padx=5)
    
    def show_register_screen(self):
        """Display registration interface"""
        self.clear_window()
        
        # Register frame
        reg_frame = tk.Frame(self.root, bg="white", relief=tk.RAISED, bd=2)
        reg_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=400)
        
        tk.Label(reg_frame, text="Create New Account", 
                font=("Arial", 20, "bold"), bg="white", fg="#2c3e50").pack(pady=20)
        
        # Full Name
        tk.Label(reg_frame, text="Full Name:", font=("Arial", 12), bg="white").pack(pady=5)
        self.fullname_entry = tk.Entry(reg_frame, font=("Arial", 12), width=30)
        self.fullname_entry.pack(pady=5)
        
        # Username
        tk.Label(reg_frame, text="Username:", font=("Arial", 12), bg="white").pack(pady=5)
        self.reg_username_entry = tk.Entry(reg_frame, font=("Arial", 12), width=30)
        self.reg_username_entry.pack(pady=5)
        
        # Password
        tk.Label(reg_frame, text="Password:", font=("Arial", 12), bg="white").pack(pady=5)
        self.reg_password_entry = tk.Entry(reg_frame, font=("Arial", 12), width=30, show="*")
        self.reg_password_entry.pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(reg_frame, bg="white")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Register", command=self.register,
                 bg="#2ecc71", fg="white", font=("Arial", 12),
                 width=12, cursor="hand2").grid(row=0, column=0, padx=5)
        
        tk.Button(btn_frame, text="Back to Login", command=self.show_login_screen,
                 bg="#95a5a6", fg="white", font=("Arial", 12),
                 width=12, cursor="hand2").grid(row=0, column=1, padx=5)
    
    def register(self):
        """Register new user"""
        full_name = self.fullname_entry.get().strip()
        username = self.reg_username_entry.get().strip()
        password = self.reg_password_entry.get().strip()
        
        if not full_name or not username or not password:
            messagebox.showerror("Error", "All fields are required!")
            return
        
        try:
            self.cursor.execute("INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
                              (username, password, full_name))
            user_id = self.cursor.lastrowid
            
            # Create default settings
            self.cursor.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
            self.conn.commit()
            
            messagebox.showinfo("Success", "Account created successfully!")
            self.show_login_screen()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists!")
    
    def login(self):
        """Authenticate user"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password!")
            return
        
        self.cursor.execute("SELECT id, full_name FROM users WHERE username=? AND password=?",
                          (username, password))
        result = self.cursor.fetchone()
        
        if result:
            self.current_user = {"id": result[0], "name": result[1], "username": username}
            self.show_main_screen()
        else:
            messagebox.showerror("Error", "Invalid username or password!")
    
    def show_main_screen(self):
        """Display main dashboard"""
        self.clear_window()
        
        # Top bar
        top_bar = tk.Frame(self.root, bg="#34495e", height=60)
        top_bar.pack(fill=tk.X)
        
        tk.Label(top_bar, text=f"Welcome, {self.current_user['name']}!", 
                font=("Arial", 16, "bold"), bg="#34495e", fg="white").pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Button(top_bar, text="Logout", command=self.logout,
                 bg="#e74c3c", fg="white", font=("Arial", 10),
                 cursor="hand2").pack(side=tk.RIGHT, padx=20)
        
        # Sidebar
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        menu_items = [
            ("Dashboard", self.show_dashboard),
            ("Add Reminder", self.show_add_reminder),
            ("View Reminders", self.show_reminders),
            ("Task Log", self.show_task_log),
            ("Settings", self.show_settings)
        ]
        
        for text, command in menu_items:
            btn = tk.Button(sidebar, text=text, command=command,
                          bg="#34495e", fg="white", font=("Arial", 12),
                          bd=0, activebackground="#1abc9c", 
                          activeforeground="white", cursor="hand2",
                          width=20, height=2)
            btn.pack(pady=5, padx=10)
        
        # Main content area
        self.content_frame = tk.Frame(self.root, bg="#ecf0f1")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Show dashboard by default
        self.show_dashboard()
    
    def show_dashboard(self):
        """Display dashboard with statistics"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Dashboard", 
                font=("Arial", 24, "bold"), bg="#ecf0f1").pack(pady=20)
        
        # Statistics
        stats_frame = tk.Frame(self.content_frame, bg="#ecf0f1")
        stats_frame.pack(pady=20)
        
        # Get statistics
        self.cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id=? AND status='pending'",
                          (self.current_user['id'],))
        pending = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id=? AND status='completed'",
                          (self.current_user['id'],))
        completed = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id=? AND reminder_date=?",
                          (self.current_user['id'], datetime.now().strftime('%Y-%m-%d')))
        today = self.cursor.fetchone()[0]
        
        # Stat cards
        stats = [
            ("Pending Tasks", pending, "#e74c3c"),
            ("Completed Tasks", completed, "#2ecc71"),
            ("Today's Reminders", today, "#3498db")
        ]
        
        for i, (label, value, color) in enumerate(stats):
            card = tk.Frame(stats_frame, bg=color, width=200, height=120, relief=tk.RAISED, bd=2)
            card.grid(row=0, column=i, padx=20, pady=10)
            card.pack_propagate(False)
            
            tk.Label(card, text=str(value), font=("Arial", 36, "bold"), 
                    bg=color, fg="white").pack(pady=10)
            tk.Label(card, text=label, font=("Arial", 12), 
                    bg=color, fg="white").pack()
        
        # Upcoming reminders
        upcoming_frame = tk.LabelFrame(self.content_frame, text="Upcoming Reminders", 
                                      font=("Arial", 14, "bold"), bg="#ecf0f1", padx=20, pady=10)
        upcoming_frame.pack(pady=20, padx=40, fill=tk.BOTH, expand=True)
        
        self.cursor.execute("""
            SELECT title, reminder_date, reminder_time, category 
            FROM reminders 
            WHERE user_id=? AND status='pending' AND datetime(reminder_date || ' ' || reminder_time) >= datetime('now')
            ORDER BY reminder_date, reminder_time 
            LIMIT 5
        """, (self.current_user['id'],))
        
        upcoming = self.cursor.fetchall()
        
        if upcoming:
            for reminder in upcoming:
                reminder_frame = tk.Frame(upcoming_frame, bg="white", relief=tk.RAISED, bd=1)
                reminder_frame.pack(fill=tk.X, pady=5)
                
                tk.Label(reminder_frame, text=reminder[0], font=("Arial", 12, "bold"),
                        bg="white", anchor="w").pack(side=tk.LEFT, padx=10, pady=5)
                
                tk.Label(reminder_frame, text=f"{reminder[1]} at {reminder[2]}", 
                        font=("Arial", 10), bg="white", fg="#7f8c8d").pack(side=tk.RIGHT, padx=10)
        else:
            tk.Label(upcoming_frame, text="No upcoming reminders", 
                    font=("Arial", 12), bg="#ecf0f1", fg="#7f8c8d").pack(pady=20)
    
    def show_add_reminder(self):
        """Display add reminder form"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Add New Reminder", 
                font=("Arial", 24, "bold"), bg="#ecf0f1").pack(pady=20)
        
        form_frame = tk.Frame(self.content_frame, bg="white", relief=tk.RAISED, bd=2)
        form_frame.pack(pady=20, padx=100)
        
        # Title
        tk.Label(form_frame, text="Title:", font=("Arial", 12), bg="white").grid(row=0, column=0, sticky="w", padx=20, pady=10)
        title_entry = tk.Entry(form_frame, font=("Arial", 12), width=40)
        title_entry.grid(row=0, column=1, padx=20, pady=10)
        
        # Description
        tk.Label(form_frame, text="Description:", font=("Arial", 12), bg="white").grid(row=1, column=0, sticky="nw", padx=20, pady=10)
        desc_text = tk.Text(form_frame, font=("Arial", 12), width=40, height=4)
        desc_text.grid(row=1, column=1, padx=20, pady=10)
        
        # Date
        tk.Label(form_frame, text="Date (YYYY-MM-DD):", font=("Arial", 12), bg="white").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        date_entry = tk.Entry(form_frame, font=("Arial", 12), width=40)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_entry.grid(row=2, column=1, padx=20, pady=10)
        
        # Time
        tk.Label(form_frame, text="Time (HH:MM):", font=("Arial", 12), bg="white").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        time_entry = tk.Entry(form_frame, font=("Arial", 12), width=40)
        time_entry.insert(0, "09:00")
        time_entry.grid(row=3, column=1, padx=20, pady=10)
        
        # Category
        tk.Label(form_frame, text="Category:", font=("Arial", 12), bg="white").grid(row=4, column=0, sticky="w", padx=20, pady=10)
        category_var = tk.StringVar(value="Class")
        categories = ["Class", "Meeting", "Deadline", "Event", "Personal", "Other"]
        category_menu = ttk.Combobox(form_frame, textvariable=category_var, values=categories, 
                                     font=("Arial", 12), width=37, state="readonly")
        category_menu.grid(row=4, column=1, padx=20, pady=10)
        
        # Repeat
        tk.Label(form_frame, text="Repeat:", font=("Arial", 12), bg="white").grid(row=5, column=0, sticky="w", padx=20, pady=10)
        repeat_var = tk.StringVar(value="once")
        repeats = ["once", "daily", "weekly", "monthly"]
        repeat_menu = ttk.Combobox(form_frame, textvariable=repeat_var, values=repeats,
                                   font=("Arial", 12), width=37, state="readonly")
        repeat_menu.grid(row=5, column=1, padx=20, pady=10)
        
        # Save button
        def save_reminder():
            title = title_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            date = date_entry.get().strip()
            time_val = time_entry.get().strip()
            category = category_var.get()
            repeat = repeat_var.get()
            
            if not title or not date or not time_val:
                messagebox.showerror("Error", "Title, date, and time are required!")
                return
            
            try:
                # Validate date and time
                datetime.strptime(date, '%Y-%m-%d')
                datetime.strptime(time_val, '%H:%M')
                
                self.cursor.execute("""
                    INSERT INTO reminders (user_id, title, description, reminder_date, 
                                         reminder_time, category, repeat_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (self.current_user['id'], title, description, date, time_val, category, repeat))
                self.conn.commit()
                
                messagebox.showinfo("Success", "Reminder added successfully!")
                self.show_reminders()
            except ValueError:
                messagebox.showerror("Error", "Invalid date or time format!")
        
        tk.Button(form_frame, text="Save Reminder", command=save_reminder,
                 bg="#2ecc71", fg="white", font=("Arial", 14, "bold"),
                 cursor="hand2", width=20).grid(row=6, column=0, columnspan=2, pady=20)
    
    def show_reminders(self):
        """Display all reminders"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="All Reminders", 
                font=("Arial", 24, "bold"), bg="#ecf0f1").pack(pady=20)
        
        # Filter frame
        filter_frame = tk.Frame(self.content_frame, bg="#ecf0f1")
        filter_frame.pack(pady=10)
        
        tk.Label(filter_frame, text="Filter:", font=("Arial", 12), bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        
        filter_var = tk.StringVar(value="all")
        filters = [("All", "all"), ("Pending", "pending"), ("Completed", "completed")]
        
        for text, value in filters:
            tk.Radiobutton(filter_frame, text=text, variable=filter_var, value=value,
                          bg="#ecf0f1", font=("Arial", 10), 
                          command=lambda: self.update_reminders_list(tree, filter_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Treeview frame
        tree_frame = tk.Frame(self.content_frame, bg="white")
        tree_frame.pack(pady=10, padx=40, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        columns = ("ID", "Title", "Date", "Time", "Category", "Status")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                           yscrollcommand=scrollbar.set, height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)
        
        # Load reminders
        self.update_reminders_list(tree, "all")
        
        # Action buttons
        btn_frame = tk.Frame(self.content_frame, bg="#ecf0f1")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Mark Complete", 
                 command=lambda: self.mark_complete(tree),
                 bg="#2ecc71", fg="white", font=("Arial", 11), 
                 cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Delete", 
                 command=lambda: self.delete_reminder(tree),
                 bg="#e74c3c", fg="white", font=("Arial", 11),
                 cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def update_reminders_list(self, tree, filter_status):
        """Update reminders list based on filter"""
        for item in tree.get_children():
            tree.delete(item)
        
        if filter_status == "all":
            self.cursor.execute("""
                SELECT id, title, reminder_date, reminder_time, category, status 
                FROM reminders WHERE user_id=? 
                ORDER BY reminder_date DESC, reminder_time DESC
            """, (self.current_user['id'],))
        else:
            self.cursor.execute("""
                SELECT id, title, reminder_date, reminder_time, category, status 
                FROM reminders WHERE user_id=? AND status=? 
                ORDER BY reminder_date DESC, reminder_time DESC
            """, (self.current_user['id'], filter_status))
        
        reminders = self.cursor.fetchall()
        
        for reminder in reminders:
            tree.insert("", tk.END, values=reminder)
    
    def mark_complete(self, tree):
        """Mark selected reminder as complete"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a reminder!")
            return
        
        item = tree.item(selected[0])
        reminder_id = item['values'][0]
        
        self.cursor.execute("UPDATE reminders SET status='completed' WHERE id=?", (reminder_id,))
        self.conn.commit()
        
        messagebox.showinfo("Success", "Reminder marked as complete!")
        self.update_reminders_list(tree, "all")
    
    def delete_reminder(self, tree):
        """Delete selected reminder"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a reminder!")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this reminder?"):
            item = tree.item(selected[0])
            reminder_id = item['values'][0]
            
            self.cursor.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
            self.conn.commit()
            
            messagebox.showinfo("Success", "Reminder deleted!")
            self.update_reminders_list(tree, "all")
    
    def show_task_log(self):
        """Display task log"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Task Log", 
                font=("Arial", 24, "bold"), bg="#ecf0f1").pack(pady=20)
        
        # Log frame
        log_frame = tk.Frame(self.content_frame, bg="white", relief=tk.RAISED, bd=2)
        log_frame.pack(pady=20, padx=40, fill=tk.BOTH, expand=True)
        
        # Text widget for log
        log_text = tk.Text(log_frame, font=("Courier", 10), wrap=tk.WORD, 
                          bg="#2c3e50", fg="#ecf0f1", padx=10, pady=10)
        log_text.pack(fill=tk.BOTH, expand=True)
        
        # Generate log
        self.cursor.execute("""
            SELECT title, reminder_date, reminder_time, status, created_at 
            FROM reminders WHERE user_id=? 
            ORDER BY created_at DESC LIMIT 50
        """, (self.current_user['id'],))
        
        reminders = self.cursor.fetchall()
        
        log_text.insert(tk.END, "=" * 80 + "\n")
        log_text.insert(tk.END, f"TASK LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_text.insert(tk.END, "=" * 80 + "\n\n")
        
        for reminder in reminders:
            log_text.insert(tk.END, f"[{reminder[4]}]\n")
            log_text.insert(tk.END, f"Title: {reminder[0]}\n")
            log_text.insert(tk.END, f"Scheduled: {reminder[1]} at {reminder[2]}\n")
            log_text.insert(tk.END, f"Status: {reminder[3].upper()}\n")
            log_text.insert(tk.END, "-" * 80 + "\n\n")
        
        log_text.config(state=tk.DISABLED)
    
    def show_settings(self):
        """Display settings"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Settings", 
                font=("Arial", 24, "bold"), bg="#ecf0f1").pack(pady=20)
        
        settings_frame = tk.Frame(self.content_frame, bg="white", relief=tk.RAISED, bd=2)
        settings_frame.pack(pady=20, padx=100)
        
        # Get current settings
        self.cursor.execute("SELECT * FROM settings WHERE user_id=?", (self.current_user['id'],))
        settings = self.cursor.fetchone()
        
        if not settings:
            self.cursor.execute("INSERT INTO settings (user_id) VALUES (?)", (self.current_user['id'],))
            self.conn.commit()
            settings = (self.current_user['id'], 'light', 1, 0)
        
        # Theme
        tk.Label(settings_frame, text="Theme:", font=("Arial", 12), bg="white").grid(row=0, column=0, sticky="w", padx=20, pady=10)
        theme_var = tk.StringVar(value=settings[1])
        theme_menu = ttk.Combobox(settings_frame, textvariable=theme_var, 
                                 values=["light", "dark"], font=("Arial", 12), 
                                 width=30, state="readonly")
        theme_menu.grid(row=0, column=1, padx=20, pady=10)
        
        # Notification sound
        tk.Label(settings_frame, text="Notification Sound:", font=("Arial", 12), bg="white").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        sound_var = tk.IntVar(value=settings[2])
        tk.Checkbutton(settings_frame, variable=sound_var, bg="white").grid(row=1, column=1, sticky="w", padx=20, pady=10)
        
        # Save button
        def save_settings():
            self.cursor.execute("""
                UPDATE settings 
                SET theme=?, notification_sound=? 
                WHERE user_id=?
            """, (theme_var.get(), sound_var.get(), self.current_user['id']))
            self.conn.commit()
            messagebox.showinfo("Success", "Settings saved!")
        
        tk.Button(settings_frame, text="Save Settings", command=save_settings,
                 bg="#3498db", fg="white", font=("Arial", 12, "bold"),
                 cursor="hand2", width=20).grid(row=2, column=0, columnspan=2, pady=20)
    
    def play_notification_sound(self, is_advance_warning=False):
        """Play notification sound based on platform"""
        # Check if sound is enabled in settings
        self.cursor.execute("SELECT notification_sound FROM settings WHERE user_id=?", 
                          (self.current_user['id'],))
        result = self.cursor.fetchone()
        
        if result and result[0] == 1:
            try:
                system = platform.system()
                if system == "Windows":
                    if is_advance_warning:
                        # Softer sound for 10-minute warning (2 beeps)
                        for _ in range(2):
                            winsound.Beep(600, 400)  # 600Hz for 400ms
                            time.sleep(0.2)
                    else:
                        # Louder, longer sound for actual reminder (5 beeps)
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        for _ in range(5):
                            winsound.Beep(1000, 500)  # 1000Hz for 500ms - LOUDER & LONGER
                            time.sleep(0.15)
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                elif system == "Darwin":  # macOS
                    import os
                    if is_advance_warning:
                        os.system('afplay /System/Library/Sounds/Tink.aiff')
                    else:
                        # Play sound multiple times for emphasis
                        for _ in range(3):
                            os.system('afplay /System/Library/Sounds/Glass.aiff')
                elif system == "Linux":
                    import os
                    sound_file = '/usr/share/sounds/freedesktop/stereo/message.oga'
                    if is_advance_warning:
                        os.system(f'paplay {sound_file}')
                    else:
                        for _ in range(3):
                            os.system(f'paplay {sound_file}')
            except Exception as e:
                print(f"Sound error: {e}")
    
    def check_reminders(self):
        """Background thread to check and send notifications"""
        while self.running:
            try:
                if self.current_user:
                    now = datetime.now()
                    current_time = now.strftime('%Y-%m-%d %H:%M')
                    advance_time = (now + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M')
                    
                    # Check for 10-minute advance warnings
                    self.cursor.execute("""
                        SELECT id, title, description 
                        FROM reminders 
                        WHERE user_id=? AND status='pending' 
                        AND datetime(reminder_date || ' ' || reminder_time) <= datetime(?)
                        AND datetime(reminder_date || ' ' || reminder_time) > datetime(?)
                        AND advance_notified=0
                    """, (self.current_user['id'], advance_time, current_time))
                    
                    advance_reminders = self.cursor.fetchall()
                    
                    for reminder in advance_reminders:
                        try:
                            # Play advance warning sound
                            self.play_notification_sound(is_advance_warning=True)
                            
                            # Show advance notification
                            notification.notify(
                                title=f"🔔 Upcoming: {reminder[1]}",
                                message=f"In 10 minutes: {reminder[2] if reminder[2] else 'Reminder scheduled'}",
                                app_name="Teacher Reminder System",
                                timeout=10
                            )
                            
                            # Mark as advance notified
                            self.cursor.execute("UPDATE reminders SET advance_notified=1 WHERE id=?", (reminder[0],))
                            self.conn.commit()
                        except Exception as e:
                            print(f"Advance notification error: {e}")
                    
                    # Check for actual reminders
                    self.cursor.execute("""
                        SELECT id, title, description 
                        FROM reminders 
                        WHERE user_id=? AND status='pending' 
                        AND datetime(reminder_date || ' ' || reminder_time) <= datetime(?)
                        AND notified=0
                    """, (self.current_user['id'], current_time))
                    
                    reminders = self.cursor.fetchall()
                    
                    for reminder in reminders:
                        try:
                            # Play loud sound for actual reminder
                            self.play_notification_sound(is_advance_warning=False)
                            
                            # Then show notification
                            notification.notify(
                                title=f"⏰ REMINDER: {reminder[1]}",
                                message=reminder[2] if reminder[2] else "You have a pending task NOW!",
                                app_name="Teacher Reminder System",
                                timeout=15
                            )
                            
                            # Mark as notified
                            self.cursor.execute("UPDATE reminders SET notified=1 WHERE id=?", (reminder[0],))
                            self.conn.commit()
                        except Exception as e:
                            print(f"Notification error: {e}")
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Reminder check error: {e}")
                time.sleep(60)
    
    def clear_window(self):
        """Clear all widgets from root window"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def logout(self):
        """Logout current user"""
        self.current_user = None
        self.show_login_screen()
    
    def __del__(self):
        """Cleanup on exit"""
        self.running = False
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = TeacherReminderSystem(root)
    root.mainloop()