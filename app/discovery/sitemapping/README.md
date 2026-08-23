# app/discovery/sitemapping/

Stage 1 of discovery: find and structurally map the UET Admission section of
the website before any full-page crawling happens.

| File | Purpose |
|---|---|
| `admissiondiscovery.py` | Fetches only the UET Admission homepage, extracts navigation links, converts them to absolute URLs, dedupes, and saves the discovered top-level sections. First step in the sitemapping chain. |
| `admissionselection.py` | Reads the sections found by `admissiondiscovery.py` and classifies them (does not crawl) to decide what's in scope before mapping. |
| `admissionmap.py` | Builds the full structural site map of the 9 selected Admission sections chosen by `admissionselection.py`. Not the final content crawler — just structure. |
| `pagechunking.py` | Combines `_knowledge_books.json` (52 usable pages/7 books — titles/urls/categories only) with `_pages_reviewed.json` (58 raw crawled pages with full text) to produce `_pages_knowledge_chunks.json`, the page-derived half of the final knowledge base. |
| `section_discovery.py` | Earlier/alternate version of homepage section discovery (targets `_sections.json` under a `main` category rather than `admission`). Mostly commented out — appears superseded by `admissiondiscovery.py`. |
| `sitemapper.py` | Session/config scaffolding for site mapping; body is mostly headers with implementation below. Support script for `admissionmap.py`. |
| `inspect_navigation.py` | Small diagnostic script (`main()` only) for manually inspecting discovered navigation data during development. |

Pipeline: `admissiondiscovery.py` → `admissionselection.py` → `admissionmap.py`
→ (crawl) → `pagechunking.py`.
