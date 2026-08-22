"""
UET Admission PDFs
73 Approved Skipped Pages -> Native Text Recovery
---------------------------------------------------

Purpose:
    Recover the 73 manually-approved skipped pages WITHOUT modifying
    the existing knowledge-base files.

Strategy per approved page:
    1. Try native PDF text extraction first.
    2. If native text is usable, keep it as the primary source.
    3. If native text is empty/too weak, render page and OCR it.
    4. Preserve page-level output separately.
    5. Create chunks separately.

IMPORTANT:
    This script DOES NOT modify:
      - _pdf_knowledge_chunks.json
      - _pdf_knowledge_*.json
      - _pdf_extraction_skip_summary.json

Outputs:
    _pdf_recovered_native_pages.json
    _pdf_recovered_native_chunks.json
"""

import fitz
import easyocr
import numpy as np
from PIL import Image
from tqdm import tqdm
from pathlib import Path
import json
import re
import gc
import traceback


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

PDF_DIR = DATA_DIR / "pdfs"

OUTPUT_PAGES = DATA_DIR / "_pdf_recovered_native_pages.json"
OUTPUT_CHUNKS = DATA_DIR / "_pdf_recovered_native_chunks.json"


# ============================================================
# APPROVED 73 PAGES
# ============================================================

APPROVED_PAGES = {
    "1d111018-7c33-455a-9aa0-662f7c30da9e.pdf": [
        43, 54, 60, 63, 72, 74, 77, 129, 133, 135, 170
    ],

    "43d0e9ac-e1a7-49fe-9c91-a84383fa309a.pdf": [
        40, 43, 44, 47, 52, 57, 58, 69, 70,
        74, 82, 83, 86, 91, 100, 106, 107, 110, 114
    ],

    "559fc79c-04b2-4ead-81f2-d7f9af2601a9.pdf": [
        45, 56, 62, 65, 74, 76, 79, 131, 135, 137, 172
    ],

    "MS-2026-1_0475d05f-a54f-450c-8383-6733814b433d.pdf": [
        30, 34, 38, 43, 47, 52, 57, 58, 63, 67,
        73, 74, 78, 87, 91, 96, 105, 111, 112,
        115, 119, 149
    ],

    "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf": [
        43, 55, 59, 62, 71, 73, 76, 107, 136, 141
    ],
}


# ============================================================
# CONFIG
# ============================================================

OCR_DPI = 200
LANGUAGES = ["en"]

CANVAS_SIZE_LADDER = [1600, 1280, 960, 640]
RECOGNITION_BATCH_SIZE = 8

CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 30

# Native text must contain at least this many characters
# to be considered useful.
MIN_NATIVE_TEXT_CHARS = 30


# ============================================================
# VALIDATION
# ============================================================

def validate_approved_pages():

    total = sum(len(pages) for pages in APPROVED_PAGES.values())

    print("=" * 70)
    print("APPROVED PAGE VALIDATION")
    print("=" * 70)

    print(f"Configured PDFs : {len(APPROVED_PAGES)}")
    print(f"Approved pages  : {total}")

    if total != 73:
        raise RuntimeError(
            f"Expected exactly 73 approved pages, "
            f"but configuration contains {total}."
        )

    print("[OK] Exactly 73 approved pages configured.")

    for pdf_name, pages in APPROVED_PAGES.items():

        if len(pages) != len(set(pages)):
            raise RuntimeError(
                f"Duplicate page number detected in {pdf_name}"
            )

        if pages != sorted(pages):
            raise RuntimeError(
                f"Page numbers are not sorted in {pdf_name}"
            )

    print("[OK] No duplicate page numbers.")
    print("[OK] Page lists are sorted.")
    print()


# ============================================================
# CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    # Preserve newlines.
    text = "".join(
        ch for ch in text
        if ch == "\n" or ch.isprintable()
    )

    # Normalize spaces but DO NOT rewrite content.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [
        line.strip()
        for line in text.split("\n")
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    return "\n".join(lines)


