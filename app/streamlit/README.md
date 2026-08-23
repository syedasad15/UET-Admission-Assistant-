# app/streamlit/

Stage 6 — the deployed chatbot UI.

| File | Purpose |
|---|---|
| `app.py` | The Streamlit app. **File is 2,111 lines but only from line 1050 onward is live** — lines 1–1049 are a fully commented-out earlier version (same pattern as `retrieval.py`; safe to delete, git history keeps it). Live app: configures the page, loads the Gemini client and Chroma collection/embedding model as cached resources (`@st.cache_resource`), reads the API key via `_get_secret()` which checks `st.secrets` first and falls back to `os.getenv` (correct pattern for both local dev and Streamlit Cloud deployment), generates answers (`generate_answer`), and renders results including source citations (`display_sources`) and a dedicated merit-list response view (`display_merit_response`, `display_merit_error`). |

To run: `streamlit run app/streamlit/app.py` with `GOOGLE_API_KEY` or
`GEMINI_API_KEY` set as an environment variable or in `.streamlit/secrets.toml`.
