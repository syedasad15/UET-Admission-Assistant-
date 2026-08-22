
from pathlib import Path
import json


# ============================================================
# UET CHATBOT — REVIEW PAGE EXTRACTOR
# ============================================================
#
# Input:
#   data/inventory/admission/_pages_reviewed.json
#
# Output:
#   data/inventory/admission/_review_pages.txt
#
# Purpose:
#   Extract only pages whose refinement decision/status is REVIEW.
#
# This script does NOT modify the original JSON.
# It preserves the complete original page object so that the
# REVIEW pages can be inspected before changing the classifier.
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(r"D:\UET Chatbot")

DATA_DIR = (
    BASE_DIR
    / "data"
    / "inventory"
    / "admission"
)

INPUT_FILE = DATA_DIR / "_pages_reviewed.json"

OUTPUT_FILE = DATA_DIR / "_review_pages.txt"


# ============================================================
# POSSIBLE REVIEW FIELD NAMES
# ============================================================

DECISION_KEYS = [
    "status",
    "Status",
    "decision",
    "Decision",
    "review_status",
    "ReviewStatus",
    "classification",
    "Classification",
]


# ============================================================
# HELPERS
# ============================================================

def get_decision(page):
    """
    Find the decision/status field from a page.

    Supports several possible field names.
    """

    if not isinstance(page, dict):
        return ""

    for key in DECISION_KEYS:

        if key in page:

            value = page.get(key)

            if value is not None:

                value = str(value).strip().upper()

                if value:
                    return value

    return ""


def get_title(page):
    """
    Get a readable page title.
    """

    if not isinstance(page, dict):
        return "Untitled"

    for key in [
        "title",
        "name",
        "page_title",
    ]:

        value = page.get(key)

        if value is not None and str(value).strip():

            return str(value).strip()

    return "Untitled"


def get_url(page):
    """
    Get page URL.
    """

    if not isinstance(page, dict):
        return ""

    for key in [
        "url",
        "page_url",
        "source_url",
    ]:

        value = page.get(key)

        if value is not None and str(value).strip():

            return str(value).strip()

    return ""


def load_pages():
    """
    Load pages from _pages_reviewed.json.

    Supports:

        [
            {...},
            {...}
        ]

    and:

        {
            "pages": [...]
        }

    and:

        {
            "items": [...]
        }
    """

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nInput file was not found:\n"
            f"{INPUT_FILE}\n"
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if isinstance(data, list):

        return data

    if isinstance(data, dict):

        if isinstance(data.get("pages"), list):

            return data["pages"]

        if isinstance(data.get("items"), list):

            return data["items"]

        if isinstance(data.get("results"), list):

            return data["results"]

        if isinstance(data.get("reviewed_pages"), list):

            return data["reviewed_pages"]

    raise ValueError(
        "Could not find page list in _pages_reviewed.json."
    )


# ============================================================
# FORMAT PAGE
# ============================================================

def format_page(index, page):
    """
    Convert one page object into readable text.

    The complete JSON object is also included at the end
    so no information is lost during extraction.
    """

    lines = []

    lines.append("=" * 80)
    lines.append(f"REVIEW PAGE #{index}")
    lines.append("=" * 80)

    lines.append("")

    lines.append(
        f"TITLE: {get_title(page)}"
    )

    lines.append(
        f"URL: {get_url(page)}"
    )

    lines.append(
        f"DECISION: {get_decision(page)}"
    )

    lines.append("")

    lines.append("-" * 80)
    lines.append("IMPORTANT FIELDS")
    lines.append("-" * 80)

    # Print useful classification-related fields first.
    important_keys = [
        "title",
        "name",
        "url",
        "type",
        "status",
        "Status",
        "decision",
        "Decision",
        "role",
        "Role",
        "score",
        "Score",
        "book",
        "Book",
        "categories",
        "Categories",
        "reason",
        "Reason",
        "refinement_reason",
        "description",
        "summary",
        "excerpt",
    ]

    printed = set()

    for key in important_keys:

        if key in page:

            value = page[key]

            lines.append(
                f"\n{key}:\n"
                f"{value}"
            )

            printed.add(key)

    lines.append("")

    lines.append("-" * 80)
    lines.append("COMPLETE ORIGINAL PAGE JSON")
    lines.append("-" * 80)

    lines.append("")

    lines.append(
        json.dumps(
            page,
            indent=2,
            ensure_ascii=False
        )
    )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("UET ADMISSION — REVIEW PAGE EXTRACTOR")
    print("=" * 80)

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    pages = load_pages()

    print()
    print(
        f"Pages loaded: {len(pages)}"
    )

    # --------------------------------------------------------
    # FIND REVIEW PAGES
    # --------------------------------------------------------

    review_pages = []

    for index, page in enumerate(
        pages,
        start=1
    ):

        decision = get_decision(page)

        if decision == "REVIEW":

            review_pages.append(
                {
                    "index": index,
                    "page": page,
                }
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("REVIEW PAGES FOUND")
    print("=" * 80)

    print()
    print(
        f"Review pages: {len(review_pages)}"
    )

    # --------------------------------------------------------
    # PRINT TITLES
    # --------------------------------------------------------

    for item in review_pages:

        index = item["index"]
        page = item["page"]

        print()
        print(
            f"[{index}] {get_title(page)}"
        )

        print(
            f"    {get_url(page)}"
        )

    # --------------------------------------------------------
    # BUILD TXT
    # --------------------------------------------------------

    output_lines = []

    output_lines.append(
        "UET ADMISSION — REVIEW PAGES"
    )

    output_lines.append(
        "=" * 80
    )

    output_lines.append("")

    output_lines.append(
        f"Source: {INPUT_FILE}"
    )

    output_lines.append(
        f"Total pages scanned: {len(pages)}"
    )

    output_lines.append(
        f"Review pages found: {len(review_pages)}"
    )

    output_lines.append("")

    output_lines.append(
        "These are pages whose decision/status was "
        "identified as REVIEW."
    )

    output_lines.append("")

    # --------------------------------------------------------
    # ADD EACH REVIEW PAGE
    # --------------------------------------------------------

    for item in review_pages:

        output_lines.append(
            format_page(
                item["index"],
                item["page"]
            )
        )

        output_lines.append("\n\n")

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(output_lines)
        )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("SAVED")
    print("=" * 80)

    print()
    print(OUTPUT_FILE)

    print()

    print(
        f"Extracted {len(review_pages)} REVIEW pages."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
