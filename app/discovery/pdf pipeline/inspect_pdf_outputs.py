"""
UET CHATBOT — PDF OUTPUT INSPECTOR
----------------------------------

Reads and summarizes the existing PDF pipeline outputs:

1. _pdf_duplicates.json
2. _pdf_knowledge_<...>.json
3. _pdf_knowledge_chunks.json
4. _pdf_extraction_skip_summary.json

IMPORTANT:
- This script is READ-ONLY.
- It does NOT modify any existing JSON files.
- It does NOT run OCR.
- It does NOT regenerate chunks.
- It is intended only for inspection before designing
  the PDF inventory / classification / refinement stage.
"""

import json
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

DUPLICATES_FILE = DATA_DIR / "_pdf_duplicates.json"
CHUNKS_FILE = DATA_DIR / "_pdf_knowledge_chunks.json"
SKIP_FILE = DATA_DIR / "_pdf_extraction_skip_summary.json"


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    if not path.exists():
        print(f"\n[NOT FOUND] {path}")
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"\n[ERROR] Could not read {path}")
        print(f"        {e}")
        return None


def print_separator(title=None):
    print("\n" + "=" * 90)
    if title:
        print(title)
        print("=" * 90)


def short_text(value, max_len=180):
    if value is None:
        return ""

    value = str(value).replace("\n", " ").strip()

    if len(value) <= max_len:
        return value

    return value[:max_len] + "..."


# ============================================================
# 1. PDF DUPLICATES / CANONICAL REGISTRY
# ============================================================

def inspect_duplicates():
    print_separator("1. _pdf_duplicates.json — CANONICAL PDF REGISTRY")

    data = load_json(DUPLICATES_FILE)

    if data is None:
        return

    print("\nTop-level keys:")
    for key in data.keys():
        value = data[key]

        if isinstance(value, list):
            print(f"  {key}: list ({len(value)})")
        elif isinstance(value, dict):
            print(f"  {key}: dict ({len(value)})")
        else:
            print(f"  {key}: {type(value).__name__} = {value}")

    unique_documents = data.get("unique_documents", [])

    print(f"\nCanonical / unique documents: {len(unique_documents)}")

    if not unique_documents:
        return

    # Inspect schema across all documents
    all_keys = Counter()

    for doc in unique_documents:
        all_keys.update(doc.keys())

    print("\nDocument fields:")
    for key, count in all_keys.most_common():
        print(f"  {key}: present in {count}/{len(unique_documents)}")

    print("\nCanonical PDF summary:")

    for i, doc in enumerate(unique_documents, start=1):

        print(f"\n--- PDF {i}/{len(unique_documents)} ---")

        print(f"Title:       {doc.get('canonical_title', '')}")
        print(f"Filename:    {doc.get('canonical_local_filename', '')}")
        print(f"URL:         {doc.get('canonical_url', '')}")
        print(f"SHA256:      {doc.get('sha256', '')}")

        aliases = doc.get("aliases", [])

        print(f"Aliases:     {len(aliases)}")

        if aliases:
            for alias in aliases[:5]:
                if isinstance(alias, dict):
                    print(
                        f"  - {alias.get('url', '')}"
                    )
                else:
                    print(f"  - {alias}")

            if len(aliases) > 5:
                print(f"  ... +{len(aliases) - 5} more")

        # Print any additional fields we don't already know about
        known = {
            "canonical_title",
            "canonical_local_filename",
            "canonical_url",
            "sha256",
            "aliases",
        }

        extra = {
            k: v
            for k, v in doc.items()
            if k not in known
        }

        if extra:
            print("Additional metadata:")
            for key, value in extra.items():
                print(f"  {key}: {short_text(value)}")


# ============================================================
# 2. PER-PDF KNOWLEDGE FILES
# ============================================================

