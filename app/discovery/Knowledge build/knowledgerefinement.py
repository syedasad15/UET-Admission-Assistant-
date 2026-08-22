from pathlib import Path
import json
import re
from urllib.parse import urlsplit, urlunsplit


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"D:\UET Chatbot")

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "inventory"
    / "admission"
    / "_pages_reviewed.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "inventory"
    / "admission"
    / "_knowledge_refined.json"
)


# ============================================================
# KNOWLEDGE CATEGORIES
# ============================================================

CATEGORY_KEYWORDS = {
    "eligibility": [
        "eligibility",
        "eligible",
        "qualification",
        "qualifications",
        "requirements",
        "criteria",
        "minimum marks",
        "minimum percentage",
        "equivalent",
        "who can apply",
    ],

    "fees": [
        "fee",
        "fees",
        "tuition",
        "challan",
        "payment",
        "dues",
        "charges",
        "cost",
    ],

    "deadlines": [
        "deadline",
        "last date",
        "last day",
        "closing date",
        "extended deadline",
        "extend",
        "extension",
        "apply by",
        "applications close",
        "registration closes",
        "registration closed",
        "due date",
    ],

    "merit": [
        "merit list",
        "merit lists",
        "first merit",
        "1st merit",
        "second merit",
        "2nd merit",
        "third merit",
        "3rd merit",
        "merit position",
        "merit number",
        "selected candidates",
        "selection list",
        "selected candidate",
    ],

    "scholarships": [
        "scholarship",
        "scholarships",
        "financial aid",
        "fully funded",
        "funded",
        "stipend",
        "hec scholarship",
    ],

    "admission_process": [
        "admission process",
        "apply",
        "application process",
        "how to apply",
        "submission",
        "documents",
        "document submission",
        "selected candidates",
        "confirmation",
        "enrollment",
        "joining",
        "admission procedure",
        "admission instructions",
    ],

    "documents": [
        "documents",
        "required documents",
        "original documents",
        "document verification",
        "attested",
        "submission of documents",
    ],

    "ecat": [
        "ecat",
        "entry test",
        "admit card",
        "ecat result",
        "ecat registration",
        "ecat phase",
        "ecat-01",
        "ecat-02",
    ],

    "schedule": [
        "schedule",
        "date",
        "dates",
        "timeline",
        "calendar",
        "announcement date",
        "releasing",
        "release date",
        "test date",
        "orientation",
    ],

    "hostel": [
        "hostel",
        "hostels",
        "accommodation",
        "room allotment",
        "hostel allotment",
    ],

    "international": [
        "international",
        "foreign student",
        "foreign students",
        "international student",
        "international students",
        "overseas",
    ],

    "quota": [
        "quota",
        "reserved seats",
        "reserved seat",
        "self finance",
        "self-finance",
    ],

    "programs": [
        "program",
        "programs",
        "bachelor",
        "bachelors",
        "undergraduate",
        "master",
        "masters",
        "m.sc",
        "m.phil",
        "ms",
        "ph.d",
        "phd",
        "associate degree",
        "degree program",
    ],

    "contact": [
        "contact",
        "admission office",
        "admission cell",
        "phone",
        "telephone",
        "email",
        "query",
        "queries",
        "help desk",
    ],
}


# ============================================================
# STRONG TEMPORAL SIGNALS
# These are intentionally strong because this is the issue
# we are fixing: useful admission news must not disappear.
# ============================================================

TEMPORAL_SIGNALS = {
    "deadline": [
        "last date",
        "last day",
        "deadline",
        "apply by",
        "extended deadline",
        "deadline extended",
        "deadline extension",
        "applications close",
        "registration closes",
        "registration closed",
    ],

    "merit": [
        "merit list",
        "1st merit",
        "2nd merit",
        "3rd merit",
        "first merit",
        "second merit",
        "third merit",
        "selected candidates",
        "selection list",
    ],

    "fee": [
        "fee schedule",
        "fee structure",
        "undergraduate fee",
        "tuition fee",
        "fee payment",
        "fee deadline",
    ],

    "schedule": [
        "admission schedule",
        "admission process schedule",
        "schedule",
        "timeline",
        "releasing on",
        "release date",
    ],

    "ecat": [
        "ecat result",
        "ecat registration",
        "ecat admit card",
        "ecat phase",
        "ecat 2026",
        "entry test result",
    ],

    "admission_process": [
        "admission process",
        "selected candidates",
        "document submission",
        "how to complete documents",
        "admission instructions",
        "application process",
    ],
}


