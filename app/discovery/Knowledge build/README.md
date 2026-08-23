# app/discovery/Knowledge build/

Stage 5 of discovery — the final assembly step that turns cleaned page text
and PDF chunks into the finished knowledge base consumed by `app/ingestion/`.

| File | Purpose |
|---|---|
| `bookbuilder.py` | Converts refined page decisions (`_knowledge_refined.json`) into "knowledge books" (`_knowledge_books.json`) — the page-derived side of the knowledge base. |
| `knowledgerefinement.py` | Refines/filters raw page/PDF content before it's built into books — config-driven cleanup stage. |
| `actionbuilder.py` | Extracts preserved "ACTION" links (e.g. challan generation, login, apply-now buttons) from `_pages_reviewed.json` into `_actions_registry.json`, so the chatbot can point users to actionable site links, not just text. |
| `knowledgemerge.py` | The final merge: combines `_pages_knowledge_chunks.json` (133 chunks/52 pages), `_pdf_knowledge_final.json` (1250 chunks/19 PDFs), and `_actions_registry.json` (14 action links) into the single `_knowledge_base.json` that `app/ingestion/ingestion.py` embeds. |
| `knowledgecheck.py` | Manual inspection/validation script — prints formatted previews of knowledge entries for a human sanity check before ingestion. |
