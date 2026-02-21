from __future__ import annotations
from typing import Any
import yaml
from mdpub.parser.models import StructuredDocument

def emit_standard_markdown(doc: StructuredDocument) -> str:
    fm = dict(doc.frontmatter.raw)
    fm.setdefault("slug", doc.slug)
    fm.setdefault("doc_id", doc.doc_id)
    fm.setdefault("content_hash", doc.content_hash)
    fm.setdefault("tags", doc.tags)

    fm_text = yaml.safe_dump(fm, sort_keys=False).strip()
    body = "\n".join([b.text for b in doc.blocks]).strip() + "\n"
    return f"---\n{fm_text}\n---\n\n{body}"

def emit_metadata_json(doc: StructuredDocument) -> dict[str, Any]:
    return {
        "doc_id": doc.doc_id,
        "slug": doc.slug,
        "source_path": doc.source_path,
        "content_hash": doc.content_hash,
        "created_at": doc.created_at.isoformat() + "Z",
        "updated_at": doc.updated_at.isoformat() + "Z",
        "frontmatter": doc.frontmatter.raw,
        "tags": doc.tags,
        "metrics": doc.metrics,
        "blocks": [b.model_dump() for b in doc.blocks],
    }
