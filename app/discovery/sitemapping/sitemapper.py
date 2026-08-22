import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

START_URL = "https://www.uet.edu.pk/home/"

SOURCE_NAME = "main_uet"

ALLOWED_DOMAINS = {
    "uet.edu.pk",
}

OUTPUT_FILE = Path(
    "data/inventory/main_uet.json"
)

REQUEST_DELAY = 1.0

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "UET-AI-Assistant-Research-Bot/0.1 "
    "(independent student research project)"
)


# ============================================================
# SESSION
# ============================================================

def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT
    })

    return session


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(url: str) -> str | None:
    """
    Convert URLs into a canonical representation.

    Examples:

        https://www.uet.edu.pk/
        https://uet.edu.pk/

    become:

        https://uet.edu.pk/
    """

    if not url:
        return None

    url = url.strip()

    # Remove #fragments
    url = urldefrag(url)[0]

    parsed = urlparse(url)

    if parsed.scheme.lower() not in {
        "http",
        "https"
    }:
        return None

    hostname = parsed.hostname

    if not hostname:
        return None

    hostname = hostname.lower()

    # Canonicalize UET domain.
    if hostname in {
        "www.uet.edu.pk",
        "uet.edu.pk"
    }:
        hostname = "uet.edu.pk"

    path = parsed.path or "/"

    # Normalize repeated trailing slash behavior.
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    normalized = (
        f"{parsed.scheme.lower()}://"
        f"{hostname}"
        f"{path}"
    )

    # Keep query parameters for now.
    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


# ============================================================
# DOMAIN CHECK
# ============================================================

def is_allowed_domain(url: str) -> bool:

    parsed = urlparse(url)

    hostname = parsed.hostname

    if not hostname:
        return False

    hostname = hostname.lower()

    return hostname in ALLOWED_DOMAINS


# ============================================================
# RESOURCE CLASSIFICATION
# ============================================================

def classify_url(url: str) -> str:

    parsed = urlparse(url)

    path = parsed.path.lower()

    if path.endswith(".pdf"):
        return "pdf"

    if path.endswith((
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".rar"
    )):
        return "document"

    if path.endswith((
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg"
    )):
        return "image"

    return "html"


# ============================================================
# LOAD EXISTING INVENTORY
# ============================================================

def load_inventory():

    if not OUTPUT_FILE.exists():
        return {}

    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        records = {}

        for record in data.get(
            "resources",
            []
        ):

            url = record.get("url")

            if url:
                records[url] = record

        print(
            f"Loaded existing inventory: "
            f"{len(records)} resources"
        )

        return records

    except (
        json.JSONDecodeError,
        OSError
    ) as error:

        print(
            f"Could not load inventory: {error}"
        )

        return {}


# ============================================================
# SAVE INVENTORY
# ============================================================

