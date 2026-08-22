import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# UET CHATBOT — KNOWLEDGE BOOK BUILDER
# ============================================================
#
# Input:
#   data/inventory/admission/_knowledge_refined.json
#
# Output:
#   data/inventory/admission/_knowledge_books.json
#
# Purpose:
#   Convert refined page decisions into actual knowledge books.
#
# Important policy:
#
#   CORE        -> usable
#   SUPPORTING  -> usable
#   TEMPORAL    -> usable
#
#   REVIEW pages are handled by the FINAL REVIEW DECISIONS
#   defined below.
#
#   REVIEW is NOT automatically included.
#   REVIEW is NOT automatically excluded.
#
#   Each REVIEW page that was manually assessed is explicitly
#   classified as KEEP or EXCLUDE.
#
#   SKIP -> always excluded
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

INPUT_FILE = DATA_DIR / "_knowledge_refined.json"
OUTPUT_FILE = DATA_DIR / "_knowledge_books.json"


# ============================================================
# CONSTANTS
# ============================================================

VALID_STATUSES = {
    "CORE",
    "SUPPORTING",
    "TEMPORAL",
    "REVIEW",
    "SKIP",
}

USABLE_STATUSES = {
    "CORE",
    "SUPPORTING",
    "TEMPORAL",
}

VALID_ROLES = {
    "core",
    "supporting",
    "temporal",
    "operational",
    "promotional",
}

BOOK_NAMES = {
    "programs",
    "faq",
    "fees",
    "eligibility",
    "deadlines",
    "admission_process",
    "ecat",
    "international_admissions",
    "scholarships",
    "temporal_updates",
}


# ============================================================
# FINAL REVIEW DECISIONS
# ============================================================
#
# These are the REVIEW pages that were manually assessed.
#
# IMPORTANT:
#
# Do NOT use generic keyword detection to decide whether a
# REVIEW page belongs in the knowledge base.
#
# The REVIEW stage exists specifically because these pages
# require judgment.
#
# KEEP:
#
#   /news/29  Application Scrutiny Underway
#   /news/18  ECAT Fall 2026 Registrations are closed
#   /news/4   Undergraduate Admissions - Fall 2026
#   /news/10  International Students UET Lahore
#
# EXCLUDE:
#
#   /#programs  Home navigation page
#   /news/24    ECAT office operational notice
#   /news/15    Undergraduate Admissions Advertisement
#   /news/2     Financial Year 2025-26 Scholarships
#   /news/1     Financial Year 2025-26 Scholarships
#
# ============================================================
REVIEW_DECISIONS = {

    # --------------------------------------------------------
    # KEEP
    # --------------------------------------------------------

    "https://admission.uet.edu.pk": {
        "decision": "KEEP",
        "book": "programs",
        "reason": "REVIEW_KEEP_HOME_PROGRAM_INFORMATION",
    },

    "https://admission.uet.edu.pk/news/29": {
        "decision": "KEEP",
        "book": "admission_process",
        "reason": "REVIEW_KEEP_ADMISSION_PROCESS",
    },

    "https://admission.uet.edu.pk/news/24": {
        "decision": "KEEP",
        "book": "ecat",
        "reason": "REVIEW_KEEP_ECAT_OPERATIONAL_NOTICE",
    },

    "https://admission.uet.edu.pk/news/18": {
        "decision": "KEEP",
        "book": "ecat",
        "reason": "REVIEW_KEEP_ECAT_STATUS",
    },

    "https://admission.uet.edu.pk/news/15": {
        "decision": "KEEP",
        "book": "programs",
        "reason": "REVIEW_KEEP_UNDERGRADUATE_ADVERTISEMENT",
    },

    "https://admission.uet.edu.pk/news/4": {
        "decision": "KEEP",
        "book": "programs",
        "reason": "REVIEW_KEEP_ADMISSIONS_INFORMATION",
    },

    "https://admission.uet.edu.pk/news/2": {
        "decision": "KEEP",
        "book": "scholarships",
        "reason": "REVIEW_KEEP_SCHOLARSHIP_CONTENT",
    },

    "https://admission.uet.edu.pk/news/1": {
        "decision": "KEEP",
        "book": "scholarships",
        "reason": "REVIEW_KEEP_SCHOLARSHIP_CONTENT",
    },

    "https://admission.uet.edu.pk/news/10": {
        "decision": "KEEP",
        "book": "international_admissions",
        "reason": "REVIEW_KEEP_INTERNATIONAL_ADMISSIONS",
    },
}
# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize arbitrary text.
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def normalize_status(value):
    """
    Convert status into canonical uppercase form.
    """

    if value is None:
        return ""

    return str(value).strip().upper()


