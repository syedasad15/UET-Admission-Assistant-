"""
Audit recovered native text from the 73 manually approved pages.

INPUT:
    _pdf_recovered_native_pages.json
    _pdf_recovered_native_chunks.json

OUTPUT:
    _pdf_recovered_native_audit.json
    _pdf_recovered_native_audit.txt

IMPORTANT:
    This script is READ-ONLY with respect to the recovery files.
    It does NOT modify:
        _pdf_knowledge_chunks.json
        _pdf_knowledge_*.json
        _pdf_extraction_skip_summary.json
        _pdf_recovered_native_pages.json
        _pdf_recovered_native_chunks.json
"""

import json
import re
from pathlib import Path
from collections import defaultdict


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

PAGES_FILE = (
    DATA_DIR
    / "_pdf_recovered_native_pages.json"
)

CHUNKS_FILE = (
    DATA_DIR
    / "_pdf_recovered_native_chunks.json"
)

AUDIT_JSON = (
    DATA_DIR
    / "_pdf_recovered_native_audit.json"
)

AUDIT_TXT = (
    DATA_DIR
    / "_pdf_recovered_native_audit.txt"
)


# ============================================================
# EXPECTATIONS
# ============================================================

EXPECTED_PAGES = 73
EXPECTED_CHUNKS = 154


# ============================================================
# PATTERNS
# ============================================================

COURSE_CODE_PATTERN = re.compile(
    r"\b[A-Z]{2,5}\d{3,4}\b"
)

COURSE_NUMBER_PATTERN = re.compile(
    r"\b(?:Course\s*(?:No|Number)|Code)\b",
    re.IGNORECASE
)

SUBJECT_PATTERN = re.compile(
    r"\bSubject\b",
    re.IGNORECASE
)

CREDIT_PATTERN = re.compile(
    r"\b(?:Cr\.?\s*Hrs?|Credit\s*Hours?|Credits?)\b",
    re.IGNORECASE
)

ELECTIVE_PATTERN = re.compile(
    r"\bElective\s+Courses?\b",
    re.IGNORECASE
)

COURSE_PATTERN = re.compile(
    r"\bCourses?\b",
    re.IGNORECASE
)

