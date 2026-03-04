# mdpub
A CLI pipeline for recomposing Markdown documents into structured content — persisted to a database and emitted as standardized MD/MDX + JSON for intelligence-augmented static site publishing.  

The standardized, configurable, flat section based data configuration supports a unified surface to present to AI-powered static templating engines such as the `nlp-stemplate` natural language powered static templating tool, creating a simple plug-and-play data interface layer.

General Workflow:
```
MD/MDX → parse + extract(configs) → commit → export(configs) → structured MD/MDX + JSON
```


## Features
- **Frontmatter extraction** — parses YAML frontmatter (title, date, tags, custom fields)
- **Rich block extraction** — headings, paragraphs, code fences, lists, images, tables
- **Incremental updates** — SHA-256 content hashing skips unchanged documents
- **Versioning & diffs** — tracks document history; surfaces unified diffs between versions
- **Dual output** — exports standardized MD/MDX files and sidecar JSON metadata alongside DB persistence
- **Composable CLI** — pipeline steps (extract, commit, export) can be run independently or chained
- **Pluggable storage** — supports standard persistance layers: SQLite (default) or PostgreSQL


## Pipeline
Each step is a discrete CLI command that can run independently or be chained:

```
mdpub build <path>    # run the entire pipeline (all of the following commands)
mdpub init            # initialize database schema and optionally clears stored data
mdpub extract <path>  # recursively extract blocks, frontmatter, and content hash
mdpub commit          # upsert parsed document data to the database
mdpub list            # list collections (top-level source directories) stored in the database
mdpub export          # write standardized MD/MDX + sidecar JSON to output dir
```

`<path>` is a single `.md`/`.mdx` file or a directory (recursively scanned).


## Configuration
All settings follow a four-tier priority (highest to lowest):
**CLI option → `MDPUB_<FIELD>` env var → `config.yaml` → built-in default**

Place a `config.yaml` in your working directory to set project-wide defaults. Any setting can be
overridden with `MDPUB_<FIELD>` env vars (e.g. `MDPUB_DB_URL`, `MDPUB_MAX_NESTING`) for a session.
Pass CLI options for per-run overrides.

| Setting | Default | Description |
|---------|---------|-------------|
| `db_url` | `sqlite:///mdpub.db` | SQLAlchemy connection string |
| `max_nesting` | `6` | Max heading depth before child content is flattened |
| `max_versions` | `10` | Max stored versions per document; `0` disables versioning |
| `max_tags` | `0` | Max tags per section in export; `0` = unlimited |
| `max_metrics` | `0` | Max metrics per section in export; `0` = unlimited |
| `output_dir` | `dist` | Output directory for exported MD/MDX + JSON files |
| `output_format` | `mdx` | Markdown output format: `md` or `mdx` |
| `parser_config` | `gfm-like` | MarkdownIt parser preset name |
| `staging_dir` | `.mdpub/staging` | Staging directory for intermediate extracted JSON |


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
# Single command:
mdpub build docs/ --out-dir dist/

# Run in stages:
mdpub init
mdpub extract docs/
mdpub commit
mdpub list                          # list available collections
mdpub export                        # export documents from the last commit
mdpub export --collection docs      # export all documents under docs/
mdpub export --all --out-dir dist/  # export every document to dist/
```

### Output
For each document, `export` produces:

| File | Description |
|------|-------------|
| `<slug>.md/mdx` | Standardized MD/MDX with frontmatter (slug + user fields only) |
| `<slug>.json` | Minimal metadata: frontmatter, sections with position, tags, and metrics |


### Enrichment (optional)
Between `extract` and `commit`, the staging JSON in `.mdpub/staging/` can be annotated by an
external tool. Each block supports:
- `tags`: `{tag_name: relevance_score}` — topic labels with a 0–1 relevance float
- `metrics`: `{metric_name: value}` — numeric measurements (readability, complexity, etc.)

These values are aggregated to the section level at commit time and included in the sidecar JSON.


## Architecture
```
nlp-mdpub/
├── src/mdpub/        # Main package source
│   ├── cli/          # Command-line interface
│   ├── core/         # Markdown parsing & recomposition logic
│   └── crud/         # Persistence layer (e.g. SQLModel)
├── tests/            # Test suite (pytest)
├── examples/         # Sample markdown input & output
├── pyproject.toml    # Project definition and metadata
└── README.md         # User documentation
```


### cli
The command line interface package contains all modules that define the CLI app, its available commands, options, flags, and interfaces to the `core` logic and `crud` layers. 

```
cli/
  cli.py              # CLI interface entrypoint (Typer command based)
  commands.py         # Defines available commands (e.g. init, extract, commit, export)