def normalize_role(value):
    """
    Convert role into canonical lowercase form.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


def normalize_book(value):
    """
    Convert book name into canonical lowercase form.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
    )


def normalize_url(url):
    """
    Normalize URL for duplicate detection.

    Removes:
        - fragments
        - trailing slash
    """

    if not url:
        return ""

    url = str(url).strip()

    if not url:
        return ""

    url = url.split("#", 1)[0]

    return url.rstrip("/")


# ============================================================
# SAFE VALUE EXTRACTION
# ============================================================

def first_value(obj, keys):
    """
    Return the first non-empty value from a dictionary
    using multiple possible key names.
    """

    if not isinstance(obj, dict):
        return None

    for key in keys:

        if key in obj:

            value = obj.get(key)

            if value is not None and value != "":
                return value

    return None


def find_nested_refinement(page):
    """
    Look for refinement information nested inside the page.
    """

    if not isinstance(page, dict):
        return {}

    possible_keys = [
        "refinement",
        "knowledge_refinement",
        "knowledge_refined",
        "classification",
        "decision",
        "review",
    ]

    for key in possible_keys:

        value = page.get(key)

        if isinstance(value, dict):
            return value

    return {}


def get_field(page, keys):
    """
    Search for a field both at the top level and inside
    possible nested refinement structures.
    """

    value = first_value(page, keys)

    if value is not None:
        return value

    nested = find_nested_refinement(page)

    value = first_value(nested, keys)

    if value is not None:
        return value

    return None


# ============================================================
# LOAD JSON
# ============================================================

def load_refined_data():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nKnowledge refinement file was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run knowledgerefinement.py first."
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data


# ============================================================
# EXTRACT PAGES
# ============================================================

def extract_pages(data):
    """
    Extract page records from refinement JSON.
    """

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):

        raise ValueError(
            "Invalid _knowledge_refined.json structure."
        )

    for key in [
        "pages",
        "results",
        "refined_pages",
        "knowledge_pages",
        "items",
    ]:

        value = data.get(key)

        if isinstance(value, list):
            return value

    sources = data.get("sources")

    if isinstance(sources, list):
        return sources

    if all(
        isinstance(value, dict)
        for value in data.values()
    ):

        possible_pages = []

        for key, value in data.items():

            if (
                isinstance(key, str)
                and key.startswith("http")
                and isinstance(value, dict)
            ):

                page = dict(value)

                if "url" not in page:
                    page["url"] = key

                possible_pages.append(page)

        if possible_pages:
            return possible_pages

    raise ValueError(
        "Could not find page records in "
        "_knowledge_refined.json.\n\n"
        "Expected a list or an object containing "
        "'pages'."
    )


# ============================================================
# PAGE NORMALIZATION
# ============================================================

