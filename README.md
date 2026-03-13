# Folder Cleaner

A Python command-line tool to scan, filter, deduplicate, and clean up any folder on Windows.

## Features

- Scan and display all file types and sub-folders with sizes
- Delete files by extension with optional filters
- Age filter — only delete files older than N days
- Size filter — only delete files larger than a given size
- Duplicate detector — finds and removes duplicate files (keeps oldest copy)
- Exclude list — protect specific files, extensions, or folders from deletion
- Recursive scan — go into sub-folders
- Dry run — safely preview what would be deleted before doing anything
- Verbose mode — see every file name during preview or deletion
- All deletions go to the **Recycle Bin** (not permanent)
- Deletion log saved automatically to `cleaner.log`
- Windows right-click context menu integration

---

## Requirements

- Python 3.10+
- Windows

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/your-username/folder-cleaner.git
cd folder-cleaner
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. (Optional) Add to PATH for easy access from any folder**

Add the `folder-cleaner` folder to your Windows PATH environment variable.
Then you can run `clean scan` from anywhere in CMD.

**4. (Optional) Set up Windows right-click context menu**

Right-click `scripts\setup_context_menu.bat` → **Run as Administrator**
After this, right-clicking any folder shows **"Clean with Cleaner"**.

To remove the context menu later:
Right-click `scripts\remove_context_menu.bat` → **Run as Administrator**

---

## Usage

All commands target `%USERPROFILE%\Downloads` by default.
Use `--folder "PATH"` before the subcommand to target a different folder.

### Scan
```bash
# Show all file types and sub-folders
python main.py scan

# Scan recursively into sub-folders
python main.py scan --recursive

# Scan a specific folder
python main.py --folder "D:\Work" scan
```

### Clean (delete by file type / folder)
```bash
# Preview files that would be deleted (safe — nothing is deleted)
python main.py clean -t zip,exe --dry-run
python main.py clean -t zip,exe --dry-run -v        # with file list

# Delete files
python main.py clean -t zip,exe
python main.py clean -t zip,exe -v                  # with file list

# Delete ALL file types
python main.py clean -t all --dry-run -v

# Delete sub-folders by name
python main.py clean -f "temp,old stuff" --dry-run -v
python main.py clean -f all --dry-run -v            # all sub-folders

# Combine files + folders
python main.py clean -t zip,exe -f "temp" --dry-run -v
```

### Filters (combine with clean)
```bash
# Only files older than 30 days
python main.py clean -t zip --older-than 30 --dry-run -v

# Only files larger than 50 MB
python main.py clean -t pdf --larger-than 50MB --dry-run -v

# Combine both filters
python main.py clean -t zip --older-than 30 --larger-than 10MB --dry-run -v

# Recursive (include files in sub-folders)
python main.py clean -t zip --recursive --dry-run -v
```

### Find Duplicates
```bash
# Preview duplicates (keeps oldest copy, removes the rest)
python main.py dupes --dry-run -v

# Actually remove duplicates
python main.py dupes -v

# Recursive
python main.py dupes --recursive --dry-run -v
```

### Exclude List
Files, extensions, and folders on the exclude list are **never deleted**, even if targeted.

```bash
# View current exclude list
python main.py config --show

# Add to exclude list
python main.py config --add-ext docx --add-ext xlsx
python main.py config --add-file "important.pdf"
python main.py config --add-folder "Work"

# Remove from exclude list
python main.py config --remove-ext docx
python main.py config --remove-file "important.pdf"
python main.py config --remove-folder "Work"
```

### Check version
```bash
python main.py --version
```

---

## Project Structure

```
folder-cleaner/
├── cleaner/
│   ├── __init__.py          — package info & version
│   ├── cleaner.py           — core CLI logic
│   └── launcher.py          — interactive right-click menu
├── scripts/
│   ├── clean.bat            — shortcut to run from anywhere in CMD
│   ├── setup_context_menu.bat  — registers right-click menu (run as Admin once)
│   └── remove_context_menu.bat — removes right-click menu (run as Admin)
├── main.py                  — entry point
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## Safety

- All deletions use `send2trash` — files go to the **Recycle Bin**, not permanently deleted
- `--dry-run` mode lets you preview every deletion before it happens
- The exclude list protects important files from accidental deletion
- `config.json` and `cleaner.log` are personal and excluded from git via `.gitignore`

---

## Version History

### v0.1.0
- Initial release
- Scan, clean, dupes, config subcommands
- Age filter, size filter, recursive scan
- Exclude list with config.json
- Deletion log
- Windows right-click context menu integration

---

## License

All rights reserved. See [LICENSE](LICENSE) for details.
