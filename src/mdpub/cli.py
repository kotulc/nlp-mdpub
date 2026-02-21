from __future__ import annotations

from pathlib import Path
import json
import typer

from mdpub.parser.pipeline import ingest_markdown_file
from mdpub.parser.emit import emit_standard_markdown, emit_metadata_json
from mdpub.parser.diff import unified_diff
from mdpub.util.fs import iter_markdown_files

from mdpub.crud.db import get_db_url, make_engine, create_tables, session_scope
from mdpub.crud.sql_repo import SQLRepo

app = typer.Typer(add_completion=False, help="mdpub: Markdown -> structured -> DB -> standardized MD/MDX + JSON")

def _ensure_out(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "diffs").mkdir(parents=True, exist_ok=True)

@app.command("db-init")
def db_init(db_url: str = typer.Option(None, "--db-url", help="Database URL (or set mdpub_DB_URL)")) -> None:
    """Create tables (quick start). For production, prefer Alembic migrations."""
    url = get_db_url(db_url)
    engine = make_engine(url)
    create_tables(engine)
    typer.echo("Tables created/verified.")

@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Markdown/MDX file to ingest"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Output directory"),
    db_url: str = typer.Option(None, "--db-url", help="Database URL (or set mdpub_DB_URL)"),
    diff: bool = typer.Option(False, "--diff", help="Write unified diffs on update"),
) -> None:
    """Ingest a single file with incremental update + optional diff."""
    _ensure_out(out)
    url = get_db_url(db_url)
    engine = make_engine(url)
    create_tables(engine)

    doc = ingest_markdown_file(path)

    with session_scope(engine) as session:
        repo = SQLRepo(session)
        old = repo.get_by_source_path(doc.source_path)
        saved, changed = repo.upsert_by_source_path(doc)

        stem = path.stem
        new_md = emit_standard_markdown(saved)

        (out / f"{stem}.standard.md").write_text(new_md, encoding="utf-8")
        (out / f"{stem}.metadata.json").write_text(
            json.dumps(emit_metadata_json(saved), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        if diff and changed and old is not None:
            old_md = emit_standard_markdown(old)
            d = unified_diff(old_md, new_md, fromfile=f"a/{stem}", tofile=f"b/{stem}")
            (out / "diffs" / f"{saved.slug or stem}.diff").write_text(d, encoding="utf-8")

    typer.echo("updated" if changed else "skipped (no change)")

@app.command("ingest-dir")
def ingest_dir(
    root: Path = typer.Argument(..., exists=True, readable=True, help="Directory to ingest recursively"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Output directory"),
    db_url: str = typer.Option(None, "--db-url", help="Database URL (or set mdpub_DB_URL)"),
    diff: bool = typer.Option(False, "--diff", help="Write unified diffs on update"),
) -> None:
    """Ingest a directory recursively with incremental updates + optional diff detection."""
    _ensure_out(out)
    url = get_db_url(db_url)
    engine = make_engine(url)
    create_tables(engine)

    files = list(iter_markdown_files(root))
    if not files:
        typer.echo("No .md/.mdx files found.")
        raise typer.Exit(code=0)

    updated = 0
    skipped = 0

    with session_scope(engine) as session:
        repo = SQLRepo(session)

        for path in files:
            doc = ingest_markdown_file(path)
            old = repo.get_by_source_path(doc.source_path)
            saved, changed = repo.upsert_by_source_path(doc)

            stem = path.stem
            new_md = emit_standard_markdown(saved)

            (out / f"{stem}.standard.md").write_text(new_md, encoding="utf-8")
            (out / f"{stem}.metadata.json").write_text(
                json.dumps(emit_metadata_json(saved), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            if diff and changed and old is not None:
                old_md = emit_standard_markdown(old)
                d = unified_diff(old_md, new_md, fromfile=f"a/{stem}", tofile=f"b/{stem}")
                (out / "diffs" / f"{saved.slug or stem}.diff").write_text(d, encoding="utf-8")

            if changed:
                updated += 1
            else:
                skipped += 1

    typer.echo(f"Done. updated={updated} skipped={skipped} total={len(files)}")