def normalize_page(raw_page):
    """
    Convert raw refinement page into a consistent structure.
    """

    if not isinstance(raw_page, dict):
        return None

    title = get_field(
        raw_page,
        [
            "title",
            "name",
            "page_title",
        ]
    )

    url = get_field(
        raw_page,
        [
            "url",
            "page_url",
            "source_url",
        ]
    )

    status = get_field(
        raw_page,
        [
            "status",
            "Status",
            "decision_status",
        ]
    )

    role = get_field(
        raw_page,
        [
            "role",
            "Role",
            "source_role",
        ]
    )

    book = get_field(
        raw_page,
        [
            "book",
            "Book",
            "book_target",
            "book_name",
        ]
    )

    score = get_field(
        raw_page,
        [
            "score",
            "Score",
        ]
    )

    categories = get_field(
        raw_page,
        [
            "categories",
            "Categories",
        ]
    )

    page_type = get_field(
        raw_page,
        [
            "type",
            "Type",
            "page_type",
        ]
    )

    reason = get_field(
        raw_page,
        [
            "reason",
            "Reason",
        ]
    )

    # --------------------------------------------------------
    # Categories normalization
    # --------------------------------------------------------

    if categories is None:

        categories = []

    elif isinstance(categories, str):

        categories = [
            item.strip()
            for item in categories.split(",")
            if item.strip()
        ]

    elif not isinstance(categories, list):

        categories = [str(categories)]

    categories = [
        str(item).strip().lower()
        for item in categories
        if str(item).strip()
    ]

    # --------------------------------------------------------
    # Canonical record
    # --------------------------------------------------------

    normalized = {

        "title": (
            str(title).strip()
            if title is not None
            else ""
        ),

        "url": (
            str(url).strip()
            if url is not None
            else ""
        ),

        "status": normalize_status(status),

        "role": normalize_role(role),

        "book": normalize_book(book),

        "score": score,

        "categories": categories,

        "type": (
            str(page_type).strip().lower()
            if page_type is not None
            else ""
        ),

        "reason": (
            str(reason).strip()
            if reason is not None
            else ""
        ),
    }

    return normalized


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_pages(pages):

    unique = []

    duplicates = []

    seen = {}

    for page in pages:

        url = normalize_url(
            page.get("url", "")
        )

        if not url:

            unique.append(page)
            continue

        if url not in seen:

            seen[url] = page
            unique.append(page)

        else:

            original = seen[url]

            duplicates.append(
                {
                    "url": url,
                    "existing": original,
                    "candidate": page,
                }
            )

    return unique, duplicates


# ============================================================
# BOOK TARGET FALLBACK
# ============================================================

def infer_book(page):
    """
    Infer a book only when refinement did not explicitly
    provide one.
    """

    categories = set(
        page.get("categories", [])
    )

    page_type = normalize_text(
        page.get("type", "")
    )

    title = normalize_text(
        page.get("title", "")
    )

    # --------------------------------------------------------
    # FAQ
    # --------------------------------------------------------

    if (
        page_type == "faq"
        or "faq" in categories
    ):
        return "faq"

    # --------------------------------------------------------
    # International
    # --------------------------------------------------------

    if (
        "international" in categories
        or "foreign" in title
    ):
        return "international_admissions"

    # --------------------------------------------------------
    # ECAT
    # --------------------------------------------------------

    if "ecat" in categories:
        return "ecat"

    # --------------------------------------------------------
    # Deadlines
    # --------------------------------------------------------

    if "deadlines" in categories:
        return "deadlines"

    # --------------------------------------------------------
    # Admission process
    # --------------------------------------------------------

    if "admission_process" in categories:
        return "admission_process"

    # --------------------------------------------------------
    # Eligibility
    # --------------------------------------------------------

    if "eligibility" in categories:
        return "eligibility"

    # --------------------------------------------------------
    # Fees
    # --------------------------------------------------------

    if "fees" in categories:
        return "fees"

    # --------------------------------------------------------
    # Temporal
    # --------------------------------------------------------

    if (
        "temporal" in categories
        or "temporal_updates" in categories
    ):
        return "temporal_updates"

    # --------------------------------------------------------
    # Programs
    # --------------------------------------------------------

    if (
        "programs" in categories
        or page_type in {
            "program",
            "admission",
        }
    ):
        return "programs"

    return ""


# ============================================================
# REVIEW DECISION
# ============================================================

