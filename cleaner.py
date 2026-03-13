"""
Downloads Folder Cleaner  v0.1.0
Commands:
  scan    - show all file types, folders, sizes
  clean   - delete files/folders with filters
  dupes   - find and remove duplicate files
  config  - manage the exclude list

Examples:
  python cleaner.py scan
  python cleaner.py --folder "C:/Users/me/Downloads" scan --recursive

  python cleaner.py clean -t zip,exe --dry-run -v
  python cleaner.py clean -t zip --older-than 30 --dry-run -v
  python cleaner.py clean -t pdf --larger-than 50MB --dry-run -v
  python cleaner.py clean -t all -f all --recursive --dry-run -v

  python cleaner.py dupes --dry-run -v
  python cleaner.py dupes --recursive

  python cleaner.py config --show
  python cleaner.py config --add-ext docx --add-file "keep.pdf" --add-folder "Work"
  python cleaner.py config --remove-ext docx
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import send2trash
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# ── Constants ──────────────────────────────────────────────────────────────────
__version__       = "0.1.0"

DEFAULT_DOWNLOADS = Path.home() / "Downloads"
SCRIPT_DIR        = Path(__file__).parent
CONFIG_FILE       = SCRIPT_DIR / "config.json"
LOG_FILE          = SCRIPT_DIR / "cleaner.log"
console           = Console()

DEFAULT_CONFIG = {
    "excluded_files":      [],
    "excluded_extensions": [],
    "excluded_folders":    [],
}

# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ── Logging ────────────────────────────────────────────────────────────────────

def write_log(action: str, folder: str, items: list) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as lf:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lf.write(f"\n{'='*64}\n")
            lf.write(f"[{ts}]  {action}\n")
            lf.write(f"Folder : {folder}\n")
            lf.write(f"Items  : {len(items)}\n")
            lf.write(f"{'─'*64}\n")
            for item in items:
                try:
                    size = item.stat().st_size
                except OSError:
                    size = 0
                lf.write(f"  {item}  ({format_size(size)})\n")
    except OSError as e:
        console.print(f"[yellow]Warning:[/yellow] Could not write log: {e}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def format_size(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def parse_size(s: str) -> int:
    """Parse '10MB', '500KB', '1.5GB' → bytes."""
    s = s.strip().upper().replace(" ", "")
    for suffix, factor in [("TB", 1024**4), ("GB", 1024**3), ("MB", 1024**2), ("KB", 1024), ("B", 1)]:
        if s.endswith(suffix):
            return int(float(s[: -len(suffix)]) * factor)
    return int(s)


def file_hash(path: Path, chunk: int = 8192) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def get_files(folder: Path, recursive: bool = False) -> list:
    if not folder.exists():
        console.print(f"[bold red]Error:[/bold red] Folder not found: {folder}")
        sys.exit(1)
    if recursive:
        return [f for f in folder.rglob("*") if f.is_file()]
    return [f for f in folder.iterdir() if f.is_file()]


def get_subfolders(folder: Path) -> list:
    return sorted([d for d in folder.iterdir() if d.is_dir()], key=lambda d: d.name.lower())


def build_ext_map(files: list) -> dict:
    m: dict = defaultdict(list)
    for f in files:
        ext = f.suffix.lower().lstrip(".") or "no_extension"
        m[ext].append(f)
    return dict(sorted(m.items()))


def resolve_targets(types_arg: str, ext_map: dict) -> set:
    if types_arg.lower() == "all":
        return set(ext_map.keys())
    return {e.strip().lower().lstrip(".") for e in types_arg.split(",") if e.strip()}


def is_excluded(path: Path, cfg: dict) -> bool:
    return (
        path.name.lower() in {e.lower() for e in cfg["excluded_files"]}
        or path.suffix.lower().lstrip(".") in {e.lower() for e in cfg["excluded_extensions"]}
    )


def apply_filters(files: list, cfg: dict, older_than=None, larger_than=None) -> dict:
    """
    Returns dict:
      kept       — files that pass all filters
      excluded   — blocked by exclude list
      too_new    — blocked by age filter
      too_small  — blocked by size filter
    """
    result = {"kept": [], "excluded": [], "too_new": [], "too_small": []}
    cutoff   = (datetime.now() - timedelta(days=older_than)) if older_than else None
    min_size = parse_size(larger_than) if larger_than else None

    for f in files:
        if is_excluded(f, cfg):
            result["excluded"].append(f)
        elif cutoff and datetime.fromtimestamp(f.stat().st_mtime) >= cutoff:
            result["too_new"].append(f)
        elif min_size is not None and f.stat().st_size < min_size:
            result["too_small"].append(f)
        else:
            result["kept"].append(f)

    return result


def do_delete(items: list, verbose: bool) -> tuple:
    """Send items to Recycle Bin. Returns (deleted_count, failed_list)."""
    deleted, failed = 0, []
    for item in items:
        is_dir = item.is_dir()
        try:
            send2trash.send2trash(str(item))
            deleted += 1
            if verbose:
                tag = "[yellow]folder[/yellow]" if is_dir else "file"
                console.print(f"  [green]✓[/green] {tag}: {item.name}")
        except Exception as exc:
            failed.append((item, str(exc)))
            if verbose:
                console.print(f"  [red]✗[/red] {item.name}  —  {exc}")
    return deleted, failed


# ── Subcommand: scan ──────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> None:
    folder     = Path(args.folder)
    cfg        = load_config()
    files      = get_files(folder, args.recursive)
    ext_map    = build_ext_map(files)
    subfolders = get_subfolders(folder)
    excl_exts  = {e.lower() for e in cfg["excluded_extensions"]}
    excl_dirs  = {e.lower() for e in cfg["excluded_folders"]}
    label      = f"{'[dim](recursive)[/dim] ' if args.recursive else ''}{folder}"

    if not ext_map and not subfolders:
        console.print("[yellow]Folder is empty.[/yellow]")
        return

    # ── Files table ────────────────────────────────────────────────────────────
    if ext_map:
        table = Table(title=f"File Types in {label}", box=box.ROUNDED,
                      show_lines=True, title_style="bold cyan")
        table.add_column("Extension",  style="cyan",    no_wrap=True)
        table.add_column("Files",      style="magenta", justify="right")
        table.add_column("Total Size", style="green",   justify="right")
        table.add_column("Excluded",   style="yellow",  justify="center")

        total_files = total_bytes = 0
        for ext, flist in ext_map.items():
            size = sum(f.stat().st_size for f in flist)
            table.add_row(
                f".{ext}", str(len(flist)), format_size(size),
                "[yellow]✓[/yellow]" if ext in excl_exts else "",
            )
            total_files += len(flist)
            total_bytes += size

        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {total_files} file(s)  |  [bold]{format_size(total_bytes)}[/bold]\n")

    # ── Folders table ──────────────────────────────────────────────────────────
    if subfolders:
        ftable = Table(title="Sub-Folders", box=box.ROUNDED,
                       show_lines=True, title_style="bold yellow")
        ftable.add_column("#",           style="dim",     justify="right", width=4)
        ftable.add_column("Folder Name", style="yellow")
        ftable.add_column("Items",       style="magenta", justify="right")
        ftable.add_column("Size",        style="green",   justify="right")
        ftable.add_column("Excluded",    style="yellow",  justify="center")

        for idx, d in enumerate(subfolders, 1):
            try:
                items = sum(1 for _ in d.iterdir())
            except PermissionError:
                items = -1
            ftable.add_row(
                str(idx), d.name,
                str(items) if items >= 0 else "[red]no access[/red]",
                format_size(folder_size(d)),
                "[yellow]✓[/yellow]" if d.name.lower() in excl_dirs else "",
            )

        console.print(ftable)
        console.print(f"\n[bold]Sub-folders:[/bold] {len(subfolders)}\n")

    console.print(
        "[dim]Tip: [bold]python cleaner.py clean -t ext1,ext2 --dry-run -v[/bold]  to preview deletion.[/dim]"
    )
    if LOG_FILE.exists():
        console.print(f"[dim]Log file: {LOG_FILE}[/dim]")


# ── Subcommand: clean ─────────────────────────────────────────────────────────

def cmd_clean(args: argparse.Namespace) -> None:
    folder     = Path(args.folder)
    cfg        = load_config()
    files      = get_files(folder, args.recursive)
    ext_map    = build_ext_map(files)
    subfolders = get_subfolders(folder)

    # ── Resolve files ──────────────────────────────────────────────────────────
    matched_files: list = []
    skipped_count = 0
    if args.types:
        targets = resolve_targets(args.types, ext_map)
        unknown = targets - set(ext_map.keys())
        if unknown:
            console.print(f"[yellow]Warning:[/yellow] Extensions not found: {', '.join(sorted(unknown))}")
        raw = [f for ext in targets for f in ext_map.get(ext, [])]
        stats = apply_filters(raw, cfg, args.older_than, args.larger_than)
        matched_files = sorted(stats["kept"], key=lambda f: f.name.lower())
        skipped_count = len(stats["excluded"]) + len(stats["too_new"]) + len(stats["too_small"])

    # ── Resolve folders ────────────────────────────────────────────────────────
    matched_folders: list = []
    excl_dirs = {e.lower() for e in cfg["excluded_folders"]}
    if args.folders:
        pool = [d for d in subfolders if d.name.lower() not in excl_dirs]
        if args.folders.lower() == "all":
            matched_folders = pool
        else:
            names = {n.strip().lower() for n in args.folders.split(",") if n.strip()}
            matched_folders = [d for d in pool if d.name.lower() in names]
            not_found = names - {d.name.lower() for d in matched_folders}
            if not_found:
                console.print(f"[yellow]Warning:[/yellow] Folders not found: {', '.join(sorted(not_found))}")

    if not matched_files and not matched_folders:
        console.print("[yellow]Nothing matched. Check your -t / -f args or filters.[/yellow]")
        return

    total_file_size   = sum(f.stat().st_size for f in matched_files)
    total_folder_size = sum(folder_size(d) for d in matched_folders)
    total_size        = total_file_size + total_folder_size
    mode_label        = "[bold yellow]DRY RUN[/bold yellow]" if args.dry_run else "[bold red]DELETE[/bold red]"

    # ── Header panel ───────────────────────────────────────────────────────────
    lines = f"  Mode      : {mode_label}\n"
    if args.types:
        lines += f"  Types     : [cyan]{args.types}[/cyan]\n"
    if args.older_than:
        lines += f"  Age filter: older than [cyan]{args.older_than}[/cyan] days\n"
    if args.larger_than:
        lines += f"  Size filter: larger than [cyan]{args.larger_than}[/cyan]\n"
    if args.recursive:
        lines += f"  Scan      : [cyan]recursive[/cyan]\n"
    if skipped_count:
        lines += f"  Skipped   : [yellow]{skipped_count}[/yellow] file(s) (excluded/filtered)\n"
    if matched_files:
        lines += f"  Files     : [magenta]{len(matched_files)}[/magenta]  ({format_size(total_file_size)})\n"
    if matched_folders:
        lines += f"  Folders   : [yellow]{len(matched_folders)}[/yellow]  ({format_size(total_folder_size)})\n"
    lines += f"  Total     : [bold green]{format_size(total_size)}[/bold green]"

    console.print(Panel(lines, title="Downloads Cleaner", box=box.ROUNDED))

    # ── Verbose file listing ───────────────────────────────────────────────────
    if args.verbose and matched_files:
        ft = Table(title="Selected Files", box=box.SIMPLE_HEAD, show_lines=False, title_style="bold cyan")
        ft.add_column("#",        style="dim",     justify="right", width=5)
        ft.add_column("File Name",style="cyan")
        ft.add_column("Ext",      style="magenta", width=10)
        ft.add_column("Size",     style="green",   justify="right", width=12)
        ft.add_column("Modified", style="dim",     width=12)
        for idx, f in enumerate(matched_files, 1):
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
            ft.add_row(str(idx), f.name, f.suffix.lower() or "(none)", format_size(f.stat().st_size), mtime)
        console.print(ft)

    if args.verbose and matched_folders:
        dt = Table(title="Selected Folders", box=box.SIMPLE_HEAD, show_lines=False, title_style="bold yellow")
        dt.add_column("#",           style="dim",     justify="right", width=5)
        dt.add_column("Folder Name", style="yellow")
        dt.add_column("Items",       style="magenta", justify="right", width=8)
        dt.add_column("Size",        style="green",   justify="right", width=12)
        for idx, d in enumerate(matched_folders, 1):
            try:
                items = sum(1 for _ in d.iterdir())
            except PermissionError:
                items = -1
            dt.add_row(str(idx), d.name, str(items) if items >= 0 else "[red]?[/red]", format_size(folder_size(d)))
        console.print(dt)

    # ── Dry run ────────────────────────────────────────────────────────────────
    if args.dry_run:
        hints = "".join([
            f" -t {args.types}"            if args.types       else "",
            f" -f {args.folders}"          if args.folders     else "",
            f" --older-than {args.older_than}" if args.older_than else "",
            f" --larger-than {args.larger_than}" if args.larger_than else "",
            " --recursive"                 if args.recursive   else "",
            " -v"                          if args.verbose     else "",
        ])
        console.print(
            f"\n[bold yellow]Dry run complete[/bold yellow] — nothing deleted.\n"
            f"To delete, re-run without [bold]--dry-run[/bold]:\n"
            f"  [dim]python cleaner.py clean{hints}[/dim]\n"
        )
        return

    # ── Delete ─────────────────────────────────────────────────────────────────
    console.print("\n[bold red]Sending to Recycle Bin…[/bold red]\n")

    del_f, fail_f = do_delete(matched_files,   args.verbose)
    del_d, fail_d = do_delete(matched_folders, args.verbose)
    failed = fail_f + fail_d

    write_log("DELETE", str(folder), matched_files[:del_f] + matched_folders[:del_d])

    parts = []
    if del_f: parts.append(f"[magenta]{del_f}[/magenta] file(s)")
    if del_d: parts.append(f"[yellow]{del_d}[/yellow] folder(s)")
    console.print(
        f"\n[bold green]Done![/bold green]  Moved {' and '.join(parts)} "
        f"([green]{format_size(total_size)}[/green]) to Recycle Bin.\n"
        f"[dim]Log saved → {LOG_FILE}[/dim]"
    )
    if failed:
        console.print(f"\n[bold red]Failed:[/bold red] {len(failed)} item(s):")
        for item, reason in failed:
            console.print(f"  [red]✗[/red] {item.name}  —  {reason}")


# ── Subcommand: dupes ─────────────────────────────────────────────────────────

def cmd_dupes(args: argparse.Namespace) -> None:
    folder = Path(args.folder)
    cfg    = load_config()

    console.print(f"[dim]Scanning {'recursively ' if args.recursive else ''}for duplicates in {folder}…[/dim]")
    all_files = [f for f in get_files(folder, args.recursive) if not is_excluded(f, cfg)]

    # Step 1 — group by size (fast pre-filter)
    by_size: dict = defaultdict(list)
    for f in all_files:
        by_size[f.stat().st_size].append(f)
    candidates = [f for group in by_size.values() if len(group) > 1 for f in group]

    if not candidates:
        console.print("[green]No duplicate files found.[/green]")
        return

    # Step 2 — group by MD5 hash
    console.print(f"[dim]Hashing {len(candidates)} candidate file(s)…[/dim]")
    by_hash: dict = defaultdict(list)
    for f in candidates:
        try:
            by_hash[file_hash(f)].append(f)
        except OSError:
            pass

    dupe_groups = {h: paths for h, paths in by_hash.items() if len(paths) > 1}

    if not dupe_groups:
        console.print("[green]No duplicate files found.[/green]")
        return

    total_dupes = sum(len(v) - 1 for v in dupe_groups.values())
    total_waste = sum(
        f.stat().st_size * (len(v) - 1)
        for v in dupe_groups.values()
        for f in [sorted(v, key=lambda x: x.stat().st_mtime)[0]]
    )

    console.print(
        Panel(
            f"  Mode        : {'[bold yellow]DRY RUN[/bold yellow]' if args.dry_run else '[bold red]DELETE[/bold red]'}\n"
            f"  Groups      : [magenta]{len(dupe_groups)}[/magenta]\n"
            f"  Duplicates  : [magenta]{total_dupes}[/magenta] file(s) to remove\n"
            f"  Reclaimable : [green]{format_size(total_waste)}[/green]\n"
            f"  Strategy    : keep [cyan]oldest[/cyan] file in each group",
            title="Duplicate Files",
            box=box.ROUNDED,
        )
    )

    to_delete: list = []
    for idx, (_, group) in enumerate(sorted(dupe_groups.items()), 1):
        group_sorted = sorted(group, key=lambda f: f.stat().st_mtime)   # oldest first
        keep   = group_sorted[0]
        remove = group_sorted[1:]
        to_delete.extend(remove)

        if args.verbose:
            console.print(f"\n  [bold]Group {idx}[/bold]")
            console.print(f"    [green]KEEP[/green]  {keep.name}  [dim]({format_size(keep.stat().st_size)})[/dim]")
            for r in remove:
                console.print(f"    [red]DEL [/red]  {r.name}  [dim]({format_size(r.stat().st_size)})[/dim]")

    if args.dry_run:
        console.print(
            f"\n[bold yellow]Dry run complete[/bold yellow] — nothing deleted.\n"
            f"To delete, re-run without [bold]--dry-run[/bold]:\n"
            f"  [dim]python cleaner.py dupes"
            + (" --recursive" if args.recursive else "")
            + (" -v" if args.verbose else "") + "[/dim]\n"
        )
        return

    console.print("\n[bold red]Removing duplicates to Recycle Bin…[/bold red]\n")
    deleted, failed = do_delete(to_delete, args.verbose)
    write_log("DUPES", str(folder), to_delete[:deleted])

    console.print(
        f"\n[bold green]Done![/bold green]  Removed [magenta]{deleted}[/magenta] duplicate(s) "
        f"([green]{format_size(total_waste)}[/green]) to Recycle Bin.\n"
        f"[dim]Log saved → {LOG_FILE}[/dim]"
    )
    if failed:
        console.print(f"\n[bold red]Failed:[/bold red] {len(failed)} item(s):")
        for item, reason in failed:
            console.print(f"  [red]✗[/red] {item.name}  —  {reason}")


# ── Subcommand: config ────────────────────────────────────────────────────────

def cmd_config(args: argparse.Namespace) -> None:
    cfg = load_config()

    if args.show:
        table = Table(title="Exclude List", box=box.ROUNDED, show_lines=True, title_style="bold")
        table.add_column("Type",  style="cyan")
        table.add_column("Value", style="yellow")
        for name in cfg["excluded_files"]:
            table.add_row("file", name)
        for ext in cfg["excluded_extensions"]:
            table.add_row("extension", f".{ext}")
        for d in cfg["excluded_folders"]:
            table.add_row("folder", d)
        if not any(cfg.values()):
            console.print("[yellow]Exclude list is empty.[/yellow]")
        else:
            console.print(table)
        console.print(f"\n[dim]Config : {CONFIG_FILE}[/dim]")
        console.print(f"[dim]Log    : {LOG_FILE}[/dim]")
        return

    def add_unique(lst: list, val: str) -> bool:
        v = val.strip().lower().lstrip(".")
        if v and v not in [x.lower() for x in lst]:
            lst.append(v)
            return True
        return False

    def remove_val(lst: list, val: str) -> bool:
        v = val.strip().lower().lstrip(".")
        before = len(lst)
        lst[:] = [x for x in lst if x.lower() != v]
        return len(lst) < before

    changed = False
    for v in (args.add_file    or []):
        if add_unique(cfg["excluded_files"],      v): console.print(f"[green]Added[/green]   file      : [cyan]{v}[/cyan]");      changed = True
    for v in (args.add_ext     or []):
        if add_unique(cfg["excluded_extensions"], v): console.print(f"[green]Added[/green]   extension : [cyan].{v.lstrip('.')}[/cyan]"); changed = True
    for v in (args.add_folder  or []):
        if add_unique(cfg["excluded_folders"],    v): console.print(f"[green]Added[/green]   folder    : [cyan]{v}[/cyan]");      changed = True
    for v in (args.remove_file or []):
        if remove_val(cfg["excluded_files"],      v): console.print(f"[red]Removed[/red] file      : [cyan]{v}[/cyan]");          changed = True
    for v in (args.remove_ext  or []):
        if remove_val(cfg["excluded_extensions"], v): console.print(f"[red]Removed[/red] extension : [cyan]{v}[/cyan]");          changed = True
    for v in (args.remove_folder or []):
        if remove_val(cfg["excluded_folders"],    v): console.print(f"[red]Removed[/red] folder    : [cyan]{v}[/cyan]");          changed = True

    if changed:
        save_config(cfg)
        console.print(f"\n[green]Config saved →[/green] {CONFIG_FILE}")
    elif not args.show:
        console.print("[yellow]Nothing changed. Use --show to view config.[/yellow]")


# ── CLI setup ─────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleaner",
        description="Downloads folder cleaner — scan, filter, deduplicate, and delete.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python cleaner.py scan
  python cleaner.py --folder "C:/Users/me/Downloads" scan --recursive

  python cleaner.py clean -t zip,exe --dry-run -v
  python cleaner.py clean -t zip --older-than 30 --dry-run -v
  python cleaner.py clean -t pdf --larger-than 50MB --dry-run -v
  python cleaner.py clean -t all -f all --recursive --dry-run -v
  python cleaner.py clean -f "temp,old" --dry-run -v

  python cleaner.py dupes --dry-run -v
  python cleaner.py dupes --recursive -v

  python cleaner.py config --show
  python cleaner.py config --add-ext docx --add-ext xlsx
  python cleaner.py config --add-file "important.pdf" --add-folder "Work"
  python cleaner.py config --remove-ext docx
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--folder", default=str(DEFAULT_DOWNLOADS), metavar="PATH",
        help=f"Target folder (default: {DEFAULT_DOWNLOADS})",
    )

    subs = parser.add_subparsers(dest="command", metavar="<command>")
    subs.required = True

    # ── scan ──────────────────────────────────────────────────────────────────
    sp = subs.add_parser("scan", help="Show all file types and folders in the target directory")
    sp.add_argument("--recursive", "-r", action="store_true", help="Scan sub-folders recursively")
    sp.set_defaults(func=cmd_scan)

    # ── clean ─────────────────────────────────────────────────────────────────
    cp = subs.add_parser("clean", help="Delete files/folders with optional filters")
    cp.add_argument("-t", "--types",   default=None, metavar="EXTENSIONS",
                    help='Extensions to target e.g. "jpg,png" or "all"')
    cp.add_argument("-f", "--folders", default=None, metavar="FOLDERS",
                    help='Folder names to target e.g. "temp,old" or "all"')
    cp.add_argument("--dry-run",       action="store_true",
                    help="Preview without deleting anything")
    cp.add_argument("-v", "--verbose", action="store_true",
                    help="Show each file/folder name")
    cp.add_argument("--older-than",    type=int, default=None, metavar="DAYS",
                    help="Only target files older than N days")
    cp.add_argument("--larger-than",   default=None, metavar="SIZE",
                    help='Only target files larger than SIZE e.g. "10MB", "500KB"')
    cp.add_argument("--recursive", "-r", action="store_true",
                    help="Scan sub-folders recursively")
    cp.set_defaults(func=cmd_clean)

    # ── dupes ─────────────────────────────────────────────────────────────────
    dp = subs.add_parser("dupes", help="Find and remove duplicate files (keeps oldest copy)")
    dp.add_argument("--dry-run",       action="store_true", help="Preview without deleting")
    dp.add_argument("-v", "--verbose", action="store_true", help="Show each duplicate group")
    dp.add_argument("--recursive", "-r", action="store_true", help="Scan sub-folders recursively")
    dp.set_defaults(func=cmd_dupes)

    # ── config ────────────────────────────────────────────────────────────────
    xp = subs.add_parser("config", help="Manage the exclude list and view config paths")
    xp.add_argument("--show",          action="store_true",  help="Show current exclude list")
    xp.add_argument("--add-file",      nargs="+", metavar="NAME", help="Exclude file name(s)")
    xp.add_argument("--add-ext",       nargs="+", metavar="EXT",  help="Exclude extension(s)")
    xp.add_argument("--add-folder",    nargs="+", metavar="NAME", help="Exclude folder name(s)")
    xp.add_argument("--remove-file",   nargs="+", metavar="NAME", help="Un-exclude file name(s)")
    xp.add_argument("--remove-ext",    nargs="+", metavar="EXT",  help="Un-exclude extension(s)")
    xp.add_argument("--remove-folder", nargs="+", metavar="NAME", help="Un-exclude folder name(s)")
    xp.set_defaults(func=cmd_config)

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()
    args.func(args)
