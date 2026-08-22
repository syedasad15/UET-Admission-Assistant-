
from pathlib import Path
import json
import re

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

ADMISSION_ROOT = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

INPUT_FILE = (
    ADMISSION_ROOT
    / "_content_targets.json"
)

OUTPUT_FILE = (
    ADMISSION_ROOT
    / "_content_targets_reviewed.json"
)

BASE_DOMAIN = "https://admission.uet.edu.pk"


# ============================================================
# REVIEW RULES
# ============================================================

# Pages that are directly useful for an admission chatbot.
KEEP_PAGE_PATTERNS = [
    r"/program/",
    r"/faqs(?:/|$)",
    r"/foreign-students(?:/|$)",
    r"/downloads(?:/|$)",
]

# Pages that may contain useful information but require
# freshness/relevance review.
REVIEW_PAGE_PATTERNS = [
    r"/news(?:/|$)",
]

# ------------------------------------------------------------
# IMPORTANT:
#
# These are NOT simply "SKIP" anymore.
#
# They are ACTION pages.
#
# The chatbot may need to give their links to users.
#
# Example:
#   User: "I forgot my challan number"
#   Bot: "You can retrieve your challan here: <link>"
# ------------------------------------------------------------

ACTION_PAGE_PATTERNS = [
    r"/account/",
    r"/login(?:/|$)",
    r"/forgetchallan(?:/|$)",
    r"/create-challan(?:/|$)",
    r"/modules/",
]

# File types we currently care about.
KEEP_FILE_EXTENSIONS = {
    ".pdf",
}

# Words strongly suggesting a useful admission document.
IMPORTANT_FILE_WORDS = [
    "prospectus",
    "admission",
    "guide",
    "fee",
    "merit",
    "scholarship",
    "schedule",
    "advertisement",
    "eligibility",
    "program",
    "undergraduate",
    "graduate",
    "phd",
    "ms",
]


# ============================================================
# HELPERS
# ============================================================

def normalize(value):
    """
    Convert a value to a clean string.
    """
    if value is None:
        return ""

    return str(value).strip()


def normalize_url(value):
    """
    Convert URLs that may have been stored as Markdown links:

        [https://example.com](https://example.com)

    into:

        https://example.com

    Also handles normal plain URLs.
    """

    url = normalize(value)

    if not url:
        return ""

    # Markdown link:
    # [TEXT](URL)
    markdown_match = re.match(
        r"^\[.*?\]\((https?://[^)]+)\)$",
        url,
        flags=re.IGNORECASE,
    )

    if markdown_match:
        return markdown_match.group(1).strip()

    return url


def get_url(item):
    """
    Get and normalize an item's URL.
    """
    if not isinstance(item, dict):
        return ""

    return normalize_url(
        item.get("url")
    )


def get_title(item):
    """
    Get an item's title.
    """
    if not isinstance(item, dict):
        return ""

    return normalize(
        item.get("title")
    )


def get_original_classification(item):
    """
    Preserve the classification produced by the previous
    discovery stage.
    """
    if not isinstance(item, dict):
        return ""

    return normalize(
        item.get("classification")
    )


def lower_text(*values):
    """
    Combine values into lowercase searchable text.
    """
    return " ".join(
        normalize(value).lower()
        for value in values
        if value is not None
    )


def matches_any(text, patterns):
    """
    Return True if any regex pattern matches.
    """
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def is_external(url):
    """
    Determine whether a URL points outside the official
    UET admission domain.
    """

    url = normalize_url(url)

    if not url:
        return False

    lowered = url.lower()

    official_https = BASE_DOMAIN.lower()
    official_http = "http://admission.uet.edu.pk"

    return not (
        lowered.startswith(official_https)
        or lowered.startswith(official_http)
    )


def get_file_extension(url):
    """
    Safely extract the file extension from a URL.

    Example:
        https://example.com/file.pdf?x=1
        -> .pdf
    """

    clean_url = normalize_url(url)

    if not clean_url:
        return ""

    path_without_query = (
        clean_url
        .split("?", 1)[0]
        .split("#", 1)[0]
    )

    return Path(
        path_without_query
    ).suffix.lower()


# ============================================================
# PAGE CLASSIFICATION
# ============================================================

