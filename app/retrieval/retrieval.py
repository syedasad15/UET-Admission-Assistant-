# # import json
# # import sys
# # from pathlib import Path

# # import chromadb
# # from sentence_transformers import SentenceTransformer


# # # ============================================================
# # # UET CHATBOT — IMPROVED SEMANTIC RETRIEVAL
# # # ============================================================
# # #
# # # Input:
# # #   data/vectorstore/chroma/
# # #
# # # Collection:
# # #   uet_admission_knowledge
# # #
# # # Embedding model:
# # #   BAAI/bge-small-en-v1.5
# # #
# # # Purpose:
# # #   Production-oriented semantic retrieval for the UET
# # #   Admissions chatbot.
# # #
# # # Improvements:
# # #   1. Correct BGE query instruction prefix
# # #   2. Configurable similarity threshold
# # #   3. Source/document grouping
# # #   4. Duplicate result suppression
# # #   5. Source metadata preservation
# # #   6. PDF/page/source URL reporting
# # #   7. Confidence classification
# # #   8. Retrieval audit JSON
# # #
# # # IMPORTANT:
# # #   This script DOES NOT modify the knowledge base.
# # #   This script DOES NOT modify ChromaDB.
# # #   It only reads from the vector store.
# # #
# # # ============================================================


# # # ============================================================
# # # PROJECT PATHS
# # # ============================================================

# # PROJECT_ROOT = Path(r"D:\UET Chatbot")

# # VECTORSTORE_DIR = (
# #     PROJECT_ROOT
# #     / "data"
# #     / "vectorstore"
# #     / "chroma"
# # )

# # AUDIT_DIR = (
# #     PROJECT_ROOT
# #     / "data"
# #     / "retrieval"
# # )

# # LAST_RETRIEVAL_FILE = (
# #     AUDIT_DIR
# #     / "last_retrieval.json"
# # )


# # # ============================================================
# # # CONFIGURATION
# # # ============================================================

# # EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# # COLLECTION_NAME = "uet_admission_knowledge"


# # # Number of candidates requested from Chroma.
# # #
# # # We retrieve more candidates than we finally display because
# # # filtering/grouping may remove some results.
# # RETRIEVAL_CANDIDATES = 20


# # # Number of final results shown.
# # FINAL_RESULTS = 8


# # # Chroma distance is cosine distance because the embeddings
# # # were normalized during ingestion.
# # #
# # # Lower distance = more similar.
# # #
# # # This is deliberately not extremely strict because admission
# # # questions can have different wording from the source text.
# # MAX_DISTANCE = 0.78


# # # Results below these distances are considered stronger.
# # STRONG_DISTANCE = 0.55
# # GOOD_DISTANCE = 0.65


# # # ============================================================
# # # BGE QUERY INSTRUCTION
# # # ============================================================
# # #
# # # BAAI/bge-small-en-v1.5 uses an asymmetric retrieval setup.
# # #
# # # Passages:
# # #   embedded normally during ingestion.
# # #
# # # Queries:
# # #   should use the following instruction.
# # #
# # # ============================================================

# # BGE_QUERY_PREFIX = (
# #     "Represent this sentence for searching relevant passages: "
# # )


# # # ============================================================
# # # HELPERS
# # # ============================================================

# # def normalize(value):
# #     if value is None:
# #         return ""

# #     return str(value).strip()


# # def safe_int(value):
# #     try:
# #         return int(value)
# #     except (TypeError, ValueError):
# #         return 0


# # def build_query(question):
# #     """
# #     Apply the BGE retrieval instruction.
# #     """

# #     question = normalize(question)

# #     if not question:
# #         return ""

# #     return BGE_QUERY_PREFIX + question


# # def get_source_key(metadata):
# #     """
# #     Create a stable source/document grouping key.

# #     PDF chunks:
# #         grouped primarily by pdf_file.

# #     Page chunks:
# #         grouped by URL/title.

# #     This allows the retrieval layer to recognize that several
# #     chunks belong to the same underlying document.
# #     """

# #     source_type = normalize(
# #         metadata.get("source_type")
# #     )

# #     pdf_file = normalize(
# #         metadata.get("pdf_file")
# #     )

# #     url = normalize(
# #         metadata.get("url")
# #     )

# #     title = normalize(
# #         metadata.get("title")
# #     )

# #     if source_type == "pdf" and pdf_file:
# #         return f"pdf::{pdf_file}"

# #     if url:
# #         return f"url::{url}"

# #     if title:
# #         return f"title::{title}"

# #     return "unknown"


# # def classify_confidence(results):
# #     """
# #     Classify retrieval confidence using the best distance.
# #     """

# #     if not results:
# #         return "none"

# #     best_distance = results[0]["distance"]

# #     if best_distance <= STRONG_DISTANCE:
# #         return "strong"

# #     if best_distance <= GOOD_DISTANCE:
# #         return "good"

# #     if best_distance <= MAX_DISTANCE:
# #         return "moderate"

# #     return "low"


# # def make_source_reference(result):
# #     """
# #     Produce a clean source-reference object.

# #     This is intentionally generated from retrieval metadata,
# #     NOT invented by the LLM.
# #     """

# #     metadata = result.get("metadata", {})

# #     source_type = normalize(
# #         metadata.get("source_type")
# #     )

# #     title = normalize(
# #         metadata.get("title")
# #     )

# #     url = normalize(
# #         metadata.get("url")
# #     )

# #     pdf_file = normalize(
# #         metadata.get("pdf_file")
# #     )

# #     page = safe_int(
# #         metadata.get("page")
# #     )

# #     reference = {
# #         "source_type": source_type,
# #         "title": title,
# #         "url": url,
# #         "pdf_file": pdf_file,
# #         "page": page if page > 0 else None,
# #     }

# #     return reference


# # def clean_result(result):
# #     """
# #     Convert Chroma result into a clean structure that the
# #     future LLM/API layer can directly consume.
# #     """

# #     metadata = result.get("metadata", {}) or {}

# #     return {
# #         "rank": result.get("rank"),
# #         "id": result.get("id"),
# #         "distance": result.get("distance"),
# #         "source_type": normalize(
# #             metadata.get("source_type")
# #         ),
# #         "title": normalize(
# #             metadata.get("title")
# #         ),
# #         "url": normalize(
# #             metadata.get("url")
# #         ),
# #         "pdf_file": normalize(
# #             metadata.get("pdf_file")
# #         ),
# #         "page": safe_int(
# #             metadata.get("page")
# #         ),
# #         "book": normalize(
# #             metadata.get("book")
# #         ),
# #         "temporal": bool(
# #             metadata.get("temporal", False)
# #         ),
# #         "quality_flag": normalize(
# #             metadata.get("quality_flag")
# #         ),
# #         "extraction_method": normalize(
# #             metadata.get("extraction_method")
# #         ),
# #         "categories": normalize(
# #             metadata.get("categories")
# #         ),
# #         "text": normalize(
# #             result.get("document")
# #         ),
# #     }


# # # ============================================================
# # # LOAD VECTOR STORE
# # # ============================================================

# # def load_collection():

# #     if not VECTORSTORE_DIR.exists():

# #         raise FileNotFoundError(
# #             "\nVector store was not found:\n"
# #             f"{VECTORSTORE_DIR}\n\n"
# #             "Run ingestion.py first."
# #         )

# #     print()
# #     print("Vector store:")
# #     print(VECTORSTORE_DIR)

# #     client = chromadb.PersistentClient(
# #         path=str(VECTORSTORE_DIR)
# #     )

# #     try:

# #         collection = client.get_collection(
# #             name=COLLECTION_NAME
# #         )

# #     except Exception as exc:

# #         raise RuntimeError(
# #             "\nChroma collection was not found:\n"
# #             f"{COLLECTION_NAME}\n\n"
# #             "Run ingestion.py first."
# #         ) from exc

# #     return collection


# # # ============================================================
# # # LOAD EMBEDDING MODEL
# # # ============================================================

# # def load_embedding_model():

# #     print()
# #     print(
# #         f"Loading embedding model: "
# #         f"{EMBEDDING_MODEL_NAME}"
# #     )

# #     model = SentenceTransformer(
# #         EMBEDDING_MODEL_NAME
# #     )

# #     return model


# # # ============================================================
# # # RAW RETRIEVAL
# # # ============================================================

# # def retrieve_candidates(
# #     collection,
# #     model,
# #     question,
# # ):

# #     query_text = build_query(question)

# #     query_embedding = model.encode(
# #         [query_text],
# #         normalize_embeddings=True,
# #         show_progress_bar=False,
# #     )

# #     result = collection.query(
# #         query_embeddings=query_embedding.tolist(),
# #         n_results=RETRIEVAL_CANDIDATES,
# #         include=[
# #             "documents",
# #             "metadatas",
# #             "distances",
# #         ],
# #     )

# #     ids = (
# #         result.get("ids", [[]])[0]
# #         if result.get("ids")
# #         else []
# #     )

# #     documents = (
# #         result.get("documents", [[]])[0]
# #         if result.get("documents")
# #         else []
# #     )

# #     metadatas = (
# #         result.get("metadatas", [[]])[0]
# #         if result.get("metadatas")
# #         else []
# #     )

# #     distances = (
# #         result.get("distances", [[]])[0]
# #         if result.get("distances")
# #         else []
# #     )

# #     candidates = []

# #     for index, chunk_id in enumerate(ids):

# #         distance = (
# #             distances[index]
# #             if index < len(distances)
# #             else None
# #         )

# #         metadata = (
# #             metadatas[index]
# #             if index < len(metadatas)
# #             else {}
# #         )

# #         document = (
# #             documents[index]
# #             if index < len(documents)
# #             else ""
# #         )

# #         candidates.append(
# #             {
# #                 "id": chunk_id,
# #                 "distance": distance,
# #                 "metadata": metadata or {},
# #                 "document": document or "",
# #             }
# #         )

# #     return candidates


# # # ============================================================
# # # FILTERING
# # # ============================================================

# # def filter_by_distance(candidates):

# #     filtered = []

# #     for candidate in candidates:

# #         distance = candidate.get("distance")

# #         if distance is None:
# #             continue

# #         if distance <= MAX_DISTANCE:
# #             filtered.append(candidate)

# #     return filtered


# # # ============================================================
# # # DUPLICATE / SOURCE CONTROL
# # # ============================================================

# # def deduplicate_results(candidates):

# #     """
# #     Remove exact duplicate chunk IDs.

# #     Chroma should already have unique IDs, but this defensive
# #     layer keeps retrieval output clean.
# #     """

# #     seen_ids = set()
# #     unique = []

# #     for candidate in candidates:

# #         chunk_id = candidate.get("id")

# #         if chunk_id in seen_ids:
# #             continue

# #         seen_ids.add(chunk_id)

# #         unique.append(candidate)

# #     return unique


# # def diversify_sources(candidates):

# #     """
# #     Prevent the first few results from being dominated by
# #     identical chunks from exactly the same source.

# #     We keep up to 4 results from one source initially, while
# #     still allowing additional results if the candidate pool
# #     is small.

# #     This is useful for questions such as:

# #         "What is the BS fee structure?"

# #     where pages 1, 2 and 240 may all be useful, but unrelated
# #     chunks from the same source should not overwhelm the
# #     retrieval list.
# #     """

# #     selected = []

# #     source_counts = {}

# #     # First pass: source diversity.
# #     for candidate in candidates:

# #         source_key = get_source_key(
# #             candidate.get("metadata", {})
# #         )

# #         count = source_counts.get(
# #             source_key,
# #             0,
# #         )

# #         if count >= 4:
# #             continue

# #         selected.append(candidate)

# #         source_counts[source_key] = count + 1

# #         if len(selected) >= FINAL_RESULTS:
# #             break

# #     # Second pass: fill if necessary.
# #     if len(selected) < FINAL_RESULTS:

# #         selected_ids = {
# #             item.get("id")
# #             for item in selected
# #         }

# #         for candidate in candidates:

# #             if candidate.get("id") in selected_ids:
# #                 continue

# #             selected.append(candidate)

# #             if len(selected) >= FINAL_RESULTS:
# #                 break

# #     return selected


# # # ============================================================
# # # FINAL RESULT BUILD
# # # ============================================================

# # def build_results(candidates):

# #     cleaned = []

# #     for rank, candidate in enumerate(
# #         candidates,
# #         start=1,
# #     ):

# #         item = clean_result(
# #             {
# #                 **candidate,
# #                 "rank": rank,
# #             }
# #         )

# #         item["source_reference"] = (
# #             make_source_reference(candidate)
# #         )

# #         cleaned.append(item)

# #     return cleaned


# # # ============================================================
# # # SOURCE SUMMARY
# # # ============================================================

# # def build_source_summary(results):

# #     sources = []

# #     seen = set()

# #     for result in results:

# #         reference = result.get(
# #             "source_reference",
# #             {},
# #         )

# #         key = (
# #             reference.get("source_type"),
# #             reference.get("title"),
# #             reference.get("url"),
# #             reference.get("pdf_file"),
# #         )

# #         if key in seen:
# #             continue

# #         seen.add(key)

# #         sources.append(
# #             reference
# #         )

# #     return sources


# # # ============================================================
# # # AUDIT
# # # ============================================================

# # def save_audit(
# #     question,
# #     results,
# #     confidence,
# #     candidate_count,
# # ):

# #     AUDIT_DIR.mkdir(
# #         parents=True,
# #         exist_ok=True,
# #     )

# #     audit = {
# #         "question": question,
# #         "embedding_model": EMBEDDING_MODEL_NAME,
# #         "query_prefix": BGE_QUERY_PREFIX,
# #         "collection": COLLECTION_NAME,
# #         "candidate_count": candidate_count,
# #         "final_result_count": len(results),
# #         "max_distance": MAX_DISTANCE,
# #         "confidence": confidence,
# #         "sources": build_source_summary(
# #             results
# #         ),
# #         "results": results,
# #     }

# #     with LAST_RETRIEVAL_FILE.open(
# #         "w",
# #         encoding="utf-8",
# #     ) as file:

# #         json.dump(
# #             audit,
# #             file,
# #             indent=2,
# #             ensure_ascii=False,
# #         )


# # # ============================================================
# # # DISPLAY
# # # ============================================================

# # def display_results(
# #     question,
# #     results,
# #     confidence,
# # ):

# #     print()
# #     print("=" * 78)
# #     print("RETRIEVAL RESULTS")
# #     print("=" * 78)

# #     print()
# #     print(
# #         f"Query      : {question}"
# #     )

# #     print(
# #         f"Confidence : {confidence.upper()}"
# #     )

# #     print(
# #         f"Results    : {len(results)}"
# #     )

# #     if not results:

# #         print()
# #         print(
# #             "[NO RELIABLE RESULTS]"
# #         )

# #         print(
# #             "The question did not produce sufficiently "
# #             "similar knowledge chunks."
# #         )

# #         return

# #     for result in results:

# #         print()
# #         print("-" * 78)

# #         print(
# #             f"RANK       : {result['rank']}"
# #         )

# #         print(
# #             f"ID         : {result['id']}"
# #         )

# #         print(
# #             f"DISTANCE   : {result['distance']}"
# #         )

# #         print(
# #             f"SOURCE TYPE: {result['source_type']}"
# #         )

# #         print(
# #             f"TITLE      : {result['title']}"
# #         )

# #         print(
# #             f"URL        : {result['url']}"
# #         )

# #         if result["pdf_file"]:

# #             print(
# #                 f"PDF FILE   : {result['pdf_file']}"
# #             )

# #         if result["page"]:

# #             print(
# #                 f"PAGE       : {result['page']}"
# #             )

# #         print(
# #             f"BOOK       : {result['book']}"
# #         )

# #         print(
# #             f"TEMPORAL   : {result['temporal']}"
# #         )

# #         print()
# #         print("TEXT:")

# #         print(
# #             result["text"]
# #         )

# #         print()
# #         print("SOURCE REFERENCE:")

# #         reference = result[
# #             "source_reference"
# #         ]

# #         print(
# #             f"  Title : {reference.get('title', '')}"
# #         )

# #         if reference.get("page"):

# #             print(
# #                 f"  Page  : {reference['page']}"
# #             )

# #         if reference.get("url"):

# #             print(
# #                 f"  URL   : {reference['url']}"
# #             )

# #     print()
# #     print("=" * 78)
# #     print(
# #         "AUDIT SAVED:"
# #     )
# #     print(
# #         LAST_RETRIEVAL_FILE
# #     )
# #     print("=" * 78)


# # # ============================================================
# # # RETRIEVE
# # # ============================================================

# # def retrieve(
# #     collection,
# #     model,
# #     question,
# # ):

# #     candidates = retrieve_candidates(
# #         collection,
# #         model,
# #         question,
# #     )

# #     # Lowest distance = best match.
# #     candidates.sort(
# #         key=lambda item: (
# #             item.get("distance")
# #             if item.get("distance") is not None
# #             else float("inf")
# #         )
# #     )

# #     # Remove weak matches.
# #     filtered = filter_by_distance(
# #         candidates
# #     )

# #     # Remove duplicate IDs.
# #     filtered = deduplicate_results(
# #         filtered
# #     )

# #     # Prefer source diversity.
# #     selected = diversify_sources(
# #         filtered
# #     )

# #     results = build_results(
# #         selected
# #     )

# #     confidence = classify_confidence(
# #         results
# #     )

# #     return (
# #         results,
# #         confidence,
# #         len(candidates),
# #     )


# # # ============================================================
# # # MAIN
# # # ============================================================

# # def main():

# #     print()
# #     print("=" * 78)
# #     print(
# #         "UET ADMISSION — IMPROVED SEMANTIC RETRIEVAL"
# #     )
# #     print("=" * 78)

# #     print()
# #     print(
# #         "Vector store:"
# #     )

# #     print(
# #         VECTORSTORE_DIR
# #     )

# #     print()
# #     print(
# #         "Collection:"
# #     )

# #     print(
# #         COLLECTION_NAME
# #     )

# #     collection = load_collection()

# #     count = collection.count()

# #     print()
# #     print(
# #         f"Vectors available: {count}"
# #     )

# #     if count == 0:

# #         raise RuntimeError(
# #             "ChromaDB collection is empty."
# #         )

# #     model = load_embedding_model()

# #     print()
# #     print("=" * 78)
# #     print("READY")
# #     print("=" * 78)

# #     print()
# #     print(
# #         "Ask a question."
# #     )

# #     print(
# #         "Type 'exit' to stop."
# #     )

# #     print()
# #     print(
# #         "Retrieval configuration:"
# #     )

# #     print(
# #         f"  Candidate results : "
# #         f"{RETRIEVAL_CANDIDATES}"
# #     )

# #     print(
# #         f"  Final results     : "
# #         f"{FINAL_RESULTS}"
# #     )

# #     print(
# #         f"  Max distance      : "
# #         f"{MAX_DISTANCE}"
# #     )

# #     print(
# #         f"  Query prefix      : "
# #         f"BGE instruction enabled"
# #     )

# #     while True:

# #         try:

# #             question = input(
# #                 "\nUser question: "
# #             ).strip()

# #         except (
# #             KeyboardInterrupt,
# #             EOFError,
# #         ):

# #             print()
# #             print(
# #                 "Exiting."
# #             )

# #             break

# #         if not question:

# #             continue

# #         if question.lower() in {
# #             "exit",
# #             "quit",
# #             "q",
# #         }:

# #             print()
# #             print(
# #                 "Exiting."
# #             )

# #             break

# #         try:

# #             (
# #                 results,
# #                 confidence,
# #                 candidate_count,
# #             ) = retrieve(
# #                 collection,
# #                 model,
# #                 question,
# #             )

# #             display_results(
# #                 question,
# #                 results,
# #                 confidence,
# #             )

# #             save_audit(
# #                 question,
# #                 results,
# #                 confidence,
# #                 candidate_count,
# #             )

# #         except Exception as exc:

# #             print()
# #             print(
# #                 "[ERROR]"
# #             )

# #             print(
# #                 str(exc)
# #             )


# # # ============================================================
# # # ENTRY POINT
# # # ============================================================

# # if __name__ == "__main__":
# #     main()


# # import json
# # import re
# # from pathlib import Path

# # import chromadb
# # from sentence_transformers import SentenceTransformer

# # # Import dynamic merit engine
# # from merit import load_latest_merit


# # # ============================================================
# # # UET CHATBOT — PRODUCTION RETRIEVER
# # # ============================================================
# # #
# # # ROUTING:
# # #
# # #   Merit question
# # #       ↓
# # #   Dynamic merit.py
# # #       ↓
# # #   Latest UET merit PDF
# # #
# # #   Normal question
# # #       ↓
# # #   ChromaDB
# # #       ↓
# # #   BGE semantic retrieval
# # #
# # # ============================================================


# # # ============================================================
# # # PROJECT PATHS
# # # ============================================================

# # PROJECT_ROOT = Path(r"D:\UET Chatbot")

