# app/

All source code, organized by pipeline stage.

| Folder | Stage | Purpose |
|---|---|---|
| `crawler/` | 1. Crawl | Generic breadth-first website crawler |
| `discovery/` | 2. Discover & clean | Everything from finding admission pages/PDFs through OCR, review, and knowledge-base assembly. The largest and messiest stage — see `discovery/README.md`. |
| `ingestion/` | 3. Ingest | Embeds the finished knowledge base and stores it in ChromaDB |
| `retrieval/` | 4. Retrieve | Runtime semantic search + merit-list-specific query handling |
| `answer/` | 5. Answer | Sends retrieved evidence to Gemini and generates a grounded answer |
| `streamlit/` | 6. UI | The deployed chatbot interface |
| `structure.py` | dev tool | One-off script: walks the project and counts Python imports per module. Hardcodes a Windows path (`D:\UET Chatbot`) — a personal dev utility, not part of the app. |

Run order for rebuilding the knowledge base from scratch: `crawler/` →
`discovery/` (sitemapping → content targeting → content crawling → pdf
pipeline → Knowledge build) → `ingestion/`. Then `retrieval/` and `answer/`
are used at query time, served by `streamlit/`.