def classify_page(item):
    """
    Classify a CONTENT target.

    Possible decisions:

        KEEP
        REVIEW
        ACTION
    """

    url = get_url(item)
    title = get_title(item)

    text = lower_text(
        url,
        title,
    )

    # --------------------------------------------------------
    # External resources
    # --------------------------------------------------------

    if is_external(url):
        return {
            "decision": "REVIEW",
            "reason": (
                "External URL; do not crawl automatically"
            ),
            "priority": "medium",
        }

    # --------------------------------------------------------
    # ACTION PAGES
    # --------------------------------------------------------
    #
    # These pages are not knowledge sources, but their links
    # are valuable to the chatbot.
    #
    # Example:
    #
    # User:
    #   "I have forgotten my challan number."
    #
    # Bot can use:
    #
    #   action_type = "forget_challan"
    #   url = "/forgetchallan"
    #
    # --------------------------------------------------------

    if matches_any(
        text,
        ACTION_PAGE_PATTERNS,
    ):

        action_type = determine_action_type(
            url,
            title,
        )

        return {
            "decision": "ACTION",
            "reason": (
                "User action page; preserve URL so "
                "the chatbot can provide the link"
            ),
            "priority": "high",
            "action_type": action_type,
        }

    # --------------------------------------------------------
    # Core admission pages
    # --------------------------------------------------------

    if matches_any(
        text,
        KEEP_PAGE_PATTERNS,
    ):
        return {
            "decision": "KEEP",
            "reason": "Core admission information page",
            "priority": "high",
        }

    # --------------------------------------------------------
    # News
    # --------------------------------------------------------

    if matches_any(
        text,
        REVIEW_PAGE_PATTERNS,
    ):
        return {
            "decision": "REVIEW",
            "reason": (
                "Admission news requires relevance "
                "and freshness review"
            ),
            "priority": "medium",
        }

    # --------------------------------------------------------
    # Conservative fallback
    # --------------------------------------------------------

    return {
        "decision": "REVIEW",
        "reason": "Could not confidently classify",
        "priority": "medium",
    }


# ============================================================
# ACTION TYPE DETECTION
# ============================================================

def determine_action_type(url, title):
    """
    Give ACTION pages a stable action_type.

    This makes the reviewed JSON more useful to the chatbot.

    Example:

        /forgetchallan
        -> forget_challan

        /create-challan
        -> create_challan
    """

    text = lower_text(
        url,
        title,
    )

    if "forgetchallan" in text:
        return "forget_challan"

    if "create-challan" in text:
        return "create_challan"

    if "/login" in text:
        return "login"

    if "/account/" in text:
        return "account"

    if "/modules/" in text:
        return "module_action"

    return "admission_action"


# ============================================================
# FILE CLASSIFICATION
# ============================================================

def classify_file(item):
    """
    Conservatively classify a FILE target.

    Possible decisions:

        KEEP_FILE
        REVIEW
    """

    url = get_url(item)
    title = get_title(item)

    text = lower_text(
        url,
        title,
    )

    extension = get_file_extension(url)

    # --------------------------------------------------------
    # Unsupported file type
    # --------------------------------------------------------

    if extension not in KEEP_FILE_EXTENSIONS:
        return {
            "decision": "REVIEW",
            "reason": (
                "Unsupported or unknown file type"
            ),
            "priority": "medium",
        }

    # --------------------------------------------------------
    # Strongly relevant documents
    # --------------------------------------------------------

    matched_words = [
        word
        for word in IMPORTANT_FILE_WORDS
        if word in text
    ]

    if matched_words:
        return {
            "decision": "KEEP_FILE",
            "reason": (
                "Likely official admission document"
            ),
            "priority": "high",
            "matched_keywords": matched_words,
        }

    # --------------------------------------------------------
    # Generic PDF
    # --------------------------------------------------------

    return {
        "decision": "REVIEW",
        "reason": (
            "PDF with insufficient filename/title "
            "information"
        ),
        "priority": "medium",
    }


# ============================================================
# LOAD
# ============================================================

def load_targets():

    print()
    print("=" * 70)
    print("UET ADMISSION — CONTENT TARGET REVIEW")
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
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Expected the JSON root to be an object/dict."
        )

    if "targets" not in data:
        raise ValueError(
            "Expected top-level key 'targets' "
            "but it was not found."
        )

    if not isinstance(data["targets"], dict):
        raise ValueError(
            "Expected 'targets' to be a dictionary."
        )

    return data


# ============================================================
# REVIEW
# ============================================================