# # VECTORSTORE_DIR = (
# #     PROJECT_ROOT
# #     / "data"
# #     / "vectorstore"
# #     / "chroma"
# # )

# # AUDIT_DIR = (
# #     PROJECT_ROOT
# #     / "data"
# #     / "retrieval"
# # )

# # LAST_RETRIEVAL_FILE = (
# #     AUDIT_DIR
# #     / "last_retrieval.json"
# # )


# # # ============================================================
# # # CHROMA CONFIGURATION
# # # ============================================================

# # EMBEDDING_MODEL_NAME = (
# #     "BAAI/bge-small-en-v1.5"
# # )

# # COLLECTION_NAME = (
# #     "uet_admission_knowledge"
# # )

# # RETRIEVAL_CANDIDATES = 20

# # FINAL_RESULTS = 8

# # MAX_DISTANCE = 0.78

# # STRONG_DISTANCE = 0.55

# # GOOD_DISTANCE = 0.65


# # # ============================================================
# # # BGE QUERY PREFIX
# # # ============================================================

# # BGE_QUERY_PREFIX = (
# #     "Represent this sentence for searching relevant passages: "
# # )


# # # ============================================================
# # # MERIT CONFIGURATION
# # # ============================================================



# # CAMPUS_ALIASES = {

# #     "lahore":
# #         "Main Campus (LHR)",

# #     "lhr":
# #         "Main Campus (LHR)",

# #     "lahore campus":
# #         "Main Campus (LHR)",

# #     "main campus":
# #         "Main Campus (LHR)",

# #     "ksk":
# #         "New Campus (KSK)",

# #     "new campus":
# #         "New Campus (KSK)",

# #     "new campus ksk":
# #         "New Campus (KSK)",

# #     "faisalabad":
# #         "Faislabad Campus",

# #     "faislabad":
# #         "Faislabad Campus",

# #     "faisalabad campus":
# #         "Faislabad Campus",

# #     "gujranwala":
# #         "Gujar anwala",

# #     "gujranwala campus":
# #         "Gujar anwala",

# #     "gujaranwala":
# #         "Gujar anwala",

# #     "narowal":
# #         "Narowal Campus (NWL)",

# #     "nwl":
# #         "Narowal Campus (NWL)",
# # }


# # CATEGORY_PATTERN = re.compile(
# #     r"\b(A1-M|A2-M|A1|A2|NM)\b",
# #     re.IGNORECASE,
# # )


# # # ============================================================
# # # GENERAL HELPERS
# # # ============================================================

# # def normalize(value):

# #     if value is None:
# #         return ""

# #     return re.sub(
# #         r"\s+",
# #         " ",
# #         str(value).strip(),
# #     )


# # def safe_int(value):

# #     try:
# #         return int(value)

# #     except (
# #         TypeError,
# #         ValueError,
# #     ):
# #         return 0


# # def build_query(question):

# #     question = normalize(
# #         question
# #     )

# #     if not question:
# #         return ""

# #     return (
# #         BGE_QUERY_PREFIX
# #         + question
# #     )


# # # ============================================================
# # # MERIT QUERY DETECTION
# # # ============================================================

# # def is_merit_question(question):

# #     text = normalize(question).lower()

# #     merit_keywords = [
# #         "merit",
# #         "aggregate",
# #         "selected",
# #         "selection",
# #         "cutoff",
# #         "cut off",
# #         "closing merit",
# #         "minimum aggregate",
# #         "last merit",
# #         "merit list",
# #         "merit check",
# #         "eligible",
# #         "can i get",
# #         "can i get admission",
# #         "will i get",
# #         "am i selected",
# #     ]

# #     if any(
# #         keyword in text
# #         for keyword in merit_keywords
# #     ):
# #         return True

# #     has_number = bool(
# #         re.search(
# #             r"\b\d{2}(?:\.\d+)?\b",
# #             text,
# #         )
# #     )

# #     has_campus = any(
# #         alias in text
# #         for alias in CAMPUS_ALIASES
# #     )

# #     if has_number and has_campus:
# #         return True

# #     return False


# # # ============================================================
# # # CAMPUS EXTRACTION
# # # ============================================================

# # def extract_campus(question):

# #     text = normalize(
# #         question
# #     ).lower()

# #     # Longest aliases first.
# #     aliases = sorted(
# #         CAMPUS_ALIASES.keys(),
# #         key=len,
# #         reverse=True,
# #     )

# #     for alias in aliases:

# #         if alias in text:

# #             return CAMPUS_ALIASES[
# #                 alias
# #             ]

# #     return None


# # # ============================================================
# # # CATEGORY EXTRACTION
# # # ============================================================

# # def extract_category(question):

# #     match = CATEGORY_PATTERN.search(
# #         question
# #     )

# #     if not match:
# #         return None

# #     return match.group(1).upper()


# # # ============================================================
# # # AGGREGATE EXTRACTION
# # # ============================================================

# # def extract_aggregate(question):

# #     text = normalize(
# #         question
# #     )

# #     # --------------------------------------------------------
# #     # Strong patterns first
# #     # --------------------------------------------------------

# #     patterns = [

# #         r"(?:aggregate|merit)\s*(?:is|of|=|:)?\s*"
# #         r"(\d{2}(?:\.\d+)?)",

# #         r"(\d{2}(?:\.\d+)?)\s*"
# #         r"(?:aggregate|merit)",

# #         r"(?:got|have|scored|score)\s*"
# #         r"(\d{2}(?:\.\d+)?)",

# #     ]

# #     for pattern in patterns:

# #         try:

# #             match = re.search(
# #                 pattern,
# #                 text,
# #                 re.IGNORECASE,
# #             )

# #         except re.error:
# #             continue

# #         if match:

# #             try:

# #                 value = float(
# #                     match.group(1)
# #                 )

# #                 if 0 <= value <= 100:
# #                     return value

# #             except ValueError:
# #                 pass

# #     # --------------------------------------------------------
# #     # General fallback
# #     # --------------------------------------------------------

# #     numbers = re.findall(
# #         r"\b\d{2}(?:\.\d+)?\b",
# #         text,
# #     )

# #     for number in numbers:

# #         try:

# #             value = float(
# #                 number
# #             )

# #             if 0 <= value <= 100:
# #                 return value

# #         except ValueError:
# #             continue

# #     return None


# # # ============================================================
# # # MERIT INTENT
# # # ============================================================

# # def parse_merit_query(question):

# #     return {
# #         "is_merit": is_merit_question(
# #             question
# #         ),

# #         "campus": extract_campus(
# #             question
# #         ),

# #         "category": extract_category(
# #             question
# #         ),

# #         "aggregate": extract_aggregate(
# #             question
# #         ),

# #         "program": "Computer Science",
# #     }


# # # ============================================================
# # # MERIT DATA FILTER
# # # ============================================================

# # def filter_cs_data(
# #     data,
# #     campus=None,
# #     category=None,
# # ):

# #     results = []

# #     for item in data:

# #         if normalize(
# #             item.get("program")
# #         ).lower() != "computer science":

# #             continue

# #         if campus:

# #             if (
# #                 normalize(
# #                     item.get("campus")
# #                 ).lower()
# #                 != normalize(
# #                     campus
# #                 ).lower()
# #             ):

# #                 continue

# #         if category:

# #             if (
# #                 normalize(
# #                     item.get("category")
# #                 ).upper()
# #                 != category.upper()
# #             ):

# #                 continue

# #         results.append(
# #             item
# #         )

# #     return results


# # # ============================================================
# # # MERIT RESPONSE
# # # ============================================================

# # def answer_merit_question(
# #     question,
# # ):

# #     intent = parse_merit_query(
# #         question
# #     )

# #     campus = intent[
# #         "campus"
# #     ]

# #     category = intent[
# #         "category"
# #     ]

# #     aggregate = intent[
# #         "aggregate"
# #     ]

# #     # --------------------------------------------------------
# #     # Current/latest merit data
# #     # --------------------------------------------------------

# #     merit = load_latest_merit()

# #     data = merit[
# #         "data"
# #     ]

# #     source_url = merit[
# #         "source_url"
# #     ]

# #     # --------------------------------------------------------
# #     # If campus wasn't specified
# #     #
# #     # Return all CS campuses.
# #     # --------------------------------------------------------

# #     records = filter_cs_data(
# #         data,
# #         campus=campus,
# #         category=category,
# #     )

# #     if not records:

# #         return {
# #             "type": "merit",
# #             "success": False,
# #             "message": (
# #                 "No current Computer Science "
# #                 "merit record was found for "
# #                 "the requested campus/category."
# #             ),
# #             "source_url": source_url,
# #             "records": [],
# #         }

# #     # --------------------------------------------------------
# #     # Student selection check
# #     # --------------------------------------------------------

# #     if aggregate is not None:

# #         checks = []

# #         for record in records:

# #             minimum = float(
# #                 record[
# #                     "minimum_aggregate"
# #                 ]
# #             )

# #             difference = (
# #                 aggregate
# #                 - minimum
# #             )

# #             selected = (
# #                 aggregate >= minimum
# #             )

# #             checks.append({

# #                 **record,

# #                 "student_aggregate":
# #                     aggregate,

# #                 "selected":
# #                     selected,

# #                 "difference":
# #                     round(
# #                         difference,
# #                         5,
# #                     ),
# #             })

# #         return {
# #             "type": "merit_check",
# #             "success": True,
# #             "message": (
# #                 "Latest UET merit data "
# #                 "was used."
# #             ),
# #             "source_url": source_url,
# #             "student_aggregate": aggregate,
# #             "records": checks,
# #         }

# #     # --------------------------------------------------------
# #     # Just merit lookup
# #     # --------------------------------------------------------

# #     return {
# #         "type": "merit",
# #         "success": True,
# #         "message": (
# #             "Latest UET merit data "
# #             "was used."
# #         ),
# #         "source_url": source_url,
# #         "records": records,
# #     }


# # # ============================================================
# # # CHROMA SOURCE HELPERS
# # # ============================================================

# # def get_source_key(
# #     metadata
# # ):

# #     source_type = normalize(
# #         metadata.get(
# #             "source_type"
# #         )
# #     )

# #     pdf_file = normalize(
# #         metadata.get(
# #             "pdf_file"
# #         )
# #     )

# #     url = normalize(
# #         metadata.get(
# #             "url"
# #         )
# #     )

# #     title = normalize(
# #         metadata.get(
# #             "title"
# #         )
# #     )

# #     if (
# #         source_type == "pdf"
# #         and pdf_file
# #     ):

# #         return (
# #             f"pdf::{pdf_file}"
# #         )

# #     if url:

# #         return (
# #             f"url::{url}"
# #         )

# #     if title:

# #         return (
# #             f"title::{title}"
# #         )

# #     return "unknown"


# # def classify_confidence(
# #     results
# # ):

# #     if not results:
# #         return "none"

# #     best_distance = results[
# #         0
# #     ]["distance"]

# #     if (
# #         best_distance
# #         <= STRONG_DISTANCE
# #     ):

# #         return "strong"

# #     if (
# #         best_distance
# #         <= GOOD_DISTANCE
# #     ):

# #         return "good"

# #     if (
# #         best_distance
# #         <= MAX_DISTANCE
# #     ):

# #         return "moderate"

# #     return "low"


# # # ============================================================
# # # SOURCE REFERENCE
# # # ============================================================

# # def make_source_reference(
# #     result
# # ):

# #     metadata = result.get(
# #         "metadata",
# #         {},
# #     )

# #     source_type = normalize(
# #         metadata.get(
# #             "source_type"
# #         )
# #     )

# #     title = normalize(
# #         metadata.get(
# #             "title"
# #         )
# #     )

# #     url = normalize(
# #         metadata.get(
# #             "url"
# #         )
# #     )

# #     pdf_file = normalize(
# #         metadata.get(
# #             "pdf_file"
# #         )
# #     )

# #     page = safe_int(
# #         metadata.get(
# #             "page"
# #         )
# #     )

# #     return {
# #         "source_type":
# #             source_type,

# #         "title":
# #             title,

# #         "url":
# #             url,

# #         "pdf_file":
# #             pdf_file,

# #         "page":
# #             page
# #             if page > 0
# #             else None,
# #     }


# # # ============================================================
# # # CLEAN CHROMA RESULT
# # # ============================================================

# # def clean_result(
# #     result
# # ):

# #     metadata = (
# #         result.get(
# #             "metadata",
# #             {},
# #         )
# #         or {}
# #     )

# #     return {

# #         "rank":
# #             result.get(
# #                 "rank"
# #             ),

# #         "id":
# #             result.get(
# #                 "id"
# #             ),

# #         "distance":
# #             result.get(
# #                 "distance"
# #             ),

# #         "source_type":
# #             normalize(
# #                 metadata.get(
# #                     "source_type"
# #                 )
# #             ),

# #         "title":
# #             normalize(
# #                 metadata.get(
# #                     "title"
# #                 )
# #             ),

# #         "url":
# #             normalize(
# #                 metadata.get(
# #                     "url"
# #                 )
# #             ),

# #         "pdf_file":
# #             normalize(
# #                 metadata.get(
# #                     "pdf_file"
# #                 )
# #             ),

# #         "page":
# #             safe_int(
# #                 metadata.get(
# #                     "page"
# #                 )
# #             ),

# #         "book":
# #             normalize(
# #                 metadata.get(
# #                     "book"
# #                 )
# #             ),

# #         "temporal":
# #             bool(
# #                 metadata.get(
# #                     "temporal",
# #                     False,
# #                 )
# #             ),

# #         "quality_flag":
# #             normalize(
# #                 metadata.get(
# #                     "quality_flag"
# #                 )
# #             ),

# #         "extraction_method":
# #             normalize(
# #                 metadata.get(
# #                     "extraction_method"
# #                 )
# #             ),

# #         "categories":
# #             normalize(
# #                 metadata.get(
# #                     "categories"
# #                 )
# #             ),

# #         "text":
# #             normalize(
# #                 result.get(
# #                     "document"
# #                 )
# #             ),
# #     }


# # # ============================================================
# # # LOAD CHROMA
# # # ============================================================

# # def load_collection():

# #     if not VECTORSTORE_DIR.exists():

# #         raise FileNotFoundError(
# #             "\nVector store was not found:\n"
# #             f"{VECTORSTORE_DIR}\n\n"
# #             "Run ingestion.py first."
# #         )

# #     client = (
# #         chromadb.PersistentClient(
# #             path=str(
# #                 VECTORSTORE_DIR
# #             )
# #         )
# #     )

# #     try:

# #         collection = (
# #             client.get_collection(
# #                 name=COLLECTION_NAME
# #             )
# #         )

# #     except Exception as exc:

# #         raise RuntimeError(
# #             "\nChroma collection was not found:\n"
# #             f"{COLLECTION_NAME}\n\n"
# #             "Run ingestion.py first."
# #         ) from exc

# #     return collection


# # # ============================================================
# # # LOAD EMBEDDING MODEL
# # # ============================================================

# # def load_embedding_model():

# #     print()
# #     print(
# #         "Loading embedding model:"
# #     )

# #     print(
# #         EMBEDDING_MODEL_NAME
# #     )

# #     return SentenceTransformer(
# #         EMBEDDING_MODEL_NAME
# #     )


# # # ============================================================
# # # RAW CHROMA RETRIEVAL
# # # ============================================================

# # def retrieve_candidates(
# #     collection,
# #     model,
# #     question,
# # ):

# #     query_text = build_query(
# #         question
# #     )

# #     query_embedding = (
# #         model.encode(
# #             [query_text],
# #             normalize_embeddings=True,
# #             show_progress_bar=False,
# #         )
# #     )

# #     result = collection.query(

# #         query_embeddings=
# #             query_embedding.tolist(),

# #         n_results=
# #             RETRIEVAL_CANDIDATES,

# #         include=[
# #             "documents",
# #             "metadatas",
# #             "distances",
# #         ],
# #     )

# #     ids = (
# #         result.get(
# #             "ids",
# #             [[]],
# #         )[0]
# #         if result.get("ids")
# #         else []
# #     )

# #     documents = (
# #         result.get(
# #             "documents",
# #             [[]],
# #         )[0]
# #         if result.get("documents")
# #         else []
# #     )

# #     metadatas = (
# #         result.get(
# #             "metadatas",
# #             [[]],
# #         )[0]
# #         if result.get("metadatas")
# #         else []
# #     )

# #     distances = (
# #         result.get(
# #             "distances",
# #             [[]],
# #         )[0]
# #         if result.get("distances")
# #         else []
# #     )

# #     candidates = []

# #     for index, chunk_id in enumerate(
# #         ids
# #     ):

# #         candidates.append({

# #             "id":
# #                 chunk_id,

# #             "distance":
# #                 distances[index]
# #                 if index < len(
# #                     distances
# #                 )
# #                 else None,

# #             "metadata":
# #                 metadatas[index]
# #                 if index < len(
# #                     metadatas
# #                 )
# #                 else {},

# #             "document":
# #                 documents[index]
# #                 if index < len(
# #                     documents
# #                 )
# #                 else "",
# #         })

# #     return candidates


# # # ============================================================
# # # DISTANCE FILTER
# # # ============================================================

# # def filter_by_distance(
# #     candidates
# # ):

# #     return [

# #         candidate

# #         for candidate in candidates

# #         if (
# #             candidate.get(
# #                 "distance"
# #             )
# #             is not None
# #             and
# #             candidate.get(
# #                 "distance"
# #             )
# #             <= MAX_DISTANCE
# #         )

# #     ]


# # # ============================================================
# # # DEDUPLICATION
# # # ============================================================

# # def deduplicate_results(
# #     candidates
# # ):

# #     seen = set()

# #     results = []

# #     for candidate in candidates:

# #         chunk_id = candidate.get(
# #             "id"
# #         )

# #         if chunk_id in seen:
# #             continue

# #         seen.add(
# #             chunk_id
# #         )

# #         results.append(
# #             candidate
# #         )

# #     return results


# # # ============================================================
# # # SOURCE DIVERSIFICATION
# # # ============================================================

# # def diversify_sources(
# #     candidates
# # ):

# #     selected = []

# #     source_counts = {}

# #     for candidate in candidates:

# #         source_key = get_source_key(
# #             candidate.get(
# #                 "metadata",
# #                 {},
# #             )
# #         )

# #         count = source_counts.get(
# #             source_key,
# #             0,
# #         )

# #         if count >= 4:
# #             continue

# #         selected.append(
# #             candidate
# #         )

# #         source_counts[
# #             source_key
# #         ] = count + 1

# #         if (
# #             len(selected)
# #             >= FINAL_RESULTS
# #         ):
# #             break

# #     # Fill remaining slots
# #     if (
# #         len(selected)
# #         < FINAL_RESULTS
# #     ):

# #         selected_ids = {
# #             item.get("id")
# #             for item in selected
# #         }

# #         for candidate in candidates:

# #             if (
# #                 candidate.get("id")
# #                 in selected_ids
# #             ):
# #                 continue

# #             selected.append(
# #                 candidate
# #             )

# #             if (
# #                 len(selected)
# #                 >= FINAL_RESULTS
# #             ):
# #                 break

# #     return selected


# # # ============================================================
# # # BUILD CHROMA RESULTS
# # # ============================================================

# # def build_results(
# #     candidates
# # ):

# #     results = []

# #     for rank, candidate in enumerate(
# #         candidates,
# #         start=1,
# #     ):

# #         item = clean_result({

# #             **candidate,

# #             "rank":
# #                 rank,
# #         })

# #         item[
# #             "source_reference"
# #         ] = make_source_reference(
# #             candidate
# #         )

# #         results.append(
# #             item
# #         )

# #     return results


# # # ============================================================
# # # SOURCE SUMMARY
# # # ============================================================

# # def build_source_summary(
# #     results
# # ):

# #     sources = []

# #     seen = set()

# #     for result in results:

# #         reference = result.get(
# #             "source_reference",
# #             {},
# #         )

# #         key = (

# #             reference.get(
# #                 "source_type"
# #             ),

# #             reference.get(
# #                 "title"
# #             ),

# #             reference.get(
# #                 "url"
# #             ),

# #             reference.get(
# #                 "pdf_file"
# #             ),
# #         )

# #         if key in seen:
# #             continue

# #         seen.add(
# #             key
# #         )

# #         sources.append(
# #             reference
# #         )

# #     return sources


# # # ============================================================
# # # SAVE AUDIT
# # # ============================================================

# # def save_audit(
# #     question,
# #     results,
# #     confidence,
# #     candidate_count,
# # ):

# #     AUDIT_DIR.mkdir(
# #         parents=True,
# #         exist_ok=True,
# #     )

# #     audit = {

# #         "question":
# #             question,

# #         "embedding_model":
# #             EMBEDDING_MODEL_NAME,

# #         "query_prefix":
# #             BGE_QUERY_PREFIX,

# #         "collection":
# #             COLLECTION_NAME,

# #         "candidate_count":
# #             candidate_count,

