import sqlite3
from datetime import datetime
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# --- Database Setup ---
conn = sqlite3.connect('study_planner.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    planned_duration INTEGER,
    start_time TEXT,
    end_time TEXT,
    actual_duration INTEGER,
    status TEXT
)
''')
conn.commit()

# --- Task Functions ---
def add_task():
    name = task_name_entry.get()
    duration = planned_duration_entry.get()
    if not name or not duration:
        messagebox.showerror("Error", "Please enter task name and duration")
        return
    try:
        duration = int(duration)
    except ValueError:
        messagebox.showerror("Error", "Duration must be a number")
        return
    cursor.execute("INSERT INTO tasks (name, planned_duration, status) VALUES (?, ?, ?)",
                   (name, duration, 'Pending'))
    conn.commit()
    task_name_entry.delete(0, tk.END)
    planned_duration_entry.delete(0, tk.END)
    refresh_tasks()
    messagebox.showinfo("Success", f"Task '{name}' added successfully!")

def start_task():
    selected = tasks_tree.focus()
    if not selected:
        messagebox.showwarning("Warning", "Select a task to start")
        return
    task_id = int(selected)
    cursor.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
    status = cursor.fetchone()[0]
    if status == "Completed":
        messagebox.showinfo("Info", "Task already completed")
        return
    
    start_time = datetime.now()
    cursor.execute("UPDATE tasks SET start_time=?, status=? WHERE id=?",
                   (start_time, 'In Progress', task_id))
    conn.commit()
    refresh_tasks()
    messagebox.showinfo("Task Started", f"Task {task_id} started!")

    # --- Monitor and Timer Thread ---
    cursor.execute("SELECT planned_duration FROM tasks WHERE id=?", (task_id,))
    planned_duration = cursor.fetchone()[0]

    def monitor_task(planned_minutes):
        start_dt = datetime.now()
        while True:
            threading.Event().wait(1)  # every second
            cursor.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
            status_db = cursor.fetchone()[0]
            if status_db != 'In Progress':
                break

            elapsed_seconds = int((datetime.now() - start_dt).total_seconds())
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60

            timer_label.config(text=f"⏱️ Task {task_id} Running: {minutes:02d}:{seconds:02d}")
            root.update_idletasks()

            if elapsed_seconds >= planned_minutes * 60:
                messagebox.showwarning("Reminder", f"⏰ Planned time for Task {task_id} is over!")
                break

    threading.Thread(target=monitor_task, args=(planned_duration,), daemon=True).start()

def end_task():
    selected = tasks_tree.focus()
    if not selected:
        messagebox.showwarning("Warning", "Select a task to end")
        return
    task_id = int(selected)
    cursor.execute("SELECT start_time, status FROM tasks WHERE id=?", (task_id,))
    result = cursor.fetchone()
    if not result:
        return
    start_time_str, status = result
    if status != "In Progress":
        messagebox.showinfo("Info", "Task not in progress")
        return
    
    end_time = datetime.now()
    start_time = datetime.fromisoformat(start_time_str)
    actual_duration = int((end_time - start_time).total_seconds() // 60)
    
    cursor.execute("UPDATE tasks SET end_time=?, actual_duration=?, status=? WHERE id=?",
                   (end_time, actual_duration, 'Completed', task_id))
    conn.commit()
    refresh_tasks()
    timer_label.config(text="✅ Task completed.")
    messagebox.showinfo("Task Completed", f"Task {task_id} completed! Actual duration: {actual_duration} mins")

def refresh_tasks():
    for row in tasks_tree.get_children():
        tasks_tree.delete(row)
    cursor.execute("SELECT id, name, planned_duration, start_time, end_time, actual_duration, status FROM tasks")
    for task in cursor.fetchall():
        tasks_tree.insert('', tk.END, iid=task[0], values=task)

def daily_summary():
    today = datetime.now().date()
    cursor.execute("SELECT name, planned_duration, actual_duration, status FROM tasks WHERE start_time LIKE ?", 
                   (f"{today}%",))
    tasks = cursor.fetchall()
    if not tasks:
        messagebox.showinfo("Daily Summary", "No tasks for today")
        return
    summary_text = ""
    total_planned = total_actual = 0
    for t in tasks:
        name, planned, actual, status = t
        actual = actual if actual else 0
        total_planned += planned
        total_actual += actual
        summary_text += f"Task: {name} | Planned: {planned} mins | Actual: {actual} mins | Status: {status}\n"
    summary_text += f"\nTotal Planned: {total_planned} mins | Total Actual: {total_actual} mins"
    messagebox.showinfo("Daily Summary", summary_text)

# --- GUI Setup ---
root = tk.Tk()
root.title("📚 Study Planner & Time Tracker")
root.geometry("950x550")
root.config(bg="#f0f4f8")

# --- Header ---
tk.Label(root, text="Study Planner & Time Tracker", font=("Arial", 18, "bold"), bg="#f0f4f8", fg="#2c3e50").pack(pady=10)

# --- Task Input ---
frame = tk.Frame(root, bg="#f0f4f8")
frame.pack()

tk.Label(frame, text="Task Name:", bg="#f0f4f8").grid(row=0, column=0, padx=5, pady=5)
task_name_entry = tk.Entry(frame, width=25)
task_name_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(frame, text="Planned Duration (mins):", bg="#f0f4f8").grid(row=0, column=2, padx=5, pady=5)
planned_duration_entry = tk.Entry(frame, width=10)
planned_duration_entry.grid(row=0, column=3, padx=5, pady=5)

tk.Button(frame, text="➕ Add Task", command=add_task, bg="#4CAF50", fg="white", width=15).grid(row=0, column=4, padx=10)
tk.Button(frame, text="▶️ Start Task", command=start_task, bg="#2196F3", fg="white", width=15).grid(row=1, column=0, padx=10)
tk.Button(frame, text="⏹️ End Task", command=end_task, bg="#f44336", fg="white", width=15).grid(row=1, column=1, padx=10)
tk.Button(frame, text="📅 Daily Summary", command=daily_summary, bg="#FF9800", fg="white", width=15).grid(row=1, column=2, padx=10)
tk.Button(frame, text="🔄 Refresh", command=refresh_tasks, bg="#9C27B0", fg="white", width=15).grid(row=1, column=3, padx=10)

# --- Live Timer Label ---
timer_label = tk.Label(root, text="⏱️ Timer not started", font=("Arial", 12, "bold"), bg="#f0f4f8", fg="#1e88e5")
timer_label.pack(pady=10)

# --- Task Table ---
columns = ("ID", "Name", "Planned Duration", "Start Time", "End Time", "Actual Duration", "Status")
tasks_tree = ttk.Treeview(root, columns=columns, show='headings', height=10)
for col in columns:
    tasks_tree.heading(col, text=col)
    tasks_tree.column(col, width=120)
tasks_tree.pack(pady=10)

refresh_tasks()
root.mainloop()
conn.close()
