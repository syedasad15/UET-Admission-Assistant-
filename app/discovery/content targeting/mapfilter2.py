
from pathlib import Path
import json
from urllib.parse import urlparse


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
    / "_map.json"
)

OUTPUT_FILE = (
    ADMISSION_ROOT
    / "_content_targets.json"
)


# ============================================================
# CONSTANTS
# ============================================================

ADMISSION_DOMAIN = "admission.uet.edu.pk"

# URLs that usually represent actions rather than knowledge.
ACTION_KEYWORDS = [
    "/account/login",
    "/account/forget",
    "/account/create",
    "/account/register",
    "/account/logout",
    "/application/",
    "/apply/",
    "/pg/account/",
    "/modules/",
]

# URLs that are potentially useful knowledge sources.
CONTENT_KEYWORDS = [
    "/faqs",
    "/faq",
    "/program/",
    "/news",
    "/downloads",
    "/foreign-students",
    "/UG-",
    "/MS-",
    "/PhD-",
    "/PHD-",
]

# File types worth considering as knowledge sources.
DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
}


# ============================================================
# HELPERS
# ============================================================

def normalize_url(url):
    """
    Normalize a URL enough for duplicate detection.

    We intentionally do NOT aggressively rewrite URLs because
    query parameters may sometimes carry meaningful information.
    """
    if not url:
        return ""

    return str(url).strip()


def get_extension(url):
    """
    Return the lowercase file extension from a URL path.
    """
    try:
        path = urlparse(url).path
        return Path(path).suffix.lower()
    except Exception:
        return ""


def is_admission_url(url):
    """
    Check whether a URL belongs to the UET admission domain.
    """
    try:
        hostname = urlparse(url).hostname
        return hostname == ADMISSION_DOMAIN
    except Exception:
        return False


def classify_url(url, title=""):
    """
    Conservative URL classification.

    Returns:
        CONTENT
        ACTION
        FILE
        EXTERNAL
        OTHER
    """

    url_lower = url.lower()
    title_lower = title.lower()

    # --------------------------------------------------------
    # External
    # --------------------------------------------------------

    if not is_admission_url(url):
        return "EXTERNAL"

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    extension = get_extension(url)

    if extension in DOCUMENT_EXTENSIONS:
        return "FILE"

    # --------------------------------------------------------
    # Action / transactional pages
    # --------------------------------------------------------

    for keyword in ACTION_KEYWORDS:
        if keyword.lower() in url_lower:
            return "ACTION"

    # --------------------------------------------------------
    # Explicit content patterns
    # --------------------------------------------------------

    for keyword in CONTENT_KEYWORDS:
        if keyword.lower() in url_lower:
            return "CONTENT"

    # --------------------------------------------------------
    # Title-based hints
    # --------------------------------------------------------

    title_hints = [
        "faq",
        "frequently asked",
        "admission",
        "program",
        "prospectus",
        "fee",
        "scholarship",
        "merit",
        "eligibility",
        "schedule",
        "deadline",
        "news",
        "announcement",
        "foreign student",
        "downloads",
    ]

    for hint in title_hints:
        if hint in title_lower:
            return "CONTENT"

    return "OTHER"


def add_unique(target_list, seen, item):
    """
    Add an item only once.
    """
    url = item.get("url", "")

    if not url:
        return

    normalized = normalize_url(url)

    if normalized in seen:
        return

    seen.add(normalized)
    target_list.append(item)


# ============================================================
# LOAD MAP
# ============================================================

def load_map():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"_map.json not found:\n{INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# EXTRACT PAGE RECORDS
# ============================================================

def extract_pages(data):

    pages = []

    # --------------------------------------------------------
    # Case 1:
    # map contains a direct list
    # --------------------------------------------------------

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                pages.append(item)

        return pages

    # --------------------------------------------------------
    # Case 2:
    # map contains a dictionary
    # --------------------------------------------------------

    if not isinstance(data, dict):
        return pages

    # Try common possible keys.
    possible_keys = [
        "pages",
        "results",
        "records",
        "map",
        "entries",
        "items",
    ]

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):

            for item in value:

                if isinstance(item, dict):
                    pages.append(item)

            if pages:
                return pages

    return pages


