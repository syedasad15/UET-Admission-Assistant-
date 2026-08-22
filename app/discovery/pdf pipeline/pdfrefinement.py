# import json
# from pathlib import Path


# # ============================================================
# # UET CHATBOT — PDF REFINEMENT
# # ============================================================
# #
# # Input:
# #   data/inventory/admission/_pdf_knowledge_chunks_filtered.json
# #   (1284 chunks across 23 unique PDFs, after stale-document
# #   exclusion)
# #
# # Output:
# #   data/inventory/admission/_pdf_knowledge_final.json
# #
# # Purpose:
# #   The filtered chunk set still carries generic titles
# #   ("Download") and no topic/book assignment for most PDFs.
# #   This script is the PDF-side equivalent of bookbuilder.py:
# #   it applies the final, manually-reviewed decision for every
# #   remaining PDF —
# #
# #       - a real title
# #       - a book (topic category)
# #       - KEEP / EXCLUDE
# #       - TEMPORAL flag, where the content will go stale once
# #         a newer merit list / schedule is published
# #       - a manual text override, for the one PDF (d3f4869b)
# #         whose OCR came out too garbled to trust numerically
# #
# #   so the chatbot only ever answers from clean, correctly
# #   labelled, non-duplicate content.
# #
# # ============================================================


# # ============================================================
# # PROJECT PATH
# # ============================================================

# PROJECT_ROOT = Path(r"D:\UET Chatbot")

# DATA_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "inventory"
#     / "admission"
# )

# INPUT_FILE = DATA_DIR / "_pdf_knowledge_chunks_filtered.json"

# OUTPUT_FILE = DATA_DIR / "_pdf_knowledge_final.json"


# # ============================================================
# # DOCUMENT DECISIONS
# # ============================================================
# #
# # Keyed by pdf_file (the canonical local filename, exactly as
# # it appears on each chunk). Covers every PDF still present in
# # the filtered chunk set (23 total: 3 already-known KEEPs from
# # pdfreviewer.py + the 20 that needed title/category review).
# #
# # decision:
# #   KEEP    -> title/book applied, chunks retained
# #   EXCLUDE -> all chunks for this PDF are dropped
# #
# # temporal:
# #   True -> content is correct today but will go stale once a
# #   newer version is published (merit lists, revised
# #   schedules). Kept for now, flagged so a future refresh step
# #   can find it quickly.
# #
# # ============================================================

# DOCUMENT_DECISIONS = {

#     # ------------------------------------------------------
#     # Already-known documents (from pdfreviewer.py) — carried
#     # forward here so this script is the single source of
#     # truth for the final PDF book.
#     # ------------------------------------------------------

#     "MS-2026-1_0475d05f-a54f-450c-8383-6733814b433d.pdf": {
#         "decision": "KEEP",
#         "title": "MS / M.Phil / PhD Prospectus (Fall 2026)",
#         "book": "programs",
#     },

#     "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf": {
#         "decision": "KEEP",
#         "title": "Undergraduate Prospectus (Fall 2026)",
#         "book": "programs",
#     },

#     "admission-guide.pdf": {
#         "decision": "KEEP",
#         "title": "Admission Guide (Undergraduate, Fall 2026)",
#         "book": "admission_process",
#     },

#     # ------------------------------------------------------
#     # Reviewed in this stage (Phase 5e)
#     # ------------------------------------------------------

#     "6e353ce3-0f77-4d45-8747-2fdf9cfb90e6.pdf": {
#         "decision": "KEEP",
#         "title": (
#             "Undertaking — Admission Cancellation & Refund "
#             "Policy"
#         ),
#         "book": "admission_process",
#     },

#     "a8090b4d-2448-42e7-999a-a948573c7f3b.pdf": {
#         "decision": "KEEP",
#         "title": "Closing Merit Report — Merit List 2 (UG Fall 2026)",
#         "book": "admission_process",
#         "temporal": True,
#         "temporal_note": (
#             "Will be superseded once a later merit list is "
#             "published for this admission cycle."
#         ),
#     },

#     "bc079c7a-2bcf-4ca6-81bc-f15b9eb23b64.pdf": {
#         "decision": "KEEP",
#         "title": "Undergraduate Admission Process Schedule (Fall 2026)",
#         "book": "admission_process",
#     },

#     "4808e934-e5dc-4a3d-b53e-88e72d948ac0.pdf": {
#         "decision": "KEEP",
#         "title": "Fee Structure — Undergraduate Programs",
#         "book": "fees",
#     },

#     "91a868d2-dfcb-4974-af21-453f6b6853d0.pdf": {
#         "decision": "KEEP",
#         "title": "Minimum Aggregate Report — Merit List 1 (UG Fall 2026)",
#         "book": "eligibility",
#         "temporal": True,
#         "temporal_note": (
#             "Will be superseded once a later merit list is "
#             "published for this admission cycle."
#         ),
#     },

#     "a9f1df72-962b-4b2e-aebe-bd624d917953.pdf": {
#         "decision": "KEEP",
#         "title": "Affidavit for Non-Muslim Candidates (NM Category)",
#         "book": "eligibility",
#     },

#     "7faf8b8c-f607-43dd-ab53-6c5e261f705b.pdf": {
#         "decision": "KEEP",
#         "title": "Specimen Income Certificate (Self-Employed)",
#         "book": "eligibility",
#     },

#     "f9eba060-e8d2-48a3-8fa5-9c8d58655e9f.pdf": {
#         "decision": "EXCLUDE",
#         "note": (
#             "Undergraduate Admissions Highlights Flyer — "
#             "promotional content, no information not already "
#             "covered by the prospectus/schedule/fee documents."
#         ),
#     },

#     "90166bac-e657-4cee-890f-c34aee652b6c.pdf": {
#         "decision": "EXCLUDE",
#         "note": (
#             "Admission Guide cover + schedule — substantially "
#             "duplicates admission-guide.pdf (cover/intro) and "
#             "bc079c7a (schedule). Byte-different from both "
#             "(different render/encoding), so SHA-256 dedup did "
#             "not catch it, but the content is redundant."
#         ),
#     },

#     "14a1476c-9fc8-4728-96a7-3c181b0e9c81.pdf": {
#         "decision": "KEEP",
#         "title": (
#             "Form VIII — Overseas Pakistanis Certificate "
#             "(S/SI Category)"
#         ),
#         "book": "eligibility",
#     },

#     "dee8172b-0888-4be5-84a3-7b2c3005c880.pdf": {
#         "decision": "KEEP",
#         "title": (
#             "Form V & VI — Employee / Unmarried Status "
#             "Certificates"
#         ),
#         "book": "eligibility",
#     },

