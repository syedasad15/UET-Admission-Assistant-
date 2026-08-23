# data/inventory/admission/

The working directory for the entire admission discovery/PDF pipeline — 85
files. Grouped below by pipeline stage rather than listed alphabetically,
since most are intermediate outputs of the scripts in `app/discovery/`
(named to match the script that produced them).

## What's actually needed at runtime

Only **`_knowledge_base.json`** (1383 chunks, read by `app/ingestion/ingestion.py`)
matters once the vector store is built. Everything else below is a build-time
artifact kept for traceability/debugging.

## Site mapping & content targeting outputs

| File | Produced by | Contents |
|---|---|---|
| `_sections.json` | `sitemapping/admissiondiscovery.py` | Discovered top-level Admission homepage sections |
| `_selected_sections.json` | `sitemapping/admissionselection.py` | The 9 sections classified as in-scope |
| `_map.json` | `sitemapping/admissionmap.py` | Full structural site map |
| `_map_inspection.txt` | manual inspection | Human-readable structural review of `_map.json` |
| `_content_targets.json` | `content targeting/mapfiilter.py` / `mapfilter2.py` | Filtered, in-scope crawl targets |
| `_content_targets_reviewed.json` | `content targeting/contenttargetreview.py` | Manually reviewed/approved targets |

## Page crawling & review outputs

| File | Produced by | Contents |
|---|---|---|
| `_pages_reviewed.json` | `content crawling/pagereviewer.py` | 58 raw crawled pages with full text + review decisions (KEEP_FILE flags for PDFs, ACTION links, etc.) |
| `_review_pages.txt` | `content crawling/extractreviewpages.py` | Pages flagged `REVIEW` for manual attention |
| `_pages_knowledge_chunks.json` | `sitemapping/pagechunking.py` | 133 page-derived knowledge chunks (52 usable pages) |
| `_knowledge_books.json` | `Knowledge build/bookbuilder.py` | 52 pages/7 "books" (title/url/category only) |
| `_knowledge_refined.json` | `Knowledge build/knowledgerefinement.py` | Refined/filtered page decisions feeding `bookbuilder.py` |
| `_actions_registry.json` | `Knowledge build/actionbuilder.py` | 14 extracted action links (challan, apply, login, etc.) |
| `_sections.json` (main) — see `data/inventory/main_sections.json` | — | Separate, non-admission-scoped site sections |

## PDF pipeline outputs

| File | Produced by | Contents |
|---|---|---|
| `_pdf_downloads.json` | `pdf pipeline/pdfdownloader.py` | Manifest of ~29 downloaded PDFs |
| `_pdf_duplicates.json` | `pdf pipeline/pdfduplicator.py` | Byte-identical duplicate groups |
| `_pdf_ocr_check.json` | `pdf pipeline/pdfocrchecker.py` | Which unique PDFs need OCR |
| `_pdf_content.json` | text extraction | Raw extracted text per PDF |
| `_pdf_title_review.json` | `pdf pipeline/pdfreviewer.py` | Manual title/quality review |
| `_pdf_extraction_skip_summary.json` (see `_phase1_nonocr_content.json`, `_phase2_ocr_content.json`) | extraction phases | Phase 1 = native-text pages, Phase 2 = OCR'd pages |
| `_skipped_pages_manual_audit.csv` / `.txt` | manual audit | Human-reviewed table of skipped/low-quality OCR pages, with notes on which garbled pages still contain usable data (e.g. course-code tables) |
| `_pdf_skipped_page_audit_images/` | `pdf pipeline/ocr85.py` | Rendered page images for the skipped-page audit (e.g. `MS-2026-1_..._page_0009.png`) |
| `_pdf_recovered_pages.json`, `_pdf_recovered_native_pages.json`, `_pdf_recovered_native_chunks.json`, `_pdf_recovered_chunks.json` | recovery pass | Pages/chunks recovered from initially-skipped or misclassified PDFs |
| `_pdf_recovered_native_audit.json` / `.txt` | recovery audit | QA on the recovered-pages pass |
| `_pdf_knowledge_<uuid>.json` (23 files) | per-PDF extraction | One knowledge-chunk file per source PDF, named by an internal UUID (or by filename for a few, e.g. `_pdf_knowledge_admission-guide.json`, `_pdf_knowledge_MS-2026-1_...json`, `_pdf_knowledge_UG-2026-1_...json`) |
| `_pdf_knowledge_issues.json` | audit | Flagged problems across per-PDF knowledge files |
| `_pdf_knowledge_audit.json` | audit | General audit pass over per-PDF knowledge |
| `_pdf_knowledge_chunks.json` → `_pdf_knowledge_chunks_filtered.json` → `_pdf_knowledge_chunks_filtered_audit.json`/`.txt` | `filterexcluded.py` | Combined chunk set, then filtered to exclude promotional/duplicate PDFs, then audited |
| `_pdf_knowledge_chunks_73_merged.json` → `..._73_merged_audit.json`/`.txt` → `..._73_merged_final.json` → `..._73_merged_final_audit.json`/`.txt` → `..._73_merged_final_deep_audit.json`/`.txt` | `merge73.py`, `audit73*.py`, `promote73_final.py` | Iterative merge-then-audit cycle for a batch of 73 chunks — each step's output is the next step's input, kept as a paper trail |
| `_pdf_knowledge_chunks_backup_20260819_122306.json`, `..._124747.json` | `promote73_final.py` (safety backups) | Pre-replacement snapshots taken before overwriting the working chunk set |
| `_pdf_knowledge_final.json` | end of PDF pipeline | 1250 final PDF-derived chunks (19 PDFs) — merged into `_knowledge_base.json` by `knowledgemerge.py` |
| `_pdf_73_metadata_discovery_audit.json` / `.txt` | `audit73_metadata_sources.py` | Metadata-source consistency check for the "73" batch |

## Final knowledge base

| File | Purpose |
|---|---|
| `_knowledge_base.json` | **The file that matters at runtime.** 1383 merged chunks (133 page + 1250 PDF), built by `Knowledge build/knowledgemerge.py`, consumed by `app/ingestion/ingestion.py`. |
| `_ingestion_manifest.json` | Written by `app/ingestion/ingestion.py` — record of what was embedded and stored in ChromaDB. |

## Manual inspection / one-off scripts

| File | Purpose |
|---|---|
| `inspectjsons.py` | Read-only inventory inspector — auto-discovers every JSON file in this folder, categorizes them, and reports structure/record counts without modifying anything. |
| `jsonstrcutrechecker.py` | Reads `_content_targets.json` specifically and prints its structure (filename typo — "strcutre" — kept as-is). |
| `kb_inspection.txt` | Saved output of a knowledge-base inspection run (1383 total chunks). |
| `program_inspection.txt`, `program_list_only.txt` | Saved output of targeted inspections of program-related chunks within the knowledge base. |
| `admission-guide.txt` | Plain-text dump of the admission guide PDF's content, page by page — likely a manual reference copy. |
| `avvv.txt` | UTF-16 tab-separated audit table of manually-reviewed low-quality OCR pages (audit number, PDF, page, reason, decision, notes) — appears to be an early/working name for one of the skipped-page audit files. Worth renaming to something descriptive. |

## Nested folder

| Folder | Purpose |
|---|---|
| `phase2_ocr_pages/` | Raw OCR text output, one `.txt` file per page, organized into subfolders per source PDF (by UUID or filename, e.g. `admission-guide/page_0001.txt`, `90166bac-.../page_0008.txt`). Input to the Phase 2 OCR content assembly. |
