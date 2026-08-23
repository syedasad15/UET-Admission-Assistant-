# app/discovery/content targeting/

Stage 2 of discovery: narrows the site map down to the URLs actually worth
crawling for content (drops external links, raw files, duplicates).

| File | Purpose |
|---|---|
| `contenttargetreview.py` | Normalizes URLs/values from the site map and produces a reviewed target list (`_content_targets_reviewed.json`) for manual sign-off before crawling. |
| `mapfiilter.py` | Filters the raw site map: identifies file-type links (`looks_like_file`) vs external links (`is_external`), shortens text for review output, writes a human-readable filtered report. (Note the filename typo — "fiilter" — kept as-is to match the repo.) |
| `mapfilter2.py` | Second-pass filter over the map — normalizes URLs and extracts file extensions, likely refining what `mapfiilter.py` produced. |
