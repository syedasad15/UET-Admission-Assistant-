# app/discovery/content crawling/

Stage 3 of discovery: crawls the targeted pages and pulls out the subset
that needs manual review before being trusted as knowledge-base content.

| File | Purpose |
|---|---|
| `pagereviewer.py` | Normalizes crawled page records/URLs (largest file in this folder at ~40 KB) and drives the manual page-review workflow — deciding which crawled pages are usable, need rework, or should be dropped. |
| `extractreviewpages.py` | Reads `_pages_reviewed.json` and pulls out only the pages whose refinement decision/status is `REVIEW`, saving them to `_review_pages.txt` for focused manual attention. |
