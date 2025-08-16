# The following script scans recursively all .md files for their keywords[] on bookworm.
# This script generates a contents.md file that lists all markdown files. When following symlinks to the parent dir it avoids loops.
# It uses an array called 'keywords:[love, hate, ennui]', that is hidden for github markdown inside html comments <!--XX-->.
import os
import re
from collections import defaultdict

def find_markdown_files(root='.'):
    """Recursively find all .md files under root."""
    md_files = []
    seen_dirs = set()  # Track visited directories by inode to avoid cycles

    # Enable following symlinked directories
    for dirpath, _, filenames in os.walk(root, followlinks=True):
        # Avoid revisiting the same directory via different symlinks
        try:
            stat_info = os.stat(dirpath)
        except FileNotFoundError:
            continue
        if stat_info.st_ino in seen_dirs:
            continue
        seen_dirs.add(stat_info.st_ino)

        for fname in filenames:
            if fname.lower().endswith('.md') and fname != 'contents.md':
                md_files.append(os.path.relpath(os.path.join(dirpath, fname), root))
    return md_files

def extract_keywords(filepath):
    """Extract keywords from <!-- keywords[word, ...] --> comments in a file."""
    keywords = set()
    pattern = re.compile(r'<!--\s*keywords*\[([^\]]*)\]\s*-->')
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                # Split by comma and strip whitespace
                words = [word.strip() for word in match.group(1).split(',')]
                keywords.update(filter(None, words))
    return keywords

def build_keyword_map(md_files):
    """Map each keyword to the set of files that contain it."""
    keyword_map = defaultdict(set)
    for filepath in md_files:
        kws = extract_keywords(filepath)
        for kw in kws:
            keyword_map[kw].add(filepath)
    return keyword_map

def write_contents_md(keyword_map, outfile='station3/contents.md'):
    """Write out the contents.md file."""
    with open(outfile, "w", encoding="utf-8") as f:
        # f.write("## Verzeichnis\n\n")
        for kw in sorted(keyword_map):
            files = sorted(keyword_map[kw])
            links = ', '.join(f'[{os.path.basename(fp)}]({fp})' for fp in files)
            f.write(f"- **{kw}**: {links}\n")

if __name__ == "__main__":
    root = '.'   # change to your docs directory if needed
    md_files = find_markdown_files(root)
    keyword_map = build_keyword_map(md_files)
    write_contents_md(keyword_map)
    print("contents.md generated.")