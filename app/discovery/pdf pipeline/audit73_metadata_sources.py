"""
73 RECOVERED CHUNKS — METADATA SOURCE DISCOVERY AUDIT

Purpose:
    Find the correct document-level metadata for the 154 recovered chunks.

IMPORTANT:
    - READ ONLY
    - No JSON file is modified
    - Original global KB is not modified
    - Per-PDF knowledge files are not modified
    - Merged KB is not modified

Output:
    _pdf_73_metadata_discovery_audit.json
    _pdf_73_metadata_discovery_audit.txt
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")

RECOVERED_FILE = BASE_DIR / "_pdf_recovered_native_chunks.json"

OUTPUT_JSON = BASE_DIR / "_pdf_73_metadata_discovery_audit.json"
OUTPUT_TXT = BASE_DIR / "_pdf_73_metadata_discovery_audit.txt"


REQUIRED_FIELDS = [
    "canonical_url",
    "canonical_title",
    "sha256",
    "all_urls",
]


# ---------------------------------------------------------------------
# JSON HELPERS
# ---------------------------------------------------------------------

def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def iter_records(obj):
    """
    Recursively yield dictionaries that look like records.
    """

    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from iter_records(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from iter_records(item)


# ---------------------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------------------

def norm(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def pdf_name(value):
    value = norm(value)

    if not value:
        return ""

    return Path(value).name.lower()


def sha256_normalized(value):
    return norm(value).lower()


def looks_like_sha256(value):
    value = norm(value)

    return bool(
        re.fullmatch(r"[0-9a-fA-F]{64}", value)
    )


def score_metadata(record):
    """
    Score how useful a record is as document-level metadata.
    """

    score = 0

    if norm(record.get("canonical_url")):
        score += 1

    if norm(record.get("canonical_title")):
        score += 1

    if looks_like_sha256(record.get("sha256")):
        score += 2
    elif norm(record.get("sha256")):
        score += 1

    if record.get("all_urls"):
        score += 1

    if norm(record.get("pdf_file")):
        score += 2

    return score


# ---------------------------------------------------------------------
# METADATA EXTRACTION
# ---------------------------------------------------------------------

def extract_metadata(record):
    result = {}

    for field in REQUIRED_FIELDS:
        value = record.get(field)

        if value is not None and value != "":
            result[field] = value

    return result


def merge_metadata(target, source):
    """
    Fill missing metadata only.
    Never overwrite an already discovered value.
    """

    for field in REQUIRED_FIELDS:
        if field not in target or target[field] in ("", None, []):
            if field in source and source[field] not in ("", None, []):
                target[field] = source[field]


# ---------------------------------------------------------------------
# BUILD INDEX
# ---------------------------------------------------------------------

def build_indexes(json_files):
    by_pdf = defaultdict(list)
    by_sha256 = defaultdict(list)
    by_url = defaultdict(list)
    by_title = defaultdict(list)

    scanned_files = 0
    loaded_files = 0

    for path in json_files:

        # Never use our audit outputs as metadata sources.
        if path.name in {
            OUTPUT_JSON.name,
        }:
            continue

        data = load_json(path)

        scanned_files += 1

        if data is None:
            continue

        loaded_files += 1

        for record in iter_records(data):

            if not isinstance(record, dict):
                continue

            metadata = extract_metadata(record)

            if not metadata:
                continue

            # PDF
            p = pdf_name(record.get("pdf_file"))

            if p:
                by_pdf[p].append({
                    "file": path.name,
                    "metadata": metadata,
                    "score": score_metadata(record),
                })

            # SHA
            sha = sha256_normalized(record.get("sha256"))

            if sha:
                by_sha256[sha].append({
                    "file": path.name,
                    "metadata": metadata,
                    "score": score_metadata(record),
                })

            # URL
            url = norm(record.get("canonical_url"))

            if url:
                by_url[url].append({
                    "file": path.name,
                    "metadata": metadata,
                    "score": score_metadata(record),
                })

            # Title
            title = norm(record.get("canonical_title"))

            if title:
                by_title[title].append({
                    "file": path.name,
                    "metadata": metadata,
                    "score": score_metadata(record),
                })

    return {
        "by_pdf": by_pdf,
        "by_sha256": by_sha256,
        "by_url": by_url,
        "by_title": by_title,
        "scanned_files": scanned_files,
        "loaded_files": loaded_files,
    }


# ---------------------------------------------------------------------
# CANDIDATE COLLECTION
# ---------------------------------------------------------------------

def collect_candidates(chunk, indexes):

    candidates = []

    p = pdf_name(chunk.get("pdf_file"))

    if p:
        candidates.extend(indexes["by_pdf"].get(p, []))

    sha = sha256_normalized(chunk.get("sha256"))

    if sha:
        candidates.extend(indexes["by_sha256"].get(sha, []))

    url = norm(chunk.get("canonical_url"))

    if url:
        candidates.extend(indexes["by_url"].get(url, []))

    title = norm(chunk.get("canonical_title"))

    if title:
        candidates.extend(indexes["by_title"].get(title, []))

    # Deduplicate candidates.
    seen = set()
    unique = []

    for candidate in candidates:

        metadata = candidate["metadata"]

        key = (
            candidate["file"],
            tuple(
                (field, repr(metadata.get(field)))
                for field in REQUIRED_FIELDS
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    unique.sort(
        key=lambda x: x.get("score", 0),
        reverse=True
    )

    return unique


# ---------------------------------------------------------------------
# RESOLUTION
# ---------------------------------------------------------------------

def resolve_chunk(chunk, indexes):

    candidates = collect_candidates(chunk, indexes)

    resolved = {}

    sources = []

    for candidate in candidates:

        metadata = candidate["metadata"]

        before = dict(resolved)

        merge_metadata(resolved, metadata)

        if resolved != before:
            sources.append(candidate["file"])

        if all(
            field in resolved and
            resolved[field] not in ("", None, [])
            for field in REQUIRED_FIELDS
        ):
            break

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in resolved
        or resolved[field] in ("", None, [])
    ]

    return {
        "metadata": resolved,
        "missing": missing,
        "resolved": len(missing) == 0,
        "candidate_count": len(candidates),
        "candidate_files": sorted(set(
            c["file"] for c in candidates
        )),
        "sources_used": sorted(set(sources)),
    }


# ---------------------------------------------------------------------
# TEXT REPORT
# ---------------------------------------------------------------------

def write_txt(report):

    lines = []

    lines.append("=" * 100)
    lines.append("73 RECOVERED CHUNKS — METADATA SOURCE DISCOVERY AUDIT")
    lines.append("=" * 100)
    lines.append("")

    lines.append(f"Base directory : {BASE_DIR}")
    lines.append(f"Recovered file : {RECOVERED_FILE}")
    lines.append("")

    lines.append("=" * 100)
    lines.append("SUMMARY")
    lines.append("=" * 100)

    summary = report["summary"]

    for key, value in summary.items():
        lines.append(f"{key:35}: {value}")

    lines.append("")

    lines.append("=" * 100)
    lines.append("FIELD RESOLUTION")
    lines.append("=" * 100)

    for field, value in report["field_resolution"].items():
        lines.append(
            f"{field:35}: {value}"
        )

    lines.append("")

    lines.append("=" * 100)
    lines.append("SOURCE FILE FREQUENCY")
    lines.append("=" * 100)

    for source, count in sorted(
        report["source_file_frequency"].items(),
        key=lambda x: (-x[1], x[0])
    ):
        lines.append(
            f"{count:6}  {source}"
        )

    lines.append("")

    lines.append("=" * 100)
    lines.append("UNRESOLVED / PARTIAL RECORDS")
    lines.append("=" * 100)

    partial = [
        r for r in report["records"]
        if not r["resolved"]
    ]

    if not partial:
        lines.append("[NONE]")

    else:

        for r in partial:

            lines.append("")
            lines.append(
                f"Index       : {r['index']}"
            )
            lines.append(
                f"PDF         : {r['pdf_file']}"
            )
            lines.append(
                f"Page        : {r['page']}"
            )
            lines.append(
                f"Chunk       : {r['chunk_index']}"
            )
            lines.append(
                f"Missing     : {', '.join(r['missing'])}"
            )
            lines.append(
                f"Candidates  : {r['candidate_count']}"
            )

            if r["candidate_files"]:
                lines.append(
                    "Candidate files:"
                )

                for f in r["candidate_files"]:
                    lines.append(
                        f"   - {f}"
                    )

    lines.append("")

    lines.append("=" * 100)
    lines.append("RECOVERED RECORD DETAILS")
    lines.append("=" * 100)

    for r in report["records"]:

        lines.append("")
        lines.append(
            f"[{r['index']}] "
            f"{r['pdf_file']} "
            f"page={r['page']} "
            f"chunk={r['chunk_index']}"
        )

        lines.append(
            f"Resolved : {r['resolved']}"
        )

        lines.append(
            f"Missing  : {', '.join(r['missing']) if r['missing'] else 'NONE'}"
        )

        lines.append(
            f"Candidates: {r['candidate_count']}"
        )

        if r["sources_used"]:
            lines.append(
                "Sources:"
            )

            for source in r["sources_used"]:
                lines.append(
                    f"   - {source}"
                )

        metadata = r.get("metadata", {})

        for field in REQUIRED_FIELDS:

            value = metadata.get(field)

            if isinstance(value, list):
                value = f"list[{len(value)}]"

            elif value is None:
                value = "<MISSING>"

            lines.append(
                f"   {field}: {value}"
            )

    lines.append("")
    lines.append("=" * 100)
    lines.append("AUDIT COMPLETE")
    lines.append("=" * 100)
    lines.append("")
    lines.append("READ-ONLY: No JSON file was modified.")

    OUTPUT_TXT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    print("=" * 90)
    print("73 RECOVERED CHUNKS — METADATA SOURCE DISCOVERY AUDIT")
    print("=" * 90)
    print()

    print(f"Base directory:")
    print(BASE_DIR)
    print()

    print("Recovered file:")
    print(RECOVERED_FILE)
    print()

    print("=" * 90)
    print("IMPORTANT")
    print("=" * 90)
    print("READ ONLY")
    print("No JSON file will be modified.")
    print()

    if not RECOVERED_FILE.exists():
        raise FileNotFoundError(
            f"Recovered file not found:\n{RECOVERED_FILE}"
        )

    recovered_data = load_json(RECOVERED_FILE)

    if recovered_data is None:
        raise ValueError(
            "Could not load recovered JSON."
        )

    # Handle both:
    # list[records]
    # and {"chunks": [...]}
    if isinstance(recovered_data, list):
        recovered_chunks = recovered_data

    elif isinstance(recovered_data, dict):
        recovered_chunks = recovered_data.get(
            "chunks",
            []
        )

    else:
        raise ValueError(
            "Unexpected recovered JSON structure."
        )

    print("=" * 90)
    print("RECOVERED INPUT")
    print("=" * 90)

    print(
        f"Recovered chunks : {len(recovered_chunks)}"
    )

    if len(recovered_chunks) != 154:
        raise ValueError(
            f"Expected 154 recovered chunks, "
            f"found {len(recovered_chunks)}."
        )

    recovered_pages = sorted({
        (
            norm(chunk.get("pdf_file")),
            chunk.get("page"),
        )
        for chunk in recovered_chunks
    })

    print(
        f"Recovered pages  : {len(recovered_pages)}"
    )

    if len(recovered_pages) != 73:
        raise ValueError(
            f"Expected 73 recovered pages, "
            f"found {len(recovered_pages)}."
        )

    print()

    # ---------------------------------------------------------------
    # SCAN ALL JSONS
    # ---------------------------------------------------------------

    json_files = sorted(
        BASE_DIR.glob("*.json")
    )

    print("=" * 90)
    print("SCANNING JSON INVENTORY")
    print("=" * 90)

    print(
        f"JSON files found : {len(json_files)}"
    )

    indexes = build_indexes(json_files)

    print(
        f"Files scanned    : "
        f"{indexes['scanned_files']}"
    )

    print(
        f"Files loaded     : "
        f"{indexes['loaded_files']}"
    )

    print()

    # ---------------------------------------------------------------
    # RESOLVE
    # ---------------------------------------------------------------

    print("=" * 90)
    print("RECOVERED METADATA DISCOVERY")
    print("=" * 90)

    records = []

    field_resolution = {
        field: 0
        for field in REQUIRED_FIELDS
    }

    resolved_count = 0
    partial_count = 0
    unresolved_count = 0

    source_frequency = defaultdict(int)

    for index, chunk in enumerate(recovered_chunks):

        result = resolve_chunk(
            chunk,
            indexes
        )

        missing = result["missing"]

        for field in REQUIRED_FIELDS:

            if field not in missing:
                field_resolution[field] += 1

        if result["resolved"]:
            resolved_count += 1

        elif result["metadata"]:
            partial_count += 1

        else:
            unresolved_count += 1

        for source in result["sources_used"]:
            source_frequency[source] += 1

        records.append({
            "index": index,
            "pdf_file": chunk.get("pdf_file"),
            "page": chunk.get("page"),
            "chunk_index": chunk.get("chunk_index"),
            "resolved": result["resolved"],
            "missing": missing,
            "candidate_count": result["candidate_count"],
            "candidate_files": result["candidate_files"],
            "sources_used": result["sources_used"],
            "metadata": result["metadata"],
        })

    # ---------------------------------------------------------------
    # PRINT SUMMARY
    # ---------------------------------------------------------------

    print()
    print("=" * 90)
    print("RESULT")
    print("=" * 90)

    print(
        f"Recovered chunks       : {len(recovered_chunks)}"
    )

    print(
        f"Recovered pages        : {len(recovered_pages)}"
    )

    print(
        f"Fully resolved         : {resolved_count}"
    )

    print(
        f"Partially resolved     : {partial_count}"
    )

    print(
        f"Completely unresolved  : {unresolved_count}"
    )

    print()

    print("=" * 90)
    print("FIELD RESOLUTION")
    print("=" * 90)

    for field in REQUIRED_FIELDS:

        count = field_resolution[field]

        print(
            f"{field:25}: "
            f"{count} / {len(recovered_chunks)}"
        )

    print()

    print("=" * 90)
    print("SOURCE FILE FREQUENCY")
    print("=" * 90)

    if source_frequency:

        for source, count in sorted(
            source_frequency.items(),
            key=lambda x: (-x[1], x[0])
        ):
            print(
                f"{count:6}  {source}"
            )

    else:
        print("[NONE]")

    print()

    # ---------------------------------------------------------------
    # IMPORTANT DIAGNOSTIC
    # ---------------------------------------------------------------

    print("=" * 90)
    print("PARTIAL / UNRESOLVED SAMPLE")
    print("=" * 90)

    partial = [
        r for r in records
        if not r["resolved"]
    ]

    if not partial:

        print("[NONE]")

    else:

        for r in partial[:30]:

            print(
                f"index={r['index']} "
                f"pdf={r['pdf_file']} "
                f"page={r['page']} "
                f"chunk={r['chunk_index']}"
            )

            print(
                f"   missing: "
                f"{', '.join(r['missing'])}"
            )

            print(
                f"   candidates: "
                f"{r['candidate_count']}"
            )

            if r["candidate_files"]:

                print(
                    "   candidate files:"
                )

                for f in r["candidate_files"][:10]:
                    print(
                        f"      - {f}"
                    )

            print()

    # ---------------------------------------------------------------
    # SAVE REPORT
    # ---------------------------------------------------------------

    report = {
        "audit": {
            "name": "73 recovered chunks metadata source discovery",
            "read_only": True,
        },
        "input": {
            "recovered_file": str(
                RECOVERED_FILE
            ),
            "recovered_chunks": len(
                recovered_chunks
            ),
            "recovered_pages": len(
                recovered_pages
            ),
            "json_files_found": len(
                json_files
            ),
            "json_files_loaded": indexes[
                "loaded_files"
            ],
        },
        "summary": {
            "recovered_chunks": len(
                recovered_chunks
            ),
            "recovered_pages": len(
                recovered_pages
            ),
            "fully_resolved": resolved_count,
            "partially_resolved": partial_count,
            "completely_unresolved": unresolved_count,
        },
        "field_resolution": field_resolution,
        "source_file_frequency": dict(
            source_frequency
        ),
        "records": records,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    write_txt(report)

    print("=" * 90)
    print("OUTPUT")
    print("=" * 90)

    print()
    print("JSON audit:")
    print(OUTPUT_JSON)

    print()
    print("TXT audit:")
    print(OUTPUT_TXT)

    print()
    print("READ-ONLY:")
    print("No JSON file was modified.")

    print("=" * 90)
    print("AUDIT COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()