import json
import sys
from pathlib import Path

from pypdf import PdfReader


# ============================================================
# UET CHATBOT — PDF OCR CHECKER
# ============================================================
#
# Input:
#   data/inventory/admission/_pdf_duplicates.json
#   (uses "unique_documents" — canonical PDFs after dedup)
#
# Output:
#   data/inventory/admission/_pdf_ocr_check.json
#
# Purpose:
#   Decide, per unique PDF, whether it needs OCR or not —
#   WITHOUT running any OCR. This is a fast, cheap pass using
#   ordinary text-layer extraction (pypdf) only.
#
#   Two outcomes:
#
#       TEXT_OK    -> the PDF has a real text layer. Its full
#                      extracted text is cached right here in
#                      this output, so the next stage
#                      (pdftextextractor.py) does not need to
#                      re-open/re-parse the PDF at all.
#
#       NEEDS_OCR  -> no usable text layer was found (this is
#                      almost certainly a scanned/image-only
#                      PDF). No text is produced for these —
#                      they are left for a dedicated OCR stage
#                      to handle later.
#
# Important policy:
#
#   This script does NOT depend on pymupdf/easyocr at all.
#   OCR decision-making and OCR execution are two separate
#   concerns, kept in two separate scripts.
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

INPUT_FILE = DATA_DIR / "_pdf_duplicates.json"

OUTPUT_FILE = DATA_DIR / "_pdf_ocr_check.json"

# The actual folder where downloaded PDFs live on disk. We
# resolve against this rather than trusting a possibly-stale
# stored path, same as pdftextextractor.py does.
PDF_DIR = DATA_DIR / "pdfs"


# ============================================================
# CONFIGURATION
# ============================================================

# A document is considered TEXT_OK only if its extracted text
# has at least this many non-whitespace characters. A handful
# of stray characters (e.g. a stamp or page number caught by
# the text layer on an otherwise scanned page) should not be
# enough to call a document "text_ok".
MIN_CHARS_FOR_TEXT_OK = 40


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def clean_text(text):
    """
    Light normalization only. Unlike HTML pages, PDFs don't
    carry markup noise, so this just collapses excess
    whitespace without stripping structure.
    """

    if not text:
        return ""

    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    return "\n".join(lines).strip()


# ============================================================
# LOAD
# ============================================================

def load_duplicates():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nPDF duplicates registry was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run pdfduplicator.py first."
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    documents = data.get("unique_documents", [])

    if not isinstance(documents, list):

        raise ValueError(
            "Expected 'unique_documents' to be a list in "
            "_pdf_duplicates.json."
        )

    return documents


# ============================================================
# TEXT-LAYER EXTRACTION (no OCR)
# ============================================================

def extract_pdf_text(path):
    """
    Extract text from every page of a PDF using only the
    text layer (no OCR, no rendering to images).

    Prints a live "page X/Y" progress indicator on a single
    line so a large/slow PDF doesn't look like it has hung.

    Returns:
        (full_text, page_count, per_page_char_counts)

    Raises on unreadable/corrupt files; caller handles it.
    """

    reader = PdfReader(str(path))

    page_count = len(reader.pages)

    page_texts = []

    for page_index, page in enumerate(reader.pages, start=1):

        sys.stdout.write(
            f"\r        page {page_index}/{page_count}..."
        )
        sys.stdout.flush()

        page_text = page.extract_text() or ""

        page_texts.append(
            clean_text(page_text)
        )

    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()

    full_text = "\n\n".join(
        text
        for text in page_texts
        if text
    )

    per_page_char_counts = [
        len(text)
        for text in page_texts
    ]

    return full_text, page_count, per_page_char_counts


# ============================================================
# PROCESS ONE DOCUMENT
# ============================================================

