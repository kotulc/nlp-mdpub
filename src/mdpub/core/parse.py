"""File discovery, frontmatter extraction, and markdown-it tokenization"""

import re
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt

from mdpub.core.models import ParsedDoc
from mdpub.core.utils.hashing import sha256
from mdpub.core.utils.slug import slugify


FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
MD_EXTENSIONS = {'.md', '.mdx'}


def _make_parser(preset: str) -> MarkdownIt:
    """Build a MarkdownIt instance for the given preset name."""
    return MarkdownIt(preset, options_update={"linkify": False})


def _strip_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body) with YAML header removed."""
    m = FRONTMATTER_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e
        if not isinstance(fm, dict):
            raise ValueError(f"Invalid YAML frontmatter: expected a mapping, got {type(fm).__name__}")
        return fm, text[m.end():]
    return {}, text


def discover_files(path: Path) -> list[Path]:
    """Return sorted .md/.mdx files under path, or [path] if a single file."""
    if path.is_file():
        return [path] if path.suffix in MD_EXTENSIONS else []
    return sorted(p for p in path.rglob('*') if p.suffix in MD_EXTENSIONS)


def parse_file(path: Path, parser_config: str = 'gfm-like') -> ParsedDoc:
    """Parse a single markdown file into a ParsedDoc with token stream."""
    raw = path.read_text(encoding='utf-8')
    frontmatter, body = _strip_frontmatter(raw)
    tokens = _make_parser(parser_config).parse(body)
    slug = frontmatter.get('slug') or slugify(path.stem)
    return ParsedDoc(
        path=path,
        slug=slug,
        raw_markdown=raw,
        markdown=body,
        hash=sha256(raw),
        frontmatter=frontmatter,
        tokens=tokens,
    )


def parse_dir(path: Path, parser_config: str = 'gfm-like') -> list[ParsedDoc]:
    """Parse all .md/.mdx files under path (file or directory)."""
    return [parse_file(p, parser_config) for p in discover_files(path)]
