from __future__ import annotations
from dataclasses import dataclass
import yaml

@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict
    body: str

def parse_frontmatter(markdown_text: str) -> ParsedMarkdown:
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ParsedMarkdown(frontmatter={}, body=markdown_text)

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return ParsedMarkdown(frontmatter={}, body=markdown_text)

    fm_text = "\n".join(lines[1:end_idx]).strip()
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    fm = yaml.safe_load(fm_text) if fm_text else {}
    if fm is None or not isinstance(fm, dict):
        fm = {}
    return ParsedMarkdown(frontmatter=fm, body=body)
