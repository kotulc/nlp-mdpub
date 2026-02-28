"""Pipeline step functions: extract, commit, and export orchestration"""

from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from mdpub.core.export import write_doc
from mdpub.core.extract.extract import extract_doc
from mdpub.core.models import StagedBlock, StagedDoc
from mdpub.core.extract.parse import discover_files, parse_file
from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import commit_doc
from mdpub.crud.models import SectionBlockEnum


def _heading_level(content: str) -> int | None:
    """Derive heading level (1-6) from content string (e.g. '## Title' → 2), else None."""
    stripped = content.lstrip()
    count = len(stripped) - len(stripped.lstrip('#'))
    return count if 1 <= count <= 6 else None


def _process(staged: StagedDoc, max_nesting: int) -> dict:
    """Group flat blocks into sections and compute all hashes, positions, and levels."""
    sections = []
    current: list[StagedBlock] = []

    def _flush(blocks: list[StagedBlock], position: int) -> dict:
        hashed_blocks = [
            {"content": b.content, "hash": sha256(b.content),
             "type": b.type, "position": float(i), "level": _heading_level(b.content)}
            for i, b in enumerate(blocks)
        ]
        # Aggregate tags (deduplicated, insertion order) and metrics (last-wins) from all blocks.
        tags = list(dict.fromkeys(t for b in blocks for t in b.tags))
        metrics: dict[str, float] = {}
        for b in blocks:
            metrics.update(b.metrics)
        return {
            "hash": sha256("".join(b["content"] for b in hashed_blocks)),
            "position": position,
            "blocks": hashed_blocks,
            "tags": tags,
            "metrics": metrics,
        }

    for block in staged.content:
        level = _heading_level(block.content)
        if block.type == SectionBlockEnum.heading and level and level <= max_nesting:
            if current:
                sections.append(_flush(current, len(sections)))
                current = []
        current.append(block)
    if current:
        sections.append(_flush(current, len(sections)))

    return {
        "slug": staged.slug,
        "path": staged.path,
        "markdown": staged.markdown,
        "hash": sha256(staged.markdown),
        "frontmatter": staged.frontmatter,
        "sections": sections,
    }


def run_extract(
    path: str,
    parser_config: str,
    staging_dir: Path,
    ) -> list[tuple[str, Path]]:
    """Parse path and write StagedDoc JSON to staging_dir. Returns (source_path, staging_file) pairs."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for p in discover_files(Path(path)):
        try:
            parsed = parse_file(p, parser_config)
            staged = extract_doc(parsed)
            out_file = staging_dir / f"{staged.slug}.json"
            out_file.write_text(staged.model_dump_json(indent=2))
            results.append((p, out_file))
        except Exception as e:
            raise RuntimeError(f"Failed to extract {p}: {e}") from e
    return results


def run_commit(
    engine,
    max_versions: int,
    max_nesting: int,
    staging_dir: Path,
    ) -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Read staged StagedDoc JSON, process, and commit to database.

    Returns (counts, changes) where changes is a list of (status, slug) for
    created/updated docs. Returns ({}, []) when staging_dir is empty.
    """
    files = sorted(staging_dir.glob('*.json')) if staging_dir.exists() else []
    if not files:
        return {}, []

    committed_at = datetime.now()
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    changes = []
    with Session(engine) as session:
        for f in files:
            staged = StagedDoc.model_validate_json(f.read_text())
            data = _process(staged, max_nesting)
            doc, status = commit_doc(session, data, max_versions, committed_at)
            counts[status] += 1
            if status != 'unchanged':
                changes.append((status, doc.slug))
        session.commit()
    return counts, changes


def run_export(
    session: Session,
    docs: list,
    output_dir: Path,
    fmt: str,
    ) -> list[tuple[str, Path]]:
    """Write docs to output_dir using an open session. Returns (slug, mdx_path) pairs."""
    results = []
    for doc in docs:
        mdx_path, _ = write_doc(doc, session, output_dir, fmt)
        results.append((doc.slug, mdx_path))
    return results
