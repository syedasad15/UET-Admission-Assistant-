from pathlib import Path
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


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
    / "_content_targets_reviewed.json"
)

OUTPUT_FILE = (
    ADMISSION_ROOT
    / "_pages_reviewed.json"
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DOMAIN = "https://admission.uet.edu.pk"

REQUEST_TIMEOUT = 20
REQUEST_DELAY_SECONDS = 0.5

MAX_TEXT_LENGTH = 30000
MAX_LINKS_PER_PAGE = 200

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36 "
    "UET-Admission-Chatbot/1.0"
)


# ============================================================
# PAGE TYPES
# ============================================================

PAGE_TYPE_PATTERNS = {
    "faq": [
        r"/faqs(?:/|$)",
        r"\bfaq\b",
        r"frequently asked",
    ],

    "program": [
        r"/program(?:/|$)",
        r"\bprogram\b",
        r"\bprograms\b",
        r"degree program",
        r"bachelor",
        r"master",
        r"ph\.?d",
        r"associate degree",
    ],

    "download": [
        r"/downloads(?:/|$)",
        r"\bdownload\b",
        r"\bprospectus\b",
    ],

    "foreign_students": [
        r"/foreign-students(?:/|$)",
        r"foreign student",
        r"international student",
    ],

    "news": [
        r"/news(?:/|$)",
    ],

    "admission": [
        r"/UG-\d",
        r"/MS-\d",
        r"/PhD-\d",
        r"\badmission\b",
        r"apply now",
        r"application",
    ],

    "home": [
        r"^https?://admission\.uet\.edu\.pk/?$",
    ],
}


# ============================================================
# CONTENT SIGNALS
# ============================================================

HIGH_VALUE_PATTERNS = {
    "eligibility": [
        r"\beligibility\b",
        r"eligible candidates",
        r"eligibility criteria",
        r"minimum qualification",
        r"minimum marks",
    ],

    "fee": [
        r"\bfee\b",
        r"\bfees\b",
        r"fee structure",
        r"fee schedule",
        r"tuition fee",
        r"admission fee",
    ],

    "deadline": [
        r"deadline",
        r"last date",
        r"last day",
        r"closing date",
        r"application deadline",
    ],

    "merit": [
        r"merit list",
        r"merit lists",
        r"merit position",
        r"selected candidates",
        r"waiting list",
    ],

    "scholarship": [
        r"scholarship",
        r"financial assistance",
        r"financial aid",
    ],

    "admission_process": [
        r"admission process",
        r"application process",
        r"how to apply",
        r"apply online",
        r"application procedure",
        r"step.*application",
    ],

    "documents": [
        r"required documents",
        r"documents required",
        r"documents",
        r"document checklist",
        r"original documents",
    ],

    "ecat": [
        r"\becat\b",
        r"entry test",
        r"entrance test",
    ],

    "schedule": [
        r"schedule",
        r"important dates",
        r"admission calendar",
        r"timeline",
    ],

    "hostel": [
        r"hostel",
        r"hostels",
        r"accommodation",
    ],

    "quota": [
        r"quota",
        r"reserved seats",
        r"reserved seat",
    ],

    "international": [
        r"international student",
        r"foreign student",
        r"foreign students",
    ],

    "contact": [
        r"contact us",
        r"admission office",
        r"admission cell",
        r"phone",
        r"email",
    ],
}


# ============================================================
# ACTION SIGNALS
# ============================================================

ACTION_PATTERNS = {
    "apply": [
        r"apply now",
        r"apply online",
        r"online application",
        r"submit application",
    ],

    "download": [
        r"download",
        r"prospectus",
        r"admission advertisement",
        r"fee schedule",
    ],

    "check_merit": [
        r"merit list",
        r"selected candidates",
        r"check merit",
    ],

    "check_result": [
        r"result",
        r"result announcement",
        r"ecat result",
    ],

    "contact": [
        r"contact",
        r"admission office",
        r"admission cell",
    ],
}


# ============================================================
# KEEP / REVIEW POLICY
# ============================================================

KEEP_PAGE_TYPES = {
    "faq",
    "program",
    "download",
    "foreign_students",
    "admission",
}

KEEP_CONTENT_SIGNALS = {
    "eligibility",
    "fee",
    "deadline",
    "merit",
    "scholarship",
    "admission_process",
    "documents",
    "ecat",
    "schedule",
    "hostel",
    "quota",
    "international",
    "contact",
}


