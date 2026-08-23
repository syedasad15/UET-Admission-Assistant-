# app/retrieval/

Stage 4 — runtime semantic search over the ChromaDB vector store, plus a
separate specialized path for merit-list questions.

| File | Purpose |
|---|---|
| `retrieval.py` | The production retriever. **File is 11,063 lines but only the last ~2,300 (from `normalize()` at line 8736 onward) are live code** — everything above is a fully commented-out earlier version left in place; should be deleted since git history preserves it. Live functionality: BGE query-prefix handling, similarity-threshold filtering, source/document grouping, duplicate suppression, confidence classification (`classify_confidence`), source diversification (`diversify_sources`), merit-question detection and routing (`is_merit_question`, `route_question`), and retrieval audit logging (`save_audit`). Entry point: `main()`. |
| `merit.py` | Merit-list-specific logic (~49 KB, 23 functions): parses merit questions (campus, category, program, aggregate), filters merit data accordingly, and formats merit-specific responses (`format_merit_response`) separately from general RAG answers. |
| `check_merit.py` | Manual diagnostic: loads the Chroma collection directly and checks how merit-related content is indexed. |
| `check_merit_pdf.py` | Manual diagnostic with queries specifically designed to locate the merit-list PDF itself within the vector store (rather than its content), to verify it was ingested. |
| `debug_retrieval.py` | Diagnostic tool: for a given question, shows every candidate ChromaDB returns (not just the final filtered/diversified top-8) with distance and page, to debug whether a specific expected result is missing, filtered out, or crowded out by diversification. |
| `__pycache__/` | Compiled bytecode cache (`merit.cpython-312.pyc`, `retrieval.cpython-312.pyc`) — should not be committed; add to `.gitignore`. |
