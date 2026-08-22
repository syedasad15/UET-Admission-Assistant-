"""
UET Admission PDFs -> MANUALLY APPROVED SKIPPED PAGE RECOVERY
---------------------------------------------------------------

Purpose:
    Recover ONLY the pages manually marked as useful during the
    skipped-page audit.

IMPORTANT:
    This script DOES NOT modify:
        _pdf_knowledge_chunks.json
        existing _pdf_knowledge_<pdf>.json files
        _pdf_extraction_skip_summary.json

Output:
    _pdf_recovered_pages.json
    _pdf_recovered_chunks.json

The recovery output remains separate until manually reviewed/approved.

Strategy per approved page:
    1. Prefer native/selectable PDF text.
    2. If native text is missing, use full-page OCR.
    3. Do NOT reject native text merely because the English OCR
       quality heuristic would consider it suspicious.
    4. Keep the recovered content separate from the main KB.
"""

import fitz
import easyocr
import numpy as np
from PIL import Image
from tqdm import tqdm
import json
from pathlib import Path
import re
import gc
import sys
import traceback


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

PDF_DIR = DATA_DIR / "pdfs"

RECOVERED_PAGES_FILE = (
    DATA_DIR / "_pdf_recovered_pages.json"
)

RECOVERED_CHUNKS_FILE = (
    DATA_DIR / "_pdf_recovered_chunks.json"
)


# ============================================================
# OCR CONFIG
# ============================================================

OCR_DPI = 200

LANGUAGES = ["en"]

CANVAS_SIZE_LADDER = [1600, 1280, 960, 640]

RECOGNITION_BATCH_SIZE = 8

CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 30


# ============================================================
# MANUALLY APPROVED PAGES
#
# Page numbers are 1-based, exactly as shown in the audit.
# ============================================================

APPROVED_PAGES = {

    "1d111018-7c33-455a-9aa0-662f7c30da9e.pdf": [
        43,
        54,
        60,
        63,
        72,
        74,
        77,
        129,
        133,
        135,
        170,
    ],

    "43d0e9ac-e1a7-49fe-9c91-a84383fa309a.pdf": [
        40,
        43,
        44,
        47,
        52,
        57,
        58,
        69,
        70,
        74,
        82,
        83,
        86,
        91,
        100,
        106,
        107,
        110,
        114,
    ],

    "559fc79c-04b2-4ead-81f2-d7f9af2601a9.pdf": [
        45,
        56,
        62,
        65,
        74,
        76,
        79,
        131,
        135,
        137,
        172,
    ],

    "MS-2026-1_0475d05f-a54f-450c-8383-6733814b433d.pdf": [
        30,
        34,
        38,
        43,
        47,
        52,
        57,
        58,
        63,
        67,
        73,
        74,
        78,
        87,
        91,
        96,
        105,
        111,
        112,
        115,
        119,
        149,
    ],

    "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf": [
        43,
        55,
        59,
        62,
        71,
        73,
        76,
        107,
        136,
        141,
    ],
}


# ============================================================
# EXPECTED COUNT CHECK
# ============================================================

EXPECTED_APPROVED_COUNT = 73


# ============================================================
# TEXT CLEANUP
# ============================================================

def clean_text(text):
    """
    Formatting-only cleanup.

    Does NOT rewrite or guess content.
    """

    if not text:
        return ""

    text = "".join(
        ch for ch in text
        if ch == "\n" or ch.isprintable()
    )

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(
        r"\|\s*\|",
        "|",
        text
    )

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
# NATIVE TEXT EXTRACTION
# ============================================================

def extract_native_text(page):
    """
    Extract selectable/native PDF text.

    'blocks' preserves the spatial structure better than a simple
    page.get_text("text") call and is useful for tables.
    """

    blocks = page.get_text("blocks")

    if not blocks:
        return ""

    usable_blocks = []

    for block in blocks:

        if len(block) < 5:
            continue

        x0, y0, x1, y1, text = block[:5]

        if not text or not text.strip():
            continue

        usable_blocks.append({
            "x": x0,
            "y": y0,
            "text": text.strip(),
        })

    if not usable_blocks:
        return ""

    # Sort approximately in reading order.
    usable_blocks.sort(
        key=lambda b: (
            round(b["y"], 1),
            b["x"]
        )
    )

    lines = []

    for block in usable_blocks:
        lines.append(block["text"])

    return clean_text("\n".join(lines))


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