# ============================================================
# QUALITY
# ============================================================

def native_text_quality(text):

    if not text or not text.strip():
        return {
            "flag": "empty",
            "chars": 0,
            "words": 0,
            "ascii_letters": 0,
        }

    chars = len(text)

    words = text.split()

    ascii_letters = sum(
        1 for c in text
        if c.isascii() and c.isalpha()
    )

    return {
        "flag": (
            "usable"
            if chars >= MIN_NATIVE_TEXT_CHARS
            else "too_short"
        ),
        "chars": chars,
        "words": len(words),
        "ascii_letters": ascii_letters,
    }


# ============================================================
# CHUNKING
# ============================================================

def chunk_text(
    text,
    chunk_size_words=CHUNK_SIZE_WORDS,
    overlap_words=CHUNK_OVERLAP_WORDS
):

    words = text.split()

    if not words:
        return []

    if len(words) <= chunk_size_words:
        return [text]

    chunks = []

    start = 0

    step = max(
        chunk_size_words - overlap_words,
        1
    )

    while start < len(words):

        chunk_words = words[
            start:start + chunk_size_words
        ]

        chunks.append(
            " ".join(chunk_words)
        )

        if start + chunk_size_words >= len(words):
            break

        start += step

    return chunks


# ============================================================
# OCR
# ============================================================

def _is_oom_error(e):

    msg = str(e).lower()

    return (
        isinstance(e, MemoryError)
        or "not enough memory" in msg
        or "out of memory" in msg
    )


def cluster_1d(values, threshold):

    if not values:
        return []

    vals = sorted(values)

    clusters = [[vals[0]]]

    for value in vals[1:]:

        if value - clusters[-1][-1] > threshold:
            clusters.append([])

        clusters[-1].append(value)

    return clusters


def reconstruct_table_text(items, page_width):

    if not items:
        return ""

    heights = [
        item["h"]
        for item in items
    ]

    median_h = sorted(heights)[
        len(heights) // 2
    ]

    row_tol = max(
        median_h * 1.3,
        8
    )

    col_gap_px = max(
        page_width * 0.08,
        40
    )

    items_sorted = sorted(
        items,
        key=lambda x: x["y"]
    )

    rows = []

    current_row = [
        items_sorted[0]
    ]

    anchor_y = items_sorted[0]["y"]

    for item in items_sorted[1:]:

        if item["y"] - anchor_y <= row_tol:

            current_row.append(item)

        else:

            rows.append(current_row)

            current_row = [item]

            anchor_y = item["y"]

    rows.append(current_row)

    lines = []

    for row in rows:

        xs = [
            item["x"]
            for item in row
        ]

        clusters = cluster_1d(
            xs,
            col_gap_px
        )

        col_bounds = sorted(
            [
                (min(c), max(c))
                for c in clusters
            ],
            key=lambda x: x[0]
        )

        buckets = {
            i: []
            for i in range(len(col_bounds))
        }

        for item in row:

            for idx, (lo, hi) in enumerate(
                col_bounds
            ):

                if (
                    lo - 1
                    <= item["x"]
                    <= hi + 1
                ):

                    buckets[idx].append(item)
                    break

        col_texts = []

        for idx in range(
            len(col_bounds)
        ):

            bucket_items = sorted(
                buckets[idx],
                key=lambda x: x["y"]
            )

            col_texts.append(
                " ".join(
                    item["text"]
                    for item in bucket_items
                )
            )

        line = " | ".join(
            text
            for text in col_texts
            if text
        )

        if line:
            lines.append(line)

    return "\n".join(lines)