#     "30097787-4e76-496e-8e19-7b99fdf17347.pdf": {
#         "decision": "KEEP",
#         "title": (
#             "Undertaking — IBCC Equivalence Certificate "
#             "(Foreign Students)"
#         ),
#         "book": "international_admissions",
#     },

#     "098eca99-9df5-4ef9-81f0-275861ad27ac.pdf": {
#         "decision": "KEEP",
#         "title": "Application Form — Admission by Migration (Full)",
#         "book": "admission_process",
#     },

#     "937243bf-044d-422e-b0f0-c32b36e04f7d.pdf": {
#         "decision": "KEEP",
#         "title": "Application Form — Migration (Short)",
#         "book": "admission_process",
#     },

#     "c8856fd5-733e-46c8-8271-1ff78cdb9ceb.pdf": {
#         "decision": "EXCLUDE",
#         "note": (
#             "MSc/M.Phil Admissions Highlights Flyer — "
#             "promotional content, superseded by the MS/M.Phil "
#             "prospectus and fee structure documents."
#         ),
#     },

#     "d3f4869b-a8d6-426b-a462-357c0b33ed58.pdf": {
#         "decision": "KEEP",
#         "title": "MS / M.Phil Fee Structure (Fall 2026)",
#         "book": "fees",
#         "manual_override": True,
#         "manual_override_reason": (
#             "OCR output for this table was too garbled to trust "
#             "numerically (e.g. '6Z,200', '9WeQ'). Replaced with "
#             "a single manually transcribed and human-verified "
#             "chunk instead of the 3 OCR chunks."
#         ),
#     },

#     "d94be6f4-4fc6-4789-a525-992014caa653.pdf": {
#         "decision": "EXCLUDE",
#         "note": (
#             "PhD Admissions Highlights Flyer — promotional "
#             "content, superseded by the prospectus and fee "
#             "structure documents."
#         ),
#     },

#     "010ddcc2-6039-4d0c-8cff-4bd4b6131ab1.pdf": {
#         "decision": "KEEP",
#         "title": "Declaration Form & Biodata Card",
#         "book": "eligibility",
#     },

#     "104495c8-1fd5-4476-9721-66a4d5b653dd.pdf": {
#         "decision": "KEEP",
#         "title": "Form III & IV — Domicile / Residency Certificates",
#         "book": "eligibility",
#     },

#     "429cada0-b8a1-4b15-8c3b-392d9a4f1d50.pdf": {
#         "decision": "KEEP",
#         "title": "Postgraduate Subject Test Schedule (Fall 2026, Revised)",
#         "book": "deadlines",
#     },
# }


# # ============================================================
# # MANUAL OVERRIDE TEXT — d3f4869b (MS/M.Phil Fee Structure)
# # ============================================================
# #
# # Transcribed by hand from the source PDF page and confirmed
# # by the project owner (including the easily-misread 4,430
# # figure in the PhD table). Replaces the 3 garbled OCR chunks
# # for this document.
# #
# # ============================================================

# D3F4869B_CORRECTED_TEXT = """\
# FEE AND EXPENSES

# REGULAR M.S / M.Sc / M.Phil STUDENT'S FEE STRUCTURE FOR \
# SESSION 2026 Fall - Morning / Evening

# Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
# 4th Semester | 5th Semester | 6th Semester
# Admission Fee | 11,980 | - | - | - | - | -
# Tuition Fee Semester Wise | 67,200 | 67,200 | 75,270 | 75,270 \
# | 84,300 | 84,300
# Facilities Charges | 7,220 | 7,220 | 8,090 | 8,090 | 9,060 | \
# 9,060
# Examination Charges | 1,350 | 1,350 | 1,510 | 1,510 | 1,690 | \
# 1,690
# Miscellaneous Charges | 16,790 | 3,530 | 3,530 | 3,530 | \
# 3,530 | 3,530
# Tuition Fee Semester Wise (Total) | 104,540 | 79,300 | \
# 88,400 | 88,400 | 98,580 | 98,580

# PH.D STUDENT'S FEE STRUCTURE FOR SESSION 2026 FALL
# (With 50% waiver in admission charges & 30% waiver in \
# semester tuition fee)

# Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
# 4th Semester | 5th Semester | 6th Semester
# Admission Fee | 5,990 (after 50% discount) | - | - | - | - | -
# Tuition Fee Semester Wise | 47,040 | 47,040 | 52,690 | 52,690 \
# | 59,010 | 59,010
# Facilities Charges | 7,220 | 7,220 | 8,090 | 8,090 | 9,060 | \
# 9,060
# Examination Charges | 1,350 | 1,350 | 1,510 | 1,510 | 1,690 | \
# 1,690
# Miscellaneous Charges | 16,790 | 3,530 | 3,950 | 3,950 | \
# 4,430 | 4,430
# 30% Discounted Tuition Fee Semester Wise (Total) | 78,390 | \
# 59,140 | 66,240 | 66,240 | 74,190 | 74,190

# WEEKEND FEE STRUCTURE FOR SESSION 2026 FALL FOR M.S / M.SC / \
# M.PHIL / M.B.A

# Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
# 4th Semester | 5th Semester | 6th Semester
# Admission Fee | 13,370 | - | - | - | - | -
# Tuition Fee Semester Wise | 100,800 | 100,800 | 100,800 | \
# 50,400 | 50,400 | 50,400
# Miscellaneous Charges | 26,980 | 11,110 | 11,110 | 11,110 | \
# 11,110 | 11,110
# First Semester Weekend Fee (Total) | 141,150 | 111,910 | \
# 111,910 | 61,510 | 61,510 | 61,510

# NOTE:
# The university reduced 50% Ph.D. admission charges and 30% \
# tuition fee waiver as research support scholarship to all \
# graduates admitted to Ph.D. programs (from Spring 2026 \
# onward). The Ph.D. students would be given preference for \
# appointment as teaching fellows at university.
# 25% discount in tuition fee for alumni of UET, Lahore, for \
# M.Sc / M.Phil / Masters / MS Programs.
# """


# # ============================================================
# # HELPERS
# # ============================================================

# def normalize(value):

#     if value is None:
#         return ""

#     return str(value).strip()


# def load_filtered_chunks():

#     if not INPUT_FILE.exists():

#         raise FileNotFoundError(
#             "\nFiltered PDF chunks file was not found:\n"
#             f"{INPUT_FILE}\n\n"
#             "Run the filtering stage first."
#         )

#     print()
#     print("Reading:")
#     print(INPUT_FILE)

#     with INPUT_FILE.open(
#         "r",
#         encoding="utf-8"
#     ) as file:

#         chunks = json.load(file)

#     if not isinstance(chunks, list):

#         raise ValueError(
#             "Expected _pdf_knowledge_chunks_filtered.json to "
#             "be a list of chunks."
#         )

#     return chunks


# # ============================================================
# # GROUP CHUNKS BY PDF
# # ============================================================