# #         "final_result_count":
# #             len(results),

# #         "max_distance":
# #             MAX_DISTANCE,

# #         "confidence":
# #             confidence,

# #         "sources":
# #             build_source_summary(
# #                 results
# #             ),

# #         "results":
# #             results,
# #     }

# #     with LAST_RETRIEVAL_FILE.open(
# #         "w",
# #         encoding="utf-8",
# #     ) as file:

# #         json.dump(
# #             audit,
# #             file,
# #             indent=2,
# #             ensure_ascii=False,
# #         )


# # # ============================================================
# # # DISPLAY MERIT RESPONSE
# # # ============================================================

# # def display_merit_response(
# #     response
# # ):

# #     print()
# #     print("=" * 80)
# #     print(
# #         "CURRENT UET MERIT RESULT"
# #     )
# #     print("=" * 80)

# #     print()

# #     print(
# #         response.get(
# #             "message",
# #             "",
# #         )
# #     )

# #     source_url = response.get(
# #         "source_url"
# #     )

# #     if source_url:

# #         print()
# #         print(
# #             "SOURCE:"
# #         )

# #         print(
# #             source_url
# #         )

# #     records = response.get(
# #         "records",
# #         [],
# #     )

# #     if not records:

# #         print()
# #         print(
# #             "No matching records."
# #         )

# #         return

# #     for record in records:

# #         print()
# #         print(
# #             "-" * 80
# #         )

# #         print(
# #             f"Campus       : "
# #             f"{record['campus']}"
# #         )

# #         print(
# #             f"Program      : "
# #             f"{record['program']}"
# #         )

# #         print(
# #             f"Category     : "
# #             f"{record['category']}"
# #         )

# #         print(
# #             f"Session      : "
# #             f"{record['session']}"
# #         )

# #         print(
# #             f"Type         : "
# #             f"{record['type']}"
# #         )

# #         print(
# #             f"Minimum Merit: "
# #             f"{record['minimum_aggregate']:.5f}"
# #         )

# #         if (
# #             "student_aggregate"
# #             in record
# #         ):

# #             print(
# #                 f"Student       : "
# #                 f"{record['student_aggregate']:.5f}"
# #             )

# #             print(
# #                 f"Difference    : "
# #                 f"{record['difference']:+.5f}"
# #             )

# #             if record["selected"]:

# #                 print(
# #                     "STATUS        : "
# #                     "SELECTED / ABOVE CURRENT MERIT"
# #                 )

# #             else:

# #                 print(
# #                     "STATUS        : "
# #                     "BELOW CURRENT MERIT"
# #                 )

# #         if record.get(
# #             "page"
# #         ):

# #             print(
# #                 f"PDF Page      : "
# #                 f"{record['page']}"
# #             )


# # # ============================================================
# # # DISPLAY NORMAL RETRIEVAL
# # # ============================================================

# # def display_results(
# #     question,
# #     results,
# #     confidence,
# # ):

# #     print()
# #     print("=" * 78)
# #     print(
# #         "SEMANTIC RETRIEVAL RESULTS"
# #     )
# #     print("=" * 78)

# #     print()
# #     print(
# #         f"Query      : {question}"
# #     )

# #     print(
# #         f"Confidence : {confidence.upper()}"
# #     )

# #     print(
# #         f"Results    : {len(results)}"
# #     )

# #     if not results:

# #         print()
# #         print(
# #             "[NO RELIABLE RESULTS]"
# #         )

# #         return

# #     for result in results:

# #         print()
# #         print(
# #             "-" * 78
# #         )

# #         print(
# #             f"RANK       : "
# #             f"{result['rank']}"
# #         )

# #         print(
# #             f"DISTANCE   : "
# #             f"{result['distance']}"
# #         )

# #         print(
# #             f"SOURCE TYPE: "
# #             f"{result['source_type']}"
# #         )

# #         print(
# #             f"TITLE      : "
# #             f"{result['title']}"
# #         )

# #         if result["url"]:

# #             print(
# #                 f"URL        : "
# #                 f"{result['url']}"
# #             )

# #         if result["pdf_file"]:

# #             print(
# #                 f"PDF FILE   : "
# #                 f"{result['pdf_file']}"
# #             )

# #         if result["page"]:

# #             print(
# #                 f"PAGE       : "
# #                 f"{result['page']}"
# #             )

# #         print()
# #         print(
# #             "TEXT:"
# #         )

# #         print(
# #             result["text"]
# #         )


# # # ============================================================
# # # NORMAL RETRIEVE
# # # ============================================================

# # def retrieve_normal(
# #     collection,
# #     model,
# #     question,
# # ):

# #     candidates = retrieve_candidates(
# #         collection,
# #         model,
# #         question,
# #     )

# #     candidates.sort(
# #         key=lambda item: (
# #             item.get(
# #                 "distance"
# #             )
# #             if item.get(
# #                 "distance"
# #             ) is not None
# #             else float("inf")
# #         )
# #     )

# #     filtered = filter_by_distance(
# #         candidates
# #     )

# #     filtered = deduplicate_results(
# #         filtered
# #     )

# #     selected = diversify_sources(
# #         filtered
# #     )

# #     results = build_results(
# #         selected
# #     )

# #     confidence = classify_confidence(
# #         results
# #     )

# #     return (
# #         results,
# #         confidence,
# #         len(candidates),
# #     )


# # # ============================================================
# # # MAIN ROUTER
# # # ============================================================

# # def route_question(
# #     question,
# #     collection,
# #     model,
# # ):

# #     question = normalize(
# #         question
# #     )

# #     # --------------------------------------------------------
# #     # MERIT ROUTE
# #     # --------------------------------------------------------

# #     if is_merit_question(
# #         question
# #     ):

# #         print()
# #         print(
# #             "[ROUTER] Merit question detected."
# #         )

# #         print(
# #             "[ROUTER] Using latest UET merit data."
# #         )

# #         response = answer_merit_question(
# #             question
# #         )

# #         return {
# #             "route":
# #                 "merit",

# #             "response":
# #                 response,
# #         }

# #     # --------------------------------------------------------
# #     # NORMAL SEMANTIC ROUTE
# #     # --------------------------------------------------------

# #     print()
# #     print(
# #         "[ROUTER] Normal knowledge question."
# #     )

# #     (
# #         results,
# #         confidence,
# #         candidate_count,
# #     ) = retrieve_normal(
# #         collection,
# #         model,
# #         question,
# #     )

# #     save_audit(
# #         question,
# #         results,
# #         confidence,
# #         candidate_count,
# #     )

# #     return {
# #         "route":
# #             "semantic",

# #         "results":
# #             results,

# #         "confidence":
# #             confidence,
# #     }


# # # ============================================================
# # # MAIN
# # # ============================================================

# # def main():

# #     print()
# #     print("=" * 80)
# #     print(
# #         "UET CHATBOT — PRODUCTION RETRIEVER"
# #     )
# #     print("=" * 80)

# #     print()
# #     print(
# #         "Routes:"
# #     )

# #     print(
# #         "  Merit questions  -> Dynamic latest UET merit"
# #     )

# #     print(
# #         "  Other questions  -> ChromaDB semantic search"
# #     )

# #     # --------------------------------------------------------
# #     # Load Chroma
# #     # --------------------------------------------------------

# #     collection = load_collection()

# #     count = collection.count()

# #     print()
# #     print(
# #         f"Vectors available: {count}"
# #     )

# #     if count == 0:

# #         raise RuntimeError(
# #             "ChromaDB collection is empty."
# #         )

# #     # --------------------------------------------------------
# #     # Load embedding model
# #     # --------------------------------------------------------

# #     model = load_embedding_model()

# #     print()
# #     print("=" * 80)
# #     print(
# #         "READY"
# #     )
# #     print("=" * 80)

# #     print()
# #     print(
# #         "Examples:"
# #     )

# #     print(
# #         "  Lahore CS merit?"
# #     )

# #     print(
# #         "  My aggregate is 90, am I selected for CS Lahore?"
# #     )

# #     print(
# #         "  KSK CS merit A1?"
# #     )

# #     print(
# #         "  What is UET admission process?"
# #     )

# #     print(
# #         "  exit"
# #     )

# #     while True:

# #         try:

# #             question = input(
# #                 "\nUser question: "
# #             ).strip()

# #         except (
# #             KeyboardInterrupt,
# #             EOFError,
# #         ):

# #             print()
# #             print(
# #                 "Exiting."
# #             )

# #             break

# #         if not question:
# #             continue

# #         if question.lower() in {
# #             "exit",
# #             "quit",
# #             "q",
# #         }:

# #             print()
# #             print(
# #                 "Exiting."
# #             )

# #             break

# #         try:

# #             result = route_question(
# #                 question,
# #                 collection,
# #                 model,
# #             )

# #             # ------------------------------------------------
# #             # MERIT
# #             # ------------------------------------------------

# #             if (
# #                 result["route"]
# #                 == "merit"
# #             ):

# #                 display_merit_response(
# #                     result["response"]
# #                 )

# #             # ------------------------------------------------
# #             # NORMAL
# #             # ------------------------------------------------

# #             else:

# #                 display_results(
# #                     question,
# #                     result["results"],
# #                     result["confidence"],
# #                 )

# #         except Exception as exc:

# #             print()
# #             print(
# #                 "=" * 80
# #             )

# #             print(
# #                 "[ERROR]"
# #             )

# #             print(
# #                 str(exc)
# #             )

# #             print(
# #                 "=" * 80
# #             )


# # # ============================================================
# # # ENTRY POINT
# # # ============================================================

# # if __name__ == "__main__":

# #     main()






# import json
# import re
# from pathlib import Path

# import chromadb
# from sentence_transformers import SentenceTransformer

# # Dynamic merit engine
# from merit import load_latest_merit


# # ============================================================
# # UET CHATBOT — PRODUCTION RETRIEVER
# # ============================================================
# #
# # ROUTING
# #
# # Merit / closing merit / aggregate question
# #       ↓
# #       merit.py
# #       ↓
# # Latest UET merit-list PDF
# #
# # Normal admission question
# #       ↓
# # ChromaDB
# #       ↓
# # BGE semantic retrieval
# #
# # IMPORTANT:
# #
# # This file does NOT download merit PDFs itself.
# #
# # merit.py is responsible for:
# #   - finding latest merit-list PDF
# #   - downloading it
# #   - extracting merit records
# #
# # This file is responsible for:
# #   - detecting merit intent
# #   - extracting campus / program / category / aggregate
# #   - routing
# #   - normal Chroma retrieval
# #   - audit logging
# #
# # ============================================================


# # ============================================================
# # PROJECT PATHS
# # ============================================================

# PROJECT_ROOT = Path(r"D:\UET Chatbot")

# VECTORSTORE_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "vectorstore"
#     / "chroma"
# )

# AUDIT_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "retrieval"
# )

# LAST_RETRIEVAL_FILE = (
#     AUDIT_DIR
#     / "last_retrieval.json"
# )


# # ============================================================
# # CHROMA CONFIGURATION
# # ============================================================

# EMBEDDING_MODEL_NAME = (
#     "BAAI/bge-small-en-v1.5"
# )

# COLLECTION_NAME = (
#     "uet_admission_knowledge"
# )

# RETRIEVAL_CANDIDATES = 20

# FINAL_RESULTS = 8

# MAX_DISTANCE = 0.78

# STRONG_DISTANCE = 0.55

# GOOD_DISTANCE = 0.65


# # ============================================================
# # BGE QUERY PREFIX
# # ============================================================

# BGE_QUERY_PREFIX = (
#     "Represent this sentence for searching relevant passages: "
# )


# # ============================================================
# # CAMPUS ALIASES
# # ============================================================

# CAMPUS_ALIASES = {

#     "lahore":
#         "Main Campus (LHR)",

#     "lhr":
#         "Main Campus (LHR)",

#     "lahore campus":
#         "Main Campus (LHR)",

#     "main campus":
#         "Main Campus (LHR)",

#     "main campus lhr":
#         "Main Campus (LHR)",

#     "ksk":
#         "New Campus (KSK)",

#     "new campus":
#         "New Campus (KSK)",

#     "new campus ksk":
#         "New Campus (KSK)",

#     "faisalabad":
#         "Faislabad Campus",

#     "faislabad":
#         "Faislabad Campus",

#     "faisalabad campus":
#         "Faislabad Campus",

#     "gujranwala":
#         "Gujar anwala",

#     "gujaranwala":
#         "Gujar anwala",

#     "gujranwala campus":
#         "Gujar anwala",

#     "narowal":
#         "Narowal Campus (NWL)",

#     "nwl":
#         "Narowal Campus (NWL)",

#     "narowal campus":
#         "Narowal Campus (NWL)",
# }


# # ============================================================
# # CATEGORY
# # ============================================================

# CATEGORY_PATTERN = re.compile(
#     r"\b(A1-M|A2-M|A1|A2|NM)\b",
#     re.IGNORECASE,
# )


# # ============================================================
# # COMMON PROGRAM ALIASES
# # ============================================================
# #
# # This is ONLY for understanding user questions.
# #
# # The actual official program name comes from merit.py data.
# #
# # ============================================================

# PROGRAM_ALIASES = {

#     "computer science":
#         "Computer Science",

#     "cs":
#         "Computer Science",

#     "computer engineering":
#         "Computer Engineering",

#     "ce":
#         "Computer Engineering",

#     "software engineering":
#         "Software Engineering",

#     "se":
#         "Software Engineering",

#     "electrical engineering":
#         "Electrical Engineering",

#     "ee":
#         "Electrical Engineering",

#     "mechanical engineering":
#         "Mechanical Engineering",

#     "me":
#         "Mechanical Engineering",

#     "civil engineering":
#         "Civil Engineering",

#     "civil":
#         "Civil Engineering",

#     "chemical engineering":
#         "Chemical Engineering",

#     "architecture":
#         "Architecture",

#     "architectural engineering":
#         "Architectural Engineering",

#     "environmental engineering":
#         "Environmental Engineering",

#     "industrial engineering":
#         "Industrial Engineering",

#     "transportation engineering":
#         "Transportation Engineering",

#     "petroleum engineering":
#         "Petroleum Engineering",

#     "mining engineering":
#         "Mining Engineering",

#     "mechatronics":
#         "Mechatronics",

#     "biomedical engineering":
#         "Biomedical Engineering",

#     "food engineering":
#         "Food Engineering",

#     "metallurgical engineering":
#         "Metallurgical Engineering",
# }


# # ============================================================
# # MERIT KEYWORDS
# # ============================================================

# MERIT_KEYWORDS = [

#     "merit",

#     "aggregate",

#     "selected",

#     "selection",

#     "closing merit",

#     "cutoff",

#     "cut off",

#     "minimum merit",

#     "minimum aggregate",

#     "last merit",

#     "merit list",

#     "meritlist",

#     "closing aggregate",

#     "above merit",

#     "below merit",

#     "my aggregate",

#     "my merit",

#     "can i get admission",

#     "can i get in",

#     "will i get admission",

#     "am i selected",

#     "got selected",

# ]


# # ============================================================
# # GENERAL HELPERS
# # ============================================================

# def normalize(value):

#     if value is None:
#         return ""

#     return re.sub(
#         r"\s+",
#         " ",
#         str(value).strip(),
#     )


# def safe_int(value):

#     try:
#         return int(value)

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0


# def safe_float(value):

#     try:
#         return float(value)

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return None


# def build_query(question):

#     question = normalize(
#         question
#     )

#     if not question:
#         return ""

#     return (
#         BGE_QUERY_PREFIX
#         + question
#     )


# # ============================================================
# # MERIT QUESTION DETECTION
# # ============================================================

# def is_merit_question(question):

#     text = normalize(
#         question
#     ).lower()

#     # --------------------------------------------------------
#     # Explicit merit language
#     # --------------------------------------------------------

#     if any(
#         keyword in text
#         for keyword in MERIT_KEYWORDS
#     ):
#         return True

#     # --------------------------------------------------------
#     # Aggregate number + program/campus
#     #
#     # Example:
#     #
#     # 90 CS Lahore
#     # 88 Electrical KSK
#     # 85 Civil Faisalabad
#     # --------------------------------------------------------

#     has_number = bool(
#         re.search(
#             r"\b\d{2}(?:\.\d+)?\b",
#             text,
#         )
#     )

#     has_campus = any(
#         alias in text
#         for alias in CAMPUS_ALIASES
#     )

#     has_program = any(
#         alias in text
#         for alias in PROGRAM_ALIASES
#     )

#     if (
#         has_number
#         and
#         (
#             has_campus
#             or has_program
#         )
#     ):
#         return True

#     return False


# # ============================================================
# # CAMPUS EXTRACTION
# # ============================================================

# def extract_campus(question):

#     text = normalize(
#         question
#     ).lower()

#     aliases = sorted(
#         CAMPUS_ALIASES.keys(),
#         key=len,
#         reverse=True,
#     )

#     for alias in aliases:

#         if alias in text:

#             return CAMPUS_ALIASES[
#                 alias
#             ]

#     return None


# # ============================================================
# # CATEGORY EXTRACTION
# # ============================================================

# def extract_category(question):

#     match = CATEGORY_PATTERN.search(
#         question
#     )

#     if not match:
#         return None

#     return match.group(1).upper()


# # ============================================================
# # AGGREGATE EXTRACTION
# # ============================================================

# def extract_aggregate(question):

#     text = normalize(
#         question
#     )

#     patterns = [

#         # aggregate is 90
#         r"(?:aggregate|merit)"
#         r"\s*(?:is|of|=|:)?\s*"
#         r"(\d{2}(?:\.\d+)?)",

#         # 90 aggregate
#         r"(\d{2}(?:\.\d+)?)"
#         r"\s*(?:aggregate|merit)",

#         # I have 90
#         r"(?:got|have|scored|score|aggregate\s+is)"
#         r"\s*(?:=|:)?\s*"
#         r"(\d{2}(?:\.\d+)?)",

#         # am I selected with 90
#         r"(?:with)"
#         r"\s*(\d{2}(?:\.\d+)?)",

#     ]

#     for pattern in patterns:

#         match = re.search(
#             pattern,
#             text,
#             re.IGNORECASE,
#         )

#         if match:

#             value = safe_float(
#                 match.group(1)
#             )

#             if (
#                 value is not None
#                 and
#                 0 <= value <= 100
#             ):

#                 return value

#     # --------------------------------------------------------
#     # General fallback
#     # --------------------------------------------------------

#     numbers = re.findall(
#         r"\b\d{2}(?:\.\d+)?\b",
#         text,
#     )

#     for number in numbers:

#         value = safe_float(
#             number
#         )

#         if (
#             value is not None
#             and
#             0 <= value <= 100
#         ):

#             return value

#     return None


# # ============================================================
# # PROGRAM EXTRACTION
# # ============================================================

# def extract_program(question):

#     text = normalize(
#         question
#     ).lower()

#     aliases = sorted(
#         PROGRAM_ALIASES.keys(),
#         key=len,
#         reverse=True,
#     )

#     for alias in aliases:

#         # Word boundary for short aliases
#         if len(alias) <= 3:

#             pattern = (
#                 r"\b"
#                 + re.escape(alias)
#                 + r"\b"
#             )

#             if re.search(
#                 pattern,
#                 text,
#             ):

#                 return PROGRAM_ALIASES[
#                     alias
#                 ]

#         else:

#             if alias in text:

#                 return PROGRAM_ALIASES[
#                     alias
#                 ]

#     return None


# # ============================================================
# # MERIT INTENT
# # ============================================================

# def parse_merit_query(question):

#     return {

#         "is_merit":
#             is_merit_question(
#                 question
#             ),

#         "campus":
#             extract_campus(
#                 question
#             ),

#         "category":
#             extract_category(
#                 question
#             ),

#         "aggregate":
#             extract_aggregate(
#                 question
#             ),

#         "program":
#             extract_program(
#                 question
#             ),
#     }


# # ============================================================
# # NORMALIZE PROGRAM FOR COMPARISON
# # ============================================================

# def normalize_program_name(
#     value
# ):

#     text = normalize(
#         value
#     ).lower()

#     text = re.sub(
#         r"\([^)]*\)",
#         "",
#         text,
#     )

#     text = re.sub(
#         r"[^a-z0-9]+",
#         " ",
#         text,
#     )

#     return normalize(
#         text
#     )


# # ============================================================
# # PROGRAM MATCH
# # ============================================================

# def program_matches(
#     record_program,
#     requested_program,
# ):

#     if not requested_program:
#         return True

#     actual = normalize_program_name(
#         record_program
#     )

#     requested = normalize_program_name(
#         requested_program
#     )

#     if not actual or not requested:
#         return False

#     return (
#         actual == requested
#         or requested in actual
#         or actual in requested
#     )


# # ============================================================
# # CAMPUS MATCH
# # ============================================================

# def campus_matches(
#     record_campus,
#     requested_campus,
# ):

#     if not requested_campus:
#         return True

#     actual = normalize(
#         record_campus
#     ).lower()