# ============================================================
# PROMOTIONAL / LOW-VALUE SIGNALS
# ============================================================

LOW_VALUE_PATTERNS = [
    r"welcome to uet",
    r"where your future begins",
    r"record response",
    r"proud moment",
    r"celebrating",
    r"congratulations",
    r"success story",
    r"meet our",
    r"message from vc",
]


# ============================================================
# HELPERS
# ============================================================

def normalize(value):
    """Convert a value to a clean string."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_url(value):
    """Normalize plain URLs and Markdown-style URLs."""

    url = normalize(value)

    if not url:
        return ""

    markdown_match = re.match(
        r"^\[.*?\]\((https?://[^)]+)\)$",
        url,
        flags=re.IGNORECASE,
    )

    if markdown_match:
        return markdown_match.group(1).strip()

    return url


def get_url(item):
    """Get an item's URL."""

    if not isinstance(item, dict):
        return ""

    return normalize_url(
        item.get("url")
    )


def get_title(item):
    """Get an item's title."""

    if not isinstance(item, dict):
        return ""

    return normalize(
        item.get("title")
    )


def is_official_url(url):
    """
    Determine whether a URL belongs to the
    official UET admission portal.
    """

    url = normalize_url(url)

    if not url:
        return False

    parsed = urlparse(url)

    hostname = (
        parsed.hostname or ""
    ).lower()

    return (
        hostname == "admission.uet.edu.pk"
        or hostname.endswith(
            ".admission.uet.edu.pk"
        )
    )


def clean_text(text):
    """Normalize extracted page text."""

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def matches_any(text, patterns):
    """Check whether any regex pattern matches text."""

    if not text:
        return False

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def detect_page_type(url, title, text):
    """
    Determine the most likely page type.
    """

    searchable_text = " ".join(
        [
            normalize(url),
            normalize(title),
            normalize(text[:10000]),
        ]
    ).lower()

    detected_types = []

    for page_type, patterns in PAGE_TYPE_PATTERNS.items():

        if matches_any(
            searchable_text,
            patterns,
        ):
            detected_types.append(
                page_type
            )

    priority_order = [
        "faq",
        "program",
        "download",
        "foreign_students",
        "news",
        "admission",
        "home",
    ]

    for page_type in priority_order:

        if page_type in detected_types:
            return page_type

    return "other"


def detect_content_signals(text):
    """
    Detect useful admission-related topics
    from actual page content.
    """

    text = normalize(text).lower()

    signals = []

    for signal, patterns in HIGH_VALUE_PATTERNS.items():

        if matches_any(
            text,
            patterns,
        ):
            signals.append(signal)

    return signals


def detect_action_signals(text):
    """
    Detect actions users may need to perform.
    """

    text = normalize(text).lower()

    actions = []

    for action, patterns in ACTION_PATTERNS.items():

        if matches_any(
            text,
            patterns,
        ):
            actions.append(action)

    return actions


def detect_low_value_signals(text):
    """
    Detect promotional / low-information content.
    """

    text = normalize(text).lower()

    signals = []

    for pattern in LOW_VALUE_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            signals.append(pattern)

    return signals


def detect_date_signals(text):
    """
    Detect dates and years in page content.

    This is useful because admission information is
    often time-sensitive.
    """

    if not text:
        return []

    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+\d{4}\b",
        r"\b(?:20\d{2})\b",
    ]

    found = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        found.extend(matches)

    # Preserve order, remove duplicates.
    result = []

    seen = set()

    for value in found:

        value = normalize(value)

        key = value.lower()

        if key not in seen:

            seen.add(key)
            result.append(value)

    return result[:50]


def extract_links(soup, page_url):
    """
    Extract links from the page.

    Internal official UET links are preserved.
    External links are preserved separately.
    """

    internal_links = []
    external_links = []

    seen_internal = set()
    seen_external = set()

    for anchor in soup.find_all("a"):

        href = anchor.get("href")

        if not href:
            continue

        href = href.strip()

        if href.startswith(
            (
                "#",
                "javascript:",
                "mailto:",
                "tel:",
            )
        ):
            continue

        absolute_url = urljoin(
            page_url,
            href,
        )

        absolute_url = normalize_url(
            absolute_url
        )

        if not absolute_url:
            continue

        link_text = clean_text(
            anchor.get_text(
                " ",
                strip=True,
            )
        )

        if is_official_url(
            absolute_url
        ):

            if (
                absolute_url
                not in seen_internal
            ):

                seen_internal.add(
                    absolute_url
                )

                internal_links.append(
                    {
                        "title": link_text,
                        "url": absolute_url,
                    }
                )

        else:

            if (
                absolute_url
                not in seen_external
            ):

                seen_external.add(
                    absolute_url
                )

                external_links.append(
                    {
                        "title": link_text,
                        "url": absolute_url,
                    }
                )

        if (
            len(internal_links)
            >= MAX_LINKS_PER_PAGE
        ):
            break

    return (
        internal_links,
        external_links,
    )