config.py             # Settings model (Pydantic) and config.yaml / env var loader
```


### core
The core package contains all of the internal logic leveraged by the pipeline and CLI commands. This includes markdown parsing, data extraction, recomposition, versioning and related utilties.

```
core/
  extract/            # Parsing and block extraction
    blocks.py         # Token-to-block converters (headings, code, lists, images, tables)
    extract.py        # Orchestrates parse → blocks → StagedDoc assembly
    parse.py          # File discovery, markdown parsing, frontmatter and token extraction
  utils/              # Core utility functions
    diff.py           # Unified diff between document versions
    hashing.py        # SHA-256 content hashing
    slug.py           # Document slugification
    tokens.py         # markdown-it token utilities
  export.py           # DB → MDX/MD + sidecar JSON output
  models.py           # Staging contract: StagedBlock, StagedDoc (Pydantic)
  pipeline.py         # run_extract / run_commit / run_export orchestration
```


### crud
The crud package is the data persistance layer that defines the interface surface between the database (stored data, tables, methods, and utilties) and the rest of the application.

```
crud/
  database.py         # Database engine, session, schema initialization
  documents.py        # Document and section persistence
  models.py           # SQLModel database schema definition
  versioning.py       # Support for document versioning logic
```


## Development
```bash
pytest          # run tests
ruff check .    # lint
mypy src/       # type check
```

### Contributing
This repository is currently in early development but feel free to submit PRs as long as all of your updates align with the following conventions...


#### Development Conventions
Focus on building readable, concise, minimal functional blocks organized by purpose. Project maintainability and interpretability is the primary goal, everything else is secondary.

The most important rule is to keep modules and code blocks simple and purposeful: Each module, class, function, block or call should have a single well-defined (and commented) purpose. DO NOT re-create the wheel, DO NOT add custom code when a common package will suffice. Add only the MINIMAL amount of code to implement the modules documented purpose.

#### Do's
- Be consistent with the style of the project and its conventions
- Simple elegant terse lines and declarations are the goal; optimize for readability
- Keep module, variable, class, and function names short (1-4 words) but distinct
- Function and variable names are snake case and class names are camel case
- Try to keep lines to 100 columns/characters or less (this is a soft limit)
- Include single returns (white space) to separate lines WITHIN logical blocks of code
- Include double returns (white space) BETWEEN logical blocks of code (e.g. after imports)
- Include a description of each module in a triple quoted comment at the top before imports
- Order module functions alphabetically or otherwise logically, be consistent.
- When vertically listing function arguments, indent the closing ) to match 
the argument indent (one level in from def), not back to the def column.

#### Dont's
- DO NOT vertically space lines of code unless completely necessary.
- DO NOT vertically align function arguments if they can reasonably fit on a single line.
- DO NOT * import ANYTHING. Always explicitly import at the top of the module only.
- DO NOT add any functionality outside the defined scope of a given module.


### Testing
- Use pytest: Organize by folder and module mirroring the structure of the source
- Add fixtures when multiple tests require them and define them at the top of the test module or in a conftest file when shared between modules.
- Define tests with the user's input prior to implementing a new feature (TDD)
- Keep unit and integration tests separate, short, and isolated
- Unit tests should test a single function with names like `test_<function>_<case>`
- Tests should be able to be described in a single line with triple quote docstrings
- Use parameterized tests when possible to avoid test sprawl
