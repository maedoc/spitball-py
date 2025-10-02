#!/usr/bin/env python3
from asyncio.events import Handle
import sys
import os
import glob
import subprocess
from pathlib import Path
import argparse
from typing import List, Set
import tempfile


def log_file_status(included_files: List[str], excluded_files: List[tuple]):
    """Log which files were included and excluded"""
    for f in included_files:
        print(f"+ {f}")
    for f, reason in excluded_files:
        print(f"- {f} ({reason})")


def load_gitignore_patterns():
    """Load .gitignore patterns from current directory"""
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        return []

    with open(gitignore_path, "r") as f:
        patterns = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
    return patterns


def is_git_path(path):
    """Check if path is within .git directory"""
    return ".git" in Path(path).parts


def is_binary_or_large(filepath, max_size=100 * 1024):
    """Check if file is binary or exceeds size limit"""
    if os.path.getsize(filepath) > max_size:
        return True

    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
            # Check for non-text characters
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
            return bool(chunk.translate(None, text_chars))
    except Exception:
        return True  # Treat unreadable files as binary


def open_file_with_default_viewer(filepath):
    """
    Opens a file with its default OS viewer in a cross-platform way.
    """
    if sys.platform == "win32":
        os.startfile(filepath)
    elif sys.platform == "darwin":
        subprocess.call(["open", filepath])
    else:
        subprocess.call(["xdg-open", filepath])


def handle_output(md_content, output_file=None, open_file=False, enable_logging=True):
    # Handle file output
    if output_file is not None:
        if output_file == "":
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                tmp.write(md_content.encode("utf-8"))
                output_path = tmp.name
        else:
            # Use specified file path, ensure .txt extension
            if not output_file.endswith(".txt"):
                output_file += ".txt"
            output_path = output_file
            # Create directories if needed
            os.makedirs(
                os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
                exist_ok=True,
            )

        # Write content to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        if enable_logging:
            print(f"Markdown output saved to: {output_path}")

        # Open file if requested
        if open_file:
            open_file_with_default_viewer(output_path)
    else:
        # Original clipboard behavior
        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True
            )
            process.communicate(input=md_content)
            if process.returncode == 0:
                if enable_logging:
                    print("Markdown output copied to clipboard.")
            else:
                print("Failed to copy to clipboard.")
        except FileNotFoundError:
            print("xclip not found. Install it with: sudo apt install xclip")

def parse_tree_clipboard():
    """Return list of (depth, name, is_dir) parsed from clipboard tree."""
    try:
        raw = subprocess.check_output(["xclip", "-o"], text=True)
    except FileNotFoundError:
        sys.exit("xclip not found. Install with: sudo apt install xclip")
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    entries = []
    for ln in lines:
        # count leading tree chars (4 per level)
        prefix_len = 0
        for ch in ln:
            if ch in "├──│└":
                prefix_len += 1
            else:
                break
        depth = prefix_len // 4
        name = ln[prefix_len:].strip()
        if not name:
            continue
        is_dir = "." not in name  # crude: dirs have no extension
        entries.append((depth, name, is_dir))
    return entries


def create_tree_from_clipboard(dry_run=False, edit=False):
    """Create folder/file structure from clipboard tree."""
    entries = parse_tree_clipboard()
    # stack to track current directory path
    stack = []
    created_files = []
    for depth, name, is_dir in entries:
        # pop stack until correct depth
        while len(stack) > depth:
            stack.pop()
        if is_dir:
            path = os.path.join(*stack, name)
            if dry_run:
                print("mkdir", path)
            else:
                os.makedirs(path, exist_ok=True)
            stack.append(name)
        else:
            path = os.path.join(*stack, name)
            if dry_run:
                print("touch", path)
            else:
                Path(path).touch()
            created_files.append(path)
    if edit and not dry_run:
        editor = os.environ.get("EDITOR", "vi")
        for f in created_files:
            subprocess.call([editor, f])
    return created_files


def main(patterns, enable_logging=True, output_file=None, open_file=False):
    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns()

    # Get all files matching glob
    files = []
    for pattern in patterns:
        fs = glob.glob(pattern, recursive=True)
        files.extend([f for f in fs if os.path.isfile(f)])
    files = sorted(set(files))

    # Track excluded files
    excluded_files = []

    # Always filter .git paths
    filtered_files = []
    for f in files:
        if is_git_path(f):
            if enable_logging:
                excluded_files.append((f, "git path"))
        else:
            filtered_files.append(f)
    files = filtered_files

    # Filter binary/large files
    filtered_files = []
    for f in files:
        if is_binary_or_large(f):
            if enable_logging:
                excluded_files.append((f, "binary/large"))
        else:
            filtered_files.append(f)
    files = filtered_files

    # Filter with gitignore if patterns exist
    if gitignore_patterns:
        try:
            import pathspec

            spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_patterns)
            filtered_files = []
            for f in files:
                if spec.match_file(f):
                    if enable_logging:
                        excluded_files.append((f, "gitignore"))
                else:
                    filtered_files.append(f)
            files = filtered_files
        except ImportError:
            print(
                "Warning: pathspec module not found. Install with: pip install pathspec"
            )
            print("Skipping .gitignore filtering.")

    files.sort()

    if enable_logging:
        log_file_status(files, excluded_files)

    md_lines = []
    for file_path in files:
        rel_path = os.path.relpath(file_path)
        header_level = rel_path.count(os.sep) + 1
        header_mark = "#" * header_level
        md_lines.append(f"{header_mark} {rel_path}\n")
        try:
            with open(file_path, "r") as f:
                content = f.read()
            md_lines.append(f"```\n{content}\n```\n")
        except Exception as e:
            md_lines.append(f"```\nError reading file: {e}\n```\n")

    md_content = "\n".join(md_lines)

    handle_output(
        md_content,
        output_file=output_file,
        open_file=open_file,
        enable_logging=enable_logging,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aggregate files into structured Markdown"
    )
    parser.add_argument("pattern", nargs="*", default=["./*"],
                        help="Glob pattern to match files")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress file logging"
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="?",
        const="",
        help="Save output to file (temp file if no path provided)",
    )
    parser.add_argument(
        "-t", "--tree", action="store_true",
        help="Parse clipboard as tree and create folder/file structure"
    )
    parser.add_argument(
        "-e", "--edit", action="store_true",
        help="Open each created file in $EDITOR (only with --tree)"
    )
    parser.add_argument(
        "-o",
        "--open",
        action="store_true",
        help="Open the output file with default viewer",
    )

    args = parser.parse_args()
    if args.tree:
        create_tree_from_clipboard(dry_run=False, edit=args.edit)
    else:
        main(args.pattern, not args.quiet, args.file, args.open)