def extract_page_content(html, page_url):
    """
    Extract useful text and links from HTML.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        element.decompose()

    title = ""

    if soup.title:

        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("body")
    )

    if main is not None:

        text = clean_text(
            main.get_text(
                " ",
                strip=True,
            )
        )

    else:

        text = clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )

    if len(text) > MAX_TEXT_LENGTH:

        text = text[
            :MAX_TEXT_LENGTH
        ]

    (
        internal_links,
        external_links,
    ) = extract_links(
        soup,
        page_url,
    )

    return {
        "title": title,
        "text": text,
        "internal_links": internal_links,
        "external_links": external_links,
    }


# ============================================================
# PAGE QUALITY
# ============================================================

def calculate_quality_score(
    page_type,
    text,
    content_signals,
    action_signals,
    low_value_signals,
):
    """
    Calculate a simple knowledge-quality score.

    This is intentionally transparent rather than
    machine-learning based.
    """

    score = 0

    # Strong page types.
    if page_type in KEEP_PAGE_TYPES:
        score += 30

    # Admission information.
    score += min(
        len(content_signals) * 8,
        48,
    )

    # User actions.
    score += min(
        len(action_signals) * 5,
        15,
    )

    # Useful amount of content.
    text_length = len(text)

    if text_length >= 1000:
        score += 10

    elif text_length >= 500:
        score += 5

    # Penalize promotional pages.
    score -= min(
        len(low_value_signals) * 15,
        30,
    )

    return max(
        0,
        min(
            score,
            100,
        ),
    )


# ============================================================
# PAGE DECISION
# ============================================================

def classify_page(
    url,
    title,
    text,
    original_classification="",
):
    """
    Classify a page into:

        KEEP
        REVIEW
        SKIP

    The decision is based on the actual page content.
    """

    page_type = detect_page_type(
        url,
        title,
        text,
    )

    content_signals = detect_content_signals(
        text
    )

    action_signals = detect_action_signals(
        text
    )

    low_value_signals = detect_low_value_signals(
        text
    )

    date_signals = detect_date_signals(
        text
    )

    # --------------------------------------------------------
    # Empty content
    # --------------------------------------------------------

    if not text:

        return {
            "decision": "REVIEW",
            "reason": (
                "Page content could not be "
                "reliably extracted"
            ),
            "priority": "medium",
            "confidence": 0.0,
            "quality_score": 0,
            "page_type": page_type,
            "content_signals": [],
            "action_signals": [],
            "low_value_signals": [],
            "date_signals": [],
        }

    # --------------------------------------------------------
    # Quality score
    # --------------------------------------------------------

    score = calculate_quality_score(
        page_type=page_type,
        text=text,
        content_signals=content_signals,
        action_signals=action_signals,
        low_value_signals=low_value_signals,
    )

    # --------------------------------------------------------
    # Strong knowledge pages
    # --------------------------------------------------------

    if (
        page_type in KEEP_PAGE_TYPES
        and score >= 45
    ):

        return {
            "decision": "KEEP",
            "reason": (
                "Strong admission knowledge "
                "page with useful content"
            ),
            "priority": "high",
            "confidence": min(
                score / 100,
                0.99,
            ),
            "quality_score": score,
            "page_type": page_type,
            "content_signals": content_signals,
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # News pages
    # --------------------------------------------------------

    if page_type == "news":

        # News with several useful admission signals.
        if (
            len(content_signals) >= 2
            and score >= 35
        ):

            return {
                "decision": "KEEP",
                "reason": (
                    "News page contains "
                    "actionable admission information"
                ),
                "priority": "high",
                "confidence": min(
                    score / 100,
                    0.95,
                ),
                "quality_score": score,
                "page_type": page_type,
                "content_signals": content_signals,
                "action_signals": action_signals,
                "low_value_signals": low_value_signals,
                "date_signals": date_signals,
            }

        # One strong signal can still justify review,
        # but not automatic KEEP.
        if content_signals:

            return {
                "decision": "REVIEW",
                "reason": (
                    "News page contains some "
                    "admission information but "
                    "requires relevance review"
                ),
                "priority": "medium",
                "confidence": 0.60,
                "quality_score": score,
                "page_type": page_type,
                "content_signals": content_signals,
                "action_signals": action_signals,
                "low_value_signals": low_value_signals,
                "date_signals": date_signals,
            }

        return {
            "decision": "REVIEW",
            "reason": (
                "News page does not contain "
                "enough recognized admission knowledge"
            ),
            "priority": "low",
            "confidence": 0.35,
            "quality_score": score,
            "page_type": page_type,
            "content_signals": [],
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # Strong unknown page
    # --------------------------------------------------------

    if (
        page_type == "other"
        and len(content_signals) >= 3
    ):

        return {
            "decision": "KEEP",
            "reason": (
                "Unknown page type but content "
                "contains multiple admission signals"
            ),
            "priority": "high",
            "confidence": 0.80,
            "quality_score": score,
            "page_type": page_type,
            "content_signals": content_signals,
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # Home page
    # --------------------------------------------------------

    if page_type == "home":

        if content_signals:

            return {
                "decision": "KEEP",
                "reason": (
                    "Admission portal home page "
                    "contains useful information"
                ),
                "priority": "medium",
                "confidence": 0.75,
                "quality_score": score,
                "page_type": page_type,
                "content_signals": content_signals,
                "action_signals": action_signals,
                "low_value_signals": low_value_signals,
                "date_signals": date_signals,
            }

        return {
            "decision": "REVIEW",
            "reason": (
                "Home page requires content review"
            ),
            "priority": "medium",
            "confidence": 0.40,
            "quality_score": score,
            "page_type": page_type,
            "content_signals": [],
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # Generic pages with useful signals
    # --------------------------------------------------------

    useful_signals = [
        signal
        for signal in content_signals
        if signal in KEEP_CONTENT_SIGNALS
    ]

    if (
        len(useful_signals) >= 2
        and score >= 30
    ):

        return {
            "decision": "KEEP",
            "reason": (
                "Page contains important "
                "admission information"
            ),
            "priority": "high",
            "confidence": 0.75,
            "quality_score": score,
            "page_type": page_type,
            "content_signals": useful_signals,
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # Promotional content
    # --------------------------------------------------------

    if low_value_signals and not useful_signals:

        return {
            "decision": "REVIEW",
            "reason": (
                "Page appears promotional or "
                "low-value for the knowledge base"
            ),
            "priority": "low",
            "confidence": 0.70,
            "quality_score": score,
            "page_type": page_type,
            "content_signals": useful_signals,
            "action_signals": action_signals,
            "low_value_signals": low_value_signals,
            "date_signals": date_signals,
        }

    # --------------------------------------------------------
    # Conservative fallback
    # --------------------------------------------------------

    return {
        "decision": "REVIEW",
        "reason": (
            "Page does not contain enough "
            "recognized admission information"
        ),
        "priority": "medium",
        "confidence": 0.50,
        "quality_score": score,
        "page_type": page_type,
        "content_signals": useful_signals,
        "action_signals": action_signals,
        "low_value_signals": low_value_signals,
        "date_signals": date_signals,
    }


# ============================================================
# FETCH
# ============================================================

def fetch_page(
    session,
    url,
):
    """
    Fetch an official admission page.
    """

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
            .lower()
        )

        if (
            "text/html"
            not in content_type
            and "application/xhtml"
            not in content_type
        ):

            return {
                "success": False,
                "status_code": response.status_code,
                "error": (
                    "URL did not return HTML"
                ),
                "content_type": content_type,
            }

        return {
            "success": True,
            "status_code": response.status_code,
            "html": response.text,
            "final_url": response.url,
            "content_type": content_type,
        }

    except requests.RequestException as exc:

        return {
            "success": False,
            "status_code": None,
            "error": str(exc),
        }


# ============================================================
# LOAD INPUT
# ============================================================

def load_targets():

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
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        dict,
    ):

        raise ValueError(
            "Expected JSON root to be an object."
        )

    pages = data.get(
        "pages",
        [],
    )

    if not isinstance(
        pages,
        list,
    ):

        raise ValueError(
            "Expected 'pages' to be a list."
        )

    return data


# ============================================================
# REVIEW PAGES
# ============================================================

def review_pages(data):

    pages = data.get(
        "pages",
        [],
    )

    reviewed_pages = []

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
        }
    )

    total = len(pages)

    print(
        f"Pages to review: {total}"
    )
    print()

    for index, item in enumerate(
        pages,
        start=1,
    ):

        url = get_url(item)
        original_title = get_title(item)

        print(
            f"[{index:03d}/{total:03d}] "
            f"{original_title}"
        )

        print(
            f"URL: {url}"
        )

        # ----------------------------------------------------
        # Validate URL
        # ----------------------------------------------------

        if not url:

            reviewed_pages.append(
                {
                    "url": "",
                    "title": original_title,
                    "decision": "REVIEW",
                    "reason": "Missing page URL",
                    "priority": "medium",
                    "confidence": 0.0,
                    "quality_score": 0,
                    "page_type": "unknown",
                    "content_signals": [],
                    "action_signals": [],
                    "low_value_signals": [],
                    "date_signals": [],
                    "text": "",
                    "internal_links": [],
                    "external_links": [],
                    "fetch": {
                        "success": False,
                        "status_code": None,
                        "error": "Missing URL",
                    },
                }
            )

            print("Decision: REVIEW")
            print()

            continue

        # ----------------------------------------------------
        # Official URL validation
        # ----------------------------------------------------

        if not is_official_url(url):

            reviewed_pages.append(
                {
                    "url": url,
                    "title": original_title,
                    "decision": "REVIEW",
                    "reason": (
                        "Non-official URL; "
                        "manual review required"
                    ),
                    "priority": "medium",
                    "confidence": 0.0,
                    "quality_score": 0,
                    "page_type": "external",
                    "content_signals": [],
                    "action_signals": [],
                    "low_value_signals": [],
                    "date_signals": [],
                    "text": "",
                    "internal_links": [],
                    "external_links": [],
                    "fetch": {
                        "success": False,
                        "status_code": None,
                        "error": "Non-official URL",
                    },
                }
            )

            print("Decision: REVIEW")
            print()

            continue

        # ----------------------------------------------------
        # Fetch
        # ----------------------------------------------------

        result = fetch_page(
            session,
            url,
        )

        if not result.get("success"):

            reviewed_pages.append(
                {
                    "url": url,
                    "title": original_title,
                    "decision": "REVIEW",
                    "reason": "Page could not be fetched",
                    "priority": "medium",
                    "confidence": 0.0,
                    "quality_score": 0,
                    "page_type": "unknown",
                    "content_signals": [],
                    "action_signals": [],
                    "low_value_signals": [],
                    "date_signals": [],
                    "text": "",
                    "internal_links": [],
                    "external_links": [],
                    "fetch": {
                        "success": False,
                        "status_code": result.get(
                            "status_code"
                        ),
                        "error": result.get(
                            "error"
                        ),
                    },
                }
            )

            print("Decision: REVIEW")
            print(
                f"Reason: {result.get('error')}"
            )
            print()

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

            continue

        # ----------------------------------------------------
        # Extract
        # ----------------------------------------------------

        extracted = extract_page_content(
            result.get(
                "html",
                "",
            ),
            url,
        )

        extracted_title = (
            extracted.get("title")
            or original_title
        )

        text = extracted.get(
            "text",
            "",
        )

        internal_links = extracted.get(
            "internal_links",
            [],
        )

        external_links = extracted.get(
            "external_links",
            [],
        )

        # ----------------------------------------------------
        # Classify
        # ----------------------------------------------------

        classification = classify_page(
            url=url,
            title=extracted_title,
            text=text,
            original_classification=item.get(
                "original_classification",
                "",
            ),
        )

        reviewed_item = {
            "url": url,

            "final_url": result.get(
                "final_url",
                url,
            ),

            "title": extracted_title,

            "original_classification": item.get(
                "original_classification",
                "",
            ),

            **classification,

            "text": text,

            "internal_links": internal_links,

            "external_links": external_links,

            "fetch": {
                "success": True,
                "status_code": result.get(
                    "status_code"
                ),
                "content_type": result.get(
                    "content_type"
                ),
            },

            "reviewed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        reviewed_pages.append(
            reviewed_item
        )

        print(
            f"Decision: "
            f"{classification.get('decision')}"
        )

        print(
            f"Type: "
            f"{classification.get('page_type')}"
        )

        print(
            f"Score: "
            f"{classification.get('quality_score')}"
        )

        print(
            f"Signals: "
            f"{', '.join(classification.get('content_signals', [])) or 'none'}"
        )

        print()

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    return reviewed_pages


# ============================================================
# SAVE
# ============================================================

def save_results(
    source_data,
    reviewed_pages,
):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "metadata": {
            "source": str(INPUT_FILE),

            "stage": (
                "admission_knowledge_refinement"
            ),

            "purpose": (
                "Refine official UET admission "
                "pages before knowledge-base ingestion."
            ),

            "review_policy": {
                "crawl_external_websites": False,
                "download_files": False,
                "preserve_action_links": True,
                "content_based_classification": True,
                "conservative_news_review": True,
            },

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },

        "source_counts": {
            "pages": len(reviewed_pages),

            "actions": len(
                source_data.get(
                    "actions",
                    [],
                )
            ),

            "files": len(
                source_data.get(
                    "files",
                    [],
                )
            ),
        },

        "pages": reviewed_pages,

        # Preserve previous-stage action registry.
        "actions": source_data.get(
            "actions",
            [],
        ),

        # Preserve previous-stage file registry.
        "files": source_data.get(
            "files",
            [],
        ),
    }

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
    print("SAVED")
    print("=" * 70)
    print()
    print(OUTPUT_FILE)
    print()


# ============================================================
# SUMMARY
# ============================================================

def count(
    items,
    decision,
):

    return sum(
        item.get("decision") == decision
        for item in items
    )


def print_summary(
    reviewed_pages,
):

    print()
    print("=" * 70)
    print("KNOWLEDGE REFINEMENT RESULT")
    print("=" * 70)
    print()

    total = len(reviewed_pages)
    keep = count(
        reviewed_pages,
        "KEEP",
    )
    review = count(
        reviewed_pages,
        "REVIEW",
    )
    skip = count(
        reviewed_pages,
        "SKIP",
    )

    print(
        f"Pages: {total}"
    )

    print(
        f"  KEEP:   {keep}"
    )

    print(
        f"  REVIEW: {review}"
    )

    print(
        f"  SKIP:   {skip}"
    )

    print()

    # --------------------------------------------------------
    # KEEP
    # --------------------------------------------------------

    print("=" * 70)
    print("KEEP — KNOWLEDGE SOURCES")
    print("=" * 70)

    keep_pages = [
        item
        for item in reviewed_pages
        if item.get("decision") == "KEEP"
    ]

    if not keep_pages:

        print("None")

    else:

        for index, item in enumerate(
            keep_pages,
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
                f"Type: "
                f"{item.get('page_type')}"
            )

            print(
                f"Score: "
                f"{item.get('quality_score')}"
            )

            print(
                f"Priority: "
                f"{item.get('priority')}"
            )

            print(
                "Signals: "
                + (
                    ", ".join(
                        item.get(
                            "content_signals",
                            [],
                        )
                    )
                    or "none"
                )
            )

            print()

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    print("=" * 70)
    print("REVIEW — MANUAL KNOWLEDGE CHECK")
    print("=" * 70)

    review_pages = [
        item
        for item in reviewed_pages
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
                f"Type: "
                f"{item.get('page_type')}"
            )

            print(
                f"Score: "
                f"{item.get('quality_score')}"
            )

            print(
                f"Reason: "
                f"{item.get('reason')}"
            )

            print()

    # --------------------------------------------------------
    # SKIP
    # --------------------------------------------------------

    print("=" * 70)
    print("SKIP")
    print("=" * 70)

    skip_pages = [
        item
        for item in reviewed_pages
        if item.get("decision") == "SKIP"
    ]

    if not skip_pages:

        print("None")

    else:

        for index, item in enumerate(
            skip_pages,
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
                f"Reason: "
                f"{item.get('reason')}"
            )

            print()


# ============================================================
# MAIN
# ============================================================

def main():

    source_data = load_targets()

    reviewed_pages = review_pages(
        source_data
    )

    print_summary(
        reviewed_pages
    )

    save_results(
        source_data,
        reviewed_pages,
    )


if __name__ == "__main__":
    main()