# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the tool:**
```bash
python main.py scan
python main.py clean -t zip,exe --dry-run -v
python main.py dupes --dry-run -v
python main.py config --show
```

**Run the interactive launcher (right-click menu mode):**
```bash
python cleaner/launcher.py "C:/path/to/folder"
```

There are no automated tests in this project.

## Architecture

- `main.py` — thin entry point; imports `build_parser` from `cleaner/cleaner.py` and dispatches to subcommands
- `cleaner/cleaner.py` — all CLI logic: argument parsing (`build_parser`), four subcommand handlers (`cmd_scan`, `cmd_clean`, `cmd_dupes`, `cmd_config`), and shared helpers
- `cleaner/launcher.py` — interactive TUI menu for the Windows right-click context menu integration; spawns `cleaner.py` as a subprocess for each action
- `scripts/` — `.bat` files for Windows PATH shortcut and Registry-based context menu install/uninstall

**Data files** (gitignored, stored at project root):
- `config.json` — persists the exclude list (excluded files, extensions, folders)
- `cleaner.log` — append-only deletion log

**Key design points:**
- All deletions use `send2trash` (Recycle Bin, never permanent)
- `cleaner.py` is self-contained and can be invoked directly or via `main.py`
- `launcher.py` calls `cleaner.py` via `subprocess`, so both entry points share identical behaviour
- `SCRIPT_DIR` in `cleaner.py` resolves to the project root (parent of `cleaner/`), which is where `config.json` and `cleaner.log` are stored
- Duplicate detection uses two-pass: group by file size first, then MD5 hash only on size-matched candidates
