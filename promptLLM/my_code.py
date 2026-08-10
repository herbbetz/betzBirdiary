#!/usr/bin/env python3
"""
load_prompt.py – Lade eine MD-Prompt-Vorlage und füge Code/Kontext ein.

Verwendung:
    python load_prompt.py refactor.md "Refactor the code" "Only return the refactored code, in a Python code block." my_code.py
"""

import sys
from pathlib import Path

def load_prompt(template_path: str, task: str, output_fmt: str, code_path: str) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    code = Path(code_path).read_text(encoding="utf-8")

    prompt = template.format(
        task_description=task,
        output_format=output_fmt,
        code_snippet=code
    )
    return prompt

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python load_prompt.py <template.md> <task> <output_format> <code_file>")
        sys.exit(1)

    template_path = sys.argv[1]
    task = sys.argv[2]
    output_fmt = sys.argv[3]
    code_path = sys.argv[4]

    prompt = load_prompt(template_path, task, output_fmt, code_path)
    print(prompt)