def ocr_page(reader, page):

    mat = fitz.Matrix(
        OCR_DPI / 72,
        OCR_DPI / 72
    )

    pix = page.get_pixmap(
        matrix=mat,
        alpha=False
    )

    pil_img = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    pix = None

    img_array = np.array(
        pil_img
    )

    page_width = pil_img.width

    results = None
    canvas_used = None

    for canvas_size in CANVAS_SIZE_LADDER:

        try:

            results = reader.readtext(
                img_array,
                detail=1,
                paragraph=False,
                canvas_size=canvas_size,
                mag_ratio=1.0,
                batch_size=RECOGNITION_BATCH_SIZE,
            )

            canvas_used = canvas_size
            break

        except Exception as e:

            if _is_oom_error(e):

                print(
                    f"   [WARN] OOM at "
                    f"canvas_size={canvas_size}, "
                    f"trying smaller..."
                )

                gc.collect()

                continue

            raise

    del img_array
    del pil_img
    gc.collect()

    if not results:
        return "", canvas_used

    items = []

    for bbox, text, confidence in results:

        if not text.strip():
            continue

        xs = [
            point[0]
            for point in bbox
        ]

        ys = [
            point[1]
            for point in bbox
        ]

        items.append({
            "text": text.strip(),
            "x": min(xs),
            "y": sum(ys) / len(ys),
            "h": max(ys) - min(ys),
        })

    if not items:
        return "", canvas_used

    return (
        reconstruct_table_text(
            items,
            page_width
        ),
        canvas_used
    )


# ============================================================
# PAGE RECOVERY
# ============================================================

