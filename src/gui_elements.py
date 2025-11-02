import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- IMPORTS for Tray, Startup, and Threading ---
import queue
import threading
from PIL import Image, ImageTk # Requires 'Pillow'
import pystray # Requires 'pystray'
import winshell # Requires 'winshell'
from file_watcher import FolderWatcher

from categories import CategoryManager
from organizer import organize_folder, undo_last_organization

# --- NEW GLOBALS & CONFIG ---
CONFIG_DIR = "config"
WATCHED_FOLDERS_FILE = os.path.join(CONFIG_DIR, "watched_folders.json")
STARTUP_SHORTCUT_NAME = "File Organizer.lnk"

# Global state
global_watchers = {}  # Holds {path: FolderWatcher}
log_queue = queue.Queue()
tray_icon_thread = None
app_is_quitting = False

def create_main_window():
    root = ttk.Window(themename="litera")
    root.title("Local File Organizer")
    root.geometry("700x550")
    root.resizable(False, False)
    
    # --- Set window icon (Requires icon.ico) ---
    try:
        # This logic helps find the icon when frozen by PyInstaller
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_path,'icon.ico')
        app_icon = ImageTk.PhotoImage(file=icon_path)
        root.iconphoto(True, app_icon)
    except Exception as e:
        print(f"Error loading icon.ico: {e}. Please create an icon.ico file.")
        icon_path = None # Will use a default image later
    # --- END NEW ---

    # Use the real CategoryManager
    cm = CategoryManager()
    categories = cm.get()
    category_vars = {}

    # --- LOGGING (Now thread-safe) ---
    def log_func(msg):
        """Main GUI log function."""
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)

    def thread_safe_log_func(msg):
        """Puts a log message onto the queue from any thread."""
        log_queue.put(msg)

    def process_log_queue():
        """Polls the queue and updates the GUI log."""
        try:
            while True:
                msg = log_queue.get_nowait()
                log_func(msg)
        except queue.Empty:
            pass  # No more messages
        
        if not app_is_quitting:
            root.after(100, process_log_queue)
    # --- END LOGGING ---

    # --- WATCHER MANAGEMENT ---
    def start_watcher(folder_path):
        if folder_path in global_watchers:
            log_func(f"[Info] Watcher for {folder_path} is already running.")
            return
        if not os.path.isdir(folder_path):
            log_func(f"[Error] Cannot watch non-existent folder: {folder_path}")
            return
        
        try:
            # Pass the REAL category manager and the thread-safe logger
            watcher = FolderWatcher(folder_path, log_func=thread_safe_log_func, cm=cm)
            watcher.start()
            global_watchers[folder_path] = watcher
            thread_safe_log_func(f"[Watcher] Started watching: {folder_path}")
        except Exception as e:
            thread_safe_log_func(f"[Error] Failed to start watcher for {folder_path}: {e}")

    def stop_watcher(folder_path):
        watcher = global_watchers.pop(folder_path, None)
        if watcher:
            watcher.stop()
            thread_safe_log_func(f"[Watcher] Stopped watching: {folder_path}")
    
    def load_watched_folders():
        try:
            with open(WATCHED_FOLDERS_FILE, 'r') as f:
                folders = json.load(f)
            log_func(f"Loaded {len(folders)} watched folder(s) from config.")
            for folder in folders:
                start_watcher(folder)
        except FileNotFoundError:
            log_func("No watched folder config found. Starting fresh.")
        except Exception as e:
            log_func(f"Error loading watched folders: {e}")
            
    def save_watched_folders():
        try:
            with open(WATCHED_FOLDERS_FILE, 'w') as f:
                json.dump(list(global_watchers.keys()), f, indent=2)
        except Exception as e:
            log_func(f"Error saving watched folders: {e}")

    # --- Watcher Manager Window (Replaces "Organize" button) ---
    def open_watcher_manager_window(cm): # Now accepts CategoryManager
        win = ttk.Toplevel(root)
        win.title("Manage Auto-Organization")
        win.geometry("750x450") # Made wider for buttons
        win.resizable(False, True)
        win.grab_set()

        def run_manual_org(folder_path):
            if not messagebox.askyesno("Confirm Organize", f"This will organize all existing files in:\n\n{folder_path}\n\nThis may take a while. Are you sure?", parent=win):
                return
            
            thread_safe_log_func(f"[Manual Org] Starting manual scan for: {folder_path}...")
            
            # Get all categories
            all_categories_dict = cm.get()
            all_category_names = list(all_categories_dict.keys())
            
            # Run the existing organizer.py function in a background thread
            # We pass the thread_safe_log_func and 'None' for progress
            org_thread = threading.Thread(
                target=organize_folder,
                args=(folder_path, all_categories_dict, all_category_names, thread_safe_log_func, None, False),
                daemon=True
            )
            org_thread.start()
            
            messagebox.showinfo("Organization Started", 
                                "Manual organization has started in the background.\nCheck the Activity Log for progress.", 
                                parent=win)

        # --- Top control frame ---
        control_frame = ttk.Frame(win)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(control_frame, text="Add Folder to Watch", command=lambda: add_folder(), bootstyle="success").pack(side="left", padx=5)
        ttk.Button(control_frame, text="Close", command=win.destroy, bootstyle="secondary").pack(side="right", padx=5)
        
        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=10)

        # --- Custom list area (replaces Listbox) ---
        list_frame = ttk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        list_canvas = tk.Canvas(list_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=list_canvas.yview)
        inner_frame = ttk.Frame(list_canvas) # This frame holds the rows

        inner_frame.bind(
            "<Configure>",
            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all"), width=e.width)
        )
        
        list_canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        list_canvas.configure(yscrollcommand=scrollbar.set)

        list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- Functions to manage the custom list ---
        
        def rebuild_folder_list():
            # Clear old widgets
            for widget in inner_frame.winfo_children():
                widget.destroy()
            
            # Add header
            ttk.Label(inner_frame, text="Watched Folder Path", font=("-weight bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            ttk.Label(inner_frame, text="Actions", font=("-weight bold")).grid(row=0, column=1, columnspan=2, sticky="w", padx=10, pady=5)
            
            # Add a row for each watched folder
            row_index = 1
            if not global_watchers:
                ttk.Label(inner_frame, text="No folders are being watched.", bootstyle="secondary").grid(row=1, column=0, padx=10, pady=10)
                
            for path in global_watchers.keys():
                # The folder path label
                path_label = ttk.Label(inner_frame, text=path, wraplength=450, justify="left")
                path_label.grid(row=row_index, column=0, sticky="w", padx=10, pady=8)
                
                # "Organize Now" button
                org_button = ttk.Button(inner_frame, text="Organize Now", 
                                        command=lambda p=path: run_manual_org(p), 
                                        bootstyle="primary-outline", width=12)
                org_button.grid(row=row_index, column=1, sticky="e", padx=5)
                
                # "Remove" button
                remove_button = ttk.Button(inner_frame, text="Remove Watch", 
                                           command=lambda p=path: remove_folder(p), 
                                           bootstyle="danger-outline", width=12)
                remove_button.grid(row=row_index, column=2, sticky="e", padx=10)
                
                row_index += 1
        
        def add_folder():
            folder = filedialog.askdirectory(parent=win)
            if folder and folder not in global_watchers:
                start_watcher(folder)
                save_watched_folders()
                rebuild_folder_list() # Update UI
            elif folder:
                messagebox.showwarning("Already Watching", "That folder is already being watched.", parent=win)
                
        def remove_folder(path_to_remove):
            if messagebox.askyesno("Confirm Removal", f"Stop watching this folder?\n\n{path_to_remove}", parent=win):
                stop_watcher(path_to_remove) # This also deletes the sentinel
                save_watched_folders()
                rebuild_folder_list() # Update UI

        # Initial load
        rebuild_folder_list()
    
    
    # --- Category Checkbox Refresh ---
    def refresh_categories_ui():
        nonlocal categories
        categories = cm.get()
        for w in category_frame.winfo_children():
            w.destroy()
        category_vars.clear()
        
        for cat in categories: # Dicts preserve order
            var = tk.BooleanVar(value=True)
            chk = ttk.Checkbutton(category_frame, text=cat, variable=var)
            chk.pack(anchor="w")
            category_vars[cat] = var

    # --- "View Categories" Window (with Drag-and-Drop) ---
    def open_categories_window():
        win = ttk.Toplevel(root)
        win.title("Manage Categories")
        win.resizable(False, True) 
        win.grab_set()

        drag_data = {}

        control_frame = ttk.Frame(win)
        control_frame.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(control_frame, text="Add New", command=lambda: add_new_row(), bootstyle="primary", width=10).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Save & Close", command=lambda: (apply_row_selection(), win.destroy()), bootstyle="success", width=12).pack(side="right", padx=4)

        hdr = ttk.Frame(win)
        hdr.pack(fill="x", padx=8)
        hdr_widths = [4, 6, 28, 60, 18]
        ttk.Label(hdr, text="", width=hdr_widths[0]).grid(row=0, column=0)
        ttk.Label(hdr, text="Select", width=hdr_widths[1], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(hdr, text="Category", width=hdr_widths[2], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
        ttk.Label(hdr, text="Extensions", width=hdr_widths[3], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w")
        ttk.Label(hdr, text="Actions", width=hdr_widths[4], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w")

        rows_frame = ttk.Frame(win)
        rows_frame.pack(fill="both", expand=True, padx=8, pady=6)
        list_canvas = tk.Canvas(rows_frame)
        scrollbar = ttk.Scrollbar(rows_frame, orient="vertical", command=list_canvas.yview)
        inner = ttk.Frame(list_canvas) 
        inner.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=inner, anchor="nw")
        list_canvas.configure(yscrollcommand=scrollbar.set)
        list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        drop_indicator = ttk.Separator(inner, orient="horizontal")

        row_vars = {}
        row_widgets = {}

        def on_drag_start(event, cat_name):
            drag_data['category'] = cat_name
            drag_data['start_row'] = row_widgets[cat_name]['row']
            drag_data['widget'] = event.widget
            event.widget.config(cursor="fleur") # Use standard cursor

        def on_drag_motion(event):
            if 'category' not in drag_data: return
            mouse_y_root = event.y_root
            target_row = -1
            current_rows = sorted(row_widgets.values(), key=lambda w: w['row'])
            
            for row_data in current_rows:
                handle = row_data['handle']
                row_y_root = handle.winfo_rooty()
                row_height = handle.winfo_height()
                row_midpoint = row_y_root + (row_height / 2)
                if mouse_y_root < row_midpoint:
                    target_row = row_data['row']
                    break
            
            if target_row == -1: target_row = len(current_rows)
            
            drop_indicator.grid_forget()
            drop_indicator.grid(row=target_row, column=0, columnspan=5, sticky="we", pady=0)
            drag_data['drop_target_row'] = target_row

        def on_drag_end(event):
            if 'widget' in drag_data:
                drag_data['widget'].config(cursor="hand2")
            drop_indicator.grid_forget()
            cat_to_move = drag_data.get('category')
            target_row = drag_data.get('drop_target_row')
            start_row = drag_data.get('start_row')
            drag_data.clear()

            if cat_to_move and target_row is not None and target_row != start_row and target_row != start_row + 1:
                final_index = target_row
                if target_row > start_row:
                    final_index -= 1
                
                cm.reorder(cat_to_move, final_index)
                refresh_categories_ui()
                rebuild_rows()

        def rebuild_rows():
            drop_indicator.grid_forget()
            for w in inner.winfo_children():
                if w != drop_indicator: w.destroy()
            row_vars.clear(); row_widgets.clear()
            cats = cm.get(); r = 0
            for cat, exts in cats.items(): add_row(cat, exts, r); r += 1

        def add_row(cat_name, exts_list, row_index):
            handle = ttk.Label(inner, text="☰", cursor="hand2")
            handle.grid(row=row_index, column=0, sticky="w", padx=(4, 6))
            handle.bind("<Button-1>", lambda e, c=cat_name: on_drag_start(e, c))
            handle.bind("<B1-Motion>", on_drag_motion)
            handle.bind("<ButtonRelease-1>", on_drag_end)

            v = tk.BooleanVar(value=category_vars.get(cat_name, tk.BooleanVar(value=True)).get())
            chk = ttk.Checkbutton(inner, variable=v)
            chk.grid(row=row_index, column=1, sticky="w", padx=4, pady=6)
            lbl_name = ttk.Label(inner, text=cat_name, anchor="w", width=hdr_widths[2])
            lbl_name.grid(row=row_index, column=2, sticky="w")
            lbl_exts = ttk.Label(inner, text=", ".join(exts_list), anchor="w", width=hdr_widths[3], justify="left")
            lbl_exts.grid(row=row_index, column=3, sticky="w")
            btn_frame = ttk.Frame(inner)
            btn_frame.grid(row=row_index, column=4, sticky="w")
            btn_edit = ttk.Button(btn_frame, text="Edit", command=lambda c=cat_name: switch_to_edit(c), width=6, bootstyle="info-outline")
            btn_edit.pack(side="left", padx=2)
            btn_delete = ttk.Button(btn_frame, text="Delete", command=lambda c=cat_name: delete_category_confirm(c), width=6, bootstyle="danger-outline")
            btn_delete.pack(side="left", padx=2)
            row_vars[cat_name] = v
            row_widgets[cat_name] = {"handle": handle, "chk": chk, "lbl_name": lbl_name, "lbl_exts": lbl_exts, "btn_edit": btn_edit, "btn_delete": btn_delete, "row": row_index}

        def switch_to_edit(cat_name, creating_new=False):
            current_categories = cm.get(); old_exts = current_categories.get(cat_name, []) if not creating_new else []
            r = row_widgets[cat_name]["row"] if cat_name in row_widgets else len(row_widgets)
            for widget in inner.grid_slaves(row=r): widget.destroy()
            handle = ttk.Label(inner, text="☰", cursor="arrow"); handle.config(state="disabled"); handle.grid(row=r, column=0, sticky="w", padx=(4, 6))
            sel_var = row_vars.get(cat_name, tk.BooleanVar(value=True)); chk = ttk.Checkbutton(inner, variable=sel_var); chk.grid(row=r, column=1, sticky="w", padx=4, pady=6)
            name_var = tk.StringVar(value=cat_name if not creating_new else ""); ent_name = ttk.Entry(inner, textvariable=name_var, width=hdr_widths[2] + 2); ent_name.grid(row=r, column=2, sticky="w", padx=2)
            ext_var = tk.StringVar(value=", ".join(old_exts)); ent_exts = ttk.Entry(inner, textvariable=ext_var, width=hdr_widths[3] + 2); ent_exts.grid(row=r, column=3, sticky="w", padx=2)
            btn_frame = ttk.Frame(inner); btn_frame.grid(row=r, column=4, sticky="w")
            btn_save = ttk.Button(btn_frame, text="Save", command=lambda: save_edit(cat_name, name_var.get().strip(), ext_var.get().strip(), creating_new), width=6, bootstyle="success"); btn_save.pack(side="left", padx=2)
            btn_cancel = ttk.Button(btn_frame, text="Cancel", command=lambda: cancel_edit(cat_name, creating_new), width=6, bootstyle="secondary"); btn_cancel.pack(side="left", padx=2)
            new_key = name_var.get() if creating_new else cat_name
            row_vars[new_key] = sel_var
            row_widgets[new_key] = {"handle": handle, "chk": chk, "ent_name": ent_name, "ent_exts": ent_exts, "btn_save": btn_save, "btn_cancel": btn_cancel, "row": r, "creating_new": creating_new, "orig_name": cat_name}
            ent_name.focus_set()
        
        def save_edit(orig_name, new_name, new_exts_csv, creating_new=False):
            if not new_name: messagebox.showwarning("Validation", "Category name cannot be empty.", parent=win); return
            exts = [e.strip().lower() for e in new_exts_csv.split(",")] if new_exts_csv else []; exts = [e for e in exts if e]
            try:
                if creating_new: cm.add(new_name, exts)
                else: cm.edit(orig_name, new_name=new_name if new_name != orig_name else None, new_exts=exts)
            except Exception as e: messagebox.showerror("Error", f"Could not save category: {e}", parent=win); return
            # When categories change, we MUST re-create watchers so they have the new rules
            # Easiest way: just log it and let the user restart, or...
            log_func("[Info] Category changes will apply to new files.")
            # We also refresh the main UI
            refresh_categories_ui()
            rebuild_rows()
        
        def cancel_edit(cat_name, creating_new=False): rebuild_rows()
        def add_new_row(): r = len(row_widgets); temp_key = f"__new_{r}"; switch_to_edit(temp_key, creating_new=True)
        def delete_category_confirm(cat_name):
            if messagebox.askyesno("Delete Category", f"Delete category '{cat_name}'?", parent=win):
                cm.delete(cat_name)
                log_func("[Info] Category changes will apply to new files.")
                refresh_categories_ui()
                rebuild_rows()
        
        def apply_row_selection():
            cats = cm.get();
            for w in category_frame.winfo_children(): w.destroy()
            category_vars.clear()
            for cat in cats:
                val = row_vars[cat].get() if cat in row_vars else True
                var = tk.BooleanVar(value=val); chk = ttk.Checkbutton(category_frame, text=cat, variable=var); chk.pack(anchor="w"); category_vars[cat] = var
        
        rebuild_rows()
        win.protocol("WM_DELETE_WINDOW", lambda: (apply_row_selection(), win.destroy()))

    # --- STARTUP MANAGEMENT ---
    def get_shortcut_path():
        startup_folder = winshell.startup()
        return os.path.join(startup_folder, STARTUP_SHORTCUT_NAME)

    def check_startup_status():
        shortcut_path = get_shortcut_path()
        startup_var.set(os.path.exists(shortcut_path))

    def toggle_startup():
        shortcut_path = get_shortcut_path()
        try:
            if startup_var.get():
                # Create shortcut
                # Use sys.executable, which is the .exe path when frozen
                target_path = sys.executable
                working_dir = os.path.dirname(target_path)
                
                with winshell.shortcut(shortcut_path) as shortcut:
                    shortcut.path = target_path
                    shortcut.working_directory = working_dir
                    shortcut.description = "File Organizer"
                log_func("Created startup shortcut.")
            else:
                # Remove shortcut
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    log_func("Removed startup shortcut.")
        except Exception as e:
            log_func(f"Error managing startup shortcut: {e}")
            messagebox.showerror("Startup Error", f"Could not manage startup shortcut.\nTry running as administrator.\nError: {e}")
            startup_var.set(os.path.exists(shortcut_path)) # Reset to actual state

    # --- TRAY ICON & APP CLOSE MANAGEMENT ---
    global_tray_icon = None

    def show_from_tray():
        global global_tray_icon
        if global_tray_icon:
            global_tray_icon.stop()
            global_tray_icon = None
        root.after(0, root.deiconify) # 'after' ensures it runs on main thread

    def quit_app():
        global app_is_quitting, global_tray_icon
        
        # 1. User is asked to confirm the quit
        if not messagebox.askyesno("Quit?", "Are you sure you want to quit?\nThis will stop all file watchers."):
            return
            
        app_is_quitting = True
        
        if global_tray_icon:
            global_tray_icon.stop()
            
        log_func("Shutting down... stopping watchers.")
        
        # 2. It loops through every running watcher
        for path in list(global_watchers.keys()):
            # 3. It calls stop_watcher() for each one
            stop_watcher(path) 
        
        # 4. And stop_watcher() is where we added the code
        #    to delete the sentinel file.
        
        save_watched_folders()
        root.quit()

    def hide_to_tray():
        """Hides the window to the system tray."""
        root.withdraw()
        
        def run_tray_icon(icon_image):
            global global_tray_icon
            
            menu = (pystray.MenuItem('Show', show_from_tray, default=True),
                    pystray.MenuItem('Quit', quit_app))
            
            global_tray_icon = pystray.Icon("file_organizer", icon_image, "File Organizer", menu)
            global_tray_icon.run()

        # Load icon for tray
        try:
            tray_icon_image = Image.open(icon_path)
        except Exception:
            # Create a default black square if icon.ico is missing
            tray_icon_image = Image.new('RGB', (64, 64), color='black')

        # Start tray icon in a separate thread
        global tray_icon_thread
        if not tray_icon_thread or not tray_icon_thread.is_alive():
            tray_icon_thread = threading.Thread(target=run_tray_icon, args=(tray_icon_image,), daemon=True)
            tray_icon_thread.start()

    # --- RESTORED: Undo Action ---
    def undo_action():
        if messagebox.askyesno("Undo", "Undo last auto-organization move?"):
            # Pass the main GUI logger, as this is a manual action
            undo_last_organization(log_func=log_func)
    # --- END RESTORED ---

    # ---- Build main UI ----
    ttk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

    # Note: This frame is now informational, as the watcher uses
    # the categories from CategoryManager directly.
    category_frame = ttk.Labelframe(root, text="Categories Loaded (Managed in 'Manage Categories')")
    category_frame.pack(pady=8, fill="x", padx=12)
    refresh_categories_ui()

    controls = ttk.Frame(root)
    controls.pack(pady=10, fill="x", padx=10)
    
    # --- NEW: Replaced button layout ---
    ttk.Button(controls, text="Manage Categories", command=open_categories_window, bootstyle="info").pack(side="left", padx=6)
    ttk.Button(controls, text="Manage Auto-Organization", command=lambda: open_watcher_manager_window(cm), bootstyle="success").pack(side="left", padx=6)
    
    # --- RESTORED: Undo Button ---
    ttk.Button(controls, text="Undo Last Move", command=undo_action, bootstyle="danger-outline").pack(side="left", padx=6)
    # --- END RESTORED ---
    
    startup_var = tk.BooleanVar()
    startup_check = ttk.Checkbutton(controls, text="Run on Startup", variable=startup_var, command=toggle_startup, bootstyle="secondary")
    startup_check.pack(side="right", padx=6)
    # --- END NEW ---

    log_frame = ttk.Labelframe(root, text="Activity Log")
    log_frame.pack(padx=12, pady=10, fill="both", expand=True)
    
    log_text = tk.Text(log_frame, height=15, font=("Segoe UI", 9))
    log_text.pack(side="left", fill="both", expand=True, padx=(4,0), pady=4)
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    scrollbar.pack(side="right", fill="y")
    log_text.config(yscrollcommand=scrollbar.set)

    # --- INITIALIZATION ---
    os.makedirs(CONFIG_DIR, exist_ok=True)
    check_startup_status()
    load_watched_folders()
    process_log_queue()
    log_func("Ready. Manage auto-organization or categories.")
    log_func("App will minimize to tray on close.")

    root.protocol("WM_DELETE_WINDOW", hide_to_tray)
    root.mainloop()

if __name__ == "__main__":
    create_main_window()