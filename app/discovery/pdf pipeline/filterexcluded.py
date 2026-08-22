"""
FILTER EXCLUDED DOCUMENTS FROM THE GLOBAL KNOWLEDGE CHUNKS FILE
-----------------------------------------------------------------

Purpose:
    Remove chunks belonging to documents that were manually confirmed
    as STALE (superseded by a current-cycle document) and explicitly
    marked EXCLUDE. This decision was made in review but never applied
    to any file -- _pdf_knowledge_chunks.json still contains 1736
    chunks (57%% of the file) from these 3 documents.

Excluded documents (confirmed via manual content review):
    43d0e9ac-...pdf  -- Postgraduate Prospectus, Spring 2026
                         (superseded by MS-2026-1, Fall 2026)
    1d111018-...pdf  -- Undergraduate Prospectus, Spring 2026
                         (superseded by UG-2026-1, Fall 2026)
    559fc79c-...pdf  -- Undergraduate Prospectus, Fall 2025
                         (superseded by UG-2026-1, Fall 2026)

IMPORTANT:
    - READ ONLY with respect to the input file.
    - _pdf_knowledge_chunks.json is NEVER modified here.
    - Output is a NEW file: _pdf_knowledge_chunks_filtered.json
    - A separate audit JSON + TXT report is also written.

Expected:
    Original chunks : 3020
    Removed chunks   : 1736
    Remaining chunks : 1284
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

INPUT_FILE = BASE_DIR / "_pdf_knowledge_chunks.json"

OUTPUT_FILE = BASE_DIR / "_pdf_knowledge_chunks_filtered.json"

AUDIT_JSON = BASE_DIR / "_pdf_knowledge_chunks_filtered_audit.json"
AUDIT_TXT = BASE_DIR / "_pdf_knowledge_chunks_filtered_audit.txt"


# ============================================================
# EXCLUDED DOCUMENTS (confirmed via manual content review)
# ============================================================

EXCLUDED_DOCUMENTS = {
    "344e04fc714a2c74e003101804d54cad3549f44b1e7e0f6ec9bf7e7238d84d32": {
        "pdf_file": "43d0e9ac-e1a7-49fe-9c91-a84383fa309a.pdf",
        "reason": (
            "Stale Postgraduate Prospectus (Spring 2026) -- "
            "superseded by MS-2026-1 (Fall 2026, current cycle)"
        ),
        "expected_removed": 431,
    },
    "2b46e0a809266e43f93c653891c477fb36496ccb0cd782ac7f85b3085265a2c8": {
        "pdf_file": "1d111018-7c33-455a-9aa0-662f7c30da9e.pdf",
        "reason": (
            "Stale Undergraduate Prospectus (Spring 2026) -- "
            "superseded by UG-2026-1 (Fall 2026, current cycle)"
        ),
        "expected_removed": 640,
    },
    "0dde331d92181e248bc69ea35125c0ccdfb569a7ebbf7908f354fcbbe924fd29": {
        "pdf_file": "559fc79c-04b2-4ead-81f2-d7f9af2601a9.pdf",
        "reason": (
            "Stale Undergraduate Prospectus (Fall 2025) -- "
            "superseded by UG-2026-1 (Fall 2026, current cycle)"
        ),
        "expected_removed": 665,
    },
}

EXPECTED_ORIGINAL = 3020
EXPECTED_REMOVED = 1736
EXPECTED_REMAINING = 1284

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

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def chunk_key(chunk):
    """Stable identity for a chunk, used to verify nothing outside
    the excluded set was altered."""
    return (
        chunk.get("sha256", ""),
        chunk.get("page"),
        chunk.get("chunk_index"),
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("FILTER EXCLUDED DOCUMENTS FROM GLOBAL KNOWLEDGE CHUNKS")
    print("=" * 70)

    print(f"\nReading: {INPUT_FILE}")
    original = load_json(INPUT_FILE)

    if not isinstance(original, list):
        raise ValueError("_pdf_knowledge_chunks.json is not a list.")

    print(f"Original chunks: {len(original)}")

    checks = {}

    # --------------------------------------------------------
    # Split into kept / removed
    # --------------------------------------------------------

    excluded_shas = set(EXCLUDED_DOCUMENTS.keys())

    kept = [c for c in original if c.get("sha256", "") not in excluded_shas]
    removed = [c for c in original if c.get("sha256", "") in excluded_shas]

    print(f"Kept: {len(kept)}")
    print(f"Removed: {len(removed)}")

    # --------------------------------------------------------
    # CHECK: count formula
    # --------------------------------------------------------

    checks["count_formula"] = (
        len(kept) + len(removed) == len(original)
    )

    # --------------------------------------------------------
    # CHECK: matches expected totals
    # --------------------------------------------------------

    checks["matches_expected_totals"] = (
        len(original) == EXPECTED_ORIGINAL
        and len(removed) == EXPECTED_REMOVED
        and len(kept) == EXPECTED_REMAINING
    )

    # --------------------------------------------------------
    # CHECK: per-document removed counts match expectation
    # --------------------------------------------------------

    removed_by_sha = Counter(c.get("sha256", "") for c in removed)

    per_doc_ok = True
    per_doc_detail = {}

    for sha, info in EXCLUDED_DOCUMENTS.items():
        actual = removed_by_sha.get(sha, 0)
        expected = info["expected_removed"]
        ok = actual == expected
        per_doc_ok = per_doc_ok and ok
        per_doc_detail[info["pdf_file"]] = {
            "expected": expected,
            "actual": actual,
            "ok": ok,
        }

    checks["per_document_counts"] = per_doc_ok

    # --------------------------------------------------------
    # CHECK: exhaustive removal -- no excluded sha256 remains in kept
    # --------------------------------------------------------

    checks["exhaustive_removal"] = not any(
        c.get("sha256", "") in excluded_shas for c in kept
    )

    # --------------------------------------------------------
    # CHECK: removed chunks' pdf_file matches expected pdf_file
    # (catches any sha256 collision / mislabeling)
    # --------------------------------------------------------

    cross_contamination = []

    for c in removed:
        sha = c.get("sha256", "")
        expected_pdf = EXCLUDED_DOCUMENTS.get(sha, {}).get("pdf_file", "")
        if c.get("pdf_file", "") != expected_pdf:
            cross_contamination.append(c)

    checks["no_cross_contamination"] = len(cross_contamination) == 0

    # --------------------------------------------------------
    # CHECK: required fields intact on every kept chunk
    # --------------------------------------------------------

    missing_fields = []

    for c in kept:
        for field in REQUIRED_FIELDS:
            if field not in c:
                missing_fields.append((chunk_key(c), field))

    checks["required_fields"] = len(missing_fields) == 0

    # --------------------------------------------------------
    # CHECK: every kept chunk is byte-identical to its original
    # (filtering must never alter surviving chunks)
    # --------------------------------------------------------

    original_by_key = {chunk_key(c): c for c in original}

    altered = []

    for c in kept:
        key = chunk_key(c)
        if original_by_key.get(key) != c:
            altered.append(key)

    checks["kept_chunks_unaltered"] = len(altered) == 0

    # --------------------------------------------------------
    # CHECK: no empty text in kept chunks
    # --------------------------------------------------------

    empty_text = [
        chunk_key(c) for c in kept if not str(c.get("text", "")).strip()
    ]

    checks["no_empty_text"] = len(empty_text) == 0

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    overall_pass = all(checks.values())

    # --------------------------------------------------------
    # Save filtered output (only if checks pass)
    # --------------------------------------------------------

    if overall_pass:
        save_json(OUTPUT_FILE, kept)
        print(f"\nSaved filtered file: {OUTPUT_FILE}")
    else:
        print(
            "\n[!] One or more checks FAILED -- filtered file was "
            "NOT written. See audit report."
        )

    # --------------------------------------------------------
    # Build audit report
    # --------------------------------------------------------

    remaining_by_pdf = Counter(c.get("pdf_file", "") for c in kept)

    audit = {
        "status": "PASS" if overall_pass else "FAIL",
        "input_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE) if overall_pass else None,
        "original_chunks": len(original),
        "removed_chunks": len(removed),
        "kept_chunks": len(kept),
        "expected": {
            "original": EXPECTED_ORIGINAL,
            "removed": EXPECTED_REMOVED,
            "remaining": EXPECTED_REMAINING,
        },
        "checks": checks,
        "per_document_removed_counts": per_doc_detail,
        "remaining_chunks_by_pdf": dict(
            sorted(remaining_by_pdf.items(), key=lambda x: -x[1])
        ),
        "cross_contamination_examples": [
            chunk_key(c) for c in cross_contamination[:10]
        ],
        "missing_fields_examples": missing_fields[:10],
        "altered_chunk_examples": altered[:10],
        "empty_text_examples": empty_text[:10],
    }

    save_json(AUDIT_JSON, audit)

    with AUDIT_TXT.open("w", encoding="utf-8") as f:
        f.write("FILTER EXCLUDED DOCUMENTS — AUDIT REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Status: {audit['status']}\n\n")
        f.write(f"Original chunks : {len(original)}\n")
        f.write(f"Removed chunks  : {len(removed)}\n")
        f.write(f"Kept chunks     : {len(kept)}\n")
        f.write(f"Expected kept   : {EXPECTED_REMAINING}\n\n")
        f.write("REMOVED BY DOCUMENT\n")
        f.write("-" * 70 + "\n")
        for pdf_file, detail in per_doc_detail.items():
            status = "OK" if detail["ok"] else "MISMATCH"
            f.write(
                f"{pdf_file}: expected={detail['expected']} "
                f"actual={detail['actual']} [{status}]\n"
            )
        f.write("\nCHECKS\n")
        f.write("-" * 70 + "\n")
        for name, result in checks.items():
            f.write(f"{name:<28}: {'PASS' if result else 'FAIL'}\n")
        f.write("\nREMAINING CHUNKS BY PDF\n")
        f.write("-" * 70 + "\n")
        for pdf_file, count in sorted(
            remaining_by_pdf.items(), key=lambda x: -x[1]
        ):
            f.write(f"{pdf_file}: {count}\n")

    print(f"Audit JSON: {AUDIT_JSON}")
    print(f"Audit TXT : {AUDIT_TXT}")

    print("\n" + "=" * 70)
    print("CHECKS")
    print("=" * 70)
    for name, result in checks.items():
        print(f"  {name:<28}: {'PASS' if result else 'FAIL'}")

    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")


if __name__ == "__main__":
    main()