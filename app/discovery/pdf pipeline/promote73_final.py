from pathlib import Path
from datetime import datetime
import json
import shutil
import os
import sys


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

ORIGINAL = BASE_DIR / "_pdf_knowledge_chunks.json"
FINAL = BASE_DIR / "_pdf_knowledge_chunks_73_merged_final.json"

# Backup created before replacement
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = BASE_DIR / f"_pdf_knowledge_chunks_backup_{timestamp}.json"

EXPECTED_ORIGINAL = 2866
EXPECTED_RECOVERED = 154
EXPECTED_FINAL = 3020
EXPECTED_RECOVERED_PAGES = 73


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(data, label):
    if isinstance(data, list):
        if not all(isinstance(x, dict) for x in data):
            raise ValueError(
                f"{label}: list contains non-object records."
            )
        return data

    if isinstance(data, dict):
        chunks = data.get("chunks")

        if isinstance(chunks, list):
            if not all(isinstance(x, dict) for x in chunks):
                raise ValueError(
                    f"{label}: chunks contains non-object records."
                )
            return chunks

    raise ValueError(
        f"{label}: unsupported JSON structure."
    )


def key(x):
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


def main():

    print("=" * 90)
    print("SAFE PROMOTION — 73 PAGE RECOVERY FINAL KB")
    print("=" * 90)

    print()
    print("Original:")
    print(ORIGINAL)

    print()
    print("Final:")
    print(FINAL)

    print()
    print("Backup:")
    print(BACKUP)

    print()
    print("=" * 90)
    print("SAFETY RULE")
    print("=" * 90)

    print("Original will NOT be touched until every validation passes.")
    print("A backup will be created before replacement.")
    print()

    # ---------------------------------------------------------
    # FILE EXISTENCE
    # ---------------------------------------------------------

    if not ORIGINAL.exists():
        print("[FAIL] Original KB does not exist.")
        sys.exit(1)

    if not FINAL.exists():
        print("[FAIL] Final KB does not exist.")
        sys.exit(1)

    print("[OK] Original KB exists.")
    print("[OK] Final KB exists.")

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------

    try:
        original_raw = load_json(ORIGINAL)
        final_raw = load_json(FINAL)
    except Exception as e:
        print()
        print("[FAIL] Could not load JSON.")
        print(e)
        sys.exit(1)

    try:
        original = normalize(
            original_raw,
            "Original"
        )

        final = normalize(
            final_raw,
            "Final"
        )

    except Exception as e:
        print()
        print("[FAIL] JSON structure validation failed.")
        print(e)
        sys.exit(1)

    # ---------------------------------------------------------
    # COUNT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("1. COUNT VALIDATION")
    print("=" * 90)

    original_count = len(original)
    final_count = len(final)

    print(f"Original chunks : {original_count}")
    print(f"Final chunks    : {final_count}")

    if original_count != EXPECTED_ORIGINAL:
        print(
            f"[FAIL] Original count expected "
            f"{EXPECTED_ORIGINAL}, got {original_count}"
        )
        sys.exit(1)

    if final_count != EXPECTED_FINAL:
        print(
            f"[FAIL] Final count expected "
            f"{EXPECTED_FINAL}, got {final_count}"
        )
        sys.exit(1)

    recovered_count = final_count - original_count

    if recovered_count != EXPECTED_RECOVERED:
        print(
            f"[FAIL] Recovered count expected "
            f"{EXPECTED_RECOVERED}, got {recovered_count}"
        )
        sys.exit(1)

    print(
        f"[OK] {original_count} + {recovered_count} "
        f"= {final_count}"
    )

    # ---------------------------------------------------------
    # DUPLICATES
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("2. DUPLICATE VALIDATION")
    print("=" * 90)

    original_keys = [key(x) for x in original]
    final_keys = [key(x) for x in final]

    original_set = set(original_keys)
    final_set = set(final_keys)

    original_duplicates = len(original_keys) - len(
        original_set
    )

    final_duplicates = len(final_keys) - len(
        final_set
    )

    cross_overlap = len(
        original_set.intersection(final_set)
    )

    print(
        f"Original duplicate keys : "
        f"{original_duplicates}"
    )

    print(
        f"Final duplicate keys    : "
        f"{final_duplicates}"
    )

    print(
        f"Original/final key overlap: "
        f"{cross_overlap}"
    )

    # IMPORTANT:
    # The final KB naturally contains the original records,
    # so overlap is expected and MUST equal original_count.

    if original_duplicates != 0:
        print("[FAIL] Original contains duplicate keys.")
        sys.exit(1)

    if final_duplicates != 0:
        print("[FAIL] Final KB contains duplicate keys.")
        sys.exit(1)

    if cross_overlap != EXPECTED_ORIGINAL:
        print(
            "[FAIL] Final KB does not contain exactly all "
            "original chunk keys."
        )
        sys.exit(1)

    print("[OK] No duplicate chunk keys.")

    # ---------------------------------------------------------
    # REQUIRED FIELDS
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("3. REQUIRED FIELD VALIDATION")
    print("=" * 90)

    required = [
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

    missing = []

    for i, record in enumerate(final):

        bad = [
            field
            for field in required
            if field not in record
            or record.get(field) is None
        ]

        if bad:
            missing.append({
                "index": i,
                "missing": bad,
            })

    print(
        f"Records with missing fields: "
        f"{len(missing)}"
    )

    if missing:
        print("[FAIL] Required fields missing.")

        for item in missing[:10]:
            print(item)

        sys.exit(1)

    print("[OK] All required fields present.")

    # ---------------------------------------------------------
    # EMPTY TEXT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("4. TEXT VALIDATION")
    print("=" * 90)

    empty_text = [
        i
        for i, record in enumerate(final)
        if not str(record.get("text", "")).strip()
    ]

    print(
        f"Empty text records: {len(empty_text)}"
    )

    if empty_text:
        print("[FAIL] Empty text detected.")
        sys.exit(1)

    print("[OK] No empty text records.")

    # ---------------------------------------------------------
    # RECOVERED PAGE VALIDATION
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("5. RECOVERED PAGE VALIDATION")
    print("=" * 90)

    original_pages = {
        page_key(x)
        for x in original
    }

    final_pages = {
        page_key(x)
        for x in final
    }

    new_pages = final_pages - original_pages

    print(
        f"Original unique pages : "
        f"{len(original_pages)}"
    )

    print(
        f"Final unique pages    : "
        f"{len(final_pages)}"
    )

    print(
        f"New pages              : "
        f"{len(new_pages)}"
    )

    if len(new_pages) != EXPECTED_RECOVERED_PAGES:
        print(
            f"[FAIL] Expected "
            f"{EXPECTED_RECOVERED_PAGES} new pages, "
            f"got {len(new_pages)}"
        )
        sys.exit(1)

    print("[OK] Exactly 73 recovered pages present.")

    # ---------------------------------------------------------
    # ORIGINAL TEXT PRESERVATION
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("6. ORIGINAL DATA PRESERVATION")
    print("=" * 90)

    final_map = {
        key(record): record
        for record in final
    }

    changed = 0
    missing_original = 0

    for record in original:

        k = key(record)

        if k not in final_map:
            missing_original += 1
            continue

        if str(
            final_map[k].get("text", "")
        ) != str(
            record.get("text", "")
        ):
            changed += 1

    print(
        f"Original records missing: "
        f"{missing_original}"
    )

    print(
        f"Original records changed: "
        f"{changed}"
    )

    if missing_original != 0:
        print("[FAIL] Original records missing.")
        sys.exit(1)

    if changed != 0:
        print("[FAIL] Original text changed.")
        sys.exit(1)

    print("[OK] All original records preserved.")

    # ---------------------------------------------------------
    # RECOVERED QUALITY
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("7. RECOVERED QUALITY VALIDATION")
    print("=" * 90)

    recovered_records = [
        record
        for record in final
        if record.get("source")
        == "native_text_recovery"
    ]

    print(
        f"native_text_recovery records: "
        f"{len(recovered_records)}"
    )

    if len(recovered_records) != EXPECTED_RECOVERED:
        print(
            f"[FAIL] Expected "
            f"{EXPECTED_RECOVERED} recovered records."
        )
        sys.exit(1)

    bad_quality = [
        i
        for i, record in enumerate(
            recovered_records
        )
        if record.get("quality_flag") != "ok"
    ]

    print(
        f"Recovered records not marked ok: "
        f"{len(bad_quality)}"
    )

    if bad_quality:
        print("[FAIL] Recovered quality validation failed.")
        sys.exit(1)

    print("[OK] All recovered records are quality_flag='ok'.")

    # ---------------------------------------------------------
    # ALL VALIDATIONS PASSED
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("ALL PRE-PROMOTION CHECKS PASSED")
    print("=" * 90)

    print()
    print(f"Original : {original_count}")
    print(f"Recovered: {recovered_count}")
    print(f"Final    : {final_count}")
    print(f"New pages: {len(new_pages)}")

    print()
    print("[OK] It is safe to create the backup.")

    # ---------------------------------------------------------
    # BACKUP
    # ---------------------------------------------------------

    try:
        shutil.copy2(
            ORIGINAL,
            BACKUP
        )
    except Exception as e:
        print()
        print("[FAIL] Backup creation failed.")
        print(e)
        print()
        print("ORIGINAL FILE WAS NOT MODIFIED.")
        sys.exit(1)

    print()
    print("=" * 90)
    print("8. BACKUP")
    print("=" * 90)

    print(
        f"[OK] Backup created:"
    )
    print(BACKUP)

    # Verify backup exists and is readable
    if not BACKUP.exists():
        print("[FAIL] Backup file does not exist.")
        print("ORIGINAL FILE WAS NOT MODIFIED.")
        sys.exit(1)

    try:
        backup_raw = load_json(BACKUP)
        backup = normalize(
            backup_raw,
            "Backup"
        )
    except Exception as e:
        print("[FAIL] Backup verification failed.")
        print(e)
        print("ORIGINAL FILE WAS NOT MODIFIED.")
        sys.exit(1)

    if len(backup) != EXPECTED_ORIGINAL:
        print(
            "[FAIL] Backup count does not match original."
        )
        print("ORIGINAL FILE WAS NOT MODIFIED.")
        sys.exit(1)

    print(
        "[OK] Backup verified with "
        f"{len(backup)} chunks."
    )

    # ---------------------------------------------------------
    # ATOMIC REPLACEMENT
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("9. PROMOTION")
    print("=" * 90)

    temp_target = BASE_DIR / (
        "_pdf_knowledge_chunks.__promotion_tmp.json"
    )

    try:

        # Copy final into temporary file first
        shutil.copy2(
            FINAL,
            temp_target
        )

        # Verify temporary copy
        temp_raw = load_json(temp_target)
        temp_chunks = normalize(
            temp_raw,
            "Temporary promotion file"
        )

        if len(temp_chunks) != EXPECTED_FINAL:
            raise ValueError(
                "Temporary promotion file has "
                "incorrect chunk count."
            )

        # Atomic replace on same filesystem
        os.replace(
            temp_target,
            ORIGINAL
        )

    except Exception as e:

        print()
        print("[FAIL] Promotion failed.")
        print(e)

        if temp_target.exists():
            try:
                temp_target.unlink()
            except Exception:
                pass

        print()
        print(
            "Original file was NOT intentionally "
            "replaced."
        )

        print(
            "Backup remains available at:"
        )
        print(BACKUP)

        sys.exit(1)

    # ---------------------------------------------------------
    # POST-PROMOTION VERIFICATION
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("10. POST-PROMOTION VERIFICATION")
    print("=" * 90)

    try:
        promoted_raw = load_json(ORIGINAL)
        promoted = normalize(
            promoted_raw,
            "Promoted KB"
        )
    except Exception as e:
        print("[FAIL] Could not read promoted KB.")
        print(e)
        print()
        print("BACKUP:")
        print(BACKUP)
        sys.exit(1)

    promoted_count = len(promoted)

    print(
        f"Promoted KB chunks: "
        f"{promoted_count}"
    )

    if promoted_count != EXPECTED_FINAL:
        print(
            "[FAIL] Promoted KB count is incorrect."
        )
        print()
        print("BACKUP:")
        print(BACKUP)
        sys.exit(1)

    promoted_keys = [
        key(x)
        for x in promoted
    ]

    promoted_duplicates = (
        len(promoted_keys)
        - len(set(promoted_keys))
    )

    if promoted_duplicates != 0:
        print(
            "[FAIL] Promoted KB has duplicate keys."
        )
        print()
        print("BACKUP:")
        print(BACKUP)
        sys.exit(1)

    print("[OK] Promoted KB verified.")

    # ---------------------------------------------------------
    # SUCCESS
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("PROMOTION COMPLETE")
    print("=" * 90)

    print()
    print("[OK] Production KB is now:")
    print(ORIGINAL)

    print()
    print("[OK] Backup is available at:")
    print(BACKUP)

    print()
    print("[OK] 2866 original chunks preserved.")
    print("[OK] 154 recovered chunks included.")
    print("[OK] 3020 total chunks verified.")
    print("[OK] 73 recovered pages included.")
    print("[OK] No duplicate keys.")
    print("[OK] Promotion successful.")

    print()
    print("=" * 90)
    print("SAFE PROMOTION SUCCESS")
    print("=" * 90)


if __name__ == "__main__":
    main()