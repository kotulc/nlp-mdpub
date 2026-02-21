from __future__ import annotations
import difflib

def unified_diff(old_text: str, new_text: str, fromfile: str, tofile: str) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile))
