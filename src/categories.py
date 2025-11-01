import os
import json

DEFAULT_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif"],
    "Documents": [".pdf", ".docx", ".txt", ".pptx", ".xls", ".xlsx"],
    "Audio": [".mp3", ".wav", ".flac"],
    "Video": [".mp4", ".mkv", ".mov"],
    "Code": [".py", ".js", ".cpp", ".java", ".html", ".css"],
    "Archives": [".zip", ".rar", ".tar", ".gz"],
    "Others": []
}

CATEGORY_FILE = os.path.join("config", "categories.json")

def load_categories():
    if os.path.exists(CATEGORY_FILE):
        with open(CATEGORY_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CATEGORIES.copy()

def save_categories(categories):
    os.makedirs("config", exist_ok=True)
    with open(CATEGORY_FILE, "w") as f:
        json.dump(categories, f, indent=4)
