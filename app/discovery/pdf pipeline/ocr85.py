# """
# UET Admission PDFs -> skipped-page audit / reprocessing script
# ---------------------------------------------------------------

# Purpose:
#     Audit ONLY the pages currently listed in:
#         _pdf_extraction_skip_summary.json

# This script does NOT rerun the complete PDF extraction pipeline.

# For every skipped page it:
#     1. Opens the original canonical PDF.
#     2. Renders the specific page.
#     3. Runs OCR using English + Urdu.
#     4. Analyzes detected script/content.
#     5. Classifies the page as one of:
#          - urdu_content
#          - mixed_language
#          - english_content
#          - ocr_failure
#          - decorative_or_non_content
#          - needs_manual_review
#     6. Saves OCR text and audit metadata.
#     7. Saves a rendered PNG for visual/manual inspection.

# IMPORTANT:
#     - Existing _pdf_knowledge_*.json files are NOT modified.
#     - Existing _pdf_knowledge_chunks.json is NOT modified.
#     - Existing skip summary is NOT modified.
#     - This is an AUDIT stage only.
#     - No embeddings are generated.

# Output:
#     _pdf_skipped_page_audit.json
#     _pdf_skipped_page_audit_images/
# """

# import fitz
# import easyocr
# import numpy as np
# from PIL import Image
# from pathlib import Path
# from tqdm import tqdm
# import json
# import re
# import gc
# import traceback


# # ============================================================
# # PROJECT PATHS
# # ============================================================

# PROJECT_ROOT = Path(r"D:\UET Chatbot")

# DATA_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "inventory"
#     / "admission"
# )

# PDF_DIR = DATA_DIR / "pdfs"

# SKIP_SUMMARY_FILE = (
#     DATA_DIR
#     / "_pdf_extraction_skip_summary.json"
# )

# AUDIT_OUTPUT_FILE = (
#     DATA_DIR
#     / "_pdf_skipped_page_audit.json"
# )

# AUDIT_IMAGE_DIR = (
#     DATA_DIR
#     / "_pdf_skipped_page_audit_images"
# )


# # ============================================================
# # CONFIG
# # ============================================================

# # Use both languages ONLY for this audit.
# # This does not change the main extractor.
# LANGUAGES = ["en", "ur"]

# OCR_DPI = 180

# CANVAS_SIZE_LADDER = [
#     1600,
#     1280,
#     960,
#     640,
# ]

# RECOGNITION_BATCH_SIZE = 4

# # Save rendered page images for manual inspection.
# SAVE_PAGE_IMAGES = True

# # If a page contains fewer than this many OCR characters,
# # don't confidently classify it as textual.
# MIN_TEXT_CHARS = 20

# # Rough thresholds for classification.
# URDU_RATIO_THRESHOLD = 0.30
# ENGLISH_RATIO_THRESHOLD = 0.30
# MIXED_URDU_THRESHOLD = 0.10
# MIXED_ENGLISH_THRESHOLD = 0.10


# # ============================================================
# # BASIC TEXT HELPERS
# # ============================================================

# def clean_text(text):
#     if not text:
#         return ""

#     text = "".join(
#         ch for ch in text
#         if ch == "\n" or ch.isprintable()
#     )

#     text = re.sub(r"[ \t]+", " ", text)

#     lines = [
#         line.strip()
#         for line in text.split("\n")
#         if line.strip()
#     ]

#     return "\n".join(lines)


# def count_urdu_chars(text):
#     """
#     Urdu/Arabic/Persian script ranges.

#     This is intentionally broad because Urdu uses Arabic-derived
#     Unicode characters.
#     """
#     count = 0

#     for ch in text:
#         code = ord(ch)

#         if (
#             0x0600 <= code <= 0x06FF
#             or 0x0750 <= code <= 0x077F
#             or 0x08A0 <= code <= 0x08FF
#             or 0xFB50 <= code <= 0xFDFF
#             or 0xFE70 <= code <= 0xFEFF
#         ):
#             count += 1

#     return count


# def count_english_chars(text):
#     return sum(
#         1
#         for ch in text
#         if ("A" <= ch <= "Z") or ("a" <= ch <= "z")
#     )


# def count_digits(text):
#     return sum(
#         1
#         for ch in text
#         if ch.isdigit()
#     )


# def script_statistics(text):
#     total = len(text)

