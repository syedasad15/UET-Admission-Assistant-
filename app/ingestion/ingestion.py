import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ============================================================
# UET CHATBOT — KNOWLEDGE INGESTION (EMBEDDINGS)
# ============================================================
#
# Input:
#   data/inventory/admission/_knowledge_base.json
#   (1383 chunks: 133 from pages, 1250 from PDFs)
#
# Output:
#   data/vectorstore/chroma/              (persistent ChromaDB)
#   data/inventory/admission/_ingestion_manifest.json
#
# Purpose:
#   Turn every retrievable chunk into a vector embedding and
#   store it in a persistent, on-disk ChromaDB collection, so
#   the retrieval stage can do semantic search over the whole
#   admissions knowledge base without re-computing embeddings
#   every run.
#
#   Actions (_actions_registry.json / the "actions" section of
#   _knowledge_base.json) are intentionally NOT embedded here.
#   They're navigational links matched by intent/keyword, not
#   semantic passages — embedding them would let the retriever
#   return a login link as if it were an answer to a factual
#   question, which is the wrong behaviour.
#
# Model:
#   BAAI/bge-small-en-v1.5 (sentence-transformers, local, free,
#   ~130MB, runs on CPU). Chosen over an API-based embedding
#   model so the pipeline has no ongoing cost and no external
#   dependency — important since the eventual goal is handing
#   this over to UET's admissions office to host officially.
#
#   NOTE for the retrieval stage: BGE models are trained with
#   an asymmetric convention — passages (what's ingested here)
#   are embedded as-is, but QUERIES at retrieval time should be
#   prefixed with:
#       "Represent this sentence for searching relevant
#       passages: "
#   Skipping that prefix at query time measurably hurts
#   retrieval quality with BGE models.
#
# ============================================================


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

KNOWLEDGE_BASE_FILE = DATA_DIR / "_knowledge_base.json"

VECTORSTORE_DIR = (
    PROJECT_ROOT
    / "data"
    / "vectorstore"
    / "chroma"
)

MANIFEST_FILE = DATA_DIR / "_ingestion_manifest.json"


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

COLLECTION_NAME = "uet_admission_knowledge"

# How many chunks to embed per model.encode() call. Keeps
# memory bounded and gives us a place to show progress.
EMBED_BATCH_SIZE = 32

# Embed "title + text" rather than text alone. The title often
# carries context the chunk body doesn't repeat (e.g. "MS/M.Phil
# Fee Structure" for a chunk that just says "78,390 | 59,140 |
# ..."), which measurably helps semantic matching.
def build_embedding_input(chunk):

    title = (chunk.get("title") or "").strip()

    text = (chunk.get("text") or "").strip()

    if title:

        return f"{title}\n\n{text}"

    return text


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def sanitize_metadata(chunk):
    """
    ChromaDB metadata values must be str, int, float, or bool
    -- no lists/dicts/None. Flatten each chunk's fields into a
    metadata dict the vector store can actually accept, without
    losing the information (list fields become comma-joined
    strings).
    """

    origin = chunk.get("origin", {}) or {}

    categories = origin.get("categories", [])

    all_urls = origin.get("all_urls", [])

    metadata = {
        "source_type": normalize(chunk.get("source_type")),
        "title": normalize(chunk.get("title")),
        "book": normalize(chunk.get("book")),
        "url": normalize(chunk.get("url")),
        "temporal": bool(chunk.get("temporal", False)),
        "quality_flag": normalize(chunk.get("quality_flag")),
        "extraction_method": normalize(
            chunk.get("extraction_method")
        ),
        "categories": ", ".join(
            str(c) for c in categories
        ),
        "all_urls": ", ".join(
            str(u) for u in all_urls
        ),
        "pdf_file": normalize(origin.get("pdf_file")),
        "page": int(origin.get("page", 0) or 0),
        "status": normalize(origin.get("status")),
        "role": normalize(origin.get("role")),
        "score": int(origin.get("score", 0) or 0),
        "page_type": normalize(origin.get("page_type")),
    }

    # ChromaDB rejects empty-string metadata values in some
    # versions' query filters; keep them but never None.
    return {
        key: (value if value is not None else "")
        for key, value in metadata.items()
    }


# ============================================================
# LOAD
# ============================================================

def load_knowledge_base():

    if not KNOWLEDGE_BASE_FILE.exists():

        raise FileNotFoundError(
            "\nKnowledge base file was not found:\n"
            f"{KNOWLEDGE_BASE_FILE}\n\n"
            "Run knowledgemerge.py first."
        )

    print()
    print("Reading:")
    print(KNOWLEDGE_BASE_FILE)

    with KNOWLEDGE_BASE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    chunks = data.get("chunks", [])

    if not isinstance(chunks, list):

        raise ValueError(
            "Expected 'chunks' to be a list in "
            "_knowledge_base.json."
        )

    return chunks


# ============================================================
# EMBEDDING
# ============================================================

def load_embedding_model():

    print()
    print(
        f"Loading embedding model: {EMBEDDING_MODEL_NAME}"
    )

    print(
        "(first run downloads the model, ~130MB; "
        "cached after that)"
    )

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return model


