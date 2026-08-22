import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


START_URL = "https://www.uet.edu.pk/home/"

ALLOWED_DOMAIN = "www.uet.edu.pk"

MAX_PAGES = 20

REQUEST_DELAY = 1.0

OUTPUT_DIR = Path("data/raw")

USER_AGENT = "UET-AI-Assistant-Research-Bot/0.1"


def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT
    })

    return session


def normalize_url(url: str) -> str:
    """
    Normalize a URL so that duplicate URLs are easier to detect.
    """

    url = urldefrag(url)[0]

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    normalized = f"{scheme}://{netloc}{path}"

    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


def is_allowed_url(url: str) -> bool:
    """
    Only allow URLs belonging to the main UET domain.
    """

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    if parsed.netloc.lower() != ALLOWED_DOMAIN:
        return False

    return True


def fetch_page(session, url: str):
    """
    Download a webpage.
    """

    try:
        response = session.get(
            url,
            timeout=20,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if "text/html" not in content_type:
            print(f"Skipping non-HTML content: {url}")
            return None

        return response.text

    except requests.RequestException as error:
        print(f"ERROR: {url}")
        print(f"       {error}")

        return None


def extract_page(url: str, html: str) -> dict:
    """
    Extract useful information from an HTML page.
    """

    soup = BeautifulSoup(html, "html.parser")

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        )

    text = soup.get_text(
        separator="\n",
        strip=True
    )

    links = []

    for anchor in soup.find_all("a", href=True):

        href = anchor["href"].strip()

        absolute_url = urljoin(
            url,
            href
        )

        absolute_url = normalize_url(
            absolute_url
        )

        if is_allowed_url(absolute_url):
            links.append(absolute_url)

    links = sorted(set(links))

    return {
        "url": url,
        "title": title,
        "content": text,
        "links": links,
        "crawled_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def save_page(page: dict, page_number: int):
    """
    Save a crawled page as JSON.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        OUTPUT_DIR /
        f"page_{page_number:06d}.json"
    )

    with filename.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            page,
            file,
            ensure_ascii=False,
            indent=2
        )

    return filename


def crawl():
    """
    Main crawling loop.
    """

    session = create_session()

    queue = deque()

    queue.append(
        normalize_url(START_URL)
    )

    visited = set()

    saved_pages = 0

    while queue and saved_pages < MAX_PAGES:

        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)

        print(
            f"\n[{saved_pages + 1}/{MAX_PAGES}] "
            f"Crawling: {url}"
        )

        html = fetch_page(
            session,
            url
        )

        if html is None:
            continue

        page = extract_page(
            url,
            html
        )

        saved_pages += 1

        filename = save_page(
            page,
            saved_pages
        )

        print(
            f"Saved: {filename}"
        )

        for link in page["links"]:

            if link not in visited:
                queue.append(link)

        time.sleep(
            REQUEST_DELAY
        )

    print("\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)

    print(f"Pages saved : {saved_pages}")
    print(f"URLs visited: {len(visited)}")
    print(f"Output      : {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    crawl()