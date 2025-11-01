import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# File categories
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif"],
    "Documents": [".pdf", ".docx", ".txt", ".pptx", ".xls", ".xlsx"],
    "Audio": [".mp3", ".wav", ".flac"],
    "Video": [".mp4", ".mkv", ".mov"],
    "Code": [".py", ".js", ".cpp", ".java", ".html", ".css"],
    "Applications": [".exe", ".msi"],
    "Archives": [".zip", ".rar", ".tar", ".gz"],
    "Others": []
}

# Store moves for undo
last_moves = []

def get_category(extension):
    for category, extensions in FILE_CATEGORIES.items():
        if extension.lower() in extensions:
            return category
    return "Others"

def organize_folder(folder_path, progress_var, log_text):
    global last_moves
    last_moves = []  # Reset for new organization

    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    total_files = len(files)
    if total_files == 0:
        messagebox.showinfo("Info", "No files to organize in this folder.")
        return

    for idx, file in enumerate(files, start=1):
        file_path = os.path.join(folder_path, file)
        ext = os.path.splitext(file)[1]
        category = get_category(ext)
        category_path = os.path.join(folder_path, category)
        os.makedirs(category_path, exist_ok=True)
        new_path = os.path.join(category_path, file)

        shutil.move(file_path, new_path)
        last_moves.append((new_path, file_path))  # Log for undo

        log_text.insert(tk.END, f"Moved: {file} → {category}\n")
        log_text.see(tk.END)

        progress_var.set(int((idx / total_files) * 100))
        root.update_idletasks()

    messagebox.showinfo("Success", "✅ Folder organized successfully!")
    progress_var.set(0)

def undo_organization(log_text):
    global last_moves
    if not last_moves:
        messagebox.showinfo("Info", "Nothing to undo!")
        return

    for new_path, original_path in reversed(last_moves):
        if os.path.exists(new_path):
            shutil.move(new_path, original_path)
            log_text.insert(tk.END, f"Undo: {os.path.basename(new_path)} → original location\n")
            log_text.see(tk.END)

    last_moves = []
    messagebox.showinfo("Undo Complete", "✅ Last organization undone.")

# --- GUI Setup ---
root = tk.Tk()
root.title("Local File Organizer v1.2")
root.geometry("500x450")
root.resizable(False, False)

selected_folder = tk.StringVar(value="No folder selected")

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        selected_folder.set(folder)

def start_organizing():
    folder = selected_folder.get()
    if not os.path.exists(folder) or folder == "No folder selected":
        messagebox.showwarning("Warning", "Please select a valid folder first.")
        return
    organize_folder(folder, progress_var, log_text)

# --- UI Elements ---
tk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

tk.Button(root, text="Select Folder", command=select_folder, width=15, bg="#3498db", fg="white").pack(pady=5)
tk.Label(root, textvariable=selected_folder, wraplength=450, fg="gray").pack(pady=5)

tk.Button(root, text="Organize Files", command=start_organizing, width=15, bg="#2ecc71", fg="white").pack(pady=5)
tk.Button(root, text="Undo Last Organization", command=lambda: undo_organization(log_text), width=25, bg="#e74c3c", fg="white").pack(pady=5)

# Progress Bar
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress_bar.pack(pady=5)

# Log Textbox
log_frame = tk.Frame(root)
log_frame.pack(pady=10, fill="both", expand=True)
log_text = tk.Text(log_frame, height=10)
log_text.pack(side="left", fill="both", expand=True)
scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
scrollbar.pack(side="right", fill="y")
log_text.config(yscrollcommand=scrollbar.set)

root.mainloop()
