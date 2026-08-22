"""
UET Admission PDFs -> knowledge base JSON extractor
--------------------------------------------------------
Handles all 26 CANONICAL PDFs from _pdf_duplicates.json (not the raw
pdfs/ folder directly -- that would reprocess duplicate content that
was already deduplicated in an earlier stage).

Pipeline per page:
  1. Native text layer if present (fast, exact).
  2. If native text exists, ALSO scan embedded images >= a minimum
     size and OCR them -- captures tables/notices/charts dropped into
     an otherwise normal text page (native text alone would miss
     anything baked into image pixels).
  3. If NO native text exists, the whole page is rendered and OCR'd as
     one image. This single pass already captures everything visually
     on the page (vector art + composited images together), so no
     separate per-image OCR is needed on this path -- it would risk
     missing vector-drawn headings and producing garbage from
     small QR codes/icons.
  4. clean_ocr_text(): SAFE formatting-only cleanup. Never
     guesses/rewrites content -- e.g. it does NOT try to reconstruct a
     garbled URL, because a wrong guess would silently feed incorrect
     info (like a broken admissions link) into a chatbot students rely
     on. Garbled URL-looking fragments are surfaced in "flagged_lines"
     for manual review instead.
  5. assess_text_quality(): heuristic-only signal (vowel ratio + how
     many "words" look like noise). FLAGS a page, never drops it from
     the per-PDF file -- but flagged pages do NOT contribute chunks to
     the combined chunk file (there's no point chunking/embedding
     garbage). This is the mechanism that currently filters out
     Urdu-only content, since EasyOCR is only loaded for English right
     now (LANGUAGES = ["en"]) -- Urdu OCR is a deliberate, scoped-out
     decision for a later phase with dedicated resources, not a bug.

KNOWN, INTENTIONAL LIMITATION:
  Urdu-language content (whether in embedded images or full-page
  scans) will come back garbled under English-only OCR and get
  filtered by the quality check. This is expected. See the
  SKIP SUMMARY printed at the end of each run, and
  _pdf_extraction_skip_summary.json, to see exactly how much content
  (and which PDFs/pages) this affects, so it's a known, trackable gap
  rather than a silent one.

Output:
  data/inventory/admission/_pdf_knowledge_<canonical_filename_stem>.json
    - list of page-level records for that one PDF

  data/inventory/admission/_pdf_knowledge_chunks.json
    - flat list of chunk-level records across ALL PDFs, each tagged
      with the originating canonical_url/canonical_title/sha256 so
      later pipeline stages can trace content back to its source.

  data/inventory/admission/_pdf_extraction_skip_summary.json
    - every page that was skipped (garbled/empty), across all PDFs,
      with its reason -- so scoped-out content (like Urdu right now)
      is visible and trackable, not silently missing.
"""

import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image
from tqdm import tqdm
import json
from pathlib import Path
import re
import sys
import gc
import traceback

try:
    import torch
    import os as _os
    torch.set_num_threads(_os.cpu_count())
except Exception:
    pass

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

DUPLICATES_FILE = DATA_DIR / "_pdf_duplicates.json"

PDF_DIR = DATA_DIR / "pdfs"

CHUNKS_OUTPUT_FILE = DATA_DIR / "_pdf_knowledge_chunks.json"

SKIP_SUMMARY_FILE = DATA_DIR / "_pdf_extraction_skip_summary.json"


# ============================================================
# CONFIGURATION
# ============================================================

OCR_DPI = 200
LANGUAGES = ["en"]  # Urdu intentionally scoped out for now -- see
# module docstring. Add "ur" back once dedicated resources are
# allocated post-approval.

ROW_TOLERANCE_RATIO = 1.3
COLUMN_GAP_RATIO = 0.08

CANVAS_SIZE_LADDER = [1600, 1280, 960, 640]
RECOGNITION_BATCH_SIZE = 8

CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 30

MIN_IMAGE_AREA_FOR_OCR = 40000  # ~200x200px -- filters out small
# decorative icons/logos/QR codes so they don't get OCR'd into
# garbage. A page that mixes real body text with a meaningful
# embedded graphic (a scanned table, a photo of a notice board, etc.)
# needs BOTH captured -- see extract_page() below.


# ============================================================
# TEXT CLEANUP / QUALITY / CHUNKING
# ============================================================

