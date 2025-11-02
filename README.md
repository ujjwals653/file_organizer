# 🗂️ Local File Organizer (Python + Tkinter)

A simple desktop app built with **Python** and **Tkinter** that helps you automatically organize files in any folder based on their type.  
It categorizes files like Images, Documents, Audio, Videos, Code files, Archives, etc., into separate subfolders.

---

## ✨ Features

- Select any folder using a GUI dialog
- Automatically sorts files into categorized subfolders
- Supports multiple file types (images, documents, media, code, etc.)
- Simple and clean interface built with Tkinter
- Works on Windows, macOS, and Linux

---

## 🖼️ Before and After

### 📁 Before Organization

![Before](assets/before.png)

### 🗃️ After Organization

![After](assets/after.png)

---

## ❓ How to Use

1.  **Download the latest release** (the `.exe` file) from the repository’s [Releases](../../releases) section.
2.  Place the `.exe` file anywhere on your computer (e.g., Desktop).
3.  Double-click to open the app. The window will open, and the app will also start running in your system tray.

### Auto-Organization (for New Files)

This is the main feature. The app will monitor a folder and organize new files as they arrive.

1.  Click **“Manage Auto-Organization”**.
2.  In the new window, click **“Add Folder”** and select a folder you want to keep clean (e.g., your `Downloads` folder).
3.  That's it! The folder is now being watched. You can close this window.
4.  When a new file is saved or downloaded into that folder, the app will automatically wait for it to be stable, then move it into the correct category subfolder (e.g., `Downloads/Documents`).

### Manual Organization (for Existing Files)

If you have a messy folder _before_ you started watching it, you can run a one-time organization.

1.  Click **“Manage Auto-Organization”**.
2.  Find the folder you want to clean up in the list.
3.  Click the **“Organize Now”** button next to it.
4.  The app will scan all existing files in that folder and move them to their correct category subfolders. (This will ignore any new files that arrive during the scan).

---

## 🧩 Tech Stack

- **Language:** Python
- **GUI:** Tkinter
- **Libraries:** `os`, `shutil`, `tkinter`, `filedialog`, `messagebox`
- **Packaged with:** PyInstaller (`pyinstaller --onefile file_organizer_gui.py`)

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).

---

Made with ❤️ using Python
