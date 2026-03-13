# Downloads Folder Cleaner

A Python command-line tool to scan, filter, deduplicate, and clean up your Downloads folder (or any folder) on Windows.

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
git clone https://github.com/your-username/downloads-cleaner.git
cd downloads-cleaner
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. (Optional) Add to PATH for easy access from any folder**

Add the `downloads-cleaner` folder to your Windows PATH environment variable.
Then you can run `clean scan` from anywhere in CMD.

**4. (Optional) Set up Windows right-click context menu**

Right-click `setup_context_menu.bat` → **Run as Administrator**
After this, right-clicking any folder shows **"Clean with Cleaner"**.

To remove the context menu later:
Right-click `remove_context_menu.bat` → **Run as Administrator**

---

## Usage

All commands target `%USERPROFILE%\Downloads` by default.
Use `--folder "PATH"` before the subcommand to target a different folder.

### Scan
```bash
# Show all file types and sub-folders
python cleaner.py scan

# Scan recursively into sub-folders
python cleaner.py scan --recursive

# Scan a specific folder
python cleaner.py --folder "D:\Work" scan
```

### Clean (delete by file type / folder)
```bash
# Preview files that would be deleted (safe — nothing is deleted)
python cleaner.py clean -t zip,exe --dry-run
python cleaner.py clean -t zip,exe --dry-run -v        # with file list

# Delete files
python cleaner.py clean -t zip,exe
python cleaner.py clean -t zip,exe -v                  # with file list

# Delete ALL file types
python cleaner.py clean -t all --dry-run -v

# Delete sub-folders by name
python cleaner.py clean -f "temp,old stuff" --dry-run -v
python cleaner.py clean -f all --dry-run -v            # all sub-folders

# Combine files + folders
python cleaner.py clean -t zip,exe -f "temp" --dry-run -v
```

### Filters (combine with clean)
```bash
# Only files older than 30 days
python cleaner.py clean -t zip --older-than 30 --dry-run -v

# Only files larger than 50 MB
python cleaner.py clean -t pdf --larger-than 50MB --dry-run -v

# Combine both filters
python cleaner.py clean -t zip --older-than 30 --larger-than 10MB --dry-run -v

# Recursive (include files in sub-folders)
python cleaner.py clean -t zip --recursive --dry-run -v
```

### Find Duplicates
```bash
# Preview duplicates (keeps oldest copy, removes the rest)
python cleaner.py dupes --dry-run -v

# Actually remove duplicates
python cleaner.py dupes -v

# Recursive
python cleaner.py dupes --recursive --dry-run -v
```

### Exclude List
Files, extensions, and folders on the exclude list are **never deleted**, even if targeted.

```bash
# View current exclude list
python cleaner.py config --show

# Add to exclude list
python cleaner.py config --add-ext docx --add-ext xlsx
python cleaner.py config --add-file "important.pdf"
python cleaner.py config --add-folder "Work"

# Remove from exclude list
python cleaner.py config --remove-ext docx
python cleaner.py config --remove-file "important.pdf"
python cleaner.py config --remove-folder "Work"
```

### Check version
```bash
python cleaner.py --version
```

---

## File Overview

| File | Purpose |
|---|---|
| `cleaner.py` | Main CLI script |
| `launcher.py` | Interactive menu launcher (used by context menu) |
| `clean.bat` | Shortcut — run `clean scan` from anywhere in CMD |
| `setup_context_menu.bat` | Registers right-click menu (run as Admin once) |
| `remove_context_menu.bat` | Removes right-click menu (run as Admin) |
| `config.json` | Auto-created — stores your exclude list |
| `cleaner.log` | Auto-created — deletion history log |

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