def save_inventory(records):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "source": SOURCE_NAME,

        "start_url": START_URL,

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_resources": len(records),

        "resources": list(
            records.values()
        ),
    }

    temporary_file = OUTPUT_FILE.with_suffix(
        ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    temporary_file.replace(
        OUTPUT_FILE
    )


# ============================================================
# FETCH
# ============================================================

def fetch_url(session, url):

    resource_type = classify_url(url)

    try:

        # ====================================================
        # FILES
        # ====================================================
        # We don't need to download the actual file during
        # discovery. HEAD gives us metadata only.
        # ====================================================

        if resource_type != "html":

            response = session.head(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            return {
                "success": True,

                "status_code": response.status_code,

                "content_type": content_type,

                "final_url": normalize_url(
                    response.url
                ),

                "content_length": response.headers.get(
                    "Content-Length"
                ),

                "html": None,
            }

        # ====================================================
        # HTML
        # ====================================================
        # HTML needs GET because we need the page contents
        # to discover more links.
        # ====================================================

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        return {
            "success": True,

            "status_code": response.status_code,

            "content_type": content_type,

            "final_url": normalize_url(
                response.url
            ),

            "content_length": response.headers.get(
                "Content-Length"
            ),

            "html": response.text
            if "text/html" in content_type
            else None,
        }

    except requests.RequestException as error:

        return {
            "success": False,

            "status_code": None,

            "content_type": None,

            "final_url": None,

            "content_length": None,

            "html": None,

            "error": str(error),
        }
# ============================================================
# LINK EXTRACTION
# ============================================================

def extract_links(
    current_url,
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    discovered_links = set()

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        ).strip()

        if not href:
            continue

        absolute_url = urljoin(
            current_url,
            href
        )

        normalized_url = normalize_url(
            absolute_url
        )

        if not normalized_url:
            continue

        discovered_links.add(
            normalized_url
        )

    return sorted(
        discovered_links
    )


# ============================================================
# RECORD CREATION
# ============================================================

def create_record(
    url,
    parent_url=None,
    depth=0
):

    return {

        "url": url,

        "source": SOURCE_NAME,

        "resource_type": classify_url(
            url
        ),

        "parent_url": parent_url,

        "depth": depth,

        "status": "discovered",

        "http_status": None,

        "content_type": None,

        "final_url": None,

        "content_length": None,

        "title": None,

        "discovered_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "checked_at": None,

        "error": None,
    }


# ============================================================
# SITE DISCOVERY
# ============================================================

def discover_site():

    session = create_session()

    records = load_inventory()

    start_url = normalize_url(
        START_URL
    )

    queue = deque()

    # --------------------------------------------------------
    # If inventory already exists, continue from discovered
    # resources that have not yet been checked.
    # --------------------------------------------------------

    if records:

        for url, record in records.items():

            if record.get("status") != "checked":

                queue.append(
                    (
                        url,
                        record.get("parent_url"),
                        record.get("depth", 0)
                    )
                )

        print(
            f"Resuming with "
            f"{len(queue)} pending resources."
        )

    else:

        queue.append(
            (
                start_url,
                None,
                0
            )
        )

        records[start_url] = create_record(
            url=start_url,
            parent_url=None,
            depth=0
        )

    queued = {
        item[0]
        for item in queue
    }

    processed_this_run = 0

    while queue:

        current_url, parent_url, depth = (
            queue.popleft()
        )

        record = records.get(
            current_url
        )

        if record is None:

            record = create_record(
                current_url,
                parent_url,
                depth
            )

            records[current_url] = record

        # ----------------------------------------------------
        # Do not request already checked resources.
        # ----------------------------------------------------

        if record.get("status") == "checked":
            continue

        processed_this_run += 1

        print()
        print(
            f"[{processed_this_run}] "
            f"Checking: {current_url}"
        )

        result = fetch_url(
            session,
            current_url
        )

        record["checked_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        # ----------------------------------------------------
        # Request failed.
        # ----------------------------------------------------

        if not result["success"]:

            record["status"] = "error"

            record["error"] = result[
                "error"
            ]

            print(
                f"    ERROR: "
                f"{result['error']}"
            )

            save_inventory(
                records
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue

        # ----------------------------------------------------
        # Save HTTP metadata.
        # ----------------------------------------------------

        record["http_status"] = (
            result["status_code"]
        )

        record["content_type"] = (
            result["content_type"]
        )

        record["final_url"] = (
            result["final_url"]
        )

        record["content_length"] = (
            result["content_length"]
        )

        record["status"] = "checked"

        print(
            f"    Status: "
            f"{result['status_code']}"
        )

        print(
            f"    Type: "
            f"{result['content_type']}"
        )

        # ----------------------------------------------------
        # HTML processing.
        # ----------------------------------------------------

        if result["html"]:

            soup = BeautifulSoup(
                result["html"],
                "html.parser"
            )

            if soup.title:

                record["title"] = (
                    soup.title.get_text(
                        " ",
                        strip=True
                    )
                )

            links = extract_links(
                current_url,
                result["html"]
            )

            new_links = 0

            for link in links:

                if not is_allowed_domain(
                    link
                ):
                    continue

                if link in records:
                    continue

                records[link] = create_record(
                    url=link,
                    parent_url=current_url,
                    depth=depth + 1
                )

                queue.append(
                    (
                        link,
                        current_url,
                        depth + 1
                    )
                )

                queued.add(link)

                new_links += 1

            print(
                f"    New links: "
                f"{new_links}"
            )

        # ----------------------------------------------------
        # Save progress after every request.
        # ----------------------------------------------------

        save_inventory(
            records
        )

        # ----------------------------------------------------
        # Respectful delay.
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    total = len(records)

    checked = sum(
        1
        for record in records.values()
        if record.get("status") == "checked"
    )

    errors = sum(
        1
        for record in records.values()
        if record.get("status") == "error"
    )

    html_count = sum(
        1
        for record in records.values()
        if record.get("resource_type") == "html"
    )

    pdf_count = sum(
        1
        for record in records.values()
        if record.get("resource_type") == "pdf"
    )

    document_count = sum(
        1
        for record in records.values()
        if record.get("resource_type") == "document"
    )

    image_count = sum(
        1
        for record in records.values()
        if record.get("resource_type") == "image"
    )

    print()
    print("=" * 70)
    print("DISCOVERY COMPLETE")
    print("=" * 70)

    print(
        f"Total resources : {total}"
    )

    print(
        f"Checked         : {checked}"
    )

    print(
        f"Errors          : {errors}"
    )

    print(
        f"HTML            : {html_count}"
    )

    print(
        f"PDF             : {pdf_count}"
    )

    print(
        f"Documents       : {document_count}"
    )

    print(
        f"Images          : {image_count}"
    )

    print()
    print(
        f"Inventory: "
        f"{OUTPUT_FILE.resolve()}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    discover_site()