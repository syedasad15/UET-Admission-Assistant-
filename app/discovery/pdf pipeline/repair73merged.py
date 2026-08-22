"""
FINAL 73-PAGE RECOVERY MERGE / METADATA REPAIR

Purpose:
    Merge the 154 recovered native-text chunks into the existing
    2866-chunk global knowledge base while restoring document-level
    metadata from the ORIGINAL global knowledge file.

IMPORTANT:
    - READ ONLY inputs
    - _pdf_knowledge_chunks.json is NEVER modified
    - Per-PDF knowledge files are NEVER modified
    - Existing merged files are NEVER modified
    - Output is a NEW file

Expected:
    Original chunks  : 2866
    Recovered chunks : 154
    Final chunks     : 3020
    Recovered pages  : 73
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

ORIGINAL_FILE = BASE_DIR / "_pdf_knowledge_chunks.json"
RECOVERED_FILE = BASE_DIR / "_pdf_recovered_native_chunks.json"

OUTPUT_FILE = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final.json"
AUDIT_JSON = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final_audit.json"
AUDIT_TXT = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final_audit.txt"

EXPECTED_ORIGINAL = 2866
EXPECTED_RECOVERED = 154
EXPECTED_FINAL = 3020
EXPECTED_RECOVERED_PAGES = 73

REQUIRED_FIELDS = [
    "canonical_url",
    "canonical_title",
    "sha256",
    "all_urls",
    "pdf_file",
    "page",
    "chunk_index",
    "text",
    "source",
    "quality_flag",
]


# ============================================================
# HELPERS
# ============================================================

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def norm(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def pdf_name(value):
    return Path(norm(value)).name.lower()


def chunk_key(record):
    return (
        pdf_name(record.get("pdf_file")),
        record.get("page"),
        record.get("chunk_index"),
    )


def page_key(record):
    return (
        pdf_name(record.get("pdf_file")),
        record.get("page"),
    )


def metadata_complete(record):
    return all(
        field in record
        and record[field] not in ("", None, [])
        for field in [
            "canonical_url",
            "canonical_title",
            "sha256",
            "all_urls",
        ]
    )


# ============================================================
# BUILD METADATA INDEX FROM ORIGINAL GLOBAL KB
# ============================================================

def build_metadata_index(original_chunks):

    by_pdf = defaultdict(list)
    by_sha256 = defaultdict(list)
    by_url = defaultdict(list)

    for record in original_chunks:

        p = pdf_name(record.get("pdf_file"))

        if p:
            by_pdf[p].append(record)

        sha = norm(record.get("sha256"))

        if sha:
            by_sha256[sha].append(record)

        url = norm(record.get("canonical_url"))

        if url:
            by_url[url].append(record)

    return {
        "by_pdf": by_pdf,
        "by_sha256": by_sha256,
        "by_url": by_url,
    }


def resolve_metadata(chunk, indexes):

    candidates = []

    p = pdf_name(chunk.get("pdf_file"))

    if p:
        candidates.extend(indexes["by_pdf"].get(p, []))

    sha = norm(chunk.get("sha256"))

    if sha:
        candidates.extend(indexes["by_sha256"].get(sha, []))

    url = norm(chunk.get("canonical_url"))

    if url:
        candidates.extend(indexes["by_url"].get(url, []))

    # Deduplicate candidate objects by identity.
    seen = set()
    unique = []

    for candidate in candidates:

        key = (
            norm(candidate.get("canonical_url")),
            norm(candidate.get("canonical_title")),
            norm(candidate.get("sha256")),
            repr(candidate.get("all_urls")),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    if not unique:
        return None

    # Prefer a candidate with all four required metadata fields.
    complete = [
        candidate
        for candidate in unique
        if metadata_complete(candidate)
    ]

    if complete:
        return complete[0]

    return unique[0]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)
    print("FINAL 73-PAGE RECOVERY MERGE / METADATA REPAIR")
    print("=" * 90)
    print()

    print("Original:")
    print(ORIGINAL_FILE)

    print()
    print("Recovered:")
    print(RECOVERED_FILE)

    print()
    print("Output:")
    print(OUTPUT_FILE)

    print()
    print("=" * 90)
    print("IMPORTANT")
    print("=" * 90)
    print("Original global KB will NOT be modified.")
    print("Per-PDF knowledge files will NOT be modified.")
    print("Existing merged files will NOT be modified.")
    print("A completely new output file will be created.")
    print()

    # --------------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------------

    if not ORIGINAL_FILE.exists():
        raise FileNotFoundError(
            f"Original KB not found:\n{ORIGINAL_FILE}"
        )

    if not RECOVERED_FILE.exists():
        raise FileNotFoundError(
            f"Recovered chunks not found:\n{RECOVERED_FILE}"
        )

    original = load_json(ORIGINAL_FILE)
    recovered_obj = load_json(RECOVERED_FILE)

    if not isinstance(original, list):
        raise ValueError(
            "Original _pdf_knowledge_chunks.json must be a list."
        )

    if isinstance(recovered_obj, dict):
        recovered = recovered_obj.get("chunks", [])
    elif isinstance(recovered_obj, list):
        recovered = recovered_obj
    else:
        raise ValueError(
            "Unexpected recovered chunks structure."
        )

    print("=" * 90)
    print("INPUT COUNTS")
    print("=" * 90)

    print(f"Original chunks  : {len(original)}")
    print(f"Recovered chunks : {len(recovered)}")

    if len(original) != EXPECTED_ORIGINAL:
        raise ValueError(
            f"Expected {EXPECTED_ORIGINAL} original chunks, "
            f"found {len(original)}."
        )

    if len(recovered) != EXPECTED_RECOVERED:
        raise ValueError(
            f"Expected {EXPECTED_RECOVERED} recovered chunks, "
            f"found {len(recovered)}."
        )

    print("[OK] Input counts are correct.")
    print()

    # --------------------------------------------------------
    # ORIGINAL CHUNK SNAPSHOT
    # --------------------------------------------------------

    original_snapshot = [
        (
            chunk_key(record),
            norm(record.get("text")),
        )
        for record in original
    ]

    original_keys = {
        chunk_key(record)
        for record in original
    }

    if len(original_keys) != len(original):
        raise ValueError(
            "Original KB contains duplicate chunk keys."
        )

    # --------------------------------------------------------
    # RECOVERED AUDIT
    # --------------------------------------------------------

    recovered_keys = [
        chunk_key(record)
        for record in recovered
    ]

    if len(set(recovered_keys)) != len(recovered_keys):
        duplicates = [
            key
            for key, count in
            __import__("collections").Counter(
                recovered_keys
            ).items()
            if count > 1
        ]

        raise ValueError(
            "Recovered chunks contain duplicate keys:\n"
            + repr(duplicates[:20])
        )

    recovered_pages = {
        page_key(record)
        for record in recovered
    }

    print("=" * 90)
    print("RECOVERED PAGE AUDIT")
    print("=" * 90)

    print(
        f"Recovered chunks : {len(recovered)}"
    )

    print(
        f"Recovered pages  : {len(recovered_pages)}"
    )

    if len(recovered_pages) != EXPECTED_RECOVERED_PAGES:
        raise ValueError(
            f"Expected {EXPECTED_RECOVERED_PAGES} recovered pages, "
            f"found {len(recovered_pages)}."
        )

    # Make sure these are actually new pages.
    overlapping_pages = recovered_pages & {
        page_key(record)
        for record in original
    }

    print(
        f"Overlapping pages: {len(overlapping_pages)}"
    )

    if overlapping_pages:
        print("[WARNING] Recovered pages overlap original pages.")
        print(
            "The script will STOP to prevent accidental replacement."
        )

        raise ValueError(
            "Recovered pages overlap original KB pages."
        )

    print("[OK] Exactly 73 new recovered pages.")
    print()

    # --------------------------------------------------------
    # METADATA INDEX
    # --------------------------------------------------------

    print("=" * 90)
    print("BUILDING METADATA INDEX")
    print("=" * 90)

    indexes = build_metadata_index(original)

    print(
        f"PDF metadata entries : "
        f"{len(indexes['by_pdf'])}"
    )

    print(
        f"SHA256 entries       : "
        f"{len(indexes['by_sha256'])}"
    )

    print(
        f"URL entries           : "
        f"{len(indexes['by_url'])}"
    )

    print()

    # --------------------------------------------------------
    # REBUILD RECOVERED RECORDS
    # --------------------------------------------------------

    print("=" * 90)
    print("REPAIRING RECOVERED RECORDS")
    print("=" * 90)

    repaired = []

    unresolved = []

    for index, recovered_record in enumerate(recovered):

        metadata = resolve_metadata(
            recovered_record,
            indexes,
        )

        if metadata is None:
            unresolved.append({
                "index": index,
                "pdf_file": recovered_record.get("pdf_file"),
                "page": recovered_record.get("page"),
                "chunk_index": recovered_record.get("chunk_index"),
            })
            continue

        record = dict(recovered_record)

        # ----------------------------------------------------
        # Copy ONLY document-level metadata from original KB.
        # ----------------------------------------------------

        record["canonical_url"] = metadata.get(
            "canonical_url"
        )

        record["canonical_title"] = metadata.get(
            "canonical_title"
        )

        record["sha256"] = metadata.get(
            "sha256"
        )

        record["all_urls"] = metadata.get(
            "all_urls"
        )

        # ----------------------------------------------------
        # Preserve recovered content identity.
        # ----------------------------------------------------

        record["pdf_file"] = recovered_record.get(
            "pdf_file"
        )

        record["page"] = recovered_record.get(
            "page"
        )

        record["chunk_index"] = recovered_record.get(
            "chunk_index"
        )

        record["text"] = recovered_record.get(
            "text"
        )

        # Recovered native extraction source.
        record["source"] = recovered_record.get(
            "source",
            "native_text_recovery",
        )

        # The recovered audit already established these pages
        # as valid native-text recovery pages.
        record["quality_flag"] = "ok"

        # Final required-field check.
        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in record
            or record[field] in ("", None, [])
        ]

        if missing:
            unresolved.append({
                "index": index,
                "pdf_file": record.get("pdf_file"),
                "page": record.get("page"),
                "chunk_index": record.get("chunk_index"),
                "missing": missing,
            })
            continue

        repaired.append(record)

    print(
        f"Recovered records processed : {len(recovered)}"
    )

    print(
        f"Successfully repaired       : {len(repaired)}"
    )

    print(
        f"Unresolved                   : {len(unresolved)}"
    )

    if unresolved:

        print()
        print("[FAIL] Some recovered records could not be repaired.")

        for item in unresolved[:30]:
            print(item)

        raise ValueError(
            "Metadata repair failed."
        )

    print("[OK] All 154 recovered records repaired.")
    print()

    # --------------------------------------------------------
    # BUILD FINAL
    # --------------------------------------------------------

    final_chunks = list(original) + repaired

    print("=" * 90)
    print("BUILDING FINAL OUTPUT")
    print("=" * 90)

    print(
        f"Original chunks : {len(original)}"
    )

    print(
        f"Recovered chunks: {len(repaired)}"
    )

    print(
        f"Final chunks    : {len(final_chunks)}"
    )

    if len(final_chunks) != EXPECTED_FINAL:
        raise ValueError(
            f"Expected final count {EXPECTED_FINAL}, "
            f"found {len(final_chunks)}."
        )

    # --------------------------------------------------------
    # FINAL DUPLICATE AUDIT
    # --------------------------------------------------------

    final_keys = [
        chunk_key(record)
        for record in final_chunks
    ]

    duplicate_final_keys = [
        key
        for key, count in
        __import__("collections").Counter(
            final_keys
        ).items()
        if count > 1
    ]

    print()
    print("=" * 90)
    print("FINAL DUPLICATE AUDIT")
    print("=" * 90)

    print(
        f"Duplicate final chunk keys : "
        f"{len(duplicate_final_keys)}"
    )

    if duplicate_final_keys:
        for key in duplicate_final_keys[:20]:
            print(key)

        raise ValueError(
            "Final output contains duplicate chunk keys."
        )

    print("[OK] No duplicate chunk keys.")
    print()

    # --------------------------------------------------------
    # REQUIRED FIELD AUDIT
    # --------------------------------------------------------

    missing_records = []

    for index, record in enumerate(final_chunks):

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in record
            or record[field] in ("", None, [])
        ]

        if missing:
            missing_records.append({
                "index": index,
                "pdf_file": record.get("pdf_file"),
                "page": record.get("page"),
                "chunk_index": record.get("chunk_index"),
                "missing": missing,
            })

    print("=" * 90)
    print("REQUIRED FIELD AUDIT")
    print("=" * 90)

    print(
        f"Records with missing fields : "
        f"{len(missing_records)}"
    )

    if missing_records:

        for item in missing_records[:30]:
            print(item)

        raise ValueError(
            "Final output has missing required fields."
        )

    print("[OK] All final records have required fields.")
    print()

    # --------------------------------------------------------
    # RECOVERED DATA PRESENCE
    # --------------------------------------------------------

    final_key_set = set(final_keys)

    missing_recovered = [
        key
        for key in recovered_keys
        if key not in final_key_set
    ]

    print("=" * 90)
    print("RECOVERED DATA PRESENCE")
    print("=" * 90)

    print(
        f"Recovered chunks missing : "
        f"{len(missing_recovered)}"
    )

    if missing_recovered:
        raise ValueError(
            "Some recovered chunks are missing from final output."
        )

    print("[OK] All 154 recovered chunks present.")
    print()

    # --------------------------------------------------------
    # ORIGINAL PRESERVATION
    # --------------------------------------------------------

    final_original_section = final_chunks[:len(original)]

    changed_original = []

    for index, (key, original_text) in enumerate(
        original_snapshot
    ):

        final_record = final_original_section[index]

        if chunk_key(final_record) != key:
            changed_original.append({
                "index": index,
                "expected_key": key,
                "actual_key": chunk_key(final_record),
            })
            continue

        if norm(final_record.get("text")) != original_text:
            changed_original.append({
                "index": index,
                "key": key,
                "reason": "text_changed",
            })

    print("=" * 90)
    print("ORIGINAL DATA PRESERVATION")
    print("=" * 90)

    print(
        f"Original records changed : "
        f"{len(changed_original)}"
    )

    if changed_original:
        for item in changed_original[:20]:
            print(item)

        raise ValueError(
            "Original records were changed."
        )

    print(
        "[OK] All 2866 original records preserved."
    )
    print()

    # --------------------------------------------------------
    # PAGE AUDIT
    # --------------------------------------------------------

    final_pages = {
        page_key(record)
        for record in final_chunks
    }

    original_pages = {
        page_key(record)
        for record in original
    }

    new_pages = final_pages - original_pages

    print("=" * 90)
    print("FINAL PAGE AUDIT")
    print("=" * 90)

    print(
        f"Original unique pages : "
        f"{len(original_pages)}"
    )

    print(
        f"Recovered pages       : "
        f"{len(recovered_pages)}"
    )

    print(
        f"Final unique pages    : "
        f"{len(final_pages)}"
    )

    print(
        f"Newly added pages     : "
        f"{len(new_pages)}"
    )

    if new_pages != recovered_pages:
        raise ValueError(
            "Final page set does not exactly match "
            "original + recovered pages."
        )

    print("[OK] Page sets are correct.")
    print()

    # --------------------------------------------------------
    # RECOVERED SOURCE / QUALITY
    # --------------------------------------------------------

    recovered_sources = defaultdict(int)
    recovered_quality = defaultdict(int)

    for record in repaired:

        recovered_sources[
            norm(record.get("source"))
        ] += 1

        recovered_quality[
            norm(record.get("quality_flag"))
        ] += 1

    print("=" * 90)
    print("RECOVERED RECORD QUALITY")
    print("=" * 90)

    print("Sources:")

    for source, count in sorted(
        recovered_sources.items()
    ):
        print(
            f"   {source}: {count}"
        )

    print()

    print("Quality flags:")

    for quality, count in sorted(
        recovered_quality.items()
    ):
        print(
            f"   {quality}: {count}"
        )

    if recovered_quality != {"ok": EXPECTED_RECOVERED}:
        raise ValueError(
            "Recovered quality flags are unexpected."
        )

    print()
    print("[OK] All recovered records marked quality_flag='ok'.")
    print()

    # --------------------------------------------------------
    # WRITE OUTPUT
    # --------------------------------------------------------

    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"Output already exists:\n{OUTPUT_FILE}\n\n"
            "Delete/rename it manually if you intentionally "
            "want to regenerate it."
        )

    save_json(
        OUTPUT_FILE,
        final_chunks,
    )

    # --------------------------------------------------------
    # POST-WRITE VERIFICATION
    # --------------------------------------------------------

    written = load_json(OUTPUT_FILE)

    if not isinstance(written, list):
        raise ValueError(
            "Written output is not a JSON list."
        )

    if len(written) != EXPECTED_FINAL:
        raise ValueError(
            "Written output count is incorrect."
        )

    written_keys = {
        chunk_key(record)
        for record in written
    }

    if len(written_keys) != EXPECTED_FINAL:
        raise ValueError(
            "Written output contains duplicate keys."
        )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    audit = {
        "status": "PASS",
        "read_only_inputs": True,
        "original_file_modified": False,
        "per_pdf_files_modified": False,
        "original_chunks": EXPECTED_ORIGINAL,
        "recovered_chunks": EXPECTED_RECOVERED,
        "final_chunks": len(written),
        "expected_final_chunks": EXPECTED_FINAL,
        "original_unique_pages": len(original_pages),
        "recovered_unique_pages": len(recovered_pages),
        "final_unique_pages": len(final_pages),
        "newly_added_pages": len(new_pages),
        "duplicate_final_keys": len(
            duplicate_final_keys
        ),
        "missing_required_fields": len(
            missing_records
        ),
        "unresolved_recovered_records": len(
            unresolved
        ),
        "recovered_sources": dict(
            recovered_sources
        ),
        "recovered_quality_flags": dict(
            recovered_quality
        ),
        "output_file": str(
            OUTPUT_FILE
        ),
    }

    save_json(
        AUDIT_JSON,
        audit,
    )

    txt_lines = [
        "=" * 90,
        "FINAL 73-PAGE MERGED KNOWLEDGE BASE AUDIT",
        "=" * 90,
        "",
        f"Original chunks          : {EXPECTED_ORIGINAL}",
        f"Recovered chunks         : {EXPECTED_RECOVERED}",
        f"Final chunks             : {len(written)}",
        f"Recovered pages          : {len(recovered_pages)}",
        f"Final unique pages       : {len(final_pages)}",
        f"Newly added pages        : {len(new_pages)}",
        f"Duplicate final keys     : {len(duplicate_final_keys)}",
        f"Missing required fields  : {len(missing_records)}",
        f"Unresolved records       : {len(unresolved)}",
        "",
        "Recovered sources:",
    ]

    for source, count in sorted(
        recovered_sources.items()
    ):
        txt_lines.append(
            f"   {source}: {count}"
        )

    txt_lines.extend([
        "",
        "Recovered quality flags:",
    ])

    for quality, count in sorted(
        recovered_quality.items()
    ):
        txt_lines.append(
            f"   {quality}: {count}"
        )

    txt_lines.extend([
        "",
        "STATUS: PASS",
        "",
        "Original _pdf_knowledge_chunks.json was NOT modified.",
        "Per-PDF knowledge files were NOT modified.",
        "Existing merged files were NOT modified.",
        "",
        f"Final output:",
        str(OUTPUT_FILE),
        "",
        f"Audit JSON:",
        str(AUDIT_JSON),
        "",
        f"Audit TXT:",
        str(AUDIT_TXT),
    ])

    AUDIT_TXT.write_text(
        "\n".join(txt_lines),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # FINAL SCREEN
    # --------------------------------------------------------

    print("=" * 90)
    print("FINAL RESULT")
    print("=" * 90)

    print(
        f"Original chunks : {EXPECTED_ORIGINAL}"
    )

    print(
        f"Recovered chunks: {EXPECTED_RECOVERED}"
    )

    print(
        f"Final chunks    : {len(written)}"
    )

    print(
        f"Final pages     : {len(final_pages)}"
    )

    print()
    print("[OK] 2866 original chunks preserved.")
    print("[OK] 154 recovered chunks added.")
    print("[OK] 73 recovered pages present.")
    print("[OK] Metadata resolved for all recovered chunks.")
    print("[OK] All required fields present.")
    print("[OK] No duplicate chunk keys.")
    print("[OK] No original text changed.")
    print("[OK] All recovered quality flags are 'ok'.")
    print()

    print("=" * 90)
    print("FINAL KB CREATED SUCCESSFULLY")
    print("=" * 90)

    print()
    print("Final KB:")
    print(OUTPUT_FILE)

    print()
    print("Audit JSON:")
    print(AUDIT_JSON)

    print()
    print("Audit TXT:")
    print(AUDIT_TXT)

    print()
    print("IMPORTANT:")
    print("Do NOT replace _pdf_knowledge_chunks.json yet.")
    print("Keep this final file separate until the final audit is reviewed.")

    print("=" * 90)


if __name__ == "__main__":
    main()