"""
FINAL AUDIT FOR 73-PAGE MERGED KNOWLEDGE CHUNKS

READ-ONLY:
- Does NOT modify _pdf_knowledge_chunks.json
- Does NOT modify per-PDF knowledge files
- Does NOT modify _pdf_knowledge_chunks_73_merged.json
- Writes only a separate audit JSON + TXT report
"""

from pathlib import Path
import json
from collections import Counter, defaultdict


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

ORIGINAL_FILE = BASE_DIR / "_pdf_knowledge_chunks.json"
MERGED_FILE = BASE_DIR / "_pdf_knowledge_chunks_73_merged.json"
RECOVERED_FILE = BASE_DIR / "_pdf_recovered_native_chunks.json"

AUDIT_JSON = BASE_DIR / "_pdf_knowledge_chunks_73_merged_audit.json"
AUDIT_TXT = BASE_DIR / "_pdf_knowledge_chunks_73_merged_audit.txt"

EXPECTED_ORIGINAL = 2866
EXPECTED_RECOVERED = 154
EXPECTED_FINAL = 3020
EXPECTED_RECOVERED_PAGES = 73


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_chunks(data):
    """
    Supports:
      - list of chunks
      - {"chunks": [...]}
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("chunks"), list):
        return data["chunks"]

    raise ValueError(
        f"Unsupported JSON structure: {type(data).__name__}"
    )


def chunk_key(chunk):
    """
    Primary chunk identity.
    """
    return (
        str(chunk.get("pdf_file", "")),
        str(chunk.get("page", "")),
        str(chunk.get("chunk_index", "")),
    )


def content_key(chunk):
    """
    Strong content identity.
    """
    return (
        str(chunk.get("pdf_file", "")),
        str(chunk.get("page", "")),
        str(chunk.get("text", "")).strip(),
    )


def page_key(chunk):
    return (
        str(chunk.get("pdf_file", "")),
        str(chunk.get("page", "")),
    )


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def main():

    print("=" * 90)
    print("FINAL AUDIT — 73 PAGE MERGED KNOWLEDGE CHUNKS")
    print("=" * 90)

    print()
    print("Base directory:")
    print(BASE_DIR)

    print()
    print("Original:")
    print(ORIGINAL_FILE)

    print()
    print("Merged:")
    print(MERGED_FILE)

    print()
    print("Recovered:")
    print(RECOVERED_FILE)

    # ------------------------------------------------------------------
    # FILE CHECK
    # ------------------------------------------------------------------

    for path in [ORIGINAL_FILE, MERGED_FILE, RECOVERED_FILE]:

        if not path.exists():
            raise FileNotFoundError(
                f"Required file not found:\n{path}"
            )

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------

    original_data = load_json(ORIGINAL_FILE)
    merged_data = load_json(MERGED_FILE)
    recovered_data = load_json(RECOVERED_FILE)

    original = normalize_chunks(original_data)
    merged = normalize_chunks(merged_data)
    recovered = normalize_chunks(recovered_data)

    print()
    print("=" * 90)
    print("INPUT COUNTS")
    print("=" * 90)

    print(f"Original chunks  : {len(original)}")
    print(f"Recovered chunks : {len(recovered)}")
    print(f"Merged chunks    : {len(merged)}")

    # ------------------------------------------------------------------
    # BASIC COUNT CHECK
    # ------------------------------------------------------------------

    expected_formula = len(original) + len(recovered)

    count_ok = len(merged) == expected_formula

    print()
    print("Count formula:")
    print(
        f"{len(original)} + {len(recovered)} = "
        f"{expected_formula}"
    )

    print(
        "[OK] Count formula matches."
        if count_ok
        else "[FAIL] Count formula does NOT match."
    )

    # ------------------------------------------------------------------
    # CHUNK KEY DUPLICATES
    # ------------------------------------------------------------------

    original_keys = [chunk_key(c) for c in original]
    recovered_keys = [chunk_key(c) for c in recovered]
    merged_keys = [chunk_key(c) for c in merged]

    original_counter = Counter(original_keys)
    recovered_counter = Counter(recovered_keys)
    merged_counter = Counter(merged_keys)

    duplicate_original = {
        str(k): v
        for k, v in original_counter.items()
        if v > 1
    }

    duplicate_recovered = {
        str(k): v
        for k, v in recovered_counter.items()
        if v > 1
    }

    duplicate_merged = {
        str(k): v
        for k, v in merged_counter.items()
        if v > 1
    }

    # ------------------------------------------------------------------
    # CROSS DUPLICATES
    # ------------------------------------------------------------------

    original_key_set = set(original_keys)
    recovered_key_set = set(recovered_keys)

    cross_duplicate_keys = sorted(
        original_key_set.intersection(recovered_key_set)
    )

    # ------------------------------------------------------------------
    # PAGE ANALYSIS
    # ------------------------------------------------------------------

    original_pages = set(page_key(c) for c in original)
    recovered_pages = set(page_key(c) for c in recovered)
    merged_pages = set(page_key(c) for c in merged)

    newly_added_pages = recovered_pages - original_pages
    overlapping_pages = recovered_pages.intersection(original_pages)

    # ------------------------------------------------------------------
    # RECOVERED PAGE CHECK
    # ------------------------------------------------------------------

    recovered_page_count = len(recovered_pages)

    # ------------------------------------------------------------------
    # TEXT / METADATA VALIDATION
    # ------------------------------------------------------------------

    required_fields = [
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

    missing_field_records = []
    empty_text_records = []
    invalid_page_records = []
    invalid_chunk_index_records = []

    source_counter = Counter()
    quality_counter = Counter()
    pdf_counter = Counter()

    for i, chunk in enumerate(merged):

        if not isinstance(chunk, dict):
            missing_field_records.append({
                "index": i,
                "reason": "record_is_not_object",
            })
            continue

        missing = [
            field
            for field in required_fields
            if field not in chunk
        ]

        if missing:
            missing_field_records.append({
                "index": i,
                "pdf_file": chunk.get("pdf_file"),
                "page": chunk.get("page"),
                "missing": missing,
            })

        text = safe_text(chunk.get("text"))

        if not text:
            empty_text_records.append({
                "index": i,
                "pdf_file": chunk.get("pdf_file"),
                "page": chunk.get("page"),
                "chunk_index": chunk.get("chunk_index"),
            })

        try:
            page = int(chunk.get("page"))
            if page < 1:
                raise ValueError
        except Exception:
            invalid_page_records.append({
                "index": i,
                "pdf_file": chunk.get("pdf_file"),
                "page": chunk.get("page"),
            })

        try:
            chunk_index = int(chunk.get("chunk_index"))
            if chunk_index < 0:
                raise ValueError
        except Exception:
            invalid_chunk_index_records.append({
                "index": i,
                "pdf_file": chunk.get("pdf_file"),
                "chunk_index": chunk.get("chunk_index"),
            })

        source_counter[str(chunk.get("source", ""))] += 1
        quality_counter[str(chunk.get("quality_flag", ""))] += 1
        pdf_counter[str(chunk.get("pdf_file", ""))] += 1

    # ------------------------------------------------------------------
    # RECOVERED CONTENT PRESENCE
    # ------------------------------------------------------------------

    merged_key_set = set(merged_keys)

    recovered_missing_from_merged = sorted(
        recovered_key_set - merged_key_set
    )

    # ------------------------------------------------------------------
    # ORIGINAL CONTENT PRESENCE
    # ------------------------------------------------------------------

    original_missing_from_merged = sorted(
        original_key_set - merged_key_set
    )

    # ------------------------------------------------------------------
    # EXACT TEXT PRESERVATION FOR ORIGINAL CHUNKS
    # ------------------------------------------------------------------

    original_by_key = {
        chunk_key(c): c
        for c in original
    }

    merged_by_key = {
        chunk_key(c): c
        for c in merged
    }

    changed_original_chunks = []

    for key, original_chunk in original_by_key.items():

        merged_chunk = merged_by_key.get(key)

        if merged_chunk is None:
            continue

        original_text = safe_text(original_chunk.get("text"))
        merged_text = safe_text(merged_chunk.get("text"))

        if original_text != merged_text:

            changed_original_chunks.append({
                "key": key,
                "pdf_file": original_chunk.get("pdf_file"),
                "page": original_chunk.get("page"),
                "chunk_index": original_chunk.get("chunk_index"),
            })

    # ------------------------------------------------------------------
    # PER PDF
    # ------------------------------------------------------------------

    per_pdf = defaultdict(lambda: {
        "chunks": 0,
        "pages": set(),
    })

    for chunk in merged:

        pdf = str(chunk.get("pdf_file", ""))

        per_pdf[pdf]["chunks"] += 1
        per_pdf[pdf]["pages"].add(
            str(chunk.get("page", ""))
        )

    per_pdf_summary = {}

    for pdf, info in sorted(per_pdf.items()):

        per_pdf_summary[pdf] = {
            "chunks": info["chunks"],
            "pages": len(info["pages"]),
        }

    # ------------------------------------------------------------------
    # PRINT RESULTS
    # ------------------------------------------------------------------

    print()
    print("=" * 90)
    print("DUPLICATE AUDIT")
    print("=" * 90)

    print(
        f"Duplicate original keys  : "
        f"{len(duplicate_original)}"
    )

    print(
        f"Duplicate recovered keys : "
        f"{len(duplicate_recovered)}"
    )

    print(
        f"Duplicate merged keys    : "
        f"{len(duplicate_merged)}"
    )

    print(
        f"Cross original/recovered : "
        f"{len(cross_duplicate_keys)}"
    )

    print()
    print("=" * 90)
    print("PAGE AUDIT")
    print("=" * 90)

    print(f"Original unique pages     : {len(original_pages)}")
    print(f"Recovered unique pages    : {len(recovered_pages)}")
    print(f"Merged unique pages       : {len(merged_pages)}")
    print(f"Newly added pages         : {len(newly_added_pages)}")
    print(f"Overlapping pages         : {len(overlapping_pages)}")

    print()
    print("=" * 90)
    print("RECOVERED PAGE CHECK")
    print("=" * 90)

    print(f"Expected recovered pages  : {EXPECTED_RECOVERED_PAGES}")
    print(f"Actual recovered pages    : {recovered_page_count}")

    recovered_pages_ok = (
        recovered_page_count == EXPECTED_RECOVERED_PAGES
    )

    print(
        "[OK] Exactly 73 recovered pages."
        if recovered_pages_ok
        else "[FAIL] Recovered page count mismatch."
    )

    print()
    print("=" * 90)
    print("TEXT / METADATA AUDIT")
    print("=" * 90)

    print(
        f"Records with missing fields : "
        f"{len(missing_field_records)}"
    )

    print(
        f"Records with empty text     : "
        f"{len(empty_text_records)}"
    )

    print(
        f"Invalid page records        : "
        f"{len(invalid_page_records)}"
    )

    print(
        f"Invalid chunk_index records : "
        f"{len(invalid_chunk_index_records)}"
    )

    print()
    print("Sources:")
    for key, value in sorted(source_counter.items()):
        print(f"   {key}: {value}")

    print()
    print("Quality flags:")
    for key, value in sorted(quality_counter.items()):
        print(f"   {key}: {value}")

    # ------------------------------------------------------------------
    # PRESERVATION
    # ------------------------------------------------------------------

    print()
    print("=" * 90)
    print("ORIGINAL DATA PRESERVATION")
    print("=" * 90)

    print(
        f"Original chunks missing from merged : "
        f"{len(original_missing_from_merged)}"
    )

    print(
        f"Original chunks with changed text   : "
        f"{len(changed_original_chunks)}"
    )

    # ------------------------------------------------------------------
    # RECOVERED PRESENCE
    # ------------------------------------------------------------------

    print()
    print("=" * 90)
    print("RECOVERED DATA PRESENCE")
    print("=" * 90)

    print(
        f"Recovered chunks missing from merged : "
        f"{len(recovered_missing_from_merged)}"
    )

    # ------------------------------------------------------------------
    # FINAL VALIDATION
    # ------------------------------------------------------------------

    all_ok = True

    checks = {
        "original_count": len(original) == EXPECTED_ORIGINAL,
        "recovered_count": len(recovered) == EXPECTED_RECOVERED,
        "merged_count": len(merged) == EXPECTED_FINAL,
        "formula": count_ok,
        "no_duplicate_original": len(duplicate_original) == 0,
        "no_duplicate_recovered": len(duplicate_recovered) == 0,
        "no_duplicate_merged": len(duplicate_merged) == 0,
        "no_cross_duplicates": len(cross_duplicate_keys) == 0,
        "recovered_pages": recovered_page_count == EXPECTED_RECOVERED_PAGES,
        "all_recovered_present": len(recovered_missing_from_merged) == 0,
        "all_original_present": len(original_missing_from_merged) == 0,
        "original_text_unchanged": len(changed_original_chunks) == 0,
        "no_missing_fields": len(missing_field_records) == 0,
        "no_empty_text": len(empty_text_records) == 0,
        "valid_pages": len(invalid_page_records) == 0,
        "valid_chunk_indexes": len(invalid_chunk_index_records) == 0,
    }

    for name, result in checks.items():

        if result:
            print(f"[OK]   {name}")
        else:
            print(f"[FAIL] {name}")
            all_ok = False

    # ------------------------------------------------------------------
    # AUDIT OBJECT
    # ------------------------------------------------------------------

    audit = {
        "audit": {
            "name": "73_page_merged_knowledge_chunks_final_audit",
            "read_only": True,
        },

        "files": {
            "original": str(ORIGINAL_FILE),
            "recovered": str(RECOVERED_FILE),
            "merged": str(MERGED_FILE),
        },

        "expected": {
            "original_chunks": EXPECTED_ORIGINAL,
            "recovered_chunks": EXPECTED_RECOVERED,
            "final_chunks": EXPECTED_FINAL,
            "recovered_pages": EXPECTED_RECOVERED_PAGES,
        },

        "actual": {
            "original_chunks": len(original),
            "recovered_chunks": len(recovered),
            "merged_chunks": len(merged),
            "original_pages": len(original_pages),
            "recovered_pages": len(recovered_pages),
            "merged_pages": len(merged_pages),
            "newly_added_pages": len(newly_added_pages),
            "overlapping_pages": len(overlapping_pages),
        },

        "duplicates": {
            "original": duplicate_original,
            "recovered": duplicate_recovered,
            "merged": duplicate_merged,
            "cross_original_recovered": cross_duplicate_keys,
        },

        "missing": {
            "recovered_from_merged": recovered_missing_from_merged,
            "original_from_merged": original_missing_from_merged,
        },

        "integrity": {
            "missing_fields": missing_field_records,
            "empty_text": empty_text_records,
            "invalid_pages": invalid_page_records,
            "invalid_chunk_indexes": invalid_chunk_index_records,
            "changed_original_chunks": changed_original_chunks,
        },

        "sources": dict(source_counter),
        "quality_flags": dict(quality_counter),
        "per_pdf": per_pdf_summary,

        "checks": checks,
        "overall_status": "PASS" if all_ok else "FAIL",
    }

    # ------------------------------------------------------------------
    # WRITE AUDIT ONLY
    # ------------------------------------------------------------------

    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ------------------------------------------------------------------
    # TXT REPORT
    # ------------------------------------------------------------------

    lines = []

    lines.append("=" * 90)
    lines.append("FINAL AUDIT — 73 PAGE MERGED KNOWLEDGE CHUNKS")
    lines.append("=" * 90)
    lines.append("")

    lines.append(f"Original chunks : {len(original)}")
    lines.append(f"Recovered chunks: {len(recovered)}")
    lines.append(f"Merged chunks   : {len(merged)}")
    lines.append("")

    lines.append("PAGE COUNTS")
    lines.append("-" * 90)
    lines.append(f"Original pages      : {len(original_pages)}")
    lines.append(f"Recovered pages     : {len(recovered_pages)}")
    lines.append(f"Merged pages        : {len(merged_pages)}")
    lines.append(f"Newly added pages   : {len(newly_added_pages)}")
    lines.append(f"Overlapping pages   : {len(overlapping_pages)}")
    lines.append("")

    lines.append("DUPLICATES")
    lines.append("-" * 90)
    lines.append(
        f"Original duplicate keys  : {len(duplicate_original)}"
    )
    lines.append(
        f"Recovered duplicate keys : {len(duplicate_recovered)}"
    )
    lines.append(
        f"Merged duplicate keys    : {len(duplicate_merged)}"
    )
    lines.append(
        f"Cross duplicates         : {len(cross_duplicate_keys)}"
    )
    lines.append("")

    lines.append("INTEGRITY")
    lines.append("-" * 90)
    lines.append(
        f"Missing fields           : {len(missing_field_records)}"
    )
    lines.append(
        f"Empty text               : {len(empty_text_records)}"
    )
    lines.append(
        f"Invalid pages            : {len(invalid_page_records)}"
    )
    lines.append(
        f"Invalid chunk indexes    : {len(invalid_chunk_index_records)}"
    )
    lines.append(
        f"Changed original chunks  : {len(changed_original_chunks)}"
    )
    lines.append("")

    lines.append("VALIDATION")
    lines.append("-" * 90)

    for name, result in checks.items():
        lines.append(
            f"[{'OK' if result else 'FAIL'}] {name}"
        )

    lines.append("")
    lines.append(
        f"OVERALL STATUS: {'PASS' if all_ok else 'FAIL'}"
    )

    with open(AUDIT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------

    print()
    print("=" * 90)

    if all_ok:
        print("FINAL STATUS: PASS")
        print("=" * 90)
        print()
        print("3020 merged chunks passed all integrity checks.")
        print("73 recovered pages are present.")
        print("Original 2866 chunks are preserved.")
        print("No duplicate chunk keys detected.")
        print("No original chunk text was changed.")
    else:
        print("FINAL STATUS: FAIL")
        print("=" * 90)
        print()
        print("One or more integrity checks failed.")
        print("DO NOT use the merged file as final KB until reviewed.")

    print()
    print("Audit JSON:")
    print(AUDIT_JSON)

    print()
    print("Audit TXT:")
    print(AUDIT_TXT)

    print()
    print("IMPORTANT:")
    print("_pdf_knowledge_chunks.json was NOT modified.")
    print("Per-PDF knowledge files were NOT modified.")
    print("_pdf_knowledge_chunks_73_merged.json was NOT modified.")
    print("=" * 90)


if __name__ == "__main__":
    main()