def inspect_pdf_knowledge_files():
    print_separator("2. _pdf_knowledge_<...>.json — PER-PDF EXTRACTION")

    files = sorted(DATA_DIR.glob("_pdf_knowledge_*.json"))

    # Exclude combined chunk file if glob ever catches it
    files = [
        f for f in files
        if f.name != "_pdf_knowledge_chunks.json"
    ]

    print(f"\nPer-PDF knowledge files found: {len(files)}")

    if not files:
        return

    global_page_count = 0
    global_skipped_count = 0

    source_counter = Counter()
    quality_counter = Counter()

    pdf_summaries = []

    for file in files:

        data = load_json(file)

        if not isinstance(data, dict):
            continue

        pages = data.get("pages", [])

        canonical_title = data.get("canonical_title", "")
        canonical_url = data.get("canonical_url", "")
        sha256 = data.get("sha256", "")

        page_count = len(pages)

        skipped = [
            p for p in pages
            if p.get("skipped") is True
        ]

        chunks_count = sum(
            len(p.get("chunks", []))
            for p in pages
        )

        source_counter.update(
            p.get("source", "missing")
            for p in pages
        )

        quality_counter.update(
            p.get("quality", {}).get("flag", "missing")
            for p in pages
        )

        global_page_count += page_count
        global_skipped_count += len(skipped)

        pdf_summaries.append({
            "file": file.name,
            "title": canonical_title,
            "url": canonical_url,
            "sha256": sha256,
            "pages": page_count,
            "skipped": len(skipped),
            "usable": page_count - len(skipped),
            "chunks": chunks_count,
        })

    print("\nOverall extraction statistics:")
    print(f"  PDF files:       {len(pdf_summaries)}")
    print(f"  Total pages:     {global_page_count}")
    print(f"  Skipped pages:   {global_skipped_count}")
    print(f"  Usable pages:    {global_page_count - global_skipped_count}")

    total_chunks = sum(x["chunks"] for x in pdf_summaries)

    print(f"  Total chunks:    {total_chunks}")

    print("\nPage source distribution:")

    for key, count in source_counter.most_common():
        print(f"  {key}: {count}")

    print("\nQuality flag distribution:")

    for key, count in quality_counter.most_common():
        print(f"  {key}: {count}")

    print("\nPer-PDF summary:")

    for i, item in enumerate(pdf_summaries, start=1):

        print(
            f"\n{i:02d}. {item['file']}"
        )

        print(
            f"    title:   {short_text(item['title'], 120)}"
        )

        print(
            f"    pages:   {item['pages']} | "
            f"usable: {item['usable']} | "
            f"skipped: {item['skipped']} | "
            f"chunks: {item['chunks']}"
        )

        print(
            f"    url:     {short_text(item['url'], 160)}"
        )

    # --------------------------------------------------------
    # Inspect representative page records
    # --------------------------------------------------------

    print_separator(
        "2A. REPRESENTATIVE PAGE RECORDS / SCHEMA INSPECTION"
    )

    # Pick:
    # 1. first PDF
    # 2. largest PDF
    # 3. PDF with skipped pages
    # 4. small PDF

    representative_files = []

    if files:
        representative_files.append(files[0])

    # Largest based on JSON page count
    largest_file = None
    largest_pages = -1

    skipped_file = None
    small_file = None

    for file in files:
        data = load_json(file)

        if not isinstance(data, dict):
            continue

        pages = data.get("pages", [])

        if len(pages) > largest_pages:
            largest_pages = len(pages)
            largest_file = file

        if skipped_file is None:
            if any(p.get("skipped") for p in pages):
                skipped_file = file

        if small_file is None and 1 <= len(pages) <= 10:
            small_file = file

    for candidate in [largest_file, skipped_file, small_file]:
        if candidate and candidate not in representative_files:
            representative_files.append(candidate)

    for file in representative_files:

        data = load_json(file)

        if not isinstance(data, dict):
            continue

        pages = data.get("pages", [])

        print(f"\nFILE: {file.name}")
        print(f"Title: {data.get('canonical_title', '')}")
        print(f"URL:   {data.get('canonical_url', '')}")
        print(f"SHA:   {data.get('sha256', '')}")
        print(f"Pages: {len(pages)}")

        print("\nTop-level keys:")
        for key in data.keys():
            value = data[key]

            if isinstance(value, list):
                print(f"  {key}: list ({len(value)})")
            elif isinstance(value, dict):
                print(f"  {key}: dict ({len(value)})")
            else:
                print(f"  {key}: {type(value).__name__}")

        if pages:

            print("\nFirst page record keys:")
            for key in pages[0].keys():
                print(f"  {key}")

            print("\nFirst page record:")
            print(json.dumps(
                pages[0],
                ensure_ascii=False,
                indent=2
            )[:7000])

            # Find a skipped page
            skipped_page = next(
                (p for p in pages if p.get("skipped")),
                None
            )

            if skipped_page:
                print("\nExample skipped page:")
                print(json.dumps(
                    skipped_page,
                    ensure_ascii=False,
                    indent=2
                )[:5000])

            # Find page with flagged lines
            flagged_page = next(
                (
                    p for p in pages
                    if p.get("flagged_lines")
                ),
                None
            )

            if flagged_page:
                print("\nExample page with flagged lines:")
                print(json.dumps(
                    flagged_page,
                    ensure_ascii=False,
                    indent=2
                )[:5000])


