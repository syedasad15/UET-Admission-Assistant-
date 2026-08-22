import json
import re
from pathlib import Path


# ============================================================
# UET CHATBOT — PAGE CHUNKING
# ============================================================
#
# Input:
#   data/inventory/admission/_knowledge_books.json
#   (52 usable pages, 7 books -- title/url/category only,
#   no text)
#   data/inventory/admission/_pages_reviewed.json
#   (58 raw crawled pages -- has the actual text)
#
# Output:
#   data/inventory/admission/_pages_knowledge_chunks.json
#
# Purpose:
#   bookbuilder.py's output only carries metadata (title, url,
#   category, score) -- it never attached the actual page
#   text. This script closes that gap: for every usable page
#   in _knowledge_books.json, it looks up the full text in
#   _pages_reviewed.json (matched by URL) and splits it into
#   sentence-aware chunks sized similarly to the PDF pipeline's
#   chunks (~1000-1400 chars), so pages and PDFs can later be
#   merged into one consistent knowledge base.
#
#   A page with no matching text (shouldn't happen, but not
#   assumed) is recorded under "missing_text" rather than
#   silently dropped.
#
# ============================================================


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

BOOKS_FILE = DATA_DIR / "_knowledge_books.json"

PAGES_FILE = DATA_DIR / "_pages_reviewed.json"

OUTPUT_FILE = DATA_DIR / "_pages_knowledge_chunks.json"


# ============================================================
# CONFIGURATION
# ============================================================

# Target chunk size, matched to the PDF pipeline's average
# (~1036 chars) so retrieval later treats page chunks and PDF
# chunks consistently.
TARGET_CHUNK_CHARS = 1200

# Hard ceiling -- a single "sentence" longer than this gets
# split on whitespace instead of left whole.
MAX_CHUNK_CHARS = 1800

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


# ============================================================
# HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize_url(url):
    """
    Normalize a URL for matching purposes only (trailing
    slash / fragment differences shouldn't break a lookup).
    """

    url = normalize(url)

    url = url.split("#", 1)[0]

    if url.endswith("/"):

        url = url[:-1]

    return url


# ============================================================
# LOAD
# ============================================================

def load_books():

    if not BOOKS_FILE.exists():

        raise FileNotFoundError(
            "\nKnowledge books file was not found:\n"
            f"{BOOKS_FILE}\n\n"
            "Run bookbuilder.py first."
        )

    print()
    print("Reading:")
    print(BOOKS_FILE)

    with BOOKS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data.get("books", {})


def load_pages():

    if not PAGES_FILE.exists():

        raise FileNotFoundError(
            "\nPages reviewed file was not found:\n"
            f"{PAGES_FILE}\n\n"
            "Run pagereviewer.py first."
        )

    print(
        "Reading:"
    )

    print(PAGES_FILE)

    with PAGES_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data.get("pages", [])


def build_page_lookup(pages):
    """
    Index pages by normalized URL, trying both 'url' and
    'final_url' so a redirect doesn't break the match.
    """

    lookup = {}

    for page in pages:

        for key in ("url", "final_url"):

            url = normalize_url(page.get(key, ""))

            if url and url not in lookup:

                lookup[url] = page

    return lookup


# ============================================================
# CHUNKING
# ============================================================

def split_into_sentences(text):

    text = text.strip()

    if not text:
        return []

    return [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_PATTERN.split(text)
        if sentence.strip()
    ]


def hard_split(sentence, max_chars):
    """
    Split an overlong sentence on whitespace boundaries so no
    single chunk ever exceeds max_chars.
    """

    words = sentence.split(" ")

    pieces = []

    current = ""

    for word in words:

        candidate = (
            f"{current} {word}".strip()
            if current
            else word
        )

        if len(candidate) > max_chars and current:

            pieces.append(current)

            current = word

        else:

            current = candidate

    if current:

        pieces.append(current)

    return pieces


def chunk_text(text):
    """
    Greedily pack sentences into chunks close to
    TARGET_CHUNK_CHARS, never exceeding MAX_CHUNK_CHARS.
    """

    sentences = split_into_sentences(text)

    chunks = []

    current = ""

    for sentence in sentences:

        if len(sentence) > MAX_CHUNK_CHARS:

            if current:

                chunks.append(current)
                current = ""

            chunks.extend(
                hard_split(sentence, MAX_CHUNK_CHARS)
            )

            continue

        candidate = (
            f"{current} {sentence}".strip()
            if current
            else sentence
        )

        if len(candidate) > TARGET_CHUNK_CHARS and current:

            chunks.append(current)
            current = sentence

        else:

            current = candidate

    if current:

        chunks.append(current)

    return chunks


# ============================================================
# BUILD PAGE CHUNKS
# ============================================================