#     requested = normalize(
#         requested_campus
#     ).lower()

#     return (
#         actual == requested
#         or requested in actual
#         or actual in requested
#     )


# # ============================================================
# # CATEGORY MATCH
# # ============================================================

# def category_matches(
#     record_category,
#     requested_category,
# ):

#     if not requested_category:
#         return True

#     return (
#         normalize(
#             record_category
#         ).lower()
#         ==
#         normalize(
#             requested_category
#         ).lower()
#     )


# # ============================================================
# # GENERIC MERIT DATA FILTER
# # ============================================================

# def filter_merit_data(
#     data,
#     program=None,
#     campus=None,
#     category=None,
# ):

#     results = []

#     for item in data:

#         if not isinstance(
#             item,
#             dict,
#         ):
#             continue

#         record_program = item.get(
#             "program",
#             item.get(
#                 "discipline",
#                 "",
#             ),
#         )

#         record_campus = item.get(
#             "campus",
#             "",
#         )

#         record_category = item.get(
#             "category",
#             "",
#         )

#         if not program_matches(
#             record_program,
#             program,
#         ):
#             continue

#         if not campus_matches(
#             record_campus,
#             campus,
#         ):
#             continue

#         if not category_matches(
#             record_category,
#             category,
#         ):
#             continue

#         results.append(
#             item
#         )

#     return results


# # ============================================================
# # MERIT RESPONSE
# # ============================================================

# def answer_merit_question(
#     question
# ):

#     intent = parse_merit_query(
#         question
#     )

#     program = intent[
#         "program"
#     ]

#     campus = intent[
#         "campus"
#     ]

#     category = intent[
#         "category"
#     ]

#     aggregate = intent[
#         "aggregate"
#     ]

#     # --------------------------------------------------------
#     # Load latest merit data
#     # --------------------------------------------------------

#     try:

#         merit = load_latest_merit()

#     except Exception as exc:

#         return {

#             "success":
#                 False,

#             "type":
#                 "merit_unavailable",

#             "message":
#                 (
#                     "The latest UET merit list "
#                     "could not be retrieved right now."
#                 ),

#             "error":
#                 str(exc),

#             "source_url":
#                 None,

#             "records":
#                 [],
#         }

#     data = merit.get(
#         "data",
#         [],
#     )

#     source_url = merit.get(
#         "source_url"
#     )

#     pdf_file = merit.get(
#         "pdf_file"
#     )

#     checked_at = merit.get(
#         "checked_at"
#     )

#     if not data:

#         return {

#             "success":
#                 False,

#             "type":
#                 "merit_empty",

#             "message":
#                 (
#                     "The latest UET merit PDF "
#                     "was downloaded, but no merit "
#                     "records could be extracted."
#                 ),

#             "error":
#                 None,

#             "source_url":
#                 source_url,

#             "pdf_file":
#                 pdf_file,

#             "checked_at":
#                 checked_at,

#             "records":
#                 [],
#         }

#     # --------------------------------------------------------
#     # If user did not mention a program, try to understand
#     # from the data only when there is exactly one obvious
#     # match. Otherwise return available guidance.
#     # --------------------------------------------------------

#     records = filter_merit_data(
#         data,
#         program=program,
#         campus=campus,
#         category=category,
#     )

#     # --------------------------------------------------------
#     # No records found with requested filters
#     # --------------------------------------------------------

#     if not records:

#         return {

#             "success":
#                 False,

#             "type":
#                 "merit_not_found",

#             "message":
#                 (
#                     "No current merit record was "
#                     "found for the requested "
#                     "program, campus, or category."
#                 ),

#             "source_url":
#                 source_url,

#             "pdf_file":
#                 pdf_file,

#             "checked_at":
#                 checked_at,

#             "program":
#                 program,

#             "campus":
#                 campus,

#             "category":
#                 category,

#             "student_aggregate":
#                 aggregate,

#             "records":
#                 [],
#         }

#     # --------------------------------------------------------
#     # Student aggregate check
#     # --------------------------------------------------------

#     if aggregate is not None:

#         checks = []

#         for record in records:

#             minimum = safe_float(
#                 record.get(
#                     "minimum_aggregate",
#                     record.get(
#                         "closing_merit"
#                     ),
#                 )
#             )

#             if minimum is None:
#                 continue

#             difference = (
#                 aggregate
#                 - minimum
#             )

#             checks.append({

#                 **record,

#                 "student_aggregate":
#                     aggregate,

#                 "selected":
#                     aggregate >= minimum,

#                 "difference":
#                     round(
#                         difference,
#                         5,
#                     ),

#             })

#         if not checks:

#             return {

#                 "success":
#                     False,

#                 "type":
#                     "merit_invalid_records",

#                 "message":
#                     (
#                         "Matching merit records "
#                         "were found, but their "
#                         "closing merit could not "
#                         "be read."
#                     ),

#                 "source_url":
#                     source_url,

#                 "pdf_file":
#                     pdf_file,

#                 "checked_at":
#                     checked_at,

#                 "records":
#                     [],
#             }

#         return {

#             "success":
#                 True,

#             "type":
#                 "merit_check",

#             "message":
#                 (
#                     "Latest UET merit data "
#                     "was used."
#                 ),

#             "source_url":
#                 source_url,

#             "pdf_file":
#                 pdf_file,

#             "checked_at":
#                 checked_at,

#             "program":
#                 program,

#             "campus":
#                 campus,

#             "category":
#                 category,

#             "student_aggregate":
#                 aggregate,

#             "records":
#                 checks,
#         }

#     # --------------------------------------------------------
#     # Normal merit lookup
#     # --------------------------------------------------------

#     return {

#         "success":
#             True,

#         "type":
#             "merit",

#         "message":
#             (
#                 "Latest UET merit data "
#                 "was used."
#             ),

#         "source_url":
#             source_url,

#         "pdf_file":
#             pdf_file,

#         "checked_at":
#             checked_at,

#         "program":
#             program,

#         "campus":
#             campus,

#         "category":
#             category,

#         "records":
#             records,
#     }


# # ============================================================
# # MERIT RESULT TEXT
# # ============================================================

# def format_merit_response(
#     response
# ):

#     if not response.get(
#         "success",
#         False,
#     ):

#         return {

#             "answer":
#                 response.get(
#                     "message",
#                     "The merit system could not process this question.",
#                 ),

#             "source_url":
#                 response.get(
#                     "source_url"
#                 ),

#             "merit_response":
#                 response,
#         }

#     response_type = response.get(
#         "type"
#     )

#     records = response.get(
#         "records",
#         [],
#     )

#     source_url = response.get(
#         "source_url"
#     )

#     # --------------------------------------------------------
#     # Student selection
#     # --------------------------------------------------------

#     if response_type == "merit_check":

#         aggregate = response.get(
#             "student_aggregate"
#         )

#         lines = []

#         lines.append(
#             f"Your aggregate: **{aggregate:.5f}**"
#         )

#         for record in records:

#             program = record.get(
#                 "program",
#                 record.get(
#                     "discipline",
#                     "Unknown program",
#                 ),
#             )

#             campus = record.get(
#                 "campus",
#                 "Unknown campus",
#             )

#             category = record.get(
#                 "category",
#                 "",
#             )

#             session = record.get(
#                 "session",
#                 "",
#             )

#             admission_type = record.get(
#                 "type",
#                 "",
#             )

#             minimum = safe_float(
#                 record.get(
#                     "minimum_aggregate",
#                     record.get(
#                         "closing_merit"
#                     ),
#                 )
#             )

#             difference = safe_float(
#                 record.get(
#                     "difference"
#                 )
#             )

#             selected = bool(
#                 record.get(
#                     "selected"
#                 )
#             )

#             if selected:

#                 status = (
#                     "✅ **SELECTED / ABOVE CURRENT MERIT**"
#                 )

#             else:

#                 status = (
#                     "❌ **BELOW CURRENT MERIT**"
#                 )

#             lines.append(
#                 ""
#             )

#             lines.append(
#                 f"**{program} — {campus}**"
#             )

#             if category:
#                 lines.append(
#                     f"- Category: {category}"
#                 )

#             if session:
#                 lines.append(
#                     f"- Session: {session}"
#                 )

#             if admission_type:
#                 lines.append(
#                     f"- Type: {admission_type}"
#                 )

#             if minimum is not None:
#                 lines.append(
#                     f"- Current closing merit: **{minimum:.5f}**"
#                 )

#             if difference is not None:
#                 lines.append(
#                     f"- Difference: **{difference:+.5f}**"
#                 )

#             lines.append(
#                 f"- Status: {status}"
#             )

#         if source_url:

#             lines.append(
#                 ""
#             )

#             lines.append(
#                 f"[🔗 Open official UET merit source]({source_url})"
#             )

#         return {

#             "answer":
#                 "\n".join(lines),

#             "source_url":
#                 source_url,

#             "merit_response":
#                 response,
#         }

#     # --------------------------------------------------------
#     # Normal merit lookup
#     # --------------------------------------------------------

#     lines = []

#     for record in records:

#         program = record.get(
#             "program",
#             record.get(
#                 "discipline",
#                 "Unknown program",
#             ),
#         )

#         campus = record.get(
#             "campus",
#             "Unknown campus",
#         )

#         category = record.get(
#             "category",
#             "",
#         )

#         session = record.get(
#             "session",
#             "",
#         )

#         admission_type = record.get(
#             "type",
#             "",
#         )

#         minimum = safe_float(
#             record.get(
#                 "minimum_aggregate",
#                 record.get(
#                     "closing_merit"
#                 ),
#             )
#         )

#         line = (
#             f"**{program} — {campus}**"
#         )

#         if category:
#             line += (
#                 f" | {category}"
#             )

#         if session:
#             line += (
#                 f" | {session}"
#             )

#         if admission_type:
#             line += (
#                 f" | {admission_type}"
#             )

#         if minimum is not None:
#             line += (
#                 f" → **{minimum:.5f}**"
#             )

#         lines.append(
#             line
#         )

#     if source_url:

#         lines.append(
#             ""
#         )

#         lines.append(
#             f"[🔗 Open official UET merit source]({source_url})"
#         )

#     return {

#         "answer":
#             "\n".join(lines),

#         "source_url":
#             source_url,

#         "merit_response":
#             response,
#     }


# # ============================================================
# # CHROMA SOURCE HELPERS
# # ============================================================

# def get_source_key(
#     metadata
# ):

#     metadata = (
#         metadata
#         or {}
#     )

#     source_type = normalize(
#         metadata.get(
#             "source_type"
#         )
#     )

#     pdf_file = normalize(
#         metadata.get(
#             "pdf_file"
#         )
#     )

#     url = normalize(
#         metadata.get(
#             "url"
#         )
#     )

#     title = normalize(
#         metadata.get(
#             "title"
#         )
#     )

#     if (
#         source_type == "pdf"
#         and pdf_file
#     ):

#         return (
#             f"pdf::{pdf_file}"
#         )

#     if url:

#         return (
#             f"url::{url}"
#         )

#     if title:

#         return (
#             f"title::{title}"
#         )

#     return "unknown"


# # ============================================================
# # CONFIDENCE
# # ============================================================

# def classify_confidence(
#     results
# ):

#     if not results:
#         return "none"

#     best_distance = results[
#         0
#     ].get(
#         "distance"
#     )

#     if best_distance is None:
#         return "none"

#     if (
#         best_distance
#         <= STRONG_DISTANCE
#     ):

#         return "strong"

#     if (
#         best_distance
#         <= GOOD_DISTANCE
#     ):

#         return "good"

#     if (
#         best_distance
#         <= MAX_DISTANCE
#     ):

#         return "moderate"

#     return "low"


# # ============================================================
# # SOURCE REFERENCE
# # ============================================================

# def make_source_reference(
#     result
# ):

#     metadata = (
#         result.get(
#             "metadata",
#             {},
#         )
#         or {}
#     )

#     source_type = normalize(
#         metadata.get(
#             "source_type"
#         )
#     )

#     title = normalize(
#         metadata.get(
#             "title"
#         )
#     )

#     url = normalize(
#         metadata.get(
#             "url"
#         )
#     )

#     pdf_file = normalize(
#         metadata.get(
#             "pdf_file"
#         )
#     )

#     page = safe_int(
#         metadata.get(
#             "page"
#         )
#     )

#     return {

#         "source_type":
#             source_type,

#         "title":
#             title,

#         "url":
#             url,

#         "pdf_file":
#             pdf_file,

#         "page":
#             page
#             if page > 0
#             else None,
#     }


# # ============================================================
# # CLEAN CHROMA RESULT
# # ============================================================

# def clean_result(
#     result
# ):

#     metadata = (
#         result.get(
#             "metadata",
#             {},
#         )
#         or {}
#     )

#     return {

#         "rank":
#             result.get(
#                 "rank"
#             ),

#         "id":
#             result.get(
#                 "id"
#             ),

#         "distance":
#             result.get(
#                 "distance"
#             ),

#         "source_type":
#             normalize(
#                 metadata.get(
#                     "source_type"
#                 )
#             ),

#         "title":
#             normalize(
#                 metadata.get(
#                     "title"
#                 )
#             ),

#         "url":
#             normalize(
#                 metadata.get(
#                     "url"
#                 )
#             ),

#         "pdf_file":
#             normalize(
#                 metadata.get(
#                     "pdf_file"
#                 )
#             ),

#         "page":
#             safe_int(
#                 metadata.get(
#                     "page"
#                 )
#             ),

#         "book":
#             normalize(
#                 metadata.get(
#                     "book"
#                 )
#             ),

#         "temporal":
#             bool(
#                 metadata.get(
#                     "temporal",
#                     False,
#                 )
#             ),

#         "quality_flag":
#             normalize(
#                 metadata.get(
#                     "quality_flag"
#                 )
#             ),

#         "extraction_method":
#             normalize(
#                 metadata.get(
#                     "extraction_method"
#                 )
#             ),

#         "categories":
#             normalize(
#                 metadata.get(
#                     "categories"
#                 )
#             ),

#         "text":
#             normalize(
#                 result.get(
#                     "document"
#                 )
#             ),
#     }


# # ============================================================
# # LOAD CHROMA
# # ============================================================

# def load_collection():

#     if not VECTORSTORE_DIR.exists():

#         raise FileNotFoundError(
#             "\nVector store was not found:\n"
#             f"{VECTORSTORE_DIR}\n\n"
#             "Run ingestion.py first."
#         )

#     client = chromadb.PersistentClient(
#         path=str(
#             VECTORSTORE_DIR
#         )
#     )

#     try:

#         collection = (
#             client.get_collection(
#                 name=COLLECTION_NAME
#             )
#         )

#     except Exception as exc:

#         raise RuntimeError(
#             "\nChroma collection was not found:\n"
#             f"{COLLECTION_NAME}\n\n"
#             "Run ingestion.py first."
#         ) from exc

#     return collection


# # ============================================================
# # LOAD EMBEDDING MODEL
# # ============================================================

# def load_embedding_model():

#     print()
#     print(
#         "Loading embedding model:"
#     )

#     print(
#         EMBEDDING_MODEL_NAME
#     )

#     return SentenceTransformer(
#         EMBEDDING_MODEL_NAME
#     )


# # ============================================================
# # RAW CHROMA RETRIEVAL
# # ============================================================

# def retrieve_candidates(
#     collection,
#     model,
#     question,
# ):

#     query_text = build_query(
#         question
#     )

#     query_embedding = (
#         model.encode(
#             [query_text],
#             normalize_embeddings=True,
#             show_progress_bar=False,
#         )
#     )

#     result = collection.query(

#         query_embeddings=
#             query_embedding.tolist(),

#         n_results=
#             RETRIEVAL_CANDIDATES,

#         include=[
#             "documents",
#             "metadatas",
#             "distances",
#         ],
#     )

#     ids = (
#         result.get(
#             "ids",
#             [[]],
#         )[0]
#         if result.get("ids")
#         else []
#     )

#     documents = (
#         result.get(
#             "documents",
#             [[]],
#         )[0]
#         if result.get("documents")
#         else []
#     )

#     metadatas = (
#         result.get(
#             "metadatas",
#             [[]],
#         )[0]
#         if result.get("metadatas")
#         else []
#     )

#     distances = (
#         result.get(
#             "distances",
#             [[]],
#         )[0]
#         if result.get("distances")
#         else []
#     )

#     candidates = []

#     for index, chunk_id in enumerate(
#         ids
#     ):

#         candidates.append({

#             "id":
#                 chunk_id,

#             "distance":
#                 distances[index]
#                 if index < len(
#                     distances
#                 )
#                 else None,

#             "metadata":
#                 metadatas[index]
#                 if index < len(
#                     metadatas
#                 )
#                 else {},

#             "document":
#                 documents[index]
#                 if index < len(
#                     documents
#                 )
#                 else "",
#         })

#     return candidates


# # ============================================================
# # DISTANCE FILTER
# # ============================================================

# def filter_by_distance(
#     candidates
# ):

#     return [

#         candidate

#         for candidate in candidates

#         if (
#             candidate.get(
#                 "distance"
#             )
#             is not None
#             and
#             candidate.get(
#                 "distance"
#             )
#             <= MAX_DISTANCE
#         )

#     ]


# # ============================================================
# # DEDUPLICATION
# # ============================================================

# def deduplicate_results(
#     candidates
# ):

#     seen = set()

#     results = []

#     for candidate in candidates:

#         chunk_id = candidate.get(
#             "id"
#         )

#         if chunk_id in seen:
#             continue

#         seen.add(
#             chunk_id
#         )

#         results.append(
#             candidate
#         )

#     return results


# # ============================================================
# # SOURCE DIVERSIFICATION
# # ============================================================

# def diversify_sources(
#     candidates
# ):

#     selected = []

#     source_counts = {}

#     for candidate in candidates:

#         source_key = get_source_key(
#             candidate.get(
#                 "metadata",
#                 {},
#             )
#         )

#         count = source_counts.get(
#             source_key,
#             0,
#         )

#         if count >= 4:
#             continue

#         selected.append(
#             candidate
#         )

#         source_counts[
#             source_key
#         ] = count + 1

#         if (
#             len(selected)
#             >= FINAL_RESULTS
#         ):
#             break

#     # --------------------------------------------------------
#     # Fill remaining slots
#     # --------------------------------------------------------

#     if (
#         len(selected)
#         < FINAL_RESULTS
#     ):

#         selected_ids = {
#             item.get("id")
#             for item in selected
#         }

#         for candidate in candidates:

#             if (
#                 candidate.get("id")
#                 in selected_ids
#             ):
#                 continue

#             selected.append(
#                 candidate
#             )

#             if (
#                 len(selected)
#                 >= FINAL_RESULTS
#             ):
#                 break

#     return selected


# # ============================================================
# # BUILD CHROMA RESULTS
# # ============================================================

# def build_results(
#     candidates
# ):

#     results = []

#     for rank, candidate in enumerate(
#         candidates,
#         start=1,
#     ):

#         item = clean_result({

#             **candidate,

#             "rank":
#                 rank,
#         })

#         item[
#             "source_reference"
#         ] = make_source_reference(
#             candidate
#         )

#         results.append(
#             item
#         )

#     return results


# # ============================================================
# # SOURCE SUMMARY
# # ============================================================

# def build_source_summary(
#     results
# ):

#     sources = []

#     seen = set()

#     for result in results:

#         reference = result.get(
#             "source_reference",
#             {},
#         )

#         key = (

#             reference.get(
#                 "source_type"
#             ),

#             reference.get(
#                 "title"
#             ),

#             reference.get(
#                 "url"
#             ),

#             reference.get(
#                 "pdf_file"
#             ),
#         )

#         if key in seen:
#             continue

#         seen.add(
#             key
#         )

#         sources.append(
#             reference
#         )

#     return sources


# # ============================================================
# # SAVE AUDIT
# # ============================================================

# def save_audit(
#     question,
#     results,
#     confidence,
#     candidate_count,
# ):

#     AUDIT_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     audit = {

#         "question":
#             question,

#         "embedding_model":
#             EMBEDDING_MODEL_NAME,

#         "query_prefix":
#             BGE_QUERY_PREFIX,

#         "collection":
#             COLLECTION_NAME,

#         "candidate_count":
#             candidate_count,

#         "final_result_count":
#             len(results),

#         "max_distance":
#             MAX_DISTANCE,

#         "confidence":
#             confidence,

#         "sources":
#             build_source_summary(
#                 results
#             ),

#         "results":
#             results,
#     }

#     with LAST_RETRIEVAL_FILE.open(
#         "w",
#         encoding="utf-8",
#     ) as file:

#         json.dump(
#             audit,
#             file,
#             indent=2,
#             ensure_ascii=False,
#         )


# # ============================================================
# # NORMAL RETRIEVE
# # ============================================================

# def retrieve_normal(
#     collection,
#     model,
#     question,
# ):

#     candidates = retrieve_candidates(
#         collection,
#         model,
#         question,
#     )

