"""CLI command implementations"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from sqlmodel import Session, SQLModel

from mdpub.config import load_config
from mdpub.core.pipeline import STAGING, run_commit, run_export, run_extract
from mdpub.crud.database import init_db, make_engine
from mdpub.crud.documents import (
    get_all_documents,
    get_by_collection,
    get_last_committed,
    list_collections,
)


def build_cmd(
    path: Annotated[str, typer.Argument(help="File or directory to process")],
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory override")] = None,
    ):
    """Run the full pipeline: extract -> commit -> export."""
    settings = load_config(config_path=config, overrides={"db_url": db_url, "output_dir": out})
    engine = make_engine(settings.db_url)
    init_db(engine)

    # --- extract ---
    extracted = run_extract(path, settings.parser_config, settings.max_nesting)
    for src, out_file in extracted:
        typer.echo(f"  {src} -> {out_file}")
    typer.echo(f"Extracted {len(extracted)} document(s) to {STAGING}/")

    # --- commit ---
    counts, changes = run_commit(engine, settings.max_versions)
    for status, slug in changes:
        typer.echo(f"  {status}: {slug}")
    typer.echo(
        f"Commit complete - "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} unchanged"
    )

    # --- export ---
    output_dir = Path(settings.output_dir)
    with Session(engine) as session:
        exported = get_last_committed(session)
        results = run_export(session, exported, output_dir, settings.output_format)
    for slug, mdx_path in results:
        typer.echo(f"  {slug} -> {mdx_path}")
    typer.echo(f"Exported {len(results)} document(s) to {output_dir}/")


def list_cmd(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    ):
    """List top-level directories (collections) that contain documents in the database."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})
    engine = make_engine(settings.db_url)
    init_db(engine)
    with Session(engine) as session:
        cols = list_collections(session)
    if not cols:
        typer.echo("No documents found in database.")
        raise typer.Exit(1)
    for c in cols:
        typer.echo(c)


def init_cmd(
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


def extract_cmd(
    path: Annotated[str, typer.Argument(help="File or directory to extract from")],
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    ):
    """Recursively extract blocks, frontmatter, and content hash."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})
    results = run_extract(path, settings.parser_config, settings.max_nesting)
    for src, out_file in results:
        typer.echo(f"  {src} -> {out_file}")
    typer.echo(f"Extracted {len(results)} document(s) to {STAGING}/")


def commit_cmd(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    ):
    """Upsert parsed document data to the database."""
    settings = load_config(config_path=config, overrides={"db_url": db_url})
    engine = make_engine(settings.db_url)
    init_db(engine)

    counts, changes = run_commit(engine, settings.max_versions)
    if not counts:
        typer.echo("Nothing staged. Run 'mdpub extract <path>' first.")
        raise typer.Exit(1)

    for status, slug in changes:
        typer.echo(f"  {status}: {slug}")
    typer.echo(
        f"Commit complete - "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} unchanged"
    )


def export_cmd(
    config: Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")] = None,
    db_url: Annotated[Optional[str], typer.Option("--db-url", help="Database URL override")] = None,
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory override")] = None,
    collection: Annotated[Optional[str], typer.Option("--collection", help="Export docs under this top-level directory")] = None,
    all_docs: Annotated[bool, typer.Option("--all", help="Export all documents in the database")] = False,
    ):
    """Write standardized MD/MDX + sidecar JSON to output dir."""
    settings = load_config(config_path=config, overrides={"db_url": db_url, "output_dir": out})
    engine = make_engine(settings.db_url)
    init_db(engine)
    output_dir = Path(settings.output_dir)

    with Session(engine) as session:
        if all_docs:
            docs = get_all_documents(session)
            scope = "all"
        elif collection:
            docs = get_by_collection(session, collection)
            scope = f"collection '{collection}'"
        else:
            docs = get_last_committed(session)
            scope = "last commit"

        if not docs:
            typer.echo(f"No documents found for scope: {scope}.")
            raise typer.Exit(1)

        results = run_export(session, docs, output_dir, settings.output_format)

    for slug, mdx_path in results:
        typer.echo(f"  {slug} -> {mdx_path}")
    typer.echo(f"Exported {len(results)} document(s) to {output_dir}/")
