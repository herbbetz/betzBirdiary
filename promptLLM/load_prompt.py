#!/usr/bin/env python3
"""
load_prompt.py – Load an MD prompt template and insert code/context.

Usage:
    python load_prompt.py <template.md> <task> <output_format> <code_file>
"""

import sys
from pathlib import Path

def main():
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Arguments received: {sys.argv}", file=sys.stderr)

    if len(sys.argv) != 5:
        print(f"ERROR: Expected 4 arguments, got {len(sys.argv) - 1}", file=sys.stderr)
        print("Usage: python load_prompt.py <template.md> <task> <output_format> <code_file>", file=sys.stderr)
        return 1

    template_path = sys.argv[1]
    task = sys.argv[2]
    output_fmt = sys.argv[3]
    code_path = sys.argv[4]

    print(f"Template path: {template_path}", file=sys.stderr)
    print(f"Task: {task}", file=sys.stderr)
    print(f"Output format: {output_fmt}", file=sys.stderr)
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
        output_format=output_fmt,
        code_snippet=code
    )

    print("=== FINAL PROMPT ===", file=sys.stderr)
    print(prompt)  # This goes to stdout
    print("=== END PROMPT ===", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