#     if total == 0:
#         return {
#             "total_chars": 0,
#             "urdu_chars": 0,
#             "english_chars": 0,
#             "digit_chars": 0,
#             "urdu_ratio": 0.0,
#             "english_ratio": 0.0,
#             "digit_ratio": 0.0,
#         }

#     urdu = count_urdu_chars(text)
#     english = count_english_chars(text)
#     digits = count_digits(text)

#     return {
#         "total_chars": total,
#         "urdu_chars": urdu,
#         "english_chars": english,
#         "digit_chars": digits,
#         "urdu_ratio": round(urdu / total, 4),
#         "english_ratio": round(english / total, 4),
#         "digit_ratio": round(digits / total, 4),
#     }


# # ============================================================
# # CLASSIFICATION
# # ============================================================

# def classify_page(text, stats):
#     """
#     Conservative classification.

#     We do NOT automatically declare a page irrelevant merely
#     because OCR found little text. Such pages go to manual review.
#     """

#     total = stats["total_chars"]
#     urdu_ratio = stats["urdu_ratio"]
#     english_ratio = stats["english_ratio"]

#     if total < MIN_TEXT_CHARS:
#         return "ocr_failure"

#     has_urdu = urdu_ratio >= URDU_RATIO_THRESHOLD
#     has_english = english_ratio >= ENGLISH_RATIO_THRESHOLD

#     if has_urdu and has_english:
#         return "mixed_language"

#     if has_urdu:
#         return "urdu_content"

#     if has_english:
#         return "english_content"

#     # Some Urdu OCR may contain Unicode characters that don't fall
#     # neatly into the broad ranges above, so don't discard it.
#     if urdu_ratio >= MIXED_URDU_THRESHOLD:
#         return "needs_manual_review"

#     if english_ratio >= MIXED_ENGLISH_THRESHOLD:
#         return "needs_manual_review"

#     return "decorative_or_non_content"


# # ============================================================
# # OCR
# # ============================================================

# def check_model_cache(languages):
#     import os

#     cache_dir = os.path.join(
#         os.path.expanduser("~"),
#         ".EasyOCR",
#         "model"
#     )

#     print(f"EasyOCR cache: {cache_dir}")

#     if not os.path.isdir(cache_dir):
#         print("  Cache directory does not exist yet.")
#         return

#     files = os.listdir(cache_dir)

#     print(f"  Cached files: {len(files)}")

#     for language in languages:
#         if language == "en":
#             hint = "english"
#         elif language == "ur":
#             hint = "urdu"
#         else:
#             hint = language

#         found = any(
#             hint in filename.lower()
#             for filename in files
#         )

#         print(
#             f"  [{language}] "
#             f"{'cached' if found else 'NOT FOUND'}"
#         )


# def load_reader():
#     check_model_cache(LANGUAGES)

#     print()
#     print(
#         "Loading EasyOCR with languages:",
#         LANGUAGES
#     )

#     reader = easyocr.Reader(
#         LANGUAGES,
#         gpu=False
#     )

#     print("EasyOCR loaded.")

#     return reader


# def is_oom_error(exc):
#     msg = str(exc).lower()

#     return (
#         isinstance(exc, MemoryError)
#         or "out of memory" in msg
#         or "not enough memory" in msg
#     )


# def ocr_page_image(reader, pil_image):
#     """
#     OCR the complete rendered page.

#     We intentionally don't do embedded-image OCR here.
#     The purpose is to audit the exact visual page that was skipped.
#     """

#     img_array = np.array(pil_image)

#     last_error = None

#     for canvas_size in CANVAS_SIZE_LADDER:

#         try:
#             results = reader.readtext(
#                 img_array,
#                 detail=1,
#                 paragraph=True,
#                 canvas_size=canvas_size,
#                 mag_ratio=1.0,
#                 batch_size=RECOGNITION_BATCH_SIZE,
#             )

#             pieces = []

#             for item in results:
#                 if len(item) >= 2:
#                     text = item[1]

#                     if text and text.strip():
#                         pieces.append(
#                             text.strip()
#                         )

#             text = "\n".join(pieces)

#             return clean_text(text), canvas_size

#         except Exception as exc:

#             if is_oom_error(exc):
#                 print(
#                     f"    OOM at canvas_size={canvas_size}; "
#                     "trying smaller..."
#                 )

#                 gc.collect()

#                 last_error = exc
#                 continue

#             raise

#     raise last_error or RuntimeError(
#         "OCR failed without an exception."
#     )


# # ============================================================
# # PDF / PAGE RENDERING
# # ============================================================