# def group_by_pdf(chunks):

#     groups = {}

#     for chunk in chunks:

#         pdf_file = normalize(chunk.get("pdf_file"))

#         groups.setdefault(pdf_file, []).append(chunk)

#     return groups


# # ============================================================
# # BUILD MANUAL OVERRIDE CHUNK
# # ============================================================

# def build_override_chunk(template_chunk, pdf_file, decision):

#     return {
#         "canonical_url": template_chunk.get("canonical_url", ""),
#         "canonical_title": decision["title"],
#         "sha256": template_chunk.get("sha256", ""),
#         "all_urls": template_chunk.get("all_urls", []),
#         "pdf_file": pdf_file,
#         "page": 1,
#         "chunk_index": 0,
#         "text": D3F4869B_CORRECTED_TEXT.strip(),
#         "source": "manual_correction",
#         "quality_flag": "manually_verified",
#         "title": decision["title"],
#         "book": decision["book"],
#     }


# # ============================================================
# # REFINE
# # ============================================================

# def refine(chunks):

#     groups = group_by_pdf(chunks)

#     final_chunks = []

#     excluded_documents = []

#     unknown_documents = []

#     temporal_documents = []

#     manual_overrides = []

#     for pdf_file, group in groups.items():

#         decision = DOCUMENT_DECISIONS.get(pdf_file)

#         if decision is None:

#             unknown_documents.append({
#                 "pdf_file": pdf_file,
#                 "chunk_count": len(group),
#             })

#             continue

#         if decision["decision"] == "EXCLUDE":

#             excluded_documents.append({
#                 "pdf_file": pdf_file,
#                 "chunk_count": len(group),
#                 "reason": decision.get("note", ""),
#             })

#             continue

#         # ------------------------------------------------
#         # Manual override — replace all chunks for this PDF
#         # with a single hand-verified chunk.
#         # ------------------------------------------------

#         if decision.get("manual_override"):

#             override_chunk = build_override_chunk(
#                 group[0],
#                 pdf_file,
#                 decision,
#             )

#             final_chunks.append(override_chunk)

#             manual_overrides.append({
#                 "pdf_file": pdf_file,
#                 "original_chunk_count": len(group),
#                 "replacement_chunk_count": 1,
#                 "reason": decision.get(
#                     "manual_override_reason",
#                     "",
#                 ),
#             })

#             continue

#         # ------------------------------------------------
#         # Normal KEEP — apply title/book to every chunk.
#         # ------------------------------------------------

#         is_temporal = decision.get("temporal", False)

#         if is_temporal:

#             temporal_documents.append({
#                 "pdf_file": pdf_file,
#                 "title": decision["title"],
#                 "note": decision.get("temporal_note", ""),
#             })

#         for chunk in group:

#             enriched = {
#                 **chunk,
#                 "title": decision["title"],
#                 "book": decision["book"],
#                 "temporal": is_temporal,
#             }

#             final_chunks.append(enriched)

#     return (
#         final_chunks,
#         excluded_documents,
#         unknown_documents,
#         temporal_documents,
#         manual_overrides,
#     )


# # ============================================================
# # VALIDATION
# # ============================================================

# def validate(
#     input_chunks,
#     final_chunks,
#     excluded_documents,
#     unknown_documents,
# ):

#     errors = []

#     if unknown_documents:

#         names = ", ".join(
#             doc["pdf_file"] for doc in unknown_documents
#         )

#         errors.append(
#             "Document(s) present in filtered chunks but "
#             f"missing from DOCUMENT_DECISIONS: {names}"
#         )

#     input_pdf_files = {
#         chunk.get("pdf_file", "")
#         for chunk in input_chunks
#     }

#     decided_pdf_files = set(DOCUMENT_DECISIONS.keys())

#     missing_from_decisions = input_pdf_files - decided_pdf_files

#     if missing_from_decisions:

#         errors.append(
#             "Document(s) with chunks in input but no entry in "
#             f"DOCUMENT_DECISIONS: {missing_from_decisions}"
#         )

#     for chunk in final_chunks:

#         if not chunk.get("text", "").strip():

#             errors.append(
#                 "Final chunk has empty text: "
#                 f"{chunk.get('pdf_file')} "
#                 f"page {chunk.get('page')}"
#             )

#         if not chunk.get("book"):

#             errors.append(
#                 "Final chunk missing 'book': "
#                 f"{chunk.get('pdf_file')} "
#                 f"page {chunk.get('page')}"
#             )

#         if not chunk.get("title"):

#             errors.append(
#                 "Final chunk missing 'title': "
#                 f"{chunk.get('pdf_file')} "
#                 f"page {chunk.get('page')}"
#             )

#     excluded_pdf_files = {
#         doc["pdf_file"] for doc in excluded_documents
#     }

#     leaked = excluded_pdf_files & {
#         chunk.get("pdf_file", "") for chunk in final_chunks
#     }

#     if leaked:

#         errors.append(
#             f"Excluded document(s) still present in output: "
#             f"{leaked}"
#         )

#     return errors


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 70)
#     print(
#         "UET ADMISSION — PDF REFINEMENT"
#     )
#     print("=" * 70)

#     chunks = load_filtered_chunks()

#     print()
#     print(
#         f"Input chunks: {len(chunks)}"
#     )

#     input_pdf_count = len({
#         chunk.get("pdf_file", "")
#         for chunk in chunks
#     })

#     print(
#         f"Input PDFs: {input_pdf_count}"
#     )

#     # --------------------------------------------------------
#     # Refine
#     # --------------------------------------------------------

#     (
#         final_chunks,
#         excluded_documents,
#         unknown_documents,
#         temporal_documents,
#         manual_overrides,
#     ) = refine(chunks)

#     # --------------------------------------------------------
#     # Report
#     # --------------------------------------------------------

#     print()
#     print("=" * 70)
#     print(
#         "EXCLUDED DOCUMENTS"
#     )
#     print("=" * 70)

#     if not excluded_documents:

#         print("None")

#     else:

#         for doc in excluded_documents:

#             print()
#             print(
#                 f" — {doc['pdf_file']} "
#                 f"({doc['chunk_count']} chunks removed)"
#             )

#             print(
#                 f"   Reason: {doc['reason']}"
#             )

#     print()
#     print("=" * 70)
#     print(
#         "MANUAL OVERRIDES"
#     )
#     print("=" * 70)

#     if not manual_overrides:

#         print("None")

#     else:

#         for doc in manual_overrides:

#             print()
#             print(
#                 f" — {doc['pdf_file']}"
#             )

#             print(
#                 f"   {doc['original_chunk_count']} OCR chunks "
#                 f"-> {doc['replacement_chunk_count']} manual "
#                 f"chunk"
#             )

