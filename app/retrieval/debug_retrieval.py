import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# UET CHATBOT — RETRIEVAL DIAGNOSTIC
# ============================================================
#
# Purpose:
#   For a given question, show EVERY candidate ChromaDB
#   returns (not just the final filtered/diversified 8), with
#   its distance and page. This tells us whether the page
#   11/12 override chunks are:
#
#     a) not being retrieved at all (ranking problem -- their
#        embedding doesn't match the query well), or
#     b) being retrieved but filtered out by MAX_DISTANCE, or
#     c) being retrieved and passing the filter, but crowded
#        out by diversify_sources() before reaching the final
#        list the LLM sees.
#
#   This script does NOT modify anything -- read-only.
#
# Usage:
#   python -u debug_retrieval.py "your question here"
#
# ============================================================


PROJECT_ROOT = Path(r"D:\UET Chatbot")

VECTORSTORE_DIR = (
    PROJECT_ROOT
    / "data"
    / "vectorstore"
    / "chroma"
)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

COLLECTION_NAME = "uet_admission_knowledge"

BGE_QUERY_PREFIX = (
    "Represent this sentence for searching relevant passages: "
)

# Same threshold retrieval.py uses -- shown here so we can see
# which candidates would survive it.
MAX_DISTANCE = 0.78

# Pages we specifically care about for this diagnostic (the
# UG prospectus program-list override chunks).
WATCH_PDF_FILE = "UG-2026-1_78f5bbdf-88d5-4889-b97c-9f0d773d7d6d.pdf"

WATCH_PAGES = {11, 12}


def main():

    if len(sys.argv) < 2:

        question = (
            "What BS programs are offered at UET?"
        )

        print(
            f"No question given, using default: {question!r}"
        )

    else:

        question = " ".join(sys.argv[1:])

    print()
    print("=" * 78)
    print(
        "RETRIEVAL DIAGNOSTIC"
    )
    print("=" * 78)

    print()
    print(
        f"Question: {question}"
    )

    client = chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    print(
        f"Collection size: {collection.count()}"
    )

    print()
    print(
        "Loading embedding model..."
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    query_text = BGE_QUERY_PREFIX + question

    query_embedding = model.encode(
        [query_text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Ask for a large candidate pool -- 50 -- so we can see
    # deep into the ranking, not just the top few.
    result = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=50,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]

    metadatas = result.get("metadatas", [[]])[0]

    distances = result.get("distances", [[]])[0]

    documents = result.get("documents", [[]])[0]

    print()
    print("=" * 78)
    print(
        f"TOP {len(ids)} CANDIDATES (all, before filtering)"
    )
    print("=" * 78)

    watched_found = []

    for rank, chunk_id in enumerate(ids, start=1):

        metadata = metadatas[rank - 1] or {}

        distance = distances[rank - 1]

        pdf_file = metadata.get("pdf_file", "")

        page = metadata.get("page", 0)

        title = metadata.get("title", "")

        is_watched = (
            pdf_file == WATCH_PDF_FILE
            and page in WATCH_PAGES
        )

        passes_filter = (
            distance is not None
            and distance <= MAX_DISTANCE
        )

        marker = ""

        if is_watched:

            marker = "  <<< PAGE 11/12 OVERRIDE CHUNK"

            watched_found.append(
                (rank, chunk_id, distance, page)
            )

        flag = "PASS" if passes_filter else "FILTERED OUT"

        print(
            f"[{rank:02d}] dist={distance:.4f} "
            f"({flag:<12}) "
            f"id={chunk_id:<10} "
            f"page={page:<4} "
            f"title={title[:45]:<45}{marker}"
        )

    print()
    print("=" * 78)
    print(
        "SUMMARY"
    )
    print("=" * 78)

    if not watched_found:

        print()
        print(
            "None of the page 11/12 override chunks appeared "
            f"in the top {len(ids)} candidates at all."
        )

        print(
            "This means the embedding of these chunks doesn't "
            "semantically match this question well enough --"
        )

        print(
            "a ranking/embedding problem, not a filtering "
            "problem."
        )

    else:

        print()
        print(
            "Page 11/12 override chunks found in candidates:"
        )

        for rank, chunk_id, distance, page in watched_found:

            passes = distance <= MAX_DISTANCE

            print(
                f"  Rank {rank}: {chunk_id} (page {page}) "
                f"distance={distance:.4f} "
                f"-> {'PASSES' if passes else 'FILTERED OUT'} "
                f"filter (MAX_DISTANCE={MAX_DISTANCE})"
            )

        best_rank = watched_found[0][0]

        if best_rank > 8:

            print()
            print(
                f"Best rank is {best_rank}, but retrieval.py "
                "only keeps the top few after diversify_sources "
                "(FINAL_RESULTS=8) -- likely crowded out even "
                "though it technically matched."
            )

    print()


if __name__ == "__main__":
    main()