import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from organizer import organize_folder, undo_last_organization
from categories import load_categories

def create_main_window():
    root = tk.Tk()
    root.title("Local File Organizer")
    root.geometry("500x450")
    root.resizable(False, False)

    selected_folder = tk.StringVar(value="No folder selected")
    categories = load_categories()
    category_vars = {}

    # --- Logging & Progress ---
    def log_func(message):
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)

    def progress_func(idx, total):
        progress_var.set(int((idx / total) * 100))
        root.update_idletasks()

    # --- Folder selection ---
    def select_folder():
        folder = filedialog.askdirectory()
        if folder:
            selected_folder.set(folder)

    def start_organizing():
        folder = selected_folder.get()
        if not os.path.exists(folder) or folder == "No folder selected":
            messagebox.showwarning("Warning", "Please select a valid folder first.")
            return
        selected_cats = [cat for cat, var in category_vars.items() if var.get()]
        organize_folder(folder, categories, selected_cats, log_func, progress_func)
        messagebox.showinfo("Success", "✅ Folder organized successfully!")
        progress_var.set(0)

    def undo_organizing():
        undo_last_organization(log_func)
        messagebox.showinfo("Undo Complete", "✅ Last organization undone.")

    # --- Category Management ---
    def refresh_categories():
        for widget in category_frame.winfo_children():
            widget.destroy()
        category_vars.clear()
        for cat in categories:
            var = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(category_frame, text=cat, variable=var)
            chk.pack(anchor="w")
            category_vars[cat] = var

    # --- GUI Elements ---
    tk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

    tk.Label(root, textvariable=selected_folder, wraplength=550, fg="gray").pack(pady=5)
    tk.Button(root, text="Select Folder", command=select_folder, width=20, bg="#3498db", fg="white").pack(pady=5)
    tk.Button(root, text="Organize Files", command=start_organizing, width=20, bg="#2ecc71", fg="white").pack(pady=5)
    tk.Button(root, text="Undo Last Organization", command=undo_organizing, width=25, bg="#e74c3c", fg="white").pack(pady=5)

    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate", variable=progress_var)
    progress_bar.pack(pady=5)

    log_frame = tk.Frame(root)
    log_frame.pack(pady=10, fill="both", expand=True)
    log_text = tk.Text(log_frame, height=10)
    log_text.pack(side="left", fill="both", expand=True)
    scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.pack(side="right", fill="y")
    log_text.config(yscrollcommand=scrollbar.set)

    root.mainloop()