#             print(
#                 f"   Reason: {doc['reason']}"
#             )

#     print()
#     print("=" * 70)
#     print(
#         "TEMPORAL DOCUMENTS (kept, flagged for future refresh)"
#     )
#     print("=" * 70)

#     if not temporal_documents:

#         print("None")

#     else:

#         for doc in temporal_documents:

#             print()
#             print(
#                 f" — {doc['title']} ({doc['pdf_file']})"
#             )

#             print(
#                 f"   {doc['note']}"
#             )

#     if unknown_documents:

#         print()
#         print("=" * 70)
#         print(
#             "UNDECIDED DOCUMENTS (no entry in DOCUMENT_DECISIONS)"
#         )
#         print("=" * 70)

#         for doc in unknown_documents:

#             print()
#             print(
#                 f" — {doc['pdf_file']} "
#                 f"({doc['chunk_count']} chunks)"
#             )

#     # --------------------------------------------------------
#     # Summary
#     # --------------------------------------------------------

#     final_pdf_count = len({
#         chunk.get("pdf_file", "")
#         for chunk in final_chunks
#     })

#     books = {}

#     for chunk in final_chunks:

#         books[chunk["book"]] = books.get(chunk["book"], 0) + 1

#     print()
#     print("=" * 70)
#     print(
#         "REFINEMENT RESULT"
#     )
#     print("=" * 70)

#     print()
#     print(
#         f"  Input chunks       : {len(chunks)}"
#     )

#     print(
#         f"  Final chunks       : {len(final_chunks)}"
#     )

#     print(
#         f"  Input PDFs         : {input_pdf_count}"
#     )

#     print(
#         f"  Final PDFs         : {final_pdf_count}"
#     )

#     print(
#         f"  Excluded PDFs      : {len(excluded_documents)}"
#     )

#     print(
#         f"  Manual overrides   : {len(manual_overrides)}"
#     )

#     print(
#         f"  Temporal documents : {len(temporal_documents)}"
#     )

#     print()
#     print(
#         "  Chunks per book:"
#     )

#     for book, count in sorted(
#         books.items(),
#         key=lambda item: -item[1],
#     ):

#         print(
#             f"    {book:<28} : {count}"
#         )

#     # --------------------------------------------------------
#     # Validate
#     # --------------------------------------------------------

#     print()
#     print("=" * 70)
#     print(
#         "VALIDATION"
#     )
#     print("=" * 70)

#     validation_errors = validate(
#         chunks,
#         final_chunks,
#         excluded_documents,
#         unknown_documents,
#     )

#     if validation_errors:

#         print(
#             "INVALID"
#         )

#         for error in validation_errors:

#             print(
#                 f"ERROR: {error}"
#             )

#         raise ValueError(
#             "PDF refinement validation failed."
#         )

#     else:

#         print(
#             "VALID"
#         )

#     # --------------------------------------------------------
#     # Save
#     # --------------------------------------------------------

#     output = {
#         "source": "UET Admissions Portal",
#         "stage": "pdf_refinement",
#         "input_file": str(INPUT_FILE),
#         "output_file": str(OUTPUT_FILE),
#         "counts": {
#             "input_chunks": len(chunks),
#             "final_chunks": len(final_chunks),
#             "input_pdfs": input_pdf_count,
#             "final_pdfs": final_pdf_count,
#             "excluded_pdfs": len(excluded_documents),
#             "manual_overrides": len(manual_overrides),
#             "temporal_documents": len(temporal_documents),
#         },
#         "books": books,
#         "excluded_documents": excluded_documents,
#         "manual_overrides": manual_overrides,
#         "temporal_documents": temporal_documents,
#         "chunks": final_chunks,
#     }

#     DATA_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     with OUTPUT_FILE.open(
#         "w",
#         encoding="utf-8",
#     ) as file:

#         json.dump(
#             output,
#             file,
#             indent=2,
#             ensure_ascii=False,
#         )

#     print()
#     print("=" * 70)
#     print(
#         "SAVED"
#     )
#     print("=" * 70)

#     print()
#     print(
#         OUTPUT_FILE
#     )

#     print()


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":
#     main()

import json
from pathlib import Path


# ============================================================
# UET CHATBOT — PDF REFINEMENT
# ============================================================
#
# Input:
#   data/inventory/admission/_pdf_knowledge_chunks_filtered.json
#   (1284 chunks across 23 unique PDFs, after stale-document
#   exclusion)
#
# Output:
#   data/inventory/admission/_pdf_knowledge_final.json
#
# Purpose:
#   The filtered chunk set still carries generic titles
#   ("Download") and no topic/book assignment for most PDFs.
#   This script is the PDF-side equivalent of bookbuilder.py:
#   it applies the final, manually-reviewed decision for every
#   remaining PDF —
#
#       - a real title
#       - a book (topic category)
#       - KEEP / EXCLUDE
#       - TEMPORAL flag, where the content will go stale once
#         a newer merit list / schedule is published
#       - a manual text override, for the one PDF (d3f4869b)
#         whose OCR came out too garbled to trust numerically
#
#   so the chatbot only ever answers from clean, correctly
#   labelled, non-duplicate content.
#
# ============================================================


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

INPUT_FILE = DATA_DIR / "_pdf_knowledge_chunks_filtered.json"

OUTPUT_FILE = DATA_DIR / "_pdf_knowledge_final.json"


# ============================================================
# DOCUMENT DECISIONS
# ============================================================
#
# Keyed by pdf_file (the canonical local filename, exactly as
# it appears on each chunk). Covers every PDF still present in
# the filtered chunk set (23 total: 3 already-known KEEPs from
# pdfreviewer.py + the 20 that needed title/category review).
#
# decision:
#   KEEP    -> title/book applied, chunks retained
#   EXCLUDE -> all chunks for this PDF are dropped
#
# temporal:
#   True -> content is correct today but will go stale once a
#   newer version is published (merit lists, revised
#   schedules). Kept for now, flagged so a future refresh step
#   can find it quickly.
#
# ============================================================

