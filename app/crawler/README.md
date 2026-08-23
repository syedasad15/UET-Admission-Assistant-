# app/crawler/

Generic website crawler used to pull raw pages from the UET site before
admission-specific filtering happens in `app/discovery/`.

| File | Purpose |
|---|---|
| `crawler.py` | Breadth-first crawler (`requests` + `BeautifulSoup`). Normalizes URLs, strips fragments, allow-lists domains/paths, fetches pages, extracts text/links, and saves each page to disk. Entry point: `crawl()`. |
| `admissioncrawler.py` | **Empty file (0 bytes).** Presumably intended as an admission-specific crawler variant; currently dead — either finish it or delete it. |
