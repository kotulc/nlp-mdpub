"""Pipeline step functions: extract, commit, and export orchestration"""

import dataclasses
import json
from datetime import date, datetime
from pathlib import Path

from sqlmodel import Session

from mdpub.core.export import write_doc
from mdpub.core.extract.extract import extract_doc
from mdpub.core.parse import discover_files, parse_file
from mdpub.crud.documents import commit_doc
from mdpub.crud.models import SectionBlockEnum


def run_extract(
    path: str,
    parser_config: str,
    max_nesting: int,
    staging_dir: Path,
    ) -> list[tuple[str, Path]]:
    """Parse path and write extracted JSON to staging_dir. Returns (source_path, staging_file) pairs."""
    def _serial(obj):
        if isinstance(obj, SectionBlockEnum):
            return obj.value
        if isinstance(obj, date):  # catches date and datetime (datetime subclasses date)
            return obj.isoformat()
        raise TypeError(type(obj))

    staging_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for p in discover_files(Path(path)):
        try:
            parsed = parse_file(p, parser_config)
            extracted = extract_doc(parsed, max_nesting)
            out_file = staging_dir / f"{extracted.slug}.json"
            out_file.write_text(json.dumps(dataclasses.asdict(extracted), default=_serial, indent=2))
            results.append((p, out_file))
        except Exception as e:
            raise RuntimeError(f"Failed to extract {p}: {e}") from e
    return results


def run_commit(
    engine,
    max_versions: int,
    staging_dir: Path,
    ) -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Commit staged JSON files to the database.

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
            data = json.loads(f.read_text())
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
