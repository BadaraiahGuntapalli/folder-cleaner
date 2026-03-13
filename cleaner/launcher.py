"""
Interactive right-click launcher for the Folder Cleaner.
Triggered via context menu: python launcher.py "C:/path/to/folder"
"""

import sys
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()
SCRIPT  = Path(__file__).parent / "cleaner.py"   # cleaner/cleaner.py


def run(folder: str, *extra_args: str) -> None:
    subprocess.run([sys.executable, str(SCRIPT), "--folder", folder, *extra_args], check=False)


# ── Input helpers ─────────────────────────────────────────────────────────────

def ask_types() -> str | None:
    v = Prompt.ask(
        "\n  [cyan]File extensions[/cyan] (e.g. [dim]jpg,png,zip[/dim]) or [bold]all[/bold] "
        "or [dim]Enter to skip[/dim]",
        default="",
    ).strip()
    return v or None


def ask_folders() -> str | None:
    v = Prompt.ask(
        "  [yellow]Folder names[/yellow] (e.g. [dim]temp,old[/dim]) or [bold]all[/bold] "
        "or [dim]Enter to skip[/dim]",
        default="",
    ).strip()
    return v or None


def ask_older_than() -> str | None:
    v = Prompt.ask(
        "  [dim]Only files older than N days?[/dim] (e.g. [dim]30[/dim]) "
        "or [dim]Enter to skip[/dim]",
        default="",
    ).strip()
    return v or None


def ask_larger_than() -> str | None:
    v = Prompt.ask(
        "  [dim]Only files larger than SIZE?[/dim] (e.g. [dim]10MB, 500KB[/dim]) "
        "or [dim]Enter to skip[/dim]",
        default="",
    ).strip()
    return v or None


def ask_recursive() -> bool:
    return Confirm.ask("  Scan sub-folders recursively?", default=False)


def ask_verbose() -> bool:
    return Confirm.ask("  Show verbose file list?", default=True)


def pause() -> None:
    Prompt.ask("\n[dim]Press Enter to return to menu[/dim]", default="")


# ── Menu pages ────────────────────────────────────────────────────────────────

def menu_scan(folder: str) -> None:
    recursive = ask_recursive()
    console.print()
    run(folder, "scan", *(["--recursive"] if recursive else []))


def menu_clean(folder: str, dry_run: bool) -> None:
    types   = ask_types()
    folders = ask_folders()
    if not types and not folders:
        console.print("[yellow]Nothing selected — returning to menu.[/yellow]")
        return

    older   = ask_older_than()
    larger  = ask_larger_than()
    recurse = ask_recursive()
    verbose = ask_verbose()

    if not dry_run:
        console.print("\n[bold red]Warning:[/bold red] Files will be sent to the Recycle Bin.")
        if not Confirm.ask("  Proceed?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    args = ["clean"]
    if types:    args += ["-t", types]
    if folders:  args += ["-f", folders]
    if dry_run:  args.append("--dry-run")
    if older:    args += ["--older-than", older]
    if larger:   args += ["--larger-than", larger]
    if recurse:  args.append("--recursive")
    if verbose:  args.append("-v")

    console.print()
    run(folder, *args)


def menu_dupes(folder: str) -> None:
    recurse = ask_recursive()
    verbose = ask_verbose()

    console.print()
    run(folder, "dupes", "--dry-run",
        *(["--recursive"] if recurse else []),
        *(["--verbose"]   if verbose else []))
    console.print()

    if Confirm.ask("  Proceed with deletion?", default=False):
        args = ["dupes"]
        if recurse: args.append("--recursive")
        if verbose: args.append("-v")
        console.print()
        run(folder, *args)
    else:
        console.print("[yellow]Cancelled — dry run only.[/yellow]")


def menu_config(folder: str) -> None:
    while True:
        console.clear()
        console.print(
            Panel(
                "  [bold cyan]1.[/bold cyan]  Show exclude list\n"
                "  [bold cyan]2.[/bold cyan]  Add file / extension / folder to exclude list\n"
                "  [bold cyan]3.[/bold cyan]  Remove from exclude list\n"
                "  [bold red]4.[/bold red]  Back",
                title="[bold]Config — Exclude List[/bold]",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        choice = Prompt.ask("  Choose", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            console.print()
            run(folder, "config", "--show")

        elif choice == "2":
            kind = Prompt.ask(
                "  Add [cyan]file[/cyan] name, [cyan]ext[/cyan]ension, or [cyan]folder[/cyan]",
                choices=["file", "ext", "folder"], default="ext",
            )
            val = Prompt.ask(f"  Enter {kind} name").strip()
            if val:
                flag = {"file": "--add-file", "ext": "--add-ext", "folder": "--add-folder"}[kind]
                run(folder, "config", flag, val)

        elif choice == "3":
            kind = Prompt.ask(
                "  Remove [cyan]file[/cyan] name, [cyan]ext[/cyan]ension, or [cyan]folder[/cyan]",
                choices=["file", "ext", "folder"], default="ext",
            )
            val = Prompt.ask(f"  Enter {kind} name to remove").strip()
            if val:
                flag = {"file": "--remove-file", "ext": "--remove-ext", "folder": "--remove-folder"}[kind]
                run(folder, "config", flag, val)

        elif choice == "4":
            break

        if choice != "4":
            pause()


# ── Main menu ─────────────────────────────────────────────────────────────────

def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Downloads")

    while True:
        console.clear()
        console.print(
            Panel(
                f"[bold]Folder:[/bold] [green]{folder}[/green]\n\n"
                "  [bold cyan]1.[/bold cyan]  Scan             [dim]— show all file types & folders[/dim]\n"
                "  [bold cyan]2.[/bold cyan]  Dry Run          [dim]— preview what would be deleted[/dim]\n"
                "  [bold cyan]3.[/bold cyan]  Delete           [dim]— send selected items to Recycle Bin[/dim]\n"
                "  [bold cyan]4.[/bold cyan]  Find Duplicates  [dim]— detect & remove duplicate files[/dim]\n"
                "  [bold cyan]5.[/bold cyan]  Config           [dim]— manage exclude list[/dim]\n"
                "  [bold red]6.[/bold red]  Exit",
                title="[bold]Folder Cleaner[/bold]",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        choice = Prompt.ask("  Choose", choices=["1", "2", "3", "4", "5", "6"], default="1")

        if   choice == "1": menu_scan(folder)
        elif choice == "2": menu_clean(folder, dry_run=True)
        elif choice == "3": menu_clean(folder, dry_run=False)
        elif choice == "4": menu_dupes(folder)
        elif choice == "5": menu_config(folder)
        elif choice == "6":
            console.print("\n[dim]Bye![/dim]\n")
            break

        if choice != "6":
            pause()


if __name__ == "__main__":
    main()
