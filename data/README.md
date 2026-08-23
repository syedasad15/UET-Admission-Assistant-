# data/

All pipeline data: crawl output, PDF/OCR artifacts, the assembled knowledge
base, the vector store, and runtime retrieval logs.

| Folder | Purpose |
|---|---|
| `inventory/` | Every intermediate JSON/text artifact produced by `app/discovery/`, plus the final `_knowledge_base.json`. Contains one large working subfolder, `admission/` — see `inventory/README.md`. |
| `merit/` | Holds the current UET merit-list PDF used by the merit-question retrieval path. |
| `retrieval/` | Runtime output: the most recent retrieval result, read by `app/answer/answer.py`. |
| `vectorstore/` | The persistent ChromaDB vector store (embeddings + SQLite metadata) built by `app/ingestion/ingestion.py`. |

**Housekeeping note:** `inventory/admission/` alone holds 85 files, including
14 numbered/dated backup and audit copies of the same PDF-chunk data
(`_pdf_knowledge_chunks_73_merged*`, `_pdf_knowledge_chunks_backup_*`, etc.).
These were useful during manual pipeline debugging but aren't needed at
runtime — only `_knowledge_base.json` (consumed by `app/ingestion/`) and
`main_sections.json` are. Consider moving the rest to an `archive/` folder
or excluding them from the repo.
