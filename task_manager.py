import json
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta

# ==========================================
# 1. DATA MODEL
# ==========================================
class Task:
    def __init__(self, title, description="", priority="Medium", intention="General"):
        self.title = title
        self.description = description
        self.priority = priority
        self.intention = intention
        self.completed = False
        self.artifacts = []
        self.deadline = None      # NEW: Stores deadline as a string "YYYY-MM-DD HH:MM"
        self.progress = 0         # NEW: Stores progress as an integer 0-100

# ==========================================
# 2. HELPER: TIME REMAINING CALCULATOR
# ==========================================
def get_time_remaining(deadline_str):
    """Returns (text, color_tag) based on how much time is left."""
    if not deadline_str:
        return "No Deadline", "gray"
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        now = datetime.now()
        diff = deadline - now

        if diff.total_seconds() <= 0:
            return "⏰ OVERDUE!", "red"
        elif diff <= timedelta(hours=24):
            hours = int(diff.total_seconds() // 3600)
            mins = int((diff.total_seconds() % 3600) // 60)
            return f"🔴 {hours}h {mins}m left", "red"
        elif diff <= timedelta(days=3):
            days = diff.days
            hours = int((diff.total_seconds() % 86400) // 3600)
            return f"🟡 {days}d {hours}h left", "yellow"
        else:
            days = diff.days
            return f"🟢 {days} days left", "green"
    except ValueError:
        return "Invalid Date", "gray"

# ==========================================
# 3. GUI APPLICATION CLASS
# ==========================================
class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Developer Task Manager")
        self.root.geometry("1050x600")
        
        self.tasks = []
        self.item_to_task = {}
        
        self.load_tasks()
        self.build_ui()
        self.refresh_list()

        # Auto-refresh every 60 seconds to keep deadlines updated!
        self.auto_refresh()

    def auto_refresh(self):
        self.refresh_list(self.search_var.get())
        self.root.after(60000, self.auto_refresh) # Refresh every 60 seconds

    # --- DATA MANAGEMENT ---
    def load_tasks(self):
        try:
            with open("tasks.json", "r") as file:
                loaded_data = json.load(file)
                if isinstance(loaded_data, list):
                    for data in loaded_data:
                        task = Task(data["title"], data.get("description", ""), 
                                    data.get("priority", "Medium"), data.get("intention", "General"))
                        task.completed = data.get("completed", False)
                        task.artifacts = data.get("artifacts", [])
                        task.deadline = data.get("deadline", None)    # Load deadline
                        task.progress = data.get("progress", 0)      # Load progress
                        self.tasks.append(task)
        except (FileNotFoundError, json.JSONDecodeError):
            pass 

    def save_tasks(self):
        tasks_to_save = []
        for task in self.tasks:
            tasks_to_save.append({
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "intention": task.intention,
                "completed": task.completed,
                "artifacts": task.artifacts,
                "deadline": task.deadline,      # Save deadline
                "progress": task.progress       # Save progress
            })
        try:
            with open("tasks.json", "w") as file:
                json.dump(tasks_to_save, file, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save tasks: {e}")

    # --- USER INTERFACE SETUP ---
    def build_ui(self):
        # --- Top Search Bar ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        tk.Label(top_frame, text="🔍 Search:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=10)

        # --- Left: Treeview ---
        list_frame = tk.Frame(self.root)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Status", "Priority", "Deadline", "Progress", "Artifacts")
        self.tree = ttk.Treeview(list_frame, columns=columns, selectmode="browse")
        self.tree.heading("#0", text="Intention / Task Title", anchor=tk.W)
        self.tree.heading("Status", text="Status")
        self.tree.heading("Priority", text="Priority")
        self.tree.heading("Deadline", text="Deadline")
        self.tree.heading("Progress", text="Progress")
        self.tree.heading("Artifacts", text="Artifacts")
        
        self.tree.column("#0", width=250)
        self.tree.column("Status", width=80)
        self.tree.column("Priority", width=70)
        self.tree.column("Deadline", width=130)
        self.tree.column("Progress", width=100)
        self.tree.column("Artifacts", width=70)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Color tags for deadline urgency
        self.tree.tag_configure("red", foreground="red")
        self.tree.tag_configure("yellow", foreground="#b8860b") # dark yellow for readability
        self.tree.tag_configure("green", foreground="green")
        self.tree.tag_configure("gray", foreground="gray")
        self.tree.tag_configure("done", foreground="gray")

        # --- Right: Buttons ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=5)

        tk.Button(btn_frame, text="➕ Add Task", width=18, command=self.open_task_form, bg="#d4edda").pack(pady=5)
        tk.Button(btn_frame, text="✏️ Edit Task", width=18, command=self.edit_selected_task).pack(pady=5)
        tk.Button(btn_frame, text="✅ Toggle Complete", width=18, command=self.toggle_complete).pack(pady=5)
        tk.Button(btn_frame, text="📊 Set Progress", width=18, command=self.set_progress).pack(pady=5)
        tk.Button(btn_frame, text="📎 Manage Artifacts", width=18, command=self.manage_artifacts).pack(pady=5)
        tk.Button(btn_frame, text="🗑️ Delete Task", width=18, command=self.delete_task, bg="#f8d7da").pack(pady=20)

    # --- SEARCH ---
    def on_search(self, *args):
        query = self.search_var.get().lower()
        self.refresh_list(search_query=query)

    # --- REFRESH LIST ---
    def refresh_list(self, search_query=""):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_to_task.clear()

        grouped = {}
        for task in self.tasks:
            if search_query:
                if (search_query not in task.title.lower() and 
                    search_query not in task.description.lower() and 
                    search_query not in task.intention.lower()):
                    continue

            if task.intention not in grouped:
                grouped[task.intention] = []
            grouped[task.intention].append(task)

        for intention, t_list in grouped.items():
            parent_id = self.tree.insert("", tk.END, text=f"🎯 {intention.upper()}", open=True)
            
            for task in t_list:
                # Status
                status = "✅ Done" if task.completed else "⏳ Pending"
                
                # Deadline with color
                deadline_text, color_tag = get_time_remaining(task.deadline)
                
                # Progress bar text
                progress_bar = self.make_progress_bar(task.progress)
                
                # Artifacts
                arts = f"📎 {len(task.artifacts)}" if task.artifacts else ""
                
                # Use 'done' tag if completed, otherwise use deadline color
                tag = "done" if task.completed else color_tag
                
                item_id = self.tree.insert(
                    parent_id, tk.END, text=task.title, 
                    values=(status, task.priority, deadline_text, progress_bar, arts),
                    tags=(tag,)
                )
                self.item_to_task[item_id] = task

    def make_progress_bar(self, progress):
        """Creates a text-based progress bar like [████░░░░░░] 40%"""
        filled = int(progress / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {progress}%"

    # --- ACTIONS ---
    def get_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a task first!")
            return None
        item_id = selected[0]
        if item_id not in self.item_to_task:
            messagebox.showinfo("Info", "Please select a specific task, not an Intention header.")
            return None
        return self.item_to_task[item_id]

    def delete_task(self):
        task = self.get_selected_task()
        if task and messagebox.askyesno("Confirm", f"Delete '{task.title}'?"):
            self.tasks.remove(task)
            self.save_tasks()
            self.refresh_list(self.search_var.get())

    def toggle_complete(self):
        task = self.get_selected_task()
        if task:
            task.completed = not task.completed
            if task.completed:
                task.progress = 100  # Auto-set progress to 100% when completed
            self.save_tasks()
            self.refresh_list(self.search_var.get())

    # --- NEW: SET PROGRESS ---
    def set_progress(self):
        task = self.get_selected_task()
        if not task: return

        win = tk.Toplevel(self.root)
        win.title(f"Progress: {task.title}")
        win.geometry("350x200")

        tk.Label(win, text=f"Task: {task.title}", font=("Arial", 11, "bold")).pack(pady=(15,5))
        
        tk.Label(win, text="Set Completion Percentage:").pack(pady=5)

        # Progress slider
        progress_var = tk.IntVar(value=task.progress)
        
        # Display current value
        val_label = tk.Label(win, text=f"{task.progress}%", font=("Arial", 18, "bold"))
        val_label.pack()

        def update_label(val):
            val_label.config(text=f"{int(float(val))}%")

        slider = tk.Scale(
            win, from_=0, to=100, orient=tk.HORIZONTAL, 
            variable=progress_var, length=250,
            command=update_label
        )
        slider.pack(pady=5)

        def save_progress():
            task.progress = progress_var.get()
            if task.progress == 100:
                task.completed = True
            elif task.progress < 100:
                task.completed = False
            self.save_tasks()
            self.refresh_list(self.search_var.get())
            win.destroy()

        tk.Button(win, text="Save Progress", command=save_progress, bg="#007bff", fg="white").pack(pady=10)

    # --- TASK FORM (ADD / EDIT) ---
    def open_task_form(self, task_to_edit=None):
        form = tk.Toplevel(self.root)
        form.title("Edit Task" if task_to_edit else "New Task")
        form.geometry("400x400")

        tk.Label(form, text="Title:").pack(pady=(10,0))
        title_entry = tk.Entry(form, width=40)
        title_entry.pack()

        tk.Label(form, text="Description:").pack(pady=(10,0))
        desc_entry = tk.Entry(form, width=40)
        desc_entry.pack()

        tk.Label(form, text="Intention (Goal):").pack(pady=(10,0))
        int_entry = tk.Entry(form, width=40)
        int_entry.pack()

        tk.Label(form, text="Priority:").pack(pady=(10,0))
        pri_combo = ttk.Combobox(form, values=["High", "Medium", "Low"], state="readonly")
        pri_combo.pack()

        # --- NEW: Deadline Fields ---
        tk.Label(form, text="Deadline (Date):").pack(pady=(10,0))
        date_frame = tk.Frame(form)
        date_frame.pack()

        # Year
        tk.Label(date_frame, text="Year:").pack(side=tk.LEFT)
        year_var = tk.StringVar()
        year_entry = tk.Entry(date_frame, textvariable=year_var, width=6)
        year_entry.pack(side=tk.LEFT, padx=2)

        # Month
        tk.Label(date_frame, text="Month:").pack(side=tk.LEFT)
        month_var = tk.StringVar()
        month_combo = ttk.Combobox(date_frame, textvariable=month_var, 
                                    values=[f"{i:02d}" for i in range(1,13)], width=4, state="readonly")
        month_combo.pack(side=tk.LEFT, padx=2)

        # Day
        tk.Label(date_frame, text="Day:").pack(side=tk.LEFT)
        day_var = tk.StringVar()
        day_combo = ttk.Combobox(date_frame, textvariable=day_var, 
                                  values=[f"{i:02d}" for i in range(1,32)], width=4, state="readonly")
        day_combo.pack(side=tk.LEFT, padx=2)

        tk.Label(form, text="Deadline (Time):").pack(pady=(10,0))
        time_frame = tk.Frame(form)
        time_frame.pack()

        # Hour
        tk.Label(time_frame, text="Hour:").pack(side=tk.LEFT)
        hour_var = tk.StringVar()
        hour_combo = ttk.Combobox(time_frame, textvariable=hour_var, 
                                   values=[f"{i:02d}" for i in range(0,24)], width=4, state="readonly")
        hour_combo.pack(side=tk.LEFT, padx=2)

        # Minute
        tk.Label(time_frame, text="Min:").pack(side=tk.LEFT)
        min_var = tk.StringVar()
        min_combo = ttk.Combobox(time_frame, textvariable=min_var, 
                                  values=[f"{i:02d}" for i in range(0,60,5)], width=4, state="readonly")
        min_combo.pack(side=tk.LEFT, padx=2)

        # Pre-fill values
        if task_to_edit:
            title_entry.insert(0, task_to_edit.title)
            desc_entry.insert(0, task_to_edit.description)
            int_entry.insert(0, task_to_edit.intention)
            pri_combo.set(task_to_edit.priority)
            
            if task_to_edit.deadline:
                try:
                    dt = datetime.strptime(task_to_edit.deadline, "%Y-%m-%d %H:%M")
                    year_var.set(str(dt.year))
                    month_combo.set(f"{dt.month:02d}")
                    day_combo.set(f"{dt.day:02d}")
                    hour_combo.set(f"{dt.hour:02d}")
                    min_combo.set(f"{dt.minute:02d}")
                except ValueError:
                    pass
        else:
            int_entry.insert(0, "General")
            pri_combo.set("Medium")
            year_var.set(str(datetime.now().year))

        def save_form():
            title = title_entry.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required!")
                return

            # Build deadline string
            deadline = None
            if year_var.get() and month_var.get() and day_var.get():
                hour = hour_combo.get() or "00"
                minute = min_combo.get() or "00"
                deadline_str = f"{year_var.get()}-{month_var.get()}-{day_var.get()} {hour}:{minute}"
                try:
                    datetime.strptime(deadline_str, "%Y-%m-%d %H:%M") # Validate
                    deadline = deadline_str
                except ValueError:
                    messagebox.showerror("Error", "Invalid date. Please check your deadline.")
                    return

            if task_to_edit:
                task_to_edit.title = title
                task_to_edit.description = desc_entry.get()
                task_to_edit.intention = int_entry.get() or "General"
                task_to_edit.priority = pri_combo.get()
                task_to_edit.deadline = deadline
            else:
                new_task = Task(title, desc_entry.get(), pri_combo.get(), int_entry.get() or "General")
                new_task.deadline = deadline
                self.tasks.append(new_task)

            self.save_tasks()
            self.refresh_list(self.search_var.get())
            form.destroy()

        tk.Button(form, text="Save Task", command=save_form, bg="#007bff", fg="white").pack(pady=15)

    def edit_selected_task(self):
        task = self.get_selected_task()
        if task:
            self.open_task_form(task)

    # --- ARTIFACTS WINDOW ---
    def manage_artifacts(self):
        task = self.get_selected_task()
        if not task: return

        win = tk.Toplevel(self.root)
        win.title(f"Artifacts: {task.title}")
        win.geometry("550x300")

        listbox = tk.Listbox(win, width=80)
        listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        def refresh_arts():
            listbox.delete(0, tk.END)
            for art in task.artifacts:
                exists = "✅" if os.path.exists(art['path']) else "❌"
                listbox.insert(tk.END, f"{exists} [{art['type']}] {art['path']}")

        refresh_arts()

        def add_art():
            filepath = filedialog.askopenfilename(title="Select File to Link")
            if filepath:
                task.artifacts.append({
                    "type": "Linked File",
                    "path": filepath,
                    "description": ""
                })
                self.save_tasks()
                refresh_arts()
                self.refresh_list(self.search_var.get())

        def remove_art():
            selection = listbox.curselection()
            if selection:
                task.artifacts.pop(selection[0])
                self.save_tasks()
                refresh_arts()
                self.refresh_list(self.search_var.get())

        def open_art():
            selection = listbox.curselection()
            if selection:
                filepath = task.artifacts[selection[0]]['path']
                if os.path.exists(filepath):
                    try:
                        if sys.platform == "win32":
                            os.startfile(filepath)
                        elif sys.platform == "darwin":
                            subprocess.call(('open', filepath))
                        else:
                            subprocess.call(('xdg-open', filepath))
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not open file: {e}")
                else:
                    messagebox.showwarning("Not Found", "File no longer exists at this path.")

        btn_f = tk.Frame(win)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="➕ Browse File", command=add_art).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_f, text="🚀 Open File", command=open_art, bg="#cce5ff").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_f, text="🗑️ Remove Selected", command=remove_art).pack(side=tk.LEFT, padx=5)

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()