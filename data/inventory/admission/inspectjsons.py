"""
Admission JSON Inventory Inspector
-----------------------------------

SAFE READ-ONLY inspection of:

D:\\UET Chatbot\\data\\inventory\\admission

This script:
- discovers JSON files automatically
- categorizes them
- safely loads JSON
- reports structure and record counts
- inspects per-PDF knowledge files
- inspects recovered files
- inspects global chunks separately
- NEVER modifies any JSON file
"""

import json
from pathlib import Path
from collections import Counter


# ============================================================
# CONFIG
# ============================================================

ADMISSION_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")


# ============================================================
# SAFE JSON LOADER
# ============================================================

def load_json(path):
    """
    ALWAYS returns exactly:

        (data, error)

    error is None when successful.
    """

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data, None

    except Exception as e:
        return None, str(e)


# ============================================================
# CATEGORIZATION
# ============================================================

def categorize(filename):

    if filename == "_pdf_duplicates.json":
        return "PDF DUPLICATE REGISTRY"

    if filename == "_pdf_extraction_skip_summary.json":
        return "SKIP SUMMARY"

    if filename == "_pdf_knowledge_chunks.json":
        return "GLOBAL KNOWLEDGE CHUNKS"

    if filename == "_pdf_recovered_chunks.json":
        return "RECOVERED CHUNKS"

    if filename == "_pdf_recovered_native_chunks.json":
        return "RECOVERED NATIVE CHUNKS"

    if filename == "_pdf_recovered_native_pages.json":
        return "RECOVERED NATIVE PAGES"

    if filename == "_pdf_recovered_pages.json":
        return "RECOVERED PAGES"

    if filename == "_pdf_recovered_native_audit.json":
        return "RECOVERY AUDIT"

    if filename.startswith("_pdf_knowledge_"):
        return "PER-PDF KNOWLEDGE"

    return "OTHER JSON"


# ============================================================
# BASIC STRUCTURE DESCRIPTION
# ============================================================

def describe_structure(data):

    if isinstance(data, list):

        if not data:
            return "list (empty)"

        first = data[0]

        if isinstance(first, dict):
            return f"list[{len(data)}] of objects"

        return f"list[{len(data)}] of {type(first).__name__}"

    if isinstance(data, dict):

        keys = list(data.keys())

        preview = ", ".join(keys[:8])

        if len(keys) > 8:
            preview += ", ..."

        return f"object {{{preview}}}"

    return type(data).__name__


# ============================================================
# COUNT HELPERS
# ============================================================

def count_pages(data):

    if isinstance(data, dict):

        pages = data.get("pages")

        if isinstance(pages, list):
            return len(pages)

    return None


def count_chunks(data):

    if isinstance(data, list):

        # Global/recovered chunk lists
        return len(data)

    if isinstance(data, dict):

        chunks = data.get("chunks")

        if isinstance(chunks, list):
            return len(chunks)

    return None


def count_skipped(data):

    if isinstance(data, dict):

        skipped = data.get("skipped_pages")

        if isinstance(skipped, list):
            return len(skipped)

    return None


def count_quality_flags(data):

    if not isinstance(data, list):
        return Counter()

    counter = Counter()

    for item in data:

        if not isinstance(item, dict):
            continue

        quality = item.get("quality")

        if isinstance(quality, dict):

            flag = quality.get("flag")

            if flag:
                counter[flag] += 1

        quality_flag = item.get("quality_flag")

        if quality_flag:
            counter[quality_flag] += 1

    return counter


# ============================================================
# PER-PDF INSPECTION
# ============================================================

def inspect_per_pdf(path, data):

    print(f"\n  {path.name}")

    if not isinstance(data, dict):

        print(f"     Structure : {describe_structure(data)}")
        print("     [WARNING] Expected object with pages.")
        return

    pages = data.get("pages", [])

    if not isinstance(pages, list):

        print("     Pages     : NOT A LIST")
        return

    page_count = len(pages)

    usable_pages = 0
    skipped_pages = 0
    total_chunks = 0

    sources = Counter()
    quality_flags = Counter()

    for page in pages:

        if not isinstance(page, dict):
            continue

        if page.get("skipped"):
            skipped_pages += 1
        else:
            usable_pages += 1

        source = page.get("source")

        if source:
            sources[source] += 1

        quality = page.get("quality")

        if isinstance(quality, dict):

            flag = quality.get("flag")

            if flag:
                quality_flags[flag] += 1

        chunks = page.get("chunks", [])

        if isinstance(chunks, list):
            total_chunks += len(chunks)

    print(f"     Pages     : {page_count}")
    print(f"     Usable    : {usable_pages}")
    print(f"     Skipped   : {skipped_pages}")
    print(f"     Chunks    : {total_chunks}")

    if sources:
        print(f"     Sources   : {dict(sources)}")

    if quality_flags:
        print(f"     Quality   : {dict(quality_flags)}")


