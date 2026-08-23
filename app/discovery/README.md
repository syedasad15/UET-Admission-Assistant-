# app/discovery/

The data-preparation stage: turning raw crawled pages and downloaded PDFs
into a clean, deduplicated, reviewed knowledge base ready for embedding.
This is the largest and most iteratively-built part of the project — most
scripts read/write JSON files in `data/inventory/admission/` and were run
by hand, in sequence, with manual review steps in between.

## Sub-pipeline order

1. **`sitemapping/`** — find and classify which pages/sections on the UET
   admission site are worth crawling
2. **`content targeting/`** — filter the site map down to in-scope,
   internal, non-file URLs
3. **`content crawling/`** — pull out pages flagged for manual review
4. **`pdf pipeline/`** — download, dedupe, OCR, clean, and audit every
   admission PDF (prospectus, fee schedule, merit lists, etc.)
5. **`Knowledge build/`** — merge the cleaned page text and PDF chunks into
   the final knowledge base consumed by `app/ingestion/`

See each subfolder's own `README.md` for file-by-file detail.