def review_targets(data):

    targets = data.get(
        "targets",
        {},
    )

    # --------------------------------------------------------
    # _content_targets.json actually has:
    #
    # targets:
    #   content
    #   files
    #   action
    # --------------------------------------------------------

    content_targets = targets.get(
        "content",
        [],
    )

    file_targets = targets.get(
        "files",
        [],
    )

    action_targets = targets.get(
        "action",
        [],
    )

    reviewed = {
        "metadata": {
            "source": str(INPUT_FILE),
            "stage": "admission_content_target_review",
            "purpose": (
                "Conservative review of discovered "
                "admission content before acquisition"
            ),
            "policy": {
                "download_files": False,
                "crawl_pages": False,
                "crawl_external_websites": False,

                # IMPORTANT:
                # Action URLs are intentionally preserved.
                "preserve_action_links": True,
            },
        },

        "source_counts": {
            "content": len(content_targets),
            "files": len(file_targets),
            "action": len(action_targets),
        },

        "pages": [],
        "files": [],
        "actions": [],
        "external_urls": [],
    }

    # ========================================================
    # CONTENT / PAGES
    # ========================================================

    for item in content_targets:

        result = classify_page(item)

        reviewed_item = {
            "url": get_url(item),
            "title": get_title(item),
            "original_classification": (
                get_original_classification(item)
            ),
            **result,
        }

        reviewed["pages"].append(
            reviewed_item
        )

        # Track external content separately.
        if is_external(
            get_url(item)
        ):

            reviewed["external_urls"].append(
                {
                    "url": get_url(item),
                    "title": get_title(item),
                    "source_type": "content",
                    "decision": "REVIEW",
                    "reason": (
                        "External website; do not "
                        "crawl automatically"
                    ),
                    "priority": "medium",
                }
            )

    # ========================================================
    # FILES
    # ========================================================

    for item in file_targets:

        result = classify_file(item)

        reviewed_item = {
            "url": get_url(item),
            "title": get_title(item),
            "original_classification": (
                get_original_classification(item)
            ),
            **result,
        }

        reviewed["files"].append(
            reviewed_item
        )

        # Track external files separately if any exist.
        if is_external(
            get_url(item)
        ):

            reviewed["external_urls"].append(
                {
                    "url": get_url(item),
                    "title": get_title(item),
                    "source_type": "file",
                    "decision": "REVIEW",
                    "reason": (
                        "External file URL; do not "
                        "download automatically"
                    ),
                    "priority": "medium",
                }
            )

    # ========================================================
    # ACTION TARGETS
    # ========================================================
    #
    # IMPORTANT:
    #
    # We DO NOT throw these away anymore.
    #
    # We preserve:
    #   - URL
    #   - title
    #   - action type
    #   - original classification
    #
    # This gives the chatbot a usable action/link registry.
    #
    # ========================================================

    for item in action_targets:

        url = get_url(item)
        title = get_title(item)

        action_type = determine_action_type(
            url,
            title,
        )

        reviewed["actions"].append(
            {
                "url": url,
                "title": title,
                "original_classification": (
                    get_original_classification(item)
                ),
                "decision": "ACTION",
                "reason": (
                    "Action URL preserved for chatbot "
                    "navigation"
                ),
                "priority": "high",
                "action_type": action_type,
            }
        )

    # ========================================================
    # ALSO MOVE ACTION PAGES FOUND IN CONTENT
    # ========================================================
    #
    # Some discovery pipelines may put /forgetchallan,
    # /create-challan, etc. inside "content" rather than
    # "action".
    #
    # We therefore also preserve them in "actions".
    #
    # Avoid duplicates by URL.
    #
    # ========================================================

    existing_action_urls = {
        item.get("url")
        for item in reviewed["actions"]
        if item.get("url")
    }

    for item in reviewed["pages"]:

        if item.get("decision") != "ACTION":
            continue

        url = item.get("url", "")

        if not url:
            continue

        if url in existing_action_urls:
            continue

        reviewed["actions"].append(
            {
                "url": url,
                "title": item.get("title", ""),
                "original_classification": (
                    item.get(
                        "original_classification",
                        "",
                    )
                ),
                "decision": "ACTION",
                "reason": (
                    "Action URL preserved for chatbot "
                    "navigation"
                ),
                "priority": "high",
                "action_type": item.get(
                    "action_type",
                    "admission_action",
                ),
            }
        )

        existing_action_urls.add(url)

    return reviewed


# ============================================================
# SUMMARY
# ============================================================

def count(items, decision):

    return sum(
        item.get("decision") == decision
        for item in items
    )


