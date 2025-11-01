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
                    # normalize keys and extensions
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
        self.categories[name] = [e.strip().lower() for e in exts]
        self.save()

    def edit(self, old_name, new_name=None, new_exts=None):
        if old_name not in self.categories:
            return False
        exts = self.categories.pop(old_name)
        name = new_name or old_name
        if new_exts is not None:
            exts = [e.strip().lower() for e in new_exts]
        self.categories[name] = exts
        self.save()
        return True

    def delete(self, name):
        if name in self.categories:
            self.categories.pop(name)
            self.save()
            return True
        return False

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
