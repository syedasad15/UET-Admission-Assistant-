# UET Admission Assistant

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about
University of Engineering and Technology (UET) Lahore admissions, built from
crawled web pages and downloaded PDFs (prospectuses, fee schedules, merit
lists), embedded into a local vector store, and answered through Gemini with
citations back to the source page/PDF.

## Pipeline

```
Crawl site pages ─┐
                   ├─► Discovery / cleaning / OCR ─► Knowledge merge ─► Ingestion (embed + store)
Download PDFs ────┘                                                          │
                                                                              ▼
                                                                     ChromaDB vector store
                                                                              │
User question ──► Streamlit UI ──► retrieval.py ──► answer.py (Gemini) ──► Answer + sources
```

## Top-level layout

| Path | Purpose |
|---|---|
| `app/` | All source code — see `app/README.md` |
| `data/` | Crawled/extracted data, the vector store, and pipeline artifacts — see `data/README.md` |
| `main.py` | Standalone dev utility that prints a directory tree of the project. Not part of the app runtime. |
| `requirements.txt` | Python dependencies (`streamlit`, `python-dotenv`, `google-genai`, `chromadb`, `sentence-transformers`, `requests`, `pymupdf`) |
| `PROJECT_STRUCTURE.txt` | An auto-generated file/folder inventory snapshot, produced by `app/structure.py`. Note: it references a `tests/` layout that does not exist in the current tree — treat it as a stale snapshot, not documentation. |

## Running it

1. Install dependencies: `pip install -r requirements.txt`
2. Set a Gemini API key as `GOOGLE_API_KEY` or `GEMINI_API_KEY` (via Streamlit
   secrets when deployed, or environment variable / `keyy.env` locally).
3. The vector store under `data/vectorstore/chroma/` is already populated —
   to launch the chatbot UI directly: `streamlit run app/streamlit/app.py`
4. To rebuild the knowledge base from scratch, run the discovery/ingestion
   scripts in `app/discovery/` and `app/ingestion/` in pipeline order (see
   `app/discovery/README.md`).

## Known housekeeping items

- No `.gitignore` — `__pycache__/`, the compiled Chroma binaries, and many
  intermediate backup/audit JSON files under `data/inventory/admission/` are
  committed and inflate the repo (~74 MB).
- `app/retrieval/retrieval.py` and `app/streamlit/app.py` each carry a large
  commented-out earlier version of the file above the live code.
- `app/crawler/admissioncrawler.py` is an empty (0-byte) file.
