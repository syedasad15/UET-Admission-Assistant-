import json
from pathlib import Path


# ============================================================
# UET CHATBOT — PDF PREVIEWER
# ============================================================
#
# Input:
#   data/inventory/admission/_pdf_duplicates.json
#   data/inventory/admission/_pdf_knowledge_<filename>.json  (per PDF)
#
# Output:
#   data/inventory/admission/_pdf_title_review.json
#   (+ printed to console for easy copy/paste review)
#
# Purpose:
#   Most PDFs still have a generic "Download" title -- we don't
#   actually know what they are yet. Rather than guess with a
#   fragile heuristic, this script prints a short, readable preview
#   (page count + first couple of pages of real text) for every PDF
#   that hasn't already been manually identified, so a human can
#   assign the real title/category/decision (mirroring how REVIEW
#   pages were handled in bookbuilder.py).
#
#   Already-identified documents (KNOWN_DOCUMENTS below) are skipped
#   here -- no need to re-review what's already settled.
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

DUPLICATES_FILE = DATA_DIR / "_pdf_duplicates.json"

OUTPUT_FILE = DATA_DIR / "_pdf_title_review.json"


# ============================================================
# ALREADY IDENTIFIED DOCUMENTS
# ============================================================
#
# Identified through manual review earlier in the project. Keyed by
# sha256 so renames/URL changes don't break the match.
#
# decision:
#   KEEP    -> already known, don't need preview/review again
#   EXCLUDE -> confirmed stale/duplicate content, permanently excluded
#
# ============================================================

KNOWN_DOCUMENTS = {

    # MS Prospectus Fall 2026 -- current cycle, keep.
    "5479e8f8a7cd7861731d0b0ae2c963dabbf57a419496689739b873da39e440c7": {
        "decision": "KEEP",
        "note": "MS-2026-1 Prospectus (Fall 2026, current cycle)",
    },

    # UG Prospectus Fall 2026 -- current cycle, keep.
    "97115d62779d03c772e47d1fe3f5c667cf763184d9533920b9251e1b47342bd4": {
        "decision": "KEEP",
        "note": "UG-2026-1 Prospectus (Fall 2026, current cycle)",
    },

    # Admission Guide -- keep.
    "d59b5f4a1bc68a9301bc2849663ec2f6d56c4ad83eba56a9d4d0d155ca5eedb6": {
        "decision": "KEEP",
        "note": "Admission Guide",
    },

    # Stale Postgraduate Prospectus Spring 2026 -- superseded by
    # MS-2026-1 (Fall 2026). Confirmed via manual review.
    "344e04fc714a2c74e003101804d54cad3549f44b1e7e0f6ec9bf7e7238d84d32": {
        "decision": "EXCLUDE",
        "note": "Stale Postgraduate Prospectus (Spring 2026) -- superseded by MS-2026-1",
    },

    # Stale Undergraduate Prospectus Spring 2026 -- superseded by
    # UG-2026-1 (Fall 2026). Confirmed via manual review.
    "2b46e0a809266e43f93c653891c477fb36496ccb0cd782ac7f85b3085265a2c8": {
        "decision": "EXCLUDE",
        "note": "Stale Undergraduate Prospectus (Spring 2026) -- superseded by UG-2026-1",
    },

    # Stale Undergraduate Prospectus Fall 2025 -- superseded by
    # UG-2026-1 (Fall 2026). Confirmed via manual review.
    "0dde331d92181e248bc69ea35125c0ccdfb569a7ebbf7908f354fcbbe924fd29": {
        "decision": "EXCLUDE",
        "note": "Stale Undergraduate Prospectus (Fall 2025) -- superseded by UG-2026-1",
    },
}


# ============================================================
# CONFIGURATION
# ============================================================

PREVIEW_CHARS_PER_PAGE = 400

PREVIEW_PAGE_COUNT = 2


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# LOAD
# ============================================================

