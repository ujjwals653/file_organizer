import os
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from categories import CategoryManager
from organizer import organize_folder, undo_last_organization


def create_main_window():
    root = ttk.Window(themename="litera")
    root.title("Local File Organizer")
    root.geometry("700x650")
    root.resizable(False, False)

    selected_folder = tk.StringVar(value="No folder selected")
    cm = CategoryManager()
    categories = cm.get()  # dict
    category_vars = {}

    # Logging widget
    def log_func(msg):
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)

    # Progress function
    def progress_func(processed, total):
        if total == 0:
            progress_var.set(0)
        else:
            progress_var.set(int((processed / total) * 100))
        root.update_idletasks()

    # Folder picker
    def select_folder():
        folder = filedialog.askdirectory()
        if folder:
            selected_folder.set(folder)

    # Refresh local categories & UI checkbox list
    def refresh_categories_ui():
        nonlocal categories
        categories = cm.get()
        for w in category_frame.winfo_children():
            w.destroy()
        category_vars.clear()
        
        # NEW: Iterate over the ordered dict
        for cat in categories:
            var = tk.BooleanVar(value=True)
            chk = ttk.Checkbutton(category_frame, text=cat, variable=var)
            chk.pack(anchor="w")
            category_vars[cat] = var

    # Open "View Categories" window
    def open_categories_window():
        win = ttk.Toplevel(root)
        win.title("Manage Categories")
        win.resizable(False, True) 
        win.grab_set()

        # --- DRAG & DROP STATE ---
        drag_data = {}
        
        # --- END D&D STATE ---

        control_frame = ttk.Frame(win)
        control_frame.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(control_frame, text="Add New", command=lambda: add_new_row(), bootstyle="primary", width=10).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Save & Close", command=lambda: (apply_row_selection(), win.destroy()), bootstyle="success", width=12).pack(side="right", padx=4)

        # Header row
        hdr = ttk.Frame(win)
        hdr.pack(fill="x", padx=8)
        
        # --- CHANGED: Added new column 0 for drag handle ---
        hdr_widths = [4, 6, 28, 60, 18] # Handle, Select, Category, Extensions, Actions
        ttk.Label(hdr, text="", width=hdr_widths[0], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="Select", width=hdr_widths[1], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(hdr, text="Category", width=hdr_widths[2], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
        ttk.Label(hdr, text="Extensions", width=hdr_widths[3], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w")
        ttk.Label(hdr, text="Actions", width=hdr_widths[4], anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w")
        # --- END CHANGE ---

        # Scrollable list area
        rows_frame = ttk.Frame(win)
        rows_frame.pack(fill="both", expand=True, padx=8, pady=6)

        list_canvas = tk.Canvas(rows_frame)
        scrollbar = ttk.Scrollbar(rows_frame, orient="vertical", command=list_canvas.yview)
        inner = ttk.Frame(list_canvas) 

        inner.bind(
            "<Configure>",
            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        )
        list_canvas.create_window((0, 0), window=inner, anchor="nw")
        list_canvas.configure(yscrollcommand=scrollbar.set)

        list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- NEW: Drop indicator ---
        # This separator will "move" to show where the drop will happen
        drop_indicator = ttk.Separator(inner, orient="horizontal")
        # --- END NEW ---

        row_vars = {}
        row_widgets = {}

        # --- DRAG & DROP FUNCTIONS ---
        def on_drag_start(event, cat_name):
            # Store which category we're dragging
            drag_data['category'] = cat_name
            drag_data['start_row'] = row_widgets[cat_name]['row']
            drag_data['widget'] = event.widget
            event.widget.config(cursor="fleur")

        def on_drag_motion(event):
            if 'category' not in drag_data:
                return

            # Find which row the mouse is currently over
            mouse_y_root = event.y_root
            target_row = -1
            
            # Sort rows by their current grid row index
            current_rows = sorted(row_widgets.values(), key=lambda w: w['row'])
            
            for row_data in current_rows:
                # Find the vertical center of the row
                handle = row_data['handle'] # Use the handle as the reference
                row_y_root = handle.winfo_rooty()
                row_height = handle.winfo_height()
                row_midpoint = row_y_root + (row_height / 2)

                if mouse_y_root < row_midpoint:
                    target_row = row_data['row']
                    break
            
            if target_row == -1:
                # Mouse is below all rows
                target_row = len(current_rows)
            
            # Move the drop indicator to the target row
            drop_indicator.grid_forget()
            drop_indicator.grid(row=target_row, column=0, columnspan=5, sticky="we", pady=0)
            drag_data['drop_target_row'] = target_row

        def on_drag_end(event):
            if 'widget' in drag_data:
                drag_data['widget'].config(cursor="hand2") # Reset cursor
            
            drop_indicator.grid_forget() # Hide indicator

            cat_to_move = drag_data.get('category')
            target_row = drag_data.get('drop_target_row')
            start_row = drag_data.get('start_row')

            # Clear drag data
            drag_data.clear()

            if cat_to_move and target_row is not None and target_row != start_row and target_row != start_row + 1:
                # We need to adjust the index if moving an item "down"
                # If moving [A, B, C] 'A' (0) to after 'B' (1), target_row will be 2
                # We want to insert at index 1
                final_index = target_row
                if target_row > start_row:
                    final_index -= 1
                
                # Update the CategoryManager
                cm.reorder(cat_to_move, final_index)
                
                # Refresh both UI lists
                refresh_categories_ui() # Main window
                rebuild_rows() # This popup window

        # --- END D&D FUNCTIONS ---


        def rebuild_rows():
            # Clear any old indicator
            drop_indicator.grid_forget()
            
            for w in inner.winfo_children():
                # Don't destroy the indicator itself, just hide it
                if w != drop_indicator:
                    w.destroy()
                    
            row_vars.clear()
            row_widgets.clear()
            cats = cm.get()
            r = 0
            for cat, exts in cats.items():
                add_row(cat, exts, r)
                r += 1

        def add_row(cat_name, exts_list, row_index):
            # --- NEW: Drag Handle ---
            handle = ttk.Label(inner, text="☰", cursor="hand2")
            handle.grid(row=row_index, column=0, sticky="w", padx=(4, 6))
            # Bind drag events to the handle
            handle.bind("<Button-1>", lambda e, c=cat_name: on_drag_start(e, c))
            handle.bind("<B1-Motion>", on_drag_motion)
            handle.bind("<ButtonRelease-1>", on_drag_end)
            # --- END NEW ---

            v = tk.BooleanVar(value=category_vars.get(cat_name, tk.BooleanVar(value=True)).get() if cat_name in category_vars else True)
            chk = ttk.Checkbutton(inner, variable=v)
            # --- CHANGED: Column from 0 to 1 ---
            chk.grid(row=row_index, column=1, sticky="w", padx=4, pady=6)

            lbl_name = ttk.Label(inner, text=cat_name, anchor="w", width=hdr_widths[2])
            # --- CHANGED: Column from 1 to 2 ---
            lbl_name.grid(row=row_index, column=2, sticky="w")

            lbl_exts = ttk.Label(inner, text=", ".join(exts_list), anchor="w", width=hdr_widths[3], justify="left")
            # --- CHANGED: Column from 2 to 3 ---
            lbl_exts.grid(row=row_index, column=3, sticky="w")

            btn_frame = ttk.Frame(inner)
            # --- CHANGED: Column from 3 to 4 ---
            btn_frame.grid(row=row_index, column=4, sticky="w")
            btn_edit = ttk.Button(btn_frame, text="Edit", command=lambda c=cat_name: switch_to_edit(c), width=6, bootstyle="info-outline")
            btn_edit.pack(side="left", padx=2)
            btn_delete = ttk.Button(btn_frame, text="Delete", command=lambda c=cat_name: delete_category_confirm(c), width=6, bootstyle="danger-outline")
            btn_delete.pack(side="left", padx=2)

            row_vars[cat_name] = v
            row_widgets[cat_name] = {
                "handle": handle, # Store handle
                "chk": chk, "lbl_name": lbl_name, "lbl_exts": lbl_exts,
                "btn_edit": btn_edit, "btn_delete": btn_delete, "row": row_index
            }

        def switch_to_edit(cat_name, creating_new=False):
            current_categories = cm.get()
            old_exts = current_categories.get(cat_name, []) if not creating_new else []

            if cat_name in row_widgets:
                r = row_widgets[cat_name]["row"]
            else:
                r = len(row_widgets)

            for widget in inner.grid_slaves(row=r):
                widget.destroy()

            # --- NEW: Add disabled handle placeholder ---
            handle = ttk.Label(inner, text="☰", cursor="arrow") # Not draggable
            handle.config(state="disabled")
            handle.grid(row=r, column=0, sticky="w", padx=(4, 6))
            # --- END NEW ---

            sel_var = row_vars.get(cat_name, tk.BooleanVar(value=True))
            chk = ttk.Checkbutton(inner, variable=sel_var)
            chk.grid(row=r, column=1, sticky="w", padx=4, pady=6)

            name_var = tk.StringVar(value=cat_name if not creating_new else "")
            ent_name = ttk.Entry(inner, textvariable=name_var, width=hdr_widths[2] + 2) # Make entry slightly wider
            ent_name.grid(row=r, column=2, sticky="w", padx=2)

            ext_var = tk.StringVar(value=", ".join(old_exts))
            ent_exts = ttk.Entry(inner, textvariable=ext_var, width=hdr_widths[3] + 2) # Make entry slightly wider
            ent_exts.grid(row=r, column=3, sticky="w", padx=2)

            btn_frame = ttk.Frame(inner)
            btn_frame.grid(row=r, column=4, sticky="w")
            btn_save = ttk.Button(btn_frame, text="Save", command=lambda: save_edit(cat_name, name_var.get().strip(), ext_var.get().strip(), creating_new), width=6, bootstyle="success")
            btn_save.pack(side="left", padx=2)
            btn_cancel = ttk.Button(btn_frame, text="Cancel", command=lambda: cancel_edit(cat_name, creating_new), width=6, bootstyle="secondary")
            btn_cancel.pack(side="left", padx=2)

            new_key = name_var.get() if creating_new else cat_name
            row_vars[new_key] = sel_var
            row_widgets[new_key] = {
                "handle": handle, "chk": chk, "ent_name": ent_name, "ent_exts": ent_exts,
                "btn_save": btn_save, "btn_cancel": btn_cancel, "row": r,
                "creating_new": creating_new, "orig_name": cat_name
            }
            ent_name.focus_set()

        def save_edit(orig_name, new_name, new_exts_csv, creating_new=False):
            if not new_name:
                messagebox.showwarning("Validation", "Category name cannot be empty.", parent=win)
                return
            exts = [e.strip().lower() for e in new_exts_csv.split(",")] if new_exts_csv else []
            exts = [e for e in exts if e]

            try:
                if creating_new:
                    cm.add(new_name, exts)
                else:
                    cm.edit(orig_name, new_name=new_name if new_name != orig_name else None, new_exts=exts)
            except ValueError as e:
                messagebox.showerror("Error", f"Could not save category: {e}", parent=win)
                return

            refresh_categories_ui()
            rebuild_rows()

        def cancel_edit(cat_name, creating_new=False):
            rebuild_rows()

        def add_new_row():
            r = len(row_widgets)
            temp_key = f"__new_{r}"
            switch_to_edit(temp_key, creating_new=True)

        def delete_category_confirm(cat_name):
            if messagebox.askyesno("Delete Category", f"Delete category '{cat_name}'? This will not move/delete files.", parent=win):
                cm.delete(cat_name)
                refresh_categories_ui()
                rebuild_rows()

        def apply_row_selection():
            cats = cm.get()
            for w in category_frame.winfo_children():
                w.destroy()
            category_vars.clear()
            for cat in cats:
                val = True
                if cat in row_vars:
                    try:
                        val = row_vars[cat].get()
                    except Exception:
                        val = True
                var = tk.BooleanVar(value=val)
                chk = ttk.Checkbutton(category_frame, text=cat, variable=var)
                chk.pack(anchor="w")
                category_vars[cat] = var

        rebuild_rows()

        def on_close():
            apply_row_selection()
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

    def start_organizing():
        folder = selected_folder.get()
        if not os.path.exists(folder) or folder == "No folder selected":
            messagebox.showwarning("Warning", "Please select a valid folder first.")
            return
        selected = [cat for cat, var in category_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Warning", "Select at least one category.")
            return
        if messagebox.askyesno("Preview", "Run a dry-run first (no files will be moved)?"):
            organize_folder(folder, cm.get(), selected, log_func=log_func, progress_func=progress_func, dry_run=True)
            if not messagebox.askyesno("Proceed", "Dry-run complete. Proceed with actual organization?"):
                return
        organize_folder(folder, cm.get(), selected, log_func=log_func, progress_func=progress_func, dry_run=False)
        messagebox.showinfo("Done", "Organization finished.")

    def undo_action():
        if messagebox.askyesno("Undo", "Undo last organization?"):
            undo_last_organization(log_func=log_func)
            messagebox.showinfo("Undo", "Undo complete.")

    # ---- Build main UI ----
    ttk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

    category_frame = ttk.Labelframe(root, text="Select Categories to Organize")
    category_frame.pack(pady=8, fill="x", padx=12)
    refresh_categories_ui()

    controls = ttk.Frame(root)
    controls.pack(pady=6)
    ttk.Button(controls, text="View Categories", command=open_categories_window, width=14, bootstyle="info").pack(side="left", padx=6)
    ttk.Button(controls, text="Select Folder", command=select_folder, width=14, bootstyle="primary").pack(side="left", padx=6)
    ttk.Button(controls, text="Organize Files", command=start_organizing, width=14, bootstyle="success").pack(side="left", padx=6)
    ttk.Button(controls, text="Undo Last Organization", command=undo_action, width=18, bootstyle="danger").pack(side="left", padx=6)

    ttk.Label(root, textvariable=selected_folder, wraplength=650, bootstyle="secondary").pack(pady=6)

    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate", variable=progress_var, bootstyle="success-striped")
    progress_bar.pack(pady=6)

    log_frame = ttk.Labelframe(root, text="Activity Log")
    log_frame.pack(padx=12, pady=10, fill="both", expand=True)
    
    log_text = tk.Text(log_frame, height=15)
    log_text.pack(side="left", fill="both", expand=True, padx=(4,0), pady=4)
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    scrollbar.pack(side="right", fill="y")
    log_text.config(yscrollcommand=scrollbar.set)

    log_func("Ready. Click 'View Categories' to manage categories or 'Select Folder' to begin.")

    root.mainloop()

if __name__ == "__main__":
    create_main_window()