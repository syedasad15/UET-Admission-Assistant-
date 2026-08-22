import hashlib
import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# UET CHATBOT — PDF DEDUPLICATOR
# ============================================================
#
# Input:
#   data/inventory/admission/_pdf_downloads.json
#
# Output:
#   data/inventory/admission/_pdf_duplicates.json
#
# Purpose:
#   Several downloaded PDFs may be byte-for-byte identical
#   even though they were linked from different URLs (e.g. a
#   generic "Download" link and a "Download Prospectus" link
#   pointing at the exact same file).
#
#   This script computes a SHA-256 hash of every successfully
#   downloaded PDF, groups files that are truly identical
#   (not just similar size), and picks ONE canonical copy per
#   group so that:
#
#       - text extraction only processes each unique document
#         once (not once per URL that happens to serve it)
#       - every original URL is still preserved as an "alias"
#         of the canonical file, so the chatbot can still hand
#         back whichever link the student actually clicked
#
# Important policy:
#
#   Canonical selection prefers a MEANINGFUL title (e.g.
#   "Download Prospectus", "Admission Guide") over a generic
#   one (e.g. "Download"), since a meaningful title is more
#   useful downstream (naming, categorization, review).
#
#   If all titles in a group are equally generic, the first
#   one encountered becomes canonical.
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

INPUT_FILE = DATA_DIR / "_pdf_downloads.json"

OUTPUT_FILE = DATA_DIR / "_pdf_duplicates.json"


# ============================================================
# CONFIGURATION
# ============================================================

# Titles that don't actually describe the document. A group
# whose canonical candidate has one of these titles will lose
# priority to any group member with a more specific title.
GENERIC_TITLES = {
    "download",
    "click here",
    "here",
    "link",
}

HASH_CHUNK_SIZE = 1024 * 1024  # 1 MB


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def is_generic_title(title):

    return normalize(title).lower() in GENERIC_TITLES


def compute_sha256(path):
    """
    Compute the SHA-256 hash of a file's contents, streamed
    in chunks so large PDFs don't need to be loaded fully
    into memory at once.
    """

    hasher = hashlib.sha256()

    with path.open("rb") as file:

        while True:

            chunk = file.read(HASH_CHUNK_SIZE)

            if not chunk:
                break

            hasher.update(chunk)

    return hasher.hexdigest()


# ============================================================
# LOAD
# ============================================================

def load_downloads():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nPDF downloads manifest was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run pdfdownloader.py first."
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
            "_pdf_downloads.json."
        )

    return files


# ============================================================
# HASHING
# ============================================================

def hash_downloaded_files(files):
    """
    Compute a hash for every entry marked DOWNLOADED.

    Returns:
        (hashed_entries, skipped_entries)
    """

    hashed_entries = []

    skipped_entries = []

    for item in files:

        status = normalize(
            item.get("status")
        )

        if status != "DOWNLOADED":

            skipped_entries.append(item)
            continue

        local_path = normalize(
            item.get("local_path")
        )

        path = Path(local_path)

        if not local_path or not path.exists():

            skipped_entries.append({
                **item,
                "dedup_error": (
                    "local_path missing or file "
                    "does not exist on disk"
                ),
            })

            continue

        file_hash = compute_sha256(path)

        hashed_entries.append({
            **item,
            "sha256": file_hash,
        })

    return hashed_entries, skipped_entries


# ============================================================
# GROUPING
# ============================================================

def group_by_hash(hashed_entries):

    groups = defaultdict(list)

    for entry in hashed_entries:

        groups[entry["sha256"]].append(entry)

    return dict(groups)


def choose_canonical(group):
    """
    Pick the canonical entry within a group of identical
    files.

    Preference order:
        1. Entry with a non-generic title
        2. First entry encountered
    """

    for entry in group:

        if not is_generic_title(
            entry.get("title", "")
        ):

            return entry

    return group[0]


# ============================================================
# BUILD REGISTRY
# ============================================================

def build_registry(groups):

    unique_documents = []

    duplicate_count = 0

    for file_hash, group in groups.items():

        canonical = choose_canonical(group)

        aliases = [
            {
                "url": entry.get("url", ""),
                "title": entry.get("title", ""),
                "local_filename": entry.get(
                    "local_filename",
                    "",
                ),
            }
            for entry in group
            if entry is not canonical
        ]

        duplicate_count += len(aliases)

        unique_documents.append({
            "sha256": file_hash,
            "size_bytes": canonical.get(
                "size_bytes",
                0,
            ),
            "canonical_url": canonical.get(
                "url",
                "",
            ),
            "canonical_title": canonical.get(
                "title",
                "",
            ),
            "canonical_local_filename": canonical.get(
                "local_filename",
                "",
            ),
            "canonical_local_path": canonical.get(
                "local_path",
                "",
            ),
            "group_size": len(group),
            "aliases": aliases,
        })

    return unique_documents, duplicate_count


# ============================================================
# SORT
# ============================================================