# def render_page(doc, page_number):
#     """
#     page_number is 1-based.
#     """

#     page = doc[page_number - 1]

#     matrix = fitz.Matrix(
#         OCR_DPI / 72,
#         OCR_DPI / 72
#     )

#     pix = page.get_pixmap(
#         matrix=matrix,
#         alpha=False
#     )

#     image = Image.frombytes(
#         "RGB",
#         [pix.width, pix.height],
#         pix.samples
#     )

#     pix = None

#     return image


# # ============================================================
# # LOAD SKIPPED PAGES
# # ============================================================

# def load_skipped_pages():
#     if not SKIP_SUMMARY_FILE.exists():
#         raise FileNotFoundError(
#             f"Skip summary not found:\n"
#             f"{SKIP_SUMMARY_FILE}"
#         )

#     with SKIP_SUMMARY_FILE.open(
#         "r",
#         encoding="utf-8"
#     ) as f:
#         data = json.load(f)

#     skipped = data.get(
#         "skipped_pages",
#         []
#     )

#     return skipped


# # ============================================================
# # GROUP BY PDF
# # ============================================================

# def group_by_pdf(skipped_pages):

#     grouped = {}

#     for item in skipped_pages:

#         pdf_file = item.get(
#             "pdf_file",
#             ""
#         )

#         if not pdf_file:
#             continue

#         grouped.setdefault(
#             pdf_file,
#             []
#         ).append(item)

#     return grouped


# # ============================================================
# # AUDIT ONE PAGE
# # ============================================================

# def audit_page(
#     doc,
#     pdf_file,
#     page_info,
#     reader
# ):

#     page_number = int(
#         page_info["page"]
#     )

#     print(
#         f"    Auditing page {page_number}"
#     )

#     image = render_page(
#         doc,
#         page_number
#     )

#     image_path = None

#     if SAVE_PAGE_IMAGES:

#         safe_stem = Path(pdf_file).stem

#         image_name = (
#             f"{safe_stem}"
#             f"__page_{page_number:04d}.png"
#         )

#         image_path = (
#             AUDIT_IMAGE_DIR
#             / image_name
#         )

#         image.save(
#             image_path,
#             "PNG"
#         )

#     try:

#         ocr_text, canvas_size = (
#             ocr_page_image(
#                 reader,
#                 image
#             )
#         )

#     finally:

#         del image
#         gc.collect()

#     stats = script_statistics(
#         ocr_text
#     )

#     classification = classify_page(
#         ocr_text,
#         stats
#     )

#     result = {
#         "pdf_file": pdf_file,
#         "page": page_number,

#         "original_skip_reason": page_info.get(
#             "reason",
#             ""
#         ),

#         "original_quality_flag": page_info.get(
#             "quality_flag",
#             ""
#         ),

#         "audit": {
#             "classification": classification,
#             "ocr_languages": LANGUAGES,
#             "canvas_size_used": canvas_size,
#             "script_statistics": stats,
#         },

#         "ocr_text": ocr_text,

#         "rendered_image": (
#             str(image_path)
#             if image_path
#             else None
#         ),

#         # IMPORTANT:
#         # This remains false until a human confirms it.
#         "human_reviewed": False,

#         "human_decision": None,

#         "recommended_action": None,
#     }

#     # Suggested next action
#     if classification == "urdu_content":
#         result["recommended_action"] = (
#             "keep_skipped_until_urdu_ocr"
#         )

#     elif classification == "mixed_language":
#         result["recommended_action"] = (
#             "manual_review_and_reprocess"
#         )

#     elif classification == "english_content":
#         result["recommended_action"] = (
#             "reprocess_with_ocr"
#         )

#     elif classification == "ocr_failure":
#         result["recommended_action"] = (
#             "manual_visual_review"
#         )

#     elif classification == "decorative_or_non_content":
#         result["recommended_action"] = (
#             "manual_visual_review"
#         )

#     else:
#         result["recommended_action"] = (
#             "manual_visual_review"
#         )

#     return result


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print("=" * 72)
#     print("UET ADMISSION PDF - SKIPPED PAGE AUDIT")
#     print("=" * 72)

#     skipped_pages = load_skipped_pages()

#     print(
#         f"\nSkipped pages found: "
#         f"{len(skipped_pages)}"
#     )

#     if not skipped_pages:
#         print(
#             "No skipped pages found."
#         )
#         return

#     # --------------------------------------------------------
#     # Create image directory
#     # --------------------------------------------------------

