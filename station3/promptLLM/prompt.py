#!/usr/bin/env python3
"""
load_prompt.py – Load an MD prompt template, insert code, and write to prompt.md with UTF-8 encoding.

Usage:
    python load_prompt.py <template.md> <task> <code_file>

Output:
    Writes the final prompt to 'prompt.md' in UTF-8 encoding (no BOM)
"""

import sys
from pathlib import Path

OUTPUT_FILE = Path("prompt.md") # redirection like ' > prompt.md' is not used to avoid UTF8 BOM issues

def main():
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Arguments received: {sys.argv}", file=sys.stderr)
    
    if len(sys.argv) != 4:
        print(f"ERROR: Expected 3 arguments, got {len(sys.argv) - 1}", file=sys.stderr)
        print("Usage: python load_prompt.py <template.md> <task> <code_file>", file=sys.stderr)
        return 1
    
    template_path = sys.argv[1]
    task = sys.argv[2]
    code_path = sys.argv[3]
    
    print(f"Template path: {template_path}", file=sys.stderr)
    print(f"Task: {task}", file=sys.stderr)
    print(f"Code path: {code_path}", file=sys.stderr)
    
    try:
        template = Path(template_path).read_text(encoding="utf-8")
        print(f"Template loaded, length: {len(template)} chars", file=sys.stderr)
    except Exception as e:
        print(f"ERROR loading template: {e}", file=sys.stderr)
        return 1
    
    try:
        code = Path(code_path).read_text(encoding="utf-8")
        print(f"Code loaded, length: {len(code)} chars", file=sys.stderr)
    except Exception as e:
        print(f"ERROR loading code: {e}", file=sys.stderr)
        return 1
    
    prompt = template.format(
        task_description=task,
        code_snippet=code
    )
    
    print("=== FINAL PROMPT ===", file=sys.stderr)
    
    # Write to file with UTF-8 encoding (no BOM)
    try:
        OUTPUT_FILE.write_text(prompt, encoding="utf-8")
        print(f"Prompt written to '{OUTPUT_FILE}' ({len(prompt)} chars)", file=sys.stderr)
    except Exception as e:
        print(f"ERROR writing to file: {e}", file=sys.stderr)
        return 1
    
    print("=== END PROMPT ===", file=sys.stderr)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())