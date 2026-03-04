# mdpub — Potential Directions

The core pipeline (extract → commit → export) is stable and fully tested. The directions below
are ordered roughly by value and implementation effort, starting with the most natural next step.

---

## B. `mdpub status`

**What**: Show pipeline state — what's staged, what's committed but not exported, DB summary.

```
Staged:    3 documents in .mdpub/staging/
Committed: 12 documents (last: 2026-02-28)
Exported:  10 documents in dist/ (2 pending export)
```

**Why**: Useful for understanding where you are in the pipeline, especially in CI or watch mode.

**Scope**: New `status_cmd`; read-only queries against the staging dir and DB.

---

## C. Watch mode (`mdpub watch <path>`)

**What**: Re-run `extract` + `commit` automatically when source `.md`/`.mdx` files change.

**Why**: Removes manual re-runs during authoring; natural fit after the pipeline stabilizes.

**Scope**: New `watch_cmd` wrapping `run_extract` + `run_commit` with `watchfiles` (or similar).
Optional `--export` flag to also re-export on each change.

---

## D. Section reconfiguration via DB

**What**: CLI commands to hide/show/reorder sections without re-running the pipeline.

```bash
mdpub section hide my-doc 2      # set Section.hidden = True for position 2
mdpub section show my-doc 2
mdpub section move my-doc 2 0    # reorder section to position 0
```

**Why**: `Section.hidden` and `Section.position` are already in the schema. Expose them as
first-class controls so content can be reshaped post-commit without re-parsing.

**Scope**: New `section_cmd` group in `commands.py`; CRUD helpers in `documents.py`.

---

## E. Query / search (`mdpub query`)

**What**: Search sections by tag, metric threshold, or content substring.

```bash
mdpub query --tag nlp --min-relevance 0.8
mdpub query --metric readability --min-value 70
mdpub query --content "introduction"
```

Returns matching sections with their slug, position, and matched value.

**Why**: Exposes the DB's structured data as a searchable surface — useful for pre-filtering
content before templating or for auditing enrichment results.

**Scope**: New `query_cmd`; SQL queries via existing `Session` + `select` patterns.

---

## F. nlp-stemplate integration contract

**What**: Formalize the data contract between mdpub's export and nlp-stemplate's input.

- Add a `$schema` version field to the sidecar JSON
- Publish a JSON Schema for `<slug>.json`
- Add `mdpub validate-export` to verify sidecar files against the schema

**Why**: The README describes mdpub as a "plug-and-play data interface layer" for nlp-stemplate.
A versioned schema makes that interface explicit, testable, and stable across releases.

**Scope**: Schema definition file; `validate_cmd` in `commands.py`; `jsonschema` dependency.

---

## G. PostgreSQL / multi-project support

**What**: Support multiple named projects sharing a single PostgreSQL instance via schema namespacing.

```bash
MDPUB_DB_URL="postgresql://..." mdpub --project mysite build docs/
```

**Why**: SQLite is fine for single projects; PostgreSQL with schema isolation enables team use
or multiple sites managed from one server.

**Scope**: `project` setting in `Settings`; schema prefix in `database.py`; no model changes needed.
