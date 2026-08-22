import json
import time
from pathlib import Path
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


# ============================================================
# UET CHATBOT — ADMISSION COURSE OUTLINE / SITE MAP BUILDER
# ============================================================
#
# Purpose:
#
# Build the structural map of the 9 selected Admission sections.
#
# This is NOT the final content crawler.
#
# Pipeline:
#
# admissiondiscovery.py
#          ↓
# _sections.json
#          ↓
# admissionselection.py
#          ↓
# _selected_sections.json
#          ↓
# THIS FILE
#          ↓
# _map.json
#          ↓
# CONTENT CRAWLER (later)
#
#
# The map answers:
#
#   What pages exist?
#   Which page belongs to which section?
#   What is the parent of each page?
#   What child links does each page contain?
#   What files were discovered?
#   What is the depth of each page?
#
# IMPORTANT:
#
# We do NOT extract/store full page content here.
# We are building the "course outline" first.
#
# ============================================================


# ============================================================
# FILES
# ============================================================
# ============================================================
# PROJECT PATHS
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
    / "_selected_sections.json"
)

OUTPUT_DIR = ADMISSION_ROOT

OUTPUT_FILE = (
    ADMISSION_ROOT
    / "_map.json"
)


print()
print("PATH CHECK")
print("=" * 70)

print("Project root:")
print(PROJECT_ROOT)
print()

print("Admission inventory:")
print(ADMISSION_ROOT)
print()

print("Input file:")
print(INPUT_FILE)
print()

print("Output file:")
print(OUTPUT_FILE)
print()

print("Project exists:", PROJECT_ROOT.exists())
print("Admission directory exists:", ADMISSION_ROOT.exists())
print("Selected sections exists:", INPUT_FILE.exists())

print("=" * 70)
print()
# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_DELAY = 0.5

# Safety limit.
#
# This protects us if one section unexpectedly contains
# thousands of links.
#
# We can increase this later after inspecting the map.
MAX_PAGES_PER_SECTION = 200


# ============================================================
# ADMISSION DOMAIN
# ============================================================

ADMISSION_HOST = "admission.uet.edu.pk"


# ============================================================
# FILE TYPES
# ============================================================

FILE_EXTENSIONS = {
    ".pdf": "pdf",
    ".doc": "document",
    ".docx": "document",
    ".xls": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".ppt": "presentation",
    ".pptx": "presentation",
    ".csv": "csv",
    ".txt": "text",
    ".zip": "archive",
    ".rar": "archive",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "UET-Chatbot-Admission-Mapper/1.0 "
            "(educational research)"
        )
    }
)


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(url):
    """
    Normalize a URL.

    Removes:
        - URL fragments
        - trailing slash

    Example:

        https://example.com/page/#abc

    becomes:

        https://example.com/page
    """

    url = urldefrag(url)[0]

    return url.rstrip("/")


# ============================================================
# URL HELPERS
# ============================================================

def get_extension(url):
    """
    Return lowercase file extension.
    """

    path = urlparse(url).path.lower()

    for extension in FILE_EXTENSIONS:

        if path.endswith(extension):
            return extension

    return ""


def get_file_type(url):
    """
    Determine whether URL is a known file type.
    """

    extension = get_extension(url)

    if extension:
        return FILE_EXTENSIONS[extension]

    return None


def is_http_url(url):
    """
    Allow only HTTP/HTTPS URLs.
    """

    parsed = urlparse(url)

    return parsed.scheme in {
        "http",
        "https",
    }


def is_admission_url(url):
    """
    Keep the map restricted to the Admission website.
    """

    parsed = urlparse(url)

    hostname = (
        parsed.hostname or ""
    ).lower()

    return hostname == ADMISSION_HOST


# ============================================================
# TECHNICAL URL FILTER
# ============================================================

def is_ignored_url(url):
    """
    Ignore technical/non-useful URLs.
    """

    parsed = urlparse(url)

    path = parsed.path.lower()

    # Cloudflare email protection
    if "/cdn-cgi/" in path:
        return True

    # JavaScript
    if path.endswith(".js"):
        return True

    # CSS
    if path.endswith(".css"):
        return True

    # Images/media are mapped as files only,
    # not treated as pages.
    return False


# ============================================================
# LOAD SELECTED SECTIONS
# ============================================================

def load_selected_sections():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nSelected sections file not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run admissionselection.py first."
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    sections = data.get(
        "selected_sections",
        []
    )

    if not isinstance(sections, list):

        raise ValueError(
            "'selected_sections' must be a list."
        )

    return sections


