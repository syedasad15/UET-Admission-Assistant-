# app/discovery/section/_discovery.py

import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

# HOME_URL = "https://www.uet.edu.pk/home/"

# OUTPUT_FILE = (
#     Path(__file__).resolve().parents[3]
#     / "data"
#     / "inventory"
#     / "main"
#     / "_sections.json"
# )

HOME_URL = "https://www.uet.edu.pk/home/"

# --------------------------------------------------------
# NOTE (fixed):
#
# This used to be computed as
#   Path(__file__).resolve().parents[3]
# which depended on this file's exact folder depth.
#
# It was ALSO wrong before this fix: it resolved to one
# level ABOVE the "UET Chatbot" project folder instead of
# inside it, so output was silently written outside the
# project (e.g. D:\data\... instead of
# D:\UET Chatbot\data\...).
#
# Using a hardcoded PROJECT_ROOT matches every other script
# in this codebase and is immune to future folder moves.
# --------------------------------------------------------

PROJECT_ROOT = Path(r"D:\UET Chatbot")

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "main"
    / "_sections.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

TIMEOUT = 20


# ============================================================
# FETCH HOMEPAGE
# ============================================================

def fetch_homepage():
    response = requests.get(
        HOME_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response


# ============================================================
# FIND QUICK LINKS
# ============================================================

def find_quick_links(soup):
    """
    Find the homepage's small top-level navigation.

    UET currently exposes this as:

        <ul class="nav-menu" id="nav_nav-main-addition">

    It contains:

        News & Events
        Admission
        LMS
        Donate
        Financial Aid
        Contacts
        UET Email

    We intentionally DO NOT crawl the large main navigation.
    """

    # --------------------------------------------------------
    # Primary selector: exact UET quick-links navigation
    # --------------------------------------------------------

    quick_menu = soup.find(
        "ul",
        id="nav_nav-main-addition",
    )

    # --------------------------------------------------------
    # Fallback: class-based lookup
    # --------------------------------------------------------

    if quick_menu is None:
        candidates = soup.find_all(
            "ul",
            class_="nav-menu",
        )

        for menu in candidates:
            links = menu.find_all("a", href=True)

            if len(links) == 7:
                quick_menu = menu
                break

    if quick_menu is None:
        return []

    # --------------------------------------------------------
    # Extract links
    # --------------------------------------------------------

    sections = []

    for link in quick_menu.find_all("a", href=True):
        name = link.get_text(" ", strip=True)
        href = link.get("href", "").strip()

        if not name or not href:
            continue

        # Ignore anchor-only links
        if href.startswith("#"):
            continue

        absolute_url = urljoin(HOME_URL, href)

        sections.append(
            {
                "name": name,
                "url": absolute_url,
            }
        )

    return sections


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(sections):
    seen = set()
    result = []

    for section in sections:
        url = section["url"]

        if url in seen:
            continue

        seen.add(url)
        result.append(section)

    return result


# ============================================================
# SAVE INVENTORY
# ============================================================

def save_inventory(sections):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "source": HOME_URL,
        "stage": "homepage_section_discovery",
        "crawl_policy": {
            "homepage_only": True,
            "discovered_links_crawled": False,
        },
        "sections": sections,
    }

    with open(
        OUTPUT_FILE,
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

def display_result(sections):
    print()
    print("# UET WEBSITE — HOME PAGE ANALYZER")
    print()

    print(f"URL: {HOME_URL}")
    print("Status: 200")
    print("Content-Type: text/html")
    print()

    for index, section in enumerate(sections, start=1):
        print(f"[{index:02d}] {section['name']}")
        print(f"     {section['url']}")

    print()
    print("=" * 70)
    print(f"MAIN ENTRY SECTIONS FOUND: {len(sections)}")
    print("=" * 70)

    print()
    print("IMPORTANT:")
    print("Only the UET homepage was requested.")
    print("No discovered URL was crawled.")
    print("Large navigation menus, news, pagination and footer links were ignored.")
    print()

    print(f"Saved to: {OUTPUT_FILE}")


# ============================================================
# MAIN
# ============================================================

def main():
    try:
        response = fetch_homepage()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        sections = find_quick_links(soup)
        sections = remove_duplicates(sections)

        if not sections:
            print("ERROR: Could not find the UET quick-links section.")
            return

        save_inventory(sections)

        # Replace status information with actual values
        print()
        print("# UET WEBSITE — HOME PAGE ANALYZER")
        print()
        print(f"URL: {response.url}")
        print(f"Status: {response.status_code}")
        print(
            f"Content-Type: "
            f"{response.headers.get('Content-Type', 'unknown')}"
        )

        print()

        for index, section in enumerate(sections, start=1):
            print(f"[{index:02d}] {section['name']}")
            print(f"     {section['url']}")

        print()
        print("=" * 70)
        print(f"MAIN ENTRY SECTIONS FOUND: {len(sections)}")
        print("=" * 70)

        print()
        print("IMPORTANT:")
        print("Only the UET homepage was requested.")
        print("No discovered URL was crawled.")
        print("Large navigation menus, news, pagination and footer links were ignored.")
        print()
        print(f"Saved to: {OUTPUT_FILE}")

    except requests.RequestException as exc:
        print()
        print("ERROR: Failed to fetch UET homepage.")
        print(exc)

    except Exception as exc:
        print()
        print("ERROR:")
        print(exc)


if __name__ == "__main__":
    main()