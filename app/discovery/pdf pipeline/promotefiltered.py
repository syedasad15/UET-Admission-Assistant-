"""
PROMOTE FILTERED KNOWLEDGE CHUNKS TO OFFICIAL
------------------------------------------------

Purpose:
    Replace the official _pdf_knowledge_chunks.json with the filtered
    version (stale/excluded documents removed), after taking a
    timestamped backup of the current official file first.

    Run filter_excluded.py BEFORE this script and confirm its audit
    report says PASS -- this script trusts that the filtered file is
    already verified correct and does no re-validation of content,
    only of counts.

IMPORTANT:
    - Requires _pdf_knowledge_chunks_filtered.json to exist (output
      of filter_excluded.py).
    - The current _pdf_knowledge_chunks.json is backed up BEFORE
      being overwritten -- nothing is lost.

Expected:
    Before (official) : 3020
    After  (official)  : 1284
"""

from pathlib import Path
from datetime import datetime
import json
import shutil
import sys


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

OFFICIAL = BASE_DIR / "_pdf_knowledge_chunks.json"
FILTERED = BASE_DIR / "_pdf_knowledge_chunks_filtered.json"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = BASE_DIR / f"_pdf_knowledge_chunks_backup_{timestamp}.json"

EXPECTED_BEFORE = 3020
EXPECTED_AFTER = 1284


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 70)
    print("PROMOTE FILTERED KNOWLEDGE CHUNKS TO OFFICIAL")
    print("=" * 70)

    if not OFFICIAL.exists():
        print(f"[!] Missing official file: {OFFICIAL}")
        sys.exit(1)

    if not FILTERED.exists():
        print(f"[!] Missing filtered file: {FILTERED}")
        print("    Run filter_excluded.py first.")
        sys.exit(1)

    official_data = load_json(OFFICIAL)
    filtered_data = load_json(FILTERED)

    print(f"\nCurrent official chunks : {len(official_data)}")
    print(f"Filtered chunks         : {len(filtered_data)}")

    if len(official_data) != EXPECTED_BEFORE:
        print(
            f"[!] WARNING: official file has {len(official_data)} "
            f"chunks, expected {EXPECTED_BEFORE}. "
            "Proceeding anyway, but double-check this is intended."
        )

    if len(filtered_data) != EXPECTED_AFTER:
        print(
            f"[!] WARNING: filtered file has {len(filtered_data)} "
            f"chunks, expected {EXPECTED_AFTER}. "
            "Proceeding anyway, but double-check this is intended."
        )

    # --------------------------------------------------------
    # Backup current official file
    # --------------------------------------------------------

    shutil.copy2(OFFICIAL, BACKUP)
    print(f"\nBackup created: {BACKUP}")

    if not BACKUP.exists():
        print("[!] Backup file was not created. Aborting.")
        sys.exit(1)

    backup_data = load_json(BACKUP)
    if len(backup_data) != len(official_data):
        print(
            "[!] Backup chunk count does not match original. "
            "Aborting before overwrite."
        )
        sys.exit(1)

    print("Backup verified.")

    # --------------------------------------------------------
    # Promote: overwrite official with filtered
    # --------------------------------------------------------

    with OFFICIAL.open("w", encoding="utf-8") as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)

    print(f"\nPromoted: {OFFICIAL} now has {len(filtered_data)} chunks.")

    # --------------------------------------------------------
    # Final verification: re-read from disk
    # --------------------------------------------------------

    verify_data = load_json(OFFICIAL)

    if len(verify_data) == len(filtered_data):
        print("\n[OK] Official file verified after write.")
    else:
        print(
            "\n[!] MISMATCH after write: "
            f"expected {len(filtered_data)}, got {len(verify_data)}. "
            f"Restore from backup if needed: {BACKUP}"
        )
        sys.exit(1)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"Backup   : {BACKUP}")
    print(f"Official : {OFFICIAL} ({len(verify_data)} chunks)")


if __name__ == "__main__":
    main()