def get_review_decision(page):
    """
    Return the final manually assessed REVIEW decision.

    REVIEW pages are intentionally handled by explicit
    decisions rather than broad keyword matching.

    Returns:

        {
            "decision": "KEEP" / "EXCLUDE",
            "book": "...",
            "reason": "...",
        }

    or:

        None

    if the REVIEW page has not been manually decided yet.
    """

    url = normalize_url(
        page.get("url", "")
    )

    decision = REVIEW_DECISIONS.get(url)

    if decision is None:
        return None

    return {
        "decision": str(
            decision.get(
                "decision",
                ""
            )
        ).strip().upper(),

        "book": normalize_book(
            decision.get(
                "book",
                ""
            )
        ),

        "reason": str(
            decision.get(
                "reason",
                "REVIEW_DECISION"
            )
        ).strip(),
    }


# ============================================================
# REVIEW RESOLUTION
# ============================================================

def resolve_review_page(page):
    """
    Apply the final manual decision for a REVIEW page.

    This is the ONLY decision path for REVIEW pages.

    A REVIEW page is never automatically rescued merely
    because its title contains words such as:

        deadline
        result
        merit
        admission
        ECAT

    Those keyword heuristics were deliberately removed.

    Returns:

        (True, reason, signals)

    for a kept REVIEW page.

    Returns:

        (False, reason, signals)

    for an excluded REVIEW page.
    """

    decision = get_review_decision(
        page
    )

    # --------------------------------------------------------
    # No manual decision
    # --------------------------------------------------------

    if decision is None:

        return (
            False,
            "REVIEW_UNDECIDED",
            [],
        )

    # --------------------------------------------------------
    # EXCLUDE
    # --------------------------------------------------------

    if decision["decision"] == "EXCLUDE":

        return (
            False,
            decision["reason"],
            [],
        )

    # --------------------------------------------------------
    # KEEP
    # --------------------------------------------------------

    if decision["decision"] == "KEEP":

        book = decision["book"]

        # ----------------------------------------------------
        # A kept REVIEW page MUST have a valid book.
        # ----------------------------------------------------

        if not book:

            return (
                False,
                "REVIEW_KEEP_NO_BOOK",
                [],
            )

        if book not in BOOK_NAMES:

            return (
                False,
                f"REVIEW_KEEP_UNKNOWN_BOOK:{book}",
                [],
            )

        page["book"] = book

        return (
            True,
            decision["reason"],
            [],
        )

    # --------------------------------------------------------
    # Invalid manual decision
    # --------------------------------------------------------

    return (
        False,
        f"INVALID_REVIEW_DECISION:{decision['decision']}",
        [],
    )


# ============================================================
# DETERMINE USABILITY
# ============================================================

def determine_usability(page):

    status = page.get("status", "")
    role = page.get("role", "")
    book = page.get("book", "")

    # --------------------------------------------------------
    # Missing status
    # --------------------------------------------------------

    if not status:

        return (
            False,
            "UNKNOWN_STATUS",
            [],
        )

    # --------------------------------------------------------
    # Explicit skip
    # --------------------------------------------------------

    if status == "SKIP":

        return (
            False,
            "SKIP_STATUS",
            [],
        )

    # --------------------------------------------------------
    # REVIEW
    #
    # REVIEW is resolved by the manually assessed decisions
    # above.
    # --------------------------------------------------------

    if status == "REVIEW":

        return resolve_review_page(
            page
        )

    # --------------------------------------------------------
    # Invalid status
    # --------------------------------------------------------

    if status not in VALID_STATUSES:

        return (
            False,
            f"INVALID_STATUS:{status}",
            [],
        )

    # --------------------------------------------------------
    # Operational/promotional material
    # --------------------------------------------------------

    if role in {
        "operational",
        "promotional",
    }:

        return (
            False,
            f"ROLE_{role.upper()}",
            [],
        )

    # --------------------------------------------------------
    # Missing book can sometimes be recovered
    # --------------------------------------------------------

    if not book:

        inferred = infer_book(page)

        if inferred:

            page["book"] = inferred
            book = inferred

    # --------------------------------------------------------
    # Still no book
    # --------------------------------------------------------

    if not book:

        return (
            False,
            "NO_BOOK_TARGET",
            [],
        )

    # --------------------------------------------------------
    # Unknown book
    # --------------------------------------------------------

    if book not in BOOK_NAMES:

        return (
            False,
            f"UNKNOWN_BOOK:{book}",
            [],
        )

    # --------------------------------------------------------
    # Usable
    # --------------------------------------------------------

    return (
        True,
        "USABLE",
        [],
    )


