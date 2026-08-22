import json
from pathlib import Path


# ============================================================
# UET CHATBOT — KNOWLEDGE MERGE
# ============================================================
#
# Input:
#   data/inventory/admission/_pages_knowledge_chunks.json
#   (133 chunks from 52 pages)
#   data/inventory/admission/_pdf_knowledge_final.json
#   (1250 chunks from 19 PDFs)
#   data/inventory/admission/_actions_registry.json
#   (14 navigational action links)
#
# Output:
#   data/inventory/admission/_knowledge_base.json
#
# Purpose:
#   Bring the two retrievable-text sources (pages + PDFs) into
#   one unified "chunks" array with a consistent schema and a
#   stable, traceable ID per chunk -- ready for the ingestion /
#   embeddings stage.
#
#   Actions are intentionally kept as a SEPARATE section, not
#   merged into "chunks". They are single navigational links
#   (e.g. "forgot my challan number" -> URL), not paragraphs a
#   retrieval system should return as an answer. Mixing them in
#   would make retrieval treat a login link the same way as a
#   fee-structure paragraph, which is the wrong behaviour.
#
# ID scheme:
#   page_001, page_002, ...   (stable within this run, based on
#                               sorted url then chunk_index)
#   pdf_001,  pdf_002,  ...    (stable within this run, based on
#                               sorted pdf_file then chunk_index)
#
#   IDs are re-generated fresh each run rather than reusing any
#   upstream index, since neither _pages_knowledge_chunks.json
#   nor _pdf_knowledge_final.json currently carries a stable ID
#   of its own.
#
# ============================================================


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

PAGES_CHUNKS_FILE = DATA_DIR / "_pages_knowledge_chunks.json"

PDF_CHUNKS_FILE = DATA_DIR / "_pdf_knowledge_final.json"

ACTIONS_FILE = DATA_DIR / "_actions_registry.json"

OUTPUT_FILE = DATA_DIR / "_knowledge_base.json"


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# LOAD
# ============================================================

def load_json(path, label):

    if not path.exists():

        raise FileNotFoundError(
            f"\n{label} file was not found:\n"
            f"{path}"
        )

    print(
        "Reading:"
    )

    print(path)

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# NORMALIZE PAGE CHUNKS
# ============================================================

def normalize_page_chunks(raw_chunks):
    """
    Assign a stable page_NNN id and a consistent field set.
    Ordered by (canonical_url, chunk_index) so IDs don't jump
    around between runs just because dict ordering changed.
    """

    ordered = sorted(
        raw_chunks,
        key=lambda c: (
            normalize(c.get("canonical_url")),
            c.get("chunk_index", 0),
        ),
    )

    normalized = []

    for index, chunk in enumerate(ordered, start=1):

        normalized.append({
            "id": f"page_{index:03d}",
            "source_type": "page",
            "title": chunk.get("title", ""),
            "book": chunk.get("book", ""),
            "url": chunk.get("canonical_url", ""),
            "text": chunk.get("text", ""),
            "temporal": chunk.get("temporal", False),
            "quality_flag": chunk.get("quality_flag", ""),
            "extraction_method": chunk.get("source", "page"),
            "origin": {
                "chunk_index": chunk.get("chunk_index", 0),
                "status": chunk.get("status", ""),
                "role": chunk.get("role", ""),
                "score": chunk.get("score", 0),
                "categories": chunk.get("categories", []),
                "page_type": chunk.get("page_type", ""),
            },
        })

    return normalized


# ============================================================
# NORMALIZE PDF CHUNKS
# ============================================================

def normalize_pdf_chunks(raw_chunks):
    """
    Assign a stable pdf_NNN id and the same consistent field
    set as page chunks. Ordered by (pdf_file, page, chunk_index)
    for run-to-run stability.
    """

    ordered = sorted(
        raw_chunks,
        key=lambda c: (
            normalize(c.get("pdf_file")),
            c.get("page", 0),
            c.get("chunk_index", 0),
        ),
    )

    normalized = []

    for index, chunk in enumerate(ordered, start=1):

        normalized.append({
            "id": f"pdf_{index:03d}",
            "source_type": "pdf",
            "title": chunk.get("title", ""),
            "book": chunk.get("book", ""),
            "url": chunk.get("canonical_url", ""),
            "text": chunk.get("text", ""),
            "temporal": chunk.get("temporal", False),
            "quality_flag": chunk.get("quality_flag", ""),
            "extraction_method": chunk.get("source", "pdf"),
            "origin": {
                "pdf_file": chunk.get("pdf_file", ""),
                "page": chunk.get("page", 0),
                "chunk_index": chunk.get("chunk_index", 0),
                "sha256": chunk.get("sha256", ""),
                "all_urls": chunk.get("all_urls", []),
            },
        })

    return normalized


# ============================================================
# NORMALIZE ACTIONS
# ============================================================

