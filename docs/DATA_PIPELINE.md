# Data Pipeline

Waypoint uses a manual source-update workflow for the Immigration New Zealand Operational Manual.

The system does **not** automatically crawl or scrape the INZ website.

## Overview

```text
1. Manually save MHTML
        ↓
2. Validate the archive
        ↓
3. Extract policy content
        ↓
4. Build staging corpus
        ↓
5. Compare and audit
        ↓
6. Promote approved corpus
        ↓
7. Ingest changed content
        ↓
8. Evaluate
```

The source archive and staging area are kept separate from the active corpus so changes can be reviewed before they affect the live system.

## 1. Capture the Source

Open the required Operational Manual page in a normal browser and save it manually as an MHTML file.

Use the section code as the filename.

Example:

```text
U13.15.mhtml
SR3.5.mhtml
WD3.5.mhtml
```

Store the files under:

```text
data/source_archive/operational_manual/
```

The source archive is local working material and is not intended to be committed to the public repository.

## 2. Validate the MHTML Archive

From `backend/`:

```bash
uv run python -m scripts.validate_mhtml_archive
```

The validator checks that each archive:

- can be read as MHTML;
- contains an HTML page;
- contains the expected Operational Manual content area; and
- matches the section code in its filename.

Do not continue if a source file fails validation.

## 3. Build the Staging Corpus

Run:

```bash
uv run python -m scripts.build_staging_corpus
```

This converts the manually archived MHTML into the Markdown format used by Waypoint.

The process:

- extracts the current policy area;
- removes navigation and unrelated page content;
- preserves policy lists and tables;
- records source information and effective dates; and
- creates a staging manifest.

The active corpus is not changed during this step.

## 4. Audit the Staging Build

Run the staging integrity audit:

```bash
uv run python -m scripts.audit_staging_integrity
```

Useful additional checks include:

```bash
uv run python -m scripts.audit_mhtml_encoding
uv run python -m scripts.audit_mhtml_parser
uv run python -m scripts.audit_mhtml_topic_boundaries
uv run python -m scripts.audit_policy_list_shapes
uv run python -m scripts.audit_browse_taxonomy
```

These are read-only checks.

They are intended to catch malformed source captures, parsing problems, encoding issues and taxonomy gaps before the new corpus is promoted.

## 5. Compare Staging with the Active Corpus

Run:

```bash
uv run python -m scripts.compare_active_staging
uv run python -m scripts.compare_corpus_semantics
```

These commands show what changed between the current corpus and the newly rebuilt staging corpus.

Review:

- added sections;
- removed sections;
- title changes;
- source URL changes;
- effective-date changes; and
- policy-content changes.

Unexpected changes should be investigated before promotion.

## 6. Promote the Approved Corpus

After the staging build and comparison have been reviewed, replace the active corpus and manifest with the approved staging version using the project's normal promotion process.

The important rule is:

**Do not promote staging merely because the scripts completed successfully. Review the reported changes first.**

## 7. Audit the Active Corpus

After promotion:

```bash
uv run python -m scripts.audit_corpus
```

If needed, use:

```bash
uv run python -m scripts.inspect_corpus_diffs
```

for a closer review of content changes.

## 8. Update the Database

First preview the database change:

```bash
uv run python -m scripts.ingest --dry-run --prune
```

Review the output.

If it is correct:

```bash
uv run python -m scripts.ingest --prune
```

Waypoint compares content hashes and only re-embeds sections whose content changed.

This avoids re-embedding the entire corpus after every update.

## 9. Evaluate

After ingestion, run:

```bash
uv run python -m scripts.evaluate
```

Then, with the backend running:

```bash
uv run python -m scripts.evaluate_answers
```

Finally run the unit tests:

```bash
uv run pytest
```

## Recommended Update Checklist

Before considering an update complete:

- MHTML files validated
- staging corpus built
- staging integrity audit passed
- active vs staging differences reviewed
- browse taxonomy checked
- active corpus audited
- database dry run reviewed
- changed content ingested
- retrieval evaluation reviewed
- answer evaluation reviewed
- tests passing

## Source Boundary

This pipeline is intentionally manual at the source-acquisition stage.

Waypoint processes locally saved copies of public Operational Manual pages. It does not run a background crawler or automatically fetch changes from Immigration New Zealand.