def sort_documents(documents):

    return sorted(
        documents,
        key=lambda item: (
            -item["group_size"],
            item["canonical_title"].lower(),
        ),
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_output(output):

    errors = []

    documents = output.get(
        "unique_documents",
        [],
    )

    seen_hashes = set()

    all_urls_in = set()

    all_urls_out = set()

    for doc in documents:

        file_hash = doc.get("sha256", "")

        if file_hash in seen_hashes:

            errors.append(
                f"Duplicate hash group emitted twice: "
                f"{file_hash}"
            )

        seen_hashes.add(file_hash)

        if not doc.get("canonical_url"):

            errors.append(
                f"Document with hash {file_hash} has "
                "no canonical_url."
            )

        all_urls_out.add(
            doc.get("canonical_url", "")
        )

        for alias in doc.get("aliases", []):

            all_urls_out.add(
                alias.get("url", "")
            )

    for entry in output.get(
        "_all_hashed_urls_for_validation",
        [],
    ):

        all_urls_in.add(entry)

    missing = all_urls_in - all_urls_out

    if missing:

        errors.append(
            f"{len(missing)} URL(s) present in input "
            "but missing from output registry."
        )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PDF DEDUPLICATOR"
    )
    print("=" * 70)

    files = load_downloads()

    print()
    print(
        f"Files listed: {len(files)}"
    )

    # --------------------------------------------------------
    # Hash
    # --------------------------------------------------------

    print()
    print(
        "Hashing downloaded files..."
    )

    hashed_entries, skipped_entries = hash_downloaded_files(
        files
    )

    print(
        f"Hashed: {len(hashed_entries)}"
    )

    print(
        f"Skipped (not downloaded / missing): "
        f"{len(skipped_entries)}"
    )

    # --------------------------------------------------------
    # Group
    # --------------------------------------------------------

    groups = group_by_hash(hashed_entries)

    unique_documents, duplicate_count = build_registry(
        groups
    )

    unique_documents = sort_documents(
        unique_documents
    )

    duplicate_groups = [
        doc
        for doc in unique_documents
        if doc["group_size"] > 1
    ]

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "DEDUPLICATION RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"Hashed files:        {len(hashed_entries)}"
    )

    print(
        f"Unique documents:    {len(unique_documents)}"
    )

    print(
        f"Duplicate groups:    {len(duplicate_groups)}"
    )

    print(
        f"Total duplicate URLs (aliases): {duplicate_count}"
    )

    # --------------------------------------------------------
    # Duplicate groups detail
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "DUPLICATE GROUPS"
    )
    print("=" * 70)

    if not duplicate_groups:

        print("None")

    else:

        for index, doc in enumerate(
            duplicate_groups,
            start=1,
        ):

            print()
            print(
                f"[{index:03d}] "
                f"{doc['group_size']} copies "
                f"({doc['size_bytes']} bytes)"
            )

            print(
                f"      Canonical: "
                f"{doc['canonical_title']}"
            )

            print(
                f"      {doc['canonical_url']}"
            )

            for alias in doc["aliases"]:

                print(
                    f"      Alias: "
                    f"{alias['title']}"
                )

                print(
                    f"      {alias['url']}"
                )

    # --------------------------------------------------------
    # Skipped
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "SKIPPED (not hashed)"
    )
    print("=" * 70)

    if not skipped_entries:

        print("None")

    else:

        for item in skipped_entries:

            print()
            print(
                f" — {item.get('title', '')}"
            )

            print(
                item.get('url', '')
            )

            print(
                f"   Status: "
                f"{item.get('status', '')}"
            )

            if item.get("dedup_error"):

                print(
                    f"   Reason: "
                    f"{item['dedup_error']}"
                )

    # --------------------------------------------------------
    # Build output
    # --------------------------------------------------------

    all_hashed_urls = [
        entry.get("url", "")
        for entry in hashed_entries
    ]

    output = {
        "source": "UET Admissions Portal",
        "stage": "pdf_deduplication",
        "input_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE),
        "counts": {
            "hashed_files": len(hashed_entries),
            "skipped_files": len(skipped_entries),
            "unique_documents": len(unique_documents),
            "duplicate_groups": len(duplicate_groups),
            "duplicate_urls": duplicate_count,
        },
        "unique_documents": unique_documents,
        "skipped": [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "status": item.get("status", ""),
                "reason": item.get("dedup_error", ""),
            }
            for item in skipped_entries
        ],
        "_all_hashed_urls_for_validation": all_hashed_urls,
    }

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate_output(
        output
    )

    if validation_errors:

        print(
            "INVALID"
        )

        for error in validation_errors:

            print(
                f"ERROR: {error}"
            )

        raise ValueError(
            "PDF deduplication validation failed."
        )

    else:

        print(
            "VALID"
        )

    # Internal-only validation helper key; not needed in the
    # saved file.
    del output["_all_hashed_urls_for_validation"]

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

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
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()