DOCUMENT_DECISIONS = {

    # ------------------------------------------------------
    # Already-known documents (from pdfreviewer.py) — carried
    # forward here so this script is the single source of
    # truth for the final PDF book.
    # ------------------------------------------------------

    "MS-2026-1_0475d05f-a54f-450c-8383-6733814b433d.pdf": {
        "decision": "KEEP",
        "title": "MS / M.Phil / PhD Prospectus (Fall 2026)",
        "book": "programs",
    },

    "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf": {
        "decision": "KEEP",
        "title": "Undergraduate Prospectus (Fall 2026)",
        "book": "programs",
    },

    "admission-guide.pdf": {
        "decision": "KEEP",
        "title": "Admission Guide (Undergraduate, Fall 2026)",
        "book": "admission_process",
    },

    # ------------------------------------------------------
    # Reviewed in this stage (Phase 5e)
    # ------------------------------------------------------

    "6e353ce3-0f77-4d45-8747-2fdf9cfb90e6.pdf": {
        "decision": "KEEP",
        "title": (
            "Undertaking — Admission Cancellation & Refund "
            "Policy"
        ),
        "book": "admission_process",
    },

    "a8090b4d-2448-42e7-999a-a948573c7f3b.pdf": {
        "decision": "KEEP",
        "title": "Closing Merit Report — Merit List 2 (UG Fall 2026)",
        "book": "admission_process",
        "temporal": True,
        "temporal_note": (
            "Will be superseded once a later merit list is "
            "published for this admission cycle."
        ),
    },

    "bc079c7a-2bcf-4ca6-81bc-f15b9eb23b64.pdf": {
        "decision": "KEEP",
        "title": "Undergraduate Admission Process Schedule (Fall 2026)",
        "book": "admission_process",
    },

    "4808e934-e5dc-4a3d-b53e-88e72d948ac0.pdf": {
        "decision": "KEEP",
        "title": "Fee Structure — Undergraduate Programs",
        "book": "fees",
    },

    "91a868d2-dfcb-4974-af21-453f6b6853d0.pdf": {
        "decision": "KEEP",
        "title": "Minimum Aggregate Report — Merit List 1 (UG Fall 2026)",
        "book": "eligibility",
        "temporal": True,
        "temporal_note": (
            "Will be superseded once a later merit list is "
            "published for this admission cycle."
        ),
    },

    "a9f1df72-962b-4b2e-aebe-bd624d917953.pdf": {
        "decision": "KEEP",
        "title": "Affidavit for Non-Muslim Candidates (NM Category)",
        "book": "eligibility",
    },

    "7faf8b8c-f607-43dd-ab53-6c5e261f705b.pdf": {
        "decision": "KEEP",
        "title": "Specimen Income Certificate (Self-Employed)",
        "book": "eligibility",
    },

    "f9eba060-e8d2-48a3-8fa5-9c8d58655e9f.pdf": {
        "decision": "EXCLUDE",
        "note": (
            "Undergraduate Admissions Highlights Flyer — "
            "promotional content, no information not already "
            "covered by the prospectus/schedule/fee documents."
        ),
    },

    "90166bac-e657-4cee-890f-c34aee652b6c.pdf": {
        "decision": "EXCLUDE",
        "note": (
            "Admission Guide cover + schedule — substantially "
            "duplicates admission-guide.pdf (cover/intro) and "
            "bc079c7a (schedule). Byte-different from both "
            "(different render/encoding), so SHA-256 dedup did "
            "not catch it, but the content is redundant."
        ),
    },

    "14a1476c-9fc8-4728-96a7-3c181b0e9c81.pdf": {
        "decision": "KEEP",
        "title": (
            "Form VIII — Overseas Pakistanis Certificate "
            "(S/SI Category)"
        ),
        "book": "eligibility",
    },

    "dee8172b-0888-4be5-84a3-7b2c3005c880.pdf": {
        "decision": "KEEP",
        "title": (
            "Form V & VI — Employee / Unmarried Status "
            "Certificates"
        ),
        "book": "eligibility",
    },

    "30097787-4e76-496e-8e19-7b99fdf17347.pdf": {
        "decision": "KEEP",
        "title": (
            "Undertaking — IBCC Equivalence Certificate "
            "(Foreign Students)"
        ),
        "book": "international_admissions",
    },

    "098eca99-9df5-4ef9-81f0-275861ad27ac.pdf": {
        "decision": "KEEP",
        "title": "Application Form — Admission by Migration (Full)",
        "book": "admission_process",
    },

    "937243bf-044d-422e-b0f0-c32b36e04f7d.pdf": {
        "decision": "KEEP",
        "title": "Application Form — Migration (Short)",
        "book": "admission_process",
    },

    "c8856fd5-733e-46c8-8271-1ff78cdb9ceb.pdf": {
        "decision": "EXCLUDE",
        "note": (
            "MSc/M.Phil Admissions Highlights Flyer — "
            "promotional content, superseded by the MS/M.Phil "
            "prospectus and fee structure documents."
        ),
    },

    "d3f4869b-a8d6-426b-a462-357c0b33ed58.pdf": {
        "decision": "KEEP",
        "title": "MS / M.Phil Fee Structure (Fall 2026)",
        "book": "fees",
        "manual_override": True,
        "manual_override_reason": (
            "OCR output for this table was too garbled to trust "
            "numerically (e.g. '6Z,200', '9WeQ'). Replaced with "
            "a single manually transcribed and human-verified "
            "chunk instead of the 3 OCR chunks."
        ),
    },

    "d94be6f4-4fc6-4789-a525-992014caa653.pdf": {
        "decision": "EXCLUDE",
        "note": (
            "PhD Admissions Highlights Flyer — promotional "
            "content, superseded by the prospectus and fee "
            "structure documents."
        ),
    },

    "010ddcc2-6039-4d0c-8cff-4bd4b6131ab1.pdf": {
        "decision": "KEEP",
        "title": "Declaration Form & Biodata Card",
        "book": "eligibility",
    },

    "104495c8-1fd5-4476-9721-66a4d5b653dd.pdf": {
        "decision": "KEEP",
        "title": "Form III & IV — Domicile / Residency Certificates",
        "book": "eligibility",
    },

    "429cada0-b8a1-4b15-8c3b-392d9a4f1d50.pdf": {
        "decision": "KEEP",
        "title": "Postgraduate Subject Test Schedule (Fall 2026, Revised)",
        "book": "deadlines",
    },
}


# ============================================================
# MANUAL OVERRIDE TEXT — d3f4869b (MS/M.Phil Fee Structure)
# ============================================================
#
# Transcribed by hand from the source PDF page and confirmed
# by the project owner (including the easily-misread 4,430
# figure in the PhD table). Replaces the 3 garbled OCR chunks
# for this document.
#
# ============================================================

