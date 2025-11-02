# file_watcher.py
import os
import time
import threading
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# optional: import CategoryManager and organizer to reuse logic
from categories import CategoryManager
import organizer  # used to append to organizer._last_moves for undo, if available

# Name of the sentinel file (exact filename placed into watched folder)
SENTINEL_FILENAME = "AUTO-ORGANIZER-WATCH - This folder is under watch of auto organizer (delete this to stop auto organization).txt"

# common partial/temp extensions produced by browsers/downloaders
PARTIAL_EXTENSIONS = {".crdownload", ".part", ".partial", ".tmp", ".download", ".!download"}

# interval between size checks in seconds
DEFAULT_STABLE_CHECK_INTERVAL = 1.0
# how many consecutive equal-size checks count as "stable"
DEFAULT_STABLE_CHECKS = 3
# maximum wait (seconds) before giving up on stability
DEFAULT_STABILITY_TIMEOUT = 30.0


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


def _is_partial(filename):
    """
    Quick check for known partial download filename patterns.
    """
    name_lower = filename.lower()
    for ext in PARTIAL_EXTENSIONS:
        if name_lower.endswith(ext):
            return True
    # some downloaders append temporary suffixes like .part<random> or .tmp
    # We already cover common ones; further heuristics can be added if needed.
    return False


def _wait_for_stable_file(path, check_interval=DEFAULT_STABLE_CHECK_INTERVAL, stable_checks=DEFAULT_STABLE_CHECKS, timeout=DEFAULT_STABILITY_TIMEOUT, log_func=print):
    """
    Wait until the file size remains identical for `stable_checks` consecutive checks,
    checking every `check_interval` seconds, but give up after `timeout` seconds.
    Returns True if stable, False otherwise.
    """
    start = time.time()
    last_size = -1
    stable_count = 0

    while True:
        try:
            if not os.path.exists(path):
                log_func(f"[Watcher] File disappeared while waiting: {path}")
                return False
            size = os.path.getsize(path)
        except Exception as e:
            log_func(f"[Watcher] Error accessing file {path} while waiting for stability: {e}")
            return False

        # if size unchanged since last check
        if size == last_size:
            stable_count += 1
        else:
            stable_count = 0
            last_size = size

        if stable_count >= stable_checks:
            return True

        if (time.time() - start) > timeout:
            log_func(f"[Watcher] Timed out waiting for file stability: {path}")
            return False

        time.sleep(check_interval)


class _WatchHandler(FileSystemEventHandler):
    """
    Handles filesystem events for a single watched folder.
    """

    def __init__(self, folder_path, category_manager: CategoryManager, log_func=print,
                 stable_checks=DEFAULT_STABLE_CHECKS, check_interval=DEFAULT_STABLE_CHECK_INTERVAL, stability_timeout=DEFAULT_STABILITY_TIMEOUT):
        super().__init__()
        self.folder_path = os.path.abspath(folder_path)
        self.cm = category_manager # Use the passed-in CM
        self.log = log_func
        self._processing = set()  # set of canonical paths currently being handled
        self.stable_checks = stable_checks
        self.check_interval = check_interval
        self.stability_timeout = stability_timeout

        # set of folder names that are category targets (so we can ignore events inside them)
        self._category_folder_names = set(self.cm.get().keys())

    def _is_inside_category_folder(self, path):
        # check whether path is inside any of the category folders at root
        rel = os.path.relpath(path, self.folder_path)
        # if file is outside watched folder then don't process
        if rel.startswith(os.pardir):
            return True
        parts = rel.split(os.sep)
        if len(parts) >= 1 and parts[0] in self._category_folder_names:
            return True
        return False

    def _process_new_file(self, src_path):
        """
        Move a single file into its category folder (if any category matches).
        This is intentionally conservative and only touches the single file.
        """
        # normalize
        src_path = os.path.abspath(src_path)

        # ignore sentinel file itself
        if os.path.basename(src_path) == SENTINEL_FILENAME:
            return

        # ignore files outside the watched folder
        if not os.path.commonpath([self.folder_path, src_path]) == self.folder_path:
            return

        # ignore directories
        if not os.path.isfile(src_path):
            return

        # ignore files that are already inside category folders
        if self._is_inside_category_folder(src_path):
            return

        filename = os.path.basename(src_path)
        if _is_partial(filename):
            self.log(f"[Watcher] Ignoring partial/temp file (by extension): {filename}")
            return

        # avoid double-processing same file
        if src_path in self._processing:
            return

        # mark as processing
        self._processing.add(src_path)
        try:
            # wait until the file is stable (not changing in size)
            stable = _wait_for_stable_file(src_path, check_interval=self.check_interval,
                                           stable_checks=self.stable_checks, timeout=self.stability_timeout, log_func=self.log)
            if not stable:
                self.log(f"[Watcher] Skipping unstable file: {filename}")
                return

            # determine extension
            ext = os.path.splitext(filename)[1].lower()
            if not ext:
                # guess extension via mimetypes fallback (optional)
                import mimetypes
                guessed = mimetypes.guess_extension(mimetypes.guess_type(src_path)[0] or "")
                if guessed:
                    ext = guessed.lower()

            # find category
            category = self.cm.find_category_for_ext(ext)
            if not category:
                # fallback to "Others" if present
                if "Others" in self.cm.get():
                    category = "Others"
                else:
                    self.log(f"[Watcher] No category for extension '{ext}' (file: {filename}); skipping.")
                    return

            # prepare destination
            dest_dir = os.path.join(self.folder_path, category)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, filename)
            dest = _resolve_duplicate(dest)

            # move file
            try:
                shutil.move(src_path, dest)
                self.log(f"[Auto] {filename} → {category}")
                # record move in organizer._last_moves (if module available)
                try:
                    organizer._last_moves.append((dest, src_path))
                except Exception:
                    # ignore–undo will not be available if organizer not present
                    pass
            except Exception as e:
                self.log(f"[Watcher] Error moving file {filename}: {e}")
        finally:
            # unmark processing (use discard to be safe)
            self._processing.discard(src_path)

    # event callbacks
    def on_created(self, event):
        # handle created files (and moved-in files also trigger on_moved)
        if event.is_directory:
            return
        path = event.src_path
        # if sentinel file was removed we shouldn't be here (observer stops), but we still check
        if os.path.basename(path) == SENTINEL_FILENAME:
            return
        # spawn a short-lived thread to not block the handler (so we can wait for stability)
        threading.Thread(target=self._process_new_file, args=(path,), daemon=True).start()

    def on_moved(self, event):
        # handle files moved into watched folder
        if event.is_directory:
            return
        dest_path = event.dest_path
        # if sentinel file was moved in/out, ignore
        if os.path.basename(dest_path) == SENTINEL_FILENAME:
            return
        threading.Thread(target=self._process_new_file, args=(dest_path,), daemon=True).start()