#     candidates.sort(
#         key=lambda item: (
#             item.get(
#                 "distance"
#             )
#             if item.get(
#                 "distance"
#             ) is not None
#             else float("inf")
#         )
#     )

#     filtered = filter_by_distance(
#         candidates
#     )

#     filtered = deduplicate_results(
#         filtered
#     )

#     selected = diversify_sources(
#         filtered
#     )

#     results = build_results(
#         selected
#     )

#     confidence = classify_confidence(
#         results
#     )

#     return (
#         results,
#         confidence,
#         len(candidates),
#     )


# # ============================================================
# # MAIN ROUTER
# # ============================================================

# def route_question(
#     question,
#     collection,
#     model,
# ):

#     question = normalize(
#         question
#     )

#     if not question:

#         return {

#             "route":
#                 "semantic",

#             "results":
#                 [],

#             "confidence":
#                 "none",
#         }

#     # ========================================================
#     # MERIT ROUTE
#     # ========================================================

#     if is_merit_question(
#         question
#     ):

#         print()
#         print(
#             "[ROUTER] Merit question detected."
#         )

#         intent = parse_merit_query(
#             question
#         )

#         print(
#             f"[ROUTER] Program : "
#             f"{intent.get('program')}"
#         )

#         print(
#             f"[ROUTER] Campus  : "
#             f"{intent.get('campus')}"
#         )

#         print(
#             f"[ROUTER] Category: "
#             f"{intent.get('category')}"
#         )

#         print(
#             f"[ROUTER] Aggregate: "
#             f"{intent.get('aggregate')}"
#         )

#         response = answer_merit_question(
#             question
#         )

#         formatted = format_merit_response(
#             response
#         )

#         return {

#             "route":
#                 "merit",

#             "response":
#                 response,

#             "answer":
#                 formatted["answer"],

#             "source_url":
#                 formatted.get(
#                     "source_url"
#                 ),
#         }

#     # ========================================================
#     # NORMAL SEMANTIC ROUTE
#     # ========================================================

#     print()
#     print(
#         "[ROUTER] Normal knowledge question."
#     )

#     (
#         results,
#         confidence,
#         candidate_count,
#     ) = retrieve_normal(
#         collection,
#         model,
#         question,
#     )

#     save_audit(
#         question,
#         results,
#         confidence,
#         candidate_count,
#     )

#     return {

#         "route":
#             "semantic",

#         "results":
#             results,

#         "confidence":
#             confidence,
#     }


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 80)
#     print(
#         "UET CHATBOT — PRODUCTION RETRIEVER"
#     )
#     print("=" * 80)

#     print()
#     print(
#         "Routes:"
#     )

#     print(
#         "  Merit questions  -> Dynamic latest UET merit"
#     )

#     print(
#         "  Other questions  -> ChromaDB semantic search"
#     )

#     # --------------------------------------------------------
#     # Load Chroma
#     # --------------------------------------------------------

#     collection = load_collection()

#     count = collection.count()

#     print()
#     print(
#         f"Vectors available: {count}"
#     )

#     if count == 0:

#         raise RuntimeError(
#             "ChromaDB collection is empty."
#         )

#     # --------------------------------------------------------
#     # Load embedding model
#     # --------------------------------------------------------

#     model = load_embedding_model()

#     print()
#     print("=" * 80)
#     print(
#         "READY"
#     )
#     print("=" * 80)

#     print()
#     print(
#         "Examples:"
#     )

#     print(
#         "  My aggregate is 90, am I selected for CS Lahore?"
#     )

#     print(
#         "  What is the merit for Electrical Engineering Lahore?"
#     )

#     print(
#         "  What is Civil Engineering merit KSK?"
#     )

#     print(
#         "  What is UET admission process?"
#     )

#     print(
#         "  exit"
#     )

#     while True:

#         try:

#             question = input(
#                 "\nUser question: "
#             ).strip()

#         except (
#             KeyboardInterrupt,
#             EOFError,
#         ):

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         if not question:
#             continue

#         if question.lower() in {
#             "exit",
#             "quit",
#             "q",
#         }:

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         try:

#             result = route_question(
#                 question,
#                 collection,
#                 model,
#             )

#             # ------------------------------------------------
#             # MERIT
#             # ------------------------------------------------

#             if (
#                 result["route"]
#                 == "merit"
#             ):

#                 print()
#                 print("=" * 80)
#                 print(
#                     "MERIT RESPONSE"
#                 )
#                 print("=" * 80)

#                 print()
#                 print(
#                     result.get(
#                         "answer",
#                         "",
#                     )
#                 )

#             # ------------------------------------------------
#             # NORMAL
#             # ------------------------------------------------

#             elif (
#                 result["route"]
#                 == "semantic"
#             ):

#                 display_results(
#                     question,
#                     result.get(
#                         "results",
#                         [],
#                     ),
#                     result.get(
#                         "confidence",
#                         "none",
#                     ),
#                 )

#             else:

#                 print()
#                 print(
#                     "[ERROR] Unknown route:"
#                 )

#                 print(
#                     result
#                 )

#         except Exception as exc:

#             print()
#             print(
#                 "=" * 80
#             )

#             print(
#                 "[ERROR]"
#             )

#             print(
#                 str(exc)
#             )

#             print(
#                 "=" * 80
#             )


# # ============================================================
# # DISPLAY NORMAL RETRIEVAL
# # ============================================================

# def display_results(
#     question,
#     results,
#     confidence,
# ):

#     print()
#     print("=" * 78)
#     print(
#         "SEMANTIC RETRIEVAL RESULTS"
#     )
#     print("=" * 78)

#     print()
#     print(
#         f"Query      : {question}"
#     )

#     print(
#         f"Confidence : {confidence.upper()}"
#     )

#     print(
#         f"Results    : {len(results)}"
#     )

#     if not results:

#         print()
#         print(
#             "[NO RELIABLE RESULTS]"
#         )

#         return

#     for result in results:

#         print()
#         print(
#             "-" * 78
#         )

#         print(
#             f"RANK       : "
#             f"{result['rank']}"
#         )

#         print(
#             f"DISTANCE   : "
#             f"{result['distance']}"
#         )

#         print(
#             f"SOURCE TYPE: "
#             f"{result['source_type']}"
#         )

#         print(
#             f"TITLE      : "
#             f"{result['title']}"
#         )

#         if result["url"]:

#             print(
#                 f"URL        : "
#                 f"{result['url']}"
#             )

#         if result["pdf_file"]:

#             print(
#                 f"PDF FILE   : "
#                 f"{result['pdf_file']}"
#             )

#         if result["page"]:

#             print(
#                 f"PAGE       : "
#                 f"{result['page']}"
#             )

#         print()
#         print(
#             "TEXT:"
#         )

#         print(
#             result["text"]
#         )


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":

#     main()





# import json
# import sys
# from pathlib import Path

# import chromadb
# from sentence_transformers import SentenceTransformer


# # ============================================================
# # UET CHATBOT — IMPROVED SEMANTIC RETRIEVAL
# # ============================================================
# #
# # Input:
# #   data/vectorstore/chroma/
# #
# # Collection:
# #   uet_admission_knowledge
# #
# # Embedding model:
# #   BAAI/bge-small-en-v1.5
# #
# # Purpose:
# #   Production-oriented semantic retrieval for the UET
# #   Admissions chatbot.
# #
# # Improvements:
# #   1. Correct BGE query instruction prefix
# #   2. Configurable similarity threshold
# #   3. Source/document grouping
# #   4. Duplicate result suppression
# #   5. Source metadata preservation
# #   6. PDF/page/source URL reporting
# #   7. Confidence classification
# #   8. Retrieval audit JSON
# #
# # IMPORTANT:
# #   This script DOES NOT modify the knowledge base.
# #   This script DOES NOT modify ChromaDB.
# #   It only reads from the vector store.
# #
# # ============================================================


# # ============================================================
# # PROJECT PATHS
# # ============================================================

# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# VECTORSTORE_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "vectorstore"
#     / "chroma"
# )

# AUDIT_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "retrieval"
# )

# LAST_RETRIEVAL_FILE = (
#     AUDIT_DIR
#     / "last_retrieval.json"
# )


# # ============================================================
# # CONFIGURATION
# # ============================================================

# EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# COLLECTION_NAME = "uet_admission_knowledge"


# # Number of candidates requested from Chroma.
# #
# # We retrieve more candidates than we finally display because
# # filtering/grouping may remove some results.
# RETRIEVAL_CANDIDATES = 20


# # Number of final results shown.
# FINAL_RESULTS = 8


# # Chroma distance is cosine distance because the embeddings
# # were normalized during ingestion.
# #
# # Lower distance = more similar.
# #
# # This is deliberately not extremely strict because admission
# # questions can have different wording from the source text.
# MAX_DISTANCE = 0.78


# # Results below these distances are considered stronger.
# STRONG_DISTANCE = 0.55
# GOOD_DISTANCE = 0.65


# # ============================================================
# # BGE QUERY INSTRUCTION
# # ============================================================
# #
# # BAAI/bge-small-en-v1.5 uses an asymmetric retrieval setup.
# #
# # Passages:
# #   embedded normally during ingestion.
# #
# # Queries:
# #   should use the following instruction.
# #
# # ============================================================

# BGE_QUERY_PREFIX = (
#     "Represent this sentence for searching relevant passages: "
# )


# # ============================================================
# # HELPERS
# # ============================================================

# def normalize(value):
#     if value is None:
#         return ""

#     return str(value).strip()


# def safe_int(value):
#     try:
#         return int(value)
#     except (TypeError, ValueError):
#         return 0


# def build_query(question):
#     """
#     Apply the BGE retrieval instruction.
#     """

#     question = normalize(question)

#     if not question:
#         return ""

#     return BGE_QUERY_PREFIX + question


# def get_source_key(metadata):
#     """
#     Create a stable source/document grouping key.

#     PDF chunks:
#         grouped primarily by pdf_file.

#     Page chunks:
#         grouped by URL/title.

#     This allows the retrieval layer to recognize that several
#     chunks belong to the same underlying document.
#     """

#     source_type = normalize(
#         metadata.get("source_type")
#     )

#     pdf_file = normalize(
#         metadata.get("pdf_file")
#     )

#     url = normalize(
#         metadata.get("url")
#     )

#     title = normalize(
#         metadata.get("title")
#     )

#     if source_type == "pdf" and pdf_file:
#         return f"pdf::{pdf_file}"

#     if url:
#         return f"url::{url}"

#     if title:
#         return f"title::{title}"

#     return "unknown"


# def classify_confidence(results):
#     """
#     Classify retrieval confidence using the best distance.
#     """

#     if not results:
#         return "none"

#     best_distance = results[0]["distance"]

#     if best_distance <= STRONG_DISTANCE:
#         return "strong"

#     if best_distance <= GOOD_DISTANCE:
#         return "good"

#     if best_distance <= MAX_DISTANCE:
#         return "moderate"

#     return "low"


# def make_source_reference(result):
#     """
#     Produce a clean source-reference object.

#     This is intentionally generated from retrieval metadata,
#     NOT invented by the LLM.
#     """

#     metadata = result.get("metadata", {})

#     source_type = normalize(
#         metadata.get("source_type")
#     )

#     title = normalize(
#         metadata.get("title")
#     )

#     url = normalize(
#         metadata.get("url")
#     )

#     pdf_file = normalize(
#         metadata.get("pdf_file")
#     )

#     page = safe_int(
#         metadata.get("page")
#     )

#     reference = {
#         "source_type": source_type,
#         "title": title,
#         "url": url,
#         "pdf_file": pdf_file,
#         "page": page if page > 0 else None,
#     }

#     return reference


# def clean_result(result):
#     """
#     Convert Chroma result into a clean structure that the
#     future LLM/API layer can directly consume.
#     """

#     metadata = result.get("metadata", {}) or {}

#     return {
#         "rank": result.get("rank"),
#         "id": result.get("id"),
#         "distance": result.get("distance"),
#         "source_type": normalize(
#             metadata.get("source_type")
#         ),
#         "title": normalize(
#             metadata.get("title")
#         ),
#         "url": normalize(
#             metadata.get("url")
#         ),
#         "pdf_file": normalize(
#             metadata.get("pdf_file")
#         ),
#         "page": safe_int(
#             metadata.get("page")
#         ),
#         "book": normalize(
#             metadata.get("book")
#         ),
#         "temporal": bool(
#             metadata.get("temporal", False)
#         ),
#         "quality_flag": normalize(
#             metadata.get("quality_flag")
#         ),
#         "extraction_method": normalize(
#             metadata.get("extraction_method")
#         ),
#         "categories": normalize(
#             metadata.get("categories")
#         ),
#         "text": normalize(
#             result.get("document")
#         ),
#     }


# # ============================================================
# # LOAD VECTOR STORE
# # ============================================================

# def load_collection():

#     if not VECTORSTORE_DIR.exists():

#         raise FileNotFoundError(
#             "\nVector store was not found:\n"
#             f"{VECTORSTORE_DIR}\n\n"
#             "Run ingestion.py first."
#         )

#     print()
#     print("Vector store:")
#     print(VECTORSTORE_DIR)

#     client = chromadb.PersistentClient(
#         path=str(VECTORSTORE_DIR)
#     )

#     try:

#         collection = client.get_collection(
#             name=COLLECTION_NAME
#         )

#     except Exception as exc:

#         raise RuntimeError(
#             "\nChroma collection was not found:\n"
#             f"{COLLECTION_NAME}\n\n"
#             "Run ingestion.py first."
#         ) from exc

#     return collection


# # ============================================================
# # LOAD EMBEDDING MODEL
# # ============================================================

# def load_embedding_model():

#     print()
#     print(
#         f"Loading embedding model: "
#         f"{EMBEDDING_MODEL_NAME}"
#     )

#     model = SentenceTransformer(
#         EMBEDDING_MODEL_NAME
#     )

#     return model


# # ============================================================
# # RAW RETRIEVAL
# # ============================================================

# def retrieve_candidates(
#     collection,
#     model,
#     question,
# ):

#     query_text = build_query(question)

#     query_embedding = model.encode(
#         [query_text],
#         normalize_embeddings=True,
#         show_progress_bar=False,
#     )

#     result = collection.query(
#         query_embeddings=query_embedding.tolist(),
#         n_results=RETRIEVAL_CANDIDATES,
#         include=[
#             "documents",
#             "metadatas",
#             "distances",
#         ],
#     )

#     ids = (
#         result.get("ids", [[]])[0]
#         if result.get("ids")
#         else []
#     )

#     documents = (
#         result.get("documents", [[]])[0]
#         if result.get("documents")
#         else []
#     )

#     metadatas = (
#         result.get("metadatas", [[]])[0]
#         if result.get("metadatas")
#         else []
#     )

#     distances = (
#         result.get("distances", [[]])[0]
#         if result.get("distances")
#         else []
#     )

#     candidates = []

#     for index, chunk_id in enumerate(ids):

#         distance = (
#             distances[index]
#             if index < len(distances)
#             else None
#         )

#         metadata = (
#             metadatas[index]
#             if index < len(metadatas)
#             else {}
#         )

#         document = (
#             documents[index]
#             if index < len(documents)
#             else ""
#         )

#         candidates.append(
#             {
#                 "id": chunk_id,
#                 "distance": distance,
#                 "metadata": metadata or {},
#                 "document": document or "",
#             }
#         )

#     return candidates


# # ============================================================
# # FILTERING
# # ============================================================

# def filter_by_distance(candidates):

#     filtered = []

#     for candidate in candidates:

#         distance = candidate.get("distance")

#         if distance is None:
#             continue

#         if distance <= MAX_DISTANCE:
#             filtered.append(candidate)

#     return filtered


# # ============================================================
# # DUPLICATE / SOURCE CONTROL
# # ============================================================

# def deduplicate_results(candidates):

#     """
#     Remove exact duplicate chunk IDs.

#     Chroma should already have unique IDs, but this defensive
#     layer keeps retrieval output clean.
#     """

#     seen_ids = set()
#     unique = []

#     for candidate in candidates:

#         chunk_id = candidate.get("id")

#         if chunk_id in seen_ids:
#             continue

#         seen_ids.add(chunk_id)

#         unique.append(candidate)

#     return unique


# def diversify_sources(candidates):

#     """
#     Prevent the first few results from being dominated by
#     identical chunks from exactly the same source.

#     We keep up to 4 results from one source initially, while
#     still allowing additional results if the candidate pool
#     is small.

#     This is useful for questions such as:

#         "What is the BS fee structure?"

#     where pages 1, 2 and 240 may all be useful, but unrelated
#     chunks from the same source should not overwhelm the
#     retrieval list.
#     """

#     selected = []

#     source_counts = {}

#     # First pass: source diversity.
#     for candidate in candidates:

#         source_key = get_source_key(
#             candidate.get("metadata", {})
#         )

#         count = source_counts.get(
#             source_key,
#             0,
#         )

#         if count >= 4:
#             continue

#         selected.append(candidate)

#         source_counts[source_key] = count + 1

#         if len(selected) >= FINAL_RESULTS:
#             break

#     # Second pass: fill if necessary.
#     if len(selected) < FINAL_RESULTS:

#         selected_ids = {
#             item.get("id")
#             for item in selected
#         }

#         for candidate in candidates:

#             if candidate.get("id") in selected_ids:
#                 continue

#             selected.append(candidate)

#             if len(selected) >= FINAL_RESULTS:
#                 break

#     return selected


# # ============================================================
# # FINAL RESULT BUILD
# # ============================================================

# def build_results(candidates):

#     cleaned = []

#     for rank, candidate in enumerate(
#         candidates,
#         start=1,
#     ):

#         item = clean_result(
#             {
#                 **candidate,
#                 "rank": rank,
#             }
#         )

#         item["source_reference"] = (
#             make_source_reference(candidate)
#         )

#         cleaned.append(item)

#     return cleaned


# # ============================================================
# # SOURCE SUMMARY
# # ============================================================

# def build_source_summary(results):

#     sources = []

#     seen = set()

#     for result in results:

#         reference = result.get(
#             "source_reference",
#             {},
#         )

#         key = (
#             reference.get("source_type"),
#             reference.get("title"),
#             reference.get("url"),
#             reference.get("pdf_file"),
#         )

#         if key in seen:
#             continue

#         seen.add(key)

#         sources.append(
#             reference
#         )

#     return sources


# # ============================================================
# # AUDIT
# # ============================================================

# def save_audit(
#     question,
#     results,
#     confidence,
#     candidate_count,
# ):

#     AUDIT_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     audit = {
#         "question": question,
#         "embedding_model": EMBEDDING_MODEL_NAME,
#         "query_prefix": BGE_QUERY_PREFIX,
#         "collection": COLLECTION_NAME,
#         "candidate_count": candidate_count,
#         "final_result_count": len(results),
#         "max_distance": MAX_DISTANCE,
#         "confidence": confidence,
#         "sources": build_source_summary(
#             results
#         ),
#         "results": results,
#     }

#     with LAST_RETRIEVAL_FILE.open(
#         "w",
#         encoding="utf-8",
#     ) as file:

#         json.dump(
#             audit,
#             file,
#             indent=2,
#             ensure_ascii=False,
#         )


# # ============================================================
# # DISPLAY
# # ============================================================

# def display_results(
#     question,
#     results,
#     confidence,
# ):

#     print()
#     print("=" * 78)
#     print("RETRIEVAL RESULTS")
#     print("=" * 78)

#     print()
#     print(
#         f"Query      : {question}"
#     )

#     print(
#         f"Confidence : {confidence.upper()}"
#     )

#     print(
#         f"Results    : {len(results)}"
#     )

#     if not results:

#         print()
#         print(
#             "[NO RELIABLE RESULTS]"
#         )

#         print(
#             "The question did not produce sufficiently "
#             "similar knowledge chunks."
#         )

#         return

#     for result in results:

#         print()
#         print("-" * 78)

#         print(
#             f"RANK       : {result['rank']}"
#         )

#         print(
#             f"ID         : {result['id']}"
#         )

#         print(
#             f"DISTANCE   : {result['distance']}"
#         )

#         print(
#             f"SOURCE TYPE: {result['source_type']}"
#         )

#         print(
#             f"TITLE      : {result['title']}"
#         )

#         print(
#             f"URL        : {result['url']}"
#         )

#         if result["pdf_file"]:

#             print(
#                 f"PDF FILE   : {result['pdf_file']}"
#             )

#         if result["page"]:

#             print(
#                 f"PAGE       : {result['page']}"
#             )

#         print(
#             f"BOOK       : {result['book']}"
#         )

#         print(
#             f"TEMPORAL   : {result['temporal']}"
#         )

#         print()
#         print("TEXT:")

#         print(
#             result["text"]
#         )

#         print()
#         print("SOURCE REFERENCE:")

#         reference = result[
#             "source_reference"
#         ]

#         print(
#             f"  Title : {reference.get('title', '')}"
#         )

#         if reference.get("page"):