D3F4869B_CORRECTED_TEXT = """\
FEE AND EXPENSES

REGULAR M.S / M.Sc / M.Phil STUDENT'S FEE STRUCTURE FOR \
SESSION 2026 Fall - Morning / Evening

Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
4th Semester | 5th Semester | 6th Semester
Admission Fee | 11,980 | - | - | - | - | -
Tuition Fee Semester Wise | 67,200 | 67,200 | 75,270 | 75,270 \
| 84,300 | 84,300
Facilities Charges | 7,220 | 7,220 | 8,090 | 8,090 | 9,060 | \
9,060
Examination Charges | 1,350 | 1,350 | 1,510 | 1,510 | 1,690 | \
1,690
Miscellaneous Charges | 16,790 | 3,530 | 3,530 | 3,530 | \
3,530 | 3,530
Tuition Fee Semester Wise (Total) | 104,540 | 79,300 | \
88,400 | 88,400 | 98,580 | 98,580

PH.D STUDENT'S FEE STRUCTURE FOR SESSION 2026 FALL
(With 50% waiver in admission charges & 30% waiver in \
semester tuition fee)

Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
4th Semester | 5th Semester | 6th Semester
Admission Fee | 5,990 (after 50% discount) | - | - | - | - | -
Tuition Fee Semester Wise | 47,040 | 47,040 | 52,690 | 52,690 \
| 59,010 | 59,010
Facilities Charges | 7,220 | 7,220 | 8,090 | 8,090 | 9,060 | \
9,060
Examination Charges | 1,350 | 1,350 | 1,510 | 1,510 | 1,690 | \
1,690
Miscellaneous Charges | 16,790 | 3,530 | 3,950 | 3,950 | \
4,430 | 4,430
30% Discounted Tuition Fee Semester Wise (Total) | 78,390 | \
59,140 | 66,240 | 66,240 | 74,190 | 74,190

WEEKEND FEE STRUCTURE FOR SESSION 2026 FALL FOR M.S / M.SC / \
M.PHIL / M.B.A

Particulars | 1st Semester | 2nd Semester | 3rd Semester | \
4th Semester | 5th Semester | 6th Semester
Admission Fee | 13,370 | - | - | - | - | -
Tuition Fee Semester Wise | 100,800 | 100,800 | 100,800 | \
50,400 | 50,400 | 50,400
Miscellaneous Charges | 26,980 | 11,110 | 11,110 | 11,110 | \
11,110 | 11,110
First Semester Weekend Fee (Total) | 141,150 | 111,910 | \
111,910 | 61,510 | 61,510 | 61,510

NOTE:
The university reduced 50% Ph.D. admission charges and 30% \
tuition fee waiver as research support scholarship to all \
graduates admitted to Ph.D. programs (from Spring 2026 \
onward). The Ph.D. students would be given preference for \
appointment as teaching fellows at university.
25% discount in tuition fee for alumni of UET, Lahore, for \
M.Sc / M.Phil / Masters / MS Programs.
"""


# ============================================================
# PAGE OVERRIDES — UG-2026-1 Prospectus, Pages 11 & 12
# ============================================================
#
# The prospectus lists every undergraduate program by campus
# (page 11) and every affiliated institution (page 12) as one
# continuous enumerated list. The automatic chunker split that
# list mid-item across 3 chunks on page 11 and 2 on page 12,
# so a retrieval hit on any single chunk returned a truncated,
# sometimes misleading fragment of the list (verified: this
# caused genuinely inconsistent answers to "what BS programs
# does UET offer" across near-identical phrasings of the same
# question).
#
# Fix: replace those chunks with one clean, self-contained
# chunk per campus / per institution group, reconstructed by
# hand from the actual page text (same text, just re-chunked
# on real boundaries instead of a fixed character count).
#
# Keyed by (pdf_file, page) -> list of chunk texts.
# ============================================================

UG_PROGRAMS_PAGE_11_CHUNKS = [
    (
        "Main Campus — Undergraduate Degree Programs "
        "(Fall 2026)\n\n"
        "Bachelor of Science (B.Sc.): Architectural "
        "Engineering, Artificial Intelligence, Automotive "
        "Engineering, Chemical Engineering, Civil Engineering, "
        "City and Regional Planning, Computer Engineering, "
        "Computer Science, Cyber Security, Data Science, "
        "Electrical Engineering, Environmental Engineering, "
        "Geological Engineering, Industrial and Manufacturing "
        "Engineering, Interior Design, Mechanical Engineering, "
        "Mechatronics and Control Engineering, Metallurgical "
        "and Materials Engineering, Mining Engineering, "
        "Petroleum and Gas Engineering, Polymer Engineering, "
        "Robotics and Intelligent Systems, Transportation "
        "Engineering, Software Engineering.\n\n"
        "Bachelor's degree: Architecture, Business Data "
        "Analytics, Business Administration, Business "
        "Analytics, Logistics and Supply Chain Management, "
        "Business and Information Technology, Environmental "
        "Science, Materials Science, Product and Industrial "
        "Design, Remote Sensing and GIS.\n\n"
        "Bachelor of Science (B.S.): Chemistry, Industrial "
        "Chemistry, Mathematics, Physics, Islamic Studies "
        "(Specialization in Computer Technology), English "
        "Language and Literature."
    ),
    (
        "New Campus, Kala Shah Kaku (KSK) — Undergraduate "
        "Degree Programs (Fall 2026)\n\n"
        "Bachelor of Science (B.Sc.): Biomedical Engineering, "
        "Artificial Intelligence, Computer Engineering "
        "(NCEAC), Computer Science, Chemical Engineering, "
        "Electrical Engineering, Energy Systems Management, "
        "Food Science and Bio-Technology, Mechanical "
        "Engineering, Software Engineering, Data Science, "
        "Cyber Security.\n\n"
        "Bachelor's degree: Business Administration, Business "
        "and Information Technology.\n\n"
        "Bachelor of Science (B.S.): Mathematics."
    ),
    (
        "Faisalabad Campus — Undergraduate Degree Programs "
        "(Fall 2026)\n\n"
        "Bachelor of Science (B.Sc.): Chemical Engineering, "
        "Computer Engineering (NCEAC), Computer Science, "
        "Electrical Engineering, Mechatronics & Control "
        "Engineering, Textile Engineering, Data Science, Cyber "
        "Security.\n\n"
        "Bachelor of Science (B.S.): Industrial Chemistry."
    ),
    (
        "Rachna College of Engineering & Technology, "
        "Gujranwala — Undergraduate Degree Programs "
        "(Fall 2026)\n\n"
        "Bachelor of Science (B.Sc.): Computer Science, "
        "Computer Engineering (NCEAC), Electrical Engineering, "
        "Mechanical Engineering."
    ),
    (
        "Narowal Campus — Undergraduate Degree Programs "
        "(Fall 2026)\n\n"
        "Bachelor of Science (B.Sc.): Architecture, Biomedical "
        "Engineering, Civil Engineering, Computer Engineering "
        "(NCEAC), Computer Science, Electrical Engineering, "
        "Mechanical Engineering.\n\n"
        "Bachelor's degree: Business Information Technology."
    ),
]