def clean_ocr_text(text):
    """SAFE, format-level cleanup only -- content-level guesses (like
    URL reconstruction) are intentionally NOT done here."""
    if not text:
        return text
    text = "".join(ch for ch in text if ch == "\n" or ch.isprintable())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\|\s*\|", "|", text)
    text = re.sub(r"^\s*\|\s*|\s*\|\s*$", "", text, flags=re.MULTILINE)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def flag_garbled_urls(text):
    """Surfaces lines that LOOK like a mangled URL/website reference so
    a human can verify the real link. Does not auto-correct."""
    flags = []
    for line in text.split("\n"):
        if re.search(r"\bhttps?\b", line, re.IGNORECASE) or re.search(
            r"\b\w+\s*\.\s*(edu|pk|com|org|gov)\b", line, re.IGNORECASE
        ):
            flags.append(line.strip())
    return flags


def assess_text_quality(text):
    """Heuristic flag for garbled/wrong-script OCR output (this is
    what currently catches Urdu-only pages under English-only OCR).
    Flags, never drops from the per-page record -- but flagged pages
    contribute no chunks to the combined chunk file."""
    if not text or not text.strip():
        return {"flag": "empty", "ascii_letter_ratio": 0.0, "vowel_ratio": 0.0, "suspicious_word_ratio": 0.0}

    letters = sum(1 for c in text if c.isalpha() and c.isascii())
    total_chars = len(text)
    ascii_letter_ratio = letters / total_chars if total_chars else 0.0

    vowels = sum(1 for c in text if c.lower() in "aeiou")
    vowel_ratio = vowels / letters if letters else 0.0

    words = text.split()

    def _is_suspicious(w):
        has_noise_char = bool(re.search(r"[_~{}]", w))
        # A single hyphenated alpha+digit token (e.g. "FALL-2026", "COVID-19",
        # "Rs.5000") is completely normal English text -- only treat
        # letter+digit mixing as suspicious when it's NOT just a
        # word-hyphen-number pattern.
        core = re.sub(r"[-./]", "", w)
        has_mixed_alnum = any(c.isdigit() for c in core) and any(c.isalpha() for c in core)
        return has_noise_char or has_mixed_alnum

    suspicious_ratio = (
        sum(1 for w in words if _is_suspicious(w)) / len(words) if words else 0.0
    )

    # Ratio-based judgement is unreliable on very short text.
    ratio_is_reliable = len(words) >= 10

    if (ratio_is_reliable and suspicious_ratio > 0.15) or vowel_ratio < 0.25:
        flag = "likely_garbled"
    elif ascii_letter_ratio < 0.35:
        flag = "likely_non_english_or_garbled"
    else:
        flag = "ok"

    return {
        "flag": flag,
        "ascii_letter_ratio": round(ascii_letter_ratio, 3),
        "vowel_ratio": round(vowel_ratio, 3),
        "suspicious_word_ratio": round(suspicious_ratio, 3),
    }