# ============================================================
# BUILD BOOKS
# ============================================================

def build_books(pages):

    books = defaultdict(list)

    excluded = []

    unassigned = []

    usable_pages = []

    rescued_reviews = []

    for page in pages:

        usable, reason, signals = determine_usability(
            page
        )

        # ----------------------------------------------------
        # Excluded
        # ----------------------------------------------------

        if not usable:

            excluded.append(
                {
                    "page": page,
                    "reason": reason,
                    "signals": signals,
                }
            )

            continue

        # ----------------------------------------------------
        # Track kept REVIEW pages
        # ----------------------------------------------------

        if page.get("status") == "REVIEW":

            rescued_reviews.append(
                {
                    "page": page,
                    "signals": signals,
                    "reason": reason,
                }
            )

        # ----------------------------------------------------
        # Book
        # ----------------------------------------------------

        book = page.get("book", "")

        if not book:

            unassigned.append(page)

            continue

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        if book not in BOOK_NAMES:

            excluded.append(
                {
                    "page": page,
                    "reason": f"UNKNOWN_BOOK:{book}",
                    "signals": signals,
                }
            )

            continue

        # ----------------------------------------------------
        # Book record
        # ----------------------------------------------------

        record = {

            "title": page.get(
                "title",
                ""
            ),

            "url": page.get(
                "url",
                ""
            ),

            "status": page.get(
                "status",
                ""
            ),

            "role": page.get(
                "role",
                ""
            ),

            "score": page.get(
                "score"
            ),

            "categories": page.get(
                "categories",
                []
            ),

            "type": page.get(
                "type",
                ""
            ),

            "builder_reason": reason,

        }

        # ----------------------------------------------------
        # Keep REVIEW decision information
        # ----------------------------------------------------

        if page.get("status") == "REVIEW":

            record["review_decision"] = "KEEP"

        # ----------------------------------------------------
        # Book record
        # ----------------------------------------------------

        if signals:

            record["temporal_signals"] = signals

        books[book].append(record)

        usable_pages.append(page)

    return (
        dict(books),
        excluded,
        unassigned,
        usable_pages,
        rescued_reviews,
    )


# ============================================================
# SORT BOOKS
# ============================================================

def sort_books(books):

    sorted_books = {}

    for book_name in sorted(
        books.keys()
    ):

        pages = books[book_name]

        pages.sort(
            key=lambda item: (
                -(
                    float(
                        item["score"]
                    )
                    if isinstance(
                        item.get("score"),
                        (int, float)
                    )
                    else 0
                ),
                item.get(
                    "title",
                    ""
                ).lower(),
            )
        )

        sorted_books[book_name] = pages

    return sorted_books


# ============================================================
# BUILD OUTPUT
# ============================================================

