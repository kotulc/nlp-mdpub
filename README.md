# mdpub

CLI pipeline for decomposing Markdown documents into structured content — persisted to a database and emitted as standardized MDX + JSON for static site publishing.

```
Markdown → parse → store → emit MDX + JSON
```


## Features

- **Frontmatter extraction** — parses YAML frontmatter (title, date, tags, custom fields)
- **Rich block extraction** — headings, paragraphs, code fences, lists, images, tables
- **Incremental updates** — SHA-256 content hashing skips unchanged documents
- **Versioning & diffs** — tracks document history; surfaces unified diffs between versions
- **Dual output** — emits standardized MDX files and sidecar JSON metadata alongside DB persistence
- **Composable CLI** — pipeline steps (parse, store, emit) can be run independently or chained
- **Pluggable storage** — SQLite by default; PostgreSQL via environment variable


## Pipeline

Each step is a discrete CLI command that can run independently or be chained:

```
mdpub parse <path>   # extract blocks, frontmatter, and content hash
mdpub store          # upsert parsed documents to the database
mdpub emit           # write standardized MDX + sidecar JSON to output dir
mdpub db-init        # initialize database schema
```

`<path>` is a single `.md`/`.mdx` file or a directory (recursively scanned).


## Quickstart

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

### PostgreSQL support (optional)

```bash
pip install -e ".[dev,postgres]"
export MDPUB_DB_URL="postgresql+psycopg://user:pass@localhost/mdpub"
```

### Run the pipeline

```bash
mdpub db-init
mdpub parse docs/
mdpub store
mdpub emit --out dist/
```


## Output

For each document, `emit` produces:

| File | Description |
|------|-------------|
| `<slug>.mdx` | Standardized MDX with merged frontmatter (slug, doc_id, hash, tags) |
| `<slug>.json` | Full metadata: frontmatter, blocks, metrics, version history |


## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MDPUB_DB_URL` | `sqlite:///mdpub.db` | SQLAlchemy database URL |


## Development

```bash
pytest          # run tests
ruff check .    # lint
mypy src/       # type check
```


## Architecture

```
cli.py              # Typer commands — parse, store, emit, db-init
parser/
  parse.py          # frontmatter + body extraction
  pipeline.py       # orchestrates parse → StructuredDocument
  blocks.py         # rich block extraction (headings, code, lists, images, tables)
  emit.py           # MDX + JSON output
  diff.py           # unified diff between document versions
crud/
  repo.py           # abstract DocumentRepo interface
  sql_repo.py       # SQLModel implementation with versioning
  memory_repo.py    # in-memory implementation for testing
  db.py             # engine, session, table init
util/
  fs.py             # slugify, markdown file discovery
  hashing.py        # SHA-256 content hashing
```