def print_summary(reviewed):

    pages = reviewed["pages"]
    files = reviewed["files"]
    actions = reviewed["actions"]
    external = reviewed["external_urls"]

    print()
    print("# RESULT")
    print()

    # --------------------------------------------------------
    # Pages
    # --------------------------------------------------------

    print(
        "Content pages:",
        len(pages),
    )

    print(
        "  KEEP:",
        count(pages, "KEEP"),
    )

    print(
        "  REVIEW:",
        count(pages, "REVIEW"),
    )

    print(
        "  ACTION:",
        count(pages, "ACTION"),
    )

    print()

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    print(
        "Files:",
        len(files),
    )

    print(
        "  KEEP_FILE:",
        count(files, "KEEP_FILE"),
    )

    print(
        "  REVIEW:",
        count(files, "REVIEW"),
    )

    print()

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    print(
        "Action links:",
        len(actions),
    )

    print()

    # --------------------------------------------------------
    # External URLs
    # --------------------------------------------------------

    print(
        "External URLs:",
        len(external),
    )

    print()

    # ========================================================
    # HIGH PRIORITY PAGES
    # ========================================================

    print("=" * 70)
    print("HIGH PRIORITY PAGES")
    print("=" * 70)

    high_pages = [
        item
        for item in pages
        if (
            item.get("priority") == "high"
            and item.get("decision") == "KEEP"
        )
    ]

    if not high_pages:
        print("None")
    else:

        for index, item in enumerate(
            high_pages,
            start=1,
        ):

            print(
                f"[{index:03d}] "
                f"{item.get('title', '')}"
            )

            print(
                item.get("url", "")
            )

            print(
                f"      Decision: "
                f"{item.get('decision')}"
            )

            print(
                f"      Reason: "
                f"{item.get('reason')}"
            )

            print()

    # ========================================================
    # REVIEW PAGES
    # ========================================================

    print("=" * 70)
    print("PAGES REQUIRING REVIEW")
    print("=" * 70)

    review_pages = [
        item
        for item in pages
        if item.get("decision") == "REVIEW"
    ]

    if not review_pages:
        print("None")
    else:

        for index, item in enumerate(
            review_pages,
            start=1,
        ):

            print(
                f"[{index:03d}] "
                f"{item.get('title', '')}"
            )

            print(
                item.get("url", "")
            )

            print(
                f"      Reason: "
                f"{item.get('reason')}"
            )

            print()

    # ========================================================
    # HIGH PRIORITY FILES
    # ========================================================

    print("=" * 70)
    print("HIGH PRIORITY FILES")
    print("=" * 70)

    high_files = [
        item
        for item in files
        if (
            item.get("decision") == "KEEP_FILE"
            and item.get("priority") == "high"
        )
    ]

    if not high_files:
        print("None")
    else:

        for index, item in enumerate(
            high_files,
            start=1,
        ):

            print(
                f"[{index:03d}] "
                f"{item.get('title', '')}"
            )

            print(
                item.get("url", "")
            )

            matched = item.get(
                "matched_keywords",
                [],
            )

            if matched:

                print(
                    "      Matched keywords:",
                    ", ".join(matched),
                )

            print()

    # ========================================================
    # FILES REQUIRING REVIEW
    # ========================================================

    print("=" * 70)
    print("FILES REQUIRING REVIEW")
    print("=" * 70)

    review_files = [
        item
        for item in files
        if item.get("decision") == "REVIEW"
    ]

    if not review_files:
        print("None")
    else:

        for index, item in enumerate(
            review_files,
            start=1,
        ):

            print(
                f"[{index:03d}] "
                f"{item.get('title', '')}"
            )

            print(
                item.get("url", "")
            )

            print(
                f"      Reason: "
                f"{item.get('reason')}"
            )

            print()

    # ========================================================
    # ACTION LINKS
    # ========================================================

    print("=" * 70)
    print("ACTION LINKS — PRESERVED FOR CHATBOT")
    print("=" * 70)

    if not actions:

        print("None")

    else:

        for index, item in enumerate(
            actions,
            start=1,
        ):

            print(
                f"[{index:03d}] "
                f"{item.get('title', '')}"
            )

            print(
                f"      URL: "
                f"{item.get('url', '')}"
            )

            print(
                f"      Action type: "
                f"{item.get('action_type', '')}"
            )

            print(
                f"      Decision: "
                f"{item.get('decision', '')}"
            )

            print()

    print()


# ============================================================
# SAVE
# ============================================================

def save_review(reviewed):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            reviewed,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print("SAVED")
    print("=" * 70)
    print()
    print(
        OUTPUT_FILE
    )
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    data = load_targets()

    reviewed = review_targets(
        data
    )

    print_summary(
        reviewed
    )

    save_review(
        reviewed
    )


if __name__ == "__main__":
    main()
