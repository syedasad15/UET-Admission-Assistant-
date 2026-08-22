import json
import re
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(r"D:\UET Chatbot")
INVENTORY = ROOT / "data" / "inventory" / "admission"

PDF_DUPLICATES = INVENTORY / "_pdf_duplicates.json"
PDF_CHUNKS = INVENTORY / "_pdf_knowledge_chunks.json"
PDF_SKIP_SUMMARY = INVENTORY / "_pdf_extraction_skip_summary.json"

OUTPUT_REPORT = INVENTORY / "_pdf_knowledge_audit.json"
OUTPUT_ISSUES = INVENTORY / "_pdf_knowledge_issues.json"


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


def normalize_text(text):
    if not isinstance(text, str):
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def word_count(text):
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def url_like_lines(text):
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if (
            "http://" in line
            or "https://" in line
            or "www." in line
            or ".edu.pk" in line
        ):
            lines.append(line)

    return lines


def suspicious_text(text):
    """
    Heuristic only.
    Does not alter the text.
    """

    if not text:
        return ["empty_text"]

    issues = []

    wc = word_count(text)

    if wc < 5:
        issues.append("very_short")

    # Excessive replacement characters / OCR artifacts
    replacement_count = text.count("�")

    if replacement_count >= 2:
        issues.append("replacement_characters")

    # Excessive repeated punctuation
    if re.search(r"[^\w\s]{8,}", text, flags=re.UNICODE):
        issues.append("punctuation_noise")

    # Extremely high digit density
    chars = [c for c in text if not c.isspace()]

    if chars:
        digit_ratio = sum(c.isdigit() for c in chars) / len(chars)

        if digit_ratio > 0.65:
            issues.append("high_digit_ratio")

    return issues


# ============================================================
# LOAD INPUTS
# ============================================================

print("=" * 70)
print("UET PDF KNOWLEDGE AUDIT")
print("=" * 70)

duplicates_data = load_json(PDF_DUPLICATES)
chunks_data = load_json(PDF_CHUNKS)
skip_data = load_json(PDF_SKIP_SUMMARY)

print(f"\nInventory: {INVENTORY}")
print(f"Chunks file: {PDF_CHUNKS}")


# ============================================================
# EXTRACT CANONICAL PDF INFORMATION
# ============================================================

canonical_pdfs = []

if isinstance(duplicates_data, dict):

    # Common possible structures
    for key in (
        "canonical_pdfs",
        "canonical",
        "unique_pdfs",
        "pdfs",
        "files",
    ):
        value = duplicates_data.get(key)

        if isinstance(value, list):
            canonical_pdfs = value
            break

elif isinstance(duplicates_data, list):
    canonical_pdfs = duplicates_data


canonical_urls = set()
canonical_titles = set()
canonical_hashes = set()

for item in canonical_pdfs:

    if not isinstance(item, dict):
        continue

    url = item.get("canonical_url") or item.get("url")

    title = item.get("canonical_title") or item.get("title")

    sha = item.get("sha256")

    if url:
        canonical_urls.add(url)

    if title:
        canonical_titles.add(title)

    if sha:
        canonical_hashes.add(sha)


# ============================================================
# FIND CHUNKS
# ============================================================

if isinstance(chunks_data, dict):

    chunks = (
        chunks_data.get("chunks")
        or chunks_data.get("data")
        or chunks_data.get("items")
        or []
    )

elif isinstance(chunks_data, list):

    chunks = chunks_data

else:

    chunks = []


print(f"Canonical PDFs detected: {len(canonical_pdfs)}")
print(f"Chunks detected: {len(chunks)}")


# ============================================================
# BASIC CHUNK AUDIT
# ============================================================

issues = []

quality_counts = Counter()
source_counts = Counter()

pdf_chunk_counts = Counter()
page_chunk_counts = Counter()

text_lengths = []

missing_metadata = Counter()

duplicate_exact = Counter()

seen_text = {}


