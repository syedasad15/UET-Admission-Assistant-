# data/vectorstore/

| Folder | Purpose |
|---|---|
| `chroma/` | Persistent ChromaDB store built by `app/ingestion/ingestion.py`. Contains the `uet_admission_knowledge` collection: 1383 embedded chunks (via `BAAI/bge-small-en-v1.5`), queried at runtime by `app/retrieval/retrieval.py`. |
