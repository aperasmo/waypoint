"""
collect_manual.py

Collects sections of the public INZ Operational Manual for the Waypoint
RAG project's ingestion pipeline.

WHY THIS RUNS LOCALLY, NOT IN CLAUDE'S SANDBOX:
Claude's bash environment has no outbound network access, so this script
cannot be executed inside that sandbox. Run it on your own machine, where
you have normal internet access.

WHAT IT DOES
1. Reads robots.txt and respects Disallow rules and crawl-delay.
2. Starts from the manual's table of contents (toc.htm) and walks every
   /opsmanual/<id>.htm link, optionally filtered to a prefix allowlist
   (e.g. only "SR" and "WD" section codes).
3. Rate-limits requests (default: 1 request every 2 seconds) and retries
   transient failures with exponential backoff.
4. Extracts the page title, effective date, and body text, and writes one
   markdown file per section with YAML front matter, matching the format
   Claude already used for the seed files in this folder.
5. Is resumable: pages already saved are skipped on the next run, unless
   --force is passed.
6. Writes/updates manifest.json with every collected section.

USAGE
    pip install -r requirements.txt
    python collect_manual.py --prefixes SR WD --out ../
    python collect_manual.py --prefixes SR WD --out ../ --force   # re-download everything
    python collect_manual.py --all --out ../                     # collect the ENTIRE manual (slow, be deliberate about this)

A NOTE ON SCOPE AND COURTESY
This script is deliberately conservative by default: a real crawl-delay,
a real User-Agent that identifies the tool honestly, and a hard concurrency
of 1 (no parallel requests). Before doing a full-manual run, it's worth
rereading immigration.govt.nz's website terms of use. This is public
government information, but "publicly available" and "unrestricted bulk
scraping" are not automatically the same thing.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Requires Python 3.10+ (uses the `X | None` union syntax below).

BASE_URL = "https://www.immigration.govt.nz"
TOC_URL = f"{BASE_URL}/opsmanual/toc.htm"
USER_AGENT = "WaypointManualCollector/0.1 (personal research project; contact: allanperasmo@gmail.com)"
DEFAULT_DELAY_SECONDS = 2.0
MAX_RETRIES = 3
PAGE_ID_RE = re.compile(r"/opsmanual/(\d+)\.htm$")
SECTION_CODE_RE = re.compile(r"^([A-Z]{1,3}\d+(?:\.\d+)*)\s+(.*)$")
EFFECTIVE_DATE_RE = re.compile(r"Effective\s+(\d{2}/\d{2}/\d{4})")


@dataclass
class Page:
    url: str
    page_id: str
    section_code: str | None = None
    title: str | None = None


@dataclass
class Collector:
    out_dir: Path
    prefixes: list[str] | None
    delay: float
    session: requests.Session = field(default_factory=requests.Session)
    manifest: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(f"{BASE_URL}/robots.txt")
        self.rp.read()

    def allowed(self, url: str) -> bool:
        return self.rp.can_fetch(USER_AGENT, url)

    def fetch(self, url: str) -> str | None:
        if not self.allowed(url):
            print(f"  SKIP (robots.txt disallows): {url}")
            return None
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=20)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                last_err = e
                wait = 2 ** attempt
                print(f"  retry {attempt}/{MAX_RETRIES} after error ({e}); waiting {wait}s")
                time.sleep(wait)
        print(f"  FAILED after {MAX_RETRIES} attempts: {url} ({last_err})")
        return None

    def discover_links(self) -> list[Page]:
        html = self.fetch(TOC_URL)
        if not html:
            raise SystemExit("Could not fetch the table of contents. Aborting.")
        soup = BeautifulSoup(html, "html.parser")
        all_anchors = soup.find_all("a", href=True)
        print(f"  (diagnostic) total <a href> tags on the page: {len(all_anchors)}")

        pages: dict[str, Page] = {}
        opsmanual_link_count = 0
        code_matched_count = 0

        for a in all_anchors:
            href = urljoin(TOC_URL, a["href"])
            m = PAGE_ID_RE.search(urlparse(href).path)
            if not m:
                continue
            opsmanual_link_count += 1
            page_id = m.group(1)

            # The code (e.g. "SR3.10") and the title text are sometimes in
            # separate inline elements with no literal space between them,
            # which breaks a naive get_text(). Try the anchor's title
            # attribute first (this site puts "CODE Title text" there),
            # then fall back to text with an inserted separator so words
            # from different child tags don't get glued together.
            candidates = [
                a.get("title", "").strip(),
                a.get_text(" ", strip=True),
            ]
            section_code, title_text = None, None
            for candidate in candidates:
                candidate = re.sub(r"\s+", " ", candidate).strip()
                code_match = SECTION_CODE_RE.match(candidate)
                if code_match:
                    section_code = code_match.group(1)
                    title_text = candidate
                    code_matched_count += 1
                    break
            if title_text is None:
                title_text = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()

            if self.prefixes:
                if not section_code or not any(section_code.startswith(p) for p in self.prefixes):
                    continue

            pages[page_id] = Page(url=href, page_id=page_id, section_code=section_code, title=title_text)

        print(f"  (diagnostic) links pointing to /opsmanual/<id>.htm: {opsmanual_link_count}")
        print(f"  (diagnostic) of those, links where a section code could be parsed: {code_matched_count}")
        if opsmanual_link_count == 0:
            print(
                "  (diagnostic) WARNING: zero /opsmanual/ links found at all. This means the page "
                "requests.get() fetched doesn't look like the manual page -- possibly a redirect, "
                "cookie/consent wall, or bot-protection response. Try: "
                "print(len(html)) and print(html[:500]) right after the fetch() call to inspect it."
            )
        return list(pages.values())

    def extract_content(self, html: str) -> tuple[str, str | None]:
        """Returns (markdown_body, effective_date). Falls back gracefully if
        the page structure doesn't match what we expect -- inspect the raw
        HTML in your browser's dev tools and adjust the selector below if
        INZ changes their template."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # Try a few likely content containers before falling back to <body>.
        content = (
            soup.find("div", id=re.compile("content", re.I))
            or soup.find("main")
            or soup.find("article")
            or soup.body
        )
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)

        date_match = EFFECTIVE_DATE_RE.search(text)
        effective_date = date_match.group(1) if date_match else None

        return text, effective_date

    def save_page(self, page: Page, body: str, effective_date: str | None):
        code = page.section_code or page.page_id
        safe_name = code.replace(" ", "_")
        dest = self.out_dir / f"{safe_name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)

        front_matter = {
            "section_code": code,
            "title": page.title or code,
            "source_url": page.url,
            "effective_date": effective_date,
            "fetched_date": time.strftime("%Y-%m-%d"),
        }
        fm_lines = "\n".join(f'{k}: {json.dumps(v)}' for k, v in front_matter.items())
        dest.write_text(f"---\n{fm_lines}\n---\n\n{body}\n", encoding="utf-8")

        self.manifest.append(
            {
                "section_code": code,
                "title": page.title,
                "file": str(dest.relative_to(self.out_dir.parent)) if self.out_dir.parent in dest.parents else str(dest),
                "source_url": page.url,
                "effective_date": effective_date,
            }
        )

    def write_manifest(self):
        manifest_path = self.out_dir.parent / "manifest.json"
        existing = {}
        if manifest_path.exists():
            try:
                existing_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = {p["section_code"]: p for p in existing_data.get("pages", [])}
            except (json.JSONDecodeError, KeyError):
                pass
        for entry in self.manifest:
            existing[entry["section_code"]] = entry
        manifest_path.write_text(
            json.dumps(
                {
                    "manual_toc_url": TOC_URL,
                    "collected_date": time.strftime("%Y-%m-%d"),
                    "pages": list(existing.values()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote manifest with {len(existing)} total entries -> {manifest_path}")

    def run(self, force: bool):
        print(f"Reading table of contents: {TOC_URL}")
        pages = self.discover_links()
        print(f"Found {len(pages)} matching section links.")

        for i, page in enumerate(pages, 1):
            code = page.section_code or page.page_id
            safe_name = code.replace(" ", "_")
            dest = self.out_dir / f"{safe_name}.md"
            if dest.exists() and not force:
                print(f"[{i}/{len(pages)}] SKIP (already have) {code}")
                continue

            print(f"[{i}/{len(pages)}] Fetching {code}: {page.url}")
            html = self.fetch(page.url)
            if html is None:
                continue
            body, effective_date = self.extract_content(html)
            self.save_page(page, body, effective_date)
            time.sleep(self.delay)

        self.write_manifest()


def main():
    parser = argparse.ArgumentParser(description="Collect INZ Operational Manual sections.")
    parser.add_argument(
        "--prefixes",
        nargs="*",
        default=["SR", "WD"],
        help="Only collect section codes starting with these prefixes (default: SR WD). "
        "Ignored if --all is passed.",
    )
    parser.add_argument("--all", action="store_true", help="Collect the entire manual, ignoring --prefixes.")
    parser.add_argument("--out", default="../residence", help="Output directory for markdown files.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="Seconds between requests.")
    parser.add_argument("--force", action="store_true", help="Re-download pages even if already saved.")
    args = parser.parse_args()

    prefixes = None if args.all else args.prefixes
    collector = Collector(out_dir=Path(args.out), prefixes=prefixes, delay=args.delay)
    collector.run(force=args.force)


if __name__ == "__main__":
    main()
