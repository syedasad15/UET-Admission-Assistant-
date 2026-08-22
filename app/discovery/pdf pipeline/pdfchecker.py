"""
UET CHATBOT — Quick duplicate verifier

Extracts the first page of text from the three PDFs flagged
as byte-identical by pdfduplicator.py, so you can visually
confirm what content UET is actually serving.

Requires: pip install pypdf
"""

from pathlib import Path
from pypdf import PdfReader

PDF_DIR = Path(r"D:\UET Chatbot\data\inventory\admission\pdfs")

# The three filenames from the duplicate group [001] report
FILES_TO_CHECK = [
    "MS-2026-1_0475d05f-a54f-450c-8383-6733814b433d.pdf",
    "PhD-2026-1_6c024cbe-f598-4566-91ad-66bc1783302f.pdf",
    "8484474c-267f-44bc-93f8-63618c61a9af.pdf",
]


def get_first_page_text(path: Path) -> str:
    reader = PdfReader(str(path))
    if len(reader.pages) == 0:
        return "(no pages found)"
    return reader.pages[0].extract_text() or "(no extractable text)"


def main():
    print()
    print("=" * 70)
    print("DUPLICATE GROUP — FIRST PAGE COMPARISON")
    print("=" * 70)

    texts = {}

    for filename in FILES_TO_CHECK:
        path = PDF_DIR / filename

        print()
        print("-" * 70)
        print(filename)
        print("-" * 70)

        if not path.exists():
            print(f"  MISSING FILE: {path}")
            continue

        text = get_first_page_text(path)
        texts[filename] = text

        # print first ~500 chars so it's readable in terminal
        preview = text.strip()[:500]
        print(preview)
        if len(text.strip()) > 500:
            print("... (truncated)")

    # --------------------------------------------------------
    # Quick verdict
    # --------------------------------------------------------
    print()
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)

    unique_texts = set(t.strip() for t in texts.values())

    if len(unique_texts) == 1:
        print("All three first pages are IDENTICAL text.")
        print("-> Confirms UET is serving the exact same document")
        print("   for MS, PhD, and the generic download link.")
    else:
        print("First-page text DIFFERS between files despite same hash.")
        print("-> Unexpected. Worth a manual look — possibly a PDF")
        print("   with per-page images/fonts that extract differently,")
        print("   but same underlying bytes. Open both manually.")

    print()


if __name__ == "__main__":
    main()