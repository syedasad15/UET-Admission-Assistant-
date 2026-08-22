from pathlib import Path
import json
from collections import Counter


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

ORIGINAL_FILE = BASE_DIR / "_pdf_knowledge_chunks.json"
RECOVERED_FILE = BASE_DIR / "_pdf_recovered_native_chunks.json"
FINAL_FILE = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final.json"

AUDIT_JSON = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final_deep_audit.json"
AUDIT_TXT = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final_deep_audit.txt"


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


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_chunks(data, label):
    """
    Safely extract chunk list from different JSON structures.
    """

    if isinstance(data, list):
        if all(isinstance(x, dict) for x in data):
            return data

        raise ValueError(
            f"{label}: JSON is a list but not a list of objects."
        )

    if isinstance(data, dict):

        # Common direct chunk containers
        for key in [
            "chunks",
            "records",
            "data",
            "items",
        ]:
            value = data.get(key)

            if isinstance(value, list):
                if all(isinstance(x, dict) for x in value):
                    return value

        # Special recovery structure
        # {description, total_chunks, chunks}
        if isinstance(data.get("chunks"), list):
            return [
                x for x in data["chunks"]
                if isinstance(x, dict)
            ]

        raise ValueError(
            f"{label}: Could not find a list of chunk objects."
        )

    raise ValueError(
        f"{label}: Unsupported JSON root type: {type(data).__name__}"
    )


def chunk_key(x):
    return (
        x.get("pdf_file"),
        x.get("page"),
        x.get("chunk_index"),
    )


def page_key(x):
    return (
        x.get("pdf_file"),
        x.get("page"),
    )


def safe_text(x):
    value = x.get("text")
    if value is None:
        return ""
    return str(value)


def audit_required_fields(chunks):
    missing = []

    for i, x in enumerate(chunks):
        fields = [
            field for field in REQUIRED_FIELDS
            if field not in x
            or x.get(field) is None
        ]

        if fields:
            missing.append({
                "index": i,
                "pdf_file": x.get("pdf_file"),
                "page": x.get("page"),
                "chunk_index": x.get("chunk_index"),
                "missing": fields,
            })

    return missing


def count_duplicates(keys):
    counts = Counter(keys)
    return sum(
        count - 1
        for count in counts.values()
        if count > 1
    )


def unique_pages(chunks):
    return {
        page_key(x)
        for x in chunks
    }


def compare_original_text(original, final):
    final_map = {
        chunk_key(x): safe_text(x)
        for x in final
    }

    changed = []

    for i, x in enumerate(original):
        key = chunk_key(x)

        if key not in final_map:
            changed.append({
                "index": i,
                "key": key,
                "problem": "missing_from_final",
            })
            continue

        if safe_text(x) != final_map[key]:
            changed.append({
                "index": i,
                "key": key,
                "problem": "text_changed",
            })

    return changed