def build_output(
    input_count,
    unique_count,
    duplicate_count,
    books,
    excluded,
    unassigned,
    duplicate_records,
    rescued_reviews,
):

    total_book_pages = sum(
        len(pages)
        for pages in books.values()
    )

    output = {

        "source":
            "UET Admissions Portal",

        "stage":
            "knowledge_books",

        "input_file":
            str(INPUT_FILE),

        "output_file":
            str(OUTPUT_FILE),

        "counts": {

            "input_pages":
                input_count,

            "unique_pages":
                unique_count,

            "duplicates":
                duplicate_count,

            "usable_pages":
                total_book_pages,

            "excluded_pages":
                len(excluded),

            "unassigned_pages":
                len(unassigned),

            "books":
                len(books),

            "rescued_review_pages":
                len(rescued_reviews),
        },

        "books":
            books,

        "duplicates": [

            {

                "url":
                    item["url"],

                "existing": {

                    "title":
                        item["existing"].get(
                            "title",
                            ""
                        ),

                    "url":
                        item["existing"].get(
                            "url",
                            ""
                        ),
                },

                "candidate": {

                    "title":
                        item["candidate"].get(
                            "title",
                            ""
                        ),

                    "url":
                        item["candidate"].get(
                            "url",
                            ""
                        ),
                },
            }

            for item in duplicate_records
        ],

        "unassigned": [

            {

                "title":
                    page.get(
                        "title",
                        ""
                    ),

                "url":
                    page.get(
                        "url",
                        ""
                    ),

                "status":
                    page.get(
                        "status",
                        ""
                    ),

                "role":
                    page.get(
                        "role",
                        ""
                    ),

                "book":
                    page.get(
                        "book",
                        ""
                    ),
            }

            for page in unassigned
        ],

        "excluded": [

            {

                "title":
                    item["page"].get(
                        "title",
                        ""
                    ),

                "url":
                    item["page"].get(
                        "url",
                        ""
                    ),

                "status":
                    item["page"].get(
                        "status",
                        ""
                    ),

                "role":
                    item["page"].get(
                        "role",
                        ""
                    ),

                "book":
                    item["page"].get(
                        "book",
                        ""
                    ),

                "reason":
                    item["reason"],

                "temporal_signals":
                    item.get(
                        "signals",
                        []
                    ),
            }

            for item in excluded
        ],

        "rescued_review_pages": [

            {

                "title":
                    item["page"].get(
                        "title",
                        ""
                    ),

                "url":
                    item["page"].get(
                        "url",
                        ""
                    ),

                "book":
                    item["page"].get(
                        "book",
                        ""
                    ),

                "signals":
                    item["signals"],

                "reason":
                    item["reason"],
            }

            for item in rescued_reviews
        ],
    }

    return output


# ============================================================
# VALIDATION
# ============================================================

