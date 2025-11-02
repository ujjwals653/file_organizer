import os
import json

DEFAULT_CATEGORIES = {
	"Applications": [".exe", ".msi"],
    "Images": [".jpg", ".jpeg", ".png", ".gif"],
    "Documents": [".pdf", ".docx", ".txt", ".pptx", ".xls", ".xlsx"],
    "Audio": [".mp3", ".wav", ".flac"],
    "Video": [".mp4", ".mkv", ".mov"],
    "Code": [".py", ".js", ".cpp", ".java", ".html", ".css"],
    "Archives": [".zip", ".rar", ".tar", ".gz"],
    "Others": []
}

CONFIG_DIR = "config"
CATEGORY_FILE = os.path.join(CONFIG_DIR, "categories.json")


class CategoryManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.categories = self._load()

    def _load(self):
        if os.path.exists(CATEGORY_FILE):
            with open(CATEGORY_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    # Python dicts preserve insertion order (Python 3.7+)
                    return {k: [ext.lower() for ext in v] for k, v in data.items()}
                except Exception:
                    return DEFAULT_CATEGORIES.copy()
        return DEFAULT_CATEGORIES.copy()

    def save(self):
        with open(CATEGORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.categories, f, indent=4, ensure_ascii=False)

    def get(self):
        return self.categories

    def add(self, name, exts):
        if name in self.categories:
            raise ValueError(f"Category '{name}' already exists.")
        self.categories[name] = [e.strip().lower() for e in exts]
        self.save()

    # --- (MODIFIED) ---
    # This method is now order-preserving. It rebuilds the dictionary
    # instead of using .pop() which ruins the order.
    def edit(self, old_name, new_name=None, new_exts=None):
        if old_name not in self.categories:
            return False
        
        # Check for name collision if renaming
        if new_name and new_name != old_name and new_name in self.categories:
            raise ValueError(f"Category name '{new_name}' already exists.")

        new_dict = {}
        for cat_name, exts_list in self.categories.items():
            if cat_name == old_name:
                # This is the item to change
                updated_name = new_name if new_name else old_name
                updated_exts = [e.strip().lower() for e in new_exts] if new_exts is not None else exts_list
                new_dict[updated_name] = updated_exts
            else:
                # Just copy the existing item
                new_dict[cat_name] = exts_list
        
        self.categories = new_dict
        self.save()
        return True
    # --- (END MODIFICATION) ---

    def delete(self, name):
        if name in self.categories:
            self.categories.pop(name)
            self.save()
            return True
        return False

    # --- (NEW METHOD) ---
    def reorder(self, category_to_move, new_index):
        """Moves a category to a new index in the order."""
        items = list(self.categories.items())
        
        # Find the item to move
        current_index = -1
        for i, (name, exts) in enumerate(items):
            if name == category_to_move:
                current_index = i
                break
        
        if current_index == -1:
            return # Category not found

        # Pop and insert
        item_to_move = items.pop(current_index)
        items.insert(new_index, item_to_move)
        
        # Rebuild the dictionary from the reordered list
        self.categories = dict(items)
        self.save()
    # --- (END NEW METHOD) ---

    def rename(self, old_name, new_name):
        return self.edit(old_name, new_name=new_name)

    def extensions_for(self, name):
        return self.categories.get(name, [])

    def find_category_for_ext(self, ext):
        ext = ext.lower()
        for cat, exts in self.categories.items():
            if ext in exts:
                return cat
        return None

    def category_folders(self):
        # returns a set of folder names that represent categories (safe to use to skip)
        return set(self.categories.keys())
