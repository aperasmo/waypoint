# INZ Manual Data — Phase 1 Seed Set

## What's in here

**11 real, live-fetched sections** of the current INZ Operational Manual, covering the two scope areas from the project scope document:

- `residence/skilled-migrant-category/` — SR1.1, SR3.1, SR3.10, SR3.15, SR3.20, SR2.10
- `temporary-entry/post-study-work-visa/` — WD1, WD2, WD3, WD3.1, WD3.5

Each file is markdown with YAML front matter (`section_code`, `title`, `category`, `source_url`, `effective_date`, `fetched_date`), matching the schema your ingestion pipeline should expect. `manifest.json` indexes all of them.

`scraper/collect_manual.py` is a real, runnable Python scraper for collecting the rest of the manual, or re-collecting these same sections on a schedule.

## Important: why only 11 pages, and why fetched by hand

Claude's sandbox has no outbound network access for running code, so a bulk crawl can't run from inside this chat. What Claude *can* do is fetch individual pages one at a time through its own search/fetch tools, which is how these 11 real pages were collected, verified against the live site (not the outdated 2003–2010 archive that shows up in search results), and turned into structured files.

Doing that for the whole manual (hundreds of clauses) one page at a time in a chat isn't practical. That's what `collect_manual.py` is for: run it on your own machine, where you have normal network access.

## Correction from the earlier mockup

The mockup UI used citation codes like "SM7" as placeholders. The actual current section prefix for Skilled Migrant Category is **SR** (Skilled Migrant Residence Instructions), not SM. SM was the old numbering, retired in 2010. The real manual also shows a full revision history on every clause (e.g. SR3.10 has 6 previous versions going back to 2022), which is worth designing your re-index job around, not just a single "last updated" date.

## Running the scraper

```bash
cd scraper
pip install -r requirements.txt

# Default: just the SR and WD sections used in this seed set
python collect_manual.py --out ../residence

# Collect everything under a different prefix, e.g. Residence Instructions
python collect_manual.py --prefixes R --out ../residence-instructions

# Full manual (hundreds of pages -- be deliberate, this takes a while at the default 2s delay)
python collect_manual.py --all --out ../full-manual
```

The script:
- reads and respects `robots.txt` (confirmed: `/opsmanual/` is not disallowed, only `/admin`, `/Security/`, and the internal search paths are);
- identifies itself honestly via User-Agent;
- rate-limits to 1 request per 2 seconds by default;
- retries transient failures with backoff;
- skips pages it already has, so it's safe to re-run;
- updates `manifest.json` incrementally.

## Before you scale this up

Two things worth doing before a full-manual crawl or before this becomes anything other than your own local dev/portfolio use:

1. Re-read INZ's website terms of use for anything about automated collection.
2. Keep the content on the "information" side of the no-advice boundary from the scope document. These files are the raw material; how your app answers questions with them is what actually matters for the legal line.

## Content note

The section text in these files is reproduced from the public INZ Operational Manual for the purpose of building your own RAG index, the same reason the manual itself needs to be readable text for a retrieval pipeline to work. It isn't intended for redistribution as a document in its own right. The SR2.10 file also condenses the ESOL fee-schedule sub-clauses for readability; re-fetch the source URL directly before using it for anything involving exact dollar figures.
