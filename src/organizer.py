import os
import shutil
import mimetypes

# keep last moves for undo; external modules will use these functions
_last_moves = []
SENTINEL_FILENAME = "AUTO-ORGANIZER-WATCH - This folder is under watch of auto organizer (delete this to stop auto organization).txt"

def _resolve_duplicate(dest_path):
    """
    If dest_path exists, append ' (n)' before extension.
    """
    if not os.path.exists(dest_path):
        return dest_path
    base, ext = os.path.splitext(os.path.basename(dest_path))
    dirpath = os.path.dirname(dest_path)
    n = 1
    while True:
        candidate = f"{base} ({n}){ext}"
        full = os.path.join(dirpath, candidate)
        if not os.path.exists(full):
            return full
        n += 1


def _guess_ext_by_mime(file_path):
    """
    If a file lacks an extension, try to guess one from its mime type.
    Return the guessed extension (like '.txt') or ''.
    """
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        # map a few common mime types to extensions as a fallback
        if mime.startswith("text/"):
            return ".txt"
        if mime.startswith("image/"):
            # mimetypes may return none extension, so we try common ones
            return ".png"
        if mime.startswith("audio/"):
            return ".mp3"
        if mime.startswith("video/"):
            return ".mp4"
    return ""


def organize_folder(folder_path, categories_dict, selected_categories=None, log_func=print, progress_func=None, dry_run=False):
    """
    Organize files in folder_path using categories_dict (name -> [exts]).
    selected_categories: list/set of category names to include. If None, include all.
    log_func(message) used for app logs (gui or CLI).
    progress_func(processed, total) used to update progress UI; may be None.
    dry_run: if True, don't actually move files; only log planned moves.
    """
    global _last_moves
    _last_moves = []

    if selected_categories is None:
        selected_categories = set(categories_dict.keys())
    else:
        selected_categories = set(selected_categories)

    # Build a flat list of files in the root of folder_path (do not descend)
    # Skip files already inside any category folder.
    category_folder_names = set(name for name in categories_dict.keys())
    files = []
    for entry in os.listdir(folder_path):
        full = os.path.join(folder_path, entry)
        if os.path.isfile(full):
            if entry == SENTINEL_FILENAME:
                continue
            files.append(entry)

    # Filter and prepare list of candidate moves
    candidates = []
    for f in files:
        # skip files that are in category folders (they're at root so this check isn't needed,
        # but we also skip if filename matches a category folder name or hidden files)
        if f.startswith("."):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext == "":
            ext = _guess_ext_by_mime(os.path.join(folder_path, f))
        # find category for this extension
        category = None
        for cat, exts in categories_dict.items():
            if ext in map(str.lower, exts):
                category = cat
                break
        if not category:
            category = "Others" if "Others" in categories_dict else None

        if category and category in selected_categories:
            # ensure we don't try to move a file already in a folder with that name
            # (since we are operating at root, it's safe; this is a precaution)
            candidates.append((f, ext, category))

    total = len(candidates)
    if total == 0:
        log_func("No files to organize (based on selected categories).")
        if progress_func:
            progress_func(0, 0)
        return

    processed = 0
    for idx, (filename, ext, category) in enumerate(candidates, start=1):
        src = os.path.join(folder_path, filename)
        dest_folder = os.path.join(folder_path, category)
        os.makedirs(dest_folder, exist_ok=True)
        dest = os.path.join(dest_folder, filename)
        dest = _resolve_duplicate(dest)  # ensure no overwrite

        if dry_run:
            log_func(f"[DRY RUN] Would move: {filename} -> {category}/{os.path.basename(dest)}")
            # do not record moves in dry-run
        else:
            try:
                shutil.move(src, dest)
                _last_moves.append((dest, src))
                log_func(f"Moved: {filename} -> {category}/{os.path.basename(dest)}")
            except Exception as e:
                log_func(f"Error moving {filename}: {e}")

        processed = idx
        if progress_func:
            progress_func(processed, total)

    # done
    if dry_run:
        log_func("Dry-run complete. No files were moved.")
    else:
        log_func("Organization complete.")


def undo_last_organization(log_func=print):
    """
    Move files back in reverse order of moves recorded in _last_moves.
    """
    global _last_moves
    if not _last_moves:
        log_func("Nothing to undo.")
        return
    # reverse order
    for dest, original in reversed(_last_moves):
        if os.path.exists(dest):
            try:
                # ensure original dir exists
                orig_dir = os.path.dirname(original)
                os.makedirs(orig_dir, exist_ok=True)
                shutil.move(dest, original)
                log_func(f"Undo: {os.path.basename(dest)} -> {original}")
            except Exception as e:
                log_func(f"Error undoing {dest}: {e}")
        else:
            log_func(f"File not found for undo: {dest}")
    _last_moves = []
    log_func("Undo complete.")
