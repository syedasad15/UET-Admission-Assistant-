# app/ingestion/

Stage 3 of the overall pipeline: turns the finished knowledge base into
vector embeddings and stores them for retrieval.

| File | Purpose |
|---|---|
| `ingestion.py` | Loads `_knowledge_base.json` (1383 chunks: 133 from pages, 1250 from PDFs), builds embedding input text per chunk, sanitizes metadata, embeds everything with `BAAI/bge-small-en-v1.5` (`sentence-transformers`), stores the vectors in a persistent on-disk ChromaDB collection (`data/vectorstore/chroma/`), and validates the result. Also writes `_ingestion_manifest.json`. Well-structured, single-purpose script — the cleanest file in the repo. |
| `inspectkb.py` | Small manual-inspection tool for spot-checking the knowledge base or ingestion manifest during development. |
