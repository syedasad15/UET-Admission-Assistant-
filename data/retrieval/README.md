# data/retrieval/

| File | Purpose |
|---|---|
| `last_retrieval.json` | Output of the most recent run of `app/retrieval/retrieval.py` — the retrieved candidate chunks, their sources, and confidence classifications. Read by `app/answer/answer.py` to generate the grounded Gemini answer. Overwritten on every query — not meant to be a persistent log. |