for index, chunk in enumerate(chunks):

    if not isinstance(chunk, dict):

        issues.append({
            "type": "invalid_chunk_record",
            "chunk_index": index,
            "detail": "Chunk is not an object"
        })

        continue


    text = normalize_text(chunk.get("text", ""))

    quality = chunk.get("quality_flag") or chunk.get("quality") or "unknown"

    source = chunk.get("source") or "unknown"

    quality_counts[quality] += 1
    source_counts[source] += 1

    text_lengths.append(len(text))


    # --------------------------------------------------------
    # Metadata checks
    # --------------------------------------------------------

    required_metadata = [
        "canonical_url",
        "canonical_title",
        "pdf_file",
        "page",
        "text",
    ]

    for field in required_metadata:

        value = chunk.get(field)

        if value is None or value == "":
            missing_metadata[field] += 1

            issues.append({
                "type": "missing_metadata",
                "chunk_index": index,
                "field": field
            })


    # --------------------------------------------------------
    # Empty / short text
    # --------------------------------------------------------

    if not text:

        issues.append({
            "type": "empty_text",
            "chunk_index": index
        })

    elif len(text) < 40:

        issues.append({
            "type": "very_short_text",
            "chunk_index": index,
            "length": len(text),
            "text_preview": text[:200]
        })


    # --------------------------------------------------------
    # Suspicious OCR
    # --------------------------------------------------------

    text_issues = suspicious_text(text)

    for problem in text_issues:

        issues.append({
            "type": "suspicious_text",
            "chunk_index": index,
            "problem": problem,
            "text_preview": text[:300]
        })


    # --------------------------------------------------------
    # Flagged URLs
    # --------------------------------------------------------

    flagged = chunk.get("flagged_lines")

    if flagged:

        issues.append({
            "type": "flagged_lines",
            "chunk_index": index,
            "flagged_lines": flagged
        })


    # --------------------------------------------------------
    # Per-PDF statistics
    # --------------------------------------------------------

    pdf_file = chunk.get("pdf_file") or "UNKNOWN"

    page = chunk.get("page")

    pdf_chunk_counts[pdf_file] += 1

    if page is not None:
        page_chunk_counts[(pdf_file, str(page))] += 1


    # --------------------------------------------------------
    # Exact duplicate detection
    # --------------------------------------------------------

    if text:

        if text in seen_text:

            duplicate_exact[text] += 1

        else:

            seen_text[text] = index


# ============================================================
# PDF PAGE LEVEL KNOWLEDGE FILE AUDIT
# ============================================================

page_files = sorted(
    INVENTORY.glob("_pdf_knowledge_*.json")
)

page_file_stats = []

for path in page_files:

    try:

        data = load_json(path)

        if isinstance(data, dict):

            pages = (
                data.get("pages")
                or data.get("page_knowledge")
                or data.get("records")
                or []
            )

        elif isinstance(data, list):

            pages = data

        else:

            pages = []


        page_file_stats.append({
            "file": path.name,
            "pages_detected": len(pages),
            "status": "ok"
        })

    except Exception as exc:

        page_file_stats.append({
            "file": path.name,
            "pages_detected": 0,
            "status": "error",
            "error": str(exc)
        })


# ============================================================
# SKIP AUDIT
# ============================================================

skip_records = []

if isinstance(skip_data, dict):

    skip_records = (
        skip_data.get("skipped_pages")
        or skip_data.get("pages")
        or skip_data.get("records")
        or []
    )

elif isinstance(skip_data, list):

    skip_records = skip_data


skip_reason_counts = Counter()

for item in skip_records:

    if not isinstance(item, dict):
        continue

    reason = (
        item.get("reason")
        or item.get("quality_flag")
        or item.get("status")
        or "unknown"
    )

    skip_reason_counts[reason] += 1


# ============================================================
# PDF DISTRIBUTION
# ============================================================

pdf_distribution = []

for pdf_file, count in sorted(
    pdf_chunk_counts.items(),
    key=lambda x: x[0].lower()
):

    pdf_distribution.append({
        "pdf_file": pdf_file,
        "chunks": count
    })


# ============================================================
# EXACT DUPLICATES
# ============================================================

duplicate_text_records = []

for text, count in duplicate_exact.items():

    duplicate_text_records.append({
        "occurrences": count + 1,
        "text_preview": text[:500]
    })

duplicate_text_records.sort(
    key=lambda x: x["occurrences"],
    reverse=True
)


# ============================================================
# STATISTICS
# ============================================================

if text_lengths:

    avg_length = sum(text_lengths) / len(text_lengths)

    min_length = min(text_lengths)

    max_length = max(text_lengths)

else:

    avg_length = 0
    min_length = 0
    max_length = 0