def process_document(document):

    local_filename = normalize(
        document.get("canonical_local_filename")
    )

    path = PDF_DIR / local_filename if local_filename else None

    all_urls = [
        document.get("canonical_url", "")
    ] + [
        alias.get("url", "")
        for alias in document.get("aliases", [])
    ]

    base_record = {
        "sha256": document.get("sha256", ""),
        "canonical_url": document.get("canonical_url", ""),
        "canonical_title": document.get("canonical_title", ""),
        "canonical_local_filename": document.get(
            "canonical_local_filename",
            "",
        ),
        "all_urls": all_urls,
        "size_bytes": document.get("size_bytes", 0),
        "group_size": document.get("group_size", 1),
    }

    if not local_filename or path is None or not path.exists():

        return {
            "decision": "FAILED",
            "error": (
                "canonical_local_filename missing or file "
                f"does not exist in PDF_DIR ({PDF_DIR})"
            ),
            "page_count": 0,
            "char_count": 0,
            "text": "",
            **base_record,
        }

    try:

        full_text, page_count, per_page_char_counts = (
            extract_pdf_text(path)
        )

    except Exception as error:  # noqa: BLE001

        return {
            "decision": "FAILED",
            "error": f"{type(error).__name__}: {error}",
            "page_count": 0,
            "char_count": 0,
            "text": "",
            **base_record,
        }

    char_count = len(full_text.strip())

    if char_count >= MIN_CHARS_FOR_TEXT_OK:

        return {
            "decision": "TEXT_OK",
            "error": "",
            "page_count": page_count,
            "char_count": char_count,
            "text": full_text,
            **base_record,
        }

    return {
        "decision": "NEEDS_OCR",
        "error": (
            f"Only {char_count} extractable characters "
            f"found across {page_count} page(s) — likely "
            "a scanned/image-only PDF."
        ),
        "page_count": page_count,
        "char_count": char_count,
        "text": "",
        **base_record,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_output(output):

    errors = []

    documents = output.get("documents", [])

    for doc in documents:

        decision = doc.get("decision", "")

        if decision not in {
            "TEXT_OK",
            "NEEDS_OCR",
            "FAILED",
        }:

            errors.append(
                f"Invalid decision '{decision}' for "
                f"{doc.get('canonical_local_filename', '')}"
            )

        if decision == "TEXT_OK" and not doc.get("text"):

            errors.append(
                "TEXT_OK document has no cached text: "
                f"{doc.get('canonical_local_filename', '')}"
            )

        if decision != "TEXT_OK" and doc.get("text"):

            errors.append(
                f"{decision} document unexpectedly has "
                f"cached text: "
                f"{doc.get('canonical_local_filename', '')}"
            )

    counts = output.get("counts", {})

    actual_total = len(documents)

    if actual_total != counts.get(
        "total_documents",
        actual_total,
    ):

        errors.append(
            "Document count does not match counts.total_documents."
        )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PDF OCR CHECKER"
    )
    print("=" * 70)

    documents_in = load_duplicates()

    print()
    print(
        f"Unique documents: {len(documents_in)}"
    )

    print()
    print("=" * 70)
    print(
        "CHECKING (text-layer only, no OCR run here)"
    )
    print("=" * 70)

    results = []

    counts = {
        "TEXT_OK": 0,
        "NEEDS_OCR": 0,
        "FAILED": 0,
    }

    for index, document in enumerate(documents_in, start=1):

        title = document.get("canonical_title", "")

        filename = document.get(
            "canonical_local_filename",
            "",
        )

        print()
        print(
            f"[{index:03d}/{len(documents_in):03d}] "
            f"{title or '(no title)'}"
        )

        print(
            f"        {filename}"
        )

        result = process_document(document)

        print(
            f"        {result['decision']} "
            f"(chars={result['char_count']}, "
            f"pages={result['page_count']})"
        )

        if result["error"]:

            print(
                f"        {result['error']}"
            )

        counts[result["decision"]] = (
            counts.get(result["decision"], 0) + 1
        )

        results.append(result)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "SUMMARY"
    )
    print("=" * 70)

    print()

    for decision, count in counts.items():

        print(
            f"  {decision:<12} : {count}"
        )

    # --------------------------------------------------------
    # NEEDS_OCR list (so it's easy to see what's left)
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "NEEDS OCR (left for a dedicated OCR stage)"
    )
    print("=" * 70)

    needs_ocr = [
        result
        for result in results
        if result["decision"] == "NEEDS_OCR"
    ]

    if not needs_ocr:

        print("None")

    else:

        for result in needs_ocr:

            print()
            print(
                f" — {result['canonical_title']}"
            )

            print(
                f"   {result['canonical_local_filename']}"
            )

    # --------------------------------------------------------
    # Build output
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "pdf_ocr_check",
        "input_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE),
        "min_chars_for_text_ok": MIN_CHARS_FOR_TEXT_OK,
        "counts": {
            "total_documents": len(documents_in),
            **counts,
        },
        "documents": results,
    }

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate_output(output)

    if validation_errors:

        print("INVALID")

        for error in validation_errors:

            print(f"ERROR: {error}")

        raise ValueError(
            "PDF OCR-check validation failed."
        )

    else:

        print("VALID")

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

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
    print(OUTPUT_FILE)

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