class FolderWatcher:
    """
    Controls a watchdog Observer for a single folder.
    - Creates the sentinel file if not present.
    - Stops itself if sentinel is deleted.
    """

    def __init__(self, folder_path, log_func=print, cm: CategoryManager = None, 
                 stable_checks=DEFAULT_STABLE_CHECKS,
                 check_interval=DEFAULT_STABLE_CHECK_INTERVAL, 
                 stability_timeout=DEFAULT_STABILITY_TIMEOUT):
        
        self.folder_path = os.path.abspath(folder_path)
        self.log = log_func
        # Use the passed-in CategoryManager, or create a default one if not provided
        self.cm = cm if cm is not None else CategoryManager()
        self.handler = _WatchHandler(self.folder_path, self.cm, log_func=self.log,
                                     stable_checks=stable_checks, check_interval=check_interval, stability_timeout=stability_timeout)
        self.observer = Observer()
        self._thread = None
        self._running = False

    def _sentinel_path(self):
        return os.path.join(self.folder_path, SENTINEL_FILENAME)

    def start(self):
        """
        Start watching the folder. Creates sentinel file if missing.
        """
        if not os.path.isdir(self.folder_path):
            raise ValueError("Folder does not exist: " + self.folder_path)

        # create sentinel if missing
        sentinel = self._sentinel_path()
        if not os.path.exists(sentinel):
            try:
                with open(sentinel, "w", encoding="utf-8") as f:
                    f.write("This folder is under watch of auto organizer (delete this to stop auto organization)\n")
            except Exception as e:
                self.log(f"[Watcher] Could not create sentinel file: {e}")

        # schedule handler
        self.observer.schedule(self.handler, self.folder_path, recursive=False)
        self.observer.start()
        self._running = True
        self._thread = threading.Thread(target=self._monitor_sentinel, daemon=True)
        self._thread.start()
        self.log(f"[Watcher] Started watching: {self.folder_path}")

    def _monitor_sentinel(self):
        """
        Background thread that watches the sentinel file. When sentinel is removed, stop observer.
        """
        sentinel = self._sentinel_path()
        while self._running:
            if not os.path.exists(sentinel):
                # stop observing if sentinel deleted
                self.log("[Watcher] Sentinel file removed — stopping watcher.")
                self.stop()
                break
            time.sleep(1)

    def stop(self):
        if not self._running:
            return
        self._running = False
        try:
            self.observer.stop()
            self.observer.join(timeout=5)
        except Exception:
            pass

        # --- NEW: Delete sentinel file on stop ---
        try:
            sentinel = self._sentinel_path()
            if os.path.exists(sentinel):
                os.remove(sentinel)
                self.log(f"[Watcher] Removed sentinel file.")
        except Exception as e:
            self.log(f"[Watcher] Error removing sentinel file: {e}")
        # --- END NEW ---

        self.log(f"[Watcher] Stopped watching: {self.folder_path}")

    def is_running(self):
        return self._running
