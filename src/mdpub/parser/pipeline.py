from __future__ import annotations
from pathlib import Path
from datetime import datetime

from mdpub.parser.models import StructuredDocument, Frontmatter, Block
from mdpub.parser.parse import parse_frontmatter
from mdpub.util.hashing import sha256_text
from mdpub.util.fs import slugify

def ingest_markdown_text(source_path: str, raw: str) -> StructuredDocument:
    parsed = parse_frontmatter(raw)
    content_hash = sha256_text(raw)

    blocks: list[Block] = []
    for line in parsed.body.splitlines():
        if line.startswith("#"):
            blocks.append(Block(kind="heading", text=line.strip()))
        elif line.strip():
            blocks.append(Block(kind="paragraph", text=line.strip()))

    slug = slugify(parsed.frontmatter.get("slug") or Path(source_path).stem)
    now = datetime.utcnow()

    return StructuredDocument(
        doc_id=content_hash[:16],
        source_path=source_path,
        slug=slug,
        created_at=now,
        updated_at=now,
        frontmatter=Frontmatter(raw=parsed.frontmatter),
        blocks=blocks,
        content_hash=content_hash,
        tags=list(parsed.frontmatter.get("tags", []) or []),
        metrics={},
    )

def ingest_markdown_file(path: Path) -> StructuredDocument:
    raw = path.read_text(encoding="utf-8")
    return ingest_markdown_text(str(path), raw)