#             print(
#                 f"  Page  : {reference['page']}"
#             )

#         if reference.get("url"):

#             print(
#                 f"  URL   : {reference['url']}"
#             )

#     print()
#     print("=" * 78)
#     print(
#         "AUDIT SAVED:"
#     )
#     print(
#         LAST_RETRIEVAL_FILE
#     )
#     print("=" * 78)


# # ============================================================
# # RETRIEVE
# # ============================================================

# def retrieve(
#     collection,
#     model,
#     question,
# ):

#     candidates = retrieve_candidates(
#         collection,
#         model,
#         question,
#     )

#     # Lowest distance = best match.
#     candidates.sort(
#         key=lambda item: (
#             item.get("distance")
#             if item.get("distance") is not None
#             else float("inf")
#         )
#     )

#     # Remove weak matches.
#     filtered = filter_by_distance(
#         candidates
#     )

#     # Remove duplicate IDs.
#     filtered = deduplicate_results(
#         filtered
#     )

#     # Prefer source diversity.
#     selected = diversify_sources(
#         filtered
#     )

#     results = build_results(
#         selected
#     )

#     confidence = classify_confidence(
#         results
#     )

#     return (
#         results,
#         confidence,
#         len(candidates),
#     )


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 78)
#     print(
#         "UET ADMISSION — IMPROVED SEMANTIC RETRIEVAL"
#     )
#     print("=" * 78)

#     print()
#     print(
#         "Vector store:"
#     )

#     print(
#         VECTORSTORE_DIR
#     )

#     print()
#     print(
#         "Collection:"
#     )

#     print(
#         COLLECTION_NAME
#     )

#     collection = load_collection()

#     count = collection.count()

#     print()
#     print(
#         f"Vectors available: {count}"
#     )

#     if count == 0:

#         raise RuntimeError(
#             "ChromaDB collection is empty."
#         )

#     model = load_embedding_model()

#     print()
#     print("=" * 78)
#     print("READY")
#     print("=" * 78)

#     print()
#     print(
#         "Ask a question."
#     )

#     print(
#         "Type 'exit' to stop."
#     )

#     print()
#     print(
#         "Retrieval configuration:"
#     )

#     print(
#         f"  Candidate results : "
#         f"{RETRIEVAL_CANDIDATES}"
#     )

#     print(
#         f"  Final results     : "
#         f"{FINAL_RESULTS}"
#     )

#     print(
#         f"  Max distance      : "
#         f"{MAX_DISTANCE}"
#     )

#     print(
#         f"  Query prefix      : "
#         f"BGE instruction enabled"
#     )

#     while True:

#         try:

#             question = input(
#                 "\nUser question: "
#             ).strip()

#         except (
#             KeyboardInterrupt,
#             EOFError,
#         ):

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         if not question:

#             continue

#         if question.lower() in {
#             "exit",
#             "quit",
#             "q",
#         }:

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         try:

#             (
#                 results,
#                 confidence,
#                 candidate_count,
#             ) = retrieve(
#                 collection,
#                 model,
#                 question,
#             )

#             display_results(
#                 question,
#                 results,
#                 confidence,
#             )

#             save_audit(
#                 question,
#                 results,
#                 confidence,
#                 candidate_count,
#             )

#         except Exception as exc:

#             print()
#             print(
#                 "[ERROR]"
#             )

#             print(
#                 str(exc)
#             )


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":
#     main()


# import json
# import re
# from pathlib import Path

# import chromadb
# from sentence_transformers import SentenceTransformer

# # Import dynamic merit engine
# from merit import load_latest_merit


# # ============================================================
# # UET CHATBOT — PRODUCTION RETRIEVER
# # ============================================================
# #
# # ROUTING:
# #
# #   Merit question
# #       ↓
# #   Dynamic merit.py
# #       ↓
# #   Latest UET merit PDF
# #
# #   Normal question
# #       ↓
# #   ChromaDB
# #       ↓
# #   BGE semantic retrieval
# #
# # ============================================================


# # ============================================================
# # PROJECT PATHS
# # ============================================================

# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# VECTORSTORE_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "vectorstore"
#     / "chroma"
# )

# AUDIT_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "retrieval"
# )

# LAST_RETRIEVAL_FILE = (
#     AUDIT_DIR
#     / "last_retrieval.json"
# )


# # ============================================================
# # CHROMA CONFIGURATION
# # ============================================================

# EMBEDDING_MODEL_NAME = (
#     "BAAI/bge-small-en-v1.5"
# )

# COLLECTION_NAME = (
#     "uet_admission_knowledge"
# )

# RETRIEVAL_CANDIDATES = 20

# FINAL_RESULTS = 8

# MAX_DISTANCE = 0.78

# STRONG_DISTANCE = 0.55

# GOOD_DISTANCE = 0.65


# # ============================================================
# # BGE QUERY PREFIX
# # ============================================================

# BGE_QUERY_PREFIX = (
#     "Represent this sentence for searching relevant passages: "
# )


# # ============================================================
# # MERIT CONFIGURATION
# # ============================================================



# CAMPUS_ALIASES = {

#     "lahore":
#         "Main Campus (LHR)",

#     "lhr":
#         "Main Campus (LHR)",

#     "lahore campus":
#         "Main Campus (LHR)",

#     "main campus":
#         "Main Campus (LHR)",

#     "ksk":
#         "New Campus (KSK)",

#     "new campus":
#         "New Campus (KSK)",

#     "new campus ksk":
#         "New Campus (KSK)",

#     "faisalabad":
#         "Faislabad Campus",

#     "faislabad":
#         "Faislabad Campus",

#     "faisalabad campus":
#         "Faislabad Campus",

#     "gujranwala":
#         "Gujar anwala",

#     "gujranwala campus":
#         "Gujar anwala",

#     "gujaranwala":
#         "Gujar anwala",

#     "narowal":
#         "Narowal Campus (NWL)",

#     "nwl":
#         "Narowal Campus (NWL)",
# }


# CATEGORY_PATTERN = re.compile(
#     r"\b(A1-M|A2-M|A1|A2|NM)\b",
#     re.IGNORECASE,
# )


# # ============================================================
# # GENERAL HELPERS
# # ============================================================

# def normalize(value):

#     if value is None:
#         return ""

#     return re.sub(
#         r"\s+",
#         " ",
#         str(value).strip(),
#     )


# def safe_int(value):

#     try:
#         return int(value)

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0


# def build_query(question):

#     question = normalize(
#         question
#     )

#     if not question:
#         return ""

#     return (
#         BGE_QUERY_PREFIX
#         + question
#     )


# # ============================================================
# # MERIT QUERY DETECTION
# # ============================================================

# def is_merit_question(question):

#     text = normalize(question).lower()

#     merit_keywords = [
#         "merit",
#         "aggregate",
#         "selected",
#         "selection",
#         "cutoff",
#         "cut off",
#         "closing merit",
#         "minimum aggregate",
#         "last merit",
#         "merit list",
#         "merit check",
#         "eligible",
#         "can i get",
#         "can i get admission",
#         "will i get",
#         "am i selected",
#     ]

#     if any(
#         keyword in text
#         for keyword in merit_keywords
#     ):
#         return True

#     has_number = bool(
#         re.search(
#             r"\b\d{2}(?:\.\d+)?\b",
#             text,
#         )
#     )

#     has_campus = any(
#         alias in text
#         for alias in CAMPUS_ALIASES
#     )

#     if has_number and has_campus:
#         return True

#     return False


# # ============================================================
# # CAMPUS EXTRACTION
# # ============================================================

# def extract_campus(question):

#     text = normalize(
#         question
#     ).lower()

#     # Longest aliases first.
#     aliases = sorted(
#         CAMPUS_ALIASES.keys(),
#         key=len,
#         reverse=True,
#     )

#     for alias in aliases:

#         if alias in text:

#             return CAMPUS_ALIASES[
#                 alias
#             ]

#     return None


# # ============================================================
# # CATEGORY EXTRACTION
# # ============================================================

# def extract_category(question):

#     match = CATEGORY_PATTERN.search(
#         question
#     )

#     if not match:
#         return None

#     return match.group(1).upper()


# # ============================================================
# # AGGREGATE EXTRACTION
# # ============================================================

# def extract_aggregate(question):

#     text = normalize(
#         question
#     )

#     # --------------------------------------------------------
#     # Strong patterns first
#     # --------------------------------------------------------

#     patterns = [

#         r"(?:aggregate|merit)\s*(?:is|of|=|:)?\s*"
#         r"(\d{2}(?:\.\d+)?)",

#         r"(\d{2}(?:\.\d+)?)\s*"
#         r"(?:aggregate|merit)",

#         r"(?:got|have|scored|score)\s*"
#         r"(\d{2}(?:\.\d+)?)",

#     ]

#     for pattern in patterns:

#         try:

#             match = re.search(
#                 pattern,
#                 text,
#                 re.IGNORECASE,
#             )

#         except re.error:
#             continue

#         if match:

#             try:

#                 value = float(
#                     match.group(1)
#                 )

#                 if 0 <= value <= 100:
#                     return value

#             except ValueError:
#                 pass

#     # --------------------------------------------------------
#     # General fallback
#     # --------------------------------------------------------

#     numbers = re.findall(
#         r"\b\d{2}(?:\.\d+)?\b",
#         text,
#     )

#     for number in numbers:

#         try:

#             value = float(
#                 number
#             )

#             if 0 <= value <= 100:
#                 return value

#         except ValueError:
#             continue

#     return None


# # ============================================================
# # MERIT INTENT
# # ============================================================

# def parse_merit_query(question):

#     return {
#         "is_merit": is_merit_question(
#             question
#         ),

#         "campus": extract_campus(
#             question
#         ),

#         "category": extract_category(
#             question
#         ),

#         "aggregate": extract_aggregate(
#             question
#         ),

#         "program": "Computer Science",
#     }


# # ============================================================
# # MERIT DATA FILTER
# # ============================================================

# def filter_cs_data(
#     data,
#     campus=None,
#     category=None,
# ):

#     results = []

#     for item in data:

#         if normalize(
#             item.get("program")
#         ).lower() != "computer science":

#             continue

#         if campus:

#             if (
#                 normalize(
#                     item.get("campus")
#                 ).lower()
#                 != normalize(
#                     campus
#                 ).lower()
#             ):

#                 continue

#         if category:

#             if (
#                 normalize(
#                     item.get("category")
#                 ).upper()
#                 != category.upper()
#             ):

#                 continue

#         results.append(
#             item
#         )

#     return results


# # ============================================================
# # MERIT RESPONSE
# # ============================================================

# def answer_merit_question(
#     question,
# ):

#     intent = parse_merit_query(
#         question
#     )

#     campus = intent[
#         "campus"
#     ]

#     category = intent[
#         "category"
#     ]

#     aggregate = intent[
#         "aggregate"
#     ]

#     # --------------------------------------------------------
#     # Current/latest merit data
#     # --------------------------------------------------------

#     merit = load_latest_merit()

#     data = merit[
#         "data"
#     ]

#     source_url = merit[
#         "source_url"
#     ]

#     # --------------------------------------------------------
#     # If campus wasn't specified
#     #
#     # Return all CS campuses.
#     # --------------------------------------------------------

#     records = filter_cs_data(
#         data,
#         campus=campus,
#         category=category,
#     )

#     if not records:

#         return {
#             "type": "merit",
#             "success": False,
#             "message": (
#                 "No current Computer Science "
#                 "merit record was found for "
#                 "the requested campus/category."
#             ),
#             "source_url": source_url,
#             "records": [],
#         }

#     # --------------------------------------------------------
#     # Student selection check
#     # --------------------------------------------------------

#     if aggregate is not None:

#         checks = []

#         for record in records:

#             minimum = float(
#                 record[
#                     "minimum_aggregate"
#                 ]
#             )

#             difference = (
#                 aggregate
#                 - minimum
#             )

#             selected = (
#                 aggregate >= minimum
#             )

#             checks.append({

#                 **record,

#                 "student_aggregate":
#                     aggregate,

#                 "selected":
#                     selected,

#                 "difference":
#                     round(
#                         difference,
#                         5,
#                     ),
#             })

#         return {
#             "type": "merit_check",
#             "success": True,
#             "message": (
#                 "Latest UET merit data "
#                 "was used."
#             ),
#             "source_url": source_url,
#             "student_aggregate": aggregate,
#             "records": checks,
#         }

#     # --------------------------------------------------------
#     # Just merit lookup
#     # --------------------------------------------------------

#     return {
#         "type": "merit",
#         "success": True,
#         "message": (
#             "Latest UET merit data "
#             "was used."
#         ),
#         "source_url": source_url,
#         "records": records,
#     }


# # ============================================================
# # CHROMA SOURCE HELPERS
# # ============================================================

# def get_source_key(
#     metadata
# ):

#     source_type = normalize(
#         metadata.get(
#             "source_type"
#         )
#     )

#     pdf_file = normalize(
#         metadata.get(
#             "pdf_file"
#         )
#     )

#     url = normalize(
#         metadata.get(
#             "url"
#         )
#     )

#     title = normalize(
#         metadata.get(
#             "title"
#         )
#     )

#     if (
#         source_type == "pdf"
#         and pdf_file
#     ):

#         return (
#             f"pdf::{pdf_file}"
#         )

#     if url:

#         return (
#             f"url::{url}"
#         )

#     if title:

#         return (
#             f"title::{title}"
#         )

#     return "unknown"


# def classify_confidence(
#     results
# ):

#     if not results:
#         return "none"

#     best_distance = results[
#         0
#     ]["distance"]

#     if (
#         best_distance
#         <= STRONG_DISTANCE
#     ):

#         return "strong"

#     if (
#         best_distance
#         <= GOOD_DISTANCE
#     ):

#         return "good"

#     if (
#         best_distance
#         <= MAX_DISTANCE
#     ):

#         return "moderate"

#     return "low"


# # ============================================================
# # SOURCE REFERENCE
# # ============================================================

# def make_source_reference(
#     result
# ):

#     metadata = result.get(
#         "metadata",
#         {},
#     )

#     source_type = normalize(
#         metadata.get(
#             "source_type"
#         )
#     )

#     title = normalize(
#         metadata.get(
#             "title"
#         )
#     )

#     url = normalize(
#         metadata.get(
#             "url"
#         )
#     )

#     pdf_file = normalize(
#         metadata.get(
#             "pdf_file"
#         )
#     )

#     page = safe_int(
#         metadata.get(
#             "page"
#         )
#     )

#     return {
#         "source_type":
#             source_type,

#         "title":
#             title,

#         "url":
#             url,

#         "pdf_file":
#             pdf_file,

#         "page":
#             page
#             if page > 0
#             else None,
#     }


# # ============================================================
# # CLEAN CHROMA RESULT
# # ============================================================

# def clean_result(
#     result
# ):

#     metadata = (
#         result.get(
#             "metadata",
#             {},
#         )
#         or {}
#     )

#     return {

#         "rank":
#             result.get(
#                 "rank"
#             ),

#         "id":
#             result.get(
#                 "id"
#             ),

#         "distance":
#             result.get(
#                 "distance"
#             ),

#         "source_type":
#             normalize(
#                 metadata.get(
#                     "source_type"
#                 )
#             ),

#         "title":
#             normalize(
#                 metadata.get(
#                     "title"
#                 )
#             ),

#         "url":
#             normalize(
#                 metadata.get(
#                     "url"
#                 )
#             ),

#         "pdf_file":
#             normalize(
#                 metadata.get(
#                     "pdf_file"
#                 )
#             ),

#         "page":
#             safe_int(
#                 metadata.get(
#                     "page"
#                 )
#             ),

#         "book":
#             normalize(
#                 metadata.get(
#                     "book"
#                 )
#             ),

#         "temporal":
#             bool(
#                 metadata.get(
#                     "temporal",
#                     False,
#                 )
#             ),

#         "quality_flag":
#             normalize(
#                 metadata.get(
#                     "quality_flag"
#                 )
#             ),

#         "extraction_method":
#             normalize(
#                 metadata.get(
#                     "extraction_method"
#                 )
#             ),

#         "categories":
#             normalize(
#                 metadata.get(
#                     "categories"
#                 )
#             ),

#         "text":
#             normalize(
#                 result.get(
#                     "document"
#                 )
#             ),
#     }


# # ============================================================
# # LOAD CHROMA
# # ============================================================

# def load_collection():

#     if not VECTORSTORE_DIR.exists():

#         raise FileNotFoundError(
#             "\nVector store was not found:\n"
#             f"{VECTORSTORE_DIR}\n\n"
#             "Run ingestion.py first."
#         )

#     client = (
#         chromadb.PersistentClient(
#             path=str(
#                 VECTORSTORE_DIR
#             )
#         )
#     )

#     try:

#         collection = (
#             client.get_collection(
#                 name=COLLECTION_NAME
#             )
#         )

#     except Exception as exc:

#         raise RuntimeError(
#             "\nChroma collection was not found:\n"
#             f"{COLLECTION_NAME}\n\n"
#             "Run ingestion.py first."
#         ) from exc

#     return collection


# # ============================================================
# # LOAD EMBEDDING MODEL
# # ============================================================

# def load_embedding_model():

#     print()
#     print(
#         "Loading embedding model:"
#     )

#     print(
#         EMBEDDING_MODEL_NAME
#     )

#     return SentenceTransformer(
#         EMBEDDING_MODEL_NAME
#     )


# # ============================================================
# # RAW CHROMA RETRIEVAL
# # ============================================================

# def retrieve_candidates(
#     collection,
#     model,
#     question,
# ):

#     query_text = build_query(
#         question
#     )

#     query_embedding = (
#         model.encode(
#             [query_text],
#             normalize_embeddings=True,
#             show_progress_bar=False,
#         )
#     )

#     result = collection.query(

#         query_embeddings=
#             query_embedding.tolist(),

#         n_results=
#             RETRIEVAL_CANDIDATES,

#         include=[
#             "documents",
#             "metadatas",
#             "distances",
#         ],
#     )

#     ids = (
#         result.get(
#             "ids",
#             [[]],
#         )[0]
#         if result.get("ids")
#         else []
#     )

#     documents = (
#         result.get(
#             "documents",
#             [[]],
#         )[0]
#         if result.get("documents")
#         else []
#     )

#     metadatas = (
#         result.get(
#             "metadatas",
#             [[]],
#         )[0]
#         if result.get("metadatas")
#         else []
#     )

#     distances = (
#         result.get(
#             "distances",
#             [[]],
#         )[0]
#         if result.get("distances")
#         else []
#     )

#     candidates = []

#     for index, chunk_id in enumerate(
#         ids
#     ):

#         candidates.append({

#             "id":
#                 chunk_id,

#             "distance":
#                 distances[index]
#                 if index < len(
#                     distances
#                 )
#                 else None,

#             "metadata":
#                 metadatas[index]
#                 if index < len(
#                     metadatas
#                 )
#                 else {},

#             "document":
#                 documents[index]
#                 if index < len(
#                     documents
#                 )
#                 else "",
#         })

#     return candidates


# # ============================================================
# # DISTANCE FILTER
# # ============================================================

# def filter_by_distance(
#     candidates
# ):

#     return [

#         candidate

#         for candidate in candidates

#         if (
#             candidate.get(
#                 "distance"
#             )
#             is not None
#             and
#             candidate.get(
#                 "distance"
#             )
#             <= MAX_DISTANCE
#         )

#     ]


# # ============================================================
# # DEDUPLICATION
# # ============================================================

# def deduplicate_results(
#     candidates
# ):

#     seen = set()

#     results = []

#     for candidate in candidates:

#         chunk_id = candidate.get(
#             "id"
#         )

#         if chunk_id in seen:
#             continue

#         seen.add(
#             chunk_id
#         )

#         results.append(
#             candidate
#         )

#     return results


# # ============================================================
# # SOURCE DIVERSIFICATION
# # ============================================================

# def diversify_sources(
#     candidates
# ):

#     selected = []

#     source_counts = {}

#     for candidate in candidates:

#         source_key = get_source_key(
#             candidate.get(
#                 "metadata",
#                 {},
#             )
#         )

#         count = source_counts.get(
#             source_key,
#             0,
#         )

#         if count >= 4:
#             continue

#         selected.append(
#             candidate
#         )

#         source_counts[
#             source_key
#         ] = count + 1

#         if (
#             len(selected)
#             >= FINAL_RESULTS
#         ):
#             break

#     # Fill remaining slots
#     if (
#         len(selected)
#         < FINAL_RESULTS
#     ):

#         selected_ids = {
#             item.get("id")
#             for item in selected
#         }

#         for candidate in candidates:

#             if (
#                 candidate.get("id")
#                 in selected_ids
#             ):
#                 continue

#             selected.append(
#                 candidate
#             )

#             if (
#                 len(selected)
#                 >= FINAL_RESULTS
#             ):
#                 break

#     return selected


# # ============================================================
# # BUILD CHROMA RESULTS
# # ============================================================

