import os
import chromadb

# ============================================================
# CONFIG
# ============================================================

CHROMA_PATH = r"D:\UET Chatbot\data\vectorstore\chroma"
COLLECTION_NAME = "uet_admission_knowledge"

# Queries specifically designed to find the actual merit-list PDF
QUERIES = [
    "Computer Science closing merit 1st merit list",
    "Computer Science Merit List No. 1 closing merit",
    "Minimum Aggregate Computer Science Merit List No. 1",
    "Computer Science closing aggregate first merit list",
]

# ============================================================
# HELPERS
# ============================================================

def print_result(number, query, doc, metadata, distance=None):
    print("\n" + "-" * 80)
    print(f"RESULT #{number}")
    print(f"Query: {query}")

    if distance is not None:
        print(f"Distance: {distance}")

    print("\nMetadata:")
    if metadata:
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    else:
        print("  No metadata")

    print("\nText:")
    print("-" * 80)
    print(doc[:5000])
    print("-" * 80)


# ============================================================
# MAIN
# ============================================================

print("=" * 80)
print("UET ADMISSION — MERIT LIST PDF VERIFICATION")
print("=" * 80)

print(f"\nChroma path:")
print(CHROMA_PATH)

print(f"\nCollection:")
print(COLLECTION_NAME)

if not os.path.exists(CHROMA_PATH):
    print("\n❌ Chroma path does not exist!")
    print(CHROMA_PATH)
    raise SystemExit(1)

# ------------------------------------------------------------
# Connect to Chroma
# ------------------------------------------------------------

try:
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

except Exception as e:
    print("\n❌ Could not open Chroma collection.")
    print(f"Error: {e}")
    raise SystemExit(1)

print(f"\nTotal vectors: {collection.count()}")

print("\n" + "=" * 80)
print("SEARCHING FOR ACTUAL MERIT-LIST CONTENT")
print("=" * 80)

# ------------------------------------------------------------
# Run multiple semantic searches
# ------------------------------------------------------------

all_results = []

for query in QUERIES:

    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    try:
        results = collection.query(
            query_texts=[query],
            n_results=10,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    except Exception as e:
        print(f"❌ Query failed: {e}")
        continue

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        print("❌ No results.")
        continue

    for i, doc in enumerate(documents):

        metadata = (
            metadatas[i]
            if i < len(metadatas)
            else {}
        )

        distance = (
            distances[i]
            if i < len(distances)
            else None
        )

        print_result(
            i + 1,
            query,
            doc,
            metadata,
            distance,
        )

        all_results.append(
            {
                "query": query,
                "document": doc,
                "metadata": metadata,
                "distance": distance,
            }
        )


# ============================================================
# KEYWORD ANALYSIS
# ============================================================

print("\n\n" + "=" * 80)
print("KEYWORD ANALYSIS")
print("=" * 80)

keywords = [
    "merit list no. 1",
    "merit list no 1",
    "first merit list",
    "computer science",
    "computer sciences",
    "closing merit",
    "closing aggregate",
    "minimum aggregate",
    "cs",
]

matches = []

for item in all_results:

    text = item["document"].lower()

    found = [
        keyword
        for keyword in keywords
        if keyword in text
    ]

    if found:
        matches.append(
            {
                **item,
                "matched_keywords": found,
            }
        )


print(f"\nResults containing relevant keywords: {len(matches)}")

for i, item in enumerate(matches, 1):

    print("\n" + "-" * 80)
    print(f"MATCH #{i}")

    print(
        "Matched keywords:",
        ", ".join(item["matched_keywords"])
    )

    print("\nMetadata:")

    for key, value in item["metadata"].items():
        print(f"  {key}: {value}")

    print("\nRelevant text:")

    # Print only around occurrences of important terms
    text = item["document"]

    lower = text.lower()

    positions = []

    for keyword in [
        "computer science",
        "closing merit",
        "minimum aggregate",
        "merit list no. 1",
    ]:
        pos = lower.find(keyword)

        if pos != -1:
            positions.append(pos)

    if positions:
        start = max(0, min(positions) - 1000)
        end = min(len(text), max(positions) + 3000)

        print(text[start:end])

    else:
        print(text[:4000])


# ============================================================
# PDF METADATA CHECK
# ============================================================

print("\n\n" + "=" * 80)
print("PDF SOURCE CHECK")
print("=" * 80)

pdf_results = []

for item in all_results:

    metadata = item["metadata"]

    pdf_file = str(metadata.get("pdf_file", "")).strip()
    source_type = str(metadata.get("source_type", "")).lower()

    if pdf_file or source_type == "pdf":
        pdf_results.append(item)


print(f"\nPDF-related results found: {len(pdf_results)}")

if pdf_results:

    for i, item in enumerate(pdf_results, 1):

        print("\n" + "-" * 80)
        print(f"PDF RESULT #{i}")

        metadata = item["metadata"]

        print(f"pdf_file: {metadata.get('pdf_file', '')}")
        print(f"source_type: {metadata.get('source_type', '')}")
        print(f"title: {metadata.get('title', '')}")
        print(f"url: {metadata.get('url', '')}")
        print(f"page: {metadata.get('page', '')}")

else:

    print("""
⚠️ NO PDF-SOURCE RESULT FOUND.

This is important.

The vectorstore may contain the Downloads page that LINKS to the
merit-list PDF, but the actual PDF content may not have been ingested.
""")


# ============================================================
# FINAL DIAGNOSIS
# ============================================================

print("\n\n" + "=" * 80)
print("FINAL DIAGNOSIS")
print("=" * 80)

has_cs = False
has_merit1 = False
has_closing = False
has_pdf = False

for item in all_results:

    text = item["document"].lower()
    metadata = item["metadata"]

    if "computer science" in text:
        has_cs = True

    if (
        "merit list no. 1" in text
        or "merit list no 1" in text
        or "first merit list" in text
    ):
        has_merit1 = True

    if (
        "closing merit" in text
        or "closing aggregate" in text
        or "minimum aggregate" in text
    ):
        has_closing = True

    if (
        str(metadata.get("pdf_file", "")).strip()
        or str(metadata.get("source_type", "")).lower() == "pdf"
    ):
        has_pdf = True


print(f"""
Computer Science found:       {"✅ YES" if has_cs else "❌ NO"}
1st Merit List found:         {"✅ YES" if has_merit1 else "❌ NO"}
Closing merit/aggregate:      {"✅ YES" if has_closing else "❌ NO"}
Actual PDF source found:      {"✅ YES" if has_pdf else "❌ NO"}
""")


if has_cs and has_merit1 and has_closing and has_pdf:

    print("""
✅ GOOD NEWS

The actual merit-list PDF content appears to be in Chroma.

Next step:
We should inspect the exact matching chunk and then fix/test
the answer-generation layer.
""")

elif has_cs and has_merit1 and has_closing and not has_pdf:

    print("""
⚠️ PARTIAL SUCCESS

Merit information is present, but the result appears to come from
a webpage/index rather than the actual PDF.

We should verify PDF ingestion and metadata.
""")

else:

    print("""
❌ MERIT PDF CONTENT NOT PROPERLY RETRIEVED

The Downloads page/index appears to be present, but the exact
Computer Science closing-merit data is not being retrieved.

Next step should be PDF ingestion/retrieval debugging.
""")


print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)