# ============================================================
# PROMOTIONAL / LOW VALUE SIGNALS
# ============================================================

PROMOTIONAL_SIGNALS = [
    "record response",
    "welcome to uet",
    "where your future begins",
    "meet our international student",
    "student from",
    "podcast series",
    "podcast",
    "message from vc",
]


OPERATIONAL_SIGNALS = [
    "network services",
    "network restored",
    "portal restored",
    "system restored",
    "server",
    "maintenance",
    "technical issue",
]


# ============================================================
# HELPERS
# ============================================================

def normalize_url(url):
    """
    Normalize URLs for duplicate detection.
    Removes fragments and normalizes trailing slash.
    """
    if not url:
        return ""

    url = str(url).strip()

    try:
        parts = urlsplit(url)

        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        path = parts.path.rstrip("/")

        if not path:
            path = ""

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                parts.query,
                "",
            )
        )
    except Exception:
        return url.rstrip("/")


def get_text(page):
    """
    Build searchable text from whatever fields are available
    in _pages_reviewed.json.
    """
    fields = [
        "title",
        "name",
        "description",
        "content",
        "text",
        "body",
        "summary",
        "excerpt",
        "url",
        "type",
    ]

    values = []

    for field in fields:
        value = page.get(field)

        if isinstance(value, str):
            values.append(value)

        elif isinstance(value, list):
            values.extend(str(x) for x in value)

        elif isinstance(value, dict):
            values.append(json.dumps(value, ensure_ascii=False))

    return " ".join(values).lower()


def detect_categories(text):
    categories = set()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                categories.add(category)
                break

    return sorted(categories)


def detect_temporal_signals(text):
    found = []

    for signal_type, keywords in TEMPORAL_SIGNALS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                found.append(signal_type)
                break

    return sorted(set(found))


def contains_any(text, signals):
    return any(signal.lower() in text for signal in signals)