#     if SAVE_PAGE_IMAGES:
#         AUDIT_IMAGE_DIR.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#     # --------------------------------------------------------
#     # Group pages by PDF
#     # --------------------------------------------------------

#     grouped = group_by_pdf(
#         skipped_pages
#     )

#     print(
#         f"PDFs containing skipped pages: "
#         f"{len(grouped)}"
#     )

#     for pdf_file, pages in grouped.items():

#         print(
#             f"  - {pdf_file}: "
#             f"{len(pages)} page(s)"
#         )

#     # --------------------------------------------------------
#     # Load OCR reader
#     # --------------------------------------------------------

#     reader = load_reader()

#     # --------------------------------------------------------
#     # Audit
#     # --------------------------------------------------------

#     results = []

#     for pdf_file, pages in grouped.items():

#         pdf_path = (
#             PDF_DIR
#             / pdf_file
#         )

#         print()
#         print("-" * 72)
#         print(
#             f"PDF: {pdf_file}"
#         )

#         if not pdf_path.exists():

#             print(
#                 "  [WARNING] PDF not found:"
#             )
#             print(
#                 f"  {pdf_path}"
#             )

#             for page_info in pages:

#                 results.append({
#                     "pdf_file": pdf_file,
#                     "page": page_info.get(
#                         "page"
#                     ),
#                     "audit": {
#                         "classification":
#                             "needs_manual_review"
#                     },
#                     "error":
#                         "source_pdf_not_found",
#                     "human_reviewed": False,
#                     "human_decision": None,
#                 })

#             continue

#         try:

#             doc = fitz.open(
#                 str(pdf_path)
#             )

#         except Exception as exc:

#             print(
#                 f"  [ERROR] Could not open PDF: "
#                 f"{exc}"
#             )

#             for page_info in pages:

#                 results.append({
#                     "pdf_file": pdf_file,
#                     "page": page_info.get(
#                         "page"
#                     ),
#                     "audit": {
#                         "classification":
#                             "needs_manual_review"
#                     },
#                     "error":
#                         f"pdf_open_error: {exc}",
#                     "human_reviewed": False,
#                     "human_decision": None,
#                 })

#             continue

#         try:

#             for page_info in tqdm(
#                 pages,
#                 desc=f"  {Path(pdf_file).stem}",
#                 unit="page"
#             ):

#                 try:

#                     result = audit_page(
#                         doc,
#                         pdf_file,
#                         page_info,
#                         reader
#                     )

#                     results.append(
#                         result
#                     )

#                 except Exception as exc:

#                     print(
#                         f"\n  [ERROR] "
#                         f"{pdf_file} "
#                         f"page "
#                         f"{page_info.get('page')}: "
#                         f"{exc}"
#                     )

#                     traceback.print_exc()

#                     results.append({
#                         "pdf_file": pdf_file,
#                         "page": page_info.get(
#                             "page"
#                         ),
#                         "audit": {
#                             "classification":
#                                 "needs_manual_review"
#                         },
#                         "error": str(exc),
#                         "human_reviewed": False,
#                         "human_decision": None,
#                     })

#                 # Checkpoint after every page
#                 save_report(
#                     results
#                 )

#         finally:

#             doc.close()
#             gc.collect()

#     # --------------------------------------------------------
#     # Final summary
#     # --------------------------------------------------------

#     save_report(
#         results
#     )

#     print()
#     print("=" * 72)
#     print("AUDIT COMPLETE")
#     print("=" * 72)

#     print(
#         f"Pages audited: {len(results)}"
#     )

#     counts = {}

#     for result in results:

#         classification = (
#             result
#             .get("audit", {})
#             .get(
#                 "classification",
#                 "unknown"
#             )
#         )

#         counts[classification] = (
#             counts.get(
#                 classification,
#                 0
#             ) + 1
#         )

#     print()

#     for classification, count in sorted(
#         counts.items()
#     ):
#         print(
#             f"  {classification}: {count}"
#         )

#     print()
#     print(
#         f"Audit JSON:\n"
#         f"{AUDIT_OUTPUT_FILE}"
#     )

#     if SAVE_PAGE_IMAGES:
#         print()
#         print(
#             f"Rendered pages:\n"
#             f"{AUDIT_IMAGE_DIR}"
#         )


# # ============================================================
# # SAVE REPORT
# # ============================================================

# def save_report(results):

#     summary = {}

#     for result in results:

#         classification = (
#             result
#             .get("audit", {})
#             .get(
#                 "classification",
#                 "unknown"
#             )
#         )

