#!/usr/bin/env python3
import sys
import os
import glob
import subprocess
from pathlib import Path

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

def main(pattern):
    # Load gitignore patterns
    gitignore_patterns = load_gitignore_patterns()

    # Get all files matching glob
    files = glob.glob(pattern, recursive=True)
    files = [f for f in files if os.path.isfile(f)]

    # Always filter .git paths
    files = [f for f in files if not is_git_path(f)]

    # Filter binary/large files
    files = [f for f in files if not is_binary_or_large(f)]

    # Filter with gitignore if patterns exist
    if gitignore_patterns:
        try:
            import pathspec
            spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_patterns)
            files = [f for f in files if not spec.match_file(f)]
        except ImportError:
            print("Warning: pathspec module not found. Install with: pip install pathspec")
            print("Skipping .gitignore filtering.")

    files.sort()

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
            print("Markdown output copied to clipboard.")
        else:
            print("Failed to copy to clipboard.")
    except FileNotFoundError:
        print("xclip not found. Install it with: sudo apt install xclip")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: spitball.py '<glob_pattern>'")
        sys.exit(1)
    main(sys.argv[1])