def is_news(page):
    page_type = str(page.get("type", "")).lower()

    title = str(
        page.get("title")
        or page.get("name")
        or ""
    ).lower()

    url = str(page.get("url", "")).lower()

    return (
        page_type == "news"
        or "/news/" in url
        or "news" in title
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_page(page):
    text = get_text(page)

    title = str(
        page.get("title")
        or page.get("name")
        or ""
    ).strip()

    page_type = str(page.get("type", "")).lower()

    categories = detect_categories(text)

    temporal_signals = detect_temporal_signals(text)

    news = is_news(page)

    promotional = contains_any(
        text,
        PROMOTIONAL_SIGNALS
    )

    operational = contains_any(
        text,
        OPERATIONAL_SIGNALS
    )

    # --------------------------------------------------------
    # 1. OPERATIONAL CONTENT
    # --------------------------------------------------------

    if operational and not temporal_signals:
        return {
            "status": "SKIP",
            "role": "operational",
            "score": 0,
            "reason": "Operational/technical information is not admission knowledge",
            "categories": categories,
            "book": choose_book(categories),
        }

    # --------------------------------------------------------
    # 2. PROMOTIONAL CONTENT
    #
    # Promotional pages remain SKIP unless they also contain
    # strong actionable admission signals.
    # --------------------------------------------------------

    if promotional and not temporal_signals:
        return {
            "status": "SKIP",
            "role": "promotional",
            "score": 0,
            "reason": "Page appears promotional or low-value for the knowledge base",
            "categories": categories,
            "book": choose_book(categories),
        }

    # --------------------------------------------------------
    # 3. STRONG TEMPORAL NEWS
    #
    # THIS IS THE IMPORTANT CHANGE.
    #
    # A news page containing a deadline, merit list, fee,
    # schedule, ECAT result, or admission-process update
    # is retained.
    # --------------------------------------------------------

    if news and temporal_signals:

        # Deadline / merit / admission process information
        # is highly actionable.
        strong_actionable = any(
            signal in temporal_signals
            for signal in [
                "deadline",
                "merit",
                "fee",
                "admission_process",
            ]
        )

        if strong_actionable:
            return {
                "status": "CORE",
                "role": "temporal",
                "score": 100,
                "reason": "News page contains actionable admission information",
                "categories": categories,
                "book": choose_temporal_book(categories, temporal_signals),
            }

        # ECAT/schedule updates are also retained but marked
        # temporal/supporting rather than discarded.
        return {
            "status": "TEMPORAL",
            "role": "temporal",
            "score": 85,
            "reason": "News page contains time-sensitive admission information",
            "categories": categories,
            "book": choose_temporal_book(categories, temporal_signals),
        }

    # --------------------------------------------------------
    # 4. NON-NEWS CORE PAGES
    # --------------------------------------------------------

    if page_type in {
        "program",
        "faq",
        "admission",
        "download",
        "foreign_students",
    }:

        if len(categories) >= 2:
            return {
                "status": "CORE",
                "role": "core",
                "score": 100,
                "reason": "Core admission knowledge source",
                "categories": categories,
                "book": choose_book(categories),
            }

        if categories:
            return {
                "status": "SUPPORTING",
                "role": "core",
                "score": 75,
                "reason": "Useful supporting admission information",
                "categories": categories,
                "book": choose_book(categories),
            }

    # --------------------------------------------------------
    # 5. GENERIC PAGES WITH ACTIONABLE SIGNALS
    # --------------------------------------------------------

    if temporal_signals:
        return {
            "status": "TEMPORAL",
            "role": "temporal",
            "score": 80,
            "reason": "Contains time-sensitive admission information",
            "categories": categories,
            "book": choose_temporal_book(categories, temporal_signals),
        }

    # --------------------------------------------------------
    # 6. WEAK PROGRAM PAGE
    # --------------------------------------------------------

    if "programs" in categories:
        return {
            "status": "REVIEW",
            "role": "supporting",
            "score": 30,
            "reason": "Page contains program information but not enough actionable admission knowledge",
            "categories": categories,
            "book": "programs",
        }

    # --------------------------------------------------------
    # 7. DEFAULT
    # --------------------------------------------------------

    return {
        "status": "REVIEW",
        "role": "supporting",
        "score": 20,
        "reason": "Page does not contain enough recognized admission knowledge",
        "categories": categories,
        "book": choose_book(categories),
    }


# ============================================================
# BOOK SELECTION
# ============================================================

def choose_temporal_book(categories, temporal_signals):

    # Deadline always gets deadline book.
    if "deadline" in temporal_signals:
        return "deadlines"

    # Merit lists get merit information under admission process
    # for now, while retaining the temporal role.
    if "merit" in temporal_signals:
        return "admission_process"

    if "fee" in temporal_signals:
        return "fees"

    if "ecat" in temporal_signals:
        return "ecat"

    if "schedule" in temporal_signals:
        return "admission_process"

    if "admission_process" in temporal_signals:
        return "admission_process"

    return choose_book(categories)


def choose_book(categories):

    # Most specific books first.
    priority = [
        ("deadlines", "deadlines"),
        ("ecat", "ecat"),
        ("eligibility", "eligibility"),
        ("fees", "fees"),
        ("admission_process", "admission_process"),
        ("scholarships", "scholarships"),
        ("hostel", "hostel"),
        ("international", "international_admissions"),
        ("faq", "faq"),
        ("programs", "programs"),
    ]

    for category, book in priority:
        if category in categories:
            return book

    return "temporal_updates"


# ============================================================
# DUPLICATE DETECTION
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

        if url in seen:

            duplicates.append(
                {
                    "url": url,
                    "original": seen[url],
                    "candidate": page.get("title")
                    or page.get("name")
                    or "",
                }
            )

            continue

        seen[url] = (
            page.get("title")
            or page.get("name")
            or ""
        )

        unique.append(page)

    return unique, duplicates


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("UET ADMISSION — KNOWLEDGE REFINEMENT")
    print("=" * 70)
    print()

    print("Reading:")
    print(INPUT_FILE)
    print()

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    # Support either:
    #   [...]
    # or
    #   {"pages": [...]}
    if isinstance(data, list):
        pages = data

    elif isinstance(data, dict):
        if isinstance(data.get("pages"), list):
            pages = data["pages"]

        elif isinstance(data.get("items"), list):
            pages = data["items"]

        else:
            raise ValueError(
                "Could not find pages/items list in input JSON."
            )

    else:
        raise ValueError(
            "Input JSON must be a list or object."
        )

    print(f"Pages to refine: {len(pages)}")
    print()

    refined = []

    # --------------------------------------------------------
    # CLASSIFY
    # --------------------------------------------------------

    for index, page in enumerate(pages, start=1):

        result = classify_page(page)

        title = (
            page.get("title")
            or page.get("name")
            or "Untitled"
        )

        url = page.get("url", "")

        # Preserve original page data.
        item = dict(page)

        # Add / overwrite refinement fields.
        item["status"] = result["status"]
        item["role"] = result["role"]
        item["score"] = result["score"]
        item["categories"] = result["categories"]
        item["book"] = result["book"]
        item["refinement_reason"] = result["reason"]

        # Extra fields specifically useful for temporal content.
        temporal_signals = detect_temporal_signals(
            get_text(page)
        )

        item["temporal_signals"] = temporal_signals

        refined.append(item)

        print(
            f"[{index:03d}/{len(pages):03d}] {title}"
        )
        print(f"URL: {url}")
        print(f"Status: {result['status']}")
        print(f"Type: {page.get('type', '')}")
        print(f"Role: {result['role']}")
        print(f"Score: {result['score']}")
        print(
            "Categories: "
            + (
                ", ".join(result["categories"])
                if result["categories"]
                else "none"
            )
        )
        print(f"Book: {result['book']}")

        if temporal_signals:
            print(
                "Temporal signals: "
                + ", ".join(temporal_signals)
            )

        print()

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    unique_pages, duplicates = deduplicate_pages(refined)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    status_counts = {}

    role_counts = {}

    book_counts = {}

    for page in unique_pages:

        status = page.get("status", "UNKNOWN")
        role = page.get("role", "unknown")
        book = page.get("book", "unknown")

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

        role_counts[role] = (
            role_counts.get(role, 0) + 1
        )

        book_counts[book] = (
            book_counts.get(book, 0) + 1
        )

    print("=" * 70)
    print("KNOWLEDGE REFINEMENT RESULT")
    print("=" * 70)
    print()

    print(f"Pages: {len(pages)}")
    print()

    print("STATUS")

    for status in [
        "CORE",
        "SUPPORTING",
        "TEMPORAL",
        "REVIEW",
        "SKIP",
    ]:
        print(
            f"  {status:<12}: "
            f"{status_counts.get(status, 0)}"
        )

    print()

    print("SOURCE ROLES")

    for role in [
        "core",
        "temporal",
        "supporting",
        "operational",
        "promotional",
    ]:
        print(
            f"  {role:<15}: "
            f"{role_counts.get(role, 0)}"
        )

    print()

    print("BOOK TARGETS")

    for book in sorted(book_counts):
        print(
            f"  {book:<30}: "
            f"{book_counts[book]}"
        )

    # --------------------------------------------------------
    # TEMPORAL CHECK
    # --------------------------------------------------------

    temporal_pages = [
        page
        for page in unique_pages
        if page.get("role") == "temporal"
        or page.get("status") == "TEMPORAL"
    ]

    print()
    print("=" * 70)
    print("ACTIONABLE TEMPORAL KNOWLEDGE")
    print("=" * 70)
    print()

    if temporal_pages:

        for page in temporal_pages:

            print(
                f"[{page.get('status')}] "
                f"{page.get('title') or page.get('name')}"
            )

            print(
                f"  URL: {page.get('url', '')}"
            )

            print(
                f"  Book: {page.get('book', '')}"
            )

            print(
                "  Signals: "
                + (
                    ", ".join(
                        page.get(
                            "temporal_signals",
                            []
                        )
                    )
                    or "none"
                )
            )

            print()

    else:
        print("None")
        print()

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    print("=" * 70)
    print("DUPLICATES")
    print("=" * 70)

    if duplicates:

        for duplicate in duplicates:

            print(
                f"DUPLICATE: {duplicate['url']}"
            )

            print(
                f"  Original: "
                f"{duplicate['original']}"
            )

            print(
                f"  Candidate: "
                f"{duplicate['candidate']}"
            )

    else:
        print("None")

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "metadata": {
            "source": str(INPUT_FILE),
            "total_pages": len(pages),
            "unique_pages": len(unique_pages),
            "duplicates": len(duplicates),
            "refinement_version": "2.0",
            "policy": (
                "Retain actionable admission information "
                "even when published as news."
            ),
        },

        "status_counts": status_counts,

        "role_counts": role_counts,

        "book_counts": book_counts,

        "duplicates": duplicates,

        "pages": unique_pages,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("SAVED")
    print("=" * 70)
    print()
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()