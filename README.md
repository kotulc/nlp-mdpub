# mdpub
A CLI pipeline for decomposing Markdown documents into structured content — persisted to a database and emitted as standardized MD/MDX + JSON for static site publishing.

General Workflow:
```
MD/MDX → parse → extract(configs) → commit → export(configs) → structured MD/MDX + JSON
```


## Features
- **Frontmatter extraction** — parses YAML frontmatter (title, date, tags, custom fields)
- **Rich block extraction** — headings, paragraphs, code fences, lists, images, tables
- **Incremental updates** — SHA-256 content hashing skips unchanged documents
- **Versioning & diffs** — tracks document history; surfaces unified diffs between versions
- **Dual output** — emits standardized MD/MDX files and sidecar JSON metadata alongside DB persistence
- **Composable CLI** — pipeline steps (parse, store, emit) can be run independently or chained
- **Pluggable storage** — SQLite by default; PostgreSQL via environment variable


## Pipeline
Each step is a discrete CLI command that can run independently or be chained:

```
mdpub build <path>    # run the entire pipeline (all of the following commands)
mdpub init            # initialize database schema and optionally clears stored data
mdpub extract <path>  # recursively extract blocks, frontmatter, and content hash
mdpub commit          # upsert parsed document data to the database
mdpub export          # write standardized MD/MDX + sidecar JSON to output dir
```

`<path>` is a single `.md`/`.mdx` file or a directory (recursively scanned).


## Configuration
The standardized structure of the returned MD/MDX documents is fully configurable either via CLI options or by modifying the default `config.yaml` file. Options and flags supplied via the CLI will override all local configurations stored in `config.yaml`.

`config.yaml` contains the following app-level settings:
- db_url (str): The connection string to the external databse instance
- max_nesting (int): The maximum nesting level before child content is flattened
- output_dir (str): The output directory to export results to
- output_format (str): Desired markdown output format, "md" or "mdx" 
- parser_config (str): MarkdownIt parser configuration preset name, defaults to "gfm-like"


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
mdpub build docs/ --dir dist/

# Or in stages:
mdpub init
mdpub extract docs/
mdpub commit
mdpub export --dir dist/
```

### Output
For each document, `export` produces:

| File | Description |
|------|-------------|
| `<slug>.mdx` | Standardized MDX with merged frontmatter (slug, doc_id, hash, tags) |
| `<slug>.json` | Full metadata: frontmatter, blocks, metrics, version history |


### Persistance
| Variable | Default | Description |
|----------|---------|-------------|
| `MDPUB_DB_URL` | `sqlite:///mdpub.db` | SQLAlchemy database URL |


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
  config.py           # Loads user options and configurations
```


### core
The core package contains all of the internal logic leveraged by the pipeline and CLI commands. This includes markdown parsing, data extraction, recomposition, versioning and related utilties.

```
core/
  extract/            # Config based conversion of parsed outputs
    extract.py        # Convert parsed content to standard representation
    sections.py       # Conversion logic for the standard representation of document content
    blocks.py         # Conversion logic for content blocks (headings, code, lists, images, tables)
  utils/              # Core utility functions
    diff.py           # Functionality to present unified diffs between document versions
    slug.py           # Document slugification utility
    hashing.py        # SHA-256 content hashing utilities
  export.py           # Config based DB to MDX + JSON output logic
  parse.py            # File discovery, markdown parsing, frontmatter and token conversion
  pipeline.py         # Orchestrates parse → export pipeline
```


### crud
The crud package is the data persistance layer that defines the interface surface between the database (stored data, tables, methods, and utilties) and the rest of the application.

```
crud/
  database.py         # Database engine, session, schema initialization
  tables.py           # SQLModel database schema definition
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
- Use paramaterized tests when possible to avoid test sprawl
