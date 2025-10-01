# spitball.py

A command-line utility that aggregates files matching a glob pattern into a
structured Markdown document, respecting `.gitignore` rules and filtering out
binary or large files.

## Features

- Recursive glob matching with `**` support
- Automatically excludes:
  - Files matching `.gitignore` patterns (if `pathspec` installed)
  - Files within `.git` directories
  - Binary files (detected heuristically)
  - Files larger than 100KB
- Generates hierarchical Markdown with headers based on directory structure
- Copies output directly to clipboard (requires `xclip`)

## Installation

```bash
sudo apt install xclip
pip install pathspec
chmod +x spitball.py
sudo ln -s $PWD/spitball.py /usr/local/bin/spitball.py
```

## Usage

```bash
spitball.py '<glob_pattern>'
```

Examples:
```bash
# All Python files recursively
spitball.py '**/*.py'

# All files in src directory
spitball.py 'src/**/*'

# Specific file types
spitball.py '**/*.{md,txt}'
```

## Output Format

The generated Markdown follows this structure:
- Headers represent directory hierarchy depth
- File contents are included in code blocks
- Files are sorted alphabetically within each directory

## Requirements

- Python 3.6+
- `xclip` for clipboard integration
- `pathspec` (optional but recommended for .gitignore support)

## Roadmap

- [ ] Log files included / excluded
- [ ] Configurable size limits
- [ ] Prioritize README files
- [ ] Customizable header prefixes
- [ ] Configurable output (stdout, /tmp/file, etc)

