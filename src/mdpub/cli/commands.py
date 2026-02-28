"""CLI command implementations"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from sqlmodel import Session, SQLModel

from mdpub.config import Settings, load_config
from mdpub.core.pipeline import run_commit, run_export, run_extract
from mdpub.crud.database import init_db, make_engine
from mdpub.crud.documents import (
    get_all_documents,
    get_by_collection,
    get_last_committed,
    list_collections,
)


def _fail(msg: str, cause: Exception = None) -> None:
    """Print a user-friendly error to stderr and exit 1."""
    typer.echo(f"Error: {msg}", err=True)
    if cause:
        typer.echo(f"  {cause}", err=True)
    raise typer.Exit(1)


def _settings(overrides: dict = None) -> Settings:
    """Load config with standard CLI error handling."""
    try:
        return load_config(overrides=overrides)
    except ValueError as e:
        _fail(str(e))


def _echo_commit(counts: dict, changes: list) -> None:
    """Print per-doc commit status and a summary line."""
    for status, slug in changes:
        typer.echo(f"  {status}: {slug}")
    typer.echo(
        f"Commit complete - "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} unchanged"
    )


def build_cmd(
    path: Annotated[str, typer.Argument(help="File or directory to process")],
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory")] = None,
    staging: Annotated[Optional[str], typer.Option("--staging-dir", help="Staging directory")] = None,
    parser: Annotated[Optional[str], typer.Option("--parser-config", help="MarkdownIt preset name")] = None,
    nesting: Annotated[Optional[int], typer.Option("--max-nesting", help="Max heading depth for sections")] = None,
    versions: Annotated[Optional[int], typer.Option("--max-versions", help="Max stored versions per doc")] = None,
    ):
    """Run the full pipeline: extract -> commit -> export."""
    settings = _settings(overrides={
        "output_dir": out, "staging_dir": staging,
        "parser_config": parser, "max_nesting": nesting, "max_versions": versions,
    })
    engine = make_engine(settings.db_url)
    init_db(engine)
    staging_dir = Path(settings.staging_dir)

    # --- extract ---
    try:
        extracted = run_extract(path, settings.parser_config, staging_dir)
    except RuntimeError as e:
        _fail(str(e))
    for src, out_file in extracted:
        typer.echo(f"  {src} -> {out_file}")
    typer.echo(f"Extracted {len(extracted)} document(s) to {staging_dir}/")

    # --- commit ---
    try:
        counts, changes = run_commit(engine, settings.max_versions, settings.max_nesting, staging_dir)
    except Exception as e:
        _fail("Commit failed", e)
    _echo_commit(counts, changes)

    # --- export ---
    output_dir = Path(settings.output_dir)
    try:
        with Session(engine) as session:
            exported = get_last_committed(session)
            results = run_export(
                session, exported, output_dir, settings.output_format,
                settings.max_tags, settings.max_metrics,
            )
    except Exception as e:
        _fail("Export failed", e)
    for slug, mdx_path in results:
        typer.echo(f"  {slug} -> {mdx_path}")
    typer.echo(f"Exported {len(results)} document(s) to {output_dir}/")


def list_cmd():
    """List top-level directories (collections) that contain documents in the database."""
    settings = _settings()
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
    reset: Annotated[bool, typer.Option("--reset", help="Drop and recreate all tables")] = False,
    ):
    """Initialize database schema. Use --reset to clear existing data."""
    settings = _settings()
    engine = make_engine(settings.db_url)
    if reset:
        SQLModel.metadata.drop_all(engine)
        typer.echo("Existing data cleared.")
    init_db(engine)
    typer.echo(f"Database initialized at: {settings.db_url}")


def extract_cmd(
    path: Annotated[str, typer.Argument(help="File or directory to extract from")],
    staging: Annotated[Optional[str], typer.Option("--staging-dir", help="Staging directory")] = None,
    parser: Annotated[Optional[str], typer.Option("--parser-config", help="MarkdownIt preset name")] = None,
    ):
    """Recursively extract blocks, frontmatter, and content hash."""
    settings = _settings(overrides={"staging_dir": staging, "parser_config": parser})
    staging_dir = Path(settings.staging_dir)
    try:
        results = run_extract(path, settings.parser_config, staging_dir)
    except RuntimeError as e:
        _fail(str(e))
    for src, out_file in results:
        typer.echo(f"  {src} -> {out_file}")
    typer.echo(f"Extracted {len(results)} document(s) to {staging_dir}/")


def commit_cmd(
    staging: Annotated[Optional[str], typer.Option("--staging-dir", help="Staging directory")] = None,
    nesting: Annotated[Optional[int], typer.Option("--max-nesting", help="Max heading depth for sections")] = None,
    versions: Annotated[Optional[int], typer.Option("--max-versions", help="Max stored versions per doc")] = None,
    ):
    """Upsert parsed document data to the database."""
    settings = _settings(overrides={"staging_dir": staging, "max_nesting": nesting, "max_versions": versions})
    engine = make_engine(settings.db_url)
    init_db(engine)
    staging_dir = Path(settings.staging_dir)

    try:
        counts, changes = run_commit(engine, settings.max_versions, settings.max_nesting, staging_dir)
    except Exception as e:
        _fail("Commit failed", e)
    if not counts:
        typer.echo("Nothing staged. Run 'mdpub extract <path>' first.")
        raise typer.Exit(1)

    _echo_commit(counts, changes)


def export_cmd(
    out: Annotated[Optional[str], typer.Option("--out-dir", help="Output directory")] = None,
    collection: Annotated[Optional[str], typer.Option("--collection", help="Export docs under this top-level directory")] = None,
    all_docs: Annotated[bool, typer.Option("--all", help="Export all documents in the database")] = False,
    max_tags: Annotated[Optional[int], typer.Option("--max-tags", help="Max tags per section; 0 = unlimited")] = None,
    max_metrics: Annotated[Optional[int], typer.Option("--max-metrics", help="Max metrics per section; 0 = unlimited")] = None,
    ):
    """Write standardized MD/MDX + sidecar JSON to output dir."""
    settings = _settings(overrides={"output_dir": out, "max_tags": max_tags, "max_metrics": max_metrics})
    engine = make_engine(settings.db_url)
    init_db(engine)
    output_dir = Path(settings.output_dir)

    try:
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
                raise typer.Exit(1)  # intentional early exit; re-raised below

            results = run_export(
                session, docs, output_dir, settings.output_format,
                settings.max_tags, settings.max_metrics,
            )
    except typer.Exit:
        raise  # re-raise intentional no-docs exit before generic handler
    except Exception as e:
        _fail("Export failed", e)

    for slug, mdx_path in results:
        typer.echo(f"  {slug} -> {mdx_path}")
    typer.echo(f"Exported {len(results)} document(s) to {output_dir}/")
