#!/usr/bin/env python3
import sys
import os
import glob
import subprocess
from pathlib import Path
import argparse
from typing import List, Set


def log_file_status(included_files: List[str], excluded_files: List[tuple]):
    """Log which files were included and excluded"""
    for f in included_files:
        print(f"+ {f}")
    for f, reason in excluded_files:
        print(f"- {f} ({reason})")

def load_gitignore_patterns():
    """Load .gitignore patterns from current directory"""
    gitignore_path = '.gitignore'
    if not os.path.exists(gitignore_path):
        return []

    with open(gitignore_path, 'r') as f:
        patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return patterns

def is_git_path(path):
    """Check if path is within .git directory"""
    return '.git' in Path(path).parts

def is_binary_or_large(filepath, max_size=100*1024):
    """Check if file is binary or exceeds size limit"""
    if os.path.getsize(filepath) > max_size:
        return True

    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return True
            # Check for non-text characters
            text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))
            return bool(chunk.translate(None, text_chars))
    except Exception:
        return True  # Treat unreadable files as binary


def main(pattern, enable_logging=True):
    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns()

    # Get all files matching glob
    files = glob.glob(pattern, recursive=True)
    files = [f for f in files if os.path.isfile(f)]

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
            spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_patterns)
            filtered_files = []
            for f in files:
                if spec.match_file(f):
                    if enable_logging:
                        excluded_files.append((f, "gitignore"))
                else:
                    filtered_files.append(f)
            files = filtered_files
        except ImportError:
            print("Warning: pathspec module not found. Install with: pip install pathspec")
            print("Skipping .gitignore filtering.")

    files.sort()

    if enable_logging:
        log_file_status(files, excluded_files)

    md_lines = []
    for file_path in files:
        rel_path = os.path.relpath(file_path)
        header_level = rel_path.count(os.sep) + 1
        header_mark = '#' * header_level
        md_lines.append(f"{header_mark} {rel_path}\n")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            md_lines.append(f"```\n{content}\n```\n")
        except Exception as e:
            md_lines.append(f"```\nError reading file: {e}\n```\n")

    md_content = '\n'.join(md_lines)

    try:
        process = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                                   stdin=subprocess.PIPE,
                                   text=True)
        process.communicate(input=md_content)
        if process.returncode == 0:
            if enable_logging:
                print("Markdown output copied to clipboard.")
        else:
            print("Failed to copy to clipboard.")
    except FileNotFoundError:
        print("xclip not found. Install it with: sudo apt install xclip")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate files into structured Markdown")
    parser.add_argument('pattern', help='Glob pattern to match files')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress file logging')

    args = parser.parse_args()
    main(args.pattern, not args.quiet)