def build_chunks(books, page_lookup):

    all_chunks = []

    missing_text = []

    for book_name, entries in books.items():

        for entry in entries:

            url = normalize_url(entry.get("url", ""))

            page = page_lookup.get(url)

            if page is None:

                missing_text.append({
                    "book": book_name,
                    "title": entry.get("title", ""),
                    "url": entry.get("url", ""),
                })

                continue

            text = normalize(page.get("text", ""))

            if not text:

                missing_text.append({
                    "book": book_name,
                    "title": entry.get("title", ""),
                    "url": entry.get("url", ""),
                    "reason": (
                        "Page matched but its text field is "
                        "empty."
                    ),
                })

                continue

            pieces = chunk_text(text)

            is_temporal = (
                entry.get("status") == "TEMPORAL"
                or entry.get("role") == "temporal"
            )

            for chunk_index, piece in enumerate(pieces):

                all_chunks.append({
                    "canonical_url": entry.get("url", ""),
                    "title": entry.get("title", ""),
                    "book": book_name,
                    "chunk_index": chunk_index,
                    "text": piece,
                    "source": "page",
                    "quality_flag": "ok",
                    "status": entry.get("status", ""),
                    "role": entry.get("role", ""),
                    "score": entry.get("score", 0),
                    "categories": entry.get("categories", []),
                    "page_type": entry.get("type", ""),
                    "temporal": is_temporal,
                })

    return all_chunks, missing_text


# ============================================================
# VALIDATION
# ============================================================

def validate(books, chunks, missing_text):

    errors = []

    input_page_count = sum(
        len(entries) for entries in books.values()
    )

    covered_pages = {
        (chunk["book"], chunk["canonical_url"])
        for chunk in chunks
    }

    expected_pages = {
        (book_name, entry.get("url", ""))
        for book_name, entries in books.items()
        for entry in entries
    }

    missing_pages = {
        (item["book"], item["url"])
        for item in missing_text
    }

    unaccounted = expected_pages - covered_pages - missing_pages

    if unaccounted:

        errors.append(
            f"{len(unaccounted)} page(s) neither chunked nor "
            "reported as missing text."
        )

    for chunk in chunks:

        if not chunk["text"].strip():

            errors.append(
                "Empty chunk text for "
                f"{chunk['canonical_url']} "
                f"(chunk {chunk['chunk_index']})"
            )

        if len(chunk["text"]) > MAX_CHUNK_CHARS:

            errors.append(
                "Chunk exceeds MAX_CHUNK_CHARS for "
                f"{chunk['canonical_url']} "
                f"(chunk {chunk['chunk_index']}, "
                f"{len(chunk['text'])} chars)"
            )

    if len(covered_pages) + len(missing_pages) != input_page_count:

        errors.append(
            "Covered + missing page count does not match "
            "input page count "
            f"({len(covered_pages)} + {len(missing_pages)} != "
            f"{input_page_count})"
        )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — PAGE CHUNKING"
    )
    print("=" * 70)
    print()

    books = load_books()

    input_page_count = sum(
        len(entries) for entries in books.values()
    )

    print()
    print(
        f"Books: {len(books)}"
    )

    print(
        f"Input pages: {input_page_count}"
    )

    pages = load_pages()

    print(
        f"Raw crawled pages available: {len(pages)}"
    )

    page_lookup = build_page_lookup(pages)

    # --------------------------------------------------------
    # Chunk
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "CHUNKING"
    )
    print("=" * 70)

    chunks, missing_text = build_chunks(books, page_lookup)

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print()

    if not missing_text:

        print("All pages matched and chunked successfully.")

    else:

        print(
            f"WARNING: {len(missing_text)} page(s) could not "
            "be chunked:"
        )

        for item in missing_text:

            print()
            print(
                f" — [{item['book']}] {item['title']}"
            )

            print(
                f"   {item['url']}"
            )

            if item.get("reason"):

                print(
                    f"   Reason: {item['reason']}"
                )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    chunk_lens = [len(c["text"]) for c in chunks]

    books_count = {}

    for chunk in chunks:

        books_count[chunk["book"]] = (
            books_count.get(chunk["book"], 0) + 1
        )

    print()
    print("=" * 70)
    print(
        "CHUNKING RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"  Pages chunked      : "
        f"{input_page_count - len(missing_text)}"
    )

    print(
        f"  Pages missing text : {len(missing_text)}"
    )

    print(
        f"  Total chunks       : {len(chunks)}"
    )

    if chunk_lens:

        print(
            f"  Avg chunk size     : "
            f"{sum(chunk_lens) // len(chunk_lens)} chars"
        )

        print(
            f"  Min / Max chunk    : "
            f"{min(chunk_lens)} / {max(chunk_lens)} chars"
        )

    print()
    print(
        "  Chunks per book:"
    )

    for book_name, count in sorted(
        books_count.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"    {book_name:<28} : {count}"
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate(books, chunks, missing_text)

    if validation_errors:

        print(
            "INVALID"
        )

        for error in validation_errors:

            print(
                f"ERROR: {error}"
            )

        raise ValueError(
            "Page chunking validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "source": "UET Admissions Portal",
        "stage": "page_chunking",
        "books_file": str(BOOKS_FILE),
        "pages_file": str(PAGES_FILE),
        "output_file": str(OUTPUT_FILE),
        "counts": {
            "input_pages": input_page_count,
            "pages_chunked": (
                input_page_count - len(missing_text)
            ),
            "pages_missing_text": len(missing_text),
            "total_chunks": len(chunks),
        },
        "books": books_count,
        "missing_text": missing_text,
        "chunks": chunks,
    }

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print(
        "SAVED"
    )
    print("=" * 70)

    print()
    print(
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()