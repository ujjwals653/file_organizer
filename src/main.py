import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

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

def get_category(extension):
    for category, extensions in FILE_CATEGORIES.items():
        if extension.lower() in extensions:
            return category
    return "Others"

def organize_folder(folder_path):
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1]
            category = get_category(ext)
            category_path = os.path.join(folder_path, category)
            os.makedirs(category_path, exist_ok=True)
            shutil.move(file_path, os.path.join(category_path, file))
    messagebox.showinfo("Success", "✅ Folder organized successfully!")

# --- GUI Setup ---
root = tk.Tk()
root.title("Local File Organizer")
root.geometry("400x200")
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
    organize_folder(folder)

# --- UI Elements ---
tk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

tk.Button(root, text="Select Folder", command=select_folder, width=15, bg="#3498db", fg="white").pack(pady=5)
tk.Label(root, textvariable=selected_folder, wraplength=350, fg="gray").pack(pady=5)
tk.Button(root, text="Organize Files", command=start_organizing, width=15, bg="#2ecc71", fg="white").pack(pady=10)

root.mainloop()
