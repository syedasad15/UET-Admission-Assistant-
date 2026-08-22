from pathlib import Path
import json
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

EXISTING_FILE = BASE_DIR / "_pdf_knowledge_chunks.json"
RECOVERED_FILE = BASE_DIR / "_pdf_recovered_native_chunks.json"

OUTPUT_FILE = BASE_DIR / "_pdf_knowledge_chunks_73_merged.json"
AUDIT_FILE = BASE_DIR / "_pdf_knowledge_chunks_73_merge_audit.json"


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def chunk_key(chunk):
    """
    Identity of a chunk.

    pdf_file + page + chunk_index is used because chunk_index
    belongs to a specific page inside a specific PDF.
    """
    return (
        str(chunk.get("pdf_file", "")),
        int(chunk.get("page", -1)),
        int(chunk.get("chunk_index", -1)),
    )


def page_key(chunk):
    return (
        str(chunk.get("pdf_file", "")),
        int(chunk.get("page", -1)),
    )


def normalize_chunks(data, source_name):
    """
    Supports:
      - list of chunks
      - {"chunks": [...]}
    """

    if isinstance(data, list):
        chunks = data

    elif isinstance(data, dict) and isinstance(data.get("chunks"), list):
        chunks = data["chunks"]

    else:
        raise ValueError(
            f"{source_name} does not contain a supported chunk structure."
        )

    return chunks


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)
    print("73 RECOVERED CHUNKS SAFE MERGE / REPLACEMENT AUDIT")
    print("=" * 90)

    print()
    print(f"Base directory:")
    print(BASE_DIR)

    print()
    print("Existing global KB:")
    print(EXISTING_FILE)

    print()
    print("Recovered native chunks:")
    print(RECOVERED_FILE)

    print()
    print("IMPORTANT:")
    print("Original _pdf_knowledge_chunks.json will NOT be modified.")
    print("Per-PDF knowledge files will NOT be modified.")
    print()

    # --------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------

    if not EXISTING_FILE.exists():
        raise FileNotFoundError(
            f"Existing knowledge chunks file not found:\n{EXISTING_FILE}"
        )

    if not RECOVERED_FILE.exists():
        raise FileNotFoundError(
            f"Recovered native chunks file not found:\n{RECOVERED_FILE}"
        )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    existing_data = load_json(EXISTING_FILE)
    recovered_data = load_json(RECOVERED_FILE)

    existing_chunks = normalize_chunks(
        existing_data,
        EXISTING_FILE.name
    )

    recovered_chunks = normalize_chunks(
        recovered_data,
        RECOVERED_FILE.name
    )

    print("=" * 90)
    print("INPUT COUNTS")
    print("=" * 90)

    print(f"Existing chunks  : {len(existing_chunks)}")
    print(f"Recovered chunks : {len(recovered_chunks)}")

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    existing_keys = [chunk_key(c) for c in existing_chunks]
    recovered_keys = [chunk_key(c) for c in recovered_chunks]

    existing_key_set = set(existing_keys)

    duplicate_existing = [
        key for key, count in Counter(existing_keys).items()
        if count > 1
    ]

    duplicate_recovered = [
        key for key, count in Counter(recovered_keys).items()
        if count > 1
    ]

    print()
    print("=" * 90)
    print("CHUNK IDENTITY AUDIT")
    print("=" * 90)

    print(f"Duplicate existing chunk keys  : {len(duplicate_existing)}")
    print(f"Duplicate recovered chunk keys : {len(duplicate_recovered)}")

    # --------------------------------------------------------
    # GROUP BY PAGE
    # --------------------------------------------------------

    existing_by_page = defaultdict(list)
    recovered_by_page = defaultdict(list)

    for chunk in existing_chunks:
        existing_by_page[page_key(chunk)].append(chunk)

    for chunk in recovered_chunks:
        recovered_by_page[page_key(chunk)].append(chunk)

    recovered_pages = sorted(recovered_by_page.keys())

    existing_recovered_page_overlap = []
    new_pages = []

    for pkey in recovered_pages:
        if pkey in existing_by_page:
            existing_recovered_page_overlap.append(pkey)
        else:
            new_pages.append(pkey)

    # --------------------------------------------------------
    # PAGE-LEVEL ANALYSIS
    # --------------------------------------------------------

    replaced_pages = []
    added_pages = []
    unchanged_pages = []
    partial_overlap_pages = []

    page_details = []

    for pkey in recovered_pages:

        pdf_file, page = pkey

        old_chunks = existing_by_page.get(pkey, [])
        new_chunks = recovered_by_page[pkey]

        old_keys = {chunk_key(c) for c in old_chunks}
        new_keys = {chunk_key(c) for c in new_chunks}

        overlapping_chunk_keys = sorted(
            old_keys.intersection(new_keys)
        )

        if not old_chunks:
            action = "ADD_NEW_PAGE"
            added_pages.append(pkey)

        else:

            old_sources = Counter(
                str(c.get("source", ""))
                for c in old_chunks
            )

            old_quality = Counter(
                str(c.get("quality_flag", ""))
                for c in old_chunks
            )

            # If recovered chunks replace an existing page,
            # treat the entire page as replacement.
            action = "REPLACE_EXISTING_PAGE"
            replaced_pages.append(pkey)

            if overlapping_chunk_keys:
                partial_overlap_pages.append(pkey)

        page_details.append({
            "pdf_file": pdf_file,
            "page": page,
            "action": action,
            "existing_chunks": len(old_chunks),
            "recovered_chunks": len(new_chunks),
            "overlapping_chunk_keys": len(overlapping_chunk_keys),
        })

    # --------------------------------------------------------
    # BUILD MERGED RESULT
    # --------------------------------------------------------

    # Keep all existing chunks EXCEPT pages being recovered.
    replaced_page_set = set(replaced_pages)

    merged_chunks = []

    removed_existing_chunks = []

    for chunk in existing_chunks:

        pkey = page_key(chunk)

        if pkey in replaced_page_set:

            removed_existing_chunks.append(chunk)

        else:

            merged_chunks.append(chunk)

    # Add recovered chunks.
    merged_chunks.extend(recovered_chunks)

    # --------------------------------------------------------
    # FINAL DUPLICATE CHECK
    # --------------------------------------------------------

    final_keys = [chunk_key(c) for c in merged_chunks]

    final_key_counts = Counter(final_keys)

    final_duplicates = [
        {
            "key": list(key),
            "count": count
        }
        for key, count in final_key_counts.items()
        if count > 1
    ]

    # --------------------------------------------------------
    # PAGE COUNTS
    # --------------------------------------------------------

    final_pages = {
        page_key(chunk)
        for chunk in merged_chunks
    }

    existing_pages = {
        page_key(chunk)
        for chunk in existing_chunks
    }

    recovered_page_set = set(recovered_pages)

    # Expected:
    #
    # final chunks =
    # existing chunks
    # - old chunks from replaced pages
    # + recovered chunks
    #
    expected_final_count = (
        len(existing_chunks)
        - len(removed_existing_chunks)
        + len(recovered_chunks)
    )

    count_check = len(merged_chunks) == expected_final_count

    # --------------------------------------------------------
    # PDF SUMMARY
    # --------------------------------------------------------

    pdf_summary = defaultdict(lambda: {
        "recovered_pages": 0,
        "replaced_pages": 0,
        "added_pages": 0,
        "recovered_chunks": 0,
        "removed_existing_chunks": 0,
    })

    for pkey in recovered_pages:

        pdf_file, page = pkey

        info = pdf_summary[pdf_file]

        info["recovered_pages"] += 1

        recovered_count = len(recovered_by_page[pkey])
        info["recovered_chunks"] += recovered_count

        if pkey in replaced_page_set:
            info["replaced_pages"] += 1
            info["removed_existing_chunks"] += len(
                existing_by_page.get(pkey, [])
            )

        else:
            info["added_pages"] += 1

    # --------------------------------------------------------
    # SOURCE / QUALITY SUMMARY
    # --------------------------------------------------------

    existing_sources = Counter(
        str(c.get("source", ""))
        for c in existing_chunks
    )

    recovered_sources = Counter(
        str(c.get("source", ""))
        for c in recovered_chunks
    )

    final_sources = Counter(
        str(c.get("source", ""))
        for c in merged_chunks
    )

    existing_quality = Counter(
        str(c.get("quality_flag", ""))
        for c in existing_chunks
    )

    recovered_quality = Counter(
        str(c.get("quality_flag", ""))
        for c in recovered_chunks
    )

    final_quality = Counter(
        str(c.get("quality_flag", ""))
        for c in merged_chunks
    )

    # --------------------------------------------------------
    # SAVE MERGED OUTPUT
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        merged_chunks
    )

    # --------------------------------------------------------
    # AUDIT OBJECT
    # --------------------------------------------------------

    audit = {

        "audit": "73 recovered native chunks safe merge audit",

        "created_at": datetime.now().isoformat(),

        "policy": {
            "original_global_file_modified": False,
            "per_pdf_files_modified": False,
            "merge_mode": "page_level_replacement",
            "recovered_pages_replace_existing_page_chunks": True,
            "new_recovered_pages_are_added": True,
            "duplicate_chunks_allowed": False,
        },

        "input_files": {
            "existing_global_chunks": str(EXISTING_FILE),
            "recovered_native_chunks": str(RECOVERED_FILE),
        },

        "output_files": {
            "merged_chunks": str(OUTPUT_FILE),
            "audit": str(AUDIT_FILE),
        },

        "counts": {

            "existing_chunks": len(existing_chunks),

            "existing_pages": len(existing_pages),

            "recovered_chunks": len(recovered_chunks),

            "recovered_pages": len(recovered_pages),

            "replaced_pages": len(replaced_pages),

            "added_pages": len(added_pages),

            "removed_existing_chunks": len(
                removed_existing_chunks
            ),

            "final_chunks": len(merged_chunks),

            "final_pages": len(final_pages),

            "expected_final_chunks": expected_final_count,

            "final_duplicate_chunk_keys": len(
                final_duplicates
            ),
        },

        "validation": {

            "expected_recovered_pages_73":
                len(recovered_pages) == 73,

            "expected_recovered_chunks_154":
                len(recovered_chunks) == 154,

            "final_count_formula_ok":
                count_check,

            "no_final_duplicate_chunk_keys":
                len(final_duplicates) == 0,

            "all_recovered_pages_present":
                recovered_page_set.issubset(final_pages),

        },

        "source_counts": {

            "existing": dict(existing_sources),

            "recovered": dict(recovered_sources),

            "final": dict(final_sources),
        },

        "quality_counts": {

            "existing": dict(existing_quality),

            "recovered": dict(recovered_quality),

            "final": dict(final_quality),
        },

        "pdf_summary": dict(pdf_summary),

        "page_details": page_details,

        "duplicate_existing_keys": [
            list(key)
            for key in duplicate_existing
        ],

        "duplicate_recovered_keys": [
            list(key)
            for key in duplicate_recovered
        ],

        "final_duplicate_keys": final_duplicates,

    }

    save_json(
        AUDIT_FILE,
        audit
    )

    # --------------------------------------------------------
    # CONSOLE REPORT
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print("PAGE-LEVEL MERGE DECISION")
    print("=" * 90)

    print(f"Recovered pages          : {len(recovered_pages)}")
    print(f"Pages replacing old data: {len(replaced_pages)}")
    print(f"Pages newly added        : {len(added_pages)}")
    print(f"Old chunks removed       : {len(removed_existing_chunks)}")
    print(f"Recovered chunks added   : {len(recovered_chunks)}")

    print()
    print("=" * 90)
    print("FINAL RESULT")
    print("=" * 90)

    print(f"Existing chunks : {len(existing_chunks)}")
    print(f"Final chunks    : {len(merged_chunks)}")
    print(f"Expected        : {expected_final_count}")
    print(f"Final pages     : {len(final_pages)}")

    print()
    print("=" * 90)
    print("VALIDATION")
    print("=" * 90)

    if len(recovered_pages) == 73:
        print("[OK] Exactly 73 recovered pages detected.")
    else:
        print(
            f"[WARNING] Expected 73 recovered pages, "
            f"found {len(recovered_pages)}."
        )

    if len(recovered_chunks) == 154:
        print("[OK] Exactly 154 recovered chunks detected.")
    else:
        print(
            f"[WARNING] Expected 154 recovered chunks, "
            f"found {len(recovered_chunks)}."
        )

    if count_check:
        print("[OK] Final chunk count formula is correct.")
    else:
        print("[ERROR] Final chunk count formula mismatch.")

    if len(final_duplicates) == 0:
        print("[OK] No duplicate chunk keys in final output.")
    else:
        print(
            f"[ERROR] {len(final_duplicates)} duplicate "
            f"chunk keys found in final output."
        )

    if recovered_page_set.issubset(final_pages):
        print("[OK] All recovered pages exist in final output.")
    else:
        print("[ERROR] Some recovered pages are missing.")

    print()
    print("=" * 90)
    print("OUTPUT FILES")
    print("=" * 90)

    print()
    print("Merged chunks:")
    print(OUTPUT_FILE)

    print()
    print("Merge audit:")
    print(AUDIT_FILE)

    print()
    print("=" * 90)
    print("IMPORTANT")
    print("=" * 90)

    print("Original _pdf_knowledge_chunks.json was NOT modified.")
    print("Per-PDF _pdf_knowledge_*.json files were NOT modified.")
    print("This script created a completely separate merged file.")

    print()
    print("MERGE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()