UG_PROGRAMS_PAGE_12_CHUNKS = [
    (
        "Affiliated Institutions and Programs Offered "
        "(Fall 2026)\n\n"
        "1. NFC Institute of Engineering and Fertilizer "
        "Research, Faisalabad: B.Sc. Chemical Engineering, "
        "B.Sc. Civil Engineering, B.Sc. Electrical "
        "Engineering, B.Sc. Mechanical Engineering, B.Sc. "
        "Computer Engineering, B.Sc. Computer Science, B.Sc. "
        "Cyber Security, B.Sc. Artificial Intelligence, B.Sc. "
        "Data Science, Bachelor of Business Administration, "
        "Bachelor of Business Administration (Information "
        "Technology).\n\n"
        "2. Government College of Technology, Railway Road, "
        "Lahore: B.Sc. Mechanical Engineering Technology.\n\n"
        "3. Government College of Technology, Faisalabad: "
        "B.Sc. Electrical Engineering Technology.\n\n"
        "4. Sharif College of Engineering & Technology, "
        "Raiwind Road, Lahore: B.Sc. Electrical Engineering, "
        "B.Sc. Computer Science, B.Sc. Robotics & "
        "Intelligence, B.Sc. Data Science, B.Sc. Artificial "
        "Intelligence.\n\n"
        "5. Quaid-e-Azam College of Engineering and "
        "Technology, Sahiwal: B.Sc. Civil Engineering, B.Sc. "
        "Mechanical Engineering, B.Sc. Electrical Engineering, "
        "B.Sc. Computer Science.\n\n"
        "6. Swedish College of Engineering & Technology, Rahim "
        "Yar Khan: B.Sc. Civil Engineering, B.Sc. Mechanical "
        "Engineering, B.Sc. Computer Science, B.Sc. Software "
        "Engineering, B.Sc. Cyber Security, B.Sc. Artificial "
        "Intelligence.\n\n"
        "7. Government Swedish Pakistani College of "
        "Technology, Gujrat: B.Sc. Mechanical Engineering "
        "Technology."
    ),
]

PAGE_OVERRIDES = {
    (
        "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf",
        11,
    ): UG_PROGRAMS_PAGE_11_CHUNKS,
    (
        "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf",
        12,
    ): UG_PROGRAMS_PAGE_12_CHUNKS,
}


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def load_filtered_chunks():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nFiltered PDF chunks file was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run the filtering stage first."
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        chunks = json.load(file)

    if not isinstance(chunks, list):

        raise ValueError(
            "Expected _pdf_knowledge_chunks_filtered.json to "
            "be a list of chunks."
        )

    return chunks


# ============================================================
# GROUP CHUNKS BY PDF
# ============================================================

def group_by_pdf(chunks):

    groups = {}

    for chunk in chunks:

        pdf_file = normalize(chunk.get("pdf_file"))

        groups.setdefault(pdf_file, []).append(chunk)

    return groups


# ============================================================
# BUILD MANUAL OVERRIDE CHUNK
# ============================================================

def build_override_chunk(template_chunk, pdf_file, decision):

    return {
        "canonical_url": template_chunk.get("canonical_url", ""),
        "canonical_title": decision["title"],
        "sha256": template_chunk.get("sha256", ""),
        "all_urls": template_chunk.get("all_urls", []),
        "pdf_file": pdf_file,
        "page": 1,
        "chunk_index": 0,
        "text": D3F4869B_CORRECTED_TEXT.strip(),
        "source": "manual_correction",
        "quality_flag": "manually_verified",
        "title": decision["title"],
        "book": decision["book"],
    }


def build_page_override_chunks(
    template_chunk,
    pdf_file,
    page,
    texts,
    decision,
):

    is_temporal = decision.get("temporal", False)

    return [
        {
            "canonical_url": template_chunk.get(
                "canonical_url", ""
            ),
            "canonical_title": decision["title"],
            "sha256": template_chunk.get("sha256", ""),
            "all_urls": template_chunk.get("all_urls", []),
            "pdf_file": pdf_file,
            "page": page,
            "chunk_index": chunk_index,
            "text": text.strip(),
            "source": "manual_correction",
            "quality_flag": "manually_re-chunked",
            "title": decision["title"],
            "book": decision["book"],
            "temporal": is_temporal,
        }
        for chunk_index, text in enumerate(texts)
    ]


# ============================================================
# REFINE
# ============================================================

