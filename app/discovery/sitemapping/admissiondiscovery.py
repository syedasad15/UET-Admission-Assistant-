import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# UET CHATBOT — ADMISSION HOMEPAGE DISCOVERY
# ============================================================
#
# Purpose:
#   Analyze ONLY the UET Admission homepage.
#
# This script:
#   1. Fetches the Admission homepage
#   2. Finds navigation links
#   3. Converts relative URLs to absolute URLs
#   4. Removes duplicate links
#   5. Saves the discovered sections
#
# IMPORTANT:
#   This script DOES NOT crawl discovered URLs.
#
# Output:
#
# D:\UET Chatbot\data\inventory\admission\_sections.json
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

ADMISSION_URL = "https://admission.uet.edu.pk/"


# ------------------------------------------------------------
# PROJECT ROOT
# ------------------------------------------------------------
#
# File:
# D:\UET Chatbot\app\discovery\admissiondiscovery.py
#
# parents[0] = discovery
# parents[1] = app
# parents[2] = D:\UET Chatbot
#
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------
# INVENTORY DIRECTORY
# ------------------------------------------------------------

INVENTORY_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)


# ------------------------------------------------------------
# OUTPUT FILE
# ------------------------------------------------------------

OUTPUT_FILE = (
    INVENTORY_DIR
    / "_sections.json"
)


# ------------------------------------------------------------
# HTTP SETTINGS
# ------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

TIMEOUT = 20


# ============================================================
# FETCH ADMISSION HOMEPAGE
# ============================================================

def fetch_admission_homepage():
    """
    Fetch ONLY the UET Admission homepage.

    No discovered URLs are requested here.
    """

    response = requests.get(
        ADMISSION_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response


# ============================================================
# ANALYZE NAVIGATION
# ============================================================

def discover_sections(soup):
    """
    Analyze ONLY the Admission homepage.

    Discover meaningful links from navigation elements.

    No discovered URL is crawled.
    """

    sections = []

    # --------------------------------------------------------
    # Search navigation containers
    # --------------------------------------------------------

    navigation_candidates = soup.find_all(
        ["nav", "ul"]
    )

    for container in navigation_candidates:

        links = container.find_all(
            "a",
            href=True,
        )

        if not links:
            continue

        for link in links:

            name = link.get_text(
                " ",
                strip=True,
            )

            href = link.get(
                "href",
                "",
            ).strip()

            # ------------------------------------------------
            # Ignore empty links
            # ------------------------------------------------

            if not name or not href:
                continue

            # ------------------------------------------------
            # Ignore page anchors
            #
            # Example:
            # #programs
            # ------------------------------------------------

            if href.startswith("#"):
                continue

            # ------------------------------------------------
            # Ignore JavaScript links
            # ------------------------------------------------

            if href.lower().startswith(
                ("javascript:", "mailto:")
            ):
                continue

            # ------------------------------------------------
            # Convert relative URL → absolute URL
            # ------------------------------------------------

            url = urljoin(
                ADMISSION_URL,
                href,
            )

            sections.append(
                {
                    "name": name,
                    "url": url,
                }
            )

    return sections


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(sections):
    """
    Remove duplicate name + URL combinations.
    """

    seen = set()
    unique = []

    for section in sections:

        name = section["name"].strip()
        url = section["url"].strip()

        key = (
            name.lower(),
            url.rstrip("/"),
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            {
                "name": name,
                "url": url,
            }
        )

    return unique


# ============================================================
# REMOVE NON-ADMISSION / UNWANTED LINKS
# ============================================================

def filter_sections(sections):
    """
    Keep links that are useful for Admission discovery.

    We do NOT crawl them here.
    """

    filtered = []

    for section in sections:

        name = section["name"]
        url = section["url"]

        parsed_url = url.lower()

        # ----------------------------------------------------
        # Skip Cloudflare email protection endpoint
        # ----------------------------------------------------

        if "cdn-cgi/l/email-protection" in parsed_url:
            continue

        # ----------------------------------------------------
        # Skip external action/contact systems
        #
        # Complaint system is not admission knowledge content.
        # ----------------------------------------------------

        if "ecat.uet.edu.pk" in parsed_url:
            continue

        filtered.append(section)

    return filtered


# ============================================================
# SAVE INVENTORY
# ============================================================

def save_inventory(sections):
    """
    Save Admission homepage discovery results.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "source": ADMISSION_URL,

        "stage": (
            "admission_homepage_discovery"
        ),

        "crawl_policy": {
            "homepage_only": True,
            "discovered_links_crawled": False,
        },

        "sections": sections,
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# DISPLAY RESULT
# ============================================================

def display_result(
    response,
    sections,
):
    """
    Display discovery results.
    """

    print()

    print(
        "# UET ADMISSION — HOMEPAGE ANALYZER"
    )

    print()

    print(
        f"Project: {PROJECT_ROOT}"
    )

    print(
        f"URL: {response.url}"
    )

    print(
        f"Status: {response.status_code}"
    )

    print(
        "Content-Type: "
        f"{response.headers.get('Content-Type', 'unknown')}"
    )

    print()

    for index, section in enumerate(
        sections,
        start=1,
    ):

        print(
            f"[{index:02d}] "
            f"{section['name']}"
        )

        print(
            f"     {section['url']}"
        )

    print()

    print("=" * 70)

    print(
        f"ADMISSION LINKS FOUND: "
        f"{len(sections)}"
    )

    print("=" * 70)

    print()

    print("IMPORTANT:")

    print(
        "Only the Admission homepage was requested."
    )

    print(
        "No discovered URL was crawled."
    )

    print()

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "# UET ADMISSION — HOMEPAGE DISCOVERY"
    )

    print()

    print(
        f"Project root: {PROJECT_ROOT}"
    )

    print(
        f"Output:       {OUTPUT_FILE}"
    )

    print()

    try:

        # ----------------------------------------------------
        # 1. Fetch homepage
        # ----------------------------------------------------

        response = fetch_admission_homepage()

        # ----------------------------------------------------
        # 2. Parse HTML
        # ----------------------------------------------------

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        # ----------------------------------------------------
        # 3. Discover links
        # ----------------------------------------------------

        sections = discover_sections(
            soup
        )

        # ----------------------------------------------------
        # 4. Remove duplicates
        # ----------------------------------------------------

        sections = remove_duplicates(
            sections
        )

        # ----------------------------------------------------
        # 5. Remove unwanted endpoints
        # ----------------------------------------------------

        sections = filter_sections(
            sections
        )

        # ----------------------------------------------------
        # 6. Save
        # ----------------------------------------------------

        save_inventory(
            sections
        )

        # ----------------------------------------------------
        # 7. Display
        # ----------------------------------------------------

        display_result(
            response,
            sections,
        )

    except requests.RequestException as exc:

        print()

        print(
            "ERROR: Failed to fetch "
            "Admission homepage."
        )

        print(exc)

        print()

    except Exception as exc:

        print()

        print("ERROR:")

        print(exc)

        print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()