# ============================================================
# AUDIT STATUS
# ============================================================

critical_issue_types = {
    "invalid_chunk_record",
    "empty_text",
    "missing_metadata"
}

critical_issues = [
    item
    for item in issues
    if item.get("type") in critical_issue_types
]


if critical_issues:

    overall_status = "NEEDS_REPAIR"

elif duplicate_text_records:

    overall_status = "NEEDS_REVIEW"

else:

    overall_status = "PASS_WITH_HEURISTIC_REVIEW"


# ============================================================
# FINAL REPORT
# ============================================================

report = {

    "source": "UET Admissions Portal",

    "stage": "pdf_knowledge_audit",

    "status": overall_status,

    "input_files": {

        "canonical_pdf_registry": str(PDF_DUPLICATES),

        "combined_chunks": str(PDF_CHUNKS),

        "skip_summary": str(PDF_SKIP_SUMMARY)
    },

    "counts": {

        "canonical_pdfs": len(canonical_pdfs),

        "page_knowledge_files": len(page_files),

        "chunks": len(chunks),

        "skipped_pages": len(skip_records),

        "issues": len(issues),

        "critical_issues": len(critical_issues),

        "exact_duplicate_texts": len(duplicate_text_records)
    },

    "text_statistics": {

        "average_characters": round(avg_length, 2),

        "minimum_characters": min_length,

        "maximum_characters": max_length
    },

    "quality_distribution": dict(
        quality_counts
    ),

    "source_distribution": dict(
        source_counts
    ),

    "skip_reason_distribution": dict(
        skip_reason_counts
    ),

    "missing_metadata": dict(
        missing_metadata
    ),

    "pdf_chunk_distribution": pdf_distribution,

    "page_file_audit": page_file_stats,

    "canonical_registry": {

        "urls": len(canonical_urls),

        "titles": len(canonical_titles),

        "sha256": len(canonical_hashes)
    },

    "recommendations": []
}


# ============================================================
# RECOMMENDATIONS
# ============================================================

if missing_metadata:

    report["recommendations"].append(
        "Repair missing required metadata before normalization."
    )

if duplicate_text_records:

    report["recommendations"].append(
        "Review exact duplicate chunks before embedding/indexing."
    )

if skip_records:

    report["recommendations"].append(
        "Audit skipped pages and classify Urdu/non-English, OCR failure, decorative, or important content."
    )

if any(
    item.get("type") == "flagged_lines"
    for item in issues
):

    report["recommendations"].append(
        "Review flagged URL-like lines manually; do not reconstruct URLs automatically."
    )

report["recommendations"].append(
    "Do not generate embeddings until this audit and skipped-page review are complete."
)

report["recommendations"].append(
    "Preserve raw PDF knowledge files as immutable extraction output."
)


# ============================================================
# SAVE
# ============================================================

save_json(
    OUTPUT_REPORT,
    report
)

save_json(
    OUTPUT_ISSUES,
    {
        "source": "UET Admissions Portal",
        "stage": "pdf_knowledge_audit_issues",
        "issue_count": len(issues),
        "issues": issues,
        "exact_duplicate_texts": duplicate_text_records
    }
)


# ============================================================
# CONSOLE SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AUDIT RESULT")
print("=" * 70)

print(f"Status:              {overall_status}")
print(f"Canonical PDFs:      {len(canonical_pdfs)}")
print(f"Page JSON files:     {len(page_files)}")
print(f"Chunks:              {len(chunks)}")
print(f"Skipped pages:      {len(skip_records)}")
print(f"Total issues:        {len(issues)}")
print(f"Critical issues:     {len(critical_issues)}")
print(f"Exact duplicate text:{len(duplicate_text_records)}")

print("\nQuality:")
for key, value in quality_counts.items():
    print(f"  {key}: {value}")

print("\nSources:")
for key, value in source_counts.items():
    print(f"  {key}: {value}")

print("\nSkip reasons:")
for key, value in skip_reason_counts.items():
    print(f"  {key}: {value}")

print("\nText length:")
print(f"  Average: {avg_length:.2f}")
print(f"  Minimum: {min_length}")
print(f"  Maximum: {max_length}")

print("\nOutput:")
print(f"  {OUTPUT_REPORT}")
print(f"  {OUTPUT_ISSUES}")

print("\n" + "=" * 70)
print("PDF audit complete.")
print("=" * 70)