def _cluster_1d_fixed(values, threshold):

    if not values:
        return []

    vals = sorted(values)

    clusters = [[vals[0]]]

    for i in range(1, len(vals)):

        if vals[i] - vals[i - 1] > threshold:
            clusters.append([])

        clusters[-1].append(vals[i])

    return clusters


def reconstruct_table_text(items, page_width):

    if not items:
        return ""

    heights = [
        item["h"]
        for item in items
    ]

    median_h = sorted(heights)[len(heights) // 2]

    row_tolerance = max(
        median_h * 1.3,
        8
    )

    column_gap = max(
        page_width * 0.08,
        40
    )

    items_sorted = sorted(
        items,
        key=lambda d: d["y"]
    )

    rows = []

    current_row = [items_sorted[0]]

    anchor_y = items_sorted[0]["y"]

    for item in items_sorted[1:]:

        if item["y"] - anchor_y <= row_tolerance:

            current_row.append(item)

        else:

            rows.append(current_row)

            current_row = [item]

            anchor_y = item["y"]

    rows.append(current_row)

    output_lines = []

    for row in rows:

        xs = [
            item["x"]
            for item in row
        ]

        x_clusters = _cluster_1d_fixed(
            xs,
            threshold=column_gap
        )

        column_bounds = sorted(
            [
                (min(c), max(c))
                for c in x_clusters
            ],
            key=lambda b: b[0]
        )

        buckets = {
            i: []
            for i in range(len(column_bounds))
        }

        for item in row:

            for idx, (lo, hi) in enumerate(
                column_bounds
            ):

                if (
                    lo - 1
                    <= item["x"]
                    <= hi + 1
                ):

                    buckets[idx].append(item)
                    break

        column_texts = []

        for idx in range(
            len(column_bounds)
        ):

            bucket_items = sorted(
                buckets[idx],
                key=lambda d: d["y"]
            )

            column_texts.append(
                " ".join(
                    item["text"]
                    for item in bucket_items
                )
            )

        line = " | ".join(
            text
            for text in column_texts
            if text
        )

        if line:
            output_lines.append(line)

    return "\n".join(output_lines)


def ocr_image_ordered(reader, pil_image):

    image_array = np.array(
        pil_image
    )

    page_width = pil_image.width

    results = None

    canvas_size_used = None

    last_error = None

    for canvas_size in CANVAS_SIZE_LADDER:

        try:

            results = reader.readtext(
                image_array,
                detail=1,
                paragraph=False,
                canvas_size=canvas_size,
                mag_ratio=1.0,
                batch_size=RECOGNITION_BATCH_SIZE,
            )

            canvas_size_used = canvas_size

            break

        except Exception as e:

            if _is_oom_error(e):

                print(
                    f"   [WARN] OCR OOM at "
                    f"canvas_size={canvas_size}; "
                    f"trying smaller size..."
                )

                gc.collect()

                last_error = e

                continue

            raise

    if results is None:

        raise (
            last_error
            if last_error
            else RuntimeError(
                "OCR failed"
            )
        )

    if not results:
        return "", canvas_size_used

    items = []

    for bbox, text, conf in results:

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
            "confidence": float(conf),
        })

    if not items:
        return "", canvas_size_used

    text = reconstruct_table_text(
        items,
        page_width
    )

    return clean_text(text), canvas_size_used


# ============================================================
# PAGE EXTRACTION
# ============================================================