def chunk_text(text, chunk_size_words=CHUNK_SIZE_WORDS, overlap_words=CHUNK_OVERLAP_WORDS):
    """Splits text into overlapping word-count chunks for embedding."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size_words:
        return [text]

    chunks = []
    start = 0
    step = max(chunk_size_words - overlap_words, 1)
    while start < len(words):
        chunk_words = words[start : start + chunk_size_words]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size_words >= len(words):
            break
        start += step
    return chunks


# ============================================================
# OCR SETUP
# ============================================================

def check_model_cache(languages):
    import os
    cache_dir = os.path.join(os.path.expanduser("~"), ".EasyOCR", "model")
    print(f"Checking EasyOCR model cache: {cache_dir}")
    if not os.path.isdir(cache_dir):
        print("   No cache directory yet -- all models will be downloaded now.")
        return
    cached_files = os.listdir(cache_dir)
    print(f"   Found {len(cached_files)} cached file(s): {cached_files}")
    hints = {"en": "english", "ur": "urdu"}
    for lang in languages:
        hint = hints.get(lang, lang)
        found = any(hint in f.lower() for f in cached_files)
        status = "already cached" if found else "NOT found -- will download on first use"
        print(f"   [{lang}] {status}")


def load_reader():
    check_model_cache(LANGUAGES)
    print(f"Loading EasyOCR reader for languages: {LANGUAGES} ...")
    reader = easyocr.Reader(LANGUAGES, gpu=False)
    print("EasyOCR reader loaded.")
    return reader


def _is_oom_error(e):
    msg = str(e).lower()
    return isinstance(e, MemoryError) or "not enough memory" in msg or "out of memory" in msg


def _cluster_1d_fixed(values, threshold):
    if not values:
        return []
    vals = sorted(values)
    clusters = [[vals[0]]]
    for i in range(1, len(vals)):
        if vals[i] - vals[i - 1] > threshold:
            clusters.append([])
        clusters[-1].append(vals[i])
    return clusters


def reconstruct_table_text(items, page_width):
    """Anchor-based row grouping + column bucketing."""
    if not items:
        return ""

    heights = [it["h"] for it in items]
    median_h = sorted(heights)[len(heights) // 2]
    row_tol = max(median_h * ROW_TOLERANCE_RATIO, 8)
    col_gap_px = max(page_width * COLUMN_GAP_RATIO, 40)

    items_sorted = sorted(items, key=lambda d: d["y"])
    rows = []
    current_row = [items_sorted[0]]
    anchor_y = items_sorted[0]["y"]
    for it in items_sorted[1:]:
        if it["y"] - anchor_y <= row_tol:
            current_row.append(it)
        else:
            rows.append(current_row)
            current_row = [it]
            anchor_y = it["y"]
    rows.append(current_row)

    lines = []
    for row in rows:
        xs = [it["x"] for it in row]
        x_clusters = _cluster_1d_fixed(xs, threshold=col_gap_px)
        col_bounds = sorted([(min(c), max(c)) for c in x_clusters], key=lambda b: b[0])

        buckets = {i: [] for i in range(len(col_bounds))}
        for it in row:
            for idx, (lo, hi) in enumerate(col_bounds):
                if lo - 1 <= it["x"] <= hi + 1:
                    buckets[idx].append(it)
                    break

        col_texts = []
        for idx in range(len(col_bounds)):
            bucket_items = sorted(buckets[idx], key=lambda d: d["y"])
            col_texts.append(" ".join(it["text"] for it in bucket_items))

        lines.append(" | ".join(t for t in col_texts if t))

    return "\n".join(lines)


def ocr_image_ordered(reader, pil_image):
    img_array = np.array(pil_image)
    page_width = pil_image.width

    results = None
    canvas_size_used = None
    last_error = None

    for canvas_size in CANVAS_SIZE_LADDER:
        try:
            results = reader.readtext(
                img_array,
                detail=1,
                paragraph=False,
                canvas_size=canvas_size,
                mag_ratio=1.0,
                batch_size=RECOGNITION_BATCH_SIZE,
            )
            canvas_size_used = canvas_size
            break
        except Exception as e:
            if _is_oom_error(e):
                tqdm.write(f"   [warn] OOM at canvas_size={canvas_size}, retrying smaller...")
                gc.collect()
                last_error = e
                continue
            raise

    if results is None:
        raise last_error if last_error else RuntimeError("OCR failed: unknown reason")

    if not results:
        return "", canvas_size_used

    items = []
    for bbox, text, conf in results:
        if not text.strip():
            continue
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        y_center = sum(ys) / len(ys)
        x_left = min(xs)
        height = max(ys) - min(ys)
        items.append({"text": text.strip(), "y": y_center, "x": x_left, "h": height})

    if not items:
        return "", canvas_size_used

    text_out = reconstruct_table_text(items, page_width)
    return text_out, canvas_size_used


# ============================================================
# PER-PAGE EXTRACTION
# ============================================================

QUALITY_FLAGS_TO_SKIP_SAVING = {"likely_garbled", "likely_non_english_or_garbled"}


def _pixmap_to_pil(doc, xref):
    """Convert an embedded image xref to a PIL RGB image, handling
    grayscale and CMYK color spaces."""
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha < 4:
        if pix.n - pix.alpha == 1:
            pil_img = Image.frombytes("L", [pix.width, pix.height], pix.samples).convert("RGB")
        else:
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    else:
        pix = fitz.Pixmap(fitz.csRGB, pix)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    pix = None
    return pil_img


def extract_page(doc, page_index, reader):
    """
    Handles pages with:
      - only native (selectable) text -> use it directly.
      - only image/vector content, no text layer -> full-page render +
        OCR (captures everything composited on the page in one pass).
      - BOTH native text AND a meaningful embedded image with its own
        extra text -> native text + OCR of images >= MIN_IMAGE_AREA_FOR_OCR,
        merged together.
    """
    page = doc[page_index]
    native_raw = page.get_text("text").strip()

    if native_raw:
        image_texts = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                pil_img = _pixmap_to_pil(doc, xref)
            except Exception as e:
                tqdm.write(f"   [warn] page {page_index+1}: couldn't decode image xref {xref}: {e}")
                continue

            if pil_img.width * pil_img.height < MIN_IMAGE_AREA_FOR_OCR:
                continue

            try:
                img_txt, _ = ocr_image_ordered(reader, pil_img)
                img_txt = clean_ocr_text(img_txt)
                if img_txt:
                    image_texts.append(img_txt)
            except Exception as e:
                tqdm.write(f"   [warn] page {page_index+1}: embedded image OCR failed: {e}")
            finally:
                del pil_img
                gc.collect()

        parts = [clean_ocr_text(native_raw)]
        if image_texts:
            parts.append("\n\n".join(image_texts))
        cleaned = "\n\n".join(parts)
        quality = assess_text_quality(cleaned)
        source = "native+embedded_image_ocr" if image_texts else "native"
        canvas_size_used = None
    else:
        mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pix = None

        raw_txt, canvas_size_used = ocr_image_ordered(reader, pil_img)
        del pil_img
        gc.collect()

        cleaned = clean_ocr_text(raw_txt)
        quality = assess_text_quality(cleaned)
        source = "full_page_ocr"

    if quality["flag"] in QUALITY_FLAGS_TO_SKIP_SAVING:
        result = {
            "page": page_index + 1,
            "source": source,
            "quality": quality,
            "skipped": True,
            "skip_reason": "low_quality_ocr_output",
            "text": "",
            "chunks": [],
        }
        if canvas_size_used is not None:
            result["canvas_size_used"] = canvas_size_used
        return result

    result = {
        "page": page_index + 1,
        "source": source,
        "text": cleaned,
        "quality": quality,
    }
    if canvas_size_used is not None:
        result["canvas_size_used"] = canvas_size_used

    flagged = flag_garbled_urls(result["text"])
    if flagged:
        result["flagged_lines"] = flagged

    result["chunks"] = chunk_text(result["text"])
    return result


# ============================================================
# PER-PDF PROCESSING
# ============================================================

def process_pdf(pdf_path, doc_metadata, reader, output_dir):
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    stem = pdf_path.stem
    out_json = output_dir / f"_pdf_knowledge_{stem}.json"

    print(f"\nPDF: {pdf_path.name} | Pages: {total_pages}")
    print(f"  Source URL: {doc_metadata.get('canonical_url', '')}")

    knowledge = []
    skipped_pages = []

    progress = tqdm(range(total_pages), desc=f"  {stem}", unit="page")
    for i in progress:
        progress.set_postfix_str(f"page {i+1}/{total_pages}: OCR running...")
        try:
            result = extract_page(doc, i, reader)
            progress.set_postfix_str(
                f"page {i+1}/{total_pages}: done ({result['source']}, quality={result['quality']['flag']})"
            )
        except Exception as e:
            tqdm.write(f"   [ERROR] {stem} page {i+1} failed even after retry ladder: {e}")
            traceback.print_exc()
            result = {"page": i + 1, "source": "error", "text": "", "error": str(e), "chunks": [], "skipped": True, "skip_reason": "extraction_error"}
            progress.set_postfix_str(f"page {i+1}/{total_pages}: ERROR")
        knowledge.append(result)

        if result.get("skipped"):
            skipped_pages.append({
                "page": result["page"],
                "reason": result.get("skip_reason", "unknown"),
                "quality_flag": result.get("quality", {}).get("flag", ""),
            })

        with out_json.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "canonical_url": doc_metadata.get("canonical_url", ""),
                    "canonical_title": doc_metadata.get("canonical_title", ""),
                    "sha256": doc_metadata.get("sha256", ""),
                    "all_urls": doc_metadata.get("all_urls", []),
                    "pages": knowledge,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        gc.collect()

    doc.close()

    if skipped_pages:
        print(
            f"  {len(skipped_pages)}/{total_pages} page(s) skipped "
            f"(low quality / likely non-English OCR output)"
        )

    print(f"  Done: {stem} -> {out_json}")
    return knowledge, skipped_pages, stem


# ============================================================
# LOAD CANONICAL PDF LIST (from _pdf_duplicates.json -- avoids
# reprocessing duplicate content already resolved earlier)
# ============================================================

def load_canonical_documents():

    if not DUPLICATES_FILE.exists():
        raise FileNotFoundError(
            f"\nPDF duplicates registry was not found:\n{DUPLICATES_FILE}\n\n"
            "Run pdfduplicator.py first."
        )

    with DUPLICATES_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    unique_documents = data.get("unique_documents", [])

    entries = []
    missing = []

    for doc in unique_documents:
        filename = doc.get("canonical_local_filename", "")
        path = PDF_DIR / filename if filename else None

        all_urls = [doc.get("canonical_url", "")] + [
            alias.get("url", "") for alias in doc.get("aliases", [])
        ]

        metadata = {
            "canonical_url": doc.get("canonical_url", ""),
            "canonical_title": doc.get("canonical_title", ""),
            "sha256": doc.get("sha256", ""),
            "all_urls": all_urls,
        }

        if not filename or path is None or not path.exists():
            missing.append(metadata)
            continue

        entries.append((path, metadata))

    return entries, missing


# ============================================================
# MAIN
# ============================================================

def main():
    entries, missing = load_canonical_documents()

    print(f"Canonical PDFs found: {len(entries)}")
    if missing:
        print(f"WARNING: {len(missing)} canonical PDF(s) missing on disk, skipped:")
        for m in missing:
            print(f"  - {m.get('canonical_title', '')} | {m.get('canonical_url', '')}")

    if not entries:
        print("No PDFs to process.")
        sys.exit(1)

    reader = load_reader()

    all_chunks = []
    all_skipped = []  # across every PDF, for the run-wide summary

    for pdf_path, doc_metadata in entries:
        knowledge, skipped_pages, stem = process_pdf(pdf_path, doc_metadata, reader, DATA_DIR)

        for page_record in knowledge:
            source = page_record.get("source", "unknown")
            quality_flag = page_record.get("quality", {}).get("flag", "n/a")
            for idx, chunk in enumerate(page_record.get("chunks", [])):
                all_chunks.append({
                    "canonical_url": doc_metadata.get("canonical_url", ""),
                    "canonical_title": doc_metadata.get("canonical_title", ""),
                    "sha256": doc_metadata.get("sha256", ""),
                    "all_urls": doc_metadata.get("all_urls", []),
                    "pdf_file": pdf_path.name,
                    "page": page_record["page"],
                    "chunk_index": idx,
                    "text": chunk,
                    "source": source,
                    "quality_flag": quality_flag,
                })

        for skip in skipped_pages:
            all_skipped.append({
                "canonical_url": doc_metadata.get("canonical_url", ""),
                "canonical_title": doc_metadata.get("canonical_title", ""),
                "pdf_file": pdf_path.name,
                "page": skip["page"],
                "reason": skip["reason"],
                "quality_flag": skip["quality_flag"],
            })

        # checkpoint after every PDF
        with CHUNKS_OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        with SKIP_SUMMARY_FILE.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "note": (
                        "Pages listed here produced no usable text under "
                        "current OCR settings (LANGUAGES = "
                        f"{LANGUAGES}). As of now, Urdu-only content is "
                        "expected to appear here -- this is a scoped, "
                        "intentional gap (see module docstring), not a bug."
                    ),
                    "total_skipped_pages": len(all_skipped),
                    "skipped_pages": all_skipped,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    # --------------------------------------------------------
    # Final run-wide summary
    # --------------------------------------------------------

    print(f"\nAll done. {len(entries)} PDF(s) processed, {len(all_chunks)} total chunks.")
    print(f"Combined chunk file: {CHUNKS_OUTPUT_FILE}")

    print()
    print("=" * 70)
    print("SKIP SUMMARY (pages that produced no usable text)")
    print("=" * 70)

    if not all_skipped:
        print("None -- every page produced usable text.")
    else:
        print(f"{len(all_skipped)} page(s) skipped across {len(entries)} PDF(s):")
        by_pdf = {}
        for s in all_skipped:
            by_pdf.setdefault(s["pdf_file"], []).append(s["page"])
        for pdf_file, pages in by_pdf.items():
            print(f"  - {pdf_file}: page(s) {pages}")
        print(f"\nFull detail saved to: {SKIP_SUMMARY_FILE}")


if __name__ == "__main__":
    main()