def load_duplicates():

    if not DUPLICATES_FILE.exists():

        raise FileNotFoundError(
            "\nPDF duplicates registry was not found:\n"
            f"{DUPLICATES_FILE}\n\n"
            "Run pdfduplicator.py first."
        )

    print()
    print("Reading:")
    print(DUPLICATES_FILE)

    with DUPLICATES_FILE.open(
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


def load_knowledge_file(canonical_local_filename):

    stem = Path(canonical_local_filename).stem

    path = DATA_DIR / f"_pdf_knowledge_{stem}.json"

    if not path.exists():

        return None

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# BUILD PREVIEW
# ============================================================

def build_preview(document, knowledge_data):

    pages = knowledge_data.get("pages", [])

    total_pages = len(pages)

    usable_pages = [
        page
        for page in pages
        if not page.get("skipped")
        and normalize(page.get("text"))
    ]

    preview_pages = []

    for page in usable_pages[:PREVIEW_PAGE_COUNT]:

        text = normalize(page.get("text"))

        truncated = text[:PREVIEW_CHARS_PER_PAGE]

        if len(text) > PREVIEW_CHARS_PER_PAGE:

            truncated += "..."

        preview_pages.append({
            "page": page.get("page"),
            "text": truncated,
        })

    return {
        "canonical_url": document.get("canonical_url", ""),
        "canonical_title": document.get("canonical_title", ""),
        "canonical_local_filename": document.get(
            "canonical_local_filename",
            "",
        ),
        "sha256": document.get("sha256", ""),
        "group_size": document.get("group_size", 1),
        "total_pages": total_pages,
        "usable_pages": len(usable_pages),
        "preview_pages": preview_pages,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PDF PREVIEWER"
    )
    print("=" * 70)

    documents = load_duplicates()

    print()
    print(
        f"Total unique documents: {len(documents)}"
    )

    known_count = sum(
        1
        for document in documents
        if document.get("sha256", "") in KNOWN_DOCUMENTS
    )

    print(
        f"Already identified (skipped here): {known_count}"
    )

    to_review = [
        document
        for document in documents
        if document.get("sha256", "") not in KNOWN_DOCUMENTS
    ]

    print(
        f"Needing preview/review: {len(to_review)}"
    )

    # --------------------------------------------------------
    # Build previews
    # --------------------------------------------------------

    previews = []

    missing_knowledge_files = []

    print()
    print("=" * 70)
    print(
        "PREVIEWS"
    )
    print("=" * 70)

    for index, document in enumerate(to_review, start=1):

        filename = document.get(
            "canonical_local_filename",
            "",
        )

        knowledge_data = load_knowledge_file(filename)

        if knowledge_data is None:

            missing_knowledge_files.append(document)
            continue

        preview = build_preview(
            document,
            knowledge_data,
        )

        previews.append(preview)

        print()
        print(
            f"[{index:03d}] {filename}"
        )

        print(
            f"      URL: {preview['canonical_url']}"
        )

        print(
            f"      Pages: {preview['total_pages']} total, "
            f"{preview['usable_pages']} usable"
        )

        if not preview["preview_pages"]:

            print(
                "      (no usable text found on any page)"
            )

        for page_preview in preview["preview_pages"]:

            print()
            print(
                f"      --- page {page_preview['page']} ---"
            )

            for line in page_preview["text"].splitlines():

                print(
                    f"      {line}"
                )

    # --------------------------------------------------------
    # Missing knowledge files
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "MISSING KNOWLEDGE FILES"
    )
    print("=" * 70)

    if not missing_knowledge_files:

        print("None")

    else:

        for document in missing_knowledge_files:

            print()
            print(
                f" — {document.get('canonical_title', '')}"
            )

            print(
                document.get(
                    'canonical_local_filename',
                    '',
                )
            )

            print(
                "   (run pdfextractor.py first)"
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "pdf_title_review",
        "counts": {
            "total_documents": len(documents),
            "already_identified": known_count,
            "needing_review": len(to_review),
            "previewed": len(previews),
            "missing_knowledge_files": len(
                missing_knowledge_files
            ),
        },
        "previews": previews,
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
    print(OUTPUT_FILE)

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()