import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from categories import CategoryManager
from organizer import organize_folder, undo_last_organization


def create_main_window():
    root = tk.Tk()
    root.title("Local File Organizer")
    root.geometry("700x650")
    root.resizable(False, False)

    selected_folder = tk.StringVar(value="No folder selected")
    cm = CategoryManager()
    categories = cm.get()  # dict
    # category_vars maps category name -> BooleanVar (selected or not)
    category_vars = {}

    # Logging widget
    def log_func(msg):
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)

    # Progress function: expects processed, total
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
        # clear frame
        for w in category_frame.winfo_children():
            w.destroy()
        category_vars.clear()
        for cat in categories:
            var = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(category_frame, text=cat, variable=var)
            chk.pack(anchor="w")
            category_vars[cat] = var

    # Open "View Categories" window (single window for all category management)
    def open_categories_window():
        win = tk.Toplevel(root)
        win.title("Manage Categories")
        win.geometry("750x450")
        root.resizable(False, True)
        win.grab_set()  # modal-like behavior

        # Top controls
        control_frame = tk.Frame(win)
        control_frame.pack(fill="x", padx=8, pady=(8, 4))
        tk.Button(control_frame, text="Add New", command=lambda: add_new_row(), bg="#8e44ad", fg="white", width=10).pack(side="left", padx=4)
        tk.Button(control_frame, text="Save & Close", command=lambda: (apply_row_selection(), win.destroy()), bg="#2ecc71", fg="white", width=12).pack(side="right", padx=4)

        # Header row
        hdr = tk.Frame(win)
        hdr.pack(fill="x", padx=8)
        tk.Label(hdr, text="Select", width=6, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(hdr, text="Category", width=25, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(hdr, text="Extensions", width=50, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
        tk.Label(hdr, text="Actions", width=18, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w")

        # Scrollable list area
        rows_frame = tk.Frame(win)
        rows_frame.pack(fill="both", expand=True, padx=8, pady=6)

        list_canvas = tk.Canvas(rows_frame)
        scrollbar = ttk.Scrollbar(rows_frame, orient="vertical", command=list_canvas.yview)
        inner = tk.Frame(list_canvas)

        inner.bind(
            "<Configure>",
            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        )
        list_canvas.create_window((0, 0), window=inner, anchor="nw")
        list_canvas.configure(yscrollcommand=scrollbar.set)

        list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Keep references to row widgets and selection vars
        row_vars = {}       # cat_name -> BooleanVar (select/unselect)
        row_widgets = {}    # cat_name -> dict of widgets for easy manipulation

        def rebuild_rows():
            # Destroy existing widgets and recreate from cm.get()
            for w in inner.winfo_children():
                w.destroy()
            row_vars.clear()
            row_widgets.clear()
            cats = cm.get()
            r = 0
            for cat, exts in cats.items():
                add_row(cat, exts, r)
                r += 1

        def add_row(cat_name, exts_list, row_index):
            """
            Create a normal (non-editing) row for the category.
            """
            v = tk.BooleanVar(value=category_vars.get(cat_name, tk.BooleanVar(value=True)).get() if cat_name in category_vars else True)
            chk = tk.Checkbutton(inner, variable=v)
            chk.grid(row=row_index, column=0, sticky="w", padx=4, pady=6)

            lbl_name = tk.Label(inner, text=cat_name, anchor="w", width=25)
            lbl_name.grid(row=row_index, column=1, sticky="w")

            lbl_exts = tk.Label(inner, text=", ".join(exts_list), anchor="w", width=50, wraplength=380, justify="left")
            lbl_exts.grid(row=row_index, column=2, sticky="w")

            btn_frame = tk.Frame(inner)
            btn_frame.grid(row=row_index, column=3, sticky="w")
            btn_edit = tk.Button(btn_frame, text="Edit", command=lambda c=cat_name: switch_to_edit(c), width=6)
            btn_edit.pack(side="left", padx=2)
            btn_delete = tk.Button(btn_frame, text="Delete", command=lambda c=cat_name: delete_category_confirm(c), width=6)
            btn_delete.pack(side="left", padx=2)

            row_vars[cat_name] = v
            row_widgets[cat_name] = {
                "chk": chk,
                "lbl_name": lbl_name,
                "lbl_exts": lbl_exts,
                "btn_edit": btn_edit,
                "btn_delete": btn_delete,
                "row": row_index
            }

        def switch_to_edit(cat_name, creating_new=False):
            """
            Replace labels with Entry widgets to allow inline editing for the given category.
            If 'creating_new' is True, we treat this as add-new row flow.
            """
            # If editing a category that doesn't exist in cm anymore, ignore
            current_categories = cm.get()
            old_exts = current_categories.get(cat_name, []) if not creating_new else []

            # find row index if exists otherwise append at the end
            if cat_name in row_widgets:
                r = row_widgets[cat_name]["row"]
            else:
                # append at end
                r = len(row_widgets)

            # clear any widgets at this row (if present)
            # iterate over widgets in that row and destroy them
            for widget in inner.grid_slaves(row=r):
                widget.destroy()

            # Checkbox variable
            sel_var = row_vars.get(cat_name, tk.BooleanVar(value=True))
            chk = tk.Checkbutton(inner, variable=sel_var)
            chk.grid(row=r, column=0, sticky="w", padx=4, pady=6)

            # Name entry
            name_var = tk.StringVar(value=cat_name if not creating_new else "")
            ent_name = tk.Entry(inner, textvariable=name_var, width=28)
            ent_name.grid(row=r, column=1, sticky="w", padx=2)

            # Exts entry
            ext_var = tk.StringVar(value=", ".join(old_exts))
            ent_exts = tk.Entry(inner, textvariable=ext_var, width=60)
            ent_exts.grid(row=r, column=2, sticky="w", padx=2)

            # Buttons: Save, Cancel
            btn_frame = tk.Frame(inner)
            btn_frame.grid(row=r, column=3, sticky="w")
            btn_save = tk.Button(btn_frame, text="Save", command=lambda: save_edit(cat_name, name_var.get().strip(), ext_var.get().strip(), creating_new), width=6, bg="#27ae60", fg="white")
            btn_save.pack(side="left", padx=2)
            btn_cancel = tk.Button(btn_frame, text="Cancel", command=lambda: cancel_edit(cat_name, creating_new), width=6)
            btn_cancel.pack(side="left", padx=2)

            # temporarily store these widgets
            new_key = name_var.get() if creating_new else cat_name
            row_vars[new_key] = sel_var
            row_widgets[new_key] = {
                "chk": chk,
                "ent_name": ent_name,
                "ent_exts": ent_exts,
                "btn_save": btn_save,
                "btn_cancel": btn_cancel,
                "row": r,
                "creating_new": creating_new,
                "orig_name": cat_name
            }

            ent_name.focus_set()

        def save_edit(orig_name, new_name, new_exts_csv, creating_new=False):
            """
            Save the edited or newly created category.
            """
            if not new_name:
                messagebox.showwarning("Validation", "Category name cannot be empty.", parent=win)
                return
            # parse extensions
            exts = [e.strip().lower() for e in new_exts_csv.split(",")] if new_exts_csv else []
            # remove empty strings
            exts = [e for e in exts if e]

            # If creating_new and name exists already -> warn
            if creating_new and new_name in cm.get():
                messagebox.showwarning("Duplicate", f"Category '{new_name}' already exists.", parent=win)
                rebuild_rows()
                return

            try:
                if creating_new:
                    cm.add(new_name, exts)
                else:
                    # if orig_name != new_name, call edit to rename; else update exts
                    cm.edit(orig_name, new_name=new_name if new_name != orig_name else None, new_exts=exts)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save category: {e}", parent=win)
                return

            # refresh both UI lists
            refresh_categories_ui()
            rebuild_rows()

        def cancel_edit(cat_name, creating_new=False):
            # On cancel, just rebuild rows to normal view
            rebuild_rows()

        def add_new_row():
            """
            Append an editable blank row at the end for creating a new category.
            """
            # determine new row index as current number of rows
            r = len(row_widgets)
            # Use a unique temporary key to avoid clash
            temp_key = f"__new_{r}"
            # create editable row with creating_new=True
            switch_to_edit(temp_key, creating_new=True)
            # After creation, the save handler uses creating_new flag to add real category

        def delete_category_confirm(cat_name):
            if messagebox.askyesno("Delete Category", f"Delete category '{cat_name}'? This will not move/delete files.", parent=win):
                cm.delete(cat_name)
                refresh_categories_ui()
                rebuild_rows()

        def apply_row_selection():
            """
            Update main window category_vars based on the checkboxes in categories window.
            We use the current cm.get() to align names and the stored row_vars booleans.
            """
            cats = cm.get()
            # Clear and re-create category_vars to match saved categories
            for w in category_frame.winfo_children():
                w.destroy()
            category_vars.clear()
            for cat in cats:
                # pick value from row_vars if exists, else default True
                val = True
                if cat in row_vars:
                    try:
                        val = row_vars[cat].get()
                    except Exception:
                        val = True
                var = tk.BooleanVar(value=val)
                chk = tk.Checkbutton(category_frame, text=cat, variable=var)
                chk.pack(anchor="w")
                category_vars[cat] = var

        # initial build
        rebuild_rows()

        # when window closes, ensure main UI updated
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
        # Optionally ask whether to dry-run
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
    tk.Label(root, text="Local File Organizer", font=("Segoe UI", 16, "bold")).pack(pady=10)

    # categories frame (checkboxes)
    category_frame = tk.LabelFrame(root, text="Select Categories to Organize")
    category_frame.pack(pady=8, fill="x", padx=12)
    refresh_categories_ui()

    controls = tk.Frame(root)
    controls.pack(pady=6)
    tk.Button(controls, text="View Categories", command=open_categories_window, width=14, bg="#2980b9", fg="white").pack(side="left", padx=6)
    tk.Button(controls, text="Select Folder", command=select_folder, width=14, bg="#3498db", fg="white").pack(side="left", padx=6)
    tk.Button(controls, text="Organize Files", command=start_organizing, width=14, bg="#2ecc71", fg="white").pack(side="left", padx=6)
    tk.Button(controls, text="Undo Last Organization", command=undo_action, width=18, bg="#e74c3c", fg="white").pack(side="left", padx=6)

    tk.Label(root, textvariable=selected_folder, wraplength=650, fg="gray").pack(pady=6)

    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate", variable=progress_var)
    progress_bar.pack(pady=6)

    # log area
    log_frame = tk.LabelFrame(root, text="Activity Log")
    log_frame.pack(padx=12, pady=10, fill="both", expand=True)
    log_text = tk.Text(log_frame, height=15)
    log_text.pack(side="left", fill="both", expand=True, padx=(4,0), pady=4)
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    scrollbar.pack(side="right", fill="y")
    log_text.config(yscrollcommand=scrollbar.set)

    # initial info
    log_func("Ready. Click 'View Categories' to manage categories or 'Select Folder' to begin.")

    root.mainloop()
