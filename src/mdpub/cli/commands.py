"""CLI command implementations"""

import dataclasses
import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from sqlmodel import Session, SQLModel

from mdpub.config import load_config
from mdpub.core.extract.extract import extract_doc
from mdpub.core.parse import parse_dir
from mdpub.crud.database import init_db, make_engine
from mdpub.crud.documents import commit_doc
from mdpub.crud.tables import SectionBlockEnum


def build(
    path: Annotated[str, typer.Argument(help="File or directory to process")],
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory override")] = None,
    ):
    """Run the full pipeline: extract -> commit -> export."""
    raise NotImplementedError("build is not yet implemented")


def init(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    reset: Annotated[bool, typer.Option("--reset", help="Drop and recreate all tables")] = False,
    ):
    """Initialize database schema. Use --reset to clear existing data."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})
    engine = make_engine(settings.db_url)
    if reset:
        SQLModel.metadata.drop_all(engine)
        typer.echo("Existing data cleared.")
    init_db(engine)
    typer.echo(f"Database initialized at: {settings.db_url}")


def extract(
    path: Annotated[str, typer.Argument(help="File or directory to extract from")],
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    ):
    """Recursively extract blocks, frontmatter, and content hash."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})

    def _serial(obj):
        if isinstance(obj, SectionBlockEnum):
            return obj.value
        raise TypeError(type(obj))

    staging = Path('.mdpub/staging')
    staging.mkdir(parents=True, exist_ok=True)

    docs = parse_dir(Path(path), settings.parser_config)
    for parsed in docs:
        extracted = extract_doc(parsed, settings.max_nesting)
        out = staging / f"{extracted.slug}.json"
        out.write_text(json.dumps(dataclasses.asdict(extracted), default=_serial, indent=2))
        typer.echo(f"  {parsed.path} -> {out}")

    typer.echo(f"Extracted {len(docs)} document(s) to {staging}/")


def commit(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    ):
    """Upsert parsed document data to the database."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})
    engine = make_engine(settings.db_url)
    init_db(engine)

    staging = Path('.mdpub/staging')
    files = sorted(staging.glob('*.json')) if staging.exists() else []
    if not files:
        typer.echo("Nothing staged. Run 'mdpub extract <path>' first.")
        raise typer.Exit(1)

    counts = {"created": 0, "updated": 0, "unchanged": 0}
    with Session(engine) as session:
        for f in files:
            data = json.loads(f.read_text())
            doc, status = commit_doc(session, data, settings.max_versions)
            counts[status] += 1
            if status != 'unchanged':
                typer.echo(f"  {status}: {doc.slug}")
        session.commit()

    typer.echo(
        f"Commit complete - "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} unchanged"
    )


def export(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory override")] = None,
    ):
    """Write standardized MD/MDX + sidecar JSON to output dir."""
    raise NotImplementedError("export is not yet implemented")
