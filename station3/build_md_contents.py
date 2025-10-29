#!/usr/bin/env python3
# build-md-contents.py
# Iterative version: scans .md files under station3 and its 'parentdir' symlink (if present),
# extracts keywords from HTML comments <!-- keywords[...] -->,
# generates contents.md, prevents loops (station3 inside parentdir is skipped),
# does not follow symlinks inside parentdir, skips negative-list dirs.

import os
import re
from collections import defaultdict
import sys

# ----------------------------
# Configuration
# ----------------------------
CONTENTS_MD = "contents.md"  # default output file name
KEYWORDS_RE = re.compile(r'<!--\s*keywords?\[([^\]]*)\]\s*-->')

# ----------------------------
# Helper Functions
# ----------------------------

def check_running_dir():
    """Ensure script is run from its own directory."""
    script_dir = os.path.abspath(os.path.dirname(__file__))
    cwd = os.path.abspath(os.getcwd())
    if cwd != script_dir:
        print(f"Error: Run this script only from inside its own directory:\n  cd {script_dir} && python {os.path.basename(__file__)}")
        sys.exit(1)
    return script_dir

def find_parentdir_symlink(script_dir):
    """Return path to 'parentdir' symlink if exists, else None and warn."""
    symlink_path = os.path.join(script_dir, "parentdir")
    if not os.path.islink(symlink_path):
        print("Warning: No symlink 'parentdir' found; only local .md files will be processed.")
        return None
    return symlink_path

def find_markdown_files(root, parentdir_symlink, contents_md_file):
    """
    Iteratively find all .md files.
    - Returns list of tuples: (relative_path, via_parentdir)
    - Follow parentdir_symlink exactly once.
    - Inside parentdir, do not follow further symlinks.
    - Skip station3 inside parentdir to prevent recursion loops.
    - Skip any directory listed in negative_dirs.
    """
    md_files = []
    stack = [(os.path.abspath(root), True, False)]  # (dirpath, follow_symlinks, under_parentdir)
    script_realpath = os.path.realpath(root)
    seen_realpaths = set()

    # Negative list: directories to skip entirely
    negative_dirs = []
    # if parentdir_symlink:
        # negative_dirs.append(os.path.join(os.path.realpath(parentdir_symlink), "birdvenv"))

    while stack:
        dirpath, follow_symlinks, under_parentdir = stack.pop()
        dir_real = os.path.realpath(dirpath)

        if dir_real in seen_realpaths:
            continue
        seen_realpaths.add(dir_real)

        # Skip station3 inside parentdir to prevent loops
        if under_parentdir and dir_real == script_realpath:
            continue

        # Skip any directory in negative list
        if any(dir_real == nd for nd in negative_dirs):
            continue

        try:
            entries = list(os.scandir(dirpath))
        except PermissionError:
            continue

        for entry in entries:
            path = entry.path
            if entry.is_file() and entry.name.lower().endswith('.md') and entry.name != contents_md_file:
                md_files.append((os.path.relpath(path, root), under_parentdir))
            elif entry.is_dir(follow_symlinks=follow_symlinks):
                abspath = os.path.abspath(path)
                # If this directory is parentdir, follow it once but don't follow further symlinks inside it
                if parentdir_symlink and os.path.samefile(abspath, parentdir_symlink):
                    stack.append((abspath, False, True))  # mark under_parentdir=True
                else:
                    stack.append((abspath, follow_symlinks, under_parentdir))

    return md_files, negative_dirs

def extract_keywords(filepath):
    """Extract keywords from <!-- keywords[...] --> comments in a file."""
    keywords = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                match = KEYWORDS_RE.search(line)
                if match:
                    words = [w.strip() for w in match.group(1).split(",")]
                    keywords.update(filter(None, words))
    except Exception:
        # Any read errors are silently ignored
        pass
    return keywords

def build_keyword_map(md_files):
    """Map each keyword to the set of files that contain it."""
    keyword_map = defaultdict(set)
    for filepath, _ in md_files:
        kws = extract_keywords(filepath)
        for kw in kws:
            keyword_map[kw].add(filepath)
    return keyword_map

def prettify_label(fp):
    """Make a human-friendly label for a markdown file path."""
    norm = os.path.normpath(fp)
    base = os.path.basename(norm)
    if norm.lower() == "readme.md":
        return "README"
    elif base.lower() == "readme.md":
        return os.path.basename(os.path.dirname(norm)) or "README"
    else:
        return os.path.splitext(base)[0]

def write_contents_md(keyword_map, outfile):
    """Write contents.md with pretty links relative to its own location."""
    outdir = os.path.dirname(os.path.abspath(outfile))
    with open(outfile, "w", encoding="utf-8") as f:
        for kw in sorted(keyword_map):
            files = sorted(keyword_map[kw])
            links = []
            for fp in files:
                rel_link = os.path.relpath(os.path.abspath(fp), outdir)
                # Force forward slashes for GitHub compatibility
                rel_link = rel_link.replace(os.sep, "/")
                links.append(f'[{prettify_label(fp)}]({rel_link})')
            f.write(f"- **{kw}**: {', '.join(links)}\n")

# ----------------------------
# Main Execution
# ----------------------------

if __name__ == "__main__":
    script_dir = check_running_dir()
    parentdir_symlink = find_parentdir_symlink(script_dir)
    md_files, negative_dirs = find_markdown_files(script_dir, parentdir_symlink, CONTENTS_MD)

    # Compute keyword map
    keyword_map = build_keyword_map(md_files)
    write_contents_md(keyword_map, os.path.join(script_dir, CONTENTS_MD))
    print(f"{CONTENTS_MD} generated in {script_dir}")

    # Optional statistics
    station3_count = sum(1 for _, via_parentdir in md_files if not via_parentdir)
    parentdir_count = sum(1 for _, via_parentdir in md_files if via_parentdir)
    print(f"Markdown files counted: station3={station3_count}, parentdir={parentdir_count}")

    # Print all files considered 'via parentdir'
    via_parentdir_files = [fp for fp, via_parentdir in md_files if via_parentdir]
    if parentdir_symlink:
        parentdir_real = os.path.realpath(parentdir_symlink)
        print("Files considered via parentdir (relative to symlink):")
        for fp in via_parentdir_files:
            abs_fp = os.path.abspath(fp)
            try:
                rel_fp = os.path.relpath(abs_fp, parentdir_real)
            except ValueError:
                rel_fp = abs_fp
            # Normalize to forward slashes
            rel_fp = rel_fp.replace(os.sep, "/")
            print(f"  {rel_fp}")
    else:
        print("No parentdir symlink; no files marked via parentdir.")

    # Print negative-list directories skipped
    if negative_dirs:
        print("Directories excluded by negative list:")
        for nd in negative_dirs:
            # Normalize to forward slashes
            print(f"  {nd.replace(os.sep, '/')}")