def recover_page(
    doc,
    page_number,
    reader
):

    page_index = page_number - 1

    page = doc[page_index]

    # --------------------------------------------------------
    # FIRST: native PDF text
    # --------------------------------------------------------

    native_raw = page.get_text(
        "text"
    )

    native_text = clean_text(
        native_raw
    )

    quality = native_text_quality(
        native_text
    )

    # --------------------------------------------------------
    # If native text is useful, USE IT.
    # --------------------------------------------------------

    if (
        quality["flag"] == "usable"
    ):

        chunks = chunk_text(
            native_text
        )

        return {
            "page": page_number,
            "source": "native_text_recovery",
            "text": native_text,
            "quality": quality,
            "ocr_used": False,
            "chunks": chunks,
        }

    # --------------------------------------------------------
    # Native text weak -> OCR fallback
    # --------------------------------------------------------

    print(
        f"   [OCR fallback] page {page_number}: "
        f"native text too weak "
        f"({quality['chars']} chars)"
    )

    ocr_text, canvas_size = ocr_page(
        reader,
        page
    )

    ocr_text = clean_text(
        ocr_text
    )

    chunks = chunk_text(
        ocr_text
    )

    result = {
        "page": page_number,
        "source": "ocr_fallback",
        "text": ocr_text,
        "native_text": native_text,
        "quality": quality,
        "ocr_used": True,
        "chunks": chunks,
    }

    if canvas_size is not None:
        result["canvas_size_used"] = canvas_size

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    validate_approved_pages()

    print("=" * 70)
    print("73 APPROVED PAGE NATIVE RECOVERY")
    print("=" * 70)
    print()
    print("IMPORTANT:")
    print("Existing knowledge-base files will NOT be modified.")
    print()

    # --------------------------------------------------------
    # Load OCR reader only when needed.
    # --------------------------------------------------------

    print("Loading EasyOCR reader...")

    reader = easyocr.Reader(
        LANGUAGES,
        gpu=False
    )

    print("EasyOCR reader loaded.")
    print()

    all_pages = []
    all_chunks = []

    failed_pages = []

    # --------------------------------------------------------
    # Process PDFs
    # --------------------------------------------------------

    for pdf_name, approved_pages in APPROVED_PAGES.items():

        pdf_path = PDF_DIR / pdf_name

        print("-" * 70)
        print(f"PDF: {pdf_name}")
        print(
            f"Approved pages: "
            f"{approved_pages}"
        )
        print("-" * 70)

        if not pdf_path.exists():

            print(
                f"[ERROR] PDF not found: "
                f"{pdf_path}"
            )

            for page in approved_pages:

                failed_pages.append({
                    "pdf_file": pdf_name,
                    "page": page,
                    "reason": "pdf_not_found",
                })

            continue

        doc = fitz.open(
            str(pdf_path)
        )

        print(
            f"PDF total pages: "
            f"{len(doc)}"
        )

        # Validate page numbers.
        invalid = [
            p
            for p in approved_pages
            if p < 1 or p > len(doc)
        ]

        if invalid:

            print(
                f"[ERROR] Invalid page numbers: "
                f"{invalid}"
            )

            for page in invalid:

                failed_pages.append({
                    "pdf_file": pdf_name,
                    "page": page,
                    "reason": "page_out_of_range",
                })

            approved_pages = [
                p
                for p in approved_pages
                if p not in invalid
            ]

        progress = tqdm(
            approved_pages,
            desc="Recovering pages",
            unit="page"
        )

        for page_number in progress:

            try:

                result = recover_page(
                    doc,
                    page_number,
                    reader
                )

                result["pdf_file"] = pdf_name

                all_pages.append(
                    result
                )

                # Add separate chunk records.
                for chunk_index, chunk in enumerate(
                    result.get("chunks", [])
                ):

                    all_chunks.append({
                        "pdf_file": pdf_name,
                        "page": page_number,
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "source": result["source"],
                        "ocr_used": result["ocr_used"],
                    })

            except Exception as e:

                print(
                    f"\n[ERROR] "
                    f"{pdf_name} "
                    f"page {page_number}: "
                    f"{e}"
                )

                traceback.print_exc()

                failed_pages.append({
                    "pdf_file": pdf_name,
                    "page": page_number,
                    "reason": str(e),
                })

        doc.close()

        gc.collect()

    # --------------------------------------------------------
    # Save page-level output
    # --------------------------------------------------------

    page_output = {
        "description": (
            "73 manually approved skipped pages "
            "recovered using native PDF text first, "
            "with OCR fallback where native text was "
            "insufficient."
        ),
        "total_requested": 73,
        "total_recovered": len(all_pages),
        "total_failed": len(failed_pages),
        "failed_pages": failed_pages,
        "pages": all_pages,
    }

    with OUTPUT_PAGES.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            page_output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Save chunk-level output
    # --------------------------------------------------------

    chunk_output = {
        "description": (
            "Chunks generated only from the "
            "73 manually approved recovered pages. "
            "This file is intentionally separate from "
            "_pdf_knowledge_chunks.json."
        ),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
    }

    with OUTPUT_CHUNKS.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            chunk_output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RECOVERY COMPLETE")
    print("=" * 70)

    print(
        f"Requested pages : 73"
    )

    print(
        f"Recovered pages : "
        f"{len(all_pages)}"
    )

    print(
        f"Failed pages    : "
        f"{len(failed_pages)}"
    )

    print(
        f"Recovered chunks: "
        f"{len(all_chunks)}"
    )

    native_count = sum(
        1
        for p in all_pages
        if p.get("source") == "native_text_recovery"
    )

    ocr_count = sum(
        1
        for p in all_pages
        if p.get("source") == "ocr_fallback"
    )

    print()
    print(
        f"Native recovered: "
        f"{native_count}"
    )

    print(
        f"OCR fallback   : "
        f"{ocr_count}"
    )

    print()
    print("Separate page output:")
    print(OUTPUT_PAGES)

    print()
    print("Separate chunk output:")
    print(OUTPUT_CHUNKS)

    print()
    print("IMPORTANT:")
    print("_pdf_knowledge_chunks.json was NOT modified.")
    print("_pdf_knowledge_*.json was NOT modified.")
    print("_pdf_extraction_skip_summary.json was NOT modified.")


if __name__ == "__main__":
    main()