# ============================================================
# EXTRACT URLs RECURSIVELY
# ============================================================

def recursively_find_urls(obj, results):

    """
    Recursively search the JSON structure for dictionaries
    containing a URL.

    This makes the filter resilient to the exact _map.json
    structure.
    """

    if isinstance(obj, dict):

        url = obj.get("url")

        if isinstance(url, str) and url.strip():

            results.append(obj)

        for value in obj.values():
            recursively_find_urls(value, results)

    elif isinstance(obj, list):

        for item in obj:
            recursively_find_urls(item, results)


# ============================================================
# BUILD TARGETS
# ============================================================

def build_targets(data):

    discovered = []

    recursively_find_urls(
        data,
        discovered
    )

    content = []
    files = []
    action = []
    external = []
    other = []

    seen_content = set()
    seen_files = set()
    seen_action = set()
    seen_external = set()
    seen_other = set()

    for item in discovered:

        url = str(
            item.get("url", "")
        ).strip()

        if not url:
            continue

        title = str(
            item.get("title", "")
        ).strip()

        name = str(
            item.get("name", "")
        ).strip()

        if not title:
            title = name

        classification = classify_url(
            url,
            title
        )

        target = {
            "url": url,
            "title": title,
            "classification": classification,
        }

        if classification == "CONTENT":

            add_unique(
                content,
                seen_content,
                target
            )

        elif classification == "FILE":

            add_unique(
                files,
                seen_files,
                target
            )

        elif classification == "ACTION":

            add_unique(
                action,
                seen_action,
                target
            )

        elif classification == "EXTERNAL":

            add_unique(
                external,
                seen_external,
                target
            )

        else:

            add_unique(
                other,
                seen_other,
                target
            )

    return {
        "content": content,
        "files": files,
        "action": action,
        "external": external,
        "other": other,
    }


# ============================================================
# SAVE
# ============================================================

def save_targets(groups):

    ADMISSION_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    result = {
        "source": str(INPUT_FILE),
        "stage": "admission_content_target_filter",

        "policy": {
            "download_files": False,
            "crawl_pages": False,
            "crawl_external_websites": False,
            "classification": "conservative",
        },

        "counts": {
            "content": len(groups["content"]),
            "files": len(groups["files"]),
            "action": len(groups["action"]),
            "external": len(groups["external"]),
            "other": len(groups["other"]),
        },

        "targets": groups,
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_group(title, items, limit=20):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    print(
        f"Total unique: {len(items)}"
    )

    for index, item in enumerate(
        items[:limit],
        start=1
    ):

        print(
            f"[{index:03}] "
            f"{item['title'] or '(no title)'}"
        )

        print(
            f"      {item['url']}"
        )

    if len(items) > limit:

        print()
        print(
            f"... {len(items) - limit} more"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "UET ADMISSION — CONTENT TARGET FILTER"
    )

    print("=" * 70)

    print(
        f"Reading:\n{INPUT_FILE}"
    )

    data = load_map()

    print()
    print("Building conservative target classification...")

    groups = build_targets(data)

    print()
    print("RESULT")
    print("=" * 70)

    print(
        f"Content targets : {len(groups['content'])}"
    )

    print(
        f"Files           : {len(groups['files'])}"
    )

    print(
        f"Action pages    : {len(groups['action'])}"
    )

    print(
        f"External URLs   : {len(groups['external'])}"
    )

    print(
        f"Other           : {len(groups['other'])}"
    )

    print_group(
        "CONTENT TARGETS",
        groups["content"]
    )

    print_group(
        "FILES",
        groups["files"]
    )

    print_group(
        "OTHER — NEEDS REVIEW",
        groups["other"]
    )

    save_targets(groups)

    print()
    print("=" * 70)
    print("SAVED")
    print("=" * 70)

    print(
        OUTPUT_FILE
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Nothing was downloaded."
    )
    print(
        "No pages were crawled."
    )
    print(
        "External websites were not crawled."
    )


if __name__ == "__main__":
    main()