def main():

    print("=" * 90)
    print("FINAL DEEP AUDIT — 73 PAGE RECOVERY MERGED KNOWLEDGE BASE")
    print("=" * 90)

    print()
    print("Base directory:")
    print(BASE_DIR)

    print()
    print("Original:")
    print(ORIGINAL_FILE)

    print()
    print("Recovered:")
    print(RECOVERED_FILE)

    print()
    print("Final:")
    print(FINAL_FILE)

    print()
    print("=" * 90)
    print("READ-ONLY MODE")
    print("=" * 90)
    print("No source JSON will be modified.")

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------

    original_raw = load_json(ORIGINAL_FILE)
    recovered_raw = load_json(RECOVERED_FILE)
    final_raw = load_json(FINAL_FILE)

    original = normalize_chunks(
        original_raw,
        "Original"
    )

    recovered = normalize_chunks(
        recovered_raw,
        "Recovered"
    )

    final = normalize_chunks(
        final_raw,
        "Final"
    )

    # ---------------------------------------------------------
    # STRUCTURE REPORT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("0. STRUCTURE AUDIT")
    print("=" * 90)

    print(
        f"Original root type  : "
        f"{type(original_raw).__name__}"
    )

    print(
        f"Recovered root type : "
        f"{type(recovered_raw).__name__}"
    )

    print(
        f"Final root type     : "
        f"{type(final_raw).__name__}"
    )

    print(
        f"Original chunks     : {len(original)}"
    )

    print(
        f"Recovered chunks    : {len(recovered)}"
    )

    print(
        f"Final chunks        : {len(final)}"
    )

    # ---------------------------------------------------------
    # COUNT AUDIT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("1. COUNT AUDIT")
    print("=" * 90)

    original_count = len(original)
    recovered_count = len(recovered)
    final_count = len(final)

    expected_final = original_count + recovered_count

    print(f"Original chunks  : {original_count}")
    print(f"Recovered chunks : {recovered_count}")
    print(f"Final chunks     : {final_count}")

    print()
    print(
        f"Formula: {original_count} + "
        f"{recovered_count} = {expected_final}"
    )

    count_ok = final_count == expected_final

    if count_ok:
        print("[OK] Count formula is correct.")
    else:
        print("[FAIL] Count formula incorrect.")

    # ---------------------------------------------------------
    # CHUNK IDENTITY
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("2. CHUNK IDENTITY / DUPLICATE AUDIT")
    print("=" * 90)

    original_keys = [chunk_key(x) for x in original]
    recovered_keys = [chunk_key(x) for x in recovered]
    final_keys = [chunk_key(x) for x in final]

    duplicate_original = count_duplicates(original_keys)
    duplicate_recovered = count_duplicates(recovered_keys)
    duplicate_final = count_duplicates(final_keys)

    original_set = set(original_keys)
    recovered_set = set(recovered_keys)
    final_set = set(final_keys)

    cross_duplicates = original_set.intersection(
        recovered_set
    )

    print(
        f"Duplicate original keys   : "
        f"{duplicate_original}"
    )

    print(
        f"Duplicate recovered keys  : "
        f"{duplicate_recovered}"
    )

    print(
        f"Duplicate final keys      : "
        f"{duplicate_final}"
    )

    print(
        f"Cross original/recovered  : "
        f"{len(cross_duplicates)}"
    )

    duplicate_ok = (
        duplicate_original == 0
        and duplicate_recovered == 0
        and duplicate_final == 0
        and len(cross_duplicates) == 0
    )

    if duplicate_ok:
        print("[OK] No duplicate chunk keys.")
    else:
        print("[FAIL] Duplicate chunk keys detected.")

    # ---------------------------------------------------------
    # PAGE AUDIT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("3. PAGE AUDIT")
    print("=" * 90)

    original_pages = unique_pages(original)
    recovered_pages = unique_pages(recovered)
    final_pages = unique_pages(final)

    overlapping_pages = original_pages.intersection(
        recovered_pages
    )

    newly_added_pages = recovered_pages - original_pages

    print(
        f"Original unique pages : "
        f"{len(original_pages)}"
    )

    print(
        f"Recovered unique pages: "
        f"{len(recovered_pages)}"
    )

    print(
        f"Final unique pages    : "
        f"{len(final_pages)}"
    )

    print(
        f"Overlapping pages     : "
        f"{len(overlapping_pages)}"
    )

    print(
        f"Newly added pages     : "
        f"{len(newly_added_pages)}"
    )

    page_ok = (
        len(recovered_pages) == 73
        and len(overlapping_pages) == 0
        and len(newly_added_pages) == 73
    )

    if page_ok:
        print("[OK] Exactly 73 new recovered pages.")
    else:
        print("[FAIL] Recovered page audit failed.")

    # ---------------------------------------------------------
    # REQUIRED FIELDS
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("4. REQUIRED FIELD AUDIT")
    print("=" * 90)

    original_missing = audit_required_fields(original)
    recovered_missing = audit_required_fields(recovered)
    final_missing = audit_required_fields(final)

    print(
        f"Original records with missing fields : "
        f"{len(original_missing)}"
    )

    print(
        f"Recovered records with missing fields: "
        f"{len(recovered_missing)}"
    )

    print(
        f"Final records with missing fields     : "
        f"{len(final_missing)}"
    )

    fields_ok = len(final_missing) == 0

    if fields_ok:
        print("[OK] All final records have required fields.")
    else:
        print("[FAIL] Final records have missing fields.")

        for item in final_missing[:20]:
            print(item)

    # ---------------------------------------------------------
    # EMPTY TEXT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("5. TEXT AUDIT")
    print("=" * 90)

    empty_original = [
        i for i, x in enumerate(original)
        if not safe_text(x).strip()
    ]

    empty_recovered = [
        i for i, x in enumerate(recovered)
        if not safe_text(x).strip()
    ]

    empty_final = [
        i for i, x in enumerate(final)
        if not safe_text(x).strip()
    ]

    print(
        f"Original empty text  : {len(empty_original)}"
    )

    print(
        f"Recovered empty text : {len(empty_recovered)}"
    )

    print(
        f"Final empty text     : {len(empty_final)}"
    )

    text_ok = len(empty_final) == 0

    if text_ok:
        print("[OK] No final records have empty text.")
    else:
        print("[FAIL] Empty text records detected.")

    # ---------------------------------------------------------
    # ORIGINAL PRESERVATION
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("6. ORIGINAL DATA PRESERVATION")
    print("=" * 90)

    changed_original = compare_original_text(
        original,
        final
    )

    original_missing_from_final = [
        key for key in original_set
        if key not in final_set
    ]

    print(
        f"Original records changed : "
        f"{len(changed_original)}"
    )

    print(
        f"Original records missing : "
        f"{len(original_missing_from_final)}"
    )

    preservation_ok = (
        len(changed_original) == 0
        and len(original_missing_from_final) == 0
    )

    if preservation_ok:
        print("[OK] All original records preserved.")
    else:
        print("[FAIL] Original data preservation failed.")

    # ---------------------------------------------------------
    # RECOVERED PRESENCE
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("7. RECOVERED DATA PRESENCE")
    print("=" * 90)

    recovered_missing_from_final = [
        key for key in recovered_set
        if key not in final_set
    ]

    print(
        f"Recovered records missing from final : "
        f"{len(recovered_missing_from_final)}"
    )

    recovered_ok = (
        len(recovered_missing_from_final) == 0
    )

    if recovered_ok:
        print(
            f"[OK] All {recovered_count} recovered "
            f"chunks are present."
        )
    else:
        print("[FAIL] Recovered chunks are missing.")

    # ---------------------------------------------------------
    # SOURCE AUDIT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("8. SOURCE / QUALITY AUDIT")
    print("=" * 90)

    source_counts = Counter(
        x.get("source")
        for x in final
    )

    quality_counts = Counter(
        x.get("quality_flag")
        for x in final
    )

    print("Sources:")

    for source, count in sorted(
        source_counts.items(),
        key=lambda x: str(x[0])
    ):
        print(
            f"   {str(source):30} : {count}"
        )

    print()
    print("Quality flags:")

    for quality, count in sorted(
        quality_counts.items(),
        key=lambda x: str(x[0])
    ):
        print(
            f"   {str(quality):30} : {count}"
        )

    recovered_final = [
        x for x in final
        if x.get("source") == "native_text_recovery"
    ]

    recovered_quality_ok = all(
        x.get("quality_flag") == "ok"
        for x in recovered_final
    )

    recovered_source_count_ok = (
        len(recovered_final) == recovered_count
    )

    source_quality_ok = (
        recovered_source_count_ok
        and recovered_quality_ok
    )

    if source_quality_ok:
        print(
            f"[OK] All {recovered_count} recovered chunks "
            f"are present as native_text_recovery/ok."
        )
    else:
        print(
            "[FAIL] Recovered source/quality audit failed."
        )

    # ---------------------------------------------------------
    # FINAL STATUS
    # ---------------------------------------------------------

    all_ok = all([
        count_ok,
        duplicate_ok,
        page_ok,
        fields_ok,
        text_ok,
        preservation_ok,
        recovered_ok,
        source_quality_ok,
    ])

    print()
    print("=" * 90)
    print("9. FINAL STATUS")
    print("=" * 90)

    if all_ok:
        status = "PASS"

        print()
        print("[OK] FINAL DEEP AUDIT PASSED")
        print()
        print(
            f"[OK] {original_count} original chunks preserved."
        )
        print(
            f"[OK] {recovered_count} recovered chunks present."
        )
        print(
            "[OK] 73 recovered pages present."
        )
        print(
            "[OK] All required metadata fields present."
        )
        print(
            "[OK] No duplicate chunk keys."
        )
        print(
            "[OK] No original text changed."
        )
        print(
            "[OK] Recovered quality flags are correct."
        )

    else:
        status = "FAIL"

        print()
        print("[FAIL] FINAL DEEP AUDIT FAILED")
        print()
        print("Review the failed sections above.")
        print(
            "DO NOT replace the original KB until "
            "the failure is understood."
        )

    # ---------------------------------------------------------
    # AUDIT OBJECT
    # ---------------------------------------------------------

    audit = {
        "status": status,

        "files": {
            "original": str(ORIGINAL_FILE),
            "recovered": str(RECOVERED_FILE),
            "final": str(FINAL_FILE),
        },

        "counts": {
            "original": original_count,
            "recovered": recovered_count,
            "final": final_count,
            "expected_final": expected_final,
            "formula_ok": count_ok,
        },

        "duplicates": {
            "original": duplicate_original,
            "recovered": duplicate_recovered,
            "final": duplicate_final,
            "cross_original_recovered": len(
                cross_duplicates
            ),
        },

        "pages": {
            "original": len(original_pages),
            "recovered": len(recovered_pages),
            "final": len(final_pages),
            "overlapping": len(overlapping_pages),
            "newly_added": len(newly_added_pages),
        },

        "required_fields": {
            "original_missing": len(original_missing),
            "recovered_missing": len(recovered_missing),
            "final_missing": len(final_missing),
        },

        "text": {
            "original_empty": len(empty_original),
            "recovered_empty": len(empty_recovered),
            "final_empty": len(empty_final),
        },

        "preservation": {
            "original_changed": len(changed_original),
            "original_missing_from_final": len(
                original_missing_from_final
            ),
        },

        "recovered_presence": {
            "missing_from_final": len(
                recovered_missing_from_final
            ),
        },

        "sources": dict(source_counts),
        "quality_flags": dict(quality_counts),

        "checks": {
            "count_formula": count_ok,
            "duplicates": duplicate_ok,
            "pages": page_ok,
            "required_fields": fields_ok,
            "text": text_ok,
            "original_preservation": preservation_ok,
            "recovered_presence": recovered_ok,
            "source_quality": source_quality_ok,
        },
    }

    # ---------------------------------------------------------
    # WRITE AUDIT
    # ---------------------------------------------------------

    with open(
        AUDIT_JSON,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            audit,
            f,
            indent=2,
            ensure_ascii=False
        )

    txt_lines = []

    txt_lines.append(
        "FINAL DEEP AUDIT — 73 PAGE RECOVERY MERGED KB"
    )
    txt_lines.append("=" * 70)
    txt_lines.append(
        f"Status: {status}"
    )
    txt_lines.append("")
    txt_lines.append(
        f"Original chunks : {original_count}"
    )
    txt_lines.append(
        f"Recovered chunks: {recovered_count}"
    )
    txt_lines.append(
        f"Final chunks    : {final_count}"
    )
    txt_lines.append(
        f"Expected final  : {expected_final}"
    )
    txt_lines.append("")
    txt_lines.append(
        f"Recovered pages : {len(recovered_pages)}"
    )
    txt_lines.append(
        f"Final pages     : {len(final_pages)}"
    )
    txt_lines.append("")
    txt_lines.append(
        f"Final missing fields: {len(final_missing)}"
    )
    txt_lines.append(
        f"Final empty text    : {len(empty_final)}"
    )
    txt_lines.append(
        f"Original changed    : {len(changed_original)}"
    )
    txt_lines.append(
        f"Recovered missing   : "
        f"{len(recovered_missing_from_final)}"
    )
    txt_lines.append("")
    txt_lines.append(
        "CHECKS"
    )
    txt_lines.append("-" * 70)

    for name, value in audit["checks"].items():
        txt_lines.append(
            f"{name:30} : "
            f"{'PASS' if value else 'FAIL'}"
        )

    with open(
        AUDIT_TXT,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(txt_lines))

    print()
    print("=" * 90)
    print("AUDIT OUTPUT")
    print("=" * 90)

    print()
    print("JSON:")
    print(AUDIT_JSON)

    print()
    print("TXT:")
    print(AUDIT_TXT)

    print()
    print("=" * 90)

    if all_ok:
        print("AUDIT COMPLETE — PASS")
    else:
        print("AUDIT COMPLETE — FAIL")

    print("=" * 90)


if __name__ == "__main__":
    main()