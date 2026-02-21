from __future__ import annotations
from pathlib import Path
import re
from typing import Iterable

_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = _slug_re.sub("-", s).strip("-")
    return s or "doc"

def iter_markdown_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".mdx"}:
            yield p