# ============================================================
# FETCH
# ============================================================

def fetch_page(url):

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        return {
            "success": True,
            "status": response.status_code,
            "content_type": response.headers.get(
                "Content-Type",
                ""
            ),
            "html": response.text,
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "status": None,
            "content_type": "",
            "html": "",
            "error": str(error),
        }


# ============================================================
# PAGE TITLE
# ============================================================

def extract_title(soup):

    if soup.title:

        return soup.title.get_text(
            " ",
            strip=True
        )

    return ""


# ============================================================
# LINK TEXT
# ============================================================

def clean_link_text(text):

    return " ".join(
        text.strip().split()
    )


# ============================================================
# EXTRACT LINKS
# ============================================================

def extract_links(
    html,
    current_url
):
    """
    Discover links from a page.

    Returns both:
        pages
        files

    External domains are recorded separately
    but NOT followed.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    pages = []

    files = []

    external = []

    seen_pages = set()
    seen_files = set()
    seen_external = set()

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
            current_url,
            href
        )

        absolute_url = normalize_url(
            absolute_url
        )

        if not is_http_url(
            absolute_url
        ):
            continue

        link_text = clean_link_text(
            anchor.get_text(
                " ",
                strip=True
            )
        )

        file_type = get_file_type(
            absolute_url
        )

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        if file_type:

            if absolute_url not in seen_files:

                seen_files.add(
                    absolute_url
                )

                files.append(
                    {
                        "name": link_text,
                        "url": absolute_url,
                        "type": file_type,
                    }
                )

            continue

        # ----------------------------------------------------
        # EXTERNAL DOMAIN
        # ----------------------------------------------------

        if not is_admission_url(
            absolute_url
        ):

            if absolute_url not in seen_external:

                seen_external.add(
                    absolute_url
                )

                external.append(
                    {
                        "name": link_text,
                        "url": absolute_url,
                    }
                )

            continue

        # ----------------------------------------------------
        # TECHNICAL URL
        # ----------------------------------------------------

        if is_ignored_url(
            absolute_url
        ):
            continue

        # ----------------------------------------------------
        # INTERNAL PAGE
        # ----------------------------------------------------

        if absolute_url not in seen_pages:

            seen_pages.add(
                absolute_url
            )

            pages.append(
                {
                    "name": link_text,
                    "url": absolute_url,
                }
            )

    return {
        "pages": pages,
        "files": files,
        "external": external,
    }


# ============================================================
# CRAWL / MAP ONE SECTION
# ============================================================

def map_section(
    section_name,
    section_url
):
    """
    Build a hierarchical map for one selected section.

    BFS structure:

        root
          ↓
        children
          ↓
        grandchildren
          ↓
        etc.
    """

    section_url = normalize_url(
        section_url
    )

    print()
    print("=" * 75)
    print(
        f"SECTION: {section_name}"
    )
    print(
        f"ROOT:    {section_url}"
    )
    print("=" * 75)

    queue = deque()

    queue.append(
        {
            "url": section_url,
            "parent_url": None,
            "parent_name": None,
            "depth": 0,
            "link_name": section_name,
        }
    )

    visited = set()

    pages = {}

    while queue:

        item = queue.popleft()

        current_url = normalize_url(
            item["url"]
        )

        if current_url in visited:
            continue

        # ----------------------------------------------------
        # Safety limit
        # ----------------------------------------------------

        if len(pages) >= MAX_PAGES_PER_SECTION:

            print()
            print(
                "SAFETY LIMIT REACHED:"
            )

            print(
                f"{MAX_PAGES_PER_SECTION} pages"
            )

            break

        visited.add(
            current_url
        )

        print()
        print(
            f"[{len(pages) + 1:03}] "
            f"Depth: {item['depth']}"
        )

        print(
            current_url
        )

        result = fetch_page(
            current_url
        )

        # ----------------------------------------------------
        # Failed request
        # ----------------------------------------------------

        if not result["success"]:

            print(
                "ERROR:",
                result.get(
                    "error",
                    "unknown"
                )
            )

            pages[current_url] = {
                "name": item["link_name"],
                "url": current_url,
                "parent_url": item["parent_url"],
                "parent_name": item["parent_name"],
                "depth": item["depth"],
                "status": None,
                "type": "page",
                "success": False,
                "error": result.get(
                    "error",
                    "unknown"
                ),
                "children": [],
                "files": [],
                "external_links": [],
            }

            continue

        status = result["status"]

        content_type = (
            result["content_type"]
            or ""
        )

        print(
            "Status:",
            status
        )

        # ----------------------------------------------------
        # Non-HTML
        # ----------------------------------------------------

        if "text/html" not in (
            content_type.lower()
        ):

            print(
                "Skipped: non-HTML"
            )

            pages[current_url] = {
                "name": item["link_name"],
                "url": current_url,
                "parent_url": item["parent_url"],
                "parent_name": item["parent_name"],
                "depth": item["depth"],
                "status": status,
                "type": "non_html",
                "success": True,
                "children": [],
                "files": [],
                "external_links": [],
            }

            continue

        # ----------------------------------------------------
        # Parse HTML
        # ----------------------------------------------------

        soup = BeautifulSoup(
            result["html"],
            "html.parser"
        )

        title = extract_title(
            soup
        )

        discovered = extract_links(
            result["html"],
            current_url
        )

        child_pages = discovered[
            "pages"
        ]

        files = discovered[
            "files"
        ]

        external = discovered[
            "external"
        ]

        print(
            "Title:",
            title
        )

        print(
            "Child pages:",
            len(child_pages)
        )

        print(
            "Files:",
            len(files)
        )

        print(
            "External:",
            len(external)
        )

        # ----------------------------------------------------
        # Store page node
        # ----------------------------------------------------

        pages[current_url] = {
            "name": item["link_name"],
            "title": title,
            "url": current_url,

            "parent_url": (
                item["parent_url"]
            ),

            "parent_name": (
                item["parent_name"]
            ),

            "depth": item["depth"],

            "status": status,

            "type": "page",

            "success": True,

            "children": child_pages,

            "files": files,

            "external_links": external,
        }

        # ----------------------------------------------------
        # Queue child pages
        # ----------------------------------------------------

        for child in child_pages:

            child_url = child["url"]

            if child_url in visited:
                continue

            queue.append(
                {
                    "url": child_url,

                    "parent_url": (
                        current_url
                    ),

                    "parent_name": (
                        item["link_name"]
                    ),

                    "depth": (
                        item["depth"] + 1
                    ),

                    "link_name": (
                        child["name"]
                    ),
                }
            )

        time.sleep(
            REQUEST_DELAY
        )

    return pages


# ============================================================
# BUILD TREE
# ============================================================

def build_tree(pages, root_url):
    """
    Convert flat page inventory into a nested hierarchy.
    """

    root_url = normalize_url(
        root_url
    )

    nodes = {}

    # --------------------------------------------------------
    # Create nodes
    # --------------------------------------------------------

    for url, page in pages.items():

        nodes[url] = {
            "name": page.get(
                "name",
                ""
            ),

            "title": page.get(
                "title",
                ""
            ),

            "url": url,

            "depth": page.get(
                "depth",
                0
            ),

            "children": [],

            "files": page.get(
                "files",
                []
            ),
        }

    # --------------------------------------------------------
    # Connect children
    # --------------------------------------------------------

    for url, page in pages.items():

        parent_url = page.get(
            "parent_url"
        )

        if (
            parent_url
            and parent_url in nodes
            and url != root_url
        ):

            nodes[parent_url][
                "children"
            ].append(
                nodes[url]
            )

    # --------------------------------------------------------
    # Root
    # --------------------------------------------------------

    return nodes.get(
        root_url
    )


# ============================================================
# PRINT TREE
# ============================================================

def print_tree(
    node,
    prefix="",
    is_last=True
):
    """
    Print the course outline in tree form.
    """

    if not node:
        return

    connector = "└── " if is_last else "├── "

    print(
        prefix
        + connector
        + node.get(
            "name",
            "Unnamed"
        )
    )

    print(
        prefix
        + ("    " if is_last else "│   ")
        + node.get(
            "url",
            ""
        )
    )

    children = node.get(
        "children",
        []
    )

    files = node.get(
        "files",
        []
    )

    # --------------------------------------------------------
    # Child pages
    # --------------------------------------------------------

    total_items = (
        len(children)
        + len(files)
    )

    current = 0

    for child in children:

        current += 1

        print_tree(
            child,
            prefix
            + ("    " if is_last else "│   "),
            current == total_items
        )

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    for file_item in files:

        current += 1

        connector = (
            "└── "
            if current == total_items
            else "├── "
        )

        print(
            prefix
            + ("    " if is_last else "│   ")
            + connector
            + "[FILE] "
            + file_item.get(
                "name",
                "Unnamed file"
            )
        )

        print(
            prefix
            + ("    " if is_last else "│   ")
            + ("    " if current == total_items else "│   ")
            + file_item.get(
                "url",
                ""
            )
        )


# ============================================================
# SAVE MAP
# ============================================================

def save_map(
    selected_sections,
    section_maps
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total_pages = sum(
        len(item["pages"])
        for item in section_maps
    )

    total_files = sum(
        item["file_count"]
        for item in section_maps
    )

    total_external = sum(
        item["external_count"]
        for item in section_maps
    )

    result = {

        "source": (
            "https://admission.uet.edu.pk/"
        ),

        "stage": (
            "admission_course_outline"
        ),

        "description": (
            "Structural map of selected "
            "Admission sections. "
            "No page content is stored."
        ),

        "crawl_policy": {

            "selected_sections_only": True,

            "admission_domain_only": True,

            "content_extraction": False,

            "files_downloaded": False,

            "external_links_followed": False,

            "max_pages_per_section": (
                MAX_PAGES_PER_SECTION
            ),
        },

        "selected_sections": (
            selected_sections
        ),

        "counts": {

            "sections": len(
                section_maps
            ),

            "pages": total_pages,

            "files": total_files,

            "external_links": total_external,
        },

        "sections": section_maps,
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
# MAIN
# ============================================================

def main():

    print()

    print(
        "# UET ADMISSION — COURSE OUTLINE BUILDER"
    )

    print()

    print(
        f"Reading: {INPUT_FILE}"
    )

    selected_sections = (
        load_selected_sections()
    )

    print()

    print(
        "Selected sections:",
        len(selected_sections)
    )

    print()

    print(
        "MAP POLICY:"
    )

    print(
        "✓ Selected Admission sections only"
    )

    print(
        "✓ Admission domain only"
    )

    print(
        "✓ Child hierarchy discovered"
    )

    print(
        "✓ Files recorded"
    )

    print(
        "✓ External links recorded"
    )

    print(
        "✗ External websites NOT crawled"
    )

    print(
        "✗ Files NOT downloaded"
    )

    print(
        "✗ Full content NOT stored"
    )

    section_maps = []

    # ========================================================
    # PROCESS 9 SECTIONS
    # ========================================================

    for index, section in enumerate(
        selected_sections,
        start=1
    ):

        name = section.get(
            "name",
            ""
        ).strip()

        url = section.get(
            "url",
            ""
        ).strip()

        if not name or not url:
            continue

        print()

        print(
            f"\n### SECTION "
            f"{index}/{len(selected_sections)}"
        )

        pages = map_section(
            name,
            url
        )

        root = build_tree(
            pages,
            url
        )

        file_count = sum(
            len(
                page.get(
                    "files",
                    []
                )
            )
            for page in pages.values()
        )

        external_count = sum(
            len(
                page.get(
                    "external_links",
                    []
                )
            )
            for page in pages.values()
        )

        section_maps.append(
            {
                "name": name,

                "url": normalize_url(
                    url
                ),

                "page_count": len(
                    pages
                ),

                "file_count": file_count,

                "external_count": (
                    external_count
                ),

                "pages": pages,

                "tree": root,
            }
        )

        # ----------------------------------------------------
        # Print hierarchy
        # ----------------------------------------------------

        print()

        print(
            f"COURSE OUTLINE: {name}"
        )

        print(
            "-" * 75
        )

        print_tree(
            root
        )

    # ========================================================
    # SAVE
    # ========================================================

    save_map(
        selected_sections,
        section_maps
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    total_pages = sum(
        item["page_count"]
        for item in section_maps
    )

    total_files = sum(
        item["file_count"]
        for item in section_maps
    )

    total_external = sum(
        item["external_count"]
        for item in section_maps
    )

    print()

    print("=" * 75)

    print(
        "COURSE OUTLINE COMPLETE"
    )

    print("=" * 75)

    print(
        "Sections:",
        len(section_maps)
    )

    print(
        "Pages discovered:",
        total_pages
    )

    print(
        "Files discovered:",
        total_files
    )

    print(
        "External links discovered:",
        total_external
    )

    print()

    print(
        "Saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This is a STRUCTURAL MAP."
    )

    print(
        "No full page content was stored."
    )

    print(
        "No files were downloaded."
    )

    print(
        "External websites were not crawled."
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()