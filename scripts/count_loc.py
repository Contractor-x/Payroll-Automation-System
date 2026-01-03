#!/usr/bin/env python3
"""
Simple Lines-of-Code counter.

Usage:
  python3 scripts/count_loc.py [path]
  python3 scripts/count_loc.py -h
"""

import argparse
import os
from collections import defaultdict

DEFAULT_IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv", "env", "build", "dist"
}

EXT_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".kt": "Kotlin",
}

def is_ignored_dir(dirname, extra_ignored):
    return dirname in DEFAULT_IGNORED_DIRS or dirname in extra_ignored

def count_file_lines(path):
    try:
        with open(path, "rb") as f:
            data = f.read().splitlines()
    except Exception:
        return 0, 0
    total = len(data)
    non_empty = sum(1 for b in data if b.strip())
    return total, non_empty

def walk_and_count(root, include_exts, exclude_exts, extra_ignored):
    per_lang = defaultdict(lambda: {"files": 0, "lines": 0, "non_empty": 0})
    total_files = total_lines = total_non_empty = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # filter ignored dirs in-place to avoid descending into them
        dirnames[:] = [d for d in dirnames if not is_ignored_dir(d, extra_ignored)]
        for fn in filenames:
            _, ext = os.path.splitext(fn.lower())
            if include_exts and ext not in include_exts:
                continue
            if ext in exclude_exts:
                continue
            full = os.path.join(dirpath, fn)
            t, ne = count_file_lines(full)
            lang = EXT_LANG.get(ext, ext or "no_ext")
            per_lang[lang]["files"] += 1
            per_lang[lang]["lines"] += t
            per_lang[lang]["non_empty"] += ne
            total_files += 1
            total_lines += t
            total_non_empty += ne

    return per_lang, total_files, total_lines, total_non_empty

def parse_args():
    p = argparse.ArgumentParser(description="Count lines of code in a project")
    p.add_argument("path", nargs="?", default=".", help="Project path (default: current dir)")
    p.add_argument("--include", "-i", nargs="*", default=[], help="Extensions to include (e.g. .py .js)")
    p.add_argument("--exclude", "-e", nargs="*", default=[], help="Extensions to exclude")
    p.add_argument("--ignore-dir", "-g", nargs="*", default=[], help="Additional directory names to ignore")
    p.add_argument("--show-files", action="store_true", help="Also list files counted (can be large)")
    return p.parse_args()

def main():
    args = parse_args()
    root = os.path.abspath(args.path)
    include = set(x.lower() if x.startswith(".") else f".{x.lower()}" for x in args.include) if args.include else set()
    exclude = set(x.lower() if x.startswith(".") else f".{x.lower()}" for x in args.exclude)

    per_lang, total_files, total_lines, total_non_empty = walk_and_count(root, include, exclude, set(args.ignore_dir))

    print(f"Scanned: {root}")
    print(f"Files: {total_files}   Total lines: {total_lines}   Non-empty lines: {total_non_empty}\n")
    print(f"{'Language':20} {'Files':>7} {'Lines':>12} {'Non-empty':>12}")
    print("-" * 55)
    for lang, stats in sorted(per_lang.items(), key=lambda x: x[0].lower()):
        print(f"{lang:20} {stats['files']:7d} {stats['lines']:12d} {stats['non_empty']:12d}")

if __name__ == "__main__":
    main()