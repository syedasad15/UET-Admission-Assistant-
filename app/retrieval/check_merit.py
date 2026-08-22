
import json
from pathlib import Path
import chromadb

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")
CHROMA_PATH = PROJECT_ROOT / "data" / "vectorstore" / "chroma"

COLLECTION_NAME = "uet_admission_knowledge"


# ============================================================
# HEADER
# ============================================================

print("\n" + "=" * 78)
print("UET ADMISSION — MERIT LIST DATA VERIFICATION")
print("=" * 78)

print(f"\nChroma path:")
print(CHROMA_PATH)

print(f"\nCollection:")
print(COLLECTION_NAME)


# ============================================================
# LOAD CHROMA
# ============================================================

try:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)

except Exception as e:
    print("\nERROR loading Chroma:")
    print(e)
    raise SystemExit(1)


# ============================================================
# BASIC INFO
# ============================================================

count = collection.count()

print(f"\nTotal vectors: {count}")

if count == 0:
    print("\nNo vectors found.")
    raise SystemExit(0)


# ============================================================
# GET ALL METADATA
# ============================================================

data = collection.get(
    include=["metadatas", "documents"]
)

metadatas = data.get("metadatas", [])
documents = data.get("documents", [])


# ============================================================
# SEARCH MERIT-RELATED METADATA/TEXT
# ============================================================

keywords = [
    "merit",
    "merit list",
    "meritlist",
    "selected candidates",
    "selection",
    "closing merit",
    "merit position",
    "merit score",
    "aggregate"
]

matches = []

for i, metadata in enumerate(metadatas):

    metadata_text = json.dumps(
        metadata,
        ensure_ascii=False
    ).lower()

    document_text = ""

    if i < len(documents) and documents[i]:
        document_text = documents[i].lower()

    combined = metadata_text + "\n" + document_text

    matched_keywords = [
        keyword
        for keyword in keywords
        if keyword.lower() in combined
    ]

    if matched_keywords:
        matches.append(
            {
                "index": i,
                "metadata": metadata,
                "document": documents[i] if i < len(documents) else "",
                "matched_keywords": matched_keywords,
            }
        )


# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 78)
print("MERIT-RELATED DATA")
print("=" * 78)

print(f"\nMatching chunks: {len(matches)}")


if not matches:
    print(
        "\n❌ No obvious merit-list data was found "
        "in the current Chroma collection."
    )

else:

    print(
        "\n✅ Merit-related data appears to be present "
        "in the vector store."
    )

    # Show maximum 20 examples
    for number, item in enumerate(matches[:20], start=1):

        print("\n" + "-" * 78)

        print(f"RESULT #{number}")

        print(
            "Matched keywords:",
            ", ".join(item["matched_keywords"])
        )

        print("\nMetadata:")

        for key, value in item["metadata"].items():
            print(f"  {key}: {value}")

        print("\nText preview:")

        text = item["document"].replace("\n", " ")

        if len(text) > 700:
            text = text[:700] + "..."

        print(text)


# ============================================================
# METADATA SUMMARY
# ============================================================

print("\n" + "=" * 78)
print("SOURCE / BOOK SUMMARY")
print("=" * 78)

book_counts = {}
source_counts = {}
type_counts = {}

for metadata in metadatas:

    book = str(metadata.get("book", "UNKNOWN"))
    source = str(metadata.get("source", metadata.get("url", "UNKNOWN")))
    source_type = str(metadata.get("source_type", "UNKNOWN"))

    book_counts[book] = book_counts.get(book, 0) + 1
    source_counts[source] = source_counts.get(source, 0) + 1
    type_counts[source_type] = type_counts.get(source_type, 0) + 1


print("\nBooks:")

for book, count_value in sorted(
    book_counts.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"  {book}: {count_value}")


print("\nSource types:")

for source_type, count_value in sorted(
    type_counts.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"  {source_type}: {count_value}")


print("\n" + "=" * 78)
print("VERIFICATION COMPLETE")
print("=" * 78)