# def build_results(
#     candidates
# ):

#     results = []

#     for rank, candidate in enumerate(
#         candidates,
#         start=1,
#     ):

#         item = clean_result({

#             **candidate,

#             "rank":
#                 rank,
#         })

#         item[
#             "source_reference"
#         ] = make_source_reference(
#             candidate
#         )

#         results.append(
#             item
#         )

#     return results


# # ============================================================
# # SOURCE SUMMARY
# # ============================================================

# def build_source_summary(
#     results
# ):

#     sources = []

#     seen = set()

#     for result in results:

#         reference = result.get(
#             "source_reference",
#             {},
#         )

#         key = (

#             reference.get(
#                 "source_type"
#             ),

#             reference.get(
#                 "title"
#             ),

#             reference.get(
#                 "url"
#             ),

#             reference.get(
#                 "pdf_file"
#             ),
#         )

#         if key in seen:
#             continue

#         seen.add(
#             key
#         )

#         sources.append(
#             reference
#         )

#     return sources


# # ============================================================
# # SAVE AUDIT
# # ============================================================

# def save_audit(
#     question,
#     results,
#     confidence,
#     candidate_count,
# ):

#     AUDIT_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     audit = {

#         "question":
#             question,

#         "embedding_model":
#             EMBEDDING_MODEL_NAME,

#         "query_prefix":
#             BGE_QUERY_PREFIX,

#         "collection":
#             COLLECTION_NAME,

#         "candidate_count":
#             candidate_count,

#         "final_result_count":
#             len(results),

#         "max_distance":
#             MAX_DISTANCE,

#         "confidence":
#             confidence,

#         "sources":
#             build_source_summary(
#                 results
#             ),

#         "results":
#             results,
#     }

#     with LAST_RETRIEVAL_FILE.open(
#         "w",
#         encoding="utf-8",
#     ) as file:

#         json.dump(
#             audit,
#             file,
#             indent=2,
#             ensure_ascii=False,
#         )


# # ============================================================
# # DISPLAY MERIT RESPONSE
# # ============================================================

# def display_merit_response(
#     response
# ):

#     print()
#     print("=" * 80)
#     print(
#         "CURRENT UET MERIT RESULT"
#     )
#     print("=" * 80)

#     print()

#     print(
#         response.get(
#             "message",
#             "",
#         )
#     )

#     source_url = response.get(
#         "source_url"
#     )

#     if source_url:

#         print()
#         print(
#             "SOURCE:"
#         )

#         print(
#             source_url
#         )

#     records = response.get(
#         "records",
#         [],
#     )

#     if not records:

#         print()
#         print(
#             "No matching records."
#         )

#         return

#     for record in records:

#         print()
#         print(
#             "-" * 80
#         )

#         print(
#             f"Campus       : "
#             f"{record['campus']}"
#         )

#         print(
#             f"Program      : "
#             f"{record['program']}"
#         )

#         print(
#             f"Category     : "
#             f"{record['category']}"
#         )

#         print(
#             f"Session      : "
#             f"{record['session']}"
#         )

#         print(
#             f"Type         : "
#             f"{record['type']}"
#         )

#         print(
#             f"Minimum Merit: "
#             f"{record['minimum_aggregate']:.5f}"
#         )

#         if (
#             "student_aggregate"
#             in record
#         ):

#             print(
#                 f"Student       : "
#                 f"{record['student_aggregate']:.5f}"
#             )

#             print(
#                 f"Difference    : "
#                 f"{record['difference']:+.5f}"
#             )

#             if record["selected"]:

#                 print(
#                     "STATUS        : "
#                     "SELECTED / ABOVE CURRENT MERIT"
#                 )

#             else:

#                 print(
#                     "STATUS        : "
#                     "BELOW CURRENT MERIT"
#                 )

#         if record.get(
#             "page"
#         ):

#             print(
#                 f"PDF Page      : "
#                 f"{record['page']}"
#             )


# # ============================================================
# # DISPLAY NORMAL RETRIEVAL
# # ============================================================

# def display_results(
#     question,
#     results,
#     confidence,
# ):

#     print()
#     print("=" * 78)
#     print(
#         "SEMANTIC RETRIEVAL RESULTS"
#     )
#     print("=" * 78)

#     print()
#     print(
#         f"Query      : {question}"
#     )

#     print(
#         f"Confidence : {confidence.upper()}"
#     )

#     print(
#         f"Results    : {len(results)}"
#     )

#     if not results:

#         print()
#         print(
#             "[NO RELIABLE RESULTS]"
#         )

#         return

#     for result in results:

#         print()
#         print(
#             "-" * 78
#         )

#         print(
#             f"RANK       : "
#             f"{result['rank']}"
#         )

#         print(
#             f"DISTANCE   : "
#             f"{result['distance']}"
#         )

#         print(
#             f"SOURCE TYPE: "
#             f"{result['source_type']}"
#         )

#         print(
#             f"TITLE      : "
#             f"{result['title']}"
#         )

#         if result["url"]:

#             print(
#                 f"URL        : "
#                 f"{result['url']}"
#             )

#         if result["pdf_file"]:

#             print(
#                 f"PDF FILE   : "
#                 f"{result['pdf_file']}"
#             )

#         if result["page"]:

#             print(
#                 f"PAGE       : "
#                 f"{result['page']}"
#             )

#         print()
#         print(
#             "TEXT:"
#         )

#         print(
#             result["text"]
#         )


# # ============================================================
# # NORMAL RETRIEVE
# # ============================================================

# def retrieve_normal(
#     collection,
#     model,
#     question,
# ):

#     candidates = retrieve_candidates(
#         collection,
#         model,
#         question,
#     )

#     candidates.sort(
#         key=lambda item: (
#             item.get(
#                 "distance"
#             )
#             if item.get(
#                 "distance"
#             ) is not None
#             else float("inf")
#         )
#     )

#     filtered = filter_by_distance(
#         candidates
#     )

#     filtered = deduplicate_results(
#         filtered
#     )

#     selected = diversify_sources(
#         filtered
#     )

#     results = build_results(
#         selected
#     )

#     confidence = classify_confidence(
#         results
#     )

#     return (
#         results,
#         confidence,
#         len(candidates),
#     )


# # ============================================================
# # MAIN ROUTER
# # ============================================================

# def route_question(
#     question,
#     collection,
#     model,
# ):

#     question = normalize(
#         question
#     )

#     # --------------------------------------------------------
#     # MERIT ROUTE
#     # --------------------------------------------------------

#     if is_merit_question(
#         question
#     ):

#         print()
#         print(
#             "[ROUTER] Merit question detected."
#         )

#         print(
#             "[ROUTER] Using latest UET merit data."
#         )

#         response = answer_merit_question(
#             question
#         )

#         return {
#             "route":
#                 "merit",

#             "response":
#                 response,
#         }

#     # --------------------------------------------------------
#     # NORMAL SEMANTIC ROUTE
#     # --------------------------------------------------------

#     print()
#     print(
#         "[ROUTER] Normal knowledge question."
#     )

#     (
#         results,
#         confidence,
#         candidate_count,
#     ) = retrieve_normal(
#         collection,
#         model,
#         question,
#     )

#     save_audit(
#         question,
#         results,
#         confidence,
#         candidate_count,
#     )

#     return {
#         "route":
#             "semantic",

#         "results":
#             results,

#         "confidence":
#             confidence,
#     }


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 80)
#     print(
#         "UET CHATBOT — PRODUCTION RETRIEVER"
#     )
#     print("=" * 80)

#     print()
#     print(
#         "Routes:"
#     )

#     print(
#         "  Merit questions  -> Dynamic latest UET merit"
#     )

#     print(
#         "  Other questions  -> ChromaDB semantic search"
#     )

#     # --------------------------------------------------------
#     # Load Chroma
#     # --------------------------------------------------------

#     collection = load_collection()

#     count = collection.count()

#     print()
#     print(
#         f"Vectors available: {count}"
#     )

#     if count == 0:

#         raise RuntimeError(
#             "ChromaDB collection is empty."
#         )

#     # --------------------------------------------------------
#     # Load embedding model
#     # --------------------------------------------------------

#     model = load_embedding_model()

#     print()
#     print("=" * 80)
#     print(
#         "READY"
#     )
#     print("=" * 80)

#     print()
#     print(
#         "Examples:"
#     )

#     print(
#         "  Lahore CS merit?"
#     )

#     print(
#         "  My aggregate is 90, am I selected for CS Lahore?"
#     )

#     print(
#         "  KSK CS merit A1?"
#     )

#     print(
#         "  What is UET admission process?"
#     )

#     print(
#         "  exit"
#     )

#     while True:

#         try:

#             question = input(
#                 "\nUser question: "
#             ).strip()

#         except (
#             KeyboardInterrupt,
#             EOFError,
#         ):

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         if not question:
#             continue

#         if question.lower() in {
#             "exit",
#             "quit",
#             "q",
#         }:

#             print()
#             print(
#                 "Exiting."
#             )

#             break

#         try:

#             result = route_question(
#                 question,
#                 collection,
#                 model,
#             )

#             # ------------------------------------------------
#             # MERIT
#             # ------------------------------------------------

#             if (
#                 result["route"]
#                 == "merit"
#             ):

#                 display_merit_response(
#                     result["response"]
#                 )

#             # ------------------------------------------------
#             # NORMAL
#             # ------------------------------------------------

#             else:

#                 display_results(
#                     question,
#                     result["results"],
#                     result["confidence"],
#                 )

#         except Exception as exc:

#             print()
#             print(
#                 "=" * 80
#             )

#             print(
#                 "[ERROR]"
#             )

#             print(
#                 str(exc)
#             )

#             print(
#                 "=" * 80
#             )


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":

#     main()






import json
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# Dynamic merit engine
from merit import load_latest_merit


# ============================================================
# UET CHATBOT — PRODUCTION RETRIEVER
# ============================================================
#
# ROUTING
#
# Merit / closing merit / aggregate question
#       ↓
#       merit.py
#       ↓
# Latest UET merit-list PDF
#
# Normal admission question
#       ↓
# ChromaDB
#       ↓
# BGE semantic retrieval
#
# IMPORTANT:
#
# This file does NOT download merit PDFs itself.
#
# merit.py is responsible for:
#   - finding latest merit-list PDF
#   - downloading it
#   - extracting merit records
#
# This file is responsible for:
#   - detecting merit intent
#   - extracting campus / program / category / aggregate
#   - routing
#   - normal Chroma retrieval
#   - audit logging
#
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

VECTORSTORE_DIR = (
    PROJECT_ROOT
    / "data"
    / "vectorstore"
    / "chroma"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "retrieval"
)

LAST_RETRIEVAL_FILE = (
    AUDIT_DIR
    / "last_retrieval.json"
)


# ============================================================
# CHROMA CONFIGURATION
# ============================================================

EMBEDDING_MODEL_NAME = (
    "BAAI/bge-small-en-v1.5"
)

COLLECTION_NAME = (
    "uet_admission_knowledge"
)

RETRIEVAL_CANDIDATES = 20

FINAL_RESULTS = 8

MAX_DISTANCE = 0.78

STRONG_DISTANCE = 0.55

GOOD_DISTANCE = 0.65


# ============================================================
# BGE QUERY PREFIX
# ============================================================

BGE_QUERY_PREFIX = (
    "Represent this sentence for searching relevant passages: "
)


# ============================================================
# CAMPUS ALIASES
# ============================================================

CAMPUS_ALIASES = {

    "lahore":
        "Main Campus (LHR)",

    "lhr":
        "Main Campus (LHR)",

    "lahore campus":
        "Main Campus (LHR)",

    "main campus":
        "Main Campus (LHR)",

    "main campus lhr":
        "Main Campus (LHR)",

    "ksk":
        "New Campus (KSK)",

    "new campus":
        "New Campus (KSK)",

    "new campus ksk":
        "New Campus (KSK)",

    "faisalabad":
        "Faislabad Campus",

    "faislabad":
        "Faislabad Campus",

    "faisalabad campus":
        "Faislabad Campus",

    "gujranwala":
        "Gujar anwala",

    "gujaranwala":
        "Gujar anwala",

    "gujranwala campus":
        "Gujar anwala",

    "narowal":
        "Narowal Campus (NWL)",

    "nwl":
        "Narowal Campus (NWL)",

    "narowal campus":
        "Narowal Campus (NWL)",
}


# ============================================================
# CATEGORY
# ============================================================

CATEGORY_PATTERN = re.compile(
    r"\b(A1-M|A2-M|A1|A2|NM)\b",
    re.IGNORECASE,
)


# ============================================================
# COMMON PROGRAM ALIASES
# ============================================================
#
# This is ONLY for understanding user questions.
#
# The actual official program name comes from merit.py data.
#
# ============================================================

PROGRAM_ALIASES = {

    "computer science":
        "Computer Science",

    "cs":
        "Computer Science",

    "computer engineering":
        "Computer Engineering",

    "ce":
        "Computer Engineering",

    "software engineering":
        "Software Engineering",

    "se":
        "Software Engineering",

    "electrical engineering":
        "Electrical Engineering",

    "ee":
        "Electrical Engineering",

    "mechanical engineering":
        "Mechanical Engineering",

    "me":
        "Mechanical Engineering",

    "civil engineering":
        "Civil Engineering",

    "civil":
        "Civil Engineering",

    "chemical engineering":
        "Chemical Engineering",

    "architecture":
        "Architecture",

    "architectural engineering":
        "Architectural Engineering",

    "environmental engineering":
        "Environmental Engineering",

    "industrial engineering":
        "Industrial Engineering",

    "transportation engineering":
        "Transportation Engineering",

    "petroleum engineering":
        "Petroleum Engineering",

    "mining engineering":
        "Mining Engineering",

    "mechatronics":
        "Mechatronics",

    "biomedical engineering":
        "Biomedical Engineering",

    "food engineering":
        "Food Engineering",

    "metallurgical engineering":
        "Metallurgical Engineering",
}


# ============================================================
# MERIT KEYWORDS
# ============================================================

MERIT_KEYWORDS = [

    "merit",

    "aggregate",

    "selected",

    "selection",

    "closing merit",

    "cutoff",

    "cut off",

    "minimum merit",

    "minimum aggregate",

    "last merit",

    "merit list",

    "meritlist",

    "closing aggregate",

    "above merit",

    "below merit",

    "my aggregate",

    "my merit",

    "can i get admission",

    "can i get in",

    "will i get admission",

    "am i selected",

    "got selected",

]


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def safe_int(value):

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0


def safe_float(value):

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def build_query(question):

    question = normalize(
        question
    )

    if not question:
        return ""

    return (
        BGE_QUERY_PREFIX
        + question
    )


# ============================================================
# MERIT QUESTION DETECTION
# ============================================================

def is_merit_question(question):

    text = normalize(
        question
    ).lower()

    # --------------------------------------------------------
    # Explicit merit language
    # --------------------------------------------------------

    if any(
        keyword in text
        for keyword in MERIT_KEYWORDS
    ):
        return True

    # --------------------------------------------------------
    # Aggregate number + program/campus
    #
    # Example:
    #
    # 90 CS Lahore
    # 88 Electrical KSK
    # 85 Civil Faisalabad
    # --------------------------------------------------------

    has_number = bool(
        re.search(
            r"\b\d{2}(?:\.\d+)?\b",
            text,
        )
    )

    has_campus = any(
        alias in text
        for alias in CAMPUS_ALIASES
    )

    has_program = any(
        alias in text
        for alias in PROGRAM_ALIASES
    )

    if (
        has_number
        and
        (
            has_campus
            or has_program
        )
    ):
        return True

    return False


# ============================================================
# CAMPUS EXTRACTION
# ============================================================

def extract_campus(question):

    text = normalize(
        question
    ).lower()

    aliases = sorted(
        CAMPUS_ALIASES.keys(),
        key=len,
        reverse=True,
    )

    for alias in aliases:

        if alias in text:

            return CAMPUS_ALIASES[
                alias
            ]

    return None


# ============================================================
# CATEGORY EXTRACTION
# ============================================================

def extract_category(question):

    match = CATEGORY_PATTERN.search(
        question
    )

    if not match:
        return None

    return match.group(1).upper()


# ============================================================
# AGGREGATE EXTRACTION
# ============================================================

