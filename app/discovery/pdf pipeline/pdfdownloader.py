import json
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests


# ============================================================
# UET CHATBOT — PDF DOWNLOADER
# ============================================================
#
# Input:
#   data/inventory/admission/_pages_reviewed.json
#   (uses the "files" list — 29 KEEP_FILE entries)
#
# Output:
#   data/inventory/admission/pdfs/<filename>.pdf   (actual files)
#   data/inventory/admission/_pdf_downloads.json    (manifest)
#
# Purpose:
#   Download every KEEP_FILE PDF referenced in the reviewed
#   pages data, verify it is actually a PDF (not an error page
#   or HTML redirect wearing a .pdf URL), and build a manifest
#   that the next stage (text extraction) will read.
#
# Important policy:
#
#   A successful HTTP 200 is NOT proof of a real PDF.
#   Every downloaded file is checked for the "%PDF" magic
#   header before being marked DOWNLOADED.
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

INPUT_FILE = DATA_DIR / "_pages_reviewed.json"

PDF_DIR = DATA_DIR / "pdfs"

OUTPUT_FILE = DATA_DIR / "_pdf_downloads.json"


# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_DELAY = 1.0

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "UET-AI-Assistant-Research-Bot/0.1 "
    "(independent student research project)"
)

PDF_MAGIC_HEADER = b"%PDF"

MAX_RETRIES = 2


# ============================================================
# LOAD
# ============================================================

def load_files():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nPages-reviewed file was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run pagereviewer.py first."
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    files = data.get("files", [])

    if not isinstance(files, list):

        raise ValueError(
            "Expected 'files' to be a list in "
            "_pages_reviewed.json."
        )

    return files


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def get_local_filename(url):
    """
    Derive a stable local filename from the URL's last path
    segment.

    Example:
        https://.../uploads/downloads/abc-123.pdf
        -> abc-123.pdf

        https://.../uploads/prospectus/UG-2026-1_xyz.pdf
        -> UG-2026-1_xyz.pdf
    """

    path = urlsplit(url).path

    filename = path.rsplit("/", 1)[-1]

    filename = filename.strip()

    if not filename or not filename.lower().endswith(".pdf"):

        return ""

    return filename


def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT
    })

    return session


# ============================================================
# DOWNLOAD
# ============================================================

def download_pdf(session, url, destination):
    """
    Download a single PDF.

    Returns a dict describing the outcome. Does not raise for
    ordinary failures (network errors, non-PDF content) so the
    caller can keep going through the rest of the list.
    """

    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            status_code = response.status_code

            if status_code != 200:

                last_error = (
                    f"HTTP {status_code}"
                )

                continue

            content = response.content

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            # ------------------------------------------------
            # Verify actual PDF content, not just status/type.
            # ------------------------------------------------

            if not content.startswith(PDF_MAGIC_HEADER):

                return {
                    "status": "NOT_A_PDF",
                    "http_status": status_code,
                    "content_type": content_type,
                    "size_bytes": len(content),
                    "error": (
                        "Response did not start with "
                        "the %PDF magic header"
                    ),
                }

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with destination.open("wb") as file:

                file.write(content)

            return {
                "status": "DOWNLOADED",
                "http_status": status_code,
                "content_type": content_type,
                "size_bytes": len(content),
                "error": "",
            }

        except requests.RequestException as error:

            last_error = str(error)

    return {
        "status": "FAILED",
        "http_status": None,
        "content_type": "",
        "size_bytes": 0,
        "error": last_error or "Unknown error",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PDF DOWNLOADER"
    )
    print("=" * 70)

    files = load_files()

    print()
    print(
        f"Files listed: {len(files)}"
    )

    session = create_session()

    manifest_entries = []

    counts = {
        "DOWNLOADED": 0,
        "NOT_A_PDF": 0,
        "FAILED": 0,
        "SKIPPED_NOT_KEEP_FILE": 0,
        "SKIPPED_BAD_URL": 0,
        "SKIPPED_ALREADY_EXISTS": 0,
    }

    print()
    print("=" * 70)
    print(
        "DOWNLOADING"
    )
    print("=" * 70)

    for index, item in enumerate(files, start=1):

        url = normalize(
            item.get("url")
        )

        title = normalize(
            item.get("title")
        )

        decision = normalize(
            item.get("decision")
        )

        print()
        print(
            f"[{index:03d}/{len(files):03d}] "
            f"{title or '(no title)'}"
        )

        print(
            f"        {url}"
        )

        # ------------------------------------------------
        # Only download files explicitly marked KEEP_FILE.
        # ------------------------------------------------

        if decision != "KEEP_FILE":

            print(
                f"        SKIPPED "
                f"(decision={decision or 'MISSING'})"
            )

            counts["SKIPPED_NOT_KEEP_FILE"] += 1

            manifest_entries.append({
                "url": url,
                "title": title,
                "decision": decision,
                "local_filename": "",
                "local_path": "",
                "status": "SKIPPED_NOT_KEEP_FILE",
                "http_status": None,
                "content_type": "",
                "size_bytes": 0,
                "error": "",
            })

            continue

        local_filename = get_local_filename(url)

        if not local_filename:

            print(
                "        SKIPPED (could not derive "
                ".pdf filename from URL)"
            )

            counts["SKIPPED_BAD_URL"] += 1

            manifest_entries.append({
                "url": url,
                "title": title,
                "decision": decision,
                "local_filename": "",
                "local_path": "",
                "status": "SKIPPED_BAD_URL",
                "http_status": None,
                "content_type": "",
                "size_bytes": 0,
                "error": "Could not derive .pdf filename",
            })

            continue

        destination = PDF_DIR / local_filename

        # ------------------------------------------------
        # Skip re-downloading files we already have.
        # ------------------------------------------------

        if destination.exists():

            print(
                f"        SKIPPED (already exists: "
                f"{local_filename})"
            )

            counts["SKIPPED_ALREADY_EXISTS"] += 1

            manifest_entries.append({
                "url": url,
                "title": title,
                "decision": decision,
                "local_filename": local_filename,
                "local_path": str(destination),
                "status": "SKIPPED_ALREADY_EXISTS",
                "http_status": None,
                "content_type": "",
                "size_bytes": destination.stat().st_size,
                "error": "",
            })

            continue

        result = download_pdf(
            session,
            url,
            destination,
        )

        print(
            f"        {result['status']} "
            f"({result['size_bytes']} bytes)"
        )

        if result["error"]:

            print(
                f"        Error: {result['error']}"
            )

        counts[result["status"]] = (
            counts.get(result["status"], 0) + 1
        )

        manifest_entries.append({
            "url": url,
            "title": title,
            "decision": decision,
            "local_filename": local_filename,
            "local_path": (
                str(destination)
                if result["status"] == "DOWNLOADED"
                else ""
            ),
            **result,
        })

        time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "SUMMARY"
    )
    print("=" * 70)

    print()

    for status, count in counts.items():

        print(
            f"  {status:<28} : {count}"
        )

    # --------------------------------------------------------
    # Save manifest
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "pdf_download",
        "input_file": str(INPUT_FILE),
        "pdf_dir": str(PDF_DIR),
        "output_file": str(OUTPUT_FILE),
        "counts": counts,
        "files": manifest_entries,
    }

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    print(
        "SAVED"
    )
    print("=" * 70)

    print()
    print(
        f"PDFs saved to: {PDF_DIR}"
    )

    print(
        f"Manifest saved to: {OUTPUT_FILE}"
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()