# ============================================================
# SPECIAL FILE INSPECTION
# ============================================================

def inspect_special(name, data):

    print(f"\n  {name}")

    print(f"     Structure : {describe_structure(data)}")

    if isinstance(data, list):

        print(f"     Records   : {len(data)}")

        if data and isinstance(data[0], dict):

            keys = list(data[0].keys())

            print(
                "     Record keys:",
                ", ".join(keys[:15])
            )

    elif isinstance(data, dict):

        print(f"     Keys      : {len(data)}")

        if "total_skipped_pages" in data:
            print(
                f"     Skipped   : {data.get('total_skipped_pages')}"
            )

        if "skipped_pages" in data:
            skipped = data.get("skipped_pages")

            if isinstance(skipped, list):
                print(
                    f"     Skip records: {len(skipped)}"
                )

        if "total" in data:
            print(f"     Total     : {data.get('total')}")

        if "pages" in data and isinstance(data["pages"], list):
            print(f"     Pages     : {len(data['pages'])}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)
    print("ADMISSION JSON INVENTORY INSPECTION")
    print("=" * 90)

    print()
    print("Directory:")
    print(ADMISSION_DIR)

    if not ADMISSION_DIR.exists():

        print("\n[ERROR] Directory does not exist.")
        return

    json_files = sorted(
        ADMISSION_DIR.glob("*.json"),
        key=lambda p: p.name.lower()
    )

    print()
    print(f"JSON files found: {len(json_files)}")

    if not json_files:
        print("[ERROR] No JSON files found.")
        return

    # --------------------------------------------------------
    # Categorize
    # --------------------------------------------------------

    categories = {}

    for path in json_files:

        category = categorize(path.name)

        categories.setdefault(category, []).append(path)

    # --------------------------------------------------------
    # FILE LIST
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print("JSON FILE LIST")
    print("=" * 90)

    category_order = [
        "OTHER JSON",
        "PDF DUPLICATE REGISTRY",
        "SKIP SUMMARY",
        "PER-PDF KNOWLEDGE",
        "GLOBAL KNOWLEDGE CHUNKS",
        "RECOVERED CHUNKS",
        "RECOVERY AUDIT",
        "RECOVERED NATIVE CHUNKS",
        "RECOVERED NATIVE PAGES",
        "RECOVERED PAGES",
    ]

    for category in category_order:

        files = categories.get(category, [])

        if not files:
            continue

        print()
        print(f"[{category}]")

        for path in files:
            print(f"   {path.name}")

    # --------------------------------------------------------
    # LOAD ALL
    # --------------------------------------------------------

    loaded = {}
    errors = []

    for path in json_files:

        data, error = load_json(path)

        if error:

            errors.append(
                {
                    "file": path.name,
                    "error": error,
                }
            )

        else:

            loaded[path.name] = data

    # --------------------------------------------------------
    # LOAD STATUS
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print("JSON LOAD STATUS")
    print("=" * 90)

    print()
    print(f"Successfully loaded : {len(loaded)}")
    print(f"Failed to load      : {len(errors)}")

    if errors:

        print()

        for item in errors:

            print(f"[ERROR] {item['file']}")
            print(f"        {item['error']}")

    # --------------------------------------------------------
    # PER-PDF KNOWLEDGE
    # --------------------------------------------------------

    per_pdf_files = categories.get(
        "PER-PDF KNOWLEDGE",
        []
    )

    print()
    print("=" * 90)
    print("PER-PDF KNOWLEDGE INVENTORY")
    print("=" * 90)

    total_pdf_pages = 0
    total_pdf_chunks = 0
    total_pdf_skipped = 0

    for path in per_pdf_files:

        data = loaded.get(path.name)

        if data is None:
            continue

        inspect_per_pdf(path, data)

        pages = count_pages(data)

        if pages is not None:
            total_pdf_pages += pages

        if isinstance(data, dict):

            page_records = data.get("pages", [])

            if isinstance(page_records, list):

                for page in page_records:

                    if not isinstance(page, dict):
                        continue

                    if page.get("skipped"):
                        total_pdf_skipped += 1

                    chunks = page.get("chunks", [])

                    if isinstance(chunks, list):
                        total_pdf_chunks += len(chunks)

    print()
    print("-" * 90)
    print("PER-PDF TOTALS")
    print("-" * 90)

    print(f"PDF knowledge files : {len(per_pdf_files)}")
    print(f"Total pages         : {total_pdf_pages}")
    print(f"Total chunks        : {total_pdf_chunks}")
    print(f"Total skipped pages : {total_pdf_skipped}")

    # --------------------------------------------------------
    # GLOBAL / RECOVERY FILES
    # --------------------------------------------------------

    special_categories = [
        "GLOBAL KNOWLEDGE CHUNKS",
        "RECOVERED CHUNKS",
        "RECOVERY AUDIT",
        "RECOVERED NATIVE CHUNKS",
        "RECOVERED NATIVE PAGES",
        "RECOVERED PAGES",
        "SKIP SUMMARY",
        "PDF DUPLICATE REGISTRY",
    ]

    print()
    print("=" * 90)
    print("GLOBAL / RECOVERY FILES")
    print("=" * 90)

    for category in special_categories:

        files = categories.get(category, [])

        for path in files:

            data = loaded.get(path.name)

            if data is None:
                continue

            inspect_special(path.name, data)

    # --------------------------------------------------------
    # OTHER JSON
    # --------------------------------------------------------

    other_files = categories.get("OTHER JSON", [])

    print()
    print("=" * 90)
    print("OTHER JSON FILES")
    print("=" * 90)

    for path in other_files:

        data = loaded.get(path.name)

        if data is None:
            continue

        print()
        print(f"  {path.name}")
        print(f"     Structure : {describe_structure(data)}")

        if isinstance(data, list):
            print(f"     Records   : {len(data)}")

        elif isinstance(data, dict):
            print(f"     Keys      : {len(data)}")

    # --------------------------------------------------------
    # IMPORTANT COMPARISON
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print("IMPORTANT KNOWLEDGE-BASE COMPARISON")
    print("=" * 90)

    global_chunks_path = "_pdf_knowledge_chunks.json"

    recovered_chunks_path = "_pdf_recovered_native_chunks.json"

    global_data = loaded.get(global_chunks_path)
    recovered_data = loaded.get(recovered_chunks_path)

    global_count = (
        len(global_data)
        if isinstance(global_data, list)
        else 0
    )

    recovered_count = (
        len(recovered_data)
        if isinstance(recovered_data, list)
        else 0
    )

    print()
    print(f"_pdf_knowledge_chunks.json")
    print(f"   Current chunks : {global_count}")

    print()
    print(f"_pdf_recovered_native_chunks.json")
    print(f"   Recovered chunks: {recovered_count}")

    print()
    print("These are currently SEPARATE.")

    print()
    print(
        "Per-PDF knowledge files are also separate and should NOT "
        "automatically be merged with recovered chunks."
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print("FINAL SUMMARY")
    print("=" * 90)

    print()
    print(f"Total JSON files       : {len(json_files)}")
    print(f"Successfully loaded    : {len(loaded)}")
    print(f"Load errors            : {len(errors)}")
    print(f"Per-PDF knowledge JSONs: {len(per_pdf_files)}")
    print(f"Per-PDF pages          : {total_pdf_pages}")
    print(f"Per-PDF chunks         : {total_pdf_chunks}")
    print(f"Per-PDF skipped pages  : {total_pdf_skipped}")
    print(f"Global chunks          : {global_count}")
    print(f"Recovered chunks       : {recovered_count}")

    print()
    print("=" * 90)
    print("INSPECTION COMPLETE")
    print("=" * 90)

    print()
    print("READ-ONLY:")
    print("No JSON file was modified.")


if __name__ == "__main__":
    main()