TABLE_SEPARATOR_PATTERN = re.compile(
    r"\|"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def count_words(text):

    return len(
        text.split()
    )


def count_lines(text):

    if not text.strip():
        return 0

    return len(
        [
            line
            for line in text.splitlines()
            if line.strip()
        ]
    )


def find_course_codes(text):

    return sorted(
        set(
            COURSE_CODE_PATTERN.findall(
                text
            )
        )
    )


def get_indicators(text):

    indicators = []

    if COURSE_NUMBER_PATTERN.search(text):
        indicators.append("course_number_header")

    if SUBJECT_PATTERN.search(text):
        indicators.append("subject_header")

    if CREDIT_PATTERN.search(text):
        indicators.append("credit_header")

    if ELECTIVE_PATTERN.search(text):
        indicators.append("elective_courses")

    if COURSE_PATTERN.search(text):
        indicators.append("course_keyword")

    if TABLE_SEPARATOR_PATTERN.search(text):
        indicators.append("pipe_table_structure")

    return indicators


def first_nonempty_lines(text, n=5):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return lines[:n]


def last_nonempty_lines(text, n=5):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return lines[-n:]


def suspicious_reasons(text):

    reasons = []

    words = text.split()

    if not text.strip():
        reasons.append("empty")

    if len(words) < 10:
        reasons.append("very_short")

    # Excessive weird punctuation
    weird_chars = sum(
        1
        for ch in text
        if ch in "{}[]~"
    )

    if len(text) > 0:
        weird_ratio = (
            weird_chars / len(text)
        )

        if weird_ratio > 0.03:
            reasons.append(
                "unusual_punctuation"
            )

    # Very low ASCII letters.
    ascii_letters = sum(
        1
        for ch in text
        if ch.isascii() and ch.isalpha()
    )

    if len(text) >= 30:

        ascii_ratio = (
            ascii_letters / len(text)
        )

        if ascii_ratio < 0.20:
            reasons.append(
                "low_ascii_letter_ratio"
            )

    return reasons


# ============================================================
# PAGE AUDIT
# ============================================================

def audit_page(page_record):

    text = page_record.get(
        "text",
        ""
    )

    words = count_words(text)
    lines = count_lines(text)

    course_codes = find_course_codes(
        text
    )

    indicators = get_indicators(
        text
    )

    suspicious = suspicious_reasons(
        text
    )

    return {
        "pdf_file": page_record.get(
            "pdf_file",
            ""
        ),
        "page": page_record.get(
            "page"
        ),
        "source": page_record.get(
            "source",
            ""
        ),
        "ocr_used": page_record.get(
            "ocr_used",
            False
        ),
        "characters": len(text),
        "words": words,
        "lines": lines,
        "chunks": len(
            page_record.get(
                "chunks",
                []
            )
        ),
        "course_code_count": len(
            course_codes
        ),
        "course_codes": course_codes,
        "table_indicators": indicators,
        "suspicious_reasons": suspicious,
        "first_lines": first_nonempty_lines(
            text,
            5
        ),
        "last_lines": last_nonempty_lines(
            text,
            5
        ),
        "text": text,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("73 PAGE NATIVE TEXT AUDIT")
    print("=" * 70)
    print()

    pages_data = load_json(
        PAGES_FILE
    )

    chunks_data = load_json(
        CHUNKS_FILE
    )

    pages = pages_data.get(
        "pages",
        []
    )

    chunks = chunks_data.get(
        "chunks",
        []
    )

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    print(
        f"Expected pages : "
        f"{EXPECTED_PAGES}"
    )

    print(
        f"Actual pages   : "
        f"{len(pages)}"
    )

    print(
        f"Expected chunks: "
        f"{EXPECTED_CHUNKS}"
    )

    print(
        f"Actual chunks  : "
        f"{len(chunks)}"
    )

    print()

    validation = {
        "pages_count_ok": (
            len(pages)
            == EXPECTED_PAGES
        ),
        "chunks_count_ok": (
            len(chunks)
            == EXPECTED_CHUNKS
        ),
    }

    # --------------------------------------------------------
    # Audit each page
    # --------------------------------------------------------

    page_audits = []

    for page in pages:

        page_audits.append(
            audit_page(page)
        )

    # --------------------------------------------------------
    # Group by PDF
    # --------------------------------------------------------

    by_pdf = defaultdict(list)

    for item in page_audits:

        by_pdf[
            item["pdf_file"]
        ].append(item)

    pdf_summary = {}

    for pdf_file, items in by_pdf.items():

        total_words = sum(
            x["words"]
            for x in items
        )

        total_chars = sum(
            x["characters"]
            for x in items
        )

        total_chunks = sum(
            x["chunks"]
            for x in items
        )

        course_pages = sum(
            1
            for x in items
            if x["course_code_count"] > 0
        )

        suspicious_pages = sum(
            1
            for x in items
            if x["suspicious_reasons"]
        )

        pdf_summary[pdf_file] = {
            "pages": len(items),
            "characters": total_chars,
            "words": total_words,
            "chunks": total_chunks,
            "pages_with_course_codes": course_pages,
            "suspicious_pages": suspicious_pages,
        }

    # --------------------------------------------------------
    # Special categories
    # --------------------------------------------------------

    pages_with_course_codes = [
        x
        for x in page_audits
        if x["course_code_count"] > 0
    ]

    pages_without_course_codes = [
        x
        for x in page_audits
        if x["course_code_count"] == 0
    ]

    suspicious_pages = [
        x
        for x in page_audits
        if x["suspicious_reasons"]
    ]

    table_pages = [
        x
        for x in page_audits
        if x["table_indicators"]
    ]

    native_pages = [
        x
        for x in page_audits
        if x["source"]
        == "native_text_recovery"
    ]

    ocr_pages = [
        x
        for x in page_audits
        if x["source"]
        == "ocr_fallback"
    ]

    # --------------------------------------------------------
    # All course codes
    # --------------------------------------------------------

    all_course_codes = sorted(
        set(
            code
            for page in page_audits
            for code in page["course_codes"]
        )
    )

    # --------------------------------------------------------
    # JSON report
    # --------------------------------------------------------

    report = {
        "audit": {
            "expected_pages": EXPECTED_PAGES,
            "actual_pages": len(pages),
            "expected_chunks": EXPECTED_CHUNKS,
            "actual_chunks": len(chunks),
            "validation": validation,
        },

        "summary": {
            "native_pages": len(
                native_pages
            ),
            "ocr_pages": len(
                ocr_pages
            ),
            "pages_with_course_codes": len(
                pages_with_course_codes
            ),
            "pages_without_course_codes": len(
                pages_without_course_codes
            ),
            "table_indicator_pages": len(
                table_pages
            ),
            "suspicious_pages": len(
                suspicious_pages
            ),
            "unique_course_codes": len(
                all_course_codes
            ),
        },

        "pdf_summary": pdf_summary,

        "course_codes": all_course_codes,

        "suspicious_pages": suspicious_pages,

        "pages_without_course_codes": [
            {
                "pdf_file": x["pdf_file"],
                "page": x["page"],
                "words": x["words"],
                "first_lines": x["first_lines"],
            }
            for x in pages_without_course_codes
        ],

        "pages": page_audits,
    }

    with AUDIT_JSON.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Human-readable TXT report
    # --------------------------------------------------------

    with AUDIT_TXT.open(
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "=" * 80
            + "\n"
        )

        f.write(
            "73 PAGE NATIVE TEXT AUDIT\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        f.write(
            f"Expected pages : "
            f"{EXPECTED_PAGES}\n"
        )

        f.write(
            f"Actual pages   : "
            f"{len(pages)}\n"
        )

        f.write(
            f"Expected chunks: "
            f"{EXPECTED_CHUNKS}\n"
        )

        f.write(
            f"Actual chunks  : "
            f"{len(chunks)}\n\n"
        )

        f.write(
            f"Native pages   : "
            f"{len(native_pages)}\n"
        )

        f.write(
            f"OCR pages      : "
            f"{len(ocr_pages)}\n"
        )

        f.write(
            f"Course-code pages: "
            f"{len(pages_with_course_codes)}\n"
        )

        f.write(
            f"Table pages    : "
            f"{len(table_pages)}\n"
        )

        f.write(
            f"Suspicious pages: "
            f"{len(suspicious_pages)}\n"
        )

        f.write(
            f"Unique course codes: "
            f"{len(all_course_codes)}\n"
        )

        f.write(
            "\n"
            + "=" * 80
            + "\n"
        )

        f.write(
            "PDF SUMMARY\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        for pdf_file, summary in pdf_summary.items():

            f.write(
                f"{pdf_file}\n"
            )

            f.write(
                f"  Pages: "
                f"{summary['pages']}\n"
            )

            f.write(
                f"  Words: "
                f"{summary['words']}\n"
            )

            f.write(
                f"  Chunks: "
                f"{summary['chunks']}\n"
            )

            f.write(
                f"  Course-code pages: "
                f"{summary['pages_with_course_codes']}\n"
            )

            f.write(
                f"  Suspicious pages: "
                f"{summary['suspicious_pages']}\n\n"
            )

        # ----------------------------------------------------
        # Suspicious pages
        # ----------------------------------------------------

        f.write(
            "=" * 80
            + "\n"
        )

        f.write(
            "SUSPICIOUS / NEEDS MANUAL CHECK\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        if not suspicious_pages:

            f.write(
                "NONE\n\n"
            )

        else:

            for item in suspicious_pages:

                f.write(
                    f"{item['pdf_file']} | "
                    f"page {item['page']}\n"
                )

                f.write(
                    f"Words: "
                    f"{item['words']}\n"
                )

                f.write(
                    f"Reasons: "
                    f"{', '.join(item['suspicious_reasons'])}\n"
                )

                f.write(
                    "Preview:\n"
                )

                for line in item[
                    "first_lines"
                ]:

                    f.write(
                        f"  {line}\n"
                    )

                f.write("\n")

        # ----------------------------------------------------
        # Pages without course codes
        # ----------------------------------------------------

        f.write(
            "=" * 80
            + "\n"
        )

        f.write(
            "PAGES WITHOUT COURSE-CODE PATTERNS\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        if not pages_without_course_codes:

            f.write(
                "NONE\n\n"
            )

        else:

            for item in pages_without_course_codes:

                f.write(
                    f"{item['pdf_file']} | "
                    f"page {item['page']} | "
                    f"{item['words']} words\n"
                )

                for line in item[
                    "first_lines"
                ]:

                    f.write(
                        f"  {line}\n"
                    )

                f.write("\n")

        # ----------------------------------------------------
        # Course codes
        # ----------------------------------------------------

        f.write(
            "=" * 80
            + "\n"
        )

        f.write(
            "UNIQUE COURSE CODES FOUND\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        for i in range(
            0,
            len(all_course_codes),
            10
        ):

            f.write(
                "  "
                + ", ".join(
                    all_course_codes[
                        i:i + 10
                    ]
                )
                + "\n"
            )

        f.write("\n")

        # ----------------------------------------------------
        # Full page text
        # ----------------------------------------------------

        f.write(
            "=" * 80
            + "\n"
        )

        f.write(
            "FULL EXTRACTED PAGE TEXT\n"
        )

        f.write(
            "=" * 80
            + "\n\n"
        )

        for item in page_audits:

            f.write(
                "\n"
                + "-" * 80
                + "\n"
            )

            f.write(
                f"PDF: "
                f"{item['pdf_file']}\n"
            )

            f.write(
                f"PAGE: "
                f"{item['page']}\n"
            )

            f.write(
                f"SOURCE: "
                f"{item['source']}\n"
            )

            f.write(
                f"WORDS: "
                f"{item['words']}\n"
            )

            f.write(
                f"CHUNKS: "
                f"{item['chunks']}\n"
            )

            f.write(
                f"COURSE CODES: "
                f"{', '.join(item['course_codes'])}\n"
            )

            f.write(
                f"INDICATORS: "
                f"{', '.join(item['table_indicators'])}\n"
            )

            f.write(
                "-" * 80
                + "\n"
            )

            f.write(
                item["text"]
            )

            f.write("\n")

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)

    print(
        f"Pages             : "
        f"{len(pages)} / {EXPECTED_PAGES}"
    )

    print(
        f"Chunks            : "
        f"{len(chunks)} / {EXPECTED_CHUNKS}"
    )

    print(
        f"Native pages      : "
        f"{len(native_pages)}"
    )

    print(
        f"OCR fallback      : "
        f"{len(ocr_pages)}"
    )

    print(
        f"Course-code pages : "
        f"{len(pages_with_course_codes)}"
    )

    print(
        f"Table pages       : "
        f"{len(table_pages)}"
    )

    print(
        f"Suspicious pages  : "
        f"{len(suspicious_pages)}"
    )

    print(
        f"Unique course codes: "
        f"{len(all_course_codes)}"
    )

    print()

    if suspicious_pages:

        print(
            "[WARNING] Pages needing manual review:"
        )

        for item in suspicious_pages:

            print(
                f"  - "
                f"{item['pdf_file']} "
                f"| page {item['page']} "
                f"| {item['suspicious_reasons']}"
            )

    else:

        print(
            "[OK] No suspicious pages detected."
        )

    print()

    print(
        "JSON audit:"
    )

    print(
        AUDIT_JSON
    )

    print()

    print(
        "Readable TXT audit:"
    )

    print(
        AUDIT_TXT
    )

    print()
    print(
        "No existing knowledge-base file was modified."
    )


if __name__ == "__main__":
    main()