def normalize_actions(actions_data):
    """
    Actions are grouped by action_type in the source file
    ({"create_challan": [...], "forget_challan": [...], ...}).
    This flattens that into a single list, carrying the type
    forward as an explicit field on each action.
    """

    grouped_actions = actions_data.get("actions", {})

    normalized = []

    index = 0

    for action_type, group in grouped_actions.items():

        for action in group:

            index += 1

            normalized.append({
                "id": f"action_{index:03d}",
                "title": action.get("title", ""),
                "url": action.get("url", ""),
                "program": action.get("program", ""),
                "context": action.get("context", ""),
                "action_type": action_type,
                "priority": action.get("priority", ""),
            })

    return normalized


# ============================================================
# VALIDATION
# ============================================================

def validate(page_chunks, pdf_chunks, actions, raw_pages, raw_pdfs, raw_actions):

    errors = []

    if len(page_chunks) != len(raw_pages):

        errors.append(
            f"Page chunk count mismatch: {len(page_chunks)} "
            f"normalized vs {len(raw_pages)} input"
        )

    if len(pdf_chunks) != len(raw_pdfs):

        errors.append(
            f"PDF chunk count mismatch: {len(pdf_chunks)} "
            f"normalized vs {len(raw_pdfs)} input"
        )

    raw_action_count = sum(
        len(group)
        for group in raw_actions.get("actions", {}).values()
    )

    if len(actions) != raw_action_count:

        errors.append(
            f"Action count mismatch: {len(actions)} "
            f"normalized vs {raw_action_count} input"
        )

    all_ids = (
        [c["id"] for c in page_chunks]
        + [c["id"] for c in pdf_chunks]
        + [a["id"] for a in actions]
    )

    if len(all_ids) != len(set(all_ids)):

        errors.append(
            "Duplicate IDs found across chunks/actions."
        )

    for chunk in page_chunks + pdf_chunks:

        if not chunk["text"].strip():

            errors.append(
                f"Empty text for chunk {chunk['id']}"
            )

        if not chunk["book"]:

            errors.append(
                f"Missing book for chunk {chunk['id']}"
            )

        if not chunk["url"]:

            errors.append(
                f"Missing url for chunk {chunk['id']}"
            )

    for action in actions:

        if not action["url"]:

            errors.append(
                f"Missing url for {action['id']}"
            )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — KNOWLEDGE MERGE"
    )
    print("=" * 70)
    print()

    pages_data = load_json(PAGES_CHUNKS_FILE, "Page chunks")

    pdf_data = load_json(PDF_CHUNKS_FILE, "PDF chunks")

    actions_data = load_json(ACTIONS_FILE, "Actions registry")

    raw_pages = pages_data.get("chunks", [])

    raw_pdfs = pdf_data.get("chunks", [])

    print()
    print(
        f"Input page chunks : {len(raw_pages)}"
    )

    print(
        f"Input PDF chunks   : {len(raw_pdfs)}"
    )

    print(
        f"Input actions      : "
        f"{sum(len(g) for g in actions_data.get('actions', {}).values())}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    page_chunks = normalize_page_chunks(raw_pages)

    pdf_chunks = normalize_pdf_chunks(raw_pdfs)

    actions = normalize_actions(actions_data)

    all_chunks = page_chunks + pdf_chunks

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    books_count = {}

    for chunk in all_chunks:

        books_count[chunk["book"]] = (
            books_count.get(chunk["book"], 0) + 1
        )

    action_types_count = {}

    for action in actions:

        action_types_count[action["action_type"]] = (
            action_types_count.get(
                action["action_type"],
                0,
            )
            + 1
        )

    temporal_count = sum(
        1 for chunk in all_chunks if chunk["temporal"]
    )

    print()
    print("=" * 70)
    print(
        "MERGE RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"  Total chunks       : {len(all_chunks)}"
    )

    print(
        f"    from pages       : {len(page_chunks)}"
    )

    print(
        f"    from PDFs        : {len(pdf_chunks)}"
    )

    print(
        f"  Temporal chunks    : {temporal_count}"
    )

    print(
        f"  Total actions      : {len(actions)}"
    )

    print()
    print(
        "  Chunks per book:"
    )

    for book_name, count in sorted(
        books_count.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"    {book_name:<28} : {count}"
        )

    print()
    print(
        "  Actions per type:"
    )

    for action_type, count in sorted(
        action_types_count.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"    {action_type:<28} : {count}"
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate(
        page_chunks,
        pdf_chunks,
        actions,
        raw_pages,
        raw_pdfs,
        actions_data,
    )

    if validation_errors:

        print(
            "INVALID"
        )

        for error in validation_errors:

            print(
                f"ERROR: {error}"
            )

        raise ValueError(
            "Knowledge merge validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "knowledge_merge",
        "input_files": {
            "pages": str(PAGES_CHUNKS_FILE),
            "pdfs": str(PDF_CHUNKS_FILE),
            "actions": str(ACTIONS_FILE),
        },
        "output_file": str(OUTPUT_FILE),
        "counts": {
            "total_chunks": len(all_chunks),
            "page_chunks": len(page_chunks),
            "pdf_chunks": len(pdf_chunks),
            "temporal_chunks": temporal_count,
            "total_actions": len(actions),
        },
        "books": books_count,
        "action_types": action_types_count,
        "chunks": all_chunks,
        "actions": actions,
    }

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print(
        "SAVED"
    )
    print("=" * 70)

    print()
    print(
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()