def extract_approved_page(
    doc,
    page_number,
    reader
):

    # Convert 1-based page number -> 0-based index
    page_index = page_number - 1

    page = doc[page_index]

    # --------------------------------------------------------
    # FIRST: NATIVE TEXT
    # --------------------------------------------------------

    native_text = extract_native_text(page)

    if native_text:

        return {
            "page": page_number,
            "source": "native",
            "text": native_text,
            "quality": {
                "flag": "ok",
                "method": "manual_approval_native_text"
            },
        }

    # --------------------------------------------------------
    # SECOND: FULL PAGE OCR
    # --------------------------------------------------------

    print(
        f"   [INFO] Page {page_number}: "
        f"no native text -> OCR fallback"
    )

    matrix = fitz.Matrix(
        OCR_DPI / 72,
        OCR_DPI / 72
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    pil_image = Image.frombytes(
        "RGB",
        [
            pix.width,
            pix.height
        ],
        pix.samples
    )

    pix = None

    try:

        ocr_text, canvas_size = (
            ocr_image_ordered(
                reader,
                pil_image
            )
        )

    finally:

        del pil_image
        gc.collect()

    return {
        "page": page_number,
        "source": "full_page_ocr",
        "text": ocr_text,
        "quality": {
            "flag": "manual_approved_ocr",
            "method": "manual_approval"
        },
        "canvas_size_used": canvas_size,
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
            start:
            start + chunk_size_words
        ]

        chunks.append(
            " ".join(chunk_words)
        )

        if (
            start + chunk_size_words
            >= len(words)
        ):
            break

        start += step

    return chunks


# ============================================================
# METADATA
# ============================================================

def load_pdf_metadata():

    duplicates_file = (
        DATA_DIR / "_pdf_duplicates.json"
    )

    if not duplicates_file.exists():

        print(
            f"[ERROR] Missing:\n"
            f"{duplicates_file}"
        )

        sys.exit(1)

    with duplicates_file.open(
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    metadata_by_filename = {}

    for doc in data.get(
        "unique_documents",
        []
    ):

        filename = doc.get(
            "canonical_local_filename",
            ""
        )

        if not filename:
            continue

        all_urls = [
            doc.get(
                "canonical_url",
                ""
            )
        ]

        all_urls.extend(
            alias.get("url", "")
            for alias in doc.get(
                "aliases",
                []
            )
        )

        metadata_by_filename[filename] = {
            "canonical_url": doc.get(
                "canonical_url",
                ""
            ),
            "canonical_title": doc.get(
                "canonical_title",
                ""
            ),
            "sha256": doc.get(
                "sha256",
                ""
            ),
            "all_urls": all_urls,
        }

    return metadata_by_filename


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_outputs(
    recovered_pages,
    recovered_chunks
):

    with RECOVERED_PAGES_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            recovered_pages,
            f,
            ensure_ascii=False,
            indent=2
        )

    with RECOVERED_CHUNKS_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            recovered_chunks,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    total_requested = sum(
        len(pages)
        for pages in APPROVED_PAGES.values()
    )

    print("=" * 70)
    print("MANUALLY APPROVED SKIPPED PAGE RECOVERY")
    print("=" * 70)

    print(
        f"Approved pages configured: "
        f"{total_requested}"
    )

    if total_requested != EXPECTED_APPROVED_COUNT:

        print(
            f"[WARNING] Expected "
            f"{EXPECTED_APPROVED_COUNT}, "
            f"but configuration contains "
            f"{total_requested}."
        )

        print(
            "Please verify APPROVED_PAGES "
            "before continuing."
        )

        sys.exit(1)

    metadata_by_filename = (
        load_pdf_metadata()
    )

    reader = None

    recovered_pages = []

    recovered_chunks = []

    successful_pages = 0

    failed_pages = []

    # --------------------------------------------------------
    # PROCESS PDF BY PDF
    # --------------------------------------------------------

    for pdf_filename, pages in (
        APPROVED_PAGES.items()
    ):

        pdf_path = (
            PDF_DIR / pdf_filename
        )

        print()
        print("-" * 70)
        print(
            f"PDF: {pdf_filename}"
        )
        print(
            f"Approved pages: {pages}"
        )
        print("-" * 70)

        if not pdf_path.exists():

            print(
                f"[ERROR] PDF not found:\n"
                f"{pdf_path}"
            )

            for page_number in pages:

                failed_pages.append({
                    "pdf_file": pdf_filename,
                    "page": page_number,
                    "error": "pdf_not_found",
                })

            continue

        metadata = (
            metadata_by_filename.get(
                pdf_filename,
                {}
            )
        )

        try:

            doc = fitz.open(
                str(pdf_path)
            )

        except Exception as e:

            print(
                f"[ERROR] Could not open PDF: {e}"
            )

            for page_number in pages:

                failed_pages.append({
                    "pdf_file": pdf_filename,
                    "page": page_number,
                    "error": str(e),
                })

            continue

        print(
            f"PDF total pages: {len(doc)}"
        )

        # ----------------------------------------------------
        # Validate page numbers
        # ----------------------------------------------------

        invalid_pages = [
            page
            for page in pages
            if page < 1
            or page > len(doc)
        ]

        if invalid_pages:

            print(
                f"[ERROR] Invalid page numbers: "
                f"{invalid_pages}"
            )

            for page_number in invalid_pages:

                failed_pages.append({
                    "pdf_file": pdf_filename,
                    "page": page_number,
                    "error": "invalid_page_number",
                })

            pages = [
                page
                for page in pages
                if page not in invalid_pages
            ]

        # Load OCR only if necessary.
        # Native text pages won't need it.
        if reader is None:

            print(
                "\nLoading EasyOCR reader..."
            )

            reader = easyocr.Reader(
                LANGUAGES,
                gpu=False
            )

            print(
                "EasyOCR reader loaded."
            )

        for page_number in tqdm(
            pages,
            desc="Recovering pages",
            unit="page"
        ):

            try:

                result = extract_approved_page(
                    doc,
                    page_number,
                    reader
                )

                text = result.get(
                    "text",
                    ""
                ).strip()

                # --------------------------------------------
                # Recovery record
                # --------------------------------------------

                page_record = {
                    "canonical_url": metadata.get(
                        "canonical_url",
                        ""
                    ),
                    "canonical_title": metadata.get(
                        "canonical_title",
                        ""
                    ),
                    "sha256": metadata.get(
                        "sha256",
                        ""
                    ),
                    "all_urls": metadata.get(
                        "all_urls",
                        []
                    ),
                    "pdf_file": pdf_filename,
                    "page": page_number,
                    "source": result.get(
                        "source",
                        ""
                    ),
                    "quality": result.get(
                        "quality",
                        {}
                    ),
                    "text": text,
                }

                if (
                    "canvas_size_used"
                    in result
                ):

                    page_record[
                        "canvas_size_used"
                    ] = result[
                        "canvas_size_used"
                    ]

                chunks = chunk_text(text)

                page_record["chunks"] = chunks

                recovered_pages.append(
                    page_record
                )

                # --------------------------------------------
                # Separate chunk output
                # --------------------------------------------

                for chunk_index, chunk in enumerate(
                    chunks
                ):

                    recovered_chunks.append({
                        "canonical_url": metadata.get(
                            "canonical_url",
                            ""
                        ),
                        "canonical_title": metadata.get(
                            "canonical_title",
                            ""
                        ),
                        "sha256": metadata.get(
                            "sha256",
                            ""
                        ),
                        "all_urls": metadata.get(
                            "all_urls",
                            []
                        ),
                        "pdf_file": pdf_filename,
                        "page": page_number,
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "source": result.get(
                            "source",
                            ""
                        ),
                        "quality_flag": result.get(
                            "quality",
                            {}
                        ).get(
                            "flag",
                            ""
                        ),
                    })

                successful_pages += 1

                # Checkpoint after every page
                save_outputs(
                    recovered_pages,
                    recovered_chunks
                )

            except Exception as e:

                print()
                print(
                    f"[ERROR] "
                    f"{pdf_filename} "
                    f"page {page_number}: "
                    f"{e}"
                )

                traceback.print_exc()

                failed_pages.append({
                    "pdf_file": pdf_filename,
                    "page": page_number,
                    "error": str(e),
                })

            gc.collect()

        doc.close()

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("RECOVERY COMPLETE")
    print("=" * 70)

    print(
        f"Requested pages : {total_requested}"
    )

    print(
        f"Recovered pages : {successful_pages}"
    )

    print(
        f"Failed pages    : {len(failed_pages)}"
    )

    print(
        f"Recovered chunks: {len(recovered_chunks)}"
    )

    print()
    print(
        "Separate page output:"
    )

    print(
        RECOVERED_PAGES_FILE
    )

    print()
    print(
        "Separate chunk output:"
    )

    print(
        RECOVERED_CHUNKS_FILE
    )

    if failed_pages:

        print()
        print(
            "=" * 70
        )

        print(
            "FAILED PAGES"
        )

        print(
            "=" * 70
        )

        for item in failed_pages:

            print(
                f"  - "
                f"{item['pdf_file']} "
                f"| page {item['page']} "
                f"| {item['error']}"
            )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "_pdf_knowledge_chunks.json "
        "was NOT modified."
    )

    print(
        "Existing _pdf_knowledge_*.json "
        "files were NOT modified."
    )

    print(
        "_pdf_extraction_skip_summary.json "
        "was NOT modified."
    )


if __name__ == "__main__":
    main()