# ============================================================
# 3. COMBINED CHUNKS
# ============================================================

def inspect_chunks():
    print_separator("3. _pdf_knowledge_chunks.json — COMBINED CHUNKS")

    data = load_json(CHUNKS_FILE)

    if data is None:
        return

    if not isinstance(data, list):
        print(f"Unexpected structure: {type(data).__name__}")
        return

    print(f"\nTotal chunk records: {len(data)}")

    if not data:
        return

    # Schema
    all_keys = Counter()

    for item in data:
        if isinstance(item, dict):
            all_keys.update(item.keys())

    print("\nChunk record fields:")

    for key, count in all_keys.most_common():
        print(f"  {key}: present in {count}/{len(data)}")

    # Distribution by PDF
    pdf_counter = Counter(
        item.get("pdf_file", "MISSING")
        for item in data
        if isinstance(item, dict)
    )

    print("\nChunks by PDF:")

    for pdf, count in pdf_counter.most_common():
        print(f"  {pdf}: {count}")

    # Distribution by source
    source_counter = Counter(
        item.get("source", "MISSING")
        for item in data
        if isinstance(item, dict)
    )

    print("\nChunks by extraction source:")

    for source, count in source_counter.most_common():
        print(f"  {source}: {count}")

    # Quality
    quality_counter = Counter(
        item.get("quality_flag", "MISSING")
        for item in data
        if isinstance(item, dict)
    )

    print("\nChunks by quality flag:")

    for quality, count in quality_counter.most_common():
        print(f"  {quality}: {count}")

    # Page distribution
    pages_per_pdf = defaultdict(set)

    for item in data:
        if not isinstance(item, dict):
            continue

        pdf = item.get("pdf_file", "MISSING")
        page = item.get("page")

        if page is not None:
            pages_per_pdf[pdf].add(page)

    print("\nDistinct usable pages represented in chunks:")

    for pdf, pages in sorted(
        pages_per_pdf.items(),
        key=lambda x: len(x[1]),
        reverse=True
    ):
        print(
            f"  {pdf}: {len(pages)} pages"
        )

    # Sample chunks
    print_separator("3A. SAMPLE CHUNK RECORDS")

    sample_indices = [0]

    if len(data) > 1:
        sample_indices.append(len(data) // 2)

    if len(data) > 2:
        sample_indices.append(len(data) - 1)

    for idx in sample_indices:

        item = data[idx]

        print(f"\n--- Chunk index {idx} ---")
        print(json.dumps(
            item,
            ensure_ascii=False,
            indent=2
        )[:6000])


# ============================================================
# 4. SKIP SUMMARY
# ============================================================

def inspect_skip_summary():
    print_separator(
        "4. _pdf_extraction_skip_summary.json — SKIPPED PAGE ANALYSIS"
    )

    data = load_json(SKIP_FILE)

    if data is None:
        return

    print("\nTop-level keys:")

    for key in data.keys():
        value = data[key]

        if isinstance(value, list):
            print(f"  {key}: list ({len(value)})")
        elif isinstance(value, dict):
            print(f"  {key}: dict ({len(value)})")
        else:
            print(f"  {key}: {type(value).__name__}")

    skipped = data.get("skipped_pages", [])

    print(
        f"\nTotal skipped pages according to file: "
        f"{data.get('total_skipped_pages', len(skipped))}"
    )

    if not skipped:
        print("No skipped pages.")
        return

    reason_counter = Counter(
        item.get("reason", "MISSING")
        for item in skipped
    )

    quality_counter = Counter(
        item.get("quality_flag", "MISSING")
        for item in skipped
    )

    pdf_counter = Counter(
        item.get("pdf_file", "MISSING")
        for item in skipped
    )

    print("\nSkip reasons:")

    for key, count in reason_counter.most_common():
        print(f"  {key}: {count}")

    print("\nQuality flags among skipped pages:")

    for key, count in quality_counter.most_common():
        print(f"  {key}: {count}")

    print("\nSkipped pages by PDF:")

    for pdf, count in pdf_counter.most_common():
        pages = [
            item.get("page")
            for item in skipped
            if item.get("pdf_file") == pdf
        ]

        print(
            f"  {pdf}: {count} page(s) -> {pages}"
        )

    print_separator("4A. SAMPLE SKIPPED RECORDS")

    for item in skipped[:10]:

        print(json.dumps(
            item,
            ensure_ascii=False,
            indent=2
        ))


# ============================================================
# 5. CROSS-FILE CONSISTENCY CHECK
# ============================================================

def consistency_check():
    print_separator("5. CROSS-FILE CONSISTENCY CHECK")

    duplicates = load_json(DUPLICATES_FILE)
    chunks = load_json(CHUNKS_FILE)
    skips = load_json(SKIP_FILE)

    # --------------------------------------------------------
    # Canonical PDFs
    # --------------------------------------------------------

    canonical_files = set()

    if isinstance(duplicates, dict):
        for doc in duplicates.get("unique_documents", []):
            filename = doc.get("canonical_local_filename")

            if filename:
                canonical_files.add(filename)

    # --------------------------------------------------------
    # Per-PDF extraction files
    # --------------------------------------------------------

    extraction_files = {
        f.name
        for f in DATA_DIR.glob("_pdf_knowledge_*.json")
        if f.name != "_pdf_knowledge_chunks.json"
    }

    print(f"\nCanonical PDFs:          {len(canonical_files)}")
    print(f"Per-PDF extraction files:{len(extraction_files)}")

    missing_extractions = canonical_files - extraction_files
    extra_extractions = extraction_files - {
        f"_pdf_knowledge_{Path(x).stem}.json"
        for x in canonical_files
    }

    if missing_extractions:
        print("\n[WARNING] Canonical PDFs without extraction file:")

        for x in sorted(missing_extractions):
            print(f"  - {x}")
    else:
        print("\n[OK] Every canonical PDF has a per-PDF extraction file.")

    # --------------------------------------------------------
    # Chunk PDFs
    # --------------------------------------------------------

    chunk_pdfs = set()

    if isinstance(chunks, list):
        chunk_pdfs = {
            item.get("pdf_file")
            for item in chunks
            if isinstance(item, dict)
            and item.get("pdf_file")
        }

    print(f"\nPDFs represented in chunks: {len(chunk_pdfs)}")

    missing_from_chunks = extraction_files - {
        f"_pdf_knowledge_{Path(x).stem}.json"
        for x in chunk_pdfs
    }

    if missing_from_chunks:
        print(
            "\n[INFO] Extraction files not represented in "
            "combined chunks:"
        )

        for x in sorted(missing_from_chunks):
            print(f"  - {x}")
    else:
        print("\n[OK] All extraction PDFs are represented in chunks.")

    # --------------------------------------------------------
    # Skip PDFs
    # --------------------------------------------------------

    skip_pdfs = set()

    if isinstance(skips, dict):
        skip_pdfs = {
            item.get("pdf_file")
            for item in skips.get("skipped_pages", [])
            if item.get("pdf_file")
        }

    print(
        f"\nPDFs with at least one skipped page: "
        f"{len(skip_pdfs)}"
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nConsistency check complete.")


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("#" * 90)
    print(" UET CHATBOT — PDF PIPELINE OUTPUT INSPECTION")
    print("#" * 90)

    print(f"\nProject root:")
    print(f"  {PROJECT_ROOT}")

    print(f"\nData directory:")
    print(f"  {DATA_DIR}")

    print("\nThis script is READ-ONLY.")
    print("No source files will be modified.")

    inspect_duplicates()
    inspect_pdf_knowledge_files()
    inspect_chunks()
    inspect_skip_summary()
    consistency_check()

    print_separator("INSPECTION COMPLETE")

    print(
        "\nPlease copy the terminal output back here.\n"
        "I will use it to design the PDF inventory, classification,\n"
        "refinement and review stage without changing the completed\n"
        "web/action pipeline."
    )


if __name__ == "__main__":
    main()