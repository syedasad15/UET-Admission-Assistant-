# data/inventory/admission/phase2_ocr_pages/

Raw per-page OCR text output from the PDF pipeline's Phase 2 (OCR'd pages).

One subfolder per source PDF (named by internal UUID, or by filename for a
few — `admission-guide/`, and two UUID-named ones tied to specific documents),
each containing one `page_NNNN.txt` file per OCR'd page:

| Subfolder | Pages |
|---|---|
| `90166bac-e657-4cee-890f-c34aee652b6c/` | 8 pages |
| `admission-guide/` | 8 pages |
| `bc079c7a-2bcf-4ca6-81bc-f15b9eb23b64/` | 2 pages |
| `c8856fd5-733e-46c8-8271-1ff78cdb9ceb/` | 1 page |
| `d3f4869b-a8d6-426b-a462-357c0b33ed58/` | 1 page |
| `d94be6f4-4fc6-4789-a525-992014caa653/` | 1 page |
| `f9eba060-e8d2-48a3-8fa5-9c8d58655e9f/` | 1 page |

These feed into `_phase2_ocr_content.json` and ultimately the per-PDF
`_pdf_knowledge_<uuid>.json` files one level up.