#         summary[classification] = (
#             summary.get(
#                 classification,
#                 0
#             ) + 1
#         )

#     report = {
#         "stage": "pdf_skipped_page_audit",

#         "purpose": (
#             "Audit only pages that were skipped by the "
#             "English-only admission PDF extractor."
#         ),

#         "source_skip_summary": str(
#             SKIP_SUMMARY_FILE
#         ),

#         "ocr_languages": LANGUAGES,

#         "total_pages_audited": len(
#             results
#         ),

#         "classification_summary": summary,

#         "important_note": (
#             "This file is an audit artifact only. "
#             "No existing PDF knowledge files or "
#             "combined chunks were modified."
#         ),

#         "pages": results,
#     }

#     with AUDIT_OUTPUT_FILE.open(
#         "w",
#         encoding="utf-8"
#     ) as f:

#         json.dump(
#             report,
#             f,
#             ensure_ascii=False,
#             indent=2
#         )


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":
#     main()


import json
import csv
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

SKIP_SUMMARY_FILE = DATA_DIR / "_pdf_extraction_skip_summary.json"

CSV_OUTPUT = DATA_DIR / "_skipped_pages_manual_audit.csv"
TXT_OUTPUT = DATA_DIR / "_skipped_pages_manual_audit.txt"


# ============================================================
# LOAD
# ============================================================

if not SKIP_SUMMARY_FILE.exists():
    raise FileNotFoundError(
        f"Skip summary not found:\n{SKIP_SUMMARY_FILE}"
    )

with SKIP_SUMMARY_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

skipped_pages = data.get("skipped_pages", [])

print(f"Total skipped pages found: {len(skipped_pages)}")

if not skipped_pages:
    print("No skipped pages found.")
    raise SystemExit(0)


# ============================================================
# SORT
# ============================================================

# Sort primarily by PDF, then page number
skipped_pages.sort(
    key=lambda x: (
        x.get("pdf_file", ""),
        int(x.get("page", 0)),
    )
)


# ============================================================
# CSV
# ============================================================

csv_rows = []

for idx, item in enumerate(skipped_pages, start=1):
    csv_rows.append({
        "audit_no": idx,
        "pdf_file": item.get("pdf_file", ""),
        "page": item.get("page", ""),
        "reason": item.get("reason", ""),
        "quality_flag": item.get("quality_flag", ""),
        "decision": "",
        "notes": "",
    })


with CSV_OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "audit_no",
            "pdf_file",
            "page",
            "reason",
            "quality_flag",
            "decision",
            "notes",
        ],
    )

    writer.writeheader()
    writer.writerows(csv_rows)


# ============================================================
# TXT
# ============================================================

with TXT_OUTPUT.open("w", encoding="utf-8") as f:

    f.write("UET ADMISSION PDF - SKIPPED PAGE MANUAL AUDIT\n")
    f.write("=" * 80 + "\n\n")

    f.write(f"Total skipped pages: {len(skipped_pages)}\n\n")

    f.write(
        "Instructions:\n"
        "  IMPORTANT = page contains useful admission information and must be reprocessed\n"
        "  SKIP     = page is decorative / irrelevant / Urdu content not needed\n"
        "  REVIEW   = uncertain, inspect later\n\n"
    )

    f.write("=" * 80 + "\n\n")

    for idx, item in enumerate(skipped_pages, start=1):

        pdf_file = item.get("pdf_file", "")
        page = item.get("page", "")
        reason = item.get("reason", "")
        quality = item.get("quality_flag", "")

        f.write(
            f"{idx:03d}. "
            f"{pdf_file} | "
            f"PAGE {page} | "
            f"{reason} | "
            f"{quality}\n"
        )

        f.write("     DECISION: __________\n")
        f.write("     NOTES:    ________________________________\n\n")


# ============================================================
# SUMMARY BY PDF
# ============================================================

by_pdf = {}

for item in skipped_pages:
    pdf = item.get("pdf_file", "")
    page = item.get("page", "")
    by_pdf.setdefault(pdf, []).append(page)


print()
print("=" * 70)
print("SKIPPED PAGE SUMMARY")
print("=" * 70)

for pdf_file, pages in by_pdf.items():
    print(f"{pdf_file}: {pages}")

print()
print(f"Total skipped pages: {len(skipped_pages)}")
print()
print(f"CSV: {CSV_OUTPUT}")
print(f"TXT: {TXT_OUTPUT}")