def refine(chunks):

    groups = group_by_pdf(chunks)

    final_chunks = []

    excluded_documents = []

    unknown_documents = []

    temporal_documents = []

    manual_overrides = []

    page_overrides_applied = []

    for pdf_file, group in groups.items():

        decision = DOCUMENT_DECISIONS.get(pdf_file)

        if decision is None:

            unknown_documents.append({
                "pdf_file": pdf_file,
                "chunk_count": len(group),
            })

            continue

        if decision["decision"] == "EXCLUDE":

            excluded_documents.append({
                "pdf_file": pdf_file,
                "chunk_count": len(group),
                "reason": decision.get("note", ""),
            })

            continue

        # ------------------------------------------------
        # Manual override — replace all chunks for this PDF
        # with a single hand-verified chunk.
        # ------------------------------------------------

        if decision.get("manual_override"):

            override_chunk = build_override_chunk(
                group[0],
                pdf_file,
                decision,
            )

            final_chunks.append(override_chunk)

            manual_overrides.append({
                "pdf_file": pdf_file,
                "original_chunk_count": len(group),
                "replacement_chunk_count": 1,
                "reason": decision.get(
                    "manual_override_reason",
                    "",
                ),
            })

            continue

        # ------------------------------------------------
        # Normal KEEP — apply title/book to every chunk.
        # ------------------------------------------------

        is_temporal = decision.get("temporal", False)

        if is_temporal:

            temporal_documents.append({
                "pdf_file": pdf_file,
                "title": decision["title"],
                "note": decision.get("temporal_note", ""),
            })

        # ------------------------------------------------
        # Page-level overrides — some pages for this
        # document get replaced with hand re-chunked text
        # (e.g. an enumerated list that the automatic
        # chunker split mid-item); the rest of the
        # document's chunks are enriched normally.
        # ------------------------------------------------

        overridden_pages = {
            page
            for (doc, page) in PAGE_OVERRIDES
            if doc == pdf_file
        }

        for chunk in group:

            page = chunk.get("page")

            if page in overridden_pages:

                continue  # handled below, once per page

            enriched = {
                **chunk,
                "title": decision["title"],
                "book": decision["book"],
                "temporal": is_temporal,
            }

            final_chunks.append(enriched)

        for page in overridden_pages:

            texts = PAGE_OVERRIDES[(pdf_file, page)]

            original_chunks_on_page = [
                c for c in group if c.get("page") == page
            ]

            if not original_chunks_on_page:

                continue  # this document has no such page

            override_chunks = build_page_override_chunks(
                original_chunks_on_page[0],
                pdf_file,
                page,
                texts,
                decision,
            )

            final_chunks.extend(override_chunks)

            page_overrides_applied.append({
                "pdf_file": pdf_file,
                "page": page,
                "original_chunk_count": len(
                    original_chunks_on_page
                ),
                "replacement_chunk_count": len(
                    override_chunks
                ),
            })

    return (
        final_chunks,
        excluded_documents,
        unknown_documents,
        temporal_documents,
        manual_overrides,
        page_overrides_applied,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate(
    input_chunks,
    final_chunks,
    excluded_documents,
    unknown_documents,
):

    errors = []

    if unknown_documents:

        names = ", ".join(
            doc["pdf_file"] for doc in unknown_documents
        )

        errors.append(
            "Document(s) present in filtered chunks but "
            f"missing from DOCUMENT_DECISIONS: {names}"
        )

    input_pdf_files = {
        chunk.get("pdf_file", "")
        for chunk in input_chunks
    }

    decided_pdf_files = set(DOCUMENT_DECISIONS.keys())

    missing_from_decisions = input_pdf_files - decided_pdf_files

    if missing_from_decisions:

        errors.append(
            "Document(s) with chunks in input but no entry in "
            f"DOCUMENT_DECISIONS: {missing_from_decisions}"
        )

    for chunk in final_chunks:

        if not chunk.get("text", "").strip():

            errors.append(
                "Final chunk has empty text: "
                f"{chunk.get('pdf_file')} "
                f"page {chunk.get('page')}"
            )

        if not chunk.get("book"):

            errors.append(
                "Final chunk missing 'book': "
                f"{chunk.get('pdf_file')} "
                f"page {chunk.get('page')}"
            )

        if not chunk.get("title"):

            errors.append(
                "Final chunk missing 'title': "
                f"{chunk.get('pdf_file')} "
                f"page {chunk.get('page')}"
            )

    excluded_pdf_files = {
        doc["pdf_file"] for doc in excluded_documents
    }

    leaked = excluded_pdf_files & {
        chunk.get("pdf_file", "") for chunk in final_chunks
    }

    if leaked:

        errors.append(
            f"Excluded document(s) still present in output: "
            f"{leaked}"
        )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PDF REFINEMENT"
    )
    print("=" * 70)

    chunks = load_filtered_chunks()

    print()
    print(
        f"Input chunks: {len(chunks)}"
    )

    input_pdf_count = len({
        chunk.get("pdf_file", "")
        for chunk in chunks
    })

    print(
        f"Input PDFs: {input_pdf_count}"
    )

    # --------------------------------------------------------
    # Refine
    # --------------------------------------------------------

    (
        final_chunks,
        excluded_documents,
        unknown_documents,
        temporal_documents,
        manual_overrides,
        page_overrides_applied,
    ) = refine(chunks)

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "EXCLUDED DOCUMENTS"
    )
    print("=" * 70)

    if not excluded_documents:

        print("None")

    else:

        for doc in excluded_documents:

            print()
            print(
                f" — {doc['pdf_file']} "
                f"({doc['chunk_count']} chunks removed)"
            )

            print(
                f"   Reason: {doc['reason']}"
            )

    print()
    print("=" * 70)
    print(
        "MANUAL OVERRIDES"
    )
    print("=" * 70)

    if not manual_overrides:

        print("None")

    else:

        for doc in manual_overrides:

            print()
            print(
                f" — {doc['pdf_file']}"
            )

            print(
                f"   {doc['original_chunk_count']} OCR chunks "
                f"-> {doc['replacement_chunk_count']} manual "
                f"chunk"
            )

            print(
                f"   Reason: {doc['reason']}"
            )

    print()
    print("=" * 70)
    print(
        "PAGE-LEVEL OVERRIDES (list re-chunked on real "
        "boundaries)"
    )
    print("=" * 70)

    if not page_overrides_applied:

        print("None")

    else:

        for item in page_overrides_applied:

            print()
            print(
                f" — {item['pdf_file']}, page {item['page']}"
            )

            print(
                f"   {item['original_chunk_count']} "
                f"auto-chunks -> "
                f"{item['replacement_chunk_count']} clean "
                f"chunks"
            )

    print()
    print("=" * 70)
    print(
        "TEMPORAL DOCUMENTS (kept, flagged for future refresh)"
    )
    print("=" * 70)

    if not temporal_documents:

        print("None")

    else:

        for doc in temporal_documents:

            print()
            print(
                f" — {doc['title']} ({doc['pdf_file']})"
            )

            print(
                f"   {doc['note']}"
            )

    if unknown_documents:

        print()
        print("=" * 70)
        print(
            "UNDECIDED DOCUMENTS (no entry in DOCUMENT_DECISIONS)"
        )
        print("=" * 70)

        for doc in unknown_documents:

            print()
            print(
                f" — {doc['pdf_file']} "
                f"({doc['chunk_count']} chunks)"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    final_pdf_count = len({
        chunk.get("pdf_file", "")
        for chunk in final_chunks
    })

    books = {}

    for chunk in final_chunks:

        books[chunk["book"]] = books.get(chunk["book"], 0) + 1

    print()
    print("=" * 70)
    print(
        "REFINEMENT RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"  Input chunks       : {len(chunks)}"
    )

    print(
        f"  Final chunks       : {len(final_chunks)}"
    )

    print(
        f"  Input PDFs         : {input_pdf_count}"
    )

    print(
        f"  Final PDFs         : {final_pdf_count}"
    )

    print(
        f"  Excluded PDFs      : {len(excluded_documents)}"
    )

    print(
        f"  Manual overrides   : {len(manual_overrides)}"
    )

    print(
        f"  Page overrides     : {len(page_overrides_applied)}"
    )

    print(
        f"  Temporal documents : {len(temporal_documents)}"
    )

    print()
    print(
        "  Chunks per book:"
    )

    for book, count in sorted(
        books.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"    {book:<28} : {count}"
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate(
        chunks,
        final_chunks,
        excluded_documents,
        unknown_documents,
    )

    if validation_errors:

        print(
            "INVALID"
        )

        for error in validation_errors:

            print(
                f"ERROR: {error}"
            )

        raise ValueError(
            "PDF refinement validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "pdf_refinement",
        "input_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE),
        "counts": {
            "input_chunks": len(chunks),
            "final_chunks": len(final_chunks),
            "input_pdfs": input_pdf_count,
            "final_pdfs": final_pdf_count,
            "excluded_pdfs": len(excluded_documents),
            "manual_overrides": len(manual_overrides),
            "page_overrides": len(page_overrides_applied),
            "temporal_documents": len(temporal_documents),
        },
        "books": books,
        "excluded_documents": excluded_documents,
        "manual_overrides": manual_overrides,
        "page_overrides_applied": page_overrides_applied,
        "temporal_documents": temporal_documents,
        "chunks": final_chunks,
    }

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print(
        "SAVED"
    )
    print("=" * 70)

    print()
    print(
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()