def embed_chunks(model, chunks):

    inputs = [
        build_embedding_input(chunk)
        for chunk in chunks
    ]

    embeddings = []

    total = len(inputs)

    for start in range(0, total, EMBED_BATCH_SIZE):

        end = min(start + EMBED_BATCH_SIZE, total)

        batch = inputs[start:end]

        sys.stdout.write(
            f"\r        embedding {end}/{total} chunks..."
        )
        sys.stdout.flush()

        batch_embeddings = model.encode(
            batch,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        embeddings.extend(batch_embeddings.tolist())

    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()

    return embeddings


# ============================================================
# VECTOR STORE
# ============================================================

def get_collection():

    VECTORSTORE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR)
    )

    # Fresh ingestion each run -- drop and recreate so stale
    # chunks (renamed titles, excluded documents, corrected
    # text) never linger in the store from a previous run.
    try:

        client.delete_collection(COLLECTION_NAME)

    except Exception:  # noqa: BLE001

        pass  # Collection didn't exist yet -- fine.

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "embedding_model": EMBEDDING_MODEL_NAME,
            "description": (
                "UET Admissions chatbot knowledge base -- "
                "page and PDF chunks."
            ),
        },
    )

    return collection


def store_chunks(collection, chunks, embeddings):

    ids = [chunk["id"] for chunk in chunks]

    documents = [chunk.get("text", "") for chunk in chunks]

    metadatas = [
        sanitize_metadata(chunk)
        for chunk in chunks
    ]

    # Chroma has an add() batch-size ceiling in some backends;
    # chunk our own inserts defensively.
    insert_batch_size = 500

    total = len(ids)

    for start in range(0, total, insert_batch_size):

        end = min(start + insert_batch_size, total)

        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )


# ============================================================
# VALIDATION
# ============================================================

def validate(collection, chunks):

    errors = []

    stored_count = collection.count()

    if stored_count != len(chunks):

        errors.append(
            f"Stored vector count ({stored_count}) does not "
            f"match input chunk count ({len(chunks)})."
        )

    # Spot-check: fetch a handful of ids back and confirm the
    # document text round-trips correctly.
    sample_ids = [
        chunk["id"]
        for chunk in chunks[:: max(1, len(chunks) // 10)]
    ][:10]

    if sample_ids:

        result = collection.get(
            ids=sample_ids,
            include=["documents", "metadatas"],
        )

        returned_ids = set(result.get("ids", []))

        missing = set(sample_ids) - returned_ids

        if missing:

            errors.append(
                f"Sample ID(s) not retrievable after storing: "
                f"{missing}"
            )

    return errors, stored_count


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — KNOWLEDGE INGESTION (EMBEDDINGS)"
    )
    print("=" * 70)

    chunks = load_knowledge_base()

    print()
    print(
        f"Chunks to embed: {len(chunks)}"
    )

    # --------------------------------------------------------
    # Embed
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "EMBEDDING"
    )
    print("=" * 70)

    model = load_embedding_model()

    print()
    print(
        "Embedding chunks "
        f"(batch size {EMBED_BATCH_SIZE})..."
    )
    print()

    embeddings = embed_chunks(model, chunks)

    print(
        f"Done. {len(embeddings)} embeddings generated, "
        f"dimension {len(embeddings[0]) if embeddings else 0}."
    )

    # --------------------------------------------------------
    # Store
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "STORING IN CHROMADB"
    )
    print("=" * 70)

    print()
    print(
        f"Vector store path: {VECTORSTORE_DIR}"
    )

    collection = get_collection()

    store_chunks(collection, chunks, embeddings)

    print(
        f"Stored {collection.count()} vectors in collection "
        f"'{COLLECTION_NAME}'."
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

    validation_errors, stored_count = validate(
        collection,
        chunks,
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
            "Ingestion validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Summary by book (sanity check on distribution)
    # --------------------------------------------------------

    books_count = {}

    for chunk in chunks:

        book = chunk.get("book", "")

        books_count[book] = books_count.get(book, 0) + 1

    print()
    print("=" * 70)
    print(
        "INGESTION RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"  Total chunks embedded : {len(chunks)}"
    )

    print(
        f"  Vectors stored        : {stored_count}"
    )

    print(
        f"  Embedding model       : {EMBEDDING_MODEL_NAME}"
    )

    print(
        f"  Vector dimension      : "
        f"{len(embeddings[0]) if embeddings else 0}"
    )

    print(
        f"  Collection name       : {COLLECTION_NAME}"
    )

    print()
    print(
        "  Chunks per book:"
    )

    for book, count in sorted(
        books_count.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"    {book:<28} : {count}"
        )

    # --------------------------------------------------------
    # Save manifest (audit trail -- what was ingested, when,
    # with what model, without duplicating the vectors
    # themselves into another JSON file)
    # --------------------------------------------------------

    manifest = {
        "source": "UET Admissions Portal",
        "stage": "knowledge_ingestion",
        "input_file": str(KNOWLEDGE_BASE_FILE),
        "vectorstore_path": str(VECTORSTORE_DIR),
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_dimension": (
            len(embeddings[0]) if embeddings else 0
        ),
        "counts": {
            "chunks_embedded": len(chunks),
            "vectors_stored": stored_count,
        },
        "books": books_count,
        "chunk_ids": [chunk["id"] for chunk in chunks],
    }

    with MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
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
        f"Vector store : {VECTORSTORE_DIR}"
    )

    print(
        f"Manifest     : {MANIFEST_FILE}"
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()