def validate_output(output):

    errors = []

    books = output.get(
        "books",
        {}
    )

    counts = output.get(
        "counts",
        {}
    )

    # --------------------------------------------------------
    # Every book must contain a list
    # --------------------------------------------------------

    for book_name, pages in books.items():

        if not isinstance(
            pages,
            list
        ):

            errors.append(
                f"Book '{book_name}' is not a list."
            )

    # --------------------------------------------------------
    # Every book must be known
    # --------------------------------------------------------

    for book_name in books.keys():

        if book_name not in BOOK_NAMES:

            errors.append(
                f"Unknown book '{book_name}'."
            )

    # --------------------------------------------------------
    # Every page must have URL/title
    # --------------------------------------------------------

    for book_name, pages in books.items():

        for page in pages:

            if not page.get("url"):

                errors.append(
                    f"Missing URL in "
                    f"book '{book_name}'."
                )

            if not page.get("title"):

                errors.append(
                    f"Missing title in "
                    f"book '{book_name}'."
                )

            if page.get("status") not in {
                "CORE",
                "SUPPORTING",
                "TEMPORAL",
                "REVIEW",
            }:

                errors.append(
                    "Invalid status in usable "
                    f"book: {page.get('status')}"
                )

    # --------------------------------------------------------
    # Count consistency
    # --------------------------------------------------------

    actual_usable = sum(
        len(pages)
        for pages in books.values()
    )

    if actual_usable != counts.get(
        "usable_pages",
        actual_usable
    ):

        errors.append(
            "Usable page count does not "
            "match book contents."
        )

    # --------------------------------------------------------
    # REVIEW pages must have KEEP decision
    # --------------------------------------------------------

    for book_name, pages in books.items():

        for page in pages:

            if page.get("status") == "REVIEW":

                if page.get(
                    "review_decision"
                ) != "KEEP":

                    errors.append(
                        "REVIEW page included "
                        "without KEEP decision: "
                        f"{page.get('title', '')}"
                    )

    # --------------------------------------------------------
    # REVIEW pages must never appear as excluded
    # without a valid decision reason.
    # --------------------------------------------------------

    for item in output.get(
        "excluded",
        []
    ):

        page = item.get(
            "page",
            {}
        )

        if page.get("status") == "REVIEW":

            reason = item.get(
                "reason",
                ""
            )

            if not reason.startswith(
                "REVIEW_"
            ):

                errors.append(
                    "REVIEW page excluded "
                    "without REVIEW reason: "
                    f"{page.get('title', '')}"
                )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — KNOWLEDGE BOOK BUILDER"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    data = load_refined_data()

    raw_pages = extract_pages(data)

    print()
    print(
        f"Pages available: {len(raw_pages)}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    pages = []

    for raw_page in raw_pages:

        page = normalize_page(
            raw_page
        )

        if page is not None:

            pages.append(page)

    print(
        f"Pages normalized: {len(pages)}"
    )

    # --------------------------------------------------------
    # Refinement field check
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("REFINEMENT FIELD CHECK")
    print("=" * 70)

    status_counts = defaultdict(int)
    role_counts = defaultdict(int)
    book_counts = defaultdict(int)
    review_decision_counts = defaultdict(int)

    for page in pages:

        status_counts[
            page.get(
                "status",
                ""
            )
            or "<EMPTY>"
        ] += 1

        role_counts[
            page.get(
                "role",
                ""
            )
            or "<EMPTY>"
        ] += 1

        book_counts[
            page.get(
                "book",
                ""
            )
            or "<EMPTY>"
        ] += 1

        # ----------------------------------------------------
        # REVIEW decision check
        # ----------------------------------------------------

        if page.get("status") == "REVIEW":

            decision = get_review_decision(
                page
            )

            if decision is None:

                review_decision_counts[
                    "<UNDECIDED>"
                ] += 1

            else:

                review_decision_counts[
                    decision["decision"]
                ] += 1

    print()
    print("STATUS VALUES:")

    for key, value in sorted(
        status_counts.items()
    ):

        print(
            f"  {key:<20} : {value}"
        )

    print()
    print("ROLE VALUES:")

    for key, value in sorted(
        role_counts.items()
    ):

        print(
            f"  {key:<20} : {value}"
        )

    print()
    print("BOOK VALUES:")

    for key, value in sorted(
        book_counts.items()
    ):

        print(
            f"  {key:<30} : {value}"
        )

    print()
    print("REVIEW DECISIONS:")

    for key, value in sorted(
        review_decision_counts.items()
    ):

        print(
            f"  {key:<20} : {value}"
        )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    print()
    print(
        "Deduplicating pages..."
    )

    (
        unique_pages,
        duplicate_records
    ) = deduplicate_pages(
        pages
    )

    print(
        f"Unique pages: "
        f"{len(unique_pages)}"
    )

    print(
        f"Duplicates: "
        f"{len(duplicate_records)}"
    )

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    print()
    print(
        "Building knowledge books..."
    )

    (
        books,
        excluded,
        unassigned,
        usable_pages,
        rescued_reviews,
    ) = build_books(
        unique_pages
    )

    books = sort_books(
        books
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "KNOWLEDGE BOOK BUILD RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"Input pages: "
        f"{len(pages)}"
    )

    print(
        f"Unique pages: "
        f"{len(unique_pages)}"
    )

    print(
        f"Duplicates: "
        f"{len(duplicate_records)}"
    )

    print(
        f"Usable: "
        f"{len(usable_pages)}"
    )

    print(
        f"Excluded: "
        f"{len(excluded)}"
    )

    print(
        f"Unassigned: "
        f"{len(unassigned)}"
    )

    print(
        f"REVIEW kept: "
        f"{len(rescued_reviews)}"
    )

    # --------------------------------------------------------
    # Books
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "KNOWLEDGE BOOKS"
    )
    print("=" * 70)

    if not books:

        print(
            "No books were created."
        )

    else:

        for book_name, book_pages in books.items():

            print()
            print(
                f"[{book_name}]"
            )

            print(
                f"Pages: "
                f"{len(book_pages)}"
            )

            for index, page in enumerate(
                book_pages,
                start=1
            ):

                print(
                    f"  [{index:03d}] "
                    f"{page['title']}"
                )

                print(
                    f"        "
                    f"{page['url']}"
                )

                print(
                    f"        Status: "
                    f"{page['status']} | "
                    f"Role: "
                    f"{page['role']} | "
                    f"Score: "
                    f"{page['score']}"
                )

                if page.get(
                    "status"
                ) == "REVIEW":

                    print(
                        f"        "
                        f"REVIEW KEPT"
                    )

                    print(
                        f"        Reason: "
                        f"{page.get('builder_reason', '')}"
                    )

    # --------------------------------------------------------
    # Kept REVIEW pages
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "KEPT REVIEW PAGES"
    )
    print("=" * 70)

    if not rescued_reviews:

        print("None")

    else:

        for item in rescued_reviews:

            page = item["page"]

            print()
            print(
                f"  {page.get('title', '')}"
            )

            print(
                f"  {page.get('url', '')}"
            )

            print(
                f"  Book: "
                f"{page.get('book', '')}"
            )

            print(
                f"  Decision: KEEP"
            )

            print(
                f"  Reason: "
                f"{item['reason']}"
            )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "DUPLICATES"
    )
    print("=" * 70)

    if not duplicate_records:

        print("None")

    else:

        for item in duplicate_records:

            print()
            print(
                f"DUPLICATE: "
                f"{item['url']}"
            )

            print(
                f"  Existing: "
                f"{item['existing'].get('title', '')}"
            )

            print(
                f"  Candidate: "
                f"{item['candidate'].get('title', '')}"
            )

            print(
                f"  Kept: "
                f"{item['existing'].get('title', '')}"
            )

    # --------------------------------------------------------
    # Unassigned
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "UNASSIGNED PAGES"
    )
    print("=" * 70)

    if not unassigned:

        print("None")

    else:

        for page in unassigned:

            print()
            print(
                f" — "
                f"{page.get('title', '')}"
            )

            print(
                page.get(
                    'url',
                    ''
                )
            )

            print(
                f"Status: "
                f"{page.get('status', '')}"
            )

            print(
                f"Role: "
                f"{page.get('role', '')}"
            )

            print(
                f"Book: "
                f"{page.get('book', '')}"
            )

    # --------------------------------------------------------
    # Excluded
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "EXCLUDED"
    )
    print("=" * 70)

    if not excluded:

        print("None")

    else:

        for item in excluded:

            page = item["page"]

            print()
            print(
                f" — "
                f"{page.get('title', '')}"
            )

            print(
                page.get(
                    'url',
                    ''
                )
            )

            print(
                f"Status: "
                f"{page.get('status', '')}"
            )

            print(
                f"Role: "
                f"{page.get('role', '')}"
            )

            print(
                f"Book: "
                f"{page.get('book', '')}"
            )

            print(
                f"Reason: "
                f"{item['reason']}"
            )

            if item.get(
                "signals"
            ):

                print(
                    f"Signals: "
                    f"{', '.join(item['signals'])}"
                )

    # --------------------------------------------------------
    # Build output
    # --------------------------------------------------------

    output = build_output(

        input_count=len(
            pages
        ),

        unique_count=len(
            unique_pages
        ),

        duplicate_count=len(
            duplicate_records
        ),

        books=books,

        excluded=excluded,

        unassigned=unassigned,

        duplicate_records=
            duplicate_records,

        rescued_reviews=
            rescued_reviews,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate_output(
        output
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
            "Knowledge book validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Saved
    # --------------------------------------------------------

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