# app/answer/

Stage 5 — takes retrieval results and generates a grounded answer via Gemini.

| File | Purpose |
|---|---|
| `answer.py` | Reads `data/retrieval/last_retrieval.json`, loads a Gemini API key from `app/retrieval/keyy.env` (local dev path — the Streamlit app uses `st.secrets`/env vars instead, see `app/streamlit/README.md`), and calls `gemini-3.6-flash` with the retrieved PDF/webpage evidence. Explicitly constrained: Gemini is instructed not to invent information and must answer only from retrieved evidence, then returns an answer with source references. Config: `MAX_CONTEXT_RESULTS = 8`, `MAX_DOCUMENT_CHARS = 12000`. |
