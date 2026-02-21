from pathlib import Path
from mdpub.parser.pipeline import ingest_markdown_text
from mdpub.crud.db import make_engine, create_tables, session_scope
from mdpub.crud.sql_repo import SQLRepo

def test_incremental_upsert_skips_when_hash_unchanged(tmp_path: Path):
    engine = make_engine("sqlite://")
    create_tables(engine)

    raw1 = """---
title: X
---
# H
Hello
"""
    source = str(tmp_path / "a.md")
    doc1 = ingest_markdown_text(source, raw1)

    with session_scope(engine) as session:
        repo = SQLRepo(session)

        _, changed1 = repo.upsert_by_source_path(doc1)
        assert changed1 is True

        # same content -> skip
        doc2 = ingest_markdown_text(source, raw1)
        _, changed2 = repo.upsert_by_source_path(doc2)
        assert changed2 is False

        # changed content -> update
        raw2 = raw1 + "\nMore\n"
        doc3 = ingest_markdown_text(source, raw2)
        _, changed3 = repo.upsert_by_source_path(doc3)
        assert changed3 is True