def extract_aggregate(question):

    text = normalize(
        question
    )

    patterns = [

        # aggregate is 90
        r"(?:aggregate|merit)"
        r"\s*(?:is|of|=|:)?\s*"
        r"(\d{2}(?:\.\d+)?)",

        # 90 aggregate
        r"(\d{2}(?:\.\d+)?)"
        r"\s*(?:aggregate|merit)",

        # I have 90
        r"(?:got|have|scored|score|aggregate\s+is)"
        r"\s*(?:=|:)?\s*"
        r"(\d{2}(?:\.\d+)?)",

        # am I selected with 90
        r"(?:with)"
        r"\s*(\d{2}(?:\.\d+)?)",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            value = safe_float(
                match.group(1)
            )

            if (
                value is not None
                and
                0 <= value <= 100
            ):

                return value

    # --------------------------------------------------------
    # General fallback
    # --------------------------------------------------------

    numbers = re.findall(
        r"\b\d{2}(?:\.\d+)?\b",
        text,
    )

    for number in numbers:

        value = safe_float(
            number
        )

        if (
            value is not None
            and
            0 <= value <= 100
        ):

            return value

    return None


# ============================================================
# PROGRAM EXTRACTION
# ============================================================

def extract_program(question):

    text = normalize(
        question
    ).lower()

    aliases = sorted(
        PROGRAM_ALIASES.keys(),
        key=len,
        reverse=True,
    )

    for alias in aliases:

        # Word boundary for short aliases
        if len(alias) <= 3:

            pattern = (
                r"\b"
                + re.escape(alias)
                + r"\b"
            )

            if re.search(
                pattern,
                text,
            ):

                return PROGRAM_ALIASES[
                    alias
                ]

        else:

            if alias in text:

                return PROGRAM_ALIASES[
                    alias
                ]

    return None


# ============================================================
# MERIT INTENT
# ============================================================

def parse_merit_query(question):

    return {

        "is_merit":
            is_merit_question(
                question
            ),

        "campus":
            extract_campus(
                question
            ),

        "category":
            extract_category(
                question
            ),

        "aggregate":
            extract_aggregate(
                question
            ),

        "program":
            extract_program(
                question
            ),
    }


# ============================================================
# NORMALIZE PROGRAM FOR COMPARISON
# ============================================================

def normalize_program_name(
    value
):

    text = normalize(
        value
    ).lower()

    text = re.sub(
        r"\([^)]*\)",
        "",
        text,
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return normalize(
        text
    )


# ============================================================
# PROGRAM MATCH
# ============================================================

def program_matches(
    record_program,
    requested_program,
):

    if not requested_program:
        return True

    actual = normalize_program_name(
        record_program
    )

    requested = normalize_program_name(
        requested_program
    )

    if not actual or not requested:
        return False

    return (
        actual == requested
        or requested in actual
        or actual in requested
    )


# ============================================================
# CAMPUS MATCH
# ============================================================

def campus_matches(
    record_campus,
    requested_campus,
):

    if not requested_campus:
        return True

    actual = normalize(
        record_campus
    ).lower()

    requested = normalize(
        requested_campus
    ).lower()

    return (
        actual == requested
        or requested in actual
        or actual in requested
    )


# ============================================================
# CATEGORY MATCH
# ============================================================

def category_matches(
    record_category,
    requested_category,
):

    if not requested_category:
        return True

    return (
        normalize(
            record_category
        ).lower()
        ==
        normalize(
            requested_category
        ).lower()
    )


# ============================================================
# GENERIC MERIT DATA FILTER
# ============================================================

def filter_merit_data(
    data,
    program=None,
    campus=None,
    category=None,
):

    results = []

    for item in data:

        if not isinstance(
            item,
            dict,
        ):
            continue

        record_program = item.get(
            "program",
            item.get(
                "discipline",
                "",
            ),
        )

        record_campus = item.get(
            "campus",
            "",
        )

        record_category = item.get(
            "category",
            "",
        )

        if not program_matches(
            record_program,
            program,
        ):
            continue

        if not campus_matches(
            record_campus,
            campus,
        ):
            continue

        if not category_matches(
            record_category,
            category,
        ):
            continue

        results.append(
            item
        )

    return results


# ============================================================
# MERIT RESPONSE
# ============================================================

def answer_merit_question(
    question
):

    intent = parse_merit_query(
        question
    )

    program = intent[
        "program"
    ]

    campus = intent[
        "campus"
    ]

    category = intent[
        "category"
    ]

    aggregate = intent[
        "aggregate"
    ]

    # --------------------------------------------------------
    # Load latest merit data
    # --------------------------------------------------------

    try:

        merit = load_latest_merit()

    except Exception as exc:

        return {

            "success":
                False,

            "type":
                "merit_unavailable",

            "message":
                (
                    "The latest UET merit list "
                    "could not be retrieved right now."
                ),

            "error":
                str(exc),

            "source_url":
                None,

            "records":
                [],
        }

    data = merit.get(
        "data",
        [],
    )

    source_url = merit.get(
        "source_url"
    )

    pdf_file = merit.get(
        "pdf_file"
    )

    checked_at = merit.get(
        "checked_at"
    )

    if not data:

        return {

            "success":
                False,

            "type":
                "merit_empty",

            "message":
                (
                    "The latest UET merit PDF "
                    "was downloaded, but no merit "
                    "records could be extracted."
                ),

            "error":
                None,

            "source_url":
                source_url,

            "pdf_file":
                pdf_file,

            "checked_at":
                checked_at,

            "records":
                [],
        }

    # --------------------------------------------------------
    # If user did not mention a program, try to understand
    # from the data only when there is exactly one obvious
    # match. Otherwise return available guidance.
    # --------------------------------------------------------

    records = filter_merit_data(
        data,
        program=program,
        campus=campus,
        category=category,
    )

    # --------------------------------------------------------
    # No records found with requested filters
    # --------------------------------------------------------

    if not records:

        return {

            "success":
                False,

            "type":
                "merit_not_found",

            "message":
                (
                    "No current merit record was "
                    "found for the requested "
                    "program, campus, or category."
                ),

            "source_url":
                source_url,

            "pdf_file":
                pdf_file,

            "checked_at":
                checked_at,

            "program":
                program,

            "campus":
                campus,

            "category":
                category,

            "student_aggregate":
                aggregate,

            "records":
                [],
        }

    # --------------------------------------------------------
    # Student aggregate check
    # --------------------------------------------------------

    if aggregate is not None:

        checks = []

        for record in records:

            minimum = safe_float(
                record.get(
                    "minimum_aggregate",
                    record.get(
                        "closing_merit"
                    ),
                )
            )

            if minimum is None:
                continue

            difference = (
                aggregate
                - minimum
            )

            checks.append({

                **record,

                "student_aggregate":
                    aggregate,

                "selected":
                    aggregate >= minimum,

                "difference":
                    round(
                        difference,
                        5,
                    ),

            })

        if not checks:

            return {

                "success":
                    False,

                "type":
                    "merit_invalid_records",

                "message":
                    (
                        "Matching merit records "
                        "were found, but their "
                        "closing merit could not "
                        "be read."
                    ),

                "source_url":
                    source_url,

                "pdf_file":
                    pdf_file,

                "checked_at":
                    checked_at,

                "records":
                    [],
            }

        return {

            "success":
                True,

            "type":
                "merit_check",

            "message":
                (
                    "Latest UET merit data "
                    "was used."
                ),

            "source_url":
                source_url,

            "pdf_file":
                pdf_file,

            "checked_at":
                checked_at,

            "program":
                program,

            "campus":
                campus,

            "category":
                category,

            "student_aggregate":
                aggregate,

            "records":
                checks,
        }

    # --------------------------------------------------------
    # Normal merit lookup
    # --------------------------------------------------------

    return {

        "success":
            True,

        "type":
            "merit",

        "message":
            (
                "Latest UET merit data "
                "was used."
            ),

        "source_url":
            source_url,

        "pdf_file":
            pdf_file,

        "checked_at":
            checked_at,

        "program":
            program,

        "campus":
            campus,

        "category":
            category,

        "records":
            records,
    }


# ============================================================
# MERIT RESULT TEXT
# ============================================================

def format_merit_response(
    response
):

    if not response.get(
        "success",
        False,
    ):

        return {

            "answer":
                response.get(
                    "message",
                    "The merit system could not process this question.",
                ),

            "source_url":
                response.get(
                    "source_url"
                ),

            "merit_response":
                response,
        }

    response_type = response.get(
        "type"
    )

    records = response.get(
        "records",
        [],
    )

    source_url = response.get(
        "source_url"
    )

    # --------------------------------------------------------
    # Student selection
    # --------------------------------------------------------

    if response_type == "merit_check":

        aggregate = response.get(
            "student_aggregate"
        )

        lines = []

        lines.append(
            f"Your aggregate: **{aggregate:.5f}**"
        )

        for record in records:

            program = record.get(
                "program",
                record.get(
                    "discipline",
                    "Unknown program",
                ),
            )

            campus = record.get(
                "campus",
                "Unknown campus",
            )

            category = record.get(
                "category",
                "",
            )

            session = record.get(
                "session",
                "",
            )

            admission_type = record.get(
                "type",
                "",
            )

            minimum = safe_float(
                record.get(
                    "minimum_aggregate",
                    record.get(
                        "closing_merit"
                    ),
                )
            )

            difference = safe_float(
                record.get(
                    "difference"
                )
            )

            selected = bool(
                record.get(
                    "selected"
                )
            )

            if selected:

                status = (
                    "✅ **SELECTED / ABOVE CURRENT MERIT**"
                )

            else:

                status = (
                    "❌ **BELOW CURRENT MERIT**"
                )

            lines.append(
                ""
            )

            lines.append(
                f"**{program} — {campus}**"
            )

            if category:
                lines.append(
                    f"- Category: {category}"
                )

            if session:
                lines.append(
                    f"- Session: {session}"
                )

            if admission_type:
                lines.append(
                    f"- Type: {admission_type}"
                )

            if minimum is not None:
                lines.append(
                    f"- Current closing merit: **{minimum:.5f}**"
                )

            if difference is not None:
                lines.append(
                    f"- Difference: **{difference:+.5f}**"
                )

            lines.append(
                f"- Status: {status}"
            )

        if source_url:

            lines.append(
                ""
            )

            lines.append(
                f"[🔗 Open official UET merit source]({source_url})"
            )

        return {

            "answer":
                "\n".join(lines),

            "source_url":
                source_url,

            "merit_response":
                response,
        }

    # --------------------------------------------------------
    # Normal merit lookup
    # --------------------------------------------------------

    lines = []

    for record in records:

        program = record.get(
            "program",
            record.get(
                "discipline",
                "Unknown program",
            ),
        )

        campus = record.get(
            "campus",
            "Unknown campus",
        )

        category = record.get(
            "category",
            "",
        )

        session = record.get(
            "session",
            "",
        )

        admission_type = record.get(
            "type",
            "",
        )

        minimum = safe_float(
            record.get(
                "minimum_aggregate",
                record.get(
                    "closing_merit"
                ),
            )
        )

        line = (
            f"**{program} — {campus}**"
        )

        if category:
            line += (
                f" | {category}"
            )

        if session:
            line += (
                f" | {session}"
            )

        if admission_type:
            line += (
                f" | {admission_type}"
            )

        if minimum is not None:
            line += (
                f" → **{minimum:.5f}**"
            )

        lines.append(
            line
        )

    if source_url:

        lines.append(
            ""
        )

        lines.append(
            f"[🔗 Open official UET merit source]({source_url})"
        )

    return {

        "answer":
            "\n".join(lines),

        "source_url":
            source_url,

        "merit_response":
            response,
    }


# ============================================================
# CHROMA SOURCE HELPERS
# ============================================================

def get_source_key(
    metadata
):

    metadata = (
        metadata
        or {}
    )

    source_type = normalize(
        metadata.get(
            "source_type"
        )
    )

    pdf_file = normalize(
        metadata.get(
            "pdf_file"
        )
    )

    url = normalize(
        metadata.get(
            "url"
        )
    )

    title = normalize(
        metadata.get(
            "title"
        )
    )

    if (
        source_type == "pdf"
        and pdf_file
    ):

        return (
            f"pdf::{pdf_file}"
        )

    if url:

        return (
            f"url::{url}"
        )

    if title:

        return (
            f"title::{title}"
        )

    return "unknown"


# ============================================================
# CONFIDENCE
# ============================================================

def classify_confidence(
    results
):

    if not results:
        return "none"

    best_distance = results[
        0
    ].get(
        "distance"
    )

    if best_distance is None:
        return "none"

    if (
        best_distance
        <= STRONG_DISTANCE
    ):

        return "strong"

    if (
        best_distance
        <= GOOD_DISTANCE
    ):

        return "good"

    if (
        best_distance
        <= MAX_DISTANCE
    ):

        return "moderate"

    return "low"


# ============================================================
# SOURCE REFERENCE
# ============================================================

def make_source_reference(
    result
):

    metadata = (
        result.get(
            "metadata",
            {},
        )
        or {}
    )

    source_type = normalize(
        metadata.get(
            "source_type"
        )
    )

    title = normalize(
        metadata.get(
            "title"
        )
    )

    url = normalize(
        metadata.get(
            "url"
        )
    )

    pdf_file = normalize(
        metadata.get(
            "pdf_file"
        )
    )

    page = safe_int(
        metadata.get(
            "page"
        )
    )

    return {

        "source_type":
            source_type,

        "title":
            title,

        "url":
            url,

        "pdf_file":
            pdf_file,

        "page":
            page
            if page > 0
            else None,
    }


# ============================================================
# CLEAN CHROMA RESULT
# ============================================================

def clean_result(
    result
):

    metadata = (
        result.get(
            "metadata",
            {},
        )
        or {}
    )

    return {

        "rank":
            result.get(
                "rank"
            ),

        "id":
            result.get(
                "id"
            ),

        "distance":
            result.get(
                "distance"
            ),

        "source_type":
            normalize(
                metadata.get(
                    "source_type"
                )
            ),

        "title":
            normalize(
                metadata.get(
                    "title"
                )
            ),

        "url":
            normalize(
                metadata.get(
                    "url"
                )
            ),

        "pdf_file":
            normalize(
                metadata.get(
                    "pdf_file"
                )
            ),

        "page":
            safe_int(
                metadata.get(
                    "page"
                )
            ),

        "book":
            normalize(
                metadata.get(
                    "book"
                )
            ),

        "temporal":
            bool(
                metadata.get(
                    "temporal",
                    False,
                )
            ),

        "quality_flag":
            normalize(
                metadata.get(
                    "quality_flag"
                )
            ),

        "extraction_method":
            normalize(
                metadata.get(
                    "extraction_method"
                )
            ),

        "categories":
            normalize(
                metadata.get(
                    "categories"
                )
            ),

        "text":
            normalize(
                result.get(
                    "document"
                )
            ),
    }


# ============================================================
# LOAD CHROMA
# ============================================================

def load_collection():

    if not VECTORSTORE_DIR.exists():

        raise FileNotFoundError(
            "\nVector store was not found:\n"
            f"{VECTORSTORE_DIR}\n\n"
            "Run ingestion.py first."
        )

    client = chromadb.PersistentClient(
        path=str(
            VECTORSTORE_DIR
        )
    )

    try:

        collection = (
            client.get_collection(
                name=COLLECTION_NAME
            )
        )

    except Exception as exc:

        raise RuntimeError(
            "\nChroma collection was not found:\n"
            f"{COLLECTION_NAME}\n\n"
            "Run ingestion.py first."
        ) from exc

    return collection


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

def load_embedding_model():

    print()
    print(
        "Loading embedding model:"
    )

    print(
        EMBEDDING_MODEL_NAME
    )

    return SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )


# ============================================================
# RAW CHROMA RETRIEVAL
# ============================================================

def retrieve_candidates(
    collection,
    model,
    question,
):

    query_text = build_query(
        question
    )

    query_embedding = (
        model.encode(
            [query_text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    )

    result = collection.query(

        query_embeddings=
            query_embedding.tolist(),

        n_results=
            RETRIEVAL_CANDIDATES,

        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    ids = (
        result.get(
            "ids",
            [[]],
        )[0]
        if result.get("ids")
        else []
    )

    documents = (
        result.get(
            "documents",
            [[]],
        )[0]
        if result.get("documents")
        else []
    )

    metadatas = (
        result.get(
            "metadatas",
            [[]],
        )[0]
        if result.get("metadatas")
        else []
    )

    distances = (
        result.get(
            "distances",
            [[]],
        )[0]
        if result.get("distances")
        else []
    )

    candidates = []

    for index, chunk_id in enumerate(
        ids
    ):

        candidates.append({

            "id":
                chunk_id,

            "distance":
                distances[index]
                if index < len(
                    distances
                )
                else None,

            "metadata":
                metadatas[index]
                if index < len(
                    metadatas
                )
                else {},

            "document":
                documents[index]
                if index < len(
                    documents
                )
                else "",
        })

    return candidates


# ============================================================
# DISTANCE FILTER
# ============================================================

def filter_by_distance(
    candidates
):

    return [

        candidate

        for candidate in candidates

        if (
            candidate.get(
                "distance"
            )
            is not None
            and
            candidate.get(
                "distance"
            )
            <= MAX_DISTANCE
        )

    ]


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_results(
    candidates
):

    seen = set()

    results = []

    for candidate in candidates:

        chunk_id = candidate.get(
            "id"
        )

        if chunk_id in seen:
            continue

        seen.add(
            chunk_id
        )

        results.append(
            candidate
        )

    return results


# ============================================================
# SOURCE DIVERSIFICATION
# ============================================================

def diversify_sources(
    candidates
):

    selected = []

    source_counts = {}

    for candidate in candidates:

        source_key = get_source_key(
            candidate.get(
                "metadata",
                {},
            )
        )

        count = source_counts.get(
            source_key,
            0,
        )

        if count >= 4:
            continue

        selected.append(
            candidate
        )

        source_counts[
            source_key
        ] = count + 1

        if (
            len(selected)
            >= FINAL_RESULTS
        ):
            break

    # --------------------------------------------------------
    # Fill remaining slots
    # --------------------------------------------------------

    if (
        len(selected)
        < FINAL_RESULTS
    ):

        selected_ids = {
            item.get("id")
            for item in selected
        }

        for candidate in candidates:

            if (
                candidate.get("id")
                in selected_ids
            ):
                continue

            selected.append(
                candidate
            )

            if (
                len(selected)
                >= FINAL_RESULTS
            ):
                break

    return selected


# ============================================================
# BUILD CHROMA RESULTS
# ============================================================

def build_results(
    candidates
):

    results = []

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):

        item = clean_result({

            **candidate,

            "rank":
                rank,
        })

        item[
            "source_reference"
        ] = make_source_reference(
            candidate
        )

        results.append(
            item
        )

    return results


# ============================================================
# SOURCE SUMMARY
# ============================================================

def build_source_summary(
    results
):

    sources = []

    seen = set()

    for result in results:

        reference = result.get(
            "source_reference",
            {},
        )

        key = (

            reference.get(
                "source_type"
            ),

            reference.get(
                "title"
            ),

            reference.get(
                "url"
            ),

            reference.get(
                "pdf_file"
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        sources.append(
            reference
        )

    return sources


# ============================================================
# SAVE AUDIT
# ============================================================

def save_audit(
    question,
    results,
    confidence,
    candidate_count,
):

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit = {

        "question":
            question,

        "embedding_model":
            EMBEDDING_MODEL_NAME,

        "query_prefix":
            BGE_QUERY_PREFIX,

        "collection":
            COLLECTION_NAME,

        "candidate_count":
            candidate_count,

        "final_result_count":
            len(results),

        "max_distance":
            MAX_DISTANCE,

        "confidence":
            confidence,

        "sources":
            build_source_summary(
                results
            ),

        "results":
            results,
    }

    with LAST_RETRIEVAL_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            audit,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# NORMAL RETRIEVE
# ============================================================

def retrieve_normal(
    collection,
    model,
    question,
):

    candidates = retrieve_candidates(
        collection,
        model,
        question,
    )

    candidates.sort(
        key=lambda item: (
            item.get(
                "distance"
            )
            if item.get(
                "distance"
            ) is not None
            else float("inf")
        )
    )

    filtered = filter_by_distance(
        candidates
    )

    filtered = deduplicate_results(
        filtered
    )

    selected = diversify_sources(
        filtered
    )

    results = build_results(
        selected
    )

    confidence = classify_confidence(
        results
    )

    return (
        results,
        confidence,
        len(candidates),
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def route_question(
    question,
    collection,
    model,
):

    question = normalize(
        question
    )

    if not question:

        return {

            "route":
                "semantic",

            "results":
                [],

            "confidence":
                "none",
        }

    # ========================================================
    # MERIT ROUTE
    # ========================================================

    if is_merit_question(
        question
    ):

        print()
        print(
            "[ROUTER] Merit question detected."
        )

        intent = parse_merit_query(
            question
        )

        print(
            f"[ROUTER] Program : "
            f"{intent.get('program')}"
        )

        print(
            f"[ROUTER] Campus  : "
            f"{intent.get('campus')}"
        )

        print(
            f"[ROUTER] Category: "
            f"{intent.get('category')}"
        )

        print(
            f"[ROUTER] Aggregate: "
            f"{intent.get('aggregate')}"
        )

        response = answer_merit_question(
            question
        )

        formatted = format_merit_response(
            response
        )

        return {

            "route":
                "merit",

            "response":
                response,

            "answer":
                formatted["answer"],

            "source_url":
                formatted.get(
                    "source_url"
                ),
        }

    # ========================================================
    # NORMAL SEMANTIC ROUTE
    # ========================================================

    print()
    print(
        "[ROUTER] Normal knowledge question."
    )

    (
        results,
        confidence,
        candidate_count,
    ) = retrieve_normal(
        collection,
        model,
        question,
    )

    save_audit(
        question,
        results,
        confidence,
        candidate_count,
    )

    return {

        "route":
            "semantic",

        "results":
            results,

        "confidence":
            confidence,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print(
        "UET CHATBOT — PRODUCTION RETRIEVER"
    )
    print("=" * 80)

    print()
    print(
        "Routes:"
    )

    print(
        "  Merit questions  -> Dynamic latest UET merit"
    )

    print(
        "  Other questions  -> ChromaDB semantic search"
    )

    # --------------------------------------------------------
    # Load Chroma
    # --------------------------------------------------------

    collection = load_collection()

    count = collection.count()

    print()
    print(
        f"Vectors available: {count}"
    )

    if count == 0:

        raise RuntimeError(
            "ChromaDB collection is empty."
        )

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    model = load_embedding_model()

    print()
    print("=" * 80)
    print(
        "READY"
    )
    print("=" * 80)

    print()
    print(
        "Examples:"
    )

    print(
        "  My aggregate is 90, am I selected for CS Lahore?"
    )

    print(
        "  What is the merit for Electrical Engineering Lahore?"
    )

    print(
        "  What is Civil Engineering merit KSK?"
    )

    print(
        "  What is UET admission process?"
    )

    print(
        "  exit"
    )

    while True:

        try:

            question = input(
                "\nUser question: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print()
            print(
                "Exiting."
            )

            break

        if not question:
            continue

        if question.lower() in {
            "exit",
            "quit",
            "q",
        }:

            print()
            print(
                "Exiting."
            )

            break

        try:

            result = route_question(
                question,
                collection,
                model,
            )

            # ------------------------------------------------
            # MERIT
            # ------------------------------------------------

            if (
                result["route"]
                == "merit"
            ):

                print()
                print("=" * 80)
                print(
                    "MERIT RESPONSE"
                )
                print("=" * 80)

                print()
                print(
                    result.get(
                        "answer",
                        "",
                    )
                )

            # ------------------------------------------------
            # NORMAL
            # ------------------------------------------------

            elif (
                result["route"]
                == "semantic"
            ):

                display_results(
                    question,
                    result.get(
                        "results",
                        [],
                    ),
                    result.get(
                        "confidence",
                        "none",
                    ),
                )

            else:

                print()
                print(
                    "[ERROR] Unknown route:"
                )

                print(
                    result
                )

        except Exception as exc:

            print()
            print(
                "=" * 80
            )

            print(
                "[ERROR]"
            )

            print(
                str(exc)
            )

            print(
                "=" * 80
            )


# ============================================================
# DISPLAY NORMAL RETRIEVAL
# ============================================================

def display_results(
    question,
    results,
    confidence,
):

    print()
    print("=" * 78)
    print(
        "SEMANTIC RETRIEVAL RESULTS"
    )
    print("=" * 78)

    print()
    print(
        f"Query      : {question}"
    )

    print(
        f"Confidence : {confidence.upper()}"
    )

    print(
        f"Results    : {len(results)}"
    )

    if not results:

        print()
        print(
            "[NO RELIABLE RESULTS]"
        )

        return

    for result in results:

        print()
        print(
            "-" * 78
        )

        print(
            f"RANK       : "
            f"{result['rank']}"
        )

        print(
            f"DISTANCE   : "
            f"{result['distance']}"
        )

        print(
            f"SOURCE TYPE: "
            f"{result['source_type']}"
        )

        print(
            f"TITLE      : "
            f"{result['title']}"
        )

        if result["url"]:

            print(
                f"URL        : "
                f"{result['url']}"
            )

        if result["pdf_file"]:

            print(
                f"PDF FILE   : "
                f"{result['pdf_file']}"
            )

        if result["page"]:

            print(
                f"PAGE       : "
                f"{result['page']}"
            )

        print()
        print(
            "TEXT:"
        )

        print(
            result["text"]
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
