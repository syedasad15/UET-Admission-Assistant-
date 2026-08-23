# app/discovery/pdf pipeline/

Stage 4 of discovery: the PDF side of the knowledge base (prospectus, fee
schedules, merit lists, etc.). This is the largest and most manually-iterated
part of the whole project — 21 scripts, several of which are numbered/dated
one-off audit or repair passes rather than a clean linear pipeline. Grouped
below by function rather than filename, since several scripts are ad-hoc
patches on top of earlier ones.

## Core linear pipeline

| File | Purpose |
|---|---|
| `pdfdownloader.py` | Downloads the ~29 PDFs marked `KEEP_FILE` in `_pages_reviewed.json`, saves them under `data/inventory/admission/pdfs/`, and writes a manifest (`_pdf_downloads.json`). |
| `pdfduplicator.py` | Detects byte-for-byte identical downloaded PDFs and records canonical/duplicate groups in `_pdf_duplicates.json`. |
| `pdfchecker.py` | Reads the first page of specific PDFs (used to manually sanity-check a reported duplicate group). |
| `pdfocrchecker.py` | For each unique (deduped) PDF, checks whether it needs OCR (i.e. has no extractable native text) and writes `_pdf_ocr_check.json`. |
| `pdftextextractor.py` | Core OCR/text-cleaning utilities: `clean_ocr_text` (format-only cleanup), `flag_garbled_urls`, `assess_text_quality` (heuristic detector for garbled/wrong-script OCR output). |
| `pdfreviewer.py` | Prints/reviews extracted per-PDF knowledge chunks against the duplicates list, producing `_pdf_title_review.json` for manual title/quality sign-off. |
| `pdfrefinement.py` | Groups filtered chunks by source PDF and builds manual "override" chunks per page/decision — the step that folds in hand-corrected content (e.g. a fee table transcribed from a photo). |
| `filterexcluded.py` | Removes chunks belonging to excluded/promotional/duplicate PDFs from the working chunk set, verifying nothing outside the exclusion list is touched (`chunk_key` identity check). |
| `promotefiltered.py` | Promotes the filtered/cleaned chunk set forward to the next stage file. |

## Audit / repair scripts (manual QA passes, largely one-off)

| File | Purpose |
|---|---|
| `audit_pdf_knowledge.py` | General audit of extracted PDF knowledge chunks against source metadata. |
| `audit73.py`, `audit73_final.py`, `audit73_metadata_sources.py`, `audit_73_merged.py` | A sequence of audits specifically for a batch of "73" chunks (likely 73 recovered/re-processed chunks) — checking word/line counts, course-code detection, and metadata source consistency at each stage of merging. Names indicate iterative fix-and-recheck cycles rather than a single script. |
| `merge73.py`, `promote73_final.py`, `repair73merged.py` | Merge, promote, and repair passes for that same "73" batch — deduping by `chunk_key`/`page_key` and backing up before replacing data. |
| `73.py`, `85.py` | Batch-specific extraction/validation scripts (73 and 85 refer to specific page/chunk counts being processed) — includes page-quality heuristics (`native_text_quality`), text chunking, and OOM-safety handling for large PDFs. |
| `ocr85.py` | Re-OCRs specifically the pages listed in `_pdf_extraction_skip_summary.json` (previously skipped pages), using English + Urdu OCR, without rerunning the full pipeline. |
| `inspect_pdf_outputs.py` | Manual inspection tool for reviewing PDF pipeline output files during development. |

**Note for cleanup:** the `73`/`85`-prefixed and `audit`/`merge`/`promote`/`repair`
scripts read as an incremental, hand-run debugging trail (fix data → audit →
merge → repair → re-audit) rather than a maintained pipeline. If this repo is
going in front of UET admin, consider consolidating this folder into a single
documented `pdf_pipeline.py` with clear stage functions, and moving the
one-off audit scripts into a `dev/` or `scripts/archive/` folder.
