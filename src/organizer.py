import os
import shutil

last_moves = []

def organize_folder(folder_path, categories, selected_categories, log_func, progress_func):
    global last_moves
    last_moves = []

    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    total_files = len(files)
    if total_files == 0:
        log_func("No files to organize.")
        return

    for idx, file in enumerate(files, start=1):
        file_path = os.path.join(folder_path, file)
        ext = os.path.splitext(file)[1].lower()
        category = next((cat for cat, exts in categories.items() if ext in exts), "Others")
        if category not in selected_categories:
            continue
        category_path = os.path.join(folder_path, category)
        os.makedirs(category_path, exist_ok=True)
        new_path = os.path.join(category_path, file)
        shutil.move(file_path, new_path)
        last_moves.append((new_path, file_path))

        log_func(f"Moved: {file} → {category}")
        progress_func(idx, total_files)

def undo_last_organization(log_func):
    global last_moves
    if not last_moves:
        log_func("Nothing to undo.")
        return
    for new_path, original_path in reversed(last_moves):
        if os.path.exists(new_path):
            shutil.move(new_path, original_path)
            log_func(f"Undo: {os.path.basename(new_path)} → original location")
    last_moves = []
